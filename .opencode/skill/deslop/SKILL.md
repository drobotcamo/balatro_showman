---
name: deslop
description: Remove predictable AI writing patterns from prose. Use this skill when writing, drafting, editing, reviewing, or revising pull request descriptions, issue updates, handoffs, or other lengthy technical summaries.
---

# Deslop

Use this skill before delivering substantial technical prose. Keep the facts,
evidence, commands, paths, and uncertainty, but remove filler, formulaic
transitions, vague claims, inflated language, repetitive summaries, and
mechanical list structures. Prefer direct statements with named actors and
specific evidence.

## Required Checks

- Cut throat-clearing, meta-commentary, and empty conclusions.
- Replace vague or passive wording with concrete subjects and actions.
- Vary sentence rhythm without adding flourish.
- Remove em dashes, bold-first list labels, rhetorical questions, and stock AI
  phrases where they do not serve the technical meaning.
- Do not dilute or omit limitations, failed checks, or unresolved uncertainty.
- Inspect the final text for literal `\\n` sequences. Use actual line breaks in
  the submitted body unless the backslash-n characters are intentionally part
  of a code example.

## Applies To

Run this pass on pull request descriptions, issue descriptions and comments,
work-thread batons, handoffs, review summaries, release notes, and any other
lengthy technical summary. Short factual status lines do not need expansion.

## PR Body Submission

Construct the body as a real multiline file or heredoc, not a quoted string
containing escaped newlines. Before submission, inspect the rendered or local
body and search for `\\n`. A clean body should contain section breaks as actual
line breaks and should preserve the repository's evidence and validation
commands.
