import uuid
from datetime import datetime, timezone
from typing import List
from src.repositories.product_repository import DynamoDBProductRepository
from src.models.product import Product
from src.dto.product_dto import CreateProductDTO, UpdateProductDTO
from src.exceptions.app_exceptions import NotFoundError

class ProductService:
    def __init__(self, repository: DynamoDBProductRepository):
        self.repository = repository

    def create_product(self, dto: CreateProductDTO) -> Product:
        new_product = Product(
            product_id=str(uuid.uuid4()),
            sku=dto.sku,
            name=dto.name,
            description=dto.description,
            category=dto.category,
            brand=dto.brand,
            price=dto.price,
            currency=dto.currency,
            status="DRAFT",
            images=dto.images,
            attributes=dto.attributes,
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        return self.repository.create(new_product)

    def get_product(self, product_id: str) -> Product:
        product = self.repository.find_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product with ID {product_id} not found")
        return product

    def get_all_products(self) -> List[Product]:
        return self.repository.find_all()

    def update_product(self, product_id: str, dto: UpdateProductDTO) -> Product:
        product = self.get_product(product_id)
        
        update_data = dto.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(product, key):
                setattr(product, key, value)
                
        product.updated_at = datetime.now(timezone.utc)
        return self.repository.update(product)

    def delete_product(self, product_id: str) -> None:
        product = self.get_product(product_id)
        product.is_deleted = True
        product.updated_at = datetime.now(timezone.utc)
        self.repository.update(product)