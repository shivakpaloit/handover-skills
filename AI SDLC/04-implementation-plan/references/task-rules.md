# Checklist Format and Task Rules

Apply these when writing the Tasks section. They are instructions for the planner, not plan content: do not copy them into the plan. They override any conflicting rule elsewhere in this skill.

## Required Checklist Format

- The Tasks section reproduces the `**Implementation Checklist:**` structure using the **Checklist Template** of the selected stack profile (and, for more than one profile, [multi-stack.md](./multi-stack.md)).
- Keep the profile's task names, subtask wording, and template order as the baseline; replace bracketed placeholders with this story's real names. Repeat a templated task once per area (component, entity, service, client, endpoint, integration). Number tasks consecutively across the final list.
- Omit tasks or whole phases the profile marks optional when they do not apply; never leave an empty phase. Record every omission, repeat, and adaptation in the **Phase structure rationale** line.

## Shape

- **A task is a numbered bold heading; a subtask is a `- [ ]` line beneath it.** Task headings carry no checkbox and are the default unit of execution. Do not create a parent subtask with smaller steps; make separately verifiable steps sibling subtasks.
- **A task is a focused context unit, finished before the next begins.** Each task is one vertical slice of one logical area that an agent can build, test and verify in one session with only that area's context loaded. Do not group by layer across areas (all code, then all tests). Split a task spanning several independent areas or exceeding about twelve subtasks; name splits `**N. Name — Area:**`. Do not create single-subtask tasks or merge unrelated areas.
- **One outcome per subtask** — one observable behavior or one clearly bounded change. Do not bundle independent outcomes, and do not split a coherent behavior into artificial code-versus-test subtasks; an area's tests belong in its own task.
- **Story-specific, not generic.** Each subtask names this story's entity, component, service, endpoint, rule, or behavior. Add subtasks when an AC needs behavior the template does not cover (an additional rule, state, transition, or ownership check).
- **Nothing beneath a subtask.** A subtask may name its file inline, but never add IDs, nested items, descriptions, AC links, test links, commands, or status fields.
- **Order is the dependency model within a phase.** Tasks run in numbered order per the profile's order rule; shared prerequisites come first. Do not add task-level dependency IDs or parallelizable flags; dependencies between phases live only on each phase's `Depends on` line.

## Verification

- Check a subtask only after its implementation and relevant verification are complete. If blocked, leave it unchecked and explain under Risks, Dependencies & Open Questions.
- Each area task includes focused tests naming the behavior they prove; flow tests go in the profile's integration/E2E task. Record test files in the Test Scenario Inventory and commands in Test Execution Approach or the Exit gate, not beneath subtasks.
- Include failure-path tests for security-relevant behavior (authentication, authorization, ownership, input validation).
- Each phase has one Exit gate after its last task, followed by `Gate result: Not run`: the profile's gate commands plus which ACs are now provable. The last phase's gate also confirms every AC has a passing scenario.

## Contract-First Phasing

Plan so that no work stream waits on another's implementation — only on an agreed data contract.

- **Data Contract phase first** whenever the story has an API, Server Action, message, or data-driven UI. It defines the request/response types and validation schemas, confirms the contract recorded in Technical Approach, and creates contract fixtures (populated, empty, validation-error, unauthorized and failure examples) typed against those schemas. It contains no UI, persistence, or handler logic. Its gate proves every fixture conforms to its schema.
- **Adopt existing design inputs.** When the Design inputs (OpenAPI spec, SAD interface or API section, sequence or ER diagrams) already define the contract, the Data Contract phase encodes them rather than redefining them; record any deviation under Open Questions.
- **Build phases depend only on the contract.** The UI phase builds against contract fixtures; the backend/provider phase implements the contract and proves its real responses conform to the same schemas. Neither depends on the other, so both may start once the Data Contract gate passes.
- **API Integration is always the last phase.** It swaps fixtures for real calls, wires the API client, maps real errors to UI states, and holds end-to-end testing and final polishing. It depends on every build phase. No integration subtask (replacing fixtures, real data fetching, cross-unit E2E) appears earlier. Contract fixtures stay as test fixtures afterwards.
- **Contract changes are explicit.** If a build phase must change the contract, the same subtask updates the schemas, fixtures and Technical Approach contract, and the change is recorded under Risks; implementations never diverge silently.
- Omit the Data Contract phase only when the story has no API, interface, or data-driven UI (for example a pure styling change), and record why in the Phase structure rationale.

## Phases

- Phases are the profile's milestones. Every subtask sits under exactly one task, every task under exactly one phase.
- **Each phase has a `Depends on` line** directly under its heading: `None`, or the phases whose Exit gates must pass first. Phases with disjoint dependencies may run in parallel; the API Integration phase depends on every build phase. Never create a dependency cycle.
- **Final decomposition audit:** each task is one focused area, each subtask one clear outcome, order respects dependencies, every omission has a recorded reason, no subtask is generic, and the profile's **Layer coverage check** is satisfied across the subtasks and technical/test sections.
- **Oversized-story warning:** if the checklist exceeds about fifty subtasks, still produce the plan and add an open question recommending the story be split.

## Status Handling

- Subtask checkboxes are the single source of progress. A task is complete when all its subtasks are checked. The overall `Status` is derived (`Not Started` = none checked; `Completed` = all checked; otherwise `In Progress`). Tasks and phases carry no status field; a phase is complete when all its checkboxes are checked and its `Gate result` records a pass.
- Do not start a phase until every phase on its `Depends on` line has a recorded passing Exit gate. Replace `Not run` with the result and date when the gate runs.
