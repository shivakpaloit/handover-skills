# Performance Rules

Report only issues with a plausible real-world cost given the data sizes and call frequency visible in the code. State the assumption (e.g. "list endpoint, unbounded rows") in **Why it matters**.

| Rule | Default | What to look for | Typical fix |
| --- | --- | --- | --- |
| **PERF-NPLUS1-01** N+1 queries / calls | High | DB query, HTTP call, or file read inside a loop over a collection; lazy-loaded relations accessed per item | Batch query (`IN`, joins, `include`/`select_related`), bulk API, dataloader |
| **PERF-QUERY-01** Unbounded query | High | Fetching all rows without `LIMIT`/pagination; `SELECT *` on wide tables for a few fields | Paginate; select needed columns |
| **PERF-INDEX-01** Query likely missing an index | Medium | New filter/sort/join on columns without an index in schema/migration | Add index in migration (verify with query plan) |
| **PERF-ALGO-01** Inefficient algorithm | Medium | Nested loops / `includes`/`indexOf`/`in list` lookups inside loops (O(n²)) on non-trivial collections; repeated sort | Use `Set`/`Map`/dict; sort once; precompute |
| **PERF-ALLOC-01** Avoidable allocation / copying | Low | String concatenation in loops, repeated array spreads/copies, re-creating regex/formatters per call | Builder/join; mutate locally; hoist constants |
| **PERF-IO-01** Blocking I/O on hot or async path | High | Sync file/network/crypto calls (`readFileSync`, `requests` in async code, `.Result`/`.Wait()`) in request handlers or event loop | Async APIs; offload to worker |
| **PERF-SEQ-01** Sequential independent awaits | Medium | Independent async calls awaited one after another | `Promise.all` / `asyncio.gather` / parallel tasks (with concurrency limit) |
| **PERF-CACHE-01** Missing or broken caching | Medium | Repeated expensive pure computation or remote fetch of rarely-changing data; cache without TTL/eviction or keyed incorrectly | Memoize / cache with TTL and bounded size; correct key |
| **PERF-MEM-01** Memory growth / leak | High | Unbounded in-memory collections, listeners/subscriptions/intervals never removed, loading whole large files/results into memory | Bounded structures, cleanup, streaming |
| **PERF-PAYLOAD-01** Over-fetching / large payload | Medium | Returning full entities or large nested graphs to clients; no compression/pagination | DTO with needed fields; paginate |
| **PERF-RENDER-01** UI render inefficiency | Medium | Expensive computation in render, unstable props/keys causing re-renders, missing list `key`, index as key on reorderable lists, effects without/with wrong dependencies, large client bundles from server-capable code | Memoize where measured; stable keys; correct deps; move work server-side; code-split |
| **PERF-ASSET-01** Unoptimized assets | Low | Large images without sizing/lazy loading, blocking scripts/fonts | Framework image component, lazy load, `defer` |
| **PERF-CONC-01** Concurrency hazards | High | Lock held across I/O, unbounded parallelism (fan-out without limit), connection pool exhaustion, missing timeouts on outbound calls | Narrow critical sections; concurrency limits; timeouts and retries with backoff |
| **PERF-LOG-01** Expensive logging | Low | Building large log strings or serializing objects in hot loops regardless of log level | Level guards / lazy formatting |

## Notes

- Do not recommend micro-optimisations (`for` vs `forEach`, etc.) without evidence of a hot path.
- Prefer findings backed by code structure (loop + query) over speculation. If impact depends on data volume you cannot see, set `Confidence: Medium`.
