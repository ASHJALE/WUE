"""Configurable preliminary quantity rules for structured WUE BOM components."""

from dataclasses import dataclass

from app.schemas.bom import GeneratedBOMItem
from app.schemas.quantity import EstimatedQuantityItem, FurnitureDimensions


class UnsupportedBOMComponentError(ValueError):
    """Raised when a component has no approved rule for its furniture type."""


@dataclass(frozen=True)
class QuantityRule:
    unit: str
    basis: str
    multiplier: float


QUANTITY_RULE_CATALOG = {
    "chair": {
        "Frame": QuantityRule("board_foot", "volume", 0.035),
        "Seat": QuantityRule("square_meter", "width_depth_area", 1.12),
        "Backrest": QuantityRule("square_meter", "width_height_area", 0.58),
        "Legs": QuantityRule("meter", "height_length", 1.8),
        "Fasteners": QuantityRule("set", "fixed", 1),
        "Finish": QuantityRule("application", "fixed", 1),
    },
    "bed": {
        "Headboard": QuantityRule("square_meter", "width_height_area", 0.72),
        "Footboard": QuantityRule("square_meter", "width_height_area", 0.38),
        "Rails": QuantityRule("meter", "perimeter_length", 1.05),
        "Slats": QuantityRule("square_meter", "width_depth_area", 1.08),
        "Legs": QuantityRule("meter", "height_length", 0.9),
        "Hardware": QuantityRule("set", "fixed", 1),
    },
    "sofa": {
        "Frame": QuantityRule("board_foot", "volume", 0.028),
        "Foam": QuantityRule("square_meter", "width_depth_area", 1.65),
        "Fabric": QuantityRule("square_meter", "surface_area", 1.3),
        "Legs": QuantityRule("set", "fixed", 1),
        "Fasteners": QuantityRule("set", "fixed", 1),
    },
    "dining_table": {
        "Tabletop": QuantityRule("square_meter", "width_depth_area", 1.08),
        "Frame": QuantityRule("board_foot", "volume", 0.018),
        "Legs": QuantityRule("meter", "height_length", 3.6),
        "Fasteners": QuantityRule("set", "fixed", 1),
        "Finish": QuantityRule("application", "fixed", 1),
    },
    "lamp_shade": {
        "Shade": QuantityRule("square_meter", "surface_area", 0.42),
        "Frame": QuantityRule("meter", "perimeter_length", 0.9),
        "Holder": QuantityRule("piece", "fixed", 1),
        "Base": QuantityRule("piece", "fixed", 1),
        "Electrical Hardware": QuantityRule("set", "fixed", 1),
    },
}


def _basis_value(basis: str, dimensions: FurnitureDimensions) -> float:
    width = dimensions.width / 1000
    depth = dimensions.depth / 1000
    height = dimensions.height / 1000
    values = {
        "volume": width * depth * height * 423.776,
        "width_depth_area": width * depth,
        "width_height_area": width * height,
        "surface_area": 2 * (width * depth + width * height + depth * height),
        "perimeter_length": 2 * (width + depth),
        "height_length": height,
        "fixed": 1.0,
    }
    return values[basis]


def estimate_quantities(
    furniture_type: str,
    dimensions: FurnitureDimensions,
    components: list[GeneratedBOMItem],
) -> list[EstimatedQuantityItem]:
    rules = QUANTITY_RULE_CATALOG[furniture_type]
    estimates = []
    for component in components:
        rule = rules.get(component.component)
        if rule is None:
            raise UnsupportedBOMComponentError(
                f"Component '{component.component}' is not valid for {furniture_type}."
            )
        quantity = max(round(_basis_value(rule.basis, dimensions) * rule.multiplier, 3), 0.001)
        estimates.append(
            EstimatedQuantityItem(
                component=component.component,
                material=component.recommended_material,
                category=component.category,
                estimated_quantity=quantity,
                unit=rule.unit,
            )
        )
    return estimates
