"""Inventory ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .material import Material


class Inventory(Base):
    """Current inventory quantities for one material."""

    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint(
            "quantity_available >= 0", name="ck_inventory_quantity_available"
        ),
        CheckConstraint("reorder_level >= 0", name="ck_inventory_reorder_level"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    material_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("materials.id"), nullable=False, unique=True
    )
    quantity_available: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0.000"), server_default="0.000"
    )
    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0.000"), server_default="0.000"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    material: Mapped[Material] = relationship(back_populates="inventory")
