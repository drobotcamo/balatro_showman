# Video and action review viewer

The local video/action viewer is retained as active project tooling. It is the
repeatable inspection surface for reviewing recorded frames beside oracle
actions and is expected to grow with the capture and QA workflow.

## Scope

- Keep viewer code and its focused tests when capture tooling is reorganized.
- Expand playback, step navigation, and review/export affordances
  incrementally.
- Treat displayed video, actions, and overlays as review inputs, not as proof
  that frame alignment or recording association is correct.

The viewer does not replace the Lua oracle, run-bundle provenance, explicit
alignment metadata, or the approved evaluation protocol. Any future viewer
feature that writes annotations or evidence must define its provenance and
validation contract before it is used for acceptance claims.

See `planning/DECISIONS.md` D031 and the ground-truth component contract.
