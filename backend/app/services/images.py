"""Validated, bounded local storage for furniture image uploads."""

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


async def save_furniture_image(image: UploadFile | None) -> ImageUploadRead:
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
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except OSError as error:
        destination.unlink(missing_ok=True)
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
