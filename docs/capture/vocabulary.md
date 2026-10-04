# Showman Capture vocabulary

Use these names in guides and reports. Existing package names and on-disk
schema identifiers retain their exact meanings.

| Term | Meaning |
| --- | --- |
| Balatro Showman | The project that reconstructs visible game state and actions from video. |
| Showman Capture | Its operational evidence-capture and inspection capability. |
| Game bridge / producer | The Lua mod inside Balatro that publishes engine-reference snapshots before supported action callbacks. |
| Recorder / consumer | The Python process that persists queued snapshots, acknowledges them, recovers durable sessions, and optionally imports terminal captures. |
| Run Store | The persistence surface implemented by `RunBundle`, SQLAlchemy, SQLite, and Alembic. |
| Inspector | The read-only CLI/library surface implemented by `RunBundleInspector`. |
| Producer session / run | A sequence identified by the producer's `run_id`. The storage API calls it a run. It is not necessarily a full human playthrough. |
| Recording | One OBS video capture, identified by a recording marker ID and a separate video-file reference when supplied. It can span multiple producer sessions. |
| Capture directory | One session's `session.json`, `steps.ndjson`, and optional `capture_diagnostics.ndjson`/quarantined bytes. The Recorder writes this before SQLite import. |
| Run bundle / bundle | A versioned SQLite database holding one or more runs, typed evidence records, provenance, and integrity metadata. It does not embed video or decoded frames. |
| Snapshot | The game bridge's engine-reference state immediately before a supported action. This is event-driven, not a sample of every video frame. |
| Step | A persisted snapshot plus its recorded action and consumer persistence timestamp. The following step is not necessarily the immediate result of the previous action. |
| Request ID | A positive, run-scoped producer counter. Use `(run_id, request_id)` for identity; the number alone is not globally unique. |
| Step ID | Producer identity such as `<run_id>:<request_id>`. Preserve the source value. |
| Sequence | The Run Store's zero-based order across imported records. `inspect step --sequence 0` reads the first record; it is not request ID 0 or video frame 0. |
| Queue / file IPC | Immutable request files in `agent_io`. The consumer removes each after durable persistence. An end signal declares the last request ID that must be drained. |
| Recording marker | Recording ID, FPS, and a start timestamp sampled in the producer's clock. It supports candidate alignment; it does not prove that a video exists. |
| Recording association | Additive provenance linking a marker/run and optional video reference after explicit human confirmation. Automatic capture import does not perform this confirmation. |
| Alignment | Mapping a producer step to a video frame. Computed indices are candidates until rendered pre-action correspondence and uncertainty are independently checked. |
| Provenance | Where evidence came from: source identities/hashes, producer/schema versions, runtime, recording references, and confirmation metadata. |
| Integrity | Whether retained record bytes and aggregate metadata agree with their hashes/counts. Integrity does not establish field correctness, complete action coverage, or rendered alignment. |
| Oracle / engine reference | The separate engine-access channel used to evaluate video-only reconstruction. Suitability depends on field, producer revision, and independent checks. |
| Visual annotation | A human observation of recorded pixels, kept separate from oracle values, normalization, and inference. |
| Evaluation manifest | A deterministic document linking reviewed labels, frames, geometry, sources, splits, and alignment evidence. Distinct from a bundle and from an asset-provenance manifest. |
| Slice | A declared supported portion of gameplay and label families, with its own versioned evaluation protocol. |

## Three kinds of status

Keep these separate in reports:

- Run lifecycle: `active`, `interrupted`, `incomplete`, `completed`, `won`,
  `lost`, `aborted`, or `endless`. `incomplete` is terminal capture closure
  without a game outcome; `interrupted` is resumable. A crash leaves the
  durable active session recoverable. Win/loss/endless are distinct meanings.
- Inspection result: `observed`, `derived`, `missing`, `unknown`, or
  `unsupported`. These describe the result, not the run lifecycle.
- Annotation state: `observed`, `unknown`, `missing`, `occluded`, `ambiguous`,
  `unsupported`, or `not_applicable`. An unreviewed family is not an absent
  object or a correct negative example.

The compatibility reader's `video_status=obs` means a marker is present;
`no-video` means no association was supplied. Neither checks the video file.
Association's `marker-associated` also describes provenance, not image validation.

## Three clocks and several versions

Producer `capture_timestamp_ns` and `meta.video_timestamp_ns` use the game
process's monotonic clock. `_recorded_at` and session usage timestamps are UTC
consumer persistence times. The video has its own frame/presentation timeline.
Do not use wall-clock filenames or `_recorded_at` as producer alignment time.

The top-level `producer/1.0.0`, IPC `file-queue/1.0.0`, SQLite schema `1.0`,
annotation/manifest versions, producer build revision, and evaluation protocol
version identify different interfaces. They are not interchangeable. Legacy
`live/2.0.0` and `live/3.0.0` labels remain historical source identifiers.

## Coverage limits worth naming

The producer intentionally coalesces callbacks within 30 ms. A complete queue
drain proves delivery of published requests, not capture of every possible
action. `Game.start_run` may create a new producer session during a continued
playthrough; do not merge those IDs by observed continuity. The Recorder
attaches a recording marker ID to only one session, so later sessions in the
same video do not automatically inherit the marker.

`raw_persistent` contains engine reads. Canonical `persistent_state` is a
future reducer output and remains empty in producer snapshots. Coarse
`legal_actions` are not a complete indexed legality mask.
