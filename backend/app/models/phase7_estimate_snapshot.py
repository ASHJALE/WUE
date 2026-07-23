"""One-to-one persisted snapshot of a completed Phase 7 workflow."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .estimate import Estimate


class Phase7EstimateSnapshot(Base):
    __tablename__ = "phase7_estimate_snapshots"
    __table_args__ = (
        UniqueConstraint("estimate_id", name="uq_phase7_snapshots_estimate_id"),
        UniqueConstraint("upload_id", name="uq_phase7_snapshots_upload_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    estimate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False
    )
    upload_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    dimensions_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    recommendations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    bom_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    quantities_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    cost_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preliminary_quotation_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    estimate: Mapped[Estimate] = relationship(back_populates="phase7_snapshot")
