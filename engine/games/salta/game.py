"""Salta -- Konrad Heinrich Büttgenbach's 1899 race game on a 10x10 draughts
board (the Belle Époque "humanistic game").

Primary source: Ralf Gering, "Salta -- The Humanistic Game", Abstract Games
issue 8 (2001), based on the original 1902 rules booklet. Cross-checked with
Wikipedia "Salta (game)" and the nestorgames 2018 rulebook (whose "1901
edition" variant is exactly this ruleset).

Each side has 15 pieces on the dark squares of its first three ranks:
stars 1-5 (rank 1), moons 1-5 (rank 2), suns 1-5 (rank 3), numbered from each
player's LEFT. All play is on dark squares (a1 dark). Pieces move one square
diagonally in ANY direction to a vacant square. If an enemy piece stands
diagonally IN FRONT of one of your pieces with the square immediately beyond
vacant, you MUST jump it (jumps are compulsory) -- but the jumped piece is NOT
removed (there are no captures in Salta). Only ONE jump per turn (no chains),
forward only, and never over your own pieces. It is forbidden to play a move
that leaves the opponent with no legal move (the blockade rule).

GOAL: be first to shift your whole opening position seven rows forward, each
row keeping its original left-to-right order (so each numbered piece has one
exact target square). Because the first player (historically Green) has a
one-tempo advantage, the original point system subtracts one point from him:
if he completes his goal while the opponent needs exactly one more move, the
game is a DRAW; the second player completing first always wins.

TERMINATION (from the original rules): at the latest the game is "completed"
after 120 moves by each player (240 plies). Each side's remaining move count
is then the sum, over its pieces, of each piece's minimum diagonal-step
distance to its target square ignoring all other pieces (Wikipedia's reading
of the original counting rule); the difference, minus one point from the
first player, decides winner/points/draw. This makes the game provably finite
-- no extra no-progress counter is needed.

Player 0 moves first (historically "Green", green symbols on black pieces;
rendered red here). Player 1 is historically "Red" (rendered blue).
Moves are "c,r>c,r" cell paths; "pass" exists only for the theoretically
unreachable fully-blockaded case.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 10
PLY_CAP = 240          # 120 moves each -- the game is "completed" at the latest here
NAMES = {0: "Red", 1: "Blue"}
FILL = {0: "#d23b3b", 1: "#3b6fd2"}     # platform seat colours (see web/src/colors.js)
GLYPH = {"star": "★", "moon": "☾", "sun": "☼"}

# ---- setup & targets (Abstract Games #8 diagrams, verified square by square) --
# Player 0's start: stars 1-5 on a1,c1,e1,g1,i1; moons 1-5 on b2,d2,f2,h2,j2;
# suns 1-5 on a3,c3,e3,g3,i3 (numbered from the player's left). Player 1's
# setup is the 180-degree rotation (so red star 1 is on j10, etc.).
# Target = the opening position shifted seven rows forward, order retained --
# the forced order-preserving map between each rank's five dark squares.


def _rot(sq):
    return (N - 1 - sq[0], N - 1 - sq[1])


def _build_tables():
    start0, target0 = {}, {}
    for n in range(1, 6):
        start0[("star", n)] = (2 * n - 2, 0)    # a1 c1 e1 g1 i1
        start0[("moon", n)] = (2 * n - 1, 1)    # b2 d2 f2 h2 j2
        start0[("sun", n)] = (2 * n - 2, 2)     # a3 c3 e3 g3 i3
        target0[("star", n)] = (2 * n - 1, 7)   # b8 d8 f8 h8 j8
        target0[("moon", n)] = (2 * n - 2, 8)   # a9 c9 e9 g9 i9
        target0[("sun", n)] = (2 * n - 1, 9)    # b10 d10 f10 h10 j10
    start1 = {k: _rot(v) for k, v in start0.items()}
    target1 = {k: _rot(v) for k, v in target0.items()}
    return (start0, start1), (target0, target1)


START, TARGET = _build_tables()


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _dist(a, b):
    """Minimum number of diagonal steps between two dark squares, ignoring all
    pieces (the original counting rule per Wikipedia's reading). On the
    rotated lattice x=c+r, y=c-r a diagonal step changes exactly one of x,y
    by 2, so the distance is (|dx| + |dy|) / 2 -- achievable within the board
    via a zig-zag."""
    dx = abs((a[0] + a[1]) - (b[0] + b[1]))
    dy = abs((a[0] - a[1]) - (b[0] - b[1]))
    return (dx + dy) // 2


def _start_board():
    board = {}
    for pl in (0, 1):
        for (kind, n), sq in START[pl].items():
            board[sq] = (pl, kind, n)
    return board


def _needed(board, player):
    """Total remaining moves for `player`: sum of each piece's free diagonal
    distance to its own target square."""
    total = 0
    for sq, (pl, kind, n) in board.items():
        if pl == player:
            total += _dist(sq, TARGET[player][(kind, n)])
    return total


def _forward(player):
    return 1 if player == 0 else -1


def _jumps(board, player):
    """Compulsory jumps: an enemy piece diagonally in FRONT with the square
    beyond vacant. Forward only, single jump, never over own pieces; the
    jumped piece stays on the board."""
    dr = _forward(player)
    out = []
    for (c, r), (pl, _k, _n) in board.items():
        if pl != player:
            continue
        for dc in (-1, 1):
            over = (c + dc, r + dr)
            land = (c + 2 * dc, r + 2 * dr)
            if not _on(*land) or land in board:
                continue
            occ = board.get(over)
            if occ is not None and occ[0] != player:
                out.append(((c, r), land))
    return out


def _steps(board, player):
    out = []
    for (c, r), (pl, _k, _n) in board.items():
        if pl != player:
            continue
        for dc in (-1, 1):
            for dr in (-1, 1):
                t = (c + dc, r + dr)
                if _on(*t) and t not in board:
                    out.append(((c, r), t))
    return out


def _has_any_move(board, player):
    dr = _forward(player)
    for (c, r), (pl, _k, _n) in board.items():
        if pl != player:
            continue
        for dc in (-1, 1):
            for sr in (-1, 1):
                t = (c + dc, r + sr)
                if _on(*t) and t not in board:
                    return True
            over = (c + dc, r + dr)
            land = (c + 2 * dc, r + 2 * dr)
            occ = board.get(over)
            if (occ is not None and occ[0] != player and _on(*land)
                    and land not in board):
                return True
    return False


@dataclass
class SaltaState:
    board: dict = field(default_factory=dict)   # (c, r) -> (player, kind, n)
    to_move: int = 0
    ply: int = 0
    done: bool = False                          # goal reached (winner / tempo draw)
    winner: Optional[int] = None                # only meaningful when done


class Salta(Game):
    name = "Salta"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SaltaState:
        return SaltaState(board=_start_board())

    def current_player(self, s: SaltaState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _opp_mobile_after(self, board, frm, to, opp):
        b2 = dict(board)
        b2[to] = b2.pop(frm)
        return _has_any_move(b2, opp)

    def _move_pairs(self, s: SaltaState):
        """(from, to) pairs. Jump obligation + blockade rule. Precedence
        (documented in rules.md): the blockade prohibition is absolute, so a
        totally-blockading move is illegal outright and the jump obligation
        applies among the remaining moves; if every move would blockade, the
        blockade rule is unenforceable and the plain jump-priority moves
        stand."""
        p, opp = s.to_move, 1 - s.to_move
        jumps = _jumps(s.board, p)
        steps = _steps(s.board, p)
        cand = jumps if jumps else steps
        if not cand:
            return []
        ok = [m for m in cand if self._opp_mobile_after(s.board, m[0], m[1], opp)]
        if ok:
            return ok
        if jumps and steps:
            ok = [m for m in steps
                  if self._opp_mobile_after(s.board, m[0], m[1], opp)]
            if ok:
                return ok
        return cand

    def legal_moves(self, s: SaltaState) -> list[str]:
        if self.is_terminal(s):
            return []
        pairs = self._move_pairs(s)
        if not pairs:
            return ["pass"]     # fully blockaded (theoretically unreachable)
        return [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for f, t in pairs]

    # ---- state transitions -------------------------------------------------
    def apply_move(self, s: SaltaState, move: str, rng=None) -> SaltaState:
        if move == "pass":
            return SaltaState(board=dict(s.board), to_move=1 - s.to_move,
                              ply=s.ply + 1, done=s.done, winner=s.winner)
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        piece = board.pop(frm)
        board[to] = piece
        pl = piece[0]
        done, winner = False, None
        if _needed(board, pl) == 0:
            # mover completed the goal position
            done = True
            if pl == 0:
                # first-player tempo compensation: opponent needing exactly one
                # more move means a zero-point margin -> draw
                winner = 0 if _needed(board, 1) >= 2 else None
            else:
                winner = 1
        return SaltaState(board=board, to_move=1 - pl, ply=s.ply + 1,
                          done=done, winner=winner)

    # ---- results -----------------------------------------------------------
    # Original point system (Gering): each side's surplus = opponent's needed
    # moves minus its own; one point is then subtracted from the FIRST player's
    # surplus (tempo compensation). The winner keeps a positive surplus, the
    # loser scores 0; both non-positive = draw. So with diff = D1 - D0:
    #   player 0 wins by diff-1 when diff >= 2, player 1 wins by -diff when
    #   diff <= -1, and diff in {0, 1} is a draw. The Krone-Grotewold 1901
    #   game ("Red wins by 27") pins this reading in the selftest.
    def _surpluses(self, s: SaltaState):
        diff = _needed(s.board, 1) - _needed(s.board, 0)
        return diff - 1, -diff      # (player 0 surplus, player 1 surplus)

    def is_terminal(self, s: SaltaState) -> bool:
        return s.done or s.ply >= PLY_CAP

    def returns(self, s: SaltaState) -> list[float]:
        if s.done:
            if s.winner is None:
                return [0.0, 0.0]
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        s0, s1 = self._surpluses(s)
        if s0 > 0:
            return [1.0, -1.0]
        if s1 > 0:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: SaltaState) -> list[float]:
        s0, _s1 = self._surpluses(s)
        v = math.tanh((s0 + 0.5) / 10.0)    # centre of the {0,1} draw band
        return [v, -v]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: SaltaState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, kind, n]
                      for (c, r), (pl, kind, n) in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "done": s.done,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> SaltaState:
        return SaltaState(
            board={_cell(k): (v[0], v[1], v[2]) for k, v in d["board"].items()},
            to_move=d["to_move"], ply=d["ply"],
            done=d.get("done", False), winner=d.get("winner"),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s: SaltaState, move: str) -> str:
        if move == "pass":
            return "pass (blockaded)"
        frm, to = (_cell(x) for x in move.split(">"))
        pl, kind, n = s.board[frm]
        sep = ":" if abs(to[1] - frm[1]) == 2 else "-"
        alg = lambda sq: f"{chr(97 + sq[0])}{sq[1] + 1}"
        return f"{GLYPH[kind]}{n} {alg(frm)}{sep}{alg(to)}"

    def render(self, s: SaltaState, perspective=None) -> dict:
        tints = {}
        for sq in TARGET[0].values():
            tints[f"{sq[0]},{sq[1]}"] = "#ffdede"    # player 0's goal squares
        for sq in TARGET[1].values():
            tints[f"{sq[0]},{sq[1]}"] = "#dedeff"    # player 1's goal squares
        pieces = [{"cell": f"{c},{r}", "owner": pl,
                   "label": f"{GLYPH[kind]}{n}",
                   "fill": FILL[pl], "stroke": "#ffffff"}
                  for (c, r), (pl, kind, n) in s.board.items()]
        if self.is_terminal(s):
            s0, s1 = self._surpluses(s)
            if s.done:
                if s.winner is None:
                    caption = "Draw — goal reached, one tempo apart"
                elif s.winner == 0:
                    caption = f"{NAMES[0]} wins by {s0} points (goal reached)"
                else:
                    caption = f"{NAMES[1]} wins by {s1} points (goal reached)"
            else:
                if s0 > 0:
                    caption = f"{NAMES[0]} wins by {s0} points (120-move rule)"
                elif s1 > 0:
                    caption = f"{NAMES[1]} wins by {s1} points (120-move rule)"
                else:
                    caption = "Draw (120-move rule)"
        else:
            caption = f"{NAMES[s.to_move]} to move — move {s.ply // 2 + 1}"
        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
