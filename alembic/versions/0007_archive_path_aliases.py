from alembic import op
import sqlalchemy as sa

revision = "0007_archive_path_aliases"
down_revision = "0006_archive_media"


def upgrade():
    op.add_column("archive_entries", sa.Column("current_source_path", sa.Text()))
    op.add_column("archive_media", sa.Column("current_path", sa.Text()))
    op.create_table(
        "archive_aliases",
        sa.Column("original_path", sa.Text(), primary_key=True),
        sa.Column("target_path", sa.Text(), nullable=False, unique=True),
        sa.Column("item_type", sa.String(16), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("archive_aliases")
    op.drop_column("archive_media", "current_path")
    op.drop_column("archive_entries", "current_source_path")
