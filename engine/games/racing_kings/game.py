"""Racing Kings (8x8) -- both kings race to the eighth rank.

A V. R. Parton chess variant (1961). No pawns, no castling, no en passant; the
pieces (K Q R B N) move exactly as in orthodox chess. The twist:

* **Check is forbidden.** It is illegal to move your own king into check (as
  usual) *and* illegal to make any move that gives check to the opponent's king.
  Because of this kings are never actually in check during play and there is no
  checkmate.
* **Goal: reach the eighth rank (row 7).** The first player to move their king
  onto row 7 wins -- with one exception that compensates for White's tempo:
* **White-reaches / Black-replies draw.** If White moves their king to row 7,
  Black gets one more move; if Black can also bring their king to row 7 on that
  immediate reply, both kings are home and the game is a **draw**. (Black moving
  to row 7 is otherwise an immediate Black win, since White has no further reply.)

Built on :class:`agp.chesslike.ChessLike`: the board model, slider/leaper move
generation, attack/king-safety testing and (de)serialization are all inherited.
This module adds the no-pawn setup, the "may not give check" move filter, and the
race win/draw conditions. White = player 0 and starts on the king's side (right
half); both players view the board from the same side.

Correctness anchor: the published Racing Kings opening perft (shakmaty's
``racingkings.perft`` and the Fairy-Stockfish test suite) --
21 / 421 / 11264 / 296242 at depths 1..4 for the standard start
``8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1``. See ``selftest.py``.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, PawnRules, NoCastling, PromotionRules,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

GOAL_ROW = 7  # the eighth rank


class NoPawn(PawnRules):
    """Racing Kings has no pawns; this strategy never generates or attacks."""

    def __init__(self):
        super().__init__(white_start=-1, black_start=-1, double=False)

    def pseudo(self, core, board, c, r, player, ep_target):
        return iter(())

    def attacks(self, core, board, c, r, by) -> bool:
        return False


class NoPromotion(PromotionRules):
    def options(self, core, state, frm, to):
        return [None]


class RacingKings(ChessLike):
    uid = "racing_kings"
    name = "Racing Kings"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    # No pawns; "heavy" only matters for the insufficient-material draw, which we
    # disable below, but keep the real heavies listed for completeness.
    HEAVY = ("R", "Q")
    PAWN = NoPawn()
    PROMOTION = NoPromotion()
    CASTLING = NoCastling()

    # Standard Racing Kings start (python-chess / Fairy-Stockfish / shakmaty):
    #   FEN  8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1
    # rank 2 (row 1):  a2 k  b2 r  c2 b  d2 n  e2 N  f2 B  g2 R  h2 K
    # rank 1 (row 0):  a1 q  b1 r  c1 b  d1 n  e1 N  f1 B  g1 R  h1 Q
    # lower-case = Black (player 1), upper-case = White (player 0).
    _RANK2 = [(BLACK, "K"), (BLACK, "R"), (BLACK, "B"), (BLACK, "N"),
              (WHITE, "N"), (WHITE, "B"), (WHITE, "R"), (WHITE, "K")]
    _RANK1 = [(BLACK, "Q"), (BLACK, "R"), (BLACK, "B"), (BLACK, "N"),
              (WHITE, "N"), (WHITE, "B"), (WHITE, "R"), (WHITE, "Q")]

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = self._RANK1[c]
            b[(c, 1)] = self._RANK2[c]
        return b

    # ------------------------------------------------------------------ #
    # Race win/draw helpers
    # ------------------------------------------------------------------ #
    def _king_row(self, board, player):
        k = self._king(board, player)
        return None if k is None else k[1]

    def _variant_end(self, state) -> bool:
        """Has the race ended? Mirrors python-chess RacingKingsBoard.is_variant_end.

        No king on the goal row -> not ended. Otherwise it is ended unless it is
        Black to move with only White home: then Black still has its one reply,
        and the game is over only if Black *cannot* legally bring its king to an
        (empty) goal-row square -- every such square is either occupied by a Black
        piece or attacked by White (so stepping there would be moving into check,
        which is forbidden). If Black can reach the goal row, play continues so
        Black may equalise (-> draw)."""
        wr = self._king_row(state.board, WHITE)
        br = self._king_row(state.board, BLACK)
        white_home = wr == GOAL_ROW
        black_home = br == GOAL_ROW
        if not (white_home or black_home):
            return False
        if state.to_move == WHITE or black_home:
            return True
        # Black to move, only White is home: ended iff Black can't safely step a
        # king onto an empty goal-row square.
        bk = self._king(state.board, BLACK)
        for dc in (-1, 0, 1):
            tc, tr = bk[0] + dc, GOAL_ROW
            if not self.on(tc, tr):
                continue
            occ = state.board.get((tc, tr))
            if occ is not None and occ[0] == BLACK:
                continue  # blocked by own piece
            if abs(tr - bk[1]) > 1:
                continue  # not a king step
            if not self.attacked(state.board, tc, tr, WHITE):
                return False  # Black has a safe dash to the goal row
        return True

    def _winner(self, state):
        """0 = White wins, 1 = Black wins, 2 = draw, None = undecided."""
        if not self._variant_end(state):
            return None
        white_home = self._king_row(state.board, WHITE) == GOAL_ROW
        black_home = self._king_row(state.board, BLACK) == GOAL_ROW
        if white_home and black_home:
            return 2
        return 0 if white_home else 1

    # ------------------------------------------------------------------ #
    # Move generation: standard legality PLUS "may not give check"
    # ------------------------------------------------------------------ #
    def _legal(self, state):
        # No moves once the race is decided.
        if self._winner(state) is not None:
            return []
        enemy = 1 - state.to_move
        moves = []
        for frm, to in self._pseudo(state):
            nb = self._apply_board(state.board, frm, to, state.ep)
            # Must not leave own king in check, and must not give check.
            if self.in_check(nb, state.to_move):
                continue
            if self.in_check(nb, enemy):
                continue
            moves.append((frm, to))
        # No castling in Racing Kings (CASTLING is NoCastling, so .moves() is empty).
        return moves

    def legal_moves(self, state) -> list:
        if self.is_terminal(state):
            return []
        return [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for f, t in self._legal(state)]

    # ------------------------------------------------------------------ #
    # Terminal / returns
    # ------------------------------------------------------------------ #
    def _draw_other(self, state) -> bool:
        # Loop guards. (No fifty-move/insufficient-material draws -- there are no
        # pawns, captures are frequent, and material can be reduced to bare kings
        # which still race; rely on threefold repetition + the ply cap.)
        if state.ply >= self.PLY_CAP:
            return True
        key = self._poskey(state.board, state.to_move, state.castling, state.ep)
        return state.reps.get(key, 0) >= 3

    def is_terminal(self, state) -> bool:
        if self._winner(state) is not None:
            return True
        if self._draw_other(state):
            return True
        return len(self._legal(state)) == 0

    def returns(self, state) -> list:
        w = self._winner(state)
        if w == 0:
            return [1.0, -1.0]
        if w == 1:
            return [-1.0, 1.0]
        # Draw: both home, repetition/ply cap, or stalemate (no legal moves).
        return [0.0, 0.0]

    # ------------------------------------------------------------------ #
    # Presentation
    # ------------------------------------------------------------------ #
    def describe_move(self, state, move) -> str:
        fs, ts = move.split(">")
        fc, fr = (int(x) for x in fs.split(","))
        tc, tr = (int(x) for x in ts.split(","))
        pl, t = state.board.get((fc, fr), (None, "?"))
        capture = (tc, tr) in state.board
        files = "abcdefgh"
        alg = lambda c, r: f"{files[c]}{r + 1}"  # noqa: E731
        return f"{t}{alg(fc, fr)}{'x' if capture else '-'}{alg(tc, tr)}"

    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": t}
            for (c, r), (pl, t) in state.board.items()
        ]
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                caption = "Draw"
            else:
                caption = f"{names[0 if ret[0] > 0 else 1]} wins (reached the 8th rank)"
        else:
            caption = f"{names[state.to_move]} to move"
        # Highlight the goal rank lightly via the caption only; the renderer
        # draws the board generically.
        return {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
