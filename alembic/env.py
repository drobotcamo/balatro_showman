from alembic import context
from sqlalchemy import engine_from_config, pool
from run_bundle.models import Base
config = context.config
target_metadata = Base.metadata
def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()
if context.is_offline_mode():
    raise RuntimeError("offline migrations are not supported")
else: run_migrations_online()
