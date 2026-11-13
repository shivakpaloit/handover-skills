# Mermaid Version Compatibility

Diagram types ship on Mermaid's own release cadence, and every renderer that embeds
Mermaid (GitHub, VS Code, Confluence, Mermaid Live) bundles a specific version rather
than tracking `npm latest` in real time. A diagram type that exists in the newest
Mermaid release can still render as a blank box or raw text in a given tool for months
after it ships upstream. Treat "does this diagram type exist in Mermaid" and "will it
render where the user is looking" as two separate questions.

**This file is a snapshot** (verified against the published `mermaid` npm package and
its `develop`-branch docs). Version numbers move fast — if a claim here matters for a
decision (not just background color), re-check `npm view mermaid version` and
`npm view mermaid time` rather than trusting the number below indefinitely.

---

## Snapshot: latest published version

- **`mermaid@11.17.2`**, published 2026-08-25 (confirmed via the npm registry).
- Verify freshness before relying on any "introduced in vX.Y" claim below:
  ```bash
  npm view mermaid version        # current latest
  npm view mermaid time --json    # publish dates, to gauge how recent "latest" is
  ```

---

## Diagram type → introduced-in version

Confirmed by checking the primary keyword string against the actual published
`mermaid.min.js` bundle for `11.17.2` (not just the docs) — the "Shipped?" column
reflects what is genuinely in that build, not what the source-repo docs describe.

| Diagram type | Primary keyword | Introduced | Shipped in 11.17.2? |
|---|---|---|---|
| Packet Diagram | `packet` (also `packet-beta`) | v11.0.0 | ✅ |
| Architecture Diagram | `architecture-beta` | v11.1.0 | ✅ |
| Radar Chart | `radar-beta` | v11.6.0 | ✅ |
| Ishikawa / Fishbone | `ishikawa-beta` | v11.12.3 | ✅ |
| Venn Diagram | `venn-beta` | v11.12.3 | ✅ |
| Tree View | `treeView-beta` | v11.14.0 | ✅ |
| Wardley Map | `wardley-beta` | v11.14.0 | ✅ |
| Event Modeling | `eventmodeling` | v11.15.0 | ✅ |
| Cynefin Framework | `cynefin-beta` | v11.16.0 | ✅ |
| Railroad (Syntax) Diagrams | `railroad-beta`, `railroad-ebnf-beta`, `railroad-abnf-beta`, `railroad-peg-beta` | v11.16.0 | ✅ |
| Swimlane Diagram | `swimlane-beta` | v11.16.0 | ✅ |
| Block Diagram | `block` (also `block-beta`) | pre-v11, established | ✅ |
| Kanban Board | `kanban` | pre-v11, established | ✅ |
| Requirement Diagram | `requirementDiagram` (also bare `requirement`) | long-established | ✅ |
| XY Chart | `xychart` (also `xychart-beta`) | ~v10.7, established | ✅ |
| Treemap | `treemap-beta` | established | ✅ |
| Sankey Diagram | `sankey` (also `sankey-beta`) | established | ✅ |
| ZenUML | `zenuml` | external plugin, never core | ⚠️ opt-in only |
| **Agent Flow** | `agentflow-beta` | **not yet released** | ❌ |
| **Use Case Diagram** | `usecase-beta` | **not yet released** | ❌ |

**Agent Flow and Use Case are documented on Mermaid's `develop` branch but absent from
the actual `11.17.2` bundle** — their doc pages carry an unresolved
`<MERMAID_RELEASE_VERSION>+` placeholder instead of a real version number, and grepping
the published minified bundle for `agentflow-beta` / `usecase-beta` returns zero
matches. **Do not draft either of these today** — no renderer anywhere can display
them yet. If the user's intent matches one:
- "Use case diagram" / "actor + system boundary" → use `flowchart LR` with actor-shaped
  nodes (`user((Customer))`) and a labelled subgraph as the system boundary, or fall
  back to `classDiagram` if the UML-specific notation matters more than fidelity.
- "Agent flow" / "AI agent workflow with tools" → use `flowchart TD` (or
  `sequenceDiagram` if timing/handoffs matter more than branching), and say so —
  mention that a dedicated `agentflow-beta` type is coming in a future Mermaid release
  so the user knows to revisit it later.

`zenuml` is a separate package (`@mermaid-js/mermaid-zenuml`) that a consuming app must
explicitly register — it is never available by default in GitHub, VS Code, or
Mermaid Live's default configuration. Don't reach for it unless the user confirms their
renderer has it registered.

---

## Renderer reality check

### GitHub (README, issues, PRs, Discussions, Gists)
Renders via GitHub's own internal service, which bundles a pinned Mermaid version and
updates on GitHub's schedule, not npm's. In practice this means:
- The well-established types (flowchart, sequence, state, ER, class, gantt, pie,
  journey, gitGraph, mindmap, timeline, quadrant, sankey) render reliably.
- Anything introduced in roughly the last 6–12 months of Mermaid releases is a coin
  flip — GitHub may not have picked it up yet. Treat the newest row-group in the table
  above (Cynefin, Railroad, Swimlane, Event Modeling, Wardley, Tree View, Ishikawa,
  Venn) as **unverified on GitHub** unless the user confirms it renders for them.
- There is no public, authoritative "GitHub currently runs Mermaid vX.Y.Z" page to
  check against — when it matters, the only reliable test is asking the user to look
  at the actual rendered page, or steering them to a type from the established list.

### VS Code — default/built-in Markdown preview
As of **VS Code 1.121** (released 2026-05-20), the built-in Markdown preview renders
Mermaid natively via a bundled extension ("Mermaid Markdown Features") that absorbed
the previously-separate `bierner.markdown-mermaid` extension. Before 1.121, the default
preview shows the raw fenced code block, not a diagram or an error — that alone is a
useful diagnostic if a user says "nothing renders."

This built-in support is **not the same thing** as the Mermaid Chart extension
(`mermaidChart.*` commands — see `.github/instructions/mermaid.instructions.md` in this
repo) or a manually-installed community extension; each bundles its own Mermaid version
and updates on its own cadence:
- The folded-in extension pinned `mermaid ^11.12.2` at merge time. VS Code's own release
  cadence (not live npm) governs when that bundled copy gets bumped, so it lags the
  npm-latest version by an unpredictable amount — likely weeks to a couple of months at
  any given time.
- Practical implication: a diagram type that shipped in the last one or two Mermaid
  minor releases (currently: anything from v11.16.0 or later — Cynefin, Railroad,
  Swimlane) may not render in a default VS Code preview even on a fully-updated VS Code,
  simply because the bundled copy hasn't caught up yet.

**When a diagram doesn't render in VS Code's default preview**, check in this order:
1. VS Code version — `Help > About`, must be **≥ 1.121** or the preview has no native
   Mermaid support at all (shows the raw code fence).
2. How recent the diagram type is — cross-reference the table above; anything from the
   last two Mermaid minor releases is the most likely culprit.
3. If both check out and it still fails, the bundled copy just hasn't caught up yet —
   recommend the Mermaid Chart extension or https://mermaid.live for that specific
   diagram instead of assuming the syntax is wrong.

### VS Code — Mermaid Chart extension / Mermaid Live Editor (mermaid.live)
Both track close to npm-latest and are the most reliable way to confirm a
brand-new diagram type actually renders, independent of what the default preview or
GitHub currently support. Prefer routing the user here to verify anything from the
newest row-group in the table above.

### Confluence
Depends entirely on which Mermaid macro app the workspace has installed and how
recently it was updated — there is no single answer. Don't assume parity with any of
the above; ask if the diagram type is unusual and it matters.

---

## Decision procedure ("which types are safe to draft here")

1. Diagram-type selection already asks for the rendering environment
   (`SKILL.md` Step 1). Use the answer:
   - **GitHub / unspecified / broad audience** → default to types from the
     established list (pre-11.16, or explicitly confirmed by the user). Flag anything
     newer as "verify this renders before relying on it" rather than silently using it.
   - **VS Code, default preview** → same caution for anything from the last two Mermaid
     minor releases; also confirm VS Code ≥ 1.121 if the user reports nothing rendering.
   - **VS Code Mermaid Chart extension / Mermaid Live / "just show me the syntax"** →
     free to use any type confirmed shipped in the table above.
2. Never draft `agentflow-beta` or `usecase-beta` — they don't exist in any published
   release yet, regardless of target. Use the fallback types noted above and say why.
3. When a user reports a diagram "not rendering" and the syntax passes Pass 2
   verification (`SKILL.md` Step 5), suspect a version/renderer mismatch before
   suspecting a syntax bug — walk the renderer reality check above rather than
   re-deriving the diagram from scratch.
