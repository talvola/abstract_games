"""Mattock selftest — pure stdlib.

Anchors (Abstract Games magazine #21, pp. 14-20 + solution p. 25; figures
pixel-read from the PDF at 300 dpi):

1. Board geometry + fixed setups (the board-sizes/fixed-setup diagram, p.14):
   hexhex-7 = 127 cells / 6 miners each, inner hexhex-5 = 61 cells / 3 each;
   setups centrally symmetric, pairwise non-adjacent, both sides can mine.
2. The p.14-15 worked example, figure 1: Red's COMPLETE legal-mine set must
   equal the 11 cells starred in the figure (collapse + connection combined).
3. The p.15 worked example, figure 2: "Red places the highlighted tile,
   moves 1 miner, and removes 2 blue miners. The final blue miner remains,
   as it connects to only 1 red miner." Exact end-of-turn board asserted.
4. The p.20 puzzle with the p.25 solution: Red mines the whirligig tile and
   moves her southern miner; exactly Blue's south-west miner is removed;
   the resulting board equals the printed solution diagram; the whirligig
   blocks the invasion squares B and C for Blue; Blue's forced replacement
   (hand miner auto-placed on his next mine); the stated alternatives
   A, B, C are indeed legal Red mines in the puzzle position.
5. Collapse/connection/removal unit rules + random-playout invariants
   (every tile always touches <= 3 tiles; games always end with a winner).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = Path(__file__).resolve().parent
man, G = load_from_dir(PKG)

checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    if not cond:
        raise SystemExit(f"FAIL: {msg}")


def cells_of(size):
    n = size - 1
    return [(q, r) for q in range(-n, n + 1) for r in range(-n, n + 1)
            if max(abs(q), abs(r), abs(q + r)) <= n]


def neighbors(q, r):
    return [(q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1),
            (q + 1, r - 1), (q - 1, r + 1)]


def build(size, tiles_only, red, blue, phase="mine", to_move=0, hands=(0, 0)):
    """Hand-build a state: miners stand on their own tiles."""
    s = G.initial_state({"board": f"hex{size}"})
    s.tiles = set(tiles_only) | set(red) | set(blue)
    s.miners = {c: 0 for c in red}
    s.miners.update({c: 1 for c in blue})
    s.hands = list(hands)
    s.phase = phase
    s.to_move = to_move
    s.mined = None
    s.last = ()
    return s


def mine_set(s, seat):
    return {tuple(int(x) for x in m.split(",")) for m in
            (G.legal_moves(s) if s.to_move == seat and s.phase == "mine"
             else [])}


# ---------------------------------------------------------------- 1. geometry
for size, ncells, nminers in ((7, 127, 6), (5, 61, 3)):
    s = G.initial_state({"board": f"hex{size}"})
    ok(len(cells_of(size)) == ncells, f"hex{size} cell count")
    ok(len(s.miners) == 2 * nminers, f"hex{size} miner count")
    ok(all(c in s.tiles for c in s.miners), f"hex{size} miners on tiles")
    red = sorted(c for c, o in s.miners.items() if o == 0)
    blue = sorted(c for c, o in s.miners.items() if o == 1)
    ok(sorted((-q, -r) for q, r in red) == blue,
       f"hex{size} setup centrally symmetric")
    for c in s.tiles:
        ok(not any(nb in s.tiles for nb in neighbors(*c)),
           f"hex{size} setup tiles pairwise non-adjacent")
    # both players can mine at the start
    ok(len(G.legal_moves(s)) > 0, f"hex{size} Red has opening mines")
    s2 = G._copy(s)
    s2.to_move = 1
    ok(len(G.legal_moves(s2)) == len(G.legal_moves(s)),
       f"hex{size} symmetric opening mobility")

# hex-5 fixed setup matches the magazine diagram's inner marked cells
s5 = G.initial_state({"board": "hex5"})
ok(sorted(c for c, o in s5.miners.items() if o == 0)
   == sorted([(-2, -1), (3, -2), (-1, 3)]), "hex5 Red fixed setup cells")

# hex-7 fixed setup per the p.14 diagram
s7 = G.initial_state({"board": "hex7"})
ok(sorted(c for c, o in s7.miners.items() if o == 0)
   == sorted([(2, -6), (-2, -1), (3, -2), (-6, 4), (-1, 3), (4, 2)]),
   "hex7 Red fixed setup cells")

# ------------------------------------------------- 2. figure 1: legal mines
FIG1_TILES = [(-2, -1), (-2, 3), (-1, -2), (-1, -1), (0, -2), (0, 0), (0, 1),
              (1, -3), (1, -1), (1, 2), (2, 1), (3, -3)]
FIG1_RED = [(-2, 2), (-1, 3), (2, -3)]
FIG1_BLUE = [(-3, 2), (0, 2), (2, -2)]
STARS = {(-3, -1), (-3, 0), (-3, 3), (-3, 4), (-2, 1), (-2, 4), (-1, 1),
         (-1, 4), (1, -4), (4, -4), (4, -3)}

f1 = build(5, FIG1_TILES, FIG1_RED, FIG1_BLUE)
got = {tuple(int(x) for x in m.split(",")) for m in G.legal_moves(f1)}
ok(got == STARS, f"fig1 legal-mine set == the 11 starred cells (got {sorted(got)})")

# ------------------------------------- 3. figure 2: mine + move + double removal
f2 = G.apply_move(f1, "-1,1")               # the highlighted tile
ok(f2.phase == "move" and f2.to_move == 0, "fig2 mine keeps the turn")
lbl = G.describe_move(f2, "-1,3>0,1")
ok("removes 2" in lbl, f"fig2 describe_move shows the double removal ({lbl!r})")
f2 = G.apply_move(f2, "-1,3>0,1")           # the moved miner
ok(sorted(c for c, o in f2.miners.items() if o == 0)
   == sorted([(-2, 2), (0, 1), (2, -3)]), "fig2 red miners after the turn")
ok(sorted(c for c, o in f2.miners.items() if o == 1) == [(-3, 2)],
   "fig2 the final blue miner remains (connects to only 1 red miner)")
ok(f2.hands == [0, 2], "fig2 two removed blue miners in hand")
ok(f2.tiles == set(FIG1_TILES) | set(FIG1_RED) | set(FIG1_BLUE) | {(-1, 1)},
   "fig2 tiles = fig1 tiles + the mined tile (removal keeps tiles)")
ok(f2.to_move == 1 and f2.phase == "mine" and not f2.over,
   "fig2 turn passes to Blue")

# ------------------------------------------------- 4. the p.20 puzzle (hex-5)
PUZ_TILES = [(-1, -2), (0, -2), (1, -3), (2, -1), (2, 0), (2, 1), (1, 2),
             (-1, 2), (-1, 3)]
PUZ_RED = [(-3, 1), (0, 2), (3, -2)]
PUZ_BLUE = [(-1, -1), (2, -3), (-2, 3)]
A, B, C = (3, -3), (1, 0), (3, -1)          # labels in the p.25 solution figure

puz = build(5, PUZ_TILES, PUZ_RED, PUZ_BLUE)
legal = mine_set(puz, 0)
ok((1, -1) in legal, "solution mine (whirligig tile) is legal")
ok({A, B, C} <= legal, "solution alternatives A, B, C are legal Red mines")

# mining alone does not yet remove the SW blue miner (the move is load-bearing)
alt = G.apply_move(puz, "1,-1")
alt = G.apply_move(alt, "pass")
ok(sorted(alt.miners.items()) == sorted(
    {**{c: 0 for c in PUZ_RED}, **{c: 1 for c in PUZ_BLUE}}.items()),
   "mine alone removes nothing (removal needs the corridor opened by the move)")

sol = G.apply_move(puz, "1,-1")             # 1. mine: completes the whirligig
sol = G.apply_move(sol, "0,2>-1,2")         # 2. move: opens the corridor
# 3. remove: exactly Blue's south-west miner
ok(sorted(c for c, o in sol.miners.items() if o == 1)
   == sorted([(-1, -1), (2, -3)]), "solution removes exactly Blue (-2,3)")
ok(sol.hands == [0, 1], "removed Blue miner goes to Blue's hand")
# the resulting board equals the printed solution diagram
ok(sorted(c for c, o in sol.miners.items() if o == 0)
   == sorted([(-3, 1), (-1, 2), (3, -2)]), "solution red miners")
ok(sol.tiles == set(PUZ_TILES) | set(PUZ_RED) | set(PUZ_BLUE) | {(1, -1)},
   "solution tiles")
ok(sol.to_move == 1 and sol.phase == "mine" and not sol.over,
   "solution hands the turn to Blue")
# the whirligig centre (2,-1) now touches 3 tiles -> B and C are dead for Blue
blue_mines = mine_set(sol, 1)
ok(B not in blue_mines and C not in blue_mines,
   "whirligig blocks the invasion squares B and C")
ok(sum(1 for nb in neighbors(2, -1) if nb in sol.tiles) == 3,
   "whirligig centre touches exactly 3 tiles")
# Blue must replace his removed miner on his next mine
any_mine = sorted(blue_mines)[0]
nb = G.apply_move(sol, f"{any_mine[0]},{any_mine[1]}")
ok(nb.miners.get(any_mine) == 1 and nb.hands == [0, 0],
   "Blue's next mine auto-places the hand miner")

# ------------------------------------------------------------- 5. unit rules
# collapse clause 1: a cell touching 4 tiles is unmineable
u = build(5, [(1, 1), (-1, 1), (0, 0), (0, 2)], [(1, 0)], [])
u.tiles.add((1, 0))
ok((0, 1) not in mine_set(u, 0), "cell touching 4 tiles is blocked")

# collapse clause 2: touching a tile that already touches 3 is unmineable
u = build(5, [(0, 0), (1, 0), (0, 1)], [(1, -1)], [])
ok(sum(1 for nbc in neighbors(0, 0) if nbc in u.tiles) == 3,
   "unit: (0,0) touches 3")
ms = mine_set(u, 0)
ok((-1, 0) not in ms and (-1, 1) not in ms,
   "cells touching a 3-degree tile are blocked")
ok((0, 2) in ms, "cell touching only low-degree tiles is mineable")

# connection blocking: enemy miners block, own do not
u = build(5, [(1, 0), (2, 0)], [(0, 0)], [(1, 0)])
ok((3, 0) not in mine_set(u, 0), "enemy miner blocks Red's connection")
u2 = build(5, [(1, 0), (2, 0)], [(0, 0)], [(1, 0)], to_move=1)
ok((3, 0) in mine_set(u2, 1), "Blue connects through his own miner's tile")

# removal: adjacency immunity vs. isolated miner between two enemies
line = [(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0)]
u = build(5, line, [(-2, 0), (3, 0)], [(0, 0), (1, 0)], phase="move")
u = G.apply_move(u, "pass")
ok(sorted(c for c, o in u.miners.items() if o == 1) == [(0, 0), (1, 0)],
   "two adjacent miners are immune from removal")
u = build(5, line, [(-2, 0), (3, 0)], [(0, 0)], phase="move")
u = G.apply_move(u, "pass")
ok(all(o == 0 for o in u.miners.values()) and u.hands == [0, 1],
   "isolated miner connected to 2 enemies is removed")
ok(u.over and u.winner == 0,
   "Blue's last miner gone -> Blue cannot mine -> Red wins")

# ------------------------------------------------- freestyle setup mechanics
fs = G.initial_state({"board": "hex5", "setup": "freestyle"})
ok(fs.phase == "setup" and fs.to_move == 1, "freestyle: Blue places first")
ok(len(G.legal_moves(fs)) == 61, "freestyle: first placement anywhere")
rng = random.Random(7)
while fs.phase == "setup":
    mv = rng.choice(G.legal_moves(fs))
    fs = G.apply_move(fs, mv)
ok(fs.to_move == 0 and fs.phase == "mine",
   "freestyle: Red places last and takes the first turn")
ok(len(fs.miners) == 6 and len(fs.tiles) == 6, "freestyle: 3 miners each")
for c in fs.tiles:
    ok(not any(nbc in fs.tiles for nbc in neighbors(*c)),
       "freestyle placements non-adjacent")
ok(len(G.legal_moves(fs)) > 0, "freestyle: first mover can mine")

# ------------------------------------- random playouts: invariants + endings
def tile_degrees_ok(s):
    return all(sum(1 for nbc in neighbors(*t) if nbc in s.tiles) <= 3
               for t in s.tiles)

for size, ngames in ((5, 12), (7, 4)):
    for gi in range(ngames):
        rng = random.Random(1000 * size + gi)
        opts = {"board": f"hex{size}"}
        if gi % 2:
            opts["setup"] = "freestyle"
        s = G.initial_state(opts)
        cap = 4 * len(cells_of(size)) + 30
        n = 0
        while not G.is_terminal(s):
            mvs = G.legal_moves(s)
            ok(len(mvs) > 0, "non-terminal state has moves")
            s = G.apply_move(s, rng.choice(mvs))
            n += 1
            ok(n <= cap, f"terminates within ply cap (hex{size})")
            ok(all(c in s.tiles for c in s.miners), "miners always on tiles")
        ok(tile_degrees_ok(s), "collapse invariant: every tile touches <= 3")
        ok(s.winner in (0, 1), "game always ends with a winner (no draws)")
        # round-trip
        ok(G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s),
           "serialize round-trip")

# a mid-game round-trip incl. hands / phase
mid = G.serialize(sol)
ok(G.serialize(G.deserialize(mid)) == mid, "mid-game round-trip")

print(f"mattock selftest: all {checks} checks passed")
