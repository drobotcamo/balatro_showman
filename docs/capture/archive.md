# Recording archive and catalog

The operational home for this machine is
`F:\OBS_RECORDINGS\showman-archive`. The catalog is `catalog.sqlite` (Alembic
revision `0007_archive_path_aliases`); it holds run records and location metadata,
not video bytes. `captures/<producer-run-id>/` contains byte-preserved capture
files. `videos/` holds checked copies of already confirmed historical originals
and is the destination for future OBS originals after a separately verified OBS
configuration change. `reviews/` holds viewer derivatives
and unscored notes. The recording's original filename is retained; a run ID is
not a video ID and several segments can belong to one video.

Set `SHOWMAN_ARCHIVE_ROOT` to the absolute archive root or pass `--root` to each
archive command. The tools do **not** silently default to the machine-specific
F-drive path: without `--root` or `SHOWMAN_ARCHIVE_ROOT`, archive commands fail
with a diagnostic. On this machine, set the variable once per PowerShell session
to use the designated catalog. `archive init` alone creates a new archive;
inspection does not create or migrate a SQLite file. The archive directory must
not exist before initialization. On this machine it already exists; **do not run
init again**. Schema upgrades are explicit `showman archive upgrade` operations
on the existing catalog, never a side effect of reading or ingesting.

```powershell
$env:SHOWMAN_ARCHIVE_ROOT = 'F:\OBS_RECORDINGS\showman-archive'
py -3 -m showman archive list
py -3 -m showman inspect summary --db "$env:SHOWMAN_ARCHIVE_ROOT\catalog.sqlite" --run 658987181400-2294
py -3 -m showman archive verify --legacy-db "$env:SHOWMAN_ARCHIVE_ROOT\legacy-databases\run_bundle_issue79.sqlite" --legacy-db "$env:SHOWMAN_ARCHIVE_ROOT\legacy-databases\issue123_dagger_reference.sqlite"
py -3 -m showman archive review --run 658987181400-2294 --open
```

`archive review` resolves a **confirmed** video reference and the staged source
from the catalog, then starts the existing local QA viewer. For multiple
confirmed segments of one video, repeat `--run` in the operator-verified order
and include all confirmed catalog segments. An unconfirmed video is never guessed
from timestamps or names. The viewer's explicit `--video`/`--run` interface
remains available for diagnostic, unassociated, or shared-marker reviews; any
`--recording-start-ns` override requires `--timing-evidence`. This is debugging,
not independent visual QA or scored annotation.

## Names and locations

| Type | Prospective location and name | Evidence rule |
| --- | --- | --- |
| Operational database | `showman-archive/catalog.sqlite` | One default catalog, schema migration tracked by Alembic. Do not put it under the recorder's capture directory. |
| Capture segment | `showman-archive/captures/<producer-run-id>/session.json`, `steps.ndjson`, optional `mechanics_reference.ndjson` and diagnostics | Preserve raw bytes and original producer ID. The directory name is a locator, not a whole-play ID. |
| Video | `showman-archive/videos/<OBS-generated-filename>.mkv` or `videos/unlinked/` | Confirmed and unlinked files stay separate. Retain the native filename and identify relationships only by confirmed association/hash, not by run ID. |
| QA derivative | `showman-archive/reviews/<review-id>/` | Keep hash-linked source references and unscored status. |
| Original capture files | `showman-archive/source-originals/<old-root>/` | Retained unchanged. Hidden symbolic links at old absolute paths preserve references. |
| Previous bundles | `showman-archive/legacy-databases/` | Retained as historical stores. `catalog.sqlite` is the operational catalog. |
| Evaluation artifacts | `showman-archive/evaluations/` | Original files retained with hidden links at old root paths. |
| Recorder logs and miscellaneous | `showman-archive/logs/`, `showman-archive/misc/` | Grouped by type; hidden compatibility links preserve old paths. |

`archive media-inventory` lists root-level MKVs and archive state.
`archive stage-media` copies and hashes media into `videos/` for already
confirmed associations, or `videos/unlinked/` otherwise. It never infers a run
pairing or rewrites references. It skips recent files by default; repeat
`--only <basename>` to limit a pass. `archive verify-media` reconciles
registered copies with their source locations.

The physical cutover is complete. `archive relocate-root` printed a dry-run
plan; `--apply` then moved **101 root entries** to the categories above and left
hidden symbolic links at their old absolute paths. A normal Explorer listing of
`F:\OBS_RECORDINGS` now shows only `showman-archive`; the links remain accessible
for existing scripts and manifests. `archive verify-relocation` checks link
targets and recorded tree hashes. It refuses detected game/OBS/recorder/viewer
processes and pending IPC files; the 211 unfinished segment is copied to
`captures/` for recovery, not assigned a fabricated outcome.

The old date-prefixed capture folders are staged under their actual `run_id`
without editing their `session.json`; their original path is retained in
`archive_entries.original_path`. `archive_entries.capture_path` points at the
staged copy. Each file is checked by SHA-256 after copying. `source.identity`
still hashes the session, steps and optional mechanics sidecar. Other files in
the capture directory (for example `NOTE.txt`) are copied and verified too.

## Capture going forward

Do not retarget a running recorder or OBS process. Read the
[capture guide's new-session recipe](README.md#record-a-new-session) and the
[staged live preflight](../../planning/RUN_BUNDLE_OPERATIONS.md#existing-evidence-and-capture-preflight).
Once the operator has stopped recording and the producer terminal watermark
has drained, verify the intended IPC path and only one recorder, the
installed/loaded Lua build and source hash, OBS script/FPS/destination and the
existing queue. Then use the capture README's PowerShell recorder command,
which pairs this archive's `captures` directory with its `catalog.sqlite`.

Terminal imports into this path automatically register their locations in the
catalog. An active session remains on disk before it is imported. Failed intake
remains pending for retry; never treat a directory as a successfully stored run
without `archive list` and `inspect validate`. OBS destination remains its
existing path until verified and changed at a separate idle checkpoint. OBS
recordings made elsewhere can still be associated by the existing explicit
human-confirmed flow. Refresh catalog locations with `archive sync-associations`
after association. The archive must not be under the repository or `%TEMP%`.

With `SHOWMAN_ARCHIVE_ROOT` configured, `showman record` defaults to
`<root>/captures` and `<root>/catalog.sqlite`, and imports each completed
terminal session automatically. A custom `--out-dir` requires an explicit
`--bundle-db`; this prevents imports from becoming undiscoverable outside the
archive's capture tree. Without the environment variable, supply both explicit
paths. A diagnostic capture that must not enter SQLite requires the explicit
`--no-import --out-dir <new-dir>` option. The lower-level bridge entrypoint
retains its optional bundle behavior, but the documented product command fails
closed rather than silently capturing without catalog intake. After a
terminal run, confirm it appears in `archive list` and passes strict
`showman inspect validate`.

## Media staging and path cutover

`archive media-inventory` is read-only. `archive stage-media` copies stable
top-level MKVs into the archive, hashes the copy, and records location metadata;
already confirmed files go under `videos/`, while unlinked files go under
`videos/unlinked/`. Names, timestamps, and file age never create associations.
The age threshold is only a precaution: it cannot prove that OBS has closed a
file. Exclude known active recordings or select explicit basenames with
`--only`. Original files remain untouched by staging.

`archive relocate-root --recordings-root <F-drive-root>` prints a dry-run plan;
`--apply` runs only after the recorder, viewers, game and OBS are stopped and
IPC is drained. It moves classified entries into the archive and creates hidden
symbolic links at their old absolute paths. That keeps old manifests, issue
notes and scripts usable while normal Explorer browsing sees one top-level
`showman-archive` directory. The operation refuses active processes, pending
IPC, unknown root entries, unverified video copies, conflicting destinations
and changed source bytes. A durable plan allows interrupted moves to resume;
`archive verify-relocation` checks all 101 current compatibility links and
their moved content. This machine's cutover completed on 2026-10-10. Do not
manually remove the hidden compatibility links; old absolute references rely
on them.

`capture_build` in newly created `session.json` records the installed Lua
SHA-256 and the bridge/producer Git commit **only when the bytes match that
commit's clean checkout** (allowing Git's Windows line-ending filter). A
missing, modified or inaccessible installed
producer yields null/unknown revision, not a guessed commit. This is distinct
from the session/IPC/mechanics protocol versions and the catalog schema version.
Installed-file identity does not itself establish which Lua bytes a game process
loaded earlier; verify the loaded build in the current Lovely log during the
normal capture preflight. The bridge commit identifies the clean checked-in
Python recorder file at new-session creation, not an arbitrary running server.
Older sessions have no capture-time commit; leave it unknown even when an old
build label or approximate date is available.

## Historical staging and verification

Issue #153's approved historical baseline is exactly the seven roots reported
by `archive inventory`: **28** sessions and 3,800 *declared* steps. After that
baseline, four terminal Issue #82 sessions were audited and ingested:
`894135760800-6346` (77 steps), `360895785900-4129` (29), `1821708101000-7354`
(71), and `550271964300-8956` (363). `2110871066199-6186` is unfinished and is
preserved under `captures/` for recovery but is not yet cataloged; no outcome
was invented. None of those runs has a confirmed video association. For a new
archive, use:

```powershell
py -3 -m showman archive inventory --recordings-root 'F:\OBS_RECORDINGS'
py -3 -m showman archive init --root '<new-archive-root>'
py -3 -m showman archive ingest --root '<new-archive-root>' --source '<original-capture-directory>'
py -3 -m showman archive sync-associations --root '<new-archive-root>' --legacy-db '<existing-bundle.sqlite>'
py -3 -m showman archive verify --root '<new-archive-root>' --legacy-db '<existing-bundle.sqlite>'
```

Repeat `ingest` for each explicitly inventoried source. It stages files and
imports from the staged directory without mutating the original. Same bytes and
source path are idempotent; a changed source or destination is a conflict.
`sync-associations` imports **only already human-confirmed** video metadata
whose run/source identity matches; it does not establish new associations or
align frames. It records a SHA-256 of the existing confirmed video. `verify`
checks original/staged members, confirmed video bytes, and record integrity and
compares overlapping runs' status, count and aggregate hash with supplied old
bundles. Run capture audits separately for field/conformance claims. SQLite hash
validation does not prove complete gameplay, video identity or rendered frames.

The original catalog verification returned 28 baseline runs and exact overlaps
of 5 and 4 with the legacy databases. Four post-baseline terminal sessions bring
the catalog to **32 runs and 4,340 declared steps**. The unfinished 112-step
`2110871066199-6186` is retained on disk for recovery and is not added as a run
row. The legacy overlap remains 5 and 4, with no source or stored-integrity
failures. Five confirmed recording references remain addressable through the
catalog. The 60 old root MKV names are hidden compatibility links to files
physically under `videos/`: five already-confirmed videos and 55 explicitly
unlinked items. The four derived QA MKVs are under
`reviews/qa_debug/.media/`. Evaluation files and database records retain their
original bytes and metadata; old absolute paths resolve through hidden
compatibility links. The one operative database is `catalog.sqlite`; the two
old database files remain grouped under `legacy-databases/` as historic copies.
