# Code Review — feature/order-search

> Sample output of the `code-review` skill. File paths and code are illustrative.

**Scope:** `main...feature/order-search` · 4 files changed · +186 / -12 lines
**Intent:** Adds an order search endpoint with filtering by customer and status, and a summary export for admins.

## Quality Gate: Failed

| Condition | Status |
| --- | --- |
| No Critical findings | ❌ (2) |
| No High-confidence High findings | ❌ (2) |
| New-code coverage ≥ 80% | ❌ (41%) |
| New-code duplication ≤ 3% | ✅ (0%) |
| No new lint / type / test failures | ✅ |

| Severity | Count |   | Category | Count |
| --- | --- | --- | --- | --- |
| Critical | 2 |   | Security | 4 |
| High | 2 |   | Error Prone | 1 |
| Medium | 3 |   | Performance | 1 |
| Low | 1 |   | Complexity | 1 |
| Info | 0 |   | Maintainability / Clean Code / Best Practice | 1 |

## Metrics (changed code)

| File | Function | Cyclomatic | Cognitive | Length (LOC) | Max nesting | Params |
| --- | --- | --- | --- | --- | --- | --- |
| src/orders/orders.repository.ts | `searchOrders` | 4 | 3 | 18 | 1 | 2 |
| src/orders/orders.service.ts | `buildSummary` | 14 ⚠ | 22 ⚠ | 61 ⚠ | 4 ⚠ | 3 |
| src/orders/orders.controller.ts | `search` | 2 | 1 | 9 | 1 | 2 |
| src/orders/orders.controller.ts | `exportSummary` | 3 | 2 | 14 | 1 | 2 |

## Findings

### 1. (Security) (Critical) SQL query built from request input
- **Reference:** CWE-89 · OWASP A05:2025
- **Location:** src/orders/orders.repository.ts lines 24–27
- **Action:** Must fix
- **Confidence:** High (0.95)
- **Status:** New

**Issue:** `searchOrders` interpolates `filters.status` and `filters.sortBy` from the query string directly into the SQL text passed to `db.raw`. Every other repository in `src/` uses bound parameters.

**Why it matters:** Any signed-in caller can read or modify other customers' orders.

**Exploit scenario:** `GET /orders?status=x' OR '1'='1` → `search` controller → `searchOrders(filters)` → `db.raw(sql)` returns every customer's orders.

**Affected code:**
```ts
const sql = `SELECT * FROM orders
  WHERE customer_id = ${customerId} AND status = '${filters.status}'
  ORDER BY ${filters.sortBy}`;
return db.raw(sql);
```

**Suggested fix:**
```diff
- const sql = `SELECT * FROM orders
-   WHERE customer_id = ${customerId} AND status = '${filters.status}'
-   ORDER BY ${filters.sortBy}`;
- return db.raw(sql);
+ const SORTABLE = { createdAt: 'created_at', total: 'total' } as const;
+ const sortColumn = SORTABLE[filters.sortBy as keyof typeof SORTABLE] ?? 'created_at';
+ return db.raw(
+   `SELECT id, status, total, created_at FROM orders
+    WHERE customer_id = ? AND status = ? ORDER BY ${sortColumn} LIMIT ?`,
+   [customerId, filters.status, PAGE_SIZE],
+ );
```
Also resolves finding 6's unbounded `SELECT *`.

---

### 2. (Security) (Critical) Hard-coded API key
- **Reference:** CWE-798 · OWASP A07:2025
- **Location:** src/orders/orders.service.ts line 8
- **Action:** Must fix
- **Confidence:** High (0.95)
- **Status:** New

**Issue:** The reporting service API key is committed as a string literal (`sk_l****`).

**Why it matters:** Anyone with repo access, including CI logs and forks, can use the key. Removing it from code does not remove it from git history.

**Exploit scenario:** Anyone who can read the repository or a fork copies the key and calls the reporting API directly.

**Affected code:**
```ts
const REPORTING_API_KEY = 'sk_l************************';
```

**Suggested fix:**
```diff
- const REPORTING_API_KEY = 'sk_l************************';
+ const REPORTING_API_KEY = process.env.REPORTING_API_KEY;
+ if (!REPORTING_API_KEY) throw new Error('REPORTING_API_KEY is not configured');
```
Rotate the exposed key with the provider.

---

### 3. (Security) (High) Admin export has no role check
- **Reference:** CWE-285 · OWASP A01:2025
- **Location:** src/orders/orders.controller.ts lines 41–44
- **Action:** Must fix
- **Confidence:** High (0.9)
- **Status:** New

**Issue:** `exportSummary` is registered with `requireAuth` only. Sibling admin routes in this controller use `requireRole('admin')`.

**Why it matters:** Any signed-in customer can export the summary for all customers.

**Exploit scenario:** A customer signs in and calls `GET /orders/summary/export?from=2026-01-01&to=2026-12-31`, which returns every customer's order totals.

**Affected code:**
```ts
router.get('/orders/summary/export', requireAuth, async (req, res) => {
  const summary = await ordersService.buildSummary(req.query.from, req.query.to, 'csv');
  res.send(summary);
});
```

**Suggested fix:**
```diff
- router.get('/orders/summary/export', requireAuth, async (req, res) => {
+ router.get('/orders/summary/export', requireAuth, requireRole('admin'), async (req, res) => {
```
Add a test asserting a non-admin gets `403`.

---

### 4. (Error Prone) (High) Unawaited promise in loop
- **Location:** src/orders/orders.service.ts lines 52–54
- **Action:** Must fix
- **Confidence:** High (0.9)
- **Status:** New

**Issue:** `orders.forEach(async (o) => ...)` starts `enrichWithCustomer` calls but `buildSummary` returns before they finish, and any rejections are unhandled.

**Why it matters:** The summary is returned with missing customer data, and failures crash the process or are lost silently.

**Affected code:**
```ts
orders.forEach(async (o) => {
  o.customer = await customersClient.enrichWithCustomer(o.customerId);
});
```

**Suggested fix:** see finding 6, which replaces this loop with one batched call.

---

### 5. (Security) (Medium) Database error message returned to client
- **Reference:** CWE-209 · OWASP A10:2025
- **Location:** src/orders/orders.controller.ts line 30
- **Action:** Should fix
- **Confidence:** Medium (0.7). Depends on whether the DB driver's messages include SQL or schema details; confirm by triggering a query error locally.
- **Status:** Needs review

**Issue:** The `search` handler's `catch` sends `err.message` straight to the client. The shared `errorHandler` middleware used elsewhere returns a generic message and a correlation ID.

**Why it matters:** Driver errors often include table names, column names, or SQL fragments, which help an attacker probe finding 1.

**Exploit scenario:** Send a malformed `sortBy` value. The 500 response body contains the failing SQL statement.

**Affected code:**
```ts
} catch (err) { res.status(500).send(err.message); }
```

**Suggested fix:**
```diff
- } catch (err) { res.status(500).send(err.message); }
+ } catch (err) { next(err); }
```

---

### 6. (Performance) (Medium) Remote call per order (N+1)
- **Location:** src/orders/orders.service.ts lines 52–54
- **Action:** Should fix
- **Confidence:** Medium (0.7). Assumes date ranges can return hundreds of orders; confirm with production order volumes.
- **Status:** Needs review

**Issue:** One HTTP request to the customers service is made for each order.

**Why it matters:** A month-long export with 2,000 orders makes 2,000 outbound calls. That can exceed request timeouts and the downstream rate limits.

**Affected code:**
```ts
orders.forEach(async (o) => {
  o.customer = await customersClient.enrichWithCustomer(o.customerId);
});
```

**Suggested fix:**
```diff
- orders.forEach(async (o) => {
-   o.customer = await customersClient.enrichWithCustomer(o.customerId);
- });
+ const ids = [...new Set(orders.map((o) => o.customerId))];
+ const customers = new Map((await customersClient.getMany(ids)).map((c) => [c.id, c]));
+ for (const o of orders) o.customer = customers.get(o.customerId);
```

---

### 7. (Complexity) (Medium) `buildSummary` is too complex and too long
- **Location:** src/orders/orders.service.ts lines 30–90
- **Action:** Should fix
- **Confidence:** High (0.85, ≈ manual count)
- **Status:** New

**Issue:** Cognitive complexity is ≈ 22 (threshold 15), cyclomatic complexity is 14 (threshold 10), the function is 61 lines long (threshold 50) and nesting reaches depth 4. A single function fetches the data, enriches it, totals it by status, and formats it as CSV or JSON.

**Why it matters:** Every new status or output format adds more nested branches. The function is hard to test in isolation.

**Affected code:**
```ts
for (const o of orders) {
  if (o.status !== 'cancelled') {
    if (format === 'csv') {
      if (o.total > 0) { rows.push(toCsvRow(o)); } else { /* ... */ }
    } else { /* ... */ }
  }
}
```

**Suggested fix:**
```diff
- for (const o of orders) {
-   if (o.status !== 'cancelled') {
-     if (format === 'csv') {
-       ...
-     }
-   }
- }
+ const billable = orders.filter((o) => o.status !== 'cancelled' && o.total > 0);
+ const totals = totalByStatus(billable);
+ return FORMATTERS[format](billable, totals);
```
Move the fetching and enrichment into `loadOrdersWithCustomers` and the totals into `totalByStatus`, and replace the format branches with a `FORMATTERS` map.

---

### 8. (Clean Code) (Low) Magic number for page size
- **Location:** src/orders/orders.controller.ts line 22
- **Action:** Consider
- **Confidence:** High (0.9)
- **Status:** New

**Issue:** `Math.min(Number(req.query.limit), 500)` uses an unexplained literal.

**Why it matters:** The same limit is needed in the repository (the finding 1 fix) and will drift if it is copied.

**Affected code:**
```ts
const limit = Math.min(Number(req.query.limit), 500);
```

**Suggested fix:**
```diff
- const limit = Math.min(Number(req.query.limit), 500);
+ const limit = Math.min(Number(req.query.limit) || DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE);
```

**Notable positives:** `search` caps the page size on the server, so clients can't request unbounded result sets.

## Checks run
- `npm run lint` → pass
- `npm run typecheck` → pass
- `npm test -- --coverage` → pass; new-code coverage 41%. `orders.controller.ts` and `orders.service.ts` have no tests, so the role check (finding 3) and the export path are unverified.
- Not run: `npm audit` — no dependency manifest changes

The user confirmed the branch was trusted, so the project scripts were run.

## Not reviewed
- `package-lock.json` — lock file
