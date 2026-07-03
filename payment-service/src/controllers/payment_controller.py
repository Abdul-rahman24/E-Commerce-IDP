from fastapi import APIRouter, Depends, Header, status
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