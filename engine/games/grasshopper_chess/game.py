"""Grasshopper Chess (Joseph Boyer, 1950s), on the shared chess-like core.

Standard 8x8 chess plus an extra rank of **grasshoppers** (G) directly in front
of each side's pawns: White grasshoppers on rank 3 (row 2), Black grasshoppers on
rank 6 (row 5). Pawns stay on their usual ranks (rows 1 / 6) and the back rank is
unchanged, so each side starts with 8 pawns, 8 grasshoppers and the 8 orthodox
pieces (24 men per side; 48 men total).

The **grasshopper** is a fairy "hopper" that moves along the eight queen lines
(ranks, files, diagonals) but ONLY by hopping over exactly one piece -- the
"hurdle", of either colour -- and landing on the square IMMEDIATELY BEYOND the
hurdle. If that landing square is empty it is a move; if it holds an enemy piece
it is a capture; if it holds a friendly piece, or is off the board, that
direction is blocked. A grasshopper has no move along a direction that contains no
hurdle. Grasshoppers give check the same way (a grasshopper checks the king if it
could hop onto the king's square).

Everything else is orthodox chess: pawns (double-step, en passant, promotion to
Q/R/B/N), castling, check / checkmate / stalemate, and
draws by the fifty-move rule, threefold repetition and a hard ply cap (insufficient
material is disabled -- a lone grasshopper's value is unclear, so we never claim
an automatic material draw; the ply cap still guarantees termination). White =
player 0.

Implementation notes (how the hopper was added to ChessLike):
  * "G" is registered in PIECES with EMPTY slide/leap lists, so the base
    ``_pseudo`` / ``attacked`` slider-leaper machinery generates nothing for it.
  * ``_grasshopper_targets`` does the hop move-gen, modelled on the xiangqi cannon
    screen-scan but landing IMMEDIATELY past the hurdle (the cannon may land
    anywhere beyond its screen; the grasshopper lands on the very next square).
    For each of the 8 queen directions it scans to the first occupied square (the
    hurdle); the single candidate is the square one step further. Empty -> move,
    enemy -> capture, friend/off-board -> blocked.
  * ``_pseudo`` is overridden to also yield grasshopper hops (the base handles
    every other piece type unchanged).
  * ``attacked`` is overridden so grasshopper checks are detected: from the target
    square, in each of the 8 directions, the adjacent square is a potential hurdle;
    if it is occupied, scan past it to the first piece -- if that is an enemy
    grasshopper it attacks the target square.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class GrasshopperChess(ChessLike):
    uid = "grasshopper_chess"
    name = "Grasshopper Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
        "G": ([], []),     # grasshopper: hop move-gen is custom (see below)
    }
    HEAVY = ("P", "R", "Q", "G")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 2)] = (WHITE, "G")      # White grasshoppers, rank 3
            b[(c, 5)] = (BLACK, "G")      # Black grasshoppers, rank 6
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # ---- grasshopper hop move-gen -------------------------------------------
    def _grasshopper_targets(self, board, c, r, player):
        """Squares the grasshopper at (c, r) can hop to: along each queen line,
        over exactly one hurdle and onto the square immediately beyond it."""
        for dc, dr in ALL8:
            cc, rr = c + dc, r + dr
            # scan to the first piece (the hurdle)
            while self.on(cc, rr) and (cc, rr) not in board:
                cc += dc
                rr += dr
            if not self.on(cc, rr):
                continue                          # no hurdle in this direction
            # the landing square is the one immediately beyond the hurdle
            lc, lr = cc + dc, rr + dr
            if not self.on(lc, lr):
                continue                          # hurdle on the edge -> blocked
            occ = board.get((lc, lr))
            if occ is None or occ[0] != player:   # empty = move, enemy = capture
                yield (c, r), (lc, lr)

    def _pseudo(self, state):
        board, player = state.board, state.to_move
        for (c, r), (pl, t) in list(board.items()):
            if pl == player and t == "G":
                yield from self._grasshopper_targets(board, c, r, player)
        yield from super()._pseudo(state)

    # ---- attack detection (check) must include grasshopper hops -------------
    def attacked(self, board, c, r, by) -> bool:
        if super().attacked(board, c, r, by):
            return True
        # An enemy grasshopper attacks (c, r) if it can hop onto it: the square
        # adjacent to (c, r) in some direction is a hurdle, and the first piece
        # beyond the hurdle (in that same direction) is an enemy grasshopper.
        for dc, dr in ALL8:
            hc, hr = c + dc, r + dr
            if not self.on(hc, hr) or (hc, hr) not in board:
                continue                          # need an occupied hurdle adjacent
            cc, rr = hc + dc, hr + dr
            while self.on(cc, rr) and (cc, rr) not in board:
                cc += dc
                rr += dr
            if self.on(cc, rr):
                occ = board[(cc, rr)]
                if occ[0] == by and occ[1] == "G":
                    return True
        return False

    # ---- a lone grasshopper has unclear value: never auto-draw on material ---
    def _insufficient(self, board) -> bool:
        return False
