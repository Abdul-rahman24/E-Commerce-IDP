import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from src.models.inventory import Inventory
from src.exceptions.app_exceptions import DatabaseError, ConflictError, NotFoundError
from src.utils.logger import get_logger

logger = get_logger("InventoryRepository")

class DynamoDBInventoryRepository:
    def __init__(self):
        # Use IAM Role credentials, set the company region
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
        
        # Point to the new company table with the _abd suffix
        self.table = self.dynamodb.Table('inventory_abd')

    def get_by_product_id(self, product_id: str) -> Inventory:
        try:
            response = self.table.get_item(Key={'productId': product_id})
            item = response.get('Item')
            if not item:
                raise NotFoundError(f"Inventory record for product {product_id} not found")
            return Inventory(
                product_id=item['productId'],
                available_quantity=int(item.get('availableQuantity', 0)),
                reserved_quantity=int(item.get('reservedQuantity', 0)),
                updated_at=datetime.fromisoformat(item['updated_at'])
            )
        except ClientError as e:
            logger.error(f"DB Error: {str(e)}")
            raise DatabaseError("Failed to fetch inventory")

    def atomic_update(self, product_id: str, available_delta: int, reserved_delta: int) -> Inventory:
        """Performs a mathematical atomic update on quantities."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            # If we are subtracting available quantity, ensure we don't go below 0
            condition_expr = "attribute_exists(productId)"
            if available_delta < 0:
                condition_expr += " AND availableQuantity >= :min_avail"

            response = self.table.update_item(
                Key={'productId': product_id},
                UpdateExpression="SET availableQuantity = availableQuantity + :avail_val, reservedQuantity = reservedQuantity + :res_val, updated_at = :now",
                ConditionExpression=condition_expr,
                ExpressionAttributeValues={
                    ':avail_val': available_delta,
                    ':res_val': reserved_delta,
                    ':now': now,
                    **( {':min_avail': abs(available_delta)} if available_delta < 0 else {} )
                },
                ReturnValues="ALL_NEW"
            )
            item = response['Attributes']
            return Inventory(
                product_id=item['productId'],
                available_quantity=int(item['availableQuantity']),
                reserved_quantity=int(item['reservedQuantity']),
                updated_at=datetime.fromisoformat(item['updated_at'])
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                raise ConflictError("Insufficient available inventory or record does not exist")
            logger.error(f"DB Update Error: {str(e)}")
            raise DatabaseError("Failed to update inventory")

    def initialize_inventory(self, product_id: str, initial_quantity: int) -> Inventory:
        """Used when a new product is created."""
        now = datetime.now(timezone.utc).isoformat()
        item = {
            'productId': product_id,
            'availableQuantity': initial_quantity,
            'reservedQuantity': 0,
            'updated_at': now
        }
        self.table.put_item(Item=item)
        return Inventory(product_id, initial_quantity, 0, datetime.fromisoformat(now))