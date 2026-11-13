---
name: refine-transcript
description: "Refine a Microsoft Teams transcript (VTT or copied text) or a raw transcript with no speaker data into a lossless, organised markdown document: topic headers, clean speaker turns, original chronology kept, nothing summarised or dropped. Flags likely misheard terms (product names, acronyms, people, jargon) and asks the user to confirm them before applying. Use when the user asks to clean up, refine, tidy, organise, structure or format a meeting transcript or recording text."
---

# Refine transcript

Turn a messy transcript into a readable document **without losing content**.
This is formatting, not summarising. Every sentence in the source must appear
in the output, in the same order.

Track the five steps below with a todo list.

## Rules

Allowed changes:

- Add `##` topic headers and `###` sub-topic headers.
- Remove transcript noise: VTT `WEBVTT` header, cue numbers, cue IDs,
  `-->` timing lines, `<v Name>` tags.
- Merge consecutive lines from the same speaker into one turn.
- Fix punctuation, capitalisation and paragraph breaks.
- Apply term corrections **the user approved** in step 3.

Not allowed:

- Summarising, paraphrasing, shortening or reordering what was said.
- Dropping filler, false starts or repeats, unless the user explicitly asks for
  a "clean read" (then remove only `um`, `uh`, `erm` and immediate
  word repeats, and say so in the document header).
- Guessing a term correction without asking.
- Inventing speaker names for a raw transcript.

Chronology: headers follow the conversation. If a topic comes back later,
add a new header such as `## Pricing (revisited)`. Never move text to group
it with an earlier section.

## 1. Read and detect

Read the whole file. Identify the format:

| Format | Looks like |
| --- | --- |
| Teams VTT | `WEBVTT`, `00:01:02.000 --> 00:01:05.000`, `<v Jane Doe>text</v>` |
| Teams copied text | Name line, then a timestamp line (`0:02` or `00:01:02`), then text |
| Speaker-labelled | `Jane: text` or `[00:01:02] Jane: text` |
| Raw | Plain text, no speakers |

For raw transcripts, do not guess speakers. Write paragraphs and, where
the speaker obviously changes (a question followed by an answer), start a new
paragraph. If the user can name the speakers, use those names.

Note the meeting length, the speakers, and the main topic shifts.

## 2. Find suspect terms

Speech-to-text often mishears domain words. Look for:

- Words that make no sense in context ("cubes cluster" for "Kubernetes cluster").
- Near-miss product, company, tool or people names ("Jura" for "Jira",
  "get hub" for "GitHub").
- Acronyms split or spelled out wrongly ("A P I gateway", "sequel" for "SQL").
- The same term spelled several ways across the transcript.
- Names of attendees spelled differently from the speaker labels.

Use the speaker names, the meeting subject and any files in the workspace
(READMEs, docs, glossaries) as context for what the right term probably is.

## 3. Ask the user

Ask in batches of up to 10 questions. For each suspect term give:

- the heard text and how many times it appears,
- one short quote showing it in context, with a timestamp if there is one,
- your best guess as the recommended option, plus "keep as is".

Leave free-text input on so the user can type the right term.

If the user skips or does not know, keep the original text and mark it
`[?]` the first time it appears, for example `cubes cluster [?]`.

## 4. Write the refined transcript

Write to `<source-name>.refined.md` next to the source, unless the user names
another path. For long transcripts (more than about 300 lines) write it in
chunks: create the file with the first sections, then append section by
section. Never try to output a long transcript in one reply.

Structure:

```markdown
# <Meeting title or file name>

- **Source:** <file name>
- **Date / length:** <if known>
- **Speakers:** <names, or "not identified">
- **Edits:** formatting only, nothing removed | clean read (fillers removed)

## Contents

1. [Topic one](#topic-one) (00:00)
2. [Topic two](#topic-two) (07:45)

## Topic one

**Jane Doe** (00:00:12): Text of the turn, with punctuation fixed.

**John Smith** (00:00:31): Text of the reply.

## Topic two

...

## Term corrections

| Heard | Changed to | Times |
| --- | --- | --- |
| Jura | Jira | 6 |

## Open terms

- `cubes cluster [?]` at 00:14:02, not confirmed by the user.
```

Use the first timestamp of each turn and of each section. Leave
timestamps out if the source has none. Drop the "Term corrections" or
"Open terms" section if it would be empty.

## 5. Check nothing was lost

Go through the source again from start to end and compare it with the
output, section by section:

1. Every source turn appears in the output, in the same order.
2. The first and last few words of each turn match the source, except
   for approved corrections and punctuation.
3. No turn was shortened. Long turns are the most likely to have been
   cut, so check those closely.
4. Speaker labels and timestamps match the source.

Fix any gaps in the file before reporting. Then tell the user:

- the output path,
- the number of sections and turns,
- the corrections applied and the open `[?]` terms,
- any part of the source you could not read (garbled or cut-off text, kept
  as is).
