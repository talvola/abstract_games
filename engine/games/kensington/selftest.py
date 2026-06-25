"""Standalone correctness anchor for Kensington (pure stdlib: agp + this game).

Asserts:
  * board structure: 72 vertices, 7 hexagons (3 white / 2 red / 2 blue), 30
    squares, 24 triangles, 132 edges; a symmetric adjacency graph; each hexagon
    is a genuine 6-cycle; spot-checked adjacencies;
  * the opening legal-move count == number of empty vertices (72);
  * the phase transition placement -> movement;
  * a constructed win: occupy all 6 vertices of a hexagon, reached via apply_move
    (win-as-event), for a white hexagon AND for an own-colour hexagon;
  * the triangle / square mill -> relocation, constructed via apply_move;
  * serialize / deserialize round-trip.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.kensington.game import (  # noqa: E402
    Kensington, KState, RED, BLUE,
    POINTS, VERTS, ADJ, HEXES, SQUARES, TRIANGLES, TRIANGLES_AT, SQUARES_AT,
    _OWN_COLOR,
)


def test_structure():
    assert len(POINTS) == 72, len(POINTS)
    assert len(set(POINTS)) == 72
    assert len(HEXES) == 7, len(HEXES)
    colors = sorted(h["color"] for h in HEXES)
    assert colors == ["blue", "blue", "red", "red", "white", "white", "white"], colors
    assert len(SQUARES) == 30, len(SQUARES)
    assert len(TRIANGLES) == 24, len(TRIANGLES)

    # adjacency is symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], (p, q)
    # edge count = sum(deg)/2 == 132
    edges = sum(len(ADJ[p]) for p in POINTS) // 2
    assert edges == 132, edges
    # degree distribution: 48 interior (deg 4), 24 perimeter (deg 3)
    degs = sorted(len(ADJ[p]) for p in POINTS)
    assert degs.count(4) == 48 and degs.count(3) == 24, degs

    # each hexagon's 6 vertices form a 6-cycle in the adjacency graph
    import math
    for h in HEXES:
        vs = list(h["verts"])
        assert len(vs) == 6
        cx = sum(VERTS[v][0] for v in vs) / 6
        cy = sum(VERTS[v][1] for v in vs) / 6
        vs.sort(key=lambda v: math.atan2(VERTS[v][1] - cy, VERTS[v][0] - cx))
        for i in range(6):
            assert vs[(i + 1) % 6] in ADJ[vs[i]], (h["color"], vs)

    # the three white hexagons sit on the vertical centre line (x ~ 0)
    whites = [h for h in HEXES if h["color"] == "white"]
    for h in whites:
        cx = sum(VERTS[v][0] for v in h["verts"]) / 6
        assert abs(cx) < 1e-6, cx
    # red hexagons on one side, blue on the other (opposite x signs)
    redx = [sum(VERTS[v][0] for v in h["verts"]) / 6 for h in HEXES if h["color"] == "red"]
    bluex = [sum(VERTS[v][0] for v in h["verts"]) / 6 for h in HEXES if h["color"] == "blue"]
    assert all(x > 0 for x in redx) and all(x < 0 for x in bluex), (redx, bluex)


def test_opening():
    g = Kensington()
    st = g.initial_state()
    assert g.current_player(st) == RED
    moves = g.legal_moves(st)
    assert len(moves) == 72, len(moves)            # every vertex empty
    assert set(moves) == set(POINTS)
    assert not g.is_terminal(st)


def test_phase_transition():
    """Fill the board with 15+15 placements; the next mover must be sliding."""
    g = Kensington()
    st = g.initial_state()
    # place 15 red and 15 blue on chosen empty vertices, avoiding any mill/win.
    # Strategy: just take legal placement moves and play them; mills may happen,
    # but at minimum after 30 *placements* the placement phase is over.
    placements = 0
    guard = 0
    while g._placing(st) and not g.is_terminal(st):
        guard += 1
        assert guard < 500
        mv = g.legal_moves(st)[0]
        before = sum(st.placed)
        st = g.apply_move(st, mv)
        if sum(st.placed) > before:
            placements += 1
    if not g.is_terminal(st):
        # placement phase complete -> all 30 counters placed, next move is a slide
        assert st.placed == [15, 15], st.placed
        for m in g.legal_moves(st):
            assert ">" in m


def _occupy(pos, verts, owner):
    for v in verts:
        pos[v] = owner


def test_win_white_hex():
    """Filling all 6 vertices of a WHITE hexagon (reached via apply_move) wins."""
    g = Kensington()
    white = next(h for h in HEXES if h["color"] == "white")
    vs = list(white["verts"])
    # Build a near-complete state: Red owns 5 of the 6 white-hex vertices, in the
    # movement phase, and slides a counter onto the 6th from an adjacent vertex.
    last = vs[-1]
    # find an adjacent vertex to `last` not in the hex to slide from
    src = next(q for q in ADJ[last] if q not in vs)
    pos = {}
    _occupy(pos, vs[:-1], RED)         # 5 of 6
    pos[src] = RED                     # the sliding counter
    # give Blue some counters elsewhere so placement is "done"
    others = [p for p in POINTS if p not in pos][:30]
    for i, p in enumerate(others):
        if len([x for x in pos.values() if x == BLUE]) >= 15:
            break
        pos[p] = BLUE
    st = KState(pos=pos, to_move=RED, placed=[15, 15], relo=0, since_progress=0)
    assert not g.is_terminal(st)        # not yet won (win is an event)
    st2 = g.apply_move(st, f"{src}>{last}")
    assert g.is_terminal(st2)
    assert st2.winner == RED, st2.winner
    assert g.returns(st2) == [1.0, -1.0]


def test_win_own_color_only():
    """Red wins on a RED hexagon; Red must NOT win on a Blue hexagon."""
    g = Kensington()
    red_hex = next(h for h in HEXES if h["color"] == "red")
    blue_hex = next(h for h in HEXES if h["color"] == "blue")

    # Red completes a RED hexagon -> win.
    vs = list(red_hex["verts"])
    src = next(q for q in ADJ[vs[-1]] if q not in vs)
    pos = {}
    _occupy(pos, vs[:-1], RED)
    pos[src] = RED
    st = KState(pos=pos, to_move=RED, placed=[15, 15], relo=0, since_progress=0)
    st2 = g.apply_move(st, f"{src}>{vs[-1]}")
    assert st2.winner == RED

    # Red occupies all 6 of a BLUE hexagon -> NOT a win for Red.
    bvs = list(blue_hex["verts"])
    src2 = next(q for q in ADJ[bvs[-1]] if q not in bvs)
    pos = {}
    _occupy(pos, bvs[:-1], RED)
    pos[src2] = RED
    st = KState(pos=pos, to_move=RED, placed=[15, 15], relo=0, since_progress=0)
    st3 = g.apply_move(st, f"{src2}>{bvs[-1]}")
    assert st3.winner is None, st3.winner
    # (and BLUE certainly hasn't won either — they own none of it)


def test_triangle_mill_relocation():
    """Completing a triangle earns exactly one enemy relocation."""
    g = Kensington()
    tri = next(iter(TRIANGLES))
    vs = list(tri)
    last = vs[-1]
    src = next(q for q in ADJ[last] if q not in vs)
    pos = {}
    _occupy(pos, vs[:-1], RED)
    pos[src] = RED
    pos_enemy = next(p for p in POINTS if p not in pos and p not in vs)
    pos[pos_enemy] = BLUE             # an enemy counter that can be relocated
    st = KState(pos=pos, to_move=RED, placed=[15, 15], relo=0, since_progress=5)
    st2 = g.apply_move(st, f"{src}>{last}")
    # the move completed the triangle (assuming no hexagon completed) -> relo == 1
    if st2.winner is None:
        assert st2.relo == 1, st2.relo
        assert st2.to_move == RED      # same player keeps the turn
        assert st2.since_progress == 0  # a mill is progress
        # legal relocations move an enemy counter to an empty vertex
        rmoves = g.legal_moves(st2)
        assert all(">" in m for m in rmoves)
        frm, to = rmoves[0].split(">")
        assert st2.pos[frm] == BLUE and to not in st2.pos
        st3 = g.apply_move(st2, rmoves[0])
        # relocation done; if no win, turn passes to Blue with relo back to 0
        if st3.winner is None:
            assert st3.relo == 0
            assert st3.to_move == BLUE


def test_square_mill_relocation():
    """Completing a square earns two relocations (capped at two)."""
    g = Kensington()
    sq = next(iter(SQUARES))
    vs = list(sq)
    last = vs[-1]
    src = next(q for q in ADJ[last] if q not in vs)
    pos = {}
    _occupy(pos, vs[:-1], RED)
    pos[src] = RED
    # two enemy counters somewhere relocatable
    empties = [p for p in POINTS if p not in pos and p not in vs]
    pos[empties[0]] = BLUE
    pos[empties[1]] = BLUE
    st = KState(pos=pos, to_move=RED, placed=[15, 15], relo=0, since_progress=0)
    st2 = g.apply_move(st, f"{src}>{last}")
    if st2.winner is None:
        assert st2.relo == 2, st2.relo


def test_serialize_roundtrip():
    g = Kensington()
    st = g.initial_state()
    for _ in range(8):
        mvs = g.legal_moves(st)
        if not mvs:
            break
        st = g.apply_move(st, mvs[0])
    d = g.serialize(st)
    st2 = g.deserialize(d)
    assert g.serialize(st2) == d
    import json
    json.dumps(d)   # must be JSON-able


def test_termination_random():
    """Random playouts must terminate (draw cap / win)."""
    import random
    g = Kensington()
    for seed in range(20):
        rng = random.Random(seed)
        st = g.initial_state()
        for ply in range(5000):
            if g.is_terminal(st):
                break
            mvs = g.legal_moves(st)
            assert mvs, "non-terminal with no moves"
            st = g.apply_move(st, rng.choice(mvs))
        assert g.is_terminal(st), f"seed {seed} did not terminate"
        r = g.returns(st)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)


if __name__ == "__main__":
    test_structure()
    test_opening()
    test_phase_transition()
    test_win_white_hex()
    test_win_own_color_only()
    test_triangle_mill_relocation()
    test_square_mill_relocation()
    test_serialize_roundtrip()
    test_termination_random()
    print("kensington selftest: all tests passed")
