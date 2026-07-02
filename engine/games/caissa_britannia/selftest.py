#!/usr/bin/env python3
"""Standalone correctness anchor for Caissa Britannia (Fergus Duniho, 2003).

Run from the engine dir with::

    PYTHONPATH=. python3 games/caissa_britannia/selftest.py

Pure stdlib + this game only, fast (~10s). Prints ``SELFTEST OK`` and exits 0
on success, nonzero on any failure.

It asserts:

* the setup (44 men; D R U B Q K B U R D / lions b/i / pawns on rank 3,
  mirrored);
* the opening **perft** baseline d1=56, d2=3127, d3=176883. No published node
  counts exist, so d2/d3 are frozen self-computed values, but d1=56 is fully
  hand-verified against the source diagram (per side: 20 pawn moves, rooks 0,
  dragons 0, bishops 3+3, unicorns 3+3, lions 9+9, prince consort 3,
  queen 3 = 56);
* exact move-target sets for the **Dragon** (two-square rider: leaps odd
  squares, blocked by an occupied landing square mid-ride), the **Unicorn**
  (bishop + nightrider, blocked at the first landing), the **Lion** (Leo:
  Queen-slide non-captures only, captures ONLY over exactly one screen -- an
  adjacent enemy is uncapturable, and it may not land on empty squares beyond
  the screen), the **Anglican Bishop** (diagonal slider + NON-capturing
  orthogonal step) and the **Prince Consort** (Queen-slide without capturing +
  one-step capture only);
* the **royal-Queen** mechanics: Queens may not face each other (both as a
  destination and as an xiangqi-style screen pin), a Queen may not move
  through or into an attacked square (and squares beyond are unreachable),
  checkmate of the Queen ends the game, stalemate is a draw, and bare Queen
  vs bare Queen is an insufficient-material draw;
* mandatory last-rank **promotion**: Knight always available, other types only
  while the owner has fewer on the board than at the start ("liberating" a
  captured piece), never the (uncaptured) Queen, and no plain push;
* **en passant** after a third-rank double step;
* serialize round-trips and the render spec is a 10x10 square board.
"""

import sys

from agp.chesslike import CState, WHITE, BLACK
from games.caissa_britannia.game import CaissaBritannia

G = CaissaBritannia()


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


def targets(board, frm, to_move=WHITE):
    """The set of destination cells of legal moves from ``frm``."""
    st = CState(board=dict(board), to_move=to_move)
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
check(len(s0.board) == 44, "44 men at the start (22 per side)")
RANK1 = ["D", "R", "U", "B", "Q", "K", "B", "U", "R", "D"]
for i, t in enumerate(RANK1):
    check(s0.board[(i, 0)] == (WHITE, t), "White rank 1 is D R U B Q K B U R D")
    check(s0.board[(i, 9)] == (BLACK, t), "Black rank 10 mirrors rank 1")
for c in (1, 8):
    check(s0.board[(c, 1)] == (WHITE, "L"), "White Lions on b2/i2")
    check(s0.board[(c, 8)] == (BLACK, "L"), "Black Lions on b9/i9")
for c in range(10):
    check(s0.board[(c, 2)] == (WHITE, "P"), "White pawns on rank 3")
    check(s0.board[(c, 7)] == (BLACK, "P"), "Black pawns on rank 8")

# --------------------------------------------------------------------------- #
# 2. Perft (frozen; d1 hand-verified against the source diagram)
# --------------------------------------------------------------------------- #
for d, want in ((1, 56), (2, 3127), (3, 176883)):
    got = perft(s0, d)
    check(got == want, f"perft({d}) = {got}, expected {want}")

# Queens sit far apart in the corners for the piece anchors below; (0,0) and
# (9,8) share no line, so neither restricts the other.
QS = {(0, 0): (WHITE, "Q"), (9, 8): (BLACK, "Q")}

# --------------------------------------------------------------------------- #
# 3. Dragon: two-square rider; jumped odd squares ignored, landing squares block
# --------------------------------------------------------------------------- #
b = {**QS, (4, 4): (WHITE, "D"),
     (5, 5): (WHITE, "P"),      # on a jumped-over odd square: irrelevant
     (6, 6): (BLACK, "P"),      # capture target; also ends the (2,2) ride
     (4, 6): (WHITE, "P")}      # own piece on a landing square: blocks the ride
DRAGON_SET = {(6, 6),                       # capture over the ignored (5,5)
              (6, 2), (8, 0), (2, 6), (0, 8), (2, 2),
              (6, 4), (8, 4), (2, 4), (0, 4), (4, 2), (4, 0)}
got = targets(b, (4, 4))
check(got == DRAGON_SET, f"Dragon targets: {sorted(got)}")
check((8, 8) not in got, "Dragon ride ends on the captured piece")
check((4, 8) not in got, "Dragon blocked by an occupied landing square")

# --------------------------------------------------------------------------- #
# 4. Unicorn: bishop + nightrider (first landing blocks the whole ride)
# --------------------------------------------------------------------------- #
b = {**QS, (4, 4): (WHITE, "U"),
     (5, 6): (WHITE, "P"),      # own piece on the first (1,2) landing
     (6, 5): (BLACK, "P")}      # enemy on the first (2,1) landing: capture, stop
UNI_SET = ({(5, 5), (6, 6), (7, 7), (8, 8), (9, 9)}         # NE bishop ray
           | {(5, 3), (6, 2), (7, 1), (8, 0)}               # SE
           | {(3, 3), (2, 2), (1, 1)}                       # SW (own Q stops it)
           | {(3, 5), (2, 6), (1, 7), (0, 8)}               # NW
           | {(6, 5)}                                       # (2,1) capture
           | {(6, 3), (8, 2), (5, 2), (6, 0), (3, 2), (2, 0),
              (2, 3), (0, 2), (2, 5), (0, 6), (3, 6), (2, 8)})
got = targets(b, (4, 4))
check(got == UNI_SET, f"Unicorn targets: {sorted(got)}")
check((6, 8) not in got, "nightrider blocked at its first landing square")
check((8, 6) not in got, "nightrider capture ends the ride")

# --------------------------------------------------------------------------- #
# 5. Lion (Leo): slides without capturing; captures only over exactly one screen
# --------------------------------------------------------------------------- #
b = {**QS, (4, 4): (WHITE, "L"),
     (4, 5): (WHITE, "P"),      # screen on the N ray
     (4, 8): (BLACK, "P"),      # capturable over that screen
     (5, 4): (BLACK, "P")}      # ADJACENT enemy: no screen -> uncapturable
LION_SET = ({(4, 8)}                                        # screen capture
            | {(4, 3), (4, 2), (4, 1), (4, 0)}              # S slides
            | {(3, 4), (2, 4), (1, 4), (0, 4)}              # W
            | {(5, 5), (6, 6), (7, 7), (8, 8), (9, 9)}      # NE
            | {(3, 5), (2, 6), (1, 7), (0, 8)}              # NW
            | {(5, 3), (6, 2), (7, 1), (8, 0)}              # SE
            | {(3, 3), (2, 2), (1, 1)})                     # SW (own Q blocks)
got = targets(b, (4, 4))
check(got == LION_SET, f"Lion targets: {sorted(got)}")
check((5, 4) not in got, "Lion cannot capture an adjacent enemy (no screen)")
check((4, 6) not in got and (4, 7) not in got,
      "Lion cannot land on empty squares beyond the screen")
# A second piece between screen and target kills the capture.
b[(4, 6)] = (WHITE, "P")
check((4, 8) not in targets(b, (4, 4)),
      "Lion capture needs EXACTLY one screen (two men in between: no capture)")

# --------------------------------------------------------------------------- #
# 6. Anglican Bishop: diagonal slider + NON-capturing orthogonal step
# --------------------------------------------------------------------------- #
b = {**QS, (4, 4): (WHITE, "B"),
     (4, 5): (BLACK, "P"),      # orthogonally adjacent enemy: NOT capturable
     (5, 5): (BLACK, "P")}      # diagonal enemy: capturable
BISHOP_SET = ({(5, 5)}
              | {(3, 5), (2, 6), (1, 7), (0, 8)}
              | {(5, 3), (6, 2), (7, 1), (8, 0)}
              | {(3, 3), (2, 2), (1, 1)}
              | {(3, 4), (5, 4), (4, 3)})                   # wazir steps to EMPTY
got = targets(b, (4, 4))
check(got == BISHOP_SET, f"Bishop targets: {sorted(got)}")
check((4, 5) not in got, "the Bishop's orthogonal step cannot capture")

# --------------------------------------------------------------------------- #
# 7. Prince Consort: Queen-slide without capturing, one-step capture only
# --------------------------------------------------------------------------- #
b = {**QS, (4, 4): (WHITE, "K"),
     (4, 7): (BLACK, "P"),      # distant enemy on the N file: NOT capturable
     (5, 5): (BLACK, "P")}      # adjacent enemy: capturable
CONSORT_SET = ({(5, 5)}
               | {(4, 5), (4, 6)}                           # N stops before (4,7)
               | {(5, 4), (6, 4), (7, 4), (8, 4), (9, 4)}
               | {(4, 3), (4, 2), (4, 1), (4, 0)}
               | {(3, 4), (2, 4), (1, 4), (0, 4)}
               | {(3, 5), (2, 6), (1, 7), (0, 8)}
               | {(5, 3), (6, 2), (7, 1), (8, 0)}
               | {(3, 3), (2, 2), (1, 1)})
got = targets(b, (4, 4))
check(got == CONSORT_SET, f"Prince Consort targets: {sorted(got)}")
check((4, 7) not in got, "the Prince Consort cannot capture at a distance")

# --------------------------------------------------------------------------- #
# 8. Royal Queen: facing ban, through-check ban, mate, stalemate, Q-vs-Q draw
# --------------------------------------------------------------------------- #
# 8a. Destination + pass-through facing ban: the white Queen may not step onto
# the open file of the black Queen, nor pass over such a square. (An inert
# pawn sits at (9,1) so the position is not a bare-queens material draw.)
st = CState(board={(3, 0): (WHITE, "Q"), (4, 9): (BLACK, "Q"),
                   (9, 1): (WHITE, "P")}, to_move=WHITE)
ms = set(G.legal_moves(st))
check("3,0>4,0" not in ms, "Queen may not move onto an open line facing the enemy Queen")
check("3,0>4,1" not in ms, "…nor onto the open file further up")
check("3,0>5,2" not in ms, "…nor PASS OVER such a square (through-move ban)")
check("3,0>3,7" in ms, "a quiet file move stays legal")
check("3,0>3,8" not in ms, "…but not next to the enemy Queen (diagonally attacked)")

# 8b. Xiangqi-style screen pin: a piece between facing Queens may not leave the line.
st = CState(board={(4, 0): (WHITE, "Q"), (4, 9): (BLACK, "Q"),
                   (4, 4): (WHITE, "R")}, to_move=WHITE)  # R keeps material alive
ms = set(G.legal_moves(st))
check("4,4>5,4" not in ms, "the screen Rook may not expose facing Queens")
check("4,4>4,5" in ms, "the screen Rook may move along the file")

# 8c. Through-check: an enemy Rook's covered square stops the Queen's slide and
# makes everything beyond unreachable.
st = CState(board={(0, 0): (WHITE, "Q"), (8, 9): (BLACK, "Q"),
                   (5, 9): (BLACK, "R")}, to_move=WHITE)
got = targets(st.board, (0, 0))
check((4, 0) in got, "Queen slides up to the covered square")
check((5, 0) not in got, "Queen may not move INTO the Rook's line")
check((6, 0) not in got and (7, 0) not in got,
      "squares beyond a covered square are unreachable (no moving THROUGH check)")

# 8d. Checkmate of the Queen, reached via apply_move (two Rooks ladder-mate).
st = CState(board={(5, 0): (WHITE, "Q"), (9, 9): (BLACK, "Q"),
                   (0, 8): (WHITE, "R"), (1, 5): (WHITE, "R")}, to_move=WHITE)
check(not G.is_terminal(st), "pre-mate position is live")
st = G.apply_move(st, "1,5>1,9")
check(G.in_check(st.board, BLACK), "the Rook checks the black Queen")
check(G.is_terminal(st), "Rb10 is checkmate")
check(G.returns(st) == [1.0, -1.0], "White wins the mate")

# 8e. Stalemate is a draw: the black Queen is trapped but not in check.
st = CState(board={(2, 0): (WHITE, "Q"), (9, 9): (BLACK, "Q"),
                   (0, 8): (WHITE, "R"), (8, 0): (WHITE, "R")}, to_move=BLACK)
check(not G.in_check(st.board, BLACK), "stalemate position: no check")
check(G.legal_moves(st) == [], "the trapped Queen has no legal moves")
check(G.is_terminal(st) and G.returns(st) == [0.0, 0.0], "stalemate is a draw")

# 8f. Bare Queen vs bare Queen is a dead draw (they can never capture each other).
st = CState(board=dict(QS), to_move=WHITE)
check(G.is_terminal(st) and G.returns(st) == [0.0, 0.0],
      "bare Queen vs bare Queen: insufficient material draw")

# --------------------------------------------------------------------------- #
# 9. Promotion: mandatory; Knight always, others only while "captured"
# --------------------------------------------------------------------------- #
st = CState(board={(2, 0): (WHITE, "Q"), (9, 6): (BLACK, "Q"),
                   (0, 8): (WHITE, "P"), (5, 5): (WHITE, "R")}, to_move=WHITE)
ms = set(G.legal_moves(st))
check("0,8>0,9" not in ms, "promotion is mandatory (no plain push to the last rank)")
for t in ("N", "R", "B", "U", "L", "D"):
    check(f"0,8>0,9={t}" in ms, f"may promote to {t} (fewer on board than at start)")
check("0,8>0,9=Q" not in ms, "may not promote to the (uncaptured) Queen")
st2 = G.apply_move(st, "0,8>0,9=U")
check(st2.board[(0, 9)] == (WHITE, "U"), "promotion produced a Unicorn")

# Full complement: only the Knight is available.
full = {(2, 0): (WHITE, "Q"), (9, 6): (BLACK, "Q"), (0, 8): (WHITE, "P"),
        (3, 0): (WHITE, "R"), (4, 0): (WHITE, "R"),
        (3, 1): (WHITE, "B"), (4, 1): (WHITE, "B"),
        (3, 2): (WHITE, "U"), (4, 2): (WHITE, "U"),
        (3, 3): (WHITE, "L"), (4, 3): (WHITE, "L"),
        (3, 4): (WHITE, "D"), (4, 4): (WHITE, "D")}
ms = set(G.legal_moves(CState(board=full, to_move=WHITE)))
pawn_ms = {m for m in ms if m.startswith("0,8>")}
check(pawn_ms == {"0,8>0,9=N"},
      f"with a full complement only =N is offered: {sorted(pawn_ms)}")

# --------------------------------------------------------------------------- #
# 10. En passant after a third-rank double step
# --------------------------------------------------------------------------- #
st = CState(board={**QS, (2, 2): (WHITE, "P"), (3, 4): (BLACK, "P")},
            to_move=WHITE)
check("2,2>2,4" in G.legal_moves(st), "double step from the third rank")
st = G.apply_move(st, "2,2>2,4")
check("3,4>2,3" in G.legal_moves(st), "en passant capture is offered")
st = G.apply_move(st, "3,4>2,3")
check(st.board.get((2, 3)) == (BLACK, "P") and (2, 4) not in st.board,
      "en passant removes the double-stepped pawn")

# --------------------------------------------------------------------------- #
# 11. Serialize round-trip + render shape
# --------------------------------------------------------------------------- #
s1 = G.apply_move(s0, G.legal_moves(s0)[0])
for s in (s0, s1):
    rt = G.deserialize(G.serialize(s))
    check(G._poskey_state(rt) == G._poskey_state(s) and rt.ply == s.ply,
          "serialize round-trips")
spec = G.render(s0)
check(spec["board"] == {"type": "square", "width": 10, "height": 10},
      "render: 10x10 square board")
check(len(spec["pieces"]) == 44 and all(len(p["label"]) == 1 for p in spec["pieces"]),
      "render: 44 one-letter pieces")

print("SELFTEST OK")
