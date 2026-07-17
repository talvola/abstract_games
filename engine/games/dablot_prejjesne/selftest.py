"""Dablot Prejjesne correctness anchor (pure stdlib).

No published perft exists; the anchor is the frozen 72-point / 191-edge lattice
(6x7 grid vertices + 30 square centres, per Keyland 1921 / Wikipedia / Ludii),
the exact 30v30 initial setup, the rank-restricted jump rule (a piece captures
only equal or lower rank), optional-vs-compulsory capture modes, chain captures
with direction change, the special endings (two lone kings = draw; equal-rank
single combat; trapped player loses), and seeded playout termination with
conservation sweeps.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.dablot_prejjesne.game import (  # noqa: E402
    DablotPrejjesne, DState, GEOM, SAMI, FARMER, CONE, PRINCE, KING,
    PLY_CAP, NO_CAPTURE_DRAW,
)

G = DablotPrejjesne()

# Frozen full edge list (191 drawn segments), generated independently of
# game.py: horizontal/vertical lines between the 42 grid vertices plus both
# diagonals of each of the 30 squares through its centre point.
FROZEN_EDGES = (
    "0,0-0,2;0,0-1,1;0,0-2,0;0,2-0,4;0,2-1,1;0,2-1,3;0,2-2,2;0,4-0,6;0,4-1,3;0,4-"
    "1,5;0,4-2,4;0,6-0,8;0,6-1,5;0,6-1,7;0,6-2,6;0,8-0,10;0,8-1,7;0,8-1,9;0,8-"
    "2,8;0,10-0,12;0,10-1,9;0,10-1,11;0,10-2,10;0,12-1,11;0,12-2,12;1,1-2,0;1,1-"
    "2,2;1,3-2,2;1,3-2,4;1,5-2,4;1,5-2,6;1,7-2,6;1,7-2,8;1,9-2,8;1,9-2,10;1,11-"
    "2,10;1,11-2,12;2,0-2,2;2,0-3,1;2,0-4,0;2,2-2,4;2,2-3,1;2,2-3,3;2,2-4,2;2,4-"
    "2,6;2,4-3,3;2,4-3,5;2,4-4,4;2,6-2,8;2,6-3,5;2,6-3,7;2,6-4,6;2,8-2,10;2,8-"
    "3,7;2,8-3,9;2,8-4,8;2,10-2,12;2,10-3,9;2,10-3,11;2,10-4,10;2,12-3,11;2,12-"
    "4,12;3,1-4,0;3,1-4,2;3,3-4,2;3,3-4,4;3,5-4,4;3,5-4,6;3,7-4,6;3,7-4,8;3,9-"
    "4,8;3,9-4,10;3,11-4,10;3,11-4,12;4,0-4,2;4,0-5,1;4,0-6,0;4,2-4,4;4,2-"
    "5,1;4,2-5,3;4,2-6,2;4,4-4,6;4,4-5,3;4,4-5,5;4,4-6,4;4,6-4,8;4,6-5,5;4,6-"
    "5,7;4,6-6,6;4,8-4,10;4,8-5,7;4,8-5,9;4,8-6,8;4,10-4,12;4,10-5,9;4,10-"
    "5,11;4,10-6,10;4,12-5,11;4,12-6,12;5,1-6,0;5,1-6,2;5,3-6,2;5,3-6,4;5,5-"
    "6,4;5,5-6,6;5,7-6,6;5,7-6,8;5,9-6,8;5,9-6,10;5,11-6,10;5,11-6,12;6,0-"
    "6,2;6,0-7,1;6,0-8,0;6,2-6,4;6,2-7,1;6,2-7,3;6,2-8,2;6,4-6,6;6,4-7,3;6,4-"
    "7,5;6,4-8,4;6,6-6,8;6,6-7,5;6,6-7,7;6,6-8,6;6,8-6,10;6,8-7,7;6,8-7,9;6,8-"
    "8,8;6,10-6,12;6,10-7,9;6,10-7,11;6,10-8,10;6,12-7,11;6,12-8,12;7,1-8,0;7,1-"
    "8,2;7,3-8,2;7,3-8,4;7,5-8,4;7,5-8,6;7,7-8,6;7,7-8,8;7,9-8,8;7,9-8,10;7,11-"
    "8,10;7,11-8,12;8,0-8,2;8,0-9,1;8,0-10,0;8,2-8,4;8,2-9,1;8,2-9,3;8,2-"
    "10,2;8,4-8,6;8,4-9,3;8,4-9,5;8,4-10,4;8,6-8,8;8,6-9,5;8,6-9,7;8,6-10,6;8,8-"
    "8,10;8,8-9,7;8,8-9,9;8,8-10,8;8,10-8,12;8,10-9,9;8,10-9,11;8,10-10,10;8,12-"
    "9,11;8,12-10,12;9,1-10,0;9,1-10,2;9,3-10,2;9,3-10,4;9,5-10,4;9,5-10,6;9,7-"
    "10,6;9,7-10,8;9,9-10,8;9,9-10,10;9,11-10,10;9,11-10,12;10,0-10,2;10,2-"
    "10,4;10,4-10,6;10,6-10,8;10,8-10,10;10,10-10,12"
)


def st(board, to_move=SAMI, compulsory=False):
    return DState(board=dict(board), to_move=to_move, compulsory=compulsory)


def moves(board, to_move=SAMI, compulsory=False):
    return G.legal_moves(st(board, to_move, compulsory))


def main():
    # ---- lattice: 72 points, frozen 191-edge list, degree histogram --------
    assert len(GEOM.points) == 72 and len(set(GEOM.points)) == 72
    assert len(GEOM.verts) == 42 and len(GEOM.cents) == 30
    edges = sorted({tuple(sorted((a, b))) for a in GEOM.adj for b in GEOM.adj[a]})
    assert len(edges) == 191, len(edges)
    got = ";".join(f"{a[0]},{a[1]}-{b[0]},{b[1]}" for a, b in edges)
    assert got == FROZEN_EDGES, "edge list mismatch"
    from collections import Counter
    degs = Counter(len(GEOM.adj[p]) for p in GEOM.points)
    assert degs == {4: 30, 8: 20, 5: 18, 3: 4}, degs
    # centres connect only to their four square corners
    assert GEOM.adj[(1, 1)] == {(0, 0), (2, 0), (0, 2), (2, 2)}
    # capture geometry samples: along each straight drawn line only
    assert ((2, 0), (4, 0)) in GEOM.cap_pairs[(0, 0)]      # horizontal
    assert ((0, 2), (0, 4)) in GEOM.cap_pairs[(0, 0)]      # vertical
    assert ((1, 1), (2, 2)) in GEOM.cap_pairs[(0, 0)]      # diagonal over centre
    assert ((2, 2), (3, 3)) in GEOM.cap_pairs[(1, 1)]      # diagonal over vertex
    assert all(land != (0, 0) for _, land in GEOM.cap_pairs[(1, 1)])

    # ---- initial setup: exact 30v30 ---------------------------------------
    s = G.initial_state()
    expected = {}
    for (x, y) in GEOM.points:
        if y >= 8:
            expected[(x, y)] = (SAMI, CONE)
        elif y <= 4:
            expected[(x, y)] = (FARMER, CONE)
    expected[(9, 7)] = (SAMI, PRINCE)
    expected[(10, 6)] = (SAMI, KING)
    expected[(1, 5)] = (FARMER, PRINCE)
    expected[(0, 6)] = (FARMER, KING)
    assert s.board == expected
    for side in (SAMI, FARMER):
        ranks = [r for (o, r) in s.board.values() if o == side]
        assert len(ranks) == 30 and ranks.count(CONE) == 28
        assert ranks.count(PRINCE) == 1 and ranks.count(KING) == 1
    # setup is symmetric under 180-degree rotation
    for (x, y), (own, rank) in s.board.items():
        assert s.board[(10 - x, 12 - y)] == (1 - own, rank)
    # opening: Sami to move, exactly 15 single steps along drawn lines, no jumps
    ms = G.legal_moves(s)
    assert len(ms) == 15, ms
    for m in ms:
        a, b = m.split(">")
        pa, pb = tuple(map(int, a.split(","))), tuple(map(int, b.split(",")))
        assert s.board[pa][0] == SAMI and pb in GEOM.adj[pa] and pb not in s.board
    assert "10,6>9,5" in ms and "9,7>8,6" in ms          # king and prince steps

    # ---- rank rule: attacker (4,6) jumps (4,4) to (4,2) iff rank allows ----
    filler = {(0, 0): (FARMER, CONE), (10, 12): (FARMER, CONE)}  # avoid special endings
    for atk, vic, ok in [(CONE, CONE, True), (CONE, PRINCE, False), (CONE, KING, False),
                         (PRINCE, CONE, True), (PRINCE, PRINCE, True), (PRINCE, KING, False),
                         (KING, CONE, True), (KING, PRINCE, True), (KING, KING, True)]:
        b = {(4, 6): (SAMI, atk), (4, 4): (FARMER, vic), **filler}
        assert ("4,6>4,2" in moves(b)) == ok, (atk, vic)
    # a cone facing the enemy king (the opening corner situation) cannot take it
    b = {(0, 8): (SAMI, CONE), (0, 6): (FARMER, KING), **filler}
    assert "0,8>0,4" not in moves(b)

    # ---- jumps over/onto centre points ------------------------------------
    b = {(2, 6): (SAMI, CONE), (3, 5): (FARMER, CONE), (10, 12): (FARMER, CONE)}
    assert "2,6>4,4" in moves(b)                          # vertex over centre
    b = {(3, 5): (SAMI, CONE), (4, 4): (FARMER, CONE), (10, 12): (FARMER, CONE)}
    assert "3,5>5,3" in moves(b)                          # centre over vertex

    # ---- chain capture with direction change; optional vs compulsory ------
    chain = {(2, 6): (SAMI, CONE), (3, 5): (FARMER, CONE), (3, 3): (FARMER, CONE)}
    opt = moves(chain)
    assert "2,6>4,4>2,2" in opt          # full chain (NE then NW)
    assert "2,6>4,4" in opt              # optional: may stop mid-chain
    assert "2,6>2,4" in opt              # optional: may decline and step
    comp = moves(chain, compulsory=True)
    assert "2,6>4,4>2,2" in comp
    assert "2,6>4,4" not in comp         # compulsory: must continue the chain
    for m in comp:                       # compulsory: every move is a jump
        pts = [tuple(map(int, c.split(","))) for c in m.split(">")]
        assert pts[1] not in GEOM.adj[pts[0]], m
    end = G.apply_move(st(chain), "2,6>4,4>2,2")
    assert (3, 5) not in end.board and (3, 3) not in end.board
    assert end.board[(2, 2)] == (SAMI, CONE) and end.winner == SAMI  # annihilation
    assert G.returns(end) == [1.0, -1.0]
    # rank respected mid-chain: second victim is a prince -> chain must stop
    b = {(2, 6): (SAMI, CONE), (3, 5): (FARMER, CONE), (3, 3): (FARMER, PRINCE)}
    assert "2,6>4,4" in moves(b, compulsory=True)
    assert "2,6>4,4>2,2" not in moves(b, compulsory=True)
    # compulsory: any capture anywhere suppresses all plain steps
    b = {(2, 6): (SAMI, CONE), (3, 5): (FARMER, CONE),
         (10, 12): (SAMI, CONE), (0, 0): (FARMER, CONE)}
    assert all(m not in moves(b, compulsory=True)
               for m in ("10,12>10,10", "2,6>2,4"))

    # ---- two lone kings: draw (hand-built and reached via apply_move) ------
    kk = st({(4, 6): (SAMI, KING), (0, 0): (FARMER, KING)})
    assert G.is_terminal(kk) and kk.winner is None and G.returns(kk) == [0.0, 0.0]
    pre = st({(4, 6): (SAMI, KING), (4, 4): (FARMER, CONE), (0, 0): (FARMER, KING)})
    assert "4,6>4,2" in G.legal_moves(pre)
    post = G.apply_move(pre, "4,6>4,2")
    assert G.is_terminal(post) and post.winner is None
    assert G.returns(post) == [0.0, 0.0] and G.legal_moves(post) == []

    # ---- trapped player loses (win reached via apply_move) -----------------
    # Farmer's lone cone in the corner (0,0): steps blocked by Sami pieces,
    # jumps blocked by rank (king/prince) or an occupied landing point.
    trap = {(0, 0): (FARMER, CONE), (1, 1): (SAMI, KING), (0, 2): (SAMI, PRINCE),
            (2, 0): (SAMI, CONE), (4, 0): (SAMI, CONE), (10, 12): (SAMI, CONE)}
    assert moves(trap, to_move=FARMER) == []
    after = G.apply_move(st(trap), "10,12>10,10")        # quiet Sami step
    assert after.winner == SAMI and G.is_terminal(after)
    assert G.returns(after) == [1.0, -1.0]

    # ---- single combat: equal-rank lone pieces must close in --------------
    sc = moves({(0, 0): (SAMI, CONE), (10, 12): (FARMER, CONE)})
    assert set(sc) == {"0,0>1,1", "0,0>2,0", "0,0>0,2"}, sc   # only approach steps
    # adjacent equal singles: the capture is forced and ends the game
    duel = st({(2, 2): (SAMI, CONE), (3, 3): (FARMER, CONE)})
    assert G.legal_moves(duel) == ["2,2>4,4"]
    assert G.apply_move(duel, "2,2>4,4").winner == SAMI
    # unequal lone pieces: no restriction (retreat is legal), no illegal capture
    free = moves({(4, 6): (SAMI, PRINCE), (4, 4): (FARMER, KING)})
    assert "4,6>4,8" in free and "4,6>4,2" not in free

    # ---- serialize round-trips (both modes, legacy default) ----------------
    for mode in (False, True):
        s0 = G.initial_state(options={"captures": "compulsory" if mode else "optional"})
        s1 = G.apply_move(s0, G.legal_moves(s0)[0])
        d = G.serialize(s1)
        assert G.serialize(G.deserialize(d)) == d
        assert G.deserialize(d).compulsory == mode
        assert ("captures" in d) == mode
    legacy = dict(G.serialize(G.initial_state()))
    legacy.pop("captures", None)
    assert G.deserialize(legacy).compulsory is False

    # ---- describe_move / render / heuristic --------------------------------
    assert G.describe_move(s, "10,6>9,5") == "10,6-9,5"
    assert G.describe_move(st(chain), "2,6>4,4>2,2") == "2,6x4,4x2,2"
    spec = G.render(s)
    assert spec["board"]["type"] == "polygons"
    assert len(spec["board"]["cells"]) == 72 and len(spec["board"]["lines"]) == 191
    assert len(spec["pieces"]) == 60
    labels = [p.get("label") for p in spec["pieces"]]
    assert labels.count("K") == 2 and labels.count("P") == 2
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9

    # ---- seeded playouts: termination + conservation -----------------------
    for mode, n_games in (("optional", 130), ("compulsory", 70)):
        rng = random.Random(20260717 if mode == "optional" else 1921)
        for _ in range(n_games):
            stt = G.initial_state(options={"captures": mode})
            prev = 60
            while not G.is_terminal(stt):
                ms = G.legal_moves(stt)
                assert ms, "non-terminal state with no moves"
                stt = G.apply_move(stt, rng.choice(ms))
                now = len(stt.board)
                assert now <= prev, "pieces appeared"
                prev = now
                for side in (SAMI, FARMER):
                    rks = [r for (o, r) in stt.board.values() if o == side]
                    assert rks.count(KING) <= 1 and rks.count(PRINCE) <= 1
                    assert len(rks) <= 30
            assert stt.ply <= PLY_CAP
            assert stt.since <= NO_CAPTURE_DRAW
            r = G.returns(stt)
            assert r in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0])

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
