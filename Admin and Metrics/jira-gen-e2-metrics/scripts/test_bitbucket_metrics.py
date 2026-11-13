import json
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import bitbucket_metrics as bm  # noqa: E402
import code_metrics as cm  # noqa: E402
import gen_e2_metrics as g  # noqa: E402
from test_code_metrics import FakeRest  # noqa: E402
from test_gen_e2_metrics import GEN, OTHER, FakeAcli, FakeChangelog, issue  # noqa: E402

TZ = timezone(timedelta(hours=8))
DIFF_TICKS = """diff --git a/docs/stories/01-x.md b/docs/stories/01-x.md
--- a/docs/stories/01-x.md
+++ b/docs/stories/01-x.md
@@ -40,4 +40,5 @@ Tasks
-- [ ] T-01 [Depends on: None] Add tooling.
+- [x] T-01 [Depends on: None] Add tooling.
-- [ ] T-02 [Depends on: T-01] Integrate sign-in
+- [x] T-02 [Depends on: T-01] Integrate sign-in with SSO.
+- [ ] T-03 [Depends on: T-02] Add the denied page.
 - [ ] T-04 [Depends on: T-03] Unchanged context line.
"""
DIFF_PLAN_ADDED = """--- a/docs/stories/02-y.md
+++ b/docs/stories/02-y.md
@@ -10,0 +11,4 @@
+## Implementation Plan
+- [ ] T-01 [Depends on: None] First.
+- [ ] T-02 [Depends on: T-01] Second.
+Some prose with [x] inside that is not a task.
"""


class ParsingTest(unittest.TestCase):
    def test_ticks_matched_by_task_id_even_if_text_changed(self):
        self.assertEqual(bm.task_changes(DIFF_TICKS), {"added": 1, "removed": 0, "ticked": 2, "unticked": 0})

    def test_plan_added(self):
        self.assertEqual(bm.task_changes(DIFF_PLAN_ADDED), {"added": 2, "removed": 0, "ticked": 0, "unticked": 0})

    def test_untick_and_non_story_text(self):
        d = "-- [x] T-05 Done\n+- [ ] T-05 Done\n+plain line\n"
        self.assertEqual(bm.task_changes(d)["unticked"], 1)
        self.assertEqual(bm.task_changes("+just text\n-other\n"), {"added": 0, "removed": 0, "ticked": 0, "unticked": 0})

    def test_other_id_styles_and_numbered_checkboxes(self):
        d = ("-- [ ] **P1-01 Contracts:** Define PlanDto.\n+- [x] **P1-01 Contracts:** Define the PlanDto type.\n"
             "-1. [ ] 2.1 Wire the API\n+1. [x] 2.1 Wire the API to the screen\n"
             "-* [ ] TASK-3 Add tests\n+* [X] TASK-3 Add tests\n")
        self.assertEqual(bm.analyse(d), ({"added": 0, "removed": 0, "ticked": 3, "unticked": 0}, None))

    def test_reworded_task_without_id_matched_by_similarity(self):
        d = "-- [ ] Add the booking form validation\n+- [x] Add booking form validation\n"
        self.assertEqual(bm.analyse(d)[0]["ticked"], 1)

    def test_unclassifiable_changes_are_flagged(self):
        table = "-| T-01 | Build screen | In progress |\n+| T-01 | Build screen | Done ✅ |\n"
        self.assertEqual(bm.analyse(table)[1], "story file changed without any checklist change")
        swapped = "-- [ ] Build the screen components\n+- [x] Ship it\n"
        self.assertIn("don't match", bm.analyse(swapped)[1])
        self.assertIsNone(bm.analyse(DIFF_TICKS)[1])

    def test_keys_in(self):
        self.assertEqual(bm.keys_in("CSNPBE-2840: fix; also csnpbe-12, ABC-1", ["CSNPBE"]), {"CSNPBE-2840", "CSNPBE-12"})
        self.assertEqual(bm.keys_in("CSNPBE-1", []), set())


class ClientTest(unittest.TestCase):
    def test_commits_window_merges_and_stop(self):
        bb = bm.Bitbucket("me@x.com", "t", sleep=lambda _s: None)
        pages = {
            "/repositories/ws/web/commits?pagelen=100": {"values": [
                {"hash": "a1", "date": "2026-11-20T00:00:00+00:00", "message": "late", "parents": [{}]},
                {"hash": "a0", "date": "2026-10-16T00:00:00+00:00", "message": "no user", "parents": [{}],
                 "author": {"raw": "Ben Lim <ben@x.com>"}},
                {"hash": "a2", "date": "2026-10-15T00:00:00+00:00", "message": "CSNPBE-1 work",
                 "author": {"raw": "Ann <a@x>", "user": {"display_name": "Ann"}}, "parents": [{}]},
                {"hash": "a3", "date": "2026-10-14T00:00:00+00:00", "message": "Merge", "parents": [{}, {}]},
            ], "next": "https://api.bitbucket.org/2.0/p2"},
            "https://api.bitbucket.org/2.0/p2": {"values": [
                {"hash": "a4", "date": "2026-09-01T00:00:00+00:00", "message": "old", "parents": [{}]},
            ], "next": "https://api.bitbucket.org/2.0/p3"},
        }
        bb._request = lambda url, raw=False: pages[url]
        out = bb.commits("ws", "web", datetime(2026, 10, 1, tzinfo=TZ), datetime(2026, 11, 1, tzinfo=TZ))
        self.assertEqual([(c["id"], c["author"]) for c in out], [("a0", "Ben Lim"), ("a2", "Ann")])  # p3 never requested

    def test_probe_reads_granted_scopes_from_403(self):
        import io, urllib.error
        from unittest import mock
        body = b'{"type":"error","error":{"message":"lack scopes","detail":{"required":["read:workspace:bitbucket"],' \
               b'"granted":["read:repository:bitbucket","read:pullrequest:bitbucket"]}}}'
        err = urllib.error.HTTPError("u", 403, "Forbidden", {}, io.BytesIO(body))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            ok, granted, _ = bm.Bitbucket("me@x.com", "t").probe()
        self.assertTrue(ok)
        self.assertIn("read:repository:bitbucket", granted)
        bad = urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=bad):
            self.assertFalse(bm.Bitbucket("me@x.com", "t").probe()[0])

    def test_changed_files_handles_deletes(self):
        bb = bm.Bitbucket("me@x.com", "t")
        bb._request = lambda url, raw=False: {"values": [{"new": {"path": "src/a.ts"}},
                                                         {"new": None, "old": {"path": "docs/stories/old.md"}}]}
        self.assertEqual(bb.changed_files("ws", "web", "abc"), ["src/a.ts", "docs/stories/old.md"])


class FakeBitbucket:
    calls = 0

    def __init__(self, commits, files, diffs, workspaces=("ws",), repos=None):
        self.c, self.files, self.diffs = commits, files, diffs
        self.ws, self.r = list(workspaces), repos or {"ws": [{"workspace": "ws", "slug": "web"}]}
        self.scanned = []

    def workspaces(self):
        return self.ws

    def repos(self, ws, since):
        return self.r.get(ws, [])

    def commits(self, ws, slug, start, end_excl):
        self.scanned.append(f"{ws}/{slug}")
        return [c for c in self.c if c["slug"] == slug]

    def changed_files(self, ws, slug, commit):
        return self.files.get(commit, [])

    def diff(self, ws, slug, commit, path):
        return self.diffs.get((commit, path), "")


def bb_commit(cid, message, author, slug="web"):
    return {"id": cid, "at": datetime(2026, 10, 20, tzinfo=TZ), "message": message, "author": author,
            "workspace": "ws", "slug": slug}


class NoRest:
    available, missing = False, ["ATLASSIAN_TOKEN"]


def metrics(acli):
    return g.Metrics(acli, FakeChangelog({}), ["CSNPBE"], "AISDLC", date(2026, 10, 12), date(2026, 11, 11),
                     ["To Do"], log=lambda _m: None)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.t_gen = [issue("CSNPBE-1", "2026-10-12T00:00:00Z", status="In Progress", labels=["AISDLC"]),
                      issue("CSNPBE-2", "2026-10-12T00:00:00Z", status="Review", labels=["AISDLC"])]
        self.t_other = [issue("CSNPBE-3", "2026-10-12T00:00:00Z", status="Done")]
        self.acli = FakeAcli(routes=[(('issuetype = "Story"', "updated >=", GEN), self.t_gen),
                                     (('issuetype = "Story"', "updated >=", OTHER), self.t_other)], counts=[])
        self.bb = FakeBitbucket(
            commits=[bb_commit("c1", "CSNPBE-1 add plan", "Ann"),
                     bb_commit("c2", "CSNPBE-1 implement T-01, T-02", "Ann"),
                     bb_commit("c3", "CSNPBE-2 and CSNPBE-3 shared fix", "Ben"),
                     bb_commit("c4", "tidy up, no key", "Ben")],
            files={"c1": ["docs/stories/01-x.md"], "c2": ["src/a.ts", "docs/stories/01-x.md"], "c3": ["src/b.ts"]},
            diffs={("c1", "docs/stories/01-x.md"): DIFF_PLAN_ADDED, ("c2", "docs/stories/01-x.md"): DIFF_TICKS})

    def test_scan_finds_commits_and_checks_story_updates(self):
        m = metrics(self.acli)
        r = bm.run(m, self.bb, NoRest(), ["CSNPBE"], [{"workspace": "ws", "slug": "web"}])
        self.assertEqual(r["source"], "scan")
        gen = r["cohorts"]["gen-e2"]
        self.assertEqual((gen["tickets"], gen["with_commits"], gen["commits"]), (2, 2, 3))
        self.assertEqual((gen["commits_story"], gen["commits_tasks"], gen["tickets_tasks"], gen["tasks_ticked"]), (2, 2, 1, 2))
        other = r["cohorts"]["other"]
        self.assertEqual((other["commits"], other["commits_story"]), (1, 0))  # shared commit c3 counts for both tickets
        self.assertEqual(r["unmatched_commits"], 1)
        # Ann (task-list commits on gen-e2 tickets) and Ben (shared commit only): 1 of 2 engineers push gen-e2 commits
        self.assertEqual(r["engineers"], {"total": 2, "gen_e2_commits": 1, "on_gen_e2_tickets": 2,
                                          "on_gen_e2_tickets_with_gen_e2_commits": 1})

    def test_raw_commit_records(self):
        r = bm.run(metrics(self.acli), self.bb, NoRest(), ["CSNPBE"], [{"workspace": "ws", "slug": "web"}])
        by_id = {c["id"]: c for c in r["commits"]}
        self.assertEqual(by_id["c3"]["tickets"], ["CSNPBE-2", "CSNPBE-3"])
        self.assertEqual(by_id["c2"]["tasks"], {"added": 1, "removed": 0, "ticked": 2, "unticked": 0})
        self.assertEqual(by_id["c2"]["story_files"], ["docs/stories/01-x.md"])
        self.assertNotIn("c4", by_id)  # no ticket key
        self.assertEqual(by_id["c1"]["author"], g.pseudonym("Ann"))
        self.assertRegex(by_id["c1"]["author"], r"^engineer-[0-9a-f]{6}$")
        self.assertNotIn("Ann", json.dumps(r, default=str))

    def review_setup(self):
        table = "-| T-01 | Build screen | In progress |\n+| T-01 | Build screen | Done |\n"
        self.bb.c.append(bb_commit("c5", "CSNPBE-2 mark T-01 done", "Ben"))
        self.bb.files["c5"] = ["docs/stories/02-y.md"]
        self.bb.diffs[("c5", "docs/stories/02-y.md")] = table

    def test_pending_review_items(self):
        self.review_setup()
        m = metrics(self.acli)
        r = bm.run(m, self.bb, NoRest(), ["CSNPBE"], [{"workspace": "ws", "slug": "web"}])
        self.assertEqual(len(r["pending_review"]), 1)
        item = r["pending_review"][0]
        self.assertEqual((item["key"], item["tickets"]), ("c5:docs/stories/02-y.md", ["CSNPBE-2"]))
        self.assertEqual(item["author"], g.pseudonym("Ben"))
        self.assertIn("+| T-01 | Build screen | Done |", item["diff_excerpt"])
        self.assertEqual(r["classification"], {"mechanical": 2, "agent review": 0, "pending review": 1})
        self.assertEqual(r["cohorts"]["gen-e2"]["tickets_tasks"], 1)  # CSNPBE-2 not counted until reviewed
        self.assertTrue(any("couldn't be classified" in n for n in m.notes))

    def test_saved_decision_is_applied(self):
        self.review_setup()
        decisions = {"c5:docs/stories/02-y.md": {"task_progress": True, "ticked": 1, "reason": "status table marks T-01 done"}}
        r = bm.run(metrics(self.acli), self.bb, NoRest(), ["CSNPBE"], [{"workspace": "ws", "slug": "web"}],
                   decisions=decisions)
        self.assertEqual(r["pending_review"], [])
        self.assertEqual(r["cohorts"]["gen-e2"]["tickets_tasks"], 2)
        self.assertEqual(r["cohorts"]["gen-e2"]["tasks_ticked"], 3)
        c5 = next(c for c in r["commits"] if c["id"] == "c5")
        self.assertEqual(c5["files"][0]["classified_by"], "agent review")
        self.assertEqual(c5["files"][0]["decision_reason"], "status table marks T-01 done")
        self.assertIn("by agent review: 1; awaiting review: 0", "\n".join(bm.render(r)))

    def test_load_decisions_validates(self):
        import json, tempfile
        notes = []
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"a:x.md": {"task_progress": True, "ticked": 1, "reason": "ok"},
                       "b:y.md": {"task_progress": "yes"}}, f)
        self.assertEqual(list(g.load_decisions(f.name, notes)), ["a:x.md"])
        self.assertIn("1 entries ignored", notes[0])
        os.unlink(f.name)
        self.assertEqual(g.load_decisions("/nonexistent.json", []), {})

    def test_scan_discovers_repositories_when_none_given(self):
        m = metrics(self.acli)
        r = bm.run(m, self.bb, NoRest(), ["CSNPBE"])
        self.assertEqual(r["scanned_repositories"], ["ws/web"])
        self.assertTrue(any("scanned all 1 repositories in ws" in n for n in m.notes))

    def test_configured_workspace_is_scanned_without_listing_workspaces(self):
        self.bb.ws = []  # token can't list workspaces
        self.bb.r = {"acme": [{"workspace": "acme", "slug": "web"}]}
        m = metrics(self.acli)
        r = bm.run(m, self.bb, NoRest(), ["CSNPBE"], workspaces=["acme"])
        self.assertEqual(r["scanned_repositories"], ["acme/web"])
        self.assertEqual(r["cohorts"]["gen-e2"]["commits"], 3)
        self.assertTrue(any("repositories in acme" in n for n in m.notes))

    def test_jira_source_uses_linked_commits_and_repo_url(self):
        tickets = [{**t, "id": str(n)} for n, t in enumerate(self.t_gen + self.t_other, 1)]
        acli = FakeAcli(routes=[(("updated >=", GEN, cm.HAS_CODE), tickets[:1]),
                                (("updated >=", OTHER, cm.HAS_CODE), []),
                                (('issuetype = "Story"', "updated >=", GEN), tickets[:2]),
                                (('issuetype = "Story"', "updated >=", OTHER), tickets[2:])], counts=[])
        rest = FakeRest({("1", "repository"): [{"repositories": [{
            "name": "web", "url": "https://bitbucket.org/ws/web",
            "commits": [{"id": "c2", "authorTimestamp": "2026-10-20T00:00:00.000+0800", "message": "x",
                         "author": {"name": "Ann"}}]}]}]})
        m = metrics(acli)
        r = bm.run(m, self.bb, rest, ["CSNPBE"])
        self.assertEqual(r["source"], "jira")
        self.assertEqual(self.bb.scanned, [])  # no repository scan needed
        self.assertEqual((r["cohorts"]["gen-e2"]["commits"], r["cohorts"]["gen-e2"]["tasks_ticked"]), (1, 2))
        self.assertEqual(r["repositories"], [("ws/web", 1)])

    def test_render(self):
        m = metrics(self.acli)
        r = bm.run(m, self.bb, NoRest(), ["CSNPBE"], [{"workspace": "ws", "slug": "web"}])
        md = "\n".join(bm.render(r))
        self.assertIn("## Bitbucket: commits and gen-e2 story-file updates", md)
        self.assertIn("| gen-e2 | 2 | 2 (100%) | 3 | 2 (67%) | 2 (67%) | 1 (50%) | 1 (50%) | 2 |", md)
        self.assertIn("| With commits on the period's tickets | 2 | 1 | 50% |", md)
        self.assertIn("| Of those, working on gen-e2 tickets | 2 | 1 | 50% |", md)
        self.assertNotIn("Ann", md)
        self.assertNotIn("Ben", md)
        self.assertIn("`ws/web` (3)", md)

    def test_no_commits_note(self):
        m = metrics(self.acli)
        bm.run(m, FakeBitbucket([], {}, {}), NoRest(), ["CSNPBE"], [{"workspace": "ws", "slug": "web"}])
        self.assertTrue(any("no commits found" in n for n in m.notes))


if __name__ == "__main__":
    unittest.main()
