"""Sho Shogi (小将棋, "small / old shogi") -- the 16th-century immediate
predecessor of modern Shogi, on the same 9x9 board and setup, but with two
differences:

  * an extra **Drunk Elephant** (E) sits in front of each king, and it promotes
    to a **Crown Prince** (+E) that acts as a *second king*; and
  * there are **NO drops** -- captured pieces leave play permanently (the drop
    rule was Shogi's later innovation, introduced around the same time the
    Emperor Go-Nara removed the Drunk Elephant, giving rise to modern shogi).

Everything else is modern shogi, so this reuses ``agp.shogilike`` unchanged for
the standard pieces P/L/N/S/G/K/R/B, colour-relative movement, zone promotion,
attack maps and check. The Drunk Elephant / Crown Prince are added *entirely in
this subclass* (shadowed movement tables + reverse-attack maps), without editing
the shared core.

Sources (implementation-grade, followed exactly; sources override any brief):
  * https://en.wikipedia.org/wiki/Sho_shogi   (setup, pieces, promotion,
    check/mate with the "sole royal" rule, bare-king win, sennichite draw)
  * https://www.chessvariants.com/shogivariants.dir/shoshogi.html
    (Steve Evans' reconstruction; the bare-king rule + its mutual-bare draw
    exception).

Dual royalty (the crux): a player has one or two ROYAL pieces -- the King, plus
a Crown Prince if the Drunk Elephant promoted. A player is "in check" iff EVERY
one of their royals is attacked; a move is illegal iff it leaves the mover in
check. Thus while both royals live, either may be legally left to be captured --
you must take BOTH to win by capture. Checkmate/stalemate of the side to move is
a loss (as in shogi). See rules.md for the full write-up.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from agp.shogilike import (ShogiLike, SState, BLACK, WHITE, cell, KING,
                           BASE_MOVE as _STD_BASE, PROMO_MOVE as _STD_PROMO)

# Drunk Elephant: one step in any of the 8 king directions EXCEPT straight
# backward -- King's offsets minus (0,-1) (straight back in the forward frame).
ELEPHANT = [d for d in KING if d != (0, -1)]

# Shadowed movement tables: the standard shogi pieces + the two new letters.
BASE_MOVE = dict(_STD_BASE)
BASE_MOVE["E"] = ([], ELEPHANT)                 # Drunk Elephant (leaper, no back)
PROMO_MOVE = dict(_STD_PROMO)
PROMO_MOVE["E"] = ([], list(KING))              # Crown Prince: moves as a King

BACK = ["L", "N", "S", "G", "K", "G", "S", "N", "L"]


@dataclass
class ShoState(SState):
    winner: object = None      # None | 0 (Black) | 1 (White) | "draw"


class ShoShogi(ShogiLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Sho Shogi"

    WIDTH = HEIGHT = 9
    ZONE = 3
    PLY_CAP = 400
    CAN_PROMOTE = ("P", "L", "N", "S", "R", "B", "E")
    LABELS = {
        "K": "K", "R": "R", "B": "B", "G": "G", "S": "S", "N": "N", "L": "L",
        "P": "P", "E": "DE",
        "+R": "+R", "+B": "+B", "+S": "+S", "+N": "+N", "+L": "+L", "+P": "+P",
        "+E": "CP",            # Crown Prince (a second royal)
    }

    # Rough material values for the MCTS rollout cutoff (standard-shogi scale).
    _VAL = {"P": 1, "L": 3, "N": 3, "S": 5, "G": 6, "E": 5, "B": 8, "R": 10,
            "K": 0}
    _PVAL = {"P": 6, "L": 6, "N": 6, "S": 6, "E": 6, "B": 10, "R": 12}

    def __init__(self):
        # Per-colour reverse-attack maps built from the SHADOWED tables (so E/+E
        # are included for both colours) -- mirrors ShogiLike.__init__.
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        kinds = [(L, False) for L in BASE_MOVE] + [(L, True) for L in PROMO_MOVE]
        for pl in (BLACK, WHITE):
            fwd = 1 if pl == BLACK else -1
            for (letter, prom) in kinds:
                slides, leaps = self._move_table(letter, prom)
                for (dc, dr) in leaps:
                    off = (dc, dr * fwd)
                    self._leap_att[pl].setdefault((-off[0], -off[1]), set()).add((letter, prom))
                for (dc, dr) in slides:
                    d = (dc, dr * fwd)
                    self._slide_att[pl].setdefault((-d[0], -d[1]), set()).add((letter, prom))

    @staticmethod
    def _move_table(letter, promoted):
        return PROMO_MOVE[letter] if promoted else BASE_MOVE[letter]

    # ---- movement (override to consult the shadowed tables) ----------------
    def _piece_targets(self, board, sq, pl, letter, promoted):
        c, r = sq
        fwd = self._fwd(pl)
        slides, leaps = self._move_table(letter, promoted)
        for (dc, dr) in leaps:
            t = (c + dc, r + dr * fwd)
            if self.on(*t) and (board.get(t) or (None,))[0] != pl:
                yield t
        for (dc, dr) in slides:
            step_r = dr * fwd
            cc, rr = c + dc, r + step_r
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is None:
                    yield (cc, rr)
                else:
                    if occ[0] != pl:
                        yield (cc, rr)
                    break
                cc += dc
                rr += step_r

    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted or letter not in self.CAN_PROMOTE:
            return [False]
        if not (self.in_zone(pl, frm_r) or self.in_zone(pl, to_r)):
            return [False]
        # mandatory only when the piece would otherwise be stuck (never for E).
        if letter in ("P", "L") and self._last_rank(pl, to_r):
            return [True]
        if letter == "N" and self._last_two(pl, to_r):
            return [True]
        return [False, True]

    # ---- dual royalty ------------------------------------------------------
    def _royals(self, board, promoted, pl):
        return [sq for sq, (p, t) in board.items()
                if p == pl and (t == "K" or (t == "E" and sq in promoted))]

    def _alive(self, board, promoted, pl) -> bool:
        return bool(self._royals(board, promoted, pl))

    def in_check(self, board, promoted, pl) -> bool:
        """In check iff the player has >=1 royal AND every royal is attacked."""
        royals = self._royals(board, promoted, pl)
        if not royals:
            return False
        enemy = 1 - pl
        return all(self.attacked(board, promoted, sq, enemy) for sq in royals)

    def _bare(self, board, promoted, pl) -> bool:
        """pl is reduced to only royal piece(s) -- a 'bare' king/prince."""
        royal = nonroyal = 0
        for sq, (p, t) in board.items():
            if p != pl:
                continue
            if t == "K" or (t == "E" and sq in promoted):
                royal += 1
            else:
                nonroyal += 1
        return royal >= 1 and nonroyal == 0

    # ---- no drops ----------------------------------------------------------
    def _drop_moves(self, state):
        return []

    # ---- Game interface ----------------------------------------------------
    def setup_board(self):
        b = {}
        for c in range(9):
            b[(c, 0)] = (BLACK, BACK[c])
            b[(c, 2)] = (BLACK, "P")
            b[(c, 6)] = (WHITE, "P")
            b[(c, 8)] = (WHITE, BACK[c])
        b[(1, 1)] = (BLACK, "B")
        b[(7, 1)] = (BLACK, "R")
        b[(4, 1)] = (BLACK, "E")       # Drunk Elephant, in front of the king
        b[(1, 7)] = (WHITE, "R")
        b[(7, 7)] = (WHITE, "B")
        b[(4, 7)] = (WHITE, "E")
        return b, set()

    def initial_state(self, options=None, rng=None):
        board, promoted = self.setup_board()
        st = ShoState(board=board, promoted=frozenset(promoted),
                      hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
        st.reps = {self._poskey(st): 1}
        return st

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        out = []
        for frm, to, promote in self._legal_board_moves(state):
            m = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
            out.append(m + "=+" if promote else m)
        return out                      # no drops in Sho Shogi

    def is_terminal(self, state) -> bool:
        if state.winner is not None or self._draw(state):
            return True
        if not self._alive(state.board, state.promoted, state.to_move):
            return True                 # side to move has no royal (defensive)
        return not self._has_move(state)

    def returns(self, state):
        if state.winner == "draw":
            return [0.0, 0.0]
        if state.winner == BLACK:
            return [1.0, -1.0]
        if state.winner == WHITE:
            return [-1.0, 1.0]
        if self._draw(state):
            return [0.0, 0.0]
        # no legal move / no royal: the side to move loses (mate / stalemate /
        # bared-out are all a loss for the player on the move here).
        return [-1.0, 1.0] if state.to_move == BLACK else [1.0, -1.0]

    def apply_move(self, state, move, rng=None):
        promote = move.endswith("=+")
        if promote:
            move = move[:-2]
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        enemy = 1 - pl
        b = dict(state.board)
        b.pop(frm)
        prom = set(state.promoted)
        prom.discard(frm)
        prom.discard(to)                # a captured piece loses its promoted flag
        if promote or (frm in state.promoted):
            prom.add(to)
        b[to] = (pl, t)                 # NB: no banking to hand -- no drops
        fprom = frozenset(prom)

        winner = self._resolve(state, b, fprom, pl, enemy)

        st = ShoState(board=b, promoted=fprom, hands={BLACK: {}, WHITE: {}},
                      to_move=enemy, ply=state.ply + 1, reps=dict(state.reps),
                      winner=winner)
        key = self._poskey(st)
        st.reps[key] = st.reps.get(key, 0) + 1
        return st

    def _resolve(self, state, board, promoted, mover, enemy):
        """Win-as-event after ``mover``'s move produced ``board``/``promoted``.

        Returns None (game continues), a seat, or "draw":
          * royal annihilation -- the opponent has no royal left -> mover wins;
          * bare-king rule -- baring the opponent (reducing them to only
            royal pieces) wins, but the bared player gets its immediately
            following move to bare back for a DRAW (else the barer wins).
        """
        # 1) royal annihilation (defensive: the sole royal is normally protected
        #    by the legal-move filter and so is never actually capturable).
        if not self._alive(board, promoted, enemy):
            return mover

        # 2) bare-king rule.
        pre = state.promoted
        mover_pre_bared = (self._bare(state.board, pre, mover)
                           and not self._bare(state.board, pre, enemy))
        opp_bare_now = self._bare(board, promoted, enemy)
        if mover_pre_bared:
            # this move IS the bared player's 'following move' chance.
            return "draw" if opp_bare_now else enemy
        if opp_bare_now:
            if self._bare(board, promoted, mover):
                return "draw"           # both bare at once -> mutual bare
            return None                 # defer: the opponent gets one reply
        return None

    # ---- (de)serialise -----------------------------------------------------
    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["winner"] = state.winner
        return d

    def deserialize(self, d) -> ShoState:
        base = super().deserialize(d)
        return ShoState(board=base.board, promoted=base.promoted,
                        hands=base.hands, to_move=base.to_move, ply=base.ply,
                        reps=base.reps, winner=d.get("winner"))

    # ---- bot heuristic -----------------------------------------------------
    def heuristic(self, state):
        bal = 0.0
        for sq, (p, t) in state.board.items():
            v = (self._PVAL if sq in state.promoted else self._VAL).get(t, 1)
            bal += v if p == BLACK else -v
        s = math.tanh(bal / 30.0)
        return [s, -s]

    # ---- presentation ------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": p,
             "label": self._label(t, (c, r) in state.promoted)}
            for (c, r), (p, t) in state.board.items()
        ]
        names = {BLACK: "Sente (Black)", WHITE: "Gote (White)"}
        if self.is_terminal(state):
            ret = self.returns(state)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins"
        elif self.in_check(state.board, state.promoted, state.to_move):
            caption = f"{names[state.to_move]} to move (check)"
        else:
            caption = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
