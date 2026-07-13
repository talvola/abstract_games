"""Yoxii — Jeremy Partinico, Cosmoludo 2022.

Rules implemented from the official Cosmoludo rulebook (the multilingual sheet
Yoxii-ML9-25.pdf on cosmoludo.com and the 1jour-1jeu English rulebook PDF),
cross-checked against the BGG game description:

* Board: 37 squares laid out as an OCTAGON — a 7x7 grid with a 3-square
  triangular notch cut from each corner (row widths 3,5,7,7,7,5,3). The single
  neutral Totem starts on the centre square (3,3).
* Pieces: each player has 18 pieces with printed values — 5x1 (symbol "O"),
  5x2 ("II"), 5x3 ("Y"), 3x4 ("X"). Seat 0 = White (plays first), seat 1 = Red.
* A turn = two sub-moves by the same player:
  1. MOVE the Totem one square in any of the 8 directions to a free (empty,
     on-board) square; OR jump it, in a straight line (orthogonal or diagonal),
     over a CONTINUOUS run of >= 1 of YOUR OWN pieces to land on the first free
     square just beyond the run. You may NEVER jump over an opponent's piece,
     and the landing square must be free.
  2. PLACE one of your pieces (any value from your remaining stock) on a free
     square among the (up to 8) squares directly around the Totem's new
     position. SPECIAL CASE: if every square around the Totem is occupied, place
     your piece on ANY other free square of the board.
* End: the game ends when the player to move can no longer move the Totem (it is
  encircled/immobilised — no free adjacent square and no legal jump). Each player
  sums the values of THEIR pieces on the (up to 8) squares around the Totem. The
  higher sum wins; tie -> the player with MORE of their pieces around the Totem
  wins; still tied -> an honest DRAW.

Termination is structural: every turn permanently places exactly one piece on a
previously empty square, and there are only 36 non-Totem squares, so a game
lasts at most 36 turns (72 plies). A generous ply cap is a defensive backstop.

Move encoding (prefix-safe two-click):
* Totem sub-move: "c1,r1>c2,r2" (the source cell is always the Totem's square;
  steps and jumps share the same encoding).
* Piece placement: "c,r=V" where V is the value 1/2/3/4 (an "=CHOICE" suffix ->
  the web UI shows a value picker on the clicked square).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# ---------------------------------------------------------------------------
# Board geometry: a 37-square octagon on a 7x7 grid (3-square corner notches).
GRID = 7
CENTER = (3, 3)
# the 3-square triangular notch cut from each corner
_CORNERS = {
    (0, 0), (1, 0), (0, 1),          # top-left
    (5, 0), (6, 0), (6, 1),          # top-right
    (0, 5), (0, 6), (1, 6),          # bottom-left
    (6, 5), (5, 6), (6, 6),          # bottom-right
}
CELLS = frozenset((c, r) for c in range(GRID) for r in range(GRID)
                  if (c, r) not in _CORNERS)          # 49 - 12 = 37

DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

STOCK = {1: 5, 2: 5, 3: 5, 4: 3}                       # 18 pieces per player
SYM = {1: "O", 2: "II", 3: "Y", 4: "X"}                # printed piece symbols
COLS = "abcdefg"
NAMES = ("White", "Red")
PLY_CAP = 200                                          # defensive backstop

# neutral (owner-2) green totem, matching web/src/colors.js
TOTEM_FILL, TOTEM_STROKE = "#3aa84a", "#1c5a26"


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(p) -> str:
    return f"{p[0]},{p[1]}"


def _alg(p) -> str:
    return f"{COLS[p[0]]}{p[1] + 1}"


@dataclass
class YoxState:
    pieces: dict = field(default_factory=dict)         # (c,r) -> (owner, value)
    totem: tuple = CENTER
    stock: list = field(default_factory=lambda: [dict(STOCK), dict(STOCK)])
    to_move: int = 0
    phase: str = "MOVE"                                 # MOVE -> PLACE -> MOVE ...
    last: list = field(default_factory=list)           # cells to highlight
    ply: int = 0


class Yoxii(Game):
    name = "Yoxii"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> YoxState:
        return YoxState()

    def current_player(self, s: YoxState) -> int:
        return s.to_move

    # -- geometry ----------------------------------------------------------------

    def _totem_dests(self, s: YoxState) -> list:
        """Landing squares for the Totem: a one-step move to a free neighbour, or
        a jump over a continuous run of >= 1 own pieces to the first free square
        just beyond (never over an opponent's piece)."""
        owner = s.to_move
        tc = s.totem
        out = []
        for dc, dr in DIRS:
            n = (tc[0] + dc, tc[1] + dr)
            if n in CELLS and n not in s.pieces:       # one-step move
                out.append(n)
                continue
            # jump: the first cell must be one of OUR pieces
            x, y = n
            cnt = 0
            while (x, y) in CELLS and s.pieces.get((x, y), (None,))[0] == owner:
                x, y = x + dc, y + dr
                cnt += 1
            if cnt and (x, y) in CELLS and (x, y) not in s.pieces:
                out.append((x, y))
        return out

    def _place_cells(self, s: YoxState) -> list:
        """Free squares directly around the Totem; if none, any free square."""
        tc = s.totem
        adj = [(tc[0] + dc, tc[1] + dr) for dc, dr in DIRS
               if (tc[0] + dc, tc[1] + dr) in CELLS
               and (tc[0] + dc, tc[1] + dr) not in s.pieces]
        if adj:
            return sorted(adj)
        return sorted(c for c in CELLS if c not in s.pieces and c != s.totem)

    def _neighbors(self, pos) -> list:
        return [(pos[0] + dc, pos[1] + dr) for dc, dr in DIRS
                if (pos[0] + dc, pos[1] + dr) in CELLS]

    # -- move generation ---------------------------------------------------------

    def legal_moves(self, s: YoxState) -> list:
        if self.is_terminal(s):
            return []
        if s.phase == "MOVE":
            frm = _fmt(s.totem)
            return [f"{frm}>{_fmt(d)}" for d in self._totem_dests(s)]
        # PLACE: each free target x each value still in stock
        vals = [v for v in (1, 2, 3, 4) if s.stock[s.to_move][v] > 0]
        return [f"{_fmt(c)}={v}" for c in self._place_cells(s) for v in vals]

    # -- move application --------------------------------------------------------

    def apply_move(self, s: YoxState, move: str, rng=None) -> YoxState:
        if move not in self.legal_moves(s):
            raise ValueError(f"illegal move {move!r}")
        p = s.to_move
        ns = YoxState(pieces=dict(s.pieces), totem=s.totem,
                      stock=[dict(s.stock[0]), dict(s.stock[1])],
                      to_move=p, phase=s.phase, last=list(s.last), ply=s.ply + 1)
        if s.phase == "MOVE":
            frm, _, to = move.partition(">")
            ns.totem = _cell(to)
            ns.phase = "PLACE"
            ns.last = [frm, to]
        else:                                           # PLACE
            cell_s, _, vs = move.partition("=")
            cell, v = _cell(cell_s), int(vs)
            ns.pieces[cell] = (p, v)
            ns.stock[p][v] -= 1
            ns.phase = "MOVE"
            ns.to_move = 1 - p
            ns.last = ns.last + [cell_s]
        return ns

    # -- termination / scoring ---------------------------------------------------

    def is_terminal(self, s: YoxState) -> bool:
        if s.ply >= PLY_CAP:
            return True
        return s.phase == "MOVE" and not self._totem_dests(s)

    def _scores(self, s: YoxState):
        """(sum, count) of each player's pieces on squares around the Totem."""
        val = [0, 0]
        cnt = [0, 0]
        for nb in self._neighbors(s.totem):
            pc = s.pieces.get(nb)
            if pc is not None:
                val[pc[0]] += pc[1]
                cnt[pc[0]] += 1
        return val, cnt

    def returns(self, s: YoxState) -> list:
        val, cnt = self._scores(s)
        if val[0] != val[1]:
            return [1.0, -1.0] if val[0] > val[1] else [-1.0, 1.0]
        if cnt[0] != cnt[1]:
            return [1.0, -1.0] if cnt[0] > cnt[1] else [-1.0, 1.0]
        return [0.0, 0.0]                               # honest draw

    # -- serialisation -----------------------------------------------------------

    def serialize(self, s: YoxState) -> dict:
        return {
            "pieces": {_fmt(c): [o, v] for c, (o, v) in sorted(s.pieces.items())},
            "totem": _fmt(s.totem),
            "stock": [{str(k): n for k, n in s.stock[0].items()},
                      {str(k): n for k, n in s.stock[1].items()}],
            "to_move": s.to_move,
            "phase": s.phase,
            "last": list(s.last),
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> YoxState:
        return YoxState(
            pieces={_cell(k): (int(v[0]), int(v[1]))
                    for k, v in d["pieces"].items()},
            totem=_cell(d["totem"]),
            stock=[{int(k): int(n) for k, n in d["stock"][0].items()},
                   {int(k): int(n) for k, n in d["stock"][1].items()}],
            to_move=d["to_move"],
            phase=d.get("phase", "MOVE"),
            last=list(d.get("last", [])),
            ply=d.get("ply", 0),
        )

    # -- presentation ------------------------------------------------------------

    def describe_move(self, s: YoxState, move: str) -> str:
        if s.phase == "MOVE":
            frm, _, to = move.partition(">")
            return f"Totem {_alg(_cell(frm))}-{_alg(_cell(to))}"
        cell_s, _, vs = move.partition("=")
        return f"{SYM[int(vs)]}({vs}) @ {_alg(_cell(cell_s))}"

    def render(self, s: YoxState, perspective=None) -> dict:
        # 37 octagon cells as unit-square polygons centred at (c, r)
        hs = 0.46
        cells = [{"id": _fmt(c),
                  "points": [[c[0] - hs, c[1] - hs], [c[0] + hs, c[1] - hs],
                             [c[0] + hs, c[1] + hs], [c[0] - hs, c[1] + hs]]}
                 for c in sorted(CELLS)]
        pieces = [{"cell": _fmt(c), "owner": o, "label": SYM[v]}
                  for c, (o, v) in sorted(s.pieces.items())]
        pieces.append({"cell": _fmt(s.totem), "owner": 2, "label": "T",
                       "fill": TOTEM_FILL, "stroke": TOTEM_STROKE})
        highlights = [{"cell": c, "kind": "last-move"} for c in s.last]
        if self.is_terminal(s):
            val, cnt = self._scores(s)
            if val[0] != val[1] or cnt[0] != cnt[1]:
                w = 0 if (val[0], cnt[0]) > (val[1], cnt[1]) else 1
                caption = (f"{NAMES[w]} wins — {NAMES[0]} {val[0]} pts / "
                           f"{NAMES[1]} {val[1]} pts (Totem encircled)")
            else:
                caption = f"Draw — {val[0]}-{val[1]}, equal points and pieces"
        elif s.phase == "MOVE":
            caption = f"{NAMES[s.to_move]} — move the Totem (step or jump own pieces)"
        else:
            caption = f"{NAMES[s.to_move]} — place a piece around the Totem"
        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": highlights,
            "reserve": {str(p): {SYM[v]: n for v, n in sorted(s.stock[p].items())
                                 if n > 0}
                        for p in (0, 1)},
            "caption": caption,
        }
