from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass

class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    producer_version: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime)
    outcome: Mapped[str | None] = mapped_column(String(16))
    integrity_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")

class Record(Base):
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    integrity_status: Mapped[str] = mapped_column(String(16), nullable=False, default="valid")
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_record_sequence"),)

class Provenance(Base):
    __tablename__ = "provenance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

class Integrity(Base):
    __tablename__ = "integrity"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)

class SchemaVersion(Base):
    __tablename__ = "schema_versions"
    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
