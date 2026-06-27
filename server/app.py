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
from fastapi.staticfiles import StaticFiles
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


def _seat_ratings(db, match) -> list[dict]:
    """Per-seat rating snapshot for match_view: current rating/rd/games for each
    human seat, plus the rating `delta` once the match is rated. db may be None
    (e.g. some read paths) — then no rating fields are attached."""
    from .models import MatchRatingChange, UserGameRating

    out = [{"name": s.get("name"), "type": s["type"],
            **({"user_id": s["user_id"]} if s.get("type") == "user" else {})}
           for s in match.players]
    if db is None:
        return out
    deltas = {}
    if match.status == "finished":
        for ch in db.query(MatchRatingChange).filter_by(match_id=match.id).all():
            deltas[ch.user_id] = round(ch.delta, 1)
    for seat, s in zip(out, match.players):
        if s.get("type") != "user":
            continue
        uid = s.get("user_id")
        r = db.query(UserGameRating).filter_by(user_id=uid, game_uid=match.game_uid).first()
        if r is not None:
            seat["rating"] = round(r.rating)
            seat["rd"] = round(r.rd)
            seat["provisional"] = r.rd > 110  # high RD = not yet settled
        if uid in deltas:
            seat["delta"] = deltas[uid]
    return out


def match_view(match: Match, me_id: int | None, db: Session | None = None) -> dict:
    _, game = registry.get(match.game_uid)
    state = game.deserialize(match.state)
    my_seat = seat_of(match, me_id)
    pos = G.position_view(game, state)
    # The MATCH status is authoritative for terminality: resign/draw end a match
    # via match.status without necessarily ending the engine state (e.g. /resign
    # doesn't checkmate the board), so a finished match must read as terminal.
    pos["terminal"] = match.status == "finished"
    return {
        "id": match.id,
        "game_uid": match.game_uid,
        "game_name": game_name(match.game_uid),
        "options": match.options,
        "players": _seat_ratings(db, match),
        "my_seat": my_seat,
        "my_turn": match.status == "active"
        and my_seat is not None
        and match.current_player == my_seat,
        "status": match.status,
        "winner": match.winner,
        "deadline": (lambda d: d.isoformat() if d else None)(G.match_deadline(match)),
        "history": G.build_history(game, match),
        **pos,
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


class QuickPairBody(BaseModel):
    game_uid: str
    options: dict | None = None


class MoveBody(BaseModel):
    move: str


class MessageBody(BaseModel):
    body: str


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
            "mode": m.get("mode", "enforced"),
            "freeform": m.get("mode") == "freeform",
            "source": entry["source"],
            "uploader": entry.get("uploader"),
            "has_rules": (entry["path"] / "rules.md").exists(),
        })
    return {"games": out}


@app.get("/api/games/{uid}/rules")
def game_rules(uid: str):
    entry = registry.entries.get(uid)
    if entry is None:
        raise HTTPException(404, f"unknown game {uid!r}")
    path = entry["path"] / "rules.md"
    if not path.exists():
        raise HTTPException(404, f"no rules for {uid!r}")
    return {
        "uid": uid,
        "name": entry["manifest"]["name"],
        "markdown": path.read_text(encoding="utf-8"),
        "source_url": entry["manifest"].get("bgg_url"),
    }


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
    from .models import UserGameRating

    seeks = db.query(Seek).order_by(Seek.created_at.desc()).all()

    def creator_rating(s):
        r = (db.query(UserGameRating)
               .filter_by(user_id=s.creator_id, game_uid=s.game_uid).first())
        return {"rating": round(r.rating), "provisional": r.rd > 110} if r else None

    return {
        "seeks": [
            {
                "id": s.id,
                "creator_name": s.creator_name,
                "creator_id": s.creator_id,
                "creator_rating": creator_rating(s),
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


def _rating_value(db, user_id: int, game_uid: str) -> float:
    from .models import UserGameRating
    r = db.query(UserGameRating).filter_by(user_id=user_id, game_uid=game_uid).first()
    return r.rating if r else 1500.0


@app.post("/api/quickpair")
def quick_pair(body: QuickPairBody, background: BackgroundTasks,
               db: Session = Depends(get_db), user: User = Depends(current_user)):
    """One-click pairing. If an open seek for this game (+options) exists from
    another player, pair with the CLOSEST-rated one immediately and return the
    match. Otherwise post a seek and return paired=false (the caller waits)."""
    registry.get(body.game_uid)  # validate game exists
    opts = body.options or {}
    candidates = [
        s for s in db.query(Seek).filter(Seek.game_uid == body.game_uid).all()
        if s.creator_id != user.id and (s.options or {}) == opts
        and db.get(User, s.creator_id) is not None
    ]
    if candidates:
        my_r = _rating_value(db, user.id, body.game_uid)
        seek = min(candidates, key=lambda s: abs(_rating_value(db, s.creator_id, body.game_uid) - my_r))
        creator = db.get(User, seek.creator_id)
        players = order_seats(seat_user(creator), seat_user(user), seek.seat_pref)
        match = create_match(db, seek.game_uid, seek.options, players)
        db.delete(seek)
        db.commit()
        notify_turn(db, match, user.id, background)
        return {"paired": True, "match_id": match.id}
    # No opponent waiting — post our own seek.
    seek = Seek(id=G.new_id(), creator_id=user.id, creator_name=user.display_name,
                game_uid=body.game_uid, options=opts, seat_pref="random")
    db.add(seek)
    db.commit()
    return {"paired": False, "seek_id": seek.id}


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
    _, game = registry.get(body.game_uid)
    if body.opponent == "bot":
        if G.is_freeform(game):
            raise HTTPException(400, "freeform (unenforced) games have no computer opponent")
        bot = seat_bot(body.bot_iterations)
        players = order_seats(seat_user(user), bot, body.seat)
        match = create_match(db, body.game_uid, body.options or {}, players)
        return {"match_id": match.id}
    raise HTTPException(400, "for a human opponent, create a seek instead")


@app.get("/api/matches")
def my_matches(db: Session = Depends(get_db), user: User = Depends(current_user)):
    from .models import MatchRatingChange

    G.sweep_overdue(db)  # opportunistic: clear rotted correspondence games on lobby load
    # Small-scale: scan recent matches and filter by membership in Python.
    rows = db.query(Match).order_by(Match.updated_at.desc()).limit(200).all()
    out = []
    for m in rows:
        seat = seat_of(m, user.id)
        if seat is None:
            continue
        opp = next((s.get("name") for i, s in enumerate(m.players) if i != seat), "?")
        dl = G.match_deadline(m)
        delta = None
        if m.status == "finished":
            ch = (db.query(MatchRatingChange)
                    .filter_by(match_id=m.id, user_id=user.id).first())
            if ch:
                delta = round(ch.delta, 1)
        out.append({
            "id": m.id,
            "game_name": game_name(m.game_uid),
            "opponent": opp,
            "status": m.status,
            "my_turn": m.status == "active" and m.current_player == seat,
            "winner_is_me": m.status == "finished" and m.winner == seat,
            "winner": m.winner,
            "updated_at": m.updated_at.isoformat(),
            "deadline": dl.isoformat() if dl else None,
            "delta": delta,
        })
    out.sort(key=lambda r: (r["status"] != "active", not r["my_turn"]))
    return {"matches": out}


@app.get("/api/matches/{match_id}")
def get_match(match_id: str, db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(404, "match not found")
    G.forfeit_if_overdue(db, match)  # opening an overdue game settles it
    return match_view(match, user.id if user else None, db)


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
    # Enforced games check legal-move membership; freeform (honor-system) games
    # accept any structurally-valid move — the server relays, it doesn't referee.
    ok = (G.freeform_move_ok(game, state, body.move) if G.is_freeform(game)
          else body.move in game.legal_moves(state))
    if not ok:
        raise HTTPException(400, f"illegal move {body.move!r}")

    # Apply ONLY the human move and return immediately, so the client paints it
    # before any bot starts thinking. The bot's reply is fetched via /advance.
    G.apply_human_move(match, game, body.move)
    db.commit()
    db.refresh(match)
    G.rate_finished_match(db, match)  # idempotent; only fires on human-vs-human finish
    notify_turn(db, match, user.id, background)
    return match_view(match, user.id, db)


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
    return match_view(match, user.id, db)


@app.post("/api/matches/{match_id}/resign")
def resign_match(match_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(404, "match not found")
    seat = seat_of(match, user.id)
    if seat is None:
        raise HTTPException(403, "you are not a player in this match")
    if match.status != "active":
        return match_view(match, user.id, db)
    _, game = registry.get(match.game_uid)
    match.status = "finished"
    # 2-player: the opponent wins. Otherwise just end it with no winner.
    match.winner = (1 - seat) if game.num_players == 2 else None
    db.commit()
    db.refresh(match)
    G.rate_finished_match(db, match)
    return match_view(match, user.id, db)


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


@app.get("/api/matches/{match_id}/messages")
def list_messages(match_id: str, db: Session = Depends(get_db)):
    """Chat thread for a match (public — spectators can read)."""
    from .models import Message

    msgs = (db.query(Message).filter_by(match_id=match_id)
              .order_by(Message.created_at.asc()).all())
    return {"messages": [
        {"user_id": m.user_id, "name": m.name, "body": m.body,
         "ts": m.created_at.isoformat()} for m in msgs
    ]}


@app.post("/api/matches/{match_id}/messages")
def post_message(match_id: str, body: MessageBody, db: Session = Depends(get_db),
                 user: User = Depends(current_user)):
    """Post to a match thread. Only the match's players may chat."""
    from .models import Message

    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(404, "match not found")
    if seat_of(match, user.id) is None:
        raise HTTPException(403, "only players in this match can chat")
    text = (body.body or "").strip()[:1000]
    if not text:
        raise HTTPException(400, "empty message")
    msg = Message(match_id=match_id, user_id=user.id, name=user.display_name, body=text)
    db.add(msg)
    db.commit()
    return {"ok": True}


# ===========================================================================
#  ratings: leaderboards + player profiles
# ===========================================================================
@app.get("/api/leaderboard/{game_uid}")
def leaderboard(game_uid: str, limit: int = 50, db: Session = Depends(get_db)):
    """Top rated players for one game (provisional ratings — RD>110 — ranked last)."""
    from .models import User, UserGameRating

    limit = max(1, min(limit, 200))
    rows = (db.query(UserGameRating, User)
              .join(User, User.id == UserGameRating.user_id)
              .filter(UserGameRating.game_uid == game_uid, UserGameRating.games > 0)
              .all())
    ranked = sorted(rows, key=lambda ru: (ru[0].rd > 110, -ru[0].rating))[:limit]
    return {
        "game_uid": game_uid,
        "game_name": game_name(game_uid),
        "entries": [
            {"user_id": u.id, "name": u.display_name, "rating": round(r.rating),
             "rd": round(r.rd), "provisional": r.rd > 110,
             "games": r.games, "wins": r.wins, "losses": r.losses, "draws": r.draws}
            for r, u in ranked
        ],
    }


@app.get("/api/matches/{match_id}/replay")
def match_replay(match_id: str, db: Session = Depends(get_db)):
    """Step-through frames of a match: the render + caption at every ply, from the
    initial position to the final one. Re-applies the stored moves (same path as
    build_history). Public — any finished/ongoing match can be reviewed."""
    match = db.get(Match, match_id)
    if not match:
        raise HTTPException(404, "match not found")
    _, game = registry.get(match.game_uid)
    names = [s.get("name") for s in match.players]
    try:
        state = game.initial_state(options=match.options or {})
    except Exception:
        raise HTTPException(500, "cannot replay this match")

    def frame(ply, mover, label):
        r = game.render(state)
        return {"ply": ply, "render": r, "caption": r.get("caption"),
                "mover": mover, "label": label}

    frames = [frame(0, None, None)]
    for mr in sorted(match.moves, key=lambda r: r.ply):
        try:
            label = game.describe_move(state, mr.move)
        except Exception:
            label = mr.move
        try:
            state = game.apply_move(state, mr.move)
        except Exception:
            break
        mover = names[mr.seat] if mr.seat < len(names) else f"P{mr.seat}"
        frames.append(frame(mr.ply + 1, mover, label))
    return {
        "id": match.id, "game_uid": match.game_uid,
        "game_name": game_name(match.game_uid),
        "players": [{"name": s.get("name"), "type": s["type"]} for s in match.players],
        "winner": match.winner, "status": match.status, "frames": frames,
    }


@app.get("/api/users/{user_id}")
def user_profile(user_id: int, db: Session = Depends(get_db)):
    """Public profile: display name + per-game ratings/records, best games first."""
    from .models import User, UserGameRating

    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "user not found")
    ratings = (db.query(UserGameRating)
                 .filter_by(user_id=user_id).filter(UserGameRating.games > 0).all())
    ratings.sort(key=lambda r: (r.rd > 110, -r.rating))
    return {
        "id": u.id,
        "display_name": u.display_name,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "ratings": [
            {"game_uid": r.game_uid, "game_name": game_name(r.game_uid),
             "rating": round(r.rating), "rd": round(r.rd), "provisional": r.rd > 110,
             "games": r.games, "wins": r.wins, "losses": r.losses, "draws": r.draws}
            for r in ratings
        ],
    }


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
    ok = (G.freeform_move_ok(game, state, body.move) if G.is_freeform(game)
          else body.move in game.legal_moves(state))
    if not ok:
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
    move = MCTSBot(_rng, iterations=iters, max_time=G.BOT_MAX_TIME).select(game, state)
    return {"move": move}


@app.get("/api/health")
def health():
    return {"ok": True, "games": list(registry.entries)}


# ===========================================================================
#  Serve the built frontend (single-service production deploy).
#  In local dev the Vite server (:5173) handles the UI and proxies /api here, so
#  this is a no-op unless `web/dist` has been built (see build.sh / render.yaml).
#  Mounted LAST so every /api/* route above takes precedence; html=True serves
#  index.html at "/". The frontend calls origin-relative /api, so one origin =
#  no CORS and same-site session cookies.
# ===========================================================================
_WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
if _WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_WEB_DIST), html=True), name="spa")
