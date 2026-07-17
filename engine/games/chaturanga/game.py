"""Chaturanga -- the ancient Indian ancestor of chess (~6th-7th century A.D.).

Built on the shared chess-like core (``agp.chesslike``), templated off
``games/shatranj`` (its direct descendant).  The army (Sanskrit names):

* **Raja** (King, ``K``) -- one square in any direction. NO castling; this
  package follows Murray/Golombek and gives the Raja no one-time knight leap
  (that privilege is Gollon's reconstruction -- see ``rules.md``).
* **Mantri** (Minister / counsellor, ``F``) -- exactly ONE square diagonally
  (the ferz), ancestor of the queen.
* **Gaja** (Elephant, ``A``) -- LEAPS exactly two squares diagonally, jumping
  over the square in between (the alfil), ancestor of the bishop.
* **Ratha** (Chariot, ``R``) -- moves like a chess rook.
* **Ashva** (Horse, ``N``) -- the chess knight's leap.
* **Padati** (Foot-soldier, ``P``) -- one square straight forward (NO double
  step, no en passant), captures one square diagonally forward, promotes ONLY
  to a Mantri on the last rank.

Setup: the Rajas do NOT face each other (Wikipedia; the chessvariants.com play
preset): White Raja e1 / Mantri d1, Black Raja d8 / Mantri e8.

Results differ from both chess and Shatranj:

* **Checkmate** -- the mated side loses (as in chess).
* **Stalemate is a WIN for the STALEMATED player** (al-Adli via Murray p.6 and
  Golombek p.19) -- the OPPOSITE of Shatranj, where the stalemated side loses.
* **Baring the enemy king wins OUTRIGHT** -- first to reduce the opponent to a
  lone king wins, with NO Shatranj-style "bare back next move -> draw"
  exception (al-Adli: "the player that is FIRST to bare the opponent's king
  wins").  Two simultaneously bare kings (unreachable in play, but possible in
  hand-built positions) are an honest draw.

Chaturanga had no fifty-move / repetition / insufficient-material draws; the
only automatic draw is a ply cap guaranteeing termination.  White = player 0.
See ``rules.md`` for the exact ruleset choices and documented alternatives.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, NoCastling,
    ORTHO, KNIGHT, WHITE, BLACK,
)

# Mantri (ferz): one square diagonally.
FERZ = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
# Gaja (alfil): exactly two squares diagonally, leaping the square between.
ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]

# a1..h1: Mantri on d1, Raja on e1;  a8..h8: Raja on d8, Mantri on e8.
WHITE_BACK = ["R", "N", "A", "F", "K", "A", "N", "R"]
BLACK_BACK = ["R", "N", "A", "K", "F", "A", "N", "R"]


class Chaturanga(ChessLike):
    uid = "chaturanga"
    name = "Chaturanga"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []),        # Ratha -- chariot (rook)
        "N": ([], KNIGHT),       # Ashva -- horse (knight)
        "A": ([], ALFIL),        # Gaja -- elephant, (2,2) leaper
        "F": ([], FERZ),         # Mantri -- minister, one-step diagonal
        "K": ([], ORTHO + FERZ), # Raja -- king
    }
    # Baring the king is decisive, so the insufficient-material draw is switched
    # off entirely (see _draw); HEAVY is left broad for clarity.
    HEAVY = ("P", "R", "F", "A", "N")
    PAWN = StandardPawn(white_start=1, black_start=6, double=False)
    PROMOTION = LastRankPromotion(("F",))   # Padati promotes only to a Mantri
    CASTLING = NoCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, WHITE_BACK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BLACK_BACK[c])
        return b

    # ---- draws --------------------------------------------------------------
    def _draw(self, state) -> bool:
        """Chaturanga had no fifty-move / threefold-repetition / insufficient-
        material draws; baring the king is decisive instead.  The only forced
        draw kept here is the ply cap, purely to guarantee termination."""
        return state.ply >= self.PLY_CAP

    # ---- bare-king rule -----------------------------------------------------
    def _lone_king(self, board, player) -> bool:
        """True if ``player`` has only their king left on the board."""
        return not any(pl == player and t != "K" for (pl, t) in board.values())

    def _bare_result(self, state):
        """Resolve the baring rule: ``None`` (nobody bared), ``"draw"`` (both
        kings bare -- unreachable in play, kept for hand-built positions), or
        the winning player index.  Unlike Shatranj there is NO "bare back on
        the very next move -> draw" exception: the FIRST player to bare the
        opponent wins outright."""
        lone_w = self._lone_king(state.board, WHITE)
        lone_b = self._lone_king(state.board, BLACK)
        if lone_w and lone_b:
            return "draw"
        if lone_w:
            return BLACK
        if lone_b:
            return WHITE
        return None

    # ---- terminal / result --------------------------------------------------
    def legal_moves(self, state) -> list:
        if self._bare_result(state) is not None:
            return []
        return super().legal_moves(state)

    def is_terminal(self, state) -> bool:
        if self._bare_result(state) is not None:
            return True
        return super().is_terminal(state)

    def returns(self, state) -> list:
        bare = self._bare_result(state)
        if bare == "draw":
            return [0.0, 0.0]
        if bare is not None:
            return [1.0, -1.0] if bare == WHITE else [-1.0, 1.0]
        if self._draw(state):
            return [0.0, 0.0]
        if len(self._legal(state)) == 0:
            mover = state.to_move
            if self.in_check(state.board, mover):
                # Checkmate: the side to move loses.
                return [-1.0, 1.0] if mover == WHITE else [1.0, -1.0]
            # Stalemate: a WIN for the STALEMATED player (the side to move) --
            # the opposite of Shatranj.
            return [1.0, -1.0] if mover == WHITE else [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            bare = self._bare_result(state)
            if bare == "draw":
                spec["caption"] = "Draw (both kings bared)"
            elif bare is not None:
                spec["caption"] = f"{names[bare]} wins (bare king)"
            elif self._draw(state):
                spec["caption"] = "Draw (ply cap)"
            elif len(self._legal(state)) == 0:
                mover = state.to_move
                if self.in_check(state.board, mover):
                    spec["caption"] = f"{names[1 - mover]} wins (checkmate)"
                else:
                    spec["caption"] = (f"{names[mover]} wins "
                                       "(stalemated player wins in Chaturanga)")
        return spec
