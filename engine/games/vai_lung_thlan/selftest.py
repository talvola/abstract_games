"""Standalone correctness anchor for Vai lung thlân.

Run with:  PYTHONPATH=. python3 games/vai_lung_thlan/selftest.py

Pure stdlib + this game only. Fast. Prints "SELFTEST OK" and exits 0 on
success, nonzero on any failure.

PRIMARY ANCHOR: the endgame problem printed in *Abstract Games* issue 12
(Winter 2002, p.15, solution p.29). The drawing line 4 / 2 / 5 / 1 / 6 is played
out to the very end of the game and must clear the board to a 30-30 draw. This
pins the sowing direction, the capture rule and the hole numbering all at once.
"""

from __future__ import annotations

import random
import sys

from games.vai_lung_thlan.game import (
    VaiLungThlan, VLTState, PIT_ORDER, OWN_PITS,
)

G = VaiLungThlan()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def state(board_overrides, stores=(0, 0), to_move=0, ply=0, no_progress=0, done=False):
    board = {pit: 0 for pit in PIT_ORDER}
    for k, v in board_overrides.items():
        board[k] = v
    return VLTState(board=dict(board), stores=list(stores),
                    to_move=to_move, ply=ply, no_progress=no_progress, done=done)


def cell(player, hole):
    """Translate a per-player hole number (1..6, right-to-left) to a cell id."""
    if player == 0:      # South: hole n -> (6-n, 0)
        return f"{6 - hole},0"
    return f"{hole - 1},1"  # North: hole n -> (n-1, 1)


def total_on_board(s):
    return sum(s.board.values())


# ---------------------------------------------------------------------------
# 1. Setup invariants
# ---------------------------------------------------------------------------
s0 = G.initial_state()
if total_on_board(s0) != 60:
    fail(f"initial board should hold 60 stones, got {total_on_board(s0)}")
if any(v != 5 for v in s0.board.values()):
    fail("every hole should start with 5 stones")
if G.current_player(s0) != 0:
    fail("South (player 0) should move first")
if len(G.legal_moves(s0)) != 6:
    fail("all six holes should be legal openers")

# ---------------------------------------------------------------------------
# 2. Single lap: last stone in a non-empty hole -> NO capture, NO relay
# ---------------------------------------------------------------------------
# origin (5,0)=2 -> drops in (4,0) then (3,0). Pre-load (3,0)=1 so the last
# stone lands in a hole that already held a stone: no capture, and crucially the
# move ENDS there (no re-lift / relay from (3,0)).
s = state({(5, 0): 2, (3, 0): 1}, to_move=0)
b, cap = G._sow_and_capture(s.board, (5, 0))
if cap != 0:
    fail(f"single-lap non-empty landing must not capture, got {cap}")
if b[(4, 0)] != 1 or b[(3, 0)] != 2 or b[(5, 0)] != 0:
    fail(f"single-lap sowing wrong: {b[(5,0)]},{b[(4,0)]},{b[(3,0)]}")
if sum(b.values()) != 3:
    fail("single-lap should conserve all 3 stones on the board (no capture)")

# ---------------------------------------------------------------------------
# 3. Chain of singles: capture the last hole + the unbroken run of singles
#    behind it, STOPPING at the first non-single hole.
# ---------------------------------------------------------------------------
# origin (5,0)=4 -> drops in (4,0),(3,0),(2,0),(1,0). Pre-load (3,0)=1 so it
# becomes 2 and breaks the chain. Landing hole (1,0)=1 (was empty) -> capture
# (1,0) and (2,0); the chain STOPS at (3,0)=2; (4,0)=1 is beyond the break and
# must NOT be captured.
s = state({(5, 0): 4, (3, 0): 1}, to_move=0)
b, cap = G._sow_and_capture(s.board, (5, 0))
if cap != 2:
    fail(f"chain capture should take exactly 2 stones, got {cap}")
if b[(1, 0)] != 0 or b[(2, 0)] != 0:
    fail("captured single-stone holes must be emptied")
if b[(3, 0)] != 2:
    fail("chain must stop at the first non-single hole (3,0)=2, left intact")
if b[(4, 0)] != 1:
    fail("single-stone hole beyond the break must NOT be captured")

# ---------------------------------------------------------------------------
# 4. A 12-stone hole always captures (its last stone lands back in the origin).
# ---------------------------------------------------------------------------
s = state({(5, 0): 12}, to_move=0)
b, cap = G._sow_and_capture(s.board, (5, 0))
if cap != 12:
    fail(f"a 12-stone lap on an empty board should capture all 12, got {cap}")
if sum(b.values()) != 0:
    fail("board should be empty after the 12-stone sweep")

# ---------------------------------------------------------------------------
# 5. PRIMARY ANCHOR -- the printed endgame problem, played to a 30-30 draw.
# ---------------------------------------------------------------------------
# Figure (Abstract Games #12, p.15):
#   North (top row):    [2, 3, 0, 0, 0, 0]   captured 23
#   South (bottom row): [0, 10, 3, 0, 0, 0]  captured 19
#   South to move.
def endgame():
    return state(
        {(0, 1): 2, (1, 1): 3,          # North row
         (1, 0): 10, (2, 0): 3},        # South row
        stores=(19, 23), to_move=0,
    )

s = endgame()
if total_on_board(s) != 18 or s.stores != [19, 23]:
    fail("endgame position setup is wrong")
# South's only non-empty holes are #4 (=cell 2,0 with 3) and #5 (=cell 1,0 w/10).
legal = set(G.legal_moves(s))
if legal != {cell(0, 4), cell(0, 5)}:
    fail(f"endgame South legal moves should be holes 4 and 5, got {legal}")

# The drawing line: South 4 / North 2 / South 5 / North 1 / South 6.
line = [(0, 4), (1, 2), (0, 5), (1, 1), (0, 6)]
for player, hole in line:
    if s.done:
        fail("game ended before the drawing line was complete")
    if G.current_player(s) != player:
        fail(f"expected {player} to move, got {G.current_player(s)}")
    mv = cell(player, hole)
    if mv not in G.legal_moves(s):
        fail(f"printed move {['S','N'][player]}{hole} ({mv}) is not legal")
    s = G.apply_move(s, mv)

if not s.done:
    fail("board should be empty (game over) after the printed drawing line")
if s.stores != [30, 30]:
    fail(f"printed drawing line must reach 30-30, got {s.stores}")
if G.returns(s) != [0.0, 0.0]:
    fail("30-30 must be an honest draw")

# The alternate order 6 / 1 / 5 for the last three plies also draws.
s = endgame()
for player, hole in [(0, 4), (1, 2), (0, 6), (1, 1), (0, 5)]:
    s = G.apply_move(s, cell(player, hole))
if not s.done or s.stores != [30, 30]:
    fail(f"alternate drawing line 6/1/5 must also reach 30-30, got {s.stores}")

# ---------------------------------------------------------------------------
# 6. Forced pass: a seat with an empty row is skipped (mover continues).
# ---------------------------------------------------------------------------
# North to move, South row empty. North's move lands its last stone in an
# already-occupied hole (no capture) and does not feed South, so afterwards
# South must pass and it is North's turn again.
s = state({(1, 1): 1, (2, 1): 1}, to_move=1)
s2 = G.apply_move(s, cell(1, 2))   # North hole 2 = (1,1); last lands in (2,1)=2
if s2.done:
    fail("game must not end while stones remain on the board")
if s2.to_move != 1:
    fail("a seat with no legal move must be skipped (mover continues)")
if not G.legal_moves(s2):
    fail("the seat to move must always have at least one legal move")

# ---------------------------------------------------------------------------
# 7. Honest scoring: draw vs. win.
# ---------------------------------------------------------------------------
if G.returns(state({}, stores=(30, 30), done=True)) != [0.0, 0.0]:
    fail("30-30 stores must return a draw")
if G.returns(state({}, stores=(31, 29), done=True)) != [1.0, -1.0]:
    fail("31-29 must be a South win")
if G.returns(state({}, stores=(20, 25), done=True)) != [-1.0, 1.0]:
    fail("20-25 must be a North win")

# ---------------------------------------------------------------------------
# 8. Serialize round-trip.
# ---------------------------------------------------------------------------
for st in (G.initial_state(), endgame()):
    r = G.deserialize(G.serialize(st))
    if G.serialize(r) != G.serialize(st):
        fail("serialize round-trip mismatch")

# ---------------------------------------------------------------------------
# 9. Random conformance: games terminate and stores stay sane.
# ---------------------------------------------------------------------------
rng = random.Random(20021)
for _ in range(60):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s):
        mv = rng.choice(G.legal_moves(s))
        s = G.apply_move(s, mv)
        steps += 1
        if steps > 700:
            fail("random game failed to terminate within the ply cap")
    if s.stores[0] + s.stores[1] > 60:
        fail("captured more stones than exist")
    ret = G.returns(s)
    if sorted(ret) not in ([-1.0, 1.0], [0.0, 0.0]):
        fail(f"illegal returns {ret}")

print("SELFTEST OK")
