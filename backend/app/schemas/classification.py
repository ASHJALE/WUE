"""Public contract for development furniture classification results."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

FurnitureClass = Literal["chair", "bed", "sofa", "dining_table", "lamp_shade"]


class ClassificationRead(BaseModel):
    upload_id: UUID
    predicted_class: FurnitureClass
    display_name: str
    confidence: float = Field(ge=0, le=1)
    model_name: Literal["wue-development-classifier"] = "wue-development-classifier"
    model_version: Literal["0.1.0"] = "0.1.0"
    is_placeholder: Literal[True] = True
    supported_classes: list[FurnitureClass]
    status: Literal["classified"] = "classified"
