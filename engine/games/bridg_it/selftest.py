"""Standalone correctness anchor for Bridg-It (Game of Gale).

Run: PYTHONPATH=. python3 games/bridg_it/selftest.py

Pure stdlib + the agp package only. There is no published perft for Bridg-It;
the anchor is a set of baked rule asserts on the Shannon-switching ruleset:

  (1) the two interleaved dot grids — Red an N×(N+1) lattice (odd-x/even-y),
      Blue an (N+1)×N lattice (even-x/odd-y); for N=5 that is the classic
      30-dot / 30-dot Hasbro Bridg-It board;
  (2) a move draws a unit EDGE between two orthogonally-adjacent dots of YOUR
      colour, and an edge is illegal if it would CROSS an opponent's already-
      drawn edge (each interior edge crosses exactly one opponent edge, rim
      edges cross none);
  (3) WIN = connect your two opposite sides with a path of your edges (BFS over
      your placed edges), and the game cannot draw.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ENGINE))

from agp import check, load  # noqa: E402

GAME_DIR = ENGINE / "games" / "bridg_it"


def _new(n=5):
    _manifest, game = load(GAME_DIR)
    return game, game.initial_state(options={"size": n})


def test_conformance():
    manifest, game = load(GAME_DIR)
    res = check(game, manifest, games=40)
    assert res.ok, f"conformance failed: {getattr(res, 'errors', res)}"


def test_interleaved_grids():
    """(1) The two dot lattices match the standard Bridg-It geometry."""
    from games.bridg_it.game import _dots, _is_dot, RED, BLUE  # noqa: E402

    reds = _dots(5, RED)
    blues = _dots(5, BLUE)
    # Classic 5x6 / 6x5 interleave -> 30 + 30 dots.
    assert len(reds) == 30, f"expected 30 Red dots, got {len(reds)}"
    assert len(blues) == 30, f"expected 30 Blue dots, got {len(blues)}"
    # Red: 5 columns (odd x) x 6 rows (even y); Blue: 6 columns x 5 rows.
    assert sorted({x for x, y in reds}) == [1, 3, 5, 7, 9]
    assert sorted({y for x, y in reds}) == [0, 2, 4, 6, 8, 10]
    assert sorted({x for x, y in blues}) == [0, 2, 4, 6, 8, 10]
    assert sorted({y for x, y in blues}) == [1, 3, 5, 7, 9]
    # No dot is shared between the colours.
    assert reds.isdisjoint(blues), "dot lattices must not overlap"
    # Parity predicate is exact.
    assert _is_dot(1, 0, RED) and not _is_dot(1, 0, BLUE)
    assert _is_dot(0, 1, BLUE) and not _is_dot(0, 1, RED)


def test_edge_move_between_own_adjacent_dots():
    """(2a) A move is an edge between two orthogonally-adjacent own-colour dots."""
    game, st = _new(5)
    assert game.current_player(st) == 0, "Red moves first"
    moves = game.legal_moves(st)
    # Every legal opening move connects two Red dots 2 apart in one axis.
    from games.bridg_it.game import _parse_edge, _is_dot, RED  # noqa: E402

    for m in moves:
        a, b = _parse_edge(m)
        assert _is_dot(*a, RED) and _is_dot(*b, RED), f"{m}: endpoints must be Red dots"
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        assert (dx, dy) in ((2, 0), (0, 2)), f"{m}: must be a unit edge"
    # A specific Red vertical edge is legal at the start; it is then drawn.
    assert "1,0>1,2" in moves
    st2 = game.apply_move(st, "1,0>1,2")
    assert "1,0>1,2" in st2.red_edges
    assert game.current_player(st2) == 1, "Blue to move next"
    # You cannot redraw an edge you already own.
    st3 = game.apply_move(st2, game.legal_moves(st2)[0])  # any Blue move
    assert "1,0>1,2" not in game.legal_moves(st3), "cannot redraw own edge"


def test_crossing_pairing_is_one_to_one():
    """(2b) Each interior edge crosses exactly one opponent edge; rim edges none."""
    from games.bridg_it.game import (  # noqa: E402
        _potential_edges, _crossing_edge, _edge_key, RED, BLUE,
    )

    red_edges = _potential_edges(5, RED)
    with_partner = 0
    rim = 0
    blue_set = {_edge_key(*b) for b in _potential_edges(5, BLUE)}
    for e in red_edges:
        cross = _crossing_edge(e, RED, 5)
        if cross is None:
            rim += 1
            continue
        with_partner += 1
        # The partner must be a real Blue potential edge, and crossing is mutual.
        assert _edge_key(*cross) in blue_set, "crossing edge must be a valid Blue edge"
        back = _crossing_edge(cross, BLUE, 5)
        assert back is not None and _edge_key(*back) == _edge_key(*e), (
            "crossing relation must be symmetric"
        )
    assert with_partner == 41 and rim == 8, (
        f"expected 41 crossing + 8 rim Red edges, got {with_partner}+{rim}"
    )


def test_crossing_rejection():
    """(2c) An edge is illegal once the opponent edge crossing it is drawn."""
    game, st = _new(5)
    # Red draws horizontal edge 1,2 - 3,2 (midpoint at the cell centred on (2,2)).
    # The Blue edge that crosses it is the vertical 2,1 - 2,3.
    from games.bridg_it.game import _crossing_edge, _edge_key, _parse_edge, RED  # noqa: E402

    red_h = ((1, 2), (3, 2))
    cross = _crossing_edge(red_h, RED, 5)
    assert cross is not None and _edge_key(*cross) == "2,1>2,3", (
        f"crossing of 1,2-3,2 should be 2,1-2,3, got {cross}"
    )
    st = game.apply_move(st, "1,2>3,2")     # Red horizontal
    assert game.current_player(st) == 1
    # Blue must NOT be allowed to draw the crossing vertical edge.
    assert "2,1>2,3" not in game.legal_moves(st), "crossing Blue edge must be rejected"
    assert game.legal_moves(st), "Blue must still have legal moves"
    # Symmetric direction: after Blue takes the crossing slot first, Red cannot.
    game3, st3 = _new(5)
    st3 = game3.apply_move(st3, "1,0>1,2")          # Red somewhere harmless
    st3 = game3.apply_move(st3, "2,1>2,3")          # Blue vertical
    assert "1,2>3,2" not in game3.legal_moves(st3), "crossing Red edge must be rejected"


def test_red_win_by_connection():
    """(3) Red wins by linking top (y=0) to bottom (y=2N) with a chain of edges."""
    game, st = _new(5)
    # Red builds the straight vertical column at x=1: edges 1,0-1,2 / 1,2-1,4 /
    # 1,4-1,6 / 1,6-1,8 / 1,8-1,10. Blue plays harmless edges along its right rim
    # (x=10 verticals never form a left-right chain). Interleave Red/Blue.
    red_chain = ["1,0>1,2", "1,2>1,4", "1,4>1,6", "1,6>1,8", "1,8>1,10"]
    blue_harmless = ["10,1>10,3", "10,3>10,5", "10,5>10,7", "10,7>10,9"]
    for i, rm in enumerate(red_chain):
        assert game.current_player(st) == 0
        assert rm in game.legal_moves(st), f"{rm} should be legal"
        if i == len(red_chain) - 1:
            st = game.apply_move(st, rm)  # completes the chain
            break
        st = game.apply_move(st, rm)
        # Blue plays a harmless reply.
        bm = blue_harmless[i]
        assert bm in game.legal_moves(st), f"{bm} should be legal"
        st = game.apply_move(st, bm)
    assert st.winner == 0, "Red wins by connecting top-bottom"
    assert game.is_terminal(st)
    assert game.returns(st) == [1.0, -1.0]


def test_blue_win_by_connection():
    """(3) Blue wins by linking left (x=0) to right (x=2N)."""
    game, st = _new(5)
    # Blue builds horizontal row at y=1: 0,1-2,1 / 2,1-4,1 / 4,1-6,1 / 6,1-8,1 /
    # 8,1-10,1. Red plays harmless edges along its top rim (y=0 horizontals).
    blue_chain = ["0,1>2,1", "2,1>4,1", "4,1>6,1", "6,1>8,1", "8,1>10,1"]
    red_harmless = ["1,0>3,0", "3,0>5,0", "5,0>7,0", "7,0>9,0", "1,10>3,10"]
    for i in range(5):
        # Red moves first each round.
        rm = red_harmless[i]
        assert game.current_player(st) == 0
        assert rm in game.legal_moves(st), f"{rm} should be legal"
        st = game.apply_move(st, rm)
        bm = blue_chain[i]
        assert game.current_player(st) == 1
        assert bm in game.legal_moves(st), f"{bm} should be legal"
        st = game.apply_move(st, bm)
        if i == 4:
            break
    assert st.winner == 1, "Blue wins by connecting left-right"
    assert game.returns(st) == [-1.0, 1.0]


def test_connect_helper():
    """Direct check of the connection predicate."""
    from games.bridg_it.game import _connects, RED, BLUE  # noqa: E402

    # A full Red vertical column connects top-bottom.
    col = {f"1,{y}>1,{y + 2}" for y in range(0, 10, 2)}
    assert _connects(col, 5, RED), "Red full column connects"
    assert not _connects(col, 5, BLUE), "that column is not a Blue win"
    # A broken column (drop one edge) does not connect.
    broken = set(col) - {"1,4>1,6"}
    assert not _connects(broken, 5, RED), "broken column must not connect"
    # A full Blue horizontal row connects left-right.
    row = {f"{x},1>{x + 2},1" for x in range(0, 10, 2)}
    assert _connects(row, 5, BLUE), "Blue full row connects"
    assert not _connects(row, 5, RED), "that row is not a Red win"


def test_serialize_roundtrip():
    game, st = _new(5)
    st = game.apply_move(st, "1,0>1,2")
    st = game.apply_move(st, "0,1>2,1")
    data = game.serialize(st)
    st2 = game.deserialize(data)
    assert game.serialize(st2) == data, "serialize must round-trip"


def main():
    test_conformance()
    test_interleaved_grids()
    test_edge_move_between_own_adjacent_dots()
    test_crossing_pairing_is_one_to_one()
    test_crossing_rejection()
    test_red_win_by_connection()
    test_blue_win_by_connection()
    test_connect_helper()
    test_serialize_roundtrip()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
