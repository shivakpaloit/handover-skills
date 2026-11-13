# Complexity & Maintainability Rules

Measure every **new or changed** function, class, and file. Report the metric table in the report and raise a finding when a threshold is exceeded **because of the change** (new code, or the change pushed an existing unit over the limit).

## Thresholds

Defaults align with common SonarQube / Codacy profiles. Repo config (e.g. ESLint `complexity`, `.codacy.yml`, `sonar-project.properties`, Pylint, Checkstyle) overrides these.

| Metric | Warn (Medium) | Fail (High) | How to count |
| --- | --- | --- | --- |
| Cyclomatic complexity / function | > 10 | > 20 | 1 + each `if`, `else if`, `case`, loop, `catch`, `&&`, `||`, `?:`, `??` |
| Cognitive complexity / function | > 15 | > 25 | SonarSource method: +1 per break in linear flow (`if`, `else`, loops, `catch`, `switch`, ternary, jumps, mixed boolean operator sequences, recursion); +1 extra per nesting level for nested structures |
| Function length (logical LOC) | > 50 | > 100 | Non-blank, non-comment lines in the body |
| Nesting depth | > 3 | > 5 | Deepest nested control structure |
| Parameters | > 4 | > 7 | Excluding a single options/props object |
| File length | > 400 | > 1000 | Non-blank, non-comment lines |
| Class: methods / fields | > 20 / > 15 | > 40 / > 30 | Public + private |
| Duplicated block | ≥ 6 lines or ≥ 50 tokens repeated | ≥ 3 copies, or > 3% of new lines duplicated | Within the change, or change copies existing code |

Cognitive complexity 15 and cyclomatic 10 match the SonarQube default rule thresholds; 3% duplication on new code matches the Sonar way quality gate.

If counts are approximate (no tool run), say "≈" in the metric table.

## Rules

| Rule | Default | What to look for | Typical fix |
| --- | --- | --- | --- |
| **CPLX-CYC-01** High cyclomatic complexity | per table | Many independent paths in one function | Extract branches into functions; lookup tables/polymorphism instead of long `switch`/`if` chains |
| **CPLX-COG-01** High cognitive complexity | per table | Hard-to-follow control flow, deep nesting, mixed `&&`/`||` chains | Guard clauses / early returns; extract well-named predicates |
| **CPLX-NEST-01** Deep nesting | per table | Arrow-shaped code | Invert conditions, early return, extract inner block |
| **CPLX-LEN-01** Long function / file | per table | Function or file over length threshold | Split by responsibility |
| **CPLX-PARAM-01** Too many parameters | per table | Long positional parameter lists, especially same-typed | Parameter object; split function |
| **MNT-SRP-01** Mixed responsibilities | Medium | Module/class mixing transport, business rules, persistence, and presentation | Separate layers per codebase architecture |
| **MNT-COUPLE-01** Tight coupling | Medium | Direct instantiation of infrastructure in business logic, reaching through objects (`a.b.c.d`), importing internals of another module | Dependency injection, interfaces, public module API |
| **MNT-CYCLE-01** Circular dependency | Medium | New import that creates a cycle between modules | Extract shared piece; invert dependency |
| **MNT-LAYER-01** Layer violation | Medium | UI calling DB directly, domain importing framework/transport types, server-only code imported by client code | Route through the correct layer |
| **MNT-ABSTR-01** Premature or needless abstraction | Low | Interface/factory/generic with one implementation and no foreseeable second; wrapper that only forwards | Inline until needed |
| **MNT-GOD-01** God class / module | Medium | Class/file accumulating unrelated features; over class thresholds | Split by cohesion |
| **MNT-PRIM-01** Primitive obsession | Low | Same group of primitives passed together repeatedly; stringly-typed statuses | Value object / type / enum |
| **MNT-DEBT-01** New technical debt marker | Info | New `TODO`/`FIXME`/`HACK`/`XXX` | Link to a ticket or resolve |

## Reporting

- One finding per function that breaches a threshold; cite the function's full line range and give the measured value vs threshold in **Issue** (e.g. "Cognitive complexity 23 (threshold 15)").
- The **Suggested fix** should show the concrete refactor for the worst part (e.g. extract the nested block into a named function), not a generic "reduce complexity".
- Do not raise complexity findings for tests, generated code, or declarative configuration unless extreme.
