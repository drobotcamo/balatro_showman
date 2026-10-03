# Required-slice provenance and eligibility

Updated: 2026-10-02

This is the bounded Q02 disposition for issue #80. It records what the
currently selected development slice may consume; it does not grant a blanket
license or promote the legacy tree into an active store.

## Selected slice

The current pilot is the inspectable recorded-run/evaluation path owned by
#81/#79/#82. Its required inputs are recorded video, the oracle run bundle, the
versioned development protocol supplied by #79, and minimal annotation/export
tooling. No model weights, game assets, OCR dataset, or legacy policy checkpoint is required by that
dependency-free pilot, so unresolved legacy candidates do not block it.

The detector class-map CSV is not treated as optional: the inventory references
it as a possible semantic dependency, but this checkout does not contain a
readable `legacy/vendor/balatro-policy-transformer/data/class_map.csv`. Its
source, revision, checksum, license, and compatibility must be recorded before
any class-map-consuming slice uses it.

## Artifact dispositions

| Artifact or class | Evidence | Eligibility | Status |
| --- | --- | --- | --- |
| `legacy/vendor/balatro-cv-pipeline/**` | Gitlink `4f06eaeeb57ef90f84a321c1cb67088e265bce20`; no independently verified source/license evidence here | Research reference only; do not redistribute or import | Not-ready/unavailable |
| `legacy/vendor/balatro-policy-transformer/**` | Gitlink `d2f087640438857b1e22cfaa1cfc533b76cf2bef`; no independently verified source/license evidence here | Research reference only; do not redistribute or import | Not-ready/unavailable |
| `.../data/class_map.csv` | Referenced by legacy documentation, absent here | Required only if a later slice consumes class IDs; user/source decision required | Unavailable |
| `legacy/label_store.py`, `legacy/tools/**` | Repository-local legacy files; no independent redistribution evidence | Tooling research only; no promotion | Not-ready |
| Legacy checkpoint, OCR geometry, datasets, footage, screenshots, game assets | Candidate references identified in `PHASE0_INVENTORY.md`; no artifact-specific source/license/revision evidence | Not eligible for active use or redistribution | Not-ready |

Presence, a filename, or a transitive code license is insufficient evidence
for weights, datasets, footage, screenshots, or game assets. A future consuming
slice must record source, exact revision, SHA-256, compatibility, license and
redistribution evidence. The user-approved Q02 policy for unresolved legacy
artifacts is `user-supplied`: such artifacts must be provided outside the
public active store and are not redistributed by this repository.

## Reproduction and boundary checks

```powershell
python planning/provenance_inventory.py
python planning/check_contracts.py
git diff --check
```

The inventory is read-only unless `--output` is explicitly supplied. It records
candidate bytes and unknowns; it does not copy, modify, or promote anything.
The missing vendor checkout is an eligibility finding, not a repair under this
issue.

## Open decision

Q02 is resolved for the bounded policy choice above: future unresolved legacy
artifacts are user-supplied. The dependency-free pilot may proceed without
them. This is not a legal conclusion about any particular artifact; each
consuming slice still needs artifact-specific evidence and compatibility review.
