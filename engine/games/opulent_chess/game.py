"""Opulent Chess (Greg Strong, 2005), 10x10, built on the shared core.

A Grand Chess derivative with two compound pieces -- the Chancellor "C"
(rook + knight) and the Archbishop "A" (bishop + knight) -- plus two new
short-range leapers and a strengthened Knight:

* **Wizard "W"** -- camel (1,3)-leaper + ferz (one step diagonally). Colorbound.
* **Lion "L"**   -- Betza's Half-Duck: leaps 2 or 3 squares orthogonally
  (jumping over anything in between) or steps one square diagonally.
* **Knight "N"** -- standard knight + wazir (one step orthogonally).

The Archbishop/Chancellor knight component is the ORTHODOX knight (it does NOT
inherit the Knight's extra wazir step). Pawns start on the third rank with an
optional double step and en passant; there is no castling; promotion follows
Grand Chess (only to a piece type the owner has lost; optional on ranks 8/9,
compulsory on rank 10 -- a pawn with nothing to promote to may not enter the
last rank). Checkmate wins. White = player 0.

Source: https://www.chessvariants.com/rules/opulent-chess
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, GrandPromotion, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]
DABBABAH = [(2, 0), (-2, 0), (0, 2), (0, -2)]
THREELEAP = [(3, 0), (-3, 0), (0, 3), (0, -3)]           # Betza "H"

RANK2 = ["C", "L", "N", "B", "Q", "K", "B", "N", "L", "A"]   # files a..j


class OpulentChess(ChessLike):
    name = "Opulent Chess"

    WIDTH = HEIGHT = 10
    PLY_CAP = 800
    PIECES = {
        "R": (ORTHO, []),
        "B": (DIAG, []),
        "Q": (ALL8, []),
        "N": ([], KNIGHT + ORTHO),          # knight + wazir
        "W": ([], CAMEL + DIAG),            # camel + ferz (colorbound)
        "L": ([], DABBABAH + THREELEAP + DIAG),  # Half-Duck
        "C": (ORTHO, KNIGHT),               # rook + orthodox knight
        "A": (DIAG, KNIGHT),                # bishop + orthodox knight
        "K": ([], ALL8),
    }
    # Everything except a lone bishop counts as mating material (the fairy
    # leapers are all worth ~a rook-minor; never auto-draw them away).
    HEAVY = ("P", "R", "Q", "C", "A", "L", "W", "N")
    # Author's published midgame values (quick-reference chart on the source page).
    PIECE_VALUES = {"P": 1.0, "B": 4.0, "W": 4.5, "N": 4.75, "L": 4.75,
                    "R": 5.5, "A": 7.5, "C": 9.25, "Q": 10.0, "K": 0.0}
    PAWN = StandardPawn(white_start=2, black_start=7)
    PROMOTION = GrandPromotion({"Q": 1, "C": 1, "A": 1, "R": 2,
                                "B": 2, "N": 2, "L": 2, "W": 2})
    CASTLING = NoCastling()

    def setup_board(self) -> dict:
        b = {}
        b[(0, 0)] = b[(9, 0)] = (WHITE, "R")
        b[(1, 0)] = b[(8, 0)] = (WHITE, "W")
        b[(0, 9)] = b[(9, 9)] = (BLACK, "R")
        b[(1, 9)] = b[(8, 9)] = (BLACK, "W")
        for i, t in enumerate(RANK2):
            b[(i, 1)] = (WHITE, t)
            b[(i, 8)] = (BLACK, t)
        for c in range(10):
            b[(c, 2)] = (WHITE, "P")
            b[(c, 7)] = (BLACK, "P")
        return b
