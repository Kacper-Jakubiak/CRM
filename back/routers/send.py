from fastapi import APIRouter, HTTPException, status
from schemas import EmailSendRequest
from services import integration_service

router = APIRouter(
    prefix="/api/send",
    tags=["send"]
)

@router.post("", response_model=str)
def send(payload: EmailSendRequest):
    send_status = integration_service.send_customer_email(
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        body=payload.body,
        reply_message_id=payload.reply_message_id,
        add_html=payload.should_add_html
        )
    
    if send_status != "OK":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=status)
    return send_status