# Diagram Type Selector

Read the user's intent, then follow this tree top-to-bottom. Stop at the first match.

---

## Primary decision tree

```
Showing actors exchanging messages/events over time?
  └─ YES → sequenceDiagram

Showing states + labelled transitions (lifecycle, status workflow)?
  └─ YES → stateDiagram-v2

Showing database / domain model entities + relationships?
  └─ YES → erDiagram

Showing OOP class structure (fields, methods, inheritance, composition)?
  └─ YES → classDiagram

Showing software system at Context / Container / Component level (C4 model)?
  └─ YES → C4Context  /  C4Container  /  C4Component  (pick zoom level)

Showing a user's emotional journey through steps / touchpoints?
  └─ YES → journey

Showing tasks on a timeline with durations and dependencies?
  └─ YES → gantt

Showing parts-of-a-whole as percentages?
  └─ YES → pie

Showing a branching hierarchy / brainstorm map?
  └─ YES → mindmap

Showing a git commit / branch history?
  └─ YES → gitGraph

Showing flow of quantities between categories (energy, money, traffic)?
  └─ YES → sankey

Showing a chronological sequence of events (history, releases)?
  └─ YES → timeline

Showing items positioned on a 2×2 priority / impact grid?
  └─ YES → quadrantChart

Showing cloud/CI-CD service topology (services, storage, groups, icons)?
  └─ YES → architecture-beta

Showing numeric series (bar/line) against categories?
  └─ YES → xychart

Showing several entities scored across the same dimensions (skill/capability comparison)?
  └─ YES → radar-beta

Showing nested parts-of-a-whole (categories containing sized sub-items)?
  └─ YES → treemap-beta

Showing a task board (backlog / in progress / done)?
  └─ YES → kanban

Showing formal requirements and their trace/verify relationships?
  └─ YES → requirementDiagram

Showing a binary wire format / protocol header bit-by-bit?
  └─ YES → packet

Free-form block layout that doesn't fit flowchart's edge-driven model (spanning blocks, explicit grid)?
  └─ YES → block

Showing components arranged in horizontal tiers (Frontend / Backend / Data)?
  └─ YES → flowchart TB   (one subgraph per layer)

Showing a dependency graph, network, or flat component map?
  └─ YES → flowchart LR

Decision tree / algorithm / process with branching logic?
  └─ YES → flowchart TD

Anything else?
  └─ → flowchart TB   (safe default)
```

For a niche or very recently shipped type not on this tree (Venn, Ishikawa, Wardley
Map, Cynefin, Swimlane, Tree View, Event Modeling, Railroad, ZenUML), see
`references/emerging-diagram-types.md`. If the user asks for an "agent flow" or a UML
"use case diagram," neither exists in any published Mermaid release yet — see the
"Not yet released" section of that same file for the fallback pattern to use instead.

---

## Quick lookup table

| What you're describing | Best type | Acceptable alt |
|---|---|---|
| API request/response cycle | `sequenceDiagram` | `flowchart LR` |
| Order/payment flow with retries | `sequenceDiagram` | — |
| Ticket / order lifecycle | `stateDiagram-v2` | — |
| DB schema / entity model | `erDiagram` | — |
| Domain model (aggregates, value objects) | `erDiagram` | `classDiagram` |
| OOP inheritance hierarchy | `classDiagram` | — |
| Microservice / service mesh topology | `flowchart LR` | `C4Container` |
| System context (your system + external actors) | `C4Context` | `flowchart TB` |
| Container map (apps, DBs, queues in one system) | `C4Container` | `flowchart LR` |
| Internal component breakdown | `C4Component` | `flowchart LR` |
| Layered architecture (3-tier, hexagonal) | `flowchart TB` + subgraphs | — |
| Decision tree / algorithm | `flowchart TD` | — |
| User journey with sentiment | `journey` | — |
| Sprint / release plan | `gantt` | `timeline` |
| Historical timeline | `timeline` | `gantt` |
| Git branching strategy | `gitGraph` | — |
| Energy / budget Sankey | `sankey` | — |
| Prioritisation matrix | `quadrantChart` | — |
| Mind map / brainstorm | `mindmap` | — |
| Process decomposition | `flowchart TB` | `mindmap` |
| Network topology | `flowchart LR` | — |
| Cloud / CI-CD service topology | `architecture-beta` | `flowchart LR` |
| Numeric series (bar/line) by category | `xychart` | — (or a real charting tool) |
| Multi-entity dimension comparison | `radar-beta` | — |
| Nested proportions | `treemap-beta` | `pie` (if flat) |
| Task board (backlog/in-progress/done) | `kanban` | — |
| Formal requirements + traceability | `requirementDiagram` | — |
| Binary wire format / protocol header | `packet` | — |
| Free-form block layout / spanning blocks | `block` | `flowchart` |
| Root-cause analysis | `ishikawa-beta` (see emerging types) | `flowchart TD` |
| Set overlap | `venn-beta` (see emerging types) | — |
| Strategy / value-chain mapping | `wardley-beta` (see emerging types) | — |
| Cross-team process handoff | `swimlane-beta` (see emerging types) | `flowchart` + subgraphs |
| File/directory structure | `treeView-beta` (see emerging types) | `mindmap` |
| Formal grammar / DSL syntax | `railroad-*-beta` (see emerging types) | — |
| AI agent workflow ("agent flow") | not yet released | `flowchart TD` (see emerging types) |
| UML use case diagram | not yet released | `flowchart LR` (see emerging types) |

---

## When flowchart beats a specialised type

Prefer `flowchart` when:
- The diagram mixes concerns (not pure state, not pure sequence)
- Subgraph grouping or colour-coding matters more than strict notation
- The target renderer has limited support for newer diagram types
  (GitHub supports flowchart/sequence/ER/class/state/Gantt reliably;
   C4, sankey, timeline, mindmap, quadrant need a newer renderer)

---

## Renderer compatibility matrix

The **VS Code** column below means the *default, built-in* Markdown preview
(native since VS Code 1.121, May 2026) — not the separate Mermaid Chart extension.
See "VS Code default preview — version intelligence" below for why that distinction
matters and how to reason about it when a diagram doesn't show up.

| Type | GitHub Markdown | Confluence | VS Code (default preview) | Mermaid Live / Mermaid Chart ext. |
|---|---|---|---|---|
| flowchart | ✅ | ✅ | ✅ | ✅ |
| sequenceDiagram | ✅ | ✅ | ✅ | ✅ |
| stateDiagram-v2 | ✅ | ✅ | ✅ | ✅ |
| erDiagram | ✅ | ✅ | ✅ | ✅ |
| classDiagram | ✅ | ✅ | ✅ | ✅ |
| gantt | ✅ | ✅ | ✅ | ✅ |
| pie | ✅ | ✅ | ✅ | ✅ |
| C4Context / Container | ⚠️ partial | ⚠️ partial | ✅ | ✅ |
| mindmap | ⚠️ partial | ⚠️ partial | ✅ | ✅ |
| timeline | ⚠️ partial | ⚠️ partial | ✅ | ✅ |
| gitGraph | ✅ | ⚠️ partial | ✅ | ✅ |
| requirementDiagram | ✅ | ⚠️ partial | ✅ | ✅ |
| kanban | ⚠️ partial | ❌ | ✅ | ✅ |
| xychart | ⚠️ partial | ❌ | ✅ | ✅ |
| block | ⚠️ partial | ❌ | ✅ | ✅ |
| architecture-beta | ⚠️ partial | ❌ | ✅ | ✅ |
| radar-beta | ⚠️ partial | ❌ | ✅ | ✅ |
| treemap-beta | ⚠️ partial | ❌ | ✅ | ✅ |
| packet | ❌ | ❌ | ⚠️ verify version | ✅ |
| sankey | ❌ | ❌ | ✅ | ✅ |
| quadrantChart | ❌ | ❌ | ✅ | ✅ |
| ishikawa-beta / venn-beta | ❌ | ❌ | ⚠️ verify version | ✅ |
| treeView-beta / wardley-beta | ❌ | ❌ | ⚠️ verify version | ✅ |
| eventmodeling | ❌ | ❌ | ⚠️ verify version | ✅ |
| cynefin-beta / railroad-*-beta / swimlane-beta | ❌ | ❌ | ⚠️ verify version | ✅ |
| agentflow-beta / usecase-beta | ❌ (not yet released) | ❌ (not yet released) | ❌ (not yet released) | ❌ (not yet released) |

When targeting GitHub, stick to the ✅ types — anything ⚠️/❌ for GitHub either isn't
picked up by GitHub's bundled Mermaid version yet, or (for the last row) doesn't exist
in any published Mermaid release. For VS Code's default preview or Mermaid Live/Chart,
most types work — the exceptions are the diagram types from Mermaid's newest releases
(v11.14.0+), where VS Code's default preview needs a version check first.

### VS Code default preview — version intelligence

Don't assume "VS Code = works." The default preview's Mermaid support:
1. Requires **VS Code ≥ 1.121** — older versions show the raw code fence, not an error.
2. Bundles a **pinned** Mermaid version that updates on VS Code's own release cadence,
   not live from npm — so it can lag npm-latest by weeks to months at any given time.

Before asserting a ⚠️/newer type will render in VS Code's default preview:
- Confirm the user's VS Code version if it's in question (`Help > About`).
- Cross-check the diagram type's "introduced in" version against how recent that likely
  is — see `references/mermaid-version-compatibility.md` for the full table and the
  step-by-step reasoning.
- If genuinely uncertain, say so and point to the Mermaid Chart extension or
  https://mermaid.live as a way to confirm rendering independent of the default
  preview's bundled version.
