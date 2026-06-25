"""Judkins Shogi (a 6x6 shogi variant), built on the same ShogiLike core as full
Shogi -- so its move generation, drops and promotion are exactly the
python-shogi-verified engine, only on a 6x6 board with a Knight added.

Each side has one of each of seven pieces: King, Rook, Bishop, Knight, Gold,
Silver and a single Pawn. The promotion zone is the **far two ranks** (ZONE = 2,
"at the original line of the opponent's pawn and beyond"). Drops,
captures-switch-sides, the two-pawns (nifu), last-rank and drop-mate
(uchifuzume) rules are inherited unchanged.

Standard setup (Wikipedia "Judkins shogi"): the back rank, left->right from each
player's view, is **K G S N B R** (King in the left corner), with one Pawn in
front of the King. The two armies are rotated 180 degrees from each other.
"""

from __future__ import annotations

from agp.shogilike import ShogiLike, BLACK, WHITE


class JudkinsShogi(ShogiLike):
    uid = "judkins_shogi"
    name = "Judkins Shogi"

    WIDTH = HEIGHT = 6
    ZONE = 2                 # the far two ranks promote
    PLY_CAP = 300
    LABELS = {
        "K": "K", "R": "R", "B": "B", "N": "N", "G": "G", "S": "S", "P": "P",
        "+R": "+R", "+B": "+B", "+N": "+N", "+S": "+S", "+P": "+P",
    }

    def setup_board(self):
        b = {}
        # Black (Sente) home rank at the bottom (row 0): K G S N B R
        for c, t in enumerate("KGSNBR"):
            b[(c, 0)] = (BLACK, t)
        b[(0, 1)] = (BLACK, "P")          # black pawn in front of the king
        # White (Gote) home rank at the top (row 5): R B N S G K  (180deg rotation)
        for c, t in enumerate("RBNSGK"):
            b[(c, 5)] = (WHITE, t)
        b[(5, 4)] = (WHITE, "P")          # white pawn in front of its king
        return b, set()
