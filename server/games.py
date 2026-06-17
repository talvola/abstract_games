"""Engine integration: the game registry and the helpers that drive a stored
Match through the engine (apply human moves, auto-play bot seats, build views)."""

from __future__ import annotations

import random
import sys
import uuid
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))

from agp import MCTSBot, PackageError, load  # noqa: E402

GAMES_DIR = ENGINE / "games"
_rng = random.Random()


class Registry:
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


def new_id() -> str:
    return uuid.uuid4().hex


def position_view(game, state) -> dict:
    """Render + actionable info for a position (no per-viewer fields)."""
    terminal = game.is_terminal(state)
    return {
        "render": game.render(state),
        "legal_moves": game.legal_moves(state),
        "current_player": game.current_player(state),
        "num_players": game.num_players,
        "terminal": terminal,
        "returns": game.returns(state) if terminal else None,
    }


def advance_bots(match, game) -> None:
    """While it's a bot seat's turn, play it. Mutates match.state/current_player/
    status/winner in place and appends moves. Handles multi-move turns."""
    state = game.deserialize(match.state)
    ply = len(match.moves)
    while not game.is_terminal(state):
        seat_idx = game.current_player(state)
        seat = match.players[seat_idx]
        if seat.get("type") != "bot":
            break
        move = MCTSBot(_rng, iterations=int(seat.get("iterations", 300))).select(game, state)
        state = game.apply_move(state, move, rng=_rng)
        match.moves.append(_move_record(match.id, ply, seat_idx, move))
        ply += 1
    _commit_position(match, game, state)


def apply_human_move(match, game, move: str) -> None:
    state = game.deserialize(match.state)
    state = game.apply_move(state, move, rng=_rng)
    match.moves.append(_move_record(match.id, len(match.moves), match.current_player, move))
    _commit_position(match, game, state)


def _commit_position(match, game, state) -> None:
    match.state = game.serialize(state)
    match.current_player = game.current_player(state)
    if game.is_terminal(state):
        match.status = "finished"
        ret = game.returns(state)
        best = max(ret)
        winners = [i for i, v in enumerate(ret) if v == best]
        match.winner = winners[0] if (len(winners) == 1 and best > 0) else None


def _move_record(match_id, ply, seat, move):
    from .models import MoveRecord

    return MoveRecord(match_id=match_id, ply=ply, seat=seat, move=move)
