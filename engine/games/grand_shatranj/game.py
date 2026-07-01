"""Grand Shatranj (Joe Joyce, 2006), 10x10, built on the shared chess core.

An all-short-range army in the spirit of shatranj: instead of long sliders,
every piece steps or jumps at most a few squares. This is the author's primary
setup, "Grand Shatranj D" (Lightning War Machines in the corners); the "R"
setup, which swaps them for standard rooks, is documented on the source page
as an optional replacement and is not implemented here.

Pieces (per side: K, 1x J/M/H, 2x O/N/W, 10 pawns):

* King ``K`` -- royal; one step in all 8 directions.
* Jumping General ``J`` -- one step in all 8 directions, OR a jump of exactly
  2 squares orthogonally or diagonally (alfil + dabbabah + king moves).
* Minister ``M`` -- wazir (1 orthogonal) + dabbabah (2-square orthogonal jump)
  + knight.
* High Priestess ``H`` -- ferz (1 diagonal) + alfil (2-square diagonal jump)
  + knight.
* Knight ``N`` -- standard chess knight.
* Oliphant ``O`` -- a *double elephant-rider*: moves once or twice along one
  diagonal line, each leg being a 1-square step (ferz) or a 2-square jump
  (alfil). It may end 1-4 squares away but must move in a straight line, and
  (capture is by replacement) may only capture on the FINAL square -- an
  intermediate landing square must be empty, though jumped squares may be
  occupied.
* Lightning War Machine ``W`` -- the orthogonal twin of the Oliphant: one or
  two wazir-steps / dabbabah-jumps along a single orthogonal line (1-4 squares).

Reachability along a line with intermediate squares s1..s3 (target s_k):
  k=1 always; k=2 always (the jump passes over s1); k=3 iff s1 or s2 is empty;
  k=4 iff s2 is empty (jump-land-jump).  This relation is symmetric, so the
  attack test scans outward from the attacked square with the same rule.

Pawns are standard but have NO double step (hence no en passant). Promotion is
to a piece type the owner has lost: optional on the 9th rank, mandatory on the
10th. A pawn reaching the 10th with nothing to promote to stays a pawn and may
move/capture one square SIDEWAYS along the back rank ("stranded pawn"),
promoting on a later sideways move once a piece has been lost.

Win by checkmate, or by BARING the enemy king (capturing its last non-king
man) -- unless the bared side can immediately bare you back in one legal move,
in which case the game is a draw (the counter-capture is assumed). Stalemate
and the usual repetition/no-progress situations are draws.

White = player 0, moving toward higher rows.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, GrandPromotion, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]     # 2-square diagonal jumps
DABBABAH = [(2, 0), (-2, 0), (0, 2), (0, -2)]    # 2-square orthogonal jumps

# The two double-riders and the line families they move along.
RIDERS = {"O": DIAG, "W": ORTHO}


class ShatranjPawn(StandardPawn):
    """Standard pawn, no double step, plus the 'stranded pawn' sideways move:
    a pawn sitting on the final rank may step/capture one square sideways."""

    def __init__(self, white_start: int, black_start: int):
        super().__init__(white_start, black_start, double=False)

    def _last(self, core, player) -> int:
        return core.HEIGHT - 1 if player == WHITE else 0

    def pseudo(self, core, board, c, r, player, ep_target):
        yield from super().pseudo(core, board, c, r, player, ep_target)
        if r == self._last(core, player):
            for dc in (-1, 1):
                t = (c + dc, r)
                if core.on(*t):
                    occ = board.get(t)
                    if occ is None or occ[0] != player:
                        yield (c, r), t

    def attacks(self, core, board, c, r, by) -> bool:
        if super().attacks(core, board, c, r, by):
            return True
        if r == self._last(core, by):     # stranded pawns attack sideways
            return any(board.get((c + dc, r)) == (by, "P") for dc in (-1, 1))
        return False


class ShatranjPromotion(GrandPromotion):
    """Promote only to a lost piece type; optional on the 9th rank, mandatory
    on the 10th. A pawn ARRIVING on the 10th with nothing available stays a
    pawn (stranded); a stranded pawn's sideways moves offer optional promotion
    once a piece type has been lost."""

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        last = core.HEIGHT - 1 if pl == WHITE else 0
        ninth = core.HEIGHT - 2 if pl == WHITE else 1
        if to[1] == last:
            avail = self._avail(state.board, pl)
            if frm[1] == last:                    # stranded pawn moving sideways
                return [None] + list(avail)
            return list(avail) if avail else [None]
        if to[1] == ninth:
            return [None] + list(self._avail(state.board, pl))
        return [None]


class GrandShatranj(ChessLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Grand Shatranj"

    WIDTH = HEIGHT = 10
    PLY_CAP = 800
    PIECES = {
        "K": ([], ALL8),
        "J": ([], ALL8 + ALFIL + DABBABAH),
        "M": ([], ORTHO + DABBABAH + KNIGHT),
        "H": ([], DIAG + ALFIL + KNIGHT),
        "N": ([], KNIGHT),
        # The double-riders get custom move generation (see _rider_targets);
        # empty tables here keep the base slide/leap machinery away from them.
        "O": ([], []),
        "W": ([], []),
    }
    HEAVY = ("P", "N", "J", "M", "H", "O", "W")
    PIECE_VALUES = {"P": 1.0, "N": 3.0, "J": 4.0, "M": 4.5, "H": 4.0,
                    "O": 3.5, "W": 4.0, "K": 0.0}
    PAWN = ShatranjPawn(white_start=2, black_start=7)
    PROMOTION = ShatranjPromotion({"J": 1, "M": 1, "H": 1, "O": 2, "N": 2, "W": 2})
    CASTLING = NoCastling()

    # ---- setup (Grand Shatranj D) -------------------------------------------
    # Rank 1: War Machines in the corners. Rank 2: N O J K M H O N on files b-i.
    # Rank 3: ten pawns. Black mirrors White (kings share the e-file).
    RANK2 = ["N", "O", "J", "K", "M", "H", "O", "N"]      # files b..i

    def setup_board(self) -> dict:
        b = {}
        b[(0, 0)] = b[(9, 0)] = (WHITE, "W")
        b[(0, 9)] = b[(9, 9)] = (BLACK, "W")
        for i, t in enumerate(self.RANK2):
            b[(i + 1, 1)] = (WHITE, t)
            b[(i + 1, 8)] = (BLACK, t)
        for c in range(10):
            b[(c, 2)] = (WHITE, "P")
            b[(c, 7)] = (BLACK, "P")
        return b

    # ---- double-riders (Oliphant / Lightning War Machine) --------------------
    def _rider_targets(self, board, c, r, dirs):
        """Squares a double-rider at (c, r) can move to / capture on: one or two
        step-or-jump legs along a straight line; an intermediate landing square
        must be empty (no capturing mid-move); jumped squares may be occupied."""
        for dc, dr in dirs:
            sq = [(c + dc * k, r + dr * k) for k in (1, 2, 3, 4)]
            on = [self.on(*s) for s in sq]
            emp = [on[i] and sq[i] not in board for i in range(4)]
            if on[0]:
                yield sq[0]                       # step
            if on[1]:
                yield sq[1]                       # jump (passes over s1)
            if on[2] and (emp[0] or emp[1]):
                yield sq[2]                       # step+jump or jump+step
            if on[3] and emp[1]:
                yield sq[3]                       # jump+jump (lands on s2)

    def _pseudo(self, state):
        yield from super()._pseudo(state)
        board, player = state.board, state.to_move
        for (c, r), (pl, t) in list(board.items()):
            if pl == player and t in RIDERS:
                for tgt in self._rider_targets(board, c, r, RIDERS[t]):
                    occ = board.get(tgt)
                    if occ is None or occ[0] != player:
                        yield (c, r), tgt

    def attacked(self, board, c, r, by) -> bool:
        if super().attacked(board, c, r, by):
            return True
        # The double-rider reachability relation is symmetric, so scan outward
        # from the attacked square with the same rule.
        for t, dirs in RIDERS.items():
            for sq in self._rider_targets(board, c, r, dirs):
                if board.get(sq) == (by, t):
                    return True
        return False

    # ---- baring (shatranj win) ----------------------------------------------
    def _bare_result(self, state):
        """Terminal result forced by the bare-king rule, or None.

        If the side to move has only its king while the opponent still has
        men, the opponent has won -- unless the bare king can bare the
        opponent right back in one legal move, in which case the game is
        declared drawn (the counter-capture is assumed)."""
        men = {WHITE: 0, BLACK: 0}
        for (pl, t) in state.board.values():
            if t != "K":
                men[pl] += 1
        mover, other = state.to_move, 1 - state.to_move
        if (men[mover] == 0) == (men[other] == 0):
            return None                           # both bare (K v K) or neither
        if men[other] == 0:
            winner = mover                        # bare side already had its reply
        else:
            if men[other] == 1 and self._can_bare_back(state):
                return [0.0, 0.0]
            winner = other
        return [1.0, -1.0] if winner == WHITE else [-1.0, 1.0]

    def _can_bare_back(self, state):
        """Can the (bare) side to move legally capture the opponent's last man?"""
        target = next(sq for sq, (pl, t) in state.board.items()
                      if pl != state.to_move and t != "K")
        return any(to == target for (_, to) in self._legal(state))

    def _insufficient(self, board) -> bool:
        return len(board) <= 2                    # only K vs K (baring covers the rest)

    def is_terminal(self, state) -> bool:
        if self._bare_result(state) is not None:
            return True
        return super().is_terminal(state)

    def returns(self, state) -> list:
        br = self._bare_result(state)
        if br is not None:
            return br
        return super().returns(state)

    def legal_moves(self, state) -> list:
        if self._bare_result(state) is not None:
            return []
        return super().legal_moves(state)

    # ---- presentation --------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        br = self._bare_result(state)
        if br is not None:
            if br == [0.0, 0.0]:
                spec["caption"] = "Draw (mutual bare kings)"
            else:
                spec["caption"] = f"{'White' if br[0] > 0 else 'Black'} wins (bare king)"
        return spec
