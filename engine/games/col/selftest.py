"""Standalone correctness anchor for Col. Pure-stdlib; run with PYTHONPATH=.

Anchors the three defining rules plus a few hand-built positions:

  (1) a square grid board (default 5x5, with a working `size` option);
  (2) a turn colours an empty cell with YOUR colour that is NOT orthogonally
      adjacent to a cell already holding YOUR OWN colour (adjacency to the
      OPPONENT's colour is allowed; diagonals unrestricted);
  (3) normal play: the last player able to move WINS (no legal move = loss),
      reached via apply_move.

No published perft exists for Col, so the anchor is baked rule asserts.
"""

import sys

from games.col.game import Col, ColState


def check(cond, msg):
    if not cond:
        print("SELFTEST FAIL:", msg)
        sys.exit(1)


def main():
    g = Col()

    # (1) Board: default 5x5, and a working size option.
    s0 = g.initial_state()
    check(s0.width == 5 and s0.height == 5, "default board is 5x5")
    r = g.render(s0)
    check(r["board"] == {"type": "square", "width": 5, "height": 5},
          "render emits a 5x5 square board")
    s3 = g.initial_state(options={"size": 3})
    check(s3.width == 3 and s3.height == 3, "size option yields a 3x3 board")
    # Empty 5x5: every one of 25 cells is legal for the mover.
    check(len(g.legal_moves(s0)) == 25, "all 25 cells legal on empty 5x5")
    check(g.current_player(s0) == 0, "player 0 moves first")

    # (2a) A legal placement: place your colour, opponent then has restrictions.
    s1 = g.apply_move(s0, "2,2")
    check(s1.board[(2, 2)] == 0, "P1 stone recorded with owner 0")
    check(g.current_player(s1) == 1, "turn passes to player 1")

    # (2b) Adjacent-to-OWN is forbidden; adjacent-to-OPPONENT is allowed.
    # Build a position by hand: player 0 stone at (1,1); player 0 to move.
    hand = ColState(width=5, height=5, board={(1, 1): 0}, to_move=0)
    legal0 = set(g.legal_moves(hand))
    # Orthogonal neighbours of (1,1) -> illegal for player 0 (own colour).
    for cell in ["2,1", "0,1", "1,2", "1,0"]:
        check(cell not in legal0, f"placing P1 next to own stone forbidden: {cell}")
    # Diagonal neighbours of (1,1) -> legal (diagonals unrestricted).
    for cell in ["0,0", "2,2", "0,2", "2,0"]:
        check(cell in legal0, f"diagonal placement allowed for P1: {cell}")

    # Now player 1 facing the same single P0 stone: adjacency to OPPONENT is fine.
    hand1 = ColState(width=5, height=5, board={(1, 1): 0}, to_move=1)
    legal1 = set(g.legal_moves(hand1))
    for cell in ["2,1", "0,1", "1,2", "1,0"]:
        check(cell in legal1, f"P2 may sit next to opponent's stone: {cell}")

    # (3) Normal play: last to move wins, reached via apply_move. Use a 1x3 strip
    # (build directly) so we can force a clean finish.
    #   Cells (0,0),(0,1),(0,2). P0 colours the middle (0,1). Then neither (0,0)
    #   nor (0,2) is adjacent to a P1 stone, but they ARE both adjacent to... no.
    # Simpler deterministic line: 1x2 strip. P0 colours (0,0); (0,1) is adjacent
    # to P1's own? No — for P1 it's adjacent to OPPONENT, allowed; so P1 plays
    # (0,1); board full; P0 has no move -> P1 (last mover) wins.
    strip = ColState(width=1, height=2, board={}, to_move=0)
    a = g.apply_move(strip, "0,0")          # P0 plays
    check(not g.is_terminal(a), "1x2: not terminal after first move")
    b = g.apply_move(a, "0,1")              # P1 plays (adjacent to opponent OK)
    check(g.is_terminal(b), "1x2 board full -> terminal")
    check(b.winner == 1, "1x2: last mover (P1) wins")
    check(g.returns(b) == [-1.0, 1.0], "returns reflect P2 win")

    # A forced win where a player gets STUCK before the board is full.
    # 1x3 strip: P0 plays the centre (0,1). Now for P1, both ends (0,0)/(0,2) are
    # adjacent only to OPPONENT colour -> legal. P1 plays (0,0). For P0, the only
    # empty cell (0,2) is orthogonally adjacent to P0's OWN stone at (0,1) ->
    # FORBIDDEN. P0 has no legal move and is stuck -> P1 (last mover) wins, even
    # though one cell remains empty. This exercises the "stuck before full" path.
    s = ColState(width=1, height=3, board={}, to_move=0)
    s = g.apply_move(s, "0,1")
    check(not g.is_terminal(s), "1x3: alive after centre")
    s = g.apply_move(s, "0,0")
    check(g.is_terminal(s), "1x3: terminal once P0 is stuck (cell (0,2) blocked)")
    check(s.winner == 1, "1x3: P1 wins, board NOT full (one cell unplayable)")
    check((0, 2) not in s.board, "1x3: (0,2) stayed empty at the win")

    # A position where the mover is ALREADY stuck the instant it's their turn:
    # 1x3 with P0 stones at both ends; P0 to move. (0,1) is orthogonally adjacent
    # to own stones at (0,0) and (0,2) -> no legal move for P0 at all.
    stuck = ColState(width=1, height=3, board={(0, 0): 0, (0, 2): 0}, to_move=0)
    check(g.legal_moves(stuck) == [], "P0 has no legal move (surrounded by own)")

    # apply_move purity: original state untouched.
    base = g.initial_state()
    _ = g.apply_move(base, "0,0")
    check((0, 0) not in base.board, "apply_move did not mutate input state")

    # serialize round-trips.
    mid = g.apply_move(g.apply_move(g.initial_state(), "2,2"), "2,3")
    again = g.deserialize(g.serialize(mid))
    check(g.serialize(again) == g.serialize(mid), "serialize round-trips")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
