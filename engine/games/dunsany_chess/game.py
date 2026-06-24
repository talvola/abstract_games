"""Dunsany's Chess -- Lord Dunsany's asymmetric variant (1942).

Black fields the standard 16-piece army with the ordinary goal (deliver
checkmate). White has NO king: instead it fields **32 pawns** filling ranks 1-4.
The two asymmetric win conditions are:

* **Black wins** by capturing the *entire* pawn army -- when White has no pieces
  left on the board.
* **White wins** by checkmating Black's king.
* Stalemate (the side to move has no legal move and, for Black, is not in check)
  is a draw, as are the usual fifty-move / repetition draws.

This is closely related to Horde Chess (which the platform also ships), and the
implementation reuses Horde's machinery: a king-less pawn army (White is never in
check -- ``_king`` returns ``None`` -> ``in_check`` False), win-by-annihilation,
and the same asymmetric terminal/winner logic. The DIFFERENCES from Horde are:

  1. **32 pawns on the FOUR full ranks 1-4** (Horde packs 36 pawns in a different
     shape, with four extra on rank 5).
  2. **Black moves first** (Horde is White-to-move). Dunsany's gives the piece
     side the first move; ``initial_state`` overrides ``to_move`` to Black.
  3. **No double-step for White's pawns.** In Horde, White's pawns may double-step
     from rank 1 *and* rank 2. In Dunsany's, *only Black's* pawns get the
     two-square first move; White's pawns always single-step. (Hence no White
     pawn can ever be captured en passant -- it never makes a two-rank jump.)

See ``rules.md`` for the full ruleset and sources.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class DunsanyPawn(StandardPawn):
    """An orthodox pawn, except White's pawns NEVER get the initial two-square
    move (only Black's do). Capturing and en passant are otherwise standard; since
    a White pawn never makes a two-rank jump it never creates an e.p. target and
    so can never be captured en passant -- consistent with the Dunsany rule."""

    def pseudo(self, core, board, c, r, player, ep_target):
        fwd = self.fwd(player)
        if core.on(c, r + fwd) and (c, r + fwd) not in board:
            yield (c, r), (c, r + fwd)
            # Only Black double-steps (from its home rank); White never does.
            if (self.double and player == BLACK and r == self.black_start
                    and (c, r + 2 * fwd) not in board):
                yield (c, r), (c, r + 2 * fwd)
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if (occ is not None and occ[0] != player) or t == ep_target:
                yield (c, r), t


class DunsanyChess(ChessLike):
    uid = "dunsany_chess"
    name = "Dunsany's Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    # white_start is unused (White never double-steps); Black double-steps from r=6.
    PAWN = DunsanyPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    # Only Black has a king/rooks on home squares, so only Black can castle.
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        b = {}
        # White: 32 pawns filling the bottom four ranks (1-4 -> r = 0..3).
        for r in range(4):
            for c in range(8):
                b[(c, r)] = (WHITE, "P")
        # Black: the ordinary army on ranks 7-8 (r = 6, 7).
        for c in range(8):
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    def initial_state(self, options=None, rng=None):
        st = super().initial_state(options=options, rng=rng)
        # Dunsany's: BLACK moves first (the piece side opens).
        st.to_move = BLACK
        # Only Black has castling rights ("kq"); White has no king or home rooks.
        st.castling = frozenset("kq")
        st.reps = {self._poskey(st.board, BLACK, st.castling, None): 1}
        return st

    # ---- terminal / winner --------------------------------------------------
    def _white_has_pieces(self, board) -> bool:
        return any(pl == WHITE for (_, (pl, _)) in board.items())

    def is_terminal(self, state) -> bool:
        # Black annihilated the pawn army -> game over (Black has won) even though
        # the side to move (White) "having no moves" would otherwise look like a
        # stalemate. Keep the explicit check so the meaning is unambiguous.
        if not self._white_has_pieces(state.board):
            return True
        return super().is_terminal(state)

    def returns(self, state) -> list:
        # Black wins iff the pawn army is gone.
        if not self._white_has_pieces(state.board):
            return [-1.0, 1.0]
        # Ordinary draws (fifty-move / repetition / insufficient material / ply cap).
        if self._draw(state):
            return [0.0, 0.0]
        # If the side to move still has a legal move it is not terminal; payoff 0.
        if len(self._legal(state)) > 0:
            return [0.0, 0.0]
        # No legal moves and the pawn army survives:
        #  - White to move with no move = stalemate of White -> draw.
        #  - Black to move: checkmate (in check) -> White wins; else stalemate draw.
        if state.to_move == BLACK and self.in_check(state.board, BLACK):
            return [1.0, -1.0]
        return [0.0, 0.0]

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "White (pawns)", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                spec["caption"] = "Draw"
            elif ret[1] > 0:
                reason = ("pawn army annihilated"
                          if not self._white_has_pieces(state.board) else "checkmate")
                spec["caption"] = f"Black wins ({reason})"
            else:
                spec["caption"] = "White (pawns) wins (checkmate)"
        elif state.to_move == BLACK and self.in_check(state.board, BLACK):
            spec["caption"] = "Black to move (check)"
        else:
            spec["caption"] = f"{names[state.to_move]} to move"
        return spec
