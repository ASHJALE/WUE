"""Quotation generation request and read schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.bom import GeneratedBOMItem
from app.schemas.classification import ClassificationRead, FurnitureClass
from app.schemas.cost import CostCalculateResponse
from app.schemas.material import MaterialRecommendation
from app.schemas.quantity import EstimatedQuantityItem

QuotationStatus = Literal["draft", "approved", "rejected", "completed"]


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


class PreliminaryCustomerInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    project_name: str = Field(min_length=1, max_length=150)
    location: str = Field(min_length=1, max_length=200)

    @field_validator("name", "project_name", "location")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Customer and project fields must not be blank.")
        return cleaned


class PreliminaryQuotationAssemble(BaseModel):
    customer: PreliminaryCustomerInput
    classification: ClassificationRead
    recommendations: list[MaterialRecommendation] = Field(min_length=1)
    bom: list[GeneratedBOMItem] = Field(min_length=1)
    quantity_estimates: list[EstimatedQuantityItem] = Field(min_length=1)
    cost_summary: CostCalculateResponse

    @model_validator(mode="after")
    def validate_sections_are_consistent(self):
        selected_type = self.classification.confirmed_class or self.classification.predicted_class
        if selected_type != self.cost_summary.furniture_type:
            raise ValueError("Classification and cost summary furniture types must match.")
        bom_components = {item.component for item in self.bom}
        quantity_components = {item.component for item in self.quantity_estimates}
        cost_components = {item.component for item in self.cost_summary.components}
        if bom_components != quantity_components or quantity_components != cost_components:
            raise ValueError("BOM, quantity, and cost components must match.")
        return self


class PreliminaryCustomerRead(BaseModel):
    name: str
    location: str


class PreliminaryProjectRead(BaseModel):
    name: str


class PreliminaryFurnitureRead(BaseModel):
    furniture_type: FurnitureClass
    recognized_furniture_type: FurnitureClass | None = None
    display_name: str
    confidence: float = Field(ge=0, le=1)
    model_name: str
    model_version: str
    is_placeholder: bool
    model_backend: str | None = None
    model_mode: str | None = None


class PreliminaryQuotationRead(BaseModel):
    quotation_id: str = Field(pattern=r"^TMP-\d{8}-\d{4}$")
    status: Literal["preliminary"] = "preliminary"
    currency: Literal["PHP"] = "PHP"
    generated_at: datetime
    customer: PreliminaryCustomerRead
    project: PreliminaryProjectRead
    furniture: PreliminaryFurnitureRead
    recommendations: list[MaterialRecommendation]
    bom: list[GeneratedBOMItem]
    quantity_estimates: list[EstimatedQuantityItem]
    cost_summary: CostCalculateResponse
    assumptions: list[str]
    disclaimer: Literal["This quotation preview is generated for estimation purposes only."]
