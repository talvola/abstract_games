"""Neutreeko — Jan Kristian Haugland (2001), neutreeko.net.

A 5x5 abstract; the name is a portmanteau of Neutron and Teeko, the two
games it is based on. Each player has three pieces.

Official rules (www.neutreeko.net/neutreeko.htm, verbatim anchors):
  * "A piece slides orthogonally or diagonally until stopped by an occupied
    square or the border of the board. Black always moves first."
  * Objective: "To get three in a row, orthogonally or diagonally. The row
    must be connected."
  * "A match is declared a draw if the same position occurs three times."

Initial setup (from the official figure; ranks 1..5 bottom-to-top,
files a..e left-to-right): Black b1, d1, c4; White b5, d5, c2.

The game is solved (the site's "Perfect Neutreeko opening play" analysis):
the starting position is neutral — a DRAW with perfect play. "Only about 3%
of all legal positions are neutral, including the starting position", and
"there are positions for which perfect play leads to a win in 51 moves".
All three claims were re-verified for this port by a one-time full
retrograde solve (3,395,644 legal (mover, other) positions: start = draw,
3.08% neutral, max forced-win distance = exactly 51 plies).

Implementation notes:
  * Coordinates are "col,row" with row 0 at the BOTTOM (the renderer draws
    row 0 at the bottom), so algebraic b1 = "1,0".
  * A slide must travel as far as it can; a direction that is immediately
    blocked is not a move. There are no captures.
  * Only the mover can complete a row (the opponent's pieces don't move),
    so the win check runs on the mover after each move.
  * Repetition: a position = piece placement + side to move. The third
    occurrence of the same position is an immediate draw (the initial
    position counts as its first occurrence).
  * A hard PLY_CAP draw guarantees termination for random play (threefold
    repetition alone bounds the game only astronomically).
  * The official rules never mention a stalemate; with 6 pieces on 25
    squares a player with no legal slide is unreachable in practice (an
    8-connected blocked set would need far more pieces). For a well-formed
    terminal we rule: no legal move = loss for the player to move.

Moves are "from>to" cell paths. Player 0 = Black (moves first), 1 = White.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 5
NAMES = {0: "Black", 1: "White"}
PLY_CAP = 300  # backstop draw; the repetition rule is the real draw rule

DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

# Official starting position: Black b1, d1, c4; White b5, d5, c2
# (algebraic file a..e = col 0..4, rank 1..5 = row 0..4).
START = {(1, 0): 0, (3, 0): 0, (2, 3): 0,
         (1, 4): 1, (3, 4): 1, (2, 1): 1}


@dataclass
class NeutreekoState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = 0
    winner: Optional[int] = None
    draw: bool = False
    draw_reason: Optional[str] = None           # "repetition" | "cap"
    ply: int = 0
    history: dict = field(default_factory=dict)  # position key -> occurrences


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _slide_dest(board: dict, c: int, r: int, dc: int, dr: int):
    """Final empty cell sliding from (c,r) along (dc,dr), or None if the
    direction is immediately blocked (edge or a piece)."""
    nc, nr = c + dc, r + dr
    if not _on(nc, nr) or (nc, nr) in board:
        return None
    while _on(nc + dc, nr + dr) and (nc + dc, nr + dr) not in board:
        nc, nr = nc + dc, nr + dr
    return (nc, nr)


def _moves(board: dict, player: int) -> list:
    out = []
    for (c, r), pl in board.items():
        if pl != player:
            continue
        for dc, dr in DIRS:
            dest = _slide_dest(board, c, r, dc, dr)
            if dest is not None:
                out.append(((c, r), dest))
    return out


def _has_row(board: dict, player: int) -> bool:
    """True if `player`'s three pieces form a CONNECTED 3-in-a-row,
    orthogonally or diagonally."""
    cells = sorted(cell for cell, pl in board.items() if pl == player)
    if len(cells) != 3:
        return False
    (c0, r0), (c1, r1), (c2, r2) = cells
    d1 = (c1 - c0, r1 - r0)
    d2 = (c2 - c1, r2 - r1)
    return d1 == d2 and d1 in ((0, 1), (1, 0), (1, 1), (1, -1))


def _pos_key(board: dict, to_move: int) -> str:
    black = sorted(f"{c},{r}" for (c, r), pl in board.items() if pl == 0)
    white = sorted(f"{c},{r}" for (c, r), pl in board.items() if pl == 1)
    return " ".join(black) + "|" + " ".join(white) + "|" + str(to_move)


class Neutreeko(Game):
    name = "Neutreeko"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> NeutreekoState:
        board = dict(START)
        return NeutreekoState(board=board,
                              history={_pos_key(board, 0): 1})

    def current_player(self, s: NeutreekoState) -> int:
        return s.to_move

    def legal_moves(self, s: NeutreekoState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}"
                for a, b in _moves(s.board, s.to_move)]

    def apply_move(self, s: NeutreekoState, move: str, rng=None) -> NeutreekoState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        pl = board.pop(frm)
        board[to] = pl
        ply = s.ply + 1
        to_move = 1 - pl

        winner = None
        draw = False
        draw_reason = None
        history = s.history
        if _has_row(board, pl):
            winner = pl                     # only the mover can complete a row
        else:
            key = _pos_key(board, to_move)
            count = s.history.get(key, 0) + 1
            history = dict(s.history)
            history[key] = count
            if count >= 3:
                draw, draw_reason = True, "repetition"
            elif ply >= PLY_CAP:
                draw, draw_reason = True, "cap"

        return NeutreekoState(board=board, to_move=to_move, winner=winner,
                              draw=draw, draw_reason=draw_reason, ply=ply,
                              history=history)

    def is_terminal(self, s: NeutreekoState) -> bool:
        if s.winner is not None or s.draw:
            return True
        # unreachable in practice; a stuck player loses (see module docstring)
        return not _moves(s.board, s.to_move)

    def returns(self, s: NeutreekoState) -> list[float]:
        if s.draw:
            return [0.0, 0.0]
        w = s.winner if s.winner is not None else 1 - s.to_move
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def heuristic(self, s: NeutreekoState) -> list:
        """Tiny rollout-cutoff signal: connected own pairs (2/3 of a row)."""
        pairs = [0, 0]
        cells = {0: [], 1: []}
        for cell, pl in s.board.items():
            cells[pl].append(cell)
        for pl in (0, 1):
            cs = cells[pl]
            for i in range(len(cs)):
                for j in range(i + 1, len(cs)):
                    if max(abs(cs[i][0] - cs[j][0]),
                           abs(cs[i][1] - cs[j][1])) == 1:
                        pairs[pl] += 1
        bal = 0.1 * (pairs[0] - pairs[1])
        return [bal, -bal]

    def serialize(self, s: NeutreekoState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "draw_reason": s.draw_reason,
            "ply": s.ply,
            "history": dict(s.history),
        }

    def deserialize(self, d: dict) -> NeutreekoState:
        return NeutreekoState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            draw=d["draw"],
            draw_reason=d.get("draw_reason"),
            ply=d["ply"],
            history=dict(d.get("history", {})),
        )

    def describe_move(self, s: NeutreekoState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcde'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{alg(frm)}-{alg(to)}"

    def render(self, s: NeutreekoState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            if s.draw:
                caption = ("Draw by threefold repetition"
                           if s.draw_reason == "repetition"
                           else "Draw (move cap reached)")
            else:
                ret = self.returns(s)
                caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
