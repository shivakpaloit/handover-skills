# Handoff: metrics-collector

Written 2026-11-13 at the end of a long session. Read `README.md`, `AGENTS.md` and `.github/skills/metrics-collector/SKILL.md` first; this file covers what they don't: current state, decisions, and open items.

## What this is

Node ESM CLI (Node >= 22.19) that collects engineering metrics (Jira, Bamboo, SonarQube, Fortify, Nexus IQ, ServiceNow, Dynatrace, QMetry) into `output/<timestamp>/`. All config via env vars (`.env`, gitignored). Branch `main`, 11 commits, nothing pushed (no remote discussed).

## Commands

```
npm run selftest   # read-only connectivity/auth probe per configured tool, with fix hints
npm run dry-run    # count-only preview: issues + API calls per Jira query
npm run check      # which metrics are runnable with current env
npm test           # 9 tests (unit + mock Jira server); no credentials needed
METRICS=<key> LOG_LEVEL=debug npm start
```

If `node`/`npm` is "not found" in a shell, prefix `PATH=/opt/homebrew/bin:$PATH` (the PATH was missing it partway through the session).

## What was built this session

- Skill at `.github/skills/metrics-collector/` (real copy, for VS Code Copilot) with a symlink `.claude/skills/metrics-collector` -> it (for Claude Code). `AGENTS.md` added.
- `selftest`, `--dry-run`, progress logging (`PROGRESS_INTERVAL_MS`), `approximate-count` for Jira totals (`JIRA_EXACT_COUNTS=true` for exact).
- `docker-compose.yml`: SonarQube + Postgres (default) and Bamboo + Postgres (`--profile bamboo`, needs a free eval license). Works with `podman compose`.
- PRDs read from **markdown attachments on Jira epics** (`PRD_SOURCE=epic`, now the default): `src/lib/prd.js`, `epicPrds()` in `src/metrics/requirements.js`.
- `.gitignore` covers `.env*` (not `.env.example`), `teams/*.env`, `output/`, `node_modules/`.

## Decisions made

- **PRD source = epic attachments** (user's choice). Gen-e2 identified by the `aisdlc` label on the epic. Stories are children of the epic (`parent in (...)`). Start of PRD-to-story = first PRD upload (or `PRD_APPROVED_AT=status:X`). A re-upload of the same file name = a new version for acceptance; never re-uploaded = counted as accepted.
- **Bitbucket Cloud** was mentioned as a possible PRD source but **not built**. It would need a client, token and a file-to-epic mapping rule.
- Local test data lives in Jira project **AC** (shared, mostly auto-generated issues). `AC` has no `Story` type, so `.env` has `JIRA_STORY_TYPES=New Feature`; it has no "Found In" field, so `JIRA_ESCAPED_DEFECT_JQL=labels in (uat-defect, prod-defect)`; the start status is `WIP`, not "In Progress". These are specific to `AC`; revert for real projects.

## Current state of the environment

- `.env` (gitignored) is configured for Jira (`paloitsingapore.atlassian.net`, scoped token, `JIRA_SCOPE_JQL=project in (AC)`), window 2026-08-01 -> 2026-11-12, local SonarQube (`SONAR_URL=http://localhost:9000`, token and project key `metrics-collector`). Never print `.env` values. The local SonarQube admin password is recorded in a comment in `.env`. A backup of an earlier `.env` is in the old session scratchpad (may be gone).
- Test issues created in AC: `AC-79`..`AC-89`, all labelled `metrics-test` (6 `New Feature` stories, 5 bugs). Remove with JQL `labels = metrics-test`.
- SonarQube containers are still running in Podman (`podman compose down` to stop, `-v` to delete data). The Podman VM was raised from 2 to 4 GiB (SonarQube was OOM-killed at 2 GiB). The compose healthcheck shows "unhealthy" although the API answers UP; not investigated.
- The scanner container image is amd64-only and hangs on Apple Silicon; scan natively: `SONAR_TOKEN=... npx --yes @sonar/scan -Dsonar.host.url=http://localhost:9000 -Dsonar.projectKey=metrics-collector -Dsonar.sources=src`.
- `src/lib/util.js` has an **uncommitted change that is not ours** (5 insertions, 3 deletions). Ask the user before touching or committing it.

## Last verified results (AC, window to 2026-11-12)

cycle_time 0.01 days (8 rows); defect_escape_rate 5.45 %; gene2_story_rate 50 %; sonar_maintainability A; regression_defects n/a (the one regression-labelled bug has no affected/fix version). Epic PRD metrics return 0 rows on AC (no epic has an attachment) and are only verified against the mock server in `test/epic-flow.test.js`.

## Open items / next steps

1. **Validate the epic PRD metrics on real data.** The Jira token is read-only and `acli` can't upload attachments, so attach a `.md` to an `AC` epic (UI) with label `aisdlc`, then run `METRICS=gene2_prd_rate,prd_to_story_lead_time,gene2_acceptance_rate`. Scoped tokens probably also need `read:attachment:jira` (attachment content download is untested against real Jira; it follows a redirect).
2. **Unverified against real instances:** Bamboo (lead_time), Fortify, Nexus IQ, ServiceNow, Dynatrace, QMetry endpoints. No local stand-ins exist for these; `selftest` is the first step once credentials are set.
3. **Scale:** only tested at ~90 issues. `--dry-run` estimates calls; the slowest paths for thousands of tickets are per-story remote links (Confluence mode only) and attachment downloads (up to 2 per Gen-e2 epic). An optional on-disk changelog cache was proposed but not built.
4. `regression_defects` needs affected/fix versions set on bugs to produce a value.
5. Decide what to do about `src/lib/util.js` and whether to push the repo anywhere.
6. Skills/instructions work in VS Code Copilot per the docs but were not verified inside VS Code (agent mode; check the skills setting and VS Code version if `/metrics-collector` doesn't appear).
