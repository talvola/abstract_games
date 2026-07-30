#!/usr/bin/env python3
"""Monkey Queen correctness anchors -- pure stdlib, run by tests/test_games.py.

Everything here is checked against the designer's own rule sheet,
https://www.marksteeregames.com/Monkey_Queen_rules.html, including its nine
figures (JPEG images referenced from that page; the piece placements below were
recovered by pixel-sampling each figure's printed grid).

A second, independent anchor lives in the scratch harness `_diff_gameslib.py`
(manual/one-time -- it needs node + the AbstractPlay `gameslib` clone): it
replays random games through both engines and compares the legal-move set as
{(from, to)} algebraic pairs, the whole board, the side to move, terminality and
the winner.  Result at the time of writing: **1400 games, 80 626 positions,
6 433 055 moves compared, driven from BOTH sides, 0 mismatches.**  What follows
re-checks the rules from constructed positions and invariants, without node.

NOTE the coverage gap that makes this file load-bearing: **random play never
reaches a stuck-loss** — 3000/3000 random games end with a killed queen, and an
independent QA census of a further 6000 games (2000 at each starting height,
longest 377 plies) also ended 6000/6000 with a killed queen.  So the "deprive your
opponent of moves" half of the rules is exercised ONLY here, and it is exercised
for **both seats**: hard-coding the winning colour in either the stuck-loss
`returns` or the stuck-loss / killed-queen caption were three SURVIVING mutants
until the both-seat assertions below existed.
"""

import dataclasses
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                              # noqa: E402
from agp.mcts import MCTSBot                                      # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
M = sys.modules[type(G).__module__]          # the LIVE module object
MQState = M.MQState
IV, CG = M.IVORY, M.CIGAR
ALL_CELLS = [(c, r) for c in range(M.SIZE) for r in range(M.SIZE)]

FAILS = []


def ok(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


def mv(frm, to):
    return f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"


# ---------------------------------------------------------------------------
# 1. Setup -- Figure 1
# ---------------------------------------------------------------------------
s0 = G.initial_state()
ok(s0.board == {(6, 0): (IV, 20), (5, 11): (CG, 20)},
   f"Figure 1: ivory 20 on g1 and cigar 20 on f12; got {sorted(s0.board.items())}")
ok(M.alg(6, 0) == "g1" and M.alg(5, 11) == "f12", "algebraic naming g1 / f12")
ok(s0.to_move == IV and s0.ply == 0, "Ivory moves first")
ok(M.START[CG] == M.MonkeyQueen._rot_cell(M.START[IV]),
   "the two starting squares are 180-degree images (what makes the pie swap exact)")
ok(G.conjugate(s0).board == s0.board,
   "the opening BOARD is a fixed point of the seat-swapping conjugation")
for h in M.HEIGHTS:
    st = G.initial_state({"height": h})
    ok(st.board == {(6, 0): (IV, h), (5, 11): (CG, h)}, f"height option {h}")
ok(G.initial_state({"height": 7}).board[(6, 0)] == (IV, 20),
   "an unsupported height falls back to the published 20")

# The 33 opening moves, derived square by square from the rule sheet rather than
# from the move generator (this is also the AbstractPlay reference's count).
OPEN = ([(6, r) for r in range(1, 12)]                       # north, 11
        + [(c, 0) for c in range(7, 12)]                     # east, 5
        + [(c, 0) for c in range(0, 6)]                      # west, 6
        + [(7, 1), (8, 2), (9, 3), (10, 4), (11, 5)]         # north-east, 5
        + [(5, 1), (4, 2), (3, 3), (2, 4), (1, 5), (0, 6)])  # north-west, 6
ok(len(OPEN) == 33, "hand-derived opening list has 33 destinations")
ok(set(G.legal_moves(s0)) == {mv((6, 0), t) for t in OPEN},
   f"33 opening moves exactly; got {len(G.legal_moves(s0))}")
for h in M.HEIGHTS:
    ok(len(G.legal_moves(G.initial_state({"height": h}))) == 33,
       f"33 opening moves at height {h} too")

# ---------------------------------------------------------------------------
# 2. The figures.  Each figure is an 8x8 excerpt of the 12x12 board; a placement
#    maps excerpt (row-from-top, col) -> board (c0 + col, rtop - row).
# ---------------------------------------------------------------------------
def place(fig, c0, rtop, to_move, ply=10):
    board = {(c0 + ec, rtop - er): v for (er, ec), v in fig.items()}
    assert len(board) == len(fig), "figure placement collided"
    return MQState(board=board, to_move=to_move, ply=ply)


OFFSETS = [(c0, rtop) for c0 in range(5) for rtop in range(7, 12)]

# --- Figure 2: "Ivory has one queen (a stack of seven) and one baby; Cigar has
#     one queen and two babies."  Fixes what counts as a queen vs a baby.
FIG2 = {(3, 0): (IV, 1), (5, 2): (IV, 7),
        (4, 7): (CG, 1), (5, 6): (CG, 1), (6, 7): (CG, 9)}
s = place(FIG2, 2, 9, IV)
ok(G.queen_of(s, IV) == (2 + 2, 9 - 5) and s.board[G.queen_of(s, IV)][1] == 7,
   "Figure 2: Ivory's queen is the 7-stack")
ok(G.queen_of(s, CG) == (2 + 7, 9 - 6) and s.board[G.queen_of(s, CG)][1] == 9,
   "Figure 2: Cigar's queen is the 9-stack")
ok(sum(1 for o, h in s.board.values() if o == IV and h == 1) == 1
   and sum(1 for o, h in s.board.values() if o == CG and h == 1) == 2,
   "Figure 2: one ivory baby, two cigar babies")

# --- Figure 3: the ivory queen kills a cigar baby, keeping its height ------
FIG3 = {(1, 5): (IV, 1), (3, 6): (CG, 4), (4, 2): (IV, 6), (6, 2): (CG, 1)}
s = place(FIG3, 2, 9, IV)
frm, to = (2 + 2, 9 - 4), (2 + 2, 9 - 6)
ok(mv(frm, to) in G.legal_moves(s), "Figure 3: the queen's capture is legal")
ns = G.apply_move(s, mv(frm, to))
ok(frm not in ns.board and ns.board[to] == (IV, 6),
   "Figure 3 / NOTE 1: a CAPTURING queen move carries the whole stack and leaves "
   f"NOTHING behind (6 -> 6); got {sorted(ns.board.items())}")
ok(ns.winner is None, "Figure 3: killing a baby is not a win")
ok(sum(h for _o, h in ns.board.values()) == 6 + 4 + 1,
   "Figure 3: the captured baby leaves the game")

# --- Figure 4: a non-capturing queen move gives birth ----------------------
FIG4 = {(2, 5): (CG, 1), (3, 4): (CG, 8), (6, 6): (IV, 5)}
s = place(FIG4, 2, 9, IV)
frm, to = (2 + 6, 9 - 6), (2 + 0, 9 - 6)
ok(mv(frm, to) in G.legal_moves(s), "Figure 4: the 6-square queen slide is legal")
ns = G.apply_move(s, mv(frm, to))
ok(ns.board[to] == (IV, 4) and ns.board[frm] == (IV, 1),
   "Figure 4: queen 5 -> 4 at the destination, a NEW ivory baby on the origin; "
   f"got {sorted(ns.board.items())}")
ok(sum(h for _o, h in ns.board.values()) == 5 + 8 + 1,
   "Figure 4: a birth conserves total material")

# --- Figure 5: an ivory baby kills a cigar baby at range ------------------
FIG5 = {(1, 2): (IV, 3), (2, 6): (CG, 1), (3, 1): (CG, 5), (6, 2): (IV, 1)}
s = place(FIG5, 2, 9, IV)
frm, to = (2 + 2, 9 - 6), (2 + 6, 9 - 2)
ok(mv(frm, to) in G.legal_moves(s), "Figure 5: the baby's 4-square diagonal kill")
ns = G.apply_move(s, mv(frm, to))
ok(frm not in ns.board and ns.board[to] == (IV, 1),
   "Figure 5: the baby replaces the victim and stays a singleton")

# A baby capture is NOT subject to the distance rule, and FIGURE 5 IS ITSELF THE
# PUBLISHED PROOF: the cigar queen stands three ranks below the ivory baby, and
# the kill carries the baby from squared distance 10 to squared distance 26 --
# strictly FARTHER.  Checked at every one of the 25 possible crops, since the
# distances are translation-invariant.
for c0, rtop in OFFSETS:
    s5 = place(FIG5, c0, rtop, IV)
    b5, e5, d5 = (c0 + 2, rtop - 6), (c0 + 1, rtop - 3), (c0 + 6, rtop - 2)
    ok(M.d2(b5, e5) == 10 and M.d2(d5, e5) == 26,
       f"Figure 5 geometry at offset {(c0, rtop)}: 10 -> 26, i.e. AWAY from the "
       f"cigar queen; got {M.d2(b5, e5)} -> {M.d2(d5, e5)}")
    ok(mv(b5, d5) in set(G.legal_moves(s5)),
       f"Figure 5: the published baby kill is legal even though it moves the baby "
       f"FARTHER from the enemy queen, at offset {(c0, rtop)}")
s = place(FIG5, 2, 9, IV)

# ...and a second, synthetic case of the same exemption, plus its control.
s = MQState(board={(0, 0): (IV, 1), (0, 5): (CG, 1), (1, 0): (CG, 4)}, to_move=IV, ply=10)
ok(M.d2((0, 5), (1, 0)) > M.d2((0, 0), (1, 0)),
   "the away-capture test really does move away from the enemy queen")
ok(mv((0, 0), (0, 5)) in G.legal_moves(s),
   "a baby may capture even when the capture INCREASES its distance to the queen")
ok(mv((0, 0), (0, 4)) not in G.legal_moves(s),
   "...but the same baby may not merely step to that farther square")

# --- Figure 6: a baby must STRICTLY shorten its distance to the enemy queen
FIG6 = {(0, 0): (CG, 7), (5, 1): (IV, 7), (7, 4): (IV, 1)}
for c0, rtop in OFFSETS:
    s = place(FIG6, c0, rtop, IV)
    baby = (c0 + 4, rtop - 7)
    eq = (c0 + 0, rtop - 0)
    dest = (c0 + 6, rtop - 5)                  # the figure's arrow, d2 61 < 65
    other = (c0 + 5, rtop - 6)                 # the other 61 square on that ray
    xsq = (c0 + 7, rtop - 4)                   # the square marked X, d2 65 == 65
    beyond = (c0 + 8, rtop - 3)                # further along the ray, d2 73 > 65
    lm = set(G.legal_moves(s))
    ok(M.d2(baby, eq) == 65 and M.d2(dest, eq) == 61 and M.d2(xsq, eq) == 65,
       f"Figure 6 geometry at offset {(c0, rtop)}")
    ok(mv(baby, dest) in lm, f"Figure 6: the closer square is legal {(c0, rtop)}")
    ok(mv(baby, other) in lm, f"Figure 6: the other closer square is legal {(c0, rtop)}")
    ok(mv(baby, xsq) not in lm,
       f"Figure 6: the square marked X (EQUAL distance) is illegal {(c0, rtop)}")
    if 0 <= beyond[0] < 12 and 0 <= beyond[1] < 12:
        ok(mv(baby, beyond) not in lm,
           f"Figure 6: a farther square on the same ray is illegal {(c0, rtop)}")

# --- NOTE 2: a queen of height two may not give birth, but may still kill ---
s = MQState(board={(4, 4): (IV, 2), (4, 9): (CG, 3), (0, 0): (CG, 1)},
            to_move=IV, ply=10)
lm = set(G.legal_moves(s))
ok(all(">" not in m or G.parse(m)[1] in ((4, 9), (0, 0)) for m in lm),
   "NOTE 2: a height-2 queen has ONLY capturing moves")
ok(mv((4, 4), (4, 9)) in lm and mv((4, 4), (0, 0)) in lm,
   "NOTE 2: ...and it really can capture in every direction")
ok(mv((4, 4), (4, 5)) not in lm, "NOTE 2: no birth from a height-2 queen")
s3 = MQState(board={(4, 4): (IV, 3), (4, 9): (CG, 3), (0, 0): (CG, 1)},
             to_move=IV, ply=10)
ok(mv((4, 4), (4, 5)) in G.legal_moves(s3),
   "NOTE 2 bites: the same slide IS legal from a height-3 queen")
ns = G.apply_move(s, mv((4, 4), (4, 9)))
ok(ns.board[(4, 9)] == (IV, 2) and (4, 4) not in ns.board and ns.winner == IV,
   "a height-2 queen capturing the enemy QUEEN wins and stays height 2")

# --- Figure 7: cigar is lost -- every move loses the queen next ply --------
FIG7 = {(0, 3): (CG, 1), (0, 5): (CG, 1), (0, 7): (CG, 1),
        (1, 1): (CG, 1), (1, 3): (CG, 1), (1, 4): (CG, 1), (1, 7): (CG, 6),
        (2, 1): (CG, 1), (2, 6): (CG, 1),
        (3, 4): (IV, 1),
        (5, 2): (IV, 1), (5, 6): (IV, 1),
        (6, 0): (IV, 9), (6, 7): (IV, 1),
        (7, 1): (IV, 1)}
# Of the 25 possible crops of the 12x12 board, EXACTLY ONE makes the published
# claim true, and it is the top-right corner (c0=4, rtop=11) -- independently
# confirmed by the figure's checkerboard parity.
good = []
for c0, rtop in OFFSETS:
    s = place(FIG7, c0, rtop, CG)
    moves = G.legal_moves(s)
    if not moves:
        continue
    if any(G.apply_move(s, m).winner == CG for m in moves):
        continue
    if all(any(G.apply_move(G.apply_move(s, m), r).winner == IV
               for r in G.legal_moves(G.apply_move(s, m))) for m in moves):
        good.append((c0, rtop))
ok(good == [(4, 11)],
   f"Figure 7 is uniquely the top-right crop of the board; got {good}")
s = place(FIG7, 4, 11, CG)
ok(len(G.legal_moves(s)) == 92,
   f"Figure 7: cigar has 92 legal moves; got {len(G.legal_moves(s))}")
ok(not G.is_terminal(s), "Figure 7 is not yet terminal -- cigar must move")

# --- Figure 8: the stuck-loss.  Ivory has a height-2 queen, no babies and
#     nothing in line of sight, so he cannot move and LOSES.
FIG8 = {(1, 6): (CG, 1), (4, 5): (IV, 2), (5, 2): (CG, 2)}
for c0, rtop in OFFSETS:
    s = place(FIG8, c0, rtop, IV)
    ok(G.legal_moves(s) == [],
       f"Figure 8: Ivory has NO legal move at offset {(c0, rtop)}")
    ok(G.is_terminal(s), f"Figure 8 is terminal at offset {(c0, rtop)}")
    ok(G.returns(s) == [-1.0, 1.0],
       f"Figure 8: Ivory loses (Cigar wins) at offset {(c0, rtop)}")
    ok(G.render(s)["caption"].startswith("Cigar wins"),
       "Figure 8 caption names the winner")

# ...and reached through apply_move from a legal predecessor, not hand-built:
#   the cigar baby on b12 walks to i9, closing on the ivory queen at h6.
pre = MQState(board={(7, 5): (IV, 2), (4, 4): (CG, 2), (8, 11): (CG, 1)},
              to_move=CG, ply=12)
ok(M.d2((8, 8), (7, 5)) < M.d2((8, 11), (7, 5)),
   "the predecessor's baby move really does close on the ivory queen")
ok(mv((8, 11), (8, 8)) in G.legal_moves(pre), "predecessor move is legal")
post = G.apply_move(pre, mv((8, 11), (8, 8)))
ok(post.to_move == IV and post.winner is None, "stuck position reached, Ivory to move")
ok(G.legal_moves(post) == [] and G.is_terminal(post) and G.returns(post) == [-1.0, 1.0],
   "a stuck-loss REACHED VIA apply_move scores as a loss for the player to move")
ok(G.render(post)["caption"].startswith("Cigar wins"),
   "the reached ivory stuck-loss caption names Cigar")

# ...and the SAME thing with the seats exchanged, so the stuck-loss is reached
# through apply_move for BOTH seats.  The predecessor is the hand-written 180-degree
# + colour image of `pre`: the ivory baby on d1 walks to d4, closing on the cigar
# queen on e7, which is then left with nothing on any of its eight rays.
pre_c = MQState(board={(4, 6): (CG, 2), (7, 7): (IV, 2), (3, 0): (IV, 1)},
                to_move=IV, ply=12)
ok(G.conjugate(pre) == pre_c,
   f"the mirror predecessor really is `pre` conjugated; got {sorted(G.conjugate(pre).board.items())}")
ok(mv((3, 0), (3, 3)) in G.legal_moves(pre_c), "mirror predecessor move is legal")
post_c = G.apply_move(pre_c, mv((3, 0), (3, 3)))
ok(post_c.to_move == CG and post_c.winner is None, "stuck position reached, Cigar to move")
ok(G.legal_moves(post_c) == [] and G.is_terminal(post_c) and G.returns(post_c) == [1.0, -1.0],
   f"a CIGAR stuck-loss reached via apply_move scores as a loss for Cigar; "
   f"got {G.legal_moves(post_c)} {G.returns(post_c)}")
ok(G.render(post_c)["caption"].startswith("Ivory wins"),
   f"the reached cigar stuck-loss caption names Ivory; got "
   f"{G.render(post_c)['caption']!r}")
ok(G.conjugate(post) == post_c,
   "the two reached stuck-losses are exact 180-degree + colour conjugates")

# --- Figure 9: exactly one move, and it loses ------------------------------
FIG9 = {(1, 6): (CG, 1), (4, 6): (IV, 2), (5, 2): (CG, 2)}
for c0, rtop in OFFSETS:
    s = place(FIG9, c0, rtop, IV)
    only = mv((c0 + 6, rtop - 4), (c0 + 6, rtop - 1))
    ok(G.legal_moves(s) == [only],
       f"Figure 9: Ivory's ONLY move is the kill, at offset {(c0, rtop)}; "
       f"got {G.legal_moves(s)}")
    ns = G.apply_move(s, only)
    ok(ns.winner is None, "Figure 9: killing the baby is not a win")
    reply = G.legal_moves(ns)
    ok(len(reply) == 1, f"Figure 9: Cigar then has one move; got {reply}")
    nn = G.apply_move(ns, reply[0])
    ok(nn.winner == CG and G.is_terminal(nn) and G.returns(nn) == [-1.0, 1.0],
       f"Figure 9: 'Ivory then loses on the following turn' at offset {(c0, rtop)}")

# ---------------------------------------------------------------------------
# 3. "No legal moves" == the rule sheet's condition 2 (queen of height two, no
#    babies, nothing in line of sight).  Proof + machine check.
# ---------------------------------------------------------------------------
def cond2(s, p):
    q = None
    babies = 0
    for _cell, (o, h) in s.board.items():
        if o == p:
            if h >= 2:
                q = h
            else:
                babies += 1
    if q != 2 or babies:
        return False
    return not G.queen_attacked(s, p)


# The lemma the proof rests on, checked EXHAUSTIVELY over every ordered pair of
# squares: unless the enemy queen is a neighbour (in which case the baby can
# simply take it), a baby has at least TWO on-board first steps that strictly
# shorten its distance to the queen.  Both of those squares would have to hold
# one of the mover's own pieces for the baby to be stuck -- and the closest such
# piece can only be the queen, of which there is one.  Hence a stuck player has
# no babies; a queen of height >= 3 always has a birth move somewhere (it cannot
# be walled in without babies); so a stuck player's queen has height exactly two
# and sees nothing to kill.
worst = 99
npairs = ntight = 0
for B in ALL_CELLS:
    for Q in ALL_CELLS:
        if B == Q or max(abs(B[0] - Q[0]), abs(B[1] - Q[1])) == 1:
            continue
        npairs += 1
        n = 0
        for dc, dr in M.DIRS:
            t = (B[0] + dc, B[1] + dr)
            if M.on_board(*t) and M.d2(t, Q) < M.d2(B, Q):
                n += 1
        worst = min(worst, n)
        ntight += (n == 2)
ok(worst == 2 and npairs == 19_580 and ntight == 440,
   f"exhaustive lemma: all {npairs} non-adjacent (baby, enemy queen) pairs have "
   f">= 2 reducing on-board first steps (min {worst}, tight in {ntight})")
ok(all(B[0] == Q[0] or B[1] == Q[1] or abs(B[0] - Q[0]) == abs(B[1] - Q[1])
       for B in ALL_CELLS for Q in ALL_CELLS
       if B != Q and max(abs(B[0] - Q[0]), abs(B[1] - Q[1])) == 1),
   "every neighbour lies on a queen line, so an adjacent enemy queen is takeable")

rng = random.Random(20110131)
nstuck = ndis = 0
stuck_seen = {IV: 0, CG: 0}
for _i in range(4000):
    nb0, nb1 = rng.randrange(0, 5), rng.randrange(0, 5)
    hq0, hq1 = rng.choice([2, 2, 2, 3, 4, 7]), rng.choice([2, 2, 2, 3, 4, 7])
    cells = rng.sample(ALL_CELLS, 2 + nb0 + nb1)
    board = {cells[0]: (IV, hq0), cells[1]: (CG, hq1)}
    for k in range(nb0):
        board[cells[2 + k]] = (IV, 1)
    for k in range(nb1):
        board[cells[2 + nb0 + k]] = (CG, 1)
    for p in (IV, CG):
        s = MQState(board=board, to_move=p, ply=10)
        st = not G.board_moves(s, p)
        nstuck += st
        if st != cond2(s, p):
            ndis += 1
        if not st:
            continue
        # THE STUCK-LOSS VERDICT, SCORED FOR **BOTH** SEATS.  Asserting it only
        # from Figures 8/9 (where Ivory is the stuck player) leaves seat CIGAR
        # completely untested: a `returns` that hard-codes the winner, or a
        # caption that hard-codes a colour, then passes.  Both were surviving
        # mutants until this loop existed.
        stuck_seen[p] += 1
        ok(G.legal_moves(s) == [] and G.is_terminal(s),
           f"stuck position is terminal, seat {p}")
        ok(G.returns(s) == [1.0 if q == 1 - p else -1.0 for q in (IV, CG)],
           f"the STUCK player loses, seat {p}: got {G.returns(s)}")
        ok(G.render(s)["caption"].startswith(f"{M.NAMES[1 - p]} wins"),
           f"the stuck-loss caption names the seat that WON, seat {p}: "
           f"{G.render(s)['caption']!r}")
        poisoned = dataclasses.replace(s, ply=M.PLY_CAP + 7)
        ok(G.is_terminal(poisoned) and G.returns(poisoned) == G.returns(s),
           f"a stuck loss outranks the ply cap for seat {p} too")
ok(ndis == 0 and nstuck > 100,
   f"'no legal moves' == the sheet's condition 2 over 8000 random positions "
   f"({nstuck} stuck, {ndis} disagreements)")
ok(min(stuck_seen.values()) > 20,
   f"stuck-loss verdicts were scored for BOTH seats: {stuck_seen}")

# The reverse lookup `queen_attacked` is a SEPARATE code path from movegen (it
# fires rays out of the queen instead of out of the movers), so check it
# positively, per attacker type, against a brute-force recomputation from the
# move generator.
nb = nq = 0
for _i in range(3000):
    cells = rng.sample(ALL_CELLS, rng.randrange(2, 8))
    board = {cells[0]: (IV, rng.choice([2, 3, 9])), cells[1]: (CG, rng.choice([2, 5]))}
    for c in cells[2:]:
        board[c] = (rng.choice([IV, CG]), 1)
    s = MQState(board=board, to_move=IV, ply=10)
    for defender in (IV, CG):
        q = G.queen_of(s, defender)
        brute = any(G.parse(m)[1] == q for m in G.board_moves(s, 1 - defender))
        ok(G.queen_attacked(s, defender) == brute,
           f"queen_attacked matches movegen for seat {defender}")
        if brute:
            attacker = [G.parse(m)[0] for m in G.board_moves(s, 1 - defender)
                        if G.parse(m)[1] == q]
            if any(s.board[a][1] == 1 for a in attacker):
                nb += 1
            if any(s.board[a][1] >= 2 for a in attacker):
                nq += 1
ok(nb > 50 and nq > 50,
   f"queen_attacked was exercised positively by BOTH attacker types "
   f"(baby {nb}, queen {nq})")

# ---------------------------------------------------------------------------
# 4. Seat symmetry -- neither seat may be untested.
# ---------------------------------------------------------------------------
def flip_owners(s):
    """Pure colour exchange, geometry untouched.  Monkey Queen has no forward
    direction, so this alone must map the move set onto itself IDENTICALLY."""
    return MQState(board={c: (1 - o, h) for c, (o, h) in s.board.items()},
                   to_move=1 - s.to_move, ply=s.ply, last=s.last,
                   winner=(None if s.winner is None else 1 - s.winner))


def rot_move(m):
    frm, to = G.parse(m)
    return mv((11 - frm[0], 11 - frm[1]), (11 - to[0], 11 - to[1]))


GUARD = 3000          # >> the 325-ply worst case seen in 1800 random games
nsym = 0
for gi in range(40):
    s = G.initial_state({"height": rng.choice(M.HEIGHTS)})
    while not G.is_terminal(s):
        ok(s.ply < GUARD, "random game terminated well inside the guard")
        if s.ply >= GUARD:
            break
        if s.ply >= 2:
            a = set(G.legal_moves(s))
            ok(a == set(G.legal_moves(flip_owners(s))),
               "colour exchange leaves the move set identical")
            conj = G.conjugate(s)
            ok(conj.to_move == 1 - s.to_move, "conjugation swaps the seat to move")
            ok({rot_move(m) for m in a} == set(G.legal_moves(conj)),
               "the 180-degree + colour conjugation maps the move set over exactly")
            ok(G.conjugate(conj) == s, "conjugation is an involution")
            ok(G.returns(conj) == G.returns(s)[::-1], "returns conjugates")
            ok([round(x, 9) for x in G.heuristic(conj)]
               == [round(x, 9) for x in G.heuristic(s)[::-1]], "heuristic conjugates")
            nsym += 1
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
ok(nsym > 1500, f"seat-symmetry checked at {nsym} positions")

# ---------------------------------------------------------------------------
# 5. The pie rule
# ---------------------------------------------------------------------------
ok("swap" not in G.legal_moves(s0), "no swap on Ivory's first turn")
a1 = G.apply_move(s0, mv((6, 0), (6, 4)))
ok(a1.ply == 1 and a1.to_move == CG and "swap" in G.legal_moves(a1),
   "swap is offered on Cigar's first turn")
sw = G.apply_move(a1, "swap")
ok(sw.board == {(5, 11): (CG, 1), (5, 7): (CG, 19), (6, 0): (IV, 20)},
   f"swap = 180-degree rotation + colour exchange; got {sorted(sw.board.items())}")
ok(sw.to_move == IV and sw.ply == 2, "after the swap the other seat moves, as second")
ok("swap" not in G.legal_moves(sw), "the pie is offered once only")
ok(G.conjugate(a1).board == sw.board, "swap is exactly the documented conjugation")
ok(len(G.legal_moves(sw)) == 33,
   "after a swap the second player faces the untouched 33-move opening")
a2 = G.apply_move(a1, mv((5, 11), (5, 7)))
ok("swap" not in G.legal_moves(a2), "no swap from ply 2 onward")
ok(G.describe_move(a1, "swap") == "Cigar swap (pie rule)", "swap notation")
ok(G.render(a1).get("actionNames", {}).get("swap"), "the swap renders as a button")
ok("actionNames" not in G.render(sw), "no stray action button after the pie window")

# ---------------------------------------------------------------------------
# 6. Termination -- the (H, Q, D) monovariant, machine-checked on every ply
# ---------------------------------------------------------------------------
def monovariant(s):
    H = sum(h for _o, h in s.board.values())
    Q = sum(h for _o, h in s.board.values() if h >= 2)
    q = [G.queen_of(s, 0), G.queen_of(s, 1)]
    D = sum(M.d2(c, q[1 - o]) for c, (o, h) in s.board.items()
            if h == 1 and q[1 - o] is not None)
    return (H, Q, D)


longest = nplies = 0
kinds = {"capture": 0, "birth": 0, "babystep": 0, "swap": 0}
for gi in range(300):
    s = G.initial_state({"height": M.HEIGHTS[gi % 3]})
    prev = monovariant(s)
    n = 0
    while not G.is_terminal(s):
        ok(n < GUARD, "random game terminated well inside the guard")
        if n >= GUARD:
            break
        m = rng.choice(G.legal_moves(s))
        if m == "swap":
            kinds["swap"] += 1
        else:
            frm, to = G.parse(m)
            kinds["capture" if to in s.board else
                  ("birth" if s.board[frm][1] >= 2 else "babystep")] += 1
        ns = G.apply_move(s, m)
        cur = monovariant(ns)
        if m == "swap":
            # the pie swap is an isometry: it must leave the monovariant alone
            ok(cur == prev, f"the pie swap preserves (H,Q,D): {prev} -> {cur}")
        else:
            ok(cur < prev, f"the (H,Q,D) monovariant strictly decreases: {prev} -> {cur}")
        ok(cur[0] <= prev[0] and cur[1] <= prev[1],
           "total material and total queen height never increase")
        # invariants
        ok(all(h >= 1 for _o, h in ns.board.values()), "no empty stack")
        ok(ns.ply % 2 == ns.to_move, "ply parity tracks the seat to move")
        if ns.winner is None:
            ok(len([1 for o, h in ns.board.values() if o == 0 and h >= 2]) == 1
               and len([1 for o, h in ns.board.values() if o == 1 and h >= 2]) == 1,
               "each side keeps exactly one queen while the game is live")
        prev, s = cur, ns
        n += 1
    nplies += n
    longest = max(longest, n)
    ok(G.returns(s) in ([1.0, -1.0], [-1.0, 1.0]),
       "every terminal is decisive -- a draw cannot occur")
ok(all(kinds[k] > 200 for k in ("capture", "birth", "babystep")) and kinds["swap"] >= 1,
   f"every move kind exercised: {kinds}")
ok(monovariant(a1) == monovariant(sw),
   "deterministic check: the pie swap leaves (H,Q,D) untouched")
ok(longest < 2000, f"random games are short (longest {longest} plies of {nplies})")
ok(M.PLY_CAP == M.ply_cap(M.MAX_START) and M.PLY_CAP > 2_000_000,
   f"the ply cap is the documented, provably dead bound; got {M.PLY_CAP}")
ok(M.ply_cap(20) == 636_050, f"ply_cap(20) = 636050; got {M.ply_cap(20)}")
# Re-derive the bound from its three factors rather than trusting one constant.
# The `+ 2` (not `+ 1`) is load-bearing: captures are bounded by m + 1, not m,
# because the GAME-ENDING queen kill is the one capture after which H >= 4 need
# not hold.  Publishing this bound with `+ 1` leaves it one ply short of airtight.
for _start in M.HEIGHTS:
    _m = 2 * _start - 4
    _births, _caps, _runs = _m, _m + 1, 2 * _m + 1
    ok(M.ply_cap(_start) == _births + _caps + 1 + _runs * _m * M.MAX_D2,
       f"ply_cap({_start}) = births({_births}) + captures({_caps}) + pie(1) + "
       f"{_runs} baby-step runs of <= {_m}*{M.MAX_D2}; got {M.ply_cap(_start)}")
ok(M.MAX_D2 == 11 ** 2 + 11 ** 2 == 242, f"MAX_D2 is the 12x12 diameter; got {M.MAX_D2}")

# A DECISIVE RESULT OUTRANKS THE PLY CAP.  Both flavours of decisive result are
# re-scored with the counter poisoned, and the poison is shown to bite.
kill = G.apply_move(MQState(board={(4, 4): (IV, 2), (4, 9): (CG, 3)}, to_move=IV,
                           ply=10), mv((4, 4), (4, 9)))
kill_cg = G.apply_move(MQState(board={(7, 7): (CG, 2), (7, 2): (IV, 3)}, to_move=CG,
                              ply=10), mv((7, 7), (7, 2)))
ok(kill_cg.winner == CG and G.returns(kill_cg) == [-1.0, 1.0],
   "Cigar killing the ivory queen wins for Cigar")
# The killed-queen caption must name the ACTUAL winner -- checked for both seats,
# or a hard-coded colour survives (it did).
ok(G.render(kill)["caption"].startswith("Ivory wins -- enemy queen killed"),
   f"killed-queen caption for Ivory; got {G.render(kill)['caption']!r}")
ok(G.render(kill_cg)["caption"].startswith("Cigar wins -- enemy queen killed"),
   f"killed-queen caption for Cigar; got {G.render(kill_cg)['caption']!r}")
for name, dead in (("killed queen", kill), ("killed queen (cigar)", kill_cg),
                   ("stuck loss", post), ("stuck loss (cigar)", post_c)):
    poisoned = dataclasses.replace(dead, ply=10 ** 9)
    ok(G.is_terminal(poisoned) and G.returns(poisoned) == G.returns(dead),
       f"a {name} still scores decisively at ply 10^9, not as a cap draw")
live = MQState(board={(4, 4): (IV, 5), (9, 9): (CG, 5)}, to_move=IV, ply=10)
ok(not G.is_terminal(live) and G.legal_moves(live), "control: the live position is live")
capped = dataclasses.replace(live, ply=M.PLY_CAP)
ok(G.is_terminal(capped) and G.legal_moves(capped) == [] and G.returns(capped) == [0, 0],
   "the poison bites: at the cap a LIVE position ends as an honest 0-0 draw")

# ---------------------------------------------------------------------------
# 7. serialize / deserialize -- compare STATES, and the exact key set
# ---------------------------------------------------------------------------
KEYS = {"board", "to_move", "ply", "last", "winner"}
nser = 0
for gi in range(30):
    s = G.initial_state({"height": M.HEIGHTS[gi % 3]})
    seen_swap = False
    while True:
        d = G.serialize(s)
        ok(set(d) == KEYS, f"serialize key set is exactly {sorted(KEYS)}; got {sorted(d)}")
        ok(json.loads(json.dumps(d)) == d, "serialize output is JSON-able")
        ok(G.deserialize(json.loads(json.dumps(d))) == s,
           f"deserialize(serialize(s)) == s (STATE comparison) at ply {s.ply}")
        nser += 1
        if G.is_terminal(s):
            break
        ok(s.ply < GUARD, "random game terminated well inside the guard")
        if s.ply >= GUARD:
            break
        ms = G.legal_moves(s)
        if "swap" in ms and not seen_swap:
            seen_swap = True
            s = G.apply_move(s, "swap")           # cover the post-swap shape too
        else:
            s = G.apply_move(s, rng.choice(ms))
ok(nser > 800, f"serialize sweep covered {nser} states")
ok(G.serialize(s0)["last"] is None and G.serialize(kill)["winner"] == IV,
   "the optional fields really do take both shapes in the sweep")

# ---------------------------------------------------------------------------
# 8. Notation
# ---------------------------------------------------------------------------
s = place(FIG3, 2, 9, IV)
ok(G.describe_move(s, mv((4, 5), (4, 3))) == "Ivory Qe6xe4 takes baby",
   f"queen capture notation; got {G.describe_move(s, mv((4, 5), (4, 3)))}")
s = place(FIG4, 2, 9, IV)
ok(G.describe_move(s, mv((8, 3), (2, 3))) == "Ivory Qi4-c4 (birth i4, 5>4)",
   f"queen birth notation; got {G.describe_move(s, mv((8, 3), (2, 3)))}")
s = place(FIG5, 2, 9, IV)
ok(G.describe_move(s, mv((4, 3), (8, 7))) == "Ivory e4xi8 takes baby",
   f"baby capture notation; got {G.describe_move(s, mv((4, 3), (8, 7)))}")
s = place(FIG6, 2, 9, IV)
ok(G.describe_move(s, mv((6, 2), (8, 4))) == "Ivory g3-i5",
   f"baby step notation; got {G.describe_move(s, mv((6, 2), (8, 4)))}")
s = MQState(board={(4, 4): (IV, 2), (4, 9): (CG, 3)}, to_move=IV, ply=10)
ok(G.describe_move(s, mv((4, 4), (4, 9))) == "Ivory Qe5xe10 takes queen (3)",
   f"queen-kill notation; got {G.describe_move(s, mv((4, 4), (4, 9)))}")
for gi in range(6):                              # never crashes, never empty
    s = G.initial_state()
    while not G.is_terminal(s):
        ok(s.ply < GUARD, "random game terminated well inside the guard")
        if s.ply >= GUARD:
            break
        for m in G.legal_moves(s):               # EVERY move of every position
            ok(len(G.describe_move(s, m)) > 4, "describe_move returns a label")
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))

# ---------------------------------------------------------------------------
# 9. render -- declared bounds for EVERY option, from a far-corner position
# ---------------------------------------------------------------------------
CORNER_LINE = [mv((6, 0), (0, 0)), mv((5, 11), (11, 11)),
               mv((0, 0), (0, 11)), mv((11, 11), (11, 0))]
for h in M.HEIGHTS:
    s = G.initial_state({"height": h})
    for m in CORNER_LINE:
        ok(m in G.legal_moves(s), f"corner-walk move {m} legal at height {h}")
        s = G.apply_move(s, m)
    ok({(0, 0), (0, 11), (11, 0), (11, 11)} <= set(s.board),
       f"all four corners occupied at height {h}")
    spec = G.render(s)
    b = spec["board"]
    ok(b["type"] == "square" and b["width"] == 12 and b["height"] == 12,
       f"render declares a 12x12 square board at height {h}")
    for p in spec["pieces"]:
        c, r = M._cell(p["cell"])
        ok(0 <= c < b["width"] and 0 <= r < b["height"],
           f"rendered piece {p['cell']} inside the declared board (height {h})")
    ok(len(spec["pieces"]) == len(s.board), "every stack is rendered")
    for p in spec["pieces"]:
        c, r = M._cell(p["cell"])
        o, hh = s.board[(c, r)]
        ok(p["owner"] == o, "rendered owner matches")
        if hh == 1:
            ok("stack" not in p, "a baby renders as a plain disc (no stack tower)")
        else:
            ok(p.get("stack") == [o] * hh,
               f"a queen renders as a {hh}-band tower of its own colour")
    ok(len(spec["highlights"]) == 2
       and {x["cell"] for x in spec["highlights"]} == {"11,11", "11,0"},
       f"last-move highlights the two squares of the last move; got {spec['highlights']}")
    ok("to move" in spec["caption"], "caption names the side to move")
ok(sorted(G.render(s0)["pieces"], key=lambda p: p["cell"])
   == [{"cell": "5,11", "owner": CG, "stack": [CG] * 20},
       {"cell": "6,0", "owner": IV, "stack": [IV] * 20}],
   "the opening render is the two 20-high towers")
ok(G.render(s0)["highlights"] == [], "no last-move highlight before the first move")
att = MQState(board={(4, 4): (IV, 2), (4, 9): (CG, 3)}, to_move=IV, ply=10)
ok("queen is attacked" in G.render(att)["caption"], "the caption warns about attacks")

# ---------------------------------------------------------------------------
# 10. Bot / heuristic -- ONE PAYOFF PER SEAT, and the cutoff really fires
# ---------------------------------------------------------------------------
for st in (s0, place(FIG7, 4, 11, CG), att):
    hv = G.heuristic(st)
    ok(isinstance(hv, list) and len(hv) == 2, "heuristic returns a list of 2")
    ok(all(isinstance(x, float) and -1.0 <= x <= 1.0 for x in hv),
       f"heuristic values are bounded floats; got {hv}")
    ok(abs(hv[0] + hv[1]) < 1e-9, "heuristic is zero-sum")
ok(G.heuristic(s0) == [0.0, 0.0], "the symmetric opening evaluates to 0")
ok(G.heuristic(kill) == G.returns(kill), "heuristic defers to returns at a terminal")
bot = MCTSBot(random.Random(5), iterations=40, max_rollout=4)
pick = bot.select(G, s0)
ok(pick in G.legal_moves(s0),
   "MCTSBot with max_rollout=4 (forcing the heuristic cutoff) returns a legal move")

# ---------------------------------------------------------------------------
print(f"monkey_queen selftest: {len(FAILS)} failure(s)")
if FAILS:
    sys.exit(1)
print("OK")
