from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
from mangum import Mangum
from src.controllers import search_controller
from src.exceptions.app_exceptions import AppError
from fastapi.middleware.cors import CORSMiddleware
from src.controllers import search_controller
from src.utils.logger import get_logger

logger = get_logger("MainApp")
app = FastAPI(title="Search Service",redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows your local frontend (or any domain) to connect
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Allows all headers
)

app.include_router(search_controller.router)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.message})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "error": "Invalid request parameters"})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content={"success": False, "error": "Internal Server Error"})
handler=Mangum(app)
if __name__ == "__main__":
    # Running on port 8005
    uvicorn.run("src.main:app", host="127.0.0.1", port=8005, reload=True)