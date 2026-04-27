from datetime import datetime
import os
from urllib.parse import quote

from twilio.rest import Client

from app.extensions import db
from app.models import NotificationLog, get_app_settings


def format_brl(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def build_reminder_message(student_name, due_date, amount):
    settings = get_app_settings()
    values = SafeDict(
        student_name=student_name,
        due_date=due_date.strftime("%d/%m/%Y"),
        amount=format_brl(amount),
        gym_name=settings.gym_name,
    )
    return settings.whatsapp_template.format_map(values)


def is_twilio_configured():
    return all(
        [
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN"),
            os.getenv("TWILIO_WHATSAPP_FROM"),
        ]
    )


def build_manual_whatsapp_url(phone, message):
    destination = "".join(char for char in (phone or "") if char.isdigit())
    return f"https://wa.me/{destination}?text={quote(message)}"


def register_notification(payment, provider, status, details, message):
    payment.reminder_sent_at = datetime.utcnow()
    log = NotificationLog(
        payment_id=payment.id,
        phone=payment.student.phone,
        message=message,
        provider=provider,
        status=status,
        details=details,
    )
    db.session.add(log)
    db.session.commit()
    return log


def register_manual_whatsapp_click(payment):
    message = build_reminder_message(payment.student.full_name, payment.due_date, payment.amount)
    manual_url = build_manual_whatsapp_url(payment.student.phone, message)
    register_notification(
        payment,
        provider="whatsapp-link",
        status="opened",
        details=manual_url,
        message=message,
    )
    return manual_url


def send_whatsapp_reminder(payment):
    message = build_reminder_message(payment.student.full_name, payment.due_date, payment.amount)
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")

    if not is_twilio_configured():
        manual_url = build_manual_whatsapp_url(payment.student.phone, message)
        register_notification(
            payment,
            provider="whatsapp-link",
            status="manual-required",
            details=manual_url,
            message=message,
        )
        return "whatsapp-link", "manual-required"

    provider = "twilio"
    status = "queued"
    details = ""

    if provider == "twilio":
        client = Client(account_sid, auth_token)
        response = client.messages.create(
            body=message,
            from_=whatsapp_from,
            to=f"whatsapp:{payment.student.phone}",
        )
        status = response.status or "sent"
        details = response.sid

    register_notification(payment, provider=provider, status=status, details=details, message=message)
    return provider, status