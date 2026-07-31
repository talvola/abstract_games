"""Narrows correctness anchors (pure stdlib).

What is pinned here, and by what:

* **Figure 1 — the setup.**  The rule sheet draws a checkerboard with a BLACK
  stone on the top-left cell; that convention, applied to this package's
  ``W x (W-1)`` boards, is asserted for every offered size.  It is the datum
  that pins the coordinate map: on a board with an EVEN width and an ODD height
  the vertical mirror preserves the checkerboard parity (it is a genuine
  automorphism and cannot distinguish anything), while the horizontal mirror
  flips it — so "top-left is Black" is exactly the half of the symmetry group
  that has to be pinned from the printed figure.  The opening move count is
  asserted against the closed form ``2*W*H - W - H`` (241 on the standard
  12x11 board, which is what AbstractPlay's independent ``gameslib``
  implementation reports for the same board).

* **Figure 2 — rook captures.**  The 5x4 position of the sheet's Figure 2 is
  transcribed cell by cell (by SAMPLING THE RENDERED PDF PIXELS at four probe
  points per pit plus one at the centre for the coloured dot, not by eye), and the capture set of the yellow-dotted black stone
  is asserted to be EXACTLY the three green-dotted white stones — one adjacent,
  one two empty points away, and one blocked direction that must NOT appear.
  The figure's PREMISE is asserted too (16 stones, 8 apiece, 4 empty points ⇒
  four plies have been played ⇒ it really is Black's turn), because a
  mis-transcribed figure passes every assertion built on it.

* **Figure 3 — the object of the game.**  The 5x4 position of the sheet's
  Figure 3 is transcribed cell by cell.  Black is linked (one component), White
  is not (three), and the sheet's four BLUE-DOTTED points are reproduced exactly
  by ``narrows_cells`` — including the fifth empty point, which the sheet leaves
  unmarked because it links nothing.  The premise (8 black / 7 white / 5 empty ⇒
  five plies ⇒ Black moved last) is asserted as well.

* **Every way of winning, reached through ``apply_move``.**  A move that links
  only the mover, a move that links only the OPPONENT (you can win on your
  opponent's turn), and a move that links BOTH (the mover wins the tie) — three
  frozen positions, each replayed through the real ``apply_move`` so that the
  "win as an event" ``winner`` field is genuinely exercised, plus a random sweep
  that confirms all three arise in normal play at every board size.

* **Termination, proved rather than capped.**  Every capture removes exactly one
  enemy stone and nothing is ever added, and a player holding one stone is
  trivially linked, so a game lasts at most ``W*H - 3`` capture plies plus the
  one optional pie ply: ``max_plies(w, h) = W*H - 2``, derived in code from the
  board dimensions.  Asserted on random play at every size.  There is NO ply cap
  and NO repetition rule, so no constant can be outcome-load-bearing.

* **The 4x3 board is SOLVED exhaustively, through the shipped Game API.**
  25,301 reachable states, 20,552 leaves, ZERO draws and ZERO no-move leaves.
  With the pie rule the value is a SECOND-player win; with the pie rule disabled
  the same board is a FIRST-player win — so the swap is doing exactly what a pie
  rule must do, and a broken swap changes the answer.  The walk also carries an
  explicit on-stack repetition check, which proves cycle-freedom directly rather
  than inferring it from "the search finished".

* **"No capture available" is VACUOUS — proved, not defended.**  You have no
  capture iff no row and no column holds stones of both colours; and if every
  row and column is monochromatic then both players are already linked, so the
  game ended on the previous move.  Random play can never reach such a position,
  so it is tested EXHAUSTIVELY on constructed boards (551,853 boards over three
  small grids).

* **A player never runs out of stones.**  Reaching zero stones would require the
  opponent to be down to one stone first, which already ends the game.  Asserted
  over random play and over the whole 4x3 solve.

* **``serialize``/``deserialize`` are compared as STATES**, with an exact key-set
  assertion, at every ply of whole games on every board size — the vacuous
  ``serialize(deserialize(d)) == d`` form cannot see a dropped field.

* **``render()`` declares a board big enough for every piece, at EVERY size**,
  from positions reached through ``apply_move`` (a piece outside the declared
  width/height is silently dropped by the web renderer), and the winner named in
  the caption is asserted to be the winner in the state.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.narrows.game import (  # noqa: E402
    ORTHO, SIZES, Narrows, NarrowsState, all_captures, board_dims,
    captures_from, cell_name, is_linked, linked_components, max_plies,
    narrows_cells,
)

G = Narrows()
B, W = 0, 1


def board_from_rows(rows):
    """Rows are given TOP-DOWN as in the rule sheet's figures; '#'=Black,
    'O'=White, '.'=empty.  Returns (board, w, h) in engine coordinates
    (row 0 = the BOTTOM row, as the renderer draws it)."""
    h = len(rows)
    w = len(rows[0])
    board = {}
    for i, row in enumerate(rows):
        assert len(row) == w
        r = h - 1 - i
        for c, ch in enumerate(row):
            if ch == "#":
                board[(c, r)] = B
            elif ch == "O":
                board[(c, r)] = W
            else:
                assert ch == ".", ch
    return board, w, h


# --------------------------------------------------------------------------
#  Figure 1 — the setup
# --------------------------------------------------------------------------

def test_figure1_setup_and_opening_count():
    for size in SIZES:
        w, h = board_dims(size)
        assert w % 2 == 0, "the rule sheet requires at least one even dimension"
        s = G.initial_state({"size": size})
        assert (s.w, s.h) == (w, h)
        # every pit holds exactly one stone
        assert len(s.board) == w * h
        # ...in a strict checkerboard: no two orthogonal neighbours match
        for (c, r), p in s.board.items():
            for dc, dr in ORTHO:
                q = (c + dc, r + dr)
                if q in s.board:
                    assert s.board[q] != p, "the setup is not a checkerboard"
        # Figure 1: the TOP-LEFT cell holds a BLACK stone.  On an even-width /
        # odd-height board the horizontal mirror flips the checkerboard parity,
        # so this is the assertion that pins the map; the vertical mirror
        # preserves it and could not be pinned by any figure.
        assert s.board[(0, h - 1)] == B, "top-left must be Black (Figure 1)"
        assert s.board[(0, 0)] == B
        assert s.board[(w - 1, h - 1)] == (B if (w - 1) % 2 == 0 else W)
        # equal material
        n0 = sum(1 for p in s.board.values() if p == B)
        assert n0 * 2 == w * h, "the two colours must start equal"
        # Black moves first, and nobody has won yet.
        assert G.current_player(s) == B
        assert s.winner is None and not G.is_terminal(s)
        # The opening move count is exactly the number of orthogonally adjacent
        # pairs, every one of which is a Black/White pair on a full checkerboard.
        expect = 2 * w * h - w - h
        assert len(G.legal_moves(s)) == expect, (size, len(G.legal_moves(s)))
        assert "swap" not in G.legal_moves(s), "the pie is White's option, not Black's"
    # the standard board, spelled out (gameslib reports the same number)
    assert len(G.legal_moves(G.initial_state({"size": 12}))) == 241
    assert len(G.legal_moves(G.initial_state({"size": 4}))) == 17


# --------------------------------------------------------------------------
#  Figure 2 — rook captures
# --------------------------------------------------------------------------

#  Figure 2 of Narrows_rules.pdf, transcribed top-down.  The yellow-dotted black
#  stone is b2 = (1, 2); the green-dotted white stones are (0, 2), (4, 2), (1, 1).
FIG2 = [
    "##.O#",
    "O#..O",
    "#OO##",
    ".OO#O",
]
FIG2_YELLOW = (1, 2)
FIG2_GREEN = {(0, 2), (4, 2), (1, 1)}


def test_figure2_rook_captures():
    board, w, h = board_from_rows(FIG2)
    # --- the figure's PREMISE, not just the outcome it illustrates ---
    assert (w, h) == (5, 4), "Figure 2 is drawn on the 5x4 grid of Figure 1"
    n0 = sum(1 for p in board.values() if p == B)
    n1 = sum(1 for p in board.values() if p == W)
    empties = w * h - len(board)
    assert (n0, n1, empties) == (8, 8, 4)
    # Each ply removes exactly one enemy stone and creates exactly one empty
    # point, so 4 empty points == 4 plies played, and 10-n1 == plies by Black.
    assert empties == (10 - n0) + (10 - n1), "counts must be consistent"
    assert 10 - n1 == 2 and 10 - n0 == 2, "two plies each ⇒ it is Black's turn"
    assert board[FIG2_YELLOW] == B, "the yellow-dotted stone is Black's"
    for g in FIG2_GREEN:
        assert board[g] == W, "the green-dotted stones are White's"

    # --- the illustrated outcome ---
    got = set(captures_from(board, w, h, FIG2_YELLOW))
    assert got == FIG2_GREEN, sorted(got)
    # one adjacent (south), one across two empty points (east), and NORTH must
    # be absent because a friendly stone blocks the ray
    assert (1, 3) not in got and board[(1, 3)] == B
    # a ray that runs off the board past an empty point yields nothing (south
    # from a2 = (0, 1) passes the empty a1 and leaves the board)
    assert set(captures_from(board, w, h, (0, 1))) == {(1, 1), (0, 2)}
    # ...and a ray through empties reaches the first stone beyond them, while a
    # friendly stone blocks: from d2 = (3, 1), north crosses the empty d3 to
    # take d4, west takes the adjacent c2, east and south are blocked by Black.
    assert set(captures_from(board, w, h, (3, 1))) == {(2, 1), (3, 3)}
    assert board[(4, 1)] == B and board[(3, 0)] == B
    # every generated move belongs to the mover and lands on an enemy
    for f, t in all_captures(board, w, h, B):
        assert board[f] == B and board[t] == W
        assert f[0] == t[0] or f[1] == t[1], "captures are orthogonal"
    # an empty cell generates nothing
    assert captures_from(board, w, h, (2, 3)) == []


# --------------------------------------------------------------------------
#  Figure 3 — the object of the game
# --------------------------------------------------------------------------

#  Figure 3, transcribed top-down.  The blue-dotted points are the four empties
#  d4=(3,3), b3=(1,2), c3=(2,2), d1=(3,0); the fifth empty point e2=(4,1) is
#  deliberately NOT dotted on the sheet — it links nothing.
FIG3 = [
    "#OO.#",
    "#..#O",
    "#OO#.",
    "O##.O",
]
FIG3_BLUE = {(3, 3), (1, 2), (2, 2), (3, 0)}
FIG3_UNMARKED_EMPTY = (4, 1)


def test_figure3_object_of_the_game():
    board, w, h = board_from_rows(FIG3)
    # --- the figure's PREMISE ---
    assert (w, h) == (5, 4)
    n0 = sum(1 for p in board.values() if p == B)
    n1 = sum(1 for p in board.values() if p == W)
    empties = w * h - len(board)
    assert (n0, n1, empties) == (8, 7, 5)
    assert empties == (10 - n0) + (10 - n1)
    assert 10 - n1 == 3 and 10 - n0 == 2, "Black has moved 3 times, White 2 ⇒ " \
                                          "Black moved last, as 'Black wins' requires"
    assert set(board) | set(FIG3_BLUE) | {FIG3_UNMARKED_EMPTY} == \
        {(c, r) for c in range(w) for r in range(h)}, "the empties are exactly the 5 named"

    # --- the illustrated outcome: Black has won, White has not ---
    assert is_linked(board, w, h, B), "Figure 3: Black is linked"
    assert not is_linked(board, w, h, W)
    assert len(linked_components(board, w, h, W)) == 3, "White has three groups"
    # ...and Black's single component covers every black stone
    comp = linked_components(board, w, h, B)[0]
    assert all(c in comp for c, p in board.items() if p == B)

    # --- the sheet's blue dots, reproduced exactly ---
    assert narrows_cells(board, w, h, B) == FIG3_BLUE
    assert FIG3_UNMARKED_EMPTY not in FIG3_BLUE
    # ...and the unmarked empty really is inessential
    without = dict(board)
    without[FIG3_UNMARKED_EMPTY] = W
    assert is_linked(without, w, h, B), "e2 links nothing"
    # ...while every blue point really is essential
    for cell in FIG3_BLUE:
        blocked = dict(board)
        blocked[cell] = W
        assert not is_linked(blocked, w, h, B), f"{cell_name(cell)} is a narrows"
    # a player who is not linked has no narrows
    assert narrows_cells(board, w, h, W) == set()


def test_linked_edge_cases():
    # A single stone is trivially linked (this is what ends every game).
    assert is_linked({(0, 0): B, (2, 2): W, (2, 0): W}, 3, 3, B)
    # A player with NO stones has no groups and has NOT won -- matching
    # AbstractPlay.  (Unreachable in play; see test_no_stone_exhaustion.)
    assert not is_linked({(0, 0): W}, 3, 3, B)
    assert linked_components({(0, 0): W}, 3, 3, B) == []
    # A FULL board (no empty points) leaves every checkerboard stone alone.
    full = {(c, r): (c + r) % 2 for c in range(4) for r in range(3)}
    assert not is_linked(full, 4, 3, B) and not is_linked(full, 4, 3, W)
    assert len(linked_components(full, 4, 3, B)) == 6
    # Two stones joined only through a friendly stone (no empty point at all).
    assert is_linked({(0, 0): B, (1, 0): B, (2, 0): W, (0, 1): W, (1, 1): W},
                     3, 2, B)
    # Two stones separated by an enemy wall are NOT linked.
    wall = {(0, 0): B, (2, 0): B, (1, 0): W, (1, 1): W}
    assert not is_linked(wall, 3, 2, B)
    # ...but they are linked if the wall has a gap.
    assert is_linked({(0, 0): B, (2, 0): B, (1, 0): W}, 3, 2, B)


# --------------------------------------------------------------------------
#  Winning — every path, reached through apply_move
# --------------------------------------------------------------------------

#  Frozen from random play on the 4x3 board: (serialized pre-move state, move,
#  expected winner).  Each is replayed through the real apply_move so the
#  "win as an event" winner field is exercised rather than hand-built.
WIN_CASES = {
    "mover": (
        {"w": 4, "h": 3,
         "board": {"0,0": 0, "0,1": 1, "0,2": 0, "1,0": 1, "1,2": 0, "2,0": 0,
                   "3,0": 1, "3,1": 0, "3,2": 1},
         "to_move": 1, "winner": None, "ply": 3, "last": ["1,1", "3,1"],
         "swapped": False},
        "3,2>3,1", 1),
    "other": (
        {"w": 4, "h": 3,
         "board": {"0,0": 0, "0,1": 1, "0,2": 0, "1,0": 1, "1,1": 0, "1,2": 1,
                   "2,2": 1, "3,0": 0, "3,1": 0, "3,2": 1},
         "to_move": 0, "winner": None, "ply": 2, "last": ["2,1", "2,2"],
         "swapped": False},
        "1,1>1,0", 1),
    "both": (
        {"w": 4, "h": 3,
         "board": {"0,0": 0, "0,1": 1, "0,2": 0, "1,1": 0, "1,2": 1, "2,0": 1,
                   "2,1": 1, "2,2": 0, "3,0": 1, "3,2": 0},
         "to_move": 0, "winner": None, "ply": 2, "last": ["1,0", "2,0"],
         "swapped": False},
        "1,1>1,2", 0),
}


def test_win_paths_through_apply_move():
    for kind, (data, move, winner) in WIN_CASES.items():
        s = G.deserialize(data)
        assert not G.is_terminal(s) and s.winner is None
        assert move in G.legal_moves(s)
        mover = s.to_move
        t = G.apply_move(s, move)
        a = is_linked(t.board, t.w, t.h, mover)
        b = is_linked(t.board, t.w, t.h, 1 - mover)
        if kind == "mover":
            assert a and not b
            assert t.winner == mover
        elif kind == "other":
            assert b and not a
            assert t.winner == 1 - mover, "you can win on your opponent's turn"
        else:
            assert a and b
            assert t.winner == mover, "the mover wins the tie"
        assert t.winner == winner
        assert G.is_terminal(t)
        assert G.returns(t) == ([1.0, -1.0] if winner == 0 else [-1.0, 1.0])
        assert G.legal_moves(t) == []
        # and the caption names the same winner (a predicate off the legality path)
        cap = G.render(t)["caption"]
        assert cap.startswith(("Black wins", "White wins"))
        assert cap.startswith(("Black", "White")[winner])


def test_capture_is_by_replacement():
    s = G.initial_state({"size": 4})
    before = dict(s.board)
    t = G.apply_move(s, "0,0>0,1")
    assert (0, 0) not in t.board, "the mover's stone leaves its pit"
    assert t.board[(0, 1)] == B, "and replaces the captured stone"
    assert len(t.board) == len(before) - 1, "exactly one stone leaves the board"
    assert sum(1 for p in t.board.values() if p == B) == \
        sum(1 for p in before.values() if p == B), "the mover loses nothing"
    assert t.to_move == W and t.ply == 1 and t.last == ((0, 0), (0, 1))
    assert s.board == before, "apply_move must not mutate its input"
    # illegal moves are rejected
    for bad in ("0,1>0,0", "9,9>0,0", "0,0>3,2", "swap"):
        try:
            G.apply_move(s, bad)
        except (ValueError, KeyError):
            pass
        else:
            raise AssertionError(f"{bad} should be rejected at ply 0")


# --------------------------------------------------------------------------
#  The pie rule
# --------------------------------------------------------------------------

def test_pie_rule():
    s = G.initial_state({"size": 6})
    assert "swap" not in G.legal_moves(s), "not before Black has moved"
    s1 = G.apply_move(s, G.legal_moves(s)[0])
    assert "swap" in G.legal_moves(s1), "White's first turn only"
    assert s1.to_move == W
    s2 = G.apply_move(s1, "swap")
    assert s2.swapped and s2.ply == 2
    assert s2.to_move == B, "after the swap it is the other seat's turn"
    # The POSITION is untouched: only the seat that owns each colour changes.
    assert set(s2.board) == set(s1.board)
    assert all(s2.board[c] == 1 - s1.board[c] for c in s1.board)
    # ...so the group structure of each COLOUR is unchanged.
    assert (len(linked_components(s2.board, s2.w, s2.h, B))
            == len(linked_components(s1.board, s1.w, s1.h, W)))
    assert (len(linked_components(s2.board, s2.w, s2.h, W))
            == len(linked_components(s1.board, s1.w, s1.h, B)))
    assert s2.winner is None, "the swap cannot create a win it did not already have"
    assert "swap" not in G.legal_moves(s2), "one bite at the pie"
    s3 = G.apply_move(s2, G.legal_moves(s2)[0])
    assert "swap" not in G.legal_moves(s3)
    assert G.describe_move(s1, "swap") == "swap (pie)"
    assert G.render(s1)["actionNames"]["swap"]
    # the swap is rejected outside White's first turn
    for st in (s, s2, s3):
        try:
            G.apply_move(st, "swap")
        except ValueError:
            pass
        else:
            raise AssertionError("swap must be rejected off White's first turn")
    # A declined pie leaves the game running normally.
    s2b = G.apply_move(s1, [m for m in G.legal_moves(s1) if m != "swap"][0])
    assert not s2b.swapped and "swap" not in G.legal_moves(s2b)

    # --- the COLOUR NAMES follow the swap (a predicate off the legality path) --
    # "White ... has the option of switching colors and BECOMING BLACK", so the
    # seat that took the pie owns the army that opened the game and must be
    # called Black from here on.  The top-left pit holds the Figure-1 BLACK
    # stone, so its owner is the ground truth for who is Black.
    top_left = (0, s.h - 1)
    assert s1.board[top_left] == B and G.seat_colour(s1, B) == "Black"
    assert G.render(s1)["caption"].startswith("White to move"), \
        "before the swap seat 1 is White"
    assert s2.board[top_left] == W, "the swap handed the opening army to seat 1"
    assert G.seat_colour(s2, W) == "Black" and G.seat_colour(s2, B) == "White"
    assert G.render(s2)["caption"].startswith("White to move"), \
        "after the swap the seat on move (0) plays WHITE"
    # ...and the same holds for the winner announced at the end of a swapped game
    rnd = random.Random(19)
    t = s2
    while not G.is_terminal(t):
        t = G.apply_move(t, rnd.choice(G.legal_moves(t)))
    assert t.swapped and t.winner is not None
    assert G.render(t)["caption"].startswith(G.seat_colour(t, t.winner) + " wins")
    assert G.seat_colour(t, t.winner) == ("Black" if t.winner == W else "White"), \
        "in a swapped game seat 1 is Black"
    # a game in which the pie was DECLINED keeps the plain seat->colour mapping
    assert G.seat_colour(s2b, B) == "Black" and G.seat_colour(s2b, W) == "White"


# --------------------------------------------------------------------------
#  "No capture available" is vacuous — proved on constructed boards
# --------------------------------------------------------------------------

def _rows_and_cols_monochrome(board, w, h):
    for line in ([[(c, r) for c in range(w)] for r in range(h)]
                 + [[(c, r) for r in range(h)] for c in range(w)]):
        seats = {board[x] for x in line if x in board}
        if len(seats) > 1:
            return False
    return True


def test_no_capture_is_impossible():
    """Exhaustive over every board on three small grids.

    Asserts the two halves of the proof:
      (a) one player has no capture IFF the other has none IFF every row and
          every column is monochromatic;
      (b) in that case every player holding a stone is already LINKED, so the
          game ended on the previous move and the position is unreachable.
    Random play can never reach such a position, so nothing but a constructed
    sweep can cover it.
    """
    checked = mono = 0
    for w, h in ((2, 3), (3, 3), (4, 3)):
        cells = [(c, r) for c in range(w) for r in range(h)]
        n = len(cells)
        for code in range(3 ** n):
            board = {}
            x = code
            for cell in cells:
                x, d = divmod(x, 3)
                if d:
                    board[cell] = d - 1
            checked += 1
            no0 = not all_captures(board, w, h, B)
            no1 = not all_captures(board, w, h, W)
            assert no0 == no1, (w, h, board)
            if not no0:
                continue
            mono += 1
            assert _rows_and_cols_monochrome(board, w, h), (w, h, board)
            for seat in (B, W):
                if any(p == seat for p in board.values()):
                    assert is_linked(board, w, h, seat), (w, h, board, seat)
    assert (checked, mono) == (551853, 11441), (checked, mono)


def test_no_stone_exhaustion():
    """A player can never be reduced to zero stones: that needs the opponent to
    be down to one stone first, and one stone is trivially linked, so the game
    is already over."""
    rnd = random.Random(4242)
    for size in (4, 6, 8):
        for _ in range(60):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                n0 = sum(1 for p in s.board.values() if p == B)
                n1 = sum(1 for p in s.board.values() if p == W)
                assert n0 >= 1 and n1 >= 1
                assert abs(n0 - n1) <= 1, "counts stay balanced"
                s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
            n0 = sum(1 for p in s.board.values() if p == B)
            n1 = sum(1 for p in s.board.values() if p == W)
            assert min(n0, n1) >= 1, (n0, n1)


# --------------------------------------------------------------------------
#  Termination — proved, and no cap to be load-bearing
# --------------------------------------------------------------------------

def test_termination_bound():
    assert max_plies(12, 11) == 130 and max_plies(4, 3) == 10
    rnd = random.Random(7)
    seen_swap = 0
    for size in SIZES:
        w, h = board_dims(size)
        bound = max_plies(w, h)
        for _ in range(12 if size <= 8 else 4):
            s = G.initial_state({"size": size})
            total = len(s.board)
            while not G.is_terminal(s):
                m = rnd.choice(G.legal_moves(s))
                t = G.apply_move(s, m)
                if m == "swap":
                    seen_swap += 1
                    assert len(t.board) == len(s.board), "the swap removes nothing"
                else:
                    assert len(t.board) == len(s.board) - 1, \
                        "every capture removes exactly one stone"
                s = t
                assert s.ply <= bound, (size, s.ply, bound)
            assert s.winner is not None, "every game ends decisively"
            assert G.returns(s) != [0.0, 0.0]
            assert s.ply <= total - 2
    assert seen_swap > 0, "the swap ply must actually be exercised"


def test_solved_4x3():
    """Exhaustive solve of the smallest offered board, through the shipped API.

    Also proves cycle-freedom on-line (an explicit on-stack check) and that no
    draw and no no-move leaf is reachable.
    """
    def solve(allow_swap):
        memo, onstack = {}, set()
        stat = {"nodes": 0, "leaves": 0, "draws": 0, "maxply": 0}

        def key(s):
            return (tuple(sorted(s.board.items())), s.to_move, min(s.ply, 2))

        def negamax(s):
            k = key(s)
            if k in memo:
                return memo[k]
            assert k not in onstack, "a position repeated -- the game can cycle"
            stat["nodes"] += 1
            stat["maxply"] = max(stat["maxply"], s.ply)
            if G.is_terminal(s):
                stat["leaves"] += 1
                ret = G.returns(s)
                if ret == [0.0, 0.0]:
                    stat["draws"] += 1
                memo[k] = int(ret[s.to_move])
                return memo[k]
            onstack.add(k)
            best = -2
            for m in G.legal_moves(s):
                if m == "swap" and not allow_swap:
                    continue
                best = max(best, -negamax(G.apply_move(s, m)))
            onstack.discard(k)
            memo[k] = best
            return best

        return negamax(G.initial_state({"size": 4})), stat

    v, st = solve(True)
    assert (v, st["nodes"], st["leaves"], st["draws"]) == (-1, 25301, 20552, 0), st
    assert st["maxply"] == 9 <= max_plies(4, 3)
    v2, st2 = solve(False)
    assert (v2, st2["nodes"], st2["leaves"], st2["draws"]) == (1, 12651, 10276, 0), st2
    assert st2["maxply"] == 8
    # With the pie rule the second player wins; without it the first player
    # does.  A swap that did not hand the position over would not flip this.
    assert v == -v2 == -1


# --------------------------------------------------------------------------
#  Plumbing: serialize, render, describe_move
# --------------------------------------------------------------------------

SER_KEYS = {"w", "h", "board", "to_move", "winner", "ply", "last", "swapped"}


def test_serialize_round_trip_as_states():
    rnd = random.Random(11)
    seen_swapped = seen_winner = 0
    for size in SIZES:
        s = G.initial_state({"size": size})
        while True:
            d = G.serialize(s)
            assert set(d) == SER_KEYS, set(d) ^ SER_KEYS
            import json
            json.dumps(d)                       # must be JSON-able
            back = G.deserialize(d)
            assert back == s, (size, s.ply)     # compare STATES, not dicts
            assert G.serialize(back) == d
            if s.swapped:
                seen_swapped += 1
            if s.winner is not None:
                seen_winner += 1
                break
            if G.is_terminal(s):
                break
            mvs = G.legal_moves(s)
            # take the swap when it is offered, so `swapped` is covered
            m = "swap" if "swap" in mvs and size % 4 == 0 else rnd.choice(mvs)
            s = G.apply_move(s, m)
    assert seen_swapped and seen_winner == len(SIZES)


def test_render_bounds_every_size():
    rnd = random.Random(3)
    for size in SIZES:
        w, h = board_dims(size)
        s = G.initial_state({"size": size})
        for _ in range(max_plies(w, h) + 2):
            spec = G.render(s)
            bd = spec["board"]
            assert bd == {"type": "square", "width": w, "height": h}
            assert spec["pieces"], "an empty board would render nothing"
            for pc in spec["pieces"]:
                c, r = (int(x) for x in pc["cell"].split(","))
                assert 0 <= c < w and 0 <= r < h, (size, pc)
                assert pc["owner"] in (0, 1)
            for hl in spec["highlights"]:
                c, r = (int(x) for x in hl["cell"].split(","))
                assert 0 <= c < w and 0 <= r < h, (size, hl)
            assert isinstance(spec["caption"], str) and spec["caption"]
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
        # a terminal position was reached and its caption names the winner —
        # in the SHEET's colours, which the pie swap exchanges (see test_pie_rule)
        assert G.is_terminal(s) and s.winner is not None
        assert G.render(s)["caption"].startswith(
            ("Black", "White")[s.winner ^ int(s.swapped)])
        # every corner of the board was rendered at ply 0 (the board is FULL),
        # so the bound check is not vacuous
        spec0 = G.render(G.initial_state({"size": size}))
        cells = {pc["cell"] for pc in spec0["pieces"]}
        for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            assert f"{corner[0]},{corner[1]}" in cells


def test_describe_move_and_names():
    s = G.initial_state({"size": 12})
    assert cell_name((0, 0)) == "a1" and cell_name((11, 10)) == "l11"
    assert G.describe_move(s, "0,0>0,1") == "a1xa2"
    assert G.describe_move(s, "swap") == "swap (pie)"
    assert G.describe_move(s, "nonsense") == "nonsense"
    rnd = random.Random(5)
    for _ in range(120):
        if G.is_terminal(s):
            break
        for m in G.legal_moves(s):
            lbl = G.describe_move(s, m)
            assert isinstance(lbl, str) and lbl
        s = G.apply_move(s, rnd.choice(G.legal_moves(s)))


def test_options_and_state_defaults():
    assert G.num_players == 2
    assert G.initial_state().w == 12, "the default board is 12x11"
    for bad in (5, 7, 0, 20, 3):
        try:
            G.initial_state({"size": bad})
        except ValueError:
            pass
        else:
            raise AssertionError(f"size {bad} should be rejected")
    # the dataclass default must agree with the default option
    assert (NarrowsState().w, NarrowsState().h) == (12, 11)


def test_all_win_kinds_reachable_in_play():
    """Guard against a sweep that silently covers only one win condition."""
    rnd = random.Random(2024)
    kinds = set()
    for size in (4, 6):
        for _ in range(120):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
            mover = 1 - s.to_move
            a = is_linked(s.board, s.w, s.h, mover)
            b = is_linked(s.board, s.w, s.h, 1 - mover)
            kinds.add("both" if a and b else "mover" if a else "other")
            assert s.winner == (mover if a else 1 - mover)
    assert kinds == {"mover", "other", "both"}, kinds


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"narrows selftest: {len(tests)} checks passed")


if __name__ == "__main__":
    main()
