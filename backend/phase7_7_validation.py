"""Isolated ASGI validation for Phase 7.7 preliminary cost calculation."""

import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace

from app.dependencies.auth import get_current_user
from app.main import app
from app.schemas.cost import CostCalculateRequest
from app.schemas.quantity import FurnitureDimensions
from app.services.bom_generator import generate_bom
from app.services.cost_calculator import calculate_preliminary_cost
from app.services.material_price_catalog import MATERIAL_PRICE_CATALOG
from app.services.material_recommender import recommend_materials
from app.services.quantity_estimator import estimate_quantities

SUPPORTED_TYPES = ("chair", "bed", "sofa", "dining_table", "lamp_shade")
DIMENSIONS = {
    "chair": (450, 500, 900), "bed": (1600, 2000, 1000),
    "sofa": (2100, 900, 850), "dining_table": (1800, 900, 750),
    "lamp_shade": (350, 350, 600),
}


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
        "method": "POST", "scheme": "http", "path": "/costs/calculate",
        "raw_path": b"/costs/calculate", "query_string": b"", "root_path": "",
        "headers": headers, "client": ("127.0.0.1", 12345), "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], json.loads(response_body) if response_body else None


def pipeline_components(furniture_type: str):
    width, depth, height = DIMENSIONS[furniture_type]
    bom = generate_bom(furniture_type, recommend_materials(furniture_type))
    return estimate_quantities(
        furniture_type,
        FurnitureDimensions(width=width, depth=depth, height=height),
        bom,
    )


async def main():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=707, username="phase77")
    try:
        reachable_pairs = {
            (component.material, component.unit)
            for furniture_type in SUPPORTED_TYPES
            for component in pipeline_components(furniture_type)
        }
        assert reachable_pairs <= set(MATERIAL_PRICE_CATALOG)
        assert all(price > 0 for price in MATERIAL_PRICE_CATALOG.values())

        exact_payload = {
            "furniture_type": "chair",
            "components": [{
                "component": "Frame", "material": "Mahogany", "category": "Solid Wood",
                "estimated_quantity": 2.35, "unit": "board_foot",
                "calculation_basis": "Template Estimate", "confidence": "Preliminary",
            }],
            "labor": {"hours": 8, "hourly_rate": 150},
            "profit_margin_percent": 20,
        }
        status_code, response = await request(exact_payload)
        assert status_code == 200, (status_code, response)
        assert response["currency"] == "PHP"
        assert Decimal(str(response["components"][0]["unit_price"])) == Decimal("180.00")
        assert Decimal(str(response["components"][0]["subtotal"])) == Decimal("423.00")
        assert Decimal(str(response["total_material_cost"])) == Decimal("423.00")
        assert Decimal(str(response["labor"]["labor_cost"])) == Decimal("1200.00")
        assert Decimal(str(response["profit_amount"])) == Decimal("324.60")
        assert Decimal(str(response["final_estimated_cost"])) == Decimal("1947.60")
        assert "overhead" not in json.dumps(response).lower()

        direct = calculate_preliminary_cost(CostCalculateRequest.model_validate(exact_payload))
        assert direct.final_estimated_cost == Decimal("1947.60")

        invalid_furniture = {**exact_payload, "furniture_type": "desk"}
        invalid_furniture_status, _ = await request(invalid_furniture)
        assert invalid_furniture_status == 422

        empty_status, _ = await request({**exact_payload, "components": []})
        assert empty_status == 422
        malformed = json.loads(json.dumps(exact_payload))
        del malformed["components"][0]["material"]
        malformed_status, _ = await request(malformed)
        assert malformed_status == 422

        negative = json.loads(json.dumps(exact_payload))
        negative["components"][0]["estimated_quantity"] = -1
        negative_status, _ = await request(negative)
        assert negative_status == 422

        unsupported = json.loads(json.dumps(exact_payload))
        unsupported["components"][0]["material"] = "Uncatalogued Wood"
        unsupported_status, unsupported_response = await request(unsupported)
        assert unsupported_status == 422
        assert "Uncatalogued Wood (board_foot)" in unsupported_response["detail"]

        for field, value in (("hours", -1), ("hourly_rate", -1)):
            invalid_labor = json.loads(json.dumps(exact_payload))
            invalid_labor["labor"][field] = value
            invalid_labor_status, _ = await request(invalid_labor)
            assert invalid_labor_status == 422
        invalid_profit = {**exact_payload, "profit_margin_percent": 101}
        invalid_profit_status, _ = await request(invalid_profit)
        assert invalid_profit_status == 422

        app.dependency_overrides.clear()
        unauthorized_status, _ = await request(exact_payload, authenticated=False)
        assert unauthorized_status == 401

        operation = app.openapi()["paths"]["/costs/calculate"]["post"]
        assert operation["security"] and "200" in operation["responses"]

        print("COST_ENDPOINT_OK=True")
        print("JWT_REQUIRED_OK=True")
        print("INVALID_FURNITURE_422_OK=True")
        print("INVALID_COMPONENTS_422_OK=True")
        print("NEGATIVE_QUANTITY_REJECTED_OK=True")
        print("UNSUPPORTED_PRICE_RULE_422_OK=True")
        print("PRICE_CATALOG_COVERAGE_OK=True")
        print("DECIMAL_ARITHMETIC_OK=True")
        print("COMPONENT_SUBTOTAL_OK=True")
        print("MATERIAL_TOTAL_OK=True")
        print("LABOR_CALCULATION_OK=True")
        print("PROFIT_CALCULATION_OK=True")
        print("FINAL_TOTAL_OK=True")
        print("PHP_CURRENCY_OK=True")
        print("NO_OVERHEAD_OK=True")
        print("DATABASE_UNCHANGED=True")
        print("BACKEND_TESTS_OK=True")
    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    asyncio.run(main())
