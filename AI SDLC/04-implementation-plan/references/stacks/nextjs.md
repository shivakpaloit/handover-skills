# Stack Profile: Next.js (TypeScript full-stack)

## Detection

Select this profile for a unit whose `package.json` declares `next`, with an `app/` (or `src/app/`) directory or `next.config.*`. Pages Router, a different ORM, or a different test runner still select this profile, recorded as **Differs**.

**Baseline for Stack match:** Next.js App Router + TypeScript, Prisma, Zod, React Hook Form, Tailwind CSS, Jest + React Testing Library, Playwright.

**Role:** UI, and also API provider (Server Actions / Route Handlers + data layer) unless another in-scope unit owns the API — see [multi-stack.md](../multi-stack.md).

## Discovery

Read `package.json`, lockfile, `next.config.*`, `tsconfig.json`, `prisma/schema.prisma`, test configs, and `.env.example` directly. Fill the Discovery Summary block as:

- Stack: [Node/TypeScript, Next.js version and router, package manager, and the affected app/package if a monorepo]
- Data & auth: [data layer (e.g. Prisma + database) and auth mechanism, or "None present"]
- Tooling: [testing, lint, and build tooling]
- Stack match: [Matches the Next.js baseline | Differs: [specifics] | Greenfield: no app present]

**Missing tooling:** tooling listed in `package.json` but without its config or schema (for example `jest.config.*`, `playwright.config.*`, `prisma/schema.prisma`) counts as missing: record it under Differs, add one setup subtask for it to the first task, and note it under Risks. Missing tooling alone does not switch off Core Conventions; only a different framework or library does.

## Plan Section Rules

- **Files & Reuse Audit:** for a new or modified UI component, the rationale gives its responsibility, Server vs Client Component choice (justified only by in-scope behavior), and key props. With no UI, omit those rows and state in Technical Approach that no UI is affected.
- **Paths:** do not assume `src/components/`; App Router components may live beside their routes and a feature may need no new components. Never use example paths from other projects (for example `src/types/index.ts` or `src/mocks/`) unless the repo has that layout.
- **API contract:** for each new/changed Route Handler or Server Action — method, path (or action name), auth, request schema, response schema, error responses. Use a Route Handler unless Core Conventions favor a Server Action for an in-app mutation; record the choice.
- **UI states:** for any data-driven UI, subtasks account for loading, empty, error, and populated states (consider `loading.tsx`, `error.tsx`, `not-found.tsx` and in-component empty states). If there is no data-driven UI, say so and why.
- **Integration Diagram participants:** User, Component, Server Action / Route Handler, Data layer / external service.
- **Inventory automation layers:** narrowest of unit, component (RTL), integration, API, or end-to-end (Playwright).
- **Test Execution Approach:** add a design/responsive verification bullet only when the story includes a design specification; name the source and whether checks are automated or manual. Omit it otherwise.

## Checklist Template

**Phase 1: Data Contract**
Depends on: None

**1. Data Contract:**
- [ ] Define `[NewDataType]` request/response types in `[repo-relative types path]`
- [ ] Define Zod schemas for `[NewDataType]` inputs and responses in `[repo-relative schema path]`
- [ ] Confirm the `[EndpointName]` contract in Technical Approach matches the schemas
- [ ] Create typed contract fixtures for populated, empty, validation-error, unauthorized and failure responses in `[repo-relative fixtures path]`
- [ ] Write schema tests proving every `[NewDataType]` fixture parses against its Zod schema

**Phase 2: UI Implementation with Contract Fixtures**
Depends on: Phase 1

**2. [ComponentName]:**
<!-- Repeat per new or modified UI component. -->
- [ ] Create `[repo-relative component path]/[ComponentName].tsx` with its structure and props
- [ ] Add form using `[the repo's form approach, e.g. React Hook Form if installed]` with the Phase 1 Zod schema <!-- Include only when the story has a form. -->
- [ ] Configure `[ComponentName]` to read contract fixtures through `[data seam, e.g. typed props from a page loader or a fetcher function]`
- [ ] Handle loading, empty and error states using the contract fixtures
- [ ] Apply design-spec colors (direct hex values), spacing and typography EXACTLY <!-- Include only with a design spec. -->
- [ ] Verify component structure and hierarchy matches design spec EXACTLY <!-- Include only with a design spec. -->
- [ ] Apply Tailwind classes for layout and other styling aspects
- [ ] Implement responsive behavior according to design
- [ ] Write component tests for `[ComponentName]` with contract fixtures
- [ ] Create Playwright visual test in `[component path]/[ComponentName].visual.spec.ts` for mobile, tablet and desktop viewports
- [ ] Add computed-style tests for exact colors (RGB), spacing/layout pixel measurements and typography from the design spec <!-- Include only with a design spec. -->
- [ ] Run manual and accessibility checks (keyboard, labels, contrast) for `[ComponentName]`

**Phase 3: Backend Implementation**
Depends on: Phase 1

**3. Data Model:**
<!-- Include only when the feature adds or changes a database schema. -->
- [ ] Add/Modify relevant models/fields in ORM schema (e.g., `[schema file path]`)
- [ ] Create and run database migration
- [ ] Update database ERD in `docs/erd.md`

**4. [EndpointName]:**
<!-- Repeat per new or changed Route Handler or Server Action. -->
- [ ] Create `[repo-relative route handler path]/route.ts`
- [ ] Implement handler logic (validation with the Phase 1 Zod schemas, processing, auth)
- [ ] Write unit tests for `[EndpointName]` validation, authorization and failure paths
- [ ] Write contract tests proving `[EndpointName]` responses parse against the Phase 1 response schemas
- [ ] Verify the implemented handler matches the API contract in Technical Approach and update the contract, schemas and fixtures together if it differs

**Phase 4: API Integration with Real Data**
Depends on: Phase 2, Phase 3

**5. Integrate [ComponentName]:**
<!-- Repeat per component that moves from contract fixtures to real data. -->
- [ ] Replace contract fixtures with real `[EndpointName]` calls in `[ComponentName]`
- [ ] Update state management to handle real data fetching
- [ ] Map real API error responses to `[ComponentName]` error states
- [ ] Add loading states connected to real data fetching
- [ ] Update component tests for `[ComponentName]` to cover real data fetching (mocked at the network boundary with the contract fixtures)

**6. End-to-End Testing:**
- [ ] End-to-end testing of `[user flow]` with UI and API integration

**7. Final Documentation & Polishing:**
- [ ] Add JSDoc documentation
- [ ] Final review of integration
- [ ] Performance checks with real data

## Checklist Rules

- **Phase 1 — Data Contract**: types, Zod schemas and typed contract fixtures only; no UI, persistence or handler logic. Encode contracts from design inputs (for example an OpenAPI spec or SAD API section) when they exist. Its gate proves every fixture parses against its schema.
- **Phase 2 — UI with contract fixtures** (depends on Phase 1 only): one `[ComponentName]` task per new or modified UI component carrying its build, fixture wiring, states, styling, and its own component, visual and accessibility tests. Phase 2 leaves a working UI on contract fixtures, and its fixtures exercise every UI state.
- **Phase 3 — Backend** (depends on Phase 1 only, so it can run in parallel with Phase 2): Data Model (only with a schema change), then one `[EndpointName]` task per Route Handler or Server Action. Each endpoint validates with the Phase 1 schemas and proves its responses conform to them.
- **Phase 4 — API Integration** (always last; depends on Phases 2 and 3): one `Integrate [ComponentName]` task per component moving to real data, End-to-End Testing, Final Documentation & Polishing. Phase 4 leaves the feature working on real data.
- Contract fixtures are not throwaway mocks: they are the agreed contract in example form and stay as test fixtures after integration.
- No UI: omit Phase 2 and the Integrate tasks; Phase 4 keeps End-to-End (or API flow) testing and Final Documentation & Polishing. UI consuming only existing endpoints: Phase 1 encodes the existing contract and Phase 3 is omitted. No API, Server Action or data-driven UI: omit Phases 1, 3 and 4's Integrate and End-to-End Testing tasks, and keep Final Documentation & Polishing at the end of the last remaining phase. Renumber phases consecutively and update `Depends on` lines after omissions.
- Tests live in their slice: schema tests in Data Contract; component, viewport and accessibility tests in the component task; handler and contract tests in the endpoint task. End-to-End Testing is the only test-only task.
- Order: Data Contract; each component (shared/child before parent); Data Model; each endpoint; each integration (after the endpoints it needs); End-to-End Testing; final review.
- **Exit gate commands:** typecheck, lint, tests, migration validation, build (for example `npx tsc --noEmit && npm run lint && npm test && npm run build`).
- **Layer coverage check:** types and contracts (Zod schemas, shared types); data and schema (migration); Server Actions and Route Handlers (input validation, server-side authorization); client components (only where state, effects, refs, browser APIs or event handlers are required); UI states; styling and accessibility; tests.

## Quality Gate Specifics

- **Security:** server-side auth in every Server Action/Route Handler; injection/XSS/CSRF/SSRF/open redirect; secrets never in logs, client bundles, or `NEXT_PUBLIC_*` vars; cite the concrete concern (for example an image domain allowlist).
- **Performance:** query/network efficiency, caching/invalidation, bundle size.
- **Accessibility:** keyboard navigation, labeled controls, semantic markup, color contrast.
- Inventory `Type` values add **Accessibility** for this profile.

## Core Conventions

Apply only when Stack match confirms the baseline; otherwise use the repo's own conventions and state each deviation inline. Code, security, and testing conventions live in `.github/instructions/nextjs-react-typescript.instructions.md` and the `frontend-nextjs-conventions` skill; read them during Discovery and plan work that satisfies them; do not restate them.

- **Greenfield file shape** (the repo's layout wins): `app/(feature)/page.tsx` routes, `app/(feature)/actions.ts` Server Actions, `app/api/(resource)/route.ts` Route Handlers for external consumers, `components/ui/` presentational components, `components/(feature)/` feature components, `lib/validations/` Zod schemas, `server/` shared server-only logic and data access.
- **Version-sensitive behavior:** check the discovered Next.js version for async `params`/`cookies` and caching defaults before planning around them.
- **Test layers:** jsdom does not evaluate CSS breakpoints, so verify responsive behavior with Playwright viewports, not RTL. RTL cannot render async Server Components; extract their logic into plain testable functions and cover the rendered result with Playwright. Test Route Handlers by calling the exported handler with a constructed `Request`. Add at least one real-database integration scenario when persistence changes. Plan the auth state and seed data an E2E spec needs; do not duplicate unit-level cases there.
- **Coverage expectations:** every new Server Action/Route Handler gets a success and a failure scenario; every new form a valid-submit and a validation-error scenario; every new user-facing flow one E2E scenario.
