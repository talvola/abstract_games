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

from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import notify

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
    if G.OPEN_UPLOADS and not G.ADMIN_EMAILS:
        print(
            "WARNING: AGP_ALLOW_OPEN_UPLOADS is on with no admin allowlist — any "
            "signed-in user can upload code that runs in-process. Use only on a "
            "trusted/local instance.",
        )


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
        "history": G.build_history(game, match),
        **G.position_view(game, state),
    }


def notify_turn(db: Session, match: Match, actor_id: int | None, background: BackgroundTasks) -> None:
    """If it's now a *different* human's turn, email them. No-op for bots/self."""
    if match.status != "active":
        return
    seat = match.players[match.current_player]
    if seat.get("type") != "user" or seat.get("user_id") == actor_id:
        return
    user = db.get(User, seat["user_id"])
    if not user:
        return
    others = [s.get("name") for i, s in enumerate(match.players) if i != match.current_player]
    opponent = others[0] if len(others) == 1 else "your opponent"
    background.add_task(
        notify.notify_your_turn,
        user.email, user.display_name, opponent, game_name(match.game_uid), match.id,
    )


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
            "category": m.get("category", "Other"),
            "source": entry["source"],
            "uploader": entry.get("uploader"),
        })
    return {"games": out}


@app.post("/api/games/upload")
async def upload_game(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
):
    """Validate and register an uploaded game package (.zip). On success the
    game is immediately playable -- no redeploy.

    SECURITY: registered game code runs in-process (effectively RCE), so this is
    gated to admins / explicitly-opened instances. See server/games.py."""
    if not G.can_upload(user.email):
        raise HTTPException(
            403,
            "uploads are restricted on this server; an operator must allowlist "
            "your account (AGP_ADMIN_EMAILS) to add games",
        )
    data = await file.read()
    manifest = G.install_upload(data, user.id, user.display_name)
    return {"uid": manifest["uid"], "name": manifest["name"], "version": manifest["version"]}


@app.get("/api/devkit")
def download_devkit():
    """Download the self-contained game-dev kit (SDK + spec + template + agent
    guide). Lets an outside developer build a game without the platform source."""
    kit = Path(__file__).resolve().parent.parent / "dist" / "gamedev-kit.zip"
    if not kit.exists():
        raise HTTPException(404, "dev kit not built yet (run tools/build_devkit.py)")
    return FileResponse(kit, media_type="application/zip", filename="gamedev-kit.zip")


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
    if not user:
        return None
    return {**user_public(user), "can_upload": G.can_upload(user.email)}


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
def accept_seek(seek_id: str, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)):
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
    notify_turn(db, match, user.id, background)  # if the creator is to move first
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
    background: BackgroundTasks,
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

    # Apply ONLY the human move and return immediately, so the client paints it
    # before any bot starts thinking. The bot's reply is fetched via /advance.
    G.apply_human_move(match, game, body.move)
    db.commit()
    db.refresh(match)
    notify_turn(db, match, user.id, background)
    return match_view(match, user.id)


@app.post("/api/matches/{match_id}/advance")
def advance_match(match_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """If it's a bot's turn, play it (looping multi-move turns). No-op otherwise.
    Kept separate from /move so the human's move renders first."""
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(404, "match not found")
    if seat_of(match, user.id) is None:
        raise HTTPException(403, "you are not a player in this match")
    if match.status == "active" and match.players[match.current_player].get("type") == "bot":
        _, game = registry.get(match.game_uid)
        G.advance_bots(match, game)
        db.commit()
        db.refresh(match)
    return match_view(match, user.id)


@app.post("/api/matches/{match_id}/resign")
def resign_match(match_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(404, "match not found")
    seat = seat_of(match, user.id)
    if seat is None:
        raise HTTPException(403, "you are not a player in this match")
    if match.status != "active":
        return match_view(match, user.id)
    _, game = registry.get(match.game_uid)
    match.status = "finished"
    # 2-player: the opponent wins. Otherwise just end it with no winner.
    match.winner = (1 - seat) if game.num_players == 2 else None
    db.commit()
    db.refresh(match)
    return match_view(match, user.id)


@app.delete("/api/matches/{match_id}")
def delete_match(match_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Remove a match from your lobby. Allowed when it's finished or your only
    opponents are bots; for a live game against a person, resign first."""
    match = db.get(Match, match_id)
    if not match:
        return {"ok": True}
    seat = seat_of(match, user.id)
    if seat is None:
        raise HTTPException(403, "you are not a player in this match")
    others_bots = all(s.get("type") == "bot" for i, s in enumerate(match.players) if i != seat)
    if match.status == "active" and not others_bots:
        raise HTTPException(400, "resign this game before removing it")
    db.delete(match)
    db.commit()
    return {"ok": True}


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
    label = game.describe_move(state, body.move)
    mover = game.current_player(state)
    state = game.apply_move(state, body.move, rng=_rng)
    return {"state": game.serialize(state), "view": G.position_view(game, state),
            "label": label, "mover": mover}


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
