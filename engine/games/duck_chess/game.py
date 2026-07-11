"""Duck Chess (Tim Paulden, 2016) -- standard chess plus a shared rubber duck.

A turn is two sub-moves by the same player (the Backgammon/Monster-Chess
multi-move pattern -- ``to_move`` stays put until the turn is finished):

1. a normal chess move (``"fc,fr>tc,tr"`` + optional ``"=X"`` promotion), then
2. **the duck MUST be moved** to any empty square *different* from where it
   stands (single-cell move ``"c,r"``). The duck starts off the board; the
   first placement (after White's first chess move) may pick any empty square.

The duck is an absolute blocker: no piece may land on or slide through its
square (knights jump over it as they jump over anything). There is NO check or
checkmate -- kings may move into or stay in attack, and the game is won by
**capturing the enemy king** (the game ends at once; no duck move follows).
Castling needs only unmoved king+rook and empty in-between squares (the duck
counts as an occupant); castling out of / through / into "check" is legal.

Stalemate ("fowling", per the designer's rules at duckchess.com and
Fairy-Stockfish ``stalemateValue = VALUE_MATE``): a player to move with no
possible chess move at all **wins** immediately.

Implementation notes:

* The duck lives OUTSIDE ``state.board`` (in ``DState.duck``). Move generation
  runs the shared pseudo-legal generator on a temp board with the duck
  inserted as a piece of the *moving* player (type ``"D"``, no moves) -- own
  pieces can't land on it, sliders stop at it, leapers skip it, pawns are
  blocked by it, and it can never be captured. If the duck sits on the
  en-passant target square, the e.p. capture is disabled.
* No self-check filter anywhere: every pseudo-legal move is legal.
* Anchored move-for-move against Fairy-Stockfish's ``duck`` variant (pyffish);
  see ``_diff_pyffish.py`` (one-time, not part of the stdlib selftest).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, StandardCastling, cell,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, _FILES,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]
NAMES = {WHITE: "White", BLACK: "Black"}
DUCK_FILL, DUCK_STROKE = "#f2c94c", "#6b4a00"


@dataclass
class DState(CState):
    """Chess state + the duck square, the pending-duck flag and the result."""
    duck: Optional[tuple] = None      # (c, r), or None before the first placement
    need_duck: bool = False           # True = the mover still owes the duck move
    winner: Optional[int] = None


class DuckCastling(StandardCastling):
    """Orthodox castling geometry, but with every check-related restriction
    removed (Duck Chess has no check): only unmoved king+rook and empty
    in-between squares are required. Called on the duck-inserted temp board,
    so a duck on any in-between square blocks the castle by occupancy."""

    def moves(self, core, state):
        player = state.to_move
        for flag in self.BY_COLOR[player]:
            if flag not in state.castling:
                continue
            kfrom, kto, rfrom, rto, empties, _path = self.CASTLES[flag]
            if state.board.get(kfrom) != (player, "K") or state.board.get(rfrom) != (player, "R"):
                continue
            if any(sq in state.board for sq in empties):
                continue
            yield kfrom, kto


class DuckChess(ChessLike):
    WIDTH = HEIGHT = 8
    PLY_CAP = 600                      # 2 plies per turn -> 300 full turns
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
        "D": ([], []),                 # the duck: present on temp boards, never moves
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = DuckCastling()

    # ---- setup --------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    def initial_state(self, options=None, rng=None):
        st = DState(board=self.setup_board(), to_move=WHITE,
                    castling=frozenset("KQkq"), ep=None,
                    duck=None, need_duck=False, winner=None)
        st.reps = {self._poskey_state(st): 1}
        return st

    def current_player(self, state) -> int:
        return state.to_move

    # ---- move generation ----------------------------------------------------
    def _gen_state(self, state) -> CState:
        """A throwaway state whose board contains the duck as an unmovable
        piece of the side to move (so it blocks and can't be captured); e.p.
        is cancelled if the duck occupies the e.p. target square."""
        b = dict(state.board)
        ep = state.ep
        if state.duck is not None:
            b[state.duck] = (state.to_move, "D")
            if ep is not None and ep[0] == state.duck:
                ep = None
        return CState(board=b, to_move=state.to_move,
                      castling=state.castling, ep=ep)

    def _chess_moves(self, state) -> list:
        """Every pseudo-legal chess move -- Duck Chess has no self-check filter."""
        gs = self._gen_state(state)
        out = []
        for f, t in self._pseudo(gs):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if gs.board[f][1] == "P":
                for ch in self.PROMOTION.options(self, gs, f, t):
                    out.append(base if ch is None else base + "=" + ch)
            else:
                out.append(base)
        for f, t in self.CASTLING.moves(self, gs):
            out.append(f"{f[0]},{f[1]}>{t[0]},{t[1]}")
        return out

    def _duck_moves(self, state) -> list:
        """The mandatory duck relocation: any empty square other than the
        duck's current one. Always non-empty (<=33 occupants on 64 squares)."""
        out = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                if (c, r) not in state.board and (c, r) != state.duck:
                    out.append(f"{c},{r}")
        return out

    def legal_moves(self, state) -> list:
        if state.winner is not None or self._draw(state):
            return []
        return self._duck_moves(state) if state.need_duck else self._chess_moves(state)

    # ---- draws / terminal ---------------------------------------------------
    def _draw(self, state) -> bool:
        # No insufficient-material rule: with king capture and no check, even
        # bare-kings positions are decided by the clock rules below.
        return (state.halfmove >= 100 or state.ply >= self.PLY_CAP
                or state.reps.get(self._poskey_state(state), 0) >= 3)

    def _fowled(self, state) -> bool:
        """Stalemate = the side to move (chess phase) has no move at all -> it WINS."""
        return not state.need_duck and not self._chess_moves(state)

    def is_terminal(self, state) -> bool:
        if state.winner is not None or self._draw(state):
            return True
        return False if state.need_duck else self._fowled(state)

    def returns(self, state) -> list:
        if state.winner is not None:
            return [1.0, -1.0] if state.winner == WHITE else [-1.0, 1.0]
        if self._draw(state):
            return [0.0, 0.0]
        if self._fowled(state):        # the stalemated ("fowled") player wins
            return [1.0, -1.0] if state.to_move == WHITE else [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- apply --------------------------------------------------------------
    def _captures_king(self, state, move) -> bool:
        raw = move.split("=")[0]
        _, ts = raw.split(">")
        occ = state.board.get(cell(ts))
        return occ is not None and occ[1] == "K"

    def apply_move(self, state, move, rng=None):
        if state.need_duck:                    # sub-move 2: relocate the duck
            return self._finish(
                state, board=state.board, to_move=1 - state.to_move,
                castling=state.castling, ep=state.ep, halfmove=state.halfmove,
                ply=state.ply + 1, duck=cell(move), need_duck=False, winner=None)

        # sub-move 1: the chess move
        mover = state.to_move
        wins = self._captures_king(state, move)
        ns = super().apply_move(state, move, rng)     # plain CState bookkeeping
        if wins:                              # king captured: game over at once
            return self._finish(
                state, board=ns.board, to_move=1 - mover, castling=ns.castling,
                ep=None, halfmove=ns.halfmove, ply=ns.ply,
                duck=state.duck, need_duck=False, winner=mover)
        return self._finish(                  # same player still owes the duck
            state, board=ns.board, to_move=mover, castling=ns.castling,
            ep=ns.ep, halfmove=ns.halfmove, ply=ns.ply,
            duck=state.duck, need_duck=True, winner=None)

    def _finish(self, prev, **kw):
        result = DState(reps={}, **kw)
        reps = dict(prev.reps)
        key = self._poskey_state(result)
        reps[key] = reps.get(key, 0) + 1
        result.reps = reps
        return result

    # ---- (de)serialize ------------------------------------------------------
    def _poskey_state(self, state) -> str:
        return (super()._poskey_state(state)
                + f"#duck{state.duck}#{int(state.need_duck)}")

    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["duck"] = f"{state.duck[0]},{state.duck[1]}" if state.duck else None
        d["need_duck"] = state.need_duck
        d["winner"] = state.winner
        return d

    def deserialize(self, d):
        base = super().deserialize(d)
        return DState(board=base.board, to_move=base.to_move,
                      castling=base.castling, ep=base.ep,
                      halfmove=base.halfmove, ply=base.ply, reps=base.reps,
                      duck=cell(d["duck"]) if d.get("duck") else None,
                      need_duck=bool(d.get("need_duck", False)),
                      winner=d.get("winner"))

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if state.need_duck:
            c, r = cell(move)
            return f"duck→{_FILES[c]}{r + 1}"
        return super().describe_move(state, move)

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        if state.duck is not None:
            spec["pieces"].append({
                "cell": f"{state.duck[0]},{state.duck[1]}", "owner": 0,
                "label": "D", "fill": DUCK_FILL, "stroke": DUCK_STROKE,
            })
        if state.winner is not None:
            caption = f"{NAMES[state.winner]} wins (king captured)"
        elif self._draw(state):
            caption = "Draw"
        elif self._fowled(state):
            caption = f"{NAMES[state.to_move]} wins (fowled — no legal move)"
        elif state.need_duck:
            caption = f"{NAMES[state.to_move]}: move the duck to an empty square"
        else:
            caption = f"{NAMES[state.to_move]} to move"
        spec["caption"] = caption
        return spec
