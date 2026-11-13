# Evaluation Frameworks

Scoring rubric, non-functional validation checklist, risk register, ADR format, and quality-bar formats used across Phases 4, 7, 8, and 9.

## Solution Options Scoring Rubric

Score every candidate option from Section 8 (Solution Options Considered) against the same weighted criteria. Use a 1-5 scale (5 = best fit). Number of options scored is determined by [Scope Tiers](./scope-tiers.md).

| Criterion                                     | Weight | Option A | Option B | Option C |
| --------------------------------------------- | ------ | -------- | -------- | -------- |
| Functional fit                                | 20%    |          |          |          |
| Non-functional fit                            | 20%    |          |          |          |
| Integration complexity (lower = higher score) | 15%    |          |          |          |
| Cost (lower cost = higher score)              | 15%    |          |          |          |
| Risk (lower risk = higher score)              | 10%    |          |          |          |
| Time to implement (faster = higher score)     | 10%    |          |          |          |
| Future extensibility                          | 10%    |          |          |          |
| **Weighted Total**                            | 100%   |          |          |          |

Recommend the option with the highest weighted total that also satisfies every binding enterprise standard and mandatory constraint from Section 7 (Enterprise Standards & Constraints). If the highest-scoring option fails a mandatory constraint, document why it was disqualified and recommend the next-highest compliant option.

## Non-Functional Validation Checklist

Table for Section 17 (Non-Functional Validation). Every category is required regardless of Solution Scope Tier.

| Requirement Category | Target (from Section 5) | Validation Approach | Status (Met/Partial/Gap) | Notes |
| -------------------- | ----------------------- | ------------------- | ------------------------ | ----- |
| Performance          |                         |                     |                          |       |
| Scalability          |                         |                     |                          |       |
| Availability         |                         |                     |                          |       |
| Security             |                         |                     |                          |       |
| Cost                 |                         |                     |                          |       |
| Operability          |                         |                     |                          |       |
| Supportability       |                         |                     |                          |       |

For every row marked Partial or Gap, describe the design adjustment made (or the risk accepted) directly beneath the table.

## Risk Register Format

Table for Section 22 (Risks). Cover technical feasibility, integration, security/compliance, operational, and delivery-timeline categories at minimum:

| Risk | Description | Category | Likelihood      | Impact          | Mitigation | Owner | Residual Risk   |
| ---- | ----------- | -------- | --------------- | --------------- | ---------- | ----- | --------------- |
|      |             |          | High/Medium/Low | High/Medium/Low |            |       | High/Medium/Low |

## Architecture Decision Record (ADR) Format

Use one ADR per major decision in Section 24 (Architecture Decisions). Open the section with a summary table, then include the full ADR for each row. Expected count per tier is defined in [Scope Tiers](./scope-tiers.md).

Summary table:

| #       | Decision | Status                       |
| ------- | -------- | ---------------------------- |
| ADR-001 |          | Proposed/Accepted/Superseded |

Full ADR template (repeat per decision):

```markdown
### ADR-NNN: <Decision Title>

**Status:** Proposed | Accepted | Superseded

**Context**
What problem or forces led to this decision.

**Decision**
What was decided.

**Alternatives Considered**
Other options and why they were not selected.

**Consequences**
Resulting trade-offs, both positive and negative.
```

## SAD Quality Bar

Before finalizing the document, verify it:

- Starts with business outcomes before technical details.
- Explicitly traces functional and non-functional requirements to architectural decisions.
- Presents solution options with trade-off analysis and rationale, scaled to the confirmed Solution Scope Tier.
- Validates every non-functional category against a measurable target, not just the ones with obvious gaps.
- States explicitly whether enterprise standards were confirmed or assumed absent, never silently inventing them.
- Includes diagrams that progressively move from business context to implementation detail, scoped to the confirmed tier.
- Identifies risks, assumptions, and dependencies with named owners.
- Defines a migration/rollout approach with an explicit rollback strategy.
- Ends with clear architectural decisions recorded as ADRs.
