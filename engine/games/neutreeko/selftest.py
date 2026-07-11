#!/usr/bin/env python3
"""Standalone correctness anchor for Neutreeko. Pure stdlib + agp only.

Run:  PYTHONPATH=. python3 games/neutreeko/selftest.py

Anchors (all against www.neutreeko.net, the designer's official site):
  * the official starting position (Black b1,d1,c4; White b5,d5,c2 — from
    the official setup figure) and Black moving first,
  * the exact 14-move legal-move set of the starting position (hand-derived,
    exercises slide-until-blocked in all 8 directions),
  * slide exactness: as far as possible, no stopping short, an immediately
    blocked direction is no move,
  * the official "Perfect Neutreeko opening play" main line (neutr_open.txt):
    all 16 plies of the published DRAW line replay legally with no premature
    terminal,
  * two published solve anchors from the same file, verified by a bounded
    win-distance search: after 1.b1-c1 c2-c3 2.c1-a3 b5-c5 3.d1-d4 c5-b4
    4.d4-c5 d5-d1 5.a3-a5 b4-b5 6.c5-a3 c3-b4 7.c4-a2 d1-a4 then
      - 8.a2-a1 b4-c5 "<08>": White forces a win in exactly 8 plies,
      - 8.a2-d5 b4-e1 9.a5-d2 "<08>": Black forces a win in exactly 8 plies
    (win within 8 plies TRUE, within 6 FALSE — exact distance 8),
  * win detection in all four line directions; the row must be CONNECTED,
  * the official threefold-repetition draw (a shuttle cycle),
  * the PLY_CAP backstop draw,
  * conformance (random playouts terminate).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.conformance import check  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("neutreeko_game", os.path.join(_HERE, "game.py"))
_mod = importlib.util.module_from_spec(_spec)
sys.modules["neutreeko_game"] = _mod
_spec.loader.exec_module(_mod)

Neutreeko = _mod.Neutreeko


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def alg2move(a):
    """'b1-c1' -> '1,0>2,0' (file a..e = col 0..4, rank 1..5 = row 0..4)."""
    f, t = a.split("-")
    cc = lambda x: f"{'abcde'.index(x[0])},{int(x[1]) - 1}"  # noqa: E731
    return f"{cc(f)}>{cc(t)}"


# ---------- bounded win-distance search (bitmask, for the solve anchors) ----
def _idx(c, r):
    return r * 5 + c


_RAYS = []
_DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
for _i in range(25):
    _c, _r = _i % 5, _i // 5
    _rays = []
    for _dc, _dr in _DIRS:
        _ray = []
        _nc, _nr = _c + _dc, _r + _dr
        while 0 <= _nc < 5 and 0 <= _nr < 5:
            _ray.append(1 << _idx(_nc, _nr))
            _nc += _dc
            _nr += _dr
        if _ray:
            _rays.append(_ray)
    _RAYS.append(_rays)

_ROWSET = set()
for _r in range(5):
    for _c in range(5):
        for _dc, _dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
            _c2, _r2 = _c + 2 * _dc, _r + 2 * _dr
            if 0 <= _c2 < 5 and 0 <= _r2 < 5:
                _ROWSET.add((1 << _idx(_c, _r)) | (1 << _idx(_c + _dc, _r + _dr))
                            | (1 << _idx(_c2, _r2)))


def _gen(own, opp):
    occ = own | opp
    out = []
    m = own
    while m:
        fb = m & -m
        m ^= fb
        for ray in _RAYS[fb.bit_length() - 1]:
            dest = 0
            for b in ray:
                if occ & b:
                    break
                dest = b
            if dest:
                out.append(fb | dest)
    return out


def _wins_within(own, opp, k, memo):
    """Side to move (mask `own`) can force its own 3-row within k plies."""
    if k <= 0:
        return False
    key = (own, opp, k, 1)
    v = memo.get(key)
    if v is not None:
        return v
    succ = []
    for mv in _gen(own, opp):
        nown = own ^ mv
        if nown in _ROWSET:
            memo[key] = True
            return True
        succ.append(nown)
    res = False
    if k >= 2:
        for nown in succ:
            if _loses_within(opp, nown, k - 1, memo):
                res = True
                break
    memo[key] = res
    return res


def _loses_within(own, opp, k, memo):
    """Side to move (mask `own`) is forced to lose within k plies."""
    key = (own, opp, k, 0)
    v = memo.get(key)
    if v is not None:
        return v
    ms = _gen(own, opp)
    if not ms:
        memo[key] = True  # stuck loses (unreachable in practice)
        return True
    if k <= 0:
        memo[key] = False
        return False
    res = True
    for mv in ms:
        nown = own ^ mv
        if nown in _ROWSET or not _wins_within(opp, nown, k - 1, memo):
            res = False
            break
    memo[key] = res
    return res


def _masks(state):
    b = w = 0
    for (c, r), p in state.board.items():
        if p == 0:
            b |= 1 << _idx(c, r)
        else:
            w |= 1 << _idx(c, r)
    return b, w


# The official perfect-play main line (neutr_open.txt), plies 1..14.
MAIN14 = ["b1-c1", "c2-c3", "c1-a3", "b5-c5", "d1-d4", "c5-b4", "d4-c5",
          "d5-d1", "a3-a5", "b4-b5", "c5-a3", "c3-b4", "c4-a2", "d1-a4"]


def replay(g, algs, start=None):
    s = start if start is not None else g.initial_state()
    for i, a in enumerate(algs):
        m = alg2move(a)
        if m not in g.legal_moves(s):
            fail(f"official move {i + 1} ({a} = {m}) not legal")
        s = g.apply_move(s, m)
        if g.is_terminal(s):
            fail(f"premature terminal after official move {i + 1} ({a})")
    return s


def main():
    g = Neutreeko()

    # --- conformance ---
    with open(os.path.join(_HERE, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = check(g, manifest, games=30, seed=7)
    if not rep.ok:
        fail(f"conformance:\n{rep}")

    # --- official starting position ---
    s0 = g.initial_state()
    if g.current_player(s0) != 0:
        fail("Black (0) must move first")
    want = {(1, 0): 0, (3, 0): 0, (2, 3): 0,   # Black b1, d1, c4
            (1, 4): 1, (3, 4): 1, (2, 1): 1}   # White b5, d5, c2
    if s0.board != want:
        fail(f"starting position wrong: {s0.board}")
    if g.is_terminal(s0):
        fail("start must not be terminal")

    # --- exact legal-move set at the start (hand-derived, 14 moves) ---
    expect = {
        # b1: a1, c1 (blocked by d1), b4 (blocked by b5), a2; NE blocked by c2
        "1,0>0,0", "1,0>2,0", "1,0>1,3", "1,0>0,1",
        # d1: c1 (blocked by b1), e1, d4 (blocked by d5), e2; NW blocked by c2
        "3,0>2,0", "3,0>4,0", "3,0>3,3", "3,0>4,1",
        # c4: c5, c3 (blocked by c2), a4, e4, e2, a2; NE/NW blocked by d5/b5
        "2,3>2,4", "2,3>2,2", "2,3>0,3", "2,3>4,3", "2,3>4,1", "2,3>0,1",
    }
    got = set(g.legal_moves(s0))
    if got != expect:
        fail(f"start legal moves wrong:\n missing={expect - got}\n extra={got - expect}")

    # --- slide exactness units ---
    b = {(0, 0): 0}
    if _mod._slide_dest(b, 0, 0, 1, 0) != (4, 0):
        fail("open slide right from a1 must reach e1 (no stopping short)")
    if _mod._slide_dest(b, 0, 0, 1, 1) != (4, 4):
        fail("open diagonal slide from a1 must reach e5")
    b = {(0, 0): 0, (3, 0): 1}
    if _mod._slide_dest(b, 0, 0, 1, 0) != (2, 0):
        fail("slide must stop on the square before a blocker")
    b = {(0, 0): 0, (1, 0): 1}
    if _mod._slide_dest(b, 0, 0, 1, 0) is not None:
        fail("an immediately blocked direction is not a move")
    if _mod._slide_dest(b, 0, 0, -1, 0) is not None:
        fail("sliding off the board edge is not a move")

    # --- win detection: connected 3-in-a-row, all four directions ---
    W = _mod._has_row
    mk = lambda cells, others: {c: 0 for c in cells} | {c: 1 for c in others}  # noqa: E731
    inert = [(4, 4), (3, 3), (0, 4)]
    if not W(mk([(1, 1), (2, 1), (3, 1)], inert), 0):
        fail("horizontal row must win")
    if not W(mk([(2, 0), (2, 1), (2, 2)], inert), 0):
        fail("vertical row must win")
    if not W(mk([(0, 0), (1, 1), (2, 2)], inert), 0):
        fail("NE diagonal row must win")
    if not W(mk([(0, 2), (1, 1), (2, 0)], inert), 0):
        fail("NW diagonal row must win")
    if W(mk([(0, 0), (2, 0), (4, 0)], inert), 0):
        fail("a non-connected line must NOT win (the row must be connected)")
    if W(mk([(0, 0), (1, 0), (3, 0)], inert), 0):
        fail("a gapped triple must NOT win")
    if W(mk([(0, 0), (1, 1), (2, 1)], inert), 0):
        fail("a bent triple must NOT win")
    if W(dict(_mod.START), 0) or W(dict(_mod.START), 1):
        fail("the starting position must not contain a row")

    # --- win as an event, via apply_move ---
    # Black a1,a2 + c3; c3 slides west to a3 completing the a-file column.
    s = g.deserialize({
        "board": {"0,0": 0, "0,1": 0, "2,2": 0, "4,0": 1, "4,2": 1, "3,4": 1},
        "to_move": 0, "winner": None, "draw": False, "draw_reason": None,
        "ply": 10, "history": {}})
    if "2,2>0,2" not in g.legal_moves(s):
        fail("expected c3-a3 to be legal")
    s2 = g.apply_move(s, "2,2>0,2")
    if s2.winner != 0 or not g.is_terminal(s2) or g.returns(s2) != [1.0, -1.0]:
        fail("completing a column must be an immediate Black win")

    # --- the official 16-ply perfect-play DRAW line replays legally ---
    s = replay(g, MAIN14 + ["a2-d5", "a4-d1"])
    if s.ply != 16:
        fail("draw line should reach ply 16")

    # --- solve anchors from the official analysis (both <08> lines) ---
    # After ...15.a2-a1 16.b4-c5 the file gives <08>: White wins in 8 plies.
    s = replay(g, MAIN14 + ["a2-a1", "b4-c5"])
    if s.to_move != 0:
        fail("anchor 1: Black should be to move")
    bm, wm = _masks(s)
    memo = {}
    if _loses_within(bm, wm, 6, memo):
        fail("anchor 1: White must NOT win within 6 plies")
    if not _loses_within(bm, wm, 8, memo):
        fail("anchor 1: White must force a win within 8 plies (<08>)")
    # After ...15.a2-d5 16.b4-e1 17.a5-d2 the file gives <08>: Black wins in 8.
    s = replay(g, MAIN14 + ["a2-d5", "b4-e1", "a5-d2"])
    if s.to_move != 1:
        fail("anchor 2: White should be to move")
    bm, wm = _masks(s)
    memo = {}
    if _loses_within(wm, bm, 6, memo):
        fail("anchor 2: Black must NOT win within 6 plies")
    if not _loses_within(wm, bm, 8, memo):
        fail("anchor 2: Black must force a win within 8 plies (<08>)")

    # --- threefold repetition draw (the official draw rule) ---
    # Black shuttles a1<->a3 (blocked by White a4); White shuttles e5<->d5
    # (blocked by its own c5). 4 plies return to the same position+to_move.
    base = {"board": {"0,0": 0, "4,0": 0, "4,2": 0,
                      "0,3": 1, "2,4": 1, "4,4": 1},
            "to_move": 0, "winner": None, "draw": False, "draw_reason": None,
            "ply": 0, "history": {}}
    s = g.deserialize(base)
    s.history[_mod._pos_key(s.board, 0)] = 1  # seed: current pos seen once
    cycle = ["0,0>0,2", "4,4>3,4", "0,2>0,0", "3,4>4,4"]
    for lap in range(2):
        for i, m in enumerate(cycle):
            if g.is_terminal(s):
                fail(f"repetition shuttle terminal too early (lap {lap} step {i})")
            if m not in g.legal_moves(s):
                fail(f"shuttle move {m} not legal (lap {lap} step {i})")
            s = g.apply_move(s, m)
            if s.winner is not None:
                fail("shuttle must not produce a win")
    if not (s.draw and s.draw_reason == "repetition"):
        fail("third occurrence of the same position must be a repetition draw")
    if g.returns(s) != [0.0, 0.0]:
        fail("a repetition draw must return [0, 0] — an honest draw")

    # --- PLY_CAP backstop draw ---
    s = g.deserialize({**base, "ply": _mod.PLY_CAP - 1})
    s2 = g.apply_move(s, "0,0>0,2")
    if not (s2.draw and s2.draw_reason == "cap"):
        fail("ply-cap backstop draw not triggered")
    if g.returns(s2) != [0.0, 0.0]:
        fail("cap draw must return [0, 0]")

    # --- notation & serialization ---
    s0 = g.initial_state()
    if g.describe_move(s0, "1,0>2,0") != "b1-c1":
        fail("describe_move should give algebraic 'b1-c1'")
    s = g.apply_move(s0, "1,0>2,0")
    d = g.serialize(s)
    if g.serialize(g.deserialize(d)) != d:
        fail("serialize does not round-trip")

    # --- render probe ---
    spec = g.render(g.initial_state())
    if spec["board"] != {"type": "square", "width": 5, "height": 5}:
        fail("render board spec wrong")
    if len(spec["pieces"]) != 6:
        fail("render should show 6 pieces")

    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
