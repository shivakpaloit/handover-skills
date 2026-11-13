---
name: confluence-doc-sync
description: "Look up a Confluence page (PRD, design doc) by ID or URL and return its content, create a new space/page, or update an existing page's body. Read-only lookups need no confirmation; creates and updates require explicit confirmation. Use when the user asks to find, read, link, create, or update a PRD/requirements/design doc in Confluence."
---

# Confluence doc sync

This skill reads, creates, and updates Confluence Cloud spaces/pages. It does
not delete pages/spaces or manage permissions.

## When to use

- A story file's `[PRD](...)` link points to a Confluence page and the user wants
  its content pulled in (e.g. to resolve `BR-004` into full requirement text).
- The user wants to confirm a Jira issue's linked Confluence page is current.
- The user wants to push a small update to an existing page (e.g. append a note,
  update a status line).
- The user wants a brand-new space and/or page created for project docs (e.g.
  pushing a BRD or product-requirements doc that doesn't exist in Confluence yet).

## Auth

Confluence Cloud uses the same email + API token scheme as Jira Cloud. Env vars,
in priority order (each falls back to the Jira equivalent so one set of
credentials covers both services on the same Atlassian site):

| Var | Falls back to |
|---|---|
| `CONFLUENCE_BASE_URL` (e.g. `https://yoursite.atlassian.net/wiki`) | `JIRA_BASE_URL` + `/wiki` |
| `CONFLUENCE_EMAIL` | `JIRA_EMAIL` |
| `CONFLUENCE_API_TOKEN` | `JIRA_API_TOKEN` |

Never ask for, echo, or write the token.

## Commands

```sh
C=<skill>/scripts/confluence_doc.py
python3 $C get --page-id 123456                  # fetch a page by ID
python3 $C get --url "https://...atlassian.net/wiki/spaces/X/pages/123456/Title"
python3 $C search --cql 'space="PRD" and title~"Checkout"'
python3 $C update --page-id 123456 --body-file new-body.html --project PROJ --dry-run
python3 $C update --page-id 123456 --body-file new-body.html --project PROJ
python3 $C label --page-id 123456 --project PROJ --dry-run   # (re)apply labels only
python3 $C create-space --key PROJ --name "Project Docs" --description "..." --dry-run
python3 $C create-space --key PROJ --name "Project Docs"
python3 $C create-page --space PROJ --title "Business Requirements Document" \
  --body-file brd.html --project PROJ --dry-run
python3 $C create-page --space PROJ --title "Business Requirements Document" \
  --body-file brd.html --project PROJ
```

- `get` / `search` are read-only, no confirmation needed.
- `update` replaces the page body with the given file's contents (Confluence
  "storage format" HTML) and bumps the version. Always run `--dry-run` first and
  get explicit user confirmation before running without it — Confluence is a
  shared system.
- `create-space` creates a new space (key + name); `create-page` creates a new
  page in a space, optionally under `--parent-id`. Both are hard-to-reverse,
  shared-system actions: always run `--dry-run` first and get explicit user
  confirmation before running without it.
- Every page touched by `update`, `create-page`, or `label` automatically gets
  a `gen-e2` label plus the project key (lowercased, e.g. `proj`) as its own
  label, mirroring the `gen-e2`/`br-<id>` labels `jira-story-sync` applies to
  issues. Pass `--project` so the project label is included; use `--label` for
  any extra labels on top of the automatic ones. Ask the user for the project
  key if it's not already known from the story/issue being synced.

## Procedure

1. Resolve the page: prefer `--page-id` from a known link; use `search` with a
   CQL query if only a title/space is known. Report the match to the user before
   using it (titles can collide).
2. For `get`: print title, version, space, and body text (strip HTML tags for
   chat display unless the user wants raw storage format).
3. For `update`: show the current vs. proposed body diff, get explicit approval,
   then run without `--dry-run`. Report the new version number and page URL,
   and confirm which labels were applied.
4. For `create-space` / `create-page`: confirm the space key/name (or space +
   title + optional parent page) with the user, show the `--dry-run` payload,
   get explicit approval, then run without `--dry-run`. Report the new
   space/page key/id, URL, and applied labels.

## Limits

- No deletion, no permission changes.
- No macro-level editing — treat the body as opaque HTML; don't try to parse or
  rewrite Confluence macros.
- Converting markdown (e.g. a BRD/product-requirements doc from the repo) to
  Confluence storage-format HTML is the caller's responsibility before calling
  `create-page`/`update` with `--body-file`.

## Troubleshooting

- **401 on every Confluence endpoint, even `get`/`search`, while the same
  email+token works fine against the Jira REST API:** this does not mean the
  token is wrong. It usually means **Confluence isn't provisioned on the site
  at all** (common on Jira-only sites). An HTML response containing
  `"(null)"` / a null-null error page (instead of JSON) confirms this —
  Confluence needs to be added via https://admin.atlassian.com (Products ->
  Add product) before anything here will work. Verify with:
  `curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" "$CONFLUENCE_BASE_URL/rest/api/user/current"`
  — 200 + your identity means Confluence access is fine; 401 + HTML means it
  isn't provisioned/licensed for this account yet.
- **`acli jira auth status` shows `oauth_global`:** that only proves Jira
  OAuth works: it does **not** guarantee classic email+API-token Basic Auth
  (what this script uses) is enabled or that the account has Confluence
  access. Test Confluence auth independently rather than assuming it inherits
  from a working `acli`/Jira session.
- **`--dry-run` still fails on missing/invalid env vars:** the script builds
  the authenticated client before checking the dry-run flag, so dry-run is
  not a true no-credentials-needed preview — the env vars still must be set
  and valid even to preview a `create-space`/`create-page`/`update` payload.
- **Env vars set in one terminal tab don't appear in another:** each terminal
  session has its own process environment. If an agent runs the script in a
  different terminal than the one you exported variables in, it will see
  them as unset. Confirm you're exporting in the same session the commands
  actually run in — if unsure which terminal an agent's tool calls land in,
  have it print a one-off unique marker string and ask the user to find the
  matching terminal tab before exporting there.
- **If an API token is ever pasted into chat (by mistake or otherwise):**
  treat it as compromised immediately — don't use it for anything beyond
  finishing the task at hand, and tell the user to rotate/revoke it at
  https://id.atlassian.com/manage-profile/security/api-tokens as soon as
  possible, even if it still "works".
- Converting source markdown to Confluence storage-format HTML: the
  `python-markdown` library (`tables`, `fenced_code`, `sane_lists` extensions)
  produces valid storage-format HTML and has handled multi-hundred-KB
  documents without issue in practice — a reasonable default if the caller
  doesn't already have a converter.
