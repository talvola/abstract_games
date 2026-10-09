"""Tiny in-memory per-IP rate limiter (fixed window) for the abuse-prone
routes: registration, login, challenge/match creation, chat and chat reports.

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
    "forgot": 3,     # password-reset emails per IP per minute
    "report": 10,    # chat-message reports per IP per minute
    "bot": 40,       # anonymous vs-computer bot moves per IP per minute (each
                     # is up to AGP_BOT_MAX_TIME seconds of CPU)
}
WINDOW = 60.0

LIMITS = {k: int(os.environ.get(f"AGP_RATE_LIMIT_{k.upper()}", v)) for k, v in DEFAULTS.items()}

_lock = threading.Lock()
_hits: dict[tuple[str, str], list[float]] = defaultdict(list)


# How many reverse proxies in front of us APPEND to X-Forwarded-For (Render: 1).
TRUSTED_PROXY_HOPS = max(1, int(os.environ.get("AGP_TRUSTED_PROXY_HOPS", "1")))


def client_ip(request: Request) -> str:
    # The client controls everything it sends in X-Forwarded-For; each proxy
    # APPENDS the address it saw. So the trustworthy entry is the one our own
    # proxy added — counted from the RIGHT, never the left. (The leftmost entry
    # was used until 2026-10-08, and a prod probe confirmed it let anyone dodge
    # every rate limit, login included, by sending a fresh fake XFF each time.)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        hops = [h.strip() for h in xff.split(",") if h.strip()]
        if hops:
            return hops[-min(TRUSTED_PROXY_HOPS, len(hops))]
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
