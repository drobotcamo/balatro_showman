# Run-bundle storage

Issue #44 stores each operational bundle in SQLite using SQLAlchemy 2.x. Alembic
owns schema creation and upgrades: `alembic upgrade head` (set
`sqlalchemy.url` to the bundle URL) is the production setup command. SQLite
transactions are short and atomic; one writer is expected, while readers may
use SQLite's normal snapshot/read isolation. Evidence records are canonical
JSON UTF-8 bytes, or unmodified raw bytes, hashed with SHA-256. Final outcomes
reject further evidence writes; validation reports and persists integrity
failures without rewriting payloads.

`python -m run_bundle import-oracle` copies one file-IPC `session.json` and
`steps.ndjson` run into the database in one transaction. It stores canonical
step JSON as records and retains source-file SHA-256 values, usage metadata,
and recording metadata as provenance. Import never modifies the source run;
the original files remain the byte-level evidence. See
`planning/RUN_BUNDLE_OPERATIONS.md` for the command and inspection sequence.

The permitted lifecycle graph is: `active` may become `interrupted`,
`completed`, `won`, `lost`, `aborted`, or `endless`; `interrupted` may resume
to `active` or take any terminal outcome. Terminal outcomes, including the
distinct `endless` outcome, cannot transition or accept evidence.
