"""Makruk (Thai chess), 8x8, built on the shared chess-like core.

Pieces:

* **Khun** (king, ``K``) -- moves like an orthodox king; there is no castling.
* **Met** (queen, ``M``) -- a *ferz*: one square diagonally only.
* **Khon** (silver-general, ``S``/``s``) -- one square diagonally OR one square
  straight forward (five directions). The "forward" direction depends on colour,
  so White's Khon is the letter ``S`` and Black's is ``s`` (the engine's leap
  table is colour-blind, so the two directions need two letters; both render and
  are described as "Khon").
* **Ruea** (rook, ``R``) and **Ma** (knight, ``N``) -- exactly as in chess.
* **Bia** (pawn, ``P``) -- starts on the third rank, steps one square forward
  (no double step), captures one square diagonally forward, and **promotes to a
  Met (``M``) on reaching the sixth rank** (row 5 for White, row 2 for Black).

Win by checkmate; stalemate is a draw. No en passant, no castling. The native
Makruk *counting / honour-counting* endgame rule is **omitted**; instead, to keep
the game finite, a bare-king-vs-bare-king position is a draw and there is a hard
ply cap (and a no-progress halfmove cap). White = player 0 moves first.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, PromotionRules, NoCastling,
    ORTHO, DIAG, KNIGHT, ALL8, WHITE, BLACK,
)

# Back rank (files a..h). In Makruk the kings stand opposite each other: White's
# Khun is on e1 (col 4) with the Met on d1 (col 3); Black's Khun is on d8 (col 3)
# with the Met on e8 (col 4) -- so the two Mets and the two Khuns face on the same
# files. (Black's Khon uses the lowercase letter so its forward step points down.)
BACK_RANK_WHITE = ["R", "N", "S", "M", "K", "S", "N", "R"]
BACK_RANK_BLACK = ["R", "N", "s", "K", "M", "s", "N", "R"]

# Khon leap sets: the four diagonals plus the single straight-forward step.
KHON_WHITE = DIAG + [(0, 1)]    # White advances toward higher rows
KHON_BLACK = DIAG + [(0, -1)]   # Black advances toward lower rows


class MakrukPromotion(PromotionRules):
    """Bia promotes (mandatory) to a Met on the sixth rank: row 5 for White,
    row 2 for Black."""

    def _is_promo_rank(self, core, player, row):
        return (player == WHITE and row == 5) or (player == BLACK and row == 2)

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        return ["M"] if self._is_promo_rank(core, pl, to[1]) else [None]

    def safety_piece(self) -> str:
        return "M"


class Makruk(ChessLike):
    uid = "makruk"
    name = "Makruk"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []),
        "N": ([], KNIGHT),
        "M": ([], DIAG),          # Met = ferz
        "K": ([], ALL8),          # Khun = king
        "S": ([], KHON_WHITE),    # White Khon
        "s": ([], KHON_BLACK),    # Black Khon
    }
    HEAVY = ("P", "R")            # mating material; lone Met/Khon/Ma can't force mate
    PAWN = StandardPawn(white_start=2, black_start=5, double=False)
    PROMOTION = MakrukPromotion()
    CASTLING = NoCastling()

    # ---- Khon promotion / king-safety: promote on the 6th rank, not the last ---
    def _apply_board(self, board, frm, to, ep):
        """Board after a (non-castling) move, for king-safety testing only.
        Overridden so a Bia that promotes on the 6th rank is tested as a Met."""
        b = dict(board)
        pl, t = b.pop(frm)
        if t == "P" and self.PROMOTION._is_promo_rank(self, pl, to[1]):
            t = self.PROMOTION.safety_piece()
        b[to] = (pl, t)
        return b

    # ---- presentation -------------------------------------------------------
    _LABELS = {"S": "S", "s": "S", "M": "M", "K": "K", "R": "R", "N": "N", "P": "P"}

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        for p in spec["pieces"]:
            p["label"] = self._LABELS.get(p["label"], p["label"])
        return spec

    def describe_move(self, state, move) -> str:
        text = super().describe_move(state, move)
        # Normalise the Black-Khon letter so the move log reads "Khon" for both.
        return text.replace("s", "S", 1) if text[:1] == "s" else text

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK_WHITE[c])
            b[(c, 2)] = (WHITE, "P")
            b[(c, 5)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK_BLACK[c])
        return b
