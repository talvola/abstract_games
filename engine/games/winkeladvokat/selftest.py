#!/usr/bin/env python3
"""Standalone correctness anchor for Winkeladvokat. Pure stdlib + agp only.

Run:  PYTHONPATH=. python3 games/winkeladvokat/selftest.py

Winkeladvokat has no published problem position, so the anchors are:

1. THE PRINTED BOARD. All 64 cell values and the two 2-player start squares are
   asserted against a grid transcribed cell by cell from photographs of three
   different physical copies of the 1986 Schmidt Spiele board — BGG images
   pic4768412 ("Game board") and pic431977 ("gameboard") in the gallery of
   https://boardgamegeek.com/boardgame/2473/winkeladvokat, and the front-cover
   photograph of *Abstract Games* issue 23 (Spring 2022). Four concentric rings
   2 / 4 / 8 / 16, blank colour-coded corner start squares; the blue and red
   start corners (the two used at 2 players) are diagonally opposite.
2. THE THREE RULES-SHEET FIGURES, replayed move for move through apply_move:
   Abb. 1 (the DETOUR/Winkelzug), Abb. 2 (Winkelzug -> article dropped on the
   Winkelfeld -> that article jumps the opposing article, which leaves the
   board) and Abb. 3 (an avocat blocked in all four directions = game over).
   Figures pixel-read from the Schmidt Spiele German sheet
   (spielanleitung.com/download.php4?id=2051) and the identical drawings in the
   French Schmidt/jeuxsoc translation.
3. APPLY_MOVE ACCEPTS EXACTLY legal_moves. Every 2- and 3-cell candidate string
   is applied on several positions (including mid-chain) and its acceptance
   compared with membership of legal_moves.
4. AN INDEPENDENT MOVE GENERATOR. A second, structurally different Winkelzug
   and jump enumerator (all-pairs filter with explicit segment listing, instead
   of the engine's directional walk) is compared move-for-move against
   legal_moves over random positions, including blocked legs.
5. INVARIANTS: 25+25 articles conserved (hand + board + captured), full random
   games terminate far below the ply cap, an honest DRAW really occurs, and
   serialize round-trips (including mid-chain).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                    # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)
M = sys.modules[type(G).__module__]

W = H = 8


def idx(c, r):
    return r * W + c


def cell(c, r):
    return f"{c},{r}"


# ---------------------------------------------------------------------------
# 1. The printed board
# ---------------------------------------------------------------------------
# Transcribed row by row from the board photographs, TOP row of the photo first.
# "." marks the four blank coloured start corners. Because the grid has full
# dihedral symmetry the photo's orientation does not matter, but for the record
# this is BGG pic4768412 as shot: green corner top-left, red top-right, blue
# bottom-left, yellow bottom-right.
PHOTO_ROWS = [
    ".  2  2  2  2  2  2  .",
    "2  4  4  4  4  4  4  2",
    "2  4  8  8  8  8  4  2",
    "2  4  8 16 16  8  4  2",
    "2  4  8 16 16  8  4  2",
    "2  4  8  8  8  8  4  2",
    "2  4  4  4  4  4  4  2",
    ".  2  2  2  2  2  2  .",
]


def test_board_values():
    assert len(PHOTO_ROWS) == H
    for photo_row, line in enumerate(PHOTO_ROWS):
        cells = line.split()
        assert len(cells) == W, line
        r = H - 1 - photo_row                    # engine row 0 is the BOTTOM row
        for c, tok in enumerate(cells):
            want = 0 if tok == "." else int(tok)
            got = M.VALUES[idx(c, r)]
            assert got == want, f"cell {cell(c, r)}: value {got}, photo says {want}"
    # the closed form used by the engine, and the resulting totals
    assert M.BOARD_TOTAL == 288
    counts = {}
    for v in M.VALUES:
        counts[v] = counts.get(v, 0) + 1
    assert counts == {0: 4, 2: 24, 4: 20, 8: 12, 16: 4}, counts
    # start squares: diagonally opposite corners, both blank
    assert M.START == (idx(0, 0), idx(7, 7))
    for i in M.START:
        assert i in M.CORNERS and M.VALUES[i] == 0
    s = G.initial_state()
    assert s.avocat == M.START
    assert s.hand == (25, 25) and s.taken == (0, 0)
    assert set(s.board) == {-1}
    print("  board: 64 printed values + start squares match the board photographs")


# ---------------------------------------------------------------------------
# helpers for building positions
# ---------------------------------------------------------------------------
def make(articles=(), avocat=((0, 0), (7, 7)), hand=(25, 25), taken=(0, 0),
         to_move=0, chain=None, ply=0):
    """articles = ((c, r, owner), ...)"""
    board = [-1] * (W * H)
    for c, r, owner in articles:
        board[idx(c, r)] = owner
    return M.WState(board=tuple(board),
                    avocat=tuple(idx(c, r) for c, r in avocat),
                    hand=tuple(hand), taken=tuple(taken), to_move=to_move,
                    chain=None if chain is None else idx(*chain), ply=ply)


# ---------------------------------------------------------------------------
# 2a. Abb. 1 — the DETOUR
# ---------------------------------------------------------------------------
def test_figure_1():
    """Abb. 1 / Figure 1: on an empty field the avocat runs two cells in a
    straight line, turns 90 degrees and runs two more; the turn cell is the
    Winkelfeld."""
    s = make(avocat=((1, 5), (7, 7)))
    assert not G.is_terminal(s)
    mv = "1,5>3,5>3,3"                            # right 2, turn, down 2
    assert mv in G.legal_moves(s)
    t = G.apply_move(s, mv)
    assert t.avocat[0] == idx(3, 3), "the avocat ends on the far end of leg two"
    assert t.board[idx(3, 5)] == 0, "an article is dropped on the Winkelfeld"
    assert t.board[idx(3, 3)] == -1 and t.board[idx(2, 5)] == -1
    assert t.hand == (24, 25) and t.to_move == 1 and t.chain is None
    assert M.VALUES[idx(3, 5)] == 8
    assert G.score(t, 0) == 8 and G.score(t, 1) == 0
    # a straight rook move with no turn is NOT a Winkelzug
    assert "1,5>3,5" not in G.legal_moves(s)
    assert not any(m.count(">") == 2 and m.split(">")[1] == m.split(">")[2]
                   for m in G.legal_moves(s)), "leg two must be at least one cell"
    for m in G.legal_moves(s):
        a, b, _c = m.split(">")
        assert a != b, "leg one must be at least one cell"
    print("  Abb. 1: the DETOUR places its article on the pivot cell")


# ---------------------------------------------------------------------------
# 2b. Abb. 2 — Winkelzug, article dropped, that article jumps the enemy article
# ---------------------------------------------------------------------------
def test_figure_2():
    """Abb. 2 / Figure 2, step for step:

      (1) 'Der Advokatenstein macht einen Winkelzug'  — one cell left, turn,
          one cell down (figure orientation);
      (2) 'Im Eckfeld wird ein Paragraphenstein plaziert';
      (3) 'Der Paragraphenstein hat einen gegnerischen Paragraphenstein (4)
          uebersprungen. Der uebersprungene Stein wird vom Spielplan genommen.'

    The figure's four drawn columns map to engine columns 1..4 and its four rows
    (top to bottom) to engine rows 5, 4, 3, 2 — so the figure's upward jump is a
    jump towards increasing engine row.
    """
    # (4) the opposing article, and seat 0's avocat at figure cell (C3, R2)
    s = make(articles=((3, 4, 1),), avocat=((4, 3), (7, 0)), to_move=0)

    detour = "4,3>3,3>3,2"                        # left 1, turn, down 1
    assert detour in G.legal_moves(s)
    s = G.apply_move(s, detour)
    assert s.avocat[0] == idx(3, 2)
    assert s.board[idx(3, 3)] == 0, "(2) article placed on the Winkelfeld"
    assert s.hand[0] == 24 and s.to_move == 1

    filler = "7,0>6,0>6,1"                        # seat 1 plays far from the figure
    assert filler in G.legal_moves(s)
    s = G.apply_move(s, filler)
    assert s.to_move == 0

    jump = "3,3>3,5"                              # (3) over the enemy article at 3,4
    assert jump in G.legal_moves(s)
    s = G.apply_move(s, jump)
    assert s.board[idx(3, 5)] == 0, "the jumping article lands beyond"
    assert s.board[idx(3, 4)] == -1, "'wird vom Spielplan genommen'"
    assert s.board[idx(3, 3)] == -1, "it left the Winkelfeld"
    assert s.taken == (1, 0), "captured articles are kept by the capturer"
    assert s.chain is None and s.to_move == 1, "no further jump -> turn over"
    assert s.hand[0] == 24, "a capture is a turn INSTEAD of a Winkelzug"
    assert G.score(s, 0) == M.VALUES[idx(3, 5)] + 1 == 9

    # diagonal jumps do not exist ('You may not jump diagonally' — Domino
    # Runners; Abb. 2 shows an orthogonal jump)
    d = make(articles=((3, 3, 0), (4, 4, 1)), avocat=((0, 7), (7, 0)))
    assert not any(m.startswith("3,3>") for m in G.legal_moves(d))
    # ... and an article may not jump its OWN colour
    d = make(articles=((3, 3, 0), (3, 4, 0)), avocat=((0, 7), (7, 0)))
    assert "3,3>3,5" not in G.legal_moves(d)
    # ... nor jump over, or land on, an avocat
    d = make(articles=((3, 3, 0),), avocat=((0, 7), (3, 4)))
    assert "3,3>3,5" not in G.legal_moves(d)
    d = make(articles=((3, 3, 0), (3, 4, 1)), avocat=((3, 5), (7, 0)))
    assert "3,3>3,5" not in G.legal_moves(d)
    print("  Abb. 2: Winkelzug -> article on the Winkelfeld -> orthogonal jump")


# ---------------------------------------------------------------------------
# 2c. Abb. 3 — the avocat is blocked, the game is over
# ---------------------------------------------------------------------------
def test_figure_3():
    """Abb. 3 / Figure 3: 'Der Advokatenstein ist in alle vier moeglichen
    Bewegungsrichtungen blockiert und somit eingeschlossen.'"""
    blockers = ((3, 4, 1), (3, 2, 0), (2, 3, 1), (4, 3, 0))
    s = make(articles=blockers, avocat=((3, 3), (7, 0)), to_move=0)
    assert s.hand[0] == 25, "not the empty-hand rule — the avocat is hemmed in"
    assert G.is_terminal(s)
    assert G.legal_moves(s) == []
    # freeing any one of the four un-blocks it
    for skip in range(4):
        t = make(articles=tuple(b for i, b in enumerate(blockers) if i != skip),
                 avocat=((3, 3), (7, 0)), to_move=0)
        assert not G.is_terminal(t) and G.legal_moves(t)
    # the same avocat is fine while it is the OPPONENT's turn (the end condition
    # is evaluated for the player to move)
    t = make(articles=blockers, avocat=((3, 3), (7, 0)), to_move=1)
    assert not G.is_terminal(t)
    # the board edge blocks exactly like an article (French sheet: "entre des
    # articles et le bord du plateau de jeu")
    e = make(articles=((1, 0, 1), (0, 1, 1)), avocat=((0, 0), (7, 7)), to_move=0)
    assert G.is_terminal(e)
    # an empty hand also ends it: placing an article is mandatory in a Winkelzug
    h = make(avocat=((3, 3), (7, 0)), hand=(0, 25), to_move=0)
    assert G.is_terminal(h) and G.legal_moves(h) == []
    assert not G.is_terminal(make(avocat=((3, 3), (7, 0)), hand=(1, 25), to_move=0))
    print("  Abb. 3: blocked avocat (articles, board edge, empty hand) ends the game")


# ---------------------------------------------------------------------------
# 3. Independent move generators
# ---------------------------------------------------------------------------
def brute_detours(s, seat):
    """Second implementation: filter ALL (pivot, end) pairs, listing each leg's
    cells explicitly. Deliberately unlike the engine's directional walk."""
    if s.hand[seat] <= 0:
        return set()
    start = s.avocat[seat]
    sc, sr = start % W, start // W
    occ = set(s.avocat) | {i for i in range(W * H) if s.board[i] != -1}

    def free(c, r):
        return 0 <= c < W and 0 <= r < H and idx(c, r) not in occ

    def span(a, b):
        step = 1 if b > a else -1
        return list(range(a + step, b + step, step))

    out = set()
    for pc in range(W):
        for pr in range(H):
            if (pc == sc) == (pr == sr):          # need EXACTLY one axis to change
                continue
            leg1 = ([(c, sr) for c in span(sc, pc)] if pr == sr
                    else [(sc, r) for r in span(sr, pr)])
            if not all(free(c, r) for c, r in leg1):
                continue
            for ec in range(W):
                for er in range(H):
                    if pr == sr:                  # leg one horizontal -> leg two vertical
                        if ec != pc or er == pr:
                            continue
                        leg2 = [(pc, r) for r in span(pr, er)]
                    else:                         # leg one vertical -> leg two horizontal
                        if er != pr or ec == pc:
                            continue
                        leg2 = [(c, pr) for c in span(pc, ec)]
                    if all(free(c, r) for c, r in leg2):
                        out.add(f"{sc},{sr}>{pc},{pr}>{ec},{er}")
    return out


def brute_jumps(s, seat):
    """Second implementation of the first jump of a capture."""
    occ = set(s.avocat) | {i for i in range(W * H) if s.board[i] != -1}
    out = set()
    for c in range(W):
        for r in range(H):
            if s.board[idx(c, r)] != seat:
                continue
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                oc, orr, lc, lr = c + dc, r + dr, c + 2 * dc, r + 2 * dr
                if not (0 <= lc < W and 0 <= lr < H):
                    continue
                if s.board[idx(oc, orr)] != 1 - seat:
                    continue
                if idx(lc, lr) in occ:
                    continue
                out.add(f"{c},{r}>{lc},{lr}")
    return out


def test_movegen_vs_brute_force():
    rng = random.Random(20260725)
    checked = 0
    # (a) the two empty-board start corners, exhaustively
    for start in ((0, 0), (7, 7), (3, 4)):
        s = make(avocat=(start, (7, 0) if start != (7, 0) else (0, 7)))
        assert set(G.legal_moves(s)) == brute_detours(s, 0)
        checked += 1
    # (b) random positions: articles, both avocats, blocked legs
    for _ in range(400):
        n = rng.randrange(0, 30)
        occupied = rng.sample(range(W * H), n + 2)
        av0, av1 = occupied[0], occupied[1]
        arts = tuple((i % W, i // W, rng.randrange(2)) for i in occupied[2:])
        seat = rng.randrange(2)
        s = make(articles=arts, avocat=((av0 % W, av0 // W), (av1 % W, av1 // W)),
                 hand=(rng.choice([0, 1, 25]), rng.choice([0, 1, 25])),
                 to_move=seat)
        want = brute_detours(s, seat) | brute_jumps(s, seat)
        got = set(G.legal_moves(s))
        assert len(got) == len(G.legal_moves(s)), "legal_moves must not repeat"
        if G.is_terminal(s):
            assert not brute_detours(s, seat), "terminal <=> no Winkelzug"
            assert got == set()
        else:
            assert got == want, (sorted(got - want), sorted(want - got))
        checked += 1
    # (c) both legs must run over EMPTY cells — an article one cell along a leg
    #     truncates it exactly there
    s = make(articles=((3, 0, 1),), avocat=((0, 0), (7, 7)))
    for m in G.legal_moves(s):
        a, b, c = m.split(">")
        pc, pr = (int(x) for x in b.split(","))
        assert not (pr == 0 and pc >= 3), f"leg one ran through the blocker: {m}"
    assert set(G.legal_moves(s)) == brute_detours(s, 0)
    print(f"  move generation: {checked} positions match an independent enumerator")


# ---------------------------------------------------------------------------
# 4. Capture chains (optional, one turn, several moves)
# ---------------------------------------------------------------------------
def test_apply_move_accepts_exactly_the_legal_moves():
    """apply_move must reject every ill-formed move, not just the obvious ones:
    a leg that crosses an occupied cell, a second leg that does not turn 90
    degrees, a jump from the wrong stone mid-chain, 'done' with no chain.
    Brute-forces EVERY 2- and 3-cell candidate string on a few positions and
    checks acceptance matches legal_moves exactly."""
    positions = [
        G.initial_state(),
        make(articles=((2, 0, 1), (2, 1, 0), (0, 2, 1), (5, 5, 1)),
             avocat=((0, 0), (7, 7)), to_move=0),
    ]
    # ... and a mid-chain position (only the chaining stone may jump on)
    mid = G.apply_move(make(articles=((1, 1, 0), (2, 1, 1), (4, 1, 1), (5, 5, 0),
                                      (5, 6, 1)),
                            avocat=((0, 7), (7, 7)), to_move=0), "1,1>3,1")
    positions.append(mid)
    ids = [M.cid(i) for i in range(W * H)]
    tried = 0
    for s in positions:
        legal = set(G.legal_moves(s))
        cands = [f"{a}>{b}" for a in ids for b in ids]
        cands += [f"{a}>{b}>{ids[0]}" for a in ids for b in ids]
        cands += [f"0,0>{b}>{c}" for b in ids for c in ids]
        cands += [f"{M.cid(s.avocat[s.to_move])}>{b}>{c}" for b in ids for c in ids]
        cands.append("done")
        for mv in cands:
            try:
                G.apply_move(s, mv)
                accepted = True
            except ValueError:
                accepted = False
            assert accepted == (mv in legal), f"apply_move({mv!r}) -> {accepted}"
            tried += 1
    print(f"  apply_move accepts exactly legal_moves ({tried} candidate strings)")


def test_capture_chain():
    s = make(articles=((1, 1, 0), (2, 1, 1), (4, 1, 1)),
             avocat=((0, 7), (7, 7)), to_move=0)
    assert "done" not in G.legal_moves(s), "nothing to stop before a chain starts"
    assert "1,1>3,1" in G.legal_moves(s)
    t = G.apply_move(s, "1,1>3,1")
    assert t.to_move == 0 and t.chain == idx(3, 1), "the turn continues"
    assert t.taken == (1, 0) and t.board[idx(2, 1)] == -1
    assert sorted(G.legal_moves(t)) == sorted(["3,1>5,1", "done"])
    # stopping is legal — "Auch Kettensprünge sind erlaubt", not compulsory
    stop = G.apply_move(t, "done")
    assert stop.to_move == 1 and stop.chain is None and stop.taken == (1, 0)
    assert stop.board[idx(4, 1)] == 1, "the second enemy article survives"
    # ... and so is carrying on
    go = G.apply_move(t, "3,1>5,1")
    assert go.taken == (2, 0) and go.board[idx(4, 1)] == -1
    assert go.board[idx(5, 1)] == 0 and go.chain is None and go.to_move == 1
    assert go.hand == (25, 25), "captures never spend an article from the hand"
    # a capture never moves the avocat and never places an article
    assert go.avocat == s.avocat
    print("  capture chains: optional, one turn, jumped articles removed at once")


# ---------------------------------------------------------------------------
# 5. Scoring, honest draw, serialization, invariants
# ---------------------------------------------------------------------------
def test_scoring():
    # hand-computed: seat 0 = 2 + 8 + 16 + 3 taken = 29; seat 1 = 2 + 16 + 4 = 22
    s = make(articles=((0, 1, 0), (2, 2, 0), (3, 3, 0),
                       (7, 4, 1), (4, 4, 1), (1, 1, 1)),
             taken=(3, 0))
    assert (M.VALUES[idx(0, 1)], M.VALUES[idx(2, 2)], M.VALUES[idx(3, 3)]) == (2, 8, 16)
    assert (M.VALUES[idx(7, 4)], M.VALUES[idx(4, 4)], M.VALUES[idx(1, 1)]) == (2, 16, 4)
    assert G.score(s, 0) == 29 and G.score(s, 1) == 22
    # an article pivoted onto a blank corner scores nothing
    z = make(articles=((7, 0, 0),))
    assert M.VALUES[idx(7, 0)] == 0 and G.score(z, 0) == 0

    # an equal total is an honest DRAW, never a fabricated tie-break
    tied = make(articles=((3, 3, 0),                               # seat 0: 16
                          (1, 0, 1), (0, 1, 1),                    # seat 1: 2 + 2 ...
                          (2, 2, 1), (1, 1, 1)),                   # ... + 8 + 4 = 16
                avocat=((0, 0), (7, 7)), to_move=0)
    assert G.is_terminal(tied), "seat 0's avocat is boxed into its home corner"
    assert G.score(tied, 0) == G.score(tied, 1) == 16
    assert G.returns(tied) == [0.0, 0.0]
    print("  scoring: hand-computed totals, blank corners score 0, ties draw")


def test_random_games():
    rng = random.Random(7)
    longest, draws, results = 0, 0, {(1.0, -1.0): 0, (-1.0, 1.0): 0}
    for seed in range(240):
        r = random.Random(seed)
        s = G.initial_state()
        plies = 0
        while not G.is_terminal(s):
            moves = G.legal_moves(s)
            assert moves, "legal_moves is empty on a non-terminal state"
            # article conservation, every ply
            for p in (0, 1):
                on_board = sum(1 for x in s.board if x == p)
                assert on_board + s.hand[p] + s.taken[1 - p] == 25
            s = G.apply_move(s, r.choice(moves))
            plies += 1
            assert plies < M.PLY_CAP
        longest = max(longest, plies)
        ret = G.returns(s)
        assert sorted(ret) in ([-1.0, 1.0], [0.0, 0.0]) and len(ret) == 2
        if ret == [0.0, 0.0]:
            draws += 1
        else:
            results[tuple(ret)] += 1
        # totals still add up at the terminal
        for p in (0, 1):
            on_board = sum(1 for x in s.board if x == p)
            assert on_board + s.hand[p] + s.taken[1 - p] == 25
        # terminal really means "the player to move cannot move the avocat"
        assert not G._any_detour(s, s.to_move)
    assert draws > 0, "a genuine tie must be reachable"
    assert results[(1.0, -1.0)] > 0 and results[(-1.0, 1.0)] > 0
    # the ply cap is a safety net, not a game rule: every turn either spends an
    # article (at most 50) or removes one that was spent (at most 50), plus at
    # most one 'done' per capture turn -> under 200 plies, cap is 400.
    assert longest < M.PLY_CAP // 2, longest
    print(f"  240 random games: max {longest} plies (cap {M.PLY_CAP}), "
          f"{draws} draws, both seats win")
    return rng


def test_serialize_and_render():
    s = G.initial_state()
    for mv in ("0,0>2,0>2,3", "7,7>5,7>5,4", "2,3>4,3>4,6"):
        assert mv in G.legal_moves(s)
        s = G.apply_move(s, mv)
    for st in (G.initial_state(), s,
               make(articles=((1, 1, 0), (2, 1, 1)), chain=(1, 1), to_move=0)):
        d = G.serialize(st)
        import json
        json.dumps(d)
        assert G.serialize(G.deserialize(d)) == d
        spec = G.render(st)
        json.dumps(spec)
        b = spec["board"]
        assert b["type"] == "square" and b["width"] == 8 and b["height"] == 8
        assert len(b["labels"]) == 60 and len(b["tints"]) == 64
        assert b["labels"]["3,3"] == "16" and b["labels"]["0,1"] == "2"
        assert "0,0" not in b["labels"] and "7,7" not in b["labels"]
        avocats = [p for p in spec["pieces"] if p.get("glyph") == "A"]
        assert len(avocats) == 2
        assert {p["cell"] for p in avocats} == {M.cid(i) for i in st.avocat}
        # articles are plain discs; no piece shares a cell with another
        assert len({p["cell"] for p in spec["pieces"]}) == len(spec["pieces"])
    # the bot heuristic must return one payoff PER SEAT (SPEC.md)
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9
    assert G.describe_move(G.initial_state(), "0,0>2,0>2,3") == "A a1-c1-c4 §c1(2)"
    print("  serialize round-trips, RenderSpec well-formed, heuristic per-seat")


def main():
    print(f"== selftest {MAN['uid']} v{MAN['version']} ==")
    test_board_values()
    test_figure_1()
    test_figure_2()
    test_figure_3()
    test_movegen_vs_brute_force()
    test_apply_move_accepts_exactly_the_legal_moves()
    test_capture_chain()
    test_scoring()
    test_random_games()
    test_serialize_and_render()
    print("OK")


if __name__ == "__main__":
    main()
