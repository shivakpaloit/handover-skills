"""Code metrics for the gen-e2 report: Bitbucket commits and pull requests linked to Jira stories.

Reads Jira's development information with the same API token as the rest of the report, so no
Bitbucket credentials or repository list are needed. Repositories are discovered from the stories.
Bitbucket must be connected to the Jira site, and commit messages, branch names or PR titles must
mention the ticket key.

Used by `gen_e2_metrics.py report --code`; not run on its own.
"""
import urllib.parse

import gen_e2_metrics as g

DEV_DETAIL = "/rest/dev-status/latest/issue/detail?issueId={id}&applicationType={app}&dataType={dtype}"
HAS_CODE = "development[commits].all > 0"


def to_dt(value):
    return g.parse_dt(g.epoch_to_iso(value))


class DevInfo:
    """Commits, pull requests and repositories linked to one issue, from Jira's development information."""

    def __init__(self, rest, app="bitbucket"):
        self.rest, self.app, self.cache = rest, app, {}

    def _detail(self, issue_id, dtype):
        path = DEV_DETAIL.format(id=urllib.parse.quote(str(issue_id)), app=urllib.parse.quote(self.app), dtype=dtype)
        data = self.rest.get_json(path) or {}
        return data.get("detail") or []

    def get(self, issue):
        key = issue["key"]
        if key in self.cache:
            return self.cache[key]
        if not issue.get("id"):
            raise g.JiraError(f"{key}: no issue id; code metrics need the REST search (set the API token)")
        commits, prs, repos = {}, {}, {}
        for det in self._detail(issue["id"], "repository"):
            for repo in det.get("repositories") or []:
                name = repo.get("name") or "?"
                repos.setdefault(name, repo.get("url"))
                for c in repo.get("commits") or []:
                    cid = c.get("id") or c.get("displayId")
                    if cid and not c.get("merge"):
                        author = c.get("author") or {}
                        commits[cid] = {"id": cid, "at": to_dt(c.get("authorTimestamp")), "repo": name,
                                        "repo_url": repo.get("url"), "message": c.get("message") or "",
                                        "author": author.get("name") or author.get("displayName") or "unknown"}
        for det in self._detail(issue["id"], "pullrequest"):
            for pr in det.get("pullRequests") or []:
                repo = pr.get("repositoryName") or "?"
                if pr.get("repositoryName"):
                    repos.setdefault(repo, pr.get("repositoryUrl"))
                pid = f"{repo}{pr.get('id') or pr.get('url')}"
                prs[pid] = {"status": (pr.get("status") or "").upper(), "updated": to_dt(pr.get("lastUpdate")),
                            "repo": repo}
        self.cache[key] = {"commits": list(commits.values()), "prs": list(prs.values()), "repos": repos}
        return self.cache[key]


def run(m, dev):
    """Compute code metrics for the Done stories of each cohort in the report period."""
    stories = {}
    traceability = {}
    for c in g.COHORTS:
        done = m.done_stories("code", c)
        linked = m.find(m.remember("code", f"{c}, with linked commits", m.done_jql(c, HAS_CODE)))
        stories[c] = linked
        traceability[c] = {"done": len(done), "with_code": len(linked),
                           "pct": round(100 * len(linked) / len(done), 1) if done else None}
    everything = [i for c in g.COHORTS for i in stories[c]]
    if m.cl.available and hasattr(m.cl, "prefetch"):
        m.cl.prefetch(everything)
    m.log(f"code: reading development information for {len(everything)} stories")
    info = {i["key"]: dev.get(i) for i in everything}

    owners = {}
    for key, d in info.items():
        for cm in d["commits"]:
            owners.setdefault(cm["id"], set()).add(key)

    out = {"traceability": traceability}
    pickup, coding, closing, volume = {}, {}, {}, {}
    repos = {}
    for c in g.COHORTS:
        p_vals, before_start = [], 0
        c_vals, no_merge = [], 0
        d_vals, closed_first = [], 0
        weighted, pr_counts, shared, total_commits, declined, post_done = [], [], 0, 0, 0, 0
        for i in stories[c]:
            d, f = info[i["key"]], i["fields"]
            times = sorted(cm["at"] for cm in d["commits"] if cm["at"])
            first = times[0] if times else None
            merged = [pr["updated"] for pr in d["prs"] if pr["status"] == "MERGED" and pr["updated"]]
            merge = max(merged) if merged else None
            finished = g.done_at(f)
            started = m.work_started_at(i)

            if first and started:
                p_vals.append(g.days_between(started, first))
                before_start += first < started
            if first and merge:
                c_vals.append(g.days_between(first, merge))
            elif first:
                no_merge += 1
            if merge and finished:
                d_vals.append(g.days_between(merge, finished))
                closed_first += finished < merge

            weighted.append(sum(1 / len(owners[cm["id"]]) for cm in d["commits"]))
            pr_counts.append(len(d["prs"]))
            total_commits += len(d["commits"])
            shared += sum(1 for cm in d["commits"] if len(owners[cm["id"]]) > 1)
            declined += sum(1 for pr in d["prs"] if pr["status"] == "DECLINED")
            post_done += bool(finished and any(t > finished for t in times))
            for name, url in d["repos"].items():
                r = repos.setdefault(name, {"repository": name, "url": url, "stories": 0, "gen-e2": 0, "other": 0})
                r["stories"] += 1
                r[c] += 1
        pickup[c] = {**g.summarize(p_vals), "before_in_progress": before_start}
        coding[c] = {**g.summarize(c_vals), "no_merged_pr": no_merge}
        closing[c] = {**g.summarize(d_vals), "closed_before_merge": closed_first}
        n = len(stories[c])
        volume[c] = {
            "stories": n,
            "commits_per_story": round(sum(weighted) / n, 2) if n else None,
            "prs_per_story": round(sum(pr_counts) / n, 2) if n else None,
            "pct_shared_commits": round(100 * shared / total_commits, 1) if total_commits else None,
            "declined_prs": declined,
            "stories_with_commits_after_done": post_done,
        }
    out.update({"pickup": pickup, "commit_to_merge": coding, "merge_to_done": closing, "volume": volume,
                "repositories": sorted(repos.values(), key=lambda r: (-r["stories"], r["repository"]))})
    if not any(traceability[c]["with_code"] for c in g.COHORTS):
        m.notes.append("Code metrics: no Done story has linked commits. Check that Bitbucket is connected to this "
                       "Jira site and that commit messages, branch names or PR titles include the ticket key.")
    return out


def render(r):
    L = ["## Code (Bitbucket, via Jira development information)", "", "### Done stories with linked code", "",
         "| Cohort | Done stories | With linked commits | % |", "|---|---|---|---|"]
    for c in g.COHORTS:
        t = r["traceability"][c]
        L.append(f"| {c} | {t['done']} | {t['with_code']} | {g.fmt(t['pct'], '%')} |")
    if not any(r["traceability"][c]["with_code"] for c in g.COHORTS):
        return L + ["", "No linked code found, so the other code metrics are empty (see Notes).", ""]
    L += ["", "### In Progress → first commit", ""]
    L += g.duration_table(r["pickup"], ("before_in_progress", "Committed before In Progress"))
    L += ["", "### First commit → PR merged", ""]
    L += g.duration_table(r["commit_to_merge"], ("no_merged_pr", "No merged PR"))
    L += ["", "### PR merged → story Done", ""]
    L += g.duration_table(r["merge_to_done"], ("closed_before_merge", "Closed before merge"))
    L += ["", "### Commits and pull requests", "",
          "| Cohort | Stories | Commits per story | PRs per story | % shared commits | Declined PRs | Stories with commits after Done |",
          "|---|---|---|---|---|---|---|"]
    for c in g.COHORTS:
        v = r["volume"][c]
        L.append(f"| {c} | {v['stories']} | {g.fmt(v['commits_per_story'])} | {g.fmt(v['prs_per_story'])} | "
                 f"{g.fmt(v['pct_shared_commits'], '%')} | {v['declined_prs']} | {v['stories_with_commits_after_done']} |")
    L += ["", "### Repositories found", ""]
    if r["repositories"]:
        L += ["| Repository | Stories | gen-e2 | other |", "|---|---|---|---|"]
        L += [f"| {x['repository']} | {x['stories']} | {x['gen-e2']} | {x['other']} |" for x in r["repositories"]]
    else:
        L.append("None.")
    return L + [""]


DEFINITIONS = [
    "- **Code, population**: Done stories in the period (same as 2 → Done) that have commits linked in Jira's development information.",
    "- **Code, In Progress → first commit**: earliest linked commit's author time minus the first entry into a pre-review In Progress status. Negative when coding started before the ticket was moved.",
    "- **Code, first commit → PR merged**: last merged PR's last-update time (used as the merge time) minus the earliest linked commit.",
    "- **Code, PR merged → story Done**: Done time minus the merge time. Negative when the story was closed before the code merged.",
    "- **Code, commits per story**: merge commits excluded; a commit linked to several stories is split equally between them. % shared = commits linked to more than one story in scope.",
]
