from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

@dataclass
class Product:
    product_id: str
    sku: str
    name: str
    description: str
    category: str
    brand: str
    price: float
    currency: str
    status: str
    images: List[str]
    attributes: Dict[str, Any]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime