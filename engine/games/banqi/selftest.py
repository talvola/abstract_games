#!/usr/bin/env python3
"""Correctness anchors for Banqi (Dark Chess), Taiwanese ruleset.

No perft-style published node counts exist, so the anchors pin the ruleset
directly against the Wikipedia (en.wikipedia.org/wiki/Banqi) Taiwanese rules:

  * 32-piece inventory (per colour 1G 2A 2E 2R 2H 2C 5S), all face-down at start;
  * the opening move set is exactly the 32 flips, and the first flip assigns
    the flipper the revealed piece's colour;
  * the FULL 7x7 step-capture matrix (every attacker kind x every defender
    kind), including the Soldier/General exception and the cannon's
    exemptions (never step-captures; capturable by all but the Soldier);
  * cannon jump geometry: exactly one screen (friend/foe/face-down all OK),
    empty squares elsewhere, any-rank face-up enemy target, no adjacent
    capture, no jump onto face-down or friendly pieces, no screenless shot;
  * face-down immunity: face-down pieces can't move, step-capture, be
    step-captured, or be cannon-captured — but can always be flipped;
  * no-move loss REACHED via apply_move (win-as-event rule);
  * threefold-repetition and no-progress (quiet-cap) honest draws;
  * render never leaks a face-down piece's identity;
  * 500 seeded random playouts all terminate.

Pure stdlib + agp only.  PYTHONPATH=. python3 games/banqi/selftest.py
Prints "SELFTEST OK" and exits 0 on success; nonzero on failure.
"""

from __future__ import annotations

import importlib.util
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("banqi_game", os.path.join(_HERE, "game.py"))
_mod = importlib.util.module_from_spec(_spec)
sys.modules["banqi_game"] = _mod
_spec.loader.exec_module(_mod)

Banqi = _mod.Banqi
BanqiState = _mod.BanqiState
RED, BLACK = _mod.RED, _mod.BLACK
QUIET_CAP, PLY_CAP = _mod.QUIET_CAP, _mod.PLY_CAP
KIND_COUNTS = _mod.KIND_COUNTS

G = Banqi()
KINDS = "GAERHCS"


def fail(msg):
    print("SELFTEST FAILED:", msg, file=sys.stderr)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def state(pieces, to_move=0, colors=RED, quiet=0, ply=0, reps=None):
    """pieces: dict (c,r) -> (color, kind, up). Seat 0 plays `colors`."""
    return BanqiState(board=dict(pieces), colors=colors, to_move=to_move,
                      quiet=quiet, ply=ply, reps=dict(reps or {}))


# --------------------------------------------------------------------------- #
# 1. Inventory + opening flips
# --------------------------------------------------------------------------- #
s0 = G.initial_state(rng=random.Random(42))
check(len(s0.board) == 32, "initial board must hold 32 pieces")
check(all(not up for (_c, _k, up) in s0.board.values()), "all pieces start face-down")
for col in (RED, BLACK):
    for k, n in KIND_COUNTS.items():
        have = sum(1 for (c2, k2, _u) in s0.board.values() if c2 == col and k2 == k)
        check(have == n, f"colour {col} must have {n} x {k}, got {have}")
check(s0.colors is None, "colours undecided before the first flip")
m0 = G.legal_moves(s0)
check(len(m0) == 32 and all(">" not in m for m in m0),
      "the opening move set is exactly the 32 flips")

# Different seeds shuffle differently (randomness actually stored in state).
s0b = G.initial_state(rng=random.Random(43))
check(any(s0.board[c] != s0b.board[c] for c in s0.board),
      "different rng seeds must give different shuffles")

# --------------------------------------------------------------------------- #
# 2. First flip assigns the flipper the REVEALED colour
# --------------------------------------------------------------------------- #
for want in (RED, BLACK):
    cell = next(c for c, (col, _k, _u) in s0.board.items() if col == want)
    s1 = G.apply_move(s0, f"{cell[0]},{cell[1]}")
    check(s1.colors == want,
          f"first flip revealing colour {want}: seat 0 must play that colour")
    check(s1.board[cell][2], "flipped piece must be face-up")
    check(s1.to_move == 1, "turn passes after a flip")
    # Seat 1 owns no revealed piece yet: only flips are legal.
    m1 = G.legal_moves(s1)
    check(len(m1) == 31 and all(">" not in m for m in m1),
          "after the first flip, the second player can only flip (31 face-down left)")

# --------------------------------------------------------------------------- #
# 3. The full step-capture matrix (attacker x defender)
# --------------------------------------------------------------------------- #
# Independently hand-coded from the Wikipedia Taiwanese rules:
# equal-or-lower rank in G>A>E>R>H>S; Soldier takes General, General can't take
# Soldier; Cannon never step-captures; Cannon is takeable by all but the Soldier.
T, F = True, False
EXPECTED = {
    #        G  A  E  R  H  C  S      (defender)
    "G": dict(zip(KINDS, (T, T, T, T, T, T, F))),
    "A": dict(zip(KINDS, (F, T, T, T, T, T, T))),
    "E": dict(zip(KINDS, (F, F, T, T, T, T, T))),
    "R": dict(zip(KINDS, (F, F, F, T, T, T, T))),
    "H": dict(zip(KINDS, (F, F, F, F, T, T, T))),
    "C": dict(zip(KINDS, (F, F, F, F, F, F, F))),
    "S": dict(zip(KINDS, (T, F, F, F, F, F, T))),
}
for a in KINDS:
    for t in KINDS:
        s = state({(1, 1): (RED, a, True), (2, 1): (BLACK, t, True)})
        got = "1,1>2,1" in G.legal_moves(s)
        check(got == EXPECTED[a][t],
              f"step-capture {a} x {t}: expected {EXPECTED[a][t]}, got {got}")

# --------------------------------------------------------------------------- #
# 4. Cannon jump geometry
# --------------------------------------------------------------------------- #
CAN = {(0, 0): (RED, "C", True)}

# One screen (own piece), face-up enemy beyond -> capture at any distance.
s = state({**CAN, (2, 0): (RED, "S", True), (5, 0): (BLACK, "G", True)})
check("0,0>5,0" in G.legal_moves(s), "cannon jumps a screen to take ANY rank (General)")
# The screen itself is never the target.
check("0,0>2,0" not in G.legal_moves(s), "the screen square is not a capture target")

# Face-DOWN screen works too.
s = state({**CAN, (2, 0): (BLACK, "S", False), (5, 0): (BLACK, "A", True)})
check("0,0>5,0" in G.legal_moves(s), "a face-down piece is a valid screen")

# Enemy face-up screen works.
s = state({**CAN, (2, 0): (BLACK, "S", True), (5, 0): (BLACK, "A", True)})
check("0,0>5,0" in G.legal_moves(s), "an enemy piece is a valid screen")

# No screen -> no shot.
s = state({**CAN, (5, 0): (BLACK, "A", True)})
check("0,0>5,0" not in G.legal_moves(s), "cannon cannot capture without a screen")

# Two pieces between cannon and victim -> blocked (first piece past the screen
# is a friend, and the real enemy is beyond it).
s = state({**CAN, (2, 0): (RED, "S", True), (3, 0): (RED, "H", True),
           (5, 0): (BLACK, "A", True)})
check("0,0>5,0" not in G.legal_moves(s), "two screens block the cannon")

# Adjacent enemy: never capturable by the cannon (must jump).
s = state({**CAN, (1, 0): (BLACK, "S", True)})
check("0,0>1,0" not in G.legal_moves(s), "cannon cannot capture an adjacent piece")

# Target face-down -> illegal even over a valid screen.
s = state({**CAN, (2, 0): (RED, "S", True), (5, 0): (BLACK, "A", False)})
check("0,0>5,0" not in G.legal_moves(s), "cannon may not capture a face-down piece")

# Target own colour -> illegal.
s = state({**CAN, (2, 0): (RED, "S", True), (5, 0): (RED, "A", True)})
check("0,0>5,0" not in G.legal_moves(s), "cannon may not capture a friendly piece")

# Vertical jump.
s = state({(3, 0): (RED, "C", True), (3, 1): (BLACK, "S", False),
           (3, 3): (BLACK, "R", True)})
check("3,0>3,3" in G.legal_moves(s), "cannon jumps vertically too")

# Quiet cannon movement is one step to an empty square only.
s = state({(3, 1): (RED, "C", True)})
steps = {m for m in G.legal_moves(s) if ">" in m}
check(steps == {"3,1>2,1", "3,1>4,1", "3,1>3,0", "3,1>3,2"},
      f"cannon quiet moves are the four one-step moves, got {steps}")

# Applying a jump actually lands the cannon on the victim's square.
s = state({**CAN, (2, 0): (RED, "S", True), (5, 0): (BLACK, "G", True)})
s2 = G.apply_move(s, "0,0>5,0")
check(s2.board[(5, 0)] == (RED, "C", True) and (0, 0) not in s2.board,
      "cannon jump-capture lands on the target square")
check(sum(1 for p in s2.board.values() if p[0] == BLACK) == 0, "victim removed")

# --------------------------------------------------------------------------- #
# 5. Face-down immunity (and movability)
# --------------------------------------------------------------------------- #
s = state({(1, 1): (RED, "G", True), (2, 1): (BLACK, "S", False)})
ms = G.legal_moves(s)
check("1,1>2,1" not in ms, "no piece may step-capture a face-down piece")
check("2,1" in ms, "the face-down piece can still be flipped")
# A face-down piece generates no moves of its own even for its owner.
s = state({(1, 1): (RED, "G", False)}, to_move=0)
check(all(">" not in m for m in G.legal_moves(s)), "face-down pieces cannot move")
# You may not move your opponent's revealed pieces.
s = state({(1, 1): (BLACK, "G", True), (5, 2): (RED, "S", True)}, to_move=0)
check(all(m.startswith("5,2") for m in G.legal_moves(s) if ">" in m),
      "a player may only move their own revealed pieces")

# --------------------------------------------------------------------------- #
# 6. No-move loss, reached via apply_move
# --------------------------------------------------------------------------- #
s = state({(0, 0): (RED, "A", True), (1, 0): (BLACK, "S", True)}, to_move=0)
check(not G.is_terminal(s), "position with a capture available is live")
s2 = G.apply_move(s, "0,0>1,0")           # Advisor takes the last Black piece
check(G.is_terminal(s2), "opponent annihilated + nothing to flip => terminal")
check(G.returns(s2) == [1.0, -1.0], "seat 0 wins when seat 1 cannot move")

# Mirror: seat 1 delivers the killing blow.
s = state({(0, 0): (BLACK, "A", True), (1, 0): (RED, "S", True)}, to_move=1)
s2 = G.apply_move(s, "0,0>1,0")
check(G.is_terminal(s2) and G.returns(s2) == [-1.0, 1.0],
      "seat 1 wins when seat 0 cannot move")

# --------------------------------------------------------------------------- #
# 7. Draw backstops
# --------------------------------------------------------------------------- #
# Threefold repetition via a shuffling cycle of two lone generals.
s = state({(0, 0): (RED, "G", True), (7, 3): (BLACK, "G", True)}, to_move=0)
cycle = ["0,0>1,0", "7,3>6,3", "1,0>0,0", "6,3>7,3"]
plies = 0
while not G.is_terminal(s):
    s = G.apply_move(s, cycle[plies % 4])
    plies += 1
    check(plies <= 12, "repetition draw must trigger within three cycles")
check(s.draw == "repetition", f"expected repetition draw, got {s.draw!r}")
check(G.returns(s) == [0.0, 0.0], "repetition is an honest draw")

# Quiet cap: QUIET_CAP plies without flip/capture draws.
s = state({(0, 0): (RED, "G", True), (7, 3): (BLACK, "G", True)},
          to_move=0, quiet=QUIET_CAP - 1)
s2 = G.apply_move(s, "0,0>1,0")
check(s2.quiet == QUIET_CAP and G.is_terminal(s2) and G.returns(s2) == [0.0, 0.0],
      "no-progress (quiet-cap) draw")
# ...and a flip resets the quiet counter.
s = state({(0, 0): (RED, "G", True), (7, 3): (BLACK, "G", False)},
          to_move=0, quiet=QUIET_CAP - 1)
s2 = G.apply_move(s, "0,0>1,0")           # quiet move -> would draw
check(G.is_terminal(s2), "sanity: quiet move hits the cap")
s3 = G.apply_move(s, "7,3")               # flip instead -> resets
check(s3.quiet == 0 and not G.is_terminal(s3), "a flip resets the no-progress clock")

# --------------------------------------------------------------------------- #
# 8. Render must not leak face-down identities
# --------------------------------------------------------------------------- #
spec = G.render(s0)
check(len(spec["pieces"]) == 32, "render shows all 32 discs")
for p in spec["pieces"]:
    check(p["label"] == "?", "face-down pieces render as '?'")
    check("owner" not in p, "face-down pieces carry no owner/seat colour")
blob = json.dumps(spec)
for kind in KINDS:
    check(f'"label": "{kind}"' not in blob and f'"kind"' not in blob,
          "no piece identity may appear in the opening render spec")
# After one flip, exactly one piece is identified.
cell = next(iter(s0.board))
s1 = G.apply_move(s0, f"{cell[0]},{cell[1]}")
spec1 = G.render(s1)
shown = [p for p in spec1["pieces"] if p["label"] != "?"]
check(len(shown) == 1 and shown[0]["label"] in KINDS and shown[0]["owner"] in (0, 1),
      "after one flip exactly one piece is revealed in the render")
check(sum(1 for p in spec1["pieces"] if p["label"] == "?") == 31,
      "31 discs stay anonymous after one flip")

# Serialize round-trips (identities ARE in the state — documented).
d = json.loads(json.dumps(G.serialize(s1)))
check(G.serialize(G.deserialize(d)) == G.serialize(s1), "serialize round-trip")

# describe_move
check(G.describe_move(s0, "3,2") == "flip 3,2", "flip notation")
s = state({(0, 0): (RED, "H", True), (1, 0): (BLACK, "S", True)})
check(G.describe_move(s, "0,0>1,0") == "H0,0x1,0", "capture notation")

# --------------------------------------------------------------------------- #
# 9. 500 seeded random playouts terminate
# --------------------------------------------------------------------------- #
results = {"seat0": 0, "seat1": 0, "draw": 0}
total_plies = 0
max_plies = 0
for i in range(500):
    rng = random.Random(10_000 + i)
    s = G.initial_state(rng=rng)
    n = 0
    while not G.is_terminal(s):
        moves = G.legal_moves(s)
        check(bool(moves), "non-terminal state must have legal moves")
        s = G.apply_move(s, rng.choice(moves), rng=rng)
        n += 1
        check(n <= PLY_CAP + 1, "playout must terminate within the ply cap")
    r = G.returns(s)
    if r == [1.0, -1.0]:
        results["seat0"] += 1
    elif r == [-1.0, 1.0]:
        results["seat1"] += 1
    else:
        results["draw"] += 1
    total_plies += n
    max_plies = max(max_plies, n)

check(results["seat0"] + results["seat1"] + results["draw"] == 500, "500 games")
check(results["seat0"] > 0 and results["seat1"] > 0, "both seats can win")
print(f"playouts: 500 games, seat0 {results['seat0']} / seat1 {results['seat1']} "
      f"/ draws {results['draw']}, avg plies {total_plies / 500:.1f}, max {max_plies}")

print("SELFTEST OK")
