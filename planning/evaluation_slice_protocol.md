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

Frame indices are zero-based in the exact source video identified by its hash;
mapping coordinates are source pixels and retain the canonical transform from
the canonical view. Source video/run hashes and the alignment hash are required.
Malformed mappings, duplicate frame IDs or source frame indices, contradictory annotations,
and incomplete review are export diagnostics, not silently repaired rows.

## Splits and review

Assign splits at source-video/run level. A video or run identity may occur in
only one split; neighboring source frames cannot cross partitions. Held-out
exports require at least one development split-context manifest; callers must
provide the complete development-manifest inventory for a meaningful leakage
check. Development exporters should pass sibling manifests through
`split_context` when other development slices exist. The exporter rejects reused
video/run identities and duplicate or neighboring frame assignments across the
provided manifests. The standalone `validate_split_assignments()` helper can
check a collection before batch processing. Synthetic backgrounds are excluded. A second reviewer must mark
every exported frame reviewed; disagreements remain explicit until resolved.
The development pilot reports coverage, disagreement, missingness, and
exclusions. Held-out criteria are frozen only after this pilot and explicit
approval.

The development pilot review was performed by the agent using this work session;
`qa-2a` was supplied as the second-reviewer label but did not independently
inspect the frames. `review.status` and pilot `reviewed`/`coverage` metrics are
self-reported claims, not verified reviewer identity or independent QA. The
pilot therefore does not establish independent human QA and must not be used as
held-out or acceptance evidence requiring that review.

The manifest is an external, deterministic artifact distinct from provenance
manifests, SQLite run bundles, and broad Phase 9 exports.
