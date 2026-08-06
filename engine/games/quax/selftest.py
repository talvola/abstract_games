#!/usr/bin/env python3
"""Correctness anchors for Quax (games/quax).  Pure stdlib.

The anchors, strongest first:

1. **The designer's published 3x3 puzzle.**  Bill Taylor's puzzle (jpn's page:
   "Black started.  Who wins?" / "Solution: Black wins!") is solved
   EXHAUSTIVELY here and must come out a first-player win.  A published game
   value validates the whole ruleset end-to-end.
2. **The designer's "Race to connections" figure**, transcribed cell-for-cell
   from the encoded diagram on his page, whose caption states the winner and
   the winning move.  This is the OUTSIDE-THE-ENGINE ground truth for which
   seat owns which pair of edges, so the seat-name / goal / caption constants
   cannot be swapped without failing here.
3. **Drawlessness (Lemma A)** verified exhaustively over every full 3x3 and 4x4
   position with the contested squares resolved every possible way.
4. **The designer's three sample game records** replayed move for move.
5. Move generation cross-checked against an independently written enumerator.
6. serialize/deserialize compared as STATES, render bounds at every board size
   from far-corner positions, and the transpose lemma the pie rule rests on.
7. **The designer's 1992 COMPLETED 4x4 game** (r.g.a, 1992-12-18) -- a second
   independent published position with a stated winner, path length and move
   counts, already in this library's frame.
8. The two things mutation testing showed nothing else pinned: the sign of
   `returns()`, and the bar-overlay colour / goal-edge tints -- who owns
   which bar and who aims at which pair of edges, read off the BOARD.
"""
from __future__ import annotations

import itertools
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir                       # noqa: E402

HERE = Path(__file__).resolve().parent
MAN, G = load_from_dir(HERE)
M = sys.modules[type(G).__module__]
QuaxState = M.QuaxState
endpoints, link_move, algebraic = M.endpoints, M.link_move, M.algebraic
BLACK, WHITE = M.BLACK, M.WHITE

CHECKS = 0


def ck(cond, msg):
    global CHECKS
    CHECKS += 1
    if not cond:
        raise AssertionError(msg)


# --------------------------------------------------------------------------
# helpers shared by several anchors
# --------------------------------------------------------------------------
def alg2cell(a: str) -> tuple[int, int]:
    """Designer's / igGameCenter's algebraic ("f7") -> our (col, row)."""
    return (ord(a[0]) - 97, int(a[1:]) - 1)


def T(cell):
    return (cell[1], cell[0])


def mv_of(cell):
    return f"{cell[0]},{cell[1]}"


def link_between(a, b) -> str:
    """Canonical link move joining two diagonally adjacent cells."""
    square = (min(a[0], b[0]), min(a[1], b[1]))
    diag = "/" if (a[0] < b[0]) == (a[1] < b[1]) else "\\"
    ck(set(endpoints(square, diag)) == {a, b}, "link_between geometry")
    return link_move(square, diag)


def brute_moves(st):
    """An INDEPENDENT move enumerator, deliberately written the other way round:
    it walks CELL PAIRS and looks the blocking diagonal up by its ENDPOINTS,
    the way the AbstractPlay implementation does, instead of keying links by
    2x2 square as game.py does."""
    n = st.size
    out = set()
    for r in range(n):
        for c in range(n):
            if (c, r) not in st.stones:
                out.add(f"{c},{r}")
    linked = set()
    for sq, (owner, diag) in st.links.items():
        a, b = endpoints(sq, diag)
        linked.add(frozenset((a, b)))
    p = st.to_move
    for (c, r), o in st.stones.items():
        if o != p:
            continue
        for dc, dr in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            nb = (c + dc, r + dr)
            if not (0 <= nb[0] < n and 0 <= nb[1] < n):
                continue
            if st.stones.get(nb) != p:
                continue
            if frozenset(((c, r), nb)) in linked:
                continue
            cross = frozenset((((c, r)[0], nb[1]), (nb[0], (c, r)[1])))
            if cross in linked:
                continue
            out.add(link_between((c, r), nb))
    if G._swap_available(st):
        out.add("swap")
    return out


def solve(st, memo):
    """Exact value from seat 0's point of view (+1 Black win, -1 White win)."""
    if st.winner is not None:
        return 1 if st.winner == BLACK else -1
    mv = G.legal_moves(st)
    if not mv:
        return 0                                   # would be a DRAW
    k = (tuple(sorted(st.stones.items())), tuple(sorted(st.links.items())),
         st.to_move, G._swap_available(st))
    if k in memo:
        return memo[k]
    best = -2 if st.to_move == BLACK else 2
    for m in mv:
        v = solve(G.apply_move(st, m), memo)
        if st.to_move == BLACK:
            if v > best:
                best = v
            if best == 1:
                break
        else:
            if v < best:
                best = v
            if best == -1:
                break
    memo[k] = best
    return best


# --------------------------------------------------------------------------
# 1. the designer's published 3x3 puzzle  (jpn/Bill Taylor: "Black wins!")
# --------------------------------------------------------------------------
def test_designer_puzzle():
    # His diagram is `lurd,3,3,3/3/.x.` -- a single Black stone on b1 -- and in
    # HIS frame Black joins the LEFT and RIGHT edges (see test_race_figure).
    # This library's seat 0 joins TOP and BOTTOM, so his position maps into our
    # frame by the transpose: b1 = (1,0) -> (0,1).
    st = QuaxState(size=3, pie=False, stones={T(alg2cell("b1")): BLACK},
                   to_move=WHITE, ply=1)
    v = solve(st, {})
    ck(v == 1, f"designer's 3x3 puzzle should be a BLACK (first player) win, got {v}")

    # And the published solution line must be legal and reach his final diagram
    # (`lurd,3,3,.i./cae/.xd`): Red b2, Black a2, Red c1, Black c2,
    # Red connects b2-c1, Black b3.
    line = ["b2", "a2", "c1", "c2", ("b2", "c1"), "b3"]
    cur = st
    for step in line:
        if isinstance(step, tuple):
            m = link_between(T(alg2cell(step[0])), T(alg2cell(step[1])))
        else:
            m = mv_of(T(alg2cell(step)))
        ck(m in G.legal_moves(cur), f"puzzle solution move {step} illegal")
        cur = G.apply_move(cur, m)
    ck(cur.winner is None, "the puzzle line should not have ended the game yet")
    ck(solve(cur, {}) == 1, "Black must still be winning after the published line")
    # "There is no way to stop the Black chain": Black wins whatever Red does.
    for m in G.legal_moves(cur):
        ck(solve(G.apply_move(cur, m), {}) == 1,
           f"Red's {m} should not save the position")


# --------------------------------------------------------------------------
# 2. the designer's "Race to connections" figure  -> pins seats to edges
# --------------------------------------------------------------------------
# Transcribed from the encoded diagram
#   lurd,11,11,u10/.x9/u3u6/u10/axxxx@cx0010u4/u4u@cx1000xxxx/uu@cu00108/
#   3@cu10107/4@cu1000u5/5x5/11
# x = Black, u = Red, and the caption reads: "If it's Black turn he wins by
# playing at cell [1]" -- cell [1] being the marker at a7.  Black's chain then
# runs a7-b7-c7-d7-e7-f7 = g6-h6-i6-j6-k6, i.e. from file a to file k: in the
# DESIGNER's frame Black joins LEFT to RIGHT.  Under this library's convention
# (seat 0 joins TOP to BOTTOM) the figure maps in by the transpose, which is
# why every cell below is wrapped in T().
RACE_BLACK = "b10 b7 c7 d7 e7 f7 g6 h6 i6 j6 k6 f2".split()
RACE_RED = "a11 a9 a8 a6 a5 b5 c5 d4 e3 f3 f6 g7 e9".split()
RACE_LINKS_BLACK = [("f7", "g6")]
RACE_LINKS_RED = [("c5", "d4"), ("d4", "e3")]
RACE_WINNING_MOVE = "a7"


def race_state(to_move):
    stones = {}
    for a in RACE_BLACK:
        stones[T(alg2cell(a))] = BLACK
    for a in RACE_RED:
        stones[T(alg2cell(a))] = WHITE
    ck(len(stones) == len(RACE_BLACK) + len(RACE_RED), "figure has overlapping stones")
    links = {}
    for owner, pairs in ((BLACK, RACE_LINKS_BLACK), (WHITE, RACE_LINKS_RED)):
        for a, b in pairs:
            m = link_between(T(alg2cell(a)), T(alg2cell(b)))
            sq, diag = M.link_of_move(m)
            links[sq] = (owner, diag)
    ck(len(links) == 3, "figure has 3 links")
    return QuaxState(size=11, pie=False, stones=stones, links=links,
                     to_move=to_move, ply=len(stones) + len(links))


def test_race_figure():
    win = mv_of(T(alg2cell(RACE_WINNING_MOVE)))
    # -- premises the figure relies on (a mis-transcription breaks these first)
    st = race_state(BLACK)
    ck(G.connection_path(st, BLACK) is None, "nobody is connected in the figure yet")
    ck(G.connection_path(st, WHITE) is None, "nobody is connected in the figure yet")
    ck(win in G.legal_moves(st), "cell [1] must be empty and playable")
    for a in RACE_BLACK:
        ck(st.stones[T(alg2cell(a))] == BLACK, f"figure: {a} is Black")
    for a in RACE_RED:
        ck(st.stones[T(alg2cell(a))] == WHITE, f"figure: {a} is Red")

    # -- the outcome the caption states: Black to move WINS by playing [1]
    after = G.apply_move(st, win)
    ck(after.winner == BLACK,
       "the designer's figure says Black wins by playing cell [1]")
    path = G.connection_path(after, BLACK)
    ck(path is not None and len(path) == 11, f"winning chain of 11 stones, got {path}")
    # The chain must touch BOTH of seat 0's edges and NOT be a left-right chain:
    rows = {cell[1] for cell in path}
    cols = {cell[0] for cell in path}
    ck(0 in rows and 10 in rows, "the winning chain reaches both of seat 0's edges")
    ck(cols == {5, 6}, f"the chain occupies exactly two files, got {sorted(cols)}")

    # -- and the OTHER half of the caption: "If it's Red he must play at [1] AND
    #    have a powerful threat to win at cell a10" -- i.e. Red playing [1] does
    #    NOT win.  This is what makes the figure discriminate the two seats:
    #    swapping the goals makes one of these two assertions fail.
    st_r = race_state(WHITE)
    after_r = G.apply_move(st_r, win)
    ck(after_r.winner is None, "Red playing cell [1] must NOT win outright")
    ck(mv_of(T(alg2cell("a10"))) in G.legal_moves(after_r),
       "a10 (Red's follow-up) must still be empty")

    # -- captions, pinned to the figure rather than to the engine's own naming
    cap = G.render(after)["caption"]
    ck(cap.startswith("Black wins"), f"terminal caption: {cap!r}")
    ck("top-bottom" in cap, f"seat 0's edges named in the caption: {cap!r}")
    cap_r = G.render(st_r)["caption"]
    ck(cap_r.startswith("White to move"), f"in-play caption: {cap_r!r}")
    ck("left-right" in cap_r, f"seat 1's edges named in the caption: {cap_r!r}")
    cap_b = G.render(st)["caption"]
    ck(cap_b.startswith("Black to move") and "top-bottom" in cap_b,
       f"in-play caption: {cap_b!r}")


# --------------------------------------------------------------------------
# 3. Lemma A -- drawlessness.  Also Lemma R, which Lemma A's enumeration uses.
# --------------------------------------------------------------------------
def _is_checker(cols):
    bl, br, tl, tr = cols
    return bl == tr and tl == br and bl != tl


def _mono(cols):
    bl, br, tl, tr = cols
    out = []
    if bl == tr:
        out.append(("/", bl))
    if tl == br:
        out.append(("\\", tl))
    return out


def test_lemma_R():
    """A monochromatic diagonal in a NON-checkerboard 2x2 square is REDUNDANT:
    its two endpoints already share a same-coloured orthogonal neighbour inside
    the square.  This is what lets Lemma A's enumeration ignore those links."""
    seen = 0
    for cols in itertools.product((0, 1), repeat=4):
        if _is_checker(cols):
            continue
        bl, br, tl, tr = cols
        for diag, owner in _mono(cols):
            others = (tl, br) if diag == "/" else (bl, tr)
            ck(owner in others, f"Lemma R fails for {cols} {diag}")
            seen += 1
    ck(seen == 12, f"Lemma R covered {seen} cases")


def _resolutions(size, colouring):
    contested = []
    for sr in range(size - 1):
        for sc in range(size - 1):
            cols = (colouring[(sc, sr)], colouring[(sc + 1, sr)],
                    colouring[(sc, sr + 1)], colouring[(sc + 1, sr + 1)])
            if _is_checker(cols):
                contested.append(((sc, sr), cols))
    for choice in itertools.product((0, 1), repeat=len(contested)):
        links = {}
        for (sq, cols), which in zip(contested, choice):
            diag, owner = _mono(cols)[which]
            links[sq] = (owner, diag)
        yield links


def _check_full(size, colouring, tally):
    for links in _resolutions(size, colouring):
        st = QuaxState(size=size, pie=False, stones=dict(colouring), links=links)
        b = G.connection_path(st, BLACK) is not None
        w = G.connection_path(st, WHITE) is not None
        tally[0] += 1
        ck(b != w, f"Lemma A: b={b} w={w} on {size}x{size} {sorted(colouring.items())} "
                   f"links {sorted(links.items())}")
        tally[1 if b else 2] += 1


def test_lemma_A_exhaustive(size):
    """EXACTLY ONE player is connected in every full board whose contested
    (checkerboard) squares all hold a link.  That is precisely the shape of an
    exhausted Quax position (Lemma B), so Quax cannot be drawn and can never
    leave a player with no legal move before the game is already over."""
    cells = [(c, r) for r in range(size) for c in range(size)]
    tally = [0, 0, 0]
    for bits in range(2 ** len(cells)):
        _check_full(size, {cells[i]: (bits >> i) & 1 for i in range(len(cells))},
                    tally)
    # the enumeration is transpose-symmetric, so the two winner counts must match
    ck(tally[1] == tally[2], f"asymmetric tally {tally}")
    return tally


def test_lemma_A_sampled(size, n, seed):
    rng = random.Random(seed)
    cells = [(c, r) for r in range(size) for c in range(size)]
    tally = [0, 0, 0]
    for _ in range(n):
        colouring = {cell: rng.randrange(2) for cell in cells}
        links = {}
        for sr in range(size - 1):
            for sc in range(size - 1):
                cols = (colouring[(sc, sr)], colouring[(sc + 1, sr)],
                        colouring[(sc, sr + 1)], colouring[(sc + 1, sr + 1)])
                if _is_checker(cols):
                    diag, owner = _mono(cols)[rng.randrange(2)]
                    links[(sc, sr)] = (owner, diag)
        st = QuaxState(size=size, pie=False, stones=colouring, links=links)
        b = G.connection_path(st, BLACK) is not None
        w = G.connection_path(st, WHITE) is not None
        ck(b != w, f"Lemma A sampled failure at {size}x{size}")
        tally[0] += 1
    return tally


def test_lemma_B():
    """A player with no legal move implies every contested square is resolved.

    Verified over every 2x2 colour pattern: a CHECKERBOARD square always offers
    a link to BOTH colours, so an unlinked one can never leave anybody stuck.
    """
    for cols in itertools.product((0, 1), repeat=4):
        owners = {owner for _, owner in _mono(cols)}
        if _is_checker(cols):
            ck(owners == {0, 1},
               f"checkerboard {cols} must offer a link to both seats, got {owners}")
        else:
            ck(len(owners) <= 1, f"non-checkerboard {cols} offers {owners}")


# --------------------------------------------------------------------------
# 4. exhaustive 3x3 solves (drawlessness + the pie-rule value)
# --------------------------------------------------------------------------
def test_small_solves():
    v_off = solve(G.initial_state(options={"size": 3, "pie": "off"}), {})
    ck(v_off == 1, f"3x3 without the pie rule is a first-player win, got {v_off}")
    v_on = solve(G.initial_state(options={"size": 3, "pie": "on"}), {})
    # Strategy stealing: in a drawless game whose swap is value-preserving, the
    # pie rule hands the win to the SECOND player.  A swap that were not
    # value-preserving would not have to produce this.
    ck(v_on == -1, f"3x3 WITH the pie rule is a second-player win, got {v_on}")


# --------------------------------------------------------------------------
# 5. the transpose lemma the pie rule rests on
# --------------------------------------------------------------------------
def test_transpose_lemma():
    """`_transpose` (transpose + recolour) is an exact ANTI-automorphism.

    Exhaustively over every state of the 3x3 game: the transposed position has
    the OTHER seat to move and exactly the OPPOSITE value.  A "recolour in
    place" swap fails this on 795 of the 1937 states (measured), whereas the
    3x3 pie-rule VALUE alone is blind to that mutant -- so this test, not the
    value, is what pins the swap.
    """
    memo = {}
    solve(G.initial_state(options={"size": 3, "pie": "off"}), memo)
    memo2 = {}
    n = 0
    for (stones, links, to_move, _), v in list(memo.items()):
        st = QuaxState(size=3, pie=False, stones=dict(stones), links=dict(links),
                       to_move=to_move, ply=len(stones) + len(links))
        t = replace(G._transpose(st), to_move=1 - to_move)
        ck(solve(t, memo2) == -v, f"transpose lemma fails on {stones} {links}")
        # structural half of the lemma, over the same whole domain
        ck(replace(G._transpose(t), to_move=st.to_move) == st,
           "transpose is not an involution")
        ck((G.connection_path(st, BLACK) is None) ==
           (G.connection_path(t, WHITE) is None), "transpose must exchange the goals")
        ck((G.connection_path(st, WHITE) is None) ==
           (G.connection_path(t, BLACK) is None), "transpose must exchange the goals")
        n += 1
    ck(n > 1900, f"transpose lemma covered only {n} states")
    return n


def test_swap_is_a_transpose():
    """Directly: the pie swap moves the stone to the TRANSPOSED cell and gives
    it to White.  Pinned on a deliberately ASYMMETRIC opening so a "recolour in
    place" implementation cannot pass."""
    st = G.initial_state(options={"size": 11, "pie": "on"})
    st = G.apply_move(st, "2,7")
    ck(st.to_move == WHITE and "swap" in G.legal_moves(st), "swap must be offered")
    sw = G.apply_move(st, "swap")
    ck(sw.stones == {(7, 2): WHITE}, f"swap must transpose+recolour, got {sw.stones}")
    ck(sw.to_move == BLACK and sw.swapped and sw.ply == 2, "swap bookkeeping")
    ck("swap" not in G.legal_moves(sw), "swap must be a one-shot")
    # ... and it is not on offer at any other moment, nor when switched off
    ck("swap" not in G.legal_moves(G.initial_state(options={"size": 11, "pie": "on"})),
       "Black may not swap")
    st3 = G.apply_move(G.apply_move(sw, "0,0"), "1,1")
    ck("swap" not in G.legal_moves(st3), "swap only on White's FIRST turn")
    # and a DECLINED swap is gone for good -- White's second turn, pie still on,
    # nothing swapped, so only the "first turn" clause can rule it out
    dec = G.apply_move(G.apply_move(G.apply_move(
        G.initial_state(options={"size": 11, "pie": "on"}), "2,7"), "5,5"), "6,6")
    ck(dec.to_move == WHITE and not dec.swapped and dec.pie, "premise: White to move again")
    ck("swap" not in G.legal_moves(dec),
       "a swap declined on White's first turn must not come back")
    off = G.apply_move(G.initial_state(options={"size": 11, "pie": "off"}), "2,7")
    ck("swap" not in G.legal_moves(off), "pie=off must not offer swap")
    ck(G.describe_move(st, "swap") == "swap (pie)", "swap notation")


# --------------------------------------------------------------------------
# 6. the crossing rule, pinned to the designer's "connecting example" figure
# --------------------------------------------------------------------------
def test_connecting_example():
    """`lurd,11,11,.../5@cx0010u4/5u@cx10004/...` with the caption "The black
    stones are connected.  The red stones cannot be connected directly.":
    Black f7+g6 with a link, Red g7+f6 with none -- one rhombic cell, two
    candidate diagonals, and the Black link permanently kills the Red one."""
    f7, g6, g7, f6 = (alg2cell(a) for a in ("f7", "g6", "g7", "f6"))
    stones = {f7: BLACK, g6: BLACK, g7: WHITE, f6: WHITE}
    black_link = link_between(f7, g6)
    red_link = link_between(g7, f6)
    ck(M.link_of_move(black_link)[0] == M.link_of_move(red_link)[0],
       "the two diagonals must share one rhombic cell")
    ck(black_link != red_link, "and be different links")

    # before: each side may take the cell
    st_b = QuaxState(size=11, pie=False, stones=stones, to_move=BLACK, ply=4)
    st_w = replace(st_b, to_move=WHITE)
    ck(black_link in G.legal_moves(st_b), "Black's diagonal is available")
    ck(red_link in G.legal_moves(st_w), "Red's diagonal is available")
    # after Black takes it: Red's crossing diagonal is gone for good
    after = G.apply_move(st_b, black_link)
    ck(red_link not in G.legal_moves(after), "a link must block the crossing diagonal")
    ck(black_link not in G.legal_moves(replace(after, to_move=BLACK)),
       "and cannot be placed twice")
    # ... and the figure's connectivity claim
    ck(G.connection_path(replace(after, stones={f7: BLACK, g6: BLACK}), BLACK) is None,
       "premise: two stones alone do not span the board")
    adj = G._neighbours(after, BLACK)
    ck(g6 in adj[f7] and f7 in adj[g6], "the linked Black stones are connected")
    adj_w = G._neighbours(after, WHITE)
    ck(f6 not in adj_w[g7], "the Red stones are NOT connected")


# --------------------------------------------------------------------------
# 7. the designer's three sample games, replayed move for move
# --------------------------------------------------------------------------
SAMPLE_GAMES = [
    "d3 f5 f8 h8 g6 f7 g3 f3 f2 e2 e3 e2f3 f4 g4 f4g3 h3 g5 f5g4 h4 g4h3 g7 e8",
    "d3 e6 c6 c8 h6 h8 f7 f9 e9 e8 d8 g9 c7 e10 c9 d9 c9d8 c4 d5",
    "c3 e5 f3 h3 g5 i6 h4 i4 i9 g7 f8 g9 g8 h8 h7 i7",
]


def test_move_notation():
    """`describe_move` must reproduce the designer's own notation, token for
    token, over all three published game records.

    The records are replayed here UNtransposed: Quax's legality is exactly
    transpose-invariant (see test_transpose_lemma), so the same move sequence is
    legal either way, and this replay pins `algebraic()` -- the move-log
    notation -- to a published source rather than to the engine itself.
    """
    seen_links = 0
    for gi, rec in enumerate(SAMPLE_GAMES):
        st = G.initial_state(options={"size": 11, "pie": "off"})
        for tok in rec.split():
            letters = [i for i, ch in enumerate(tok) if ch.isalpha()]
            if len(letters) == 2:
                a, b = alg2cell(tok[:letters[1]]), alg2cell(tok[letters[1]:])
                m = link_between(a, b)
                want = f"{tok[:letters[1]]}-{tok[letters[1]:]}"
                seen_links += 1
            else:
                m = mv_of(alg2cell(tok))
                want = tok
            ck(m in G.legal_moves(st), f"record {gi + 1}: {tok} illegal (untransposed)")
            got = G.describe_move(st, m)
            ck(got == want, f"record {gi + 1}: describe_move gave {got!r}, "
                            f"the designer wrote {want!r}")
            st = G.apply_move(st, m)
    ck(seen_links == 5, f"expected 5 link tokens across the records, saw {seen_links}")


def test_sample_games():
    for gi, rec in enumerate(SAMPLE_GAMES):
        st = G.initial_state(options={"size": 11, "pie": "off"})
        links_played = 0
        for tok in rec.split():
            # the designer writes a link as two cells run together ("e2f3"),
            # a placement as one cell ("d3", "e10"): split on the 2nd letter.
            letters = [i for i, ch in enumerate(tok) if ch.isalpha()]
            ck(len(letters) in (1, 2) and letters[0] == 0,
               f"cannot parse record token {tok!r}")
            if len(letters) == 2:
                a, b = alg2cell(tok[:letters[1]]), alg2cell(tok[letters[1]:])
                m = link_between(T(a), T(b))
                links_played += 1
            else:
                m = mv_of(T(alg2cell(tok)))
            ck(m in G.legal_moves(st), f"sample game {gi + 1}: {tok} ({m}) is illegal")
            st = G.apply_move(st, m)
            ck(st.winner is None,
               f"sample game {gi + 1} ended in a connection at {tok}; the record "
               f"ends in a resignation")
        ck(links_played == (4, 1, 0)[gi],
           f"sample game {gi + 1} should contain {(4, 1, 0)[gi]} links")


# --------------------------------------------------------------------------
# 8. sweeps: move-gen cross-check, the termination monovariant, invariants
# --------------------------------------------------------------------------
def test_sweeps(sizes=(3, 4, 5, 7, 11), games=6, seed=7):
    rng = random.Random(seed)
    for size in sizes:
        for gi in range(games):
            pie = (gi % 2 == 0)
            st = G.initial_state(options={"size": size,
                                          "pie": "on" if pie else "off"})
            bound = 1 + size * size + (size - 1) * (size - 1)   # see rules.md
            prev_mat = -1
            plies = 0
            while not G.is_terminal(st):
                mv = G.legal_moves(st)
                ck(mv, "a non-terminal state must have a legal move")
                ck(set(mv) == brute_moves(st),
                   f"move-gen disagrees with the independent enumerator at "
                   f"{size}x{size} ply {plies}: only-gen="
                   f"{sorted(set(mv) - brute_moves(st))[:4]} only-brute="
                   f"{sorted(brute_moves(st) - set(mv))[:4]}")
                ck(len(mv) == len(set(mv)), "duplicate legal moves")
                ck(st.to_move == st.ply % 2, "to_move must track ply parity")
                # only the MOVER can ever complete a connection
                ck(G.connection_path(st, 1 - st.to_move) is None,
                   "the player NOT to move is already connected")
                mat = len(st.stones) + len(st.links)
                ck(mat > prev_mat or (st.swapped and mat == prev_mat),
                   "the stones+links monovariant must strictly increase")
                prev_mat = mat
                m = rng.choice(mv)
                before = (dict(st.stones), dict(st.links), st.to_move, st.ply,
                          st.winner, st.swapped, st.last)
                nxt = G.apply_move(st, m)
                # purity -- compare against a SNAPSHOT taken before the call.
                # (The old form, `st.stones == dict(st.stones)`, was vacuous.)
                ck((st.stones, st.links, st.to_move, st.ply, st.winner, st.swapped,
                    st.last) == before, "apply_move mutated the input state")
                st = nxt
                plies += 1
                ck(plies <= bound, f"ply bound {bound} exceeded at {size}x{size}")
            ck(st.winner is not None,
               f"a {size}x{size} game ended without a winner -- Quax is drawless, "
               f"so this is a bug, not a draw")
            ck(G.returns(st) in ([1.0, -1.0], [-1.0, 1.0]), "returns at terminal")
            ck(sum(G.returns(st)) == 0, "zero sum")
            ck(G.legal_moves(st) == [], "no moves after the game is over")
            # the winning chain really joins the winner's two edges
            path = G.connection_path(st, st.winner)
            ck(path, "the winner must have a chain")
            a, b = G._edges(st, st.winner)
            ck(path[0] in a and path[-1] in b, "the chain must span both edges")
            for x, y in zip(path, path[1:]):
                ck(y in G._neighbours(st, st.winner)[x], "chain steps must be links")


# --------------------------------------------------------------------------
# 9. serialize / deserialize (compared as STATES) and render bounds
# --------------------------------------------------------------------------
KEYS = {"size", "pie", "stones", "links", "to_move", "winner", "ply", "swapped",
        "last"}


def test_serialize_and_render(seed=3):
    rng = random.Random(seed)
    saw = {"swapped": 0, "links": 0, "winner": 0, "last_link": 0}
    for size in MAN["options"]["size"]["choices"]:
        for pie in ("on", "off"):
            st = G.initial_state(options={"size": size, "pie": pie})
            far = {(0, 0), (size - 1, size - 1), (0, size - 1), (size - 1, 0)}
            plies = 0
            while True:
                # cover EVERY shape of every serialized field: take the pie when
                # it is on (otherwise `swapped` is never True in this sweep and a
                # serialize() that drops it round-trips vacuously).
                if pie == "on" and "swap" in G.legal_moves(st):
                    st = G.apply_move(st, "swap")
                    ck(st.swapped, "swap taken")
                    d0 = G.serialize(st)
                    ck(d0["swapped"] is True, "serialize must emit swapped=True")
                    ck(G.deserialize(d0) == st, "round-trip after a swap")
                    saw["swapped"] += 1
                d = G.serialize(st)
                ck(set(d) == KEYS, f"serialize keys {set(d) ^ KEYS}")
                import json
                json.dumps(d)
                ck(G.deserialize(d) == st, "deserialize(serialize(s)) must equal s")
                spec = G.render(st)
                b = spec["board"]
                ck(b["width"] == size and b["height"] == size,
                   f"render must declare {size}x{size}")
                ids = {f"{c},{r}" for c in range(size) for r in range(size)}
                for p in spec["pieces"]:
                    ck(p["cell"] in ids, f"piece {p} outside the declared board")
                for h in spec["highlights"]:
                    ck(h["cell"] in ids, f"highlight {h} outside the board")
                for seg in b.get("overlay", []):
                    for pt in seg[:-1] if isinstance(seg[-1], str) else seg:
                        ck(0 <= pt[0] < size and 0 <= pt[1] < size,
                           f"overlay point {pt} outside the {size}x{size} board")
                ck(set(b["tints"]) <= ids, "tint outside the board")
                if st.links:
                    saw["links"] += 1
                    ck(len(b.get("overlay", [])) == len(st.links),
                       "one overlay segment per link")
                if st.last and ">" in st.last and st.winner is None:
                    saw["last_link"] += 1
                    ck(len(spec["highlights"]) == 2, "both ends of a link highlighted")
                if st.winner is not None:
                    ck(all(h["kind"] == "goal" for h in spec["highlights"])
                       and len(spec["highlights"]) >= 2,
                       "the winning chain must be highlighted")
                if G.is_terminal(st):
                    saw["winner"] += 1
                    break
                # steer toward the far corners first so the checks are not vacuous
                mv = G.legal_moves(st)
                pref = [m for m in mv if ">" not in m and m != "swap"
                        and tuple(int(x) for x in m.split(",")) in far]
                st = G.apply_move(st, rng.choice(pref or mv))
                plies += 1
            ck(far <= set(st.stones), f"far corners not reached at size {size}")
            ck(len(st.stones) > 0 and any(spec["pieces"] for _ in (0,)),
               "render had no pieces")
    # coverage of the sweep itself, so none of the above can go vacuous
    ck(saw["swapped"] == len(MAN["options"]["size"]["choices"]),
       f"the swap was not exercised at every size: {saw}")
    ck(saw["links"] > 500 and saw["last_link"] > 100 and saw["winner"] == 14,
       f"sweep coverage too thin: {saw}")
    # links at the extreme squares of every size, rendered
    for size in MAN["options"]["size"]["choices"]:
        for sq in ((0, 0), (size - 2, size - 2)):
            a, b2 = endpoints(sq, "/")
            st = QuaxState(size=size, pie=False, stones={a: BLACK, b2: BLACK},
                           links={sq: (BLACK, "/")}, to_move=WHITE, ply=3)
            ov = G.render(st)["board"]["overlay"]
            ck(len(ov) == 1, "one overlay segment per link")
            for pt in ov[0][:2]:
                ck(0 <= pt[0] < size and 0 <= pt[1] < size,
                   f"link overlay outside the {size}x{size} board")


def test_public_helpers():
    """`connection_path` is a public helper, so test it POSITIVELY on its own."""
    for size in (3, 5, 11):
        # a straight file joins seat 0's edges; a straight rank joins seat 1's
        col = {(2 % size, r): BLACK for r in range(size)}
        st = QuaxState(size=size, pie=False, stones=col)
        p = G.connection_path(st, BLACK)
        ck(p is not None and len(p) == size, f"vertical chain of {size}")
        ck(G.connection_path(st, WHITE) is None, "White owns no stones here")
        row = {(c, 1 % size): WHITE for c in range(size)}
        st2 = QuaxState(size=size, pie=False, stones=row)
        ck(G.connection_path(st2, WHITE) is not None, f"horizontal chain of {size}")
        ck(G.connection_path(st2, BLACK) is None, "Black owns no stones here")
        # a chain one cell short of an edge is NOT a connection
        short = {(2 % size, r): BLACK for r in range(size - 1)}
        ck(G.connection_path(QuaxState(size=size, pie=False, stones=short),
                             BLACK) is None, "an incomplete chain must not win")
        # a purely DIAGONAL chain with no links must not connect
        diagchain = {(i, i): BLACK for i in range(size)}
        ck(G.connection_path(QuaxState(size=size, pie=False, stones=diagchain),
                             BLACK) is None,
           "diagonal adjacency alone must NOT connect")
        # ... and it does once every link is bought
        links = {(i, i): (BLACK, "/") for i in range(size - 1)}
        ck(G.connection_path(QuaxState(size=size, pie=False, stones=diagchain,
                                       links=links), BLACK) is not None,
           "a fully linked diagonal chain must connect")
    # corners count for both edges: a single corner stone is on two edges
    st = QuaxState(size=5, pie=False, stones={(0, 0): BLACK})
    ck(G.connection_path(st, BLACK) is None, "one corner is not a connection")
    e0, e1 = G._edges(st, BLACK)
    ck((0, 0) in e0 or (0, 0) in e1, "the corner belongs to seat 0's edges")
    e0w, e1w = G._edges(st, WHITE)
    ck((0, 0) in e0w or (0, 0) in e1w, "the corner belongs to seat 1's edges too")


def test_illegal_moves_rejected():
    st = G.initial_state(options={"size": 5, "pie": "off"})
    st = G.apply_move(st, "1,1")          # Black
    st = G.apply_move(st, "3,3")          # White
    for bad, why in (("1,1", "occupied"), ("5,0", "off board"), ("-1,0", "off board"),
                     ("0,0>1,1", "no stone at 0,0"), ("2,2>3,3", "not both mine"),
                     ("swap", "pie off")):
        try:
            G.apply_move(st, bad)
            raise AssertionError(f"{bad} ({why}) was accepted")
        except AssertionError:
            raise
        except Exception:
            CHECKS_INC()
    # a link written the wrong way round is rejected (canonical form only)
    st = G.apply_move(G.apply_move(st, "2,2"), "0,4")
    ck("1,1>2,2" in G.legal_moves(st), "canonical link direction")
    try:
        G.apply_move(st, "2,2>1,1")
        raise AssertionError("a reversed link move was accepted")
    except AssertionError:
        raise
    except Exception:
        CHECKS_INC()


# --------------------------------------------------------------------------
# 10. Bill Taylor's 1992 diagram: a COMPLETE 4x4 game with a stated winner.
#
# The r.g.a post of 1992-12-18 (quoted verbatim on the designer's page under
# "RULES OF LINK") prints a finished game and states three facts about it.  It
# is a second, independent, outside-the-engine anchor for the seat/goal
# assignment -- and unlike the 2000-era figures it is already in THIS frame:
# "The winner is the first player to complete a path of stones between his own
# two edges of the board: north-south for black, east-west for white."
#
# The diagram, character-exact (cells at string indices 0,2,4,6; a bar glyph at
# index 1/3/5 sits on the midpoint of cols 1-2 / 2-3 / 3-4):
#
#     . O X .
#       /            <- one '/'  at index 3   => cols 2-3, between rows 1-2
#     X X O .
#       \ \          <- two '\' at indices 3,5 => cols 2-3 and 3-4, rows 2-3
#     . O X O
#                    <- nothing between rows 3-4
#     . O X .
#
#   "The diagram here shows a completed game on a 4x4 board.  Black has won with
#    a 4-counter 2-bar path.  Black has played 7 moves and white 6."
#
# X = Black is forced two independent ways: (a) 10 stones + (7+6) moves => 3
# bars, and only X can own 2 of them, since if O owned two bars they would have
# to sit in the cols 2-3 blocks and X would then have NO legal bar at all
# (6 moves impossible); (b) the printed bar glyph positions match (a) exactly.
# --------------------------------------------------------------------------
LINK1992_BLACK = [(2, 3), (0, 2), (1, 2), (2, 1), (2, 0)]
LINK1992_WHITE = [(1, 3), (2, 2), (1, 1), (3, 1), (1, 0)]
LINK1992_BLACK_BARS = [((1, 2), "/"), ((1, 1), "\\")]
LINK1992_WHITE_BARS = [((2, 1), "\\")]
# an alternating order that builds exactly that position, Black first and last
LINK1992_ORDER = [
    (BLACK, "2,0"), (WHITE, "1,0"), (BLACK, "2,1"), (WHITE, "1,1"),
    (BLACK, "1,2"), (WHITE, "2,2"), (BLACK, "0,2"), (WHITE, "3,1"),
    (BLACK, "2,3"), (WHITE, "1,3"),
    (BLACK, None), (WHITE, None), (BLACK, None),      # the three bars, below
]


def test_1992_completed_game():
    ck(len(LINK1992_BLACK) + len(LINK1992_BLACK_BARS) == 7,
       "the figure says Black played 7 moves")
    ck(len(LINK1992_WHITE) + len(LINK1992_WHITE_BARS) == 6,
       "the figure says White played 6 moves")
    bars = [link_move(*LINK1992_BLACK_BARS[1]), link_move(*LINK1992_WHITE_BARS[0]),
            link_move(*LINK1992_BLACK_BARS[0])]
    moves = [m for _, m in LINK1992_ORDER[:10]] + bars
    st = G.initial_state(options={"size": 4, "pie": "off"})
    for i, m in enumerate(moves):
        ck(G.current_player(st) == i % 2, f"ply {i}: wrong player to move")
        ck(not G.is_terminal(st), f"ply {i}: the game ended before move 13")
        ck(m in G.legal_moves(st), f"ply {i}: {m} is not legal")
        st = G.apply_move(st, m)
    ck(len(moves) == 13, "13 moves in the figure")
    # the three published facts
    ck(G.is_terminal(st), "the figure is a COMPLETED game")
    ck(st.winner == BLACK, f"the figure says BLACK won; engine says {st.winner}")
    path = G.connection_path(st, BLACK)
    ck(path is not None and len(path) == 4, f"a 4-counter path, got {path}")
    ck({c[1] for c in path} == {0, 1, 2, 3}, "the path spans rows 0..3 (north-south)")
    ck(G.connection_path(st, WHITE) is None, "White has NOT connected in the figure")
    # the board matches the figure cell for cell
    ck(st.stones == ({c: BLACK for c in LINK1992_BLACK}
                     | {c: WHITE for c in LINK1992_WHITE}), st.stones)
    ck(st.links == ({sq: (BLACK, d) for sq, d in LINK1992_BLACK_BARS}
                    | {sq: (WHITE, d) for sq, d in LINK1992_WHITE_BARS}), st.links)
    # the figure's PREMISE: White's two other diagonal pairs are blocked, and
    # blocked by BLACK's bars (so this figure cannot speak to same-colour
    # crossing -- igGameCenter's "empty rhombic cell" settles that instead)
    for sq, diag in (((1, 2), "\\"), ((1, 1), "/")):
        a, b = endpoints(sq, diag)
        ck(st.stones[a] == WHITE and st.stones[b] == WHITE, (sq, diag))
        ck(sq in {s for s, _ in LINK1992_BLACK_BARS}, "blocked by a BLACK bar")
        ck(link_move(sq, diag) not in G.legal_moves(replace(st, winner=None,
                                                            to_move=WHITE)),
           f"the crossing bar {sq}{diag} must be illegal")
    # captions + PAYOFF, pinned to this figure
    ck(G.render(st)["caption"].startswith("Black wins"), G.render(st)["caption"])
    ck("top-bottom" in G.render(st)["caption"], G.render(st)["caption"])
    ck(G.returns(st) == [1.0, -1.0],
       f"the figure's winner is Black = seat 0, so returns must be [+1,-1]; "
       f"got {G.returns(st)}")


# --------------------------------------------------------------------------
# 11. what every anchor above still failed to pin (found by mutation testing:
#     each of these mutants passed all 585,929 other checks in this file).
# --------------------------------------------------------------------------
def test_returns_pays_the_winner():
    """A flipped `returns()` inverts every stored match result, every rating
    update and the bot's objective while the board still reads correctly.  The
    Black case is pinned by the 1992 figure above; here is the White mirror plus
    a whole-game agreement sweep."""
    st = G.initial_state(options={"size": 3, "pie": "off"})
    for m in ("0,0", "0,1", "0,2", "1,1", "2,0", "2,1"):
        st = G.apply_move(st, m)
    ck(st.winner == WHITE, f"expected a White left-right win, got {st.winner}")
    ck(G.render(st)["caption"].startswith("White wins"), "caption premise")
    ck(G.returns(st) == [-1.0, 1.0], f"a White win must pay seat 1; got {G.returns(st)}")
    rng = random.Random(19921218)
    seen = set()
    for size in (3, 5, 7):
        for _ in range(20):
            s = G.initial_state(options={"size": size, "pie": "off"})
            while not G.is_terminal(s):
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            r = G.returns(s)
            ck(r[s.winner] == 1.0 and r[1 - s.winner] == -1.0,
               f"returns {r} does not pay the winner {s.winner}")
            ck(G.render(s)["caption"].startswith(("Black", "White")[s.winner] + " wins"),
               "the caption and the payoff must name the same winner")
            seen.add(s.winner)
    ck(seen == {BLACK, WHITE}, f"only {seen} ever won -- the sweep is one-sided")


def test_render_ownership():
    """Who owns which bar, and which seat aims at which pair of edges, must be
    READABLE ON THE BOARD.  Drawing a bar in the opponent's colour, and tinting
    seat 0's rows with seat 1's colour, each survived every other check here --
    the same class of defect as a caption naming the wrong player."""
    st = QuaxState(size=7, pie=False,
                   stones={(0, 0): BLACK, (1, 1): BLACK, (4, 4): WHITE, (5, 5): WHITE},
                   links={(0, 0): (BLACK, "/"), (4, 4): (WHITE, "/")},
                   to_move=BLACK, ply=6)
    ov = G.render(st)["board"]["overlay"]
    ck(len(ov) == 2, f"two links must give two overlay segments, got {ov}")
    colour_of = {}
    for seg in ov:
        (x1, y1), (x2, y2) = seg[0], seg[1]
        ck(abs(x1 - x2) == 1 and abs(y1 - y2) == 1, f"a bar must be a diagonal: {seg}")
        owner = st.stones[(x1, y1)]
        ck(st.stones[(x2, y2)] == owner, "both ends of a bar share an owner")
        colour_of[owner] = seg[-1]
    ck(set(colour_of) == {BLACK, WHITE}, colour_of)
    ck(colour_of[BLACK] != colour_of[WHITE],
       "the two seats' bars must be drawn in DIFFERENT colours")
    ck(colour_of[BLACK] == G.LINK_FILL[BLACK] and colour_of[WHITE] == G.LINK_FILL[WHITE],
       f"a bar must carry ITS OWN owner's colour, got {colour_of}")

    # web/src/colors.js: seat 0 is RED (#d23b3b), seat 1 BLUE (#3b6fd2).  So seat
    # 0's goal rows must be tinted red-dominant and seat 1's columns
    # blue-dominant -- igGameCenter's board colours each player's own pair in
    # that player's colour.
    def rgb(h):
        return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)

    for size in MAN["options"]["size"]["choices"]:
        t = G.render(QuaxState(size=size, pie=False))["board"]["tints"]
        n = size
        rows = {t[f"{c},{r}"] for r in (0, n - 1) for c in range(1, n - 1)}
        cols = {t[f"{c},{r}"] for c in (0, n - 1) for r in range(1, n - 1)}
        corners = {t[f"{c},{r}"] for c in (0, n - 1) for r in (0, n - 1)}
        ck(len(rows) == 1 and len(cols) == 1 and len(corners) == 1,
           f"size {size}: each edge class must be uniformly tinted: {rows} {cols}")
        ck(rows != cols, "seat 0's rows and seat 1's columns must be tinted differently")
        ck(corners.isdisjoint(rows | cols),
           "a corner belongs to BOTH edges and gets its own blend")
        rr, _, rb = rgb(next(iter(rows)))
        cr, _, cb = rgb(next(iter(cols)))
        ck(rr > rb, f"seat 0's top/bottom rows must be RED-dominant, got {rows}")
        ck(cb > cr, f"seat 1's left/right columns must be BLUE-dominant, got {cols}")


def CHECKS_INC():
    global CHECKS
    CHECKS += 1


def main():
    test_lemma_R()
    test_lemma_B()
    print("Lemma R + Lemma B: OK")
    test_connecting_example()
    print("designer's 'connecting example' figure (the crossing rule): OK")
    test_designer_puzzle()
    print("designer's published 3x3 puzzle solves to a first-player win: OK")
    test_race_figure()
    print("designer's 'Race to connections' figure pins the seats/edges/captions: OK")
    test_sample_games()
    test_move_notation()
    print("designer's three sample game records replay + pin the notation: OK")
    test_1992_completed_game()
    print("designer's 1992 COMPLETED 4x4 game (winner, path, move counts): OK")
    test_returns_pays_the_winner()
    test_render_ownership()
    print("the payoff sign and render ownership pinned: OK")
    t3 = test_lemma_A_exhaustive(3)
    t4 = test_lemma_A_exhaustive(4)
    print(f"Lemma A exhaustive: 3x3 {t3[0]} and 4x4 {t4[0]} full positions, "
          f"exactly one winner in each")
    for size, n in ((5, 4000), (7, 2000), (11, 800)):
        test_lemma_A_sampled(size, n, seed=size)
    print("Lemma A sampled at 5x5/7x7/11x11: OK")
    test_small_solves()
    print("3x3 exhaustive solve: first-player win, second-player win WITH the pie")
    n = test_transpose_lemma()
    print(f"transpose lemma (value + structure) over all {n} 3x3 states: OK")
    test_swap_is_a_transpose()
    print("the pie swap is a transpose+recolour: OK")
    test_public_helpers()
    test_illegal_moves_rejected()
    test_serialize_and_render()
    print("serialize round-trip (state equality) + render bounds at every size: OK")
    test_sweeps()
    print("random sweeps: move-gen cross-check, monovariant, invariants: OK")
    print(f"quax selftest: {CHECKS} checks passed")


if __name__ == "__main__":
    main()
