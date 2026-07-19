"""Mirador selftest — pure stdlib.

Anchors (all pixel-verified from Abstract Games magazine #22, pp. 35-38, and
the designer's own rules at miradorthegame.blogspot.ca):

1. The annotated game fritzd (Green) vs pim (Blue), 18 moves, replayed with
   every move legal; the printed move list's "16. O16" is a typo — the final-
   position diagram (and placement legality: O16 would overlap 12. P16) proves
   the move was C16.
   Position claims from the annotation are asserted:
     - after 9. U25, Blue cannot place ANY mirador covering cols U/V between
       U12 and the top ("Blue cannot even add any pieces ... to renew");
     - after 13. O21, Q19 is a Green "reserve": legal for Green, and no Blue
       placement can ever cover any square of it;
     - after 18. K19, N18 is a Blue reserve completing the Blue connection
       ("no way Green can prevent Blue from playing at N18").
   Blue then declares and wins.
2. The four-move-win position (SDG game shown in the article: Green E4, F11,
   E18, D24; Blue T5, S10, T17, S22): Blue's chain spans north-south, survives
   EVERY single Green challenge placement, and every pair of challenge
   placements that could touch the corridors (cols S-U).  "Blue wins with only
   four miradors!"
3. The premature-declaration example (p. 36): Green breaks Blue's east-west
   chain with exactly the two printed placements E6 + K4 and wins.
4. The sound-declaration example (H6 moved to G6): E6 is now an illegal
   placement, and NO single Green placement breaks the Blue chain.
5. Pie rule: swap recolours the opening mirador to seat 1 (Mirador's goals are
   colour-symmetric, so recolour-in-place is an exact swap).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

_man, G = load_from_dir(Path(__file__).resolve().parent)
from games.mirador.game import (  # noqa: E402
    GREEN, BLUE, _occupancy, _can_place, _placements, _spanning,
)


def anchor(name: str) -> str:
    """'E4' -> '4,3' (letter column, 1-based row -> 0-indexed cell id)."""
    return f"{ord(name[0]) - 65},{int(name[1:]) - 1}"


def cells_of(name: str):
    c, r = ord(name[0]) - 65, int(name[1:]) - 1
    return {(c + dc, r + dr) for dc in (0, 1) for dr in (0, 1)}


def build(miradors, phase="play", to_move=GREEN, declarer=None, ply=20):
    """Hand-build a state (the magazine's composed examples aren't reachable
    by alternation — they show unequal piece counts)."""
    return G.deserialize({
        "miradors": [[ord(n[0]) - 65, int(n[1:]) - 1, col] for n, col in miradors],
        "swapped": False, "to_move": to_move, "phase": phase,
        "declarer": declarer, "winner": None, "draw": False,
        "ply": ply, "last": None,
    })


fails = 0


def check(cond, msg):
    global fails
    if cond:
        print(f"  ok: {msg}")
    else:
        fails += 1
        print(f"  FAIL: {msg}")


# ---------------------------------------------------------------- basic shape
s = G.initial_state()
check(len(G.legal_moves(s)) == 676, "676 first placements (26x26 anchors)")
check(G.current_player(s) == 0, "seat 0 starts")

# ------------------------------------------------- 1. the annotated game (AG22)
print("== annotated game fritzd-pim ==")
GAME = ["E4", "T5", "V22", "S22", "S17", "V17", "X20", "U12", "U25", "Z16",
        "Z22", "P16", "O21", "J15", "F16", "C16", "M15", "K19"]
s = G.initial_state()
positions = []
for i, mv in enumerate(GAME):
    m = anchor(mv)
    lm = G.legal_moves(s)
    check(m in lm, f"{i + 1}. {mv} is legal")
    if i == 1:
        check("swap" in lm, "swap offered to the second player on move 2")
    s = G.apply_move(s, m)
    if s.phase == "window":          # decline every declaration in the record
        s = G.apply_move(s, "pass")
    positions.append(s)

final = {(c, r, col) for c, r, col in s.miradors}
expect = {(ord(n[0]) - 65, int(n[1:]) - 1, col) for n, col in [
    ("E4", GREEN), ("V22", GREEN), ("S17", GREEN), ("X20", GREEN), ("U25", GREEN),
    ("Z22", GREEN), ("O21", GREEN), ("F16", GREEN), ("M15", GREEN),
    ("T5", BLUE), ("S22", BLUE), ("V17", BLUE), ("U12", BLUE), ("Z16", BLUE),
    ("P16", BLUE), ("J15", BLUE), ("C16", BLUE), ("K19", BLUE)]}
check(final == expect, "final position matches the magazine diagram (16. C16, not 'O16')")

# after 9. U25: no Blue placement covers cols U/V between U12 and the top
s9 = positions[8]
occ9 = _occupancy(s9.miradors)
zone = {(x, y) for x in (20, 21) for y in range(13, 24)}  # cols U,V rows 14..24
bad = [p for p in _placements(occ9, BLUE)
       if {(p[0] + dc, p[1] + dr) for dc in (0, 1) for dr in (0, 1)} & zone]
check(bad == [], "after 9. U25 Blue cannot renew the U12 top threat (annotation)")

# after 13. O21: Q19 is a Green reserve
s13 = positions[12]
occ13 = _occupancy(s13.miradors)
q19 = cells_of("Q19")
check(_can_place(occ13, GREEN, 16, 18), "after 13. O21, Q19 legal for Green")
bad = [p for p in _placements(occ13, BLUE)
       if {(p[0] + dc, p[1] + dr) for dc in (0, 1) for dr in (0, 1)} & q19]
check(bad == [], "no Blue placement can ever touch Q19 (Green reserve, annotation)")

# after 18. K19: N18 is a Blue reserve; Blue plays it and wins by declaration
s18 = positions[17]
occ18 = _occupancy(s18.miradors)
n18 = cells_of("N18")
check(_can_place(occ18, BLUE, 13, 17), "after 18. K19, N18 legal for Blue")
check(not _can_place(occ18, GREEN, 13, 17), "N18 itself illegal for Green (P16 corner)")
bad = [p for p in _placements(occ18, GREEN)
       if {(p[0] + dc, p[1] + dr) for dc in (0, 1) for dr in (0, 1)} & n18]
check(bad == [], "no Green placement can touch N18 (Blue reserve, annotation)")

check(G.current_player(s18) == 0, "move 19 is Green's")
s19 = G.apply_move(s18, anchor("A1"))          # Green filler (resigned in reality)
if s19.phase == "window":
    s19 = G.apply_move(s19, "pass")
s20 = G.apply_move(s19, anchor("N18"))         # Blue completes the connection
check(s20.phase == "window" and "declare" in G.legal_moves(s20),
      "N18 completes a Blue chain -> declaration window opens")
ns, ew = _spanning(s20.miradors, BLUE)
check(ew, "the completed Blue connection is east-west (annotation's 'run across')")
check(ns, "…and in fact also north-south (a rare 'double win', designer's term)")
s21 = G.apply_move(s20, "declare")
check(G.current_player(s21) == 0 and "accept" in G.legal_moves(s21),
      "Green challenges after Blue declares")
s22 = G.apply_move(s21, "accept")
check(G.is_terminal(s22) and G.returns(s22) == [-1.0, 1.0],
      "Blue (seat 1) wins the annotated game")

# ------------------------------------- 2. the four-move win ("Blue wins with
# only four miradors!") — 1-ply and corridor 2-ply unassailability
print("== four-move connection ==")
s = G.initial_state()
for mv in ["E4", "T5", "F11", "S10", "E18", "T17", "D24", "S22"]:
    s = G.apply_move(s, anchor(mv))
    if s.phase == "window" and mv != "S22":
        s = G.apply_move(s, "pass")
check(s.phase == "window", "8. S22 opens Blue's declaration window")
ns, ew = _spanning(s.miradors, BLUE)
check(ns, "Blue's four miradors span north-south")
s = G.apply_move(s, "declare")
occ = _occupancy(s.miradors)
greens = _placements(occ, GREEN)
ok1 = all(any(_spanning(s.miradors + [(c, r, GREEN)], BLUE)) for c, r in greens)
check(ok1, f"no single Green challenge placement breaks it ({len(greens)} tried)")
# two-ply: only placements covering cols S,T,U (18-20) can obstruct the
# vertical corridors, so restrict both plies to anchors touching those columns
cand = [(c, r) for c, r in greens if c + 1 >= 17 and c <= 20]
ok2 = True
tried = 0
for c1, r1 in cand:
    mir1 = s.miradors + [(c1, r1, GREEN)]
    occ1 = _occupancy(mir1)
    for c2, r2 in cand:
        if (c2, r2) == (c1, r1) or not _can_place(occ1, GREEN, c2, r2):
            continue
        tried += 1
        if not any(_spanning(mir1 + [(c2, r2, GREEN)], BLUE)):
            ok2 = False
            print(f"  broken by {c1},{r1} + {c2},{r2}")
check(ok2, f"no PAIR of corridor challenge placements breaks it ({tried} pairs)")

# ------------------------------------------- 3. premature declaration (p. 36)
# The magazine strips show the bottom 8 rows of a board — the discussion is
# about Blue's EAST-WEST chain, so these checks assert at the axis level (on a
# full empty 27x27 board the strip pieces trivially also span north-south).
print("== premature declaration ==")
BASE = [("B4", BLUE), ("F3", BLUE), ("N4", BLUE), ("P6", BLUE), ("U6", BLUE),
        ("W4", BLUE), ("Y2", BLUE), ("J1", GREEN), ("Q1", GREEN),
        ("S3", GREEN), ("U1", GREEN)]
s = build(BASE + [("H6", BLUE)], phase="refute", to_move=GREEN, declarer=BLUE)
check(_spanning(s.miradors, BLUE)[1], "Blue has an east-west chain when declaring")
s = G.apply_move(s, anchor("E6"))
check(_spanning(s.miradors, BLUE)[1], "E6 alone does not break the E-W chain")
s = G.apply_move(s, anchor("K4"))
check(not _spanning(s.miradors, BLUE)[1],
      "E6 + K4 break the E-W chain (the two red-dotted miradors)")

# ------------------------------------------------ 4. sound declaration (p. 36)
print("== sound declaration ==")
s = build(BASE + [("G6", BLUE)], phase="refute", to_move=GREEN, declarer=BLUE)
check(_spanning(s.miradors, BLUE)[1], "Blue's E-W chain intact with G6")
lm = G.legal_moves(s)
check(anchor("E6") not in lm, "E6 now illegal (touches G6): the break is gone")
occ = _occupancy(s.miradors)
greens = _placements(occ, GREEN)
ok = all(_spanning(s.miradors + [(c, r, GREEN)], BLUE)[1] for c, r in greens)
check(ok, f"no single Green placement breaks the sound E-W chain ({len(greens)} tried)")

# --------------------------------------------------------------- 5. pie rule
print("== pie rule ==")
s = G.initial_state()
s = G.apply_move(s, anchor("E4"))
check(s.phase == "window", "even move 1 opens a declare window (E4 spans alone)")
s = G.apply_move(s, "pass")
check("swap" in G.legal_moves(s), "swap on offer")
s2 = G.apply_move(s, "swap")
check(s2.miradors == [(4, 3, GREEN)] and s2.swapped, "swap keeps the mirador Green")
spec = G.render(s2)
check(all(p["owner"] == 1 for p in spec["pieces"]), "after swap seat 1 owns the opening")
check(G.current_player(s2) == 0, "seat 0 continues as Blue")
s3 = G.apply_move(s2, anchor("T5"))
check(G.render(s3)["pieces"][4]["owner"] == 0, "seat 0's reply rendered as seat 0")
check("swap" not in G.legal_moves(s3), "swap only once")
check(G.describe_move(G.initial_state(), anchor("E4")) == "E4", "notation E4")

# ---------------------------------------------------------------------------
if fails:
    print(f"SELFTEST FAILED: {fails} failing checks")
    sys.exit(1)
print("mirador selftest: all checks passed")
