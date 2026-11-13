#!/usr/bin/env python3
"""Gen-e2 (AISDLC) delivery metrics from Jira, using the Atlassian CLI (acli).

Commands:
  doctor                 check acli, its login, and the ATLASSIAN_* variables (prints JSON, no secrets)
  report [options]       compute the metrics and print a Markdown (or JSON) report
  bb-repos               list Bitbucket repositories updated since a date (needs BITBUCKET_TOKEN)

acli handles login, counts and project listing. acli can't return dates, parent links or change
history, so issue lists and history come from the Jira REST API (read-only) with the same API token.
Without a token, metrics that need history are skipped and the others still run.

Environment (or the nearest .env up to the repo root):
  ATLASSIAN_TOKEN    API token (id.atlassian.com > Security > API tokens); JIRA_TOKEN also accepted
  ATLASSIAN_URL      https://<site>.atlassian.net (default: the site acli is logged in to)
  ATLASSIAN_EMAIL    account email for the token (default: the email acli is logged in with)
  BITBUCKET_TOKEN    API token with Bitbucket scopes, only for `report --bitbucket` and `bb-repos`
  ATLASSIAN_PROJECT  default project key(s), comma-separated (optional)
  BITBUCKET_WORKSPACE  Bitbucket workspace(s) to scan, comma-separated: every repository updated in the period
                     is searched for ticket keys (optional; not needed if the token has read:workspace)
  BITBUCKET_REPOS    limit the scan to these repositories, WORKSPACE/REPO comma-separated (optional)
  ACLI_PATH          optional path to the acli binary
"""

import argparse
import base64
import calendar
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

# code_metrics.py imports this module; register it under its own name when run as a script,
# so both share one copy (and one JiraError class).
if __name__ == "__main__":
    sys.modules.setdefault("gen_e2_metrics", sys.modules[__name__])

ALL_METRICS = ("1", "2", "13", "14", "15", "16")
COHORTS = ("gen-e2", "other")
ISSUE_FIELDS = "issuetype,status,created,resolutiondate,statuscategorychangedate,labels,parent"
ACLI_SEARCH_FIELDS = "key,issuetype,status,labels"  # acli workitem search rejects date fields and parent
PARENT_CHUNK = 50  # epics per "parent in (...)" search, keeps JQL short


class JiraError(Exception):
    pass


# ---------- config ----------

def find_env_file(start):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, ".env")
        if os.path.isfile(p):
            return p
        parent = os.path.dirname(d)
        if os.path.exists(os.path.join(d, ".git")) or parent == d:
            return None
        d = parent


def load_env(path=None):
    path = path or find_env_file(os.getcwd())
    if not path or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            k = re.sub(r"^export\s+", "", k.strip())
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            if k and k not in os.environ:
                os.environ[k] = v
    return path


ENV_ALIASES = {"ATLASSIAN_TOKEN": "JIRA_TOKEN", "ATLASSIAN_EMAIL": "JIRA_EMAIL", "ATLASSIAN_URL": "JIRA_URL"}


def cfg(name):
    alias = ENV_ALIASES.get(name)
    return os.environ.get(name) or (os.environ.get(alias) if alias else None) or None


def site_url():
    u = cfg("ATLASSIAN_URL")
    if not u:
        return None
    u = u.strip().rstrip("/")
    if u.startswith("http://"):
        raise SystemExit("ATLASSIAN_URL must use https://")
    return u if u.startswith("https://") else "https://" + u


# ---------- dates ----------

def parse_dt(value):
    if not value or not isinstance(value, str):
        return None
    s = value.strip().replace("Z", "+00:00")
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)
    s = re.sub(r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), s)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def days_between(start, end):
    return (end - start).total_seconds() / 86400


def last_month(today=None):
    today = today or date.today()
    first_this = today.replace(day=1)
    end = first_this - timedelta(days=1)
    return end.replace(day=1), end


def month_range(ym):
    y, m = (int(x) for x in ym.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


# ---------- acli ----------

def acli_exe():
    p = cfg("ACLI_PATH")
    if p:
        return p if os.path.isfile(p) else None
    return shutil.which("acli")


def acli_status(exe):
    try:
        r = subprocess.run([exe, "jira", "auth", "status"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    out = (r.stdout + r.stderr).strip()
    authed = r.returncode == 0 and not re.search(
        r"not (logged|authenticated)|unauthenticated|no (active )?account|please (log ?in|authenticate)", out, re.I)
    return authed, out[:300]


def acli_identity(status_out):
    """Site URL and email from `acli jira auth status` output, e.g. 'Site: x.atlassian.net', 'Email: me@x.com'."""
    site = re.search(r"Site:\s*(\S+)", status_out or "")
    email = re.search(r"Email:\s*(\S+@\S+)", status_out or "")
    url = site.group(1) if site else None
    if url and not url.startswith("https://"):
        url = "https://" + url.split("://", 1)[-1]
    return url, email.group(1) if email else None


def fill_from_acli():
    """Default ATLASSIAN_URL/ATLASSIAN_EMAIL to acli's login, so only the token has to be configured.
    Returns which values came from acli."""
    if cfg("ATLASSIAN_URL") and cfg("ATLASSIAN_EMAIL"):
        return []
    exe = acli_exe()
    if not exe:
        return []
    authed, out = acli_status(exe)
    if not authed:
        return []
    url, email = acli_identity(out)
    filled = []
    for name, value in (("ATLASSIAN_URL", url), ("ATLASSIAN_EMAIL", email)):
        if value and not cfg(name):
            os.environ[name] = value
            filled.append(name)
    return filled


def bitbucket_client(debug=False):
    """Bitbucket API client from BITBUCKET_TOKEN (an API token with Bitbucket scopes) and the account email."""
    token, email = cfg("BITBUCKET_TOKEN"), cfg("BITBUCKET_EMAIL") or cfg("ATLASSIAN_EMAIL")
    missing = [n for n, v in (("BITBUCKET_TOKEN", token), ("ATLASSIAN_EMAIL", email)) if not v]
    if missing:
        raise JiraError(f"Bitbucket needs {', '.join(missing)} (env or .env). BITBUCKET_TOKEN must be an Atlassian "
                        "API token created with Bitbucket scopes (read repositories and pull requests).")
    import bitbucket_metrics
    return bitbucket_metrics.Bitbucket(email, token, debug)


def normalize_issues(data):
    """Accept the shapes acli --json may return and yield {'key', 'fields'} dicts."""
    if isinstance(data, dict):
        for k in ("issues", "workItems", "values", "results"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
        else:
            data = [data]
    out = []
    for item in data or []:
        if not isinstance(item, dict):
            continue
        fields = item.get("fields") if isinstance(item.get("fields"), dict) else {
            k: v for k, v in item.items() if k != "key"}
        out.append({"key": item.get("key") or fields.get("key"), "id": str(item.get("id") or fields.get("id") or "") or None,
                    "fields": fields})
    return out


class Acli:
    def __init__(self, exe, debug=False):
        self.exe, self.debug, self.cache = exe, debug, {}

    def run(self, *args):
        if self.debug:
            print("+ acli jira " + " ".join(args), file=sys.stderr)
        r = subprocess.run([self.exe, "jira", *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        if r.returncode:
            raise JiraError(f"acli {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[:500]}")
        return r.stdout

    def search(self, jql, fields=ACLI_SEARCH_FIELDS):
        """acli search only allows display fields (no dates or parent); see search_with_dates."""
        if (jql, fields) in self.cache:
            return self.cache[(jql, fields)]
        out = self.run("workitem", "search", "--jql", jql, "--fields", fields, "--json", "--paginate").strip()
        try:
            data = json.loads(out) if out else []
        except ValueError:
            raise JiraError(f"acli search returned non-JSON output: {out[:300]}")
        self.cache[(jql, fields)] = normalize_issues(data)
        return self.cache[(jql, fields)]

    def view(self, key, fields=ISSUE_FIELDS):
        out = self.run("workitem", "view", key, "--fields", fields, "--json").strip()
        try:
            data = json.loads(out)
        except ValueError:
            raise JiraError(f"acli view returned non-JSON output: {out[:300]}")
        return data.get("fields") if isinstance(data.get("fields"), dict) else data

    def search_with_dates(self, jql):
        """Fallback without REST credentials: one acli view per issue (slow, about 2-3 s each)."""
        if ("dates", jql) in self.cache:
            return self.cache[("dates", jql)]
        issues = [{**i, "fields": {**i["fields"], **self.view(i["key"])}} for i in self.search(jql)]
        self.cache[("dates", jql)] = issues
        return issues

    def count(self, jql):
        out = self.run("workitem", "search", "--jql", jql, "--count")
        nums = re.findall(r"\d+", out)
        if not nums:
            return len(self.search(jql, "key"))
        return int(nums[-1])


# ---------- REST (issue search and change history) ----------

BULK_CHUNK = 1000  # Jira's limit on issues per /changelog/bulkfetch request


def epoch_to_iso(value):
    if isinstance(value, (int, float)):
        secs = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(secs, tz=timezone.utc).isoformat()
    return value


class Changelog:
    def __init__(self, debug=False):
        self.base, email, token = site_url(), cfg("ATLASSIAN_EMAIL"), cfg("ATLASSIAN_TOKEN")
        self.missing = [n for n, v in (("ATLASSIAN_URL", self.base), ("ATLASSIAN_EMAIL", email),
                                       ("ATLASSIAN_TOKEN", token)) if not v]
        self.auth = None if self.missing else "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        self.debug, self.cache = debug, {}
        self.fallback_reason = None

    @property
    def available(self):
        return not self.missing

    def _get(self, path):
        for attempt in range(5):
            req = urllib.request.Request(self.base + path, headers={
                "Authorization": self.auth, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 4:
                    time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                    continue
                raise JiraError(f"GET {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")
            except urllib.error.URLError as e:
                raise JiraError(f"GET {path}: {e.reason}")
        raise JiraError(f"GET {path}: rate limited")

    def get_json(self, path):
        return self._get(path)

    def search(self, jql, fields=ISSUE_FIELDS):
        """POST /rest/api/3/search/jql: issues with dates and parent, 100 per call."""
        if ("search", jql) in self.cache:
            return self.cache[("search", jql)]
        if self.debug:
            print(f"+ rest search {jql}", file=sys.stderr)
        issues, token = [], None
        while True:
            body = {"jql": jql, "fields": fields.split(","), "maxResults": 100}
            if token:
                body["nextPageToken"] = token
            page = self._post("/rest/api/3/search/jql", body)
            issues += normalize_issues(page.get("issues", []))
            token = page.get("nextPageToken")
            if not token or page.get("isLast"):
                break
        self.cache[("search", jql)] = issues
        return issues

    def _post(self, path, body):
        for attempt in range(5):
            req = urllib.request.Request(self.base + path, method="POST", data=json.dumps(body).encode(), headers={
                "Authorization": self.auth, "Accept": "application/json", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 4:
                    time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                    continue
                raise JiraError(f"POST {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")
            except urllib.error.URLError as e:
                raise JiraError(f"POST {path}: {e.reason}")
        raise JiraError(f"POST {path}: rate limited")

    def prefetch(self, issues):
        """Bulk-load change history for `issues` via POST /changelog/bulkfetch.

        Issues without an id, or every issue if the bulk call fails, fall back to get() one at a time.
        """
        todo = {i["id"]: i["key"] for i in issues if i.get("id") and i.get("key") and i["key"] not in self.cache}
        if not todo or self.fallback_reason:
            return
        ids = list(todo)
        try:
            for n in range(0, len(ids), BULK_CHUNK):
                chunk = ids[n:n + BULK_CHUNK]
                found = {todo[i]: [] for i in chunk}
                token = None
                if self.debug:
                    print(f"+ changelog bulkfetch {len(chunk)} issues", file=sys.stderr)
                while True:
                    # No fieldIds filter: history items from Jira's importers have no field ID and would be
                    # dropped. Callers filter by field name instead.
                    body = {"issueIdsOrKeys": chunk, "maxResults": 1000}
                    if token:
                        body["nextPageToken"] = token
                    page = self._post("/rest/api/3/changelog/bulkfetch", body)
                    for log in page.get("issueChangeLogs", []):
                        key = todo.get(str(log.get("issueId")))
                        if key in found:
                            found[key] += [{**h, "created": epoch_to_iso(h.get("created"))}
                                           for h in log.get("changeHistories", [])]
                    token = page.get("nextPageToken")
                    if not token:
                        break
                for key, hist in found.items():
                    hist.sort(key=lambda h: parse_dt(h.get("created")) or datetime.min.replace(tzinfo=timezone.utc))
                    self.cache[key] = hist
        except JiraError as e:
            self.fallback_reason = str(e)

    def get(self, key):
        """Return the issue's change histories, oldest first."""
        if key in self.cache:
            return self.cache[key]
        if self.debug:
            print(f"+ changelog {key}", file=sys.stderr)
        values, start = [], 0
        while True:
            page = self._get(f"/rest/api/3/issue/{urllib.parse.quote(key)}/changelog?startAt={start}&maxResults=100")
            batch = page.get("values", [])
            values += batch
            start += len(batch)
            if page.get("isLast", True) or not batch or start >= page.get("total", start):
                break
        values.sort(key=lambda h: h.get("created", ""))
        self.cache[key] = values
        return values


# ---------- status discovery ----------

# Jira status category keys: new = "To Do", indeterminate = "In Progress", done = "Done".
TODO_NAME = re.compile(r"^(to ?do|selected for (development|dev)|ready( for (development|dev|work))?|open|committed)$", re.I)
NOT_TODO_NAME = re.compile(r"backlog|draft|funnel|idea|triage|new|refine|groom|discovery|hold|block", re.I)
REVIEW_NAME = re.compile(r"review|\bqa\b|test|verif|approv|uat", re.I)


def status_entry(s):
    cat = s.get("statusCategory") or {}
    return {"name": s.get("name"), "category": cat.get("key") or (cat.get("name") or "").lower() or None}


def discover_statuses(rest, acli, projects, story_type, epic_type):
    """Return {'story': [...], 'epic': [...], 'source': ...}; each item {'name', 'category'}."""
    found = {"story": {}, "epic": {}}
    source = None
    if rest.available and projects:
        source = "rest: /rest/api/3/project/{key}/statuses (full workflow)"
        for p in projects:
            for it in rest.get_json(f"/rest/api/3/project/{urllib.parse.quote(p)}/statuses"):
                kind = {story_type.lower(): "story", epic_type.lower(): "epic"}.get((it.get("name") or "").lower())
                for s in it.get("statuses", []) if kind else []:
                    e = status_entry(s)
                    found[kind][e["name"]] = e
    if not any(found.values()):
        source = "acli: statuses currently used by issues (may miss unused statuses)"
        scope = f"project in ({', '.join(q(p) for p in projects)}) AND " if projects else ""
        for kind, itype in (("story", story_type), ("epic", epic_type)):
            jql = f"{scope}issuetype = {q(itype)} ORDER BY updated DESC"
            out = acli.run("workitem", "search", "--jql", jql, "--fields", "status", "--json", "--limit", "500")
            try:
                issues = normalize_issues(json.loads(out or "[]"))
            except ValueError:
                raise JiraError(f"acli search returned non-JSON output: {out[:300]}")
            for i in issues:
                s = i["fields"].get("status")
                e = status_entry(s) if isinstance(s, dict) else {"name": s, "category": None}
                if e["name"]:
                    found[kind].setdefault(e["name"], e)
    return {"source": source, "story": list(found["story"].values()), "epic": list(found["epic"].values())}


def suggest_statuses(discovered):
    """Match workflow statuses to the metric concepts; returns names plus the reasoning."""
    story = discovered["story"]
    new = [s["name"] for s in story if s["category"] == "new"]
    todo = [n for n in new if TODO_NAME.match(n)]
    why_todo = "To Do-category statuses named like To Do / Selected for Development / Ready"
    if not todo:
        todo = [n for n in new if not NOT_TODO_NAME.search(n)]
        why_todo = "To Do-category statuses that are not backlog/draft/triage-like"
    if not todo:
        todo = [s["name"] for s in story if (s["name"] or "").lower() == "to do"] or ["To Do"]
        why_todo = "fallback: no match in the workflow; default 'To Do'"
    in_progress = [s["name"] for s in story if s["category"] == "indeterminate"]
    why_in_progress = "all In Progress-category story statuses (work starts on first entry into any of them)"
    if not in_progress:
        in_progress = ["In Progress"]
        why_in_progress = "fallback: no In Progress-category story status found; default 'In Progress'"
    review = [n for n in in_progress if REVIEW_NAME.search(n)]
    why_review = ("In Progress-category story statuses named like Review / QA / Test" if review
                  else "no review-like story status found; the Review tables will be empty")
    return {"todo_status": todo, "in_progress_status": in_progress, "review_status": review,
            "reason": {"todo_status": why_todo, "in_progress_status": why_in_progress,
                       "review_status": why_review}}


# ---------- history helpers ----------

def status_name(fields):
    s = fields.get("status")
    return (s.get("name") if isinstance(s, dict) else s) or ""


def done_at(fields):
    return parse_dt(fields.get("resolutiondate")) or parse_dt(fields.get("statuscategorychangedate"))


def entered_status_at(fields, histories, names):
    """First time the issue was in one of `names`: its creation time if it was created in that status."""
    names = {n.lower() for n in names}
    moves = [(parse_dt(h.get("created")), it) for h in histories for it in h.get("items", [])
             if (it.get("field") or "").lower() == "status"]
    initial = (moves[0][1].get("fromString") if moves else status_name(fields)) or ""
    if initial.lower() in names:
        return parse_dt(fields.get("created"))
    for when, it in moves:
        if (it.get("toString") or "").lower() in names:
            return when
    return None


def entries_into(fields, histories, names):
    """Every time the issue entered one of `names`, oldest first (its creation time if created in one)."""
    names = {n.lower() for n in names}
    moves = [(parse_dt(h.get("created")), it) for h in histories for it in h.get("items", [])
             if (it.get("field") or "").lower() == "status"]
    initial = (moves[0][1].get("fromString") if moves else status_name(fields)) or ""
    out = [parse_dt(fields.get("created"))] if initial.lower() in names else []
    out += [when for when, it in moves if (it.get("toString") or "").lower() in names]
    return [t for t in out if t]


RAW_HISTORY_FIELDS = ("status", "description", "attachment", "labels")


def pseudonym(name):
    """Stable anonymous ID for a person ("engineer-3f2a9c"), so files never contain names but the same person
    always maps to the same ID."""
    if not name or name == "unknown":
        return "unknown"
    return "engineer-" + hashlib.sha256(name.strip().lower().encode()).hexdigest()[:6]


def anonymised_links(cache):
    """Jira development-information records (--code) with commit authors replaced by pseudonyms."""
    if not cache:
        return cache
    return {k: {**v, "commits": [{**c, "author": pseudonym(c.get("author"))} for c in v.get("commits", [])]}
            for k, v in cache.items()}


def issue_snapshot(issue):
    """The fields the metrics use, flattened for the raw-data file."""
    f = issue.get("fields") or {}
    s, t, p = f.get("status"), f.get("issuetype"), f.get("parent")
    return {"type": t.get("name") if isinstance(t, dict) else t, "status": status_name(f),
            "status_category": status_entry(s)["category"] if isinstance(s, dict) else None,
            "created": f.get("created"), "resolved": f.get("resolutiondate"),
            "status_category_changed": f.get("statuscategorychangedate"), "labels": f.get("labels") or [],
            "parent": p.get("key") if isinstance(p, dict) else p}


def raw_history(histories):
    """Status, description, attachment and label changes. Descriptions are recorded by length only."""
    out = []
    for h in histories:
        for it in h.get("items", []):
            field = (it.get("field") or "").lower()
            if field not in RAW_HISTORY_FIELDS:
                continue
            change = {"at": h.get("created"), "field": field}
            if field == "description":
                change.update(from_length=len(it.get("fromString") or ""), to_length=len(it.get("toString") or ""))
            else:
                change.update({"from": it.get("fromString"), "to": it.get("toString")})
            out.append(change)
    return out


REVIEW_INSTRUCTIONS = (
    "Each item is a change to a gen-e2 story file that the script could not classify mechanically. Read its "
    "diff_excerpt and decide: task_progress = true if the change records progress on the story's implementation "
    "tasks in any format (ticked checkboxes, a status table, a 'Done' marker, a reworded task marked done); false "
    "for edits that are not task progress (acceptance criteria, wording, notes). ticked = how many tasks the change "
    "marks done. Add one entry per item to the decisions file, keyed by the item's key: "
    '{"<key>": {"task_progress": true|false, "ticked": <int>, "reason": "<one line>", "reviewed_by": "agent"}}. '
    "Leave an item out if you can't tell. Then rerun the same report command; saved decisions are reused on later runs.")


def parse_repos(values):
    """["acme/api,acme/web", "acme/docs"] -> [{"workspace": "acme", "slug": "api"}, ...]; ignores blanks."""
    out = []
    for v in values:
        for x in (v or "").split(","):
            w, _, r = x.strip().strip("/").partition("/")
            if w and r:
                out.append({"workspace": w, "slug": r})
    return out


def bitbucket_enabled(flag, notes):
    """--bitbucket / --no-bitbucket win; otherwise run the checks when a Bitbucket token is configured."""
    if flag is not None:
        return flag
    if cfg("BITBUCKET_TOKEN"):
        return True
    notes.append("Bitbucket checks skipped: no BITBUCKET_TOKEN configured (see references/bitbucket-checks.md).")
    return False


def load_decisions(path, notes):
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        notes.append(f"Review decisions file `{path}` is not valid JSON ({e}); ignored.")
        return {}
    valid = {k: v for k, v in data.items() if isinstance(v, dict) and isinstance(v.get("task_progress"), bool)
             and isinstance(v.get("ticked", 0), int) and v.get("reason")}
    if len(valid) != len(data):
        notes.append(f"Review decisions: {len(data) - len(valid)} entries ignored (need task_progress true/false, "
                     "an integer ticked and a reason).")
    return valid


def raw_data(m, meta, results, code=None, bitbucket=None, dev=None):
    """Everything the report was computed from: searches with the issue keys they returned, issue snapshots,
    change history, and (with --code / --bitbucket) the linked commits and their checks."""
    used_by = {}
    for metric, items in m.jql.items():
        for item in items:
            used_by.setdefault(item["jql"], []).append({"metric": metric, "label": item["label"]})
    searches = [{"used_by": used_by.get(x["jql"], []), **x} for x in m.raw_searches]
    cache = getattr(m.cl, "cache", None) or {}
    histories = {k: raw_history(v) for k, v in cache.items() if isinstance(k, str)}
    return {"meta": meta, "searches": searches, "issues": m.raw_issues,
            "histories": {k: v for k, v in histories.items() if v},
            "results": results, "code": code, "code_links": anonymised_links(getattr(dev, "cache", None)),
            "bitbucket": bitbucket, "notes": m.notes}


def status_spans(fields, histories):
    """(status, from, to) for each status the issue has been in, oldest first; `to` is None for the current one."""
    moves = [(parse_dt(h.get("created")), it) for h in histories for it in h.get("items", [])
             if (it.get("field") or "").lower() == "status"]
    current = (moves[0][1].get("fromString") if moves else status_name(fields)) or ""
    since, spans = parse_dt(fields.get("created")), []
    for when, it in moves:
        spans.append((current, since, when))
        current, since = it.get("toString") or "", when
    return spans + [(current, since, None)]


def count_edits(histories, field_names):
    wanted = {f.lower() for f in field_names}
    counts = {f: 0 for f in field_names}
    for h in histories:
        for it in h.get("items", []):
            f = (it.get("field") or "").lower()
            if f in wanted:
                counts[next(n for n in field_names if n.lower() == f)] += 1
    return counts


def summarize(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0, "avg": None, "median": None}
    return {"n": len(values), "avg": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2)}


# ---------- metrics ----------

def q(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


class Metrics:
    def __init__(self, acli, changelog, projects, label, start, end, todo_statuses,
                 story_type="Story", epic_type="Epic", log=None, in_progress_statuses=("In Progress",),
                 review_statuses=("In Review",)):
        self.acli, self.cl = acli, changelog
        self.label, self.start, self.end = label, start, end
        self.todo = todo_statuses
        self.in_progress = list(in_progress_statuses)
        self.review = list(review_statuses)
        self.story, self.epic = story_type, epic_type
        self.scope = f"project in ({', '.join(q(p) for p in projects)})" if projects else ""
        self.notes, self.jql = [], {}
        self.raw_searches, self.raw_issues = [], {}
        self.now = None  # "as of" time for metric 1; None = when the report runs
        self.log = log or (lambda msg: print(msg, file=sys.stderr))

    # JQL building blocks
    @property
    def d_from(self):
        return self.start.isoformat()

    @property
    def d_to_excl(self):
        return (self.end + timedelta(days=1)).isoformat()

    def cohort(self, name):
        if name == "gen-e2":
            return f"labels = {q(self.label)}"
        return f"(labels is EMPTY OR labels not in ({q(self.label)}))"

    def jql_for(self, *parts):
        return " AND ".join(p for p in (self.scope, *parts) if p)

    def remember(self, metric, label, jql):
        entry = {"label": label, "jql": jql}
        if entry not in self.jql.setdefault(metric, []):
            self.jql[metric].append(entry)
        return jql

    def find(self, jql):
        """Issues with dates and parent: REST search when credentials are set, else acli view per issue."""
        found = self.cl.search(jql) if self.cl.available and hasattr(self.cl, "search") else self.acli.search_with_dates(jql)
        self.raw_searches.append({"jql": jql, "keys": [i["key"] for i in found]})
        for i in found:
            self.raw_issues.setdefault(i["key"], issue_snapshot(i))
        return found

    def count(self, jql):
        n = self.acli.count(jql)
        self.raw_searches.append({"jql": jql, "count": n})
        return n

    def need_changelog(self, metric):
        if self.cl.available:
            return True
        self.notes.append(f"Metric {metric} skipped: changelog needs {', '.join(self.cl.missing)}.")
        return False

    def done_jql(self, cohort, *extra):
        # Same rule as done_at(): resolution date, or the status-category date when there is no resolution.
        in_period = (f"((resolved >= {q(self.d_from)} AND resolved < {q(self.d_to_excl)}) OR "
                     f"(resolution is EMPTY AND statusCategoryChangedDate >= {q(self.d_from)} "
                     f"AND statusCategoryChangedDate < {q(self.d_to_excl)}))")
        return self.jql_for(f"issuetype = {q(self.story)}", "statusCategory = Done", in_period,
                            self.cohort(cohort), *extra)

    def done_stories(self, metric, cohort):
        return self.find(self.remember(metric, cohort, self.done_jql(cohort)))

    def in_period(self, t):
        tz = datetime.now().astimezone().tzinfo
        lo = datetime.combine(self.start, datetime.min.time(), tz)
        hi = datetime.combine(self.end + timedelta(days=1), datetime.min.time(), tz)
        return t is not None and lo <= t < hi

    def touched_in_period(self, metric, label, itype, cohort):
        """Candidates for a status change in the period: created before its end and updated since its start.
        The change itself is checked in the history, not with JQL `CHANGED ... DURING`, which doesn't see
        history from Jira's importers."""
        jql = self.jql_for(f"issuetype = {q(itype)}", f"created < {q(self.d_to_excl)}",
                           f"updated >= {q(self.d_from)}", self.cohort(cohort))
        return self.find(self.remember(metric, f"{cohort}, {label}", jql))

    def reviewed_stories(self, metric, cohort):
        """Candidate stories for the Review tables (see touched_in_period)."""
        if not self.review:
            return []
        return self.touched_in_period(metric, "candidates for review", self.story, cohort)

    def review_table(self, metric, start_of):
        """Per cohort: days from start_of(issue) to the first review entry."""
        if not self.review:
            self.notes.append(f"Metric {metric} review table skipped: no review status matched (pass --review-status).")
            return None
        if not self.need_changelog(f"{metric} (to Review)"):
            return None
        out = {}
        for c in COHORTS:
            vals, excluded = [], 0
            for i in self.reviewed_stories(metric, c):
                entries = entries_into(i["fields"], self.cl.get(i["key"]), self.review)
                if not any(self.in_period(t) for t in entries):
                    continue
                reviewed, start = entries[0], start_of(i)
                if self.in_period(reviewed) and start and reviewed >= start:
                    vals.append(days_between(start, reviewed))
                else:
                    excluded += 1
            out[c] = {**summarize(vals), "excluded": excluded}
        return out

    def work_started_at(self, issue):
        """First entry into a pre-review In Progress status (review statuses don't count as starting work)."""
        before_review = [s for s in self.in_progress if s.lower() not in {r.lower() for r in self.review}]
        return entered_status_at(issue["fields"], self.cl.get(issue["key"]), before_review or self.in_progress)

    def created_stories(self, metric, cohort):
        jql = self.jql_for(f"issuetype = {q(self.story)}", f"created >= {q(self.d_from)}",
                           f"created < {q(self.d_to_excl)}", self.cohort(cohort))
        return self.find(self.remember(metric, cohort, jql))

    def story_state(self, fields):
        """'done', 'review' or 'open', from the story's current status."""
        s = fields.get("status")
        category = status_entry(s)["category"] if isinstance(s, dict) else None
        name = status_name(fields).lower()
        if category == "done" or (category is None and (fields.get("resolutiondate") or name == "done")):
            return "done"
        if name in {r.lower() for r in self.review}:
            return "review"
        return "open"

    def m1(self):
        """Stories created in the period, followed up to now: completion, time to Review / Done, and the age
        of the stories that are neither Done nor in Review."""
        now = self.now or datetime.now(timezone.utc)
        history = bool(self.review) and self.cl.available
        if not self.review:
            self.notes.append("Metric 1 creation → Review times skipped: no review status matched (pass --review-status).")
        elif not self.cl.available:
            self.notes.append(f"Metric 1 creation → Review times skipped: change history needs {', '.join(self.cl.missing)}.")
        out = {}
        for c in COHORTS:
            stories = self.created_stories("1", c)
            if history:
                self.log(f"metric 1: reading changelog for {len(stories)} {c} stories")
            counts = {"done": 0, "review": 0, "open": 0}
            to_done, to_review, open_rows = [], [], []
            for i in stories:
                f = i["fields"]
                created, state = parse_dt(f.get("created")), self.story_state(f)
                counts[state] += 1
                finished = done_at(f) if state == "done" else None
                if created and finished:
                    to_done.append(days_between(created, finished))
                if history and created:
                    reviewed = entered_status_at(f, self.cl.get(i["key"]), self.review)
                    if reviewed and reviewed >= created:
                        to_review.append(days_between(created, reviewed))
                if state == "open":
                    open_rows.append({"key": i["key"], "status": status_name(f) or "unknown",
                                      "age": round(days_between(created, now), 2) if created else None})
            total = len(stories)
            ages = [r["age"] for r in open_rows if r["age"] is not None]
            by_status = {}
            for r in open_rows:
                by_status[r["status"]] = by_status.get(r["status"], 0) + 1
            pct = (lambda n: round(100 * n / total, 1)) if total else (lambda n: None)
            out[c] = {
                "created": total, **counts,
                "pct_done": pct(counts["done"]),
                "pct_done_or_review": pct(counts["done"] + counts["review"]),
                "to_done": summarize(to_done),
                "to_review": {**summarize(to_review), "pct_reached": pct(len(to_review))} if history else None,
                "open_stories": {**summarize(ages), "oldest": max(ages, default=None),
                                 "by_status": dict(sorted(by_status.items(), key=lambda kv: -kv[1])),
                                 "stories": sorted(open_rows, key=lambda r: -(r["age"] or 0))},
            }
        return {"as_of": now.isoformat(timespec="seconds"), "cohorts": out}

    def m2(self):
        if not self.need_changelog("2"):
            return None
        done = {}
        for c in COHORTS:
            vals, never = [], 0
            stories = self.done_stories("2", c)
            self.log(f"metric 2: reading changelog for {len(stories)} {c} stories")
            for i in stories:
                f = i["fields"]
                started = entered_status_at(f, self.cl.get(i["key"]), self.in_progress)
                finished = done_at(f)
                if started and finished and finished >= started:
                    vals.append(days_between(started, finished))
                else:
                    never += 1
            done[c] = {**summarize(vals), "excluded": never}
        return {"done": done, "review": self.review_table("2", self.work_started_at)}

    def period_bounds(self):
        tz = datetime.now().astimezone().tzinfo
        return (datetime.combine(self.start, datetime.min.time(), tz),
                datetime.combine(self.end + timedelta(days=1), datetime.min.time(), tz))

    def active_candidates(self):
        """Stories that may have been active in the period: changed since it began, or still In Progress."""
        jql = self.jql_for(f"issuetype = {q(self.story)}", f"created < {q(self.d_to_excl)}",
                           f'(updated >= {q(self.d_from)} OR statusCategory = "In Progress")')
        return self.find(self.remember("13", "active story candidates", jql))

    def was_active(self, issue):
        """In an In Progress or Review status at any time in the period, or reached Done in the period."""
        f = issue["fields"]
        if self.story_state(f) == "done" and self.in_period(done_at(f)):
            return True
        lo, hi = self.period_bounds()
        working = {s.lower() for s in self.in_progress}
        return any(status.lower() in working and (a is None or a < hi) and (b is None or b > lo)
                   for status, a, b in status_spans(f, self.cl.get(issue["key"])))

    def m13(self):
        """Epics with at least one active story in the period, split by the epic's own label."""
        stories = self.active_candidates()
        if self.cl.available:
            active = [i for i in stories if self.was_active(i)]
        else:
            active = stories
            self.notes.append("Metric 13 is approximate: without change history, every story updated in the period "
                              f"or still In Progress counts as active ({', '.join(self.cl.missing)} missing).")
        by_epic, no_epic = {}, 0
        for i in active:
            p = i["fields"].get("parent")
            pkey = p.get("key") if isinstance(p, dict) else p
            if pkey:
                by_epic[pkey] = by_epic.get(pkey, 0) + 1
            else:
                no_epic += 1
        epics, keys = [], sorted(by_epic)
        for n in range(0, len(keys), PARENT_CHUNK):
            chunk = keys[n:n + PARENT_CHUNK]
            jql = self.jql_for(f"key in ({', '.join(q(k) for k in chunk)})", f"issuetype = {q(self.epic)}")
            for e in self.find(self.remember("13", "epics of active stories", jql)):
                f = e["fields"]
                epics.append({"epic": e["key"], "cohort": "gen-e2" if self.label in (f.get("labels") or []) else "other",
                              "status": status_name(f) or "?", "active_stories": by_epic.get(e["key"], 0)})
        out = {c: sum(1 for e in epics if e["cohort"] == c) for c in COHORTS}
        out.update({
            "total": len(epics),
            "active_stories": {c: sum(e["active_stories"] for e in epics if e["cohort"] == c) for c in COHORTS},
            "active_stories_without_epic": no_epic,
            "epics": sorted(epics, key=lambda e: (e["cohort"], -e["active_stories"], e["epic"])),
        })
        return out

    def m14(self):
        base = (f"issuetype = {q(self.story)}", f"created >= {q(self.d_from)}", f"created < {q(self.d_to_excl)}")
        total = self.count(self.remember("14", "all stories", self.jql_for(*base)))
        gen = self.count(self.remember("14", "gen-e2 stories", self.jql_for(*base, self.cohort("gen-e2"))))
        return {"total": total, "gen-e2": gen, "pct": round(100 * gen / total, 1) if total else None}

    def epics_created(self, metric, cohort):
        jql = self.jql_for(f"issuetype = {q(self.epic)}", f"created >= {q(self.d_from)}",
                           f"created < {q(self.d_to_excl)}", self.cohort(cohort))
        return self.find(self.remember(metric, cohort, jql))

    def children_of(self, epics):
        """Child stories grouped by parent key, using one search per PARENT_CHUNK epics."""
        groups = {e["key"]: [] for e in epics}
        keys = list(groups)
        for n in range(0, len(keys), PARENT_CHUNK):
            chunk = keys[n:n + PARENT_CHUNK]
            jql = self.jql_for(f"parent in ({', '.join(q(k) for k in chunk)})", f"issuetype = {q(self.story)}")
            for ch in self.find(jql):
                p = ch["fields"].get("parent")
                pkey = p.get("key") if isinstance(p, dict) else p
                if pkey in groups:
                    groups[pkey].append(ch)
        return groups

    def m15(self):
        if not self.need_changelog("15"):
            return None
        out = {}
        for c in COHORTS:
            vals, pending, detail = [], 0, []
            epics = self.epics_created("15", c)
            self.log(f"metric 15: scanning stories of {len(epics)} {c} epics")
            groups = self.children_of(epics)
            for e in epics:
                created = parse_dt(e["fields"].get("created"))
                children = groups[e["key"]]
                firsts = [t for t in (entered_status_at(ch["fields"], self.cl.get(ch["key"]), self.todo)
                                      for ch in children) if t]
                if created and firsts:
                    lag = days_between(created, min(firsts))
                    vals.append(lag)
                    detail.append({"epic": e["key"], "days": round(lag, 2), "stories": len(children)})
                else:
                    pending += 1
                    detail.append({"epic": e["key"], "days": None, "stories": len(children)})
            out[c] = {**summarize(vals), "epics_without_story_in_todo": pending, "epics": detail}
        self.remember("15", "children (batched)", self.jql_for('parent in ("<EPIC-1>", "<EPIC-2>", …)', f"issuetype = {q(self.story)}"))
        return out

    def m16(self):
        if not self.need_changelog("16"):
            return None
        fields = ("description", "Attachment")
        out = {}
        for c in COHORTS:
            per_epic = []
            epics = self.epics_created("16", c)
            self.log(f"metric 16: reading changelog for {len(epics)} {c} epics")
            for e in epics:
                counts = count_edits(self.cl.get(e["key"]), fields)
                per_epic.append({"epic": e["key"], **counts, "total": sum(counts.values())})
            totals = [p["total"] for p in per_epic]
            out[c] = {
                "epics": len(per_epic),
                "description_edits": sum(p["description"] for p in per_epic),
                "attachment_changes": sum(p["Attachment"] for p in per_epic),
                "avg_edits_per_epic": round(statistics.mean(totals), 2) if totals else None,
                "pct_epics_reworked": round(100 * sum(1 for t in totals if t) / len(totals), 1) if totals else None,
                "per_epic": per_epic,
            }
        return out

    def prefetch_histories(self, which):
        """Fetch change history in bulk before the metrics run: one batch of stories (metrics 1, 2, 13, 15)
        and one batch of epics (metric 16)."""
        if not self.cl.available or not hasattr(self.cl, "prefetch"):
            return
        stories, epics = [], []
        for c in COHORTS:
            if "1" in which and self.review:
                stories += self.created_stories("1", c)
            if "2" in which:
                stories += self.done_stories("2", c)
                if self.review:
                    stories += self.reviewed_stories("2", c)
            if "15" in which:
                stories += [ch for kids in self.children_of(self.epics_created("15", c)).values() for ch in kids]
            if "16" in which:
                epics += self.epics_created("16", c)
        if "13" in which:
            stories += self.active_candidates()
        for kind, issues in (("story", stories), ("epic", epics)):
            issues = list({i["key"]: i for i in issues}.values())
            if issues:
                self.log(f"fetching {kind} history for {len(issues)} issues in bulk")
                self.cl.prefetch(issues)
        no_id = sum(1 for i in stories + epics if not i.get("id"))
        if no_id:
            self.notes.append(f"{no_id} issues had no id in the acli output; their history was fetched one issue at a time.")

    def run(self, which):
        results = {}
        try:
            self.prefetch_histories(which)
        except JiraError as e:
            self.notes.append(f"Bulk history prefetch failed ({e}); history is fetched per issue instead.")
        for m in which:
            try:
                results[m] = getattr(self, "m" + m)()
            except JiraError as e:
                results[m] = None
                self.notes.append(f"Metric {m} failed: {e}")
        reason = getattr(self.cl, "fallback_reason", None)
        if reason:
            self.notes.append(f"Bulk history fetch unavailable ({reason}); history was fetched one issue at a time.")
        return results


# ---------- rendering ----------

TITLES = {
    "1": "Completion and lead time of stories created in the period (creation to Review and to Done)",
    "2": "Average time from In Progress to Review and to Done (cycle time)",
    "13": "Epics with active stories in the period (gen-e2 vs not)",
    "14": "% of stories created with gen-e2",
    "15": "Time between epic creation and first story in To Do",
    "16": "Rate of BRD rework (epic description and attachment edits)",
}


def fmt(v, suffix=""):
    return "n/a" if v is None else f"{v}{suffix}"


def duration_table(rows, extra=None):
    head = "| Cohort | Count | Average (days) | Median (days) |" + (f" {extra[1]} |" if extra else "")
    L = [head, "|" + "---|" * (5 if extra else 4)]
    for c in COHORTS:
        row = f"| {c} | {rows[c]['n']} | {fmt(rows[c]['avg'])} | {fmt(rows[c]['median'])} |"
        L.append(row + (f" {rows[c][extra[0]]} |" if extra else ""))
    return L


def render_m1(r):
    rows = r["cohorts"]
    L = [f"Stories created in the period, with their status as of {r['as_of']}.", "",
         "### Completion", "",
         "| Cohort | Created | Done | In Review | Not Done or in Review | % Done | % Done or in Review |",
         "|---|---|---|---|---|---|---|"]
    for c in COHORTS:
        x = rows[c]
        L.append(f"| {c} | {x['created']} | {x['done']} | {x['review']} | {x['open']} | "
                 f"{fmt(x['pct_done'], '%')} | {fmt(x['pct_done_or_review'], '%')} |")
    L += ["", "### Creation → Done (stories now Done)", ""] + duration_table({c: rows[c]["to_done"] for c in COHORTS})
    L += ["", "### Creation → Review (stories that ever reached a Review status, including ones now Done)", ""]
    if any(rows[c]["to_review"] is None for c in COHORTS):
        L.append("Not computed (see Notes).")
    else:
        L += ["| Cohort | Count | % of created | Average (days) | Median (days) |", "|---|---|---|---|---|"]
        for c in COHORTS:
            x = rows[c]["to_review"]
            L.append(f"| {c} | {x['n']} | {fmt(x['pct_reached'], '%')} | {fmt(x['avg'])} | {fmt(x['median'])} |")
    L += ["", "### Stories not Done or in Review (age since creation)", "",
          "| Cohort | Count | Average age (days) | Median age (days) | Oldest (days) | Current status |",
          "|---|---|---|---|---|---|"]
    for c in COHORTS:
        o = rows[c]["open_stories"]
        by_status = ", ".join(f"{s} {n}" for s, n in o["by_status"].items()) or "-"
        L.append(f"| {c} | {rows[c]['open']} | {fmt(o['avg'])} | {fmt(o['median'])} | {fmt(o['oldest'])} | {by_status} |")
    for c in COHORTS:
        stories = rows[c]["open_stories"]["stories"]
        if stories:
            L += ["", f"<details><summary>{c} stories not Done or in Review</summary>", "",
                  "| Story | Status | Age (days) |", "|---|---|---|"]
            L += [f"| {s['key']} | {s['status']} | {fmt(s['age'])} |" for s in stories]
            L += ["", "</details>"]
    return L


def render_markdown(meta, results, jql, notes, code=None, bitbucket=None):
    L = [f"# Gen-e2 delivery metrics: {meta['from']} to {meta['to']}", "",
         f"- Projects: {', '.join(meta['projects']) or 'all (no project filter)'}",
         f"- Gen-e2 = label `{meta['label']}`; \"other\" = issues without that label",
         f"- To Do status: {', '.join(meta['todo_statuses'])}; In Progress status: {', '.join(meta['in_progress_statuses'])}; "
         f"Review status: {', '.join(meta.get('review_statuses') or ['none'])}",
         f"- Generated: {meta['generated']}", ""]
    for m, r in results.items():
        L += [f"## {m}. {TITLES[m]}", ""]
        if r is None:
            L.append("Not computed (see Notes).")
        elif m == "1":
            L += render_m1(r)
        elif m == "2":
            L += ["### In Progress → Done", ""] + duration_table(r["done"], ("excluded", "Excluded (never In Progress)"))
            L += ["", "### In Progress → Review", ""]
            if r["review"] is None:
                L.append("Not computed (see Notes).")
            else:
                L += duration_table(r["review"], ("excluded", "Excluded (no In Progress before review, or first review before period)"))
        elif m == "15":
            L += duration_table(r, ("epics_without_story_in_todo", "Epics without story in To Do"))
            for c in COHORTS:
                if r[c]["epics"]:
                    L += ["", f"<details><summary>{c} epics</summary>", "",
                          "| Epic | Days to first story in To Do | Stories |", "|---|---|---|"]
                    L += [f"| {e['epic']} | {fmt(e['days'])} | {e['stories']} |" for e in r[c]["epics"]]
                    L += ["", "</details>"]
        elif m == "13":
            a = r["active_stories"]
            L += ["| Cohort (epic's label) | Epics with active stories | Active stories in those epics |", "|---|---|---|",
                  f"| gen-e2 | {r['gen-e2']} | {a['gen-e2']} |", f"| other | {r['other']} | {a['other']} |",
                  f"| **total** | **{r['total']}** | **{a['gen-e2'] + a['other']}** |"]
            if r["active_stories_without_epic"]:
                L += ["", f"Active stories with no epic: {r['active_stories_without_epic']}."]
            for c in COHORTS:
                rows = [e for e in r["epics"] if e["cohort"] == c]
                if rows:
                    L += ["", f"<details><summary>{c} epics</summary>", "",
                          "| Epic | Status | Active stories |", "|---|---|---|"]
                    L += [f"| {e['epic']} | {e['status']} | {e['active_stories']} |" for e in rows]
                    L += ["", "</details>"]
        elif m == "14":
            L += ["| Stories created | Gen-e2 stories | % gen-e2 |", "|---|---|---|",
                  f"| {r['total']} | {r['gen-e2']} | {fmt(r['pct'], '%')} |"]
        elif m == "16":
            L += ["| Cohort | Epics | Description edits | Attachment changes | Avg edits per epic | % epics reworked |",
                  "|---|---|---|---|---|---|"]
            for c in COHORTS:
                x = r[c]
                L.append(f"| {c} | {x['epics']} | {x['description_edits']} | {x['attachment_changes']} | "
                         f"{fmt(x['avg_edits_per_epic'])} | {fmt(x['pct_epics_reworked'], '%')} |")
            reworked = [p for p in r["gen-e2"]["per_epic"] if p["total"]]
            if reworked:
                L += ["", "<details><summary>gen-e2 epics with rework</summary>", "",
                      "| Epic | Description | Attachment | Total |", "|---|---|---|---|"]
                L += [f"| {p['epic']} | {p['description']} | {p['Attachment']} | {p['total']} |" for p in reworked]
                L += ["", "</details>"]
        L.append("")
    if code is not None:
        import code_metrics
        L += code_metrics.render(code)
    if bitbucket is not None:
        import bitbucket_metrics
        L += bitbucket_metrics.render(bitbucket)
    L += ["## Definitions", "",
          "- **1**: stories created in the period, with their status when the report runs. Done = Done status category; In Review = currently in a Review status; % Done or in Review = (Done + In Review) / created.",
          "- **1 → Done**: stories now Done; resolved (or status-category change) minus created.",
          "- **1 → Review**: stories that ever entered a Review status (from their change history, including ones now Done); first entry minus created.",
          "- **1 not Done or in Review**: the rest; age = report time minus created, grouped by current status.",
          "- **2 → Done**: stories in the Done status category resolved in the period (or, if unresolved, whose status category changed in the period); Done time minus the first entry into any In Progress status. Stories that went straight to Done are excluded.",
          "- **2 → Review**: stories that first entered a Review status in the period; that time minus the first entry into a pre-review In Progress status.",
          "- **13**: epics with at least one active story in the period, split by the epic's own label. A story is active if it was in an In Progress or Review status at any time in the period, or reached Done in the period (from its change history).",
          "- **14**: stories created in the period carrying the gen-e2 label, divided by all stories created in the period.",
          "- **15**: epics created in the period; first time any child story was in To Do minus the epic's creation time.",
          "- **16**: epics created in the period; changelog entries for `description` and `Attachment` from creation until now.",
          ]
    if code is not None:
        import code_metrics
        L += code_metrics.DEFINITIONS
    if bitbucket is not None:
        import bitbucket_metrics
        L += bitbucket_metrics.DEFINITIONS
    L.append("")
    if notes:
        L += ["## Notes", ""] + [f"- {n}" for n in notes] + [""]
    L += ["## JQL used", ""]
    for m, qs in sorted(jql.items(), key=lambda kv: (not kv[0].isdigit(), int(kv[0]) if kv[0].isdigit() else 0)):
        for item in qs:
            L.append(f"- **{m}** ({item['label']}): `{item['jql']}`")
    return "\n".join(L) + "\n"


# ---------- commands ----------

def doctor(env_file):
    exe = acli_exe()
    authed, status_out = acli_status(exe) if exe else (False, None)
    from_acli = fill_from_acli()
    env = {n: ("from acli login" if n in from_acli else "set" if cfg(n) else "missing") for n in
           ("ATLASSIAN_URL", "ATLASSIAN_EMAIL", "ATLASSIAN_TOKEN", "ATLASSIAN_PROJECT", "BITBUCKET_WORKSPACE",
            "BITBUCKET_REPOS")}
    report = {
        "env_file": env_file,
        "acli": {"path": exe, "authenticated": authed, "status": status_out},
        "env": env,
        "searches_ready": bool(exe and authed),
        "changelog_ready": all(env[n] != "missing" for n in ("ATLASSIAN_URL", "ATLASSIAN_EMAIL", "ATLASSIAN_TOKEN")),
    }
    if env["ATLASSIAN_TOKEN"] == "missing":
        report["token_hint"] = ("Only the API token is missing: add ATLASSIAN_TOKEN=<token> (or JIRA_TOKEN=<token>) "
                                "to a git-ignored .env in the repo. Site and email are read from the acli login.")
    if not exe:
        report["acli_install"] = {
            "macOS": "brew tap atlassian/homebrew-acli && brew install acli",
            "docs": "https://developer.atlassian.com/cloud/acli/guides/install-acli/",
        }
    elif not authed:
        report["acli_login"] = ("run `acli jira auth login --web`, or pipe the token: "
                                "echo $ATLASSIAN_TOKEN | acli jira auth login --site <site> --email <email> --token")
    report["bitbucket"] = {"token": "set" if cfg("BITBUCKET_TOKEN") else "missing (only needed for --bitbucket)"}
    if cfg("BITBUCKET_TOKEN"):
        try:
            ok, granted, error = bitbucket_client().probe()
        except JiraError as e:
            ok, granted, error = False, None, str(e)
        bb = report["bitbucket"]
        if granted is None and ok:
            bb.update(ready=True, repository_discovery=True)
        elif granted is not None:
            bb.update(ready="read:repository:bitbucket" in granted,
                      repository_discovery="read:workspace:bitbucket" in granted, scopes=sorted(granted))
            missing = [x for x in ("read:repository:bitbucket", "read:workspace:bitbucket") if x not in granted]
            if missing:
                bb["missing_scopes"] = missing
                bb["hint"] = ("read:repository is required. Without read:workspace, set BITBUCKET_WORKSPACE (or pass "
                              "--bb-workspace) so the skill knows which workspace to search.")
        else:
            bb.update(ready=False, error=(error or "")[:200])
    print(json.dumps(report, indent=2))


def report(args):
    exe = acli_exe()
    if not exe:
        raise SystemExit("acli not found; install it or set ACLI_PATH (run `doctor`)")
    if args.month:
        start, end = month_range(args.month)
    elif args.date_from or args.date_to:
        if not (args.date_from and args.date_to):
            raise SystemExit("--from and --to must be used together")
        start, end = date.fromisoformat(args.date_from), date.fromisoformat(args.date_to)
    else:
        start, end = last_month()
    if end < start:
        raise SystemExit("--to is before --from")
    projects = resolve_projects(args)
    which = [m.strip() for m in args.metrics.split(",")] if args.metrics else list(ALL_METRICS)
    bad = [m for m in which if m not in ALL_METRICS]
    if bad:
        raise SystemExit(f"unknown metric(s) {', '.join(bad)}; choose from {', '.join(ALL_METRICS)}")

    acli, rest = Acli(exe, args.debug), Changelog(args.debug)
    todo, in_prog, review = args.todo_status, args.in_progress_status, args.review_status
    auto_note = None
    if not (todo and in_prog and review):
        try:
            sug = suggest_statuses(discover_statuses(rest, acli, projects, args.story_type, args.epic_type))
            todo = todo or sug["todo_status"]
            in_prog = in_prog or sug["in_progress_status"]
            review = review or sug["review_status"]
            auto_note = (f"Statuses auto-matched from the workflow: To Do = {', '.join(todo)}; "
                         f"In Progress = {', '.join(in_prog)}; Review = {', '.join(review) or 'none'}. "
                         "Override with --todo-status / --in-progress-status / --review-status.")
        except JiraError as e:
            todo, in_prog = todo or ["To Do"], in_prog or ["In Progress"]
            review = review or ["In Review"]
            auto_note = f"Status discovery failed ({e}); used defaults 'To Do' / 'In Progress'."

    m = Metrics(acli, rest, projects, args.label, start, end, todo, args.story_type, args.epic_type,
                in_progress_statuses=in_prog, review_statuses=review)
    if auto_note:
        m.notes.append(auto_note)
    if not projects:
        m.notes.append("No project filter: JQL searched the whole site. Pass --project or set ATLASSIAN_PROJECT.")
    results = m.run(which)
    code, dev = None, None
    if args.code:
        if not rest.available:
            m.notes.append(f"Code metrics skipped: Jira's development information needs {', '.join(rest.missing)}.")
        else:
            import code_metrics
            try:
                dev = code_metrics.DevInfo(rest, args.code_app)
                code = code_metrics.run(m, dev)
            except JiraError as e:
                m.notes.append(f"Code metrics failed: {e}")
    bb_result = None
    out_dir = os.path.dirname(os.path.abspath(args.out)) if args.out else None
    decisions_path = args.decisions or (os.path.join(out_dir, "gen-e2-review-decisions.json") if out_dir else None)
    review_path = args.review_file or (os.path.splitext(args.out)[0] + ".review.json" if args.out else None)
    if bitbucket_enabled(args.bitbucket, m.notes):
        import bitbucket_metrics
        try:
            repos = parse_repos(args.bb_repo or [cfg("BITBUCKET_REPOS") or ""])
            decisions = load_decisions(decisions_path, m.notes)
            workspaces = [w.strip() for v in (args.bb_workspace or [cfg("BITBUCKET_WORKSPACE") or ""])
                          for w in v.split(",") if w.strip()]
            bb_result = bitbucket_metrics.run(m, bitbucket_client(args.debug), rest, projects, repos or None,
                                              args.bb_source, args.stories_dir, args.code_app, decisions, workspaces)
            pending = bb_result["pending_review"]
            if pending and review_path:
                with open(review_path, "w", encoding="utf-8") as f:
                    json.dump({"instructions": REVIEW_INSTRUCTIONS, "decisions_file": decisions_path,
                               "items": pending}, f, indent=2, default=str)
                    f.write("\n")
                m.notes.append(f"Review file: `{os.path.basename(review_path)}`; decisions are saved in "
                               f"`{os.path.basename(decisions_path or '')}`.")
            elif review_path and os.path.isfile(review_path):
                os.remove(review_path)  # nothing pending any more
            elif pending:
                m.notes.append("Pass --review-file (or --out) to write the items awaiting review.")
        except JiraError as e:
            m.notes.append(f"Bitbucket checks failed: {e}")
    raw_path = args.raw or (os.path.splitext(args.out)[0] + ".raw.json" if args.out else None)
    if raw_path:
        m.notes.append(f"Raw data behind this report: `{os.path.basename(raw_path)}`.")
    meta = {"from": start.isoformat(), "to": end.isoformat(), "projects": projects, "label": args.label,
            "todo_statuses": m.todo, "in_progress_statuses": m.in_progress, "review_statuses": m.review,
            "generated": datetime.now().astimezone().isoformat(timespec="seconds")}
    if args.format == "json":
        text = json.dumps({"meta": meta, "results": results, "code": code, "bitbucket": bb_result,
                           "notes": m.notes, "jql": m.jql},
                          indent=2, default=str) + "\n"
    else:
        text = render_markdown(meta, results, m.jql, m.notes, code, bb_result)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    if raw_path:
        os.makedirs(os.path.dirname(os.path.abspath(raw_path)), exist_ok=True)
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_data(m, meta, results, code, bb_result, dev), f, indent=2, default=str)
            f.write("\n")
        print(f"wrote raw data {raw_path}", file=sys.stderr)


def bb_repos(args):
    bb = bitbucket_client(args.debug)
    since = date.fromisoformat(args.since) if args.since else last_month()[0]
    workspaces = args.workspace or [w.strip() for w in (cfg("BITBUCKET_WORKSPACE") or "").split(",") if w.strip()] \
        or bb.workspaces()
    repos = [r for ws in workspaces for r in bb.repos(ws, since)]
    print(json.dumps({"since": since.isoformat(), "workspaces": workspaces, "repositories":
                      [f"{r['workspace']}/{r['slug']}" for r in repos]}, indent=2))


def statuses(args):
    exe = acli_exe()
    if not exe:
        raise SystemExit("acli not found; install it or set ACLI_PATH (run `doctor`)")
    projects = resolve_projects(args)
    found = discover_statuses(Changelog(args.debug), Acli(exe, args.debug), projects, args.story_type, args.epic_type)
    print(json.dumps({"projects": projects, **found, "suggested": suggest_statuses(found)}, indent=2))


def parse_projects(data):
    if isinstance(data, dict):
        for k in ("values", "projects", "results"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
        else:
            data = [data]
    return [{"key": p.get("key"), "name": p.get("name")} for p in data or []
            if isinstance(p, dict) and p.get("key")]


def projects_cmd(args):
    exe = acli_exe()
    if not exe:
        raise SystemExit("acli not found; install it or set ACLI_PATH (run `doctor`)")
    acli = Acli(exe, args.debug)
    out = acli.run("project", "list", "--paginate", "--json").strip()
    try:
        visible = parse_projects(json.loads(out or "[]"))
    except ValueError:
        raise JiraError(f"acli project list returned non-JSON output: {out[:300]}")
    # One search for recent labelled issues; project keys come from the issue key prefix.
    jql = f"labels = {q(args.label)} AND created >= -{args.days}d ORDER BY created DESC"
    used = {}
    for i in acli.search(jql, "key"):
        key = (i.get("key") or "").rsplit("-", 1)[0]
        if key:
            used[key] = used.get(key, 0) + 1
    for p in visible:
        p["labelled_issues_sampled"] = used.get(p["key"], 0)
    visible.sort(key=lambda p: (-p["labelled_issues_sampled"], p["key"]))
    print(json.dumps({"label": args.label, "label_window_days": args.days,
                      "default_from_env": cfg("ATLASSIAN_PROJECT"),
                      "projects": visible}, indent=2))


def resolve_projects(args):
    projects = [p.strip().upper() for v in (args.project or []) for p in v.split(",") if p.strip()]
    projects = projects or [p.strip() for p in (cfg("ATLASSIAN_PROJECT") or "").split(",") if p.strip()]
    if not projects and not getattr(args, "all_projects", False):
        raise SystemExit("no project selected: pass --project KEY (repeatable or comma-separated), "
                         "set ATLASSIAN_PROJECT, or pass --all-projects to search the whole site")
    return projects


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--env-file", help="path to a .env file (default: nearest .env up to the repo root)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    b = sub.add_parser("bb-repos", help="list Bitbucket repositories updated since a date (needs BITBUCKET_TOKEN)")
    b.add_argument("--workspace", action="append", help="Bitbucket workspace; default: all the token can see")
    b.add_argument("--since", help="YYYY-MM-DD (default: start of last month)")
    b.add_argument("--debug", action="store_true")
    pr = sub.add_parser("projects", help="list visible projects, ranked by recent use of the gen-e2 label")
    pr.add_argument("--label", default="AISDLC")
    pr.add_argument("--days", type=int, default=180, help="look-back window for the label usage hint (default 180)")
    pr.add_argument("--debug", action="store_true")
    s = sub.add_parser("statuses", help="list workflow statuses and the suggested To Do / In Progress / Review matching")
    s.add_argument("--project", action="append", help="project key; repeat or comma-separate for several")
    s.add_argument("--all-projects", action="store_true", help="explicitly search the whole site")
    s.add_argument("--story-type", default="Story")
    s.add_argument("--epic-type", default="Epic")
    s.add_argument("--debug", action="store_true")
    r = sub.add_parser("report")
    r.add_argument("--project", action="append", help="project key; repeat or comma-separate for several (default ATLASSIAN_PROJECT)")
    r.add_argument("--all-projects", action="store_true", help="explicitly search the whole site (no project filter)")
    r.add_argument("--label", default="AISDLC", help="label that marks gen-e2 epics and stories (default AISDLC)")
    r.add_argument("--month", help="calendar month YYYY-MM (default: last month)")
    r.add_argument("--from", dest="date_from", help="start date YYYY-MM-DD (inclusive)")
    r.add_argument("--to", dest="date_to", help="end date YYYY-MM-DD (inclusive)")
    r.add_argument("--metrics", help=f"comma-separated subset of {','.join(ALL_METRICS)} (default all)")
    r.add_argument("--todo-status", action="append", help="status name(s) that count as To Do, for metric 15 (default: auto-matched from the workflow)")
    r.add_argument("--review-status", action="append", help="story status name(s) that mean review, for the Review tables of metrics 1 and 2 (default: auto-matched)")
    r.add_argument("--in-progress-status", action="append", help="story status name(s) where work starts, for metric 2 (default: auto-matched from the workflow)")
    r.add_argument("--story-type", default="Story")
    r.add_argument("--epic-type", default="Epic")
    r.add_argument("--code", action="store_true",
                   help="add code metrics from Bitbucket commits and PRs linked to the stories (Jira development information)")
    r.add_argument("--code-app", default="bitbucket",
                   help="development tool type in Jira's development information (default bitbucket)")
    r.add_argument("--bitbucket", action=argparse.BooleanOptionalAction, default=None,
                   help="find each ticket's commits and check they update the story file and its task list "
                        "(default: on when BITBUCKET_TOKEN is set; --no-bitbucket to skip)")
    r.add_argument("--bb-repo", action="append", help="WORKSPACE/REPO to scan for commits; repeat or comma-separate")
    r.add_argument("--bb-workspace", action="append",
                   help="Bitbucket workspace whose repositories updated in the period are all scanned "
                        "(default BITBUCKET_WORKSPACE; needs only read:repository)")
    r.add_argument("--bb-source", choices=("auto", "jira", "scan"), default="auto",
                   help="find commits via Jira's development information or by scanning repositories (default auto)")
    r.add_argument("--stories-dir", default="docs/stories/", help="folder of gen-e2 story files (default docs/stories/)")
    r.add_argument("--format", choices=("md", "json"), default="md")
    r.add_argument("--out", help="write the report to this file instead of stdout")
    r.add_argument("--raw", help="write the raw data behind the report as JSON (default with --out: <out>.raw.json)")
    r.add_argument("--review-file", help="where to write story-file changes awaiting agent review "
                                         "(default with --out: <out>.review.json)")
    r.add_argument("--decisions", help="agent review decisions to apply and reuse "
                                       "(default with --out: gen-e2-review-decisions.json next to the report)")
    r.add_argument("--debug", action="store_true", help="log acli commands and changelog fetches to stderr")
    args = p.parse_args(argv)
    env_file = load_env(args.env_file)
    try:
        if args.cmd == "doctor":
            doctor(env_file)
        elif args.cmd == "statuses":
            fill_from_acli()
            statuses(args)
        elif args.cmd == "projects":
            projects_cmd(args)
        elif args.cmd == "bb-repos":
            fill_from_acli()
            bb_repos(args)
        else:
            fill_from_acli()
            report(args)
    except JiraError as e:
        raise SystemExit(f"error: {e}")


if __name__ == "__main__":
    main()
