from alembic import op
import sqlalchemy as sa

revision = "0004_archive_catalog"
down_revision = "0003_binary_evidence"


def upgrade():
    op.create_table(
        "archive_entries",
        sa.Column("run_id", sa.String(128), sa.ForeignKey("runs.id"), primary_key=True),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.Column("capture_path", sa.Text(), nullable=False),
        sa.Column("source_identity", sa.Text(), nullable=False),
        sa.Column("capture_revision", sa.String(40)),
        sa.Column("bridge_revision", sa.String(40)),
        sa.Column("producer_sha256", sa.String(64)),
        sa.Column("video_path", sa.Text()),
        sa.Column("video_status", sa.String(16), nullable=False),
    )


def downgrade():
    op.drop_table("archive_entries")
