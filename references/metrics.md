# Metric definitions

All periods are inclusive calendar dates, interpreted in the Jira user's time zone (JQL).
Durations are in days (decimals), reported as average and median per cohort.

**Cohorts**

- gen-e2: `labels = "AISDLC"`
- other: `(labels is EMPTY OR labels not in ("AISDLC"))`. Plain `labels != X` would drop issues with no labels.

A cohort is decided by the issue's labels *now*, not at the time of the event.

**Change history** (metrics 1, 2, 15 and 16) is fetched in two bulk batches per run: stories with
`status` changes only, and epics with `description` and `attachment` changes only. The BRD/PRD
lives on the epic, so story-level edits are never counted.

## 1. Completion and lead time of stories created in the period

Population: Stories **created** in the period, per cohort. Each story's state is read **when the report runs**, so a recent period always looks less complete than an older one.

- **State.** *Done*: the current status is in the `Done` category (without a category, a resolution date or a status named `Done`). *In Review*: the current status is a Review status (`--review-status`) and the story isn't Done. *Not Done or in Review*: everything else.
- **Completion.** `% Done = Done / created`; `% Done or in Review = (Done + In Review) / created`.
- **Creation → Done.** Stories now Done. Value: `resolutiondate` (or `statuscategorychangedate` when no resolution is set) minus `created`.
- **Creation → Review.** Stories that ever entered a Review status, from their change history. This includes stories now Done, and stories that went back from Review to In Progress. Value: the first entry into a Review status minus `created` (0 if the story was created in Review). Also reported as a % of stories created. This needs REST history; without it, only the counts and Creation → Done are reported.
- **Not Done or in Review.** Count, average, median and oldest age (report time minus `created`), a breakdown by current status, and a per-story list, oldest first.

## 2. Average time from In Progress to Review and to Done (cycle time)

Two tables, each with its own population:

- **Done population.** Stories in the `Done` status category resolved in the period, or, if they have no resolution (common in team-managed projects), whose `statusCategoryChangedDate` falls in the period.
- **Review population.** Stories that entered a Review status (`--review-status`) during the period. Candidates are stories created before the period ended and updated since it began. The entry into Review is then checked in each story's change history.

Measures:
- **In Progress → Done.** Start: the first time the story entered any In Progress status (`--in-progress-status`; by default every In Progress-category story status, auto-matched by `statuses`). If the story was *created* in one of those statuses, the start is its creation time. The initial status comes from the first status change's `fromString`, or the current status if it never changed. End: same as metric 1. Stories that never entered an In Progress status (for example To Do straight to Done) are excluded.
- **In Progress → Review.** Start: the first entry into an In Progress status that is *not* a Review status, because entering review doesn't count as starting work. End: the first entry into a Review status. Stories that went to Review without a prior In Progress status, or whose first review was before the period, are excluded.

## 13. Epics with active stories in the period (gen-e2 vs not)

- **Active story:** a story that was in an In Progress or Review status (`--in-progress-status`) at any time during the period, or reached Done in the period. Checked against each story's status history, so a story sitting In Progress all month with no edits still counts.
- **Candidates:** `issuetype = Story AND created < <end> AND (updated >= <start> OR statusCategory = "In Progress")`.
- **Value:** the epics (parents) of the active stories, split by the **epic's own** `AISDLC` label, with the number of active stories in each. Active stories with no epic are reported separately.
- **Without REST credentials:** approximate; every candidate counts as active, and Notes says so.

## 14. % of stories created with gen-e2

- **Value:** `count(Stories created in period AND labels = AISDLC) / count(Stories created in period) × 100`.

## 15. Time between epic creation and first story in To Do

- **Population:** epics created in the period.
- **Children:** `parent in (<EPIC-1>, <EPIC-2>, …) AND issuetype = Story`, batched 50 epics per search and grouped by `parent`.
- **Value:** the earliest "entered To Do" time across child stories (same rule as metric 2) minus the epic's `created`.
- Epics with no child story in To Do yet are counted in `epics_without_story_in_todo` and left out of the average.

## 16. Rate of BRD rework

- **Population:** epics created in the period, as a proxy for the BRD.
- **Value:** the number of changelog items whose `field` is `description` or `Attachment`, from creation until the report runs.
- **Reported:** description edits, attachment changes (each attachment added or removed is one item), average edits per epic, and the % of epics with at least one edit.
- Attachments uploaded while the epic was being created can show up as changelog items. Compare cohorts rather than reading the absolute number.
