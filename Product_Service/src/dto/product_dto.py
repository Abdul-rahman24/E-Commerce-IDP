from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from typing import TypeVar, Generic

class CreateProductDTO(BaseModel):
    sku: str = Field(..., min_length=3)
    name: str = Field(..., min_length=1)
    description: str
    category: str
    brand: str
    price: float = Field(..., gt=0)
    currency: str = "USD"
    images: List[str] = []
    attributes: Dict[str, Any] = {}

class UpdateProductDTO(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    status: Optional[str] = None

class ProductResponseDTO(BaseModel):
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
    created_at: datetime
    updated_at: datetime

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T