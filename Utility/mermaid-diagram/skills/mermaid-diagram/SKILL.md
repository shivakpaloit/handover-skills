---
name: mermaid-diagram
description: >
  Create, review, or fix any Mermaid diagram. Use when the user wants a
  flowchart, sequence, state machine, ER, C4, class, journey, Gantt, mindmap,
  timeline, git graph, sankey, quadrant, requirement, XY chart, block,
  kanban, architecture/cloud topology, radar, treemap, packet, or any other
  Mermaid diagram type (including niche ones like Venn, Ishikawa/fishbone,
  Wardley map, Cynefin, swimlane, tree view, or event modeling). Also use
  when an existing Mermaid diagram renders incorrectly, looks wrong, or needs
  a layout fix, or when a diagram fails to render in GitHub or VS Code's
  Markdown preview and the cause may be a Mermaid version/renderer mismatch.
  Do not use when the deliverable is a Lucid/Lucidchart document or a
  FigJam/Figma diagram, or for data-dense charts better served by a plotting
  tool.
---

# Mermaid Diagram Skill

## Purpose

Produce correct, semantically clear Mermaid diagrams on first draft.
Layout renders as intended. Syntax is valid. Style is consistent.

---

## Procedure

### Step 1 — Gather intent

Collect before drafting. Ask once for anything missing:

| Question | Why it matters |
|---|---|
| **What to diagram?** | System, flow, entities, lifecycle, interactions? |
| **Audience?** | Engineering detail vs. exec overview vs. BA handoff? |
| **Preferred orientation?** | Top-down, left-right, or no preference? |
| **Rendering environment?** | GitHub, Confluence, VS Code, Mermaid live? |

Never assume the diagram type — state your choice and the reasoning.

---

### Step 2 — Select diagram type

Read `references/diagram-type-selector.md` and pick the single best type.
State your selection in one line: `Diagram type: X — because Y.`

If the selected type shipped in one of Mermaid's last few releases (check
`references/mermaid-version-compatibility.md`), reason about whether the target
renderer from Step 1 will actually display it before drafting — see "Renderer
compatibility matrix" in the selector file. Never select `agentflow-beta` or
`usecase-beta` — neither exists in any published Mermaid release yet; use the
documented fallback instead and say why.

---

### Step 3 — Build a node/edge inventory

Before writing any syntax, list every element:

- **Nodes / entities / actors / states** — with proposed ID and display label
- **Edges / transitions / messages** — with direction and label
- **Groups / subgraphs / clusters / swimlanes**

This inventory is the source of truth for Pass 2 verification.
If the inventory exceeds ~40 nodes, recommend splitting into multiple focused diagrams.

---

### Step 4 — Draft

Apply the matching pattern from `references/diagram-patterns.md`:

- **IDs**: `camelCase` or `snake_case`; no spaces; no Mermaid reserved words
  (`end`, `class`, `call`, `graph`, `subgraph`, `direction`, `style`, `classDef`)
- **Labels**: ≤ 5 words; quote if they contain `( ) [ ] { } : / @ # > < & " '` (if the label contains `"`, encode it as `&quot;`)
- **Multi-line labels**: use `<br>` inside the label string — never `\n`. Mermaid renders `\n` as a literal backslash-n, not a line break.
- **Colour / style**: `classDef` only — never inline `style nodeId ...`
  Apply palette from `references/style-palette.md`
- **Comments**: `%%` for context that doesn't belong in a label
- **`%%{init}%%`**: place on line 1, before the diagram type declaration

---

### Step 5 — Two-pass verification (MANDATORY — never skip Pass 2)

**Pass 1 — Structural correctness**

Walk the inventory against the draft:
- [ ] Every node present exactly once (no duplicates, no omissions)
- [ ] Every edge has correct direction and label
- [ ] Subgraph labels match their intended content
- [ ] No orphan nodes (disconnected from everything)
- [ ] Every `:::className` matches a defined `classDef` (order-independent; convention: define them at the bottom)

**Pass 2 — Syntax correctness**

- [ ] No spaces in node IDs
- [ ] No Mermaid reserved words used as IDs
- [ ] All brackets/parens/braces balanced
- [ ] Labels with special characters are quoted
- [ ] Arrow type matches diagram semantics (see pattern file)
- [ ] No semicolons in `classDiagram` attributes
- [ ] `%%{init}%%` directive is on line 1 if used
- [ ] Direction (`TB`, `LR`, `RL`, `BT`) matches visual intent

---

### Step 6 — Layout check

Before outputting, apply the rules in `references/layout-troubleshooting.md`:

- Diagrams with sibling subgraphs in `direction LR`? → check for vertical stacking bug
- Diagram > 15 nodes? → consider ELK layout hint
- Any subgraph with external connections? → note that `direction` hint will be ignored

---

### Step 7 — Output

Emit the diagram in a fenced ` ```mermaid ``` ` block.

If the target doesn't render Mermaid natively (a Marp slide deck, PDF/PPTX export, or
any consumer expecting an image rather than markdown), read
`references/exporting-to-svg.md` instead and embed the rendered, patched SVG.

Follow with:
1. One sentence describing what the diagram shows
2. Any rendering notes (ELK requirement, known renderer gaps, split recommendation).
   If the diagram type is anything other than a well-established one (see the
   compatibility matrix in `references/diagram-type-selector.md`), state plainly
   whether it's confirmed to render in the target environment or still needs
   verification — don't let a ⚠️/❌ type pass silently as if it were a safe default.

If fixing an existing diagram, also note what was wrong and what changed. If the
underlying cause turns out to be a renderer/version mismatch rather than a syntax
error, say so explicitly — see `references/mermaid-version-compatibility.md`.

---

## Anti-patterns — never do these

| Anti-pattern | Why it fails |
|---|---|
| `style nodeId fill:#...` inline | Fragile; use `classDef` + `:::class` |
| Reserved word as node ID | Parse error (`end`, `call`, `graph`, etc.) |
| Spaces in node IDs | Parse error |
| Unquoted label with special characters | Parse error on `( ) [ ] { } : / @ #` |
| `\n` for a multi-line label | Renders as literal `\n` text, not a line break; use `<br>` |
| `-->` in `sequenceDiagram` | Wrong; `-->` = dashed; `->>` = solid sync |
| Semicolons in `classDiagram` | Mermaid doesn't use semicolons |
| `linkStyle N` for semantic colouring | Edge index shifts when you add edges; use node `classDef` instead |
| One giant diagram (> 50 nodes) | Unreadable and layout breaks; split it |
| Wrapper subgraph around LR siblings | Causes vertical stacking; flatten instead |
| Skipping Pass 2 on a "simple" diagram | Simple diagrams still have syntax errors |
| Drafting `agentflow-beta` or `usecase-beta` | Not in any published Mermaid release yet; nothing can render them — see `references/mermaid-version-compatibility.md` |
| Assuming a brand-new diagram type renders wherever Mermaid renders anything | Each renderer bundles a pinned Mermaid version and lags npm-latest; check `references/mermaid-version-compatibility.md` |

---

## When NOT to use Mermaid

- Photographic, hand-drawn, or spatial diagrams where position = meaning
- Data-dense charts (bar, line, scatter, heatmap) — use a real charting tool
- Diagrams where after Pass 2 you cannot honestly verify every element

Use a PNG + prose description instead:

```markdown
![Diagram description](path/to/image.png)

> **Diagram note:** {What it shows and why Mermaid was not used.}
```

---

## Reference files

| File | Purpose |
|---|---|
| `references/diagram-type-selector.md` | Decision tree for picking the right type, plus the renderer compatibility matrix |
| `references/diagram-patterns.md` | Canonical pattern + example for every mainstream supported type |
| `references/emerging-diagram-types.md` | Niche/very recent types (Venn, Ishikawa, Wardley, Cynefin, Swimlane, Tree View, Event Modeling, Railroad, ZenUML) and the not-yet-released types (Agent Flow, Use Case) |
| `references/mermaid-version-compatibility.md` | Which Mermaid version introduced each type, and whether GitHub / VS Code's default preview / Mermaid Live actually render it yet |
| `references/layout-troubleshooting.md` | Layout fixes, syntax error catalogue, rendering notes |
| `references/style-palette.md` | `classDef` palettes, theming, edge styling |
| `references/exporting-to-svg.md` | Rendering to SVG for targets that don't support Mermaid natively (Marp, PDF/PPTX, image-only consumers) |
