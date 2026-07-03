import boto3
import time
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from botocore.exceptions import ClientError
from src.models.cart import Cart, CartItem
from src.exceptions.app_exceptions import DatabaseError
from src.utils.logger import get_logger

logger = get_logger("CartRepository")

class DynamoDBCartRepository:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
        
        # Point to the new company table with the _abd suffix
        self.table = self.dynamodb.Table('cart_abd')
        self.TTL_SECONDS = 604800 # 7 days

    def _to_item(self, cart: Cart) -> dict:
        items_dict = {}
        for pid, item in cart.items.items():
            items_dict[pid] = {
                'productId': item.product_id,
                'name': item.name,
                'price': Decimal(str(item.price)),
                'quantity': item.quantity
            }
            
        return {
            'userId': cart.user_id,
            'items': items_dict,
            'updatedAt': cart.updated_at.isoformat(),
            'expiresAt': int(time.time()) + self.TTL_SECONDS
        }

    def _to_entity(self, item: dict) -> Cart:
        items = {}
        for pid, data in item.get('items', {}).items():
            items[pid] = CartItem(
                product_id=data['productId'],
                name=data['name'],
                price=float(data['price']),
                quantity=int(data['quantity'])
            )
            
        return Cart(
            user_id=item['userId'],
            items=items,
            updated_at=datetime.fromisoformat(item['updatedAt']),
            expires_at=int(item.get('expiresAt', 0))
        )

    def get_cart(self, user_id: str) -> Optional[Cart]:
        try:
            response = self.table.get_item(Key={'userId': user_id})
            item = response.get('Item')
            if not item:
                return None
                
            # Check if TTL has technically passed but AWS hasn't swept it yet
            if int(item.get('expiresAt', 0)) < int(time.time()):
                return None
                
            return self._to_entity(item)
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to fetch cart")

    def save_cart(self, cart: Cart) -> Cart:
        try:
            self.table.put_item(Item=self._to_item(cart))
            return cart
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to save cart")

    def delete_cart(self, user_id: str) -> None:
        try:
            self.table.delete_item(Key={'userId': user_id})
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to delete cart")