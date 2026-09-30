# Component Contract: Tracking and Cleanup

Status: `planned`

## Purpose

Convert independent detections into temporally consistent object observations,
with a single shared stabilization model for objects and OCR fields.

## Inputs

- Raw detections.
- Page/zone assignment.
- Frame timing and canonical-coordinate metadata.
- Ontology family and movement rules.

## Outputs

- Track IDs, per-frame boxes, confidence history, and lifecycle status.
- Cleaned detection tables.
- Track-quality diagnostics.
- A shared stabilization/age record also consumed by OCR.

## Invariants

- Track IDs are unique within a video and stable through allowed gaps.
- A gap fill is marked as inferred, not observed.
- Parent/attribute tracks remain composable.
- Objects are tracked within their zone; a track does not silently cross
  incompatible zones or pages.

## Acceptance Criteria

- Duplicate boxes are handled deterministically.
- Short detector misses do not fragment ordinary object tracks.
- Fast transitions do not silently interpolate across incompatible objects.
- The OCR/tracking stabilization interface is defined and free of double-carry.
