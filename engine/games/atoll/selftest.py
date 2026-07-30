"""Atoll selftest — pure stdlib (agp + this package only).

Anchors, in order:
  1. board geometry vs Fig. 1 of Atoll_rules.pdf, transcribed cell-for-cell from
     the PDF's vector art, plus the derived cell counts at all three sizes;
  2. the perimeter cycle of the eight islands, DERIVED from the geometry, and
     the alternation / opposition that the goal depends on;
  3. Figure 2 and Figure 3 replayed as real games (one placement per turn) —
     Black must win on the last stone and not one ply earlier, by North-South in
     Fig. 2 and West-East in Fig. 3, with Fig. 3's winning group also containing
     Black's South island (the rule sheet says so explicitly);
  4. near-misses: every critical stone of both figures removed one at a time,
     and a group joining two NON-opposite islands;
  5. win detection cross-checked at every ply against an INDEPENDENT brute-force
     component scan written here, not shared with game.py;
  6. the generalized "perimeter path" objective from the rule sheet, brute-forced
     over every island subset, must agree with the opposite-pair rule;
  7. seat symmetry: the vertical mirror conjugates the whole engine;
  8. serialize/deserialize compared as STATES with an exact key set, swept over a
     whole game at every size;
  9. no draws: full random colourings must always have exactly one winner;
 10. render()'s declared cell set must contain every rendered piece, at every
     size, from a position with stones in the far corners;
 11. heuristic shape (a list of two, antisymmetric, bounded) and an MCTS run with
     max_rollout=4 so the cutoff — and therefore the heuristic — actually fires;
 12. `_link_cost`'s three documented cases (own/island free, empty costs one,
     opponent impassable) and the tempo term in the eval;
 13. `cell_name` at EVERY size, derived from the cell coordinates;
 14. the eight perimeter seams and the two notches, at every size;
 15. the `winning_group` / `connected_islands` diagnostics, against the brute
     force, order-free, plus the sorted-tuple contract of the latter.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir            # noqa: E402
from agp.mcts import MCTSBot                    # noqa: E402

MAN, GAME = load_from_dir(Path(__file__).resolve().parent)
G = sys.modules[type(GAME).__module__]          # the LIVE module object

# --------------------------------------------------------------------------- 1
# Figure 1 of the rule sheet, transcribed from the PDF's vector art: 13 columns
# (0 and 12 are the island columns) x 23 half-rows.  '.' = empty playable cell,
# 'B' = a stone of the first player's islands, 'W' = the second player's.
FIG1 = (
    "  W W   B B  ",
    " W W W B B B ",
    "  . . . . .  ",
    " . . . . . . ",
    "B . . . . . W",
    " . . . . . . ",
    "B . . . . . W",
    " . . . . . . ",
    "B . . . . . W",
    " . . . . . . ",
    "B . . . . . W",
    " . . . . . . ",
    "W . . . . . B",
    " . . . . . . ",
    "W . . . . . B",
    " . . . . . . ",
    "W . . . . . B",
    " . . . . . . ",
    "W . . . . . B",
    " . . . . . . ",
    "  . . . . .  ",
    " B B B W W W ",
    "  B B   W W  ",
)
# Fig. 2 — "Black wins by connecting his North and South islands".
FIG2 = (
    "  W W   B B  ",
    " W W W B B B ",
    "  . W . . .  ",
    " . . . . B . ",
    "B . W . B . W",
    " . W . . . . ",
    "B B . . B . W",
    " . W . . B . ",
    "B W . . B . W",
    " . W . . . W ",
    "B W . B B . W",
    " . . B B . W ",
    "W W B B . . B",
    " W . . . . . ",
    "W . B . W . B",
    " W . B . . . ",
    "W . . . . . B",
    " . . B . W . ",
    "W . B . . . B",
    " . . . . W . ",
    "  . B . . W  ",
    " B B B W W W ",
    "  B B   W W  ",
)
# Fig. 3 — "Black wins by connecting his West and East islands.  Note that
# stones in Black's South island comprise part of the winning sequence."
FIG3 = (
    "  W W   B B  ",
    " W W W B B B ",
    "  . W . . .  ",
    " . . W . . . ",
    "B . . B . . W",
    " . W W W . . ",
    "B . . W W . W",
    " . W . B W W ",
    "B . . . W W W",
    " B . . W W . ",
    "B B . W . . W",
    " W B . . . . ",
    "W B . W . . B",
    " . B . . . . ",
    "W . . W . . B",
    " . B . . . . ",
    "W B . . B B B",
    " B . . B B B ",
    "W . . . . B B",
    " B . . B . . ",
    "  . . B . .  ",
    " B B B W W W ",
    "  B B   W W  ",
)
# Stones whose removal from the figure destroys Black's win (independently
# recomputed below, so this list is an assertion about the figures, not input).
FIG2_CRITICAL = 13
FIG3_CRITICAL = 13


def ax(c, row):
    assert (row - c) % 2 == 0, (c, row)
    return (c, (row - c) // 2)


def parse_fig(rows):
    """-> {axial cell: char} for every drawn circle."""
    out = {}
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch != " ":
                out[ax(c, r)] = ch
    return out


def check_geometry():
    sizes = MAN["options"]["size"]["choices"]
    assert sizes == [11, 15, 19], sizes
    assert MAN["options"]["size"]["default"] == 11
    expect_cells = {11: 104, 15: 202, 19: 332}
    expect_isl = {11: 36, 15: 52, 19: 68}
    for size in sizes:
        sp = G.spec_for(size)
        assert len(sp.playable) == expect_cells[size], (size, len(sp.playable))
        assert sum(len(v) for v in sp.islands.values()) == expect_isl[size]
        assert len(sp.islands) == 8
        assert set(sp.islands) == set(G.PERIMETER_ORDER)
        assert len(sp.all_cells) == expect_cells[size] + expect_isl[size]
        assert set(sp.all_cells) == set(sp.playable) | set(sp.island_of)
        # islands are disjoint, off the playable area, internally connected, and
        # each cell of one touches the playable area somewhere
        seen = set()
        for k, cells in sp.islands.items():
            assert not (cells & sp.playable), k
            assert not (cells & seen), k
            seen |= cells
            comp, stack = {min(cells)}, [min(cells)]
            while stack:
                for nb in G.neighbors(*stack.pop()):
                    if nb in cells and nb not in comp:
                        comp.add(nb)
                        stack.append(nb)
            assert comp == cells, k
            for cell in cells:
                assert any(nb in sp.playable for nb in G.neighbors(*cell)), (k, cell)
        # no two islands of the SAME owner touch — so the empty board is not a win
        for a in sp.islands:
            for b in sp.islands:
                if a < b and a[0] == b[0]:
                    assert not any(nb in sp.islands[b]
                                   for cell in sp.islands[a] for nb in G.neighbors(*cell)), (a, b)
        s0 = GAME.initial_state({"size": size})
        assert s0.winner is None and not GAME.is_terminal(s0)
        assert len(GAME.legal_moves(s0)) == expect_cells[size]
        assert set(GAME.legal_moves(s0)) == {f"{q},{r}" for q, r in sp.playable}
    # the default option really is the 11 board
    assert len(GAME.legal_moves(GAME.initial_state())) == 104
    # ...and Figure 1 is exactly that board
    fig = parse_fig(FIG1)
    sp = G.spec_for(11)
    assert {c for c, ch in fig.items() if ch == "."} == set(sp.playable)
    for owner, ch in ((0, "B"), (1, "W")):
        drawn = {c for c, v in fig.items() if v == ch}
        derived = {c for c, o in sp.owner_of.items() if o == owner}
        assert drawn == derived, (ch, sorted(drawn ^ derived))
    assert len(fig) == 140
    # algebraic naming (also AbstractPlay's): a1 is the foot of the left file
    assert G.cell_name(11, ax(1, 19)) == "a1"
    assert G.cell_name(11, ax(1, 3)) == "a9"
    assert G.cell_name(11, ax(2, 20)) == "b1"
    assert G.cell_name(11, ax(2, 2)) == "b10"
    assert G.cell_name(11, ax(11, 3)) == "k9"
    names = {G.cell_name(11, c) for c in sp.playable}
    assert len(names) == 104
    assert GAME.describe_move(GAME.initial_state(), "%d,%d" % ax(6, 2)) == "f10"


# --------------------------------------------------------------------------- 2
def check_perimeter():
    """Derive the island cycle from the geometry alone and match it to
    PERIMETER_ORDER; then check alternation and that 'opposite' = 4 apart."""
    for size in (11, 15, 19):
        sp = G.spec_for(size)
        adj = {k: set() for k in sp.islands}
        for a in sp.islands:
            for b in sp.islands:
                if b <= a:
                    continue
                ca, cb = sp.islands[a], sp.islands[b]
                touch = any(nb in cb for c in ca for nb in G.neighbors(*c))
                corner = any(all(any(nb in s for nb in G.neighbors(*p)) for s in (ca, cb))
                             for p in sp.playable)
                if touch or corner:
                    adj[a].add(b)
                    adj[b].add(a)
        assert all(len(v) == 2 for v in adj.values()), adj
        cyc, cur, prev = [G.PERIMETER_ORDER[0]], G.PERIMETER_ORDER[0], None
        while True:
            nxt = sorted(x for x in adj[cur] if x != prev)
            nxt = nxt[0] if prev is None else nxt[0]
            if nxt == cyc[0]:
                break
            cyc.append(nxt)
            prev, cur = cur, nxt
        assert len(cyc) == 8
        assert tuple(cyc) == G.PERIMETER_ORDER, (size, cyc)
    order = G.PERIMETER_ORDER
    for i, k in enumerate(order):                       # owners alternate
        assert k[0] != order[(i + 1) % 8][0], order
    for a, b in G.OPPOSITE_PAIRS:                       # opposite = 4 apart
        assert (order.index(a) - order.index(b)) % 8 == 4, (a, b)
        assert a[0] == b[0]
    assert len(G.OPPOSITE_PAIRS) == 4
    assert {frozenset(p) for p in G.OPPOSITE_PAIRS} == {
        frozenset(("0N", "0S")), frozenset(("0W", "0E")),
        frozenset(("1N", "1S")), frozenset(("1W", "1E"))}


# --------------------------------------------------------------------------- 5
def brute_winner(size, stones):
    """Independent re-implementation: every island pair joined by one group."""
    sp = G.spec_for(size)

    def owner(c):
        v = stones.get(c)
        return v if v is not None else sp.owner_of.get(c)

    pairs, seen = set(), set()
    for cell in sp.all_cells:
        if cell in seen or owner(cell) is None:
            continue
        seat = owner(cell)
        comp, stack = {cell}, [cell]
        while stack:
            for nb in G.neighbors(*stack.pop()):
                if nb not in comp and owner(nb) == seat:
                    comp.add(nb)
                    stack.append(nb)
        seen |= comp
        isls = sorted({sp.island_of[c] for c in comp if c in sp.island_of})
        for i, a in enumerate(isls):
            for b in isls[i + 1:]:
                pairs.add(frozenset((a, b)))
    wins = {int(next(iter(p))[0]) for p in pairs
            if p in {frozenset(x) for x in G.OPPOSITE_PAIRS}}
    assert len(wins) <= 1, (wins, "both players connected — impossible")
    return (next(iter(wins)) if wins else None), pairs


# --------------------------------------------------------------------------- 3/4
def fig_stones(rows):
    sp = G.spec_for(11)
    out = {}
    for cell, ch in parse_fig(rows).items():
        if cell in sp.playable and ch in "BW":
            out[cell] = 0 if ch == "B" else 1
    return out


def check_figure(rows, expect_pair, also_touches, ncrit):
    stones = fig_stones(rows)
    black = sorted(c for c, v in stones.items() if v == 0)
    white = sorted(c for c, v in stones.items() if v == 1)
    # the figure is a legal alternating position with Black having just moved
    assert len(black) == len(white) + 1, (len(black), len(white))
    win, pairs = brute_winner(11, stones)
    assert win == 0, win
    assert frozenset(expect_pair) in pairs, (expect_pair, sorted(map(sorted, pairs)))
    # White is NOT winning even though White's groups do span two islands
    whitepairs = {p for p in pairs if all(k[0] == "1" for k in p)}
    assert whitepairs, "expected White to join two islands (a non-opposite pair)"
    assert not (whitepairs & {frozenset(x) for x in G.OPPOSITE_PAIRS})

    # which black stones are load-bearing?
    crit = []
    for c in black:
        cut = dict(stones)
        del cut[c]
        if brute_winner(11, cut)[0] is None:
            crit.append(c)
        else:
            assert brute_winner(11, cut)[0] == 0
    assert len(crit) == ncrit, (len(crit), ncrit)

    # replay the figure as a real game, saving one critical stone for last
    for last in crit:
        seq = []
        rest = [c for c in black if c != last] + [last]
        for i in range(len(black) + len(white)):
            seq.append(rest[i // 2] if i % 2 == 0 else white[i // 2])
        s = GAME.initial_state()
        for i, cell in enumerate(seq):
            assert s.winner is None, f"won early at ply {i}"
            assert not GAME.is_terminal(s)
            mv = f"{cell[0]},{cell[1]}"
            assert mv in GAME.legal_moves(s)
            s = GAME.apply_move(s, mv)
            assert s.winner == brute_winner(11, s.stones)[0], i
        assert s.winner == 0
        assert GAME.is_terminal(s) and GAME.returns(s) == [1.0, -1.0]
        assert GAME.legal_moves(s) == []
        # the winning group really does contain both islands of the pair
        grp = GAME.winning_group(s)
        sp = G.spec_for(11)
        for k in expect_pair:
            assert grp & sp.islands[k], k
        for k in also_touches:
            assert grp & sp.islands[k], k
        assert s.stones == stones
    # one stone short is not a win, at any of the critical squares
    for c in crit:
        cut = dict(stones)
        del cut[c]
        d = GAME.serialize(GAME.initial_state())
        d["stones"] = {f"{q},{r}": v for (q, r), v in cut.items()}
        s = GAME.deserialize(d)
        assert brute_winner(11, s.stones)[0] is None
        assert not GAME.is_terminal(s)
        # ...and putting it back wins
        s2 = GAME.apply_move(GAME.deserialize({**d, "to_move": 0}), f"{c[0]},{c[1]}")
        assert s2.winner == 0, c


def check_non_opposite():
    """A chain joining two islands that are NOT opposite must never win."""
    sp = G.spec_for(11)
    order = G.PERIMETER_ORDER
    tested = 0
    for i, a in enumerate(order):
        for j, b in enumerate(order):
            if j <= i or a[0] != b[0] or (i - j) % 8 == 4:
                continue
            seat = int(a[0])
            # flood a shortest corridor of `seat` stones between the islands
            start = set(sp.islands[a])
            prev, frontier = {}, list(start)
            dist = {c: 0 for c in start}
            goal = None
            while frontier and goal is None:
                nxt = []
                for c in frontier:
                    for nb in G.neighbors(*c):
                        if nb in dist or (nb not in sp.playable and nb not in sp.island_of):
                            continue
                        if nb in sp.island_of and nb not in sp.islands[b]:
                            continue
                        dist[nb] = dist[c] + 1
                        prev[nb] = c
                        if nb in sp.islands[b]:
                            goal = nb
                            break
                        nxt.append(nb)
                    if goal:
                        break
                frontier = nxt
            assert goal is not None, (a, b)
            stones, cur = {}, goal
            while cur in prev:
                if cur in sp.playable:
                    stones[cur] = seat
                cur = prev[cur]
            win, pairs = brute_winner(11, stones)
            assert frozenset((a, b)) in pairs, (a, b)
            assert win is None, (a, b, "non-opposite pair must not win")
            tested += 1
    # 4 same-owner pairs per seat are NOT opposite (C(4,2) - 2), so 8 in total
    assert tested == 8, tested


# --------------------------------------------------------------------------- 6
def check_generalized_objective():
    """The rule sheet's generalized objective: connect two or more of your
    islands such that the SHORTEST perimeter path touching them touches at least
    (total/2 + 1) islands.  On the 8-island board that must be exactly the
    'two exactly opposite islands' rule."""
    order = G.PERIMETER_ORDER
    n = len(order)
    need = n // 2 + 1
    checked = 0
    for seat in (0, 1):
        mine = [k for k in order if int(k[0]) == seat]
        assert len(mine) == 4
        for mask in range(1 << 4):
            sub = {mine[i] for i in range(4) if mask >> i & 1}
            if len(sub) < 2:
                continue
            idx = {order.index(k) for k in sub}
            best = min(L for L in range(1, n + 1)
                       for st in range(n)
                       if idx <= {(st + d) % n for d in range(L)})
            generalized = best >= need
            opposite = any(a in sub and b in sub for a, b in G.OPPOSITE_PAIRS)
            assert generalized == opposite, (sorted(sub), best, generalized, opposite)
            checked += 1
    assert checked == 22, checked


# --------------------------------------------------------------------------- 7
def mirror(size, cell):
    """The board's only non-trivial symmetry: reflect left<->right.  It maps
    each island onto the OTHER seat's island of the mirrored compass point, so
    conjugating by it must swap the two seats' roles exactly."""
    q, r = cell
    m = (size + 1) // 2
    return (size + 1 - q, r + q - m)


def conj(s):
    return G.AtollState(
        size=s.size,
        stones={mirror(s.size, c): 1 - v for c, v in s.stones.items()},
        to_move=1 - s.to_move,
        winner=None if s.winner is None else 1 - s.winner,
        last=None if s.last is None else mirror(s.size, s.last),
    )


def check_seat_symmetry():
    for size in (11, 15, 19):
        sp = G.spec_for(size)
        assert {mirror(size, c) for c in sp.playable} == set(sp.playable)
        flip = {"N": "N", "S": "S", "W": "E", "E": "W"}
        for k, cells in sp.islands.items():
            tgt = f"{1 - int(k[0])}{flip[k[1]]}"
            assert {mirror(size, c) for c in cells} == sp.islands[tgt], (size, k)
        assert all(mirror(size, mirror(size, c)) == c for c in sp.all_cells)
    rng = random.Random(4242)
    checks = 0
    for size in (11, 15):
        for _ in range(6):
            s = GAME.initial_state({"size": size})
            while not GAME.is_terminal(s):
                t = conj(s)
                assert GAME.current_player(t) == 1 - GAME.current_player(s)
                assert (sorted(GAME.legal_moves(t))
                        == sorted("%d,%d" % mirror(size, G._cell(m))
                                  for m in GAME.legal_moves(s)))
                assert GAME.is_terminal(t) == GAME.is_terminal(s)
                h, ht = GAME.heuristic(s), GAME.heuristic(t)
                assert abs(h[0] + ht[0]) < 1e-9 and abs(h[1] + ht[1]) < 1e-9, (h, ht)
                mv = rng.choice(GAME.legal_moves(s))
                s2 = GAME.apply_move(s, mv)
                t2 = GAME.apply_move(t, "%d,%d" % mirror(size, G._cell(mv)))
                assert t2 == conj(s2), (mv, t2, conj(s2))
                checks += 1
                s = s2
            assert GAME.returns(conj(s)) == list(reversed(GAME.returns(s)))
    assert checks > 400, checks


# --------------------------------------------------------------------------- 8
KEYS = {"size", "stones", "to_move", "winner", "last"}


def check_roundtrip():
    rng = random.Random(11)
    shapes = set()
    for size in (11, 15, 19):
        s = GAME.initial_state({"size": size})
        while True:
            d = GAME.serialize(s)
            assert set(d) == KEYS, set(d) ^ KEYS
            assert GAME.deserialize(d) == s, (d, s)          # STATES, not dicts
            assert json.loads(json.dumps(d)) == d
            shapes.add((s.winner is None, s.last is None, bool(s.stones)))
            if GAME.is_terminal(s):
                break
            s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
    # every field shape occurred: fresh state, mid-game, and a decided game
    assert (True, True, False) in shapes
    assert (True, False, True) in shapes
    assert (False, False, True) in shapes, shapes
    # a dropped field must be a hard error, not a silent re-default
    for k in KEYS:
        d = GAME.serialize(GAME.initial_state())
        del d[k]
        try:
            GAME.deserialize(d)
        except KeyError:
            continue
        raise AssertionError(f"deserialize silently tolerated a missing {k!r}")


# --------------------------------------------------------------------------- 9
def check_no_draws():
    """Every FULL board has exactly one winner (the rule sheet's claim), and
    real games never reach a full board without one."""
    rng = random.Random(2024)
    for size, trials in ((11, 250), (15, 30), (19, 8)):
        sp = G.spec_for(size)
        for _ in range(trials):
            stones = {c: rng.randrange(2) for c in sp.playable}
            win, _ = brute_winner(size, stones)
            assert win is not None, f"full board with no winner at size {size}"
    lens, won = [], set()
    for _ in range(40):
        s = GAME.initial_state()
        while not GAME.is_terminal(s):
            s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
            assert s.winner == brute_winner(11, s.stones)[0]
        assert s.winner is not None, "a real game ended in a draw"
        assert GAME.returns(s) in ([1.0, -1.0], [-1.0, 1.0])
        won.add(s.winner)
        lens.append(len(s.stones))
    # BOTH seats must be able to win through apply_move — not just seat 0, which
    # is the only one the figure replays exercise
    assert won == {0, 1}, won
    assert max(lens) <= 104
    # the bound: at most one stone per placeable cell, so no ply cap is needed
    assert max(lens) <= len(G.spec_for(11).playable)


def check_full_board_invariant():
    """Defensive branch.  A full board always has a winner (checked above), so
    this state cannot arise in play — but the engine invariant "no legal moves
    implies terminal" must still hold, and an (unreachable) tie must score as an
    honest 0-0 draw rather than a fabricated tie-break."""
    sp = G.spec_for(11)
    d = GAME.serialize(GAME.initial_state())
    d["stones"] = {f"{q},{r}": (q + r) % 2 for (q, r) in sp.playable}
    d["winner"] = None
    s = GAME.deserialize(d)
    assert GAME.legal_moves(s) == []
    assert GAME.is_terminal(s), "no legal moves must imply terminal"
    assert GAME.returns(s) == [0.0, 0.0]
    assert "draw" in GAME.render(s)["caption"].lower()
    # ...and scored honestly that very board is decided, which is why the branch
    # is dead in real play
    assert brute_winner(11, s.stones)[0] is not None
    # A DECISIVE RESULT MUST OUTRANK THE FULL-BOARD BRANCH.  Winning on the very
    # last stone is genuinely reachable here (random play hits 104 plies), so the
    # two conditions really do collide; the win has to win.
    for seat in (0, 1):
        w = GAME.deserialize({**d, "winner": seat})
        assert GAME.legal_moves(w) == [] and GAME.is_terminal(w)
        assert GAME.returns(w) == ([1.0, -1.0] if seat == 0 else [-1.0, 1.0]), seat
        assert "draw" not in GAME.render(w)["caption"].lower()
        assert G.SEAT_NAMES[seat] in GAME.render(w)["caption"]


# -------------------------------------------------------------------------- 10
def check_render():
    for size in (11, 15, 19):
        sp = G.spec_for(size)
        s = GAME.initial_state({"size": size})
        spec = GAME.render(s)
        assert spec["board"]["type"] == "hex"
        assert spec["board"]["orientation"] == "flat"
        declared = spec["board"]["cells"]
        assert isinstance(declared, list) and all(isinstance(x, str) for x in declared)
        assert len(declared) == len(set(declared)) == len(sp.all_cells)
        # reach the far corners through apply_move, then re-check
        corners = sorted(sp.playable, key=lambda c: (c[0], c[1]))
        extremes = [corners[0], corners[-1],
                    min(sp.playable, key=lambda c: (c[1], c[0])),
                    max(sp.playable, key=lambda c: (c[1], c[0]))]
        for cell in extremes:
            if GAME.is_terminal(s):
                break
            s = GAME.apply_move(s, f"{cell[0]},{cell[1]}")
        spec = GAME.render(s)
        declared = set(spec["board"]["cells"])
        assert len(spec["pieces"]) == len(sp.island_of) + len(s.stones)
        for p in spec["pieces"]:
            assert p["cell"] in declared, (size, p)          # else silently dropped
            assert p["owner"] in (0, 1)
        for k in spec["board"]["tints"]:
            assert k in declared, k
        assert set(spec["board"]["tints"]) == {f"{q},{r}" for q, r in sp.island_of}
        for h in spec["highlights"]:
            assert h["cell"] in declared
        assert isinstance(spec["caption"], str) and spec["caption"]
        for cell in extremes:
            assert f"{cell[0]},{cell[1]}" in declared


# -------------------------------------------------------------------------- 11
def check_bot_and_heuristic():
    rng = random.Random(5)
    s = GAME.initial_state()
    for _ in range(20):
        s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
    h = GAME.heuristic(s)
    assert isinstance(h, list) and len(h) == 2, h
    assert all(isinstance(x, float) for x in h)
    assert abs(h[0] + h[1]) < 1e-12 and all(-1.0 <= x <= 1.0 for x in h)
    # a low max_rollout forces the cutoff, so the heuristic really is exercised
    mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(GAME, s)
    assert mv in GAME.legal_moves(s)
    # the eval must prefer the side that is closer to connecting
    sp = G.spec_for(11)
    d = GAME.serialize(GAME.initial_state())
    corridor = {}
    for row in range(3, 20, 2):                 # a full black file a1..a9
        corridor[f"1,{(row - 1) // 2}"] = 0
    d["stones"] = corridor
    near = GAME.deserialize(d)
    assert GAME.heuristic(near)[0] > 0.5, GAME.heuristic(near)
    assert brute_winner(11, near.stones)[0] is None      # a file alone is no win
    # placing the last link of that file's West-East run does not exist; but the
    # symmetric position must evaluate oppositely
    assert abs(GAME.heuristic(near)[0] + GAME.heuristic(conj(near))[0]) < 1e-9
    # the eval's tempo term: the side to move is half a stone closer, so the
    # EMPTY board is not level -- whoever is on move is ahead.  (Antisymmetry
    # alone cannot see this: dropping the term keeps h == [0, 0].)
    e0 = GAME.initial_state()
    e1 = G.AtollState(size=11, stones={}, to_move=1)
    assert GAME.heuristic(e0)[0] > 0.05, GAME.heuristic(e0)
    assert GAME.heuristic(e1)[1] > 0.05, GAME.heuristic(e1)
    assert GAME.heuristic(e0) == [-x for x in GAME.heuristic(e1)]


# -------------------------------------------------------------------------- 12
def check_link_cost():
    """`_link_cost`'s docstring is a claim about three separate cases -- own and
    island cells are free, empty cells cost one, and OPPONENT stones are
    impassable.  It is the whole of the bot's eval, so a wrong cost silently
    weakens every vs-bot game while every rule test still passes.  Check all
    three, and check the block is really a block."""
    sp = G.spec_for(11)
    INF = 1 << 30
    # empty board: crossing 11 playable files costs 11 stones, and the shorter
    # North-South link costs 10.  Identical for both seats, by symmetry.
    for seat in (0, 1):
        assert GAME._link_cost(sp, {}, seat, f"{seat}W", f"{seat}E") == 11
        assert GAME._link_cost(sp, {}, seat, f"{seat}N", f"{seat}S") == 10
    # own stones are free: paving the left half drops the West-East cost to 5
    own = {c: 0 for c in sp.playable if c[0] <= 6}
    assert GAME._link_cost(sp, own, 0, "0W", "0E") == 5, GAME._link_cost(sp, own, 0, "0W", "0E")
    # a solid enemy file is IMPASSABLE -- it cuts seat 0 both ways, while its
    # owner gets that file for free
    wall = {c: 1 for c in sp.playable if c[0] == 6}
    assert len(wall) == 10
    assert GAME._link_cost(sp, wall, 0, "0W", "0E") == INF
    assert GAME._link_cost(sp, wall, 0, "0N", "0S") == INF
    assert GAME._link_cost(sp, wall, 1, "1W", "1E") == 10
    # ...and the eval reads that as a rout for the wall's owner
    blocked = G.AtollState(size=11, stones=dict(wall), to_move=0)
    assert GAME.heuristic(blocked) == [-1.0, 1.0], GAME.heuristic(blocked)


# -------------------------------------------------------------------------- 13
def check_naming():
    """`cell_name` must be AbstractPlay's algebraic name at EVERY size, not only
    at the five spot values pinned above: files run a.. left to right and ranks
    count 1.. upward from the foot of each file with no gaps.  Derived from the
    cell coordinates, so it does not just restate cell_name's own formula."""
    for size in (11, 15, 19):
        sp = G.spec_for(size)
        by_file = {}
        for cell in sp.playable:
            by_file.setdefault(cell[0], []).append(cell)
        assert sorted(by_file) == list(range(1, size + 1)), (size, sorted(by_file))
        names = {}
        for q, cells in sorted(by_file.items()):
            cells.sort(key=lambda c: -(2 * c[1] + c[0]))    # row grows downwards
            assert len(cells) == (size - 2 if q % 2 else size - 1), (size, q, len(cells))
            letter = chr(ord('a') + q - 1)
            for i, cell in enumerate(cells):
                nm = f"{letter}{i + 1}"
                assert G.cell_name(size, cell) == nm, (size, cell, G.cell_name(size, cell), nm)
                names[nm] = cell
        assert len(names) == len(sp.playable)
        assert "a1" in names and f"a{size - 2}" in names and f"a{size - 1}" not in names
        # the middle file is the long one and its top cell sits under the notch
        mid = chr(ord('a') + (size + 1) // 2 - 1)
        assert f"{mid}{size - 1}" in names and f"{mid}{size}" not in names, (size, mid)
    # spot values cross-checked against AbstractPlay's own cell names
    assert G.cell_name(11, ax(6, 2)) == "f10"
    assert G.cell_name(15, ax(8, 2)) == "h14"
    assert G.cell_name(19, ax(10, 2)) == "j18"
    assert G.cell_name(15, ax(15, 27)) == "o1"
    assert G.cell_name(19, ax(19, 35)) == "s1"


# -------------------------------------------------------------------------- 14
NOTCHED_SEAMS = {frozenset(p) for p in (
    ("1N", "0N"), ("0N", "1E"), ("0E", "1S"), ("1S", "0S"), ("0S", "1W"), ("0W", "1N"))}


def check_seams():
    """The eight perimeter seams, pinned explicitly at every size.  Six of them
    -- top centre, bottom centre and the four corners -- are separated by a
    NOTCH (a missing island cell), while at the two side-centre seams the two
    islands are in DIRECT contact.  Every seam is bridged by exactly one playable
    cell that touches both of its islands.  An off-by-two in the notch is the one
    geometry error that still yields a plausible-looking board, so it gets its
    own test at every size rather than only via the Figure 1 transcription."""
    for size in (11, 15, 19):
        sp = G.spec_for(size)
        order = G.PERIMETER_ORDER
        notched = set()
        for i, a in enumerate(order):
            b = order[(i + 1) % 8]
            touch = any(nb in sp.islands[b] for c in sp.islands[a] for nb in G.neighbors(*c))
            bridge = [c for c in sp.playable
                      if any(nb in sp.islands[a] for nb in G.neighbors(*c))
                      and any(nb in sp.islands[b] for nb in G.neighbors(*c))]
            assert len(bridge) == 1, (size, a, b, len(bridge))
            if not touch:
                notched.add(frozenset((a, b)))
        assert notched == NOTCHED_SEAMS, (size, sorted(map(sorted, notched)))
        # each notch is a real lattice position that is NOT on the board, and it
        # really does separate one island of each colour
        m = (size + 1) // 2
        for row in (0, 2 * size):
            notch = ax(m, row)
            assert notch not in sp.all_cells, (size, row, notch)
            nbs = {sp.island_of[c] for c in G.neighbors(*notch) if c in sp.island_of}
            assert len(nbs) == 2 and {k[0] for k in nbs} == {"0", "1"}, (size, row, nbs)


# -------------------------------------------------------------------------- 15
def check_diagnostics():
    """`winning_group` and `connected_islands` are code paths of their own, and
    are what a UI or analysis layer calls.  `connected_islands` hands back pairs
    as tuples sorted ALPHABETICALLY, so a caller comparing one against a literal
    ("0W", "0E") silently never matches -- exactly the trap that once made a
    whole no-draw sweep report 1,253 phantom draws.  Pin both against the
    independent brute force, order-free, and pin the sorted-tuple contract."""
    rng = random.Random(31337)
    sp = G.spec_for(11)
    checks = pairs_seen = 0
    for _ in range(6):
        s = GAME.initial_state()
        while True:
            want = brute_winner(11, s.stones)[1]
            for seat in (0, 1):
                got = GAME.connected_islands(s, seat)
                for a, b in got:                     # the documented contract
                    assert a < b, (a, b)
                    assert a[0] == b[0] == str(seat), (seat, a, b)
                mine = {p for p in want if all(k[0] == str(seat) for k in p)}
                assert {frozenset(p) for p in got} == mine, (seat, sorted(map(sorted, got)))
                pairs_seen += len(got)
            checks += 1
            if s.winner is not None:
                grp = GAME.winning_group(s)
                assert grp, "a decided game must expose its winning group"
                seat = s.winner
                assert s.last in grp
                assert all(GAME._owner(sp, s.stones, c) == seat for c in grp)
                for c in grp:                        # closed under adjacency
                    for nb in G.neighbors(*c):
                        if GAME._owner(sp, s.stones, nb) == seat:
                            assert nb in grp, (c, nb)
                isls = {sp.island_of[c] for c in grp if c in sp.island_of}
                assert any({a, b} <= isls for a, b in G.OPPOSITE_PAIRS
                           if int(a[0]) == seat), (seat, sorted(isls))
            else:
                assert GAME.winning_group(s) == set()
            if GAME.is_terminal(s):
                break
            s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
    assert checks > 300, checks
    assert pairs_seen > 100, pairs_seen        # non-vacuity: pairs really occur


def check_purity_and_errors():
    s = GAME.initial_state()
    before = GAME.serialize(s)
    mv = GAME.legal_moves(s)[17]
    GAME.apply_move(s, mv)
    assert GAME.serialize(s) == before, "apply_move mutated its input"
    # island cells (0,2)=(c0,row4), (12,2)=(c12,row16), (1,0)=(c1,row1) and a
    # cell that is simply off the board must all be rejected outright
    for bad in ("0,2", "12,2", "1,0", "99,99"):
        try:
            GAME.apply_move(s, bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted a placement on the non-playable cell {bad}")
    s2 = GAME.apply_move(s, mv)
    try:
        GAME.apply_move(s2, mv)
    except ValueError:
        pass
    else:
        raise AssertionError("accepted a placement on an occupied cell")
    try:
        G.spec_for(13)
    except ValueError:
        pass
    else:
        raise AssertionError("accepted an unsupported board size")
    try:
        GAME.initial_state({"size": 13})
    except ValueError:
        pass
    else:
        raise AssertionError("initial_state accepted an unsupported board size")


if __name__ == "__main__":
    check_geometry()
    check_perimeter()
    check_figure(FIG2, ("0N", "0S"), (), FIG2_CRITICAL)
    check_figure(FIG3, ("0W", "0E"), ("0S",), FIG3_CRITICAL)
    check_non_opposite()
    check_generalized_objective()
    check_seat_symmetry()
    check_roundtrip()
    check_no_draws()
    check_full_board_invariant()
    check_render()
    check_bot_and_heuristic()
    check_link_cost()
    check_naming()
    check_seams()
    check_diagnostics()
    check_purity_and_errors()
    print("atoll selftest OK")
