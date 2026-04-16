import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from string import Template

from django.conf import settings

from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from services.firebase.firestore import create_document, get_document, query_documents, update_document


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


def list_templates():
    return query_documents(COLLECTIONS["email_templates"])


def create_template(payload, actor_uid):
    now = datetime.utcnow().isoformat()
    doc = {
        **payload,
        "created_at": now,
        "updated_at": now,
        "created_by": actor_uid,
    }
    template_id = create_document(COLLECTIONS["email_templates"], doc)
    return get_document(COLLECTIONS["email_templates"], template_id)


def update_template(template_id, patch):
    existing = get_document(COLLECTIONS["email_templates"], template_id)
    if not existing:
        raise AppError("Template not found", ERROR_CODES["NOT_FOUND"], 404)
    update_document(COLLECTIONS["email_templates"], template_id, {**patch, "updated_at": datetime.utcnow().isoformat()})
    return get_document(COLLECTIONS["email_templates"], template_id)


def delete_template(template_id):
    existing = get_document(COLLECTIONS["email_templates"], template_id)
    if not existing:
        raise AppError("Template not found", ERROR_CODES["NOT_FOUND"], 404)
    update_document(COLLECTIONS["email_templates"], template_id, {"is_active": False, "deleted_at": datetime.utcnow().isoformat()})
    return True


def resolve_message(subject, message, template_id="", variables=None):
    variables = variables or {}
    if not template_id:
        if not subject or not message:
            raise AppError("subject and message are required when template_id is not provided", ERROR_CODES["VALIDATION_ERROR"], 400)
        return subject, message

    tpl = get_document(COLLECTIONS["email_templates"], template_id)
    if not tpl or not tpl.get("is_active", True):
        raise AppError("Template not found or inactive", ERROR_CODES["NOT_FOUND"], 404)

    try:
        rendered_subject = Template(tpl.get("subject") or "").safe_substitute(variables)
        rendered_body = Template(tpl.get("body") or "").safe_substitute(variables)
    except Exception as exc:
        raise AppError("Template rendering failed", ERROR_CODES["VALIDATION_ERROR"], 400) from exc

    if not rendered_subject or not rendered_body:
        raise AppError("Rendered template is empty", ERROR_CODES["VALIDATION_ERROR"], 400)

    return rendered_subject, rendered_body
