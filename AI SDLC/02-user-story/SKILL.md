---
name: user-story
description: 'Write well-formed user stories from a feature request, meeting transcript, discussion notes, or Business Requirements Document, following INVEST principles and vertical slicing. Saves each story as docs/stories/NN-slug.md. Use when creating, reviewing, or splitting user stories/requirements before implementation planning.'
---

# User Story

Turn a feature idea, meeting transcript, or discussion into one or more well-formed user stories that a planner can turn into an implementation plan.

## When to Use

- A feature request, bug report, or discussion needs to be turned into a story before planning/implementation starts.
- A raw meeting transcript needs to be mined for distinct pieces of user-facing value.
- An approved Business Requirements Document (BRD) needs to be converted into traceable stories.
- An existing story needs review or splitting because it's too large or not vertically sliced.

## Story Format

Each story is a single Markdown file using the [story template](./assets/story-template.md):

```markdown
# User Story: [Number] - [Brief Title Describing the Goal]

**As a** [type of user/role],
**I want** [to perform an action or achieve a goal],
**so that** [I gain a specific benefit or value].

**Source requirement(s):** [BR-0NN, ... from the source BRD, or "derived from discussion — no BRD"]

## Acceptance Criteria

- [Criterion 1]
- [Criterion 2]

## Notes (Optional)

- [Context, constraints, or open questions]
```

## INVEST Checklist

Every story must satisfy all six before it's considered done:

- **Independent** — self-contained; avoid coupling unrelated concepts into one story.
- **Negotiable** — captures intent, not a rigid contract; details can be refined later.
- **Valuable** — delivers tangible value to an end-user, stakeholder, or the system (e.g. security, performance). The "so that" clause must be concrete, not filler.
- **Estimable** — clear enough that a team could reasonably size the effort.
- **Small** — completable within a single iteration; split epics into multiple stories rather than writing one large story.
- **Testable** — has explicit or clearly implied acceptance criteria that can be verified.

## Vertical Slicing (critical)

- **DO** write stories as a complete, thin slice of end-to-end functionality that delivers user value — e.g. "As a user, I want to log in with my email and password so that I can access my account" (touches UI, logic, and backend together).
- **DO NOT** split stories horizontally by technical layer — e.g. "Create the login database table," "Build the login API endpoint," "Design the login UI" are tasks, not stories. Reject or merge these into one vertical story.

## Procedure

1. If neither a feature request/discussion nor a BRD is supplied, ask the user what to generate stories from.
2. If a BRD is attached or supplied, treat it as the primary source of truth. Derive scope from its End-to-End Primary Journey / Primary Journey Requirements, numbered Business Requirements (`BR-0NN`), and MoSCoW Must Have list. Use any feature discussion or transcript only as supporting context; do not re-derive or expand BRD scope from it.
3. Identify distinct pieces of end-user-facing functionality or value. Ignore conversational filler and administrative details unless they inform a requirement. With a BRD, draft stories for Must Have requirements first; do not draft Should Have or Could Have requirements yet.
4. Use explicitly mentioned user roles; otherwise infer a logical role (e.g. "user," "administrator," "guest"). With a BRD, use the exact actor role names it defines.
5. Draft each story against the format above. With a BRD, map each story to the exact `BR-0NN` requirement ID(s) it satisfies. A story may map to multiple requirements, and a requirement requiring multiple stories must be listed on each. Seed acceptance criteria from relevant BRD Acceptance Criteria (including Given/When/Then examples), `BRULE-0NN` business rules, and `E-00N` exception scenarios rather than inventing criteria independently. Without a BRD, set Source requirement(s) to `derived from discussion — no BRD` and derive acceptance criteria from the supplied context.
6. Validate every story against the INVEST checklist and the vertical-slicing rule; merge or split stories that fail.
7. Determine the next sequential number by checking existing files in `docs/stories/` (numbering continues across the whole project, it does not restart per feature).
8. Save each story as `docs/stories/NN-kebab-case-title.md` (two-digit-minimum sequential prefix, e.g. `01-search-products-by-name.md`).
9. Report the file(s) created, a one-line summary and source requirement mapping for each story, and anything that did not clearly map to a valid story. With a BRD, include a short "Candidate follow-up stories" line for any Should Have or Could Have requirements not drafted.
