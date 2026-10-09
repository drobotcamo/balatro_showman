# Development evaluation-slice protocol (v1)

This is the bounded protocol used by the first annotation/export pilot. It is
not a Phase 3–8 sufficiency claim and it does not promote producer labels to
independent ground truth.

## Unit and supported fields

One unit is one externally stored video frame with an auditable producer-step
alignment. The pilot records page, zone, object identity, modifier/edition/seal/
sticker, and OCR text when visible. Each value carries its observation status:
`observed`, `unknown`, `missing`, `occluded`, `ambiguous`, or `unsupported`.
Raw values and normalized values are separate; oracle values are validation
references only and are never copied into observations.

Frames use zero-based source coordinates and retain the canonical transform to
the source pixel space. Source video/run hashes and the alignment hash are
required. Malformed mappings, duplicate frame IDs, contradictory annotations,
and incomplete review are export diagnostics, not silently repaired rows.

## Splits and review

Split at source-video/run level. Neighboring frames from one source cannot be
split across partitions. Synthetic backgrounds are excluded. A second reviewer
must mark every exported frame reviewed; disagreements remain explicit until
resolved. The development pilot reports coverage, disagreement, missingness,
and exclusions. Held-out criteria are frozen only after this pilot and explicit
approval.

The manifest is an external, deterministic artifact distinct from provenance
manifests, SQLite run bundles, and broad Phase 9 exports.
