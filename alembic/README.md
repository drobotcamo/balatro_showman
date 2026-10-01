Run `alembic upgrade head` against a SQLite URL. Production databases are
created and upgraded by Alembic; `RunBundle.create_schema()` exists only for
isolated test fixtures.
