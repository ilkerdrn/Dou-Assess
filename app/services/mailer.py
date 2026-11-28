"""Basit SMTP gönderici. Kapalıysa ya da hata olursa sessizce False döner; uygulama içi bildirim her durumda üretilir."""
from __future__ import annotations

import logging
import re
import smtplib
from email.message import EmailMessage

from ..config import settings

log = logging.getLogger("dou.mailer")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def mail_enabled() -> bool:
    return bool(settings.email_notifications_enabled and settings.smtp_host and settings.smtp_from)


def send_mail(to: str, subject: str, body: str) -> bool:
    if not mail_enabled() or not _EMAIL.match((to or "").strip()):
        return False
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to.strip()
    msg["Subject"] = subject[:200]
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # ağ/kimlik hatası uygulamayı durdurmamalı
        log.warning("E-posta gönderilemedi (%s): %s", to, exc.__class__.__name__)
        return False
