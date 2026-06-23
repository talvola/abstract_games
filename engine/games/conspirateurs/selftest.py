"""Conspirateurs self-test (pure stdlib: imports only `agp` + this game).

CORRECTNESS ANCHOR. There is no published perft for Conspirateurs, so the anchor
is a set of baked rule assertions verified against authoritative sources
(Wikipedia "Conspirateurs"; the nestorgames 2018 rulebook; Ludii).

NOTE ON THE BRIEF: the original task summary described chess-QUEEN movement with
a "may not land adjacent to another man" constraint. That is NOT how Conspirateurs
is actually played. The real game is a HALMA-style step-and-jump RACE with NO
capturing and NO adjacency restriction. These asserts encode the REAL rules:

  (1) Movement is a STEP to an adjacent empty cell, OR a JUMP over one adjacent
      occupied man (friend or foe) onto the empty cell beyond, with optional
      multi-jump chains. (There is NO queen sliding and NO "must land isolated"
      rule -- a man routinely lands next to others.)
  (2) There is NO capturing -- a jumped man stays on the board.
  (3) A man that BEGINS the turn on a sanctuary may not move.
  (4) GOAL: get ALL your men onto the corner/edge sanctuaries; the first player
      with all men sheltered wins.

Run:  PYTHONPATH=. python3 games/conspirateurs/selftest.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from games.conspirateurs.game import (   # noqa: E402
    Conspirateurs, CState, N, MEN, CENTER_AREA, SANCTUARIES,
)


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        raise SystemExit(1)


def cellset(moves):
    return set(moves)


g = Conspirateurs()

# ---------------------------------------------------------------------------
# Board geometry sanity.
# ---------------------------------------------------------------------------
check(N == 17, "board is 17x17")
check(MEN == 20, "20 men per player (in play; the box supplies 21 cones, one spare)")
check(len(CENTER_AREA) == 45, f"central drop area is 9x5=45 cells, got {len(CENTER_AREA)}")
# central area is exactly the 9x5 block centred on (8,8)
check((8, 8) in CENTER_AREA, "centre cell (8,8) is in the drop zone")
check(all(4 <= c <= 12 and 6 <= r <= 10 for (c, r) in CENTER_AREA),
      "drop zone is cols 4..12, rows 6..10")
# sanctuaries are all on the perimeter, none overlap the drop zone
check(len(SANCTUARIES) >= MEN, "enough sanctuaries to shelter a full side")
check(all(c in (0, N - 1) or r in (0, N - 1) for (c, r) in SANCTUARIES),
      "every sanctuary lies on the board perimeter")
check(not (SANCTUARIES & CENTER_AREA), "sanctuaries never overlap the drop zone")
# four corners are shelters (shared / not assigned per player)
for corner in [(0, 0), (16, 0), (0, 16), (16, 16)]:
    check(corner in SANCTUARIES, f"corner {corner} is a sanctuary")

# ---------------------------------------------------------------------------
# (A) Drop phase: legal moves are exactly the vacant central cells; players
#     alternate; no movement is offered until both have placed all men.
# ---------------------------------------------------------------------------
s = g.initial_state()
check(g.current_player(s) == 0, "Black drops first")
check(cellset(g.legal_moves(s)) == {f"{c},{r}" for (c, r) in CENTER_AREA},
      "opening drop moves == all 45 central cells")

# Drop all 40 men (20 each) by walking through apply_move with deterministic picks.
order = sorted(CENTER_AREA)            # 45 cells; we will use the first 40 (5 left free)
idx = 0
while (s.dropped[0] < MEN or s.dropped[1] < MEN):
    legal = set(g.legal_moves(s))
    # pick the next cell in canonical order that is still legal
    pick = None
    while idx < len(order):
        cand = f"{order[idx][0]},{order[idx][1]}"
        if cand in legal:
            pick = cand
            break
        idx += 1
    check(pick is not None, "a legal drop cell exists during the drop phase")
    s = g.apply_move(s, pick)

check(s.dropped == (MEN, MEN), f"both sides dropped {MEN}, got {s.dropped}")
check(sum(1 for v in s.board.values() if v == 0) == MEN, "Black placed 20 men")
check(sum(1 for v in s.board.values() if v == 1) == MEN, "White placed 20 men")
# 40 men into the 45-cell centre leaves exactly 5 cells free.
check(len(s.board) == 2 * MEN == 40, f"40 men placed into the 45-cell centre, got {len(s.board)}")
check(len(CENTER_AREA) - len(s.board) == 5, "5 central cells remain free after dropping")
# now we are in the MOVE phase
check(not g.is_terminal(s), "not terminal after the drop phase")
mv = g.legal_moves(s)
check(len(mv) > 0, "move-phase moves exist")
check(all(">" in m for m in mv), "every move-phase move is a from>to(>..) path")

# ---------------------------------------------------------------------------
# (B) STEP: a man moves to any of the 8 adjacent EMPTY cells. Build a tiny
#     isolated position so the move set is exactly predictable.
# ---------------------------------------------------------------------------
s2 = CState(board={(5, 5): 0}, to_move=0, dropped=(MEN, MEN))
steps = set(g.legal_moves(s2))
expected_steps = {f"5,5>{5 + dc},{5 + dr}"
                  for dc in (-1, 0, 1) for dr in (-1, 0, 1) if (dc, dr) != (0, 0)}
check(steps == expected_steps, f"a lone man at 5,5 has the 8 king-steps, got {steps}")

# A man may NOT step onto an occupied cell.
s3 = CState(board={(5, 5): 0, (5, 6): 1}, to_move=0, dropped=(MEN, MEN))
check("5,5>5,6" not in set(g.legal_moves(s3)), "cannot step onto an occupied cell")

# ---------------------------------------------------------------------------
# (C) JUMP over a neighbour (friend OR foe) onto the empty cell beyond; the
#     jumped man is NOT captured (stays on the board). NO capturing.
# ---------------------------------------------------------------------------
s4 = CState(board={(5, 5): 0, (6, 5): 1}, to_move=0, dropped=(MEN, MEN))
moves4 = set(g.legal_moves(s4))
check("5,5>7,5" in moves4, "can jump east over an enemy at 6,5 onto 7,5")
after4 = g.apply_move(s4, "5,5>7,5")
check(after4.board.get((7, 5)) == 0, "jumper lands on 7,5")
check(after4.board.get((6, 5)) == 1, "jumped enemy man is NOT captured (still at 6,5)")
check((5, 5) not in after4.board, "jumper vacated its start cell")
check(len(after4.board) == 2, "no piece removed by a jump")

# A blocked landing (cell beyond is occupied) yields no jump there.
s5 = CState(board={(5, 5): 0, (6, 5): 1, (7, 5): 1}, to_move=0, dropped=(MEN, MEN))
check("5,5>7,5" not in set(g.legal_moves(s5)), "cannot jump when the landing cell is occupied")

# Multi-jump: hop east over 6,5 to 7,5, then north over 7,4 to 7,3. Moves are
# emitted as source>destination (the platform's click-path), so BOTH the
# single-hop destination 7,5 and the chained destination 7,3 appear, and the man
# may stop after either hop.
s6 = CState(board={(5, 5): 0, (6, 5): 1, (7, 4): 1}, to_move=0, dropped=(MEN, MEN))
moves6 = set(g.legal_moves(s6))
check("5,5>7,5" in moves6, "single-hop destination 7,5 available")
check("5,5>7,3" in moves6, "chained-jump destination 7,3 available (stop after any hop)")
# the chained move actually relocates the man to 7,3, capturing nothing
after6 = g.apply_move(s6, "5,5>7,3")
check(after6.board.get((7, 3)) == 0, "multi-jump lands the man on 7,3")
check(after6.board.get((6, 5)) == 1 and after6.board.get((7, 4)) == 1,
      "both jumped-over men remain on the board (no capture)")

# ---------------------------------------------------------------------------
# (D) A man that BEGINS the turn on a sanctuary may NOT move.
# ---------------------------------------------------------------------------
corner = (0, 0)
check(corner in SANCTUARIES, "0,0 is a sanctuary")
s7 = CState(board={corner: 0, (5, 5): 0}, to_move=0, dropped=(MEN, MEN))
m7 = set(g.legal_moves(s7))
check(not any(mv.startswith("0,0>") for mv in m7), "a man already in a sanctuary cannot move")
check(any(mv.startswith("5,5>") for mv in m7), "the non-sheltered man can still move")

# ---------------------------------------------------------------------------
# (E) WIN: first player with ALL men sheltered wins. Place 19 of Black's men on
#     sanctuaries and one man one step away; move it home (20th) -> Black wins.
# ---------------------------------------------------------------------------
shelters = sorted(SANCTUARIES)
home_pre = shelters[:MEN - 1]               # MEN-1 = 19 distinct sanctuary cells
# find a sanctuary cell with an adjacent EMPTY non-sanctuary cell to step in from
last_shelter = shelters[MEN - 1]
lc, lr = last_shelter
approach = None
for dc, dr in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
    ac, ar = lc + dc, lr + dr
    if 0 <= ac < N and 0 <= ar < N and (ac, ar) not in SANCTUARIES:
        approach = (ac, ar)
        break
check(approach is not None, "found an off-shelter approach cell to the final sanctuary")

board = {cell: 0 for cell in home_pre}
board[approach] = 0                          # Black's 20th man, not yet sheltered
# a token White man far away so White exists but is irrelevant
board[(8, 8)] = 1
win_state = CState(board=board, to_move=0, dropped=(MEN, MEN))
check(not g.is_terminal(win_state), "not yet won: 19/20 Black men sheltered")
# the winning move: step the 20th man onto its sanctuary
win_move = f"{approach[0]},{approach[1]}>{lc},{lr}"
check(win_move in set(g.legal_moves(win_state)), "the winning step is legal")
won = g.apply_move(win_state, win_move)
check(won.winner == 0, "Black wins once all 20 men are sheltered")
check(g.is_terminal(won), "terminal after the win")
check(g.returns(won) == [1.0, -1.0], "returns: Black +1, White -1")

# Sanity: with only 19 sheltered (MEN-1), no win.
no_win = CState(board={cell: 0 for cell in home_pre} | {(8, 8): 1},
                to_move=0, dropped=(MEN, MEN))
# (this is a constructed mid-position; nobody has all 20 sheltered)
check(no_win.winner is None and not g.is_terminal(no_win)
      if g.legal_moves(no_win) else True,
      "19/20 sheltered is not a win")

# ---------------------------------------------------------------------------
# Purity + serialize round-trip.
# ---------------------------------------------------------------------------
before_board = dict(s4.board)
_ = g.apply_move(s4, "5,5>7,5")
check(s4.board == before_board, "apply_move did not mutate the input state")

rt = g.deserialize(g.serialize(won))
check(g.serialize(rt) == g.serialize(won), "serialize round-trips")

print("SELFTEST OK")
