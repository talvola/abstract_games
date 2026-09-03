"""Email notifications (your turn, paired, game over, deadline reminder).

Pluggable transport: if SMTP is configured via env it sends real mail, otherwise
it logs the message (so it works out of the box locally and in tests). Any
provider with an SMTP relay works (Brevo, Resend, SES, Mailgun, ...) — set the
AGP_SMTP_* vars, no code change. See DEPLOY.md "Email".

Delivery runs on a daemon thread so a slow relay never delays a move; set
AGP_EMAIL_SYNC=1 (tests) to deliver inline.

The *decision* of who to notify and when lives in ``server/events.py``; this
module only formats and sends.
"""

from __future__ import annotations

import os
import smtplib
import ssl
import threading
from email.message import EmailMessage

SMTP_HOST = os.environ.get("AGP_SMTP_HOST")
SMTP_PORT = int(os.environ.get("AGP_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("AGP_SMTP_USER")
SMTP_PASS = os.environ.get("AGP_SMTP_PASS")
EMAIL_FROM = os.environ.get("AGP_EMAIL_FROM", "Abstract Games <no-reply@localhost>")
BASE_URL = os.environ.get("AGP_BASE_URL", "http://localhost:5173").rstrip("/")
EMAIL_SYNC = os.environ.get("AGP_EMAIL_SYNC", "") not in ("", "0", "false")


def configured() -> bool:
    return bool(SMTP_HOST)


def send_email(to: str, subject: str, body: str) -> None:
    """Deliver one message now (blocking). Never raises — a notification
    failure must not break the move that triggered it."""
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
                s.login(SMTP_USER, SMTP_PASS or "")
            s.send_message(msg)
    except Exception as e:  # noqa: BLE001 - never let notification failure break a move
        print(f"[notify] email to {to} failed: {e!r}")


def _dispatch(to: str, subject: str, body: str) -> None:
    # Look up send_email at call time so tests can monkeypatch it.
    if EMAIL_SYNC:
        send_email(to, subject, body)
        return
    threading.Thread(target=send_email, args=(to, subject, body), daemon=True).start()


def match_url(match_id: str) -> str:
    return f"{BASE_URL}/?match={match_id}"


_FOOTER = (
    "\n\n— Abstract Games\n"
    "You're getting this because you have an account at {base}. "
    "Games time out after {days:g} days without a move."
)


def _footer() -> str:
    from .games import MOVE_DEADLINE_DAYS  # lazy: games imports the engine

    return _FOOTER.format(base=BASE_URL, days=MOVE_DEADLINE_DAYS)


# ---------------------------------------------------------------------------
#  templates
# ---------------------------------------------------------------------------
def notify_your_turn(to_email: str, to_name: str, opponent: str, game_name: str, match_id: str) -> None:
    subject = f"Your turn — {game_name} vs {opponent}"
    body = (
        f"Hi {to_name},\n\n"
        f"It's your move in your {game_name} game against {opponent}.\n\n"
        f"Play it here: {match_url(match_id)}" + _footer()
    )
    _dispatch(to_email, subject, body)


def notify_paired(to_email: str, to_name: str, opponent: str, game_name: str, match_id: str,
                  your_move: bool) -> None:
    subject = f"{opponent} accepted your {game_name} challenge"
    turn = ("It's your move first." if your_move
            else f"{opponent} moves first — we'll email you when it's your turn.")
    body = (
        f"Hi {to_name},\n\n"
        f"{opponent} accepted your open challenge, so your {game_name} game has started. {turn}\n\n"
        f"Open the game: {match_url(match_id)}" + _footer()
    )
    _dispatch(to_email, subject, body)


def notify_game_over(to_email: str, to_name: str, opponent: str, game_name: str, match_id: str,
                     outcome: str, reason: str = "") -> None:
    """outcome: 'won' | 'lost' | 'draw'. reason: '' | 'resignation' | 'timeout'."""
    how = {
        "": "",
        "resignation": (f" — {opponent} resigned" if outcome == "won" else " by resignation"),
        "timeout": (f" — {opponent} ran out of time" if outcome == "won"
                    else " — you ran out of time to move"),
    }[reason]
    headline = {"won": "You won", "lost": "You lost", "draw": "Draw"}[outcome]
    subject = f"{headline}{how} — {game_name} vs {opponent}"
    body = (
        f"Hi {to_name},\n\n"
        f"Your {game_name} game against {opponent} is over: {headline.lower()}{how}.\n\n"
        f"See the final position or replay it: {match_url(match_id)}" + _footer()
    )
    _dispatch(to_email, subject, body)


def notify_deadline_reminder(to_email: str, to_name: str, opponent: str, game_name: str,
                             match_id: str, hours_left: float) -> None:
    h = max(1, int(round(hours_left)))
    subject = f"About {h}h left to move — {game_name} vs {opponent}"
    body = (
        f"Hi {to_name},\n\n"
        f"Reminder: you have about {h} hour{'s' if h != 1 else ''} left to move in your "
        f"{game_name} game against {opponent}. If the clock runs out the game is forfeited.\n\n"
        f"Play it here: {match_url(match_id)}" + _footer()
    )
    _dispatch(to_email, subject, body)
