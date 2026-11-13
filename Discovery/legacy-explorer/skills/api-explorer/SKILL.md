---
name: api-explorer
description: "Inventories an existing app's APIs in both directions: what it serves (inbound endpoints, handlers, auth, request/response, errors) and what it calls (outbound HTTP/SOAP/queue/email calls, including frontend calls to its own backend). Use when asked to list, map or document the endpoints, API surface, integrations or downstream dependencies of an existing or legacy app."
argument-hint: "App path, optionally a feature or module to limit scope"
---

# API explorer

Two inventories: the app **as server** and the app **as client**. Record
what the code does today; no target-design advice.

## As server (inbound)

Find every way a request gets in: route/controller annotations, action
mappings, servlet mappings, `web.xml`, router files, SOAP endpoints, message
listeners, scheduled jobs (record jobs as `JOB` method).

Per endpoint record:

| Field | Notes |
|---|---|
| Method + path | Resolve prefixes and context roots to the full path |
| Handler | Class/method or file |
| Auth | Filter, annotation, interceptor or role check; `none` if open |
| Request | Params, body fields, form bean or DTO (link to `DM-` ID if known) |
| Response | DTO, view/forward name, redirect, content type |
| Errors | Status codes, error views, error messages |

## As client (outbound)

Find every call leaving the process: fetch/axios/HTTP clients, SOAP stubs,
REST templates, queue producers, mail senders, file drops, and frontend
calls to the app's own backend.

Per call record: caller, target (host/config key + path or operation),
method, payload, response handling, timeout/retry if set.

Resolve base URLs through config files and env vars; cite the config line.

## Output

`api.md` in the run's output directory:

````markdown
# API — <app>
Scope: <paths>

## Served (inbound)
| ID | Method | Path | Handler | Auth | Request | Response | Errors | Evidence | Status |
|---|---|---|---|---|---|---|---|---|---|

## Called (outbound)
| ID | Caller | Target | Method / op | Payload | Handling | Evidence | Status |
|---|---|---|---|---|---|---|---|

## Open questions
| ID | Question | Evidence | Ask |
|---|---|---|---|
````

IDs: `API-IN-NNN`, `API-OUT-NNN`. Evidence: `path:line`.
Status: `Confirmed` (cited lines show it), `Inferred` (say why) or `Open`.
