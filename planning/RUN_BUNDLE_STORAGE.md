# Run-bundle storage

Issue #44 stores each operational bundle in SQLite using SQLAlchemy 2.x. Alembic
owns schema creation and upgrades: `alembic upgrade head` (set
`sqlalchemy.url` to the bundle URL) is the production setup command. SQLite
transactions are short and atomic; one writer is expected, while readers may
use SQLite's normal snapshot/read isolation. Evidence records are canonical
JSON bytes hashed with SHA-256. Final outcomes reject further evidence writes;
validation reports and persists integrity failures without rewriting payloads.
