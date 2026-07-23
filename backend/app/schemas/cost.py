"""Validated request and response contracts for preliminary Phase 7 costing."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.material import FurnitureRecommendationType
from app.schemas.quantity import QuantityUnit

MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


class CostComponentInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    component: str = Field(min_length=1)
    material: str = Field(min_length=1)
    category: str = Field(min_length=1)
    estimated_quantity: Decimal = Field(gt=0)
    unit: QuantityUnit
    calculation_basis: Literal["Template Estimate"]
    confidence: Literal["Preliminary"]

    @field_validator("component", "material", "category")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Component, material, and category values must not be blank.")
        return cleaned


class LaborInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    hours: Decimal = Field(ge=0)
    hourly_rate: Decimal = Field(ge=0)


class CostCalculateRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    furniture_type: FurnitureRecommendationType
    components: list[CostComponentInput] = Field(min_length=1)
    labor: LaborInput
    profit_margin_percent: Decimal = Field(ge=0, le=100)


class CostedComponent(BaseModel):
    component: str
    material: str
    category: str
    estimated_quantity: Decimal = Field(gt=0)
    unit: QuantityUnit
    unit_price: Decimal = Field(ge=0, decimal_places=2)
    subtotal: Decimal = Field(ge=0, decimal_places=2)


class LaborCostRead(BaseModel):
    hours: Decimal = Field(ge=0)
    hourly_rate: Decimal = Field(ge=0, decimal_places=2)
    labor_cost: Decimal = Field(ge=0, decimal_places=2)


class CostCalculateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    furniture_type: FurnitureRecommendationType
    display_name: str
    currency: Literal["PHP"] = "PHP"
    components: list[CostedComponent]
    total_material_cost: Decimal = Field(ge=0, decimal_places=2)
    labor: LaborCostRead
    profit_margin_percent: Decimal = Field(ge=0, le=100)
    profit_amount: Decimal = Field(ge=0, decimal_places=2)
    final_estimated_cost: Decimal = Field(ge=0, decimal_places=2)
    pricing_status: Literal["preliminary"] = "preliminary"
    status: Literal["calculated"] = "calculated"

    @model_validator(mode="after")
    def validate_documented_totals(self):
        material_total = money(sum((item.subtotal for item in self.components), Decimal("0")))
        labor_total = money(self.labor.hours * self.labor.hourly_rate)
        profit = money(
            (material_total + labor_total) * self.profit_margin_percent / Decimal("100")
        )
        final_total = money(material_total + labor_total + profit)
        if self.total_material_cost != material_total:
            raise ValueError("Material total does not equal component subtotals.")
        if self.labor.labor_cost != labor_total:
            raise ValueError("Labor cost does not equal hours multiplied by hourly rate.")
        if self.profit_amount != profit:
            raise ValueError("Profit amount does not match the documented formula.")
        if self.final_estimated_cost != final_total:
            raise ValueError("Final estimated cost does not match material, labor, and profit totals.")
        return self
