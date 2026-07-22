"""Furniture Bill of Materials request and response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FurnitureMaterialCreate(BaseModel):
    furniture_type_id: int
    material_id: int
    quantity_required: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    wastage_percentage: Decimal = Field(
        default=Decimal("0.00"), ge=0, le=100, max_digits=5, decimal_places=2
    )
    notes: str | None = None


class FurnitureMaterialUpdate(BaseModel):
    furniture_type_id: int | None = None
    material_id: int | None = None
    quantity_required: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=3
    )
    wastage_percentage: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    notes: str | None = None


class FurnitureMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    furniture_type_id: int
    furniture_type_name: str
    material_id: int
    material_name: str
    quantity_required: Decimal
    wastage_percentage: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime
