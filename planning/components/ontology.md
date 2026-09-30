# Component Contract: Ontology and Metadata

Status: `planned`

## Purpose

Define stable identities and composition rules for every visible gameplay object
the pipeline may detect or reconstruct.

## Inputs

- Existing asset sprites and names.
- Balatro screenshots and UI observations.
- Public model class mappings where useful.

## Outputs

- Canonical asset IDs and human-readable names.
- Class-family definitions.
- Asset source and visual-variant metadata.
- Modifier and parent-child composition rules.
- Versioned class map usable by training and inference.

## Invariants

- IDs are stable once published.
- Names are unique within their declared family.
- Modifier combinations do not require an unbounded class explosion.
- Unknown assets can be represented without corrupting known IDs.

## Acceptance Criteria

- Every initial asset has a source, family, ID, and expected visual footprint.
- A class-map version can translate detector IDs back to canonical metadata.
- At least one example exists for every composition rule.
