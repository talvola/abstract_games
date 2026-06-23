"""Clobber correctness anchor — pure-stdlib, fast.

No published perft exists for Clobber, so the anchor is a set of baked rule
assertions plus small-board combinatorial-game outcomes computed by full search:

  (1) the board starts COMPLETELY FILLED in a checkerboard — (c+r) even = player 0,
      odd = player 1 — on every supported size (default 5x6 + the size option);
  (2) a legal move takes one of YOUR stones onto an orthogonally ADJACENT cell
      holding an OPPONENT stone, removing it (your stone replaces it); nothing else
      is legal (no move onto empty / own / non-adjacent cells);
  (3) normal play — a player with no legal move LOSES (last to move wins), no draws;
  (4) tiny-board forced-win outcomes by exhaustive search (1x2/1x3/1x4/2x2/3x3 are
      first-player wins; 2x3 is a SECOND-player win), and a hand-built clobber.

Run:  PYTHONPATH=. python3 games/clobber/selftest.py
"""

from __future__ import annotations

import sys

from games.clobber.game import Clobber, CLState, SIZES


def check(cond, msg):
    if not cond:
        print("SELFTEST FAIL:", msg)
        sys.exit(1)


g = Clobber()


# (1) Checkerboard start, every cell filled, on every supported size.
for size, (w, h) in SIZES.items():
    s = g.initial_state(options={"size": size})
    check(s.width == w and s.height == h, f"{size}: dims {s.width}x{s.height} != {w}x{h}")
    check(len(s.board) == w * h, f"{size}: board not completely filled ({len(s.board)} != {w*h})")
    for c in range(w):
        for r in range(h):
            check((c, r) in s.board, f"{size}: cell {c},{r} missing")
            check(s.board[(c, r)] == (c + r) % 2,
                  f"{size}: cell {c},{r} colour {s.board[(c,r)]} != checkerboard {(c+r)%2}")
    check(g.current_player(s) == 0, f"{size}: player 0 should move first")

# Default size is 5x6.
sd = g.initial_state()
check((sd.width, sd.height) == (5, 6), f"default size {sd.width}x{sd.height} != 5x6")


# (2) Move rule: only onto an orthogonally adjacent OPPONENT stone.
# Hand-built 3x1 row: P0 P1 P0 at (0,0)(1,0)(2,0).
row = CLState(board={(0, 0): 0, (1, 0): 1, (2, 0): 0}, to_move=0, width=3, height=1)
lm = set(g.legal_moves(row))
# P0 stones are (0,0) and (2,0); both are adjacent to the P1 stone at (1,0).
check(lm == {"0,0>1,0", "2,0>1,0"}, f"3x1 P0 legal moves wrong: {sorted(lm)}")
# A clobber: 0,0 -> 1,0 removes the enemy and leaves P0 on (1,0).
after = g.apply_move(row, "0,0>1,0")
check((0, 0) not in after.board, "clobber: source cell still occupied")
check(after.board.get((1, 0)) == 0, "clobber: P0 stone did not replace the enemy at 1,0")
check(after.board.get((2, 0)) == 0, "clobber: untouched P0 stone vanished")
check(after.to_move == 1, "clobber: turn did not pass to player 1")
check(len(after.board) == 2, "clobber: should remove exactly one stone")

# No non-capturing moves: an isolated stone with an empty neighbour can't move there,
# and you cannot move onto your own stone or a non-adjacent enemy.
# Board: P0 at (0,0), empty (1,0), P0 at (2,0), P1 at (2,1) [non-adjacent to (0,0)].
mixed = CLState(board={(0, 0): 0, (2, 0): 0, (2, 1): 1}, to_move=0, width=3, height=2)
mm = set(g.legal_moves(mixed))
# Only (2,0) is orthogonally adjacent to the enemy (2,1).
check(mm == {"2,0>2,1"}, f"mixed board: expected only 2,0>2,1, got {sorted(mm)}")
check("0,0>1,0" not in mm, "illegal: moved onto an empty cell")
check("2,0>0,0" not in mm, "illegal: moved onto an own stone (also non-adjacent)")
check("0,0>2,1" not in mm, "illegal: moved onto a non-adjacent enemy")


# (3) Normal play: no legal move => the player to move loses.
# After P0 clobbers in the 3x1 row, player 1 has no stones at all -> P1 loses.
check(g.is_terminal(after), "3x1 after clobber should be terminal (P1 has no move)")
ret = g.returns(after)
check(ret == [1.0, -1.0], f"3x1 after clobber: P0 should win, got returns {ret}")

# A position where player 0 (to move) has NO move loses for player 0.
stuck = CLState(board={(0, 0): 0, (2, 0): 1}, to_move=0, width=3, height=1)
check(g.legal_moves(stuck) == [], "stuck: expected no legal moves")
check(g.is_terminal(stuck), "stuck: should be terminal")
check(g.returns(stuck) == [-1.0, 1.0], f"stuck: P0 (to move, no move) should lose, got {g.returns(stuck)}")


# (4) Small-board forced-win outcomes by exhaustive search.
def first_player_wins(s: CLState) -> bool:
    """True iff the player to move can force a win (normal play)."""
    moves = g.legal_moves(s)
    if not moves:
        return False            # no move -> mover loses
    for m in moves:
        if not first_player_wins(g.apply_move(s, m)):
            return True
    return False


def checker(w, h) -> CLState:
    return CLState(board={(c, r): (c + r) % 2 for c in range(w) for r in range(h)},
                   to_move=0, width=w, height=h)


# Baked outcomes (verified by this same search; cheap to recompute for these sizes).
expected = {
    (2, 1): True,    # 1x2  -> first player wins
    (3, 1): True,    # 1x3  -> first player wins
    (4, 1): True,    # 1x4  -> first player wins
    (2, 2): True,    # 2x2  -> first player wins
    (2, 3): False,   # 2x3  -> SECOND player wins (non-obvious)
    (3, 3): True,    # 3x3  -> first player wins
}
for (w, h), exp in expected.items():
    got = first_player_wins(checker(w, h))
    check(got == exp, f"{w}x{h}: first-player-wins {got} != expected {exp}")


# Termination sanity: each move removes exactly one stone (count strictly decreases).
s2 = checker(2, 2)
before_n = len(s2.board)
s2 = g.apply_move(s2, g.legal_moves(s2)[0])
check(len(s2.board) == before_n - 1, "a move must remove exactly one stone")


# Serialize round-trip.
for size in SIZES:
    s = g.initial_state(options={"size": size})
    s = g.apply_move(s, g.legal_moves(s)[0])
    d = g.serialize(s)
    s2 = g.deserialize(d)
    check(g.serialize(s2) == d, f"{size}: serialize round-trip mismatch")


print("SELFTEST OK")
