---
name: commit-message
description: 'Generate a commit message subject tagged with a Jira ID and an AI-SDLC marker, in the form "[JIRA-ID] [AISDLC] <summary>". Use when asked to prepare, write, or generate a commit message for completed work, or automatically after an implementation plan finishes.'
---

# Commit Message

Produce a ready-to-use commit message for work that has just been completed. This skill only generates the message — it never stages files or runs `git commit` itself; the user commits manually.

## Format

```
[JIRA-ID] [AISDLC] <imperative, concise summary>

<optional body: bullet list of key changes>
```

- `JIRA-ID`: the Jira issue key (e.g. `MKT-11`), uppercase, no `https://` link.
- `[AISDLC]`: literal marker, always included, identifying the commit as produced through the AI SDLC pipeline.
- Summary: imperative mood (e.g. "Add", "Fix", "Update"), no trailing period, aim for ≤72 characters.

## Procedure

1. **Resolve the Jira ID**:
   - If a source story is attached or known, look for a `**Jira:** [KEY](url)` line near the top of the story (written back by the `jira-story-sync` skill) and extract `KEY`.
   - If no story is available or it has no `**Jira:**` line, ask the user for the Jira ID.
   - If the user has no Jira ID for this change, use the literal placeholder `NO-JIRA` in place of the Jira ID and say so explicitly in the report — never invent or guess an ID.
2. **Summarize the change**: base the summary on what was actually done — the implementation report, the plan's `Change Log` entry, or `git diff --stat`/`git status` if available. Describe the net behavior change, not individual file edits.
3. **Compose the subject line** using the Format above.
4. **Add an optional body** only when there are multiple distinct changes worth listing separately (e.g. several files or scenarios) — a short bullet list, each line also imperative mood.
5. **Output the message** in a fenced code block so the user can copy it directly into `git commit -m "..."` or their editor. Do not run any git command.

## Rules

- Never fabricate a Jira ID; always confirm its source (story line vs. user-provided vs. `NO-JIRA` fallback).
- Never stage changes or run `git add`/`git commit` — this skill only produces the message text.
- Keep the subject line on one line; put any additional detail in the body after a blank line.
