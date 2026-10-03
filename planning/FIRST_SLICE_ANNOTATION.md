# First-slice annotation/export (development only)

`ground_truth.eval_manifest` exports caller-authored, independently reviewed
visual observations for the selected stages of `FIRST_SLICE_PROTOCOL_V1.md`.
It does not extract frames, infer observations from the oracle, score a held-out
set, or write into a run bundle. No private recording or annotation is checked
in. The input is UTF-8 JSON; the output is a distinct `first-slice-evaluation/1`
JSON manifest in caller-selected storage. Example input structure is exercised
by `tests/test_eval_manifest.py` (`sample`).

```powershell
python -m ground_truth.eval_manifest "C:\external\annotations.json" "C:\external\evaluation.json"
```

The command prints the output SHA-256. Repeat export with identical content
keeps identical bytes; a different payload cannot replace an existing file.
Neither the input nor source evidence may be selected as the output path. The
caller must verify the destination is external to Git, accessible only as
intended, and not a source file. Validation fails closed before output writing.

## Input records

`schema` is `first-slice-annotations/1`; `protocol` is
`FIRST_SLICE_PROTOCOL_V1`. `sources` contains a unique source `id`, `run_id`,
`group` (same underlying play, including excerpts/transformed captures),
`split` (`development`, `held_out`, `training`, `synthetic`), `origin` (`real` or
`synthetic`), lowercase SHA-256 digests for `video`, `session`, and `steps`, and
`alignment` with `method`, `version`, `marker`, `offset_ns`, and `fps`. The
alignment parameters are provenance, not proof of visual correspondence. A
synthetic source is restricted to the synthetic split; real evaluation and
training sources must remain disjoint. The exporter rejects differing splits
for a shared run ID, video hash, or group. It cannot discover repeated play
with different hashes: the caller must group those sources and audit external
training/synthetic source registries before any held-out use.

Each `frame` references its source by `source_id`, an integer video `index`,
`timestamp_ns`, optional `step_id` (null if not paired), `stage` (`start`,
`small_blind_select`, `small_blind_play`, `cash_out`, `first_shop`), and the
decoded frame's SHA-256. A frame `alignment` includes `state` (`confirmed`,
`unverified`, `failed`, `disputed`), `uncertainty_frames` (or null), and a
nonempty evidence note. `confirmed` requires a step and a measured uncertainty;
it is not assigned automatically from timestamps. Optional `exclusion` records
why the frame is not usable for comparison. Unaligned/disputed samples remain
visible in output and are not scored by this exporter.

`geometry` declares `canonical_size` and `source_size` in pixels, positive
per-axis `scale`, `offset`, and `active_source_box` as `[x,y,w,h]` source pixels.
The mapping is `source_x = offset_x + canonical_x * scale_x` (likewise for y);
no rotation or perspective is supported. Per-label `box` is `[x,y,w,h]` in
canonical coordinates. Output adds an inspectable `source_box` using that
mapping. Coordinates outside the canonical, active, or source rectangle are
errors. Canonical dimensions, active viewport, crop/letterbox, overlays, and
scale must be measured for each source; the fixture's 960×540 is **not** a
project-wide canonical-space decision. Unsupported geometry needs a later
version, not an improvised conversion.

Every `label` has a frame-unique `id`, a `family` (`page`, `control`, `object`,
`ocr`, `transition`), and a `key` unique within its family on that frame (for
multiple objects use distinct keys). `state` is `observed`, `unknown`,
`missing`, `occluded`, `ambiguous`, `unsupported`, or `not_applicable`. Store
literal observed `raw` separately from `normalized`; neither may be supplied
for an unobserved state. Any `inferred` value is separate and cites its
`method` and `evidence`. Optional `zone`, `order`, `attributes` (including
identity, edition, seal, sticker, modifier, and visibility when applicable),
and canonical `box` retain visible object details. Observed objects require
all four (box, zone, order, attributes); attributes should explicitly record
unknown modifier/edition/seal/sticker/identity rather than inventing them.
A `transition` also declares
`context_frames` from the same source; do not use future context to rewrite an
earlier raw observation. Oracle fields and producer page labels must **not** be
copied into visual labels. Oracle references belong to the associated run and
are for validation only.

`annotator` and `reviewer` must differ. `review` is `agree`, `disagree`, or
`excluded`; `adjudicated` retains the reviewed raw value or null when excluded
or unresolved. `rationale` records the review basis. A disagreement does not
erase the original. Unresolved cases must use a non-observed state; this tool
does not elevate producer labels to independent review. The exporter rejects
duplicate frames/slots, malformed geometry, incomplete review, missing source
or alignment provenance, invalid version/hash/split/context, and synthetic
leakage. It sorts sources, frames, labels and count rows deterministically.

`pilot_counts` reports observed/unknown/etc. and agreement/disagreement counts
by source, stage, and family. These are inventory counts, **not** accuracy,
coverage denominator, alignment success, or a sufficiency claim. A bounded
pilot still needs independently inspected real frames and a per-recording
report of sampled/eligible/missing/excluded stages and families, disagreements
and adjudications, correspondence evidence, and limitations under the
development protocol. Final Q03/Q04 criteria and held-out collection require
the separate user-approved frozen protocol. No broad Phase 3–8 sufficiency or
Phase 9 export gate is passed by this manifest.
