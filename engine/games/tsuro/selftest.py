"""Pure-stdlib selftest for Tsuro -- correctness anchors.

Run: PYTHONPATH=. python3 games/tsuro/selftest.py
Imports only `agp` + this game (no python-chess / numpy).
"""

from __future__ import annotations

import random

from games.tsuro.game import (
    Tsuro, TsuroState, DECK, CROSS, build_deck, _rotate_pairs, _all_matchings,
)


def _is_matching(pairs):
    notches = []
    for a, b in pairs:
        notches.extend([a, b])
    return sorted(notches) == list(range(8)) and len(pairs) == 4


def test_deck_count_and_rotation():
    all_m = list(_all_matchings(list(range(8))))
    assert len(all_m) == 105, f"expected 105 perfect matchings, got {len(all_m)}"
    assert len(DECK) == 35, f"deck must have 35 distinct tiles, got {len(DECK)}"
    # every tile is a perfect matching of {0..7}
    for tile in DECK:
        assert _is_matching([tuple(p) for p in tile]), f"not a perfect matching: {tile}"
    # rotation maps n -> (n+2)%8: rotating a tile 4 times returns to itself
    for tile in DECK:
        t = tuple(tuple(p) for p in tile)
        assert _rotate_pairs(t, 4) == tuple(sorted(tuple(sorted(p)) for p in t))
        assert _rotate_pairs(t, 0) == tuple(sorted(tuple(sorted(p)) for p in t))
    # deck is canonical/rotation-closed: every rotation of a deck tile canonicalizes
    # to a deck tile, and no two deck tiles are rotations of each other.
    canon = set()
    for tile in DECK:
        t = tuple(tuple(p) for p in tile)
        best = min(_rotate_pairs(t, k) for k in range(4))
        assert best not in canon, "two deck tiles are rotations of each other"
        canon.add(best)
        for k in range(4):
            rot = _rotate_pairs(t, k)
            rb = min(_rotate_pairs(rot, j) for j in range(4))
            assert rb == best  # rotating stays in the same canonical class
    assert len(canon) == 35
    print("ok: deck = 35 distinct tiles, each a perfect matching; rotation n->(n+2)%8")


def test_cross_mapping():
    # cross mapping is an involution on (cell-relative) notches: exit n then the
    # reverse should come back. exit 0 -> neighbour @5; from that neighbour, exit
    # 5 must return to the original cell @0.
    pairs = [(0, 5), (1, 4), (2, 7), (3, 6)]
    for ex, (dc, dr, en) in CROSS.items():
        # the reverse: leaving the neighbour through `en` returns to origin
        rdc, rdr, ren = CROSS[en]
        assert (rdc, rdr) == (-dc, -dr), f"cross not reversible at {ex}"
        assert ren == ex
    print("ok: cross-cell notch mapping is a consistent involution")


def test_path_following_multi_tile():
    g = Tsuro()
    # Build a straight horizontal corridor across three cells using tiles that
    # connect left-notch 6 to right-notch 3 (enter left-bottom -> exit right-bottom).
    # notch 6 (left,bottom) <-> we want it to exit on the right side. Choose a tile
    # pair {6,3}: enter at 6, exit at 3 (right side, bottom third). CROSS[3] ->
    # (c+1, r) enter @6, so it lines up across cells.
    placed = {
        (1, 1): [[6, 3], [0, 5], [1, 4], [2, 7]],
        (2, 1): [[6, 3], [0, 5], [1, 4], [2, 7]],
        (3, 1): [[6, 3], [0, 5], [1, 4], [2, 7]],
    }
    # a marker resting on the left edge of cell (1,1) at notch 6, riding right.
    fc, fn, elim = g._follow(placed, (1, 1), 6)
    # after three tiles it exits (3,1) through notch 3 -> CROSS[3] -> (4,1) @6,
    # which is empty & on-board, so it rests at (4,1) notch 6.
    assert not elim, "should not be eliminated"
    assert fc == (4, 1) and fn == 6, f"expected rest at (4,1)/6, got {fc}/{fn}"
    print("ok: path-following across 3 placed tiles reaches the right exit notch")


def test_carried_off_edge_eliminates():
    g = Tsuro()
    # A marker on the bottom edge cell (2,0) with a tile that exits the bottom
    # (notch 4 or 5). Enter at notch 0 (top), exit at notch 5 (bottom). CROSS[5]
    # -> (2,-1) which is off-board => eliminated.
    placed = {(2, 0): [[0, 5], [1, 4], [2, 7], [3, 6]]}
    fc, fn, elim = g._follow(placed, (2, 0), 0)
    assert elim, f"should be carried off, got {fc}/{fn} elim={elim}"
    print("ok: a token carried off the board edge is eliminated")


def test_no_suicide_unless_forced():
    g = Tsuro()
    # Construct a state where the mover (seat 0) has ONE non-suicidal option among
    # several -> only safe moves are offered. Place seat 0 on a bottom edge cell.
    # Hand tile A exits the bottom (suicide); tile B turns inward (safe).
    suicide = [[0, 5], [1, 4], [2, 7], [3, 6]]   # entering 0 -> exits 5 (off bottom)
    safe = [[0, 2], [1, 3], [4, 6], [5, 7]]      # entering 0 -> exits 2 (right, stays on)
    s = TsuroState(
        placed={},
        tokens={0: ((2, 0), 0), 1: ((5, 5), 1)},   # seat0 on bottom-edge cell, enters at notch 0
        hands={0: [suicide, safe], 1: [[[0, 5], [1, 4], [2, 7], [3, 6]]]},
        deck=[], to_move=0, ply=0, winner=None,
    )
    moves = g.legal_moves(s)
    # all offered moves must keep seat 0 alive
    for mv in moves:
        cid, choice = mv.split("=")
        hi, rot = (int(x) for x in choice.split("."))
        oriented = [list(p) for p in _rotate_pairs(s.hands[0][hi], rot)]
        _p, ends, _w = g._resolve_placement(s, (2, 0), oriented)
        assert ends[0] is not None, f"offered a self-eliminating move: {mv}"
    assert moves, "should have at least one safe move"
    # Now force suicide: give seat 0 only suicidal tiles -> moves still non-empty
    s2 = TsuroState(
        placed={}, tokens={0: ((2, 0), 0), 1: ((5, 5), 1)},
        hands={0: [suicide], 1: [suicide]}, deck=[], to_move=0, ply=0, winner=None,
    )
    forced = g.legal_moves(s2)
    assert forced, "must still offer a move when every option is suicidal"
    print("ok: no-suicide-unless-forced filter works (and falls back when forced)")


def test_collision_eliminates_both():
    g = Tsuro()
    # Two markers about to be routed onto the SAME notch by one placement.
    # Seat 0 at cell (2,2) notch 0; seat 1 at cell (2,2) notch ... they can't share
    # a cell start. Instead: seat0 rides into rest notch X; seat1 already rests at X.
    # Place a tile under seat0 that carries it onto seat1's resting (cell,notch).
    # seat1 rests on (3,2) notch 6 (empty cell, on-board). seat0 at (2,2) enters
    # at notch 0 and we give it tile {0,3}: exit 3 -> CROSS[3] -> (3,2) @6 == seat1.
    s = TsuroState(
        placed={},
        tokens={0: ((2, 2), 0), 1: ((3, 2), 6)},
        hands={0: [[[0, 3], [1, 2], [4, 6], [5, 7]]], 1: [[[0, 5], [1, 4], [2, 7], [3, 6]]]},
        deck=[], to_move=0, ply=0, winner=None,
    )
    oriented = [list(p) for p in s.hands[0][0]]
    _p, ends, winner = g._resolve_placement(s, (2, 2), oriented)
    assert ends[0] is None and ends[1] is None, f"both should die, got {ends}"
    assert winner == "draw", f"simultaneous elimination -> draw, got {winner}"
    print("ok: a collision eliminates both markers (here -> draw)")


def test_win_and_draw_via_apply_move():
    g = Tsuro()
    # Last-standing win: seat 0 places safely, seat 1 is routed off the board.
    # seat1 at (5,5) notch... give seat1 a forced suicide later; simpler: build a
    # state where seat 0's placement sends seat 1 off-board. But a placement only
    # goes on the MOVER's cell. So: it is seat 1's turn and every seat-1 tile is a
    # suicide -> seat 1 eliminates itself -> seat 0 wins.
    suicide = [[0, 5], [1, 4], [2, 7], [3, 6]]   # enter 0 -> exit 5 -> off bottom
    s = TsuroState(
        placed={},
        tokens={0: ((1, 3), 0), 1: ((2, 0), 0)},   # seat1 on a bottom-edge cell
        hands={0: [suicide], 1: [suicide]},
        deck=[], to_move=1, ply=0, winner=None,
    )
    mv = g.legal_moves(s)[0]
    s2 = g.apply_move(s, mv)
    assert g.is_terminal(s2), "should be terminal after the last opponent dies"
    assert s2.winner == 0, f"seat 0 should win, got {s2.winner}"
    assert g.returns(s2) == [1.0, -1.0]
    print("ok: last-standing win via apply_move")

    # Simultaneous-elimination draw via apply_move. Force the collision by making
    # it seat 0's ONLY non-... move: a symmetric tile {0-3,1-2,4-7,5-6} placed on
    # cell (2,2) entering at notch 0. Whatever rotation, seat 0 follows to a single
    # destination; we pre-seat seat 1 exactly on that destination so EVERY rotation
    # collides -> the no-suicide filter (all unsafe) falls back to all, and apply
    # yields a draw.
    tile0 = [[0, 3], [1, 2], [4, 7], [5, 6]]      # enter 0 -> exit 3 -> (3,2)@6
    sd = TsuroState(
        placed={},
        tokens={0: ((2, 2), 0), 1: ((3, 2), 6)},
        hands={0: [tile0], 1: [suicide]},
        deck=[], to_move=0, ply=0, winner=None,
    )
    md = g.legal_moves(sd)
    # confirm the chosen (rotation-0) move collides
    s3 = g.apply_move(sd, "2,2=0.0")
    assert g.is_terminal(s3) and s3.winner == "draw", f"expected draw, got {s3.winner}"
    assert g.returns(s3) == [0.0, 0.0]
    assert md, "a forced collision must still be offered"
    print("ok: simultaneous-elimination draw via apply_move")


def test_serialize_roundtrip():
    g = Tsuro()
    s = g.initial_state(rng=random.Random(7))
    # play a few moves to populate placed/hands/deck/tokens
    for _ in range(5):
        if g.is_terminal(s):
            break
        s = g.apply_move(s, g.legal_moves(s)[0], rng=random.Random(99))
    d = g.serialize(s)
    s2 = g.deserialize(d)
    assert g.serialize(s2) == d, "serialize did not round-trip"
    import json
    json.dumps(d)  # must be JSON-able
    # fields preserved
    assert s2.to_move == s.to_move and s2.ply == s.ply and s2.winner == s.winner
    assert len(s2.deck) == len(s.deck)
    assert s2.tokens == s.tokens
    print("ok: serialize round-trips (placed/tokens/hands/deck/pointer)")


def test_random_playouts_terminate():
    g = Tsuro()
    for seed in range(30):
        s = g.initial_state(rng=random.Random(seed))
        rng = random.Random(seed + 1000)
        steps = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            assert moves, "non-terminal state with no legal moves"
            s = g.apply_move(s, rng.choice(moves), rng=rng)
            steps += 1
            assert steps < 500, "playout did not terminate"
        r = g.returns(s)
        assert len(r) == 2 and all(isinstance(x, float) for x in r)
    print("ok: 30 random playouts terminate with well-formed returns")


def main():
    # sanity: build_deck is deterministic
    assert build_deck() == DECK
    test_deck_count_and_rotation()
    test_cross_mapping()
    test_path_following_multi_tile()
    test_carried_off_edge_eliminates()
    test_no_suicide_unless_forced()
    test_collision_eliminates_both()
    test_win_and_draw_via_apply_move()
    test_serialize_roundtrip()
    test_random_playouts_terminate()
    print("\nALL TSURO SELFTESTS PASSED")


if __name__ == "__main__":
    main()
