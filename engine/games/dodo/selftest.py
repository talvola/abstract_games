"""Dodo selftest — anchors the implementation against the official rule sheet
(marksteeregames.com/Dodo_rules.pdf, Mark Steere, May 2021):

 (a) initial setup: the exact 13+13 checker layout of the PDF's Figure 1
     (transcribed cell-by-cell; shown rotated a quarter-turn: Red = left
     corner region, Blue = right), 11-cell empty central band, point-
     symmetric, Red moves first;
 (b) movement: exactly one cell "directly forward or diagonally forward" —
     the three-direction set verified for BOTH players (PDF Figure 2), and
     the full 13-move opening list for Red hardcoded;
 (c) all moves are to unoccupied cells: no captures, no jumps, no backward /
     sideways steps (illegal applies raise);
 (d) object: a player with no moves at the START of their turn WINS —
     reached via apply_move, plus a hand-built stuck position;
 (e) finiteness: every move strictly increases the mover's forward-progress
     sum by exactly 1 or 2 (asserted per move over 500 random playouts, all
     of which terminate decisively far below the ply cap — no draws);
 (f) exhaustive negamax solve of the side-2 board (1 checker each).

Pure stdlib. Run: PYTHONPATH=. python3 games/dodo/selftest.py
"""

import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = pathlib.Path(__file__).resolve().parent
_, G = load_from_dir(PKG)

RED, BLUE = 0, 1


def state(size, red, blue, to_move=0):
    return G.deserialize({
        "size": size,
        "board": {**{f"{q},{r}": RED for q, r in red},
                  **{f"{q},{r}": BLUE for q, r in blue}},
        "to_move": to_move, "ply": 6, "drawn": False, "last": None,
    })


# ---- (a) initial setup: Figure 1, cell by cell --------------------------------
# PDF Figure 1 (hexhex-4): per line from each player's corner the checker
# counts are 1,2,2,3,2,2,1 (13 each), leaving a 3-file central band of 11
# empty cells. Transcribed in this port's orientation (Red = left corner):
FIG1_RED = {(0, -3), (-1, -2), (0, -2), (-2, -1), (-1, -1),
            (-3, 0), (-2, 0), (-1, 0),
            (-3, 1), (-2, 1), (-3, 2), (-2, 2), (-3, 3)}
FIG1_BLUE = {(-q, -r) for (q, r) in FIG1_RED}
FIG1_EMPTY = {(1, -3), (0, -1), (-1, 1), (-2, 3),      # band 2q+r = -1
              (1, -2), (0, 0), (-1, 2),                 # band 2q+r =  0
              (2, -3), (1, -1), (0, 1), (-1, 3)}        # band 2q+r = +1

s0 = G.initial_state()
assert s0.size == 4
reds = {p for p, c in s0.board.items() if c == RED}
blues = {p for p, c in s0.board.items() if c == BLUE}
assert reds == FIG1_RED, reds ^ FIG1_RED
assert blues == FIG1_BLUE, blues ^ FIG1_BLUE
assert len(reds) == 13 and len(blues) == 13          # "13 checkers per player"
all_cells = {(q, r) for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3}
assert len(all_cells) == 37
assert all_cells - reds - blues == FIG1_EMPTY        # empty central band
assert blues == {(-q, -r) for (q, r) in reds}        # point symmetry
assert G.current_player(s0) == RED                   # "starting with Red"
assert "Red to move" in G.render(s0)["caption"]
# size option keeps the same construction (all cells beyond the 3-file band)
for size, per_side in ((3, 6), (5, 24), (6, 37)):
    st = G.initial_state(options={"size": size})
    n = sum(1 for c in st.board.values() if c == RED)
    assert n == per_side == sum(1 for c in st.board.values() if c == BLUE), (size, n)
    assert {p for p, c in st.board.items() if c == BLUE} == \
        {(-q, -r) for (q, r), c in st.board.items() if c == RED}
print("(a) Figure-1 initial setup OK")

# ---- (b) forward directions (Figure 2) + exact opening move list ----------------
# Lone Red checker at the centre: exactly E, NE, SE.
s = state(4, red=[(0, 0)], blue=[(3, 0)], to_move=RED)
assert set(G.legal_moves(s)) == {"0,0>1,0", "0,0>1,-1", "0,0>0,1"}, G.legal_moves(s)
# Lone Blue checker at the centre: exactly W, NW, SW (mirror).
s = state(4, red=[(-3, 0)], blue=[(0, 0)], to_move=BLUE)
assert set(G.legal_moves(s)) == {"0,0>-1,0", "0,0>0,-1", "0,0>-1,1"}, G.legal_moves(s)
# Direction is absolute (Figure 2 shows a red checker deep in blue territory
# still moving toward blue's corner): red on blue's home corner cell is stuck-y
# only by geometry, never re-oriented.
s = state(4, red=[(2, 0)], blue=[(-3, 3)], to_move=RED)
assert set(G.legal_moves(s)) == {"2,0>3,0", "2,0>3,-1", "2,0>2,1"}
# Red's full opening move list (hand-derived from Figure 1: only checkers on
# the two files bordering the band can move, all into the empty band).
OPENING = {
    "0,-2>1,-2", "-1,0>0,0", "-2,2>-1,2",        # directly forward (E)
    "0,-2>1,-3", "-1,0>0,-1", "-2,2>-1,1",       # diagonally forward (NE)
    "0,-2>0,-1", "-1,0>-1,1", "-2,2>-2,3",       # diagonally forward (SE)
    "0,-3>1,-3", "-1,-1>0,-1", "-2,1>-1,1", "-3,3>-2,3",  # from the back file (E)
}
assert set(G.legal_moves(s0)) == OPENING, set(G.legal_moves(s0)) ^ OPENING
assert len(G.legal_moves(s0)) == 13
print("(b) forward-direction sets + opening list OK")

# ---- (c) moves only to unoccupied cells; no captures / jumps / backward ---------
s = state(4, red=[(0, 0), (1, 0)], blue=[(0, 1), (3, -3)], to_move=RED)
moves = set(G.legal_moves(s))
assert "0,0>1,0" not in moves and "0,0>0,1" not in moves  # occupied targets
assert moves == {"0,0>1,-1", "1,0>2,0", "1,0>2,-1", "1,0>1,1"}, moves
for bad in ("0,0>1,0",    # onto own checker (no stacking)
            "0,0>0,1",    # onto enemy checker (no captures)
            "0,0>-1,0",   # backward
            "0,0>0,-1",   # backward-diagonal
            "0,0>2,0",    # jump (two cells)
            "1,0>1,-1"):  # sideways-ish backward diagonal
    try:
        G.apply_move(s, bad)
        raise AssertionError(f"{bad} should be illegal")
    except ValueError:
        pass
# board edge: no wrapping
s = state(4, red=[(3, 0)], blue=[(-3, 0)], to_move=RED)
assert G.legal_moves(s) == []  # E/NE/SE all off-board at the right corner
print("(c) empty-target / no-capture / forward-only OK")

# ---- (d) no moves at the start of your turn => YOU win --------------------------
# Hand-built: Blue to move, lone Blue checker on Red's home corner (-3,0):
# W/NW/SW are all off-board -> terminal immediately, Blue wins.
s = state(4, red=[(0, 0)], blue=[(-3, 0)], to_move=BLUE)
assert G.is_terminal(s) and G.returns(s) == [-1.0, 1.0]
# Reached via apply_move: Red moves; Blue then has no move and WINS.
s = state(4, red=[(0, 0)], blue=[(-3, 0)], to_move=RED)
assert not G.is_terminal(s)               # Red still has moves
s2 = G.apply_move(s, "0,0>1,0")
assert G.is_terminal(s2)
assert G.returns(s2) == [-1.0, 1.0], "stuck Blue must WIN"
assert "Blue cannot move" in G.render(s2)["caption"]
# and the mirror: Red hemmed in by its OWN flock at the right corner — after
# Blue's move, Red has no moves at the start of its turn and WINS.
s = state(4, red=[(3, 0), (3, -1), (2, 1), (2, 0)], blue=[(0, 0)], to_move=BLUE)
assert not G.is_terminal(s)               # Blue can still move
s2 = G.apply_move(s, "0,0>-1,0")
assert G.is_terminal(s2)
assert G.returns(s2) == [1.0, -1.0], "stuck Red must WIN"
assert "Red cannot move" in G.render(s2)["caption"]
print("(d) stuck-player-wins OK")

# ---- (e) 500 random playouts: monotone progress, decisive, no draws -------------
def potential(st, seat):
    sgn = 1 if seat == RED else -1
    return sum(sgn * (2 * q + r) for (q, r), c in st.board.items() if c == seat)

stats = {RED: 0, BLUE: 0}
lengths = []
rng = random.Random(2021)
for i in range(500):
    size = (4, 4, 4, 3, 5)[i % 5]
    st = G.initial_state(options={"size": size})
    n = 0
    while not G.is_terminal(st):
        mover = G.current_player(st)
        p_before = potential(st, mover)
        st = G.apply_move(st, rng.choice(G.legal_moves(st)))
        gain = potential(st, mover) - p_before
        assert gain in (1, 2), f"move must gain exactly 1 or 2 progress, got {gain}"
        n += 1
        assert n < 700, "runaway game"
    assert not st.drawn, "draw backstop must be unreachable"
    r = G.returns(st)
    assert sorted(r) == [-1.0, 1.0]
    stats[G.current_player(st)] += 1  # the player to move is stuck and wins
    if size == 4:
        lengths.append(n)
    snap = G.serialize(st)
    assert G.serialize(G.deserialize(snap)) == snap
print(f"(e) 500 playouts OK — wins by seat {stats}, "
      f"size-4 plies min/avg/max = {min(lengths)}/{sum(lengths)//len(lengths)}/{max(lengths)}")

# ---- (f) exhaustive solve, side-2 board (1 checker each) ------------------------
def solve(st, memo):
    key = (tuple(sorted((p, c) for p, c in st.board.items())), st.to_move)
    if key in memo:
        return memo[key]
    if G.is_terminal(st):
        v = 1.0  # player to move is stuck -> wins
    else:
        v = max(-solve(G.apply_move(st, m), memo) for m in G.legal_moves(st))
    memo[key] = v
    return v

memo = {}
v = solve(G.initial_state(options={"size": 2}), memo)
assert v in (1.0, -1.0), "Dodo is drawless"
print(f"(f) side-2 exhaustive solve OK — {'Red' if v > 0 else 'Blue'} wins "
      f"with perfect play ({len(memo)} states)")

# ---- render probe ----------------------------------------------------------------
spec = G.render(s0)
assert spec["board"] == {"type": "hex", "shape": "hexagon", "size": 4}
assert len(spec["pieces"]) == 26 and {p["owner"] for p in spec["pieces"]} == {0, 1}
ids = {p["cell"] for p in spec["pieces"]}
assert all("," in i and ">" not in i for i in ids)
after = G.apply_move(s0, sorted(G.legal_moves(s0))[0])
sp2 = G.render(after)
assert len(sp2["highlights"]) == 2
assert {h["kind"] for h in sp2["highlights"]} == {"last-move"}
print("render probe OK")

print("dodo selftest: all checks passed")
