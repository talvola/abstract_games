"""Mini Shogi (Gotenshogi / 5x5 shogi, Shigenobu Kusano, 1970), built on the same
ShogiLike core as full Shogi -- so its move generation, drops and promotion are
exactly the python-shogi-verified engine, only on a 5x5 board.

Each side has a King, Gold, Silver, Bishop, Rook and one Pawn. The promotion zone
is just the **far rank** (ZONE = 1). Drops, captures-switch-sides, the two-pawns
(nifu) and drop-mate (uchifuzume) rules are inherited unchanged. Initial position
is the standard SFEN ``rbsgk/4p/5/P4/KGSBR b`` -- King in a corner, each side
rotated 180deg from the other.
"""

from __future__ import annotations

from agp.shogilike import ShogiLike, BLACK, WHITE


class MiniShogi(ShogiLike):
    uid = "mini_shogi"
    name = "Mini Shogi"

    WIDTH = HEIGHT = 5
    ZONE = 1                 # only the farthest rank promotes
    PLY_CAP = 300
    LABELS = {
        "K": "K", "R": "R", "B": "B", "G": "G", "S": "S", "P": "P",
        "+R": "+R", "+B": "+B", "+S": "+S", "+P": "+P",
    }

    def setup_board(self):
        b = {}
        # Black (Sente) home rank at the bottom (row 0): K G S B R
        for c, t in enumerate("KGSBR"):
            b[(c, 0)] = (BLACK, t)
        b[(0, 1)] = (BLACK, "P")          # black pawn in front of the king
        # White (Gote) home rank at the top (row 4): R B S G K  (180deg rotation)
        for c, t in enumerate("RBSGK"):
            b[(c, 4)] = (WHITE, t)
        b[(4, 3)] = (WHITE, "P")          # white pawn in front of its king
        return b, set()
