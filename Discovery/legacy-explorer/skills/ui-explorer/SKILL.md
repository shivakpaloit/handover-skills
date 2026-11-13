---
name: ui-explorer
description: "Summarises an existing app's user interface: every page or screen, its fields (label, type, required, validation) and its actions (buttons, links, submits, auto-loads) with what each triggers. Uses frontend code, server-rendered templates and screenshots. Use when asked to list, inventory or document the pages, screens, forms, fields or UI actions of an existing or legacy app."
argument-hint: "App path, optionally screenshots and a feature to limit scope"
---

# UI explorer

A page-by-page summary of what users see and can do. Record what the app
does today; no redesign advice.

## Where to look

| Find | Sources |
|---|---|
| Pages | Route tables, page files, view templates (JSP, Razor, PHP), welcome files, menus, screenshots |
| Fields | Form components, template inputs, form beans, message/label bundles |
| Validation | Form schemas, inline checks, validator config, `required`/`maxlength` attributes |
| Actions | `onClick`/`onSubmit`, `<form action>`, `<a href>`, menu items, on-load data fetches |
| Visibility | Role checks, conditional rendering, disabled/hidden conditions |

Resolve labels through message bundles so fields carry the words users
see. Screenshots confirm labels and layout; code confirms behaviour.

## Per page record

- Name (as users call it), route/template, who can reach it.
- Fields: label, name, type, required, validation and when it fires.
- Actions: label, kind (`submit`, `link`, `button`, `on-load`), what it
  triggers (`API-` ID or navigation target), outcomes (success, error).
- Messages: errors, empties and confirmations shown on the page.

## Output

`ui.md` in the run's output directory:

````markdown
# UI — <app>
Scope: <paths> · Screenshots: <files>

## Page map
```mermaid
flowchart LR
```

## UI-001 · <page name>
Route/template: <...> · Reached by: <persona/role> · Evidence: <path:line>

Fields
| Label | Name | Type | Required | Validation | Evidence | Status |
|---|---|---|---|---|---|---|

Actions
| Label | Kind | Triggers | Outcomes | Evidence | Status |
|---|---|---|---|---|---|

## Open questions
| ID | Question | Evidence | Ask |
|---|---|---|---|
````

IDs: `UI-NNN`. Evidence: `path:line` or screenshot file.
Status: `Confirmed` (cited lines show it), `Inferred` (say why) or `Open`.
