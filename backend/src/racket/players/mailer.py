"""Outgoing email adapter (ST-013; ADR 0008: Mailpit in dev). SMTP behind a small interface,
so the production provider (Sprint 4 ADR) replaces only this module."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import urlsplit

from racket.players.domain import SignInEmail

SMTP_TIMEOUT_S = 10


class Mailer(Protocol):
    def send(self, to: str, message: SignInEmail) -> None: ...


class SmtpMailer:
    def __init__(self, smtp_url: str, sender: str) -> None:
        parts = urlsplit(smtp_url)
        if parts.scheme != "smtp" or not parts.hostname:
            raise ValueError("MAIL_SMTP_URL must look like smtp://host:port")
        self.host, self.port, self.sender = parts.hostname, parts.port or 25, sender

    def send(self, to: str, message: SignInEmail) -> None:
        email = EmailMessage()
        email["From"] = self.sender
        email["To"] = to
        email["Subject"] = message.subject
        email.set_content(message.text)
        email.add_alternative(message.html, subtype="html")
        with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_S) as smtp:
            smtp.send_message(email)
