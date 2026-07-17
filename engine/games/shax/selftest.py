"""Shax selftest -- pure stdlib.

Anchors:
(a) placement fills the board (24 men, no removals) and jare priority is tracked;
(b) transition double removal: first-jare player removes first, then the other,
    first-jare player slides first; captures may take men out of mills;
(c) no-jare placement: the second placer removes first / moves first (documented
    interpretation), removals still one each;
(d) oodan: a blocked player's turn becomes the opponent's forced freeing move;
    the freeing set is exactly the moves that free, and a freeing jare captures
    nothing;
(e) no flying: a 3-man player still slides only along lines;
(f) win by reduction to two men, reached via apply_move;
(g) draw backstops fire (50-ply clock, threefold repetition, dead lock) and are
    honest draws [0, 0];
(h) frozen counts: 24 opening placements; movement-phase legal-move counts after
    the two scripted openings (3 and 1).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

PKG = Path(__file__).resolve().parent
_, G = load_from_dir(PKG)

from games.shax.game import MILLS, POINTS, OUTER, MIDDLE, INNER  # noqa: E402


def pid(t):
    return f"{t[0]},{t[1]}"


def play(seq, st=None):
    st = st or G.initial_state()
    for mv in seq:
        assert mv in G.legal_moves(st), f"illegal scripted move {mv}"
        st = G.apply_move(st, mv)
    return st


def mk(pos, to_move, **kw):
    d = {"pos": pos, "to_move": to_move, "placed": [12, 12], "first_jare": 0,
         "trans_removals": 0, "removing": False, "freeing": False,
         "since_removal": 0, "reps": {}, "dead": False, "winner": None}
    d.update(kw)
    return G.deserialize(d)


# ---- (h) opening: 24 placement moves ---------------------------------------
st0 = G.initial_state()
assert len(G.legal_moves(st0)) == 24
assert G.current_player(st0) == 0

# ---- (a)+(b) mill case: P0 forms the first jare while placing --------------
p0m = ["0,0", "3,0", "6,0"]
p1m = ["6,6", "0,6", "5,5"]
rest = [p for p in POINTS if p not in p0m + p1m]
p0m += rest[0::2][:9]
p1m += rest[1::2][:9]
seq_mill = [x for pair in zip(p0m, p1m) for x in pair]

st = play(seq_mill)
assert len(st.pos) == 24 and st.placed == [12, 12]          # (a) board full
assert sum(1 for v in st.pos.values() if v == 0) == 12      # no removals yet
assert st.first_jare == 0                                    # jare tracked
assert st.to_move == 0 and st.trans_removals == 2            # (b) P0 removes 1st
lm = G.legal_moves(st)
assert sorted(lm) == sorted(p for p in POINTS if st.pos[p] == 1) and len(lm) == 12
st = G.apply_move(st, "6,6")                                 # P0 takes a P1 man
assert st.to_move == 1 and st.trans_removals == 1
lm = G.legal_moves(st)
assert len(lm) == 12 and all(st.pos[p] == 0 for p in lm)
# "0,0" is inside P0's standing mill 0,0-3,0-6,0: still removable (no protection)
assert "0,0" in lm
st = G.apply_move(st, "0,0")                                 # P1 takes from a mill
assert st.to_move == 0 and st.trans_removals == 0            # jare player moves 1st
mv = G.legal_moves(st)
assert sorted(mv) == ["0,3>0,0", "3,0>0,0", "6,3>6,6"]       # (h) frozen: 3 slides
assert all(">" in m for m in mv)

# ---- (c) no-jare case: full board, no mill for either side -----------------
p0 = ([pid(OUTER[i]) for i in range(8) if i % 2 == 0]
      + [pid(INNER[i]) for i in range(8) if i % 2 == 0]
      + [pid(MIDDLE[i]) for i in range(8) if i % 2 == 1])
p1 = [p for p in POINTS if p not in p0]
seq_nomill = [x for pair in zip(p0, p1) for x in pair]
colouring = {p: 0 for p in p0} | {p: 1 for p in p1}
assert all(len({colouring[q] for q in m}) > 1 for m in MILLS)  # truly mill-free

st = play(seq_nomill)
assert st.first_jare is None and len(st.pos) == 24
assert st.to_move == 1 and st.trans_removals == 2            # 2nd placer removes 1st
st = G.apply_move(st, "0,0")                                 # P1 removes a P0 man
assert st.to_move == 0 and st.trans_removals == 1            # P0 removes too
st = G.apply_move(st, "3,0")
assert st.to_move == 1 and st.trans_removals == 0            # 2nd placer moves 1st
assert G.legal_moves(st) == ["0,3>0,0"]                      # (h) frozen: 1 slide

# ---- (d) oodan: forced freeing move, freeing jare captures nothing ---------
st = mk({"0,0": 1, "3,0": 1, "0,3": 1,
         "3,1": 0, "0,6": 0, "1,3": 0, "6,3": 0, "5,3": 0, "4,3": 0, "4,4": 0}, 0)
assert "6,3>6,0" in G.legal_moves(st)
st = G.apply_move(st, "6,3>6,0")            # blocks all three P1 men
assert st.to_move == 0 and st.freeing and not st.removing
frees = sorted(G.legal_moves(st))
assert frees == ["0,6>3,6", "1,3>1,1", "1,3>1,5", "1,3>2,3",
                 "3,1>1,1", "3,1>3,2", "3,1>5,1", "6,0>6,3"]
assert "4,4>3,4" not in frees               # a legal slide that frees nothing
for m in frees:                             # every offered move really frees
    ns = G.apply_move(st, m)
    assert ns.to_move == 1 and G.legal_moves(ns), m
st2 = G.apply_move(st, "6,0>6,3")           # forms jare 6,3-5,3-4,3 while freeing
assert not st2.removing                     # ...but captures nothing (oodan)
assert sum(1 for v in st2.pos.values() if v == 1) == 3
assert st2.to_move == 1
# ---- (e) no flying: the freed 3-man player slides only along a line --------
assert G.legal_moves(st2) == ["3,0>6,0"]    # many empties exist; no flying to them

# ---- (f) reduction to two men wins (via apply_move) ------------------------
st = mk({"0,0": 0, "3,0": 0, "6,3": 0,
         "2,2": 1, "2,3": 1, "2,4": 1, "5,5": 1}, 0)
st = G.apply_move(st, "6,3>6,0")            # completes 0,0-3,0-6,0
assert st.removing and st.to_move == 0
assert sorted(G.legal_moves(st)) == ["2,2", "2,3", "2,4", "5,5"]  # mill men takeable
st = G.apply_move(st, "2,3")                # 4 -> 3 men: game goes on
assert st.winner is None and not G.is_terminal(st)

st = mk({"0,0": 0, "3,0": 0, "6,3": 0, "2,2": 1, "2,3": 1, "5,5": 1}, 0)
st = G.apply_move(st, "6,3>6,0")
st = G.apply_move(st, "5,5")                # 3 -> 2 men: reduction win
assert st.winner == 0 and G.is_terminal(st)
assert G.returns(st) == [1.0, -1.0]

# ---- (g) draw backstops ----------------------------------------------------
# 50-ply no-progress clock
base = {"0,0": 0, "1,1": 0, "2,2": 0, "6,6": 1, "5,5": 1, "4,4": 1}
st = mk(dict(base), 0, since_removal=G.DRAW_PLIES - 1)
st = G.apply_move(st, "0,0>3,0")
assert G.is_terminal(st) and st.winner is None and G.returns(st) == [0.0, 0.0]

# threefold repetition via a real shuttle
st = mk(dict(base), 0)
cycle = ["0,0>3,0", "6,6>3,6", "3,0>0,0", "3,6>6,6"]
for ply in range(40):
    if G.is_terminal(st):
        break
    st = G.apply_move(st, cycle[ply % 4])
assert G.is_terminal(st) and st.winner is None and G.returns(st) == [0.0, 0.0]

# dead lock: blocked player cannot be freed by ANY move -> honest draw
st = mk({"0,0": 1, "3,0": 1, "0,3": 1,
         "3,1": 0, "1,3": 0, "6,0": 0, "0,6": 0, "3,6": 0, "1,1": 0,
         "5,1": 0, "3,2": 0, "1,5": 0, "2,3": 0, "6,6": 0}, 0)
st = G.apply_move(st, "6,6>6,3")            # completes the unopenable cage
assert st.dead and G.is_terminal(st) and st.winner is None
assert G.returns(st) == [0.0, 0.0]

# ---- heuristic contract: a payoff PER SEAT, zero-sum -----------------------
h = G.heuristic(G.initial_state())
assert isinstance(h, list) and len(h) == 2 and h[0] == -h[1] and h[0] == 0.0
h = G.heuristic(mk({"0,0": 0, "1,1": 0, "2,2": 0, "6,6": 1, "5,5": 1,
                    "4,4": 1, "3,5": 0, "5,3": 0}, 0))
assert isinstance(h, list) and len(h) == 2 and h[0] > 0 and h[1] == -h[0]

# ---- random-game termination sanity ---------------------------------------
rng = random.Random(7)
for _ in range(3):
    st = G.initial_state()
    for ply in range(2000):
        if G.is_terminal(st):
            break
        st = G.apply_move(st, rng.choice(G.legal_moves(st)))
    assert G.is_terminal(st)
    assert isinstance(G.returns(st), list) and len(G.returns(st)) == 2

print("shax selftest: all checks passed")
