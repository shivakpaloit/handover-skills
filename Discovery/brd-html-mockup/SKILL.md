---
name: brd-html-mockup
description: "Create an interactive HTML mockup or clickable prototype of user journeys from a Business Requirements Document (BRD). Use when asked to turn business requirements into HTML screens, journey mockups, or a prototype. Discover the BRD and complementary files, find applicable design framework or design system skills, resolve conflicting design choices with the user, and verify journey coverage and interactions."
---

# BRD HTML Mockup

Turn a Business Requirements Document into a reviewable, interactive HTML prototype of its in-scope user journeys, not an HTML rendering of the document itself.

## Recommended Model

Recommend **Claude Sonnet 5.5** for this workflow. This is a recommendation, not a mandatory model setting: do not claim to switch models, add unsupported model frontmatter, or override the user's selected model. If asked how to select it, use the host's model picker.

## 1. Resolve the BRD

1. Prefer an explicit user-provided path or attachment.
2. Otherwise inspect `docs/business-requirement-docuemnt` (including this spelling). It may be a file or a directory; discover candidate BRDs inside it.
3. If that path is absent or contains no usable BRD, check these common alternatives:
   - `docs/business-requirement-document`
   - `docs/business-requirements-document`
   - `docs/business_requirements_document.md`
   - BRD-named files immediately under `docs/`.
4. If no source is found, ask the user to supply the BRD file or path. If multiple candidates remain, ask which is authoritative; do not silently combine them.
5. Read the entire selected BRD, including tables and appendices. Use available document-reading tools or skills for its format. If content cannot be extracted reliably, ask for a readable export rather than inventing requirements.

Use the host's structured question tool when available for all required questions. Stop at unresolved input gates before generating the mockup.

## 2. Discover Complementary Journey Inputs

Inspect the BRD's linked or referenced files and relevant nearby documentation. Look for:

- User stories, use cases, journey maps, process diagrams, and acceptance criteria.
- Role/permission matrices, business rules, state transitions, and exception flows.
- Data dictionaries, form fields, sample data, content/copy, and notification templates.
- Existing wireframes, screenshots, brand assets, accessibility requirements, and design guidelines.

Ask the user whether any additional complementary files are needed to accurately produce the journeys. Present the files already found and the specific missing inputs; let the user provide paths/attachments or confirm that the BRD and discovered materials are sufficient.

Treat the BRD as the scope authority. Complementary files may clarify its journeys but must not silently add features or override requirements. Ask about contradictions that change behavior, roles, fields, or outcomes. Confirm which source wins before implementing those parts.

Do not search unrelated personal directories or send source documents to external services. Use fictional, non-sensitive demo data.

## 3. Select the Design Framework / Design System

Before choosing visual conventions:

1. Inspect available skill names and descriptions for relevant UI design, design systems, branding, accessibility, or framework guidance. Check workspace skill locations and host-listed personal/plugin skills when accessible; do not assume unlisted skills exist.
2. Inspect the BRD and complementary design files, plus relevant project manifests, style tokens, component-library configuration, and existing UI examples when present.
3. Distinguish a runtime framework (such as React or Next.js), a styling framework (such as Tailwind or Bootstrap), and a design system (such as Material Design or a company component library). A complementary stack is not automatically a conflict.
4. If multiple alternative design frameworks or design systems are detected, ask the user which to use. Show the candidates and their evidence, explain any HTML-delivery constraints, and wait for a selection. Do not silently choose, blend alternatives, or prefer whichever skill loads first.
5. If one coherent choice is detected, state the intended choice and invoke/read its applicable available skills before generating HTML. Also load relevant frontend and accessibility skills when available.
6. If no design guidance is found, ask the user to provide a design system/brand reference or approve a neutral, accessible vanilla HTML/CSS design.

Use the selected system's tokens, typography, spacing, colors, and component conventions consistently. If it requires a runtime or build step incompatible with standalone HTML, explain the limitation and ask whether to use a build/export approach or a clearly labeled visual approximation. Do not label approximations as actual library components or certified compliance.

## 4. Map Requirements to Journeys

Before writing the prototype, derive a compact working map:

| Source ID / section | Actor | Journey and steps | Screens / states | Business rules / exceptions |
|---|---|---|---|---|

- Preserve existing requirement IDs. Where none exist, reference the source heading or page instead of inventing official IDs.
- Cover all in-scope actors and journeys, including required validation, empty/error states, permission boundaries, confirmations, cancellation, and recovery where specified.
- Distinguish user-facing workflows from non-UI requirements; do not force backend-only requirements into fake screens.
- Ask about missing decisions that materially change journeys. Label non-blocking presentation assumptions explicitly.
- Keep out-of-scope and future features out of the prototype. Do not invent required fields, eligibility rules, payment flows, or successful outcomes.

Keep this map in working context and include a compact coverage/assumptions section in the deliverable for reviewers. Do not create a separate planning document unless requested.

## 5. Build the HTML Prototype

Default output: `docs/mockups/<brd-slug>/index.html`. Honor an explicit output path.

- Check for existing output before writing. Ask before replacing an existing prototype; preserve user-maintained content during an approved update.
- Prefer one self-contained HTML file with inline CSS and JavaScript, usable locally without a build, network access, or backend. Use local companion assets only when the selected design or provided assets require them.
- Do not add application dependencies merely to make a mockup. Reuse an existing toolchain only when needed for the approved design framework and HTML export.
- Follow applicable repository instructions for any HTML, CSS, JavaScript, or framework files being written.
- Provide clear entry points for each actor/journey and working navigation between screens. Mark any role switcher or scenario selector as a demo/reviewer control, not real authentication.
- Make primary actions work: form validation, branching, confirmations, state changes, and recovery must reflect the source rules. No dead buttons, placeholder links, or fabricated server responses presented as real integrations.
- Simulate source-required backend operations locally and label them as simulations. No live authentication, real transactions, outbound submissions, or storage of sensitive information.
- Keep simulated state internally consistent across the journey. Include an obvious reset control so reviewers can repeat scenarios.
- Use semantic landmarks, headings, labels, accessible names, visible keyboard focus, keyboard-operable controls, and accessible status/error feedback. Manage focus when switching views or opening dialogs.
- Make layouts usable on narrow and wide viewports. Do not convey status by color alone.
- Use realistic fictional content rather than generic filler; escape document-derived content and use safe DOM APIs such as `textContent` instead of injecting untrusted HTML.
- Include a clearly separated reviewer section listing source documents, selected design approach, journey coverage, simulation boundaries, assumptions, and unresolved gaps.

## 6. Verify the Saved Deliverable

Use browser tools or the repository's available browser-testing tools when possible:

1. Open the saved HTML and confirm it loads with no missing required assets or JavaScript errors.
2. Walk every mapped journey end to end, including each source-required branch, validation failure, cancellation, and recovery path.
3. Check that interactive controls perform their labeled actions, simulated state remains consistent, and reset restores the initial demo state.
4. Check keyboard navigation, labels, visible focus, and narrow/wide layouts for clipping or unusable controls.
5. Compare the final screens and states against the working coverage map. Account for every in-scope journey and report unsupported or unresolved requirements rather than claiming full coverage.

Do not install browser tooling without a demonstrated need or claim browser validation when only static inspection was possible. If browser tools are unavailable, perform the available static checks and explicitly report the remaining manual verification. Stop temporary preview helpers after testing unless the user asks to keep them available.

## Completion Report

Provide the saved HTML path/link, how to open it, the design framework/system used, covered journeys, assumptions/gaps, and checks actually performed. Clearly identify simulated functionality and any unverified behavior. Register the HTML as a deliverable when the host supports artifact registration.
