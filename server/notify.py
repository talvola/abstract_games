"""'Your turn' notifications.

Pluggable email: if SMTP is configured via env it sends real mail, otherwise it
logs the message (so it works out of the box locally and in tests). Wire it to
SendGrid/SES/etc. later by setting the AGP_SMTP_* vars — no code change.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = os.environ.get("AGP_SMTP_HOST")
SMTP_PORT = int(os.environ.get("AGP_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("AGP_SMTP_USER")
SMTP_PASS = os.environ.get("AGP_SMTP_PASS")
EMAIL_FROM = os.environ.get("AGP_EMAIL_FROM", "Abstract Games <no-reply@localhost>")
BASE_URL = os.environ.get("AGP_BASE_URL", "http://localhost:5173")


def send_email(to: str, subject: str, body: str) -> None:
    if not SMTP_HOST:
        print(f"[notify] (no SMTP; would email) to={to} | {subject}\n{body}\n")
        return
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls(context=ssl.create_default_context())
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    except Exception as e:  # noqa: BLE001 - never let notification failure break a move
        print(f"[notify] email to {to} failed: {e!r}")


def notify_your_turn(to_email: str, to_name: str, opponent: str, game_name: str, match_id: str) -> None:
    subject = f"Your turn — {game_name} vs {opponent}"
    body = (
        f"Hi {to_name},\n\n"
        f"It's your move in your {game_name} game against {opponent}.\n\n"
        f"Play it here: {BASE_URL}/?match={match_id}\n\n"
        f"— Abstract Games"
    )
    send_email(to_email, subject, body)
