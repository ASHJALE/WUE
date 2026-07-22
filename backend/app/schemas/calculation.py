"""Read-only dynamic BOM calculation response schemas."""

from decimal import Decimal

from pydantic import BaseModel


class InventoryAvailabilityRead(BaseModel):
    inventory_id: int | None
    quantity_on_hand: Decimal
    reorder_level: Decimal
    shortage_quantity: Decimal
    is_available: bool


class AlternativeMaterialPreview(BaseModel):
    alternative_material_id: int
    alternative_material_name: str
    alternative_unit: str
    alternative_current_unit_price: Decimal
    alternative_inventory_id: int | None
    alternative_quantity_on_hand: Decimal
    alternative_shortage_quantity: Decimal
    alternative_is_available: bool
    estimated_alternative_line_total: Decimal


class BOMPreviewItem(BaseModel):
    furniture_material_id: int
    material_id: int
    material_name: str
    unit: str
    base_quantity: Decimal
    wastage_percentage: Decimal
    wastage_quantity: Decimal
    required_quantity: Decimal
    current_unit_price: Decimal
    line_total: Decimal
    inventory: InventoryAvailabilityRead
    direct_alternative: AlternativeMaterialPreview | None


class BOMPreviewRead(BaseModel):
    estimate_id: int
    furniture_type_id: int
    furniture_type_name: str
    material_total: Decimal
    has_inventory_shortage: bool
    item_count: int
    items: list[BOMPreviewItem]
