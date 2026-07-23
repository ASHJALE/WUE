"""Contracts for atomically integrating a completed Phase 7 workflow."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.bom import GeneratedBOMItem
from app.schemas.classification import FurnitureClass
from app.schemas.cost import CostCalculateResponse
from app.schemas.material import MaterialRecommendation
from app.schemas.quantity import EstimatedQuantityItem, FurnitureDimensions
from app.schemas.quotation import PreliminaryQuotationRead


class Phase7UploadIntegration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    upload_id: UUID
    image_path: str = Field(min_length=1, max_length=500)


class Phase7ClassificationIntegration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recognized_furniture_type: FurnitureClass
    confirmed_furniture_type: FurnitureClass
    confidence: Decimal = Field(ge=0, le=1, max_digits=5, decimal_places=4)


class Phase7DimensionsIntegration(FurnitureDimensions):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    unit: Literal["mm", "cm"]


class Phase7IntegrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upload: Phase7UploadIntegration
    classification: Phase7ClassificationIntegration
    dimensions: Phase7DimensionsIntegration
    recommendations: list[MaterialRecommendation] = Field(min_length=1)
    bom: list[GeneratedBOMItem] = Field(min_length=1)
    quantity_estimates: list[EstimatedQuantityItem] = Field(min_length=1)
    cost_summary: CostCalculateResponse
    preliminary_quotation: PreliminaryQuotationRead

    @model_validator(mode="after")
    def validate_completed_workflow(self):
        confirmed = self.classification.confirmed_furniture_type
        if self.cost_summary.furniture_type != confirmed:
            raise ValueError("Cost summary furniture type must match the confirmed type.")
        if self.preliminary_quotation.furniture.furniture_type != confirmed:
            raise ValueError("Quotation furniture type must match the confirmed type.")
        if Decimal(str(self.preliminary_quotation.furniture.confidence)) != self.classification.confidence:
            raise ValueError("Quotation confidence must match submitted classification confidence.")
        if self.preliminary_quotation.status != "preliminary" or self.preliminary_quotation.currency != "PHP":
            raise ValueError("Preliminary quotation must use preliminary status and PHP currency.")
        if self.preliminary_quotation.cost_summary != self.cost_summary:
            raise ValueError("Quotation and submitted cost summaries must match.")
        bom_components = {item.component for item in self.bom}
        quantity_components = {item.component for item in self.quantity_estimates}
        cost_components = {item.component for item in self.cost_summary.components}
        quotation_bom = {item.component for item in self.preliminary_quotation.bom}
        quotation_quantities = {
            item.component for item in self.preliminary_quotation.quantity_estimates
        }
        if not (
            bom_components
            == quantity_components
            == cost_components
            == quotation_bom
            == quotation_quantities
        ):
            raise ValueError("BOM, quantity, cost, and quotation components must match.")
        if self.preliminary_quotation.recommendations != self.recommendations:
            raise ValueError("Quotation recommendations must match submitted recommendations.")
        return self


class IntegratedFurnitureTypeRead(BaseModel):
    id: int
    name: str


class Phase7IntegrationRead(BaseModel):
    estimate_id: int
    status: Literal["integrated"] = "integrated"
    selected_furniture_type: IntegratedFurnitureTypeRead
    recognized_furniture_type: IntegratedFurnitureTypeRead
    recognition_confidence: Decimal
    image_path: str
    phase7_snapshot_saved: bool
    bom_preview_available: bool
    updated_at: datetime
