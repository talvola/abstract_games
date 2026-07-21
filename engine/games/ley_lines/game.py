"""Ley Lines (Eric Solomon, 2019) — a route-finding capture game on an 18x18
array of pointy-top hexagons.

White "Go stones" are randomly scattered over the board (>= 6 in each of the
nine 6x6 zones). Each player has a single coloured ring. On your turn you either

  * single-step the ring one hex to an adjacent cell (no capture), or
  * jump: if the ring is *on* a stone, hop along one of the three principal
    directions to the next stone, optionally continuing in the SAME direction.
    Every WHITE stone the ring starts on or reaches is captured (replaced by a
    black stone).

Captured stones go to two piles. Pile 1 = a *complete line* (one turn's jumps
that visit EVERY stone on a principal line, with no black stones visited, when
the player's PRECEDING move was a single step) — these count double. Pile 2 =
everything else. When both players pass in succession the game ends; the higher
score (pile1*2 + pile2) wins, an equal score is an honest draw.

Board model: 18x18 "odd-r" offset coordinates ``"c,r"`` (columns 0..17, rows
0..17; odd rows shifted right). Internally cube coordinates give the three
principal lines (row = z const, and the two diagonals = x const / y const).

Rules as implemented match Abstract Games magazine, Issue 17 (Autumn 2019),
pp. 43-45. See rules.md for the interpretation notes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 18                 # 18x18 array
ZONE = 6                  # 6x6 colour zones (3x3 of them)
MIN_PER_ZONE = 6          # >= 6 stones per zone at deal time
PLY_CAP = 1000            # hard backstop so random play always terminates

# Six cube directions for pointy-top hexes. Each principal LINE is the pair of
# opposite directions; the invariant cube coordinate names the line.
CUBE_DIRS = [
    (1, -1, 0), (-1, 1, 0),   # E / W       -> z (row) constant
    (1, 0, -1), (-1, 0, 1),   # NE / SW     -> y constant
    (0, 1, -1), (0, -1, 1),   # NW / SE     -> x constant
]
DIR_NAME = {(1, -1, 0): "E", (-1, 1, 0): "W", (1, 0, -1): "NE",
            (-1, 0, 1): "SW", (0, 1, -1): "NW", (0, -1, 1): "SE"}

SEAT_NAME = {0: "Player 1", 1: "Player 2"}


# ----------------------------------------------------------------- geometry ---
def in_board(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE


def off2cube(c, r):
    x = c - ((r - (r & 1)) // 2)
    z = r
    return (x, -x - z, z)


def cube2off(x, y, z):
    return (x + ((z - (z & 1)) // 2), z)


def add_dir(cell, d):
    x, y, z = off2cube(*cell)
    return cube2off(x + d[0], y + d[1], z + d[2])


def cell_str(cell):
    return f"{cell[0]},{cell[1]}"


def parse_cell(s):
    c, r = s.split(",")
    return (int(c), int(r))


def zone_of(c, r):
    return (c // ZONE, r // ZONE)


# ------------------------------------------------------------------- state ----
@dataclass
class LLState:
    stones: dict = field(default_factory=dict)   # (c,r) -> 'W' | 'B'
    rings: list = field(default_factory=lambda: [None, None])  # per seat: (c,r) | None
    phase: str = "place"                          # "place" | "move"
    place_order: list = field(default_factory=lambda: [1, 0])  # seats left to place
    turn: int = 0                                 # seat to move (move phase)
    piles: list = field(default_factory=lambda: [[0, 0], [0, 0]])  # [pile1,pile2] per seat
    prev_step: list = field(default_factory=lambda: [False, False])
    passes: int = 0
    plies: int = 0
    over: bool = False
    last: list = field(default_factory=list)      # cells of last move (highlight)


class LeyLines(Game):
    uid = "ley_lines"
    name = "Ley Lines"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> LLState:
        import random
        rng = rng or random.Random()
        opts = options or {}
        total = int(opts.get("num_stones", 54))
        stones: dict = {}
        # 1) satisfy the per-zone quota first.
        for zc in range(SIZE // ZONE):
            for zr in range(SIZE // ZONE):
                cells = [(zc * ZONE + dc, zr * ZONE + dr)
                         for dc in range(ZONE) for dr in range(ZONE)]
                rng.shuffle(cells)
                for cell in cells[:MIN_PER_ZONE]:
                    stones[cell] = "W"
        # 2) top up to the target total on any remaining empty cells.
        empties = [(c, r) for c in range(SIZE) for r in range(SIZE)
                   if (c, r) not in stones]
        rng.shuffle(empties)
        need = max(0, total - len(stones))
        for cell in empties[:need]:
            stones[cell] = "W"
        return LLState(stones=stones)

    def current_player(self, s: LLState) -> int:
        if s.phase == "place":
            return s.place_order[0]
        return s.turn

    def is_terminal(self, s: LLState) -> bool:
        return s.over

    # ---- move generation -------------------------------------------------
    def _next_stone(self, stones, cell, d):
        """Nearest stone from `cell` stepping along direction `d` (excludes
        `cell` itself); None if the ray leaves the board first."""
        cur = cell
        while True:
            cur = add_dir(cur, d)
            if not in_board(*cur):
                return None
            if cur in stones:
                return cur

    def _jump_paths(self, stones, ring, opp_ring):
        """All legal jump paths from `ring` (which must sit on a stone). Each
        path is a list of cells [ring, s1, s2, ...]; every prefix of length >= 1
        stone is a legal stopping point."""
        out = []
        for d in CUBE_DIRS:
            chain = []
            cur = ring
            while True:
                nxt = self._next_stone(stones, cur, d)
                if nxt is None or nxt == opp_ring:
                    break                      # off board, or cannot land on opp ring
                chain.append(nxt)
                cur = nxt
            for i in range(1, len(chain) + 1):
                out.append([ring] + chain[:i])
        return out

    def legal_moves(self, s: LLState) -> list[str]:
        if s.over:
            return []
        if s.phase == "place":
            occ = set(s.stones.keys()) | {r for r in s.rings if r is not None}
            return [f"{c},{r}" for c in range(SIZE) for r in range(SIZE)
                    if (c, r) not in occ]
        seat = s.turn
        ring = s.rings[seat]
        opp = s.rings[1 - seat]
        moves = ["pass"]
        # single steps: any adjacent cell not holding the opponent's ring
        for d in CUBE_DIRS:
            n = add_dir(ring, d)
            if in_board(*n) and n != opp:
                moves.append(f"{cell_str(ring)}>{cell_str(n)}")
        # jumps: only if the ring surrounds a stone
        if ring in s.stones:
            for path in self._jump_paths(s.stones, ring, opp):
                moves.append(">".join(cell_str(c) for c in path) + "=J")
        return moves

    # ---- apply -----------------------------------------------------------
    def _clone(self, s: LLState) -> LLState:
        return LLState(
            stones=dict(s.stones),
            rings=list(s.rings),
            phase=s.phase,
            place_order=list(s.place_order),
            turn=s.turn,
            piles=[list(s.piles[0]), list(s.piles[1])],
            prev_step=list(s.prev_step),
            passes=s.passes,
            plies=s.plies,
            over=s.over,
            last=list(s.last),
        )

    @staticmethod
    def _line_stones(stones, a, b):
        """All stone cells lying on the principal line through cells a and b."""
        xa, ya, za = off2cube(*a)
        xb, yb, zb = off2cube(*b)
        if xa == xb:
            keep = lambda cell: off2cube(*cell)[0] == xa
        elif ya == yb:
            keep = lambda cell: off2cube(*cell)[1] == ya
        else:
            keep = lambda cell: off2cube(*cell)[2] == za
        return [cell for cell in stones if keep(cell)]

    def apply_move(self, s: LLState, move: str, rng=None) -> LLState:
        ns = self._clone(s)

        # ----- placement phase -----
        if s.phase == "place":
            seat = ns.place_order.pop(0)
            ns.rings[seat] = parse_cell(move)
            ns.last = [move]
            if not ns.place_order:
                ns.phase = "move"
                ns.turn = seat           # last player to place moves first
            return ns

        seat = ns.turn

        # ----- pass -----
        if move == "pass":
            ns.prev_step[seat] = False
            ns.passes += 1
            ns.plies += 1
            ns.last = []
            if ns.passes >= self.num_players:
                ns.over = True
            elif ns.plies >= PLY_CAP:
                ns.over = True
            ns.turn = 1 - seat
            return ns

        is_jump = move.endswith("=J")
        core = move[:-2] if is_jump else move
        path = [parse_cell(p) for p in core.split(">")]
        ring = path[0]

        if not is_jump:
            # ----- single step (no capture) -----
            ns.rings[seat] = path[1]
            ns.prev_step[seat] = True
        else:
            # ----- jump chain -----
            visited = path
            line = self._line_stones(s.stones, path[0], path[1])
            had_black = any(s.stones.get(c) == "B" for c in visited)
            newly = [c for c in visited if s.stones.get(c) == "W"]
            complete = (set(visited) == set(line)
                        and not had_black
                        and s.prev_step[seat])
            for c in newly:
                ns.stones[c] = "B"           # capture: white -> black
            if complete:
                ns.piles[seat][0] += len(newly)
            else:
                ns.piles[seat][1] += len(newly)
            ns.rings[seat] = path[-1]
            ns.prev_step[seat] = False

        ns.passes = 0
        ns.plies += 1
        ns.last = [cell_str(c) for c in path]
        if ns.plies >= PLY_CAP:
            ns.over = True
        ns.turn = 1 - seat
        return ns

    # ---- scoring ---------------------------------------------------------
    def _score(self, s: LLState, seat: int) -> int:
        return s.piles[seat][0] * 2 + s.piles[seat][1]

    def returns(self, s: LLState) -> list[float]:
        a, b = self._score(s, 0), self._score(s, 1)
        if a == b:
            return [0.0, 0.0]
        return [1.0, -1.0] if a > b else [-1.0, 1.0]

    def heuristic(self, s: LLState) -> list[float]:
        import math
        d = self._score(s, 0) - self._score(s, 1)
        v = math.tanh(d / 6.0)
        return [v, -v]

    # ---- serialize -------------------------------------------------------
    def serialize(self, s: LLState) -> dict:
        return {
            "stones": {cell_str(c): v for c, v in s.stones.items()},
            "rings": [cell_str(r) if r is not None else None for r in s.rings],
            "phase": s.phase,
            "place_order": list(s.place_order),
            "turn": s.turn,
            "piles": [list(s.piles[0]), list(s.piles[1])],
            "prev_step": list(s.prev_step),
            "passes": s.passes,
            "plies": s.plies,
            "over": s.over,
            "last": list(s.last),
        }

    def deserialize(self, d: dict) -> LLState:
        return LLState(
            stones={parse_cell(k): v for k, v in d["stones"].items()},
            rings=[parse_cell(r) if r is not None else None for r in d["rings"]],
            phase=d["phase"],
            place_order=list(d["place_order"]),
            turn=d["turn"],
            piles=[list(d["piles"][0]), list(d["piles"][1])],
            prev_step=list(d["prev_step"]),
            passes=d["passes"],
            plies=d["plies"],
            over=d["over"],
            last=list(d.get("last", [])),
        )

    # ---- move description ------------------------------------------------
    def describe_move(self, s: LLState, move: str) -> str:
        who = SEAT_NAME[self.current_player(s)][-1]  # "1" or "2"
        if s.phase == "place":
            return f"P{who} ring @ {move}"
        if move == "pass":
            return f"P{who} pass"
        is_jump = move.endswith("=J")
        core = move[:-2] if is_jump else move
        cells = core.split(">")
        if is_jump:
            return f"P{who} jump {'-'.join(cells)}"
        return f"P{who} step {cells[0]}->{cells[1]}"

    # ---- render ----------------------------------------------------------
    def _hex_points(self, c, r):
        import math
        # pointy-top hex, size 1; odd rows shifted right by SQRT3/2.
        s3 = math.sqrt(3.0)
        cx = s3 * (c + 0.5 * (r & 1))
        cy = 1.5 * r
        pts = []
        for k in range(6):
            ang = math.radians(60 * k - 30)   # -30,30,90,... : flat sides L/R, vertex up/down
            pts.append([round(cx + math.cos(ang), 4), round(cy + math.sin(ang), 4)])
        return pts

    def render(self, s: LLState, perspective=None) -> dict:
        cells = [{"id": f"{c},{r}", "points": self._hex_points(c, r)}
                 for r in range(SIZE) for c in range(SIZE)]
        # muted 6x6 zone tints (checkerboard), cosmetic — zones only matter at deal.
        tints = {}
        for c in range(SIZE):
            for r in range(SIZE):
                zc, zr = zone_of(c, r)
                tints[f"{c},{r}"] = "#26343f" if (zc + zr) % 2 == 0 else "#26382b"

        ring_cells = {s.rings[i]: i for i in range(2) if s.rings[i] is not None}
        pieces = []
        for (c, r), col in s.stones.items():
            if (c, r) in ring_cells:
                continue                       # drawn as ring-with-marker below
            pieces.append({"cell": f"{c},{r}", "owner": 0,
                           "fill": "#f2f2ee" if col == "W" else "#1c1c1c",
                           "stroke": "#555" if col == "W" else "#000"})
        for cell, seat in ring_cells.items():
            p = {"cell": cell_str(cell), "owner": seat, "shape": "ring"}
            st = s.stones.get(cell)
            if st is not None:
                p["label"] = "○" if st == "W" else "●"  # ○ white / ● black
            pieces.append(p)

        highlights = [{"cell": c, "kind": "last-move"} for c in s.last]

        sc0, sc1 = self._score(s, 0), self._score(s, 1)
        if s.over:
            if sc0 == sc1:
                cap = f"Game over — draw {sc0}-{sc1}"
            else:
                w = 0 if sc0 > sc1 else 1
                cap = f"Game over — {SEAT_NAME[w]} wins {max(sc0,sc1)}-{min(sc0,sc1)}"
        elif s.phase == "place":
            cap = f"{SEAT_NAME[self.current_player(s)]}: place your ring"
        else:
            cap = f"{SEAT_NAME[s.turn]} to move  (score {sc0}-{sc1})"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
            "choiceNames": {"J": "Jump (capture)"},
        }
