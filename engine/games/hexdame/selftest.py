#!/usr/bin/env python3
"""Standalone correctness self-test for HexDame (pure stdlib).

Run from engine/ with:  PYTHONPATH=. python3 games/hexdame/selftest.py

Anchors:
  1. Exact initial setup from the mindsports.nl diagram (61 cells, 16+16 men
     in 4x4 corner rhombi, a1/i9 corners occupied) and opening mobility 15
     (hand-derived: men on files d / rank 4 only; d4 has 3 moves, the other
     six 2 each). perft(2)=211 / perft(3)=3337 are frozen self-derived
     regression values (211 = 15*15 - 14: only 1.d4-e5 forces a lone reply).
  2. Man movement directions for both colours (3 forward moves; e5 -> f5/e6/f6
     for White, d5/e4/d4 for Black).
  3. Majority (maximum) capture: a 2-man chain outranks a single capture even
     when the single capture takes a KING (a king counts as one piece); the
     shorter option is pruned. Includes a backward man capture.
  4. Flying king: 16 slide moves from e1 on an open board; long-range capture
     with free landing choice; and a continuation that outranks stopping.
  5. Promotion: the back rank is exactly 9 cells per side (file i + rank 9 /
     file a + rank 1); a man promotes by ENDING a move or capture there but
     NOT by passing through mid-capture.
  6. Full replay of the published game fragment Kok-Goverde (Abstract Games
     issue 8, p.21, Winter 2001): 17 half-moves, every one asserted legal
     under compulsory maximal capture, final position checked.
  7. 200 random playouts terminate with well-formed returns; serialize
     round-trip; describe_move notation; heuristic shape (per-seat payoffs)
     including an MCTSBot rollout-cutoff probe.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import random
import sys

from games.hexdame.game import HexDame, HexDameState, _promotes

G = HexDame()
FILES = "abcdefghi"


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def cell(n):
    """Traditional notation 'c5' -> axial (q, y)."""
    f = FILES.index(n[0]) + 1
    r = int(n[1])
    return (r - 5, 5 - f)


def cid(n):
    q, y = cell(n)
    return f"{q},{y}"


def path(*names):
    return ">".join(cid(n) for n in names)


def state(white, black, to_move=0, kings=()):
    board = {}
    for n in white:
        board[cell(n)] = (0, "k" if n in kings else "m")
    for n in black:
        board[cell(n)] = (1, "k" if n in kings else "m")
    return HexDameState(board=board, to_move=to_move)


def perft(st, d):
    if d == 0:
        return 1
    return sum(perft(G.apply_move(st, m), d - 1) for m in G.legal_moves(st))


# ---------------------------------------------------------------------------
# 1. Initial setup + opening perft
# ---------------------------------------------------------------------------
init = G.initial_state()
cells = [(q, y) for q in range(-4, 5) for y in range(-4, 5) if abs(q + y) <= 4]
if len(cells) != 61:
    fail(f"board has {len(cells)} cells, expected 61")
white = {G._notation(c) for c, (p, k) in init.board.items() if p == 0}
black = {G._notation(c) for c, (p, k) in init.board.items() if p == 1}
exp_white = {f"{FILES[f-1]}{r}" for f in range(1, 5) for r in range(1, 5)}
exp_black = {f"{FILES[f-1]}{r}" for f in range(6, 10) for r in range(6, 10)}
if white != exp_white:
    fail(f"White setup {sorted(white)} != files a-d x ranks 1-4")
if black != exp_black:
    fail(f"Black setup {sorted(black)} != files f-i x ranks 6-9")
if "a1" not in white or "i9" not in black:
    fail("corner cells a1/i9 must be occupied in the opening")
if any(k != "m" for (p, k) in init.board.values()):
    fail("opening must be all men")
for d, expected in {1: 15, 2: 211, 3: 3337}.items():
    got = perft(init, d)
    if got != expected:
        fail(f"perft({d}) = {got}, expected {expected}")
print("setup + perft(1..3) = 15/211/3337  OK")

# ---------------------------------------------------------------------------
# 2. Man movement directions
# ---------------------------------------------------------------------------
s = state(["e5"], ["i9"])
if {m.split(">")[1] for m in G.legal_moves(s)} != {cid("f5"), cid("e6"), cid("f6")}:
    fail("White man on e5 must move to exactly f5/e6/f6")
s = state(["a1"], ["e5"], to_move=1)
if {m.split(">")[1] for m in G.legal_moves(s)} != {cid("d5"), cid("e4"), cid("d4")}:
    fail("Black man on e5 must move to exactly d5/e4/d4")
print("man movement directions  OK")

# ---------------------------------------------------------------------------
# 3. Majority capture (and king counts as one piece; backward man capture)
# ---------------------------------------------------------------------------
# White men e5 and c3. Black men f5, g4 give e5 a 2-chain (e5xg5xg3);
# a black KING on b3 gives c3 a single BACKWARD capture (c3xa3).
# Only the 2-chain may be legal: 2 men outrank 1 king.
s = state(["e5", "c3"], ["f5", "g4", "b3"], kings={"b3"})
if G.legal_moves(s) != [path("e5", "g5", "g3")]:
    fail(f"majority rule: expected only e5xg5xg3, got "
         f"{[G.describe_move(s, m) for m in G.legal_moves(s)]}")
# sanity: without the 2-chain, the single king capture (backward) IS legal
s = state(["c3"], ["b3"], kings={"b3"})
if G.legal_moves(s) != [path("c3", "a3")]:
    fail("backward man capture c3xa3 expected")
after = G.apply_move(s, path("c3", "a3"))
if cell("b3") in after.board:
    fail("captured king must be removed")
print("majority capture + backward capture  OK")

# ---------------------------------------------------------------------------
# 4. Flying king
# ---------------------------------------------------------------------------
s = state(["e1"], ["i9"], kings={"e1"}, to_move=0)
# i9's man cannot be captured (no cell beyond); king slides: 8 on the e-file
# line toward e9, 4 up file a-e line (a1 dir), 4 along the edge toward i5.
slides = {m for m in G.legal_moves(s) if m.startswith(cid("e1"))}
if len(slides) != 16:
    fail(f"flying king on e1 (open board) has {len(slides)} slides, expected 16")
# long capture, free landing: king e1, enemy man e5 -> land e6/e7/e8/e9
s = state(["e1"], ["e5"], kings={"e1"})
exp = {path("e1", n) for n in ("e6", "e7", "e8", "e9")}
if set(G.legal_moves(s)) != exp:
    fail("flying king capture e1xe5 must offer landings e6-e9 only")
# continuation outranks stopping: with a second enemy on f7 every legal move
# is a 2-chain — via e7 (jumping f7 on the file-f... rank-7 line) or via the
# e6 landing (jumping f7 on the oblique line, landing g8/h9); all 1-jump
# stops are pruned.
s = state(["e1"], ["e5", "f7"], kings={"e1"})
exp = {path("e1", "e7", n) for n in ("g7", "h7", "i7")} | \
      {path("e1", "e6", n) for n in ("g8", "h9")}
if set(G.legal_moves(s)) != exp:
    fail(f"king majority: expected e1xe7x(g7|h7|i7), got "
         f"{[G.describe_move(s, m) for m in G.legal_moves(s)]}")
after = G.apply_move(s, path("e1", "e7", "g7"))
if cell("e5") in after.board or cell("f7") in after.board:
    fail("king chain must remove both captured pieces at the end")
if after.board[cell("g7")] != (0, "k"):
    fail("king must stay a king")
# regression: a capture may slide OVER (or end on) the mover's vacated origin
# cell (mindsports: "may end on the square of origin"). The third leg here
# passes straight over e5; all three victims must be removed.
s = state(["e5"], ["f5", "g6", "d4"], kings={"e5"})
exp = {path("e5", "g5", "g7", n) for n in ("c3", "b2", "a1")}
if set(G.legal_moves(s)) != exp:
    fail(f"origin-crossing king chain: expected e5xg5xg7x(c3|b2|a1), got "
         f"{[G.describe_move(s, m) for m in G.legal_moves(s)]}")
after = G.apply_move(s, path("e5", "g5", "g7", "c3"))
if any(p == 1 for (p, k) in after.board.values()):
    fail("origin-crossing chain must capture all three pieces "
         f"(left: {sorted(G._notation(c) for c, v in after.board.items() if v[0] == 1)})")
print("flying king  OK")

# ---------------------------------------------------------------------------
# 5. Promotion: 9-cell back rank; only when ENDING there
# ---------------------------------------------------------------------------
w_promo = {G._notation(c) for c in cells if _promotes(0, c)}
b_promo = {G._notation(c) for c in cells if _promotes(1, c)}
if w_promo != {"i5", "i6", "i7", "i8", "i9", "e9", "f9", "g9", "h9"}:
    fail(f"White promotion cells wrong: {sorted(w_promo)}")
if b_promo != {"a1", "a2", "a3", "a4", "a5", "b1", "c1", "d1", "e1"}:
    fail(f"Black promotion cells wrong: {sorted(b_promo)}")
# quiet move onto the back rank promotes
s = state(["h5"], ["a5"])
after = G.apply_move(s, path("h5", "i5"))
if after.board[cell("i5")] != (0, "k"):
    fail("man ending a quiet move on i5 must promote")
# capture ENDING on the back rank promotes
s = state(["g5"], ["h5", "a5"])
if G.legal_moves(s) != [path("g5", "i5")]:
    fail("compulsory capture g5xi5 expected")
after = G.apply_move(s, path("g5", "i5"))
if after.board[cell("i5")] != (0, "k"):
    fail("man ENDING a capture on i5 must promote")
# passing over the back rank mid-capture does NOT promote
s = state(["g5"], ["h5", "h4", "a5"])
if G.legal_moves(s) != [path("g5", "i5", "g3")]:
    fail(f"maximal chain g5xi5xg3 expected, got "
         f"{[G.describe_move(s, m) for m in G.legal_moves(s)]}")
after = G.apply_move(s, path("g5", "i5", "g3"))
if after.board[cell("g3")] != (0, "m"):
    fail("man passing over i5 mid-capture must NOT promote")
print("promotion (9-cell back rank, end-of-move only)  OK")

# ---------------------------------------------------------------------------
# 6. Published game replay: Kok-Goverde, Abstract Games #8 p.21 (2001)
# ---------------------------------------------------------------------------
s = state(
    white=["a5", "c3", "c4", "c5", "d3", "d4", "d5", "e1", "e3", "f2", "g3"],
    black=["d8", "e7", "f7", "g6", "g7", "g8", "g9", "h4", "h5", "h8", "i5"],
)
kok = [
    ["c5", "d6"], ["e7", "c5", "e5"],          # 1. c5d6!  e7:c5:e5
    ["d4", "f6", "h6"], ["h5", "h7"],          # 2. d4:f6:h6  h5:h7
    ["e3", "f4"], ["h7", "h6"],                # 3. e3f4  h7h6
    ["f4", "g4"], ["h4", "f4"],                # 4. f4g4  h4:f4
    ["g3", "h4"], ["i5", "g3"],                # 5. g3h4  i5:g3
    ["f2", "h4"], ["h6", "h5"],                # 6. f2:h4  h6h5!
    ["h4", "h6"], ["g7", "g6"],                # 7. h4:h6  g7g6
    ["h6", "f6", "f8"], ["g9", "e7"],          # 8. h6:f6:f8  g9:e7
    ["e1", "f2"],                              # 9. e1f2!
]
for i, p in enumerate(kok):
    mv = path(*p)
    if mv not in G.legal_moves(s):
        fail(f"Kok replay: half-move {i+1} {'x'.join(p)} not legal; legal = "
             f"{[G.describe_move(s, m) for m in G.legal_moves(s)]}")
    s = G.apply_move(s, mv)
w_end = {G._notation(c) for c, (p, k) in s.board.items() if p == 0}
b_end = {G._notation(c) for c, (p, k) in s.board.items() if p == 1}
if w_end != {"a5", "c3", "c4", "d3", "f2"}:
    fail(f"Kok replay: White end position wrong: {sorted(w_end)}")
if b_end != {"d8", "e7", "f4", "g8", "h8"}:
    fail(f"Kok replay: Black end position wrong: {sorted(b_end)}")
if any(k != "m" for (p, k) in s.board.values()):
    fail("Kok replay: no piece should have promoted")
print("Kok-Goverde published combination (17 half-moves)  OK")

# ---------------------------------------------------------------------------
# 7. Termination, serialization, notation, heuristic
# ---------------------------------------------------------------------------
d = G.serialize(init)
if G.serialize(G.deserialize(d)) != d:
    fail("serialize does not round-trip")
s = G.initial_state()
if G.describe_move(s, path("d4", "e5")) != "d4-e5":
    fail("describe_move quiet notation")
ks = state(["e1"], ["e5"], kings={"e1"})
if G.describe_move(ks, path("e1", "e7")) != "e1xe7":
    fail("describe_move capture notation")
h = G.heuristic(init)
if not (isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9):
    fail(f"heuristic must be a zero-sum per-seat list, got {h}")
from agp.mcts import MCTSBot
mv = MCTSBot(random.Random(1), iterations=25, max_rollout=4).select(G, init)
if mv not in G.legal_moves(init):
    fail("MCTSBot (forced rollout cutoff -> heuristic) returned illegal move")

rng = random.Random(20260718)
results = []
for i in range(200):
    s = G.initial_state()
    plies = 0
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        plies += 1
        if plies > 500:
            fail("random playout exceeded 500 plies (ply cap broken?)")
    r = G.returns(s)
    if len(r) != 2 or any(x not in (-1.0, 0.0, 1.0) for x in r):
        fail(f"bad returns {r}")
    results.append(tuple(r))
from collections import Counter
print("200 random playouts terminate  OK", dict(Counter(results)))

print("SELFTEST OK")
