import boto3
from decimal import Decimal
from typing import List
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from src.models.search_item import SearchItem
from src.exceptions.app_exceptions import DatabaseError
from src.utils.logger import get_logger

logger = get_logger("SearchRepository")

class DynamoDBSearchRepository:
    def __init__(self):
        # Use IAM Role credentials, set the company region
        self.dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
        
        # Point to the new company table with the _abd suffix
        self.table = self.dynamodb.Table('searchindex_abd')

    def index_item(self, item: SearchItem) -> None:
        try:
            self.table.put_item(Item={
                'productId': item.product_id,
                'name': item.name,
                'description': item.description,
                'category': item.category,
                'price': Decimal(str(item.price)),
                'images': item.images,
                'searchTags': item.search_tags
            })
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Failed to index product for search")

    def search(self, query: str) -> List[SearchItem]:
        try:
            # 1. Clean and lowercase the search term
            query_clean = query.strip().lower()
            
            # 2. Keep the existing scan to pull items out of the search index table
            response = self.table.scan()
            
            items = []
            for item in response.get('Items', []):
                # 💡 THE FIX: Extract the product name and make it lowercase
                product_name = str(item.get('name', '')).lower()
                
                # 💡 THE CORE PREFIX LOGIC: Only match if the name STARTS WITH your query!
                if product_name.startswith(query_clean):
                    items.append(SearchItem(
                        product_id=item['productId'],
                        name=item['name'],
                        description=item.get('description', ''),
                        category=item.get('category', ''),
                        price=float(item['price']),
                        images=item.get('images', []),
                        search_tags=item.get('searchTags', '')
                    ))
                    
            return items
        except ClientError as e:
            logger.error(f"DynamoDB Error: {str(e)}")
            raise DatabaseError("Search query failed")