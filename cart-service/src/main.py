from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
from mangum import Mangum
from src.controllers import cart_controller
from src.exceptions.app_exceptions import AppError
from src.utils.logger import get_logger

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
if __name__ == "__main__":
    # Running on port 8002 to avoid clashing with Product (8000) and Inventory (8001)
    uvicorn.run("src.main:app", host="127.0.0.1", port=8002, reload=True)