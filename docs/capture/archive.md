# Recording archive and catalog

The operational home for this machine is
`F:\OBS_RECORDINGS\showman-archive`. The catalog is `catalog.sqlite` (Alembic
revision `0005_archive_video_hash`); it holds run records and location metadata,
not video bytes. `captures/<producer-run-id>/` contains byte-preserved capture
files. `videos/` holds checked copies of already confirmed historical originals
and is the destination for future OBS originals after a separately verified OBS
configuration change. `reviews/` holds viewer derivatives
and unscored notes. The recording's original filename is retained; a run ID is
not a video ID and several segments can belong to one video.

Set `SHOWMAN_ARCHIVE_ROOT` to the absolute archive root or pass `--root` to each
archive command. An archive is created only with `archive init`; inspection does
not create or migrate a SQLite file. The archive directory must not exist before
initialization. On this machine the archive has already been initialized; **do
not run init again**. Schema upgrades are an explicit `showman archive upgrade`
operation on the existing catalog, never a side effect of reading or ingesting.

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
| Original video | `showman-archive/videos/<OBS-generated-filename>.mkv` | Retain OBS's filename; rely on an explicit recording ID, confirmed association, video hash and/or reviewed grouping rather than renaming by run ID. |
| QA derivative | `showman-archive/reviews/<review-id>/` | Keep hash-linked source references and unscored status. |
| Older bundles/sources | Their existing paths under `F:\OBS_RECORDINGS` | Keep while their absolute links and active users exist. No inferred rename or deletion. |

The old date-prefixed capture folders are staged under their actual `run_id`
without editing their `session.json`; their original path is retained in
`archive_entries.original_path`. `archive_entries.capture_path` points at the
staged copy. Each file is checked by SHA-256 after copying. `source.identity`
still hashes the session, steps and optional mechanics sidecar. Other files in
the capture directory (for example `NOTE.txt`) are copied and verified too.

## Capture going forward

Do not retarget a running recorder or OBS process. Once the operator has stopped
recording and the producer terminal watermark has drained, verify the intended
IPC path and only one recorder, the installed/loaded Lua build and source hash,
OBS script/FPS/destination, and the existing queue as described in
`planning/RUN_BUNDLE_OPERATIONS.md`. With an already migrated catalog, use:

```powershell
py -3 -m showman record --io-dir 'C:\Users\camgr\AppData\Roaming\Balatro\agent_io' --out-dir "$env:SHOWMAN_ARCHIVE_ROOT\captures" --bundle-db "$env:SHOWMAN_ARCHIVE_ROOT\catalog.sqlite"
```

Terminal imports into this path automatically register their locations in the
catalog. An active session remains on disk before it is imported. Failed intake
remains pending for retry; never treat a directory as a successfully stored run
without `archive list` and `inspect validate`. OBS destination remains its
existing path until verified and changed at a separate idle checkpoint. OBS
recordings made elsewhere can still be associated by the existing explicit
human-confirmed flow. Refresh catalog locations with `archive sync-associations`
after association. The archive must not be under the repository or `%TEMP%`.

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

Issue #153's approved baseline is exactly the seven roots in `archive inventory`
and their **28** session files (3,800 *declared* steps). The separate
`oracle_runs_issue82` live root is excluded. Commands for a new archive:

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

As of the staging check, `archive verify` returned 28 runs, 3,800 declared
steps, 5 and 4 exact old-bundle matches, and zero failures. Five confirmed
recording references were transferred. A confirmed closed video can be staged
with `py -3 -m showman archive stage-video --run <run-id>`; this hashes the
original and copy, updates only its catalog location and retains its original
association provenance. Old databases and original media remain in their prior
locations; the catalog does not redirect active tools. The five already
confirmed videos were staged under `videos/` with matching hashes and are
addressable by `archive review`. Their original MKVs remain at the root.
There were 55 top-level MKVs and 3 QA-derived MKVs in the initial media
inventory, not 58 confirmed associations. Do not bulk-pair or relocate those
files while OBS, the recorder and viewers are using the old paths. A future
physical media cutover must inventory embedded paths in evaluation artifacts,
hash each closed original, verify any copied bytes and update *location* only
after the idle/drained checkpoint. Keep historical provenance paths intact.
