"""Starchess (Polgár Superstar Chess) — László Polgár, Hungary.

A chess variant on a 37-cell **hexagram** (Star of David) whose cells carry the
printed numbers 1-37. Two signatures set it apart from every other hex chess:

1. **The players build their own back rank.** Only the five pawns of each side
   start on the board; the K, Q, R, B and N are *placed alternately, one at a
   time*, on the five free back-rank cells before play — "1 of 14400" openings
   (= (5!)^2), as the official rules sheet puts it.
2. **There is no hex-diagonal movement at all.** The rook moves *only
   vertically* (2 directions), the bishop on the *four non-vertical
   orthogonals*, and the queen on all six orthogonals. Knight and pawn are as in
   Gliński's hexagonal chess, but there is **no en passant and no castling**.

Board & coordinates
-------------------
Cells are axial hex coordinates "q,r"; q is the printed board's vertical FILE
(nine files of heights 1, 2, 7, 6, 5, 6, 7, 2, 1 from left to right) and r grows
downwards inside a file, so White's forward direction is (0,-1). Cell **numbers
1-37** run bottom-to-top within a file, files left to right — exactly the
numbering printed on the commercial board (see rules.md). `describe_move` and
`board.labels` both use those official numbers; the axial ids exist only so the
generic hex renderer can draw the star.

The cell set is the union of the two triangles {q,-q-r,r <= 2} and
{q,-q-r,r >= -2}, i.e. a hexhex of radius 2 (19 cells) plus six 3-cell points.

Rules implemented (official rules sheet + the 16-image rules gallery at
polgarstarchess.com, cross-checked cell-by-cell against Árpád Rusz's Zillions
implementation linked from the site's Downloads page; see rules.md)
-------------------------------------------------------------------
* Setup phase: White places first (as in the Zillions file), then the sides
  alternate, each dropping one of K/Q/R/B/N onto one of its five empty back-rank
  cells (White 4 11 17 22 28, Black 10 16 21 27 34). Ten plies, White then moves.
* Rook: the two vertical rays. Bishop: the four oblique (non-vertical)
  orthogonal rays. Queen: all six orthogonal rays. King: one orthogonal step;
  NO castling. Knight: the 12-target hex leap (as Gliński).
* Pawn: one vacant cell straight forward; two cells forward only as its very
  first move (a pawn that reached a start cell by capturing is a "limping pawn"
  and has lost the double step, so unmoved-ness is tracked per pawn, not per
  square). It captures one cell on either forward oblique orthogonal. NO en
  passant. It promotes — compulsorily, to Q/R/B/N — only on the *opponent's
  back rank*; a pawn that drifts into files 1-2 or 8-9 (cells 1 2 3 35 36 37)
  can never promote from there ("dead pawn" / "mummy").
* Checkmate wins. Stalemate is a DRAW (the official sheet lists it among the
  drawing results). Further draws: threefold repetition, the 50-move rule, and
  bare king vs bare king (the only material that provably cannot mate here —
  K+B and K+N both mate, see the official mate-in-1 problems 2 and 3).
  Checkmate OUTRANKS all of those: a mate delivered on the ply that trips the
  50-move counter is a win, not a draw.
* A hard ply cap exists purely as a termination backstop and can never be the
  reason a game ends: the 50-move counter draws 100 plies after the last
  capture/pawn move; there are at most 18 captures (kings are never taken) and
  each of the ten pawns makes at most 8 non-capturing moves (a non-capturing
  pawn move strictly decreases r for White / increases it for Black, and the
  board spans r = 4..-4), so at most 98 irreversible events and hence
  10 + 98 + 100*99 = 10 008 plies (cap: 20 000). See rules.md for the measured
  confirmation that no outcome depends on the constant.

Move strings: "L@q,r" during the setup phase; "q1,r1>q2,r2" afterwards, with an
"=Q/=R/=B/=N" suffix on promotions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
PLY_CAP = 20000            # pure backstop; the 50-move rule always fires first

# --- the 37-cell hexagram, in printed board order --------------------------
# file q -> (top-most r that is NOT the numbering start, ...) -- listed as
# (r_bottom, r_top): numbering runs bottom-to-top, i.e. r descending.
_FILE_RANGE = {-4: (2, 2), -3: (2, 1), -2: (4, -2), -1: (3, -2), 0: (2, -2),
               1: (2, -3), 2: (2, -4), 3: (-1, -2), 4: (-2, -2)}
_CELLS = []
for _q in range(-4, 5):
    _rb, _rt = _FILE_RANGE[_q]
    for _r in range(_rb, _rt - 1, -1):
        _CELLS.append((_q, _r))
CELLS = tuple(_CELLS)                       # index i  <-> printed number i+1
NUM = {c: i + 1 for i, c in enumerate(CELLS)}
BY_NUM = {i + 1: c for i, c in enumerate(CELLS)}
ON = frozenset(CELLS)

# --- directions (axial q,r) -------------------------------------------------
UP, DOWN = (0, -1), (0, 1)
VERT = [UP, DOWN]                                   # rook
OBLIQUE = [(-1, 0), (1, -1), (1, 0), (-1, 1)]       # bishop: up-left, up-right,
ORTHO = VERT + OBLIQUE                              #   down-right, down-left
# The 12-target hex knight leap (2 orthogonal steps + 1 at 60 deg).
KNIGHT = [(1, -3), (-1, -2), (3, -2), (2, -3), (2, 1), (3, -1),
          (-1, 3), (1, 2), (-3, 2), (-2, 3), (-2, -1), (-3, 1)]

PAWN_FWD = {WHITE: UP, BLACK: DOWN}
PAWN_CAPS = {WHITE: [(-1, 0), (1, -1)], BLACK: [(1, 0), (-1, 1)]}

BACK_NUMS = {WHITE: (4, 11, 17, 22, 28), BLACK: (10, 16, 21, 27, 34)}
PAWN_NUMS = {WHITE: (5, 12, 18, 23, 29), BLACK: (9, 15, 20, 26, 33)}
BACK_RANK = {p: tuple(BY_NUM[n] for n in ns) for p, ns in BACK_NUMS.items()}
PAWN_START = {p: tuple(BY_NUM[n] for n in ns) for p, ns in PAWN_NUMS.items()}
# A pawn promotes on the OPPONENT's back rank -- and nowhere else.
PROMO_CELLS = {WHITE: frozenset(BACK_RANK[BLACK]), BLACK: frozenset(BACK_RANK[WHITE])}
PROMO_CHOICES = ("Q", "R", "B", "N")
SETUP_PIECES = ("K", "Q", "R", "B", "N")

# --- precomputed geometry ---------------------------------------------------
_STEPS = {c: {d: (c[0] + d[0], c[1] + d[1]) for d in ORTHO
              if (c[0] + d[0], c[1] + d[1]) in ON} for c in CELLS}
_KNIGHT_TO = {c: tuple(t for t in ((c[0] + d[0], c[1] + d[1]) for d in KNIGHT)
                       if t in ON) for c in CELLS}


def _ray(cell, d):
    out = []
    q, r = cell[0] + d[0], cell[1] + d[1]
    while (q, r) in ON:
        out.append((q, r))
        q, r = q + d[0], r + d[1]
    return tuple(out)


_RAYS = {c: {d: _ray(c, d) for d in ORTHO} for c in CELLS}
SLIDE_DIRS = {"R": tuple(VERT), "B": tuple(OBLIQUE), "Q": tuple(ORTHO)}


def cell_name(cell) -> str:
    """Axial (q,r) -> the number printed on the official board, e.g. '19'."""
    return str(NUM[cell])


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _setup_board() -> dict:
    b = {}
    for p in (WHITE, BLACK):
        for c in PAWN_START[p]:
            b[c] = (p, "P")
    return b


@dataclass
class SState:
    board: dict = field(default_factory=_setup_board)   # (q,r) -> (owner, letter)
    to_move: int = WHITE
    # pieces still waiting to be placed in the opening setup phase
    hands: dict = field(default_factory=lambda: {WHITE: dict.fromkeys(SETUP_PIECES, 1),
                                                 BLACK: dict.fromkeys(SETUP_PIECES, 1)})
    # cells holding a pawn that has NEVER moved (the double-step right; a pawn
    # that captured onto a start cell is a "limping pawn" and is not in here)
    unmoved: frozenset = field(
        default_factory=lambda: frozenset(PAWN_START[WHITE]) | frozenset(PAWN_START[BLACK]))
    halfmove: int = 0          # plies since the last capture / pawn move
    ply: int = 0
    reps: dict = field(default_factory=dict)
    last: Optional[tuple] = None


def _poskey(board, to_move, unmoved) -> str:
    items = sorted((q, r, o, t) for (q, r), (o, t) in board.items())
    um = ";".join(f"{q},{r}" for q, r in sorted(unmoved))
    return f"{to_move}|{um}|" + ";".join(f"{q},{r},{o},{t}" for q, r, o, t in items)


def _attacked(board: dict, cell, by: int) -> bool:
    """Is `cell` attacked by any piece of player `by`?"""
    for dq, dr in PAWN_CAPS[by]:
        p = board.get((cell[0] - dq, cell[1] - dr))
        if p is not None and p[0] == by and p[1] == "P":
            return True
    for t in _KNIGHT_TO[cell]:
        p = board.get(t)
        if p is not None and p[0] == by and p[1] == "N":
            return True
    for t in _STEPS[cell].values():
        p = board.get(t)
        if p is not None and p[0] == by and p[1] == "K":
            return True
    rays = _RAYS[cell]
    for d in ORTHO:
        letters = ("R", "Q") if d in (UP, DOWN) else ("B", "Q")
        for t in rays[d]:
            p = board.get(t)
            if p is not None:
                if p[0] == by and p[1] in letters:
                    return True
                break
    return False


def _king_cell(board: dict, player: int):
    for cell, (o, t) in board.items():
        if o == player and t == "K":
            return cell
    return None


def _in_check(board: dict, player: int) -> bool:
    k = _king_cell(board, player)
    return k is not None and _attacked(board, k, 1 - player)


class Starchess(Game):

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SState:
        return SState()

    def current_player(self, s: SState) -> int:
        return s.to_move

    # ---- opening setup phase ----------------------------------------------
    @staticmethod
    def in_setup(s: SState) -> bool:
        return any(n > 0 for h in s.hands.values() for n in h.values())

    def _setup_drops(self, s: SState) -> list:
        hand = s.hands.get(s.to_move, {})
        free = [c for c in BACK_RANK[s.to_move] if c not in s.board]
        return [f"{L}@{c[0]},{c[1]}" for L in SETUP_PIECES if hand.get(L, 0) > 0
                for c in free]

    def _apply_setup(self, s: SState, move: str) -> SState:
        letter, cs = move.split("@")
        to = _cell(cs)
        me = s.to_move
        if (letter not in SETUP_PIECES or s.hands.get(me, {}).get(letter, 0) <= 0
                or to not in BACK_RANK[me] or to in s.board):
            raise ValueError(f"illegal move {move!r}")
        board = dict(s.board)
        board[to] = (me, letter)
        hands = {p: dict(h) for p, h in s.hands.items()}
        hands[me][letter] -= 1
        if hands[me][letter] <= 0:
            del hands[me][letter]
        nxt = 1 - me
        if not hands.get(nxt):            # opponent finished: keep placing
            nxt = me if hands.get(me) else WHITE
        done = not any(h for h in hands.values())
        reps = {_poskey(board, nxt, s.unmoved): 1} if done else {}
        return SState(board=board, to_move=nxt, hands=hands, unmoved=s.unmoved,
                      halfmove=0, ply=s.ply + 1, reps=reps, last=(to, to))

    # ---- move generation ---------------------------------------------------
    def _pseudo(self, s: SState) -> list:
        """Pseudo-legal moves as (frm, to, promo_or_None)."""
        out = []
        me = s.to_move
        board = s.board
        for cell, (owner, t) in board.items():
            if owner != me:
                continue
            if t == "P":
                self._pawn_moves(s, cell, out)
            elif t == "N":
                for tgt in _KNIGHT_TO[cell]:
                    occ = board.get(tgt)
                    if occ is None or occ[0] != me:
                        out.append((cell, tgt, None))
            elif t == "K":
                for tgt in _STEPS[cell].values():
                    occ = board.get(tgt)
                    if occ is None or occ[0] != me:
                        out.append((cell, tgt, None))
            else:
                rays = _RAYS[cell]
                for d in SLIDE_DIRS[t]:
                    for tgt in rays[d]:
                        occ = board.get(tgt)
                        if occ is None:
                            out.append((cell, tgt, None))
                        else:
                            if occ[0] != me:
                                out.append((cell, tgt, None))
                            break
        return out

    def _pawn_moves(self, s: SState, cell, out):
        me = s.to_move
        board = s.board
        promo = PROMO_CELLS[me]
        fq, fr = PAWN_FWD[me]
        one = (cell[0] + fq, cell[1] + fr)
        if one in ON and one not in board:
            if one in promo:
                for pc in PROMO_CHOICES:
                    out.append((cell, one, pc))
            else:
                out.append((cell, one, None))
                # double step: only a pawn that has NEVER moved (limping pawn)
                if cell in s.unmoved:
                    two = (one[0] + fq, one[1] + fr)
                    if two in ON and two not in board:
                        out.append((cell, two, None))
        for dq, dr in PAWN_CAPS[me]:
            tgt = (cell[0] + dq, cell[1] + dr)
            occ = board.get(tgt)
            if occ is not None and occ[0] != me:
                if tgt in promo:
                    for pc in PROMO_CHOICES:
                        out.append((cell, tgt, pc))
                else:
                    out.append((cell, tgt, None))

    @staticmethod
    def _apply_board(board: dict, frm, to, promo) -> dict:
        nb = dict(board)
        owner, t = nb.pop(frm)
        nb[to] = (owner, promo if promo else t)
        return nb

    def _legal(self, s: SState) -> list:
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        me = s.to_move
        out = [m for m in self._pseudo(s)
               if not _in_check(self._apply_board(s.board, m[0], m[1], m[2]), me)]
        object.__setattr__(s, "_legal_cache", out)
        return out

    @staticmethod
    def _mstr(frm, to, promo) -> str:
        return f"{frm[0]},{frm[1]}>{to[0]},{to[1]}" + (f"={promo}" if promo else "")

    # ---- draws -------------------------------------------------------------
    def _draw_reason(self, s: SState) -> Optional[str]:
        if self.in_setup(s):
            return None
        # CHECKMATE (and stalemate) OUTRANK every automatic draw: the previous
        # move already ended the game. Without this a mate delivered on the very
        # ply that trips the 50-move counter — e.g. the published mate-in-1 #4
        # played at halfmove 99 — would score 0-0 instead of 1-0. (FIDE 5.1.1 /
        # 9.6: the automatic draws apply only if the last move was not mate.)
        # Threefold + mate and K-v-K + mate are impossible, so in practice this
        # guards exactly the 50-move counter; it is checked for all of them so
        # the caption also names stalemate rather than whichever clock expired.
        if not self._legal(s):
            return None
        if s.halfmove >= 100:
            return "50-move rule"
        if s.reps and max(s.reps.values()) >= 3:
            return "threefold repetition"
        if len(s.board) == 2:
            return "insufficient material"          # bare king vs bare king
        if s.ply >= PLY_CAP:
            return "move limit"
        return None

    # ---- Game interface ----------------------------------------------------
    def legal_moves(self, s: SState) -> list:
        if self.in_setup(s):
            return self._setup_drops(s)
        if self._draw_reason(s) is not None:
            return []
        return [self._mstr(*m) for m in self._legal(s)]

    def apply_move(self, s: SState, move: str, rng=None) -> SState:
        if self.in_setup(s):
            return self._apply_setup(s, move)
        if self._draw_reason(s) is not None:
            raise ValueError(f"illegal move {move!r}")
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        if ">" not in body:
            raise ValueError(f"illegal move {move!r}")
        frm_s, to_s = body.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        if (frm, to, promo) not in self._legal(s):
            raise ValueError(f"illegal move {move!r}")
        me = s.to_move
        moved = s.board[frm]
        is_capture = to in s.board
        nb = self._apply_board(s.board, frm, to, promo)
        unmoved = s.unmoved - {frm, to}
        irreversible = is_capture or moved[1] == "P"
        halfmove = 0 if irreversible else s.halfmove + 1
        reps = {} if irreversible else dict(s.reps)
        key = _poskey(nb, 1 - me, unmoved)
        reps[key] = reps.get(key, 0) + 1
        return SState(board=nb, to_move=1 - me, hands={WHITE: {}, BLACK: {}},
                      unmoved=unmoved, halfmove=halfmove, ply=s.ply + 1,
                      reps=reps, last=(frm, to))

    def is_terminal(self, s: SState) -> bool:
        if self.in_setup(s):
            return False
        if self._draw_reason(s) is not None:
            return True
        return len(self._legal(s)) == 0

    def returns(self, s: SState) -> list:
        if self.in_setup(s) or self._draw_reason(s) is not None:
            return [0.0, 0.0]
        if len(self._legal(s)) == 0 and _in_check(s.board, s.to_move):
            return [-1.0, 1.0] if s.to_move == WHITE else [1.0, -1.0]
        return [0.0, 0.0]              # stalemate (and non-terminal) are drawn

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: SState) -> dict:
        return {
            "board": {f"{q},{r}": [o, t] for (q, r), (o, t) in s.board.items()},
            "to_move": s.to_move,
            "hands": {str(p): dict(h) for p, h in s.hands.items()},
            "unmoved": sorted(f"{q},{r}" for q, r in s.unmoved),
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
            "last": ([f"{s.last[0][0]},{s.last[0][1]}", f"{s.last[1][0]},{s.last[1][1]}"]
                     if s.last else None),
        }

    def deserialize(self, d: dict) -> SState:
        last = d.get("last")
        hands = {int(p): dict(h) for p, h in d.get("hands", {}).items()}
        for p in (WHITE, BLACK):
            hands.setdefault(p, {})
        return SState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            hands=hands,
            unmoved=frozenset(_cell(c) for c in d.get("unmoved", [])),
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            last=(_cell(last[0]), _cell(last[1])) if last else None,
        )

    # ---- presentation ------------------------------------------------------
    _PIECE_WORD = {"K": "king", "Q": "queen", "R": "rook", "B": "bishop", "N": "knight"}

    def describe_move(self, s: SState, move: str) -> str:
        """Official numeric notation, e.g. 'K@28', 'B5-36', '26x27=N'."""
        if "@" in move:
            letter, cs = move.split("@")
            return f"{letter}@{cell_name(_cell(cs))}"
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        frm_s, to_s = body.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        piece = s.board.get(frm)
        letter = "" if piece is None or piece[1] == "P" else piece[1]
        sep = "x" if to in s.board else "-"
        return (f"{letter}{cell_name(frm)}{sep}{cell_name(to)}"
                + (f"={promo}" if promo else ""))

    # Decorative three-colouring of the hex board (NOT a rule: the bishop moves
    # on orthogonals here, so no piece is colour-bound).
    _SHADES = {0: "#e8ab6f", 1: "#ffce9e", 2: "#d18b47"}

    def render(self, s: SState, perspective=None) -> dict:
        setup = self.in_setup(s)
        pieces = [{"cell": f"{q},{r}", "owner": o, "label": t}
                  for (q, r), (o, t) in s.board.items()]
        highlights = []
        if s.last is not None:
            seen = set()
            for c in s.last:
                if c not in seen:
                    seen.add(c)
                    highlights.append({"cell": f"{c[0]},{c[1]}", "kind": "last-move"})
        tints = {f"{q},{r}": self._SHADES[(q - r) % 3] for (q, r) in CELLS}
        if setup:                       # highlight this side's free back-rank cells
            for c in BACK_RANK[s.to_move]:
                if c not in s.board:
                    tints[f"{c[0]},{c[1]}"] = "#4f8f4f"

        if self.is_terminal(s):
            reason = self._draw_reason(s)
            if reason is not None:
                caption = f"Draw ({reason})"
            elif _in_check(s.board, s.to_move):
                caption = f"{NAMES[1 - s.to_move]} wins (checkmate)"
            else:
                caption = f"Draw (stalemate — {NAMES[s.to_move]} has no legal move)"
        elif setup:
            left = sum(sum(h.values()) for h in s.hands.values())
            caption = (f"{NAMES[s.to_move]} to place a piece "
                       f"(setup phase — {left} left)")
        else:
            check = " (check)" if _in_check(s.board, s.to_move) else ""
            caption = f"{NAMES[s.to_move]} to move{check}"

        spec = {
            "board": {
                "type": "hex",
                "cells": [f"{q},{r}" for (q, r) in CELLS],
                "tints": tints,
                "labels": {f"{q},{r}": str(NUM[(q, r)]) for (q, r) in CELLS},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "pieceset": "chess",
        }
        if setup:
            spec["reserve"] = {str(p): {L: n for L, n in sorted(s.hands.get(p, {}).items())
                                        if n > 0} for p in (WHITE, BLACK)}
        return spec

    # ---- bot eval ----------------------------------------------------------
    # Relative values reflect this board, not orthodox chess: the rook has only
    # 2 rays, the bishop 4, the queen 6, and the 12-way knight is strong on 37
    # cells. Bot heuristic only — not a rule.
    VALUES = {"P": 1.0, "R": 3.0, "N": 3.5, "B": 4.0, "Q": 8.0, "K": 0.0}

    def heuristic(self, s: SState) -> list:
        import math
        bal = 0.0
        for (o, t) in s.board.values():
            v = self.VALUES.get(t, 0.0)
            bal += v if o == WHITE else -v
        v = math.tanh(bal / 6.0)
        return [v, -v]
