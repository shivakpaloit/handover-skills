---
name: solution-architecture-doc
description: "Provides the canonical Solution Architecture Document (SAD) structure: discovery checklists, Solution Scope Tiers (Feature/Service, Application, Program) that scale diagram depth and template sections, the document template, Mermaid diagram skeletons, a solution-options scoring rubric, a non-functional validation checklist, a risk register format, and an ADR format. Use when compiling initiative/requirements discovery notes, comparing solution options, drawing solution architecture diagrams, validating non-functional requirements, or drafting the final SAD for a specific business initiative."
---

# Solution Architecture Document

## Overview

Reusable structure and templates for producing a Solution Architecture Document (SAD) for a single, already-scoped business initiative. This skill defines _what_ to produce at each stage; it does not define interview behavior (see the Solution Architect agent for that).

## When to Use

- Confirming initiative and requirements discovery is complete before drafting.
- Determining the Solution Scope Tier (Feature/Service, Application, or Program) and which document sections apply as a result.
- Comparing two or more solution options with a consistent scoring rubric.
- Drafting the SAD.
- Producing Mermaid diagrams for context, component, sequence, deployment, integration, data flow, network, and roadmap/timeline views.
- Validating a recommended architecture against non-functional requirement targets.
- Building a risk register or an Architecture Decision Record (ADR) log.

## Resources

- [Discovery Checklists](./references/discovery-checklists.md) — Initiative and Requirements Discovery topics to confirm before drafting.
- [Scope Tiers](./references/scope-tiers.md) — how Solution Scope Tier (Feature/Service, Application, Program) changes the number of solution options compared, diagram depth, and which template sections apply.
- [Document Template](./references/document-template.md) — canonical SAD outline with per-section guidance and conditional sections.
- [Diagram Templates](./references/diagram-templates.md) — Mermaid skeletons for every required diagram type, including the conditional network and roadmap/timeline views.
- [Evaluation Frameworks](./references/evaluation-frameworks.md) — solution-options scoring rubric, non-functional validation checklist, risk register format, ADR format, and the SAD quality bar.

## Procedure

1. Confirm discovery is complete using [Discovery Checklists](./references/discovery-checklists.md), including whether enterprise standards or platform mandates exist. List any open items as Assumptions if the user accepts them unresolved.
2. Determine the Solution Scope Tier using [Scope Tiers](./references/scope-tiers.md) and use it to decide which Document Template sections are required, conditional, or not applicable.
3. Produce candidate solution options scaled to the confirmed tier and score each with the rubric in [Evaluation Frameworks](./references/evaluation-frameworks.md); recommend the highest-scoring option that also satisfies any binding enterprise standards or mandatory constraints.
4. Insert Mermaid diagrams from [Diagram Templates](./references/diagram-templates.md) for each required view, adapted to the project's actual components and scaled to the Solution Scope Tier.
5. Validate the recommended architecture against non-functional targets using the checklist in [Evaluation Frameworks](./references/evaluation-frameworks.md), recording gaps and design adjustments.
6. Populate the risk register and ADR log using the formats in [Evaluation Frameworks](./references/evaluation-frameworks.md).
7. Assemble the final document in the section order defined by [Document Template](./references/document-template.md); do not omit a required section without recording a rationale in the Assumptions section, and mark conditional sections not applicable where Scope Tiers says so.
