"""Tenjiku Shogi (天竺将棋, "Indian chess") -- the classic 16x16 large-shogi
variant: 78 pieces a side of 36 types, DROP-LESS, famous for the jumping
Generals and the burning Fire Demon. Win by CAPTURING or BURNING the enemy's
last royal (King, plus a Prince if a Drunk Elephant promoted -- DUAL ROYALTY).

Primary source (implementation-grade, followed exactly, overrides all briefs):
https://en.wikipedia.org/wiki/Tenjiku_shogi -- the fullest reliable spec: the
complete 36-type piece list with Betza moves, the exact 16x16 starting setup,
the promotion chains, the range-jumping Generals' rank hierarchy, and the Fire
Demon burning rules. Cross-checked against The Chess Variant Pages' Tenjiku
pages. Where the historical sources are contested, we take the mainstream
modern reading used by Wikipedia / The Chess Variant Pages / HaChu (documented
in rules.md and in the "Interpretations" comments below).

Modelled directly on games/nutty_shogi (H. G. Muller's "demagnified Tenjiku"),
which is a demagnification of THIS game: almost every Tenjiku special maps onto
a Nutty generator, verbatim:

  * Fire Demon  = Nutty FIREDEMON  (Bishop + sideways slide + 3-step area move;
    active burn, passive-PRIORITY burn, win/lose on burn, safe capture);
  * Horned Falcon = Nutty UNICORN  (slides all but forward + forward Lion sting);
  * Soaring Eagle = Nutty EAGLE    (slides all but fwd-diag + fwd-diag sting);
  * Lion / +Kirin = Nutty LION     (double king-step, jump, igui, pass);
  * Lion Hawk   = Nutty GRIFFON    (Lion + Bishop);
  * Free Eagle  = Nutty HARPY      (Queen + diagonal Lion);
  * Bishop/Rook/Vice/Great General = Nutty jumping-general rank machinery
    (range-jump over STRICTLY-lower-ranked pieces only when capturing);
  * Heavenly Tetrarch = Nutty TETRARCHS (skip the ignored first square).

Key facts:

* **Board 16x16**, files 16..1 (col 0..15), ranks 1..16. Player 0 = Sente
  (Black) at the bottom (row 0), advancing +row. White = the 180-degree
  rotation.
* **DROP-LESS** (no reserve / hand / '@' moves).
* **Win as event** -- DUAL ROYALTY. The King is royal; a Drunk Elephant that
  promotes becomes a Prince, a second royal. The game ends the instant a player
  loses their LAST royal (captured OR burned). Movegen is pseudo-legal (a side
  MAY leave a royal attacked); ``winner`` is stored when the last royal leaves
  the board. Stalemate (no legal move) loses (CVP ``stalemate=win``).
* **Promotion**: zone = far FIVE ranks (rows 11-15 for Black). Optional at end
  of a move that ENTERS the zone (start outside -> end inside) OR that CAPTURES
  and STARTS inside the zone. 30 types promote; King, Great General, Vice
  General, Free Eagle, Lion Hawk and Fire Demon do not, nor do already-promoted
  pieces (each piece has exactly one promoted form).
* **Range-jumping Generals' rank hierarchy** (Tenjiku's signature). A jumper
  may, ONLY when capturing, leap over any number of pieces of STRICTLY LOWER
  rank (friend or foe); it may capture ANY piece (even equal/higher rank) but
  cannot pass one of equal/higher rank. No jumper may pass a King or Prince.
    King, Prince        rank 4
    Great General       rank 3
    Vice General        rank 2
    Rook / Bishop Gen.  rank 1
* **Repetition / draws**: fourfold repetition of (position + side to move) or a
  hard ply cap -> an honest draw. The JCSA intent-based perpetual-check /
  perpetual-chase rules are a documented simplification (see rules.md).

36 piece types (internal letters):
  P pawn, D dog, S silver, FL ferocious leopard, G gold, BT blind tiger,
  C copper, I iron, N knight, L lance, VM vertical mover, SM side mover,
  RC reverse chariot, VS vertical soldier, SS side soldier, B bishop, R rook,
  DH dragon horse, DK dragon king, Q queen, Kr kirin, Ph phoenix,
  DE drunk elephant, WB water buffalo, CS chariot soldier, K king, Ln lion,
  LH lion hawk, FE free eagle, HF horned falcon, SE soaring eagle,
  BG bishop general, RG rook general, VG vice general, GG great general,
  FD fire demon.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from agp.shogilike import ShogiLike, SState, BLACK, WHITE, cell

# ---------------------------------------------------------------- directions
# All in Black's forward frame: forward = +row (toward the enemy).
F, B = (0, 1), (0, -1)
WL, WR = (-1, 0), (1, 0)
FL, FR = (-1, 1), (1, 1)
BL, BR = (-1, -1), (1, -1)
ORTHO = [F, B, WL, WR]
DIAG = [FL, FR, BL, BR]
ALL8 = ORTHO + DIAG
BOX2 = [(dc, dr) for dc in range(-2, 3) for dr in range(-2, 3) if (dc, dr) != (0, 0)]
# diagonal-lion (Free Eagle) reach: the 4 diagonal-adjacent squares + the 8
# squares reachable by two ferz steps (the "even" distance-2 squares).
EVEN8 = [(2, 0), (-2, 0), (0, 2), (0, -2), (2, 2), (-2, 2), (2, -2), (-2, -2)]
DIAG_BOX = DIAG + EVEN8
# Heavenly Tetrarch: 6 "long" directions (skip square 1, then slide) + 2
# sideways (squares 2-3 only).
LONG = [F, B, FL, FR, BL, BR]
SIDE = [WL, WR]

# ------------------------------------------------------------ movement tables
# letter -> (slides, leaps, ranged); ranged = [((dc, dr), max_steps), ...]
# (bounded, blockable rides -- NOT jumps). Special pieces (Lion, Lion Hawk,
# Free Eagle, Fire Demon, Horned Falcon, Soaring Eagle, the four Generals, the
# Heavenly Tetrarch) are NOT in these tables -- ``_kind``-dispatched code.
BASE_MOVE = {
    "P": ([], [F], []),                                       # fW
    "D": ([], [F, BL, BR], []),                               # fWbF   (dog)
    "S": ([], [FL, FR, BL, BR, F], []),                       # FfW    (silver)
    "FL": ([], [FL, FR, BL, BR, F, B], []),                   # FfbW   (leopard)
    "G": ([], [F, B, WL, WR, FL, FR], []),                    # WfF    (gold)
    "BT": ([], [FL, FR, BL, BR, WL, WR, B], []),              # FrlbW  (blind tiger)
    "C": ([], [F, FL, FR, B], []),                            # fKbW   (copper)
    "I": ([], [F, FL, FR], []),                               # fK     (iron)
    "N": ([], [(-1, 2), (1, 2)], []),                         # ffN    (knight)
    "L": ([F], [], []),                                       # fR     (lance)
    "VM": ([F, B], [WL, WR], []),                             # WfbR   (vertical mover)
    "SM": ([WL, WR], [F, B], []),                             # WrlR   (side mover)
    "RC": ([F, B], [], []),                                   # fbR    (reverse chariot)
    "VS": ([F], [B], [(WL, 2), (WR, 2)]),                     # WfRrlR2 (vertical soldier)
    "SS": ([WL, WR], [B], [(F, 2)]),                          # WfR2rlR (side soldier)
    "B": (DIAG, [], []),                                      # B
    "R": (ORTHO, [], []),                                     # R
    "DH": (DIAG, ORTHO, []),                                  # WB     (dragon horse)
    "DK": (ORTHO, DIAG, []),                                  # FR     (dragon king)
    "Q": (ALL8, [], []),                                      # Q
    "Kr": ([], [FL, FR, BL, BR, (0, 2), (0, -2), (2, 0), (-2, 0)], []),  # FD (kirin)
    "Ph": ([], [F, B, WL, WR, (2, 2), (-2, 2), (2, -2), (-2, -2)], []),  # WA (phoenix)
    "DE": ([], [F, FL, FR, WL, WR, BL, BR], []),              # FfrlW  (drunk elephant)
    "WB": (DIAG + [WL, WR], [], [(F, 2), (B, 2)]),            # BrlRfbR2 (water buffalo)
    "CS": (DIAG + [F, B], [], [(WL, 2), (WR, 2)]),            # BfbRrlR2 (chariot soldier)
    "K": ([], ALL8, []),                                      # K
}
PROMO_MOVE = {
    "P": ([], [F, B, WL, WR, FL, FR], []),                    # -> Gold (WfF)
    "D": ([F, BL, BR], [], []),                               # -> Multi General (fRbB)
    "S": ([F, B], [WL, WR], []),                              # -> Vertical Mover (WfbR)
    "FL": (DIAG, [], []),                                     # -> Bishop
    "G": (ORTHO, [], []),                                     # -> Rook
    "BT": ([F, B], [FL, FR, BL, BR, WL, WR], []),             # -> Flying Stag (fbRK)
    "C": ([WL, WR], [F, B], []),                              # -> Side Mover (WrlR)
    "I": ([F], [B], [(WL, 2), (WR, 2)]),                      # -> Vertical Soldier
    "N": ([WL, WR], [B], [(F, 2)]),                           # -> Side Soldier
    "L": ([F, FL, FR, B], [], []),                            # -> White Horse (fQbR)
    "VM": (DIAG + [F, B], [], []),                            # -> Flying Ox (BfbR)
    "SM": (DIAG + [WL, WR], [], []),                          # -> Free Boar (BrlR)
    "RC": ([F, B, BL, BR], [], []),                           # -> Whale (fRbQ)
    "VS": (DIAG + [F, B], [], [(WL, 2), (WR, 2)]),            # -> Chariot Soldier
    "SS": (DIAG + [WL, WR], [], [(F, 2), (B, 2)]),            # -> Water Buffalo
    "B": (DIAG, ORTHO, []),                                   # -> Dragon Horse (WB)
    "R": (ORTHO, DIAG, []),                                   # -> Dragon King (FR)
    "Ph": (ALL8, [], []),                                     # -> Queen
    "DE": ([], ALL8, []),                                     # -> Prince (K, 2nd royal)
    # Kr->Lion, Q->FreeEagle, WB->FireDemon, DH->HornedFalcon, DK->SoaringEagle,
    # CS->HeavenlyTetrarch, BG->ViceGeneral, RG->GreatGeneral, Ln->LionHawk,
    # HF->BishopGeneral, SE->RookGeneral : all special (see _kind).
}
# 30 promotable base types (K, GG, VG, FE, LH, FD never promote).
CAN_PROMOTE = frozenset(
    ["P", "D", "S", "FL", "G", "BT", "C", "I", "N", "L", "VM", "SM", "RC",
     "VS", "SS", "B", "R", "DH", "DK", "Q", "Kr", "Ph", "DE", "WB", "CS",
     "Ln", "HF", "SE", "BG", "RG"])

# German Chu Shogi Association average piece values (via Wikipedia), pawn = 1.
VALS = {"P": 1, "D": 1, "N": 1, "I": 2, "C": 2, "S": 2, "G": 3, "FL": 3,
        "BT": 3, "Kr": 3, "Ph": 3, "DE": 3, "K": 4, "L": 6, "RC": 6, "VM": 7,
        "SM": 7, "SS": 7, "VS": 8, "B": 10, "R": 12, "DH": 12, "DK": 14,
        "WB": 17, "CS": 18, "Ln": 18, "SE": 18, "HF": 19, "BG": 21, "Q": 22,
        "FE": 22, "RG": 23, "LH": 25, "VG": 39, "GG": 45, "FD": 83}
PVALS = {"P": 3, "D": 6, "N": 7, "I": 8, "C": 7, "S": 7, "G": 12, "FL": 10,
         "BT": 9, "Kr": 18, "Ph": 22, "DE": 4, "L": 14, "RC": 10, "VM": 16,
         "SM": 16, "SS": 17, "VS": 18, "B": 12, "R": 14, "DH": 19, "DK": 18,
         "WB": 83, "CS": 12, "Ln": 25, "SE": 23, "HF": 21, "BG": 39, "Q": 22,
         "RG": 45}

# Black's setup, rows 0-5 (White = the 180-degree rotation). Transcribed
# VERBATIM from the Wikipedia setup table (files 16..1 -> col 0..15; Black at
# the bottom). Rows: 0=back rank, 1, 2, 3, 4=pawns, 5=dogs.
ROW0 = ["L", "N", "FL", "I", "C", "S", "G", "K", "DE", "G", "S", "C", "I",
        "FL", "N", "L"]
ROW1 = {0: "RC", 2: "CS", 3: "CS", 5: "BT", 6: "Kr", 7: "Ln", 8: "Q",
        9: "Ph", 10: "BT", 12: "CS", 13: "CS", 15: "RC"}
ROW2 = ["SS", "VS", "B", "DH", "DK", "WB", "FD", "LH", "FE", "FD", "WB",
        "DK", "DH", "B", "VS", "SS"]
ROW3 = ["SM", "VM", "R", "HF", "SE", "BG", "RG", "GG", "VG", "RG", "BG",
        "SE", "HF", "R", "VM", "SM"]
DOGS = (4, 11)                                               # row 5


@dataclass
class TenjikuState(SState):
    winner: object = None      # seat that removed the opponent's last royal
    key: str = ""              # cached repetition key (recomputed, not serialized)


class TenjikuShogi(ShogiLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Tenjiku Shogi"

    WIDTH = HEIGHT = 16
    ZONE = 5
    PLY_CAP = 800
    LABELS = {
        # promoted forms with a distinct identity get a short label; unpromoted
        # letters default to themselves (already 1-2 char abbreviations).
        "+P": "+G", "+D": "MG", "+S": "+V", "+FL": "+B", "+G": "+R",
        "+BT": "FS", "+C": "+C", "+I": "+I", "+N": "+N", "+L": "WH",
        "+VM": "FO", "+SM": "FB", "+RC": "Wh", "+VS": "+VS", "+SS": "+WB",
        "+B": "+H", "+R": "+DK", "+DH": "HF", "+DK": "SE", "+Q": "FE",
        "+Kr": "Ln", "+Ph": "Q", "+DE": "Pr", "+WB": "FD", "+CS": "HT",
        "+Ln": "LH", "+HF": "BG", "+SE": "RG", "+BG": "VG", "+RG": "GG",
    }

    def __init__(self):
        # No reverse-attack maps: Tenjiku has no check rule (win = last royal
        # off the board). attacked() (for the selftest) is computed forward
        # from the same move generator.
        pass

    # ---- kind dispatch -----------------------------------------------------
    def _kind(self, letter, promoted):
        """Return the special-generator tag for this (letter, promoted), or
        None for a table-driven 'plain' piece."""
        if not promoted:
            return {"Ln": "LION", "LH": "LIONHAWK", "FE": "FREEEAGLE",
                    "FD": "FIREDEMON", "HF": "HORNEDFALCON", "SE": "SOARINGEAGLE",
                    "BG": "BISHOPGEN", "RG": "ROOKGEN", "VG": "VICEGEN",
                    "GG": "GREATGEN"}.get(letter)
        return {"Kr": "LION", "Ln": "LIONHAWK", "Q": "FREEEAGLE",
                "WB": "FIREDEMON", "DH": "HORNEDFALCON", "DK": "SOARINGEAGLE",
                "CS": "TETRARCH", "BG": "VICEGEN", "RG": "GREATGEN",
                "HF": "BISHOPGEN", "SE": "ROOKGEN"}.get(letter)

    def _jrank(self, letter, promoted):
        """Jumping-general rank: what a piece IS in the range-jump hierarchy.
        A jumper may pass (only when capturing) any piece of STRICTLY lower
        rank; it may capture, but not pass, one of equal/higher rank."""
        if letter == "K":
            return 4
        if letter == "DE" and promoted:            # Prince (2nd royal)
            return 4
        if letter == "GG" or (letter == "RG" and promoted):     # Great General
            return 3
        if letter == "VG" or (letter == "BG" and promoted):     # Vice General
            return 2
        if letter in ("RG", "BG") and not promoted:             # Rook/Bishop Gen.
            return 1
        if (letter == "SE" or letter == "HF") and promoted:     # ->Rook/Bishop Gen.
            return 1
        return 0

    def _is_fire_demon(self, letter, promoted):
        return letter == "FD" or (letter == "WB" and promoted)

    def _royal(self, letter, promoted):
        return letter == "K" or (letter == "DE" and promoted)

    # ---- primitive generators ----------------------------------------------
    def _slides(self, board, f, pl, dirs, fwd):
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in dirs:
            d = (dc, dr * fwd)
            cc = (f[0] + d[0], f[1] + d[1])
            while self.on(*cc):
                occ = board.get(cc)
                if occ is None:
                    yield f"{fs}>{cc[0]},{cc[1]}"
                else:
                    if occ[0] != pl:
                        yield f"{fs}>{cc[0]},{cc[1]}"
                    break
                cc = (cc[0] + d[0], cc[1] + d[1])

    def _plain_moves(self, board, f, pl, letter, promd, fwd):
        slides, leaps, ranged = (PROMO_MOVE if promd else BASE_MOVE)[letter]
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in leaps:
            to = (f[0] + dc, f[1] + dr * fwd)
            if not self.on(*to):
                continue
            occ = board.get(to)
            if occ is not None and occ[0] == pl:
                continue
            yield f"{fs}>{to[0]},{to[1]}"
        for (dc, dr), n in ranged:
            d = (dc, dr * fwd)
            cc = f
            for _ in range(n):
                cc = (cc[0] + d[0], cc[1] + d[1])
                if not self.on(*cc):
                    break
                occ = board.get(cc)
                if occ is None:
                    yield f"{fs}>{cc[0]},{cc[1]}"
                else:
                    if occ[0] != pl:
                        yield f"{fs}>{cc[0]},{cc[1]}"
                    break
        yield from self._slides(board, f, pl, slides, fwd)

    def _jump_slides(self, board, promoted, f, pl, dirs, mover_rank):
        """A slider that, when capturing, may jump over any number of pieces of
        STRICTLY lower jumping-rank; it may capture any piece regardless of rank
        (the destination need not be jumped over). Non-captures are normal
        slides (blocked by the first piece)."""
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in dirs:                                 # dirs are symmetric
            cc = (f[0] + dc, f[1] + dr)
            passed = 0
            while self.on(*cc):
                occ = board.get(cc)
                if occ is None:
                    if passed == 0:
                        yield f"{fs}>{cc[0]},{cc[1]}"         # normal slide
                else:
                    if occ[0] != pl:
                        yield f"{fs}>{cc[0]},{cc[1]}"         # capture (maybe over pieces)
                    if self._jrank(occ[1], cc in promoted) < mover_rank:
                        passed += 1                          # jump over lower rank
                    else:
                        break                                # cannot pass this piece
                cc = (cc[0] + dc, cc[1] + dr)

    def _area_targets(self, board, f, pl, max_steps):
        """King-walk of up to ``max_steps`` steps through EMPTY squares,
        stopping at the first capture (no jumping). Returns the set of reachable
        destination squares (an empty square or an enemy). Excludes the origin."""
        reached = set()
        frontier = {f}
        visited = {f}
        for _ in range(max_steps):
            nxt = set()
            for sq in frontier:
                for (dc, dr) in ALL8:
                    t = (sq[0] + dc, sq[1] + dr)
                    if not self.on(*t):
                        continue
                    occ = board.get(t)
                    if occ is None:
                        if t not in visited:
                            visited.add(t)
                            nxt.add(t)
                            reached.add(t)
                    elif occ[0] != pl:
                        reached.add(t)                       # capture -> stop here
            frontier = nxt
        reached.discard(f)
        return reached

    def _tetrarchs(self, board, f, pl):
        """Heavenly Tetrarch: SKIPS the (ignored, unaffected) first square in
        every direction: unlimited in the 6 long directions, squares 2-3 only
        sideways; plus igui (capture an adjacent enemy without moving)."""
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in LONG:                                # symmetric set
            cc = (f[0] + 2 * dc, f[1] + 2 * dr)
            while self.on(*cc):
                occ = board.get(cc)
                if occ is None:
                    yield f"{fs}>{cc[0]},{cc[1]}"
                else:
                    if occ[0] != pl:
                        yield f"{fs}>{cc[0]},{cc[1]}"
                    break
                cc = (cc[0] + dc, cc[1] + dr)
        for (dc, dr) in SIDE:
            for k in (2, 3):
                cc = (f[0] + k * dc, f[1] + k * dr)
                if not self.on(*cc):
                    break
                occ = board.get(cc)
                if occ is None:
                    yield f"{fs}>{cc[0]},{cc[1]}"
                else:
                    if occ[0] != pl:
                        yield f"{fs}>{cc[0]},{cc[1]}"
                    break
        for (dc, dr) in ALL8:                                # igui
            t = (f[0] + dc, f[1] + dr)
            if not self.on(*t):
                continue
            occ = board.get(t)
            if occ is not None and occ[0] != pl:
                yield f"{fs}>{t[0]},{t[1]}>{fs}"

    def _power_moves(self, board, f, pl, dirs, fwd):
        """Lion 'sting' power along each given ray: single step, direct 2-leap
        (jump), igui (capture-in-place), out-and-back pass, and double move --
        each leg staying on the same ray. (Horned Falcon forward, Soaring Eagle
        forward-diagonal.)"""
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in dirs:
            d = (dc, dr * fwd)
            m = (f[0] + d[0], f[1] + d[1])
            if not self.on(*m):
                continue
            occ_m = board.get(m)
            ms = f"{m[0]},{m[1]}"
            if occ_m is None:
                yield f"{fs}>{ms}>{ms}"                       # single step
                yield f"{fs}>{ms}>{fs}"                       # pass
            elif occ_m[0] != pl:
                yield f"{fs}>{ms}>{ms}"                       # capture-step
                yield f"{fs}>{ms}>{fs}"                       # igui
            j = (f[0] + 2 * d[0], f[1] + 2 * d[1])
            if not self.on(*j):
                continue
            occ_j = board.get(j)
            js = f"{j[0]},{j[1]}"
            if occ_j is None or occ_j[0] != pl:
                yield f"{fs}>{js}"                            # direct 2-leap
            if occ_m is not None and occ_m[0] != pl and (occ_j is None or occ_j[0] != pl):
                yield f"{fs}>{ms}>{js}"                       # double move

    def _lion_moves(self, board, f, pl, steps, box):
        """Generic (possibly direction-restricted) Lion: up to two king steps
        per turn (changing direction), first step may jump. Encodings:
          ``f>t``      adjacent step (dist 1) or direct 2-leap (dist 2, jumps),
          ``f>m>f``    igui (m enemy) or out-and-back pass (m empty),
          ``f>m>t``    double capture / hit-and-run (m enemy, t != m,f).
        (Adjacent steps use the 2-cell form so they de-duplicate against a
        companion slider's first square in Lion Hawk / Free Eagle.)"""
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in box:
            t = (f[0] + dc, f[1] + dr)
            if not self.on(*t):
                continue
            occ = board.get(t)
            if occ is not None and occ[0] == pl:
                continue
            yield f"{fs}>{t[0]},{t[1]}"
        for (dc, dr) in steps:
            m = (f[0] + dc, f[1] + dr)
            if not self.on(*m):
                continue
            occ_m = board.get(m)
            ms = f"{m[0]},{m[1]}"
            if occ_m is None:
                yield f"{fs}>{ms}>{fs}"                       # pass
                continue
            if occ_m[0] == pl:
                continue
            yield f"{fs}>{ms}>{fs}"                           # igui
            for (dc2, dr2) in steps:
                t = (m[0] + dc2, m[1] + dr2)
                if not self.on(*t) or t == f:
                    continue
                occ_t = board.get(t)
                if occ_t is not None and occ_t[0] == pl:
                    continue
                yield f"{fs}>{ms}>{t[0]},{t[1]}"             # double / hit-run

    def _piece_moves(self, state, f, pl, letter, promd, fwd):
        board = state.board
        k = self._kind(letter, promd)
        if k is None:
            yield from self._plain_moves(board, f, pl, letter, promd, fwd)
        elif k == "LION":
            yield from self._lion_moves(board, f, pl, ALL8, BOX2)
        elif k == "LIONHAWK":
            yield from self._lion_moves(board, f, pl, ALL8, BOX2)
            yield from self._slides(board, f, pl, DIAG, fwd)
        elif k == "FREEEAGLE":
            yield from self._slides(board, f, pl, ALL8, fwd)
            yield from self._lion_moves(board, f, pl, DIAG, DIAG_BOX)
        elif k == "FIREDEMON":
            yield from self._slides(board, f, pl, DIAG + [WL, WR], fwd)
            fs = f"{f[0]},{f[1]}"
            for t in self._area_targets(board, f, pl, 3):
                yield f"{fs}>{t[0]},{t[1]}"
        elif k == "VICEGEN":
            yield from self._jump_slides(board, state.promoted, f, pl, DIAG, 2)
            fs = f"{f[0]},{f[1]}"
            for t in self._area_targets(board, f, pl, 3):
                yield f"{fs}>{t[0]},{t[1]}"
        elif k == "BISHOPGEN":
            yield from self._jump_slides(board, state.promoted, f, pl, DIAG, 1)
        elif k == "ROOKGEN":
            yield from self._jump_slides(board, state.promoted, f, pl, ORTHO, 1)
        elif k == "GREATGEN":
            yield from self._jump_slides(board, state.promoted, f, pl, ALL8, 3)
        elif k == "TETRARCH":
            yield from self._tetrarchs(board, f, pl)
        elif k == "HORNEDFALCON":
            yield from self._slides(board, f, pl, DIAG + [B, WL, WR], fwd)
            yield from self._power_moves(board, f, pl, [F], fwd)
        elif k == "SOARINGEAGLE":
            yield from self._slides(board, f, pl, ORTHO + [BL, BR], fwd)
            yield from self._power_moves(board, f, pl, [FL, FR], fwd)

    # ---- move generation (with de-dup + zone promotion) --------------------
    def _moves(self, state):
        board, pl = state.board, state.to_move
        fwd = self._fwd(pl)
        seen = set()
        for sq, (p, letter) in list(board.items()):
            if p != pl:
                continue
            promd = sq in state.promoted
            fz = self.in_zone(pl, sq[1])
            promotable = (not promd) and (letter in CAN_PROMOTE)
            for m in self._piece_moves(state, sq, pl, letter, promd, fwd):
                if m in seen:
                    continue
                seen.add(m)
                yield m
                if not promotable:
                    continue
                cells = [cell(c) for c in m.split(">")]
                final = cells[-1]
                if len(cells) == 2:
                    occ = board.get(cells[1])
                    cap = occ is not None and occ[0] != pl
                else:
                    om = board.get(cells[1])
                    cap = om is not None and om[0] != pl
                    if not cap and cells[2] not in (cells[1], sq):
                        ot = board.get(cells[2])
                        cap = ot is not None and ot[0] != pl
                tz = self.in_zone(pl, final[1])
                if (tz and not fz) or (fz and cap):
                    pm = m + "=+"
                    if pm not in seen:
                        seen.add(pm)
                        yield pm

    # ---- Game interface ----------------------------------------------------
    def setup_board(self):
        b = {}
        for c, t in enumerate(ROW0):
            b[(c, 0)] = (BLACK, t)
        for c, t in ROW1.items():
            b[(c, 1)] = (BLACK, t)
        for c, t in enumerate(ROW2):
            b[(c, 2)] = (BLACK, t)
        for c, t in enumerate(ROW3):
            b[(c, 3)] = (BLACK, t)
        for c in range(self.WIDTH):
            b[(c, 4)] = (BLACK, "P")
        for c in DOGS:
            b[(c, 5)] = (BLACK, "D")
        for (c, r), (p, t) in list(b.items()):
            b[(self.WIDTH - 1 - c, self.HEIGHT - 1 - r)] = (WHITE, t)
        return b, set()

    def initial_state(self, options=None, rng=None):
        board, promoted = self.setup_board()
        st = TenjikuState(board=board, promoted=frozenset(promoted),
                          hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
        st.key = self._poskey(st)
        st.reps = {st.key: 1}
        return st

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        return list(self._moves(state))

    def _draw(self, state) -> bool:
        if state.winner is not None:
            return False
        return state.ply >= self.PLY_CAP or state.reps.get(state.key, 0) >= 4

    def is_terminal(self, state) -> bool:
        if state.winner is not None or self._draw(state):
            return True
        return next(self._moves(state), None) is None

    def returns(self, state):
        if state.winner is not None:
            return [1.0, -1.0] if state.winner == BLACK else [-1.0, 1.0]
        if self._draw(state):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == BLACK else [1.0, -1.0]

    def apply_move(self, state, move, rng=None):
        promote = move.endswith("=+")
        if promote:
            move = move[:-2]
        cells = [cell(p) for p in move.split(">")]
        f = cells[0]
        b = dict(state.board)
        prom = set(state.promoted)
        pl, letter = b.pop(f)
        was_prom = f in state.promoted
        prom.discard(f)
        enemy = 1 - pl

        if len(cells) == 2:
            final = cells[1]
            if b.pop(final, None) is not None:
                prom.discard(final)
        else:
            m, final = cells[1], cells[2]
            if b.pop(m, None) is not None:
                prom.discard(m)
            if final != m and final != f:
                if b.pop(final, None) is not None:
                    prom.discard(final)
        b[final] = (pl, letter)
        prom.discard(final)
        if promote or was_prom:
            prom.add(final)

        # ---- Fire effects ----------------------------------------------------
        # Passive burn (priority): if the mover LANDS next to a surviving enemy
        # Fire Demon, the mover is destroyed before it can do anything else (its
        # capture, if any, has already happened). The stationary Demon and every
        # other adjacent piece survive.
        burned = False
        for (dc, dr) in ALL8:
            nb = (final[0] + dc, final[1] + dr)
            occ = b.get(nb)
            if occ is not None and occ[0] == enemy and self._is_fire_demon(occ[1], nb in prom):
                burned = True
                break
        if burned:
            b.pop(final, None)
            prom.discard(final)
        elif self._is_fire_demon(letter, final in prom):
            # Active burn: the (surviving) Fire Demon torches every enemy on its
            # eight neighbours (no enemy Demon can be adjacent here, else the
            # passive burn above would have fired first).
            for (dc, dr) in ALL8:
                nb = (final[0] + dc, final[1] + dr)
                occ = b.get(nb)
                if occ is not None and occ[0] == enemy:
                    b.pop(nb, None)
                    prom.discard(nb)

        # ---- win as event: DUAL ROYALTY -- a side lost its LAST royal --------
        winner = state.winner
        b_royal = any(p == BLACK and self._royal(t, sq in prom)
                      for sq, (p, t) in b.items())
        w_royal = any(p == WHITE and self._royal(t, sq in prom)
                      for sq, (p, t) in b.items())
        if not w_royal and (pl == BLACK or b_royal):
            winner = BLACK          # the winning capture/burn takes priority
        elif not b_royal and (pl == WHITE or w_royal):
            winner = WHITE
        elif not b_royal:
            winner = WHITE
        elif not w_royal:
            winner = BLACK

        st = TenjikuState(board=b, promoted=frozenset(prom),
                          hands={BLACK: {}, WHITE: {}}, to_move=enemy,
                          ply=state.ply + 1, reps=dict(state.reps), winner=winner)
        st.key = self._poskey(st)
        st.reps[st.key] = st.reps.get(st.key, 0) + 1
        return st

    # ---- attacks (forward, for the selftest -- NOT used by the live rules) --
    def attacked_squares(self, state, by):
        """Set of opponent-occupied squares that side ``by`` can remove this
        turn (capture OR burn), computed FORWARD from the same move generator
        so it can never disagree with movegen."""
        probe = TenjikuState(board=dict(state.board),
                             promoted=frozenset(state.promoted),
                             hands={BLACK: {}, WHITE: {}}, to_move=by)
        probe.key = ""
        probe.reps = {}
        enemy = 1 - by
        victims = {sq for sq, (p, t) in state.board.items() if p == enemy}
        out = set()
        for m in self._moves(probe):
            nb = self.apply_move(probe, m).board
            for sq in victims:
                if nb.get(sq) != state.board[sq]:
                    out.add(sq)
        return out

    def attacked(self, state, sq, by):
        return sq in self.attacked_squares(state, by)

    # ---- keys / (de)serialise ----------------------------------------------
    def _poskey(self, state) -> str:
        parts = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                occ = state.board.get((c, r))
                if occ is None:
                    parts.append(".")
                else:
                    tag = "+" if (c, r) in state.promoted else ""
                    parts.append("bw"[occ[0]] + tag + occ[1])
        return "|".join(parts) + f"#{state.to_move}"

    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["winner"] = state.winner
        return d

    def deserialize(self, d) -> TenjikuState:
        base = super().deserialize(d)
        st = TenjikuState(board=base.board, promoted=base.promoted,
                          hands=base.hands, to_move=base.to_move, ply=base.ply,
                          reps=base.reps, winner=d.get("winner"))
        st.key = self._poskey(st)
        return st

    # ---- bot heuristic -----------------------------------------------------
    def heuristic(self, state):
        bal = 0.0
        for sq, (p, t) in state.board.items():
            v = (PVALS if sq in state.promoted else VALS).get(t, 4.0)
            bal += v if p == BLACK else -v
        score = math.tanh(bal / 120.0)
        return [score, -score]

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move) -> str:
        promote = move.endswith("=+")
        raw = move[:-2] if promote else move
        parts = raw.split(">")
        f = cell(parts[0])
        _, t = state.board.get(f, (None, "?"))
        tag = self._label(t, f in state.promoted)
        if len(parts) == 3:
            m, tt = cell(parts[1]), cell(parts[2])
            if tt == f:
                if m in state.board:
                    return f"{tag}{parts[0]}x!{parts[1]}"     # igui
                return f"{tag}{parts[0]} pass"
            s1 = "x" if m in state.board else "-"
            s2 = "x" if tt in state.board else "-"
            return f"{tag}{parts[0]}{s1}{parts[1]}{s2}{parts[2]}"
        sep = "x" if cell(parts[1]) in state.board else "-"
        return f"{tag}{parts[0]}{sep}{parts[1]}" + ("+" if promote else "")

    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": p,
             "label": self._label(t, (c, r) in state.promoted)}
            for (c, r), (p, t) in state.board.items()
        ]
        names = {BLACK: "Sente (Black)", WHITE: "Gote (White)"}
        if state.winner is not None:
            caption = f"{names[state.winner]} wins — enemy royals captured or burned"
        elif self.is_terminal(state):
            ret = self.returns(state)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
