#!/usr/bin/env python3
"""Standalone correctness anchor for Opulent Chess (Greg Strong, 2005).

Run from the engine dir with::

    PYTHONPATH=. python3 games/opulent_chess/selftest.py

Pure stdlib + this game only, fast (~5s). Prints ``SELFTEST OK`` and exits 0 on
success, nonzero on any failure.

It asserts:

* the setup (48 men; R W . . . . . . W R / C L N B Q K B N L A / pawns, mirrored);
* the opening **perft** baseline d1=52, d2=2704, d3=147909. No published node
  counts exist for Opulent Chess, so these are frozen self-computed values, but
  d1=52 is fully hand-verified against the source diagram (per side: 20 pawn
  moves, rooks 0, wizards 2+2, chancellor 2, lions 3+3, knights 4+4,
  bishops 2+2, queen 3, king 3, archbishop 2 = 52);
* exact move-target sets for the **Lion** (Half-Duck: 2/3-square orthogonal
  leaps over intervening men + ferz), the **Wizard** (camel + ferz) and the
  augmented **Knight** (knight + wazir), including jumping, captures and
  own-piece blocks;
* the **Archbishop** keeps the ORTHODOX knight component (no wazir step);
* **en passant** after a third-rank double step;
* the Grand-Chess **promotion** rule: optional-with-choice on rank 9, mandatory
  on rank 10, only to types the owner has lost, and a full-complement pawn is
  **stuck** on the 9th rank (may not enter the 10th);
* a **checkmate** reached via apply_move (terminal + the mated side loses);
* serialize round-trips.
"""

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.opulent_chess.game import OpulentChess

G = OpulentChess()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def perft(state, depth):
    if depth == 0:
        return 1
    return sum(perft(G.apply_move(state, m), depth - 1)
               for m in G.legal_moves(state))


def targets(board, frm, extra=None):
    """The set of destination cells of legal moves from ``frm`` (white to move)."""
    st = CState(board=dict(board), to_move=WHITE)
    if extra:
        extra(st)
    out = set()
    for m in G.legal_moves(st):
        raw = m.split("=")[0]
        if ">" not in raw:
            continue
        f, t = raw.split(">")
        if f == f"{frm[0]},{frm[1]}":
            out.add(tuple(int(x) for x in t.split(",")))
    return out


# --------------------------------------------------------------------------- #
# 1. Setup
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
check(len(s0.board) == 48, "48 men at the start (24 per side)")
RANK2 = ["C", "L", "N", "B", "Q", "K", "B", "N", "L", "A"]
for i, t in enumerate(RANK2):
    check(s0.board[(i, 1)] == (WHITE, t), "White rank 2 is C L N B Q K B N L A")
    check(s0.board[(i, 8)] == (BLACK, t), "Black rank 9 is C L N B Q K B N L A")
for c in range(10):
    check(s0.board[(c, 2)] == (WHITE, "P"), "White pawns on rank 3")
    check(s0.board[(c, 7)] == (BLACK, "P"), "Black pawns on rank 8")
for c, t in [(0, "R"), (1, "W"), (8, "W"), (9, "R")]:
    check(s0.board[(c, 0)] == (WHITE, t), "White rank 1 is R W . ... . W R")
    check(s0.board[(c, 9)] == (BLACK, t), "Black rank 10 is R W . ... . W R")

# --------------------------------------------------------------------------- #
# 2. Perft (frozen; d1 hand-verified against the source diagram)
# --------------------------------------------------------------------------- #
for d, want in ((1, 52), (2, 2704), (3, 147909)):
    got = perft(s0, d)
    check(got == want, f"perft({d}) = {got}, expected {want}")

# --------------------------------------------------------------------------- #
# 3. Piece movement anchors (kings far away in the corners)
# --------------------------------------------------------------------------- #
KINGS = {(0, 0): (WHITE, "K"), (9, 9): (BLACK, "K")}

# Lion on an empty board: 2/3-square orthogonal leaps + one-step diagonal.
LION_SET = {(2, 4), (6, 4), (4, 2), (4, 6), (1, 4), (7, 4), (4, 1), (4, 7),
            (3, 3), (5, 3), (3, 5), (5, 5)}
got = targets({**KINGS, (4, 4): (WHITE, "L")}, (4, 4))
check(got == LION_SET, f"Lion targets on empty board: {sorted(got)}")

# Lion jumps: own pawns on all four adjacent orthogonals (not Lion squares) do
# not stop the 2/3 leaps; an enemy pawn on (4,6) is capturable; an own pawn on
# (4,2) blocks that square but NOT the leap over it to (4,1).
b = {**KINGS, (4, 4): (WHITE, "L"),
     (4, 5): (WHITE, "P"), (5, 4): (WHITE, "P"),
     (3, 4): (WHITE, "P"), (4, 3): (WHITE, "P"),
     (4, 6): (BLACK, "P"), (4, 2): (WHITE, "P")}
got = targets(b, (4, 4))
check(got == LION_SET - {(4, 2)},
      f"Lion leaps over men, captures (4,6), blocked only on own (4,2): {sorted(got)}")

# Wizard: camel (1,3) leaps + ferz.
WIZ_SET = {(5, 7), (3, 7), (5, 1), (3, 1), (7, 5), (7, 3), (1, 5), (1, 3),
           (3, 3), (5, 3), (3, 5), (5, 5)}
got = targets({**KINGS, (4, 4): (WHITE, "W")}, (4, 4))
check(got == WIZ_SET, f"Wizard targets on empty board: {sorted(got)}")

# Augmented Knight: orthodox knight + wazir.
KN_SET = {(5, 6), (6, 5), (3, 6), (2, 5), (5, 2), (6, 3), (3, 2), (2, 3),
          (5, 4), (3, 4), (4, 5), (4, 3)}
got = targets({**KINGS, (4, 4): (WHITE, "N")}, (4, 4))
check(got == KN_SET, f"Knight (knight+wazir) targets: {sorted(got)}")

# Archbishop = bishop + ORTHODOX knight: no wazir step (the Knight's bonus does
# not carry over to the compounds).
got = targets({(0, 0): (WHITE, "K"), (9, 0): (BLACK, "K"),
               (4, 4): (WHITE, "A")}, (4, 4))
check((4, 5) not in got and (4, 3) not in got,
      "Archbishop has NO one-step orthogonal move")
check({(5, 6), (2, 3), (5, 5), (8, 8), (1, 7)} <= got,
      "Archbishop keeps knight leaps and bishop rays")

# --------------------------------------------------------------------------- #
# 4. En passant after a third-rank double step
# --------------------------------------------------------------------------- #
st = CState(board={(0, 0): (WHITE, "K"), (9, 9): (BLACK, "K"),
                   (2, 2): (WHITE, "P"), (3, 4): (BLACK, "P")}, to_move=WHITE)
check("2,2>2,4" in G.legal_moves(st), "double step from the third rank")
st = G.apply_move(st, "2,2>2,4")
check("3,4>2,3" in G.legal_moves(st), "en passant capture is offered")
st = G.apply_move(st, "3,4>2,3")
check(st.board.get((2, 3)) == (BLACK, "P") and (2, 4) not in st.board,
      "en passant removes the double-stepped pawn")

# --------------------------------------------------------------------------- #
# 5. Promotion: capture onto rank 9 (optional, only to lost types)
# --------------------------------------------------------------------------- #
st = CState(board={(5, 0): (WHITE, "K"), (9, 9): (BLACK, "K"),
                   (1, 7): (WHITE, "P"), (0, 8): (BLACK, "R")}, to_move=WHITE)
ms = G.legal_moves(st)
check("1,7>0,8" in ms, "rank-9 promotion is optional (plain capture allowed)")
for t in ("Q", "C", "A", "R", "B", "N", "L", "W"):
    check(f"1,7>0,8={t}" in ms, f"may promote to lost type {t} on rank 9")
st2 = G.apply_move(st, "1,7>0,8=Q")
check(st2.board[(0, 8)] == (WHITE, "Q"), "capture-promotion produced a Queen")

# Mandatory on rank 10: the plain push is NOT offered.
st = CState(board={(5, 0): (WHITE, "K"), (9, 9): (BLACK, "K"),
                   (0, 8): (WHITE, "P")}, to_move=WHITE)
ms = G.legal_moves(st)
check("0,8>0,9" not in ms, "moving to rank 10 without promoting is illegal")
check(all(f"0,8>0,9={t}" in ms for t in ("Q", "C", "A", "R", "B", "N", "L", "W")),
      "rank-10 promotion to any lost type")

# Stuck pawn: with a FULL complement (nothing lost) the pawn may not enter
# rank 10 at all.
full = {(5, 0): (WHITE, "K"), (4, 0): (WHITE, "Q"), (3, 0): (WHITE, "C"),
        (5, 1): (WHITE, "A"), (6, 0): (WHITE, "R"), (7, 0): (WHITE, "R"),
        (1, 0): (WHITE, "B"), (2, 0): (WHITE, "B"), (0, 1): (WHITE, "N"),
        (1, 1): (WHITE, "N"), (2, 1): (WHITE, "L"), (3, 1): (WHITE, "L"),
        (4, 1): (WHITE, "W"), (6, 1): (WHITE, "W"),
        (0, 8): (WHITE, "P"), (9, 9): (BLACK, "K")}
st = CState(board=full, to_move=WHITE)
ms = G.legal_moves(st)
check(not any(m.startswith("0,8>") for m in ms),
      "a full-complement pawn is stuck on rank 9")
check(len(ms) > 0, "the side with the stuck pawn still has other moves")

# --------------------------------------------------------------------------- #
# 6. Checkmate reached via apply_move
# --------------------------------------------------------------------------- #
st = CState(board={(9, 7): (WHITE, "K"), (7, 8): (WHITE, "Q"),
                   (9, 9): (BLACK, "K")}, to_move=WHITE)
check(not G.is_terminal(st), "pre-mate position is live")
st = G.apply_move(st, "7,8>8,8")
check(G.is_terminal(st), "Qi9 is checkmate")
check(G.returns(st) == [1.0, -1.0], "White wins the mate")

# --------------------------------------------------------------------------- #
# 7. Serialize round-trip
# --------------------------------------------------------------------------- #
s1 = G.apply_move(s0, G.legal_moves(s0)[0])
for s in (s0, s1):
    rt = G.deserialize(G.serialize(s))
    check(G._poskey_state(rt) == G._poskey_state(s) and rt.ply == s.ply,
          "serialize round-trips")

print("SELFTEST OK")
