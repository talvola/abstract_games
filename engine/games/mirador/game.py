"""Mirador — Andrew Perkis (2010).

Connection game on a 27x27 grid of small squares, presented in Abstract Games
magazine #22 (pp. 35-38, intro Kerry Handscomb, annotation Paul van Wamelen),
originally published in the January 2010 Games magazine and described by the
designer at miradorthegame.blogspot.ca (the SuperDuperGames rules PDF).

A move fills an empty 2x2 block ("mirador") in your colour.  Miradors may not
overlap or touch — the sole exception is that two miradors of the SAME colour
may touch corner-to-corner.  Same-colour miradors are *connected* by (a) that
corner contact, or (b) an unobstructed line of sight: an empty one-square-wide
row or column corridor along a row/column both miradors cover.  A mirador with
an unobstructed line of sight to a board edge (along one of its own rows or
columns) is connected to that side.  You win by building a chain of your
miradors connecting either pair of opposite sides — either player may connect
either axis.

Wins are adjudicated by DECLARATION: after placing, if you believe your
connection is unbreakable you declare; your opponent then challenges by
placing as many miradors as they like (consecutive turns) trying to break the
chain.  If they break it, they win the game; if they cannot (and accept, or
run out of placements), you win.  Green moves first; pie rule (swap).

Coordinates: a mirador is named by its bottom-left square, letter (column
A-Z) + number (row 1-26); the engine's cell id is "c,r" 0-indexed with r=0 the
bottom row.  Anchor "4,3" = E4, covering columns 4-5 and rows 3-4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 27          # board is 27x27 small squares
AMAX = N - 1    # anchors run 0..25 (26x26 = 676 first placements)
GREEN, BLUE = 0, 1  # colours (Green = first mover's colour, pre-swap seat 0)
COLOUR_NAME = {GREEN: "Green", BLUE: "Blue"}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class MirState:
    # each mirador: (anchor_col, anchor_row, colour)
    miradors: list = field(default_factory=list)
    swapped: bool = False          # pie rule taken (colours exchanged between seats)
    to_move: int = GREEN           # COLOUR to move
    phase: str = "play"            # "play" | "window" (declare?) | "refute"
    declarer: Optional[int] = None  # colour that declared (refute phase)
    winner: Optional[int] = None   # SEAT index of the winner
    draw: bool = False             # locked board, no declaration possible
    ply: int = 0
    last: Optional[str] = None     # last placement anchor "c,r" (for highlight)


def _occupancy(miradors) -> dict:
    occ = {}
    for c, r, col in miradors:
        for dc in (0, 1):
            for dr in (0, 1):
                occ[(c + dc, r + dr)] = col
    return occ


def _can_place(occ, colour, c, r) -> bool:
    """May `colour` place a mirador with anchor (c, r)?

    Scans the 4x4 neighbourhood of the 2x2 footprint: every on-board cell must
    be empty, except the four diagonal corner cells, which may hold the
    placer's OWN colour (the same-colour corner-touch exception).
    """
    for dc in (-1, 0, 1, 2):
        for dr in (-1, 0, 1, 2):
            x, y = c + dc, r + dr
            if 0 <= x < N and 0 <= y < N:
                v = occ.get((x, y))
                if v is None:
                    continue
                if dc in (-1, 2) and dr in (-1, 2) and v == colour:
                    continue  # own-colour corner contact is allowed
                return False
    return True


def _placements(occ, colour):
    out = []
    for r in range(AMAX):
        for c in range(AMAX):
            if _can_place(occ, colour, c, r):
                out.append((c, r))
    return out


def _any_placement(occ, colour) -> bool:
    for r in range(AMAX):
        for c in range(AMAX):
            if _can_place(occ, colour, c, r):
                return True
    return False


def _spanning(miradors, colour, occ=None):
    """Return (north_south, east_west): does `colour` have a chain of connected
    miradors linking bottom+top / left+right?"""
    if occ is None:
        occ = _occupancy(miradors)
    mine = [(c, r) for c, r, col in miradors if col == colour]
    if not mine:
        return (False, False)

    def col_clear(x, r0, r1):  # cells (x, r0..r1) all empty
        for y in range(r0, r1 + 1):
            if (x, y) in occ:
                return False
        return True

    def row_clear(y, c0, c1):
        for x in range(c0, c1 + 1):
            if (x, y) in occ:
                return False
        return True

    n = len(mine)
    # side flags per mirador: [left, right, bottom, top]
    sides = []
    for c, r in mine:
        left = any(row_clear(y, 0, c - 1) for y in (r, r + 1))
        right = any(row_clear(y, c + 2, N - 1) for y in (r, r + 1))
        bottom = any(col_clear(x, 0, r - 1) for x in (c, c + 1))
        top = any(col_clear(x, r + 2, N - 1) for x in (c, c + 1))
        sides.append([left, right, bottom, top])

    # union-find over this colour's miradors
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        ci, ri = mine[i]
        for j in range(i + 1, n):
            cj, rj = mine[j]
            dc, dr = abs(ci - cj), abs(ri - rj)
            if dc == 2 and dr == 2:
                union(i, j)  # corner contact
                continue
            # vertical line of sight: shared column(s), empty corridor between
            if dc <= 1 and dr > 2:
                lo, hi = (i, j) if ri < rj else (j, i)
                (lc, lr), (hc, hr) = mine[lo], mine[hi]
                shared = set(range(lc, lc + 2)) & set(range(hc, hc + 2))
                if any(col_clear(x, lr + 2, hr - 1) for x in shared):
                    union(i, j)
                    continue
            # horizontal line of sight
            if dr <= 1 and dc > 2:
                lo, hi = (i, j) if ci < cj else (j, i)
                (lc, lr), (hc, hr) = mine[lo], mine[hi]
                shared = set(range(lr, lr + 2)) & set(range(hr, hr + 2))
                if any(row_clear(y, lc + 2, hc - 1) for y in shared):
                    union(i, j)

    comp = {}
    for i in range(n):
        comp.setdefault(find(i), [False, False, False, False])
        for k in range(4):
            comp[find(i)][k] = comp[find(i)][k] or sides[i][k]
    ns = any(f[2] and f[3] for f in comp.values())
    ew = any(f[0] and f[1] for f in comp.values())
    return (ns, ew)


class Mirador(Game):
    name = "Mirador"

    @property
    def num_players(self) -> int:
        return 2

    # ---- helpers -----------------------------------------------------------
    @staticmethod
    def _seat(state: MirState, colour: int) -> int:
        return colour ^ int(state.swapped)

    @staticmethod
    def _swap_available(s: MirState) -> bool:
        # exactly Blue's first turn: one mirador down, no swap taken yet
        return (s.phase == "play" and not s.swapped
                and s.to_move == BLUE and len(s.miradors) == 1)

    # ---- Game interface ----------------------------------------------------
    def initial_state(self, options=None, rng=None) -> MirState:
        return MirState()

    def current_player(self, s: MirState) -> int:
        return self._seat(s, s.to_move)

    def legal_moves(self, s: MirState):
        if s.winner is not None or s.draw:
            return []
        if s.phase == "window":
            return ["declare", "pass"]
        occ = _occupancy(s.miradors)
        moves = [f"{c},{r}" for c, r in _placements(occ, s.to_move)]
        if s.phase == "refute":
            moves.append("accept")
            return moves
        # phase == "play"
        if self._swap_available(s):
            moves.append("swap")
        if not moves:
            # locked board: forced declaration if a chain exists, else the
            # game is a dead draw (handled by is_terminal)
            if any(_spanning(s.miradors, s.to_move, occ)):
                return ["declare"]
            return []
        return moves

    def apply_move(self, s: MirState, move: str, rng=None) -> MirState:
        mir = list(s.miradors)
        if move == "swap":
            if not self._swap_available(s):
                raise ValueError("swap only available to the second player on move 2")
            return MirState(miradors=mir, swapped=True, to_move=BLUE,
                            phase="play", ply=s.ply + 1, last=s.last)
        if move == "pass":
            if s.phase != "window":
                raise ValueError("pass only in the declaration window")
            return MirState(miradors=mir, swapped=s.swapped,
                            to_move=1 - s.to_move, phase="play",
                            ply=s.ply + 1, last=s.last)
        if move == "declare":
            if s.phase not in ("window", "play"):
                raise ValueError("cannot declare now")
            declarer = s.to_move
            return MirState(miradors=mir, swapped=s.swapped,
                            to_move=1 - declarer, phase="refute",
                            declarer=declarer, ply=s.ply + 1, last=s.last)
        if move == "accept":
            if s.phase != "refute":
                raise ValueError("accept only during a challenge")
            return MirState(miradors=mir, swapped=s.swapped, to_move=s.to_move,
                            phase="refute", declarer=s.declarer,
                            winner=self._seat(s, s.declarer),
                            ply=s.ply + 1, last=s.last)

        # a placement
        c, r = _cell(move)
        occ = _occupancy(mir)
        if not (0 <= c < AMAX and 0 <= r < AMAX) or not _can_place(occ, s.to_move, c, r):
            raise ValueError(f"illegal placement {move}")
        mir.append((c, r, s.to_move))
        for dc in (0, 1):
            for dr in (0, 1):
                occ[(c + dc, r + dr)] = s.to_move

        if s.phase == "refute":
            # challenger keeps placing; the moment the declared chain is
            # broken, the challenge succeeds and the challenger wins
            if not any(_spanning(mir, s.declarer, occ)):
                return MirState(miradors=mir, swapped=s.swapped,
                                to_move=s.to_move, phase="refute",
                                declarer=s.declarer,
                                winner=self._seat(s, s.to_move),
                                ply=s.ply + 1, last=move)
            return MirState(miradors=mir, swapped=s.swapped, to_move=s.to_move,
                            phase="refute", declarer=s.declarer,
                            ply=s.ply + 1, last=move)

        # normal play: open the declaration window only if the mover now has
        # a side-to-side chain (declaring without one is a guaranteed loss)
        if any(_spanning(mir, s.to_move, occ)):
            return MirState(miradors=mir, swapped=s.swapped, to_move=s.to_move,
                            phase="window", ply=s.ply + 1, last=move)
        return MirState(miradors=mir, swapped=s.swapped, to_move=1 - s.to_move,
                        phase="play", ply=s.ply + 1, last=move)

    def is_terminal(self, s: MirState) -> bool:
        if s.winner is not None or s.draw:
            return True
        if s.phase != "play":
            return False  # window/refute phases always have moves
        occ = _occupancy(s.miradors)
        if _any_placement(occ, s.to_move):
            return False
        # stuck: forced declare if a chain exists, otherwise a dead draw
        return not any(_spanning(s.miradors, s.to_move, occ))

    def returns(self, s: MirState):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def serialize(self, s: MirState) -> dict:
        return {
            "miradors": [[c, r, col] for c, r, col in s.miradors],
            "swapped": s.swapped,
            "to_move": s.to_move,
            "phase": s.phase,
            "declarer": s.declarer,
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
            "last": s.last,
        }

    def deserialize(self, data: dict) -> MirState:
        return MirState(
            miradors=[(int(c), int(r), int(col)) for c, r, col in data["miradors"]],
            swapped=bool(data.get("swapped", False)),
            to_move=int(data["to_move"]),
            phase=data.get("phase", "play"),
            declarer=data.get("declarer"),
            winner=data.get("winner"),
            draw=bool(data.get("draw", False)),
            ply=int(data.get("ply", 0)),
            last=data.get("last"),
        )

    # ---- notation ----------------------------------------------------------
    @staticmethod
    def _name(move: str) -> str:
        c, r = _cell(move)
        return f"{chr(65 + c)}{r + 1}"

    def describe_move(self, s: MirState, move: str) -> str:
        if move == "swap":
            return "Swap (pie rule)"
        if move == "declare":
            return f"{COLOUR_NAME[s.to_move]} declares a win!"
        if move == "pass":
            return "No declaration"
        if move == "accept":
            return "Challenge abandoned — declarer wins"
        name = self._name(move)
        if s.phase == "refute":
            return f"{name} (challenge)"
        return name

    # ---- rendering ---------------------------------------------------------
    def render(self, s: MirState, perspective=None) -> dict:
        pieces = []
        for c, r, col in s.miradors:
            owner = self._seat(s, col)
            for dc in (0, 1):
                for dr in (0, 1):
                    pieces.append({"cell": f"{c + dc},{r + dr}", "owner": owner,
                                   "shape": "fill"})
        spec = {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "actionNames": {
                "declare": "Declare win!",
                "pass": "Continue (no declaration)",
                "accept": "Accept the connection (declarer wins)",
                "swap": "Swap (pie rule)",
            },
        }
        if s.last is not None:
            c, r = _cell(s.last)
            spec["highlights"] = [{"cell": f"{c + dc},{r + dr}", "kind": "last-move"}
                                  for dc in (0, 1) for dr in (0, 1)]
        if s.winner is not None:
            spec["caption"] = f"Player {s.winner + 1} wins"
        elif s.draw or self.is_terminal(s):
            spec["caption"] = "Draw — board locked, no connection"
        elif s.phase == "window":
            spec["caption"] = f"{COLOUR_NAME[s.to_move]} may declare a win"
        elif s.phase == "refute":
            spec["caption"] = (f"{COLOUR_NAME[s.declarer]} declared — "
                               f"{COLOUR_NAME[s.to_move]} challenges the connection")
        else:
            spec["caption"] = f"{COLOUR_NAME[s.to_move]} to place a mirador"
        return spec

    # ---- bot eval ----------------------------------------------------------
    def heuristic(self, s: MirState):
        """Progress = per colour, the best component's side count on its best
        axis (0, 1 or 2 sides), scaled; returns per-SEAT payoffs."""
        if s.winner is not None or s.draw:
            return self.returns(s)
        occ = _occupancy(s.miradors)

        def prog(colour):
            mine = [(c, r) for c, r, col in s.miradors if col == colour]
            if not mine:
                return 0.0
            ns, ew = _spanning(s.miradors, colour, occ)
            if ns or ew:
                return 1.0
            best = 0
            for c, r in mine:
                left = any(all((x, y) not in occ for x in range(0, c)) for y in (r, r + 1))
                right = any(all((x, y) not in occ for x in range(c + 2, N)) for y in (r, r + 1))
                bottom = any(all((x, y) not in occ for y in range(0, r)) for x in (c, c + 1))
                top = any(all((x, y) not in occ for y in range(r + 2, N)) for x in (c, c + 1))
                best = max(best, int(left) + int(right), int(bottom) + int(top))
            return 0.25 * best
        d = prog(GREEN) - prog(BLUE)
        val = 0.6 * d  # bounded in [-0.6, 0.6]
        g_seat = self._seat(s, GREEN)
        out = [0.0, 0.0]
        out[g_seat] = val
        out[1 - g_seat] = -val
        return out
