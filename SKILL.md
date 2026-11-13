---
name: jira-gen-e2-metrics
description: "Measure Gen-e2 (AI-SDLC) adoption and delivery metrics from Jira with the Atlassian CLI (acli), comparing epics and stories labelled AISDLC against the rest: (1) completion and lead time of stories created in the period (% Done / in Review, creation to Review and to Done, age of unfinished stories), (2) average cycle time from In Progress to Review and to Done, (13) epics with active stories in the period, gen-e2 vs not, (14) % of stories created with gen-e2, (15) time from epic creation to first story in To Do, (16) rate of BRD rework (edits to the epic description and attachments), and Bitbucket checks (on when a Bitbucket token is configured): whether each story's commits update its gen-e2 story file and task list, plus optional code metrics. Use when asked for gen-e2, AISDLC, or AI-SDLC metrics, lead or cycle time, epic or story adoption counts, BRD rework, commits or pull requests per ticket, whether engineers follow gen-e2, or a monthly Jira delivery report."
argument-hint: "Jira project key(s) (asked for if missing), optional month (YYYY-MM) or date range, metric numbers, To Do / In Progress / Review status names"
---

# Jira Gen-e2 Metrics

Computes six delivery metrics for a period, split into two cohorts:

- **gen-e2**: issues with the Jira label `AISDLC`, set on both the Epic and its Stories.
- **other**: issues without that label.

`scripts/gen_e2_metrics.py` (Python 3.9+, standard library only) splits the work between
**acli** and the Jira REST API, using the same Atlassian API token for both. Nothing is written to Jira.

- **acli** handles login, counts (`acli jira workitem search --count`, for metric 14) and project listing. The site and email for REST also come from the acli login, so the only extra setting is the API token.
- **REST** returns issue lists with dates and parent (`POST /rest/api/3/search/jql`, 100 per call) and change history. Two acli gaps make this necessary: `acli workitem search` only returns display fields (key, summary, status, labels, issue type, assignee, priority, reporter, description), not `created`, `resolutiondate`, `statuscategorychangedate` or `parent`; and acli has no changelog command.
- Without REST credentials, metric 1 falls back to `acli workitem view` per issue (about 2–3 s each) and skips its creation → Review times, and metrics 2, 15 and 16 are skipped.

| History | Issues | Fields read | Used by |
|---|---|---|---|
| Story | Stories created in the period, stories active in the period, stories done in the period, stories created before the period ended and updated since it began (Review candidates), and child stories of epics created in the period | `status` | 1, 2, 13, 15 |
| Epic (BRD/PRD) | Epics created in the period | `description`, `attachment` | 16 |

Each batch is fetched once per run with `POST /rest/api/3/changelog/bulkfetch` (up to 1000
issues per call). The request is not filtered by field ID, because history created by Jira's importers has no field IDs; the script filters by field name instead. A typical run makes only a few REST calls. The BRD/PRD lives on the epic,
so story descriptions and attachments are never read. If the bulk call is rejected, or an issue
has no ID, the script falls back to `GET /rest/api/3/issue/{key}/changelog` one
issue at a time and says so under **Notes**.

Intended scope: up to about 10 projects and one month per run.

| # | Metric | Source |
|---|---|---|
| 1 | Stories created in the period: % Done and % Done or in Review, average time from creation to Review and to Done, and the age and status of stories not yet Done or in Review | REST search + history (counts and → Done also work with acli view fallback) |
| 2 | Average time from In Progress to Review, and to Done (cycle time) | REST search + history |
| 13 | Epics with active stories in the period, gen-e2 vs not (by the epic's label) | REST search + story history (approximate without history) |
| 14 | % of stories created in the period with gen-e2 | acli counts |
| 15 | Time between epic creation and first story in To Do | REST search + history |
| 16 | Rate of BRD rework (epic `description` and `Attachment` edits) | REST search + history |

Exact definitions are in [references/metrics.md](references/metrics.md). Read it before
explaining or interpreting the numbers. [references/sample-report.md](references/sample-report.md)
shows the report format, generated from synthetic data. For the optional code metrics
(`--code`), read [references/code-metrics.md](references/code-metrics.md) before running or explaining them.
For the Bitbucket checks (`--bitbucket`), read [references/bitbucket-checks.md](references/bitbucket-checks.md).

`S` below is `scripts/gen_e2_metrics.py` in this skill folder.

## Phase 1: Ask which projects to check

**Always ask this first, before running anything else.** Never assume a project, and never
search the whole site without the user saying so.

- If the user already named project keys in their request, confirm them back and continue.
- Otherwise ask for the Jira project key(s), for example `MKT` or `MKT, OPS`. If `ATLASSIAN_PROJECT` is set, offer it as the default, but still ask.
- If the user doesn't know the keys, run Phase 2 first, then list the projects:

  ```bash
  python3 S projects
  ```

  This lists the projects visible to the user, ranked by how many `AISDLC`-labelled issues they had in the last 180 days (`--days` to change). Show the top results as choices.

Pass the confirmed keys as `--project` to every later command (repeat the flag or comma-separate the keys).
`statuses` and `report` refuse to run without `--project` or `ATLASSIAN_PROJECT`.

**Bitbucket.** The Bitbucket checks run by default when `BITBUCKET_TOKEN` is set (check with `doctor` in
Phase 2). The script finds each ticket's commits itself by matching ticket keys in commit messages; it only
needs to know which workspace to search. Don't ask for repositories:
- If `doctor` shows `BITBUCKET_WORKSPACE` or `BITBUCKET_REPOS` set, or `repository_discovery: true`, ask nothing.
- Otherwise ask once for the Bitbucket **workspace** name (from `bitbucket.org/<workspace>/`), pass it as
  `--bb-workspace`, and suggest adding `BITBUCKET_WORKSPACE=<workspace>` to `.env` so it isn't asked again.
  Every repository in the workspace updated in the period is searched.
- Use `--bb-repo` / `BITBUCKET_REPOS` only if the user wants to limit the search to specific repositories.
If the user doesn't know them and `doctor` shows `repository_discovery: true`, list them with `python3 S bb-repos`
and offer the results as choices. Skip the question only if the user doesn't want the Bitbucket checks (then pass
`--no-bitbucket`) or no Bitbucket token is configured.

## Phase 2: Check setup

```bash
python3 S doctor
```

The output is JSON and never contains secrets. It looks for variables in the environment
first, then in the nearest `.env` up to the repo root (or `--env-file`).

1. **`searches_ready: false`**: acli is missing or not logged in. All metrics need it.
   - Not installed: show the `acli_install` commands and let the user run them, or run them only after explicit approval.
   - Not logged in: the user runs `acli jira auth login --web` in their own terminal, or logs in with a token (see `acli_login`).
2. **`changelog_ready: false`**: only the API token is missing. The site and email are read from the acli login (`"from acli login"` in `env`). Don't offer to run without it: acli can't return dates, parent links or change history, so only metric 14 would be complete.

   Ask the user to add one line to a git-ignored `.env` in the repo root (`.env*` is in `.gitignore`):

   ```bash
   ATLASSIAN_TOKEN=<API token>   # or JIRA_TOKEN=<API token>
   ```

   This is the same token acli was logged in with (id.atlassian.com > Security > API tokens). The VS Code agent doesn't load `~/.zshrc`, so a token exported there isn't visible; `.env` is. Never ask the user to paste the token into chat. Optional: `ATLASSIAN_PROJECT=KEY1,KEY2` as the default project, and `ATLASSIAN_URL` / `ATLASSIAN_EMAIL` to override the acli login.

Never print, echo or commit token values.

## Phase 3: Match the workflow statuses

Metrics 1, 2, 13 and 15 depend on status names, which differ between projects. Discover them; don't guess:

```bash
python3 S statuses --project MKT
```

The output lists the Story and Epic statuses with their Jira status category (`new` = To Do,
`indeterminate` = In Progress, `done` = Done). It also includes a `suggested` mapping and the reason for it.
With `ATLASSIAN_*` set, it reads the full workflow over REST. Otherwise it reads the statuses
currently in use through acli, which can miss statuses that no issue is in right now.

Review the suggestion yourself before using it:

- **In Progress** (`--in-progress-status`, metric 2): every story status in the In Progress category. Work starts the first time a story enters any of them, so include review and test statuses too.
- **Review** (`--review-status`, metric 1's In Review count and the Review tables of metrics 1 and 2): the In Progress-category story status or statuses that mean the work is in review, for example `In Review`, `Code Review`, `QA` or `Testing`. If none match, the Review tables are skipped, no story counts as In Review, and Notes says so.
- **To Do** (`--todo-status`, metric 15): the status or statuses where a story is committed and ready to be worked on. Examples are `To Do`, `Selected for Development` and `Ready`. Leave out pre-commitment statuses such as Backlog, Draft or Triage, even though they are also in the To Do category.

Show the user a short table (concept, matched statuses, reason) and confirm it, or adjust it with
them. Then pass the confirmed names explicitly in Phase 5. If you run `report` without these
flags, it matches automatically using the same rules and records the result under **Notes**.

## Phase 4: Confirm the other inputs

Use defaults for anything the user did not specify, and state which defaults you used:

| Input | Flag | Default |
|---|---|---|
| Period | `--month YYYY-MM` or `--from YYYY-MM-DD --to YYYY-MM-DD` | last calendar month |
| Gen-e2 label | `--label` | `AISDLC` |
| Metrics | `--metrics 1,2,13,14,15,16` | all |
| Issue type names | `--story-type`, `--epic-type` | `Story`, `Epic` |
| Bitbucket checks: commits updating the story file and task list | `--bitbucket` / `--no-bitbucket` (`--bb-repo`, `--bb-source`, `--stories-dir`) | **on** when `BITBUCKET_TOKEN` is set, using the repositories confirmed in Phase 1 (`--bb-repo`). Notes say so when they're skipped because no token is configured. |
| Code metrics (Bitbucket) | `--code` | off. Offer it when the user asks about commits, pull requests or repositories, or wants code-side cycle time. It needs Bitbucket connected to Jira; no repository list or extra token. |

## Phase 5: Run the report

```bash
python3 S report --project MKT --month 2026-10 \
  --todo-status "Selected for Development" --in-progress-status "In Development" --in-progress-status "Code Review" \
  --review-status "Code Review" \
  --bb-repo acme/payments-api,acme/payments-web \
  --out docs/metrics/gen-e2-metrics-2026-10.md
```

- Save to `docs/metrics/gen-e2-metrics-<period>.md` unless the user names another path, or print to stdout if they only want the numbers.
- Use `--format json` for data that feeds a dashboard or spreadsheet.
- If Notes say story-file changes are waiting for review, open the review file named there, decide each item as its instructions say (task progress yes/no, tasks ticked, one-line reason; skip items you can't judge), add the decisions to the decisions file, and rerun the same command. Don't change the parser's results by hand. See [references/bitbucket-checks.md](references/bitbucket-checks.md).
- With `--out`, the raw data behind the report is also written as JSON next to it (`<out>.raw.json`; `--raw PATH` to choose the path, or to write it without `--out`). It holds every search with the issue keys or count it returned and the metrics that used it, a snapshot of each issue's fields, the status / description / attachment / label history used (descriptions as lengths only, never their text), and, with `--code` / `--bitbucket`, every linked commit with its checks. Use it to answer "which stories were counted?" and to audit a number.
- Progress messages go to stderr. Metrics 2, 15 and 16 make one changelog call per story or epic, so large projects take a while. Run one metric at a time with `--metrics` to test.
- With `--code`, the report makes two extra calls per Done story with linked code and lists the repositories it found.
- If a search fails or returns odd results, re-run with `--debug` to see each acli command and changelog fetch.

## Phase 6: Report back

Summarize the headline numbers for each metric (gen-e2 vs other) in a short table, link
the saved report and its raw-data file, and call out:

- The projects checked (from Phase 1) and the status mapping used (from Phase 3).
- Any **Notes** in the report (skipped metrics, missing project filter, errors).
- Small samples: an average over fewer than about 5 issues is not meaningful.
- Metric 1 completion (% Done, % Done or in Review) and the stories not yet Done or in Review: how many, how old, and which statuses they sit in. Status is as of the report run, so a recent period always looks less complete.
- Excluded issues: stories never In Progress (metric 2) and epics with no story in To Do yet (metric 15).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `acli not found` | Install acli or set `ACLI_PATH` to the binary. |
| Code metrics: "no Done story has linked commits" | Bitbucket isn't connected to this Jira site, or commits, branches and PR titles don't mention ticket keys. A Jira admin connects the workspace; see [references/code-metrics.md](references/code-metrics.md). |
| `Bitbucket needs BITBUCKET_TOKEN` | Ask the user to create an API token with Bitbucket scopes and add `BITBUCKET_TOKEN=` to `.env`; the Jira token won't work for Bitbucket. |
| `the token can't list workspaces` | Set `BITBUCKET_WORKSPACE=<workspace>` in `.env` (or pass `--bb-workspace`), or add `read:workspace` to the token. `doctor` lists the token's scopes. |
| Bitbucket: "no commits found for the tickets" | Commit messages don't mention ticket keys, or the wrong repositories were scanned. Check with `bb-repos` and `--bb-repo`. |
| Code metrics need review times or lines changed | Not in Jira's development information. They need Bitbucket's own API and a token with Bitbucket scopes (not yet supported by the script). |
| `acli workitem: … unauthorized` | `acli jira auth login --web`, then `doctor` again. |
| `acli search returned non-JSON output` | Update acli (`brew upgrade acli`); the script needs `workitem search --json`. |
| JQL error on `statusCategoryChangedDate` (Jira Server/Data Center) | This skill targets Jira Cloud. |
| Imported or migrated issues show empty tables | Status changes are read from each issue's history rather than JQL `CHANGED … DURING`, which doesn't see imported history, so this should not happen with REST set up. Without REST, metric 13 is approximate (any story updated in the period counts as active). |
| JQL error on `parent in` | Old company-managed project: replace `parent` with `"Epic Link"` in `children_of` in the script. |
| Metric 13 is 0 for both cohorts | No story was in an In Progress or Review status in the period: check the In Progress statuses with `statuses` and pass `--in-progress-status`. |
| Metric 2 has many `excluded never in progress` | Stories skip In Progress (To Do straight to Done), or an In Progress status is missing from `--in-progress-status`. |
| `no project selected` | Ask the user for project keys (Phase 1) and pass `--project`. |
| `Bulk history fetch unavailable` in Notes | Results are still correct, but slower. Re-run with `--debug` to see the bulk request and the error. |
| `field 'created' is not allowed` from acli | acli search can't return dates; set the `ATLASSIAN_*` variables so the script uses REST search. |
| `HTTP 401/403` on changelog | Check `ATLASSIAN_EMAIL` and `ATLASSIAN_TOKEN`, and that the account can browse the project. |

## Tests

```bash
python3 -m unittest discover -s .github/skills/jira-gen-e2-metrics/scripts -p "test_*.py"
```

The tests use a fake acli binary and a fake changelog. They make no network calls.
