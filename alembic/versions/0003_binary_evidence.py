from alembic import op
import sqlalchemy as sa

revision = "0003_binary_evidence"
down_revision = "0002_record_integrity_index"

def upgrade():
    with op.batch_alter_table("records") as batch:
        batch.alter_column("payload", existing_type=sa.Text(), type_=sa.LargeBinary(), existing_nullable=False)

def downgrade():
    with op.batch_alter_table("records") as batch:
        batch.alter_column("payload", existing_type=sa.LargeBinary(), type_=sa.Text(), existing_nullable=False)
