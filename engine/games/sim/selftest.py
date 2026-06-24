"""Pure-stdlib selftest for Sim (the Ramsey K6 graph game). Run:

    cd engine && PYTHONPATH=. python3 games/sim/selftest.py
"""

from __future__ import annotations

import json
import random

from games.sim.game import Sim, SimState, ALL_EDGES, edge_id, parse_edge

G = Sim()


def test_opening_move_count():
    # K6 has exactly 15 edges; all are uncoloured and legal at the opening.
    s = G.initial_state()
    lm = G.legal_moves(s)
    assert len(lm) == 15, f"opening should have 15 legal edges, got {len(lm)}"
    assert len(ALL_EDGES) == 15
    assert len(set(lm)) == 15, "moves must be unique"
    # Every move parses to a valid i<j vertex pair and round-trips its id.
    for mv in lm:
        i, j = parse_edge(mv)
        assert 0 <= i < j <= 5
        assert edge_id(i, j) == mv
    assert G.current_player(s) == 0


def test_completing_own_triangle_loses():
    # Red (player 0) owns edges (0,1) and (0,2). It is Red's turn; colouring
    # (1,2) completes the Red triangle on {0,1,2} -> Red (the mover) LOSES.
    s = SimState(colors={(0, 1): 0, (0, 2): 0}, to_move=0)
    assert s.loser is None
    assert not G.is_terminal(s)
    mv = edge_id(1, 2)
    assert mv in G.legal_moves(s)
    s2 = G.apply_move(s, mv)
    assert s2.loser == 0, "mover who completes own-colour triangle must be the loser"
    assert G.is_terminal(s2)
    # Loser = player 0 -> player 1 wins.
    assert G.returns(s2) == [-1.0, 1.0]


def test_no_loss_from_opponent_triangle():
    # Blue (player 1) owns (0,1) and (0,2). It is Red's (player 0) turn. Colouring
    # (1,2) -- which would CLOSE a BLUE triangle on {0,1,2} -- must NOT make Red
    # (the mover) lose: you can only lose by your OWN colour. Here no Red triangle
    # is formed, so the game continues with nobody losing.
    s = SimState(colors={(0, 1): 1, (0, 2): 1}, to_move=0)
    s2 = G.apply_move(s, edge_id(1, 2))
    assert s2.loser is None, "completing the OPPONENT's triangle must not lose"
    assert not G.is_terminal(s2)


def test_loss_only_triggers_via_own_third_edge():
    # Exhaustive: for every reachable single move from a position, the only way a
    # mover can become the loser is by completing a triangle in their OWN colour.
    # Build: Red owns (0,1),(0,2); Blue owns (3,4),(3,5). Red to move. The unique
    # losing move for Red is (1,2). No other Red move loses; Red can NEVER lose by
    # a Blue triangle.
    s = SimState(colors={(0, 1): 0, (0, 2): 0, (3, 4): 1, (3, 5): 1}, to_move=0)
    losing = []
    for mv in G.legal_moves(s):
        s2 = G.apply_move(s, mv)
        if s2.loser is not None:
            assert s2.loser == 0, "the mover (Red) can only lose by a RED triangle"
            losing.append(mv)
    assert losing == [edge_id(1, 2)], f"only (1,2) should lose for Red, got {losing}"


def test_full_playout_always_decisive():
    # Ramsey R(3,3)=6 => no K6 game can be a draw. Play many random games; each
    # MUST terminate with a loser (and so a [+1,-1] payoff), never a draw, in
    # <= 15 plies.
    rng = random.Random(20240624)
    for trial in range(400):
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            mv = rng.choice(G.legal_moves(s))
            s = G.apply_move(s, mv)
            steps += 1
            assert steps <= 15, "K6 must resolve within 15 plies"
        assert s.loser is not None, "a finished Sim game must have a loser (no draws)"
        r = G.returns(s)
        assert sorted(r) == [-1.0, 1.0], f"payoff must be win/loss, got {r}"
        assert r[s.loser] == -1.0 and r[1 - s.loser] == 1.0


def test_serialize_roundtrip():
    rng = random.Random(7)
    s = G.initial_state()
    for _ in range(6):
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert G.serialize(s2) == d
    json.dumps(d)  # must be JSON-able


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("sim selftest: all tests passed")


if __name__ == "__main__":
    main()
