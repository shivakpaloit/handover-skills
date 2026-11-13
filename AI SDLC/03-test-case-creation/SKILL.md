---
name: test-case-creation
description: 'Generate a traceable test-case matrix from a user story (docs/stories/NN-slug.md) and write it to docs/test-cases/NN-slug-test-cases.md after input and readiness checks. Use when asked to create or update test cases from a user story, for any language or framework.'
---

# Test Case Creation

Turn a story's acceptance criteria into a traceable test-case matrix and save it as a separate file after the input and readiness checks pass.

```
docs/stories/NN-slug.md  --(read)-->  matrix  --(write)-->  docs/test-cases/NN-slug-test-cases.md
```

- **Step 1 — read**: the source story.
- **Step 2 — draft**: apply the gates below in chat.
- **Step 3 — write**: after checks pass, write the matrix to its separate output file; do not wait for chat approval.
- **Step 4 — verify**: read the output file back from disk; it is the source of truth for previously generated cases.

## Core Principles

- **Traceability**: every row maps to a specific acceptance criterion (AC) in the source story; the output file header records the source story and AC set it was generated from.
- **No silent skips**: an AC that's ambiguous or untestable as written is listed as "needs clarification" in the matrix, never dropped.
- **One story at a time**: never batch-approve multiple stories in one pass.
- **The output file is the state**: there is no separate progress file — the existing test-case markdown (if any) is the source of truth for what was previously generated.

## Input And Output

- Resolve one story from an attached file, pasted text, or a story name/number to look up in `docs/stories/`.
- Source stories: `docs/stories/NN-slug.md`.
- Generated test cases: `docs/test-cases/NN-slug-test-cases.md` (same number and slug as the source story).
- Create `docs/test-cases/` if it does not exist.
- If the story was pasted as text, derive its slug and assign the next sequential number by checking existing files in `docs/test-cases/`.

## Gate 0: Locate & Validate Input

- Resolve the story from an attached file, pasted text, or a name/number to look up in `docs/stories/`.
- If no matching file is found, list what's in `docs/stories/` and ask the user to pick one rather than guessing.
- If no story input is provided, ask which story to use before proceeding.
- Every story produced by the `user-story` skill includes an Acceptance Criteria section. Treat a missing one as broken/incomplete input — stop and ask the user to add it rather than inventing criteria.

## Gate 1: Story Readiness

- Extract the AC as a numbered list (`AC-1`, `AC-2`, ...), preserving the original wording.
- Generate requirements-level test cases even when implementation code, architecture, routes, or test tooling do not exist yet; do not block on implementation availability.
- Keep steps and expected results technology-neutral when implementation details are unknown. Do not guess components, actions, routes, data access, or test frameworks from the story alone.
- If the story has a **Source requirement(s)** line with `BR-0NN` IDs and the source `business_requirements_document.md` is available (attached or discoverable in the repo), use relevant `BRULE-0NN` business rules and `E-00N` exception scenarios to seed additional Validation/Negative/Edge rows. Reference each originating BRD ID alongside its `AC Ref`.
- If AC volume is large (more than ~15 rows) or the projected test count looks like it will exceed ~30, pause and ask the user whether to split the story into multiple test-case passes before drafting.

## Gate 2: Matrix & Write

Draft a test case matrix as a markdown table with these columns:

| ID | Title | Type | Preconditions | Steps | Expected Result | AC Ref | Priority | Automation |
|----|-------|------|----------------|-------|------------------|--------|----------|------------|

- `ID`: `TC-NN-<slug>-01`, incrementing.
- `Type`: `Functional`, `Validation`, `Negative`, or `Edge`.
- `Automation`: name confirmed tooling only when the repository or an existing implementation plan establishes it (e.g. `Frontend (Jest/RTL)` or `E2E (Playwright)`). Include a target test file/spec name if an implementation plan has already named one for this story. Otherwise use `Manual / future automation target TBD`.
- Every AC must be covered by at least one row (`AC Ref` column). Add `Validation`/`Negative` rows for known constraints even if not spelled out in the AC — e.g. required fields, auth/authorization checks, 404s on missing resources, 400s on invalid input.
- Steps should reference actual routes, components, or actions when they exist; otherwise describe observable user or business behavior without inventing implementation details.
- Write the full matrix to `docs/test-cases/NN-slug-test-cases.md` once the preceding checks pass. Do not pause for chat approval.

## Gate 3: Write & Verify

- Write the matrix to `docs/test-cases/NN-slug-test-cases.md`, prefixed with the source story path, generation date, and AC list used (so future re-runs can diff against it).
- Verify by reading the file back from disk (don't assume the write succeeded just because the tool call returned):
  - every AC in the story has at least one row referencing it
  - no duplicate `ID` values
  - the output file content matches what was generated

## Re-run / Update Handling

If `docs/test-cases/NN-slug-test-cases.md` already exists:

- read its embedded AC list from the header
- compare against the story's current AC
- if unchanged, tell the user the file is already up to date and stop
- if changed, show which AC were added/removed/modified and propose which existing rows to keep, which to regenerate, and which new rows to add — present this as a diff for approval (Gate 2 applies again), never silently overwrite or delete existing rows outright.
