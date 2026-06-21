#!/usr/bin/env python3
"""Correctness anchor for Dou Shou Qi (Jungle).

No published perft/node count exists for this game, so the anchor is
*conformance* (random games terminate, with legal moves at every non-terminal
node, serialize round-trips) plus a set of hand-built **rule positions** that
pin down the Jungle-specific rules:

  * the rank capture hierarchy Elephant > Lion > Tiger > Leopard > Wolf > Dog >
    Cat > Rat, with the single exception that the Rat beats the Elephant (and
    the Elephant cannot take the Rat);
  * Lion / Tiger jumping straight across the river, blocked when a Rat sits in
    the water on the path;
  * only the Rat may enter the water, and a Rat in the water can neither capture
    nor be captured across the land/water boundary (so it can't take a land
    Elephant);
  * an enemy piece on your trap is demoted to rank 0 and capturable by anything;
  * you win by entering the enemy den, and you may not enter your own den.

Pure stdlib + the agp package only. Run with:

    PYTHONPATH=. python3 games/dou_shou_qi/selftest.py

Prints "SELFTEST OK" and exits 0 on success; nonzero on failure.
"""

from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.conformance import check as conformance_check  # noqa: E402

import importlib.util  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("dsq_game", os.path.join(_HERE, "game.py"))
_mod = importlib.util.module_from_spec(_spec)
sys.modules["dsq_game"] = _mod
_spec.loader.exec_module(_mod)

DouShouQi = _mod.DouShouQi
DSQState = _mod.DSQState
DEN = _mod.DEN
WATER = _mod.WATER
TRAPS = _mod.TRAPS

G = DouShouQi()

# rank values for readability
ELE, LION, TIGER, LEOP, WOLF, DOG, CAT, RAT = 8, 7, 6, 5, 4, 3, 2, 1


def fail(msg):
    print("SELFTEST FAILED:", msg, file=sys.stderr)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def state(pieces, to_move=0, ply=0):
    """pieces: dict (c,r) -> (player, rank)."""
    return DSQState(board=dict(pieces), to_move=to_move, winner=None, ply=ply)


def dests_from(s, frm):
    out = set()
    for m in G.legal_moves(s):
        a, b = m.split(">")
        if a == f"{frm[0]},{frm[1]}":
            c, r = b.split(",")
            out.add((int(c), int(r)))
    return out


def can_capture(attacker, target):
    """High-level helper: place `attacker` adjacent to `target` on dry land in
    open space and report whether the capture move is legal."""
    # attacker at (3,4)? avoid water/dens; use a dry area near centre-top.
    a_cell = (3, 3)
    t_cell = (3, 2)   # one square 'down' (toward row 0)
    s = state({a_cell: attacker, t_cell: target}, to_move=attacker[0])
    return t_cell in dests_from(s, a_cell)


# --------------------------------------------------------------------------- #
def test_conformance():
    with open(os.path.join(_HERE, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = conformance_check(G, manifest, games=30, seed=11)
    if not rep.ok:
        fail("conformance:\n" + rep.summary())


# --------------------------------------------------------------------------- #
def test_start_position():
    s0 = G.initial_state()
    check(not G.is_terminal(s0), "start position must not be terminal")
    check(G.current_player(s0) == 0, "player 0 moves first")
    check(len(s0.board) == 16, f"expected 16 pieces at start, got {len(s0.board)}")
    # each side has exactly one of each rank
    for pl in (0, 1):
        ranks = sorted(rk for (p, rk) in s0.board.values() if p == pl)
        check(ranks == [1, 2, 3, 4, 5, 6, 7, 8],
              f"player {pl} should have one of each rank, got {ranks}")
    # serialize round-trips
    d = G.serialize(s0)
    check(G.serialize(G.deserialize(d)) == d, "serialize must round-trip")


# --------------------------------------------------------------------------- #
def test_rank_hierarchy():
    order = [ELE, LION, TIGER, LEOP, WOLF, DOG, CAT, RAT]
    # strictly-higher beats strictly-lower; equal beats equal; lower never beats
    # higher (except the Rat/Elephant special case handled separately).
    for i, hi in enumerate(order):
        for j, lo in enumerate(order):
            if {hi, lo} == {ELE, RAT}:
                continue  # special-cased below
            can = can_capture((0, hi), (1, lo))
            if i <= j:   # hi has higher-or-equal rank value
                check(can, f"rank {hi} should capture rank {lo}")
            else:
                check(not can, f"rank {hi} should NOT capture rank {lo}")
    # equal ranks capture each other
    for rk in order:
        check(can_capture((0, rk), (1, rk)), f"rank {rk} should capture equal rank")


def test_rat_elephant_special():
    check(can_capture((0, RAT), (1, ELE)), "Rat must capture Elephant")
    check(not can_capture((0, ELE), (1, RAT)), "Elephant must NOT capture Rat")


# --------------------------------------------------------------------------- #
def test_only_rat_in_water():
    # pick a water cell with a dry neighbour: (1,3) has dry neighbour (0,3).
    wcell = (1, 3)
    check(wcell in WATER, "test setup: (1,3) must be water")
    dry = (0, 3)
    # a Wolf on the dry bank may NOT step into the water
    s = state({dry: (0, WOLF)}, to_move=0)
    check(wcell not in dests_from(s, dry), "non-Rat must not enter water")
    # a Rat on the dry bank MAY step into the water
    s = state({dry: (0, RAT)}, to_move=0)
    check(wcell in dests_from(s, dry), "Rat must be able to enter water")


def test_rat_cannot_capture_across_bank():
    # Water Rat at (1,3); enemy Elephant on land at (0,3) (adjacent, dry).
    s = state({(1, 3): (0, RAT), (0, 3): (1, ELE)}, to_move=0)
    check((0, 3) not in dests_from(s, (1, 3)),
          "Rat in water must NOT capture a land piece (Elephant)")
    # And the land piece cannot capture the water Rat either: enemy Wolf to move.
    s = state({(1, 3): (1, RAT), (0, 3): (0, WOLF)}, to_move=0)
    check((1, 3) not in dests_from(s, (0, 3)),
          "land piece must NOT capture a Rat in the water")
    # Two rats both in the water (adjacent) CAN capture each other.
    s = state({(1, 3): (0, RAT), (2, 3): (1, RAT)}, to_move=0)
    check((2, 3) in dests_from(s, (1, 3)),
          "a water Rat should capture an adjacent enemy water Rat")


# --------------------------------------------------------------------------- #
def test_lion_tiger_jump():
    # Vertical jump over the left pool (cols 1, rows 3-5). Lion on (1,2) jumps to
    # (1,6) across rows 3,4,5.
    for rank in (LION, TIGER):
        s = state({(1, 2): (0, rank)}, to_move=0)
        d = dests_from(s, (1, 2))
        check((1, 6) in d, f"rank {rank} should jump vertically across the river to (1,6)")
        # horizontal jump: piece on (0,4) jumps across cols 1,2 to (3,4).
        s = state({(0, 4): (0, rank)}, to_move=0)
        d = dests_from(s, (0, 4))
        check((3, 4) in d, f"rank {rank} should jump horizontally across the river to (3,4)")


def test_jump_blocked_by_rat_in_water():
    # A Rat in the water on the path blocks the Lion's jump.
    s = state({(1, 2): (0, LION), (1, 4): (1, RAT)}, to_move=0)
    check((1, 6) not in dests_from(s, (1, 2)),
          "a Rat in the water on the path must block the Lion jump")
    # own-colour Rat in the water also blocks
    s = state({(1, 2): (0, LION), (1, 4): (0, RAT)}, to_move=0)
    check((1, 6) not in dests_from(s, (1, 2)),
          "a friendly Rat in the water on the path must also block the jump")
    # a Rat NOT in the path does not block (control): rat on the right pool.
    s = state({(1, 2): (0, LION), (4, 4): (1, RAT)}, to_move=0)
    check((1, 6) in dests_from(s, (1, 2)),
          "a Rat off the leap path must NOT block the jump")


def test_jump_captures_on_landing():
    # Lion jumps and lands on an enemy Cat (lower rank) -> capture allowed.
    s = state({(1, 2): (0, LION), (1, 6): (1, CAT)}, to_move=0)
    check((1, 6) in dests_from(s, (1, 2)), "Lion jump should capture weaker piece on landing")
    # Landing on an enemy Elephant (higher rank) is NOT allowed.
    s = state({(1, 2): (0, LION), (1, 6): (1, ELE)}, to_move=0)
    check((1, 6) not in dests_from(s, (1, 2)),
          "Lion jump must NOT capture a stronger piece on landing")


# --------------------------------------------------------------------------- #
def test_trap_demotes_enemy():
    # Enemy Elephant sits on one of player 0's traps (2,0). Player 0's Cat (rank
    # 2) on (2,1) should be able to capture it (Elephant demoted to 0).
    trap = (2, 0)
    check(trap in TRAPS[0], "test setup: (2,0) is a player-0 trap")
    s = state({(2, 1): (0, CAT), trap: (1, ELE)}, to_move=0)
    check(trap in dests_from(s, (2, 1)),
          "any piece must capture an enemy on your trap (rank treated as 0)")
    # But a piece on its OWN trap is not demoted: player 1 Elephant on player 1's
    # trap cannot be taken by a weaker player-0 piece that somehow reaches it.
    ptrap = (2, 8)  # player 1's trap
    s = state({(2, 7): (0, CAT), ptrap: (1, ELE)}, to_move=0)
    check(ptrap not in dests_from(s, (2, 7)),
          "an enemy piece on its OWN trap is not demoted")


# --------------------------------------------------------------------------- #
def test_den_rules():
    # You may not enter your OWN den. Player 0's den is (3,0); a Red piece on
    # (3,1) must not be able to step onto (3,0).
    own_den = DEN[0]
    s = state({(3, 1): (0, WOLF)}, to_move=0)
    check(own_den not in dests_from(s, (3, 1)), "must not enter your own den")
    # You WIN by entering the enemy den. Player 0 piece adjacent to enemy den
    # (3,8); step in -> winner 0, terminal.
    enemy_den = DEN[1]
    s = state({(3, 7): (0, WOLF)}, to_move=0)
    check(enemy_den in dests_from(s, (3, 7)), "must be able to enter the enemy den")
    s2 = G.apply_move(s, "3,7>3,8")
    check(s2.winner == 0, "entering the enemy den must win for the mover")
    check(G.is_terminal(s2), "a den win must be terminal")
    check(G.returns(s2) == [1.0, -1.0], f"den win returns wrong: {G.returns(s2)}")


def test_no_move_loses():
    # Player 0 has a single Rat in the corner (0,0). Its only neighbours are
    # (1,0) and (0,1); occupy both with uncapturable HIGHER-rank enemies (Lion
    # and Tiger, both > Rat and not the Elephant) so the Rat has no legal move.
    # (0,0) is not a den or trap, so the only constraint is the rank rule.
    s = state({(0, 0): (0, RAT), (1, 0): (1, LION), (0, 1): (1, TIGER)},
              to_move=0)
    check(G.legal_moves(s) == [], "expected a fully blocked side to have no moves")
    check(G.is_terminal(s), "no-move position must be terminal")
    check(G.returns(s) == [-1.0, 1.0], f"no-move side should lose, got {G.returns(s)}")


def main():
    test_conformance()
    test_start_position()
    test_rank_hierarchy()
    test_rat_elephant_special()
    test_only_rat_in_water()
    test_rat_cannot_capture_across_bank()
    test_lion_tiger_jump()
    test_jump_blocked_by_rat_in_water()
    test_jump_captures_on_landing()
    test_trap_demotes_enemy()
    test_den_rules()
    test_no_move_loses()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
