#!/usr/bin/env python3
"""Standalone correctness self-test for Chase (pure stdlib).

Run from engine/ with:  PYTHONPATH=. python3 games/chase/selftest.py

Anchors (Abstract Games magazine issue 9, Spring 2002, pp.13-17/21/29 —
"Chase: A 1980's Yard Sale Classic" by C. Rodeffer & J. Neto):

  1. Opening setup: Diagram 1 — both home rows 1 2 3 4 5 4 3 2 1 (total 25),
     Chamber E5 empty, 70 legal opening moves (frozen self-derived count),
     and the article's named opening moves are legal: A3D5 (duck a 3 behind
     the Chamber), A8C7, A5F8, plus the 1's wraparound chain-reaction bump
     (whole home row rotates one hex).
  2. PROBLEM 1 (printed solution, p.29) replayed in full — main line
     1...E4F5 2.1B1C9 F5G5 3.C9G7 G5G6/G6:G7(B1=6/F7=5) 4.G2:G7 White wins:
     covers the exchange move, a 4-hex quiet run, a bump-capture, the forced
     +4 redistribution stopping on the F7/G2 tie (owner's choice, F7 chosen
     per the printed solution), and the ≤4-dice loss. The printed variation
     1...E4:F4 2.B1:F4 "via a ricochet at A1" is also replayed: a 3-way
     lowest tie (B1/F7/G2) after the forced C9 3→6 overflow, then a speed-6
     ricochet capture ending the game.
  3. PROBLEM 2 (printed solution): both printed winning lines — the direct
     C6:C2 wrap-capture and the bump-capture C6C1/C1:C2 (landing on your own
     die so it bumps onward into the enemy).
  4. Chamber moves: the article's own example (entry via F5 → exits F6 left /
     E4 right); a 5 entering via E4 splits 3+2 with Large=Left (F5=3, D5=2);
     a speed-1 die does not split; a player at ten pieces does not split;
     a chamber exit capturing an enemy die; a bump into the Chamber makes
     the whole move illegal.
  5. Bump geometry: bump-ricochet at the top edge (bumped die leaves in the
     billiard direction) and bump-wraparound across the cylinder seam.
  6. Exchange legality: value ranges, no null exchange, no exchange between
     two 1s, adjacency across the seam (B1-C9, used by the Problem 1
     solution), and the "=M" move/exchange disambiguation.
  7. Redistribution: forced single-lowest, cap-at-6 overflow, tie → explicit
     choice by the owner (dist phase), all exercised by the problem replays.
  8. 150 random playouts all reach a terminal state (termination guarantee)
     while maintaining the invariants: totals of 25 for both sides and 5-10
     dice in play in every "move"-phase state; serialize round-trip;
     describe_move notation; heuristic shape + MCTSBot rollout-cutoff probe.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

import random
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ENGINE))

from agp.loader import load_from_dir  # noqa: E402
from agp.mcts import MCTSBot  # noqa: E402

_, G = load_from_dir(Path(__file__).resolve().parent)

ROWS = "ABCDEFGHI"


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def cid(nm):
    """'E4' -> '4,5' (column,row cell id)."""
    return f"{int(nm[1:])},{ROWS.index(nm[0]) + 1}"


def cc(nm):
    return int(nm[1:]), ROWS.index(nm[0]) + 1


def S(white, grey, to_move=0):
    data = {"board": {}, "to_move": to_move, "phase": "move", "deficit": 0,
            "winner": None, "quiet": 0, "ply": 0, "last": []}
    for nm, sp in white.items():
        data["board"][cid(nm)] = [0, sp]
    for nm, sp in grey.items():
        data["board"][cid(nm)] = [1, sp]
    return G.deserialize(data)


def total(s, p):
    return sum(v[1] for v in s["board"].values() if v[0] == p)


def count(s, p):
    return sum(1 for v in s["board"].values() if v[0] == p)


# ---- 1. opening setup + article opening moves ------------------------------
s0 = G.initial_state()
for p in (0, 1):
    check(total(s0, p) == 25 and count(s0, p) == 9, "opening totals")
for i, sp in enumerate((1, 2, 3, 4, 5, 4, 3, 2, 1)):
    check(s0["board"][(i + 1, 1)] == (0, sp), "row A setup")
    check(s0["board"][(i + 1, 9)] == (1, sp), "row I setup")
check((5, 5) not in s0["board"], "Chamber empty at start")
mv0 = G.legal_moves(s0)
check(len(mv0) == 70, f"opening move count 70 (got {len(mv0)})")
check(cid("A3") + ">" + cid("B4") + ">" + cid("D5") in mv0, "A3D5 legal")
check(cid("A8") + ">" + cid("B8") + ">" + cid("C7") in mv0, "A8C7 legal")
check(cid("A5") + ">" + cid("B6") + ">" + cid("F8") in mv0, "A5F8 legal")
check(cid("A6") + ">" + cid("A7") + "=4" in mv0, "exchange 1A6A7 legal")
check(cid("A6") + ">" + cid("A7") + "=3" not in mv0, "null exchange illegal")
s1 = G.apply_move(s0, cid("A1") + ">" + cid("A2") + "=M")  # wraparound bump
want = {1: 1, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 4, 8: 3, 9: 2}
for c, sp in want.items():
    check(s1["board"][(c, 1)] == (0, sp), "row rotation after chain bump")
check(total(s1, 0) == 25, "total preserved by bump")
d = G.serialize(s1)
check(G.serialize(G.deserialize(d)) == d, "serialize round-trip")

# ---- 2. Problem 1 ----------------------------------------------------------
P1W = {"B1": 4, "C9": 3, "F4": 5, "F7": 4, "F9": 5, "G2": 4}
P1G = {"E4": 1, "G4": 6, "G6": 6, "I3": 6, "I7": 6}
p1 = S(P1W, P1G, to_move=1)
check(total(p1, 0) == 25 and total(p1, 1) == 25, "P1 totals")

s = G.apply_move(p1, cid("E4") + ">" + cid("F5"))               # 1... E4F5
m = cid("B1") + ">" + cid("C9") + "=4"                          # 2. 1B1C9
check(m in G.legal_moves(s), "seam exchange B1-C9 legal")
s = G.apply_move(s, m)
check(s["board"][cc("B1")] == (0, 3) and s["board"][cc("C9")] == (0, 4),
      "exchange result")
s = G.apply_move(s, cid("F5") + ">" + cid("G5"))                # 2... F5G5
m = cid("C9") + ">" + cid("D9") + ">" + cid("G7")               # 3. C9G7
check(m in G.legal_moves(s), "C9G7 legal")
s = G.apply_move(s, m)
m = cid("G5") + ">" + cid("G6") + "=M"                          # 3... G5G6/G6:G7
check(m in G.legal_moves(s), "bump-capture G5G6/G6:G7 legal")
s = G.apply_move(s, m)
check(s["phase"] == "dist" and G.current_player(s) == 0 and s["deficit"] == 1,
      "dist phase after bump capture")
check(s["board"][cc("B1")] == (0, 6), "B1 3->6 forced first")
check(sorted(G.legal_moves(s)) == sorted([cid("F7"), cid("G2")]),
      "F7/G2 tie is the owner's choice")
check(G.describe_move(s, cid("F7")) == "+1 → F7", "dist notation")
s = G.apply_move(s, cid("F7"))                                  # (B1=6/F7=5)
check(s["phase"] == "move" and s["board"][cc("F7")] == (0, 5), "F7=5")
m = cid("G2") + ">" + cid("G1") + ">" + cid("G7")               # 4. G2:G7
check(m in G.legal_moves(s), "G2:G7 legal (westward wrap)")
s = G.apply_move(s, m)
check(G.is_terminal(s) and G.returns(s) == [1.0, -1.0],
      "Problem 1: White wins (Grey on 4 dice)")

# variation: 1... E4:F4 2.B1:F4 "via a ricochet at A1"
s = G.apply_move(p1, cid("E4") + ">" + cid("F4"))
check(s["phase"] == "dist" and s["deficit"] == 2, "P1 var: +5 dist, 2 left")
check(s["board"][cc("C9")] == (0, 6), "C9 3->6 forced (overflow)")
check(sorted(G.legal_moves(s)) == sorted([cid("B1"), cid("F7"), cid("G2")]),
      "3-way lowest tie")
s = G.apply_move(s, cid("B1"))
check(s["board"][cc("B1")] == (0, 6), "B1 -> 6 (printed C9=6/B1=6)")
m = cid("B1") + ">" + cid("A1") + ">" + cid("F4")
check(m in G.legal_moves(s), "B1:F4 via ricochet at A1 legal")
s = G.apply_move(s, m)
check(G.is_terminal(s) and s["winner"] == 0, "P1 variation: White wins")

# ---- 3. Problem 2 ----------------------------------------------------------
def p2():
    return S({"C1": 6, "C6": 4, "E7": 2, "G2": 4, "I6": 4, "I8": 5},
             {"A6": 4, "A7": 4, "C2": 6, "E1": 5, "I3": 6}, to_move=0)

check(total(p2(), 0) == 25 and total(p2(), 1) == 25 and count(p2(), 1) == 5,
      "P2 position (after the forced C6 1->4 promotion)")
sA = G.apply_move(p2(), cid("C6") + ">" + cid("C5") + ">" + cid("C2"))
check(G.is_terminal(sA) and sA["winner"] == 0, "P2: C6:C2 wins")
sB = G.apply_move(p2(), cid("C6") + ">" + cid("C7") + ">" + cid("C1"))
check(G.is_terminal(sB) and sB["winner"] == 0, "P2: C6C1/C1:C2 wins")

# ---- 4. Chamber ------------------------------------------------------------
s = S({"E9": 5, "A1": 1}, {"I9": 5, "I1": 5})
s2 = G.apply_move(s, cid("E9") + ">" + cid("E1") + ">" + cid("E5"))
check(s2["board"][cc("F5")] == (0, 3) and s2["board"][cc("D5")] == (0, 2)
      and cc("E9") not in s2["board"], "split 5 -> F5=3 / D5=2 (Large=Left)")
check(count(s2, 0) == 3, "chamber move brings one die into play")

s = S({"G4": 2, "A1": 1}, {"I9": 5, "I1": 5})  # the article's F5-entry example
s2 = G.apply_move(s, cid("G4") + ">" + cid("F5") + ">" + cid("E5"))
check(s2["board"][cc("F6")] == (0, 1) and s2["board"][cc("E4")] == (0, 1),
      "entry via F5 -> exits F6 (left) and E4 (right)")

s = S({"E4": 1, "A1": 1}, {"I9": 5, "I1": 5})
s2 = G.apply_move(s, cid("E4") + ">" + cid("E5"))
check(s2["board"][cc("F5")] == (0, 1) and cc("D5") not in s2["board"]
      and count(s2, 0) == 2, "speed-1 chamber move does not split")

w = {"E3": 2, "A1": 2, "A2": 2, "A3": 2, "A4": 2, "A5": 2, "A6": 2, "A7": 2,
     "A8": 3, "A9": 6}
s = S(w, {"I9": 5, "I1": 5})
s2 = G.apply_move(s, cid("E3") + ">" + cid("E4") + ">" + cid("E5"))
check(s2["board"][cc("F5")] == (0, 2) and count(s2, 0) == 10,
      "at ten pieces the mover exits left unsplit")

s = S({"E9": 5, "A1": 1}, {"F5": 2, "I9": 5})
s2 = G.apply_move(s, cid("E9") + ">" + cid("E1") + ">" + cid("E5"))
check(s2["board"][cc("F5")] == (0, 3) and s2["winner"] == 0,
      "chamber exit captures (and Grey drops to <=4 dice)")

s = S({"E3": 1, "E4": 1, "A1": 1}, {"I9": 5, "I1": 5})
check(not [m for m in G.legal_moves(s)
           if m.startswith(cid("E3") + ">" + cid("E4"))],
      "bump into the Chamber is illegal")

# ---- 5. bump geometry ------------------------------------------------------
s = S({"H3": 1, "I3": 2, "A1": 1}, {"I9": 5, "A9": 5})
s2 = G.apply_move(s, cid("H3") + ">" + cid("I3") + "=M")
check(s2["board"][cc("I3")] == (0, 1) and s2["board"][cc("H4")] == (0, 2),
      "bump-ricochet: I3 die leaves SE to H4")
s2 = G.apply_move(s, cid("H3") + ">" + cid("I3") + "=1")
check(s2["board"][cc("H3")] == (0, 2) and s2["board"][cc("I3")] == (0, 1),
      "the '=1' twin is the exchange, not the bump")

s = S({"B8": 1, "B9": 3, "A1": 1}, {"I9": 5, "I1": 5})
s2 = G.apply_move(s, cid("B8") + ">" + cid("B9") + "=M")
check(s2["board"][cc("B1")] == (0, 3) and s2["board"][cc("B9")] == (0, 1),
      "bump-wraparound across the seam")

# ---- 6. exchange corners ---------------------------------------------------
mv = G.legal_moves(S({"A1": 1, "A9": 1, "C5": 6}, {"I9": 5, "I1": 5}))
check(not [m for m in mv if "=" in m and not m.endswith("=M")],
      "two 1s cannot exchange")
mv = G.legal_moves(S({"D4": 6, "D5": 6, "A1": 1}, {"I9": 5, "I1": 5}))
check(not [m for m in mv if m.startswith(cid("D4") + ">" + cid("D5") + "=")],
      "two 6s cannot exchange")

# ---- 7. notation smoke -----------------------------------------------------
check(G.describe_move(s0, cid("A3") + ">" + cid("B4") + ">" + cid("D5"))
      == "A3→D5 (3)", "quiet-move notation")
check(G.describe_move(s0, cid("A6") + ">" + cid("A7") + "=4")
      == "A6⇄A7 (3/4)", "exchange notation")
check("×" in G.describe_move(p1, cid("E4") + ">" + cid("F4")),
      "capture notation")
check("Chamber" in G.describe_move(S({"E4": 1, "A1": 1}, {"I9": 5, "I1": 5}),
                                   cid("E4") + ">" + cid("E5")),
      "chamber notation")

# ---- 8. playouts, heuristic, render ---------------------------------------
r = G.render(s0)
check(r["board"]["type"] == "polygons" and len(r["board"]["cells"]) == 81,
      "render: 81 polygon cells")
check(isinstance(r["board"]["cells"], list)
      and "points" in r["board"]["cells"][0], "render: cells list w/ points")
check(len(r["pieces"]) == 18 and r["pieces"][0].get("label"), "render pieces")
check(r["board"]["tints"].get("5,5"), "Chamber tinted")

h = G.heuristic(s0)
check(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
      "heuristic returns per-seat payoffs")
bm = MCTSBot(random.Random(1), iterations=25, max_rollout=4).select(G, s0)
check(bm in G.legal_moves(s0), "MCTSBot (forced rollout cutoff) legal move")

rng = random.Random(2026)
results = {}
for i in range(150):
    st = G.initial_state()
    n = 0
    while not G.is_terminal(st):
        moves = G.legal_moves(st)
        check(moves, "non-empty legal_moves on non-terminal")
        if st["phase"] == "move":
            for p in (0, 1):
                check(total(st, p) == 25, f"total-25 invariant (game {i})")
                check(5 <= count(st, p) <= 10, f"dice-count invariant (game {i})")
        st = G.apply_move(st, rng.choice(moves))
        n += 1
        check(n < 2500, "runaway game")
    key = tuple(G.returns(st))
    results[key] = results.get(key, 0) + 1
check(sum(results.values()) == 150, "all playouts terminal")
check((1.0, -1.0) in results and (-1.0, 1.0) in results,
      "both players can win under random play")

print(f"playout results: {results}")
print("SELFTEST OK")
