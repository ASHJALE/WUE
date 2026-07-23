"""Decimal-safe preliminary material, labor, and profit calculation."""

from decimal import Decimal

from app.schemas.cost import (
    CostCalculateRequest,
    CostCalculateResponse,
    CostedComponent,
    LaborCostRead,
    money,
)
from app.services.material_price_catalog import MATERIAL_PRICE_CATALOG
from app.services.material_recommender import DISPLAY_NAMES


class UnsupportedMaterialPriceError(ValueError):
    """Raised when preliminary pricing lacks an exact material/unit rule."""


def calculate_preliminary_cost(data: CostCalculateRequest) -> CostCalculateResponse:
    costed_components = []
    for component in data.components:
        unit_price = MATERIAL_PRICE_CATALOG.get((component.material, component.unit))
        if unit_price is None:
            raise UnsupportedMaterialPriceError(
                f"No preliminary price is configured for {component.material} ({component.unit})."
            )
        costed_components.append(
            CostedComponent(
                component=component.component,
                material=component.material,
                category=component.category,
                estimated_quantity=component.estimated_quantity,
                unit=component.unit,
                unit_price=money(unit_price),
                subtotal=money(component.estimated_quantity * unit_price),
            )
        )

    material_total = money(sum((item.subtotal for item in costed_components), Decimal("0")))
    labor_cost = money(data.labor.hours * data.labor.hourly_rate)
    profit_amount = money(
        (material_total + labor_cost) * data.profit_margin_percent / Decimal("100")
    )
    final_cost = money(material_total + labor_cost + profit_amount)
    return CostCalculateResponse(
        furniture_type=data.furniture_type,
        display_name=DISPLAY_NAMES[data.furniture_type],
        components=costed_components,
        total_material_cost=material_total,
        labor=LaborCostRead(
            hours=data.labor.hours,
            hourly_rate=money(data.labor.hourly_rate),
            labor_cost=labor_cost,
        ),
        profit_margin_percent=data.profit_margin_percent,
        profit_amount=profit_amount,
        final_estimated_cost=final_cost,
    )
