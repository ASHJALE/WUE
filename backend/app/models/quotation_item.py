"""Quotation item ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
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
    from .furniture_material import FurnitureMaterial
    from .material import Material
    from .quotation import Quotation


class QuotationItem(Base):
    """Historical material-price snapshot belonging to a quotation."""

    __tablename__ = "quotation_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_quotation_items_quantity"),
        CheckConstraint(
            "unit_price_snapshot >= 0",
            name="ck_quotation_items_unit_price_snapshot",
        ),
        CheckConstraint("line_total >= 0", name="ck_quotation_items_line_total"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quotation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quotations.id"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("materials.id"), nullable=False
    )
    furniture_material_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("furniture_materials.id"), nullable=True
    )
    material_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_snapshot: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_alternative: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    quotation: Mapped[Quotation] = relationship(back_populates="items")
    material: Mapped[Material] = relationship(back_populates="quotation_items")
    furniture_material: Mapped[FurnitureMaterial | None] = relationship(
        back_populates="quotation_items"
    )
