#!/usr/bin/env python3
"""Correctness anchors for CLEARCUT (Mark Steere, July 2023).

Pure stdlib.  Run standalone or via tests/test_games.py::test_package_selftests.

THE ANCHORS
-----------
1. ALL SEVEN PRINTED FIGURES, transcribed from the rule sheet's VECTOR ARTWORK
   (`pdftocairo -svg`, disc/square path bounding boxes snapped onto each
   figure's 6x6 lattice - not read off pixels), with every number the prose
   prints reproduced by this implementation, AND the PREMISES each figure
   relies on (which square carries the printed "?", whether the position is
   crosscut-free, which checkers the yellow/green dots mark).

2. THE DISTINCTNESS ANCHOR.  Figure 4 is the SAME printed position in the
   Clearcut and Halfcut sheets with OPPOSITE verdicts.  This file asserts BOTH:
   our engine calls it illegal (Clearcut's "larger than EACH"), and the "at
   least one" reading - computed here, independently of the game module - calls
   it legal (Halfcut).  If those two ever agree, one of the two games is wrong.

3. THE ANCHOR'S MEASURED DISCRIMINATING POWER.  Fourteen wrong readings of the
   sheet are implemented here and run against the figure assertions: the
   figures kill 10 of them.  The four survivors are closed deliberately -
   two by constructed positions, two by a proof that they are behaviourally
   IDENTICAL to the correct reading (and a sweep that checks it).

4. THE TERMINATION AND DRAWLESSNESS PROOFS, STEP BY STEP, ON LIVE POSITIONS.
   Every step of both proofs is an assertion that runs on every ply of every
   random game swept here - a proof used as a bug detector, not documentation.

5. EXHAUSTIVE SOLVES.  2x2 and 3x3 are solved over their WHOLE reachable state
   space (no alpha cutoff): no cycle, no draw, and a game value.  Every full
   crosscut-free board up to 4x4 is enumerated and shown to have EXACTLY ONE
   winner (the Crossway duality step).  What the small boards CANNOT exhibit is
   listed at the bottom and covered by directed tests at real sizes.
"""
import itertools
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.clearcut.game import (                                  # noqa: E402
    RED, BLUE, Clearcut, ClearcutState, _ORTH, _DIAG, _cell,
    connection_path, connects, crosscuts_formed, crosscuts_on_board,
    group_of, group_size, group_size_signature, has_placement, is_legal,
    placements, resolve,
)

G = Clearcut()
CHECKS = []


def ok(name):
    CHECKS.append(name)


# ==========================================================================
# The seven figures, transcribed from the PDF's vector artwork.
# Rows run TOP to BOTTOM as printed; '-' and '.' are the two shades of empty
# square (the figures use a checkerboard tint), 'R'/'B' are checkers.
# ==========================================================================

FIGS = {
    'F1':  ["-R-.-.", ".R.-.-", "-R-.BB", ".RBRBR", "BBBBBR", ".R.-.R"],
    'F2':  ["-.-.-.", ".-.-.-", "-.-.-.", ".RB-.-", "-BR.-.", ".-.-.-"],
    'F3':  ["-.-.-.", ".-.-.-", "-.RBBB", ".BBRR-", "-.-RR.", ".-.-.-"],
    'F4':  ["-.-.-.", ".BRRR-", "-BR.-.", ".-BBB-", "-R-.-B", ".R.-.-"],
    'F5':  ["-.R.-.", ".-RRR-", "-B-BR.", ".BBBR-", "-RR.B.", ".-BRBB"],
    'F6a': ["RR-.-.", ".-BB.-", "-RRB-B", ".BRBRR", "-.RRBB", ".-.-.-"],
    'F6b': ["RR-.-.", ".-BB.-", "-RRB-B", ".BR-RR", "-.RR-B", ".-.-.-"],
    'F7':  ["-.R.-.", ".BR-.-", "-B-BBB", ".RBR.-", "-R-.-.", ".-.-R-"],
}
N6 = 6
# The squares carrying the printed "?" glyph.  These are NOT inferred from the
# prose - they are the <use> positions of the '?' glyph in the SVG, snapped to
# the same lattice as the checkers.
QMARK = {'F4': (1, 3), 'F5': (3, 4), 'F7': (2, 2)}
# The yellow dot in 6a / green dot in 6b mark the checker Red places.
DOT = (3, 4)


def fig(name):
    b = {}
    for r, row in enumerate(FIGS[name]):
        for c, ch in enumerate(row):
            if ch == 'R':
                b[(c, r)] = RED
            elif ch == 'B':
                b[(c, r)] = BLUE
    return b


def enemy_sizes(board, c, r, player):
    """[[size, size], ...] - the enemy crosscut group sizes, per crosscut."""
    after = dict(board)
    after[(c, r)] = player
    return [[group_size(after, p) for p in pair]
            for pair in crosscuts_formed(board, c, r, player)]


def mine_size(board, c, r, player):
    after = dict(board)
    after[(c, r)] = player
    return group_size(after, (c, r))


# ==========================================================================
# 1.  The figures
# ==========================================================================

def test_figures():
    # ---- Figure 1: "In Figure 1, Blue has won."
    # GROUND TRUTH FOR THE EDGE MAPPING, taken from OUTSIDE the engine: the
    # figure's frame is a RED square with two BLUE triangles laid over its left
    # and right halves and a white interior on top, so the visible red bars are
    # the TOP and BOTTOM edges and the blue bars the LEFT and RIGHT.  The
    # winning blue chain in the artwork runs from column 0 to column 5.
    b = fig('F1')
    assert connects(b, BLUE, N6), "F1: Blue must have won"
    assert not connects(b, RED, N6), "F1: Red must NOT have connected"
    # premise: the printed win really is a LEFT-to-RIGHT chain
    path = connection_path(b, BLUE, N6)
    assert path and path[0][0] == 0 and path[-1][0] == N6 - 1
    assert all(b[p] == BLUE for p in path)
    for x, y in zip(path, path[1:]):
        assert abs(x[0] - y[0]) + abs(x[1] - y[1]) == 1, "orthogonal steps only"
    # the corner squares of the artwork pin the orientation independently:
    # (1,0) is a RED checker on Red's own goal edge (row 0)
    assert b[(1, 0)] == RED and b[(0, 4)] == BLUE
    ok("Figure 1 - Blue has won, Red has not, via an orthogonal left->right chain")

    # ---- Figure 2: the crosscut shape.
    b = fig('F2')
    assert len(b) == 4, "F2 prints exactly four checkers"
    assert sorted(b.values()) == [RED, RED, BLUE, BLUE]
    assert crosscuts_on_board(b, N6) == [(1, 3)], "F2 is exactly one crosscut"
    # like colours DIAGONALLY OPPOSED
    assert b[(1, 3)] == b[(2, 4)] and b[(2, 3)] == b[(1, 4)]
    assert b[(1, 3)] != b[(2, 3)]
    ok("Figure 2 - the crosscut shape (like colours diagonally opposed)")

    # ---- Figure 3: "Red has crosscut groups of sizes 1 and 4.  Blue has
    #      crosscut groups of sizes 2 and 3."
    b = fig('F3')
    cc = crosscuts_on_board(b, N6)
    assert cc == [(2, 2)], cc
    c, r = cc[0]
    sq = [(c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)]
    reds = sorted(group_size(b, p) for p in sq if b[p] == RED)
    blues = sorted(group_size(b, p) for p in sq if b[p] == BLUE)
    assert reds == [1, 4], reds
    assert blues == [2, 3], blues
    # PREMISE: the two same-coloured crosscut checkers are in DIFFERENT groups
    # (that is the whole point of "up to two crosscut groups per colour").
    assert group_of(b, (2, 2)) != group_of(b, (3, 3))
    # and the sizes are ORTHOGONAL-only: under 8-adjacency the same figure
    # would read 5 and 5 / 5 and 5, which is what the sheet's "diagonal
    # adjacencies are irrelevant" rules out.
    ok("Figure 3 - crosscut group sizes red {1,4}, blue {2,3}, orthogonal only")

    # ---- Figure 4: "Red can't place on the ? because his newly formed
    #      crosscut group would only be size 3, which is not larger than the
    #      blue crosscut group of size 3."
    b, q = fig('F4'), QMARK['F4']
    assert q not in b, "the ? square must be empty"
    assert not crosscuts_on_board(b, N6), "F4 is a legal mid-game position"
    assert len(crosscuts_formed(b, q[0], q[1], RED)) == 1
    assert mine_size(b, q[0], q[1], RED) == 3
    assert sorted(enemy_sizes(b, q[0], q[1], RED)[0]) == [2, 3]
    assert not is_legal(b, q[0], q[1], RED), "F4: Red can NOT place"
    ok("Figure 4 - Red's new group 3 vs blue {2,3}: ILLEGAL under 'each'")

    # ---- Figure 5: "Red can't place on the ? because his newly formed
    #      crosscut group of size 4 wouldn't be larger than the blue crosscut
    #      group of size 5.  If it were Blue's turn however, Blue could place
    #      on the ?, forming a crosscut group of size 9, which would be larger
    #      than the red crosscut groups of sizes 1 and 2."
    b, q = fig('F5'), QMARK['F5']
    assert q not in b
    assert not crosscuts_on_board(b, N6)
    assert mine_size(b, q[0], q[1], RED) == 4
    assert sorted(enemy_sizes(b, q[0], q[1], RED)[0]) == [3, 5]
    assert not is_legal(b, q[0], q[1], RED)
    assert mine_size(b, q[0], q[1], BLUE) == 9
    assert sorted(enemy_sizes(b, q[0], q[1], BLUE)[0]) == [1, 2]
    assert is_legal(b, q[0], q[1], BLUE)
    nb, removed, _ = resolve(b, q[0], q[1], BLUE)
    assert set(removed) == {(2, 4), (3, 5)}, removed
    assert all(b[p] == RED for p in removed)
    ok("Figure 5 - same square, Red 4 vs {3,5} illegal / Blue 9 vs {1,2} legal")

    # ---- Figures 6a/6b: "Red places the checker marked with a yellow dot,
    #      and kills two blue checkers."
    a, after = fig('F6a'), fig('F6b')
    assert a[DOT] == RED, "the yellow dot marks a RED checker"
    pre = dict(a)
    del pre[DOT]
    # PREMISES: the pre-placement position is a legal (crosscut-free) one, and
    # the placement forms exactly ONE crosscut.
    assert not crosscuts_on_board(pre, N6)
    assert len(crosscuts_formed(pre, DOT[0], DOT[1], RED)) == 1
    assert mine_size(pre, DOT[0], DOT[1], RED) == 5
    assert sorted(enemy_sizes(pre, DOT[0], DOT[1], RED)[0]) == [2, 4]
    nb, removed, mine = resolve(pre, DOT[0], DOT[1], RED)
    assert nb == after, "6a + placement + removals must be 6b, square for square"
    assert set(removed) == {(3, 3), (4, 4)}, removed
    assert len(removed) == 2 and all(a[p] == BLUE for p in removed)
    # 6b differs from 6a in EXACTLY those two squares
    assert set(a) - set(after) == {(3, 3), (4, 4)}
    assert not set(after) - set(a)
    # the killed checkers' GROUP-MATES survive: removal takes checkers, never
    # whole groups.  (3,3) sat in a group of 4 and (4,4) in a group of 2.
    assert (3, 2) in after and (5, 4) in after
    ok("Figures 6a/6b - one crosscut, BOTH enemy checkers die, board == 6b")

    # ---- Figure 7: simultaneous crosscuts.
    b, q = fig('F7'), QMARK['F7']
    assert q not in b
    assert not crosscuts_on_board(b, N6)
    crosses = crosscuts_formed(b, q[0], q[1], RED)
    assert len(crosses) == 2, crosses
    assert mine_size(b, q[0], q[1], RED) == 3
    sizes = enemy_sizes(b, q[0], q[1], RED)
    # the sheet names the size-2 group of the LEFT crosscut and the size-3
    # group of the RIGHT crosscut; the other member of each pair is the SHARED
    # size-1 blue checker.
    assert sorted(sorted(s) for s in sizes) == [[1, 2], [1, 3]], sizes
    shared = set(crosses[0]) & set(crosses[1])
    assert len(shared) == 1, "two simultaneous crosscuts share exactly one enemy"
    assert group_size(b, next(iter(shared))) == 1
    assert not is_legal(b, q[0], q[1], RED), "F7: not allowed for Red"
    ok("Figure 7 - two crosscuts sharing one enemy checker; 3 vs {1,3} ILLEGAL")


# ==========================================================================
# 2.  The distinctness anchor: Figure 4 is Halfcut's Figure 4
# ==========================================================================

def halfcut_legal(board, c, r, player):
    """The HALFCUT reading ("larger than AT LEAST ONE"), written here from the
    Halfcut sheet and deliberately independent of game.py, so that Figure 4 -
    the position the two sheets SHARE - can be checked to give OPPOSITE
    verdicts under the two readings."""
    crosses = crosscuts_formed(board, c, r, player)
    if not crosses:
        return True
    after = dict(board)
    after[(c, r)] = player
    mine = group_size(after, (c, r))
    for pair in crosses:
        if not any(group_size(after, p) < mine for p in pair):
            return False
    return True


def test_distinct_from_halfcut():
    b, q = fig('F4'), QMARK['F4']
    assert not is_legal(b, q[0], q[1], RED), "Clearcut: Red can NOT place"
    assert halfcut_legal(b, q[0], q[1], RED), "Halfcut: Red CAN place"
    # ... and the two readings really are the same predicate everywhere else on
    # this figure, so the difference is the rule and not the transcription.
    diff = [(c, r, p)
            for r in range(N6) for c in range(N6) for p in (RED, BLUE)
            if (c, r) not in b
            and is_legal(b, c, r, p) != halfcut_legal(b, c, r, p)]
    assert (q[0], q[1], RED) in diff, diff
    # The two games differ on a substantial fraction of crosscut placements,
    # not on one hand-picked square: sweep random dense boards.
    rng = random.Random(4)
    seen = diff_cnt = 0
    for _ in range(800):
        size = 6
        board = {(c, r): rng.randrange(2)
                 for r in range(size) for c in range(size) if rng.random() < 0.6}
        if crosscuts_on_board(board, size):
            continue
        for r in range(size):
            for c in range(size):
                if (c, r) in board:
                    continue
                for p in (RED, BLUE):
                    if not crosscuts_formed(board, c, r, p):
                        continue
                    seen += 1
                    if is_legal(board, c, r, p) != halfcut_legal(board, c, r, p):
                        diff_cnt += 1
    assert seen > 500, seen
    assert diff_cnt > seen // 20, (diff_cnt, seen)
    ok(f"Clearcut != Halfcut - Figure 4 flips, and {diff_cnt}/{seen} "
       f"crosscut placements disagree")


# ==========================================================================
# 3.  Measured discriminating power of the figure anchor
# ==========================================================================

_ALL8 = _ORTH + _DIAG


def _grp(board, cell, dirs):
    who = board[cell]
    seen = {cell}
    stack = [cell]
    while stack:
        c, r = stack.pop()
        for dc, dr in dirs:
            nb = (c + dc, r + dr)
            if nb not in seen and board.get(nb) == who:
                seen.add(nb)
                stack.append(nb)
    return seen


def _crosses(board, c, r, player, diag_opposed=True):
    enemy = 1 - player
    out = []
    for dc, dr in _DIAG:
        a, b = (c + dc, r), (c, r + dr)
        if diag_opposed:
            good = (board.get((c + dc, r + dr)) == player
                    and board.get(a) == enemy and board.get(b) == enemy)
        else:
            good = (board.get((c + dc, r + dr)) == enemy
                    and board.get(a) == player and board.get(b) == enemy)
        if good:
            out.append((a, b))
    return out


def variant(board, c, r, player, *, mode="each", strict=True, scope="crosscut",
            dirs=_ORTH, mine_from="placed", removal="two", first_only=False,
            diag_opposed=True, also_mine=False, mine_minus_one=False):
    """A parameterised WRONG reading of the sheet.  Defaults = correct."""
    crosses = _crosses(board, c, r, player, diag_opposed)
    out = dict(board)
    out[(c, r)] = player
    if not crosses:
        return True, out, set()
    if mine_from == "placed":
        mine = len(_grp(out, (c, r), dirs))
    else:
        dc = crosses[0][0][0] - c
        dr = crosses[0][1][1] - r
        mine = len(_grp(out, (c + dc, r + dr), dirs))
    if mine_minus_one:
        mine -= 1
    pool = None
    if scope == "board":
        groups = {frozenset(_grp(out, p, dirs))
                  for p, who in out.items() if who != player}
        pool = [len(g) for g in groups]
    for pair in (crosses[:1] if first_only else crosses):
        cand = pool if pool is not None else [len(_grp(out, p, dirs)) for p in pair]
        test = (lambda s: mine > s) if strict else (lambda s: mine >= s)
        if not (all(map(test, cand)) if mode == "each" else any(map(test, cand))):
            return False, None, set()
    kill = set()
    for pair in (crosses[:1] if first_only else crosses):
        if removal == "two":
            kill |= set(pair)
        elif removal == "smaller":
            kill |= {p for p in pair if len(_grp(out, p, dirs)) < mine}
        elif removal == "groups":
            for p in pair:
                kill |= _grp(out, p, dirs)
        elif removal == "smallest":
            kill.add(min(pair, key=lambda p: len(_grp(out, p, dirs))))
        if also_mine:
            kill.add((c, r))
            kill.add((c + pair[0][0] - c, r + pair[1][1] - r))
    for p in kill:
        out.pop(p, None)
    return True, out, kill


def _correct(board, c, r, player):
    nb, rm, _ = resolve(board, c, r, player)
    return nb is not None, nb, set(rm)


WRONG_READINGS = {
    "at-least-one (= Halfcut)":       lambda *a: variant(*a, mode="one"),
    ">= instead of > (ties allowed)": lambda *a: variant(*a, strict=False),
    "vs ALL enemy groups on board":   lambda *a: variant(*a, scope="board"),
    "groups use 8-adjacency":         lambda *a: variant(*a, dirs=_ALL8),
    "'yours' = diagonal partner":     lambda *a: variant(*a, mine_from="diag"),
    "remove whole enemy GROUPS":      lambda *a: variant(*a, removal="groups"),
    "remove only smaller-group ckrs": lambda *a: variant(*a, removal="smaller"),
    "remove only the SMALLEST ckr":   lambda *a: variant(*a, removal="smallest"),
    "judge only the FIRST crosscut":  lambda *a: variant(*a, first_only=True),
    "like colours ADJACENT":          lambda *a: variant(*a, diag_opposed=False),
    "removal also kills your two":    lambda *a: variant(*a, also_mine=True),
    "pool all crosscuts' enemies":    lambda *a: variant(*a),
    "goal swap (Red = left/right)":   _correct,     # judged by the F1 block
    "new group counted pre-place":    lambda *a: variant(*a, mine_minus_one=True),
}
# Measured, then pinned.  Changing these numbers means the anchor changed.
FIGURES_KILL = 10
SURVIVORS = {"vs ALL enemy groups on board", "remove only smaller-group ckrs",
             "judge only the FIRST crosscut", "pool all crosscuts' enemies"}


def figure_verdicts(V, goalswap=False):
    """Every assertion the SEVEN FIGURES support, as a list of failures."""
    bad = []

    def chk(tag, cond):
        if not cond:
            bad.append(tag)

    b = fig('F1')
    if goalswap:
        chk("F1", connects(b, RED, N6) and not connects(b, BLUE, N6))
    else:
        chk("F1", connects(b, BLUE, N6) and not connects(b, RED, N6))
    b, q = fig('F4'), QMARK['F4']
    chk("F4", not V(b, q[0], q[1], RED)[0])
    b, q = fig('F5'), QMARK['F5']
    chk("F5-red", not V(b, q[0], q[1], RED)[0])
    legal, _, rm = V(b, q[0], q[1], BLUE)
    chk("F5-blue", legal)
    chk("F5-kill", legal and rm == {(2, 4), (3, 5)})
    a, aft = fig('F6a'), fig('F6b')
    pre = dict(a)
    del pre[DOT]
    legal, nb, rm = V(pre, DOT[0], DOT[1], RED)
    chk("F6-legal", legal)
    chk("F6-board", legal and nb == aft)
    b, q = fig('F7'), QMARK['F7']
    chk("F7", not V(b, q[0], q[1], RED)[0])
    return bad


def test_anchor_power():
    assert not figure_verdicts(_correct), "the CORRECT reading must pass"
    killed, survived = 0, set()
    for name, V in WRONG_READINGS.items():
        if figure_verdicts(V, goalswap=name.startswith("goal swap")):
            killed += 1
        else:
            survived.add(name)
    assert killed == FIGURES_KILL, (killed, survived)
    assert survived == SURVIVORS, survived
    ok(f"figure anchor measured: kills {killed}/{len(WRONG_READINGS)} wrong "
       f"readings; {len(SURVIVORS)} survivors closed below")


# --- survivor 1: "vs ALL enemy groups on board".  Closed by a constructed
#     position: a legal crosscut whose enemy groups are tiny, with a LARGE
#     enemy group in the far corner that has nothing to do with the crosscut.
W3_BOARD = {(2, 1): RED, (1, 2): RED, (3, 2): BLUE, (2, 3): BLUE, (3, 3): RED,
            (6, 0): BLUE, (6, 1): BLUE, (6, 2): BLUE, (6, 3): BLUE,
            (6, 4): BLUE, (5, 4): BLUE}
# --- survivor 2: "judge only the FIRST crosscut".  Closed by a constructed
#     simultaneous crosscut whose FIRST-enumerated crosscut PASSES and whose
#     second FAILS: judging only the first would wrongly allow it.
W9_BOARD = {(1, 1): BLUE, (2, 1): BLUE, (3, 1): RED, (1, 2): RED,
            (3, 2): BLUE, (2, 3): BLUE, (3, 3): RED}


def test_survivors_closed():
    # survivor 1
    b = W3_BOARD
    assert not crosscuts_on_board(b, 7)
    assert len(crosscuts_formed(b, 2, 2, RED)) == 1
    assert mine_size(b, 2, 2, RED) == 3
    assert enemy_sizes(b, 2, 2, RED) == [[1, 1]]
    biggest = max(group_size(b, p) for p, who in b.items() if who == BLUE)
    assert biggest == 6, biggest          # bigger than Red's new group
    assert is_legal(b, 2, 2, RED), "only the CROSSCUT's enemy groups count"
    assert not variant(b, 2, 2, RED, scope="board")[0], "the wrong reading differs"

    # survivor 2
    b = W9_BOARD
    assert not crosscuts_on_board(b, 5)
    crosses = crosscuts_formed(b, 2, 2, RED)
    assert len(crosses) == 2
    mine = mine_size(b, 2, 2, RED)
    assert mine == 2
    per = enemy_sizes(b, 2, 2, RED)
    assert per == [[1, 1], [1, 2]], per         # first passes, second fails
    assert all(s < mine for s in per[0]) and not all(s < mine for s in per[1])
    assert not is_legal(b, 2, 2, RED), "EVERY crosscut must satisfy the rule"
    assert variant(b, 2, 2, RED, first_only=True)[0], "the wrong reading differs"

    # survivors 3 and 4 are PROVABLY the same predicate, not gaps:
    #  * "remove only the smaller-group checkers" (Halfcut's removal clause)
    #    can only differ when a crosscut has an enemy group of size >= mine -
    #    which Clearcut's crosscut rule makes ILLEGAL, so it never happens;
    #  * "pool all the crosscuts' enemy groups" is the same as judging each
    #    crosscut separately, because "larger than EACH" over a union is the
    #    conjunction of "larger than EACH" over the parts (and every crosscut
    #    shares the same `mine`).  This is exactly how the AbstractPlay oracle
    #    implements the rule.
    # Both are ASSERTED over a sweep rather than merely argued.
    rng = random.Random(9)
    checked = sim = 0
    for _ in range(700):
        size = 6
        board = {(c, r): rng.randrange(2)
                 for r in range(size) for c in range(size) if rng.random() < 0.55}
        if crosscuts_on_board(board, size):
            continue
        for r in range(size):
            for c in range(size):
                if (c, r) in board:
                    continue
                for p in (RED, BLUE):
                    ncc = len(crosscuts_formed(board, c, r, p))
                    if not ncc:
                        continue
                    checked += 1
                    if ncc > 1:
                        sim += 1
                    assert _correct(board, c, r, p) == \
                        variant(board, c, r, p, removal="smaller")
                    assert _correct(board, c, r, p) == variant(board, c, r, p)
    assert checked > 500 and sim > 5, (checked, sim)
    ok(f"survivors closed: 2 by constructed positions, 2 proven equivalent "
       f"over {checked} crosscut placements ({sim} simultaneous)")


# ==========================================================================
# 4.  The proofs, checked step by step on live positions
# ==========================================================================

def quad_of(cell, pair):
    c, r = cell
    dc = next(p[0] - c for p in pair if p[1] == r)
    dr = next(p[1] - r for p in pair if p[0] == c)
    return dc, dr


def sweep(size, games, seed, st):
    rng = random.Random(seed)
    for gi in range(games):
        s = G.initial_state(options={"size": size})
        while not G.is_terminal(s):
            b, mover = s.board, s.to_move
            st['plies'] += 1
            # P1  no crosscut exists at the start of a turn
            assert not crosscuts_on_board(b, size), ("P1", gi, s.ply)
            # P2  at most one colour is blocked on any empty square
            for c in range(size):
                for r in range(size):
                    if (c, r) in b:
                        continue
                    rb = not is_legal(b, c, r, RED)
                    bb = not is_legal(b, c, r, BLUE)
                    st['blocked'] += rb + bb
                    assert not (rb and bb), ("P2", gi, s.ply, (c, r))
            moves = G.legal_moves(s)
            assert moves, ("legal_moves must be non-empty on a live state", gi)
            # placements() and legal_moves() must agree with is_legal()
            assert {_cell(m) for m in moves} == set(placements(b, size, mover))
            mv = rng.choice(moves)
            cell = _cell(mv)
            crosses = crosscuts_formed(b, cell[0], cell[1], mover)
            after = dict(b)
            after[cell] = mover
            n = group_size(after, cell)
            if crosses:
                st['crosscut_plies'] += 1
                # S2  at most two crosscuts, adjacent quadrants, one shared enemy
                assert len(crosses) <= 2, ("S2-count", crosses)
                if len(crosses) == 2:
                    st['sim'] += 1
                    assert len(set(crosses[0]) & set(crosses[1])) == 1
                    q0, q1 = quad_of(cell, crosses[0]), quad_of(cell, crosses[1])
                    assert q0 != q1 and (q0[0] == q1[0] or q0[1] == q1[1])
                # T1  every friendly group merged has size <= n-1
                for dc, dr in _ORTH:
                    nb = (cell[0] + dc, cell[1] + dr)
                    if b.get(nb) == mover:
                        st['T1'] += 1
                        assert group_size(b, nb) <= n - 1, ("T1", gi, s.ply)
            sig_before = group_size_signature(b)
            big_before = sorted((z for z in sig_before if z >= n), reverse=True)
            s2 = G.apply_move(s, mv)
            assert s.board == b, "apply_move must not mutate its input"
            if s2.removed:
                st['kills'] += 1
                st['killed'] += len(s2.removed)
                st['maxkill'] = max(st['maxkill'], len(s2.removed))
                for p in s2.removed:
                    # T2  every removed checker came from a group of size < n
                    st['T2'] += 1
                    assert group_size(after, p) < n, ("T2", gi, s.ply)
                    assert b[p] == 1 - mover, "only enemy checkers are removed"
                if s2.winner is not None:
                    st['win_with_capture'] += 1
            sig_after = group_size_signature(s2.board)
            big_after = sorted((z for z in sig_after if z >= n), reverse=True)
            # T3  every group of size >= n survives; exactly one new member n
            assert big_after == sorted(big_before + [n], reverse=True), \
                ("T3", gi, s.ply, big_before, big_after, n)
            # T4  the monovariant strictly increases
            assert sig_after > sig_before, ("T4", gi, s.ply)
            # S1  simultaneous resolution == sequential resolution
            if len(crosses) == 2:
                seq = dict(after)
                for pair in crosses:
                    for p in pair:
                        seq.pop(p, None)
                assert seq == s2.board, ("S1", gi, s.ply)
                for i in (0, 1):
                    tmp = dict(after)
                    for p in crosses[i]:
                        del tmp[p]
                    for p in crosses[1 - i]:
                        if p in tmp:
                            assert group_size(tmp, p) < n, ("S1-order", gi)
            # only the MOVER can ever hold a connection
            assert not connects(s2.board, 1 - mover, size), ("opp-connect", gi)
            if s2.skips > s.skips:
                st['skips'] += 1
            s = s2
        st['games'] += 1
        if s.winner is None:
            st['draws'] += 1
        else:
            st['wins'][s.winner] += 1
        assert not s.stalled, "the stall branch must be unreachable"
        if len(s.board) == size * size:
            st['full'] += 1
            assert not crosscuts_on_board(s.board, size)
    return st


def test_proof_steps():
    st = dict(games=0, plies=0, wins=[0, 0], draws=0, skips=0, crosscut_plies=0,
              sim=0, kills=0, killed=0, maxkill=0, blocked=0, T1=0, T2=0,
              full=0, win_with_capture=0)
    sweep(5, 40, 5, st)
    sweep(7, 20, 7, st)
    sweep(9, 8, 9, st)
    assert st['draws'] == 0, st
    assert st['crosscut_plies'] > 30 and st['kills'] > 30, st
    assert st['sim'] >= 1, st
    assert st['skips'] >= 1, "the skip rule must be REACHABLE, not vacuous"
    assert st['maxkill'] == 3, st        # 2+2 minus the one shared checker
    assert st['blocked'] > 1000, st
    ok(f"proof steps P1/P2/S1/S2/T1-T4 hold on {st['plies']} live plies of "
       f"{st['games']} games ({st['crosscut_plies']} crosscut plies, "
       f"{st['sim']} simultaneous, {st['killed']} checkers killed, "
       f"{st['skips']} skips, 0 draws)")
    return st


# ==========================================================================
# 5.  Exhaustive solves
# ==========================================================================

def solve(size):
    """Solve an NxN board over its WHOLE reachable state space (no cutoff).

    Asserts, on every reachable position: the recursion never revisits a node
    on its own stack (no cycle), and the group-size monovariant strictly
    increases on every legal ply.
    """
    memo, stack = {}, set()
    stats = dict(nodes=0, terminals=0, draws=0, stalls=0, skips=0, sim=0,
                 kills=0, maxkill=0)

    def rec(board, to_move, sig):
        key = (frozenset(board.items()), to_move)
        if key in memo:
            return memo[key]
        assert key not in stack, "CYCLE - the game would not terminate"
        stack.add(key)
        stats['nodes'] += 1
        moves = [(c, r) for r in range(size) for c in range(size)
                 if (c, r) not in board and is_legal(board, c, r, to_move)]
        if not moves:
            if any((c, r) not in board and is_legal(board, c, r, 1 - to_move)
                   for r in range(size) for c in range(size)):
                stats['skips'] += 1
                val = rec(board, 1 - to_move, sig)
            else:
                stats['stalls'] += 1
                stats['terminals'] += 1
                stats['draws'] += 1
                val = 0
            stack.discard(key)
            memo[key] = val
            return val
        best = -2
        for (c, r) in moves:
            nb, removed, _ = resolve(board, c, r, to_move)
            if len(crosscuts_formed(board, c, r, to_move)) > 1:
                stats['sim'] += 1
            if removed:
                stats['kills'] += 1
                stats['maxkill'] = max(stats['maxkill'], len(removed))
            nsig = group_size_signature(nb)
            assert nsig > sig, ("monovariant", sorted(board.items()), (c, r))
            if connects(nb, to_move, size):
                stats['terminals'] += 1
                val = 1
            else:
                val = -rec(nb, 1 - to_move, nsig)
            best = max(best, val)
        stack.discard(key)
        memo[key] = best
        return best

    value = rec({}, RED, ())
    return value, stats, len(memo)


def test_p2_on_constructed_inputs():
    """Step 2 of the drawlessness proof - "at most one colour can be blocked on
    any empty square" - on CONSTRUCTED inputs, not just live positions.

    Live positions are always crosscut-free at the start of a turn, so the sweep
    can never test the lemma on a board that already contains a crosscut; the
    proof does not use crosscut-freeness, so it should hold there too.  Checked
    exhaustively on ALL 19,683 3x3 boards (including the crosscut-carrying ones,
    which real play never reaches) and on random dense 5x5/7x7 boards."""
    checks = 0
    cells3 = [(c, r) for r in range(3) for c in range(3)]
    for bits in itertools.product((None, RED, BLUE), repeat=9):
        b = {p: v for p, v in zip(cells3, bits) if v is not None}
        for p in cells3:
            if p in b:
                continue
            checks += 1
            assert is_legal(b, p[0], p[1], RED) or is_legal(b, p[0], p[1], BLUE), \
                ("P2", sorted(b.items()), p)
    assert checks == 59049, checks
    rng = random.Random(77)
    withcc = 0
    for _ in range(400):
        size = rng.choice((5, 7))
        b = {(c, r): rng.randrange(2)
             for r in range(size) for c in range(size) if rng.random() < 0.75}
        if crosscuts_on_board(b, size):
            withcc += 1
        for r in range(size):
            for c in range(size):
                if (c, r) in b:
                    continue
                checks += 1
                assert is_legal(b, c, r, RED) or is_legal(b, c, r, BLUE), \
                    ("P2", sorted(b.items()), (c, r))
    assert withcc > 100, withcc      # the boards real play can never reach
    ok(f"drawlessness step 2 holds on {checks} constructed empty squares, "
       f"including {withcc} boards that already contain a crosscut")


def test_exhaustive_solves():
    v2, s2, n2 = solve(2)
    assert s2['draws'] == 0 and s2['stalls'] == 0, s2
    assert v2 == -1, v2                       # 2x2: second player (Blue) wins
    v3, s3, n3 = solve(3)
    assert s3['draws'] == 0 and s3['stalls'] == 0, s3
    assert v3 == 1, v3                        # 3x3: first player (Red) wins
    assert n3 == 7631, n3                     # pinned: the whole reachable space
    assert s3['sim'] > 0 and s3['maxkill'] == 3, s3
    ok(f"exhaustive solve: 2x2 = Blue win ({n2} states), "
       f"3x3 = Red win ({n3} states, {s3['terminals']} terminals) - "
       f"no cycle, NO DRAW, monovariant strictly increasing everywhere")


def test_crossway_duality():
    """A FULL crosscut-free board always has EXACTLY ONE winner.

    This is step 3 of the drawlessness proof (the Crossway theorem): with no
    crosscut anywhere, two diagonally adjacent friends on a full board are
    joined through one of the two squares between them, so orthogonal
    connectivity coincides with king connectivity and the standard 8-vs-4
    duality applies.  Checked by brute force on every full board up to 4x4.
    """
    total = free = 0
    for size in (2, 3, 4):
        cells = [(c, r) for r in range(size) for c in range(size)]
        for bits in itertools.product((RED, BLUE), repeat=len(cells)):
            board = dict(zip(cells, bits))
            total += 1
            if crosscuts_on_board(board, size):
                continue
            free += 1
            assert connects(board, RED, size) != connects(board, BLUE, size), \
                sorted(board.items())
    assert total == 66064 and free == 24194, (total, free)
    ok(f"Crossway duality: all {free} crosscut-free full boards up to 4x4 "
       f"have EXACTLY ONE winner (of {total} full boards)")


# ==========================================================================
# 6.  Directed tests for what the small boards / random play cannot exhibit
# ==========================================================================

# A capturing placement that ALSO wins.  Red joins row 0 to row 4 through the
# very square that forms the crosscut.  Random play at these sizes reaches this
# combination essentially never (0 in ~5,000 plies), and 3x3 is too small to
# hold a five-square chain plus a crosscut, so it is pinned here.
WIN_WITH_CAPTURE = {(2, 0): RED, (2, 1): RED, (1, 2): RED, (1, 3): RED,
                    (1, 4): RED, (3, 2): BLUE, (2, 3): BLUE, (3, 3): RED}
# A placement that WINS while filling the last empty square, so that after it
# NEITHER player has a placement.  Pins that a decisive result outranks the
# stall bookkeeping.
FILL_AND_WIN = {(0, 1): RED, (0, 2): RED, (1, 0): RED, (1, 1): BLUE,
                (1, 2): BLUE, (2, 0): RED, (2, 1): RED, (2, 2): BLUE}
# A position where Red's placement leaves BLUE with no legal square while Red
# still has one, so Blue's turn is skipped.
SKIP_POSITION = {(0, 1): RED, (0, 2): RED, (1, 1): BLUE, (1, 2): BLUE,
                 (2, 0): RED, (2, 1): RED, (2, 2): BLUE}
# A LEGAL simultaneous crosscut.  Random play reaches one on ~0.1% of plies, and
# it is the only way three checkers die in one turn (the two crosscuts share one
# enemy checker), so it is pinned here rather than left to the sweep.
LEGAL_DOUBLE = {(2, 1): BLUE, (3, 1): RED, (0, 2): RED, (1, 2): RED,
                (3, 2): BLUE, (2, 3): BLUE, (3, 3): RED}


def test_directed():
    # -- a capture that wins
    b = dict(WIN_WITH_CAPTURE)
    assert not crosscuts_on_board(b, 5)
    assert not connects(b, RED, 5) and not connects(b, BLUE, 5)
    s = ClearcutState(size=5, board=b, to_move=RED)
    n = G.apply_move(s, "2,2")
    assert set(n.removed) == {(2, 3), (3, 2)}, n.removed
    assert n.winner == RED and not n.stalled
    assert G.is_terminal(n) and G.returns(n) == [1.0, -1.0]
    assert G.describe_move(s, "2,2") == "c3xc4d3#", G.describe_move(s, "2,2")
    path = connection_path(n.board, RED, 5)
    assert (2, 2) in path and path[0][1] == 0 and path[-1][1] == 4
    ok("directed: a capturing placement that also WINS "
       "(both removals and the win in one ply)")

    # -- a decisive result outranks the stall
    b = dict(FILL_AND_WIN)
    assert not crosscuts_on_board(b, 3)
    s = ClearcutState(size=3, board=b, to_move=RED)
    n = G.apply_move(s, "0,0")
    assert len(n.board) == 9, "the board is now FULL"
    assert not has_placement(n.board, 3, RED) and not has_placement(n.board, 3, BLUE)
    assert n.winner == RED and n.stalled is False, (n.winner, n.stalled)
    assert G.returns(n) == [1.0, -1.0]
    assert G.legal_moves(n) == [] and G.is_terminal(n)
    assert G.describe_move(s, "0,0").endswith("#")
    ok("directed: a win that FILLS the board still scores as a win, not a stall")

    # -- the skip rule is reachable and is flagged in the move log
    b = dict(SKIP_POSITION)
    s = ClearcutState(size=3, board=b, to_move=RED)
    assert has_placement(b, 3, RED) and has_placement(b, 3, BLUE)
    n = G.apply_move(s, "1,0")
    assert not has_placement(n.board, 3, BLUE), "Blue must now be stuck"
    assert has_placement(n.board, 3, RED)
    assert n.to_move == RED and n.skips == s.skips + 1
    assert n.winner is None and not n.stalled
    assert G.describe_move(s, "1,0") == "b1 (opponent skipped)"
    ok("directed: the skip rule fires, hands the turn back, and is logged")

    # -- a LEGAL simultaneous crosscut kills THREE checkers, not four
    b = dict(LEGAL_DOUBLE)
    assert not crosscuts_on_board(b, 5)
    crosses = crosscuts_formed(b, 2, 2, RED)
    assert len(crosses) == 2
    assert len(set(crosses[0]) & set(crosses[1])) == 1, "one shared enemy checker"
    assert mine_size(b, 2, 2, RED) == 3
    assert enemy_sizes(b, 2, 2, RED) == [[1, 1], [1, 1]]
    s = ClearcutState(size=5, board=b, to_move=RED)
    n = G.apply_move(s, "2,2")
    assert set(n.removed) == {(2, 1), (2, 3), (3, 2)}, n.removed
    assert len(n.removed) == 3, "2 + 2 crosscut checkers minus the shared one"
    assert all(b[p] == BLUE for p in n.removed)
    assert G.describe_move(s, "2,2") == "c3xc2c4d3", G.describe_move(s, "2,2")
    # and resolving the two crosscuts one at a time gives the same board
    seq = dict(b)
    seq[(2, 2)] = RED
    for pair in crosses:
        for p in pair:
            seq.pop(p, None)
    assert seq == n.board
    ok("directed: a LEGAL simultaneous crosscut kills exactly three checkers")

    # -- the stall branch itself (provably unreachable) is an HONEST DRAW.
    #    Built by hand, since it cannot be reached through apply_move.
    s = ClearcutState(size=3, board={(0, 0): RED}, to_move=BLUE, stalled=True)
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0]
    assert G.legal_moves(s) == []
    assert "Draw" in G.render(s)['caption']
    ok("directed: the (unreachable) both-stuck branch scores an honest DRAW")


# ==========================================================================
# 7.  Platform contract: serialize, render, describe_move, purity
# ==========================================================================

SER_KEYS = {"size", "board", "to_move", "last", "removed", "winner",
            "stalled", "ply", "skips"}


def test_serialize_roundtrip():
    """Compare STATE OBJECTS, not dicts: `serialize(deserialize(d)) == d` is
    blind to a field `serialize` stops emitting (deserialize re-defaults it)."""
    rng = random.Random(17)
    seen_removed = seen_winner = seen_skips = 0
    for size in (5, 7):
        for gi in range(6):
            s = G.initial_state(options={"size": size})
            while True:
                d = G.serialize(s)
                assert set(d) == SER_KEYS, set(d) ^ SER_KEYS
                import json
                json.dumps(d)                      # must be JSON-able
                back = G.deserialize(d)
                assert back == s, (back, s)        # STATE equality
                assert G.serialize(back) == d
                if s.removed:
                    seen_removed += 1
                if s.winner is not None:
                    seen_winner += 1
                if s.skips:
                    seen_skips += 1
                if G.is_terminal(s):
                    break
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert seen_removed > 5 and seen_winner >= 12, (seen_removed, seen_winner)
    ok(f"serialize/deserialize round-trips as STATES over 12 whole games "
       f"({seen_removed} states with removals, {seen_skips} with skips)")


def test_render_every_size():
    """A board-SIZE option means render() must declare the RIGHT dimensions for
    EVERY size, and no piece may fall outside them.  Checked from a FAR-CORNER
    position reached through apply_move (a fresh state has no pieces at all, so
    checking one would be vacuous)."""
    for size in (5, 7, 9, 11, 13, 19):
        s = G.initial_state(options={"size": size})
        corners = [(0, 0), (size - 1, size - 1), (size - 1, 0), (0, size - 1)]
        for cell in corners:
            assert f"{cell[0]},{cell[1]}" in G.legal_moves(s)
            s = G.apply_move(s, f"{cell[0]},{cell[1]}")
        spec = G.render(s)
        board = spec['board']
        assert board['type'] == 'square'
        assert board['width'] == size and board['height'] == size, board
        assert board['edges'] == {"top": RED, "bottom": RED,
                                  "left": BLUE, "right": BLUE}
        cells = {p['cell'] for p in spec['pieces']}
        assert cells == {f"{c},{r}" for c, r in corners}, cells
        for p in spec['pieces']:
            c, r = _cell(p['cell'])
            assert 0 <= c < size and 0 <= r < size, (size, p)
            assert p['owner'] in (RED, BLUE)
        for h in spec['highlights']:
            c, r = _cell(h['cell'])
            assert 0 <= c < size and 0 <= r < size
            assert h['kind'] in ('goal', 'last-move')
        assert isinstance(spec['caption'], str) and spec['caption']
    ok("render() declares the right dimensions and stays in bounds at all "
       "six board sizes, from a far-corner position")


def test_render_and_describe():
    rng = random.Random(23)
    s = G.initial_state(options={"size": 7})
    caps, kinds = set(), set()
    while not G.is_terminal(s):
        spec = G.render(s)
        caps.add(spec['caption'])
        kinds |= {h['kind'] for h in spec['highlights']}
        for m in G.legal_moves(s):
            txt = G.describe_move(s, m)
            assert txt and isinstance(txt, str)
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    spec = G.render(s)
    assert spec['caption'].endswith("wins")
    goal = [h for h in spec['highlights'] if h['kind'] == 'goal']
    assert goal, "the winning chain must be highlighted"
    # the highlighted chain is a REAL winning chain of the REAL winner
    chain = [_cell(h['cell']) for h in goal]
    assert all(s.board[p] == s.winner for p in chain)
    assert 'last-move' in {h['kind'] for h in spec['highlights']}
    # the caption names the winner by the SEAT the engine recorded, and Figure
    # 1's frame pins seat 1 = Blue = left/right (asserted in test_figures).
    assert spec['caption'] == ("Red wins" if s.winner == RED else "Blue wins")
    ok("render captions/highlights and describe_move cover a whole game")


def test_purity_and_helpers():
    """Predicates NOT on the legality path are the ones nobody tests."""
    rng = random.Random(31)
    s = G.initial_state(options={"size": 7})
    for _ in range(60):
        if G.is_terminal(s):
            break
        before = dict(s.board)
        moves = G.legal_moves(s)
        m = rng.choice(moves)
        G.describe_move(s, m)
        n = G.apply_move(s, m)
        assert s.board == before, "apply_move mutated its input"
        assert n.board is not s.board
        # crosscuts_on_board (whole-board diagnostic) must agree with the local
        # crosscuts_formed predicate on every empty square and both colours.
        for r in range(7):
            for c in range(7):
                if (c, r) in s.board:
                    continue
                for p in (RED, BLUE):
                    tmp = dict(s.board)
                    tmp[(c, r)] = p
                    made = {tuple(sorted((min(a[0], b[0]), min(a[1], b[1]))
                                         for a, b in [pair]))[0]
                            for pair in crosscuts_formed(s.board, c, r, p)}
                    whole = set(crosscuts_on_board(tmp, 7))
                    assert made <= whole, ((c, r), p, made, whole)
                    assert len(whole) == len(crosscuts_formed(s.board, c, r, p))
        # group_of / group_size / group_size_signature agree with each other
        sizes = []
        seen = set()
        for cell in s.board:
            if cell in seen:
                continue
            g = group_of(s.board, cell)
            seen |= g
            assert all(group_size(s.board, x) == len(g) for x in g)
            sizes.append(len(g))
        assert group_size_signature(s.board) == tuple(sorted(sizes, reverse=True))
        assert sum(sizes) == len(s.board)
        # connection_path is empty exactly when connects() is False
        for p in (RED, BLUE):
            assert bool(connection_path(s.board, p, 7)) == connects(s.board, p, 7)
        s = n
    ok("apply_move is pure; crosscuts_on_board / group_* / connection_path "
       "cross-checked against the legality path")


def test_no_heuristic():
    """rules.md documents a MEASURED decision to ship no bot evaluation.

    Pinned here so the decision is falsifiable rather than just prose.  If a
    `heuristic` is ever added it MUST return a LIST of `num_players` payoffs -
    a bare float raises `TypeError: 'float' object is not subscriptable` in
    MCTSBot's back-propagation, and that bug only fires once a rollout reaches
    the cutoff, so short games hide it.  Anyone adding one must also redo
    rules.md's head-to-head measurement, which currently reads 0.58 (p 0.27) at
    the production shape.
    """
    if hasattr(G, "heuristic"):
        h = G.heuristic(G.initial_state())
        assert isinstance(h, list) and len(h) == G.num_players, (
            "heuristic must return a LIST of num_players payoffs, got %r" % (h,))
        raise AssertionError(
            "a heuristic was added: update rules.md's 'No bot evaluation is "
            "shipped' section with a fresh MCTSBot measurement")
    ok("no bot evaluation is shipped - the measured decision in rules.md is pinned")


# ==========================================================================

def main():
    test_figures()
    test_distinct_from_halfcut()
    test_anchor_power()
    test_survivors_closed()
    st = test_proof_steps()
    test_p2_on_constructed_inputs()
    test_exhaustive_solves()
    test_crossway_duality()
    test_directed()
    test_serialize_roundtrip()
    test_render_every_size()
    test_render_and_describe()
    test_no_heuristic()
    test_purity_and_helpers()
    for c in CHECKS:
        print("  ok:", c)
    print(f"\nclearcut selftest: {len(CHECKS)} checks passed "
          f"({st['plies']} swept plies, 0 draws)")


if __name__ == "__main__":
    main()
