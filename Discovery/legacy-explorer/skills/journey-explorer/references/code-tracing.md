# Tracing a journey step through code

Two halves of one step. In a server-rendered app both live in the same
codebase; in an SPA + API they may be separate repos. Trace only what the
step needs; this is not a full FE or BE analysis.

## Frontend trace

From the user's action to the request leaving the client.

| Find | Where it usually lives | Record in step cell |
|---|---|---|
| Screen | Route table, page file, view template, welcome file | Component |
| Action | `onClick`/`onSubmit` handler, `<form action>`, `<a href>`, menu config | User action |
| Input fields | Form component, template inputs, form bean | Data exchanged (out) |
| Client rules | Form schema, inline checks, disabled/hidden conditions, role-based rendering | Logic performed (`FE`) |
| Request | fetch/axios/client wrapper call, form post target | API |
| Response handling | `.then`/`await` branches, error boundaries, redirects | Exits |
| State carried | Store, context, session/local storage, hidden fields, query params | Data exchanged (state) |
| UI states | Loading, empty, error, partial-failure rendering | Exits |

For each client rule note **when** it fires (on change, on blur, on
submit, on load) and **what the user sees**.

## Backend trace

From the request arriving to the response leaving the server.

| Find | Where it usually lives | Record in step cell |
|---|---|---|
| Endpoint | Route/controller mapping, action mapping, servlet mapping | API (method + path) |
| Request shape | DTO, form bean, request params | Data exchanged (in) |
| Auth gate | Filter, annotation, interceptor, role check in handler | Logic performed (`SEC`) |
| Validation | Bean validation, validator config, manual checks | Logic performed (`BE`) |
| Business logic | Service methods, decision branches, calculations | Logic performed (`BE`) |
| Data touched | Repository/DAO calls, SQL, tables read/written | Logic performed (`DATA`) |
| Downstream calls | HTTP/SOAP clients, queues, email, caches | API (outbound) |
| Response | Returned DTO, view/forward name, redirect, status codes | Data exchanged (out), Exits |
| Async side effects | Events published, jobs scheduled | Logic performed (`ASYNC`) |

## Duplicated and divergent rules

When the same rule appears in FE and BE, record it once with both
citations and tag `FE+BE`. When they differ (e.g. FE max length 50, BE 40),
record both and raise an `Open` item; this is a migration risk.

## When code is missing

- FE only: record API from the call site, logic from response handling;
  mark server-side logic `Open`.
- BE only: derive screens from views/endpoints and screenshots; mark UI
  behaviour `Inferred`.
