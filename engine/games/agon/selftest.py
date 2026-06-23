"""Standalone correctness anchor for Agon (Queen's Guard).

Run from the engine dir:  PYTHONPATH=. python3 games/agon/selftest.py

There is no published perft for Agon, so the anchor is a set of baked rule
assertions on the documented standard ruleset:

  (1) the board is a hexagon of hexes, 6 cells per side (91 cells), centre = throne;
  (2) each player starts with exactly 1 Queen + 6 Guards, all on the outer ring,
      with the two queens on opposite corners and a 180-degree-symmetric layout;
  (3) MOVEMENT: a piece steps to an adjacent cell only INWARD or SIDEWAYS
      (same / smaller ring) — never to a larger ring; the throne is queen-only;
  (4) CAPTURE: a piece flanked between two enemies along a straight line is
      captured and sent to the owner's hand to be re-entered on the outer ring
      (a hand-built sandwich, then the rescue move);
  (5) WIN: queen on the centre with all six adjacent guards (reached via apply_move);
      plus the self-block FORFEIT (six guards, no queen -> the owner loses);
  (6) conformance + serialize round-trip.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure. Pure stdlib.
"""

from __future__ import annotations

import json
import os
import sys

from games.agon.game import (
    Agon, AgonState, P0, P1, SIZE, N, THRONE,
    _cells, _ring, _outer_ring, _inner_ring, _neighbors, _start_setup,
    _captures, _check_end, _queens_from_board,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def main():
    g = Agon()

    # ---- (1) board geometry ----------------------------------------------
    if SIZE != 6:
        fail(f"board side must be 6, got {SIZE}")
    if len(_cells()) != 91:
        fail(f"hexhex side 6 must have 91 cells, got {len(_cells())}")
    if THRONE != (0, 0) or _ring(0, 0) != 0:
        fail("throne must be the ring-0 centre cell")
    if len(_outer_ring()) != 30:
        fail(f"outer ring must have 30 cells, got {len(_outer_ring())}")
    if len(_inner_ring()) != 6:
        fail(f"inner ring must have 6 cells, got {len(_inner_ring())}")
    # every cell on the board, ring within 0..5
    for c in _cells():
        if not (0 <= _ring(*c) <= N):
            fail(f"cell {c} has out-of-range ring {_ring(*c)}")

    # ---- (2) starting material + symmetry --------------------------------
    s0 = g.initial_state()
    for p in (P0, P1):
        mine = [(c, k) for c, (o, k) in s0.board.items() if o == p]
        queens = [c for c, k in mine if k == "Q"]
        guards = [c for c, k in mine if k == "G"]
        if len(queens) != 1:
            fail(f"player {p} must start with exactly 1 queen, got {len(queens)}")
        if len(guards) != 6:
            fail(f"player {p} must start with exactly 6 guards, got {len(guards)}")
        for c, _k in mine:
            if _ring(*c) != N:
                fail(f"player {p} start piece {c} not on the outer ring")
    q = _queens_from_board(s0.board)
    if (q[P0][0], q[P0][1]) != (-q[P1][0], -q[P1][1]):
        fail("the two queens must start on opposite corners")
    # 180-degree symmetry of the whole layout
    sym = {(-c[0], -c[1]): (1 - o, k) for c, (o, k) in s0.board.items()}
    if sym != s0.board:
        fail("starting layout is not 180-degree symmetric")
    # 14 distinct occupied cells
    if len(s0.board) != 14:
        fail(f"expected 14 pieces on the board, got {len(s0.board)}")

    # ---- (3) movement: inward/sideways legal, outward illegal ------------
    # Hand-built: a single P0 guard on an outer-ring cell.
    src = (5, -2)                       # ring 5
    inward = (4, -2)                    # ring 4 (toward centre) -- legal
    sideways = (5, -3)                  # ring 5 (same ring)     -- legal
    if _ring(*src) != 5 or _ring(*inward) != 4 or _ring(*sideways) != 5:
        fail("movement fixture rings are wrong")
    st = AgonState(board={src: (P0, "G")}, to_move=P0)
    legal = set(g.legal_moves(st))
    if f"{src[0]},{src[1]}>{inward[0]},{inward[1]}" not in legal:
        fail("inward step should be legal")
    if f"{src[0]},{src[1]}>{sideways[0]},{sideways[1]}" not in legal:
        fail("sideways step should be legal")
    # An OUTWARD move from an inner cell must be rejected.
    inner_src = (3, 0)                  # ring 3
    outward = (4, 0)                    # ring 4 -- illegal (away from centre)
    if _ring(*inner_src) != 3 or _ring(*outward) != 4:
        fail("outward fixture rings wrong")
    st2 = AgonState(board={inner_src: (P0, "G")}, to_move=P0)
    if f"{inner_src[0]},{inner_src[1]}>{outward[0]},{outward[1]}" in set(g.legal_moves(st2)):
        fail("outward move was offered as legal")
    try:
        g.apply_move(st2, f"{inner_src[0]},{inner_src[1]}>{outward[0]},{outward[1]}")
        fail("apply_move accepted an illegal outward move")
    except ValueError:
        pass
    # A guard may NOT enter the throne; the queen may.
    g_adj = (1, 0)
    stg = AgonState(board={g_adj: (P0, "G")}, to_move=P0)
    if f"{g_adj[0]},{g_adj[1]}>0,0" in set(g.legal_moves(stg)):
        fail("a guard was allowed onto the throne")
    stq = AgonState(board={g_adj: (P0, "Q")}, to_move=P0)
    if f"{g_adj[0]},{g_adj[1]}>0,0" not in set(g.legal_moves(stq)):
        fail("the queen was not allowed onto the throne")

    # ---- (4) custodial capture + rescue ----------------------------------
    # P1 guard at (0,0)-ish flanked by two P0 pieces along the (1,0) axis.
    mid = (2, 0)
    a, b = (3, 0), (1, 0)              # opposite neighbours of mid along (1,0)
    if not (a in _neighbors(*mid) and b in _neighbors(*mid)):
        fail("sandwich fixture not adjacent")
    sand = {mid: (P1, "G"), a: (P0, "G"), b: (P0, "G")}
    caps = _captures(sand, P0)
    if mid not in caps:
        fail("custodial sandwich not detected as a capture")
    # The just-moved player never self-captures: same board, mover = P1.
    if _captures(sand, P1):
        fail("mover wrongly captured one of its own framing pieces")
    # Play the capture through apply_move: P0 moves a piece to COMPLETE the sandwich.
    # Start: P1 guard at mid, P0 guard at b, a P0 guard one step from a.
    start_a = (3, 1)                   # ring 4; a=(3,0) is ring 3 -> inward step OK
    pre = AgonState(board={mid: (P1, "G"), b: (P0, "G"), start_a: (P0, "G")}, to_move=P0)
    after = g.apply_move(pre, f"{start_a[0]},{start_a[1]}>{a[0]},{a[1]}")
    if mid in after.board:
        fail("captured enemy guard was not lifted off the board")
    if after.hands[P1] != ["G"]:
        fail(f"captured guard not placed in owner's hand, hands={after.hands}")
    # Now it's P1's turn and they MUST rescue (every legal move is a '@' placement).
    rescue_moves = g.legal_moves(after)
    if not rescue_moves or any(not m.startswith("@") for m in rescue_moves):
        fail(f"P1 must be forced to rescue, got {rescue_moves}")
    # Rescue targets must all be vacant OUTER-RING cells.
    for m in rescue_moves:
        cq, cr = m[1:].split(",")
        if _ring(int(cq), int(cr)) != N:
            fail(f"guard rescue target {m} is not on the outer ring")
    rescued = g.apply_move(after, rescue_moves[0])
    rq, rr = rescue_moves[0][1:].split(",")
    if rescued.board.get((int(rq), int(rr))) != (P1, "G"):
        fail("rescued guard not re-entered onto the board")
    if rescued.hands[P1] != []:
        fail("hand not emptied after rescue")

    # Queen-first rescue: if both Q and G are captured, only '@' queen targets
    # are offered, and the queen may land anywhere but the throne.
    qg_state = AgonState(board={(5, 0): (P0, "G")}, to_move=P1,
                         hands={P0: [], P1: ["G", "Q"]})
    qmoves = g.legal_moves(qg_state)
    if THRONE in [tuple(int(x) for x in m[1:].split(",")) for m in qmoves]:
        fail("queen rescue offered the throne as a target")
    # queen rescue may use non-outer cells too (anywhere but throne / occupied)
    if not any(_ring(*tuple(int(x) for x in m[1:].split(","))) < N for m in qmoves):
        fail("queen rescue should allow interior cells")
    after_q = g.apply_move(qg_state, qmoves[0])
    if after_q.hands[P1] != ["G"]:
        fail("after queen rescue, only the guard should remain in hand")

    # ---- (5a) ENTHRONED WIN reached via apply_move -----------------------
    inner = list(_inner_ring())
    # Build a near-win: P0 queen one step from throne, 5 guards already on inner
    # cells, the 6th guard adjacent to the last open inner cell.
    open_inner = inner[0]
    filled_inner = inner[1:]            # five guards
    # queen sits at an outer neighbour of the throne? No -- queen must step to (0,0).
    # Place queen on an inner cell? It must MOVE onto throne, so put it adjacent.
    # Use a ring-1 cell as the queen's launch is impossible (throne is ring 0,
    # neighbours of throne are ring 1). Put queen on a ring-1 cell -> step to throne.
    # But all ring-1 cells must end as guards. So instead: queen already on throne,
    # and the final guard steps into the last open inner cell to complete the win.
    win_board = {THRONE: (P0, "Q")}
    for c in filled_inner:
        win_board[c] = (P0, "G")
    # sixth guard one step OUTSIDE open_inner, on ring 2, stepping inward to it.
    guard_src = None
    for nb in _neighbors(*open_inner):
        if _ring(*nb) == 2:
            guard_src = nb
            break
    if guard_src is None:
        fail("could not find a ring-2 launch cell for the final guard")
    win_board[guard_src] = (P0, "G")
    win_pre = AgonState(board=win_board, to_move=P0)
    if g.is_terminal(win_pre):
        fail("pre-win position should not already be terminal")
    won = g.apply_move(win_pre, f"{guard_src[0]},{guard_src[1]}>{open_inner[0]},{open_inner[1]}")
    if won.winner != P0 or won.win_kind != "enthroned":
        fail(f"enthroned win not detected: winner={won.winner} kind={won.win_kind}")
    if g.returns(won) != [1.0, -1.0]:
        fail(f"enthroned win returns wrong: {g.returns(won)}")

    # ---- (5b) SELF-BLOCK FORFEIT -----------------------------------------
    # Six P0 guards fill ring 1 but P0's queen is NOT on the throne -> P0 loses.
    forfeit_board = {c: (P0, "G") for c in inner}      # six guards, empty throne
    w, k = _check_end(forfeit_board, _queens_from_board(forfeit_board))
    if not (w == P1 and k == "forfeit"):
        fail(f"empty-throne self-block should forfeit to P1, got ({w},{k})")
    # Reach it via apply_move: 5 inner guards + one stepping into the 6th, no queen.
    fb = {c: (P0, "G") for c in inner[1:]}
    fsrc = None
    for nb in _neighbors(*inner[0]):
        if _ring(*nb) == 2:
            fsrc = nb
            break
    fb[fsrc] = (P0, "G")
    fpre = AgonState(board=fb, to_move=P0)
    fafter = g.apply_move(fpre, f"{fsrc[0]},{fsrc[1]}>{inner[0][0]},{inner[0][1]}")
    if fafter.winner != P1 or fafter.win_kind != "forfeit":
        fail(f"self-block via play not detected: winner={fafter.winner} kind={fafter.win_kind}")

    # ---- (6) conformance + serialize round-trip --------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(g, manifest, games=4, seed=3)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    rt = g.deserialize(g.serialize(won))
    if g.serialize(rt) != g.serialize(won):
        fail("serialize round-trip mismatch")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
