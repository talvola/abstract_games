"""Tori Shogi (Bird Shogi, 鳥将棋), a 19th-century 7x7 Shogi variant in which
every piece is a bird. Built on the shared :mod:`agp.shogilike` core, so the drop
mechanic (captures switch sides and re-enter from hand), zone promotion,
serialize/render and reserve trays are all inherited -- but Tori's pieces are
entirely different from Shogi's and, crucially, the two Quails are *left/right
asymmetric*. The shogilike core flips only the forward (row) axis between colours,
which is correct for Shogi's left/right-symmetric pieces but WRONG for the Quails.

So this subclass supplies its own bird move-tables (in Black's forward frame) and
applies a full **180-degree rotation** (negate both file and rank offsets) for
White -- the correct transform for a point-symmetric Shogi setup, which is a no-op
for symmetric birds and the right mirror for the Quails.

Letters: P=Phoenix (royal), S=Swallow, F=Falcon, C=Crane, H=Pheasant (kiji),
L=Left Quail, R=Right Quail; promoted: +S=Goose, +F=Eagle. Player 0 = Black
(Sente) at the bottom (row 0), advancing toward higher rows.
"""

from __future__ import annotations

from agp.shogilike import ShogiLike, SState, BLACK, WHITE

# ---- bird movement, all expressed in BLACK's forward frame (forward = +row) ----
KING = [(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0), (-1, -1), (0, -1), (1, -1)]

# (slide_dirs, leap_offsets)
BIRD_BASE = {
    # Phoenix: royal, steps one square in all 8 directions.
    "P": ([], KING),
    # Swallow: steps one square straight forward (the pawn).
    "S": ([], [(0, 1)]),
    # Falcon: steps one square in all directions except straight backward.
    "F": ([], [(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0), (-1, -1), (1, -1)]),
    # Crane: one square in the 4 diagonals and straight forward/backward (no sideways).
    "C": ([], [(-1, 1), (1, 1), (-1, -1), (1, -1), (0, 1), (0, -1)]),
    # Pheasant: jumps to the 2nd square straight forward; steps one square diagonally
    # backward (both diagonals).
    "H": ([], [(0, 2), (-1, -1), (1, -1)]),
    # Left Quail: ranges straight forward and diagonally backward-right; steps one
    # square diagonally backward-left.
    "L": ([(0, 1), (1, -1)], [(-1, -1)]),
    # Right Quail: ranges straight forward and diagonally backward-left; steps one
    # square diagonally backward-right.
    "R": ([(0, 1), (-1, -1)], [(1, -1)]),
}

BIRD_PROMO = {
    # Goose (promoted Swallow): jumps to the 2nd square diagonally forward (both) or
    # the 2nd square straight backward.
    "S": ([], [(-2, 2), (2, 2), (0, -2)]),
    # Eagle (promoted Falcon): ranges diagonally forward and straight backward; steps
    # 1-2 squares diagonally backward; steps one square straight forward or sideways.
    "F": ([(-1, 1), (1, 1), (0, -1)],
          [(0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-2, -2), (2, -2)]),
}

CAN_PROMOTE = ("S", "F")
PROMO_MAP = {"S": "Goose", "F": "Eagle"}
DROP_TYPES = ("S", "F", "C", "H", "L", "R")   # Phoenix is never in hand


def _movement(letter, promoted):
    if promoted:
        return BIRD_PROMO[letter]
    return BIRD_BASE[letter]


class ToriShogi(ShogiLike):
    uid = "tori_shogi"
    name = "Tori Shogi"

    WIDTH = HEIGHT = 7
    ZONE = 2                  # the two farthest ranks promote
    PLY_CAP = 400
    LABELS = {
        "P": "Ph", "S": "Sw", "F": "Fa", "C": "Cr", "H": "Pt", "L": "LQ", "R": "RQ",
        "+S": "Go", "+F": "Ea",
    }

    def __init__(self):
        # Re-build the reverse-attack maps from the BIRD tables. As for the core,
        # a colour only changes the orientation, but here that is a full 180-deg
        # rotation (both axes), so we negate dc as well as dr for White.
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        kinds = [(L, False) for L in BIRD_BASE] + [(L, True) for L in BIRD_PROMO]
        for pl in (BLACK, WHITE):
            sgn = 1 if pl == BLACK else -1
            for (letter, prom) in kinds:
                slides, leaps = _movement(letter, prom)
                for (dc, dr) in leaps:
                    off = (dc * sgn, dr * sgn)
                    self._leap_att[pl].setdefault((-off[0], -off[1]), set()).add((letter, prom))
                for (dc, dr) in slides:
                    d = (dc * sgn, dr * sgn)
                    self._slide_att[pl].setdefault((-d[0], -d[1]), set()).add((letter, prom))

    # ---- movement (override the core's row-only flip with a full 180 rotation) --
    def _piece_targets(self, board, sq, pl, letter, promoted):
        c, r = sq
        sgn = 1 if pl == BLACK else -1
        slides, leaps = _movement(letter, promoted)
        for (dc, dr) in leaps:
            t = (c + dc * sgn, r + dr * sgn)
            if self.on(*t) and (board.get(t) or (None,))[0] != pl:
                yield t
        for (dc, dr) in slides:
            sc, sr = dc * sgn, dr * sgn
            cc, rr = c + sc, r + sr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is None:
                    yield (cc, rr)
                else:
                    if occ[0] != pl:
                        yield (cc, rr)
                    break
                cc += sc
                rr += sr

    def _king(self, board, pl):
        for sq, (p, t) in board.items():
            if p == pl and t == "P":          # Phoenix is the royal piece
                return sq
        return None

    # ---- promotion (only Swallow / Falcon, in the far two ranks) ----------------
    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted or letter not in CAN_PROMOTE:
            return [False]
        if not (self.in_zone(pl, frm_r) or self.in_zone(pl, to_r)):
            return [False]
        # A Swallow on the last rank could never move again -> promotion mandatory.
        if letter == "S" and self._last_rank(pl, to_r):
            return [True]
        return [False, True]

    # ---- drops (Tori nifu = at most TWO unpromoted swallows per file) ------------
    def _drop_moves(self, state):
        pl = state.to_move
        letters = [L for L, n in state.hands.get(pl, {}).items() if n > 0]
        if not letters:
            return []
        in_chk = self.in_check(state.board, state.promoted, pl)
        # count own unpromoted swallows per file (Tori allows up to two)
        swallow_files = {}
        for (c, r), (p, t) in state.board.items():
            if p == pl and t == "S" and (c, r) not in state.promoted:
                swallow_files[c] = swallow_files.get(c, 0) + 1
        out = []
        for c in range(self.WIDTH):
            for r in range(self.HEIGHT):
                if (c, r) in state.board:
                    continue
                for L in letters:
                    if not self._drop_ok(state, pl, L, c, r, swallow_files, in_chk):
                        continue
                    out.append(f"{L}@{c},{r}")
        return out

    def _drop_ok(self, state, pl, L, c, r, swallow_files, in_chk):
        if L == "S":
            # may not be dropped on the last rank (would have no move), and may not
            # be a THIRD unpromoted swallow on a file (Tori's nifu allows two).
            if self._last_rank(pl, r) or swallow_files.get(c, 0) >= 2:
                return False
        # a drop may not leave your own Phoenix in check
        if in_chk:
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            if self.in_check(b, state.promoted, pl):
                return False
        # a Swallow drop may not give immediate checkmate (uchifuzume analogue)
        if L == "S":
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            opp_k = self._king(b, 1 - pl)
            if opp_k is not None and self.attacked(b, state.promoted, opp_k, pl):
                if self._is_mated(b, state.promoted, state.hands, 1 - pl):
                    return False
        return True

    # ---- setup ------------------------------------------------------------------
    def setup_board(self):
        b = {}
        # Black (Sente) at the bottom. Back rank (row 0), from Black's left:
        #   Left Quail, Pheasant, Crane, Phoenix, Crane, Pheasant, Right Quail.
        back = ["L", "H", "C", "P", "C", "H", "R"]
        for c, t in enumerate(back):
            b[(c, 0)] = (BLACK, t)
        b[(3, 1)] = (BLACK, "F")                 # Falcon in front of the Phoenix
        for c in range(7):
            b[(c, 2)] = (BLACK, "S")             # swallow rank
        b[(2, 3)] = (BLACK, "S")                 # one advanced swallow (file c, offset)

        # White (Gote) at the top -- a 180-degree rotation of Black's army, so the
        # Quail labels line up (a Right Quail faces a Right Quail across the board).
        for (c, r), (p, t) in list(b.items()):
            rc, rr = self.WIDTH - 1 - c, self.HEIGHT - 1 - r
            b[(rc, rr)] = (WHITE, t)
        return b, set()
