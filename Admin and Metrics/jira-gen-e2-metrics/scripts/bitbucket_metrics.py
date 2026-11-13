"""Bitbucket checks for the gen-e2 report: find each ticket's commits, and check whether those commits
update the gen-e2 story file (docs/stories/) and its task list.

Commits are found from Jira's development information when Bitbucket is connected to Jira, or by scanning
chosen Bitbucket repositories for commit messages that mention the ticket key. Commit changes are read from
Bitbucket's API, which needs an API token with Bitbucket scopes (BITBUCKET_TOKEN).

Used by `gen_e2_metrics.py report --bitbucket` and `gen_e2_metrics.py bb-repos`; not run on its own.
"""
import base64
import difflib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import code_metrics as cm
import gen_e2_metrics as g

API = "https://api.bitbucket.org/2.0"
MAX_COMMIT_PAGES = 50  # per repository; commits are listed newest first
# A checklist line: "- [ ] task", "* [x] task", "1. [X] task", "2) [ ] task" (any indentation).
CHECKBOX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[( |x|X)\]\s+(.*\S)\s*$")
# A task ID at the start of the text, optionally in bold: T-01, P1-01, TASK-3, 1.2, 2.3.1.
TASK_ID = re.compile(r"^[*_]*\s*([A-Za-z]{1,6}\d*[-.]\d+(?:\.\d+)*|\d+(?:\.\d+)+)\b")
SIMILAR = 0.8  # wording similarity for matching a reworded task without an ID
EXCERPT_LINES = 60
REPO_URL = re.compile(r"bitbucket\.org/([^/]+)/([^/?#]+)")


class Bitbucket:
    def __init__(self, email, token, debug=False, sleep=time.sleep):
        self.auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        self.debug, self.sleep, self.calls = debug, sleep, 0

    def _request(self, url, raw=False):
        url = url if url.startswith("http") else API + url
        for attempt in range(5):
            if self.debug:
                print(f"+ bitbucket GET {url}", file=sys.stderr)
            self.calls += 1
            req = urllib.request.Request(url, headers={
                "Authorization": self.auth, "Accept": "text/plain" if raw else "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read()
                    return body.decode("utf-8", "replace") if raw else json.loads(body or b"{}")
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 4:
                    self.sleep(float(e.headers.get("Retry-After") or 2 ** (attempt + 1)))
                    continue
                raise g.JiraError(f"Bitbucket GET {url}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")
            except urllib.error.URLError as e:
                raise g.JiraError(f"Bitbucket GET {url}: {e.reason}")
        raise g.JiraError(f"Bitbucket GET {url}: rate limited")

    def paged(self, path, max_pages=None):
        url, pages = path, 0
        while url and (max_pages is None or pages < max_pages):
            page = self._request(url)
            pages += 1
            yield page.get("values", [])
            url = page.get("next")

    def probe(self):
        """Check the token: (ok, granted scopes or None, error). Needs no particular scope: Bitbucket's 403
        response lists the scopes the token was granted."""
        req = urllib.request.Request(API + "/user/workspaces?pagelen=1", headers={"Authorization": self.auth,
                                                                                  "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30):
                return True, None, None
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                granted = json.loads(body)["error"]["detail"]["granted"]
            except (ValueError, KeyError, TypeError):
                granted = None
            return e.code == 403 and granted is not None, granted, f"HTTP {e.code} {body[:200]}"
        except urllib.error.URLError as e:
            return False, None, str(e.reason)

    def workspaces(self):
        try:
            return [(v.get("workspace") or v).get("slug") for page in self.paged("/user/workspaces?pagelen=100")
                    for v in page if (v.get("workspace") or v).get("slug")]
        except g.JiraError as e:
            if "read:workspace" in str(e):
                raise g.JiraError("the token can't list workspaces (no read:workspace scope): set BITBUCKET_WORKSPACE "
                                  "in .env or pass --bb-workspace WORKSPACE, or add the scope to the token")
            raise

    def repos(self, workspace, since):
        q = urllib.parse.quote(f'updated_on >= {since.isoformat()}')
        path = f"/repositories/{urllib.parse.quote(workspace)}?pagelen=100&sort=-updated_on&q={q}"
        return [{"workspace": workspace, "slug": r["slug"], "updated": r.get("updated_on")}
                for page in self.paged(path) for r in page]

    def commits(self, workspace, slug, start, end_excl):
        """Commits on all branches authored in [start, end_excl), newest first, skipping merge commits."""
        path = f"/repositories/{urllib.parse.quote(workspace)}/{urllib.parse.quote(slug)}/commits?pagelen=100"
        out = []
        for page in self.paged(path, MAX_COMMIT_PAGES):
            dated = [(g.parse_dt(c.get("date")), c) for c in page]
            for at, c in dated:
                if at and start <= at < end_excl and len(c.get("parents") or []) < 2:
                    author = c.get("author") or {}
                    raw = re.sub(r"\s*<[^>]*>\s*$", "", author.get("raw") or "").strip()  # "Name <email>" -> "Name"
                    out.append({"id": c["hash"], "at": at, "message": c.get("message") or "",
                                "author": (author.get("user") or {}).get("display_name") or raw or "unknown",
                                "workspace": workspace, "slug": slug})
            if dated and all(at and at < start for at, _ in dated):
                break
        return out

    def changed_files(self, workspace, slug, commit):
        path = f"/repositories/{urllib.parse.quote(workspace)}/{urllib.parse.quote(slug)}/diffstat/{commit}?pagelen=500"
        files = []
        for page in self.paged(path):
            for f in page:
                p = (f.get("new") or {}).get("path") or (f.get("old") or {}).get("path")
                if p:
                    files.append(p)
        return files

    def diff(self, workspace, slug, commit, path):
        q = urllib.parse.quote(path)
        return self._request(f"/repositories/{urllib.parse.quote(workspace)}/{urllib.parse.quote(slug)}/diff/{commit}?path={q}",
                             raw=True)


# ---------- parsing ----------

def keys_in(text, projects):
    if not projects:
        return set()
    pattern = re.compile(r"\b(" + "|".join(re.escape(p) for p in projects) + r")-(\d+)\b", re.I)
    return {f"{p.upper()}-{n}" for p, n in pattern.findall(text or "")}


def changed_lines(diff_text):
    return [l for l in (diff_text or "").splitlines() if l[:1] in ("+", "-") and not l.startswith(("+++", "---"))]


def _tasks(lines):
    """({key: done} removed, {key: done} added, {key: text}) for checklist lines; key = task ID or normalised text."""
    removed, added, text_of = {}, {}, {}
    for line in lines:
        m = CHECKBOX.match(line[1:])
        if not m:
            continue
        text = re.sub(r"\s+", " ", m.group(2)).strip()
        tid = TASK_ID.match(text)
        key = tid.group(1).upper() if tid else text.lower()
        text_of[key] = text.lower()
        (added if line[0] == "+" else removed)[key] = m.group(1).lower() == "x"
    return removed, added, text_of


def analyse(diff_text):
    """Checklist changes in one story file's diff, and why it needs review (None if it doesn't).

    Tasks are paired by ID, then by exact text, then by similar wording (for reworded tasks without an ID).
    """
    lines = changed_lines(diff_text)
    removed, added, text_of = _tasks(lines)
    pairs = [(k, k) for k in added if k in removed]
    left_r = [k for k in removed if k not in added]
    left_a = [k for k in added if k not in removed]
    for a in list(left_a):
        best = max(left_r, key=lambda r: difflib.SequenceMatcher(None, text_of[r], text_of[a]).ratio(), default=None)
        if best is not None and difflib.SequenceMatcher(None, text_of[best], text_of[a]).ratio() >= SIMILAR:
            pairs.append((best, a))
            left_r.remove(best)
            left_a.remove(a)
    counts = {"added": len(left_a), "removed": len(left_r),
              "ticked": sum(1 for r, a in pairs if added[a] and not removed[r]),
              "unticked": sum(1 for r, a in pairs if removed[r] and not added[a])}
    reason = None
    if lines and not removed and not added:
        reason = "story file changed without any checklist change"
    elif left_r and left_a:
        reason = "checklist items removed and added that don't match (reworded, or a different format?)"
    return counts, reason


def task_changes(diff_text):
    """Checkbox changes in a unified diff: tasks added, removed, ticked ([ ] -> [x]) and unticked."""
    return analyse(diff_text)[0]


def review_key(commit, path):
    return f"{commit['id']}:{path}"


def check_commit(bb, commit, stories_dir, decisions=None):
    """Story-file and task-list checks for one commit. Each changed story file is classified mechanically, or
    by a saved agent decision when the mechanical check flagged it; flagged files without a decision are
    returned in `pending` for review."""
    decisions = decisions or {}
    files = [f for f in bb.changed_files(commit["workspace"], commit["slug"], commit["id"])
             if f.startswith(stories_dir) and f.endswith(".md")]
    tasks = {"added": 0, "removed": 0, "ticked": 0, "unticked": 0}
    progress, per_file, pending = False, [], []
    for f in files:
        diff = bb.diff(commit["workspace"], commit["slug"], commit["id"], f)
        counts, reason = analyse(diff)
        decision = decisions.get(review_key(commit, f)) if reason else None
        if decision is not None:
            counts = {"added": 0, "removed": 0, "ticked": int(decision.get("ticked") or 0), "unticked": 0}
            file_progress, how = bool(decision.get("task_progress")), "agent review"
        else:
            file_progress, how = any(counts.values()), "pending review" if reason else "mechanical"
        if reason and decision is None:
            excerpt = [l[:200] for l in changed_lines(diff)]
            pending.append({"key": review_key(commit, f), "file": f, "reason": reason, "mechanical": counts,
                            "diff_excerpt": excerpt[:EXCERPT_LINES], "diff_lines": len(excerpt)})
        progress = progress or file_progress
        for k, v in counts.items():
            tasks[k] += v
        per_file.append({"path": f, "classified_by": how, "task_progress": file_progress, "tasks": counts,
                         **({"reason": reason} if reason else {}),
                         **({"decision_reason": decision.get("reason")} if decision else {})})
    return {"story_files": files, "story_updated": bool(files), "tasks": tasks,
            "task_list_updated": progress, "files": per_file, "pending": pending}


# ---------- finding commits ----------

def from_jira(m, rest, tickets, app):
    """Ticket key -> commits, from Jira's development information (Bitbucket connected to Jira)."""
    dev = cm.DevInfo(rest, app)
    out = {}
    for key, issue in tickets.items():
        commits = []
        for c in dev.get(issue)["commits"]:
            match = REPO_URL.search(c.get("repo_url") or "")
            if match:
                commits.append({**c, "workspace": match.group(1), "slug": match.group(2)})
        out[key] = commits
    return out


def from_scan(bb, repos, tickets, projects, start, end_excl):
    """Ticket key -> commits, by scanning repositories for commit messages that mention the key."""
    out = {k: [] for k in tickets}
    unmatched = 0
    for r in repos:
        for c in bb.commits(r["workspace"], r["slug"], start, end_excl):
            keys = keys_in(c["message"], projects)
            if not keys:
                unmatched += 1
            for k in keys & set(tickets):
                out[k].append(c)
    return out, unmatched


# ---------- metric ----------

def run(m, bb, rest, projects, repos=None, source="auto", stories_dir="docs/stories/", app="bitbucket",
        decisions=None, workspaces=None):
    tickets, cohort_of = {}, {}
    for c in g.COHORTS:
        for i in m.touched_in_period("bitbucket", "tickets", m.story, c):
            tickets[i["key"]] = i
            cohort_of[i["key"]] = c
    tz = datetime.now().astimezone().tzinfo
    start = datetime.combine(m.start, datetime.min.time(), tz)
    end_excl = datetime.combine(m.end + timedelta(days=1), datetime.min.time(), tz)

    unmatched, used = None, None
    if source == "jira" and not rest.available:
        raise g.JiraError(f"--bb-source jira needs Jira's development information: set {', '.join(rest.missing)}")
    if source in ("auto", "jira") and rest.available:
        linked = {i["key"] for c in g.COHORTS for i in m.find(m.remember(
            "bitbucket", f"{c}, with linked commits",
            m.jql_for(f"issuetype = {g.q(m.story)}", f"created < {g.q(m.d_to_excl)}", f"updated >= {g.q(m.d_from)}",
                      m.cohort(c), cm.HAS_CODE)))}
        if linked or source == "jira":
            used = "jira"
            found = from_jira(m, rest, {k: tickets[k] for k in linked if k in tickets}, app)
            found = {k: found.get(k, []) for k in tickets}
    if used != "jira":
        used = "scan"
        if not repos:
            ws = list(workspaces or []) or bb.workspaces()
            repos = [r for w in ws for r in bb.repos(w, m.start)]
            m.notes.append(f"Bitbucket: scanned all {len(repos)} repositories in {', '.join(ws)} updated since "
                           f"{m.d_from}. Pass --bb-repo WORKSPACE/REPO to limit the scan.")
        found, unmatched = from_scan(bb, repos, tickets, projects, start, end_excl)

    checks = {}
    for commits in found.values():
        for c in commits:
            if c["id"] not in checks:
                checks[c["id"]] = check_commit(bb, c, stories_dir, decisions)

    cohorts, authors, rows, repos_seen, unique, commit_tickets = {}, {}, [], {}, {}, {}
    for c in g.COHORTS:
        cohorts[c] = {"tickets": 0, "with_commits": 0, "commits": 0, "commits_story": 0, "commits_tasks": 0,
                      "tickets_story": 0, "tickets_tasks": 0, "tasks_ticked": 0}
    for key, issue in tickets.items():
        c = cohort_of[key]
        commits = {x["id"]: x for x in found.get(key, [])}.values()
        story = sum(1 for x in commits if checks[x["id"]]["story_updated"])
        tasks = sum(1 for x in commits if checks[x["id"]]["task_list_updated"])
        ticked = sum(checks[x["id"]]["tasks"]["ticked"] for x in commits)
        s = cohorts[c]
        s["tickets"] += 1
        s["with_commits"] += bool(commits)
        s["commits"] += len(commits)
        s["commits_story"] += story
        s["commits_tasks"] += tasks
        s["tickets_story"] += bool(story)
        s["tickets_tasks"] += bool(tasks)
        s["tasks_ticked"] += ticked
        for x in commits:
            unique.setdefault(x["id"], (x, set()))[1].add(c)
            commit_tickets.setdefault(x["id"], []).append(key)
        if commits:
            rows.append({"ticket": key, "cohort": c, "status": g.status_name(issue["fields"]) or "?",
                         "commits": len(commits), "story": story, "tasks": tasks, "ticked": ticked})
    for x, cs in unique.values():  # each commit once, even if it is linked to several tickets
        a = authors.setdefault(x["author"], {"on_gen_e2_tickets": False, "gen_e2_commits": False})
        a["on_gen_e2_tickets"] |= "gen-e2" in cs
        a["gen_e2_commits"] |= checks[x["id"]]["task_list_updated"]
        name = f"{x['workspace']}/{x['slug']}"
        repos_seen[name] = repos_seen.get(name, 0) + 1
    pending, classified = [], {"mechanical": 0, "agent review": 0, "pending review": 0}
    for x, _ in unique.values():
        for f in checks[x["id"]]["files"]:
            classified[f["classified_by"]] += 1
        for item in checks[x["id"]]["pending"]:
            pending.append({**item, "commit": x["id"], "repository": f"{x['workspace']}/{x['slug']}", "at": x["at"],
                            "author": g.pseudonym(x["author"]), "message": (x["message"] or "").splitlines()[0] if x["message"] else "",
                            "tickets": sorted(commit_tickets[x["id"]])})
    if pending:
        m.notes.append(f"Bitbucket: {len(pending)} story-file change(s) couldn't be classified mechanically and are "
                       "counted as-is until reviewed (see the review file).")
    if not any(cohorts[c]["with_commits"] for c in g.COHORTS):
        m.notes.append("Bitbucket: no commits found for the tickets. Check that commit messages mention ticket keys"
                       + (" and that the right repositories were scanned." if used == "scan" else "."))
    return {
        "source": used, "stories_dir": stories_dir, "cohorts": cohorts,
        "engineers": {
            "total": len(authors), "gen_e2_commits": sum(a["gen_e2_commits"] for a in authors.values()),
            "on_gen_e2_tickets": sum(a["on_gen_e2_tickets"] for a in authors.values()),
            "on_gen_e2_tickets_with_gen_e2_commits": sum(a["on_gen_e2_tickets"] and a["gen_e2_commits"]
                                                         for a in authors.values()),
        },
        "tickets": sorted(rows, key=lambda r: (r["cohort"], r["ticket"])),
        "repositories": sorted(repos_seen.items(), key=lambda kv: -kv[1]),
        "scanned_repositories": [f"{r['workspace']}/{r['slug']}" for r in repos] if used == "scan" else None,
        "unmatched_commits": unmatched, "api_calls": bb.calls,
        "commits": [{"id": x["id"], "repository": f"{x['workspace']}/{x['slug']}", "at": x["at"],
                     "author": g.pseudonym(x["author"]),
                     "message": (x["message"] or "").splitlines()[0] if x["message"] else "",
                     "tickets": sorted(commit_tickets[x["id"]]),
                     **{k: v for k, v in checks[x["id"]].items() if k != "pending"}}
                    for x, _ in sorted(unique.values(), key=lambda v: str(v[0]["at"]))],
        "classification": classified,
        "pending_review": sorted(pending, key=lambda p: str(p["at"])),
    }


def pct(n, d):
    return f"{n} ({round(100 * n / d)}%)" if d else str(n)


def render(r):
    src = ("Jira development information" if r["source"] == "jira"
           else f"scan of {len(r['scanned_repositories'] or [])} Bitbucket "
                f"{'repository' if len(r['scanned_repositories'] or []) == 1 else 'repositories'}")
    L = ["## Bitbucket: commits and gen-e2 story-file updates", "",
         f"Commits found from {src}. Story files: `{r['stories_dir']}`.", "",
         "### Tickets and their commits", "",
         "| Cohort | Tickets | With commits | Commits | Commits updating story file | Commits updating task list | "
         "Tickets with story file updated | Tickets with task list updated | Tasks ticked |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c in g.COHORTS:
        s = r["cohorts"][c]
        L.append(f"| {c} | {s['tickets']} | {pct(s['with_commits'], s['tickets'])} | {s['commits']} | "
                 f"{pct(s['commits_story'], s['commits'])} | {pct(s['commits_tasks'], s['commits'])} | "
                 f"{pct(s['tickets_story'], s['with_commits'])} | {pct(s['tickets_tasks'], s['with_commits'])} | "
                 f"{s['tasks_ticked']} |")
    e = r["engineers"]
    if e["total"]:
        L += ["", "### Engineers", "",
              "| | Engineers | Pushing gen-e2 commits | % |", "|---|---|---|---|",
              f"| With commits on the period's tickets | {e['total']} | {e['gen_e2_commits']} | "
              f"{round(100 * e['gen_e2_commits'] / e['total'])}% |"]
        if e["on_gen_e2_tickets"]:
            L.append(f"| Of those, working on gen-e2 tickets | {e['on_gen_e2_tickets']} | "
                     f"{e['on_gen_e2_tickets_with_gen_e2_commits']} | "
                     f"{round(100 * e['on_gen_e2_tickets_with_gen_e2_commits'] / e['on_gen_e2_tickets'])}% |")
    if r["tickets"]:
        L += ["", "<details><summary>Tickets with commits</summary>", "",
              "| Ticket | Cohort | Status | Commits | Updating story file | Updating task list | Tasks ticked |",
              "|---|---|---|---|---|---|---|"]
        L += [f"| {t['ticket']} | {t['cohort']} | {t['status']} | {t['commits']} | {t['story']} | {t['tasks']} | "
              f"{t['ticked']} |" for t in r["tickets"]]
        L += ["", "</details>"]
    if r["repositories"]:
        L += ["", "Repositories with matching commits: " + ", ".join(f"`{n}` ({k})" for n, k in r["repositories"]) + "."]
    if r["unmatched_commits"]:
        L += ["", f"Commits in the scanned repositories that mention no ticket key: {r['unmatched_commits']}."]
    k = r.get("classification") or {}
    if any(k.values()):
        L += ["", f"Story-file changes classified mechanically: {k.get('mechanical', 0)}; by agent review: "
                  f"{k.get('agent review', 0)}; awaiting review: {k.get('pending review', 0)}."]
    return L + [""]


DEFINITIONS = [
    "- **Bitbucket, tickets**: stories created before the period ended and updated since it began (both cohorts).",
    "- **Bitbucket, commits**: non-merge commits linked to a ticket, from Jira's development information, or from a "
    "scan of commits authored in the period whose message mentions the ticket key.",
    "- **Bitbucket, engineers**: distinct commit authors on the period's tickets. A **gen-e2 commit** updates a gen-e2 "
    "story file's task list (adds the plan or marks tasks done, including changes accepted in agent review). No names "
    "are reported; the raw-data and review files use stable anonymous IDs.",
    "- **Bitbucket, updating story file**: the commit changes a Markdown file under the story folder (default `docs/stories/`).",
    "- **Bitbucket, updating task list**: in those files the commit adds, removes, ticks or unticks a checklist task "
    "(`- [ ]` / `- [x]`, or numbered `1. [ ]`). Tasks are matched by ID (`T-01`, `P1-01`, `1.2`, …), then by text, then "
    "by similar wording. Story-file changes the parser can't classify (no checklist change, or unmatched items) are "
    "reviewed by the agent; its saved decisions are applied and reused.",
]
