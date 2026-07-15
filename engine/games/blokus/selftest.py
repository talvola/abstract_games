"""Blokus selftest — pure stdlib (agp + this game only).

Primary anchor: the opening legal-move set, cross-checked against Pentobi
(Markus Enzenberger's reference Blokus engine, `pentobi-gtp`: `set_game blokus`
+ `all_legal <1|2|3|4>`), which reports **58** legal first moves for EVERY
colour, with the size distribution {1: 1, 2: 2, 3: 5, 4: 13, 5: 37}.

Pentobi also pins the corner each colour starts on — 1=a20, 2=t20, 3=t1, 4=a1,
i.e. our seats 0..3 at (0,19), (19,19), (19,0), (0,0).

The distribution is the valuable part: it pins the orientation enumeration per
piece SIZE, so a missing/spurious rotation or reflection lands in the wrong
bucket instead of merely shifting the total. Unlike Duo's centre-ish start
point, a corner clips most orientations against two board edges, which is why
58 is far below Duo's 414 — every placement must both cover the corner cell and
fit inside the quarter-plane from it.

A full Pentobi differential over complete games lives in `_diff_pentobi.py`
(manual/one-time; it needs the external pentobi-gtp binary, so it is
deliberately not part of this pure-stdlib selftest).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Import through the canonical package path (as games/blokus_duo/selftest.py
# does). Importing the bare `game` module instead would load a SECOND copy
# alongside the one agp.loader registers under its own synthetic module name,
# duplicating the placement tables and making `type(state) is BState` false.
import games.blokus.game as G  # noqa: E402

GAME = G.Blokus()


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
    """21 free polyominoes of size 1..5, split 1/1/2/5/12; 84 pieces over 4 colours."""
    assert len(G.PIECES) == 21, len(G.PIECES)
    assert len(set(G.PIECES)) == 21
    split = {}
    for k in G.PIECES:
        split[G.SIZES[k]] = split.get(G.SIZES[k], 0) + 1
    assert split == {1: 1, 2: 1, 3: 2, 4: 5, 5: 12}, split

    # "84 pieces in four different colours (21 pieces per colour)" (R1983).
    assert len(G.PIECES) * G.N_SEATS == 84
    # "a board of 400 squares".
    assert G.W == 20 and G.H == 20 and G.N_CELLS == 400

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
    print("  piece set: 21 pieces x 4 colours = 84, split 1/1/2/5/12, 91 orientations OK")
    print("  anchor contract: every orientation covers its anchor [0,0] OK")


def test_opening_anchor():
    """Pentobi ground truth: 58 opening moves for EVERY seat, {1:1,2:2,3:5,4:13,5:37}.

    The centrepiece anchor. Checked for all four seats — they are symmetric
    (each corner is equivalent under the board's dihedral symmetry), so all four
    must give the identical count and split.
    """
    s = GAME.initial_state()
    for seat in range(4):
        moves = list(GAME._gen(s, seat))
        dist = {}
        for m in moves:
            n = _size_of(m)
            dist[n] = dist.get(n, 0) + 1
        assert dist == {1: 1, 2: 2, 3: 5, 4: 13, 5: 37}, (seat, dist)
        assert len(moves) == 58, (seat, len(moves))
        assert len(set(moves)) == 58, f"seat {seat}: duplicate moves generated"

        # Every opening move covers THIS seat's own corner.
        for m in moves:
            assert _covers(m, G.START[seat]), (seat, m)

        # Every generated move's ANCHOR is on-board and is a cell the piece
        # covers (the end-to-end form of the anchor contract: what you click is
        # what you get).
        for m in moves:
            c, r = (int(x) for x in m.split("@", 1)[1].split(","))
            assert 0 <= c < G.W and 0 <= r < G.H, f"{m}: anchor off-board"
            assert _covers(m, (c, r)), f"{m}: anchor {(c, r)} is not covered"

    # And the seat to move at the start actually sees its own 58.
    assert GAME.current_player(s) == 0
    assert len(GAME.legal_moves(s)) == 58
    print("  opening: 58 moves x 4 seats, {1:1, 2:2, 3:5, 4:13, 5:37} (Pentobi) OK")


def test_start_corners():
    """Each seat owns one corner; play order 0->1->2->3 is clockwise (Pentobi)."""
    # Pentobi: colour 1=a20, 2=t20, 3=t1, 4=a1 -> our bottom-origin (col,row).
    assert G.START == ((0, 19), (19, 19), (19, 0), (0, 0)), G.START
    # All four are genuine board corners, and all distinct.
    corners = {(0, 0), (0, G.H - 1), (G.W - 1, 0), (G.W - 1, G.H - 1)}
    assert set(G.START) == corners
    assert len(set(G.START)) == 4
    print("  start corners: seats 0-3 at a20/t20/t1/a1, clockwise (Pentobi) OK")


def test_first_move_must_cover_own_corner():
    """A seat's first piece must cover ITS OWN corner — not just any corner.

    The rule most likely to be mis-ported to 4 players: another seat's corner,
    or a bare corner-adjacent cell, must both be rejected.
    """
    s = GAME.initial_state()
    for seat in range(4):
        legal = set(GAME._gen(s, seat))
        # A monomino on your OWN corner is legal.
        assert _move_for("I1", [G.START[seat]]) in legal, seat
        # ...on ANY OTHER seat's corner it is not.
        for other in range(4):
            if other == seat:
                continue
            bad = _move_for("I1", [G.START[other]])
            assert bad not in legal, f"seat {seat} accepted seat {other}'s corner"
        # ...nor anywhere else on the board.
        for cell in ((1, 1), (10, 10), (0, 18), (1, 19), (19, 1)):
            assert _move_for("I1", [cell]) not in legal, (seat, cell)

    # apply_move independently rejects a first move that misses seat 0's corner.
    for cell in ((19, 19), (19, 0), (0, 0), (10, 10), (1, 19)):
        try:
            GAME.apply_move(s, _move_for("I1", [cell]))
        except ValueError:
            pass
        else:
            raise AssertionError(f"apply_move accepted illegal first move at {cell}")
    print("  first piece must cover the seat's OWN corner (all 4 seats) OK")


def test_corner_yes_edge_no():
    """Concrete positions for the two core placement rules (own colour)."""
    s = GAME.initial_state()
    # Each seat drops its monomino on its own corner.
    for seat in range(4):
        s = GAME.apply_move(s, _move_for("I1", [G.START[seat]]))
    assert GAME.current_player(s) == 0
    legal = set(GAME.legal_moves(s))

    # Seat 0 has a single square at (0,19) — the TOP-LEFT corner, so its only
    # free diagonal is down-right, at (1,18).
    # CORNER touch, no edge contact -> LEGAL.
    for cells in ([(1, 18), (2, 18)], [(1, 18), (1, 17)]):
        mv = _move_for("I2", cells)
        assert mv in legal, f"corner-touching domino {cells} should be legal"

    # EDGE contact with own colour -> ILLEGAL.
    for cells in ([(1, 19), (2, 19)],     # (1,19) shares an edge with (0,19)
                  [(0, 18), (0, 17)],     # (0,18) shares an edge with (0,19)
                  [(0, 18), (1, 18)]):    # ditto, running right
        mv = _move_for("I2", cells)
        assert mv not in legal, f"edge-touching domino {cells} must be illegal"

    # Overlap -> ILLEGAL.
    assert _move_for("I2", [(0, 19), (1, 19)]) not in legal

    # NO contact at all with own colour -> ILLEGAL (must touch at a corner).
    for cells in ([(10, 10), (11, 10)], [(3, 16), (4, 16)], [(2, 17), (3, 17)]):
        assert _move_for("I2", cells) not in legal, f"detached domino {cells}"

    # apply_move independently rejects each class of illegal move.
    for cells in ([(1, 19), (2, 19)], [(0, 18), (0, 17)], [(10, 10), (11, 10)],
                  [(0, 19), (1, 19)]):
        try:
            GAME.apply_move(s, _move_for("I2", cells))
        except ValueError:
            pass
        else:
            raise AssertionError(f"apply_move accepted illegal placement {cells}")

    # A corner touch counts even for a piece that only grazes one cell: the X5
    # plus-pentomino centred at (2,18), so only its left arm (1,18) diagonally
    # meets (0,19) and nothing shares an edge with it. ((0,19) is a board corner,
    # so (1,18) is its ONLY diagonal neighbour.)
    mv = _move_for("X5", [(2, 19), (1, 18), (2, 18), (3, 18), (2, 17)])
    assert mv in legal, "X5 cornering (0,19) at (1,18) should be legal"
    print("  corner-touch legal / same-colour edge-touch illegal OK")


def test_other_colour_edge_contact_is_legal():
    """"There are no restrictions on how pieces of different colours may contact
    each other" — the rule most likely to be wrong in a 4-player port.

    A/B test isolating exactly the colour distinction: same board, same
    placement; only the OWNER of the neighbouring square differs. Run for every
    other seat, so a bug that leaks any single opponent's colour into the
    edge/corner test is caught.
    """
    rest = tuple(k for k in G.PIECES if k != "I1")
    place = _move_for("I2", [(1, 18), (1, 17)])   # corners seat 0's (0,19)
    mine = G._bit(*G.START[0])
    neighbour = G._bit(2, 18)                     # shares an edge with (1,18)
    assert G._edge_zone(G._bit(1, 18)) & neighbour, "sanity: the square does touch"

    # A: that neighbouring square belongs to ANOTHER seat -> still LEGAL,
    # for each of the three other colours in turn.
    for other in (1, 2, 3):
        occ = [0, 0, 0, 0]
        occ[0] = mine
        occ[other] = neighbour
        hands = [G.PIECES] * 4
        hands[0] = rest
        hands[other] = rest
        lk = [None] * 4
        lk[0] = lk[other] = "I1"
        a = G.BState(occ=tuple(occ), hands=tuple(hands), to_move=0,
                     last=(), last_key=tuple(lk))
        assert place in set(GAME.legal_moves(a)), \
            f"edge contact with seat {other}'s colour must be allowed"
        GAME.apply_move(a, place)   # must not raise

    # A2: an opponent square that merely CORNERS us gives no corner-touch right —
    # only our OWN colour does. Seat 0 owns nothing adjacent here.
    b = G.BState(occ=(G._bit(0, 0), G._bit(5, 5), 0, 0),
                 hands=(rest, rest, G.PIECES, G.PIECES), to_move=0,
                 last=(), last_key=("I1", "I1", None, None))
    assert _move_for("I2", [(6, 6), (7, 6)]) not in set(GAME.legal_moves(b)), \
        "cornering an OPPONENT's piece must not satisfy the corner-touch rule"

    # B: the identical square at (2,18) belongs to US -> now ILLEGAL.
    c = G.BState(occ=(mine | neighbour, 0, 0, 0),
                 hands=(rest, G.PIECES, G.PIECES, G.PIECES), to_move=0,
                 last=(), last_key=("I1", None, None, None))
    assert place not in set(GAME.legal_moves(c)), \
        "edge contact with your OWN colour must be forbidden"
    try:
        GAME.apply_move(c, place)
    except ValueError:
        pass
    else:
        raise AssertionError("apply_move allowed same-colour edge contact")

    # C: an opponent square may not be OVERLAPPED, though.
    d = G.BState(occ=(mine, G._bit(1, 18), 0, 0),
                 hands=(rest, rest, G.PIECES, G.PIECES), to_move=0,
                 last=(), last_key=("I1", "I1", None, None))
    assert place not in set(GAME.legal_moves(d)), "must not overlap another colour"
    print("  different colours may touch along an edge (A/B, all 3 opponents) OK")


def test_scoring():
    """The rulebook's own worked example (figure 5), plus both bonuses."""
    S = GAME

    def st(hands, last=(None, None, None, None)):
        return G.BState(occ=(0, 0, 0, 0), hands=tuple(tuple(h) for h in hands),
                        to_move=0, last=(), last_key=tuple(last))

    # R1983 figure 5, the completed game it prints scores for:
    #   blue placed all his/her pieces, smallest piece last          -> +20
    #   yellow could not place 2 four-square pieces                  ->  -8
    #   red could not place 1 three-square, 4 four-square,
    #       1 five-square piece                                      -> -24
    #   green could not place 1 three-square, 3 four-square,
    #       1 five-square piece                                      -> -20
    s = st([[],                                    # blue: everything placed
            ["I4", "L4"],                          # yellow: 2 x 4 squares = -8
            ["I3", "I4", "L4", "N4", "T4", "I5"],  # red: 3+16+5 = -24
            ["V3", "I4", "L4", "N4", "I5"]],       # green: 3+12+5 = -20
           last=("I1", "O4", "O4", "O4"))
    assert S.score(s, 0) == 20, S.score(s, 0)
    assert S.score(s, 1) == -8, S.score(s, 1)
    assert S.score(s, 2) == -24, S.score(s, 2)
    assert S.score(s, 3) == -20, S.score(s, 3)

    # +15 for placing everything, without the monomino-last bonus.
    assert S.score(st([[], [], [], []], ("P5", None, None, None)), 0) == 15
    # -1 per remaining unit square.
    assert S.score(st([["I1"], [], [], []]), 0) == -1
    assert S.score(st([["I5"], [], [], []]), 0) == -5
    assert S.score(st([["I5", "F5", "X5"], [], [], []]), 0) == -15
    # Every piece left = -(1+2+3+3+4*5+5*12) = -89.
    assert S.score(st([list(G.PIECES), [], [], []]), 0) == -89
    # The +5 requires the +15: monomino played last but pieces still in hand
    # earns no bonus (documented interpretation).
    assert S.score(st([["I5"], [], [], []], ("I1", None, None, None)), 0) == -5
    print("  scoring: rulebook figure-5 example +20/-8/-24/-20 OK")


def test_honest_draw_on_tie():
    """A tie for FIRST is a draw; a sole leader wins (rolit convention)."""
    # A completely full board -> nobody can place -> terminal. Split it into
    # four quarters so every seat owns cells and no seat can move.
    def quarters():
        occ = [0, 0, 0, 0]
        for r in range(G.H):
            for c in range(G.W):
                q = (0 if r >= 10 else 2) + (0 if c < 10 else 1)
                # q: 0=top-left,1=top-right,2=bottom-left,3=bottom-right
                seat = {0: 0, 1: 1, 2: 3, 3: 2}[q]
                occ[seat] |= G._bit(c, r)
        return tuple(occ)

    occ = quarters()
    assert occ[0] | occ[1] | occ[2] | occ[3] == G.FULL, "quarters must fill the board"

    # 4-WAY TIE -> honest draw, [0,0,0,0].
    s = G.BState(occ=occ, hands=(("I3",), ("I3",), ("I3",), ("I3",)),
                 to_move=0, last=(), last_key=("P5",) * 4)
    assert GAME.is_terminal(s), "full board must be terminal"
    assert [GAME.score(s, p) for p in range(4)] == [-3, -3, -3, -3]
    assert GAME.returns(s) == [0.0, 0.0, 0.0, 0.0], GAME.returns(s)

    # A PARTIAL tie for first (2 seats lead) is also a draw — no fabricated
    # tiebreak between the co-leaders.
    s2 = G.BState(occ=occ, hands=(("I3",), ("I3",), ("I5",), ("I5",)),
                  to_move=0, last=(), last_key=("P5",) * 4)
    assert [GAME.score(s2, p) for p in range(4)] == [-3, -3, -5, -5]
    assert GAME.returns(s2) == [0.0, 0.0, 0.0, 0.0], GAME.returns(s2)

    # A SOLE leader wins: +1 to them, -1 to the other three. Checked for each
    # seat in turn, so the draw is not blanket behaviour.
    for winner in range(4):
        hands = [("I5",)] * 4
        hands[winner] = ("I3",)          # -3 beats -5
        s3 = G.BState(occ=occ, hands=tuple(hands), to_move=0,
                      last=(), last_key=("P5",) * 4)
        exp = [1.0 if i == winner else -1.0 for i in range(4)]
        assert GAME.returns(s3) == exp, (winner, GAME.returns(s3))

    # A 1-point edge is enough.
    s4 = G.BState(occ=occ, hands=(("I3",), ("O4",), ("O4",), ("O4",)),
                  to_move=0, last=(), last_key=("P5",) * 4)
    assert [GAME.score(s4, p) for p in range(4)] == [-3, -4, -4, -4]
    assert GAME.returns(s4) == [1.0, -1.0, -1.0, -1.0]
    print("  honest draw on a tie for first / sole leader wins OK")


def test_pass_and_termination():
    """A blocked seat is skipped; the game ends when ALL seats are blocked."""
    # Cover seats 1..3's corners with seat 0's colour: they can never place, so
    # after seat 0 moves the turn must come straight back to seat 0.
    covered = G._bit(*G.START[1]) | G._bit(*G.START[2]) | G._bit(*G.START[3])
    s = G.BState(occ=(covered | G._bit(*G.START[0]), 0, 0, 0),
                 hands=(tuple(k for k in G.PIECES if k not in ("I1", "V3")),
                        G.PIECES, G.PIECES, G.PIECES),
                 to_move=0, last=(), last_key=("V3", None, None, None))
    for seat in (1, 2, 3):
        assert not GAME._any_moves(s, seat), f"seat {seat}'s corner is covered"
    assert GAME._any_moves(s, 0)
    assert not GAME.is_terminal(s), "seat 0 can still place -> not terminal"
    nxt = GAME.apply_move(s, GAME.legal_moves(s)[0])
    assert nxt.to_move == 0, "blocked seats must be skipped, not given the turn"

    # legal_moves is never empty on a non-terminal state, and the seat to move
    # always has moves.
    s = GAME.initial_state()
    for _ in range(30):
        if GAME.is_terminal(s):
            break
        mv = GAME.legal_moves(s)
        assert mv, "empty legal_moves on a non-terminal state"
        s = GAME.apply_move(s, mv[0])
    print("  blocked seat skipped; legal_moves never empty OK")


def test_turn_order_is_clockwise():
    """With nobody blocked, play runs 0 -> 1 -> 2 -> 3 -> 0 (blue, yellow, red, green)."""
    s = GAME.initial_state()
    seen = []
    for _ in range(8):
        seen.append(GAME.current_player(s))
        s = GAME.apply_move(s, GAME.legal_moves(s)[0])
    assert seen == [0, 1, 2, 3, 0, 1, 2, 3], seen
    print("  play order 0->1->2->3 (blue, yellow, red, green) OK")


def test_full_game_terminates():
    """Play deterministic games to the end and check the invariants."""
    import random
    for seed in (12345, 999):
        rng = random.Random(seed)
        s = GAME.initial_state()
        plies = 0
        while not GAME.is_terminal(s):
            mv = GAME.legal_moves(s)
            assert mv
            s = GAME.apply_move(s, rng.choice(mv))
            plies += 1
            assert plies <= 84, "more plies than pieces exist (21 x 4)"
        # The four colours never overlap; each seat's placed squares tally.
        for i in range(4):
            for j in range(i + 1, 4):
                assert not (s.occ[i] & s.occ[j]), f"colours {i}/{j} overlap"
        total = sum(G.SIZES[k] for k in G.PIECES)
        for p in range(4):
            placed = bin(s.occ[p]).count("1")
            assert placed == total - sum(G.SIZES[k] for k in s.hands[p])
        r = GAME.returns(s)
        assert len(r) == 4
        assert sorted(r) in ([-1.0, -1.0, -1.0, 1.0], [0.0, 0.0, 0.0, 0.0]), r
        # The heuristic must be a LIST of 4 payoffs (MCTS indexes payoffs[p]).
        h = GAME.heuristic(s)
        assert isinstance(h, list) and len(h) == 4, h
        assert all(-1.0 <= x <= 1.0 for x in h), h
        # Round-trip through serialization.
        s2 = GAME.deserialize(GAME.serialize(s))
        assert s2.occ == s.occ and s2.hands == s.hands and s2.to_move == s.to_move
        assert s2.last_key == s.last_key
        assert GAME.returns(s2) == r
        print(f"  random game (seed {seed}): {plies} plies, "
              f"scores {[GAME.score(s, p) for p in range(4)]}, serialization OK")


def test_render_shape():
    s = GAME.initial_state()
    v = GAME.render(s)
    assert v["board"]["type"] == "square"
    assert v["board"]["width"] == 20 and v["board"]["height"] == 20
    pal = v["palette"]
    assert set(pal) == {"0", "1", "2", "3"}, set(pal)
    for seat in ("0", "1", "2", "3"):
        assert len(pal[seat]) == 21
        for t in pal[seat]:
            assert set(t) >= {"key", "orients"}
            assert ":" not in t["key"] and "@" not in t["key"]
            for o in t["orients"]:
                assert all(isinstance(x, list) and len(x) == 2 for x in o)
                assert [0, 0] in o
    # All four corners tinted while uncovered.
    assert v["board"]["tints"] == {"0,19": "#c8b88a", "19,19": "#c8b88a",
                                   "19,0": "#c8b88a", "0,0": "#c8b88a"}, v["board"]["tints"]
    # After a placement the palette shrinks and the piece renders.
    s = GAME.apply_move(s, _move_for("I1", [(0, 19)]))
    v = GAME.render(s)
    assert len(v["palette"]["0"]) == 20
    assert len(v["palette"]["1"]) == 21
    # Match on the MEANINGFUL fields, not the whole dict: pieces also carry
    # `shape: "fill"` so a tile renders as one solid block rather than a disc
    # per cell, and an exact-equality check would break on any such addition.
    assert any(p["cell"] == "0,19" and p["owner"] == 0 for p in v["pieces"]), v["pieces"][:3]
    assert all(p.get("shape") == "fill" for p in v["pieces"]), "tiles must render as filled cells"
    assert "0,19" not in v["board"]["tints"]
    print("  render: board/palette(4 seats)/tints shape OK")


if __name__ == "__main__":
    test_piece_set()
    test_start_corners()
    test_opening_anchor()
    test_first_move_must_cover_own_corner()
    test_corner_yes_edge_no()
    test_other_colour_edge_contact_is_legal()
    test_scoring()
    test_honest_draw_on_tie()
    test_pass_and_termination()
    test_turn_order_is_clockwise()
    test_full_game_terminates()
    test_render_shape()
    print("blokus selftest: all OK")
