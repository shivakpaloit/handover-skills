# Exporting to SVG for Non-Native Renderers

Some targets don't render Mermaid source directly — Marp slide decks, PDF/PPTX export,
Confluence macros that expect an image, older static-site generators. For these, render
the diagram to SVG first and embed the image instead of the fenced ` ```mermaid ` block.

## Rendering options

| Tool | Runs | Network |
|---|---|---|
| `@mermaid-js/mermaid-cli` (`mmdc`) | Locally, via `npx @mermaid-js/mermaid-cli` | None — diagram source never leaves the machine |
| `mermaid.ink` API | Remote HTTP GET, URL-encodes the diagram source | Diagram source is sent to a third-party service |

Prefer the local CLI when the diagram may contain project-sensitive names or structure.
Reach for `mermaid.ink` only when a local Node/CLI toolchain isn't available.

## The width/max-width trap (applies to both renderers)

Generated SVGs commonly carry `width="100%"` and an inline `style="max-width: <n>px"` on
the opening `<svg>` tag. Any consumer that respects those values — an `<img>` tag, a
Marp slide, a browser — will size the image to fill its container regardless of the
`width`/`w:Npx` directive you set on the embedding markup. This is not a bug in the
embedding syntax; the SVG itself overrides it.

**Always patch the SVG after generating it, before embedding:**

```python
import re, pathlib

svg_path = pathlib.Path("path/to/diagram.svg")
content = svg_path.read_text(encoding="utf-8")
content = re.sub(r'(<svg[^>]*)\bwidth="100%"', r'\1width="600"', content, count=1)
content = re.sub(r'(<svg[^>]*)style="max-width:[^"]*"', r'\1style=""', content, count=1)
svg_path.write_text(content, encoding="utf-8")
```

Or by hand: in the opening `<svg>` tag, change `width="100%"` to a fixed pixel value and
delete the `style="max-width: ...px"` attribute entirely.

Verify the patch worked by re-opening the SVG and confirming the `<svg>` tag has no
`width="100%"` and no `max-width` in its `style`.

## Embedding the patched SVG

Use the embedding target's native image-sizing mechanism — check its own conventions
first (for example, a Marp deck ignores inline `<img style>` and instead uses the
`![alt w:600px](./diagram.svg)` sizing directive). SVG scales losslessly, so prefer it
over a rasterized PNG wherever the target supports it.

Keep the diagram's own title in the surrounding document heading rather than baking a
title into the SVG — one caption, not two.
