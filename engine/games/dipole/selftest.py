#!/usr/bin/env python3
"""Dipole correctness anchors -- pure stdlib, run by tests/test_games.py.

Everything here is checked against the designer's own rulebook,
https://www.marksteeregames.com/Dipole_rules.pdf (a vector PDF *with* a text
layer; Fig. 1 was read at 400 dpi to fix the two starting squares).

A second, independent anchor lives in `_diff_gameslib.py` (manual/one-time --
it needs node + the AbstractPlay `gameslib` clone): it replays random games
through both engines and compares the whole on-board move set, the whole board,
the side to move, terminality and the winner.  What follows re-checks the rules
with constructed positions and invariants, without needing node.
"""

import dataclasses
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                              # noqa: E402
from agp.mcts import MCTSBot                                      # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
M = sys.modules[type(G).__module__]          # the LIVE module object
DState = M.DState
WHITE, BLACK = M.WHITE, M.BLACK

FAILS = []


def ok(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


def st(board, to_move=WHITE, size=8, ply=0):
    """Hand-built state.  `board` maps 'c,r' -> (owner, height)."""
    return DState(size=size, to_move=to_move, ply=ply,
                  board={M._cell(k): v for k, v in board.items()})


def moves(s):
    return set(G.legal_moves(s))


def after(s, mv):
    return G.apply_move(s, mv)


# ==========================================================================
# 1. Setup -- Fig. 1 of the rulebook (and the 10x10 note in the text)
# ==========================================================================
s8 = G.initial_state()
ok(s8.size == 8, "default board is 8x8")
ok(s8.board == {(4, 0): (WHITE, 12), (3, 7): (BLACK, 12)},
   f"8x8 setup is White 12 on e1 and Black 12 on d8, got {s8.board}")
ok(s8.to_move == WHITE, "White (the bottom seat) moves first")

s10 = G.initial_state(options={"size": 10})
ok(s10.board == {(4, 0): (WHITE, 20), (5, 9): (BLACK, 20)},
   f"10x10 setup is White 20 on e1 and Black 20 on f10, got {s10.board}")

for (c, r) in list(s8.board) + list(s10.board):
    ok((c + r) % 2 == 0, f"pole square {c},{r} is a DARK square")
ok(M.pole_columns(8) == (4, 3) and M.pole_columns(10) == (4, 5),
   "pole columns are 8x8 (4,3) = e1/d8 and 10x10 (4,5) = e1/f10")

# ==========================================================================
# 2. The opening move list, move by move.
#
# White's 12-stack on e1 may move a k-substack exactly k squares N/NE/NW.
#   N  (straight => k must be EVEN, only dark squares exist): k=2,4,6 land on
#      e3,e5,e7; k=8,10,12 fall off the top edge.
#   NE: k=1,2,3 land on f2,g3,h4; k>=4 falls off the right edge.
#   NW: k=1..4 land on d2,c3,b4,a5; k>=5 falls off the left edge.
# so 10 on-board destinations and bear-off counts {4..12}.
# The 10 on-board moves match the AbstractPlay gameslib reference EXACTLY.
# ==========================================================================
EXPECT8 = {"4,0>4,2", "4,0>4,4", "4,0>4,6",              # N, k = 2,4,6
           "4,0>5,1", "4,0>6,2", "4,0>7,3",              # NE, k = 1,2,3
           "4,0>3,1", "4,0>2,2", "4,0>1,3", "4,0>0,4"}   # NW, k = 1,2,3,4
EXPECT8 |= {f"4,0>off={k}" for k in range(4, 13)}
ok(moves(s8) == EXPECT8, f"8x8 opening move set (19 moves), got {sorted(moves(s8))}")
ok(len(moves(s10)) == 29, f"10x10 opening has 29 moves, got {len(moves(s10))}")

# ==========================================================================
# 3. Distance == size of the moved sub-stack (the game's central rule)
# ==========================================================================
one = st({"4,0": (WHITE, 1)})
ok(moves(one) == {"4,0>3,1", "4,0>5,1"},
   f"a lone checker moves exactly one square, diagonally forward only: {moves(one)}")
three = st({"4,0": (WHITE, 3)})
ok(moves(three) == {"4,0>3,1", "4,0>5,1", "4,0>2,2", "4,0>4,2", "4,0>6,2",
                    "4,0>1,3", "4,0>7,3"},
   f"a 3-stack can move 1, 2 or 3 squares: {sorted(moves(three))}")
ns = after(three, "4,0>1,3")
ok(ns.board == {(1, 3): (WHITE, 3)}, f"moving all 3 empties the source: {ns.board}")
ns = after(three, "4,0>5,1")
ok(ns.board == {(4, 0): (WHITE, 2), (5, 1): (WHITE, 1)},
   f"moving 1 of 3 leaves 2 behind: {ns.board}")

# ==========================================================================
# 4. Directions.  Non-capturing moves: forward / diagonally forward ONLY.
#    Straight moves need an EVEN count (only dark squares exist).
# ==========================================================================
mid = st({"4,4": (WHITE, 2)})
ok(moves(mid) == {"4,4>3,5", "4,4>5,5", "4,4>2,6", "4,4>4,6", "4,4>6,6"},
   f"no sideways or backward non-capturing moves: {sorted(moves(mid))}")
ok("4,4>4,5" not in moves(st({"4,4": (WHITE, 1)})),
   "a 1-stack may NOT move straight forward (that lands on a light square)")
ok("4,4>4,6" in moves(mid), "a 2-stack MAY move straight forward two squares")
black_mid = st({"4,4": (BLACK, 2)}, to_move=BLACK)
ok(moves(black_mid) == {"4,4>3,3", "4,4>5,3", "4,4>2,2", "4,4>4,2", "4,4>6,2"},
   f"Black's forward is DOWN the board: {sorted(moves(black_mid))}")

# ==========================================================================
# 5. Captures: any of the eight directions, enemy stack must be <= movers.
# ==========================================================================
cap = st({"4,4": (WHITE, 2),
          "3,3": (BLACK, 1), "5,3": (BLACK, 1),        # diagonally BACKWARD
          "2,4": (BLACK, 1), "6,4": (BLACK, 1),        # SIDEWAYS (k=2, even)
          "4,2": (BLACK, 1),                           # straight BACKWARD (k=2)
          "3,5": (BLACK, 1)})                          # diagonally forward
mv = moves(cap)
for tgt in ("3,3", "5,3", "2,4", "6,4", "4,2", "3,5"):
    ok(f"4,4>{tgt}" in mv, f"capture toward {tgt} is legal in all 8 directions")
ok("4,4>3,3" in mv and "4,4>2,2" not in mv,
   "a backward step is legal ONLY as a capture -- never to an empty square")
big = st({"4,4": (WHITE, 2), "3,5": (BLACK, 3)})
ok("4,4>3,5" not in moves(big), "a 1-substack may not capture a 3-stack")
ok("4,4>2,6" in moves(big), "...but the 2-substack may still move past it")
eq = st({"4,4": (WHITE, 2), "2,6": (BLACK, 2)})
ok("4,4>2,6" in moves(eq), "an EQUAL-sized enemy stack may be captured")
gt = st({"4,4": (WHITE, 2), "2,6": (BLACK, 3)})
ok("4,4>2,6" not in moves(gt), "a LARGER enemy stack may not be captured")
ns = after(eq, "4,4>2,6")
ok(ns.board == {(2, 6): (WHITE, 2)},
   f"capture removes the WHOLE enemy stack and lands the movers: {ns.board}")
part = st({"4,4": (WHITE, 5), "2,6": (BLACK, 2)})
ns = after(part, "4,4>2,6")
ok(ns.board == {(4, 4): (WHITE, 3), (2, 6): (WHITE, 2)},
   f"a 2-substack of a 5-stack captures and leaves 3 behind: {ns.board}")

# Captures in the non-forward directions must also EXECUTE correctly, not merely
# be generated.  The moved count is the CHEBYSHEV distance, so a SIDEWAYS
# capture (row unchanged) is precisely the case a row-delta-only reading of the
# move string turns into k = 0 -- which silently banks a phantom 0-high stack
# and never removes a checker from the mover.
side = st({"4,4": (WHITE, 5), "2,4": (BLACK, 2)})
ok(after(side, "4,4>2,4").board == {(4, 4): (WHITE, 3), (2, 4): (WHITE, 2)},
   f"a SIDEWAYS capture moves exactly 2 checkers 2 squares: {after(side, '4,4>2,4').board}")
ok(G.describe_move(side, "4,4>2,4") == "White e5xc5 (2, takes 2)",
   G.describe_move(side, "4,4>2,4"))
diag_back = st({"4,4": (WHITE, 5), "6,2": (BLACK, 2)})
ok(after(diag_back, "4,4>6,2").board == {(4, 4): (WHITE, 3), (6, 2): (WHITE, 2)},
   f"a diagonally BACKWARD capture: {after(diag_back, '4,4>6,2').board}")
str_back = st({"4,4": (WHITE, 5), "4,2": (BLACK, 1)})
ok(after(str_back, "4,4>4,2").board == {(4, 4): (WHITE, 3), (4, 2): (WHITE, 2)},
   f"a straight BACKWARD capture: {after(str_back, '4,4>4,2').board}")

# ==========================================================================
# 6. Nothing ever blocks a move (rulebook Fig. 4: the white stack jumps the
#    black 5-stack).
# ==========================================================================
jump = st({"1,1": (WHITE, 3), "2,2": (BLACK, 5)})
ok("1,1>4,4" in moves(jump), "a 3-stack jumps clean over an intervening 5-stack")
ok("1,1>2,2" not in moves(jump), "...but may not land on it (1 < 5)")

# ==========================================================================
# 7. Merging (rulebook Fig. 4): forward only, heights add.
# ==========================================================================
mg = st({"1,1": (WHITE, 4), "4,4": (WHITE, 2)})
ok("1,1>4,4" in moves(mg), "a 3-substack may merge onto a friendly stack 3 away")
ns = after(mg, "1,1>4,4")
ok(ns.board == {(1, 1): (WHITE, 1), (4, 4): (WHITE, 5)},
   f"merge: 3 + 2 = 5, one left behind (Fig. 4): {ns.board}")
back = st({"4,4": (WHITE, 4), "1,1": (WHITE, 2)})
ok("4,4>1,1" not in moves(back), "merging BACKWARD is illegal")

# ==========================================================================
# 8. Bear-off ("if you move a stack out of bounds you must remove it").
# ==========================================================================
far = st({"4,6": (WHITE, 1)})
ok(moves(far) == {"4,6>3,7", "4,6>5,7"},
   f"a singleton one row from the edge just steps: {moves(far)}")
edge = st({"5,7": (WHITE, 1)})
ok(moves(edge) == {"5,7>off=1"},
   f"a singleton on the far row can only be removed, diagonally: {moves(edge)}")
edge2 = st({"5,7": (WHITE, 2)})
ok(moves(edge2) == {"5,7>off=1", "5,7>off=2"},
   f"a 2-stack on the far row may remove 1 or 2: {sorted(moves(edge2))}")
ok(after(edge2, "5,7>off=1").board == {(5, 7): (WHITE, 1)},
   "bearing off 1 of 2 leaves 1 on the board")
ok(after(edge2, "5,7>off=2").board == {}, "bearing off 2 of 2 empties the square")
# The dark-square parity rule still applies OFF the board: a 1-stack on row 6
# cannot go straight off (row 7 is on the board anyway), and a 1-stack on the
# far row cannot go straight off either, because (c, 8) is a light square.
straight_off = st({"5,7": (WHITE, 3)})
ok("5,7>off=2" in moves(straight_off) and "5,7>off=3" in moves(straight_off),
   "straight-off with an even count and diagonal-off with any count")
ok(sorted(moves(straight_off)) == ["5,7>off=1", "5,7>off=2", "5,7>off=3"],
   f"3-stack on the far row: {sorted(moves(straight_off))}")
# Bear-off is forward-only: a Black stack on row 7 has no bear-off at all.
bk = st({"5,7": (BLACK, 1)}, to_move=BLACK)
ok(all(">off" not in m for m in moves(bk)),
   "Black cannot bear off across its OWN back row (removal is forward only)")

# ==========================================================================
# 9. Winning -- and losing by running yourself off the board.
# ==========================================================================
win = st({"4,4": (WHITE, 2), "2,6": (BLACK, 2)})
ns = after(win, "4,4>2,6")
ok(ns.over and ns.winner == WHITE and G.returns(ns) == [1, -1],
   "capturing the last enemy stack wins")
suicide = st({"5,7": (WHITE, 1), "0,0": (BLACK, 3)})
ns = after(suicide, "5,7>off=1")
ok(ns.over and ns.winner == BLACK and G.returns(ns) == [-1, 1],
   "bearing off your own LAST checker loses -- the opponent wins")
# A finished game must offer no moves.  Check that on the CAPTURE-wipe terminal,
# where the side to move is the WINNER and still has a stack that could move --
# on the self-bear-off terminal above the mover has no checkers left, so the
# guard would pass even if it were deleted.
wipe = after(win, "4,4>2,6")
ok(wipe.over and G.legal_moves(wipe) == [],
   f"a FINISHED game offers no moves: {G.legal_moves(wipe)}")
ok(G._moves_for(wipe, wipe.to_move) != [],
   "...and the check is not vacuous -- the winner's surviving stack can move")

# The very first move of the game can end it: e1>off=12 removes all of White.
op = after(s8, "4,0>off=12")
ok(op.over and op.winner == BLACK, "e1 bearing off all 12 hands Black the win")

# ==========================================================================
# 10. A DECISIVE RESULT OUTRANKS EVERY DRAW COUNTER.
#     Re-score the SAME winning position with the ply counter tripped and with
#     the ply cap patched down to nothing; the win must survive both.
# ==========================================================================
cap_real = M.ply_cap
try:
    poisoned = dataclasses.replace(win, ply=10 ** 9)
    ns = after(poisoned, "4,4>2,6")
    ok(ns.over and ns.winner == WHITE,
       "a win delivered past the ply cap is still a win (ply=1e9)")
    M.ply_cap = lambda size: 1                       # patch the LIVE module
    ns = after(win, "4,4>2,6")
    ok(ns.over and ns.winner == WHITE,
       "a win delivered at ply_cap == 1 is still a win")
    # ...and prove the patch actually BITES, so this test cannot go vacuous.
    quiet = st({"4,0": (WHITE, 6), "3,7": (BLACK, 6)})
    ns = after(quiet, "4,0>5,1")
    ok(ns.over and ns.winner is None,
       "with ply_cap patched to 1 a non-decisive move draws (the patch bites)")
finally:
    M.ply_cap = cap_real
ns = after(quiet, "4,0>5,1")
ok(not ns.over, "with the real ply cap the same quiet move does not end the game")
ok(M.ply_cap(8) == 3648 and M.ply_cap(10) == 16400,
   f"ply cap is the game's own bound: {M.ply_cap(8)} / {M.ply_cap(10)}")

# ==========================================================================
# 11. Sitting out ("if you have no moves available you must sit the game out
#     until you do have a move available").  A stuck player is SKIPPED -- the
#     engine hands the turn straight back to the player who can move.
# ==========================================================================
# White's lone checker on e5 can only step to d6 or f6, both held by Black
# 2-stacks it cannot capture; a far-off Black singleton makes the move.
sit = st({"4,4": (WHITE, 1), "3,5": (BLACK, 2), "5,5": (BLACK, 2),
          "0,6": (BLACK, 1)}, to_move=BLACK)
ok(moves(st({"4,4": (WHITE, 1), "3,5": (BLACK, 2), "5,5": (BLACK, 2)})) == set(),
   "the boxed-in White checker really has no legal move")
ns = after(sit, "0,6>1,5")
ok(not ns.over and ns.to_move == BLACK,
   f"Black moves again while White sits out (got to_move={ns.to_move}, over={ns.over})")
ok(G.legal_moves(ns) != [], "and legal_moves is still non-empty")
ok("White has no legal move" in G.render(ns)["caption"],
   f"the caption says who is sitting out: {G.render(ns)['caption']!r}")
# Both players stuck at once is a position Steere says cannot arise; force the
# branch anyway (instance-level patch) and check it is an HONEST DRAW.
orig_has = G._has_move
try:
    G._has_move = lambda s, p: False
    ns = after(quiet, "4,0>5,1")
    ok(ns.over and ns.winner is None and G.returns(ns) == [0, 0],
       "a genuine double stalemate is a draw, not a fabricated win")
    ok(after(win, "4,4>2,6").winner == WHITE,
       "...and a win still outranks the double-stalemate test too")
finally:
    G._has_move = orig_has
ok(after(quiet, "4,0>5,1").to_move == BLACK, "the instance patch was undone")

# ==========================================================================
# 12. serialize / deserialize -- compare the STATE OBJECTS, sweep a whole game.
# ==========================================================================
KEYS = {"size", "board", "to_move", "ply", "last", "over", "winner"}
rng = random.Random(11)
rt_states = 0
for size in (8, 10):
    for _ in range(6):
        s = G.initial_state(options={"size": size})
        while True:
            d = G.serialize(s)
            ok(set(d) == KEYS, f"serialize key set is exactly {sorted(KEYS)}, got {sorted(d)}")
            json.dumps(d)                                   # must be JSON-able
            back = G.deserialize(d)
            ok(back == s, f"deserialize(serialize(s)) == s  (ply {s.ply}, size {size})")
            ok(G.serialize(back) == d, "and it re-serializes identically")
            rt_states += 1
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
ok(rt_states > 150, f"round-trip swept {rt_states} states")

# ==========================================================================
# 13. Purity: apply_move must not touch the state it was given.
# ==========================================================================
s = G.initial_state()
snapshot = G.serialize(s)
board_id = id(s.board)
for m in G.legal_moves(s):
    ns = G.apply_move(s, m)
    ok(ns.board is not s.board, "apply_move returns a NEW board dict (no aliasing)")
ok(G.serialize(s) == snapshot and id(s.board) == board_id,
   "the input state is unchanged after generating every successor")

# ==========================================================================
# 14. render(): declared bounds per board size, and the tower spec.
# ==========================================================================
for size, corners in ((8, ["7,3", "0,4"]), (10, ["9,5", "0,4", "8,4"])):
    s = G.initial_state(options={"size": size})
    # Reach the far files through apply_move -- a check on a fresh state is
    # vacuous (both stacks sit near the middle).
    for tgt in corners:
        ok(f"4,0>{tgt}" in G.legal_moves(s),
           f"size {size}: {tgt} is reachable in one move")
    s2 = G.apply_move(s, f"4,0>{corners[0]}")
    for state in (s, s2):
        spec = G.render(state)
        b = spec["board"]
        ok(b["width"] == size and b["height"] == size,
           f"render declares {size}x{size}, got {b['width']}x{b['height']}")
        for p in spec["pieces"]:
            c, r = M._cell(p["cell"])
            ok(0 <= c < size and 0 <= r < size,
               f"rendered piece {p['cell']} is inside the declared {size}x{size} board")
    # ...and sweep random play so no later position leaks outside either.
    rng2 = random.Random(size)
    for _ in range(25):
        s = G.initial_state(options={"size": size})
        while not G.is_terminal(s):
            s = G.apply_move(s, rng2.choice(G.legal_moves(s)))
            spec = G.render(s)
            ok(spec["board"]["width"] == size and spec["board"]["height"] == size,
               "render dimensions stay constant")
            for p in spec["pieces"]:
                c, r = M._cell(p["cell"])
                ok(0 <= c < size and 0 <= r < size,
                   f"size {size}: rendered piece {p['cell']} outside the board")

# Tower spec: the stack list is the piece's height, every band its owner.
tower = st({"4,4": (WHITE, 7), "1,3": (BLACK, 2)})
spec = G.render(tower)
by_cell = {p["cell"]: p for p in spec["pieces"]}
ok(by_cell["4,4"]["stack"] == [WHITE] * 7 and by_cell["4,4"]["owner"] == WHITE,
   f"a 7-high White tower renders as 7 White bands: {by_cell['4,4']}")
ok(by_cell["1,3"]["stack"] == [BLACK] * 2 and by_cell["1,3"]["owner"] == BLACK,
   f"a 2-high Black tower renders as 2 Black bands: {by_cell['1,3']}")
ok(len(spec["board"]["tints"]) == 64
   and spec["board"]["tints"]["0,0"] != spec["board"]["tints"]["1,0"],
   "every square is tinted and the two colours differ (only dark squares play)")


# The PLAYABLE tint has to be visibly different from Board.jsx's hard-coded
# "last-move" fill, or the highlight silently disappears on the only squares a
# move can ever touch (that bug shipped once, at a 1.04:1 contrast ratio).
def _lum(hexcol):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)))
    return (lb + 0.05) / (la + 0.05)


BOARD_JSX_LAST_MOVE = "#3a3228"          # web/src/Board.jsx, hl == 'last-move'
dark_tint = spec["board"]["tints"]["0,0"]     # a playable (dark) square
light_tint = spec["board"]["tints"]["1,0"]
ok(_contrast(dark_tint, BOARD_JSX_LAST_MOVE) >= 1.25,
   f"the playable tint {dark_tint} must contrast with Board.jsx's last-move "
   f"fill {BOARD_JSX_LAST_MOVE} (got {_contrast(dark_tint, BOARD_JSX_LAST_MOVE):.2f}:1)")
ok(_contrast(dark_tint, light_tint) >= 1.5,
   f"the checkerboard must actually read as a checkerboard "
   f"({_contrast(dark_tint, light_tint):.2f}:1)")

# Highlights: the last move must mark both of its squares (a bear-off has only
# a source), and a fresh position must mark none.
ok(G.render(s8)["highlights"] == [], "the opening position has no last move")
hl_move = G.render(after(s8, "4,0>7,3"))["highlights"]
ok({(h["cell"], h["kind"]) for h in hl_move} == {("4,0", "last-move"), ("7,3", "last-move")},
   f"a board move highlights both of its squares: {hl_move}")
hl_off = G.render(after(s8, "4,0>off=12"))["highlights"]
ok([h["cell"] for h in hl_off] == ["4,0"], f"a bear-off highlights its source only: {hl_off}")

# Board-size option hygiene: the server passes `options` through from the API
# WITHOUT validating them against the manifest, so initial_state has to clamp.
ok(G.initial_state(options={"size": 3}).size == 8,
   "an out-of-range board size falls back to the standard 8x8")
ok(G.initial_state(options={"size": "10"}).size == 10
   and len(G.initial_state(options={"size": "10"}).board) == 2,
   "a stringly-typed size option still selects the 10x10 board")
# Bear-off moves are action buttons, so they must all carry a friendly label.
spec = G.render(s8)
offs = [m for m in G.legal_moves(s8) if ">off=" in m]
ok(offs and all(m in spec.get("actionNames", {}) for m in offs),
   "every bear-off action button has a label")

# describe_move covers all four move kinds.
ok(G.describe_move(s8, "4,0>4,2") == "White e1-e3 (2)", G.describe_move(s8, "4,0>4,2"))
ok(G.describe_move(s8, "4,0>off=5") == "White e1 bears off 5", G.describe_move(s8, "4,0>off=5"))
ok(G.describe_move(mg, "1,1>4,4") == "White b2+e5 (3, merge to 5)", G.describe_move(mg, "1,1>4,4"))
ok(G.describe_move(eq, "4,4>2,6") == "White e5xc7 (2, takes 2)", G.describe_move(eq, "4,4>2,6"))

# ==========================================================================
# 15. Termination.  The game is finite by construction (see ply_cap's proof);
#     these games must finish far short of the cap.
# ==========================================================================
rng = random.Random(3)
longest = 0
for size in (8, 10):
    for _ in range(80):
        s = G.initial_state(options={"size": size})
        n = 0
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            ok(ms != [], "legal_moves is non-empty on a non-terminal state")
            # "There will always be a move available to one player or the other"
            # -- the sit-out rule can never deadlock (see apply_move's proof).
            ok(G._has_move(s, WHITE) or G._has_move(s, BLACK),
               f"at least one player always has a move: {s.board}")
            before = {p: sum(h for o, h in s.board.values() if o == p) for p in (WHITE, BLACK)}
            s = G.apply_move(s, rng.choice(ms))
            got = {p: sum(h for o, h in s.board.values() if o == p) for p in (WHITE, BLACK)}
            # Material only ever goes DOWN (captures and bear-offs destroy
            # checkers; nothing creates them), and no stack may be empty.
            ok(got[WHITE] <= before[WHITE] and got[BLACK] <= before[BLACK],
               f"material never grows: {before} -> {got}")
            ok(all(hh >= 1 for _o, hh in s.board.values()),
               f"no zero-height stack on the board: {s.board}")
            n += 1
        longest = max(longest, n)
        ok(s.winner is not None, "a finished random game has a winner (no draws)")
        ok(sorted(G.returns(s)) == [-1, 1], "returns is +1 / -1 at a decisive terminal")
ok(longest < 300, f"random games finish far below the ply cap (longest {longest})")

# ==========================================================================
# 16. Bot plumbing -- heuristic shape, forced at the rollout cutoff.
# ==========================================================================
h = G.heuristic(st({"4,4": (WHITE, 6), "1,3": (BLACK, 2)}))
ok(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9
   and all(-1.0 <= x <= 1.0 for x in h) and h[0] > 0,
   f"heuristic() returns a 2-list of bounded, zero-sum payoffs: {h}")
bot = MCTSBot(random.Random(5), iterations=40, max_rollout=4)
start = G.initial_state()
ok(bot.select(G, start) in G.legal_moves(start),
   "MCTSBot with max_rollout=4 (forcing the heuristic cutoff) returns a legal move")

print(f"dipole selftest: {len(FAILS)} failure(s)")
if FAILS:
    sys.exit(1)
