"""Volo selftest — anchors the rules as implemented against the official
spielstein.com rules and the nestorgames rulebook:

 (a) board = the hexhex "sky": 120 points (edge 7) / 84 points (edge 6) with the
     6 corners and the centre removed; setup = 3 birds each in alternating
     edge-midpoint nests; Orange (seat 0) moves first;
 (b) ADD legality: illegal if adjacent to a friendly bird, illegal inside an
     opponent-controlled region (no open path to a friendly bird), legal into a
     neutral region;
 (c) FLY: a straight-line move must END adjacent to a friendly bird (enlarge);
     an enemy bird BLOCKS the flight; a single-bird move that would SPLIT its
     flock is illegal; a whole straight-line flock may fly as a rigid unit;
 (d) REGIONS: a move fragmenting the opponent offers a survival CHOICE (keep one
     region, clear the rest to the owner's supply); WIN PRIORITY — a move that
     unifies the mover AND fragments the opponent wins with no clearing; and a
     clearing choice can hand the opponent a single-flock win;
 (e) WIN = all your birds in one contiguous flock (reached via apply_move);
 (f) forced pass when no action is possible; double-pass = draw;
 (g) random playouts terminate (natural or ply cap); serialize round-trips.

Pure stdlib. Run: PYTHONPATH=. python3 games/volo/selftest.py
"""

import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = pathlib.Path(__file__).resolve().parent
_, G = load_from_dir(PKG)
MOD = sys.modules[type(G).__module__]
_points, _flocks, _regions, _is_line = MOD._points, MOD._flocks, MOD._regions, MOD._is_line


def st(orange, blue, to_move=0, supply=(55, 55), passes=0):
    board = {f"{q},{r}": 0 for q, r in orange}
    board.update({f"{q},{r}": 1 for q, r in blue})
    return G.deserialize({
        "R": 6, "board": board, "to_move": to_move, "supply": list(supply),
        "ply": 6, "passes": passes, "winner": None, "drawn": False,
        "draw_kind": "", "last": None,
    })


# ---- (a) board + setup -------------------------------------------------------
assert len(_points(6)) == 120 and len(_points(5)) == 84
for excl in [(0, 0), (6, 0), (6, -6), (0, -6), (-6, 0), (-6, 6), (0, 6)]:
    assert excl not in _points(6), excl                    # centre + 6 corners gone
s0 = G.initial_state()
assert s0.R == 6 and G.current_player(s0) == 0
orange = {p for p, c in s0.board.items() if c == 0}
blue = {p for p, c in s0.board.items() if c == 1}
assert orange == {(6, -3), (-3, -3), (-3, 6)}, orange       # seat-0 nests
assert blue == {(3, -6), (-6, 3), (3, 3)}, blue             # seat-1 nests
assert all(p in _points(6) for p in orange | blue)
# supply = points/2 - 3 already placed
assert s0.supply == (57, 57), s0.supply
ssm = G.initial_state({"size": 84})
assert ssm.R == 5 and len(ssm.board) == 6 and ssm.supply == (39, 39)
assert {p for p, c in ssm.board.items() if c == 0} == {(4, -2), (-2, -2), (-2, 4)}
spec = G.render(s0)
assert spec["board"] == {"type": "hex", "shape": "hexagon", "size": 7}
assert len(spec["pieces"]) == 6 and {p["owner"] for p in spec["pieces"]} == {0, 1}
assert "Orange" in spec["caption"]
assert "pass" not in G.legal_moves(s0)                      # actions available
print("(a) board + setup OK")

# ---- (b) ADD legality --------------------------------------------------------
# Blue walls point X=(6,-1) (its 3 on-board neighbours); Orange has a bird at (0,1).
s = st(orange=[(0, 1)], blue=[(5, -1), (6, -2), (5, 0)], supply=(55, 54))
lm = set(G.legal_moves(s))
assert "6,-1" not in lm                 # inside an opponent-controlled region
assert "0,0" not in lm                  # the excluded centre point
assert "1,1" not in lm                  # adjacent to friendly Orange (0,1)
assert "2,1" in lm                      # neutral region, not adjacent to a friend
print("(b) ADD legality OK")

# ---- (c) FLY ----------------------------------------------------------------
c1 = st(orange=[(2, 0), (5, 0)], blue=[])
l1 = set(G.legal_moves(c1))
assert "2,0>4,0" in l1                  # lands adjacent to friendly (5,0): enlarges
assert "2,0>3,0" not in l1              # lands with no friendly neighbour: illegal
assert "5,0>3,0" in l1                  # symmetric straight-line join
c2 = st(orange=[(2, 0), (5, 0)], blue=[(3, 0)], supply=(55, 54))
assert not any(m.startswith("2,0>") for m in G.legal_moves(c2))   # enemy at (3,0) blocks
c3 = st(orange=[(2, 2), (3, 2), (4, 2), (2, 5)], blue=[], supply=(54, 55))
assert not any(m.startswith("3,2>") for m in G.legal_moves(c3))   # moving centre splits
assert _is_line([(2, 2), (3, 2), (4, 2)]) and not _is_line([(2, 2), (4, 2)])
# a whole straight-line flock flies as a rigid unit:
c4 = st(orange=[(2, 0), (3, 0), (5, 0)], blue=[], supply=(54, 55))
assert "*2,0>3,0" in G.legal_moves(c4)  # {(2,0),(3,0)} -> {(3,0),(4,0)} joins (5,0)
print("(c) FLY OK")

# ---- (d) REGIONS: survival choice + win priority -----------------------------
# Orange flies (1,0)->(5,0), completing a wall that isolates Blue (6,-1). Orange
# has a stray bird (0,3) so Orange is NOT unified -> region clearing triggers.
frag = st(orange=[(5, -1), (6, -2), (1, 0), (0, 3)],
          blue=[(6, -1), (-3, 0), (-1, 0)], supply=(53, 53))
fm = set(G.legal_moves(frag))
assert "1,0>5,0=6,-1" in fm and "1,0>5,0=-3,0" in fm     # two survival choices offered
assert "1,0>5,0" not in fm                                # bare (unresolved) move NOT legal
# keep the trapped bird -> Blue reduced to a single flock -> Blue WINS immediately
keepB = G.apply_move(frag, "1,0>5,0=6,-1")
assert {p for p, c in keepB.board.items() if c == 1} == {(6, -1)}
assert keepB.supply[1] == 55 and G.is_terminal(keepB) and G.returns(keepB) == [-1.0, 1.0]
# keep the main region -> two Blue flocks remain -> no win; one bird returned
keepA = G.apply_move(frag, "1,0>5,0=-3,0")
assert {p for p, c in keepA.board.items() if c == 1} == {(-3, 0), (-1, 0)}
assert keepA.supply[1] == 54 and keepA.winner is None and len(_flocks(keepA.board, 1)) == 2
# WIN PRIORITY: same fly WITHOUT the stray (0,3) unifies Orange AND fragments Blue
# -> Orange wins, regions IGNORED (Blue birds not cleared).
win = st(orange=[(5, -1), (6, -2), (1, 0)], blue=[(6, -1), (-3, 0), (-1, 0)], supply=(54, 54))
assert "1,0>5,0" in G.legal_moves(win) and "1,0>5,0=6,-1" not in G.legal_moves(win)
wn = G.apply_move(win, "1,0>5,0")
assert wn.winner == 0 and {p for p, c in wn.board.items() if c == 1} == {(6, -1), (-3, 0), (-1, 0)}
print("(d) regions / survival choice / win priority OK")

# ---- (e) WIN = single flock via apply_move -----------------------------------
assert G.is_terminal(wn) and G.returns(wn) == [1.0, -1.0]
assert len(_flocks(wn.board, 0)) == 1
print("(e) win = single flock OK")

# ---- (f) forced pass + double-pass draw --------------------------------------
# Lone Orange bird, empty supply: no add, no enlarging fly -> forced pass.
fp = st(orange=[(0, -2)], blue=[(3, 3), (3, -6)], supply=(0, 54))
assert G.legal_moves(fp) == ["pass"]
p1 = G.apply_move(fp, "pass")
p2 = G.apply_move(p1, "pass")
assert p2.drawn and p2.draw_kind == "double-pass"
assert G.is_terminal(p2) and G.returns(p2) == [0.0, 0.0]
print("(f) forced pass + double-pass draw OK")

# ---- (g) termination + serialize round-trip ----------------------------------
for seed in range(6):
    rng = random.Random(seed)
    s = G.initial_state({"size": 84 if seed % 2 else 120})
    n = 0
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        n += 1
        assert n <= G._cap(s.R) + 2
    r = G.returns(s)
    assert len(r) == 2 and all(isinstance(x, float) for x in r)
    if s.winner is not None:
        assert len(_flocks(s.board, s.winner)) == 1     # winner really unified
    snap = G.serialize(s)
    assert G.serialize(G.deserialize(snap)) == snap
print("(g) termination / serialize OK")

print("volo selftest: all checks passed")
