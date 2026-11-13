# Multi-Stack Composition

Apply when the story touches more than one deployable unit with different stack profiles (for example a Next.js frontend that calls a Spring Boot API). Still produce **one** plan in the source story. A unit the story does not touch is not in scope: name it under Out of scope and, if this story changes a contract it relies on, under Contracts to preserve.

## Roles

Assign each in-scope unit one role, and record it in its Discovery Summary block:

- **Provider** — owns persistence, business rules and the API the story needs (for example Spring Boot, or Next.js when it has its own data layer).
- **Consumer** — calls the provider's API (for example a Next.js UI calling a Spring Boot API).

When two units both could own a behavior, the repository's existing ownership wins; if unclear, ask the user, because it changes every section below.

## Section-by-Section Rules

| Section | Single profile | Multi-stack adjustment |
|---|---|---|
| Scope & Dependencies | As template | Out of scope lists untouched units. Contracts to preserve lists existing cross-unit contracts this story must not break. Assumptions records the role assignment if inferred. |
| Discovery Summary | One block | One block per unit, each starting with `Stack profile: [profile] — [unit name] ([path]) — [Provider/Consumer]`, each with its own Stack match. |
| Files & Reuse Audit | One table | One table; paths identify the unit. Each row's rationale follows its own profile's audit rule. Add the consumer's API client/config and the provider's CORS/security config when they change. |
| Technical Approach | As template | **API contract is defined once, by the provider**, in the provider profile's contract format; the consumer references it and never redefines it. Data flow spans both units. Integration points name the cross-unit call: base URL config per environment, auth/token propagation, CORS, and how provider errors (e.g. `ProblemDetail`) map to consumer UI states. Response states (provider) and UI states (consumer) are both required. Schema changes belong to the provider only. |
| Integration Diagram | Conditional | **Required** — a cross-unit call is an external call. Participants span the consumer UI, the network boundary, and the provider layers. |
| Tasks | Profile template | See Phase Composition below. |
| Test Scenario Inventory | As template | `Automation layer & file` names the unit (for example `backend: @WebMvcTest …`, `frontend: Playwright …`). Prove each behavior at the narrowest layer in its owning unit; reserve cross-unit end-to-end scenarios for user flows. UI-only scenarios are covered by the consumer, not AC gaps. `Type` values are the union of the profiles'. Add a contract scenario proving the consumer's client matches the provider's contract. |
| Test Execution Approach | As template | Focused commands grouped per unit. Runtime requirements list everything the cross-unit E2E needs: both units running, start order, provider database/containers, consumer base URL env var, test auth. Fixtures name seed data in the provider and auth state in the consumer. |
| Risks, Dependencies & Open Questions | As template | Add contract drift between units, deployment order and backward compatibility (provider ships a compatible API before the consumer depends on it), CORS/auth misconfiguration, and environment parity. |
| References | As template | Include the provider's API spec/OpenAPI location when it exists. |

## Phase Composition

Phases follow Contract-First Phasing in [task-rules.md](./task-rules.md): one shared contract, build phases per unit that depend only on it, and one API Integration phase last. Prefix each build phase name with its unit and number phases and tasks consecutively across the whole plan. Typical shape for a Spring Boot provider and a Next.js consumer:

| Phase | Depends on | Content |
|---|---|---|
| 1: Data Contract | None | Provider's Data Contract task, then the consumer's Data Contract task |
| 2: Backend — Domain, Persistence & Service Logic | 1 | Provider Phase-2 tasks |
| 3: Backend — API Exposure | 2 | Provider endpoint tasks and its in-process Integration Testing |
| 4: Frontend — UI Implementation with Contract Fixtures | 1 | Consumer component tasks |
| 5: API Integration | 3, 4 | API Client, `Integrate [ComponentName]`, cross-unit End-to-End Testing, Final Documentation & Polishing |

1. **One shared Data Contract phase first, owned by the provider.** It holds the provider's Data Contract task (DTOs, published OpenAPI or schema, example payloads) followed by the consumer's Data Contract task (types and schemas generated from or matching that contract, plus contract fixtures copied from the provider's example payloads). Name them `**N. Data Contract — Backend:**` and `**N. Data Contract — Frontend:**`. Adopt contracts from design inputs when they exist. Its gate runs both units' contract/fixture tests.
2. **Provider build phases next**, in the provider profile's order, minus its Data Contract phase and minus Integration-phase work moved below. They depend on the Data Contract phase and on each other in sequence.
3. **Consumer UI phase depends only on the Data Contract phase**, so it runs in parallel with the provider build phases. It builds every component against contract fixtures; no consumer phase waits on the provider's implementation.
4. **Remove duplicated ownership from the consumer.** Omit consumer tasks for work the provider owns: in a Next.js consumer, drop Data Model, the `[EndpointName]` Route Handler/Server Action tasks and the backend phase — unless the repo deliberately uses a BFF/proxy layer, in which case keep one endpoint task per proxy route in a consumer build phase that depends on the Data Contract phase, and say so in the rationale.
5. **API Integration is the last phase** and depends on every build phase. It starts with an API Client task, before any `Integrate [ComponentName]` task:
   - [ ] Create/modify the typed `[ApiClientName]` for `[provider endpoints]` in `[repo-relative path]` from the Phase 1 contract
   - [ ] Configure the provider base URL via `[env var]` per environment and propagate `[auth token/session]`
   - [ ] Map provider error responses to consumer error/empty states in `[ApiClientName]`
   - [ ] Write tests for `[ApiClientName]` success, validation-error, unauthorized and downstream-failure responses (mocked HTTP using the contract fixtures)
   Then one `Integrate [ComponentName]` task per component, one cross-unit End-to-End Testing task covering user flows with both units running, and one Final Documentation & Polishing task merging each profile's doc and review subtasks. The provider keeps its in-process Integration Testing task in its own last build phase.
6. **Contract fixtures are shared truth**: consumer fixtures are the provider's example payloads, so integration swaps the data source, not the shape. A contract change in either unit updates both units' schemas and fixtures in the same subtask.
7. **Exit gates** use the commands of the phase's unit (the Data Contract gate runs both). The last phase's gate runs both units' suites plus the cross-unit E2E and confirms every AC has a passing scenario.
8. **Phase count** is one Data Contract phase, the provider's build phases, one consumer UI phase, and one API Integration phase (five for Spring Boot + Next.js), minus phases a profile omits. The oversized-story warning applies to the combined checklist; recommend splitting by unit when it fires.
