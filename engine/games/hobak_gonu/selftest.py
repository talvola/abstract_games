"""Selftest for Hobak Gonu — frozen board graph + rule probes + FULL SOLVE.

The state space is tiny (both variants together < 20k reachable positions),
so this selftest re-runs the complete solve THROUGH the game class on every
run and asserts the frozen results:

    invasion="closed" (default): reachable 2,278  edges  6,518
        WIN(to-move) 1,062 / LOSS 726 / DRAW(cycle-bound) 490
        ROOT = DRAW   (max forced-win depth 20 plies)
    invasion="trap":             reachable 15,972 edges 52,878
        WIN(to-move) 1,608 / LOSS 1,134 / DRAW 13,230
        ROOT = DRAW   (max forced-win depth 22 plies)

Cycle-bound positions count as draws, matching the in-game rule (first
positional repetition = draw).  ROOT = DRAW agrees with namu.wiki's claim
that Hobak Gonu has no forced win ("without mistakes the game continues
forever").  Pure stdlib, runs in a couple of seconds.
"""

from __future__ import annotations

import random
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.hobak_gonu.game import (  # noqa: E402
    ADJ, CIRCLE, EDGES, H0, H1, HGState, HobakGonu, POINTS,
)


def state(black, white, to_move, variant="closed"):
    """Hand-built position (fresh history => repetition rule not binding)."""
    pos = {c: 0 for c in black}
    pos.update({c: 1 for c in white})
    return HGState(pos=pos, to_move=to_move, variant=variant)


def solve(g, variant):
    """Forward BFS + retrograde win/loss over the full reachable graph."""
    root_state = g.initial_state({"invasion": variant})
    key = lambda st: (tuple(sorted((p, o) for p, o in st.pos.items())), st.to_move)
    unkey = lambda k: state([p for p, o in k[0] if o == 0],
                            [p for p, o in k[0] if o == 1], k[1], variant)
    root = key(root_state)
    succs = {}
    q = deque([root])
    n_edges = 0
    seen = {root}
    while q:
        k = q.popleft()
        st = unkey(k)
        ms = [key(g.apply_move(st, m)) for m in g.legal_moves(st)]
        succs[k] = ms
        n_edges += len(ms)
        for t in ms:
            if t not in seen:
                seen.add(t)
                q.append(t)
    preds = {k: [] for k in succs}
    for k, ms in succs.items():
        for t in ms:
            preds[t].append(k)
    val, dist = {}, {}
    deg = {k: len(ms) for k, ms in succs.items()}
    q = deque(k for k, ms in succs.items() if not ms)
    for k in q:
        val[k], dist[k] = "LOSS", 0
    while q:
        k = q.popleft()
        for p in preds[k]:
            if p in val:
                continue
            if val[k] == "LOSS":
                val[p], dist[p] = "WIN", dist[k] + 1
                q.append(p)
            else:
                deg[p] -= 1
                if deg[p] == 0:
                    val[p] = "LOSS"
                    dist[p] = 1 + max(dist[t] for t in succs[p])
                    q.append(p)
    nwin = sum(1 for v in val.values() if v == "WIN")
    nloss = sum(1 for v in val.values() if v == "LOSS")
    ndraw = len(succs) - nwin - nloss
    rootval = val.get(root, "DRAW")
    maxdist = max(dist.values()) if dist else 0
    return len(succs), n_edges, nwin, nloss, ndraw, rootval, maxdist


def run():
    g = HobakGonu()

    # --- frozen board graph: 11 points, 14 edges (Ludii Ho-Bag Gonu) ----
    assert len(POINTS) == 11
    norm = {frozenset(e) for e in EDGES}
    assert len(norm) == 14
    expect = {
        frozenset({(0, 4), (2, 4)}), frozenset({(2, 4), (4, 4)}),
        frozenset({(0, 0), (2, 0)}), frozenset({(2, 0), (4, 0)}),
        frozenset({(2, 4), (2, 3)}), frozenset({(2, 0), (2, 1)}),
        frozenset({(2, 3), (1, 2)}), frozenset({(1, 2), (2, 1)}),
        frozenset({(2, 1), (3, 2)}), frozenset({(3, 2), (2, 3)}),
        frozenset({(2, 2), (2, 3)}), frozenset({(2, 2), (1, 2)}),
        frozenset({(2, 2), (3, 2)}), frozenset({(2, 2), (2, 1)}),
    }
    assert norm == expect, norm ^ expect
    assert all(len(ADJ[p]) in (1, 3, 4) for p in POINTS)
    assert len(ADJ[(2, 2)]) == 4 and len(ADJ[(0, 4)]) == 1

    # --- opening: both first moves are forced funnels-out ---------------
    s0 = g.initial_state()
    assert g.current_player(s0) == 0 and not g.is_terminal(s0)
    assert g.legal_moves(s0) == ["2,4>2,3"], g.legal_moves(s0)
    s1 = g.apply_move(s0, "2,4>2,3")
    assert g.legal_moves(s1) == ["2,0>2,1"], g.legal_moves(s1)

    # --- movement restrictions (default: closed) ------------------------
    # endpoint is exit-only: home middle may NOT slide to an empty endpoint
    s = state(black=[(2, 4), (0, 4)], white=[(2, 0), (0, 0)], to_move=0)
    ms = g.legal_moves(s)
    assert "2,4>4,4" not in ms and "2,4>2,3" in ms, ms
    # funnel: endpoint -> own middle when the middle is empty
    s = state(black=[(0, 4), (4, 4)], white=[(2, 0)], to_move=0)
    ms = g.legal_moves(s)
    assert sorted(ms) == ["0,4>2,4", "4,4>2,4"], ms
    # no re-entry: circle piece may not step back onto its own home middle
    s = state(black=[(2, 3)], white=[(2, 0)], to_move=0)
    ms = g.legal_moves(s)
    assert "2,3>2,4" not in ms and "2,3>2,2" in ms, ms
    # closed: circle piece may not enter the opponent's home middle
    s = state(black=[(2, 1)], white=[(0, 0)], to_move=0)
    assert "2,1>2,0" not in g.legal_moves(s)
    # namu footnote: a home piece beside an EMPTY endpoint, exit corked,
    # counts as fully blocked
    s = state(black=[(2, 4)], white=[(2, 3)], to_move=0)
    assert g._moves_for(s, 0) == [], g._moves_for(s, 0)

    # --- trap variant ----------------------------------------------------
    s = state(black=[(2, 1)], white=[(0, 0)], to_move=0, variant="trap")
    ms = g.legal_moves(s)
    assert "2,1>2,0" in ms, ms                       # may enter enemy middle
    s3 = state(black=[(2, 0)], white=[(1, 2)], to_move=0, variant="trap")
    ms = g.legal_moves(s3)
    assert sorted(ms) == ["2,0>0,0", "2,0>4,0"], ms  # inside: row only, no exit
    s5 = state(black=[(0, 0)], white=[(1, 2)], to_move=0, variant="trap")
    assert g.legal_moves(s5) == ["0,0>2,0"]          # may shuffle back to middle

    # --- blockade win reached via apply_move (closed, solver line) ------
    line = ["2,4>2,3", "2,0>2,1", "0,4>2,4", "2,1>1,2", "2,3>3,2",
            "1,2>2,2", "2,4>2,3", "0,0>2,0", "4,4>2,4", "2,0>2,1",
            "2,3>1,2", "4,0>2,0", "2,4>2,3"]
    s = g.initial_state()
    for m in line:
        assert not g.is_terminal(s)
        assert m in g.legal_moves(s), (m, g.legal_moves(s))
        s = g.apply_move(s, m)
    assert g.is_terminal(s) and s.winner == 0, (s.winner, s.drawn)
    assert g.returns(s) == [1.0, -1.0]
    # the blocked side even has an empty own-home endpoint next to a piece
    assert s.pos.get((2, 0)) == 1 and (0, 0) not in s.pos

    # --- blockade win, trap variant (mutual-invasion race, solver line) -
    line = ["2,4>2,3", "2,0>2,1", "2,3>1,2", "2,1>3,2", "1,2>2,1",
            "3,2>2,3", "2,1>2,0", "2,3>2,4"]
    s = g.initial_state({"invasion": "trap"})
    for m in line:
        assert m in g.legal_moves(s), (m, g.legal_moves(s))
        s = g.apply_move(s, m)
    assert g.is_terminal(s) and s.winner == 1
    assert g.returns(s) == [-1.0, 1.0]

    # --- repetition draw -------------------------------------------------
    # after B s->w->s and W n->e->n the position after ply 2 recurs at ply 6
    s = g.initial_state()
    for m in ["2,4>2,3", "2,0>2,1", "2,3>1,2", "2,1>3,2",
              "1,2>2,3", "3,2>2,1"]:
        assert not g.is_terminal(s), s.ply
        s = g.apply_move(s, m)
    assert s.drawn and g.is_terminal(s) and s.winner is None
    assert g.returns(s) == [0.0, 0.0]

    # --- serialize round-trip -------------------------------------------
    s = g.apply_move(g.initial_state(), "2,4>2,3")
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert s2.pos == s.pos and s2.to_move == s.to_move
    assert s2.history == s.history and s2.variant == s.variant

    # --- FULL SOLVE anchors (through the game class) --------------------
    assert solve(g, "closed") == (2278, 6518, 1062, 726, 490, "DRAW", 20)
    assert solve(g, "trap") == (15972, 52878, 1608, 1134, 13230, "DRAW", 22)

    # --- random-playout termination sweep -------------------------------
    rng = random.Random(7)
    for variant in ("closed", "trap"):
        for _ in range(100):
            s = g.initial_state({"invasion": variant})
            while not g.is_terminal(s):
                s = g.apply_move(s, rng.choice(g.legal_moves(s)))
            r = g.returns(s)
            assert r in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0])
            assert s.ply <= 200

    # --- render spec shape probe ----------------------------------------
    spec = g.render(g.initial_state())
    assert spec["board"]["type"] == "polygons"
    assert isinstance(spec["board"]["cells"], list) and len(spec["board"]["cells"]) == 11
    assert all("id" in c and "points" in c for c in spec["board"]["cells"])
    assert len(spec["pieces"]) == 6

    print("hobak_gonu selftest OK")


if __name__ == "__main__":
    run()
