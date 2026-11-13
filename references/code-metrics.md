# Code metrics (Bitbucket)

Optional section of the report, added with `report --code`. It joins Bitbucket commits and pull
requests (PRs) to the Done stories of the period, and compares gen-e2 with other stories.

## Where the data comes from

Jira's development information (`/rest/dev-status/latest/issue/detail`), read with the same API
token as the rest of the report. No Bitbucket token, workspace name or repository list is needed:
Jira already links each commit, branch and PR to every ticket key it mentions, and the report lists
the repositories it found.

**Prerequisites**

- A Jira admin has connected the Bitbucket workspace to this Jira site.
- Commit messages, branch names or PR titles include the ticket key, for example `GEM-5 add booking API` or `feature/GEM-5-booking`.

Without these, every story shows as "no linked code" and Notes explains why. The endpoints are the
ones Jira's own Development panel uses; Atlassian does not document them publicly, so the response
shape could change.

**Calls:** one JQL search per cohort (`development[commits].all > 0`) to find Done stories with linked
code, then two calls per such story (commits, then PRs). For about 10 projects and one month, that is
at most a few hundred calls.

## Definitions

All metrics use Done stories in the period (the same population as 2 → Done) that have at least one
linked commit. Merge commits are ignored.

| Metric | Value | Notes |
|---|---|---|
| Done stories with linked code | Stories with linked commits ÷ Done stories | Traceability. Low values make the other code metrics unrepresentative. |
| In Progress → first commit | Earliest linked commit's author time − first entry into a pre-review In Progress status | Negative when coding started before the ticket was moved; counted in "Committed before In Progress". |
| First commit → PR merged | Merge time − earliest linked commit | Merge time = the latest last-update time among the story's merged PRs; Jira's development information has no separate merge date. Stories without a merged PR are counted separately. |
| PR merged → story Done | Done time − merge time | Negative when the story was closed before its code merged; counted in "Closed before merge". |
| Commits per story | Linked commits per story | A commit linked to several stories is split equally between them, so totals aren't double-counted. |
| % shared commits | Commits linked to more than one story in scope ÷ all linked commits | High values mean several stories are being delivered in one commit (batching). |
| PRs per story, declined PRs | Count of linked PRs, and of PRs with status DECLINED | |
| Stories with commits after Done | Stories with a linked commit authored after their Done time | Follow-up fixes after the story was closed. |
| Repositories found | Repositories with commits or PRs linked to the stories | Shows which repositories the project's work lives in. |

## Limits

- **Commits that finish a story without naming it** can't be detected. Encourage putting every key in the commit message, branch name or PR title. A PR title naming several keys links the whole PR to each of them.
- **Commit author times** can be rewritten by rebasing, and individual commits disappear from a squash merge. PR times are more reliable than commit times.
- **Not available from Jira's development information:** when a PR was opened or first reviewed, review comments, and lines changed. These need Bitbucket's own API and a token with Bitbucket scopes; the Jira-only token is rejected there ("API Token provided has no Bitbucket scopes").
- **Other tools:** `--code-app` changes the development tool type requested from Jira (default `bitbucket`). Only Bitbucket Cloud has been considered.
