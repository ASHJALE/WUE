"""Backward-compatible public contracts for local furniture classification."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FurnitureClass = Literal["bed", "chair", "sofa", "dining_table", "lamp_shade"]
ClassifierStatus = Literal["ready", "disabled", "unavailable", "error"]


class FurnitureTypePrediction(BaseModel):
    key: FurnitureClass
    name: str
    confidence: float = Field(ge=0, le=1)


class RecognizedFurnitureType(BaseModel):
    key: FurnitureClass
    name: str


class ClassifierModelRead(BaseModel):
    backend: Literal["onnx"]
    version: str
    mode: Literal["trained_model", "development_fallback"]


class ClassificationRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upload_id: UUID
    predicted_class: FurnitureClass
    display_name: str
    confidence: float = Field(ge=0, le=1)
    model_name: str = "wue-furniture-classifier"
    model_version: str
    is_placeholder: bool
    supported_classes: list[FurnitureClass]
    status: Literal["classified"] = "classified"
    recognized_furniture_type: RecognizedFurnitureType | None = None
    confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    requires_confirmation: Literal[True] = True
    low_confidence: bool = False
    predictions: list[FurnitureTypePrediction] = Field(default_factory=list, max_length=5)
    model: ClassifierModelRead | None = None
    inference_ms: float = Field(default=0, ge=0)
    confirmed_class: FurnitureClass | None = None


class ClassifierHealthRead(BaseModel):
    status: ClassifierStatus
    enabled: bool
    backend: Literal["onnx"]
    model_version: str
    mode: Literal["trained_model", "development_fallback", "unavailable"]
    supported_labels: list[FurnitureClass]
