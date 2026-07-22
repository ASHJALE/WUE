"""Quotation generation request and read schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QuotationStatus = Literal["draft", "issued", "accepted", "rejected", "expired"]


class QuotationGenerate(BaseModel):
    """User-supplied costs; the service rounds monetary values before storage."""

    labor_cost: Decimal = Field(ge=0, max_digits=12)
    logistics_cost: Decimal = Field(ge=0, max_digits=12)
    profit_margin_percentage: Decimal = Field(ge=0, le=100, max_digits=5)


class QuotationItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_id: int
    furniture_material_id: int | None
    material_name_snapshot: str
    unit_snapshot: str
    quantity: Decimal
    unit_price_snapshot: Decimal
    line_total: Decimal
    is_alternative: bool
    created_at: datetime


class QuotationListRead(BaseModel):
    id: int
    quotation_number: str
    estimate_id: int
    user_id: int
    username: str
    furniture_type_id: int
    furniture_type_name: str
    material_total: Decimal
    labor_cost: Decimal
    logistics_cost: Decimal
    subtotal_before_profit: Decimal
    profit_percentage: Decimal
    profit_amount: Decimal
    grand_total: Decimal
    currency_code: str
    status: QuotationStatus
    valid_until: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class QuotationRead(QuotationListRead):
    items: list[QuotationItemRead]
