from fastapi import APIRouter, Depends, status
from typing import List
from src.dto.product_dto import CreateProductDTO, UpdateProductDTO, ProductResponseDTO
from src.services.product_service import ProductService
from src.repositories.product_repository import DynamoDBProductRepository

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

# Dependency Injection
def get_product_service() -> ProductService:
    repo = DynamoDBProductRepository()
    return ProductService(repo)

@router.post("/", response_model=ProductResponseDTO, status_code=status.HTTP_201_CREATED)
def create_product(dto: CreateProductDTO, service: ProductService = Depends(get_product_service)):
    return service.create_product(dto)

@router.get("/", response_model=List[ProductResponseDTO])
def get_all_products(service: ProductService = Depends(get_product_service)):
    return service.get_all_products()

@router.get("/{product_id}", response_model=ProductResponseDTO)
def get_product(product_id: str, service: ProductService = Depends(get_product_service)):
    return service.get_product(product_id)

@router.patch("/{product_id}", response_model=ProductResponseDTO)
def update_product(product_id: str, dto: UpdateProductDTO, service: ProductService = Depends(get_product_service)):
    return service.update_product(product_id, dto)

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str, service: ProductService = Depends(get_product_service)):
    service.delete_product(product_id)
    return None