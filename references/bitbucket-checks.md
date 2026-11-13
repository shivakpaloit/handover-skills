# Bitbucket checks: are commits following gen-e2?

Optional section of the report, added with `report --bitbucket`. For each story in the period it finds
the story's commits, then checks whether those commits update the gen-e2 story file and its task list.
This is the repository-side evidence that developers work through the gen-e2 plan: the implementer
agent ticks the plan's tasks (`- [ ] T-01 …` → `- [x] T-01 …`) in `docs/stories/NN-slug.md` as it
implements them.

## Setup

- **`BITBUCKET_TOKEN`** in the environment or the git-ignored `.env`: an Atlassian API token created
  with **Create API token with scopes**, app **Bitbucket**, with read access to repositories and pull
  requests. The normal Jira token is rejected by Bitbucket ("API Token provided has no Bitbucket scopes").
  The account email comes from `ATLASSIAN_EMAIL` or the acli login (`BITBUCKET_EMAIL` overrides it).
- **Scopes:** `read:repository` is required. `read:workspace` is optional: it lets the skill find the
  workspaces itself. Without it, set **`BITBUCKET_WORKSPACE`** in `.env` (or pass `--bb-workspace`); the
  skill can then list that workspace's repositories with `read:repository` alone. No write scopes are needed.
- `python3 S doctor` shows `"bitbucket": {"ready": true, "repository_discovery": …, "scopes": […], "missing_scopes": […]}`.
  It works out the token's scopes from Bitbucket's response, so it needs no extra scope itself.

## Finding each story's commits (`--bb-source`)

| Source | When | How |
|---|---|---|
| `jira` | Bitbucket is connected to the Jira site | Jira's development information lists each ticket's commits and repository; no repository list needed |
| `scan` | Not connected, or as a fallback | Lists commits authored in the period on all branches of the chosen repositories, and matches ticket keys in commit messages (case-insensitive) |
| `auto` (default) | — | `jira` if any story in scope has linked commits in Jira, otherwise `scan` |

For `scan`, nobody needs to name repositories. The skill searches every repository in the workspace(s)
that was updated during the period, and matches ticket keys in the commit messages itself. The workspace
comes from `BITBUCKET_WORKSPACE` / `--bb-workspace`, or from the token if it has `read:workspace`. Use
`--bb-repo WORKSPACE/REPO` (or `BITBUCKET_REPOS`) only to limit the search to specific repositories;
`python3 S bb-repos` shows which repositories would be searched.

## Checks per commit

1. **Updates story file:** the commit changes a Markdown file under `--stories-dir` (default `docs/stories/`).
   Read from the commit's file list (diffstat).
2. **Updates task list:** in those files, the commit adds, removes, ticks or unticks a checklist task.
   Read from the commit's diff, limited to the story files. This is mechanical (pattern matching):
   - Checklist lines: `- [ ]`, `* [x]`, `+ [X]`, numbered `1. [ ]` / `2) [x]`, at any indentation.
   - Tasks are paired by ID (`T-01`, `**P1-01 …**`, `TASK-3`, `1.2`), then by exact text, then by similar
     wording (80% or more), so a task reworded while being ticked still counts as ticked.

Merge commits are ignored. A commit linked to several tickets counts for each ticket, but only once in
the engineer and repository counts.

## Changes the parser can't classify: agent review

A story-file change is flagged when it has **no checklist change** (for example progress kept in a status
table, a ✅ marker, or an acceptance-criteria edit) or when checklist items were **removed and added
without matching** (reworded beyond recognition, or a different format). Flagged changes are counted
as-is (usually as no task progress) until reviewed.

1. The report's Notes say how many are waiting and name the review file (`<out>.review.json`). Each item
   has a key, the repository, tickets, an anonymous author ID, the commit message, the reason, and up to
   60 changed lines of the diff.
2. **The agent reads each item** and decides: `task_progress` (true if the change records progress on the
   story's implementation tasks in any format; false for wording, acceptance criteria or notes) and
   `ticked` (how many tasks it marks done), with a one-line `reason`. The instructions are in the file.
   If it can't tell, it leaves the item out.
3. Decisions go in `gen-e2-review-decisions.json` next to the report (`--decisions` to choose another
   path), keyed by the item key: `{"<key>": {"task_progress": true, "ticked": 1, "reason": "…", "reviewed_by": "agent"}}`.
4. Rerun the same report command. Decisions are applied, shown as "by agent review" in the report and in
   the raw data (with the reason), and reused on every later run, so the numbers stay repeatable. The
   review file is removed once nothing is waiting.

## Report

| Table | Columns |
|---|---|
| Tickets and their commits (gen-e2 vs other) | Tickets; with commits; commits; commits updating the story file; commits updating the task list; tickets with the story file updated; tickets with the task list updated; tasks ticked |
| Engineers | Engineers with commits on the period's tickets, and how many pushed gen-e2 commits (%); the same for engineers working on gen-e2 tickets. A gen-e2 commit updates a gen-e2 story file's task list. No names are shown. |
| Tickets with commits (collapsed) | Per ticket: status, commits, story-file commits, task-list commits, tasks ticked |

The raw-data file (`<out>.raw.json`, `bitbucket.commits`) lists every counted commit: repository, date,
anonymous author ID, first line of the message, the tickets it was linked to, and for each story file it
changed: the task changes and whether it was classified mechanically or by agent review (with the reason).

**People:** the report has no per-person figures. The raw-data and review files replace author names with
stable anonymous IDs (`engineer-3f2a9c`, a one-way hash of the name), so the engineer counts can be audited
without names.

**Reading it:** a gen-e2 story whose commits never update its task list was probably implemented
outside the gen-e2 flow. "Other" stories updating story files may be unlabelled gen-e2 work.

**Several repositories:** pass each with `--bb-repo` (repeatable). When code and story files live in
different repositories, code commits never touch the story file, so the per-commit percentages drop even
when the team follows gen-e2. Use the per-ticket columns (tickets with the story file / task list updated,
tasks ticked) as the adherence measure; they don't depend on how many repositories the code spans.

## Calls and limits

- Per commit: one diffstat call, plus one diff call per changed story file. Scanning adds about one call
  per 100 commits per repository. Bitbucket Cloud limits API requests per hour, so keep to about 10
  repositories and one month.
- Commits that don't mention a ticket key (scan) or aren't linked in Jira can't be attributed; the scan
  reports how many commits had no key.
- Squash merges collapse a branch's commits into one; the checks still work on the squashed commit if the
  feature-branch commits are gone.
- Story files kept in a different repository from the code are only found if that repository is scanned
  (or linked in Jira).
