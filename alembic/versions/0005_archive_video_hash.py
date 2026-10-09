from alembic import op
import sqlalchemy as sa

revision = "0005_archive_video_hash"
down_revision = "0004_archive_catalog"


def upgrade():
    op.add_column("archive_entries", sa.Column("video_sha256", sa.String(64)))


def downgrade():
    op.drop_column("archive_entries", "video_sha256")
