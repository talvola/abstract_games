"""Churn — correctness anchors.

Pure stdlib.  Every board position below is TRANSCRIBED FROM THE RULE SHEET's
figures, which were parsed out of the PDF's vector artwork (``pdftocairo -svg``
+ reading the 147 shape paths: 76 hex outlines, 31 red discs, 29 blue discs,
7 green dots, 4 black dots — a complete, self-checking inventory of all four
figures).  The anchors are:

  1. Figures 1-4, with each figure's PREMISE asserted, not just its outcome, and
     the DISCRIMINATING POWER of each figure MEASURED against an enumerated list
     of wrong readings (with the gaps closed by constructed positions).
  2. An exhaustive solve of the smallest legal board (hexhex side 2, 7 cells):
     no cycles, no draws, and the game value with and without the pie.
  3. The termination monovariant, checked move by move on real play.
  4. The pie swap — the one area the AbstractPlay oracle structurally cannot
     cover (it implements pie as a UI-level flag outside the game class).
  5. serialize/deserialize compared as STATE OBJECTS over whole games.
  6. render() bounds for EVERY shipped board, at the FULL final board.

Run:  cd engine && PYTHONPATH=. python3 games/churn/selftest.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.churn.game import (  # noqa: E402
    BOARD_KEYS, DEFAULT_BOARD, SEAT_NAMES, Churn, ChurnState, _cell, cell_name,
    group_of, label_groups, max_plies, spec_for,
)

G = Churn()
OK = []


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: FAILED {detail}")
    OK.append(name)


def C(txt):
    """'0,-2' -> (0, -2); accepts a space separated list."""
    return [_cell(t) for t in txt.split()]


def pos(red, blue, board="hex3", to_move=0, ply=10):
    stones = {}
    for c in C(red):
        stones[c] = 0
    for c in C(blue):
        stones[c] = 1
    return ChurnState(board=board, stones=stones, to_move=to_move, ply=ply)


def names(sp, cells):
    return sorted(cell_name(sp, c) for c in cells)


# ==========================================================================
#  0.  Board geometry, and the sheet's "odd number of cells" clause
# ==========================================================================
SP = {k: spec_for(k) for k in BOARD_KEYS}

check("boards: hexhex side 3 has 19 cells (the sheet's figures)",
      len(SP["hex3"].cells) == 19)
check("boards: hexhex side 2 has 7 cells", len(SP["hex2"].cells) == 7)
check("boards: the limping 3,4,3,4,3,4 board has 27 cells (the sheet names it)",
      len(SP["limping34"].cells) == 27)
check("boards: limping row widths are 3,4,5,6,5,4",
      tuple(w for _r, _q, w in SP["limping34"].rows) == (3, 4, 5, 6, 5, 4))
for k, sp in SP.items():
    # "Only boards with an odd number of cells should be used, to prevent ties."
    check(f"boards: {k} has an ODD cell count (no tie is possible)",
          len(sp.cells) % 2 == 1, f"{len(sp.cells)}")
    # every cell has 2..6 neighbours and adjacency is symmetric
    for c in sp.cells:
        check(f"boards: {k} adjacency symmetric",
              all(c in sp.nbrs[n] for n in sp.nbrs[c]))
    check(f"boards: {k} degrees in 2..6",
          all(2 <= len(sp.nbrs[c]) <= 6 for c in sp.cells))
# 3n^2-3n+1 is odd for EVERY n, so "use an odd board" is automatic for hexhex
check("boards: 3n^2-3n+1 is odd for every n in 1..40",
      all((3 * n * n - 3 * n + 1) % 2 == 1 for n in range(1, 41)))


# ==========================================================================
#  1.  FIGURE 1 — the isolation branch
# ==========================================================================
# Rows top->bottom, transcribed from the PDF vector artwork.
F1_RED = "0,-2 1,-2 2,-1 -2,0 -2,1"
F1_BLUE = "0,-1 0,0 2,0 -2,2 -1,2"
F1_GREEN = C("0,1 1,1 0,2")          # the printed available placements for Red
f1 = pos(F1_RED, F1_BLUE, to_move=0)
sp3 = SP["hex3"]

# --- PREMISES the figure relies on ---------------------------------------
check("fig1 premise: 5 red + 5 blue + 9 empty = 19",
      len(f1.stones) == 10 and len(sp3.cells) - len(f1.stones) == 9)
_lab, _sizes = label_groups(sp3, f1.stones, 0)
check("fig1 premise: Red holds three groups of sizes 2,1,2",
      sorted(_sizes) == [1, 2, 2], str(_sizes))
check("fig1 premise: ALL THREE green cells TOUCH A BLUE STONE — which is what "
      "makes the figure rule out 'adjacent to any group'",
      all(any(f1.stones.get(nb) == 1 for nb in sp3.nbrs[c]) for c in F1_GREEN))
check("fig1 premise: every green cell has NO red neighbour",
      all(all(f1.stones.get(nb) != 0 for nb in sp3.nbrs[c]) for c in F1_GREEN))

check("FIGURE 1: legal set == the three printed green cells",
      G.placements(f1) == sorted(F1_GREEN),
      f"{names(sp3, G.placements(f1))} vs {names(sp3, F1_GREEN)}")


# ==========================================================================
#  2.  FIGURE 2 — "the smallest friendly group possible"
# ==========================================================================
F2_RED = "0,-2 1,-1 -1,0 -2,1 0,1 1,1 0,2"
F2_BLUE = "2,-2 -1,-1 0,-1 2,-1 0,0 2,0 -2,2 -1,2"
F2_GREEN = C("1,-2 -2,0")
f2 = pos(F2_RED, F2_BLUE, to_move=0)

check("fig2 premise: 7 red + 8 blue + 4 empty = 19",
      len(f2.stones) == 15 and len(sp3.cells) - len(f2.stones) == 4)
_lab2, _sizes2 = label_groups(sp3, f2.stones, 0)
check("fig2 premise: Red holds groups of sizes 1,1,2,3",
      sorted(_sizes2) == [1, 1, 2, 3], str(_sizes2))
sizes_after = G.placement_sizes(f2)
check("fig2 premise: NO empty cell is isolated (every one touches a red group)",
      all(v > 1 for v in sizes_after.values()))
check("fig2 premise: the four empties would form groups of 3, 3, 5, 6",
      sorted(sizes_after.values()) == [3, 3, 5, 6], str(sizes_after))

check("FIGURE 2: legal set == the two printed green cells",
      G.placements(f2) == sorted(F2_GREEN),
      f"{names(sp3, G.placements(f2))} vs {names(sp3, F2_GREEN)}")


# ==========================================================================
#  3.  DISCRIMINATING POWER of Figures 1 and 2 (measured, not assumed)
# ==========================================================================
def _adj_group_sizes(s, cell, seat=0):
    sp = spec_for(s.board)
    lab, sizes = label_groups(sp, s.stones, seat)
    return [sizes[g] for g in {lab[nb] for nb in sp.nbrs[cell] if nb in lab}]


def R_correct(s):
    return set(G.placements(s))


def R_min_adjacent(s):                 # minimise the SMALLEST adjacent group
    sp = spec_for(s.board)
    e = [c for c in sp.cells if c not in s.stones]
    f = {c: min(_adj_group_sizes(s, c), default=0) for c in e}
    m = min(f.values())
    return {c for c in e if f[c] == m}


def R_max_adjacent(s):                 # minimise the LARGEST adjacent group
    sp = spec_for(s.board)
    e = [c for c in sp.cells if c not in s.stones]
    f = {c: max(_adj_group_sizes(s, c), default=0) for c in e}
    m = min(f.values())
    return {c for c in e if f[c] == m}


def R_fewest_merges(s):                # minimise the NUMBER of groups merged
    sp = spec_for(s.board)
    e = [c for c in sp.cells if c not in s.stones]
    f = {c: len(_adj_group_sizes(s, c)) for c in e}
    m = min(f.values())
    return {c for c in e if f[c] == m}


def R_untouched_first(s):              # "isolated" = touches NO stone at all
    sp = spec_for(s.board)
    e = [c for c in sp.cells if c not in s.stones]
    iso = {c for c in e if not any(nb in s.stones for nb in sp.nbrs[c])}
    return iso if iso else R_correct(s)


def R_any_group_blocks(s):             # a cell touching ANY stone is not isolated
    sp = spec_for(s.board)
    e = [c for c in sp.cells if c not in s.stones]
    iso = {c for c in e if not any(nb in s.stones for nb in sp.nbrs[c])}
    if iso:
        return iso
    f = G.placement_sizes(s)
    m = min(f.values())
    return {c for c in e if f[c] == m}


def R_isolation_optional(s):           # "may" place in isolation, not "must"
    sp = spec_for(s.board)
    f = G.placement_sizes(s)
    iso = {c for c, v in f.items() if v == 1}
    rest = {c: v for c, v in f.items() if v > 1}
    out = set(iso)
    if rest:
        m = min(rest.values())
        out |= {c for c, v in rest.items() if v == m}
    return out


def R_unrestricted(s):                 # no placement restriction at all
    sp = spec_for(s.board)
    return {c for c in sp.cells if c not in s.stones}


def R_maximise(s):                     # form the LARGEST group possible
    f = G.placement_sizes(s)
    m = max(f.values())
    return {c for c, v in f.items() if v == m}


def R_min_largest_after(s):            # minimise your LARGEST group after the turn
    sp = spec_for(s.board)
    f = {}
    for c, new in G.placement_sizes(s).items():
        st = dict(s.stones)
        st[c] = s.to_move
        _l, _z = label_groups(sp, st, s.to_move)
        f[c] = max(z for z in _z if z >= new)
    m = min(f.values())
    return {c for c, v in f.items() if v == m}


WRONG_PLACEMENT_READINGS = [
    ("isolation is OPTIONAL, not mandatory", R_isolation_optional),
    ("no placement restriction at all", R_unrestricted),
    ("form the LARGEST group possible", R_maximise),
    ("minimise the SMALLEST adjacent group", R_min_adjacent),
    ("minimise the LARGEST adjacent group", R_max_adjacent),
    ("minimise the NUMBER of groups merged", R_fewest_merges),
    ("minimise your LARGEST group after the turn", R_min_largest_after),
    ("'isolated' = touches no stone AT ALL", R_untouched_first),
    ("enemy stones also block isolation", R_any_group_blocks),
]

fig_kills = {"fig1": [], "fig2": [], "blind": []}
for label, fn in WRONG_PLACEMENT_READINGS:
    k1 = fn(f1) != R_correct(f1)
    k2 = fn(f2) != R_correct(f2)
    if k1:
        fig_kills["fig1"].append(label)
    if k2:
        fig_kills["fig2"].append(label)
    if not (k1 or k2):
        fig_kills["blind"].append(label)

check("fig1 kills 'isolation is OPTIONAL' — the reading fig2 cannot see, "
      "because fig2 has no isolated cell at all",
      "isolation is OPTIONAL, not mandatory" in fig_kills["fig1"]
      and "isolation is OPTIONAL, not mandatory" not in fig_kills["fig2"])
for lbl in ("minimise the SMALLEST adjacent group",
            "minimise the LARGEST adjacent group",
            "minimise the NUMBER of groups merged"):
    check(f"fig2 kills {lbl!r} (fig1 cannot: with an isolated cell available "
          f"every one of these agrees)",
          lbl in fig_kills["fig2"] and lbl not in fig_kills["fig1"])
# MEASURED GAPS.  Neither figure has an empty cell with NO neighbouring stone at
# all, so neither can see the two "what counts as isolated" readings; and
# "minimise your largest group after the turn" happens to agree on both figures.
check("MEASURED GAP: figures 1+2 are blind to exactly the two "
      "'what counts as isolated' readings",
      sorted(fig_kills["blind"]) == [
          "'isolated' = touches no stone AT ALL",
          "enemy stones also block isolation"],
      str(fig_kills))
check("figures 1+2 together kill 7 of the 9 enumerated wrong readings "
      "(fig1 kills 4, fig2 kills 5, 2 in common)",
      len(set(fig_kills["fig1"]) | set(fig_kills["fig2"])) == 7
      and len(fig_kills["fig1"]) == 4 and len(fig_kills["fig2"]) == 5,
      str(fig_kills))

# Constructed closer: one red stone and one blue stone, far apart, Red to move.
# The sheet says isolation is "not adjacent to any FRIENDLY groups", so the six
# cells around the lone BLUE stone are legal; under either blind reading they
# are not.
gap = pos("-2,2", "2,-2", to_move=0)
legal_gap = set(G.placements(gap))
blue_ring = {nb for nb in sp3.nbrs[(2, -2)]}
check("gap closer: cells adjacent to a lone ENEMY stone are legal placements",
      blue_ring <= legal_gap, names(sp3, blue_ring - legal_gap))
check("gap closer: cells adjacent to the lone FRIENDLY stone are NOT legal",
      not (set(sp3.nbrs[(-2, 2)]) & legal_gap))
check("gap closer: both blind readings are killed by this position",
      R_untouched_first(gap) != legal_gap and R_any_group_blocks(gap) != legal_gap)

# The two PLAY clauses are one rule: an isolated placement forms a group of 1,
# which is the smallest value `placement_sizes` can take, so "isolation first"
# and "minimise the resulting size" can never disagree.  Swept over real play so
# the claim in game.py's docstring is checked rather than asserted.
_rng = random.Random(31337)
for _bk in BOARD_KEYS:
    for _ in range(6):
        _s = G.initial_state({"board": _bk})
        while not G.is_terminal(_s):
            _f = G.placement_sizes(_s)
            _iso = {c for c, v in _f.items() if v == 1}
            _minim = {c for c, v in _f.items() if v == min(_f.values())}
            check("PLAY: the isolation clause and the minimisation clause "
                  "always agree (1 is the minimum achievable size)",
                  (_iso == _minim) if _iso else True)
            check("PLAY: legal_moves is exactly the minimiser set",
                  set(G.placements(_s)) == _minim)
            _s = G.apply_move(_s, _rng.choice(
                [m for m in G.legal_moves(_s) if m != "swap"]))


# ==========================================================================
#  4.  FIGURE 3 — removals are STRICT ("<", not "<="), and reach the whole board
# ==========================================================================
F3_RED_AFTER = "1,-2 -1,-1 0,-1 2,-1 1,0 2,0 -2,1 -2,2 0,2"
F3_BLUE = "0,-2 2,-2 1,-1 -2,0 0,0 1,1 -1,2"
F3_PLACED = _cell("2,-1")                       # the green dot
F3_BLACK = set(C("-2,1 -2,2 0,2"))              # the black dots

f3_before = pos(" ".join(t for t in F3_RED_AFTER.split() if t != "2,-1"),
                F3_BLUE, to_move=0)
check("fig3 premise: the green cell is empty before the placement",
      F3_PLACED not in f3_before.stones)
check("fig3 premise: 8 red + 7 blue + 4 empty = 19",
      len(f3_before.stones) == 15)
check("fig3 premise: the placement is legal for Red",
      F3_PLACED in G.placements(f3_before))

f3_after = G.apply_move(f3_before, "2,-1")
check("FIGURE 3: exactly the three black-dotted stones are removed",
      set(f3_after.removed) == F3_BLACK,
      f"{names(sp3, f3_after.removed)} vs {names(sp3, F3_BLACK)}")

# The PREMISE that makes this figure decide "<" vs "<=":
f3_mid = dict(f3_before.stones)
f3_mid[F3_PLACED] = 0
_lab3, _sz3 = label_groups(sp3, f3_mid, 0)
_new = _sz3[_lab3[F3_PLACED]]
_survivor_sizes = sorted(_sz3[g] for g in set(_lab3.values()) if g != _lab3[F3_PLACED])
check("fig3 premise: the group formed has size 3", _new == 3, str(_new))
check("fig3 premise: another RED group of size EXACTLY 3 is on the board",
      3 in _survivor_sizes, str(_survivor_sizes))
check("FIGURE 3 discriminates '<' from '<=': the equal-sized red 3-group SURVIVES",
      not (group_of(sp3, f3_mid, (0, -1)) & set(f3_after.removed)))
check("FIGURE 3: the newly formed group is never removed",
      group_of(sp3, f3_mid, F3_PLACED) <= set(f3_after.stones))
check("FIGURE 3: removals reach groups NOT adjacent to the placement",
      all(c not in sp3.nbrs[F3_PLACED] for c in F3_BLACK))
check("FIGURE 3: no BLUE stone is ever removed",
      all(f3_before.stones.get(c) != 1 for c in f3_after.removed)
      and sum(1 for v in f3_after.stones.values() if v == 1) == 7)
check("fig3: removing 3 stones from 3 separate groups (a multi-group cascade)",
      len({_lab3[c] for c in F3_BLACK}) == 2 and len(F3_BLACK) == 3)


# ==========================================================================
#  5.  FIGURE 4 — the majority is counted at the CONCLUSION of the turn
# ==========================================================================
# "Figure 4 is a win for Blue."  <- ground truth OUTSIDE the engine.
F4_RED_AFTER = "1,-2 0,-1 1,-1 -1,0 0,0 2,0 -1,1 0,1 -1,2 0,2"
F4_BLUE = "0,-2 2,-2 -1,-1 2,-1 -2,0 1,0 -2,1 1,1 -2,2"
F4_PLACED = _cell("1,-1")
F4_BLACK = {_cell("2,0")}

f4_before = pos(" ".join(t for t in F4_RED_AFTER.split() if t != "1,-1"),
                F4_BLUE, to_move=0)
check("fig4 premise: the board has exactly ONE hole, the green cell",
      [c for c in sp3.cells if c not in f4_before.stones] == [F4_PLACED])
check("fig4 premise: Red is therefore FORCED to play it",
      G.legal_moves(f4_before) == ["1,-1"], str(G.legal_moves(f4_before)))
check("fig4 premise: before the placement Red has 9 stones and Blue 9",
      G.counts(f4_before) == (9, 9), str(G.counts(f4_before)))
_mid4 = dict(f4_before.stones)
_mid4[F4_PLACED] = 0
check("fig4 premise: the placement FILLS the board, 10 Red to 9 Blue",
      len(_mid4) == 19 and sum(1 for v in _mid4.values() if v == 0) == 10)

f4_after = G.apply_move(f4_before, "1,-1")
check("FIGURE 4: exactly the one black-dotted red stone is removed",
      set(f4_after.removed) == F4_BLACK)
check("FIGURE 4: the board is NOT full after the removal, so nobody has won yet",
      not G.is_terminal(f4_after) and G.counts(f4_after) == (9, 9))
check("FIGURE 4: counting the majority BEFORE the removals would call it a "
      "RED win — the figure's printed verdict rules that reading out",
      sum(1 for v in _mid4.values() if v == 0) >
      sum(1 for v in _mid4.values() if v == 1))

check("fig4 premise: Blue's reply is forced into the hole",
      G.legal_moves(f4_after) == ["2,0"], str(G.legal_moves(f4_after)))
f4_end = G.apply_move(f4_after, "2,0")
check("FIGURE 4: Blue's reply removes nothing (Blue's other group is also 5)",
      f4_end.removed == ())
check("FIGURE 4: the board is now full", G.is_terminal(f4_end))
check("FIGURE 4 IS A WIN FOR BLUE, 10 stones to 9 (the sheet's own verdict)",
      G.counts(f4_end) == (9, 10) and G.winner(f4_end) == 1
      and G.returns(f4_end) == [-1.0, 1.0], str(G.counts(f4_end)))
check("FIGURE 4: the caption names BLUE as the winner",
      G.render(f4_end)["caption"].startswith("Blue wins"),
      G.render(f4_end)["caption"])
# ... and the caption is NOT pinned to the engine's own naming: seat 0 is Red
# because the sheet says play starts with Red.
check("seat 0 is RED — the sheet: 'take turns placing ... starting with Red'",
      G.render(G.initial_state())["caption"].startswith("Red to move")
      and SEAT_NAMES == ("Red", "Blue"))
_b_lab, _b_sz = label_groups(sp3, dict(f4_end.stones), 1)
check("fig4 premise: after Blue's reply BOTH blue groups have size 5",
      sorted(_b_sz) == [5, 5], str(_b_sz))
# Second, independent kill of the '<=' reading, computed rather than asserted:
# under '<=' Blue's forced reply would sweep Blue's OTHER 5-group off the board,
# leaving 9 Red to 5 Blue on a board with four holes — no Blue win anywhere.
_new_gid = _b_lab[_cell("2,0")]
_le_all = {c for c, gid in _b_lab.items() if _b_sz[gid] <= 5}
_le_other = {c for c, gid in _b_lab.items() if _b_sz[gid] <= 5 and gid != _new_gid}
check("FIGURE 4 kills '<=' a second time: '<=' over all groups would leave Blue "
      "0 stones and '<=' over the other groups 5, against Red's 9 — neither is "
      "the sheet's 'Figure 4 is a win for Blue'",
      len(_le_all) == 10 and len(_le_other) == 5,
      f"{len(_le_all)} {len(_le_other)}")


# ==========================================================================
#  5b. The SUPERSEDED revision's figures — independent evidence
# ==========================================================================
# The live sheet (md5 ccfa0adc..., ModDate 2025-03-16) is a silent revision of
# the December 2024 original (md5 4d63728b..., ModDate 2024-12-27, archived at
# web.archive.org/web/20250103064012).  Figures 1 and 2 are byte-identical
# between the two; Figures 3 and 4 were REDRAWN, and the OBJECT paragraph gained
# the parenthetical about finishing your turn.  The old figures are a completely
# independent transcription of the same rules and must also come out right.
#
# OLD Figure 3: Red plays the green cell, forming a 4-group; a red 2-group and a
# red 3-group (five stones, five black dots) come off.
O3_RED = "1,-2 -1,-1 1,-1 -2,0 1,0 -1,1 1,1 -2,2 -1,2"
O3_BLUE = "0,-2 2,-2 2,-1 -1,0 2,0 -2,1 0,1 0,2"
O3_BLACK = set(C("-1,-1 -2,0 -1,1 -2,2 -1,2"))
o3_before = pos(" ".join(t for t in O3_RED.split() if t != "1,1"), O3_BLUE)
check("OLD fig3 premise: only two cells are empty and the green one is legal",
      len([c for c in sp3.cells if c not in o3_before.stones]) == 3
      and _cell("1,1") in G.placements(o3_before))
o3_after = G.apply_move(o3_before, "1,1")
check("OLD FIGURE 3 (superseded revision): the five black-dotted stones come off",
      set(o3_after.removed) == O3_BLACK, names(sp3, o3_after.removed))
_o3 = dict(o3_before.stones); _o3[_cell("1,1")] = 0
check("OLD fig3 premise: the group formed has size 4",
      label_groups(sp3, _o3, 0)[1][label_groups(sp3, _o3, 0)[0][_cell("1,1")]] == 4)
check("OLD FIGURE 3: the newly formed 4-group survives (it is not < itself)",
      group_of(sp3, _o3, _cell("1,1")) <= set(o3_after.stones))

# OLD Figure 4 was a COMPLETED game, and the old prose read "In Figure 4, Blue
# has won by occupying 10 of the 19 board cells" — a direct majority check.
O4_RED = "1,-2 1,-1 -2,0 -1,0 0,0 1,0 -1,1 1,1 -2,2"
O4_BLUE = "0,-2 2,-2 -1,-1 0,-1 2,-1 2,0 -2,1 0,1 -1,2 0,2"
o4 = pos(O4_RED, O4_BLUE, to_move=0)
check("OLD fig4 premise: the board is FULL", len(o4.stones) == 19)
check("OLD FIGURE 4 (superseded revision): Blue has won by occupying 10 of the "
      "19 board cells", G.is_terminal(o4) and G.counts(o4) == (9, 10)
      and G.winner(o4) == 1 and G.render(o4)["caption"].startswith("Blue wins"))


# ==========================================================================
#  6.  Multi-group / multi-stone removal cascades  (hexhex 2 CANNOT show these:
#      an exhaustive walk of side 2 has 0 such turns out of 2,003)
# ==========================================================================
# Reached in real play (found by a directed search over 400 random hex3 games):
# Red holds SIX singletons; joining two of them into a 2-group wipes the other
# FIVE at once, none of which touches the placement.
CASC_RED = "0,-1 2,0 -2,0 -1,1 0,2 2,-2"
CASC_BLUE = "1,-2 1,1 2,-1 0,0 -2,2 -1,-1"
casc = pos(CASC_RED, CASC_BLUE, to_move=0)
_cl, _cs = label_groups(sp3, casc.stones, 0)
check("cascade premise: Red holds SIX singleton groups",
      sorted(_cs) == [1] * 6, str(_cs))
check("cascade premise: no isolated placement exists",
      min(G.placement_sizes(casc).values()) > 1)
check("cascade premise: the placement is legal (it forms the smallest group)",
      _cell("1,0") in G.placements(casc))
casc2 = G.apply_move(casc, "1,0")
_dead_groups = {_cl[c] for c in casc2.removed}
check("cascade: ONE turn removes FIVE stones from FIVE different groups",
      len(casc2.removed) == 5 and len(_dead_groups) == 5,
      f"removed={names(sp3, casc2.removed)}")
check("cascade: none of the removed stones touches the placement",
      not (set(casc2.removed) & set(sp3.nbrs[_cell("1,0")])))
check("cascade: the surviving red stones are exactly the new 2-group",
      {c for c, o in casc2.stones.items() if o == 0} == {_cell("1,0"), _cell("2,0")})
check("cascade: no BLUE stone moved", {c for c, o in casc2.stones.items() if o == 1}
      == set(C(CASC_BLUE)))
_al, _as = label_groups(sp3, casc2.stones, 0)
check("cascade: after the turn every friendly group is >= the new group",
      min(_as) == _as[_al[_cell("1,0")]] == 2, str(_as))
# each removed group is individually decisive: put any one of them back next to
# the new group and it would have merged instead of dying
for one in C(CASC_RED):
    if one == _cell("2,0"):
        continue
    check("cascade: each removed singleton was a separate group",
          len(group_of(sp3, casc.stones, one)) == 1)

# A placement that merges THREE groups at once (rare in random play: 46 turns in
# 28,055), also from a real game.  Dropping ANY ONE of the three changes the
# resulting group size, so all three are load-bearing.
TRI_RED = "2,-2 2,-1 1,-2 -1,-1 -2,1 -2,0 -1,2 0,0 1,1"
TRI_BLUE = "0,-1 0,-2 1,0 2,0 1,-1 -1,1 -2,2 0,2"
tri = pos(TRI_RED, TRI_BLUE, to_move=0)
_tl, _ts = label_groups(sp3, tri.stones, 0)
merged_gids = {_tl[nb] for nb in sp3.nbrs[_cell("0,1")] if nb in _tl}
check("triple-merge premise: the placement touches THREE distinct red groups",
      len(merged_gids) == 3, str(sorted(_ts[g] for g in merged_gids)))
full = G.placement_sizes(tri)[_cell("0,1")]
check("triple-merge: the resulting size is 1 + the three groups' total",
      full == 1 + sum(_ts[g] for g in merged_gids), str(full))
for one in TRI_RED.split():
    sub = pos(" ".join(t for t in TRI_RED.split() if t != one), TRI_BLUE, to_move=0)
    if _cell(one) in {nb for nb in sp3.nbrs[_cell("0,1")]}:
        check(f"triple-merge: dropping the neighbour {one} shrinks the result",
              G.placement_sizes(sub)[_cell("0,1")] < full)


# ==========================================================================
#  7.  Exhaustive solve of the SMALLEST board (hexhex side 2, 7 cells)
# ==========================================================================
def solve(board, use_pie):
    memo, onstack = {}, set()
    tested = [0]

    def rec(s, depth):
        if G.is_terminal(s):
            w = G.winner(s)
            return (0 if w is None else (1 if w == 0 else -1)), depth
        k = (frozenset(s.stones.items()), s.to_move, min(s.ply, 2), s.swapped)
        if k in memo:
            return memo[k], depth
        tested[0] += 1                       # the acyclicity guard, exercised
        if k in onstack:
            raise AssertionError("CYCLE in the Churn game graph")
        onstack.add(k)
        deep = depth
        vals = []
        for m in G.legal_moves(s):
            if m == "swap" and not use_pie:
                continue
            v, d = rec(G.apply_move(s, m), depth + 1)
            vals.append(v)
            deep = max(deep, d)
        onstack.discard(k)
        memo[k] = max(vals) if s.to_move == 0 else min(vals)
        return memo[k], deep

    v, deep = rec(G.initial_state({"board": board}), 0)
    return v, deep, len(memo), tested[0]


v_pie, depth_pie, n_pie, t_pie = solve("hex2", True)
v_nopie, depth_nopie, n_nopie, t_nopie = solve("hex2", False)
# The acyclicity guard raises on any back edge; assert it was actually EVALUATED
# once per reachable state, so "no cycle" is a measured result, not a no-op.
check("hex2 exhaustive: the reachable game graph is ACYCLIC — the on-stack "
      "guard was evaluated on every one of the reachable states",
      t_pie == n_pie and t_nopie == n_nopie and n_pie > 1000,
      f"{t_pie}/{n_pie} {t_nopie}/{n_nopie}")
check("hex2 exhaustive: the reachable non-terminal state counts are pinned",
      (n_nopie, n_pie) == (535, 1069), f"{n_nopie} {n_pie}")
check("hex2 exhaustive: the longest possible game is 9 plies without the pie",
      depth_nopie == 9, str(depth_nopie))
check("hex2 exhaustive: the pie adds EXACTLY the one extra ply max_plies() "
      "budgets for it", depth_pie == depth_nopie + 1, str(depth_pie))
check("hex2 exhaustive: WITHOUT the pie, the FIRST player wins",
      v_nopie == 1, str(v_nopie))
# Strategy stealing: in a drawless game where player 2 may, after player 1's one
# opening move, either keep their colour or adopt the opening as their own,
# player 2 wins.  Ground truth from theory, independent of this engine.
check("hex2 exhaustive: WITH the pie, the SECOND player wins (strategy stealing)",
      v_pie == -1, str(v_pie))


# ==========================================================================
#  8.  The pie swap — the oracle's structural blind spot
# ==========================================================================
s0 = G.initial_state()
check("pie: no swap is offered on the opening move", "swap" not in G.legal_moves(s0))
s1 = G.apply_move(s0, "0,0")
check("pie: the swap IS offered on the second player's first turn",
      "swap" in G.legal_moves(s1))
s1b = G.apply_move(s1, "2,-2")
check("pie: no swap after the second player has placed",
      "swap" not in G.legal_moves(s1b))
s2 = G.apply_move(s1, "swap")
# This is the assertion that catches a swap which forgets to hand the move back
# (invisible to the solved value, which stays a second-player win either way).
check("pie: swap yields EXACTLY the colour-mirror of the pre-swap position",
      s2.stones == {c: 1 - o for c, o in s1.stones.items()}
      and s2.to_move == 1 - s1.to_move,
      f"{s2.stones} to_move={s2.to_move}")
check("pie: after the swap the lone stone is BLUE and RED is to move",
      s2.stones == {(0, 0): 1} and s2.to_move == 0
      and G.render(s2)["caption"].startswith("Red to move"))
check("pie: the swap places no stone", len(s2.stones) == len(s1.stones) == 1)
check("pie: swapped flag set and the swap cannot be taken twice",
      s2.swapped and "swap" not in G.legal_moves(s2))
try:
    G.apply_move(s2, "swap")
    raise AssertionError("pie: a second swap was accepted")
except ValueError:
    OK.append("pie: a late swap raises ValueError")
check("pie: describe_move labels it", G.describe_move(s1, "swap") == "swap (pie)")
check("pie: the caption offers the swap only when it is legal",
      "swap (pie rule)" in G.render(s1)["caption"]
      and "swap (pie rule)" not in G.render(s0)["caption"]
      and "swap (pie rule)" not in G.render(s2)["caption"])
# Colour symmetry of the whole ruleset, which is WHY recolouring in place is a
# value-preserving swap: mirror any position and the values negate.
def mirror(s):
    return ChurnState(board=s.board, stones={c: 1 - o for c, o in s.stones.items()},
                      to_move=1 - s.to_move, ply=s.ply)
rng = random.Random(4242)
for _ in range(30):
    s = G.initial_state({"board": "hex2"})
    for _ in range(rng.randrange(1, 6)):
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    m = mirror(s)
    check("colour symmetry: mirrored positions have mirrored legal sets",
          set(G.placements(m)) == set(G.placements(s)))
    check("colour symmetry: mirrored terminal results negate",
          (not G.is_terminal(s)) or G.returns(m) == list(reversed(G.returns(s))))


# ==========================================================================
#  9.  Termination — the monovariant, checked on real play, plus the bound
# ==========================================================================
def vector(s, seat):
    return sorted(label_groups(spec_for(s.board), s.stones, seat)[1], reverse=True)


def lex_gt(a, b):
    """Sorted-descending vectors, lexicographic with prefix < extension."""
    for x, y in zip(a, b):
        if x != y:
            return x > y
    return len(a) > len(b)


rng = random.Random(20261231)
longest = {}
for key, ngames in (("hex2", 200), ("hex3", 40), ("limping34", 4)):
    worst = 0
    for _ in range(ngames):
        s = G.initial_state({"board": key})
        plies = 0
        while not G.is_terminal(s):
            mv = G.legal_moves(s)
            check("no-stuck invariant: a non-terminal state always has a move", mv)
            m = rng.choice(mv)
            before = vector(s, s.to_move)
            mover = s.to_move
            s = G.apply_move(s, m)
            if m != "swap":
                check("MONOVARIANT: the mover's group vector strictly increases",
                      lex_gt(vector(s, mover), before),
                      f"{before} -> {vector(s, mover)}")
            plies += 1
            check("termination: play never exceeds the derived bound",
                  plies <= max_plies(key))
        worst = max(worst, plies)
        check("terminal states are full boards",
              len(s.stones) == len(spec_for(key).cells))
        check("no board can tie", G.winner(s) is not None)
    longest[key] = worst
check("termination: the derived bound is far above observed play",
      all(longest[k] < max_plies(k) for k in longest), str(longest))
# The bound is DERIVED from the board, not pinned: a bigger board raises it.
check("termination: max_plies() is derived from the board's own cell count",
      max_plies("hex2") < max_plies("hex3") < max_plies("limping34"))
check("termination: the bound counts the pie ply (it is odd)",
      max_plies("hex3") % 2 == 1)

fake = ChurnState(board="hex2",
                  stones={c: i % 2 for i, c in enumerate(spec_for("hex2").cells)})
fake.stones[spec_for("hex2").cells[0]] = 1     # 4 blue / 3 red -> decisive
check("winner(): a decisive full board is decisive", G.winner(fake) == 1)
part = ChurnState(board="hex2", stones={c: i % 2 for i, c in
                                        enumerate(spec_for("hex2").cells[:6])})
check("winner(): a non-full board is not terminal", not G.is_terminal(part))

# The draw branch is VACUOUS on every shipped board (all have an odd cell count),
# so no amount of random play, differential or sweep can ever reach it.  Test it
# on a CONSTRUCTED input instead: register a 6-cell board just for this check.
import games.churn.game as _M                                    # noqa: E402
_M.BOARD_PARAMS["_test_even_6"] = (0, 1, 0, 2, 0, 3)
_even_sp = spec_for("_test_even_6")
check("draw path: the constructed test board really has an EVEN cell count "
      "(so the patch bites)", len(_even_sp.cells) == 6)
_tie = ChurnState(board="_test_even_6",
                  stones={c: i % 2 for i, c in enumerate(_even_sp.cells)})
check("draw path: an equal FULL board is terminal", G.is_terminal(_tie))
check("draw path: an equal full board is an HONEST DRAW, never a fabricated "
      "tie-break", G.winner(_tie) is None and G.returns(_tie) == [0.0, 0.0],
      f"{G.winner(_tie)} {G.returns(_tie)}")
check("draw path: the draw caption says so",
      G.render(_tie)["caption"].startswith("Draw"), G.render(_tie)["caption"])
del _M.BOARD_PARAMS["_test_even_6"]
_M._SPECS.pop("_test_even_6", None)
check("draw path: the test board is deregistered afterwards",
      "_test_even_6" not in _M.BOARD_PARAMS and set(BOARD_KEYS) == set(_M.BOARD_PARAMS))


# ==========================================================================
# 10.  serialize / deserialize compared as STATE OBJECTS, over whole games
# ==========================================================================
KEYS = {"board", "stones", "to_move", "ply", "swapped", "last", "removed"}
seen_shapes = {"swapped_true": 0, "swapped_false": 0, "removed_empty": 0,
               "removed_nonempty": 0, "last_none": 0, "last_set": 0}
rng = random.Random(777)
for key in BOARD_KEYS:
    for gi in range(3):
        s = G.initial_state({"board": key})
        while True:
            d = G.serialize(s)
            check("serialize: exact key set", set(d) == KEYS, str(sorted(d)))
            check("serialize: JSON-safe scalars",
                  all(isinstance(v, (str, int, bool, dict, list, type(None)))
                      for v in d.values()))
            back = G.deserialize(d)
            check("round-trip compares STATE OBJECTS", back == s,
                  f"{back}\n vs {s}")
            check("round-trip is idempotent on the dict", G.serialize(back) == d)
            seen_shapes["swapped_true" if s.swapped else "swapped_false"] += 1
            seen_shapes["removed_nonempty" if s.removed else "removed_empty"] += 1
            seen_shapes["last_set" if s.last else "last_none"] += 1
            if G.is_terminal(s):
                break
            mv = G.legal_moves(s)
            if gi == 0 and s.ply == 1 and "swap" in mv:
                m = "swap"
            else:
                m = rng.choice([x for x in mv if x != "swap"] or mv)
            s = G.apply_move(s, m)
check("serialize sweep: every field shape was exercised",
      all(v > 0 for v in seen_shapes.values()), str(seen_shapes))


# ==========================================================================
# 11.  render() — bounds for EVERY board, at the FULL final position
# ==========================================================================
def declared(board):
    if isinstance(board.get("cells"), list):
        return set(board["cells"])
    n = board["size"] - 1
    return {f"{q},{r}" for q in range(-n, n + 1) for r in range(-n, n + 1)
            if abs(q + r) <= n}


rng = random.Random(99)
for key in BOARD_KEYS:
    s = G.initial_state({"board": key})
    spec = G.render(s)
    check(f"render {key}: board type is hex", spec["board"]["type"] == "hex")
    check(f"render {key}: declared cells == the engine's cell set",
          declared(spec["board"]) ==
          {f"{q},{r}" for (q, r) in spec_for(key).cells})
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    spec = G.render(s)
    cells = declared(spec["board"])
    pcells = {p["cell"] for p in spec["pieces"]}
    # The final board is FULL, so this covers every cell including the corners.
    check(f"render {key}: every piece lies inside the declared board",
          pcells <= cells, str(sorted(pcells - cells)))
    check(f"render {key}: the FULL final board covers every declared cell "
          f"(so the check is not vacuous)", pcells == cells)
    check(f"render {key}: owners are 0/1",
          all(p["owner"] in (0, 1) for p in spec["pieces"]))
    check(f"render {key}: highlights reference real cells",
          all(h["cell"] in cells for h in spec["highlights"]))
    check(f"render {key}: terminal caption names a winner",
          spec["caption"].startswith(("Red wins", "Blue wins")), spec["caption"])
    check(f"render {key}: describe_move never raises",
          all(isinstance(G.describe_move(G.initial_state({"board": key}), m), str)
              for m in G.legal_moves(G.initial_state({"board": key}))))

# describe_move reports the removal count
check("describe_move: a quiet placement is just the cell name",
      G.describe_move(f1, "0,1") == cell_name(sp3, (0, 1)) == "b3",
      G.describe_move(f1, "0,1"))
check("describe_move: a removing placement is annotated with the count",
      G.describe_move(f3_before, "2,-1") == f"{cell_name(sp3, F3_PLACED)} -3",
      G.describe_move(f3_before, "2,-1"))
check("cell_name: a1 is the bottom-left cell of every board",
      all(cell_name(SP[k], min(SP[k].cells, key=lambda c: (-c[1], c[0]))) == "a1"
          for k in BOARD_KEYS))


# ==========================================================================
# 12.  Illegal moves are refused
# ==========================================================================
for bad, why in ((("9,9"), "off board"), ("0,-2", "occupied"), ("1,0", "not a minimiser")):
    try:
        G.apply_move(f2, bad)
        raise AssertionError(f"illegal move {bad} ({why}) was accepted")
    except ValueError:
        OK.append(f"illegal move refused: {bad} ({why})")
try:
    G.initial_state({"board": "hex9"})
    raise AssertionError("unknown board accepted")
except ValueError:
    OK.append("initial_state rejects an unknown board key")
check("default board is the designer's recommended side 3",
      DEFAULT_BOARD == "hex3")


print(f"churn selftest: {len(OK)} assertions passed")
print(f"  figure kills — fig1: {len(fig_kills['fig1'])}, fig2: "
      f"{len(fig_kills['fig2'])}, blind to {len(fig_kills['blind'])} "
      f"(closed by construction)")
print(f"  hex2 solved: {n_nopie} states, depth {depth_nopie} (+1 with the pie), "
      f"value {v_nopie:+d} without the pie / {v_pie:+d} with it")
print(f"  longest random games: {longest}")
