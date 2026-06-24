"""Extinction Chess -- "Survival of the Species" (R. Wayne Schmittberger, 1985).

Standard chess board, setup, piece movement, en passant, pawn double-step and
castling -- but the WIN CONDITION is completely different and the king is NOT
royal:

* You WIN the instant any ONE *type* of the opponent's pieces becomes EXTINCT
  (count drops to zero).  The six types are King, Queen, Rook, Bishop, Knight,
  Pawn.  So capturing the opponent's last knight wins; capturing their last
  bishop wins; reducing their kings to zero wins; capturing all eight pawns
  wins; and so on.
* The king is just an ordinary piece.  There is NO check, NO checkmate, NO
  stalemate.  Moving your king "into check" (onto an attacked square, or leaving
  it attacked) is perfectly LEGAL -- the game only ends on an extinction (or a
  draw rule for termination).

How the standard ``agp.chesslike`` royalty is DISABLED here
-----------------------------------------------------------
``ChessLike`` enforces royalty in exactly two places, both overridden below:

1. ``_legal()`` filters every pseudo-legal move through
   ``in_check(board_after, side_to_move)``.  We override ``_legal`` to return the
   *pseudo-legal* moves unfiltered (plus the castles), so a move that leaves
   one's own king attacked is legal.
2. ``StandardCastling.moves()`` forbids castling out of / through / into check
   via ``in_check`` and ``attacked``.  Per the published rules castling IS legal
   when in / through check (only the unmoved-king-and-rook and empty-between
   requirements remain), so we use ``NoCheckCastling`` which drops those two
   filters but keeps the rest.

How the EXTINCTION win is wired
-------------------------------
"Win as event": ``apply_move`` calls the base mover, then checks whether the
move rendered any of the *mover's-opponent's* piece types extinct (and, only via
a last-pawn promotion, possibly the mover's own).  The result is stored on a
``winner`` field of the state (``ECState``); ``is_terminal`` / ``returns`` /
``legal_moves`` read that field.  If BOTH sides go extinct on the same move (only
possible by a capturing pawn-promotion, e.g. ``bxc8=Q`` emptying White's pawns
and Black's bishops at once) the MOVER is ruled the winner, per the rules.

Promotion
---------
A pawn promotes on the last rank to Q, R, B, N **or K** (the king is not
special).  Promotion is mandatory on the last rank (a pawn cannot stay a pawn
there).  Promoting your last pawn IS legal even though it empties your own pawns
-- it is only a self-loss if it does not simultaneously win, and the engine
evaluates the resulting extinctions with the mover-wins tiebreak.

Draws / termination
-------------------
Standard insufficient-material is meaningless here (a lone king already makes
several types extinct), so it is DISABLED.  The fifty-move rule, threefold
repetition and a hard ply cap remain purely to guarantee termination; a draw is
declared 0/0.  (These are coarse relative to a real extinction-chess engine but
are correct enough to terminate every random game.)

White = player 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.chesslike import (
    ChessLike, CState, StandardPawn, PromotionRules, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, cell,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

# The six piece types; one of them dropping to zero (for a side) is extinction.
TYPES = ("K", "Q", "R", "B", "N", "P")


@dataclass
class ECState(CState):
    # The winning player once an extinction has occurred, else None.  "Win as
    # event": set inside apply_move, never inferred from a hand-built board.
    winner: int = None


class NoCheckCastling(StandardCastling):
    """Castling as in Extinction Chess: legal even when in / through / into
    check.  Only the orthodox requirements remain -- king and rook on their home
    squares with their rights intact, and the squares between them empty."""

    def moves(self, core, state):
        player = state.to_move
        for flag in self.BY_COLOR[player]:
            if flag not in state.castling:
                continue
            kfrom, kto, rfrom, rto, empties, path = self.CASTLES[flag]
            if state.board.get(kfrom) != (player, "K") or state.board.get(rfrom) != (player, "R"):
                continue
            if any(sq in state.board for sq in empties):
                continue
            yield kfrom, kto


class ExtinctionPromotion(PromotionRules):
    """Mandatory last-rank promotion to Q / R / B / N or K (king is not special
    in Extinction Chess).  No early/optional promotion."""

    TARGETS = ("Q", "R", "B", "N", "K")

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        last = (to[1] == core.HEIGHT - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK)
        return list(self.TARGETS) if last else [None]


class ExtinctionChess(ChessLike):
    uid = "extinction_chess"
    name = "Extinction Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = ExtinctionPromotion()
    CASTLING = NoCheckCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # ---- royalty DISABLED: no king-safety filter on move generation --------
    def _legal(self, state):
        """All pseudo-legal moves are legal (the king is not royal), plus the
        castles.  This is the only change to move generation; everything about
        *how* pieces move is identical to standard chess."""
        moves = list(self._pseudo(state))
        moves.extend(self.CASTLING.moves(self, state))
        return moves

    # ---- extinction bookkeeping --------------------------------------------
    @staticmethod
    def _present_types(board, player):
        """The set of piece types ``player`` still has on the board."""
        return {t for (_, (pl, t)) in board.items() if pl == player}

    def _extinct_for(self, board, player) -> bool:
        """True if ``player`` has lost (any one of its six types is extinct)."""
        return len(self._present_types(board, player)) < len(TYPES)

    # ---- state with winner --------------------------------------------------
    def initial_state(self, options=None, rng=None):
        board = self.setup_board()
        rights = self.CASTLING.initial_rights()
        st = ECState(board=board, to_move=WHITE, castling=rights, ep=None)
        st.reps = {self._poskey_state(st): 1}
        return st

    def apply_move(self, state, move, rng=None):
        mover = state.to_move
        ns = super().apply_move(state, move, rng)
        # Determine the winner from the resulting board.  Normally only the
        # opponent of the mover can have been reduced; a capturing pawn-promotion
        # can empty the mover's OWN pawns simultaneously -- in that mutual case
        # the MOVER wins (per the rules).
        opp_extinct = self._extinct_for(ns.board, 1 - mover)
        self_extinct = self._extinct_for(ns.board, mover)
        winner = None
        if opp_extinct or self_extinct:
            winner = mover if opp_extinct else (1 - mover)
        return ECState(board=ns.board, to_move=ns.to_move, castling=ns.castling,
                       ep=ns.ep, halfmove=ns.halfmove, ply=ns.ply, reps=ns.reps,
                       winner=winner)

    # ---- terminal / result --------------------------------------------------
    def _insufficient(self, board) -> bool:
        # Material-based draw is meaningless under extinction (a lone king is
        # already several extinctions); disabled.
        return False

    def legal_moves(self, state) -> list:
        if getattr(state, "winner", None) is not None:
            return []
        return super().legal_moves(state)

    def is_terminal(self, state) -> bool:
        if getattr(state, "winner", None) is not None:
            return True
        if self._draw(state):
            return True
        # No royalty: a side with no moves simply... has no moves.  In practice a
        # side always has a king-step or other move unless it has been driven to
        # extinction first, but guard anyway: no legal moves => terminal (draw).
        return not self._legal(state)

    def returns(self, state) -> list:
        w = getattr(state, "winner", None)
        if w is not None:
            return [1.0, -1.0] if w == WHITE else [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- (de)serialize ------------------------------------------------------
    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["winner"] = getattr(state, "winner", None)
        return d

    def deserialize(self, d: dict):
        base = super().deserialize(d)
        return ECState(board=base.board, to_move=base.to_move,
                       castling=base.castling, ep=base.ep,
                       halfmove=base.halfmove, ply=base.ply, reps=base.reps,
                       winner=d.get("winner"))

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "White", BLACK: "Black"}
        w = getattr(state, "winner", None)
        if w is not None:
            # Name the extinct type(s) of the loser for a helpful caption.
            loser = 1 - w
            present = self._present_types(state.board, loser)
            extinct = [t for t in TYPES if t not in present]
            label = "/".join(extinct) if extinct else "?"
            spec["caption"] = f"{names[w]} wins (extinction: {names[loser]} {label})"
        elif self._draw(state):
            spec["caption"] = "Draw"
        else:
            spec["caption"] = f"{names[state.to_move]} to move"
        return spec
