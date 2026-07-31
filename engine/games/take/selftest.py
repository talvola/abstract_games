#!/usr/bin/env python3
"""Correctness anchors for Take (Mark Steere, February 2024).

Pure stdlib.  Anchors, strongest first:

1.  **Figures 1, 2a/2b and 3a/3b of the official rule sheet**, transcribed from
    the PDF's vector geometry (each cell hexagon and each disc was parsed out of
    `pdftocairo -svg` output, so the transcription is measured, not eyeballed).
    Each figure is asserted together with the PREMISES it relies on — which
    cells are clods vs bare, which liberties existed before the placement and
    which the placement destroyed — because a mis-transcribed figure passes
    every assertion built on it.
2.  **An exhaustive solve of the smallest legal board** (side 2, 7 cells) in
    BOTH variants: the reachable game graph is a DAG (no repetition is even
    possible), no reachable position is stuck, no game is drawn, and the game
    value is a second-player win.
3.  The **(K, G, U) termination monovariant** asserted ply by ply on every board
    size, and the derived finiteness bound.
4.  `serialize`/`deserialize` compared as STATES with an exact key set, over
    every reachable side-2 position and whole games on the bigger boards.
5.  Every win condition reached THROUGH `apply_move`, and the render caption's
    winner attribution for each of them.
6.  `render()` bounds for every board size, from positions with stones on the
    outermost ring.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                # noqa: E402

MAN, GAME = load_from_dir(Path(__file__).resolve().parent)
G = sys.modules[type(GAME).__module__]
assert Path(G.__file__).resolve().parent == Path(__file__).resolve().parent, \
    f"loaded the wrong game module: {G.__file__}"

C = G._cell
N = G._name


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def state(size, churn, red=(), blue=(), clods=(), to_move=0, **kw):
    return G.TakeState(size=size, churn=churn,
                       stones={**{C(c): 0 for c in red}, **{C(c): 1 for c in blue}},
                       clods=frozenset(C(c) for c in clods),
                       to_move=to_move, **kw)


def board_of(s):
    """(stones, clods) in comparable string form."""
    return ({N(c): v for c, v in sorted(s.stones.items())},
            sorted(N(c) for c in s.clods))


def bounded_via_moves(s, seat, comp):
    """`is_bounded` restated the long way round: is any LEGAL placement of
    `seat` adjacent to this group?  (This is the oracle's formulation.)"""
    sp = G.spec_for(s.size)
    legal = {C(m) for m in GAME.legal_moves(
        G.TakeState(size=s.size, churn=s.churn, stones=s.stones, clods=s.clods,
                    to_move=seat))}
    for x in comp:
        for y in sp.nbrs[x]:
            if y in legal:
                return False
    return True


def potential(s):
    """The termination monovariant (K, G, U)."""
    sp = G.spec_for(s.size)
    return (len(s.clods), len(G.groups(s.stones, sp.nbrs)),
            len(sp.cells) - len(s.stones))


# --------------------------------------------------------------------------- #
# 1.  FIGURE 1 — the placements available to Red
# --------------------------------------------------------------------------- #
# Rule sheet, side-3 board.  Transcribed from the PDF's vector shapes: cell
# hexagons at 22.46pt column pitch / 19.45pt row pitch, stones as 19.4pt discs,
# the placement dots as 9.7pt red discs.
FIG1 = dict(
    size=3, churn=False,
    red=["2,-2", "1,-1", "-2,0", "0,0", "-2,1", "0,1", "1,1"],
    blue=["0,-1", "-1,0", "1,0", "-1,1", "-1,2"],
    clods=["0,-2", "1,-2", "-1,-1", "-2,2", "0,2"],
    to_move=0,
)
FIG1_DOTS = {"0,-2", "-1,-1", "2,0", "-2,2"}
FIG1_BARE = {"2,-1", "2,0"}          # cream cells: no clod, no stone


def test_figure1():
    s = state(**FIG1)
    sp = G.spec_for(3)

    # --- premises the figure's answer hinges on ---------------------------- #
    occupied = set(s.stones)
    free = [c for c in sp.cells if c not in occupied]
    assert len(free) == 7, free
    assert {N(c) for c in free if c in s.clods} == set(FIG1["clods"])
    assert {N(c) for c in free if c not in s.clods} == FIG1_BARE
    # 19 cells = 12 stones + 5 clods + 2 bare — the figure is NOT saturated,
    # and both kinds of free cell are present (a figure with no bare cell could
    # not distinguish the clod rule from the bare rule at all).
    assert len(sp.cells) == 19 and len(s.stones) == 12 and len(s.clods) == 5

    ac = {N(c): G.ally_count(s.stones, sp.nbrs, c, 0) for c in free}
    assert ac == {"0,-2": 0,    # a SEED: zero friendly neighbours, on a clod
                  "1,-2": 2,    # clod but two red neighbours -> illegal
                  "-1,-1": 1,   # clod, exactly one -> growth
                  "2,-1": 2,    # BARE, two red neighbours -> illegal
                  "2,0": 1,     # BARE, exactly one -> growth
                  "-2,2": 1,    # clod, exactly one -> growth
                  "0,2": 2}, ac  # clod but two red neighbours -> illegal

    # --- the figure's illustrated outcome ---------------------------------- #
    assert set(GAME.legal_moves(s)) == FIG1_DOTS, sorted(GAME.legal_moves(s))

    # Blue's placements are a genuinely different set (the figure only draws
    # Red's, but a colour-blind bug would make the two identical).
    sb = state(**{**FIG1, "to_move": 1})
    assert set(GAME.legal_moves(sb)) != FIG1_DOTS
    assert set(GAME.legal_moves(sb)) == {"0,-2", "1,-2", "2,-1", "2,0", "0,2"}

    # Figure 1 does NOT by itself rule out a seed on a BARE cell (neither bare
    # cell has zero red neighbours).  Constructed input for that clause:
    s2 = state(size=3, churn=False, red=["0,0"], clods=["0,-2"])
    assert G.ally_count(s2.stones, sp.nbrs, C("-2,2"), 0) == 0
    assert C("-2,2") not in s2.clods
    assert "-2,2" not in GAME.legal_moves(s2)        # bare + 0 friends = illegal
    assert "0,-2" in GAME.legal_moves(s2)            # clod + 0 friends = seed
    print("  figure 1 OK — 4 dots, both seed clauses, 6 ally-counts pinned")


# --------------------------------------------------------------------------- #
# 2.  FIGURES 2a -> 2b — group removal in the base game
# --------------------------------------------------------------------------- #
FIG2A = dict(
    size=3, churn=False,
    red=["0,-1", "1,-1", "2,-1", "-2,0", "-2,1", "-1,1", "0,2"],
    blue=["0,-2", "1,-2", "-1,0", "0,0", "1,0", "1,1"],
    clods=["2,-2", "-1,-1", "2,0", "0,1"],
    to_move=1,
)
FIG2B_RED = ["0,-1", "1,-1", "2,-1"]
FIG2B_BLUE = ["0,-2", "1,-2"]
FIG2B_CLODS = ["-1,-1", "0,1", "2,-2", "2,0"]
PLACED_2A = "0,2"                                    # the green dot

R1 = {"0,-1", "1,-1", "2,-1"}
R2 = {"-2,0", "-2,1", "-1,1"}
R3 = {"0,2"}
B1 = {"0,-2", "1,-2"}
B2 = {"-1,0", "0,0", "1,0", "1,1"}


def test_figure2():
    sp = G.spec_for(3)
    after = state(**FIG2A)

    # --- the figure's own group decomposition ------------------------------ #
    gs = {frozenset(N(c) for c in comp): col for col, comp in G.groups(after.stones, sp.nbrs)}
    assert gs == {frozenset(R1): 0, frozenset(R2): 0, frozenset(R3): 0,
                  frozenset(B1): 1, frozenset(B2): 1}, gs

    # --- the position BEFORE Red's placement, and its premises ------------- #
    before = state(size=3, churn=False,
                   red=sorted(set(FIG2A["red"]) - {PLACED_2A}),
                   blue=FIG2A["blue"],
                   clods=sorted(set(FIG2A["clods"]) | {PLACED_2A}),
                   to_move=0)
    # the placement is a SEED on a clod (zero red neighbours)
    assert G.ally_count(before.stones, sp.nbrs, C(PLACED_2A), 0) == 0
    assert C(PLACED_2A) in before.clods
    assert PLACED_2A in GAME.legal_moves(before)

    # PREMISE: nothing was bounded before the placement — this is a real
    # mid-game position, and the seed alone does all the work.
    for col, comp in G.groups(before.stones, sp.nbrs):
        assert not G.is_bounded(before.stones, sp.nbrs, comp, col), comp
    # PREMISE: the exact liberties the seed destroys.
    #   R2 could grow at (-1,2) and (0,1); B2 could grow only at (0,2) itself.
    assert set(GAME.legal_moves(before)) == {"2,0", "0,1", "0,2", "-1,2"}
    blue_before = GAME.legal_moves(G.TakeState(size=3, churn=False,
                                               stones=before.stones,
                                               clods=before.clods, to_move=1))
    assert set(blue_before) == {"0,2", "2,-2"}, blue_before
    # B2's only liberty is (0,2): every other blue-legal cell is far from B2.
    b2_libs = {m for m in blue_before
               if any(C(m) in sp.nbrs[C(x)] for x in B2)}
    assert b2_libs == {"0,2"}, b2_libs

    # --- the figure's illustrated outcome ---------------------------------- #
    res = GAME.apply_move(before, PLACED_2A)
    stones, clods = board_of(res)
    assert stones == {**{c: 0 for c in FIG2B_RED}, **{c: 1 for c in FIG2B_BLUE}}, stones
    assert clods == sorted(FIG2B_CLODS), clods
    assert set(N(c) for c in res.removed) == R2 | R3 | B2
    assert len(res.removed) == 8                     # 3 groups, 8 stones
    # exactly two red groups and one blue group, as the caption says
    removed_cols = [0 if x in R2 | R3 else 1 for x in (R2 | R3 | B2)]
    assert removed_cols.count(0) == 4 and removed_cols.count(1) == 4
    assert res.winner is None                        # both colours survive

    # --- PREMISE: the removals are SIMULTANEOUS ---------------------------- #
    # Sequentially removing R2 first would give (-1,2) exactly one red
    # neighbour, un-bounding R3 -- so a sequential implementation would leave
    # the seed alive and contradict Figure 2b.
    seq = dict(after.stones)
    for c in R2:
        del seq[C(c)]
    assert not G.is_bounded(seq, sp.nbrs, [C(x) for x in R3], 0), \
        "sequential removal no longer distinguishable -- the anchor is vacuous"
    assert G.is_bounded(after.stones, sp.nbrs, [C(x) for x in R3], 0)

    # --- PREMISE: R1 and B1 survive for a NAMED reason --------------------- #
    red_after = GAME.legal_moves(G.TakeState(size=3, churn=False, stones=after.stones,
                                             clods=after.clods, to_move=0))
    assert red_after == ["2,0"] and C("2,0") in sp.nbrs[C("2,-1")]
    blue_after = GAME.legal_moves(G.TakeState(size=3, churn=False, stones=after.stones,
                                              clods=after.clods, to_move=1))
    assert blue_after == ["2,-2"] and C("2,-2") in sp.nbrs[C("1,-2")]

    assert GAME.describe_move(before, PLACED_2A) == "Red 0,2 seed ×8 (incl. 4 own)"
    print("  figure 2a/2b OK — 3 groups / 8 stones removed, simultaneity pinned")


# --------------------------------------------------------------------------- #
# 3.  FIGURES 3a -> 3b — the High Churn variant
# --------------------------------------------------------------------------- #
FIG3A = dict(
    size=3, churn=True,
    red=["2,-2", "-1,-1", "0,-1", "1,-1", "1,1", "-1,2", "0,2"],
    blue=["0,-2", "2,-1", "0,0", "1,0", "-2,1", "-2,2"],
    # every cell drawn as a brown hexagon: unoccupied tiles AND tiles under a stone
    clods=["0,-2", "2,-2", "-1,-1", "1,-1", "2,-1", "-2,0", "-1,0", "0,0",
           "1,0", "0,1", "-2,2", "0,2"],
    to_move=1,
)
PLACED_3A = "1,1"
BB = {"2,-1", "0,0", "1,0"}


def test_figure3():
    sp = G.spec_for(3)
    after = state(**FIG3A)

    # --- premises: which cells carry a tile, which are bare ---------------- #
    # Stones drawn on a brown hexagon sit ON a tile; stones on a cream hexagon
    # do not.  Bare stones are the former seeds (plus this figure's placement).
    bare_stones = {N(c) for c in after.stones if c not in after.clods}
    assert bare_stones == {"0,-1", "-2,1", "-1,2", "1,1"}, bare_stones
    free_tiles = {N(c) for c in after.clods if c not in after.stones}
    assert free_tiles == {"-2,0", "-1,0", "0,1"}, free_tiles
    bare_free = {N(c) for c in sp.cells if c not in after.stones and c not in after.clods}
    assert bare_free == {"1,-2", "2,0", "-1,1"}, bare_free
    assert len(after.clods) == 12 and len(after.stones) == 13

    # --- the position BEFORE Red's placement ------------------------------- #
    before = state(size=3, churn=True,
                   red=sorted(set(FIG3A["red"]) - {PLACED_3A}),
                   blue=FIG3A["blue"], clods=FIG3A["clods"], to_move=0)
    assert C(PLACED_3A) not in before.clods           # placed on a BARE cell
    assert G.ally_count(before.stones, sp.nbrs, C(PLACED_3A), 0) == 1
    assert PLACED_3A in GAME.legal_moves(before)
    for col, comp in G.groups(before.stones, sp.nbrs):
        assert not G.is_bounded(before.stones, sp.nbrs, comp, col), comp
    # PREMISE: (1,1) was the blue group's ONLY growth cell.
    blue_before = GAME.legal_moves(G.TakeState(size=3, churn=True, stones=before.stones,
                                               clods=before.clods, to_move=1))
    bb_libs = {m for m in blue_before if any(C(m) in sp.nbrs[C(x)] for x in BB)}
    assert bb_libs == {PLACED_3A}, bb_libs

    # --- the figure's illustrated outcome ---------------------------------- #
    res = GAME.apply_move(before, PLACED_3A)
    assert set(N(c) for c in res.removed) == BB, res.removed
    # An ASYMMETRIC removal (3 enemy stones, 0 of Red's own) — Figure 2's split
    # is 4-4, so only this case can catch a colour swap in the move-log summary.
    assert GAME.describe_move(before, PLACED_3A) == "Red 1,1 ×3"
    # 3b: the three cleared cells revert to BARE TILES — the tile survived the
    # stone that stood on it.  This is the whole point of the variant.
    for c in BB:
        assert C(c) not in res.stones and C(c) in res.clods, c
    assert res.clods == after.clods, "no tile may be consumed by a removal"
    # and the placement itself consumed nothing (it was a non-seed on a bare cell)
    assert res.clods == before.clods

    # --- the same position in the BASE game diverges ------------------------ #
    # (proves the churn flag is load-bearing, not decoration)
    base_before = state(size=3, churn=False,
                        red=sorted(set(FIG3A["red"]) - {PLACED_3A}),
                        blue=FIG3A["blue"], clods=FIG3A["clods"], to_move=0)
    base = GAME.apply_move(base_before, PLACED_3A)
    assert base.clods == before.clods                # bare cell: nothing to eat
    # a SEED eats its clod/tile in BOTH variants
    hi = state(size=3, churn=True, red=["0,0"], clods=["0,-2", "1,-2"], to_move=0)
    lo = state(size=3, churn=False, red=["0,0"], clods=["0,-2", "1,-2"], to_move=0)
    assert C("0,-2") not in GAME.apply_move(hi, "0,-2").clods
    assert C("0,-2") not in GAME.apply_move(lo, "0,-2").clods
    # a GROWTH stone on a tile: kept in High Churn, eaten in the base game
    hi2 = state(size=3, churn=True, red=["0,-1"], clods=["0,-2"], to_move=0)
    lo2 = state(size=3, churn=False, red=["0,-1"], clods=["0,-2"], to_move=0)
    assert G.ally_count(hi2.stones, G.spec_for(3).nbrs, C("0,-2"), 0) == 1
    assert C("0,-2") in GAME.apply_move(hi2, "0,-2").clods
    assert C("0,-2") not in GAME.apply_move(lo2, "0,-2").clods
    print("  figure 3a/3b OK — tile persistence + seed-eats-tile in both variants")


# --------------------------------------------------------------------------- #
# 4.  EXHAUSTIVE SOLVE of the smallest legal board (side 2, 7 cells)
# --------------------------------------------------------------------------- #
# Frozen results.  Re-derived from scratch on every run; the numbers are the
# transcription being checked, so a ruleset change moves them.
SOLVED = {
    (2, False): {"value": -1.0, "length": 9, "states": 1683},
    (2, True): {"value": -1.0, "length": 10, "states": 4330},
}


def test_exhaustive_size2():
    sys.setrecursionlimit(20000)
    for churn in (False, True):
        memo, onstack = {}, set()
        seen_keys = set()

        def key(s):
            return (tuple(sorted(s.stones.items())), s.clods, s.to_move)

        def solve(s, depth):
            k = key(s)
            if k in memo:
                return memo[k]
            assert k not in onstack, "a POSITION REPEATED — the game is not a DAG"
            # every reachable state gets fully audited, once
            if k not in seen_keys:
                seen_keys.add(k)
                audit(s)
            if GAME.is_terminal(s):
                assert GAME.returns(s) in ([1.0, -1.0], [-1.0, 1.0]), \
                    "a terminal Take position must be decisive"
                memo[k] = (GAME.returns(s)[0], depth)
                return memo[k]
            ms = GAME.legal_moves(s)
            assert ms, "a non-terminal position with no legal placement"
            onstack.add(k)
            best = bl = None
            for m in ms:
                v, ln = solve(GAME.apply_move(s, m), depth + 1)
                if s.to_move == 0:
                    better = (best is None or v > best or
                              (v == best and ((v > 0 and ln < bl) or (v <= 0 and ln > bl))))
                else:
                    better = (best is None or v < best or
                              (v == best and ((v < 0 and ln < bl) or (v >= 0 and ln > bl))))
                if better:
                    best, bl = v, ln
            onstack.discard(k)
            memo[k] = (best, bl)
            return memo[k]

        def audit(s):
            sp = G.spec_for(s.size)
            # serialize/deserialize compared as STATES, exact key set
            d = GAME.serialize(s)
            assert set(d) == {"size", "churn", "stones", "clods", "to_move",
                              "winner", "last", "removed", "plies"}, sorted(d)
            assert GAME.deserialize(d) == s
            # the base game never has a stone and a clod on the same cell
            if not s.churn:
                assert not (set(s.stones) & s.clods)
            # is_bounded agrees with the legal-move formulation, both colours
            for col, comp in G.groups(s.stones, sp.nbrs):
                assert G.is_bounded(s.stones, sp.nbrs, comp, col) == \
                    bounded_via_moves(s, col, comp)
            # ...and NOTHING is bounded at the start of a turn (the no-stuck proof)
            for col, comp in G.groups(s.stones, sp.nbrs):
                assert not G.is_bounded(s.stones, sp.nbrs, comp, col), \
                    "a bounded group survived into the next turn"

        v, ln = solve(GAME.initial_state({"size": 2, "churn": "high" if churn else "standard"}), 0)
        exp = SOLVED[(2, churn)]
        assert (v, ln, len(memo)) == (exp["value"], exp["length"], exp["states"]), \
            f"churn={churn}: got value={v} len={ln} states={len(memo)}, expected {exp}"
        print(f"  side-2 {'high churn' if churn else 'base'} solved: "
              f"value(Red)={v:+.0f} (Blue wins) optimal length={ln} "
              f"over {len(memo)} reachable positions — DAG, no draws, no stuck states")


# --------------------------------------------------------------------------- #
# 5.  Termination monovariant + no-stuck + round-trip over whole games
# --------------------------------------------------------------------------- #

def test_monovariant_and_roundtrip():
    rnd = random.Random(20240220)
    plies = 0
    for size in (2, 3, 4, 5, 6):
        bound = G.PLY_BOUND(size)
        assert bound == (len(G.spec_for(size).cells) + 1) ** 3
        for churn in ("standard", "high"):
            for _ in range(6 if size < 6 else 2):
                s = GAME.initial_state({"size": size, "churn": churn})
                prev = potential(s)
                n = 0
                while not GAME.is_terminal(s):
                    ms = GAME.legal_moves(s)
                    assert ms, f"stuck at size={size} churn={churn} ply={n}"
                    assert GAME.deserialize(GAME.serialize(s)) == s
                    s = GAME.apply_move(s, rnd.choice(ms))
                    cur = potential(s)
                    assert cur < prev, \
                        f"monovariant did not decrease: {prev} -> {cur}"
                    prev = cur
                    n += 1
                    assert n < bound
                assert GAME.deserialize(GAME.serialize(s)) == s
                assert GAME.returns(s) in ([1.0, -1.0], [-1.0, 1.0])
                plies += n
    print(f"  monovariant (clods, groups, free cells) strictly lex-decreased on "
          f"all {plies} plies; every state round-tripped")


# --------------------------------------------------------------------------- #
# 6.  Every win condition, reached THROUGH apply_move, + caption attribution
# --------------------------------------------------------------------------- #

def test_win_conditions():
    rnd = random.Random(99)
    kinds = {}
    for _ in range(400):
        s = GAME.initial_state({"size": 2})
        while not GAME.is_terminal(s):
            mover = s.to_move
            prev = s
            s = GAME.apply_move(s, rnd.choice(GAME.legal_moves(s)))
        mine = sum(1 for v in s.stones.values() if v == mover)
        theirs = sum(1 for v in s.stones.values() if v != mover)
        if not s.stones:
            k = "total annihilation"
            assert s.winner == mover, "the MOVER wins when everything goes"
        elif mine == 0:
            k = "self-elimination"
            assert s.winner == 1 - mover
        else:
            k = "enemy eliminated"
            assert s.winner == mover and theirs == 0
        kinds.setdefault(k, 0)
        kinds[k] += 1
        # (11) the render caption is NOT on the legality path — check it names
        # the real winner, and that the loser's name never leads.
        cap = GAME.render(s)["caption"]
        assert cap.startswith(G.SEAT_NAMES[s.winner] + " wins"), cap
        assert G.SEAT_NAMES[1 - s.winner] in cap
        assert GAME.returns(s)[s.winner] == 1.0
        # and a non-terminal caption never claims a win
        assert "wins" not in GAME.render(prev)["caption"]
    assert set(kinds) == {"total annihilation", "self-elimination", "enemy eliminated"}, kinds
    print(f"  all three win conditions reached via apply_move: {kinds}")

    # The ply-1 guard: Blue has no stones after Red's first move, but nothing
    # has been *removed*, so the game must NOT be over.
    for size in G.SIZES:
        for churn in ("standard", "high"):
            s = GAME.initial_state({"size": size, "churn": churn})
            assert len(GAME.legal_moves(s)) == len(G.spec_for(size).cells)
            for m in GAME.legal_moves(s):
                t = GAME.apply_move(s, m)
                assert t.winner is None and not GAME.is_terminal(t)
                assert sum(1 for v in t.stones.values() if v == 1) == 0
                # a lone opening seed can never bound itself on any board
                assert len(t.stones) == 1 and not t.removed
    print("  ply-1 guard OK — an opponent who has not played yet is not 'eliminated'")

    # ...and the guard must be `before_other > 0`, NOT `> 1`: winning by taking
    # the opponent's LAST AND ONLY stone is a real, reachable win.  It cannot be
    # reached on the side-2 board (a one-stone group is bounded only when every
    # one of its neighbours is occupied, and side 2 never gets there), so the
    # exhaustive solve above is blind to it and random play essentially never
    # produces it — a directed search finds it 15 times in 2,500 side-3 games.
    # Constructed input, played THROUGH apply_move, in both seat directions.
    for mover in (0, 1):
        s = G.TakeState(
            size=3, churn=False,
            stones={C("2,-1"): mover, C("1,-1"): mover, C("2,-2"): 1 - mover},
            clods=frozenset(C(x) for x in ("1,-2", "0,-2", "0,-1")), to_move=mover)
        # PREMISES: it is a legal start-of-turn position (nothing bounded), the
        # opponent holds EXACTLY one stone, and the mover keeps stones afterwards
        # — so it is the third win branch, not annihilation and not self-loss.
        sp = G.spec_for(3)
        for col, comp in G.groups(s.stones, sp.nbrs):
            assert not G.is_bounded(s.stones, sp.nbrs, comp, col), comp
        assert sum(1 for v in s.stones.values() if v != mover) == 1
        assert "1,-2" in GAME.legal_moves(s)
        t = GAME.apply_move(s, "1,-2")
        assert t.removed == (C("2,-2"),), t.removed
        assert sum(1 for v in t.stones.values() if v == mover) == 3
        assert sum(1 for v in t.stones.values() if v != mover) == 0
        assert t.winner == mover, \
            f"taking the opponent's only stone must win for seat {mover}"
        assert GAME.render(t)["caption"].startswith(G.SEAT_NAMES[mover] + " wins")
    print("  taking the opponent's LAST stone wins, for both seats "
          "(before_other == 1 — unreachable on side 2, so constructed)")


# --------------------------------------------------------------------------- #
# 7.  render() bounds for EVERY board size, from far-corner positions
# --------------------------------------------------------------------------- #

def test_render_bounds():
    rnd = random.Random(5)
    self_swept = [False]      # did a placement ever sweep away its own stone?
    for size in G.SIZES:
        sp = G.spec_for(size)
        ids = {N(c) for c in sp.cells}
        for churn in ("standard", "high"):
            reached_rim = False
            stone_on_tile = False
            for _ in range(4):
                s = GAME.initial_state({"size": size, "churn": churn})
                while True:
                    spec = GAME.render(s)
                    b = spec["board"]
                    assert b["type"] == "hex" and b["shape"] == "hexagon"
                    assert b["size"] == size, (size, b["size"])
                    piece_cells = {p["cell"] for p in spec["pieces"]}
                    assert piece_cells == {N(c) for c in s.stones}
                    for p in spec["pieces"]:
                        assert p["cell"] in ids, (size, p["cell"])
                        assert p["owner"] == s.stones[C(p["cell"])]
                    # every clod/tile is drawn, and nothing else is
                    assert set(b["tints"]) == {N(c) for c in s.clods}, (size, churn)
                    assert set(b["tints"].values()) <= {G.CLOD_TINT}
                    for cid in b["tints"]:
                        assert cid in ids, (size, cid)
                    both = piece_cells & set(b["tints"])
                    if churn == "standard":
                        assert not both, "a base-game clod cannot sit under a stone"
                    elif both:
                        stone_on_tile = True
                    for h in spec["highlights"]:
                        assert h["cell"] in ids
                        assert h["kind"] in ("last-move", "goal"), h
                        if h["kind"] == "goal":
                            assert C(h["cell"]) in s.removed, h
                        else:
                            # the last-move marker belongs to the stone that is
                            # still standing; when the placement swept ITSELF
                            # away the cell is empty and gets the `goal` marker
                            # instead, never a marker for a stone that is gone.
                            assert C(h["cell"]) == s.last and C(h["cell"]) in s.stones, h
                    if s.last is not None and s.last not in s.stones:
                        assert not any(h["kind"] == "last-move"
                                       for h in spec["highlights"]), spec["highlights"]
                        self_swept[0] = True
                    rim = [p["cell"] for p in spec["pieces"]
                           if max(abs(C(p["cell"])[0]), abs(C(p["cell"])[1]),
                                  abs(sum(C(p["cell"])))) == size - 1]
                    if rim:
                        reached_rim = True
                    if GAME.is_terminal(s):
                        break
                    s = GAME.apply_move(s, rnd.choice(GAME.legal_moves(s)))
            assert reached_rim, f"size {size} churn {churn}: no outer-ring stone seen"
            if churn == "high":
                assert stone_on_tile, \
                    f"size {size}: no High-Churn stone ever drawn ON a tile"
    # non-vacuity: the "the placement swept itself away" branch above only means
    # something if the sweep actually reached it.
    assert self_swept[0], "no self-sweeping placement seen — the last-move " \
                          "highlight check is vacuous"
    print(f"  render() bounds OK for sizes {G.SIZES} x both variants, "
          f"with stones on the outermost ring, stones on tiles (High Churn), "
          f"and no last-move marker on a swept-away stone")


# --------------------------------------------------------------------------- #
# 8.  legal-move / apply_move guards
# --------------------------------------------------------------------------- #

def test_guards():
    s = GAME.initial_state({"size": 3})
    for bad in ("9,9", "0,-3"):
        try:
            GAME.apply_move(s, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"off-board move {bad} accepted")
    t = GAME.apply_move(s, "0,0")
    try:
        GAME.apply_move(t, "0,0")            # occupied
    except ValueError:
        pass
    else:
        raise AssertionError("placement on an occupied cell accepted")
    # apply_move must not mutate its input
    snap = GAME.serialize(s)
    GAME.apply_move(s, "0,0")
    assert GAME.serialize(s) == snap
    # a finished game offers no moves
    fin = state(size=2, churn=False, red=["0,0"], to_move=1, winner=0)
    assert GAME.legal_moves(fin) == [] and GAME.is_terminal(fin)
    print("  guards OK — off-board / occupied / purity / terminal")


if __name__ == "__main__":
    print("Take — selftest")
    test_figure1()
    test_figure2()
    test_figure3()
    test_exhaustive_size2()
    test_monovariant_and_roundtrip()
    test_win_conditions()
    test_render_bounds()
    test_guards()
    print("ALL OK")
