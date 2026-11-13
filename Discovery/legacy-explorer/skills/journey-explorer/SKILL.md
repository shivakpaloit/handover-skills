---
name: journey-explorer
description: "Business-analyst method for extracting user journeys from an existing application by triangulating chat or meeting transcripts, screenshots, test cases and the frontend/backend code. Produces an application summary, personas, and step-by-step flows (user action, component, API, data exchanged, logic performed), discovered by dynamic decomposition from the first entry point. Use when asked to extract, map, document or reconstruct user journeys, user flows or screen flows of an existing or legacy app, e.g. before migrating a JSP app to Next.js."
argument-hint: "App path or name, plus any transcript, screenshots or test cases to use"
---

# Journey explorer

Reconstruct what users actually do in an existing app, step by step, and
what the system does at each step. If `ui.md`, `api.md` or
`data-models.md` already exist in the output directory, reuse their
`UI-`, `API-` and `DM-` IDs in the trace instead of re-tracing.

## Inputs

Use whatever is supplied; at least one of code or screenshots is required.

| Input | Gives you | How to read it |
|---|---|---|
| Transcript (chat, meeting, interview) | Intent, personas, vocabulary, steps users describe | [sources.md](references/sources.md#transcripts) |
| Screenshots | Screens, fields, buttons, messages, step order | [sources.md](references/sources.md#screenshots) |
| Test cases | Expected paths, edge cases, rules, roles | [sources.md](references/sources.md#test-cases) |
| Frontend code | Screens, components, user actions, client rules, API calls | [code-tracing.md](references/code-tracing.md#frontend-trace) |
| Backend code | Endpoints, processing, server rules, data touched | [code-tracing.md](references/code-tracing.md#backend-trace) |

Server-rendered apps (JSP, JSF, WebForms, PHP) are one codebase holding
both traces.

## Steps

1. **Orient.** Read non-code sources first. Distil a long transcript to
   journey-relevant statements before using it. Write a draft application
   summary and persona list, both marked `Inferred` until code confirms.
2. **Find the first entry point.** Landing page, login redirect, default
   route, welcome file, menu root. Cite it.
3. **Decompose dynamically.** Run the frontier loop below until it is empty.
4. **Reconcile.** Cross-check each journey against every source. Code wins
   on *what happens*; transcript and screenshots win on *what users intend
   and call things*. Log every conflict as `Open`.
5. **Verify.** Re-read the cited lines of every step's API and logic cell.
   Downgrade anything not shown outright to `Inferred`.
6. **Write the trace** (`journeys-trace.md`): the evidence-backed,
   per-step technical table.
7. **Translate** it into `journeys.md`: plain language, no code, rules as
   "must" statements, quirks moved to *Things to confirm*. Then reread it
   as a non-technical reader and cut anything they could not explain back.

Both files: [output-format.md](references/output-format.md).

## Frontier loop (dynamic decomposition)

Keep a frontier of unexplored *step targets* (screens, routes, handlers).
Seed it with the entry point.

```
while frontier not empty:
  take target T
  identify screen + persona(s) that reach it
  list every user action on T (buttons, links, submits, auto-loads)
  for each action:
    trace FE: handler -> client validation -> API call (or form post)
    trace BE: endpoint -> processing -> rules -> data -> response
    record the step row
    record every exit: success, validation error, business error, system error
    push each exit's destination onto the frontier if not yet visited
  group consecutive steps toward one user outcome into a journey
```

- Start a new journey when the user's goal changes, not when the screen does.
- A branch that reaches a distinct outcome becomes its own journey or an
  alternate path; a validation loop stays inside the step.
- Stop following a branch at the app boundary (external system, email,
  logout) and record it as an exit.
- After the loop, list **orphans**: screens, routes or endpoints in code that
  no journey reached (check against `ui.md` and `api.md` when present), and
  transcript/test steps with no code found.

## Rules

- Every trace row cites evidence (`path:line`, screenshot file, transcript
  line or test-case ID). Status: `Confirmed` (cited lines show it),
  `Inferred` (say why) or `Open`.
- `journeys.md` is for humans first: no code, paths, URLs or tags in it.
  Evidence lives only in the trace.
- Describe the current behaviour; no target-design recommendations.
- Stay in scope: if the user names a feature, follow only journeys that
  touch it and mark adjacent ones `Out of scope`.
