"""Boom & Zoom selftest — anchored on the AG#21 article (Ploog, pp. 21-25/29).

Anchors, all from the article's diagrams/text:
 1. Opening position + exact opening move count (38, hand-derived).
 2. Boom range example (p.22): a 3-stack shoots a 2-stack at distance 3,
    removing exactly one counter; a 2-stack cannot shoot that far.
 3. Corner bear-off clarification (p.22/23 diagram): W3 b6 + W3 f6 vs
    B1 b8/d8/f8 — the right piece has exactly one bear-off (diagonally
    through the corner past h8), the left piece none.
 4. The White-timer table (p.23): minimal bear-off move counts for a lone
    1/2/3-stack from every rank — all 24 entries, via BFS over real moves.
 5. The shoot-out asymmetry (p.23): 3-stack vs 3-stack at range 2 — whoever
    shoots second ends a singleton and cannot answer.
 6. Problem "White 6 : Black 0" + its printed solution: the key capture
    f4:f5, the full 9:8 White race win, and the 9:9 draw line if White races
    immediately.  (The magazine swapped the two problem diagrams' captions;
    this position is the one consistent with the printed solution AND with
    exact counter accounting: W 3 on board + 6 scored + 3 shot = 12,
    B 11 on board + 0 + 1 = 12.)
 7. Problem "White 0 : Black 5": key capture b4:b6 and the solution's side
    lines (f6:h6 counter-boom, c4-f7, the backwards f6-g7 + g7:h6).
 8. Random-game invariants: termination, counter conservation, monotone
    scores, honest result shapes.  Plus a heuristic-shape MCTS probe.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

MAN, GAME = load_from_dir(Path(__file__).resolve().parent)
W, B = 0, 1


def mk(stacks, to_move=W, scores=(0, 0)):
    """Build a state from {(c,r): (owner, h)}."""
    st = GAME.initial_state()
    st.board = dict(stacks)
    st.scores = list(scores)
    st.to_move = to_move
    return st


def moves_from(st, cell):
    pre = f"{cell[0]},{cell[1]}>"
    return [m for m in GAME.legal_moves(st) if m.startswith(pre)]


def play(st, seq):
    for mv in seq:
        assert mv in GAME.legal_moves(st), f"{mv} not legal; legal={GAME.legal_moves(st)}"
        st = GAME.apply_move(st, mv)
    return st


# 1 ── opening ---------------------------------------------------------------
st = GAME.initial_state()
assert st.board == {
    **{(c, 1): (W, 3) for c in (3, 4, 5, 6)},
    **{(c, 8): (B, 3) for c in (3, 4, 5, 6)},
}
assert not GAME.is_terminal(st)
ms = GAME.legal_moves(st)
assert len(ms) == len(set(ms)) == 38, len(ms)   # 10+9+9+10, hand-derived
assert all(">" in m for m in ms)

# 2 ── boom range example (p.22) --------------------------------------------
st = mk({(2, 4): (W, 3), (5, 4): (B, 2)})
assert "2,4>5,4" in GAME.legal_moves(st)          # range 3 = height
s2 = GAME.apply_move(st, "2,4>5,4")
assert s2.board[(5, 4)] == (B, 1)                 # one counter removed
assert s2.board[(2, 4)] == (W, 3)                 # shooter stays put
assert GAME.describe_move(st, "2,4>5,4") == "b4:e4 (2→1)"
st = mk({(2, 4): (W, 2), (5, 4): (B, 2)})
assert "2,4>5,4" not in GAME.legal_moves(st)      # 2-stack range is 2

# 3 ── corner bear-off clarification (p.22/23) ------------------------------
st = mk({(2, 6): (W, 3), (6, 6): (W, 3),
         (2, 8): (B, 1), (4, 8): (B, 1), (6, 8): (B, 1)})
right = moves_from(st, (6, 6))
exits = [m for m in right if m.endswith(",9")]
assert exits == ["6,6>9,9"], exits                # only diagonally past h8
left = moves_from(st, (2, 6))
assert not any(m.endswith(",9") for m in left)    # left piece cannot bear off
assert "6,6>6,8" in right                          # ...but can boom f8
s2 = GAME.apply_move(st, "6,6>9,9")               # bear off through the corner
assert (6, 6) not in s2.board and s2.scores[W] == 3
assert GAME.describe_move(st, "6,6>9,9") == "f6-off (+3)"

# corner exit exists from the a-file too (10-square zone), never further out
st = mk({(1, 8): (W, 1)})
assert set(moves_from(st, (1, 8))) >= {"1,8>0,9", "1,8>1,9", "1,8>2,9"}
st = mk({(8, 6): (W, 3)})                          # h6: up-right d=3 -> col 11: out
assert "8,6>11,9" not in moves_from(st, (8, 6))
# a stack may never enter its OWN side's virtual row
st = mk({(3, 2): (W, 3)})
assert not any(m.endswith(",0") for m in moves_from(st, (3, 2)))

# 4 ── the White-timer table (p.23) -----------------------------------------
TABLE = {3: [3, 3, 2, 2, 2, 1, 1, 1],
         2: [4, 4, 3, 3, 2, 2, 1, 1],
         1: [8, 7, 6, 5, 4, 3, 2, 1]}
for h, row in TABLE.items():
    for r in range(1, 9):
        # BFS over real legal moves: lone White h-stack, minimal moves to exit
        frontier, seen, depth, done = {(4, r)}, {(4, r)}, 0, None
        while done is None:
            depth += 1
            nxt = set()
            for cell in frontier:
                for m in moves_from(mk({cell: (W, h)}), cell):
                    tc, tr = (int(v) for v in m.split(">")[1].split(","))
                    if tr == 9:
                        done = depth
                        break
                    if (tc, tr) not in seen:
                        seen.add((tc, tr))
                        nxt.add((tc, tr))
                if done:
                    break
            frontier = nxt
        assert done == row[r - 1], (h, r, done)

# 5 ── shoot-out asymmetry (p.23) -------------------------------------------
st = mk({(3, 3): (W, 3), (5, 3): (B, 3)})
st = play(st, ["3,3>5,3", "5,3>3,3", "3,3>5,3"])   # W first: B 3->2->1, W 3->2
assert st.board[(3, 3)] == (W, 2) and st.board[(5, 3)] == (B, 1)
assert "5,3>3,3" not in GAME.legal_moves(st)       # the singleton is outranged

# 6 ── Problem "White 6, Black 0" + printed solution ------------------------
PA = {(4, 6): (W, 2), (6, 4): (W, 1),
      (2, 5): (B, 3), (6, 5): (B, 3), (8, 3): (B, 2), (4, 2): (B, 3)}
st = mk(PA, scores=(6, 0))
assert "6,4>6,5" in GAME.legal_moves(st)           # the key capture f4:f5
s2 = GAME.apply_move(st, "6,4>6,5")
assert s2.board[(6, 5)] == (B, 2)

# the winning race after 1. f4:f5 — White 9 : Black 8
end = play(s2, [
    "4,2>4,0",              # 1... d2-off (+3)
    "4,6>4,8", "2,5>2,2",   # 2. d6-d8   b5-b2
    "4,8>4,9", "2,2>2,0",   # 3. d8-off (+2)  b2-off (+3)
    "6,4>7,5", "6,5>6,3",   # 4. f4-g5   f5-f3
    "7,5>7,6", "6,3>6,1",   # 5. g5-g6   f3-f1
    "7,6>7,7", "6,1>6,0",   # 6. g6-g7   f1-off (+2)
    "7,7>7,8", "8,3>8,1",   # 7. g7-g8   h3-h1
    "7,8>7,9",              # 8. g8-off (+1) — White's board is empty: game over
])
assert GAME.is_terminal(end) and end.scores == [9, 8]
assert end.winner == W and GAME.returns(end) == [1, -1]

# the article's draw line: White races immediately, Black answers f5-c2 → 9:9
end = play(mk(PA, scores=(6, 0)), [
    "4,6>4,8", "6,5>3,2",   # 1. d6-d8   f5-c2
    "4,8>4,9", "3,2>3,0",   # 2. d8-off  c2-off (+3)
    "6,4>7,5", "4,2>4,0",   # 3. f4-g5   d2-off (+3)
    "7,5>7,6", "2,5>2,2",   # 4. g5-g6   b5-b2
    "7,6>7,7", "2,2>2,0",   # 5. g6-g7   b2-off (+3)
    "7,7>7,8", "8,3>8,1",   # 6. g7-g8   h3-h1
    "7,8>7,9",              # 7. g8-off — 9:9
])
assert GAME.is_terminal(end) and end.scores == [9, 9]
assert end.winner is None and GAME.returns(end) == [0, 0]   # honest draw

# 7 ── Problem "White 0, Black 5" key lines ---------------------------------
PB = {(4, 7): (W, 2), (8, 6): (W, 2), (2, 4): (W, 3), (3, 4): (W, 3),
      (2, 6): (B, 3), (6, 6): (B, 2)}
st = mk(PB, scores=(0, 5))
assert "2,4>2,6" in GAME.legal_moves(st)           # 1. b4:b6
s2 = GAME.apply_move(st, "2,4>2,6")
assert s2.board[(2, 6)] == (B, 2)
s2 = play(s2, ["6,6>8,6",                          # 1... f6:h6 (W h6 2->1)
               "2,4>2,6",                          # 2. b4:b6 — black singleton
               "2,6>3,5"])                         # 2... b6-c5 (the singleton runs)
assert s2.board[(8, 6)] == (W, 1) and s2.board[(3, 5)] == (B, 1)
assert "3,4>6,7" in GAME.legal_moves(s2)           # 3. c4-f7 "is a white win"
# side line: 1. h6:f6 f6-g7! (backwards) corners White's edge piece: g7:h6
s3 = play(mk(PB, scores=(0, 5)),
          ["8,6>6,6", "6,6>7,7", "4,7>4,8", "7,7>8,6"])
assert s3.board[(8, 6)] == (W, 1)                  # h6 shot by the g7 singleton

# 8 ── random-game invariants + heuristic probe -----------------------------
for seed in range(25):
    rng = random.Random(seed)
    st = GAME.initial_state()
    prev_total = [12, 12]
    plies = 0
    while not GAME.is_terminal(st):
        mv = rng.choice(GAME.legal_moves(st))
        st = GAME.apply_move(st, mv)
        plies += 1
        assert plies < 2600, "no termination"
        on = [0, 0]
        for (o, h) in st.board.values():
            assert 1 <= h <= 3
            on[o] += h
        for p in (W, B):
            total = on[p] + st.scores[p]
            assert total <= prev_total[p] <= 12     # counters only ever leave
            prev_total[p] = total
    r = GAME.returns(st)
    assert r in ([1, -1], [-1, 1], [0, 0])
    if st.winner is not None:
        assert st.scores[st.winner] == max(st.scores)
    data = GAME.serialize(st)
    assert GAME.serialize(GAME.deserialize(data)) == data

hv = GAME.heuristic(GAME.initial_state())
assert isinstance(hv, list) and len(hv) == 2 and abs(hv[0] + hv[1]) < 1e-9

from agp.mcts import MCTSBot  # noqa: E402
mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(GAME, GAME.initial_state())
assert mv in GAME.legal_moves(GAME.initial_state())

print("boom_zoom selftest: all anchors OK")
