#!/usr/bin/env python3
"""Correctness anchors for Minefield (Mark Steere, 2024).

Pure stdlib. The two strongest anchors are the official rule sheet's own
figures, transcribed from the vector artwork of Minefield_rules.pdf (each disc
and dot parsed out of `pdftocairo -svg` output, not read off pixels):

  * FIGURE 2 "Prohibited glyphs" — the three printed glyphs (one hard corner,
    one 2x3 "short" switch, one 2x4 "long" switch) with their 1+2+4 = 7 blue
    unoccupied-point dots.
  * FIGURE 3 "Black placements" — a 9x9 position in which the 13 red dots are
    ALL of Black's illegal placements and two green dots are legal ones. The
    figure's PREMISES are asserted too (equal stone counts => Black to move,
    the position itself glyph-free, 26 stones / 55 empty points), because a
    mis-transcribed board would satisfy every assertion built on it.
  * FIGURE 1 "Black wins" — an orthogonally connected Black win, 13 black vs
    12 white stones (Black has just moved), White not connected.

plus a complete enumeration of every reachable 3x3 position, the pie-rule
symmetry, the crosscut-impossibility argument, serialization, render bounds at
every offered board size, and the ply bound.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import random                                                   # noqa: E402
from games.minefield.game import (                              # noqa: E402
    BLACK, WHITE, SWITCH_DIMS, Minefield, MinefieldState, max_plies,
    _hard_corner_at, _switch_at, connects, forms_glyph, glyphs_on_board,
    placements,
)

G = Minefield()
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


def board_of(black, white):
    bd = {}
    for p in black:
        bd[p] = BLACK
    for p in white:
        bd[p] = WHITE
    return bd


# --------------------------------------------------------------------------
# FIGURE 2 — the two prohibited glyphs, exactly as printed
# --------------------------------------------------------------------------
# 9x9 figure; (col, row) with col left->right, row top->bottom.
FIG2_BLACK = [(1, 2), (3, 5), (2, 7), (7, 4), (6, 7)]
FIG2_WHITE = [(1, 1), (2, 2), (2, 5), (3, 7), (6, 4), (7, 7)]
FIG2_BLUE = [(2, 1), (2, 6), (3, 6), (6, 5), (6, 6), (7, 5), (7, 6)]  # unoccupied

fig2 = board_of(FIG2_BLACK, FIG2_WHITE)
check(len(FIG2_BLUE) == 7, "figure 2 has 7 blue dots (1 hard corner + 2 + 4 switch)")
check(all(p not in fig2 for p in FIG2_BLUE), "figure 2's blue dots are unoccupied points")
found = sorted(glyphs_on_board(fig2, 9))
check(found == [("hard", 1, 1), ("switch", 2, 3, 2, 5), ("switch", 2, 4, 6, 4)],
      f"figure 2 prints exactly one hard corner, one 2x3 and one 2x4 switch, got {found}")

# each glyph is destroyed by filling any one of its unoccupied points, and is
# the ONLY reason the last stone of it cannot be played
for glyph_cells, hole, colour in (
        ([(1, 1), (1, 2), (2, 2)], (2, 1), None),
):
    for c in (BLACK, WHITE):
        bd = {p: fig2[p] for p in glyph_cells}
        bd[hole] = c
        check(glyphs_on_board(bd, 9) == [],
              "filling a hard corner's empty point destroys the glyph")

# the hard corner is exactly reproducible from its own definition
hc = {(0, 0): WHITE, (0, 1): BLACK, (1, 1): WHITE}
check(_hard_corner_at(hc, 0, 0), "W./BW is a hard corner")
check(not _hard_corner_at({(0, 0): WHITE, (0, 1): WHITE, (1, 1): WHITE}, 0, 0),
      "three stones of ONE colour in a 2x2 is not a hard corner")
check(not _hard_corner_at({(0, 0): WHITE, (1, 1): WHITE}, 0, 0),
      "two stones in a 2x2 is not a hard corner")
check(not _hard_corner_at({(0, 0): WHITE, (1, 0): BLACK, (0, 1): BLACK, (1, 1): WHITE}, 0, 0),
      "a FULL 2x2 (crosscut) is not a hard corner — no unoccupied point")

# a 2x2 checkerboard is NOT a switch (the sheet says 2x3 or 2x4 only)
cross = {(0, 0): BLACK, (1, 0): WHITE, (0, 1): WHITE, (1, 1): BLACK}
check(glyphs_on_board(cross, 4) == [], "a bare crosscut is not itself a prohibited glyph")
# ... but it can never be built: every 3-stone predecessor IS a hard corner
for drop in list(cross):
    pred = {k: v for k, v in cross.items() if k != drop}
    check(_hard_corner_at(pred, 0, 0),
          f"removing {drop} from a crosscut leaves a hard corner (so crosscuts are unreachable)")

for keep in list(cross):                 # the 3-stone stage of any crosscut ...
    three = {k: v for k, v in cross.items() if k != keep}
    for third in three:                  # ... whichever stone completed it ...
        two = {k: v for k, v in three.items() if k != third}
        check(forms_glyph(two, 4, third[0], third[1], three[third]),
              "every 3-stone stage of a crosscut was illegal to form")

# switch geometry: 2x3 and 2x4 in both orientations, nothing wider
check(set(SWITCH_DIMS) == {(2, 3), (3, 2), (2, 4), (4, 2)},
      "switch areas are 2x3 / 2x4 and their rotations only")
sw25 = {(0, 0): BLACK, (1, 0): WHITE, (0, 4): WHITE, (1, 4): BLACK}
check(glyphs_on_board(sw25, 6) == [], "a 2x5 'switch' is NOT prohibited")
sw23 = {(0, 0): BLACK, (1, 0): WHITE, (0, 2): WHITE, (1, 2): BLACK}
check(_switch_at(sw23, 0, 0, 2, 3), "the printed 2x3 switch shape is a switch")
sw23_filled = dict(sw23)
sw23_filled[(0, 1)] = BLACK
check(not _switch_at(sw23_filled, 0, 0, 2, 3),
      "occupying a non-corner point stops it being a switch")
sw23_same = {(0, 0): BLACK, (1, 0): BLACK, (0, 2): WHITE, (1, 2): WHITE}
check(not _switch_at(sw23_same, 0, 0, 2, 3),
      "same-colour pairs on the SIDES (not the diagonals) is not a switch")

# --------------------------------------------------------------------------
# FIGURE 3 — the worked example: exactly which points Black may not play
# --------------------------------------------------------------------------
FIG3_BLACK = [(1, 0), (1, 1), (1, 4), (2, 1), (2, 6), (4, 0), (4, 8), (5, 4),
              (5, 8), (6, 0), (6, 1), (6, 6), (7, 3)]
FIG3_WHITE = [(0, 8), (1, 2), (1, 6), (2, 0), (3, 3), (3, 8), (4, 5), (5, 1),
              (5, 3), (6, 8), (7, 6), (8, 6), (8, 8)]
FIG3_RED = {(0, 2), (1, 5), (1, 7), (3, 0), (3, 5), (3, 7), (4, 3), (5, 2),
            (6, 3), (6, 7), (7, 5), (7, 7), (7, 8)}
FIG3_GREEN = {(2, 2), (5, 0)}

fig3 = board_of(FIG3_BLACK, FIG3_WHITE)
# --- the figure's PREMISES (a mis-transcription breaks these first) ---
check(len(FIG3_BLACK) == 13 and len(FIG3_WHITE) == 13,
      "figure 3 has equal stone counts (13/13) — consistent with BLACK to move")
check(len(fig3) == 26 and 81 - len(fig3) == 55, "figure 3: 26 stones, 55 empty points")
check(glyphs_on_board(fig3, 9) == [],
      "figure 3's position is itself glyph-free (a legal position)")
check(not FIG3_RED & set(fig3) and not FIG3_GREEN & set(fig3),
      "figure 3's dots all sit on unoccupied points")
check(not connects(fig3, BLACK, 9) and not connects(fig3, WHITE, 9),
      "figure 3 is not already won by either side")
# --- the outcome the figure illustrates ---
illegal = {p for p in [(c, r) for c in range(9) for r in range(9)]
           if p not in fig3 and forms_glyph(fig3, 9, p[0], p[1], BLACK)}
check(illegal == FIG3_RED,
      f"figure 3: Black's illegal set == the 13 red dots "
      f"(missing {sorted(FIG3_RED - illegal)}, extra {sorted(illegal - FIG3_RED)})")
legal = {(c, r) for (c, r) in placements(fig3, 9, BLACK)}
check(FIG3_GREEN <= legal, "figure 3: both green dots are legal for Black")
check(len(legal) == 55 - 13 == 42, f"figure 3: 42 legal Black placements, got {len(legal)}")

# --------------------------------------------------------------------------
# FIGURE 1 — "Black wins": orthogonal connection, and ONLY orthogonal
# --------------------------------------------------------------------------
FIG1_BLACK = [(5, 0), (5, 1), (5, 2), (4, 2), (3, 2), (3, 3), (4, 3), (3, 4),
              (3, 5), (3, 6), (3, 7), (4, 7), (4, 8)]
FIG1_WHITE = [(0, 4), (1, 4), (2, 4), (2, 5), (4, 5), (5, 5), (6, 4), (6, 5),
              (7, 4), (8, 4), (6, 7), (7, 7)]
fig1 = board_of(FIG1_BLACK, FIG1_WHITE)
check(len(FIG1_BLACK) == len(FIG1_WHITE) + 1,
      "figure 1: 13 black vs 12 white — Black has just placed the winning stone")
check(glyphs_on_board(fig1, 9) == [], "figure 1's position is glyph-free")
check(connects(fig1, BLACK, 9), "figure 1: Black connects top and bottom")
check(not connects(fig1, WHITE, 9), "figure 1: White does not connect left and right")

# orthogonal ONLY: a diagonal staircase does not connect (AbstractPlay's
# implementation gets this wrong; the rule sheet and design note do not)
stair = {(i, i): BLACK for i in range(9)}
check(not connects(stair, BLACK, 9), "a purely diagonal chain does NOT connect")
check(connects({(0, r): BLACK for r in range(9)}, BLACK, 9), "a file of black connects")
check(connects({(c, 0): WHITE for c in range(9)}, WHITE, 9), "a rank of white connects")
check(not connects({(c, 0): BLACK for c in range(9)}, BLACK, 9),
      "Black joins ROWS (top/bottom), not columns")
check(not connects({(0, r): WHITE for r in range(9)}, WHITE, 9),
      "White joins COLUMNS (left/right), not rows")

# --------------------------------------------------------------------------
# symmetry: the glyph set is closed under the whole dihedral group AND colour
# reversal (the sheet: "or their reflections, rotations, or color reversals")
# --------------------------------------------------------------------------
def d4(p, n, k):
    c, r = p
    if k & 4:
        c, r = r, c
    for _ in range(k & 3):
        c, r = n - 1 - r, c
    return (c, r)


rng = random.Random(4242)
n = 7
sym_checked = 0
for _ in range(120):
    bd = {}
    for _ in range(rng.randrange(4, 16)):
        bd[(rng.randrange(n), rng.randrange(n))] = rng.randrange(2)
    base = sorted((p, forms_glyph(bd, n, p[0], p[1], BLACK),
                   forms_glyph(bd, n, p[0], p[1], WHITE))
                  for p in [(c, r) for c in range(n) for r in range(n)] if p not in bd)
    for k in range(8):
        tb = {d4(p, n, k): v for p, v in bd.items()}
        for (tp, bb, ww) in [(d4(p, n, k), bb, ww) for p, bb, ww in base]:
            check(forms_glyph(tb, n, tp[0], tp[1], BLACK) == bb
                  and forms_glyph(tb, n, tp[0], tp[1], WHITE) == ww,
                  f"glyph legality is invariant under D4 element {k}")
            sym_checked += 1
    cb = {p: 1 - v for p, v in bd.items()}
    for (p, bb, ww) in base:
        check(forms_glyph(cb, n, p[0], p[1], WHITE) == bb
              and forms_glyph(cb, n, p[0], p[1], BLACK) == ww,
              "glyph legality is invariant under colour reversal")
        sym_checked += 1

# --------------------------------------------------------------------------
# the fast LOCAL legality test must agree with a naive WHOLE-BOARD rescan
# (forms_glyph only inspects areas containing the point; glyphs_on_board scans
# everything).  Checked on glyph-free boards, which is the only state real play
# ever produces.
# --------------------------------------------------------------------------
local_vs_global = 0
for _ in range(150):
    n = rng.choice((5, 6, 7))
    bd = {}
    for _ in range(rng.randrange(2, n * n)):
        p = (rng.randrange(n), rng.randrange(n))
        bd[p] = rng.randrange(2)
        if glyphs_on_board(bd, n):      # keep the board glyph-free, as in play
            del bd[p]
    check(glyphs_on_board(bd, n) == [], "the constructed sample board is glyph-free")
    for c in range(n):
        for r in range(n):
            if (c, r) in bd:
                continue
            for who in (BLACK, WHITE):
                bd[(c, r)] = who
                naive = bool(glyphs_on_board(bd, n))
                del bd[(c, r)]
                check(forms_glyph(bd, n, c, r, who) == naive,
                      f"local legality == whole-board rescan at {(c, r)} for {who}")
                local_vs_global += 1
check(local_vs_global > 4000, f"local-vs-global comparisons {local_vs_global}")

# --------------------------------------------------------------------------
# complete enumeration of every reachable 3x3 position
# --------------------------------------------------------------------------
seen = set()
stats = {"nodes": 0, "wins": [0, 0], "stalls": 0, "skips": 0, "maxply": 0}


def walk(bd, to_move, ply):
    key = (frozenset(bd.items()), to_move)
    if key in seen:
        return
    seen.add(key)
    stats["nodes"] += 1
    stats["maxply"] = max(stats["maxply"], ply)
    mine = placements(bd, 3, to_move)
    if not mine:
        if placements(bd, 3, 1 - to_move):
            stats["skips"] += 1
            walk(bd, 1 - to_move, ply)      # a skip is not a ply
        else:
            stats["stalls"] += 1
        return
    for (c, r) in mine:
        bd[(c, r)] = to_move
        if connects(bd, to_move, 3):
            stats["wins"][to_move] += 1
        else:
            walk(bd, 1 - to_move, ply + 1)
        del bd[(c, r)]


walk({}, BLACK, 0)
check(stats["nodes"] == 2980, f"3x3: 2980 reachable (board, to-move) nodes, got {stats['nodes']}")
check(stats["wins"] == [801, 422], f"3x3 winning terminals [801, 422], got {stats['wins']}")
check(stats["skips"] == 86, f"3x3: 86 reachable skip nodes, got {stats['skips']}")
check(stats["stalls"] == 0, "3x3: NO reachable position stalls both players (no draws)")
check(stats["maxply"] == 8, f"3x3: deepest non-terminal is ply 8, got {stats['maxply']}")


def solve3(bd, to_move, memo):
    key = (frozenset(bd.items()), to_move)
    if key in memo:
        return memo[key]
    mine = placements(bd, 3, to_move)
    if not mine:
        if not placements(bd, 3, 1 - to_move):
            memo[key] = 0
            return 0
        memo[key] = solve3(bd, 1 - to_move, memo)
        return memo[key]
    best = None
    for (c, r) in mine:
        bd[(c, r)] = to_move
        v = (1 if to_move == BLACK else -1) if connects(bd, to_move, 3) \
            else solve3(bd, 1 - to_move, memo)
        del bd[(c, r)]
        best = v if best is None else (max(best, v) if to_move == BLACK else min(best, v))
        if best == (1 if to_move == BLACK else -1):
            break
    memo[key] = best
    return best


memo = {}
check(solve3({}, BLACK, memo) == 1, "3x3 is a first-player (Black) win without the pie rule")
pie = max(min(solve3({(c, r): BLACK}, WHITE, memo) if not connects({(c, r): BLACK}, BLACK, 3) else 1,
              solve3({(r, c): WHITE}, BLACK, memo))
          for (c, r) in placements({}, 3, BLACK))
check(pie == -1, "3x3 WITH the pie rule is a win for the swapper (seat 1) — the pie works")

# --------------------------------------------------------------------------
# pie rule: swap == transpose + colour reversal, and it is value-preserving
# --------------------------------------------------------------------------
s = G.initial_state(options={"size": 9})
check(sorted(G.legal_moves(s)) == sorted(f"{c},{r}" for c in range(9) for r in range(9)),
      "every point is legal on an empty board")
check("swap" not in G.legal_moves(s), "no swap on Black's first turn")
s1 = G.apply_move(s, "2,6")
check("swap" in G.legal_moves(s1), "swap offered on White's first turn")
s2 = G.apply_move(s1, "swap")
check(s2.board == {(6, 2): WHITE}, f"swap transposes AND recolours, got {s2.board}")
check(G.current_player(s2) == BLACK, "after the swap it is seat 0 (Black) to move")
check("swap" not in G.legal_moves(s2), "swap is available once only")
s3 = G.apply_move(s2, "0,0")
check("swap" not in G.legal_moves(s3), "swap is not offered later in the game")
# value preservation: transpose+colour-swap maps legal moves and wins over
for _ in range(60):
    bd = {}
    for _ in range(rng.randrange(3, 18)):
        bd[(rng.randrange(9), rng.randrange(9))] = rng.randrange(2)
    tb = {(r, c): 1 - v for (c, r), v in bd.items()}
    lb = {(r, c) for (c, r) in placements(bd, 9, BLACK)}
    lw = {p for p in placements(tb, 9, WHITE)}
    check(lb == lw, "transpose+colour-swap maps Black's legal set onto White's")
    check(connects(bd, BLACK, 9) == connects(tb, WHITE, 9),
          "transpose+colour-swap maps a Black connection onto a White one")

# --------------------------------------------------------------------------
# the skip rule (reached VIA apply_move, never hand-built)
# --------------------------------------------------------------------------
skip_games = skipped = 0
for seed in range(400):
    r2 = random.Random(seed)
    st = G.initial_state(options={"size": 5})
    while not G.is_terminal(st):
        before = G.current_player(st)
        mv = r2.choice(G.legal_moves(st))
        nxt = G.apply_move(st, mv)
        if not G.is_terminal(nxt) and G.current_player(nxt) == before and mv != "swap":
            skipped += 1
            check(nxt.skips == st.skips + 1, "a skip bumps the skip counter")
            check(not placements(nxt.board, 5, 1 - before),
                  "a player is skipped only when they have NO legal placement")
            check(G.describe_move(st, mv).endswith("(opponent skipped)"),
                  "describe_move reports the skip")
        st = nxt
    if st.skips:
        skip_games += 1
check(skipped >= 5, f"the skip rule is REACHABLE in 5x5 random play (saw {skipped})")

# A mutual stall is an honest DRAW.  Random play never reaches one (see the
# 3x3 enumeration above), so it is exercised here on a CONSTRUCTED input: a
# 4x4 checkerboard with one point missing.  Such a position cannot arise in
# play — it is riddled with hard corners, asserted below — but filling its last
# point is legal by the glyph rule (the areas involved all become full), and
# leaves a full board on which neither colour is connected.  Reached VIA
# apply_move, so the stall detection itself is under test, not a hand-set flag.
chk = {(c, r): (c + r) % 2 for c in range(4) for r in range(4)}
hole = (3, 3)
del chk[hole]
pre = MinefieldState(size=4, board=chk, to_move=chk[(2, 3)])
check(glyphs_on_board(chk, 4) != [],
      "the constructed checkerboard is full of hard corners — it is unreachable in play")
check(G.legal_moves(pre) == ["3,3"], f"its only legal move is the hole, got {G.legal_moves(pre)}")
post = G.apply_move(pre, "3,3")
check(len(post.board) == 16, "the constructed move fills the board")
check(post.winner is None and not connects(post.board, BLACK, 4)
      and not connects(post.board, WHITE, 4), "nobody is connected on the checkerboard")
check(post.stalled, "with no point left, BOTH players are stuck -> stalled")
check(G.is_terminal(post), "a mutual stall is terminal")
check(G.returns(post) == [0.0, 0.0], "a mutual stall scores 0-0 — an honest draw")
check("Draw" in G.render(post)["caption"], "the stalled caption says Draw")
check(G.deserialize(G.serialize(post)) == post, "a stalled state round-trips")

# --------------------------------------------------------------------------
# random games: termination bound, monotonicity, serialization, captions
# --------------------------------------------------------------------------
KEYS = {"size", "board", "to_move", "last", "winner", "stalled", "ply", "skips"}
results = {0: 0, 1: 0, None: 0}
for seed in range(120):
    size = (5, 7, 9, 11)[seed % 4]
    r2 = random.Random(1000 + seed)
    st = G.initial_state(options={"size": size})
    stones = 0
    while not G.is_terminal(st):
        mv = r2.choice(G.legal_moves(st))
        d = G.serialize(st)
        check(set(d) == KEYS, f"serialize key set is exactly {KEYS}, got {set(d)}")
        check(G.deserialize(d) == st, "deserialize(serialize(s)) restores the STATE")
        nxt = G.apply_move(st, mv)
        check(st.board == G.deserialize(G.serialize(st)).board, "apply_move did not mutate")
        if mv == "swap":
            check(len(nxt.board) == len(st.board) == 1, "the swap places no stone")
        else:
            check(len(nxt.board) == len(st.board) + 1, "every other ply places exactly one stone")
        check(nxt.ply == st.ply + 1, "ply increments once per move")
        st = nxt
        stones = len(st.board)
    check(st.ply <= max_plies(size),
          f"ply {st.ply} within the derived bound {max_plies(size)} (size*size + 1 swap)")
    check(G.deserialize(G.serialize(st)) == st, "terminal state round-trips")
    results[st.winner] += 1
    if st.winner is not None:
        check(connects(st.board, st.winner, size), "the declared winner really is connected")
        check(not connects(st.board, 1 - st.winner, size), "the loser is not connected")
        check(G.returns(st) == ([1.0, -1.0] if st.winner == BLACK else [-1.0, 1.0]),
              "returns matches the winner")
        cap = G.render(st)["caption"]
        check(cap == ("Black wins" if st.winner == BLACK else "White wins"),
              f"the render caption names the right winner, got {cap!r}")
    check(stones <= size * size, "never more stones than points")
check(results[None] == 0, f"no draws in 120 random games, got {results[None]}")
check(results[0] > 0 and results[1] > 0, "both colours win some random games")

# describe_move marks the winning move
st = G.initial_state(options={"size": 5})
r2 = random.Random(7)
prev = None
while not G.is_terminal(st):
    mv = r2.choice(G.legal_moves(st))
    prev, st = (st, mv), G.apply_move(st, mv)
check(G.describe_move(prev[0], prev[1]).endswith("#"), "describe_move marks the winning move")

# --------------------------------------------------------------------------
# render bounds at EVERY offered board size, from a far-corner position
# --------------------------------------------------------------------------
import json                                                     # noqa: E402
man = json.loads((Path(__file__).resolve().parent / "manifest.json").read_text())
sizes = man["options"]["size"]["choices"]
check(man["options"]["size"]["default"] in sizes, "the default size is one of the choices")
for size in sizes:
    st = G.initial_state(options={"size": size})
    # walk into all four corners via apply_move (corner placements are legal
    # early: a glyph needs three stones)
    for cell in ((0, 0), (size - 1, size - 1), (size - 1, 0), (0, size - 1)):
        mv = f"{cell[0]},{cell[1]}"
        check(mv in G.legal_moves(st), f"corner {mv} is legal on the {size}x{size} board")
        st = G.apply_move(st, mv)
    spec = G.render(st)
    b = spec["board"]
    check(b["width"] == size and b["height"] == size,
          f"render declares {size}x{size}, got {b['width']}x{b['height']}")
    check(b["type"] == "square", "square board")
    check(set(b["edges"]) == {"top", "bottom", "left", "right"}, "all four edges coloured")
    check(b["edges"]["top"] == b["edges"]["bottom"] == BLACK
          and b["edges"]["left"] == b["edges"]["right"] == WHITE,
          "top/bottom are Black's edges, left/right are White's")
    cells = {p["cell"] for p in spec["pieces"]}
    check(len(spec["pieces"]) == 4, "all four corner stones are rendered")
    for cid in cells:
        c, r = (int(x) for x in cid.split(","))
        check(0 <= c < b["width"] and 0 <= r < b["height"],
              f"rendered piece {cid} lies inside the declared {size}x{size} board")

# --------------------------------------------------------------------------
# heuristic: shape, direction, and zero-sum
# --------------------------------------------------------------------------
st = G.initial_state(options={"size": 9})
h = G.heuristic(st)
check(isinstance(h, list) and len(h) == 2, "heuristic returns a LIST of 2 payoffs")
check(all(isinstance(x, float) for x in h), "heuristic payoffs are floats")
check(abs(h[0] + h[1]) < 1e-9, "heuristic is zero-sum")
check(abs(h[0]) < 1e-9, "the empty board is even")
ahead = MinefieldState(size=9, board={(4, r): BLACK for r in range(7)})
behind = MinefieldState(size=9, board={(4, r): WHITE for r in range(7)})
check(G.heuristic(ahead)[0] > 0.5, f"a near-complete Black chain scores high, got {G.heuristic(ahead)}")
check(G.heuristic(behind)[0] < 0.0, "a near-complete White chain scores low for Black")
check(G.heuristic(ahead)[0] > G.heuristic(st)[0] > G.heuristic(behind)[0],
      "heuristic direction: better Black position => higher Black payoff")

print(("FAILED: %d" % len(FAILS)) if FAILS else "minefield selftest: all checks passed")
sys.exit(1 if FAILS else 0)
