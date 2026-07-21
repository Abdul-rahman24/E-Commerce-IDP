from fastapi import APIRouter, Depends, Query
from typing import List
from src.dto.search_dto import IndexProductDTO, SearchResultDTO, SuccessResponse
from src.services.search_service import SearchService
from src.repositories.search_repository import DynamoDBSearchRepository

router = APIRouter(prefix="/v1/search", tags=["Search"])

def get_search_service() -> SearchService:
    repo = DynamoDBSearchRepository()
    return SearchService(repo)

@router.get("", response_model=SuccessResponse[List[SearchResultDTO]])
def search_products(
    q: str = Query(..., description="The search query string (prefix match)"), 
    service: SearchService = Depends(get_search_service)
):
    # Pass the trimmed query to your service layer
    data = service.perform_search(q.trim() if hasattr(q, 'trim') else q.strip())
    return {"success": True, "data": data}

@router.post("/index", response_model=SuccessResponse[str])
def index_product(dto: IndexProductDTO, service: SearchService = Depends(get_search_service)):
    # This endpoint is internal: called by the Product Service when a new product is created
    service.index_product(dto)
    return {"success": True, "data": "Product indexed successfully"}