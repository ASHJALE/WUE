"""Authenticated furniture image upload endpoint."""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.dependencies.auth import CurrentUser
from app.schemas.image import ImageUploadRead
from app.services.images import save_furniture_image

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/upload", response_model=ImageUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_furniture_image(
    _current_user: CurrentUser,
    image: Annotated[UploadFile | None, File()] = None,
) -> ImageUploadRead:
    return await save_furniture_image(image)
