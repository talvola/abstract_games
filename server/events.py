"""Who gets told what, when, about a correspondence match.

Called from the route handlers (pairing, move, resign) and from the deadline
sweep (timeout, reminders). Every send is recorded in the `notifications` table
so reminders are sent once per turn and the history is auditable. Only human
seats are ever emailed; the acting player is never emailed about their own
action (they are looking at the screen).
"""

from __future__ import annotations

import os
from datetime import datetime

from . import notify
from .models import Match, MoveRecord, Notification, User

REMINDER_HOURS = float(os.environ.get("AGP_REMINDER_HOURS", "24"))


def _game_name(uid: str) -> str:
    from .app import game_name  # lazy: app imports this module

    return game_name(uid)


def _human_seats(match: Match):
    for i, s in enumerate(match.players or []):
        if s.get("type") == "user" and s.get("user_id"):
            yield i, s


def _opponent_name(match: Match, seat: int) -> str:
    others = [s.get("name") or "?" for i, s in enumerate(match.players) if i != seat]
    return others[0] if len(others) == 1 else "your opponents"


def _turn_key(db, match: Match) -> str:
    return str(db.query(MoveRecord).filter(MoveRecord.match_id == match.id).count())


def _record(db, match: Match, user_id: int, kind: str, turn_key: str) -> bool:
    """Insert the audit row; False if this exact notification was already sent."""
    exists = (
        db.query(Notification)
        .filter_by(match_id=match.id, user_id=user_id, kind=kind, turn_key=turn_key)
        .first()
    )
    if exists:
        return False
    db.add(Notification(match_id=match.id, user_id=user_id, kind=kind, turn_key=turn_key))
    db.commit()
    return True


# ---------------------------------------------------------------------------
#  events
# ---------------------------------------------------------------------------
def on_match_started(db, match: Match, actor_id: int | None) -> None:
    """A seek was accepted / quick-pair matched. Tell the player who was waiting
    (everyone but the actor) — one email, which also says whose move it is."""
    if match.status != "active":
        return
    for seat, s in _human_seats(match):
        if s["user_id"] == actor_id:
            continue
        user = db.get(User, s["user_id"])
        if not user or not _record(db, match, user.id, "paired", "0"):
            continue
        notify.notify_paired(
            user.email, user.display_name, _opponent_name(match, seat),
            _game_name(match.game_uid), match.id, your_move=(match.current_player == seat),
        )


def on_move(db, match: Match, actor_id: int | None) -> None:
    """After a human move: either the game ended (tell the others the result) or
    it's someone else's turn (tell them)."""
    if match.status != "active":
        on_finished(db, match, actor_id, reason="")
        return
    seat = match.current_player
    s = match.players[seat]
    if s.get("type") != "user" or s.get("user_id") == actor_id:
        return
    user = db.get(User, s["user_id"])
    if not user or not _record(db, match, user.id, "turn", _turn_key(db, match)):
        return
    notify.notify_your_turn(
        user.email, user.display_name, _opponent_name(match, seat),
        _game_name(match.game_uid), match.id,
    )


def on_finished(db, match: Match, actor_id: int | None, reason: str) -> None:
    """The match is over (final move, resignation or timeout). Tell every human
    who didn't cause it. reason: '' | 'resignation' | 'timeout'."""
    if match.status != "finished":
        return
    for seat, s in _human_seats(match):
        if s["user_id"] == actor_id:
            continue
        user = db.get(User, s["user_id"])
        if not user or not _record(db, match, user.id, "over", "0"):
            continue
        outcome = "draw" if match.winner is None else ("won" if match.winner == seat else "lost")
        notify.notify_game_over(
            user.email, user.display_name, _opponent_name(match, seat),
            _game_name(match.game_uid), match.id, outcome, reason,
        )


def send_deadline_reminders(db, active_matches) -> int:
    """Email the side to move in every clocked match with < REMINDER_HOURS left,
    once per turn. Returns how many were sent."""
    from .games import match_deadline

    now = datetime.utcnow()
    n = 0
    for match in active_matches:
        dl = match_deadline(match)
        if dl is None:
            continue
        hours_left = (dl - now).total_seconds() / 3600
        if not (0 < hours_left <= REMINDER_HOURS):
            continue
        seat = match.current_player
        s = match.players[seat]
        if s.get("type") != "user":
            continue
        user = db.get(User, s["user_id"])
        if not user or not _record(db, match, user.id, "reminder", _turn_key(db, match)):
            continue
        notify.notify_deadline_reminder(
            user.email, user.display_name, _opponent_name(match, seat),
            _game_name(match.game_uid), match.id, hours_left,
        )
        n += 1
    return n
