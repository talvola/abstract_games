"""Cylinder Chess -- standard chess on a board that wraps horizontally.

Identical to standard chess (castling, en passant, pawn double-step and
promotion to Q/R/B/N, check / checkmate / stalemate, and the fifty-move /
threefold-repetition / insufficient-material draws), all supplied by
``agp.chesslike`` -- EXCEPT the board is a vertical CYLINDER: the a-file and the
h-file are joined, so the file index wraps modulo 8 while the rank index stays
bounded 0..7 (ranks do NOT wrap). A rook/queen on the a-file may slide left and
reappear on the h-file; bishops/queens wrap diagonally; a knight's file offset
is taken mod 8.

The ONLY change vs standard chess is the move-generation / attack geometry:

* ``on(c, r)`` keeps the rank bound only (``0 <= r < HEIGHT``); the column is
  always considered "on the board" because it wraps. We therefore do NOT use
  ``on`` to gate the column.
* leaper targets (knight, king) wrap the file: ``tc = (c + dc) % WIDTH`` and the
  target is valid iff its *rank* is on the board.
* slider rays (R/B/Q) are walked here (``attacked`` and ``_pseudo`` are both
  overridden) with the file wrapping mod 8. A ray takes at most ``WIDTH - 1``
  steps so it can never loop all the way around and revisit its own origin
  square; it stops at the first occupied square (a blocker is NOT bypassed by
  wrapping). Pawns are unchanged (they never wrap -- a pawn capture that would
  leave the board is simply not generated, matching real cylinder-chess play
  where pawns advance straight and capture only one file left/right within the
  wrap, which we also support via the wrapped capture squares below).

Because ``attacked`` uses the same wrapped rays, a rook gives check *around* the
cylinder, and the king may not castle through / into a square attacked via the
wrap. Castling is standard (king e1->g1/c1); see rules.md for the source.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class CylinderPawn(StandardPawn):
    """Orthodox pawn whose diagonal captures wrap horizontally (a-pawn can
    capture a piece on the h-file one rank ahead, and vice versa). Straight
    advances never wrap (a file is a file)."""

    def pseudo(self, core, board, c, r, player, ep_target):
        W = core.WIDTH
        fwd = self.fwd(player)
        if core.on(c, r + fwd) and (c, r + fwd) not in board:
            yield (c, r), (c, r + fwd)
            if self.double and r == self.start(player) and (c, r + 2 * fwd) not in board:
                yield (c, r), (c, r + 2 * fwd)
        for dc in (-1, 1):
            t = ((c + dc) % W, r + fwd)
            if not (0 <= t[1] < core.HEIGHT):
                continue
            occ = board.get(t)
            if (occ is not None and occ[0] != player) or t == ep_target:
                yield (c, r), t

    def attacks(self, core, board, c, r, by) -> bool:
        W = core.WIDTH
        pr = r - self.fwd(by)
        return any(board.get(((c + dc) % W, pr)) == (by, "P") for dc in (-1, 1))


class CylinderChess(ChessLike):
    uid = "cylinder_chess"
    name = "Cylinder Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = CylinderPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # ---- cylinder geometry --------------------------------------------------
    # `on` still answers "is this rank on the board?" -- the column is handled by
    # wrapping mod WIDTH in the ray/leaper walkers below, so we keep the standard
    # rank bound but make the column always-valid (callers that pass an already
    # wrapped column get a truthful answer; raw out-of-range columns are never
    # passed to `on` in this subclass).
    def on(self, c, r) -> bool:
        return 0 <= r < self.HEIGHT

    def _slide_targets(self, board, c, r, dc, dr):
        """Yield the squares a slider on (c,r) reaches along (dc,dr), with the
        file wrapping mod WIDTH and the rank bounded. Stops at (and includes) the
        first occupied square. At most WIDTH-1 steps, so a horizontal ray never
        wraps back onto its own origin."""
        W, H = self.WIDTH, self.HEIGHT
        cc, rr = (c + dc) % W, r + dr
        steps = 0
        while 0 <= rr < H and steps < W - 1:
            yield (cc, rr), board.get((cc, rr))
            if board.get((cc, rr)) is not None:
                return
            cc, rr = (cc + dc) % W, rr + dr
            steps += 1

    def attacked(self, board, c, r, by) -> bool:
        W = self.WIDTH
        # leapers (knight, king): wrap the file, bound the rank
        for (dx, dy), types in self._leap_map.items():
            rr = r + dy
            if not (0 <= rr < self.HEIGHT):
                continue
            occ = board.get(((c + dx) % W, rr))
            if occ is not None and occ[0] == by and occ[1] in types:
                return True
        # sliders: walk wrapped rays
        for (dx, dy), types in self._slide_map.items():
            for sq, occ in self._slide_targets(board, c, r, dx, dy):
                if occ is not None:
                    if occ[0] == by and occ[1] in types:
                        return True
                    break
        return self.PAWN.attacks(self, board, c, r, by)

    # ---- move generation (wrapped) -----------------------------------------
    def _pseudo(self, state):
        board, player = state.board, state.to_move
        W = self.WIDTH
        ep_target = state.ep[0] if state.ep else None
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "P":
                yield from self.PAWN.pseudo(self, board, c, r, player, ep_target)
                continue
            slides, leaps = self.PIECES[t]
            # Dedup destinations: on a cylinder the leftward and rightward
            # horizontal rays of a rook/queen on an open rank cover the SAME
            # other files (each ray is WIDTH-1 long), so the two directions
            # would otherwise both offer every far square. We emit each distinct
            # target once.
            seen = set()
            for dc, dr in leaps:
                rr = r + dr
                if not (0 <= rr < self.HEIGHT):
                    continue
                tc = (c + dc) % W
                if (tc, rr) not in seen and (board.get((tc, rr)) or (None,))[0] != player:
                    seen.add((tc, rr))
                    yield (c, r), (tc, rr)
            for dc, dr in slides:
                for sq, occ in self._slide_targets(board, c, r, dc, dr):
                    if occ is None:
                        if sq not in seen:
                            seen.add(sq)
                            yield (c, r), sq
                    else:
                        if occ[0] != player and sq not in seen:
                            seen.add(sq)
                            yield (c, r), sq
                        break
