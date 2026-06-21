"""Standalone correctness anchor for Tanbo (Mark Steere, 1993 / 2026).

Run: PYTHONPATH=. python3 games/tanbo/selftest.py

Pure stdlib + the agp package only (NO third-party libraries, NO long self-play
loops): it is run by the shared test suite under the system python3. Prints
"SELFTEST OK" and exits 0 on success, nonzero on failure.

There is no published perft / node count for Tanbo, so the anchor is conformance
plus a battery of hand-built rule positions that pin down Tanbo's distinctive
mechanics (which differ from ordinary Go liberties):

  * the 2026 dense starting layout (single-stone roots on the even sublattice);
  * PLACEMENT legality -- a stone must touch EXACTLY ONE of your own stones
    (not zero, not two);
  * a root that can no longer grow (is "bounded") is PRUNED -- here, bounding an
    opponent's last root annihilates it and wins;
  * CURRENT-ROOT self-capture: growing your own root into a bounded shape removes
    YOUR root (Steere's Fig 3 -- this is legal and mandatory, not forbidden);
  * CURRENT-ROOT precedence: when your placement bounds your own current root,
    only it is removed -- other simultaneously-bounded roots survive (Fig 3);
  * WIN by annihilation == last-player-able-to-keep-a-root; a player with no
    legal move (no root left to grow) loses.
"""

from __future__ import annotations

import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ENGINE))

from agp import check, load  # noqa: E402
from games.tanbo.game import (  # noqa: E402
    Tanbo,
    TanboState,
    _can_grow,
    _group,
    _resolve,
    _seed_layout,
)

GAME_DIR = ENGINE / "games" / "tanbo"


def test_conformance():
    manifest, game = load(GAME_DIR)
    res = check(game, manifest, games=20)
    assert res.ok, f"conformance failed: {getattr(res, 'errors', res)}"


def test_initial_layout():
    """Dense 2026 opening: single-stone roots on the even sublattice, coloured by
    (i+j)%2, with one empty point between adjacent stones. Black moves first."""
    _m, game = load(GAME_DIR)
    s = game.initial_state(options={"size": 11})
    assert game.current_player(s) == 0, "Black moves first"
    assert not game.is_terminal(s)
    # 11x11 even sublattice {0,2,4,6,8,10} -> 6x6 = 36 seeds, 18 black + 18 white.
    assert len(s.board) == 36, f"expected 36 seeds, got {len(s.board)}"
    blacks = sum(1 for v in s.board.values() if v == 0)
    whites = sum(1 for v in s.board.values() if v == 1)
    assert (blacks, whites) == (18, 18), f"expected 18/18, got {blacks}/{whites}"
    # Stones only on even points; colour = (c//2 + r//2) % 2.
    for (c, r), v in s.board.items():
        assert c % 2 == 0 and r % 2 == 0, f"seed off the even sublattice: {(c, r)}"
        assert v == (c // 2 + r // 2) % 2, f"seed colour wrong at {(c, r)}"
    # No two seeds are orthogonally adjacent (each is an isolated single-stone root).
    for (c, r) in s.board:
        for nb in [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]:
            assert nb not in s.board, f"seeds adjacent at {(c, r)}/{nb}"
    # Layout helper agrees with initial_state.
    assert _seed_layout(11) == s.board


def test_placement_exactly_one_own():
    """A placement is legal iff it is adjacent to EXACTLY ONE of the mover's own
    stones (Steere's core placement rule). Zero or two-or-more is illegal."""
    game = Tanbo()
    N = 5
    # Single black stone: its 4 orthogonal neighbours are the only legal moves.
    s = TanboState(size=N, board={(2, 2): 0}, to_move=0)
    assert set(game.legal_moves(s)) == {"1,2", "3,2", "2,1", "2,3"}
    # An empty point adjacent to NO black stone is illegal (e.g. far corner).
    assert "0,0" not in game.legal_moves(s)
    # Two black stones with a gap: the gap point touches BOTH -> illegal.
    s2 = TanboState(size=N, board={(2, 2): 0, (2, 4): 0}, to_move=0)
    assert "2,3" not in game.legal_moves(s2), "adjacent-to-two-own must be illegal"
    # ...but a point touching exactly one of them is legal.
    assert "2,1" in game.legal_moves(s2)


def test_bound_opponent_root_wins():
    """Bounding the opponent's last root prunes it -> annihilation win.

    White has a single-stone corner root at (4,4). Black already brackets it on
    one side; Black plays the point that brackets the other side, after which the
    White root has no empty point it could grow into -> it is bounded -> removed.
    White is annihilated, so Black (the mover) wins immediately.
    """
    game = Tanbo()
    N = 5
    board = {(2, 4): 0, (4, 3): 0, (4, 4): 1}
    s = TanboState(size=N, board=board, to_move=0)
    assert "3,4" in game.legal_moves(s), "the bracketing growth move must be legal"
    nb = _resolve(board, 3, 4, 0, N)
    assert all(v != 1 for v in nb.values()), "White root must be pruned (bounded)"
    st = game.apply_move(s, "3,4")
    assert st.winner == 0, "Black wins by annihilating White"
    assert game.is_terminal(st)
    assert game.returns(st) == [1.0, -1.0]


def test_current_root_self_capture():
    """Growing your own root into a bounded shape removes YOUR current root.

    This is Steere's 'current root capture' (Fig 3): legal and MANDATORY, not a
    forbidden suicide. Black has a stone at (1,0) hemmed in by White; Black's only
    growth, to (0,0), leaves the 2-stone Black root with nowhere to grow -> it is
    bounded -> Black's own root is removed.
    """
    game = Tanbo()
    N = 5
    board = {(1, 0): 0, (2, 0): 1, (0, 1): 1, (1, 1): 1, (2, 1): 1}
    s = TanboState(size=N, board=board, to_move=0)
    assert "0,0" in game.legal_moves(s), "the self-bounding growth is a legal placement"
    nb = _resolve(board, 0, 0, 0, N)
    assert all(v != 0 for v in nb.values()), "Black's own current root must be removed"
    # White is untouched by a current-root capture.
    assert {k for k, v in nb.items() if v == 1} == {(2, 0), (0, 1), (1, 1), (2, 1)}


def test_current_root_precedence():
    """When the placement bounds the CURRENT root, ONLY it is removed -- any other
    root that is also bounded survives this turn (Steere Fig 3 wording)."""
    game = Tanbo()
    N = 5
    # Black root {(3,3)} walled so growing to (4,3) self-bounds it; plus an
    # already-bounded White stone at (0,0) hemmed by Black (1,0),(0,1).
    board = {
        (3, 3): 0, (4, 2): 1, (3, 4): 1, (4, 4): 1, (2, 3): 1, (3, 2): 1,
        (0, 0): 1, (1, 0): 0, (0, 1): 0,
    }
    s = TanboState(size=N, board=board, to_move=0)
    assert "4,3" in game.legal_moves(s)
    nb = _resolve(board, 4, 3, 0, N)
    # Current black root removed...
    assert (3, 3) not in nb and (4, 3) not in nb, "current root must be removed"
    # ...but the other (also-bounded) White stone is NOT removed this turn.
    assert nb.get((0, 0)) == 1, "non-current bounded root must survive a current-root capture"


def test_no_legal_move_loses():
    """A player with no root left to grow has no legal move and loses.

    White has a lone stone fully hemmed by Black (it cannot grow). It is White to
    move; White has no legal placement, so White loses.
    """
    game = Tanbo()
    N = 5
    # White (2,2) surrounded on all four sides by Black; Black also has room.
    board = {
        (2, 2): 1,
        (1, 2): 0, (3, 2): 0, (2, 1): 0, (2, 3): 0,
    }
    s = TanboState(size=N, board=board, to_move=1)
    assert game.legal_moves(s) == [], "White (hemmed lone root) has no legal move"
    # Drive it through apply_move from a Black move so no_move_loss is set: build a
    # position where after Black moves, White is to move and stuck. We assert the
    # returns/terminal semantics directly on a constructed no_move_loss state.
    stuck = TanboState(size=N, board=board, to_move=1, no_move_loss=True)
    assert game.is_terminal(stuck)
    assert game.returns(stuck) == [1.0, -1.0], "White to move with no move -> Black wins"


def test_can_grow_predicate():
    """_can_grow encodes 'bounded': a root can grow iff some empty point is
    adjacent to exactly one of its stones and to no other stone of its colour."""
    N = 5
    # A lone black stone in open space can grow.
    assert _can_grow({(2, 2): 0}, _group({(2, 2): 0}, (2, 2), N), N)
    # A black stone whose every neighbour is occupied cannot grow.
    walled = {(2, 2): 0, (1, 2): 1, (3, 2): 1, (2, 1): 1, (2, 3): 1}
    assert not _can_grow(walled, {(2, 2)}, N)
    # Subtlety: an empty point adjacent to TWO stones of the root's colour does
    # NOT count as growth room (placing there would be illegal -- touches two).
    # Black at (1,1) and (3,1) and (2,0): the empty (2,1) touches (1,1),(3,1) both
    # black -> illegal placement; if those are the only empties, root is bounded.
    twotouch = {(1, 1): 0, (3, 1): 0, (2, 0): 0,
                (1, 0): 1, (3, 0): 1, (0, 1): 1, (4, 1): 1,
                (1, 2): 1, (3, 2): 1, (2, 1): None}
    twotouch = {k: v for k, v in twotouch.items() if v is not None}
    # The black root containing (2,0): {(2,0)} only ((1,1)/(3,1) are separate roots).
    root20 = _group(twotouch, (2, 0), N)
    # (2,0) neighbours: (1,0)=W,(3,0)=W,(2,1)=empty. (2,1) touches (1,1)=B,(3,1)=B
    # -> two same-colour stones -> not legal growth -> {(2,0)} is bounded.
    assert root20 == {(2, 0)}
    assert not _can_grow(twotouch, root20, N), "two-touch empty is not growth room"


def test_serialize_roundtrip():
    _m, game = load(GAME_DIR)
    s = game.initial_state(options={"size": 9})
    s = game.apply_move(s, game.legal_moves(s)[0])
    d = game.serialize(s)
    s2 = game.deserialize(d)
    assert game.serialize(s2) == d, "serialize must round-trip"


def main():
    test_conformance()
    test_initial_layout()
    test_placement_exactly_one_own()
    test_bound_opponent_root_wins()
    test_current_root_self_capture()
    test_current_root_precedence()
    test_no_legal_move_loses()
    test_can_grow_predicate()
    test_serialize_roundtrip()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
