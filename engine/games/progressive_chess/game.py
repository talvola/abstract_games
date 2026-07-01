"""Progressive Chess -- the multi-move variant, Italian rules (Scacchi progressivi).

Built on the shared chess-like core (:mod:`agp.chesslike`): standard 8x8 board,
standard army, standard piece movement, castling, en passant and promotion are
all inherited unchanged.  What differs is the TURN STRUCTURE and the CHECK rule.

Turn structure
--------------
A "turn" is a *series* of several ordinary chess moves by the SAME player, one
more than the previous turn::

    turn 1: White  -> 1 move
    turn 2: Black  -> 2 moves
    turn 3: White  -> 3 moves
    turn 4: Black  -> 4 moves ...

so the series length of turn ``N`` is ``N``.  This is modelled exactly like the
platform's dice games (Backgammon): a turn is consumed ONE sub-move at a time.
Each ``apply_move`` plays a single chess move and keeps the SAME player to move
until the series is spent, only then flipping ``to_move``.  The generic UI/bot
need no change -- they just keep asking the same player for moves.

State carries two extra fields on top of :class:`agp.chesslike.CState`:

* ``moves_left`` -- moves still to play in the CURRENT series (starts at the
  series length, decremented per sub-move; the sub-move with ``moves_left == 1``
  is the LAST move of the series);
* ``turn_no``   -- the current turn/series number (so the next series length is
  known).  ``moves_left == turn_no`` iff we are on the FIRST move of a series.

Italian check rules (verified against Wikipedia "Progressive chess" and
chessvariants.com/multimove.dir/progressive.html)
-------------------------------------------------
* A player may give check ONLY on the LAST move of the series.  On any earlier
  sub-move, a move that would leave the OPPONENT in check is illegal.
* A player may never leave their OWN king in check after any of their sub-moves
  (standard king safety, applied to every sub-move).
* If in check at the start of the turn, the check must be escaped on the FIRST
  move.  Because on a series of length >= 2 the first move may not give check, if
  the *only* escapes from check would deliver check, there is no legal first move
  -> that is a "progressive checkmate" and the checked side loses (this falls out
  of the generation rules automatically).
* Checkmate: the side to move is in check at the start of its series and has no
  legal first move -> loss.
* Stalemate: not in check but no legal first move -> DRAW (progressive stalemate).
* A player must play ALL moves of the series while a legal move exists.  If part
  way through the series no legal continuation exists (e.g. the only remaining
  moves would give check on a non-final move), the turn simply ENDS EARLY via a
  forced ``"pass"`` -- this is NOT a loss (only being unable to make the FIRST
  move while in check is checkmate).

Documented simplifications
--------------------------
* En passant: the platform stores the ep square created by a pawn double-step and
  makes it capturable by the opponent on their next move.  Here ep is preserved
  only when the double-step is the LAST move of a series (so the opponent may
  capture it on the first move of theirs, matching "must be captured on the first
  move"); a double-step made on a non-final sub-move does NOT leave an ep target
  (this both avoids a player en-passant-capturing their own pawn and keeps the
  common "ep only from the immediately preceding move" behaviour).
* Draws for termination use the shared 50-move (100 half-move) counter, a hard
  ply cap, and threefold repetition (position + side + series state).  Insufficient
  material is NOT auto-drawn: in progressive chess a mate can be forced with very
  little material thanks to multi-move series, so an automatic insufficient-material
  draw would be wrong.
"""

from __future__ import annotations

from dataclasses import dataclass

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, cell,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


@dataclass
class PState(CState):
    """Chess state + the progressive-turn bookkeeping."""
    moves_left: int = 1   # moves still to play in the current series
    turn_no: int = 1      # current turn/series number (series length == turn_no)


class ProgressiveChess(ChessLike):
    uid = "progressive_chess"
    name = "Progressive Chess"

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

    # ---- initial state ------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        st = PState(board=self.setup_board(), to_move=WHITE,
                    castling=self.CASTLING.initial_rights(), ep=None,
                    moves_left=1, turn_no=1)
        st.reps = {self._poskey_state(st): 1}
        return st

    # ---- progressive helpers ------------------------------------------------
    @staticmethod
    def _is_first_move(state) -> bool:
        """True iff no sub-move of the current series has been played yet."""
        return state.moves_left == state.turn_no

    def _board_after_move(self, state, frm, to, promo):
        """Exact board after playing (frm->to[=promo]) -- for check testing.

        Handles castling (rook follows), en-passant capture, and the ACTUAL
        promotion piece (which matters for whether the move gives check)."""
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)
        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        elif t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                b.pop(state.ep[1], None)
            if promo:
                t = promo
        b[to] = (pl, t)
        return b

    def _candidates(self, state) -> list:
        """Legal move-strings for the current sub-move (no ``pass``), applying the
        Italian check rules: own king never left in check; the opponent may be put
        in check only on the LAST move of the series."""
        me = state.to_move
        opp = 1 - me
        last = state.moves_left <= 1
        out = []

        def keep(nb):
            if self.in_check(nb, me):
                return False                 # never leave own king in check
            if not last and self.in_check(nb, opp):
                return False                 # no check except on the last move
            return True

        for frm, to in self._pseudo(state):
            _, t = state.board[frm]
            if t == "P":
                for ch in self.PROMOTION.options(self, state, frm, to):
                    nb = self._board_after_move(state, frm, to, ch)
                    if keep(nb):
                        base = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
                        out.append(base if ch is None else base + "=" + ch)
            else:
                nb = self._board_after_move(state, frm, to, None)
                if keep(nb):
                    out.append(f"{frm[0]},{frm[1]}>{to[0]},{to[1]}")

        for frm, to in self.CASTLING.moves(self, state):
            nb = self._board_after_move(state, frm, to, None)
            if keep(nb):
                out.append(f"{frm[0]},{frm[1]}>{to[0]},{to[1]}")
        return out

    # ---- public move / terminal API ----------------------------------------
    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        cands = self._candidates(state)
        if cands:
            return cands
        # No legal sub-move.  Mid-series -> the turn ends early (forced pass, not a
        # loss).  On the FIRST move of the series -> checkmate/stalemate (terminal).
        if self._is_first_move(state):
            return []
        return ["pass"]

    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        if self._candidates(state):
            return False
        # No sub-move available: terminal only if this is the first move of the
        # series (checkmate if in check, stalemate otherwise); mid-series just
        # ends the turn via a pass.
        return self._is_first_move(state)

    # returns() is inherited: on a terminal position it awards the loss to the
    # side to move iff that side is in check (checkmate), else a draw (stalemate /
    # draw-rule).  This is exactly the Italian scoring.

    # In progressive chess a mate can be forced with minimal material, so the
    # insufficient-material auto-draw must be disabled.
    def _insufficient(self, board) -> bool:
        return False

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        if move == "pass":
            turn_no = state.turn_no + 1
            ns = PState(board=dict(state.board), to_move=1 - pl,
                        castling=state.castling, ep=None,
                        halfmove=state.halfmove + 1, ply=state.ply + 1,
                        moves_left=turn_no, turn_no=turn_no)
            self._bump_reps(state, ns)
            return ns

        # Apply the ordinary chess move via the shared core (board, castling, ep,
        # promotion, halfmove and ply are all handled there).
        base = super().apply_move(state, move, rng)

        if state.moves_left - 1 > 0:
            # Same player continues the series.  Clear ep: a player can never
            # en-passant their own pawn, and ep is only offered on the opponent's
            # first move.
            ns = PState(board=base.board, to_move=pl, castling=base.castling,
                        ep=None, halfmove=base.halfmove, ply=base.ply,
                        moves_left=state.moves_left - 1, turn_no=state.turn_no)
        else:
            # Series spent -> flip; the new series length is the new turn number.
            turn_no = state.turn_no + 1
            ns = PState(board=base.board, to_move=1 - pl, castling=base.castling,
                        ep=base.ep, halfmove=base.halfmove, ply=base.ply,
                        moves_left=turn_no, turn_no=turn_no)
        self._bump_reps(state, ns)
        return ns

    def _bump_reps(self, prev, ns):
        reps = dict(prev.reps)
        key = self._poskey_state(ns)
        reps[key] = reps.get(key, 0) + 1
        ns.reps = reps

    # ---- keys / (de)serialize ----------------------------------------------
    def _poskey_state(self, state) -> str:
        return (super()._poskey_state(state)
                + f"#ml{state.moves_left}#tn{state.turn_no}")

    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["moves_left"] = state.moves_left
        d["turn_no"] = state.turn_no
        return d

    def deserialize(self, d: dict):
        base = super().deserialize(d)
        return PState(board=base.board, to_move=base.to_move,
                      castling=base.castling, ep=base.ep,
                      halfmove=base.halfmove, ply=base.ply, reps=base.reps,
                      hands=base.hands, promoted=base.promoted,
                      moves_left=int(d.get("moves_left", 1)),
                      turn_no=int(d.get("turn_no", 1)))

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        if not self.is_terminal(state):
            name = "White" if state.to_move == WHITE else "Black"
            chk = " — in check!" if self.in_check(state.board, state.to_move) else ""
            spec["caption"] = (
                f"{name} to move · turn {state.turn_no} · "
                f"move {state.turn_no - state.moves_left + 1} of {state.turn_no}{chk}"
            )
        return spec
