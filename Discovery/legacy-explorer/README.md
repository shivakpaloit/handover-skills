# legacy-explorer v6
VS Code agent plugin (Agent Plugins 1.0 format) for exploring an existing
or legacy codebase with no trusted docs.

## What it provides

| Type | Name | Purpose |
|---|---|---|
| Agent | `Legacy Explorer` | Orchestrator: identifies the app, scopes the views, runs the explorers in parallel or series, consolidates. |
| Skill | `ui-explorer` | Pages, fields and actions → `ui.md`. |
| Skill | `api-explorer` | Endpoints served and calls made → `api.md`. |
| Skill | `data-model-explorer` | Tables, entities, DTOs, relationships → `data-models.md`. |
| Skill | `journey-explorer` | Personas and step-by-step flows from transcripts, screenshots, test cases and code → `journeys.md`, `journeys-trace.md`. |

UI, API and data models are independent and run first (in parallel by
default). Journeys run last and reuse their IDs.

-------

## Layout

```
legacy-explorer/
  plugin.json
  com.github.copilot/agents/legacy-explorer.agent.md
  skills/
    ui-explorer/
    api-explorer/
    data-model-explorer/
    journey-explorer/
  tests/triggers.json
```

## Install locally

### Option A: paste into the target repo

```sh
plugins/legacy-explorer/build.sh
```

Copy `dist/.github/` into the target repo's root (merge with any existing
`.github/`), or unzip `dist/legacy-explorer-github.zip` there. VS Code picks
up `.github/agents/` and `.github/skills/` automatically.

### Option B: as a plugin

Add to user `settings.json`:

```jsonc
"chat.plugins.enabled": true,
"chat.pluginLocations": {
  "/absolute/path/to/plugins/legacy-explorer": true
}
```

Open the target codebase, pick **Legacy Explorer** in the agent picker, and
give it the app path, e.g. "Explore the app in `web/`". Name views to run a
subset ("just api and data for `web/`") or add "in series" to run one at a
time.

## Test

`tests/triggers.json` pins which skill each prompt should route to.
