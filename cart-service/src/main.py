from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
from mangum import Mangum
from src.controllers import cart_controller
from src.exceptions.app_exceptions import AppError
from src.utils.logger import get_logger
from src.repositories.cart_repository import DynamoDBCartRepository
from src.services.cart_service import CartService
import json

logger = get_logger("MainApp")
app = FastAPI(title="Cart Service",redirect_slashes=False)

app.include_router(cart_controller.router)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.warning(f"AppError occurred: {exc.message}")
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.message})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "error": "Invalid request parameters"})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content={"success": False, "error": "Internal Server Error"})
handler = Mangum(app)
def handler(event, context):
    """Universal Router for Cart Service: Handles both HTTP APIs and SQS Background Events"""
    if "Records" in event and "eventSource" in event["Records"][0] and event["Records"][0]["eventSource"] == "aws:sqs":
        logger.info("Received SQS background event in Cart Service!")
        repo = DynamoDBCartRepository()
        service = CartService(repo)
        
        for record in event["Records"]:
            payload = json.loads(record["body"])
            service.handle_sqs_event(payload)
            
        return {"status": "SUCCESS", "message": "Cart cleared via SQS event."}
    
    return handler(event, context)

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="127.0.0.1", port=8002, reload=True)