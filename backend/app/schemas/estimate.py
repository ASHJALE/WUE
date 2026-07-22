"""Estimate request and response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EstimateInputMethod = Literal["predefined", "image_upload"]
EstimateStatus = Literal["draft", "processing", "processed", "quoted"]


class EstimateCreate(BaseModel):
    user_id: int
    selected_furniture_type_id: int | None = None
    recognized_furniture_type_id: int | None = None
    image_path: str | None = Field(default=None, max_length=500)
    input_method: EstimateInputMethod
    recognition_confidence: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=5, decimal_places=4
    )

    @model_validator(mode="after")
    def validate_related_fields(self):
        recognized = self.recognized_furniture_type_id is not None
        confidence = self.recognition_confidence is not None
        if recognized != confidence:
            raise ValueError(
                "Recognized furniture type and confidence must be supplied together."
            )
        if self.input_method == "image_upload" and not (
            self.image_path and self.image_path.strip()
        ):
            raise ValueError("Image upload requires a nonblank image path.")
        if self.image_path is not None:
            self.image_path = self.image_path.strip() or None
        return self


class EstimateUpdate(BaseModel):
    user_id: int | None = None
    selected_furniture_type_id: int | None = None
    recognized_furniture_type_id: int | None = None
    image_path: str | None = Field(default=None, max_length=500)
    input_method: EstimateInputMethod | None = None
    recognition_confidence: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=5, decimal_places=4
    )
    status: EstimateStatus | None = None


class EstimateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str
    selected_furniture_type_id: int | None
    selected_furniture_type_name: str | None
    recognized_furniture_type_id: int | None
    recognized_furniture_type_name: str | None
    image_path: str | None
    input_method: EstimateInputMethod
    recognition_confidence: Decimal | None
    status: EstimateStatus
    created_at: datetime
    updated_at: datetime
