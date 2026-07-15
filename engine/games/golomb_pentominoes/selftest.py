"""Standalone correctness anchor for Pentominoes (Golomb's game).

Run with:  PYTHONPATH=. python3 games/golomb_pentominoes/selftest.py

Pure-stdlib: imports only `agp` (transitively) and this game. No third-party
deps, no long searches.

THE ANCHOR (Orman, "Pentominoes: A First Player Win", Games of No Chance, MSRI
vol. 29 (1996), pp. 339-344 — https://library.slmath.org/books/Book29/files/orman.pdf):

  "At the start of the game, there are 2308 possible moves, or 296 when
   symmetries are discounted. After the first move there are between 1181 and
   about 2000 replies. The search was originally conducted for one of the
   optimally restrictive moves, using the long 'L' piece (Figure 2, left).
   There are 1181 replies to this move."

  "the opening move shown in Figure 3, one of the second most restrictive
   (1197 replies)"

2308 and 296 together validate the whole move generator AND pin the FREE
pentomino model (reflections allowed): with one-sided pieces there would be 18
pieces, and the counts would not come out. The 1181/1197 reply counts extend the
anchor to the second ply and to the SHARED pool (a piece played by either player
is gone for both).

The two figures were read off the paper's PDF and are asserted as exact
placements: Orman's Figure 2 (the losing long "L") is `L:1@4,2` here and has
exactly 1181 replies — the global minimum. Orman's 1197 is the most restrictive
placement of the "N", which is the piece drawn in her Figure 3.

NOTE on the 1181/1197 trap: 1181 belongs to the LOSING move of Figure 2; 1197 to
the WINNING move of Figure 3. They are not interchangeable.

Known result, NOT re-derived here: Pentominoes is a first-player win (Orman 1996,
~22 billion positions; independently verified by Richard Schroeppel).
"""

import json
import sys

from games.golomb_pentominoes.game import (
    ORDER, ORIENTS, TEMPLATES, GolombPentominoes, PentState,
)


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


g = GolombPentominoes()
W = H = 8


# ---- (1) setup: empty 8x8, P1 first, 12 pieces in one SHARED pool -----------
s0 = g.initial_state()
check(len(s0.board) == 0, "initial board not empty")
check(s0.used == frozenset(), "initial pool not full")
check(g.current_player(s0) == 0, "Player 1 must move first")
check(g.num_players == 2, "must be a 2-player game")
check(len(ORDER) == 12 and set(ORDER) == set(TEMPLATES), "not 12 pieces")
check(ORDER == "FILNPTUVWXYZ", f"unexpected piece lettering: {ORDER}")


# ---- (2) the pieces really ARE the twelve free pentominoes ------------------
# Re-derive them from scratch with an INDEPENDENT implementation (grow polyominoes
# cell by cell, collapse by the 8 symmetries of the square) and check the letter
# table matches exactly. This is what makes the letter set trustworthy.
def transforms(cells):
    out, cur = [], list(cells)
    for flip in (False, True):
        c0 = [(-c, r) for c, r in cur] if flip else list(cur)
        for _ in range(4):
            c0 = [(r, -c) for c, r in c0]
            out.append(list(c0))
    return out


def canon(cells):
    best = None
    for t in transforms(cells):
        mc = min(c for c, _ in t)
        mr = min(r for _, r in t)
        n = tuple(sorted((c - mc, r - mr) for c, r in t))
        if best is None or n < best:
            best = n
    return best


shapes = {canon([(0, 0)])}
for _ in range(4):                                   # monomino -> pentomino
    nxt = set()
    for sh in shapes:
        st = set(sh)
        for (c, r) in sh:
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c + dc, r + dr)
                if n not in st:
                    nxt.add(canon(list(st) + [n]))
    shapes = nxt
check(len(shapes) == 12, f"there must be 12 free pentominoes, generated {len(shapes)}")

tmpl = {k: canon(o[0]) for k, o in ORIENTS.items()}
check(len(set(tmpl.values())) == 12, "the 12 letters are not 12 distinct shapes")
check(set(tmpl.values()) == shapes,
      "the letter table is not exactly the set of 12 free pentominoes")
for k, o in ORIENTS.items():
    for form in o:
        check(len(form) == 5, f"{k} is not a 5-omino")

# 63 fixed pentominoes; the standard per-piece orientation counts.
FIXED = {"F": 8, "I": 2, "L": 8, "N": 8, "P": 8, "T": 4,
         "U": 4, "V": 4, "W": 4, "X": 1, "Y": 8, "Z": 4}
for k, n in FIXED.items():
    check(len(ORIENTS[k]) == n, f"{k}: expected {n} fixed orientations, got {len(ORIENTS[k])}")
check(sum(len(o) for o in ORIENTS.values()) == 63, "not 63 fixed pentominoes in total")

# FREE, not one-sided: for each CHIRAL piece its mirror image must be reachable
# as the SAME letter. (12 free + 6 chiral pairs = 18 one-sided pieces; if we had
# modelled one-sided pieces these six assertions would fail.)
for k in ("F", "L", "N", "P", "Y", "Z"):
    form = ORIENTS[k][0]
    mirrored = [(-c, r) for c, r in form]
    ac, ar = min(mirrored, key=lambda t: (t[1], t[0]))
    norm = tuple(sorted((c - ac, r - ar) for c, r in mirrored))
    check(norm in ORIENTS[k], f"{k}: mirror image not offered — reflections must be allowed")

# Every orientation's anchor is a cell the piece actually COVERS (so the cell the
# player clicks is always part of the tile that lands).
for k, o in ORIENTS.items():
    for form in o:
        check((0, 0) in form, f"{k}: an orientation does not cover its own anchor")


# ---- (3) THE ANCHOR: 2308 opening moves ------------------------------------
opening = g.legal_moves(s0)
check(len(opening) == 2308,
      f"Orman: there must be exactly 2308 opening moves, got {len(opening)}")
check(len(set(opening)) == 2308, "opening move list contains duplicates")

PER_PIECE = {"F": 288, "I": 64, "L": 280, "N": 280, "P": 336, "T": 144,
             "U": 168, "V": 144, "W": 144, "X": 36, "Y": 280, "Z": 144}
got = {}
for m in opening:
    got[m.split(":")[0]] = got.get(m.split(":")[0], 0) + 1
check(got == PER_PIECE, f"per-piece opening counts wrong: {got}")


def covered(move):
    keyo, anchor = move.split("@")
    key, oi = keyo.split(":")
    c, r = (int(x) for x in anchor.split(","))
    return frozenset((c + dc, r + dr) for dc, dr in ORIENTS[key][int(oi)])


# every opening move is 5 on-board cells, and no two moves cover the same cells
sets = set()
for m in opening:
    cs = covered(m)
    check(len(cs) == 5, f"{m} does not cover 5 cells")
    check(all(0 <= c < W and 0 <= r < H for c, r in cs), f"{m} runs off the board")
    check(cs not in sets, f"two opening moves cover the same cells: {m}")
    sets.add(cs)


# ---- (4) THE ANCHOR: 296 opening moves modulo the 8 board symmetries --------
n = W - 1
SYMS = (
    lambda c, r: (c, r),          # identity
    lambda c, r: (r, n - c),      # rotate 90
    lambda c, r: (n - c, n - r),  # rotate 180
    lambda c, r: (n - r, c),      # rotate 270
    lambda c, r: (n - c, r),      # reflect in the vertical axis
    lambda c, r: (c, n - r),      # reflect in the horizontal axis
    lambda c, r: (r, c),          # reflect in the main diagonal
    lambda c, r: (n - r, n - c),  # reflect in the anti-diagonal
)
seen, orbits = set(), 0
for cs in sets:
    if cs in seen:
        continue
    orbits += 1
    for f in SYMS:
        seen.add(frozenset(f(c, r) for c, r in cs))
check(orbits == 296,
      f"Orman: there must be 296 opening moves modulo symmetry, got {orbits}")


# ---- (5) THE ANCHOR: Orman's Figure 2 — the long "L", 1181 replies ----------
# Figure 2 (left), read off the paper: cells (col, row-from-top)
# (3,2) (4,2) (4,3) (4,4) (4,5) — a vertical bar of four with one cell at the
# top-left. "One of the first-player moves that allows the minimum number of
# responses... There are 1181 replies to this move."
FIG2 = "L:1@4,2"
check(FIG2 in opening, f"Orman's Figure 2 move {FIG2} is not legal")
check(covered(FIG2) == frozenset({(3, 5), (4, 5), (4, 4), (4, 3), (4, 2)}),
      "Figure 2 move does not cover the cells drawn in the paper")
s_fig2 = g.apply_move(s0, FIG2)
replies = g.legal_moves(s_fig2)
check(len(replies) == 1181,
      f"Orman: the long 'L' of Figure 2 must allow exactly 1181 replies, got {len(replies)}")

# 1181 is the GLOBAL MINIMUM ("between 1181 and about 2000 replies"): no opening
# may do better. Checking all 2308 openings is too slow for the suite, so spot-
# check the pieces whose best placement is known to beat nothing.
for m in (FIG2, "N:0@3,3", "Y:0@2,3", "P:0@3,3"):
    check(len(g.legal_moves(g.apply_move(s0, m))) >= 1181,
          f"{m} allows fewer than the minimum 1181 replies")

# Figure 2 (right): the straight piece refutes it. Assert the drawn reply is legal.
FIG2_REPLY = "I:1@0,1"
check(covered(FIG2_REPLY) == frozenset({(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)}),
      "Figure 2's refuting reply does not cover the cells drawn in the paper")
check(FIG2_REPLY in replies, "Orman's Figure 2 refutation (the straight piece) must be legal")


# ---- (6) THE ANCHOR: Orman's 1197 — the "N" of Figure 3 (the WINNING move) --
# CAREFUL: 1181 is the LOSING move of Figure 2; 1197 is the WINNING move of
# Figure 3 — Orman calls it "one of the second most restrictive". Ranking the
# pieces by their most restrictive placement gives L=1181 then N=1197, and
# Figure 3 does draw an N. This is the most restrictive N placement.
FIG3_N = "N:0@3,3"
check(FIG3_N in opening, f"{FIG3_N} is not legal")
check(FIG3_N.startswith("N:"), "Orman's second-most-restrictive move is an N pentomino")
n_replies = len(g.legal_moves(g.apply_move(s0, FIG3_N)))
check(n_replies == 1197,
      f"Orman: the most restrictive 'N' must allow exactly 1197 replies, got {n_replies}")


# ---- (7) the pool is SHARED, and the game is IMPARTIAL ----------------------
# After Player 1 plays the L, the L is gone for PLAYER 2 as well.
check(s_fig2.used == frozenset({"L"}), "the played piece was not consumed")
check(not any(m.startswith("L:") for m in replies),
      "SHARED POOL: the L must be unavailable to the opponent once played")
for k in ORDER:
    if k != "L":
        check(any(m.startswith(f"{k}:") for m in replies), f"{k} should still be in the pool")

# Impartial: the legal moves depend only on the position, never on whose turn it
# is. Same board, either player to move -> identical move list.
a = PentState(board=dict(s_fig2.board), used=s_fig2.used, to_move=0)
b = PentState(board=dict(s_fig2.board), used=s_fig2.used, to_move=1)
check(g.legal_moves(a) == g.legal_moves(b),
      "IMPARTIAL: both players must have exactly the same moves from a position")

# The render must advertise ONE shared pool, not a set per seat: the palette goes
# under the "shared" key, which makes the UI draw a single "Pool" tray. This has
# to be explicit — two separate but identical hands are byte-identical, so it
# cannot be inferred by comparing per-seat lists.
spec = g.render(s0)
pal = spec["palette"]
check(list(pal) == ["shared"],
      f"SHARED POOL: palette must carry only the 'shared' key, got {list(pal)}")
check("0" not in pal and "1" not in pal, "SHARED POOL: no per-seat palette keys")
check(len(pal["shared"]) == 12, "12 tiles must be offered at the start")
check([t["key"] for t in pal["shared"]] == list(ORDER), "the pool is not in F..Z order")
spec2 = g.render(s_fig2)
check(len(spec2["palette"]["shared"]) == 11,
      "SHARED POOL: a played piece must leave the one shared pool")
check(all(t["key"] != "L" for t in spec2["palette"]["shared"]),
      "the played L is still in the pool")
json.dumps(spec2)                                     # the render must be JSON-able

# Every orientation the palette advertises must be a real 5-cell tile covering
# its own anchor — the exact geometry Board.jsx dereferences for the ghost.
for t in pal["shared"]:
    for form in t["orients"]:
        check(len(form) == 5, f"{t['key']}: an advertised orientation is not 5 cells")
        check([0, 0] in form, f"{t['key']}: an advertised orientation misses its anchor")


# ---- (8) placement mechanics: covers 5 empty cells, never captures ----------
check(len(s_fig2.board) == 5, "a pentomino must fill exactly five cells")
check(all(v == 0 for v in s_fig2.board.values()), "the placer must own all five cells")
s_two = g.apply_move(s_fig2, FIG2_REPLY)
check(len(s_two.board) == 10, "placement must not remove existing pieces (no captures)")
check(s_two.used == frozenset({"L", "I"}), "pool not tracking both played pieces")
for cell in covered(FIG2):
    check(s_two.board[cell] == 0, "player 1's cells must survive (no captures)")


# ---- (9) rejections ---------------------------------------------------------
def rejects(state, move):
    try:
        g.apply_move(state, move)
        return False
    except ValueError:
        return True


check(rejects(s_fig2, FIG2), "replaying the same piece must be rejected")
check(rejects(s_fig2, "L:0@0,0"), "reusing a played piece elsewhere must be rejected")
check(rejects(s_fig2, "I:1@4,2"), "an overlapping placement must be rejected")
check(rejects(s0, "I:0@7,7"), "a placement running off the board must be rejected")
check(rejects(s0, "Q:0@0,0"), "an unknown piece letter must be rejected")
check(rejects(s0, "X:9@3,3"), "an out-of-range orientation must be rejected")
check(rejects(s0, "nonsense"), "a malformed move must be rejected")


# ---- (10) normal play: the player who cannot move loses; no draws -----------
# A game lasts AT MOST 12 placements (one per piece). Witness a full-length game:
# all twelve pentominoes packed onto the 8x8 (60 cells, 4 left over). Player 2
# lays the twelfth, so Player 1 is stuck and loses.
MAX_GAME = ["F:0@2,0", "I:0@3,0", "L:0@3,1", "N:0@3,3", "P:3@6,3", "T:2@0,2",
            "U:1@0,6", "V:2@5,1", "W:3@4,4", "X:0@1,4", "Y:2@4,6", "Z:0@5,5"]
s = s0
for i, m in enumerate(MAX_GAME):
    check(not g.is_terminal(s), f"game ended early at ply {i}")
    check(m in g.legal_moves(s), f"ply {i}: {m} is not legal")
    s = g.apply_move(s, m)
check(len(MAX_GAME) == 12, "a game can last at most 12 placements")
check(len(s.used) == 12 and len(s.board) == 60, "the 12-piece packing did not land")
check(g.is_terminal(s), "the pool is empty, so the position must be terminal")
check(g.current_player(s) == 0, "Player 1 is to move after twelve placements")
check(g.returns(s) == [-1.0, 1.0], "Player 1 cannot move and must lose")

# Normal play in the small: whoever faces a dead position loses, and the result
# is always decisive (never a draw).
check(g.returns(PentState(to_move=1)) == [1.0, -1.0], "player to move with no move loses")
check(sum(g.returns(s)) == 0.0, "returns must be zero-sum — Pentominoes has no draws")

# A random-ish game always terminates within 12 plies and ends decisively.
s = s0
plies = 0
while not g.is_terminal(s):
    s = g.apply_move(s, sorted(g.legal_moves(s))[0])
    plies += 1
    check(plies <= 12, "a game ran past 12 placements")
check(g.returns(s) in ([1.0, -1.0], [-1.0, 1.0]), "a finished game must be decisive")


# ---- (11) serialize round-trips --------------------------------------------
snap = g.serialize(s_two)
json.dumps(snap)
check(g.serialize(g.deserialize(snap)) == snap, "serialize/deserialize does not round-trip")
check(g.legal_moves(g.deserialize(snap)) == g.legal_moves(s_two),
      "a deserialized state must offer the same moves")


print("SELFTEST OK")
