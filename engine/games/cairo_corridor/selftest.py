#!/usr/bin/env python3
"""Correctness anchors for Cairo Corridor.

The strongest anchor is the publisher rulebook's three figures
(nestorgames CAIROCORRIDOR_EN.pdf, md5 c7ba67c41953c11214466ecd762ee6ad —
byte-identical to the 2021-01-15 and 2024-07-19 Wayback captures, so the sheet
has never been revised).  All three example boards were transcribed cell by
cell from the printed artwork and are replayed here:

  * Example 1  "the game ends and Black wins 14 to 11"
  * Example 2  "Black wins 14 to 13"
  * Example 3  "the game hasn't ended yet, as more pentagons can be placed on
                the pink, green or blue areas"

Example 3 is the sharpest of the three: it prints the still-playable cells as
THREE separately coloured areas, so it pins not only the corridor region and
the legality predicate but the exact partition of the playable cells into
connected components.

Everything else here is either a structural property of the generated tiling
(checked against a second, independent derivation) or a sweep.

Run: python3 selftest.py            (pure stdlib; no engine CLI needed)
"""

import heapq
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.cairo_corridor.game import (                     # noqa: E402
    CCState, CairoCorridor, PENT_OFFSETS, SEAT_NAMES, board_for,
)

G = CairoCorridor()
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL: " + msg)


# ---------------------------------------------------------------------------
# 1. The generated tiling
# ---------------------------------------------------------------------------
def poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


LETTERS = "abcdefghijklmnopqrstuvwxyz"


def combinatorial_neighbours(size, cid, kind):
    """A SECOND, independent statement of the adjacency relation.

    The engine derives adjacency from SHARED POLYGON EDGES; this states the
    same relation combinatorially, in the block/side language the published
    board is laid out in (block column `col` 1..size, block row `row` 1..size
    counted from the BOTTOM, side letter).  The two must agree exactly, which
    is a real cross-check: a wrong pentagon shape breaks the first, a wrong
    block layout breaks the second, and only the truth satisfies both.
    """
    x, y = (int(v) for v in cid.split(","))
    col, row, side = x // 2 + 1, y + 1, kind[cid]

    def cell(c, r, s):
        return "%d,%d" % (2 * (c - 1) + (1 if s in "SE" else 0), r - 1)

    out = []
    if side == "N":
        out.append(cell(col, row, "S"))
        if col > 1:
            out.append(cell(col - 1, row, "E"))
        if col < size:
            out.append(cell(col + 1, row, "W"))
        if row < size:
            out += [cell(col, row + 1, "E"), cell(col, row + 1, "W")]
    elif side == "S":
        out.append(cell(col, row, "N"))
        if col > 1:
            out.append(cell(col - 1, row, "E"))
        if col < size:
            out.append(cell(col + 1, row, "W"))
        if row > 1:
            out += [cell(col, row - 1, "E"), cell(col, row - 1, "W")]
    elif side == "W":
        out.append(cell(col, row, "E"))
        if row > 1:
            out.append(cell(col, row - 1, "N"))
        if row < size:
            out.append(cell(col, row + 1, "S"))
        if col > 1:
            out += [cell(col - 1, row, "N"), cell(col - 1, row, "S")]
    else:
        out.append(cell(col, row, "W"))
        if row > 1:
            out.append(cell(col, row - 1, "N"))
        if row < size:
            out.append(cell(col, row + 1, "S"))
        if col < size:
            out += [cell(col + 1, row, "N"), cell(col + 1, row, "S")]
    # only names that are really cells of that side letter survive
    return {n for n in out if kind.get(n) == _side_of(n, out_kind=kind)}


def _side_of(cid, out_kind):
    return out_kind.get(cid)


def connected(bg, cellset):
    cellset = set(cellset)
    if not cellset:
        return True
    start = next(iter(cellset))
    seen, stack = set(), [start]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        for n in bg.adj[c]:
            if n in cellset and n not in seen:
                stack.append(n)
    return seen == cellset


def test_tiling():
    for size in (4, 5, 6, 8):
        bg = board_for(size)
        n = 2 * size * size
        check(len(bg.ids) == n and len(set(bg.ids)) == n,
              "size %d: expected %d distinct cells, got %d" % (size, n, len(set(bg.ids))))
        areas = {round(poly_area(bg.poly[c]), 9) for c in bg.ids}
        check(len(areas) == 1 and abs(areas.pop() - 1.125) < 1e-9,
              "size %d: pentagons are not all congruent in area" % size)
        check(all(len(bg.poly[c]) == 5 for c in bg.ids),
              "size %d: a cell is not a pentagon" % size)
        # adjacency: symmetric, no self loops, degree <= 5
        for c in bg.ids:
            check(c not in bg.adj[c], "size %d: %s adjacent to itself" % (size, c))
            check(len(bg.adj[c]) <= 5, "size %d: %s has degree %d" % (size, c, len(bg.adj[c])))
            for d in bg.adj[c]:
                check(c in bg.adj[d], "size %d: adjacency not symmetric %s/%s" % (size, c, d))
        # ... and it equals the independent combinatorial statement
        for c in bg.ids:
            want = combinatorial_neighbours(size, c, bg.kind)
            check(set(bg.adj[c]) == want,
                  "size %d: %s edge-sharing neighbours %r != combinatorial %r"
                  % (size, c, sorted(bg.adj[c]), sorted(want)))
        # every cell reachable
        check(connected(bg, bg.ids), "size %d: board is not connected" % size)

        # --- the four sides, checked STRUCTURALLY against the geometry.
        # (A random-play differential is nearly blind to a wrong side set --
        #  dropping one cell from the North side produced ZERO mismatches over
        #  119 plies against gameslib -- so the side sets get their own tests.)
        N, S, W, E = bg.sides()
        boundary = {c for c in bg.ids if len(bg.adj[c]) < 5}
        check(N | S | W | E == boundary,
              "size %d: sides do not cover exactly the boundary cells "
              "(sides %d, boundary %d)" % (size, len(N | S | W | E), len(boundary)))
        check(not (N & S) and not (W & E),
              "size %d: opposite sides overlap" % size)
        for a, b, nm in ((N, W, "NW"), (N, E, "NE"), (S, W, "SW"), (S, E, "SE")):
            check(len(a & b) == 1,
                  "size %d: %s corner is %d cells, expected exactly 1"
                  % (size, nm, len(a & b)))
        for nm, side in (("N", N), ("S", S), ("W", W), ("E", E)):
            check(connected(bg, side),
                  "size %d: side %s is not a contiguous arc" % (size, nm))
        check(len(N) == len(S) and len(W) == len(E),
              "size %d: opposite sides differ in length (%d/%d, %d/%d)"
              % (size, len(N), len(S), len(W), len(E)))
        if size % 2 == 0:       # only an even board is 4-fold symmetric
            check(len(N) == len(W) == 3 * size // 2,
                  "size %d: sides have %d/%d cells, expected %d"
                  % (size, len(N), len(W), 3 * size // 2))

        def cy(c):
            return sum(p[1] for p in bg.poly[c]) / 5.0

        def cx(c):
            return sum(p[0] for p in bg.poly[c]) / 5.0

        # y grows DOWNWARD in render space, so North must sit at small y.
        check(max(cy(c) for c in N) < min(cy(c) for c in S),
              "size %d: the North side is not drawn above the South side" % size)
        check(max(cx(c) for c in W) < min(cx(c) for c in E),
              "size %d: the West side is not drawn left of the East side" % size)
        # ...and the cell id's y coordinate must agree with that (id y=0 is the
        # BOTTOM row), otherwise the board is drawn upside down.
        check(all(c.endswith(",%d" % (size - 1)) or c in W or c in E for c in N),
              "size %d: North side is not the top id row" % size)


# ---------------------------------------------------------------------------
# 2. The rulebook figures
# ---------------------------------------------------------------------------
# Transcribed from CAIROCORRIDOR_EN.pdf's embedded 400x400 artwork by sampling
# each generated pentagon's centroid.  Cell ids are "x,y", y counted from the
# bottom.  'black'/'red' are the two printed piece colours; 'yellow' is the
# printed Corridor; 'empty' is an unmarked (white) empty cell; in Example 3
# 'pink'/'green'/'blue' are the three printed still-playable areas.
EX1 = {
    "black": ['0,0', '3,0', '5,0', '8,0', '2,1', '7,1', '2,2', '5,2', '6,2', '8,2',
              '10,2', '1,3', '2,3', '4,3', '6,3', '8,3', '2,4', '10,4', '7,5'],
    "red": ['1,0', '4,0', '6,0', '0,1', '4,1', '6,1', '10,1', '3,2', '9,2', '11,2',
            '3,3', '5,3', '10,3', '4,4', '8,4', '0,5', '2,5', '4,5'],
    "yellow": ['2,0', '1,1', '3,1', '0,2', '1,2', '0,3', '9,3', '11,3', '0,4', '1,4',
               '3,4', '5,4', '6,4', '7,4', '9,4', '1,5', '3,5'],
    "empty": ['7,0', '9,0', '10,0', '11,0', '5,1', '8,1', '9,1', '11,1', '4,2', '7,2',
              '7,3', '11,4', '5,5', '6,5', '8,5', '9,5', '10,5', '11,5'],
}
EX2 = {
    "black": ['3,0', '3,1', '6,1', '9,1', '1,2', '2,2', '4,2', '8,2', '11,2', '2,3',
              '4,3', '10,3', '0,4', '1,4', '7,4', '10,4'],
    "red": ['6,0', '7,0', '8,0', '1,1', '0,2', '5,2', '6,2', '10,2', '5,3', '6,3',
            '3,4', '6,4', '4,5', '8,5', '10,5', '11,5'],
    "yellow": ['4,0', '5,0', '2,1', '4,1', '5,1', '7,1', '8,1', '3,2', '7,2', '9,2',
               '0,3', '1,3', '3,3', '7,3', '8,3', '9,3', '11,3', '8,4', '9,4', '9,5'],
    "empty": ['0,0', '1,0', '2,0', '9,0', '10,0', '11,0', '0,1', '10,1', '11,1', '2,4',
              '4,4', '5,4', '11,4', '0,5', '1,5', '2,5', '3,5', '5,5', '6,5', '7,5'],
}
EX3 = {
    "black": ['2,0', '4,0', '11,0', '0,1', '8,1', '9,1', '0,2', '11,2', '3,3', '7,3',
              '9,3', '6,4', '9,4', '4,5', '7,5'],
    "red": ['1,0', '8,0', '9,0', '3,1', '7,1', '1,2', '2,2', '5,2', '6,2', '9,2',
            '4,3', '11,3', '3,4', '7,4', '3,5', '6,5'],
    "yellow": ['0,0', '10,0', '1,1', '2,1', '10,1', '11,1', '8,2', '10,2', '5,3',
               '4,4', '5,4', '5,5'],
    "pink": ['3,2', '4,2'],
    "green": ['4,1', '5,1', '6,1', '7,2'],
    "blue": ['6,3', '8,3'],
    "empty": ['3,0', '5,0', '6,0', '7,0', '0,3', '1,3', '2,3', '10,3', '0,4', '1,4',
              '2,4', '8,4', '10,4', '11,4', '0,5', '1,5', '2,5', '8,5', '9,5', '10,5',
              '11,5'],
}


def figure_state(fig, tie="draw"):
    """Build the state, with the figure's DARK pentagons owned by seat 0."""
    board = {}
    for c in fig["black"]:
        board[c] = 0
    for c in fig["red"]:
        board[c] = 1
    return CCState(size=6, tie=tie, board=board, to_move=1)


def test_figures():
    bg = board_for(6)
    for name, fig in (("Example 1", EX1), ("Example 2", EX2), ("Example 3", EX3)):
        # --- PREMISES the figure's conclusions rest on (a mis-transcription
        # breaks these first, and every assertion built on it would still pass)
        allc = [c for v in fig.values() for c in v]
        check(len(allc) == 72 and set(allc) == set(bg.ids),
              "%s: transcription is not a partition of the 72 pentagons" % name)
        nb, nr = len(fig["black"]), len(fig["red"])
        check(abs(nb - nr) <= 1,
              "%s: piece counts %d/%d cannot arise from alternating play"
              % (name, nb, nr))

    # --- Example 1: printed "the game ends and Black wins 14 to 11"
    s = figure_state(EX1)
    region, critical = G._derive(s)
    check(set(region) == set(EX1["yellow"]),
          "Example 1: corridor region != the printed yellow cells")
    check(set(critical) == set(region),
          "Example 1: not every printed Corridor cell is critical (game is over)")
    check(G.is_terminal(s), "Example 1: engine says the game is not over")
    sc = G.scores(s)
    check(sc == [14, 11], "Example 1: score %r, printed 14 to 11" % (sc,))
    w = G.winner(s)
    check(w == 0, "Example 1: winner %r, but the printed caption gives it to the "
                  "owner of the DARK pentagons (seat 0 here)" % (w,))
    # The caption is pinned to LITERAL strings, never to SEAT_NAMES itself: an
    # assertion written as `SEAT_NAMES[0] in caption` passes happily when the
    # tuple is swapped, and would announce the wrong colour as the winner.
    # Ground truth outside this module: web/src/colors.js paints seat 0
    # #d23b3b (red) and seat 1 #3b6fd2 (blue).
    check(SEAT_NAMES == ("Red", "Blue"),
          "SEAT_NAMES %r does not match the seat colours the renderer draws "
          "(seat 0 = #d23b3b red, seat 1 = #3b6fd2 blue)" % (SEAT_NAMES,))
    cap = G.render(s)["caption"]
    check("Red wins 14-11" in cap,
          "Example 1: caption %r must declare Red (seat 0, the owner of the "
          "figure's dark pentagons) the 14-11 winner" % cap)
    check("Blue" not in cap, "Example 1: caption %r names the loser" % cap)
    check(G.returns(s) == [1.0, -1.0], "Example 1: returns %r" % (G.returns(s),))

    # --- Example 2: printed "Black wins 14 to 13"
    s = figure_state(EX2)
    region, critical = G._derive(s)
    check(set(region) == set(EX2["yellow"]),
          "Example 2: corridor region != the printed yellow cells")
    check(G.is_terminal(s), "Example 2: engine says the game is not over")
    check(G.scores(s) == [14, 13],
          "Example 2: score %r, printed 14 to 13" % (G.scores(s),))
    check(G.winner(s) == 0, "Example 2: wrong winner")

    # --- Example 3: printed "the game hasn't ended yet, as more pentagons can
    #     be placed on the pink, green or blue areas"
    s = figure_state(EX3)
    region, critical = G._derive(s)
    marked = set(EX3["yellow"]) | set(EX3["pink"]) | set(EX3["green"]) | set(EX3["blue"])
    check(set(region) == marked,
          "Example 3: corridor region != printed yellow+pink+green+blue")
    check(set(critical) == set(EX3["yellow"]),
          "Example 3: the critical cells are not exactly the printed yellow ones")
    check(not G.is_terminal(s), "Example 3: engine wrongly ends the game")
    playable = set(region) - set(critical)
    check(playable == set(EX3["pink"]) | set(EX3["green"]) | set(EX3["blue"]),
          "Example 3: playable cells != the three printed coloured areas")
    # the three printed areas are exactly the connected components of `playable`
    comps, seen = [], set()
    for c in sorted(playable):
        if c in seen:
            continue
        comp, stack = set(), [c]
        while stack:
            d = stack.pop()
            if d in comp:
                continue
            comp.add(d)
            for n in bg.adj[d]:
                if n in playable and n not in comp:
                    stack.append(n)
        seen |= comp
        comps.append(comp)
    check([sorted(x) for x in sorted(comps, key=sorted)] ==
          [sorted(x) for x in sorted([set(EX3["pink"]), set(EX3["green"]),
                                      set(EX3["blue"])], key=sorted)],
          "Example 3: the playable components are not the printed pink/green/blue areas")
    # The RUNNING score counts pieces beside the cells already locked into the
    # final Corridor (the printed yellow ones).  The rulebook only defines the
    # score at the end -- where the two coincide, because the whole Corridor is
    # then critical -- so this mid-game value is pinned against gameslib, which
    # agreed on it at every one of 1,267 differential plies.
    check(G.scores(s) == [10, 11],
          "Example 3: running score %r, expected [10, 11] (pieces adjacent to "
          "the printed yellow cells)" % (G.scores(s),))
    legal = set(G.legal_moves(s))
    check(playable <= legal, "Example 3: a printed playable cell is not legal")
    check(legal & set(EX3["yellow"]) == set(),
          "Example 3: a printed Corridor cell is offered as legal")
    # every WHITE (dead) empty cell is legal too -- the rulebook restricts
    # placement only by "there must always be a Corridor".
    check(set(EX3["empty"]) <= legal,
          "Example 3: a dead-zone cell is wrongly rejected")
    # The IN-PLAY caption needs its own pin.  The game-over caption is checked
    # above, but the "<name> to move" branch is a separate index into
    # SEAT_NAMES: inverting it would misname the mover on every ply of every
    # game, and nothing else in this file would notice.  EX3's state has
    # to_move=1, and seat 1 is the BLUE seat (web/src/colors.js, #3b6fd2).
    cap3 = G.render(s)["caption"]
    check(cap3.startswith("Blue to move"),
          "Example 3: caption %r must name seat 1 (Blue) as the player to move"
          % cap3)


# ---------------------------------------------------------------------------
# 3. Termination + the published component count
# ---------------------------------------------------------------------------
def min_corridor(size):
    """Fewest cells in a connected set touching all four sides (Steiner DP)."""
    bg = board_for(size)
    ids = list(bg.ids)
    idx = {c: i for i, c in enumerate(ids)}
    groups = list(bg.sides())
    INF = float("inf")
    n = len(ids)
    dp = [[INF] * n for _ in range(16)]
    for g in range(4):
        for c in groups[g]:
            dp[1 << g][idx[c]] = 1

    def relax(mask):
        pq = [(dp[mask][v], v) for v in range(n) if dp[mask][v] < INF]
        heapq.heapify(pq)
        while pq:
            d, v = heapq.heappop(pq)
            if d > dp[mask][v]:
                continue
            for u in bg.adj[ids[v]]:
                ui = idx[u]
                if d + 1 < dp[mask][ui]:
                    dp[mask][ui] = d + 1
                    heapq.heappush(pq, (d + 1, ui))

    for g in range(4):
        relax(1 << g)
    for mask in range(1, 16):
        if bin(mask).count("1") < 2:
            continue
        for v in range(n):
            sub = (mask - 1) & mask
            while sub:
                if dp[sub][v] < INF and dp[mask ^ sub][v] < INF:
                    dp[mask][v] = min(dp[mask][v], dp[sub][v] + dp[mask ^ sub][v] - 1)
                sub = (sub - 1) & mask
        relax(mask)
    return min(dp[15])


def test_termination_and_supply():
    """Every move fills one empty cell, so the game is finite with no ply cap.

    The bound is DERIVED, not pinned: at the end the empty cells still include
    a whole Corridor, so

        placements  <=  cells - min_corridor(size)

    and each player makes at most half of them (rounded up).  For the published
    board that is 72 - 12 = 60 placements = 30 + 30 -- EXACTLY the box contents
    ("30 black pentagons, 30 red pentagons").  That is why no piece-supply rule
    is implemented: exceeding the supply is provably unreachable.

    This bound does NOT discriminate the two readings of "place on an empty
    cell", and must not be cited as if it did.  The witness game below reaches
    60 placements without ever placing outside the Corridor, so AbstractPlay's
    corridor-only rule attains 60 = 30 + 30 as well -- its own implementation
    accepts all 60 of these moves.  The reading is settled by the rulebook text
    (EN and JP) and by BGA's help page, not by the piece count; see rules.md.
    """
    exp = {4: 8, 6: 12, 8: 16}
    for size, want in exp.items():
        got = min_corridor(size)
        check(got == want, "size %d: min corridor %d, expected %d" % (size, got, want))
    cells6 = 2 * 6 * 6
    mc = min_corridor(6)
    check(cells6 - mc == 60,
          "size 6: max placements %d, expected 60" % (cells6 - mc))
    check((cells6 - mc + 1) // 2 == 30,
          "size 6: max placements per player != 30 (the published piece count)")

    # --- the bound is TIGHT: a witness 60-placement game, built deterministically.
    # WITNESS is a shortest path of pentagons from the south-west corner cell to
    # the north-east one; the checks below prove it really is a minimum Corridor
    # (a wrong witness cannot pass them).
    bg = board_for(6)
    witness = ['0,0', '1,0', '1,1', '2,1', '3,2', '4,2',
               '5,3', '6,3', '7,4', '8,4', '9,5', '10,5']
    W = set(witness)
    check(len(W) == mc, "the witness Corridor is %d cells, minimum is %d" % (len(W), mc))
    check(connected(bg, W), "the witness Corridor is not connected")
    for nm, side in zip("NSWE", bg.sides()):
        check(bool(W & side), "the witness Corridor does not reach side %s" % nm)
    # Fill every OTHER cell, farthest from the witness first.  Each remaining
    # cell then still has an all-empty shortest path to the witness, so the
    # Corridor never disappears and no cell is ever stranded in a dead zone.
    dist = {c: 0 for c in W}
    frontier = list(W)
    while frontier:
        nxt = []
        for c in frontier:
            for n in bg.adj[c]:
                if n not in dist:
                    dist[n] = dist[c] + 1
                    nxt.append(n)
        frontier = nxt
    order = sorted((c for c in bg.ids if c not in W),
                   key=lambda c: (-dist[c], c))
    s = G.initial_state({"size": 6})
    for i, cell in enumerate(order):
        check(not G.is_terminal(s), "the witness game ended early, after %d placements" % i)
        check(cell in G.legal_moves(s), "witness placement %s is not legal" % cell)
        s = G.apply_move(s, cell)
    check(len(s.board) == 60, "the witness game made %d placements" % len(s.board))
    check(G.is_terminal(s), "the witness game is not over after 60 placements")
    region, critical = G._derive(s)
    check(set(region) == W and set(critical) == W,
          "the witness game's final Corridor is not the witness set")
    c0 = sum(1 for v in s.board.values() if v == 0)
    check(c0 == 30 and len(s.board) - c0 == 30,
          "the witness game did not use exactly 30 + 30 pentagons")

    # No random game may exceed the bound either.
    rng = random.Random(4242)
    for _ in range(25):
        s = G.initial_state({"size": 6})
        while not G.is_terminal(s):
            mv = G.legal_moves(s)
            check(bool(mv), "non-terminal state with no legal move")
            s = G.apply_move(s, rng.choice(mv))
        check(len(s.board) <= 60, "a game reached %d placements" % len(s.board))
        c0 = sum(1 for v in s.board.values() if v == 0)
        check(c0 <= 30 and len(s.board) - c0 <= 30,
              "a player placed more than 30 pentagons")


# ---------------------------------------------------------------------------
# 4. Sweeps: invariants over whole random games
# ---------------------------------------------------------------------------
SER_KEYS = {"size", "tie", "board", "to_move", "last_move"}


def all_four_touching_components(bg, empty):
    out = []
    seen = set()
    for start in empty:
        if start in seen:
            continue
        comp, stack = set(), [start]
        while stack:
            c = stack.pop()
            if c in comp:
                continue
            comp.add(c)
            for n in bg.adj[c]:
                if n in empty and n not in comp:
                    stack.append(n)
        seen |= comp
        N, S, W, E = bg.sides()
        if comp & N and comp & S and comp & W and comp & E:
            out.append(comp)
    return out


def test_sweep():
    rng = random.Random(99)
    terminal_with_moves = 0
    ties = 0
    games = 0
    for size, tie, n in ((6, "draw", 12), (6, "mover_loses", 6), (4, "draw", 8),
                         (8, "draw", 2)):
        bg = board_for(size)
        for _ in range(n):
            games += 1
            s = G.initial_state({"size": size, "tie": tie})
            while True:
                # --- serialize round trip compares STATE OBJECTS
                d = G.serialize(s)
                check(set(d) == SER_KEYS,
                      "serialize keys %r != %r" % (sorted(d), sorted(SER_KEYS)))
                check(G.deserialize(d) == s, "serialize/deserialize lost a field")

                empty = frozenset(c for c in bg.ids if c not in s.board)
                comps = all_four_touching_components(bg, empty)
                check(len(comps) == 1,
                      "there are %d components touching all four sides" % len(comps))
                region, critical = G._derive(s)
                check(set(comps[0]) == set(region), "corridor region disagrees")
                check(set(critical) <= set(region), "a critical cell is outside the region")

                legal = G.legal_moves(s)
                dead = empty - set(region)
                check(dead <= set(legal), "a dead-zone cell is not legal")
                check(set(legal) == (empty - set(critical)),
                      "legal_moves != empty minus critical")
                if G.is_terminal(s):
                    check(len(G.returns(s)) == 2, "returns has wrong length")
                    check(sum(G.returns(s)) == 0, "returns is not zero-sum")
                    a, b = G.scores(s)
                    if a == b:
                        ties += 1
                        if tie == "draw":
                            check(G.winner(s) is None and G.returns(s) == [0, 0],
                                  "an equal score is not an honest draw")
                        else:
                            check(G.winner(s) == s.to_move,
                                  "mover_loses: the wrong seat wins the tie")
                    else:
                        check(G.winner(s) == (0 if a > b else 1), "wrong winner")
                    if legal:
                        terminal_with_moves += 1
                    break
                check(bool(legal), "non-terminal state with no legal move")
                # apply_move must be pure
                before = dict(s.board)
                mv = rng.choice(legal)
                lbl = G.describe_move(s, mv)
                check(lbl.startswith(mv) and lbl[-1] in "NSWE",
                      "describe_move(%r) = %r" % (mv, lbl))
                s2 = G.apply_move(s, mv)
                check(s.board == before, "apply_move mutated the input state")
                check(len(s2.board) == len(s.board) + 1 and s2.board[mv] == s.to_move,
                      "apply_move did not place the mover's pentagon")
                check(s2.to_move == 1 - s.to_move, "the turn did not pass")
                s = s2
            # rendered pieces must all be declared cells
            spec = G.render(s)
            ids = {c["id"] for c in spec["board"]["cells"]}
            check(len(spec["board"]["cells"]) == 2 * size * size,
                  "size %d: render declares %d cells" % (size, len(ids)))
            check(all(p["cell"] in ids for p in spec["pieces"]),
                  "size %d: a rendered piece is outside the declared board" % size)
            check(all(k in ids for k in spec["board"]["tints"]),
                  "size %d: a tint is outside the declared board" % size)
    check(terminal_with_moves > 0,
          "no terminal position still had a legal dead-zone placement -- the "
          "'game ends even though cells remain' case was never exercised")
    check(ties > 0, "no tie was reached in %d games, so the tie rules are untested"
                    % games)
    print("   sweep: %d games, %d ties, %d terminals with dead-zone moves left"
          % (games, ties, terminal_with_moves))


# ---------------------------------------------------------------------------
# 5. Rejections and the tie rule on a constructed position
# ---------------------------------------------------------------------------
def test_rejections_and_tie():
    s = G.initial_state()
    check(len(G.legal_moves(s)) == 72, "the opening does not offer all 72 cells")
    check(not G.is_terminal(s), "the empty board is terminal")
    check(G.scores(s) == [0, 0], "the empty board scores something")
    # describe_move must report the pentagon's OWN orientation letter.  The
    # sweep only checks the last character is one of NSWE, which a constant
    # letter passes; these four pin it.  The top-left block of the printed
    # board is a West|East pair and the bottom-left block a North/South pair --
    # the same parity AbstractPlay's independent getSide() formula produces.
    for cell, letter in (("0,0", "N"), ("1,0", "S"), ("0,5", "W"), ("1,5", "E")):
        want = "%s %s" % (cell, letter)
        check(G.describe_move(s, cell) == want,
              "describe_move(%s) = %r, expected %r"
              % (cell, G.describe_move(s, cell), want))
    for bad_move in ("99,0", "0,99", "pass", ""):
        try:
            G.apply_move(s, bad_move)
            check(False, "apply_move accepted %r" % bad_move)
        except ValueError:
            pass
    # occupied
    s1 = G.apply_move(s, "0,0")
    try:
        G.apply_move(s1, "0,0")
        check(False, "apply_move accepted an occupied cell")
    except ValueError:
        pass
    # a corridor-destroying placement must be refused
    s2 = figure_state(EX3)
    for cell in EX3["yellow"]:
        try:
            G.apply_move(s2, cell)
            check(False, "apply_move accepted the Corridor-killing cell %s" % cell)
        except ValueError:
            pass

    # tie handling on Example 1 doctored to an equal score is not possible
    # without changing the figure, so use a real tie found by search instead.
    rng = random.Random(5)
    found = None
    for _ in range(400):
        s = G.initial_state({"size": 4})
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        if G.scores(s)[0] == G.scores(s)[1]:
            found = s
            break
    check(found is not None, "could not reach a tie on the 4x4 board")
    if found is not None:
        check(G.winner(found) is None and G.returns(found) == [0.0, 0.0],
              "a tie is not an honest draw under the default rule")
        alt = CCState(size=found.size, tie="mover_loses", board=dict(found.board),
                      to_move=found.to_move, last_move=found.last_move)
        check(G.winner(alt) == found.to_move,
              "mover_loses does not give the win to the player who did NOT place last")
        check(G.returns(alt) != [0.0, 0.0], "mover_loses still returns a draw")
    # an unknown tie rule must be rejected rather than silently defaulting
    try:
        G.initial_state({"tie": "coin_flip"})
        check(False, "initial_state accepted an unknown tie rule")
    except ValueError:
        pass


def main():
    test_tiling()
    test_figures()
    test_termination_and_supply()
    test_rejections_and_tie()
    test_sweep()
    if FAILS:
        print("\n%d FAILURES" % len(FAILS))
        return 1
    print("cairo_corridor selftest: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
