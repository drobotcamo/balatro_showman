from alembic import op
import sqlalchemy as sa

revision = "0006_archive_media"
down_revision = "0005_archive_video_hash"


def upgrade():
    op.create_table(
        "archive_media",
        sa.Column("original_path", sa.Text(), primary_key=True),
        sa.Column("archive_path", sa.Text(), nullable=False, unique=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("catalog_status", sa.String(32), nullable=False),
    )


def downgrade():
    op.drop_table("archive_media")
