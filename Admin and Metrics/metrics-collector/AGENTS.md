# metrics-collector: agent instructions

Node ESM CLI (Node >= 22.19) that collects engineering metrics from Jira, Bamboo, SonarQube, Fortify, Nexus IQ, ServiceNow and others. Configured entirely by environment variables (`.env`, see `.env.example` and `README.md`).

For running, testing and debugging, use the `metrics-collector` skill (`.github/skills/metrics-collector/SKILL.md`).

Quick reference:
- `npm run selftest`: read-only connectivity/auth check per configured tool
- `npm run check`: which metrics are runnable with the current env
- `METRICS=<key> LOG_LEVEL=debug npm start`: run one metric with request logging
- `npm test`: node:test suite against a mock Jira server (covers the epic PRD metrics). Otherwise verify with `node --check`, `selftest`, and single-metric runs.

Rules:
- Never print, log or commit values from `.env` (tokens, passwords). `output/` can contain internal issue data and is gitignored.
- Confirm scope before running against real tools; an empty filter means "everything this token can see".
- Local SonarQube/Bamboo: `docker-compose.yml` (works with `podman compose`).
