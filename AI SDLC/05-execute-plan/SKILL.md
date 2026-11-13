---
name: execute-plan
description: 'Implement the plan embedded in a user story — production code and automated tests — verify it, update the story, report, and generate a tagged commit message when finished. Use when asked to execute, implement, continue, or resume a plan, a phase, or specific tasks from a story''s Implementation Plan section.'
---

# Execute Plan

Implement the plan embedded in a story's `## Implementation Plan` section, verify it, update the plan's own status fields, report, and hand off to the `commit-message` skill once the executed scope is done.

## Inputs

- **Source story**: the story containing an `## Implementation Plan` section. Attach it with `#file:` (typically from `docs/stories/`) or provide its path/story ID. If only story or plan text is pasted, locate the unique source story file before proceeding; if it cannot be identified unambiguously, ask the user to attach or specify it. Do not create a standalone plan file.
- **Story ID**: use the ID or number in the source story; ask if it cannot be determined. Preserve the exact source story path for progress updates and the final change-log entry.
- **Execution scope**: full implementation, one or more named phases, or task IDs within a single named phase. If omitted, ask the user to choose before making implementation changes.

## Execution Scope Selection

- **Full implementation**: execute every applicable, incomplete task in the plan's listed phase and task order. Skip work already marked `Completed` or `Not Applicable`, but still verify an unrecorded phase gate before advancing.
- **Selected phase(s)**: execute every applicable, incomplete task in each requested phase, in the plan's listed order. Phase names/numbers come from the plan; do not assume a fixed phase count.
- **Selected task(s)**: execute one or more task IDs within a single named phase, in the plan's listed order. Do not execute unselected tasks. If requested task IDs span multiple phases, ask the user to select phase(s) or task IDs within one phase.
- **Prerequisites**: before changes, check selected tasks' dependencies and every preceding phase's Exit gate. If any prerequisite is incomplete, report exactly what is missing and ask whether to include it. Do not silently expand scope. A phase marked `Not Applicable` with a reason does not block later phases.
- For a selected task run, execute only those tasks and their task-level verification. Use commands recorded in Test Execution Approach; do not invent task commands. Run the phase Exit gate only when all applicable tasks in that phase are `Completed` or `Not Applicable`; otherwise leave the phase `In Progress` and report that its gate remains pending.
- For a selected phase run, complete its applicable tasks and run its Exit gate before stopping or advancing.
- A scoped run must not mark the overall plan `Completed` while any applicable task or required final gate remains incomplete. Preserve `In Progress` when work remains, or `Blocked` if execution cannot continue.

## Procedure

1. Read the source story and its `## Implementation Plan` section. Treat the plan's Scope & Assumptions, Discovery Summary, Technical Approach, Test Scenario Inventory, Existing Code/Test Audit, Test File List, and Test Execution Approach as already settled — do not re-run discovery, re-litigate scope, or re-derive test strategy. If the section is missing or lacks detail needed to implement or test safely, flag the gap and ask rather than guessing or creating a separate plan.
2. Apply the `frontend-nextjs-conventions` skill for code and test shape, engineering discipline, and quality gates — do not invent alternate conventions. Follow the repository's actual test tooling and established fixture, mock, and accessibility-query patterns.
3. Execute only the selected scope in its listed order, keeping implementation and focused tests together for each behavior. Confirm dependencies and preceding phase gates before editing. Complete one phase at a time; do not start the next phase until the current phase's applicable tasks are complete, its Exit gate has passed, and the result is recorded in Gate Results. Modify only files in Affected Files and Test File List unless an essential change is documented in the plan. Never expand scope beyond the plan.
4. Test each acceptance criterion at the automation layer named in Test Scenario Inventory. Use isolated test data and restore shared state. Update scenario Status only after its test has actually run and passed.
5. Verify the implementation:
   - **Task scope** — run each selected task's Verify command and applicable checks for the files and behavior it changes. Do not run a phase or final gate early just because selected task checks pass.
   - **Phase scope** — run the phase Exit gate after all applicable tasks in that phase are complete, using the gate recorded in the plan.
   - **Full implementation** — run the plan's Final gate after all applicable tasks and phase gates are complete.
   - **Automated tests** — run the commands named in Test Execution Approach when they belong to selected tasks or a required gate. When a human wants to visually watch a Playwright run, use `npm run test:e2e:headed` instead of headless `test:e2e`.
   - **Runtime** — when a `next dev` server can run and `next-dev-loop` is installed, verify via the Next.js MCP server (`/_next/mcp`) and `agent-browser`. If not installed and the work is UI-facing, say so explicitly.
   - Walk the Quality Gates checklist (security, performance, accessibility, reliability) for anything the change touches.
6. Update the embedded plan's overall Status, affected task checkboxes, phase statuses, Gate Results, and relevant scenario statuses to reflect actual progress. A scenario is `Completed` only after its owning tasks and required verification pass. A phase remains `In Progress` until all applicable tasks and its Exit gate pass. Edit only the `## Implementation Plan` section; preserve the story, acceptance criteria, test cases, and all other content. Do not mark the overall plan `Completed` until every applicable task and the Final gate pass. Append one plain-language `Change Log (for Review)` entry inside the section, including manual reviewer steps, touched files, verification results, and risks or known gaps.
7. Report: files changed (production and test), scenarios covered, commands run and results, what was verified and how, and what was not verified and why. Never claim an untested code path or unrun command is "verified," and never make a destructive change (dropping a migration or deleting data) without explicit confirmation.
8. **Hand off to `commit-message`**: once the executed scope's verification (step 5) and plan updates (step 6) are done — whether the run completed a task, a phase, or the whole plan — invoke the `commit-message` skill, passing it the source story (for Jira ID resolution) and this run's Change Log entry (for the summary). Present its output to the user; do not stage files or run `git commit` yourself.
