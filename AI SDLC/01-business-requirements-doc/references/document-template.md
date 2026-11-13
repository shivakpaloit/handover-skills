# Document Template

Use exactly this section order. Replace bracketed placeholders with terms from the actual input domain, but keep every section present. Do not delete a section that seems inapplicable; mark it `Not applicable — <reason>`.

## Skeleton

```markdown
# Business Requirements Document (BRD)

## <Product Name>

**Document Version:** 1.0
**Document Status:** Draft
**Product Owner:** TBD
**Business Sponsor:** TBD
**Date:** <current date>

---

# 1. Document Purpose
# 2. Executive Summary
# 3. Business Problem
# 4. Business Opportunity
# 5. Product Vision
# 6. Business Objectives
# 7. Product Scope
# 8. Out of Scope
# 9. Stakeholders
# 10. Personas
# 11. Product Capability Map
# 12. End-to-End Primary Journey
# 13. Primary Journey Requirements
# 14. Business Requirements — Account & Access
# 15. Business Requirements — Discovery / Catalogue
# 16. Business Requirements — Selection & Cart-equivalent
# 17. Business Requirements — Checkout & Payment / Fulfilment Trigger
# 18. Business Requirements — Core Entity & Transaction
# 19. Core Entity Lifecycle
# 20. Business Requirements — Supply-side / Partner Role
# 21. Business Requirements — Fulfilment / Execution Role   <!-- Conditional -->
# 22. Notification Requirements
# 23. Cancellation Requirements
# 24. Feedback Requirements (ratings/reviews or equivalent)  <!-- Conditional -->
# 25. Operational Requirements
# 26. Business Rules
# 27. Exception Scenarios
# 28. User Stories
# 29. Acceptance Criteria
# 30. MVP Prioritisation (MoSCoW)
# 31. Success Measures
# 32. Assumptions
# 33. Business Constraints
# 34. Dependencies
# 35. Business Risks
# 36. Open Business Decisions
# 37. Requirement Traceability
# 38. Product Principles
# 39. Definition of Business Acceptance
# 40. What This BRD Deliberately Does Not Define
# 41. Approval
# Appendix A — Glossary
# Appendix B — Requirement ID Convention
```

Keep section numbers sequential once conditional sections are included or marked not applicable. The numbers above are illustrative, not fixed literals.

## Section Content Guidance

The list below is grouped by content type, so its item numbers do not match the skeleton's section numbers.

1. **Document Purpose** — Bulleted list of what the document establishes (problem, outcomes, users, scope, capabilities, journeys, requirements, rules, acceptance criteria, success measures, assumptions/constraints/risks/dependencies, open decisions). Close with a line stating this is a **technology-neutral** foundation for subsequent solution design.
2. **Executive Summary** — 1-2 sentences framing what the business intends to provide. Include the actor relationship box diagram (primary actor, then the business/platform, then the other actor roles), using real actor names. State which end-to-end journey the initial release focuses on and close with a sentence on the underlying philosophy (for example predictability, or clear ownership at every stage).
3. **Business Problem** — "3.1 Current Problem": what each actor group struggles with, as bullets per actor, followed by a bulleted list of consequences of not solving it (uncertainty, missed transactions, manual coordination, poor visibility, difficulty handling exceptions, limited insight).
4. **Business Opportunity** — A single journey arrow (`Step 1 → Step 2 → Step 3 → ...`) of the target flow, followed by a short list of **future capabilities this unlocks but that are NOT in the initial release**, adapted to the domain.
5. **Product Vision** — One blockquoted sentence combining primary-actor value and manageability for the other roles.
6. **Business Objectives** — `BO-01` to `BO-0N`, each a short heading plus a one-sentence objective. Always include a primary-actor-facing objective, a transparency/visibility objective, a supply-side/partner enablement objective (if such a role exists), a coordination objective (if multiple roles hand off work), an operational-visibility objective, and a "sustainable foundation for future capability" objective.
7. **Product Scope — In Scope** — Grouped by actor role (primary actor, each supply-side/partner role, each fulfilment role, business operations); each a bullet list of capabilities, not implementation detail.
8. **Out of Scope** — Bullets of capabilities explicitly excluded from the initial release, closed with "These may be considered as future product opportunities."
9. **Stakeholders** — Table `Stakeholder | Interest`. Include every actor role plus relevant internal functions (support, operations, finance, product, business leadership, compliance/legal where relevant).
10. **Personas** — One persona per primary actor role from the Discovery Pass. Each has **Goal**, **Needs** (bullets), and **Pain points** (bullets).
11. **Product Capability Map** — ASCII tree: product name at top, branching into the capability domains of the core journey and the supporting management domains that exist for this product. Do not assume a fixed count or fixed names.
12. **End-to-End Primary Journey** — Vertical ASCII flow from initial discovery/entry to the natural end state (completion and, if applicable, feedback).
13. **Primary Journey Requirements** — One subsection per major journey stage, describing the information/capability the primary actor needs at that stage. Narrative only, no requirement IDs yet. Include a status-checklist diagram (✓/●/○) for the progress-tracking stage if the domain has one.
14. **Business Requirements (skeleton sections 14-27)** — Group requirements into capability sections that fit the domain. Do not force sections that do not apply (for example omit selection/cart for a product with no selection step; omit fulfilment/execution for a product with no physical or third-party execution handoff). Each requirement is `### BR-0NN — <Title>` followed by exactly one "shall" sentence: `The product shall...` or `<Actor> shall be able to...`. Number sequentially across the whole document; never restart per section.
    - **Core Entity Lifecycle** — ASCII state-machine diagram of the entity lifecycle, followed by a line noting that exact transition rules are defined as business rules.
    - **Notification Requirements** — Table `Business Event | Primary Actor Notified? (Yes/No)` covering every major lifecycle transition and failure event. Close with a line deferring channel choice to a later decision.
    - **Business Rules** — `## BRULE-0NN — <Title>` entries with their own numbering sequence. Cover at minimum: eligibility/availability rules, an "unavailable resource cannot be actioned" rule, a total/price-transparency rule (if money is involved), a confirmation-completeness rule, a rejection rule, a cancellation-depends-on-state rule, a refund-eligibility rule (if applicable), and access-control rules for every actor (each actor accesses only their own data/scope).
    - **Exception Scenarios** — `### E-00N — <Title>` entries, each with a one-line scenario description and a bulleted **Expected business outcome**. Where applicable cover: transaction/payment failure, supply-side rejection, resource unavailable after selection, no execution/fulfilment capacity, assigned party declining, failed execution/fulfilment, and actor-initiated cancellation. Omit categories that do not exist in the domain rather than inventing them.
15. **User Stories** — Grouped by actor role, `### US-00N — <Short Name>` followed by a blockquoted `> As a <role>, I want <goal> so that <benefit>.` Cover the primary journey end to end for the main actor at minimum. Within each actor group, order stories by the capability dependencies in the MVP Capability Sequence subsection. Do not treat each page or screen as a separate story unless it represents distinct user value.
16. **Acceptance Criteria** — 2-3 worked Given/When/Then examples (not one per requirement): the happy-path primary transaction, a rejection/failure path, and status/progress visibility. Use the bolded `**Given** / **When** / **Then**` labels with bullets underneath.
17. **MVP Prioritisation** — MoSCoW lists: **Must Have**, **Should Have**, **Could Have**, **Won't Have — MVP**. Must Have maps 1:1 to the core end-to-end journey; Won't Have mirrors Out of Scope. Add a `### MVP Capability Sequence & Dependencies` subsection with the table `Stage | Capability/outcome | Depends on | Can proceed in parallel with | Stories/requirements`. Order by business prerequisites, not by screen or document order. Identify the smallest complete end-to-end MVP slice, distinguish hard dependencies from useful sequencing, and call out cross-cutting requirements (accessibility, mobile, privacy, search) to address throughout rather than at the end. Mark unclear dependencies TBD; do not invent technical tasks or architecture.
18. **Success Measures** — Grouped by actor lens (one group per actor role plus Business/Commercial), each a bullet list of measurable indicators (rates, counts, satisfaction, retention). Close with: "Specific numerical targets should be agreed with the business sponsor before launch."
19. **Assumptions** — Numbered list (no IDs), 5-8 items covering scope boundaries, actor responsibilities (who maintains what data, who performs manual/physical work), and a note that critical policy details will be agreed before MVP completion.
20. **Business Constraints** — Bullets of constraints that plausibly apply (coverage/scope limits, partner/supply capacity, supported payment or access methods, regulatory requirements, operating hours, support model).
21. **Dependencies** — Bullets of things the product depends on (onboarding processes, third-party services, operational processes, legal/business approvals), closed with a line noting technical implications are out of scope.
22. **Business Risks** — Table `Risk | Business Impact`, 6-8 rows relevant to the domain (supply/capacity shortage, high rejection/failure, data quality, high cancellation, transaction failures, poor experience/churn, slow support).
23. **Open Business Decisions** — Numbered list of 10-17 unresolved questions to answer before sign-off (scope boundaries, supported methods/channels, policy thresholds, onboarding data, definition of "successful" completion, exception policy, mandatory notifications, targets/KPIs).
24. **Requirement Traceability** — ASCII vertical flow `Business Objective → Business Requirement → User Story → Acceptance Criteria → Product Backlog → Business Acceptance`, then a worked example table `Objective | Requirement | User Story | Acceptance`.
25. **Product Principles** — 5-6 named principles (for example Actor First, Transparency, Predictability, Simplicity, Clear Ownership, Recoverability), each a short heading plus one sentence.
26. **Definition of Business Acceptance** — Bullet checklist of the end-to-end capabilities that must all work for MVP acceptance, ending with "All agreed MVP acceptance criteria have been satisfied."
27. **What This BRD Deliberately Does Not Define** — Bullets for: application architecture, system architecture, microservices vs. monolith, APIs, databases, cloud providers, messaging technology, caching, infrastructure, deployment models, programming languages, technical security implementation, integration architecture, technical scalability mechanisms. Close by naming the Solution Architect as owner of those decisions, using this BRD as input.
28. **Approval** — Table `Role | Name | Status`, all rows `TBD | Pending` (typically Product Owner, Business Sponsor, Operations Representative, Finance Representative, and a representative of the primary actor role).
29. **Appendix A — Glossary** — Table `Term | Definition` covering every domain-specific noun introduced (actor roles, core entity, lifecycle states, MVP, BRD, Business Rule, Acceptance Criteria).
30. **Appendix B — Requirement ID Convention** — Table `Prefix | Meaning` for every ID prefix actually used (`BO`, `BR`, `BRULE`, `US`, `E`, and the document's own acronym).

## Closing Line

End the document with one short reflective sentence noting that it hands the **what/why** to delivery and architecture teams while deliberately leaving the **how** to the Solution Architect.
