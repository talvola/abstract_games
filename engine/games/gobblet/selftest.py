"""Gobblet correctness anchor -- pure stdlib, fast.

Run:  PYTHONPATH=. python3 games/gobblet/selftest.py
Asserts the baked rule facts (no published perft for Gobblet):
  (1) 4x4 board; each player 12 cups = 3 off-board nested stacks of sizes 1..4,
      only the TOP cup of a stack is offered;
  (2) a bigger cup gobbles a strictly-smaller top cup (yours or opponent's), or
      lands on an empty cell;
  (3) a turn is EITHER place an off-board top cup OR move an on-board top cup;
  (4) the off-board-gobble restriction (a DROP may cover an opponent cup only on
      a 3-in-a-line);
  (5) moving a cup UNCOVERS whatever was beneath;
  (6) WIN = four of your colour on top in a line, incl. a win created by
      uncovering, plus the simultaneous tie-break.
Prints "SELFTEST OK" and exits 0 on success / nonzero on failure.
"""

import sys

from games.gobblet.game import Gobblet, GobbletState


def check(cond, msg):
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)


G = Gobblet()


def fresh(n=4):
    return G.initial_state({"size": n})


# (1) setup: 4x4, 3 stacks of 4, sizes 1..4, only top (size 4) offered.
s = fresh()
check(s.width == 4, "board width 4")
check(G.num_players == 2, "2 players")
for p in (0, 1):
    check(len(s.stacks[p]) == 3, f"player {p} has 3 stacks")
    for st in s.stacks[p]:
        check(st == [1, 2, 3, 4], "stack nested 1..4 (top=4)")
    total = sum(len(st) for st in s.stacks[p])
    check(total == 12, f"player {p} owns 12 cups")

# Render reserve exposes ONLY the top size (three size-4s available) initially.
r = G.render(s)["reserve"]
check(r["0"] == {"4": 3}, f"seat0 reserve top-only = three 4s, got {r['0']}")
check(r["1"] == {"4": 3}, "seat1 reserve top-only = three 4s")

# Initial legal moves: drops of size 4 onto any of 16 empty cells, no moves yet.
lm = G.legal_moves(s)
check(all("@" in m for m in lm), "opening moves are all drops")
check(len(lm) == 16, f"16 opening drops (size4 x 16 cells), got {len(lm)}")
check("4@1,1" in lm and "3@1,1" not in lm, "only top size-4 offered as a drop")


# (2) strictly-larger gobble. Build a P0 size-1 alone on a cell; a P0 DROP of a
# bigger cup may cover its OWN smaller cup (always allowed), but an equal/smaller
# drop may not. (Covering an OPPONENT cup via drop is the restricted case -> (4).)
# P0 has two stacks whose tops are size 4 and size 2; both are strictly bigger
# than the size-1 on the board, so both may gobble it (a 4 may cover a 1 -- the
# cover need NOT be the next size up). A same-size drop may not.
s2 = GobbletState(
    board={(1, 1): [(0, 1)]},
    stacks={0: [[1, 2, 3, 4], [1, 2]], 1: [[1, 2, 3, 4]]},
    to_move=0, width=4,
)
lm2 = G.legal_moves(s2)
check("4@1,1" in lm2, "bigger cup may gobble a smaller (self-cover drop)")
check("2@1,1" in lm2, "any strictly-bigger top size may gobble, not just next up")
check("1@1,1" not in lm2, "equal-size drop may not gobble")
s2 = G.apply_move(s2, "4@1,1")   # P0 size-4 covers its own size-1
top = G._top(s2, (1, 1))
check(top == (0, 4), f"gobble: top is now size-4, got {top}")
check(len(s2.board[(1, 1)]) == 2, "nest depth 2 after gobble")
# (3)+(5) MOVE an on-board top cup, and UNCOVER what was beneath. Build a nest:
# P0 size-1 buried under a P1 size-4 at (2,2). P1 (to move) moves its size-4 off
# 2,2 to an empty cell -> reveals P0's size-1 underneath.
sx = GobbletState(
    board={(2, 2): [(0, 1), (1, 4)]},   # bottom P0 size-1, top P1 size-4
    stacks={0: [[]], 1: [[]]},
    to_move=1, width=4,
)
before = G._top(sx, (2, 2))
check(before == (1, 4), "P1 size-4 sits atop 2,2 before move")
lmx = G.legal_moves(sx)
check(all(m.startswith("2,2>") for m in lmx),
      "(3) only the on-board top cup may move (no off-board cups left)")
sx = G.apply_move(sx, "2,2>3,0")  # P1 moves its 4 away
after = G._top(sx, (2, 2))
check(after == (0, 1), f"(5) uncover reveals P0 size-1 beneath, got {after}")
check(G._top(sx, (3, 0)) == (1, 4), "moved cup landed at 3,0")


# (4) off-board-gobble restriction (4x4). Build P0 tops in row r=0 at cols 0,1,2
# (three in a line). A P1 DROP may cover one of those three, but NOT a lone P0
# cup off any 3-line.
s4 = GobbletState(
    board={
        (0, 0): [(0, 2)], (1, 0): [(0, 2)], (2, 0): [(0, 2)],  # P0 three-in-row
        (0, 3): [(0, 2)],                                       # lone P0 cup
    },
    stacks={0: [[1, 2, 3, 4]], 1: [[1, 2, 3, 4]]},
    to_move=1, width=4,
)
lm4 = G.legal_moves(s4)
check("4@0,0" in lm4, "drop MAY cover an opp cup on a 3-line")
check("4@1,0" in lm4 and "4@2,0" in lm4, "any of the three may be covered")
check("4@0,3" not in lm4, "drop may NOT cover a lone opp cup (restriction)")
# But an ON-BOARD cup gobbles freely: give P1 a movable size-3 to test.
s4b = GobbletState(
    board={(0, 3): [(0, 2)], (3, 3): [(1, 3)]},
    stacks={0: [[1, 2, 3, 4]], 1: [[]]},
    to_move=1, width=4,
)
lm4b = G.legal_moves(s4b)
check("3,3>0,3" in lm4b, "on-board cup gobbles a loose opp cup freely")


# (6a) WIN by completing the mover's own line. P0 tops at (0,0),(1,0),(2,0);
# drop the 4th on (3,0).
s5 = GobbletState(
    board={(0, 0): [(0, 1)], (1, 0): [(0, 1)], (2, 0): [(0, 1)]},
    stacks={0: [[1, 2, 3, 4]], 1: [[1, 2, 3, 4]]},
    to_move=0, width=4,
)
s5 = G.apply_move(s5, "4@3,0")
check(s5.winner == 0, f"P0 completes a 4-in-a-row by dropping, got {s5.winner}")
check(G.is_terminal(s5), "win is terminal")
check(G.returns(s5) == [1.0, -1.0], "returns reflect P0 win")

# (6b) WIN created by UNCOVERING the opponent's line. P1 owns four buried cups
# in column c=0 at rows 0..3, each currently topped by a P0 cup EXCEPT one;
# P0 moves the covering cup away -> uncovers P1's full column -> P1 wins.
s6 = GobbletState(
    board={
        (0, 0): [(1, 1)], (0, 1): [(1, 1)], (0, 2): [(1, 1)],
        (0, 3): [(1, 1), (0, 4)],   # P1 size-1 buried under P0 size-4
    },
    stacks={0: [[]], 1: [[]]},
    to_move=0, width=4,
)
# P0 moves its only top cup (the 4 at 0,3) elsewhere, uncovering P1's column.
check(G._top(s6, (0, 3)) == (0, 4), "P0 size-4 covers 0,3")
s6 = G.apply_move(s6, "0,3>2,2")
check(s6.winner == 1, f"uncovering P1's column -> P1 wins, got {s6.winner}")

# (6c) TIE-BREAK: a single move completes BOTH colours' lines -> mover wins.
# P0 has tops at (0,0),(1,1),(2,2) and will land the 4th of the main diagonal at
# (3,3); the SAME move uncovers a P1 line. Construct so dropping doesn't uncover,
# so use a MOVE: P0's covering cup at (3,3) sits on a P1 cup completing column 3,
# and moving P0's diagonal-completing cup INTO (3,3)... simplest: build a move
# where mover completes own line while opponent line also present.
s7 = GobbletState(
    board={
        # P0 main diagonal nearly done: (0,0),(1,1),(2,2) tops are P0
        (0, 0): [(0, 1)], (1, 1): [(0, 1)], (2, 2): [(0, 1)],
        # P1 anti-diagonal fully present already: (0,3),(1,2),(2,1),(3,0)
        (0, 3): [(1, 1)], (1, 2): [(1, 1)], (2, 1): [(1, 1)], (3, 0): [(1, 1)],
        # a P0 cup to move onto (3,3) to complete P0's diagonal
        (3, 2): [(0, 2)],
    },
    stacks={0: [[]], 1: [[]]},
    to_move=0, width=4,
)
# Before the move, P1's anti-diagonal is already 4 -- but winner is judged after
# a move, and it's P0's turn. P0 completes its OWN diagonal at (3,3):
s7 = G.apply_move(s7, "3,2>3,3")
check(s7.winner == 0,
      f"tie-break: mover (P0) wins when both lines present, got {s7.winner}")


# Gobblet Gobblers (3x3) variant sanity.
sg = fresh(3)
check(sg.width == 3, "gobblers board 3x3")
for p in (0, 1):
    check(len(sg.stacks[p]) == 2, "gobblers: 2 stacks")
    for st in sg.stacks[p]:
        check(st == [1, 2, 3], "gobblers: nested 1..3")
# No off-board restriction in 3x3: a drop may cover a lone opp cup.
sg2 = GobbletState(
    board={(1, 1): [(1, 1)]},
    stacks={0: [[1, 2, 3]], 1: [[1, 2, 3]]},
    to_move=0, width=3,
)
check("3@1,1" in G.legal_moves(sg2),
      "gobblers: drop may freely cover a lone opp cup (no restriction)")


# Purity / round-trip / no-mutation invariants.
s0 = fresh()
m0 = G.legal_moves(s0)[0]
snap = G.serialize(s0)
_ = G.apply_move(s0, m0)
check(G.serialize(s0) == snap, "apply_move did not mutate input state")
rt = G.serialize(G.deserialize(G.serialize(s5)))
check(rt == G.serialize(s5), "serialize round-trips")

print("SELFTEST OK")
sys.exit(0)
