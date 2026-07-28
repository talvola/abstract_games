"""Gliński's Hexagonal Chess (Władysław Gliński, 1936; launched 1949).

Chess on a regular hexagonal board of 91 hexes (side 6), the most widely played
hexagonal chess variant. Each side has the orthodox army plus one extra bishop
and one extra pawn (K Q R×2 B×3 N×2 P×9). The three bishops live on the three
hex colours.

Board & coordinates
-------------------
Cells are axial hex coordinates "q,r" with cube s = -q-r and
max(|q|,|r|,|s|) <= 5 (a "hexhex-6" board, 91 cells). Gliński's own notation
uses 11 files a..l (no "j") and ranks that bend 60 deg at the central f-file;
the mapping used here (and by ``describe_move``) is:

    file letter = "abcdefghikl"[q+5]
    rank        = r0 - r + 1,  where r0 = 5 - max(q, 0)

so f1=(0,5) is White's near corner, f6=(0,0) the centre, f11=(0,-5) Black's
corner. White moves in the -r direction ("north"). Because q IS the file, the
board is rendered flat-topped (`board.orientation`) so the files run vertically
as in Gliński's own diagrams.

Rules implemented (Wikipedia "Hexagonal chess", chessvariants.com; see rules.md)
-------------------------------------------------------------------------------
Piece movement, check/mate, draws, serialisation and rendering come from
``agp.hexchesslike`` (shared with the other five classical hex chesses -- the
direction tables are identical in axial space for the whole family). This
module supplies only what is Gliński-specific:

* Pawn: one vacant cell straight forward. From ANY starting cell of a pawn of
  its colour (its own, or another friendly pawn's reached by capturing) it may
  instead advance two vacant cells forward. It captures one cell orthogonally
  forward at 60 deg to the vertical (the two forward rook directions that are
  NOT straight ahead), including en passant. It promotes to Q/R/B/N on
  reaching the end of any file (the 11 far-edge cells).
* STALEMATE IS NOT A DRAW: the stalemating side scores 3/4, the stalemated
  side 1/4 (tournament rule) -- ``STALEMATE_SCORED``. On this engine's +1/0/-1
  payoff scale that is +0.5 / -0.5 (chess points p map to 2p-1), so
  win > stalemate-win > draw > stalemated > loss orders correctly. Note this
  makes BOTH no-move outcomes scored results, which is why the shared
  ``_draw_reason`` yields to "no legal move" rather than to checkmate alone.
* NO castling.
* There is deliberately NO "insufficient material" auto-draw: unlike orthodox
  chess, K vs K stalemate is REACHABLE on the hex board (e.g. white Kf9 vs
  black Kf11, Black to move) and scores 3/4-1/4, so declaring bare kings drawn
  would misjudge a live position (see rules.md).

Move strings: "q1,r1>q2,r2" with an "=Q/=R/=B/=N" suffix on promotions.
"""

from __future__ import annotations

# The names re-exported here (GState, ORTHO/DIAG/KNIGHT, on_board, cell_name,
# PLY_CAP, WHITE/BLACK) are the module's PUBLIC SURFACE: `selftest.py` imports
# them, and the selftests are the regression net for this refactor, so they are
# deliberately not rewritten. Keep these names when editing.
from agp.hexchesslike import (BLACK, DIAG, KNIGHT, ORTHO, WHITE,  # noqa: F401
                              HexChessLike, HState, cell_str)

GState = HState                # historical name, used by selftest.py

FILES = "abcdefghikl"          # no "j", per Gliński's official notation
N = 5                          # hexhex side 6 -> coordinates in [-5, 5]
# Defensive termination backstop -- it must NEVER decide a game, or a live
# position becomes a bogus "move limit" draw (and here that also erases the
# 3/4-1/4 stalemate score). The 50-move rule is the real terminator; the cap is
# only a guard. Bound: <=34 captures + <=180 pawn advances (18 pawns, longest
# file 11 cells) = <=214 irreversible plies, with <=99 reversible plies in each
# of the 215 gaps => a game cannot exceed 21,499 plies, so this cap is dead code.
# It was 1000, which random play HIT in ~0.7% of games (measured; longest 1000+).
PLY_CAP = 25000

CELLS = frozenset((q, r) for q in range(-N, N + 1) for r in range(-N, N + 1)
                  if abs(q + r) <= N)

PAWN_FWD = {WHITE: (0, -1), BLACK: (0, 1)}
# Captures: one cell orthogonally forward at 60 deg to the vertical.
PAWN_CAPS = {WHITE: [(1, -1), (-1, 0)], BLACK: [(1, 0), (-1, 1)]}

# --- start position (verified vs Wikipedia diagram + hexchess.club FEN) ----
# White: K g1, Q e1, B f1/f2/f3, N d1/h1, R c1/i1, P b1 c2 d3 e4 f5 g4 h3 i2 k1
# Black: K g10, Q e10, B f9/f10/f11, N d9/h9, R c8/i8, P b7..k7 (rank 7)
WHITE_PAWN_START = frozenset(
    [(-4, 5), (-3, 4), (-2, 3), (-1, 2), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1)])
BLACK_PAWN_START = frozenset(
    [(-4, -1), (-3, -1), (-2, -1), (-1, -1), (0, -1), (1, -2), (2, -3), (3, -4), (4, -5)])
PAWN_START = {WHITE: WHITE_PAWN_START, BLACK: BLACK_PAWN_START}


def on_board(q: int, r: int) -> bool:
    return abs(q) <= N and abs(r) <= N and abs(q + r) <= N


def cell_name(cell) -> str:
    """Axial (q,r) -> Gliński notation, e.g. (0,5) -> 'f1'."""
    q, r = cell
    r0 = 5 - max(q, 0)
    return f"{FILES[q + 5]}{r0 - r + 1}"


class GlinskiChess(HexChessLike):
    CELLS = CELLS
    FILES = FILES
    PLY_CAP = PLY_CAP
    STALEMATE_SCORED = True        # 3/4 - 1/4, not a draw

    # ---- notation ---------------------------------------------------------
    def cell_name(self, cell) -> str:
        return cell_name(cell)

    def stalemate_caption(self, s) -> str:
        return (f"{self.NAME_OF[1 - s.to_move]} stalemates "
                f"{self.NAME_OF[s.to_move]} (3/4 - 1/4)")

    # ---- setup ------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c in WHITE_PAWN_START:
            b[c] = (WHITE, "P")
        for c in BLACK_PAWN_START:
            b[c] = (BLACK, "P")
        for c in [(-3, 5), (3, 2)]:
            b[c] = (WHITE, "R")
        for c in [(-2, 5), (2, 3)]:
            b[c] = (WHITE, "N")
        for c in [(0, 5), (0, 4), (0, 3)]:
            b[c] = (WHITE, "B")
        b[(-1, 5)] = (WHITE, "Q")
        b[(1, 4)] = (WHITE, "K")
        for c in [(-3, -2), (3, -5)]:
            b[c] = (BLACK, "R")
        for c in [(-2, -3), (2, -5)]:
            b[c] = (BLACK, "N")
        for c in [(0, -3), (0, -4), (0, -5)]:
            b[c] = (BLACK, "B")
        b[(-1, -4)] = (BLACK, "Q")
        b[(1, -5)] = (BLACK, "K")
        return b

    # ---- pawns ------------------------------------------------------------
    def is_promo(self, player: int, cell) -> bool:
        """End-of-file cells: the 11 far-edge hexes for each side."""
        q, r = cell
        if player == WHITE:
            return r == -N or q + r == -N
        return r == N or q + r == N

    def pawn_attackers(self, player: int, cell):
        q, r = cell
        return [(q - dq, r - dr) for dq, dr in PAWN_CAPS[player]]

    def pawn_moves(self, s, cell, out) -> None:
        me, board = s.to_move, s.board
        q, r = cell
        fq, fr = PAWN_FWD[me]
        one = (q + fq, r + fr)
        if one in self.CELLS and one not in board:
            if self.is_promo(me, one):
                for pc in self.PROMO_CHOICES:
                    out.append((cell, one, pc, None, None))
            else:
                out.append((cell, one, None, None, None))
            # Double step from ANY friendly pawn starting cell -- Gliński's own
            # rule, not "from its own start": a pawn that captures onto another
            # pawn's home cell regains the double step.
            if cell in PAWN_START[me]:
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
                    if self.is_promo(me, tgt):
                        for pc in self.PROMO_CHOICES:
                            out.append((cell, tgt, pc, None, None))
                    else:
                        out.append((cell, tgt, None, None, None))
            elif s.ep is not None and tgt in s.ep[1]:
                out.append((cell, tgt, None, s.ep[0], None))

    def ep_after(self, s, frm, to, piece: str):
        # Only a double step creates an e.p. right. The pawn's forward vector is
        # (0, +-1), so a two-RANK jump is unambiguous here (contrast Brusky,
        # whose vertical-diagonal CAPTURE also spans two ranks).
        if piece != "P" or abs(to[1] - frm[1]) != 2:
            return None
        mid = (frm[0], (frm[1] + to[1]) // 2)
        return (to, (mid,))

    # ---- render -----------------------------------------------------------
    def board_spec(self, s) -> dict:
        shades = ["#e8ab6f", "#d18b47", "#ffce9e"]
        tints = {f"{q},{r}": shades[(q - r) % 3] for (q, r) in self.CELLS}
        return {"type": "hex", "shape": "hexagon", "size": N + 1,
                # q IS the file letter, and Glinski's files are drawn VERTICAL,
                # so the board needs flat-top hexes (see SPEC.md).
                "orientation": "flat", "tints": tints}
