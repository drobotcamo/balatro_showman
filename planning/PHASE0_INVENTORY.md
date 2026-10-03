# Phase 0 Inventory and Boundary

Updated: 2026-10-02

This is a repository inventory, not a claim that any legacy artifact is ready
for the active pipeline. Active stages must not import from `legacy/`; required
assets must move to an active, versioned store only after provenance,
redistribution status, compatibility, and checksums are established. Issue
#80's bounded eligibility disposition is in
`planning/PROVENANCE_ELIGIBILITY.md`.

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
| Aligned `(state, action, outcome)` oracle run | Ground truth | Historical run evidence plus the marker-associated 197-step Ante 1 session recorded for #79; its first-slice segment is present and a separate Ante 5 continuation is retained as another run | first-slice segment available; full first session has no terminal outcome, and seven sampled frame/step mappings remain unverified for rendered synchronization |
| Real-frame eval set, annotation protocol, and QA export | Ground truth | `FIRST_SLICE_PROTOCOL_V1.md`/`V2.md`; exporter and guide in PR #112; external user-reviewed seven-frame manifest/report linked from #79/#82 | bounded development sample and tooling delivered; no predictions, held-out set, or broad Phase 3–8 sufficiency claim |
| Required assets/weights versioned and provenance-backed | Ontology / synthetic data / detection | A legacy YOLO checkpoint and OCR geometry exist; no active-store provenance, license, compatibility, or checksum records were found | not ready to adopt |
| Applicable evaluation criteria | Owning phase/slice components; protocol owned by ground truth | User-approved `planning/FIRST_SLICE_PROTOCOL_V2.md`; #79 records the scoped decision | first-slice criteria/support/context frozen for prospective held-out use; other phase/slice criteria remain staged; no held-out score exists |

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

The inventory is shipped. #79/#82 delivered a bounded first-slice development
pilot and frozen prospective criteria. No model predictions or held-out source
set have been evaluated; seven nearest-frame mappings remain unverified for
rendered synchronization. #80 gates only required artifact use. Do not promote
candidates without source, license, checksum and compatibility. No broad Phase 0
completion is claimed. No legacy candidate has been promoted; the class-map
dependency remains unresolved for any future class-map-consuming slice.
