"""Squava selftest — correctness anchor (pure stdlib, fast).

No published perft exists for Squava; the anchor is a set of baked rule
assertions plus a few hand-built rule-specific positions:

 (1) pure placement: players alternate placing one stone of their colour on an
     empty cell (no movement, like gomoku);
 (2) making FOUR-in-a-row (h/v/diag) is an immediate WIN for the placer;
 (3) making exactly THREE-in-a-row (not part of a four) is an immediate LOSS for
     the placer (the misère twist);
 (4) a full 5x5 board with no four and no decisive three is a draw;
 (5) a placement that makes BOTH a three and a four simultaneously is a WIN
     (four takes precedence).

Run:  PYTHONPATH=. python3 games/squava/selftest.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.squava.game import Squava, SquavaState  # noqa: E402

G = Squava()


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def build(stones):
    """Build a state by directly setting the board (no win evaluation).

    stones: dict {(c,r): player}. Used to set up a position whose decisive
    move we then play via apply_move.
    """
    return SquavaState(board=dict(stones), to_move=0, winner=None)


# ---------------------------------------------------------------------------
# (1) Pure placement: alternation, one stone per turn, no movement/removal.
# ---------------------------------------------------------------------------
def test_placement():
    s = G.initial_state()
    if G.current_player(s) != 0:
        fail("Black (player 0) must move first")
    if len(G.legal_moves(s)) != 25:
        fail("empty 5x5 must have 25 legal moves")

    s1 = G.apply_move(s, "2,2")
    if G.current_player(s1) != 1:
        fail("turn must pass to player 1 after a placement")
    if s1.board.get((2, 2)) != 0:
        fail("placed stone must belong to the placer")
    # original state untouched (purity)
    if (2, 2) in s.board:
        fail("apply_move must not mutate the input state")
    if len(G.legal_moves(s1)) != 24:
        fail("one fewer legal move after a placement")

    s2 = G.apply_move(s1, "0,0")
    if s2.board.get((0, 0)) != 1:
        fail("second placement must belong to player 1")
    # cannot place on an occupied cell
    if "2,2" in G.legal_moves(s2):
        fail("occupied cell must not be a legal move")


# ---------------------------------------------------------------------------
# (2) FOUR in a row = WIN for the placer (horizontal, vertical, diagonal).
# ---------------------------------------------------------------------------
def test_four_wins():
    # Horizontal four: Black on (0,0),(1,0),(2,0); plays (3,0) to complete.
    s = build({(0, 0): 0, (1, 0): 0, (2, 0): 0})
    out = G.apply_move(s, "3,0")
    if out.winner != 0:
        fail("horizontal four must WIN for the placer (player 0)")
    if not G.is_terminal(out):
        fail("a four-win position must be terminal")
    if G.returns(out) != [1.0, -1.0]:
        fail("placer-0 win must return [+1, -1]")

    # Vertical four for player 1.
    s = SquavaState(board={(2, 0): 1, (2, 1): 1, (2, 2): 1}, to_move=1)
    out = G.apply_move(s, "2,3")
    if out.winner != 1:
        fail("vertical four must WIN for the placer (player 1)")
    if G.returns(out) != [-1.0, 1.0]:
        fail("placer-1 win must return [-1, +1]")

    # Diagonal four (down-right).
    s = build({(0, 0): 0, (1, 1): 0, (2, 2): 0})
    out = G.apply_move(s, "3,3")
    if out.winner != 0:
        fail("diagonal four must WIN for the placer")

    # Anti-diagonal four (down-left).
    s = build({(3, 0): 0, (2, 1): 0, (1, 2): 0})
    out = G.apply_move(s, "0,3")
    if out.winner != 0:
        fail("anti-diagonal four must WIN for the placer")

    # Completing a four by filling a GAP in the middle of a run also wins.
    s = build({(0, 0): 0, (1, 0): 0, (3, 0): 0})
    out = G.apply_move(s, "2,0")  # ...XX_X -> XXXX
    if out.winner != 0:
        fail("filling the gap to make a four must WIN")


# ---------------------------------------------------------------------------
# (3) Exactly THREE in a row (not part of a four) = LOSS for the placer.
# ---------------------------------------------------------------------------
def test_three_loses():
    # Horizontal three: Black on (0,0),(1,0); plays (2,0) -> exactly three.
    s = build({(0, 0): 0, (1, 0): 0})
    out = G.apply_move(s, "2,0")
    if out.winner != 1:
        fail("making exactly three must LOSE for the placer (winner=opponent)")
    if not G.is_terminal(out):
        fail("a three-loss position must be terminal")
    if G.returns(out) != [-1.0, 1.0]:
        fail("placer-0 making a three loses -> [-1, +1]")

    # Vertical three for player 1 -> player 0 wins.
    s = SquavaState(board={(4, 0): 1, (4, 1): 1}, to_move=1)
    out = G.apply_move(s, "4,2")
    if out.winner != 0:
        fail("player 1 making a three must hand the win to player 0")
    if G.returns(out) != [1.0, -1.0]:
        fail("placer-1 making a three loses -> [+1, -1]")

    # Diagonal three.
    s = build({(0, 0): 0, (1, 1): 0})
    out = G.apply_move(s, "2,2")
    if out.winner != 1:
        fail("diagonal three must LOSE for the placer")

    # A placement making only a TWO is neither win nor loss (game continues).
    s = build({(0, 0): 0})
    out = G.apply_move(s, "1,0")
    if out.winner is not None:
        fail("making only a two must not decide the game")
    if G.is_terminal(out):
        fail("a two-in-a-row position must not be terminal")


# ---------------------------------------------------------------------------
# (5) Simultaneous THREE and FOUR -> WIN (four takes precedence).
# ---------------------------------------------------------------------------
def test_four_beats_three():
    # Black has (0,0),(1,0),(2,0) [a horizontal three already on board] and a
    # vertical pair (0,1),(0,2). Playing (0,0)? — instead set it up so the new
    # stone simultaneously forms a 3 on one axis and a 4 on another.
    #
    # New stone at (3,0): horizontally it completes (0,0),(1,0),(2,0),(3,0) = a
    # FOUR. Also give it a vertical run of exactly three through (3,0):
    # (3,1),(3,2) already Black -> (3,0),(3,1),(3,2) = a THREE.
    s = build({
        (0, 0): 0, (1, 0): 0, (2, 0): 0,   # horizontal three awaiting (3,0)
        (3, 1): 0, (3, 2): 0,              # vertical pair below (3,0)
    })
    out = G.apply_move(s, "3,0")
    # Through (3,0): horizontal run = 4 (win), vertical run = 3 (would lose).
    if out.winner != 0:
        fail("a placement making BOTH a 3 and a 4 must WIN (four precedence)")
    if G.returns(out) != [1.0, -1.0]:
        fail("four-takes-precedence must return a win [+1, -1]")


# ---------------------------------------------------------------------------
# (4) Full board, no four and no decisive three -> DRAW.
# ---------------------------------------------------------------------------
def test_full_board_draw():
    # Hand-built 5x5 filling with no run >= 3 of either colour anywhere.
    # Pattern guarantees: in every row/col/diagonal no three same-colour stones
    # are consecutive. We use a checker-of-pairs layout verified below.
    #   row0: 0 0 1 1 0
    #   row1: 1 1 0 0 1
    #   row2: 0 0 1 1 0
    #   row3: 1 1 0 0 1
    #   row4: 0 0 1 1 0
    layout = [
        [0, 0, 1, 1, 0],
        [1, 1, 0, 0, 1],
        [0, 0, 1, 1, 0],
        [1, 1, 0, 0, 1],
        [0, 0, 1, 1, 0],
    ]
    board = {}
    for r in range(5):
        for c in range(5):
            board[(c, r)] = layout[r][c]
    s = SquavaState(board=board, to_move=0, winner=None)

    # Verify no cell sits in a run of 3+ (so no win/loss would ever have fired).
    from games.squava.game import _max_run
    for (c, r), p in board.items():
        if _max_run(board, (c, r), p) >= 3:
            fail(f"draw layout invalid: run >=3 through {(c, r)}")

    if len(s.board) != 25:
        fail("draw board must be full (25 stones)")
    if not G.is_terminal(s):
        fail("full board with no decision must be terminal")
    if s.winner is not None:
        fail("draw board must have no winner")
    if G.returns(s) != [0.0, 0.0]:
        fail("draw must return [0, 0]")


# ---------------------------------------------------------------------------
# Serialization round-trip.
# ---------------------------------------------------------------------------
def test_roundtrip():
    s = G.apply_move(G.apply_move(G.initial_state(), "2,2"), "0,0")
    d = G.serialize(s)
    s2 = G.deserialize(d)
    if G.serialize(s2) != d:
        fail("serialize/deserialize must round-trip identically")


if __name__ == "__main__":
    test_placement()
    test_four_wins()
    test_three_loses()
    test_four_beats_three()
    test_full_board_draw()
    test_roundtrip()
    print("SELFTEST OK")
    sys.exit(0)
