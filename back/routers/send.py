from fastapi import APIRouter, HTTPException, status
from schemas import EmailSendRequest
from services import send_service

router = APIRouter(
    prefix="/api/send",
    tags=["send"]
)

@router.post("/api/send")
def send(payload: EmailSendRequest):
    send_status = send_service.send_customer_email(
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        body=payload.body,
        reply_message_id=payload.reply_message_id
        )
    
    if send_status != "OK":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=status)
    return {"send_status": send_status}