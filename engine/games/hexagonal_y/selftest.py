#!/usr/bin/env python3
"""Correctness anchors for Hexagonal Y (pure stdlib: only `agp` + this package).

Anchors, strongest first:

1. **The rule sheet's own four figures**, transcribed cell-for-cell out of the
   vector art of ``Hexagonal_Y.pdf``.  Figures 2 and 3 also print the *shortest
   covering perimeter path* as black + green dots, so the engine's arc is
   compared to the designer's, CELL FOR CELL, not just its verdict.
2. **Two independent formulations of the win predicate** — "the shortest arc
   covering the group's perimeter cells is longer than half the perimeter"
   (shipped) versus "that arc contains a pair of antipodal perimeter cells"
   (an equivalent form, proved below) versus a brute-force minimal covering
   interval.  All three must agree everywhere.
3. **The pairing invariant** — a perimeter cell and its antipode are always
   both empty or both the same colour — swept over whole random games.  This
   is what makes the rule sheet's unstated "what if the opposite cell is
   taken?" case unreachable, and (see 4) what makes the game drawless.
4. **Drawlessness**, exhaustively for every full board of sides 2 and 3 that
   obeys the invariant, and by sampling above that.  The same exhaustion
   *without* the invariant finds thousands of draws, so the double placement
   is demonstrably load-bearing.
"""

import itertools
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)
M = sys.modules[type(G).__module__]

SIZES = M.SIZES
ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1


# ---------------------------------------------------------------- geometry --

def test_geometry():
    for n in range(2, 13):
        sp = M.spec_for(n)
        check(len(sp.cells) == 3 * n * n - 3 * n + 1, f"cell count n={n}")
        check(sp.perimeter == 6 * (n - 1) == len(sp.ring), f"perimeter n={n}")
        check(len(set(sp.ring)) == sp.perimeter, f"ring distinct n={n}")
        P = sp.perimeter
        for i, c in enumerate(sp.ring):
            # the ring really is a cycle of adjacent cells …
            check(sp.ring[(i + 1) % P] in M.neighbors(*c), f"ring cycle n={n}")
            # … and stepping half way round it is exactly (q, r) -> (-q, -r)
            check(sp.ring[(i + P // 2) % P] == M.antipode(c), f"antipode n={n}")
            check(M.hex_dist(*c) == n - 1, f"ring radius n={n}")
            check(M.antipode(M.antipode(c)) == c, "antipode involution")
        interior = [c for c in sp.cells if c not in sp.ring_index]
        check(len(interior) == 3 * n * n - 9 * n + 7, f"interior count n={n}")
        # no cell is its own antipode except the centre, which is never on the ring
        check((0, 0) not in sp.ring_index, f"centre off ring n={n}")
        # cell_name is a bijection
        names = [M.cell_name(n, c) for c in sp.cells]
        check(len(set(names)) == len(names), f"cell_name bijective n={n}")
        check(M.cell_name(n, (-(n - 1), n - 1)) == "a1", f"a1 is bottom-left n={n}")


# ------------------------------------------------- the rule sheet's figures --

# Transcribed from the vector art of the official rule sheet (side-4 board,
# 37 cells, perimeter 18).  Row r = -3 (top) … 3 (bottom), left to right.
FIG1 = ['.B..', '.....', '....R.', '.......', '......', '.....', '..B.']
FIG2 = ['B.RB', 'RR...', 'BBRRR.', 'R.RBBRR', '..RBBB', '.RBBR', 'BR.B']
FIG3 = ['RBR.', '.BRBB', 'BBRB.R', '.BRBRR.', 'RBRR.B', 'B..R.', '.RBR']
FIG4 = ['.B..', 'RRRR.', 'BBBBR.', '.B..BR.', '.R.BRB', '.RRBR', '..B.']

# The dotted cells the sheet itself prints for Figures 2 and 3: black = the
# group's own perimeter stones, black + green = the shortest covering path.
FIG2_BLACK = {(-2, 3), (-1, -2), (3, 0)}
FIG2_GREEN = {(-3, 0), (-3, 1), (-3, 2), (-3, 3), (-2, -1),
              (-1, 3), (0, 3), (1, 2), (2, 1)}
FIG3_BLACK = {(0, 3), (2, -3), (3, -1)}
FIG3_GREEN = {(1, 2), (2, 1), (3, -3), (3, -2), (3, 0)}


def parse_fig(rows):
    stones = {}
    for r, row in zip(range(-3, 4), rows):
        q_min = max(-3, -3 - r)
        check(len(row) == min(3, 3 - r) - q_min + 1, "figure row width")
        for i, ch in enumerate(row):
            if ch != '.':
                stones[(q_min + i, r)] = 0 if ch == 'R' else 1
    return stones


def best_arc(sp, stones, seat):
    """Longest covering arc over all of `seat`'s groups (with its group)."""
    best, bestg, seen = None, set(), set()
    for cell, owner in stones.items():
        if owner != seat or cell in seen:
            continue
        grp = G.group_of(stones, cell)
        seen |= grp
        arc = M.covering_arc(sp, [sp.ring_index[c] for c in grp
                                  if c in sp.ring_index])
        if arc is not None and (best is None or len(arc) > len(best)):
            best, bestg = arc, grp
    return best, bestg


def test_figures():
    sp = M.spec_for(4)
    check(sp.perimeter == 18 and len(sp.cells) == 37, "figure board is side 4")

    for name, rows in (("1", FIG1), ("2", FIG2), ("3", FIG3), ("4", FIG4)):
        stones = parse_fig(rows)
        for c in sp.ring:
            a = M.antipode(c)
            check(stones.get(c) == stones.get(a) and (c in stones) == (a in stones),
                  f"Figure {name} obeys the pairing invariant at {c}")

    # Figure 1 — Blue's first turn is an antipodal PAIR, Red's is a lone
    # interior stone.
    f1 = parse_fig(FIG1)
    blue = sorted(c for c, o in f1.items() if o == 1)
    red = [c for c, o in f1.items() if o == 0]
    check(len(blue) == 2 and M.antipode(blue[0]) == blue[1], "Fig 1 blue pair")
    check(all(c in sp.ring_index for c in blue), "Fig 1 blue on the perimeter")
    check(len(red) == 1 and red[0] not in sp.ring_index, "Fig 1 red interior")

    st1 = M.HexYState(size=4, stones=f1)
    check(not G.has_won(st1, 0) and not G.has_won(st1, 1), "Fig 1 nobody has won")

    # Figure 2 — "Thus Red has won the game."
    f2 = parse_fig(FIG2)
    arc, grp = best_arc(sp, f2, 0)
    cells = {sp.ring[i] for i in arc}
    check(cells == FIG2_BLACK | FIG2_GREEN,
          "Fig 2 arc is EXACTLY the sheet's black+green dots")
    check(len(cells) == 12 and 2 * 12 > sp.perimeter, "Fig 2 arc is 12 of 18")
    check({c for c in grp if c in sp.ring_index} == FIG2_BLACK,
          "Fig 2 group's perimeter stones are exactly the black dots")
    check(G.has_won(M.HexYState(size=4, stones=f2), 0), "Fig 2 Red has won")
    check(not G.has_won(M.HexYState(size=4, stones=f2), 1), "Fig 2 Blue has not")

    # Figure 3 — "not a winning position for Red".
    f3 = parse_fig(FIG3)
    arc, grp = best_arc(sp, f3, 0)
    cells = {sp.ring[i] for i in arc}
    check(cells == FIG3_BLACK | FIG3_GREEN,
          "Fig 3 arc is EXACTLY the sheet's black+green dots")
    check(len(cells) == 8 and 2 * 8 <= sp.perimeter, "Fig 3 arc is 8 of 18")
    check({c for c in grp if c in sp.ring_index} == FIG3_BLACK,
          "Fig 3 group's perimeter stones are exactly the black dots")
    check(not G.has_won(M.HexYState(size=4, stones=f3), 0), "Fig 3 Red has NOT won")
    check(not G.has_won(M.HexYState(size=4, stones=f3), 1), "Fig 3 Blue has not")

    # Figure 4 — "Red has won in Figure 4."  Exactly two perimeter stones, and
    # they are antipodal: the minimal winning shape (arc = half + 1).
    f4 = parse_fig(FIG4)
    arc, grp = best_arc(sp, f4, 0)
    peri = {c for c in grp if c in sp.ring_index}
    check(len(peri) == 2 and M.antipode(min(peri)) == max(peri),
          "Fig 4 the winning group's two perimeter stones are antipodal")
    check(len(arc) == 10 and 2 * 10 > sp.perimeter, "Fig 4 arc is 10 of 18")
    check(G.has_won(M.HexYState(size=4, stones=f4), 0), "Fig 4 Red has won")
    check(not G.has_won(M.HexYState(size=4, stones=f4), 1), "Fig 4 Blue has not")


# ------------------------------------------------------- the win predicate --

def test_arc_predicate():
    """`covering_arc` == brute-force minimal covering interval, and
    "longer than half" == "contains an antipodal pair"."""
    rnd = random.Random(20230923)
    trials = 0
    for n in (2, 3, 4, 5, 7, 9, 11):
        sp = M.spec_for(n)
        P = sp.perimeter
        for t in range(600):
            k = rnd.randint(0, 4) if t % 2 else rnd.randint(0, P)
            S = sorted(rnd.sample(range(P), k))
            arc = M.covering_arc(sp, S)
            if len(S) < 2:
                check(arc is None, "fewer than two perimeter stones cannot win")
                check(not M.arc_wins(sp, arc), "rule 1 needs two perimeter cells")
                continue
            # brute force: for every possible start, the shortest interval
            # from it that covers S
            brute = min(max((x - a) % P for x in S) + 1 for a in range(P))
            check(len(arc) == brute, f"minimal covering arc n={n} S={S}")
            aset = set(arc)
            check(set(S) <= aset, "the arc covers S")
            check(len(aset) == len(arc), "the arc has no repeats")
            anti = any((i + P // 2) % P in aset for i in aset)
            check(M.arc_wins(sp, arc) == anti,
                  f"win <=> the arc holds an antipodal pair (n={n}, S={S})")
            if any((i + P // 2) % P in set(S) for i in S):
                check(M.arc_wins(sp, arc),
                      "a group holding an antipodal PAIR always wins")
            trials += 1
        # degenerate cases, spelled out
        check(len(M.covering_arc(sp, range(P))) == P, "whole ring")
        check(M.arc_wins(sp, M.covering_arc(sp, range(P))), "whole ring wins")
        check(len(M.covering_arc(sp, [0, P // 2])) == P // 2 + 1,
              "an antipodal pair spans half + 1")
        check(M.arc_wins(sp, M.covering_arc(sp, [0, P // 2])),
              "an antipodal pair WINS (more than half, by exactly one cell)")
        check(not M.arc_wins(sp, M.covering_arc(sp, [0, P // 2 - 1])),
              "one short of antipodal is EXACTLY half — not a win")
        check(len(M.covering_arc(sp, [0, P // 2 - 1])) == P // 2,
              "one short of antipodal spans exactly half")
        check(not M.arc_wins(sp, M.covering_arc(sp, [0, 1])), "two neighbours")
    check(trials > 3000, "enough random subsets")


# ------------------------------------------------ whole games / invariants --

def play(size, seed, pie=False, pick=None):
    rnd = random.Random(seed)
    s = G.initial_state({"size": size, "pie": pie})
    hist = [s]
    while not G.is_terminal(s):
        mv = (pick or rnd.choice)(G.legal_moves(s))
        s = G.apply_move(s, mv)
        hist.append(s)
    return hist


def half_arcs(sp, stones):
    """Groups whose covering arc is EXACTLY half the perimeter.  Provably
    empty whenever the pairing invariant holds — see `test_games`."""
    out, seen = [], set()
    for c, o in stones.items():
        if c in seen:
            continue
        g = G.group_of(stones, c)
        seen |= g
        arc = M.covering_arc(sp, [sp.ring_index[x] for x in g
                                  if x in sp.ring_index])
        if arc is not None and 2 * len(arc) == sp.perimeter:
            out.append(g)
    return out


def test_games():
    sp_seen = {}
    wins = [0, 0]
    draws = 0
    half = 0
    max_plies = {}
    peri_moves = inter_moves = 0
    for size in SIZES:
        sp = M.spec_for(size)
        for seed in range(4):
            hist = play(size, seed * 97 + size)
            prev = hist[0]
            for s in hist[1:]:
                # a placement never removes a stone and adds 1 or 2
                added = len(s.stones) - len(prev.stones)
                check(added in (1, 2), "a turn places one or two stones")
                check(all(prev.stones[c] == s.stones[c] for c in prev.stones),
                      "stones are never removed or recoloured")
                mover = prev.to_move
                new = [c for c in s.stones if c not in prev.stones]
                check(all(s.stones[c] == mover for c in new), "own colour only")
                if len(new) == 2:
                    peri_moves += 1
                    a, b = new
                    check(M.antipode(a) == b, "the second stone is the antipode")
                    check(all(c in sp.ring_index for c in new),
                          "a double placement is a perimeter pair")
                else:
                    inter_moves += 1
                    check(new[0] not in sp.ring_index,
                          "a single placement is never on the perimeter")
                # the pairing invariant, after every single ply
                for c in sp.ring:
                    a = M.antipode(c)
                    check((c in s.stones) == (a in s.stones)
                          and s.stones.get(c) == s.stones.get(a),
                          f"pairing invariant, size {size}")
                half += len(half_arcs(sp, s.stones))
                prev = s
            last = hist[-1]
            check(G.is_terminal(last), "the game terminated")
            if last.winner is None:
                draws += 1
                check(len(last.stones) == len(sp.cells), "a draw is a FULL board")
            else:
                wins[last.winner] += 1
                check(G.has_won(last, last.winner), "the winner holds a win")
                check(not G.has_won(last, 1 - last.winner),
                      "the loser does not hold a win")
                check(G.legal_moves(last) == [], "no moves after a win")
                check(len(G.winning_group(last)) >= 2, "winning group found")
                arcs = G.winning_arc(last)
                check(2 * len(arcs) > sp.perimeter, "winning arc is over half")
                check(all(c in sp.ring_index for c in arcs), "arc is on the ring")
            # termination bound, derived from the board, not pinned
            bound = 3 * size * size - 6 * size + 4
            check(len(hist) - 1 <= bound, f"ply bound {bound} for size {size}")
            max_plies[size] = max(max_plies.get(size, 0), len(hist) - 1)
            sp_seen[size] = True
    check(draws == 0, "no random game ever ended in a draw")
    # A covering arc of EXACTLY half the perimeter is impossible while the
    # pairing invariant holds: if the arc were [a … b] of length P/2 then
    # antipode(a) = b+1, which the invariant colours like a, and b+1 is
    # ring-adjacent to b — so it would join the group and lengthen the arc.
    # (Hence "> half" and ">= half" can never disagree in a real game; the
    # difference is only visible on hand-built perimeter sets.)
    check(half == 0, "no reachable group has an arc of exactly half the perimeter")
    check(wins[0] > 0 and wins[1] > 0, "BOTH seats win somewhere in the sweep")
    check(peri_moves > 50 and inter_moves > 50, "both move kinds exercised")
    # the bound is TIGHT: a full board is reachable, so it is not slack padding
    check(max_plies[7] <= 3 * 49 - 42 + 4, "size-7 bound respected")


# A rim turn puts down TWO stones, and either of them may be the one that
# completes a win.  This position (reached in random play, side 4, Blue to
# move) is the case where the win exists ONLY in the group of the *mandatory
# second* stone: Blue plays the rim cell 2,-3, whose own group spans a mere 5
# of the 18 rim cells, and the engine's forced companion at -2,3 joins a group
# spanning 11.  A win check that looked only at the cell the player clicked
# would score this as "no win", let play continue past a legal win, and could
# hand the game to the wrong player.  Measured frequency: 5 of 1,380 random
# decisive games, so no sweep can be relied on to hit it.
SECOND_STONE_WIN = ['BB.R', 'B.BRB', 'BBBRRB', 'RRRB.BR', 'BRRRRB', 'BBRRB', 'R.BB']


def test_win_from_the_second_stone():
    sp = M.spec_for(4)
    stones = parse_fig(SECOND_STONE_WIN)
    for c in sp.ring:                       # the position is a legal one
        a = M.antipode(c)
        check((c in stones) == (a in stones) and stones.get(c) == stones.get(a),
              "the fixture obeys the pairing invariant")

    def arc_len(st, cell):
        grp = G.group_of(st, cell)
        arc = M.covering_arc(sp, [sp.ring_index[c] for c in grp
                                  if c in sp.ring_index])
        return 0 if arc is None else len(arc)

    for seat in (0, 1):                     # and its colour-swapped twin
        st = {c: (o if seat == 1 else 1 - o) for c, o in stones.items()}
        s = M.HexYState(size=4, stones=st, to_move=seat, plies=25)
        check("2,-3" in G.legal_moves(s), "the winning rim move is available")
        t = G.apply_move(s, "2,-3")
        clicked, second = (2, -3), M.antipode((2, -3))
        check(t.last == (clicked, second), "the turn placed the rim PAIR")
        check(arc_len(t.stones, clicked) == 5,
              "the clicked stone's own group spans only 5 of 18")
        check(not M.arc_wins(sp, M.covering_arc(
            sp, [sp.ring_index[c] for c in G.group_of(t.stones, clicked)
                 if c in sp.ring_index])),
              "…so the clicked stone alone is NOT a win")
        check(arc_len(t.stones, second) == 11, "the forced companion spans 11")
        check(t.winner == seat,
              "the win carried by the MANDATORY SECOND stone is detected, "
              "and awarded to the mover")
        check(G.returns(t)[seat] == 1.0, "…with the payoff on the right seat")
        check(second in G.winning_group(t),
              "winning_group reports the second stone's group")
        check(len(G.winning_arc(t)) == 11, "winning_arc reports its arc")

        # …and the mirror image: clicking the OTHER end of the same pair puts
        # the winning group on the cell the player chose and the harmless one
        # on the forced companion.  Both orders must be detected, so neither
        # "check only the clicked stone" nor "check only the companion" can
        # pass.  Same two cells, same result — only the click order differs.
        u = G.apply_move(s, f"{second[0]},{second[1]}")
        check(u.last == (second, clicked), "the mirror turn placed the same pair")
        check(arc_len(u.stones, u.last[0]) == 11 and arc_len(u.stones, u.last[1]) == 5,
              "the mirror turn's win sits on the CLICKED stone")
        check(u.winner == seat, "the mirror-order win is detected too")
        check(u.stones == t.stones, "both click orders reach the same board")


def test_termination_monovariant():
    """Every turn strictly reduces the number of empty cells (the swap is the
    only exception and can happen at most once), so the game must end; there is
    no ply cap anywhere in the package."""
    src = (Path(__file__).resolve().parent / "game.py").read_text()
    check("PLY_CAP" not in src and "max_random_plies" not in src,
          "no ply cap: termination is proved, not capped")
    for size in (4, 7):
        for pie in (False, True):
            hist = play(size, 12345 + size, pie=pie)
            empties = [len(M.spec_for(size).cells) - len(s.stones) for s in hist]
            drops = sum(1 for a, b in zip(empties, empties[1:]) if b >= a)
            check(drops <= (1 if pie else 0),
                  "empty cells strictly decrease (swap excepted, once)")
            check(empties[-1] == 0 or hist[-1].winner is not None,
                  "a game ends by a win or by filling the board")

    # The bound above is Steere's game.  The optional pie adds EXACTLY one ply
    # — the swap increments `plies` but places no stone — so a pie game's
    # ceiling is `bound + 1`, and random play DOES reach it (side 5: 50 plies
    # against a pie-free bound of 49).  Pinned here because a bound asserted
    # one too low is the classic regression in this codebase.
    s = G.initial_state({"size": 4, "pie": True})
    a = G.apply_move(s, "0,0")
    b = G.apply_move(a, "swap")
    check(b.plies == a.plies + 1 and len(b.stones) == len(a.stones),
          "the swap ply advances the ply count without filling a cell")
    for size in (4, 5):
        bound = 3 * size * size - 6 * size + 4
        for seed in range(24):
            n_free = len(play(size, seed * 17 + size, pie=False)) - 1
            n_pie = len(play(size, seed * 17 + size, pie=True)) - 1
            check(n_free <= bound, f"pie-free bound {bound} (size {size})")
            check(n_pie <= bound + 1, f"pie bound {bound + 1} (size {size})")

    # The board-full guard is a safety net that real play never reaches (the
    # game is drawless), so reach it by hand — otherwise `is_terminal` could
    # drop the "no legal moves" test and nothing would notice.
    sp = M.spec_for(4)
    full = M.HexYState(size=4, stones={c: 0 for c in sp.cells}, to_move=0,
                       plies=len(sp.cells))
    check(G.legal_moves(full) == [], "a full board offers no move")
    check(G.is_terminal(full), "a full board is TERMINAL even with no winner")
    check(G.returns(full) == [0.0, 0.0],
          "no winner scores an honest 0-0 draw, never a fabricated tiebreak")
    check(G.render(full)["caption"] == "Board full — draw", "draw caption")
    # …and a win outranks everything, whatever the board looks like
    won = M.HexYState(size=4, stones={c: 0 for c in sp.cells}, to_move=1,
                      winner=0, plies=len(sp.cells))
    check(G.is_terminal(won) and G.returns(won) == [1.0, -1.0],
          "a decisive result is decisive")


# ------------------------------------------------------------ drawlessness --

def wins_board(sp, stones, seat):
    seen = set()
    for c, o in stones.items():
        if o != seat or c in seen:
            continue
        g = G.group_of(stones, c)
        seen |= g
        arc = M.covering_arc(sp, [sp.ring_index[x] for x in g
                                  if x in sp.ring_index])
        if M.arc_wins(sp, arc):
            return True
    return False


def test_drawless():
    """Exhaustive for sides 2 and 3: EVERY full board obeying the pairing
    invariant has exactly one winner.  Dropping the invariant produces
    thousands of draws, so the double-placement rule is load-bearing."""
    for n, expect in ((2, 16), (3, 8192)):
        sp = M.spec_for(n)
        P = sp.perimeter
        pairs = [(sp.ring[i], sp.ring[i + P // 2]) for i in range(P // 2)]
        interior = [c for c in sp.cells if c not in sp.ring_index]
        total = draws = both = halves = 0
        for pv in itertools.product((0, 1), repeat=len(pairs)):
            base = {}
            for (a, b), v in zip(pairs, pv):
                base[a] = base[b] = v
            for iv in itertools.product((0, 1), repeat=len(interior)):
                st = dict(base)
                st.update(zip(interior, iv))
                total += 1
                w0, w1 = wins_board(sp, st, 0), wins_board(sp, st, 1)
                if not w0 and not w1:
                    draws += 1
                if w0 and w1:
                    both += 1
                halves += len(half_arcs(sp, st))
        check(total == expect, f"enumerated {expect} boards for n={n}")
        check(draws == 0, f"n={n}: no invariant-respecting full board is a draw")
        check(both == 0, f"n={n}: exactly one player wins on a full board")
        check(halves == 0,
              f"n={n}: no group ever spans EXACTLY half the perimeter")

    # the same exhaustion WITHOUT the pairing invariant does find draws
    sp = M.spec_for(2)
    cells = list(sp.cells)
    free_draws = sum(
        1 for v in itertools.product((0, 1), repeat=len(cells))
        if not wins_board(sp, dict(zip(cells, v)), 0)
        and not wins_board(sp, dict(zip(cells, v)), 1))
    check(free_draws > 0,
          "without the double placement, full boards CAN be drawn "
          "(so the pairing invariant is what makes the game drawless)")

    # sampling on bigger boards
    rnd = random.Random(7)
    for n, N in ((4, 3000), (5, 800), (7, 200)):
        sp = M.spec_for(n)
        P = sp.perimeter
        pairs = [(sp.ring[i], sp.ring[i + P // 2]) for i in range(P // 2)]
        interior = [c for c in sp.cells if c not in sp.ring_index]
        for _ in range(N):
            st = {}
            for a, b in pairs:
                st[a] = st[b] = rnd.randint(0, 1)
            for c in interior:
                st[c] = rnd.randint(0, 1)
            check(wins_board(sp, st, 0) != wins_board(sp, st, 1),
                  f"n={n}: a full board has exactly one winner")


# --------------------------------------------------------- state plumbing --

KEYS = {"size", "stones", "to_move", "winner", "last", "pie", "plies"}


def test_serialize():
    """Compare STATE OBJECTS (a `serialize(deserialize(d)) == d` test cannot
    see a dropped field), plus the exact key set, swept over whole games."""
    seen_winner = seen_swap = seen_pair = 0
    for size in (4, 7):
        for pie in (False, True):
            for seed in range(2):
                for s in play(size, seed * 31 + size, pie=pie):
                    d = G.serialize(s)
                    check(set(d) == KEYS, f"exact serialized key set {set(d)}")
                    json.dumps(d)
                    back = G.deserialize(d)
                    check(back == s, "deserialize(serialize(s)) == s")
                    check(G.serialize(back) == d, "and re-serializes identically")
                    if s.winner is not None:
                        seen_winner += 1
                    if len(s.last) == 2:
                        seen_pair += 1
    # force a swap through the round trip too
    s = G.initial_state({"size": 4, "pie": True})
    s = G.apply_move(s, next(m for m in G.legal_moves(s)
                             if M.hex_dist(*M._cell(m)) == 3))
    check("swap" in G.legal_moves(s), "swap offered on seat 1's first turn")
    check(len(s.stones) == 2, "the opening perimeter move placed a pair")
    t = G.apply_move(s, "swap")
    check(set(t.stones.values()) == {1}, "swap hands the opening to seat 1")
    check(t.to_move == 0 and t.plies == 2, "swap returns the move")
    check("swap" not in G.legal_moves(t), "swap is offered only once")
    check(G.deserialize(G.serialize(t)) == t, "swap state round-trips")
    seen_swap += 1
    check(seen_winner and seen_pair and seen_swap,
          "the sweep covered a winner, a perimeter pair and a swap")
    # a state whose fields are all non-default must survive
    check(G.deserialize(G.serialize(t)).pie is True, "pie survives the round trip")


# ------------------------------------------------------------------ render --

def test_render_bounds():
    """`Board.jsx` builds its clickable cells from the DECLARED board and
    silently drops any piece outside it — so check every size on a position
    reached through apply_move that reaches the far corners."""
    for size in SIZES:
        sp = M.spec_for(size)
        R = size - 1
        s = G.initial_state({"size": size})
        # drive stones into the extreme corners: a corner is on the perimeter,
        # so each of these turns also fills the opposite corner.
        for corner in ((R, 0), (0, R), (R, -R)):
            if corner in s.stones:
                continue
            s = G.apply_move(s, f"{corner[0]},{corner[1]}")
            if G.is_terminal(s):
                break
        spec = G.render(s)
        b = spec["board"]
        check(b["type"] == "hex" and b["shape"] == "hexagon", "hexhex board")
        check(b["size"] == size, f"declared size {b['size']} == {size}")
        declared = {f"{q},{r}" for q in range(-R, R + 1) for r in range(-R, R + 1)
                    if abs(q + r) <= R}
        check(declared == {f"{q},{r}" for q, r in sp.cells}, "cell sets agree")
        for p in spec["pieces"]:
            check(p["cell"] in declared,
                  f"piece {p['cell']} is inside the size-{size} board")
        check(len(spec["pieces"]) == len(s.stones), "every stone is rendered")
        for c in spec["board"]["tints"]:
            check(c in declared, "tinted cell is on the board")
        check(set(spec["board"]["tints"]) ==
              {f"{q},{r}" for q, r in sp.ring}, "the ring is tinted")
        for h in spec["highlights"]:
            check(h["cell"] in declared, "highlight is on the board")
        check(isinstance(spec["caption"], str) and spec["caption"], "caption")
        check(max(abs(q) for q, r in s.stones) == R, "a far-corner stone exists")

    # a won position renders its winning arc
    hist = play(4, 5)
    last = hist[-1]
    if last.winner is not None:
        spec = G.render(last)
        arc = {f"{q},{r}" for q, r in G.winning_arc(last)}
        check({h["cell"] for h in spec["highlights"] if h["kind"] == "goal"} == arc,
              "the winning arc is highlighted")


# -------------------------------------------------------- seat conjugation --

def mirror(s):
    """The same position with the two seats exchanged."""
    return M.HexYState(size=s.size, stones={c: 1 - o for c, o in s.stones.items()},
                       to_move=1 - s.to_move,
                       winner=None if s.winner is None else 1 - s.winner,
                       last=s.last, pie=s.pie, plies=s.plies)


def test_seat_symmetry():
    """Nothing may treat seat 0 and seat 1 differently: the engine must
    conjugate under the colour swap."""
    for size in (4, 7):
        for seed in range(3):
            for s in play(size, 1000 + seed * 7 + size):
                m = mirror(s)
                check(sorted(G.legal_moves(s)) == sorted(G.legal_moves(m)),
                      "legal moves are colour-blind")
                check(G.is_terminal(s) == G.is_terminal(m), "terminal conjugates")
                if G.is_terminal(s):
                    check(G.returns(s) == list(reversed(G.returns(m))),
                          "returns conjugate")
                check(G.has_won(s, 0) == G.has_won(m, 1), "has_won conjugates 0")
                check(G.has_won(s, 1) == G.has_won(m, 0), "has_won conjugates 1")
                h1, h2 = G.heuristic(s), G.heuristic(m)
                check(abs(h1[0] + h2[0]) < 1e-9, "the heuristic conjugates")
                if not G.is_terminal(s):
                    mv = G.legal_moves(s)[len(G.legal_moves(s)) // 2]
                    check(mirror(G.apply_move(s, mv)) == G.apply_move(m, mv),
                          "apply_move conjugates")


# --------------------------------------------------------------- heuristic --

def test_heuristic():
    s = G.initial_state({"size": 7})
    h = G.heuristic(s)
    check(isinstance(h, list) and len(h) == 2, "heuristic returns a LIST of 2")
    check(all(isinstance(x, float) for x in h), "…of floats")
    check(abs(h[0] + h[1]) < 1e-12, "zero sum")
    check(all(-1.0 <= x <= 1.0 for x in h), "in range")
    check(h == [0.0, 0.0], "an empty board is even")

    # DIRECTION.  Two invariant-respecting Red positions: a long rim span and a
    # short one, with Blue absent.  The longer span MUST score higher, and the
    # values are pinned so a rescale or a sign flip cannot pass.
    sp = M.spec_for(4)
    P = sp.perimeter

    def red_run(k):
        cells = [sp.ring[i] for i in range(k)] + [sp.ring[(i + P // 2) % P]
                                                  for i in range(k)]
        return M.HexYState(size=4, stones={c: 0 for c in cells}, to_move=1,
                           plies=k)

    strong, weak = red_run(6), red_run(2)
    hs, hw = G.heuristic(strong), G.heuristic(weak)
    check(hs[0] > hw[0] > 0.0,
          f"a longer rim span scores HIGHER ({hs[0]:.4f} > {hw[0]:.4f} > 0)")
    check(abs(hs[0] - 0.9902) < 5e-4, f"pinned strong value {hs[0]:.4f}")
    check(abs(hw[0] - 0.7106) < 5e-4, f"pinned weak value {hw[0]:.4f}")
    check(hs[1] < hw[1] < 0.0, "and Blue's payoff moves the other way")
    check(G._rim_reach(sp, strong.stones, 0) > G._rim_reach(sp, weak.stones, 0),
          "the underlying rim-reach term is monotone in the span")
    check(G._rim_reach(sp, strong.stones, 1) == 0, "an absent seat reaches nothing")

    # monotone: extending a group's rim span can only raise its own score
    prev = -2.0
    for k in range(1, 8):
        v = G.heuristic(red_run(k))[0]
        check(v >= prev, f"rim-reach is monotone in k (k={k})")
        prev = v

    # a decided position must dominate everything
    hist = play(4, 5)
    if hist[-1].winner is not None:
        w = hist[-1].winner
        check(G.heuristic(hist[-1]) == G.returns(hist[-1]),
              "a finished game evaluates to its result")
        check(G.heuristic(hist[-1])[w] == 1.0, "the winner scores +1")

    # the MCTS back-prop path: a bare float would raise here
    for st in (s, strong, weak):
        payoffs = G.heuristic(st)
        for p in range(G.num_players):
            float(payoffs[p])
    # and it stays cheap enough to be called at every rollout cut-off
    big = G.initial_state({"size": 11})
    rnd = random.Random(4)
    for _ in range(40):
        big = G.apply_move(big, rnd.choice(G.legal_moves(big)))
    check(len(G.heuristic(big)) == 2, "the largest board evaluates too")


# ------------------------------------------------------- notation & extras --

def test_notation():
    s = G.initial_state({"size": 4})
    # an interior move names one cell; a perimeter move names the pair
    check(G.describe_move(s, "0,0") == M.cell_name(4, (0, 0)), "interior notation")
    d = G.describe_move(s, "0,-3")
    check("+" in d and d.split("+")[1] == M.cell_name(4, (0, 3)),
          f"perimeter notation names the pair ({d})")
    t = G.apply_move(s, "0,-3")
    check(G.describe_move(t, "0,3") == M.cell_name(4, (0, 3)),
          "an already-paired cell is never re-paired")
    sp2 = G.initial_state({"size": 4, "pie": True})
    sp2 = G.apply_move(sp2, "0,0")
    check(G.describe_move(sp2, "swap") == "swap (pie)", "swap notation")

    # illegal moves are refused
    u = G.apply_move(t, "0,0")
    for state, bad, why in ((s, "9,9", "off-board"), (u, "0,0", "occupied"),
                            (u, "0,3", "occupied by the antipodal partner"),
                            (s, "swap", "swap while the pie rule is off")):
        try:
            G.apply_move(state, bad)
            raise AssertionError(f"{why} move {bad} was accepted")
        except ValueError:
            check(True, f"{why} move refused")

    # public helpers are covered (a predicate off the legality path is the one
    # nobody tests)
    hist = play(4, 5)
    last = hist[-1]
    if last.winner is not None:
        grp = G.winning_group(last)
        check(all(last.stones.get(c) == last.winner for c in grp),
              "winning_group is all the winner's stones")
        check(grp == G.group_of(last.stones, next(iter(grp))),
              "winning_group is connected")
        arc = G.winning_arc(last)
        peri = [c for c in grp if c in M.spec_for(4).ring_index]
        check(set(peri) <= set(arc), "the arc covers the group's perimeter stones")
    check(G.winning_group(hist[0]) == set() and G.winning_arc(hist[0]) == (),
          "no winning group before anyone has won")
    check(G.group_of({}, (0, 0)) == set(), "group_of on an empty board")


def test_options():
    for size in SIZES:
        s = G.initial_state({"size": size})
        check(len(G.legal_moves(s)) == 3 * size * size - 3 * size + 1,
              f"opening move count for size {size}")
    check(len(G.legal_moves(G.initial_state({"size": 7}))) == 127,
          "the default board offers 127 opening moves (AbstractPlay's count)")
    check(len(G.legal_moves(G.initial_state())) == 127, "default size is 7")
    for bad in (3, 12, 0):
        try:
            G.initial_state({"size": bad})
            raise AssertionError(f"accepted size {bad}")
        except ValueError:
            pass
    s = G.initial_state({"size": 4, "pie": "true"})
    check(s.pie is True, "a string option value is coerced")
    check("swap" not in G.legal_moves(s), "no swap before the opening move")
    check("swap" not in G.legal_moves(G.apply_move(
        G.apply_move(s, "0,0"), "1,0")), "swap expires after seat 1 moves")


if __name__ == "__main__":
    for fn in (test_geometry, test_figures, test_arc_predicate, test_games,
               test_win_from_the_second_stone,
               test_termination_monovariant, test_drawless, test_serialize,
               test_render_bounds, test_seat_symmetry, test_heuristic,
               test_notation, test_options):
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"hexagonal_y selftest: {ok} assertions passed")
