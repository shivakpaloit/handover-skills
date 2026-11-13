# Quality Gates

Use for the Test Scenario Inventory and Risks, Dependencies & Open Questions. Apply only what is relevant; skip what doesn't apply (for example accessibility without UI). Call out any gate the story's AC do not already cover. When a gate yields a scenario, give it the matching `Type` and reflect the work in a subtask and a scenario. Each stack profile's **Quality Gate Specifics** adds concrete checks; cite the concrete concern for this feature, not generic advice.

- **Security** (OWASP-aligned): authentication and authorization enforced server-side (including object-level ownership), input validation, injection/XSS/CSRF/SSRF/open redirect, mass assignment, secrets management, dependency vulnerabilities, rate limiting, error responses without internal detail, security event logging.
- **Testing:** unit/integration/e2e coverage of happy paths, validation failures, authorization failures, edge cases, and regressions of the behavior being changed.
- **Performance:** query/network efficiency, pagination, indexes, caching/invalidation, bundle/artifact size — justified by evidence, not speculation.
- **Reliability:** timeouts, retries and fallbacks for external calls, idempotency for retried operations, concurrent updates, backwards-compatible migrations, rollout/rollback, and feature flags where warranted.
- **Accessibility** (UI only): keyboard navigation, labeled controls, semantic markup, color contrast.
- **Observability** (when the feature adds dependencies or flows): structured logging without PII or secrets, correlation IDs, metrics/health indicators.
