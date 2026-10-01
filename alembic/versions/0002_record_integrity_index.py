from alembic import op
import sqlalchemy as sa

revision = "0002_record_integrity_index"
down_revision = "0001_run_bundle"

def upgrade():
    op.create_index("ix_records_run_sequence", "records", ["run_id", "sequence"])

def downgrade():
    op.drop_index("ix_records_run_sequence", table_name="records")
