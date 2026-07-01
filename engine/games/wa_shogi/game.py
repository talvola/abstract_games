"""Wa Shogi (和将棋, "Japanese-harmony shogi"), a large traditional Shogi variant
in which every one of the 27 pieces per side is named for an animal or bird.

Played on an 11x11 board. Built on the shared :mod:`agp.shogilike` core (royal
King, colour-relative movement, zone promotion, serialize/render), but Wa's piece
set is entirely its own, and two pieces move with *limited-range* slides that the
plain Shogi core does not model:

  * the Cloud Eagle ranges 1-3 squares diagonally forward (bounded slide), and
  * the Liberated Horse steps 1-2 squares straight backward (bounded slide),

so this subclass supplies its own move tables -- ``(slides, leaps, ranged)`` --
where ``ranged`` is a list of ``(dc, dr, maxdist)`` bounded slides, and overrides
``_piece_targets`` and ``attacked`` accordingly. All Wa pieces are left/right
symmetric (unlike Tori's Quails), so a colour only flips the forward (row) axis,
exactly as in ordinary Shogi.

**Drops:** this implementation is the DROP-LESS ("classic") ruleset. Historical
descriptions of Wa shogi make no mention of drops; the drop variant is a modern
addition. Captured pieces simply leave play. (See ``rules.md`` for the alternative.)

Player 0 = Sente (Black) at the bottom (row 0), advancing toward higher rows.
The royal piece is the Crane King (letter ``K``); mate/stalemate of it loses.
"""

from __future__ import annotations

from agp.shogilike import ShogiLike, SState, BLACK, WHITE

# ----------------------------------------------------------------- directions
# All in Black's forward frame: forward = +row (toward the enemy).
F, B = (0, 1), (0, -1)
WL, WR = (-1, 0), (1, 0)          # sideways (west / east)
FL, FR = (-1, 1), (1, 1)          # diagonally forward
BL, BR = (-1, -1), (1, -1)        # diagonally backward
ORTHO = [F, B, WL, WR]
DIAG = [FL, FR, BL, BR]
ALL8 = ORTHO + DIAG
# Treacherous-fox jump-to-second-square offsets (its 6 step directions doubled).
FOX = [FL, FR, BL, BR, F, B,
       (-2, 2), (2, 2), (-2, -2), (2, -2), (0, 2), (0, -2)]

# ------------------------------------------------------------- move tables
# BASE_MOVE[letter] = (slides, leaps, ranged); ranged = [(dc, dr, maxdist), ...]
BASE_MOVE = {
    # Crane King -- royal; one step in all 8 directions.
    "K": ([], ALL8, []),
    # Cloud Eagle -- unlimited forward/backward; 1-3 diag-forward; step sideways
    #                and diag-backward. (Does NOT promote.)
    "E": ([F, B], [WL, WR, BL, BR], [(-1, 1, 3), (1, 1, 3)]),
    # Flying Falcon -- ranges on all 4 diagonals; steps one forward.
    "H": ([FL, FR, BL, BR], [F], []),
    # Swallow's Wings -- ranges sideways; steps one forward/backward.
    "W": ([WL, WR], [F, B], []),
    # Treacherous Fox -- steps the 4 diagonals + forward/backward, and may JUMP
    #                    to the second square in each. (Does NOT promote.)
    "X": ([], FOX, []),
    # Running Rabbit -- ranges straight forward; steps 4 diagonals or straight back.
    "R": ([F], [FL, FR, BL, BR, B], []),
    # Violent Wolf -- 4 orthogonal + diag-forward (6).
    "L": ([], [F, B, WL, WR, FL, FR], []),
    # Violent Stag -- 4 diagonal + straight forward (5).
    "T": ([], [FL, FR, BL, BR, F], []),
    # Flying Goose -- forward/backward + diag-forward (4).
    "G": ([], [F, B, FL, FR], []),
    # Flying Cock -- sideways + diag-forward (4).
    "C": ([], [WL, WR, FL, FR], []),
    # Strutting Crow -- forward + diag-backward (3).
    "Y": ([], [F, BL, BR], []),
    # Swooping Owl -- forward + diag-backward (3). (Same move as the crow;
    #                 differs only in its promotion.)
    "O": ([], [F, BL, BR], []),
    # Blind Dog -- sideways + straight-backward + diag-forward (5).
    "D": ([], [WL, WR, B, FL, FR], []),
    # Climbing Monkey -- forward/backward + diag-forward (4). (Same move as the
    #                    goose; differs only in its promotion.)
    "M": ([], [F, B, FL, FR], []),
    # Liberated Horse -- ranges straight forward; steps 1-2 squares straight back.
    "N": ([F], [], [(0, -1, 2)]),
    # Oxcart -- ranges straight forward only.
    "U": ([F], [], []),
    # Sparrow Pawn -- one step straight forward.
    "P": ([], [F], []),
}

PROMO_MOVE = {
    # Sparrow Pawn -> Golden Bird (a gold general: 4 ortho + diag-forward).
    "P": ([], [F, B, WL, WR, FL, FR], []),
    # Swallow's Wings -> Gliding Swallow (a rook).
    "W": ([F, B, WL, WR], [], []),
    # Flying Falcon -> Tenacious Falcon (ranges 4 diag + forward/backward; step sideways).
    "H": ([FL, FR, BL, BR, F, B], [WL, WR], []),
    # Oxcart -> Plodding Ox (king move).
    "U": ([], ALL8, []),
    # Liberated Horse -> Heavenly Horse (knight jumps forward AND backward).
    "N": ([], [(-1, 2), (1, 2), (-1, -2), (1, -2)], []),
    # Violent Wolf -> Bear's Eyes (king move).
    "L": ([], ALL8, []),
    # Violent Stag -> Roaming Boar (king move minus straight backward).
    "T": ([], [F, WL, WR, FL, FR, BL, BR], []),
    # Flying Cock -> Raiding Falcon (ranges forward/backward; step sideways/diag-forward).
    "C": ([F, B], [WL, WR, FL, FR], []),
    # Flying Goose -> Swallow's Wings.
    "G": ([WL, WR], [F, B], []),
    # Blind Dog -> Violent Wolf.
    "D": ([], [F, B, WL, WR, FL, FR], []),
    # Climbing Monkey -> Violent Stag.
    "M": ([], [FL, FR, BL, BR, F], []),
    # Strutting Crow -> Flying Falcon.
    "Y": ([FL, FR, BL, BR], [F], []),
    # Swooping Owl -> Cloud Eagle.
    "O": ([F, B], [WL, WR, BL, BR], [(-1, 1, 3), (1, 1, 3)]),
    # Running Rabbit -> Treacherous Fox.
    "R": ([], FOX, []),
}

# Everything promotes except the Crane King, Cloud Eagle and Treacherous Fox.
CAN_PROMOTE = frozenset(PROMO_MOVE)              # = the promotable letters
# Only pure straight-forward movers can be stranded on the far rank.
FORCED_ON_LAST = ("P", "U")


def _movement(letter, promoted):
    return PROMO_MOVE[letter] if promoted else BASE_MOVE[letter]


class WaShogi(ShogiLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Wa Shogi"

    WIDTH = HEIGHT = 11
    ZONE = 3
    PLY_CAP = 400
    LABELS = {
        "K": "CK", "E": "CE", "H": "FF", "W": "SW", "X": "TF", "R": "RR",
        "L": "VW", "T": "VS", "G": "FG", "C": "FC", "Y": "SC", "O": "SO",
        "D": "BD", "M": "CM", "N": "LH", "U": "OX", "P": "SP",
        # promoted forms (labelled with the piece they become)
        "+P": "GB",   # Golden Bird
        "+W": "GS",   # Gliding Swallow
        "+H": "TcF",  # Tenacious Falcon
        "+U": "PO",   # Plodding Ox
        "+N": "HH",   # Heavenly Horse
        "+L": "BE",   # Bear's Eyes
        "+T": "RB",   # Roaming Boar
        "+C": "RF",   # Raiding Falcon
        "+G": "SW",   # Swallow's Wings
        "+D": "VW",   # Violent Wolf
        "+M": "VS",   # Violent Stag
        "+Y": "FF",   # Flying Falcon
        "+O": "CE",   # Cloud Eagle
        "+R": "TF",   # Treacherous Fox
    }

    # ---- attack maps (built from our own tables; add a ranged-slide map) -------
    def __init__(self):
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        self._ranged_att = {BLACK: {}, WHITE: {}}
        kinds = [(L, False) for L in BASE_MOVE] + [(L, True) for L in PROMO_MOVE]
        for pl in (BLACK, WHITE):
            fwd = 1 if pl == BLACK else -1
            for (letter, prom) in kinds:
                slides, leaps, ranged = _movement(letter, prom)
                for (dc, dr) in leaps:
                    off = (dc, dr * fwd)
                    self._leap_att[pl].setdefault((-off[0], -off[1]), set()).add((letter, prom))
                for (dc, dr) in slides:
                    d = (dc, dr * fwd)
                    self._slide_att[pl].setdefault((-d[0], -d[1]), set()).add((letter, prom))
                for (dc, dr, dist) in ranged:
                    d = (dc, dr * fwd)
                    self._ranged_att[pl].setdefault((-d[0], -d[1]), []).append((letter, prom, dist))

    # ---- movement --------------------------------------------------------------
    def _piece_targets(self, board, sq, pl, letter, promoted):
        c, r = sq
        fwd = self._fwd(pl)
        slides, leaps, ranged = _movement(letter, promoted)
        for (dc, dr) in leaps:
            t = (c + dc, r + dr * fwd)
            if self.on(*t) and (board.get(t) or (None,))[0] != pl:
                yield t
        for (dc, dr) in slides:
            sr = dr * fwd
            cc, rr = c + dc, r + sr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is None:
                    yield (cc, rr)
                else:
                    if occ[0] != pl:
                        yield (cc, rr)
                    break
                cc += dc
                rr += sr
        for (dc, dr, dist) in ranged:
            sr = dr * fwd
            cc, rr = c + dc, r + sr
            k = 1
            while self.on(cc, rr) and k <= dist:
                occ = board.get((cc, rr))
                if occ is None:
                    yield (cc, rr)
                else:
                    if occ[0] != pl:
                        yield (cc, rr)
                    break
                cc += dc
                rr += sr
                k += 1

    # ---- attacks (leap + unlimited slide + bounded slide) ----------------------
    def attacked(self, board, promoted, sq, by) -> bool:
        c, r = sq
        for (dc, dr), kinds in self._leap_att[by].items():
            pc = board.get((c + dc, r + dr))
            if pc is not None and pc[0] == by and (pc[1], (c + dc, r + dr) in promoted) in kinds:
                return True
        for (dc, dr), kinds in self._slide_att[by].items():
            cc, rr = c + dc, r + dr
            while self.on(cc, rr):
                pc = board.get((cc, rr))
                if pc is not None:
                    if pc[0] == by and (pc[1], (cc, rr) in promoted) in kinds:
                        return True
                    break
                cc += dc
                rr += dr
        for (dc, dr), kinds in self._ranged_att[by].items():
            maxd = max(md for (_, _, md) in kinds)
            cc, rr = c + dc, r + dr
            k = 1
            while self.on(cc, rr) and k <= maxd:
                pc = board.get((cc, rr))
                if pc is not None:
                    if pc[0] == by:
                        pr = (cc, rr) in promoted
                        for (L, kp, md) in kinds:
                            if md >= k and pc[1] == L and kp == pr:
                                return True
                    break
                cc += dc
                rr += dr
                k += 1
        return False

    # ---- promotion -------------------------------------------------------------
    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted or letter not in CAN_PROMOTE:
            return [False]
        if not (self.in_zone(pl, frm_r) or self.in_zone(pl, to_r)):
            return [False]
        # Sparrow Pawn / Oxcart move only straight forward, so on the far rank they
        # would have no move -> promotion is mandatory there.
        if letter in FORCED_ON_LAST and self._last_rank(pl, to_r):
            return [True]
        return [False, True]

    # ---- drop-less: no drops, captured pieces leave play -----------------------
    def _drop_moves(self, state):
        return []

    # ---- setup -----------------------------------------------------------------
    def setup_board(self):
        b = {}
        # Black (Sente), bottom. Back rank (row 0), files 0..10 left-to-right:
        back = ["U", "D", "Y", "G", "L", "K", "T", "C", "O", "M", "N"]
        for c, t in enumerate(back):
            b[(c, 0)] = (BLACK, t)
        # Rank 2 (row 1): Flying Falcon on the Blind-Dog file (1), Swallow's Wings
        # on the Crane-King file (5), Cloud Eagle on the Climbing-Monkey file (9).
        b[(1, 1)] = (BLACK, "H")
        b[(5, 1)] = (BLACK, "W")
        b[(9, 1)] = (BLACK, "E")
        # Rank 3 (row 2): Treacherous Fox on the Flying-Goose file (3), Running
        # Rabbit on the Flying-Cock file (7), Sparrow Pawns on every other file.
        b[(3, 2)] = (BLACK, "X")
        b[(7, 2)] = (BLACK, "R")
        for c in range(11):
            if c not in (3, 7):
                b[(c, 2)] = (BLACK, "P")
        # Rank 4 (row 3): the two remaining Sparrow Pawns, advanced in front of the
        # Fox and the Rabbit (files 3 and 7).
        b[(3, 3)] = (BLACK, "P")
        b[(7, 3)] = (BLACK, "P")
        # White (Gote): a 180-degree rotation of Black's army (all Wa pieces are
        # left/right symmetric, so this is the correct point-symmetric mirror).
        for (c, r), (p, t) in list(b.items()):
            b[(self.WIDTH - 1 - c, self.HEIGHT - 1 - r)] = (WHITE, t)
        return b, set()

    # ---- presentation: hide the (unused) reserve trays -------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        spec.pop("reserve", None)
        return spec
