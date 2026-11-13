---
name: business-requirements-doc
description: "Provides the canonical, technology-neutral Business Requirements Document (BRD) structure: input identification, a clarification gate and discovery checklist, the 41-section document template with per-section guidance, ASCII diagram conventions, requirement ID conventions (BO/BR/BRULE/US/E), and a style and quality bar. Use when drafting or reviewing a BRD for any product, idea, meeting transcript, or informal brief, before user stories, test cases, or solution architecture are produced."
---

# Business Requirements Document

## Overview

Reusable structure and rules for producing a complete, **technology-neutral** Business Requirements Document (BRD) saved as `docs/business_requirements_document.md`. The BRD defines **what** the business needs and **how the product should behave**, never **how** it is built. All "how" decisions are deferred to the Solution Architecture stage. This skill defines _what_ to produce; it does not define interview behavior (see the BRD Author agent for that).

The skill is domain-agnostic. Derive every actor name, entity name, and journey step from the user's actual input, never from a template industry.

## When to Use

- Creating a BRD from a product brief, meeting transcript, informal description, or one-line idea.
- Confirming the five discovery areas are covered before drafting.
- Reviewing an existing BRD against the standard section order, ID conventions, and style rules.
- Preparing the traceable source (`BR-0NN`, `BRULE-0NN`, `E-00N`) consumed by the `user-story`, `test-case-creation`, and `test-case-workbook-creation` skills.

## Resources

- [Discovery Checklist](./references/discovery-checklist.md) — input priority, the Clarification Gate, interview rules, and the Discovery Pass.
- [Document Template](./references/document-template.md) — exact section order and numbering, the Markdown skeleton, and per-section content guidance.
- [Diagram Conventions](./references/diagram-conventions.md) — ASCII shapes for actor relationships, journeys, lifecycle, status checklist, and capability map.
- [Style and Quality Rules](./references/style-and-quality-rules.md) — ID conventions, writing rules, the technology-neutrality rule, and the pre-save quality checklist.

## Procedure

1. Identify the input using [Discovery Checklist](./references/discovery-checklist.md). If none is supplied, ask for a one-paragraph description; never fabricate a business domain.
2. Apply the Clarification Gate. If any of the five areas is missing, run the one-question-at-a-time interview; do not draft the full BRD until the gate is complete or the user chooses to proceed with assumptions.
3. Run the Discovery Pass and record every inference as an assumption.
4. Assemble the document in the exact section order of [Document Template](./references/document-template.md), keeping every section present. Mark inapplicable sections `Not applicable — <reason>` rather than deleting them, and keep numbering sequential.
5. Draw each diagram using [Diagram Conventions](./references/diagram-conventions.md) with labels from the real domain.
6. Apply [Style and Quality Rules](./references/style-and-quality-rules.md): stable IDs, one-capability "shall" statements, no technology mentions, and every unresolved figure marked **TBD** or listed in Assumptions/Open Business Decisions.
7. Save to `docs/business_requirements_document.md` (create `docs/` if needed; replace the file if it exists unless the user names another file), then verify the file was written and report the workspace-relative path.
