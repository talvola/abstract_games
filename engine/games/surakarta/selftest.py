"""Standalone correctness anchor for Surakarta.

Run:  PYTHONPATH=. python3 games/surakarta/selftest.py

Pure stdlib + the agp package only (no third-party libs). Surakarta has no
published perft/move counts, so the anchor is a set of baked rule assertions on
hand-built positions plus an engine conformance pass:

  (1) a non-capturing move is a single step to ANY of the 8 adjacent EMPTY
      intersections (orthogonal or diagonal);
  (2) a capture is ONLY legal by sliding along the orthogonal lines through AT
      LEAST ONE corner loop and landing on the FIRST piece encountered, which
      must be an enemy — own piece in the path => no capture, and NO jumping
      over an intervening piece;
  (3) a piece may NOT capture without going around a loop (a straight no-arc
      slide to an enemy is rejected; the same enemy placed so a loop is required
      and unblocked IS captured);
  (4) capture-all-enemy win reached via apply_move;
  plus the standard opening array, the loop topology (only inner four lines per
  axis loop; corners participate in nothing), the no-capture draw cap, and a
  serialize round-trip.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import json
import os
import random
import sys

from agp.conformance import check  # type: ignore
from games.surakarta.game import (
    Surakarta,
    SurakartaState,
    _capture_targets,
    _slide,
    _start_board,
    _OCC,
    RINGS,
    ARC_IDX,
    NO_CAP_CAP,
)


def main() -> int:
    g = Surakarta()

    # --- conformance -----------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as f:
        manifest = json.load(f)
    rep = check(g, manifest, games=3, seed=11)
    assert rep.ok, f"conformance failed: {getattr(rep, 'messages', rep)}"

    # --- opening array ---------------------------------------------------
    b0 = _start_board()
    assert len(b0) == 24, "12 + 12 pieces"
    assert sum(1 for v in b0.values() if v == 0) == 12
    assert sum(1 for v in b0.values() if v == 1) == 12
    assert all(b0[(c, r)] == 0 for c in range(6) for r in (0, 1))
    assert all(b0[(c, r)] == 1 for c in range(6) for r in (4, 5))
    assert all((c, 2) not in b0 and (c, 3) not in b0 for c in range(6)), \
        "middle two rows start empty"
    s0 = g.initial_state()
    assert g.current_player(s0) == 0, "White moves first"
    # opening has no captures available (armies not yet in loop contact range
    # only via lines): every opening move is a step.
    for m in g.legal_moves(s0):
        ns = g.apply_move(s0, m)
        assert len(ns.board) == len(s0.board), f"opening move {m} must not capture"

    # --- (1) non-capturing step: exactly the 8 adjacent empty cells ------
    s = SurakartaState(board={(2, 2): 0}, to_move=0)
    steps = sorted(g.legal_moves(s))
    expect = sorted(
        f"2,2>{2 + dc},{2 + dr}"
        for dc in (-1, 0, 1) for dr in (-1, 0, 1) if not (dc == 0 and dr == 0)
    )
    assert steps == expect, f"lone-piece steps wrong: {steps}"
    # a step must be exactly one cell away (never multi-line)
    for m in steps:
        frm = tuple(int(x) for x in m.split(">")[0].split(","))
        to = tuple(int(x) for x in m.split(">")[1].split(","))
        assert max(abs(to[0] - frm[0]), abs(to[1] - frm[1])) == 1
    # occupied adjacent cells are NOT step targets (e.g. friendly above)
    s = SurakartaState(board={(2, 2): 0, (2, 3): 0}, to_move=0)
    assert "2,2>2,3" not in g.legal_moves(s)

    # --- loop topology: only inner four lines loop; corners loop on nothing
    nonpart = sorted(c for c in ((cc, rr) for cc in range(6) for rr in range(6))
                     if c not in _OCC)
    assert nonpart == [(0, 0), (0, 5), (5, 0), (5, 5)], \
        f"only the 4 true corners loop on nothing: {nonpart}"
    assert len(RINGS) == 2 and len(RINGS[0]) == 24
    # 4 arc transitions per ring
    assert ARC_IDX == {5, 11, 17, 23}

    # --- (2)/(3) loop capture vs. no-loop rejection ----------------------
    # White (2,1); friendly blocker (1,1) seals the backward route on row 1.
    # Enemy at (4,1) is two cells right on the same row: the forward slide
    # reaches it with ZERO arcs => NOT a capture (no loop traversed).
    s = SurakartaState(board={(2, 1): 0, (1, 1): 0, (4, 1): 1}, to_move=0)
    assert _capture_targets(s.board, (2, 1), 0) == set(), \
        "straight no-loop slide must not capture"
    assert "2,1>4,1" not in g.legal_moves(s)
    # Same setup but the enemy at (4,0): the forward slide now bends around the
    # bottom-right inner arc (>= 1 loop) and captures it.
    s = SurakartaState(board={(2, 1): 0, (1, 1): 0, (4, 0): 1}, to_move=0)
    assert _capture_targets(s.board, (2, 1), 0) == {(4, 0)}, \
        "loop slide must capture the first enemy met"
    assert "2,1>4,0" in g.legal_moves(s)
    # the arc count of that slide is >= 1 (sanity on the slide primitive)
    res = _slide((2, 1), 0, _OCC[(2, 1)][0][1], 1, s.board)
    assert res == ((4, 0), 1), f"forward slide should hit (4,0) after 1 arc: {res}"

    # --- (2) NO jumping: an intervening piece ends the slide -------------
    # White (0,1), enemy (4,0). Forward route crosses 1 arc; backward 3 arcs.
    # Block BOTH first-cells with friendlies -> enemy unreachable, no capture.
    s = SurakartaState(board={(0, 1): 0, (1, 1): 0, (1, 0): 0, (4, 0): 1},
                       to_move=0)
    assert _capture_targets(s.board, (0, 1), 0) == set(), \
        "cannot jump over an intervening piece (both routes blocked)"
    # With only the forward route open the capture is back:
    s = SurakartaState(board={(0, 1): 0, (1, 0): 0, (4, 0): 1}, to_move=0)
    assert (4, 0) in _capture_targets(s.board, (0, 1), 0)

    # --- own piece as the first piece met => not a capture ---------------
    # White (0,1); own White at (4,0) on the forward route; backward sealed.
    s = SurakartaState(board={(0, 1): 0, (1, 0): 0, (4, 0): 0}, to_move=0)
    assert _capture_targets(s.board, (0, 1), 0) == set(), \
        "first piece met being your own yields no capture"

    # --- diagonals never capture ----------------------------------------
    # White (0,0) (a true corner: on no loop). Enemy diagonally adjacent at
    # (1,1). (1,1) is reachable as a STEP only if empty; here it's an enemy, so
    # it is neither a step nor a capture (corner can't loop) -> no move to it.
    s = SurakartaState(board={(0, 0): 0, (1, 1): 1}, to_move=0)
    assert _capture_targets(s.board, (0, 0), 0) == set()
    assert "0,0>1,1" not in g.legal_moves(s)

    # --- a real capture applied removes the enemy & moves the slider -----
    s = SurakartaState(board={(2, 1): 0, (1, 1): 0, (4, 0): 1}, to_move=0)
    r = g.apply_move(s, "2,1>4,0")
    assert (4, 0) in r.board and r.board[(4, 0)] == 0, "slider takes the square"
    assert (2, 1) not in r.board, "slider left its origin"
    assert sum(1 for v in r.board.values() if v == 1) == 0
    assert r.no_cap == 0, "a capture resets the no-capture counter"
    assert g.describe_move(s, "2,1>4,0") == "2,1x4,0"
    assert g.describe_move(SurakartaState(board={(2, 2): 0}, to_move=0),
                           "2,2>2,3") == "2,2-2,3"

    # --- (4) capture-all win reached via apply_move ----------------------
    sWin = SurakartaState(board={(2, 1): 0, (4, 0): 1}, to_move=0)
    rWin = g.apply_move(sWin, "2,1>4,0")
    assert g.is_terminal(rWin), "capturing the last enemy must terminate"
    assert g.returns(rWin) == [1.0, -1.0], "White wins by annihilation"

    # --- no-capture draw cap --------------------------------------------
    # A state already at the brink: one more non-capturing step reaches the cap
    # and is scored a draw. (Both kings still on the board, so it is the cap and
    # not annihilation that ends it.)
    s = SurakartaState(board={(0, 0): 0, (5, 5): 1}, to_move=0,
                       no_cap=NO_CAP_CAP - 1)
    quiet = next(m for m in g.legal_moves(s)
                 if m.startswith("0,0>")
                 and not g._is_capture(dict(s.board),
                                       (0, 0),
                                       tuple(int(x) for x in m.split(">")[1].split(",")),
                                       0))
    r = g.apply_move(s, quiet)
    assert g.is_terminal(r) and r.winner == -2, "no-capture cap must draw"
    assert g.returns(r) == [0.0, 0.0]
    # and a capture before the cap resets the counter (so the cap is about
    # *consecutive* quiet plies):
    sc = SurakartaState(board={(2, 1): 0, (4, 0): 1, (5, 5): 1}, to_move=0,
                        no_cap=NO_CAP_CAP - 1)
    rc = g.apply_move(sc, "2,1>4,0")
    assert rc.no_cap == 0 and rc.winner == -1, "a capture resets / continues play"

    # --- serialize round-trip on a mid-game state ------------------------
    rng = random.Random(123)
    s = g.initial_state()
    for _ in range(25):
        if g.is_terminal(s):
            break
        s = g.apply_move(s, rng.choice(g.legal_moves(s)))
    d = g.serialize(s)
    assert g.serialize(g.deserialize(d)) == d, "serialize must round-trip"

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
