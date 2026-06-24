from fastapi import APIRouter, Depends, status
from typing import List
from src.dto.product_dto import CreateProductDTO, UpdateProductDTO, ProductResponseDTO, SuccessResponse
from src.services.product_service import ProductService
from src.repositories.product_repository import DynamoDBProductRepository
from src.utils.logger import get_logger

logger = get_logger("ProductController")
router = APIRouter(prefix="/api/v1/products", tags=["Products"])

def get_product_service() -> ProductService:
    repo = DynamoDBProductRepository()
    return ProductService(repo)

@router.post("/", response_model=SuccessResponse[ProductResponseDTO], status_code=status.HTTP_201_CREATED)
def create_product(dto: CreateProductDTO, service: ProductService = Depends(get_product_service)):
    logger.info("Received request to create product", extra={"sku": dto.sku})
    product = service.create_product(dto)
    return {"success": True, "data": product}

@router.get("/", response_model=List[ProductResponseDTO])
def get_all_products(service: ProductService = Depends(get_product_service)):
    return service.get_all_products()

@router.get("/{product_id}", response_model=SuccessResponse[ProductResponseDTO])
def get_product(product_id: str, service: ProductService = Depends(get_product_service)):
    logger.info("Received request to fetch product", extra={"productId": product_id})
    product = service.get_product(product_id)
    return {"success": True, "data": product}

@router.patch("/{product_id}", response_model=ProductResponseDTO)
def update_product(product_id: str, dto: UpdateProductDTO, service: ProductService = Depends(get_product_service)):
    return service.update_product(product_id, dto)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str, service: ProductService = Depends(get_product_service)):
    logger.info("Received request to delete product", extra={"productId": product_id})
    service.delete_product(product_id)
    return None