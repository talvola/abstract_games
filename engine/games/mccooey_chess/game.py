"""McCooey's Hexagonal Chess (Dave McCooey & Richard Honeycutt, 1978-79).

Chess on the same regular hexagonal board of 91 hexes (side 6) as Glinski's
game, designed independently to be "the closest hexagonal equivalent to the
real game of chess". Army: K, Q, 2xR, 3xB, 2xN and SEVEN pawns per side
(vs Glinski's nine); every pawn starts exactly seven hexes from promotion,
and there are no unoccupied cells behind the pawn chain.

Board & coordinates
-------------------
Cells are axial hex coordinates "q,r" with cube s = -q-r and
max(|q|,|r|,|s|) <= 5 (a "hexhex-6" board, 91 cells). McCooey's own notation
(used in his published sample games) has 11 files a..k INCLUDING "j" (unlike
Glinski's a..l without "j"), with ranks that bend 60 deg at the central
f-file; the mapping used here (and by ``describe_move``) is:

    file letter = "abcdefghijk"[q+5]
    rank        = r0 - r + 1,  where r0 = 5 - max(q, 0)

so f1=(0,5) is White's near corner, f6=(0,0) the centre, f11=(0,-5) Black's
corner. White moves in the -r direction ("north"). Because q IS the file, the
board is rendered flat-topped (`board.orientation`) so the files run vertically
as in McCooey's own diagrams.

Rules implemented (chessvariants.com hexchess2.html = McCooey's own page;
Wikipedia "Hexagonal chess"; see rules.md)
-------------------------------------------------------------------------
Piece movement, check/mate, draws, serialisation and rendering come from
``agp.hexchesslike`` (shared with the other five classical hex chesses -- the
direction tables are identical in axial space for the whole family). This
module supplies only what is McCooey-specific, which is exactly what differs
from Glinski's game: the starting array, the pawn's capturing move, the
centre-pawn double-step exclusion and the stalemate rule.

* Rook: 6 orthogonal (edge) directions. Bishop: 6 diagonal (vertex)
  directions (colourbound; the three bishops start on the three colours).
  Queen = rook + bishop (12 directions). King: one step in any of the 12;
  NO castling. Knight: two hexes orthogonally then one at 60 deg (a
  12-target hex leap), jumping over intervening pieces.
* Pawn: one vacant cell straight forward; it CAPTURES one cell along the two
  forward DIAGONAL (bishop-wise) directions -- like orthodox chess and unlike
  Glinski, whose pawns capture along the forward orthogonals. Every pawn
  except the centre pawn (f4 / f8) may advance two vacant cells straight
  forward on its first move (the centre-pawn exclusion stops White grabbing
  the centre hex on move one). Because a pawn can never re-enter a starting
  hex, "first move" is equivalent to "standing on its own starting hex".
  En passant: a pawn double-stepping across an enemy pawn's attack hex may
  be captured on that crossed hex on the immediately following move.
  Promotion to Q/R/B/N on reaching the end of any file (the 11 far-edge
  cells); forced, and free choice regardless of pieces on the board.
* Check/checkmate as in chess. STALEMATE IS A DRAW (1/2-1/2) -- McCooey
  chose the orthodox outcome, explicitly rejecting Glinski's 3/4-1/4 rule,
  so this class does NOT set ``STALEMATE_SCORED``.
* Draws: 50-move rule (100 plies with no pawn move or capture), threefold
  repetition (same board+side+en-passant), and a defensive hard ply cap as
  a termination backstop; a decisive result OUTRANKS all three (the shared
  ``_draw_reason``). No "insufficient material" auto-draw (bare-king
  endings end via the 50-move rule; K+2N genuinely mates in this family).

BUG FIXED IN THE REFACTOR (2026-07-27)
--------------------------------------
The pre-refactor implementation created an en-passant right after ANY pawn
move whose rank changed by two -- a test inherited from Gliński's game, where
it is sound because Gliński's pawns capture along the forward ORTHOGONALS.
McCooey's pawn captures along the forward DIAGONALS, and White's (1, -2)
diagonal spans two ranks, so every such CAPTURE also armed a phantom e.p.
right on a hex no pawn had crossed. Consequences: an enemy pawn could
"capture en passant" onto that hex although no double step had occurred, and
because the phantom hex (unlike a real crossed hex) can be OCCUPIED, a pawn
could land on its own man while a third, unrelated piece was removed. The
double-step test now also requires the move to stay on its own file.

Move strings: "q1,r1>q2,r2" with an "=Q/=R/=B/=N" suffix on promotions.
"""

from __future__ import annotations

# The names re-exported here (MState, ORTHO/DIAG/KNIGHT, on_board, cell_name,
# _is_promo, _attacked, _in_check, PAWN_FWD/PAWN_CAPS, PLY_CAP, WHITE/BLACK)
# are the module's PUBLIC SURFACE: `selftest.py` imports them, and the
# selftests are the regression net for this refactor, so they are deliberately
# not rewritten. Keep these names when editing.
from agp.hexchesslike import (BLACK, DIAG, KNIGHT, ORTHO, WHITE,  # noqa: F401
                              HexChessLike, HState, cell_str)

MState = HState                # historical name, used by selftest.py

NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefghijk"          # 11 files INCLUDING "j", per McCooey's notation
N = 5                          # hexhex side 6 -> coordinates in [-5, 5]
# Defensive termination backstop -- it must NEVER decide a game, or a live
# position becomes a bogus "move limit" draw. The 50-move rule is the real
# terminator; the cap is only a guard. Bound: <=30 captures + <=140 pawn
# advances (14 pawns, longest file 11 cells) = <=170 irreversible plies, with
# <=99 reversible plies in each of the 171 gaps => a game cannot exceed 17,099
# plies, so this cap is dead code. It was 1000, which random play approaches
# (measured longest: 816 plies, within 20% of the old cap).
PLY_CAP = 25000

CELLS = frozenset((q, r) for q in range(-N, N + 1) for r in range(-N, N + 1)
                  if abs(q + r) <= N)

PAWN_FWD = {WHITE: (0, -1), BLACK: (0, 1)}
# Captures: the two forward DIAGONAL (bishop) directions -- McCooey's key
# difference from Glinski (whose pawns capture along forward orthogonals).
PAWN_CAPS = {WHITE: [(1, -2), (-1, -1)], BLACK: [(-1, 2), (1, 1)]}

# --- start position --------------------------------------------------------
# Verified against three independent sources (McCooey's chessvariants.com
# page, his published sample games, and the Markmann Zillions ZRF):
# White: K g1, Q e1, N e2 g2, R d1 h1, B f1 f2 f3, P c1 d2 e3 f4 g3 h2 i1
# Black: K g10, Q e10, N e9 g9, R d9 h9, B f9 f10 f11, P c8..i8 (rank 8)
WHITE_PAWN_START = frozenset(
    [(-3, 5), (-2, 4), (-1, 3), (0, 2), (1, 2), (2, 2), (3, 2)])
BLACK_PAWN_START = frozenset(
    [(-3, -2), (-2, -2), (-1, -2), (0, -2), (1, -3), (2, -4), (3, -5)])
PAWN_START = {WHITE: WHITE_PAWN_START, BLACK: BLACK_PAWN_START}
# The centre pawn (f4 / f8) is denied the initial double step.
CENTRE_PAWN = {WHITE: (0, 2), BLACK: (0, -2)}


def on_board(q: int, r: int) -> bool:
    return abs(q) <= N and abs(r) <= N and abs(q + r) <= N


def _is_promo(player: int, cell) -> bool:
    """End-of-file cells: the 11 far-edge hexes for each side."""
    q, r = cell
    if player == WHITE:
        return r == -N or q + r == -N
    return r == N or q + r == N


def cell_name(cell) -> str:
    """Axial (q,r) -> McCooey notation, e.g. (0,5) -> 'f1'."""
    q, r = cell
    r0 = 5 - max(q, 0)
    return f"{FILES[q + 5]}{r0 - r + 1}"


class McCooeyChess(HexChessLike):
    CELLS = CELLS
    FILES = FILES
    NAME_OF = NAMES
    PLY_CAP = PLY_CAP
    # STALEMATE_SCORED stays False: stalemate is an ordinary DRAW here --
    # McCooey explicitly rejected Glinski's 3/4-1/4 rule.

    # ---- notation ---------------------------------------------------------
    def cell_name(self, cell) -> str:
        return cell_name(cell)

    def stalemate_caption(self, s) -> str:
        # McCooey's wording is terser than the family default.
        return "Draw (stalemate)"

    # ---- setup ------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c in WHITE_PAWN_START:
            b[c] = (WHITE, "P")
        for c in BLACK_PAWN_START:
            b[c] = (BLACK, "P")
        for c in [(-2, 5), (2, 3)]:            # d1, h1
            b[c] = (WHITE, "R")
        for c in [(-1, 4), (1, 3)]:            # e2, g2
            b[c] = (WHITE, "N")
        for c in [(0, 5), (0, 4), (0, 3)]:     # f1, f2, f3
            b[c] = (WHITE, "B")
        b[(-1, 5)] = (WHITE, "Q")              # e1
        b[(1, 4)] = (WHITE, "K")               # g1
        for c in [(-2, -3), (2, -5)]:          # d9, h9
            b[c] = (BLACK, "R")
        for c in [(-1, -3), (1, -4)]:          # e9, g9
            b[c] = (BLACK, "N")
        for c in [(0, -3), (0, -4), (0, -5)]:  # f9, f10, f11
            b[c] = (BLACK, "B")
        b[(-1, -4)] = (BLACK, "Q")             # e10
        b[(1, -5)] = (BLACK, "K")              # g10
        return b

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
        one = (q + fq, r + fr)
        if one in self.CELLS and one not in board:
            if _is_promo(me, one):
                for pc in self.PROMO_CHOICES:
                    out.append((cell, one, pc, None, None))
            else:
                out.append((cell, one, None, None, None))
            # Double step: from the pawn's OWN starting cell only (a pawn can
            # never re-enter a starting hex, so that IS "has not moved yet"),
            # and never for the centre pawn f4 / f8.
            if cell in PAWN_START[me] and cell != CENTRE_PAWN[me]:
                two = (q + 2 * fq, r + 2 * fr)
                if two in self.CELLS and two not in board:
                    out.append((cell, two, None, None, None))
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
        """Only a genuine DOUBLE STEP creates an e.p. right.

        Unlike Gliński -- where a two-rank move can only be a double step,
        because his pawns capture along the forward ORTHOGONALS (delta r of
        -1 or 0) -- McCooey's pawn captures along the forward DIAGONALS, and
        one of those, (1, -2) for White, spans TWO ranks. So the rank
        difference alone does NOT identify a double step here; the move must
        also stay on its own file. See the module docstring's bug note.
        """
        if piece != "P" or to[0] != frm[0] or abs(to[1] - frm[1]) != 2:
            return None
        mid = (frm[0], (frm[1] + to[1]) // 2)
        return (to, (mid,))

    # ---- render -----------------------------------------------------------
    def board_spec(self, s) -> dict:
        # The three hex colours (bishop colour classes): colour = (q - r) mod 3.
        # McCooey specifies the CENTRE hex is the lightest ("white") colour.
        shades = {0: "#ffce9e", 1: "#e8ab6f", 2: "#d18b47"}  # light, mid, dark
        tints = {}
        for q in range(-N, N + 1):
            for r in range(-N, N + 1):
                if on_board(q, r):
                    tints[f"{q},{r}"] = shades[(q - r) % 3]
        return {"type": "hex", "shape": "hexagon", "size": N + 1,
                # q IS the file letter, and McCooey's files are drawn VERTICAL,
                # so the board needs flat-top hexes (see SPEC.md).
                "orientation": "flat", "tints": tints}


# `selftest.py` calls `_attacked` / `_in_check` as module-level functions (the
# pre-refactor shape); they are one-liners onto the shared implementation.
_G = McCooeyChess()


def _attacked(board: dict, cell, by: int) -> bool:
    return _G.attacked(board, cell, by)


def _in_check(board: dict, player: int) -> bool:
    return _G.in_check(board, player)
