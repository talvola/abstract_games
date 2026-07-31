#!/usr/bin/env python3
"""Blast Radius correctness anchor -- pure stdlib (agp + this package only).

Anchors, strongest first:

1. **All four figures of the rule sheet, cell for cell.**  They were decoded from
   the PDF's *vector* paths (``pdftocairo -svg`` + parsing the 148 hexagon and 46
   marker shapes), not read off pixels, so the cell sets below are exact:
     * Fig. 1 -- the two overlapping REZs: 16 red dots, 4 blue dots, 2 purple.
       This is what fixes GROUND ZERO as being inside its own stack's REZ.
     * Fig. 2 -- Red's complete set of legal placements (2 green dots).
     * Fig. 3 -- the saturated board: Red's complete set of legal placements is
       his three shortest stacks (3 green dots) and NOT his height-2 stack.
     * Fig. 4 -- the worked capture: exactly the 2 yellow-dotted stacks go, the
       blue stack at distance 6 stays, and the newly built stack survives.
2. **The separation invariant** ``dist(A,B) > max(h_A,h_B)`` and its three
   corollaries, swept over whole random games on every board size: no stack ever
   sits in another stack's REZ (which is what makes rule 1's "friendly stack at
   ground zero" carve-out unambiguous), a height-1 placement never captures, and
   the sheet's "newly formed REZ" sweep equals a global sweep.
3. **Termination**: the descending height vector rises strictly in lexicographic
   order on EVERY ply, and no height ever exceeds the board diameter 2*(size-1).
   That is the whole termination proof -- there is no ply cap to test.
4. The rest of the bar: the single win condition reached from BOTH seats under
   random play (Blast Radius has only one -- annihilation -- so there is no
   second condition for a sweep to silently skip, but a seat can be:
   `test_sweep` asserts each side actually wins some games, which is what kills
   the frozen-seat mutant), the "except at the conclusion of Red's first turn"
   exception, the impossibility of a stuck player
   and of mutual annihilation, seat conjugation, the serialize round-trip
   compared as STATE OBJECTS with an exact key set, ``render()`` bounds at every
   board size on a far-corner position reached through ``apply_move``, and the
   heuristic's shape AND direction.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                  # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)
MOD = sys.modules[type(G).__module__]          # the LIVE module (synthetic name)
BRState = MOD.BRState
SIZES = MOD.SIZES
RED, BLUE = 0, 1
checks = 0


def ck(cond, msg):
    global checks
    checks += 1
    if not cond:
        raise AssertionError(msg)


def pos(size, board, ply=4, to_move=RED):
    return BRState(size=size,
                   board={MOD._cell(k): v for k, v in board.items()},
                   to_move=to_move, ply=ply)


def heights(s):
    return sorted((h for _, h in s.board.values()), reverse=True)


def lexvec(s):
    hs = heights(s)
    return tuple(hs) + (0,) * (len(MOD.cells(s.size)) - len(hs))


# --------------------------------------------------------------------------
# 1. The rule sheet's four figures (side-4 board, axial ids as we render them).
# --------------------------------------------------------------------------
# Fig. 1: a red height-2 stack at (0,-1) and a blue height-1 stack at (1,1).
FIG1 = {"0,-1": (RED, 2), "1,1": (BLUE, 1)}
FIG1_RED_DOTS = {(1, -3), (2, -3), (0, -3), (-1, -2), (2, -2), (0, -2), (1, -2),
                 (2, -1), (-1, -1), (1, -1), (-2, -1), (-1, 0), (-2, 0), (0, 0),
                 (-1, 1), (-2, 1)}
FIG1_BLUE_DOTS = {(2, 0), (2, 1), (1, 2), (0, 2)}
FIG1_PURPLE = {(1, 0), (0, 1)}

# Fig. 2 / 3 / 4 (green = legal placement, yellow = removed by the capture).
FIG2 = {"2,-2": (RED, 2), "1,2": (RED, 1), "-2,3": (RED, 1), "-2,-1": (BLUE, 3)}
FIG2_GREEN = {"3,0", "0,1"}
FIG3 = {"2,-2": (RED, 2), "-2,-1": (BLUE, 3), "3,0": (BLUE, 1),
        "0,1": (RED, 1), "1,2": (RED, 1), "-2,3": (RED, 1)}
FIG3_GREEN = {"0,1", "1,2", "-2,3"}
# Figure 4 prints "3" on the two yellow-dotted stacks and on the green-dotted
# red stack, but **"2"** on the blue stack at the right-hand edge (3,0) -- read
# off the digit glyph positions in the PDF and confirmed against the raster.
# Do NOT "round it up" to 3: a taller stack there has a larger REZ, which makes
# the saturation below (the reason the illustrated build is legal at all) easier
# to satisfy, and it destroys the Blue-to-move check, whose whole point is that
# Blue's shortest stack is the height-2 one.
FIG4 = {"2,-3": (BLUE, 3), "-2,-1": (RED, 3), "3,0": (BLUE, 2), "-1,2": (RED, 3)}
FIG4_GREEN = "-2,-1"
FIG4_YELLOW = {"2,-3", "-1,2"}


def test_figures():
    # -- Figure 1: the REZ of a height-h stack is every cell at distance <= h,
    #    ground zero included (the stack cells carry no dot only because the
    #    disc is drawn on them).
    s = pos(4, FIG1)
    rez = MOD.rez_cells(s.board, 4)
    red = {c for c, o in rez.items() if o == {RED}}
    blue = {c for c, o in rez.items() if o == {BLUE}}
    both = {c for c, o in rez.items() if len(o) > 1}
    ck(red == FIG1_RED_DOTS | {(0, -1)}, f"Fig1 red REZ {sorted(red)}")
    ck(blue == FIG1_BLUE_DOTS | {(1, 1)}, f"Fig1 blue REZ {sorted(blue)}")
    ck(both == FIG1_PURPLE, f"Fig1 overlap {sorted(both)}")
    ck(len(FIG1_RED_DOTS) == 16 and len(FIG1_BLUE_DOTS) == 4, "figure dot counts")
    # The tints the UI paints must agree with the same three sets, cell for
    # cell and colour for colour -- Red's zones in the Red tint, Blue's in the
    # Blue tint, the overlap purple (Figure 1's own convention), nothing else.
    tints = G.render(s)["board"]["tints"]
    want = {}
    for c in FIG1_RED_DOTS | {(0, -1)}:
        want[MOD.cid(c)] = MOD.REZ_TINT[RED]
    for c in FIG1_BLUE_DOTS | {(1, 1)}:
        want[MOD.cid(c)] = MOD.REZ_TINT[BLUE]
    for c in FIG1_PURPLE:
        want[MOD.cid(c)] = MOD.REZ_TINT[2]
    ck(tints == want, "Fig1 REZ tints (per-owner colour, exact cell set)")
    ck(len(set(MOD.REZ_TINT)) == 3, "the three REZ tints must be distinct")

    # Figures 2-4 are real play positions (only Figure 1 is captioned "would not
    # arise in play"), so each must satisfy the separation invariant.  If our
    # reading of the REZ or of restriction 1 were wrong, the designer's own
    # published positions would violate it.
    for name, fig in (("Fig2", FIG2), ("Fig3", FIG3), ("Fig4", FIG4)):
        st = {MOD._cell(k): v for k, v in fig.items()}
        for a, (_, ha) in st.items():
            for b, (_, hb) in st.items():
                if a < b:
                    ck(MOD.dist(a, b) > max(ha, hb),
                       f"{name} violates the separation invariant at {a}/{b}")

    # -- Figure 2: exactly the two green dots.
    ck(set(G.legal_moves(pos(4, FIG2))) == FIG2_GREEN, "Fig2 legal placements")

    # -- Figure 3: saturated board -> the three shortest RED stacks, and NOT
    #    Red's legal-but-taller height-2 stack.
    s3 = pos(4, FIG3)
    ck(MOD.free_cells(s3.board, 4) == [], "Fig3 must be saturated")
    ck(set(G.legal_moves(s3)) == FIG3_GREEN, "Fig3 legal placements")
    ck("2,-2" not in FIG3_GREEN, "Fig3: restriction 2 excludes the taller stack")
    # ... and Blue, whose only stacks are 3 and 1, must be on the height-1 one.
    s3b = pos(4, FIG3, to_move=BLUE)
    ck(set(G.legal_moves(s3b)) == {"3,0"}, "Fig3 Blue must use his shortest stack")

    # -- Figure 4: the worked capture.
    s4 = pos(4, FIG4)
    # The illustrated move BUILDS a stack, so the figure is only self-consistent
    # if the board is saturated -- otherwise restriction 2 would force Red onto
    # an empty cell instead and the sheet's own example would be illegal.
    ck(MOD.free_cells(s4.board, 4) == [], "Fig4 must be saturated")
    ck(set(G.legal_moves(s4)) == {"-2,-1", "-1,2"},
       "Fig4 Red's shortest stacks are his two height-3s")
    # ... and Blue, to move in the same position, is forced onto his height-2
    # stack alone.  This check is what the mis-transcribed height 3 destroyed.
    ck(set(G.legal_moves(pos(4, FIG4, to_move=BLUE))) == {"3,0"},
       "Fig4 Blue must use his height-2 stack")
    ck(FIG4_GREEN in G.legal_moves(s4), "Fig4 the illustrated move is legal")
    n = G.apply_move(s4, FIG4_GREEN)
    ck({MOD.cid(c) for c in n.removed} == FIG4_YELLOW, f"Fig4 removals {n.removed}")
    ck(n.board[MOD._cell(FIG4_GREEN)] == (RED, 4), "Fig4 new stack survives at 4")
    ck(MOD._cell("3,0") in n.board, "Fig4 the distance-6 blue stack survives")
    ck(MOD.dist(MOD._cell(FIG4_GREEN), MOD._cell("3,0")) == 6, "Fig4 geometry")
    for y in FIG4_YELLOW:
        ck(MOD.dist(MOD._cell(FIG4_GREEN), MOD._cell(y)) == 4, "Fig4 removal distance")
    ck(G.describe_move(s4, FIG4_GREEN) == "-2,-1 (3→4) ×2", G.describe_move(s4, FIG4_GREEN))

    # -- blast()'s "height >= 2" guard is the sheet's literal wording ("upon
    #    forming a stack of height 2 or more").  The separation invariant makes
    #    it unreachable -- nothing is ever within distance 1 of a legal empty
    #    placement -- so it is a predicate OFF the legality path and would
    #    otherwise be tested by nobody.  Pin it on a hand-built board.
    illegal = {(0, 0): (RED, 1), (1, 0): (BLUE, 1)}
    ck(MOD.blast(illegal, (0, 0), 4) == [],
       "a height-1 stack must not blast, even with a neighbour present")
    illegal2 = {(0, 0): (RED, 2), (1, 0): (BLUE, 1)}
    ck(MOD.blast(illegal2, (0, 0), 4) == [(1, 0)], "a height-2 stack does blast")


# --------------------------------------------------------------------------
# 2. Board geometry.
# --------------------------------------------------------------------------
def test_geometry():
    for size in SIZES:
        cs = MOD.cells(size)
        n = size - 1
        ck(len(cs) == 3 * n * n + 3 * n + 1, f"hexhex {size} cell count")
        ck(len(set(cs)) == len(cs), "cells are distinct")
        ck(all(MOD.on_board(c, size) for c in cs), "cells() agrees with on_board()")
        ck(max(MOD.dist(a, (0, 0)) for a in cs) == n, "board radius")
        # ball() must equal a brute-force distance filter, at every radius
        for radius in (0, 1, 2, n, 2 * n):
            b = set(MOD.ball((0, 0), radius, size))
            ck(b == {c for c in cs if MOD.dist(c, (0, 0)) <= radius},
               f"ball({radius}) size {size}")
        c0 = (n, -n)                                   # a corner
        ck(len(MOD.ball(c0, 1, size)) == 4, "corner has 3 neighbours + itself")
    # opening move count: every cell of an empty board (91 = AbstractPlay's default)
    for size, want in ((4, 37), (5, 61), (6, 91), (7, 127)):
        ck(len(G.legal_moves(G.initial_state({"size": size}))) == want,
           f"opening moves on side {size}")


# --------------------------------------------------------------------------
# 3. The Red-first-turn exception, and why nothing else needs one.
# --------------------------------------------------------------------------
def test_win_condition():
    s = G.initial_state({"size": 4})
    ck(not G.is_terminal(s), "empty board is not terminal")
    s1 = G.apply_move(s, "0,0")
    st, _ = G._counts(s1)
    ck(st == [1, 0], "after Red's first turn Blue has no checkers")
    ck(not G.is_terminal(s1),
       "2025 revision: Red does NOT win at the conclusion of his first turn")
    ck(G.legal_moves(s1), "Blue always has a reply")
    # the very same board one ply later WOULD be a win -- the exception is about
    # the turn number, not the position.
    ck(G.is_terminal(BRState(size=4, board=dict(s1.board), to_move=BLUE, ply=2)),
       "the same position at ply 2 is a Red win")
    ck(G.returns(BRState(size=4, board=dict(s1.board), to_move=BLUE, ply=2))
       == [1.0, -1.0], "Red wins it")
    # ... and symmetrically for Blue.
    ck(G.returns(BRState(size=4, board={(0, 0): (BLUE, 1)}, to_move=RED, ply=3))
       == [-1.0, 1.0], "Blue wins it")
    # an honest draw, not a fabricated tiebreak (proved unreachable elsewhere)
    ck(G.returns(BRState(size=4, board={}, to_move=RED, ply=9)) == [0.0, 0.0],
       "empty board scores an honest draw")
    ck(G.legal_moves(BRState(size=4, board={}, to_move=RED, ply=9)) == [],
       "a terminal state offers no moves")


# --------------------------------------------------------------------------
# 4. Invariants swept over whole random games, on every board size.
#    This is where the termination proof and the "no stuck player" /
#    "no mutual annihilation" arguments are actually exercised.
# --------------------------------------------------------------------------
def sweep(size, games, seed, per_ply=None):
    rnd = random.Random(seed)
    lengths, winners, maxh = [], [0, 0], 0
    for _ in range(games):
        s = G.initial_state({"size": size})
        v = lexvec(s)
        ply = 0
        while not G.is_terminal(s):
            moves = G.legal_moves(s)
            ck(moves, f"no legal move at ply {ply} on side {size} -- stuck player")
            mover = s.to_move
            free = MOD.free_cells(s.board, size)
            if free:
                # restriction 2: an empty legal cell forces you onto it
                ck(set(moves) == {MOD.cid(c) for c in free},
                   "restriction 2: must place on an empty cell when one exists")
            else:
                mine = [(c, h) for c, (o, h) in s.board.items() if o == mover]
                ck(mine, "a seat with no stacks would already have lost")
                lo = min(h for _, h in mine)
                ck(set(moves) == {MOD.cid(c) for c, h in mine if h == lo},
                   "restriction 2: must build on your shortest stack")
            mv = rnd.choice(moves)
            before = dict(s.board)
            s = G.apply_move(s, mv)
            ply += 1

            # (a) termination monovariant: strictly up, every single ply
            nv = lexvec(s)
            ck(nv > v, f"height vector did not increase on side {size} ply {ply}")
            v = nv
            # (b) the separation invariant -- and so: no stack in another's REZ
            for a, (_, ha) in s.board.items():
                for b, (_, hb) in s.board.items():
                    if a < b:
                        ck(MOD.dist(a, b) > max(ha, hb),
                           f"separation broken {a}{b} on side {size}")
            rez = MOD.rez_cells(s.board, size)
            for c in s.board:
                ck(rez[c] == {s.board[c][0]},
                   "a stack sits inside a foreign REZ -- rule 1 would be ambiguous")
            # (c) the mover always survives his own blast => no mutual annihilation
            st, _ = G._counts(s)
            ck(st[mover] >= 1, "the mover was wiped out by his own move")
            # (d) heights are bounded by the board diameter
            maxh = max(maxh, max(h for _, h in s.board.values()))
            ck(maxh <= 2 * (size - 1), f"height {maxh} exceeds diameter on side {size}")
            # (e) the sheet's "newly formed REZ" sweep == a global sweep
            cell = MOD._cell(mv)
            h = s.board[cell][1] if cell in s.board else 0
            probe = dict(before)
            probe[cell] = (mover, before.get(cell, (mover, 0))[1] + 1)
            glob = {e for d, (_, hd) in probe.items() for e in probe
                    if e != d and MOD.dist(d, e) <= hd}
            ck(glob == set(s.removed),
               f"newly-formed-REZ sweep != global sweep at ply {ply}: "
               f"{sorted(glob)} vs {sorted(s.removed)}")
            # (f) a height-1 placement never captures
            if h == 1:
                ck(not s.removed, "a height-1 placement captured something")
            if per_ply:
                per_ply(s)
        lengths.append(ply)
        r = G.returns(s)
        ck(r in ([1.0, -1.0], [-1.0, 1.0]), f"random game ended in a draw: {r}")
        winners[0 if r[0] > r[1] else 1] += 1
    return lengths, winners, maxh


def test_sweep():
    for size, games, seed, want_max in ((4, 120, 11, 6), (5, 40, 22, 8),
                                        (6, 14, 33, 10), (7, 6, 44, 12)):
        lengths, winners, maxh = sweep(size, games, seed)
        ck(min(winners) > 0 or size > 5,
           f"only one seat ever won on side {size}: {winners}")
        ck(maxh == want_max,
           f"side {size}: observed max height {maxh}, expected the diameter {want_max}")
        # random games are far short of the 3000-ply conformance ceiling
        ck(max(lengths) < 400, f"side {size} random game ran {max(lengths)} plies")


# --------------------------------------------------------------------------
# 5. Seat conjugation: the engine must be colour-blind.
# --------------------------------------------------------------------------
def swap_seats(s):
    return BRState(size=s.size,
                   board={c: (1 - o, h) for c, (o, h) in s.board.items()},
                   to_move=1 - s.to_move, ply=s.ply, last=s.last, removed=s.removed)


def test_seat_symmetry():
    rnd = random.Random(7)
    for _ in range(40):
        s = G.initial_state({"size": 4})
        while not G.is_terminal(s):
            t = swap_seats(s)
            ck(sorted(G.legal_moves(s)) == sorted(G.legal_moves(t)),
               "legal moves are not seat-conjugate")
            ck(G.heuristic(s) == [-x for x in G.heuristic(t)],
               "heuristic is not seat-conjugate")
            mv = rnd.choice(G.legal_moves(s))
            ns, nt = G.apply_move(s, mv), G.apply_move(t, mv)
            ck(swap_seats(ns).board == nt.board, "apply_move is not seat-conjugate")
            ck(G.is_terminal(ns) == G.is_terminal(nt), "terminality is not conjugate")
            ck(G.returns(ns) == [-x for x in G.returns(nt)],
               "returns are not seat-conjugate")
            s = ns


# --------------------------------------------------------------------------
# 6. Board automorphism: rotating the whole position by 60 degrees must
#    conjugate the game exactly.  This is a direct check on dist/ball/on_board.
# --------------------------------------------------------------------------
def rot60(c):
    q, r = c
    return (-r, q + r)


def test_rotation_equivariance():
    rnd = random.Random(13)
    for _ in range(25):
        s = G.initial_state({"size": 5})
        while not G.is_terminal(s):
            t = BRState(size=s.size, board={rot60(c): v for c, v in s.board.items()},
                        to_move=s.to_move, ply=s.ply)
            ck({MOD.cid(rot60(MOD._cell(m))) for m in G.legal_moves(s)}
               == set(G.legal_moves(t)), "legal moves are not rotation-equivariant")
            mv = rnd.choice(G.legal_moves(s))
            ns = G.apply_move(s, mv)
            nt = G.apply_move(t, MOD.cid(rot60(MOD._cell(mv))))
            ck({rot60(c): v for c, v in ns.board.items()} == nt.board,
               "apply_move is not rotation-equivariant")
            s = ns


# --------------------------------------------------------------------------
# 7. serialize/deserialize compared as STATE OBJECTS (a d -> d round trip
#    cannot see a dropped field), with the exact key set, swept over a game.
# --------------------------------------------------------------------------
KEYS = {"size", "board", "to_move", "ply", "last", "removed"}


def test_roundtrip():
    import json
    rnd = random.Random(5)
    seen_removed = seen_tall = 0
    for size in SIZES:
        s = G.initial_state({"size": size})
        while True:
            d = G.serialize(s)
            ck(set(d) == KEYS, f"serialize key set {set(d)}")
            # production reloads state from the DB as JSON TEXT every turn, so
            # round-trip through a real encode/decode, not the live dict
            back = G.deserialize(json.loads(json.dumps(d)))
            ck(back == s, f"state round trip lost information: {d}")
            ck(back.board == s.board and back.last == s.last
               and back.removed == s.removed and back.ply == s.ply
               and back.to_move == s.to_move and back.size == s.size,
               "field-by-field round trip")
            if s.removed:
                seen_removed += 1
            if s.board and max(h for _, h in s.board.values()) >= 3:
                seen_tall += 1
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
    ck(seen_removed > 0, "the sweep never covered a non-empty `removed`")
    ck(seen_tall > 0, "the sweep never covered a tall stack")


# --------------------------------------------------------------------------
# 8. render(): every board size, on a position reached through apply_move that
#    puts a stack in a FAR CORNER.  Board.jsx silently drops any piece outside
#    the declared board, so a check on a fresh state would be vacuous.
# --------------------------------------------------------------------------
def check_render(s, size, corners, need_corner, tall):
    spec = G.render(s)
    b = spec["board"]
    ck(b["type"] == "hex" and b["shape"] == "hexagon" and b["size"] == size,
       f"render declares the wrong board for side {size}")
    declared = {MOD.cid(c) for c in MOD.cells(size)}
    for p in spec["pieces"]:
        ck(p["cell"] in declared,
           f"side {size}: piece at {p['cell']} outside the declared board")
        owner, h = s.board[MOD._cell(p["cell"])]
        ck(p["owner"] == owner, "the rendered piece must carry its owner")
        ck(p["stack"] == [owner] * h,
           "the rendered tower must be `height` checkers of the owner's colour "
           "-- the height IS the blast radius and must not be dropped")
        tall.add(h)
    for c in b["tints"]:
        ck(c in declared, f"side {size}: tint at {c} outside the declared board")
    for h in spec["highlights"]:
        ck(h["cell"] in declared, f"side {size}: highlight outside the board")
    ck(len(spec["pieces"]) == len(s.board), "every stack must be rendered")
    if need_corner:
        ck(any(p["cell"] in {MOD.cid(c) for c in corners} for p in spec["pieces"]),
           f"side {size}: the far-corner stack was not rendered")
    ck(isinstance(spec["caption"], str) and spec["caption"], "caption")


def test_render_bounds():
    for size in SIZES:
        n = size - 1
        corners = [(n, 0), (0, n), (-n, n), (-n, 0), (0, -n), (n, -n)]
        s = G.initial_state({"size": size})
        # walk a real game far enough that stacks and REZ tints exist ...
        rnd = random.Random(100 + size)
        for _ in range(8):
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
        # ... then steer play onto the outermost corners, still through
        # apply_move, until at least two of them are occupied.
        cset = {MOD.cid(c) for c in corners}
        for _ in range(300):
            if G.is_terminal(s):
                break
            if sum(1 for c in corners if c in s.board) >= 2:
                break
            moves = G.legal_moves(s)
            want = [m for m in moves if m in cset and MOD._cell(m) not in s.board]
            s = G.apply_move(s, want[0] if want else rnd.choice(moves))
        ck(any(c in s.board for c in corners),
           f"side {size}: never reached a corner cell")
        tall = set()
        check_render(s, size, corners, True, tall)
        # A board of height-1 stacks makes the tower assertion VACUOUS -- [o]*1
        # and [o] are the same list -- so keep playing until real stacks exist
        # and re-check.  (Mutation testing caught exactly this hole.)
        for _ in range(600):
            if G.is_terminal(s) or max(tall) >= 3:
                break
            s = G.apply_move(s, rnd.choice(G.legal_moves(s)))
            check_render(s, size, corners, False, tall)
        ck(max(tall) >= 3, f"side {size}: never rendered a stack taller than "
                           f"{max(tall)} -- the tower check would be vacuous")


# --------------------------------------------------------------------------
# 9. The heuristic: SHAPE (a list of num_players payoffs) and DIRECTION
#    (a sign flip passes every shape/range/zero-sum/symmetry test).
# --------------------------------------------------------------------------
def test_heuristic():
    s = G.initial_state({"size": 5})
    h = G.heuristic(s)
    ck(isinstance(h, list) and len(h) == 2, f"heuristic must be a list of 2: {h!r}")
    ck(all(isinstance(x, float) for x in h), "heuristic entries must be floats")
    ck(abs(h[0] + h[1]) < 1e-12 and abs(h[0]) < 1e-12, "empty board is even")
    # DIRECTION, pinned to measured values.  The sign is COUNTER-INTUITIVE:
    # FEWER stacks is better (see rules.md), and a sign flip would sail through
    # every shape / range / zero-sum / seat-symmetry check above.
    few = pos(5, {"0,0": (RED, 1), "4,-2": (BLUE, 1), "-4,2": (BLUE, 1),
                  "0,4": (BLUE, 1)})
    many = pos(5, {"0,0": (RED, 1), "4,-2": (RED, 1), "-4,2": (RED, 1),
                   "0,4": (BLUE, 1)})
    ck(abs(G.heuristic(few)[0] - math.tanh(0.2 * 2)) < 1e-12,
       f"pinned value {G.heuristic(few)}")
    ck(abs(G.heuristic(many)[0] + math.tanh(0.2 * 2)) < 1e-12,
       f"pinned value {G.heuristic(many)}")
    ck(G.heuristic(few)[0] > 0 > G.heuristic(many)[0],
       "direction: 1-vs-3 stacks must favour the seat with FEWER stacks")
    ck(all(abs(G.heuristic(p)[0] + G.heuristic(p)[1]) < 1e-12
           for p in (few, many)), "zero sum")
    # a terminal position must report the real result, not the eval
    won = BRState(size=4, board={(0, 0): (RED, 1)}, to_move=BLUE, ply=6)
    ck(G.heuristic(won) == [1.0, -1.0], "heuristic must defer to returns()")
    # ... and, the part that actually pins the direction: greedy play on this
    # eval must beat a random player, and the SIGN-FLIPPED eval must lose to it.
    # Same seeds for both arms, both seats played, ~3s.
    def greedy_match(sign, games=250):
        rnd = random.Random(31337)
        won_ = 0
        for i in range(games):
            s, smart = G.initial_state({"size": 4}), i % 2
            while not G.is_terminal(s):
                moves = G.legal_moves(s)
                if s.to_move == smart:
                    sc = [(sign * G.heuristic(G.apply_move(s, m))[smart], m)
                          for m in moves]
                    best = max(x[0] for x in sc)
                    moves = [m for v, m in sc if v >= best - 1e-12]
                s = G.apply_move(s, rnd.choice(moves))
            won_ += G.returns(s)[smart] > 0
        return won_
    good, bad = greedy_match(1), greedy_match(-1)
    ck(good >= 140, f"greedy play on the eval won only {good}/250 vs random")
    ck(good - bad >= 40, f"the sign-flipped eval scored {bad}/250 against "
                         f"{good}/250 -- the direction is not established")


def main():
    for fn in (test_figures, test_geometry, test_win_condition, test_sweep,
               test_seat_symmetry, test_rotation_equivariance, test_roundtrip,
               test_render_bounds, test_heuristic):
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"blast_radius selftest: {checks} checks passed")


if __name__ == "__main__":
    main()
