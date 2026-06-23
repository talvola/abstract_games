"""Seega correctness anchor — pure-stdlib, fast.

No published perft for Seega; the anchor is a set of baked rule assertions:
(1) board geometry + the placement phase (2 stones/turn, centre stays empty,
    each player ends with (size^2-1)/2 stones) then the movement phase;
(2) movement = one orthogonal step into an adjacent empty cell;
(3) active custodial capture removes a flanked enemy; a stone moving INTO a
    sandwich is safe; the centre cell is a safe square (no capture there);
(4) win = reduce the opponent below 2 stones, or blockade them;
plus the placement->movement transition and serialize round-trip.

Run:  PYTHONPATH=. python3 games/seega/selftest.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from games.seega.game import Seega, SeegaState, PLACE, MOVE  # noqa: E402


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_geometry_and_options():
    g = Seega()
    for size, per in [(5, 12), (7, 24), (9, 40)]:
        s = g.initial_state(options={"size": size})
        ok(s.size == size, f"size {size}")
        ok(s.phase == PLACE, "starts in placement")
        ok(g._per_player(s) == per, f"per-player count for size {size} == {per}")
        ok(g._centre(s) == (size // 2, size // 2), "centre is the middle cell")
        r = g.render(s)
        ok(r["board"]["width"] == size and r["board"]["height"] == size, "render board")
    # default and bad option fall back to 5
    ok(g.initial_state().size == 5, "default size 5")
    ok(g.initial_state(options={"size": 4}).size == 5, "bad size -> 5")


def test_placement_phase():
    g = Seega()
    s = g.initial_state()  # 5x5
    centre = g._centre(s)
    # centre is never a legal placement; all other empties are
    moves = g.legal_moves(s)
    ok(f"{centre[0]},{centre[1]}" not in moves, "centre not placeable")
    ok(len(moves) == 24, "24 placement spots on empty 5x5")

    # play out the whole placement deterministically, alternating 2-per-turn
    turn_player = []
    while s.phase == PLACE and not g.is_terminal(s):
        before = s.to_move
        mv = g.legal_moves(s)[0]
        s = g.apply_move(s, mv)
        turn_player.append(before)

    ok(s.phase == MOVE, "transitions to movement when full")
    # exactly the centre is empty
    ok(len(s.board) == 24, "24 stones placed")
    ok(centre not in s.board, "centre left empty")
    # each player placed 12
    c0 = sum(1 for v in s.board.values() if v == 0)
    c1 = sum(1 for v in s.board.values() if v == 1)
    ok(c0 == 12 and c1 == 12, f"12 each ({c0},{c1})")
    # players placed two consecutively each turn (pattern 0,0,1,1,0,0,...)
    ok(turn_player[0:4] == [0, 0, 1, 1], f"2-per-turn alternation: {turn_player[:4]}")
    # second placer (player 1) moves first in the movement phase
    ok(s.to_move == 1, "second placer (player 1) moves first in movement")


def test_custodial_capture_active():
    g = Seega()
    # 5x5, movement phase (centre is (2,2), avoid it). Enemy (player 1) at (2,0);
    # our anchor at (3,0); mover (1,1) steps up to (1,0):
    #   from (1,0): +x mid=(2,0) enemy, beyond=(3,0) friend -> capture.
    board = {(1, 1): 0, (2, 0): 1, (3, 0): 0,
             (0, 4): 0, (4, 4): 1}  # extra stones so neither side is <2
    s = SeegaState(board=dict(board), size=5, phase=MOVE, to_move=0)
    s2 = g.apply_move(s, "1,1>1,0")
    ok((2, 0) not in s2.board, "flanked enemy captured")
    ok(s2.board.get((1, 0)) == 0, "mover landed")
    ok(s2.to_move == 1, "turn passed")


def test_move_into_sandwich_is_safe():
    g = Seega()
    # Two enemy (player 1) stones at (1,0) and (3,0); player 0 stone steps INTO
    # (2,0) between them (off-centre). It must NOT be captured (mover is safe).
    board = {(1, 0): 1, (3, 0): 1, (2, 1): 0, (0, 4): 0, (4, 4): 1}
    s = SeegaState(board=dict(board), size=5, phase=MOVE, to_move=0)
    s2 = g.apply_move(s, "2,1>2,0")
    ok(s2.board.get((2, 0)) == 0, "stone moving into a sandwich survives")
    ok((1, 0) in s2.board and (3, 0) in s2.board, "the flankers are untouched")


def test_centre_is_safe():
    g = Seega()
    # 5x5 centre is (2,2). Put enemy stone ON the centre, flank it: it must
    # survive because the centre is a safe square.
    board = {(2, 2): 1, (1, 2): 0, (3, 1): 0, (0, 0): 0, (4, 4): 1}
    # player 0 moves (3,1)->(3,2): then from (3,2) dir -x mid=(2,2) enemy(centre)
    # beyond=(1,2) friend -> would capture, but centre is safe.
    s = SeegaState(board=dict(board), size=5, phase=MOVE, to_move=0)
    s2 = g.apply_move(s, "3,1>3,2")
    ok(s2.board.get((2, 2)) == 1, "stone on the centre is never captured")


def test_multi_direction_capture():
    g = Seega()
    # Mover lands and flanks enemies in two directions at once.
    # Mover (2,0)->(2,2)? not adjacent. Use single step (2,1)->(2,2).
    # At (2,2): +x mid (3,2)=enemy beyond (4,2)=friend -> cap
    #           -y mid (2,1)? that's where we came from. use +y: mid (2,3)=enemy beyond(2,4)=friend
    board = {
        (2, 1): 0,            # mover (steps down to 2,2)
        (3, 2): 1, (4, 2): 0,  # east sandwich
        (2, 3): 1, (2, 4): 0,  # south sandwich
        (0, 0): 0, (0, 1): 1,  # spare stones keep counts >=2
    }
    s = SeegaState(board=dict(board), size=5, phase=MOVE, to_move=0)
    s2 = g.apply_move(s, "2,1>2,2")
    ok((3, 2) not in s2.board and (2, 3) not in s2.board,
       "both flanked enemies captured in one move")


def test_win_reduce_below_two():
    g = Seega()
    # Player 1 has exactly 2 stones; capturing one leaves 1 -> player 0 wins.
    # Enemy at (2,0) (off-centre), anchor (3,0), mover (1,1)->(1,0) captures it.
    board = {(1, 1): 0, (2, 0): 1, (3, 0): 0, (0, 0): 0}
    board[(0, 4)] = 1   # player 1's second (and after capture, only) stone
    s = SeegaState(board=dict(board), size=5, phase=MOVE, to_move=0)
    s2 = g.apply_move(s, "1,1>1,0")  # captures (2,0)
    ok(g.is_terminal(s2), "terminal after reducing opponent below 2")
    ok(s2.winner == 0, "player 0 wins")
    ok(g.returns(s2) == [1.0, -1.0], "returns reflect player-0 win")


def test_blockade_loss():
    g = Seega()
    # Build a movement position where after player 0's move, player 1 has no
    # legal move -> player 0 wins. Tiny crafted board on 5x5 with walls of
    # player-0 stones boxing player 1's stones with no empty adjacent cell.
    # Player1 stones at (0,0),(0,1); player0 walls them in; one empty for the
    # mover to fill the last liberty.
    board = {
        (0, 0): 1, (0, 1): 1,
        (1, 0): 0, (1, 1): 0, (0, 2): 0,
        (2, 2): 0, (3, 3): 0,   # mover + spare (keep p0 >=2)
    }
    # currently player1 has no empty neighbour already? (0,0) nbrs:(1,0)occ,(0,1)occ
    # (0,1) nbrs: (0,0)occ,(0,2)occ,(1,1)occ -> already blockaded. Make to_move=1
    # to confirm blockade loss is detected on the OPPONENT after a p0 move.
    # Instead: leave (0,2) empty as p1's only liberty, then p0 fills it.
    board = {
        (0, 0): 1, (0, 1): 1,
        (1, 0): 0, (1, 1): 0,
        (0, 3): 0,          # mover steps (0,3)->(0,2) to plug the last liberty
        (3, 3): 0,          # spare so p0 has >=2 and isn't itself stuck
    }
    s = SeegaState(board=dict(board), size=5, phase=MOVE, to_move=0)
    # sanity: before the move player1 DOES have a move ((0,1)->(0,2))
    s_check = SeegaState(board=dict(board), size=5, phase=MOVE, to_move=1)
    ok(len(g._movement_moves(s_check)) > 0, "player1 has a move before being plugged")
    s2 = g.apply_move(s, "0,3>0,2")  # no capture here; just fills the liberty
    ok(g.is_terminal(s2) and s2.winner == 0, "opponent blockaded -> player 0 wins")


def test_serialize_roundtrip():
    g = Seega()
    s = g.initial_state(options={"size": 7})
    for _ in range(20):
        if g.is_terminal(s):
            break
        s = g.apply_move(s, g.legal_moves(s)[0])
    d = g.serialize(s)
    s2 = g.deserialize(d)
    ok(g.serialize(s2) == d, "serialize round-trips")
    # JSON-able
    import json
    json.dumps(d)


def test_full_random_game_terminates():
    import random
    g = Seega()
    rng = random.Random(1234)
    for size in (5, 7):
        s = g.initial_state(options={"size": size})
        steps = 0
        while not g.is_terminal(s):
            mv = rng.choice(g.legal_moves(s))
            s = g.apply_move(s, mv)
            steps += 1
            ok(steps < 5000, "game terminates within a sane ply bound")
        r = g.returns(s)
        ok(len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r), "well-formed returns")


def main():
    test_geometry_and_options()
    test_placement_phase()
    test_custodial_capture_active()
    test_move_into_sandwich_is_safe()
    test_centre_is_safe()
    test_multi_direction_capture()
    test_win_reduce_below_two()
    test_blockade_loss()
    test_serialize_roundtrip()
    test_full_random_game_terminates()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
