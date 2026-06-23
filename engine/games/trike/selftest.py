"""Standalone correctness anchor for Trike (pure stdlib; fast).

Run: PYTHONPATH=. python3 games/trike/selftest.py

Trike has no published perft, so the anchor is a set of baked rule assertions:
  (1) a TRIANGULAR board of hexes (side N), rendered via polygon (hex) cells;
  (2) ONE shared neutral pawn; a turn slides it in a straight line any distance
      over EMPTY cells (6 hex directions, no jumping, never onto an occupied cell)
      and drops a stone of the mover's colour on the landing cell;
  (3) the game ENDS when the pawn is trapped (no empty neighbour);
  (4) SCORING: the player owning more stones on the pawn's final cell + its
      adjacent cells wins;
  plus a hand-built pawn move+drop and a trapped-pawn end score, and the pie swap.
"""

import sys

from games.trike.game import Trike, TrikeState, WHITE, BLUE, DIRS


def check(cond, msg):
    if not cond:
        print("SELFTEST FAIL:", msg)
        sys.exit(1)


def main():
    g = Trike()

    # (1) triangular board of hexes, polygon cells -------------------------
    for size in (7, 9, 11, 13):
        s = g.initial_state({"size": size})
        cells = g._cells(size)
        check(len(cells) == size * (size + 1) // 2,
              f"size {size}: triangle should have N(N+1)/2 cells, got {len(cells)}")
        # rendered as polygon hexes (6 vertices each)
        spec = g.render(s)
        check(spec["board"]["type"] == "polygons", "board must render as polygons")
        check(all(len(c["points"]) == 6 for c in spec["board"]["cells"]),
              "every cell must be a hexagon (6 vertices)")
    check(len(DIRS) == 6, "there must be exactly 6 hex directions")

    # opening: pawn is None, every cell is a legal opening placement -------
    s = g.initial_state({"size": 11})
    check(s.pawn is None, "no pawn before the opening")
    check(g.current_player(s) == WHITE, "host (white) opens")
    opening = g.legal_moves(s)
    check(len(opening) == 11 * 12 // 2, "opening can place on any cell")
    check(not g.is_terminal(s), "fresh game is not terminal")

    # (2) a turn places a stone + moves the pawn there ---------------------
    s1 = g.apply_move(s, "5,2")
    check(s1.pawn == (5, 2), "pawn lands on the chosen opening cell")
    check(s1.board[(5, 2)] == WHITE, "host's stone dropped under the pawn")
    check(s1.to_move == BLUE, "turn passes to the guest")
    check(s1 != s and s.pawn is None, "apply_move must not mutate the input state")

    # pie rule available on the guest's first turn, recolours the lone stone
    moves = g.legal_moves(s1)
    check("swap" in moves, "pie swap offered to the guest on turn 1")
    swapped = g.apply_move(s1, "swap")
    check(swapped.board[(5, 2)] == BLUE, "swap recolours the opening stone to the guest")
    check(swapped.pawn == (5, 2), "swap leaves the pawn in place")
    check(swapped.to_move == WHITE, "after swap the turn passes back")

    # straight-line slide over empty cells, no jumping --------------------
    # Build a position on size 5 with a blocker so the pawn cannot pass it.
    s2 = TrikeState(size=5, board={(2, 0): WHITE, (4, 0): BLUE},
                    pawn=(2, 0), to_move=BLUE, ply=2)
    targets = {tuple(map(int, m.split(","))) for m in g.legal_moves(s2) if m != "swap"}
    # Going "down-left-edge" direction (1,0): (3,0) is empty and reachable;
    # (4,0) is occupied so the pawn stops before it and CANNOT land on/jump it.
    check((3, 0) in targets, "pawn can slide to the empty (3,0)")
    check((4, 0) not in targets, "pawn may not land on an occupied cell")
    check(all(t != (2, 0) for t in targets), "pawn never stays put / lands on its own cell")
    # apply a slide and confirm stone dropped on landing cell only
    s3 = g.apply_move(s2, "3,0")
    check(s3.pawn == (3, 0) and s3.board[(3, 0)] == BLUE, "slide drops mover's stone on landing")
    check((2, 0) in s3.board and s3.board[(2, 0)] == WHITE, "old stones are untouched")

    # (3) trapped pawn ends the game --------------------------------------
    # Apex (0,0) on a tiny board only neighbours (1,0) and (1,1); fill both.
    trapped = TrikeState(size=2, board={(0, 0): WHITE, (1, 0): WHITE, (1, 1): BLUE},
                         pawn=(0, 0), to_move=BLUE, ply=3)
    check(g.is_terminal(trapped), "pawn with no empty neighbour is trapped (terminal)")
    check(g.legal_moves(trapped) == [], "trapped position has no legal moves")

    # (4) scoring: pawn cell + adjacent, majority wins --------------------
    w, b = g._scores(trapped)
    # cell (0,0)=W under pawn, neighbours (1,0)=W, (1,1)=B -> white 2, blue 1
    check((w, b) == (2, 1), f"scores should be white 2 / blue 1, got {w}/{b}")
    check(g.returns(trapped) == [1.0, -1.0], "higher score (white) wins")

    # symmetric blue-majority trap
    trapped_b = TrikeState(size=2, board={(0, 0): BLUE, (1, 0): BLUE, (1, 1): WHITE},
                           pawn=(0, 0), to_move=WHITE, ply=3)
    check(g.returns(trapped_b) == [-1.0, 1.0], "blue majority -> blue wins")

    # reach a trapped end via apply_move from the opening (not hand-built) -
    # size 2: open at apex, then the pawn is forced down and gets trapped.
    r = g.initial_state({"size": 2})
    r = g.apply_move(r, "0,0")          # white opens at apex, pawn (0,0)
    check(not g.is_terminal(r), "after one move on size-2 the pawn can still move")
    # blue must slide to (1,0) or (1,1)
    blue_moves = [m for m in g.legal_moves(r) if m != "swap"]
    check(set(blue_moves) == {"1,0", "1,1"}, f"pawn at apex reaches the two base cells, got {blue_moves}")
    r = g.apply_move(r, "1,0")          # blue stone (1,0), pawn there
    # white must take the last empty cell (1,1); then pawn is trapped
    white_moves = g.legal_moves(r)
    check(white_moves == ["1,1"], f"only (1,1) remains, got {white_moves}")
    r = g.apply_move(r, "1,1")
    check(g.is_terminal(r), "board full around the pawn -> trapped")
    # pawn now on (1,1)=WHITE; neighbours on-board: (1,0)=BLUE, (0,0)=WHITE
    w2, b2 = g._scores(r)
    check((w2, b2) == (2, 1), f"reached end score white 2/blue 1, got {w2}/{b2}")

    # serialize round-trips ------------------------------------------------
    for st in (s, s1, swapped, s3, trapped, r):
        d = g.serialize(st)
        check(g.serialize(g.deserialize(d)) == d, "serialize must round-trip")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
