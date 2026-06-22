"""Focus (a.k.a. Domination) -- Sid Sackson, 1964. A **stacking** game on an
octagonal 52-cell board (an 8x8 grid with the three corner cells removed at each
of the four corners, leaving a 6x6 core with a 1x4 arm sticking out of each side).

Each player owns 18 pieces. A cell holds a vertical STACK of pieces; whoever owns
the TOP piece controls the stack and may move it. On your turn you either:

  (A) **Move a stack you control.** Pick the top `k` pieces (1..stack-height) and
      slide them in one orthogonal direction exactly `k` cells (you may move fewer
      pieces and travel a shorter distance, but the distance you travel equals the
      number of pieces lifted). The lifted sub-stack lands ON TOP of whatever is
      already on the destination cell (its own internal order preserved).

  (B) **Drop a reserve piece** (only if you have one) onto ANY cell, on top of
      whatever is there -- this is your whole turn.

**Stack cap (over-5 rule):** after a move or drop, any stack taller than 5 has
pieces removed from the BOTTOM until exactly 5 remain. Each removed piece that is
YOURS (the mover's) goes to your reserve; each removed ENEMY piece is captured
(out of play permanently).

**Win:** the last player able to move -- a player loses the moment it is their
turn and they can neither move any stack nor drop a reserve piece. (Equivalently,
you win by controlling every stack while your opponent has no reserve.)

This reuses Lasca's `piece.stack` tower renderer and Crazyhouse's reserve tray.
Cells are "c,r" on the 8x8 grid; a stack move is "src>dst=k" (k = pieces lifted,
which also equals the distance), and a reserve drop is "P@c,r".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

WIDTH = HEIGHT = 8
RED, GREEN = 0, 1            # owner ids (player 0 / player 1)
CAP = 5                      # max stack height before bottom-removal
DROP_LETTER = "P"           # the single reserve-drop piece letter
PLY_CAP = 1000              # defensive draw cap (Focus is finite but guard anyway)
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]

# Corner cells removed (three per corner) -> 52-cell octagon.
REMOVED = {
    (0, 0), (1, 0), (0, 1),          # top-left
    (7, 0), (6, 0), (7, 1),          # top-right
    (0, 7), (1, 7), (0, 6),          # bottom-left
    (7, 7), (6, 7), (7, 6),          # bottom-right
}
CELLS = [(c, r) for r in range(HEIGHT) for c in range(WIDTH)
         if (c, r) not in REMOVED]
CELL_SET = set(CELLS)


def _on(c, r):
    return (c, r) in CELL_SET


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _controller(col):
    """Owner of the TOP piece (last element); None for an empty cell."""
    return col[-1] if col else None


@dataclass
class FState:
    board: dict = field(default_factory=dict)   # (c,r) -> tuple of owners, bottom->top
    reserve: dict = field(default_factory=dict)  # owner -> count of reserve pieces
    captured: dict = field(default_factory=dict)  # owner -> pieces of his captured
    to_move: int = RED
    ply: int = 0
    winner: object = None


class Focus(Game):
    uid = "focus"
    name = "Focus"

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        board = {}
        # Standard 2-player opening: the central 6x6 (cols 1..6, rows 1..6) filled
        # one piece per cell in 2-wide colour stripes; the four arms start empty.
        #   rows 1,3,5:  R R G G R R
        #   rows 2,4,6:  G G R R G G
        for r in range(1, 7):
            for c in range(1, 7):
                block = (c - 1) // 2          # 0,1,2 across the row
                if r % 2 == 1:                # rows 1,3,5
                    owner = RED if block in (0, 2) else GREEN
                else:                         # rows 2,4,6
                    owner = GREEN if block in (0, 2) else RED
                board[(c, r)] = (owner,)
        st = FState(board=board, reserve={RED: 0, GREEN: 0},
                    captured={RED: 0, GREEN: 0}, to_move=RED)
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _stack_moves(self, board, player):
        """All (src, dst, k) stack moves: lift the top k pieces and travel k cells
        orthogonally (1 <= k <= height); destination must be an on-board cell."""
        out = []
        for (sc, sr), col in board.items():
            if not col or col[-1] != player:
                continue
            height = len(col)
            for (dc, dr) in ORTHO:
                # k pieces lifted -> travel exactly k cells (no jumping off board)
                for k in range(1, height + 1):
                    tc, tr = sc + dc * k, sr + dr * k
                    if not _on(tc, tr):
                        continue
                    out.append(((sc, sr), (tc, tr), k))
        return out

    def _drop_moves(self, state, player):
        if state.reserve.get(player, 0) <= 0:
            return []
        # A reserve piece may be dropped on ANY cell (empty or occupied).
        return list(CELLS)

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        moves = []
        for (src, dst, k) in self._stack_moves(state.board, state.to_move):
            moves.append(f"{src[0]},{src[1]}>{dst[0]},{dst[1]}={k}")
        if self._drop_moves(state, state.to_move):
            for (c, r) in CELLS:
                moves.append(f"{DROP_LETTER}@{c},{r}")
        return moves

    # ---- apply -------------------------------------------------------------
    def _settle(self, board, reserve, captured, cell, mover):
        """Apply the over-5 bottom-removal rule to `cell` after a placement."""
        col = board.get(cell, ())
        if len(col) <= CAP:
            return
        overflow = len(col) - CAP
        removed = col[:overflow]            # the BOTTOM pieces
        board[cell] = col[overflow:]        # keep the top CAP pieces
        for owner in removed:
            if owner == mover:
                reserve[mover] = reserve.get(mover, 0) + 1   # yours -> reserve
            else:
                captured[mover] = captured.get(mover, 0) + 1  # enemy -> captured out

    def apply_move(self, state, move, rng=None):
        player = state.to_move
        board = dict(state.board)
        reserve = dict(state.reserve)
        captured = dict(state.captured)

        if "@" in move:                                  # ---- reserve drop ----
            _, cellstr = move.split("@")
            cell = _cell(cellstr)
            reserve[player] = reserve.get(player, 0) - 1
            existing = board.get(cell, ())
            board[cell] = existing + (player,)
            self._settle(board, reserve, captured, cell, player)
        else:                                            # ---- stack move ----
            path, kstr = move.split("=")
            k = int(kstr)
            srcstr, dststr = path.split(">")
            src, dst = _cell(srcstr), _cell(dststr)
            col = board[src]
            moving = col[len(col) - k:]                  # top k pieces (order kept)
            rest = col[:len(col) - k]
            if rest:
                board[src] = rest
            else:
                del board[src]
            existing = board.get(dst, ())
            board[dst] = existing + moving               # lifted stack lands on top
            self._settle(board, reserve, captured, dst, player)

        ns = FState(board=board, reserve=reserve, captured=captured,
                    to_move=1 - player, ply=state.ply + 1)
        if not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = player                            # opponent has no move
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return state.winner is None and state.ply >= PLY_CAP

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialise ---------------------------------------------------------
    def _col_str(self, col):
        return "".join("RG"[o] for o in col)

    def _parse_col(self, s):
        return tuple(0 if ch == "R" else 1 for ch in s)

    def serialize(self, state):
        return {
            "board": {f"{c},{r}": self._col_str(col)
                      for (c, r), col in state.board.items()},
            "reserve": {str(k): v for k, v in state.reserve.items()},
            "captured": {str(k): v for k, v in state.captured.items()},
            "to_move": state.to_move,
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return FState(
            board={_cell(k): self._parse_col(v) for k, v in d["board"].items()},
            reserve={int(k): v for k, v in d.get("reserve", {}).items()},
            captured={int(k): v for k, v in d.get("captured", {}).items()},
            to_move=d["to_move"], ply=d.get("ply", 0), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if "@" in move:
            _, cellstr = move.split("@")
            return f"drop {cellstr}"
        path, kstr = move.split("=")
        return f"{path} (x{kstr})"

    @staticmethod
    def _square_poly(c, r):
        """Unit-square polygon for cell (c,r); row 0 drawn at the top."""
        x, y = c, (HEIGHT - 1 - r)            # flip so r increases downward visually
        s = 40.0
        return [[x * s, y * s], [(x + 1) * s, y * s],
                [(x + 1) * s, (y + 1) * s], [x * s, (y + 1) * s]]

    def render(self, state, perspective=None):
        # The board is the 52-cell octagon: supply only the existing cells as
        # square polygons (the 'polygons' board honours `cells`; a plain 'square'
        # board would draw all 64 squares, including the cut corners).
        cell_specs = [{"id": f"{c},{r}", "points": self._square_poly(c, r)}
                      for (c, r) in CELLS]
        pieces = []
        for (c, r), col in state.board.items():
            if not col:
                continue
            pieces.append({
                "cell": f"{c},{r}",
                "owner": col[-1],                 # controller (top)
                "stack": list(col),               # bottom -> top owners
                "label": str(len(col)) if len(col) > 1 else "",
            })
        names = {RED: "Red", GREEN: "Green"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw (ply cap)"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cell_specs},
            "pieces": pieces,
            "reserve": {str(p): ({DROP_LETTER: n} if n > 0 else {})
                        for p, n in sorted(state.reserve.items())},
            "highlights": [],
            "caption": cap,
        }
