# Showman Capture: agent start and task guide

Showman Capture records and inspects gameplay evidence for Balatro Showman.
Start with an existing artifact or the synthetic demo. Live capture requires
the game bridge and OBS setup; inspection does not.

## First ten minutes

1. Inspect `git status --short --branch`, worktrees, and the assigned issue.
   Read the applicable checkpoint and component contract before implementation.
   [Agent workflow](../../planning/agent-workflow.md) owns work-item/review rules.
2. Read the [vocabulary](vocabulary.md). Identify whether your input is a video,
   capture directory, SQLite bundle, or annotations document.
3. Select Python 3.11+ in an environment with the declared dependencies.
   Check it with `python --version` and `python -m showman --help`. On this
   Windows machine `py -3` works; the repository `.venv` has historically pointed
   to a missing interpreter. See [Tooling](../../planning/TOOLING.md).
4. Run the demo below, then inspect its first record and provenance. A successful
   demo establishes local capture/storage access, not a working game installation.
5. For real evidence, inspect status and diagnostics before making any claim.
   Read the [API reference](reference.md) for result and exit-code meanings.

If dependencies are absent, create/use your chosen environment and install the
versions declared in `pyproject.toml` (`SQLAlchemy>=2.0,<3`, `alembic>=1.13,<2`).
Tests additionally need pytest. The module CLI is used from the repository root;
this change does not define a distributable wheel or global executable.

## Try the complete storage path without a game

Choose a **new output directory** under an existing external parent, not the
project/worktree folder. Select the example for your terminal: PowerShell and
Bash use different variable syntax. A `bash: syntax error ... '('` from the
PowerShell example means to use the Bash example below.

### PowerShell on Windows

```powershell
$demo = Join-Path $env:TEMP ("showman-demo-" + [guid]::NewGuid().ToString("N"))
py -3 -m showman demo --output-dir "$demo"
py -3 -m showman inspect summary --db "$demo\bundle.sqlite" --run demo-synthetic
py -3 -m showman inspect step --db "$demo\bundle.sqlite" --run demo-synthetic --sequence 0
py -3 -m showman inspect provenance --db "$demo\bundle.sqlite" --run demo-synthetic
py -3 -m showman inspect validate --db "$demo\bundle.sqlite" --run demo-synthetic --strict
```

### Git Bash on Windows

Run from the project/worktree root. This creates a uniquely named sibling
directory outside the repository; `..` must be an appropriate writable parent.

```bash
demo="../showman-demo-$(date +%s)-$RANDOM"
py -3 -m showman demo --output-dir "$demo"
py -3 -m showman inspect summary --db "$demo/bundle.sqlite" --run demo-synthetic
py -3 -m showman inspect step --db "$demo/bundle.sqlite" --run demo-synthetic --sequence 0
py -3 -m showman inspect provenance --db "$demo/bundle.sqlite" --run demo-synthetic
py -3 -m showman inspect validate --db "$demo/bundle.sqlite" --run demo-synthetic --strict
```

On Linux/macOS Bash, use the same syntax with `python` (or `python3`) in place
of `py -3`. Never create the final output directory beforehand: the demo creates
it and refuses to reuse existing directories. If an earlier attempt created
that directory, choose a fresh name rather than pointing the demo at it again.

Expected: two stored records, lifecycle `lost`, and validation `valid` with
no bad sequences. The first payload is explicitly synthetic and records
`SelectBlind`. Generated files stay at your chosen destination. The demo refuses
an existing destination and has no video, recording marker, or reviewed labels.

## Inspect an existing artifact

For a SQLite bundle:

```text
python -m showman inspect list --db <bundle.sqlite>
python -m showman inspect summary --db <bundle.sqlite> --run <run-id>
python -m showman inspect find --db <bundle.sqlite> --run <run-id> --kind step --from 0 --to 4
python -m showman inspect provenance --db <bundle.sqlite> --run <run-id>
python -m showman inspect validate --db <bundle.sqlite> --run <run-id> --strict
```

For a capture directory, without importing it:

```text
python -m showman capture summary <capture-directory>
python -m showman capture audit <capture-directory>
```

`capture summary` returns original source objects, file hashes, and diagnostics.
`capture audit` checks the finalized-run protocol and reports field/conformance
findings separately. It can reject a useful unfinished slice for lacking a full
run outcome. Preserve that limit rather than inventing a terminal outcome.

## Create a store and import an existing capture

```text
python -m showman store init --db <new-bundle.sqlite>
python -m showman store import --db <bundle.sqlite> --source <capture-directory>
python -m showman inspect summary --db <bundle.sqlite> --run <run-id>
```

`store init` requires an existing parent and a new SQLite filename. It runs the
checked-in Alembic migrations, never an implicit upgrade of an existing bundle.
If initialization fails after reserving the filename, preserve/diagnose the
partial file and choose a new destination for a new attempt. Existing-schema
upgrades remain the explicit procedure in
[storage operations](../../planning/RUN_BUNDLE_STORAGE.md).

Import copies records, not media. It preserves source files and retains their
SHA-256 hashes. Same run ID and source identity is a no-op success. Different
source hashes under that ID are a conflict, including a changed active capture;
this is not a synchronization operation. Prefer terminal captures for automatic
intake. See the reference for source-neutral adapter intake.

## Record a new session

Complete the approved runtime/preparation procedure in
[Bridge installation](../../planning/BRIDGE_SPIKE.md#installation-reversible)
and [runtime reference](../../planning/BALATRO_RUNTIME.md). Verify the installed
producer hash, loaded build, runtime/mod configuration, single consumer, IO
directory, destination, and recording settings. Preserve stale queue/marker
evidence rather than deleting it. The producer currently targets the documented
Windows Balatro/Steamodded/Lovely runtime; portable Python inspection does not
establish another game's runtime support.

Initialize the destination bundle once, then start the Recorder:

```text
python -m showman record --io-dir <agent_io> --out-dir <capture-root> --bundle-db <bundle.sqlite>
```

`--bundle-db` is optional. Without it, capture directories are still written.
With it, complete terminal sessions import automatically; there is no per-run
confirmation prompt. An import failure is logged as pending and retried, not
converted into a successful stored run. Verify the database after capture.

Load `ground_truth/obs_recording_start.py` in OBS Tools > Scripts. Use a fully
expanded absolute IO path, the actual recording FPS, and a recording-ID prefix.
OBS fields do not expand `%APPDATA%`. Start recording and verify the handshake
before beginning the approved gameplay sequence. OBS owns video capture; the
Showman CLI does not start/stop OBS or play the game.

After a terminal win/loss and queue drain, inspect/audit the new capture and its
stored run. Ctrl+C cleanly ends open captures as terminal `incomplete` with no
game outcome, except a pending producer watermark remains unresolved. A process
crash leaves active sessions recoverable on restart. Do not use Ctrl+C as a
pause/resume mechanism. `--timeout` and `--once` are diagnostic polling modes;
timeout expiry does not perform Ctrl+C closure.

## Associate a recording, then check alignment

Automatic intake may retain a producer marker as `oracle.recording`. That is
distinct from an explicitly confirmed association under `recording.*` keys.

Select the marker belonging to this run. If it is only embedded in the session,
use a separately retained copy of that `recording` JSON object; do not edit
source evidence or substitute a stale shared-directory marker.

```text
python -m showman associate --db <bundle.sqlite> --run <run-id> --marker <marker.json> --video <video.mkv> --confirmed-by <human-identity>
python -m showman align <capture-directory>/steps.ndjson
```

Association presents the observed run/lifecycle, marker validation, policy, and
present items on stderr. The human must type `confirm`, `decline`, or
`interrupt`. A correction or blank response stops the operation for inspection;
EOF/prompt interruption produces an interrupted result. `--required` maps any
non-confirmation to `blocked`/`recording_required`. There is no bypass flag.

`align` emits zero-based candidate frame indices using the session marker.
Review rendered pre-action frames and page transitions around the candidates;
record the protocol's tolerance, measured uncertainty, failures, and evidence.
Negative indices remain negative and require review. FPS arithmetic does not
establish presentation-time accuracy, variable-frame-rate behavior, or visual
correspondence. Diagnostics-only timestamp/FPS overrides must be reported.

## Export independently reviewed visual annotations

```text
python -m showman annotations export <annotations.json> <external-evaluation.json>
```

The input is caller-authored, independently reviewed pixels-based JSON.
[Annotation specification](../../planning/FIRST_SLICE_ANNOTATION.md) defines
geometry, labels, source hashes, splits, alignment, missingness, and review.
The exporter currently accepts the v1 development input and emits
`development_only_unscored`. Frozen [v2 criteria](../../planning/FIRST_SLICE_PROTOCOL_V2.md)
exist, but this CLI does not add v2 held-out export or scoring. Never relabel
v1 output as a scored v2 artifact. The tool validates metadata; the caller must
actually inspect source files, geometry, grouping, and rendered alignment.

Identical exports are byte-stable. Changed content cannot overwrite an existing
destination. The tool does not extract frames, provide a labeling GUI, or
populate observations from oracle values.

## Diagnose before retrying

| Symptom | Next action |
| --- | --- |
| `storage_not_found` | Correct the filename or explicitly initialize a new store. Inspection must not create it. |
| Missing schema / storage error | Verify the configured bundle and Alembic revision; do not migrate as part of reading. |
| `run_identity_conflict` | Compare source hashes and run IDs; preserve both sources. No overwrite/merge is inferred. |
| Pending import | Inspect recorder diagnostics and destination schema; retry the unchanged import after fixing the cause. |
| Pending end watermark / request gap | Preserve queued files and diagnostics; empty queue is not proof of complete delivery. |
| Quarantined malformed bytes | Retain quarantine files and hashes. Recorder recovery can reconcile its writable capture; read-only inspection never repairs it. |
| Missing/stale marker or disputed association | Reinspect the proposed evidence, then repeat the explicit human checkpoint. |
| Integrity `valid` but unknown fields | Treat byte integrity and field suitability as separate results. |
| `unsupported` transitions/diff | Report unsupported; no delta/event schema is implemented. |

## Checks for changes to these surfaces

```text
python -m pytest -q tests/test_run_bundle_showman_cli.py tests/test_file_ipc_bridge.py tests/test_run_bundle*.py tests/test_recording_association.py tests/test_align_oracle_video.py tests/test_eval_manifest.py
python planning/check_contracts.py
git diff --check
```

Use the narrow relevant subset first. The checks exercise fixture-backed
interfaces; real capture and reconstruction claims require their applicable
oracle/evaluation evidence. Follow the repository review/integration procedure
before publishing a completion claim on the work item.
