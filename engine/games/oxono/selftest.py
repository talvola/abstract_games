"""Oxono correctness anchors (pure stdlib: agp + this game only).

Anchored on the official Cosmoludo digital rulebook
(undecent.fr/wp-content/uploads/2024/04/Oxono-digital-rule-book.pdf),
cross-checked against BGA's Gamehelpoxono:

* setup (totems on the two central dot squares, 8+8 tokens each, pink first);
* rook totem movement over empty squares only (no passing tokens/totems);
* you may only move a totem whose symbol you still hold;
* surrounded totem jumps to the first free square per direction (incl. over
  the other totem); fully-trapped totem (row+column full) flies anywhere;
* token drop: empty orthogonal neighbour of the moved totem; enclosed landing
  (no free neighbour) -> anywhere free;
* wins by 4-in-a-row of colour OR of symbol (orthogonal lines only, totems
  never count, the player PLACING the 4th token of a symbol line wins it);
* supply exhaustion with no line -> honest draw;
* structural termination (<= 64 plies) over 500 random playouts + stats.

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/oxono/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.oxono.game import OxState, DOTS, SIZE

_M, G = load_from_dir(Path(__file__).resolve().parent)

ALL = [(c, r) for r in range(SIZE) for c in range(SIZE)]


def _fmt(p):
    return f"{p[0]},{p[1]}"


def _state(tokens=None, totems=None, reserve=None, to_move=0,
           phase="TOTEM", moved=None):
    """tokens: {(c,r): (owner, sym)}; totems: {"X": (c,r), "O": (c,r)}."""
    if reserve is None:
        reserve = [{"X": 8, "O": 8}, {"X": 8, "O": 8}]
    return OxState(tokens=dict(tokens or {}),
                   totems=dict(totems or {"X": DOTS[0], "O": DOTS[1]}),
                   reserve=[dict(reserve[0]), dict(reserve[1])],
                   to_move=to_move, phase=phase, moved=moved)


def _totem_moves(s, frm):
    return {m for m in G.legal_moves(s) if m.startswith(_fmt(frm) + ">")}


# --------------------------------------------------------------------------
def test_setup():
    """Rulebook setup: totems randomly on the two central dot squares, each
    player 8 X + 8 O tokens, pink (seat 0) starts with a totem move."""
    seen = set()
    for seed in range(20):
        s = G.initial_state(rng=random.Random(seed))
        assert sorted(s.totems.values()) == sorted(DOTS)
        seen.add(s.totems["X"])
        assert s.reserve == [{"X": 8, "O": 8}, {"X": 8, "O": 8}]
        assert not s.tokens and s.to_move == 0 and s.phase == "TOTEM"
        assert not G.is_terminal(s)
    assert seen == set(DOTS), "both random totem arrangements must occur"


def test_rook_movement():
    """'moving one of the two Totems ... as many squares as they want in a
    row (minimum 1 square), horizontally or vertically' — over empty squares
    only. From (2,2) on an empty board: the full row + column, 10 squares."""
    s = _state(totems={"X": (2, 2), "O": (3, 3)})
    want = {f"2,2>{c},2" for c in (0, 1, 3, 4, 5)} | \
           {f"2,2>2,{r}" for r in (0, 1, 3, 4, 5)}
    assert _totem_moves(s, (2, 2)) == want
    moves = G.legal_moves(s)
    assert len(moves) == len(set(moves)) == 20  # 10 per totem, no duplicates


def test_no_passing():
    """'A Totem can not pass over a square occupied by another piece or
    Totem' — blockers truncate the ray and are never landing squares."""
    s = _state(tokens={(4, 2): (1, "O")},
               totems={"X": (2, 2), "O": (2, 4)})
    want = {"2,2>3,2",                       # right: token on (4,2) blocks
            "2,2>2,3",                       # up: O totem on (2,4) blocks
            "2,2>0,2", "2,2>1,2",            # left clear
            "2,2>2,0", "2,2>2,1"}            # down clear
    assert _totem_moves(s, (2, 2)) == want


def test_reserve_gate():
    """'You can only move a Totem if you still have pieces of the same
    symbol in reserve.'"""
    s = _state(totems={"X": (2, 2), "O": (3, 3)},
               reserve=[{"X": 0, "O": 8}, {"X": 8, "O": 8}])
    assert _totem_moves(s, (2, 2)) == set()          # X totem locked for seat 0
    assert len(_totem_moves(s, (3, 3))) == 10        # O totem free
    s2 = _state(totems={"X": (2, 2), "O": (3, 3)},
                reserve=[{"X": 0, "O": 8}, {"X": 8, "O": 8}], to_move=1)
    assert len(_totem_moves(s2, (2, 2))) == 10       # seat 1 still has X tokens


def test_surrounded_jump():
    """Special case A: a surrounded totem jumps over the piece (or series of
    pieces) to the FIRST free square in each direction — including over the
    other totem (case C triggers only when both rows are entirely full)."""
    tokens = {(1, 2): (0, "X"), (3, 2): (1, "O"), (2, 1): (0, "O"),
              (4, 2): (1, "X")}                       # right: series of two
    s = _state(tokens=tokens, totems={"X": (2, 2), "O": (2, 3)})
    # up neighbour is the O totem -> still surrounded, and jumpable
    want = {"2,2>0,2",     # left: over (1,2)
            "2,2>5,2",     # right: over the (3,2),(4,2) series
            "2,2>2,0",     # down: over (2,1)
            "2,2>2,4"}     # up: over the other totem
    assert _totem_moves(s, (2, 2)) == want
    # a NON-surrounded totem never jumps: free one neighbour
    s2 = _state(tokens={k: v for k, v in tokens.items() if k != (2, 1)},
                totems={"X": (2, 2), "O": (2, 3)})
    assert _totem_moves(s2, (2, 2)) == {"2,2>2,0", "2,2>2,1"}


def test_corner_surround_and_edge():
    """Edges are walls: a corner totem with its 2 neighbours occupied is
    surrounded; a jump off the board is impossible."""
    s = _state(tokens={(1, 0): (0, "X"), (0, 1): (1, "O")},
               totems={"X": (0, 0), "O": (3, 3)})
    assert _totem_moves(s, (0, 0)) == {"0,0>2,0", "0,0>0,2"}


def test_fully_trapped_flies():
    """Special case C: surrounded + whole row AND column occupied -> the totem
    may be placed on any free square of the board."""
    tokens = {(c, 0): (c % 2, "X") for c in range(1, 6)}
    tokens.update({(0, r): (r % 2, "O") for r in range(1, 6)})
    s = _state(tokens=tokens, totems={"X": (0, 0), "O": (3, 3)})
    empties = {p for p in ALL if p not in tokens and p not in ((0, 0), (3, 3))}
    assert _totem_moves(s, (0, 0)) == {f"0,0>{_fmt(p)}" for p in empties}
    assert len(empties) == 36 - 10 - 2


def test_drop_adjacent():
    """'place one of their pieces with the same symbol as the Totem played,
    on a free square adjacent (vertically or horizontally) to the new
    position' — and a 1-step move's vacated origin counts (it is now free)."""
    s = _state(totems={"X": (2, 2), "O": (3, 3)})
    s2 = G.apply_move(s, "2,2>2,3")                  # X totem one step up
    assert s2.phase == "DROP" and s2.moved == "X" and s2.to_move == 0
    # neighbours of (2,3): (3,3) is the O totem (not free), the vacated
    # origin (2,2) IS free and droppable
    assert set(G.legal_moves(s2)) == {"1,3", "2,4", "2,2"}
    s3 = G.apply_move(s2, "2,2")
    assert s3.tokens[(2, 2)] == (0, "X")
    assert s3.reserve[0] == {"X": 7, "O": 8}
    assert s3.to_move == 1 and s3.phase == "TOTEM" and s3.winner is None


def test_enclosed_landing_drops_anywhere():
    """Special case B: a totem landing with no free orthogonal neighbour
    (only reachable by jump/flight) -> the token goes on ANY free square."""
    tokens = {(1, 0): (0, "X"), (0, 1): (1, "O"),
              (3, 0): (1, "X"), (2, 1): (0, "O")}
    s = _state(tokens=tokens, totems={"X": (0, 0), "O": (5, 5)})
    assert "0,0>2,0" in _totem_moves(s, (0, 0))      # jump right over (1,0)
    s2 = G.apply_move(s, "0,0>2,0")                  # (2,0): all 3 nbrs occupied
    empties = {p for p in ALL if p not in tokens and p not in ((2, 0), (5, 5))}
    assert set(G.legal_moves(s2)) == {_fmt(p) for p in empties}
    assert len(empties) == 30


def test_colour_win():
    """Win: 4 aligned tokens of your colour, symbols mixed freely."""
    tokens = {(0, 0): (0, "X"), (1, 0): (0, "O"), (2, 0): (0, "X")}
    s = _state(tokens=tokens, totems={"X": (4, 4), "O": (3, 3)})
    s2 = G.apply_move(s, "4,4>4,0")                  # X totem down to (4,0)
    s3 = G.apply_move(s2, "3,0")                     # X token completes colours
    assert s3.winner == 0 and G.is_terminal(s3)
    assert G.returns(s3) == [1.0, -1.0]
    assert G.legal_moves(s3) == []


def test_symbol_win_mixed_colours_completer_wins():
    """'The player who places the 4th piece of the same symbol wins, even if
    there are more pieces of the opponent's colour in the alignment.'"""
    tokens = {(0, 5): (1, "O"), (1, 5): (1, "O"), (2, 5): (0, "O")}
    s = _state(tokens=tokens, totems={"X": (0, 0), "O": (4, 4)})
    s2 = G.apply_move(s, "4,4>4,5")                  # O totem to (4,5)
    s3 = G.apply_move(s2, "3,5")                     # seat 0 completes O-O-O-O
    assert s3.winner == 0, "completer wins the mixed-colour symbol row"
    assert G.returns(s3) == [1.0, -1.0]


def test_totems_do_not_count():
    """'The symbol of the Totems do not count in the alignment' — X,X,X plus
    the X totem on the 4th square is NOT a win (for colour or symbol)."""
    tokens = {(0, 0): (0, "X"), (1, 0): (0, "X"), (2, 0): (0, "X")}
    s = _state(tokens=tokens, totems={"X": (3, 0), "O": (3, 3)})
    assert not G.is_terminal(s)
    s2 = G.apply_move(s, "3,3>3,4")                  # unrelated O move
    s3 = G.apply_move(s2, "3,5")                     # unrelated O drop
    assert s3.winner is None and not G.is_terminal(s3)


def test_supply_exhaustion_draw():
    """When both players have placed all their tokens with no line of 4, the
    game ends in an honest draw ([0, 0])."""
    tokens = {(0, 0): (0, "X"), (5, 5): (1, "O")}
    s = _state(tokens=tokens, totems={"X": (2, 2), "O": (3, 3)},
               reserve=[{"X": 0, "O": 1}, {"X": 0, "O": 1}])
    # only the O totem is playable for both (X reserves empty)
    assert all(m.startswith("3,3>") for m in G.legal_moves(s))
    s = G.apply_move(s, "3,3>3,0")
    s = G.apply_move(s, "4,0")                       # seat 0's last token
    assert not G.is_terminal(s) and s.to_move == 1
    s = G.apply_move(s, "3,0>3,4")
    s = G.apply_move(s, "3,5")                       # seat 1's last token
    assert G.is_terminal(s) and s.winner is None
    assert G.returns(s) == [0.0, 0.0]


def test_roundtrip_and_playouts():
    """500 random playouts: structural termination <= 64 plies, legal_moves
    non-empty until terminal, mover always holds a token, serialize
    round-trips. Prints result stats."""
    rng = random.Random(7)
    wins = [0, 0]
    draws = 0
    plies = []
    for g in range(500):
        s = G.initial_state(rng=rng)
        n = 0
        while not G.is_terminal(s):
            moves = G.legal_moves(s)
            assert moves, "non-terminal state with no moves"
            p = G.current_player(s)
            assert sum(s.reserve[p].values()) > 0
            s = G.apply_move(s, rng.choice(moves))
            n += 1
            assert n <= 64, "game exceeded the structural 64-ply bound"
        if g % 25 == 0:                              # spot-check round-trips
            d = G.serialize(s)
            assert G.serialize(G.deserialize(d)) == d
        plies.append(n)
        if s.winner is None:
            draws += 1
        else:
            wins[s.winner] += 1
    assert wins[0] + wins[1] + draws == 500
    assert wins[0] > 0 and wins[1] > 0
    print(f"  playouts: 500 games, P1 {wins[0]} / P2 {wins[1]} / draws {draws},"
          f" avg plies {sum(plies) / len(plies):.1f}, max {max(plies)}")


def test_render_shape():
    """Render probe: 6x6 square board, 2 neutral totem discs, dot tints,
    reserve trays present, tokens labelled with their symbol."""
    s = G.initial_state(rng=random.Random(1))
    s = G.apply_move(s, G.legal_moves(s)[0])
    s = G.apply_move(s, G.legal_moves(s)[0])
    spec = G.render(s)
    assert spec["board"] == {"type": "square", "width": 6, "height": 6,
                             "tints": {"2,2": "#3d4457", "3,3": "#3d4457"}}
    totems = [p for p in spec["pieces"] if p["owner"] == 2]
    assert sorted(t["label"] for t in totems) == ["O", "X"]
    assert all(t.get("fill") for t in totems)
    toks = [p for p in spec["pieces"] if p["owner"] != 2]
    assert len(toks) == 1 and toks[0]["label"] in "XO"
    assert set(spec["reserve"]) == {"0", "1"}
    assert sum(spec["reserve"]["0"].values()) == 15   # one token placed
    assert spec["caption"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        print(f"{t.__name__} ...")
        t()
    print(f"oxono selftest: {len(tests)} tests passed")
