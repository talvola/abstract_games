"""Knightmate (a.k.a. "Mate"), by Bruce Zimov (1972) -- a chess variant in which
the royal piece is a KNIGHT and the knights are replaced by non-royal "Commoners"
(king-movers). Built on the shared chess-like core ``agp.chesslike``.

Differences from orthodox chess (all else -- pawns, en passant, draws, castling
geometry -- is standard):

* The two knights are replaced by **Commoners** (letter ``C``): a Commoner moves
  like a king (one square any direction) but is NOT royal -- it captures and is
  captured like any other piece. Commoners start on the knights' squares
  (b1/g1, b8/g8).
* The king is replaced by a **Royal Knight** (letter ``K``): it moves as a knight
  -- the (1,2) leaper -- and IS the royal piece. You win by checkmating it.
  It starts on the king's square (e1/e8).

Royalty wiring: ``ChessLike`` locates "the king" purely by the piece LETTER
``"K"`` (see ``_king`` / ``in_check``), so we keep the royal piece's letter as
``"K"`` but give that letter knight movement (``([], KNIGHT)``). The Commoner is a
distinct letter ``"C"`` with king movement (``([], ALL8)``) and no royal status,
so check/checkmate are evaluated against the royal knight only, while a Commoner
is an ordinary capturable piece.

Castling: present, per the authoritative sources (chessvariants.com,
chess.com) -- the royal knight castles with a rook under the same rules and
restrictions as a king in chess (the royal knight makes the king's two-square
jump, not a knight move). Standard 8x8 castling geometry applies because the royal
knight sits on the king's home square e1/e8, so ``StandardCastling`` works
unchanged (it keys off letter ``"K"`` on col 4).

Pawn promotion: Queen, Rook, Bishop, or Commoner -- but NOT to a (royal) knight.
White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# R, Commoner, B, Q, Royal-Knight(K), B, Commoner, R
BACK_RANK = ["R", "C", "B", "Q", "K", "B", "C", "R"]


class KnightmateCastling(StandardCastling):
    """Standard chess castling, but the royal piece (letter ``K``) is a KNIGHT.

    ``StandardCastling.rook_move`` treats *any* two-file move of a ``K`` as a
    castle. A royal knight's ``(2,1)`` leap also shifts two files, so we must
    disambiguate: a genuine castle is the king's two-square horizontal jump,
    which stays on the SAME rank (``to[1] == frm[1]``); a knight leap always
    changes the rank by one. (No knight move is a same-rank two-file move, so
    this is exact.) Castling generation (``moves``) is inherited unchanged -- it
    yields the king's home->two-files move on the home rank.
    """

    def rook_move(self, frm, to, player):
        if to[1] != frm[1]:          # a knight leap changes rank -> never a castle
            return None
        return super().rook_move(frm, to, player)


class Knightmate(ChessLike):
    uid = "knightmate"
    name = "Knightmate"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "C": ([], ALL8),     # Commoner: king-mover, NON-royal
        "K": ([], KNIGHT),   # Royal Knight: knight-mover, IS royal (letter "K")
    }
    # Mating material: everything but a lone royal knight. Listing the Commoner
    # and bishop here means the only "insufficient material" draw is the bare
    # royal-knights-only ending (the generic two-bishops/lone-minor heuristic in
    # ChessLike does not really apply to Commoners, so we deliberately keep draws
    # conservative -- see rules.md).
    HEAVY = ("P", "R", "Q", "C", "B")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "C"))
    CASTLING = KnightmateCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b
