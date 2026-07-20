"""Material ORM model."""

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
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .furniture_material import FurnitureMaterial
    from .inventory import Inventory
    from .quotation_item import QuotationItem


class Material(Base):
    """Material catalog entry with its current price and one direct alternative."""

    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint(
            "current_unit_price >= 0", name="ck_materials_current_unit_price"
        ),
        CheckConstraint(
            "alternative_material_id IS NULL OR alternative_material_id <> id",
            name="ck_materials_not_own_alternative",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    current_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    alternative_material_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("materials.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
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

    alternative_material: Mapped[Material | None] = relationship(
        remote_side="Material.id",
        foreign_keys=[alternative_material_id],
        back_populates="alternative_for",
    )
    alternative_for: Mapped[list[Material]] = relationship(
        foreign_keys="Material.alternative_material_id",
        back_populates="alternative_material",
    )
    furniture_materials: Mapped[list[FurnitureMaterial]] = relationship(
        back_populates="material"
    )
    inventory: Mapped[Inventory | None] = relationship(
        back_populates="material", uselist=False
    )
    quotation_items: Mapped[list[QuotationItem]] = relationship(
        back_populates="material"
    )
