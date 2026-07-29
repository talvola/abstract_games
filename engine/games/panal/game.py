"""Panal (Glenn Overby II, May 2003) — "a hexagonal chess" on 61 hexes.

Panal (Spanish for *honeycomb*) is the hex chess that refuses to invent a
diagonal: **only the six edge directions of a hex exist**, so there is no
12-direction queen, no bishop, and a Soldier has exactly TWO forward
directions instead of three. The four non-royal pieces are one of each of the
four classical move families — stepper (Soldier), leaper (Horseman), rider
(Princess), hopper (Gunne) — and there are TWO royal pieces per side with two
quite different ways to lose:

* the **Princess** is a hex rook whose *capture* loses the game (it is legal,
  and sometimes right, to leave her en prise), and
* the **Monarch** is a king that may not move at all unless he is in check,
  and even then only by SWAPPING places with an unthreatened friendly piece
  anywhere on the board. Check must be answered; if it cannot be, you lose.

Board & coordinates
-------------------
61 hexes = the central 61 of Gliński's 91 = a hexhex of side 5. Cells are
axial ``"q,r"`` with ``|q|,|r|,|q+r| <= 4``. Overby's own notation is a
"doubled-width" grid: 17 file letters a..q and 9 ranks, where a rank is a
HORIZONTAL row of hexes (the players face each other across opposed SIDES,
not corners) and horizontally adjacent cells are two letters apart::

    file letter index = 2q + r + 8      rank = 5 - r

so e1=(-4,4) and m1=(0,4) are White's bottom corners, m9=(4,-4) and e9=(-4,-4)
Black's, i5=(0,0) the centre and q5=(4,0) the right-hand point. The board is
drawn with POINTY-TOP hexes (the SPEC default): E/W neighbours exist, there is
no vertical neighbour, and a rank is horizontal — exactly the published
diagram, and the geometric reason a Soldier has only two forward directions.

Rules implemented (see rules.md; sources: the author's page and his own ZRF)
---------------------------------------------------------------------------
* **Soldier** ``S`` — one hex forward (NE/NW for White) or sideways (E/W),
  never backward; moves and captures alike in those four directions. May
  instead advance TWO hexes in one forward direction if both are vacant (from
  anywhere, not just its home rank — the author's ZRF has no start-cell
  guard). No promotion, no en passant.
* **Horseman** ``H`` — leaps to any of the 12 cells at hex-distance exactly 2,
  ignoring intervening pieces (2 straight, or two different-but-adjacent
  directions; the "not back to its own hex nor to one adjacent to it" clause
  in the rules is exactly what excludes the 120 deg and 180 deg combinations).
* **Gunne** ``G`` — steps one hex in any of the six directions WITHOUT
  capturing; captures like a Chinese cannon (slide, hop exactly one screen of
  either colour, take the next piece in that line if it is an enemy). Any such
  capture may instead be taken as a **SHOOT**: the enemy is removed and the
  Gunne does not move (move string suffix ``=SHOOT``).
* **Princess** ``P`` — slides any distance in one of the six lines. Losing her
  loses the game; she is NOT protected by the check rules.
* **Monarch** ``M`` — no move at all unless in check; then he swaps with any
  friendly piece that is not itself under threat. He never captures, so he
  never attacks anything either. Check must be resolved (orthodox chess),
  hence the Monarch can never actually be captured.

Move strings: ``"q1,r1>q2,r2"``, plus ``"=SHOOT"`` for a Gunne's stationary
capture. A Monarch swap is written as the ordinary two-cell path (only the
Monarch can move FROM his own cell, so there is no ambiguity).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAME_OF = {WHITE: "White", BLACK: "Black"}

N = 4                      # axial radius: hexhex of side 5 = 61 cells
CELLS = frozenset((q, r) for q in range(-N, N + 1) for r in range(-N, N + 1)
                  if abs(q + r) <= N)

# The six (and only) directions of travel, axial. NW, NE, E, SE, SW, W.
DIRS = ((0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0))

# Horseman: every cell at hex-distance exactly 2 — the six 2-step straights
# plus the six 60 deg combinations. Derived, not hand-typed, so it cannot be
# mistyped; asserted to be 12 cells in selftest.py.
HORSE = tuple(sorted(
    (q, r) for q in range(-2, 3) for r in range(-2, 3)
    if (abs(q) + abs(r) + abs(q + r)) // 2 == 2))

# Soldier: forward = the two rank-increasing (White) / rank-decreasing (Black)
# directions; sideways = E/W. Never backward.
SOLDIER_FWD = {WHITE: ((0, -1), (1, -1)), BLACK: ((0, 1), (-1, 1))}
SOLDIER_STEPS = {p: SOLDIER_FWD[p] + ((1, 0), (-1, 0)) for p in (WHITE, BLACK)}

FILES = "abcdefghijklmnopq"          # 17 files, no letter skipped

# Termination backstop. Progress = a capture or a FORWARD Soldier move (a
# SIDEWAYS Soldier step is reversible, so it must not reset the counter or the
# bound below evaporates). Bound: forward Soldier plies <= 5 soldiers * 6 ranks
# * 2 players = 60; capture plies <= 22 non-royal captures + 1 game-ending
# Princess capture = 23; so at most 83 irreversible plies. A run of consecutive
# reversible plies is at most 100 long (the 100th is played and leaves
# halfmove == 100, which IS the drawn state), and 83 irreversible plies delimit
# at most 84 such runs => 84*100 + 83 = 8,483 plies.
# PLY_CAP is therefore DEAD CODE, as it must be: if it ever fires, a live
# position has been turned into a bogus draw.
PLY_CAP = 8500

# MCTS rollout-cutoff eval. Both royals score 0: the Monarch can never be
# captured and the Princess is present in every non-terminal position, so their
# values are a constant that cancels. The author rates Horsemen above Gunnes.
PIECE_VALUES = {"S": 1.0, "H": 4.0, "G": 3.5, "P": 0.0, "M": 0.0}

PIECE_NAMES = {"S": "Soldier", "H": "Horseman", "G": "Gunne",
               "P": "Princess", "M": "Monarch"}


def on_board(q: int, r: int) -> bool:
    return abs(q) <= N and abs(r) <= N and abs(q + r) <= N


def cell_name(cell) -> str:
    """Axial (q,r) -> Overby's notation, e.g. (-4,4) -> 'e1'."""
    q, r = cell
    return f"{FILES[2 * q + r + 8]}{5 - r}"


def name_cell(name: str):
    """Overby's notation -> axial (q,r). Inverse of `cell_name`."""
    letter, num = name[0], int(name[1:])
    return ((FILES.index(letter) + num - 13) // 2, 5 - num)


def cell_str(c) -> str:
    return f"{c[0]},{c[1]}"


def parse_cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _setup(spec: dict) -> dict:
    return {name_cell(n): (owner, letter)
            for (owner, letter), names in spec.items() for n in names.split()}


# Start position — the author's own ZRF board-setup, verified against his setup
# diagram (ghex-setup.gif) and against a full replay of the published sample
# game. NOTE the article's setup TABLE misprints both Soldier rows as rank 1/9
# (which would collide with the Gunnes, Princess and Monarch); rank 3/7 is what
# the ZRF, the diagram and every move of the sample game say.
START = _setup({
    (WHITE, "M"): "m1",
    (WHITE, "P"): "e1",
    (WHITE, "G"): "g1 k1",
    (WHITE, "H"): "f2 h2 j2 l2",
    (WHITE, "S"): "e3 g3 i3 k3 m3",
    (BLACK, "M"): "e9",
    (BLACK, "P"): "m9",
    (BLACK, "G"): "g9 k9",
    (BLACK, "H"): "f8 h8 j8 l8",
    (BLACK, "S"): "e7 g7 i7 k7 m7",
})


@dataclass
class PState:
    board: dict = field(default_factory=dict)   # (q,r) -> (owner, letter)
    to_move: int = WHITE
    halfmove: int = 0        # plies since last capture / forward Soldier move
    ply: int = 0
    reps: dict = field(default_factory=dict)    # position key -> count
    last: Optional[tuple] = None                # (from, to) for highlights


class Panal(Game):
    CELLS = CELLS
    PLY_CAP = PLY_CAP

    # ---- basics -----------------------------------------------------------
    @property
    def num_players(self) -> int:
        return 2

    def current_player(self, s) -> int:
        return s.to_move

    def initial_state(self, options=None, rng=None):
        s = PState(board=dict(START), to_move=WHITE)
        # Seed the opening position, or a threefold repetition OF IT would need
        # four occurrences.
        s.reps = {self.poskey(s.board, s.to_move): 1}
        return s

    # ---- move generation --------------------------------------------------
    @staticmethod
    def _takeable(board: dict, tgt, me: int) -> bool:
        """May `me` move onto `tgt` (empty, or an enemy that is not the
        Monarch)? The Monarch is unreachable in real play — leaving him
        attacked is illegal, so he is never en prise at the start of a turn —
        but excluding him here keeps "both Monarchs are always on the board" a
        structural invariant rather than a proof obligation."""
        occ = board.get(tgt)
        return occ is None or (occ[0] != me and occ[1] != "M")

    def _gunne_targets(self, board: dict, cell):
        """Cells this Gunne could capture on: slide, hop exactly one screen of
        either colour, land on the next piece in that line if it is an enemy."""
        q, r = cell
        out = []
        for dq, dr in DIRS:
            cq, cr = q + dq, r + dr
            while (cq, cr) in CELLS and (cq, cr) not in board:
                cq += dq
                cr += dr
            if (cq, cr) not in CELLS:
                continue                      # no screen in this line
            cq += dq                          # hop the screen
            cr += dr
            while (cq, cr) in CELLS and (cq, cr) not in board:
                cq += dq
                cr += dr
            if (cq, cr) in CELLS:
                occ = board[(cq, cr)]
                if occ[0] != board[cell][0] and occ[1] != "M":
                    out.append((cq, cr))
        return out

    def _pseudo(self, s) -> list:
        """Pseudo-legal moves as (frm, to, kind), kind in "", "SHOOT", "SWAP"."""
        out = []
        me, board = s.to_move, s.board
        monarch = None
        for cell, (owner, t) in board.items():
            if owner != me:
                continue
            q, r = cell
            if t == "S":
                for dq, dr in SOLDIER_STEPS[me]:
                    tgt = (q + dq, r + dr)
                    if tgt in CELLS and self._takeable(board, tgt, me):
                        out.append((cell, tgt, ""))
                for dq, dr in SOLDIER_FWD[me]:
                    one, two = (q + dq, r + dr), (q + 2 * dq, r + 2 * dr)
                    if (one in CELLS and one not in board
                            and two in CELLS and two not in board):
                        out.append((cell, two, ""))
            elif t == "H":
                for dq, dr in HORSE:
                    tgt = (q + dq, r + dr)
                    if tgt in CELLS and self._takeable(board, tgt, me):
                        out.append((cell, tgt, ""))
            elif t == "P":
                for dq, dr in DIRS:
                    cq, cr = q + dq, r + dr
                    while (cq, cr) in CELLS:
                        occ = board.get((cq, cr))
                        if occ is None:
                            out.append((cell, (cq, cr), ""))
                        else:
                            if occ[0] != me and occ[1] != "M":
                                out.append((cell, (cq, cr), ""))
                            break
                        cq += dq
                        cr += dr
            elif t == "G":
                for dq, dr in DIRS:                    # non-capturing step
                    tgt = (q + dq, r + dr)
                    if tgt in CELLS and tgt not in board:
                        out.append((cell, tgt, ""))
                for tgt in self._gunne_targets(board, cell):
                    out.append((cell, tgt, ""))        # capture by moving in
                    out.append((cell, tgt, "SHOOT"))   # ...or shoot in place
            else:                                      # "M"
                monarch = cell
        # The Monarch may not move unless he is in check, and then only by
        # swapping with a friendly piece that is not itself threatened.
        if monarch is not None and self.attacked(board, monarch, 1 - me):
            for cell, (owner, t) in board.items():
                if owner == me and t != "M" \
                        and not self.attacked(board, cell, 1 - me):
                    out.append((monarch, cell, "SWAP"))
        return out

    def attacked(self, board: dict, cell, by: int) -> bool:
        """Is `cell` immediately threatened with capture by player `by`?

        A SEPARATE code path from move generation (testing one does not test
        the other). Note the Monarch appears nowhere here: he has no capturing
        move at all, so he threatens nothing — two Monarchs may stand side by
        side. The Gunne is the interesting case: it must be the SECOND piece
        along the line (a Gunne one step away cannot capture at all).
        """
        q, r = cell
        for dq, dr in SOLDIER_STEPS[by]:          # reverse lookup, not a scan
            if board.get((q - dq, r - dr)) == (by, "S"):
                return True
        for dq, dr in HORSE:
            if board.get((q + dq, r + dr)) == (by, "H"):
                return True
        for dq, dr in DIRS:
            cq, cr = q + dq, r + dr
            while (cq, cr) in CELLS and (cq, cr) not in board:
                cq += dq
                cr += dr
            if (cq, cr) not in CELLS:
                continue
            if board[(cq, cr)] == (by, "P"):      # Princess: the FIRST piece
                return True
            cq += dq                              # past the screen…
            cr += dr
            while (cq, cr) in CELLS and (cq, cr) not in board:
                cq += dq
                cr += dr
            if (cq, cr) in CELLS and board[(cq, cr)] == (by, "G"):
                return True                       # Gunne: the SECOND piece
        return False

    def monarch_cell(self, board: dict, player: int):
        for c, (o, t) in board.items():
            if o == player and t == "M":
                return c
        return None

    def princess_cell(self, board: dict, player: int):
        for c, (o, t) in board.items():
            if o == player and t == "P":
                return c
        return None

    def in_check(self, board: dict, player: int) -> bool:
        m = self.monarch_cell(board, player)
        return m is not None and self.attacked(board, m, 1 - player)

    @staticmethod
    def apply_to_board(board: dict, frm, to, kind: str) -> dict:
        b = dict(board)
        if kind == "SHOOT":
            del b[to]                      # the Gunne does not move
        elif kind == "SWAP":
            b[frm], b[to] = b[to], b[frm]
        else:
            b[to] = b.pop(frm)
        return b

    def _legal(self, s) -> list:
        """Pseudo-legal moves that do not leave the mover's Monarch in check.

        Memoised on the state: `_draw_reason`, `legal_moves`, `is_terminal` and
        `returns` may each ask for it in the same tick.
        """
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        me = s.to_move
        out = [m for m in self._pseudo(s)
               if not self.in_check(self.apply_to_board(s.board, *m), me)]
        object.__setattr__(s, "_legal_cache", out)
        return out

    @staticmethod
    def _mstr(frm, to, kind) -> str:
        return (f"{cell_str(frm)}>{cell_str(to)}"
                + ("=SHOOT" if kind == "SHOOT" else ""))

    def _find(self, s, move: str):
        for m in self._legal(s):
            if self._mstr(*m) == move:
                return m
        raise ValueError(f"illegal move {move!r}")

    # ---- terminal / draws -------------------------------------------------
    def loser(self, s) -> Optional[int]:
        """The player who has LOST, decisively, or None.

        Two decisive events: a captured Princess, and a Monarch in check with
        no legal reply. BOTH must outrank every draw counter — a win delivered
        on the 100th reversible ply, in a thrice-repeated position or at the
        ply cap is still a win (this exact ordering bug has shipped nine times
        in this library). `_draw_reason` therefore consults this first.
        """
        for p in (WHITE, BLACK):
            if self.princess_cell(s.board, p) is None:
                return p
        if not self._legal(s) and self.in_check(s.board, s.to_move):
            return s.to_move
        return None

    def _draw_reason(self, s) -> Optional[str]:
        if self.loser(s) is not None:
            return None                    # a decisive result outranks counters
        if not self._legal(s):
            return None                    # stalemate is its own (drawn) case
        if s.halfmove >= 100:
            return "50-move rule"
        if s.reps and max(s.reps.values()) >= 3:
            return "threefold repetition"
        if s.ply >= self.PLY_CAP:
            return "move limit"
        return None

    def legal_moves(self, s) -> list:
        if self.is_terminal(s):
            return []
        return [self._mstr(*m) for m in self._legal(s)]

    def is_terminal(self, s) -> bool:
        return (self.loser(s) is not None or not self._legal(s)
                or self._draw_reason(s) is not None)

    def returns(self, s) -> list:
        loser = self.loser(s)
        if loser is None:
            return [0.0, 0.0]              # stalemate, a counter draw, or live
        return [-1.0, 1.0] if loser == WHITE else [1.0, -1.0]

    # ---- applying a move --------------------------------------------------
    def poskey(self, board: dict, to_move: int) -> str:
        items = sorted((q, r, o, t) for (q, r), (o, t) in board.items())
        return f"{to_move}|" + ";".join(f"{q},{r},{o},{t}" for q, r, o, t in items)

    def apply_move(self, s, move: str, rng=None):
        frm, to, kind = self._find(s, move)
        mover = s.to_move
        piece = s.board[frm][1]
        captured = kind != "SWAP" and to in s.board
        board = self.apply_to_board(s.board, frm, to, kind)
        # Progress = a capture or a FORWARD Soldier move. A sideways Soldier
        # step is reversible and deliberately does NOT reset the counter.
        forward = piece == "S" and kind == "" and (
            (to[1] - frm[1]) < 0 if mover == WHITE else (to[1] - frm[1]) > 0)
        irreversible = captured or forward
        halfmove = 0 if irreversible else s.halfmove + 1
        reps = {} if irreversible else dict(s.reps)
        key = self.poskey(board, 1 - mover)
        reps[key] = reps.get(key, 0) + 1
        return PState(board=board, to_move=1 - mover, halfmove=halfmove,
                      ply=s.ply + 1, reps=reps, last=(frm, to))

    # ---- serialisation ----------------------------------------------------
    def serialize(self, s) -> dict:
        return {
            "board": {cell_str(k): [v[0], v[1]] for k, v in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
            "last": [cell_str(s.last[0]), cell_str(s.last[1])] if s.last else None,
        }

    def deserialize(self, d: dict):
        last = d.get("last")
        return PState(
            board={parse_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps") or {}),
            last=(parse_cell(last[0]), parse_cell(last[1])) if last else None,
        )

    # ---- presentation -----------------------------------------------------
    def describe_move(self, s, move: str) -> str:
        """Long algebraic in Overby's notation: `Si3-g5`, `Sg5xh6`, `Gg1xm7`.

        A SHOOT is written `Gg1*m7` — the source page writes it simply `xm7`,
        which cannot be told from a capture by moving in the move log, and the
        author himself disambiguates it in prose. `Mm1<>Hl2` is a Monarch swap.

        `+` follows a move that threatens EITHER royal — the Monarch (check)
        or the Princess — which is the author's own usage ("Note the use of
        the + for check at White's seventh move attacking the Princess"); it
        reproduces all three of the sample game's `+` marks and adds none.
        `#` marks the move that ends the game.
        """
        frm, to, kind = self._find(s, move)
        piece = s.board[frm][1]
        if kind == "SWAP":
            txt = f"M{cell_name(frm)}<>{s.board[to][1]}{cell_name(to)}"
        elif kind == "SHOOT":
            txt = f"G{cell_name(frm)}*{cell_name(to)}"
        else:
            txt = (piece + cell_name(frm) + ("x" if to in s.board else "-")
                   + cell_name(to))
        nxt = self.apply_move(s, move)
        foe = nxt.to_move
        pr = self.princess_cell(nxt.board, foe)
        if self.loser(nxt) is not None:
            txt += "#"
        elif (self.in_check(nxt.board, foe)
              or (pr is not None and self.attacked(nxt.board, pr, 1 - foe))):
            txt += "+"
        return txt

    def board_spec(self, s) -> dict:
        # Honeycomb: the three hex colours of the published board (which the
        # author notes are decorative — "the coloring has no bearing on play").
        shades = ("#f0dfae", "#e2c988", "#d3b264")
        return {
            "type": "hex", "shape": "hexagon", "size": N + 1,
            # POINTY-TOP (the default): ranks are horizontal rows and the two
            # forward directions are the two upward diagonals. Flat-top would
            # draw the board 30 deg off the published diagram.
            "tints": {cell_str(c): shades[(c[0] - c[1]) % 3] for c in CELLS},
            # The author's file/rank names, printed on the cells, so the move
            # log ("Si3-g5") can be read off the board.
            "labels": {cell_str(c): cell_name(c) for c in CELLS},
        }

    def render(self, s, perspective=None) -> dict:
        pieces = [{"cell": cell_str(c), "owner": o, "label": t}
                  for c, (o, t) in sorted(s.board.items())]
        highlights = ([{"cell": cell_str(s.last[0]), "kind": "last-move"},
                       {"cell": cell_str(s.last[1]), "kind": "last-move"}]
                      if s.last else [])
        loser = self.loser(s)
        if loser is not None:
            why = ("Princess captured"
                   if self.princess_cell(s.board, loser) is None
                   else "Monarch checkmated")
            caption = f"{NAME_OF[1 - loser]} wins ({why})"
        elif not self._legal(s):
            caption = (f"Draw (stalemate — {NAME_OF[s.to_move]} has no move)")
        else:
            reason = self._draw_reason(s)
            if reason is not None:
                caption = f"Draw ({reason})"
            else:
                check = " (check)" if self.in_check(s.board, s.to_move) else ""
                caption = f"{NAME_OF[s.to_move]} to move{check}"
        return {
            "board": self.board_spec(s),
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            # The empty key labels the SUFFIX-LESS member of the pair; without
            # it Board.jsx falls back to its promotion wording ("No promotion"),
            # which is nonsense for a Gunne deciding how to take.
            "choiceNames": {"": "Capture by moving in",
                            "SHOOT": "Shoot (Gunne stays put)"},
            "choiceTitle": "Capture by moving in, or shoot?",
        }

    def heuristic(self, s) -> list:
        """Tanh material balance, as a LIST of per-player payoffs (a bare float
        raises `TypeError: 'float' object is not subscriptable` in MCTS
        back-propagation, and only when the rollout cutoff is reached)."""
        bal = 0.0
        for _, (o, t) in s.board.items():
            v = PIECE_VALUES[t]
            bal += v if o == WHITE else -v
        w = math.tanh(bal / 8.0)
        return [w, -w]
