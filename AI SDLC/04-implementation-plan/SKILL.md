---
name: implementation-plan
description: 'Append or update one actionable, task-based implementation plan in an approved user story, covering feature work and automated tests. Detects the repository stack and applies a matching stack profile (Next.js, Spring Boot, or a generic fallback), composing one plan when a story spans several stacks such as a Next.js frontend and a Spring Boot API. Reuses existing test cases. Use when asked to plan, scope, or design implementation for a story in docs/stories/, or to revise an existing plan.'
argument-hint: 'Attach a story from docs/stories/ or paste its content'
---

# Implementation Plan

Turn one approved user story into **one** actionable, **task-based** implementation plan covering feature work and its test automation, so a coding agent can execute any single task without re-deriving scope or design decisions. The plan **structure** is stack-agnostic; its **content** comes from the repository's discovered stack through a stack profile.

## When to Use

- An approved story in `docs/stories/` needs a plan before implementation.
- An existing `## Implementation Plan` needs revising because its story, repository facts, or user feedback changed, or it targets a different stack than the one now requested.

## Resources

- [Plan template](./assets/plan-template.md) — the literal `## Implementation Plan` section to append.
- [Task rules](./references/task-rules.md) — checklist shape, verification, phases and status handling. Read before writing Tasks.
- [Quality gates](./references/quality-gates.md) — shared Security/Testing/Performance/Reliability/Accessibility/Observability checklist.
- [Multi-stack composition](./references/multi-stack.md) — how every section adapts when more than one stack profile is in scope.
- Stack profiles — detection signals, Discovery fields, section rules, checklist template, gate specifics, and core conventions:
  - [Next.js (TypeScript full-stack)](./references/stacks/nextjs.md)
  - [Spring Boot (Java backend)](./references/stacks/springboot.md)
  - [Generic fallback](./references/stacks/generic.md)

To support another stack, add a profile in `references/stacks/` with the same sections.

## Inputs

- **Source story** (required): prefer the attached story file (typically in `docs/stories/`). If only story text is pasted, find its unique matching source file before editing; if none can be identified, ask the user to attach or specify it. Do not create a separate plan or story file. If no story is provided, ask which story to plan. A story without acceptance criteria is broken input: stop and ask.
- **Test cases** (optional, auto-detected): the story's own `## Test Cases` section and/or the matching `docs/test-cases/NN-kebab-case-title-test-cases.md`. Reference their rows by ID in the Test Scenario Inventory instead of copying them. If both exist, merge non-duplicate scenarios and raise conflicting expected results under Open Questions. Resolve provisional `Manual / future automation target TBD` values after discovery. If neither exists, derive scenarios from the AC; do not block planning.
- **Design inputs** (optional, auto-detected): existing solution design in `docs/` and anything the story links — Solution Architecture Documents (SAD), ADRs, API/OpenAPI specs, ERDs (for example `docs/erd.md`), Mermaid diagrams (` ```mermaid ` blocks or `*.mmd`), D2 diagrams (` ```d2 ` blocks or `*.d2`), and wireframes or mockups (Mermaid/D2/Markdown/HTML or images). Search by name and content (for example `architecture`, `solution`, `sad`, `adr`, `openapi`, `wireframe`, `mockup`, `erd`), not only fixed paths. Treat them as constraints: reuse their contracts, components, data models and flows instead of redesigning, and raise conflicts with the story or the code under Open Questions. If none are found, record "None found" and proceed.

## Core Principles

- **One plan, appended to its story** under a new `## Implementation Plan` section at the end of the source story file. No separate plan, progress, or test-plan document; the section is the source of truth.
- **Discovery controls detail**: never assume a stack. The stack profile's **Stack match** result gates whether its conventions apply.
- **Required output format — Implementation Checklist**: always the `**Implementation Checklist:**` built from the stack profile's Checklist Template, with templated tasks repeated per area and omitted where not applicable. That format takes precedence over any other rule.
- **Requirements before technology**: preserve the story's and test cases' behavior and expected outcomes, then choose implementation and automation layers from the discovered architecture.
- **Contract-first, integration last**: phases are ordered so work streams depend on an agreed data contract, not on each other's implementation — a Data Contract phase first, UI and backend build phases that each depend only on it, and API Integration as the last phase. See Contract-First Phasing in [task-rules.md](./references/task-rules.md).
- **No unrequested behavior**: plan only what the AC and Notes call for. Deferred items go under Out of scope, not into tasks.
- **Lightweight training workflow**: do not assume Git branches, commits, pull requests, Jira/issues, or story points unless explicitly requested.

## Plan Structure

Record each fact in exactly one place:

- **Story content stays in the story** — do not copy its goal, role, AC, Product Context & Sequence, or source requirements into the plan.
- **Traceability** (AC → scenario → automation layer and test file) lives only in the Test Scenario Inventory.
- **Files** (create/modify/delete/reuse, including tests and migrations) live only in the Files & Reuse Audit.
- **Progress** lives only in subtask checkboxes; `Status` is derived from them. Gate outcomes are recorded once, on each phase's `Gate result` line.
- **Phase dependencies** live only on each phase's `Depends on` line.
- **Gate commands** live only in each phase's Exit gate; Test Execution Approach holds focused commands, fixtures, and runtime needs.

## Procedure

1. **Read the story.** Extract its AC, Notes, and prerequisite/sequence context; use them, do not copy them. If the AC have no IDs, assign `AC-1…AC-n` in source order and use them everywhere.
2. **Read the test cases and design inputs** per Inputs: test cases are the requirements baseline; design inputs (SAD, ADRs, OpenAPI, ERD, Mermaid/D2 diagrams, wireframes) are the design baseline. Search `docs/` and any links in the story for them before discovery, and note which contracts, components, data models and flows they already settle.
3. **Detect the stack.** Identify the deployable units the story touches (app, service, module, or package in a monorepo) by reading manifests and config directly. Match each unit to a stack profile using the profile's Detection section; use the generic profile when none matches. Read every selected profile before going further. When the story touches more than one unit, also read [multi-stack.md](./references/multi-stack.md) and assign Provider/Consumer roles.
4. **Discover each unit** per its profile's Discovery section (stack, data and auth, tooling, layout, configuration/secrets handling), and read applicable repository instructions (`AGENTS.md`, `copilot-instructions.md`, `.github/instructions/*.instructions.md`) and any matching conventions skill. Record the Stack match: on a match, apply the profile's Core Conventions as-is; on a difference, adapt to the repo's own conventions and state each deviation inline. Apply the profile's missing-tooling and greenfield rules.
5. **Confirm scope**: in scope, out of scope, assumptions, constraints, edge cases, backwards compatibility. Treat Notes as constraints: deferred or placeholder items go under Out of scope; cross-story or cross-unit consistency requirements go under Contracts to preserve and Risks. Ask the user only when ambiguity would materially change the plan (including unclear Provider/Consumer ownership); otherwise state the assumption and proceed.
6. **Audit the codebase** before completing the Files & Reuse Audit, scoped to the affected modules/routes and their direct import/call graph — not a codebase-wide sweep. Add a row for each relevant item reused, modified, created, or deleted, with its path and an evidence-based reason (for new items, why reuse is insufficient), following the profile's audit rule. Never propose a new file without checking for a suitable existing one; list no speculative files; use `Delete` only when required. Resolve every conditional ("if needed", "create if missing") — decide, or raise it under Open Questions.
7. **Fill Technical Approach** from design inputs, repository evidence and the profile's section rules. The API contract is complete enough for UI and backend to build against independently; adopt it from a design input when one defines it, and cite the source: data flow, API/schema changes, the API contract in the provider's format, integration points, and response and UI states. If the feature has no endpoint or no data-driven UI, say so and why.
8. **Schema and diagrams.** With a schema change, include the ER diagram and the profile's Data Model task, and list `docs/erd.md` in the audit as `Create` or `Modify` after checking whether it exists; otherwise set the Schema diagram line to "None — no schema change in this feature" and omit both. Include the Integration Diagram only when the flow crosses 3+ layers, involves an external/async call, or spans units; name real participants and calls, never invent steps. Derive the ER and sequence diagrams from existing design-input diagrams when present instead of drawing new ones from scratch, and flag any difference.
9. **Write the Tasks section** from the profile's Checklist Template and Checklist Rules, following [task-rules.md](./references/task-rules.md) — including Contract-First Phasing and a `Depends on` line per phase — and, for multiple profiles, the Phase Composition in [multi-stack.md](./references/multi-stack.md).
10. **Build the Test Scenario Inventory**: at least one row per AC, plus the edge, negative, and quality-gate scenarios the AC imply and the profile's coverage expectations. Name actual test file paths where conventions allow; do not invent test directories.
11. **Fill Test Execution Approach and Risks, Dependencies & Open Questions** using [quality-gates.md](./references/quality-gates.md) and the profile's gate specifics. For each scenario, explain how its layer proves the behavior and what fixtures it needs. Keep the story's expected outcomes unchanged unless the story itself is clarified.
12. **Coverage check** before writing: every AC maps to a scenario and a subtask; every scenario maps back to an AC; the `AC gaps` line reports the result.
13. **Append** the plan per the [template](./assets/plan-template.md) to the end of the source story with `Status: Not Started`, omitting non-applicable optional sections and stripping all `<!-- -->` comments. Use the story's existing number and title. Preserve all existing story content, including `## Test Cases`.
14. **Populate References** with every file, document, API, or design link actually used, including every design input listed under Scope & Dependencies. Use "None" only if nothing beyond the story applies; never fabricate links.
15. **Report** in about ten lines: the source story updated; each unit's stack profile and Stack match; design inputs found and used (or none found); omitted or adapted tasks with reasons; phase, task, subtask and scenario counts; test-case sources found and reused; AC gaps; open questions or assumptions needing a decision. Never silently omit that a stack was unrecognized. Do not paste the plan back.

## Re-run / Update Handling

If the source story already has a `## Implementation Plan` section:

- Read its Status, subtask checkboxes, `Gate result` lines, and Test Scenario Inventory. Compare against the current story AC and Notes, test cases, new user feedback, and repository facts the plan relied on (stack, layout, existing code).
- If nothing changed, report that the plan is up to date and stop — no write.
- If changed, update only the existing section. Never duplicate it, alter story content outside it, or silently change checked boxes or recorded gate results. If a change invalidates a checked subtask, preserve its checked state and report the conflict for review. Add new subtasks under the task they belong to; update exit gates accordingly. Report what changed.
- If the requested stack or units differ from the existing plan's (for example a backend plan requested for a story planned as Next.js-only), treat it as feedback: re-detect, rewrite in this format with the right profile(s), keep stack-independent content (scope, assumptions, AC numbering, scenarios, open questions), and move work no longer in scope to Out of scope.
- If the plan lacks contract-first phasing (no Data Contract phase, integration work before the last phase, or no `Depends on` lines), restructure its phases per [task-rules.md](./references/task-rules.md), moving unchecked subtasks only; keep checked subtasks where they are and report any that now sit out of order.
- If the plan uses an older format (`T-nn` task lines, flat checklist, free-form phases, phase or scenario status fields, Change Log), convert it to this format. Fold still-valid content from retired sections (Story Reference, Product Context & Sequence, Feature Overview, Component Analysis & Reuse Strategy, Affected Files, AC Coverage Matrix, Existing Code/Test Audit, Test File List, Acceptance Criteria, Gate Results, Phase overview, Change Log) into Scope & Dependencies, Files & Reuse Audit, and the Test Scenario Inventory; carry recorded gate results onto the phase `Gate result` lines. Preserve completion state when it maps clearly; leave uncertain subtasks unchecked and report the uncertainty.

## Hard Rules

- Planning only: never write or modify implementation or test code.
- Never invent technical detail not grounded in repository discovery or a selected stack profile's documented conventions.
- Never claim a section is complete when a required input (for example the story's AC) is missing — flag the gap.
- Never plan work for a unit or layer outside the story's scope; expose the contract instead and record the rest under Out of scope.
