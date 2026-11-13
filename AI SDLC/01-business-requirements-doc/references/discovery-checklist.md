# Discovery Checklist

## Step 0 — Identify the Input

Determine what the user has given you, in priority order:

1. An existing product brief, notes, or partial requirements: treat as the primary source of truth; do not contradict it.
2. A meeting transcript or informal description of a product or feature idea: extract the business problem, actors, goals, and constraints directly from it.
3. A bare idea or one-line pitch: apply the Clarification Gate below before drafting.

If no input is provided, ask for a one-paragraph description of the product or idea (use the interactive question UI when available, with free-text input). Never fabricate a business domain.

At the top of the generated document, set the status to **Draft**, Product Owner and Business Sponsor to **TBD** unless named, and use the current date.

## Clarification Gate

The input must tell you all five of:

1. The business problem.
2. Who the primary actors/users are.
3. What success looks like.
4. The single end-to-end journey the MVP must support.
5. Any known constraint or deadline.

**If any item is missing**, do not draft the full BRD. Run a conversational clarification interview:

1. On the first turn only, restate what you understand in 3-5 lines.
2. Ask exactly **one** question per response, targeting the highest-priority missing item. Use the interactive question UI when available instead of plain chat text. Offer 2-5 concise, domain-appropriate selectable options when answers are predictable, always include **Other / I will describe it**, and allow free text. Do not list or preview remaining questions.
3. Wait for the answer before asking the next question. Never repeat an answered question.
4. Ask only what is needed to establish the five areas, with no more than 8 questions in total.
5. Include a selectable **Proceed with assumptions** option on every question. If the user selects it or answers "proceed" (or equivalent), stop asking and fill remaining gaps with clearly reasoned, industry-standard assumptions flagged **TBD** or captured in Assumptions / Open Business Decisions.
6. When all five areas are answered, confirm briefly that the discovery gate is complete and generate the full BRD in the next response.

**If the input already covers all five**, or the user has said "proceed" to a prior round, go straight to the Discovery Pass and draft the full document. Every invented target, policy, or numeric figure must be flagged **TBD** or captured in Assumptions / Open Business Decisions, never stated as settled fact.

Treat clarification as one interview session for the current input; do not restart it or loop waiting for a perfect answer.

## Discovery Pass

Before drafting, work out the following, inferring sensibly where the input is silent and recording every inference as an assumption:

- The core business problem and who experiences it.
- The primary actor/role groups (typically 2-4: a primary end user, zero or more supply-side/partner roles, zero or more fulfilment/execution roles, and internal operations staff). Name each role using terminology from the user's own input, never a stock role name from an unrelated domain.
- The core business entity (for example an order, application, booking, ticket, claim, or shipment) and the single end-to-end MVP journey around it.
- Business objectives (outcome-oriented, not feature-oriented).
- What is in scope versus out of scope for the initial release, and what is a credible future opportunity.
- The natural lifecycle/state machine of the core entity.
- Business rules that constrain the lifecycle (ownership/access, availability, transition rules).
- Exception and failure scenarios the business must answer.
- How success is measured (primary-actor, supply-side/operational, and business/commercial angles).
- Constraints, dependencies, and risks.
- The business-capability sequence needed to deliver the MVP: hard prerequisites, capabilities that can proceed in parallel, and cross-cutting requirements that apply throughout. Keep this at product/business level; do not prescribe technical implementation order.
- Unresolved decisions that must be answered before sign-off.
