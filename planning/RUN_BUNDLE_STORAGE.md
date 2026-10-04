# Run-bundle storage

Issue #44 stores each operational bundle in SQLite using SQLAlchemy 2.x. Alembic
owns schema creation and upgrades: `alembic upgrade head` (set
`sqlalchemy.url` to the bundle URL) is the production setup command. SQLite
transactions are short and atomic; one writer is expected, while readers may
use SQLite's normal snapshot/read isolation. Evidence records are canonical
JSON UTF-8 bytes, or unmodified raw bytes, hashed with SHA-256. Final outcomes
reject further evidence writes; validation reports and persists integrity
failures without rewriting payloads.

`RunBundle.ingest_run(envelope, records)` is the source-neutral intake API. An
envelope supplies run identity, source type and identity, producer version,
lifecycle/outcome and provenance; ordered typed records carry their source-
specific payloads. Source adapters own validation and call this API. The
file-IPC oracle adapter is `RunBundle.import_oracle_directory`; it stores
canonical step JSON and retains SHA-256 values for `session.json` and
`steps.ndjson`, usage metadata and recording metadata as provenance. When
`mechanics_reference.ndjson` exists, its SHA-256 is also part of source identity
and provenance; its typed records remain distinct from step evidence. Repeating
an import with the same run ID and source identity is a no-op success; a
different source identity under that run ID is a conflict. Import never
modifies source evidence. See `planning/RUN_BUNDLE_OPERATIONS.md` for automatic
intake and recovery.

The intake API requires terminal lifecycle statuses to carry their matching
outcome. An `incomplete` run must carry no outcome; `active` and `interrupted`
runs may carry only a missing or explicitly unknown outcome.

The permitted lifecycle graph is: `active` may become `interrupted`,
`incomplete`, `completed`, `won`, `lost`, `aborted`, or `endless`; `interrupted`
may resume to `active` or take a terminal outcome. `incomplete` means capture
was explicitly ended without a producer terminal outcome; it is distinct from
`interrupted`, which remains recoverable/resumable. Terminal outcomes, including
`incomplete` and the distinct `endless` outcome, cannot transition or accept
evidence. A process crash leaves the durable source recoverable as active; it
does not invent an incomplete outcome.
