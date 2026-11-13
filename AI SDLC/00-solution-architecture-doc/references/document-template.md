# Solution Architecture Document Template

Canonical outline for the Solution Architecture Document (SAD) produced in Phase 10 (SAD Assembly). Populate every required section in this order; skip or mark "Not applicable" for sections flagged **Conditional** where [Scope Tiers](./scope-tiers.md) says they don't apply to the confirmed Solution Scope Tier. Do not omit a required section without recording a rationale in Section 20 (Assumptions & Dependencies).

## Header

```markdown
# <Initiative Name> — Solution Architecture Document

**Solution Scope Tier:** Feature/Service | Application | Program
**Version:** 1.0
**Author:** <Solution Architect>
**Status:** Draft | Review | Approved
```

## 1. Executive Summary

Purpose of the initiative in 3-5 sentences. Table: `Driver | Description` for business drivers. Bulleted list of expected benefits.

## 2. Business Context & Objectives

Problem statement (current challenges as bullets) and initiative objectives table: `Objective | KPI`.

## 3. Stakeholders

Table: `Stakeholder | Role | Interest/Concern`.

## 4. Functional Requirements

Table: `ID | Requirement | Priority`.

## 5. Non-Functional Requirements

Table: `Requirement | Target` (performance, availability, scalability, security, cost, operability, supportability, data retention, RPO/RTO).

## 6. Current State Summary

Narrative of current systems, integrations, and technical debt relevant to this initiative's scope. Include a dependency list for systems this initiative touches.

## 7. Enterprise Standards & Constraints

State whether enterprise architecture principles, technology mandates, or platform standards were confirmed in discovery. If confirmed, list them as binding constraints. If none were known, state this explicitly as an Assumption rather than inventing standards. Bullet list of additional constraints (technology, organizational, regulatory, vendor, budget, timeline).

## 8. Solution Options Considered

For each candidate option (count per [Scope Tiers](./scope-tiers.md)), document: Description, Advantages, Disadvantages, Cost, Complexity, Risk, Integration Complexity, Technical Debt Impact, Future Extensibility. Score each option using [Evaluation Frameworks](./evaluation-frameworks.md) → Solution Options Scoring Rubric. Close with a summary table: `Option | Score | Decision`.

## 9. Recommended Solution

State the selected option and explain why, referencing the scoring, the requirements from Sections 4-5, and any binding constraints from Section 7. Record the key design decisions and assumptions behind the recommendation.

## 10. Solution Architecture Overview

Table: `Component | Purpose`. State the architecture style (event-driven, microservices, REST, modular monolith, etc.) with rationale. Diagram: Context Diagram (see Diagram Templates).

## 11. Application & Component Design

Component-level design of services and their responsibilities. Diagram: Component Diagram.

## 12. API & Integration Specification

API style, versioning approach, and contract summary. Table: internal integrations `System | Method | SLA`; external integrations as bullets. Integration principles (API-first, async where applicable, retry policy, circuit breaker, idempotency). Diagram: Sequence Diagram for the primary flow(s); Integration Diagram for Application and Program tiers.

## 13. Data Architecture & Data Flow

Data flow narrative, database design approach, data classification and retention rules. Diagram: Data Flow Diagram (Application and Program tiers required; optional for Feature/Service).

## 14. Security Architecture

Authentication, authorization model, data protection (encryption at rest/in transit, secrets management), and security controls relevant to this initiative's scope.

## 15. Infrastructure & Deployment Architecture

Runtime topology narrative. Diagram: Deployment Diagram (required for Application and Program tiers; required for Feature/Service only if new infrastructure is introduced).

## 16. Network Architecture

**Conditional** — see [Scope Tiers](./scope-tiers.md). Connectivity, security zones, and network changes introduced by this initiative. Diagram: Network Diagram.

## 17. Non-Functional Validation

Validation of the recommended architecture against Section 5 targets using [Evaluation Frameworks](./evaluation-frameworks.md) → Non-Functional Validation Checklist. Record any gaps and the design adjustments made to close them.

## 18. Operational Model

Support tiers, monitoring/alerting approach, logging approach, and runbook expectations, scaled to the confirmed tier.

## 19. Disaster Recovery & Resilience

**Conditional** — required for Application and Program tiers, or when a Section 5 requirement demands it for Feature/Service. RPO/RTO targets, failover strategy, backup approach.

## 20. Migration & Rollout Plan

Phased plan with an explicit rollback strategy per phase. **Conditional roadmap diagram**: include the Roadmap/Timeline diagram (Diagram Templates) only for the Program tier or when a phased delivery was confirmed in discovery.

## 21. Assumptions & Dependencies

Bullet list. Every assumption must trace back to an unresolved discovery item; every dependency must name the owning team or vendor.

## 22. Risks

Risk register — see [Evaluation Frameworks](./evaluation-frameworks.md) → Risk Register Format.

## 23. Cost Considerations

Table: `Item | Cost Driver | Notes`. State cost assumptions and any budget ceiling from discovery. This is a technical cost consideration, not a commercial pricing exercise.

## 24. Architecture Decisions

ADR log — see [Evaluation Frameworks](./evaluation-frameworks.md) → Architecture Decision Record (ADR) Format.

## 25. Appendices

Table: `Diagram | Purpose` listing every diagram produced in Phase 5/6, plus any supplementary material (glossary, reference architectures, vendor documentation links).
