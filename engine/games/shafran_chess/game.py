"""Shafran's Hexagonal Chess (Isaak Grigorevich Shafran, USSR, 1939).

The third of the historic hexagonal chesses, alongside Gliński's (1936) and
McCooey's (1978). Shafran, a Soviet geologist, invented it in 1939, registered
it in 1956 and had it demonstrated at the Leipzig Chess Olympiad in 1960. Its
board is an *irregular* hexagon of only 70 cells — four sides of 5 and two of 6
— which brings it much closer to orthodox chess's 64 squares than Gliński's 91.

Board & coordinates
-------------------
Nine vertical files ``a``-``i`` and ten *obliquely descending* ranks ``1``-``10``
(a rank runs from the upper left down to the lower right, so ``a1`` is the
highest cell of rank 1 and ``e1``, the king's cell, is the lowest cell of the
whole board). File lengths are a=6, b=7, c=8, d=9, e=10, f=9, g=8, h=7, i=6;
files f..i start at ranks 2,3,4,5 respectively.

Cells are axial hex coordinates ``"q,r"`` (cube ``s = -q-r``) with

    q = file index - 4   (a = -4 ... i = +4)
    r = 5 - rank         (rank 1 = +4 ... rank 10 = -5)

so the board is exactly ``-4 <= q <= 4``, ``-5 <= r <= 4``, ``-5 <= q+r <= 4``
(70 cells). White moves in the ``-r`` direction ("north", up a file).

Rules implemented (Derzhanski's write-up of the *Junyj texnik* report =
closest to primary; Wikipedia "Hexagonal chess" § Shafran; Duniho's
chessvariants.com page; the Jocly reference model; see rules.md)
--------------------------------------------------------------------------
Piece movement, attack detection, check/mate, the draw rules, serialisation,
rendering and the MCTS heuristic come from ``agp.hexchesslike``, shared with the
other five classical hex chesses — the axial direction tables are byte-identical
for the whole family. This module supplies only what is Shafran-specific, which
for Shafran is a lot: it is the only classical hex chess with castling, and its
pawn rules are unique.

* Setup (each side K Q R×2 B×3 N×2 P×9). White: R a1, N b1, B c1, Q d1, K e1,
  B f2, N g3, B h4, R i5; pawns a2 b2 c2 d2 e2 f3 g4 h5 i6. Black is the exact
  180° rotation (R i10, N h10, B g10, Q f10, K e10, B d9, N c8, B b7, R a6;
  pawns i9 h9 g9 f9 e9 d8 c7 b6 a5). NOTE: Duniho's prose says "the Bishop is
  on f1" — a typo. f1 is not a cell of this board at all (the f-file starts at
  f2), and only f2 puts the three bishops on the three cell colours, as his own
  text and diagram require. Jocly and the Wikipedia diagram both say f2.
* Rook: 6 orthogonal (edge) directions. Bishop: 6 diagonal (vertex) directions
  (colourbound; the three bishops start on the three colours). Queen = rook +
  bishop (12 directions). King: one step in any of the 12. Knight: the
  12-target hex leap (one orthogonal step then one *outward* diagonal step;
  equivalently, every cell of the third ring a queen cannot reach).
* Pawn: one vacant cell straight forward; captures one cell along the two
  forward DIAGONAL (bishop-wise) directions — McCooey-style, NOT Gliński's
  forward orthogonals. On its FIRST move it may advance as far as it can
  without leaving its own half of its file: 3 cells on the d/e/f files, 2 on
  b/c/g/h, 1 on a/i, over vacant cells only. Every cell CROSSED by such a
  multi-step move is an en-passant target for one move — which is why the
  shared core's ``ep`` carries a TUPLE of target cells (Shafran is the only
  member of the family that can leave two).
* Castling (unique among the classical hex chesses). Toward either rook, in
  two lengths: LONG (0-0-0) moves the king 3 cells, next to the rook, and the
  rook jumps over him to the far side; SHORT (0-0) is "the opposite procedure"
  (Derzhanski) -- the rook steps next to the king and the king jumps over it,
  landing 2 cells from home with the rook 1. The three cells between king and
  rook must be empty either way, and the king may not start from, pass through
  or land on an attacked cell. Notation is prefixed by the flank: ``Q-`` for
  the player's queen's flank, ``B-`` for his bishops' flank (the flanks are
  opposite for the two players).
* STALEMATE IS A DRAW (Wikipedia, explicit) — unlike Gliński's 3/4-1/4 rule,
  so ``STALEMATE_SCORED`` keeps its default of False.
* Draws: 50-move rule (100 plies with no pawn move or capture), threefold
  repetition (board + side + en-passant targets + castling rights), and a hard
  ply cap as a pure termination backstop that the 50-move rule provably always
  reaches first (see rules.md). No "insufficient material" auto-draw.

Move strings: ``"q1,r1>q2,r2"`` with an ``"=Q/=R/=B/=N"`` suffix on promotions.
Castling is written as the king's ordinary from>to (2 or 3 cells).
"""

from __future__ import annotations

# The names re-exported / kept module-level here (GState, WHITE/BLACK,
# ORTHO/DIAG/KNIGHT, CELLS, FILES, on_board, cell_name, _cell, _file_len,
# _is_promo, _attacked, _in_check, PAWN_*, HOME, KING_START, ROOK_START,
# CASTLE_BETWEEN, QUEEN_FLANK, PLY_CAP) are the module's PUBLIC SURFACE:
# `selftest.py` imports them, and the selftests are the regression net for this
# refactor, so they are deliberately not rewritten. Keep these names when
# editing.
from agp.hexchesslike import (BLACK, DIAG, KNIGHT, ORTHO, WHITE,  # noqa: F401
                              HexChessLike, HState, cell_str, parse_cell)

GState = HState                # historical name, used by selftest.py

NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefghi"            # nine vertical files
# Defensive termination backstop. The 50-move rule provably fires first: at most
# 178 irreversible plies (<=34 captures + <=144 pawn moves -- every pawn move
# gains a rank and no pawn can gain more than 8) and at most 99 reversible plies
# in each of the 179 gaps around them cap any game at 178 + 179*99 = 17,899
# plies. Observed longest random game: 723 plies. See rules.md.
PLY_CAP = 20000

PAWN_FWD = {WHITE: (0, -1), BLACK: (0, 1)}
# Captures: the two FORWARD DIAGONAL (bishop) directions -- Shafran follows
# McCooey here, not Gliński (whose pawns capture along the forward orthogonals).
PAWN_CAPS = {WHITE: [(1, -2), (-1, -1)], BLACK: [(-1, 2), (1, 1)]}

# --- board -----------------------------------------------------------------
QMIN, QMAX = -4, 4
RMIN, RMAX = -5, 4


def on_board(q: int, r: int) -> bool:
    return QMIN <= q <= QMAX and RMIN <= r <= RMAX and RMIN <= q + r <= RMAX


CELLS = tuple(sorted((q, r) for q in range(QMIN, QMAX + 1)
                     for r in range(RMIN, RMAX + 1) if on_board(q, r)))


def _file_top(q: int) -> int:
    """Smallest r (Black's end / White's promotion cell) of file q."""
    return max(RMIN, RMIN - q)


def _file_bottom(q: int) -> int:
    """Largest r (White's end / Black's promotion cell) of file q."""
    return min(RMAX, RMAX - q)


def _file_len(q: int) -> int:
    return _file_bottom(q) - _file_top(q) + 1


# Home ("back") cell of each file, and the pawn cell just in front of it.
HOME = {WHITE: {q: (q, _file_bottom(q)) for q in range(QMIN, QMAX + 1)},
        BLACK: {q: (q, _file_top(q)) for q in range(QMIN, QMAX + 1)}}

# A pawn's first move may take it "as far as it can without moving to the
# opponent's side of the board" (Duniho). Numbering a file 0..L-1 from the
# pawn's own end, the pawn stands on 1 and may reach at most (L-1)//2 (the
# midway cell of an odd-length file counts as reachable), so:
PAWN_STEPS = {q: (_file_len(q) - 1) // 2 - 1 for q in range(QMIN, QMAX + 1)}
# == {a:1, b:2, c:2, d:3, e:3, f:3, g:2, h:2, i:1}

PAWN_START = {p: {(q, HOME[p][q][1] + PAWN_FWD[p][1]): PAWN_STEPS[q]
                  for q in range(QMIN, QMAX + 1)} for p in (WHITE, BLACK)}

# --- castling --------------------------------------------------------------
KING_START = {WHITE: (0, 4), BLACK: (0, -5)}
# Flank key -> the direction from the king toward that flank's rook. The rook
# stands four cells away, with exactly three cells in between.
CASTLE_DIR = {(WHITE, "a"): (-1, 0), (WHITE, "i"): (1, -1),
              (BLACK, "a"): (-1, 1), (BLACK, "i"): (1, 0)}


def _castle_geometry(player: int, flank: str):
    """(rook_cell, [between1, between2, between3]) for one castling flank."""
    kq, kr = KING_START[player]
    dq, dr = CASTLE_DIR[(player, flank)]
    between = [(kq + i * dq, kr + i * dr) for i in (1, 2, 3)]
    return (kq + 4 * dq, kr + 4 * dr), between


ROOK_START = {k: _castle_geometry(*k)[0] for k in CASTLE_DIR}
CASTLE_BETWEEN = {k: _castle_geometry(*k)[1] for k in CASTLE_DIR}
ALL_CASTLES = tuple(sorted(CASTLE_DIR))
# The player's queen stands on the "a" flank for White and the "i" flank for
# Black, so the notation prefix (Q- / B-) is side-relative.
QUEEN_FLANK = {WHITE: "a", BLACK: "i"}


def _setup_board() -> dict:
    """White's array, plus Black's exact 180° rotation (q,r) -> (-q,-1-r)."""
    order = "RNBQKBNBR"                      # files a..i
    b = {}
    for i, letter in enumerate(order):
        q = QMIN + i
        b[HOME[WHITE][q]] = (WHITE, letter)
    for cell in PAWN_START[WHITE]:
        b[cell] = (WHITE, "P")
    for (q, r), (_, letter) in list(b.items()):
        b[(-q, -1 - r)] = (BLACK, letter)
    return b


def _is_promo(player: int, cell) -> bool:
    """The far end of a file: 9 cells per side (two edges of the hexagon)."""
    q, r = cell
    return r == (_file_top(q) if player == WHITE else _file_bottom(q))


def cell_name(cell) -> str:
    """Axial (q,r) -> Shafran notation, e.g. (0,4) -> 'e1'."""
    q, r = cell
    return f"{FILES[q - QMIN]}{5 - r}"


_cell = parse_cell                 # historical name, used by selftest.py


def _hex_dist(a, b) -> int:
    dq, dr = b[0] - a[0], b[1] - a[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


class ShafranChess(HexChessLike):
    CELLS = frozenset(CELLS)       # tuple above keeps render order; set = O(1)
    FILES = FILES
    PLY_CAP = PLY_CAP
    # STALEMATE_SCORED stays False: Shafran's stalemate is an ordinary draw.

    # ---- notation ---------------------------------------------------------
    def cell_name(self, cell) -> str:
        return cell_name(cell)

    # ---- setup ------------------------------------------------------------
    def setup_board(self) -> dict:
        return _setup_board()

    def initial_castling(self) -> frozenset:
        return frozenset(ALL_CASTLES)

    # ---- pawns ------------------------------------------------------------
    def is_promo(self, player: int, cell) -> bool:
        return _is_promo(player, cell)

    def pawn_attackers(self, player: int, cell):
        q, r = cell
        return [(q - dq, r - dr) for dq, dr in PAWN_CAPS[player]]

    def pawn_moves(self, s, cell, out) -> None:
        me, board = s.to_move, s.board
        q, r = cell
        fq, fr = PAWN_FWD[me]
        # The variable-length first move: 3 cells on d/e/f, 2 on b/c/g/h, 1 on
        # a/i, and only from the pawn's own starting cell (selftest proves that
        # "on its first move" == "standing on its starting cell": no pawn can
        # ever re-enter one).
        steps = PAWN_START[me].get(cell, 1)
        cq, cr = q, r
        for _ in range(steps):
            cq, cr = cq + fq, cr + fr
            if (cq, cr) not in self.CELLS or (cq, cr) in board:
                break                   # may not leap over an occupied cell
            if _is_promo(me, (cq, cr)):
                for pc in self.PROMO_CHOICES:
                    out.append((cell, (cq, cr), pc, None, None))
            else:
                out.append((cell, (cq, cr), None, None, None))
        for dq, dr in PAWN_CAPS[me]:
            tgt = (q + dq, r + dr)
            if tgt not in self.CELLS:
                continue
            occ = board.get(tgt)
            if occ is not None:
                if occ[0] != me:
                    if _is_promo(me, tgt):
                        for pc in self.PROMO_CHOICES:
                            out.append((cell, tgt, pc, None, None))
                    else:
                        out.append((cell, tgt, None, None, None))
            elif s.ep is not None and tgt in s.ep[1]:
                out.append((cell, tgt, None, s.ep[0], None))

    def ep_after(self, s, frm, to, piece: str):
        """EVERY cell crossed by a multi-step pawn move is an e.p. target.

        A capture changes the file (both capture vectors have dq != 0), so
        `to[0] == frm[0]` isolates the straight advances.
        """
        if piece != "P":
            return None
        n = _hex_dist(frm, to)
        if n <= 1 or to[0] != frm[0]:
            return None
        fq, fr = PAWN_FWD[s.to_move]
        crossed = tuple((frm[0] + i * fq, frm[1] + i * fr) for i in range(1, n))
        return (to, crossed)

    # ---- castling ---------------------------------------------------------
    def castle_moves(self, s, out) -> None:
        me = s.to_move
        rights = [k for k in s.castling if k[0] == me]
        if not rights:
            return
        king = KING_START[me]
        if s.board.get(king) != (me, "K") or self.in_check(s.board, me):
            return
        for key in sorted(rights):
            between = CASTLE_BETWEEN[key]
            if s.board.get(ROOK_START[key]) != (me, "R"):
                continue
            if any(c in s.board for c in between):
                continue
            # long: K -> between[2], R -> between[1]; short: K -> between[1],
            # R -> between[0]. The king may not pass through an attacked cell;
            # its destination is checked by the shared in-check filter. Transit
            # cells are tested on the PRE-move board (the king and rook are
            # never on them, so nothing shields them).
            if not self.attacked(s.board, between[0], 1 - me):
                out.append((king, between[1], None, None,
                            (ROOK_START[key], between[0])))
                if not self.attacked(s.board, between[1], 1 - me):
                    out.append((king, between[2], None, None,
                                (ROOK_START[key], between[1])))

    def update_castling(self, rights: frozenset, frm, to, board,
                        new_board=None) -> frozenset:
        """A right survives only while its king AND that flank's rook still
        stand on their home cells.

        The pre-refactor code re-derived this from the POST-move board; the
        core hands us the PRE-move one, so the two home cells are evaluated
        through `after()`. That reproduces the old test exactly even though
        `promo`, `ep_victim` and `castle` are not in the hook's signature:

        * promotion -- a promotion cell is never that same side's own king or
          rook home (White promotes on a6/i10, Black on a1/i5, which are the
          OPPONENT's rook homes), so a promoted piece can never satisfy a
          right's `(player, "R"/"K")` test that the unpromoted pawn fails;
        * the e.p. victim is a pawn, so the cell it vacates fails the test both
          before and after its removal;
        * the castling rook's own move only ever concerns the side that is
          castling, whose king has just left KING_START -- both of its rights
          are already dead by the king clause.
        """
        moved = board.get(frm)

        def after(cell):
            if cell == to:
                return moved
            if cell == frm:
                return None
            return board.get(cell)

        return frozenset(k for k in rights
                         if after(KING_START[k[0]]) == (k[0], "K")
                         and after(ROOK_START[k]) == (k[0], "R"))

    # ---- on-disk shapes (frozen: the server stores these in the DB) --------
    def ep_to_json(self, ep):
        """[pawn_cell, crossed..] -- Shafran's own encoding, NOT the family
        default [target, victim], because there can be two targets."""
        if not ep:
            return None
        return [cell_str(ep[0])] + [cell_str(c) for c in ep[1]]

    def ep_from_json(self, v):
        if not v:
            return None
        return (parse_cell(v[0]), tuple(parse_cell(x) for x in v[1:]))

    def castling_to_json(self, rights):
        return sorted(f"{p}{f}" for p, f in rights)

    def castling_from_json(self, v):
        if v is None:                  # legacy states predate the key
            return frozenset(ALL_CASTLES)
        return frozenset((int(x[0]), x[1]) for x in v)

    # ---- presentation -----------------------------------------------------
    def describe_move(self, s, move: str) -> str:
        """Shafran's own notation: flank-prefixed castling and an explicit
        "e.p." tag, and no check/mate suffix (unlike the family default)."""
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        frm_s, to_s = body.split(">")
        frm, to = parse_cell(frm_s), parse_cell(to_s)
        piece = s.board.get(frm)
        if piece is not None and piece[1] == "K" and _hex_dist(frm, to) > 1:
            for key, between in CASTLE_BETWEEN.items():
                if key[0] != piece[0]:
                    continue
                flank = "Q" if key[1] == QUEEN_FLANK[piece[0]] else "B"
                if to == between[2]:
                    return f"{flank}-0-0-0"
                if to == between[1]:
                    return f"{flank}-0-0"
        letter = "" if piece is None or piece[1] == "P" else piece[1]
        is_ep = (piece is not None and piece[1] == "P" and s.ep is not None
                 and to in s.ep[1] and to not in s.board)
        cap = "x" if (to in s.board or is_ep) else "-"
        out = f"{letter}{cell_name(frm)}{cap}{cell_name(to)}"
        if promo:
            out += f"={promo}"
        if is_ep:
            out += " e.p."
        return out

    def board_spec(self, s) -> dict:
        # The three hex colours (bishop colour classes): colour = (q - r) mod 3.
        shades = {0: "#e8ab6f", 1: "#ffce9e", 2: "#d18b47"}  # mid, light, dark
        return {"type": "hex",
                # An irregular hexagon: an explicit cell list, not a shape.
                "cells": [f"{q},{r}" for q, r in CELLS],
                # q IS the file index, and Shafran's files are drawn VERTICAL,
                # so use flat-top hexes (see SPEC.md).
                "orientation": "flat",
                "tints": {f"{q},{r}": shades[(q - r) % 3] for q, r in CELLS}}


# `selftest.py` calls these as module-level functions; the implementations now
# live on the shared core, so route through one throwaway instance.
_REF = ShafranChess()


def _attacked(board: dict, cell, by: int) -> bool:
    return _REF.attacked(board, cell, by)


def _in_check(board: dict, player: int) -> bool:
    return _REF.in_check(board, player)
