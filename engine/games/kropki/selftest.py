"""Kropki correctness anchors (pure stdlib; the full oracle differential lives
in _diff_oppai.py and last ran 80 games / 10,731 moves / 0 mismatches vs
oppai-rs).

Positions are written as diagrams in the same convention as the reference
engine's test suite so scenarios stay comparable: lowercase letters = Red
(seat 0), uppercase = Blue (seat 1); letters are placed in alphabetical order
(same letter: uppercase first); '.'/'z'/'Z' = empty. The top diagram row is the
top of the board. Diagrams are replayed through apply_move (with interleaved
passes to fix the seat order), so every position is REACHED, never hand-built.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # -> engine/

from agp.loader import load_from_dir  # noqa: E402
from agp.mcts import MCTSBot  # noqa: E402

G = load_from_dir(Path(__file__).resolve().parent)[1]
RED, BLUE = 0, 1


def play(size, moves, start="empty"):
    """moves = [(seat, "c,r"), ...]; inserts single passes to align seats."""
    s = G.initial_state(options={"size": size, "start": start})
    for seat, mv in moves:
        if G.current_player(s) != seat:
            s = G.apply_move(s, "pass")
        assert mv in G.legal_moves(s), f"{mv} not legal"
        s = G.apply_move(s, mv)
    return s


def diagram(rows):
    """oppai-style diagram -> (size, move list in placement order)."""
    h = len(rows)
    w = len(rows[0])
    pts = []
    for y, row in enumerate(rows):
        assert len(row) == w
        for x, ch in enumerate(row):
            if ch.isalpha() and ch.lower() != "z":
                pts.append((ch, f"{x},{h - 1 - y}"))
    pts.sort(key=lambda p: (p[0].lower(), p[0].islower()))
    return f"{w}x{h}", [(BLUE if ch.isupper() else RED, mv) for ch, mv in pts]


def run(rows, start="empty"):
    size, moves = diagram(rows)
    return play(size, moves, start=start)


def cr(s, x, y_top):
    return f"{x},{s.h - 1 - y_top}"


def dot_dead(s, x, y_top):
    f = s.cells[(y_top + 1) * (s.w + 1) + x + 1]
    assert f & 2, "no dot there"
    return bool(f & 4)


# (a) simple diamond capture: ring of 4 (all-diagonal steps) captures one --
# also proves chains are 8-connected and the interior does not leak diagonally
# (the lone interior cell touches the outside only via diagonals).
s = run([".a.",
         "cBa",
         ".a."])
assert s.scores == [1, 0], s.scores
assert dot_dead(s, 1, 1)
for x, y in ((1, 1), (1, 0), (0, 1), (2, 1), (1, 2)):
    assert cr(s, x, y) not in G.legal_moves(s)

# (b) longer mixed orthogonal+diagonal chain capturing two dots, one empty
# interior cell painted -> (i) painted cells are unplayable forever
s = run([".ac.",
         "aB.a",
         ".aa."])
assert s.scores == [1, 0], s.scores
assert dot_dead(s, 1, 1)
assert cr(s, 2, 1) not in G.legal_moves(s)          # painted empty cell
assert not G.is_terminal(s)

# (c) an OPEN chain (gap in the wall) captures nothing
s = run([".aa.",
         "aBB.",
         ".aa."])
assert s.scores == [0, 0], s.scores
assert not dot_dead(s, 1, 1) and not dot_dead(s, 2, 1)

# big all-diagonal ring with a hole inside (ported from the reference suite:
# a_hole_inside_a_surrounding) -- red captures exactly 1, everything inside is
# dead including the empty hole
s = run(["....c....",
         "...c.c...",
         "..c...c..",
         ".c..a..c.",
         "c..a.a..c",
         ".c..a..c.",
         "..c...c..",
         "...cBc...",
         "....d...."])
assert s.scores == [1, 0], s.scores
assert cr(s, 4, 4) not in G.legal_moves(s)
assert cr(s, 4, 1) not in G.legal_moves(s)

# (j) capture requires an enemy dot: a closed ring around empty space scores
# nothing and the inside stays playable (an empty base / домик)
s = run([".a.",
         "a.a",
         ".a."])
assert s.scores == [0, 0], s.scores
assert cr(s, 1, 1) in G.legal_moves(s)

# (d) ...but an enemy dot placed inside the base is captured on the spot
s2 = G.apply_move(s, cr(s, 1, 1))                    # Blue plays into the base
assert s2.scores == [1, 0], s2.scores
assert dot_dead(s2, 1, 1)
assert cr(s2, 1, 1) not in G.legal_moves(s2)

# own dots may fill one's own base freely (no self-capture)
s3 = play("3x3", [(RED, "1,0"), (RED, "0,1"), (RED, "2,1"), (RED, "1,2"),
                  (RED, "1,1")])
assert s3.scores == [0, 0], s3.scores
assert not dot_dead(s3, 1, 1)

# (e) mover precedence (СКСТ exception): a dot placed in the enemy base that
# simultaneously closes the mover's own ring CAPTURES instead of being captured
s = run([".aB.",
         "aCaB",
         ".aB."])
assert s.scores == [0, 1], s.scores                  # Blue's capture stands
assert dot_dead(s, 2, 1)                             # red dot captured
assert not dot_dead(s, 1, 1)                         # Blue's placed dot lives
# bigger variant (two red dots fall)
s = run([".B..",
         "BaB.",
         "aCaB",
         ".aB."])
assert s.scores == [0, 2], s.scores

# (f) liberation by counter-encirclement: Blue captures Red's centre dot, then
# Red encircles the whole Blue ring -> +4 for Red AND the centre dot is freed
# (Blue's score returns to 0)
s = run(["..c..",
         ".cBc.",
         "cBaBc",
         ".cBc.",
         "..c.."])
assert s.scores == [4, 0], s.scores
assert not dot_dead(s, 2, 2)                         # freed, live again
for x, y in ((2, 1), (1, 2), (3, 2), (2, 3)):
    assert dot_dead(s, x, y)                         # the Blue ring is dead

# (f2) three-level nested encirclement (adversarial-QA pin, oracle-verified):
# ring inside ring inside ring, liberation cascading correctly at each level
_c = [(BLUE, "4,4")]
_r1 = [(RED, m) for m in ("4,5", "3,4", "5,4", "4,3")]
_r2 = [(BLUE, m) for m in ("4,6", "3,5", "2,4", "3,3", "4,2", "5,3", "6,4", "5,5")]
_r3 = [(RED, m) for m in ("4,7", "3,6", "2,5", "1,4", "2,3", "3,2", "4,1", "5,2",
                          "6,3", "7,4", "6,5", "5,6")]
s = play("9x9", _c + _r1)
assert s.scores == [1, 0], s.scores                  # level 1: centre captured
s = play("9x9", _c + _r1 + _r2)
assert s.scores == [0, 4], s.scores                  # level 2: 4 captured, 1 freed
assert not dot_dead(s, 4, 4)                         # centre live again
s = play("9x9", _c + _r1 + _r2 + _r3)
assert s.scores == [9, 0], s.scores                  # level 3: 8+1 captured, 4 freed
assert dot_dead(s, 4, 4)
for x, y in ((4, 5), (3, 4), (5, 4), (4, 3)):
    assert not dot_dead(s, x, y)                     # inner red ring freed

# (f3) one dot closing TWO chains at once (figure-eight) captures both
s = play("7x5", [(BLUE, "1,3"), (BLUE, "3,3"),
                 (RED, "1,4"), (RED, "0,3"), (RED, "1,2"), (RED, "3,4"),
                 (RED, "4,3"), (RED, "3,2"), (RED, "2,3")])
assert s.scores == [2, 0], s.scores
assert dot_dead(s, 1, 1) and dot_dead(s, 3, 1)

# (f4) re-enclosing one's OWN painted area does not re-score the dead dots
# inside (the capture flood is blocked by the capturer's bound chain)
s = play("8x8", [(BLUE, "2,5"),
                 (RED, "2,6"), (RED, "1,5"), (RED, "3,5"), (RED, "2,4"),
                 (RED, "2,7"), (RED, "1,6"), (RED, "0,5"), (RED, "1,4"),
                 (RED, "2,3"), (RED, "3,4"), (RED, "4,5"), (RED, "3,6")])
assert s.scores == [1, 0], s.scores

# (g) the board edge never encloses: a corner dot walled in from the inside is
# NOT captured
s = play("4x4", [(BLUE, "0,3"), (RED, "1,3"), (RED, "0,2"), (RED, "1,2")])
assert s.scores == [0, 0], s.scores
assert not dot_dead(s, 0, 0)

# (h) double-pass ends the game; equal captures is an honest draw
s = G.initial_state(options={"size": "13x13", "start": "empty"})
s = G.apply_move(s, "pass")
assert not G.is_terminal(s)
s = G.apply_move(s, "pass")
assert G.is_terminal(s)
assert G.returns(s) == [0.0, 0.0]

# cross start: 2x2 central block, first mover (Red) on one diagonal, Red to move
s = G.initial_state(options={"size": "20x20", "start": "cross"})
assert G.current_player(s) == RED
r = G.render(s)
owners = {p["cell"]: p["owner"] for p in r["pieces"]}
assert len(owners) == 4
assert owners["9,10"] == owners["10,9"] == RED       # internal (9,9),(10,10)
assert owners["9,9"] == owners["10,10"] == BLUE
assert s.scores == [0, 0]

# serialize round-trip + describe_move
d = G.serialize(s)
s2 = G.deserialize(d)
assert G.serialize(s2) == d
import json  # noqa: E402
json.dumps(d)
assert G.describe_move(s, "pass") == "pass"
assert G.describe_move(s, "3,6") == "d7"

# heuristic returns one payoff per seat and MCTS runs at a forced rollout cutoff
h = G.heuristic(s)
assert isinstance(h, list) and len(h) == 2 and h[0] == -h[1]
bot = MCTSBot(random.Random(1), iterations=25, max_rollout=4)
mv = bot.select(G, G.initial_state(options={"size": "13x13"}))
assert mv in G.legal_moves(G.initial_state(options={"size": "13x13"}))

# termination + well-formed returns under random play (board fills up)
rng = random.Random(42)
s = G.initial_state(options={"size": "8x8", "start": "empty"})
plies = 0
while not G.is_terminal(s):
    moves = G.legal_moves(s)
    assert moves
    s = G.apply_move(s, rng.choice(moves))
    plies += 1
    assert plies <= 3 * 8 * 8
ret = G.returns(s)
assert len(ret) == 2 and all(v in (-1.0, 0.0, 1.0) for v in ret)
assert s.scores[0] >= 0 and s.scores[1] >= 0

print("kropki selftest: all checks passed")
