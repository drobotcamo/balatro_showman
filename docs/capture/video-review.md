# Video and action review

This local browser tool displays a large video on the left and original oracle
actions on the right. It is debugging QA, not an annotation/evaluation exporter.
Inputs are an existing video path and ordered capture directories for that video.
Source files remain unchanged. Generated browser media and exports stay external.

For a run with an **already confirmed** video association in the operational
catalog, start with `python -m showman archive list` followed by
`python -m showman archive review --run <run-id> --open` (set
`SHOWMAN_ARCHIVE_ROOT` first). Repeat `--run` in reviewed source order when
multiple confirmed segments share the video. [Archive layout and limitations](archive.md)
explain when the explicit paths below are still required. A marker, nearby
timestamp or matching filename never creates an association.

The example below is a **historical, explicitly grouped** Issue #115 video
whose two source segments are not both confirmed catalog associations. Their
original paths remain valid but are not new output destinations. Use this
diagnostic route rather than guessing the second segment's association. From
the repository root, with Python 3.11+ and existing `ffmpeg` / `ffprobe` on
PATH, quote paths with spaces:

```powershell
py -3 -m ground_truth.qa_viewer `
  --video "F:\OBS_RECORDINGS\2026-10-03 17-56-28.mkv" `
  --run "F:\OBS_RECORDINGS\oracle_runs_issue79\1898258342000-5384" `
  --run "F:\OBS_RECORDINGS\oracle_runs_issue79\2317688862100-2663" `
  --recording-start-ns 1895948216800 `
  --timing-evidence "User-confirmed shared recording/play in issue 115; diagnostic timing only" `
  --export-root "F:\OBS_RECORDINGS\showman-archive\reviews" --seed "issue118-review-v1" --open
```

For other recordings, supply their own paths and timing evidence. With one source
and a valid original recording marker, omit the override/evidence flags. A missing
marker remains visible and disables seeking/clip export unless an explicit
diagnostic timing basis is supplied. This operation does not associate a recording
in the Run Store and does not replace the required human-confirmed checkpoint.

The server binds only to localhost and prints its URL. Eligibility frame mapping
currently supports H.264 constant-cadence video. It checks video-packet
presentation timestamps for monotonicity and cadence, then creates a video-only
MP4 remux under `<export-root>/.media` and verifies one-to-one packet count and
timestamps before enabling frame review. Packet inspection avoids decoding every
frame during startup; large media remuxing can still take time. Original MKVs
are retained. Other codecs and variable-cadence video are rejected for this
review mode rather than assigned guessed frame indices.
Subsequent launches reuse the derivative only after checking its stored hashes.
Incomplete or changed cache entries are preserved and rejected rather than overwritten.
Stop with Ctrl+C when finished. The viewer does not start/stop OBS or Balatro.

## Controls

- **Steps** defaults to 10, accepts 1–200, and changes the current window size.
- **Start random session** starts a new random review window, not a new game.
  Eligible source-local starts are sampled uniformly. Seed, draw ordinal and
  actual selection are retained. Short sources yield a partial window.
- **Next window** advances immediately after the displayed steps. It never
  silently wraps. At a fragment boundary the button names the next original
  source ID; clicking explicitly continues into that source at its first step.
- The source selector begins a source at step one. Ordered source directories
  are caller-supplied video membership, not inferred from filenames or state.
- Clicking an action seeks to its candidate timestamp. **Play this segment**
  includes 0.75-second preroll and following-action context plus 0.75-second
  postroll, clamped to the recording. Context is not another selected step.
- The notes field records your observations separately from engine snapshots.

State is captured before callbacks resolve. An unresolved target stays unresolved;
Buy & Use may generate internal callbacks, so a source step is not always a
distinct player click. Timing remains **unverified** even when a marker exists.
This tool cannot establish independent rendered correspondence within ±3 frames.

## Export

**Export debug folder** creates a fresh timestamped folder under the external
export root containing:

- `clip.mp4`: a video-only, re-encoded debugging clip; requested interval and
  measured output metadata are recorded. It is not certified frame-exact evidence.
- `actions.ndjson`: byte-preserved original selected source lines, with no new IDs.
- `notes.txt`: the human notes.
- `manifest.json`: original source/video hashes, timing interpretation and limits,
  source-local selection, seed/draw, clip command/tool version and output hashes.
  Its `oracle-video-qa-debug/1` document is explicitly `unscored` and is distinct
  from evaluation, provenance, and Run Store manifests.
- `index.html`: a standalone browser view of that clip and action window. Open it
  directly from the exported folder; its review controls are disabled.

Input hashes are rechecked before and after extraction. Selected source lines are
frozen from the same bytes as the displayed records. Changed inputs, missing/unordered timing,
overlapping source/output paths, ffmpeg failure and unavailable destinations fail
explicitly. Failed new folders retain `INCOMPLETE.txt`; sources are untouched and
existing output folders are never overwritten. Keep exports out of Git and group
them with their original recording/play for any later split decision.
After restarting the server, reload the browser page to obtain its new session token.

Narrow checks: `py -3 -m unittest tests.test_qa_viewer` and
`py -3 planning/check_contracts.py`, followed by browser playback/seek/export QA.
## First-slice eligibility review

Open **Open eligibility review ↗** in the local viewer to review the same video
and action windows in a separate browser tab. Select a step, inspect the
rendered pre-action frame with the frame-step buttons, and record its actual
source-frame index, measured offset from the candidate, evidence, stage, visual
observation, missingness and external source-registry audit status. A confirmed
correspondence requires a measured offset within ±3 frames; otherwise choose
unverified, failed or disputed. Oracle snapshots are navigation aids, not visual
labels. The reviewer field identifies the person who inspected the pixels.

**Save unscored observation** writes a new JSON file under the selected external
export root's `eligibility-reviews` directory. The browser's decoded-frame
callback supplies the presented frame's timestamp; its index is mapped against
source video packet presentation timestamps. The viewer checks that the browser
remux has a one-to-one frame count and matching per-frame timestamps. The server
binds the oracle step to the displayed window and checks frame bounds, timestamp
correspondence, constant-FPS cadence, and candidate/offset agreement. The
callback and reviewer notes are evidence, not a cryptographic attestation of the
display. Saves record source hashes and the
original step identity. They never replace a previous observation, edit source
video/oracle files, certify source overlap, or produce a held-out manifest/score.
For recordings with multiple recorder IDs, pass every associated `--run` for the
same video and count that video only once. Review each stage and record missing
stages explicitly; audit external training and synthetic registries independently.
The frozen rules are in `planning/FIRST_SLICE_PROTOCOL_V2.md`.

### Launching several recordings

For a predeclared group, create one UTF-8 JSON config from
[`issue82-review.example.json`](issue82-review.example.json), replace its
external paths, and run this once:

```powershell
py -3 -m ground_truth.qa_viewer_launch --config "<external-review-config.json>" --open
```

The config file's directory anchors relative paths. Each video needs one object
with a `video`, ordered `runs`, and optional filesystem-safe `export_name`.
Every logical video/play group gets its own child export folder, startup logs,
and locally-bound server URL. Include every resumed/fragment run belonging to a
video in that video's `runs` array; never list the same play as separate sources.
The launcher checks that each URL serves its viewer page and rechecks the child
process before reporting its URL, PID, export directory, and seed. Startup errors
go to per-viewer `.err.txt` files beside
the export root. The browser's **Open eligibility review** link opens the second
tab; `--open` opens the regular viewer page.

Direct single-viewer launch remains available through
`py -3 -m ground_truth.qa_viewer`. Its `--run` can be repeated for all segments
of one video. Do not use `Start-Process -ArgumentList` with a PowerShell array
of space-containing paths: it split the video filename in observed launches.
Use direct PowerShell invocation, or the JSON-config launcher above. If media
preparation fails with a constant-FPS diagnostic, stop and preserve the source;
do not accept average-FPS frame numbers as rendered-frame evidence.

### Launch findings (verified 2026-10-04)

- `Start-Process -ArgumentList @(...)` split `2026-10-03 17-25-24.mkv` at the
  spaces and both viewers exited with `unrecognized arguments: 17-25-24.mkv`.
  A single explicitly quoted argument string launched both successfully.
- The initial browser link opened the same review page with
  `?mode=eligibility`; the tab itself is within that page, not a second browser
  tab. The separate eligibility tab is opened from the live viewer's link.
- Large source files take a few seconds to prepare. The successful starts printed
  localhost URLs, and the two source/run groups loaded with matching video hashes
  and no oracle diagnostics. Exports remained under their separate external
  folders; source videos and run files were unchanged.
- A real independent pilot still needs human frame inspection. Server readiness,
  matching hashes, and successful media playback do not confirm rendered
  correspondence or source-registry eligibility.
- The revised timestamp inventory was run on both candidate recordings: the
  17-25-24 video measured 7,949 frames at 60 FPS over 132.484 seconds; the
  17-56-28 video measured 80,419 frames at 60 FPS over 1,340.317 seconds.
  Both packet timestamp sequences were monotonic and within the viewer's 5%
  constant-cadence tolerance, with presentation origin 0.0. This validates the
  viewer's frame-index mapping basis, not the oracle-to-rendered correspondence.
