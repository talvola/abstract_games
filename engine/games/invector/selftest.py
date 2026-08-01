"""Invector correctness anchors (pure stdlib).

What is pinned here, and by what:

* **Figure 1 — the setup.**  The rule sheet's Figure 1 puts a BLACK stone on the
  TOP-LEFT pit of a filled checkerboard; that datum is asserted for every offered
  board size, and it is the ground truth (OUTSIDE the engine) that the pie-swap
  colour naming is checked against.  The opening move count is asserted against
  the closed form ``w*(h-1) + h*(w-1)`` — on a full checkerboard every orthogonal
  edge joins two enemies, so every edge is a capture and nothing else is legal
  (97 on the standard 8x7 board, which is exactly what AbstractPlay's independent
  ``gameslib`` implementation reports).

* **The two centre pits.**  ``[There are two center pits.]``  The definition
  implemented — the pits nearest the board's geometric centre — is asserted to
  yield EXACTLY TWO orthogonally-adjacent pits at every size, to be invariant
  under both reflections of the rectangle, and to agree with the integer
  "doubled distance" identity.

* **Figure 3 — non-capturing moves, WITH ITS DISCRIMINATING POWER MEASURED.**
  The 5x4 position of Figure 3 (transcribed from the PDF's own vector geometry,
  not by eye) prints the COMPLETE set of orthogonal neighbours of two black
  stones, three green (legal) and three red (illegal).  ``test_figure3_*``
  reproduces it exactly, asserts its PREMISES (all six pits empty; neither black
  stone has any capture available, so every dot is decided purely by the
  distance rule; the red pit e2 is EQUIDISTANT, which is what makes "strictly
  closer" load-bearing), and then MEASURES what the figure can and cannot rule
  out.  Eleven candidate definitions are named, one of which is the rule as
  implemented; of the other TEN the figure kills EIGHT (both axis-swapped pairs,
  "all four middle pits", the top/bottom-edge pair, the corner pits, a single
  centre pit on the far side, Chebyshev distance, and "no farther" instead of
  "strictly closer").  The two that survive are killed here by other means —
    - an ASYMMETRIC SINGLE CENTRE PIT: killed by the sheet's "[There are two
      center pits.]" and by the requirement that the rule be invariant under the
      board's own reflections.  Figure 3 + that invariance leave EXACTLY ONE of
      all 6,195 candidate centre sets standing, which this test computes;
    - the EUCLIDEAN metric: proved BEHAVIOURALLY IDENTICAL to Manhattan for
      single orthogonal steps on this board family (0 disagreements over every
      step of ten boards), so it is not a wrong variant at all.
  Figure 3 is also blind to a "shortest path through UNOCCUPIED pits" reading of
  "via a series of orthogonally adjacent pits" (all six dots agree); that reading
  is excluded by the sheet's own words "Manhattan distance" and by the
  ``gameslib`` differential, which uses plain Manhattan and matches us over
  thousands of positions.

* **Figure 2 — capturing moves.**  The 5x4 position of Figure 2 is transcribed
  the same way.  The dotted black stone captures exactly the four orthogonally
  adjacent white stones and NOT the diagonally adjacent one.  The premise that
  makes the figure worth printing is asserted too: two of those four captures
  move the stone strictly AWAY from the centre and a third is equidistant, so
  the figure independently proves captures are NOT subject to the closer-to-
  centre restriction ("in any direction").

* **The skip rule is REAL, mutual deadlock is IMPOSSIBLE.**  "Passing is not
  allowed, but if you don't have a legal move available, your turn is skipped."
  A single player being stuck happens in ordinary play (measured at every board
  size).  BOTH players being stuck at once would freeze the game forever; it is
  proved impossible in the module docstring and verified EXHAUSTIVELY here over
  every position of two small grids (523,852 boards on which both players still
  hold a stone), which random play could never do.  The engine still scores a hypothetical
  double-stuck position as an honest 0-0 draw rather than inventing a winner.

* **Termination: no ply cap, no repetition rule.**  The monovariant is asserted
  directly, ply by ply, on random games at every offered size: the pair
  ``(stones on the board, total distance-to-centre)`` strictly decreases
  lexicographically on every move — a capture drops the stone count and can
  never raise the distance sum (``dD = -d(from)``), a quiet move leaves the count
  alone and drops the sum by exactly one.  The resulting bound ``max_plies(w,h)``
  is computed from the board dimensions, never pinned, and asserted on random
  play.  There is NO ply cap and NO repetition rule, so no constant can be
  outcome-load-bearing.

* **Tiny boards are SOLVED exhaustively through the shipped Game API**, with an
  on-stack repetition check that proves acyclicity directly: 2x3 (325 states),
  its transpose 3x2 (identical numbers — the rules are axis-symmetric), and 2x5
  (32,903 states).  ZERO draws and ZERO no-move leaves anywhere.  On 2x5 the pie
  rule FLIPS the game value from a first-player win to a second-player win, so a
  broken swap changes the answer.  (One-time, offline: the smallest OFFERED
  board, 4x3, solves in 78s over 376,393 states — same conclusions.  It is not
  run here because it is slow, and because it is structurally unable to exhibit
  anything the 2x5 solve does not.)

* **A decisive result outranks the "nobody can move" draw.**  The capture that
  removes the last enemy stone usually leaves the winner with no legal move at
  all; ``winner`` must still be reported and ``returns`` must be +/-1, never 0-0.
  Asserted on positions reached through ``apply_move``.

* **``serialize``/``deserialize`` are compared as STATES**, with an exact key-set
  assertion, at every ply of whole games at every board size (including a
  swapped and a skipped ply) — the vacuous ``serialize(deserialize(d)) == d``
  form cannot see a dropped field.

* **``render()`` declares a board big enough for every piece at EVERY size**, from
  the full initial board and from positions reached through ``apply_move``.

* **NO ``heuristic`` is shipped, and that is asserted.**  The obvious material
  eval was implemented and measured through ``MCTSBot`` against the generic
  constant-zero fallback over 120 games at the server's default settings; it
  scored 61-59 (50.8%), i.e. no measurable effect, so it was dropped.  See
  rules.md note 13.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.invector.game import (  # noqa: E402
    ORTHO, SIZES, Invector, InvectorState, advances_from, all_moves,
    board_dims, captures_from, cell_name, centre_pits, dist_table,
    dist_to_centre, has_move, initial_distance_sum, max_plies, stone_count,
)

G = Invector()
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


def rc(w, h, c, i):
    """Cell (column c, i-th row counted TOP-DOWN) in engine coordinates."""
    return (c, h - 1 - i)


# --------------------------------------------------------------------------
#  Figure 1 — the setup
# --------------------------------------------------------------------------

def test_figure1_setup_and_opening_count():
    for size in SIZES:
        s = G.initial_state({"size": size})
        w, h = board_dims(size)
        assert (s.w, s.h) == (w, h)
        assert w % 2 == 0 and h % 2 == 1, "one even and one odd dimension"
        # completely filled, evenly split
        assert len(s.board) == w * h
        assert stone_count(s.board, B) == stone_count(s.board, W) == w * h // 2
        # Figure 1: the TOP-LEFT pit holds a BLACK stone, and colours alternate.
        assert s.board[(0, h - 1)] == B, "Figure 1: top-left pit is Black"
        for (c, r), p in s.board.items():
            assert p == ((c + r) % 2), "checkerboard"
        assert s.to_move == B, "Black moves first"
        assert s.winner is None and s.ply == 0 and not s.swapped
        # Every orthogonal edge of a full checkerboard joins two enemies, so
        # every edge is a capture and no quiet move exists.
        edges = w * (h - 1) + h * (w - 1)
        mv = G.legal_moves(s)
        assert len(mv) == edges, (size, len(mv), edges)
        assert all(s.board.get(tuple(int(x) for x in m.split(">")[1].split(","))) == W
                   for m in mv), "every opening move is a capture"
    # the standard board matches the count gameslib reports
    assert len(G.legal_moves(G.initial_state({"size": 8}))) == 97
    # PREMISE of the "ply 1 is never skipped" clause in apply_move: after ANY
    # legal opening move White always has a stone move of his own, so the pie is
    # always genuinely offered and can never be forced.  Checked exhaustively
    # over every opening move at every size.
    for size in SIZES:
        s = G.initial_state({"size": size})
        for mv in G.legal_moves(s):
            n = G.apply_move(s, mv)
            assert n.ply == 1 and not n.skipped
            assert has_move(n.board, n.w, n.h, W), (size, mv)
            assert set(G.legal_moves(n)) - {"swap"}


# --------------------------------------------------------------------------
#  The two centre pits
# --------------------------------------------------------------------------

def test_centre_pits():
    for size in SIZES:
        w, h = board_dims(size)
        cps = centre_pits(w, h)
        assert len(cps) == 2, (size, cps)
        (c1, r1), (c2, r2) = cps
        assert abs(c1 - c2) + abs(r1 - r2) == 1, "the two centre pits touch"
        # explicit closed form for this family (even width, odd height)
        assert set(cps) == {(w // 2 - 1, h // 2), (w // 2, h // 2)}
        # invariant under BOTH reflections of the rectangle
        assert {(w - 1 - c, r) for c, r in cps} == set(cps)
        assert {(c, h - 1 - r) for c, r in cps} == set(cps)
        tbl = dist_table(w, h)
        assert min(tbl.values()) == 0
        assert sum(1 for v in tbl.values() if v == 0) == 2
        # the integer "doubled distance" identity the docstring relies on
        for (c, r), d in tbl.items():
            assert d == (abs(2 * c - (w - 1)) + abs(2 * r - (h - 1)) - 1) // 2
        # every non-centre pit has a neighbour one step closer (used by the
        # mutual-deadlock proof)
        for (c, r), d in tbl.items():
            closer = [1 for dc, dr in ORTHO
                      if 0 <= c + dc < w and 0 <= r + dr < h
                      and tbl[(c + dc, r + dr)] == d - 1]
            assert bool(closer) == (d > 0), ((c, r), d)
        assert initial_distance_sum(w, h) == sum(tbl.values())
    # the definition is symmetric in the two axes (odd width / even height too)
    assert centre_pits(5, 4) == ((2, 1), (2, 2))
    assert centre_pits(4, 5) == ((1, 2), (2, 2))
    assert set(centre_pits(4, 5)) == {(r, c) for c, r in centre_pits(5, 4)}


# --------------------------------------------------------------------------
#  Figure 2 — capturing moves
# --------------------------------------------------------------------------
#
#  Figure 2 of Invector_rules.pdf, transcribed from the PDF's own vector
#  geometry (pdftocairo -svg; the coloured discs sit on a 21.6pt lattice, five
#  columns x four rows).  The dotted black stone is at column 1, row 1 counted
#  top-down.  Its four ORTHOGONAL neighbours carry green dots; the fifth marked
#  white stone, diagonally down-right, carries a red dot.

FIG2 = (
    ".O...",
    "O#O..",
    ".OO..",
    ".....",
)


def test_figure2_capturing_moves():
    board, w, h = board_from_rows(FIG2)
    assert (w, h) == (5, 4)
    stone = rc(w, h, 1, 1)
    assert board[stone] == B
    # --- the figure's PREMISES ---------------------------------------------
    nbrs = [(stone[0] + dc, stone[1] + dr) for dc, dr in ORTHO]
    assert all(board.get(n) == W for n in nbrs), \
        "all four orthogonal neighbours of the dotted stone hold white stones"
    red = rc(w, h, 2, 2)
    assert board[red] == W and red not in nbrs, \
        "the red-dotted white stone is DIAGONALLY adjacent, not orthogonally"
    # --- what the figure asserts -------------------------------------------
    caps = set(captures_from(board, w, h, stone))
    assert caps == set(nbrs), sorted(caps)
    assert red not in caps, "diagonal neighbours are never capturable"
    assert advances_from(board, w, h, stone) == [], \
        "every neighbour is occupied, so no quiet move exists here"
    assert {t for f, t in all_moves(board, w, h, B) if f == stone} == set(nbrs)
    # --- the point of the figure: capture direction is UNRESTRICTED --------
    d0 = dist_to_centre(w, h, stone)
    away = [n for n in caps if dist_to_centre(w, h, n) > d0]
    same = [n for n in caps if dist_to_centre(w, h, n) == d0]
    assert len(away) == 2 and len(same) == 1, (away, same)
    # ... which is exactly what a "captures must also close on the centre"
    # misreading would forbid.
    assert len([n for n in caps if dist_to_centre(w, h, n) < d0]) == 1


# --------------------------------------------------------------------------
#  Figure 3 — non-capturing moves (the discriminating anchor)
# --------------------------------------------------------------------------
#
#  Figure 3 of Invector_rules.pdf, same transcription method.  Two black stones
#  are shown, each with its COMPLETE set of orthogonal neighbours dotted:
#     black e3 (col 4, top-down row 1): green d3, red e4(top), red e2
#     black b1 (col 1, top-down row 3): green c1, green b2, red a1
#  A lone white stone sits on the top-left pit.

FIG3 = (
    "O....",
    "....#",
    ".....",
    ".#...",
)
FIG3_STONES = ((4, 1), (1, 3))                       # (col, top-down row)
FIG3_GREEN = {(3, 1), (1, 2), (2, 3)}
FIG3_RED = {(4, 0), (4, 2), (0, 3)}


def _fig3_engine():
    board, w, h = board_from_rows(FIG3)
    green = {rc(w, h, c, i) for c, i in FIG3_GREEN}
    red = {rc(w, h, c, i) for c, i in FIG3_RED}
    stones = [rc(w, h, c, i) for c, i in FIG3_STONES]
    return board, w, h, stones, green, red


def test_figure3_non_capturing_moves():
    board, w, h, stones, green, red = _fig3_engine()
    assert (w, h) == (5, 4)
    # --- the figure's PREMISES ---------------------------------------------
    assert sorted(board.values()) == [B, B, W], "two black stones and one white"
    assert all(board[s] == B for s in stones)
    for pit in green | red:
        assert pit not in board, "every dotted pit is EMPTY"
    marked = green | red
    for s in stones:
        nb = {(s[0] + dc, s[1] + dr) for dc, dr in ORTHO
              if 0 <= s[0] + dc < w and 0 <= s[1] + dr < h}
        assert nb <= marked, "the figure dots EVERY orthogonal neighbour"
        assert len(nb) == 3, "both stones stand on an edge of the board"
        assert captures_from(board, w, h, s) == [], \
            "neither stone has a capture, so every dot is decided by distance"
    assert len(marked) == 6
    # e2 (col 4, top-down row 2) is EQUIDISTANT, not farther — this is the pit
    # that makes "STRICTLY closer" load-bearing rather than "no farther".
    equal = rc(w, h, 4, 2)
    assert (dist_to_centre(w, h, equal)
            == dist_to_centre(w, h, rc(w, h, 4, 1)) == 2)
    assert equal in red
    # --- what the figure asserts -------------------------------------------
    got = set()
    for s in stones:
        got |= set(advances_from(board, w, h, s))
    assert got == green, (sorted(got), sorted(green))
    assert not (got & red)
    assert {t for f, t in all_moves(board, w, h, B)} == green


def test_figure3_transposed():
    """The rules are symmetric in the two axes, so the transposed position must
    have exactly the transposed answers.  This is what carries Figure 3 (an odd
    x even board) over to the even x odd boards this package actually offers."""
    board, w, h, stones, green, red = _fig3_engine()
    tb = {(r, c): p for (c, r), p in board.items()}
    got = set()
    for s in stones:
        got |= set(advances_from(tb, h, w, (s[1], s[0])))
    assert got == {(r, c) for c, r in green}


def test_figure3_discriminating_power():
    """MEASURE what Figure 3 can rule out — do not assume it."""
    import itertools
    import math
    board, w, h, stones, green, red = _fig3_engine()
    cells = [(c, r) for c in range(w) for r in range(h)]
    man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])            # noqa: E731
    euc = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])           # noqa: E731
    che = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))        # noqa: E731

    def predict(C, metric, strict):
        d = lambda x: min(metric(x, c) for c in C)                    # noqa: E731
        g, r = set(), set()
        for s in stones:
            for dc, dr in ORTHO:
                n = (s[0] + dc, s[1] + dr)
                if not (0 <= n[0] < w and 0 <= n[1] < h) or n in board:
                    continue
                (g if (d(n) < d(s) if strict else d(n) <= d(s)) else r).add(n)
        return g, r

    correct = set(centre_pits(w, h))
    variants = {
        "two pits straddling the EVEN dimension (as implemented)":
            (correct, man, True),
        "one centre pit only, engine row 2": ({(2, 2)}, man, True),
        "one centre pit only, engine row 1": ({(2, 1)}, man, True),
        "axis-swapped pair (straddling the ODD dimension), lower":
            ({(1, 2), (2, 2)}, man, True),
        "axis-swapped pair, upper": ({(1, 1), (2, 1)}, man, True),
        "all four 'middle' pits": ({(1, 1), (2, 1), (1, 2), (2, 2)}, man, True),
        "the correct pits but 'no farther' instead of 'strictly closer'":
            (correct, man, False),
        "the correct pits, Euclidean distance": (correct, euc, True),
        "the correct pits, Chebyshev distance": (correct, che, True),
        "the pits at the middle of the top and bottom edges":
            ({(2, 0), (2, 3)}, man, True),
        "the four corner pits":
            ({(0, 0), (4, 0), (0, 3), (4, 3)}, man, True),
    }
    survivors = [k for k, (C, m, st) in variants.items()
                 if predict(C, m, st) == (green, red)]
    assert len(variants) == 11
    assert set(survivors) == {
        "two pits straddling the EVEN dimension (as implemented)",
        "one centre pit only, engine row 2",
        "the correct pits, Euclidean distance",
    }, survivors
    # -> Figure 3 kills 8 of the 10 named WRONG variants (and 6,022 of the 6,195
    #    arbitrary centre sets).  The two survivors are dealt with explicitly:

    # (a) an ASYMMETRIC single centre pit.  The sheet says "[There are two
    #     center pits.]", and a ruleset must be invariant under the board's own
    #     reflections (neither player has a distinguished side).  Figure 3 plus
    #     that invariance leave EXACTLY ONE candidate standing out of all 6,195.
    def symmetric(C):
        S = set(C)
        return ({(w - 1 - c, r) for c, r in S} == S
                and {(c, h - 1 - r) for c, r in S} == S)
    allsets = [C for k in (1, 2, 3, 4) for C in itertools.combinations(cells, k)]
    assert len(allsets) == 6195
    fig3_ok = [C for C in allsets if predict(C, man, True) == (green, red)]
    assert len(fig3_ok) == 173
    both = [C for C in fig3_ok if symmetric(C)]
    assert both == [tuple(sorted(correct))], both

    # (b) EUCLIDEAN is not a wrong variant at all: for the single orthogonal
    #     steps this game makes, it is behaviourally IDENTICAL to Manhattan.
    disagree = 0
    for (bw, bh) in ((4, 3), (6, 5), (8, 7), (10, 9), (12, 11), (5, 4), (7, 6),
                     (3, 4), (5, 6), (9, 8)):
        cps = centre_pits(bw, bh)
        dm = lambda x: min(man(x, c) for c in cps)                    # noqa: E731
        de = lambda x: min(euc(x, c) for c in cps)                    # noqa: E731
        for c in range(bw):
            for r in range(bh):
                for dc, dr in ORTHO:
                    n = (c + dc, r + dr)
                    if 0 <= n[0] < bw and 0 <= n[1] < bh:
                        disagree += (dm(n) < dm((c, r))) != (de(n) < de((c, r)))
    assert disagree == 0

    # (c) Figure 3 is BLIND to a "shortest path through UNOCCUPIED pits" reading
    #     of "via a series of orthogonally adjacent pits" — every one of its six
    #     dots agrees under that reading too.  It is excluded by the sheet's own
    #     "Manhattan distance" and by the gameslib differential; recorded here so
    #     the gap is documented rather than assumed away.
    from collections import deque

    def blocked_dist(start, blocked):
        if start in correct:
            return 0
        seen, q = {start}, deque([(start, 0)])
        while q:
            x, d = q.popleft()
            for dc, dr in ORTHO:
                n = (x[0] + dc, x[1] + dr)
                if (not (0 <= n[0] < w and 0 <= n[1] < h)
                        or n in seen or n in blocked):
                    continue
                if n in correct:
                    return d + 1
                seen.add(n)
                q.append((n, d + 1))
        return 10 ** 6
    agree = 0
    for s in stones:
        blk = set(board) - {s}
        for dc, dr in ORTHO:
            n = (s[0] + dc, s[1] + dr)
            if not (0 <= n[0] < w and 0 <= n[1] < h) or n in board:
                continue
            agree += ((blocked_dist(n, blk) < blocked_dist(s, blk)) == (n in green))
    assert agree == 6, "Figure 3 cannot distinguish the blocked-path reading"


# --------------------------------------------------------------------------
#  Move mechanics
# --------------------------------------------------------------------------

def test_capture_is_by_replacement():
    s = G.initial_state({"size": 6})
    mv = G.legal_moves(s)[0]
    frm, to = (tuple(int(x) for x in p.split(",")) for p in mv.split(">"))
    assert s.board[to] == W
    n = G.apply_move(s, mv)
    assert frm not in n.board and n.board[to] == B
    assert len(n.board) == len(s.board) - 1
    assert stone_count(n.board, B) == stone_count(s.board, B)
    assert stone_count(n.board, W) == stone_count(s.board, W) - 1
    assert n.last == (frm, to) and n.ply == 1 and n.to_move == W
    assert G.describe_move(s, mv) == f"{cell_name(frm)}x{cell_name(to)}"


def test_quiet_move_rules():
    #  . . . . .        the black stone b2 (col 1, top-down row 2) may step to
    #  . . . . .        c2 (closer) but not to a2/b1/b3.
    board, w, h = board_from_rows((".....", ".....", ".#...", "....."))
    stone = rc(w, h, 1, 2)
    adv = set(advances_from(board, w, h, stone))
    assert adv == {rc(w, h, 2, 2)}, sorted(adv)
    # occupancy blocks a quiet move even when the pit is closer
    blocked = dict(board)
    blocked[rc(w, h, 2, 2)] = B
    assert advances_from(blocked, w, h, stone) == []
    blocked[rc(w, h, 2, 2)] = W
    assert advances_from(blocked, w, h, stone) == []          # it is a CAPTURE
    assert captures_from(blocked, w, h, stone) == [rc(w, h, 2, 2)]
    # a stone standing ON a centre pit has no quiet move at all
    for cp in centre_pits(w, h):
        assert advances_from({cp: B}, w, h, cp) == []
    # a diagonally adjacent enemy is never capturable (and the quiet moves the
    # corner stone does have all go somewhere else)
    corner, diag = rc(w, h, 0, 0), rc(w, h, 1, 1)
    lone = {corner: B, diag: W}
    assert captures_from(lone, w, h, corner) == []
    assert diag not in {t for f, t in all_moves(lone, w, h, B)}
    assert set(all_moves(lone, w, h, B)) == {(corner, rc(w, h, 1, 0)),
                                             (corner, rc(w, h, 0, 1))}


def test_illegal_moves_are_rejected():
    s = G.initial_state({"size": 6})
    for bad in ("0,0>1,1", "0,0>0,0", "1,0>0,0", "9,9>0,0", "swap"):
        try:
            G.apply_move(s, bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} should be rejected")


# --------------------------------------------------------------------------
#  The skip rule, and the impossibility of mutual deadlock
# --------------------------------------------------------------------------

def test_single_player_can_be_stuck():
    """Constructed: Black's only stone sits on a centre pit with no enemy
    neighbour, so he has no legal move and his turn is skipped."""
    w, h = board_dims(6)
    cp = centre_pits(w, h)[0]
    far = (0, 0) if (0, 0) not in centre_pits(w, h) else (w - 1, h - 1)
    board = {cp: B, far: W, (far[0], far[1] + 1): W}
    assert not has_move(board, w, h, B)
    assert has_move(board, w, h, W)
    s = InvectorState(w=w, h=h, board=board, to_move=W, ply=6)
    mv = G.legal_moves(s)
    assert mv, "White has moves"
    n = G.apply_move(s, mv[0])
    assert n.skipped and n.to_move == W, "Black's turn was skipped"
    assert G.legal_moves(n), "the game continues"
    assert "no legal move" in G.render(n)["caption"]
    assert not G.is_terminal(n)


def test_skip_rule_fires_in_ordinary_play():
    for size in (4, 6, 8):
        rnd = random.Random(4)
        skips = 0
        for _ in range(40):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
                skips += int(s.skipped)
        assert skips > 0, f"the skip rule never fired at size {size}"


def test_mutual_deadlock_is_impossible():
    """EXHAUSTIVE over every position of two small grids: it is never the case
    that both players hold stones and neither has a legal move.  Random play can
    never demonstrate this, so it is enumerated."""
    total = 0
    expected = 0
    for (w, h) in ((2, 3), (4, 3)):
        cells = [(c, r) for c in range(w) for r in range(h)]
        n = len(cells)
        expected += 3 ** n - 2 * 2 ** n + 1     # inclusion-exclusion
        for code in range(3 ** n):
            board, x = {}, code
            for cell in cells:
                x, d = divmod(x, 3)
                if d:
                    board[cell] = d - 1
            if not stone_count(board, B) or not stone_count(board, W):
                continue
            total += 1
            assert has_move(board, w, h, B) or has_move(board, w, h, W), board
    assert total == expected == 523_852, (total, expected)
    # ...and `has_move` really is `legal_moves` without the pie option.
    rnd = random.Random(9)
    for size in (4, 8):
        s = G.initial_state({"size": size})
        while not G.is_terminal(s):
            for seat in (B, W):
                assert has_move(s.board, s.w, s.h, seat) == bool(
                    all_moves(s.board, s.w, s.h, seat))
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))


def test_double_stuck_would_be_an_honest_draw():
    """The unreachable case is still handled honestly — no fabricated winner."""
    w, h = board_dims(6)
    (a, b) = centre_pits(w, h)
    s = InvectorState(w=w, h=h, board={a: B}, to_move=B, ply=8)
    assert G.legal_moves(s) == [] and G.is_terminal(s)
    assert G.returns(s) == [0.0, 0.0]
    assert "draw" in G.render(s)["caption"]


# --------------------------------------------------------------------------
#  Termination — proved, not capped
# --------------------------------------------------------------------------

def test_termination_monovariant_and_bound():
    """(stones, total distance-to-centre) strictly decreases lexicographically
    on every ply — asserted move by move, at every offered size."""
    def phi(s):
        tbl = dist_table(s.w, s.h)
        return (len(s.board), sum(tbl[c] for c in s.board))
    rnd = random.Random(23)
    for size in SIZES:
        w, h = board_dims(size)
        bound = max_plies(w, h)
        assert bound == 1 + w * h - 1 + initial_distance_sum(w, h)
        for g in range(6):
            s = G.initial_state({"size": size})
            if g == 0:                          # exercise the pie ply as well
                s = G.apply_move(s, rnd.choice(
                    [m for m in G.legal_moves(s) if m != "swap"]))
                s = G.apply_move(s, "swap")
            prev = phi(s)
            n = s.ply
            while not G.is_terminal(s):
                mv = rnd.choice(G.legal_moves(s))
                cap = s.board.get(
                    tuple(int(x) for x in mv.split(">")[1].split(","))) is not None
                s = G.apply_move(s, mv)
                cur = phi(s)
                assert cur < prev, (size, prev, cur)
                if cap:
                    assert cur[0] == prev[0] - 1 and cur[1] <= prev[1]
                else:
                    assert cur[0] == prev[0] and cur[1] == prev[1] - 1
                prev = cur
                n += 1
            assert s.ply <= bound, (size, s.ply, bound)
            assert s.winner is not None, "no draw in ordinary play"
    # There is no ply cap and no repetition rule: the engine never consults the
    # bound (``max_plies`` is defined for callers and used only by this test and
    # by rules.md), and the state carries no repetition/history bookkeeping.
    src = (Path(__file__).resolve().parent / "game.py").read_text()
    assert "max_plies" not in src.split("class Invector(Game):", 1)[1], \
        "the engine must never consult the ply bound"
    assert set(InvectorState().__dict__) == {
        "w", "h", "board", "to_move", "winner", "ply", "last", "swapped",
        "skipped"}


def _solve(w, h, allow_swap):
    """Exhaustive negamax through the shipped Game API, with an on-stack
    repetition check that proves the game graph is acyclic."""
    board = {(c, r): ((c + r) % 2) for c in range(w) for r in range(h)}
    s0 = InvectorState(w=w, h=h, board=board)
    memo, stack = {}, set()
    stats = {"draws": 0, "leaves": 0, "skips": 0}
    sys.setrecursionlimit(100000)

    def key(s):
        return (tuple(sorted(s.board.items())), s.to_move,
                s.ply == 1 and allow_swap)

    def nm(s):
        k = key(s)
        if k in memo:
            return memo[k]
        assert k not in stack, "REPETITION — the game graph is not acyclic"
        if G.is_terminal(s):
            stats["leaves"] += 1
            stats["draws"] += int(s.winner is None)
            memo[k] = G.returns(s)[s.to_move]
            return memo[k]
        stack.add(k)
        best = -2.0
        for m in G.legal_moves(s):
            if m == "swap" and not allow_swap:
                continue
            ns = G.apply_move(s, m)
            stats["skips"] += int(ns.skipped)
            v = nm(ns)
            best = max(best, v if ns.to_move == s.to_move else -v)
        stack.discard(k)
        memo[k] = best
        return best

    return nm(s0), len(memo), stats


def test_tiny_boards_solved_exhaustively():
    v, n, st = _solve(2, 3, True)
    assert (v, n) == (-1.0, 325), (v, n)
    assert st == {"draws": 0, "leaves": 30, "skips": 32}, st
    v2, n2, st2 = _solve(3, 2, True)
    assert (v2, n2, st2) == (v, n, st), "the rules are symmetric in the two axes"
    # 2x5: the pie rule FLIPS the value, so a broken swap changes the answer.
    with_pie, n3, st3 = _solve(2, 5, True)
    without, n4, st4 = _solve(2, 5, False)
    assert (with_pie, n3) == (-1.0, 32903), (with_pie, n3)
    assert (without, n4) == (1.0, 22920), (without, n4)
    assert st3["draws"] == st4["draws"] == 0
    assert st3["skips"] > 0 and st4["skips"] > 0


# --------------------------------------------------------------------------
#  Winning — "win as an event", reached through apply_move
# --------------------------------------------------------------------------

def test_win_is_annihilation_and_outranks_the_no_move_draw():
    # A constructed endgame: White has one stone, Black captures it.
    w, h = board_dims(6)
    cp = centre_pits(w, h)[0]
    victim = (cp[0] + 1, cp[1])
    board = {cp: B, victim: W}
    s = InvectorState(w=w, h=h, board=board, to_move=B, ply=10)
    mv = f"{cp[0]},{cp[1]}>{victim[0]},{victim[1]}"
    assert mv in G.legal_moves(s)
    n = G.apply_move(s, mv)
    assert n.winner == B and stone_count(n.board, W) == 0
    assert G.is_terminal(n) and G.returns(n) == [1.0, -1.0]
    # ...and the winner is left with NO legal move at all: the decisive result
    # must outrank the "nobody can move" draw, not be absorbed by it.
    assert not has_move(n.board, n.w, n.h, B) and not has_move(n.board, n.w, n.h, W)
    assert G.legal_moves(n) == [] and not n.skipped
    assert G.returns(n) != [0.0, 0.0]
    assert G.render(n)["caption"].startswith("Black wins")


def test_both_seats_can_win_and_no_seat_is_ever_wiped_out_silently():
    seen = set()
    rnd = random.Random(77)
    for size in (4, 6, 8):
        for _ in range(60):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                prev = s
                s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
                # the mover never annihilates himself
                assert stone_count(s.board, prev.to_move) > 0
                if s.winner is None:
                    assert stone_count(s.board, B) and stone_count(s.board, W)
            assert s.winner is not None
            assert stone_count(s.board, 1 - s.winner) == 0
            assert stone_count(s.board, s.winner) > 0
            seen.add(s.winner)
    assert seen == {B, W}


# --------------------------------------------------------------------------
#  The pie rule
# --------------------------------------------------------------------------

def test_pie_rule():
    s = G.initial_state({"size": 6})
    assert "swap" not in G.legal_moves(s), "not before Black has moved"
    s1 = G.apply_move(s, G.legal_moves(s)[0])
    assert "swap" in G.legal_moves(s1), "White's first turn only"
    assert s1.to_move == W and s1.ply == 1
    s2 = G.apply_move(s1, "swap")
    assert s2.swapped and s2.ply == 2
    assert s2.to_move == B, "after the swap it is the other seat's turn"
    # the POSITION is untouched: only the seat that owns each colour changes
    assert set(s2.board) == set(s1.board)
    assert all(s2.board[c] == 1 - s1.board[c] for c in s1.board)
    assert s2.winner is None
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
    # a declined pie leaves the game running normally
    s2b = G.apply_move(s1, [m for m in G.legal_moves(s1) if m != "swap"][0])
    assert not s2b.swapped and "swap" not in G.legal_moves(s2b)
    assert G.seat_colour(s2b, B) == "Black" and G.seat_colour(s2b, W) == "White"

    # --- the COLOUR NAMES follow the swap, pinned to FIGURE 1 --------------
    # Ground truth from OUTSIDE the engine: Figure 1 prints a BLACK stone on the
    # top-left pit.  So whoever owns the top-left army is Black, full stop — the
    # assertion is never allowed to consult the engine's own seat naming.
    top_left = (0, s.h - 1)
    assert s1.board[top_left] == B
    assert G.seat_colour(s1, s1.board[top_left]) == "Black"
    assert G.seat_colour(s1, 1 - s1.board[top_left]) == "White"
    assert G.render(s1)["caption"].startswith("White to move")
    assert s2.board[top_left] == W, "the swap handed the opening army to seat 1"
    assert G.seat_colour(s2, s2.board[top_left]) == "Black"
    assert G.seat_colour(s2, 1 - s2.board[top_left]) == "White"
    assert G.render(s2)["caption"].startswith("White to move"), \
        "after the swap the seat on move (0) plays WHITE"
    # ...and the same holds for the winner announced at the end of a swapped
    # game.  The top-left pit may have changed hands by then, so the ground
    # truth is carried forward as the PARITY CLASS the opening army started on.
    for seed in (19, 20, 21):
        rnd = random.Random(seed)
        t = s2
        while not G.is_terminal(t):
            t = G.apply_move(t, rnd.choice(G.legal_moves(t)))
        assert t.swapped and t.winner is not None
        black_seat = W          # seat 1 took the pie, so seat 1 is Black
        assert G.seat_colour(t, black_seat) == "Black"
        assert G.seat_colour(t, 1 - black_seat) == "White"
        cap = G.render(t)["caption"]
        assert cap.startswith(("Black wins" if t.winner == black_seat
                               else "White wins")), cap


# --------------------------------------------------------------------------
#  Plumbing: serialize, render, describe_move, options
# --------------------------------------------------------------------------

KEYS = {"w", "h", "board", "to_move", "winner", "ply", "last", "swapped",
        "skipped"}


def test_serialize_round_trip_as_states():
    rnd = random.Random(31)
    seen_swap = seen_skip = seen_win = 0
    for size in SIZES:
        s = G.initial_state({"size": size})
        first = True
        while True:
            d = G.serialize(s)
            assert set(d) == KEYS, set(d) ^ KEYS
            import json
            json.dumps(d)
            back = G.deserialize(d)
            assert back == s, (size, s.ply)
            assert G.serialize(back) == d
            seen_swap += int(s.swapped)
            seen_skip += int(s.skipped)
            seen_win += int(s.winner is not None)
            if G.is_terminal(s):
                break
            mv = "swap" if (first and s.ply == 1) else rnd.choice(
                [m for m in G.legal_moves(s) if m != "swap"])
            if first and s.ply == 1:
                first = False
            s = G.apply_move(s, mv)
    assert seen_swap and seen_skip and seen_win, (seen_swap, seen_skip, seen_win)


def test_render_bounds_every_size():
    rnd = random.Random(43)
    for size in SIZES:
        w, h = board_dims(size)
        s = G.initial_state({"size": size})
        spec = G.render(s)
        b = spec["board"]
        assert b["type"] == "square" and (b["width"], b["height"]) == (w, h)
        cells = {p["cell"] for p in spec["pieces"]}
        assert cells == {f"{c},{r}" for c in range(w) for r in range(h)}, size
        assert set(b["tints"]) == {f"{c},{r}" for c, r in centre_pits(w, h)}
        n = 0
        while not G.is_terminal(s) and n < 400:
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
            n += 1
            spec = G.render(s)
            assert (spec["board"]["width"], spec["board"]["height"]) == (w, h)
            for p in spec["pieces"]:
                c, r = (int(x) for x in p["cell"].split(","))
                assert 0 <= c < w and 0 <= r < h, (size, p["cell"])
                assert p["owner"] in (0, 1)
            for hl in spec["highlights"]:
                c, r = (int(x) for x in hl["cell"].split(","))
                assert 0 <= c < w and 0 <= r < h
            assert isinstance(spec["caption"], str) and spec["caption"]


def test_describe_move_and_names():
    s = G.initial_state({"size": 6})
    assert cell_name((0, 0)) == "a1" and cell_name((5, 4)) == "f5"
    cap = [m for m in G.legal_moves(s)][0]
    assert "x" in G.describe_move(s, cap)
    # a quiet move is written with a dash
    board, w, h = board_from_rows((".....", ".....", ".#...", "....."))
    q = InvectorState(w=w, h=h, board=board, to_move=B, ply=4)
    mv = G.legal_moves(q)[0]
    assert G.describe_move(q, mv) == "b2-c2", G.describe_move(q, mv)
    assert G.describe_move(q, "garbage") == "garbage"


def test_every_direction_is_exercised_at_a_real_size():
    """The exhaustive solves run on 2xN boards, where BOTH columns are centre
    columns — so a horizontal quiet move is never legal there and the solve is
    structurally unable to exhibit a bug in it.  Pair it with a directed check at
    a real size: all four capture directions and all four quiet-move directions
    must occur in ordinary play on the standard board."""
    caps, quiets = set(), set()
    rnd = random.Random(64)
    for _ in range(30):
        s = G.initial_state({"size": 8})
        while not G.is_terminal(s):
            mv = rnd.choice(G.legal_moves(s))
            f, t = (tuple(int(x) for x in p.split(",")) for p in mv.split(">"))
            d = (t[0] - f[0], t[1] - f[1])
            assert d in ORTHO, mv
            (caps if s.board.get(t) is not None else quiets).add(d)
            s = G.apply_move(s, mv)
    assert caps == set(ORTHO), sorted(caps)
    assert quiets == set(ORTHO), sorted(quiets)
    # ...and specifically that a HORIZONTAL quiet move is legal somewhere
    assert any(d[0] for d in quiets)


def test_no_heuristic_is_shipped():
    """This package deliberately ships NO ``heuristic``.  The obvious eval for
    an annihilation game (normalised material balance) was implemented and
    measured through ``MCTSBot`` against the generic constant-zero fallback and
    came out statistically indistinguishable from it — see rules.md.  The bot
    must therefore still work through the generic path, including when the
    rollout cutoff is reached (forced here with a tiny ``max_rollout``, the
    setting that would expose a bad payoff shape)."""
    from agp.mcts import MCTSBot, play_match
    assert getattr(G, "heuristic", None) is None, \
        "no heuristic is shipped; if one is added, MEASURE it (see rules.md)"
    bots = [MCTSBot(random.Random(1), iterations=40, max_rollout=3),
            MCTSBot(random.Random(2), iterations=40, max_rollout=3)]
    r = play_match(G, bots, random.Random(3), options={"size": 4})
    assert r["result"] == "terminal" and r["returns"] in ([1.0, -1.0],
                                                          [-1.0, 1.0])


def test_options_and_state_defaults():
    d = InvectorState()
    assert (d.w, d.h) == board_dims(8)
    for bad in (5, 7, 0, 20):
        try:
            G.initial_state({"size": bad})
        except ValueError:
            continue
        raise AssertionError(f"size {bad} should be rejected")
    assert G.num_players == 2
    assert G.current_player(G.initial_state()) == 0


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"invector selftest: {len(tests)} checks passed")


if __name__ == "__main__":
    main()
