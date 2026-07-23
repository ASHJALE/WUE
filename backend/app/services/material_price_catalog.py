"""Configurable preliminary Philippine-peso material prices for Phase 7.

These values are workflow placeholders, not supplier quotations. Administrators
or a future supplier integration may replace the catalog without changing cost
calculation logic.
"""

from decimal import Decimal

MATERIAL_PRICE_CATALOG: dict[tuple[str, str], Decimal] = {
    ("Mahogany", "board_foot"): Decimal("180.00"),
    ("Marine Plywood", "square_meter"): Decimal("720.00"),
    ("Mahogany", "meter"): Decimal("210.00"),
    ("Pine Wood", "set"): Decimal("260.00"),
    ("MDF", "application"): Decimal("190.00"),
    ("Mahogany", "square_meter"): Decimal("1450.00"),
    ("Hardwood Plywood", "square_meter"): Decimal("850.00"),
    ("Pine", "meter"): Decimal("130.00"),
    ("MDF", "set"): Decimal("310.00"),
    ("Kiln-dried Wood", "board_foot"): Decimal("165.00"),
    ("High Density Foam", "square_meter"): Decimal("980.00"),
    ("Ordinary Foam", "square_meter"): Decimal("520.00"),
    ("Kiln-dried Wood", "set"): Decimal("780.00"),
    ("Plywood", "set"): Decimal("430.00"),
    ("Narra", "square_meter"): Decimal("2350.00"),
    ("Tempered Glass", "board_foot"): Decimal("490.00"),
    ("Narra", "meter"): Decimal("340.00"),
    ("Mahogany", "set"): Decimal("690.00"),
    ("Marine Plywood", "application"): Decimal("240.00"),
    ("Bamboo", "square_meter"): Decimal("380.00"),
    ("Rattan", "meter"): Decimal("160.00"),
    ("PVC", "piece"): Decimal("95.00"),
    ("Acrylic", "piece"): Decimal("230.00"),
    ("PVC", "set"): Decimal("275.00"),
}
