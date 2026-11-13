# Reading non-code sources

## Transcripts

Raw transcripts are noisy. Distil before use:

1. Drop greetings, scheduling, tangents and repeated statements.
2. Keep only statements about: who uses the app, what they are trying to
   achieve, steps they take, what they see, what goes wrong, rules
   ("only leaders can…", "must be approved before…").
3. Write each kept statement as one line with its source reference
   (timestamp, speaker, line number) and tag it `PERSONA`, `GOAL`, `STEP`,
   `RULE`, `PAIN` or `TERM`.
4. Collect `TERM` lines into a vocabulary list; use those words for journey
   and step names.

Transcript statements are `Inferred` until code or screenshots confirm.

## Screenshots

Per screenshot, record:

- Screen title / URL visible / which persona sees it.
- Fields: label, input type, required marker, default or sample value,
  read-only vs editable.
- Actions: buttons, links, menu items, icons, with labels.
- Messages: errors, banners, empty states, confirmations.
- Data shown: tables, columns, counts, status badges.
- Step position: what screen likely precedes and follows it.

Map each screenshot to a code view or component once found. A screenshot
with no matching code is an orphan; a screen with no screenshot is fine.

## Test cases

- Each test case or scenario is a candidate journey or alternate path.
- Preconditions reveal personas, roles and required state.
- Expected results reveal rules and messages; cross-check them against code.
- Negative cases point at validation and business-error exits.
