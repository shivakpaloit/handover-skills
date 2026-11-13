import json
import os
import stat
import sys
import tempfile
import textwrap
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
import gen_e2_metrics as g  # noqa: E402


def issue(key, created, status="Done", done=None, labels=(), itype="Story", parent=None):
    f = {"created": created, "status": {"name": status}, "resolutiondate": done,
         "labels": list(labels), "issuetype": {"name": itype}}
    if parent:
        f["parent"] = {"key": parent}
    return {"key": key, "fields": f}


def move(when, frm, to):
    return {"created": when, "items": [{"field": "status", "fromString": frm, "toString": to}]}


class FakeAcli:
    def __init__(self, routes, counts):
        self.routes, self.counts, self.seen = routes, counts, []

    def search(self, jql, fields=None):
        self.seen.append(jql)
        for needle, result in self.routes:
            if all(n in jql for n in needle):
                return result
        return []

    search_with_dates = search

    def count(self, jql):
        self.seen.append(jql)
        for needle, n in self.counts:
            if all(x in jql for x in needle):
                return n
        return 0


class FakeChangelog:
    available, missing = True, []

    def __init__(self, data):
        self.data = data
        self.prefetched = []

    def prefetch(self, issues):
        self.prefetched.append([i["key"] for i in issues])

    def get(self, key):
        return self.data.get(key, [])


GEN = 'labels = "AISDLC"'
OTHER = "labels is EMPTY OR labels not in"


def metrics(acli, cl):
    return g.Metrics(acli, cl, ["MKT"], "AISDLC", date(2026, 10, 1), date(2026, 10, 31),
                     ["To Do"], log=lambda _m: None,
                     in_progress_statuses=["In Progress", "In Review"], review_statuses=["In Review"])


class HelpersTest(unittest.TestCase):
    def test_parse_dt_jira_formats(self):
        self.assertEqual(g.parse_dt("2026-10-01T10:00:00.000+0800").utcoffset().total_seconds(), 8 * 3600)
        self.assertIsNotNone(g.parse_dt("2026-10-01T10:00:00Z"))
        self.assertIsNotNone(g.parse_dt("2026-10-01T10:00:00.1234567+08:00"))
        self.assertIsNone(g.parse_dt(None))

    def test_last_month(self):
        self.assertEqual(g.last_month(date(2026, 1, 15)), (date(2025, 12, 1), date(2025, 12, 31)))

    def test_entered_status_created_in_todo(self):
        f = issue("A-1", "2026-10-01T00:00:00Z")["fields"]
        h = [move("2026-10-03T00:00:00Z", "To Do", "In Progress")]
        self.assertEqual(g.entered_status_at(f, h, ["to do"]), g.parse_dt("2026-10-01T00:00:00Z"))

    def test_entered_status_from_backlog(self):
        f = issue("A-1", "2026-10-01T00:00:00Z")["fields"]
        h = [move("2026-10-02T00:00:00Z", "Backlog", "To Do"), move("2026-10-04T00:00:00Z", "To Do", "Done")]
        self.assertEqual(g.entered_status_at(f, h, ["To Do"]), g.parse_dt("2026-10-02T00:00:00Z"))

    def test_entered_status_never(self):
        f = issue("A-1", "2026-10-01T00:00:00Z", status="Backlog")["fields"]
        self.assertIsNone(g.entered_status_at(f, [], ["To Do"]))

    def test_normalize_issue_shapes(self):
        self.assertEqual(g.normalize_issues({"issues": [{"key": "A-1", "fields": {"x": 1}}]})[0]["fields"], {"x": 1})
        self.assertEqual(g.normalize_issues([{"key": "A-1", "created": "c"}])[0]["fields"], {"created": "c"})


class MetricsTest(unittest.TestCase):
    def setUp(self):
        stories_gen = [issue("MKT-1", "2026-10-01T00:00:00Z", done="2026-10-05T00:00:00Z", labels=["AISDLC"]),
                       issue("MKT-2", "2026-10-01T00:00:00Z", done="2026-10-03T00:00:00Z", labels=["AISDLC"])]
        stories_other = [issue("MKT-3", "2026-10-01T00:00:00Z", done="2026-10-11T00:00:00Z")]
        epic_gen = [issue("MKT-10", "2026-10-01T00:00:00Z", status="In Progress", itype="Epic", labels=["AISDLC"])]
        epic_other = [issue("MKT-20", "2026-10-02T00:00:00Z", status="To Do", itype="Epic")]
        children = [issue("MKT-11", "2026-10-03T00:00:00Z", status="Backlog", parent="MKT-10"),
                    issue("MKT-12", "2026-10-02T12:00:00Z", status="In Progress", parent="MKT-10")]
        reviewed_gen = [stories_gen[1], issue("MKT-4", "2026-10-01T00:00:00Z", status="In Review", labels=["AISDLC"])]
        reviewed_other = [issue("MKT-5", "2026-09-20T00:00:00Z", status="In Review")]
        created_gen = [stories_gen[0], stories_gen[1], reviewed_gen[1],
                       issue("MKT-6", "2026-10-10T00:00:00Z", status="In Progress", labels=["AISDLC"])]
        created_other = [stories_other[0], issue("MKT-7", "2026-10-20T00:00:00Z", status="To Do"),
                         issue("MKT-8", "2026-10-30T00:00:00Z", status="To Do")]
        self.acli = FakeAcli(
            routes=[(("statusCategory = Done", GEN), stories_gen),
                    (("statusCategory = Done", OTHER), stories_other),
                    (('parent in (',), children),
                    (('issuetype = "Story"', 'updated >=', GEN), reviewed_gen),
                    (('issuetype = "Story"', 'updated >=', OTHER), reviewed_other),
                    (('issuetype = "Story"', 'created >=', GEN), created_gen),
                    (('issuetype = "Story"', 'created >=', OTHER), created_other),
                    (('issuetype = "Epic"', "created >=", GEN), epic_gen),
                    (('issuetype = "Epic"', "created >=", OTHER), epic_other)],
            counts=[(("CHANGED TO", GEN), 3), (("CHANGED TO", OTHER), 5),
                    (('issuetype = "Story"', "created >=", GEN), 4),
                    (('issuetype = "Story"', "created >="), 16)])
        self.cl = FakeChangelog({
            "MKT-1": [move("2026-10-02T00:00:00Z", "Backlog", "To Do"), move("2026-10-03T00:00:00Z", "To Do", "In Progress"),
                      move("2026-10-05T00:00:00Z", "In Progress", "Done")],
            "MKT-2": [move("2026-10-02T00:00:00Z", "To Do", "In Review"), move("2026-10-03T00:00:00Z", "In Review", "Done")],
            "MKT-3": [move("2026-10-11T00:00:00Z", "To Do", "Done")],
            "MKT-12": [move("2026-10-04T00:00:00Z", "To Do", "In Progress")],
            "MKT-4": [move("2026-10-02T00:00:00Z", "To Do", "In Progress"), move("2026-10-04T00:00:00Z", "In Progress", "In Review")],
            "MKT-5": [move("2026-09-25T00:00:00Z", "To Do", "In Progress"), move("2026-09-28T00:00:00Z", "In Progress", "In Review"),
                      move("2026-10-03T00:00:00Z", "In Review", "In Progress"), move("2026-10-06T00:00:00Z", "In Progress", "In Review")],
            "MKT-10": [{"created": "2026-10-02T00:00:00Z", "items": [
                {"field": "description"}, {"field": "Attachment"}]},
                {"created": "2026-10-03T00:00:00Z", "items": [{"field": "description"}, {"field": "summary"}]}],
        })
        self.m = metrics(self.acli, self.cl)
        self.m.now = g.parse_dt("2026-11-01T00:00:00Z")

    def test_m1_completion(self):
        r = self.m.m1()["cohorts"]
        gen, other = r["gen-e2"], r["other"]
        self.assertEqual((gen["created"], gen["done"], gen["review"], gen["open"]), (4, 2, 1, 1))
        self.assertEqual((gen["pct_done"], gen["pct_done_or_review"]), (50.0, 75.0))
        self.assertEqual((other["created"], other["done"], other["review"], other["open"]), (3, 1, 0, 2))
        self.assertEqual((other["pct_done"], other["pct_done_or_review"]), (33.3, 33.3))
        self.assertTrue(any('created >= "2026-10-01"' in j and 'created < "2026-11-01"' in j for j in self.acli.seen))

    def test_m1_lead_time(self):
        r = self.m.m1()["cohorts"]
        self.assertEqual(r["gen-e2"]["to_done"], {"n": 2, "avg": 3.0, "median": 3.0})
        self.assertEqual(r["other"]["to_done"]["avg"], 10.0)

    def test_m1_creation_to_review(self):
        r = self.m.m1()["cohorts"]
        # MKT-2: 1 day (now Done), MKT-4: 3 days (still In Review)
        self.assertEqual(r["gen-e2"]["to_review"], {"n": 2, "avg": 2.0, "median": 2.0, "pct_reached": 50.0})
        self.assertEqual(r["other"]["to_review"]["n"], 0)

    def test_m1_open_stories(self):
        o = self.m.m1()["cohorts"]["other"]["open_stories"]
        self.assertEqual((o["n"], o["avg"], o["median"], o["oldest"]), (2, 7.0, 7.0, 12.0))  # MKT-7: 12 days, MKT-8: 2
        self.assertEqual(o["by_status"], {"To Do": 2})
        self.assertEqual([s["key"] for s in o["stories"]], ["MKT-7", "MKT-8"])  # oldest first
        self.assertEqual(self.m.m1()["cohorts"]["gen-e2"]["open_stories"]["by_status"], {"In Progress": 1})

    def test_m1_state_uses_status_category(self):
        done = {"status": {"name": "Closed", "statusCategory": {"key": "done"}}}
        review = {"status": {"name": "in review", "statusCategory": {"key": "indeterminate"}}}
        wip = {"status": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}}, "resolutiondate": "x"}
        self.assertEqual([self.m.story_state(f) for f in (done, review, wip)], ["done", "review", "open"])

    def test_m1_without_history_keeps_counts(self):
        cl = FakeChangelog({})
        cl.available, cl.missing = False, ["ATLASSIAN_TOKEN"]
        m = metrics(self.acli, cl)
        r = m.m1()["cohorts"]["gen-e2"]
        self.assertIsNone(r["to_review"])
        self.assertEqual((r["done"], r["pct_done_or_review"]), (2, 75.0))
        self.assertTrue(any("creation → Review times skipped" in n for n in m.notes))

    def test_review_tables_skipped_without_review_status(self):
        self.m.review = []
        self.assertIsNone(self.m.m1()["cohorts"]["gen-e2"]["to_review"])
        self.assertIsNone(self.m.m2()["review"])
        self.assertTrue(any("--review-status" in n for n in self.m.notes))

    def test_m2_reviewed_population_unchanged(self):
        r = self.m.m2()["review"]
        self.assertEqual(r["other"]["excluded"], 1)  # MKT-5 first reviewed in Sept

    def test_m2_in_progress_to_done(self):
        r = self.m.m2()["done"]
        self.assertEqual(r["gen-e2"]["n"], 2)
        self.assertEqual(r["gen-e2"]["avg"], 1.5)  # MKT-1: Oct 3 -> 5, MKT-2: Oct 2 (In Review) -> 3
        self.assertEqual(r["other"]["excluded"], 1)

    def test_m2_in_progress_to_review(self):
        r = self.m.m2()["review"]
        # MKT-4: In Progress Oct 2 -> In Review Oct 4; MKT-2 went To Do -> In Review (no pre-review work status)
        self.assertEqual((r["gen-e2"]["n"], r["gen-e2"]["avg"], r["gen-e2"]["excluded"]), (1, 2.0, 1))

    def active_setup(self):
        p = lambda k: {"parent": {"key": k}}
        def story(key, status, parent=None, done=None):
            i = issue(key, "2026-09-01T00:00:00Z", status=status, done=done)
            i["fields"].update(p(parent) if parent else {})
            return i
        stories = [
            story("MKT-101", "In Progress", "MKT-50"),              # In Progress since September: active
            story("MKT-102", "Done", "MKT-50", "2026-10-06T00:00:00Z"),  # worked and done in October: active
            story("MKT-103", "To Do", "MKT-60"),                    # only edited in October: not active
            story("MKT-104", "Done", "MKT-70", "2026-10-10T00:00:00Z"),  # straight to Done in October: active
            story("MKT-105", "In Progress"),                        # active, no epic
            story("MKT-106", "Done", "MKT-80", "2026-09-28T00:00:00Z"),  # finished before the period: not active
        ]
        self.cl.data.update({
            "MKT-101": [move("2026-09-20T00:00:00Z", "To Do", "In Progress")],
            "MKT-102": [move("2026-10-05T00:00:00Z", "To Do", "In Progress"), move("2026-10-06T00:00:00Z", "In Progress", "Done")],
            "MKT-103": [move("2026-09-05T00:00:00Z", "To Do", "In Progress"), move("2026-09-15T00:00:00Z", "In Progress", "To Do")],
            "MKT-104": [move("2026-10-10T00:00:00Z", "To Do", "Done")],
            "MKT-105": [move("2026-10-02T00:00:00Z", "To Do", "In Progress")],
            "MKT-106": [move("2026-09-20T00:00:00Z", "To Do", "In Progress"), move("2026-09-28T00:00:00Z", "In Progress", "Done")],
        })
        epics = [issue("MKT-50", "2026-08-01T00:00:00Z", status="In Progress", itype="Epic", labels=["AISDLC"]),
                 issue("MKT-70", "2026-08-01T00:00:00Z", status="In Progress", itype="Epic")]
        self.acli.routes[:0] = [(('OR statusCategory = "In Progress"',), stories), (("key in (",), epics)]

    def test_m13_epics_with_active_stories(self):
        self.active_setup()
        r = self.m.m13()
        self.assertEqual((r["gen-e2"], r["other"], r["total"]), (1, 1, 2))
        self.assertEqual(r["active_stories"], {"gen-e2": 2, "other": 1})
        self.assertEqual(r["active_stories_without_epic"], 1)
        lookup = next(j for j in self.acli.seen if "key in (" in j)
        self.assertIn('"MKT-50"', lookup)
        self.assertNotIn('"MKT-60"', lookup)  # its only story wasn't active
        self.assertNotIn('"MKT-80"', lookup)

    def test_m13_approximate_without_history(self):
        self.active_setup()
        self.cl.available, self.cl.missing = False, ["ATLASSIAN_TOKEN"]
        r = self.m.m13()
        self.assertEqual(r["active_stories_without_epic"], 1)
        self.assertTrue(any("Metric 13 is approximate" in n for n in self.m.notes))

    def test_m13_render(self):
        self.active_setup()
        md = g.render_markdown({"from": "2026-10-01", "to": "2026-10-31", "projects": ["MKT"], "label": "AISDLC",
                                "todo_statuses": ["To Do"], "in_progress_statuses": ["In Progress"],
                                "review_statuses": ["In Review"], "generated": "now"},
                               {"13": self.m.m13()}, self.m.jql, self.m.notes)
        self.assertIn("## 13. Epics with active stories in the period (gen-e2 vs not)", md)
        self.assertIn("| gen-e2 | 1 | 2 |", md)
        self.assertIn("Active stories with no epic: 1.", md)

    def test_raw_data(self):
        import json
        self.cl.cache = self.cl.data
        self.cl.data["MKT-10"].append({"created": "2026-10-04T00:00:00Z", "items": [
            {"field": "description", "fromString": "BRD v1 secret text", "toString": "BRD v2 longer secret text"}]})
        results = self.m.run(["2", "14", "16"])
        raw = g.raw_data(self.m, {"from": "2026-10-01"}, results)
        json.dumps(raw, default=str)  # serialisable
        done = next(x for x in raw["searches"] if {"metric": "2", "label": "gen-e2"} in x["used_by"])
        self.assertEqual(sorted(done["keys"]), ["MKT-1", "MKT-2"])
        self.assertEqual(next(x for x in raw["searches"]
                              if {"metric": "14", "label": "all stories"} in x["used_by"])["count"], 16)
        self.assertEqual(raw["issues"]["MKT-1"]["labels"], ["AISDLC"])
        self.assertEqual(raw["histories"]["MKT-1"][0], {"at": "2026-10-02T00:00:00Z", "field": "status",
                                                       "from": "Backlog", "to": "To Do"})
        desc = [c for c in raw["histories"]["MKT-10"] if c["field"] == "description"][-1]
        self.assertEqual(desc, {"at": "2026-10-04T00:00:00Z", "field": "description", "from_length": 18, "to_length": 25})
        self.assertNotIn("secret", json.dumps(raw, default=str))  # description text is never copied

    def test_done_population_uses_resolution_date(self):
        self.m.m2()
        jql = next(j for j in self.acli.seen if "statusCategory = Done" in j)
        self.assertIn('resolved >= "2026-10-01"', jql)
        self.assertIn("resolution is EMPTY AND statusCategoryChangedDate", jql)

    def test_m14_pct(self):
        self.assertEqual(self.m.m14(), {"total": 16, "gen-e2": 4, "pct": 25.0})

    def test_m15_first_story_in_todo(self):
        r = self.m.m15()
        self.assertEqual(r["gen-e2"]["avg"], 1.5)  # MKT-12 created in To Do at Oct 2 12:00
        self.assertEqual(r["other"]["epics_without_story_in_todo"], 1)
        parent_searches = [j for j in self.acli.seen if "parent in (" in j]
        self.assertEqual(len(parent_searches), 2)  # one batched search per cohort, not one per epic

    def test_one_story_batch_and_one_epic_batch(self):
        self.m.run(["2", "15", "16"])
        self.assertEqual(len(self.cl.prefetched), 2)
        stories, epics = self.cl.prefetched
        self.assertEqual(sorted(stories), ["MKT-1", "MKT-11", "MKT-12", "MKT-2", "MKT-3", "MKT-4", "MKT-5"])  # deduped
        self.assertEqual(sorted(epics), ["MKT-10", "MKT-20"])

    def test_no_history_fetch_for_count_only_metrics(self):
        self.m.run(["13", "14"])
        self.assertEqual(self.cl.prefetched, [])

    def test_m1_prefetches_created_stories(self):
        self.m.run(["1"])
        self.assertEqual(sorted(self.cl.prefetched[0]), ["MKT-1", "MKT-2", "MKT-3", "MKT-4", "MKT-6", "MKT-7", "MKT-8"])

    def test_children_batched_in_chunks(self):
        epics = [issue(f"MKT-{n}", "2026-10-01T00:00:00Z", itype="Epic") for n in range(g.PARENT_CHUNK + 1)]
        self.m.children_of(epics)
        self.assertEqual(sum("parent in (" in j for j in self.acli.seen), 2)

    def test_m16_rework(self):
        r = self.m.m16()["gen-e2"]
        self.assertEqual((r["description_edits"], r["attachment_changes"], r["avg_edits_per_epic"]), (2, 1, 3))
        self.assertEqual(r["pct_epics_reworked"], 100.0)

    def test_changelog_missing_skips(self):
        cl = FakeChangelog({})
        cl.available, cl.missing = False, ["ATLASSIAN_TOKEN"]
        m = metrics(self.acli, cl)
        res = m.run(["2", "14"])
        self.assertIsNone(res["2"])
        self.assertEqual(res["14"]["pct"], 25.0)
        self.assertIn("ATLASSIAN_TOKEN", m.notes[0])

    def test_markdown_renders(self):
        res = self.m.run(list(g.ALL_METRICS))
        meta = {"from": "2026-10-01", "to": "2026-10-31", "projects": ["MKT"], "label": "AISDLC",
                "todo_statuses": ["To Do"], "in_progress_statuses": ["In Progress"],
                "generated": "now"}
        md = g.render_markdown(meta, res, self.m.jql, self.m.notes)
        self.assertIn("| gen-e2 | 4 | 2 | 1 | 1 | 50.0% | 75.0% |", md)
        self.assertIn("| gen-e2 | 2 | 3.0 | 3.0 |", md)
        self.assertIn("| gen-e2 | 2 | 50.0% | 2.0 | 2.0 |", md)
        self.assertIn("| other | 2 | 7.0 | 7.0 | 12.0 | To Do 2 |", md)
        self.assertIn("| MKT-7 | To Do | 12.0 |", md)
        self.assertIn("### Creation → Review", md)
        self.assertIn("### In Progress → Done", md)
        self.assertIn("| 16 | 4 | 25.0% |", md)
        self.assertIn("## JQL used", md)


class BitbucketDefaultTest(unittest.TestCase):
    def test_on_when_token_set_unless_overridden(self):
        old = os.environ.pop("BITBUCKET_TOKEN", None)
        try:
            notes = []
            self.assertFalse(g.bitbucket_enabled(None, notes))
            self.assertIn("no BITBUCKET_TOKEN", notes[0])
            os.environ["BITBUCKET_TOKEN"] = "t"
            self.assertTrue(g.bitbucket_enabled(None, []))
            self.assertFalse(g.bitbucket_enabled(False, []))  # --no-bitbucket
            del os.environ["BITBUCKET_TOKEN"]
            self.assertTrue(g.bitbucket_enabled(True, []))     # --bitbucket without a token: fails later with a clear note
        finally:
            os.environ.pop("BITBUCKET_TOKEN", None)
            if old is not None:
                os.environ["BITBUCKET_TOKEN"] = old


class ParseReposTest(unittest.TestCase):
    def test_parse_repos(self):
        self.assertEqual(g.parse_repos(["acme/api, acme/web/", "", "bad", "acme/docs"]),
                         [{"workspace": "acme", "slug": "api"}, {"workspace": "acme", "slug": "web"},
                          {"workspace": "acme", "slug": "docs"}])


class PseudonymTest(unittest.TestCase):
    def test_stable_and_nameless(self):
        self.assertEqual(g.pseudonym("Alice Tan"), g.pseudonym(" alice tan "))
        self.assertNotEqual(g.pseudonym("Alice Tan"), g.pseudonym("Ben Lim"))
        self.assertEqual(g.pseudonym(None), "unknown")
        links = g.anonymised_links({"MKT-1": {"commits": [{"id": "c1", "author": "Alice Tan"}], "prs": []}})
        self.assertEqual(links["MKT-1"]["commits"][0]["author"], g.pseudonym("Alice Tan"))


class StatusMatchingTest(unittest.TestCase):
    def wf(self, story, epic):
        return {"story": [{"name": n, "category": c} for n, c in story],
                "epic": [{"name": n, "category": c} for n, c in epic]}

    def test_standard_workflow(self):
        s = g.suggest_statuses(self.wf([("Backlog", "new"), ("To Do", "new"), ("In Progress", "indeterminate"),
                                        ("Done", "done")],
                                       [("To Do", "new"), ("In Progress", "indeterminate"), ("Done", "done")]))
        self.assertEqual((s["todo_status"], s["in_progress_status"]), (["To Do"], ["In Progress"]))
        self.assertNotIn("started_status", s)

    def test_custom_names(self):
        s = g.suggest_statuses(self.wf([("Backlog", "new"), ("Selected for Development", "new"),
                                        ("Code Review", "indeterminate")],
                                       [("Funnel", "new"), ("Analysis", "indeterminate"),
                                        ("In Development", "indeterminate")]))
        self.assertEqual(s["todo_status"], ["Selected for Development"])
        self.assertEqual(s["in_progress_status"], ["Code Review"])
        self.assertEqual(s["review_status"], ["Code Review"])

    def test_non_backlog_fallback_and_all_active(self):
        s = g.suggest_statuses(self.wf([("Backlog", "new"), ("Planned", "new")],
                                       [("Analysis", "indeterminate"), ("Build", "indeterminate")]))
        self.assertEqual(s["todo_status"], ["Planned"])

    def test_empty_workflow_defaults(self):
        s = g.suggest_statuses(self.wf([], []))
        self.assertEqual((s["todo_status"], s["in_progress_status"]), (["To Do"], ["In Progress"]))

    def test_discover_via_rest(self):
        class Rest:
            available = True

            def get_json(self, path):
                return [{"name": "Story", "statuses": [
                            {"name": "To Do", "statusCategory": {"key": "new"}}]},
                        {"name": "Epic", "statuses": [
                            {"name": "In Progress", "statusCategory": {"key": "indeterminate"}}]},
                        {"name": "Bug", "statuses": [{"name": "Triage", "statusCategory": {"key": "new"}}]}]
        d = g.discover_statuses(Rest(), None, ["MKT"], "Story", "Epic")
        self.assertEqual(d["story"], [{"name": "To Do", "category": "new"}])
        self.assertEqual(d["epic"], [{"name": "In Progress", "category": "indeterminate"}])

    def test_discover_via_acli_when_no_rest(self):
        class Rest:
            available = False

        class A:
            def run(self, *args):
                return json.dumps([{"key": "MKT-1", "fields": {"status": {
                    "name": "Ready", "statusCategory": {"key": "new"}}}}])
        d = g.discover_statuses(Rest(), A(), ["MKT"], "Story", "Epic")
        self.assertIn("acli", d["source"])
        self.assertEqual(g.suggest_statuses(d)["todo_status"], ["Ready"])


class AcliSubprocessTest(unittest.TestCase):
    def test_search_and_count_via_fake_binary(self):
        script = textwrap.dedent("""\
            #!/usr/bin/env python3
            import json, sys
            a = sys.argv[1:]
            if "--count" in a:
                print("Number of work items: 7")
            else:
                print(json.dumps([{"key": "MKT-1", "fields": {"created": "2026-10-01T00:00:00.000+0800"}}]))
            """)
        with tempfile.TemporaryDirectory() as d:
            exe = os.path.join(d, "acli")
            with open(exe, "w") as f:
                f.write(script)
            os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
            a = g.Acli(exe)
            self.assertEqual(a.count("project = MKT"), 7)
            self.assertEqual(a.search("project = MKT")[0]["key"], "MKT-1")

    def fake_acli(self, d, body):
        exe = os.path.join(d, "acli")
        with open(exe, "w") as f:
            f.write("#!/usr/bin/env python3\nimport json, os, sys\nSTATE = " + repr(os.path.join(d, "n")) + "\n" + body)
        os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
        return exe

class BulkChangelogTest(unittest.TestCase):
    def make(self, pages):
        cl = g.Changelog.__new__(g.Changelog)
        cl.cache, cl.debug, cl.fallback_reason, cl.bodies = {}, False, None, []

        def post(path, body):
            cl.bodies.append(("POST", body))
            page = pages.pop(0)
            if isinstance(page, Exception):
                raise page
            return page

        def get(path):
            cl.bodies.append(("GET", path))
            return pages.pop(0)
        cl._post, cl._get = post, get
        return cl

    def test_bulk_maps_ids_paginates_and_sorts(self):
        cl = self.make([
            {"issueChangeLogs": [{"issueId": "101", "changeHistories": [
                {"created": 1759366800000, "items": [{"field": "status", "fromString": "To Do", "toString": "Done"}]}]}],
             "nextPageToken": "t2"},
            {"issueChangeLogs": [{"issueId": "101", "changeHistories": [
                {"created": 1759280400000, "items": [{"field": "status", "fromString": "Backlog", "toString": "To Do"}]}]}]},
        ])
        cl.prefetch([{"key": "MKT-1", "id": "101"}, {"key": "MKT-2", "id": "102"}])
        self.assertNotIn("fieldIds", cl.bodies[0][1])  # imported history has no field IDs
        self.assertEqual(cl.bodies[1][1]["nextPageToken"], "t2")
        hist = cl.get("MKT-1")
        self.assertEqual([h["items"][0]["toString"] for h in hist], ["To Do", "Done"])
        self.assertIsNotNone(g.parse_dt(hist[0]["created"]))
        self.assertEqual(cl.get("MKT-2"), [])
        self.assertEqual(len(cl.bodies), 2)  # no per-issue calls

    def test_falls_back_to_per_issue_when_bulk_fails(self):
        cl = self.make([g.JiraError("HTTP 404"), {"values": [], "isLast": True}])
        cl.prefetch([{"key": "MKT-1", "id": "101"}])
        self.assertIn("404", cl.fallback_reason)
        self.assertEqual(cl.get("MKT-1"), [])
        self.assertEqual(cl.bodies[-1][0], "GET")

    def test_issues_without_id_use_per_issue(self):
        cl = self.make([{"values": [], "isLast": True}])
        cl.prefetch([{"key": "MKT-1", "id": None}])
        self.assertEqual(cl.bodies, [])
        cl.get("MKT-1")
        self.assertEqual(cl.bodies[0][0], "GET")

    def test_epoch_to_iso(self):
        self.assertEqual(g.parse_dt(g.epoch_to_iso(1759280400)), g.parse_dt(g.epoch_to_iso(1759280400000)))
        self.assertEqual(g.epoch_to_iso("2026-10-01T00:00:00Z"), "2026-10-01T00:00:00Z")

    def test_rest_search_paginates_with_dates_and_ids(self):
        cl = self.make([
            {"issues": [{"id": "1", "key": "MKT-1", "fields": {"created": "c1", "parent": {"key": "MKT-9"}}}],
             "nextPageToken": "p2"},
            {"issues": [{"id": "2", "key": "MKT-2", "fields": {"created": "c2"}}], "isLast": True},
        ])
        out = cl.search("project = MKT")
        self.assertEqual([(i["key"], i["id"]) for i in out], [("MKT-1", "1"), ("MKT-2", "2")])
        self.assertIn("created", cl.bodies[0][1]["fields"])
        self.assertEqual(cl.bodies[1][1]["nextPageToken"], "p2")
        cl.search("project = MKT")
        self.assertEqual(len(cl.bodies), 2)  # cached


class ProjectsTest(unittest.TestCase):
    def test_acli_identity(self):
        out = "✓ Authenticated\n  Site: x-team.atlassian.net\n  Email: me@x.com\n  Authentication Type: api_token"
        self.assertEqual(g.acli_identity(out), ("https://x-team.atlassian.net", "me@x.com"))
        self.assertEqual(g.acli_identity("not logged in"), (None, None))

    def test_jira_token_alias(self):
        old = {k: os.environ.pop(k, None) for k in ("ATLASSIAN_TOKEN", "JIRA_TOKEN")}
        try:
            os.environ["JIRA_TOKEN"] = "t"
            self.assertEqual(g.cfg("ATLASSIAN_TOKEN"), "t")
        finally:
            os.environ.pop("JIRA_TOKEN", None)
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v

    def test_acli_view_fallback_adds_dates(self):
        body = textwrap.dedent("""\
            a = sys.argv[1:]
            if a[1:3] == ["workitem", "search"]:
                assert "created" not in a[a.index("--fields") + 1]
                print(json.dumps([{"id": "7", "key": "MKT-1", "fields": {"status": {"name": "Done"}}}]))
            else:
                print(json.dumps({"key": "MKT-1", "fields": {"created": "2026-10-01T00:00:00.000+0800",
                                                            "parent": {"key": "MKT-9"}}}))
            """)
        with tempfile.TemporaryDirectory() as d:
            a = g.Acli(AcliSubprocessTest.fake_acli(None, d, body))
            out = a.search_with_dates("project = MKT")
        self.assertEqual(out[0]["fields"]["parent"], {"key": "MKT-9"})
        self.assertEqual(out[0]["fields"]["status"], {"name": "Done"})
        self.assertEqual(out[0]["id"], "7")
    def args(self, **kw):
        return type("A", (), {"project": None, "all_projects": False, **kw})()

    def test_resolve_projects(self):
        os.environ.pop("ATLASSIAN_PROJECT", None)
        self.assertEqual(g.resolve_projects(self.args(project=["mkt,ops", "WEB"])), ["MKT", "OPS", "WEB"])
        self.assertEqual(g.resolve_projects(self.args(all_projects=True)), [])
        with self.assertRaises(SystemExit):
            g.resolve_projects(self.args())

    def test_parse_projects(self):
        self.assertEqual(g.parse_projects({"values": [{"key": "MKT", "name": "Marketing"}, {"name": "no key"}]}),
                         [{"key": "MKT", "name": "Marketing"}])

    def test_projects_command_ranks_by_label_use(self):
        body = textwrap.dedent("""\
            a = sys.argv[1:]
            if a[1:3] == ["project", "list"]:
                print(json.dumps([{"key": "ABC", "name": "Alpha"}, {"key": "MKT", "name": "Marketing"}]))
            else:
                print(json.dumps([{"key": "MKT-1"}, {"key": "MKT-2"}]))
            """)
        with tempfile.TemporaryDirectory() as d:
            os.environ["ACLI_PATH"] = AcliSubprocessTest.fake_acli(None, d, body)
            try:
                from io import StringIO
                from contextlib import redirect_stdout
                buf = StringIO()
                with redirect_stdout(buf):
                    g.projects_cmd(type("A", (), {"label": "AISDLC", "days": 180, "debug": False})())
            finally:
                os.environ.pop("ACLI_PATH")
        out = json.loads(buf.getvalue())
        self.assertEqual([p["key"] for p in out["projects"]], ["MKT", "ABC"])
        self.assertEqual(out["projects"][0]["labelled_issues_sampled"], 2)


if __name__ == "__main__":
    unittest.main()
