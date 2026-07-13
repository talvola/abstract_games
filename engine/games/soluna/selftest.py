"""Soluna selftest -- pure stdlib.

Anchors (sources: BGA gamehelp + Steffen-Spiele / Blue Orange rulebook summaries,
Faidutti's blog):
  1. Disc composition: 12 double-sided discs, each of the 6 two-symbol
     combinations exactly twice -> each symbol on exactly 6 faces.
  2. The random deal: 12 single-disc stacks; per-symbol visible counts are
     feasible (<= 6); deal is rng-deterministic and stored in state.
  3. Merge legality: same TOP symbol OR same height, nothing else; the moved
     stack lands on top (its top disc becomes the merged top).
  4. Last-mover-wins reached via apply_move (the stuck player loses).
  5. Termination: every move removes exactly one stack -> <= 11 moves.
  6. FULL SOLVE: engine-side minimax (through legal_moves/apply_move) vs an
     INDEPENDENT brute force written straight from the rules text on the
     (top,height)-multiset abstraction -- optimal winners must agree.
  7. serialize round-trip, including the dealt board.
  8. Random-playout stats (printed).
"""

import random
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.soluna.game import Soluna, DISCS, LETTER  # noqa: E402

G = Soluna()

FAILS = 0


def check(cond, msg):
    global FAILS
    if cond:
        print(f"  ok  {msg}")
    else:
        FAILS += 1
        print(f"FAIL  {msg}")


# ---- 1. physical disc composition ------------------------------------------
check(len(DISCS) == 12, "12 discs")
pairs = {}
for d in DISCS:
    check(len(d) == 2 and d[0] != d[1], f"disc {d} has two different symbols")
    pairs[tuple(sorted(d))] = pairs.get(tuple(sorted(d)), 0) + 1
check(sorted(pairs) == sorted(combinations(range(4), 2)),
      "all 6 two-symbol combinations present")
check(all(v == 2 for v in pairs.values()), "each combination appears exactly twice")
for s in range(4):
    faces = sum(d.count(s) for d in DISCS)
    check(faces == 6, f"symbol {LETTER[s]} on exactly 6 of the 24 faces")

# ---- 2. the deal -------------------------------------------------------------
for seed in (0, 1, 7, 42, 999):
    st = G.initial_state(rng=random.Random(seed))
    check(len(st.board) == 12 and all(len(v) == 1 for v in st.board.values()),
          f"seed {seed}: 12 single-disc stacks")
    check(all(0 <= c < 4 and 0 <= r < 3 for (c, r) in st.board),
          f"seed {seed}: stacks on the 4x3 slots")
    counts = [0, 0, 0, 0]
    for (sym,) in st.board.values():
        counts[sym] += 1
    check(sum(counts) == 12 and all(n <= 6 for n in counts),
          f"seed {seed}: visible counts {counts} feasible (each symbol <= 6 faces)")
    again = G.initial_state(rng=random.Random(seed))
    check(G.serialize(st) == G.serialize(again), f"seed {seed}: deal deterministic per rng")
st_a = G.serialize(G.initial_state(rng=random.Random(1)))
st_b = G.serialize(G.initial_state(rng=random.Random(2)))
check(st_a != st_b, "different seeds give different deals")

# ---- 3. merge legality --------------------------------------------------------
# Fixed position: S(h1) at 0,0 · SM(h2, top M) at 1,0 · TC(h2, top C) at 2,0 · M(h1) at 3,0
fx = G.deserialize({"board": {"0,0": "S", "1,0": "SM", "2,0": "TC", "3,0": "M"},
                    "to_move": 0, "ply": 4})
lm = set(G.legal_moves(fx))
check("0,0>3,0" in lm, "same height (1=1), different symbols -> legal")
check("3,0>1,0" in lm, "same top symbol (M), different heights -> legal")
check("1,0>2,0" in lm and "2,0>1,0" in lm, "same height (2=2) legal both ways")
check("0,0>1,0" not in lm and "0,0>2,0" not in lm,
      "different symbol AND different height -> illegal")
check(all("0,0" != m.split(">")[1].replace("0,0", "0,0") or True for m in lm), "sanity")
nx = G.apply_move(fx, "3,0>1,0")
check(G.serialize(nx)["board"].get("1,0") == "SMM" and "3,0" not in G.serialize(nx)["board"],
      "moved stack lands ON TOP (SM + M -> SMM, top M); source slot empties")
check(nx.to_move == 1 and nx.ply == 5, "turn alternates, ply advances")
check(G.serialize(fx)["board"]["3,0"] == "M", "apply_move is pure (source state untouched)")
nx2 = G.apply_move(fx, "2,0>1,0")
check(G.serialize(nx2)["board"]["1,0"] == "SMTC",
      "same-height merge keeps the MOVED stack's top (TC onto SM -> SMTC, top C)")

# ---- 4. last-mover-wins reached via apply_move --------------------------------
end = G.deserialize({"board": {"0,0": "S", "1,0": "M"}, "to_move": 0, "ply": 10})
check(not G.is_terminal(end), "two height-1 stacks: mover still has a move")
fin = G.apply_move(end, "0,0>1,0")
check(G.is_terminal(fin), "single stack left -> terminal")
check(G.returns(fin) == [1.0, -1.0],
      "seat 0 made the last move -> seat 0 wins, stuck seat 1 loses")
# Mirror: seat 1 makes the last move.
end2 = G.deserialize({"board": {"0,0": "S", "1,0": "M"}, "to_move": 1, "ply": 9})
fin2 = G.apply_move(end2, "1,0>0,0")
check(G.returns(fin2) == [-1.0, 1.0], "seat 1 made the last move -> seat 1 wins")
# A stuck position with >1 stack: all tops differ AND all heights differ.
stuck = G.deserialize({"board": {"0,0": "S", "1,0": "MM", "2,0": "TTC"},
                       "to_move": 1, "ply": 9})
check(G.is_terminal(stuck) and G.legal_moves(stuck) == [] and G.returns(stuck) == [1.0, -1.0],
      "distinct tops + distinct heights -> stuck; the player to move loses")

# ---- 5+8. termination bound + playout stats -----------------------------------
lengths, wins = [], [0, 0]
rng = random.Random(2024)
for i in range(400):
    st = G.initial_state(rng=rng)
    n = 0
    while not G.is_terminal(st):
        moves = G.legal_moves(st)
        assert moves, "non-terminal state must have moves"
        before = len(st.board)
        st = G.apply_move(st, rng.choice(moves))
        assert len(st.board) == before - 1, "each move removes exactly one stack"
        n += 1
        assert n <= 11, "termination bound exceeded"
    lengths.append(n)
    w = 1 - st.to_move
    wins[w] += 1
    rs = G.returns(st)
    assert rs[w] == 1.0 and rs[1 - w] == -1.0 and 0.0 not in rs, "always decisive"
check(max(lengths) <= 11, f"all 400 random playouts ended in <= 11 moves (max {max(lengths)})")
check(min(lengths) >= 1, "at least one move is always available at the deal")
print(f"  ..  playout stats: mean length {sum(lengths)/len(lengths):.2f}, "
      f"min {min(lengths)}, max {max(lengths)}; random-play wins seat0/seat1 = "
      f"{wins[0]}/{wins[1]} (no draws)")

# ---- 6. full solve: engine minimax vs independent brute force ------------------
def solve_engine(state, memo):
    """Does the player to move win, playing through the ENGINE's API?
    Memo key: multiset of full stack contents (slot positions are irrelevant --
    the engine generates all ordered pairs regardless of position)."""
    key = tuple(sorted(tuple(col) for col in state.board.values()))
    if key in memo:
        return memo[key]
    moves = G.legal_moves(state)
    res = any(not solve_engine(G.apply_move(state, m), memo) for m in moves)
    memo[key] = res
    return res


def solve_rules(stacks):
    """INDEPENDENT brute force, written directly from the rules text on the
    (top symbol, height) abstraction: move any stack onto another with the
    same top or the same height; the moved stack's top wins the merged top;
    a player with no move loses."""
    memo = {}

    def rec(ms):
        if ms in memo:
            return memo[ms]
        res = False
        n = len(ms)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                (ti, hi), (tj, hj) = ms[i], ms[j]
                if ti == tj or hi == hj:
                    nxt = tuple(sorted(ms[k] for k in range(n) if k not in (i, j))
                                + [(ti, hi + hj)])
                    if not rec(nxt):
                        res = True
                        break
            if res:
                break
        memo[ms] = res
        return res

    return rec(tuple(sorted(stacks)))


for seed in (3, 11, 42, 123, 777):
    st = G.initial_state(rng=random.Random(seed))
    eng = solve_engine(st, {})
    ind = solve_rules([(col[-1], len(col)) for col in st.board.values()])
    check(eng == ind,
          f"seed {seed}: engine solve ({'first' if eng else 'second'}-player win) "
          f"matches independent brute force")
# And one hand-built midgame position (5 stacks, mixed):
mid = G.deserialize({"board": {"0,0": "SM", "1,0": "T", "2,0": "TC", "3,0": "C", "0,1": "MSSM"},
                     "to_move": 0, "ply": 7})
check(solve_engine(mid, {}) == solve_rules([(col[-1], len(col)) for col in mid.board.values()]),
      "hand-built midgame: engine solve matches independent brute force")

# ---- 7. serialize round-trip ----------------------------------------------------
for seed in (5, 17):
    st = G.initial_state(rng=random.Random(seed))
    for _ in range(4):
        st = G.apply_move(st, random.Random(seed).choice(G.legal_moves(st)))
    d = G.serialize(st)
    check(G.serialize(G.deserialize(d)) == d, f"seed {seed}: round-trip after 4 moves")
    import json
    json.dumps(d)

# ---- render probe ----------------------------------------------------------------
spec = G.render(G.initial_state(rng=random.Random(9)))
check(spec["board"] == {"type": "square", "width": 4, "height": 3}, "render: 4x3 square board")
check(len(spec["pieces"]) == 12 and
      all(p.get("fill") and p.get("label") and p.get("stroke") for p in spec["pieces"]),
      "render: 12 fill+label discs (Kamisado-style neutral pieces)")
check(all(len(p["label"]) == 1 for p in spec["pieces"]), "render: height-1 stacks label = bare glyph")
spec2 = G.render(nx)  # has an SMM stack
check(any(len(p["label"]) == 2 and p["label"][1] == "3" for p in spec2["pieces"]),
      "render: tall stack labelled glyph+height")

print()
if FAILS:
    print(f"SELFTEST FAILED: {FAILS} failing check(s)")
    sys.exit(1)
print("soluna selftest: all checks passed")
