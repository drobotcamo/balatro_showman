# Run-bundle storage

Issue #44 stores each operational bundle in SQLite using SQLAlchemy 2.x. Alembic
owns schema creation and upgrades: `alembic upgrade head` (set
`sqlalchemy.url` to the bundle URL) is the production setup command. SQLite
transactions are short and atomic; one writer is expected, while readers may
use SQLite's normal snapshot/read isolation. Evidence records are canonical
JSON UTF-8 bytes, or unmodified raw bytes, hashed with SHA-256. Final outcomes
reject further evidence writes; validation reports and persists integrity
failures without rewriting payloads.

The permitted lifecycle graph is: `active` may become `interrupted`,
`completed`, `won`, `lost`, `aborted`, or `endless`; `interrupted` may resume
to `active` or take any terminal outcome. Terminal outcomes, including the
distinct `endless` outcome, cannot transition or accept evidence.
