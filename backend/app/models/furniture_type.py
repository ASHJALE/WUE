"""Furniture type ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .estimate import Estimate
    from .furniture_material import FurnitureMaterial


class FurnitureType(Base):
    """Predefined furniture category supported by WUE."""

    __tablename__ = "furniture_types"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    furniture_materials: Mapped[list[FurnitureMaterial]] = relationship(
        back_populates="furniture_type"
    )
    selected_estimates: Mapped[list[Estimate]] = relationship(
        back_populates="selected_furniture_type",
        foreign_keys="Estimate.selected_furniture_type_id",
    )
    recognized_estimates: Mapped[list[Estimate]] = relationship(
        back_populates="recognized_furniture_type",
        foreign_keys="Estimate.recognized_furniture_type_id",
    )
