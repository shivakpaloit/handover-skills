# Stack Profile: Generic (fallback)

Use this profile for a unit that matches no other profile in this folder. Record `Stack match: No profile — generic fallback` with the discovered stack, and say so in the chat report. If a matching conventions skill or `.github/instructions/*.instructions.md` file exists for the stack, read it and apply it as the Core Conventions.

## Discovery

Read the unit's manifests and config directly (for example `package.json`, `pyproject.toml`, `go.mod`, `*.csproj`, `Cargo.toml`, `Gemfile`). Fill the Discovery Summary block as:

- Stack: [language/runtime and version, framework and version, package/build manager, affected module/app]
- Data & auth: [data layer, migration tool, and auth mechanism, or "None present"]
- Tooling: [test, lint/format, typecheck, coverage and build tooling]
- Stack match: No profile — generic fallback ([discovered stack])

Tooling the plan needs that is undeclared or unconfigured counts as missing: add one setup subtask for it to the first task and note it under Risks.

## Plan Section Rules

- **Files & Reuse Audit:** the rationale gives the module/layer, responsibility, and any transaction or security boundary.
- **API contract:** the interface the story exposes (HTTP, CLI, message, library API) with inputs, validation, auth, outputs and errors; or "None".
- **Response / UI states:** cover success, empty, not-found, validation-error, unauthorized, and downstream-failure outcomes for each interface, and loading/empty/error/populated states for any UI.
- **Inventory automation layers:** the narrowest unit, integration, contract, or end-to-end layer the discovered tooling supports.

## Checklist Template

**Phase 1: Data Contract**
Depends on: None

**1. Data Contract:**
- [ ] Add required dependencies and configuration to `[manifest path]`
- [ ] Define request/response types, validation schemas and domain errors in `[repo-relative path]`
- [ ] Confirm the `[InterfaceName]` contract in Technical Approach matches the types and schemas
- [ ] Create typed contract fixtures for success, empty, validation-error, unauthorized and failure outcomes in `[repo-relative fixtures path]`
- [ ] Write tests proving every contract fixture conforms to its schema

**Phase 2: Core Logic & Interface**
Depends on: Phase 1

**2. Data Model — [ModelName]:**
<!-- Include only with a schema change. Repeat per model. -->
- [ ] Create migration `[repo-relative path]` with tables, constraints and indexes
- [ ] Create/modify `[ModelName]` and its data access in `[repo-relative path]`
- [ ] Write data-access tests for `[ModelName]` against `[test database strategy]`
- [ ] Update database ERD in `docs/erd.md`

**3. [ModuleName]:**
<!-- Repeat per module/service holding business rules. -->
- [ ] Implement `[ModuleName]` business rules in `[repo-relative path]`
- [ ] Handle `[not-found / conflict / rule-violation]` cases in `[ModuleName]`
- [ ] Write unit tests for `[ModuleName]` success, rule-violation and failure paths

**4. [InterfaceName]:**
<!-- Repeat per endpoint, command, consumer or job the story exposes. -->
- [ ] Create/modify `[InterfaceName]` in `[repo-relative path]`
- [ ] Validate input with the Phase 1 schemas and enforce `[auth rule]` for `[InterfaceName]`
- [ ] Map errors to `[the repo's error format]` for `[InterfaceName]`
- [ ] Write tests for `[InterfaceName]` success, validation, authorization and error paths, asserting responses conform to the Phase 1 contract
- [ ] Verify `[InterfaceName]` matches the contract in Technical Approach and update the contract, schemas and fixtures together if it differs

**Phase 3: Consumer on Contract Fixtures**
Depends on: Phase 1
<!-- Include only when the story has a UI screen or other consumer of the interface. -->

**5. [ConsumerName]:**
<!-- Repeat per UI screen or consumer. -->
- [ ] Build `[ConsumerName]` in `[repo-relative path]` reading the contract fixtures
- [ ] Handle loading, empty and error states using the contract fixtures
- [ ] Write tests for `[ConsumerName]` with contract fixtures

**Phase 4: API Integration**
Depends on: Phase 2, Phase 3

**6. Integrate [ConsumerName]:**
<!-- Include only with Phase 3. Repeat per consumer. -->
- [ ] Replace contract fixtures with real `[InterfaceName]` calls in `[ConsumerName]`
- [ ] Map real error responses to `[ConsumerName]` error states
- [ ] Update `[ConsumerName]` tests to cover real calls (stubbed at the boundary with the contract fixtures)

**7. Integration Testing:**
- [ ] Integration or end-to-end test of `[user flow]` across `[layers]`

**8. Final Documentation & Polishing:**
- [ ] Document public interfaces in `[docs location]`
- [ ] Final review of integration
- [ ] Performance checks with realistic data

## Checklist Rules

- Phase 1 fixes the contract and its fixtures; Phase 2 (provider) and Phase 3 (consumer) each depend only on it and may run in parallel; Phase 4 is always last and leaves the feature usable end to end. Omit Data Model without a schema change; omit Phase 3 and the Integrate tasks when nothing consumes the interface within this story (Phase 4 then depends on Phase 2 only); replace task names with the stack's real concepts. Renumber phases consecutively and update `Depends on` lines after omissions.
- **Exit gate commands:** the discovered typecheck/compile, lint, test, migration-validation and build commands.
- **Layer coverage check:** types and contracts; data and schema; business rules; interface validation and authorization; error handling; configuration and secrets; tests.
