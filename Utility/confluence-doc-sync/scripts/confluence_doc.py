#!/usr/bin/env python3
"""Read, create, and update Confluence Cloud spaces/pages.

Subcommands:
  get    --page-id ID | --url URL        print page title/version/body
  search --cql QUERY                     print matching pages (id, title, space)
  update --page-id ID --body-file FILE [--project KEY] [--label L ...] [--dry-run]
         replace the page body (Confluence storage-format HTML), bump version,
         and apply the gen-e2 + project labels (plus any extra --label values)
  label  --page-id ID [--project KEY] [--label L ...] [--dry-run]
         apply labels only, without touching the page body
  create-space --key KEY --name NAME [--description TEXT] [--dry-run]
         create a new Confluence space
  create-page --space KEY --title TITLE --body-file FILE [--parent-id ID]
              [--project KEY] [--label L ...] [--dry-run]
         create a new page in a space (optionally under a parent page) and
         apply the gen-e2 + project labels

Auth (env): CONFLUENCE_BASE_URL/EMAIL/API_TOKEN, falling back to
JIRA_BASE_URL (+ "/wiki")/JIRA_EMAIL/JIRA_API_TOKEN for a shared Atlassian site.
Standard library only.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def env(name, fallback_name=None, fallback_suffix=""):
    val = os.environ.get(name)
    if val:
        return val
    if fallback_name:
        fb = os.environ.get(fallback_name)
        if fb:
            return fb.rstrip("/") + fallback_suffix
    return None


class Confluence:
    def __init__(self):
        self.base = env("CONFLUENCE_BASE_URL", "JIRA_BASE_URL", "/wiki")
        email = env("CONFLUENCE_EMAIL", "JIRA_EMAIL")
        token = env("CONFLUENCE_API_TOKEN", "JIRA_API_TOKEN")
        missing = [n for n, v in (("CONFLUENCE_BASE_URL/JIRA_BASE_URL", self.base),
                                   ("CONFLUENCE_EMAIL/JIRA_EMAIL", email),
                                   ("CONFLUENCE_API_TOKEN/JIRA_API_TOKEN", token)) if not v]
        if missing:
            sys.exit(f"Missing env: {', '.join(missing)}")
        if not self.base.startswith("https://"):
            sys.exit("CONFLUENCE_BASE_URL must use https://")
        self.base = self.base.rstrip("/")
        cred = f"{email}:{token}".encode()
        self.auth = "Basic " + base64.b64encode(cred).decode()

    def call(self, method, path, body=None):
        req = urllib.request.Request(
            self.base + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": self.auth, "Accept": "application/json",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            sys.exit(f"Confluence {method} {path} failed: HTTP {e.code} "
                      f"{e.read().decode(errors='replace')[:500]}")


def page_id_from_url(url):
    m = re.search(r"/pages/(\d+)", url)
    if not m:
        sys.exit(f"Could not find a page ID in URL: {url}")
    return m.group(1)


def strip_html(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def get(args):
    cf = Confluence()
    page_id = args.page_id or page_id_from_url(args.url)
    data = cf.call("GET", f"/rest/api/content/{page_id}?expand=body.storage,version,space")
    body_html = data["body"]["storage"]["value"]
    print(json.dumps({
        "id": data["id"],
        "title": data["title"],
        "space": data["space"]["key"],
        "version": data["version"]["number"],
        "url": f"{cf.base}{data['_links']['webui']}" if "_links" in data else None,
        "body_text": strip_html(body_html),
        "body_html": body_html,
    }, indent=2))


def search(args):
    cf = Confluence()
    q = urllib.parse.quote(args.cql)
    data = cf.call("GET", f"/rest/api/content/search?cql={q}&limit=20")
    results = [{"id": r["id"], "title": r["title"], "type": r["type"]} for r in data.get("results", [])]
    print(json.dumps(results, indent=2))


def auto_labels(project):
    """gen-e2 is always applied; the project key (if given) is added as its own label."""
    labels = {"gen-e2"}
    if project:
        labels.add(project.lower())
    return labels


def apply_labels(cf, page_id, labels, dry_run):
    payload = [{"prefix": "global", "name": name} for name in sorted(labels)]
    if dry_run:
        print(json.dumps({"action": "label", "page_id": page_id, "payload": payload}, indent=2))
        return None
    return cf.call("POST", f"/rest/api/content/{page_id}/label", payload)


def update(args):
    cf = Confluence()
    current = cf.call("GET", f"/rest/api/content/{args.page_id}?expand=version,space")
    with open(args.body_file, encoding="utf-8") as f:
        new_body = f.read()
    next_version = current["version"]["number"] + 1
    payload = {
        "id": args.page_id,
        "type": "page",
        "title": current["title"],
        "space": {"key": current["space"]["key"]},
        "version": {"number": next_version},
        "body": {"storage": {"value": new_body, "representation": "storage"}},
    }
    labels = auto_labels(args.project) | set(args.label or [])
    if args.dry_run:
        print(json.dumps({"action": "update", "page_id": args.page_id,
                          "from_version": current["version"]["number"],
                          "to_version": next_version, "payload": payload,
                          "labels": sorted(labels)}, indent=2))
        apply_labels(cf, args.page_id, labels, dry_run=True)
        return
    result = cf.call("PUT", f"/rest/api/content/{args.page_id}", payload)
    apply_labels(cf, args.page_id, labels, dry_run=False)
    print(json.dumps({"id": result["id"], "version": result["version"]["number"],
                      "url": f"{cf.base}{result['_links']['webui']}",
                      "labels": sorted(labels)}, indent=2))


def label(args):
    cf = Confluence()
    labels = auto_labels(args.project) | set(args.label or [])
    result = apply_labels(cf, args.page_id, labels, dry_run=args.dry_run)
    if result is not None:
        print(json.dumps({"id": args.page_id, "labels": sorted(labels)}, indent=2))


def create_space(args):
    cf = Confluence()
    payload = {"key": args.key, "name": args.name,
               "description": {"plain": {"value": args.description or "", "representation": "plain"}}}
    if args.dry_run:
        print(json.dumps({"action": "create-space", "payload": payload}, indent=2))
        return
    result = cf.call("POST", "/rest/api/space", payload)
    print(json.dumps({"key": result["key"], "name": result["name"],
                      "url": f"{cf.base}{result['_links']['webui']}"}, indent=2))


def create_page(args):
    cf = Confluence()
    with open(args.body_file, encoding="utf-8") as f:
        body = f.read()
    payload = {
        "type": "page",
        "title": args.title,
        "space": {"key": args.space},
        "body": {"storage": {"value": body, "representation": "storage"}},
    }
    if args.parent_id:
        payload["ancestors"] = [{"id": args.parent_id}]
    labels = auto_labels(args.project) | set(args.label or [])
    if args.dry_run:
        print(json.dumps({"action": "create-page", "payload": payload,
                          "labels": sorted(labels)}, indent=2))
        return
    result = cf.call("POST", "/rest/api/content", payload)
    apply_labels(cf, result["id"], labels, dry_run=False)
    print(json.dumps({"id": result["id"], "title": result["title"],
                      "url": f"{cf.base}{result['_links']['webui']}",
                      "labels": sorted(labels)}, indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("get")
    grp = g.add_mutually_exclusive_group(required=True)
    grp.add_argument("--page-id")
    grp.add_argument("--url")

    s = sub.add_parser("search")
    s.add_argument("--cql", required=True)

    u = sub.add_parser("update")
    u.add_argument("--page-id", required=True)
    u.add_argument("--body-file", required=True)
    u.add_argument("--project", help="project key; added as a label alongside the automatic gen-e2 label")
    u.add_argument("--label", action="append", help="extra label, added on top of auto labels (gen-e2, project)")
    u.add_argument("--dry-run", action="store_true")

    l = sub.add_parser("label")
    l.add_argument("--page-id", required=True)
    l.add_argument("--project", help="project key; added as a label alongside the automatic gen-e2 label")
    l.add_argument("--label", action="append", help="extra label, added on top of auto labels (gen-e2, project)")
    l.add_argument("--dry-run", action="store_true")

    cs = sub.add_parser("create-space")
    cs.add_argument("--key", required=True)
    cs.add_argument("--name", required=True)
    cs.add_argument("--description")
    cs.add_argument("--dry-run", action="store_true")

    cp = sub.add_parser("create-page")
    cp.add_argument("--space", required=True)
    cp.add_argument("--title", required=True)
    cp.add_argument("--body-file", required=True)
    cp.add_argument("--parent-id")
    cp.add_argument("--project", help="project key; added as a label alongside the automatic gen-e2 label")
    cp.add_argument("--label", action="append", help="extra label, added on top of auto labels (gen-e2, project)")
    cp.add_argument("--dry-run", action="store_true")

    a = p.parse_args()
    {"get": get, "search": search, "update": update, "label": label,
     "create-space": create_space, "create-page": create_page}[a.cmd](a)


if __name__ == "__main__":
    main()
