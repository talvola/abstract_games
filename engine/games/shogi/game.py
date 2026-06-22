"""Shogi (Japanese chess), 9x9, full rules, built on the shared Shogi-family core.

Drops (captured pieces switch sides and re-enter from hand), zone promotion (far
three ranks), the two-pawns (nifu), last-rank and drop-mate (uchifuzume) rules,
gold-moving promoted minors and the Dragon King / Dragon Horse -- all supplied by
``agp.shogilike``. Sente (Black, player 0) starts at the bottom and moves first.
Moves use the platform cell notation; a promoting move appends "=+" and a drop is
"L@c,r".
"""

from __future__ import annotations

from agp.shogilike import ShogiLike, BLACK, WHITE

BACK = ["L", "N", "S", "G", "K", "G", "S", "N", "L"]


class Shogi(ShogiLike):
    uid = "shogi"
    name = "Shogi"

    WIDTH = HEIGHT = 9
    ZONE = 3
    PLY_CAP = 400
    # Pretty single-glyph labels (Western piece letters; promoted = "+X").
    LABELS = {
        "K": "K", "R": "R", "B": "B", "G": "G", "S": "S", "N": "N", "L": "L", "P": "P",
        "+R": "+R", "+B": "+B", "+S": "+S", "+N": "+N", "+L": "+L", "+P": "+P",
    }

    def setup_board(self):
        b = {}
        for c in range(9):
            b[(c, 0)] = (BLACK, BACK[c])
            b[(c, 2)] = (BLACK, "P")
            b[(c, 6)] = (WHITE, "P")
            b[(c, 8)] = (WHITE, BACK[c])
        b[(1, 1)] = (BLACK, "B")
        b[(7, 1)] = (BLACK, "R")
        b[(1, 7)] = (WHITE, "R")
        b[(7, 7)] = (WHITE, "B")
        return b, set()
