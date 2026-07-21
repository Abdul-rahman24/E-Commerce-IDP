from fastapi import APIRouter, Depends, Header, HTTPException
from typing import List
from src.dto.order_dto import OrderResponseDTO, OrderStatusUpdateDTO, SuccessResponse
from src.services.order_service import OrderService
from src.repositories.order_repository import DynamoDBOrderRepository
import boto3
from boto3.dynamodb.conditions import Attr
import os

router = APIRouter(prefix="/v1/orders", tags=["Orders"])
dynamodb = boto3.resource('dynamodb')
order_table = dynamodb.Table(os.environ.get('ORDER_TABLE_NAME', 'OrdersTable'))

def get_order_service() -> OrderService:
    repo = DynamoDBOrderRepository()
    return OrderService(repo)

# 1. GET ALL ORDERS FOR LOGGED-IN USER
@router.get("/orders")
async def get_user_orders_by_header(x_user_id: str = Header(...)):
    """Fetch all orders belonging to the authenticated Cognito user."""
    try:
        response = order_table.scan(
            FilterExpression=Attr('user_id').eq(x_user_id) | Attr('userId').eq(x_user_id)
        )
        orders = response.get('Items', [])
        return {"orders": orders}
    except Exception as e:
        print(f"Error fetching orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve order history")

# 2. CREATE ORDER FROM CART
@router.post("", response_model=SuccessResponse[OrderResponseDTO])
def create_order(x_user_id: str = Header(...), service: OrderService = Depends(get_order_service)):
    data = service.create_order_from_cart(x_user_id)
    return {"success": True, "data": data}

# 3. GET SINGLE ORDER BY ID
@router.get("/{order_id}", response_model=SuccessResponse[OrderResponseDTO])
def get_order(order_id: str, service: OrderService = Depends(get_order_service)):
    data = service.get_order(order_id)
    return {"success": True, "data": data}

# 4. GET ORDERS BY USER ID PARAM
@router.get("/user/{user_id}", response_model=SuccessResponse[List[OrderResponseDTO]])
def get_user_orders_by_param(user_id: str, service: OrderService = Depends(get_order_service)):
    data = service.get_user_orders(user_id)
    return {"success": True, "data": data}

# 💡 5. THE SINGLE, UNIFIED ORDER STATUS UPDATE ROUTE (No Duplicates!)
@router.patch("/{order_id}/status")
async def update_order_status(order_id: str, payload: OrderStatusUpdateDTO, x_user_id: str = Header(...)):
    """Update the status of an order after a successful payment handshake."""
    try:
        # Scan for the order regardless of your exact primary key schema
        response = order_table.scan(
            FilterExpression=Attr('order_id').eq(order_id) | Attr('orderId').eq(order_id)
        )
        items = response.get('Items', [])
        
        if not items:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found in database")
            
        target_order = items[0]
        
        # Modify the status attribute in memory
        target_order['status'] = payload.status
        
        # Overwrite the existing DynamoDB record cleanly in place
        order_table.put_item(Item=target_order)
        
        print(f"✅ Order {order_id} status successfully transitioned to: {payload.status}")
        return {"success": True, "message": f"Order {order_id} updated to {payload.status}", "order": target_order}
        
    except Exception as e:
        print(f"❌ Error updating order status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update order status")

# 6. CANCEL ORDER
@router.patch("/{order_id}/cancel", response_model=SuccessResponse[OrderResponseDTO])
def cancel_order(order_id: str, service: OrderService = Depends(get_order_service)):
    data = service.cancel_order(order_id)
    return {"success": True, "data": data}