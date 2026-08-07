from integrations.sending_emails import send_email


def send_customer_email(
    recipient_email: str,
    subject: str,
    body: str,
    reply_message_id: str | None = None
) -> str:
    status = send_email(
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        reply_message_id=reply_message_id
    )

    return status