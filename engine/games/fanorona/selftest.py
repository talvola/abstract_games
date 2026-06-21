"""Standalone correctness anchor for Fanorona.

Run:  PYTHONPATH=. python3 games/fanorona/selftest.py

Pure stdlib + the agp package only. Asserts:
  * conformance (round-trip, purity, termination on a short random rollout),
  * diagonal adjacency only on strong intersections,
  * the standard opening array & must-capture-first rule,
  * approach capture removes the whole in-line enemy run,
  * withdrawal capture removes the in-line enemy run behind,
  * the must-capture rule (no paika when a capture exists),
  * the chain rules: no two consecutive steps in the same direction, and
    no revisiting a point already visited this turn.
Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
"""

from __future__ import annotations

import json
import os
import random
import sys

from agp.conformance import check  # type: ignore
from games.fanorona.game import (
    Fanorona,
    FanoronaState,
    _neighbours,
    _strong,
    _start_board,
)


def _board(pairs):
    """pairs: dict (c,r)->player -> board dict."""
    return dict(pairs)


def main() -> int:
    g = Fanorona()

    # --- conformance -----------------------------------------------------
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "manifest.json")) as f:
        manifest = json.load(f)
    rep = check(g, manifest, games=3, seed=7)
    assert rep.ok, f"conformance failed: {rep.messages if hasattr(rep, 'messages') else rep}"

    # --- adjacency: diagonals only on strong intersections ---------------
    assert _strong(0, 0) and _strong(4, 2) and _strong(2, 0)
    assert not _strong(1, 0) and not _strong(0, 1)
    # a strong centre point has all 8 neighbours
    nb = set(_neighbours(4, 2))
    assert (1, 1) in nb and (1, -1) in nb and (-1, 1) in nb and (-1, -1) in nb
    assert len(nb) == 8
    # a weak point has only the 4 orthogonals
    nb_weak = set(_neighbours(1, 2))
    assert (1, 1) not in nb_weak and (1, -1) not in nb_weak
    assert all(d in [(1, 0), (-1, 0), (0, 1), (0, -1)] for d in nb_weak)
    # corner-ish strong point (0,0): only on-board diagonals/orthogonals
    nb00 = set(_neighbours(0, 0))
    assert (1, 1) in nb00 and (-1, -1) not in nb00 and (1, 0) in nb00 and (0, 1) in nb00

    # --- opening array ---------------------------------------------------
    b0 = _start_board()
    assert (4, 2) not in b0, "centre must start empty"
    assert len(b0) == 44, "44 pieces total"
    assert sum(1 for v in b0.values() if v == 0) == 22
    assert sum(1 for v in b0.values() if v == 1) == 22
    # bottom two rows all White, top two all Black
    assert all(b0[(c, r)] == 0 for c in range(9) for r in (0, 1))
    assert all(b0[(c, r)] == 1 for c in range(9) for r in (3, 4))
    # middle clash row alternation
    assert b0[(0, 2)] == 1 and b0[(1, 2)] == 0 and b0[(3, 2)] == 0 and b0[(5, 2)] == 1

    # --- must-capture first: opening has captures, so no paika allowed ----
    s0 = g.initial_state()
    moves0 = g.legal_moves(s0)
    assert moves0, "opening must have legal moves"
    # every opening move must be a capture (touches the centre or removes a piece)
    for m in moves0:
        nb_state = g.apply_move(s0, m)
        assert len(nb_state.board) < len(s0.board), f"opening move {m} should capture"

    # === APPROACH capture: move toward a line of enemies =================
    # White at (1,2) moves to empty (2,2); enemies at (3,2),(4,2),(5,2),
    # then a gap at (6,2). Approach removes (3,2),(4,2),(5,2) only.
    bA = _board({(1, 2): 0, (3, 2): 1, (4, 2): 1, (5, 2): 1})
    sA = FanoronaState(board=bA, to_move=0)
    legalA = g.legal_moves(sA)
    assert "1,2>2,2" in legalA, f"approach move missing: {legalA}"
    rA = g.apply_move(sA, "1,2>2,2")
    assert (2, 2) in rA.board and rA.board[(2, 2)] == 0
    assert (3, 2) not in rA.board and (4, 2) not in rA.board and (5, 2) not in rA.board
    assert (1, 2) not in rA.board

    # === WITHDRAWAL capture: move away from an adjacent enemy line ========
    # White at (4,2); enemies behind it at (3,2),(2,2),(1,2) then gap (0,2).
    # White withdraws to (5,2): removes (3,2),(2,2),(1,2).
    bWd = _board({(4, 2): 0, (3, 2): 1, (2, 2): 1, (1, 2): 1})
    sWd = FanoronaState(board=bWd, to_move=0)
    legalW = g.legal_moves(sWd)
    assert "4,2>5,2" in legalW, f"withdrawal move missing: {legalW}"
    rW = g.apply_move(sWd, "4,2>5,2")
    assert (5, 2) in rW.board
    assert (3, 2) not in rW.board and (2, 2) not in rW.board and (1, 2) not in rW.board

    # === must-capture rule: paika illegal when a capture exists ==========
    # Same approach board: a quiet move like (1,2)->(1,1) is NOT in legal moves.
    assert "1,2>1,1" not in legalA
    # but on a board with NO captures, paika is legal
    bP = _board({(0, 0): 0, (8, 4): 1})
    sP = FanoronaState(board=bP, to_move=0)
    legalP = g.legal_moves(sP)
    assert legalP and all("=" not in m for m in legalP)
    rP = g.apply_move(sP, legalP[0])
    assert len(rP.board) == 2, "paika removes nothing"

    # === ambiguous step: both approach and withdrawal available ==========
    # White at (4,2) -> (5,2): enemy at (6,2) (approach) AND enemy at (3,2)
    # (withdrawal). Both choices must be offered with =A/=W suffixes.
    bAW = _board({(4, 2): 0, (6, 2): 1, (3, 2): 1})
    sAW = FanoronaState(board=bAW, to_move=0)
    lAW = g.legal_moves(sAW)
    assert "4,2>5,2=A" in lAW and "4,2>5,2=W" in lAW, f"ambiguous choices: {lAW}"
    rApp = g.apply_move(sAW, "4,2>5,2=A")
    assert (6, 2) not in rApp.board and (3, 2) in rApp.board
    rWit = g.apply_move(sAW, "4,2>5,2=W")
    assert (3, 2) not in rWit.board and (6, 2) in rWit.board

    # === chain: no two consecutive steps in the same direction ===========
    # White (0,2); enemies at (2,2),(4,2) (approach east), and after landing
    # at (1,2) a further east capture would repeat the direction -> forbidden.
    # Build a position where an east capture lands, and a *second east* capture
    # geometrically exists but must be excluded.
    bChain = _board({(0, 2): 0, (2, 2): 1, (4, 2): 1, (6, 2): 1})
    sChain = FanoronaState(board=bChain, to_move=0)
    # First step east (0,2)->(1,2) approach removes (2,2). After that, the
    # landed piece at (1,2): another east step (1,2)->? toward (3,2)... but
    # (2,2) gone; the enemies (4,2),(6,2) are not adjacent-in-line from (1,2)
    # via one empty step that captures without repeating east. We assert the
    # encoded multi-step moves never repeat a direction.
    for m in g.legal_moves(sChain):
        cells = [c.split("=")[0] for c in m.split(">")]
        pts = [tuple(int(x) for x in c.split(",")) for c in cells]
        dirs = [(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                for i in range(len(pts) - 1)]
        for i in range(len(dirs) - 1):
            assert dirs[i] != dirs[i + 1], f"repeated direction in {m}"
        # no revisited cell within a turn
        assert len(set(pts)) == len(pts), f"revisited cell in {m}"

    # === explicit two-capture chain with a direction change ==============
    # White at (1,1). Enemy east at (3,1): step (1,1)->(2,1) approaches and
    # removes (3,1). Then CHANGE direction (north): step (2,1)->(2,2)
    # approaches and removes (2,3). The chain "1,1>2,1>2,2" must be legal and
    # must clear both enemies.
    bC2 = _board({(1, 1): 0, (3, 1): 1, (2, 3): 1})
    sC2 = FanoronaState(board=bC2, to_move=0)
    moves2 = g.legal_moves(sC2)
    chained = [m for m in moves2 if len(m.split(">")) >= 3]
    assert "1,1>2,1>2,2" in chained, f"expected the 2-step chain, got {moves2}"
    rc = g.apply_move(sC2, "1,1>2,1>2,2")
    assert (3, 1) not in rc.board and (2, 3) not in rc.board
    assert sum(1 for v in rc.board.values() if v == 1) == 0
    # the chain must change direction: (2,1) east-again would repeat -> absent
    for m in chained:
        cells = [tuple(int(x) for x in c.split("=")[0].split(",")) for c in m.split(">")]
        dirs = [(cells[i + 1][0] - cells[i][0], cells[i + 1][1] - cells[i][1])
                for i in range(len(cells) - 1)]
        for i in range(len(dirs) - 1):
            assert dirs[i] != dirs[i + 1]

    # === no-revisit within a turn =======================================
    # White (0,0) strong; enemies set so a square path 0,0>1,0>1,1>0,1 captures
    # at each step. The chain must NOT continue 0,1>0,0 (revisiting the start),
    # so no legal move may contain a repeated cell.
    bNR = _board({(0, 0): 0, (2, 0): 1, (1, 2): 1, (2, 1): 1})
    sNR = FanoronaState(board=bNR, to_move=0)
    movesNR = g.legal_moves(sNR)
    assert "0,0>1,0>1,1>0,1" in movesNR, f"square chain missing: {movesNR}"
    for m in movesNR:
        pts = [tuple(int(x) for x in c.split("=")[0].split(",")) for c in m.split(">")]
        assert len(set(pts)) == len(pts), f"revisited cell in {m}"
        # and no legal continuation returns to the start (0,0)
        assert pts.count((0, 0)) == 1

    # === win by annihilation ============================================
    bWin = _board({(1, 2): 0, (3, 2): 1})
    sWin = FanoronaState(board=bWin, to_move=0)
    rWin = g.apply_move(sWin, "1,2>2,2")
    assert g.is_terminal(rWin)
    assert g.returns(rWin) == [1.0, -1.0]

    # --- serialize round-trip on a mid-game state ------------------------
    rng = random.Random(123)
    s = g.initial_state()
    for _ in range(20):
        if g.is_terminal(s):
            break
        ms = g.legal_moves(s)
        s = g.apply_move(s, rng.choice(ms))
    d = g.serialize(s)
    assert g.serialize(g.deserialize(d)) == d

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
