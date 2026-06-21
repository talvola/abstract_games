"""Shatranj -- medieval Persian/Arabic chess, the ancestor of modern chess (8x8).

Built on the shared chess-like core (``agp.chesslike``), mirroring ``games/chess``
and ``games/grand_chess`` for the strategy plug-ins.  The pieces are the historic
ones:

* **Shah** (King, ``K``) -- moves like a chess king. There is NO castling.
* **Firzan / Ferz** (``F``) -- the "counsellor", ancestor of the queen: it moves
  exactly ONE square diagonally (a one-step diagonal leaper).
* **Alfil** (Elephant, ``A``) -- ancestor of the bishop: it LEAPS exactly two
  squares diagonally, jumping over whatever sits between (a (2,2) leaper).
* **Rukh** (Rook, ``R``) -- moves like a chess rook.
* **Asp / Faras** (Knight, ``N``) -- moves like a chess knight.
* **Baidaq** (Pawn, ``P``) -- moves one square straight forward (NO double step,
  no en passant), captures one square diagonally forward, and promotes ONLY to a
  Firzan on reaching the last rank.

Win conditions differ from modern chess and are what make Shatranj distinctive:

* **Checkmate** -- as in chess.
* **Stalemate is a WIN for the side that delivers it** (the stalemated player
  loses), NOT a draw.
* **Baring the king** -- reducing the opponent to a lone king wins, UNLESS on the
  immediately following move the bared player can bare the opponent's king in
  return, in which case it is a draw.

A ply cap guarantees termination.  White = player 0.  See ``rules.md`` for the
exact ruleset choices made by this package.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, NoCastling,
    ORTHO, KNIGHT, WHITE, BLACK,
)

# Firzan: one square diagonally (a one-step diagonal leaper).
FERZ = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
# Alfil: exactly two squares diagonally, leaping over anything in between.
ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]

BACK_RANK = ["R", "N", "A", "F", "K", "A", "N", "R"]


class Shatranj(ChessLike):
    uid = "shatranj"
    name = "Shatranj"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []),        # Rukh -- rook
        "N": ([], KNIGHT),       # Asp / Faras -- knight
        "A": ([], ALFIL),        # Alfil -- (2,2) leaper (elephant)
        "F": ([], FERZ),         # Firzan / Ferz -- one-step diagonal leaper
        "K": ([], ORTHO + FERZ), # Shah -- king (one step any direction)
    }
    # Mating material: anything that is not a "minor" lone-piece draw.  In
    # Shatranj baring the king is itself a win, so the insufficient-material draw
    # is switched off entirely (see ``_draw``); HEAVY is left broad for clarity.
    HEAVY = ("P", "R", "F", "A", "N")
    PAWN = StandardPawn(white_start=1, black_start=6, double=False)
    PROMOTION = LastRankPromotion(("F",))   # Baidaq promotes only to a Firzan
    CASTLING = NoCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # ---- draws --------------------------------------------------------------
    def _draw(self, state) -> bool:
        """Shatranj had no fifty-move / threefold-repetition / insufficient-
        material draws; baring the king is decisive instead.  The only forced
        draw kept here is the ply cap, purely to guarantee termination.  (The
        double-baring draw is handled in :meth:`_bare_result`.)"""
        return state.ply >= self.PLY_CAP

    # ---- bare-king rule -----------------------------------------------------
    def _lone_king(self, board, player) -> bool:
        """True if ``player`` has only their king left on the board."""
        return not any(pl == player and t != "K" for (pl, t) in board.values())

    def _can_bare_back(self, state, victim) -> bool:
        """``victim`` (the side to move, holding a lone king) can, on this very
        move, capture the opponent's last non-king piece -- leaving the opponent
        also with a lone king.  Such a reply turns a baring into a draw."""
        enemy = 1 - victim
        for frm, to in self._legal(state):
            nb = self._apply_board(state.board, frm, to, state.ep)
            if self._lone_king(nb, enemy):
                return True
        return False

    def _bare_result(self, state):
        """Resolve the baring rule for ``state``.

        Returns one of ``None`` (no baring decision), ``"draw"`` (both kings bare,
        or the bared side can bare back), or a winning player index.

        After any move, the side now to move is the only one that can be newly
        bare (you never capture your own pieces), so it is always the side to
        move whose lone-king status we test.
        """
        lone_w = self._lone_king(state.board, WHITE)
        lone_b = self._lone_king(state.board, BLACK)
        if lone_w and lone_b:
            return "draw"               # both reduced to bare kings
        if not (lone_w or lone_b):
            return None
        victim = WHITE if lone_w else BLACK
        # The bared side gets one chance to bare the opponent back -> draw.
        if self._can_bare_back(state, victim):
            return "draw"
        return 1 - victim               # the barer wins

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
        # No legal moves and not bared: checkmate OR stalemate.  In Shatranj BOTH
        # are losses for the side to move (stalemate is a win for the opponent).
        if len(self._legal(state)) == 0:
            return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]
        return [0.0, 0.0]

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            bare = self._bare_result(state)
            if bare == "draw" and (self._lone_king(state.board, WHITE)
                                   and self._lone_king(state.board, BLACK)):
                spec["caption"] = "Draw (both kings bared)"
            elif bare == "draw":
                spec["caption"] = "Draw (bared, but bares back)"
            elif bare is not None:
                spec["caption"] = f"{names[bare]} wins (bare king)"
            elif self._draw(state):
                spec["caption"] = "Draw (ply cap)"
            elif len(self._legal(state)) == 0:
                loser = state.to_move
                how = "checkmate" if self.in_check(state.board, loser) else "stalemate"
                spec["caption"] = f"{names[1 - loser]} wins ({how})"
        return spec
