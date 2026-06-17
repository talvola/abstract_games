"""Password hashing (stdlib pbkdf2 -- no native deps) and signed-cookie
sessions (itsdangerous). Good enough for Phase 2; swap for magic-link/OAuth
later without touching the route handlers."""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Cookie, Depends, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

SECRET_KEY = os.environ.get("AGP_SECRET_KEY", "dev-insecure-change-me")
COOKIE_NAME = "agp_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
_PBKDF2_ROUNDS = 200_000

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="agp-session")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}:{dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS)
    return hmac.compare_digest(dk.hex(), dk_hex)


def make_session_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session_token(token: str) -> int | None:
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return int(data["uid"])
    except (BadSignature, SignatureExpired, KeyError, ValueError, TypeError):
        return None


def optional_user(
    agp_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not agp_session:
        return None
    uid = read_session_token(agp_session)
    if uid is None:
        return None
    return db.get(User, uid)


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(401, "not signed in")
    return user
