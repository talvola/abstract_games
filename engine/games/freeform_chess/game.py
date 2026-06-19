"""Freeform Board (8x8) — an unenforced sandbox built on agp.FreeformGame.

Demonstrates the freeform / honor-system mode: a board + starting position with
no movement or win rules (see agp/freeform.py and engine/FREEFORM_MODE.md). The
opening is the standard chess array, but nothing is enforced — any piece may move
anywhere — so it doubles as a hand-played board for any 8x8 variant.
"""

from __future__ import annotations

from agp.freeform import FreeformGame

WHITE, BLACK = 0, 1
BACK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class FreeformChess(FreeformGame):
    uid = "freeform_chess"
    name = "Freeform Board (8×8)"
    WIDTH = HEIGHT = 8

    def setup_board(self) -> dict:
        b = {}
        for c, t in enumerate(BACK):
            b[(c, 0)] = (WHITE, t)
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, t)
        return b
