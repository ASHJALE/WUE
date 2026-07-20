"""WUE ORM models.

Importing this package registers all eight tables with ``Base.metadata``. It
does not create tables or connect to PostgreSQL.
"""

from .estimate import Estimate
from .furniture_material import FurnitureMaterial
from .furniture_type import FurnitureType
from .inventory import Inventory
from .material import Material
from .quotation import Quotation
from .quotation_item import QuotationItem
from .user import User

__all__ = [
    "Estimate",
    "FurnitureMaterial",
    "FurnitureType",
    "Inventory",
    "Material",
    "Quotation",
    "QuotationItem",
    "User",
]
