"""Standalone correctness anchor for Snort. Pure-stdlib; run with PYTHONPATH=.

Snort is the exact DUAL of Col: only the adjacency test is flipped (forbid
adjacency to the OPPONENT's colour instead of to your OWN). Anchors the three
defining rules plus a few hand-built positions:

  (1) a square grid board (default 5x5, with a working `size` option);
  (2) a turn colours an empty cell with YOUR colour that is NOT orthogonally
      adjacent to a cell holding the OPPONENT's colour (adjacency to your OWN
      colour is allowed; diagonals unrestricted);
  (3) normal play: the last player able to move WINS (no legal move = loss),
      reached via apply_move.

No published perft exists for Snort, so the anchor is baked rule asserts.
"""

import sys

from games.snort.game import Snort, SnortState


def check(cond, msg):
    if not cond:
        print("SELFTEST FAIL:", msg)
        sys.exit(1)


def main():
    g = Snort()

    # (1) Board: default 5x5, and a working size option.
    s0 = g.initial_state()
    check(s0.width == 5 and s0.height == 5, "default board is 5x5")
    r = g.render(s0)
    check(r["board"] == {"type": "square", "width": 5, "height": 5},
          "render emits a 5x5 square board")
    s3 = g.initial_state(options={"size": 3})
    check(s3.width == 3 and s3.height == 3, "size option yields a 3x3 board")
    s7 = g.initial_state(options={"size": 7})
    check(s7.width == 7 and s7.height == 7, "size option yields a 7x7 board")
    # Empty 5x5: every one of 25 cells is legal for the mover.
    check(len(g.legal_moves(s0)) == 25, "all 25 cells legal on empty 5x5")
    check(g.current_player(s0) == 0, "player 0 moves first")

    # (2a) A legal placement: place your colour, turn passes.
    s1 = g.apply_move(s0, "2,2")
    check(s1.board[(2, 2)] == 0, "P1 stone recorded with owner 0")
    check(g.current_player(s1) == 1, "turn passes to player 1")

    # (2b) THE DUAL-OF-COL RULE: adjacent-to-OPPONENT is forbidden;
    #      adjacent-to-OWN is allowed; diagonals unrestricted.
    # Hand-build a position: a single P0 stone at (1,1).
    # Player 1 (the opponent of that stone) to move:
    hand1 = SnortState(width=5, height=5, board={(1, 1): 0}, to_move=1)
    legal1 = set(g.legal_moves(hand1))
    # Orthogonal neighbours of (1,1) -> ILLEGAL for player 1 (adjacent to opponent).
    for cell in ["2,1", "0,1", "1,2", "1,0"]:
        check(cell not in legal1,
              f"placing next to OPPONENT's stone forbidden (Snort rule): {cell}")
    # Diagonal neighbours of (1,1) -> LEGAL (diagonals unrestricted).
    for cell in ["0,0", "2,2", "0,2", "2,0"]:
        check(cell in legal1, f"diagonal placement allowed: {cell}")

    # Player 0 (SAME colour as the stone) to move: adjacency to OWN is fine.
    hand0 = SnortState(width=5, height=5, board={(1, 1): 0}, to_move=0)
    legal0 = set(g.legal_moves(hand0))
    for cell in ["2,1", "0,1", "1,2", "1,0"]:
        check(cell in legal0,
              f"P1 may sit next to its OWN stone (Snort, opposite of Col): {cell}")

    # (3) Normal play, forced win reached via apply_move.
    # 1x3 strip: P0 colours the centre (0,1). Now for P1 BOTH ends (0,0)/(0,2)
    # are orthogonally adjacent to the OPPONENT's (P0) stone at (0,1) -> both
    # FORBIDDEN. P1 has no legal move and is stuck -> P0 (last mover) WINS, even
    # though two cells remain empty. (This is exactly where Snort differs from
    # Col: in Col those ends would be legal for P1.)
    s = SnortState(width=1, height=3, board={}, to_move=0)
    check(not g.is_terminal(s), "1x3 empty: not terminal")
    s = g.apply_move(s, "0,1")
    check(g.is_terminal(s), "1x3: terminal once P1 is stuck after centre play")
    check(s.winner == 0, "1x3: P0 (last mover) wins")
    check((0, 0) not in s.board and (0, 2) not in s.board,
          "1x3: both ends stayed empty at the win (stuck-before-full)")
    check(g.returns(s) == [1.0, -1.0], "returns reflect P0 win")

    # A full-board finish: 1x2 strip of the SAME colour. P0 plays (0,0); for P1
    # the only empty cell (0,1) is adjacent to OPPONENT -> P1 stuck immediately,
    # so confirm a multi-move same-colour fill instead via a 2x1 line where both
    # are P0's. Build it directly: P0 to move with one own stone; P0 may extend.
    line = SnortState(width=2, height=1, board={(0, 0): 0}, to_move=0)
    # (1,0) is adjacent to OWN (P0) stone -> allowed for P0.
    check("1,0" in set(g.legal_moves(line)),
          "same-colour adjacency allowed: P0 may extend next to own stone")
    full = g.apply_move(line, "1,0")
    check(g.is_terminal(full), "2x1 board full -> terminal")
    # P1 never could move (only cell touched an opponent? no opponent stones,
    # but board is full) -> P0 (last mover) wins.
    check(full.winner == 0, "2x1: P0 wins when board is full")

    # A position where the mover is ALREADY stuck the instant it's their turn:
    # P1 to move, surrounded by opponent (P0) stones on the only free axis.
    # 1x3 with P0 stones at both ends; P1 to move. (0,1) is orthogonally adjacent
    # to opponent stones at (0,0) and (0,2) -> no legal move for P1 at all.
    stuck = SnortState(width=1, height=3, board={(0, 0): 0, (0, 2): 0}, to_move=1)
    check(g.legal_moves(stuck) == [],
          "P1 has no legal move (only empty cell touches opponent)")

    # apply_move purity: original state untouched.
    base = g.initial_state()
    _ = g.apply_move(base, "0,0")
    check((0, 0) not in base.board, "apply_move did not mutate input state")

    # serialize round-trips.
    mid = g.apply_move(g.apply_move(g.initial_state(), "0,0"), "2,2")
    again = g.deserialize(g.serialize(mid))
    check(g.serialize(again) == g.serialize(mid), "serialize round-trips")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
