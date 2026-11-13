# Style and Quality Rules

## ID Conventions

| Prefix | Meaning | Format |
|---|---|---|
| `BO` | Business Objective | `BO-01` |
| `BR` | Business Requirement | `### BR-0NN — <Title>` |
| `BRULE` | Business Rule (own sequence, separate from `BR`) | `## BRULE-0NN — <Title>` |
| `US` | User Story | `### US-00N — <Short Name>` |
| `E` | Exception Scenario | `### E-00N — <Title>` |

- Every requirement, rule, story, and exception gets a stable ID. Number sequentially in the order sections appear and never renumber.
- `BR-0NN` numbering runs across the whole document and does not restart per section.
- These IDs are consumed downstream: the `user-story` skill maps stories to `BR-0NN`, and the test-case skills use `BRULE-0NN` and `E-00N`. Keep them stable and unique.

## Writing Rules

- Write requirements as testable "shall" statements, one capability per requirement. Do not join two testable behaviors with "and".
- Never mention a specific technology, framework, database, or vendor in the body. If the input specifies one, record it as a constraint for the Solution Architect, not as a section topic.
- Mark every unresolved number, policy, or threshold **TBD** inline, or list it in Open Business Decisions / Assumptions. Never state it as a firm fact.
- Describe outcomes and behavior, not screens, tables, or endpoints.
- Never carry over actor names, entity names, or example content from the template placeholders. Use real domain names from the user's input.
- Include only sections and capability groups that genuinely apply. Mark skipped sections `Not applicable — <reason>` instead of omitting them silently.
- End with the closing line defined in [Document Template](./document-template.md).

## Pre-Save Quality Checklist

- [ ] All sections present, in template order, with sequential numbering.
- [ ] Header shows Status **Draft**, Product Owner and Sponsor **TBD** (unless named), and the current date.
- [ ] Every diagram uses real domain labels; no `<PLACEHOLDER>` text remains.
- [ ] `BO`, `BR`, `BRULE`, `US`, and `E` IDs are sequential, unique, and listed in Appendix B.
- [ ] Each `BR` is a single "shall" sentence.
- [ ] Must Have items map 1:1 to the core journey; Won't Have mirrors Out of Scope.
- [ ] MVP Capability Sequence table is present and contains no technical tasks.
- [ ] No technology, vendor, or architecture terms appear outside "What This BRD Deliberately Does Not Define".
- [ ] Every invented figure or policy is **TBD** or listed in Assumptions / Open Business Decisions.
- [ ] Glossary covers every domain noun introduced.
