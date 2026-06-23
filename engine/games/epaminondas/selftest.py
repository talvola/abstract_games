"""Standalone selftest for Epaminondas. Pure stdlib (imports only agp + this
game). Run:  PYTHONPATH=. python3 games/epaminondas/selftest.py

Asserts the correctness anchor:
  (1) a PHALANX is a maximal straight line (orthogonal OR diagonal) of >=1
      adjacent friendly pieces; a length-L phalanx slides 1..L along its axis
      onto empty squares (the trailing squares vacate);
  (2) a phalanx CAPTURES by landing its front on the FRONT of a STRICTLY SHORTER
      enemy phalanx on the same line, removing the whole enemy phalanx; an
      equal-or-longer enemy CANNOT be captured; no jumping;
  (3) the crossing win condition (deferred, one reply, strict majority);
plus a hand-built phalanx move, a shorter-enemy capture, an equal-length capture
correctly REJECTED, and the empty-path requirement.
"""

import sys

from games.epaminondas.game import (
    Epaminondas, EpamState, W, H, BACK_ROW, _phalanx_length, _back_count,
)


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def board_of(pieces):
    """pieces: dict (c,r)->owner."""
    return dict(pieces)


G = Epaminondas()


# ---------------------------------------------------------------------------
# (0) sanity on the standard setup
# ---------------------------------------------------------------------------
s0 = G.initial_state()
assert len(s0.board) == 4 * W, "setup should have 4 full rows of pieces"
assert sum(1 for v in s0.board.values() if v == 0) == 2 * W
assert sum(1 for v in s0.board.values() if v == 1) == 2 * W
assert BACK_ROW == {0: 0, 1: H - 1}
# Player 0 occupies rows 0,1 ; player 1 rows 10,11.
assert all(r in (0, 1) for (c, r), p in s0.board.items() if p == 0)
assert all(r in (H - 2, H - 1) for (c, r), p in s0.board.items() if p == 1)
# Opening move count: every column is a vertical phalanx of length 2 that can
# advance 1 or 2; plus horizontal phalanxes on each of the two rows. Just assert
# there ARE legal moves and they're well formed.
mv0 = G.legal_moves(s0)
assert mv0, "opening must have legal moves"
for m in mv0:
    assert ">" in m and m.count(">") == 1


# ---------------------------------------------------------------------------
# (1) PHALANX definition: maximal line, orthogonal & diagonal
# ---------------------------------------------------------------------------
# Horizontal phalanx of 3 for player 0 at (2,2),(3,2),(4,2). A 4th friendly at
# (5,2) would extend it (maximality); leave a gap at (5,2) but a piece at (6,2)
# (separate phalanx).
b = board_of({(2, 2): 0, (3, 2): 0, (4, 2): 0, (6, 2): 0})
# length through the middle, horizontal axis (1,0):
assert _phalanx_length(b, 3, 2, 1, 0, 0) == 3, "horizontal phalanx length"
assert _phalanx_length(b, 6, 2, 1, 0, 0) == 1, "isolated piece is length 1"
# A diagonal phalanx (1,1): (1,1),(2,2),(3,3)
bd = board_of({(1, 1): 0, (2, 2): 0, (3, 3): 0})
assert _phalanx_length(bd, 2, 2, 1, 1, 0) == 3, "diagonal phalanx length"
# anti-diagonal (1,-1): (1,5),(2,4),(3,3)
ba = board_of({(1, 5): 0, (2, 4): 0, (3, 3): 0})
assert _phalanx_length(ba, 2, 4, 1, -1, 0) == 3, "anti-diagonal phalanx length"


# ---------------------------------------------------------------------------
# (1b) SLIDE move: a length-3 horizontal phalanx slides 1..3, trailing vacates,
# path must be empty.
# ---------------------------------------------------------------------------
# Phalanx at (2,2),(3,2),(4,2) owner 0, to_move 0. Direction +x (head at (4,2)).
# Give player 1 a token elsewhere so they have pieces (avoid annihilation paths).
b = board_of({(2, 2): 0, (3, 2): 0, (4, 2): 0, (10, 10): 1})
s = EpamState(board=b, to_move=0)
moves = set(G.legal_moves(s))
# Moving +x: rear is (2,2); head (4,2) can advance to (5,2),(6,2),(7,2).
assert "2,2>5,2" in moves, "slide 1 step +x"
assert "2,2>6,2" in moves, "slide 2 steps +x"
assert "2,2>7,2" in moves, "slide 3 steps +x (=length)"
assert "2,2>8,2" not in moves, "cannot slide more than length"
# Apply a 2-step slide and verify the whole line shifted, trailing vacated.
s2 = G.apply_move(s, "2,2>6,2")
occ0 = sorted(c for c, p in s2.board.items() if p == 0)
assert occ0 == [(4, 2), (5, 2), (6, 2)], f"line should shift to 4,5,6: {occ0}"
assert (2, 2) not in s2.board and (3, 2) not in s2.board, "trailing squares vacated"

# Blocked path: put a friendly piece in front -> cannot slide through/onto it.
b = board_of({(2, 2): 0, (3, 2): 0, (4, 2): 0, (5, 2): 0, (10, 10): 1})
# Now (2..5,2) is actually a length-4 phalanx. Put the blocker NOT contiguous:
b = board_of({(2, 2): 0, (3, 2): 0, (4, 2): 0, (6, 2): 0, (10, 10): 1})
s = EpamState(board=b, to_move=0)
moves = set(G.legal_moves(s))
# The 3-phalanx (2,3,4) heading +x: (5,2) empty OK, but (6,2) friendly -> blocked.
assert "2,2>5,2" in moves, "slide into the empty gap is fine"
assert "2,2>6,2" not in moves, "cannot land on a friendly piece"
assert "2,2>7,2" not in moves, "cannot jump a friendly piece"


# ---------------------------------------------------------------------------
# (2) CAPTURE: strictly longer captures shorter, lands on enemy FRONT, removes
# the whole enemy phalanx; equal-or-longer is REJECTED; no jumping.
# ---------------------------------------------------------------------------
# Mover (player 0) horizontal length 3 at (2,2),(3,2),(4,2) heading +x.
# Enemy (player 1) phalanx length 2 with FRONT at (6,2): (6,2),(7,2). Gap (5,2).
b = board_of({(2, 2): 0, (3, 2): 0, (4, 2): 0, (6, 2): 1, (7, 2): 1})
s = EpamState(board=b, to_move=0)
moves = set(G.legal_moves(s))
# head at (4,2), one empty (5,2), then enemy front (6,2): capture lands head on
# (6,2). distance from head = 2 <= L=3, empty between -> legal capture.
assert "2,2>6,2" in moves, "strictly-longer capture (L3 vs L2) should be legal"
sc = G.apply_move(s, "2,2>6,2")
# whole enemy phalanx removed:
assert (6, 2) not in [c for c, p in sc.board.items() if p == 1]
assert (7, 2) not in sc.board, "entire enemy phalanx removed"
assert sc.board.get((6, 2)) == 0, "mover front landed on enemy front square"
# the mover phalanx shifted by 2 (head 4->6): cells (4,2),(5,2),(6,2)
movercells = sorted(c for c, p in sc.board.items() if p == 0)
assert movercells == [(4, 2), (5, 2), (6, 2)], f"mover shifted onto front: {movercells}"

# EQUAL-LENGTH capture REJECTED: mover L2 vs enemy L2, head-on.
# Mover (0) at (2,2),(3,2) heading +x; enemy (1) front (5,2): (5,2),(6,2). gap (4,2).
b = board_of({(2, 2): 0, (3, 2): 0, (5, 2): 1, (6, 2): 1})
s = EpamState(board=b, to_move=0)
moves = set(G.legal_moves(s))
# head (3,2): can slide to (4,2) (1 step, empty). Cannot capture (5,2) because
# enemy length 2 == mover length 2.
assert "2,2>4,2" in moves, "slide into the gap is legal"
assert "2,2>5,2" not in moves, "equal-length capture must be REJECTED"

# LONGER enemy capture REJECTED: mover L2 vs enemy L3.
b = board_of({(2, 2): 0, (3, 2): 0, (5, 2): 1, (6, 2): 1, (7, 2): 1})
s = EpamState(board=b, to_move=0)
moves = set(G.legal_moves(s))
assert "2,2>5,2" not in moves, "capturing a longer enemy must be REJECTED"

# NO JUMPING: an enemy piece in the path blocks even a longer phalanx from
# reaching a phalanx behind it. Mover L4, enemy single at (5,2) then enemy at
# (7,2). Mover may capture the FRONT single (5,2) only (L4 > L1), not leap to 7.
b = board_of({(1, 2): 0, (2, 2): 0, (3, 2): 0, (4, 2): 0, (5, 2): 1, (7, 2): 1})
s = EpamState(board=b, to_move=0)
moves = set(G.legal_moves(s))
assert "1,2>5,2" in moves, "L4 captures the adjacent single enemy at its front"
assert "1,2>7,2" not in moves, "cannot jump the enemy at (5,2) to reach (7,2)"

# Capture must land on the enemy FRONT, not partway: mover cannot stop short on
# an empty square that is 'inside' would-be capture distance and still be a slide
# only where empty. (Already covered: slides only onto empty.) Confirm a slide
# cannot land ON an enemy except as a capture: here enemy front is L-equal so no
# capture, and landing on it as a plain slide is illegal.
assert all(not (m.endswith(">5,2")) for m in G.legal_moves(
    EpamState(board=board_of({(2, 2): 0, (3, 2): 0, (5, 2): 1, (6, 2): 1}), to_move=0)
)), "cannot slide onto an enemy without a valid capture"


# ---------------------------------------------------------------------------
# (3) CROSSING win condition (deferred, one reply, STRICT majority)
# ---------------------------------------------------------------------------
# Player 0's back row = row 0; player 1's back row = row 11.
# Build: player 0 about to move a single piece from (3,10) onto (3,11) = enemy
# back row. Player 1 has NO piece on row 0. After 0's move, the player who is
# 'not to move' is player 1; their count on 0's back row (row 0) = 0, 0's count
# on row 11 = 1. So 1 does NOT win (X=0 not > Y=1). Then it's 1's turn; if 1
# cannot equalize, 0 wins at the end of 1's move.
# Simplest direct test of the rule mechanics: construct a position where, right
# after a move, the opponent already holds a strict majority on the mover's back
# row -> opponent wins immediately.
#
# Let player 1 already have 1 piece on row 0 (a standing crossing). Player 0 has
# 0 pieces on row 11. Player 0 makes some harmless move that does not change the
# crossing counts. End of 0's move: opponent = player 1, X = #(1 on row 0) = 1,
# Y = #(0 on row 11) = 0 -> 1 > 0 -> player 1 WINS.
b = board_of({
    (5, 0): 1,            # player 1 crossing on player 0's back row
    (3, 5): 0, (4, 5): 0,  # a player-0 phalanx to make a harmless move
    (8, 8): 0,            # extra so 0 has pieces
})
s = EpamState(board=b, to_move=0)
# player 0 slides its phalanx sideways (does not reach row 11)
mv = G.legal_moves(s)
assert mv, "player 0 should have a move"
pick = next(m for m in mv if m.startswith("3,5>") or m.startswith("4,5>") or m.startswith("8,8>"))
s_after = G.apply_move(s, pick)
assert s_after.winner == 1, (
    f"player 1 holds a strict majority on player 0's back row after 0's reply "
    f"-> player 1 wins; got winner={s_after.winner}"
)

# Strict majority required: if player 0 ALSO has 1 on row 11 (a tie), no win.
b = board_of({
    (5, 0): 1,             # player 1 on row 0
    (9, 11): 0,            # player 0 on row 11 (equalized)
    (3, 5): 0, (4, 5): 0,  # phalanx to move
})
s = EpamState(board=b, to_move=0)
mv = G.legal_moves(s)
pick = next(m for m in mv if m.startswith("3,5>") or m.startswith("4,5>"))
s_after = G.apply_move(s, pick)
assert s_after.winner is None, "an equal count (tie) on both back rows is NOT a win"

# Crossing that survives the opponent's reply: player 0 has 1 on row 11, player 1
# has 0 on row 0, and it is player 1 to move but player 1 cannot do anything
# about it (no piece can reach row 0, no capture available). After 1's move, the
# opponent (player 0) has X=1 on 1's back row vs Y=0 -> player 0 wins.
b = board_of({
    (5, 11): 0,            # player 0 standing crossing on player 1's back row
    (2, 6): 1, (3, 6): 1,  # player 1 phalanx far away, cannot equalize/capture
})
s = EpamState(board=b, to_move=1)
mv = G.legal_moves(s)
assert mv, "player 1 must have a move"
s_after = G.apply_move(s, mv[0])
assert s_after.winner == 0, (
    f"player 0's crossing survives 1's reply -> player 0 wins; got {s_after.winner}"
)

# Opponent EQUALIZES by capturing the crossing piece: player 0 has a lone piece
# on row 11; player 1 has a length-2 phalanx that can capture it head-on. After
# 1 captures, 0 has 0 on row 11 -> no win for 0; (and 0 may then have no win).
b = board_of({
    (5, 11): 0,                # player 0 crossing (length 1)
    (5, 9): 1, (5, 8): 1,      # player 1 vertical L2 below, front at (5,9) facing up
})
# player 1 to move, head of its up-phalanx is (5,9); slide/capture up: (5,10)
# empty, (5,11) enemy front length1 -> L2 > L1 capture lands on (5,11).
s = EpamState(board=b, to_move=1)
moves = set(G.legal_moves(s))
assert "5,8>5,11" in moves, f"player 1 should be able to capture the crosser: {moves}"
s_after = G.apply_move(s, "5,8>5,11")
assert s_after.board.get((5, 11)) == 1, "player 1 captured onto the crossing square"
assert _back_count(s_after.board, 0) == 0, "player 0's crossing was eliminated"
assert s_after.winner != 0, "captured crossing must not win for player 0"


# ---------------------------------------------------------------------------
# serialize round-trip
# ---------------------------------------------------------------------------
s = G.initial_state()
s = G.apply_move(s, G.legal_moves(s)[0])
d = G.serialize(s)
s_rt = G.deserialize(d)
assert G.serialize(s_rt) == d, "serialize must round-trip"


print("SELFTEST OK")
sys.exit(0)
