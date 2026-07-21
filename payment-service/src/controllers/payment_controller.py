from fastapi import APIRouter, Depends, Header, status,HTTPException
from src.dto.payment_dto import InitiatePaymentDTO, VerifyPaymentDTO, WebhookPayloadDTO, PaymentResponseDTO, SuccessResponse
from src.services.payment_service import PaymentService
from src.repositories.payment_repository import DynamoDBPaymentRepository

router = APIRouter(prefix="/v1/payments", tags=["Payments"])

def get_payment_service() -> PaymentService:
    repo = DynamoDBPaymentRepository()
    return PaymentService(repo)

@router.post("/initiate", response_model=SuccessResponse[PaymentResponseDTO])
def initiate_payment(dto: InitiatePaymentDTO, x_user_id: str = Header(...), service: PaymentService = Depends(get_payment_service)):
    data = service.initiate_payment(x_user_id, dto)
    return {"success": True, "data": data}

@router.post("/verify", response_model=SuccessResponse[PaymentResponseDTO])
def verify_payment(dto: VerifyPaymentDTO, service: PaymentService = Depends(get_payment_service)):
    data = service.verify_payment(dto)
    return {"success": True, "data": data}

@router.post("/webhook")
def payment_webhook(payload: WebhookPayloadDTO, service: PaymentService = Depends(get_payment_service)):
    # Webhooks usually return raw 200 OK without wrapper to satisfy external provider requirements
    result = service.process_webhook(payload)
    return result

# 💡 ADD THIS TO THE BOTTOM OF YOUR EXISTING payment_controller.py:
from pydantic import BaseModel
import uuid
import time

class SimplePaymentRequest(BaseModel):
    order_id: str
    amount: float
    payment_method: str = "CREDIT_CARD"

@router.post("/pay")
def process_direct_payment(payload: SimplePaymentRequest, x_user_id: str = Header(...)):
    """Direct checkout simulation endpoint for frontend modal integration."""
    try:
        # Simulate brief banking network latency
        time.sleep(1)
        transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        
        # Note: If you want this to also save via your DynamoDB repository, 
        # you can call your existing service methods here in the future!
        
        return {
            "success": True,
            "status": "PAID",
            "transaction_id": transaction_id,
            "order_id": payload.order_id,
            "amount": payload.amount,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    except Exception as e:
        print(f"Payment processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Payment authorization failed")