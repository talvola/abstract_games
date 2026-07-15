"""Blokus Trigon selftest — pure stdlib (agp + this game only).

PRIMARY ANCHOR: the opening legal-move set, cross-checked against Pentobi
(Markus Enzenberger's reference Blokus engine, `pentobi-gtp`: `set_game blokus
trigon` + `all_legal 1`), which reports **2478** legal first moves with the size
distribution {1: 6, 2: 18, 3: 54, 4: 168, 5: 540, 6: 1692}.

That single number pins three independent things at once:

* the BOARD (a hexagon of 486 triangles, and the six start points),
* the PIECE SET (the 22 free polyiamonds of size 1..6), and
* the triangular ROTATION/REFLECTION maths — a 60-degree rotation is not an
  integer map on (c, r), so a wrong transform silently merges or splits piece
  classes and moves a size bucket off.

2478 = 6 x 413: no opening move can reach two start points (they are 5+ cells
apart and no piece spans that far), so each of the six contributes exactly the
same 413 placements. `test_opening_matches_pentobi` checks the split and the
per-start-point breakdown too, so a failure localises to a piece size.

The geometry itself is NOT taken on trust from Pentobi's coordinate tables: the
adjacency/corner rules and the up/down convention are re-derived here from an
independent VERTEX model (`test_lattice_from_first_principles`), and the board is
checked to be D6-symmetric about its centre (`test_board_is_a_regular_hexagon`).
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Import through the canonical package path (as games/blokus_duo/selftest.py
# does). Importing the bare `game` module instead would load a SECOND copy
# alongside the one agp.loader registers under its own synthetic module name,
# duplicating the 32k-entry placement tables and making `type(state) is BState`
# false.
import games.blokus_trigon.game as G  # noqa: E402

GAME = G.BlokusTrigon()

# The Pentobi anchor.
OPENING = 2478
OPENING_SPLIT = {1: 6, 2: 18, 3: 54, 4: 168, 5: 540, 6: 1692}
PER_START = 413


# --------------------------------------------------------------------------
# Geometry — re-derived independently of the game's coordinate tables.
# --------------------------------------------------------------------------

def test_board_is_486_triangles():
    """Pentobi TrigonGeometry(9) / the rulebook's "a board with 486 spaces"."""
    assert len(G.ON_CELLS) == 486, len(G.ON_CELLS)
    rows = [sum(1 for c, r in G.ON_CELLS if r == rr) for rr in range(G.H)]
    assert rows == [19, 21, 23, 25, 27, 29, 31, 33, 35, 35, 33, 31, 29, 27, 25, 23, 21, 19], rows
    # A hexagon of side 9 on a triangular lattice: 6 * 9^2 unit triangles.
    assert len(G.ON_CELLS) == 6 * G.SZ ** 2
    assert bin(G.ON_BOARD).count("1") == 486
    # Up/down split: each of the 6 side-9 sub-triangles contributes evenly.
    assert bin(G.UP_MASK).count("1") == 243, bin(G.UP_MASK).count("1")
    assert bin(G.DOWN_MASK).count("1") == 243
    print("  board = 486 triangles, rows 19..35..19, 243 up / 243 down OK")


def _verts_indep(c, r):
    """The 3 lattice vertices of triangle (c, r) — derived here from scratch.

    Row r spans heights [r, r+1]; triangle (c, r) spans x in [c/2, c/2 + 1].
    An UP triangle has its base at the BOTTOM (height r) and its apex above; a
    DOWN triangle has its top edge above and its apex at height r. Vertices at
    height m sit at x = k/2 for k with the parity of m+1, so (m, k) -> the
    lattice index ((k - m - 1)/2, m) makes them plain integers.
    """
    def vx(k, m):
        assert (k - m - 1) % 2 == 0, (k, m)
        return ((k - m - 1) // 2, m)
    if (c + r) % 2 == 1:                       # up: base at height r
        return frozenset({vx(c, r), vx(c + 2, r), vx(c + 1, r + 1)})
    return frozenset({vx(c, r + 1), vx(c + 2, r + 1), vx(c + 1, r)})


def test_lattice_from_first_principles():
    """`_up`, `_ADJ_*` and `_DIAG_*` must be exactly what the geometry implies.

    Two triangles share an EDGE iff they share 2 vertices, and a CORNER iff they
    share exactly 1. Those two relations are the whole Blokus rule, so deriving
    them independently (rather than trusting Pentobi's transcribed coordinate
    lists) is what makes the corner rule trustworthy on a triangular lattice,
    where "diagonal" is far from obvious: a triangle has NINE corner neighbours,
    not four.
    """
    # The game's vertex model agrees with the independent one.
    for r in range(-3, G.H + 3):
        for c in range(-4, G.W + 4):
            assert G._verts(c, r) == _verts_indep(c, r), (c, r)
            assert G._from_verts(G._verts(c, r)) == (c, r), (c, r)

    for r in range(2, G.H - 2):
        for c in range(4, G.W - 4):
            mine = G._verts(c, r)
            # Every cell sharing at least one vertex, found by brute force.
            near = {(cc, rr) for rr in range(r - 3, r + 4) for cc in range(c - 4, c + 5)
                    if (cc, rr) != (c, r) and (mine & G._verts(cc, rr))}
            edge = {p for p in near if len(mine & G._verts(*p)) == 2}
            corner = {p for p in near if len(mine & G._verts(*p)) == 1}
            assert len(edge) == 3, (c, r, edge)
            assert len(corner) == 9, (c, r, corner)
            assert set(G._adj(c, r)) == edge, (c, r)
            diag = G._DIAG_UP if G._up(c, r) else G._DIAG_DOWN
            assert {(c + dc, r + dr) for dc, dr in diag} == corner, (c, r)
            assert not (edge & corner)
    print("  edge (3) / corner (9) neighbours re-derived from the vertex model OK")


def test_up_convention_matches_geometry():
    """UP <=> (c + r) odd, and an up-triangle's horizontal edge is at the bottom."""
    for c, r in G.ON_CELLS:
        assert G._up(c, r) == ((c + r) % 2 == 1)
        # The third (non-lateral) edge neighbour is BELOW an up-triangle.
        third = [p for p in G._adj(c, r) if p[0] == c]
        assert len(third) == 1
        assert third[0] == ((c, r - 1) if G._up(c, r) else (c, r + 1)), (c, r)
    # Adjacency is symmetric (a broken third-neighbour rule would show up here).
    on = set(G.ON_CELLS)
    for c, r in G.ON_CELLS:
        for p in G._adj(c, r):
            if p in on:
                assert (c, r) in G._adj(*p), (c, r, p)
    print("  up/down convention + adjacency symmetry OK")


def test_board_is_a_regular_hexagon():
    """The 486 cells and the 6 start points are invariant under the full D6.

    Rotating 60 degrees about the board's centre vertex must map the board onto
    itself. This checks `_onboard` AND the vertex-lattice transforms at once: if
    either the hexagon carve or the rotation matrix were wrong, the image would
    not land back on the board.
    """
    ctr = (4, 9)                        # the hexagon's centre, in vertex coords
    on = set(G.ON_CELLS)

    def turn(cell, t):
        vs = frozenset(t((i - ctr[0], j - ctr[1])) for i, j in G._verts(*cell))
        return G._from_verts(frozenset((i + ctr[0], j + ctr[1]) for i, j in vs))

    for name, t in (("rot60", G._rot60), ("mirror", G._mirror)):
        img = {turn(cell, t) for cell in G.ON_CELLS}
        assert img == on, f"{name} does not map the board onto itself"
        assert {turn(p, t) for p in G.START} == set(G.START), f"{name} moves the start points"
    print("  board + start points are D6-symmetric about the centre OK")


def test_start_points():
    """Six SHARED start points (Pentobi's colorless trigon starting points)."""
    assert len(G.START) == 6, G.START
    assert set(G.START) == {(9, 6), (9, 11), (17, 3), (17, 14), (25, 6), (25, 11)}
    for c, r in G.START:
        assert G._onboard(c, r), (c, r)
    assert bin(G.START_MASK).count("1") == 6
    print("  6 shared start points OK")


# --------------------------------------------------------------------------
# Piece set
# --------------------------------------------------------------------------

def test_piece_set_is_the_22_free_polyiamonds():
    """Rulebook: "1 piece with one triangle, 1 with two, 1 with three, 3 with
    four, 4 with five and 12 with six" — i.e. the free polyiamonds of size 1..6
    (OEIS A000577), 22 pieces and 110 unit triangles per colour."""
    assert len(G.PIECES) == 22, len(G.PIECES)
    split = Counter(G.SIZES[k] for k in G.PIECES)
    assert dict(sorted(split.items())) == {1: 1, 2: 1, 3: 1, 4: 3, 5: 4, 6: 12}, split
    assert G.TOTAL_TRIANGLES == 110, G.TOTAL_TRIANGLES
    assert len(set(G._NAMED.values())) == 22, "duplicate piece shapes"
    # Every piece is edge-connected (a polyiamond, not a scatter of triangles).
    for k in G.PIECES:
        cells = G._denorm(G._NAMED[k])
        seen, stack = {cells[0]}, [cells[0]]
        while stack:
            for p in G._adj(*stack.pop()):
                if p in cells and p not in seen:
                    seen.add(p)
                    stack.append(p)
        assert len(seen) == len(cells), f"{k} is disconnected"
    print("  22 pieces = free polyiamonds 1..6 (1,1,1,3,4,12), 110 triangles OK")


def test_orientations_and_anchor_contract():
    """SPEC: every orientation contains [0,0]; `parity` runs parallel to it.

    Also checks the orbit sizes: each piece's orientation count must divide 12
    (the order of D6) and equal 12 / |symmetry group|. The hexagon "O" is fully
    symmetric (1 orientation); the single triangle has 2 (up and down).
    """
    for k in G.PIECES:
        orients, parity = G.ORIENTS[k], G.PARITY[k]
        assert len(orients) == len(parity), k
        assert 1 <= len(orients) <= 12, (k, len(orients))
        assert 12 % len(orients) == 0, (k, len(orients))
        seen = set()
        for offs, p in zip(orients, parity):
            assert [0, 0] in offs, f"{k}: orientation misses the anchor"
            assert len(offs) == G.SIZES[k], k
            assert p in (0, 1), (k, p)
            assert min(dr for _, dr in offs) == 0, f"{k}: anchor is not bottom-most"
            assert min(dc for dc, dr in offs if dr == 0) == 0, f"{k}: anchor not left-most"
            key = (tuple(map(tuple, offs)), p)
            assert key not in seen, f"{k}: duplicate orientation"
            seen.add(key)
    assert len(G.ORIENTS["O"]) == 1, "the hexagon has full D6 symmetry"
    assert len(G.ORIENTS["1"]) == 2, "the unit triangle points up or down"
    assert G.PARITY["1"] == [0, 1] or G.PARITY["1"] == [1, 0]
    print("  anchor contract + parity array + orbit sizes OK")


def test_parity_matches_the_board():
    """THE render check: the parity contract must reproduce the real lattice.

    SPEC/Board.jsx draw the cell at offset (dc,dr) pointing UP iff
    `(dc + dr) % 2 === parity[i]`. If that disagrees with the board for even one
    placement, the chip is point-reflected into a genuinely DIFFERENT polyiamond
    while `validate` and every logic test still pass. So: for every legal
    placement of every piece, assert the drawn orientation equals the board's.
    """
    checked = 0
    for k in G.PIECES:
        for oi, (offs, p) in enumerate(G._ORIENT_DATA[k]):
            for mask, mv in G.PLACEMENTS[k]:
                if not mv.startswith(f"{k}:{oi}@"):
                    continue
                ac, ar = (int(x) for x in mv.split("@", 1)[1].split(","))
                # The anchor's parity must match the orientation's, else the
                # placement is not a translation of the plane at all.
                assert (0 if G._up(ac, ar) else 1) == p, mv
                for dc, dr in offs:
                    drawn_up = ((dc + dr) % 2) == p
                    assert drawn_up == G._up(ac + dc, ar + dr), (mv, dc, dr)
                checked += 1
                break                       # one anchor per orientation suffices
    assert checked == sum(len(G.ORIENTS[k]) for k in G.PIECES), checked
    # And exhaustively over a whole opening move list, anchors included.
    for mv in GAME.legal_moves(GAME.initial_state()):
        k, rest = mv.split(":", 1)
        oi = int(rest.split("@", 1)[0])
        ac, ar = (int(x) for x in rest.split("@", 1)[1].split(","))
        p = G.PARITY[k][oi]
        cells = {(ac + dc, ar + dr) for dc, dr in G.ORIENTS[k][oi]}
        assert cells == set(G._cells_of(G.MOVE_MASK[mv])), mv
        for dc, dr in G.ORIENTS[k][oi]:
            assert (((dc + dr) % 2) == p) == G._up(ac + dc, ar + dr), mv
    print("  parity array reproduces the board's up/down for every placement OK")


# --------------------------------------------------------------------------
# The anchor
# --------------------------------------------------------------------------

def test_opening_matches_pentobi():
    """2478 opening moves, split {1:6, 2:18, 3:54, 4:168, 5:540, 6:1692}."""
    s = GAME.initial_state()
    moves = GAME.legal_moves(s)
    assert len(moves) == len(set(moves)), "duplicate opening moves"
    assert len(moves) == OPENING, f"expected {OPENING} opening moves, got {len(moves)}"
    split = Counter(G.SIZES[m.split(":", 1)[0]] for m in moves)
    assert dict(sorted(split.items())) == OPENING_SPLIT, dict(sorted(split.items()))

    per = Counter()
    for m in moves:
        hits = [x for x in G._cells_of(G.MOVE_MASK[m]) if x in G.START]
        assert hits, f"{m} covers no start point"
        assert len(hits) == 1, f"{m} reaches two start points"
        per[hits[0]] += 1
    assert set(per) == set(G.START), per
    assert all(v == PER_START for v in per.values()), per
    assert OPENING == 6 * PER_START
    # Every seat sees the same 2478 (the start points are shared, not assigned).
    for seat in range(4):
        assert len(list(GAME._gen(s, seat))) == OPENING, seat
    print(f"  opening = {OPENING} moves = 6 x {PER_START}, split {OPENING_SPLIT} OK")


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

def test_first_piece_must_cover_a_start_point():
    s = GAME.initial_state()
    assert all(G.MOVE_MASK[m] & G.START_MASK for m in GAME.legal_moves(s))
    # A placement that fits but touches no start point is rejected.
    off = next(mv for mv in G.MOVE_MASK if not (G.MOVE_MASK[mv] & G.START_MASK))
    try:
        GAME.apply_move(s, off)
        raise AssertionError("accepted a first piece off the start points")
    except ValueError:
        pass
    print("  first piece must cover a start point OK")


def test_start_points_are_shared():
    """Any colour may open on ANY start point; a taken one is simply occupied."""
    s = GAME.initial_state()
    s = GAME.apply_move(s, _mono(9, 6))         # seat 0 takes one start point
    assert s.to_move == 1
    opens = GAME.legal_moves(s)
    covered = Counter()
    for m in opens:
        for x in G._cells_of(G.MOVE_MASK[m]):
            if x in G.START:
                covered[x] += 1
    # Seat 1 may open on any of the OTHER five, but (9,6) is now occupied.
    assert (9, 6) not in covered, "seat 1 can still open on a taken start point"
    assert set(covered) == set(G.START) - {(9, 6)}, covered
    assert all(v == PER_START for v in covered.values()), covered
    assert len(opens) == OPENING - PER_START, len(opens)
    print("  start points shared; a taken one is retired by overlap OK")


def _mono(c, r):
    """The move string placing the single triangle on (c, r), whatever its parity."""
    want = 0 if G._up(c, r) else 1
    oi = G.PARITY[G.MONOMINO].index(want)
    return f"{G.MONOMINO}:{oi}@{c},{r}"


def test_different_colours_may_touch_along_an_edge():
    """"There are no restrictions on how many pieces of different colors may be
    in contact with each other." Hand-built: seat 1 corner-touches its OWN piece
    at (12,6) while landing edge-to-edge with seat 0's (9,6)."""
    hand = tuple(k for k in G.PIECES if k != G.MONOMINO)
    s = G.BState(occ=(G._bit(9, 6), G._bit(12, 6), 0, 0),
                 hands=(hand, G.PIECES, G.PIECES, G.PIECES),
                 to_move=1, last_key=(G.MONOMINO, "I6", None, None))
    assert (10, 6) in G._adj(9, 6), "the test cell must share an edge with seat 0"
    diag1 = {(12 + dc, 6 + dr) for dc, dr in (G._DIAG_UP if G._up(12, 6) else G._DIAG_DOWN)}
    assert (10, 6) in diag1, "the test cell must corner-touch seat 1's own piece"
    assert (10, 6) not in G._adj(12, 6), "and must not edge-touch seat 1's own piece"
    assert _mono(10, 6) in GAME.legal_moves(s), "different colours may share an edge"
    print("  different colours may touch along an edge OK")


def test_corner_rule_is_exactly_the_nine_corners():
    """Own colour: >=1 corner touch, NO edge touch — checked EXACTLY.

    Seat 0 owns the single triangle (9,6) and holds only the monomino, so its
    legal moves must be precisely the NINE corner neighbours of (9,6): not the
    3 edge neighbours, and nothing else. This is the sharpest statement of the
    Blokus rule on a triangular lattice, where a cell has 9 corners and 3 edges.
    """
    hand = (G.MONOMINO,)
    s = G.BState(occ=(G._bit(9, 6), 0, 0, 0),
                 hands=(hand, G.PIECES, G.PIECES, G.PIECES),
                 to_move=0, last_key=("I6", None, None, None))
    diag = {(9 + dc, 6 + dr) for dc, dr in (G._DIAG_UP if G._up(9, 6) else G._DIAG_DOWN)}
    edge = set(G._adj(9, 6))
    assert len(diag) == 9 and len(edge) == 3
    assert all(G._onboard(*p) for p in diag | edge), "the probe must sit clear of the rim"

    got = {G._cells_of(G.MOVE_MASK[m])[0] for m in GAME.legal_moves(s)}
    assert got == diag, f"expected exactly the 9 corner cells, got {sorted(got)}"
    assert not (got & edge), "an edge neighbour was generated"
    print("  own colour: exactly the 9 corner cells, never the 3 edge cells OK")


def test_corner_and_edge_rules_over_real_moves():
    """The same invariant over a real seat-0 move list with a full hand."""
    s = GAME.initial_state()
    s = GAME.apply_move(s, _mono(9, 6))         # seat 0's single triangle
    own = s.occ[0]
    edge = set(G._adj(9, 6))
    diag = {(9 + dc, 6 + dr) for dc, dr in (G._DIAG_UP if G._up(9, 6) else G._DIAG_DOWN)}

    # Fast-forward the other seats onto their own start points.
    s2 = s
    for c, r in ((9, 11), (17, 14), (17, 3)):
        s2 = GAME.apply_move(s2, _mono(c, r))
    assert s2.to_move == 0
    taken = set(G._cells_of(s2.occ[0] | s2.occ[1] | s2.occ[2] | s2.occ[3]))
    moves = GAME.legal_moves(s2)
    assert moves
    for m in moves:
        cells = set(G._cells_of(G.MOVE_MASK[m]))
        assert cells & diag, f"{m}: no corner touch with own colour"
        assert not (cells & edge), f"{m}: shares an edge with own colour"
        assert not (cells & taken), f"{m}: overlaps"
        assert all(G._onboard(*p) for p in cells), f"{m}: off board"
    print("  corner/edge/overlap invariants hold over every generated move OK")


def test_blocked_seat_passes_and_moves_are_never_empty():
    """"A player MUST play if it is possible to play"; a blocked one is skipped."""
    import random
    rng = random.Random(11)
    s = GAME.initial_state()
    plies = 0
    while not GAME.is_terminal(s):
        moves = GAME.legal_moves(s)
        assert moves, "empty legal_moves on a non-terminal state"
        assert GAME._any_moves(s, s.to_move), "to_move cannot actually move"
        s = GAME.apply_move(s, rng.choice(moves))
        plies += 1
        assert plies < 4 * 22 + 1, "game did not terminate"
    assert not any(GAME._any_moves(s, i) for i in range(4)), "terminal but someone can move"
    assert GAME.legal_moves(s) == []
    print(f"  random game terminated in {plies} plies; blocked seats skipped OK")


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def test_scoring():
    """-1 per remaining unit triangle; +15 all placed; +5 more if the 1 was last."""
    s = GAME.initial_state()
    assert [GAME.score(s, i) for i in range(4)] == [-110] * 4, "nothing placed = -110"

    empty = G.BState(occ=(0, 0, 0, 0), hands=((), (), (), ()),
                     last_key=("1", "I6", "I6", "I6"))
    assert GAME.score(empty, 0) == 20, "all placed + monomino last = +20"
    assert GAME.score(empty, 1) == 15, "all placed = +15"

    one_left = G.BState(hands=(("I6",), ("1",), (), ()), last_key=(None, None, "O", None))
    assert GAME.score(one_left, 0) == -6, "one 6-triangle piece left = -6"
    assert GAME.score(one_left, 1) == -1, "one 1-triangle piece left = -1"
    assert GAME.score(one_left, 2) == 15, "all placed, last piece was not the 1"
    print("  scoring -1 / +15 / +5 OK")


def test_returns_ties_are_an_honest_draw():
    """rolit's convention: +1 to a SOLE leader, -1 to the rest; a tie = draw."""
    tie = G.BState(hands=((), (), (), ()), last_key=("I6",) * 4)
    assert GAME.is_terminal(tie)
    assert [GAME.score(tie, i) for i in range(4)] == [15] * 4
    assert GAME.returns(tie) == [0.0, 0.0, 0.0, 0.0], "4-way tie must be a draw"

    sole = G.BState(hands=((), (), (), ()), last_key=("I6", "1", "I6", "I6"))
    assert [GAME.score(sole, i) for i in range(4)] == [15, 20, 15, 15]
    assert GAME.returns(sole) == [-1.0, 1.0, -1.0, -1.0]

    # A tie FOR FIRST between two seats is still a draw — not a fabricated win.
    two = G.BState(hands=((), (), ("1",), ("1",)), last_key=("I6", "I6", "O", "O"))
    assert [GAME.score(two, i) for i in range(4)] == [15, 15, -1, -1]
    assert GAME.returns(two) == [0.0, 0.0, 0.0, 0.0], "tie for first must be a draw"
    print("  returns: sole leader +1 / rest -1; any tie for first is a draw OK")


def test_heuristic_is_per_seat_payoffs():
    """`heuristic` must return ONE payoff PER SEAT, like `returns`.

    MCTSBot._rollout hands the value straight to back-propagation, which indexes
    it as `payoffs[p]`; a bare float raises "'float' object is not subscriptable".
    A Trigon game runs ~65 plies, so the default max_rollout=50 cutoff DOES fire
    in normal play — this is a live path, not a theoretical one.
    """
    import random

    from agp.mcts import MCTSBot

    s = GAME.initial_state()
    for st in (s, GAME.apply_move(s, _mono(9, 6))):
        h = GAME.heuristic(st)
        assert isinstance(h, (list, tuple)), f"heuristic must be a list, got {type(h).__name__}"
        assert len(h) == GAME.num_players, f"heuristic len {len(h)} != 4 seats"
        assert all(isinstance(x, float) and -1.0 <= x <= 1.0 for x in h), h
    assert GAME.heuristic(s) == [0.0, 0.0, 0.0, 0.0], GAME.heuristic(s)
    # Force the rollout cutoff.
    mv = MCTSBot(random.Random(1), iterations=8, max_rollout=3).select(GAME, s)
    assert mv in GAME.legal_moves(s), mv
    print("  heuristic returns per-seat payoffs; MCTS survives the rollout cutoff OK")


# --------------------------------------------------------------------------
# Plumbing
# --------------------------------------------------------------------------

def test_serialization_roundtrip():
    import json
    import random
    rng = random.Random(5)
    s = GAME.initial_state()
    for _ in range(6):
        s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
    d = json.loads(json.dumps(GAME.serialize(s)))
    t = GAME.deserialize(d)
    assert t.occ == s.occ and t.hands == s.hands and t.to_move == s.to_move
    assert set(t.last) == set(s.last) and t.last_key == s.last_key
    assert GAME.legal_moves(t) == GAME.legal_moves(s)
    print("  serialize/deserialize roundtrip OK")


def test_render_shape():
    """A RenderSpec format bug white-screens the board and is invisible to
    `validate`, so check the polygons contract explicitly: `cells` is a LIST of
    {id, points} (NOT a dict, and the key is `points`, not `polygon`)."""
    import json
    s = GAME.initial_state()
    spec = GAME.render(s)
    b = spec["board"]
    assert b["type"] == "polygons"
    assert isinstance(b["cells"], list), "board.cells must be a LIST"
    assert len(b["cells"]) == 486
    ids = set()
    for cell in b["cells"]:
        assert set(cell) == {"id", "points"}, cell.keys()
        c, r = (int(x) for x in cell["id"].split(","))       # ids MUST be numeric
        assert G._onboard(c, r)
        assert len(cell["points"]) == 3, "a triangle has 3 vertices"
        assert all(len(p) == 2 for p in cell["points"])
        ids.add(cell["id"])
    assert len(ids) == 486
    for seat in range(4):
        tiles = spec["palette"][str(seat)]
        assert len(tiles) == 22
        for t in tiles:
            assert t["grid"] == "tri"
            assert len(t["parity"]) == len(t["orients"])
            assert ":" not in t["key"] and "@" not in t["key"]
    assert set(b["tints"]) <= ids
    json.dumps(spec)
    print("  render: polygons cells LIST + `points` key + tri palette OK")


def test_describe_move():
    s = GAME.initial_state()
    # Pentobi's bijective base-26 column names: 0->a, 25->z, 26->aa, 34->ai.
    assert G._coord_name(0) == "a" and G._coord_name(25) == "z"
    assert G._coord_name(26) == "aa" and G._coord_name(34) == "ai"
    assert GAME.describe_move(s, "1:0@17,14") == "1@r15"
    print("  describe_move / coordinate names OK")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"blokus_trigon selftest: {len(fns)} checks passed")
