# mermaid-diagram

Create, review, or fix any Mermaid diagram — correct on first draft. The skill selects the right
diagram type from a decision tree, builds a node/edge inventory before writing any syntax, drafts
against canonical per-type patterns, then runs a **mandatory two-pass verification** (structural +
syntax) and a layout check against known Mermaid rendering bugs.

## Skills

| Skill | Purpose |
| --- | --- |
| `mermaid-diagram` | Author or repair Mermaid diagrams: intent gathering → type selection → inventory → pattern-based draft → two-pass verify → layout check. Covers flowchart, sequence, state, ER, C4, class, journey, Gantt, mindmap, timeline, git graph, sankey, quadrant, requirement, XY chart, block, kanban, architecture, radar, treemap, packet, and niche/emerging types (Venn, Ishikawa, Wardley, Cynefin, swimlane, tree view, event modeling, railroad, ZenUML). |

## Install

```text
/plugin marketplace add Gen-e2/gen-e2-marketplace
/plugin install mermaid-diagram@Gen-e2/gen-e2-marketplace
```

Local testing from a clone:

```bash
claude --plugin-dir ./plugins/mermaid-diagram
```

## Usage

Ask in natural language, for example:

- "Sequence diagram for our login flow."
- "Layered architecture diagram of the backend as Mermaid."
- "State machine for the ticket lifecycle."
- "Fix this flowchart — the subgraphs stack vertically instead of side by side."

The skill states its diagram-type choice and reasoning, drafts from a verified pattern, and emits
the result in a `mermaid`-tagged fenced code block with rendering notes (ELK hints, renderer gaps,
split recommendations).

## Requirements & dependencies

- None. Output is plain Mermaid text; no binaries, MCP servers, or API keys required.
- Rendering-environment aware: the skill asks where the diagram will render (GitHub, Confluence,
  VS Code, Mermaid Live) and avoids syntax that the target renderer does not support — including
  distinguishing VS Code's *default* built-in Markdown preview (native since VS Code 1.121, and
  pinned to whatever Mermaid version shipped with that VS Code build) from the Mermaid Chart
  extension or Mermaid Live, which both track close to npm-latest.

## Notes

- Style is `classDef`-only (no inline `style` / `linkStyle`), with a bundled palette reference.
- Diagrams beyond ~40 nodes are split into multiple focused diagrams rather than one giant one.
- When Mermaid is the wrong tool (spatial layouts, data-dense charts), the skill says so and
  recommends an alternative instead of forcing it.
- Version-aware: `references/mermaid-version-compatibility.md` tracks which Mermaid release
  introduced each diagram type and flags the two documented-but-unreleased types (Agent Flow,
  Use Case) so the skill never drafts syntax nothing can render yet.
- Related plugins: `lucid-diagram` delivers editable diagrams into Lucid. `architecture-reviewer`
  defers to this skill when its reviews emit Mermaid — it no longer carries its own copy, so this
  plugin is the single home for Mermaid authoring.
