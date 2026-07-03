import boto3
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from botocore.exceptions import ClientError
from src.models.payment import Payment
from src.exceptions.app_exceptions import DatabaseError
from src.utils.logger import get_logger

logger = get_logger("PaymentRepository")

class DynamoDBPaymentRepository:
    def __init__(self):
        # Use IAM Role credentials, set the company region
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
        
        # Point to the new company table with the _abd suffix
        self.table = self.dynamodb.Table('payments_abd')

    def _to_item(self, payment: Payment) -> dict:
        return {
            'paymentId': payment.payment_id,
            'orderId': payment.order_id,
            'userId': payment.user_id,
            'amount': Decimal(str(payment.amount)),
            'currency': payment.currency,
            'status': payment.status,
            'provider': payment.provider,
            'providerTxId': payment.provider_transaction_id,
            'createdAt': payment.created_at.isoformat(),
            'updatedAt': payment.updated_at.isoformat()
        }

    def _to_entity(self, item: dict) -> Payment:
        return Payment(
            payment_id=item['paymentId'],
            order_id=item['orderId'],
            user_id=item['userId'],
            amount=float(item['amount']),
            currency=item['currency'],
            status=item['status'],
            provider=item['provider'],
            provider_transaction_id=item.get('providerTxId'),
            created_at=datetime.fromisoformat(item['createdAt']),
            updated_at=datetime.fromisoformat(item['updatedAt'])
        )

    def save(self, payment: Payment) -> Payment:
        try:
            self.table.put_item(Item=self._to_item(payment))
            return payment
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to save payment record")

    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        try:
            response = self.table.get_item(Key={'paymentId': payment_id})
            item = response.get('Item')
            if not item:
                return None
            return self._to_entity(item)
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to fetch payment record")

    def get_by_provider_tx_id(self, provider_tx_id: str) -> Optional[Payment]:
        # Using a scan here for simplicity, but in production, create a GSI on providerTxId
        try:
            response = self.table.scan(
                FilterExpression="providerTxId = :txId",
                ExpressionAttributeValues={":txId": provider_tx_id}
            )
            items = response.get('Items', [])
            if not items:
                return None
            return self._to_entity(items[0])
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to fetch payment by transaction ID")