import os
import sys
import unittest
import urllib.parse
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import code_metrics as cm  # noqa: E402
import gen_e2_metrics as g  # noqa: E402
from test_gen_e2_metrics import GEN, OTHER, FakeAcli, FakeChangelog, issue, move  # noqa: E402


def with_id(i, n):
    return {**i, "id": str(n)}


def commit(cid, at, merge=False):
    return {"id": cid, "displayId": cid[:7], "authorTimestamp": at, "merge": merge, "message": f"MKT {cid}"}


def pr(pid, status, updated, repo):
    return {"id": pid, "status": status, "lastUpdate": updated, "repositoryName": repo,
            "repositoryUrl": f"https://bitbucket.org/acme/{repo}"}


class FakeRest:
    """Jira development information keyed by (issue id, dataType)."""
    available, missing = True, []

    def __init__(self, data):
        self.data, self.paths = data, []

    def get_json(self, path):
        self.paths.append(path)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        return {"errors": [], "detail": self.data.get((qs["issueId"][0], qs["dataType"][0]), [])}


def repo_detail(name, commits):
    return [{"repositories": [{"name": name, "url": f"https://bitbucket.org/acme/{name}", "commits": commits}]}]


class CodeMetricsTest(unittest.TestCase):
    def setUp(self):
        s1 = with_id(issue("MKT-1", "2026-10-01T00:00:00Z", done="2026-10-05T00:00:00Z", labels=["AISDLC"]), 1)
        s2 = with_id(issue("MKT-2", "2026-10-01T00:00:00Z", done="2026-10-03T00:00:00Z", labels=["AISDLC"]), 2)
        s3 = with_id(issue("MKT-3", "2026-10-01T00:00:00Z", done="2026-10-11T00:00:00Z"), 3)
        self.acli = FakeAcli(routes=[
            (("statusCategory = Done", cm.HAS_CODE, GEN), [s1, s2]),
            (("statusCategory = Done", cm.HAS_CODE, OTHER), [s3]),
            (("statusCategory = Done", GEN), [s1, s2]),
            (("statusCategory = Done", OTHER), [s3]),
        ], counts=[])
        self.cl = FakeChangelog({
            "MKT-1": [move("2026-10-02T00:00:00Z", "To Do", "In Progress"), move("2026-10-05T00:00:00Z", "In Progress", "Done")],
            "MKT-2": [move("2026-10-01T12:00:00Z", "To Do", "In Progress"), move("2026-10-03T00:00:00Z", "In Progress", "Done")],
            "MKT-3": [move("2026-10-04T00:00:00Z", "To Do", "In Progress"), move("2026-10-11T00:00:00Z", "In Progress", "Done")],
        })
        oct3 = int(datetime(2026, 10, 3, tzinfo=timezone.utc).timestamp() * 1000)  # epoch ms is accepted too
        self.rest = FakeRest({
            ("1", "repository"): repo_detail("web", [commit("c1", "2026-10-02T12:00:00.000+0000"),
                                                     commit("c2", oct3),
                                                     commit("m1", "2026-10-04T00:00:00.000+0000", merge=True)]),
            ("1", "pullrequest"): [{"pullRequests": [pr("#1", "MERGED", "2026-10-04T00:00:00.000+0000", "web")]}],
            ("2", "repository"): repo_detail("web", [commit("c2", oct3), commit("c3", "2026-10-01T00:00:00.000+0000")]),
            ("2", "pullrequest"): [{"pullRequests": [pr("#2", "MERGED", "2026-10-03T12:00:00.000+0000", "web"),
                                                     pr("#3", "DECLINED", "2026-10-02T00:00:00.000+0000", "web")]}],
            ("3", "repository"): repo_detail("api", [commit("c4", "2026-10-05T00:00:00.000+0000"),
                                                     commit("c5", "2026-10-12T00:00:00.000+0000")]),
            ("3", "pullrequest"): [{"pullRequests": [pr("#9", "OPEN", "2026-10-06T00:00:00.000+0000", "api")]}],
        })
        self.m = g.Metrics(self.acli, self.cl, ["MKT"], "AISDLC", date(2026, 10, 1), date(2026, 10, 31),
                           ["To Do"], log=lambda _m: None,
                           in_progress_statuses=["In Progress", "In Review"], review_statuses=["In Review"])
        self.r = cm.run(self.m, cm.DevInfo(self.rest))

    def test_traceability(self):
        self.assertEqual(self.r["traceability"]["gen-e2"], {"done": 2, "with_code": 2, "pct": 100.0})
        self.assertEqual(self.r["traceability"]["other"]["with_code"], 1)
        self.assertTrue(any(cm.HAS_CODE in j for j in self.acli.seen))

    def test_pickup_allows_commits_before_in_progress(self):
        p = self.r["pickup"]["gen-e2"]  # MKT-1: +0.5 days, MKT-2: committed 0.5 days before In Progress
        self.assertEqual((p["n"], p["avg"], p["before_in_progress"]), (2, 0.0, 1))
        self.assertEqual(self.r["pickup"]["other"]["avg"], 1.0)

    def test_commit_to_merge(self):
        self.assertEqual(self.r["commit_to_merge"]["gen-e2"]["avg"], 2.0)  # 1.5 and 2.5 days
        self.assertEqual((self.r["commit_to_merge"]["other"]["n"], self.r["commit_to_merge"]["other"]["no_merged_pr"]), (0, 1))

    def test_merge_to_done_counts_closed_before_merge(self):
        d = self.r["merge_to_done"]["gen-e2"]  # MKT-1: +1 day, MKT-2: closed 0.5 days before its PR merged
        self.assertEqual((d["avg"], d["closed_before_merge"]), (0.25, 1))

    def test_shared_commits_split_and_merge_commits_ignored(self):
        v = self.r["volume"]["gen-e2"]
        self.assertEqual(v["commits_per_story"], 1.5)  # c2 is shared: half to each story; m1 is a merge commit
        self.assertEqual((v["pct_shared_commits"], v["prs_per_story"], v["declined_prs"]), (50.0, 1.5, 1))
        self.assertEqual(self.r["volume"]["other"]["stories_with_commits_after_done"], 1)

    def test_repositories_discovered_from_stories(self):
        self.assertEqual([(x["repository"], x["stories"], x["gen-e2"], x["other"]) for x in self.r["repositories"]],
                         [("web", 2, 2, 0), ("api", 1, 0, 1)])

    def test_two_calls_per_story_and_cached(self):
        self.assertEqual(len(self.rest.paths), 6)
        self.assertIn("applicationType=bitbucket", self.rest.paths[0])

    def test_render_and_jql_listing(self):
        meta = {"from": "2026-10-01", "to": "2026-10-31", "projects": ["MKT"], "label": "AISDLC",
                "todo_statuses": ["To Do"], "in_progress_statuses": ["In Progress"], "review_statuses": ["In Review"],
                "generated": "now"}
        md = g.render_markdown(meta, {}, self.m.jql, self.m.notes, self.r)
        for heading in ("## Code (Bitbucket", "### In Progress → first commit", "### Repositories found"):
            self.assertIn(heading, md)
        self.assertIn("| web | 2 | 2 | 0 |", md)
        self.assertIn("**code** (gen-e2, with linked commits)", md)

    def test_no_linked_code_adds_note(self):
        acli = FakeAcli(routes=[], counts=[])
        m = g.Metrics(acli, FakeChangelog({}), ["MKT"], "AISDLC", date(2026, 10, 1), date(2026, 10, 31),
                      ["To Do"], log=lambda _m: None)
        r = cm.run(m, cm.DevInfo(FakeRest({})))
        self.assertEqual(r["traceability"]["gen-e2"]["with_code"], 0)
        self.assertTrue(any("Bitbucket is connected" in n for n in m.notes))

    def test_issue_without_id_is_an_error(self):
        with self.assertRaises(g.JiraError):
            cm.DevInfo(FakeRest({})).get({"key": "MKT-1", "fields": {}})


if __name__ == "__main__":
    unittest.main()
