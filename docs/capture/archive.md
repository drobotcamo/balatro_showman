# Recording archive and catalog

The operational home for this machine is
`F:\OBS_RECORDINGS\showman-archive`. The catalog is `catalog.sqlite` (Alembic
revision `0006_archive_media`); it holds run records and location metadata,
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
py -3 -m showman archive verify --legacy-db 'F:\OBS_RECORDINGS\run_bundle_issue79.sqlite' --legacy-db 'F:\OBS_RECORDINGS\issue123_dagger_reference.sqlite'
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
| Video | `showman-archive/videos/<OBS-generated-filename>.mkv` | Historical members are checked copies of confirmed originals; future members may be new OBS originals after a separately verified settings change. Retain the native filename and track identity by confirmation and hash, not by run ID. |
| QA derivative | `showman-archive/reviews/<review-id>/` | Keep hash-linked source references and unscored status. |
| Older bundles/sources | Their existing paths under `F:\OBS_RECORDINGS` | Keep while their absolute links and active users exist. No inferred rename or deletion. |

`archive media-inventory` lists root-level MKVs and archive state.
`archive stage-media` copies and hashes media into `videos/` for already
confirmed associations, or `videos/unlinked/` otherwise. It never infers a run
pairing, rewrites references or removes the original. It skips recent files by
default; repeat `--only <basename>` to limit a pass. `archive verify-media`
reconciles registered copies against their originals. These commands prepare
and organize media without performing a source-path cutover.

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

`archive relocate-root --recordings-root <F-drive-root>` prints a dry-run plan.
The separate `--apply` operation moves classified entries under the archive and
leaves compatibility links at their old absolute paths. It refuses detected
game/OBS/recorder/viewer processes, pending IPC files, unknown root entries,
unverified media copies, conflicting destinations and changed bytes. A durable
plan allows verified interrupted moves to resume; `archive verify-relocation`
checks links and moved bytes. This operation is **not** needed for recording or
catalog discovery, and must not be run until every path consumer is stopped,
external references are inventoried, and the owner authorizes that cutover. A
symlink permission or filesystem failure aborts; it is not permission to bypass
the cutover check. If a retry is recovering a move already made, the verified
archive target remains intact and the old alias may be temporarily absent. Fix
the link-permission/filesystem issue and rerun the same command to finish from
the checksummed plan; do not manually move or delete either location. The
present live recorder/viewers and absolute evaluation references are why old
paths remain in place.

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
by `archive inventory`: **28** sessions and 3,800 *declared* steps. After its
recorder session finalized, the separate Issue #82 run `894135760800-6346` (77 steps)
was independently audited and staged too. It is an additional catalog run, not
part of the historical baseline or an association confirmation. For a new
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

At the original baseline check, `archive verify` returned 28 runs, 3,800 declared
steps, 5 and 4 exact old-bundle matches, and zero failures. The current catalog
has 29 runs and 3,877 declared steps; the old-bundle overlap remains 5 and 4.
Five confirmed recording references were transferred. A confirmed closed video
can be staged with `py -3 -m showman archive stage-video --run <run-id>`; this hashes the
original and copy, updates only its catalog location and retains its original
association provenance. Old databases and original media remain in their prior
locations; the catalog does not redirect active tools. The five already
confirmed videos were staged under `videos/` with matching hashes and are
addressable by `archive review`. Their original MKVs remain at the root.
The media organization pass cataloged **60 top-level MKVs**: five previously
confirmed originals copied under `videos/`, plus **55 unlinked videos** copied
under `videos/unlinked/`. All 60 root originals remain in place to preserve
historical references. `archive verify-media` returned 60 files and zero
failures. Four derived QA MKVs and other viewer outputs remain grouped beneath
`qa_debug/`; the two live viewers currently read
there. The recorder still owns `oracle_runs_issue82`, and evaluation manifests
retain absolute video paths, including the 2026-10-09 capture. Do not remove
originals or move live capture, QA or referenced paths until all consumers are
stopped and a path-reference cutover is explicitly reviewed. Historical
association/provenance strings must remain preserved; use catalog location
metadata for new lookups.
