"""Pure-stdlib correctness anchor for Four Field Kono.

Run: PYTHONPATH=. python3 games/four_field_kono/selftest.py

Anchor (no published perft) = baked rule assertions:
 (1) 4x4 board; each player has 8 pieces filling their two nearest rows at start
     (player 0 rows 0-1, player 1 rows 2-3); board is full -> first move captures.
 (2) the SIGNATURE jump: jump orthogonally over an ADJACENT OWN piece, landing on
     the cell immediately beyond, which MUST hold an OPPONENT (captured/removed);
     NOT onto empty, NOT over an enemy, NOT over a gap.
 (2f) the NON-CAPTURING slide: one step orthogonally to an adjacent EMPTY cell
     (NOT diagonal); piece relocates, counts unchanged.
 (3) WIN = opponent has no legal move (no jump AND no slide).
 (4) the formerly-degenerate position (armies separated, no captures) is NOT an
     instant loss now that slides exist.
Plus hand-built positions exercising legal/illegal jumps, slides, and a win.
"""

import sys

from games.four_field_kono.game import FourFieldKono, FFKState

G = FourFieldKono()


def fail(msg):
    print(f"SELFTEST FAIL: {msg}")
    sys.exit(1)


def board_from(rows):
    """rows[r][c] in {'.', '0', '1'} -> board dict (r=0 is bottom)."""
    b = {}
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch in "01":
                b[(c, r)] = int(ch)
    return b


# ---- (1) board geometry + start ----
rs = G.render(G.initial_state())
assert rs["board"]["type"] == "square", "board must be square"
if rs["board"]["width"] != 4 or rs["board"]["height"] != 4:
    fail("board must be 4x4")

st = G.initial_state()
if len(st.board) != 16:
    fail("start board must be completely full (16 pieces)")
p0 = sorted(k for k, v in st.board.items() if v == 0)
p1 = sorted(k for k, v in st.board.items() if v == 1)
if len(p0) != 8 or len(p1) != 8:
    fail("each player must start with 8 pieces")
if any(r not in (0, 1) for (c, r) in p0):
    fail("player 0 must occupy rows 0 and 1")
if any(r not in (2, 3) for (c, r) in p1):
    fail("player 1 must occupy rows 2 and 3")
if G.current_player(st) != 0:
    fail("player 0 moves first")

# Board is full -> first move must be a capturing jump, and such moves exist.
lm = G.legal_moves(st)
if not lm:
    fail("first player must have a legal capturing jump from the full board")
# Every legal move's landing cell currently holds an opponent piece.
for mv in lm:
    frm, to = mv.split(">")
    fc, fr = map(int, frm.split(","))
    tc, tr = map(int, to.split(","))
    if st.board.get((tc, tr)) != 1:
        fail(f"legal move {mv} must land on an opponent piece")
    if st.board.get((fc, fr)) != 0:
        fail(f"legal move {mv} must start on own piece")
    # The jumped-over (midpoint) cell must be our OWN piece, in a straight line.
    if (fc - tc) and (fr - tr):
        fail(f"move {mv} must be orthogonal (straight line)")
    mc, mr = (fc + tc) // 2, (fr + tr) // 2
    if abs(fc - tc) + abs(fr - tr) != 2:
        fail(f"move {mv} must be a two-step jump")
    if st.board.get((mc, mr)) != 0:
        fail(f"jumped-over cell of {mv} must be own piece")

# Applying a first move captures exactly one enemy: piece count drops by 1.
mv0 = lm[0]
st2 = G.apply_move(st, mv0)
if len(st2.board) != 15:
    fail("a capturing jump must remove exactly one (enemy) piece")
if G.current_player(st2) != 1:
    fail("turn must pass to the opponent after a move")

# ---- (2) hand-built legal capturing jump ----
# Column c=1: own(0) at r0, own(0) at r1, enemy(1) at r2 -> jump r0 over r1 to r2.
b = board_from([
    ".0..",   # r0
    ".0..",   # r1
    ".1..",   # r2
    "....",   # r3
])
s = FFKState(board=b, to_move=0)
moves = set(G.legal_moves(s))
if "1,0>1,2" not in moves:
    fail("expected legal jump 1,0>1,2 (over own onto enemy)")
res = G.apply_move(s, "1,0>1,2")
if res.board.get((1, 2)) != 0:
    fail("after jump, jumper must occupy the landing cell")
if (1, 0) in res.board:
    fail("after jump, the from-cell must be vacated")
if (1, 1) in res.board and res.board[(1, 1)] != 0:
    fail("the jumped-over own piece must remain")
# exactly the enemy at (1,2) was captured: only own pieces remain
if any(v == 1 for v in res.board.values()):
    fail("the enemy at the landing cell must be captured")

# ---- (2b) ILLEGAL: jump onto an EMPTY cell (no enemy beyond) ----
b = board_from([
    ".0..",   # r0 own
    ".0..",   # r1 own
    "....",   # r2 empty  <- landing empty
    "....",
])
s = FFKState(board=b, to_move=0)
if "1,0>1,2" in set(G.legal_moves(s)):
    fail("must NOT allow jumping onto an empty cell")

# ---- (2c) ILLEGAL: jump OVER an enemy piece ----
b = board_from([
    ".0..",   # r0 own jumper
    ".1..",   # r1 ENEMY in the middle
    ".1..",   # r2 enemy beyond
    "....",
])
s = FFKState(board=b, to_move=0)
if "1,0>1,2" in set(G.legal_moves(s)):
    fail("must NOT allow jumping OVER an enemy piece")

# ---- (2d) ILLEGAL: jump over an empty GAP (no own piece to leap) ----
b = board_from([
    ".0..",   # r0 own jumper
    "....",   # r1 empty gap
    ".1..",   # r2 enemy beyond
    "....",
])
s = FFKState(board=b, to_move=0)
if "1,0>1,2" in set(G.legal_moves(s)):
    fail("must NOT allow jumping over an empty gap")

# ---- (2e) diagonal is NOT a move ----
b = board_from([
    "0...",   # r0 own at (0,0)
    ".0..",   # r1 own at (1,1)
    "..1.",   # r2 enemy at (2,2)
    "....",
])
s = FFKState(board=b, to_move=0)
if "0,0>2,2" in set(G.legal_moves(s)):
    fail("must NOT allow diagonal jumps")

# ---- (2f) LEGAL non-capturing slide to an adjacent EMPTY cell ----
# One lone Black piece at (1,1); all four orthogonal neighbours empty.
b = board_from([
    "....",   # r0
    ".0..",   # r1  Black at (1,1)
    "....",   # r2
    "....",   # r3
])
s = FFKState(board=b, to_move=0)
moves = set(G.legal_moves(s))
# All four orthogonal one-step slides to empty cells are legal.
for mv in ("1,1>0,1", "1,1>2,1", "1,1>1,0", "1,1>1,2"):
    if mv not in moves:
        fail(f"expected legal non-capturing slide {mv}")
# A diagonal slide is NOT legal.
if "1,1>2,2" in moves:
    fail("must NOT allow a diagonal slide")
# Applying a slide relocates the piece; piece counts are unchanged.
res = G.apply_move(s, "1,1>2,1")
if (1, 1) in res.board:
    fail("after slide, the from-cell must be vacated")
if res.board.get((2, 1)) != 0:
    fail("after slide, the piece must occupy the destination cell")
if len(res.board) != 1:
    fail("a non-capturing slide must not change piece counts")

# ---- (4) the formerly-degenerate position is NOT an instant loss ----
# Rows top->bottom '00../00../..11/..11' (board_from is bottom-up): the two
# armies have separated with no capture available. Capture-only would declare
# the player to move a loser; with slides they have legal moves and the game
# continues.
b = board_from([
    "..11",   # r0  (bottom)
    "..11",   # r1
    "00..",   # r2
    "00..",   # r3  (top)
])
s = FFKState(board=b, to_move=0)
moves = set(G.legal_moves(s))
if not moves:
    fail("separated position must NOT be an instant loss (slides exist)")
if G.is_terminal(s):
    fail("separated position must NOT be terminal now that slides exist")
# There is no capture available here, so all legal moves must be 1-step slides.
for mv in moves:
    frm, to = mv.split(">")
    fc, fr = map(int, frm.split(","))
    tc, tr = map(int, to.split(","))
    if abs(fc - tc) + abs(fr - tr) != 1:
        fail(f"separated position should yield only slides; got {mv}")
# A representative slide into an adjacent empty cell is present.
if "1,2>2,2" not in moves and "1,3>2,3" not in moves:
    fail("expected a slide toward the empty middle columns")

# ---- (3) WIN: opponent reduced so they cannot move ----
# Player 0 to move can capture White's last useful piece, leaving White unable
# to jump -> player 0 wins immediately.
b = board_from([
    ".0..",   # r0 own
    ".0..",   # r1 own
    ".1..",   # r2 enemy (the only White piece)
    "....",
])
s = FFKState(board=b, to_move=0)
res = G.apply_move(s, "1,0>1,2")
if not G.is_terminal(res):
    fail("capturing the opponent's last piece must end the game")
ret = G.returns(res)
if ret != [1.0, -1.0]:
    fail(f"player 0 should win after annihilating opponent; got {ret}")
if res.winner != 0:
    fail("winner must be recorded as player 0")

# A genuinely BLOCKED player -> loss. White has one piece cornered at (0,0):
# both its orthogonal neighbours (1,0) and (0,1) are Black, so it can neither
# jump (no adjacent OWN piece to leap) nor slide (both neighbours occupied).
b = board_from([
    "10..",   # r0: White at (0,0), Black at (1,0)
    "0...",   # r1: Black at (0,1)
    "....",
    "....",
])
s = FFKState(board=b, to_move=1)
if G.legal_moves(s):
    fail("a fully blocked lone piece must have NO legal move (no jump, no slide)")
if not G.is_terminal(s):
    fail("a player with no legal move is in a terminal (lost) position")
if G.returns(s) != [1.0, -1.0]:
    fail("the player with no move (White) must lose")

# ---- serialize round-trip ----
s = G.initial_state()
s = G.apply_move(s, G.legal_moves(s)[0])
d = G.serialize(s)
back = G.deserialize(d)
if G.serialize(back) != d:
    fail("serialize must round-trip")

# ---- a short self-play sanity loop terminates ----
import random
rng = random.Random(7)
for _ in range(20):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s) and steps < 300:
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        steps += 1
    if not G.is_terminal(s):
        fail("random game failed to terminate")
    r = G.returns(s)
    if len(r) != 2 or abs(sum(r)) > 1e-9 and r != [0.0, 0.0]:
        fail(f"returns must be zero-sum/well-formed; got {r}")

print("SELFTEST OK")
sys.exit(0)
