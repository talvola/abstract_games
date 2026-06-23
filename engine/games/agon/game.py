"""Agon, a.k.a. Queen's Guard / Queen's Guards / Royal Guards (19th-c., 1842).

A two-player traditional game on a HEXAGONAL board of hexagons (a "hexhex") of
side 6 = 91 cells. The single central hex is the THRONE. Each player commands a
QUEEN and six GUARDS and races to enthrone the queen in the centre surrounded
by all six of her guards.

Coordinates are axial (q, r); the cube third coordinate is s = -q-r. A cell is
on the board iff max(|q|, |r|, |s|) <= 5. A cell's RING is its hex distance from
the centre, ring(q,r) = max(|q|, |r|, |s|): the throne is ring 0, the inner ring
around it is ring 1 (6 cells), the outer ring is ring 5 (30 cells).

RULES AS IMPLEMENTED (see rules.md for sourcing/citations):

  * MOVEMENT. On your turn you move one of your pieces one step to an *adjacent*,
    *vacant* cell whose ring is the SAME as (sideways) or SMALLER than (inward)
    the piece's current ring. You may never move to a cell on a larger ring
    (never away from the centre). Only the QUEEN may enter the throne (ring 0);
    a guard may never stand on the throne.

  * CAPTURE (custodial / "the sandwich"). Immediately after a move, any piece
    that is flanked between two ENEMY pieces along a straight hex line — the two
    enemies on directly opposite sides of it — is captured. Capture is by the
    sandwich only; a piece is never captured by moving itself between two enemies
    (only the just-moved player's pieces can newly flank, so a player never
    self-captures). Multiple pieces can be captured by one move.

  * RESCUE (captured pieces are NOT removed from the game). A captured piece is
    lifted off the board into its owner's "hand". On each of the owner's
    subsequent turns, *before making a normal move*, the owner MUST re-enter one
    captured piece: a guard onto any vacant OUTER-RING cell of their choice; the
    queen onto any vacant cell except the throne. Only ONE piece is rescued per
    turn, and the queen must be rescued before any guard. A rescue IS that turn's
    action (you do not also move that turn).

  * WIN. You win the instant your QUEEN stands on the throne (0,0) AND all six
    ring-1 cells adjacent to the throne are occupied by your own GUARDS.

  * FORFEIT LOSS. If your six guards occupy all six ring-1 cells but your queen
    is NOT on the throne, you LOSE (you have walled your own queen out of the
    centre — the classic Agon self-block). The opponent wins.

Termination: piece games can shuffle, so a defensive ply cap forces a draw.

Moves use the platform's clickable cell-path strings:
  * normal move:  "fq,fr>tq,tr"
  * rescue:       "@q,r"  (place a hand piece onto cell q,r; queen first)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

P0, P1 = 0, 1
SIZE = 6              # hexhex side length -> 91 cells
N = SIZE - 1          # 5
THRONE = (0, 0)
PLY_CAP = 400         # defensive draw cap (no published value; guarantees termination)
NAMES = {P0: "Red", P1: "Blue"}

# Three axis directions (each with its opposite) used for the custodial sandwich.
_DIRS = [(1, 0), (0, 1), (1, -1)]


def _neighbors(q: int, r: int):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1), (q + 1, r - 1), (q - 1, r + 1)]


def _ring(q: int, r: int) -> int:
    return max(abs(q), abs(r), abs(q + r))


@lru_cache(maxsize=None)
def _cells() -> tuple:
    out = []
    for q in range(-N, N + 1):
        for r in range(-N, N + 1):
            if abs(q) <= N and abs(r) <= N and abs(q + r) <= N:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set() -> frozenset:
    return frozenset(_cells())


@lru_cache(maxsize=None)
def _outer_ring() -> tuple:
    return tuple(c for c in _cells() if _ring(*c) == N)


@lru_cache(maxsize=None)
def _inner_ring() -> tuple:
    """The six ring-1 cells adjacent to the throne."""
    return tuple(_neighbors(0, 0))


@lru_cache(maxsize=None)
def _outer_cycle() -> tuple:
    """The outer ring traversed as a single 30-cell cycle (for the start setup)."""
    outer = set(_outer_ring())
    start = (N, 0)
    order = [start]
    seen = {start}
    cur = start
    while True:
        nxt = [nb for nb in _neighbors(*cur) if nb in outer and nb not in seen]
        if not nxt:
            break
        cur = nxt[0]
        order.append(cur)
        seen.add(cur)
    return tuple(order)


def _start_setup():
    """Return (board, queens). 180-degree-symmetric standard-style layout:
    queens on opposite corners; six guards spread symmetrically over each
    player's half of the outer ring. Documented in rules.md."""
    cyc = _outer_cycle()
    p0_q = cyc[0]                                  # corner (5,0)
    p1_q = cyc[15]                                 # opposite corner (-5,0)
    p0_g = [cyc[i] for i in (1, 3, 5, 25, 27, 29)]
    p1_g = [cyc[i] for i in (14, 12, 10, 16, 18, 20)]
    board = {}
    board[p0_q] = (P0, "Q")
    board[p1_q] = (P1, "Q")
    for c in p0_g:
        board[c] = (P0, "G")
    for c in p1_g:
        board[c] = (P1, "G")
    return board, {P0: p0_q, P1: p1_q}


def _cell(s: str) -> tuple:
    q, r = s.split(",")
    return int(q), int(r)


@dataclass
class AgonState:
    board: dict = field(default_factory=dict)   # (q,r) -> (owner, kind) kind in {"Q","G"}
    to_move: int = P0
    # captured pieces awaiting rescue, per owner: list of "Q"/"G" kinds.
    hands: dict = field(default_factory=lambda: {P0: [], P1: []})
    winner: Optional[int] = None
    win_kind: Optional[str] = None               # "enthroned" | "forfeit" | "draw"
    last: Optional[tuple] = None                 # last touched cell (for highlight)
    ply: int = 0


def _enemy(p: int) -> int:
    return 1 - p


def _captures(board: dict, mover: int) -> list:
    """List of cells holding an enemy-of-`mover` piece that is now custodially
    flanked by two of `mover`'s pieces along a straight line."""
    out = []
    foe = _enemy(mover)
    for (q, r), (owner, _kind) in board.items():
        if owner != foe:
            continue
        for dq, dr in _DIRS:
            a = board.get((q + dq, r + dr))
            b = board.get((q - dq, r - dr))
            if a is not None and b is not None and a[0] == mover and b[0] == mover:
                out.append((q, r))
                break
    return out


def _check_end(board: dict, queens: dict) -> tuple:
    """Return (winner, win_kind) or (None, None). Enthroned win and the
    self-block forfeit, evaluated for both players."""
    inner = _inner_ring()
    for p in (P0, P1):
        guards_inner = all(
            board.get(c) is not None and board[c] == (p, "G") for c in inner
        )
        if not guards_inner:
            continue
        # All six inner cells are this player's guards.
        if board.get(THRONE) == (p, "Q"):
            return p, "enthroned"
        # Six guards ring an EMPTY-or-enemy throne -> this player forfeits.
        return _enemy(p), "forfeit"
    return None, None


def _queens_from_board(board: dict) -> dict:
    out = {P0: None, P1: None}
    for cell, (owner, kind) in board.items():
        if kind == "Q":
            out[owner] = cell
    return out


class Agon(Game):
    uid = "agon"
    name = "Agon"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AgonState:
        board, _queens = _start_setup()
        return AgonState(board=board, to_move=P0)

    def current_player(self, s: AgonState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------
    def _rescue_moves(self, s: AgonState) -> list:
        """If the mover has pieces in hand, they MUST rescue; return those moves
        (queen first). Empty list if nothing to rescue."""
        hand = s.hands[s.to_move]
        if not hand:
            return []
        occupied = set(s.board.keys())
        if "Q" in hand:
            # Queen must be rescued first: any vacant cell except the throne.
            targets = [c for c in _cells() if c != THRONE and c not in occupied]
        else:
            # Guard: any vacant outer-ring cell.
            targets = [c for c in _outer_ring() if c not in occupied]
        return [f"@{q},{r}" for (q, r) in targets]

    def _normal_moves(self, s: AgonState) -> list:
        occupied = s.board
        out = []
        for (q, r), (owner, kind) in s.board.items():
            if owner != s.to_move:
                continue
            cur_ring = _ring(q, r)
            for (nq, nr) in _neighbors(q, r):
                if (nq, nr) not in _cell_set():
                    continue
                if (nq, nr) in occupied:
                    continue
                tgt_ring = _ring(nq, nr)
                if tgt_ring > cur_ring:
                    continue  # never move away from the centre
                if (nq, nr) == THRONE and kind != "Q":
                    continue  # only the queen may enter the throne
                out.append(f"{q},{r}>{nq},{nr}")
        return out

    def legal_moves(self, s: AgonState) -> list:
        if self.is_terminal(s):
            return []
        rescue = self._rescue_moves(s)
        if rescue:
            return rescue
        moves = self._normal_moves(s)
        if not moves:
            # No legal move (stuck): pass so the engine always has an action.
            return ["pass"]
        return moves

    # -- transition ---------------------------------------------------------
    def apply_move(self, s: AgonState, move: str, rng=None) -> AgonState:
        if self.is_terminal(s):
            raise ValueError("game over")
        mover = s.to_move
        board = dict(s.board)
        hands = {P0: list(s.hands[P0]), P1: list(s.hands[P1])}

        if move == "pass":
            if self._normal_moves(s) or self._rescue_moves(s):
                raise ValueError("pass not available")
            last = s.last
        elif move.startswith("@"):
            # Rescue: place a hand piece.
            if move not in self._rescue_moves(s):
                raise ValueError(f"illegal rescue {move!r}")
            q, r = _cell(move[1:])
            kind = "Q" if "Q" in hands[mover] else "G"
            hands[mover].remove(kind)
            board[(q, r)] = (mover, kind)
            last = (q, r)
        else:
            if self._rescue_moves(s):
                raise ValueError("must rescue a captured piece first")
            if move not in self._normal_moves(s):
                raise ValueError(f"illegal move {move!r}")
            src_s, dst_s = move.split(">")
            src = _cell(src_s)
            dst = _cell(dst_s)
            piece = board.pop(src)
            board[dst] = piece
            last = dst

        # Custodial captures created by this move (lift enemy pieces into hand).
        for cell in _captures(board, mover):
            owner, kind = board.pop(cell)
            hands[owner].append(kind)

        queens = _queens_from_board(board)
        winner, win_kind = _check_end(board, queens)

        ply = s.ply + 1
        if winner is None and ply >= PLY_CAP:
            winner, win_kind = None, "draw"
            terminal_draw = True
        else:
            terminal_draw = False

        ns = AgonState(
            board=board,
            to_move=_enemy(mover),
            hands=hands,
            winner=winner,
            win_kind=win_kind if (winner is not None or terminal_draw) else None,
            last=last,
            ply=ply,
        )
        return ns

    def is_terminal(self, s: AgonState) -> bool:
        if s.winner is not None:
            return True
        if s.win_kind == "draw":
            return True
        return s.ply >= PLY_CAP

    def returns(self, s: AgonState) -> list:
        if s.winner == P0:
            return [1.0, -1.0]
        if s.winner == P1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- (de)serialisation --------------------------------------------------
    def serialize(self, s: AgonState) -> dict:
        return {
            "board": {f"{q},{r}": [o, k] for (q, r), (o, k) in s.board.items()},
            "to_move": s.to_move,
            "hands": {str(P0): list(s.hands[P0]), str(P1): list(s.hands[P1])},
            "winner": s.winner,
            "win_kind": s.win_kind,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> AgonState:
        board = {_cell(k): (v[0], v[1]) for k, v in d["board"].items()}
        h = d.get("hands", {})
        hands = {P0: list(h.get(str(P0), [])), P1: list(h.get(str(P1), []))}
        last = d.get("last")
        return AgonState(
            board=board,
            to_move=d["to_move"],
            hands=hands,
            winner=d.get("winner"),
            win_kind=d.get("win_kind"),
            last=(_cell(last) if last else None),
            ply=d.get("ply", 0),
        )

    # -- notation -----------------------------------------------------------
    def describe_move(self, s: AgonState, move: str) -> str:
        if move == "pass":
            return "pass"
        if move.startswith("@"):
            q, r = _cell(move[1:])
            hand = s.hands[s.to_move]
            kind = "Q" if "Q" in hand else "G"
            label = "Queen" if kind == "Q" else "Guard"
            return f"rescue {label} → {q},{r}"
        return move

    # -- rendering ----------------------------------------------------------
    def render(self, s: AgonState, perspective=None) -> dict:
        pieces = []
        for (q, r), (owner, kind) in s.board.items():
            pieces.append({
                "cell": f"{q},{r}",
                "owner": owner,
                "label": "Q" if kind == "Q" else "",
            })
        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})

        if s.winner is not None:
            if s.win_kind == "forfeit":
                caption = (f"{NAMES[s.winner]} wins "
                           f"({NAMES[_enemy(s.winner)]} self-blocked the throne)")
            else:
                caption = f"{NAMES[s.winner]} wins (queen enthroned)"
        elif s.win_kind == "draw":
            caption = "Draw (move limit)"
        else:
            hand = s.hands[s.to_move]
            if hand:
                what = "queen" if "Q" in hand else "a guard"
                caption = f"{NAMES[s.to_move]} must rescue {what}"
            else:
                caption = f"{NAMES[s.to_move]} to move"

        return {
            "board": {
                "type": "hex",
                "shape": "hexagon",
                "size": SIZE,
                # Mark the central throne.
                "tints": {f"{THRONE[0]},{THRONE[1]}": "#e8c46a"},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
