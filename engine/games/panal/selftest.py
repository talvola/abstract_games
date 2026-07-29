#!/usr/bin/env python3
"""Panal selftest -- correctness anchors, pure stdlib.

TWO INDEPENDENT SOURCES, both by the author:

  1. the article https://www.chessvariants.com/hexagonal.dir/panal.html --
     prose rules, a setup diagram (`ghex-setup.gif`), a SAMPLE GAME with a
     mid-game diagram (`ghex-sample.gif`), and
  2. the author's own Zillions rules file, `panal.zip` ->  `panal.zrf`, linked
     from that page.

They disagree in exactly one place and the ZRF wins: the article's setup TABLE
prints both Soldier rows on ranks 1/9, which would put five Soldiers on top of
the two Gunnes, the Princess and the Monarch. The ZRF's `board-setup`, the
setup diagram, and every single move of the sample game all say ranks 3/7.

The anchors here, strongest first:

  * THE PUBLISHED SAMPLE GAME, all 17 half-moves: each is legal, our move-log
    notation reproduces the author's for 13 of the 17 verbatim -- including all
    three of his `+` marks and no extra ones -- and for the other four it is
    his notation with a documented departure (three shooting captures he prints
    as a bare `xm7`, which no move log could tell from a capture by moving, and
    the misprinted `Gh9xh6`; his `!!` on ply 17 is an annotation, not
    notation), and the position after 8...Pp4-n4 matches his diagram
    piece-for-piece (19 pieces);
  * THE ZRF'S 61 `(run <cell>)` ENTRIES, which enumerate the whole board, and
    its `board-setup`, both transcribed verbatim here as an independent check
    of the cell set and the start position;
  * hand-derived move sets for every piece of the start position (perft(1) =
    46 counted by hand, piece by piece), plus perft(2) = 2,069 and
    perft(3) = 96,352 for regression;
  * constructive tests for each piece's rule, for both loss conditions, for
    the "a decisive result outranks every draw counter" ordering, and for
    serialisation.
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                        # noqa: E402

HERE = Path(__file__).resolve().parent
MAN, GAME = load_from_dir(HERE)
# Resolve the LIVE module (load_from_dir imports game.py under a synthetic
# name, so `import games.panal.game` would patch a DIFFERENT module object).
G = sys.modules[type(GAME).__module__]
cell_name, name_cell = G.cell_name, G.name_cell
WHITE, BLACK = G.WHITE, G.BLACK

ok = 0


def check(cond, msg):
    global ok
    assert cond, "FAIL: " + msg
    ok += 1


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def pos(white: str, black: str, to_move: int = WHITE, **kw):
    """Build a state from Overby notation: pos("Mm1 Pe1 Si5", "Me9 Pm9")."""
    board = {}
    for spec, owner in ((white, WHITE), (black, BLACK)):
        for tok in spec.split():
            board[name_cell(tok[1:])] = (owner, tok[0])
    s = G.PState(board=board, to_move=to_move, **kw)
    s.reps = {GAME.poskey(board, to_move): 1}
    return s


def mv(frm: str, to: str, shoot: bool = False) -> str:
    """Move string from two Overby cell names."""
    f, t = name_cell(frm), name_cell(to)
    return f"{f[0]},{f[1]}>{t[0]},{t[1]}" + ("=SHOOT" if shoot else "")


def dests(s, frm: str):
    """Destination names reachable from `frm`; a shoot is suffixed '*'."""
    pre = "%d,%d>" % name_cell(frm)
    return {cell_name(G.parse_cell(m[len(pre):].split("=")[0]))
            + ("*" if m.endswith("=SHOOT") else "")
            for m in GAME.legal_moves(s) if m.startswith(pre)}


# --------------------------------------------------------------------------
# 1. Board geometry -- the ZRF's own 61 cells
# --------------------------------------------------------------------------
# Transcribed from panal.zrf's Monarch `(run <cell>)` list, which enumerates
# every cell of the board (it is the list of possible swap partners' cells).
ZRF_CELLS = (
    "a5 b4 b6 c3 c5 c7 d2 d4 d6 d8 e1 e3 e5 e7 e9 f2 f4 f6 f8 g1 g3 g5 g7 g9 "
    "h2 h4 h6 h8 i1 i3 i5 i7 i9 j2 j4 j6 j8 k1 k3 k5 k7 k9 l2 l4 l6 l8 m1 m3 "
    "m5 m7 m9 n2 n4 n6 n8 o3 o5 o7 p4 p6 q5").split()

check(len(ZRF_CELLS) == 61, "the ZRF enumerates 61 cells")
check({cell_name(c) for c in G.CELLS} == set(ZRF_CELLS),
      "our 61 axial cells are exactly the ZRF's 61 named cells")
check(all(name_cell(cell_name(c)) == c for c in G.CELLS),
      "cell_name / name_cell round-trip on all 61 cells")
check(all(name_cell(n) in G.CELLS for n in ZRF_CELLS), "every ZRF name parses")

# Rank 1 has 5 cells, rank 5 has 9 -- the hexhex of side 5, ranks HORIZONTAL.
by_rank = {}
for c in G.CELLS:
    by_rank.setdefault(cell_name(c)[1:], []).append(c)
check([len(by_rank[str(n)]) for n in range(1, 10)] == [5, 6, 7, 8, 9, 8, 7, 6, 5],
      "rank sizes 5,6,7,8,9,8,7,6,5")

# Six directions, closed under negation; NO hex diagonal exists in this game.
check(len(set(G.DIRS)) == 6, "six directions")
check(all((-d[0], -d[1]) in G.DIRS for d in G.DIRS), "directions come in pairs")

# The Horseman's 12 cells, derived a SECOND way: two steps in the same
# direction, or in two directions 60 deg apart (the 120 deg / 180 deg
# combinations land on an adjacent cell or the origin, which the rules exclude).
pairs = set()
for i, (aq, ar) in enumerate(G.DIRS):
    for j in (i, (i + 1) % 6):
        bq, br = G.DIRS[j]
        pairs.add((aq + bq, ar + br))
check(set(G.HORSE) == pairs and len(G.HORSE) == 12,
      "HORSE = the 12 cells at hex-distance 2 (two derivations agree)")
check(not (set(G.HORSE) & (set(G.DIRS) | {(0, 0)})),
      "a Horseman never ends on its own hex nor on one adjacent to it")

# --------------------------------------------------------------------------
# 2. Start position -- the ZRF's board-setup, verbatim
# --------------------------------------------------------------------------
ZRF_SETUP = {
    (WHITE, "M"): "m1", (WHITE, "P"): "e1", (WHITE, "G"): "g1 k1",
    (WHITE, "H"): "f2 h2 j2 l2", (WHITE, "S"): "e3 g3 i3 k3 m3",
    (BLACK, "M"): "e9", (BLACK, "P"): "m9", (BLACK, "G"): "g9 k9",
    (BLACK, "H"): "f8 h8 j8 l8", (BLACK, "S"): "e7 g7 i7 k7 m7",
}
want = {name_cell(n): k for k, v in ZRF_SETUP.items() for n in v.split()}
s0 = GAME.initial_state()
check(s0.board == want, "start position == the ZRF's board-setup (26 pieces)")
check(len(s0.board) == 26 and GAME.current_player(s0) == WHITE,
      "26 pieces, White to move")
# The start position is the 180 deg rotation of itself (point symmetry through
# the centre i5), which is how Princess e1 faces Monarch e9.
check(all(s0.board.get((-q, -r)) == (1 - o, t)
          for (q, r), (o, t) in s0.board.items()),
      "Black's array is White's rotated 180 deg")
check(not GAME.is_terminal(s0), "the opening position is not terminal")

# --------------------------------------------------------------------------
# 3. perft(1): every start move, counted by hand off the diagram
# --------------------------------------------------------------------------
OPENING = {
    "e3": {"c3", "c5", "d4", "f4", "g5"},          # Soldier: 1 fwd/side + 2 fwd
    "g3": {"e5", "f4", "h4", "i5"},                # E and W blocked by friends
    "i3": {"g5", "h4", "j4", "k5"},
    "k3": {"i5", "j4", "l4", "m5"},
    "m3": {"k5", "l4", "n4", "o3", "o5"},
    "f2": {"c3", "d4", "f4", "h4", "i1"},          # Horseman: 12 minus off-board
    "h2": {"d2", "f4", "h4", "j4"},                #  and minus friends
    "j2": {"h4", "j4", "l4", "n2"},
    "l2": {"i1", "j4", "l4", "n4", "o3"},
    "g1": {"i1"},                                  # Gunne: its ONLY empty
    "k1": {"i1"},                                  #  neighbour; no screen+enemy
    "e1": {"a5", "b4", "c3", "d2"},                # Princess: one open line
    "m1": set(),                                   # Monarch: not in check
}
for cellnm, want_dests in OPENING.items():
    check(dests(s0, cellnm) == want_dests,
          f"opening moves of the piece on {cellnm}: {dests(s0, cellnm)}")
check(len(GAME.legal_moves(s0)) == 46, "perft(1) = 46")
check(len(set(GAME.legal_moves(s0))) == 46, "no duplicate move strings")


def perft(s, d):
    if d == 0:
        return 1
    if GAME.is_terminal(s):
        return 0
    if d == 1:
        return len(GAME.legal_moves(s))
    return sum(perft(GAME.apply_move(s, m), d - 1) for m in GAME.legal_moves(s))


check(perft(s0, 2) == 2069, "perft(2) = 2069")
check(perft(s0, 3) == 96352, "perft(3) = 96352")

# --------------------------------------------------------------------------
# 4. THE PUBLISHED SAMPLE GAME (the end-to-end anchor)
# --------------------------------------------------------------------------
# (from, to, shoot, the author's own notation for the move)
SAMPLE = [
    ("i3", "g5", 0, "Si3-g5"),   ("i7", "h6", 0, "Si7-h6"),
    # "xm7" / "xm3": shooting captures. "If the Gunne had actually moved to
    # capture the notation would be Gg1xm7 or Gg9xm3, respectively."
    ("g1", "m7", 1, "Gg1*m7"),   ("g9", "m3", 1, "Gg9*m3"),
    ("g5", "h6", 0, "Sg5xh6"),
    # The page prints "Gh9xh6"; h9 is not a cell of the board (its rank-9 cells
    # are e,g,i,k,m) and only the Gunne on k9 can make this capture -- hopping
    # the Horseman on j8 to land on h6. The final diagram confirms it: k9 is
    # empty there and g9 still holds its Gunne.
    ("k9", "h6", 0, "Gk9xh6"),
    ("j2", "j4", 0, "Hj2-j4"),   ("h6", "k3", 1, "Gh6*k3"),
    ("j4", "h6", 0, "Hj4xh6"),   ("j8", "h6", 0, "Hj8xh6"),
    ("h2", "k3", 0, "Hh2-k3"),   ("m9", "q5", 0, "Pm9-q5+"),
    ("l2", "o3", 0, "Hl2-o3+"),  ("q5", "p4", 0, "Pq5-p4"),
    ("k3", "m5", 0, "Hk3-m5+"),  ("p4", "n4", 0, "Pp4-n4"),
    ("f2", "i3", 0, "Hf2-i3"),
]
s = GAME.initial_state()
after16 = None
for i, (frm, to, shoot, notation) in enumerate(SAMPLE):
    m = mv(frm, to, shoot)
    check(m in GAME.legal_moves(s), f"sample game ply {i+1} ({notation}) is legal")
    check(GAME.describe_move(s, m) == notation,
          f"sample game ply {i+1} notation: {GAME.describe_move(s, m)} != {notation}")
    s = GAME.apply_move(s, m)
    if i == 15:
        after16 = s

# The author's diagram "Position after 8...Pp4-n4" (ghex-sample.gif).
DIAGRAM = {
    "e9": (BLACK, "M"), "g9": (BLACK, "G"), "f8": (BLACK, "H"),
    "h8": (BLACK, "H"), "l8": (BLACK, "H"), "e7": (BLACK, "S"),
    "g7": (BLACK, "S"), "k7": (BLACK, "S"), "h6": (BLACK, "H"),
    "n4": (BLACK, "P"),
    "m5": (WHITE, "H"), "o3": (WHITE, "H"), "e3": (WHITE, "S"),
    "g3": (WHITE, "S"), "f2": (WHITE, "H"), "e1": (WHITE, "P"),
    "g1": (WHITE, "G"), "k1": (WHITE, "G"), "m1": (WHITE, "M"),
}
check({cell_name(c): v for c, v in after16.board.items()} == DIAGRAM,
      "position after 8...Pp4-n4 matches the author's diagram (19 pieces)")
# "Nothing can stop White's Hi3-l2+, fatally trapping the Princess."
reply = sorted(GAME.legal_moves(s))[0]
check(mv("i3", "l2") in GAME.legal_moves(GAME.apply_move(s, reply)),
      "the threatened Hi3-l2 is available")
check(GAME.attacked(GAME.apply_to_board(after16.board, name_cell("f2"),
                                        name_cell("l2"), ""),
                    name_cell("n4"), WHITE),
      "a Horseman on l2 attacks the Princess on n4")

# THE PUBLISHED DOUBLE PIN. After 3...Gk9xh6 the author writes: "The recapture
# with the Gunne moving creates a double pin. Neither the Soldier at k3 nor the
# Horseman at l2 may leave the line between the Gunne and the White Monarch."
# The Gunne on h6 needs exactly ONE screen to reach m1, so with two friendly
# pieces on that line each may move only ALONG it.
pin = GAME.initial_state()
for frm, to, shoot, _ in SAMPLE[:6]:
    pin = GAME.apply_move(pin, mv(frm, to, shoot))
check(pin.to_move == WHITE and not GAME.in_check(pin.board, WHITE),
      "White is to move and NOT in check (two screens, so no threat yet)")
check(dests(pin, "k3") == {"i5", "j4"},
      f"the pinned Soldier may only move along the h6-m1 line: {dests(pin, 'k3')}")
check(dests(pin, "l2") == {"j4"},
      f"the pinned Horseman likewise: {dests(pin, 'l2')}")
# ...and if one of them WERE off the line, the Monarch would be in check.
check(GAME.attacked(GAME.apply_to_board(pin.board, name_cell("k3"),
                                        name_cell("m3"), ""),
                    name_cell("m1"), BLACK),
      "with only one screen left the Gunne does threaten m1")

# --------------------------------------------------------------------------
# 5. Soldier
# --------------------------------------------------------------------------
ROYALS_W, ROYALS_B = "Mm1 Pe1", "Me9 Pm9"
s = pos(ROYALS_W + " Si5", ROYALS_B)
check(dests(s, "i5") == {"h6", "j6", "g5", "k5", "g7", "k7"},
      "Soldier: 2 forward + 2 sideways + 2 double-forward, never backward")
check(dests(s, "i5").isdisjoint({"h4", "j4"}), "Soldier never moves backward")
# The double step is NOT restricted to the home rank (the ZRF has no start-cell
# guard): i5 is nowhere near White's third rank.
check({"g7", "k7"} <= dests(s, "i5"), "double step available away from home")

s = pos(ROYALS_W + " Si5", ROYALS_B + " Sh6 Sk5 Sh4")
check(dests(s, "i5") == {"h6", "k5", "j6", "g5", "k7"},
      "Soldier captures forward AND sideways, but cannot capture backward "
      "(h4), and the blocked double step g7 is gone")
s = pos(ROYALS_W + " Si5 Sg7", ROYALS_B)
check("g7" not in dests(s, "i5"), "double step blocked by a friend on the far hex")
s = pos(ROYALS_W + " Si5", ROYALS_B + " Sg7")
check("g7" not in dests(s, "i5"), "double step cannot capture on the far hex")
# No promotion: a Soldier on the last rank simply has no forward move left.
s = pos(ROYALS_W + " Si9", ROYALS_B)
check(dests(s, "i9") == {"g9", "k9"}, "Soldier on rank 9: sideways only")
check(not any("=" in m for m in GAME.legal_moves(s)), "no promotion choices")
# No en passant: after a double step past a hex a Soldier attacks, nothing of
# the passing Soldier can be taken except ON its own cell.
s = pos(ROYALS_W + " Se3", ROYALS_B + " Se5", to_move=WHITE)
check(GAME.attacked(s.board, name_cell("d4"), BLACK),
      "the Black Soldier on e5 attacks d4, the hex about to be skipped")
s = GAME.apply_move(s, mv("e3", "c5"))          # e3 -> d4 -> c5, both vacant
check(s.board[name_cell("c5")] == (WHITE, "S"),
      "the double-stepping Soldier stands on c5")
check(all(name_cell("c5") in GAME.apply_move(s, m).board
          or m.split(">")[1].startswith("%d,%d" % name_cell("c5"))
          for m in GAME.legal_moves(s)),
      "no en passant: the Soldier on c5 can only be taken ON c5")
check(mv("e5", "d4") in GAME.legal_moves(s),
      "...though the skipped hex is of course still an ordinary destination")

# CHECK DETECTION IS A SEPARATE CODE PATH FROM MOVE GENERATION, and a Soldier
# captures SIDEWAYS as well as forward -- so an enemy Soldier due E or W of a
# royal gives check, and nothing else about that Soldier's geometry does (from
# k5 a Black Soldier's forward hexes are l4 and j4; its other sideways hex is
# m5). Dropping the two sideways directions from `attacked` ALONE breaks no
# move-generation test whatever -- it was a surviving mutant -- because
# `in_check` then goes blind in exactly the same way, so even the "never to
# move with the enemy Monarch en prise" sweep stays silent about it. The Black
# Princess is parked on d8, off every line through i5, so the ONLY threat to
# the Monarch here is the sideways Soldier step.
for foe, side in (("Sk5", "W"), ("Sg5", "E")):
    s = pos("Mi5 Pe1 Hq5", "Me9 Pd8 " + foe)
    check(GAME.attacked(s.board, name_cell("i5"), BLACK),
          f"a Black Soldier on {foe[1:]} attacks i5 by its {side} step")
    check(GAME.in_check(s.board, WHITE), f"...and that IS check ({foe})")
    check(dests(s, "i5") == {"e1", "q5"},
          f"...so the Monarch, being in check, may swap away: {dests(s, 'i5')}")
    check(not GAME.attacked(s.board, name_cell("h6"), BLACK),
          "...and the sideways threat is a threat to that one hex")
s = pos("Mi5 Pe1 Hq5", "Me9 Pd8 Sh4")
check(not GAME.attacked(s.board, name_cell("i5"), BLACK)
      and not GAME.in_check(s.board, WHITE),
      "a Black Soldier on h4 does NOT attack i5 -- that would be backwards")
# The same sideways threat, seen through the swap rule's use of `attacked`.
s = pos("Mi5 Pe1 Sk3 Sm5", "Me9 Pa5")
check(GAME.in_check(s.board, WHITE), "White is in check from the Princess on a5")
check(not GAME.attacked(s.board, name_cell("m5"), BLACK),
      "m5 is unthreatened (the Princess's line stops at the Monarch)")
check(dests(s, "i5") == {"k3", "m5"},
      f"both Soldiers are legal swap partners: {dests(s, 'i5')}")
s = pos("Mi5 Pe1 Sk3 Sm5", "Me9 Pa5 So5")
check(GAME.attacked(s.board, name_cell("m5"), BLACK),
      "...but a Black Soldier on o5 threatens m5 by its W step")
check(dests(s, "i5") == {"k3"}, "so m5 is no longer a legal swap partner")

# --------------------------------------------------------------------------
# 6. Horseman
# --------------------------------------------------------------------------
s = pos(ROYALS_W + " Hi5", ROYALS_B)
TWELVE = {"g7", "k7", "m5", "k3", "g3", "e5", "i7", "l6", "l4", "i3", "f4", "f6"}
check(dests(s, "i5") == TWELVE, "Horseman: exactly the 12 cells at distance 2")
check(dests(s, "i5").isdisjoint({"h6", "j6", "k5", "j4", "h4", "g5", "i5"}),
      "Horseman may not stop on its own hex or an adjacent one")
# ...ignoring any intervening piece: ring the Horseman with pieces, same 12.
s = pos(ROYALS_W + " Hi5 Sh6 Sj6 Sk5 Sj4", ROYALS_B + " Sh4 Sg5")
check(dests(s, "i5") == TWELVE, "Horseman leaps over a full ring of pieces")
s = pos(ROYALS_W + " Hi5 Sg7", ROYALS_B + " Sk7")
check("g7" not in dests(s, "i5") and "k7" in dests(s, "i5"),
      "Horseman: blocked by a friend on the target, captures an enemy there")

# --------------------------------------------------------------------------
# 7. Gunne -- the hopper, and its shoot
# --------------------------------------------------------------------------
s = pos(ROYALS_W + " Ge5", ROYALS_B + " Sm5")
check("m5" not in dests(s, "e5") and "m5*" not in dests(s, "e5"),
      "Gunne: no capture without a screen")
s = pos(ROYALS_W + " Ge5", ROYALS_B + " Si5 Sm5")
check({"m5", "m5*"} <= dests(s, "e5"),
      "Gunne: one screen (i5) -> may capture m5 by moving in OR by shooting")
check("i5" not in dests(s, "e5"), "Gunne never captures the screen itself")
s = pos(ROYALS_W + " Ge5", ROYALS_B + " Sg5 Si5 Sm5")
check(dests(s, "e5").isdisjoint({"m5", "m5*"}),
      "Gunne: two pieces in the line -> the landing hex is i5, not m5")
check(dests(s, "e5").isdisjoint({"g5", "g5*"}),
      "Gunne cannot capture an adjacent enemy (its step does not capture)")
check({"i5", "i5*"} <= dests(s, "e5"),
      "...but it CAN hop g5 and take i5, the next piece in the line")
s = pos(ROYALS_W + " Ge5 Sm5", ROYALS_B + " Si5")
check(dests(s, "e5").isdisjoint({"m5", "m5*"}),
      "Gunne: the landing piece must be an ENEMY")
s = pos(ROYALS_W + " Ge5", ROYALS_B + " Sf6")
check("f6" not in dests(s, "e5"), "a Gunne may not step onto an enemy")
check("f4" in dests(s, "e5"), "...but steps freely onto an empty neighbour")

# The shoot removes the victim and leaves the Gunne where it stood.
s = pos(ROYALS_W + " Ge5", ROYALS_B + " Si5 Sm5")
shot = GAME.apply_move(s, mv("e5", "m5", True))
check(shot.board.get(name_cell("e5")) == (WHITE, "G")
      and name_cell("m5") not in shot.board
      and shot.board.get(name_cell("i5")) == (BLACK, "S"),
      "SHOOT: victim removed, Gunne and screen unmoved")
moved = GAME.apply_move(s, mv("e5", "m5"))
check(moved.board.get(name_cell("m5")) == (WHITE, "G")
      and name_cell("e5") not in moved.board,
      "capture by moving in: the Gunne ends on the victim's hex")
check(GAME.describe_move(s, mv("e5", "m5", True)) == "Ge5*m5"
      and GAME.describe_move(s, mv("e5", "m5")) == "Ge5xm5",
      "the move log tells a shot from a capture by moving")

# --------------------------------------------------------------------------
# 8. Princess -- the rider, and loss on capture
# --------------------------------------------------------------------------
s = pos("Mm1 Pi5", "Me9 Pm9")
check(dests(s, "i5") == {
    "h6", "g7", "f8",                      # NW: stops SHORT of Black's Monarch
    "j6", "k7", "l8", "m9",                # NE: takes the enemy Princess
    "k5", "m5", "o5", "q5",                # E
    "j4", "k3", "l2",                      # SE: blocked by her own Monarch
    "h4", "g3", "f2", "e1",                # SW
    "g5", "e5", "c5", "a5"},               # W
    f"Princess: 22 cells along the six lines: {dests(s, 'i5')}")
check("m9" in dests(s, "i5") and "e9" not in dests(s, "i5"),
      "she captures the enemy Princess but never the enemy Monarch")

# The Monarch may NOT be captured: he is protected by the check rules, so no
# move is ever generated onto his hex.
s = pos("Mm1 Pi5", "Me9 Pa5")
check("e9" not in dests(s, "i5"), "a Princess never captures the enemy Monarch")
check(GAME.attacked(s.board, name_cell("e9"), WHITE) and GAME.in_check(s.board, BLACK),
      "...though he IS 'attacked' -- that is exactly what check means")
s = pos("Mm1 Pe1 Hi5", "Mk7 Pa5")
check("k7" not in dests(s, "i5") and len(dests(s, "i5")) == 11,
      "a Horseman never captures the enemy Monarch (11 of its 12 targets)")
check(GAME.attacked(s.board, name_cell("k7"), WHITE) and GAME.in_check(s.board, BLACK),
      "...he is in check from the leap")
s = pos("Mm1 Pe1 Ge5", "Mm5 Pa5 Si5")
check(dests(s, "e5").isdisjoint({"m5", "m5*"}),
      "a Gunne neither captures NOR SHOOTS the enemy Monarch")
check(GAME.in_check(s.board, BLACK), "...he is in check from the hop")

# Capturing the Princess ends the game at once (reached through apply_move).
s = pos("Mm1 Pi5", "Mi9 Pg7")
end = GAME.apply_move(s, mv("i5", "g7"))
check(GAME.is_terminal(end) and GAME.returns(end) == [1.0, -1.0]
      and GAME.legal_moves(end) == [] and GAME.loser(end) == BLACK,
      "Princess captured -> immediate loss for her owner")
check("Princess captured" in GAME.render(end)["caption"], "caption says why")
check(GAME.describe_move(s, mv("i5", "g7")) == "Pi5xg7#", "…and the log says so")
# It is NOT illegal to leave the Princess vulnerable ("if you snooze, you lose"):
# with his Princess attacked, White may quietly push a Soldier instead.
s = pos("Mm1 Pi5 Sm3", "Me9 Pa5")
check(GAME.attacked(s.board, name_cell("i5"), BLACK)
      and not GAME.in_check(s.board, WHITE),
      "the White Princess is en prise, and that is not check")
check(mv("m3", "n4") in GAME.legal_moves(s),
      "leaving the Princess to be captured is NOT illegal")

# --------------------------------------------------------------------------
# 9. Monarch -- the swap, and checkmate
# --------------------------------------------------------------------------
s = pos("Mi5 Pq5 Sg5", "Me9 Pb4")
check(not GAME.in_check(s.board, WHITE), "White is not in check here")
check(dests(s, "i5") == set(), "the Monarch may not move while not in check")
check(GAME.legal_moves(s), "...but the position is not stuck: others may move")
# Two Monarchs side by side: neither is in check, because a Monarch has no
# capturing move and therefore threatens nothing.
s = pos("Mi5 Pe1", "Mj6 Pm9")
check(not GAME.in_check(s.board, WHITE) and not GAME.in_check(s.board, BLACK),
      "a Monarch attacks nothing -- two Monarchs may stand adjacent")

# In check from a Princess down the rank: swap with an unthreatened friend.
s = pos("Mi5 Pe1 Sg7 Sk3", "Pa5 Me9")
check(GAME.in_check(s.board, WHITE), "White's Monarch is in check from a5")
check(dests(s, "i5") == {"g7", "k3"},
      f"the Monarch swaps with either unthreatened friend: {dests(s, 'i5')}")
check(GAME.attacked(s.board, name_cell("e1"), BLACK),
      "the Princess on e1 IS threatened, which is why she is not a partner")
sw = GAME.apply_move(s, mv("i5", "k3"))
check(sw.board[name_cell("k3")] == (WHITE, "M")
      and sw.board[name_cell("i5")] == (WHITE, "S")
      and not GAME.in_check(sw.board, WHITE),
      "the swap exchanges the two pieces and ends the check")
# A friend that is ITSELF threatened is not a legal swap partner, even though
# swapping there WOULD take the Monarch out of check.
s = pos("Mi5 Pe1 Sg7 Sk3", "Pa5 Me9 Hk5")
check(GAME.attacked(s.board, name_cell("k3"), BLACK),
      "k3 is threatened by the Horseman on k5")
check(dests(s, "i5") == {"g7"}, "no swap with a threatened friend")

# "…swap positions with another friendly piece NOT SO THREATENED" and the
# orthodox "you may not leave your own royal in check" are PROVABLY THE SAME
# condition here: a swap leaves every cell of the board occupied exactly as it
# was, and enemy attacks depend only on occupancy plus the ENEMY's own pieces,
# so the enemy's attack set is identical before and after. Both are enforced;
# this sweeps random positions to show they never disagree.
rng = random.Random(5)
pairs_tested = 0
for seed in range(6):
    st = GAME.initial_state()
    for _ in range(40):
        if GAME.is_terminal(st):
            break
        st = GAME.apply_move(st, rng.choice(GAME.legal_moves(st)))
        me = st.to_move
        king = GAME.monarch_cell(st.board, me)
        for c, (o, t) in st.board.items():
            if o != me or t == "M":
                continue
            swapped = GAME.apply_to_board(st.board, king, c, "SWAP")
            check(GAME.attacked(st.board, c, 1 - me)
                  == GAME.in_check(swapped, me),
                  "'friend not threatened' == 'Monarch safe after the swap'")
            pairs_tested += 1
check(pairs_tested > 1000, f"swept {pairs_tested} Monarch/partner pairs")

# Reach a real checkmate by random play rather than by construction.
mate = None
for seed in range(400):
    rng = random.Random(seed)
    st = GAME.initial_state()
    while not GAME.is_terminal(st):
        st = GAME.apply_move(st, rng.choice(GAME.legal_moves(st)))
    if GAME.loser(st) is not None and \
            GAME.princess_cell(st.board, GAME.loser(st)) is not None:
        mate = st
        break
check(mate is not None, "a checkmate is reachable by random play")
check(GAME.in_check(mate.board, mate.to_move) and GAME._legal(mate) == []
      and GAME.returns(mate) in ([1.0, -1.0], [-1.0, 1.0]),
      "checkmate: in check, no legal move, decisive result")
check("checkmated" in GAME.render(mate)["caption"], "caption says checkmate")

# Stalemate. The author writes that "stalemate is impossible"; it is not, and a
# fabricated result would be a bug, so it is scored as an honest DRAW. White,
# to move, has nine pieces and not one legal move: five Soldiers walled along
# the top rank (a Soldier there has only its E/W neighbours, both friendly),
# the Princess boxed by them and by the Monarch, and the Monarch immobile
# because he is NOT in check.
stale = pos("Se9 Sg9 Sk9 Sm9 Pi9 Mj8 Sh8 Sf8 Sd8", "Me1 Pm1", to_move=WHITE)
check(GAME.legal_moves(stale) == [] and not GAME.in_check(stale.board, WHITE),
      "constructed stalemate: no legal move, not in check")
check(GAME.is_terminal(stale) and GAME.returns(stale) == [0.0, 0.0]
      and GAME.loser(stale) is None,
      "stalemate is an honest DRAW, not a win for either side")
check("stalemate" in GAME.render(stale)["caption"], "caption says stalemate")
check(len(GAME.legal_moves(replace(stale, to_move=BLACK))) == 14,
      "...and the same position is perfectly live for Black")

# --------------------------------------------------------------------------
# 10. A DECISIVE RESULT OUTRANKS EVERY DRAW COUNTER
# --------------------------------------------------------------------------
# Nine independent instances of the opposite bug have shipped in this library:
# the counter is consulted BEFORE the loss check, so a win delivered on the
# 100th reversible ply, in a thrice-repeated position, or at the ply cap scores
# 0-0. Panal has TWO decisive events; both are tested, against all three
# counters, on the SAME position that was decisive without them.
poison = {GAME.poskey(mate.board, mate.to_move): 9}
for label, decisive in (("checkmate", mate), ("princess capture", end)):
    base = GAME.returns(decisive)
    check(base in ([1.0, -1.0], [-1.0, 1.0]), f"{label} is decisive to begin with")
    for what, tripped in (
            ("50-move", replace(decisive, halfmove=100)),
            ("ply cap", replace(decisive, ply=10 ** 9)),
            ("threefold", replace(decisive, reps=dict(poison))),
            ("all three", replace(decisive, halfmove=500, ply=10 ** 9,
                                  reps=dict(poison)))):
        check(GAME.returns(tripped) == base
              and GAME.is_terminal(tripped)
              and GAME.legal_moves(tripped) == []
              and GAME._draw_reason(tripped) is None,
              f"{label} survives a tripped {what} counter")

# --------------------------------------------------------------------------
# 11. The draw counters themselves (they must WORK, just not outrank a result)
# --------------------------------------------------------------------------
live = pos(ROYALS_W + " Hf4", ROYALS_B + " Hl6")
check(not GAME.is_terminal(live), "the shuffling position is live")
check(GAME.is_terminal(replace(live, halfmove=100))
      and GAME._draw_reason(replace(live, halfmove=100)) == "50-move rule"
      and GAME.returns(replace(live, halfmove=100)) == [0.0, 0.0],
      "100 reversible plies -> drawn")
check(not GAME.is_terminal(replace(live, halfmove=99)),
      "...but not at 99 (the boundary bites)")

# Threefold, reached by actually repeating: two Horsemen shuffle A-B-A-B.
s = live
for m in [mv("f4", "f6"), mv("l6", "l4"), mv("f6", "f4"), mv("l4", "l6")] * 2:
    check(not GAME.is_terminal(s), "shuffle stays live until the third repeat")
    s = GAME.apply_move(s, m)
check(GAME._draw_reason(s) == "threefold repetition"
      and GAME.returns(s) == [0.0, 0.0] and GAME.legal_moves(s) == [],
      "the same position three times -> drawn")
check(s.halfmove == 8, "a Horseman shuffle is reversible (halfmove kept counting)")
# A repetition is only a repetition WITH THE SAME SIDE TO MOVE, so the key must
# carry it -- otherwise one player's two visits plus the other's one count as a
# threefold and manufacture a draw out of a live position.
b0 = GAME.initial_state().board
check(GAME.poskey(b0, WHITE) != GAME.poskey(b0, BLACK),
      "the repetition key distinguishes the side to move")

# The ply cap. PLY_CAP is read as `self.PLY_CAP`, so patch the INSTANCE (the
# module constant would be a different object under `load_from_dir`'s synthetic
# module name) and prove the patch BITES before trusting the test.
check(GAME.PLY_CAP == 8500 and G.PLY_CAP == 8500, "PLY_CAP is 8500")
far = replace(live, ply=8499)
check(not GAME.is_terminal(far), "ply 8499 is live under the real cap")
try:
    GAME.PLY_CAP = 4
    check(GAME._draw_reason(replace(live, ply=5)) == "move limit"
          and GAME.is_terminal(replace(live, ply=5)),
          "an absurdly low cap DOES fire -> the cap is really consulted")
    check(GAME._draw_reason(replace(live, ply=3)) is None,
          "...and not below it")
finally:
    del GAME.PLY_CAP
check(GAME.PLY_CAP == 8500 and not GAME.is_terminal(far), "cap restored")

# Progress accounting: a capture and a FORWARD Soldier move reset the counter;
# a SIDEWAYS Soldier step does not (it is reversible, and the PLY_CAP bound is
# derived from that).
s = pos(ROYALS_W + " Si5", ROYALS_B, halfmove=17)
check(GAME.apply_move(s, mv("i5", "h6")).halfmove == 0, "forward Soldier resets")
check(GAME.apply_move(s, mv("i5", "k7")).halfmove == 0, "double step resets")
check(GAME.apply_move(s, mv("i5", "k5")).halfmove == 18,
      "a SIDEWAYS Soldier step does not reset (it is reversible)")
# ...and the SAME for Black, whose forward is the other way down the ranks. A
# non-colour-aware forward test ("r decreased") survives every White-only
# check and then never resets for Black at all, so the 50-move rule fires on a
# side that is making steady progress.
s = pos(ROYALS_W, ROYALS_B + " Si5", to_move=BLACK, halfmove=17)
check(GAME.apply_move(s, mv("i5", "h4")).halfmove == 0,
      "a BLACK forward Soldier move resets too")
check(GAME.apply_move(s, mv("i5", "g3")).halfmove == 0,
      "...and so does its double step")
check(GAME.apply_move(s, mv("i5", "k5")).halfmove == 18,
      "...while a Black SIDEWAYS step does not")
s = pos(ROYALS_W + " Hi5", ROYALS_B + " Sg7", halfmove=17)
check(GAME.apply_move(s, mv("i5", "g7")).halfmove == 0, "a capture resets")
check(GAME.apply_move(s, mv("i5", "l4")).halfmove == 18, "a quiet move does not")
s = pos(ROYALS_W + " Ge5", ROYALS_B + " Si5 Sm5", halfmove=17)
check(GAME.apply_move(s, mv("e5", "m5", True)).halfmove == 0, "a SHOOT resets")
# A swap lands on an OCCUPIED hex but captures nothing, and is reversible.
s = pos("Mi5 Pe1 Sg7 Sk3", "Pa5 Me9", halfmove=17)
sw = GAME.apply_move(s, mv("i5", "g7"))
check(sw.halfmove == 18 and len(sw.board) == len(s.board) and sw.reps,
      "a Monarch swap is not a capture: no reset, no piece lost")

# --------------------------------------------------------------------------
# 12. Serialisation -- compare STATES, not their JSON
# --------------------------------------------------------------------------
# `assert serialize(deserialize(d)) == d` is VACUOUS: a field `serialize` stops
# emitting re-defaults on the way in and is re-omitted on the way out. Three
# packages in one recent wave shipped exactly that bug, and the failure is
# invisible locally (hotseat and vs-bot keep state in memory) while an async
# match, which reloads from the DB every turn, silently breaks.
KEYS = {"board", "to_move", "halfmove", "ply", "reps", "last"}
rng = random.Random(11)
s = GAME.initial_state()
seen_last = False
while True:
    d = GAME.serialize(s)
    check(set(d) == KEYS, "serialize emits exactly the state's fields")
    check(json.loads(json.dumps(d)) == d, "serialize is JSON-able")
    check(GAME.deserialize(json.loads(json.dumps(d))) == s,
          "deserialize(serialize(s)) == s  (STATE equality, not JSON equality)")
    seen_last = seen_last or s.last is not None
    if GAME.is_terminal(s):
        break
    s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
check(seen_last and s.ply > 10 and s.reps,
      "the round-trip swept a whole game, incl. non-empty last/reps")

# --------------------------------------------------------------------------
# 13. Engine contract: purity, termination, render bounds
# --------------------------------------------------------------------------
s = GAME.initial_state()
before = GAME.serialize(s)
GAME.apply_move(s, GAME.legal_moves(s)[0])
check(GAME.serialize(s) == before, "apply_move does not mutate its input")

DECL = {f"{q},{r}" for q in range(-4, 5) for r in range(-4, 5)
        if abs(q + r) <= 4}          # what Board.jsx builds from size=5
maxply = 0
for seed in range(60):
    rng = random.Random(1000 + seed)
    s = GAME.initial_state()
    while not GAME.is_terminal(s):
        moves = GAME.legal_moves(s)
        check(moves and len(set(moves)) == len(moves),
              "non-empty, duplicate-free legal_moves on a live position")
        # The opponent's Monarch is NEVER attacked at the start of a turn --
        # which is why excluding him from capture generation is inert.
        check(not GAME.in_check(s.board, 1 - s.to_move),
              "you can never be to move with the enemy Monarch en prise")
        check(len(GAME.serialize(s)["board"]) == len(s.board), "board intact")
        s = GAME.apply_move(s, rng.choice(moves))
    maxply = max(maxply, s.ply)
    spec = GAME.render(s)
    check({p["cell"] for p in spec["pieces"]} <= DECL,
          "every rendered piece lies inside the declared board")
    check(set(spec["board"]["tints"]) <= DECL and set(spec["board"]["labels"]) <= DECL,
          "tints and labels lie inside the declared board")
    check(GAME.returns(s) in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0]),
          "well-formed returns at a terminal")
check(maxply < 400, f"random games terminate quickly (longest {maxply} plies)")
spec = GAME.render(GAME.initial_state())
check({p["cell"] for p in spec["pieces"]} <= DECL and len(spec["pieces"]) == 26,
      "the opening render is inside the board")
check(spec["board"]["size"] == 5 and spec["board"]["type"] == "hex"
      and "orientation" not in spec["board"],
      "hexhex size 5, pointy-top (the default): ranks are horizontal rows")

# --------------------------------------------------------------------------
# 14. The MCTS heuristic must be a LIST of per-seat payoffs
# --------------------------------------------------------------------------
h = GAME.heuristic(GAME.initial_state())
check(isinstance(h, list) and len(h) == 2 and abs(h[0]) < 1e-9 and h[1] == -h[0],
      "heuristic: a list of 2 payoffs, symmetric position -> 0")
s = pos(ROYALS_W + " He5 Hg5", ROYALS_B)
check(GAME.heuristic(s)[0] > 0 > GAME.heuristic(s)[1], "more material -> better")
from agp.mcts import MCTSBot                                     # noqa: E402
# max_rollout=4 FORCES the rollout cutoff, which is the only place the
# heuristic is used (a game shorter than the cutoff hides a malformed one).
pick = MCTSBot(random.Random(3), iterations=30, max_rollout=4).select(
    GAME, GAME.initial_state())
check(pick in GAME.legal_moves(GAME.initial_state()),
      "MCTS with a forced rollout cutoff picks a legal move")

print(f"panal selftest: {ok} checks passed")
