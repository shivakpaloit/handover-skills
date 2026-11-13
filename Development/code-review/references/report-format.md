# Report Format

## Severity And Action

| Severity | Action | Meaning | Typical examples |
| --- | --- | --- | --- |
| **Critical** | Must fix (blocks merge) | Exploitable vulnerability, data loss/corruption, or crash on a common path | Injection, hard-coded secret, auth bypass, unhandled null on main path |
| **High** | Must fix | Likely bug or significant security/performance weakness | Missing authorization check, N+1 on a list endpoint, swallowed exception hiding failures |
| **Medium** | Should fix | Robustness or maintainability problem that will cost later | Cognitive complexity over threshold, duplicated logic, sequential independent awaits |
| **Low** | Consider (nit) | Minor smell or readability issue | Magic number, unclear name, dead code |
| **Info** | FYI | No expected impact; follow-up idea | Possible simplification, new TODO |

Severity = impact × likelihood in **this** code. If you change a rule's default, state why in one sentence. Sonar mapping: Critical ≈ Blocker, High ≈ High/Critical, Medium ≈ Medium/Major, Low ≈ Low/Minor.

## Categories

| Category | Internal rule prefix | Sonar software quality |
| --- | --- | --- |
| Security | `SEC` | Security |
| Error Prone (bugs, correctness) | `BUG` | Reliability |
| Performance | `PERF` | Reliability / Efficiency |
| Complexity | `CPLX` | Maintainability |
| Maintainability | `MNT` | Maintainability |
| Clean Code | `CLN` | Maintainability |
| Best Practice (tests, API, a11y, config) | `BP` | Maintainability / Reliability |

## Confidence

| Level | Score | Meaning | Reported as |
| --- | --- | --- | --- |
| **High** | ≥ 0.8 | Concrete path and impact confirmed in the code you read | Normal finding |
| **Medium** | 0.6–0.8 | Clear pattern; one assumption you could not confirm (e.g. input trust, data volume) | Finding with status `Needs review`; state the assumption and how to confirm it |
| **Low** | < 0.6 | Speculative | **Do not report** |

## Quality Gate

Evaluate on new code only. The gate **fails** if any condition is met:

| Condition | Source |
| --- | --- |
| Any Critical finding | Review |
| Any High finding with High confidence (any category — High means Must fix) | Review |
| New-code coverage < 80% (or repo threshold) | Coverage tool, only if available and ≥ 20 new coverable lines |
| New-code duplicated lines > 3% (or repo threshold) | Duplication tool or review, only if ≥ 20 new lines |
| Any failing lint / type-check / test that the change introduced | Checks run |

| Verdict | Rule |
| --- | --- |
| **Failed** | Any condition above met |
| **Passed with warnings** | No fail condition, but any Medium-confidence High, any Medium, or any `Needs review` finding remains |
| **Passed** | Only Low / Info findings, or none |

A finding marked **Must fix** can never coexist with a Passed verdict. If lint, tests, or coverage were not run, append `(provisional — checks not run)` to the verdict.

List each gate condition with its status in the report so the verdict is auditable.

## Finding Heading

Readers should not see internal codes. Each finding heading is a sequence number, the category, the severity and a plain-language title:

`### <n>. (<Category>) (<Severity>) <Title>`, e.g. `### 1. (Security) (Critical) SQL query built from request input`

- Number findings 1..N in report order. Refer to other findings by number, e.g. "see finding 6".
- Rule IDs in the references (`SEC-INJ-01`, `CLN-MAGIC-01`, …) are for your own lookup only. Never print them in the report.
- For security findings, add a **Reference** line with the CWE and OWASP Top 10:2025 IDs; these are industry standards readers can look up.

## Template

````markdown
# Code Review — <branch / PR / range>

**Scope:** <mode> — e.g. `Uncommitted changes on main` · `Latest commit a1b2c3d — "<subject>"` · `main...feature/x` · <N> files changed · +<added> / -<removed> lines
**Intent:** <1–2 sentences from commits/PR on what the change does>

## Quality Gate: Failed | Passed with warnings | Passed

| Condition | Status |
| --- | --- |
| No Critical findings | ✅ / ❌ (n) |
| No High-confidence High findings | ✅ / ❌ (n) |
| New-code coverage ≥ 80% | ✅ / ❌ (x%) / n/a (<reason>) |
| New-code duplication ≤ 3% | ✅ / ❌ (x%) / n/a (<reason>) |
| No new lint / type / test failures | ✅ / ❌ / not run (<reason>) |

| Severity | Count |   | Category | Count |
| --- | --- | --- | --- | --- |
| Critical | 0 |   | Security | 0 |
| High | 0 |   | Error Prone | 0 |
| Medium | 0 |   | Performance | 0 |
| Low | 0 |   | Complexity | 0 |
| Info | 0 |   | Maintainability / Clean Code / Best Practice | 0 |

## Metrics (changed code)

| File | Function | Cyclomatic | Cognitive | Length (LOC) | Max nesting | Params |
| --- | --- | --- | --- | --- | --- | --- |
| path/to/file.ext | `fnName` | 12 ⚠ | 18 ⚠ | 74 ⚠ | 4 ⚠ | 3 |

Only list functions that are new or changed; mark values over threshold with ⚠ (thresholds in maintainability.md). Note duplicated blocks if found.

## Findings

### 1. (Security) (Critical) SQL built from request input
- **Reference:** CWE-89 · OWASP A05:2025 *(security findings only)*
- **Location:** [src/orders/repo.ts](src/orders/repo.ts#L42-L45) (lines 42–45)
- **Action:** Must fix
- **Confidence:** High (0.95)
- **Status:** New | Pre-existing (touched by change) | Needs review

**Issue:** <What is wrong, in one or two sentences, referring to the specific identifiers.>

**Why it matters:** <Concrete impact: what an attacker / user / future maintainer experiences.>

**Exploit scenario:** <Security findings only: source → sink path and an example input.>

**Affected code:**
```<lang>
<the exact offending lines from the new file>
```

**Suggested fix:**
```diff
- <old line(s)>
+ <new line(s)>
```
<Optional one-line note on alternatives or follow-up, e.g. add a test.>

---

<next finding…>

## Checks run
- `<command>` → pass / fail (<short summary>)
- Not run: <command> — <reason>

## Not reviewed
- <files or aspects excluded or only skimmed, and why (generated, vendored, size budget, checks not run)>
````

## Rules for the report

- Order findings: severity (Critical → Info), then file path, then line.
- **Location** must always be a file path plus line number(s) in the new file, e.g. `[src/a.ts](src/a.ts#L42-L45) (lines 42–45)`. Never a symbol name or description alone. For untracked files, number lines from the working-tree file. If the issue spans separate places (e.g. a call site and the blocking call it reaches), give one **Location** line for each.
- Line numbers refer to the **new** version of the file; use a single line `#L42` or a range `#L42-L45` in links. Never combine non-contiguous ranges in one link — split into separate locations.
- Keep **Affected code** to the minimal lines that show the problem (≤ 15 lines).
- **Suggested fix** must be a valid, minimal diff in the file's language and style. If the fix spans multiple files or needs a design change, describe the steps instead and say so.
- Write about the code, not the author; explain *why* in **Why it matters**.
- One root cause = one finding. If the same rule hits several locations with the same fix, list them as multiple **Location** lines in one finding (max 5, then "and N more").
- If there are no findings, still output the gate, counts, metrics, checks run, and not reviewed.
- No filler or restatement of the diff. A single optional **Notable positives** line (max 2 items) is allowed after the findings when something is worth reinforcing.
