"""WUE ORM models.

Importing this package registers all application tables with ``Base.metadata``. It
does not create tables or connect to PostgreSQL.
"""

from .estimate import Estimate
from .furniture_material import FurnitureMaterial
from .furniture_type import FurnitureType
from .inventory import Inventory
from .material import Material
from .phase7_estimate_snapshot import Phase7EstimateSnapshot
from .quotation import Quotation
from .quotation_item import QuotationItem
from .user import User

__all__ = [
    "Estimate",
    "FurnitureMaterial",
    "FurnitureType",
    "Inventory",
    "Material",
    "Phase7EstimateSnapshot",
    "Quotation",
    "QuotationItem",
    "User",
]
