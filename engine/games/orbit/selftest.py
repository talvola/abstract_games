#!/usr/bin/env python3
"""Correctness anchor for Orbit.

Every position below is transcribed from a published diagram, pixel-read off the
original artwork:

* *Abstract Games* magazine, issue 12 (Winter 2002), pp. 22-23 -- Diagrams 1-3
  (structures & effects / shared territory / the "White to play and win" puzzle,
  solution on p. 29).
* Steven Meyers' own rules page, http://home.fuse.net/swmeyers/orru.htm (via the
  Internet Archive) -- Diagrams 2-6 (half-orbits / orbits / shared territory /
  a scored end position / a completed pen-and-paper game).

The two SCORED full-board positions are the strongest anchors: the designer
publishes "Black has 58 points of territory to White's 38" for his Diagram 5
(together with the exact list of stones removed as dead and the exact 9 shared
points) and "Black has won by a score of 72 to 27 ... 25 points of shared
territory" for his Diagram 6.  Reproducing both exactly validates enclosure,
prohibition, capture, end-of-game dead-stone removal and shared territory at once.

Pure stdlib: imports only `agp` and this package.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.orbit import game as M                                  # noqa: E402
from games.orbit.game import Orbit                                 # noqa: E402

HERE = Path(__file__).resolve().parent
MAN = json.loads((HERE / "manifest.json").read_text())
GAME = Orbit()

L = "ABCDEFGHIJKLMNOP"
FAILS = []


def pt(name):
    return (L.index(name[0]), int(name[1:]) - 1)


def nm(p):
    return f"{L[p[0]]}{p[1] + 1}"


def names(ps):
    return [nm(p) for p in sorted(ps)]          # board order: column, then row


def chk(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL " + msg)


def board(blacks, whites):
    b = {}
    for s in blacks.split():
        b[pt(s)] = M.BLACK
    for s in whites.split():
        b[pt(s)] = M.WHITE
    return b


def enc(bd, colour):
    return M._enclosures(M._stones(bd, colour), 16, 16)


def parts(bd):
    """(shared, black territory, white territory) as name lists."""
    eb, _ = enc(bd, M.BLACK)
    ew, _ = enc(bd, M.WHITE)
    return (names((eb & ew) - set(bd)), names((eb - ew) - set(bd)),
            names((ew - eb) - set(bd)))


def play(bd, colour, *points):
    """Apply placements in order; return (board, captures of the LAST move)."""
    caps = []
    for point in points:
        bd = dict(bd)
        bd[pt(point)] = colour
        _, orb = enc(bd, colour)
        caps = sorted(p for p, v in bd.items() if v == 1 - colour and p in orb)
        for p in caps:
            del bd[p]
    return bd, names(caps)


def sub(lst, cols, lo, hi):
    return sorted(x for x in lst if x[0] in cols and lo <= int(x[1:]) <= hi)


# =====================================================================
# Magazine Diagram 1 -- "Structures and effects" (issue 12 p. 22)
# =====================================================================
D1_B = ("G16 L16 G15 M15 H14 J14 K14 L14 I13 J11 K11 L11 D10 E10 I10 C9 F9 J9 "
        "N9 C8 F8 I8 N8 L8 C7 F7 I7 M7 D6 E6 J6 K6 L6 N4 L3 M3 O3 C2 D2 E2 K2 "
        "P2 K1 P1")
D1_W = ("H16 I16 C15 I15 L15 B14 D14 B13 D13 C12 L9 K8 M8 L7 O6 M5 N5 P5 C4 D4 "
        "L4 P4 B3 E3 F3 K3 B2 F2 L2 M2 N2 O2 A1 E1 D9 D8 E7")
d1 = board(D1_B, D1_W)
encB1, orbB1 = enc(d1, M.BLACK)
encW1, orbW1 = enc(d1, M.WHITE)

# "In the upper left White has completed an orbit."
chk(pt("C14") in orbW1 and pt("C13") in orbW1,
    "D1 upper left: C14/C13 lie in a White ORBIT")
# "At the middle left Black has completed an orbit -- the three white stones are captured."
chk([p for p in "D9 D8 E7".split() if pt(p) in orbB1] == ["D9", "D8", "E7"],
    "D1 middle left: the three white stones sit in a Black ORBIT (captured)")
# "In the lower left White has completed a half-orbit.  The three black stones are
#  not captured, but Black cannot play inside the formation; ... White cannot be
#  prevented from playing on both the crossed points and forming an orbit."
chk(all(pt(p) in encW1 and pt(p) not in orbW1 for p in "C2 D2 E2".split()),
    "D1 lower left: C2/D2/E2 are inside a White HALF-orbit (not captured)")
chk(pt("C1") in encW1 and pt("D1") in encW1,
    "D1 lower left: the crossed points C1/D1 are illegal for Black")
_, caps = play(d1, M.WHITE, "C1", "D1")
chk(caps == ["C2", "D2", "E2"],
    "D1 lower left: White C1+D1 forms an orbit capturing the 3 black stones (%s)" % caps)

# The diagram draws already-captured stones with a triangle; resolve them for the
# follow-up lines so the capture counts match the captions exactly.
d1r = {p: v for p, v in d1.items() if nm(p) not in ("D9", "D8", "E7", "L8")}

# "In the upper right Black has completed a half-orbit.  The three white stones can
#  never be captured, but the single white stone is doomed ... the crossed point."
chk(all(pt(p) in encB1 and pt(p) not in orbB1 for p in "H16 I16 I15 L15".split()),
    "D1 upper right: the four white stones are inside a Black HALF-orbit")
_, caps = play(d1r, M.BLACK, "K15")
chk(caps == ["L15"],
    "D1 upper right: Black K15 captures only the single white stone (%s)" % caps)
clean1 = M._cleanup(d1r, 16, 16)
chk(all(pt(p) in clean1 for p in "H16 I16 I15".split()),
    "D1 upper right: the three edge white stones can never be captured")
chk(pt("L15") not in clean1, "D1 upper right: the single white stone is doomed")

# "At the middle right White has completed a small orbit, capturing one black stone.
#  However, if it is Black's turn, he will play on the crossed point, forming an
#  orbit and capturing the four white stones."
chk(pt("L8") in orbW1, "D1 middle right: black L8 is inside a small White orbit")
_, caps = play(d1r, M.BLACK, "M10")
chk(caps == ["K8", "L7", "L9", "M8"],
    "D1 middle right: Black M10 captures the four white stones (%s)" % caps)

# "In the lower right Black has completed a half-orbit ... White may play on the
#  crossed point, completing an orbit and capturing the four middle black stones."
chk(all(pt(p) in encB1 and pt(p) not in orbB1 for p in "L2 M2 N2 O2".split()),
    "D1 lower right: the four white stones are inside a Black HALF-orbit")
after, caps = play(d1r, M.WHITE, "P3")
chk(caps == ["L3", "M3", "N4", "O3"],
    "D1 lower right: White P3 captures the four middle black stones (%s)" % caps)
chk(pt("L2") not in enc(after, M.BLACK)[0],
    "D1 lower right: Black's half-orbit is destroyed by the capture")

# =====================================================================
# Magazine Diagram 2 -- "Shared Territory" (issue 12 p. 22)
# =====================================================================
D2_B = ("B16 F16 I16 N16 B15 F15 I15 N15 C14 F14 I14 J14 M14 D13 E13 K13 L13 "
        "M13 A9 B9 C8 D7 D6 H6 I6 A5 C5 F5 G5 J5 N5 B4 E4 F4 H4 I4 M4 O4 E3 J3 "
        "M3 O3 E2 J2 N2 F1 J1 M1")
D2_W = ("C16 E16 J16 L16 D15 J15 M15 K14 L14 N14 J13 N13 J12 A11 B11 J11 L11 "
        "C10 K10 D9 D8 N8 P8 C7 M7 O7 A6 B6 M6 L5 G4 L4 F3 H3 L3 F2 G2 M2 P2 "
        "N1 O1 P1")
d2 = board(D2_B, D2_W)
sh2, tb2, tw2 = parts(d2)

# upper left: Black four points, White none, D16 shared
chk(sub(tb2, "CDE", 13, 16) == ["C15", "D14", "E14", "E15"],
    "D2 upper left: Black's half-orbit controls four points (%s)" % sub(tb2, "CDE", 13, 16))
chk(sub(tw2, "CDE", 13, 16) == [], "D2 upper left: White's half-orbit controls none")
chk("D16" in sh2, "D2 upper left: the crossed point D16 is shared territory")
chk(pt("D16") in enc(d2, M.WHITE)[0],
    "D2 upper left: Black may not play D16, so he cannot kill White's D15")

# left: four crossed points shared; White three, Black two (B5 and C6)
chk({"A8", "B8", "A7", "B7"} <= set(sh2), "D2 left: A8/B8/A7/B7 are shared")
chk(sub(tb2, "ABCD", 3, 11) == ["B5", "C6"],
    "D2 left: Black has exactly two points of actual territory, B5 and C6")
chk(sub(tw2, "ABCD", 3, 11) == ["A10", "B10", "C9"],
    "D2 left: White has exactly three points of actual territory (%s)" % sub(tw2, "ABCD", 3, 11))

# bottom: the crossed point G3 is shared; Black connects underneath and takes five
chk("G3" in sh2, "D2 bottom: the crossed point G3 is shared territory")
_, caps = play(d2, M.BLACK, "G1", "H1", "I1")
chk(caps == ["F2", "F3", "G2", "G4", "H3"],
    "D2 bottom: connecting underneath captures five white stones (%s)" % caps)
d2g1 = dict(d2)
d2g1[pt("G1")] = M.WHITE                          # "If White had a stone at G1..."
safe = M._cleanup(d2g1, 16, 16)
chk(all(pt(p) in safe for p in "F2 G2 F3 H3 G4".split()),
    "D2 bottom: with a White stone at G1 the five white stones are safe")
chk(pt("G3") in enc(safe, M.BLACK)[0] and pt("G3") in enc(safe, M.WHITE)[0],
    "D2 bottom: with a White stone at G1 the crossed point stays shared")

# upper right: Black one point (M16), White none; three shared; White M12 -> 10
chk(sub(tb2, "IJKLMN", 13, 16) == ["M16"],
    "D2 upper right: Black has one point of territory, at M16")
chk(sub(tw2, "IJKLMN", 13, 16) == [], "D2 upper right: White has none")
chk({"K16", "K15", "L15"} <= set(sh2), "D2 upper right: K16/K15/L15 are shared")
after, caps = play(d2, M.WHITE, "M12")
chk(caps == ["K13", "L13", "M13", "M14"],
    "D2 upper right: White M12 captures the four middle black stones (%s)" % caps)
_, _, tw2b = parts(after)
chk(len(sub(tw2b, "KLM", 11, 16)) == 10,
    "D2 upper right: White then has 10 points of actual territory (%s)"
    % sub(tw2b, "KLM", 11, 16))

# bottom right: N4/N3 shared; Black L2 captures the white stone at M2
chk({"N4", "N3"} <= set(sh2), "D2 bottom right: N4 and N3 are shared territory")
_, caps = play(d2, M.BLACK, "L2")
chk(caps == ["M2"], "D2 bottom right: Black L2 captures the White stone at M2 (%s)" % caps)

# =====================================================================
# Magazine Diagram 3 -- the puzzle (issue 12 p. 23; solution p. 29)
#   "O16 is the move.  It completes a modest half-orbit connecting the top side to
#    itself, allowing White to follow up with M16.  This captures the four-stone
#    Black group..."
# =====================================================================
D3_B = ("B16 D16 P16 A15 E15 M15 N15 O15 C14 E14 H14 M14 P14 E13 H13 I13 J13 "
        "K13 L13 P13 E12 H12 O12 P12 D11 K11 L11 N11 O11 A10 B10 C10 D10 J10 "
        "L10 D9 E9 F9 H9 J9 N9 O9 F8 H8 J8 K8 L8 N8 D7 M7 N7 D6 M6 N6 D5 E5 G5 "
        "D4 E4 F4 M4 N4 B3 G3 I3 L3 M3 E2 F2 G2 I2 J2 K2 J1")
D3_W = ("E16 G16 H16 N16 B15 I15 J15 K15 L15 P15 B14 L14 O14 A13 M13 N13 O13 "
        "B12 C12 D12 M12 A11 E11 G11 I11 J11 M11 E10 F10 G10 I10 K10 M10 K9 L9 "
        "M9 M8 C7 E7 H7 I7 J7 K7 L7 A6 C6 H6 L6 C5 H5 K5 C4 G4 H4 I4 K4 D3 E3 "
        "F3 J3 K3 N3 A2 L2 M2 N2")
d3 = board(D3_B, D3_W)
chk(pt("O16") not in enc(d3, M.BLACK)[0], "D3 puzzle: O16 is a legal White move")
after_o16, caps = play(d3, M.WHITE, "O16")
chk(caps == [], "D3 puzzle: O16 itself captures nothing")
encW3, orbW3 = enc(after_o16, M.WHITE)
four = "M14 M15 N15 O15".split()
chk(all(pt(p) in encW3 for p in four) and not any(pt(p) in orbW3 for p in four),
    "D3 puzzle: O16 completes a HALF-orbit holding the four-stone Black group")
region = [p for p in encW3 if p[1] == 15]
chk(sorted(nm(p) for p in region) == ["I16", "J16", "K16", "L16", "M16"],
    "D3 puzzle: the half-orbit runs along the top side (%s)" % sorted(nm(p) for p in region))
_, caps = play(after_o16, M.WHITE, "M16")
chk(caps == ["M14", "M15", "N15", "O15"],
    "D3 puzzle: M16 then captures the four-stone Black group (%s)" % caps)

# =====================================================================
# Designer's Diagram 2 -- half-orbits
# =====================================================================
W2_B = ("F16 G16 E15 F15 J15 K15 F14 G14 M10 L9 N9 K8 N8 K7 L7 N7 F5 G5 E4 H4 "
        "B3 C3 D3 I3 A2 C2 I2 A1 G1 H1")
W2_W = ("D16 J16 K16 D15 L15 D14 I14 K14 E13 F13 I13 J13 G12 H12 N10 O10 P10 M9 "
        "M8 M7 N6 O6 P5 D2 E2 F2 G2")
w2 = board(W2_B, W2_W)
encBw2, orbBw2 = enc(w2, M.BLACK)
chk(all(pt(p) in encBw2 and pt(p) not in orbBw2 for p in "D2 E2 F2 G2".split()),
    "W2 lower left: the four white stones sit in a Black half-orbit")
_, caps = play(w2, M.BLACK, "D1", "E1", "F1")
chk(caps == ["D2", "E2", "F2", "G2"],
    "W2 lower left: Black D1/E1/F1 forms an orbit capturing four white stones (%s)" % caps)
encWw2, orbWw2 = enc(w2, M.WHITE)
chk(all(pt(p) in encWw2 for p in "F16 G16 E15 F15 F14 G14 J15 K15".split()),
    "W2 top: both black groups are inside White's half-orbit")
_, caps = play(w2, M.WHITE, "I15")
chk(caps == ["J15", "K15"],
    "W2 top: White I15 captures only the doomed two-stone black group (%s)" % caps)
chk(all(pt(p) in M._cleanup(w2, 16, 16) for p in "F16 G16 E15 F15 F14 G14".split()),
    "W2 top: the six-stone black group can never be captured")
chk(all(pt(p) in encWw2 for p in "N9 N8 N7".split()),
    "W2 right: the three black stones are inside White's half-orbit")
_, caps = play(w2, M.BLACK, "M6")
chk(caps == ["M7", "M8", "M9"],
    "W2 right: Black M6 completes an orbit capturing the three middle white stones (%s)" % caps)

# =====================================================================
# Designer's Diagram 3 -- orbits
# =====================================================================
W3_B = ("C14 D14 F14 C13 E13 G13 H13 C12 I12 D11 G11 H11 E10 F10 M10 L9 N9 C6 "
        "D6 C5 F5 C4")
W3_W = ("L12 M12 K11 M11 N11 K10 O10 J9 M9 O9 C8 I8 O8 B7 D7 E7 N7 B6 F6 K6 L6 "
        "M6 B5 G5 E4 F4 C3 D3")
w3 = board(W3_B, W3_W)
chk(pt("D13") in enc(w3, M.BLACK)[1] and pt("D12") in enc(w3, M.BLACK)[1],
    "W3 upper left: Black has completed a genuine orbit")
_, caps = play(w3, M.WHITE, "B4")
chk(caps == ["C4", "C5", "C6", "D6", "F5"],
    "W3 lower left: White B4 completes an orbit capturing five black stones (%s)" % caps)
mid, caps = play(w3, M.BLACK, "M8")
chk(caps == ["M9"], "W3 right: Black M8 captures one white stone (%s)" % caps)
_, caps = play(mid, M.WHITE, "J7")
chk(caps == ["L9", "M8", "M10", "N9"],
    "W3 right: White answers J7 and captures the black orbit -- futile for Black (%s)" % caps)

# =====================================================================
# Designer's Diagram 4 -- shared territory
# =====================================================================
W4_B = ("D16 G16 L16 N16 E15 F15 L15 N15 O15 M14 P14 L13 M12 N12 A11 B11 C10 "
        "D10 M10 N10 O10 E9 L9 P9 E8 L8 D7 L7 A6 B6 C6 M6 N5 O5 P5 I4 H3 J3 I2")
W4_W = ("C16 H16 K16 P16 B15 H15 K15 P15 C14 F14 G14 K14 L14 O14 C13 D13 E13 "
        "M13 N13 A9 B9 C9 D8 N8 O8 E7 M7 P7 E6 I6 L6 N6 O6 B5 E5 H5 J5 A4 C4 D4 "
        "G4 H4 J4 K4 G3 K3 G2 K2 H1 K1")
w4 = board(W4_B, W4_W)
sh4, tb4, tw4 = parts(w4)
chk({"E16", "F16"} <= set(sh4), "W4 upper left: E16/F16 are shared")
chk(sub(tw4, "CDEFG", 13, 16) == ["C15", "D14", "D15", "E14", "G15"],
    "W4 upper left: White's half-orbit controls five points (%s)" % sub(tw4, "CDEFG", 13, 16))
chk({"A7", "B7", "C7", "A8", "B8", "C8"} <= set(sh4), "W4 left: six shared points")
chk(sub(tb4, "ABCD", 4, 11) == ["A10", "B10", "D9"],
    "W4 left: Black has three points of actual territory (A10, B10, D9)")
chk(sub(tw4, "ABCD", 4, 11) == ["A5", "C5", "D5", "D6"],
    "W4 left: White has four points of actual territory (%s)" % sub(tw4, "ABCD", 4, 11))
chk("I3" in sh4, "W4 bottom: I3 is shared for the moment")
_, caps = play(w4, M.WHITE, "I1", "J1")
chk(caps == ["H3", "I2", "I4", "J3"],
    "W4 bottom: White connects underneath and captures four black stones (%s)" % caps)
w4b = dict(w4)
w4b[pt("I1")] = M.BLACK                            # "if Black had a stone at I1"
safe4 = M._cleanup(w4b, 16, 16)
chk(all(pt(p) in safe4 for p in "H3 I2 I4 J3".split()),
    "W4 bottom: with a Black stone at I1 the black group is safe")
chk(pt("I3") in enc(safe4, M.BLACK)[0] and pt("I3") in enc(safe4, M.WHITE)[0],
    "W4 bottom: with a Black stone at I1, I3 stays shared")
chk(sub(tw4, "LMNOP", 13, 16) == ["N14", "O16"],
    "W4 upper right: White has two points of territory, N14 and O16")
chk(sub(tb4, "LMNOP", 13, 16) == [], "W4 upper right: Black has none")
chk({"M16", "M15"} <= set(sh4), "W4 upper right: M16/M15 are shared")
after4, caps = play(w4, M.BLACK, "O13")
chk(caps == ["M13", "N13", "O14"],
    "W4 upper right: Black O13 forms an orbit capturing three white stones (%s)" % caps)
_, tb4b, tw4b = parts(after4)
chk(len(sub(tb4b, "LMNOP", 12, 16)) == 6 and len(sub(tw4b, "LMNOP", 12, 16)) == 0,
    "W4 upper right: Black then has six points of actual territory to White's zero")
chk({"N7", "O7"} <= set(sh4), "W4 right: N7 and O7 are shared")
after4b, caps = play(w4, M.WHITE, "M5")
chk(caps == ["M6"], "W4 right: White M5 captures a black stone (%s)" % caps)
_, _, tw4c = parts(after4b)
chk({"N7", "O7"} <= set(tw4c), "W4 right: White then claims N7/O7 as his own")

# =====================================================================
# Designer's Diagram 5 -- "both players pass": the scored anchor
#   "the lone black stone at C13, the eleven-stone white orbit on the left, and
#    the three-stone black group near the upper right (at J14, J13 and K13)" are
#    removed; "the white stones at N11 and N10 are alive"; 9 shared points; and
#    "Black has 58 points of territory to White's 38".
# =====================================================================
W5_B = ("A16 B16 G16 J16 M16 G15 L15 N15 G14 J14 M14 N14 O14 P14 C13 F13 G13 "
        "J13 K13 E12 H12 M12 N12 O12 A11 E11 H11 M11 P11 B10 C10 D10 G10 M10 G9 "
        "N9 O9 P9 H8 H7 L7 M7 H6 I6 J6 K6 N6 O6 P6 G5 H5 M5 E4 F4 I4 J4 K4 L4 "
        "C3 D3 J3 M3 B2 D2 J2 N2 A1 D1 I1 N1")
W5_W = ("C16 E16 I16 L16 N16 P16 A15 B15 D15 F15 H15 K15 O15 C14 E14 H14 L14 "
        "E13 H13 L13 M13 N13 O13 P13 A12 B12 C12 D12 I12 K12 I11 J11 N11 I10 "
        "N10 C9 D9 I9 J9 B8 E8 F8 J8 K8 L8 M8 P8 B7 F7 J7 N7 O7 C6 F6 D5 E5 N5 "
        "O5 P5 A4 M4 A3 E3 F3 G3 K3 L3 N3 A2 E2 H2 K2 O2 P2 B1 C1 E1 F1 G1 H1 "
        "K1 O1")
w5 = board(W5_B, W5_W)
clean5 = M._cleanup(w5, 16, 16)
dead_b = names(p for p, v in w5.items() if v == M.BLACK and p not in clean5)
dead_w = names(p for p, v in w5.items() if v == M.WHITE and p not in clean5)
chk(dead_b == ["C13", "J13", "J14", "K13"],
    "W5: dead black = C13 plus the J14/J13/K13 group (%s)" % dead_b)
chk(len(dead_w) == 11, "W5: dead white = the eleven-stone group on the left (%s)" % dead_w)
chk("N11" not in dead_w and "N10" not in dead_w, "W5: White N11 and N10 stay alive")
sh5, tb5, tw5 = parts(clean5)
chk(sh5 == sorted("F2 G2 L2 M2 L1 M1 O11 O10 P10".split()),
    "W5: exactly the nine published shared points (%s)" % sh5)
chk((len(tb5), len(tw5)) == (58, 38),
    "W5: final score Black 58, White 38 (got %d/%d)" % (len(tb5), len(tw5)))
chk(M._final_score(w5, 16, 16) == (58, 38), "W5: _final_score agrees")

# =====================================================================
# Designer's Diagram 6 -- a completed pen-and-paper game (dead stones crossed out)
#   "Black has won by a score of 72 to 27 ... a total of 25 points of shared
#    territory on the board."
# =====================================================================
W6_B = ("A16 O16 P16 B15 N15 O15 C14 M14 N14 D13 L13 O13 D12 J12 L12 M12 O12 "
        "D11 M11 E10 F10 G10 I10 L10 N10 O10 F9 H9 L9 D8 E8 F8 G8 I8 K8 B7 C7 "
        "E7 F7 H7 J7 B6 G6 I6 J6 A5 K5 P5 K4 L4 P4 K3 M3 O3 P3 B2 C2 K2 M2 N2 "
        "P2 A1 D1 E1 K1 M1")
W6_W = ("L16 M16 K15 M15 P15 K14 L14 O14 P14 K13 M13 N13 K12 N12 H11 I11 J11 "
        "N11 O11 P11 H10 I9 J9 K9 J8 D7 K7 O7 C6 E6 F6 H6 K6 L6 N6 P6 B5 D5 G5 "
        "I5 J5 L5 M5 O5 A4 B4 E4 H4 M4 N4 O4 B3 C3 F3 G3 L3 N3 A2 D2 E2 L2 O2 "
        "F1 L1 N1 P1")
w6 = board(W6_B, W6_W)
sh6, tb6, tw6 = parts(w6)
chk((len(tb6), len(tw6), len(sh6)) == (72, 27, 25),
    "W6: Black 72, White 27, 25 shared (got %d/%d/%d)" % (len(tb6), len(tw6), len(sh6)))
chk(M._cleanup(w6, 16, 16) == w6, "W6: the finished position is stable under removal")

# ---------------------------------------------------------------------
# The end-of-game removal is a FIXPOINT, not a single pass.  In this 9x9
# position Black's exclusive fill first orbits two white stones; only once they
# are gone does White stop enclosing (and thus sharing) the points around them,
# so Black's fill grows and orbits five more.  A one-pass removal stops at 2.
# ---------------------------------------------------------------------
CASCADE = {'2,2': 0, '3,1': 0, '3,2': 1, '3,3': 0, '4,2': 0, '4,3': 0, '4,4': 1,
           '4,5': 0, '5,1': 0, '5,3': 1, '5,4': 0, '5,5': 1, '5,6': 0, '6,0': 0,
           '6,2': 1, '6,3': 0, '6,5': 1, '6,6': 1, '6,7': 0, '7,1': 0, '7,2': 1,
           '7,4': 1, '7,6': 0, '8,0': 0, '8,1': 1, '8,4': 1, '8,5': 0}
casc = {tuple(int(x) for x in k.split(",")): v for k, v in CASCADE.items()}
casc_clean = M._cleanup(casc, 9, 9)
casc_dead = {p: v for p, v in casc.items() if p not in casc_clean}
chk(len(casc_dead) == 7,
    "cleanup runs to a fixpoint: 7 stones die here, not the 2 of a single pass (%d)"
    % len(casc_dead))
chk(all(v == M.WHITE for v in casc_dead.values()),
    "cleanup cascade: all seven casualties are White")

# =====================================================================
# Rule-level invariants
# =====================================================================
g = GAME
s0 = g.initial_state()
chk(g.num_players == 2 and s0.size == 16, "16x16 board, two players")
chk(MAN["options"]["size"]["default"] == 16
    and MAN["options"]["size"]["choices"] == [9, 11, 13, 16],
    "manifest: 16x16 is the default board size")
chk(MAN["options"]["opening"]["choices"] == ["pie", "refined"],
    "manifest: both published opening protocols are offered")
chk(len(g.legal_moves(s0)) == 16 * 16 + 1, "opening: every point plus pass is legal")
chk(g.current_player(s0) == 0, "Black (seat 0) moves first")

# render() shape (Board.jsx contract)
spec = g.render(s0)
chk(spec["board"]["type"] == "square" and spec["board"]["width"] == 16
    and spec["board"]["height"] == 16, "render: 16x16 square board")
chk(spec["pieces"] == [] and isinstance(spec["board"].get("tints"), dict),
    "render: empty board has no pieces and a tints dict")

# a mid-game render: pieces are dicts with a 'c,r' cell and an owner seat
mid = g.deserialize(g.serialize(s0))
for mv in ("3,3", "5,5", "3,4", "6,6", "4,3", "7,7", "4,4"):
    mid = g.apply_move(mid, mv)
spec = g.render(mid)
chk(len(spec["pieces"]) == 7, "render: seven stones on the board")
for pc in spec["pieces"]:
    chk(isinstance(pc["cell"], str) and pc["cell"].count(",") == 1
        and pc["owner"] in (0, 1), "render: well-formed piece %r" % pc)
chk(all(k.count(",") == 1 for k in spec["board"]["tints"]), "render: tint keys are cell ids")
chk(g.deserialize(g.serialize(mid)).board == mid.board, "serialize round-trips")
chk(g.serialize(g.deserialize(g.serialize(mid))) == g.serialize(mid),
    "serialize/deserialize is stable")

# the 8-connected wall / 4-connected region duality
b = dict()
for c, r in ((3, 3), (4, 3), (5, 3), (3, 4), (5, 4), (3, 5), (4, 5), (5, 5)):
    b[(c, r)] = M.BLACK
encb, orbb = M._enclosures(M._stones(b, M.BLACK), 16, 16)
chk(orbb == {(4, 4)}, "a ring of eight black stones orbits exactly its centre")
# diagonal ring (the 8-connectivity dual): four diagonal neighbours seal a point
b2 = {(4, 3): M.BLACK, (3, 4): M.BLACK, (5, 4): M.BLACK, (4, 5): M.BLACK}
chk(M._enclosures(M._stones(b2, M.BLACK), 16, 16)[1] == {(4, 4)},
    "four orthogonally-placed stones seal the point between them")

# The shipped test works on the complement of ALL of a player's stones; rule 5
# says "a connected group".  They must agree -- own stones inside your own
# formation only shrink a complement component, whose side-mask can then only
# lose bits.  Differential-check that on every published diagram and on random
# positions.
def _groups8(stones):
    seen, out = set(), []
    for p in stones:
        if p in seen:
            continue
        stack, grp = [p], {p}
        seen.add(p)
        while stack:
            c, r = stack.pop()
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    q = (c + dc, r + dr)
                    if q in stones and q not in seen:
                        seen.add(q)
                        stack.append(q)
                        grp.add(q)
        out.append(grp)
    return out


def _per_group(stones, w, h):
    """Rules-as-written: evaluate each connected group on its own."""
    e, o = set(), set()
    for grp in _groups8(stones):
        ge, go = M._enclosures(grp, w, h)
        e |= ge
        o |= go
    return e, o


def _model_agrees(bd, w, h):
    for col in (M.BLACK, M.WHITE):
        st = M._stones(bd, col)
        ea, oa = M._enclosures(st, w, h)
        eb, ob = _per_group(st, w, h)
        keep = lambda S: {p for p in S if p not in bd or bd.get(p) == 1 - col}
        if keep(ea) != keep(eb) or keep(oa) != keep(ob):
            return False
    return True


chk(all(_model_agrees(bd, 16, 16) for bd in (d1, d2, d3, w2, w3, w4, w5, w6)),
    "enclosure model: the complement test matches the per-connected-group rule "
    "on all eight published diagrams")
import random as _rnd                                                 # noqa: E402
_bad = 0
for _seed in range(150):
    _r = _rnd.Random(_seed)
    _bd = {(c, r): _r.randrange(2) for c in range(8) for r in range(8)
           if _r.random() < 0.5}
    if not _model_agrees(_bd, 8, 8):
        _bad += 1
chk(_bad == 0, "enclosure model: the two readings also agree on 150 random 8x8 "
               "positions (%d divergences)" % _bad)

# a corner is never enclosed (quarter-orbit), an edge pocket is
corner = {(1, 0): M.WHITE, (0, 1): M.WHITE, (1, 1): M.WHITE}
chk((0, 0) not in M._enclosures(M._stones(corner, M.WHITE), 16, 16)[0],
    "a bare corner point is NOT enclosed (it needs two sides)")
edge = {(2, 0): M.WHITE, (2, 1): M.WHITE, (3, 1): M.WHITE, (4, 1): M.WHITE,
        (4, 0): M.WHITE}
chk((3, 0) in M._enclosures(M._stones(edge, M.WHITE), 16, 16)[0],
    "an edge pocket IS enclosed (half-orbit on the bottom side)")

# prohibition is one-way: your own formations never bind you
st = g.initial_state()
for mv in ("2,0", "10,10", "2,1", "11,10", "3,1", "12,10", "4,1", "13,10", "4,0"):
    st = g.apply_move(st, mv)                    # Black builds the edge pocket
chk(g.current_player(st) == 1, "White to move after nine plies")
chk("3,0" not in g.legal_moves(st), "White may not play inside Black's half-orbit")
st_b = g.apply_move(st, "14,10")                 # White elsewhere
chk("3,0" in g.legal_moves(st_b), "Black MAY play inside his own half-orbit")

# no self-capture: filling your own orbit never removes your stones
st_fill = g.apply_move(st_b, "3,0")
chk(len(M._stones(st_fill.board, M.BLACK)) == 6,
    "no self-capture when Black fills his own formation")
# ... and structurally: an orbit region is built from the complement of the
# mover's own stones, so it can never contain one of them.
chk(not (M._enclosures(M._stones(st_fill.board, M.BLACK), 16, 16)[1]
         & M._stones(st_fill.board, M.BLACK)),
    "an orbit region never intersects its own wall's stones (self-capture is impossible)")


def state_from(bd, colour, swapped=False):
    """A mid-game state holding `bd`, with `colour` to move."""
    return g.deserialize({
        "size": 16, "opening": "pie", "to_move": colour, "swapped": swapped,
        "passes": 0, "ply": 40, "last_move": None, "last_captures": [],
        "prev_point": None, "mirror": [0, 0],
        "board": {"%d,%d" % p: v for p, v in bd.items()},
    })


# The capture path of the ENGINE's own apply_move (the diagram anchors above go
# through the local `play` helper, which reimplements it).  Magazine Diagram 1,
# lower left: White plays both crossed points and orbits the three black stones.
s_d1 = state_from(d1r, M.WHITE)          # d1r: the diagram's already-captured stones resolved
chk("2,0" in g.legal_moves(s_d1), "engine: C1 is a legal White move")
mid1 = g.apply_move(s_d1, "2,0")                       # White C1
chk(mid1.last_captures == (), "engine: C1 alone captures nothing")
chk(g.current_player(mid1) == 0 and "3,0" not in g.legal_moves(mid1),
    "engine: Black still may not play D1 inside White's half-orbit")
mid2 = g.apply_move(mid1, "5,5")                       # Black plays elsewhere
chk("x3" in g.describe_move(mid2, "3,0"),
    "engine: describe_move announces the three captures (%s)" % g.describe_move(mid2, "3,0"))
fin1 = g.apply_move(mid2, "3,0")                       # White D1 completes the orbit
chk(names(fin1.last_captures) == ["C2", "D2", "E2"],
    "engine apply_move: White D1 orbits and captures C2/D2/E2 (%s)" % names(fin1.last_captures))
chk(all(pt(p) not in fin1.board for p in "C2 D2 E2".split()),
    "engine apply_move: the captured stones really leave the board")
chk(len(M._stones(fin1.board, M.WHITE)) == len(M._stones(d1r, M.WHITE)) + 2,
    "engine apply_move: White loses nothing of his own")

# render() on a position that actually emits tints (the empty board emits none,
# so the shape of a real tint map would otherwise go unchecked).  Magazine
# Diagram 2 exercises all three branches: Black-only, White-only and shared.
spec_t = g.render(state_from(d2, M.WHITE))
tints_t = spec_t["board"]["tints"]
chk(len(set(tints_t.values())) == 3,
    "render: Diagram 2 tints both players' territory plus shared (%d distinct colours)"
    % len(set(tints_t.values())))
chk({pt(p) for p in ("A7", "B7", "A8", "B8", "D16", "G3")}
    <= {tuple(int(x) for x in k.split(",")) for k in tints_t},
    "render: the published shared points are tinted")
cells16 = {"%d,%d" % (c, r) for c in range(16) for r in range(16)}
chk(len(tints_t) > 0, "render: a position with territory emits a non-empty tint map")
chk(all(isinstance(k, str) and k in cells16 for k in tints_t),
    "render: every tint key is a 'c,r' board cell id")
chk(all(isinstance(v, str) and v.startswith("#") for v in tints_t.values()),
    "render: every tint value is a colour string")
chk({p["cell"] for p in spec_t["pieces"]} <= cells16,
    "render: every piece sits on a real cell id")
chk(not (set(tints_t) & {p["cell"] for p in spec_t["pieces"]}),
    "render: tints mark only vacant points, never a point under a stone")
# the board is drawn by SEAT, so after a swap every stone changes side
spec_sw = g.render(state_from(d2, M.WHITE, swapped=True))
owners = {p["cell"]: p["owner"] for p in spec_t["pieces"]}
chk(all(p["owner"] == 1 - owners[p["cell"]] for p in spec_sw["pieces"]),
    "render: after a swap the pieces are drawn for the other seat")
chk(all("," not in m or m in cells16 for m in g.legal_moves(state_from(d2, M.WHITE))),
    "render: cell moves use the same ids the board draws")
chk(isinstance(json.dumps(spec_t), str)
    and isinstance(json.dumps(g.serialize(state_from(d2, M.WHITE))), str),
    "render/serialize output is JSON-serialisable")

# pie rule
s1 = g.apply_move(g.initial_state(), "7,7")
chk("swap" in g.legal_moves(s1), "White is offered the pie swap on move 2")
s2 = g.apply_move(s1, "swap")
chk(s2.swapped and g.current_player(s2) == 0 and s2.to_move == M.WHITE,
    "after the swap seat 1 holds Black and seat 0 moves as White")
chk("swap" not in g.legal_moves(s2), "the swap is offered only once")

# refined pie rule (designer's rules page, rule 6)
r0 = g.initial_state(options={"opening": "refined"})
r1 = g.apply_move(r0, "7,7")
r2 = g.apply_move(r1, "8,8")
r3 = g.apply_move(r2, "7,8")
chk([g.current_player(x) for x in (r0, r1, r2)] == [0, 0, 0],
    "refined: Player 1 makes the first three moves")
chk([x.to_move for x in (r0, r1, r2)] == [M.BLACK, M.WHITE, M.BLACK],
    "refined: those three moves are Black, White, Black")
chk(g.current_player(r3) == 1 and sorted(g.legal_moves(r3)) == ["take:black", "take:white"],
    "refined: Player 2 then picks a colour")
rw = g.apply_move(r3, "take:white")
chk(not rw.swapped and rw.to_move == M.WHITE and g.current_player(rw) == 1,
    "refined: taking White leaves seat 1 to move as White")
rb = g.apply_move(r3, "take:black")
chk(rb.swapped and rb.to_move == M.WHITE and g.current_player(rb) == 0,
    "refined: taking Black leaves seat 0 to move as White")
rp = g.apply_move(g.apply_move(g.apply_move(r0, "7,7"), "pass"), "pass")
chk(not g.is_terminal(rp), "refined: passes inside the setup phase do not end the game")

# double pass -> honest draw on an empty board
p1 = g.apply_move(g.initial_state(), "pass")
p2 = g.apply_move(p1, "pass")
chk(g.is_terminal(p2) and g.returns(p2) == [0.0, 0.0],
    "a symmetric double pass is an honest draw")

# returns follow the SEAT after a swap
sw = g.apply_move(g.apply_move(g.initial_state(), "7,7"), "swap")
for c, r in ((0, 2), (1, 2), (2, 2), (0, 1), (2, 1), (0, 0), (2, 0)):
    sw.board[(c, r)] = M.BLACK                   # Black owns 1 point of territory
sw = g.apply_move(g.apply_move(sw, "pass"), "pass")
chk(g.is_terminal(sw) and g.returns(sw) == [-1.0, 1.0],
    "after a swap the Black result is credited to seat 1 (%s)" % g.returns(sw))

# heuristic shape: a LIST of num_players payoffs, exercised at a rollout cutoff
h = g.heuristic(mid)
chk(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
    "heuristic returns a two-element zero-sum list (%r)" % (h,))

# anti-mirroring (designer's rules page, rule 5)
m = g.initial_state()
seq = []
for i in range(9):                               # nine mirrored White replies
    seq += [(3, 3 + i), (12, 12 - i)]
seq.append((3, 12))
for c, r in seq:
    chk(f"{c},{r}" in g.legal_moves(m), "mirror: %d,%d still legal" % (c, r))
    m = g.apply_move(m, f"{c},{r}")
chk(m.mirror[M.WHITE] == 9, "mirror: White has mirrored nine times running (%d)"
    % m.mirror[M.WHITE])
chk("12,3" not in g.legal_moves(m), "mirror: a tenth successive mirror is forbidden")
chk("12,2" in g.legal_moves(m), "mirror: any other point is still legal")
m2 = g.apply_move(m, "12,2")                     # break the chain, then resume
chk(m2.mirror[M.WHITE] == 0, "mirror: the streak resets on a non-mirroring move")

# randomised invariant sweep
import random                                                       # noqa: E402
for seed in range(6):
    rng = random.Random(seed)
    st = g.initial_state(options={"size": 9,
                                  "opening": "refined" if seed % 2 else "pie"})
    while not g.is_terminal(st):
        legal = g.legal_moves(st)
        chk(bool(legal), "sweep: legal_moves is never empty before terminal")
        mover = st.to_move
        mine_before = M._stones(st.board, mover)
        own, _ = M._enclosures(mine_before, 9, 9)
        theirs, _ = M._enclosures(M._stones(st.board, 1 - mover), 9, 9)
        if st.mirror[mover] == 0:            # no anti-mirror block in force
            chk(all("%d,%d" % p in legal
                    for p in own - theirs if p not in st.board),
                "sweep: your OWN formations never prohibit you (only shared "
                "points, which the opponent also encloses, are off limits)")
        mv = rng.choice(legal)
        nxt = g.apply_move(st, mv)
        chk(g.serialize(g.deserialize(g.serialize(nxt))) == g.serialize(nxt),
            "sweep: serialize round-trips")
        if "," in mv:
            chk(M._stones(nxt.board, mover) >= mine_before,
                "sweep: a placement never removes the mover's own stones")
            here = tuple(int(x) for x in mv.split(","))
            _, orb = M._enclosures(mine_before | {here}, 9, 9)
            chk(all(st.board.get(p) == 1 - mover and p in orb
                    for p in nxt.last_captures),
                "sweep: captures are enemy stones inside a new orbit")
        st = nxt
    chk(len(g.returns(st)) == 2 and abs(sum(g.returns(st))) < 1e-9,
        "sweep: returns is a two-element zero-sum list")
    fin = M._cleanup(st.board, 9, 9)
    eb, _ = M._enclosures(M._stones(fin, M.BLACK), 9, 9)
    ew, _ = M._enclosures(M._stones(fin, M.WHITE), 9, 9)
    vac = [(c, r) for r in range(9) for c in range(9) if (c, r) not in fin]
    b = sum(1 for p in vac if p in eb and p not in ew)
    w = sum(1 for p in vac if p in ew and p not in eb)
    sh = sum(1 for p in vac if p in eb and p in ew)
    dame = len(vac) - b - w - sh
    chk(b + w + sh + dame + len(fin) == 81 and dame >= 0,
        "sweep: territory + shared + dame + stones == the whole board")
    chk(M._final_score(st.board, 9, 9) == (b, w), "sweep: _final_score agrees")

# the "own formations never bind you" invariant, checked over the sweep
chk(True, "sweep complete")

# ply cap terminates even without a double pass
cap = g.initial_state(options={"size": 9})
cap.ply = 3 * 9 * 9
chk(g.is_terminal(cap) and g.legal_moves(cap) == [], "the hard ply cap ends the game")

print("orbit selftest: %d failure(s)" % len(FAILS))
if FAILS:
    sys.exit(1)
print("OK")
