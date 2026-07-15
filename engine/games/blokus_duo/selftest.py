"""Blokus Duo selftest — pure stdlib (agp + this game only).

Primary anchor: the opening legal-move set, cross-checked against Pentobi
(Markus Enzenberger's reference Blokus engine, `pentobi-gtp`: `set_game blokus
duo` + `all_legal b`), which reports **414** legal first moves with the size
distribution {1: 1, 2: 4, 3: 18, 4: 76, 5: 315}.

That distribution is also derivable by hand, which is why it pins the
orientation enumeration so tightly: the start point (4,9) has at least 4 cells
of margin on every side and no piece reaches more than 4 cells from any of its
own cells, so *every* (orientation, covered-cell) pair fits on the board.
Hence the count is exactly sum(fixed orientations x size) over the piece set:
  1x1 + 2x2 + 6x3 + 19x4 + 63x5 = 1 + 4 + 18 + 76 + 315 = 414
(1, 2, 6, 19, 63 being the number of fixed polyominoes of size 1..5). A missing
or spurious reflection/rotation for any piece moves its size bucket off.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Import through the canonical package path (as games/domineering/selftest.py
# does). Importing the bare `game` module instead would load a SECOND copy
# alongside the one agp.loader registers under its own synthetic module name,
# duplicating the placement tables and making `type(state) is BState` false.
import games.blokus_duo.game as G  # noqa: E402

GAME = G.BlokusDuo()


def _size_of(move):
    return G.SIZES[move.split(":", 1)[0]]


def _covers(move, cell):
    return bool(G.MOVE_MASK[move] & G._bit(*cell))


def _move_for(key, cells):
    """The move string that places `key` covering exactly `cells`.

    Resolves the orientation index by shape, so these tests never depend on the
    order `_orients()` happens to emit.
    """
    norm = [list(x) for x in G._normalize(cells)]
    ar, ac = min((r, c) for c, r in cells)   # anchor: bottom-most, then left-most
    for i, o in enumerate(G.ORIENTS[key]):
        if o == norm:
            mv = f"{key}:{i}@{ac},{ar}"
            assert G.MOVE_MASK[mv] == sum(G._bit(c, r) for c, r in cells)
            return mv
    raise AssertionError(f"{key} has no orientation matching {sorted(cells)}")


def test_piece_set():
    """21 free polyominoes of size 1..5, split 1/1/2/5/12."""
    assert len(G.PIECES) == 21, len(G.PIECES)
    assert len(set(G.PIECES)) == 21
    split = {}
    for k in G.PIECES:
        split[G.SIZES[k]] = split.get(G.SIZES[k], 0) + 1
    assert split == {1: 1, 2: 1, 3: 2, 4: 5, 5: 12}, split

    # The named table is exactly the set of free polyominoes of size 1..5
    # (game.py asserts this at import; re-assert independently here).
    gen = set()
    for n in (1, 2, 3, 4, 5):
        gen |= G._free_polyominoes(n)
    assert {G._canonical(v) for v in G._NAMED.values()} == gen
    assert len(gen) == 21

    # Rotations AND reflections allowed => the orientation counts are the FIXED
    # polyomino counts: 1, 2, 6, 19, 63 by size. (One-sided would total 29
    # pieces, not 21 — this is the distinguishing check.)
    per_size = {}
    for k in G.PIECES:
        per_size[G.SIZES[k]] = per_size.get(G.SIZES[k], 0) + len(G.ORIENTS[k])
    assert per_size == {1: 1, 2: 2, 3: 6, 4: 19, 5: 63}, per_size

    # Spot-check specific orientation counts (X5 is 4-fold symmetric => 1;
    # I5 => 2; F5 is chiral with no symmetry => 8; O4 square => 1).
    assert len(G.ORIENTS["X5"]) == 1
    assert len(G.ORIENTS["I5"]) == 2
    assert len(G.ORIENTS["F5"]) == 8
    assert len(G.ORIENTS["O4"]) == 1
    assert len(G.ORIENTS["Z5"]) == 4

    # ANCHOR CONTRACT (SPEC): the anchor must be a cell the tile covers, so
    # every orientation contains [0,0] — otherwise you click a square up to two
    # cells away from where the piece lands. `dr` >= 0 (the anchor is the
    # bottom-most cell) and, among the bottom row, the anchor is left-most.
    for k in G.PIECES:
        for o in G.ORIENTS[k]:
            assert [0, 0] in o, f"{k}: orientation {o} does not cover its anchor"
            assert all(dr >= 0 for _, dr in o), f"{k}: {o} has a cell below the anchor"
            assert all(dc >= 0 for dc, dr in o if dr == 0), \
                f"{k}: {o} has a bottom-row cell left of the anchor"
            assert len({tuple(x) for x in o}) == len(o), f"{k}: duplicate cell in {o}"
    print("  piece set: 21 pieces, split 1/1/2/5/12, 91 orientations OK")
    print("  anchor contract: every orientation covers its anchor [0,0] OK")


def test_opening_anchor():
    """Pentobi ground truth: 414 opening moves, {1:1, 2:4, 3:18, 4:76, 5:315}."""
    s = GAME.initial_state()
    moves = GAME.legal_moves(s)
    dist = {}
    for m in moves:
        n = _size_of(m)
        dist[n] = dist.get(n, 0) + 1
    assert dist == {1: 1, 2: 4, 3: 18, 4: 76, 5: 315}, dist
    assert len(moves) == 414, len(moves)
    assert len(set(moves)) == 414, "duplicate moves generated"

    # Every opening move covers the start point.
    for m in moves:
        assert _covers(m, G.START[0]), m

    # Every generated move's ANCHOR is on-board and is a cell the piece covers
    # (the end-to-end form of the anchor contract: what you click is what you
    # get). Checked here on the widest move set, and over full games below.
    for m in moves:
        c, r = (int(x) for x in m.split("@", 1)[1].split(","))
        assert 0 <= c < 14 and 0 <= r < 14, f"{m}: anchor off-board"
        assert _covers(m, (c, r)), f"{m}: anchor {(c, r)} is not covered by the piece"

    # Player 2's opening (after any player-1 move) is the mirror-image count:
    # their start point is equally far from every edge, and player 1's first
    # piece is far away, so it is also 414.
    s2 = GAME.apply_move(s, _move_for("I1", [(4, 9)]))
    assert GAME.current_player(s2) == 1
    m2 = GAME.legal_moves(s2)
    assert len(m2) == 414, len(m2)
    for m in m2:
        assert _covers(m, G.START[1]), m
    print("  opening: 414 moves, {1:1, 2:4, 3:18, 4:76, 5:315} (Pentobi) OK")


def test_first_move_must_cover_start():
    s = GAME.initial_state()
    legal = set(GAME.legal_moves(s))
    # A monomino on the start point is legal; anywhere else is not.
    assert _move_for("I1", [(4, 9)]) in legal
    for cell in ((0, 0), (5, 9), (4, 8), (9, 4), (7, 7)):
        bad = _move_for("I1", [cell])
        assert bad not in legal, bad
        try:
            GAME.apply_move(s, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"apply_move accepted illegal first move {bad}")
    print("  first piece must cover the start point OK")


def test_corner_yes_edge_no():
    """Concrete positions for the two core placement rules."""
    s = GAME.initial_state()
    s = GAME.apply_move(s, _move_for("I1", [(4, 9)]))   # P1 on its start point
    s = GAME.apply_move(s, _move_for("I1", [(9, 4)]))   # P2 on its start point
    assert GAME.current_player(s) == 0
    legal = set(GAME.legal_moves(s))

    # P1 has a single square at (4,9).
    # CORNER touch, no edge contact -> LEGAL. Each of the four diagonal
    # neighbours of (4,9), extended away from it, is a legal domino.
    for cells in ([(5, 10), (6, 10)],    # up-right, running right
                  [(3, 10), (2, 10)],    # up-left, running left
                  [(5, 8), (6, 8)],      # down-right
                  [(3, 8), (2, 8)]):     # down-left
        mv = _move_for("I2", cells)
        assert mv in legal, f"corner-touching domino {cells} should be legal"

    # EDGE contact with own colour -> ILLEGAL (each of these also corner-touches
    # or is adjacent, but a shared edge with your own colour vetoes it).
    for cells in ([(5, 9), (6, 9)],      # (5,9) shares an edge with (4,9)
                  [(4, 10), (4, 11)],    # (4,10) shares an edge with (4,9)
                  [(4, 8), (4, 7)],      # (4,8) shares an edge with (4,9)
                  [(3, 9), (2, 9)]):     # (3,9) shares an edge with (4,9)
        mv = _move_for("I2", cells)
        assert mv not in legal, f"edge-touching domino {cells} must be illegal"

    # Overlap -> ILLEGAL.
    assert _move_for("I2", [(4, 9), (5, 9)]) not in legal

    # NO contact at all with own colour -> ILLEGAL (must touch at a corner).
    for cells in ([(0, 0), (1, 0)], [(7, 7), (8, 7)], [(6, 11), (7, 11)]):
        assert _move_for("I2", cells) not in legal, f"detached domino {cells}"

    # apply_move independently rejects each class of illegal move.
    for cells in ([(5, 9), (6, 9)], [(4, 10), (4, 11)], [(0, 0), (1, 0)],
                  [(4, 9), (5, 9)]):
        try:
            GAME.apply_move(s, _move_for("I2", cells))
        except ValueError:
            pass
        else:
            raise AssertionError(f"apply_move accepted illegal placement {cells}")

    # A corner touch counts even for a piece that only grazes one cell: the
    # X5 pentomino centred so that just one of its arms diagonally meets (4,9).
    mv = _move_for("X5", [(6, 11), (5, 10), (6, 10), (7, 10), (6, 9)])
    assert mv in legal, "X5 cornering (4,9) at (5,10) should be legal"
    print("  corner-touch legal / same-colour edge-touch illegal OK")


def test_opponent_edge_contact_is_legal():
    """"There are no restrictions on how pieces of different colours may
    contact each other" — an A/B test isolating exactly the colour distinction.

    Same board, same placement; only the OWNER of the neighbouring square
    differs. Constructed directly: this tests the placement predicate.
    """
    rest = tuple(k for k in G.PIECES if k != "I1")
    place = _move_for("I2", [(5, 10), (5, 11)])   # corners P1's (4,9)

    # A: the square at (6,10) belongs to the OPPONENT. The domino at
    # (5,10)-(5,11) shares an edge with it -> still LEGAL.
    a = G.BState(occ=(G._bit(4, 9), G._bit(6, 10)),
                 hands=(rest, rest), to_move=0, last=(), last_key=("I1", "I1"))
    assert G._edge_zone(G._bit(5, 10)) & a.occ[1], "sanity: does touch P2's square"
    assert place in set(GAME.legal_moves(a)), \
        "edge contact with a DIFFERENT colour must be allowed"
    GAME.apply_move(a, place)   # must not raise

    # B: the identical square at (6,10) belongs to US -> now ILLEGAL.
    b = G.BState(occ=(G._bit(4, 9) | G._bit(6, 10), 0),
                 hands=(rest, G.PIECES), to_move=0, last=(), last_key=("I1", None))
    assert place not in set(GAME.legal_moves(b)), \
        "edge contact with your OWN colour must be forbidden"
    try:
        GAME.apply_move(b, place)
    except ValueError:
        pass
    else:
        raise AssertionError("apply_move allowed same-colour edge contact")
    print("  different colours may touch along an edge (A/B) OK")


def test_scoring():
    """The rulebook's own worked example, plus both bonuses."""
    S = GAME

    def st(hand0, hand1, last0=None, last1=None):
        return G.BState(occ=(0, 0), hands=(tuple(hand0), tuple(hand1)),
                        to_move=0, last=(), last_key=(last0, last1))

    # Rulebook example (Blokus Duo, "A COMPLETED GAME"):
    #  - black could not place 2 three-square pieces and 1 four-square piece: -10
    assert S.score(st(["I3", "V3", "O4"], []), 0) == -10
    #  - white placed all 21 and played the smallest piece last: +20
    assert S.score(st([], [], None, "I1"), 1) == 20

    # +15 for placing everything, without the monomino-last bonus.
    assert S.score(st([], [], None, "P5"), 1) == 15
    # -1 per remaining unit square.
    assert S.score(st(["I1"], []), 0) == -1
    assert S.score(st(["I5"], []), 0) == -5
    assert S.score(st(["I5", "F5", "X5"], []), 0) == -15
    # Every piece left = -(1+2+3+3+4*5+5*12) = -89.
    assert S.score(st(list(G.PIECES), []), 0) == -(1 + 2 + 3 + 3 + 4 * 5 + 5 * 12)
    assert S.score(st(list(G.PIECES), []), 0) == -89
    # The +5 requires the +15: monomino played last but pieces still in hand
    # earns no bonus (documented interpretation).
    assert S.score(st(["I5"], [], "I1"), 0) == -5
    print("  scoring: -10 / +15 / +20 rulebook examples OK")


def test_honest_draw_on_tie():
    """Equal scores are a DRAW, not a fabricated win."""
    # A completely full board: no empty cell anywhere, so neither player can
    # place and the position is terminal. Give both the same remaining pieces.
    full = G.FULL
    half = 0
    for r in range(G.H):
        for c in range(G.W):
            if (c + r) % 2 == 0:
                half |= G._bit(c, r)
    s = G.BState(occ=(half, full & ~half),
                 hands=(("I3", "V3", "O4"), ("I3", "V3", "O4")),
                 to_move=0, last=(), last_key=("P5", "P5"))
    assert GAME.is_terminal(s), "full board must be terminal"
    assert GAME.score(s, 0) == -10 and GAME.score(s, 1) == -10
    assert GAME.returns(s) == [0.0, 0.0], GAME.returns(s)

    # And a genuine 1-point edge is a win, so the draw is not blanket behaviour.
    s2 = G.BState(occ=(half, full & ~half),
                  hands=(("I3",), ("O4",)), to_move=0, last=(), last_key=(None, None))
    assert GAME.score(s2, 0) == -3 and GAME.score(s2, 1) == -4
    assert GAME.returns(s2) == [1.0, -1.0]
    s3 = G.BState(occ=(half, full & ~half),
                  hands=(("O4",), ("I3",)), to_move=0, last=(), last_key=(None, None))
    assert GAME.returns(s3) == [-1.0, 1.0]
    print("  honest draw on a tie / win on a 1-point edge OK")


def test_pass_and_termination():
    """A blocked player is skipped; the game ends when both are blocked."""
    # Box player 2 in completely: fill everything except a pocket that only
    # player 1 can use. Simpler: verify the skip logic directly. Player 2 has
    # placed nothing and its start point is covered by player 1 -> P2 can never
    # move, so after P1's move the turn must come back to P1.
    covered = G._bit(*G.START[1])
    s = G.BState(occ=(covered, 0), hands=(tuple(k for k in G.PIECES if k != "I1"), G.PIECES),
                 to_move=0, last=(), last_key=("I1",))
    assert not GAME._any_moves(s, 1), "P2's start point is covered -> no moves"
    assert GAME._any_moves(s, 0)
    assert not GAME.is_terminal(s)
    nxt = GAME.apply_move(s, GAME.legal_moves(s)[0])
    assert nxt.to_move == 0, "blocked P2 must be skipped, not given the turn"

    # legal_moves is never empty on a non-terminal state.
    s = GAME.initial_state()
    for _ in range(40):
        if GAME.is_terminal(s):
            break
        mv = GAME.legal_moves(s)
        assert mv, "empty legal_moves on a non-terminal state"
        s = GAME.apply_move(s, mv[0])
    print("  blocked player skipped; legal_moves never empty OK")


def test_full_game_terminates():
    """Play a deterministic game to the end and check the invariants."""
    import random
    rng = random.Random(12345)
    s = GAME.initial_state()
    plies = 0
    while not GAME.is_terminal(s):
        mv = GAME.legal_moves(s)
        assert mv
        s = GAME.apply_move(s, rng.choice(mv))
        plies += 1
        assert plies <= 42, "more plies than pieces exist"
    # Board never over-filled; the two colours never overlap.
    assert not (s.occ[0] & s.occ[1]), "colours overlap"
    placed0 = bin(s.occ[0]).count("1")
    placed1 = bin(s.occ[1]).count("1")
    assert placed0 == sum(G.SIZES[k] for k in G.PIECES) - sum(G.SIZES[k] for k in s.hands[0])
    assert placed1 == sum(G.SIZES[k] for k in G.PIECES) - sum(G.SIZES[k] for k in s.hands[1])
    r = GAME.returns(s)
    assert sorted(r) in ([-1.0, 1.0], [0.0, 0.0]), r
    # Round-trip through serialization.
    s2 = GAME.deserialize(GAME.serialize(s))
    assert s2.occ == s.occ and s2.hands == s.hands and s2.to_move == s.to_move
    assert GAME.returns(s2) == r
    print(f"  random game: {plies} plies, "
          f"P1 {GAME.score(s, 0):+d} / P2 {GAME.score(s, 1):+d}, serialization OK")


def test_render_shape():
    s = GAME.initial_state()
    v = GAME.render(s)
    assert v["board"]["type"] == "square"
    assert v["board"]["width"] == 14 and v["board"]["height"] == 14
    pal = v["palette"]
    assert set(pal) == {"0", "1"}
    assert len(pal["0"]) == 21 and len(pal["1"]) == 21
    for t in pal["0"]:
        assert set(t) >= {"key", "orients"}
        assert ":" not in t["key"] and "@" not in t["key"]
        for o in t["orients"]:
            assert all(isinstance(x, list) and len(x) == 2 for x in o)
    # Both start points tinted while uncovered.
    assert v["board"]["tints"] == {"4,9": "#c8b88a", "9,4": "#c8b88a"}
    # After a placement the palette shrinks and the piece renders.
    s = GAME.apply_move(s, _move_for("I1", [(4, 9)]))
    v = GAME.render(s)
    assert len(v["palette"]["0"]) == 20
    assert {"cell": "4,9", "owner": 0} in v["pieces"]
    assert "4,9" not in v["board"]["tints"]
    print("  render: board/palette/tints shape OK")


if __name__ == "__main__":
    test_piece_set()
    test_opening_anchor()
    test_first_move_must_cover_start()
    test_corner_yes_edge_no()
    test_opponent_edge_contact_is_legal()
    test_scoring()
    test_honest_draw_on_tie()
    test_pass_and_termination()
    test_full_game_terminates()
    test_render_shape()
    print("blokus_duo selftest: all OK")
