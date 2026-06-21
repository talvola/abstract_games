"""Courier Chess (Kurierspiel), a medieval 12x8 chess variant (c. 1200),
built on the shared chess-like core (mirrors games/grand_chess: a wide board
with extra pieces).

Pieces (per side):
  * King (K)      -- royal, one step in all 8 directions.
  * Queen/Ferz (F)-- the MEDIEVAL queen: one step DIAGONALLY only.
  * Rook (R)      -- orthogonal slider.
  * Knight (N)    -- (1,2) leaper.
  * Bishop/Alfil (B in our letters -> "A") -- the Shatranj elephant: a (2,2)
    leaper that jumps exactly two squares diagonally (may leap over a piece).
  * Courier (C)   -- the piece the game introduced: an unlimited DIAGONAL
    slider, i.e. exactly the modern bishop.
  * Mann/Sage (M) -- moves like a king (one step any direction) but is NOT
    royal: it can be captured and is not subject to check.
  * Schleich/Wazir(W) -- steps one square orthogonally.

Pawns start on the third rank, step a single square (no double step, no en
passant), capture diagonally, and promote to a Ferz on the last rank.  There is
no castling.  White = player 0.

Letters on the board: K F R N A C M W P (we use "A" for the Alfil and "C" for
the Courier so the modern bishop-slider is visually distinct).
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]   # Shatranj elephant: (2,2) leaper


class FerzPromotion(LastRankPromotion):
    """Pawns promote to a Ferz (the medieval queen) only.  ``safety_piece`` is
    the Ferz too -- the default "Q" piece does not exist in this game."""

    def safety_piece(self) -> str:
        return "F"


# Back rank, files a..l (columns 0..11).
#
# Standard Courier array (after H.J.R. Murray, "A History of Chess" 1913, and
# the Lucas van Leyden painting "The Chess Players"): each colour's back rank,
# from that player's left to right, is
#   R N A C  K M F W  C A N R
# i.e. Rook Knight Alfil Courier | King Mann(Sage) Ferz Schleich(Wazir) |
#      Courier Alfil Knight Rook.
#
# Black is the usual left-right mirror of White, so the central
# King/Mann/Ferz/Wazir block of one side faces that of the other.  Concretely
# (columns a=0 .. l=11): White King on e (col 4), Mann f, Ferz g, Wazir h;
# Black Wazir e, Ferz f, Mann g, King h.  The Ferzes thus stand on the same
# diagonal colour and the kings on opposite wings of the centre, as in the
# historical opening.
WHITE_BACK = ["R", "N", "A", "C", "K", "M", "F", "W", "C", "A", "N", "R"]
BLACK_BACK = list(reversed(WHITE_BACK))   # left-right mirror: ... W F M K ...


class CourierChess(ChessLike):
    uid = "courier_chess"
    name = "Courier Chess"

    WIDTH = 12
    HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []),          # rook
        "N": ([], KNIGHT),         # knight
        "A": ([], ALFIL),          # alfil / bishop -- (2,2) leaper
        "C": (DIAG, []),           # courier -- modern bishop (diagonal slider)
        "F": ([], DIAG),           # ferz / queen -- one-step diagonal
        "W": ([], ORTHO),          # wazir / schleich -- one-step orthogonal
        "M": ([], ALL8),           # mann / sage -- king's move, not royal
        "K": ([], ALL8),           # king -- royal
    }
    # Mating material: anything that is not a lone short-range minor.  The
    # rook, courier (modern bishop) and pawn can force mate; treat them as heavy.
    HEAVY = ("P", "R", "C")
    PAWN = StandardPawn(white_start=2, black_start=5, double=False)
    PROMOTION = FerzPromotion(("F",))
    CASTLING = NoCastling()

    def _insufficient(self, board) -> bool:
        # Courier's short-range pieces (Ferz/Alfil/Wazir/Mann) are genuine mating
        # material — e.g. K + two Manns can checkmate — unlike chess B/N minors.
        # The shared-core heuristic only understands B/N, so it would wrongly draw
        # (and mask real mates in) such endgames. Only bare K-vs-K is a forced
        # draw here; any other material plays on (drawing by the ply cap if truly
        # dead). See rules.md.
        return all(t == "K" for (_, t) in board.values())

    def setup_board(self) -> dict:
        b = {}
        for c in range(self.WIDTH):
            b[(c, 0)] = (WHITE, WHITE_BACK[c])
            b[(c, 2)] = (WHITE, "P")
            b[(c, 5)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BLACK_BACK[c])
        return b
