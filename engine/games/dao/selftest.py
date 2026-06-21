#!/usr/bin/env python3
"""Standalone correctness anchor for Dao. Pure stdlib + the agp package only.

Run:  PYTHONPATH=. python3 games/dao/selftest.py
Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.

Asserts:
  * the engine conformance suite passes (general invariants),
  * the queen-like slide goes as far as possible and cannot stop short,
  * a blocked direction yields no move,
  * each of the four win conditions (2x2 square, full row/column line,
    four corners, corner-trap) is detected,
  * the starting diagonal layout is NOT a win (diagonals don't count),
  * a no-legal-move position is a loss for the player to move.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.conformance import check  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("dao_game", os.path.join(_HERE, "game.py"))
_mod = importlib.util.module_from_spec(_spec)
sys.modules["dao_game"] = _mod  # so dataclasses can resolve the module
_spec.loader.exec_module(_mod)

Dao = _mod.Dao
DaoState = _mod.DaoState


def board_of(spec):
    """spec: dict cell-str -> player; build a DaoState."""
    return {tuple(int(x) for x in k.split(",")): v for k, v in spec.items()}


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def main():
    g = Dao()

    # --- conformance (general invariants, runs random games to terminal) ---
    with open(os.path.join(_HERE, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check(g, manifest, games=30, seed=7)
    if not rep.ok:
        fail(f"conformance:\n{rep}")

    # --- starting position sanity ---
    s0 = g.initial_state()
    if g.is_terminal(s0):
        fail("start position should not be terminal")
    if g.current_player(s0) != 0:
        fail("Black (0) should move first")
    # diagonal layout must NOT be a win for either side
    if _mod._has_won(s0.board, 0) or _mod._has_won(s0.board, 1):
        fail("starting diagonals must not count as a win")

    # --- slide: must travel as far as possible, cannot stop short ---
    # A lone Black piece at (0,0) with no obstacles. Sliding right (1,0)
    # must land on (3,0), not (1,0)/(2,0). Up (0,1) must land on (0,3).
    b = board_of({"0,0": 0})
    dest = _mod._slide_dest(b, 0, 0, 1, 0)
    if dest != (3, 0):
        fail(f"slide right from (0,0) should reach (3,0), got {dest}")
    dest = _mod._slide_dest(b, 0, 0, 0, 1)
    if dest != (0, 3):
        fail(f"slide up from (0,0) should reach (0,3), got {dest}")
    dest = _mod._slide_dest(b, 0, 0, 1, 1)
    if dest != (3, 3):
        fail(f"slide diagonal from (0,0) should reach (3,3), got {dest}")

    # --- slide stops just before an obstacle ---
    # Black at (0,0), blocker at (2,0): sliding right stops at (1,0).
    b = board_of({"0,0": 0, "2,0": 1})
    dest = _mod._slide_dest(b, 0, 0, 1, 0)
    if dest != (1, 0):
        fail(f"slide should stop before obstacle at (1,0), got {dest}")

    # --- blocked direction yields no move ---
    # Black at (0,0), blocker immediately at (1,0): sliding right is illegal.
    b = board_of({"0,0": 0, "1,0": 1})
    if _mod._slide_dest(b, 0, 0, 1, 0) is not None:
        fail("a direction blocked immediately must yield no move")
    # against the edge: sliding left/down from (0,0) is off-board -> no move.
    if _mod._slide_dest(b, 0, 0, -1, 0) is not None:
        fail("sliding off the board edge must yield no move")

    # --- win condition 1: 2x2 square ---
    b = board_of({"1,1": 0, "2,1": 0, "1,2": 0, "2,2": 0,
                  "0,0": 1, "3,3": 1, "0,3": 1, "3,0": 1})
    if not _mod._has_won(b, 0):
        fail("2x2 square should be a win")

    # --- win condition 2: full row line ---
    b = board_of({"0,1": 0, "1,1": 0, "2,1": 0, "3,1": 0,
                  "0,0": 1, "3,3": 1, "0,3": 1, "3,0": 1})
    if not _mod._has_won(b, 0):
        fail("full row of four should be a win")
    # full column line
    b = board_of({"2,0": 0, "2,1": 0, "2,2": 0, "2,3": 0,
                  "0,0": 1, "3,3": 1, "0,3": 1, "1,1": 1})
    if not _mod._has_won(b, 0):
        fail("full column of four should be a win")
    # a diagonal of four must NOT be a win
    b = board_of({"0,0": 0, "1,1": 0, "2,2": 0, "3,3": 0})
    if _mod._has_won(b, 0):
        fail("a diagonal of four must NOT be a win")

    # --- win condition 3: four corners ---
    b = board_of({"0,0": 0, "0,3": 0, "3,0": 0, "3,3": 0,
                  "1,1": 1, "2,2": 1, "1,2": 1, "2,1": 1})
    if not _mod._has_won(b, 0):
        fail("all four corners should be a win")

    # --- win condition 4: corner trap ---
    # Black piece at corner (0,0); its three neighbours (1,0),(0,1),(1,1)
    # all White -> Black wins (the trapped player wins).
    b = board_of({"0,0": 0, "1,0": 1, "0,1": 1, "1,1": 1, "3,3": 0})
    if not _mod._has_won(b, 0):
        fail("corner-trapped Black piece should be a win for Black")
    if _mod._has_won(b, 1):
        fail("the trapping player should NOT win from the corner trap")
    # if only two of the three neighbours are opponent, no trap.
    b = board_of({"0,0": 0, "1,0": 1, "0,1": 1, "1,1": 0, "3,3": 0})
    if _mod._has_won(b, 0):
        fail("corner trap needs all three neighbours to be the opponent")

    # --- corner trap is detected through apply_move, even when the
    #     OPPONENT completes it (the trapped player wins) ---
    # White to move plays the piece that completes the trap on Black's corner.
    # Black at (0,0); White at (1,0),(0,1) already; a White piece slides into
    # (1,1) completing the trap. Set up so White's move lands on (1,1).
    # White at (3,1) slides left: (2,1),(1,1) empty? put nothing in between.
    b = board_of({"0,0": 0, "1,0": 1, "0,1": 1, "3,1": 1,
                  "2,3": 0, "0,3": 0})
    s = DaoState(board=b, to_move=1, ply=10)
    # White (3,1) sliding left (-1,0): stops at (1,1) (since (0,1) occupied).
    s2 = g.apply_move(s, "3,1>1,1")
    if s2.winner != 0:
        fail(f"opponent completing corner trap should make Black (0) win, "
             f"got winner={s2.winner}")

    # --- no-legal-move => loss for player to move ---
    # Construct a position where Black (to move) has no legal slide: every
    # Black piece is hemmed so each of the 8 directions is immediately blocked
    # by the edge or a piece. Pack all 8 pieces into the 2x4 bottom block so
    # the only empties are the top two rows but each Black piece is surrounded.
    # Black occupies (0,0),(1,0),(2,0),(3,0); White (0,1),(1,1),(2,1),(3,1).
    # Black at (0,0): up->(0,1) White; right->(1,0) Black; diag(1,1) White;
    # left/down off-board -> blocked. Similarly all Black pieces are blocked.
    b = board_of({"0,0": 0, "1,0": 0, "2,0": 0, "3,0": 0,
                  "0,1": 1, "1,1": 1, "2,1": 1, "3,1": 1})
    s = DaoState(board=b, to_move=0, ply=10)
    if _mod._moves(b, 0):
        fail("expected Black to have no legal move in the stuck position")
    if not g.is_terminal(s):
        fail("a no-legal-move position must be terminal")
    if g.returns(s) != [-1.0, 1.0]:
        fail(f"no-move: Black should lose, got {g.returns(s)}")

    # --- serialize round-trips ---
    s = g.initial_state()
    s = g.apply_move(s, g.legal_moves(s)[0])
    d = g.serialize(s)
    if g.serialize(g.deserialize(d)) != d:
        fail("serialize does not round-trip")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
