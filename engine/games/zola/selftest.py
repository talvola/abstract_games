"""Zola selftest — anchors the implementation against the official rule sheet
(marksteeregames.com/Zola.pdf, Mark Steere, February 2021):

 (a) initial setup: Figure 1 — the board starts completely filled with a
     checkered pattern (18 checkers each on 6x6; bottom-left square Red as
     drawn, since the renderer puts row 0 at the bottom); Red moves first;
     8x8 option extends the same pattern; odd sizes rejected;
 (b) the "DISTANCE FROM CENTER" sidebar: on 6x6 the squares fall into exactly
     6 levels (integer metric d2 = 2/10/18/26/34/50 with 4/8/4/8/8/4 squares),
     level 1 = the four central squares, level 6 = the corners;
 (c) Figure 2 (non-capturing): the diagrammed Red checker has EXACTLY the
     three shown king-steps, each strictly away from the center;
 (d) Figure 3 (capturing): the diagrammed Blue checker has EXACTLY the two
     shown queen-line captures (A: level 5 -> level 5 "maintain", B: closer);
 (e) the sidebar's worked examples (quiet 2->3/4/5; capture 4->4; capture
     6->1) plus adjacent ("zero unoccupied squares") captures;
 (f) illegal moves raise: inward/level-equal quiet steps, multi-step quiet
     moves, outward captures, blocked capture lines, capturing your own
     checker, moving the opponent's checker, pass while moves exist;
 (g) forced sit-out: a player with no moves has exactly ["pass"]; passing
     never changes the board; the win (capture ALL enemy checkers) is reached
     via apply_move;
 (h) an independent Fraction-based move-generation oracle agrees on the
     opening position and 300 random positions;
 (i) 500 random playouts (6x6 and 8x8): per-move invariants (captures shrink
     the checker count and never move outward; quiet moves are king steps
     strictly outward), every game ends decisively — no draws, never two
     passes in a row; serialize round-trip;
 (j) exhaustive solve of the 2x2 board: decisive, and NO reachable position
     leaves both players stuck (the PDF's "at least one of the two players
     will always have a move available").

Pure stdlib. Run: PYTHONPATH=. python3 games/zola/selftest.py
"""

import pathlib
import random
import sys
from fractions import Fraction

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = pathlib.Path(__file__).resolve().parent
_, G = load_from_dir(PKG)

RED, BLUE = 0, 1


def state(size, red, blue, to_move=RED):
    return G.deserialize({
        "size": size,
        "board": {**{f"{c},{r}": RED for c, r in red},
                  **{f"{c},{r}": BLUE for c, r in blue}},
        "to_move": to_move, "ply": 10, "last": None,
    })


def d2(c, r, n):
    return (2 * c - (n - 1)) ** 2 + (2 * r - (n - 1)) ** 2


# ---- (a) Figure 1: full checkered fill, Red on the bottom-left square ----------
s0 = G.initial_state()
assert s0.size == 6 and len(s0.board) == 36, "6x6 starts completely filled"
for (c, r), owner in s0.board.items():
    assert owner == (RED if (c + r) % 2 == 0 else BLUE), (c, r, owner)
counts = [0, 0]
for owner in s0.board.values():
    counts[owner] += 1
assert counts == [18, 18]
assert s0.board[(0, 0)] == RED      # bottom-left square as drawn (row 0 = bottom)
assert s0.board[(5, 5)] == RED and s0.board[(0, 5)] == BLUE and s0.board[(5, 0)] == BLUE
assert G.current_player(s0) == RED  # "starting with Red"
assert "Red to move" in G.render(s0)["caption"]
s8 = G.initial_state(options={"size": 8})
assert len(s8.board) == 64 and s8.board[(0, 0)] == RED and s8.board[(7, 0)] == BLUE
for bad_size in (5, 7):
    try:
        G.initial_state(options={"size": bad_size})
        raise AssertionError("odd board size must be rejected")
    except ValueError:
        pass
# the opening position has ONLY captures (no empty squares -> no quiet moves)
opening = G.legal_moves(s0)
assert opening and "pass" not in opening
for m in opening:
    frm, to = (tuple(map(int, p.split(","))) for p in m.split(">"))
    assert to in s0.board and s0.board[to] == BLUE, m       # every move captures
    assert abs(frm[0] - to[0]) + abs(frm[1] - to[1]) == 1, m  # orthogonal-adjacent
    assert d2(*to, 6) <= d2(*frm, 6), m
assert "0,0>1,0" in opening and "0,0>0,1" in opening  # corner dives inward
assert "3,3>3,2" in opening        # level-1 to level-1 "maintain" capture
assert "3,3>3,4" not in opening    # outward capture forbidden
print("(a) Figure-1 initial setup OK")

# ---- (b) the 6 distance levels of the sidebar -----------------------------------
levels = {}
for c in range(6):
    for r in range(6):
        levels.setdefault(d2(c, r, 6), set()).add((c, r))
assert sorted(levels) == [2, 10, 18, 26, 34, 50], sorted(levels)
assert [len(levels[k]) for k in sorted(levels)] == [4, 8, 4, 8, 8, 4]
assert levels[2] == {(2, 2), (2, 3), (3, 2), (3, 3)}          # level 1
assert levels[50] == {(0, 0), (0, 5), (5, 0), (5, 5)}          # level 6 = corners
print("(b) six distance levels OK")

# ---- (c) Figure 2: exactly three non-capturing moves ----------------------------
# PDF Figure 2 in this port's coordinates (row 0 at the bottom): Red on (1,3),
# Blue on (0,3) and (1,1). Red's only moves are the three arrows.
fig2 = state(6, red=[(1, 3)], blue=[(0, 3), (1, 1)], to_move=RED)
assert set(G.legal_moves(fig2)) == {"1,3>0,2", "1,3>0,4", "1,3>1,4"}, G.legal_moves(fig2)
for m in G.legal_moves(fig2):
    to = tuple(map(int, m.split(">")[1].split(",")))
    assert to not in fig2.board and d2(*to, 6) > d2(1, 3, 6)  # quiet, outward
    assert " > " in G.describe_move(fig2, m)
print("(c) Figure 2 non-capturing anchor OK")

# ---- (d) Figure 3: exactly two moves, both captures ------------------------------
# Figure 3 in this port's coordinates: Red on (1,5), (5,5), (2,1), (5,0);
# Blue on (5,1), to move. Move A = 5,1>1,5 (level 5 -> level 5, "equally
# distant"); move B = 5,1>2,1 ("closer to the center").
fig3 = state(6, red=[(1, 5), (5, 5), (2, 1), (5, 0)], blue=[(5, 1)], to_move=BLUE)
assert set(G.legal_moves(fig3)) == {"5,1>1,5", "5,1>2,1"}, G.legal_moves(fig3)
assert d2(1, 5, 6) == d2(5, 1, 6) == 34          # A maintains the distance
assert d2(2, 1, 6) < d2(5, 1, 6)                 # B decreases it
assert G.describe_move(fig3, "5,1>1,5") == "5,1 x 1,5"
after_a = G.apply_move(fig3, "5,1>1,5")
assert after_a.board[(1, 5)] == BLUE and (5, 1) not in after_a.board  # replaced
assert sum(1 for o in after_a.board.values() if o == RED) == 3
print("(d) Figure 3 capturing anchor OK")

# ---- (e) the sidebar's worked examples -------------------------------------------
# Example 1: quiet king-step from level 2 to level 3, 4 or 5 (Figure 2's moves
# land on d2 18/26/34 = levels 3/4/5 from level 2 — covered in (c)).
assert {d2(*tuple(map(int, m.split(">")[1].split(","))), 6)
        for m in G.legal_moves(fig2)} == {18, 26, 34}
# Example 2: capture from level 4 to level 4 (d2 26 -> 26); Figure 3's move A
# is the same "maintain" rule one level out (level 5 -> 5, covered in (d)).
s = state(6, red=[(2, 0)], blue=[(0, 2)], to_move=RED)
assert d2(2, 0, 6) == d2(0, 2, 6) == 26                    # both level 4
assert "2,0>0,2" in G.legal_moves(s)                       # diagonal via empty (1,1)
# Example 3: capture from level 6 to level 1 (corner dives to the center).
s = state(6, red=[(0, 0)], blue=[(3, 3), (0, 3)], to_move=RED)
assert "0,0>3,3" in G.legal_moves(s)             # level 6 -> level 1, long diagonal
assert "0,0>0,3" in G.legal_moves(s)             # and a rook-line capture
# "zero or more unoccupied squares": an ADJACENT enemy is capturable too.
s = state(6, red=[(2, 2)], blue=[(3, 3), (2, 3)], to_move=RED)
moves = set(G.legal_moves(s))
assert "2,2>3,3" in moves and "2,2>2,3" in moves  # level 1 -> level 1, zero gaps
print("(e) sidebar worked examples OK")

# ---- (f) illegal moves raise -------------------------------------------------------
for bad in ("1,3>1,2",    # quiet step, same level (must strictly increase)
            "1,3>2,3",    # quiet step inward
            "1,3>1,5",    # two-step quiet move (king step only)
            "1,3>0,3",    # capture outward (10 -> 26)
            "1,3>1,1",    # capture outward (10 -> 18)
            "0,3>0,4",    # not your checker
            "3,3>4,4",    # empty source
            "1,3>2,5",    # not a straight line (knight-ish)
            "pass",       # pass while moves exist
            "garbage"):
    try:
        G.apply_move(fig2, bad)
        raise AssertionError(f"{bad} should be illegal")
    except ValueError:
        pass
# a capture line must stop at the FIRST checker (blocked beyond it)
s = state(6, red=[(5, 1), (4, 1)], blue=[(2, 1)], to_move=RED)
assert "5,1>2,1" not in G.legal_moves(s)          # own checker blocks the line
s = state(6, red=[(5, 1)], blue=[(4, 1), (2, 1)], to_move=RED)
moves = set(G.legal_moves(s))
assert "5,1>4,1" in moves and "5,1>2,1" not in moves  # capture the first only
for bad in ("5,1>2,1",    # blocked capture
            "5,1>4,1>3,1"):  # multi-leg path
    try:
        G.apply_move(s, bad)
        raise AssertionError(f"{bad} should be illegal")
    except ValueError:
        pass
s = state(6, red=[(5, 1), (4, 1)], blue=[(2, 1)], to_move=RED)
try:
    G.apply_move(s, "5,1>4,1")                    # capturing your OWN checker
    raise AssertionError("own-capture should be illegal")
except ValueError:
    pass
print("(f) illegal-move rejection OK")

# ---- (g) forced pass + the capture-all win (via apply_move) -----------------------
# Red's lone corner checker: no outward neighbor, no enemy on any open line ->
# Red must sit the game out; "pass" is the ONLY legal move and changes nothing.
s = state(6, red=[(0, 0)], blue=[(2, 1)], to_move=RED)
assert not G.is_terminal(s)
assert G.legal_moves(s) == ["pass"]
assert "must pass" in G.render(s)["caption"]
s2 = G.apply_move(s, "pass")
assert s2.board == s.board and G.current_player(s2) == BLUE
assert G.legal_moves(s2) and "pass" not in G.legal_moves(s2)  # Blue has real moves
# Win: capturing the LAST enemy checker ends the game (checked via apply_move —
# "winner" semantics live in the position, not a hand-built dead state).
s = state(6, red=[(0, 0)], blue=[(3, 3)], to_move=RED)
assert not G.is_terminal(s)
end = G.apply_move(s, "0,0>3,3")
assert G.is_terminal(end) and G.legal_moves(end) == []
assert G.returns(end) == [1.0, -1.0]
assert "Red" in G.render(end)["caption"] and "wins" in G.render(end)["caption"]
# and the mirror for Blue
s = state(6, red=[(3, 2)], blue=[(0, 5)], to_move=BLUE)
end = G.apply_move(s, "0,5>3,2")
assert G.is_terminal(end) and G.returns(end) == [-1.0, 1.0]
print("(g) forced pass + capture-all win OK")


# ---- (h) independent Fraction-based move oracle ------------------------------------
def oracle_moves(st):
    """Independent movegen: true squared Euclidean distance to the center
    point ((n-1)/2, (n-1)/2), exact rationals, separate quiet/capture scans."""
    n = st.size
    ctr = Fraction(n - 1, 2)

    def dist(p):
        return (p[0] - ctr) ** 2 + (p[1] - ctr) ** 2

    out = set()
    for p, owner in st.board.items():
        if owner != st.to_move:
            continue
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if (dc, dr) == (0, 0):
                    continue
                q = (p[0] + dc, p[1] + dr)
                if 0 <= q[0] < n and 0 <= q[1] < n and q not in st.board \
                        and dist(q) > dist(p):
                    out.add(f"{p[0]},{p[1]}>{q[0]},{q[1]}")
                q = (p[0] + dc, p[1] + dr)
                while 0 <= q[0] < n and 0 <= q[1] < n:
                    if q in st.board:
                        if st.board[q] != owner and dist(q) <= dist(p):
                            out.add(f"{p[0]},{p[1]}>{q[0]},{q[1]}")
                        break
                    q = (q[0] + dc, q[1] + dr)
    return out


assert set(opening) == oracle_moves(s0)
rng = random.Random(2021)
cells6 = [(c, r) for c in range(6) for r in range(6)]
cells8 = [(c, r) for c in range(8) for r in range(8)]
for i in range(300):
    n = 6 if i % 3 else 8
    cells = cells6 if n == 6 else cells8
    k = rng.randint(2, 14)
    picks = rng.sample(cells, k)
    reds = rng.randint(1, k - 1)
    st = state(n, red=picks[:reds], blue=picks[reds:], to_move=rng.randint(0, 1))
    got = set(G.legal_moves(st)) - {"pass"}
    assert got == oracle_moves(st), (G.serialize(st), got ^ oracle_moves(st))
print("(h) 300-position independent oracle agreement OK")

# ---- (i) 500 random playouts: invariants, decisive, no draws ----------------------
stats = {RED: 0, BLUE: 0}
lengths, passes_seen = [], 0
rng = random.Random(20210206)
for i in range(500):
    size = 6 if i % 5 else 8
    st = G.initial_state(options={"size": size})
    n_moves, last_was_pass = 0, False
    while not G.is_terminal(st):
        mv = rng.choice(G.legal_moves(st))
        before, total = st.board, len(st.board)
        sum_before = sum(d2(c, r, size) for (c, r) in st.board)
        st = G.apply_move(st, mv)
        if mv == "pass":
            assert not last_was_pass, "two passes in a row = both stuck (impossible)"
            assert st.board == before
            last_was_pass = True
            passes_seen += 1
        else:
            last_was_pass = False
            frm, to = (tuple(map(int, p.split(","))) for p in mv.split(">"))
            if len(st.board) < total:                      # capture
                assert len(st.board) == total - 1
                assert d2(*to, size) <= d2(*frm, size)
            else:                                          # quiet move
                assert max(abs(frm[0] - to[0]), abs(frm[1] - to[1])) == 1
                assert d2(*to, size) > d2(*frm, size)
                assert sum(d2(c, r, size) for (c, r) in st.board) > sum_before
        n_moves += 1
        assert n_moves < 5000, "runaway game"
    r = G.returns(st)
    assert sorted(r) == [-1.0, 1.0], f"Zola is drawless, got {r}"
    stats[RED if r[0] > 0 else BLUE] += 1
    if size == 6:
        lengths.append(n_moves)
    snap = G.serialize(st)
    assert G.serialize(G.deserialize(snap)) == snap
print(f"(i) 500 playouts OK — wins Red {stats[RED]} / Blue {stats[BLUE]}, "
      f"forced passes {passes_seen}, 6x6 plies min/avg/max = "
      f"{min(lengths)}/{sum(lengths) // len(lengths)}/{max(lengths)}")


# ---- (j) exhaustive 2x2 solve: decisive + "someone can always move" ----------------
def solve(st, memo):
    key = (tuple(sorted(st.board.items())), st.to_move)
    if key in memo:
        return memo[key]
    memo[key] = 0.0  # cycle guard (passing could revisit; value overwritten below)
    if G.is_terminal(st):
        counts = [0, 0]
        for o in st.board.values():
            counts[o] += 1
        assert counts[RED] == 0 or counts[BLUE] == 0, \
            "both players stuck — contradicts the rule sheet"
        v = 1.0 if counts[1 - st.to_move] == 0 else -1.0
    else:
        v = max(-solve(G.apply_move(st, m), memo) for m in G.legal_moves(st))
    memo[key] = v
    return v


memo = {}
v = solve(G.initial_state(options={"size": 2}), memo)
assert v in (1.0, -1.0), "Zola is drawless"
print(f"(j) 2x2 exhaustive solve OK — {'Red' if v > 0 else 'Blue'} wins "
      f"with perfect play ({len(memo)} states)")

# ---- render probe -------------------------------------------------------------------
spec = G.render(s0)
assert spec["board"] == {"type": "square", "width": 6, "height": 6}
assert len(spec["pieces"]) == 36 and {p["owner"] for p in spec["pieces"]} == {0, 1}
assert all("," in p["cell"] and ">" not in p["cell"] for p in spec["pieces"])
after = G.apply_move(s0, sorted(G.legal_moves(s0))[0])
sp2 = G.render(after)
assert len(sp2["highlights"]) == 2
assert {h["kind"] for h in sp2["highlights"]} == {"last-move"}
assert len(sp2["pieces"]) == 35
print("render probe OK")

print("zola selftest: all checks passed")
