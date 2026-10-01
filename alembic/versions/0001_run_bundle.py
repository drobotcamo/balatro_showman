from alembic import op
import sqlalchemy as sa
revision = "0001_run_bundle"
down_revision = None
def upgrade():
    op.create_table("runs", sa.Column("id", sa.String(128), primary_key=True), sa.Column("status", sa.String(16), nullable=False), sa.Column("producer_version", sa.String(128), nullable=False), sa.Column("schema_version", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime, nullable=False), sa.Column("finalized_at", sa.DateTime), sa.Column("outcome", sa.String(16)), sa.Column("integrity_status", sa.String(16), nullable=False))
    op.create_table("records", sa.Column("id", sa.Integer, primary_key=True), sa.Column("run_id", sa.String(128), sa.ForeignKey("runs.id"), nullable=False), sa.Column("sequence", sa.Integer, nullable=False), sa.Column("kind", sa.String(32), nullable=False), sa.Column("payload", sa.LargeBinary, nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("integrity_status", sa.String(16), nullable=False), sa.UniqueConstraint("run_id", "sequence", name="uq_record_sequence"))
    op.create_table("provenance", sa.Column("id", sa.Integer, primary_key=True), sa.Column("run_id", sa.String(128), sa.ForeignKey("runs.id"), nullable=False), sa.Column("key", sa.String(128), nullable=False), sa.Column("value", sa.Text, nullable=False))
    op.create_table("integrity", sa.Column("run_id", sa.String(128), sa.ForeignKey("runs.id"), primary_key=True), sa.Column("record_count", sa.Integer, nullable=False), sa.Column("bundle_sha256", sa.String(64), nullable=False), sa.Column("result", sa.String(16), nullable=False))
    op.create_table("schema_versions", sa.Column("version", sa.String(32), primary_key=True), sa.Column("applied_at", sa.DateTime, nullable=False))
    op.execute("INSERT INTO schema_versions(version, applied_at) VALUES ('1.0', CURRENT_TIMESTAMP)")
def downgrade():
    for table in ("schema_versions", "integrity", "provenance", "records", "runs"): op.drop_table(table)
