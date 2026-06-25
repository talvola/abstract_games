"""Cannon Shogi (Taihou Shogi), invented by Peter Michaelsen, Feb 1998.

Standard 9x9 Shogi PLUS four "cannon" piece types borrowed from Xiangqi (Chinese
chess) and Janggi (Korean chess), and Janggi-style soldiers in place of pawns.
Built on :mod:`agp.shogilike`, so the drop / capture-switches-sides / zone
promotion machinery is shared with regular Shogi; only the cannon move-generation
and cannon check-detection are added on top.

The four cannons (forward is toward the opponent; movement is colour-symmetric):

* Gold cannon   (C) -- *orthogonal* Xiangqi cannon: slides like a rook on empty
                       squares; captures ONLY by jumping exactly one intervening
                       piece (a "screen") to land on the first enemy beyond.
* Copper cannon (D) -- *diagonal* Xiangqi cannon: like the gold cannon but on the
                       four diagonals (slides like a bishop, captures over a screen).
* Silver cannon (E) -- *orthogonal* Janggi cannon: must jump exactly one screen to
                       BOTH move and capture (it cannot move to an adjacent square;
                       it lands on the first square beyond a single screen, whether
                       empty -- a move -- or holding an enemy -- a capture).
* Iron cannon   (F) -- *diagonal* Janggi cannon: the silver cannon's move on the
                       four diagonals.

(Unlike in Janggi, a cannon here MAY use another cannon as a screen and MAY capture
another cannon -- there is no cannon-screen restriction.)

The nine pawns become five Janggi soldiers (P), one square forward OR sideways
(never backward), on files 0/2/4/6/8. A soldier captures the same way it moves and
still promotes to a Gold (tokin) in the zone.

Promotion zone is the far three ranks, as in Shogi. Promoting a cannon ("flying
cannon") adds a one-step move in the *perpendicular* family (diagonal steps for the
orthogonal cannons C/E, orthogonal steps for the diagonal cannons D/F); along that
short step a flying cannon ALSO behaves like a tiny cannon -- if a piece sits
adjacent in that direction it leaps that screen to capture on the second square.

Letters / labels: C=Gold cannon, D=Copper cannon, E=Silver cannon, F=Iron cannon,
plus the standard K R B G S N L P. A promoted piece is shown "+X".
"""

from __future__ import annotations

from agp.shogilike import (
    ShogiLike, SState, BLACK, WHITE,
    ORTHO, DIAG, CAN_PROMOTE,
)

# Our cannon letters.
GOLD_C, COPPER_C, SILVER_C, IRON_C = "C", "D", "E", "F"
CANNONS = (GOLD_C, COPPER_C, SILVER_C, IRON_C)
# Which directions each cannon ranges along, and whether it is a Janggi cannon
# (must jump a screen even to MOVE) vs an Xiangqi cannon (slides on empties,
# jumps only to capture).
CANNON_DIRS = {GOLD_C: ORTHO, COPPER_C: DIAG, SILVER_C: ORTHO, IRON_C: DIAG}
JANGGI = {GOLD_C: False, COPPER_C: False, SILVER_C: True, IRON_C: True}
# The perpendicular one-step family a *flying* (promoted) cannon gains.
FLY_STEPS = {GOLD_C: DIAG, COPPER_C: ORTHO, SILVER_C: DIAG, IRON_C: ORTHO}

# Janggi soldier: one step forward or sideways (forward sign flips per colour).
SOLDIER = [(0, 1), (-1, 0), (1, 0)]


class CannonShogi(ShogiLike):
    uid = "cannon_shogi"
    name = "Cannon Shogi"

    WIDTH = HEIGHT = 9
    ZONE = 3
    PLY_CAP = 500
    LABELS = {
        "K": "K", "R": "R", "B": "B", "G": "G", "S": "S", "N": "N", "L": "L",
        "P": "P", "C": "gC", "D": "cC", "E": "sC", "F": "iC",
        "+R": "+R", "+B": "+B", "+S": "+S", "+N": "+N", "+L": "+L", "+P": "+P",
        "+C": "+gC", "+D": "+cC", "+E": "+sC", "+F": "+iC",
    }

    # ------------------------------------------------------------------ setup
    def setup_board(self):
        b = {}
        back = ["L", "N", "S", "G", "K", "G", "S", "N", "L"]
        for c in range(9):
            b[(c, 0)] = (BLACK, back[c])
            b[(c, 8)] = (WHITE, back[c])
        # Rank 2 (row 1 for Black, row 7 for White): bishop, rook, and four cannons.
        #   Gold cannon (C)  on the left  gold-general file  (3)
        #   Silver cannon(E) on the left  silver-general file(2)
        #   Iron cannon  (F) on the right gold-general file  (5)
        #   Copper cannon(D) on the right silver-general file(6)
        #   Bishop (B) at file 1, Rook (R) at file 7 (as in Shogi).
        row2 = {1: "B", 2: SILVER_C, 3: GOLD_C, 5: IRON_C, 6: COPPER_C, 7: "R"}
        for c, t in row2.items():
            b[(c, 1)] = (BLACK, t)
        # White mirrors across the board centre (180-degree rotation).
        for c, t in row2.items():
            b[(8 - c, 7)] = (WHITE, t)
        # Five soldiers (pawns) on files 0,2,4,6,8.
        for c in (0, 2, 4, 6, 8):
            b[(c, 2)] = (BLACK, "P")
            b[(c, 6)] = (WHITE, "P")
        return b, set()

    # ------------------------------------------------------------ soldier/pawn
    # Override pawn movement: regular shogi pawn is forward-only; here it is the
    # Janggi soldier (forward + sideways). We special-case "P" in _piece_targets.

    # ---------------------------------------------------------- cannon helpers
    def _cannon_targets(self, board, sq, pl, letter, promoted):
        """Yield destination squares for a cannon (any of C/D/E/F)."""
        c, r = sq
        dirs = CANNON_DIRS[letter]
        janggi = JANGGI[letter]
        for dc, dr in dirs:
            cc, rr = c + dc, r + dr
            # Phase 1: travel over empty squares up to the first piece (the screen).
            while self.on(cc, rr) and board.get((cc, rr)) is None:
                if not janggi:
                    yield (cc, rr)        # Xiangqi cannon may move to empty squares
                cc += dc
                rr += dr
            if not self.on(cc, rr):
                continue                  # ran off the board with no screen
            # (cc,rr) holds the screen. Phase 2: continue past it to the landing.
            cc += dc
            rr += dr
            if janggi:
                # Janggi cannon: lands on the FIRST square beyond the screen,
                # whether empty (a move) or enemy (a capture). It does not range.
                if self.on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is None or occ[0] != pl:
                        yield (cc, rr)
            else:
                # Xiangqi cannon: skip empties beyond the screen, then capture the
                # first piece if it is an enemy.
                while self.on(cc, rr) and board.get((cc, rr)) is None:
                    cc += dc
                    rr += dr
                if self.on(cc, rr) and board[(cc, rr)][0] != pl:
                    yield (cc, rr)

    def _fly_step_targets(self, board, sq, pl, letter):
        """The extra perpendicular one-step (mini-cannon) move of a flying cannon.

        For each perpendicular direction: an empty adjacent square is a plain step;
        if a piece sits adjacent, leap it and land on the second square, capturing
        an enemy there (an empty second square is also a legal landing)."""
        c, r = sq
        for dc, dr in FLY_STEPS[letter]:
            a = (c + dc, r + dr)
            if not self.on(*a):
                continue
            occ = board.get(a)
            if occ is None:
                yield a                   # simple one-square step
            else:
                b2 = (c + 2 * dc, r + 2 * dr)   # leap the adjacent screen
                if self.on(*b2):
                    o2 = board.get(b2)
                    if o2 is None or o2[0] != pl:
                        yield b2

    # ----------------------------------------------------- override move-gen
    def _piece_targets(self, board, sq, pl, letter, promoted):
        if letter in CANNONS:
            yield from self._cannon_targets(board, sq, pl, letter, promoted)
            if promoted:
                yield from self._fly_step_targets(board, sq, pl, letter)
            return
        if letter == "P" and not promoted:
            c, r = sq
            fwd = self._fwd(pl)
            for dc, dr in SOLDIER:
                t = (c + dc, r + dr * fwd)
                if self.on(*t) and (board.get(t) or (None,))[0] != pl:
                    yield t
            return
        yield from super()._piece_targets(board, sq, pl, letter, promoted)

    # ------------------------------------------------- promotion eligibility
    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted:
            return [False]
        # Cannons and the Janggi soldier (P) can ALWAYS still move (they move
        # sideways / need a screen), so they are never "stuck" -- promotion is
        # purely optional whenever the move touches the zone, with no mandatory
        # last-rank case. (This differs from a regular Shogi pawn, which would be
        # frozen on the last rank and is forced to promote.)
        if letter in CANNONS or letter == "P":
            if self.in_zone(pl, frm_r) or self.in_zone(pl, to_r):
                return [False, True]
            return [False]
        return super()._promotion_options(letter, promoted, frm_r, to_r, pl)

    # ------------------------------------------------------------ drop legality
    def _drop_ok(self, state, pl, L, c, r, pawn_files, in_chk):
        # Standard Shogi drop rules (nifu / last-rank / uchifuzume / can't drop
        # into an existing check) come from the base class.
        if not super()._drop_ok(state, pl, L, c, r, pawn_files, in_chk):
            return False
        # ...but in Cannon Shogi a drop can also *discover* a check on your OWN
        # king by acting as a cannon's screen. The base class only re-checks king
        # safety when already in check, so verify it unconditionally here.
        if not in_chk:
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            if self.in_check(b, state.promoted, pl):
                return False
        return True

    # ------------------------------------------------------ cannon attacks
    def attacked(self, board, promoted, sq, by) -> bool:
        # Standard (slider/leaper) attacks first. NB: the base map models a normal
        # forward-only Shogi pawn, so it does NOT cover our Janggi soldier -- we add
        # the soldier's sideways/forward capture explicitly below.
        if super().attacked(board, promoted, sq, by):
            return True
        c, r = sq
        # Janggi soldier (unpromoted "P" of side `by`) attacks `sq` if one sits on a
        # square whose soldier-move reaches `sq`: one step back-toward-it or sideways.
        bwd = -self._fwd(by)            # the soldier of `by` advances by -bwd
        for dc, dr in ((0, bwd), (-1, 0), (1, 0)):
            p = board.get((c + dc, r + dr))
            if (p is not None and p[0] == by and p[1] == "P"
                    and (c + dc, r + dr) not in promoted):
                return True
        # Cannon attacks: a cannon of side `by` attacks `sq` iff `sq` is one of its
        # capture/landing targets. We reuse the very move-generator used for legal
        # moves, so check-detection can never diverge from how cannons actually
        # move. (Only a handful of cannons exist, so the per-cannon scan is cheap.)
        for csq, (p, t) in board.items():
            if p != by or t not in CANNONS:
                continue
            prom = csq in promoted
            if sq in self._cannon_targets(board, csq, by, t, prom):
                return True
            if prom and sq in self._fly_step_targets(board, csq, by, t):
                return True
        return False
