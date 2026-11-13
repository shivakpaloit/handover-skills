> **Sample only.** Synthetic data for a fictional project `MKT`, produced by the real report renderer:
> `python3 scripts/gen_e2_metrics.py report --project MKT --month 2026-10 --code`

# Gen-e2 delivery metrics: 2026-10-01 to 2026-10-31

- Projects: MKT
- Gen-e2 = label `AISDLC`; "other" = issues without that label
- To Do status: To Do, Selected for Development; In Progress status: In Progress, In Review; Review status: In Review
- Generated: 2026-11-11T10:30:00+08:00

## 1. Completion and lead time of stories created in the period (creation to Review and to Done)

Stories created in the period, with their status as of 2026-11-11T10:30:00+08:00.

### Completion

| Cohort | Created | Done | In Review | Not Done or in Review | % Done | % Done or in Review |
|---|---|---|---|---|---|---|
| gen-e2 | 38 | 24 | 6 | 8 | 63.2% | 78.9% |
| other | 66 | 30 | 9 | 27 | 45.5% | 59.1% |

### Creation → Done (stories now Done)

| Cohort | Count | Average (days) | Median (days) |
|---|---|---|---|
| gen-e2 | 24 | 4.03 | 4.07 |
| other | 30 | 10.69 | 10.69 |

### Creation → Review (stories that ever reached a Review status, including ones now Done)

| Cohort | Count | % of created | Average (days) | Median (days) |
|---|---|---|---|---|
| gen-e2 | 29 | 76.3% | 3.21 | 3.05 |
| other | 36 | 54.5% | 8.42 | 8.9 |

### Stories not Done or in Review (age since creation)

| Cohort | Count | Average age (days) | Median age (days) | Oldest (days) | Current status |
|---|---|---|---|---|---|
| gen-e2 | 8 | 21.07 | 21.16 | 29.01 | In Progress 5, To Do 3 |
| other | 27 | 25.37 | 25.89 | 40.29 | Blocked 11, To Do 10, In Progress 6 |

<details><summary>gen-e2 stories not Done or in Review</summary>

| Story | Status | Age (days) |
|---|---|---|
| MKT-140 | To Do | 29.01 |
| MKT-144 | In Progress | 28.28 |
| MKT-142 | In Progress | 26.6 |
| MKT-141 | To Do | 23.37 |
| MKT-146 | To Do | 18.95 |
| MKT-143 | In Progress | 17.95 |
| MKT-147 | In Progress | 12.72 |
| MKT-145 | In Progress | 11.71 |

</details>

<details><summary>other stories not Done or in Review</summary>

| Story | Status | Age (days) |
|---|---|---|
| MKT-205 | To Do | 40.29 |
| MKT-203 | Blocked | 39.43 |
| MKT-219 | To Do | 34.83 |
| MKT-220 | Blocked | 34.39 |
| MKT-223 | In Progress | 32.88 |
| MKT-213 | Blocked | 32.36 |
| MKT-202 | To Do | 29.92 |
| MKT-224 | In Progress | 29.27 |
| MKT-204 | Blocked | 28.57 |
| MKT-221 | To Do | 28.23 |
| MKT-211 | Blocked | 28.14 |
| MKT-206 | To Do | 27.7 |
| MKT-208 | To Do | 27.22 |
| MKT-215 | To Do | 25.89 |
| MKT-222 | Blocked | 25.85 |
| MKT-217 | In Progress | 24.97 |
| MKT-216 | Blocked | 23.83 |
| MKT-212 | To Do | 22.17 |
| MKT-218 | In Progress | 21.85 |
| MKT-209 | Blocked | 20.25 |
| MKT-207 | To Do | 19.69 |
| MKT-210 | Blocked | 16.42 |
| MKT-226 | In Progress | 15.95 |
| MKT-201 | Blocked | 14.71 |
| MKT-225 | To Do | 14.54 |
| MKT-214 | Blocked | 12.79 |
| MKT-200 | In Progress | 12.77 |

</details>

## 2. Average time from In Progress to Review and to Done (cycle time)

### In Progress → Done

| Cohort | Count | Average (days) | Median (days) | Excluded (never In Progress) |
|---|---|---|---|---|
| gen-e2 | 14 | 2.73 | 2.43 | 0 |
| other | 18 | 6.66 | 7.09 | 4 |

### In Progress → Review

| Cohort | Count | Average (days) | Median (days) | Excluded (no In Progress before review, or first review before period) |
|---|---|---|---|---|
| gen-e2 | 15 | 1.91 | 1.7 | 0 |
| other | 17 | 4.63 | 4.8 | 5 |

## 13. Epics with active stories in the period (gen-e2 vs not)

| Cohort (epic's label) | Epics with active stories | Active stories in those epics |
|---|---|---|
| gen-e2 | 5 | 19 |
| other | 7 | 31 |
| **total** | **12** | **50** |

Active stories with no epic: 3.

## 14. % of stories created with gen-e2

| Stories created | Gen-e2 stories | % gen-e2 |
|---|---|---|
| 104 | 38 | 36.5% |

## 15. Time between epic creation and first story in To Do

| Cohort | Count | Average (days) | Median (days) | Epics without story in todo |
|---|---|---|---|---|
| gen-e2 | 4 | 1.17 | 1.11 | 0 |
| other | 4 | 4.6 | 4.51 | 1 |

<details><summary>gen-e2 epics</summary>

| Epic | Days to first story in To Do | Stories |
|---|---|---|
| MKT-10 | 1.89 | 3 |
| MKT-11 | 0.58 | 4 |
| MKT-12 | 1.24 | 3 |
| MKT-13 | 0.97 | 6 |

</details>

<details><summary>other epics</summary>

| Epic | Days to first story in To Do | Stories |
|---|---|---|
| MKT-30 | 4.7 | 5 |
| MKT-31 | 4.13 | 5 |
| MKT-32 | 5.24 | 3 |
| MKT-33 | 4.31 | 6 |
| MKT-34 | n/a | 0 |

</details>

## 16. Rate of BRD rework (epic description and attachment edits)

| Cohort | Epics | Description edits | Attachment changes | Avg edits per epic | % epics reworked |
|---|---|---|---|---|---|
| gen-e2 | 4 | 3 | 1 | 1 | 75.0% |
| other | 5 | 12 | 7 | 3.8 | 100.0% |

<details><summary>gen-e2 epics with rework</summary>

| Epic | Description | Attachment | Total |
|---|---|---|---|
| MKT-10 | 1 | 1 | 2 |
| MKT-11 | 1 | 0 | 1 |
| MKT-13 | 1 | 0 | 1 |

</details>

## Code (Bitbucket, via Jira development information)

### Done stories with linked code

| Cohort | Done stories | With linked commits | % |
|---|---|---|---|
| gen-e2 | 14 | 13 | 92.9% |
| other | 22 | 15 | 68.2% |

### In Progress → first commit

| Cohort | Count | Average (days) | Median (days) | Committed before In Progress |
|---|---|---|---|---|
| gen-e2 | 13 | 0.38 | 0.46 | 2 |
| other | 15 | 0.99 | 1.15 | 1 |

### First commit → PR merged

| Cohort | Count | Average (days) | Median (days) | No merged PR |
|---|---|---|---|---|
| gen-e2 | 13 | 1.54 | 1.43 | 0 |
| other | 15 | 4.38 | 4.17 | 0 |

### PR merged → story Done

| Cohort | Count | Average (days) | Median (days) | Closed before merge |
|---|---|---|---|---|
| gen-e2 | 13 | 0.23 | 0.18 | 1 |
| other | 15 | 1.56 | 1.52 | 0 |

### Commits and pull requests

| Cohort | Stories | Commits per story | PRs per story | % shared commits | Declined PRs | Stories with commits after Done |
|---|---|---|---|---|---|---|
| gen-e2 | 13 | 2.85 | 1.08 | 10.3% | 1 | 0 |
| other | 15 | 4.8 | 1.13 | 2.7% | 2 | 3 |

### Repositories found

| Repository | Stories | gen-e2 | other |
|---|---|---|---|
| selfcare-web | 17 | 10 | 7 |
| billing-api | 7 | 3 | 4 |
| mobile-app | 4 | 0 | 4 |

## Definitions

- **1**: stories created in the period, with their status when the report runs. Done = Done status category; In Review = currently in a Review status; % Done or in Review = (Done + In Review) / created.
- **1 → Done**: stories now Done; resolved (or status-category change) minus created.
- **1 → Review**: stories that ever entered a Review status (from their change history, including ones now Done); first entry minus created.
- **1 not Done or in Review**: the rest; age = report time minus created, grouped by current status.
- **2 → Done**: stories in the Done status category resolved in the period (or, if unresolved, whose status category changed in the period); Done time minus the first entry into any In Progress status. Stories that went straight to Done are excluded.
- **2 → Review**: stories that first entered a Review status in the period; that time minus the first entry into a pre-review In Progress status.
- **13**: epics with at least one active story in the period, split by the epic's own label. A story is active if it was in an In Progress or Review status at any time in the period, or reached Done in the period (from its change history).
- **14**: stories created in the period carrying the gen-e2 label, divided by all stories created in the period.
- **15**: epics created in the period; first time any child story was in To Do minus the epic's creation time.
- **16**: epics created in the period; changelog entries for `description` and `Attachment` from creation until now.
- **Code, population**: Done stories in the period (same as 2 → Done) that have commits linked in Jira's development information.
- **Code, In Progress → first commit**: earliest linked commit's author time minus the first entry into a pre-review In Progress status. Negative when coding started before the ticket was moved.
- **Code, first commit → PR merged**: last merged PR's last-update time (used as the merge time) minus the earliest linked commit.
- **Code, PR merged → story Done**: Done time minus the merge time. Negative when the story was closed before the code merged.
- **Code, commits per story**: merge commits excluded; a commit linked to several stories is split equally between them. % shared = commits linked to more than one story in scope.

## Notes

- Statuses auto-matched from the workflow: To Do = To Do, Selected for Development; In Progress = In Progress, In Review; Review = In Review. Override with --todo-status / --in-progress-status / --review-status.

## JQL used

- **1** (gen-e2): `project in ("MKT") AND issuetype = "Story" AND created >= "2026-10-01" AND created < "2026-11-01" AND labels = "AISDLC"`
- **1** (other): `project in ("MKT") AND issuetype = "Story" AND created >= "2026-10-01" AND created < "2026-11-01" AND (labels is EMPTY OR labels not in ("AISDLC"))`
- **2** (gen-e2): `project in ("MKT") AND issuetype = "Story" AND statusCategory = Done AND statusCategoryChangedDate >= "2026-10-01" AND statusCategoryChangedDate < "2026-11-01" AND labels = "AISDLC"`
- **2** (other): `project in ("MKT") AND issuetype = "Story" AND statusCategory = Done AND statusCategoryChangedDate >= "2026-10-01" AND statusCategoryChangedDate < "2026-11-01" AND (labels is EMPTY OR labels not in ("AISDLC"))`
- **13** (active story candidates): `project in ("MKT") AND issuetype = "Story" AND created < "2026-11-01" AND (updated >= "2026-10-01" OR statusCategory = "In Progress")`
- **13** (epics of active stories): `project in ("MKT") AND key in ("MKT-1", "MKT-2", …) AND issuetype = "Epic"`
- **14** (all stories): `project in ("MKT") AND issuetype = "Story" AND created >= "2026-10-01" AND created < "2026-11-01"`
- **14** (gen-e2 stories): `project in ("MKT") AND issuetype = "Story" AND created >= "2026-10-01" AND created < "2026-11-01" AND labels = "AISDLC"`
- **15** (gen-e2): `project in ("MKT") AND issuetype = "Epic" AND created >= "2026-10-01" AND created < "2026-11-01" AND labels = "AISDLC"`
- **15** (other): `project in ("MKT") AND issuetype = "Epic" AND created >= "2026-10-01" AND created < "2026-11-01" AND (labels is EMPTY OR labels not in ("AISDLC"))`
- **15** (children (batched)): `project in ("MKT") AND parent in ("<EPIC-1>", "<EPIC-2>", …) AND issuetype = "Story"`
- **16** (gen-e2): `project in ("MKT") AND issuetype = "Epic" AND created >= "2026-10-01" AND created < "2026-11-01" AND labels = "AISDLC"`
- **16** (other): `project in ("MKT") AND issuetype = "Epic" AND created >= "2026-10-01" AND created < "2026-11-01" AND (labels is EMPTY OR labels not in ("AISDLC"))`
- **code** (gen-e2): `project in ("MKT") AND issuetype = "Story" AND statusCategory = Done AND ((resolved >= "2026-10-01" AND resolved < "2026-11-01") OR (resolution is EMPTY AND statusCategoryChangedDate >= "2026-10-01" AND statusCategoryChangedDate < "2026-11-01")) AND labels = "AISDLC"`
- **code** (gen-e2, with linked commits): `project in ("MKT") AND issuetype = "Story" AND statusCategory = Done AND ((resolved >= "2026-10-01" AND resolved < "2026-11-01") OR (resolution is EMPTY AND statusCategoryChangedDate >= "2026-10-01" AND statusCategoryChangedDate < "2026-11-01")) AND labels = "AISDLC" AND development[commits].all > 0`
- **code** (other): `project in ("MKT") AND issuetype = "Story" AND statusCategory = Done AND ((resolved >= "2026-10-01" AND resolved < "2026-11-01") OR (resolution is EMPTY AND statusCategoryChangedDate >= "2026-10-01" AND statusCategoryChangedDate < "2026-11-01")) AND (labels is EMPTY OR labels not in ("AISDLC"))`
- **code** (other, with linked commits): `project in ("MKT") AND issuetype = "Story" AND statusCategory = Done AND ((resolved >= "2026-10-01" AND resolved < "2026-11-01") OR (resolution is EMPTY AND statusCategoryChangedDate >= "2026-10-01" AND statusCategoryChangedDate < "2026-11-01")) AND (labels is EMPTY OR labels not in ("AISDLC")) AND development[commits].all > 0`
