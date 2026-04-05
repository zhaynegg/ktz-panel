"""SQLAlchemy models for telemetry storage (PostgreSQL / TimescaleDB)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TelemetryRecord(Base):
    """One telemetry tick — designed for time-series queries."""

    __tablename__ = "telemetry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    locomotive_id: Mapped[str] = mapped_column(String(64), default="loco-1")
    state: Mapped[str] = mapped_column(String(20))

    speed_kmh: Mapped[float] = mapped_column(Float)
    traction_power_kw: Mapped[float] = mapped_column(Float)
    engine_temp_c: Mapped[float] = mapped_column(Float)
    transformer_temp_c: Mapped[float] = mapped_column(Float)
    brake_pipe_pressure_bar: Mapped[float] = mapped_column(Float)
    voltage_v: Mapped[float] = mapped_column(Float)
    current_a: Mapped[float] = mapped_column(Float)
    vibration_mm_s: Mapped[float] = mapped_column(Float)
    fuel_level_pct: Mapped[float] = mapped_column(Float)
    fault_code: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Health index snapshot
    health_index: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_telemetry_loco_ts", "locomotive_id", "ts"),
    )


class AlertRecord(Base):
    """Persisted alert raised by the alert engine."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    locomotive_id: Mapped[str] = mapped_column(String(64), default="loco-1")
    severity: Mapped[str] = mapped_column(String(16))  # critical / warning / info
    code: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("ix_alerts_loco_ts", "locomotive_id", "ts"),
    )
