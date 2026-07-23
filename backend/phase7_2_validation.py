"""Isolated ASGI validation for Phase 7.2 furniture image uploads."""

import asyncio
import json
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from app.dependencies.auth import get_current_user
from app.main import app
from app.services import images as image_service


def multipart_body(boundary: str, filename: str, content_type: str, content: bytes) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()


async def request(body: bytes = b"", content_type: str | None = None, authenticated: bool = True):
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
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/images/upload",
        "raw_path": b"/images/upload",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], dict(start["headers"]), json.loads(response_body) if response_body else None


async def upload(filename: str, mime: str, content: bytes):
    boundary = "WUEPhase72Boundary"
    return await request(
        multipart_body(boundary, filename, mime, content),
        f"multipart/form-data; boundary={boundary}",
    )


async def main():
    original_directory = image_service.UPLOAD_DIRECTORY
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=999, username="phase72")
    with tempfile.TemporaryDirectory(prefix="wue-phase72-") as temporary:
        upload_directory = Path(temporary) / "nested" / "furniture"
        image_service.UPLOAD_DIRECTORY = upload_directory
        try:
            valid_cases = [
                ("chair.jpg", "image/jpeg", b"\xff\xd8\xff\xe0" + b"jpeg-data"),
                ("table.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"png-data"),
                ("sofa.webp", "image/webp", b"RIFF\x04\x00\x00\x00WEBP" + b"webp-data"),
            ]
            responses = []
            for filename, mime, content in valid_cases:
                status_code, _, payload = await upload(filename, mime, content)
                assert status_code == 201, (status_code, payload)
                assert payload["content_type"] == mime
                assert payload["size_bytes"] == len(content)
                UUID(payload["upload_id"])
                assert re.fullmatch(r"[0-9a-f-]{36}\.(jpg|png|webp)", payload["stored_filename"])
                assert "/" not in payload["stored_filename"] and "\\" not in payload["stored_filename"]
                assert "path" not in payload and str(upload_directory) not in json.dumps(payload)
                assert (upload_directory / payload["stored_filename"]).is_file()
                responses.append(payload)

            traversal_status, _, traversal = await upload("../../unsafe-name.jpg", "image/jpeg", b"\xff\xd8\xffsafe")
            assert traversal_status == 201 and traversal["original_filename"] == "unsafe-name.jpg"

            unsupported_status, _, _ = await upload("bad.gif", "image/gif", b"GIF89a")
            assert unsupported_status == 415

            before_oversized = set(upload_directory.iterdir())
            oversized_status, _, _ = await upload("large.jpg", "image/jpeg", b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024))
            assert oversized_status == 413
            assert set(upload_directory.iterdir()) == before_oversized

            invalid_status, _, _ = await upload("fake.jpg", "image/jpeg", b"not-a-jpeg")
            assert invalid_status == 400

            missing_status, _, _ = await request(
                b"--empty--\r\n", "multipart/form-data; boundary=empty"
            )
            assert missing_status == 400

            app.dependency_overrides.clear()
            unauthenticated_status, headers, _ = await upload("chair.jpg", "image/jpeg", b"\xff\xd8\xffdata")
            assert unauthenticated_status == 401
            assert b"www-authenticate" in headers

            openapi = app.openapi()
            operation = openapi["paths"]["/images/upload"]["post"]
            assert "multipart/form-data" in operation["requestBody"]["content"]
            assert "201" in operation["responses"]

            print("BACKEND_IMAGE_ENDPOINT_OK=True")
            print("JWT_REQUIRED_OK=True")
            print("MULTIPART_UPLOAD_OK=True")
            print("JPEG_UPLOAD_OK=True")
            print("PNG_UPLOAD_OK=True")
            print("WEBP_UPLOAD_OK=True")
            print("UNSUPPORTED_TYPE_415_OK=True")
            print("MAX_5MB_413_OK=True")
            print("SAFE_UUID_FILENAME_OK=True")
            print("UPLOAD_DIRECTORY_OK=True")
            print("PARTIAL_FILE_CLEANUP_OK=True")
            print("NO_INTERNAL_PATH_EXPOSURE_OK=True")
            print("BACKEND_TESTS_OK=True")
        finally:
            app.dependency_overrides.clear()
            image_service.UPLOAD_DIRECTORY = original_directory


if __name__ == "__main__":
    asyncio.run(main())
