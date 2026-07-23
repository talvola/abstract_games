"""Standalone correctness anchor for Ot-tjin.

Run with:  PYTHONPATH=. python3 games/ot_tjin/selftest.py

Pure stdlib + this game only. Fast. Prints "SELFTEST OK" and exits 0 on
success, nonzero on any failure.

PRIMARY ANCHOR: the endgame problem printed in *Abstract Games* issue 14
(Summer 2003, p.15, solution p.10). The printed line is a pure NO-CAPTURE
circulation ("No result. The game has to be replayed!"). Replaying it move for
move -- with ZERO fish caught at every ply -- pins the sowing direction, the
relay/gok mechanic and both players' hole numbering all at once. (The `!` / `?`
in the printed solution are chess-style move-quality marks, not fish markers:
`8?` = a losing try, `9!` = the drawing move.)
"""

from __future__ import annotations

import random
import sys

from games.ot_tjin.game import OtTjin, OtState, WIDTH, OWN_CELLS

G = OtTjin()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def make(board_overrides, sph=5, stores=(0, 0), to_move=0,
         ply=0, no_progress=0, done=False):
    board = {(c, r): 0 for r in (0, 1) for c in range(WIDTH)}
    for k, v in board_overrides.items():
        board[k] = v
    return OtState(board=board, stores=list(stores), sph=sph, to_move=to_move,
                   ply=ply, no_progress=no_progress, done=done)


def cell(player, hole):
    """Per-player hole number 1..9 -> cell id string (pinned numbering)."""
    if player == 0:               # South: hole 1 = right = col 8
        return f"{WIDTH - hole},0"
    return f"{hole - 1},1"        # North: hole 1 = left = col 0


def total(s):
    return sum(s.board.values())


# ---------------------------------------------------------------------------
# 1. Setup invariants (default 3-seed game)
# ---------------------------------------------------------------------------
s0 = G.initial_state()
if total(s0) != 3 * 18:
    fail(f"default board should hold 54 seeds, got {total(s0)}")
if any(v != 3 for v in s0.board.values()):
    fail("every hole should start with 3 seeds by default")
if s0.sph != 3:
    fail("default seeds-per-hole should be 3")
if G.current_player(s0) != 0:
    fail("South (player 0) should move first")
if len(G.legal_moves(s0)) != 9:
    fail("all nine holes should be legal openers")

# seeds option
s5 = G.initial_state(options={"seeds": "5"})
if s5.sph != 5 or total(s5) != 5 * 18:
    fail("5-seed option must fill the board with 5 per hole")

# ---------------------------------------------------------------------------
# 2. Basic sowing + gok (no capture)
# ---------------------------------------------------------------------------
# South hole 1 = (8,0) with 2 seeds. Sowing +1 from (8,0): (7,0),(6,0) empty
# -> last lands (6,0)=1 -> gok, no capture, seeds conserved.
s = make({(8, 0): 2}, sph=5)
b, fish = G._sow(s.board, (8, 0), 5)
if fish != 0:
    fail(f"landing in an empty hole must be gok (no capture), got {fish}")
if b[(7, 0)] != 1 or b[(6, 0)] != 1 or b[(8, 0)] != 0 or sum(b.values()) != 2:
    fail("basic sow wrong")

# ---------------------------------------------------------------------------
# 3. Relay + "make fish": last seed brings a hole to the start count (5).
# ---------------------------------------------------------------------------
# Put 4 seeds in (6,0); play (8,0)=2. Sow: (7,0)->1, (6,0)->5 (last). 5 == sph
# -> FISH: (6,0) emptied, 5 seeds to store.
s = make({(8, 0): 2, (6, 0): 4}, sph=5)
b, fish = G._sow(s.board, (8, 0), 5)
if fish != 5:
    fail(f"last seed making a hole reach 5 must be a 5-seed fish, got {fish}")
if b[(6, 0)] != 0:
    fail("the caught hole must be emptied")
if sum(b.values()) != 1:
    fail("after a 5-seed fish, only the intermediate seed should remain")

# A genuine RELAY (last seed lands in an occupied hole -> lift and continue).
# (8,0)=1 with (7,0)=2 occupied: sow (8,0)->(7,0)=3 occupied -> relay lift 3 ->
# (6,0),(5,0),(4,0) all empty -> last (4,0)=1 -> gok.
s = make({(8, 0): 1, (7, 0): 2}, sph=5)
b, fish = G._sow(s.board, (8, 0), 5)
if fish != 0 or b[(7, 0)] != 0 or b[(6, 0)] != 1 or b[(5, 0)] != 1 or b[(4, 0)] != 1:
    fail("relay lift-and-continue did not distribute correctly")

# ---------------------------------------------------------------------------
# 4. PRIMARY ANCHOR -- the printed endgame problem replays with NO captures.
# ---------------------------------------------------------------------------
# Endgame figure (Abstract Games #14, p.15), 5-seed variant, 8 fish each:
#   North (top, row 1):    [0,2,0,0,1,0,1,1,2]
#   South (bottom, row 0): [2,1,0,0,0,0,0,0,0]
#   South to move.
NORTH = [0, 2, 0, 0, 1, 0, 1, 1, 2]
SOUTH = [2, 1, 0, 0, 0, 0, 0, 0, 0]


def endgame():
    ov = {}
    for c in range(WIDTH):
        ov[(c, 1)] = NORTH[c]
        ov[(c, 0)] = SOUTH[c]
    return make(ov, sph=5, stores=(40, 40), to_move=0)  # 8 fish x 5 = 40 each


s = endgame()
if total(s) != 10:
    fail(f"endgame board should hold 10 seeds, got {total(s)}")

# Printed solution line (hole numbers), alternating South/North, starting South.
# '!' / '?' were move-quality marks and are stripped: it is a no-capture line.
LINE = ("9 8 8 1 5 4 4 6 2 3 6 2 5 5 4 4 3 3 7 7 6 6 5 5 4 4 "
        "8 2 7 1 6 3 5 2 8 8 2 7 1 6 3 5 2 4 4 3 3 8 7 7 6 6 5 5 4 4")
MOVES = [int(x) for x in LINE.split()]
if len(MOVES) != 56:
    fail(f"printed line should have 56 moves, parsed {len(MOVES)}")

for i, hole in enumerate(MOVES):
    player = i % 2  # South starts; strictly alternating
    if G.current_player(s) != player:
        fail(f"move {i+1}: expected player {player} to move")
    if s.done:
        fail(f"move {i+1}: game ended early")
    mv = cell(player, hole)
    if mv not in G.legal_moves(s):
        fail(f"move {i+1}: printed move {['S','N'][player]}{hole} ({mv}) not legal")
    before = list(s.stores)
    s = G.apply_move(s, mv)
    if s.stores != before:
        fail(f"move {i+1} ({['S','N'][player]}{hole}) unexpectedly captured a fish")

if s.stores != [40, 40]:
    fail(f"the printed line must catch nothing (stay 40-40), got {s.stores}")
if total(s) != 10:
    fail(f"no seeds should leave the board in the impasse line, got {total(s)}")
if G.returns(s) != [0.0, 0.0]:
    fail("an 8-8 (40-40) tied catch must be an honest draw / no result")

# ---------------------------------------------------------------------------
# 5. "No result" terminal: a long capture-less stretch ends the game as a draw
#    (with tied stores) -- seeds on the board belong to no one.
# ---------------------------------------------------------------------------
from games.ot_tjin.game import NO_PROGRESS_CAP  # noqa: E402
# One capture-less move from no_progress = CAP-1 must terminate as no-result.
s = make({(8, 0): 2, (0, 1): 1}, sph=5, stores=(40, 40), to_move=0,
         no_progress=NO_PROGRESS_CAP - 1)
s = G.apply_move(s, cell(0, 1))  # South hole 1 = (8,0)=2 -> gok, no capture
if not s.done:
    fail("hitting the no-progress cap with no capture must end the game")
if G.returns(s) != [0.0, 0.0]:
    fail("a tied catch at the no-result cap must be a draw")
if total(s) > 0 and s.stores != [40, 40]:
    fail("no-result must NOT divide the remaining seeds")

# ---------------------------------------------------------------------------
# 6. "Cannot move -> opponent captures ALL remaining seeds", game ends.
# ---------------------------------------------------------------------------
# North to move, but after North's move South has NO seeds -> South cannot move
# -> North scoops everything. Set North hole 1 = (0,1)=1 (sows to (1,1), gok),
# South row entirely empty. After North's move it is South's turn with 0 seeds.
s = make({(0, 1): 1, (5, 1): 3}, sph=5, stores=(40, 40), to_move=1)
s = G.apply_move(s, cell(1, 1))   # North hole 1 = (0,1)=1 -> lands (1,1) gok
if not s.done:
    fail("if the opponent has no legal move, the game must end")
# North should have scooped every remaining seed on the board.
if total(s) != 0:
    fail("opponent-cannot-move: the mover must scoop ALL remaining seeds")
if s.stores[1] != 40 + 4:  # 40 already + (the leftover seed + the 3 unplayed)
    fail(f"North should have scooped the 4 remaining seeds, got {s.stores[1]}")
if G.returns(s) != [-1.0, 1.0]:
    fail("North (more seeds) must win after the scoop")

# ---------------------------------------------------------------------------
# 7. Honest scoring.
# ---------------------------------------------------------------------------
if G.returns(make({}, stores=(40, 40), done=True)) != [0.0, 0.0]:
    fail("equal catch must be a draw")
if G.returns(make({}, stores=(45, 40), done=True)) != [1.0, -1.0]:
    fail("more seeds for South must be a South win")
if G.returns(make({}, stores=(35, 40), done=True)) != [-1.0, 1.0]:
    fail("more seeds for North must be a North win")

# ---------------------------------------------------------------------------
# 8. Serialize round-trip.
# ---------------------------------------------------------------------------
for st in (G.initial_state(), G.initial_state(options={"seeds": "5"}), endgame()):
    r = G.deserialize(G.serialize(st))
    if G.serialize(r) != G.serialize(st):
        fail("serialize round-trip mismatch")

# ---------------------------------------------------------------------------
# 9. Render sanity.
# ---------------------------------------------------------------------------
rspec = G.render(G.initial_state())
if rspec["board"] != {"type": "square", "width": 9, "height": 2}:
    fail("render board spec wrong")
if len(rspec["pieces"]) != 18:
    fail("render should emit all 18 holes")

# ---------------------------------------------------------------------------
# 10. Random conformance: games terminate; stores stay sane.
# ---------------------------------------------------------------------------
for seed in (1, 2, 3):
    rng = random.Random(1000 + seed)
    for _ in range(40):
        opts = {"seeds": rng.choice(["2", "3", "4", "5"])}
        s = G.initial_state(options=opts)
        cap = total(s)
        steps = 0
        while not G.is_terminal(s):
            mv = rng.choice(G.legal_moves(s))
            s = G.apply_move(s, mv)
            steps += 1
            if steps > 5000:
                fail("random game failed to terminate within the ply cap")
        if s.stores[0] + s.stores[1] > cap:
            fail("captured more seeds than existed")
        if sorted(G.returns(s)) not in ([-1.0, 1.0], [0.0, 0.0]):
            fail(f"illegal returns {G.returns(s)}")

print("SELFTEST OK")
