import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from django.conf import settings

from core.constants import COLLECTIONS
from services.firebase.firestore import create_document


def send_email(to_email, subject, message, sent_by):
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_USERNAME}>"
    msg["To"] = to_email

    status = "sent"
    error_message = None

    try:
        smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        if settings.EMAIL_USE_TLS:
            smtp.starttls()
        smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
        smtp.sendmail(settings.EMAIL_USERNAME, [to_email], msg.as_string())
        smtp.quit()
    except Exception as exc:
        status = "failed"
        error_message = str(exc)

    create_document(
        COLLECTIONS["email_logs"],
        {
            "recipient_email": to_email,
            "subject": subject,
            "body": message,
            "sent_by": sent_by,
            "sent_at": datetime.utcnow().isoformat(),
            "status": status,
            "error_message": error_message,
        },
    )

    return status == "sent", error_message
