import boto3
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from botocore.exceptions import ClientError
from src.models.order import Order, OrderItem
from src.exceptions.app_exceptions import DatabaseError
from src.utils.logger import get_logger

logger = get_logger("OrderRepository")

class DynamoDBOrderRepository:
    def __init__(self):
        # Use IAM Role credentials, set the company region
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
        
        # Point to the new company table with the _abd suffix
        self.table = self.dynamodb.Table('orders_abd')

    def _to_item(self, order: Order) -> dict:
        items_list = []
        for item in order.items:
            items_list.append({
                'productId': item.product_id,
                'name': item.name,
                'price': Decimal(str(item.price)),
                'quantity': item.quantity
            })
            
        return {
            'orderId': order.order_id,
            'userId': order.user_id,
            'items': items_list,
            'totalAmount': Decimal(str(order.total_amount)),
            'currency': order.currency,
            'status': order.status,
            'createdAt': order.created_at.isoformat(),
            'updatedAt': order.updated_at.isoformat()
        }

    def _to_entity(self, item: dict) -> Order:
        items = []
        for i in item.get('items', []):
            items.append(OrderItem(
                product_id=i['productId'],
                name=i['name'],
                price=float(i['price']),
                quantity=int(i['quantity'])
            ))
            
        return Order(
            order_id=item['orderId'],
            user_id=item['userId'],
            items=items,
            total_amount=float(item['totalAmount']),
            currency=item['currency'],
            status=item['status'],
            created_at=datetime.fromisoformat(item['createdAt']),
            updated_at=datetime.fromisoformat(item['updatedAt'])
        )

    def save(self, order: Order) -> Order:
        try:
            self.table.put_item(Item=self._to_item(order))
            return order
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to save order")

    def get_by_id(self, order_id: str) -> Optional[Order]:
        try:
            response = self.table.get_item(Key={'orderId': order_id})
            item = response.get('Item')
            return self._to_entity(item) if item else None
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to fetch order")

    def get_by_user_id(self, user_id: str) -> List[Order]:
        try:
            response = self.table.query(
                IndexName='UserIdIndex',
                KeyConditionExpression='userId = :uid',
                ExpressionAttributeValues={':uid': user_id}
            )
            return [self._to_entity(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to fetch user orders")