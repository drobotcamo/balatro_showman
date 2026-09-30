# Phase 0 Inventory and Boundary

Updated: 2026-09-30

This is a repository inventory, not a claim that any legacy artifact is ready
for the active pipeline. Active stages must not import from `legacy/`; required
assets must move to an active, versioned store only after provenance,
redistribution status, compatibility, and checksums are established.

## Gate mapping

| Phase 0 output | Owning component | Repository evidence | Status |
| --- | --- | --- | --- |
| Public-artifact inventory and provenance records | Ground truth / dataset | `legacy/vendor/balatro-cv-pipeline/`, `legacy/vendor/balatro-policy-transformer/` contain reference code/data; no active provenance records were found | inventory only |
| Aligned `(state, action, outcome)` oracle run | Ground truth | `ground_truth/balatro_mod/` Lua producer merged via PR #9; two real runs persisted and audited in `planning/ORACLE_DATA_REVIEW.md`, but neither is pinned to the merged revision and neither carries video-to-engine alignment | transport validated; contract conformance and video alignment pending |
| Real-frame eval set, annotation protocol, and QA export | Ground truth | Legacy labeling code exists (`legacy/label_store.py`, `legacy/tools/`), but no active tool, real clips, eval manifest, or protocol was found | blocked on real footage and format decision |
| Required assets/weights versioned and provenance-backed | Ontology / synthetic data / detection | A legacy YOLO checkpoint and OCR geometry exist; no active-store provenance, license, compatibility, or checksum records were found | not ready to adopt |
| Phase 1–10 thresholds | Owning phase components; protocol owned by ground truth | No Phase 0 evaluation protocol or numeric thresholds exist yet; Q03 tracks this gap | blocked on eval design and pilot data |

## Verified reusable references

- `legacy/vendor/balatro-cv-pipeline/external/runs/detect/train/weights/best.pt`
  is a candidate reference checkpoint, not an active dependency.
- `legacy/vendor/balatro-cv-pipeline/assets/text_boxes.json` is a candidate
  OCR-region reference.
- `legacy/vendor/balatro-policy-transformer/live/` and its
  `legacy/vendor/balatro-policy-transformer/data/action_map.json` and
  `legacy/vendor/balatro-policy-transformer/data/action_space_config.json`
  are candidate schema references.
- Legacy annotation and sample-run files can inform tooling and format
  research, but their source, game/mod version, and licensing are unverified.

## Boundary and next gate

The smallest safe next implementation is a provenance manifest schema plus a
read-only inventory of candidate artifacts. Do not copy weights, sprites, or
sample data into an active store until source identity, license, checksum, and
compatibility are verified. The oracle and eval-set work cannot be declared
complete from repository inspection: the bridge source is merged and transport
is validated (PR #9, `planning/ORACLE_DATA_REVIEW.md`), but Phase 0 still
requires a capture pinned to the merged revision with video-to-engine alignment,
timestamped real footage, and an agreed annotation/export format. The oracle
producer/reducer ownership decision (#14) gates the next producer iteration.
