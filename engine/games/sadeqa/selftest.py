"""Standalone correctness anchor for Sadéqa.

Run with:  PYTHONPATH=. python3 games/sadeqa/selftest.py

Pure stdlib + this game only. Fast. Prints "SELFTEST OK" and exits 0 on
success, nonzero on any failure.

There is NO printed numeric solution for Sadéqa in *Abstract Games* issue 16 --
the two problems on that page ("South to move, capture as many as possible!") are
for the 3x6 games Selus (Massawa) and Sulus Nishtaw, not for Sadéqa. So the
anchor here is (a) the exact starting position from the article's figure, (b)
hand-checked unit cases for each rule branch, and (c) a frozen maximum-capture
value on a constructed position (documented in rules.md).
"""

from __future__ import annotations

import random
import sys

from games.sadeqa.game import (
    Sadeqa, SadeqaState, PIT_ORDER, OWN_PITS, TOTAL_SEEDS,
)

G = Sadeqa()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def eb():
    return {p: 0 for p in PIT_ORDER}


def st(board, warana=None, captured=None, to_move=0, ply=5):
    return SadeqaState(board=dict(board), warana=dict(warana or {}),
                       captured=list(captured or [0, 0]),
                       to_move=to_move, ply=ply)


# ---------------------------------------------------------------------------
# 1. Starting position: 2x10 holes, 4 seeds each, 80 total, 10 legal moves.
# ---------------------------------------------------------------------------
def test_start():
    s = G.initial_state()
    if len(s.board) != 20:
        fail(f"board should have 20 holes, has {len(s.board)}")
    if any(v != 4 for v in s.board.values()):
        fail("every hole must start with 4 seeds")
    if sum(s.board.values()) != TOTAL_SEEDS or TOTAL_SEEDS != 80:
        fail("total seeds must be 80")
    lm = G.legal_moves(s)
    if len(lm) != 10:
        fail(f"South should have 10 opening moves, has {len(lm)}")
    if s.warana:
        fail("no warana at the start")
    # render is a valid RenderSpec
    r = G.render(s)
    if "board" not in r or r["board"]["type"] != "square":
        fail("render board malformed")
    if r["board"]["width"] != 10 or r["board"]["height"] != 2:
        fail("render board dims wrong")


# ---------------------------------------------------------------------------
# 2. Warana creation: last seed makes an OPPONENT hole go 3 -> 4.
#    South plays (9,0)=1 -> lands North's (9,1) which holds 3 -> warana owned S.
# ---------------------------------------------------------------------------
def test_warana_creation():
    b = eb(); b[(9, 0)] = 1; b[(9, 1)] = 3
    s = st(b)
    ns = G.apply_move(s, "9,0")
    if ns.warana.get((9, 1)) != 0:
        fail("opponent hole of 3 should become a warana owned by South")
    if ns.board[(9, 1)] != 4:
        fail("new warana should retain its 4 seeds")
    if ns.captured != [0, 0]:
        fail("creating a warana captures nothing")
    if ns.to_move != 1:
        fail("creating a warana ends the move -> opponent to move")


# ---------------------------------------------------------------------------
# 3. Own-hole 3 -> 4 must NOT create a warana: it relays.
#    South plays (0,0)=1 -> lands South's OWN (1,0) holding 3.
# ---------------------------------------------------------------------------
def test_own_hole_relays():
    b = eb(); b[(0, 0)] = 1; b[(1, 0)] = 3
    s = st(b)
    ns = G.apply_move(s, "0,0")
    if (1, 0) in ns.warana:
        fail("own hole reaching 4 must NOT become a warana")
    if ns.warana:
        fail("no warana should exist after an own-side relay")
    # the 4 seeds were re-lifted and sown onward; the hole is emptied.
    if ns.board[(1, 0)] != 0:
        fail("own 3->4 hole should be re-lifted (0 seeds) by the relay")


# ---------------------------------------------------------------------------
# 4. Capture from opponent's warana + bonus move (mover retains the turn).
# ---------------------------------------------------------------------------
def test_capture_and_bonus():
    b = eb(); b[(4, 0)] = 1; b[(5, 0)] = 3; b[(0, 0)] = 1  # (0,0) = spare move
    s = st(b, warana={(5, 0): 1})   # North owns the warana in South's row
    ns = G.apply_move(s, "4,0")
    if ns.captured != [2, 0]:
        fail(f"capturing a non-empty opponent warana takes 2 seeds, got {ns.captured}")
    if ns.board[(5, 0)] != 2:
        fail("warana of 3 -> drop -> 4 -> capture 2 should retain 2 seeds")
    if ns.to_move != 0:
        fail("a capture grants a bonus move -> same player moves again")


# ---------------------------------------------------------------------------
# 5. Capturing an EMPTY opponent warana takes only 1 seed.
# ---------------------------------------------------------------------------
def test_empty_warana_capture():
    b = eb(); b[(4, 0)] = 1; b[(5, 0)] = 0; b[(0, 0)] = 1
    s = st(b, warana={(5, 0): 1})
    ns = G.apply_move(s, "4,0")
    if ns.captured != [1, 0]:
        fail(f"empty opponent warana yields only 1 seed, got {ns.captured}")
    if ns.board[(5, 0)] != 0:
        fail("empty warana should be 0 after capturing the single dropped seed")


# ---------------------------------------------------------------------------
# 6. Last seed into the MOVER's OWN warana: nothing captured, move ends.
#    Tested via _resolve directly (feeder sits in the opponent's row).
# ---------------------------------------------------------------------------
def test_own_warana_landing():
    b = eb(); b[(6, 1)] = 1; b[(5, 1)] = 2   # (6,1)->(5,1), a South-owned warana
    nb, nw, cap, bonus, mw = G._resolve(b, {(5, 1): 0}, 0, (6, 1), False)
    if cap != 0 or bonus:
        fail("landing in your OWN warana captures nothing and gives no bonus")
    if nb[(5, 1)] != 3:
        fail("own warana just accumulates the dropped seed (2 -> 3)")


# ---------------------------------------------------------------------------
# 7. First-move exception: on ply 0 an opponent hole of 3 does NOT spear.
# ---------------------------------------------------------------------------
def test_first_move_no_warana():
    b = eb(); b[(9, 0)] = 1; b[(9, 1)] = 3
    s = st(b, ply=0)
    ns = G.apply_move(s, "9,0")
    if ns.warana:
        fail("no warana may be created on the very first move of the game")


# ---------------------------------------------------------------------------
# 8. Honest draw reached through apply_move (equal scores, board locked).
#    South spears/captures the last loose seeds into a 2-2 tie.
# ---------------------------------------------------------------------------
def test_honest_draw():
    b = eb(); b[(4, 0)] = 1; b[(5, 0)] = 3
    s = st(b, warana={(5, 0): 1})     # North owns the warana of 3
    ns = G.apply_move(s, "4,0")
    if not ns.done:
        fail("board should be locked (no loose seeds, no legal moves)")
    if G.scores(ns) != [2, 2]:
        fail(f"expected a 2-2 tie, got {G.scores(ns)}")
    if G.returns(ns) != [0.0, 0.0]:
        fail("an equal split must be an honest DRAW, not a fabricated winner")


# ---------------------------------------------------------------------------
# 9. Frozen max-capture over a full TURN (initial move + bonus chain).
#    Constructed position: three North-owned warana of 3 in South's row, each fed
#    by a lone seed. South spears all three via successive bonus moves = 6 seeds.
#    (A SINGLE apply_move captures at most 2, because landing in a warana ends the
#    move; the extra captures come from the bonus moves.)
# ---------------------------------------------------------------------------
FROZEN_TURN_MAX = 6


def _turn_max(state, player, depth=0):
    if depth > 12 or state.done or state.to_move != player:
        return 0
    base = state.captured[player]
    best = 0
    for mv in G.legal_moves(state):
        nx = G.apply_move(state, mv)
        gained = nx.captured[player] - base
        if gained > 0 and nx.to_move == player and not nx.done:
            best = max(best, gained + _turn_max(nx, player, depth + 1))
        else:
            best = max(best, gained)
    return best


def test_frozen_max_capture():
    b = eb()
    warana = {(2, 0): 1, (5, 0): 1, (8, 0): 1}
    for p in warana:
        b[p] = 3
    for feeder in [(1, 0), (4, 0), (7, 0)]:
        b[feeder] = 1
    b[(0, 0)] = 1
    s = st(b, warana=warana)
    # a capturing move must exist
    if not any(G.apply_move(s, mv).captured[0] > 0 for mv in G.legal_moves(s)):
        fail("no capturing move found in the constructed capture position")
    got = _turn_max(s, 0)
    if got != FROZEN_TURN_MAX:
        fail(f"frozen max-capture drift: expected {FROZEN_TURN_MAX}, got {got}")


# ---------------------------------------------------------------------------
# 10. Random games terminate and conserve seeds (board + captured == 80).
# ---------------------------------------------------------------------------
def test_random_termination():
    random.seed(20031  )
    for _ in range(120):
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            lm = G.legal_moves(s)
            if not lm:
                fail("non-terminal state with no legal moves")
            s = G.apply_move(s, random.choice(lm))
            if sum(s.board.values()) + sum(s.captured) != TOTAL_SEEDS:
                fail("seed conservation violated")
            steps += 1
            if steps > 6000:
                fail("game failed to terminate under the ply cap")
        r = G.returns(s)
        if r not in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]):
            fail(f"bad returns vector {r}")


def main():
    test_start()
    test_warana_creation()
    test_own_hole_relays()
    test_capture_and_bonus()
    test_empty_warana_capture()
    test_own_warana_landing()
    test_first_move_no_warana()
    test_honest_draw()
    test_frozen_max_capture()
    test_random_termination()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
