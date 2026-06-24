"""Standalone correctness anchor for Starweb.

Run from the engine dir:  PYTHONPATH=. python3 games/starweb/selftest.py

There is no published perft for Starweb; the anchor is a set of baked rule
asserts derived from the official rules and the official board diagram:

  (1) GEOMETRY — exactly 217 cells; a hexhex-7 (127) base subset; six-fold
      rotational symmetry; the hand-built EXACT set of 18 star cells (12 outward
      + 6 inward), independently both via the neighbour-count rule and against a
      literal coordinate list read off the official diagram;
  (2) PLACEMENT — a stone goes on any empty cell; pass and (turn-1) swap exist;
  (3) GROUPS — connected like-coloured components;
  (4) SCORING — the EXACT triangular formula: a single group touching k stars
      scores k*(k+1)/2 for k = 0..5 (0,1,3,6,10,15); two separate groups add;
  (5) END + WINNER — two successive passes end the game; most points wins; an
      equal score goes to the SECOND player (WHITE). Reached via apply_move
      (since the winner is set only inside apply_move / "win as event");
  (6) the documented opening move count (217 placements, plus pass);
  plus engine conformance and a serialize round-trip.

Pure stdlib: imports only `agp` + this game. Fast.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import os
import sys

from games.starweb.game import (
    Starweb, StarwebState, BLACK, WHITE,
    _cells, _cell_set, _stars, _groups, _score, _DIRS,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


# The 18 star cells, read directly off the official Starweb board diagram
# (reconstructed and verified cell-for-cell). 12 outward (convex bump tips) +
# 6 inward (concave notches between bumps).
EXPECTED_STARS = {
    # outward (12)
    (-9, 3), (-9, 6), (-6, -3), (-6, 9), (-3, -6), (-3, 9),
    (3, -9), (3, 6), (6, -9), (6, 3), (9, -6), (9, -3),
    # inward (6)
    (-6, 0), (-6, 6), (0, -6), (0, 6), (6, -6), (6, 0),
}


def main():
    g = Starweb()

    # ---- conformance ------------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check_conformance(g, manifest, games=4, seed=1)
    if not rep.ok:
        fails = [m for ok, m in rep.checks if not ok]
        fail(f"conformance failed: {fails}")

    # ---- (1) geometry -----------------------------------------------------
    cells = set(_cells())
    if len(cells) != 217:
        fail(f"expected 217 cells, got {len(cells)}")

    # hexhex-7 base is a subset
    base = {(q, r) for q in range(-6, 7) for r in range(-6, 7)
            if max(abs(q), abs(r), abs(-q - r)) <= 6}
    if len(base) != 127:
        fail(f"hexhex-7 base should be 127, got {len(base)}")
    if not base <= cells:
        fail("hexhex-7 base is not a subset of the board")
    if len(cells - base) != 90:
        fail(f"expected 90 added cells (6 chunks of 15), got {len(cells - base)}")

    # six-fold rotational symmetry of the board
    def rot(q, r):
        return (-r, q + r)
    rotated = {rot(q, r) for (q, r) in cells}
    if rotated != cells:
        fail("board is not invariant under 60-degree rotation")

    # stars: via neighbour-count rule AND against the literal expected list
    stars = set(_stars())
    if stars != EXPECTED_STARS:
        fail(f"star set mismatch:\n  extra={sorted(stars - EXPECTED_STARS)}\n"
             f"  missing={sorted(EXPECTED_STARS - stars)}")
    if len(stars) != 18:
        fail(f"expected 18 stars, got {len(stars)}")
    outward = [c for c in stars
               if sum(1 for dq, dr in _DIRS if (c[0] + dq, c[1] + dr) in cells) == 3]
    inward = [c for c in stars
              if sum(1 for dq, dr in _DIRS if (c[0] + dq, c[1] + dr) in cells) == 5]
    if len(outward) != 12 or len(inward) != 6:
        fail(f"expected 12 outward + 6 inward, got {len(outward)} + {len(inward)}")
    # stars are six-fold symmetric too
    if {rot(q, r) for (q, r) in stars} != stars:
        fail("star set is not 60-degree rotation invariant")

    # ---- (2) placement / legal moves --------------------------------------
    s0 = g.initial_state()
    lm = g.legal_moves(s0)
    placements = [m for m in lm if m not in ("swap", "pass")]
    if len(placements) != 217:
        fail(f"opening should offer 217 placements, got {len(placements)}")
    if "pass" not in lm:
        fail("pass must be legal")
    if "swap" in lm:
        fail("swap must NOT be offered on the very first move (ply 0)")

    # first stone, then the second player is offered swap
    s1 = g.apply_move(s0, "0,0")
    if s1.board.get((0, 0)) != BLACK or s1.to_move != WHITE:
        fail("first placement bookkeeping wrong")
    if "swap" not in g.legal_moves(s1):
        fail("swap must be offered to the second player on their first turn")
    # a placement removes that cell from future legal moves
    if "0,0" in g.legal_moves(s1):
        fail("an occupied cell is still offered")

    # swap: White adopts the stone, board still one stone, Black to move
    sw = g.apply_move(s1, "swap")
    if sw.board != {(0, 0): WHITE} or sw.to_move != BLACK:
        fail(f"swap did not adopt the stone correctly: {sw.board}, to_move={sw.to_move}")

    # ---- (3) groups -------------------------------------------------------
    # two adjacent black stones form one group; a separated one is its own group
    board = {(0, 0): BLACK, (1, 0): BLACK, (5, 0): BLACK}
    gps = _groups(board, BLACK)
    sizes = sorted(len(x) for x in gps)
    if sizes != [1, 2]:
        fail(f"group detection wrong: sizes {sizes}")

    # ---- (4) EXACT triangular scoring -------------------------------------
    star_list = sorted(EXPECTED_STARS)
    expected_sigma = {0: 0, 1: 1, 2: 3, 3: 6, 4: 10, 5: 15}
    for k in range(0, 6):
        # build one connected group that contains exactly k stars.
        grp = _connected_group_with_stars(cells, set(star_list), k)
        board = {c: BLACK for c in grp}
        got = _score(board, BLACK)
        if got != expected_sigma[k]:
            fail(f"k={k} stars: expected Sigma={expected_sigma[k]}, got {got}")

    # two SEPARATE black groups: one with 2 stars (->3), one with 1 star (->1) = 4
    g2 = _connected_group_with_stars(cells, set(star_list), 2)
    # find a single star far from g2 to make an isolated 1-star group
    far = None
    for st in star_list:
        if all(_dist(st, c) > 2 for c in g2):
            far = st
            break
    if far is None:
        fail("could not isolate a far star for the two-group test")
    board = {c: BLACK for c in g2}
    board[far] = BLACK
    if _score(board, BLACK) != 3 + 1:
        fail(f"two-group score wrong: {_score(board, BLACK)} != 4")

    # a 0-star group scores 0 even if large
    nonstar = [c for c in cells if c not in EXPECTED_STARS][:5]
    # make them connected by walking a path; just assert any non-star-only board
    board = {c: WHITE for c in _connected_group_with_stars(cells, set(star_list), 0)}
    if _score(board, WHITE) != 0:
        fail("a group with no stars must score 0")

    # ---- (5) end + winner (reached via apply_move) ------------------------
    # Build a position where Black holds 1 star and White holds 2 stars, then end
    # by two successive passes; White (more points) must win.
    one = _connected_group_with_stars(cells, set(star_list), 1)
    # pick a DIFFERENT 2-star group disjoint from `one`
    two = _two_star_group_disjoint(cells, set(star_list), one)
    s = StarwebState(board={**{c: BLACK for c in one}, **{c: WHITE for c in two}},
                     to_move=BLACK, ply=10)
    s = g.apply_move(s, "pass")
    s = g.apply_move(s, "pass")
    if not g.is_terminal(s):
        fail("two successive passes must end the game")
    if _score(s.board, BLACK) != 1 or _score(s.board, WHITE) != 3:
        fail(f"score setup wrong: B={_score(s.board, BLACK)} W={_score(s.board, WHITE)}")
    if s.winner != WHITE:
        fail(f"White (3) should beat Black (1), winner={s.winner}")
    if g.returns(s) != [-1.0, 1.0]:
        fail(f"returns wrong for White win: {g.returns(s)}")

    # TIE -> second player (WHITE) wins. Give each side one separate 1-star group.
    oneB = _connected_group_with_stars(cells, set(star_list), 1)
    oneW = _one_star_group_disjoint(cells, set(star_list), oneB)
    s = StarwebState(board={**{c: BLACK for c in oneB}, **{c: WHITE for c in oneW}},
                     to_move=BLACK, ply=10)
    s = g.apply_move(s, "pass")
    s = g.apply_move(s, "pass")
    if _score(s.board, BLACK) != 1 or _score(s.board, WHITE) != 1:
        fail("tie setup wrong")
    if s.winner != WHITE:
        fail(f"a tie must go to the second player WHITE, got {s.winner}")

    # ---- (6) serialize round-trip -----------------------------------------
    st = g.apply_move(g.apply_move(g.initial_state(), "0,0"), "6,3")
    rt = g.deserialize(json.loads(json.dumps(g.serialize(st))))
    if rt.board != st.board or rt.to_move != st.to_move or rt.ply != st.ply:
        fail("serialize round-trip mismatch")

    print("SELFTEST OK")


# ---- helpers --------------------------------------------------------------

def _dist(a, b):
    aq, ar = a
    bq, br = b
    return (abs(aq - bq) + abs(ar - br) + abs((-aq - ar) - (-bq - br))) // 2


def _connected_group_with_stars(cells: set, stars: set, k: int) -> set:
    """Return a CONNECTED set of cells containing exactly k stars (k=0..5).

    Build by BFS from a seed, adding cells greedily while controlling how many
    stars get included.
    """
    from collections import deque
    cells = set(cells)
    nbrs = lambda c: [(c[0] + dq, c[1] + dr) for dq, dr in _DIRS
                      if (c[0] + dq, c[1] + dr) in cells]
    if k == 0:
        # grow a blob of non-star cells
        seed = next(c for c in sorted(cells) if c not in stars)
        comp = {seed}
        frontier = deque([seed])
        while frontier and len(comp) < 4:
            c = frontier.popleft()
            for n in nbrs(c):
                if n not in comp and n not in stars:
                    comp.add(n)
                    frontier.append(n)
        return comp
    # connect k stars by shortest paths through the board (paths may add non-stars
    # but that does not change the star count; we must avoid passing through OTHER
    # stars, which the path-finder below ensures for k>=2 by routing star-to-star
    # on a chosen ordered chain).
    chosen = sorted(stars)[:k]
    comp = set(chosen[:1])
    for nxt in chosen[1:]:
        path = _path(cells, stars, set(comp), nxt)
        comp |= set(path)
    return comp


def _path(cells, stars, comp, target):
    """Shortest path (BFS) from any cell in `comp` to `target`, not passing
    through any star except `target` itself."""
    from collections import deque
    nbrs = lambda c: [(c[0] + dq, c[1] + dr) for dq, dr in _DIRS
                      if (c[0] + dq, c[1] + dr) in cells]
    start = next(iter(comp))
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        if c == target:
            break
        for n in nbrs(c):
            if n in prev:
                continue
            # don't route through a star other than the target
            if n in stars and n != target:
                continue
            prev[n] = c
            q.append(n)
    if target not in prev:
        raise RuntimeError("no star-avoiding path found")
    out = []
    c = target
    while c is not None:
        out.append(c)
        c = prev[c]
    return out


def _two_star_group_disjoint(cells, stars, avoid: set) -> set:
    """A connected 2-star group disjoint from `avoid`."""
    avail = set(stars) - _expand(cells, avoid)
    pair = sorted(avail)[:2]
    comp = {pair[0]}
    comp |= set(_path(cells - avoid, stars, comp, pair[1]))
    return comp


def _one_star_group_disjoint(cells, stars, avoid: set) -> set:
    avail = sorted(set(stars) - _expand(cells, avoid))
    return {avail[0]}


def _expand(cells, comp):
    """`comp` plus its immediate neighbours (so a 'disjoint' group is truly
    non-adjacent, hence a separate connected component)."""
    out = set(comp)
    for c in comp:
        for dq, dr in _DIRS:
            n = (c[0] + dq, c[1] + dr)
            if n in cells:
                out.add(n)
    return out


if __name__ == "__main__":
    main()
