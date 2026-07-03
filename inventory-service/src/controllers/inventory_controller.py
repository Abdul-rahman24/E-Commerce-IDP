from fastapi import APIRouter, Depends, status
from src.dto.inventory_dto import InventoryResponseDTO, InventoryTransactionDTO, SuccessResponse
from src.services.inventory_service import InventoryService
from src.repositories.inventory_repository import DynamoDBInventoryRepository
from src.dto.inventory_dto import InventoryResponseDTO, InventoryTransactionDTO, InitializeInventoryDTO, SuccessResponse

router = APIRouter(prefix="/v1/inventory", tags=["Inventory"])

def get_inventory_service() -> InventoryService:
    repo = DynamoDBInventoryRepository()
    return InventoryService(repo)

@router.get("/{product_id}", response_model=SuccessResponse[InventoryResponseDTO])
def get_inventory(product_id: str, service: InventoryService = Depends(get_inventory_service)):
    data = service.get_inventory(product_id)
    return {"success": True, "data": data}

@router.post("/reserve", response_model=SuccessResponse[InventoryResponseDTO])
def reserve_inventory(dto: InventoryTransactionDTO, service: InventoryService = Depends(get_inventory_service)):
    data = service.reserve_stock(dto)
    return {"success": True, "data": data}

@router.post("/release", response_model=SuccessResponse[InventoryResponseDTO])
def release_inventory(dto: InventoryTransactionDTO, service: InventoryService = Depends(get_inventory_service)):
    data = service.release_stock(dto)
    return {"success": True, "data": data}

@router.post("/deduct", response_model=SuccessResponse[InventoryResponseDTO])
def deduct_inventory(dto: InventoryTransactionDTO, service: InventoryService = Depends(get_inventory_service)):
    data = service.deduct_stock(dto)
    return {"success": True, "data": data}

@router.post("/restock", response_model=SuccessResponse[InventoryResponseDTO])
def restock_inventory(dto: InventoryTransactionDTO, service: InventoryService = Depends(get_inventory_service)):
    data = service.restock(dto)
    return {"success": True, "data": data}

@router.post("/initialize", response_model=SuccessResponse[InventoryResponseDTO])
def initialize_inventory(dto: InitializeInventoryDTO, service: InventoryService = Depends(get_inventory_service)):
    data = service.initialize_stock(dto.product_id)
    return {"success": True, "data": data}