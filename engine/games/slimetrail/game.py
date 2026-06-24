"""Slimetrail — Bill Taylor, 1992.

Two players share a single neutral MARKER (the "snail") on an N x N board with
two GOAL cells in opposite corners:
  * player 0 (Red)  goal is the BOTTOM-LEFT corner  (0, 0);
  * player 1 (Blue) goal is the TOP-RIGHT   corner  (N-1, N-1).

The marker starts on the centre cell. On a turn the player to move SLIDES the
marker one king-step (orthogonally or diagonally) to an adjacent cell that is
neither slimed nor a previously visited cell. The cell the marker LEAVES turns
into permanent "slime" and can never be entered again.

WIN (as an event):
  * If the marker is moved onto a goal cell, the OWNER of that goal wins — it
    does not matter which player actually pushed it there (you can be forced to
    deliver the win to your opponent). Landing on (0,0) wins for player 0;
    landing on (N-1, N-1) wins for player 1.
  * A player who has NO legal move on their turn LOSES (the marker is trapped);
    the opponent wins.

Termination is guaranteed: every move slimes exactly one cell and the board is
finite, so after at most N*N moves the marker can no longer move. (A defensive
ply cap is included regardless.)

Coordinates / moves are "c,r" cell ids. A move is the marker's DESTINATION cell
(a single click — the snail's next step).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}  # match the platform seat colours (seat 0 red, seat 1 blue)
KING_DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

# Defensive cap; the real bound is N*N (each move slimes a cell). Never reached
# in normal play, but guards any pathological conformance run.
PLY_CAP = 200


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class SlimeState:
    size: int = 8
    marker: tuple = (4, 4)                                # (c, r) of the snail
    slimed: frozenset = field(default_factory=frozenset)  # permanently blocked cells
    to_move: int = 0
    winner: Optional[int] = None
    plies: int = 0


class Slimetrail(Game):
    uid = "slimetrail"
    name = "Slimetrail"

    @property
    def num_players(self) -> int:
        return 2

    # ----- geometry ------------------------------------------------------
    def _goal0(self, n: int) -> tuple[int, int]:
        return (0, 0)

    def _goal1(self, n: int) -> tuple[int, int]:
        return (n - 1, n - 1)

    def _on(self, n: int, c: int, r: int) -> bool:
        return 0 <= c < n and 0 <= r < n

    # ----- core ----------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> SlimeState:
        n = int((options or {}).get("size", 8))
        return SlimeState(size=n, marker=(n // 2, n // 2), slimed=frozenset())

    def current_player(self, s: SlimeState) -> int:
        return s.to_move

    def _raw_moves(self, s: SlimeState) -> list[str]:
        """Destination cells the marker may slide to: adjacent, on-board, and not
        slimed (the cell the marker currently sits on is its own future slime, so
        it can't be a destination either — but it isn't adjacent to itself)."""
        out = []
        c0, r0 = s.marker
        for dc, dr in KING_DIRS:
            c, r = c0 + dc, r0 + dr
            if self._on(s.size, c, r) and (c, r) not in s.slimed:
                out.append(f"{c},{r}")
        return out

    def legal_moves(self, s: SlimeState) -> list[str]:
        if self.is_terminal(s):
            return []
        return self._raw_moves(s)

    def apply_move(self, s: SlimeState, move: str, rng=None) -> SlimeState:
        dest = _cell(move)
        # The vacated cell becomes slime.
        new_slimed = set(s.slimed)
        new_slimed.add(s.marker)

        n = s.size
        winner = None
        if dest == self._goal0(n):
            winner = 0
        elif dest == self._goal1(n):
            winner = 1

        return SlimeState(
            size=n,
            marker=dest,
            slimed=frozenset(new_slimed),
            to_move=1 - s.to_move,
            winner=winner,
            plies=s.plies + 1,
        )

    def is_terminal(self, s: SlimeState) -> bool:
        if s.winner is not None:
            return True
        if s.plies >= PLY_CAP:
            return True
        # Player to move is trapped (no legal slide) -> game over (they lose).
        return not self._raw_moves(s)

    def returns(self, s: SlimeState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        if s.plies >= PLY_CAP:
            return [0.0, 0.0]
        # Terminal because the player to move is trapped: they LOSE.
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    # ----- serialization -------------------------------------------------
    def serialize(self, s: SlimeState) -> dict:
        return {
            "size": s.size,
            "marker": f"{s.marker[0]},{s.marker[1]}",
            "slimed": [f"{c},{r}" for (c, r) in sorted(s.slimed)],
            "to_move": s.to_move,
            "winner": s.winner,
            "plies": s.plies,
        }

    def deserialize(self, d: dict) -> SlimeState:
        return SlimeState(
            size=d["size"],
            marker=_cell(d["marker"]),
            slimed=frozenset(_cell(k) for k in d["slimed"]),
            to_move=d["to_move"],
            winner=d["winner"],
            plies=d.get("plies", 0),
        )

    def describe_move(self, s: SlimeState, move: str) -> str:
        dest = _cell(move)
        return f"{NAMES[s.to_move]}: snail -> {dest[0]},{dest[1]}"

    # ----- rendering -----------------------------------------------------
    def render(self, s: SlimeState, perspective=None) -> dict:
        n = s.size
        g0 = f"{self._goal0(n)[0]},{self._goal0(n)[1]}"
        g1 = f"{self._goal1(n)[0]},{self._goal1(n)[1]}"

        # tints: goals get the seat colours (faded), slimed cells get green.
        tints = {}
        tints[g0] = "#7a2a2a"   # player 0 (Red) goal, bottom-left
        tints[g1] = "#2a4a7a"   # player 1 (Blue) goal, top-right
        for (c, r) in s.slimed:
            tints[f"{c},{r}"] = "#3f7a3f"   # slime green

        # The marker is a neutral disc (owner-less) with a snail glyph.
        mc, mr = s.marker
        pieces = [{
            "cell": f"{mc},{mr}",
            "owner": 0,
            "label": "@",
            "fill": "#d8d8b0",
            "stroke": "#555533",
        }]

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins (snail reached the {NAMES[s.winner]} goal)"
        elif s.plies >= PLY_CAP:
            caption = "Draw (ply cap)"
        elif not self._raw_moves(s):
            caption = f"{NAMES[s.to_move]} is trapped — {NAMES[1 - s.to_move]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move (slide the snail one step)"

        return {
            "board": {"type": "square", "width": n, "height": n, "tints": tints},
            "pieces": pieces,
            "highlights": [{"cell": f"{mc},{mr}", "kind": "last-move"}],
            "caption": caption,
        }
