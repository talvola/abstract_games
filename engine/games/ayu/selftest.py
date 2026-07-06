"""Ayu selftest — anchors the rules as implemented against the official
mindsports.nl rules text and the Dagaz reference implementation:

 (a) initial setup: exact interleaved pattern, 30 stones each on 11x11, no
     same-colour orthogonal adjacency, Black (seat 0) moves first;
 (b) singleton steps: adjacent empty points only, filtered by the distance
     rule (new closest distance must be strictly smaller);
 (c) group extrusion: a move that would leave its former group split is
     illegal; the re-placed stone must touch the remaining group;
 (d) distance rule per the Dagaz reading ("new closest < old closest") with
     the join exception (a joining move is always legal, even when the merged
     unit's nearest other unit is farther than the old closest distance);
     units with no reachable friendly unit are immobile;
 (e) a player who cannot move WINS (reached via apply_move);
 (f) repeated position with the same player to move is a draw;
 (g) random playouts terminate; pie-rule swap works.

Pure stdlib. Run: PYTHONPATH=. python3 games/ayu/selftest.py
"""

import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = pathlib.Path(__file__).resolve().parent
_, G = load_from_dir(PKG)


def state(n, black, white, to_move=0, pie=False, history=None):
    return G.deserialize({
        "n": n,
        "board": {**{f"{c},{r}": 0 for c, r in black},
                  **{f"{c},{r}": 1 for c, r in white}},
        "to_move": to_move, "swapped": False, "pie": pie, "ply": 4,
        "drawn": False, "draw_kind": "", "history": history or [], "last": None,
    })


# ---- (a) initial setup -------------------------------------------------------
s0 = G.initial_state()
assert s0.n == 11
blacks = {p for p, c in s0.board.items() if c == 0}
whites = {p for p, c in s0.board.items() if c == 1}
assert len(blacks) == 30 and len(whites) == 30, (len(blacks), len(whites))
# official pattern (row 0 at the bottom): Black on even rows / odd columns,
# White on odd rows / even columns; corners empty
assert blacks == {(c, r) for r in range(0, 11, 2) for c in range(1, 11, 2)}
assert whites == {(c, r) for r in range(1, 11, 2) for c in range(0, 11, 2)}
for (c, r), col in s0.board.items():
    for dc, dr in ((1, 0), (0, 1)):
        assert s0.board.get((c + dc, r + dr)) != col, "same-colour adjacency in setup"
assert G.current_player(s0) == 0
assert "Black to move" in G.render(s0)["caption"], "Black must move first"
assert not G.is_terminal(s0) and len(G.legal_moves(s0)) > 0
assert "swap" not in G.legal_moves(G.initial_state(options={"pie": True}))
# size option
s9 = G.initial_state(options={"size": 9})
assert s9.n == 9 and sum(1 for c in s9.board.values() if c == 0) == 20
print("(a) initial setup OK")

# ---- (b) singleton steps + distance filtering --------------------------------
# Black singletons at (0,0) and (0,2): closest distance 1 (via the empty (0,1)).
# Only moves that reach distance 0 (i.e. join) are legal; sideways steps that
# leave the distance at >= 1 are not.
s = state(7, black=[(0, 0), (0, 2)], white=[(6, 6), (6, 4)])
assert set(G.legal_moves(s)) == {"0,0>0,1", "0,2>0,1"}, G.legal_moves(s)
print("(b) singleton distance filtering OK")

# ---- (c) group extrusion: no-split + must touch remaining group ---------------
# Black group (2,2)-(3,2)-(4,2) + singleton (2,5) at distance 2.
s = state(9, black=[(2, 2), (3, 2), (4, 2), (2, 5)], white=[(7, 7), (7, 5)])
moves = set(G.legal_moves(s))
assert not any(m.startswith("3,2>") for m in moves), "moving the centre stone splits the group"
# every group-stone destination must be adjacent to the remaining stones
assert "4,2>4,3" not in moves and "4,2>5,2" not in moves  # touch only the moved stone's old cell
# exact legal set: extrude the group towards the singleton, or step the
# singleton towards the group (each reducing the closest distance 2 -> 1)
assert moves == {"4,2>2,3", "2,5>2,4"}, moves
print("(c) group extrusion / no-split OK")

# ---- (d) distance-rule reading + join exception -------------------------------
# Joining is always legal even though the merged unit's nearest OTHER unit
# (6,0) is farther (5) than the old closest distance (1) — a naive
# "recompute closest after the move" reading would wrongly reject this.
s = state(9, black=[(0, 0), (0, 2), (6, 0)], white=[(8, 8), (8, 6)])
assert "0,0>0,1" in G.legal_moves(s)
s2 = G.apply_move(s, "0,0>0,1")
comp = {p for p, c in s2.board.items() if c == 0}
assert comp == {(0, 1), (0, 2), (6, 0)}
# units with NO reachable friendly unit are immobile -> stuck player WINS,
# even with several units on the board (White wall separates the two Blacks)
s = state(5, black=[(0, 0), (0, 4)],
          white=[(0, 2), (1, 2), (2, 2), (3, 2), (4, 2)], to_move=0)
assert G.legal_moves(s) == [] and G.is_terminal(s)
assert G.returns(s) == [1.0, -1.0], "stuck Black must WIN"
print("(d) distance reading + join exception OK")

# ---- (e) cannot move = win, reached via apply_move -----------------------------
s = state(7, black=[(0, 0), (0, 2)], white=[(6, 6), (6, 4)])
s = G.apply_move(s, "0,0>0,1")   # Black joins into a single group
assert not G.is_terminal(s)       # White (2 units) can still move
s = G.apply_move(s, "6,6>6,5")   # White joins too; Black to move with 1 group
assert G.is_terminal(s)
assert G.returns(s) == [1.0, -1.0], "Black cannot move -> Black wins"
print("(e) stuck-player-wins via apply_move OK")

# ---- (f) repetition draw --------------------------------------------------------
base = state(9, black=[(2, 2), (3, 2), (4, 2), (2, 5)], white=[(7, 7), (7, 5)])
nxt = G.apply_move(base, "2,5>2,4")
key = nxt.history[-1]
seeded = state(9, black=[(2, 2), (3, 2), (4, 2), (2, 5)], white=[(7, 7), (7, 5)],
               history=[key])
rep = G.apply_move(seeded, "2,5>2,4")
assert rep.drawn and rep.draw_kind == "repetition"
assert G.is_terminal(rep) and G.returns(rep) == [0.0, 0.0]
print("(f) repetition draw OK")

# ---- (g) termination + swap + serialize round-trip ------------------------------
for seed, size in ((1, 9), (2, 11)):
    rng = random.Random(seed)
    s = G.initial_state(options={"size": size, "pie": True})
    n = 0
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        n += 1
        assert n < G._ply_cap(size) + 2
    r = G.returns(s)
    assert len(r) == 2 and all(isinstance(x, float) for x in r)
    snap = G.serialize(s)
    assert G.serialize(G.deserialize(snap)) == snap
# pie: swap available exactly on White's first turn, flips seat colours
s = G.initial_state(options={"pie": True})
s = G.apply_move(s, G.legal_moves(s)[0])
assert "swap" in G.legal_moves(s)
sw = G.apply_move(s, "swap")
assert sw.swapped and G.current_player(sw) == 0
assert "White to move" in G.render(sw)["caption"], "after swap, seat 0 plays White"
assert "swap" not in G.legal_moves(sw)
G.apply_move(sw, G.legal_moves(sw)[0])  # White (seat 0) can move on
# render probe
spec = G.render(G.initial_state())
assert spec["board"] == {"type": "square", "width": 11, "height": 11}
assert len(spec["pieces"]) == 60 and {p["owner"] for p in spec["pieces"]} == {0, 1}
print("(g) termination / swap / render OK")

print("ayu selftest: all checks passed")
