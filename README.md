# Balatro Showman

Turn gameplay footage into inspectable game data.

Balatro Showman is building a video-only reconstruction pipeline for Balatro:
what is on screen, what changes, and which actions a player takes. Engine
records from our own modded games provide a separate reference for measuring
that reconstruction. Trustworthy data comes first; analytics and learning are
downstream uses.

## Available now: Showman Capture

Showman Capture records and inspects the evidence used to validate reconstruction.
It captures supported pre-action game states, stores ordered records and source
provenance, and connects them to separately recorded video and reviewed labels.

```text
Balatro + game bridge -> Recorder -> capture directories -> Run Store (SQLite)
                                                              |
                                                          Inspector
OBS -> video + game-clock marker -> candidate frame alignment -> human frame QA
                                                                  |
                                                        evaluation manifest
```

The Recorder can import terminal captures into the Run Store automatically.
Video remains external. Recording association is a separate human-confirmed
operation; successful storage does not imply a confirmed video or alignment.
The designated F-drive operational catalog is
`F:\OBS_RECORDINGS\showman-archive\catalog.sqlite`; archived capture files
live under `captures/`, and checked copies of confirmed videos under `videos/`.
Use [archive layout and migration rules](docs/capture/archive.md) for paths;
an active recorder/OBS must not be redirected by following an example.

### Start here

Run commands from the repository root with Python 3.11 or newer and the
SQLAlchemy/Alembic dependencies in `pyproject.toml`. Use `py -3` instead of
`python` on Windows if needed. No editable install or console-script setup is
required for this module entrypoint.

```powershell
py -3 -m showman --help
$demo = Join-Path $env:TEMP ("showman-demo-" + [guid]::NewGuid().ToString("N"))
py -3 -m showman demo --output-dir "$demo"
```

Choose a **new** output directory under an existing parent, outside Git. The
agent guide includes separate [PowerShell and Git Bash examples](docs/capture/README.md#try-the-complete-storage-path-without-a-game).
Do not use the existing project/worktree folder as `--output-dir`. The
demo sends two synthetic actions through the real queue consumer and automatic
SQLite import, validates the stored records, and prints the next inspection
command. It needs neither Balatro nor OBS. Synthetic evidence is labeled and
has no video association; it is an onboarding check, not game-quality evidence.

| Task | Surface |
| --- | --- |
| Discover cataloged runs and confirmed videos | `python -m showman archive list` (set `SHOWMAN_ARCHIVE_ROOT`) |
| Record supported game actions | `python -m showman record` |
| Initialize a database or import a capture | `python -m showman store` |
| Read stored runs, steps, hashes, and provenance | `python -m showman inspect` |
| Read or audit a capture directory | `python -m showman capture` |
| Compute candidate video frame indices | `python -m showman align` |
| Confirm a recording association | `python -m showman associate` |
| Export reviewed development annotations | `python -m showman annotations export` |

## Documentation

- [Agent start and task guide](docs/capture/README.md): first successful use,
  capture-to-inspection workflow, and failure handling.
- [Archive layout](docs/capture/archive.md): configured catalog, capture and
  video naming, verified staging and future recording destination.
- [Vocabulary](docs/capture/vocabulary.md): what runs, recordings, steps,
  bundles, alignment, and manifests mean.
- [CLI and Python API reference](docs/capture/reference.md): arguments,
  outputs, mutation boundaries, and existing module equivalents.
- [Planning index](planning/README.md): contracts, roadmap, runtime records,
  and evaluation protocols.

## Development status

Phase 0 is `building`. Recording/storage/inspection are implemented; #81
delivered a user-confirmed recorded run with representative rendered-frame
checks. #79 delivered a reviewed development pilot and frozen prospective
first-slice criteria. The annotation exporter is development-only and unscored.
The development samples have no reconstruction predictions; reviewed frame
mappings do not establish broad alignment. Video-only reconstruction accuracy,
held-out results, and
broad Phase 0 acceptance are not established.

The current producer covers selected actions and fields. Missing identities,
unresolved actions, coarse legal-action lists, defaults, and timing ambiguity
remain visible limitations. `inspect transitions` and `inspect diff` currently
return `unsupported`. See the task guide before using captures as evaluation
references.
