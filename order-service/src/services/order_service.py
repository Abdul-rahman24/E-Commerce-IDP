import os
import uuid
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import List
from dotenv import load_dotenv
from src.repositories.order_repository import DynamoDBOrderRepository
from src.models.order import Order, OrderItem
from src.dto.order_dto import OrderResponseDTO, OrderStatusUpdateDTO, OrderItemResponseDTO
from src.exceptions.app_exceptions import NotFoundError, BadRequestError, DatabaseError, ConflictError
from src.utils.logger import get_logger

logger = get_logger("OrderService")

# Load environment variables
load_dotenv()
CART_SERVICE_URL = os.environ.get("CART_SERVICE_URL")
INVENTORY_SERVICE_URL = os.environ.get("INVENTORY_SERVICE_URL")

class OrderService:
    def __init__(self, repository: DynamoDBOrderRepository):
        self.repository = repository

    def _build_response_dto(self, order: Order) -> OrderResponseDTO:
        items = [OrderItemResponseDTO(**item.__dict__) for item in order.items]
        return OrderResponseDTO(
            order_id=order.order_id,
            user_id=order.user_id,
            items=items,
            total_amount=order.total_amount,
            currency=order.currency,
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at
        )

    def create_order_from_cart(self, user_id: str) -> OrderResponseDTO:
        # 1. Fetch Cart (GET Request)
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

        # 2. Reserve Inventory for each item (POST Request)
        for item in cart_data['items']:
            payload = {"product_id": item['product_id'], "quantity": item['quantity']}
            data = json.dumps(payload).encode('utf-8')
            
            inv_req = urllib.request.Request(
                f"{INVENTORY_SERVICE_URL}/reserve", 
                data=data, 
                headers={'Content-Type': 'application/json'}
            )
            
            try:
                with urllib.request.urlopen(inv_req, timeout=5) as response:
                    if response.getcode() != 200:
                        raise ConflictError(f"Insufficient stock for {item['name']}")
            except urllib.error.HTTPError as e:
                # If inventory service explicitly returns an error code like 400 or 500
                logger.error(f"Inventory HTTP error: {e.code}")
                raise ConflictError(f"Insufficient stock for {item['name']}")
            except urllib.error.URLError as e:
                logger.error(f"Inventory connection error: {str(e)}")
                raise DatabaseError("Inventory service is unreachable.")

        # 3. Create Order
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

        # 4. Clear the Cart (DELETE Request)
        clear_req = urllib.request.Request(
            CART_SERVICE_URL, 
            headers=headers, 
            method='DELETE'
        )
        try:
            with urllib.request.urlopen(clear_req, timeout=5):
                pass # Successfully cleared
        except urllib.error.URLError as e:
            logger.warning(f"Failed to clear cart for user {user_id}: {str(e)}. Order {order.order_id} created.")

        return self._build_response_dto(saved_order)

    def get_order(self, order_id: str) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
        return self._build_response_dto(order)

    def get_user_orders(self, user_id: str) -> List[OrderResponseDTO]:
        orders = self.repository.get_by_user_id(user_id)
        return [self._build_response_dto(o) for o in orders]

    def update_status(self, order_id: str, dto: OrderStatusUpdateDTO) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
            
        order.status = dto.status.upper()
        order.updated_at = datetime.now(timezone.utc)
        
        # If order is shipped/completed, deduct inventory permanently (POST Request)
        if order.status in ["SHIPPED", "COMPLETED"]:
            for item in order.items:
                payload = {"product_id": item.product_id, "quantity": item.quantity}
                data = json.dumps(payload).encode('utf-8')
                deduct_req = urllib.request.Request(
                    f"{INVENTORY_SERVICE_URL}/deduct", 
                    data=data, 
                    headers={'Content-Type': 'application/json'}
                )
                try:
                    with urllib.request.urlopen(deduct_req, timeout=5):
                        pass
                except Exception as e:
                    logger.error(f"Failed to deduct stock for {item.product_id}: {str(e)}")

        return self._build_response_dto(self.repository.save(order))

    def cancel_order(self, order_id: str) -> OrderResponseDTO:
        order = self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundError("Order not found")
            
        if order.status in ["SHIPPED", "COMPLETED"]:
            raise BadRequestError("Cannot cancel a shipped or completed order.")
            
        order.status = "CANCELLED"
        order.updated_at = datetime.now(timezone.utc)
        
        # Release the reserved inventory back to available stock (POST Request)
        for item in order.items:
            payload = {"product_id": item.product_id, "quantity": item.quantity}
            data = json.dumps(payload).encode('utf-8')
            release_req = urllib.request.Request(
                f"{INVENTORY_SERVICE_URL}/release", 
                data=data, 
                headers={'Content-Type': 'application/json'}
            )
            try:
                with urllib.request.urlopen(release_req, timeout=5):
                    pass
            except Exception as e:
                logger.error(f"Failed to release stock for {item.product_id}: {str(e)}")

        return self._build_response_dto(self.repository.save(order))