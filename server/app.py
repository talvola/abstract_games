"""Abstract Games Platform backend.

Phase 1 (kept): anonymous, stateless single-player endpoints for instant
hotseat / vs-bot play -- the client holds the game state.

Phase 2 (new): accounts + persistent correspondence matches. Players sign in,
post open challenges (seeks) or play a bot, and take turns asynchronously; the
server is authoritative and stores every match in the database.

Run (from repo root):
    pip install -r server/requirements.txt
    uvicorn server.app:app --reload --port 8000
"""

from __future__ import annotations

import os
import random

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import games as G
from .auth import (
    COOKIE_NAME,
    SESSION_MAX_AGE,
    current_user,
    hash_password,
    make_session_token,
    optional_user,
    verify_password,
)
from .db import get_db, init_db
from .games import registry
from .models import Match, Seek, User

app = FastAPI(title="Abstract Games Platform", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rng = random.Random()
_COOKIE_SECURE = os.environ.get("AGP_COOKIE_SECURE", "false").lower() == "true"


@app.on_event("startup")
def _startup():
    init_db()


# ===========================================================================
#  helpers
# ===========================================================================
def user_public(u: User) -> dict:
    return {"id": u.id, "display_name": u.display_name, "email": u.email}


def seat_user(u: User) -> dict:
    return {"type": "user", "user_id": u.id, "name": u.display_name}


def seat_bot(iterations: int) -> dict:
    return {"type": "bot", "iterations": int(iterations), "name": "Computer"}


def seat_of(match: Match, user_id: int | None) -> int | None:
    if user_id is None:
        return None
    for i, s in enumerate(match.players):
        if s.get("type") == "user" and s.get("user_id") == user_id:
            return i
    return None


def order_seats(a: dict, b: dict, pref: str) -> list[dict]:
    """Place `a` (the requester) and `b` per `a`'s seat preference."""
    if pref == "first":
        return [a, b]
    if pref == "second":
        return [b, a]
    return [a, b] if _rng.random() < 0.5 else [b, a]


def game_name(uid: str) -> str:
    entry = registry.entries.get(uid)
    return entry["manifest"]["name"] if entry else uid


def match_view(match: Match, me_id: int | None) -> dict:
    _, game = registry.get(match.game_uid)
    state = game.deserialize(match.state)
    my_seat = seat_of(match, me_id)
    return {
        "id": match.id,
        "game_uid": match.game_uid,
        "game_name": game_name(match.game_uid),
        "options": match.options,
        "players": [{"name": s.get("name"), "type": s["type"]} for s in match.players],
        "my_seat": my_seat,
        "my_turn": match.status == "active"
        and my_seat is not None
        and match.current_player == my_seat,
        "status": match.status,
        "winner": match.winner,
        **G.position_view(game, state),
    }


def create_match(db: Session, game_uid: str, options: dict, players: list[dict]) -> Match:
    _, game = registry.get(game_uid)
    state = game.initial_state(options=options or {}, rng=_rng)
    match = Match(
        id=G.new_id(),
        game_uid=game_uid,
        options=options or {},
        players=players,
        state=game.serialize(state),
        current_player=game.current_player(state),
    )
    G.advance_bots(match, game)  # in case a bot moves first
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        COOKIE_NAME,
        make_session_token(user.id),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_COOKIE_SECURE,
    )


# ===========================================================================
#  request bodies
# ===========================================================================
class RegisterBody(BaseModel):
    email: str
    display_name: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


class NewMatchBody(BaseModel):
    game_uid: str
    options: dict | None = None
    opponent: str = "bot"  # bot | open
    seat: str = "first"  # first | second | random
    bot_iterations: int = 300


class SeekBody(BaseModel):
    game_uid: str
    options: dict | None = None
    seat_pref: str = "random"


class MoveBody(BaseModel):
    move: str


# ---- stateless (anonymous) bodies ----
class NewBody(BaseModel):
    options: dict | None = None


class StatelessMoveBody(BaseModel):
    state: dict
    move: str


class BotBody(BaseModel):
    state: dict
    iterations: int = 250


# ===========================================================================
#  catalogue
# ===========================================================================
@app.get("/api/games")
def list_games():
    out = []
    for uid, entry in registry.entries.items():
        m = entry["manifest"]
        out.append({
            "uid": uid,
            "name": m["name"],
            "description": m.get("description", ""),
            "players": m["players"],
            "options": m.get("options", {}),
            "tags": m.get("tags", []),
            "bgg_url": m.get("bgg_url"),
        })
    return {"games": out}


# ===========================================================================
#  auth
# ===========================================================================
@app.post("/api/auth/register")
def register(body: RegisterBody, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email or len(body.password) < 6 or not body.display_name.strip():
        raise HTTPException(400, "valid email, display name, and 6+ char password required")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "email already registered")
    user = User(
        email=email,
        display_name=body.display_name.strip()[:64],
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, user)
    return user_public(user)


@app.post("/api/auth/login")
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid email or password")
    set_session_cookie(response, user)
    return user_public(user)


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: User | None = Depends(optional_user)):
    return user_public(user) if user else None


# ===========================================================================
#  seeks (open challenges)
# ===========================================================================
@app.get("/api/seeks")
def list_seeks(db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    seeks = db.query(Seek).order_by(Seek.created_at.desc()).all()
    return {
        "seeks": [
            {
                "id": s.id,
                "creator_name": s.creator_name,
                "game_uid": s.game_uid,
                "game_name": game_name(s.game_uid),
                "options": s.options,
                "seat_pref": s.seat_pref,
                "mine": user is not None and s.creator_id == user.id,
            }
            for s in seeks
        ]
    }


@app.post("/api/seeks")
def create_seek(body: SeekBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    registry.get(body.game_uid)  # validate game exists
    seek = Seek(
        id=G.new_id(),
        creator_id=user.id,
        creator_name=user.display_name,
        game_uid=body.game_uid,
        options=body.options or {},
        seat_pref=body.seat_pref,
    )
    db.add(seek)
    db.commit()
    return {"id": seek.id}


@app.post("/api/seeks/{seek_id}/accept")
def accept_seek(seek_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    seek = db.get(Seek, seek_id)
    if not seek:
        raise HTTPException(404, "seek not found")
    if seek.creator_id == user.id:
        raise HTTPException(400, "cannot accept your own challenge")
    creator = db.get(User, seek.creator_id)
    if not creator:
        db.delete(seek)
        db.commit()
        raise HTTPException(410, "challenger no longer exists")
    players = order_seats(seat_user(creator), seat_user(user), seek.seat_pref)
    match = create_match(db, seek.game_uid, seek.options, players)
    db.delete(seek)
    db.commit()
    return {"match_id": match.id}


@app.delete("/api/seeks/{seek_id}")
def cancel_seek(seek_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    seek = db.get(Seek, seek_id)
    if seek and seek.creator_id == user.id:
        db.delete(seek)
        db.commit()
    return {"ok": True}


# ===========================================================================
#  matches
# ===========================================================================
@app.post("/api/matches")
def new_match(body: NewMatchBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    registry.get(body.game_uid)
    if body.opponent == "bot":
        bot = seat_bot(body.bot_iterations)
        players = order_seats(seat_user(user), bot, body.seat)
        match = create_match(db, body.game_uid, body.options or {}, players)
        return {"match_id": match.id}
    raise HTTPException(400, "for a human opponent, create a seek instead")


@app.get("/api/matches")
def my_matches(db: Session = Depends(get_db), user: User = Depends(current_user)):
    # Small-scale: scan recent matches and filter by membership in Python.
    rows = db.query(Match).order_by(Match.updated_at.desc()).limit(200).all()
    out = []
    for m in rows:
        seat = seat_of(m, user.id)
        if seat is None:
            continue
        opp = next((s.get("name") for i, s in enumerate(m.players) if i != seat), "?")
        out.append({
            "id": m.id,
            "game_name": game_name(m.game_uid),
            "opponent": opp,
            "status": m.status,
            "my_turn": m.status == "active" and m.current_player == seat,
            "winner_is_me": m.status == "finished" and m.winner == seat,
            "winner": m.winner,
            "updated_at": m.updated_at.isoformat(),
        })
    out.sort(key=lambda r: (r["status"] != "active", not r["my_turn"]))
    return {"matches": out}


@app.get("/api/matches/{match_id}")
def get_match(match_id: str, db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(404, "match not found")
    return match_view(match, user.id if user else None)


@app.post("/api/matches/{match_id}/move")
def make_match_move(
    match_id: str,
    body: MoveBody,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(404, "match not found")
    if match.status != "active":
        raise HTTPException(400, "match is over")
    seat = seat_of(match, user.id)
    if seat is None:
        raise HTTPException(403, "you are not a player in this match")
    if match.current_player != seat:
        raise HTTPException(409, "not your turn")

    _, game = registry.get(match.game_uid)
    state = game.deserialize(match.state)
    if body.move not in game.legal_moves(state):
        raise HTTPException(400, f"illegal move {body.move!r}")

    G.apply_human_move(match, game, body.move)
    if match.status == "active":
        G.advance_bots(match, game)
    db.commit()
    db.refresh(match)
    return match_view(match, user.id)


# ===========================================================================
#  stateless single-player (anonymous, no DB) -- Phase 1
# ===========================================================================
@app.post("/api/games/{uid}/new")
def stateless_new(uid: str, body: NewBody):
    _, game = registry.get(uid)
    state = game.initial_state(options=body.options or {}, rng=_rng)
    return {"state": game.serialize(state), "view": G.position_view(game, state)}


@app.post("/api/games/{uid}/move")
def stateless_move(uid: str, body: StatelessMoveBody):
    _, game = registry.get(uid)
    state = game.deserialize(body.state)
    if game.is_terminal(state):
        raise HTTPException(400, "game is over")
    if body.move not in game.legal_moves(state):
        raise HTTPException(400, f"illegal move {body.move!r}")
    state = game.apply_move(state, body.move, rng=_rng)
    return {"state": game.serialize(state), "view": G.position_view(game, state)}


@app.post("/api/games/{uid}/bot")
def stateless_bot(uid: str, body: BotBody):
    from agp import MCTSBot

    _, game = registry.get(uid)
    state = game.deserialize(body.state)
    if game.is_terminal(state):
        raise HTTPException(400, "game is over")
    iters = max(1, min(body.iterations, 5000))
    move = MCTSBot(_rng, iterations=iters).select(game, state)
    return {"move": move}


@app.get("/api/health")
def health():
    return {"ok": True, "games": list(registry.entries)}
