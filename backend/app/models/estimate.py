"""Estimate ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .furniture_type import FurnitureType
    from .quotation import Quotation
    from .user import User


class Estimate(Base):
    """Furniture estimate request and optional AI recognition result."""

    __tablename__ = "estimates"
    __table_args__ = (
        CheckConstraint(
            "input_method IN ('predefined', 'image_upload')",
            name="ck_estimates_input_method",
        ),
        CheckConstraint(
            "status IN ('draft', 'processing', 'processed', 'quoted')",
            name="ck_estimates_status",
        ),
        CheckConstraint(
            "recognition_confidence IS NULL OR "
            "recognition_confidence BETWEEN 0 AND 1",
            name="ck_estimates_recognition_confidence",
        ),
        CheckConstraint(
            "(recognized_furniture_type_id IS NULL AND "
            "recognition_confidence IS NULL) OR "
            "(recognized_furniture_type_id IS NOT NULL AND "
            "recognition_confidence IS NOT NULL)",
            name="ck_estimates_recognition_pair",
        ),
        CheckConstraint(
            "input_method <> 'image_upload' OR image_path IS NOT NULL",
            name="ck_estimates_image_upload_path",
        ),
        CheckConstraint(
            "status IN ('draft', 'processing') OR "
            "selected_furniture_type_id IS NOT NULL",
            name="ck_estimates_selected_type_for_completed_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    selected_furniture_type_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("furniture_types.id"), nullable=True
    )
    recognized_furniture_type_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("furniture_types.id"), nullable=True
    )
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    input_method: Mapped[str] = mapped_column(String(20), nullable=False)
    recognition_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="estimates")
    selected_furniture_type: Mapped[FurnitureType | None] = relationship(
        back_populates="selected_estimates",
        foreign_keys=[selected_furniture_type_id],
    )
    recognized_furniture_type: Mapped[FurnitureType | None] = relationship(
        back_populates="recognized_estimates",
        foreign_keys=[recognized_furniture_type_id],
    )
    quotations: Mapped[list[Quotation]] = relationship(back_populates="estimate")
