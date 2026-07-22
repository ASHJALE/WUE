"""Read-only dynamic Bill of Materials calculation service."""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.estimate import Estimate
from app.models.furniture_material import FurnitureMaterial
from app.models.material import Material
from app.schemas.calculation import (
    AlternativeMaterialPreview,
    BOMPreviewItem,
    BOMPreviewRead,
    InventoryAvailabilityRead,
)

QUANTITY_QUANTUM = Decimal("0.001")
MONEY_QUANTUM = Decimal("0.01")
ONE_HUNDRED = Decimal("100")
ZERO_QUANTITY = Decimal("0.000")


class BOMPreviewNotFoundError(Exception):
    """Raised when the requested estimate does not exist."""


class BOMPreviewConflictError(Exception):
    """Raised when valid state lacks required BOM configuration."""


def _quantity(value: Decimal) -> Decimal:
    return value.quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _availability(inventory, required_quantity: Decimal) -> InventoryAvailabilityRead:
    if inventory is None:
        quantity_on_hand = ZERO_QUANTITY
        reorder_level = ZERO_QUANTITY
        inventory_id = None
    else:
        quantity_on_hand = _quantity(inventory.quantity_available)
        reorder_level = _quantity(inventory.reorder_level)
        inventory_id = inventory.id

    shortage = _quantity(max(required_quantity - quantity_on_hand, ZERO_QUANTITY))
    return InventoryAvailabilityRead(
        inventory_id=inventory_id,
        quantity_on_hand=quantity_on_hand,
        reorder_level=reorder_level,
        shortage_quantity=shortage,
        is_available=quantity_on_hand >= required_quantity,
    )


def calculate_bom_preview(db: Session, estimate_id: int) -> BOMPreviewRead:
    """Calculate current BOM costs and availability without persisting anything."""
    estimate = db.scalar(
        select(Estimate)
        .options(joinedload(Estimate.selected_furniture_type))
        .where(Estimate.id == estimate_id)
    )
    if estimate is None:
        raise BOMPreviewNotFoundError("Estimate not found.")
    if estimate.selected_furniture_type_id is None:
        raise BOMPreviewConflictError(
            "The estimate must have a selected furniture type before BOM calculation."
        )
    if estimate.selected_furniture_type is None:
        raise BOMPreviewConflictError("The selected furniture type does not exist.")

    rows = list(
        db.scalars(
            select(FurnitureMaterial)
            .options(
                joinedload(FurnitureMaterial.material).joinedload(Material.inventory),
                joinedload(FurnitureMaterial.material)
                .joinedload(Material.alternative_material)
                .joinedload(Material.inventory),
            )
            .where(
                FurnitureMaterial.furniture_type_id
                == estimate.selected_furniture_type_id
            )
            .order_by(FurnitureMaterial.id)
        )
    )
    if not rows:
        raise BOMPreviewConflictError(
            "No BOM template is configured for the selected furniture type."
        )

    items: list[BOMPreviewItem] = []
    material_total = Decimal("0.00")
    has_inventory_shortage = False

    for row in rows:
        material = row.material
        base_quantity = _quantity(row.quantity_required)
        wastage_percentage = row.wastage_percentage.quantize(
            MONEY_QUANTUM, rounding=ROUND_HALF_UP
        )
        wastage_quantity = _quantity(
            base_quantity * (wastage_percentage / ONE_HUNDRED)
        )
        required_quantity = _quantity(base_quantity + wastage_quantity)
        current_unit_price = _money(material.current_unit_price)
        line_total = _money(required_quantity * current_unit_price)
        inventory = _availability(material.inventory, required_quantity)
        has_inventory_shortage = has_inventory_shortage or not inventory.is_available

        direct_alternative = None
        alternative = material.alternative_material
        if alternative is not None:
            alternative_inventory = _availability(
                alternative.inventory, required_quantity
            )
            direct_alternative = AlternativeMaterialPreview(
                alternative_material_id=alternative.id,
                alternative_material_name=alternative.name,
                alternative_unit=alternative.unit,
                alternative_current_unit_price=_money(
                    alternative.current_unit_price
                ),
                alternative_inventory_id=alternative_inventory.inventory_id,
                alternative_quantity_on_hand=alternative_inventory.quantity_on_hand,
                alternative_shortage_quantity=alternative_inventory.shortage_quantity,
                alternative_is_available=alternative_inventory.is_available,
                estimated_alternative_line_total=_money(
                    required_quantity * alternative.current_unit_price
                ),
            )

        items.append(
            BOMPreviewItem(
                furniture_material_id=row.id,
                material_id=material.id,
                material_name=material.name,
                unit=material.unit,
                base_quantity=base_quantity,
                wastage_percentage=wastage_percentage,
                wastage_quantity=wastage_quantity,
                required_quantity=required_quantity,
                current_unit_price=current_unit_price,
                line_total=line_total,
                inventory=inventory,
                direct_alternative=direct_alternative,
            )
        )
        material_total += line_total

    return BOMPreviewRead(
        estimate_id=estimate.id,
        furniture_type_id=estimate.selected_furniture_type.id,
        furniture_type_name=estimate.selected_furniture_type.name,
        material_total=_money(material_total),
        has_inventory_shortage=has_inventory_shortage,
        item_count=len(items),
        items=items,
    )
