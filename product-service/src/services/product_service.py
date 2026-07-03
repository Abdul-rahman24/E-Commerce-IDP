import os
import uuid
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import List
from dotenv import load_dotenv
from src.repositories.product_repository import DynamoDBProductRepository
from src.models.product import Product
from src.dto.product_dto import CreateProductDTO, UpdateProductDTO
from src.exceptions.app_exceptions import NotFoundError
from src.utils.logger import get_logger

logger = get_logger("ProductService")

# Load environment variables
load_dotenv()
INVENTORY_SERVICE_URL = os.environ.get("INVENTORY_SERVICE_URL")
SEARCH_SERVICE_URL = os.environ.get("SEARCH_SERVICE_URL")

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
        
        saved_product = self.repository.create(new_product)

        # 1. Trigger Inventory Initialization
        logger.info(f"Triggering inventory initialization for {saved_product.product_id}")
        inv_payload = {"product_id": saved_product.product_id}
        inv_data = json.dumps(inv_payload).encode('utf-8')
        inv_req = urllib.request.Request(
            f"{INVENTORY_SERVICE_URL}/initialize", 
            data=inv_data, 
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(inv_req, timeout=5) as response:
                if response.getcode() != 200:
                    logger.error(f"Failed to initialize inventory for {saved_product.product_id}. Status: {response.getcode()}")
        except urllib.error.HTTPError as e:
            logger.error(f"Inventory HTTP error: {e.code}")
        except urllib.error.URLError as e:
            logger.error(f"Inventory Service is offline or unreachable: {str(e)}")
        except TimeoutError:
            logger.error(f"Inventory Service request timed out for {saved_product.product_id}")

        # 2. Trigger Search Indexing
        search_payload = {
            "product_id": saved_product.product_id,
            "name": saved_product.name,
            "description": saved_product.description,
            "category": saved_product.category,
            "price": saved_product.price,
            "images": saved_product.images
        }
        search_data = json.dumps(search_payload).encode('utf-8')
        search_req = urllib.request.Request(
            f"{SEARCH_SERVICE_URL}/index",
            data=search_data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(search_req, timeout=5) as response:
                logger.info(f"Triggered search indexing for {saved_product.product_id}")
        except urllib.error.HTTPError as e:
            logger.error(f"Search HTTP error: {e.code}")
        except urllib.error.URLError as e:
            logger.error(f"Search Service is offline or unreachable: {str(e)}")
        except TimeoutError:
            logger.error(f"Search Service request timed out for {saved_product.product_id}")
        
        return saved_product
    
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