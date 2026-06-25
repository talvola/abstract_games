"""Yari Shogi (槍将棋, "Spear Shogi"), a modern Shogi variant invented by Christian
Freeling (1981). "Yari" = spear, another name for the Shogi lance: the game's
signature is that almost every piece is a forward-ranging spear (it slides any
number of free squares straight forward, like a lance), each with a small extra
one-step component, and each promotes to a piece that ALSO ranges straight
*backward*.

Built on the shared :mod:`agp.shogilike` core, so drops (captures switch sides and
re-enter from hand), zone promotion, serialize/render and the reserve trays are all
inherited. The board is 7 files x 9 ranks. Yari pieces are left/right SYMMETRIC
(no asymmetric piece like Tori's Quails), so the core's row-only forward flip is
correct -- this subclass only supplies its own spear move-table and the royal piece
("G" = General) and drop letters.

Letters: G=General (royal, a King-mover), P=Pawn (spear), N=Yari Knight,
B=Yari Bishop, R=Yari Rook; promoted: +P=Yari Silver, +N/+B=Yari Gold,
+R=Rook (full). Player 0 = Black (Sente) at the bottom (row 0), advancing toward
higher rows.
"""

from __future__ import annotations

from agp.shogilike import ShogiLike, SState, BLACK, WHITE

# ---- spear movement, all expressed in BLACK's forward frame (forward = +row) ----
#   (slide_dirs, leap_offsets)
KING = [(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0), (-1, -1), (0, -1), (1, -1)]

YARI_BASE = {
    # General: steps one square in any of the 8 directions (royal).
    "G": ([], KING),
    # Pawn: steps one square straight forward.
    "P": ([], [(0, 1)]),
    # Yari Knight: ranges straight forward (slide); OR jumps "one forward + one
    # diagonally forward" = the two forward-narrow knight leaps (+-1, +2).
    "N": ([(0, 1)], [(-1, 2), (1, 2)]),
    # Yari Bishop: ranges straight forward (slide); OR steps one square diagonally
    # forward (either side).
    "B": ([(0, 1)], [(-1, 1), (1, 1)]),
    # Yari Rook: ranges straight forward OR sideways (3 forward/lateral rays).
    "R": ([(0, 1), (1, 0), (-1, 0)], []),
}

YARI_PROMO = {
    # Yari Silver (promoted Pawn): ranges straight backward; OR steps one square
    # forward, orthogonally or diagonally (the 3 forward steps).
    "P": ([(0, -1)], [(-1, 1), (0, 1), (1, 1)]),
    # Yari Gold (promoted Bishop / promoted Knight): ranges straight backward; OR
    # steps one square forward, sideways, or diagonally forward (5 steps).
    "N": ([(0, -1)], [(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0)]),
    "B": ([(0, -1)], [(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0)]),
    # Rook (promoted Yari Rook): the full rook -- all four orthogonal rays.
    "R": ([(0, 1), (0, -1), (1, 0), (-1, 0)], []),
}

CAN_PROMOTE = ("P", "N", "B", "R")
DROP_TYPES = ("P", "N", "B", "R")   # General is never in hand


def _movement(letter, promoted):
    if promoted:
        return YARI_PROMO[letter]
    return YARI_BASE[letter]


class YariShogi(ShogiLike):
    uid = "yari_shogi"
    name = "Yari Shogi"

    WIDTH = 7
    HEIGHT = 9
    ZONE = 3                  # the three farthest ranks promote
    PLY_CAP = 400
    LABELS = {
        "G": "G", "P": "P", "N": "yN", "B": "yB", "R": "yR",
        "+P": "yS", "+N": "yG", "+B": "yG", "+R": "+R",
    }

    def __init__(self):
        # Re-build the per-colour reverse-attack maps from the spear tables. As in
        # the core, a colour flips only the forward (row) sign -- Yari pieces are
        # left/right symmetric, so this row-only flip is correct.
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        kinds = [(L, False) for L in YARI_BASE] + [(L, True) for L in YARI_PROMO]
        for pl in (BLACK, WHITE):
            fwd = 1 if pl == BLACK else -1
            for (letter, prom) in kinds:
                slides, leaps = _movement(letter, prom)
                for (dc, dr) in leaps:
                    off = (dc, dr * fwd)
                    self._leap_att[pl].setdefault((-off[0], -off[1]), set()).add((letter, prom))
                for (dc, dr) in slides:
                    d = (dc, dr * fwd)
                    self._slide_att[pl].setdefault((-d[0], -d[1]), set()).add((letter, prom))

    # ---- movement (row-only flip, using the spear tables) ----------------------
    def _piece_targets(self, board, sq, pl, letter, promoted):
        c, r = sq
        fwd = 1 if pl == BLACK else -1
        slides, leaps = _movement(letter, promoted)
        for (dc, dr) in leaps:
            t = (c + dc, r + dr * fwd)
            if self.on(*t) and (board.get(t) or (None,))[0] != pl:
                yield t
        for (dc, dr) in slides:
            sc, sr = dc, dr * fwd
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
            if p == pl and t == "G":          # the General is the royal piece
                return sq
        return None

    # ---- promotion (P/N/B/R, in the far three ranks) ---------------------------
    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted or letter not in CAN_PROMOTE:
            return [False]
        if not (self.in_zone(pl, frm_r) or self.in_zone(pl, to_r)):
            return [False]
        # Mandatory when the unpromoted piece could never move again:
        #  - a Pawn or Yari Bishop on the last rank (no forward move left),
        #  - a Yari Knight in the last TWO ranks (no forward slide / no fwd leap).
        if letter in ("P", "B") and self._last_rank(pl, to_r):
            return [True]
        if letter == "N" and self._last_two(pl, to_r):
            return [True]
        return [False, True]

    # ---- drops (standard Shogi nifu + last-rank limits for P/N/B) ---------------
    def _drop_ok(self, state, pl, L, c, r, pawn_files, in_chk):
        # A Pawn, Yari Knight or Yari Bishop may not be dropped where it could never
        # move: P/B not on the last rank, N not on the last two ranks.
        if L == "P":
            if self._last_rank(pl, r) or c in pawn_files:
                return False
        elif L == "B":
            if self._last_rank(pl, r):
                return False
        elif L == "N":
            if self._last_two(pl, r):
                return False
        # a drop may not leave your own General in check
        if in_chk:
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            if self.in_check(b, state.promoted, pl):
                return False
        # uchifuzume: a Pawn drop may not deliver immediate checkmate
        if L == "P":
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            opp_k = self._king(b, 1 - pl)
            if opp_k is not None and self.attacked(b, state.promoted, opp_k, pl):
                if self._is_mated(b, state.promoted, state.hands, 1 - pl):
                    return False
        return True

    # ---- setup -----------------------------------------------------------------
    def setup_board(self):
        b = {}
        # Black (Sente) at the bottom. Back rank (row 0), from Black's left:
        #   Yari Rook, Yari Bishop, Yari Bishop, General, Yari Knight, Yari Knight,
        #   Yari Rook.
        back = ["R", "B", "B", "G", "N", "N", "R"]
        for c, t in enumerate(back):
            b[(c, 0)] = (BLACK, t)
        for c in range(self.WIDTH):
            b[(c, 2)] = (BLACK, "P")             # pawn (spear) rank

        # White (Gote) at the top -- a 180-degree rotation of Black's army (the
        # spears are symmetric, so this keeps the General on the centre file).
        for (c, r), (p, t) in list(b.items()):
            rc, rr = self.WIDTH - 1 - c, self.HEIGHT - 1 - r
            b[(rc, rr)] = (WHITE, t)
        return b, set()
