"""Selftest for Murus Gallicus (pure stdlib).

Anchors, per the official nestorgames rulebook (rules (c) 2009 Phillip Leduc)
and Wikipedia:
  * setup: eight height-2 towers per side on the home rows, Romans first;
  * opening mobility: exactly 20 distribution moves (8 straight + 2x6 diagonal);
  * distribution legality: empty / friendly-wall targets only, friendly towers
    and all enemy stones block, both cells must be on the board;
  * walls never move; sacrifice hits adjacent enemy WALLS only (not towers),
    costs one own stone (tower -> wall);
  * win by reaching the opponent's home row, or by stalemating them -- both
    reached via apply_move;
  * termination: random playouts always end (repetition / ply-cap honest draw).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = Path(__file__).resolve().parent
_, G = load_from_dir(PKG)

checks = 0


def ok(cond, msg):
    global checks
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    checks += 1


def st(board, to_move=0):
    return G.deserialize({"board": board, "to_move": to_move})


# ---- setup -------------------------------------------------------------------
s0 = G.initial_state()
ok(G.current_player(s0) == 0, "Romans (player 0) move first")
ok(len(s0.board) == 16, "16 occupied cells at start")
for c in range(8):
    ok(s0.board[(c, 0)] == (0, 2), f"Roman tower at ({c},0)")
    ok(s0.board[(c, 6)] == (1, 2), f"Gaul tower at ({c},6)")
stones = sum(h for (_o, h) in s0.board.values())
ok(stones == 32, "32 stones on the board")
ok(not G.is_terminal(s0), "start is not terminal")

# ---- opening mobility ----------------------------------------------------------
m0 = G.legal_moves(s0)
ok(len(m0) == 20, f"20 opening moves (got {len(m0)})")
ok(len(set(m0)) == 20, "opening moves are unique")
ok("0,0>0,2" in m0 and "5,0>7,2" in m0 and "2,0>0,2" in m0, "sample opening moves")
ok("0,0>2,2" in m0, "diagonal distribution from the corner")
ok("0,0>1,0" not in m0 and "0,0>2,0" not in m0, "sideways blocked by friendly towers")

# ---- distribution legality -----------------------------------------------------
# near empty + far friendly wall -> legal, wall builds into a tower
s = st({"3,3": [0, 2], "3,5": [0, 1]})
ok("3,3>3,5" in G.legal_moves(s), "far cell may be a friendly wall")
ns = G.apply_move(s, "3,3>3,5")
ok(ns.board.get((3, 4)) == (0, 1), "near cell gets a wall")
ok(ns.board.get((3, 5)) == (0, 2), "friendly wall built into a tower")
ok((3, 3) not in ns.board, "source cell emptied")

# near friendly wall -> legal, becomes a tower
s = st({"3,3": [0, 2], "3,4": [0, 1]})
ns = G.apply_move(s, "3,3>3,5")
ok(ns.board.get((3, 4)) == (0, 2) and ns.board.get((3, 5)) == (0, 1),
   "near friendly wall becomes a tower, far cell gets a wall")

# both cells friendly walls -> both become towers
s = st({"3,3": [0, 2], "3,4": [0, 1], "3,5": [0, 1]})
ns = G.apply_move(s, "3,3>3,5")
ok(ns.board.get((3, 4)) == (0, 2) and ns.board.get((3, 5)) == (0, 2),
   "two friendly walls both built into towers")

# blockers: friendly tower / enemy wall / enemy tower, near or far
for blocker, why in [([0, 2], "friendly tower"), ([1, 2], "enemy tower")]:
    for cell in ("3,4", "3,5"):
        s = st({"3,3": [0, 2], cell: blocker})
        ok("3,3>3,5" not in G.legal_moves(s), f"{why} at {cell} blocks distribution")
s = st({"3,3": [0, 2], "3,5": [1, 1]})
ok("3,3>3,5" not in G.legal_moves(s), "enemy wall at far cell blocks distribution")
s = st({"3,3": [0, 2], "3,4": [1, 1]})
lm = G.legal_moves(s)
ok("3,3>3,5" not in lm, "enemy wall at near cell blocks distribution")
ok("3,3>3,4" in lm, "...but is a sacrifice target")

# off-board: forward from row 5 has its far cell off the board -> illegal
s = st({"3,5": [0, 2]})
lm = G.legal_moves(s)
ok(sorted(lm) == sorted(["3,5>1,3", "3,5>3,3", "3,5>5,3", "3,5>1,5", "3,5>5,5"]),
   f"row-5 tower: forward is off-board, only backward/sideways remain (got {sorted(lm)})")

# ---- walls never move ------------------------------------------------------------
s = st({"3,3": [0, 1], "5,5": [0, 1], "0,6": [1, 2]})
ok(G.legal_moves(s) == [], "a player with only walls has no moves")

# ---- sacrifice --------------------------------------------------------------------
# diagonal-adjacent enemy wall: sacrifice legal; enemy tower: not a target
s = st({"3,3": [0, 2], "4,4": [1, 1], "2,2": [1, 2]})
lm = G.legal_moves(s)
ok("3,3>4,4" in lm, "sacrifice vs diagonally adjacent enemy wall")
ok("3,3>2,2" not in lm, "no sacrifice vs an enemy tower")
ns = G.apply_move(s, "3,3>4,4")
ok(ns.board.get((3, 3)) == (0, 1), "sacrificing tower becomes a wall")
ok((4, 4) not in ns.board, "enemy wall demolished")
ok(sum(h for (_o, h) in ns.board.values()) == 3, "two stones left the board")
ok(ns.winner is None and ns.to_move == 1, "game continues, Gauls to move")

# a wall cannot sacrifice
s = st({"3,3": [0, 1], "3,4": [1, 1], "0,0": [0, 2]})
ok("3,3>3,4" not in G.legal_moves(s), "walls cannot sacrifice")

# ---- home-row win (via apply_move) -----------------------------------------------
s = st({"3,4": [0, 2], "0,6": [1, 2]})
ns = G.apply_move(s, "3,4>3,6")
ok(ns.winner == 0 and G.is_terminal(ns), "Roman stone on row 6 wins")
ok(G.returns(ns) == [1.0, -1.0], "returns for a Roman win")
# ...and for the Gauls toward row 0
s = st({"4,2": [1, 2], "0,0": [0, 2]}, to_move=1)
ns = G.apply_move(s, "4,2>4,0")
ok(ns.winner == 1 and G.returns(ns) == [-1.0, 1.0], "Gaul stone on row 0 wins")

# ---- stalemate loss (via apply_move) ----------------------------------------------
s = st({"0,0": [0, 2], "7,3": [1, 1]})           # Gauls have only an immobile wall
ns = G.apply_move(s, "0,0>0,2")
ok(ns.winner == 0 and G.is_terminal(ns), "stalemated Gauls lose")
ok(G.returns(ns) == [1.0, -1.0], "stalemate returns")

# ---- serialize round-trip -----------------------------------------------------------
d1 = G.serialize(s0)
d2 = G.serialize(G.deserialize(d1))
ok(d1 == d2, "serialize round-trips")

# ---- termination / playout stats ----------------------------------------------------
rng = random.Random(20090707)
results = {0: 0, 1: 0, None: 0}
lengths = []
for _ in range(500):
    s = G.initial_state()
    while not G.is_terminal(s):
        lm = G.legal_moves(s)
        ok(len(lm) > 0, "non-terminal state has moves")
        ok(len(set(lm)) == len(lm), "move encodings are unique")
        s = G.apply_move(s, rng.choice(lm))
    results[s.winner] += 1
    lengths.append(s.ply)
    r = G.returns(s)
    ok(len(r) == 2 and (r == [0.0, 0.0] or sorted(r) == [-1.0, 1.0]),
       "well-formed returns")
print(f"playouts: 500  Romans {results[0]}  Gauls {results[1]}  draws {results[None]}  "
      f"plies min/avg/max {min(lengths)}/{sum(lengths)/len(lengths):.1f}/{max(lengths)}")

# render probe: stacks present
spec = G.render(s0)
ok(spec["board"] == {"type": "square", "width": 8, "height": 7}, "render board shape")
ok(all(p.get("stack") == [p["owner"], p["owner"]] for p in spec["pieces"]),
   "all opening pieces render as height-2 stacks")
sw = G.render(G.apply_move(s0, "3,0>3,2"))
walls = [p for p in sw["pieces"] if "stack" not in p]
ok(len(walls) == 2, "after one distribution two walls render as plain discs")

print(f"murus_gallicus selftest: all {checks} checks passed")
