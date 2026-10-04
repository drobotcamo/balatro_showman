# Component Contract: Ontology and Metadata

Status: `planned`

## Purpose

Define stable identities and composition rules for every visible gameplay object
the pipeline may detect or reconstruct, plus the page/zone vocabulary and the
typography needed for synthetic OCR.

## Inputs

- Existing asset sprites and names.
- The existing vendored class-ID map (cards, jokers, consumables, vouchers,
  blinds, stickers, and the like).
- Balatro screenshots and UI observations.
- Public model class mappings where useful.

## Outputs

- Canonical asset IDs and human-readable names, extended from the adopted class
  map rather than invented fresh.
- Class-family definitions, including page and zone vocabulary.
- Asset source and visual-variant metadata.
- Modifier/edition/seal composition rules attached to parent objects.
- Typography assets: every glyph, digit, symbol, and modifier state (negative,
  debuffed, highlighted) needed by synthetic OCR.
- Versioned class map usable by training and inference.
- Mechanics definitions keyed to this vocabulary, distinct from run instances and
  visual tracks. #122 versions the slice semantics in
  `planning/RUN_MECHANICS_DESIGN.md`; #125 owns exhaustive Joker inventory and
  authored/user-approved/engine-validated statuses separately.

## Invariants

- IDs are stable once published; existing IDs are extended, never renumbered.
- Names are unique within their declared family.
- Modifier combinations do not require an unbounded class explosion; they are
  composition labels with a dedicated visible-attribute channel.
- Unknown assets can be represented without corrupting known IDs.
- Every typography glyph declares its source and license.
- A bounded mechanics/visual slice declares only its consumed vocabulary and
  pinned revision. Exhaustive registry/typography is not a Dagger or Phase 0 gate.

## Acceptance Criteria

- Every initial asset has a source, family, ID, and expected visual footprint.
- A class-map version can translate detector IDs back to canonical metadata and
  is compatible with existing granularized data and published weights.
- At least one example exists for every composition rule.
- Typography coverage is complete for all OCR fields and states.
