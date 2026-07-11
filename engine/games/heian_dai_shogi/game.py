"""Heian Dai Shogi (平安大将棋) -- the earliest known large Shogi variant.

Described (alongside Heian shogi) in the *Nichūreki*, a Kamakura-era
encyclopedia drawing on 12th-century sources, where it is simply called
"dai shogi"; it is retrospectively named *Heian* dai shogi to distinguish
it from the later 15x15 dai shogi. 13x13 board, 34 pieces a side in 13
types, NO drops (captured pieces leave play).

The historical record is partial, so parts of the ruleset are a standard
modern reconstruction (see ``rules.md`` for every conjectural point).
As implemented (per Wikipedia "Heian dai shogi", cross-checked against
chessvariants.com/shogivariants.dir/heiandai.html):

* All pieces are simple steppers/riders plus the Shogi knight's jump --
  no Lion-style multi-captures, so the plain :mod:`agp.shogilike` core
  fits; this subclass supplies its own move tables (the Copper, Iron,
  Side Mover and Flying Dragon move DIFFERENTLY here from chu/dai shogi).
* Promotion zone = far 3 ranks; promotion is optional whenever a move
  starts or ends in the zone, except that a Pawn/Lance must promote on
  the last rank and a Knight on the last two. Every promotable piece
  promotes to a Gold General, EXCEPT the Flying Dragon which gains a
  one-square orthogonal step (i.e. becomes a Dragon Horse). The King and
  Gold General do not promote.
* Win by checkmating (capturing) the enemy King -- the shogilike core's
  check/mate machinery -- OR by the historical **bare-king rule**:
  reducing the opponent to a lone King wins immediately, unless the
  bared King can immediately bare you in return, in which case the game
  is drawn at once. The bare-king outcome is a "win as event" stored in
  ``HState.result``.
* Draws: fourfold repetition (sennichite, adjudicated as a draw) and a
  hard ply cap (weak pieces make for long games).

Player 0 = Sente (Black) at the bottom (row 0), advancing toward higher
rows. Letters: K king, G gold, S silver, C copper, I iron, N knight,
L lance, P pawn, M side mover, T fierce tiger, D flying dragon,
F free chariot, B go-between.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from agp.shogilike import ShogiLike, SState, BLACK, WHITE

# ---------------------------------------------------------------- directions
# All in Black's forward frame: forward = +row (toward the enemy).
FW, BK = (0, 1), (0, -1)
WL, WR = (-1, 0), (1, 0)          # sideways (west / east)
FL, FR = (-1, 1), (1, 1)          # diagonally forward
BL, BR = (-1, -1), (1, -1)        # diagonally backward
ORTHO = [FW, BK, WL, WR]
DIAGS = [FL, FR, BL, BR]
ALL8 = ORTHO + DIAGS
GOLD = [FW, BK, WL, WR, FL, FR]   # the promoted move of almost everything

# ---------------------------------------------------------------- move tables
# BASE_MOVE[letter] = (slides, leaps)   -- in Black's forward frame.
BASE_MOVE = {
    # King (gyokusho) -- royal; one step in all 8 directions.
    "K": ([], ALL8),
    # Gold General -- 4 orthogonal + 2 diagonally-forward steps.
    "G": ([], GOLD),
    # Silver General -- 4 diagonal + straight-forward steps.
    "S": ([], [FL, FR, BL, BR, FW]),
    # Copper General -- "does not move to the four corners": the 4 orthogonal
    # steps only (a wazir; NOT the chu-shogi copper).
    "C": ([], ORTHO),
    # Iron General -- "does not move to the three rear directions": the 3
    # forward + 2 sideways steps (the evil-wolf move; NOT the chu-shogi iron).
    "I": ([], [FL, FW, FR, WL, WR]),
    # Fierce Tiger -- one step on each diagonal.
    "T": ([], DIAGS),
    # Go-Between -- one step straight forward or backward.
    "B": ([], [FW, BK]),
    # Pawn -- one step straight forward.
    "P": ([], [FW]),
    # Knight -- the two forward shogi-knight jumps (leaps over anything).
    "N": ([], [(-1, 2), (1, 2)]),
    # Lance -- ranges straight forward.
    "L": ([FW], []),
    # Side Mover -- ranges sideways; steps one straight forward. (No backward
    # step, unlike the chu-shogi side mover.)
    "M": ([WL, WR], [FW]),
    # Flying Dragon -- ranges on all four diagonals (a bishop; NOT the
    # chu-shogi flying dragon).
    "D": (DIAGS, []),
    # Free Chariot -- ranges straight forward and backward.
    "F": ([FW, BK], []),
}

# Everything promotes to a Gold General, except the Flying Dragon, which gains
# a one-square orthogonal step (= the Dragon Horse). King and Gold do not
# promote.
PROMO_MOVE = {L: ([], GOLD) for L in "SCITBPNLMF"}
PROMO_MOVE["D"] = (DIAGS, ORTHO)          # Dragon Horse: bishop + wazir step

CAN_PROMOTE = frozenset(PROMO_MOVE)


def _movement(letter, promoted):
    return PROMO_MOVE[letter] if promoted else BASE_MOVE[letter]


@dataclass
class HState(SState):
    # Bare-king adjudication ("win as event"): None while the game runs,
    # BLACK/WHITE for a bare-king win, or "draw" for a mutual baring.
    result: object = None


class HeianDaiShogi(ShogiLike):
    # uid comes from the manifest; do not hardcode it here.
    name = "Heian Dai Shogi"

    WIDTH = HEIGHT = 13
    ZONE = 3
    PLY_CAP = 600
    LABELS = {
        "K": "K", "G": "G", "S": "S", "C": "C", "I": "I", "N": "N",
        "L": "L", "P": "P",
        "M": "SM",   # Side Mover
        "T": "FT",   # Fierce Tiger
        "D": "FD",   # Flying Dragon
        "F": "FC",   # Free Chariot
        "B": "GB",   # Go-Between
        # promoted pieces move as a Gold ("+X"), except the Dragon Horse
        "+D": "DH",
    }
    # Rough material values for the MCTS rollout-cutoff heuristic.
    PIECE_VALUES = {
        "P": 1.0, "B": 1.0, "N": 1.5, "T": 2.0, "C": 2.0, "L": 2.0,
        "I": 2.5, "S": 3.0, "G": 3.5, "M": 4.0, "F": 4.0, "D": 5.0,
        "K": 0.0,
    }
    GOLD_VALUE = 3.5
    HORSE_VALUE = 7.0

    # ---- attack maps built from OUR tables (base __init__ reads the plain
    # shogi tables in agp.shogilike) ------------------------------------------
    def __init__(self):
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        kinds = [(L, False) for L in BASE_MOVE] + [(L, True) for L in PROMO_MOVE]
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

    # ---- movement (same shape as the base, but over OUR tables) -------------
    def _piece_targets(self, board, sq, pl, letter, promoted):
        c, r = sq
        fwd = self._fwd(pl)
        slides, leaps = _movement(letter, promoted)
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

    # ---- promotion -----------------------------------------------------------
    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted or letter not in CAN_PROMOTE:
            return [False]
        if not (self.in_zone(pl, frm_r) or self.in_zone(pl, to_r)):
            return [False]
        # Forced when the piece would otherwise never move again: Pawn and
        # Lance on the last rank, Knight on the last two ranks. (The Iron
        # General can still step sideways on the last rank, so it is NOT
        # forced -- see rules.md for the source discrepancy.)
        if letter in ("P", "L") and self._last_rank(pl, to_r):
            return [True]
        if letter == "N" and self._last_two(pl, to_r):
            return [True]
        return [False, True]

    # ---- drop-less: captured pieces leave play --------------------------------
    def _drop_moves(self, state):
        return []

    # ---- setup -----------------------------------------------------------------
    def setup_board(self):
        b = {}
        # Black (Sente), bottom. Rank 1 (row 0), files 0..12:
        back = ["L", "N", "I", "C", "S", "G", "K", "G", "S", "C", "I", "N", "L"]
        for c, t in enumerate(back):
            b[(c, 0)] = (BLACK, t)
        # Rank 2 (row 1): Free Chariots over the Lances, Flying Dragons over the
        # Knights, Fierce Tigers over the Silvers, Side Mover over the King.
        for c, t in [(0, "F"), (1, "D"), (4, "T"), (6, "M"), (8, "T"),
                     (11, "D"), (12, "F")]:
            b[(c, 1)] = (BLACK, t)
        # Rank 3 (row 2): thirteen Pawns.
        for c in range(13):
            b[(c, 2)] = (BLACK, "P")
        # Rank 4 (row 3): the Go-Between on the King's file.
        b[(6, 3)] = (BLACK, "B")
        # White (Gote): the 180-degree rotation (all pieces are left/right
        # symmetric, so this is the correct point-symmetric mirror).
        for (c, r), (p, t) in list(b.items()):
            b[(self.WIDTH - 1 - c, self.HEIGHT - 1 - r)] = (WHITE, t)
        return b, set()

    # ---- state with the bare-king event ----------------------------------------
    def initial_state(self, options=None, rng=None):
        board, promoted = self.setup_board()
        st = HState(board=board, promoted=frozenset(promoted),
                    hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
        st.reps = {self._poskey(st): 1}
        return st

    def _finish(self, board, promoted, hands, to_move, state):
        promoted = frozenset(promoted)
        st = HState(board=board, promoted=promoted, hands=hands, to_move=to_move,
                    ply=state.ply + 1, reps=dict(state.reps))
        key = self._poskey(st)
        st.reps[key] = st.reps.get(key, 0) + 1
        st.result = self._bare_king_result(st, mover=state.to_move)
        return st

    def _nonking(self, board, pl):
        return [sq for sq, (p, t) in board.items() if p == pl and t != "K"]

    def _bare_king_result(self, st, mover):
        """Adjudicate the bare-king rule right after `mover` moved.

        If the opponent is down to a lone King, the mover wins immediately --
        unless the bared King can legally bare the mover on its very next move
        (or the mover is also already bare), in which case the game is a draw.
        """
        opp = 1 - mover
        if self._nonking(st.board, opp):
            return None                          # opponent not bare: play on
        mine = self._nonking(st.board, mover)
        if not mine:
            return "draw"                        # both bare
        if len(mine) == 1:
            target = mine[0]
            # st.to_move is already the bared opponent; its only piece is the
            # King, so this scan is a handful of king moves.
            for _frm, to, _p in self._legal_board_moves(st):
                if to == target:
                    return "draw"                # mutual baring: drawn at once
        return mover

    # ---- terminal plumbing ------------------------------------------------------
    def legal_moves(self, state):
        if getattr(state, "result", None) is not None:
            return []
        return super().legal_moves(state)

    def is_terminal(self, state) -> bool:
        if getattr(state, "result", None) is not None:
            return True
        return super().is_terminal(state)

    def returns(self, state):
        res = getattr(state, "result", None)
        if res == "draw":
            return [0.0, 0.0]
        if res == BLACK:
            return [1.0, -1.0]
        if res == WHITE:
            return [-1.0, 1.0]
        return super().returns(state)

    # ---- heuristic (MCTS rollout cutoff) ----------------------------------------
    def heuristic(self, state) -> list:
        """Material balance squashed to (-1,1), as [player0, player1] payoffs."""
        bal = 0.0
        for sq, (pl, t) in state.board.items():
            if sq in state.promoted:
                v = self.HORSE_VALUE if t == "D" else self.GOLD_VALUE
            else:
                v = self.PIECE_VALUES.get(t, 2.0)
            bal += v if pl == BLACK else -v
        score = math.tanh(bal / 10.0)
        return [score, -score]

    # ---- (de)serialise: carry the bare-king result --------------------------------
    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["result"] = getattr(state, "result", None)
        return d

    def deserialize(self, d) -> HState:
        s = super().deserialize(d)
        return HState(board=s.board, promoted=s.promoted, hands=s.hands,
                      to_move=s.to_move, ply=s.ply, reps=s.reps,
                      result=d.get("result"))

    # ---- presentation: no drops => hide the reserve trays --------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        spec.pop("reserve", None)
        if getattr(state, "result", None) is not None:
            names = {BLACK: "Sente (Black)", WHITE: "Gote (White)"}
            if state.result == "draw":
                spec["caption"] = "Draw (mutual bare kings)"
            else:
                spec["caption"] = f"{names[state.result]} wins (bare king)"
        return spec
