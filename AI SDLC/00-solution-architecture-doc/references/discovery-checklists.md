# Discovery Checklists

Use these checklists during Phase 1 (Initiative Discovery & Scope Tier Determination) and Phase 2 (Requirements Discovery). Ask about every item below before drafting the Document Template. Record confirmed answers directly into the corresponding template section. Record unresolved items as a labeled **Assumption** rather than inventing a value.

## Phase 1: Initiative Discovery

| Topic                 | Ask About                                                                                                                         |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Business overview     | Organization, business unit, product/service context                                                                              |
| Initiative objectives | The business outcome this specific initiative must deliver                                                                        |
| Pain points           | Current problems, quantified where possible                                                                                       |
| Systems in scope      | Systems being built, replaced, extended, or integrated for this initiative                                                        |
| Stakeholders          | Sponsors, product owner, technical lead, compliance/security contacts                                                             |
| Success criteria      | Measurable KPIs and definition of done for this initiative                                                                        |
| Timeline              | Target milestones, hard deadlines                                                                                                 |
| Constraints           | Technology, organizational, regulatory, or vendor constraints                                                                     |
| Enterprise standards  | Whether enterprise architecture principles, technology mandates, or platform standards exist                                      |
| Scope signal          | Whether this initiative is a single feature/service, a new/re-architected application, or a coordinated multi-application program |

Feeds Document Template sections: Executive Summary, Business Context & Objectives, Stakeholders, Enterprise Standards & Constraints.

Use the Scope Signal answer to determine the Solution Scope Tier in [Scope Tiers](./scope-tiers.md) before proceeding to Phase 2.

## Phase 2: Requirements Discovery

### Functional Requirements

Collect as `ID | Requirement | Priority` (High/Medium/Low).

### Non-Functional Requirements

Confirm a measurable target for each, recorded as `Requirement | Target`:

- Performance (response time, throughput)
- Availability (uptime %)
- Scalability (peak load, user/transaction volume)
- Security (controls, standards)
- Cost (budget signal or cost ceiling)
- Operability (support model expectations)
- Supportability (documentation, runbook, and maintainability expectations)
- Data retention (duration, archival rules)
- Disaster recovery (RPO, RTO) — required for Application and Program tiers; ask but do not force for Feature/Service tier

### Additional Requirements

- Integration requirements: systems, protocols, SLAs
- Identity requirements: IdP, federation, authentication/authorization model
- Operational requirements: support model, maintenance windows, runbooks
- Migration requirements: cutover approach, data migration, rollback expectations

Feeds Document Template sections: Functional Requirements, Non-Functional Requirements, API & Integration Specification, Operational Model, Migration & Rollout Plan.

## Completion Gate

Do not proceed to Phase 3 (Current State & Enterprise Context) until every row above is either confirmed by the user or explicitly logged as an Assumption in the final document's Assumptions & Dependencies section (Document Template).
