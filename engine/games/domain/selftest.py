#!/usr/bin/env python3
"""Standalone correctness anchor for Domain. Pure stdlib + agp only.

Run:  PYTHONPATH=. python3 games/domain/selftest.py

PRIMARY ANCHOR — the opening-move count. Larry Back (Abstract Games #12) states:
"I counted a total of 171 distinct opening moves in Domain ... and 1,149 opening
moves if you [count every placement separately]." On the empty 9x9 board this
implementation must generate exactly **1,149** placements, which reduce to
**171** orbits under the board's 8-fold dihedral symmetry. Hitting both numbers
validates the entire 26-tile shape set (shapes AND that reflections coincide
with rotations) end-to-end.

Also anchored: the flip rule (orthogonal touch flips, diagonal does not; the
intermediate vs advanced difference), the touch restriction, full-game
termination with score = covered squares, an honest DRAW on an equal cover, and
serialize round-trip.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                    # noqa: E402
from games.domain.game import (                                         # noqa: E402
    DState, PIECES, START_COUNTS, MOVE_MASK, _bit, W, H,
)

MAN, G = load_from_dir(Path(__file__).resolve().parent)

FAILED = []


def check(name, cond):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}")
        FAILED.append(name)


def mask(*cells):
    m = 0
    for c, r in cells:
        m |= _bit(c, r)
    return m


def owners(s):
    """Map cell -> owner for every covered cell."""
    out = {}
    for owner, m in s.tiles:
        for i in range(W * H):
            if m >> i & 1:
                out[(i % W, i // W)] = owner
    return out


# ---------------------------------------------------------------------------
# 1. PRIMARY ANCHOR: opening-move count 1,149 raw / 171 up to symmetry
# ---------------------------------------------------------------------------
s0 = G.initial_state({"variant": "intermediate"})
opening = G.legal_moves(s0)
check("opening placements == 1149 (raw)", len(opening) == 1149)
check("opening moves all distinct", len(set(opening)) == 1149)

# Each move string maps to a unique covered-cell set.
def cells_of_mask(m):
    return frozenset((i % W, i // W) for i in range(W * H) if m >> i & 1)


cellsets = {cells_of_mask(MOVE_MASK[mv]) for mv in opening}
check("opening covers 1149 distinct cell sets", len(cellsets) == 1149)


def dihedral(cs):
    """The 8 images of a cell set under the 9x9 board's symmetry group."""
    out = []
    for fx in (False, True):
        pts = [((W - 1 - c) if fx else c, r) for c, r in cs]
        for _ in range(4):
            pts = [(r, (H - 1 - c)) for c, r in pts]      # rotate 90 degrees
            out.append(frozenset(pts))
    return out


seen, orbits = set(), 0
for cs in cellsets:
    if cs in seen:
        continue
    orbits += 1
    seen.update(dihedral(cs))
check("opening reduces to 171 symmetry orbits", orbits == 171)

# The basic variant (touch-exempt too) has the same empty-board opening set.
check("basic opening also 1149",
      len(G.legal_moves(G.initial_state({"variant": "basic"}))) == 1149)


# ---------------------------------------------------------------------------
# 2. Flip rule — orthogonal touch flips, diagonal does not (basic: touch-exempt)
# ---------------------------------------------------------------------------
A = mask((3, 3), (4, 3))                    # Blue Short Bar
base = DState(tiles=((0, A),), hands=(START_COUNTS, START_COUNTS),
              to_move=1, variant="basic")

# White places a Short Bar directly ABOVE A (orthogonal touch) -> A flips White.
ortho = G.apply_move(base, "S2:0@3,4")      # covers (3,4),(4,4)
ow = owners(ortho)
check("orthogonal touch flips opponent tile", ow[(3, 3)] == 1 and ow[(4, 3)] == 1)
check("flip: placer's own new tile stays placer's", ow[(3, 4)] == 1)
check("flip: Blue cover now 0", G.score(ortho, 0) == 0)

# White places a Short Bar so it touches A only DIAGONALLY -> A does NOT flip.
diag = G.apply_move(base, "S2:0@5,4")       # covers (5,4),(6,4); (5,4) is diag to (4,3)
dw = owners(diag)
check("diagonal-only touch does NOT flip", dw[(3, 3)] == 0 and dw[(4, 3)] == 0)


# ---------------------------------------------------------------------------
# 3. Intermediate vs advanced flip semantics on the same position
# ---------------------------------------------------------------------------
#   Blue A below, White B above, a gap row between; Blue plays C into the gap
#   touching BOTH. Intermediate: only B (opponent) flips. Advanced: A and B both
#   flip to the opposite colour.
Amask = mask((2, 3), (3, 3))                # Blue
Bmask = mask((2, 5), (3, 5))               # White
setup = dict(tiles=((0, Amask), (1, Bmask)),
             hands=(START_COUNTS, START_COUNTS), to_move=0)

inter = G.apply_move(DState(variant="intermediate", **setup), "S2:1@2,4")
iw = owners(inter)
check("intermediate: opponent tile flips to placer",
      iw[(2, 5)] == 0 and iw[(3, 5)] == 0)
check("intermediate: placer's own touched tile does NOT flip",
      iw[(2, 3)] == 0 and iw[(3, 3)] == 0)

adv = G.apply_move(DState(variant="advanced", **setup), "S2:1@2,4")
aw = owners(adv)
check("advanced: opponent touched tile flips to placer",
      aw[(2, 5)] == 0 and aw[(3, 5)] == 0)
check("advanced: placer's OWN touched tile flips away",
      aw[(2, 3)] == 1 and aw[(3, 3)] == 1)
check("advanced: placed tile itself keeps placer colour",
      aw[(2, 4)] == 0 and aw[(3, 4)] == 0)


# ---------------------------------------------------------------------------
# 4. Touch restriction (intermediate) — every non-opening move touches an enemy
# ---------------------------------------------------------------------------
tr = DState(tiles=((0, A),), hands=(START_COUNTS, START_COUNTS),
            to_move=1, variant="intermediate")
tmoves = G.legal_moves(tr)
from games.domain.game import _edge_zone                                # noqa: E402
opp = A
check("all intermediate moves touch an opponent tile",
      all(_edge_zone(MOVE_MASK[m]) & opp for m in tmoves))
# A far-away placement is illegal here, but legal under basic (no touch rule).
far = "S2:0@0,0"
check("far placement illegal under touch rule", far not in tmoves)
tr_basic = DState(tiles=((0, A),), hands=(START_COUNTS, START_COUNTS),
                  to_move=1, variant="basic")
check("same far placement legal under basic", far in G.legal_moves(tr_basic))


# ---------------------------------------------------------------------------
# 5. Basic variant shares one pool (both hands decremented together)
# ---------------------------------------------------------------------------
b0 = G.initial_state({"variant": "basic"})
b1 = G.apply_move(b0, "S2:0@3,3")
check("basic: both hands stay identical (shared pool)", b1.hands[0] == b1.hands[1])
check("basic: shared pool decremented for the placed tile",
      b1.hands[0][PIECES.index("S2")] == START_COUNTS[PIECES.index("S2")] - 1)
rend_b = G.render(b1)
check("basic renders a shared palette", "shared" in rend_b["palette"])
rend_i = G.render(G.initial_state({"variant": "intermediate"}))
check("intermediate renders per-seat palettes",
      "0" in rend_i["palette"] and "1" in rend_i["palette"])


# ---------------------------------------------------------------------------
# 6. Full game runs to a real terminal; score == covered squares
# ---------------------------------------------------------------------------
def play_out(variant):
    s = G.initial_state({"variant": variant})
    for _ in range(400):
        if G.is_terminal(s):
            return s
        mv = G.legal_moves(s)
        assert mv, "non-terminal state with no legal moves"
        s = G.apply_move(s, mv[0])
    raise AssertionError("game did not terminate")


for v in ("basic", "intermediate", "advanced"):
    term = play_out(v)
    check(f"[{v}] reaches a terminal state", G.is_terminal(term))
    check(f"[{v}] terminal legal_moves is empty", G.legal_moves(term) == [])
    covered = len(owners(term))
    check(f"[{v}] score sums to covered squares",
          G.score(term, 0) + G.score(term, 1) == covered)
    r = G.returns(term)
    a, b = G.score(term, 0), G.score(term, 1)
    expect = [1.0, -1.0] if a > b else ([-1.0, 1.0] if b > a else [0.0, 0.0])
    check(f"[{v}] returns match the score comparison", r == expect)


# ---------------------------------------------------------------------------
# 7. Honest DRAW on an equal cover; decisive result otherwise
# ---------------------------------------------------------------------------
# Both hands exhausted -> no legal move -> terminal; equal cover -> draw.
tie = DState(tiles=((0, mask((0, 0), (1, 0))), (1, mask((0, 8), (1, 8)))),
             hands=((0,) * len(PIECES), (0,) * len(PIECES)),
             to_move=0, variant="intermediate")
check("equal-cover terminal is terminal", G.is_terminal(tie))
check("equal cover -> honest DRAW [0,0]", G.returns(tie) == [0.0, 0.0])
check("draw scores are equal", G.score(tie, 0) == G.score(tie, 1) == 2)

win = DState(tiles=((0, mask((0, 0), (1, 0), (2, 0))), (1, mask((0, 8), (1, 8)))),
             hands=((0,) * len(PIECES), (0,) * len(PIECES)),
             to_move=0, variant="intermediate")
check("unequal-cover terminal is decisive", G.returns(win) == [1.0, -1.0])


# ---------------------------------------------------------------------------
# 8. Serialize round-trip
# ---------------------------------------------------------------------------
mid = G.apply_move(G.apply_move(G.initial_state({"variant": "advanced"}),
                                "T5:0@3,3"), G.legal_moves(
    G.apply_move(G.initial_state({"variant": "advanced"}), "T5:0@3,3"))[0])
rt = G.deserialize(G.serialize(mid))
check("serialize round-trip: tiles", set(rt.tiles) == set(mid.tiles))
check("serialize round-trip: hands", rt.hands == mid.hands)
check("serialize round-trip: to_move/variant",
      rt.to_move == mid.to_move and rt.variant == mid.variant)
check("serialize round-trip: last", set(rt.last) == set(mid.last))


# ---------------------------------------------------------------------------
print()
if FAILED:
    print(f"FAILED ({len(FAILED)}): " + ", ".join(FAILED))
    sys.exit(1)
print("all Domain selftests passed")
