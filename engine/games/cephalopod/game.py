"""Cephalopod (Mark Steere, 2006) — a dice-capture majority game.

Two players alternately add one die of their own colour to a vacant square on a
5x5 board (size option 3/5/7). A die, once placed, never moves.

Placement resolution (no actual randomness — the die's value is *determined*):
  * Look at the dice on the cells ORTHOGONALLY adjacent to the placement.
  * If some subset of two-or-more of those adjacent dice has a pip sum of six or
    less, capturing is MANDATORY: the player chooses one such qualifying subset,
    removes those dice from the board, and the newly placed die shows that sum
    (2..6) in the mover's colour. (The player need not take the maximum — any
    qualifying subset is legal; Steere's Fig. 4.)
  * Otherwise the new die simply shows a one in the mover's colour.

A die's pip value is therefore always 1..6.

END: when the board is completely full, the player owning the MAJORITY of the
dice wins. The board has an odd number of cells, so no tie is possible.

Move notation (clickable):
  * Plain one-placement:  "c,r"          (single click on an empty cell)
  * Capturing placement:  "c,r=a,b;d,e"  (=CHOICE suffix lists the captured
    cells, sorted, ';'-separated). When several capturing subsets land on the
    same target cell the UI's =CHOICE picker disambiguates them.

Termination: the board is the terminal predicate — the game ends EXACTLY when
every cell is occupied. The board does NOT monotonically fill: a plain "1"
placement is net +1 die, but a capture removes >=2 dice and adds 1, so a
capturing turn INCREASES the number of empty cells. Filling thus takes far more
plies than there are cells (~165 on 5x5, not 25).

Termination is nonetheless guaranteed without any low ply cap: the total pip-sum
on the board is bounded above by 6 * cells and is NON-DECREASING — a capture
replaces dice summing S with one die showing S (sum unchanged), and a plain "1"
placement raises the sum by exactly 1. So there are at most 6 * cells plain
placements, and between/around them each capture strictly reduces the live dice
count, so captures are bounded too. The game provably reaches a full board. A
defensive ply cap is kept FAR above the true maximum as a pure backstop that
never fires in legal play.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}
DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]   # orthogonal neighbours


@dataclass
class CephState:
    board: dict = field(default_factory=dict)   # (c, r) -> (owner, pips)
    to_move: int = 0
    size: int = 5
    plies: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(c, r) -> str:
    return f"{c},{r}"


def _capturing_subsets(adj: list) -> list:
    """adj = list of (cell, pips) for occupied orthogonal neighbours.
    Return every subset (as a frozenset of cells) of size >=2 whose pip sum <=6."""
    out = []
    n = len(adj)
    for k in range(2, n + 1):
        for combo in combinations(range(n), k):
            s = sum(adj[i][1] for i in combo)
            if s <= 6:
                out.append((frozenset(adj[i][0] for i in combo), s))
    return out


class Cephalopod(Game):
    uid = "cephalopod"
    name = "Cephalopod"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CephState:
        size = int((options or {}).get("size", 5))
        return CephState(board={}, to_move=0, size=size, plies=0)

    def current_player(self, s: CephState) -> int:
        return s.to_move

    # ---- helpers -------------------------------------------------------
    def _on(self, s: CephState, c, r) -> bool:
        return 0 <= c < s.size and 0 <= r < s.size

    def _adjacent(self, s: CephState, c, r) -> list:
        adj = []
        for dc, dr in DIRS:
            cc, rr = c + dc, r + dr
            if self._on(s, cc, rr) and (cc, rr) in s.board:
                adj.append(((cc, rr), s.board[(cc, rr)][1]))
        return adj

    def _full(self, s: CephState) -> bool:
        return len(s.board) >= s.size * s.size

    # ---- core API ------------------------------------------------------
    def is_terminal(self, s: CephState) -> bool:
        # Primary (and real) terminal condition: the board is completely full.
        # The pip-sum >= 12 * cells cap is a pure defensive backstop against an
        # unforeseen infinite loop — it is FAR above the true maximum (the
        # pip-sum is bounded by 6 * cells, so a plies cap of 12 * cells can
        # never be reached in legal play; see the module docstring).
        return self._full(s) or s.plies >= 12 * s.size * s.size

    def legal_moves(self, s: CephState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = []
        for c in range(s.size):
            for r in range(s.size):
                if (c, r) in s.board:
                    continue
                adj = self._adjacent(s, c, r)
                subsets = _capturing_subsets(adj)
                if subsets:
                    # capturing is mandatory: one move per qualifying subset
                    for cells, _ in subsets:
                        tag = ";".join(_fmt(*cell) for cell in sorted(cells))
                        moves.append(f"{_fmt(c, r)}={tag}")
                else:
                    # no qualifying subset -> plain one-placement
                    moves.append(_fmt(c, r))
        return moves

    def apply_move(self, s: CephState, move: str, rng=None) -> CephState:
        board = {k: v for k, v in s.board.items()}
        if "=" in move:
            target, tag = move.split("=", 1)
            c, r = _cell(target)
            captured = [_cell(x) for x in tag.split(";")]
            pips = sum(board[cell][1] for cell in captured)
            for cell in captured:
                del board[cell]
            board[(c, r)] = (s.to_move, pips)
        else:
            c, r = _cell(move)
            board[(c, r)] = (s.to_move, 1)
        return CephState(board=board, to_move=1 - s.to_move,
                         size=s.size, plies=s.plies + 1)

    def _counts(self, s: CephState):
        a = sum(1 for o, _ in s.board.values() if o == 0)
        b = sum(1 for o, _ in s.board.values() if o == 1)
        return a, b

    def returns(self, s: CephState) -> list[float]:
        a, b = self._counts(s)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]   # impossible on an odd-celled board, but well-formed

    def serialize(self, s: CephState) -> dict:
        return {
            "board": {_fmt(c, r): [o, p] for (c, r), (o, p) in s.board.items()},
            "to_move": s.to_move,
            "size": s.size,
            "plies": s.plies,
        }

    def deserialize(self, d: dict) -> CephState:
        return CephState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            size=d.get("size", 5),
            plies=d.get("plies", 0),
        )

    def describe_move(self, s: CephState, move: str) -> str:
        who = NAMES[s.to_move][0]
        if "=" in move:
            target, tag = move.split("=", 1)
            captured = [_cell(x) for x in tag.split(";")]
            pips = sum(s.board[cell][1] for cell in captured)
            return f"{who}:{target}={pips} (x{len(captured)})"
        return f"{who}:{move}=1"

    def render(self, s: CephState, perspective=None) -> dict:
        pieces = [{"cell": _fmt(c, r), "owner": o, "label": str(p)}
                  for (c, r), (o, p) in s.board.items()]
        a, b = self._counts(s)
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = f"Draw {a}-{b}"
            else:
                w = 0 if ret[0] > 0 else 1
                caption = f"{NAMES[w]} wins {max(a, b)}-{min(a, b)}"
        else:
            caption = f"{NAMES[s.to_move]} to move  ({a}-{b})"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
