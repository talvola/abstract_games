"""Chu Shogi (中将棋, "middle shogi") -- the classic 12x12 Japanese large-shogi
variant: 46 pieces a side of 21 types, no drops, no check rules, the famous
double-moving Lion, and the traditional Lion-trading restrictions.

Primary source (implementation-grade, followed exactly):
https://en.wikipedia.org/wiki/Chu_shogi -- the ruleset HaChu (H.G. Muller's
reference engine) implements by default. Cross-checked against
https://www.chessvariants.com/rules/chu-shogi (Muller/DeWitt).

Rules implemented (see rules.md for the full write-up):

* **Win by royal annihilation** -- capture ALL the opponent's royals: the King,
  plus the Prince if a Drunk Elephant promoted. There is no check/checkmate
  rule; moving into or ignoring "check" is legal. The win is stored in the
  state (``winner``) when the last royal is captured. A player with no legal
  move (unreachable in practice) loses, per CVP's "stalemate is a win"
  convention.
* **Lion** (and promoted Kirin, which is a Lion in every respect): direct leap
  to any square within a distance of 2 (the 5x5 box), or two king steps per
  turn with capture on both (double capture), capture-without-moving (igui),
  or an out-and-back turn pass (jitto, needs an empty adjacent square).
  Move encoding follows the platform convention (Elven Chess's Warlock):
  ``f>m>m`` adjacent step, ``f>t`` distance-2 leap, ``f>m>t`` double move
  (enemy on ``m``; ``t`` may equal ``f`` = igui), ``f>m>f`` with ``m`` empty =
  pass.
* **Horned Falcon / Soaring Eagle** (promoted Dragon Horse / Dragon King):
  sliders plus the same Lion power restricted to straight forward (Falcon) /
  the two forward diagonals (Eagle), each leg staying on the same ray.
* **Lion-trading rules** (traditional / Wikipedia, HaChu's default):
  1. a Lion may not capture a non-adjacent (distance-2) enemy Lion if the
     capturing Lion could be recaptured in the resulting position (evaluated
     AFTER the move, so X-ray "hidden protectors" count and capturing the
     protector en route legalises the capture), unless the double move also
     captures a piece other than an unpromoted Pawn or Go-Between (tsukegui);
     hypothetical recaptures ignore the Lion rules (non-recursive reading).
  2. counterstrike: after a non-Lion captures a Lion, the opponent may not
     reply by capturing a Lion with a non-Lion, except on the very square of
     the first capture (which allows shooting a Kirin that promoted to Lion
     while capturing one). One-turn state: ``ChuState.counter``.
  The Okazaki variant (counterstrike allowed vs an unprotected Lion) is NOT
  implemented.
* **Promotion** (zone = far four ranks, always optional, ``=+`` suffix):
  on a non-capture only when ENTERING the zone; once inside, only on a
  capture (any move that captures with either end in the zone) or by leaving
  and re-entering. Exception: a Pawn reaching the last rank gets one extra
  non-capture chance. Declined last-rank Pawns/Lances become immobile "dead
  pieces". Promotion is permanent; a piece promotes at most once.
* **Draws**: fourfold repetition of position+side-to-move(+counterstrike flag)
  or the hard ply cap -> an honest draw. The JCSA's asymmetric repetition
  rules and bare-king rule are simplifications documented in rules.md.
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
# letter -> (slides, leaps); the Lion ("N", and promoted "O") is fully custom,
# and the Falcon/Eagle Lion powers are added on top of their slides.
BASE_MOVE = {
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
}
# Extra ATTACK reach beyond the movement tables: Lion powers hit through
# blockers (a leap), so for recapture tests they are plain leap offsets.
POWER_ATT = {
    ("N", False): BOX2,
    ("O", True): BOX2,
    ("H", True): [(0, 1), (0, 2)],
    ("D", True): [(-1, 1), (1, 1), (-2, 2), (2, 2)],
}

# German Chu Shogi Association average piece values (via Wikipedia).
VALS = {"P": 1, "I": 1, "C": 2, "S": 2, "T": 3, "F": 3, "G": 3, "E": 3, "A": 3,
        "L": 3, "O": 3, "X": 3, "V": 4, "M": 4, "K": 4, "B": 5, "R": 6, "H": 7,
        "D": 8, "Q": 12, "N": 20}
PVALS = {"P": 3, "I": 3, "C": 4, "S": 4, "T": 6, "F": 5, "G": 6, "E": 4, "A": 5,
         "L": 7, "O": 20, "X": 12, "V": 8, "M": 8, "B": 7, "R": 8, "H": 10, "D": 11}

# Black's setup, rows 0-4 (White = the 180-degree rotation). Verified against
# the Wikipedia setup diagram.
ROW0 = ["L", "F", "C", "S", "G", "K", "E", "G", "S", "C", "F", "L"]
ROW1 = {0: "A", 2: "B", 4: "T", 5: "O", 6: "X", 7: "T", 9: "B", 11: "A"}
ROW2 = ["M", "V", "R", "H", "D", "N", "Q", "D", "H", "R", "V", "M"]


@dataclass
class ChuState(SState):
    counter: tuple = ()        # squares where a Lion was just captured by a non-Lion
    winner: object = None      # seat that captured the opponent's last royal
    key: str = ""              # cached repetition key (not serialized; recomputed)


class ChuShogi(ShogiLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Chu Shogi"

    WIDTH = HEIGHT = 12
    ZONE = 4
    PLY_CAP = 600
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
        # +P/+I/+C/+S/+G/+F/+R/+B/+A/+L keep the default "+letter" label:
        # they move as Gold/Elephant/SM/VM/Rook/Bishop/DK/DH/Whale/WhiteHorse
        # but, unlike the like-named originals, can never promote (again).
    }

    def __init__(self):
        # Reverse-attack maps per colour (leaps + slides), movement tables plus
        # the Lion-power reach (POWER_ATT). Used only for the Lion-trading
        # rule's recapture test -- there is no check in Chu Shogi.
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        kinds = [(L, False) for L in BASE_MOVE] + [(L, True) for L in PROMO_MOVE]
        for pl in (BLACK, WHITE):
            fwd = 1 if pl == BLACK else -1
            for (letter, prm) in kinds:
                slides, leaps = PROMO_MOVE[letter] if prm else BASE_MOVE[letter]
                for (dc, dr) in list(leaps) + POWER_ATT.get((letter, prm), []):
                    off = (dc, dr * fwd)
                    self._leap_att[pl].setdefault((-off[0], -off[1]), set()).add((letter, prm))
                for (dc, dr) in slides:
                    d = (dc, dr * fwd)
                    self._slide_att[pl].setdefault((-d[0], -d[1]), set()).add((letter, prm))

    # ---- helpers -------------------------------------------------------------
    def _lionish(self, letter, promoted) -> bool:
        """Is this piece a Lion for the Lion-trading rules? (Lion, or promoted
        Kirin -- Wikipedia: 'there is no difference between promoted kirins and
        lions as far as these rules are concerned')."""
        return letter == "N" or (letter == "O" and promoted)

    def _royal(self, letter, promoted) -> bool:
        return letter == "K" or (letter == "E" and promoted)

    def _ctr_ok(self, state, caps) -> bool:
        """Counterstrike rule (rule 2) for a NON-Lion mover: after a Lion was
        captured by a non-Lion, the immediate reply may not capture a Lion with
        a non-Lion, except on the square of that capture. ``caps`` =
        [(square, (owner, letter)), ...] pieces this move would capture."""
        if not state.counter:
            return True
        for sq, occ in caps:
            if self._lionish(occ[1], sq in state.promoted) and sq not in state.counter:
                return False
        return True

    def _lion_cap_ok(self, state, f, t, m, pl) -> bool:
        """Rule 1 for a Lion capturing an enemy Lion on a NON-adjacent square t
        (distance 2 from f). Legal iff the move also captures a substantial
        piece (at m; not an unpromoted Pawn/Go-Between -- tsukegui), or the
        capturing Lion could not be recaptured in the resulting position
        (evaluated post-move: X-ray protectors count, captured protectors
        don't; the hypothetical recapture ignores the Lion rules)."""
        board, prom = state.board, state.promoted
        if m is not None:
            letter = board[m][1]
            if not (letter in ("P", "I") and m not in prom):
                return True
        b = dict(board)
        mover = b.pop(f)
        if m is not None:
            b.pop(m, None)
        b.pop(t, None)
        b[t] = mover
        pr = set(prom)
        pr.discard(f), pr.discard(m), pr.discard(t)
        if f in prom:                       # a promoted Kirin stays promoted
            pr.add(t)
        return not self.attacked(b, pr, t, 1 - pl)

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
            if occ is not None and (occ[0] == pl or not self._ctr_ok(state, [(to, occ)])):
                continue
            yield from self._emit(f, to, letter, promd, pl, occ is not None)
        for (dc, dr) in slides:
            d = (dc, dr * fwd)
            cc, rr = f[0] + d[0], f[1] + d[1]
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is None:
                    yield from self._emit(f, (cc, rr), letter, promd, pl, False)
                else:
                    if occ[0] != pl and self._ctr_ok(state, [((cc, rr), occ)]):
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
        if capture:
            ok = fz or tz                       # a capture touching the zone
        else:
            # non-capture: only on ENTERING the zone -- plus the Pawn's extra
            # last-rank chance (it can never leave the zone or capture back in)
            ok = (not fz and tz) or (letter == "P" and self._last_rank(pl, to[1]))
        if ok:
            yield m + "=+"

    def _lion_moves(self, state, f, pl):
        board, prom = state.board, state.promoted
        fs = f"{f[0]},{f[1]}"
        # direct leaps anywhere in the 5x5 box (jumps over anything)
        for dc, dr in BOX2:
            t = (f[0] + dc, f[1] + dr)
            if not self.on(*t):
                continue
            occ = board.get(t)
            if occ is not None and occ[0] == pl:
                continue
            if max(abs(dc), abs(dr)) == 1:
                yield f"{fs}>{t[0]},{t[1]}>{t[0]},{t[1]}"       # adjacent step
                continue
            if occ is not None and self._lionish(occ[1], t in prom) \
                    and not self._lion_cap_ok(state, f, t, None, pl):
                continue
            yield f"{fs}>{t[0]},{t[1]}"                          # distance-2 leap
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
            # capturing an ADJACENT enemy Lion is never restricted
            for dc2, dr2 in ALL8:
                t = (m[0] + dc2, m[1] + dr2)
                if not self.on(*t):
                    continue
                if t == f:
                    yield f"{fs}>{ms}>{fs}"                      # igui
                    continue
                occ_t = board.get(t)
                if occ_t is not None:
                    if occ_t[0] == pl:
                        continue
                    if self._lionish(occ_t[1], t in prom) \
                            and max(abs(t[0] - f[0]), abs(t[1] - f[1])) == 2 \
                            and not self._lion_cap_ok(state, f, t, m, pl):
                        continue
                yield f"{fs}>{ms}>{t[0]},{t[1]}"

    def _power_moves(self, state, f, pl, dirs, fwd):
        """Falcon/Eagle Lion power: up to two steps along one forward ray --
        step, direct 2-leap, double capture, igui, or an out-and-back pass."""
        board, prom = state.board, state.promoted
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
            elif occ_m[0] != pl and self._ctr_ok(state, [(m, occ_m)]):
                yield f"{fs}>{ms}>{ms}"                          # capture-step
                yield f"{fs}>{ms}>{fs}"                          # igui
            j = (f[0] + 2 * d[0], f[1] + 2 * d[1])
            if not self.on(*j):
                continue
            occ_j = board.get(j)
            js = f"{j[0]},{j[1]}"
            if occ_j is None or occ_j[0] != pl:
                if occ_j is None or self._ctr_ok(state, [(j, occ_j)]):
                    yield f"{fs}>{js}"                           # direct 2-leap
            if occ_m is not None and occ_m[0] != pl and (occ_j is None or occ_j[0] != pl):
                caps = [(m, occ_m)] + ([(j, occ_j)] if occ_j is not None else [])
                if self._ctr_ok(state, caps):
                    yield f"{fs}>{ms}>{js}"                      # double move

    # ---- Game interface ----------------------------------------------------
    def setup_board(self):
        b = {}
        for c, t in enumerate(ROW0):
            b[(c, 0)] = (BLACK, t)
        for c, t in ROW1.items():
            b[(c, 1)] = (BLACK, t)
        for c, t in enumerate(ROW2):
            b[(c, 2)] = (BLACK, t)
        for c in range(12):
            b[(c, 3)] = (BLACK, "P")
        b[(3, 4)] = (BLACK, "I")
        b[(8, 4)] = (BLACK, "I")
        for (c, r), (p, t) in list(b.items()):
            b[(11 - c, 11 - r)] = (WHITE, t)
        return b, set()

    def initial_state(self, options=None, rng=None):
        board, promoted = self.setup_board()
        st = ChuState(board=board, promoted=frozenset(promoted),
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
        mover_lion = self._lionish(letter, was_prom)

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

        # counterstrike flag: a Lion captured by a non-Lion this move
        counter = tuple(sq for (sq, lt, pr) in caps
                        if not mover_lion and self._lionish(lt, pr))
        # win-as-event: capturing the opponent's last royal
        winner = state.winner
        enemy = 1 - pl
        if any(self._royal(lt, pr) for (_, lt, pr) in caps):
            if not any(p == enemy and self._royal(t, sq in prom)
                       for sq, (p, t) in b.items()):
                winner = pl

        st = ChuState(board=b, promoted=frozenset(prom),
                      hands={BLACK: {}, WHITE: {}}, to_move=enemy,
                      ply=state.ply + 1, reps=dict(state.reps),
                      counter=counter, winner=winner)
        st.key = self._poskey(st)
        st.reps[st.key] = st.reps.get(st.key, 0) + 1
        return st

    # ---- keys / (de)serialise ---------------------------------------------
    def _poskey(self, state) -> str:
        parts = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                occ = state.board.get((c, r))
                if occ is None:
                    parts.append(".")
                else:
                    tag = "+" if (c, r) in state.promoted else ""
                    parts.append(tag + (occ[1] if occ[0] == BLACK else occ[1].lower()))
        ctr = ",".join(f"{c}.{r}" for (c, r) in sorted(state.counter))
        return "".join(parts) + f"#{state.to_move}#{ctr}"

    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["counter"] = [f"{c},{r}" for (c, r) in state.counter]
        d["winner"] = state.winner
        return d

    def deserialize(self, d) -> ChuState:
        base = super().deserialize(d)
        st = ChuState(board=base.board, promoted=base.promoted, hands=base.hands,
                      to_move=base.to_move, ply=base.ply, reps=base.reps,
                      counter=tuple(cell(s) for s in d.get("counter", [])),
                      winner=d.get("winner"))
        st.key = self._poskey(st)
        return st

    # ---- bot heuristic -------------------------------------------------------
    def heuristic(self, state):
        """Material balance (German Chu Shogi Association values) squashed to
        (-1, 1); payoffs [Black, White] for the MCTS rollout cutoff."""
        bal = 0.0
        for sq, (p, t) in state.board.items():
            v = (PVALS if sq in state.promoted else VALS).get(t, 3.0)
            bal += v if p == BLACK else -v
        score = math.tanh(bal / 30.0)
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
            if state.counter:
                caption += " — Lion just fell to a non-Lion (counterstrike bars a non-Lion reply on a Lion)"
        return {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
