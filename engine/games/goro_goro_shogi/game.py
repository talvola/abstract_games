"""Goro Goro Shogi (Gorogoro Shogi / "ごろごろ将棋", 5x6 shogi variant), built on
the same ShogiLike core as full Shogi -- so its move generation, drops and
promotion are exactly the python-shogi-verified engine, only on a 5x6 board with
the reduced Goro Goro army.

Each side has eight pieces: King (K), two Golds (G), two Silvers (S) and three
Pawns (P) -- no rook, bishop, knight or lance. (Goro Goro / "five-six" names the
5x6 board.) The promotion zone is the **far two ranks** (ZONE = 2). Drops,
captures-switch-sides, the two-pawns (nifu) and drop-mate (uchifuzume) rules are
inherited unchanged. Only the Silver and Pawn can promote (both to a Gold-mover);
Gold and King never promote.

Standard setup (5x6 ``sgkgs/5/1ppp1/1PPP1/5/SGKGS``): the back rank is
**S G K G S** with the King centred, and the three Pawns sit on the central three
files of the rank in front. The back rank is its own 180deg rotation, so both
armies share the same order.
"""

from __future__ import annotations

from agp.shogilike import ShogiLike, BLACK, WHITE


class GoroGoroShogi(ShogiLike):
    uid = "goro_goro_shogi"
    name = "Goro Goro Shogi"

    WIDTH = 5
    HEIGHT = 6
    ZONE = 2                 # the far two ranks promote
    PLY_CAP = 300
    LABELS = {
        "K": "K", "G": "G", "S": "S", "P": "P",
        "+S": "+S", "+P": "+P",
    }

    def setup_board(self):
        b = {}
        # Black (Sente) home rank at the bottom (row 0): S G K G S
        for c, t in enumerate("SGKGS"):
            b[(c, 0)] = (BLACK, t)
        # Black's three pawns on the central three files, one rank up (row 1)
        for c in (1, 2, 3):
            b[(c, 1)] = (BLACK, "P")
        # White (Gote) home rank at the top (row 5): S G K G S (180deg rotation)
        for c, t in enumerate("SGKGS"):
            b[(c, 5)] = (WHITE, t)
        for c in (1, 2, 3):
            b[(c, 4)] = (WHITE, "P")
        return b, set()
