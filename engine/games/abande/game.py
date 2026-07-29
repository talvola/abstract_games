"""Abande -- Dieter Stein, 2005 ("Connection and stacking").

Implemented from the designer's official rules
(https://spielstein.com/games/abande/rules, version 30 December 2005) and
differentialled move-for-move against the AbstractPlay `gameslib` reference
implementation (see `_diff_ap.py`).

The board starts EMPTY.  Black opens by entering a piece anywhere (the
"initiative"); after that every turn is exactly one of

  * enter a piece from hand onto an empty space **adjacent to the band**
    (all occupied spaces must always form one connected group),
  * move a stack you control (topmost piece owns it) one space **onto an
    adjacent OPPONENT stack** -- never onto an empty space, never onto a
    friendly stack, never above height 3, and never in a way that splits the
    band,
  * pass -- allowed only with an empty hand.

Moving is unlocked only once Black has entered a second piece, so Black
cannot immediately capture White's reply to the initiative.

Two passes in succession end the game.  A stack is "sleeping" -- worth ZERO
-- unless it is adjacent to a stack controlled by the opponent; every other
stack scores its HEIGHT (1/2/3).  Higher score wins; equal scores are an
honest draw.

Boards: the official rules offer three 2-player boards.  This package ships
the square board (7x7 = 49 points, 8 neighbours) as the default and the
hexagonal board (hexhex-4 = 37 points, 6 neighbours) as an option.  See
rules.md for why the snub-square board is not implemented.

Cells are "c,r" (square, col/row 0-6, row 0 at the bottom) and "q,r"
(hexagonal, axial, |q|,|r|,|q+r| <= 3).  Moves are:
  "P@c,r"     enter a piece from hand,
  "c,r>c,r"   move a stack onto an adjacent opponent stack,
  "pass".
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from agp.game import Game

BLACK, WHITE = 0, 1
NAMES = {BLACK: "Black", WHITE: "White"}

PIECES_PER_PLAYER = 18
MAX_HEIGHT = 3

# --- termination backstop -------------------------------------------------
# Every stack move merges two stacks, so it strictly DECREASES the number of
# occupied cells; every placement increases it by one.  Both hands must empty
# before anyone may pass, so a full game contains exactly 36 placements, and
# the final position holds 36 pieces in at least ceil(36/3) = 12 stacks =>
# at most 36 - 12 = 24 stack moves ever.  Non-pass plies <= 60; passes are
# separated by non-passes, so <= 62 of them.  A game therefore cannot exceed
# 122 plies.  PLY_CAP is a safety net that provably never fires (observed
# maximum over 20k random games: ~70).
PLY_CAP = 200

SQ_SIZE = 7
SQ_DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
# Pointy-top axial hex: a ROW (constant r) is horizontal, matching the way the
# hexagonal board is printed (horizontal ranks).
HEX_RADIUS = 3
HEX_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


def _build(cells, dirs):
    cellset = frozenset(cells)
    adj = {c: tuple(sorted((c[0] + d[0], c[1] + d[1])
                           for d in dirs
                           if (c[0] + d[0], c[1] + d[1]) in cellset))
           for c in cellset}
    return tuple(sorted(cellset)), adj


SQ_CELLS, SQ_ADJ = _build(
    [(c, r) for c in range(SQ_SIZE) for r in range(SQ_SIZE)], SQ_DIRS)
HEX_CELLS, HEX_ADJ = _build(
    [(q, r) for q in range(-HEX_RADIUS, HEX_RADIUS + 1)
     for r in range(-HEX_RADIUS, HEX_RADIUS + 1)
     if abs(q + r) <= HEX_RADIUS], HEX_DIRS)

BOARDS = {
    "square": (SQ_CELLS, SQ_ADJ),
    "hex": (HEX_CELLS, HEX_ADJ),
}


def _cell(s):
    a, b = s.split(",")
    return int(a), int(b)


def _s(cell):
    return f"{cell[0]},{cell[1]}"


def cell_name(kind, cell):
    """Board-printed name of a cell ('a1'..'g7'), matching the designer's and
    AbstractPlay's algebraic notation on both boards."""
    if kind == "square":
        c, r = cell
        return chr(ord("a") + c) + str(r + 1)
    q, r = cell
    letter = HEX_RADIUS - r                       # row 'a' is the bottom row
    qmin = max(-HEX_RADIUS, -HEX_RADIUS - r)
    return chr(ord("a") + letter) + str(q - qmin + 1)


@dataclass
class AbState:
    kind: str = "square"
    board: dict = field(default_factory=dict)   # cell -> tuple of owners, bottom->top
    hands: tuple = (PIECES_PER_PLAYER, PIECES_PER_PLAYER)
    to_move: int = BLACK
    passes: int = 0                              # consecutive passes just made
    ply: int = 0
    last: object = None                          # (src|None, dst) of the last move


class Abande(Game):

    @property
    def num_players(self):
        return 2

    # ---- geometry ------------------------------------------------------
    @staticmethod
    def cells(state):
        return BOARDS[state.kind][0]

    @staticmethod
    def adj(state):
        return BOARDS[state.kind][1]

    # ---- setup ---------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        kind = opts.get("board", "square")
        if kind not in BOARDS:
            kind = "square"
        return AbState(kind=kind, board={},
                       hands=(PIECES_PER_PLAYER, PIECES_PER_PLAYER),
                       to_move=BLACK, passes=0, ply=0, last=None)

    def current_player(self, state):
        return state.to_move

    # ---- rules ---------------------------------------------------------
    @staticmethod
    def _connected(board, adj):
        """Do the occupied cells form a single band?"""
        if len(board) <= 1:
            return True
        start = next(iter(board))
        seen = {start}
        todo = [start]
        while todo:
            cur = todo.pop()
            for n in adj[cur]:
                if n in board and n not in seen:
                    seen.add(n)
                    todo.append(n)
        return len(seen) == len(board)

    def _placements(self, state):
        """Empty cells adjacent to the band (all cells when the board is empty)."""
        board = state.board
        if not board:
            return list(self.cells(state))
        adj = self.adj(state)
        out = set()
        for cell in board:
            for n in adj[cell]:
                if n not in board:
                    out.add(n)
        return sorted(out)

    def _stack_moves(self, state):
        """Legal stack moves for the side to move (empty until Black has
        entered a second piece)."""
        if state.hands[BLACK] > PIECES_PER_PLAYER - 2:
            return []
        board, adj, me = state.board, self.adj(state), state.to_move
        out = []
        for src, col in board.items():
            if col[-1] != me:
                continue
            for dst in adj[src]:
                tgt = board.get(dst)
                if tgt is None or tgt[-1] == me:
                    continue
                if len(col) + len(tgt) > MAX_HEIGHT:
                    continue
                nb = dict(board)
                del nb[src]
                nb[dst] = tgt + col
                if self._connected(nb, adj):
                    out.append((src, dst))
        return out

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        moves = []
        if state.hands[state.to_move] > 0:
            moves += [f"P@{_s(c)}" for c in self._placements(state)]
        else:
            moves.append("pass")
        moves += [f"{_s(a)}>{_s(b)}" for a, b in self._stack_moves(state)]
        return sorted(moves)

    def apply_move(self, state, move, rng=None):
        board = dict(state.board)
        hands = list(state.hands)
        me = state.to_move
        if move == "pass":
            passes = state.passes + 1
            last = state.last
        elif move.startswith("P@"):
            dst = _cell(move[2:])
            board[dst] = (me,)
            hands[me] -= 1
            passes = 0
            last = (None, dst)
        else:
            a, b = move.split(">")
            src, dst = _cell(a), _cell(b)
            col = board.pop(src)
            board[dst] = board[dst] + col
            passes = 0
            last = (src, dst)
        return AbState(kind=state.kind, board=board, hands=tuple(hands),
                       to_move=1 - me, passes=passes, ply=state.ply + 1,
                       last=last)

    def is_terminal(self, state):
        return state.passes >= 2 or state.ply >= PLY_CAP

    # ---- scoring -------------------------------------------------------
    def score(self, state, player):
        """Sum of the HEIGHTS of the player's non-sleeping stacks.  A stack is
        sleeping (worth zero) unless it touches a stack the opponent controls."""
        board, adj = state.board, self.adj(state)
        total = 0
        for cell, col in board.items():
            if col[-1] != player:
                continue
            for n in adj[cell]:
                other = board.get(n)
                if other is not None and other[-1] != player:
                    total += len(col)
                    break
        return total

    def scores(self, state):
        return (self.score(state, BLACK), self.score(state, WHITE))

    def returns(self, state):
        b, w = self.scores(state)
        if b > w:
            return [1.0, -1.0]
        if w > b:
            return [-1.0, 1.0]
        return [0.0, 0.0]        # an equal score is an honest draw

    def heuristic(self, state):
        b, w = self.scores(state)
        v = math.tanh((b - w) / 6.0)
        return [v, -v]

    # ---- persistence ---------------------------------------------------
    def serialize(self, state):
        return {
            "kind": state.kind,
            "board": {_s(c): list(col) for c, col in sorted(state.board.items())},
            "hands": list(state.hands),
            "to_move": state.to_move,
            "passes": state.passes,
            "ply": state.ply,
            "last": (None if state.last is None
                     else [None if state.last[0] is None else _s(state.last[0]),
                           _s(state.last[1])]),
        }

    def deserialize(self, data):
        last = data.get("last")
        return AbState(
            kind=data.get("kind", "square"),
            board={_cell(k): tuple(v) for k, v in data["board"].items()},
            hands=tuple(data["hands"]),
            to_move=data["to_move"],
            passes=data.get("passes", 0),
            ply=data.get("ply", 0),
            last=(None if last is None
                  else (None if last[0] is None else _cell(last[0]), _cell(last[1]))),
        )

    # ---- notation ------------------------------------------------------
    def describe_move(self, state, move):
        kind = state.kind
        if move == "pass":
            return "pass"
        if move.startswith("P@"):
            return cell_name(kind, _cell(move[2:]))
        a, b = move.split(">")
        src, dst = _cell(a), _cell(b)
        h = len(state.board.get(src, ())) + len(state.board.get(dst, ()))
        return f"{cell_name(kind, src)}-{cell_name(kind, dst)} ({h})"

    # ---- presentation --------------------------------------------------
    def render(self, state, perspective=None):
        if state.kind == "hex":
            board = {"type": "hex", "shape": "hexagon", "size": HEX_RADIUS + 1}
        else:
            board = {"type": "square", "width": SQ_SIZE, "height": SQ_SIZE}

        pieces = [{"cell": _s(cell), "owner": col[-1], "stack": list(col)}
                  for cell, col in sorted(state.board.items())]

        highlights = []
        if state.last is not None:
            src, dst = state.last
            highlights.append({"cell": _s(dst), "kind": "last-move"})
            if src is not None:
                highlights.append({"cell": _s(src), "kind": "last-move"})

        b, w = self.scores(state)
        if self.is_terminal(state):
            if b > w:
                cap = f"Black wins {b}-{w}"
            elif w > b:
                cap = f"White wins {w}-{b}"
            else:
                cap = f"Draw {b}-{w}"
        else:
            cap = (f"{NAMES[state.to_move]} to move · score "
                   f"B {b} / W {w} · hand "
                   f"B {state.hands[BLACK]} / W {state.hands[WHITE]}")
            if state.passes == 1:
                cap += " · opponent passed"

        return {
            "board": board,
            "pieces": pieces,
            "highlights": highlights,
            "reserve": {"0": {"P": state.hands[BLACK]},
                        "1": {"P": state.hands[WHITE]}},
            "caption": cap,
        }
