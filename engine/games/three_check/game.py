"""Three-Check Chess (8x8).

Standard chess in every way *except* the win condition: a player wins as soon as
they have given check three times (cumulative across the whole game).  Checkmate
still wins, and the ordinary chess draws (stalemate, fifty-move, threefold
repetition, insufficient material) still apply -- but a player who reaches three
checks wins immediately, even on a move that would otherwise be a draw position.

Everything about *how the pieces move* is identical to standard chess, so the
opening perft is unchanged (20 / 400 / 8902 at depths 1/2/3).  The only state
addition is a per-side check counter, which is incremented whenever a move leaves
the opponent's king in check.

White = player 0.  Built on the shared chess-like core (``agp.chesslike``),
mirroring ``games/chess`` for the standard configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

CHECKS_TO_WIN = 3       # default threshold (also the "three-check" variant value)


@dataclass
class TCState(CState):
    # checks[player] = number of times `player` has given check so far.
    checks: list = field(default_factory=lambda: [0, 0])
    # how many cumulative checks win the game (3 = classic, 5 = five-check).
    checks_to_win: int = CHECKS_TO_WIN


class ThreeCheck(ChessLike):
    uid = "three_check"
    name = "Three-Check Chess"

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

    # ---- state with check counters -----------------------------------------
    def initial_state(self, options=None, rng=None):
        board = self.setup_board()
        rights = self.CASTLING.initial_rights()
        ctw = int((options or {}).get("checks_to_win", CHECKS_TO_WIN))
        return TCState(board=board, to_move=WHITE, castling=rights, ep=None,
                       reps={self._poskey(board, WHITE, rights, None): 1},
                       checks=[0, 0], checks_to_win=ctw)

    def apply_move(self, state, move, rng=None):
        mover = state.to_move
        ns = super().apply_move(state, move, rng)
        # `ns` is a plain CState; rebuild it as a TCState carrying the counters.
        checks = list(getattr(state, "checks", [0, 0]))
        # A move "gives check" when it leaves the side now-to-move (the opponent
        # of the mover) in check.
        if self.in_check(ns.board, ns.to_move):
            checks[mover] += 1
        return TCState(board=ns.board, to_move=ns.to_move, castling=ns.castling,
                       ep=ns.ep, halfmove=ns.halfmove, ply=ns.ply, reps=ns.reps,
                       checks=checks,
                       checks_to_win=getattr(state, "checks_to_win", CHECKS_TO_WIN))

    # ---- terminal / result --------------------------------------------------
    def _three_check_winner(self, state):
        """Return the player who has reached the check threshold, or None."""
        checks = getattr(state, "checks", [0, 0])
        ctw = getattr(state, "checks_to_win", CHECKS_TO_WIN)
        for p in (WHITE, BLACK):
            if checks[p] >= ctw:
                return p
        return None

    def legal_moves(self, state) -> list:
        # A reached three-check win is terminal -> no moves (keeps the engine's
        # "non-empty legal_moves unless terminal" invariant in sync).
        if self._three_check_winner(state) is not None:
            return []
        return super().legal_moves(state)

    def is_terminal(self, state) -> bool:
        if self._three_check_winner(state) is not None:
            return True
        return super().is_terminal(state)

    def returns(self, state) -> list:
        w = self._three_check_winner(state)
        if w is not None:
            return [1.0, -1.0] if w == WHITE else [-1.0, 1.0]
        return super().returns(state)

    # ---- (de)serialize ------------------------------------------------------
    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["checks"] = list(getattr(state, "checks", [0, 0]))
        d["checks_to_win"] = getattr(state, "checks_to_win", CHECKS_TO_WIN)
        return d

    def deserialize(self, d: dict):
        base = super().deserialize(d)
        return TCState(board=base.board, to_move=base.to_move,
                       castling=base.castling, ep=base.ep,
                       halfmove=base.halfmove, ply=base.ply, reps=base.reps,
                       checks=list(d.get("checks", [0, 0])),
                       checks_to_win=int(d.get("checks_to_win", CHECKS_TO_WIN)))

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        checks = getattr(state, "checks", [0, 0])
        ctw = getattr(state, "checks_to_win", CHECKS_TO_WIN)
        tally = f"checks W:{checks[WHITE]} B:{checks[BLACK]} (to win: {ctw})"
        w = self._three_check_winner(state)
        if w is not None and not self._draw(state) and len(self._legal(state)) > 0:
            # Won by reaching the check threshold (not already a mate/draw caption).
            name = "White" if w == WHITE else "Black"
            spec["caption"] = f"{name} wins ({ctw} checks) — {tally}"
        else:
            spec["caption"] = f"{spec['caption']} — {tally}"
        return spec
