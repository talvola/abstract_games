"""Monster Chess -- the asymmetric double-move variant.

White has only a King (e1) and four pawns (c2, d2, e2, f2), but makes TWO moves
per turn; Black has the full standard army and makes ONE move per turn. The game
is decided by *capturing the enemy king* (Wikipedia "Monster chess").

Built on the shared ``agp.chesslike`` core (board model, pseudo-move generation,
attack tests, promotion, en passant, serialize/render). What Monster Chess adds:

* **Multi-move turns.** State carries ``moves_left``; White stays to move for a
  second sub-move (``moves_left`` 2 -> 1), exactly like Backgammon's per-die turn.
  The generic UI/bot handle it (``current_player`` simply keeps returning White).
* **Win by king capture** (event, not abstract checkmate). ``apply_move`` sets a
  ``winner`` the instant a move lands on the enemy king; ``returns``/``is_terminal``
  read it.
* **Asymmetric king safety (the crux).** Because Black replies only AFTER White's
  full two-move turn, "safe" is redefined:
  - **White** moves with NO self-check filter -- White may walk its king through
    (or into) an attacked square on the first move and out on the second, and may
    freely sacrifice to grab the Black king. White's moves are all pseudo-legal.
  - **Black** may not leave its king where White could capture it within White's
    next TWO moves. Each Black move is filtered by ``_white_can_capture_bk_in_2``
    (White move1 lands on the Black king, or White move1 then move2 does). A Black
    move that itself captures the White king is always legal (it wins at once).
  Thus "checkmate" is implicit: Black is lost exactly when it has no move that
  keeps its king out of White's two-move reach (and can't grab White's king).

Castling is omitted for both sides (White has no rook; Black castling under the
two-move-check semantics is left out for simplicity -- documented in rules.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, NoCastling, cell,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]
NAMES = {WHITE: "White", BLACK: "Black"}


@dataclass
class MState(CState):
    """Chess state + the double-move budget and the king-capture result."""
    moves_left: int = 2
    winner: Optional[int] = None


class MonsterChess(ChessLike):
    uid = "monster_chess"
    name = "Monster Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 400
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = NoCastling()

    # ---- setup --------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        b[(4, 0)] = (WHITE, "K")            # King on e1
        for c in (2, 3, 4, 5):              # pawns on c2, d2, e2, f2
            b[(c, 1)] = (WHITE, "P")
        return b

    def initial_state(self, options=None, rng=None):
        st = MState(board=self.setup_board(), to_move=WHITE, castling=frozenset(),
                    ep=None, moves_left=2, winner=None)
        st.reps = {self._poskey_state(st): 1}
        return st

    def current_player(self, state) -> int:
        return state.to_move

    # ---- king-capture detection --------------------------------------------
    def _captures_king(self, state, move) -> bool:
        """True if ``move`` lands on the enemy king (an en-passant target is a
        pawn, never a king, so only the plain destination matters)."""
        raw = move.split("=")[0]
        _, ts = raw.split(">")
        occ = state.board.get(cell(ts))
        return occ is not None and occ[1] == "K"

    # ---- move generation ----------------------------------------------------
    def _pawn_variants(self, state, f, t) -> list:
        base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
        if state.board[f][1] != "P":
            return [base]
        out = []
        for ch in self.PROMOTION.options(self, state, f, t):
            out.append(base if ch is None else base + "=" + ch)
        return out

    def _white_moves(self, state) -> list:
        """Every pseudo-legal White move -- NO self-check filter (White may move
        its king through/into check, and may sacrifice to capture the enemy king)."""
        out = []
        for f, t in self._pseudo(state):
            out.extend(self._pawn_variants(state, f, t))
        return out

    def _white_can_capture_bk_in_2(self, board) -> bool:
        """Can White capture the Black king within its two-move turn on ``board``?

        White cares nothing for its own king here (grabbing the Black king wins
        immediately), so pure pseudo-moves are used. True if some White move lands
        on the Black king (1 move), or a White move followed by another does."""
        bk = self._king(board, BLACK)
        if bk is None:
            return False
        st1 = CState(board=board, to_move=WHITE, ep=None)
        for f1, t1 in self._pseudo(st1):
            if t1 == bk:
                return True
            b1 = self._apply_board(board, f1, t1, None)
            st2 = CState(board=b1, to_move=WHITE, ep=None)
            for _f2, t2 in self._pseudo(st2):
                if t2 == bk:
                    return True
        return False

    def _black_moves(self, state) -> list:
        """Pseudo-legal Black moves, filtered so the Black king is not capturable
        by White within two moves afterward. A move that captures the White king
        is always allowed (it wins on the spot)."""
        out = []
        for f, t in self._pseudo(state):
            occ = state.board.get(t)
            wins = occ is not None and occ[1] == "K"       # takes the White king
            if not wins:
                nb = self._apply_board(state.board, f, t, state.ep)
                if self._white_can_capture_bk_in_2(nb):
                    continue
            out.extend(self._pawn_variants(state, f, t))
        return out

    def _gen_moves(self, state) -> list:
        return self._white_moves(state) if state.to_move == WHITE else self._black_moves(state)

    def legal_moves(self, state) -> list:
        if state.winner is not None or self._draw(state):
            return []
        return self._gen_moves(state)

    # ---- draws / terminal ---------------------------------------------------
    def _draw(self, state) -> bool:
        return (state.ply >= self.PLY_CAP or state.halfmove >= 100
                or state.reps.get(self._poskey_state(state), 0) >= 3)

    def is_terminal(self, state) -> bool:
        if state.winner is not None or self._draw(state):
            return True
        return len(self._gen_moves(state)) == 0

    def returns(self, state) -> list:
        if state.winner is not None:
            return [1.0, -1.0] if state.winner == WHITE else [-1.0, 1.0]
        if self._draw(state):
            return [0.0, 0.0]
        if not self._gen_moves(state):        # no way to keep the king safe -> loss
            return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]
        return [0.0, 0.0]

    # The material eval is meaningless here (White is hugely down material yet the
    # two-move mechanic compensates), so give the MCTS rollout cutoff a neutral
    # eval and let the rollouts speak.
    def heuristic(self, state) -> list:
        return [0.0, 0.0]

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        mover = state.to_move
        captured_king = self._captures_king(state, move)
        ns = super().apply_move(state, move, rng)   # CState with board mutated

        if captured_king:
            return self._finish(state, ns, to_move=ns.to_move, moves_left=0,
                                ep=ns.ep, winner=mover)

        if mover == WHITE and state.moves_left == 2:
            # White plays its second move: stay White, drop an ep created by the
            # first move (it cannot carry to White's own follow-up move).
            return self._finish(state, ns, to_move=WHITE, moves_left=1,
                                ep=None, winner=None)

        # Turn ends -> hand over. White gets 2 moves, Black gets 1.
        nxt = ns.to_move
        return self._finish(state, ns, to_move=nxt,
                            moves_left=2 if nxt == WHITE else 1,
                            ep=ns.ep, winner=None)

    def _finish(self, prev, ns, to_move, moves_left, ep, winner):
        result = MState(board=ns.board, to_move=to_move, castling=ns.castling,
                        ep=ep, halfmove=ns.halfmove, ply=ns.ply, reps={},
                        moves_left=moves_left, winner=winner)
        reps = dict(prev.reps)
        key = self._poskey_state(result)
        reps[key] = reps.get(key, 0) + 1
        result.reps = reps
        return result

    # ---- (de)serialize ------------------------------------------------------
    def _poskey_state(self, state) -> str:
        return super()._poskey_state(state) + f"#ml{state.moves_left}"

    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["moves_left"] = state.moves_left
        d["winner"] = state.winner
        return d

    def deserialize(self, d):
        base = super().deserialize(d)
        return MState(board=base.board, to_move=base.to_move, castling=base.castling,
                      ep=base.ep, halfmove=base.halfmove, ply=base.ply,
                      reps=base.reps, hands=base.hands, promoted=base.promoted,
                      moves_left=d.get("moves_left", 2), winner=d.get("winner"))

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        if state.winner is not None:
            spec["caption"] = f"{NAMES[state.winner]} wins (king captured)"
        elif self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                spec["caption"] = "Draw"
            else:
                w = WHITE if ret[0] > 0 else BLACK
                spec["caption"] = f"{NAMES[w]} wins"
        elif state.to_move == WHITE:
            n = state.moves_left
            spec["caption"] = f"White to move ({n} move{'s' if n != 1 else ''} left)"
        else:
            spec["caption"] = "Black to move"
        return spec
