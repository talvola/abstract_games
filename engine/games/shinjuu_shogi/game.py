"""Shinjuu Shogi (真獣将棋, "true beast shogi") -- Dr. Eric Silverman's own
11x11 drop-shogi variant, themed on the Four Divine Beasts (Blue Dragon /
Azure Dragon, White Tiger, Vermillion Sparrow, Turtle-Snake / Black Tortoise)
plus their attendant creatures.

Sources (implementation-grade, followed exactly; sources override any brief):
  * https://drericsilverman.com/2021/11/20/11x11-shogi-part-i-shinjuu-shogi/
    (rules prose: 11x11 board, modern drops, checkmate, promotion in the far
    three ranks, the King and Great Standard do not promote).
  * https://drericsilverman.com/wp-content/uploads/2021/11/shinjuu-shogi-guide.pdf
    (the move+promotion guide -- EVERY piece's exact geometry was read square
    by square from the orange move diagrams and the red slide-arrows of this
    guide; see games/shinjuu_shogi/rules.md for the full move table and the
    handful of documented interpretations).

Standard modern-shogi engine underneath (agp.shogilike): colour-relative
movement, captured pieces change side and join the capturer's hand, drops with
the two-pawns (nifu), last-rank and drop-mate (uchifuzume) rules, promotion on
touching the far three ranks (optional; mandatory only for a Pawn reaching the
last rank), single royal King, win by checkmate. The rich Shinjuu piece set is
added ENTIRELY in this subclass -- a structured per-piece move descriptor
(simple leaps, unlimited slide rays, bounded slide ranges) plus two custom
generators for the Golden Bird (forward-diagonal ranging leap over up to three
pieces) and the Wooden Dove (a diagonal jump to the 3rd square then an optional
1-2 square slide). ``attacked()`` is computed forward from the SAME
``_piece_targets`` used to generate moves, so check detection can never
disagree with movement.

Player 0 = Sente (Black) at the bottom, advancing toward higher rows.
"""

from __future__ import annotations

import math

from agp.shogilike import ShogiLike, BLACK, WHITE

# ------------------------------------------------------------- directions
# All offsets are in Black's forward frame: forward = +row (toward the enemy);
# a piece of the other colour uses the same table with the row-sign flipped.
F, B = (0, 1), (0, -1)
WL, WR = (-1, 0), (1, 0)          # wazir left / right (sideways)
FL, FR = (-1, 1), (1, 1)          # forward-left / forward-right diagonal
BL, BR = (-1, -1), (1, -1)        # back-left / back-right diagonal
ALL8 = [FL, F, FR, WL, WR, BL, B, BR]

# ------------------------------------------------------------- move tables
# Each (letter, promoted) -> a spec dict with any of:
#   "leaps":   [(dc,df), ...]           single-square steps / multi-square jumps
#   "rays":    [(dc,df), ...]           unlimited blockable slides
#   "ranges":  [((dc,df), n), ...]      blockable slides of at most n squares
#   "special": "goldenbird" | "woodendove"
# (df = forward offset; the actual row delta is df * (+1 Black / -1 White).)


def _spec(leaps=(), rays=(), ranges=(), special=None):
    return {"leaps": list(leaps), "rays": list(rays),
            "ranges": list(ranges), "special": special}


# --- unpromoted (base) pieces -------------------------------------------------
SPEC_BASE = {
    "P": _spec(leaps=[F]),                                  # Pawn
    "G": _spec(leaps=[FL, F, FR, WL, WR, B]),               # Gold General
    "K": _spec(leaps=ALL8),                                 # King (royal)
    "L": _spec(leaps=[FL, FR, F, B, BL, BR]),               # Ferocious Leopard
    "D": _spec(leaps=[F, BL, BR]),                          # Dog
    "O": _spec(leaps=[FL, FR],                              # Old Kite
               ranges=[(F, 2), (B, 2), (WL, 2), (WR, 2)]),
    "E": _spec(leaps=[FL, F, FR],                           # Fierce Eagle
               ranges=[(WL, 2), (WR, 2), (BL, 2), (BR, 2)]),
    "T": _spec(rays=[F, FL, FR], leaps=[B],                 # Turtle Snake
               ranges=[(BL, 2), (BR, 2)]),
    "V": _spec(rays=[FL, FR, B], leaps=[F],                 # Vermillion Sparrow
               ranges=[(BL, 2), (BR, 2)]),
    "F": _spec(rays=[FL, FR],                               # Fragrant Elephant
               ranges=[(F, 2), (B, 2), (WL, 2), (WR, 2), (BL, 2), (BR, 2)]),
    "W": _spec(rays=[BL, BR],                               # White Elephant
               ranges=[(F, 2), (B, 2), (WL, 2), (WR, 2), (FL, 2), (FR, 2)]),
    "B": _spec(rays=[F, B, FR], ranges=[(WL, 2), (WR, 2)]),  # Blue Dragon
    "X": _spec(rays=[WL, WR, FL], ranges=[(F, 2), (B, 2)]),  # White Tiger
    "R": _spec(leaps=[FL, FR, BL, BR,                       # Kirin (ferz + jumps)
                      (0, 2), (0, -2), (2, 0), (-2, 0)]),
    "N": _spec(leaps=[WL, WR, F, B,                         # Phoenix (wazir + jumps)
                      (2, 2), (-2, 2), (2, -2), (-2, -2)]),
    "S": _spec(rays=[F, B, WL, WR, FL, FR],                 # Great Standard
               ranges=[(BL, 2), (BR, 2)]),
}

# --- promoted pieces ----------------------------------------------------------
SPEC_PROMO = {
    "P": _spec(leaps=[FL, F, FR, WL, WR, B]),               # +Pawn -> Gold move
    "G": _spec(rays=[FL, F, FR, WL, WR], leaps=[B]),        # Free Boar
    "L": _spec(rays=[F, B],                                 # Copper Elephant
               leaps=[WL, WR, FL, FR, BL, BR]),
    "D": _spec(rays=[F, BL, BR]),                           # Multi General
    "O": _spec(rays=[FL, F, FR, B]),                        # Bird of Paradise
    "E": _spec(rays=[F, B],                                 # Walking Heron
               ranges=[(WL, 2), (WR, 2), (FL, 2), (FR, 2)]),
    "T": _spec(rays=[FL, F, FR, BL, BR], leaps=[B]),        # Wizard Stork
    "V": _spec(rays=[FL, FR, BL, B, BR], leaps=[F]),        # Mountain Witch
    "F": _spec(rays=[F, B, WL, WR, BL, BR],                 # Great Elephant
               ranges=[(FL, 2), (FR, 2)]),
    "W": _spec(rays=[F, B],                                 # Golden Bird
               ranges=[(WL, 2), (WR, 2), (BL, 2), (BR, 2)],
               special="goldenbird"),
    "B": _spec(rays=[F, B, WR, FR], ranges=[(WL, 2)]),      # Divine Dragon
    "X": _spec(rays=[WL, WR, F, FL], ranges=[(B, 2)]),      # Divine Tiger
    "R": _spec(rays=[WL, WR],                               # Great Dragon
               leaps=[(2, 0), (-2, 0), (3, 0), (-3, 0)],
               ranges=[(F, 2), (B, 2), (BL, 3), (BR, 3)]),
    "N": _spec(leaps=[WL, WR, F, B], special="woodendove"),  # Wooden Dove
}

# Everything promotes except the King and the Great Standard.
PROMOTES = tuple(L for L in SPEC_BASE if L not in ("K", "S"))

# Rough material values for the MCTS rollout cutoff (relative, hand-tuned).
_VAL = {"P": 1, "D": 2, "L": 4, "O": 4, "R": 5, "N": 5, "G": 5, "E": 6,
        "T": 6, "V": 6, "F": 7, "W": 7, "B": 7, "X": 7, "S": 9, "K": 0}
_PVAL = {"P": 5, "D": 6, "L": 7, "O": 8, "R": 10, "N": 10, "G": 8, "E": 9,
         "T": 9, "V": 9, "F": 11, "W": 11, "B": 10, "X": 10}

# Setup -- Black's rows 0-3 (White = the 180-degree rotation). Columns 0..10
# are files 1..11 (Black's left to right). Read from shinjuu_initpos.png; note
# the deliberate left/right asymmetry (Blue Dragon / Turtle Snake / Old Kite
# on the left; White Tiger / Vermillion Sparrow / Fierce Eagle on the right).
ROW0 = ["B", "R", "N", "L", "G", "K", "G", "L", "N", "R", "X"]
ROW1 = {1: "T", 3: "F", 5: "S", 7: "W", 9: "V"}
ROW3 = {3: "D", 7: "D"}
# row 2: pawns everywhere except the two birds at files 4 (Old Kite) and 8
# (Fierce Eagle).
ROW2 = {3: "O", 7: "E"}


class ShinjuuShogi(ShogiLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Shinjuu Shogi"

    WIDTH = HEIGHT = 11
    ZONE = 3
    PLY_CAP = 600

    CAN_PROMOTE = PROMOTES
    # Short romaji abbreviations (the platform convention shared by chu/dai/sho
    # shogi — the render is tuned for 1-2 latin chars, not CJK). The authentic
    # kanji for every piece are listed in rules.md.
    LABELS = {
        # base pieces
        "P": "P", "G": "G", "K": "K", "L": "FL", "D": "Dg", "O": "OK",
        "E": "FE", "T": "TS", "V": "VS", "F": "Fg", "W": "WE",
        "B": "BD", "X": "WT", "R": "Kr", "N": "Ph", "S": "GS",
        # promoted forms (their own identities)
        "+P": "+P", "+G": "FB", "+L": "CE", "+D": "MG", "+O": "BP",
        "+E": "WH", "+T": "Wk", "+V": "MW", "+F": "GE", "+W": "GB",
        "+B": "DD", "+X": "DT", "+R": "GD", "+N": "WD",
    }

    def __init__(self):
        # No reverse-attack maps: attacked() is computed forward from
        # _piece_targets, so it stays consistent with move generation for the
        # ranging / jumping pieces the base maps cannot represent.
        pass

    # ---- movement ----------------------------------------------------------
    @staticmethod
    def _spec_for(letter, promoted):
        return SPEC_PROMO[letter] if (promoted and letter in SPEC_PROMO) else SPEC_BASE[letter]

    def _piece_targets(self, board, sq, pl, letter, promoted):
        """Return the SET of squares this piece can move to (empty or an enemy;
        never an own piece). Used for both move-gen and attack detection."""
        c, r = sq
        fwd = self._fwd(pl)
        spec = self._spec_for(letter, promoted)
        out = set()

        for (dc, df) in spec["leaps"]:
            t = (c + dc, r + df * fwd)
            if self.on(*t):
                occ = board.get(t)
                if occ is None or occ[0] != pl:
                    out.add(t)

        for (dc, df) in spec["rays"]:
            sc, sr = dc, df * fwd
            cc, rr = c + sc, r + sr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is None:
                    out.add((cc, rr))
                else:
                    if occ[0] != pl:
                        out.add((cc, rr))
                    break
                cc += sc
                rr += sr

        for (dc, df), n in spec["ranges"]:
            sc, sr = dc, df * fwd
            cc, rr = c + sc, r + sr
            k = 0
            while self.on(cc, rr) and k < n:
                occ = board.get((cc, rr))
                if occ is None:
                    out.add((cc, rr))
                else:
                    if occ[0] != pl:
                        out.add((cc, rr))
                    break
                cc += sc
                rr += sr
                k += 1

        sp = spec["special"]
        if sp == "goldenbird":
            for (dc, df) in (FL, FR):
                self._ranging_leap(board, c, r, dc, df * fwd, pl, 3, out)
        elif sp == "woodendove":
            for (dc, df) in (FL, FR, BL, BR):
                self._dove(board, c, r, dc, df * fwd, pl, out)

        return out

    def _ranging_leap(self, board, c, r, sc, sr, pl, maxjump, out):
        """Golden Bird: slide along (sc,sr) able to leap over up to `maxjump`
        pieces of either colour (landing on any empty square, or capturing an
        enemy, so long as no more than `maxjump` pieces were leapt to get
        there)."""
        jumped = 0
        cc, rr = c + sc, r + sr
        while self.on(cc, rr):
            occ = board.get((cc, rr))
            if occ is None:
                out.add((cc, rr))
            else:
                if occ[0] != pl:
                    out.add((cc, rr))
                jumped += 1
                if jumped > maxjump:
                    break
            cc += sc
            rr += sr

    def _dove(self, board, c, r, sc, sr, pl, out):
        """Wooden Dove: jump to the 3rd square along (sc,sr) -- over whatever
        occupies squares 1 and 2 -- then, if that square is empty, optionally
        slide 1 or 2 more squares (blockable)."""
        s3 = (c + 3 * sc, r + 3 * sr)
        if not self.on(*s3):
            return
        occ3 = board.get(s3)
        if occ3 is not None and occ3[0] == pl:
            return                       # cannot land on / pass an own piece here
        out.add(s3)
        if occ3 is None:
            cc, rr = s3
            for _ in range(2):
                cc += sc
                rr += sr
                if not self.on(cc, rr):
                    break
                occ = board.get((cc, rr))
                if occ is None:
                    out.add((cc, rr))
                elif occ[0] != pl:
                    out.add((cc, rr))
                    break
                else:
                    break

    # ---- attacks / check (forward, so it matches _piece_targets exactly) ---
    def attacked(self, board, promoted, sq, by) -> bool:
        if sq is None:
            return False
        for psq, (p, t) in board.items():
            if p != by:
                continue
            if sq in self._piece_targets(board, psq, by, t, psq in promoted):
                return True
        return False

    # ---- promotion ---------------------------------------------------------
    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted or letter not in self.CAN_PROMOTE:
            return [False]
        if not (self.in_zone(pl, frm_r) or self.in_zone(pl, to_r)):
            return [False]
        # A Pawn reaching the last rank would otherwise be stuck -> mandatory.
        # Every other piece can always move off the last rank, so promotion is
        # optional throughout.
        if letter == "P" and self._last_rank(pl, to_r):
            return [True]
        return [False, True]

    # ---- drops -------------------------------------------------------------
    def _drop_ok(self, state, pl, L, c, r, pawn_files, in_chk):
        # Only the Pawn carries drop restrictions here (no Lance/Knight in this
        # set); every other piece can move from any square it may be dropped on.
        if L == "P":
            if self._last_rank(pl, r) or c in pawn_files:
                return False               # last-rank / two-pawns (nifu)
        if in_chk:
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            if self.in_check(b, state.promoted, pl):
                return False               # a drop may block but never expose
        if L == "P":
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            if self.attacked(b, state.promoted, self._king(b, 1 - pl), pl):
                if self._is_mated(b, state.promoted, state.hands, 1 - pl):
                    return False           # uchifuzume: no pawn-drop checkmate
        return True

    # ---- Game interface ----------------------------------------------------
    def setup_board(self):
        b = {}
        for c, t in enumerate(ROW0):
            b[(c, 0)] = (BLACK, t)
        for c, t in ROW1.items():
            b[(c, 1)] = (BLACK, t)
        for c in range(self.WIDTH):
            b[(c, 2)] = (BLACK, ROW2.get(c, "P"))
        for c, t in ROW3.items():
            b[(c, 3)] = (BLACK, t)
        # White = the 180-degree rotation of Black's army.
        for (c, r), (p, t) in list(b.items()):
            b[(self.WIDTH - 1 - c, self.HEIGHT - 1 - r)] = (WHITE, t)
        return b, set()

    # ---- bot heuristic -----------------------------------------------------
    def heuristic(self, state):
        bal = 0.0
        for sq, (p, t) in state.board.items():
            v = (_PVAL if sq in state.promoted else _VAL).get(t, 3)
            bal += v if p == BLACK else -v
        for pl, hand in state.hands.items():
            s = sum(_VAL.get(L, 3) * n for L, n in hand.items())
            bal += s if pl == BLACK else -s
        sc = math.tanh(bal / 40.0)
        return [sc, -sc]
