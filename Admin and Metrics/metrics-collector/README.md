# metrics-collector

A one-off, ad-hoc collector for the engineering metrics scorecard. Every setting comes from environment variables. There's no database and no scheduler: you run it, and it writes a summary plus one CSV per metric so every number can be audited.

```
npm install
cp .env.example .env        # fill in tokens + scope
npm run check               # which metrics are runnable with the current env
npm run dry-run             # how many Jira issues each metric would fetch (counts only; nothing fetched)
npm test                    # unit + mock-server tests (no credentials needed)
npm run selftest            # one read-only request per configured tool: is auth/connectivity working?
npm start                   # or: METRICS=cycle_time,lead_time npm start
```

Output goes to `output/<timestamp>/`:
- `summary.json` / `summary.csv`: one row per metric (value, unit, status, and the breakdown).
- `<metric>.csv`: the underlying rows (issues, deployments, findings, incidents) behind each number.

Requires Node 22.19+. Proxies: set `HTTPS_PROXY` / `HTTP_PROXY` and `NO_PROXY`. They are honoured through `undici`, and the run fails if a proxy is set but `undici` isn't installed. Run it from a machine that can reach the on-prem tools (Bamboo, SSC, IQ, SonarQube). Set `NODE_EXTRA_CA_CERTS` if your internal tools use a corporate CA.

### TLS-inspecting proxies and internal CAs

If a proxy re-signs HTTPS traffic (Zscaler, Netskope and similar), requests fail with errors like `unable to get local issuer certificate` or `self-signed certificate in certificate chain`.

- **Trust the proxy's CA (recommended).** Export the proxy's root CA as PEM and set `NODE_EXTRA_CA_CERTS=/path/to/corp-root-ca.pem` in `.env` or your shell. Node adds it to its built-in CAs, so certificate checking stays on. To get the PEM, export the root from the macOS Keychain, or run `openssl s_client -showcerts -connect host:443` and take the last certificate in the chain.
- **Disable verification (not recommended).** `NODE_TLS_REJECT_UNAUTHORIZED=0` turns off certificate checking for every request, including those that carry your Jira, Sonar and other tokens, and Node prints a warning. Use it only to confirm a certificate is the cause, and never on a shared or production machine. It has not been tested on the `undici` proxy path.

## Local test tools (Docker)

`docker-compose.yml` runs local stand-ins so you can exercise the collector without touching real instances:

```
docker compose up -d                    # SonarQube + Postgres  -> http://localhost:9000
docker compose --profile bamboo up -d   # also Bamboo + Postgres -> http://localhost:8085 (needs a free 30-day eval license)
```

**SonarQube** (give the container VM at least 4 GiB; with 2 GiB it is OOM-killed): log in at http://localhost:9000 as `admin` / `admin` (you must change the password), then create a token and analyse this repo with the scanner (run natively: the official scanner container image is amd64-only and hangs under emulation on Apple Silicon):

```
curl -s -u admin:<new-password> -X POST "http://localhost:9000/api/user_tokens/generate" -d name=collector   # prints the token
SONAR_TOKEN=<token> npx --yes @sonar/scan -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.projectKey=metrics-collector -Dsonar.sources=src
```

Then set `SONAR_URL=http://localhost:9000`, `SONAR_TOKEN=<token>`, `SONAR_PROJECT_KEYS=metrics-collector` and run `npm run selftest` and `METRICS=sonar_maintainability npm start`. The metric compares the start and end of the report window, so a project analysed only once gives a single data point.

**Bamboo**: finish the setup wizard with the external Postgres (host `bamboo-db`, db/user/password `bamboo`), create a personal access token, set `BAMBOO_URL=http://localhost:8085` and `BAMBOO_TOKEN`. Lead time needs production deployment projects whose builds reference Jira keys.

Fortify SSC, Nexus IQ, ServiceNow, Dynatrace and QMetry have no free self-hosted image, so test those against real instances (ServiceNow offers a free personal developer instance).

## Metrics

| Key | Metric | Source | Notes |
|---|---|---|---|
| `lead_time` | Lead Time for Change | Jira + Bamboo | `LEAD_TIME_MODE=bamboo`: start (created, or `status:X`) to the first successful prod deployment whose build(s) reference the issue. Builds between two prod deployments are attributed to the later one. `fixversion` mode uses the fixVersion release date as a proxy. Also reports deployments per week. |
| `cycle_time` | Cycle Time | Jira | First move into `JIRA_START_STATUSES` to the last move into `JIRA_DONE_STATUSES` within the window. Reports mean, median and p85. |
| `defect_escape_rate` | Defect Escape Rate | Jira | Defects matching `JIRA_ESCAPED_DEFECT_JQL` ÷ all defects created in the window. |
| `sonar_maintainability` | Maintainability Rating | SonarQube | Rating and debt ratio at the start and end of the window per project, plus a trend. |
| `regression_defects` | Regression Defects / Release | Jira | Defects matching `JIRA_REGRESSION_JQL`, grouped by affected version or fix version. |
| `critical_path_coverage` | Automated Critical Path Coverage | QMetry | All test cases in the configured project count as critical; manual-only testing means automated coverage is 0%. **The endpoint is unverified**, so check it against your QMetry edition. |
| `fortify_critical` | Critical Fortify Findings | Fortify SSC | Critical/High issues open at `REPORT_TO`, reconstructed from found/removed dates. Also reports issues opened at the start and introduced during the window. |
| `vuln_mttr` | MTTR Vulnerabilities | Fortify SSC | Found date to removed date for Critical/High issues removed in the window. |
| `nexus_vulnerable_components` | Vulnerable Components Introduced | Nexus IQ | New security violations from the IQ metrics API, in monthly buckets. |
| `nexus_policy_violations` | Policy Violations | Nexus IQ | New violations across all policy categories, plus the count open at the end. |
| `change_failure_rate` | Change Failure Rate | ServiceNow | Closed changes where `close_code` is in `SNOW_FAILED_CLOSE_CODES`, or where an incident's `caused_by` points at the change. |
| `mttr` | MTTR | ServiceNow | `SNOW_INCIDENT_START_FIELD` to `SNOW_INCIDENT_END_FIELD`, filtered by `SNOW_INCIDENT_QUERY`. |
| `mttr_dynatrace` | MTTR (Dynatrace view) | Dynatrace | Problem start to end time. Optional cross-check. |
| `gene2_prd_rate` | Gen-e2 PRD Rate | Jira (epic attachments), or Confluence / JPD | Default `PRD_SOURCE=epic`: the PRD is a markdown attachment on a Jira epic (`PRD_ATTACHMENT_PATTERN`, default any `.md`), counted by its first upload date in the window. Epics matching `GENE2_JIRA_JQL` (label `aisdlc`) ÷ all epics with a PRD. |
| `gene2_story_rate` | Gen-e2 Story Rate | Jira | Stories matching `GENE2_JIRA_JQL` ÷ all stories created. |
| `prd_to_story_lead_time` | PRD-to-Story Lead Time | Jira (epics + child stories), or JPD / Confluence | Epic mode: first PRD upload (or `PRD_APPROVED_AT=status:X` on the epic) to the creation of the epic's first child story. JPD mode: idea approved to the first linked story. Confluence mode: page created to the first story linked through a remote link. |
| `gene2_acceptance_rate` | Gen-e2 Acceptance Rate | Jira (+ epic attachments / Confluence) | Text similarity between the first and current version. For epic PRDs, a re-upload of the same file name counts as a new version (first upload vs latest); a PRD never re-uploaded counts as accepted. Accepted when similarity ≥ `GENE2_ACCEPT_THRESHOLD` (default 0.8). |

## Scope ("flexible")

Each tool is scoped by its own native filter, so you can change scope without changing code:

- **Jira**: `JIRA_SCOPE_JQL`, any JQL, such as `project in (ABC, DEF)` or `"Team[Team]" = 123`.
- **Bamboo**: `BAMBOO_DEPLOY_PROJECTS` and `BAMBOO_PROD_ENVIRONMENTS`.
- **SonarQube**: `SONAR_PROJECT_KEYS` or `SONAR_PROJECT_SEARCH`.
- **Fortify**: `FORTIFY_APPLICATIONS` (`App` or `App:Version`) or `FORTIFY_VERSION_IDS`.
- **Nexus IQ**: `NEXUSIQ_APPLICATIONS` or `NEXUSIQ_ORGANIZATIONS`.
- **ServiceNow**: `SNOW_CHANGE_QUERY` and `SNOW_INCIDENT_QUERY` (encoded queries, e.g. assignment group or CMDB CI).

Leaving a filter empty means "everything this token can see".

To report per team, keep one env file per team and run with `ENV_FILE=teams/payments.env npm start`.

## Conventions that must exist first

| Metric | Needs |
|---|---|
| Defect Escape Rate | A field or label on bugs that says where the defect was found (UAT or Prod) → `JIRA_ESCAPED_DEFECT_JQL`. |
| Regression Defects | A `regression` label or root-cause value, and bugs linked to an affected version or fix version. |
| Critical Path Coverage | All QMetry test cases in the configured project are treated as critical. Testing is manual-only, so automated coverage is 0%. |
| Change Failure Rate | Consistent ServiceNow close codes, and/or incidents linked to the change that caused them through `caused_by`. |
| Gen-e2 metrics | Gen-e2 output tagged at creation: Jira label `aisdlc` on the epic and its stories (Confluence label `aisdlc` if you use Confluence). Ideally Gen-e2 applies these automatically. The acceptance rate also assumes the Gen-e2 draft is the first saved version. |
| PRD-to-Story | Epic mode: the PRD markdown attached to the epic, and stories as children of that epic. Otherwise an approval moment (a JPD status, or the page creation date as a proxy) and stories linked to their PRD. |

## Token permissions (read-only is enough)

| Tool | Token |
|---|---|
| Jira Cloud | **Scoped** API token (`JIRA_EMAIL` + `JIRA_API_TOKEN`; the default, `ATLASSIAN_TOKEN_TYPE=scoped`) with the **`read:jira-work`** scope (classic scope; it covers JQL search, bulk fetch, changelogs and remote links). If you create granular scopes instead, you need the read scopes for issues, issue changelogs and issue remote links (e.g. `read:issue:jira`, `read:issue.changelog:jira`, `read:issue.remote-link:jira`, `read:project:jira`, `read:user:jira`). The token's account also needs **Browse Projects** on every project in `JIRA_SCOPE_JQL` (and on the JPD ideas project if `PRD_SOURCE=jpd`). Scopes limit what the token can call, but the account's own permissions still decide which projects it can see. |
| Confluence Cloud | Same token, with **`read:confluence-content.all`** and **`search:confluence`** (classic scopes). The page-body call uses the v2 API, so also add **`read:page:confluence`**. The account needs **View** on the space(s) in `CONFLUENCE_PRD_CQL`. Only the Gen-e2 PRD metrics use it. |
| Bamboo | Personal access token for an account with **View** on the deployment projects and on the build plans they deploy. The build plan view is needed to read each build's linked Jira issues and commit messages. |
| Bitbucket | Not used. Build and deployment data comes from Bamboo. |
| SonarQube | User token with Browse on the projects. |
| Fortify SSC | A token type allowed to read issues, e.g. `UnifiedLoginToken`. Use the encoded token value. |
| Nexus IQ | User token (code and passcode) with view access to the apps/orgs. |
| ServiceNow | A user with read on `change_request` and `incident` (e.g. `itil`), or an OAuth token. |
| Dynatrace | API token with the `problems.read` scope. |

The epic PRD metrics download attachments, so a scoped token also needs **`read:attachment:jira`** (`read:jira-work` alone may not cover attachment content), and the account needs permission to view attachments. Confluence permissions are only needed if `PRD_SOURCE=confluence`.

**Scoped tokens and the gateway.** Scoped tokens do not work against `https://yourco.atlassian.net`. They must call `https://api.atlassian.com/ex/jira/<cloudId>/...` (and `/ex/confluence/<cloudId>/wiki/...`), authenticated with the same email and token. The collector does this automatically by default. Set `ATLASSIAN_TOKEN_TYPE=classic` to call the site URL directly instead. It looks the cloud ID up from `JIRA_BASE_URL/_edge/tenant_info` (a public endpoint) or reads `ATLASSIAN_CLOUD_ID` if you set it. The cloud-ID lookup and the gateway calls both go through `HTTPS_PROXY`. The proxy must allow `api.atlassian.com`. The scope names above are from Atlassian's docs and the gateway path has not been tested against a real tenant, so check them first with `METRICS=cycle_time LOG_LEVEL=debug npm start`. A 401 or 403 with a scope message names the missing scope.

**Scope the account, not just the query.** Leaving `JIRA_SCOPE_JQL` empty means "everything this account can see". Grant the service account access only to the projects and spaces you want measured.

## Large runs

Long Jira loops (issue search, bulk fetch, changelogs, remote links) log progress at `info` level, for example `Jira changelogs: 3000/8000 (37%) [42s]`, at most every `PROGRESS_INTERVAL_MS` (default 5000; `0` logs every batch). Jobs that finish quickly stay silent. `npm run dry-run` (`--dry-run`) shows, before you commit to a long run, how many issues each Jira query matches and roughly how many API calls it needs. It makes only count calls; metrics that depend on other tools are reported as not estimated. Totals and rate denominators use Jira's `approximate-count` (one cheap call, which can be slightly off on very large result sets); set `JIRA_EXACT_COUNTS=true` to count exactly by paging keys. To keep big runs manageable, narrow `JIRA_SCOPE_JQL` and the report window, run one metric at a time (`METRICS=<key>`), and raise `HTTP_CONCURRENCY` gradually.

## Caveats

- Endpoints were smoke-tested against a mock server only, not against your real instances. Run each metric on its own first with `LOG_LEVEL=debug`. The QMetry, Nexus IQ metrics and Bamboo response shapes are the most likely to need small tweaks.
- Jira JQL and ServiceNow `gs.dateGenerate` dates are evaluated in the API user's time zone. Set `TZ` to the same zone.
- Fortify "removed" means "not found in a later scan", which includes deleted code.
