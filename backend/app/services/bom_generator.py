"""Catalog-driven, non-persistent structured BOM generation."""

from dataclasses import dataclass

from app.schemas.bom import GeneratedBOMItem
from app.schemas.material import MaterialRecommendation


@dataclass(frozen=True)
class ComponentTemplate:
    component: str
    preferred_priority: str = "Primary"
    material_index: int = 0
    unit: str = "piece"


BOM_TEMPLATE_CATALOG = {
    "chair": [
        ComponentTemplate("Frame", "Primary", 0),
        ComponentTemplate("Seat", "Primary", 1),
        ComponentTemplate("Backrest", "Primary", 1),
        ComponentTemplate("Legs", "Primary", 0, "set"),
        ComponentTemplate("Fasteners", "Alternative", 0, "set"),
        ComponentTemplate("Finish", "Alternative", 1, "application"),
    ],
    "bed": [
        ComponentTemplate("Headboard", "Primary", 0),
        ComponentTemplate("Footboard", "Primary", 1),
        ComponentTemplate("Rails", "Primary", 0, "set"),
        ComponentTemplate("Slats", "Primary", 1, "set"),
        ComponentTemplate("Legs", "Alternative", 0, "set"),
        ComponentTemplate("Hardware", "Alternative", 1, "set"),
    ],
    "sofa": [
        ComponentTemplate("Frame", "Primary", 0),
        ComponentTemplate("Foam", "Primary", 1, "piece"),
        ComponentTemplate("Fabric", "Alternative", 0, "meter"),
        ComponentTemplate("Legs", "Primary", 0, "set"),
        ComponentTemplate("Fasteners", "Alternative", 1, "set"),
    ],
    "dining_table": [
        ComponentTemplate("Tabletop", "Primary", 0),
        ComponentTemplate("Frame", "Primary", 1, "set"),
        ComponentTemplate("Legs", "Primary", 0, "set"),
        ComponentTemplate("Fasteners", "Alternative", 0, "set"),
        ComponentTemplate("Finish", "Alternative", 1, "application"),
    ],
    "lamp_shade": [
        ComponentTemplate("Shade", "Primary", 0),
        ComponentTemplate("Frame", "Primary", 1),
        ComponentTemplate("Holder", "Alternative", 0),
        ComponentTemplate("Base", "Alternative", 1),
        ComponentTemplate("Electrical Hardware", "Alternative", 0, "set"),
    ],
}


def generate_bom(furniture_type: str, materials: list[MaterialRecommendation]) -> list[GeneratedBOMItem]:
    grouped = {
        "Primary": [material for material in materials if material.priority == "Primary"],
        "Alternative": [material for material in materials if material.priority == "Alternative"],
    }
    primary_materials = grouped["Primary"]
    components = []
    for template in BOM_TEMPLATE_CATALOG[furniture_type]:
        candidates = grouped[template.preferred_priority] or primary_materials
        material = candidates[template.material_index % len(candidates)]
        components.append(
            GeneratedBOMItem(
                component=template.component,
                recommended_material=material.name,
                category=material.category,
                source=f"{material.priority} Recommendation",
                unit=template.unit,
                quantity=None,
            )
        )
    return components
