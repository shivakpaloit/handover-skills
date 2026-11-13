# Clean Code & Correctness Rules

Readability, intent, and bug-prone patterns. Category is `Clean Code`, `Error Prone`, or `Best Practice` as listed.

## Error Prone (bugs)

| Rule | Default | What to look for | Typical fix |
| --- | --- | --- | --- |
| **BUG-NULL-01** Possible null/undefined dereference | High | Access on a value that can be null/undefined/None (optional lookup, `find`, nullable column, optional prop) without a guard | Guard, early return, or optional chaining with a defined fallback |
| **BUG-ERR-01** Swallowed exception | High | Empty `catch`/`except`, catch-and-log-only on a path where the caller needs to know, `except Exception: pass` | Handle meaningfully, rethrow with context, or return an explicit error result |
| **BUG-ERR-02** Overly broad catch | Medium | Catching base `Exception`/`Throwable`/all errors where specific ones are expected | Catch specific types; let unexpected errors propagate |
| **BUG-ASYNC-01** Unawaited promise / fire-and-forget | High | Async call result not awaited or handled; `forEach` with async callback; missing `.catch` | `await`, `Promise.all`, or explicit error handling |
| **BUG-RES-01** Resource leak | High | Files, connections, streams, cursors, locks, timers, subscriptions not closed/released on all paths | `try-with-resources`, `using`, `with`, `finally`, cleanup in effect teardown |
| **BUG-LOGIC-01** Suspicious logic | High | Identical branches, always-true/false conditions, self-assignment, `=` vs `==`, loose equality on mixed types, inverted condition vs name, off-by-one bounds | Correct the expression; add a test for the edge |
| **BUG-STATE-01** Shared mutable state | Medium | Mutating inputs/arguments, module-level mutable state, mutating props/state directly in UI frameworks | Copy-on-write; local state; immutable updates |
| **BUG-CONC-01** Race condition / deadlock | High | Read-modify-write without a lock or transaction; non-idempotent handler that can be retried; locks taken in inconsistent order; stale closure over async state | Atomic operation, transaction, idempotency key, consistent lock order |
| **BUG-TYPE-01** Unsafe type escape | Medium | `any`, unchecked casts, `as unknown as`, `# type: ignore`, non-null assertion `!` on unverified values | Narrow types properly; validate then type |
| **BUG-NUM-01** Numeric pitfalls | Medium | Floating point for money, integer overflow, division without zero check, `parseInt` without radix | Decimal/integer minor units; guards |
| **BUG-DATE-01** Time/locale pitfalls | Medium | Local-time assumptions, naive datetimes, string date comparisons, hard-coded time zones | UTC storage; timezone-aware types; explicit formatting |

## Clean Code

| Rule | Default | What to look for | Typical fix |
| --- | --- | --- | --- |
| **CLN-NAME-01** Unclear naming | Low | Single-letter or misleading names outside tiny scopes, abbreviations, names that contradict behaviour, boolean names without `is/has/should` | Rename to express intent |
| **CLN-MAGIC-01** Magic numbers / strings | Low | Unexplained literals for limits, statuses, timeouts, roles | Named constant or enum |
| **CLN-DEAD-01** Dead code | Low | Unused variables, params, imports, functions; unreachable branches; commented-out code | Delete it |
| **CLN-DUP-01** Duplicated logic | Medium | Same logic in ≥ 2 places within the change (or copied from existing code) — ≥ ~6 similar lines or repeated non-trivial expression | Extract shared function / reuse existing helper |
| **CLN-FUNC-01** Function does more than one thing | Medium | Mixed levels of abstraction; "and" in the name; parse + validate + persist + notify in one body | Split into focused functions |
| **CLN-FLAG-01** Boolean flag parameter | Low | Boolean args switching behaviour (`render(true)`) | Separate functions or options object/enum |
| **CLN-COMMENT-01** Misleading or redundant comment | Low | Comments that restate code, are stale, or contradict it; TODO/FIXME without ticket | Remove or correct; link TODO to a ticket |
| **CLN-CONSIST-01** Inconsistent with codebase conventions | Low | Different error-handling, naming, folder, or data-access pattern than neighbours without reason | Follow existing pattern |
| **CLN-RETURN-01** Inconsistent return shape | Medium | Function returns different types/shapes on different paths (value vs null vs throw) | Single contract; explicit result type |

## Best Practice

| Rule | Default | What to look for | Typical fix |
| --- | --- | --- | --- |
| **BP-TEST-01** Changed behaviour untested | Medium | New/changed logic, branches, or bug fix with no test that would fail if the change were reverted | Name the missing case and where it belongs (unit/integration/e2e) |
| **BP-TEST-02** Weak test | Low | Tests without assertions, asserting implementation details, sleeping instead of awaiting, shared state between tests | Assert behaviour; deterministic waits; isolate |
| **BP-LOG-01** Debug leftovers | Low | `console.log`, `print`, `debugger`, `System.out` in production paths | Remove or use the project logger at the right level |
| **BP-CONFIG-01** Hard-coded environment values | Medium | URLs, hosts, ports, feature flags, credentials baked in code | Config / env variables |
| **BP-A11Y-01** Accessibility regression (UI) | Medium | Interactive elements without accessible name, non-semantic clickable `div`, missing labels, keyboard traps, colour-only meaning | Semantic elements, labels, ARIA only where needed |
| **BP-API-01** Breaking contract change | High | Changed request/response shape, status codes, or public signature without versioning or caller updates | Version, keep backward compatibility, or update all callers |
| **BP-DOC-01** Docs out of date | Low | Change alters how to build, run, configure, or call the code (new env var, endpoint, CLI flag) without updating README/API docs/`.env.example` | Update the relevant doc in the same change |
