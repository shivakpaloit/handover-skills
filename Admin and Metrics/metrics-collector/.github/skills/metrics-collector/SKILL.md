---
name: metrics-collector
description: Run, test, and debug the metrics-collector CLI (engineering metrics scorecard from Jira, Bamboo, Sonar, Fortify, Nexus IQ, ServiceNow, etc.). Use when asked to run the collector, check which metrics are runnable, verify a change, or diagnose a failing/empty metric, auth error, proxy or time-zone problem.
---

# metrics-collector: run, test, debug

Node ESM CLI (Node >= 22.19, deps: `dotenv`, `undici`). Entry: `src/index.js`. All config is env vars (see `.env.example`, `README.md`). No database, no scheduler. A small `npm test` suite (`node --test test/`, mock Jira server, no credentials) covers the epic-attachment PRD metrics; everything else is verified with static checks + `--check` + running individual metrics.

Never print or commit `.env` values (tokens). `.env` is gitignored; do not `cat` it, and when inspecting config show variable names only.

## Run

```bash
npm install                                   # first time
cp .env.example .env                          # then fill in tokens + scope (ask the user; don't invent)
npm run list                                  # all metric keys + required env vars
npm run check                                 # which metrics are runnable with current env (missing vars listed)
npm run dry-run                               # count-only preview: issues + API calls per Jira query (use before big runs)
npm run selftest                              # read-only connectivity/auth probe per configured tool, with fix hints (exit 1 on failure)
npm start                                     # all runnable metrics
METRICS=cycle_time,lead_time npm start        # subset
ENV_FILE=teams/payments.env npm start         # per-team env file
REPORT_FROM=2026-08-01 REPORT_TO=2026-10-31 METRICS=cycle_time npm start   # override window
```

Output: `output/<timestamp>/summary.json|csv` plus one `<metric>.csv` per metric. Exit code 0 = no metric errored, 1 = at least one `status: error`, 2 = unknown metric key.

Metrics with missing required env are skipped, not failed, so run `npm run check` first.

Must run from a machine that can reach the on-prem tools (Bamboo, SSC, IQ, Sonar).

## Test

Do these in order, cheapest first:

1. **Syntax/import check** of everything after an edit:
   `for f in $(find src -name '*.js'); do node --check "$f" || break; done`
2. **Connectivity**: `npm run selftest` (also catches missing `node_modules`, which silently skips `.env`).
3. **Startup check**: `npm run list` (loads all metric modules; catches bad imports/registration) and `npm run check`.
4. **Single-metric run** for the metric touched, with debug logging:
   `METRICS=<key> LOG_LEVEL=debug npm start`
5. **Inspect output**: open `output/<latest>/summary.json` and `<key>.csv`. Verify the number is reproducible from the CSV rows (that is the design intent: every number is auditable).
6. README says endpoints were smoke-tested against a **mock server only**. If no real credentials are available, say so, and don't claim a metric is verified against a real instance. If adding tests, use Node's built-in runner (`node --test`) and mock `fetch`/undici rather than adding a framework.

Highest-risk areas (most likely to need tweaks against real instances): QMetry (endpoint unverified), Nexus IQ metrics API, Bamboo response shapes, the scoped-Atlassian-token gateway path.

## Debug

Always start with `LOG_LEVEL=debug` and a single metric (`METRICS=<key>`); debug prints every URL/JQL. Source layout: `src/clients/*` (HTTP per tool), `src/lib/http.js` (requests, proxy, retries), `src/lib/config.js` (env parsing), `src/metrics/{delivery,requirements,security-stability}.js` (metric logic).

| Symptom | Likely cause / fix |
|---|---|
| Metric absent from summary | Required env missing. See `npm run check` "missing" column. |
| `Unknown metric(s)` (exit 2) | Typo in `METRICS`; use `npm run list`. |
| Jira 401/403 | Scoped token (default `ATLASSIAN_TOKEN_TYPE=scoped`) lacks a scope. The error names it (`read:jira-work`; Confluence needs `read:confluence-content.all`, `search:confluence`, `read:page:confluence`). Or account lacks Browse Projects. Try `ATLASSIAN_TOKEN_TYPE=classic` if the token is classic. |
| Jira 404/401 on `*.atlassian.net` with scoped token | Scoped tokens must use `api.atlassian.com/ex/jira/<cloudId>`. Check cloud ID lookup (`JIRA_BASE_URL/_edge/tenant_info`) or set `ATLASSIAN_CLOUD_ID`; proxy must allow `api.atlassian.com`. |
| Run fails when proxy set | `HTTPS_PROXY`/`HTTP_PROXY` set but `undici` not installed: `npm install`. Check `NO_PROXY` for internal hosts. |
| TLS / self-signed cert errors on internal tools | Set `NODE_EXTRA_CA_CERTS=/path/corp-root-ca.pem`. |
| Zero rows / odd counts | Window (`REPORT_FROM`/`REPORT_TO`, default last 90 days), scope filters too narrow, or time zone mismatch. Set `TZ` to the API user's zone (Jira JQL, ServiceNow dates). Paste the debug-logged JQL into Jira's issue search to compare. |
| Defect escape / regression empty or error | `JIRA_ESCAPED_DEFECT_JQL` / `JIRA_REGRESSION_JQL` convention doesn't exist in the instance. Single-quote values starting with `"` in `.env`. |
| Lead time empty | Bamboo builds don't reference Jira keys; check `BAMBOO_PROD_ENVIRONMENTS` names and `BAMBOO_JIRA_KEY_PREFIXES`; or switch `LEAD_TIME_MODE=fixversion`. |
| Fortify counts look high | "Removed" = not found in later scan (includes deleted code). Known caveat. |
| QMetry coverage 0% | By design: all test cases treated as critical, manual-only means 0%. Endpoint itself is unverified. |

Debug loop: reproduce with one metric + `LOG_LEVEL=debug` -> find the failing request in the log -> reproduce that request in isolation (curl with the token from the environment, not pasted into chat) -> fix in the matching `src/clients/*` or `src/metrics/*` file -> re-run steps 1-4 above. For HTTP-layer or env-parsing questions, read `src/lib/http.js` and `src/lib/config.js` first.

## Rules of thumb

- Don't run against production tools with broad scope unprompted. Confirm scope (`JIRA_SCOPE_JQL`, etc.) with the user; empty filter means "everything this token can see".
- `output/` can contain internal issue data; keep it out of commits.
