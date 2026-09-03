"""Tiny in-memory per-IP rate limiter (fixed window) for the abuse-prone
routes: registration, login, challenge/match creation and chat.

Single-process by design — the hosted instance is one uvicorn worker, and the
point is to blunt password guessing and sign-up spam, not to be a precise
quota. Limits are per (bucket, client IP) per minute and can be tuned with
AGP_RATE_LIMIT_<BUCKET>=<n per minute> (0 disables that bucket).

Usage:  @app.post(...)
        def register(..., _rl: None = Depends(rate_limited("register"))): ...
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

DEFAULTS = {
    "register": 5,   # sign-ups per IP per minute
    "login": 10,     # password attempts per IP per minute
    "seek": 10,      # challenges posted / quick-pairs per IP per minute
    "match": 10,     # vs-computer matches created per IP per minute
    "message": 30,   # chat messages per IP per minute
}
WINDOW = 60.0

LIMITS = {k: int(os.environ.get(f"AGP_RATE_LIMIT_{k.upper()}", v)) for k, v in DEFAULTS.items()}

_lock = threading.Lock()
_hits: dict[tuple[str, str], list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    # Render (and any reverse proxy) puts the real client first in X-Forwarded-For.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "?"


def check(bucket: str, ip: str, now: float | None = None) -> None:
    """Record one hit; raise 429 if the bucket is over its per-minute limit."""
    limit = LIMITS.get(bucket, 0)
    if limit <= 0:
        return
    now = time.monotonic() if now is None else now
    key = (bucket, ip)
    with _lock:
        hits = _hits[key]
        cutoff = now - WINDOW
        while hits and hits[0] < cutoff:
            hits.pop(0)
        if len(hits) >= limit:
            retry = int(WINDOW - (now - hits[0])) + 1
            raise HTTPException(
                429, f"too many requests — try again in about {retry}s",
                headers={"Retry-After": str(retry)},
            )
        hits.append(now)


def rate_limited(bucket: str):
    def dep(request: Request) -> None:
        check(bucket, client_ip(request))
    return dep


def reset() -> None:
    with _lock:
        _hits.clear()
