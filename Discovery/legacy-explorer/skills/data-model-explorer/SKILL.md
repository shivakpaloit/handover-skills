---
name: data-model-explorer
description: "Inventories an existing app's data models: database tables and entities, transfer objects (DTOs, form beans, view models), their fields, types, keys and relationships, and which code reads or writes each one. Use when asked to list, map or document the data model, schema, entities, tables or DTOs of an existing or legacy app."
argument-hint: "App path, optionally a feature or module to limit scope"
---

# Data model explorer

What data the app holds and moves, and where. Record what the code does
today; no target-design advice.

## Where to look

| Kind | Sources |
|---|---|
| Stored | DDL/migration scripts, ORM mappings (annotations, `*.hbm.xml`), raw SQL in DAOs/repositories, stored-procedure calls |
| Transferred | DTOs, form beans, request/response classes, TypeScript types, view models, JSON/XML schemas |
| Reference | Enums, lookup tables, constants used as codes |

Prefer DDL over ORM over SQL strings when they disagree; log the
disagreement as `Open`.

## Per model record

- Name, kind (`table`, `entity`, `DTO`, `enum`) and source file.
- Fields: name, type, nullable/required, key (`PK`, `FK → model`),
  constraints and defaults.
- Relationships to other models.
- Read by / written by: the handlers or DAOs that touch it (link to
  `API-` IDs if known).
- Sensitive fields (personal, credential, payment): flag `PII` / `SECRET`.

Map DTO ↔ table only where the code copies fields between them; cite it.

## Output

`data-models.md` in the run's output directory:

````markdown
# Data models — <app>
Scope: <paths>

## Overview
```mermaid
erDiagram
```

## DM-001 · <name> (<kind>)
Source: <path:line> · Read by: <...> · Written by: <...>
| Field | Type | Key / constraint | Notes | Evidence | Status |
|---|---|---|---|---|---|

## Open questions
| ID | Question | Evidence | Ask |
|---|---|---|---|
````

IDs: `DM-NNN`. Evidence: `path:line`.
Status: `Confirmed` (cited lines show it), `Inferred` (say why) or `Open`.
