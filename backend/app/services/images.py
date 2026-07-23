"""Validated, bounded local storage for furniture image uploads."""

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.schemas.image import ImageUploadRead

MAX_IMAGE_BYTES = 5 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
UPLOAD_DIRECTORY = Path(__file__).resolve().parents[2] / "uploads" / "furniture"


def _matches_image_signature(content_type: str, header: bytes) -> bool:
    if content_type == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    return False


def _metadata_path(upload_id: UUID) -> Path:
    return UPLOAD_DIRECTORY / f"{upload_id}.json"


@dataclass(frozen=True)
class OwnedUpload:
    path: Path
    stored_filename: str
    content_type: str


def get_owned_upload(upload_id: UUID, owner_user_id: int) -> OwnedUpload | None:
    """Return validated upload metadata for its owner only."""
    try:
        metadata = json.loads(_metadata_path(upload_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if metadata.get("owner_user_id") != owner_user_id:
        return None
    stored_filename = metadata.get("stored_filename")
    content_type = metadata.get("content_type")
    expected_prefix = f"{upload_id}."
    if (
        not isinstance(stored_filename, str)
        or not stored_filename.startswith(expected_prefix)
        or content_type not in CONTENT_TYPE_EXTENSIONS
    ):
        return None
    candidate = UPLOAD_DIRECTORY / stored_filename
    if candidate.parent.resolve() != UPLOAD_DIRECTORY.resolve() or not candidate.is_file():
        return None
    return OwnedUpload(candidate, stored_filename, content_type)


def find_owned_upload(upload_id: UUID, owner_user_id: int) -> Path | None:
    """Resolve a server-issued upload without revealing other users' uploads."""
    owned_upload = get_owned_upload(upload_id, owner_user_id)
    return owned_upload.path if owned_upload else None


async def save_furniture_image(image: UploadFile | None, owner_user_id: int) -> ImageUploadRead:
    if image is None or not image.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A furniture image is required.")

    content_type = image.content_type or ""
    extension = CONTENT_TYPE_EXTENSIONS.get(content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Choose a JPEG, PNG, or WebP image.",
        )

    upload_id: UUID = uuid4()
    stored_filename = f"{upload_id}{extension}"
    destination = UPLOAD_DIRECTORY / stored_filename
    metadata_destination = _metadata_path(upload_id)
    size_bytes = 0
    header = b""

    try:
        UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            while chunk := await image.read(READ_CHUNK_BYTES):
                size_bytes += len(chunk)
                if size_bytes > MAX_IMAGE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="Image is larger than 5 MB.",
                    )
                if len(header) < 16:
                    header = (header + chunk)[:16]
                output.write(chunk)

        if size_bytes == 0 or not _matches_image_signature(content_type, header):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is not a valid image.",
            )
        metadata_destination.write_text(
            json.dumps(
                {
                    "upload_id": str(upload_id),
                    "owner_user_id": owner_user_id,
                    "stored_filename": stored_filename,
                    "content_type": content_type,
                    "size_bytes": size_bytes,
                }
            ),
            encoding="utf-8",
        )
    except HTTPException:
        destination.unlink(missing_ok=True)
        metadata_destination.unlink(missing_ok=True)
        raise
    except OSError as error:
        destination.unlink(missing_ok=True)
        metadata_destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The image could not be saved.",
        ) from error
    finally:
        await image.close()

    return ImageUploadRead(
        upload_id=upload_id,
        original_filename=Path(image.filename).name,
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )
