#!/usr/bin/env bash
# Packages the plugin as a .github folder to paste into a target repo.
set -euo pipefail
cd "$(dirname "$0")"

out=dist/.github
rm -rf dist
mkdir -p "$out/agents" "$out/skills"

cp com.github.copilot/agents/*.agent.md "$out/agents/"
for d in skills/*/; do
  [[ -f "$d/SKILL.md" ]] && cp -R "${d%/}" "$out/skills/"
done

(cd dist && zip -qr legacy-explorer-github.zip .github)
find dist -type f | sort
