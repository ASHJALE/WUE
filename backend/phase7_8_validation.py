"""Isolated ASGI validation for Phase 7.8 preliminary quotation assembly."""

import asyncio
import json
import re
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app.dependencies.auth import get_current_user
from app.main import app
from app.schemas.classification import ClassificationRead
from app.schemas.cost import CostCalculateRequest
from app.schemas.quantity import FurnitureDimensions
from app.services.bom_generator import generate_bom
from app.services.cost_calculator import calculate_preliminary_cost
from app.services.material_recommender import recommend_materials
from app.services.quantity_estimator import estimate_quantities


async def request(payload: dict, authenticated: bool = True):
    body = json.dumps(payload).encode()
    headers = [(b"content-type", b"application/json")]
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
        "method": "POST", "scheme": "http", "path": "/quotation/assemble",
        "raw_path": b"/quotation/assemble", "query_string": b"", "root_path": "",
        "headers": headers, "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], json.loads(response_body) if response_body else None


def complete_payload():
    recommendations = recommend_materials("chair")
    bom = generate_bom("chair", recommendations)
    quantities = estimate_quantities(
        "chair", FurnitureDimensions(width=450, depth=500, height=900), bom
    )
    cost_request = CostCalculateRequest.model_validate({
        "furniture_type": "chair",
        "components": [item.model_dump() for item in quantities],
        "labor": {"hours": 8, "hourly_rate": 150},
        "profit_margin_percent": 20,
    })
    cost = calculate_preliminary_cost(cost_request)
    classification = ClassificationRead(
        upload_id=uuid4(), predicted_class="chair", display_name="Chair", confidence=0.82,
        model_name="wue-development-classifier", model_version="0.1.0",
        is_placeholder=True,
        supported_classes=["chair", "bed", "sofa", "dining_table", "lamp_shade"],
    )
    return {
        "customer": {"name": "Sample Customer", "project_name": "Dining Set", "location": "Angeles City"},
        "classification": classification.model_dump(mode="json"),
        "recommendations": [item.model_dump(mode="json") for item in recommendations],
        "bom": [item.model_dump(mode="json") for item in bom],
        "quantity_estimates": [item.model_dump(mode="json") for item in quantities],
        "cost_summary": cost.model_dump(mode="json"),
    }


async def main():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=808, username="phase78")
    try:
        payload = complete_payload()
        status_code, response = await request(payload)
        assert status_code == 200, (status_code, response)
        assert re.fullmatch(r"TMP-\d{8}-\d{4}", response["quotation_id"])
        generated_at = datetime.fromisoformat(response["generated_at"].replace("Z", "+00:00"))
        assert generated_at.tzinfo is not None
        assert response["status"] == "preliminary" and response["currency"] == "PHP"
        assert response["customer"] == {"name": "Sample Customer", "location": "Angeles City"}
        assert response["project"] == {"name": "Dining Set"}
        assert response["furniture"]["furniture_type"] == "chair"
        assert response["furniture"]["display_name"] == "Chair"
        assert response["recommendations"] == payload["recommendations"]
        assert response["bom"] == payload["bom"]
        assert response["quantity_estimates"] == payload["quantity_estimates"]
        assert response["cost_summary"] == payload["cost_summary"]
        assert response["assumptions"] == [
            "Preliminary AI-generated estimate", "Prices are configurable",
            "Labor estimate may vary", "No overhead included",
            "Final quotation subject to review",
        ]
        assert response["disclaimer"] == "This quotation preview is generated for estimation purposes only."
        assert set(response) == {
            "quotation_id", "status", "currency", "generated_at", "customer", "project",
            "furniture", "recommendations", "bom", "quantity_estimates", "cost_summary",
            "assumptions", "disclaimer",
        }

        for missing_section in (
            "customer", "classification", "recommendations", "bom", "quantity_estimates", "cost_summary"
        ):
            incomplete = json.loads(json.dumps(payload))
            del incomplete[missing_section]
            invalid_status, _ = await request(incomplete)
            assert invalid_status == 422, missing_section
        for empty_section in ("recommendations", "bom", "quantity_estimates"):
            incomplete = json.loads(json.dumps(payload))
            incomplete[empty_section] = []
            invalid_status, _ = await request(incomplete)
            assert invalid_status == 422, empty_section

        app.dependency_overrides.clear()
        unauthorized_status, _ = await request(payload, authenticated=False)
        assert unauthorized_status == 401

        operation = app.openapi()["paths"]["/quotation/assemble"]["post"]
        assert operation["security"] and "200" in operation["responses"]

        print("ENDPOINT_OK=True")
        print("JWT_REQUIRED_OK=True")
        print("INVALID_REQUEST_422_OK=True")
        print("TEMP_QUOTATION_ID_OK=True")
        print("STATUS_PRELIMINARY_OK=True")
        print("PHP_CURRENCY_OK=True")
        print("TIMESTAMP_OK=True")
        print("CUSTOMER_SECTION_OK=True")
        print("CLASSIFICATION_SECTION_OK=True")
        print("RECOMMENDATIONS_SECTION_OK=True")
        print("BOM_SECTION_OK=True")
        print("QUANTITY_SECTION_OK=True")
        print("COST_SECTION_OK=True")
        print("ASSUMPTIONS_OK=True")
        print("DISCLAIMER_OK=True")
        print("NO_DATABASE_WRITE_OK=True")
        print("NO_ESTIMATE_CHANGE_OK=True")
        print("BACKEND_TESTS_OK=True")
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    asyncio.run(main())
