# Changelog

All notable changes to the `mermaid-diagram` plugin are documented here.

## 0.2.0

- Added 8 mainstream diagram types confirmed live in the current published Mermaid
  release (`11.17.2`): Requirement Diagram, XY Chart, Block Diagram, Kanban Board,
  Architecture Diagram, Radar Chart, Treemap, and Packet Diagram — full canonical
  patterns in `diagram-patterns.md` (Patterns 17–24), plus decision-tree branches and
  lookup rows in `diagram-type-selector.md`.
- Added `references/emerging-diagram-types.md` covering niche/very recent types (Venn,
  Ishikawa/fishbone, Wardley Map, Cynefin, Swimlane, Tree View, Event Modeling,
  Railroad/syntax diagrams, ZenUML) and explicitly flags Agent Flow (`agentflow-beta`)
  and Use Case (`usecase-beta`) as **not yet present in any published Mermaid release**
  (confirmed by grepping the published `mermaid.min.js` bundle, not just the docs),
  with fallback patterns to use in the meantime.
- Added `references/mermaid-version-compatibility.md`: a version-introduced table for
  every diagram type, plus a renderer-by-renderer reality check for GitHub, VS Code's
  *default* (built-in, native since VS Code 1.121) Markdown preview, the Mermaid Chart
  extension, and Mermaid Live — including why VS Code's default preview lags npm-latest
  (it bundles a pinned Mermaid version tied to VS Code's own release cadence) and how to
  diagnose a "diagram doesn't render" report as a version/renderer mismatch rather than
  a syntax bug.
- `diagram-type-selector.md`'s renderer compatibility matrix now distinguishes VS Code's
  default preview from the Mermaid Chart extension / Mermaid Live, and covers all newly
  added and emerging types.
- `SKILL.md` Step 2 now checks version compatibility before drafting a recently-shipped
  type, Step 7 requires stating render-support confidence for anything non-established,
  and the anti-pattern table calls out drafting the two not-yet-released types.
- Added trigger-test coverage for a newly-added diagram type (kanban, architecture),
  the `<br>` vs `\n` multi-line label repair case, and the SVG-export fallback path for
  non-native renderers (Marp).

## 0.1.0

- Initial release, ported from a project-local skill (imed-radlab-discovery) via the copy bundled
  in `architecture-reviewer` (which includes the `&quot;` label-escaping and sequence-diagram
  bidirectional-message fixes). Skill renamed `mermaid-creator` → `mermaid-diagram`.
- Single `mermaid-diagram` skill: intent gathering → diagram-type selection → node/edge inventory
  → pattern-based draft → mandatory two-pass verification (structural + syntax) → layout check.
- Bundled references: diagram-type decision tree, canonical patterns for every supported type,
  layout troubleshooting / syntax error catalogue, and `classDef` style palettes.
