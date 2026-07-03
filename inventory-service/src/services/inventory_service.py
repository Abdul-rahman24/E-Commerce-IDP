import os
import urllib.request
import urllib.error
from dotenv import load_dotenv
from src.repositories.inventory_repository import DynamoDBInventoryRepository
from src.dto.inventory_dto import InventoryTransactionDTO
from src.models.inventory import Inventory
from src.exceptions.app_exceptions import BadRequestError, DatabaseError
from src.utils.logger import get_logger

logger = get_logger("InventoryService")

# Load environment variables
load_dotenv()
PRODUCT_SERVICE_URL = os.environ.get("PRODUCT_SERVICE_URL")

class InventoryService:
    def __init__(self, repository: DynamoDBInventoryRepository):
        self.repository = repository

    def get_inventory(self, product_id: str) -> Inventory:
        return self.repository.get_by_product_id(product_id)

    # --- NEW METHOD: Used by Product Service to set stock to 0 ---
    def initialize_stock(self, product_id: str) -> Inventory:
        logger.info(f"Initializing empty stock for new product {product_id}")
        return self.repository.initialize_inventory(product_id, 0)

    # --- UPDATED METHOD: Verifies with Product Service before restocking ---
    def restock(self, dto: InventoryTransactionDTO) -> Inventory:
        logger.info(f"Verifying product {dto.product_id} exists before restocking...")
        
        try:
            # The "Phone Call" to the Product Service using built-in urllib
            url = f"{PRODUCT_SERVICE_URL}/{dto.product_id}"
            req = urllib.request.Request(url)
            
            # This makes the GET request with a 2-second timeout
            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                
            if status_code != 200:
                raise DatabaseError(f"Product Service returned unexpected status: {status_code}")
                
        except urllib.error.HTTPError as e:
            # HTTPError catches 404, 500, etc.
            if e.code == 404:
                raise BadRequestError(f"Cannot restock: Product ID {dto.product_id} does not exist.")
            else:
                raise DatabaseError(f"Product Service is returning errors. Code: {e.code}")
                
        except urllib.error.URLError as e:
            # URLError catches connection failures, DNS issues, and timeouts
            error_message = str(e.reason)
            logger.error(f"DEBUG: Request to Product Service failed! {error_message}")
            raise DatabaseError(f"Product Service is offline. Error: {error_message}")
            
        except TimeoutError:
            raise DatabaseError("Product Service request timed out.")

        # If the check passes, proceed with restocking
        logger.info("Product verified. Proceeding with restock.")
        try:
            return self.repository.atomic_update(dto.product_id, dto.quantity, 0)
        except Exception:
            return self.repository.initialize_inventory(dto.product_id, dto.quantity)

    def reserve_stock(self, dto: InventoryTransactionDTO) -> Inventory:
        return self.repository.atomic_update(dto.product_id, -dto.quantity, dto.quantity)

    def release_stock(self, dto: InventoryTransactionDTO) -> Inventory:
        return self.repository.atomic_update(dto.product_id, dto.quantity, -dto.quantity)

    def deduct_stock(self, dto: InventoryTransactionDTO) -> Inventory:
        return self.repository.atomic_update(dto.product_id, 0, -dto.quantity)