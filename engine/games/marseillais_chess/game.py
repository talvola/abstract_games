"""Marseillais Chess — the multi-move variant where each player makes TWO moves
per turn (Marseille, 1920s).

This package implements the **Balanced Marseillais** ruleset (Robert Bruce, 1963;
endorsed by Fischer and now the standard tournament version): White's very FIRST
turn is a SINGLE move, and every turn thereafter is two moves. The move order is

    White · Black Black · White White · Black Black · …

so no side ever enjoys the "double tempo" of an unanswered pair. (The classic
unbalanced version — White also opens with two moves — is documented in rules.md
as the historical alternative; balancing removes the near-winning 1-move White
opening trap.)

Built on the shared chess-like core (:class:`agp.chesslike.ChessLike`): board
model, piece movement, attack/check detection, castling, promotion, insufficient
material, serialize/render are all inherited. Only the TURN STRUCTURE and the
Marseillais CHECK RULES are new here.

The multi-move plumbing follows the platform's "one turn = several apply_move
calls" pattern (as in Backgammon): ``current_player`` / ``to_move`` stay the same
across the sub-moves of a turn and flip only when the turn ends, so the generic
UI and bot handle it with no changes.

MARSEILLAIS CHECK RULES (Wikipedia "Marseillais chess", verified):
  * You may NEVER leave your own king in check after EITHER of your sub-moves
    (you cannot move the king into check on move 1 and out on move 2). Enforced by
    king-safety filtering EVERY sub-move in ``legal_moves``.
  * Giving check ENDS your turn immediately: if your first move gives check you
    forfeit your second move. Handled in ``apply_move``.
  * If you are in check at the START of your turn you must escape it on your FIRST
    move (a natural consequence of the king-safety filter). No first move that
    leaves your king safe ⇒ checkmate ⇒ loss.
  * Checkmate = in check with no legal (king-safe) move; stalemate = no legal move,
    not in check ⇒ draw. Mate is ORDINARY (in-check-and-cannot-escape); because a
    checking move ends the turn, the opponent can never actually capture the king,
    so the "capture-the-king-in-two-moves" idea is not how mate works here.

EN PASSANT (Marseillais nuances, per Wikipedia): a pawn that double-stepped on
EITHER sub-move of a turn is en-passant-capturable on the opponent's NEXT turn,
and the capture must be made on the FIRST sub-move of that turn. We therefore
track the double-step targets created during a turn (``ep_pending``) and hand them
to the opponent (``ep_here``) when the turn flips; ``ep_here`` is cleared after the
first sub-move. DOCUMENTED SIMPLIFICATION: because ep must be on the first move,
at most one pawn can be captured en passant per turn (the rare "capture BOTH
double-stepped pawns in one turn" case is not supported).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.chesslike import (
    ChessLike, CState, cell, _FILES,
    StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


@dataclass
class MState(CState):
    """Chess state + Marseillais turn/ep bookkeeping.

    ``moves_left``  — sub-moves remaining in the current turn.
    ``ep_here``     — ep entries ((target),(captured)) the side to move may capture
                      on its FIRST sub-move (created by the opponent last turn).
    ``ep_pending``  — double-step ep entries the side to move has created so far
                      this turn (handed to the opponent when the turn flips).
    The base ``ep`` field is unused (kept None); Marseillais needs a list.
    """

    moves_left: int = 2
    ep_here: tuple = ()
    ep_pending: tuple = ()


def _entry(x):
    return ((x[0], x[1]), (x[2], x[3]))


class MarseillaisChess(ChessLike):
    uid = "marseillais_chess"
    name = "Marseillais Chess"

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

    # ---- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> MState:
        board = self.setup_board()
        st = MState(board=board, to_move=WHITE,
                    castling=self.CASTLING.initial_rights(), ep=None,
                    moves_left=1, ep_here=(), ep_pending=())   # Balanced: W opens with 1
        st.reps = {self._poskey_state(st): 1}
        return st

    def current_player(self, state) -> int:
        return state.to_move

    # ---- position key (include the turn state) ------------------------------
    def _poskey_state(self, state) -> str:
        base = self._poskey(state.board, state.to_move, state.castling, None, None)
        eph = ";".join(sorted(f"{t[0][0]},{t[0][1]}" for t in state.ep_here))
        return f"{base}#ml{state.moves_left}#ep{eph}"

    # ---- en-passant helpers -------------------------------------------------
    def _ep_capture_entry(self, state, move):
        """If ``move`` is an en-passant capture of one of ``state.ep_here``,
        return that entry ((target),(captured)); else None."""
        if "@" in move or ">" not in move:
            return None
        raw = move.split("=")[0]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        occ = state.board.get(frm)
        if occ is None or occ[1] != "P" or to in state.board:
            return None
        for e in state.ep_here:
            if e[0] == to:
                return e
        return None

    # ---- move generation ----------------------------------------------------
    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        # Normal (non-ep) moves + castling, each filtered so the mover's king is
        # safe after the sub-move. ep is handled separately below.
        tmp = CState(board=state.board, to_move=state.to_move,
                     castling=state.castling, ep=None)
        out = []
        for f, t in self._legal(tmp):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if state.board[f][1] == "P":
                for ch in self.PROMOTION.options(self, state, f, t):
                    out.append(base if ch is None else base + "=" + ch)
            else:
                out.append(base)
        # En-passant captures — allowed only on the first sub-move (ep_here is
        # non-empty only then). Also king-safety filtered.
        pl = state.to_move
        fwd = 1 if pl == WHITE else -1
        for target, _cap in state.ep_here:
            tc, tr = target
            for dc in (-1, 1):
                frm = (tc - dc, tr - fwd)
                if state.board.get(frm) != (pl, "P"):
                    continue
                nb = self._apply_board(state.board, frm, target, (target, _cap))
                if not self.in_check(nb, pl):
                    out.append(f"{frm[0]},{frm[1]}>{tc},{tr}")
        return out

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None) -> MState:
        pl = state.to_move
        ep_cap = self._ep_capture_entry(state, move)
        # Let the shared core do the board mechanics (move/capture/castle/promo/
        # ep-capture/double-step-ep/halfmove/ply). ep_cap tells it which pawn an
        # en-passant capture removes; ns.ep comes back as the double-step target
        # this move created (or None).
        tmp = CState(board=state.board, to_move=pl, castling=state.castling,
                     ep=ep_cap, halfmove=state.halfmove, ply=state.ply, reps={})
        ns = super().apply_move(tmp, move)
        created = ns.ep

        gave_check = self.in_check(ns.board, 1 - pl)
        if gave_check:                       # giving check forfeits the rest of the turn
            nxt, ml = 1 - pl, 2
        elif state.moves_left - 1 > 0:       # keep moving (same player)
            nxt, ml = pl, state.moves_left - 1
        else:                                # budget spent → hand over
            nxt, ml = 1 - pl, 2

        pending = list(state.ep_pending)
        if created is not None:
            pending.append(created)
        if nxt == pl:
            ep_here, ep_pending = (), tuple(pending)   # no ep on your 2nd move
        else:
            ep_here, ep_pending = tuple(pending), ()   # opponent may ep next turn

        new = MState(board=ns.board, to_move=nxt, castling=ns.castling, ep=None,
                     halfmove=ns.halfmove, ply=ns.ply, reps=dict(state.reps),
                     moves_left=ml, ep_here=ep_here, ep_pending=ep_pending)
        key = self._poskey_state(new)
        new.reps[key] = new.reps.get(key, 0) + 1
        return new

    # ---- terminal / returns -------------------------------------------------
    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        return not self.legal_moves(state)

    # returns() is inherited: no legal move + in check ⇒ loss for side to move
    # (ordinary checkmate); no legal move + not in check ⇒ draw (stalemate).

    # ---- (de)serialize ------------------------------------------------------
    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["moves_left"] = state.moves_left
        d["ep_here"] = [[e[0][0], e[0][1], e[1][0], e[1][1]] for e in state.ep_here]
        d["ep_pending"] = [[e[0][0], e[0][1], e[1][0], e[1][1]] for e in state.ep_pending]
        return d

    def deserialize(self, d: dict) -> MState:
        base = super().deserialize(d)
        return MState(board=base.board, to_move=base.to_move,
                      castling=base.castling, ep=None,
                      halfmove=base.halfmove, ply=base.ply, reps=base.reps,
                      moves_left=d.get("moves_left", 2),
                      ep_here=tuple(_entry(x) for x in d.get("ep_here", [])),
                      ep_pending=tuple(_entry(x) for x in d.get("ep_pending", [])))

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if self._ep_capture_entry(state, move) is not None:
            raw = move.split("=")[0]
            fs, ts = raw.split(">")
            frm, to = cell(fs), cell(ts)
            t = state.board[frm][1]
            alg = lambda c: f"{_FILES[c[0]]}{c[1] + 1}"  # noqa: E731
            return f"{t}{alg(frm)}x{alg(to)} e.p."
        return super().describe_move(state, move)

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state)
        if not self.is_terminal(state):
            n = state.moves_left
            spec["caption"] += f" · {n} move{'s' if n != 1 else ''} left this turn"
        return spec
