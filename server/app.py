"""Phase-1 backend: exposes the AGP engine over HTTP.

Server-authoritative but stateless: the client holds the (serialized) game
state and sends it back with each request. No database yet -- that arrives in
Phase 2 with accounts and async matches. The frontend never knows any game's
rules; it only renders RenderSpec and posts moves.

Run (from repo root):
    pip install -r server/requirements.txt
    uvicorn server.app:app --reload --port 8000
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make the engine importable and locate the bundled game packages.
ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))

from agp import MCTSBot, PackageError, load  # noqa: E402

GAMES_DIR = ENGINE / "games"

app = FastAPI(title="Abstract Games Platform", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-only; tighten in Phase 2
    allow_methods=["*"],
    allow_headers=["*"],
)

_rng = random.Random()


class Registry:
    """Loads every package under games/ once at startup."""

    def __init__(self, games_dir: Path):
        self.entries: dict[str, dict] = {}
        for pkg in sorted(p for p in games_dir.iterdir() if p.is_dir()):
            try:
                manifest, game = load(pkg)
            except PackageError as e:
                print(f"skip {pkg.name}: {e}", file=sys.stderr)
                continue
            self.entries[manifest["uid"]] = {"manifest": manifest, "game": game}

    def get(self, uid: str):
        entry = self.entries.get(uid)
        if entry is None:
            raise HTTPException(404, f"unknown game {uid!r}")
        return entry["manifest"], entry["game"]


registry = Registry(GAMES_DIR)


def _view(game, state) -> dict:
    """Everything the client needs to render and act on a position."""
    terminal = game.is_terminal(state)
    return {
        "render": game.render(state),
        "legal_moves": game.legal_moves(state),
        "current_player": game.current_player(state),
        "num_players": game.num_players,
        "terminal": terminal,
        "returns": game.returns(state) if terminal else None,
    }


# ---- request bodies --------------------------------------------------------
class NewBody(BaseModel):
    options: dict | None = None


class MoveBody(BaseModel):
    state: dict
    move: str


class BotBody(BaseModel):
    state: dict
    iterations: int = 250


# ---- routes ----------------------------------------------------------------
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


@app.post("/api/games/{uid}/new")
def new_game(uid: str, body: NewBody):
    _, game = registry.get(uid)
    state = game.initial_state(options=body.options or {}, rng=_rng)
    return {"state": game.serialize(state), "view": _view(game, state)}


@app.post("/api/games/{uid}/move")
def make_move(uid: str, body: MoveBody):
    _, game = registry.get(uid)
    state = game.deserialize(body.state)
    if game.is_terminal(state):
        raise HTTPException(400, "game is over")
    if body.move not in game.legal_moves(state):
        raise HTTPException(400, f"illegal move {body.move!r}")
    state = game.apply_move(state, body.move, rng=_rng)
    return {"state": game.serialize(state), "view": _view(game, state)}


@app.post("/api/games/{uid}/bot")
def bot_move(uid: str, body: BotBody):
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
