"""Standalone correctness anchor for Abalone (pure-stdlib).

Run from the engine dir:  PYTHONPATH=. python3 games/abalone/selftest.py

Asserts:
  * the 61-cell side-5 hexhex,
  * the STANDARD 14+14 starting layout (exact cells + counts + shape),
  * a single-marble step to an empty cell,
  * in-line 2-group and 3-group moves,
  * valid SUMITO pushes (2-push-1 and 3-push-2), including an edge EJECTION,
  * illegal pushes are absent (2v2, 3v3, pushing own marble, pushing when the
    cell behind the enemy line is occupied),
  * broadside 2- and 3-group moves (all destinations empty, no push),
  * the win at 6 ejections, reached via apply_move (win is an event),
  * apply_move purity and serialize round-trip,
  * the standard opening legal-move count (sanity-checked vs the known figure 44),
  * conformance (random play terminates, returns well-formed).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import copy
import json
import os
import sys

from games.abalone.game import (
    Abalone, AbaloneState, BLACK, WHITE,
    _all_cells, standard_start, _cstr, _cell,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


G = Abalone()


def place(board_pairs):
    """Build a state from a list of (cell, owner), Black to move."""
    board = {c: o for c, o in board_pairs}
    return AbaloneState(board=board, to_move=BLACK)


def legal(s):
    return set(G.legal_moves(s))


def main():
    # ---- board geometry -------------------------------------------------
    cells = _all_cells()
    check(len(cells) == 61, f"expected 61 cells, got {len(cells)}")

    # ---- standard start -------------------------------------------------
    black, white = standard_start()
    check(len(black) == 14 and len(white) == 14,
          f"start counts {len(black)}/{len(white)} != 14/14")
    exp_black = {(-1, -3), (0, -4), (0, -3), (0, -2), (1, -4), (1, -3), (1, -2),
                 (2, -4), (2, -3), (2, -2), (3, -4), (3, -3), (4, -4), (4, -3)}
    check(set(black) == exp_black, f"black start cells wrong: {sorted(black)}")
    check(set(white) == {(-q, -r) for (q, r) in black},
          "white start is not the 180-degree rotation of black")
    # disjoint + all on-board
    check(set(black).isdisjoint(set(white)), "armies overlap")
    onset = set(cells)
    check(set(black) | set(white) <= onset, "a start marble is off-board")

    s0 = G.initial_state()
    check(sum(1 for p in s0.board.values() if p == BLACK) == 14, "init black count")
    check(sum(1 for p in s0.board.values() if p == WHITE) == 14, "init white count")
    check(G.current_player(s0) == BLACK, "Black should move first")

    # ---- single marble step to empty -----------------------------------
    s = place([((0, 0), BLACK)])
    mv = "0,0>1,0"
    check(mv in legal(s), "single step E not legal")
    s2 = G.apply_move(s, mv)
    check(s2.board == {(1, 0): BLACK}, "single step result wrong")
    # all 6 dirs available from center
    check(len([m for m in legal(s)]) == 6, "single marble should have 6 steps")

    # ---- in-line 2-group move (into empty) ------------------------------
    # Encoding = group cells sorted + anchor's NEW cell. Anchor (0,0) slides E
    # to (1,0), so the path ends in "1,0".
    s = place([((0, 0), BLACK), ((1, 0), BLACK)])
    mv = "0,0>1,0>1,0"  # group {(0,0),(1,0)} slides E, anchor (0,0)->(1,0)
    check(mv in legal(s), "in-line 2-group E not legal")
    s2 = G.apply_move(s, mv)
    check(s2.board == {(1, 0): BLACK, (2, 0): BLACK}, "2-group slide result wrong")

    # ---- in-line 3-group move (into empty) ------------------------------
    s = place([((0, 0), BLACK), ((1, 0), BLACK), ((2, 0), BLACK)])
    mv = "0,0>1,0>2,0>1,0"  # anchor (0,0)->(1,0)
    check(mv in legal(s), "in-line 3-group E not legal")
    s2 = G.apply_move(s, mv)
    check(s2.board == {(1, 0): BLACK, (2, 0): BLACK, (3, 0): BLACK},
          "3-group slide result wrong")

    # ---- SUMITO 2-push-1 ------------------------------------------------
    s = place([((0, 0), BLACK), ((1, 0), BLACK), ((2, 0), WHITE)])
    mv = "0,0>1,0>1,0"  # 2 black push the 1 white E (anchor (0,0)->(1,0))
    check(mv in legal(s), "2-push-1 not legal")
    s2 = G.apply_move(s, mv)
    check(s2.board == {(1, 0): BLACK, (2, 0): BLACK, (3, 0): WHITE},
          f"2-push-1 result wrong: {s2.board}")
    check(s2.ejected == (0, 0), "no ejection should have happened mid-board")

    # ---- SUMITO 3-push-2 ------------------------------------------------
    s = place([((-1, 0), BLACK), ((0, 0), BLACK), ((1, 0), BLACK),
               ((2, 0), WHITE), ((3, 0), WHITE)])
    mv = "-1,0>0,0>1,0>0,0"  # 3 black push 2 white E (anchor (-1,0)->(0,0))
    check(mv in legal(s), "3-push-2 not legal")
    s2 = G.apply_move(s, mv)
    check(s2.board == {(0, 0): BLACK, (1, 0): BLACK, (2, 0): BLACK,
                       (3, 0): WHITE, (4, 0): WHITE},
          f"3-push-2 result wrong: {s2.board}")

    # ---- SUMITO with EDGE EJECTION --------------------------------------
    # White marble at (4,0) is on the E edge; pushing it E ejects it off-board.
    s = place([((2, 0), BLACK), ((3, 0), BLACK), ((4, 0), WHITE)])
    mv = "2,0>3,0>3,0"  # anchor (2,0)->(3,0)
    check(mv in legal(s), "edge eject push not legal")
    s2 = G.apply_move(s, mv)
    check(s2.board == {(3, 0): BLACK, (4, 0): BLACK},
          f"after eject board wrong: {s2.board}")
    check(s2.ejected == (0, 1), f"white should have lost 1 marble: {s2.ejected}")

    # ---- ILLEGAL PUSHES ARE ABSENT --------------------------------------
    # 2v2: equal numbers cannot push  (encoding: anchor (0,0)->(1,0))
    s = place([((0, 0), BLACK), ((1, 0), BLACK), ((2, 0), WHITE), ((3, 0), WHITE)])
    check("0,0>1,0>1,0" not in legal(s), "2v2 push must be illegal")
    # 3v3  (anchor (-1,0)->(0,0))
    s = place([((-1, 0), BLACK), ((0, 0), BLACK), ((1, 0), BLACK),
               ((2, 0), WHITE), ((3, 0), WHITE), ((4, 0), WHITE)])
    check("-1,0>0,0>1,0>0,0" not in legal(s), "3v3 push must be illegal")
    # pushing through your own marble: 2 black, 1 white, then a black behind the
    # white -> cell behind enemy is occupied by own marble -> illegal.
    s = place([((0, 0), BLACK), ((1, 0), BLACK), ((2, 0), WHITE), ((3, 0), BLACK)])
    check("0,0>1,0>1,0" not in legal(s),
          "push blocked by own marble behind enemy must be illegal")
    # 2 black vs a 2-white line: cell behind the first enemy is another enemy, so
    # it is really 2v2 -> illegal (covered above but assert via the encoding too).
    s = place([((0, 0), BLACK), ((1, 0), BLACK), ((2, 0), WHITE), ((3, 0), WHITE)])
    check("0,0>1,0>1,0" not in legal(s), "2 cannot push a 2-line (behind occupied)")

    # ---- BROADSIDE 2-group ----------------------------------------------
    # Two black along E axis at (0,0),(1,0); broadside SE (0,1): dests (0,1),(1,1)
    s = place([((0, 0), BLACK), ((1, 0), BLACK)])
    mv = "0,0>1,0>0,1"  # anchor (0,0)->(0,1) [SE], both step SE
    check(mv in legal(s), "broadside 2-group SE not legal")
    s2 = G.apply_move(s, mv)
    check(s2.board == {(0, 1): BLACK, (1, 1): BLACK},
          f"broadside 2-group result wrong: {s2.board}")
    # broadside must not push: block one destination with an enemy
    s = place([((0, 0), BLACK), ((1, 0), BLACK), ((0, 1), WHITE)])
    check("0,0>1,0>0,1" not in legal(s),
          "broadside into an occupied cell must be illegal (no push on broadside)")

    # ---- BROADSIDE 3-group ----------------------------------------------
    s = place([((0, 0), BLACK), ((1, 0), BLACK), ((2, 0), BLACK)])
    mv = "0,0>1,0>2,0>0,1"  # broadside SE
    check(mv in legal(s), "broadside 3-group SE not legal")
    s2 = G.apply_move(s, mv)
    check(s2.board == {(0, 1): BLACK, (1, 1): BLACK, (2, 1): BLACK},
          f"broadside 3-group result wrong: {s2.board}")

    # ---- WIN at 6 ejections (reach via apply_move) ----------------------
    # Set black's loss count to 5 and have White push a lone black off the edge.
    s = AbaloneState(
        board={(4, 0): WHITE, (3, 0): WHITE, (2, 0): BLACK},
        to_move=WHITE, ejected=(5, 0),  # BLACK has already lost 5
    )
    # 2 white at (3,0),(4,0)?? careful: white pushes WEST. Build: black at (2,0)
    # on... we need black at the W edge. Rebuild cleanly:
    s = AbaloneState(
        board={(-4, 0): BLACK, (-3, 0): WHITE, (-2, 0): WHITE},
        to_move=WHITE, ejected=(5, 0),
    )
    mv = "-3,0>-2,0>-3,0"  # 2 white push 1 black WEST, anchor (-3,0)->(-4,0)?
    # anchor is min sorted of {(-3,0),(-2,0)} = (-3,0); West dir (-1,0) -> dst (-4,0)
    mv = "-3,0>-2,0>-4,0"
    check(mv in legal(s), f"winning push not legal; legal={sorted(legal(s))}")
    s2 = G.apply_move(s, mv)
    check(s2.ejected == (6, 0), f"black should have lost 6: {s2.ejected}")
    check(s2.winner == WHITE, f"White should win at 6 ejections: winner={s2.winner}")
    check(G.is_terminal(s2), "win state must be terminal")
    check(G.returns(s2) == [-1.0, 1.0], f"returns wrong at White win: {G.returns(s2)}")

    # ---- apply_move purity ----------------------------------------------
    s = G.initial_state()
    snap = copy.deepcopy(s.board)
    m = G.legal_moves(s)[0]
    _ = G.apply_move(s, m)
    check(s.board == snap, "apply_move mutated input state board")
    check(s.to_move == BLACK, "apply_move mutated to_move")

    # ---- serialize round-trip -------------------------------------------
    s = G.initial_state()
    s = G.apply_move(s, G.legal_moves(s)[0])
    d = G.serialize(s)
    json.dumps(d)  # must be JSON-able
    s_rt = G.deserialize(d)
    check(G.serialize(s_rt) == d, "serialize round-trip mismatch")

    # ---- opening legal-move count ---------------------------------------
    s0 = G.initial_state()
    opening = G.legal_moves(s0)
    n_open = len(opening)
    # every encoding must be unique
    check(len(set(opening)) == n_open, "duplicate move encodings in opening")
    # The standard Abalone opening branching factor is widely cited as 44.
    KNOWN = 44
    print(f"opening legal moves = {n_open} (published standard-opening figure: {KNOWN})")
    check(n_open == KNOWN,
          f"opening move count {n_open} != known standard figure {KNOWN}")

    # ---- render sanity (hex spec) ---------------------------------------
    spec = G.render(s0)
    check(spec["board"] == {"type": "hex", "shape": "hexagon", "size": 5},
          f"render board spec wrong: {spec['board']}")
    check(len(spec["pieces"]) == 28, "render should show 28 marbles")

    # ---- conformance (termination, well-formed returns) -----------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(G, manifest, games=6, seed=1)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
