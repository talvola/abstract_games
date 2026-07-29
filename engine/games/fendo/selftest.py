"""Fendo correctness anchors (pure stdlib).

Covers, on hand-built positions and on random play:

* the opening move count (212 = 47 stock entries + 165 move-and-fence moves),
  which is the number the AbstractPlay reference implementation reports;
* the slide rule — straight rays, exactly ONE right-angle turn, blocked corners,
  fences cut mid-leg, and a cross-check of the whole reachability routine against
  an INDEPENDENT second implementation (the "try both corners of the bounding
  rectangle" formulation) over thousands of random positions;
* the fence restriction — no empty area may be created, no second open area may
  be left — cross-checked against the slow global form deep into the ENDGAME,
  where that rule actually bites, not only in the wide-open opening;
* two positions transcribed pixel-for-pixel from the DESIGNER's own worked
  diagrams (spielstein.com/games/fendo/rules): the "placement" diagram's 21
  marked entry cells, and Example 2's piece that has no legal action at all;
* a piece in a closed area can never be selected;
* scoring, the "closed areas partition all 49 cells" invariant at a normal end,
  and honest draw handling;
* move-string hygiene — a bare "c,r" is never legal (it would collide with stock
  entry) and every fence move is a TWO-cell path, "from>from" being the stay-put
  form, which is what makes the move-then-fence flow clickable in the web UI;
* purity, a LOSSLESS serialize round-trip (every dataclass field survives, tested
  as ``deserialize(serialize(s)) == s`` — the weaker ``serialize(deserialize(d))
  == d`` cannot see a field that serialize drops entirely, and a dropped `passes`
  or `stock` would silently break in-progress async matches, which round-trip
  through the database on every move);
* the `board.fences` render contract for ALL FOUR compass directions, and that a
  fence is never emitted on the board rim;
* describe_move (including the stay-put label) and the heuristic's shape at a
  forced MCTS rollout cutoff.

The full move-for-move differential against AbstractPlay's `gameslib` lives in
`_diff_ap.py` (manual, needs node).
"""
import json
import random
import sys
from dataclasses import fields as dc_fields, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.fendo.game import (  # noqa: E402
    EMPTY, SIZE, DIRS, DIR_ORDER, Fendo, FState, edge_key, idx, cell_name,
)

G = Fendo()
N = SIZE * SIZE


def mk(pieces, fences=(), stock=(6, 6), to_move=0, passes=0, over=False):
    """Build a position: ``pieces`` = {(c, r): seat}."""
    board = [EMPTY] * N
    for (c, r), seat in pieces.items():
        board[idx(c, r)] = seat
    return FState(board=tuple(board), fences=frozenset(fences), stock=stock,
                  to_move=to_move, passes=passes, over=over, last=None)


def reach(state, c, r):
    return {(i % SIZE, i // SIZE) for i in G.reachable(state.board, state.fences, c, r)}


# --- the designer's own algebraic names, used only to transcribe his diagrams
def cr(a):
    """'d5' -> (3, 4)."""
    return (ord(a[0]) - ord("a"), int(a[1]) - 1)


def alg(c, r):
    return f"{chr(ord('a') + c)}{r + 1}"


def diagram(white, orange, hfences, vfences, stock, to_move=0):
    """Build a position from a diagram.  ``hfences`` entries read "a5/a4" (the
    edge between those two cells, same file); ``vfences`` read "b5/c5" (same
    rank).  Keeps the transcription legible next to the published picture."""
    pieces = {}
    for a in white:
        pieces[cr(a)] = 0
    for a in orange:
        pieces[cr(a)] = 1
    fences = []
    for a in hfences:
        lo = a.split("/")[1]
        assert a.split("/")[0][0] == lo[0], a
        fences.append(("h",) + cr(lo))
    for a in vfences:
        left = a.split("/")[0]
        assert left[1] == a.split("/")[1][1], a
        fences.append(("v",) + cr(left))
    return mk(pieces, fences=fences, stock=stock, to_move=to_move)


# --- an INDEPENDENT reachability implementation, written the other way round:
# for every candidate target, test the (at most) two L-paths through the corners
# of the bounding rectangle.  Used only to cross-check G.reachable.
def reach_ref(board, fences, c0, r0):
    def clear(c, r, d, n):
        """Walk n steps in direction d from (c,r); every step must cross no fence
        and land on an empty cell."""
        dc, dr = DIRS[d]
        for _ in range(n):
            k = edge_key(c, r, d)
            if k is None or k in fences:
                return None
            c, r = c + dc, r + dr
            if board[idx(c, r)] != EMPTY:
                return None
        return (c, r)

    out = set()
    for c1 in range(SIZE):
        for r1 in range(SIZE):
            if (c1, r1) == (c0, r0) or board[idx(c1, r1)] != EMPTY:
                continue
            dh = "E" if c1 > c0 else "W"
            dv = "N" if r1 > r0 else "S"
            nh, nv = abs(c1 - c0), abs(r1 - r0)
            if nh == 0 or nv == 0:            # straight line: no turn allowed
                d = dv if nh == 0 else dh
                if clear(c0, r0, d, nh + nv) is not None:
                    out.add((c1, r1))
                continue
            for first, nf, second, ns in ((dh, nh, dv, nv), (dv, nv, dh, nh)):
                mid = clear(c0, r0, first, nf)
                if mid is not None and clear(mid[0], mid[1], second, ns) is not None:
                    out.add((c1, r1))
                    break
    return out


def legal_ref(state):
    """A deliberately SLOW, independently written second implementation of the
    whole move generator: `reach_ref` for the slide rule and the *global*
    `Fendo.fence_ok` (recount every area on the whole board) for the fence rule.
    The shipped generator uses a local split test instead; if the two ever
    disagree, one of them is wrong."""
    board, fences = state.board, state.fences
    open_cells = None
    for cells, owners in Fendo.areas(board, fences):
        if len(owners) >= 2:
            open_cells = set(cells)
    if open_cells is None:
        return []
    seat = state.to_move
    mine = [i for i in open_cells if board[i] == seat]
    tgt = {}
    for i in mine:
        d = {idx(c, r) for (c, r) in reach_ref(board, fences, i % SIZE, i // SIZE)}
        tgt[i] = (d & open_cells) | {i}
    out = []
    if state.stock[seat] > 0:
        for j in sorted(set().union(*tgt.values()) if tgt else set()):
            if board[j] == EMPTY:
                out.append("P@" + cell_name(j % SIZE, j // SIZE))
    for i in sorted(tgt):
        for j in sorted(tgt[i]):
            nb = list(board)
            nb[i] = EMPTY
            nb[j] = seat
            c, r = j % SIZE, j // SIZE
            for d in DIR_ORDER:
                key = edge_key(c, r, d)
                if key is None or key in fences:
                    continue
                if not Fendo.fence_ok(tuple(nb), fences, key):
                    continue
                out.append(cell_name(i % SIZE, i // SIZE) + ">"
                           + cell_name(c, r) + "=FENCE_" + d)
    return out or ["pass"]


def random_position(rng):
    """A random reachable-ish position: pieces and fences scattered by hand (not
    necessarily legal Fendo) — enough to stress the geometry."""
    board = [EMPTY] * N
    for i in rng.sample(range(N), rng.randint(1, 8)):
        board[i] = rng.randint(0, 1)
    fences = set()
    for _ in range(rng.randint(0, 25)):
        k = rng.choice(("h", "v"))
        c = rng.randrange(SIZE - (1 if k == "v" else 0))
        r = rng.randrange(SIZE - (1 if k == "h" else 0))
        fences.add((k, c, r))
    return tuple(board), frozenset(fences)


def main():
    # ---------------------------------------------------------------- opening
    s = G.initial_state()
    assert s.board[idx(0, 3)] == 0 and s.board[idx(6, 3)] == 1
    assert sum(1 for v in s.board if v != EMPTY) == 2
    assert s.stock == (6, 6) and s.to_move == 0 and not s.over
    lm = G.legal_moves(s)
    entries = [m for m in lm if m.startswith("P@")]
    fmoves = [m for m in lm if "=FENCE_" in m]
    assert len(lm) == 212, len(lm)          # AbstractPlay reports 212
    assert len(entries) == 47, len(entries)  # every empty cell is one move away
    assert len(fmoves) == 165, len(fmoves)
    assert len(set(lm)) == len(lm)          # no duplicates

    # Move-string shape, which the web click-router depends on:
    #  * a BARE "c,r" is never legal (it would collide with stock entry, which
    #    lives on the "P@c,r" drop channel);
    #  * every fence move is a TWO-cell path, "from>to", and "from>from" is the
    #    legal stay-put form.  A one-cell "c,r=FENCE_D" would be matched by
    #    Board.jsx as a complete move on the very click that should SELECT the
    #    piece, making move-then-fence unreachable.
    for m in lm:
        assert (m == "pass" or m.startswith("P@")
                or ("=FENCE_" in m and m.split("=")[1][6:] in DIRS)), m
        assert "," not in m or "=" in m or "@" in m, m
    for m in fmoves:
        path = m.split("=")[0]
        assert len(path.split(">")) == 2, m
    stay = [m for m in fmoves if m.split("=")[0].split(">")[0]
            == m.split("=")[0].split(">")[1]]
    assert len(stay) == 3, stay        # a4 may fence N, E or S (W is the rim)
    assert set(stay) == {"0,3>0,3=FENCE_N", "0,3>0,3=FENCE_E",
                         "0,3>0,3=FENCE_S"}, stay
    # the one-cell form is rejected outright, so it can never come back
    for bad in ("0,3=FENCE_N", "0,3", "0,3>1,3>2,3=FENCE_N"):
        try:
            Fendo._parse(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad!r} should not parse")
    # stay-put reads as such in the move log, and is not a null move
    assert G.describe_move(s, "0,3>0,3=FENCE_N") == "a4 stays, fence N"
    assert G.describe_move(s, "0,3>3,3=FENCE_N") == "a4-d4, fence N"
    assert G.describe_move(s, "P@3,3") == "enter d4"
    assert G.describe_move(s, "pass") == "pass"

    # -------------------------------------------------- the slide rule (a)
    # straight line: a piece blocks the ray beyond it, and the far cell on that
    # rank cannot be reached by any turn (same rank => straight only)
    st = mk({(0, 3): 0, (3, 3): 0, (6, 3): 1})
    rr = reach(st, 0, 3)
    assert (1, 3) in rr and (2, 3) in rr
    assert (4, 3) not in rr and (5, 3) not in rr and (3, 3) not in rr
    assert (4, 4) in rr                       # one turn: N then E

    # one right-angle turn: block BOTH corners of the bounding rectangle
    st = mk({(0, 0): 0, (6, 6): 1, (3, 0): 0, (0, 3): 0})
    assert (3, 3) not in reach(st, 0, 0)
    st = mk({(0, 0): 0, (6, 6): 1, (3, 0): 0})           # only one corner blocked
    assert (3, 3) in reach(st, 0, 0)

    # TWO turns are illegal even when a two-turn path is wide open
    st = mk({(0, 0): 0, (6, 6): 1, (2, 0): 0, (0, 2): 0})
    rr = reach(st, 0, 0)
    assert (1, 2) in rr                        # E to (1,0) then N — one turn, fine
    assert (2, 2) not in rr                    # would need E, N, E — two turns

    # a fence cuts a leg
    st = mk({(0, 0): 0, (6, 6): 1}, fences=[("v", 2, 0)])
    rr = reach(st, 0, 0)
    assert (2, 0) in rr and (3, 0) not in rr
    assert (3, 3) in rr                        # still fine via the (0,3) corner
    st = mk({(0, 0): 0, (6, 6): 1}, fences=[("v", 2, 0), ("h", 0, 2)])
    rr = reach(st, 0, 0)
    assert (3, 2) in rr and (3, 3) not in rr   # both corners now unreachable
    assert (0, 3) not in rr                    # the fence blocks the straight ray

    # a leg of length zero == the straight case, and staying put is offered
    st = mk({(0, 0): 0, (6, 6): 1})
    assert (0, 6) in reach(st, 0, 0) and (6, 0) in reach(st, 0, 0)
    assert (0, 0) not in reach(st, 0, 0)
    assert any(m.startswith("0,0>0,0=FENCE_") for m in G.legal_moves(st))

    # cross-check the whole routine against the independent formulation
    rng = random.Random(20140427)
    checked = 0
    for _ in range(400):
        board, fences = random_position(rng)
        for i, v in enumerate(board):
            if v == EMPTY:
                continue
            c, r = i % SIZE, i // SIZE
            a = reach(FState(board=board, fences=fences, stock=(0, 0), to_move=0,
                             passes=0, over=False), c, r)
            b = reach_ref(board, fences, c, r)
            assert a == b, (c, r, sorted(a ^ b), sorted(fences))
            checked += 1
    assert checked > 800, checked

    # ------------------------------------------- the fence restriction
    # (i) a fence may not create an EMPTY area
    base = {(0, 1): 0, (6, 3): 1}
    st = mk(base)
    assert "0,1>0,1=FENCE_S" in G.legal_moves(st)      # control: legal on its own
    st = mk(base, fences=[("v", 0, 0)])                # (0,0) now hangs off (0,1)
    assert "0,1>0,1=FENCE_S" not in G.legal_moves(st)  # sealing it => empty area
    assert "0,1>0,1=FENCE_N" in G.legal_moves(st)

    # (ii) a fence may not leave TWO open areas
    cut = [("v", 3, r) for r in range(SIZE) if r != 3]
    st = mk({(0, 0): 0, (3, 3): 0, (6, 0): 1, (6, 6): 1}, fences=cut)
    lm2 = G.legal_moves(st)
    assert "3,3>3,3=FENCE_E" not in lm2                # would split 2 open | 2 open
    assert "3,3>3,3=FENCE_N" in lm2                    # control

    # (iii) a piece inside a closed area can never be selected — not even when
    # its own area still offers a free (unfenced) side to build on.  The closed
    # area here is the two cells (0,0)+(0,1), so the sealed piece has a free N
    # side; only the open-area filter stops it being played.
    seal = [("v", 0, 0), ("v", 0, 1), ("h", 0, 1)]
    st = mk({(0, 0): 0, (3, 3): 0, (6, 3): 1}, fences=seal)
    assert not Fendo.blocked(frozenset(seal), 0, 0, "N")   # the side IS free
    assert all(not m.startswith("0,0") for m in G.legal_moves(st)), G.legal_moves(st)
    assert G.scores(st) == (2, 0)                      # the sealed pocket scores 2
    assert not G.is_terminal(st)                       # (3,3) & (6,3) still open
    st = mk({(0, 0): 0, (3, 3): 0, (6, 3): 1}, fences=[("v", 0, 0), ("h", 0, 0)])
    assert G.scores(st) == (1, 0)                      # a 1-cell pocket scores 1
    # an EMPTY area (impossible under the fence rule, but scored explicitly)
    # belongs to nobody
    st = mk({(0, 1): 0, (6, 3): 1}, fences=[("v", 0, 0), ("h", 0, 0)])
    assert [len(o) for _c, o in G.areas(st.board, st.fences)].count(0) == 1
    assert G.scores(st) == (0, 0)

    # (iv) no fence is ever offered on a side that already has one, or on the rim
    st = mk({(2, 2): 0, (6, 3): 1}, fences=[("h", 2, 2)])
    assert "2,2>2,2=FENCE_N" not in G.legal_moves(st)
    st = mk({(0, 0): 0, (6, 3): 1})
    lm3 = G.legal_moves(st)
    assert "0,0>0,0=FENCE_S" not in lm3 and "0,0>0,0=FENCE_W" not in lm3
    assert "0,0>0,0=FENCE_N" in lm3 and "0,0>0,0=FENCE_E" in lm3

    # ------------------------------------------- stock entry (action b)
    st = mk({(0, 0): 0, (6, 6): 1}, fences=[("v", 2, 0), ("h", 0, 2)])
    ent = {m[2:] for m in G.legal_moves(st) if m.startswith("P@")}
    assert ent == {cell_name(c, r) for (c, r) in reach(st, 0, 0)}
    assert "3,3" not in ent and "3,2" in ent
    st = mk({(0, 0): 0, (6, 6): 1}, stock=(0, 6))
    assert not any(m.startswith("P@") for m in G.legal_moves(st))  # empty stock
    st = mk({(0, 0): 0, (6, 6): 1}, stock=(6, 0), to_move=1)
    assert not any(m.startswith("P@") for m in G.legal_moves(st))
    # you may not enter next to an opponent piece in a CLOSED area
    st = mk({(0, 0): 0, (3, 3): 0, (6, 3): 1, (6, 6): 1},
            fences=[("v", 5, 6), ("h", 6, 5)])
    ent = {m[2:] for m in G.legal_moves(st) if m.startswith("P@")}
    assert "6,6" not in ent and G.scores(st) == (0, 1)

    # ---------- the DESIGNER's own worked diagrams (spielstein.com) ----------
    # An anchor independent of both this package's rules.md and the AbstractPlay
    # reference implementation: two positions read straight off Dieter Stein's
    # rules-page pictures.
    #
    # (1) .../fendo/rules/placement.png — "White may place a new piece on any of
    #     the marked spaces as they are exactly one move away from a friendly
    #     piece in the open area."  White has two pieces, but b7 is sealed inside
    #     a closed 6-cell pocket, so only f3 generates entries; every one of the
    #     21 marked cells needs the full slide (several need the right-angle
    #     turn, e.g. c5 / d1 / g7), and the slide is stopped by pieces (f6, c1)
    #     and by fences (b5|c5, c4|d4, e3|f3).
    st = diagram(white=["b7", "f3"], orange=["f6", "c1"],
                 hfences=["a3/a2", "a5/a4", "b3/b2", "b5/b4", "c2/c1", "d4/d3"],
                 vfences=["b2/c2", "b5/c5", "b6/c6", "b7/c7", "c1/d1", "c4/d4",
                          "d6/e6", "e3/f3"],
                 stock=(5, 5))
    marked = sorted(["g7", "g6", "c5", "d5", "e5", "f5", "g5", "d4", "e4", "f4",
                     "g4", "g3", "c2", "d2", "e2", "f2", "g2", "d1", "e1", "f1",
                     "g1"])
    got = sorted(alg(*(int(x) for x in m[2:].split(",")))
                 for m in G.legal_moves(st) if m.startswith("P@"))
    assert got == marked, (got, marked)
    kinds = [len(o) for _c, o in G.areas(st.board, st.fences)]
    assert sorted(kinds) == [1, 1, 2], kinds        # 2 closed + the open area
    closed = sorted(sorted(alg(i % SIZE, i // SIZE) for i in c)
                    for c, o in G.areas(st.board, st.fences) if len(o) == 1)
    assert closed[0] == ["a1", "a2", "b1", "b2", "c1"], closed[0]   # orange, 5
    assert closed[1] == ["a5", "a6", "a7", "b5", "b6", "b7"], closed[1]  # white, 6
    # b7 is sealed: only the open-area piece f3 may be selected at all
    assert {m.split(">")[0] for m in G.legal_moves(st) if ">" in m} \
        == {cell_name(*cr("f3"))}
    # entry is NOT gated on a legal fence at the target (no fence is built) —
    # c2 accepts a piece even though it is one of the tighter corners
    assert "P@" + cell_name(*cr("c2")) in G.legal_moves(st)

    # (2) .../fendo/rules/example-2.png — "The marked white piece at the bottom
    #     [e1] has no move available and cannot be selected (staying at its
    #     place), because no fences may be legally built on any of the potential
    #     target spaces or on its origin space."  The seven crossed squares are
    #     exactly its reachable set.
    st = diagram(
        white=["c7", "a5", "c5", "g5", "c2", "g2", "e1"],
        orange=["e7", "d5", "a4", "e4", "c3", "a1"],
        hfences=["a2/a1", "a5/a4", "a7/a6", "b3/b2", "b5/b4", "b7/b6", "c2/c1",
                 "c4/c3", "c6/c5", "c7/c6", "d4/d3", "d5/d4", "d7/d6", "e4/e3",
                 "e6/e5", "e7/e6", "f3/f2", "f4/f3", "f6/f5", "f7/f6", "g3/g2",
                 "g5/g4"],
        vfences=["a2/b2", "b2/c2", "b3/c3", "b4/c4", "b5/c5", "b6/c6", "c1/d1",
                 "c2/d2", "c4/d4", "c5/d5", "c7/d7", "d2/e2", "d3/e3", "d5/e5",
                 "e1/f1", "e2/f2", "e7/f7", "f6/g6"],
        stock=(0, 1))
    # the transcription is self-checking: a real Fendo position has exactly one
    # open area and never an empty one
    ar = G.areas(st.board, st.fences)
    assert sum(1 for _c, o in ar if len(o) >= 2) == 1, [len(o) for _c, o in ar]
    assert all(o for _c, o in ar)
    assert sorted(alg(c, r) for (c, r) in reach(st, *cr("e1"))) == \
        ["d1", "d2", "d3", "e2", "e3", "f3", "g3"]
    # ...and not one of those eight squares (the seven above plus e1 itself)
    # offers a legal fence, so e1 contributes no move
    assert not [m for m in G.legal_moves(st)
                if m.startswith(cell_name(*cr("e1")) + ">")], G.legal_moves(st)

    # ------------- shipped generator vs. the slow independent reference -------
    rng = random.Random(159333)
    ref_positions = ref_moves = 0
    for _ in range(10):
        t = G.initial_state()
        for _ply in range(14):
            if G.is_terminal(t):
                break
            fast, slow = G.legal_moves(t), legal_ref(t)
            assert sorted(fast) == sorted(slow), (
                sorted(set(fast) ^ set(slow)), G.serialize(t))
            ref_positions += 1
            ref_moves += len(fast)
            t = G.apply_move(t, rng.choice(fast))
    assert ref_positions >= 100 and ref_moves > 10000, (ref_positions, ref_moves)
    # the reference really is exercising the fence rule (it rejects candidates)
    st = mk({(0, 1): 0, (6, 3): 1}, fences=[("v", 0, 0)])
    assert "0,1>0,1=FENCE_S" not in legal_ref(st)
    # ...and again where the fence rule actually BITES: the loop above only sees
    # the first 14 plies, i.e. the wide-open board where almost every fence is
    # legal.  Cross-check whole games once the board is carved up.
    rng = random.Random(4242)
    late = 0
    for _ in range(4):
        t = G.initial_state()
        while not G.is_terminal(t):
            fast = G.legal_moves(t)
            if len(t.fences) >= 8:
                assert sorted(fast) == sorted(legal_ref(t)), (
                    sorted(set(fast) ^ set(legal_ref(t))), G.serialize(t))
                late += 1
            t = G.apply_move(t, rng.choice(fast))
    assert late >= 150, late

    # -------------------------------------------------- purity & round-trip
    s = G.initial_state()
    before = G.serialize(s)
    G.apply_move(s, "0,3>3,3=FENCE_N")
    assert G.serialize(s) == before
    # The round-trip must be LOSSLESS, and it has to be asserted in this
    # direction.  `serialize(deserialize(d)) == d` is blind to a field that
    # serialize never writes: drop "passes" (or "stock") from the dict and give
    # deserialize a default, and that test still passes — while a live async
    # match, which round-trips through the database on every single move, would
    # forget that a player has passed (no game could ever end on a double pass)
    # or forget how much stock is spent.  So compare STATES, and require the
    # payload to name every field.
    assert {f.name for f in dc_fields(FState)} <= set(G.serialize(G.initial_state()))
    rng = random.Random(11)
    seen_pass = seen_spent = seen_last = False
    for _ in range(20):
        t = G.initial_state()
        while not G.is_terminal(t):
            d = G.serialize(t)
            # survives an actual JSON hop, as the database gives it back
            assert G.deserialize(json.loads(json.dumps(d))) == t
            assert G.serialize(G.deserialize(d)) == d
            seen_pass |= t.passes > 0
            seen_spent |= t.stock != (6, 6)
            seen_last |= t.last is not None
            G.describe_move(t, rng.choice(G.legal_moves(t)))
            t = G.apply_move(t, rng.choice(G.legal_moves(t)))
        d = G.serialize(t)
        assert G.deserialize(json.loads(json.dumps(d))) == t
        assert G.serialize(G.deserialize(d)) == d
    # the round-trip above is only meaningful if it saw non-default values
    assert seen_pass and seen_spent and seen_last, (seen_pass, seen_spent, seen_last)
    # and explicitly, on a hand-built state, so it cannot go untested if random
    # play stops producing passes
    st = mk({(0, 0): 0, (6, 6): 1}, fences=[("v", 0, 0)], stock=(0, 4),
            to_move=1, passes=1)
    st = replace(st, last="0,0>0,0=FENCE_E")
    assert G.deserialize(G.serialize(st)) == st

    # ---------------------------------------------- termination and scoring
    rng = random.Random(2014)
    longest = 0
    normal_ends = 0
    for _ in range(120):
        t = G.initial_state()
        plies = 0
        while not G.is_terminal(t):
            lm4 = G.legal_moves(t)
            assert lm4, "no legal move on a non-terminal state"
            t = G.apply_move(t, rng.choice(lm4))
            plies += 1
            assert plies <= 200, "Fendo cannot exceed 84 fences + 12 entries + passes"
        longest = max(longest, plies)
        a, b = G.scores(t)
        areas = G.areas(t.board, t.fences)
        if t.passes < 2:
            normal_ends += 1
            # every area holds exactly one piece => the 49 cells are partitioned
            assert all(len(o) == 1 for _c, o in areas), areas
            assert a + b == N == 49, (a, b)
            assert a != b                     # 49 is odd: no tie on this path
        assert all(len(o) != 0 for _c, o in areas)   # no empty area, ever
        r = G.returns(t)
        assert r == ([1.0, -1.0] if a > b else [-1.0, 1.0] if b > a else [0.0, 0.0])
        assert sum(r) == 0.0
        cap = G.render(t)["caption"]                # the caption states the result
        assert cap == (f"Red wins {a}-{b}" if a > b else
                       f"Blue wins {b}-{a}" if b > a else f"Draw {a}-{b}"), cap
        assert len(t.fences) <= 2 * SIZE * (SIZE - 1)
    assert normal_ends == 120, normal_ends
    # structural bound: 84 internal edges + 12 stock entries + at most one pass
    # between consecutive non-pass moves
    assert longest <= 2 * SIZE * (SIZE - 1) + 12 + 97, longest

    # an honest draw is what a tie produces (double-pass ending)
    st = mk({(0, 0): 0, (6, 6): 1}, passes=2, over=True)
    assert G.is_terminal(st) and G.scores(st) == (0, 0)
    assert G.returns(st) == [0.0, 0.0]
    # ...but a DECISIVE score must still outrank the pass counter.  Seat 1 has
    # its only piece sealed in a 1-cell pocket and an empty stock, so it must
    # pass; reaching the double-pass ending through apply_move must score 0-1
    # for seat 1, NOT a draw just because the game ended on the counter.
    st = mk({(0, 0): 0, (3, 3): 0, (6, 6): 1},
            fences=[("v", 5, 6), ("h", 6, 5)], stock=(6, 0), to_move=1, passes=1)
    assert G.legal_moves(st) == ["pass"], G.legal_moves(st)
    st = G.apply_move(st, "pass")
    assert st.over and st.passes == 2
    assert G.scores(st) == (0, 1) and G.returns(st) == [-1.0, 1.0]
    assert "Blue wins 1-0" in G.render(st)["caption"], G.render(st)["caption"]

    # ------------------------------------------------------------ heuristic
    h = G.heuristic(G.initial_state())
    assert isinstance(h, list) and len(h) == 2 and h == [0.0, -0.0]
    st = mk({(0, 0): 0, (3, 3): 0, (6, 3): 1}, fences=[("v", 0, 0), ("h", 0, 0)])
    h = G.heuristic(st)
    assert len(h) == 2 and h[0] > 0 > h[1] and abs(h[0]) <= 1.0
    from agp.mcts import MCTSBot                     # forces the rollout cutoff
    mv = MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(
        G, G.initial_state())
    assert mv in G.legal_moves(G.initial_state())

    # -------------------------------------------------------------- render
    spec = G.render(G.initial_state())
    b = spec["board"]
    assert b["type"] == "square" and b["width"] == 7 and b["height"] == 7
    assert b["fences"] == {"h": [], "v": []}
    assert spec["reserve"] == {"0": {"P": 6}, "1": {"P": 6}}
    st = G.apply_move(G.initial_state(), "0,3>0,3=FENCE_N")
    b = G.render(st)["board"]
    assert b["fences"] == {"h": [[0, 3]], "v": []}, b["fences"]
    st = G.apply_move(G.initial_state(), "0,3>2,2=FENCE_E")
    b = G.render(st)["board"]
    assert b["fences"] == {"h": [], "v": [[2, 2]]}, b["fences"]
    # ALL FOUR compass sides, on real moves, against the SPEC.md contract:
    #   h:[c,r] is the edge between (c,r) and (c,r+1)
    #   v:[c,r] is the edge between (c,r) and (c+1,r)
    # and the fence must really block the step it draws, in both directions.
    opp = {"N": "S", "S": "N", "E": "W", "W": "E"}
    for d, want in (("N", {"h": [[3, 3]], "v": []}),
                    ("S", {"h": [[3, 2]], "v": []}),
                    ("E", {"h": [], "v": [[3, 3]]}),
                    ("W", {"h": [], "v": [[2, 3]]})):
        mv = f"0,3>3,3=FENCE_{d}"
        assert mv in G.legal_moves(G.initial_state()), mv
        st = G.apply_move(G.initial_state(), mv)
        assert G.render(st)["board"]["fences"] == want, (d, G.render(st)["board"])
        dc, dr = DIRS[d]
        assert G.blocked(st.fences, 3, 3, d)
        assert G.blocked(st.fences, 3 + dc, 3 + dr, opp[d])
    # a fence is never emitted on the board rim (h needs r <= 5, v needs c <= 5)
    rng = random.Random(84)
    for _ in range(30):
        t = G.initial_state()
        while not G.is_terminal(t):
            t = G.apply_move(t, rng.choice(G.legal_moves(t)))
            f = G.render(t)["board"]["fences"]
            assert all(0 <= c < SIZE and 0 <= r < SIZE - 1 for c, r in f["h"]), f
            assert all(0 <= c < SIZE - 1 and 0 <= r < SIZE for c, r in f["v"]), f
            assert len(f["h"]) + len(f["v"]) == len(t.fences)
    st = mk({(0, 0): 0, (3, 3): 0, (6, 3): 1}, fences=[("v", 0, 0), ("h", 0, 0)])
    assert G.render(st)["board"]["tints"] == {"0,0": "#5a2222"}

    print("fendo selftest OK "
          f"(212-move opening, {checked} reachability cross-checks, "
          f"{ref_positions}+{late} positions vs the slow global fence rule, "
          f"2 designer diagrams, 120 random games, longest {longest} plies)")


if __name__ == "__main__":
    main()
