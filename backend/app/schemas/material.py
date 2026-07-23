"""Material request and response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MaterialBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    unit: str = Field(min_length=1, max_length=30)
    current_unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    alternative_material_id: int | None = None
    is_active: bool = True

    @field_validator("name", "unit")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    current_unit_price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    alternative_material_id: int | None = None
    is_active: bool | None = None

    @field_validator("name", "unit")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value


class MaterialRead(MaterialBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


FurnitureRecommendationType = Literal["chair", "bed", "sofa", "dining_table", "lamp_shade"]


class MaterialRecommendRequest(BaseModel):
    furniture_type: FurnitureRecommendationType


class MaterialRecommendation(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    priority: Literal["Primary", "Alternative"]
    quality: Literal["Economy", "Standard", "Premium"]
    reason: str = Field(min_length=1)


class MaterialRecommendResponse(BaseModel):
    furniture_type: FurnitureRecommendationType
    display_name: str
    materials: list[MaterialRecommendation]
    status: Literal["recommended"] = "recommended"
