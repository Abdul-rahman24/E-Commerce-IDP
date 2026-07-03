import os
import uuid
import json
import boto3
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import List
from dotenv import load_dotenv
from src.repositories.order_repository import DynamoDBOrderRepository
from src.models.order import Order, OrderItem
from src.dto.order_dto import OrderResponseDTO, OrderStatusUpdateDTO, OrderItemResponseDTO
from src.exceptions.app_exceptions import NotFoundError, BadRequestError, DatabaseError
from src.utils.logger import get_logger

logger = get_logger("OrderService")
load_dotenv()

CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL")
ORDER_EVENTS_TOPIC_ARN = os.environ.get("ORDER_EVENTS_TOPIC_ARN")

class OrderService:
    def __init__(self, repository: DynamoDBOrderRepository):
        self.repository = repository
        # Initialize the AWS SNS Client
        self.sns_client = boto3.client('sns')

    def _publish_event(self, event_type: str, order: Order):
        """Helper method to broadcast order events to SNS"""
        if not ORDER_EVENTS_TOPIC_ARN:
            logger.warning("ORDER_EVENTS_TOPIC_ARN not set. Skipping event publish.")
            return

        payload = {
            "event_type": event_type,
            "order_id": order.order_id,
            "user_id": order.user_id,
            "status": order.status,
            "items": [
                {"product_id": item.product_id, "quantity": item.quantity, "name": item.name} 
                for item in order.items
            ]
        }
        
        try:
            self.sns_client.publish(
                TopicArn=ORDER_EVENTS_TOPIC_ARN,
                Message=json.dumps(payload),
                Subject=f"OrderEvent:{event_type}"
            )
            logger.info(f"Successfully broadcasted {event_type} for Order {order.order_id}")
        except Exception as e:
            logger.error(f"Failed to publish SNS event for order {order.order_id}: {str(e)}")

    def create_order_from_cart(self, user_id: str) -> OrderResponseDTO:
        # 1. Fetch Cart synchronously via GET (We MUST read what items they want!)
        headers = {"x-user-id": user_id}
        req = urllib.request.Request(CART_SERVICE_URL, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                resp_body = response.read().decode('utf-8')
                cart_data = json.loads(resp_body).get('data')
                
                if not cart_data or not cart_data.get('items'):
                    raise BadRequestError("Cannot create order: Cart is empty.")
        except urllib.error.URLError as e:
            logger.error(f"Cart service error: {str(e)}")
            raise DatabaseError("Cart service is unreachable.")

        # 2. Build and Save Order to DynamoDB
        order_items = [
            OrderItem(product_id=i['product_id'], name=i['name'], price=i['price'], quantity=i['quantity'])
            for i in cart_data['items']
        ]
        
        order = Order(
            order_id=f"ord_{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            items=order_items,
            total_amount=cart_data['cart_total'],
            currency="USD",
            status="PENDING_PAYMENT",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        saved_order = self.repository.save(order)

        # 3. ASYNC FAN-OUT: Shout into SNS! 
        # (This instantly triggers Inventory Reserve & Cart Cleanup in the background!)
        self._publish_event("ORDER_CREATED", saved_order)

        return self._build_response_dto(saved_order)

    def update_status(self, order_id: str, dto: OrderStatusUpdateDTO) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
            
        order.status = dto.status.upper()
        order.updated_at = datetime.now(timezone.utc)
        saved_order = self.repository.save(order)
        
        # If order is completed or shipped, broadcast event to deduct inventory permanently
        if order.status in ["SHIPPED", "COMPLETED"]:
            self._publish_event("ORDER_COMPLETED", saved_order)

        return self._build_response_dto(saved_order)

    def cancel_order(self, order_id: str) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
            
        if order.status in ["SHIPPED", "COMPLETED"]:
            raise BadRequestError("Cannot cancel a shipped or completed order.")
            
        order.status = "CANCELLED"
        order.updated_at = datetime.now(timezone.utc)
        saved_order = self.repository.save(order)
        
        # Broadcast cancellation so Inventory releases reserved stock back to available
        self._publish_event("ORDER_CANCELLED", saved_order)

        return self._build_response_dto(saved_order)

    def get_order(self, order_id: str) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        return self._build_response_dto(order)

    def get_user_orders(self, user_id: str) -> List[OrderResponseDTO]:
        orders = self.repository.get_by_user_id(user_id)
        return [self._build_response_dto(o) for o in orders]
    
    def _build_response_dto(self, order: Order) -> OrderResponseDTO:
        items = [OrderItemResponseDTO(**item.__dict__) for item in order.items]
        return OrderResponseDTO(
            order_id=order.order_id, user_id=order.user_id, items=items,
            total_amount=order.total_amount, currency=order.currency,
            status=order.status, created_at=order.created_at, updated_at=order.updated_at
        )