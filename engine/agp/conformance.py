"""Conformance harness: does a package actually honour the Game contract?

This is run by ``agp validate`` before a package is accepted, and it is the
target a Claude Code session should generate against -- "make ``agp validate``
pass" is a crisp, checkable goal. It plays random self-play games and checks
the invariants documented on ``Game``.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from .game import Game
from .types import CHANCE


@dataclass
class Report:
    ok: bool = True
    checks: list[tuple[bool, str]] = field(default_factory=list)
    games_played: int = 0
    move_lengths: list[int] = field(default_factory=list)

    def add(self, passed: bool, msg: str) -> None:
        self.checks.append((passed, msg))
        if not passed:
            self.ok = False

    def summary(self) -> str:
        lines = [("PASS" if p else "FAIL") + "  " + m for p, m in self.checks]
        if self.move_lengths:
            avg = sum(self.move_lengths) / len(self.move_lengths)
            lines.append(
                f"....  {self.games_played} random games, "
                f"avg {avg:.1f} moves (min {min(self.move_lengths)}, "
                f"max {max(self.move_lengths)})"
            )
        return "\n".join(lines)


def _equal_serialized(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def check(game: Game, manifest: dict, games: int = 40, seed: int = 0,
          max_moves: int = 3000) -> Report:
    r = Report()

    # --- static contract ---
    r.add(game.num_players == manifest["players"].get("max", game.num_players)
          or manifest["players"]["min"] <= game.num_players <= manifest["players"]["max"],
          f"num_players ({game.num_players}) within manifest players range")

    rng = random.Random(seed)
    try:
        s0 = game.initial_state(rng=rng)
    except Exception as e:  # noqa: BLE001
        r.add(False, f"initial_state raised: {e!r}")
        return r
    r.add(True, "initial_state() returns a state")

    # --- random self-play ---
    for g in range(games):
        rng = random.Random(seed * 1000 + g)
        ok = _play_one(game, rng, r, max_moves)
        if not ok:
            break
        r.games_played += 1

    # --- JSON-ability of a render + serialize ---
    try:
        rep = game.render(s0)
        json.dumps(rep)
        r.add(isinstance(rep, dict) and "board" in rep,
              "render() returns a JSON-able dict with a 'board'")
    except Exception as e:  # noqa: BLE001
        r.add(False, f"render()/json failed: {e!r}")

    return r


def _play_one(game: Game, rng, r: Report, max_moves: int) -> bool:
    state = game.initial_state(rng=rng)
    for n in range(max_moves):
        terminal = game.is_terminal(state)

        # serialize round-trips
        snap = game.serialize(state)
        try:
            json.dumps(snap)
        except TypeError as e:
            r.add(False, f"serialize() not JSON-able: {e!r}")
            return False
        if not _equal_serialized(game.serialize(game.deserialize(snap)), snap):
            r.add(False, "deserialize(serialize(s)) does not round-trip")
            return False

        if terminal:
            ret = game.returns(state)
            if len(ret) != game.num_players or not all(
                isinstance(x, (int, float)) for x in ret
            ):
                r.add(False, f"returns() malformed at terminal: {ret!r}")
                return False
            r.move_lengths.append(n)
            return True

        cp = game.current_player(state)
        if cp == CHANCE:
            r.add(False, "chance nodes not supported by this harness yet")
            return False
        if not (0 <= cp < game.num_players):
            r.add(False, f"current_player out of range: {cp}")
            return False

        moves = game.legal_moves(state)
        if not moves:
            r.add(False, "legal_moves empty on a non-terminal state")
            return False

        move = rng.choice(moves)

        # purity: apply must not mutate the input state
        before = game.serialize(state)
        new_state = game.apply_move(state, move, rng=rng)
        if not _equal_serialized(game.serialize(state), before):
            r.add(False, f"apply_move mutated its input state (move {move!r})")
            return False
        state = new_state

    r.add(False, f"game did not terminate within {max_moves} moves")
    return False
