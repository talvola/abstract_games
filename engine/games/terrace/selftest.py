"""Terrace correctness anchors (pure stdlib).

Covers, on hand-built positions and on random play:

* the BOARD ITSELF — the elevation of all 64 (and 36) squares against the
  published height tables transcribed rank-8-first, plus two structural facts
  the move generator relies on: no king-step ever changes the level by more
  than one, and every level splits into exactly TWO one-square-wide chains that
  are simple paths (which is what the publisher's "it cannot move across the
  centerpoint of the board" amounts to);
* the four published opening arrays, transcribed square by square, and the
  opening move counts for all eight option combinations — the numbers the
  AbstractPlay reference implementation reports (17 / 26 / 31 / 50 with standard
  capturing, 19 / 34 / 42 / 67 with Rank Capture);
* that the four move families (up / down / slide / capture) never generate the
  same move twice, so `legal_moves`' dedupe is a genuine no-op rather than
  hiding a double count;
* every movement rule separately: up straight AND diagonally, down STRAIGHT
  ONLY (a diagonal step down to an empty square is not a move at all), and the
  same-level slide — any distance along the terrace, stopped by an opponent's
  piece, NOT stopped by one of your own, and never crossing to the other chain.
  The slide is also cross-checked against an INDEPENDENT implementation (order
  the chain as a path and walk both ways) over thousands of random positions;
* capturing: diagonally down only, same size or smaller, your own pieces
  included (cannibalism), and the three near-misses that must NOT be captures
  (straight down, diagonally up, same level);
* the Rank Capture variant's four cases, including assassination;
* all four endings — T to the far corner, T captured, cannibalising your own T,
  and the stalemate draw — and, explicitly, that a DECISIVE result outranks
  BOTH draw conditions: a win that coincides with the opponent being stranded,
  and a win that coincides with the no-capture counter tripping, must still be
  a win;
* purity, and a LOSSLESS serialize round-trip asserted as
  ``deserialize(serialize(s)) == s`` (the weaker ``serialize(deserialize(d))
  == d`` cannot see a field that serialize drops, and a dropped `quiet` or
  `capture` would silently break in-progress async matches, which round-trip
  through the database on every move);
* termination, with the proved bound `pieces * QUIET_LIMIT`, on ALL EIGHT option
  combinations — and that the manifest's `max_random_plies` sits between what
  random play reaches and that proved bound, so a termination regression fails
  loudly instead of being absorbed into a silent cap draw;
* that `apply_move` REFUSES an illegal-but-parseable move (unchecked, the string
  `"0,0>7,7"` walks a T to the far corner and scores a win) and a move on a
  finished game;
* the RenderSpec shape — tints and elevation labels on every square, the two
  goal squares in their owners' colours, and `size` + `label` on every piece —
  on the opening AND on a mid-game position of every option combination, plus
  the tint ramp's contrast against the renderer's faint board-label colour and
  every `RESULT_TEXT` caption.

The full move-for-move differential against AbstractPlay's `gameslib` lives in
`_diff_ap.py` (manual, needs node).
"""
import json
import random
import sys
from dataclasses import fields as dc_fields, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.terrace.game import (  # noqa: E402
    QUIET_LIMIT, RESULT_TEXT, SETUPS, Terrace, TState, algebraic, dec, elevation,
    enc, geom, is_royal, owner_of, size_of,
)

G = Terrace()

# The published boards, transcribed rank-8-first (the way they are printed).
HEIGHTS = {
    8: ("87654321",
        "77654322",
        "66654333",
        "55554444",
        "44445555",
        "33345666",
        "22345677",
        "12345678"),
    6: ("654321",
        "554322",
        "444333",
        "333444",
        "223455",
        "123456"),
}

# The four published opening arrays, transcribed square by square (sizes; "T"
# marks the royal).  Seat 0 = the player whose home is rank 1.
OPENINGS = {
    (8, "long"): ({"a1": "T", "b1": 1, "c1": 2, "d1": 2, "e1": 3, "f1": 3,
                   "g1": 4, "h1": 4, "a2": 4, "b2": 4, "c2": 3, "d2": 3,
                   "e2": 2, "f2": 2, "g2": 1, "h2": 1},
                  {"a8": 4, "b8": 4, "c8": 3, "d8": 3, "e8": 2, "f8": 2,
                   "g8": 1, "h8": "T", "a7": 1, "b7": 1, "c7": 2, "d7": 2,
                   "e7": 3, "f7": 3, "g7": 4, "h7": 4}),
    (8, "short"): ({"b1": 4, "c1": 3, "d1": 3, "e1": 2, "f1": 2, "g1": "T"},
                   {"b8": "T", "c8": 2, "d8": 2, "e8": 3, "f8": 3, "g8": 4}),
    (6, "long"): ({"a1": "T", "b1": 1, "c1": 2, "d1": 2, "e1": 3, "f1": 3,
                   "a2": 3, "b2": 3, "c2": 2, "d2": 2, "e2": 1, "f2": 1},
                  {"a6": 3, "b6": 3, "c6": 2, "d6": 2, "e6": 1, "f6": "T",
                   "a5": 1, "b5": 1, "c5": 2, "d5": 2, "e5": 3, "f5": 3}),
    (6, "short"): ({"b1": 3, "c1": 2, "d1": 2, "e1": "T"},
                   {"b6": "T", "c6": 2, "d6": 2, "e6": 3}),
}

# Opening move counts reported by the AbstractPlay reference implementation.
OPENING_MOVES = {
    (8, "long", "standard"): 50, (8, "short", "standard"): 31,
    (6, "long", "standard"): 26, (6, "short", "standard"): 17,
    (8, "long", "rank"): 67, (8, "short", "rank"): 34,
    (6, "long", "rank"): 42, (6, "short", "rank"): 19,
}


def ix(a: str, n: int = 8) -> int:
    return (int(a[1:]) - 1) * n + (ord(a[0]) - ord("a"))


def cid(a: str, n: int = 8) -> str:
    i = ix(a, n)
    return f"{i % n},{i // n}"


def mk(pieces, n=8, to_move=0, capture="standard", setup="long", quiet=0, ply=0):
    """Build a position; ``pieces`` = {"d5": (seat, size, royal)}."""
    board = [0] * (n * n)
    for a, (seat, size, royal) in pieces.items():
        board[ix(a, n)] = enc(seat, size, royal)
    return TState(board=tuple(board), to_move=to_move, size=n, setup=setup,
                  capture=capture, quiet=quiet, ply=ply, winner=None, end=None,
                  last=None)


def pairs(s):
    """Legal moves as {(from-alg, to-alg)}."""
    n = s.size
    out = set()
    for m in G.legal_moves(s):
        f, t = m.split(">")
        fc, fr = (int(x) for x in f.split(","))
        tc, tr = (int(x) for x in t.split(","))
        out.add((algebraic(fr * n + fc, n), algebraic(tr * n + tc, n)))
    return out


def dests(s, frm):
    return {t for f, t in pairs(s) if f == frm}


def chains(n):
    """Every level's orthogonally connected same-level components."""
    g = geom(n)
    out = []
    seen = set()
    for i in range(n * n):
        if i in seen:
            continue
        seen.add(i)
        comp, stack = [i], [i]
        while stack:
            k = stack.pop()
            for j in g.same_orth[k]:
                if j not in seen:
                    seen.add(j)
                    comp.append(j)
                    stack.append(j)
        out.append(sorted(comp))
    return out


def slide_ref(board, n, i, seat):
    """INDEPENDENT same-level reachability, written the other way round: order
    the piece's terrace as an explicit path (each chain is a simple path, which
    the geometry check below proves), then walk outward in both directions and
    stop at the first opponent piece.  Returns the reachable EMPTY squares."""
    g = geom(n)
    # collect the chain containing i
    comp, seen, stack = [i], {i}, [i]
    while stack:
        k = stack.pop()
        for j in g.same_orth[k]:
            if j not in seen:
                seen.add(j)
                comp.append(j)
                stack.append(j)
    # order it: start at an endpoint (degree <= 1) and follow the path
    deg = {k: len([j for j in g.same_orth[k] if j in seen]) for k in comp}
    ends = [k for k in comp if deg[k] <= 1]
    assert len(comp) == 1 or len(ends) == 2, (comp, ends)
    path, prev, cur = [ends[0]], None, ends[0]
    while True:
        nxt = [j for j in g.same_orth[cur] if j in seen and j != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        path.append(cur)
    assert sorted(path) == sorted(comp)
    p = path.index(i)
    out = []
    for step in (-1, 1):
        k = p + step
        while 0 <= k < len(path):
            code = board[path[k]]
            if code and owner_of(code) != seat:
                break                       # an opponent's piece stops the walk
            if code == 0:
                out.append(path[k])
            k += step
    return set(out)


def raw_move_count(s):
    """How many moves the four families generate BEFORE legal_moves dedupes
    them.  If this ever exceeds len(legal_moves), two families are producing the
    same (from, to) pair and the generator's disjointness claim is false."""
    g = geom(s.size)
    raw = 0
    for i, code in enumerate(s.board):
        if not code or owner_of(code) != s.to_move:
            continue
        raw += sum(1 for j in g.up_any[i] if s.board[j] == 0)
        raw += sum(1 for j in g.down_orth[i] if s.board[j] == 0)
        raw += len(Terrace.same_level_targets(s.board, g, i, s.to_move))
        raw += len(Terrace.capture_targets(s.board, g, i, s.capture))
    return raw


def random_position(rng, n):
    board = [0] * (n * n)
    for i in rng.sample(range(n * n), rng.randint(2, 16)):
        board[i] = enc(rng.randint(0, 1), rng.randint(1, 4), False)
    return tuple(board)


def main():
    # =================================================== the board itself
    for n, rows in HEIGHTS.items():
        for row, text in enumerate(rows):
            for col, ch in enumerate(text):
                # rows are printed rank-N first, so rank = n - row
                assert elevation(col, n - 1 - row, n) == int(ch), (n, col, row)
        g = geom(n)
        assert max(g.elev) == n and min(g.elev) == 1
        # the two lowest and two highest corners
        assert g.elev[ix("a1", n)] == 1
        assert g.elev[(n - 1) * n + (n - 1)] == 1                 # h8 / f6
        assert g.elev[(n - 1) * n] == n and g.elev[n - 1] == n     # a8/h1, a6/f1
        # goal squares are the two LOWEST squares, and they are each other's
        assert g.target == (n * n - 1, 0)
        assert g.elev[g.target[0]] == 1 and g.elev[g.target[1]] == 1

        # (a) no king-step ever changes the level by more than one, so "one
        #     square per move, one level at a time" is never ambiguous
        for i in range(n * n):
            c, r = i % n, i // n
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    x, y = c + dc, r + dr
                    if 0 <= x < n and 0 <= y < n:
                        assert abs(elevation(x, y, n) - g.elev[i]) <= 1

        # (b) every level is exactly TWO chains, each a simple path.  The move
        #     generator's flood fill is only equivalent to "the route along the
        #     terrace" because the route is unique, and the fact that the two
        #     chains never touch IS the publisher's centerpoint rule.
        per_level = {}
        for comp in chains(n):
            per_level.setdefault(g.elev[comp[0]], []).append(comp)
            deg = [len([j for j in geom(n).same_orth[k] if j in set(comp)])
                   for k in comp]
            assert max(deg) <= 2, (n, comp, deg)              # a path, not a tree
            edges = sum(deg) // 2
            assert edges == len(comp) - 1, (n, comp)          # acyclic + connected
        assert sorted(per_level) == list(range(1, n + 1))
        for lvl, comps in per_level.items():
            assert len(comps) == 2, (n, lvl, comps)
            a, b = comps
            assert not (set(a) & set(b))
        assert [len(c) for c in per_level[1]] == [1, 1]
        assert [len(c) for c in per_level[n]] == [1, 1]
    # spot-check the 8x8 chains by name against the transcribed table
    assert {algebraic(i, 8) for i in
            [c for c in chains(8) if ix("d1") in c][0]} == \
        {"d1", "d2", "d3", "d4", "c4", "b4", "a4"}
    assert {algebraic(i, 8) for i in
            [c for c in chains(8) if ix("e5") in c][0]} == \
        {"e5", "f5", "g5", "h5", "e6", "e7", "e8"}

    # ============================================ setups and opening counts
    assert set(SETUPS) == set(OPENINGS)     # every shipped setup is transcribed
    for (n, setup), (p0, p1) in OPENINGS.items():
        s = G.initial_state({"board": n, "setup": setup})
        got = {}
        for i, code in enumerate(s.board):
            if code:
                o, sz, roy = dec(code)
                got.setdefault(o, {})[algebraic(i, n)] = "T" if roy else sz
        assert got[0] == p0, (n, setup, sorted(map(str, set(got[0].items())
                                                   ^ set(p0.items()))))
        assert got[1] == p1, (n, setup, sorted(map(str, set(got[1].items())
                                                   ^ set(p1.items()))))
        # exactly one royal each, and it is a size-1 piece
        for seat in (0, 1):
            roy = [i for i, c in enumerate(s.board)
                   if c and is_royal(c) and owner_of(c) == seat]
            assert len(roy) == 1 and size_of(s.board[roy[0]]) == 1
        assert len(p0) == len(p1) == (2 * n if setup == "long" else n - 2)
    for (n, setup, cap), want in OPENING_MOVES.items():
        s = G.initial_state({"board": n, "setup": setup, "capture": cap})
        lm = G.legal_moves(s)
        assert len(lm) == want, (n, setup, cap, len(lm), want)
        assert len(set(lm)) == len(lm)              # no duplicate move strings
        for m in lm:
            assert len(m.split(">")) == 2 and "=" not in m, m

    # ================================================== the movement rules
    # --- moving UP: straight OR diagonally, one level, to a vacant square
    st = mk({"d4": (0, 2, False)})
    assert dests(st, "d4") >= {"e3", "e4", "c5", "d5"}         # 2 diagonal, 2 straight
    assert {"e3", "c5"} <= dests(st, "d4")                     # diagonal up is legal
    st = mk({"d4": (0, 2, False), "e4": (1, 4, False), "d5": (1, 4, False)})
    assert "e4" not in dests(st, "d4") and "d5" not in dests(st, "d4")  # occupied

    # --- moving DOWN: STRAIGHT only.  d5 is level 5; e5 and d4 are straight
    #     down, c4 and e6 are diagonally down and are therefore capture-only.
    st = mk({"d5": (0, 2, False)})
    d = dests(st, "d5")
    assert {"e5", "d4"} <= d
    assert "c4" not in d and "e6" not in d, d
    # ...and the diagonal-down squares only become legal when a piece is there
    st = mk({"d5": (0, 2, False), "c4": (1, 2, False)})
    assert "c4" in dests(st, "d5")
    st = mk({"d5": (0, 2, False), "e5": (1, 1, False)})
    assert "e5" not in dests(st, "d5")            # straight down is NOT a capture

    # --- the same-level slide
    st = mk({"d1": (0, 2, False)})                # level-4 chain d1..d4,c4,b4,a4
    assert dests(st, "d1") == {"d2", "d3", "d4", "c4", "b4", "a4",   # the terrace
                               "e1", "e2",        # up to level 5 (straight, diag)
                               "c1"}              # down to level 3 (straight)
    # the OTHER level-4 chain is unreachable: the publisher's "it cannot move
    # across the centerpoint of the board"
    assert dests(st, "d1") & {"e5", "f5", "g5", "h5", "e6", "e7", "e8"} == set()
    st = mk({"d1": (0, 2, False), "d3": (1, 4, False)})
    assert dests(st, "d1") & {"d2", "d3", "d4", "c4", "b4", "a4"} == {"d2"}
    st = mk({"d1": (0, 2, False), "d3": (0, 4, False)})        # OWN piece
    assert dests(st, "d1") & {"d2", "d3", "d4", "c4", "b4", "a4"} == \
        {"d2", "d4", "c4", "b4", "a4"}, dests(st, "d1")
    # the whole slide routine vs. the independent path-walking implementation
    rng = random.Random(2872)
    checked = disjoint = 0
    for _ in range(300):
        n = rng.choice((6, 8))
        board = random_position(rng, n)
        for i, code in enumerate(board):
            if not code:
                continue
            seat = owner_of(code)
            a = set(Terrace.same_level_targets(board, geom(n), i, seat))
            b = slide_ref(board, n, i, seat)
            assert a == b, (n, algebraic(i, n), sorted(a ^ b))
            checked += 1
        # ...and the four move families never overlap, so legal_moves' dedupe
        # is genuinely a no-op rather than papering over double-counted moves
        for seat in (0, 1):
            for cap in ("standard", "rank"):
                t = TState(board=board, to_move=seat, size=n, setup="long",
                           capture=cap, quiet=0, ply=0, winner=None)
                assert raw_move_count(t) == len(G.legal_moves(t)), (n, seat, cap)
                disjoint += 1
    assert checked > 2000 and disjoint > 1000, (checked, disjoint)

    # ================================================== capturing (standard)
    # d5 is level 5; c4 and e6 are the two squares diagonally one level down.
    for victim, capturable in ((1, True), (2, True), (3, False), (4, False)):
        st = mk({"d5": (0, 2, False), "c4": (1, victim, False)})
        assert (("d5", "c4") in pairs(st)) is capturable, (victim, capturable)
    # cannibalism: your OWN piece is a legal target
    st = mk({"d5": (0, 3, False), "c4": (0, 3, False)})
    assert ("d5", "c4") in pairs(st)
    st = mk({"d5": (0, 3, False), "c4": (0, 4, False)})
    assert ("d5", "c4") not in pairs(st)          # ...still only same size or smaller
    # the three near-misses that are NOT captures
    st = mk({"d5": (0, 4, False), "d4": (1, 1, False)})       # straight DOWN
    assert ("d5", "d4") not in pairs(st)
    st = mk({"d4": (0, 4, False), "c5": (1, 1, False)})       # diagonally UP
    assert ("d4", "c5") not in pairs(st)
    st = mk({"d1": (0, 4, False), "d2": (1, 1, False)})       # SAME level
    assert ("d1", "d2") not in pairs(st)

    # ==================================== capturing (Rank Capture variant)
    # straight up: the attacker must be strictly LARGER
    for mine, victim, ok in ((3, 2, True), (3, 3, False), (2, 3, False)):
        st = mk({"d4": (0, mine, False), "e4": (1, victim, False)},
                capture="rank")
        assert (("d4", "e4") in pairs(st)) is ok, (mine, victim)
    # ...except assassination: a rank-1 piece takes a largest-rank piece
    st = mk({"d4": (0, 1, False), "e4": (1, 4, False)}, capture="rank")
    assert ("d4", "e4") in pairs(st)
    st = mk({"d4": (0, 1, True), "e4": (1, 4, False)}, capture="rank")
    assert ("d4", "e4") in pairs(st)              # the T may assassinate too
    st = mk({"d4": (0, 1, False), "e4": (1, 3, False)}, capture="rank")
    assert ("d4", "e4") not in pairs(st)          # only the LARGEST rank
    # on the 6x6 board the piece set stops at rank 3, so THAT is the assassin's
    # target (c3 is level 3, d3 level 4 straight above it)
    assert geom(6).elev[ix("c3", 6)] == 3 and geom(6).elev[ix("d3", 6)] == 4
    st = mk({"c3": (0, 1, False), "d3": (1, 3, False)}, n=6, capture="rank")
    assert ("c3", "d3") in pairs(st)
    st = mk({"c3": (0, 1, False), "d3": (1, 2, False)}, n=6, capture="rank")
    assert ("c3", "d3") not in pairs(st)
    # same level, orthogonally adjacent: at least the same size
    for mine, victim, ok in ((2, 2, True), (3, 2, True), (2, 3, False)):
        st = mk({"d1": (0, mine, False), "d2": (1, victim, False)},
                capture="rank")
        assert (("d1", "d2") in pairs(st)) is ok, (mine, victim)
    # diagonally down: at most one rank smaller
    for mine, victim, ok in ((2, 3, True), (2, 4, False), (4, 4, True)):
        st = mk({"d5": (0, mine, False), "c4": (1, victim, False)},
                capture="rank")
        assert (("d5", "c4") in pairs(st)) is ok, (mine, victim)
    # movement is untouched by the variant
    a = mk({"d1": (0, 2, False), "d3": (0, 4, False)})
    b = mk({"d1": (0, 2, False), "d3": (0, 4, False)}, capture="rank")
    assert dests(a, "d1") == dests(b, "d1") - {"d3"}   # only the capture is added

    # ========================================================== the endings
    # (1) the T reaches the lowest square across the board
    st = mk({"g8": (0, 1, True), "a3": (1, 1, True)})
    assert ("g8", "h8") in pairs(st)
    out = G.apply_move(st, cid("g8") + ">" + cid("h8"))
    assert out.winner == 0 and out.end == "target" and G.returns(out) == [1.0, -1.0]
    assert G.is_terminal(out) and G.legal_moves(out) == []
    # ...and for seat 1, whose corner is a1
    st = mk({"b1": (1, 1, True), "f6": (0, 1, True)}, to_move=1)
    out = G.apply_move(st, cid("b1") + ">" + cid("a1"))
    assert out.winner == 1 and out.end == "target" and G.returns(out) == [-1.0, 1.0]
    # A T sitting on the OPPONENT's corner is not a win — and both Ts start on
    # the opponent's corner in the long setup, so play a real (non-royal) move
    # and check the game is still live afterwards.
    st = G.initial_state()
    assert st.board[ix("a1")] == enc(0, 1, True)     # seat 0's T on seat 1's goal
    assert st.board[ix("h8")] == enc(1, 1, True)     # seat 1's T on seat 0's goal
    for _ in range(4):
        st = G.apply_move(st, [m for m in G.legal_moves(st)
                               if not m.startswith(cid("a1") + ">")
                               and not m.startswith(cid("h8") + ">")][0])
        assert st.winner is None and not G.is_terminal(st)

    # (2) capturing the opponent's T
    st = mk({"g7": (0, 3, False), "h8": (1, 1, True), "a3": (0, 1, True),
             "b5": (1, 2, False)})
    out = G.apply_move(st, cid("g7") + ">" + cid("h8"))
    assert out.winner == 0 and out.end == "royal" and G.returns(out) == [1.0, -1.0]

    # (3) cannibalising your OWN T loses on the spot
    st = G.initial_state()
    assert ("b2", "a1") in pairs(st)
    out = G.apply_move(st, cid("b2") + ">" + cid("a1"))
    assert out.winner == 1 and out.end == "royal" and G.returns(out) == [-1.0, 1.0]

    # (4) the stalemate draw: "there is no winner and no loser".
    #     Seat 1 owns only its T, on a8 — the board's highest square, so it can
    #     never move up; both squares straight down (a7, b8) are occupied, and
    #     the only square diagonally down (b7) holds a piece too big for a
    #     size-1 piece to capture.  It therefore has no move at all.
    WALL = {"a8": (1, 1, True), "a7": (0, 4, False), "b8": (0, 4, False),
            "b7": (0, 2, False)}
    st = mk(dict(WALL, d5=(0, 1, True), h4=(0, 2, False)))
    assert G.legal_moves(replace(st, to_move=1)) == []
    out = G.apply_move(st, cid("h4") + ">" + cid("h3"))
    assert out.winner == -1 and out.end == "stalemate"
    assert G.returns(out) == [0.0, 0.0]
    # ...and it is really the WALL doing it: shrink the blocker on b7 to a size
    # the T can capture and seat 1 has a move again
    assert G.legal_moves(replace(
        mk(dict(WALL, b7=(0, 1, False), d5=(0, 1, True))), to_move=1)) != []

    # (5) the no-capture draw
    st = mk({"d1": (0, 2, False), "a1": (1, 1, True), "h4": (0, 1, True)},
            quiet=QUIET_LIMIT - 1)
    out = G.apply_move(st, cid("d1") + ">" + cid("d2"))
    assert out.winner == -1 and out.end == "quiet" and G.returns(out) == [0.0, 0.0]
    # a capture resets the counter instead
    st = mk({"d5": (0, 2, False), "c4": (1, 2, False), "a1": (1, 1, True),
             "h4": (0, 1, True)}, quiet=QUIET_LIMIT - 1)
    out = G.apply_move(st, cid("d5") + ">" + cid("c4"))
    assert out.winner is None and out.quiet == 0

    # ============ A DECISIVE RESULT MUST OUTRANK BOTH DRAW CONDITIONS ============
    # (a) the winning move ALSO strands the opponent AND trips the no-capture
    #     counter.  Seat 1 owns only its walled-in T; seat 0's T steps down from
    #     g8 to h8.  All three conditions fire on the same ply.
    st = mk(dict(WALL, g8=(0, 1, True)), quiet=QUIET_LIMIT - 1)
    assert G.legal_moves(replace(st, to_move=1)) == []   # the opponent is stuck
    out = G.apply_move(st, cid("g8") + ">" + cid("h8"))
    assert out.quiet == QUIET_LIMIT                 # the counter really did trip
    assert out.winner == 0 and out.end == "target", (out.winner, out.end)
    assert G.returns(out) == [1.0, -1.0]
    # the same position WITHOUT the winning move really is a draw, so the test
    # above is not vacuous
    other = G.apply_move(st, cid("g8") + ">" + cid("g7"))
    assert other.winner == -1 and other.end in ("stalemate", "quiet")

    # (b) capturing the opponent's T on the ply that leaves them with nothing to
    #     move.  Seat 1 has only its T; taking it wins, it is not a stalemate.
    st = mk({"g7": (0, 3, False), "h8": (1, 1, True), "a3": (0, 1, True)})
    out = G.apply_move(st, cid("g7") + ">" + cid("h8"))
    assert G.legal_moves(replace(out, winner=None, end=None)) == []
    assert out.winner == 0 and out.end == "royal" and G.returns(out) == [1.0, -1.0]

    # (c) losing your own T outranks the counters too
    st = mk({"b2": (0, 4, False), "a1": (0, 1, True), "f6": (1, 1, True)},
            quiet=QUIET_LIMIT - 1)
    out = G.apply_move(st, cid("b2") + ">" + cid("a1"))
    assert out.winner == 1 and out.end == "royal"

    # ================================================= purity & round-trip
    s = G.initial_state()
    before = G.serialize(s)
    G.apply_move(s, "1,1>0,0")
    assert G.serialize(s) == before
    # Every dataclass field must appear in the payload, and the round-trip is
    # asserted STATE-first: `serialize(deserialize(d)) == d` is blind to a field
    # serialize never writes, and a dropped `quiet`/`capture`/`setup` would
    # silently corrupt live async matches, which round-trip through the database
    # on every single move.
    assert {f.name for f in dc_fields(TState)} <= set(before)
    rng = random.Random(1991)
    seen = {"quiet": False, "last": False, "end": False, "capture": False}
    for opts in ({}, {"board": 6, "setup": "short", "capture": "rank"}):
        for _ in range(6):
            t = G.initial_state(opts)
            seen["capture"] |= t.capture == "rank"
            while not G.is_terminal(t):
                d = G.serialize(t)
                assert G.deserialize(json.loads(json.dumps(d))) == t
                assert G.serialize(G.deserialize(d)) == d
                seen["quiet"] |= t.quiet > 0
                seen["last"] |= t.last is not None
                lm = G.legal_moves(t)
                assert lm, "no legal move on a non-terminal state"
                assert len(set(lm)) == len(lm) == raw_move_count(t)
                G.describe_move(t, rng.choice(lm))
                t = G.apply_move(t, rng.choice(lm))
            seen["end"] |= t.end is not None
            d = G.serialize(t)
            assert G.deserialize(json.loads(json.dumps(d))) == t
    assert all(seen.values()), seen
    # explicitly, on a hand-built state, so it cannot go untested if random play
    # stops producing these values
    st = replace(mk({"d5": (0, 2, False), "a1": (1, 1, True)}, n=8,
                    to_move=1, capture="rank", setup="short", quiet=17, ply=99),
                 last="3,4>4,4", end=None)
    assert G.deserialize(G.serialize(st)) == st

    # =============================================== describe_move notation
    s = G.initial_state()
    assert G.describe_move(mk({"a1": (0, 1, True)}), "0,0>1,1") == "T a1-b2"
    assert G.describe_move(s, "1,1>0,0") == "4 b2*a1"          # cannibalism
    assert "1,1>0,0" in G.legal_moves(s)
    st = mk({"g7": (0, 3, False), "h8": (1, 1, True)})
    assert G.describe_move(st, cid("g7") + ">" + cid("h8")) == "3 g7xh8"

    # ================================================== termination bound
    MAX_RANDOM_PLIES = json.loads(
        (Path(__file__).resolve().parent / "manifest.json").read_text()
    )["max_random_plies"]
    rng = random.Random(1992)
    ends = {}
    longest = 0
    for _ in range(150):
        t = G.initial_state()
        pieces = sum(1 for c in t.board if c)
        assert pieces == 32
        while not G.is_terminal(t):
            t = G.apply_move(t, rng.choice(G.legal_moves(t)))
            # Proved bound: every capture removes a piece for good, so a game
            # holds at most (pieces - 1) captures, and at most QUIET_LIMIT plies
            # can pass between them.
            assert t.ply <= pieces * QUIET_LIMIT, t.ply
        longest = max(longest, t.ply)
        ends[t.end] = ends.get(t.end, 0) + 1
        r = G.returns(t)
        assert sum(r) == 0.0 and len(r) == 2
        assert (r == [0.0, 0.0]) == (t.winner == -1)
    assert ends.get("royal", 0) > 100, ends       # the game really is decisive
    # The manifest's random-game ceiling must sit BELOW the game's own proved
    # bound, so a termination regression fails loudly as "did not terminate"
    # instead of being absorbed into a silent cap draw...
    assert MAX_RANDOM_PLIES < 32 * QUIET_LIMIT, MAX_RANDOM_PLIES
    # ...and comfortably ABOVE what uniform-random play actually reaches, on
    # EVERY option combination, not just the default the harness plays.
    assert longest < MAX_RANDOM_PLIES, (longest, MAX_RANDOM_PLIES)
    per_config = {}
    for n in (8, 6):
        for setup in ("long", "short"):
            for cap in ("standard", "rank"):
                worst = 0
                cends = {}
                for _ in range(12):
                    t = G.initial_state({"board": n, "setup": setup,
                                         "capture": cap})
                    pieces = sum(1 for c in t.board if c)
                    while not G.is_terminal(t):
                        t = G.apply_move(t, rng.choice(G.legal_moves(t)))
                        assert t.ply <= pieces * QUIET_LIMIT, (n, setup, cap, t.ply)
                    worst = max(worst, t.ply)
                    cends[t.end] = cends.get(t.end, 0) + 1
                assert worst < MAX_RANDOM_PLIES, (n, setup, cap, worst)
                per_config[(n, setup, cap)] = (worst, cends)
    assert len(per_config) == 8
    # The no-capture draw is OUR house rule, and it is the one cap here that is
    # outcome-load-bearing, so it must be demonstrably REACHABLE by real play --
    # otherwise QUIET_LIMIT could drift to any value at all and every test above
    # would still pass while the rule quietly became dead code.  The 8x8 short
    # setup is where it bites (rules.md measures ~9%); fixed seed, so this is
    # deterministic, not flaky.
    quiet_seen = 0
    qrng = random.Random(1995)
    for _ in range(60):
        t = G.initial_state({"board": 8, "setup": "short"})
        while not G.is_terminal(t):
            t = G.apply_move(t, qrng.choice(G.legal_moves(t)))
        quiet_seen += t.end == "quiet"
    assert quiet_seen > 0, "the no-capture draw never fires -- QUIET_LIMIT is dead"

    # ========================================================== heuristic
    h = G.heuristic(G.initial_state())
    assert isinstance(h, list) and len(h) == 2 and h[0] == -h[1] == 0.0
    st = mk({"d5": (0, 4, False), "g8": (0, 1, True), "a1": (1, 1, True)})
    h = G.heuristic(st)
    assert len(h) == 2 and h[0] > 0 > h[1] and abs(h[0]) <= 1.0
    from agp.mcts import MCTSBot                   # forces the rollout cutoff
    mv = MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(
        G, G.initial_state())
    assert mv in G.legal_moves(G.initial_state())

    # ============================================================= render
    for n in (8, 6):
        s = G.initial_state({"board": n})
        spec = G.render(s)
        b = spec["board"]
        assert b["type"] == "square" and b["width"] == n and b["height"] == n
        assert len(b["tints"]) == n * n and len(b["labels"]) == n * n
        g = geom(n)
        for i in range(n * n):
            key = f"{i % n},{i // n}"
            assert b["labels"][key] == str(g.elev[i])
            assert b["tints"][key].startswith("#") and len(b["tints"][key]) == 7
        # the two goal squares carry their owners' colours
        assert b["tints"][f"{n - 1},{n - 1}"] == "#5a2222"
        assert b["tints"]["0,0"] == "#1e2f5a"
        assert len(spec["pieces"]) == sum(1 for c in s.board if c)
        for p, code in zip(spec["pieces"], [c for c in s.board if c]):
            assert p["owner"] in (0, 1) and 1 <= p["size"] <= 4
            assert p["size"] == size_of(code)
            assert p["label"] == ("T" if is_royal(code) else str(p["size"]))
        royals = [p for p in spec["pieces"] if p["label"] == "T"]
        assert len(royals) == 2 and all(p["size"] == 1 for p in royals)
        assert spec["caption"] == "Red to move"
        assert json.dumps(spec)
    # ...and the same bounds check on a MID-GAME position of every option
    # combination, reached through apply_move.  Board.jsx silently DROPS a piece
    # whose cell falls outside the declared width/height, so a board-size option
    # has to be checked on a state that actually has pieces spread over it.
    rng = random.Random(2026)
    for n in (8, 6):
        for setup in ("long", "short"):
            for cap in ("standard", "rank"):
                t = G.initial_state({"board": n, "setup": setup, "capture": cap})
                for _ in range(30):
                    if G.is_terminal(t):
                        break
                    t = G.apply_move(t, rng.choice(G.legal_moves(t)))
                spec = G.render(t)
                b = spec["board"]
                assert b["width"] == n and b["height"] == n, (n, setup, cap, b)
                cells = set()
                for p in spec["pieces"]:
                    c, r = (int(x) for x in p["cell"].split(","))
                    assert 0 <= c < n and 0 <= r < n, (n, setup, cap, p)
                    assert 1 <= p["size"] <= (4 if n == 8 else 3), (n, p)
                    cells.add(p["cell"])
                assert len(cells) == len(spec["pieces"])       # one piece per cell
                assert len(spec["pieces"]) == sum(1 for c in t.board if c)
                for key in list(b["tints"]) + list(b["labels"]):
                    c, r = (int(x) for x in key.split(","))
                    assert 0 <= c < n and 0 <= r < n, (n, key)
                assert json.dumps(spec)
    st = mk({"g8": (0, 1, True), "a3": (1, 1, True)})
    out = G.apply_move(st, cid("g8") + ">" + cid("h8"))
    assert G.render(out)["caption"] == "Red wins — T reached the far corner"
    assert {h["cell"] for h in G.render(out)["highlights"]} == {"6,7", "7,7"}
    # every RESULT_TEXT reason must actually render a caption (a missing key
    # would be a KeyError inside render(), i.e. a white-screen board)
    for reason, winner, want in (("target", 0, "Red wins"), ("royal", 1, "Blue wins"),
                                 ("stalemate", -1, "Draw"), ("quiet", -1, "Draw")):
        cap = G.render(replace(mk({"a1": (0, 1, True), "f6": (1, 1, True)}),
                               winner=winner, end=reason))["caption"]
        assert cap.startswith(want) and RESULT_TEXT[reason] in cap, (reason, cap)

    # The elevation number is the board's own primary information channel, and
    # the generic renderer draws it on an empty cell in a FAINT stone colour
    # (`#8f8674`, web/src/Board.jsx).  A tint ramp that runs into that colour
    # makes the number invisible on exactly the highest terraces -- it did, on
    # the 8x8 level-7/8 and 6x6 level-6 squares, until the ramp was darkened.
    for n in (8, 6):
        for lvl in range(1, n + 1):
            rgb = Terrace._tint(lvl, n)
            chans = tuple(int(rgb[k:k + 2], 16) for k in (1, 3, 5))
            gap = min(abs(a - b) for a, b in zip(chans, Terrace.LABEL_COLOUR))
            assert gap >= 24, (n, lvl, rgb, gap)
    # ...and the ramp must still be monotone, or it stops reading as a height.
    for n in (8, 6):
        vals = [sum(int(Terrace._tint(l, n)[k:k + 2], 16) for k in (1, 3, 5))
                for l in range(1, n + 1)]
        assert all(b - a >= 12 for a, b in zip(vals, vals[1:])), (n, vals)

    # ======================================== apply_move rejects bad input
    s = G.initial_state()
    # a structurally valid move that is NOT legal must raise, not be applied --
    # unchecked, "0,0>7,7" teleports seat 0's T onto its goal and scores a WIN
    assert "0,0>7,7" not in G.legal_moves(s)
    for bad in ("0,0>7,7", "0,7>0,6", "9,9>0,0", "0,0", "0,0>0,0"):
        try:
            G.apply_move(s, bad)
            raise AssertionError(f"apply_move accepted {bad!r}")
        except ValueError:
            pass
    # ...and the control: the legal version of the same shape still works
    assert G.apply_move(s, "1,1>0,0").winner == 1
    # a move on a finished game is refused too
    fin = G.apply_move(s, "1,1>0,0")
    try:
        G.apply_move(fin, G.legal_moves(replace(fin, winner=None, end=None))[0])
        raise AssertionError("apply_move accepted a move on a finished game")
    except ValueError:
        pass

    print(f"terrace selftest OK (elevation tables for 6x6+8x8, "
          f"{checked} slide cross-checks, {disjoint} move-family disjointness "
          f"checks, 8 opening counts, 4 published setups, 150 random games, "
          f"longest {longest} plies, ends {ends}; plus 12 games and a mid-game "
          f"render-bounds check on each of the 8 option combinations, worst ply "
          f"{max(v[0] for v in per_config.values())} vs manifest cap "
          f"{MAX_RANDOM_PLIES})")


if __name__ == "__main__":
    main()
