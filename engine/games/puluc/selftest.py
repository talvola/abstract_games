"""Pure-stdlib selftest for Puluc (Bul / Boolik).

Anchors: the corn-dice value mapping (blacks 1-4, all-plain = 5); entry
landing spaces from both ends; capture-and-carry (pile beneath, direction
reversal); recapture of a whole pile with liberation of friendly prisoners;
bear-off killing prisoners and returning friendly pieces to hand; a free
piece's completed run returning to hand; own-pile blocking; pass when fully
blocked; win by elimination reached VIA apply_move; ply-cap = honest draw
[0,0]; serialize round-trip; determinism under a fixed seed; heuristic shape
(list of 2, exercised through MCTSBot with max_rollout=4); seeded random
playouts to a terminal with conservation invariants, on all three track
lengths.

Run: PYTHONPATH=. python3 games/puluc/selftest.py
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.mcts import MCTSBot
from games.puluc.game import Puluc, PulucState, PIECES, PLY_CAP, TRACKS


class FixedBits(random.Random):
    """rng whose randint(0,1) yields a forced bit sequence (kernel faces)."""

    def __new__(cls, *a, **k):
        return super().__new__(cls)

    def __init__(self, bits):
        super().__init__()
        self._bits = list(bits)
        self._i = 0

    def randint(self, a, b):
        v = self._bits[self._i % len(self._bits)]
        self._i += 1
        return v


G = Puluc()


def mk(n=9, piles=None, hand=(0, 0), roll=1, to_move=0, ply=0):
    track = [[] for _ in range(n)]
    for i, pile in (piles or {}).items():
        track[i] = list(pile)
    return PulucState(track=track, hand=list(hand), roll=roll,
                      to_move=to_move, ply=ply, winner=None, n=n)


def alive(s, pl):
    return s.hand[pl] + sum(pile.count(pl) for pile in s.track)


# -- 1. dice mapping ---------------------------------------------------------
for bits, want in [((1, 0, 0, 0), 1), ((1, 1, 0, 0), 2), ((1, 0, 1, 1), 3),
                   ((1, 1, 1, 1), 4), ((0, 0, 0, 0), 5)]:
    got = Puluc._roll(FixedBits(bits))
    assert got == want, f"dice {bits} -> {got}, want {want}"
seen = {Puluc._roll(random.Random(seed)) for seed in range(400)}
assert seen == {1, 2, 3, 4, 5}, f"roll support {seen}"

# -- 2. entry landing spaces from both ends ---------------------------------
s = G.initial_state(rng=FixedBits((1, 1, 1, 0)))  # first roll = 3
assert s.roll == 3 and s.to_move == 0
assert G.legal_moves(s) == ["0,0>3,0"], G.legal_moves(s)   # index 2 = cell 3
s1 = G.apply_move(s, "0,0>3,0", rng=FixedBits((1, 1, 1, 0)))  # Blue rolls 3
assert s1.track[2] == [0] and s1.hand[0] == 4 and s1.to_move == 1
assert "10,0>7,0" in G.legal_moves(s1)                     # index 9-3=6 = cell 7
s2 = G.apply_move(s1, "10,0>7,0", rng=FixedBits((1, 0, 0, 0)))
assert s2.track[6] == [1] and s2.hand[1] == 4

# -- 3. capture and carry (reversal) ----------------------------------------
s = mk(piles={2: [0], 4: [1]}, hand=(4, 4), roll=2, to_move=0)
s = G.apply_move(s, "3,0>5,0", rng=FixedBits((1, 1, 0, 0)))
assert s.track[2] == [] and s.track[4] == [1, 0], s.track  # enemy BENEATH
assert s.to_move == 1
# the carrier now heads HOME (leftward for Red): from index 4 with roll 3 -> 1
s = mk(piles={4: [1, 0]}, hand=(0, 4), roll=3, to_move=0)
assert G.legal_moves(s) == ["5,0>2,0"], G.legal_moves(s)
s = G.apply_move(s, "5,0>2,0")
assert s.track[1] == [1, 0]

# -- 4. bear-off: prisoner killed, carrier back to hand ---------------------
s = mk(piles={1: [1, 0]}, hand=(4, 4), roll=2, to_move=0)
assert G.legal_moves(s) == ["2,0>0,0"]
s = G.apply_move(s, "2,0>0,0")
assert s.hand[0] == 5 and s.track[1] == []
assert alive(s, 1) == 4 and s.winner is None               # one Blue killed

# -- 5. recapture + liberation ----------------------------------------------
# Blue carrier at index 3 holds a Red prisoner; Red single at 1 lands on it.
s = mk(piles={3: [0, 1], 1: [0]}, hand=(3, 4), roll=2, to_move=0)
s = G.apply_move(s, "2,0>4,0")
assert s.track[3] == [0, 1, 0], s.track     # whole pile beneath, Red on top
# Red bears the pile off: the Blue piece dies, BOTH Red pieces come home.
s = mk(piles={3: [0, 1, 0]}, hand=(3, 4), roll=4, to_move=0)
assert G.legal_moves(s) == ["4,0>0,0"]
s = G.apply_move(s, "4,0>0,0")
assert s.hand[0] == 5 and alive(s, 1) == 4, (s.hand, alive(s, 1))

# -- 6. free run returns to hand (no kill) ----------------------------------
s = mk(piles={6: [0]}, hand=(0, 5), roll=4, to_move=0)
assert G.legal_moves(s) == ["7,0>10,0"]     # 6+4 = 10 >= 9 -> off at far end
s = G.apply_move(s, "7,0>10,0")
assert s.hand[0] == 1 and alive(s, 1) == 5
# mirrored for Blue: index 2 with roll 3 -> -1 -> off at Red's end
s = mk(piles={2: [1]}, hand=(5, 0), roll=3, to_move=1)
assert G.legal_moves(s) == ["3,0>0,0"]
s = G.apply_move(s, "3,0>0,0")
assert s.hand[1] == 1

# -- 7. own-pile blocking ----------------------------------------------------
s = mk(piles={2: [0], 4: [0]}, hand=(3, 5), roll=2, to_move=0)
moves = G.legal_moves(s)
assert "3,0>5,0" not in moves               # own piece 2 ahead
assert "0,0>2,0" in moves and "5,0>7,0" in moves
# entry blocked too: own piece on the landing space
s = mk(piles={1: [0]}, hand=(4, 5), roll=2, to_move=0)
assert "0,0>2,0" not in G.legal_moves(s)

# -- 8. pass when fully blocked ---------------------------------------------
# Red free piece at 5 (dest 7 = own carrier); Red carrier at 7 (dest 5 = own).
s = mk(piles={5: [0], 7: [1, 0]}, hand=(0, 4), roll=2, to_move=0)
assert G.legal_moves(s) == ["pass"]
s2 = G.apply_move(s, "pass", rng=FixedBits((1, 0, 0, 0)))
assert s2.to_move == 1 and s2.roll == 1
assert G.serialize(s2)["track"] == G.serialize(s)["track"]

# -- 9. win by elimination, via apply_move ----------------------------------
s = mk(piles={1: [1, 0]}, hand=(4, 0), roll=3, to_move=0)  # last Blue = prisoner
assert alive(s, 1) == 1
s = G.apply_move(s, "2,0>0,0")
assert s.winner == 0 and G.is_terminal(s)
assert G.returns(s) == [1.0, -1.0]
assert G.legal_moves(s) == []
# and the mirrored Blue win
s = mk(piles={7: [0, 1]}, hand=(0, 4), roll=2, to_move=1)
s = G.apply_move(s, "8,0>10,0")
assert s.winner == 1 and G.returns(s) == [-1.0, 1.0]

# -- 10. ply cap -> honest draw ---------------------------------------------
s = mk(piles={0: [0], 8: [1]}, hand=(4, 4), roll=1, to_move=0,
       ply=PLY_CAP - 1)
s = G.apply_move(s, "1,0>2,0")
assert s.winner == "draw" and G.is_terminal(s)
assert G.returns(s) == [0.0, 0.0]

# -- 11. serialize round-trip ------------------------------------------------
for st in (G.initial_state(rng=random.Random(7)),
           mk(piles={3: [0, 1, 0], 6: [1]}, hand=(1, 2), roll=5, to_move=1)):
    d = G.serialize(st)
    assert json.dumps(d) == json.dumps(G.serialize(G.deserialize(d)))

# -- 12. determinism under a fixed seed --------------------------------------
def transcript(seed):
    rng = random.Random(seed)
    pick = random.Random(seed + 1)
    s = G.initial_state(rng=rng)
    out = []
    while not G.is_terminal(s) and s.ply < 400:
        mv = pick.choice(G.legal_moves(s))
        out.append(mv)
        s = G.apply_move(s, mv, rng=rng)
    out.append(json.dumps(G.serialize(s)))
    return out

assert transcript(42) == transcript(42)

# -- 13. heuristic shape (forced through the MCTS cutoff) --------------------
h = G.heuristic(mk(piles={4: [1, 0]}, hand=(4, 3)))
assert isinstance(h, list) and len(h) == 2
assert all(-1.0 <= x <= 1.0 for x in h) and abs(h[0] + h[1]) < 1e-9
mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(
    G, G.initial_state(rng=random.Random(3)))
assert mv in G.legal_moves(G.initial_state(rng=random.Random(3)))

# -- 14. random playouts: termination + invariants ---------------------------
for n in TRACKS:
    decisive = 0
    games = 120 if n == 9 else 40
    for seed in range(games):
        rng = random.Random(1000 * n + seed)
        pick = random.Random(2000 * n + seed)
        s = G.initial_state(options={"track": n}, rng=rng)
        prev_alive = [PIECES, PIECES]
        while not G.is_terminal(s):
            mv = pick.choice(G.legal_moves(s))
            s = G.apply_move(s, mv, rng=rng)
            a = [alive(s, 0), alive(s, 1)]
            for pl in (0, 1):
                assert 0 <= a[pl] <= PIECES
                assert a[pl] <= prev_alive[pl], "a dead piece came back"
                assert s.hand[pl] >= 0
            prev_alive = a
            for pile in s.track:
                if len(pile) > 1:   # every carrier pile holds >= 1 enemy
                    assert any(o != pile[-1] for o in pile), pile
            assert s.ply <= PLY_CAP
        assert s.winner in (0, 1, "draw")
        if s.winner in (0, 1):
            decisive += 1
            assert alive(s, 1 - s.winner) == 0
            assert G.returns(s)[s.winner] == 1.0
    assert decisive > 0, f"no decisive game on track {n}"

print("puluc selftest: all tests passed")
