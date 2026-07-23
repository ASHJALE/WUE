"""Authenticated furniture image upload endpoint."""

from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.dependencies.auth import CurrentUser
from app.schemas.image import ImageUploadRead
from app.schemas.classification import ClassificationRead
from app.services.image_classifier import (
    SUPPORTED_CLASSES,
    UnreadableImageError,
    image_classifier,
)
from app.services.images import find_owned_upload, get_owned_upload, save_furniture_image

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/upload", response_model=ImageUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_furniture_image(
    _current_user: CurrentUser,
    image: Annotated[UploadFile | None, File()] = None,
) -> ImageUploadRead:
    return await save_furniture_image(image, _current_user.id)


@router.post("/{upload_id}/classify", response_model=ClassificationRead)
def classify_furniture_image(upload_id: UUID, current_user: CurrentUser) -> ClassificationRead:
    image_path = find_owned_upload(upload_id, current_user.id)
    if image_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image upload not found.")
    try:
        result = image_classifier.classify_image(image_path)
    except UnreadableImageError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return ClassificationRead(
        upload_id=upload_id,
        predicted_class=result.predicted_class,
        display_name=result.display_name,
        confidence=result.confidence,
        model_name=result.model_name,
        model_version=result.model_version,
        is_placeholder=result.is_placeholder,
        supported_classes=list(SUPPORTED_CLASSES),
    )


@router.get("/{upload_id}/content", response_class=FileResponse)
def get_furniture_image_content(upload_id: UUID, current_user: CurrentUser) -> FileResponse:
    upload = get_owned_upload(upload_id, current_user.id)
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image upload not found.")
    return FileResponse(upload.path, media_type=upload.content_type)
