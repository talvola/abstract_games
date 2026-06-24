"""Checkless Chess (8x8).

Standard chess in every way *except* one restriction on checking: **a player may
not make a move that gives check to the opponent's king unless that move is
checkmate.**  In other words, you are only ever allowed to give check when the
check is mate; any other checking move -- including a discovered check or a
double check -- is illegal and is simply removed from the move list.

Because non-mating checks are forbidden, the enemy king becomes a powerful piece:
it can walk up the board into squares that *would* be attacked, since the
opponent is not allowed to actually deliver the resulting (non-mating) check.

Everything else is orthodox: castling, en passant, the pawn double-step and
promotion, stalemate, and the fifty-move / threefold / insufficient-material
draws -- all inherited unchanged from ``agp.chesslike``.  White = player 0.

Implementation of the "check only if mate" filter
-------------------------------------------------
The shared core already produces, for the side to move, every move that is legal
in ordinary chess (the mover's own king is left safe).  On top of that base set
this class removes any move whose *resulting* position leaves the **opponent** in
check but is **not** checkmate.  Concretely, for each candidate move string we:

1. apply it (via the inherited ``apply_move``) to get the successor position,
2. if the opponent (the new side to move) is **not** in check -> keep the move
   (the common case; movement is identical to chess),
3. if the opponent **is** in check -> keep the move **iff** it is checkmate,
   i.e. iff the opponent has no legal reply.

Avoiding infinite recursion.  Testing "is this checkmate?" means asking whether
the checked opponent has any legal reply -- but the opponent's replies are in
principle *also* subject to the checkless restriction, which would recurse.  We
break the recursion by computing the opponent's escape replies with the
**ordinary-chess** move generator (the inherited ``super()._legal`` plus drops),
**not** the checkless-filtered one.  This is both well-defined (it terminates
immediately -- one ply, no checkless test) and the natural ruleset: a player who
is in check must be allowed to escape, so any move that gets the opponent's king
to safety counts as an escape even if it happens to give check back (a
"cross-check").  Equivalently: **a position is checkmate in Checkless Chess
exactly when it is checkmate in ordinary chess**, so a checking move is legal iff
it mates by the standard definition.  (chessvariants.com / Wikipedia note an
alternative "cross-checks don't count as escapes" reading; we deliberately adopt
the simpler standard-mate definition and document it here and in rules.md.)
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class ChecklessChess(ChessLike):
    uid = "checkless_chess"
    name = "Checkless Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
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

    # ---- the checkless filter ----------------------------------------------
    def _standard_has_reply(self, state) -> bool:
        """Does the side to move in ``state`` have any *ordinary-chess* legal
        move?  Used as the mate test for a checked opponent -- it ignores the
        checkless restriction (and so terminates immediately, no recursion)."""
        if super()._legal(state):
            return True
        return bool(self._drop_moves(state))

    def _move_allowed(self, state, move) -> bool:
        """True unless ``move`` gives the opponent a non-mating check.

        ``move`` is already known to be ordinary-chess-legal for ``state`` (the
        mover's king is safe).  We apply it and inspect the successor: a move is
        forbidden only when it leaves the opponent in check yet the opponent
        still has an ordinary-chess reply (so the check is not mate)."""
        succ = super().apply_move(state, move)
        # In the successor, ``to_move`` is the opponent of the mover.
        if not self.in_check(succ.board, succ.to_move):
            return True
        # A check is allowed iff it is checkmate (no ordinary-chess escape).
        return not self._standard_has_reply(succ)

    def legal_moves(self, state) -> list:
        return [m for m in super().legal_moves(state) if self._move_allowed(state, m)]

    # ---- terminal / result --------------------------------------------------
    # Movement is filtered only by ``legal_moves``; ``is_terminal`` / ``returns``
    # must agree with it.  A position is terminal when the checkless move list is
    # empty.  If the side to move is then in check it is genuine checkmate (the
    # opponent's checking move was, by the rule above, only legal because it was
    # mate), so the opponent wins; otherwise it is stalemate (a draw) -- this
    # includes the case where every king-safe move would give a non-mating check.
    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        return not self.legal_moves(state)

    # ``returns`` is identical to the base rule: on a terminal position it is a
    # draw iff drawn or the side to move is not in check (stalemate), else the
    # side to move is checkmated and the opponent wins.  Inherited unchanged.
