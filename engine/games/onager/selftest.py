#!/usr/bin/env python3
"""Correctness anchors for Onager (Néstor Romeral Andrés, 2012 — nestorgames).

Pure stdlib: only `agp` and this package.  Run directly, or via
`tests/test_games.py::test_package_selftests`.

The anchors, in the order the rulebook establishes them:

* every figure of `ONAGER_EN.pdf` transcribed cell by cell — the walk figure,
  the four jump figures a-d, the multiple-jump figure and the endgame figure —
  asserting the figure's PREMISES (what the pieces are, why each blocked
  direction is blocked) and not merely its outcome;
* the wrong rulesets each figure CANNOT exclude, closed with constructed
  positions (the endgame figure is blind to three of them);
* the two win conditions, each reached through `apply_move` because Onager
  stores its result as an event.  The stuck loss is NEVER reached by random
  play (0 of 600 games), so these tests are its only coverage;
* the jump-chain model: the board during a chain is exactly "the original board
  with the mover's one disc relocated", which is what makes "no cell twice"
  equivalent to the sheet's "cannot end where it started" — and the minimised
  position where AbstractPlay's engine, which does NOT update the board between
  hops, offers a destination that does not exist;
* the effect invariants a `from>to` move must satisfy: discs are conserved, a
  turn touches exactly its own two cells, and every stack alternates colours;
* serialize/deserialize compared as STATES over a whole swept game;
* render bounds at every offered board size;
* the ply-cap backstop: a decisive result outranks it, and random play never
  reaches it.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                 # noqa: E402
from games.onager.game import (                                      # noqa: E402
    DIRS, LAKE, LAKES, PLY_CAP_CELL_FACTOR, SEAT_NAMES, SIZES,
    OnagerState, all_cells, back_rank, back_rank_counts, cell_id, cell_name,
    centre, has_turn, home_rows, is_adjacent, jump_landings, jump_route,
    jump_targets, move_targets, n_cells, occupancy, on_board, parse_cell,
    ply_cap, walk_targets,
)

MAN, G = load_from_dir(Path(__file__).resolve().parent)
FAILURES = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)
        print("FAIL:", msg)
    return cond


def eq(a, b, msg):
    return check(a == b, f"{msg}: {a!r} != {b!r}")


# Padding lakes for hand-built positions.  The placement phase is over exactly
# when three lakes are down, so a constructed MOVEMENT position must carry
# three; these mid-edge cells are far from every figure transcribed below.  A
# lake can only ever REMOVE moves, so if one of them ever did interfere, the
# exact move-set assertions would fail loudly rather than pass vacuously.
PAD = [(5, -1), (-5, 1), (4, 1), (-4, -1), (1, 4), (-1, -4), (3, 2), (-3, -2)]


def st(size=6, stacks=None, lakes=(), to_move=0, ply=10, pad=True, **kw):
    """A hand-built state.  Only for positions whose LEGALITY is under test;
    anything about a WIN is reached through `apply_move` instead."""
    stacks = {c: tuple(v) for c, v in (stacks or {}).items()}
    lakes = set(lakes)
    if pad:
        for c in PAD:
            if len(lakes) >= LAKES:
                break
            if on_board(size, c) and c not in stacks and c not in lakes:
                lakes.add(c)
        assert len(lakes) == LAKES, "could not pad the lakes"
    return OnagerState(size=size, stacks=stacks, lakes=frozenset(lakes),
                       to_move=to_move, ply=ply, **kw)


def targets(s, cell):
    """The set of cells the piece on `cell` can reach in one hop or one walk."""
    occ = occupancy(s.stacks, s.lakes)
    return (set(walk_targets(s.size, occ, cell)),
            set(jump_landings(s.size, occ, cell, s.stacks[cell][-1])))


def chain_ends(s, cell):
    """Every square reachable from `cell` by a jump or a chain of them."""
    seat = s.stacks[cell][-1]
    return jump_targets(s.size, s.stacks, s.lakes, cell, seat)


# =========================================================================
#  1. Board geometry — pinned to the rulebook's MATERIAL list, which is the
#     one hard NUMBER the sheet prints and the thing that fixes "your 2
#     nearest rows".
# =========================================================================

def test_geometry():
    eq(n_cells(6), 91, "hexhex side 6 has 91 cells")
    eq(len(all_cells(6)), 91, "enumerated cells")
    # "13 black discs, 13 white discs" -- the arithmetic that pins the two
    # home rows to the 6-cell back rank plus the 7-cell row in front of it.
    for size in SIZES:
        eq(len(home_rows(size, 0)), 2 * size + 1, f"size {size} home discs")
        eq(len(home_rows(size, 1)), 2 * size + 1, f"size {size} home discs")
        eq(len(back_rank(size, 0)), size, f"size {size} back rank width")
        eq(len(back_rank(size, 1)), size, f"size {size} back rank width")
        # GROUND TRUTH OUTSIDE THE ENGINE'S NAMING: a player's back rank is one
        # of his OWN starting rows, and the two back ranks are the two extreme
        # rows of the board.  Asserted structurally so it cannot bake in the
        # same colour mistake twice (the narrows lesson).
        check(set(back_rank(size, 0)) <= set(home_rows(size, 0)),
              f"size {size}: seat 0's back rank is inside its own home rows")
        check(set(back_rank(size, 1)) <= set(home_rows(size, 1)),
              f"size {size}: seat 1's back rank is inside its own home rows")
        eq({c[1] for c in back_rank(size, 0)}, {size - 1}, "seat 0 back row")
        eq({c[1] for c in back_rank(size, 1)}, {-(size - 1)}, "seat 1 back row")
        check(set(home_rows(size, 0)) & set(home_rows(size, 1)) == set(),
              f"size {size}: the two armies do not overlap")
    eq(len(home_rows(6, 0)), 13, "13 black discs (rulebook MATERIAL list)")

    # 13+13 discs + 3 lakes is what a legal setup needs room for.
    eq(LAKES, 3, "three lakes")
    eq(centre(6), (0, 0), "the centre space")

    # SEAT COLOURS, PINNED TO GROUND TRUTH OUTSIDE THE ENGINE.  Every other
    # caption assertion in this file is written against SEAT_NAMES itself, so
    # they all survive a swap of the two names -- and a swapped pair makes the
    # board announce the WRONG COLOUR AS WINNER.  The rulebook's setup figure
    # prints the BLACK discs filling the two BOTTOM rows, and its endgame
    # caption says "Black's back rank (bottom)".  `Board.jsx` draws a hex board
    # at y = 1.5*r, so r grows DOWNWARDS and r = size-1 is the bottom row.
    eq(SEAT_NAMES[0], "Black", "seat 0 is Black (setup figure: black fills the "
       "two bottom rows)")
    eq(SEAT_NAMES[1], "White", "seat 1 is White (setup figure: white fills the "
       "two top rows)")
    eq({c[1] for c in back_rank(6, 0)}, {5},
       "and Black's back rank is the BOTTOM row (largest r), as the endgame "
       "figure's caption states")

    # Pointy-top geometry: a row is horizontal, so E and W are neighbours and
    # there is NO vertical neighbour.  This is what every rulebook figure draws
    # (the walk figure marks W and E arrows on one piece).
    check((1, 0) in DIRS and (-1, 0) in DIRS, "E/W are neighbours")
    check(all((0, 2 * d) not in DIRS for d in (-1, 1)), "no vertical neighbour")
    eq(len(DIRS), 6, "six directions")
    eq(len({(-a, -b) for a, b in DIRS} ^ set(DIRS)), 0, "directions come in "
       "opposite pairs, so the '3 alignment directions' of the sheet are the "
       "3 axes")

    # Printed-board naming: Black's back rank is row 'a', White's is row 'k'
    # (11 rows), matching AbstractPlay's HexTriGraph.
    eq(cell_name(6, (-5, 5)), "a1", "bottom-left corner")
    eq(cell_name(6, (0, 5)), "a6", "bottom-right corner")
    eq(cell_name(6, (0, -5)), "k1", "top-left corner")
    eq(cell_name(6, (5, -5)), "k6", "top-right corner")
    eq(cell_name(6, (0, 0)), "f6", "centre")


def test_initial_position():
    s = G.initial_state()
    eq(len(s.stacks), 26, "26 discs on the board at setup")
    eq(sum(1 for v in s.stacks.values() if v == (0,)), 13, "13 black")
    eq(sum(1 for v in s.stacks.values() if v == (1,)), 13, "13 white")
    eq(s.lakes, frozenset(), "no lakes yet")
    eq(s.to_move, 0, "Black starts (the sheet's HOW TO PLAY)")
    # Every disc is a lone disc on its own player's two nearest rows.
    for cell, stack in s.stacks.items():
        eq(len(stack), 1, f"{cell_name(6, cell)} is a lone disc")
        check(cell in home_rows(6, stack[0]), f"{cell_name(6, cell)} at home")
    # The centre is empty and the placement phase offers every other empty cell.
    moves = set(G.legal_moves(s))
    eq(len(moves), 91 - 26 - 1, "placement targets = empty cells minus centre")
    check(cell_id(centre(6)) not in moves, "the centre may not take a lake")


def test_placement_phase():
    """Three lakes, alternating, Black first -- so Black places two and White
    one, and WHITE makes the first walk-or-jump (interpretive decision 1)."""
    s = G.initial_state()
    seats = []
    picks = ["-5,0", "5,0", "0,-1"]
    for m in picks:
        seats.append(s.to_move)
        check(m in G.legal_moves(s), f"{m} is a legal lake square")
        s = G.apply_move(s, m)
    eq(seats, [0, 1, 0], "lakes placed Black, White, Black")
    eq(len(s.lakes), 3, "three lakes down")
    eq(s.to_move, 1, "White makes the first movement move")
    check(not G.in_placement(s), "placement phase over")
    # No fourth lake, and every move is now a cell path.
    check(all(">" in m for m in G.legal_moves(s)), "movement moves only")
    # A lake may never be placed on the centre or on an occupied cell.
    s2 = G.initial_state()
    for bad in (cell_id(centre(6)), "-5,5"):
        try:
            G.apply_move(s2, bad)
            check(False, f"lake on {bad} should be rejected")
        except ValueError:
            pass


# =========================================================================
#  2. The rulebook figures, transcribed cell by cell.
# =========================================================================

def test_figure_walks():
    """Page 1, 'Examples of valid walks for Black'.

    Two black pieces, each with exactly three arrows.  The figure's PREMISES —
    not just its outcome — are that one of the black pieces is the TOP OF A
    STACK (the caption says so in as many words) and that each blocked
    direction is blocked by a specific thing: a lake, an enemy disc, or an
    enemy-topped stack.  Coordinates are the figure's own hex lattice, with the
    left-hand black piece at the origin and the board's origin shifted so the
    whole picture fits on the real 91-cell board.
    """
    o = (-2, 0)                       # where the figure's origin lands

    def c(dq, dr):
        return (o[0] + dq, o[1] + dr)

    stacks = {
        c(0, 0): (0,),                # left black piece, a lone disc
        c(1, -1): (1,),               # NE  -- white disc
        c(-1, 1): (0, 1),             # SW  -- white ON black (white on top)
        c(3, 0): (1, 0),              # right black piece: black ON white
        c(3, -1): (1,),               # its NW -- white disc
        c(4, -1): (0, 1),             # its NE -- white on black
    }
    lakes = {c(-1, 0), c(3, 1), c(3, -2)}
    s = st(stacks=stacks, lakes=lakes, to_move=0)

    # ---- premises -------------------------------------------------------
    eq(s.stacks[c(-1, 1)][-1], 1, "the SW stack is WHITE-topped, so it blocks")
    eq(s.stacks[c(-1, 1)][0], 0, "and a black disc is buried under it")
    eq(s.stacks[c(3, 0)][-1], 0, "the right piece is the BLACK top of a stack")
    eq(s.stacks[c(3, 0)][0], 1, "with a white disc buried under it")
    check(c(-1, 0) in s.lakes and c(3, 1) in s.lakes, "the two blocking lakes")

    # ---- the figure's three arrows, twice -------------------------------
    walks, jumps = targets(s, c(0, 0))
    eq(walks, {c(0, -1), c(1, 0), c(0, 1)},
       "left black piece walks NW, E, SE only")
    # The caption promises only WALKS, and the figure draws only walk arrows --
    # but the two black pieces really are aligned three apart with empty cells
    # between them, so the position also admits the mirror jump each way.
    # Asserting the exact set keeps the transcription honest instead of
    # asserting a convenient "no jumps".
    eq(jumps, {c(6, 0)}, "the left piece may also jump over the right one")

    walks, jumps = targets(s, c(3, 0))
    eq(walks, {c(2, 0), c(4, 0), c(2, 1)},
       "right black piece (a stack top) walks W, E, SW only")
    eq(jumps, {c(-3, 0)}, "and jump back over the left one -- the mirror")

    # ---- why each blocked direction is blocked --------------------------
    occ = occupancy(s.stacks, s.lakes)
    eq(occ[c(-1, 0)], LAKE, "W of the left piece is a lake")
    eq(occ[c(1, -1)], 1, "NE of the left piece is an enemy disc")
    eq(occ[c(-1, 1)], 1, "SW of the left piece is an enemy-TOPPED stack")
    eq(occ[c(3, -1)], 1, "NW of the right piece is an enemy disc")
    eq(occ[c(4, -1)], 1, "NE of the right piece is an enemy-topped stack")
    eq(occ[c(3, 1)], LAKE, "SE of the right piece is a lake")

    # ---- only the TOP disc moves: the buried black disc under c(-1,1) is
    #      not a piece, so Black cannot move from that cell at all.
    movers = {cell for cell, v in s.stacks.items() if v[-1] == 0}
    check(c(-1, 1) not in movers,
          "the buried black disc is not a piece and cannot move")
    eq(movers, {c(0, 0), c(3, 0)}, "Black has exactly the two figure pieces")


def _row_case(pieces, lakes=(), jumper_q=-3):
    """Lay out one of the jump figures along the board's widest row (r = 0,
    q = -5..5) with the jumper at q = -3, so offsets 0..6 all fit."""
    stacks = {(jumper_q + dq, 0): tuple(v) for dq, v in pieces.items()}
    lk = {(jumper_q + dq, 0) for dq in lakes}
    return st(stacks=stacks, lakes=lk, to_move=1), (jumper_q, 0)


def test_figure_jumps():
    """Page 2, 'Examples of legal and illegal jumps' (a-d).  All four rows are
    White to move, laid out along one row of the board."""
    o = -3

    def at(dq):
        return (o + dq, 0)

    # (a) Legal: landing space is empty.  Same distance.
    #     A plain white disc jumps its neighbour, which is a WHITE-TOPPED
    #     STACK -- so a stack top is a legal piece to jump OVER.
    s, j = _row_case({0: (1,), 1: (0, 1)})
    eq(s.stacks[at(1)][-1], 1, "(a) premise: the jumped-over piece is white")
    eq(s.stacks[at(1)][0], 0, "(a) premise: with a black disc buried under it")
    _, jumps = targets(s, j)
    eq(jumps, {at(2)}, "(a) the one legal jump lands 2 away, on an empty cell")

    # (b) Legal: the cells between jumper and jumped-over piece are empty; same
    #     distance; the destination is an enemy piece -- and a LAKE sits
    #     between the jumped-over piece and the landing square, which the sheet
    #     says explicitly does not matter.
    s, j = _row_case({0: (0, 1), 2: (1,), 4: (1, 0)}, lakes=(3,))
    eq(s.stacks[j][-1], 1, "(b) premise: the JUMPER is a white stack top")
    eq(s.stacks[at(4)][-1], 0, "(b) premise: the landing holds an enemy piece")
    check(at(3) in s.lakes, "(b) premise: a lake sits between them")
    _, jumps = targets(s, j)
    eq(jumps, {at(4)}, "(b) distance 2 partner -> landing 4 away, onto the enemy")

    # (c) Illegal: an obstacle between the jumping and jumped-over pieces.
    s, j = _row_case({0: (0, 1), 3: (1,)}, lakes=(1,))
    check(at(1) in s.lakes, "(c) premise: the obstacle is the circled lake")
    eq(s.stacks[at(3)][-1], 1, "(c) premise: the far piece IS friendly")
    _, jumps = targets(s, j)
    eq(jumps, set(), "(c) no jump: the first thing in the ray is the lake")
    check(at(6) not in jumps, "(c) the illustrated landing is illegal")

    # (d) Illegal: not the same distance.  The friendly piece is 3 away, so the
    #     only legal landing is 6 away -- never the illustrated 5.
    s, j = _row_case({0: (0, 1), 3: (1,)})
    _, jumps = targets(s, j)
    eq(jumps, {at(6)}, "(d) the mirror landing is exactly 2x the distance")
    check(at(5) not in jumps, "(d) the illustrated landing is illegal")

    # ---- what figures a-d CANNOT exclude, closed here --------------------
    # They never show a landing on a lake or on a friendly piece (the prose
    # forbids both), and they are all horizontal, so they say nothing about
    # the other two axes.
    s, j = _row_case({0: (1,), 1: (1,)}, lakes=(2,))
    _, jumps = targets(s, j)
    eq(jumps, set(), "a landing square holding a lake is illegal")
    s, j = _row_case({0: (1,), 1: (1,), 2: (1,)})
    _, jumps = targets(s, j)
    eq(jumps, set(), "a landing square holding a FRIENDLY piece is illegal")
    for dq, dr in DIRS:
        stacks = {(0, 0): (1,), (dq, dr): (1,)}
        s = st(stacks=stacks, to_move=1)
        _, jumps = targets(s, (0, 0))
        eq(jumps, {(2 * dq, 2 * dr)},
           f"jumps work in direction {(dq, dr)} too, not only along a row")


def test_figure_multiple_jumps():
    """Page 2, 'Example of multiple jumps': the row-b position, whose first hop
    lands on an enemy piece, followed by a second hop SE over an adjacent
    friendly piece.  The continuation exists ONLY because the first landing was
    on an enemy piece."""
    o = -3

    def at(dq, dr=0):
        return (o + dq, dr)

    stacks = {at(0): (0, 1), at(2): (1,), at(4): (1, 0),
              at(4, 1): (1,)}
    s = st(stacks=stacks, lakes={at(3)}, to_move=1)
    ends = chain_ends(s, at(0))
    check(at(4, 2) in ends, "the figure's two-hop chain reaches its landing")
    check(at(4) in ends,
          "stopping after one hop is legal too -- continuation is optional")
    eq(jump_route(6, s.stacks, s.lakes, at(0), at(4, 2), 1),
       (at(0), at(4), at(4, 2)), "and the route is the one the figure draws")
    eq(G.describe_move(s, f"{cell_id(at(0))}>{cell_id(at(4, 2))}"),
       "^".join(cell_name(6, c) for c in (at(0), at(4), at(4, 2))),
       "the move log reconstructs the figure's two hops")

    # PREMISE: had the first landing been EMPTY, no continuation would exist.
    stacks2 = dict(stacks)
    del stacks2[at(4)]
    s2 = st(stacks=stacks2, lakes={at(3)}, to_move=1)
    eq(chain_ends(s2, at(0)), {at(4)},
       "landing on an EMPTY square ends the turn -- no second hop")


def _endgame_state(bottom, top, extra=None, to_move=0):
    """Build the endgame figure's two back ranks.  `bottom`/`top` are lists of
    six entries (None or a stack tuple), left to right as printed."""
    stacks = dict(extra or {})
    for i, v in enumerate(bottom):
        if v is not None:
            stacks[(-5 + i, 5)] = v
    for i, v in enumerate(top):
        if v is not None:
            stacks[(i, -5)] = v
    return st(stacks=stacks, to_move=to_move)


def test_figure_endgame():
    """Page 2, 'Endgame example'.  White's turn; White wins 2 to 1.

    Bottom row (Black's back rank), left to right: white disc, empty,
    WHITE-ON-BLACK STACK, black disc, empty, black disc.
    Top row (White's back rank): white, white, empty, BLACK, empty, empty.
    So White's two counted pieces include one that is only the TOP of a stack,
    which is what pins "remember the definition of 'piece'".
    """
    bottom = [(1,), None, (0, 1), (0,), None, (0,)]
    top = [(1,), (1,), None, (0,), None, None]
    # A spare black piece with a harmless move somewhere in the middle, so the
    # win can be REACHED through apply_move (Onager stores wins as an event).
    extra = {(0, 2): (0,)}
    s = _endgame_state(bottom, top, extra, to_move=0)

    # ---- premises the figure relies on ----------------------------------
    eq(s.stacks[(-3, 5)], (0, 1), "the stack on Black's back rank is white on black")
    check((-3, 5) in back_rank(6, 0), "and it stands on BLACK's back rank")
    check((3, -5) in back_rank(6, 1), "the lone black piece is on WHITE's back rank")
    eq(back_rank_counts(6, s.stacks), (1, 2),
       "counts: Black 1 on White's rank, White 2 on Black's rank")

    # ---- Black moves; at the start of White's turn White wins 2-1 --------
    s2 = G.apply_move(s, "0,2>0,1")
    eq(s2.to_move, 1, "White to move")
    eq(s2.winner, 1, "White wins -- 2 pieces to 1 (the figure's caption)")
    eq(G.returns(s2), [-1.0, 1.0], "and the payoff says so")
    check("wins" in G.render(s2)["caption"], "caption announces the win")
    check(SEAT_NAMES[1] in G.render(s2)["caption"].split(" wins")[0],
          "and names WHITE as the winner, matching the figure's caption")

    # ---- variants the figure KILLS --------------------------------------
    # (i) "only isolated discs count": the stack would not count -> 1:1.
    b2 = list(bottom)
    b2[2] = None
    alt = _endgame_state(b2, top, extra, to_move=0)
    eq(back_rank_counts(6, alt.stacks), (1, 1), "without the stack it is 1:1")
    eq(G.apply_move(alt, "0,2>0,1").winner, None,
       "a 1:1 TIE is not a win for anybody -- the game simply goes on")
    # (ii) "a stack counts for the colour of its BOTTOM disc".
    b3 = list(bottom)
    b3[2] = (1, 0)                       # black on white instead
    alt = _endgame_state(b3, top, extra, to_move=0)
    eq(back_rank_counts(6, alt.stacks), (1, 1),
       "a BLACK-topped stack there does not count for White")

    # ---- variants the figure is BLIND to, closed with constructed cases --
    # (iii) "every disc in a stack counts for its owner".  The figure cannot
    #       see this: its buried disc is black and sits on BLACK's own back
    #       rank, where it would not be counted either way.  So put a WHITE
    #       disc under a BLACK top on WHITE's back rank.
    t4 = list(top)
    t4[4] = (1, 0)                       # black on white, on White's back rank
    alt = _endgame_state(bottom, t4, extra, to_move=0)
    eq(back_rank_counts(6, alt.stacks), (2, 2),
       "the buried WHITE disc does not count for White")
    # (iv) ">=" instead of ">": a tie must NOT win.  (Covered by (i) above and
    #      again here from the other seat.)
    alt = _endgame_state([(1,), None, None, (0,), None, (0,)],
                         [(1,), (1,), None, (0,), None, None], extra, to_move=0)
    eq(back_rank_counts(6, alt.stacks), (1, 1), "1:1")
    eq(G.apply_move(alt, "0,2>0,1").winner, None, "a tie is not a win")
    # (v) the check happens BEFORE you move, not after: a player who creates
    #     the lead on his own move does NOT win at once, and the opponent gets
    #     a turn to answer it.
    s = st(stacks={(0, -5): (0,), (0, -4): (0,), (3, -5): (1,),
                   (-5, 5): (1,), (-4, 5): (0,), (0, 3): (1,)},
           to_move=1, ply=20)
    eq(back_rank_counts(6, s.stacks), (1, 1), "level before the move")
    s2 = G.apply_move(s, "3,-5>2,-5")     # White vacates Black's counted cell
    eq(back_rank_counts(6, s2.stacks), (1, 1), "still level after it")
    eq(s2.winner, None, "nobody has won")


# =========================================================================
#  3. The two win conditions, reached through apply_move.
# =========================================================================

def test_back_rank_win_both_seats():
    for seat in (0, 1):
        other = 1 - seat
        goal = back_rank(6, other)[0]
        # `seat` already stands on one goal cell; `other` stands on none.
        stacks = {goal: (seat,), (0, 1 if seat == 0 else -1): (other,),
                  (0, 2 if seat == 0 else -2): (other,)}
        s = st(stacks=stacks, to_move=other, ply=30)
        mv = [m for m in G.legal_moves(s) if m.startswith(cell_id((0, 2 if seat == 0 else -2)))][0]
        s2 = G.apply_move(s, mv)
        eq(s2.to_move, seat, "the seat with the lead is to move")
        eq(s2.winner, seat, f"seat {seat} ({SEAT_NAMES[seat]}) wins on the back rank")
        ret = G.returns(s2)
        eq(ret[seat], 1.0, "winner gets +1")
        eq(ret[other], -1.0, "loser gets -1")
        eq(G.legal_moves(s2), [], "no moves after the game ends")
        check(G.is_terminal(s2), "terminal")


def test_stuck_loss():
    """"If the above condition is not reached and you can't make a legal
    movement at the start of your turn, you lose."

    RANDOM PLAY NEVER REACHES THIS (0 of 600 games at size 6), so this test is
    its only coverage.  The position is reached through `apply_move`, because
    `is_terminal` is False on a hand-built stuck state.
    """
    # White owns exactly one piece, the top of a stack wedged into the corner
    # (5,-5); the corner has exactly three on-board neighbours and all three
    # are lakes, so White has no walk, and with only one piece White can have
    # no jump partner either.
    stacks = {(5, -5): (0, 1), (-5, 5): (0,), (-4, 5): (0,), (-3, 4): (0,)}
    lakes = {(4, -5), (5, -4), (4, -4)}
    eq(sorted(c for c in [(5 + dq, -5 + dr) for dq, dr in DIRS]
              if on_board(6, c)), sorted(lakes),
       "PREMISE: the corner's on-board neighbours are exactly the three lakes")
    s = st(stacks=stacks, lakes=lakes, to_move=0, ply=40, pad=False)
    eq(back_rank_counts(6, s.stacks), (0, 0), "neither side has a lead")
    check(not has_turn(6, s.stacks, s.lakes, 1), "White is already stuck")
    check(has_turn(6, s.stacks, s.lakes, 0), "Black is not")
    s2 = G.apply_move(s, "-3,4>-3,3")
    eq(s2.to_move, 1, "White to move")
    eq(s2.winner, 0, "White has no legal movement and loses")
    eq(G.returns(s2), [1.0, -1.0], "payoff")

    # PREMISE of the same position: the stuck piece really is White's ONLY
    # piece, and it is a stack TOP (the buried black disc is not a piece).
    eq([c for c, v in stacks.items() if v[-1] == 1], [(5, -5)], "one white piece")
    eq(stacks[(5, -5)][0], 0, "with a black disc buried under it")

    # ORDERING: the back-rank win OUTRANKS the stuck loss.  Same position, but
    # now White also has a piece on Black's back rank -- itself walled in by
    # black discs -- so White WINS instead of losing, which is the sheet's "if
    # the above condition is NOT reached and you can't move ... you lose".
    stacks2 = dict(stacks)
    stacks2[(-2, 5)] = (1,)
    for c in ((-1, 5), (-3, 5), (-1, 4), (-2, 4)):
        stacks2[c] = (0,)
    s = st(stacks=stacks2, lakes=lakes, to_move=0, ply=40, pad=False)
    check(not has_turn(6, s.stacks, s.lakes, 1), "White still has no move")
    eq(back_rank_counts(6, s.stacks), (0, 1), "but White leads on the back ranks")
    s2 = G.apply_move(s, "-3,4>-3,3")
    eq(s2.winner, 1, "White WINS on the back rank despite having no move")

    # THE CAPTION MUST NAME THE RULE THAT ACTUALLY ENDED THE GAME.  A stuck loss
    # where the WINNER already holds a cell of the loser's back rank (without
    # leading on the count) is the case a `highlights`-based guess gets wrong:
    # it reads as a back-rank victory, and 0-to-1 is not a winning count on the
    # loser's own turn.  `_score` records the reason exactly -- the back-rank
    # rule awards the win to the player TO MOVE, the stuck rule to his opponent.
    stacks3 = dict(stacks2)                  # White walled in on Black's rank
    stacks3[(3, -5)] = (0,)                  # ...and Black on White's, so 1:1
    s = st(stacks=stacks3, lakes=lakes, to_move=0, ply=40, pad=False)
    eq(back_rank_counts(6, s.stacks), (1, 1), "the back ranks are LEVEL")
    check(not has_turn(6, s.stacks, s.lakes, 1), "White is stuck")
    s2 = G.apply_move(s, "-3,4>-3,3")
    eq(s2.winner, 0, "so Black wins by the no-legal-move rule, not on count")
    cap = G.render(s2)["caption"]
    check("no legal move" in cap,
          f"the caption must say WHY Black won, not imply a count win: {cap!r}")
    check(any(h["kind"] == "goal" for h in G.render(s2)["highlights"]),
          "PREMISE: the winner does hold a goal cell here, which is exactly "
          "what a highlights-based caption would misread")


# =========================================================================
#  4. The jump-chain model and the 2018 "cannot end where it started" clause.
# =========================================================================

def test_chain_board_model():
    """The board during a chain is exactly "the original board with the
    mover's one disc relocated" -- every intermediate square reverts when the
    disc leaves it.  Checked against a live re-implementation, and used to
    prove the no-revisit rule equivalent to the sheet's clause."""
    rng = random.Random(20120623)
    positions = 0
    for _ in range(30):
        s = G.initial_state()
        for _ in range(rng.randrange(20, 70)):
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        if G.is_terminal(s):
            continue
        seat = s.to_move
        for cell in sorted(c for c, v in s.stacks.items() if v[-1] == seat):
            positions += 1
            ours = chain_ends(s, cell)
            # Independent model: a chain is a walk on cells; the board when the
            # disc sits on `cur` is `base` (original minus the disc at `cell`)
            # plus the disc on `cur`.  Revisits ALLOWED, bounded depth.
            base = {c: list(v) for c, v in s.stacks.items()}
            base[cell].pop()
            if not base[cell]:
                del base[cell]
            reach = set()
            seen = set()
            stack = [(cell, 0)]
            while stack:
                cur, depth = stack.pop()
                if (cur, depth) in seen or depth > 4:
                    continue
                seen.add((cur, depth))
                work = {c: list(v) for c, v in base.items()}
                work.setdefault(cur, []).append(seat)
                occ = occupancy(work, s.lakes)
                for land in jump_landings(s.size, occ, cur, seat):
                    if land == cell:
                        continue          # the sheet's clause, applied at the END
                    reach.add(land)
                    if occ.get(land) == 1 - seat:
                        stack.append((land, depth + 1))
            check(ours <= reach,
                  f"{cell_name(6, cell)}: our chain ends are reachable")
            check(reach <= ours,
                  f"{cell_name(6, cell)}: no reachable end cell is lost "
                  f"({sorted(reach - ours)})")
    check(positions > 300, f"only {positions} chain origins swept")


def test_cannot_end_where_it_started():
    """The 2018 English/Japanese sheets add "Your jumping piece cannot end the
    turn in the same space where it started"; the 2012 Spanish sheet has no
    such sentence.  The clause is NOT vacuous: a jumper that was a stack top
    leaves an ENEMY disc behind, so its own start square is a legal landing
    square under the base rules.
    """
    # White's piece sits on top of a black disc at (0,0).  A white partner at
    # (2,0) lets it jump to (4,0) onto a black piece; from (4,0) the partner at
    # (2,0) would send it straight back to (0,0), which now holds the liberated
    # BLACK disc -- a legal landing square by the base rules.
    stacks = {(0, 0): (0, 1), (2, 0): (1,), (4, 0): (0,)}
    s = st(stacks=stacks, lakes={(-4, 0)}, to_move=1, ply=30)
    occ = occupancy(s.stacks, s.lakes)
    eq(jump_landings(6, occ, (0, 0), 1), [(4, 0)], "the outward jump")
    # Base-rules check on the return hop, with the disc genuinely moved:
    mid = {(0, 0): (0,), (2, 0): (1,), (4, 0): (0, 1)}
    occ2 = occupancy(mid, frozenset({(-4, 0)}))
    check((0, 0) in jump_landings(6, occ2, (4, 0), 1),
          "PREMISE: the start square really is a legal landing square")
    eq(occ2[(0, 0)], 0, "because the liberated disc there is an ENEMY disc")
    # ...and yet no legal move ends there.
    ends = chain_ends(s, (0, 0))
    check((0, 0) not in ends, "no jump chain ends on its own starting square")
    check(bool(ends), "PREMISE: this position really does offer jumps at all")
    check((0, 0) not in move_targets(6, s.stacks, s.lakes, (0, 0), 1),
          "and the square is not a walk target either")
    moves = set(G.legal_moves(s))
    check("0,0>4,0" in moves, "the outward jump is legal")
    check("0,0>0,0" not in moves, "a turn that goes nowhere is not")
    for bad in ("0,0>0,0", "0,0>4,0>0,0"):
        try:
            G.apply_move(s, bad)
            check(False, f"apply_move must reject {bad}")
        except ValueError:
            pass


def test_move_legality_rejections():
    stacks = {(0, 0): (1,), (2, 0): (1,), (-1, 0): (0,)}
    s = st(stacks=stacks, lakes={(0, 1)}, to_move=1, ply=30)
    bad = [
        ("-1,0>-1,1", "moving the opponent's disc"),
        ("0,0>0,1", "walking onto a lake"),
        ("0,0>2,0", "walking onto a friendly piece"),
        ("0,0>3,0", "a jump to a non-mirror square"),
        ("0,0>6,0", "a landing off the board"),
        ("9,9", "a cell that is not on the board"),
    ]
    for mv, why in bad:
        try:
            G.apply_move(s, mv)
            check(False, f"should reject: {why} ({mv})")
        except (ValueError, KeyError):
            pass
    check("0,0>4,0" in G.legal_moves(s), "the real jump is offered")
    check("0,0>-1,-1" not in G.legal_moves(s), "no diagonal that is not a "
          "hex direction")
    # Every legal move is `from>to` with exactly two cells, `to` reachable and
    # different from `from`.
    for m in G.legal_moves(s):
        cells = [parse_cell(p) for p in m.split(">")]
        eq(len(cells), 2, f"{m} names exactly a source and a destination")
        check(cells[0] != cells[1], "a turn never ends where it started")
        seat = s.stacks[cells[0]][-1]
        eq(seat, s.to_move, "you may only move your own piece")
        check(cells[1] in move_targets(6, s.stacks, s.lakes, cells[0], seat),
              f"{m} is reachable")


def test_start_square_is_vacated_for_later_hops():
    """A chain's SECOND and later hops see the board with the mover's disc
    ALREADY GONE from its starting square.  The piece is somewhere else, so it
    can no longer be the friendly piece jumped over, and its old square is empty
    (or shows the enemy disc it liberated).

    This is the one rule where AbstractPlay's `onager.ts` differs from this
    package: it generates whole chains against the UN-UPDATED board.  Every one
    of the 13 differential mismatches found over 2,641 positions was this, and
    each was adjudicated the same way -- the oracle's final hop needed a
    friendly piece standing on the mover's own vacated start square.  The
    position below is one of them, minimised.
    """
    # White's lone disc on h6 = (2,-2).  Chain: (2,-2) -> (0,0) -> (0,-2), each
    # hop landing on a black piece.  From (0,-2) the ray EAST is now empty all
    # the way off the board -- but the oracle still sees White on (2,-2) two
    # cells away and offers a landing on (4,-2).
    stacks = {
        (2, -2): (1,),        # the mover, a LONE disc: its square empties
        (1, -1): (1,),        # partner for hop 1
        (0, 0): (1, 0),       # hop-1 landing: a black-TOPPED stack
        (0, -1): (1,),        # partner for hop 2
        (0, -2): (0,),        # hop-2 landing: a black disc
    }
    s = st(stacks=stacks, to_move=1, ply=30)
    ends = chain_ends(s, (2, -2))
    check((0, 0) in ends, "hop 1 lands on the enemy stack")
    check((0, -2) in ends, "hop 2 continues from it")
    check((4, -2) not in ends,
          "the third hop must NOT use the mover's own vacated start square")
    eq(jump_route(6, s.stacks, s.lakes, (2, -2), (0, -2), 1),
       ((2, -2), (0, 0), (0, -2)), "the two-hop route is the expected one")

    # PREMISE -- and the proof that the assertion above is not vacuous: put a
    # DIFFERENT white piece on (2,-2) as well, so the square is genuinely
    # occupied when the third hop is tried, and the jump to (4,-2) IS legal.
    mid = {(0, 0): (1,), (0, -1): (1,), (1, -1): (1,),
           (2, -2): (1,), (0, -2): (0, 1)}
    occ = occupancy(mid, frozenset())
    check((4, -2) in jump_landings(6, occ, (0, -2), 1),
          "PREMISE: with a real white piece on (2,-2) the jump exists, so the "
          "only reason it is illegal above is that the mover had left")


def test_move_effect_invariants():
    """Every turn is the SAME operation -- one disc leaves `from` and lands on
    `to` -- so a whole game must conserve the discs and touch exactly two cells
    per move.  Also checks a ruleset invariant nothing else covers: a stack can
    only be built by landing on an ENEMY piece, so its colours always
    alternate."""
    rng = random.Random(29)
    for size in SIZES:
        discs = 2 * size + 1
        for _ in range(3):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                before, prev_lakes = s.stacks, s.lakes
                m = rng.choice(G.legal_moves(s))
                s = G.apply_move(s, m)
                for seat in (0, 1):
                    eq(sum(v.count(seat) for v in s.stacks.values()), discs,
                       f"size {size}: seat {seat} lost or gained a disc on {m}")
                if ">" in m:
                    eq(s.lakes, prev_lakes, "a turn never moves a lake")
                    changed = {c for c in set(before) | set(s.stacks)
                               if before.get(c) != s.stacks.get(c)}
                    eq(changed, set(s.last),
                       f"{m} changed cells other than its own from/to")
                    frm, to = s.last
                    eq(len(before[frm]) - len(s.stacks.get(frm, ())), 1,
                       "exactly one disc leaves the source")
                    eq(len(s.stacks[to]) - len(before.get(to, ())), 1,
                       "and exactly one arrives at the destination")
                    eq(s.stacks[to][-1], 1 - s.to_move, "the mover is on top")
                else:
                    eq(len(s.lakes), len(prev_lakes) + 1, "a lake went down")
                for cell, stack in s.stacks.items():
                    for a, b in zip(stack, stack[1:]):
                        eq(b, 1 - a, f"stack at {cell_name(size, cell)} must "
                           f"alternate colours: {stack}")


# =========================================================================
#  5. Platform contracts: serialize, render, terminate.
# =========================================================================

KEYS = {"size", "stacks", "lakes", "to_move", "winner", "capped", "ply", "last"}


def test_serialize_roundtrip():
    """Compared as STATES, not as dicts: `deserialize(serialize(s)) == s`.  The
    dict-equality form cannot see a dropped field, because `deserialize` would
    simply re-default it and `serialize` re-omit it.  Swept over whole games so
    every shape of every field is covered (lakes empty and full, stacks of
    height 1..n, a set winner, a non-empty `last` of both a placement and a
    long chain)."""
    rng = random.Random(7)
    shapes = {"lake0": 0, "lakes3": 0, "stack2": 0, "stack3": 0, "winner": 0,
              "jump": 0, "walk": 0, "placement": 0}
    for size in SIZES:
        for _ in range(3):
            s = G.initial_state({"size": size})
            while True:
                d = G.serialize(s)
                eq(set(d), KEYS, "exact serialized key set")
                import json
                json.dumps(d)                       # JSON-able
                back = G.deserialize(d)
                eq(back, s, f"state round-trip at ply {s.ply}")
                eq(G.serialize(back), d, "and the dict round-trips too")
                shapes["lake0"] += (len(s.lakes) == 0)
                shapes["lakes3"] += (len(s.lakes) == 3)
                shapes["stack2"] += any(len(v) > 1 for v in s.stacks.values())
                shapes["stack3"] += any(len(v) > 2 for v in s.stacks.values())
                shapes["winner"] += (s.winner is not None)
                shapes["jump"] += (len(s.last) == 2
                                   and not is_adjacent(*s.last))
                shapes["walk"] += (len(s.last) == 2 and is_adjacent(*s.last))
                shapes["placement"] += (len(s.last) == 1)
                if G.is_terminal(s):
                    break
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    for k, v in shapes.items():
        check(v > 0, f"round-trip sweep never covered the '{k}' shape")

    # A dropped field must be caught: this is the mutation the vacuous form of
    # the test cannot see.
    s = G.initial_state()
    s = G.apply_move(s, "-5,0")
    d = G.serialize(s)
    d2 = dict(d)
    d2.pop("lakes")
    try:
        G.deserialize(d2)
        check(False, "deserialize must not silently default a missing field")
    except KeyError:
        pass


def test_render_every_size():
    """`Board.jsx` builds its clickable cell set from the DECLARED board, and
    silently DROPS any piece outside it.  Assert the declared dimensions and
    every emitted cell id, at every offered size, from positions reached
    through `apply_move` (a fresh state proves nothing about a render that
    hard-codes the default size only when pieces have moved)."""
    rng = random.Random(11)
    for size in SIZES:
        s = G.initial_state({"size": size})
        far = set()
        for _ in range(160):
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        spec = G.render(s)
        b = spec["board"]
        eq(b["type"], "hex", "hex board")
        eq(b["shape"], "hexagon", "hexhex")
        eq(b["size"], size, f"declared size at option {size}")
        ids = ([p["cell"] for p in spec["pieces"]]
               + [h["cell"] for h in spec["highlights"]]
               + list(b["tints"]))
        for cid in ids:
            c = parse_cell(cid)
            check(on_board(size, c),
                  f"size {size}: rendered cell {cid} is outside the board")
            far.add(abs(c[0]) + abs(c[1]) + abs(c[0] + c[1]))
        eq(max(far), 2 * (size - 1),
           f"size {size}: the render reaches the board's extreme ring")
        eq(len(b["tints"]), 2 * size, "both back ranks are tinted")
        # A stack must be emitted with its full tower, top-owner last.
        for p in spec["pieces"]:
            if "stack" in p:
                eq(p["owner"], p["stack"][-1], "piece owner is the stack top")
                check(len(p["stack"]) > 1, "a lone disc emits no stack")
            elif p["owner"] == 2:
                check("fill" in p, "a lake carries its own neutral colour")
        check(any(p["owner"] == 2 for p in spec["pieces"]),
              f"size {size}: the three lakes are rendered")


def test_render_captions_and_moves():
    s = G.initial_state()
    cap = G.render(s)["caption"]
    check(cap.startswith(SEAT_NAMES[0]), "Black places the first lake")
    check("lake" in cap, "the placement phase says so")
    eq(G.describe_move(s, "-5,0"), "lake f1", "placement notation")
    s = G.apply_move(s, "-5,0")
    check(G.render(s)["caption"].startswith(SEAT_NAMES[1]), "White is next")
    for m in ("5,0", "0,-1"):
        s = G.apply_move(s, m)
    # Movement notation.
    stacks = {(0, 0): (1,), (2, 0): (1,), (1, 1): (0,)}
    s2 = st(stacks=stacks, to_move=1, ply=30)
    eq(G.describe_move(s2, "0,0>1,0"), "f6-f7", "a walk uses a dash")
    eq(G.describe_move(s2, "0,0>4,0"), "f6^f10", "a jump uses a caret")
    check("opponent's back rank" in G.render(s2)["caption"],
          "the caption shows the race")


def test_termination_and_cap():
    """Onager has no repetition or no-progress rule, so the ply cap is a
    platform backstop.  Assert (a) that it is derived from the board and not
    pinned, (b) that random play never comes near it, and (c) that a decisive
    result OUTRANKS it -- the failure mode found in eight places elsewhere in
    this codebase."""
    for size in SIZES:
        eq(ply_cap(size), PLY_CAP_CELL_FACTOR * n_cells(size),
           "the cap is derived from the board size")
    check(ply_cap(6) == 200 * 91 == 18200, "size 6 cap")
    check(MAN.get("max_random_plies", 3000) < ply_cap(6),
          "max_random_plies must sit BELOW the cap so a termination "
          "regression fails loudly")

    # (b) random play: measured elsewhere over 4,000 games (max 730 plies at
    # size 6); a cheap re-check here.
    rng = random.Random(3)
    longest = 0
    for _ in range(25):
        s = G.initial_state()
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        check(not s.capped, "a random game reached the ply cap")
        longest = max(longest, s.ply)
    check(longest < ply_cap(6) // 10,
          f"random games ({longest} plies) stay far below the cap")

    # (c) a decisive result must outrank the cap.  Re-score the very position
    # that produced a win, with the ply counter poisoned to the cap.
    goal = back_rank(6, 1)[0]
    stacks = {goal: (0,), (0, -1): (1,), (0, -2): (1,)}
    s = st(stacks=stacks, to_move=1, ply=ply_cap(6) - 1)
    s2 = G.apply_move(s, "0,-2>0,-3")
    eq(s2.ply, ply_cap(6), "the cap ply is reached by this very move")
    eq(s2.winner, 0, "and the WIN still stands")
    eq(s2.capped, False, "no draw is recorded")
    eq(G.returns(s2), [1.0, -1.0], "decisive payoff, not [0, 0]")

    # And the cap really does fire when nothing decisive happens.
    stacks = {(0, 0): (0,), (0, 1): (0,), (1, -1): (1,), (2, -2): (1,)}
    s = st(stacks=stacks, lakes={(-5, 0)}, to_move=0, ply=ply_cap(6) - 1)
    s2 = G.apply_move(s, "0,0>-1,0")
    check(s2.capped and s2.winner is None, "the backstop fires as a DRAW")
    eq(G.returns(s2), [0.0, 0.0], "an honest draw, never a fabricated winner")
    eq(G.legal_moves(s2), [], "and the game is over")


def test_no_stuck_non_terminal():
    """`legal_moves` must be non-empty on every non-terminal state."""
    rng = random.Random(5)
    for size in SIZES:
        for _ in range(4):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                ms = G.legal_moves(s)
                check(bool(ms), "a non-terminal state with no legal move")
                if not ms:
                    break
                s = G.apply_move(s, rng.choice(ms))
            eq(G.legal_moves(s), [], "a terminal state offers no move")
            r = G.returns(s)
            eq(len(r), 2, "two payoffs")
            eq(r[0] + r[1], 0.0, "zero sum")


def test_apply_move_is_pure():
    rng = random.Random(13)
    s = G.initial_state()
    for _ in range(60):
        if G.is_terminal(s):
            break
        before = G.serialize(s)
        m = rng.choice(G.legal_moves(s))
        nxt = G.apply_move(s, m)
        eq(G.serialize(s), before, "apply_move mutated its input")
        check(nxt is not s, "apply_move returned the same object")
        s = nxt


# =========================================================================
#  6. The bot evaluation.
# =========================================================================

def test_no_heuristic():
    """This package deliberately ships NO `heuristic`, and this test pins that
    decision so it cannot drift back in unmeasured.

    A candidate eval (back-rank difference + advancement) was measured THROUGH
    `MCTSBot` -- the only consumer -- at 100 iterations with `max_rollout=4` so
    the cutoff is always reached, seats alternated, 40 games a matchup on the
    side-4 board:  19-21 against a CONSTANT-ZERO eval (no measurable gain) and
    23-17 against its own SIGN-FLIPPED self (the direction is not established
    either).  Shipping none is the honest form.
    """
    check("heuristic" not in type(G).__dict__,
          "the package must not ship an unmeasured heuristic")
    check(getattr(G, "heuristic", None) is None,
          "and must not inherit one either")
    # MCTSBot must still work: with no eval it scores a truncated rollout as a
    # draw, which is the generic fallback.
    from agp.mcts import MCTSBot
    s = G.initial_state({"size": 4})
    for m in ("-3,0", "3,0", "0,-1"):
        s = G.apply_move(s, m)
    mv = MCTSBot(random.Random(1), iterations=25, max_rollout=4).select(G, s)
    check(mv in G.legal_moves(s), "MCTSBot with a forced cutoff picks a legal move")


# =========================================================================

def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    if FAILURES:
        print(f"\n{len(FAILURES)} FAILURE(S)")
        for f in FAILURES:
            print(" -", f)
        sys.exit(1)
    print("\nonager selftest: all checks passed")


if __name__ == "__main__":
    main()
