"""Dai Shogi (大将棋, "large shogi") -- the historical 15x15 Japanese great
shogi from the Kamakura period (~1230 AD), the ancestor of Chu Shogi: 65
pieces a side of 29 types, no drops, no check rules, the double-moving Lion.

Primary source (implementation-grade, followed exactly):
https://en.wikipedia.org/wiki/Dai_shogi -- cross-checked against
https://www.chessvariants.com/rules/dai-shogi (H.G. Muller) and the piece /
variant tables of HaChu 0.21 (Muller's reference engine, which plays Dai).
All three agree on every rule implemented here.

Dai Shogi = Chu Shogi's 21 piece types + 8 weak extra types (Iron General,
Stone General, Knight, Angry Boar, Cat Sword, Evil Wolf, Violent Ox, Flying
Dragon -- all promoting to Gold General), with these rule differences:

* **Promotion zone = the far FIVE ranks** (Chu: four). Same regime: optional,
  offered on ENTERING the zone with any move, or on any capture with either
  end of the move in the zone; leaving and re-entering resets. Promotion is
  permanent; a piece promotes at most once.
* **NO Lion-trading rules.** Wikipedia: "The capture rules in chu shogi do
  not apply in dai shogi." CVP: "It also lacks the refined rules against
  Lion trading." (HaChu gates them on chu only.) Lions capture Lions freely.
* **No last-rank second promotion chance for the Pawn** -- that is a Chu
  refinement motivated by its Lion-trading rules; the Wikipedia Dai article
  explicitly describes unpromoted pawns / stones / irons / knights / lances
  on the last rank as "trapped" (dead pieces) and calls the second chance
  uncertain for Dai. Declining promotion on zone entry is at your own risk.

Everything else follows Chu Shogi (and games/chu_shogi, whose implementation
this reuses): win by capturing ALL royals (King + Prince if a Drunk Elephant
promoted, win-as-event in ``winner``); the Lion's 5x5 leap / two king steps
(double capture, igui, out-and-back turn pass), encoded ``f>m>m`` step,
``f>t`` leap, ``f>m>t`` double move, ``f>m>f`` igui-or-pass; Horned Falcon /
Soaring Eagle Lion power restricted to straight-forward / forward-diagonal
rays; fourfold repetition or the hard ply cap -> an honest draw (the
historical "repetition forbidden" rule is simplified, see rules.md).
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

# ------------------------------------------------------------- move tables
# letter -> (slides, leaps, ranged); ``ranged`` = bounded slides
# [(dc, dr, max_steps), ...] for the range-2 movers (blockable, NOT jumps).
# The Lion ("N", and promoted Kirin "O") is fully custom, and the Falcon /
# Eagle Lion powers are added on top of their slides.
BASE_MOVE = {
    # -- the 21 Chu Shogi types (same letters as games/chu_shogi) ------------
    "K": ([], ALL8),                                   # King (royal)
    "E": ([], [F, FL, FR, WL, WR, BL, BR]),            # Drunk Elephant (no back)
    "T": ([], [B, FL, FR, WL, WR, BL, BR]),            # Blind Tiger (no front)
    "F": ([], [F, B, FL, FR, BL, BR]),                 # Ferocious Leopard
    "G": ([], [F, B, WL, WR, FL, FR]),                 # Gold General
    "S": ([], [F, FL, FR, BL, BR]),                    # Silver General
    "C": ([], [F, FL, FR, B]),                         # Copper General
    "I": ([], [F, B]),                                 # Go-Between
    "P": ([], [F]),                                    # Pawn
    "O": ([], DIAG + [(0, 2), (0, -2), (2, 0), (-2, 0)]),    # Kirin
    "X": ([], ORTHO + [(2, 2), (-2, 2), (2, -2), (-2, -2)]),  # Phoenix
    "Q": (ALL8, []),                                   # Queen (free king)
    "N": ([], []),                                     # Lion -- custom
    "R": (ORTHO, []),                                  # Rook
    "B": (DIAG, []),                                   # Bishop
    "D": (ORTHO, DIAG),                                # Dragon King
    "H": (DIAG, ORTHO),                                # Dragon Horse
    "V": ([F, B], [WL, WR]),                           # Vertical Mover
    "M": ([WL, WR], [F, B]),                           # Side Mover
    "A": ([F, B], []),                                 # Reverse Chariot
    "L": ([F], []),                                    # Lance
    # -- the 8 Dai-only types ------------------------------------------------
    "Ir": ([], [F, FL, FR]),                           # Iron General
    "St": ([], [FL, FR]),                              # Stone General
    "Kt": ([], [(-1, 2), (1, 2)]),                     # Knight (shogi N, jumps)
    "AB": ([], ORTHO),                                 # Angry Boar
    "CS": ([], DIAG),                                  # Cat Sword
    "EW": ([], [F, FL, FR, WL, WR]),                   # Evil Wolf
    "VO": ([], []),                                    # Violent Ox -- ranged
    "FD": ([], []),                                    # Flying Dragon -- ranged
}
# Bounded slides: up to 2 squares, blocked by any piece (no jumping).
RANGED = {
    "VO": [(d, 2) for d in ORTHO],                     # Violent Ox: R2
    "FD": [(d, 2) for d in DIAG],                      # Flying Dragon: B2
}
PROMO_MOVE = {
    "P": ([], [F, B, WL, WR, FL, FR]),                 # -> Gold General
    "I": ([], [F, FL, FR, WL, WR, BL, BR]),            # -> Drunk Elephant
    "C": ([WL, WR], [F, B]),                           # -> Side Mover
    "S": ([F, B], [WL, WR]),                           # -> Vertical Mover
    "G": (ORTHO, []),                                  # -> Rook
    "F": (DIAG, []),                                   # Leopard -> Bishop
    "T": ([F, B], [FL, FR, WL, WR, BL, BR]),           # -> Flying Stag
    "E": ([], ALL8),                                   # -> Prince (2nd royal)
    "A": ([F, B, BL, BR], []),                         # -> Whale
    "L": ([F, FL, FR, B], []),                         # -> White Horse
    "M": ([WL, WR] + DIAG, []),                        # -> Free Boar
    "V": ([F, B] + DIAG, []),                          # -> Flying Ox
    "R": (ORTHO, DIAG),                                # -> Dragon King
    "B": (DIAG, ORTHO),                                # -> Dragon Horse
    "X": (ALL8, []),                                   # Phoenix -> Queen
    "O": ([], []),                                     # Kirin -> Lion -- custom
    "H": ([B, WL, WR, FL, FR, BL, BR], []),            # -> Horned Falcon (+fwd Lion power)
    "D": ([F, B, WL, WR, BL, BR], []),                 # -> Soaring Eagle (+fwd-diag Lion power)
    # the 8 Dai-only types all promote to Gold General
    "Ir": ([], [F, B, WL, WR, FL, FR]),
    "St": ([], [F, B, WL, WR, FL, FR]),
    "Kt": ([], [F, B, WL, WR, FL, FR]),
    "AB": ([], [F, B, WL, WR, FL, FR]),
    "CS": ([], [F, B, WL, WR, FL, FR]),
    "EW": ([], [F, B, WL, WR, FL, FR]),
    "VO": ([], [F, B, WL, WR, FL, FR]),
    "FD": ([], [F, B, WL, WR, FL, FR]),
}

# Material values: the German Chu Shogi Association set (via Wikipedia) for
# the shared types, plus values for the 8 Dai-only pieces scaled to match
# HaChu's relative ordering (VO=FD > EW=Ir > CS > AB=Kt > St).
VALS = {"P": 1, "I": 1, "C": 2, "S": 2, "T": 3, "F": 3, "G": 3, "E": 3, "A": 3,
        "L": 3, "O": 3, "X": 3, "V": 4, "M": 4, "K": 4, "B": 5, "R": 6, "H": 7,
        "D": 8, "Q": 12, "N": 20,
        "St": 1, "AB": 1, "Kt": 1, "CS": 1, "Ir": 2, "EW": 2, "VO": 3, "FD": 3}
PVALS = {"P": 3, "I": 3, "C": 4, "S": 4, "T": 6, "F": 5, "G": 6, "E": 4, "A": 5,
         "L": 7, "O": 20, "X": 12, "V": 8, "M": 8, "B": 7, "R": 8, "H": 10,
         "D": 11,
         "St": 3, "AB": 3, "Kt": 3, "CS": 3, "Ir": 3, "EW": 3, "VO": 3, "FD": 3}

# Black's setup, rows 0-5 (White = the 180-degree rotation). Verified against
# the Wikipedia setup diagram, CVP's interactive-diagram config and HaChu's
# daiArray. Column 0 = HaChu file 'a' (Black's left).
ROW0 = ["L", "Kt", "St", "Ir", "C", "S", "G", "K", "G", "S", "C", "Ir", "St",
        "Kt", "L"]
ROW1 = {0: "A", 2: "CS", 4: "F", 6: "T", 7: "E", 8: "T", 10: "F", 12: "CS",
        14: "A"}
ROW2 = {1: "VO", 3: "AB", 5: "EW", 6: "O", 7: "N", 8: "X", 9: "EW", 11: "AB",
        13: "VO"}
ROW3 = ["R", "FD", "M", "V", "B", "H", "D", "Q", "D", "H", "B", "V", "M",
        "FD", "R"]


@dataclass
class DaiState(SState):
    winner: object = None      # seat that captured the opponent's last royal
    key: str = ""              # cached repetition key (not serialized; recomputed)


class DaiShogi(ShogiLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Dai Shogi"

    WIDTH = HEIGHT = 15
    ZONE = 5
    PLY_CAP = 800
    LABELS = {
        "N": "Ln", "D": "DK", "H": "DH", "O": "Kr", "X": "Ph", "E": "DE",
        "T": "BT", "F": "FL", "V": "VM", "M": "SM", "A": "RC", "I": "GB",
        # promoted forms with a piece identity of their own
        "+E": "Pr",   # Prince (a second royal)
        "+O": "Ln",   # a promoted Kirin IS a Lion, in every respect
        "+X": "Q",    # a promoted Phoenix IS a Queen
        "+H": "HF",   # Horned Falcon
        "+D": "SE",   # Soaring Eagle
        "+T": "FS",   # Flying Stag
        "+M": "FB",   # Free Boar
        "+V": "FO",   # Flying Ox
        # every gold-mover: the pawn and the 8 Dai-only pieces all promote to
        # a Gold General that can never promote again -- movement-identical,
        # so they share the "+G" label (the chu convention: +O->Ln, +X->Q).
        "+P": "+G", "+St": "+G", "+Ir": "+G", "+Kt": "+G", "+AB": "+G",
        "+CS": "+G", "+EW": "+G", "+VO": "+G", "+FD": "+G",
        # ...which frees "+G" itself: a promoted Gold moves as a Rook.
        "+G": "GR",
        # +I/+C/+S/+F/+R/+B/+A/+L keep the default "+letter" label: they move
        # as DrunkElephant/SM/VM/Bishop/DK/DH/Whale/WhiteHorse but, unlike the
        # like-named originals, can never promote (again).
    }

    def __init__(self):
        # No attack maps needed: Dai Shogi has no check rule and no
        # Lion-trading recapture test (unlike Chu).
        pass

    # ---- helpers -------------------------------------------------------------
    def _royal(self, letter, promoted) -> bool:
        return letter == "K" or (letter == "E" and promoted)

    # ---- move generation -------------------------------------------------------
    def _moves(self, state):
        board, pl = state.board, state.to_move
        fwd = self._fwd(pl)
        for sq, (p, t) in board.items():
            if p != pl:
                continue
            promd = sq in state.promoted
            if t == "N" or (t == "O" and promd):
                yield from self._lion_moves(state, sq, pl)
            else:
                yield from self._plain_moves(state, sq, pl, t, promd, fwd)
                if promd and t in ("H", "D"):
                    dirs = [F] if t == "H" else [FL, FR]
                    yield from self._power_moves(state, sq, pl, dirs, fwd)

    def _plain_moves(self, state, f, pl, letter, promd, fwd):
        board = state.board
        slides, leaps = PROMO_MOVE[letter] if promd else BASE_MOVE[letter]
        for (dc, dr) in leaps:
            to = (f[0] + dc, f[1] + dr * fwd)
            if not self.on(*to):
                continue
            occ = board.get(to)
            if occ is not None and occ[0] == pl:
                continue
            yield from self._emit(f, to, letter, promd, pl, occ is not None)
        ranged = () if promd else RANGED.get(letter, ())
        for d, n in ranged:
            cc = f
            for _ in range(n):
                cc = (cc[0] + d[0], cc[1] + d[1] * fwd)
                if not self.on(*cc):
                    break
                occ = board.get(cc)
                if occ is None:
                    yield from self._emit(f, cc, letter, promd, pl, False)
                else:
                    if occ[0] != pl:
                        yield from self._emit(f, cc, letter, promd, pl, True)
                    break
        for (dc, dr) in slides:
            d = (dc, dr * fwd)
            cc, rr = f[0] + d[0], f[1] + d[1]
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is None:
                    yield from self._emit(f, (cc, rr), letter, promd, pl, False)
                else:
                    if occ[0] != pl:
                        yield from self._emit(f, (cc, rr), letter, promd, pl, True)
                    break
                cc += d[0]
                rr += d[1]

    def _emit(self, f, to, letter, promd, pl, capture):
        m = f"{f[0]},{f[1]}>{to[0]},{to[1]}"
        yield m
        if promd or letter not in PROMO_MOVE:
            return
        fz, tz = self.in_zone(pl, f[1]), self.in_zone(pl, to[1])
        # capture: any move touching the zone; non-capture: only on ENTERING.
        # (No last-rank second chance for the Pawn -- a Chu-only refinement;
        # see rules.md. An unpromoted Pawn etc. on the last rank is dead.)
        ok = (fz or tz) if capture else (not fz and tz)
        if ok:
            yield m + "=+"

    def _lion_moves(self, state, f, pl):
        board = state.board
        fs = f"{f[0]},{f[1]}"
        # direct leaps anywhere in the 5x5 box (jumps over anything; there
        # are NO Lion-trading restrictions in Dai Shogi)
        for dc, dr in BOX2:
            t = (f[0] + dc, f[1] + dr)
            if not self.on(*t):
                continue
            occ = board.get(t)
            if occ is not None and occ[0] == pl:
                continue
            if max(abs(dc), abs(dr)) == 1:
                yield f"{fs}>{t[0]},{t[1]}>{t[0]},{t[1]}"       # adjacent step
            else:
                yield f"{fs}>{t[0]},{t[1]}"                      # distance-2 leap
        # double moves: capture an adjacent enemy, then a second king step
        # (double capture / move on / igui), plus the out-and-back turn pass
        for dc, dr in ALL8:
            m = (f[0] + dc, f[1] + dr)
            if not self.on(*m):
                continue
            occ_m = board.get(m)
            ms = f"{m[0]},{m[1]}"
            if occ_m is None:
                yield f"{fs}>{ms}>{fs}"                          # jitto (pass)
                continue
            if occ_m[0] == pl:
                continue
            for dc2, dr2 in ALL8:
                t = (m[0] + dc2, m[1] + dr2)
                if not self.on(*t):
                    continue
                if t == f:
                    yield f"{fs}>{ms}>{fs}"                      # igui
                    continue
                occ_t = board.get(t)
                if occ_t is not None and occ_t[0] == pl:
                    continue
                yield f"{fs}>{ms}>{t[0]},{t[1]}"

    def _power_moves(self, state, f, pl, dirs, fwd):
        """Falcon/Eagle Lion power: up to two steps along one forward ray --
        step, direct 2-leap, double capture, igui, or an out-and-back pass."""
        board = state.board
        fs = f"{f[0]},{f[1]}"
        for (dc, dr) in dirs:
            d = (dc, dr * fwd)
            m = (f[0] + d[0], f[1] + d[1])
            if not self.on(*m):
                continue
            occ_m = board.get(m)
            ms = f"{m[0]},{m[1]}"
            if occ_m is None:
                yield f"{fs}>{ms}>{ms}"                          # single step
                yield f"{fs}>{ms}>{fs}"                          # pass
            elif occ_m[0] != pl:
                yield f"{fs}>{ms}>{ms}"                          # capture-step
                yield f"{fs}>{ms}>{fs}"                          # igui
            j = (f[0] + 2 * d[0], f[1] + 2 * d[1])
            if not self.on(*j):
                continue
            occ_j = board.get(j)
            js = f"{j[0]},{j[1]}"
            if occ_j is None or occ_j[0] != pl:
                yield f"{fs}>{js}"                               # direct 2-leap
            if occ_m is not None and occ_m[0] != pl and (occ_j is None or occ_j[0] != pl):
                yield f"{fs}>{ms}>{js}"                          # double move

    # ---- Game interface ----------------------------------------------------
    def setup_board(self):
        b = {}
        for c, t in enumerate(ROW0):
            b[(c, 0)] = (BLACK, t)
        for c, t in ROW1.items():
            b[(c, 1)] = (BLACK, t)
        for c, t in ROW2.items():
            b[(c, 2)] = (BLACK, t)
        for c, t in enumerate(ROW3):
            b[(c, 3)] = (BLACK, t)
        for c in range(15):
            b[(c, 4)] = (BLACK, "P")
        b[(4, 5)] = (BLACK, "I")
        b[(10, 5)] = (BLACK, "I")
        for (c, r), (p, t) in list(b.items()):
            b[(14 - c, 14 - r)] = (WHITE, t)
        return b, set()

    def initial_state(self, options=None, rng=None):
        board, promoted = self.setup_board()
        st = DaiState(board=board, promoted=frozenset(promoted),
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
        # no legal move at all: the stalemated side (to move) loses
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

        caps = []                                     # [(square, letter, was_promoted)]
        if len(cells) == 2:
            final = cells[1]
            occ = b.pop(final, None)
            if occ is not None:
                caps.append((final, occ[1], final in state.promoted))
                prom.discard(final)
        else:
            m, final = cells[1], cells[2]
            occ = b.pop(m, None)
            if occ is not None:
                caps.append((m, occ[1], m in state.promoted))
                prom.discard(m)
            if final != m and final != f:
                occ = b.pop(final, None)
                if occ is not None:
                    caps.append((final, occ[1], final in state.promoted))
                    prom.discard(final)
        b[final] = (pl, letter)
        if promote or was_prom:
            prom.add(final)

        # win-as-event: capturing the opponent's last royal
        winner = state.winner
        enemy = 1 - pl
        if any(self._royal(lt, pr) for (_, lt, pr) in caps):
            if not any(p == enemy and self._royal(t, sq in prom)
                       for sq, (p, t) in b.items()):
                winner = pl

        st = DaiState(board=b, promoted=frozenset(prom),
                      hands={BLACK: {}, WHITE: {}}, to_move=enemy,
                      ply=state.ply + 1, reps=dict(state.reps),
                      winner=winner)
        st.key = self._poskey(st)
        st.reps[st.key] = st.reps.get(st.key, 0) + 1
        return st

    # ---- keys / (de)serialise ---------------------------------------------
    def _poskey(self, state) -> str:
        # per-cell separator: piece letters are 1-2 chars, so concatenation
        # without a separator would be ambiguous.
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

    def deserialize(self, d) -> DaiState:
        base = super().deserialize(d)
        st = DaiState(board=base.board, promoted=base.promoted, hands=base.hands,
                      to_move=base.to_move, ply=base.ply, reps=base.reps,
                      winner=d.get("winner"))
        st.key = self._poskey(st)
        return st

    # ---- bot heuristic -------------------------------------------------------
    def heuristic(self, state):
        """Material balance squashed to (-1, 1); payoffs [Black, White] for
        the MCTS rollout cutoff."""
        bal = 0.0
        for sq, (p, t) in state.board.items():
            v = (PVALS if sq in state.promoted else VALS).get(t, 3.0)
            bal += v if p == BLACK else -v
        score = math.tanh(bal / 40.0)
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
            if m == tt:                                   # single adjacent step
                sep = "x" if m in state.board else "-"
                return f"{tag}{parts[0]}{sep}{parts[1]}"
            if tt == f:
                if m in state.board:
                    return f"{tag}{parts[0]}x!{parts[1]}"  # igui
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
            caption = f"{names[state.winner]} wins — royals captured"
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
