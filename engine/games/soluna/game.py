"""Soluna -- Bruno Faidutti, 2012 (Blue Orange Games / Steffen-Spiele; a
re-theme of his earlier *Babylon*).

Twelve shared, double-sided wooden discs carry four celestial symbols (sun,
moon, stars, comet); each of the six two-symbol combinations appears on exactly
two discs, so every symbol exists on six faces. Setup: the discs are dropped on
the table at random -- 12 single-disc stacks, each showing a random face. The
position of a stack on the table never matters (there is no adjacency); we lay
the 12 stacks on a 4x3 grid of slots purely for display.

On your turn you MUST move one whole stack on top of another stack, provided
the two stacks (before the move) either
  * show the SAME TOP SYMBOL, or
  * have the SAME HEIGHT.
Stacks are never split or flipped; the moved stack keeps its order, so its top
disc becomes the merged stack's top. Neither player owns any disc. Every move
reduces the stack count by one (12 -> at most 11 moves), so the game always
ends: the first player with no legal move LOSES (the player who made the last
move wins). Draws are impossible.

The physical game is played as a match to four round wins with the loser of a
round starting the next; we implement a single round (seat 0 starts).

Move encoding: ``"fc,fr>tc,tr"`` -- the stack at slot ``fc,fr`` is placed on
top of the stack at slot ``tc,tr``. Randomness (the deal) follows the EinStein
pattern: rolled in ``initial_state`` with the passed rng and stored in state;
``has_randomness: true``. The hidden under-sides never matter after the deal,
so the game is perfect-information.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from itertools import combinations

from agp.game import Game

COLS, ROWS = 4, 3                       # display slots for the 12 stacks

# Symbols 0..3. Letters for serialization, glyphs+colours for the renderer.
SUN, MOON, STARS, COMET = 0, 1, 2, 3
LETTER = "SMTC"                         # Sun, Moon, sTars, Comet
GLYPH = ["☀", "☾", "✶", "☄"]        # sun moon star comet
SYM_NAME = ["Sun", "Moon", "Stars", "Comet"]
SYM_FILL = ["#e8b23a", "#c9d3e0", "#8f6fd8", "#47b3a4"]
SYM_STROKE = "#1f1a14"

# The 12 physical discs: each unordered pair of distinct symbols twice
# (Steffen-Spiele: "each combination appearing twice") -> every symbol is on
# exactly 6 of the 24 faces.
DISCS = [pair for pair in combinations(range(4), 2) for _ in range(2)]

NAMES = ["Red", "Blue"]


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class SolState:
    board: dict = field(default_factory=dict)   # (c,r) -> tuple of symbols, bottom->top
    to_move: int = 0
    ply: int = 0


class Soluna(Game):
    name = "Soluna"

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        faces = [disc[rng.randint(0, 1)] for disc in DISCS]  # random side up
        rng.shuffle(faces)                                   # random table spots
        board = {}
        for i, sym in enumerate(faces):
            board[(i % COLS, i // COLS)] = (sym,)
        return SolState(board=board, to_move=0)

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _legal(self, board, a, b):
        """May the whole stack at `a` be placed on top of the stack at `b`?
        Same top symbol OR same (pre-move) height. Position is irrelevant."""
        sa, sb = board[a], board[b]
        return sa[-1] == sb[-1] or len(sa) == len(sb)

    def legal_moves(self, state):
        board = state.board
        cells = list(board)
        out = []
        for a in cells:
            for b in cells:
                if a != b and self._legal(board, a, b):
                    out.append(f"{a[0]},{a[1]}>{b[0]},{b[1]}")
        return out

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        srcs, dsts = move.split(">")
        src, dst = _cell(srcs), _cell(dsts)
        board = dict(state.board)
        moving = board.pop(src)
        board[dst] = board[dst] + moving        # moved stack lands ON TOP
        return SolState(board=board, to_move=1 - state.to_move,
                        ply=state.ply + 1)

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        # First player with no legal move loses. Never true at the deal:
        # 12 single discs all share height 1, so the opener always has moves.
        board = state.board
        cells = list(board)
        for i, a in enumerate(cells):
            for b in cells[i + 1:]:
                if self._legal(board, a, b):
                    return False
        return True

    def returns(self, state):
        # The player to move is stuck and loses; the last mover wins.
        # Draws are impossible (strictly decreasing stack count, no pass).
        winner = 1 - state.to_move
        return [1.0 if i == winner else -1.0 for i in range(2)]

    # ---- serialise ---------------------------------------------------------
    def serialize(self, state):
        return {
            "board": {f"{c},{r}": "".join(LETTER[s] for s in col)
                      for (c, r), col in state.board.items()},
            "to_move": state.to_move,
            "ply": state.ply,
        }

    def deserialize(self, d):
        return SolState(
            board={_cell(k): tuple(LETTER.index(ch) for ch in v)
                   for k, v in d["board"].items()},
            to_move=d["to_move"], ply=d.get("ply", 0))

    # ---- presentation ------------------------------------------------------
    def _stack_str(self, col):
        return f"{GLYPH[col[-1]]}{len(col)}"

    def describe_move(self, state, move):
        srcs, dsts = move.split(">")
        a, b = state.board[_cell(srcs)], state.board[_cell(dsts)]
        why = "symbol" if a[-1] == b[-1] else "height"
        return f"{self._stack_str(a)} onto {self._stack_str(b)} ({why})"

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), col in state.board.items():
            n = len(col)
            pieces.append({
                "cell": f"{c},{r}",
                "fill": SYM_FILL[col[-1]],
                "stroke": SYM_STROKE,
                "label": GLYPH[col[-1]] + (str(n) if n > 1 else ""),
            })
        if self.is_terminal(state):
            w = 1 - state.to_move
            cap = (f"{NAMES[w]} wins -- {NAMES[state.to_move]} has no move "
                   f"({len(state.board)} stacks left)")
        else:
            cap = (f"{NAMES[state.to_move]} to move · {len(state.board)} stacks "
                   f"(shared discs; last move wins)")
        return {
            "board": {"type": "square", "width": COLS, "height": ROWS},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
