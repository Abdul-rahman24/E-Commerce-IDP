from fastapi import APIRouter, Depends, Header
from typing import List
from src.dto.order_dto import OrderResponseDTO, OrderStatusUpdateDTO, SuccessResponse
from src.services.order_service import OrderService
from src.repositories.order_repository import DynamoDBOrderRepository

router = APIRouter(prefix="/v1/orders", tags=["Orders"])

def get_order_service() -> OrderService:
    repo = DynamoDBOrderRepository()
    return OrderService(repo)

@router.post("", response_model=SuccessResponse[OrderResponseDTO])
def create_order(x_user_id: str = Header(...), service: OrderService = Depends(get_order_service)):
    # Creates order directly from the user's cart
    data = service.create_order_from_cart(x_user_id)
    return {"success": True, "data": data}

@router.get("/{order_id}", response_model=SuccessResponse[OrderResponseDTO])
def get_order(order_id: str, service: OrderService = Depends(get_order_service)):
    data = service.get_order(order_id)
    return {"success": True, "data": data}

@router.get("/user/{user_id}", response_model=SuccessResponse[List[OrderResponseDTO]])
def get_user_orders(user_id: str, service: OrderService = Depends(get_order_service)):
    data = service.get_user_orders(user_id)
    return {"success": True, "data": data}

@router.patch("/{order_id}/status", response_model=SuccessResponse[OrderResponseDTO])
def update_order_status(order_id: str, dto: OrderStatusUpdateDTO, service: OrderService = Depends(get_order_service)):
    data = service.update_status(order_id, dto)
    return {"success": True, "data": data}

@router.patch("/{order_id}/cancel", response_model=SuccessResponse[OrderResponseDTO])
def cancel_order(order_id: str, service: OrderService = Depends(get_order_service)):
    data = service.cancel_order(order_id)
    return {"success": True, "data": data}