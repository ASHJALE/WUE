"""Catalog-driven furniture material recommendations.

This service is intentionally separate from BOM, inventory, and pricing logic.
Catalog entries can be edited or extended without changing the API router.
"""

from app.schemas.material import MaterialRecommendation

DISPLAY_NAMES = {
    "chair": "Chair",
    "bed": "Bed",
    "sofa": "Sofa",
    "dining_table": "Dining Table",
    "lamp_shade": "Lamp Shade",
}

RECOMMENDATION_CATALOG = {
    "chair": {
        "primary": [
            ("Mahogany", "Solid Wood", "Premium", "Durable hardwood suited to strong chair frames and refined finishes."),
            ("Marine Plywood", "Engineered Wood", "Standard", "Moisture-resistant sheet material suitable for stable seats and back panels."),
        ],
        "alternatives": [
            ("Pine Wood", "Softwood", "Economy", "A lightweight and workable option for cost-conscious chair construction."),
            ("MDF", "Engineered Wood", "Economy", "Provides a smooth surface for painted decorative chair components."),
        ],
    },
    "bed": {
        "primary": [
            ("Mahogany", "Solid Wood", "Premium", "Offers strength and long-term durability for bed frames and headboards."),
            ("Hardwood Plywood", "Engineered Wood", "Standard", "Provides stable structural panels with good load-bearing performance."),
        ],
        "alternatives": [
            ("Pine", "Softwood", "Economy", "An affordable, workable material for lightweight bed-frame components."),
            ("MDF", "Engineered Wood", "Economy", "Suitable for non-structural headboard panels with smooth painted finishes."),
        ],
    },
    "sofa": {
        "primary": [
            ("Kiln-dried Wood", "Frame Material", "Premium", "Reduced moisture helps create a stable and durable upholstered sofa frame."),
            ("High Density Foam", "Upholstery", "Premium", "Provides resilient seating support and better shape retention."),
        ],
        "alternatives": [
            ("Ordinary Foam", "Upholstery", "Economy", "A lower-cost cushioning option for light-use seating."),
            ("Plywood", "Engineered Wood", "Standard", "Useful for sofa side, back, and support panels when properly reinforced."),
        ],
    },
    "dining_table": {
        "primary": [
            ("Narra", "Solid Wood", "Premium", "A durable hardwood with an attractive grain for long-lasting table surfaces."),
            ("Tempered Glass", "Glass", "Premium", "Creates a clean tabletop surface with improved impact and heat resistance."),
        ],
        "alternatives": [
            ("Mahogany", "Solid Wood", "Premium", "A strong and workable substitute for dining-table tops and frames."),
            ("Marine Plywood", "Engineered Wood", "Standard", "A stable moisture-resistant alternative when finished with veneer or laminate."),
        ],
    },
    "lamp_shade": {
        "primary": [
            ("Bamboo", "Natural Fiber", "Standard", "Lightweight natural strips support warm, breathable lamp-shade designs."),
            ("Rattan", "Natural Fiber", "Premium", "Flexible woven fibers provide decorative texture and diffuse light effectively."),
        ],
        "alternatives": [
            ("PVC", "Polymer", "Economy", "A lightweight and moisture-resistant option for simple shade panels."),
            ("Acrylic", "Polymer", "Standard", "Offers durable translucent panels in a range of colors and finishes."),
        ],
    },
}


def recommend_materials(furniture_type: str) -> list[MaterialRecommendation]:
    catalog = RECOMMENDATION_CATALOG[furniture_type]
    recommendations = []
    for priority_key, priority_label in (("primary", "Primary"), ("alternatives", "Alternative")):
        recommendations.extend(
            MaterialRecommendation(
                name=name,
                category=category,
                priority=priority_label,
                quality=quality,
                reason=reason,
            )
            for name, category, quality, reason in catalog[priority_key]
        )
    return recommendations
