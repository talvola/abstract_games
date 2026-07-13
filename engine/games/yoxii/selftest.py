"""Yoxii correctness anchors (pure stdlib: agp + this game only).

Anchored on the official Cosmoludo rulebook (Yoxii-ML9-25.pdf on cosmoludo.com
and the 1jour-1jeu English rulebook), cross-checked against the BGG description:

* the 37-square OCTAGON board (row widths 3,5,7,7,7,5,3; centre Totem);
* piece stock 5x1 / 5x2 / 5x3 / 3x4 = 18 per player;
* Totem one-step move in all 8 directions to a free square;
* Totem JUMP over a continuous line of >= 1 OWN pieces to the first free square;
* NO jump over an opponent's piece, and none when the landing is blocked/off-board;
* place adjacent to the Totem; place ANYWHERE when it is fully surrounded;
* immobilised Totem -> terminal + value scoring (higher sum wins);
* tie on sum broken by piece count; equal sum AND count -> honest DRAW;
* structural termination (<= 72 plies) over random playouts + serialize round-trip
  + a render-shape probe.

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/yoxii/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.yoxii.game import YoxState, CELLS, CENTER, STOCK, DIRS

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _fmt(p):
    return f"{p[0]},{p[1]}"


def _state(pieces=None, totem=CENTER, stock=None, to_move=0, phase="MOVE"):
    """pieces: {(c,r): (owner, value)}."""
    if stock is None:
        stock = [dict(STOCK), dict(STOCK)]
    return YoxState(pieces=dict(pieces or {}), totem=totem,
                    stock=[dict(stock[0]), dict(stock[1])],
                    to_move=to_move, phase=phase)


def _dests(s):
    """Set of destination cells the Totem can reach from the MOVE-phase state."""
    return {m.split(">")[1] for m in G.legal_moves(s)}


# --------------------------------------------------------------------------
def test_board_geometry():
    """37-square octagon: 7x7 grid with a 3-square notch cut from each corner
    (row widths 3,5,7,7,7,5,3); centre = (3,3)."""
    assert len(CELLS) == 37
    widths = [sum(1 for c in range(7) if (c, r) in CELLS) for r in range(7)]
    assert widths == [3, 5, 7, 7, 7, 5, 3], widths
    for corner in [(0, 0), (1, 0), (0, 1), (5, 0), (6, 0), (6, 1),
                   (0, 5), (0, 6), (1, 6), (6, 5), (5, 6), (6, 6)]:
        assert corner not in CELLS
    assert CENTER == (3, 3) and CENTER in CELLS
    # each octagon row is centred (symmetric about col 3)
    for r in range(7):
        row = sorted(c for c in range(7) if (c, r) in CELLS)
        assert row and row[0] + row[-1] == 6


def test_initial_stock():
    """Each player starts with 5x1, 5x2, 5x3, 3x4 = 18 pieces; Totem centred;
    White (seat 0) to move first."""
    s = G.initial_state()
    assert s.totem == CENTER and s.to_move == 0 and s.phase == "MOVE"
    assert s.stock == [{1: 5, 2: 5, 3: 5, 4: 3}, {1: 5, 2: 5, 3: 5, 4: 3}]
    assert all(sum(h.values()) == 18 for h in s.stock)
    assert not s.pieces and not G.is_terminal(s)


def test_step_eight_directions():
    """On an empty board the centre Totem may step to any of its 8 neighbours."""
    s = _state()
    want = {_fmt((CENTER[0] + dc, CENTER[1] + dr)) for dc, dr in DIRS}
    assert _dests(s) == want and len(want) == 8


def test_jump_over_own_pieces():
    """Jump over a CONTINUOUS line of >= 1 own pieces to the first free square
    beyond (orthogonal and diagonal)."""
    # each direction isolates a case (E: one piece, S: run of two, NW: diagonal)
    pieces = {(4, 3): (0, 1),            # E: own -> jump to (5,3)
              (3, 4): (0, 1), (3, 5): (0, 1),  # S: own run of 2 -> jump to (3,6)
              (2, 2): (0, 1)}            # NW: own -> jump to (1,1)
    s = _state(pieces=pieces)
    d = _dests(s)
    assert "5,3" in d, "jump E over one own piece"
    assert "3,6" in d and "3,5" not in d and "3,4" not in d, "jump S over run of 2"
    assert "1,1" in d, "diagonal NW jump over one own piece"
    # the jumped-over squares are never landing squares
    assert "4,3" not in d and "2,2" not in d


def test_no_jump_over_enemy():
    """It is forbidden to jump over an opponent's piece."""
    # E neighbour is an ENEMY piece: no step (occupied) and no jump past it.
    s = _state(pieces={(4, 3): (1, 2)})
    d = _dests(s)
    assert "4,3" not in d and "5,3" not in d, "cannot jump the enemy piece"
    # a mixed run own-then-enemy: run stops at the enemy (occupied) -> no landing
    s2 = _state(pieces={(4, 3): (0, 1), (5, 3): (1, 1)})
    assert "5,3" not in _dests(s2) and "6,3" not in _dests(s2)


def test_no_jump_when_blocked_or_offboard():
    """No jump when the square beyond the own run is occupied or off the board."""
    # own piece on the E edge cell (5,3) with (6,3) also filled -> nowhere to land
    s = _state(pieces={(5, 3): (0, 1)}, totem=(4, 3))
    assert "6,3" in _dests(s)                       # (6,3) empty -> jump lands
    s2 = _state(pieces={(5, 3): (0, 1), (6, 3): (0, 1)}, totem=(4, 3))
    assert "6,3" not in _dests(s2)                  # (6,3) filled -> no jump E
    # own piece against the board edge with no cell beyond (off-board)
    s3 = _state(pieces={(3, 6): (0, 1)}, totem=(3, 5))
    d3 = _dests(s3)
    assert "3,6" not in d3                           # occupied, can't step there
    # (3,7) is off-board so the jump has no landing square
    assert all(not m.endswith(">3,7") for m in G.legal_moves(s3))


def test_place_adjacent_then_anywhere():
    """After moving, place a piece of a chosen value on a free square around the
    Totem; if all surrounding squares are occupied, place anywhere free."""
    s = _state()
    s2 = G.apply_move(s, "3,3>3,4")                 # step S; totem now (3,4)
    assert s2.phase == "PLACE" and s2.to_move == 0
    place_cells = {m.split("=")[0] for m in G.legal_moves(s2)}
    want = {_fmt((3 + dc, 4 + dr)) for dc, dr in DIRS
            if (3 + dc, 4 + dr) in CELLS}
    assert place_cells == want                       # only around the Totem
    # every value the player holds is offered on each cell
    vals = {m.split("=")[1] for m in G.legal_moves(s2)}
    assert vals == {"1", "2", "3", "4"}
    s3 = G.apply_move(s2, "3,3=3")                   # drop a Y on the vacated cell
    assert s3.pieces[(3, 3)] == (0, 3)
    assert s3.stock[0][3] == 4 and s3.to_move == 1 and s3.phase == "MOVE"

    # fully-surrounded Totem -> placement goes anywhere free on the board
    surround = {(3 + dc, 4 + dr): (1, 1) for dc, dr in DIRS
                if (3 + dc, 4 + dr) in CELLS}
    surround[(0, 3)] = (0, 1)                        # a lone far-away free marker
    sp = _state(pieces=surround, totem=(3, 4), phase="PLACE", to_move=0)
    cells = {m.split("=")[0] for m in G.legal_moves(sp)}
    free = {_fmt(c) for c in CELLS if c not in surround and c != (3, 4)}
    assert cells == free and _fmt((3, 4)) not in cells


def test_immobilised_scoring_and_terminal():
    """Totem fully blocked -> terminal; higher summed value of surrounding pieces
    wins. Build a full board so the Totem cannot step or jump."""
    pieces = _full_board_except_center(
        # 8 neighbours of centre (3,3): White strong, Red weak
        {(2, 2): (0, 4), (3, 2): (0, 3), (4, 2): (0, 1),
         (2, 3): (1, 1), (4, 3): (1, 1),
         (2, 4): (1, 2), (3, 4): (1, 1), (4, 4): (1, 1)})
    s = _state(pieces=pieces, totem=CENTER, phase="MOVE")
    assert G.is_terminal(s), "a full board immobilises the Totem"
    assert G.legal_moves(s) == []
    val, cnt = G._scores(s)
    assert val == [8, 6] and cnt == [3, 5]           # White 4+3+1, Red 1+1+2+1+1
    assert G.returns(s) == [1.0, -1.0]               # higher sum wins


def test_tiebreak_by_piece_count():
    """Equal summed value -> the player with MORE surrounding pieces wins."""
    neigh = {(2, 2): (0, 4), (3, 2): (0, 4), (4, 2): (0, 1),   # White 9 in 3 pcs
             (2, 3): (1, 2), (4, 3): (1, 2), (2, 4): (1, 2),   # Red 9 in 5 pcs
             (3, 4): (1, 2), (4, 4): (1, 1)}
    s = _state(pieces=_full_board_except_center(neigh), totem=CENTER, phase="MOVE")
    val, cnt = G._scores(s)
    assert val == [9, 9], val
    assert cnt == [3, 5], cnt
    assert G.is_terminal(s)
    assert G.returns(s) == [-1.0, 1.0]               # tie on value -> more pieces


def test_honest_draw():
    """Equal summed value AND equal piece count around the Totem -> honest DRAW."""
    neigh = {(2, 2): (0, 3), (3, 2): (0, 1),         # White: 3+1+...
             (2, 3): (0, 2), (4, 3): (0, 2),         # White total: 3+1+2+2 = 8, 4 pcs
             (2, 4): (1, 2), (3, 4): (1, 2),         # Red: 2+2+3+1 = 8, 4 pcs
             (4, 2): (1, 3), (4, 4): (1, 1)}
    pieces = _full_board_except_center(neigh)
    s = _state(pieces=pieces, totem=CENTER, phase="MOVE")
    val, cnt = G._scores(s)
    assert val == [8, 8] and cnt == [4, 4]
    assert G.is_terminal(s)
    assert G.returns(s) == [0.0, 0.0]                # honest draw


def test_termination_and_roundtrip():
    """Random playouts: legal_moves non-empty until terminal, structural
    termination <= 72 plies, serialize round-trips. Print stats."""
    rng = random.Random(11)
    wins = [0, 0]
    draws = 0
    plies = []
    for g in range(300):
        s = G.initial_state()
        n = 0
        while not G.is_terminal(s):
            moves = G.legal_moves(s)
            assert moves, "non-terminal state with no legal moves"
            s = G.apply_move(s, rng.choice(moves))
            n += 1
            assert n <= 72, "exceeded the structural 72-ply bound"
        if g % 20 == 0:
            d = G.serialize(s)
            assert G.serialize(G.deserialize(d)) == d
        r = G.returns(s)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)
        plies.append(n)
        if r == [0.0, 0.0]:
            draws += 1
        else:
            wins[0 if r[0] > 0 else 1] += 1
    assert wins[0] + wins[1] + draws == 300
    print(f"  playouts: 300 games, White {wins[0]} / Red {wins[1]} / "
          f"draws {draws}, avg plies {sum(plies) / len(plies):.1f}, "
          f"max {max(plies)}")


def test_render_shape():
    """Render probe: 37 polygon cells, a neutral Totem disc, labelled pieces,
    stock trays."""
    s = G.initial_state()
    s = G.apply_move(s, G.legal_moves(s)[0])         # move
    s = G.apply_move(s, G.legal_moves(s)[0])         # place
    spec = G.render(s)
    assert spec["board"]["type"] == "polygons"
    assert len(spec["board"]["cells"]) == 37
    assert all(len(c["points"]) == 4 for c in spec["board"]["cells"])
    totems = [p for p in spec["pieces"] if p["owner"] == 2]
    assert len(totems) == 1 and totems[0]["label"] == "T" and totems[0].get("fill")
    placed = [p for p in spec["pieces"] if p["owner"] != 2]
    assert len(placed) == 1 and placed[0]["label"] in ("O", "II", "Y", "X")
    assert set(spec["reserve"]) == {"0", "1"}
    assert spec["caption"]


# --------------------------------------------------------------------------
def _full_board_except_center(neigh):
    """Fill every non-centre cell with a piece so the centre Totem is fully
    immobilised. `neigh` fixes chosen (owner,value) on specific cells (all 8
    neighbours of the centre must be listed for a well-defined score); every
    other non-centre cell gets a harmless filler."""
    pieces = {}
    filler_owner = 0
    for c in sorted(CELLS):
        if c == CENTER:
            continue
        if c in neigh:
            pieces[c] = neigh[c]
        else:
            pieces[c] = (filler_owner, 1)
            filler_owner ^= 1
    return pieces


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        print(f"{t.__name__} ...")
        t()
    print(f"yoxii selftest: {len(tests)} tests passed")
