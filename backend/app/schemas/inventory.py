"""Inventory request and response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InventoryCreate(BaseModel):
    material_id: int
    quantity_available: Decimal = Field(
        default=Decimal("0.000"), ge=0, max_digits=12, decimal_places=3
    )
    reorder_level: Decimal = Field(
        default=Decimal("0.000"), ge=0, max_digits=12, decimal_places=3
    )


class InventoryUpdate(BaseModel):
    material_id: int | None = None
    quantity_available: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=3
    )
    reorder_level: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=3
    )


class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_id: int
    material_name: str
    quantity_available: Decimal
    reorder_level: Decimal
    updated_at: datetime
