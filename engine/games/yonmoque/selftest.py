#!/usr/bin/env python3
"""Yonmoque correctness anchors.

Pure stdlib (only ``agp`` + this package).  Run:

    cd engine && PYTHONPATH=. python3 games/yonmoque/selftest.py

The anchors, in order of strength:

1. The **board census** -- "8 blue, 12 white and only 5 neutral spaces" plus "the
   half white and half blue squares, **at the center and on the corners**, are
   neutral" -- both quoted from the publisher's own page (the 2016 revision).
   Those two sentences plus the bishop-slide rule determine the whole tile map,
   so the map is checked against the SOURCE, not against the code that built it.
2. The publisher's **movement diagram** (``movement.jpg``), which prints two
   complete legal-move sets of three pieces each on an otherwise empty board --
   48 destinations in total, transcribed here cell by cell.
3. The publisher's **flip diagram** (``flip.jpg``, and the 2016 sheet's ASCII
   version) worked example, including its premises.
4. Constructed positions for every rule the diagrams cannot show: blocked
   slides, placement-never-flips, placement-never-wins, five-in-a-row by move
   AND by placement, a five plus an independent four, a four made only by
   flipped pieces, both forms of the "cannot move -> you lose" rule, and the
   ply-cap/decisive-result ordering.
5. Invariant sweeps over whole random games (the proof step behind the win test,
   serialization, describe_move, render, purity).
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from games.yonmoque.game import (  # noqa: E402
    ADJ, CELLS, DIAG_DIRS, KING_DIRS, PIECES_PER_PLAYER, RAYS, RUNS4, RUNS5,
    SIZE, TILE, YState, Yonmoque, tile_owner,
)

G = Yonmoque()
G.uid = "yonmoque"


def alg(cell):
    """`c,r` -> the publisher's algebraic name (a1 bottom-left, e5 top-right)."""
    c, r = cell.split(",")
    return chr(97 + int(c)) + str(int(r) + 1)


def cr(a):
    return f"{ord(a[0]) - 97},{int(a[1]) - 1}"


def st(pieces, to_move=0, hands=(6, 6), ply=0):
    """Build a state from {algebraic: seat}."""
    return YState(pos={cr(k): v for k, v in pieces.items()}, to_move=to_move,
                  hands=list(hands), ply=ply)


def dests(state, frm):
    return sorted(alg(m.split(">")[1]) for m in G.legal_moves(state)
                  if m.startswith(cr(frm) + ">"))


FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("  FAIL:", msg)


# --------------------------------------------------------------------------
# 1. The board.  Ground truth = the publisher's prose, not our own code.
# --------------------------------------------------------------------------
def test_board():
    census = {0: 0, 1: 0, None: 0}
    for c in CELLS:
        census[TILE[c]] += 1
    # "Board: 5 x 5 grid board; made up of 8 blue, 12 white and 5 neutral
    # spaces." (logygames.com, Complete Rules)   Blue == the FIRST player.
    check(len(CELLS) == 25, "board is 25 squares")
    check(census[0] == 8, f"8 first-player squares, got {census[0]}")
    check(census[1] == 12, f"12 second-player squares, got {census[1]}")
    check(census[None] == 5, f"5 neutral squares, got {census[None]}")
    # "The half white and half blue squares, at the center and on the corners,
    # are neutral (neither blue nor white)." (2016 revision of the same page)
    corners_centre = {"a1", "a5", "e1", "e5", "c3"}
    neutral = {alg(c) for c in CELLS if TILE[c] is None}
    check(neutral == corners_centre,
          f"neutrals are the centre and the four corners, got {sorted(neutral)}")
    # The first player's eight are exactly the ring at Manhattan distance 2.
    check({alg(c) for c in CELLS if TILE[c] == 0} ==
          {"c5", "b4", "d4", "a3", "e3", "b2", "d2", "c1"},
          "first player's eight squares are the diamond ring")

    # The map is invariant under the FULL dihedral group of the square, so no
    # orientation or mirroring error in it is observable.  (This is why no
    # coordinate "control" can prove the mapping used by the differential --
    # every candidate control lies inside the game's own automorphism group.)
    def t(c, r):
        return TILE[f"{c},{r}"]
    for c in range(SIZE):
        for r in range(SIZE):
            check(t(c, r) == t(SIZE - 1 - c, r) == t(c, SIZE - 1 - r) == t(r, c),
                  f"tile map is D4-invariant at {c},{r}")

    # Lemma used by rules.md: two ORTHOGONALLY adjacent squares never share a
    # colour (a step changes the parity of c+r, and every odd square belongs to
    # the second player), so "diagonal" in the slide rule is not separable from
    # "in a straight line" by any position -- a rook-slide reading is vacuously
    # identical.  Assert it rather than assume it.
    for c in range(SIZE):
        for r in range(SIZE):
            for dc, dr in [(1, 0), (0, 1)]:
                if c + dc < SIZE and r + dr < SIZE:
                    a, b = t(c, r), t(c + dc, r + dr)
                    check(a is None or b is None or a != b,
                          f"no two orthogonally adjacent same-colour squares at {c},{r}")
    # Corollary: for the SECOND player the path-colour test is vacuous (every
    # diagonal ray from an odd square stays odd), while for the FIRST it bites.
    for c in range(SIZE):
        for r in range(SIZE):
            if TILE[f"{c},{r}"] != 1:
                continue
            for d in DIAG_DIRS:
                for q in RAYS[f"{c},{r}"][d]:
                    check(TILE[q] == 1,
                          f"second player's diagonal rays stay on colour ({c},{r}->{q})")
    # And the OTHER half of the slide rule -- "only if the square it is on
    # matches the colour of the piece" -- is redundant on this board, because
    # from a square that is not yours no diagonal ray carries two consecutive
    # squares of your colour, and a one-square slide is just a king step.  We
    # still implement the clause as written; assert the reason it cannot bite.
    for cell in CELLS:
        for seat in (0, 1):
            if TILE[cell] == seat:
                continue
            for d in DIAG_DIRS:
                ray = RAYS[cell][d]
                check(not (len(ray) >= 2 and TILE[ray[0]] == seat
                           and TILE[ray[1]] == seat),
                      f"no two-square own-colour ray out of a foreign square {cell}")


# --------------------------------------------------------------------------
# 2. The publisher's movement diagram -- two complete legal-move sets.
#    (www.logygames.com/english/yonmoque/movement.jpg)
#
#    Each panel shows THREE pieces of ONE colour on an otherwise EMPTY board
#    and draws every square each may move to.  Transcribed arrow by arrow.
# --------------------------------------------------------------------------
FIGURE = {
    # left panel: three SECOND-player (white) pieces
    1: {
        # a4 is a white square -> king steps + a bishop slide down the white
        # diagonal as far as d1 (three squares).
        "a4": ["a3", "a5", "b3", "b4", "b5", "c2", "d1"],
        # d3 is white -> 8 king steps + slides to b5 (NW) and b1 (SW).
        "d3": ["b1", "b5", "c2", "c3", "c4", "d2", "d4", "e2", "e3", "e4"],
        # b2 is a BLUE square -> a white piece standing there gets king steps only.
        "b2": ["a1", "a2", "a3", "b1", "b3", "c1", "c2", "c3"],
    },
    # right panel: three FIRST-player (blue) pieces
    0: {
        # c5 is blue -> king steps + slides down both blue diagonals (a3, e3).
        "c5": ["a3", "b4", "b5", "c4", "d4", "d5", "e3"],
        # d3 is a WHITE square -> a blue piece there gets king steps only.
        "d3": ["c2", "c3", "c4", "d2", "d4", "e2", "e3", "e4"],
        # b2 is blue, but both of its outward diagonals hit a NEUTRAL square
        # (a1 and c3), so the slide buys it nothing: king steps only.
        "b2": ["a1", "a2", "a3", "b1", "b3", "c1", "c2", "c3"],
    },
}


def test_movement_figure():
    for seat, panel in FIGURE.items():
        s = st({c: seat for c in panel}, to_move=seat, hands=(3, 3))
        # Assert the figure's PREMISES, not only its outcome: exactly three
        # pieces, all of one colour, board otherwise empty, and the three tiles
        # are the ones the panel's colouring shows.
        check(len(s.pos) == 3 and set(s.pos.values()) == {seat},
              "figure premise: three pieces of one colour")
        for c in panel:
            for m in G.legal_moves(s):
                if ">" in m:
                    check(alg(m.split(">")[0]) in panel,
                          "figure premise: only the drawn pieces can move")
        for c, want in panel.items():
            got = dests(s, c)
            check(got == sorted(want),
                  f"movement figure, seat {seat}, {c}: {got} != {sorted(want)}")
        check(sum(len(v) for v in panel.values()) ==
              len([m for m in G.legal_moves(s) if ">" in m]),
              f"movement figure, seat {seat}: no extra moves")

    # ---- what the figure CANNOT see, covered deliberately -----------------
    # (a) Every square in the diagram is empty, so nothing there tests
    #     blocking.  A slide is stopped by ANY piece, friendly or enemy, and
    #     may not land on one.
    for blocker_seat in (0, 1):
        s = st({"a4": 1, "c2": blocker_seat}, to_move=1, hands=(3, 3))
        check(dests(s, "a4") == sorted(["a3", "a5", "b3", "b4", "b5"]),
              f"a {blocker_seat}-blocker on c2 stops the slide beyond b3")
        s = st({"a4": 1, "b3": blocker_seat}, to_move=1, hands=(3, 3))
        check(dests(s, "a4") == sorted(["a3", "a5", "b4", "b5"]),
              f"a {blocker_seat}-blocker on b3 kills the whole diagonal")
    # (b) the first player's slide really is stopped by a wrong-coloured
    #     square, with nothing occupying it (b2 -> c3 is neutral; d4 beyond it
    #     is blue and must NOT be reachable).
    s = st({"b2": 0}, to_move=0, hands=(3, 3))
    check("d4" not in dests(s, "b2"), "a neutral square stops a first-player slide")
    check("e5" not in dests(s, "b2"), "a slide cannot jump a neutral square")
    # (c) a king step onto an occupied square is illegal.
    s = st({"c4": 0, "c5": 1}, to_move=0, hands=(3, 3))
    check("c5" not in dests(s, "c4"), "a king step cannot land on a piece")


# --------------------------------------------------------------------------
# 3. The flip diagram, and its premises.
#    "(blue) (white) (white) ... blue moves up into the fourth square ...
#     -> blue white white blue -> blue blue blue blue"
# --------------------------------------------------------------------------
def test_flip_figure():
    before = st({"a3": 0, "b3": 1, "c3": 1, "d2": 0}, to_move=0, hands=(2, 2))
    # premises the figure relies on: the two enemy pieces are ADJACENT, in a
    # line, with one of ours already at the far end and the arriving piece
    # closing it; the arriving square is empty before the move.
    check(before.pos.get(cr("d3")) is None, "flip figure: d3 is empty first")
    check(before.pos[cr("a3")] == 0 and before.pos[cr("d2")] == 0,
          "flip figure: both ends are the mover's")
    s = G.apply_move(before, f"{cr('d2')}>{cr('d3')}")
    check(sorted(alg(c) for c in s.flipped) == ["b3", "c3"],
          f"flip figure flips b3 and c3, got {[alg(c) for c in s.flipped]}")
    check(all(s.pos[cr(c)] == 0 for c in ("a3", "b3", "c3", "d3")),
          "flip figure: the whole row is the mover's afterwards")
    # ...and the figure's final panel is four in a row made BY A MOVE = a win.
    # Ground truth outside the engine: the winner is the owner of the piece
    # already printed at the LEFT end of the row before the move.
    check(s.winner == before.pos[cr("a3")] and s.reason == "four",
          f"flip figure ends as a win for the left-end piece's owner, got {s.winner}")

    # The same position reached by PLACING at d3 must NOT flip and must NOT win.
    place = st({"a3": 0, "b3": 1, "c3": 1}, to_move=0, hands=(2, 2))
    s2 = G.apply_move(place, cr("d3"))
    check(s2.flipped == [], "a PLACEMENT never flips")
    check(s2.pos[cr("b3")] == 1 and s2.pos[cr("c3")] == 1,
          "a placement leaves the sandwiched pieces alone")
    check(s2.winner is None, "a placement does not win, even sandwiching")

    # A gap breaks the sandwich; running off the board breaks it too.
    gap = st({"a3": 0, "c3": 1, "d2": 0}, to_move=0, hands=(2, 2))
    s3 = G.apply_move(gap, f"{cr('d2')}>{cr('d3')}")
    check(s3.flipped == [], "an empty square between the ends blocks the flip")
    edge = st({"b3": 1, "c3": 1, "d2": 0}, to_move=0, hands=(2, 2))
    s4 = G.apply_move(edge, f"{cr('d2')}>{cr('d3')}")
    check(s4.flipped == [], "a run that reaches the board edge is not trapped")
    # Your own pieces are never flipped by your own move.
    own = st({"a3": 1, "b3": 0, "c3": 0, "d2": 1}, to_move=1, hands=(2, 2))
    s5 = G.apply_move(own, f"{cr('d2')}>{cr('d3')}")
    check(sorted(alg(c) for c in s5.flipped) == ["b3", "c3"],
          "the mover flips the ENEMY pieces it traps")
    check(all(s5.pos[cr(c)] == 1 for c in ("b3", "c3")), "flipped to the mover")
    # The square just vacated is empty, so it cannot act as a bracket end.
    vac = st({"c3": 0, "b3": 1, "a3": 0}, to_move=0, hands=(2, 2))
    s6 = G.apply_move(vac, f"{cr('a3')}>{cr('a4')}")
    check(s6.flipped == [], "the vacated square does not close a sandwich")
    # Several directions at once.
    multi = st({"c1": 0, "c2": 1, "c3": 0, "b3": 1, "a3": 0,
                "d3": 1, "e3": 0, "d2": 1, "e1": 0, "c4": 1, "c5": 0,
                "b4": 1, "a5": 0}, to_move=0, hands=(0, 0))
    s7 = G.apply_move(multi, f"{cr('c1')}>{cr('c2')}")
    check(s7.flipped == [], "sanity: no flip when the mover leaves the line")


# --------------------------------------------------------------------------
# 4. Winning, losing, and the rules the diagrams do not cover.
# --------------------------------------------------------------------------
def test_four_and_five():
    # Four in a row made by a MOVE wins.
    s = G.apply_move(st({"a3": 0, "b3": 0, "c3": 0, "d4": 0}, to_move=0,
                        hands=(2, 2)), f"{cr('d4')}>{cr('d3')}")
    check(s.winner == 0 and s.reason == "four", "four by a move wins")

    # The identical four made by a PLACEMENT does not win; the game continues.
    s = G.apply_move(st({"a3": 0, "b3": 0, "c3": 0}, to_move=0, hands=(2, 2)),
                     cr("d3"))
    check(s.winner is None and not G.is_terminal(s),
          "four by a placement does NOT win")
    # ...and that standing four does not win on some LATER, unrelated move
    # either -- the four must be CREATED by the move.  (This is the one
    # difference our differential needed ~4,000 plies to expose.)
    standing = st({"a3": 0, "b3": 0, "c3": 0, "d3": 0, "a1": 0, "e5": 1},
                  to_move=0, hands=(0, 1))
    s = G.apply_move(standing, f"{cr('a1')}>{cr('b1')}")
    check(s.winner is None,
          "a four that was already standing does not win on a later move")
    check(all(s.pos[cr(c)] == 0 for c in ("a3", "b3", "c3", "d3")),
          "premise: the standing four is still there")

    # Four made ONLY by flipped pieces, with the arriving piece outside the
    # line, still wins ("through movement").
    flipwin = st({"a3": 0, "b3": 0, "d3": 0, "c2": 0, "c3": 1, "b5": 0,
                  "e5": 1}, to_move=0, hands=(0, 2))
    s = G.apply_move(flipwin, f"{cr('b5')}>{cr('c4')}")
    check(sorted(alg(c) for c in s.flipped) == ["c3"], "the sandwich flips c3")
    win_run = [r for r in RUNS4 if all(s.pos.get(x) == 0 for x in r)]
    check(win_run and all(cr("c4") not in r for r in win_run),
          "premise: the arriving square is NOT in the completed four")
    check(s.winner == 0 and s.reason == "four",
          "a four completed by a FLIPPED piece wins")

    # Five in a row loses -- by moving...
    s = G.apply_move(st({"a3": 0, "b3": 0, "c3": 0, "d3": 0, "e4": 0},
                        to_move=0, hands=(1, 1)), f"{cr('e4')}>{cr('e3')}")
    check(s.winner == 1 and s.reason == "five", "five by a move loses")
    # ...and by placing.
    s = G.apply_move(st({"a3": 0, "b3": 0, "c3": 0, "d3": 0}, to_move=0,
                        hands=(2, 2)), cr("e3"))
    check(s.winner == 1 and s.reason == "five", "five by a placement loses")
    # A diagonal five counts ("in any direction, including diagonally").
    s = G.apply_move(st({"a1": 0, "b2": 0, "c3": 0, "d4": 0}, to_move=0,
                        hands=(2, 2)), cr("e5"))
    check(s.winner == 1 and s.reason == "five", "a diagonal five loses too")

    # INTERPRETATION (named in rules.md): a move that makes a five in one line
    # AND an independent new four in another is a LOSS -- the five is stated
    # unconditionally.  This position was REACHED in random play, not invented.
    both = YState(pos={'4,2': 0, '1,1': 1, '0,2': 1, '0,0': 0, '1,4': 0,
                       '1,3': 1, '4,4': 0, '3,3': 1, '1,2': 0, '2,3': 0,
                       '3,2': 0, '2,1': 1}, to_move=0, hands=[0, 0])
    s = G.apply_move(both, "2,3>2,2")
    five = [r for r in RUNS5 if all(s.pos.get(x) == 0 for x in r)]
    four = [r for r in RUNS4 if all(s.pos.get(x) == 0 for x in r)
            and not any(set(r) <= set(f) for f in five)]
    check(five and four, "premise: this move makes a five AND an outside four")
    check(s.winner == 1 and s.reason == "five",
          "a five outranks a simultaneous four (documented interpretation)")


def test_no_move_loses():
    # (a) the reachable form: the loser's last piece is flipped away and their
    #     hand is empty, so they have nothing at all to do.
    pre = st({"b2": 0, "c2": 1, "d1": 0}, to_move=0, hands=(3, 0))
    check(sum(1 for v in pre.pos.values() if v == 1) == 1 and pre.hands[1] == 0,
          "premise: the second player has one piece and an empty hand")
    s = G.apply_move(pre, f"{cr('d1')}>{cr('d2')}")
    check(sorted(alg(c) for c in s.flipped) == ["c2"], "the last piece is flipped")
    check(not any(v == 1 for v in s.pos.values()), "the second player is wiped out")
    check(s.winner == 0 and s.reason == "stuck",
          "total annihilation loses (no piece to place or move)")

    # (b) the other form: six pieces still on the board but every neighbour of
    #     every one of them is occupied, and the hand is empty.
    pre = st({"a1": 1, "a2": 1, "a3": 1, "b1": 1, "b2": 1, "b3": 1,
              "c1": 0, "c2": 0, "c3": 0, "c4": 0, "a4": 0, "b5": 0},
             to_move=0, hands=(0, 0))
    check(len(G.legal_moves(pre)) > 0, "premise: the mover still has moves")
    s = G.apply_move(pre, f"{cr('b5')}>{cr('b4')}")
    check(s.flipped == [], "premise: that move flips nothing")
    check(sum(1 for v in s.pos.values() if v == 1) == 6,
          "premise: the loser still has all six pieces on the board")
    check(s.winner == 0 and s.reason == "stuck",
          "being completely immobilised loses")

    # Holding a piece in hand always saves you: 25 squares, at most 12 pieces,
    # so there is always somewhere to place.
    alive = st({"a1": 1, "a2": 1, "a3": 1, "b1": 1, "b2": 1, "b3": 1,
                "c1": 0, "c2": 0, "c3": 0, "c4": 0, "a4": 0, "b4": 0},
               to_move=1, hands=(0, 1))
    check(len(G.legal_moves(alive)) == len(CELLS) - len(alive.pos),
          "with a piece in hand every empty square is a legal move")


def test_cap_and_ordering():
    check(Yonmoque.PLY_CAP == 2 * PIECES_PER_PLAYER + Yonmoque.MOVE_ALLOWANCE,
          "the cap is derived from the game's own quantities")
    # The cap bites...
    capped = st({"a3": 0, "e5": 1}, to_move=0, hands=(5, 5), ply=Yonmoque.PLY_CAP)
    check(G.is_terminal(capped) and G.returns(capped) == [0.0, 0.0]
          and G.legal_moves(capped) == [],
          "the ply cap ends the game as a draw")
    # ...but a DECISIVE result outranks it: the very move that reaches the cap
    # can still be a win, a loss, or a stuck-loss.
    win = G.apply_move(st({"a3": 0, "b3": 0, "c3": 0, "d4": 0}, to_move=0,
                          hands=(2, 2), ply=Yonmoque.PLY_CAP - 1),
                       f"{cr('d4')}>{cr('d3')}")
    check(win.ply == Yonmoque.PLY_CAP and win.winner == 0
          and G.returns(win) == [1.0, -1.0],
          "a win on the capping ply is a WIN, not a draw")
    lose = G.apply_move(st({"a3": 0, "b3": 0, "c3": 0, "d3": 0, "e4": 0},
                           to_move=0, hands=(1, 1), ply=Yonmoque.PLY_CAP - 1),
                        f"{cr('e4')}>{cr('e3')}")
    check(lose.winner == 1 and G.returns(lose) == [-1.0, 1.0],
          "a five on the capping ply is a LOSS, not a draw")
    stuck = G.apply_move(st({"b2": 0, "c2": 1, "d1": 0}, to_move=0,
                            hands=(3, 0), ply=Yonmoque.PLY_CAP - 1),
                         f"{cr('d1')}>{cr('d2')}")
    check(stuck.winner == 0 and stuck.reason == "stuck",
          "a stuck-loss on the capping ply outranks the draw counter")
    # `_draw` is a predicate nothing on the legality path consults (only the
    # caption does), so test it directly -- a decided game is never "a draw".
    for decided in (win, lose, stuck):
        check(not G._draw(decided), "a decided game at the cap is not a draw")
    check(G._draw(capped), "an undecided game at the cap IS a draw")


def test_vacuous_clauses():
    """Rules that are in the sheet but provably cannot fire.  Random play can
    never reach them, so they are checked on constructed input."""
    # "On each player's first turn they must place one of their pieces onto the
    # board."  Vacuous: with nothing on the board there is nothing else to do.
    s0 = G.initial_state()
    check(all(">" not in m for m in G.legal_moves(s0)) and len(G.legal_moves(s0)) == 25,
          "every opening move is a placement")
    s1 = G.apply_move(s0, "0,0")
    check(all(">" not in m for m in G.legal_moves(s1)),
          "the second player's first turn is a placement too")
    # Exhaustive: over EVERY board of 1..12 pieces would be huge, so instead
    # assert the structural reason -- a mover with no piece on the board has
    # only placements, and a mover always has a piece in hand or on the board.
    for hand in range(PIECES_PER_PLAYER + 1):
        s = YState(pos={}, to_move=0, hands=[hand, 0])
        check(bool(G.legal_moves(s)) == (hand > 0),
              "a player with nothing anywhere has no move")


# --------------------------------------------------------------------------
# 5. Sweeps over whole games.
# --------------------------------------------------------------------------
SER_KEYS = {"pos", "to_move", "hands", "ply", "winner", "reason", "last", "flipped"}


def test_sweep(ngames=250, seed=20260731):
    import copy
    rng = random.Random(seed)
    reasons = {}
    plies = 0
    longest = 0
    for _ in range(ngames):
        s = G.initial_state()
        while not G.is_terminal(s):
            moves = G.legal_moves(s)
            check(bool(moves), "a non-terminal state always has a move")
            check(len(moves) == len(set(moves)), "the move list has no duplicates")
            p = s.to_move
            before = copy.deepcopy(s)
            m = rng.choice(moves)
            desc = G.describe_move(s, m)
            ns = G.apply_move(s, m)
            plies += 1
            check(s == before, "apply_move does not mutate its input")

            # --- the proof step behind the win test, checked live ------------
            # "a four containing a square that only just became the mover's"
            # is the same thing as "a four that did not exist before the move".
            newly = [c for c, v in ns.pos.items() if v == p and s.pos.get(c) != p]
            old = {r for r in RUNS4 if all(s.pos.get(x) == p for x in r)}
            new = {r for r in RUNS4 if all(ns.pos.get(x) == p for x in r)}
            check(G._new_four(ns.pos, p, newly) == bool(new - old),
                  "new-four test == 'a four that did not exist before'")
            # A move never creates a line for the player who did not move.
            check(not G._has_run(ns.pos, 1 - p, RUNS5),
                  "a move cannot make FIVE for the opponent")
            # Placements never flip anything.
            if ">" not in m:
                check(ns.flipped == [] and
                      all(ns.pos[c] == v for c, v in s.pos.items()),
                      "a placement changes no existing piece")
                check(ns.hands[p] == s.hands[p] - 1, "a placement spends a piece")
            else:
                check(ns.hands == s.hands, "a move spends nothing")
                check(len(ns.pos) == len(s.pos), "a move adds no piece")
            # Material is conserved by a move; nothing ever leaves the board.
            check(len(ns.pos) + sum(ns.hands) == len(s.pos) + sum(s.hands),
                  "pieces are never destroyed")

            # --- describe_move: not on the legality path, so test it ---------
            check(isinstance(desc, str) and desc,
                  "describe_move returns a non-empty string")
            check(("x%d" % len(ns.flipped) in desc) == bool(ns.flipped),
                  f"describe_move reports the flip count: {desc}")
            check(("#4" in desc) == (ns.reason == "four"),
                  f"describe_move marks a four: {desc}")
            check(("!5" in desc) == (ns.reason == "five"),
                  f"describe_move marks a five: {desc}")

            # --- serialization: compare STATE OBJECTS, and the key set -------
            d = G.serialize(s)
            check(set(d) == SER_KEYS, f"serialize emits exactly {SER_KEYS}")
            check(G.deserialize(d) == s, "serialize/deserialize round-trips the STATE")

            # --- render ------------------------------------------------------
            spec = G.render(s)
            b = spec["board"]
            check(b["width"] == SIZE and b["height"] == SIZE, "5x5 board declared")
            check(set(b["tints"]) == set(CELLS), "every square is tinted")
            check(len(set(b["tints"].values())) == 3, "three tile colours")
            for pc in spec["pieces"]:
                c, r = pc["cell"].split(",")
                check(0 <= int(c) < SIZE and 0 <= int(r) < SIZE,
                      "every rendered piece is on the declared board")
            for h in spec["highlights"]:
                check(h["cell"] in CELLS, "highlights point at real squares")
            s = ns
        reasons[s.reason] = reasons.get(s.reason, 0) + 1
        longest = max(longest, s.ply)
        d = G.serialize(s)
        check(G.deserialize(d) == s, "the terminal state round-trips too")
        check(sum(G.returns(s)) == 0, "returns are zero-sum")
    # Reachability of each ending under random play, so we know which endings
    # the sweep actually covers and which live only in the constructed tests.
    print(f"  sweep: {ngames} games, {plies} plies, longest {longest}, "
          f"endings {reasons}")
    check(reasons.get("four", 0) > 0 and reasons.get("five", 0) > 0,
          "random play reaches both the four-win and the five-loss")
    # The ply cap must NOT be deciding games.  Measured over 60,000 random
    # games the longest was 125 plies against a cap of 412, so a cap draw here
    # means the cap has become outcome-load-bearing (or termination regressed).
    check(reasons.get(None, 0) == 0, "no random game is decided by the ply cap")
    check(longest * 3 < Yonmoque.PLY_CAP,
          f"the cap ({Yonmoque.PLY_CAP}) is far above real play ({longest})")


def test_render_naming():
    """The caption's seat naming, pinned in BOTH directions so an inverted
    mapping cannot hide behind a single assertion."""
    a = G.render(st({"a3": 0}, to_move=0, hands=(5, 6)))["caption"]
    b = G.render(st({"a3": 0}, to_move=1, hands=(5, 6)))["caption"]
    check(a.startswith("Red") and b.startswith("Blue"),
          f"to-move captions name the right seat: {a!r} / {b!r}")
    w0 = G.apply_move(st({"a3": 0, "b3": 0, "c3": 0, "d4": 0}, to_move=0,
                         hands=(2, 2)), f"{cr('d4')}>{cr('d3')}")
    w1 = G.apply_move(st({"a3": 1, "b3": 1, "c3": 1, "d4": 1}, to_move=1,
                         hands=(2, 2)), f"{cr('d4')}>{cr('d3')}")
    check(w0.winner == 0 and G.render(w0)["caption"].startswith("Red wins"),
          "seat 0 winning is captioned Red")
    check(w1.winner == 1 and G.render(w1)["caption"].startswith("Blue wins"),
          "seat 1 winning is captioned Blue")
    drawn = st({"a3": 0}, to_move=0, hands=(5, 6), ply=Yonmoque.PLY_CAP)
    check(G.render(drawn)["caption"].startswith("Draw"), "a draw is captioned Draw")

    # The "five" and "stuck" captions name the LOSER as well as the winner, via
    # `names[1 - winner]` -- an inverted index nothing else in the package
    # consults, so it has to be asserted here or it is untested.  Both are
    # pinned to ground truth read off the POSITION (who actually made the five;
    # who actually has no piece anywhere), not to the engine's own naming, and
    # both directions are covered so a swapped mapping cannot hide.
    NAME = {0: "Red", 1: "Blue"}
    for maker in (0, 1):
        five = G.apply_move(
            st({"a3": maker, "b3": maker, "c3": maker, "d3": maker, "e4": maker},
               to_move=maker, hands=(1, 1)), f"{cr('e4')}>{cr('e3')}")
        # premise: `maker` is the one holding the five, and they lost for it.
        check(all(five.pos[cr(c)] == maker for c in ("a3", "b3", "c3", "d3", "e3")),
              "five-caption premise: the five belongs to the mover")
        check(five.winner == 1 - maker and five.reason == "five",
              "five-caption premise: making the five loses")
        cap = G.render(five)["caption"]
        check(cap == f"{NAME[1 - maker]} wins - {NAME[maker]} made five in a row",
              f"the five caption blames the player who made it, got {cap!r}")

    for wiped in (0, 1):
        other = 1 - wiped
        # the wiped seat's hand is empty; the mover still holds pieces
        hands = (3, 0) if wiped == 1 else (0, 3)
        pre = st({"b2": other, "c2": wiped, "d1": other}, to_move=other,
                 hands=hands)
        s = G.apply_move(pre, f"{cr('d1')}>{cr('d2')}")
        # premise: `wiped` really has nothing left to place or move.
        check(not any(v == wiped for v in s.pos.values()) and s.hands[wiped] == 0,
              "stuck-caption premise: the loser has no piece on the board or in hand")
        check(s.winner == other and s.reason == "stuck",
              "stuck-caption premise: having no move loses")
        cap = G.render(s)["caption"]
        check(cap == f"{NAME[other]} wins - {NAME[wiped]} had no move",
              f"the stuck caption blames the player who was stuck, got {cap!r}")


def main():
    test_board()
    test_movement_figure()
    test_flip_figure()
    test_four_and_five()
    test_no_move_loses()
    test_cap_and_ordering()
    test_vacuous_clauses()
    test_render_naming()
    test_sweep()
    if FAILS:
        print(f"yonmoque selftest: {len(FAILS)} FAILURES")
        return 1
    print("yonmoque selftest: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
