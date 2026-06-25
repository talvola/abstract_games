"""Pure-stdlib selftest for Trax -- correctness anchors.

Run: PYTHONPATH=. python3 games/trax/selftest.py
Imports only `agp` + this game (no python-chess / numpy).
"""

from __future__ import annotations

import json
import random

from games.trax.game import (
    Trax, TraxState, TraxError, ORIENTATIONS, ORIENT_TOKENS,
    edges_of, segs_of, edge_colour, other_edge, W_COL, R_COL,
    WHITE_HEX, RED_HEX,
)


def test_orientations_well_formed():
    assert len(ORIENTATIONS) == 6, "must be exactly 6 orientations"
    straights, curves = 0, 0
    for tok, (edges, wseg, rseg) in ORIENTATIONS.items():
        # exactly two white, two red edges
        assert edges.count("W") == 2 and edges.count("R") == 2, tok
        # white seg joins the two white edges, red seg the two red edges
        we = tuple(sorted(i for i, c in enumerate(edges) if c == "W"))
        re = tuple(sorted(i for i, c in enumerate(edges) if c == "R"))
        assert tuple(sorted(wseg)) == we, f"{tok} white seg mismatch"
        assert tuple(sorted(rseg)) == re, f"{tok} red seg mismatch"
        # opposite-pair (0,2)/(1,3) => straight, adjacent => curve
        a, b = sorted(wseg)
        if (a, b) in ((0, 2), (1, 3)):
            straights += 1
        else:
            curves += 1
        # segs_of / edge_colour / other_edge consistency
        assert segs_of(tok)[W_COL] == wseg and segs_of(tok)[R_COL] == rseg
        for e in range(4):
            assert edge_colour(tok, e) == edges[e]
        wa, wb = wseg
        assert other_edge(tok, W_COL, wa) == wb and other_edge(tok, W_COL, wb) == wa
        ra, rb = rseg
        assert other_edge(tok, R_COL, ra) == rb
    assert straights == 2 and curves == 4, f"expected 2 straight / 4 curved, got {straights}/{curves}"
    print("ok: 2 tile types -> 6 orientations, each 2W/2R edges with correct track segments")


def test_matching_rule():
    g = Trax()
    # Place TL at (0,0): edges (W,R,R,W). Cell (1,0) is to the right; (0,0) edge 1
    # (right) = R, so (1,0) edge 3 (left) must be R.
    placed = {(0, 0): "TL"}
    assert g._orientation_fits(placed, (1, 0), "|"), "| (left=R) should match"
    assert not g._orientation_fits(placed, (1, 0), "-"), "- (left=W) must be rejected"
    # legal orientations on (1,0): all tokens whose left edge is R
    legal = g._legal_orientations(placed, (1, 0))
    for t in legal:
        assert edge_colour(t, 3) == "R", f"{t} offered but left!=R"
    for t in ORIENT_TOKENS:
        if edge_colour(t, 3) == "R":
            assert t in legal or _forces_illegal(g, placed, (1, 0), t), t
    # a cell touching no placed tile is unplayable
    assert g._legal_orientations(placed, (5, 5)) == []
    print("ok: matching rule accepts colour-matching tiles, rejects mismatches")


def _forces_illegal(g, placed, cell, tok):
    trial = dict(placed); trial[cell] = tok
    try:
        g._resolve_forced(trial)
        return False
    except TraxError:
        return True


def test_forced_move_resolution():
    g = Trax()
    # Construct an empty cell (1,1) whose two edges are forced to the SAME colour.
    # Neighbour below (1,0): make its TOP edge (edge 0) white.  Neighbour left
    # (0,1): make its RIGHT edge (edge 1) white.  Then (1,1)'s bottom (edge2) and
    # left (edge3) are both forced WHITE -> mandatory tile joining {2,3} = "BL".
    # Pick orientations for the neighbours with those edge colours:
    #   (1,0) needs edge0 (top) = W  -> "|" has edges (W,R,W,R): top=W  good.
    #   (0,1) needs edge1 (right)= W -> "-" has edges (R,W,R,W): right=W good.
    placed = {(1, 0): "|", (0, 1): "-"}
    tok = g._forced_token(placed, (1, 1))
    assert tok == "BL", f"forced tile should be BL (white joins 2,3), got {tok}"
    # resolution fills it in
    resolved = g._resolve_forced(placed)
    assert resolved.get((1, 1)) == "BL", f"forced cell not filled: {resolved}"
    # a cell with only ONE constrained edge is NOT forced
    assert g._forced_token({(1, 0): "|"}, (1, 1)) is None
    # two DIFFERENT-colour forced edges are NOT mandatory
    #   (1,0) top=W via "|"; (0,1) right=R: "|" edges (W,R,W,R): right=R.
    assert g._forced_token({(1, 0): "|", (0, 1): "|"}, (1, 1)) is None
    print("ok: forced-move detection + resolution (two like-colour edges -> mandatory tile)")


def test_forced_illegal_three_edges():
    g = Trax()
    # Make three of cell (1,1)'s edges forced to white -> illegal.
    #   below (1,0) top=W  -> "|"
    #   left  (0,1) right=W -> "-"
    #   above (1,2) bottom=W (edge2). "|" edges (W,R,W,R): bottom=W. good.
    placed = {(1, 0): "|", (0, 1): "-", (1, 2): "|"}
    raised = False
    try:
        g._forced_token(placed, (1, 1))
    except TraxError:
        raised = True
    assert raised, "3 same-colour forced edges must raise TraxError"
    print("ok: a 3-same-colour-edge configuration is detected as illegal")


def test_loop_win_via_apply_move():
    g = Trax()
    # A white 2x2 loop: white track curves around the central shared corner.
    #   (0,0) white joins right(1)+top(0) -> "TR"
    #   (1,0) white joins left(3)+top(0)  -> "TL"
    #   (1,1) white joins bottom(2)+left(3) -> "BL"
    #   (0,1) white joins right(1)+bottom(2) -> "BR"
    loop = {(0, 0): "TR", (1, 0): "TL", (1, 1): "BL", (0, 1): "BR"}
    # confirm matching is internally consistent (shared edges agree)
    for cell, tok in loop.items():
        for e in range(4):
            nb = g._neighbour(cell, e)
            if nb in loop:
                assert edge_colour(tok, e) == edge_colour(loop[nb], (e + 2) % 4), \
                    f"loop edges disagree at {cell}/{e}"
    assert g._has_loop(loop, W_COL), "white should form a loop"
    assert g._colour_won(loop, W_COL) == "loop"
    # the red tracks here do NOT loop (they run to the open outer edges)
    assert not g._has_loop(loop, R_COL)

    # Reach the loop as a real terminal via apply_move: build the position by
    # placing the first three tiles, then White completes the loop on move 4.
    # Drive it directly by setting state to the three-tile partial and letting
    # White place the closing tile. (We bypass turn alternation -- only the final
    # placement's win matters for this anchor.)
    partial = TraxState(placed={(0, 0): "TR", (1, 0): "TL", (1, 1): "BL"},
                        to_move=0, ply=3, winner=None)
    # the closing cell (0,1) with "BR" must be a legal move for White
    mv = "0,1=BR"
    assert mv in g.legal_moves(partial), f"closing move not legal: {g.legal_moves(partial)}"
    end = g.apply_move(partial, mv)
    assert g.is_terminal(end), "loop completion should be terminal"
    assert end.winner == 0, f"White (seat 0) should win the white loop, got {end.winner}"
    assert g.returns(end) == [1.0, -1.0]
    print("ok: a white 2x2 loop is detected and wins via apply_move")


def test_winning_line_via_apply_move():
    g = Trax()
    # A straight horizontal white line across 8 columns: place "-" (white joins
    # left<->right) on (0,0)..(7,0). White track runs continuously left->right and
    # touches the leftmost (col 0) and rightmost (col 7) cells; span = 8 columns.
    line = {(c, 0): "-" for c in range(8)}
    # shared vertical edges all white (right of one == left of next), consistent.
    for c in range(7):
        assert edge_colour("-", 1) == edge_colour("-", 3) == "W"
    assert g._colour_won(line, W_COL) == "line", "8-wide white line should win"
    # 7 columns is NOT enough
    line7 = {(c, 0): "-" for c in range(7)}
    assert g._colour_won(line7, W_COL) is None, "7-column line must not win"
    # vertical line of 8 with "|" (white top<->bottom)
    vline = {(0, r): "|" for r in range(8)}
    assert g._colour_won(vline, W_COL) == "line", "8-tall white line should win"

    # via apply_move: White closes the 8th tile of the line.
    partial = TraxState(placed={(c, 0): "-" for c in range(7)},
                        to_move=0, ply=7, winner=None)
    mv = "7,0=-"
    assert mv in g.legal_moves(partial), f"line-closing move illegal: {mv}"
    end = g.apply_move(partial, mv)
    assert g.is_terminal(end) and end.winner == 0, f"White should win the line, got {end.winner}"
    print("ok: an 8-span white line wins (and a 7-span line does not)")


def test_simultaneous_win_mover():
    g = Trax()
    # If the same final placement completes a win for both colours, the MOVER wins.
    # Easiest: hand-build a placed dict where BOTH white and red satisfy a win, and
    # confirm apply_move credits the mover. We fake it by setting `to_move` then
    # placing a no-op-ish legal tile that leaves both colours winning. Construct a
    # board where white already loops AND red already loops, then have Red place a
    # final tile adjacent that keeps both loops. Simpler: directly assert the
    # tie-break logic by calling apply_move from a state that is already a both-win
    # board after the placement.
    # Build two separate single-colour loops (one white, one red) far apart, then
    # Red places one extra tile that doesn't break either -> both win, Red moved.
    wloop = {(0, 0): "TR", (1, 0): "TL", (1, 1): "BL", (0, 1): "BR"}
    # red loop offset far away (cols 10+): red joins the same adjacencies.
    #   red track curves around: at (10,10) red joins right+top etc. Use the SAME
    #   token pattern but it's the RED segments that loop iff red edges curve.
    #   For a RED loop we need each tile's RED seg to curve around the corner:
    #   (10,10) red joins right(1)+top(0) -> token whose red seg = {0,1} = "BL".
    #   (11,10) red joins left(3)+top(0)  -> red {0,3} = "BR".
    #   (11,11) red joins bottom(2)+left(3) -> red {2,3} = "TR".
    #   (10,11) red joins right(1)+bottom(2) -> red {1,2} = "TL".
    rloop = {(10, 10): "BL", (11, 10): "BR", (11, 11): "TR", (10, 11): "TL"}
    both = dict(wloop); both.update(rloop)
    assert g._colour_won(both, W_COL) == "loop"
    assert g._colour_won(both, R_COL) == "loop"
    # Now: the position one tile before completion, with Red to move closing the
    # RED loop -- which simultaneously leaves the white loop already present.
    pre = dict(both); del pre[(10, 11)]
    st = TraxState(placed=pre, to_move=1, ply=8, winner=None)
    mv = "10,11=TL"
    assert mv in g.legal_moves(st), f"red closing move illegal: {g.legal_moves(st)[:5]}..."
    end = g.apply_move(st, mv)
    assert end.winner == 1, f"Red (the mover) should win the tie, got {end.winner}"
    print("ok: simultaneous both-colour win -> the player who moved wins")


def test_opening_and_legal_count():
    g = Trax()
    s = g.initial_state()
    moves = g.legal_moves(s)
    assert moves == ["0,0=TL"], f"opening must be the single canonical tile, got {moves}"
    s2 = g.apply_move(s, "0,0=TL")
    assert not g.is_terminal(s2)
    n = len(g.legal_moves(s2))
    # 4 frontier cells, each accepting some orientations; record the anchor count.
    assert n > 0
    print(f"ok: opening = '0,0=TL'; after it, {n} legal placements")
    return n


def test_serialize_roundtrip():
    g = Trax()
    s = g.initial_state()
    for _ in range(6):
        if g.is_terminal(s):
            break
        s = g.apply_move(s, g.legal_moves(s)[0])
    d = g.serialize(s)
    json.dumps(d)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d, "serialize did not round-trip"
    assert s2.placed == s.placed and s2.to_move == s.to_move and s2.winner == s.winner
    print("ok: serialize round-trips")


def test_render_contract():
    g = Trax()
    s = g.apply_move(g.initial_state(), "0,0=TL")
    spec = g.render(s)
    b = spec["board"]
    assert b["type"] == "polygons"
    assert isinstance(b["cells"], list)
    for c in b["cells"]:
        assert "id" in c and "points" in c and isinstance(c["points"], list)
    tr = b["tracks"]
    assert "0,0" in tr, "placed tile must appear in board.tracks"
    segs = tr["0,0"]
    assert len(segs) == 2, "each tile has exactly two track segments"
    cols = {seg[2] for seg in segs}
    assert cols == {WHITE_HEX, RED_HEX}, f"segment colours must be the Trax red/white, got {cols}"
    for seg in segs:
        assert all(0 <= seg[i] <= 3 for i in (0, 1)), "edge-mid indices in 0..3"
    print("ok: render emits polygons board + board.tracks {cell:[[a,b,colour]x2]} with #e8e8e8/#d9534f")


def test_random_playouts_terminate():
    g = Trax()
    for seed in range(40):
        s = g.initial_state()
        rng = random.Random(seed)
        steps = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            assert moves, "non-terminal state with no legal moves"
            s = g.apply_move(s, rng.choice(moves))
            steps += 1
            assert steps < 400, "playout did not terminate"
        r = g.returns(s)
        assert len(r) == 2 and all(isinstance(x, float) for x in r)
    print("ok: 40 random playouts terminate with well-formed returns")


def main():
    test_orientations_well_formed()
    test_matching_rule()
    test_forced_move_resolution()
    test_forced_illegal_three_edges()
    test_loop_win_via_apply_move()
    test_winning_line_via_apply_move()
    test_simultaneous_win_mover()
    test_opening_and_legal_count()
    test_serialize_roundtrip()
    test_render_contract()
    test_random_playouts_terminate()
    print("\nALL TRAX SELFTESTS PASSED")


if __name__ == "__main__":
    main()
