"""Isolated ASGI validation for Phase 7.3 furniture classification."""

import asyncio
import io
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from PIL import Image

from app.dependencies.auth import get_current_user
from app.main import app
from app.services import images as image_service
from app.services.image_classifier import SUPPORTED_CLASSES


async def request(path: str, body: bytes = b"", content_type: str | None = None, authenticated: bool = True):
    headers = []
    if content_type:
        headers.append((b"content-type", content_type.encode()))
    if authenticated:
        headers.append((b"authorization", b"Bearer validation-token"))
    messages = []
    delivered = False

    async def receive():
        nonlocal delivered
        if not delivered:
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "root_path": "", "headers": headers,
        "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], json.loads(response_body) if response_body else None


def image_bytes(image_format: str = "PNG") -> bytes:
    output = io.BytesIO()
    with Image.new("RGB", (4, 4), color=(80, 120, 90)) as image:
        image.save(output, format=image_format)
    return output.getvalue()


async def upload(content: bytes, owner_id: int = 101):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=owner_id, username=f"user-{owner_id}")
    boundary = "WUEPhase73Boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="image"; filename="chair.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return await request("/images/upload", body, f"multipart/form-data; boundary={boundary}")


async def classify(upload_id: str, owner_id: int = 101, authenticated: bool = True):
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=owner_id, username=f"user-{owner_id}")
    else:
        app.dependency_overrides.clear()
    return await request(f"/images/{upload_id}/classify", authenticated=authenticated)


async def main():
    original_directory = image_service.UPLOAD_DIRECTORY
    with tempfile.TemporaryDirectory(prefix="wue-phase73-") as temporary:
        image_service.UPLOAD_DIRECTORY = Path(temporary) / "furniture"
        try:
            upload_status, uploaded = await upload(image_bytes())
            assert upload_status == 201

            first_status, first = await classify(uploaded["upload_id"])
            second_status, second = await classify(uploaded["upload_id"])
            assert first_status == second_status == 200
            assert first == second
            assert first["predicted_class"] in SUPPORTED_CLASSES
            assert 0 <= first["confidence"] <= 1
            assert first["display_name"] and "_" not in first["display_name"]
            assert first["is_placeholder"] is True
            assert first["model_name"] == "wue-development-classifier"
            assert first["model_version"] == "0.1.0"
            assert first["supported_classes"] == list(SUPPORTED_CLASSES)
            assert "path" not in first and str(image_service.UPLOAD_DIRECTORY) not in json.dumps(first)

            missing_status, _ = await classify(str(uuid4()))
            assert missing_status == 404

            other_user_status, _ = await classify(uploaded["upload_id"], owner_id=202)
            assert other_user_status == 404

            unauthenticated_status, _ = await classify(uploaded["upload_id"], authenticated=False)
            assert unauthenticated_status == 401

            corrupt_status, corrupt_upload = await upload(image_bytes(), owner_id=101)
            assert corrupt_status == 201
            (image_service.UPLOAD_DIRECTORY / corrupt_upload["stored_filename"]).write_bytes(b"corrupted")
            corrupt_classify_status, corrupt_response = await classify(corrupt_upload["upload_id"])
            assert corrupt_classify_status == 422
            assert "corrupted or unreadable" in corrupt_response["detail"]

            operation = app.openapi()["paths"]["/images/{upload_id}/classify"]["post"]
            assert operation["security"] and "200" in operation["responses"]

            print("CLASSIFY_ENDPOINT_OK=True")
            print("JWT_REQUIRED_OK=True")
            print("UPLOAD_LOOKUP_OK=True")
            print("MISSING_UPLOAD_404_OK=True")
            print("UPLOAD_OWNERSHIP_OK=True")
            print("CORRUPT_IMAGE_422_OK=True")
            print("IMAGE_CONTENT_VERIFICATION_OK=True")
            print("DETERMINISTIC_CLASSIFIER_OK=True")
            print("SUPPORTED_CLASSES_ONLY_OK=True")
            print("CONFIDENCE_RANGE_OK=True")
            print("PLACEHOLDER_METADATA_OK=True")
            print("NO_INTERNAL_PATH_EXPOSURE_OK=True")
            print("BACKEND_TESTS_OK=True")
        finally:
            app.dependency_overrides.clear()
            image_service.UPLOAD_DIRECTORY = original_directory


if __name__ == "__main__":
    asyncio.run(main())
