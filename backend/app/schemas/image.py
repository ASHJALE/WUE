"""Response schema for authenticated furniture image uploads."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ImageUploadRead(BaseModel):
    upload_id: UUID
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    status: Literal["uploaded"] = "uploaded"
