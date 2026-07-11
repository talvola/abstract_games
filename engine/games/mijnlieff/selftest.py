"""Pure-stdlib correctness anchor for Mijnlieff. Run by tests/test_games.py and
standalone:  PYTHONPATH=. python3 games/mijnlieff/selftest.py

Anchors (official Hopwood Games rules sheet, cross-checked vs
iamkate.com/data/mijnlieff/):
  * opening restricted to the 12 outside (edge) squares;
  * each tile type's exact constraint set (Straights = row/column,
    Diagonals = diagonal, Pullers = the 8 touching squares, Pushers = the
    non-touching squares), with intervening tiles NOT blocking lines;
  * forced pass -> the other player places freely;
  * end trigger: last tile placed -> opponent gets exactly ONE final tile,
    forsaken on a pass;
  * scoring: 1 pt per consecutive line of 3, a line of 4 = 2 pts, interrupted
    lines score nothing; equal score = draw;
  * serialize round-trip; 500 random playouts terminate within 16 placements.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.mijnlieff.game import Mijnlieff, MState, TYPES  # noqa: E402


def _state(board=None, hands=None, to_move=0, constraint=None,
           last_chance=False, finished=False):
    g = Mijnlieff()
    s = g.initial_state()
    if board is not None:
        s.board = dict(board)
    if hands is not None:
        s.hands = {p: dict(h) for p, h in hands.items()}
    s.to_move = to_move
    s.constraint = constraint
    s.last_chance = last_chance
    s.finished = finished
    return s


def _target_cells(g, s):
    """The set of (c, r) cells appearing in the current legal moves."""
    out = set()
    for m in g.legal_moves(s):
        cell = m.split("@")[1]
        c, r = cell.split(",")
        out.add((int(c), int(r)))
    return out


def test_opening_edge_only():
    g = Mijnlieff()
    s = g.initial_state()
    cells = _target_cells(g, s)
    edge = {(c, r) for c in range(4) for r in range(4)
            if c in (0, 3) or r in (0, 3)}
    assert cells == edge, cells                      # exactly the 12 edge squares
    assert (1, 1) not in cells and (2, 2) not in cells
    # 12 squares x 4 available types = 48 distinct opening moves.
    ms = g.legal_moves(s)
    assert len(ms) == 48 and len(set(ms)) == 48, len(ms)


def test_straight_constraint():
    """Straights: opponent must play in the same row or column, any distance."""
    g = Mijnlieff()
    s = g.apply_move(g.initial_state(), "S@0,0")
    assert s.to_move == 1
    want = {(1, 0), (2, 0), (3, 0), (0, 1), (0, 2), (0, 3)}
    assert _target_cells(g, s) == want, _target_cells(g, s)


def test_diagonal_constraint():
    """Diagonals: opponent must play on a diagonal through the tile."""
    g = Mijnlieff()
    s = g.apply_move(g.initial_state(), "D@1,0")     # edge square
    want = {(0, 1), (2, 1), (3, 2)}                  # both diagonals from (1,0)
    assert _target_cells(g, s) == want, _target_cells(g, s)
    # From a corner: the single long diagonal.
    s2 = g.apply_move(g.initial_state(), "D@0,0")
    assert _target_cells(g, s2) == {(1, 1), (2, 2), (3, 3)}


def test_puller_constraint():
    """Pullers: opponent must play on one of the 8 touching squares."""
    g = Mijnlieff()
    s = g.apply_move(g.initial_state(), "L@0,0")
    assert _target_cells(g, s) == {(1, 0), (0, 1), (1, 1)}
    s2 = g.apply_move(g.initial_state(), "L@1,0")    # edge, 5 neighbours
    assert _target_cells(g, s2) == {(0, 0), (2, 0), (0, 1), (1, 1), (2, 1)}


def test_pusher_constraint():
    """Pushers: opponent must play on an empty square NOT touching the tile."""
    g = Mijnlieff()
    s = g.apply_move(g.initial_state(), "P@0,0")
    all_cells = {(c, r) for c in range(4) for r in range(4)}
    want = all_cells - {(0, 0), (1, 0), (0, 1), (1, 1)}
    assert _target_cells(g, s) == want, _target_cells(g, s)   # 12 squares


def test_intervening_pieces_do_not_block():
    """'Intervening pieces do not block your path' -- a straight line reaches
    past an occupied square."""
    g = Mijnlieff()
    # (1,0) is occupied; player 0 constrained by a Straight at (0,0).
    s = _state(board={(0, 0): (1, "S"), (1, 0): (0, "L")},
               to_move=0, constraint=("S", 0, 0))
    cells = _target_cells(g, s)
    assert (2, 0) in cells and (3, 0) in cells       # beyond the blocker
    assert (1, 0) not in cells                       # occupied itself
    # Same for diagonals.
    s2 = _state(board={(0, 0): (1, "D"), (1, 1): (0, "L")},
                to_move=0, constraint=("D", 0, 0))
    cells2 = _target_cells(g, s2)
    assert (2, 2) in cells2 and (3, 3) in cells2 and (1, 1) not in cells2


def test_constraint_is_next_turn_only():
    """A tile constrains only the very next placement -- afterwards only the
    newest tile matters."""
    g = Mijnlieff()
    s = g.apply_move(g.initial_state(), "S@0,0")     # Red Straight
    s = g.apply_move(s, "L@0,3")                     # Blue Puller in the column
    # Red is now constrained ONLY by the Puller at (0,3) -- not the old Straight.
    assert _target_cells(g, s) == {(0, 2), (1, 2), (1, 3)}


def test_forced_pass_gives_free_placement():
    """No legal square for the opponent => they pass; the mover plays again,
    into ANY empty square."""
    g = Mijnlieff()
    # Free placement (constraint None) with (0,0)'s neighbours all full; Red
    # plays a Puller into the corner -> Blue has no touching square -> pass.
    board = {(1, 0): (1, "S"), (0, 1): (1, "D"), (1, 1): (0, "S")}
    hands = {0: {"S": 1, "D": 2, "P": 2, "L": 2},
             1: {"S": 1, "D": 1, "P": 2, "L": 2}}
    s = _state(board=board, hands=hands, to_move=0, constraint=None)
    assert "L@0,0" in g.legal_moves(s)
    ns = g.apply_move(s, "L@0,0")
    assert not g.is_terminal(ns)
    assert ns.to_move == 0, ns.to_move               # Red moves AGAIN
    assert ns.constraint is None                     # free placement
    assert ns.just_passed == 1
    # Free placement = every empty square is a target.
    empties = {(c, r) for c in range(4) for r in range(4)} - set(ns.board)
    assert _target_cells(g, ns) == empties


def test_end_trigger_one_last_tile():
    """Placing your last tile gives the opponent exactly ONE more placement."""
    g = Mijnlieff()
    hands = {0: {"S": 1, "D": 0, "P": 0, "L": 0},    # Red's very last tile
             1: {"S": 0, "D": 0, "P": 2, "L": 1}}    # Blue still holds 3
    s = _state(board={(3, 3): (1, "P")}, hands=hands, to_move=0,
               constraint=("P", 3, 3))
    mv = "S@0,0"
    assert mv in g.legal_moves(s)
    ns = g.apply_move(s, mv)
    assert not g.is_terminal(ns)
    assert ns.to_move == 1 and ns.last_chance        # ONE last chance
    # Blue plays one tile -> game over, even though Blue holds 2 more.
    mv2 = g.legal_moves(ns)[0]
    fs = g.apply_move(ns, mv2)
    assert g.is_terminal(fs)
    assert sum(fs.hands[1].values()) == 2            # unplayed tiles remain
    assert g.legal_moves(fs) == []


def test_end_trigger_final_chance_forsaken_on_pass():
    """If the opponent would have to pass on their last chance, the game just
    ends."""
    g = Mijnlieff()
    # Red's last tile is a Puller into corner (0,0) whose neighbours are full:
    # Blue's one last chance is forsaken -> immediate game over.
    board = {(1, 0): (1, "S"), (0, 1): (1, "D"), (1, 1): (0, "S")}
    hands = {0: {"S": 0, "D": 0, "P": 0, "L": 1},
             1: {"S": 1, "D": 1, "P": 2, "L": 2}}
    s = _state(board=board, hands=hands, to_move=0, constraint=None)
    ns = g.apply_move(s, "L@0,0")
    assert g.is_terminal(ns), "final chance must be forsaken on a pass"


def test_scoring_windows():
    g = Mijnlieff()
    # Row of 3 = 1 point.
    assert g._score({(0, 0): (0, "S"), (1, 0): (0, "D"), (2, 0): (0, "L")}, 0) == 1
    # Row of 4 = 2 points (two overlapping windows of 3).
    b4 = {(c, 0): (0, "S") for c in range(4)}
    assert g._score(b4, 0) == 2
    # Column of 3 = 1 point.
    assert g._score({(2, 1): (1, "S"), (2, 2): (1, "P"), (2, 3): (1, "L")}, 1) == 1
    # Main diagonal of 4 = 2; short (offset) diagonal of 3 = 1.
    bd = {(i, i): (0, "S") for i in range(4)}
    assert g._score(bd, 0) == 2
    assert g._score({(0, 1): (0, "S"), (1, 2): (0, "D"), (2, 3): (0, "P")}, 0) == 1
    # Anti-diagonal of 3.
    assert g._score({(3, 0): (0, "S"), (2, 1): (0, "D"), (1, 2): (0, "P")}, 0) == 1
    # Interrupted lines score nothing: gap, or an opposing tile in between.
    assert g._score({(0, 0): (0, "S"), (1, 0): (0, "D"), (3, 0): (0, "L")}, 0) == 0
    assert g._score({(0, 0): (0, "S"), (1, 0): (1, "D"),
                     (2, 0): (0, "L"), (3, 0): (0, "P")}, 0) == 0
    # PDF example arithmetic: one line of 4 + two lines of 3 = 4 points.
    bx = {(c, 0): (0, "S") for c in range(4)}        # row of 4 -> 2
    bx.update({(0, 1): (0, "D"), (0, 2): (0, "L")})  # col 0 run of 3 -> 1
    bx.update({(3, 1): (0, "P"), (2, 2): (0, "P"),
               (1, 3): (0, "P")})                    # anti-diag run of 3 -> 1
    assert g._score(bx, 0) == 4, g._score(bx, 0)


def test_returns_win_and_draw():
    g = Mijnlieff()
    # Red has a row of 3, Blue nothing -> Red wins.
    s = _state(board={(0, 0): (0, "S"), (1, 0): (0, "D"), (2, 0): (0, "L"),
                      (3, 3): (1, "P")}, finished=True)
    assert g.returns(s) == [1.0, -1.0]
    # Equal scores -> honest draw.
    s2 = _state(board={(0, 0): (0, "S"), (3, 3): (1, "P")}, finished=True)
    assert g.scores(s2) == [0, 0]
    assert g.returns(s2) == [0.0, 0.0]


def test_serialize_roundtrip():
    import json
    g = Mijnlieff()
    s = g.initial_state()
    s = g.apply_move(s, "S@0,0")
    s = g.apply_move(s, "L@0,3")
    s = g.apply_move(s, "P@1,2")
    d = g.serialize(s)
    json.dumps(d)                                    # JSON-able
    s2 = g.deserialize(d)
    assert s2.board == s.board and s2.hands == s.hands
    assert s2.to_move == s.to_move and s2.constraint == s.constraint
    assert s2.last_cell == s.last_cell
    assert s2.last_chance == s.last_chance and s2.finished == s.finished
    assert g.serialize(s2) == d
    # Reserves reflect placements.
    assert s.hands[0] == {"S": 1, "D": 2, "P": 1, "L": 2}
    assert s.hands[1] == {"S": 2, "D": 2, "P": 2, "L": 1}


def test_random_playouts_terminate():
    import random
    g = Mijnlieff()
    rng = random.Random(20260710)
    results = {"red": 0, "blue": 0, "draw": 0}
    passes = 0
    for _ in range(500):
        s = g.initial_state()
        steps = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            assert moves, "non-terminal state with no moves"
            s = g.apply_move(s, rng.choice(moves))
            if s.just_passed is not None:
                passes += 1
            steps += 1
            assert steps <= 16, steps                # each move = one placement
        r = g.returns(s)
        assert r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])
        results["red" if r[0] > 0 else "blue" if r[1] > 0 else "draw"] += 1
    assert results["red"] and results["blue"] and results["draw"], results
    print(f"  playouts: {results}, forced passes: {passes}")


def run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"mijnlieff selftest: {len(fns)} tests passed")


if __name__ == "__main__":
    run()
