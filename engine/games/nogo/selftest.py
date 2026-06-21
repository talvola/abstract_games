#!/usr/bin/env python3
"""Standalone correctness anchor for NoGo.

Run with:  PYTHONPATH=. python3 games/nogo/selftest.py

Pure stdlib + this game package only (no third-party libs, no big game loops).
Asserts the rule anchor and a handful of hand-built positions, then prints
"SELFTEST OK" and exits 0. Any failure raises and exits nonzero.
"""

import sys

from agp.conformance import check
from games.nogo.game import NoGo, NoGoState, BLACK, WHITE

G = NoGo()


def legal(s):
    return set(G.legal_moves(s))


def st(n, board, to_move):
    """Build a state from a {(c,r): player} board dict."""
    return NoGoState(n=n, board=dict(board), to_move=to_move)


# --- 1. Conformance: the package honours the Game contract -------------------
manifest = {"players": {"min": 2, "max": 2}}
rep = check(G, manifest, games=12, seed=1)
assert rep.ok, "conformance failed:\n" + rep.summary()
assert rep.games_played > 0, "no random games completed"

# Initial 9x9 state: Black to move, all 81 cells legal (an empty board can
# never capture or suicide).
s0 = G.initial_state()
assert not G.is_terminal(s0)
assert len(G.legal_moves(s0)) == 81, "empty 9x9 should have 81 legal placements"
assert G.current_player(s0) == BLACK

# Serialize round-trips.
import json  # noqa: E402
snap = G.serialize(s0)
assert json.dumps(snap)
assert G.serialize(G.deserialize(snap)) == snap


# --- 2. CAPTURE is ILLEGAL ---------------------------------------------------
# White stone at (0,0). Its only neighbours on a 3x3 board are (1,0) and (0,1).
# Black already holds (0,1); the white group's sole liberty is (1,0).
# Black playing (1,0) would leave White with 0 liberties -> a capture -> ILLEGAL.
n = 3
board = {(0, 0): WHITE, (0, 1): BLACK}
s = st(n, board, BLACK)
assert "1,0" not in legal(s), "filling an enemy group's last liberty must be illegal (capture)"
# Sanity: a harmless distant placement that touches no group is legal.
assert "2,2" in legal(s), "a harmless distant placement should be legal"


# --- 3. SUICIDE is ILLEGAL ---------------------------------------------------
# Corner (0,0) is empty and surrounded by White at its only two neighbours
# (1,0) and (0,1). Black playing (0,0) would form a 1-stone group with no
# liberties (the corner has no other neighbours) -> SUICIDE -> ILLEGAL.
n = 3
board = {(1, 0): WHITE, (0, 1): WHITE}
s = st(n, board, BLACK)
assert "0,0" not in legal(s), "playing into a fully enclosed point must be illegal (suicide)"

# But the SAME point is legal if it connects to a friendly group with a liberty.
# Black at (0,1) with a White wall otherwise: place (0,0) joining Black -> the
# combined Black group still has liberty via (0,1)'s other neighbours.
n = 3
board = {(1, 0): WHITE, (0, 1): BLACK}
s = st(n, board, BLACK)
# (0,1) Black has liberties (0,2) and (1,1); playing (0,0) joins it -> legal.
assert "0,0" in legal(s), "filling a point that joins a friendly group with a liberty is legal"


# --- 4. A move that would BOTH capture and self-connect is still a capture ----
# Single White stone in atari, Black filling its last liberty even while the
# filling stone would itself have liberties: still illegal because it captures.
n = 3
board = {(1, 1): WHITE, (0, 1): BLACK, (2, 1): BLACK, (1, 2): BLACK}
# White (1,1) neighbours: (0,1)B, (2,1)B, (1,2)B, (1,0)empty -> last liberty (1,0).
s = st(n, board, BLACK)
assert "1,0" not in legal(s), "filling a surrounded enemy's last liberty is a capture -> illegal"


# --- 5. NO LEGAL MOVE => the player to move LOSES ----------------------------
# Build a 2x2 board where Black is forced into a position with no legal move.
# Fill a board so that the only empty cells are all suicidal/capturing for the
# side to move, making is_terminal true and returns decisive.
#
# 2x2 board, three stones placed: B at (0,0),(1,1) ; W at (1,0). Empty: (0,1).
# It's Black to move. (0,1) neighbours: (0,0)B and (1,1)B -> both Black, so it
# JOINS Black and the joined group: does it have a liberty? Group = {(0,0),(0,1),
# (1,1)}. Liberties: (0,0)->(1,0)=W; (0,1)->none empty; (1,1)->(1,0)=W. No empty
# neighbour -> suicide -> illegal. So Black has no legal move and LOSES.
n = 2
board = {(0, 0): BLACK, (1, 1): BLACK, (1, 0): WHITE}
s = st(n, board, BLACK)
assert legal(s) == set(), "Black should have no legal move in this packed position"
assert G.is_terminal(s), "a side with no legal move is a terminal state"
ret = G.returns(s)
assert ret == [-1.0, 1.0], f"Black to move with no move must LOSE: got {ret}"

# Symmetric check: same shape with colours/side swapped -> White loses.
n = 2
board = {(0, 0): WHITE, (1, 1): WHITE, (1, 0): BLACK}
s = st(n, board, WHITE)
assert legal(s) == set(), "White should have no legal move here"
assert G.is_terminal(s)
assert G.returns(s) == [1.0, -1.0], "White to move with no move must LOSE"


# --- 6. apply_move records the winner exactly when the opponent gets stuck ----
# Play a deterministic full game on a tiny 2x2 board (always take the
# lexicographically first legal move) until someone is stuck. The FINAL
# apply_move must detect the opponent has no move and record the mover as
# winner; the recorded loser must be the side then to move; and every
# apply_move along the way must be pure.
s = G.initial_state(options={"size": 2})
last = None
for _ in range(100):
    if G.is_terminal(s):
        break
    moves = sorted(G.legal_moves(s))
    assert moves, "non-terminal state must have a legal move"
    mover = s.to_move
    before = G.serialize(s)
    nxt = G.apply_move(s, moves[0])
    assert G.serialize(s) == before, "apply_move must not mutate its input"
    last = (mover, nxt)
    s = nxt
assert G.is_terminal(s), "the 2x2 game must reach a terminal position"
final_mover, final_state = last
# Game ended because, after final_mover's move, the opponent is stuck.
assert final_state.winner == final_mover, "apply_move must record the mover as winner"
assert G._loser(final_state) == final_state.to_move, "loser is the stuck side to move"
ret = G.returns(final_state)
assert ret[final_mover] == 1.0 and ret[1 - final_mover] == -1.0, \
    f"winner +1 / loser -1 expected, got {ret}"


print("SELFTEST OK")
sys.exit(0)
