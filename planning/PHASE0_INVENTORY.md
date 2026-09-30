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
| Aligned `(state, action, outcome)` oracle run | Ground truth | Legacy live interfaces and sample parsed/granularized data exist, but no checked-in bridge source or verified full aligned run was found | blocked on runnable modded-game bridge |
| Real-frame eval set, annotation protocol, and QA export | Ground truth | Legacy labeling code exists (`legacy/label_store.py`, `legacy/tools/`), but no active tool, real clips, eval manifest, or protocol was found | blocked on real footage and format decision |
| Required assets/weights versioned and provenance-backed | Ontology / synthetic data / detection | A legacy YOLO checkpoint and OCR geometry exist; no active-store provenance, license, compatibility, or checksum records were found | not ready to adopt |
| Phase 1–10 thresholds | Owning phase components; protocol owned by ground truth | No Phase 0 evaluation protocol or numeric thresholds exist yet; Q03 tracks this gap | blocked on eval design and pilot data |

## Verified reusable references

- `legacy/vendor/balatro-cv-pipeline/external/runs/detect/train/weights/best.pt`
  is a candidate reference checkpoint, not an active dependency.
- `legacy/vendor/balatro-cv-pipeline/assets/text_boxes.json` is a candidate
  OCR-region reference.
- `legacy/vendor/balatro-policy-transformer/live/` and its
  `data/action_map.json` / `data/action_space_config.json` are candidate
  schema references.
- Legacy annotation and sample-run files can inform tooling and format
  research, but their source, game/mod version, and licensing are unverified.

## Boundary and next gate

The smallest safe next implementation is a provenance manifest schema plus a
read-only inventory of candidate artifacts. Do not copy weights, sprites, or
sample data into an active store until source identity, license, checksum, and
compatibility are verified. The oracle and eval-set work cannot be declared
complete from repository inspection: it requires a runnable modded game bridge,
timestamped real footage, and an agreed annotation/export format.
