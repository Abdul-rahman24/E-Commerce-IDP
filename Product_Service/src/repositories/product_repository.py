import boto3
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from src.models.product import Product
from botocore.exceptions import ClientError
from src.exceptions.app_exceptions import DatabaseError
from src.utils.logger import get_logger

logger = get_logger("ProductRepository")

class DynamoDBProductRepository:
    def __init__(self):
        # Automatically uses the credentials from 'aws configure'
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('Products')

    def _to_item(self, product: Product) -> dict:
        return {
            'productId': product.product_id,
            'sku': product.sku,
            'name': product.name,
            'description': product.description,
            'category': product.category,
            'brand': product.brand,
            'price': Decimal(str(product.price)), # DynamoDB requires Decimals for floats
            'currency': product.currency,
            'status': product.status,
            'images': product.images,
            'attributes': product.attributes,
            'is_deleted': product.is_deleted,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat()
        }

    def _to_entity(self, item: dict) -> Product:
        return Product(
            product_id=item['productId'],
            sku=item['sku'],
            name=item['name'],
            description=item['description'],
            category=item['category'],
            brand=item['brand'],
            price=float(item['price']),
            currency=item['currency'],
            status=item['status'],
            images=item.get('images', []),
            attributes=item.get('attributes', {}),
            is_deleted=item.get('is_deleted', False),
            created_at=datetime.fromisoformat(item['created_at']),
            updated_at=datetime.fromisoformat(item['updated_at'])
        )

    def create(self, product: Product) -> Product:
        try:
            self.table.put_item(Item=self._to_item(product))
            logger.info(f"Successfully created product in DB", extra={"productId": product.product_id})
            return product
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {str(e)}", extra={"productId": product.product_id})
            raise DatabaseError("Failed to save product to database")

    def find_by_id(self, product_id: str) -> Optional[Product]:
        try:
            response = self.table.get_item(Key={'productId': product_id})
            item = response.get('Item')
            if item and not item.get('is_deleted'):
                return self._to_entity(item)
            return None
        except ClientError as e:
            logger.error(f"DynamoDB ClientError: {str(e)}", extra={"productId": product_id})
            raise DatabaseError("Failed to retrieve product from database")

    def find_all(self) -> List[Product]:
        # Note: Scan is okay for small catalogs, but in scale, use Secondary Indexes
        response = self.table.scan()
        items = response.get('Items', [])
        return [self._to_entity(item) for item in items if not item.get('is_deleted')]

    def update(self, product: Product) -> Product:
        self.table.put_item(Item=self._to_item(product))
        return product