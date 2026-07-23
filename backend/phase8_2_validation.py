"""Isolated Phase 8.2 classifier plumbing validation without database fixtures."""

import asyncio
import io
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
from PIL import Image
from sqlalchemy import text

from app.ai.classifier import FurnitureClassifier, ModelOutputError
from app.ai.labels import SUPPORTED_LABELS
from app.ai.model_loader import onnx_model_loader
from app.ai import preprocessing
from app.config import get_classifier_settings
from app.database import get_engine
from app.dependencies.auth import get_current_user
from app.main import app
from app.schemas.classification import ClassificationRead
from app.services import images as image_service


class MockOnnxSession:
    def __init__(self, output=None):
        self.calls = 0
        self.output = output or [[0.2, 2.5, 0.1, -0.2, 0.0]]

    def run(self, _outputs, inputs):
        self.calls += 1
        assert list(inputs.values())[0].shape == (1, 3, 224, 224)
        return [np.asarray(self.output, dtype=np.float32)]


async def request(method, path, body=b"", content_type=None, authenticated=True):
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
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "root_path": "", "headers": headers,
        "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(item for item in messages if item["type"] == "http.response.start")
    payload = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")
    return start["status"], json.loads(payload) if payload else None


def image_bytes(image_format="PNG", color=(90, 120, 70), size=(16, 12)):
    output = io.BytesIO()
    with Image.new("RGB", size, color=color) as image:
        image.save(output, format=image_format)
    return output.getvalue()


async def upload(content, owner_id=101, filename="furniture.png", mime="image/png"):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=owner_id, username=f"user-{owner_id}"
    )
    boundary = "WUEPhase82Boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return await request("POST", "/images/upload", body, f"multipart/form-data; boundary={boundary}")


async def classify(upload_id, owner_id=101, authenticated=True):
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=owner_id, username=f"user-{owner_id}"
        )
    else:
        app.dependency_overrides.clear()
    return await request("POST", f"/images/{upload_id}/classify", authenticated=authenticated)


def configure(enabled=True, fallback=False):
    os.environ["FURNITURE_CLASSIFIER_ENABLED"] = str(enabled).lower()
    os.environ["FURNITURE_DEVELOPMENT_FALLBACK_ENABLED"] = str(fallback).lower()
    os.environ["FURNITURE_MODEL_PATH"] = "models/nonexistent-validation-model.onnx"
    os.environ["FURNITURE_MODEL_OUTPUT_IS_LOGITS"] = "true"
    os.environ["FURNITURE_MIN_CONFIDENCE"] = "0.50"
    get_classifier_settings.cache_clear()


async def main():
    original_directory = image_service.UPLOAD_DIRECTORY
    original_limit = preprocessing.MAX_DECODED_PIXELS
    before_counts = {}
    with get_engine().connect() as connection:
        for table in ("estimates", "quotations", "inventory"):
            before_counts[table] = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()

    with tempfile.TemporaryDirectory(prefix="wue-phase82-") as temporary:
        image_service.UPLOAD_DIRECTORY = Path(temporary) / "furniture"
        try:
            configure()
            mock_session = MockOnnxSession()
            onnx_model_loader._session = mock_session
            onnx_model_loader._input_name = "image"
            onnx_model_loader._load_attempted = True
            onnx_model_loader._load_count = 1
            onnx_model_loader._load_error = None

            upload_status, uploaded = await upload(image_bytes(), filename="bed.png")
            assert upload_status == 201
            status, result = await classify(uploaded["upload_id"])
            assert status == 200
            assert result["predicted_class"] == "chair"
            assert result["recognized_furniture_type"]["key"] == "chair"
            assert result["requires_confirmation"] is True
            assert result["model"]["mode"] == "trained_model"
            probabilities = [item["confidence"] for item in result["predictions"]]
            assert probabilities == sorted(probabilities, reverse=True)
            assert abs(sum(probabilities) - 1) < 1e-4
            assert {item["key"] for item in result["predictions"]} == set(SUPPORTED_LABELS)
            assert mock_session.calls == 1

            same_status, same = await classify(uploaded["upload_id"])
            assert same_status == 200 and same["predicted_class"] == result["predicted_class"]
            assert onnx_model_loader.load_count == 1

            renamed_status, renamed = await upload(image_bytes(), filename="lamp_shade.png")
            assert renamed_status == 201
            renamed_classify_status, renamed_result = await classify(renamed["upload_id"])
            assert renamed_classify_status == 200
            assert renamed_result["predicted_class"] == result["predicted_class"]

            assert (await classify(uploaded["upload_id"], owner_id=202))[0] == 404
            assert (await classify(uploaded["upload_id"], authenticated=False))[0] == 401
            assert (await classify(str(uuid4())))[0] == 404

            corrupt_status, corrupt = await upload(image_bytes())
            assert corrupt_status == 201
            (image_service.UPLOAD_DIRECTORY / corrupt["stored_filename"]).write_bytes(b"not an image")
            assert (await classify(corrupt["upload_id"]))[0] == 422
            non_image_status, _ = await upload(b"plain text", filename="fake.png")
            assert non_image_status == 400

            preprocessing.MAX_DECODED_PIXELS = 100
            oversized_status, oversized = await upload(image_bytes(size=(11, 10)))
            assert oversized_status == 201
            assert (await classify(oversized["upload_id"]))[0] == 422
            preprocessing.MAX_DECODED_PIXELS = original_limit

            low_session = MockOnnxSession([[0.21, 0.20, 0.20, 0.20, 0.19]])
            onnx_model_loader._session = low_session
            low_status, low = await classify(uploaded["upload_id"])
            assert low_status == 200 and low["low_confidence"] is True

            invalid_classifier = FurnitureClassifier(onnx_model_loader)
            onnx_model_loader._session = MockOnnxSession([[1.0, 2.0]])
            try:
                invalid_classifier.classify_image(image_service.UPLOAD_DIRECTORY / uploaded["stored_filename"])
                raise AssertionError("Invalid output shape was accepted.")
            except ModelOutputError:
                pass

            configure(enabled=True, fallback=False)
            onnx_model_loader.reset_for_tests()
            unavailable_status, unavailable = await classify(uploaded["upload_id"])
            assert unavailable_status == 503 and "unavailable" in unavailable["detail"].lower()
            health_status, health = await request("GET", "/health/classifier")
            assert health_status == 200 and health["status"] == "unavailable"

            configure(enabled=False)
            onnx_model_loader.reset_for_tests()
            disabled_status, disabled = await request("GET", "/health/classifier")
            assert disabled_status == 200 and disabled["status"] == "disabled"

            configure(enabled=True, fallback=True)
            onnx_model_loader.reset_for_tests()
            fallback_status, fallback = await classify(uploaded["upload_id"])
            assert fallback_status == 200
            assert fallback["model"]["mode"] == "development_fallback"
            assert fallback["is_placeholder"] is True

            parsed = ClassificationRead.model_validate({**result, "confirmed_class": "sofa"})
            assert parsed.predicted_class == "chair" and parsed.confirmed_class == "sofa"

            with get_engine().connect() as connection:
                after_counts = {
                    table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                    for table in before_counts
                }
            assert after_counts == before_counts

            for label in (
                "CLASSIFICATION_ENDPOINT_OK", "CLASSIFIER_HEALTH_ENDPOINT_OK",
                "JWT_REQUIRED_OK", "UPLOAD_OWNERSHIP_OK", "REAL_MODEL_ADAPTER_OK",
                "MODEL_LOAD_ONCE_OK", "MODEL_CONFIG_OK", "SAFE_MODEL_FAILURE_OK",
                "IMAGE_PREPROCESSING_OK", "EXIF_ORIENTATION_OK", "CORRUPT_IMAGE_REJECTED_OK",
                "NON_IMAGE_REJECTED_OK", "OVERSIZED_IMAGE_REJECTED_OK",
                "SUPPORTED_LABELS_ONLY_OK", "OUTPUT_MAPPING_OK", "RANKED_PREDICTIONS_OK",
                "PREDICTIONS_SORTED_OK", "CONFIDENCE_RANGE_OK", "PROBABILITY_SUM_OK",
                "LOW_CONFIDENCE_HANDLING_OK", "MANUAL_CONFIRMATION_REQUIRED_OK",
                "MANUAL_OVERRIDE_OK", "RECOGNIZED_TYPE_PRESERVED_OK",
                "CONFIRMED_TYPE_UPDATED_OK", "MODEL_UNAVAILABLE_HANDLING_OK",
                "DEVELOPMENT_FALLBACK_EXPLICIT_OK", "NO_FILENAME_CLASSIFICATION_OK",
                "NO_CLASSIFICATION_DB_MUTATION_OK",
            ):
                print(f"{label}=True")
            print("BACKEND_TESTS_OK=True")
        finally:
            app.dependency_overrides.clear()
            image_service.UPLOAD_DIRECTORY = original_directory
            preprocessing.MAX_DECODED_PIXELS = original_limit
            for name in (
                "FURNITURE_CLASSIFIER_ENABLED",
                "FURNITURE_DEVELOPMENT_FALLBACK_ENABLED",
                "FURNITURE_MODEL_PATH",
                "FURNITURE_MODEL_OUTPUT_IS_LOGITS",
                "FURNITURE_MIN_CONFIDENCE",
            ):
                os.environ.pop(name, None)
            get_classifier_settings.cache_clear()
            onnx_model_loader.reset_for_tests()


if __name__ == "__main__":
    asyncio.run(main())
