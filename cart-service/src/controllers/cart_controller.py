from fastapi import APIRouter, Depends, Header, status
from src.dto.cart_dto import AddCartItemDTO, UpdateCartItemDTO, CartResponseDTO, SuccessResponse
from src.services.cart_service import CartService
from src.repositories.cart_repository import DynamoDBCartRepository

router = APIRouter(prefix="/v1/cart", tags=["Cart"])

def get_cart_service() -> CartService:
    repo = DynamoDBCartRepository()
    return CartService(repo)

@router.get("", response_model=SuccessResponse[CartResponseDTO])
def get_cart(x_user_id: str = Header(...), service: CartService = Depends(get_cart_service)):
    data = service.get_cart(x_user_id)
    return {"success": True, "data": data}

@router.post("/items", response_model=SuccessResponse[CartResponseDTO])
def add_to_cart(dto: AddCartItemDTO, x_user_id: str = Header(...), service: CartService = Depends(get_cart_service)):
    data = service.add_item(x_user_id, dto)
    return {"success": True, "data": data}

@router.patch("/items/{product_id}", response_model=SuccessResponse[CartResponseDTO])
def update_cart_item(product_id: str, dto: UpdateCartItemDTO, x_user_id: str = Header(...), service: CartService = Depends(get_cart_service)):
    data = service.update_item(x_user_id, product_id, dto)
    return {"success": True, "data": data}

@router.delete("/items/{product_id}", response_model=SuccessResponse[CartResponseDTO])
def remove_from_cart(product_id: str, x_user_id: str = Header(...), service: CartService = Depends(get_cart_service)):
    data = service.remove_item(x_user_id, product_id)
    return {"success": True, "data": data}

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(x_user_id: str = Header(...), service: CartService = Depends(get_cart_service)):
    service.clear_cart(x_user_id)
    return None