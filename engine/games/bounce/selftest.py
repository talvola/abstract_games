#!/usr/bin/env python3
"""Bounce — correctness anchors.  Pure stdlib (agp + this package only).

Anchors
  A. Figure 1 of the official rule sheet, transcribed cell-by-cell from the
     PDF's vector art, equals `setup_board(8)` exactly (30 + 30, corners empty).
  B. Figure 2 ("Blue has won") — Blue is one group of 30, Red is two groups
     [22, 8], so the OBJECT rule fires for Blue and not for Red.
  C. Figure 3 — the sheet's own worked example: the marked Red checker is in a
     group of size 11 before its move and 20 after.  Both numbers are asserted,
     and the move is required to be legal.
  D. Opening move counts 32 / 60 / 96 on 6x6 / 8x8 / 10x10 (the 8x8 count of 60
     is confirmed by AbstractPlay's independent implementation), with every
     opening destination one of the two corners whose neighbours are friendly.
  E. `_raw_moves` agrees exactly with a naive brute-force reference over swept
     random positions, on BOTH seats.
  F. The termination monovariant: the mover's DESCENDING group-size multiset
     increases strictly lexicographically on every move (so the game is finite
     with no ply cap and no repetition rule); removals drop material by one.
  G. The forced-removal spiral, reached through apply_move: a player with no
     legal move removes a checker, and a player reduced to one checker wins.
     No player ever reaches zero checkers.
  H. serialize/deserialize compare as STATE OBJECTS with an exact key set,
     swept over whole games.
  I. render() declares the right board for EVERY size option, checked on
     positions reached through apply_move that occupy all four far corners.
  J. Seat conjugation: (vertical flip + colour swap) is an automorphism of the
     initial position, and the engine commutes with it — this is what gives
     seat 1 real assertions.
  K. heuristic shape, range, zero-sum, terminal agreement and DIRECTION.
  L. Helpers that are OFF the legality path (`group_containing`, `group_sizes`,
     `algebraic`, `describe_move`) are checked against the group labelling that
     move generation actually uses.
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

MAN, GAME = load_from_dir(Path(__file__).resolve().parent)
G = sys.modules[type(GAME).__module__]   # the LIVE module object (synthetic name)
ORTH = G.ORTH


def fail(msg):
    raise AssertionError(msg)


def check(cond, msg):
    if not cond:
        fail(msg)


# --------------------------------------------------------------------------
# The three figures of https://marksteeregames.com/Bounce_rules.pdf, rows
# written TOP-DOWN as printed.  Our cell ids put row 0 at the BOTTOM, so
# printed row `rt` is our row `n-1-rt`.
FIG1 = [
    ". B R B R B R .",
    "B R B R B R B R",
    "R B R B R B R B",
    "B R B R B R B R",
    "R B R B R B R B",
    "B R B R B R B R",
    "R B R B R B R B",
    ". R B R B R B .",
]
FIG2 = [
    "R R R R R R R B",
    ". B B R B B B B",
    "B B B B B B B B",
    "B B B B B R B R",
    "B B R B R R R R",
    "B R R R R R R R",
    "B B R R R R R R",
    "B B B R R . . .",
]
FIG3 = [
    "R R R R R R R R",
    ". R B R B B B R",   # (col 7) = the checker marked with the YELLOW dot
    "B B B B B B B B",
    "B B B B B R B R",
    "B B R B R R R R",
    "B R R R R R R R",
    "B B R R R B R .",
    "B B B R . B B .",   # (col 4) = the square marked with the GREEN dot
]
FIG3_FROM = (7, 8 - 1 - 1)   # yellow dot, printed row 1
FIG3_TO = (4, 8 - 1 - 7)     # green dot,  printed row 7


def parse_fig(fig, n=8):
    board = {}
    for rt, line in enumerate(fig):
        toks = line.split()
        check(len(toks) == n, f"figure row {rt} has {len(toks)} cells")
        for c, t in enumerate(toks):
            if t == "R":
                board[(c, n - 1 - rt)] = 0
            elif t == "B":
                board[(c, n - 1 - rt)] = 1
            else:
                check(t == ".", f"bad token {t!r}")
    return board


# --------------------------------------------------------------------------
# An independent, deliberately naive reference implementation of the rules.
def ref_groups(board, seat):
    seen, out = set(), []
    for p in board:
        if board[p] != seat or p in seen:
            continue
        comp, stack = {p}, [p]
        seen.add(p)
        while stack:
            c, r = stack.pop()
            for dc, dr in ORTH:
                q = (c + dc, r + dr)
                if q not in comp and board.get(q) == seat:
                    comp.add(q)
                    seen.add(q)
                    stack.append(q)
        out.append(comp)
    return out


def ref_group_of(board, cell, seat):
    for comp in ref_groups(board, seat):
        if cell in comp:
            return comp
    return set()


def ref_moves(board, n, seat):
    """Brute force: for every (own checker, empty square), rebuild the whole
    board from scratch and flood-fill.  No incremental cleverness at all."""
    mine = sorted(p for p in board if board[p] == seat)
    empties = [(c, r) for r in range(n) for c in range(n) if (c, r) not in board]
    out = []
    for frm in mine:
        before = len(ref_group_of(board, frm, seat))
        for to in empties:
            nb = dict(board)
            del nb[frm]
            nb[to] = seat
            if len(ref_group_of(nb, to, seat)) > before:
                out.append(f"{frm[0]},{frm[1]}>{to[0]},{to[1]}")
    if not out:
        out = [f"{p[0]},{p[1]}" for p in mine]
    return out


def flip_cell(p, n):
    return (p[0], n - 1 - p[1])


def flip_move(m, n):
    if ">" in m:
        a, b = (G.parse_cell(x) for x in m.split(">"))
        return f"{G.cell_id(flip_cell(a, n))}>{G.cell_id(flip_cell(b, n))}"
    return G.cell_id(flip_cell(G.parse_cell(m), n))


def flip_state(s):
    return G.BounceState(
        n=s.n,
        board={flip_cell(p, s.n): 1 - o for p, o in s.board.items()},
        to_move=1 - s.to_move,
        winner=None if s.winner is None else 1 - s.winner,
        ply=s.ply,
    )


# ==========================================================================
def test_figure1_setup():
    b = parse_fig(FIG1)
    check(b == G.setup_board(8), "Figure 1 != setup_board(8)")
    check(sum(1 for v in b.values() if v == 0) == 30, "Figure 1 red count")
    check(sum(1 for v in b.values() if v == 1) == 30, "Figure 1 blue count")
    for n in (6, 8, 10):
        bb = G.setup_board(n)
        corners = [(0, 0), (0, n - 1), (n - 1, 0), (n - 1, n - 1)]
        for c in corners:
            check(c not in bb, f"corner {c} occupied on {n}x{n}")
        check(len(bb) == n * n - 4, f"{n}x{n} checker total")
        for seat in (0, 1):
            check(sum(1 for v in bb.values() if v == seat) == n * n // 2 - 2,
                  f"{n}x{n} seat {seat} count")
        # a checkerboard: no two same-colour checkers orthogonally adjacent
        for (c, r), o in bb.items():
            for dc, dr in ORTH:
                check(bb.get((c + dc, r + dr)) != o,
                      f"{n}x{n} setup is not a checkerboard at {c},{r}")


def test_figure2_object():
    b = parse_fig(FIG2)
    check(sorted(map(len, ref_groups(b, 1)), reverse=True) == [30],
          "Figure 2: Blue should be a single group of 30")
    check(sorted(map(len, ref_groups(b, 0)), reverse=True) == [22, 8],
          "Figure 2: Red should be two groups [22, 8]")
    check(G.Bounce._unified(b, 1) and not G.Bounce._unified(b, 0),
          "Figure 2: the OBJECT rule must fire for Blue only")


def test_figure3_worked_example():
    b = parse_fig(FIG3)
    check(b.get(FIG3_FROM) == 0, "Figure 3: the yellow-dotted checker is Red")
    check(FIG3_TO not in b, "Figure 3: the green-dotted square is empty")
    before = len(ref_group_of(b, FIG3_FROM, 0))
    nb = dict(b)
    del nb[FIG3_FROM]
    nb[FIG3_TO] = 0
    after = len(ref_group_of(nb, FIG3_TO, 0))
    check(before == 11, f"Figure 3: group size before the move is {before}, sheet says 11")
    check(after == 20, f"Figure 3: group size after the move is {after}, sheet says 20")
    s = G.BounceState(n=8, board=b, to_move=0)
    mv = f"{G.cell_id(FIG3_FROM)}>{G.cell_id(FIG3_TO)}"
    check(mv in GAME.legal_moves(s), "Figure 3: the sheet's move must be legal")
    check(GAME.describe_move(s, mv) == "h7-e1 (11→20)",
          f"Figure 3 notation: {GAME.describe_move(s, mv)!r}")
    # and neither side has already won in this position
    check(not G.Bounce._unified(b, 0) and not G.Bounce._unified(b, 1),
          "Figure 3 should be a live position")


def test_opening_counts():
    for n, want in ((6, 32), (8, 60), (10, 96)):
        s = GAME.initial_state({"size": n})
        mv = GAME.legal_moves(s)
        check(len(mv) == want, f"{n}x{n} opening moves {len(mv)} != {want}")
        # every opening move is a real move (no removals) landing on a corner
        dests = {m.split(">")[1] for m in mv}
        check(all(">" in m for m in mv), "opening turn should have real moves")
        check(dests == {"0,0", f"{n - 1},{n - 1}"},
              f"{n}x{n} opening destinations {sorted(dests)}")
        check(len(mv) == (n * n // 2 - 2) * 2, "every checker x both corners")


def test_movegen_vs_reference():
    rng = random.Random(20230801)
    positions = 0
    for size in (6, 8):
        for _ in range(12):
            s = GAME.initial_state({"size": size})
            while not GAME.is_terminal(s):
                for seat in (0, 1):
                    probe = G.BounceState(n=s.n, board=s.board, to_move=seat)
                    got = sorted(GAME.legal_moves(probe))
                    want = sorted(ref_moves(s.board, s.n, seat))
                    check(got == want,
                          f"movegen != reference (size {size}, seat {seat}): "
                          f"extra {sorted(set(got) - set(want))[:4]} "
                          f"missing {sorted(set(want) - set(got))[:4]}")
                    positions += 1
                s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
    check(positions > 900, f"movegen sweep only covered {positions} positions")
    return positions


def test_removal_rule():
    """Removals are offered EXACTLY when no real move exists, and then the
    legal set is precisely the mover's own checkers."""
    rng = random.Random(5)
    seen_removal = 0
    for _ in range(60):
        s = GAME.initial_state({"size": 8})
        while not GAME.is_terminal(s):
            mv = GAME.legal_moves(s)
            real = [m for m in mv if ">" in m]
            rem = [m for m in mv if ">" not in m]
            check(not (real and rem), "moves and removals must never coexist")
            check(bool(mv), "legal_moves must never be empty on a live state")
            if rem:
                seen_removal += 1
                mine = {G.cell_id(p) for p, o in s.board.items() if o == s.to_move}
                check(set(rem) == mine, "removal set must be exactly own checkers")
                check(not ref_moves(s.board, s.n, s.to_move)[0].count(">"),
                      "reference also says: no real move")
            s = GAME.apply_move(s, rng.choice(mv))
    check(seen_removal > 0, "random play never exercised CHECKER REMOVAL")
    return seen_removal


def test_termination_monovariant():
    """The mover's descending group-size multiset increases strictly
    lexicographically on every move — the proof that Bounce terminates without
    a ply cap or a repetition rule.  Also: no state ever repeats within a game
    for the same player to move, which the multiset argument implies."""
    rng = random.Random(99)
    longest = 0
    for size in (6, 8, 10):
        for _ in range(8 if size == 10 else 20):
            s = GAME.initial_state({"size": size})
            seen = set()
            while not GAME.is_terminal(s):
                key = (s.to_move, tuple(sorted(s.board.items())))
                check(key not in seen, "position repeated with the same player to move")
                seen.add(key)
                seat = s.to_move
                before = G.group_sizes(s.board, seat)
                m = rng.choice(GAME.legal_moves(s))
                s2 = GAME.apply_move(s, m)
                after = G.group_sizes(s2.board, seat)
                if ">" in m:
                    check(sum(after) == sum(before), "a move must not change material")
                    check(after > before,
                          f"monovariant broken: {before} -> {after} via {m}")
                else:
                    check(sum(after) == sum(before) - 1, "a removal must drop one checker")
                s = s2
                check(s.ply < 4000, "game did not terminate")
            longest = max(longest, s.ply)
    return longest


def test_win_is_the_movers_and_reachable():
    rng = random.Random(4242)
    wins = [0, 0]
    for _ in range(120):
        s = GAME.initial_state({"size": 8})
        prev = None
        while not GAME.is_terminal(s):
            prev = s.to_move
            s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
        check(s.winner == prev, "the winner must be the player who just moved")
        check(G.Bounce._unified(s.board, s.winner), "the winner must be unified")
        check(GAME.returns(s) == ([1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]),
              "returns must match the winner")
        check(GAME.legal_moves(s) == [], "a finished game has no legal moves")
        wins[s.winner] += 1
    check(wins[0] > 20 and wins[1] > 20, f"both seats must be able to win: {wins}")
    return wins


def test_removal_spiral_and_single_checker_win():
    """Random play never drives a player below ~27 checkers, so the deep end of
    the CHECKER REMOVAL rule needs a constructed position — reached through
    apply_move, because `winner` is a stored event, not a board predicate."""
    n = 6
    # (i) Three Red checkers — an adjacent pair plus a lone one — with every
    # square that could grow either unit occupied by Blue.  A lone checker can
    # only reach a group of 2, which is not > 2 for a pair-member and not
    # reachable at all for the singleton, so Red has NO legal move.
    board = {(0, 0): 0, (0, 1): 0, (5, 5): 0,
             (1, 0): 1, (1, 1): 1, (0, 2): 1, (4, 5): 1, (5, 4): 1}
    s = G.BounceState(n=n, board=board, to_move=0)
    mv = GAME.legal_moves(s)
    check(all(">" not in m for m in mv), f"Red should be forced to remove: {mv[:4]}")
    check(set(mv) == {"0,0", "0,1", "5,5"}, f"removal choices {sorted(mv)}")
    check(not GAME.is_terminal(s), "not terminal before the removal")
    check(not G.Bounce._unified(board, 1), "Blue must not already be unified")
    # Removing the odd checker out unifies Red and wins on the spot...
    won = GAME.apply_move(s, "5,5")
    check(GAME.is_terminal(won) and won.winner == 0,
          "removing the stray checker unifies Red and wins")
    check(GAME.returns(won) == [1.0, -1.0], "returns after a removal win")
    # ...but removing a pair-member does not; the game goes on with Blue to move.
    on = GAME.apply_move(s, "0,0")
    check(not GAME.is_terminal(on) and on.winner is None,
          "removing a pair-member leaves Red in two groups")
    check(on.to_move == 1 and on.last_kind == "remove", "turn passes after a removal")

    # (ii) The deep end: two separated checkers with every joining square
    # blocked => forced removal => ONE checker => one group => a win.
    for seat in (0, 1):
        b2 = {(0, 0): seat, (5, 5): seat,
              (1, 0): 1 - seat, (0, 1): 1 - seat,
              (4, 5): 1 - seat, (5, 4): 1 - seat}
        s2 = G.BounceState(n=n, board=b2, to_move=seat)
        mv2 = GAME.legal_moves(s2)
        check(set(mv2) == {"0,0", "5,5"}, f"seat {seat} forced removal {sorted(mv2)}")
        s3 = GAME.apply_move(s2, "5,5")
        check(GAME.is_terminal(s3) and s3.winner == seat,
              f"seat {seat} must win once reduced to a single checker")
        # A player therefore never reaches zero checkers: the removal that would
        # take them from 1 to 0 can never happen, because at 1 they already won.
        check(sum(1 for v in s3.board.values() if v == seat) == 1,
              "the winner holds exactly one checker")

    # (iii) The zero-checker ruling itself, pinned directly.  It is unreachable
    # in play (proved above), so nothing else in this file can see it — but it
    # is a real semantic choice and it matches AbstractPlay: no checkers means
    # no group, which is NOT "all your checkers in one group".
    check(not G.Bounce._unified({}, 0), "an empty board is not one group")
    check(not G.Bounce._unified({(0, 0): 1, (3, 3): 1}, 0),
          "a seat with no checkers of its own is not unified")
    check(G.Bounce._unified({(0, 0): 1, (3, 3): 1}, 1) is False,
          "two separated checkers are not one group")
    check(G.Bounce._unified({(0, 0): 0, (0, 1): 0, (3, 3): 1}, 0),
          "an adjacent pair is one group")
    # ...and the exhaustive statement of the reachability argument: over every
    # forced-removal turn seen in random play, the mover always held >= 2
    # checkers, so a removal never empties a seat.
    rng = random.Random(606)
    removals = 0
    for _ in range(80):
        s = GAME.initial_state({"size": 8})
        while not GAME.is_terminal(s):
            mv = GAME.legal_moves(s)
            if ">" not in mv[0]:
                removals += 1
                check(len(mv) >= 2, "a removal turn with a single checker "
                                    "should already have been a win")
            s = GAME.apply_move(s, rng.choice(mv))
        for seat in (0, 1):
            check(sum(1 for v in s.board.values() if v == seat) >= 1,
                  "a seat reached zero checkers")
    check(removals > 0, "the removal-reachability sweep saw no removals")


def test_serialize_roundtrip():
    """Compare STATE OBJECTS (not re-serialised dicts) plus the exact key set,
    swept over whole games so every shape of every field is covered."""
    keys = {"n", "board", "to_move", "winner", "ply", "last", "last_kind"}
    rng = random.Random(31337)
    kinds = set()
    for size in (6, 8, 10):
        s = GAME.initial_state({"size": size})
        while True:
            d = GAME.serialize(s)
            check(set(d) == keys, f"serialize key set {sorted(d)}")
            import json
            json.dumps(d)                       # must be JSON-able
            back = GAME.deserialize(d)
            check(back == s, f"state round-trip differs at ply {s.ply}: {back} != {s}")
            kinds.add(s.last_kind)
            if GAME.is_terminal(s):
                break
            s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
    check(kinds >= {"", "move"}, f"round-trip sweep missed a last_kind: {kinds}")


def test_render_every_size():
    """Board.jsx silently DROPS a piece outside the declared board, so check
    every size option on a position that actually occupies all four corners."""
    rng = random.Random(2024)
    for size in (6, 8, 10):
        corners = {(0, 0), (0, size - 1), (size - 1, 0), (size - 1, size - 1)}
        hit = set()
        for attempt in range(400):
            s = GAME.initial_state({"size": size})
            while not GAME.is_terminal(s):
                s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
                spec = GAME.render(s)
                b = spec["board"]
                check(b["type"] == "square" and b["width"] == size and b["height"] == size,
                      f"render declares {b} for size {size}")
                ids = {f"{c},{r}" for r in range(b["height"]) for c in range(b["width"])}
                for p in spec["pieces"]:
                    check(p["cell"] in ids,
                          f"piece at {p['cell']} outside the declared {size}x{size} board")
                    check(p["owner"] in (0, 1), "bad owner")
                for h in spec["highlights"]:
                    check(h["cell"] in ids, f"highlight {h['cell']} off-board")
                check(len(spec["pieces"]) == len(s.board), "render dropped a piece")
                hit |= corners & set(s.board)
            if hit == corners:
                break
        check(hit == corners,
              f"size {size}: never reached all four corners ({sorted(hit)}) — "
              "the render check would be vacuous")


def test_seat_conjugation():
    """(vertical flip + colour swap) maps the initial position to itself, so the
    engine must commute with it.  Without this, seat 1 has almost no coverage."""
    for size in (6, 8, 10):
        s0 = GAME.initial_state({"size": size})
        check(flip_state(s0).board == s0.board,
              "flip+swap is not an automorphism of the initial position")
    rng = random.Random(808)
    for _ in range(40):
        s = GAME.initial_state({"size": 8})
        while not GAME.is_terminal(s):
            f = flip_state(s)
            check(sorted(flip_move(m, s.n) for m in GAME.legal_moves(s))
                  == sorted(GAME.legal_moves(f)), "legal moves do not conjugate")
            m = rng.choice(GAME.legal_moves(s))
            s = GAME.apply_move(s, m)
            f2 = GAME.apply_move(f, flip_move(m, s.n))
            check(f2.board == flip_state(s).board, "apply_move does not conjugate")
            check(f2.winner == (None if s.winner is None else 1 - s.winner),
                  "the winner does not conjugate")


def test_helpers_off_the_legality_path():
    """`group_containing`, `group_sizes`, `algebraic` and `describe_move` are
    not used by move generation, so nothing else would ever test them."""
    rng = random.Random(77)
    checked = 0
    for _ in range(25):
        s = GAME.initial_state({"size": 8})
        while not GAME.is_terminal(s):
            for seat in (0, 1):
                comps = ref_groups(s.board, seat)
                check(G.group_sizes(s.board, seat)
                      == sorted((len(c) for c in comps), reverse=True),
                      "group_sizes disagrees with the reference")
                for comp in comps:
                    for cell in comp:
                        check(G.group_containing(s.board, cell, seat) == comp,
                              f"group_containing wrong at {cell}")
                        checked += 1
            m = rng.choice(GAME.legal_moves(s))
            lbl = GAME.describe_move(s, m)
            if ">" in m:
                frm, to = (G.parse_cell(x) for x in m.split(">"))
                before = len(ref_group_of(s.board, frm, s.to_move))
                nb = dict(s.board)
                del nb[frm]
                nb[to] = s.to_move
                after = len(ref_group_of(nb, to, s.to_move))
                check(after > before, "an illegal move was generated")
                want = (f"{G.algebraic(frm, s.n)}-{G.algebraic(to, s.n)}"
                        f" ({before}→{after})")
                check(lbl == want, f"describe_move {lbl!r} != {want!r}")
            else:
                check(lbl.startswith("x") and "no legal move" in lbl, f"bad label {lbl!r}")
            s = GAME.apply_move(s, m)
    check(G.algebraic((0, 0), 8) == "a1" and G.algebraic((7, 7), 8) == "h8",
          "algebraic() corners")
    check(G.algebraic((2, 7), 8) == "c8", "algebraic() c8 (gameslib's opening square)")
    return checked


def test_heuristic():
    rng = random.Random(11)
    lo, hi = 1.0, -1.0
    for _ in range(20):
        s = GAME.initial_state({"size": 8})
        while True:
            h = GAME.heuristic(s)
            check(isinstance(h, list) and len(h) == 2, f"heuristic shape {h!r}")
            check(all(isinstance(x, float) and math.isfinite(x) for x in h),
                  "heuristic values must be finite floats")
            check(abs(h[0] + h[1]) < 1e-12, "heuristic must be zero-sum")
            check(-1.0 <= h[0] <= 1.0, "heuristic out of range")
            lo, hi = min(lo, h[0]), max(hi, h[0])
            if GAME.is_terminal(s):
                check(h == GAME.returns(s), "heuristic must agree at a terminal")
                break
            s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
    check(lo < -0.2 and hi > 0.2, f"heuristic barely moves: [{lo}, {hi}]")

    # DIRECTION, pinned to measured values: with Blue held FIXED, a Red that is
    # nearly unified must score strictly higher than a Red split in two.
    blue = {(0, 4): 1, (7, 4): 1}                            # 2 groups, both boards
    blob = dict(blue)
    blob.update({(c, r): 0 for r in range(3) for c in range(8)})   # 24
    blob.update({(c, 3): 0 for c in range(5)})                     # +5 = 29 joined
    blob[(7, 7)] = 0                                               # + a lone one
    split = dict(blue)
    split.update({(c, r): 0 for r in range(2) for c in range(8)})  # 16
    split.update({(c, r): 0 for r in (5, 6) for c in range(7)})    # +14 = two groups
    check(G.group_sizes(blob, 0) == [29, 1], G.group_sizes(blob, 0))
    check(G.group_sizes(split, 0) == [16, 14], G.group_sizes(split, 0))
    check(G.group_sizes(blob, 1) == [1, 1] and G.group_sizes(split, 1) == [1, 1],
          "Blue must be identical in both probes")
    check(abs(G.Bounce._progress(blob, 0) - 28 / 29) < 1e-9,
          f"progress(blob) = {G.Bounce._progress(blob, 0)}")
    check(abs(G.Bounce._progress(split, 0) - 15 / 29) < 1e-9,
          f"progress(split) = {G.Bounce._progress(split, 0)}")
    check(G.Bounce._progress(blob, 1) == 0.0, "progress of two lone checkers is 0")
    check(G.Bounce._progress({}, 0) == 0.0, "no checkers is not a group")
    check(G.Bounce._progress({(1, 1): 0}, 0) == 1.0, "one checker is one group")
    good = GAME.heuristic(G.BounceState(n=8, board=blob, to_move=0))
    bad = GAME.heuristic(G.BounceState(n=8, board=split, to_move=0))
    check(good[0] > bad[0] + 0.2,
          f"a nearly-unified Red must score higher: {good[0]} vs {bad[0]}")
    check(abs(good[0] - math.tanh(1.5 * 28 / 29)) < 1e-9,
          f"pinned heuristic value {good[0]}")
    check(abs(bad[0] - math.tanh(1.5 * 15 / 29)) < 1e-9,
          f"pinned heuristic value {bad[0]}")
    # and the same position with the colours swapped must score the mirror image
    mirror = {(c, 7 - r): 1 - o for (c, r), o in blob.items()}
    check(abs(GAME.heuristic(G.BounceState(n=8, board=mirror, to_move=1))[1]
              - good[0]) < 1e-12, "heuristic must be seat-symmetric")

    # It only ever fires at the MCTS rollout cutoff, so force the cutoff.
    from agp.mcts import MCTSBot
    s = GAME.initial_state({"size": 8})
    mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(GAME, s)
    check(mv in GAME.legal_moves(s), "MCTS with a forced rollout cutoff")


def test_apply_move_purity_and_rejection():
    s = GAME.initial_state({"size": 8})
    before = dict(s.board)
    m = GAME.legal_moves(s)[0]
    GAME.apply_move(s, m)
    check(s.board == before and s.ply == 0, "apply_move mutated its input")
    for bad in ("0,0>1,1", "1,1", "3,3>3,4", "0,7>7,0", "nonsense"):
        try:
            GAME.apply_move(s, bad)
        except Exception:
            pass
        else:
            fail(f"apply_move accepted illegal move {bad!r}")
    for bad_size in (7, 2, 0, -4):
        try:
            GAME.initial_state({"size": bad_size})
        except ValueError:
            pass
        else:
            fail(f"initial_state accepted size {bad_size}")


if __name__ == "__main__":
    test_figure1_setup()
    print("ok  A  Figure 1 == setup_board(8): 30+30, corners empty, checkerboard (6/8/10)")
    test_figure2_object()
    print("ok  B  Figure 2: Blue [30] one group wins, Red [22, 8] does not")
    test_figure3_worked_example()
    print("ok  C  Figure 3 worked example: group 11 before the move, 20 after")
    test_opening_counts()
    print("ok  D  opening moves 32 / 60 / 96 on 6x6 / 8x8 / 10x10, all to corners")
    n = test_movegen_vs_reference()
    print(f"ok  E  move generation == brute-force reference over {n} (position, seat) pairs")
    r = test_removal_rule()
    print(f"ok  F1 CHECKER REMOVAL offered iff no real move ({r} forced removals seen)")
    longest = test_termination_monovariant()
    print(f"ok  F2 monovariant strictly increases; no repeats; longest random game {longest} plies")
    w = test_win_is_the_movers_and_reachable()
    print(f"ok  G1 only the mover wins, and both seats do (R/B = {w})")
    test_removal_spiral_and_single_checker_win()
    print("ok  G2 forced-removal spiral: one checker left == one group == a win; never zero")
    test_serialize_roundtrip()
    print("ok  H  serialize/deserialize compares equal as STATES, exact key set, whole games")
    test_render_every_size()
    print("ok  I  render() correct for sizes 6/8/10 with all four corners occupied")
    test_seat_conjugation()
    print("ok  J  engine commutes with (vertical flip + colour swap)")
    c = test_helpers_off_the_legality_path()
    print(f"ok  K  off-path helpers checked ({c} group_containing probes) + describe_move")
    test_heuristic()
    print("ok  L  heuristic shape/range/zero-sum/terminal/DIRECTION + forced rollout cutoff")
    test_apply_move_purity_and_rejection()
    print("ok  M  apply_move is pure and rejects illegal moves; bad sizes rejected")
    print("bounce selftest: all anchors passed")
