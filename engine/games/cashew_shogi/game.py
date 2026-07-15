"""Cashew Shogi -- H. G. Muller's "demagnified Dai Dai Shogi": a 13x13
large-shogi variant, 54 pieces a side of 35 types (2 more via promotion),
DROP-LESS, won by CAPTURING the enemy King.

Authoritative source (implementation-grade, followed exactly, overrides all
briefs): https://www.chessvariants.com/rules/cashew-shogi  (H. G. Muller).
Its Interactive-Diagram config block gives the exact per-piece Betza move
strings + the exact initial squares + the promotion table.

**Oracle:** every piece's move definition, the exact starting FEN and the piece
set were DIFFERENTIAL-CONFIRMED against HaChu 0.21 (Muller's own reference
engine, which plays `variant cashew-shogi`). HaChu prints, on loading the
variant, both its full initial FEN (matched here rank-by-rank) and each piece's
Betza string -- those verbatim strings are transcribed into the tables below.

Modelled on games/nutty_shogi and games/chu_shogi (drop-less, no-check,
king-capture ShogiLike subclasses with a full Lion engine). Key facts:

* **Board 13x13**, files a-m (col 0-12), ranks 1-13 (row 0-12). Player 0 =
  Sente (Black) at the bottom, advancing +row. White = the 180-degree rotation
  (asymmetric pieces -- Generals, Guards, Chariots -- flip both axes, so the
  forward frame multiplies BOTH components by the side's sign).
* **DROP-LESS** (no reserve / hand / '@' moves).
* **Win as event** -- the King is the sole royal and does NOT promote; the game
  ends the instant a King is captured. Movegen is pseudo-legal (a side MAY leave
  its own King attacked); ``winner`` is stored when a King leaves the board.
* **Promotion BY CAPTURE ONLY** -- there is NO promotion zone. A promotable
  piece that captures something MUST promote (mandatory, no choice); a
  non-capturing move never promotes. 12 types promote (each to one fixed form);
  everything else -- including Pawns -- never promotes.
* **Repetition / draws**: fourfold repetition of (position + side to move) or a
  hard ply cap -> an honest draw. CVP's intent-based perpetual-check /
  perpetual-chase loss rules are a documented simplification (see rules.md).

Internal letters (base pieces, == CVP interactive-diagram piece):
  P pawn, S silver, G gold, FL leopard, TI tiger, BE bear, LG left general,
  RG right general, K king, LA lance, GU gun, LC left chariot, RC right chariot,
  BG broad guard, DG deep guard, N commoner, BU butterfly, DR dragon,
  FH flying horse, PH phoenix, KI kirin, VI viking, HU hun, KT kite, VP viper,
  WO wolf, LN lion.
Promoted forms are the base letter + a "promoted" flag:
  N->flag, BU->crowned bishop, DR->castle, FH->queen, PH->golden bird,
  KI->unicorn, VI->wolf, HU->lion, KT->goblin, VP->hook mover,
  WO->elephant, LN->berserker.
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

# ------------------------------------------------------------ movement tables
# letter -> (slides, leaps, ranged); ranged = [((dc, dr), max_steps), ...]
# (bounded, blockable slides). Special pieces (Lion/Berserker, Wolf, Goblin,
# Hook Mover) are NOT in these tables -- they are ``_kind``-dispatched.
#
# Every entry transcribes HaChu 0.21's Betza string for that piece (shown in
# the comment as HaChu prints it).
BASE_MOVE = {
    "P":  ([],            [F],                              []),                       # fW
    "S":  ([],            [FL, FR, BL, BR, F],              []),                       # FfW
    "G":  ([],            [F, B, WL, WR, FL, FR],           []),                       # WfF
    "FL": ([],            [FL, FR, BL, BR, F, B],           []),                       # FvW
    "TI": ([],            [FL, FR],                         [(F, 2), (B, 2)]),         # fFvW2
    "BE": ([],            [WL, WR],                         [(FL, 2), (FR, 2)]),       # fF2sW
    "LG": ([],            [FL, FR, BL, BR, F, B, WR],       []),                       # FvrW
    "RG": ([],            [FL, FR, BL, BR, F, B, WL],       []),                       # FvlW
    "K":  ([],            ALL8,                             []),                       # K
    "LA": ([F],           [],                               []),                       # fR
    "GU": ([F],           [B],                              []),                       # fRbW
    "LC": ([F, FL, BR],   [B],                              []),                       # lfrbBfRbW
    "RC": ([F, FR, BL],   [B],                              []),                       # rflbBfRbW
    "BG": ([WL, WR, FR],  [FL],                             [(F, 2), (B, 2)]),         # sRvW2frBflF
    "DG": ([F, B, FL],    [FR],                             [(WL, 2), (WR, 2)]),       # vRsW2flBfrF
    "N":  ([],            ALL8,                             []),                       # K (commoner)
    "BU": ([],            [FL, FR, BL, BR],                 []),                       # F
    "DR": ([],            [],                               [(FL, 2), (FR, 2),
                                                            (BL, 2), (BR, 2)]),        # F2
    "FH": ([],            [F, B, WL, WR],                   [(FL, 2), (FR, 2)]),       # WfF2
    "PH": ([],            [F, B, WL, WR,
                          (2, 2), (-2, 2), (2, -2), (-2, -2)], []),                    # WA
    "KI": ([],            [FL, FR, BL, BR,
                          (0, 2), (0, -2), (2, 0), (-2, 0)], []),                      # FD
    "VI": ([],            [FL, FR, F, B],                   [(WL, 2), (WR, 2)]),       # fFvWsW2
    "HU": ([],            [FL, FR, WL, WR],                 [(F, 2), (B, 2)]),         # fFsWvW2
    "KT": ([],            [FL, FR],                         [(F, 2), (B, 2),
                                                            (WL, 2), (WR, 2)]),        # W2fF
    "VP": ([],            [WL, WR, (0, 2), (2, -2), (-2, -2)], []),                    # sWfDbA
    # WO (wolf) and LN (lion) are special -- see _kind.
}
PROMO_MOVE = {
    "N":  ([F, FL, FR],   [],                               [(BL, 2), (BR, 2),
                                                            (B, 2), (WL, 2), (WR, 2)]),  # +N flag: fRfBbF2bsW2
    "BU": (DIAG,          [F, B, WL, WR],                   []),                       # +C' crowned bishop: BW
    "DR": (ORTHO,         [FL, FR, BL, BR],                 []),                       # +F' castle: RF
    "FH": (ALL8,          [],                               []),                       # +H' queen: RB
    "PH": ([F, B],        [],                               [(FL, 3), (FR, 3),
                          (BL, 3), (BR, 3), (WL, 2), (WR, 2)]),                        # +X golden bird: F3vRsW2
    "KI": ([WL, WR],      [],                               [(FL, 3), (FR, 3),
                          (BL, 3), (BR, 3), (F, 2), (B, 2)]),                          # +O unicorn: F3sRvW2
    "WO": ([],            [],                               [(F, 3), (B, 3),
                          (FL, 3), (FR, 3), (WL, 5), (WR, 5), (BL, 5), (BR, 5)]),      # +W! elephant: vW3fF3sW5bF5
    # VI->wolf, HU->lion, KT->goblin, VP->hook mover, LN->berserker : special.
}
# 12 promotable base types (everything else, incl. Pawns, never promotes).
CAN_PROMOTE = frozenset(["N", "BU", "DR", "FH", "PH", "KI",
                         "VI", "HU", "KT", "VP", "WO", "LN"])

# Rough material values (heuristic only; both Kings always present).
VALS = {"P": 1, "BU": 2, "S": 3, "G": 4, "FL": 3, "TI": 4, "BE": 4, "N": 5,
        "LA": 3, "GU": 4, "DR": 4, "KT": 5, "VP": 4, "PH": 6, "KI": 6, "FH": 6,
        "VI": 7, "HU": 7, "LG": 6, "RG": 6, "LC": 6, "RC": 6, "BG": 8, "DG": 8,
        "WO": 12, "LN": 14, "K": 0}
PVALS = {"N": 9, "BU": 6, "DR": 8, "FH": 14, "PH": 10, "KI": 10,
         "VI": 12, "HU": 14, "KT": 9, "VP": 9, "WO": 18, "LN": 20}

# Black's setup, rows 0-4 (White = the 180-degree rotation). Extracted from the
# CVP interactive-diagram config squares AND confirmed rank-by-rank against
# HaChu's own printed initial FEN.
#  rank 1 (row 0): a1..m1
ROW0 = ["LA", "KT", "BU", "BU", "FH", "LG", "K", "RG", "FH", "DR", "DR", "VP", "LA"]
#  rank 2 (row 1): a2..m2
ROW1 = ["BG", "KT", "LN", "PH", "PH", "G", "N", "G", "KI", "KI", "WO", "VP", "DG"]
#  rank 3 (row 2): a3..m3
ROW2 = ["LC", "BE", "VI", "FL", "S", "TI", "N", "TI", "S", "FL", "HU", "BE", "RC"]
#  Pawns fill rank 4 (row 3); Guns on d5,j5 (row 4).
GUNS = (3, 9)                                                # d5, j5 (col 3, 9)

# Which back-rank squares carry an ALREADY-PROMOTED partner (a promoted form
# placed in the initial array). Keyed by (col, row) in Black's frame; the base
# letter here is the *unpromoted* type whose promoted form sits on that square.
#   b1 goblin(=KT+), c1 crowned bishop(=BU+), e1 queen(=FH+), j1 castle(=DR+),
#   l1 hook mover(=VP+); d2 golden bird(=PH+), g3 flag(=N+); j2 unicorn(=KI+).
PROMOTED0 = {(1, 0), (2, 0), (4, 0), (9, 0), (11, 0), (3, 1), (9, 1), (6, 2)}
# NOTE: ROW0/ROW1/ROW2 store the *base* letter on those squares; the promoted
# flag comes from PROMOTED0. (b1 base KT -> goblin, c1 base BU -> crowned
# bishop, e1 base FH -> queen, j1 base DR -> castle, l1 base VP -> hook mover,
# d2 base PH -> golden bird, j2 base KI -> unicorn, g3 base N -> flag.)
# The promotable partner sits on the ADJACENT square: d1 butterfly (-> crowned
# bishop), k1 dragon (-> castle) start UNPROMOTED. (Matches HaChu's initial FEN
# and Muller's diagram: c1 Crowned Bishop / d1 Butterfly, j1 Castle / k1 Dragon.)


@dataclass
class CashewState(SState):
    winner: object = None      # seat that removed the opponent's King
    key: str = ""              # cached repetition key


class CashewShogi(ShogiLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Cashew Shogi"

    WIDTH = HEIGHT = 13
    PLY_CAP = 600
    LABELS = {
        "FL": "Lp", "TI": "Ti", "BE": "Be", "LG": "gL", "RG": "gR", "LA": "La",
        "GU": "Gn", "LC": "cL", "RC": "cR", "BG": "Bg", "DG": "Dg", "N": "Co",
        "BU": "Bf", "DR": "Dr", "FH": "FH", "PH": "Ph", "KI": "Ki", "VI": "Vk",
        "HU": "Hn", "KT": "Kt", "VP": "Vp", "WO": "Wo", "LN": "Ln",
        "+N": "Fg", "+BU": "CB", "+DR": "Ca", "+FH": "Q", "+PH": "GB",
        "+KI": "Un", "+VI": "Wo", "+HU": "Ln", "+KT": "Gb", "+VP": "HM",
        "+WO": "El", "+LN": "Bk",
    }

    def __init__(self):
        # No reverse-attack maps: Cashew has no check rule (win = King off the
        # board). attacked_squares() (for the selftest) is computed forward.
        pass

    # ---- kind dispatch -----------------------------------------------------
    def _kind(self, letter, promoted):
        """Special-generator tag for (letter, promoted), or None for a plain
        table-driven piece."""
        if not promoted:
            return {"LN": "LION", "WO": "WOLF"}.get(letter)
        return {"LN": "BERSERKER", "HU": "LION", "VI": "WOLF",
                "KT": "GOBLIN", "VP": "HOOK"}.get(letter)

    # ---- primitive generators ----------------------------------------------
    def _slides(self, board, f, pl, dirs, fwd):
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in dirs:
            d = (dc * fwd, dr * fwd)
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
            to = (f[0] + dc * fwd, f[1] + dr * fwd)
            if not self.on(*to):
                continue
            occ = board.get(to)
            if occ is not None and occ[0] == pl:
                continue
            yield f"{fs}>{to[0]},{to[1]}"
        for (dc, dr), n in ranged:
            d = (dc * fwd, dr * fwd)
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

    def _lion_moves(self, board, f, pl):
        """Standard chu/dai Lion (no Lion-trading restrictions in Dai Dai): up
        to two king steps per turn (may change direction), first step may jump.
          ``f>t``   adjacent step (dist 1) or direct 2-leap (dist 2, jumps),
          ``f>m>f`` igui (m enemy) or out-and-back pass (m empty),
          ``f>m>t`` double capture / hit-and-run (m enemy, t != m,f)."""
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in BOX2:
            t = (f[0] + dc, f[1] + dr)
            if not self.on(*t):
                continue
            occ = board.get(t)
            if occ is not None and occ[0] == pl:
                continue
            yield f"{fs}>{t[0]},{t[1]}"
        for (dc, dr) in ALL8:
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
            for (dc2, dr2) in ALL8:
                t = (m[0] + dc2, m[1] + dr2)
                if not self.on(*t) or t == f:
                    continue
                occ_t = board.get(t)
                if occ_t is not None and occ_t[0] == pl:
                    continue
                yield f"{fs}>{ms}>{t[0]},{t[1]}"             # double / hit-run

    def _wolf_moves(self, board, f, pl):
        """Wolf = Dai Dai 'Lion Dog': up to three king steps along ONE ray,
        may jump over anything, annihilating enemies it passes. Encodings list
        every captured square before the landing square:
          ``f>s`` (jump/step, capturing s if enemy),
          ``f>s2>s1`` (land s1, also kill s2), ``f>s1>s2`` (kill s1, land s2),
          ``f>s1>f`` (igui: kill adjacent, stay), ``f>n>f`` (pass via empty n),
          ``f>s1>s2>s3`` etc. -- see rules.md for the full worked list."""
        fs = f"{f[0]},{f[1]}"
        # a single canonical pass, if any neighbour is empty
        for (dc, dr) in ALL8:
            n = (f[0] + dc, f[1] + dr)
            if self.on(*n) and board.get(n) is None:
                yield f"{fs}>{n[0]},{n[1]}>{fs}"
                break
        for (dc, dr) in ALL8:
            s1 = (f[0] + dc, f[1] + dr)
            s2 = (f[0] + 2 * dc, f[1] + 2 * dr)
            s3 = (f[0] + 3 * dc, f[1] + 3 * dr)

            def cls(sq):
                if not self.on(*sq):
                    return "off"
                occ = board.get(sq)
                if occ is None:
                    return "empty"
                return "enemy" if occ[0] != pl else "friend"
            c1, c2, c3 = cls(s1), cls(s2), cls(s3)
            s1s = f"{s1[0]},{s1[1]}"
            s2s = f"{s2[0]},{s2[1]}"
            s3s = f"{s3[0]},{s3[1]}"
            # igui: kill an adjacent enemy without moving
            if c1 == "enemy":
                yield f"{fs}>{s1s}>{fs}"
            # land s1
            if c1 in ("empty", "enemy"):
                yield f"{fs}>{s1s}"
                if c2 == "enemy":                            # land s1, also kill s2
                    yield f"{fs}>{s2s}>{s1s}"
            # land s2
            if c2 in ("empty", "enemy"):
                yield f"{fs}>{s2s}"
                if c1 == "enemy":                            # kill s1 en route
                    yield f"{fs}>{s1s}>{s2s}"
            # land s3
            if c3 in ("empty", "enemy"):
                yield f"{fs}>{s3s}"
                if c1 == "enemy":
                    yield f"{fs}>{s1s}>{s3s}"
                if c2 == "enemy":
                    yield f"{fs}>{s2s}>{s3s}"
                if c1 == "enemy" and c2 == "enemy":
                    yield f"{fs}>{s1s}>{s2s}>{s3s}"

    def _perp(self, d):
        return [(-d[1], d[0]), (d[1], -d[0])]

    def _hook_moves(self, board, f, pl, dirs):
        """Bent rider: slide (blockable) along a ray, and from any empty square
        on that ray turn 90 degrees once and slide again. ``dirs`` = ORTHO for
        the Hook Mover, DIAG for the Goblin. Encoding ``f>pivot>dest`` for a
        bent move (pivot is always empty); ``f>dest`` for a straight move."""
        fs = f"{f[0]},{f[1]}"
        for d in dirs:
            cc = (f[0] + d[0], f[1] + d[1])
            pivots = []
            while self.on(*cc):
                occ = board.get(cc)
                if occ is None:
                    yield f"{fs}>{cc[0]},{cc[1]}"
                    pivots.append(cc)
                    cc = (cc[0] + d[0], cc[1] + d[1])
                else:
                    if occ[0] != pl:
                        yield f"{fs}>{cc[0]},{cc[1]}"
                    break
            for pv in pivots:
                pvs = f"{pv[0]},{pv[1]}"
                for d2 in self._perp(d):
                    cc = (pv[0] + d2[0], pv[1] + d2[1])
                    while self.on(*cc):
                        occ = board.get(cc)
                        if occ is None:
                            yield f"{fs}>{pvs}>{cc[0]},{cc[1]}"
                            cc = (cc[0] + d2[0], cc[1] + d2[1])
                        else:
                            if occ[0] != pl:
                                yield f"{fs}>{pvs}>{cc[0]},{cc[1]}"
                            break

    def _piece_moves(self, state, f, pl, letter, promd, fwd):
        board = state.board
        k = self._kind(letter, promd)
        if k is None:
            yield from self._plain_moves(board, f, pl, letter, promd, fwd)
        elif k == "LION":
            yield from self._lion_moves(board, f, pl)
        elif k == "BERSERKER":
            yield from self._lion_moves(board, f, pl)
            for (dc, dr) in ALL8:                            # slide up to 3
                cc = f
                for _ in range(3):
                    cc = (cc[0] + dc, cc[1] + dr)
                    if not self.on(*cc):
                        break
                    occ = board.get(cc)
                    if occ is None:
                        yield f"{f[0]},{f[1]}>{cc[0]},{cc[1]}"
                    else:
                        if occ[0] != pl:
                            yield f"{f[0]},{f[1]}>{cc[0]},{cc[1]}"
                        break
        elif k == "WOLF":
            yield from self._wolf_moves(board, f, pl)
        elif k == "GOBLIN":
            yield from self._hook_moves(board, f, pl, DIAG)
            fs = f"{f[0]},{f[1]}"
            for (dc, dr) in ORTHO:                           # extra W step
                t = (f[0] + dc, f[1] + dr)
                if self.on(*t) and (board.get(t) or (None,))[0] != pl:
                    yield f"{fs}>{t[0]},{t[1]}"
        elif k == "HOOK":
            yield from self._hook_moves(board, f, pl, ORTHO)

    # ---- move generation (with de-dup) -------------------------------------
    def _moves(self, state):
        board, pl = state.board, state.to_move
        fwd = self._fwd(pl)
        seen = set()
        for sq, (p, letter) in list(board.items()):
            if p != pl:
                continue
            promd = sq in state.promoted
            for m in self._piece_moves(state, sq, pl, letter, promd, fwd):
                if m not in seen:
                    seen.add(m)
                    yield m

    # ---- Game interface ----------------------------------------------------
    def setup_board(self):
        b = {}
        for c, t in enumerate(ROW0):
            b[(c, 0)] = (BLACK, t)
        for c, t in enumerate(ROW1):
            b[(c, 1)] = (BLACK, t)
        for c, t in enumerate(ROW2):
            b[(c, 2)] = (BLACK, t)
        for c in range(self.WIDTH):
            b[(c, 3)] = (BLACK, "P")
        for c in GUNS:
            b[(c, 4)] = (BLACK, "GU")
        promoted = set(PROMOTED0)                             # Black promoted partners
        # mirror to White (180-degree rotation) + mirror the promoted set
        for (c, r), (p, t) in list(b.items()):
            mc, mr = self.WIDTH - 1 - c, self.HEIGHT - 1 - r
            b[(mc, mr)] = (WHITE, t)
            if (c, r) in PROMOTED0:
                promoted.add((mc, mr))
        return b, promoted

    def initial_state(self, options=None, rng=None):
        board, promoted = self.setup_board()
        st = CashewState(board=board, promoted=frozenset(promoted),
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
        # stalemate: the side to move has no move and loses
        return [-1.0, 1.0] if state.to_move == BLACK else [1.0, -1.0]

    def apply_move(self, state, move, rng=None):
        cells = [cell(p) for p in move.split(">")]
        f = cells[0]
        land = cells[-1]
        b = dict(state.board)
        prom = set(state.promoted)
        pl, letter = b.pop(f)
        was_prom = f in state.promoted
        prom.discard(f)
        captured = False
        # capture every listed intermediate square that holds an enemy
        for c in cells[1:-1]:
            occ = b.get(c)
            if occ is not None and occ[0] != pl:
                b.pop(c)
                prom.discard(c)
                captured = True
        # landing square (may be the origin for a pass/igui)
        if land != f:
            occ = b.get(land)
            if occ is not None and occ[0] != pl:
                prom.discard(land)
                captured = True
            b[land] = (pl, letter)
        else:
            b[land] = (pl, letter)
        # promoted-flag bookkeeping + forced promotion on capture
        prom.discard(land)
        if was_prom:
            prom.add(land)
        elif captured and letter in CAN_PROMOTE:
            prom.add(land)

        # win as event: a King left the board
        winner = state.winner
        has_bk = any(p == BLACK and t == "K" for (p, t) in b.values())
        has_wk = any(p == WHITE and t == "K" for (p, t) in b.values())
        if not has_bk:
            winner = WHITE
        elif not has_wk:
            winner = BLACK

        st = CashewState(board=b, promoted=frozenset(prom),
                         hands={BLACK: {}, WHITE: {}}, to_move=1 - pl,
                         ply=state.ply + 1, reps=dict(state.reps), winner=winner)
        st.key = self._poskey(st)
        st.reps[st.key] = st.reps.get(st.key, 0) + 1
        return st

    # ---- attacks (forward, for the selftest -- NOT used by the live rules) --
    def attacked_squares(self, state, by):
        """Set of opponent-occupied squares that side ``by`` can remove this
        turn, computed FORWARD from the same move generator."""
        probe = CashewState(board=dict(state.board),
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

    def deserialize(self, d) -> CashewState:
        base = super().deserialize(d)
        st = CashewState(board=base.board, promoted=base.promoted, hands=base.hands,
                         to_move=base.to_move, ply=base.ply, reps=base.reps,
                         winner=d.get("winner"))
        st.key = self._poskey(st)
        return st

    # ---- bot heuristic -----------------------------------------------------
    def heuristic(self, state):
        bal = 0.0
        for sq, (p, t) in state.board.items():
            v = (PVALS if sq in state.promoted else VALS).get(t, 4.0)
            bal += v if p == BLACK else -v
        score = math.tanh(bal / 40.0)
        return [score, -score]

    # ---- presentation ------------------------------------------------------
    def _label(self, letter, promoted):
        key = ("+" + letter) if promoted else letter
        return self.LABELS.get(key, letter)

    def describe_move(self, state, move) -> str:
        parts = move.split(">")
        f = cell(parts[0])
        _, t = state.board.get(f, (None, "?"))
        tag = self._label(t, f in state.promoted)
        dest = parts[-1]
        capset = [p for p in parts[1:] if cell(p) in state.board]
        sep = "x" if capset else "-"
        promo = ""
        if t in CAN_PROMOTE and f not in state.promoted and capset:
            promo = "+"
        if cell(dest) == f:
            if capset:
                return f"{tag}{parts[0]}x!{capset[0]}"          # igui
            return f"{tag}{parts[0]} pass"
        return f"{tag}{parts[0]}{sep}{dest}{promo}"

    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": p,
             "label": self._label(t, (c, r) in state.promoted)}
            for (c, r), (p, t) in state.board.items()
        ]
        names = {BLACK: "Sente (Black)", WHITE: "Gote (White)"}
        if state.winner is not None:
            caption = f"{names[state.winner]} wins — enemy King captured"
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
