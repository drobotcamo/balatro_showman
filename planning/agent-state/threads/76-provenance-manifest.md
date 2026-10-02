# Work Thread
Updated: 2026-10-02
Issue: #76
PR: none
Owner: project lead
Branch: issue-69-review-gate
Worktree: C:\Users\camgr\Documents\code_projects\balatro_showman
Objective: Define a versioned provenance manifest and deterministic read-only inventory for legacy candidate artifacts.
Status: ready-for-review
Scope: planning/provenance_manifest.schema.json, planning/provenance_inventory.py, planning/PHASE0_INVENTORY.md, tests/test_provenance_inventory.py
Dependencies: Phase 0 inventory boundary; ground-truth contract; D016.
Completed:
- Added manifest schema version 1.0.0 with explicit identity, source, revision, license, checksum, compatibility, eligibility, and status fields.
- Added deterministic path-sorted inventory over all four candidate roots; missing roots are `unavailable`, present candidates are `not-ready`, and unknown provenance is represented as null/unknown rather than inferred.
- Confirmed the current repository inventory contains 189 candidate files and performs no writes without an explicit output path.
- Documented reproduction and the research-reference-only boundary in `planning/PHASE0_INVENTORY.md`.
Next: Open the T0 auto-PR, verify planning CI, merge, and settle Issue #76 if GitHub permissions allow.
Decisions: No active-store layout or provenance claim was introduced; candidate eligibility remains research-reference-only.
Risks: License, upstream revision, compatibility, and redistribution evidence remain externally unresolved. The generated report is reproducible but is not an active asset store.
Validation: `python -m pytest tests/test_provenance_inventory.py -q` -> 3 passed; inventory smoke report -> version 1.0.0, 189 artifacts, status `not-ready`; `python planning/check_contracts.py` -> planning contracts OK; `git diff --check` -> clean apart from Git LF/CRLF warnings.
