"""Tintas correctness anchor -- pure stdlib, fast, seeded.

Run: PYTHONPATH=. python3 games/tintas/selftest.py

No published perft exists for Tintas; the anchor is the official rule set
(spielstein.com/games/tintas/rules) as baked assertions plus hand-built
positions exercising each core rule:
  (a) the official 49-cell board (hexhex-4 core + six 2-cell pinwheel bumps,
      closed under the 60-degree rotation) -- verified against the official
      board diagram;
  (b) random setup deals 7x7 colours and re-deals a single-clump colour;
  (c) slides stop on the FIRST occupied cell of a line (no passing through);
  (d) chaining is same-colour only and stopping is optional ("end");
  (e) a stuck pawn must jump to any occupied cell and the turn then ends;
  (f) collecting all 7 of a colour wins instantly;
  (g) once no colour can be completed, 4+ pieces in 4+ colours wins;
  (h) seeded random playouts terminate within 49 collections with a winner.
"""

import json
import random
import sys

from games.tintas.game import (
    Tintas, TState, CELLS, CELLSET, BUMPS, COLORS, _cid, _zero_hand,
)


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


G = Tintas()

# ---- (a) board geometry -----------------------------------------------------
check(len(CELLS) == 49, "board must have exactly 49 cells")
core = [c for c in CELLS if max(abs(c[0]), abs(c[1]), abs(c[0] + c[1])) <= 3]
check(len(core) == 37, "hexhex-4 core must be 37 cells")
check(len(BUMPS) == 12 and all(b in CELLSET for b in BUMPS), "12 bump cells")
rot = {(-r, q + r) for (q, r) in CELLS}
check(rot == set(CELLS), "board must close under the 60-degree rotation")

# ---- (b) random setup ---------------------------------------------------------
for seed in range(5):
    s0 = G.initial_state(rng=random.Random(seed))
    counts = {c: 0 for c in COLORS}
    for col in s0.board.values():
        counts[col] += 1
    check(all(counts[c] == 7 for c in COLORS), f"setup must be 7x7 (seed {seed})")
    check(len(s0.board) == 49 and s0.pawn is None and s0.to_move == 0,
          "initial state: full board, pawn off-board, player 1 to move")
    for c in COLORS:  # official constraint: no colour as ONE adjacent group of 7
        cells7 = [cell for cell, col in s0.board.items() if col == c]
        check(not G._one_clump(cells7), f"setup left colour {c} as one clump")
    check(len(G.legal_moves(s0)) == 49, "first move: place the pawn anywhere")

# same seed -> same deal (seedable despite has_randomness)
a = G.serialize(G.initial_state(rng=random.Random(11)))
b = G.serialize(G.initial_state(rng=random.Random(11)))
check(a == b, "setup must be reproducible from the rng seed")

# serialize round-trip + JSON-able
s0 = G.initial_state(rng=random.Random(1))
ser = G.serialize(s0)
check(G.serialize(G.deserialize(ser)) == ser, "serialize must round-trip")
json.dumps(ser)

# opening placement collects the piece and ends the turn
mv = "0,0"
col0 = s0.board[(0, 0)]
s1 = G.apply_move(s0, mv)
check(s1.pawn == (0, 0) and (0, 0) not in s1.board, "placement sets the pawn")
check(s1.collected[0][col0] == 1 and s1.to_move == 1, "placement collects, turn ends")
check(len(s0.board) == 49, "apply_move must not mutate its input")

# ---- (c) slide mechanics ------------------------------------------------------
def hand(board, pawn, to_move=0, chain=None, c0=None, c1=None):
    return TState(board=dict(board), pawn=pawn,
                  collected=[c0 or _zero_hand(), c1 or _zero_hand()],
                  to_move=to_move, chain=chain)

s = hand({(1, 0): "R", (2, 0): "G", (0, 2): "R", (-1, 0): "B"}, (0, 0))
lm = set(G.legal_moves(s))
check(lm == {"1,0", "0,2", "-1,0"},
      f"slides stop at the FIRST occupied cell in each line, got {lm}")
check("2,0" not in lm, "cannot slide past an occupied cell")
ns = G.apply_move(s, "1,0")
check(ns.collected[0]["R"] == 1 and ns.pawn == (1, 0), "slide collects the piece")
check(ns.to_move == 1 and ns.chain is None,
      "no same-colour continuation -> turn ends automatically")

# ---- (d) same-colour chain, optional stop -------------------------------------
s = hand({(2, 0): "R", (0, 2): "R", (3, 0): "G", (2, 1): "B"}, (0, 0))
ns = G.apply_move(s, "2,0")            # collect red; red at (0,2) is in line
check(ns.to_move == 0 and ns.chain == "R", "same-colour continuation keeps the turn")
lm = set(G.legal_moves(ns))
check(lm == {"0,2", "end"}, f"chain offers same-colour targets + end, got {lm}")
check("2,1" not in lm, "chain may not land on a different colour")
stop = G.apply_move(ns, "end")          # stopping is optional and explicit
check(stop.to_move == 1 and stop.chain is None and stop.collected[0]["R"] == 1,
      "'end' stops the chain without collecting")
go = G.apply_move(ns, "0,2")            # ... or keep collecting
check(go.collected[0]["R"] == 2 and go.pawn == (0, 2), "chained collection")
check(go.to_move == 1 and go.chain is None, "chain ends when no target remains")

# ---- (e) stuck pawn: jump anywhere, turn ends -----------------------------------
# (0,0) sees only the three lines q=0 / r=0 / q+r=0; (1,1) and (2,1) are on none.
s = hand({(1, 1): "R", (2, 1): "G"}, (0, 0))
check(G._slide_targets(s) == [], "test position: pawn must be stuck")
lm = set(G.legal_moves(s))
check(lm == {"1,1", "2,1"}, f"stuck pawn jumps to any occupied cell, got {lm}")
ns = G.apply_move(s, "1,1")
check(ns.pawn == (1, 1) and ns.collected[0]["R"] == 1, "jump collects the piece")
check(ns.to_move == 1 and ns.chain is None, "the turn ends after a jump (no chain)")

# ---- (f) instant 7-of-a-colour win ---------------------------------------------
c0 = _zero_hand(); c0["R"] = 6
s = hand({(1, 0): "R", (0, 1): "G"}, (0, 0), c0=c0)
check(not G.is_terminal(s), "6 of a colour is not yet a win")
ns = G.apply_move(s, "1,0")
check(ns.winner == 0 and G.is_terminal(ns), "7th piece of a colour wins instantly")
check(G.returns(ns) == [1.0, -1.0], "winner payoff")

# ---- (g) end condition + 4-in-4 majority ---------------------------------------
# Both players hold >=1 of every colour -> no colour can be completed any more.
c0 = {"R": 4, "O": 4, "Y": 4, "G": 3, "B": 1, "P": 1, "W": 1}
c1 = {"R": 1, "O": 1, "Y": 1, "G": 1, "B": 2, "P": 2, "W": 2}
s = hand({(1, 0): "G", (0, 1): "W", (3, 0): "B"}, (0, 0), c0=dict(c0), c1=dict(c1))
check(not G.is_terminal(s), "3 majority colours is not yet a majority win")
ns = G.apply_move(s, "1,0")             # 4th green = 4th majority colour
check(ns.winner == 0 and G.is_terminal(ns),
      "no colour completable + 4 pieces in 4 colours ends the game")
check(G.returns(ns) == [1.0, -1.0], "majority winner payoff")

# ... but with a colour still completable, the game must go on
c0 = {"R": 4, "O": 4, "Y": 4, "G": 3, "B": 0, "P": 0, "W": 0}
c1 = {"R": 1, "O": 1, "Y": 1, "G": 1, "B": 0, "P": 0, "W": 0}
s = hand({(1, 0): "G", (1, 1): "W"}, (0, 0), c0=dict(c0), c1=dict(c1))
ns = G.apply_move(s, "1,0")
check(ns.winner is None and not G.is_terminal(ns),
      "while a 7-of-a-colour is still possible the game goes on")

# ---- (h) seeded random playouts terminate with a winner -------------------------
for seed in (3, 7, 42):
    rng = random.Random(seed)
    s = G.initial_state(rng=rng)
    collections = 0
    plies = 0
    while not G.is_terminal(s):
        plies += 1
        check(plies <= 200, "playout must terminate")
        moves = G.legal_moves(s)
        check(moves, "non-terminal state must have legal moves")
        m = rng.choice(moves)
        if m != "end":
            collections += 1
        s = G.apply_move(s, m, rng=rng)
    check(collections <= 49, "at most 49 pieces can ever be collected")
    check(s.winner in (0, 1), "Tintas cannot end in a draw")
    r = G.returns(s)
    check(sorted(r) == [-1.0, 1.0], "terminal returns are win/loss")

# ---- render shape probe ----------------------------------------------------------
spec = G.render(G.initial_state(rng=random.Random(2)))
check(spec["board"]["type"] == "polygons", "render must use a polygons board")
cells = spec["board"]["cells"]
check(isinstance(cells, list) and len(cells) == 49, "polygons cells: LIST of 49")
check(all(set(c) >= {"id", "points"} and isinstance(c["points"], list)
          for c in cells), "each cell needs id + points")
check(len(spec["pieces"]) == 49, "49 pieces at setup (pawn off-board)")
spec2 = G.render(G.apply_move(G.initial_state(rng=random.Random(2)), "0,0"))
check(len(spec2["pieces"]) == 49, "48 pieces + the pawn after the first move")
check(any(p.get("cell") == "0,0" and p.get("label") == "✦"
          for p in spec2["pieces"]), "the pawn renders as a distinct piece")
check("0" in spec2["reserve"] and sum(spec2["reserve"]["0"].values()) == 1,
      "collected pieces show in the reserve tray")
json.dumps(spec2)

print("tintas selftest: all checks passed")
