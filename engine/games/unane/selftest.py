"""Ūnane correctness anchors (pure stdlib).

Every figure below was transcribed from ``Unane_rules.pdf`` (md5
``d520de357ab036f20629c514a6942340``, ModDate 2026-05-20) by SAMPLING THE
RENDERED PDF PIXELS at each grid intersection — four probes on the stone's
diagonal ring for the stone colour and nine at the centre for the coloured dot —
not by eye.  What is pinned here, and by what:

* **Figure 1 — the setup.**  A strict 5x4 checkerboard with a BLACK stone on the
  TOP-LEFT pit.  That convention, applied to this package's ``W x (W-1)`` boards
  (``W`` even, so the height is odd), is asserted for every offered size.  It is
  the datum that pins WHICH SEAT IS BLACK — a fact that lives outside the engine
  and is therefore the right thing to hang the caption assertions on.

* **Figure 2 — captures.**  Transcribed cell by cell; the four green-dotted white
  stones are exactly the capture set of the single black stone that touches them,
  and the RED-dotted white stone is the one that is only DIAGONALLY adjacent.
  The figure's DISCRIMINATING POWER is measured, not assumed: it kills the
  8-adjacency and queen-slide readings, and it is **blind to the rook-slide
  reading** (the red-dotted stone is not rook-visible from any black stone
  either), which is why the sheet's word "adjacent" — and the contrast with the
  designer's Narrows, which spells out "separated ... by empty points only" — is
  what carries that distinction.

* **Figure 3 — removals.**  Transcribed cell by cell; the three green-dotted
  black stones are exactly the removable ones and the three red-dotted ones
  exactly the non-removable ones.  Measured discriminating power: this figure
  kills the "no adjacency at all" reading, the "no FRIENDLY adjacency" reading
  and the 8-ADJACENCY reading (the same shape of bug gameslib shipped in
  Minefield).

* **Figure 4 — the object of the game, and the crux of the sheet.**  The sheet's
  summary sentence ("only one friendly group and only one enemy group") is
  SYMMETRIC in the two colours and would make "you can win on your opponent's
  turn" dead prose.  Figure 4 is captioned "Black wins" and shows Black with ONE
  group and White with **TWO** — so the symmetric reading is dead.  **Figure 4
  is NEW: it does not exist in the previous (2026-05-07) revision of the sheet,
  which is the only one Wayback holds**, so the artefact that settles the crux
  has never been archived anywhere.  Measured power: Figure 4 kills exactly ONE
  of the five wrong readings enumerated below and is BLIND to four — including
  the symmetric rule COMBINED with Narrows-style connectivity through empty
  points, under which both armies are unified in Figure 4 and Black still wins.
  Prose kills the other four, and every one is covered here by positions
  replayed through ``apply_move`` or by ``test_group_edge_cases``.

* **Every way of winning, reached through ``apply_move``** — a turn that unifies
  only the mover, one that unifies only the OPPONENT, and one that unifies BOTH
  (the mover wins the tie) — plus a random sweep confirming all three arise in
  normal play.

* **Termination, proved rather than capped.**  Every non-swap turn removes
  exactly one stone and nothing is ever added, so no position can repeat; a
  player holding one stone has one group, which ends the game, so both counts
  stay >= 2 while play continues.  ``max_plies(w, h) = W*H - 2`` is derived in
  code from the board dimensions, and the 4x3 solve REACHES it exactly (ply 10),
  so the bound is tight, not padded.  There is NO ply cap and NO repetition rule
  in the shipped game, so no constant can be outcome-load-bearing.

* **The 4x3 board is SOLVED exhaustively, through the shipped Game API.**
  84,587 reachable states, 30,130 leaves, ZERO draws, ZERO no-move leaves.  With
  the pie rule the value is a SECOND-player win; with the swap suppressed the
  same board is a FIRST-player win — so the swap genuinely hands the position
  over, and a broken swap changes the answer.  The walk carries an explicit
  on-stack repetition check, proving cycle-freedom directly.

* **"No legal turn" is VACUOUS — proved, not defended.**  Every stone you own
  offers you either a capture (it touches an enemy) or a removal (it does not),
  so only a player with NO stones can be stuck; and reaching zero stones needs
  you to pass through one stone, which is one group and ends the game.  Random
  play can never reach a stuck position, so it is tested EXHAUSTIVELY on
  constructed boards (551,853 boards over three small grids).

* **``serialize``/``deserialize`` are compared as STATES**, with an exact key-set
  assertion, at every ply of whole games on every board size.

* **``render()`` declares a board big enough for every piece, at EVERY size**,
  and its move strings obey ``Board.jsx``'s cell-path contract (a bare one-cell
  move would be fired on the FIRST click and make captures unselectable).
"""

import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.unane.game import (  # noqa: E402
    ORTHO, SIZES, Unane, UnaneState, all_turns, board_dims, can_remove,
    capture_targets, cell_name, groups, is_unified, max_plies, neighbours,
)

G = Unane()
B, W = 0, 1


def is_removal(move: str) -> bool:
    """Is this move string a REMOVAL (a self-move ``cell>cell``)?"""
    return move != "swap" and move.split(">")[0] == move.split(">")[1]


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


def _figure_premise(board, w, h, expect_black, expect_white):
    """The premise every Ūnane figure rests on: the board STARTED full with
    W*H/2 stones a side, and every turn takes exactly one stone off, so the
    number of empty pits IS the number of turns played.  That count is returned.

    NOTE what is and is not falsifiable here.  ``empties == (start - n0) +
    (start - n1)`` is an ALGEBRAIC IDENTITY -- both sides are ``w*h - n0 - n1``
    for ANY board whatsoever -- so asserting it tests nothing and it is stated
    below only as the derivation.  The assertions that CAN fail on a
    mis-transcribed figure are the pinned per-colour counts and the fact that
    neither colour shows more stones than it started with (stones are only ever
    removed, never added).

    Unlike the designer's Narrows -- where every turn removes an ENEMY stone, so
    ``start - n1`` counts Black's turns exactly -- a Ūnane turn may remove the
    MOVER's own stone.  The per-colour split therefore says NOTHING about whose
    turn it is; only the total does.  See test_figure2_captures.
    """
    n0 = sum(1 for p in board.values() if p == B)
    n1 = sum(1 for p in board.values() if p == W)
    assert (n0, n1) == (expect_black, expect_white), (n0, n1)
    start = w * h // 2
    assert 0 <= n0 <= start and 0 <= n1 <= start, \
        "a colour can never hold MORE stones than it started with"
    # empties == (start - n0) + (start - n1) is the identity noted above.
    return w * h - len(board)


# --------------------------------------------------------------------------
#  Figure 1 — the setup
# --------------------------------------------------------------------------

#  Figure 1 of Unane_rules.pdf, transcribed top-down by pixel sampling.
FIG1 = [
    "#O#O#",
    "O#O#O",
    "#O#O#",
    "O#O#O",
]


def test_figure1_setup_and_opening_count():
    # The printed figure itself: 5x4, strict checkerboard, BLACK top-left.
    board, w, h = board_from_rows(FIG1)
    assert (w, h) == (5, 4) and len(board) == 20
    assert board[(0, h - 1)] == B, "Figure 1 draws a BLACK stone top-left"
    assert min(w, h) % 2 == 0, "at least one even dimension"

    for size in SIZES:
        w, h = board_dims(size)
        assert w % 2 == 0, "the rule sheet requires at least one even dimension"
        s = G.initial_state({"size": size})
        assert (s.w, s.h) == (w, h)
        assert len(s.board) == w * h, "every pit holds exactly one stone"
        # ...in a strict checkerboard: no two orthogonal neighbours match
        for cell, p in s.board.items():
            for nb in neighbours(w, h, cell):
                assert s.board[nb] != p, "the setup is not a checkerboard"
        # Figure 1: the TOP-LEFT cell holds a BLACK stone.
        assert s.board[(0, h - 1)] == B, "top-left must be Black (Figure 1)"
        n0 = sum(1 for p in s.board.values() if p == B)
        assert n0 * 2 == w * h, "the two colours must start equal"
        assert G.current_player(s) == B, "Black moves first"
        assert s.winner is None and not G.is_terminal(s)
        # A full checkerboard has NO removals (every stone touches an enemy),
        # so the opening move count is exactly the number of adjacent pairs.
        mvs = G.legal_moves(s)
        assert not any(is_removal(m) for m in mvs), \
            "no removal is legal on a full checkerboard"
        assert len(mvs) == 2 * w * h - w - h, (size, len(mvs))
        assert "swap" not in mvs, "the pie is White's option, not Black's"
    # spelled out: gameslib reports the same counts for the same boards
    assert len(G.legal_moves(G.initial_state({"size": 8}))) == 97
    assert len(G.legal_moves(G.initial_state({"size": 4}))) == 17


# --------------------------------------------------------------------------
#  Figure 2 — capturing moves
# --------------------------------------------------------------------------

#  Figure 2, transcribed top-down.  The black stone at (1, 2) may capture the
#  four green-dotted white stones; the white stone at (2, 1) carries the RED dot
#  and is only DIAGONALLY adjacent to it.
FIG2 = [
    ".O...",
    "O#O..",
    ".OO..",
    "....#",
]
FIG2_BLACK = (1, 2)
FIG2_GREEN = {(1, 3), (0, 2), (2, 2), (1, 1)}
FIG2_RED = (2, 1)


def test_figure2_captures():
    board, w, h = board_from_rows(FIG2)
    # --- the figure's PREMISE, not just the outcome it illustrates ---
    assert (w, h) == (5, 4), "Figure 2 is drawn on the 5x4 grid of Figure 1"
    plies = _figure_premise(board, w, h, 2, 5)
    assert plies == 13
    # Turns alternate Black, White, Black, ... and the PIE SWAP DOES NOT CHANGE
    # THAT PARITY: the swapper takes over the black army and the opponent then
    # moves as White, so the sequence of COLOURS to move is unaffected.  Hence
    # after an EVEN number of stone-removing plies it is Black's turn and after
    # an ODD number it is White's -- with or without the swap.  (test_figure4
    # relies on the same rule, and the two must agree.)
    #
    # Figure 2 shows 13 -- an ODD count -- yet its caption discusses BLACK's
    # captures.  So Figure 2 is an ILLUSTRATIVE diagram, not a position legally
    # reachable with Black to move.  That costs this test nothing: what the
    # figure pins is the capture GEOMETRY, which does not depend on whose turn
    # it is.  Recorded here so the parity rule is not silently mis-stated.
    assert plies == 13 and plies % 2 == 1
    assert board[FIG2_BLACK] == B, "the moving stone is Black's"
    for g in FIG2_GREEN:
        assert board[g] == W, "the green-dotted stones are White's"
    assert board[FIG2_RED] == W

    # --- the illustrated outcome ---
    assert set(capture_targets(board, w, h, FIG2_BLACK)) == FIG2_GREEN
    assert FIG2_RED not in FIG2_GREEN
    # the other black stone (bottom-right corner) touches nothing
    assert capture_targets(board, w, h, (4, 0)) == []
    # an empty cell generates nothing
    assert capture_targets(board, w, h, (0, 0)) == []
    # every generated capture belongs to the mover and lands on an enemy
    for f, t in all_turns(board, w, h, B):
        if f == t:
            continue
        assert board[f] == B and board[t] == W
        assert abs(f[0] - t[0]) + abs(f[1] - t[1]) == 1, "captures are one step"

    # --- MEASURED discriminating power: which wrong readings does it kill? ---
    def eight_adjacent(bd, cell):
        seat = bd[cell]
        return {(cell[0] + dc, cell[1] + dr)
                for dc in (-1, 0, 1) for dr in (-1, 0, 1)
                if (dc or dr) and bd.get((cell[0] + dc, cell[1] + dr))
                not in (None, seat)}

    def slide(bd, cell, dirs):
        seat = bd[cell]
        out = set()
        for dc, dr in dirs:
            c, r = cell[0] + dc, cell[1] + dr
            while 0 <= c < w and 0 <= r < h:
                occ = bd.get((c, r))
                if occ is not None:
                    if occ != seat:
                        out.add((c, r))
                    break
                c, r = c + dc, r + dr
        return out

    diag = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    killed = {
        "8-adjacent": eight_adjacent(board, FIG2_BLACK) != FIG2_GREEN,
        "queen-slide": slide(board, FIG2_BLACK, ORTHO + diag) != FIG2_GREEN,
        "rook-slide": slide(board, FIG2_BLACK, ORTHO) != FIG2_GREEN,
    }
    assert killed["8-adjacent"] and killed["queen-slide"], killed
    assert not killed["rook-slide"], \
        "Figure 2 is BLIND to the rook-slide reading -- the sheet's word " \
        "'adjacent' is what settles it (contrast Narrows, which spells out " \
        "'separated from your stone by empty points only')"
    # ...and the blindness is not local to that one stone: NO black stone in
    # Figure 2 can rook-see a white stone it cannot already reach in one step.
    for cell, p in board.items():
        if p == B:
            assert slide(board, cell, ORTHO) == set(capture_targets(board, w, h, cell))


# --------------------------------------------------------------------------
#  Figure 3 — removals
# --------------------------------------------------------------------------

#  Figure 3, transcribed top-down.  Green dots (removable) on the black stones
#  at (2, 3), (3, 3), (2, 1); red dots (not removable) at (0, 2), (2, 2), (1, 1).
FIG3 = [
    "..##.",
    "#O#..",
    ".##..",
    ".O...",
]
FIG3_GREEN = {(2, 3), (3, 3), (2, 1)}
FIG3_RED = {(0, 2), (2, 2), (1, 1)}


def test_figure3_removals():
    board, w, h = board_from_rows(FIG3)
    # --- the figure's PREMISE ---
    assert (w, h) == (5, 4)
    plies = _figure_premise(board, w, h, 6, 2)
    assert plies == 12 and plies % 2 == 0, \
        "12 stone-removing plies ⇒ it is Black's turn with no pie swap"
    assert FIG3_GREEN | FIG3_RED == {c for c, p in board.items() if p == B}, \
        "the sheet dots EVERY black stone, so the figure is exhaustive"
    assert not (FIG3_GREEN & FIG3_RED)

    # --- the illustrated outcome ---
    for cell in FIG3_GREEN:
        assert can_remove(board, w, h, cell), cell_name(cell)
    for cell in FIG3_RED:
        assert not can_remove(board, w, h, cell), cell_name(cell)
    # White's stones are not Black's to remove
    for cell, p in board.items():
        if p == W:
            assert (cell, cell) not in all_turns(board, w, h, B)
    removals = {f for f, t in all_turns(board, w, h, B) if f == t}
    assert removals == FIG3_GREEN

    # --- MEASURED discriminating power ---
    def no_adjacency_at_all(cell):
        return not any(nb in board for nb in neighbours(w, h, cell))

    def no_friendly_adjacency(cell):
        return not any(board.get(nb) == board[cell] for nb in neighbours(w, h, cell))

    def no_enemy_within_8(cell):
        seat = board[cell]
        return not any(board.get((cell[0] + dc, cell[1] + dr)) not in (None, seat)
                       for dc in (-1, 0, 1) for dr in (-1, 0, 1) if dc or dr)

    black = FIG3_GREEN | FIG3_RED
    for label, pred in (("no adjacency at all", no_adjacency_at_all),
                        ("no FRIENDLY adjacency", no_friendly_adjacency),
                        ("no enemy within 8 neighbours", no_enemy_within_8)):
        got = {c for c in black if pred(c)}
        assert got != FIG3_GREEN, f"Figure 3 fails to kill the '{label}' reading"
    # ...specifically: (2,3) touches a FRIENDLY stone and is still green, and it
    # touches a white stone DIAGONALLY (at (1,2)) and is still green.
    assert (3, 3) in FIG3_GREEN and board.get((3, 3)) == B and board.get((2, 3)) == B
    assert board.get((1, 2)) == W and (2, 3) in FIG3_GREEN


# --------------------------------------------------------------------------
#  Figure 4 — the object of the game (the sheet's crux)
# --------------------------------------------------------------------------

def _empty_linked_components(board, w, h):
    """(black, white) component counts under the DESIGNER'S OTHER connectivity
    model — the one Narrows uses, where stones also link through EMPTY points.
    Used only to MEASURE what Figure 4 can and cannot distinguish."""
    out = []
    for seat in (B, W):
        seen, comps = set(), 0
        for start in sorted(c for c, p in board.items() if p == seat):
            if start in seen:
                continue
            comps += 1
            comp = {start}
            seen.add(start)
            stack = [start]
            while stack:
                cur = stack.pop()
                for nb in neighbours(w, h, cur):
                    if nb in comp:
                        continue
                    occ = board.get(nb)
                    if occ is None or occ == seat:
                        comp.add(nb)
                        seen.add(nb)
                        stack.append(nb)
        out.append(comps)
    return tuple(out)


#  Figure 4, transcribed top-down, captioned "Black wins".
FIG4 = [
    ".....",
    "..#O.",
    "..#OO",
    ".O..O",
]


def test_figure4_black_wins_kills_the_symmetric_reading():
    board, w, h = board_from_rows(FIG4)
    plies = _figure_premise(board, w, h, 2, 5)
    assert plies == 13
    # --- the illustrated outcome ---
    bg = groups(board, w, h, B)
    wg = groups(board, w, h, W)
    assert len(bg) == 1, "Figure 4: Black has ONE group"
    assert bg[0] == {(2, 2), (2, 1)}
    assert len(wg) == 2, "Figure 4: White has TWO groups -- this is the crux"
    assert sorted(len(g) for g in wg) == [1, 4]
    assert {(1, 0)} in wg, "the lone white stone in the bottom row"
    assert is_unified(board, w, h, B) and not is_unified(board, w, h, W)

    # --- MEASURED discriminating power ------------------------------------
    # The candidate rule space is (connectivity model) x (win rule).  Figure 4
    # kills exactly ONE cell of it; everything else is killed by prose and by
    # the gameslib differential.
    #
    # (a) SYMMETRIC win rule, friendly-only connectivity ("you win only if there
    #     is one friendly AND one enemy group").  KILLED by Figure 4: White has
    #     two groups, yet Black has won.
    assert not (is_unified(board, w, h, B) and is_unified(board, w, h, W)), \
        "under the symmetric reading Figure 4 would have no winner"
    # (a') ...but the same symmetric rule survives Figure 4 if connectivity is
    #     read the way the designer's NARROWS reads it (stones linked through
    #     EMPTY points too): under that model BOTH armies are unified here, so
    #     Figure 4 would still be a Black win.  Measured, not assumed:
    linked = _empty_linked_components(board, w, h)
    assert linked == (1, 1), linked
    #     So the connectivity model is settled by PROSE -- "only one orthogonally
    #     interconnected group of YOUR COLOR", with no mention of empty points,
    #     against Narrows' explicit "via orthogonally connected paths of
    #     unoccupied points and/or friendly stones" -- and by the differential
    #     (gameslib's getGroups drops every non-friendly node).  test_group_edge_
    #     cases pins it directly.
    # (b) "you win if you are unified and the opponent is NOT" -- Figure 4 is
    #     BLIND to this (it shows exactly that case).  Killed by the sheet's
    #     third sentence, which awards the win in the both-at-once case; covered
    #     by WIN_CASES["both"] below.
    # (c) "a tie goes to the NON-mover" -- Figure 4 shows no tie; killed by
    #     "If, after YOUR turn, ... YOU win"; covered by WIN_CASES["both"].
    # (d) "you can only win on your own turn" -- Figure 4 is consistent with it
    #     (13 stone-plies with no swap ⇒ Black moved last); killed by "You can
    #     win on your turn or on your opponent's turn"; covered by
    #     WIN_CASES["other"].
    assert plies % 2 == 1, "with no pie swap, ply 13 was BLACK's -- so Figure 4 " \
                           "alone cannot show a win on the opponent's turn"


# --------------------------------------------------------------------------
#  Winning — every path, reached through apply_move
# --------------------------------------------------------------------------

#  Frozen from random play on the 4x3 board: (serialized pre-move state, move,
#  expected winner).  Each is replayed through the real apply_move so that the
#  "win as an event" winner field is exercised rather than hand-built.
WIN_CASES = {}


def _find_win_cases():
    """Search random 4x3 games for one example of each of the three ways a game
    can end, and freeze them into WIN_CASES.  Done in-process (not pinned as
    literals) so the cases can never drift out of step with the rules, while the
    ASSERTIONS about each kind stay explicit."""
    rnd = random.Random(90210)
    for _ in range(4000):                 # bounded: never spin on a regression
        if len(WIN_CASES) == 3:
            break
        s = G.initial_state({"size": 4})
        while not G.is_terminal(s):
            prev = s
            m = rnd.choice(G.legal_moves(s))
            s = G.apply_move(s, m)
            if s.winner is None:
                continue
            mover = prev.to_move
            a = is_unified(s.board, s.w, s.h, mover)
            b = is_unified(s.board, s.w, s.h, 1 - mover)
            kind = "both" if a and b else "mover" if a else "other"
            WIN_CASES.setdefault(kind, (G.serialize(prev), m, s.winner))


def test_win_paths_through_apply_move():
    _find_win_cases()
    assert set(WIN_CASES) == {"mover", "other", "both"}
    for kind, (data, move, winner) in WIN_CASES.items():
        s = G.deserialize(data)
        assert not G.is_terminal(s) and s.winner is None
        assert move in G.legal_moves(s)
        mover = s.to_move
        t = G.apply_move(s, move)
        a = is_unified(t.board, t.w, t.h, mover)
        b = is_unified(t.board, t.w, t.h, 1 - mover)
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
        # the caption names the winner in the SHEET's colours.  The ground truth
        # for "who is Black" is the owner of the Figure-1 top-left corner stone
        # at the START of this game -- a fact outside the engine's own naming.
        assert not t.swapped, "these cases were frozen from unswapped games"
        opening = G.initial_state({"size": t.w})
        black_seat = opening.board[(0, t.h - 1)]
        assert black_seat == B
        expect = "Black" if winner == black_seat else "White"
        assert G.render(t)["caption"].startswith(expect + " wins"), \
            G.render(t)["caption"]


def test_capture_is_by_replacement_and_removal_takes_one_off():
    s = G.initial_state({"size": 4})
    # --- capture ---
    t = G.apply_move(s, "0,0>0,1")
    assert (0, 0) not in t.board, "the mover's stone leaves its pit"
    assert t.board[(0, 1)] == B, "and replaces the captured stone"
    assert len(t.board) == len(s.board) - 1, "exactly one stone leaves the board"
    assert sum(1 for p in t.board.values() if p == B) == \
        sum(1 for p in s.board.values() if p == B), "the mover loses nothing"
    assert t.to_move == W and t.ply == 1 and t.last == ((0, 0), (0, 1))
    assert s.board[(0, 0)] == B, "apply_move must not mutate its input"
    # --- removal (reached through apply_move once the board opens up) ---
    rnd = random.Random(1234)
    v = t
    for _ in range(200):
        rem = [m for m in G.legal_moves(v) if is_removal(m)]
        if rem:
            break
        v = G.apply_move(v, rnd.choice(G.legal_moves(v)))
    assert rem, "a removal must become available once a stone is isolated"
    cell = tuple(int(x) for x in rem[0].split(">")[0].split(","))
    x = G.apply_move(v, rem[0])
    assert cell not in x.board and len(x.board) == len(v.board) - 1
    assert sum(1 for p in x.board.values() if p == v.to_move) == \
        sum(1 for p in v.board.values() if p == v.to_move) - 1, \
        "a removal costs the MOVER a stone"
    # --- illegal moves are rejected ---
    for bad in ("0,1>0,0", "9,9>0,0", "0,0>3,2", "0,0>1,1", "0,0>0,0", "swap"):
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
    assert len(s2.board) == len(s1.board), "the swap removes NO stone"
    # ...so the group structure of each COLOUR is unchanged.
    assert len(groups(s2.board, s2.w, s2.h, B)) == len(groups(s1.board, s1.w, s1.h, W))
    assert len(groups(s2.board, s2.w, s2.h, W)) == len(groups(s1.board, s1.w, s1.h, B))
    assert s2.winner is None, "the swap cannot create a win it did not already have"
    assert "swap" not in G.legal_moves(s2), "one bite at the pie"
    s3 = G.apply_move(s2, G.legal_moves(s2)[0])
    assert "swap" not in G.legal_moves(s3)
    assert G.describe_move(s1, "swap") == "swap (pie)"
    assert G.render(s1)["actionNames"]["swap"]
    for st in (s, s2, s3):
        try:
            G.apply_move(st, "swap")
        except ValueError:
            pass
        else:
            raise AssertionError("swap must be rejected off White's first turn")
    s2b = G.apply_move(s1, [m for m in G.legal_moves(s1) if m != "swap"][0])
    assert not s2b.swapped and "swap" not in G.legal_moves(s2b)

    # --- the COLOUR NAMES follow the swap (a predicate off the legality path) --
    # "White ... has the option of switching colors and BECOMING BLACK", so the
    # seat that took the pie owns the army that opened the game and must be
    # called Black from here on.  GROUND TRUTH FOR "WHO IS BLACK" IS THE OWNER OF
    # THE FIGURE-1 TOP-LEFT PIT, not anything the engine derives.
    top_left = (0, s.h - 1)
    assert s.board[top_left] == B, "Figure 1: top-left is Black"
    assert G.seat_colour(s1, s1.board[top_left]) == "Black"
    assert G.render(s1)["caption"].startswith("White to move"), \
        "before the swap seat 1 is White"
    assert s2.board[top_left] == W, "the swap handed the opening army to seat 1"
    assert G.seat_colour(s2, s2.board[top_left]) == "Black", \
        "whoever owns the top-left pit is Black"
    assert G.seat_colour(s2, W) == "Black" and G.seat_colour(s2, B) == "White"
    assert G.render(s2)["caption"].startswith("White to move"), \
        "after the swap the seat on move (0) plays WHITE"
    # ...and the same holds for the winner announced at the end of a swapped game
    rnd = random.Random(19)
    t = s2
    while not G.is_terminal(t):
        t = G.apply_move(t, rnd.choice(G.legal_moves(t)))
    assert t.swapped and t.winner is not None
    # The winner's colour word must agree with the FIGURE's notion of Black.
    # Ground truth is the owner of the Figure-1 top-left pit AT THE START,
    # carried through the swap -- NOT whoever happens to occupy that pit at the
    # END of the game.  A white stone can capture INTO the top-left pit, so an
    # assertion written against the FINAL occupant is simply wrong: over 4,000
    # random swapped 6x5 games the pit ends up occupied 677 times and 358 of
    # those (53%) are WHITE.  It is also silently SKIPPED whenever the pit ends
    # up empty -- which is what happens on this test's own seed, so such an
    # assertion would verify nothing while looking like coverage.
    assert s.board[top_left] == B, "Figure 1: the top-left pit starts Black"
    assert G.seat_colour(t, W) == "Black", "in a swapped game seat 1 is Black"
    assert G.render(t)["caption"].startswith(G.seat_colour(t, t.winner) + " wins")
    # a game in which the pie was DECLINED keeps the plain seat->colour mapping
    assert G.seat_colour(s2b, B) == "Black" and G.seat_colour(s2b, W) == "White"
    # the swap must actually change who is called Black -- otherwise the whole
    # assertion above would be trivially satisfiable
    assert G.seat_colour(s1, B) != G.seat_colour(s2, B)


# --------------------------------------------------------------------------
#  "No legal turn" is vacuous — proved on constructed boards
# --------------------------------------------------------------------------

def test_no_legal_turn_is_impossible():
    """Exhaustive over every board on three small grids.

    Asserts both halves of the proof:
      (a) a player has a legal turn IFF he has at least one stone -- because
          every stone either touches an enemy (capture) or does not (removal);
      (b) a player with exactly ONE stone is already unified, so being reduced
          to zero requires passing through a position that ends the game.
    Only seat 0 is probed: colour-swapping is a bijection of the enumeration, so
    checking seat 0 over ALL boards is exactly checking both seats.
    Random play can never reach a stuck position, so nothing but a constructed
    sweep can cover this.
    """
    checked = stuck = ones = 0
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
            have = sum(1 for p in board.values() if p == B)
            turns = all_turns(board, w, h, B)
            if have == 0:
                assert not turns
                stuck += 1
            else:
                assert turns, (w, h, board)
                if have == 1:
                    assert is_unified(board, w, h, B)
                    ones += 1
    assert (checked, stuck, ones) == (551853, 4672, 27072), (checked, stuck, ones)


def test_group_edge_cases():
    # A single stone is one group -- this is what ends every game.
    assert is_unified({(0, 0): B, (2, 2): W, (2, 0): W}, 3, 3, B)
    # A player with NO stones has no groups and has NOT won (matching
    # AbstractPlay).  Unreachable in play; see test_no_stone_exhaustion.
    assert not is_unified({(0, 0): W}, 3, 3, B)
    assert groups({(0, 0): W}, 3, 3, B) == []
    # Only FRIENDLY stones connect -- empty points link nothing (unlike the
    # designer's Narrows, where they do).
    assert not is_unified({(0, 0): B, (2, 0): B}, 3, 1, B)
    assert is_unified({(0, 0): B, (1, 0): B, (2, 0): B}, 3, 1, B)
    # ...and diagonals do not connect either.
    assert not is_unified({(0, 0): B, (1, 1): B}, 2, 2, B)
    # A FULL checkerboard leaves every stone alone.
    full = {(c, r): (c + r) % 2 for c in range(4) for r in range(3)}
    assert len(groups(full, 4, 3, B)) == 6 and len(groups(full, 4, 3, W)) == 6


def test_heuristic_shape_and_direction():
    """``heuristic`` must be a LIST of num_players payoffs (a bare float raises
    TypeError in MCTSBot's back-prop), zero-sum, in range, seat-symmetric — and
    DIRECTIONALLY correct, which is a SEPARATE assertion from all of those (a
    sign-flipped eval and a constant-zero eval pass every shape check)."""
    rnd = random.Random(77)
    for size in (4, 6, 8):
        s = G.initial_state({"size": size})
        for _ in range(40):
            h = G.heuristic(s)
            assert isinstance(h, list) and len(h) == G.num_players, h
            assert all(isinstance(x, float) for x in h)
            assert all(-1.0 < x < 1.0 for x in h), h
            assert abs(h[0] + h[1]) < 1e-12, "the eval must be zero-sum"
            # seat symmetry: swapping the colours must negate the eval
            flip = dataclass_replace_board(s)
            assert abs(G.heuristic(flip)[0] + h[0]) < 1e-12
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
    # --- DIRECTION, pinned to constructed positions ---
    # Black in one group, White in four: Black is far closer to the object.
    good, w, h = board_from_rows([
        "##...",
        "##.O.",
        "...O.",
        "O.O..",
    ])
    assert len(groups(good, w, h, B)) == 1 and len(groups(good, w, h, W)) == 3
    s = UnaneState(w=w, h=h, board=good, to_move=B)
    v = G.heuristic(s)
    assert v[0] > 0.5 > 0 > v[1], v
    assert abs(v[0] - math.tanh(2 / 3)) < 1e-12, "pinned to the shipped formula"
    # ...and the mirror image (colours exchanged) must score the same, negated
    mirror = UnaneState(w=w, h=h, board={c: 1 - p for c, p in good.items()},
                        to_move=B)
    assert G.heuristic(mirror) == [v[1], v[0]]
    # equal group counts score exactly level, whatever the material
    level, w2, h2 = board_from_rows(["#.O..", "#.O..", ".....", "....."])
    assert G.heuristic(UnaneState(w=w2, h=h2, board=level, to_move=B)) == [0.0, 0.0]
    # a strictly better position for Black scores strictly higher than a worse
    # one (this is the assertion a constant-zero eval fails)
    worse, w3, h3 = board_from_rows([
        "#.#..",
        "..#.O",
        "#....",
        "..O.O",
    ])
    assert len(groups(worse, w3, h3, B)) == 3
    assert G.heuristic(UnaneState(w=w3, h=h3, board=worse, to_move=B))[0] < v[0]


def dataclass_replace_board(s):
    """`s` with the two colours exchanged (used for the seat-symmetry check)."""
    return UnaneState(w=s.w, h=s.h, board={c: 1 - p for c, p in s.board.items()},
                      to_move=1 - s.to_move, winner=s.winner, ply=s.ply)


def test_no_stone_exhaustion():
    """A player can never be reduced to zero stones: that needs him to be down
    to one stone first, and one stone is one group, which ends the game."""
    rnd = random.Random(4242)
    for size in (4, 6, 8):
        for _ in range(40):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                n0 = sum(1 for p in s.board.values() if p == B)
                n1 = len(s.board) - n0
                assert n0 >= 1 and n1 >= 1
                s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
            n0 = sum(1 for p in s.board.values() if p == B)
            assert min(n0, len(s.board) - n0) >= 1


# --------------------------------------------------------------------------
#  Termination — proved, and no cap to be load-bearing
# --------------------------------------------------------------------------

def test_termination_bound():
    assert max_plies(8, 7) == 54 and max_plies(4, 3) == 10
    # the shipped game has NO ply cap and NO repetition rule to be load-bearing
    import games.unane.game as M
    assert not [k for k in vars(M) if k.isupper() and ("CAP" in k or "MAX" in k)]
    assert {k for k in vars(M) if k.isupper()} == {"SIZES", "SEAT_NAMES", "ORTHO"}

    rnd = random.Random(7)
    seen_swap = seen_removal = 0
    for size in SIZES:
        w, h = board_dims(size)
        bound = max_plies(w, h)
        for _ in range(10 if size <= 8 else 3):
            s = G.initial_state({"size": size})
            seen = {tuple(sorted(s.board.items()))}
            while not G.is_terminal(s):
                m = rnd.choice(G.legal_moves(s))
                t = G.apply_move(s, m)
                if m == "swap":
                    seen_swap += 1
                    assert len(t.board) == len(s.board), "the swap removes nothing"
                else:
                    assert len(t.board) == len(s.board) - 1, \
                        "every turn removes exactly one stone"
                    if is_removal(m):
                        seen_removal += 1
                # the strictly decreasing monovariant is what forbids repetition
                key = tuple(sorted(t.board.items()))
                assert key not in seen, "a position repeated"
                seen.add(key)
                s = t
                assert s.ply <= bound, (size, s.ply, bound)
            assert s.winner is not None, "every game ends decisively"
            assert G.returns(s) != [0.0, 0.0]
    assert seen_swap > 0, "the swap ply must actually be exercised"
    assert seen_removal > 0, "removals must actually be exercised"


def test_solved_4x3():
    """Exhaustive solve of the smallest offered board, through the shipped API.

    Also proves cycle-freedom on-line (an explicit on-stack check), that no draw
    and no no-move leaf is reachable, and that ``max_plies`` is TIGHT (the walk
    reaches ply 10 = max_plies(4, 3) exactly, on the swap line).
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
    assert (v, st["nodes"], st["leaves"], st["draws"]) == (-1, 84587, 30130, 0), st
    assert st["maxply"] == 10 == max_plies(4, 3), st["maxply"]
    v2, st2 = solve(False)
    assert (v2, st2["nodes"], st2["leaves"], st2["draws"]) == (1, 42294, 15065, 0), st2
    assert st2["maxply"] == 9
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
            json.dumps(d)                       # must be JSON-able
            back = G.deserialize(d)
            assert back == s, (size, s.ply)     # compare STATES, not dicts
            assert G.serialize(back) == d
            if s.swapped:
                seen_swapped += 1
            if G.is_terminal(s):
                seen_winner += s.winner is not None
                break
            mvs = G.legal_moves(s)
            m = "swap" if "swap" in mvs and size % 4 == 0 else rnd.choice(mvs)
            s = G.apply_move(s, m)
    assert seen_swapped and seen_winner == len(SIZES)


def test_render_bounds_every_size():
    rnd = random.Random(3)
    for size in SIZES:
        w, h = board_dims(size)
        s = G.initial_state({"size": size})
        corners = {f"{c},{r}" for c in (0, w - 1) for r in (0, h - 1)}
        all_cells = {f"{c},{r}" for c in range(w) for r in range(h)}
        seen_cells = set()
        for _ in range(max_plies(w, h) + 2):
            spec = G.render(s)
            assert spec["board"] == {"type": "square", "width": w, "height": h}
            assert spec["pieces"], "an empty board would render nothing"
            for pc in spec["pieces"]:
                c, r = (int(x) for x in pc["cell"].split(","))
                assert 0 <= c < w and 0 <= r < h, (size, pc)
                assert pc["owner"] in (0, 1)
                seen_cells.add(pc["cell"])
            for hl in spec["highlights"]:
                c, r = (int(x) for x in hl["cell"].split(","))
                assert 0 <= c < w and 0 <= r < h, (size, hl)
            assert isinstance(spec["caption"], str) and spec["caption"]
            # Board.jsx contract: every move must be "swap" or a TWO-cell path.
            # A bare one-cell move would be fired on the FIRST click, making
            # captures unselectable.
            for m in G.legal_moves(s):
                if m == "swap":
                    continue
                parts = m.split(">")
                assert len(parts) == 2, m
                for p in parts:
                    assert p in all_cells, m
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
        assert G.is_terminal(s) and s.winner is not None
        # the far corners really were rendered (the check is not vacuous)
        assert corners <= seen_cells, (size, corners - seen_cells)
        # the winning group is highlighted, and only cells the winner owns
        spec = G.render(s)
        goals = {hl["cell"] for hl in spec["highlights"] if hl["kind"] == "goal"}
        assert goals == {f"{c},{r}" for (c, r), p in s.board.items()
                         if p == s.winner}
        assert spec["caption"].startswith(
            G.seat_colour(s, s.winner) + " wins")


def test_describe_move_and_names():
    s = G.initial_state({"size": 12})
    assert cell_name((0, 0)) == "a1" and cell_name((11, 10)) == "l11"
    assert G.describe_move(s, "0,0>0,1") == "a1xa2"
    assert G.describe_move(s, "3,4>3,4") == "-d5"
    assert G.describe_move(s, "swap") == "swap (pie)"
    assert G.describe_move(s, "nonsense") == "nonsense"
    rnd = random.Random(5)
    labels = set()
    for _ in range(150):
        if G.is_terminal(s):
            break
        for m in G.legal_moves(s):
            lbl = G.describe_move(s, m)
            assert isinstance(lbl, str) and lbl
            labels.add(lbl[0] == "-")
        s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
    assert labels == {True, False}, "both notations must be exercised"


def test_options_and_state_defaults():
    assert G.num_players == 2
    assert G.initial_state().w == 8, "the default board is 8x7"
    assert board_dims(8) == (8, 7)
    for bad in (5, 7, 0, 20, 3):
        try:
            G.initial_state({"size": bad})
        except ValueError:
            pass
        else:
            raise AssertionError(f"size {bad} should be rejected")
    assert (UnaneState().w, UnaneState().h) == (8, 7)


def test_all_win_kinds_reachable_in_play():
    """Guard against a sweep that silently covers only one win condition."""
    rnd = random.Random(2024)
    kinds = set()
    for size in (4, 6):
        for _ in range(150):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
            mover = 1 - s.to_move
            a = is_unified(s.board, s.w, s.h, mover)
            b = is_unified(s.board, s.w, s.h, 1 - mover)
            kinds.add("both" if a and b else "mover" if a else "other")
            assert s.winner == (mover if a else 1 - mover)
    assert kinds == {"mover", "other", "both"}, kinds


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"unane selftest: {len(tests)} checks passed")


if __name__ == "__main__":
    main()
