# Phase 0 Inventory and Boundary

Updated: 2026-10-02

This is a repository inventory, not a claim that any legacy artifact is ready
for the active pipeline. Active stages must not import from `legacy/`; required
assets must move to an active, versioned store only after provenance,
redistribution status, compatibility, and checksums are established.

## Provenance manifest and read-only inventory

`planning/provenance_manifest.schema.json` defines manifest version `1.0.0`.
`planning/provenance_inventory.py` inventories every file below the four
candidate roots listed in this document, computes SHA-256 from the file bytes,
and emits stable, path-sorted JSON. Missing roots are emitted as
`unavailable`; present candidates remain `not-ready` unless provenance is
independently verified. Source, revision, license, compatibility, and
eligibility fields are explicit even when their values are unknown. The tool
only reads candidate files and writes output when the caller explicitly uses
`--output` outside the legacy tree.

Reproduce the current inventory from the repository root:

```powershell
python planning/provenance_inventory.py --output planning/provenance-inventory.json
```

The report is intentionally generated rather than treated as an active asset
store. It must not be used to promote a candidate without external evidence.

## Gate mapping

| Phase 0 output | Owning component | Repository evidence | Status |
| --- | --- | --- | --- |
| Public-artifact inventory and provenance records | Ground truth / dataset | Schema and read-only inventory shipped in PR #77; candidate evidence is not eligibility | inventory delivered; adoption unresolved |
| Aligned `(state, action, outcome)` oracle run | Ground truth | `planning/ORACLE_DATA_REVIEW.md` reports older unpinned runs and a 29-step pinned loss run with marker/positive frame mappings | historical transport/alignment metadata exists; current reliability, semantic suitability and measured rendered correspondence unaccepted |
| Real-frame eval set, annotation protocol, and QA export | Ground truth | Legacy labeling code exists (`legacy/label_store.py`, `legacy/tools/`), but no active tool, real clips, eval manifest, or protocol was found | blocked on real footage and format decision |
| Required assets/weights versioned and provenance-backed | Ontology / synthetic data / detection | A legacy YOLO checkpoint and OCR geometry exist; no active-store provenance, license, compatibility, or checksum records were found | not ready to adopt |
| Applicable evaluation criteria | Owning phase/slice components; protocol owned by ground truth | No approved first-slice protocol established here; Q03 remains staged under D028 | development protocol/pilot next; freeze criteria before held-out evaluation |

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

The inventory is shipped, not the next implementation. #81 owns reliable
recorded-run inspection, starting with recorder fault regressions before live
capture. #79 supplies a development protocol; #82's minimal tool/pilot informs
its final approved evaluation protocol. #80 gates only required artifact use.
Do not promote candidates without source, license, checksum and compatibility.
Historical reports are preserved; external video was not replayed for this
reconciliation. Alignment arithmetic alone is not measured frame correspondence.
No current live acceptance or broad Phase 0 completion is claimed.
