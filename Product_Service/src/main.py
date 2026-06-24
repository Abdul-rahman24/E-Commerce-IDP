from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from src.controllers import product_controller
from src.exceptions.app_exceptions import AppError

app = FastAPI(title="Product Service")

app.include_router(product_controller.router)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.message},
    )

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)