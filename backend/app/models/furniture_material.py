"""Furniture Bill of Materials ORM model."""

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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .furniture_type import FurnitureType
    from .material import Material
    from .quotation_item import QuotationItem


class FurnitureMaterial(Base):
    """Standard material and quantity required by a furniture type."""

    __tablename__ = "furniture_materials"
    __table_args__ = (
        UniqueConstraint(
            "furniture_type_id",
            "material_id",
            name="uq_furniture_materials_type_material",
        ),
        CheckConstraint(
            "quantity_required > 0", name="ck_furniture_materials_quantity"
        ),
        CheckConstraint(
            "wastage_percentage BETWEEN 0 AND 100",
            name="ck_furniture_materials_wastage",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    furniture_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("furniture_types.id"), nullable=False
    )
    material_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("materials.id"), nullable=False
    )
    quantity_required: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False
    )
    wastage_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"), server_default="0.00"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    furniture_type: Mapped[FurnitureType] = relationship(
        back_populates="furniture_materials"
    )
    material: Mapped[Material] = relationship(back_populates="furniture_materials")
    quotation_items: Mapped[list[QuotationItem]] = relationship(
        back_populates="furniture_material"
    )
