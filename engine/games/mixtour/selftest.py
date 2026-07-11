"""Mixtour correctness anchors (pure stdlib: agp + this game only).

Anchored on the designer's official rules & worked examples:
https://spielstein.com/games/mixtour/rules

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/mixtour/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.mixtour.game import MxState, WHITE, RED

_M, G = load_from_dir(Path(__file__).resolve().parent)


def _state(cols, to_move=WHITE, supply=(20, 20), no_takeback=None):
    """cols: {(c,r): "01..."} bottom->top owner digits."""
    board = {cell: tuple(int(ch) for ch in s) for cell, s in cols.items()}
    st = MxState(board=board, supply=list(supply), to_move=to_move,
                 no_takeback=no_takeback)
    st.reps = {G._key(st): 1}
    return st


def test_setup():
    """Empty 5x5 board, 20 pieces each, White starts, 25 entry moves."""
    s = G.initial_state()
    assert s.board == {} and s.supply == [20, 20] and s.to_move == WHITE
    lm = G.legal_moves(s)
    assert sorted(lm) == sorted(f"{c},{r}" for c in range(5) for r in range(5))
    n = G.apply_move(s, "2,2")
    assert n.board[(2, 2)] == (WHITE,) and n.supply == [19, 20]
    assert n.to_move == RED and s.board == {}          # purity


def test_official_example_distance_and_blocking():
    """Designer's worked example: single at e4 may move 3 onto the 3-stack at
    b4; b4 may NOT jump on e4 (distance 3 != height 1); e1 cannot reach b4
    (blocked by d2 and c3)."""
    # a1=(0,0): e4=(4,3), b4=(1,3), e1=(4,0), d2=(3,1), c3=(2,2)
    s = _state({(4, 3): "0", (1, 3): "010", (4, 0): "1", (3, 1): "0", (2, 2): "1"})
    lm = set(G.legal_moves(s))
    assert "4,3>1,3" in lm                              # distance 3 == target height 3
    assert not any(m.startswith("1,3>4,3") for m in lm)  # not the other way round
    assert not any(m.startswith("4,0>1,3") for m in lm)  # blocked path
    # no move may end on an empty square, and entries only target empties
    for m in lm:
        if ">" in m:
            dst = tuple(int(x) for x in m.split(">")[1].split("=")[0].split(","))
            assert dst in s.board
        else:
            assert tuple(int(x) for x in m.split(",")) not in s.board


def test_official_example_height_one_reachable_by_neighbours():
    """A height-1 stack is within reach of all adjacent stacks (distance 1)."""
    s = _state({(1, 1): "0", (0, 0): "11", (1, 0): "1", (2, 2): "001"})
    lm = set(G.legal_moves(s))
    assert "0,0>1,1=1" in lm and "0,0>1,1=2" in lm
    assert "1,0>1,1" in lm and "2,2>1,1=1" in lm


def test_split_any_level_and_order_preserved():
    """Stacks may be split at any level; moved pieces keep their order on top."""
    # src c1=(2,0) = W,R,W (h3); target c3=(2,2) = R,R (h2) at distance 2.
    s = _state({(2, 0): "010", (2, 2): "11"})
    lm = set(G.legal_moves(s))
    assert {"2,0>2,2=1", "2,0>2,2=2", "2,0>2,2=3"} <= lm
    n = G.apply_move(s, "2,0>2,2=2")                   # move top two: (R, W)
    assert n.board[(2, 0)] == (0,)                     # bottom W stays behind
    assert n.board[(2, 2)] == (1, 1, 1, 0)             # R,R + R,W on top, in order


def test_move_any_colour_enter_own_only():
    """You may move stacks of any colour; you may only ENTER your own colour."""
    s = _state({(0, 0): "1", (1, 1): "1"}, to_move=WHITE)   # only Red pieces on board
    lm = set(G.legal_moves(s))
    assert "0,0>1,1" in lm and "1,1>0,0" in lm         # White moves Red's pieces
    n = G.apply_move(s, "3,3")                          # entry places WHITE
    assert n.board[(3, 3)] == (WHITE,)


def test_no_takeback():
    """It is not allowed to effectively take back the opponent's last move."""
    s = _state({(0, 0): "00", (1, 0): "1"}, to_move=WHITE)
    n = G.apply_move(s, "0,0>1,0=1")                   # W moves top piece a1->b1
    assert n.board[(1, 0)] == (1, 0) and n.board[(0, 0)] == (0,)
    lm = set(G.legal_moves(n))
    assert "1,0>0,0=1" not in lm                       # the exact take-back is barred
    assert "1,0>0,0=2" in lm                           # moving BOTH pieces back is not
    # an entry clears the restriction for the following player
    n2 = G.apply_move(n, "4,4")
    assert n2.no_takeback is None


def test_win_top_colour_wins_even_if_opponent_moved():
    """A stack of height 5+ is removed; its TOP piece's owner wins immediately."""
    # White completes a 5-stack with a White top: single W at e5 -> 4-stack at a1.
    s = _state({(0, 0): "1010", (4, 4): "0"})
    n = G.apply_move(s, "4,4>0,0")                     # distance 4 == height 4
    assert n.winner == WHITE and G.is_terminal(n)
    assert G.returns(n) == [1.0, -1.0]
    assert (0, 0) not in n.board                       # scored stack is removed
    assert n.supply == [23, 22]                        # 3 W + 2 R back to reserves
    # White is FORCED-style loss: moving a Red-topped piece onto 4 makes Red win.
    s2 = _state({(0, 0): "1010", (4, 4): "01"})        # e5 = W under, R on top
    n2 = G.apply_move(s2, "4,4>0,0=1")                 # W moves the top (Red) piece
    assert n2.winner == RED and G.returns(n2) == [-1.0, 1.0]


def test_supply_exhaustion_and_double_pass_draw():
    """No entries with an empty supply; must pass with no moves; two passes in
    sequence draw the game (official)."""
    s = _state({(0, 0): "01"}, supply=(0, 0))          # lone stack, nothing to reach
    assert G.legal_moves(s) == ["pass"]
    n = G.apply_move(s, "pass")
    assert not G.is_terminal(n) and G.legal_moves(n) == ["pass"]
    n2 = G.apply_move(n, "pass")
    assert G.is_terminal(n2) and n2.winner is None and G.returns(n2) == [0.0, 0.0]
    # with supply left, entering is possible -> pass is NOT offered
    s3 = _state({(0, 0): "01"}, supply=(1, 0))
    assert "pass" not in G.legal_moves(s3)


def test_threefold_repetition_draw():
    """The official 'endless loop -> declare drawn' note, implemented as a
    threefold-repetition draw: a legal 4-ply shuffle cycle repeated twice
    reaches the same position a third time."""
    s = _state({(0, 0): "00", (0, 1): "1", (4, 4): "11", (4, 3): "0"},
               supply=(0, 0))
    cycle = ["0,0>0,1=1", "4,4>4,3=1", "0,1>0,0=1", "4,3>4,4=1"]
    for i, m in enumerate(cycle * 2):
        assert not G.is_terminal(s), f"terminal too early at ply {i}"
        assert m in G.legal_moves(s), f"{m} not legal at ply {i}"
        s = G.apply_move(s, m)
    assert G.is_terminal(s) and s.winner is None       # third occurrence -> draw
    assert G.returns(s) == [0.0, 0.0]


def test_serialize_roundtrip_and_render():
    s = G.initial_state()
    rng = random.Random(7)
    for _ in range(30):
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    d = G.serialize(s)
    assert G.serialize(G.deserialize(d)) == d
    spec = G.render(s)
    assert spec["board"] == {"type": "square", "width": 5, "height": 5}
    for p in spec["pieces"]:
        assert isinstance(p["stack"], list) and p["owner"] == p["stack"][-1]
        assert 1 <= len(p["stack"]) <= 4               # 5+ stacks are removed


def test_playouts_terminate():
    """500 random playouts all reach a terminal; report result/backstop rates."""
    rng = random.Random(42)
    stats = {"white": 0, "red": 0, "double-pass": 0, "repetition": 0,
             "no-progress": 0, "ply-cap": 0}
    plies = []
    for _ in range(500):
        s = G.initial_state()
        while not G.is_terminal(s):
            assert s.ply <= 600, "exceeded hard cap without terminating"
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        plies.append(s.ply)
        if s.winner is not None:
            stats["white" if s.winner == WHITE else "red"] += 1
        elif s.passes >= 2:
            stats["double-pass"] += 1
        elif s.reps.get(G._key(s), 0) >= 3:
            stats["repetition"] += 1
        elif s.since >= 100:
            stats["no-progress"] += 1
        else:
            stats["ply-cap"] += 1
    assert stats["white"] + stats["red"] > 0
    print(f"  playouts: {stats}, avg plies {sum(plies)/len(plies):.1f}, "
          f"max {max(plies)}")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
    print("mixtour selftest: all passed")
