"""Horde Chess -- the lichess variant, built on the shared chess-like core.

Black fields the standard 16-piece army with its normal goal (deliver checkmate).
White has NO king: instead it fields 36 pawns filling the bottom ranks. The two
asymmetric win conditions are:

* **Black wins** by capturing the *entire* horde -- when White has no pieces left.
* **White wins** by checkmating Black's king.
* Stalemate (the side to move has no legal move and, for Black, is not in check)
  is a draw, as are the usual fifty-move / repetition draws.

White having no king means White is never in check and can never be mated; the
shared core already yields this (``_king`` returns ``None`` -> ``in_check`` False),
so White simply moves all pseudo-legal moves. The first-rank double-step is the
one extra Horde rule, supplied by :class:`HordePawn`. The terminal / winner logic
is overridden here so that an empty White army is a Black win (not a draw) while a
genuine White stalemate stays a draw.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, PawnRules, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# Official lichess Horde starting position:
#   rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1
START_FEN = "rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP"


def parse_fen_board(fen: str) -> dict:
    """Parse the piece-placement field of a FEN into a ``(c, r) -> (player, T)``
    board. Rank 8 is the first FEN row and maps to ``r = HEIGHT-1``; rank 1 maps
    to ``r = 0``. Uppercase = White (player 0), lowercase = Black (player 1)."""
    rows = fen.split("/")
    height = len(rows)
    board = {}
    for i, row in enumerate(rows):
        r = height - 1 - i
        c = 0
        for ch in row:
            if ch.isdigit():
                c += int(ch)
                continue
            player = WHITE if ch.isupper() else BLACK
            board[(c, r)] = (player, ch.upper())
            c += 1
    return board


class HordePawn(StandardPawn):
    """An orthodox pawn, except White's pawns may take the two-square step from
    BOTH their home rank *and* the first rank (Horde's special rule). En passant
    applies to those double steps exactly as usual (the generic ``ep_after`` only
    checks the two-rank jump, so a first-rank double step is e.p.-capturable)."""

    def __init__(self, white_starts, black_start):
        # white_starts: the set of ranks White may double-step from.
        super().__init__(white_start=min(white_starts), black_start=black_start)
        self._white_starts = frozenset(white_starts)

    def pseudo(self, core, board, c, r, player, ep_target):
        fwd = self.fwd(player)
        if core.on(c, r + fwd) and (c, r + fwd) not in board:
            yield (c, r), (c, r + fwd)
            home = (r in self._white_starts) if player == WHITE else (r == self.black_start)
            if self.double and home and (c, r + 2 * fwd) not in board:
                yield (c, r), (c, r + 2 * fwd)
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if (occ is not None and occ[0] != player) or t == ep_target:
                yield (c, r), t


class HordeChess(ChessLike):
    uid = "horde_chess"
    name = "Horde Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    # White may double-step from rank 1 (r=0, the Horde rule) and rank 2 (r=1);
    # Black's pawns double-step from their home rank 7 (r=6) as normal.
    PAWN = HordePawn(white_starts=(0, 1), black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    # Only Black has a king/rooks in their home squares, so only Black can castle.
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        return parse_fen_board(START_FEN)

    def initial_state(self, options=None, rng=None):
        st = super().initial_state(options=options, rng=rng)
        # Lichess Horde FEN advertises only Black's castling rights ("kq").
        st.castling = frozenset("kq")
        st.reps = {self._poskey(st.board, WHITE, st.castling, None): 1}
        return st

    # ---- terminal / winner --------------------------------------------------
    def _white_has_pieces(self, board) -> bool:
        return any(pl == WHITE for (_, (pl, _)) in board.items())

    def is_terminal(self, state) -> bool:
        # Black annihilated the horde -> game over (Black has won) even though the
        # side to move (White) "having no moves" would otherwise look like
        # stalemate. Keep the explicit check so the meaning is unambiguous.
        if not self._white_has_pieces(state.board):
            return True
        return super().is_terminal(state)

    def returns(self, state) -> list:
        # Black wins iff the horde is gone.
        if not self._white_has_pieces(state.board):
            return [-1.0, 1.0]
        # Ordinary draws (fifty-move / repetition / insufficient material / ply cap).
        if self._draw(state):
            return [0.0, 0.0]
        # If the side to move still has a legal move it is not terminal; payoff 0.
        if len(self._legal(state)) > 0:
            return [0.0, 0.0]
        # No legal moves and the horde survives:
        #  - White to move with no move = stalemate of White -> draw.
        #  - Black to move: checkmate (in check) -> White wins; else stalemate draw.
        if state.to_move == BLACK and self.in_check(state.board, BLACK):
            return [1.0, -1.0]
        return [0.0, 0.0]

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "White (horde)", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                spec["caption"] = "Draw"
            elif ret[1] > 0:
                reason = "horde annihilated" if not self._white_has_pieces(state.board) else "checkmate"
                spec["caption"] = f"Black wins ({reason})"
            else:
                spec["caption"] = "White (horde) wins (checkmate)"
        elif state.to_move == BLACK and self.in_check(state.board, BLACK):
            spec["caption"] = "Black to move (check)"
        else:
            spec["caption"] = f"{names[state.to_move]} to move"
        return spec
