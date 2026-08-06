#!/usr/bin/env python3
"""Amoeba correctness anchors — pure stdlib, run by tests/test_games.py.

The heavy anchor is the differential against AbstractPlay's `gameslib`
implementation of the same game (manual/one-time, needs node): the coordinate
map is proved by ADJACENCY ISOMORPHISM against the oracle's own graph (37/37
cells), then 660 random games / 32,084 plies compare the full legal-move SET
(mapped both ways), the exact bottom->top composition of every stack, the side
to move, terminality and the winner — 0 mismatches; and a 120-game batch of
those is driven entirely from OUR move generator, so the oracle has to *reject*
anything spurious.  Four injected bugs (reversed sow order, wrong distance,
refusing mixed stacks, treating a self-handover as an immediate loss) all produce
mismatches, so that harness is not vacuous, and a 60-degree / 180-degree
coordinate control diverges at the setup while the VERTICAL MIRROR — an
automorphism of both the setup and the rules — correctly cannot.

`gameslib` implements NO repetition rule, so the threefold-repetition ending has
ZERO differential coverage — section 9 below covers it with constructed positions
instead, in the drawn direction, in both decisive directions, and on mixed stacks
whose top count is the reverse of their bottom count.  (Random play never gets
there: over 4,000 games no position recurred more than twice, which is also why
the differential is undisturbed by the rule.)

What follows re-checks every rule against the publisher's rulebook itself, in
BOTH its English and Japanese editions — the texts, the MATERIAL list and all
three figures of each — plus the invariants, with no node needed.
"""

import json
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                              # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
M = sys.modules[type(G).__module__]        # the LIVE module object
W, B = M.WHITE, M.BLACK

FAILS = []
CHECKS = [0]


def ok(cond, msg):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


def pos(desc, to_move=W, ply=0, reps=None):
    """Position from {cell id: (piece codes bottom->top)}.

    Every point is checked to be ON the board: `pos_key` silently ignores an
    off-board cell (it walks CIDS), so a typo'd constructed position would test
    the engine on a state it can never reach, and could do so invisibly.
    """
    for k in desc:
        ok(M.parse_cell(k) in M.ON_BOARD,
           "test position uses the off-board point %s" % k)
    b = {k: tuple(v) for k, v in desc.items()}
    return M.AState(board=b, to_move=to_move, ply=ply,
                    reps=dict(reps) if reps is not None
                    else {M.pos_key(b, to_move): 1})


def wd():
    return M.piece(W, False)


def bd():
    return M.piece(B, False)


def wk():
    return M.piece(W, True)


def bk():
    return M.piece(B, True)


S0 = G.initial_state()

# ---------------------------------------------------------------------------
# 1. BOARD GEOMETRY, and the convexity lemma the whole move generator rests on
# ---------------------------------------------------------------------------
ok(len(M.CELLS) == 37, "hexhex-4 has 37 points, got %d" % len(M.CELLS))
ok(len(set(M.CELLS)) == 37, "duplicate cells")
ok(sorted(len(M.row_cells(r)) for r in range(-3, 4)) == [4, 4, 5, 5, 6, 6, 7],
   "row widths are not 4,5,6,7,6,5,4")

# `legal_moves` tests only the FAR END of the line and concludes the whole line
# is on the board (sowing needs every point of it).  That is a convexity claim.
# Domain of the lemma = every cell x every direction x every distance for which
# the far end is on the board; enumerate it exhaustively, both branches.
conv_dom = conv_bad = 0
for c in M.CELLS:
    for d in M.DIRS:
        for k in range(1, 30):
            far = (c[0] + d[0] * k, c[1] + d[1] * k)
            if far not in M.ON_BOARD:
                continue
            conv_dom += 1
            for j in range(1, k):
                if (c[0] + d[0] * j, c[1] + d[1] * j) not in M.ON_BOARD:
                    conv_bad += 1
ok(conv_bad == 0, "convexity lemma fails on %d of %d (cell,dir,dist) triples"
   % (conv_bad, conv_dom))
# The domain's size, derived a SECOND way from the row widths alone: along a row
# of width w the eastward ray lengths are w-1..0, so one direction contributes
# sum w(w-1)/2, and all six are equivalent by symmetry.
conv_expect = 6 * sum(w * (w - 1) // 2 for w in (4, 5, 6, 7, 6, 5, 4))
ok(conv_dom == conv_expect == 498,
   "convexity domain should be %d triples, got %d" % (conv_expect, conv_dom))

# The longest straight line on this board bounds how tall a MOBILE stack can be.
MAXRAY = max(k for c in M.CELLS for d in M.DIRS for k in range(1, 30)
             if (c[0] + d[0] * k, c[1] + d[1] * k) in M.ON_BOARD)
ok(MAXRAY == 2 * (M.SIZE - 1), "longest ray should be 2*(size-1)=%d, got %d"
   % (2 * (M.SIZE - 1), MAXRAY))

# ---------------------------------------------------------------------------
# 2. SETUP vs the rulebook's MATERIAL list and SETUP figure
# ---------------------------------------------------------------------------
# MATERIAL: "10 white discs, 10 black discs, 1 white 'kernel', 1 black 'kernel'".
cnt = {}
for st in S0.board.values():
    for p in st:
        cnt[p] = cnt.get(p, 0) + 1
ok(cnt.get(wd()) == 10 and cnt.get(bd()) == 10,
   "MATERIAL says 10 discs each, got %s/%s" % (cnt.get(wd()), cnt.get(bd())))
ok(cnt.get(wk()) == 1 and cnt.get(bk()) == 1, "exactly one kernel each")
ok(sum(cnt.values()) == 22, "22 pieces on the board at setup")
ok(all(len(st) == 1 for st in S0.board.values()), "setup has no stacks")

# The SETUP figure, row by row, top (row g, r=-3) to bottom (row a, r=+3):
#   4 black discs / black kernel alone on the middle point / 6 black discs /
#   empty / 6 white discs / white kernel alone on the middle point / 4 white.
for r, want in ((-3, [bd()] * 4), (-2, "mid " + str(bk())), (-1, [bd()] * 6),
                (0, []), (1, [wd()] * 6), (2, "mid " + str(wk())),
                (3, [wd()] * 4)):
    row = M.row_cells(r)
    got = [S0.board[M.cid(c)][0] for c in row if M.cid(c) in S0.board]
    if isinstance(want, str):
        mid = row[len(row) // 2]
        ok(len(got) == 1 and M.cid(mid) in S0.board
           and S0.board[M.cid(mid)] == (int(want.split()[1]),),
           "row r=%d: figure shows one kernel, alone, on the MIDDLE point" % r)
    else:
        ok(got == want, "row r=%d: figure row mismatch %s vs %s" % (r, got, want))

# The published figure DRAWS only 9 white discs — it omits the right-hand end of
# row c — which contradicts its own MATERIAL list and breaks the 180 deg
# rotational symmetry the other 36 points obey.  Both repairs are asserted here:
ok(S0.board.get("2,1") == (wd(),),
   "the point the figure omits (row c, right end) must hold a WHITE disc")
for c, st in S0.board.items():
    q, r = M.parse_cell(c)
    anti = M.cid((-q, -r))
    ok(anti in S0.board and len(S0.board[anti]) == 1
       and M.owner_of(S0.board[anti][0]) == 1 - M.owner_of(st[0])
       and M.is_kernel(S0.board[anti][0]) == M.is_kernel(st[0]),
       "setup is not 180deg-symmetric-with-colours-swapped at %s" % c)

# ORIENTATION / SEAT PIN.  Ground truth is OUTSIDE the engine: the figure draws
# the lower half of the board white and the upper half black, and the renderer
# puts larger r LOWER on screen (hex y = 1.5*r).  So every white piece must sit
# at r > 0 and every black one at r < 0.  This is the premise the caption checks
# below depend on, so it is asserted, not assumed.
for c, st in S0.board.items():
    r = M.parse_cell(c)[1]
    ok((r > 0) == (M.owner_of(st[0]) == W),
       "seat/orientation: %s (owner %d) is on the wrong half (r=%d)"
       % (c, M.owner_of(st[0]), r))
# The figure's bottom-left corner point is a WHITE disc, and the rules say
# "White starts" -> the seat owning that piece is the seat to move at setup.
FIG_BOTTOM_LEFT = M.cid((-M.SIZE + 1, M.SIZE - 1))
ok(FIG_BOTTOM_LEFT == "-3,3", "bottom-left corner id changed: %s" % FIG_BOTTOM_LEFT)
STARTER = M.owner_of(S0.board[FIG_BOTTOM_LEFT][0])
ok(S0.to_move == STARTER, "the owner of the figure's bottom-left disc starts")

# The vertical mirror (q,r) -> (-q-r,r) maps the setup to itself, so board
# orientation is only pinned up to that reflection -- and since every rule is
# geometry-free (distance and direction only), a mirrored board is
# INDISTINGUISHABLE, not a defect.  Asserted as a lemma so the claim is checked.
mir = {M.cid((-q - r, r)): st for (q, r), st in
       ((M.parse_cell(c), st) for c, st in S0.board.items())}
ok(mir == S0.board, "vertical mirror is not an automorphism of the setup")

# ---------------------------------------------------------------------------
# 3. OPENING MOVE COUNT — the independently verified anchor (52), re-derived
#    from named factors, plus what it discriminates.
# ---------------------------------------------------------------------------
open_moves = G.legal_moves(S0)
nbrs = {}
for c in M.CELLS:
    nbrs[M.cid(c)] = sum(1 for d in M.DIRS
                         if (c[0] + d[0], c[1] + d[1]) in M.ON_BOARD)
mine = [c for c, st in S0.board.items() if M.owner_of(st[-1]) == STARTER]
ok(len(mine) == 11, "the starter controls 11 stacks at setup")
ok(len(open_moves) == sum(nbrs[c] for c in mine),
   "opening moves must equal the sum of the starter's on-board neighbours")
ok(len(open_moves) == 52, "opening move count should be 52, got %d" % len(open_moves))
ok(not any(m.endswith("=S") for m in open_moves),
   "every setup stack is 1 high, so no sow move may be offered")
ok(len(set(open_moves)) == len(open_moves), "duplicate opening moves")

# The rulebook says a stack moves "as many spaces as discs comprise the stack",
# but a stack is defined as "a pile of pieces (discs or kernels)" and the
# designer's own summary says "Kernels move exactly as other pieces".  Under a
# discs-ONLY reading the lone kernel would move 0 spaces and be frozen from
# move 1; the verified count of 52 is only reachable if it is mobile.
KCELL = [c for c, st in S0.board.items() if M.is_kernel(st[0])
         and M.owner_of(st[0]) == STARTER][0]
kmoves = [m for m in open_moves if m.startswith(KCELL + ">")]
ok(len(kmoves) == 6, "the lone kernel must have 6 moves, got %d" % len(kmoves))
ok(len(open_moves) - len(kmoves) == 46,
   "a discs-only distance reading would give 46, not the verified 52")

# ---------------------------------------------------------------------------
# 4. THE "MOVING" FIGURE.  A white-topped pile of 3 whose middle piece is BLACK,
#    on row e, moves EAST exactly 3 points (the printed arrow spans 3).
#    Premises asserted alongside the outcome, because a mis-transcribed
#    constant passes every assertion built on it.
# ---------------------------------------------------------------------------
E2, E3, E4, E5 = "-1,-1", "0,-1", "1,-1", "2,-1"
# bottom -> top.  NOT read off the artwork (pixel readings of those piles are
# ambiguous): the Japanese edition's caption spells the composition out in words —
# 「3段のスタックを下から順に、①白、②黒、③白と分離させて」, "splitting a 3-tier
# stack from the bottom in order: (1) white, (2) black, (3) white".
FIGPILE = (wd(), bd(), wd())
ok(len(FIGPILE) == 3, "the figure's caption says three discs")
ok(M.owner_of(FIGPILE[-1]) == W, "the figure's pile is WHITE-topped")
ok(any(M.owner_of(p) == B for p in FIGPILE),
   "the figure's pile contains a black piece (the black band)")

p_move = pos({E2: FIGPILE}, to_move=W)
mv = G.legal_moves(p_move)
# Premise: in the MOVING figure the landing point and the points crossed are
# EMPTY, so that figure cannot discriminate the "nothing blocks you" rule --
# which is therefore tested separately below.
ok(E3 not in p_move.board and E4 not in p_move.board and E5 not in p_move.board,
   "premise: the figure's line is clear")
ok(("%s>%s" % (E2, E5)) in mv, "a 3-pile must be able to move 3 points east")
ok(("%s>%s=S" % (E2, E5)) in mv, "and to sow along the same line")
for k in (1, 2, 4, 5, 6):
    tgt = M.cid((-1 + k, -1))
    ok(("%s>%s" % (E2, tgt)) not in mv,
       "a 3-pile must NOT move %d points east" % k)
after = G.apply_move(p_move, "%s>%s" % (E2, E5))
ok(after.board.get(E5) == FIGPILE and E2 not in after.board,
   "a whole-stack move lands the pile intact, in order")
ok(E3 not in after.board and E4 not in after.board,
   "a whole-stack move drops nothing on the way")

# ---------------------------------------------------------------------------
# 5. THE "SOWING" FIGURE.  Same pile, same line; the first point is already
#    occupied ("Notice that one of the pieces is deployed on top of another
#    stack").  Sowing deploys the BOTTOM piece first.
# ---------------------------------------------------------------------------
# NOTE ON ANCHOR POWER: the printed pile is white-black-white, i.e. PALINDROMIC,
# so the figure is BLIND to the sow ORDER -- it kills 0 of the 2 candidate
# readings.  The order comes from the rulebook sentence "deploy its bottom piece
# on each step" (and the oracle agrees).  Asserted here with a NON-palindromic
# pile, which the figure could never have settled.
occupant = (bd(), wd())                      # a white-topped pile already on E3
p_sow = pos({E2: FIGPILE, E3: occupant}, to_move=W)
ok(E3 in p_sow.board, "premise: the sowing figure's first point is OCCUPIED")
s2 = G.apply_move(p_sow, "%s>%s=S" % (E2, E5))
ok(s2.board.get(E3) == occupant + (FIGPILE[0],),
   "the bottom piece lands on the FIRST point, on TOP of what is there")
ok(s2.board.get(E4) == (FIGPILE[1],), "the middle piece lands alone on point 2")
ok(s2.board.get(E5) == (FIGPILE[2],), "the top piece lands on the LAST point")
ok(E2 not in s2.board, "the sown pile leaves its point empty")
ok(sum(len(x) for x in s2.board.values())
   == sum(len(x) for x in p_sow.board.values()), "sowing conserves pieces")
# Non-palindromic: proves bottom-first, which the figure cannot.
p_np = pos({E2: (bd(), wd(), wd())}, to_move=W)
s3 = G.apply_move(p_np, "%s>%s=S" % (E2, E5))
ok(s3.board.get(E3) == (bd(),) and M.owner_of(s3.board[E3][-1]) == B,
   "bottom-first sowing: the black BOTTOM piece lands nearest and Black gains it")
ok(s3.board.get(E4) == (wd(),) and s3.board.get(E5) == (wd(),),
   "bottom-first sowing: the two white pieces land on points 2 and 3")

# ---------------------------------------------------------------------------
# 6. "Other stacks don't block the movement." + the off-board rule
# ---------------------------------------------------------------------------
blocked = pos({E2: FIGPILE, E3: (bd(), bd(), bd(), bd()), E4: (bk(), bd()),
               E5: (bd(),)}, to_move=W)
bm = G.legal_moves(blocked)
ok(("%s>%s" % (E2, E5)) in bm and ("%s>%s=S" % (E2, E5)) in bm,
   "nothing blocks a move: a fully occupied line must still be legal")
lands = G.apply_move(blocked, "%s>%s" % (E2, E5))
ok(lands.board[E5] == (bd(),) + FIGPILE,
   "a move lands ON TOP of the destination stack, keeping both orders")
sows = G.apply_move(blocked, "%s>%s=S" % (E2, E5))
ok(sows.board[E3] == (bd(),) * 4 + (FIGPILE[0],)
   and sows.board[E4] == (bk(), bd(), FIGPILE[1])
   and sows.board[E5] == (bd(), FIGPILE[2]),
   "a sow drops one piece on top of each stack along the line")
# Sowing that buries an enemy kernel under YOUR piece is a win; here the middle
# piece is BLACK, so it is not.  Checked explicitly further down.

# "high stacks might not be able to move as they would end up outside the board,
# which is illegal."  From the bottom-left corner a 4-pile has only 3 points to
# its east, so that direction is barred — but the long diagonal is 6 points, so
# the same pile CAN travel it.  Both branches, so the check is not one-sided.
CORNER = "-3,3"
edge = pos({CORNER: (wd(),) * 4}, to_move=W)
em = G.legal_moves(edge)
ok(("%s>%s" % (CORNER, M.cid((1, 3)))) not in em, "row a is 4 points wide, so a "
   "4-pile in the corner cannot travel east (that end is off the board)")
ok(("%s>%s" % (CORNER, M.cid((1, -1)))) in em,
   "…but the same 4-pile may travel the long diagonal, which is 6 points")
usable = [d for d in M.DIRS if (-3 + d[0] * 4, 3 + d[1] * 4) in M.ON_BOARD]
ok(len(usable) == 1 and len(em) == 2 * len(usable),
   "a 4-pile in the corner has %d usable line(s) => %d moves, got %d"
   % (len(usable), 2 * len(usable), len(em)))
for h in (MAXRAY + 1, MAXRAY + 4):
    for c in ((-3, 3), (0, 0)):
        ok(G.legal_moves(pos({M.cid(c): (wd(),) * h}, to_move=W)) == [],
           "no stack taller than the longest ray (%d) can ever move (h=%d at %s)"
           % (MAXRAY, h, c))
centre = pos({"0,0": (wd(), wd(), wd())}, to_move=W)
ok(len(G.legal_moves(centre)) == 12,
   "a 3-pile in the centre reaches all 6 directions (move+sow), got %d"
   % len(G.legal_moves(centre)))
# move and sow always come in PAIRS for h >= 2, and never for h == 1
for h in range(1, 7):
    ms = G.legal_moves(pos({"0,0": (wd(),) * h}, to_move=W))
    plain = [m for m in ms if not m.endswith("=S")]
    sw = [m for m in ms if m.endswith("=S")]
    ok(len(sw) == (len(plain) if h > 1 else 0),
       "h=%d: sow moves must pair 1:1 with plain moves (0 when h==1)" % h)

# ---------------------------------------------------------------------------
# 7. CONTROL IS BY THE TOPMOST PIECE
# ---------------------------------------------------------------------------
mixed = pos({"0,0": (bd(), bk(), wd()), "1,0": (wd(), bd())}, to_move=W)
srcs = set(m.split(">")[0] for m in G.legal_moves(mixed))
ok(srcs == {"0,0"}, "you may move only the stacks you TOP, got %s" % srcs)
srcs_b = set(m.split(">")[0] for m in G.legal_moves(replace(mixed, to_move=B)))
ok(srcs_b == {"1,0"}, "and the other player only theirs, got %s" % srcs_b)

# ---------------------------------------------------------------------------
# 8. WIN CONDITIONS
# ---------------------------------------------------------------------------
ok(not G.is_terminal(S0), "the opening position is not terminal")

# (a) kernel capture: White's disc lands on the point holding Black's kernel.
kw = pos({"0,0": (wd(),), "1,0": (bk(),)}, to_move=W)
ok(not G.is_terminal(kw), "burying is a move EVENT, not a board predicate")
kwin = G.apply_move(kw, "0,0>1,0")
ok(kwin.winner == W and G.is_terminal(kwin), "controlling the enemy kernel wins")
ok(G.returns(kwin) == [1.0, -1.0], "returns must be +1/-1, got %s" % G.returns(kwin))
ok(G.legal_moves(kwin) == [], "a finished game has no legal moves")
cap = G.render(kwin)["caption"]
ok(cap.startswith("White wins"),
   "terminal caption must name the seat that owns the figure's bottom-left "
   "disc; got %r" % cap)
# ... and Black's mirror image, so a swapped SEAT_NAMES tuple cannot pass both.
kb = pos({"0,0": (bd(),), "1,0": (wk(),)}, to_move=B)
kbwin = G.apply_move(kb, "0,0>1,0")
ok(kbwin.winner == B and G.render(kbwin)["caption"].startswith("Black wins"),
   "terminal caption for the other seat")

# a kernel under its OWNER's piece is NOT captured
safe = pos({"0,0": (wd(),), "1,0": (bk(), bd())}, to_move=W)
ok(G.apply_move(safe, "0,0>1,0").winner == W,
   "landing on a black-topped stack that holds the black kernel still wins")
# carrying your OWN kernel onto an enemy stack captures nothing
own = pos({"0,0": (wk(),), "1,0": (bd(),), "3,-1": (bk(),)}, to_move=W)
oafter = G.apply_move(own, "0,0>1,0")
ok(oafter.board["1,0"] == (bd(), wk()), "premise: white kernel now tops a mixed pile")
ok(oafter.winner is None,
   "your own kernel landing on an enemy piece is not a capture")

# (b) immobilisation, REACHED through apply_move (win-as-event).
#     Black's ONLY stack is taller than the longest line on the board, so it is
#     provably frozen — the reason is derived from MAXRAY, not asserted by fiat.
FROZEN = (bk(),) + (bd(),) * MAXRAY          # height MAXRAY+1, Black-topped
imm = pos({"0,0": FROZEN, "1,1": (wd(),), "-3,3": (wk(),)}, to_move=W)
ok(len(FROZEN) > MAXRAY, "premise: the black pile is taller than any line")
ok(M.owner_of(FROZEN[-1]) == B, "premise: Black tops it (so Black controls it)")
ok(G.legal_moves(replace(imm, to_move=B)) == [], "premise: Black has no move")
ok(len(G.legal_moves(imm)) > 0, "premise: White has moves")
istate = G.apply_move(imm, "1,1>1,0")
ok(istate.winner == W and G.is_terminal(istate),
   "leaving the opponent no legal move wins")
ok(G.render(istate)["caption"].startswith("White wins"),
   "immobilisation caption names the winner")

# (c) THE SELF-HANDOVER.  "You win if, AT THE END OF YOUR TURN, YOU control a
#     stack with the ENEMY kernel in it" -- so handing the opponent a stack that
#     holds your OWN kernel does not lose on the spot.  Random play reaches this
#     ~7% of games (1,389 events in 20,000), and the differential's `selfwin`
#     injection shows the oracle agrees, so it is a real, covered rule.
hand = pos({"0,0": (bd(), wd()), "0,1": (wk(),), "3,0": (bk(),), "-2,2": (wd(),)},
           to_move=W)
h1 = G.apply_move(hand, "0,0>0,2=S")     # bottom (black) piece -> 0,1 onto wk
ok(h1.board["0,1"] == (wk(), bd()), "premise: the sow put a black piece on wk")
ok(M.owner_of(h1.board["0,1"][-1]) == B, "premise: Black now tops White's kernel")
ok(h1.winner is None and not G.is_terminal(h1),
   "a self-handover does NOT end the game at the end of the mover's turn")
h2 = G.apply_move(h1, "3,0>2,0")         # Black plays anything, keeping it
ok(h2.winner == B, "Black wins at the end of THEIR turn instead")

# the helper itself (it is not on the legality path, so nothing else tests it)
HOLDS = type(G)._holds_enemy_kernel
ok(HOLDS({"0,0": (wk(), bd())}, B) and not HOLDS({"0,0": (wk(), bd())}, W),
   "_holds_enemy_kernel: black on top of the white kernel is held by Black")
ok(not HOLDS({"0,0": (wk(), wd())}, B), "not held when the owner is on top")
ok(not HOLDS({"0,0": (wk(),)}, B), "a bare kernel is not held by the foe")
ok(HOLDS({"0,0": (bd(), bk(), wd())}, W) and not HOLDS({"0,0": (bd(), bk(), wd())}, B),
   "_holds_enemy_kernel sees a kernel buried deep in a mixed stack")
ok(not HOLDS({"0,0": (wd(), bd())}, W) and not HOLDS({}, W),
   "_holds_enemy_kernel is false with no kernels at all")

# ---------------------------------------------------------------------------
# 9. TERMINATION.  There is no monovariant: here is an explicit 4-ply cycle out
#    of the opening position ("a1-b1, g1-f1, b1-a1, f1-g1" in the reference
#    implementation's notation).  The ENGLISH rulebook has nothing to say about
#    it; the publisher's JAPANESE edition of the same rulebook does —
#    「同一局面が 3 回現れた場合 … 制圧しているスタックの数がより多い
#      プレーヤーの勝ちです … 同じ場合は、引き分けとします」
#    ("if the same position appears 3 times … the player controlling more stacks
#      wins … if equal, it is a draw").  So: shuffle twice and the game ends,
#    and at the opening position the stack counts are level, so it is a DRAW.
# ---------------------------------------------------------------------------
A1, B1, G1, F1 = "-3,3", "-3,2", "0,-3", "-1,-2"
CYCLE = ("%s>%s" % (A1, B1), "%s>%s" % (G1, F1),
         "%s>%s" % (B1, A1), "%s>%s" % (F1, G1))
cyc = S0
for m in CYCLE:
    ok(m in G.legal_moves(cyc), "cycle move %s must be legal" % m)
    cyc = G.apply_move(cyc, m)
ok(cyc.board == S0.board and cyc.to_move == S0.to_move and cyc.winner is None
   and not cyc.drawn and cyc.ply == 4,
   "the 4-ply shuffle must return the EXACT opening position, 2nd occurrence")
ok(cyc.reps[M.pos_key(S0.board, S0.to_move)] == 2,
   "…and the repetition counter must show 2")
for m in CYCLE:
    ok(not G.is_terminal(cyc), "the 2nd lap must still be playable")
    cyc = G.apply_move(cyc, m)
ok(G.is_terminal(cyc) and cyc.ply == 8, "the 3rd occurrence must end the game")
ok(cyc.drawn and cyc.winner is None and G.returns(cyc) == [0.0, 0.0],
   "level stack counts at the opening position make it an honest DRAW")
ok(type(G)._stack_counts(cyc.board) == (11, 11),
   "premise: each side controls 11 stacks in the opening position")
ok(G.legal_moves(cyc) == [], "a finished game offers no moves")
ok("equal stacks 11-11" in G.render(cyc)["caption"],
   "the draw caption must state the tie-break it was decided by")

# pos_key must include the SIDE TO MOVE: the same board with the other player on
# turn is a DIFFERENT position, so its count must not carry over.  (A mutant that
# dropped the side survived until this pair was added.)
_kb = {"0,0": (wd(),), "2,0": (bd(),), "-3,0": (wk(),), "3,-3": (bk(),)}
ok(M.pos_key(_kb, W) != M.pos_key(_kb, B),
   "pos_key must distinguish whose turn it is")
ok(M.pos_key(_kb, W) != M.pos_key({"0,0": (bd(),), "2,0": (wd(),),
                                   "-3,0": (wk(),), "3,-3": (bk(),)}, W),
   "pos_key must distinguish different boards")
# …and it must distinguish the ORDER of a pile.  Order is the whole game (it
# decides which piece a sow drops where), so two piles holding the same pieces
# in a different order are DIFFERENT positions and their counts must not merge.
# A mutant that sorted each cell's pieces survived every other check here.
_ord_a, _ord_b = {"0,0": (wd(), bd())}, {"0,0": (bd(), wd())}
ok(M.pos_key(_ord_a, W) != M.pos_key(_ord_b, W),
   "pos_key must distinguish a pile's ORDER, not just its contents")
# the control that makes the line above load-bearing: those two piles really do
# behave differently — sown the same way they put opposite colours on each point
_sow_a = G.apply_move(pos({"0,0": (wd(), bd()), "3,-3": (wk(),)}, to_move=B),
                      "0,0>2,0=S").board
_sow_b = G.apply_move(pos({"0,0": (bd(), wd()), "3,-3": (wk(),)}, to_move=W),
                      "0,0>2,0=S").board
ok(_sow_a["1,0"] == (wd(),) and _sow_b["1,0"] == (bd(),) and _sow_a != _sow_b,
   "premise: the two orders sow to different boards, so conflating them in the "
   "repetition key would merge genuinely distinct positions")
_p = pos(_kb, to_move=W)
_mv = "0,0>1,0"
ok(_mv in G.legal_moves(_p), "premise: the probe move is legal")
_nb = G.apply_move(_p, _mv).board
#   (a) two prior sightings recorded against the WRONG side must NOT end it …
ok(not G.is_terminal(G.apply_move(replace(_p, reps={M.pos_key(_nb, W): 2}), _mv)),
   "a repetition count filed under the other side to move must not end the game")
#   (b) … and the control with the RIGHT side must, or (a) proves nothing.
ok(G.is_terminal(G.apply_move(replace(_p, reps={M.pos_key(_nb, B): 2}), _mv)),
   "with the correct side to move the same counts ARE a third occurrence")

# _stack_counts counts stacks by their TOP piece (that is what "control" means).
# Assert it on MIXED stacks, where top and bottom disagree — a mutant counting
# bottoms survived every singleton-only test.
ok(type(G)._stack_counts({"0,0": (wd(), bd()), "1,0": (wd(),)}) == (1, 1),
   "_stack_counts must count TOP pieces (bottoms would give 2-0)")
ok(type(G)._stack_counts({"0,0": (bd(), bd(), wd()), "1,0": (wd(), wd(), bd()),
                          "2,0": (bk(), wd())}) == (2, 1),
   "_stack_counts on deep mixed stacks")
ok(type(G)._stack_counts({}) == (0, 0), "_stack_counts on an empty board")

# The repetition end is DECISIVE when the stack counts differ, and it must name
# the side with MORE stacks — tested in BOTH directions, so a flipped comparison
# cannot pass either one.
unequal = {"0,0": (wd(),), "2,0": (wd(),), "-3,0": (bd(),), "3,-3": (bk(),),
           "-3,3": (wk(),)}
u0 = pos(unequal, to_move=W)
wc, bc = type(G)._stack_counts(u0.board)
ok((wc, bc) == (3, 2), "premise: White controls 3 stacks, Black 2; got %d-%d"
   % (wc, bc))
# play White A->B then Black x->y then White B->A then Black y->x: back to u0
seq = ("0,0>1,0", "-3,0>-2,0", "1,0>0,0", "-2,0>-3,0")
u = u0
for m in seq:
    ok(m in G.legal_moves(u), "shuffle move %s legal" % m)
    u = G.apply_move(u, m)
ok(u.board == u0.board and u.to_move == u0.to_move and not G.is_terminal(u),
   "premise: the shuffle returns the same position (2nd occurrence)")
for m in seq:
    u = G.apply_move(u, m)
ok(G.is_terminal(u) and u.winner == W and not u.drawn,
   "a 3rd occurrence with 3-2 stacks must be a WIN for White, got winner=%s "
   "drawn=%s" % (u.winner, u.drawn))
ok(G.render(u)["caption"].startswith("White wins"),
   "the repetition-win caption must name White")
# the mirror-image position must hand it to Black, so a flipped comparison dies
u0b = pos({"0,0": (bd(),), "2,0": (bd(),), "-3,0": (wd(),), "3,-3": (wk(),),
           "-3,3": (bk(),)}, to_move=B)
ok(type(G)._stack_counts(u0b.board) == (2, 3), "premise: Black leads 3-2")
ub = u0b
for m in seq * 2:
    ub = G.apply_move(ub, m)
ok(G.is_terminal(ub) and ub.winner == B,
   "the mirrored 3rd occurrence must be a WIN for Black, got %s" % ub.winner)

# …and once more on a board of MIXED stacks whose TOP count (3-2 to White) is the
# REVERSE of its bottom count (2-3), so the adjudication itself proves it counts
# tops.  Each kernel sits under its own colour, so no kernel win can fire.
mix = {"0,0": (bd(), wd()), "2,0": (wk(), wd()),      # White-topped
       "-3,0": (bk(), bd()),                          # Black-topped
       "3,-3": (wd(),), "0,3": (bd(),)}               # the two shuttles
m0 = pos(mix, to_move=W)
ok(type(G)._stack_counts(m0.board) == (3, 2), "premise: White leads 3-2 on TOPS")
bottoms = [0, 0]
for st in m0.board.values():
    bottoms[M.owner_of(st[0])] += 1
ok(tuple(bottoms) == (2, 3),
   "premise: the BOTTOM count is reversed (2-3), so this case discriminates")
ok(not type(G)._holds_enemy_kernel(m0.board, W)
   and not type(G)._holds_enemy_kernel(m0.board, B),
   "premise: neither kernel is captured in this position")
mseq = ("3,-3>2,-3", "0,3>-1,3", "2,-3>3,-3", "-1,3>0,3")
m = m0
for _lap in range(2):
    for mv in mseq:
        ok(mv in G.legal_moves(m), "mixed shuffle move %s legal" % mv)
        ok(not G.is_terminal(m), "the mixed shuffle must stay playable")
        m = G.apply_move(m, mv)
ok(m.board == m0.board and m.ply == 8, "the mixed shuffle returns the position")
ok(G.is_terminal(m) and m.winner == W and not m.drawn,
   "a 3rd occurrence must go to the side leading on TOPS (White), got winner=%s "
   "drawn=%s" % (m.winner, m.drawn))

# A DECISIVE RESULT MUST OUTRANK BOTH END-OF-GAME COUNTERS.
LIVE_CAP, LIVE_REP = M.PLY_CAP, M.REPEAT_LIMIT
ok(LIVE_CAP > 365, "PLY_CAP must sit far above real play (longest of 200,000 "
                   "random games = 365 plies); got %d" % LIVE_CAP)
ok(LIVE_REP == 3, "the Japanese rulebook says THREE occurrences, got %d" % LIVE_REP)
for src, p0, mv0 in (("kernel", kw, "0,0>1,0"), ("immobilise", imm, "1,1>1,0")):
    base = G.apply_move(p0, mv0)
    ok(base.winner is not None, "premise: %s is a decisive finish" % src)
    # (a) the ply cap already tripped
    trip = G.apply_move(replace(p0, ply=M.PLY_CAP - 1), mv0)
    ok(trip.winner == base.winner and not trip.drawn,
       "a %s win on the capping ply must still be that WIN" % src)
    ok(G.apply_move(replace(p0, ply=10 ** 9), mv0).winner == base.winner,
       "a %s win outranks an absurd ply counter" % src)
    # (b) a poisoned repetition table claiming this position is a 3rd occurrence
    poison = {k: 99 for k in list(p0.reps)}
    poison[M.pos_key(G.apply_move(p0, mv0).board, 1 - p0.to_move)] = 99
    ok(G.apply_move(replace(p0, reps=poison), mv0).winner == base.winner,
       "a %s win outranks a poisoned repetition counter" % src)

# …but `kw` and `imm` cannot PROVE that ordering: in both of them the stack-count
# adjudication happens to award the SAME seat as the real win, so a mutant that
# adjudicated the repetition BEFORE the win conditions passed every check above.
# The two positions below are built so the adjudication would award the OTHER
# seat — the winner deliberately TRAILS on stacks — which is what makes the
# ordering observable at all.  (Verified: the mutant dies on these.)
_TRAIL = (
    ("kernel",
     {"0,0": (wd(),), "1,0": (bk(),), "-3,3": (wk(),), "3,-3": (bd(),),
      "0,3": (bd(),), "-3,0": (bd(),), "2,-2": (bd(),)}, "0,0>1,0", (2, 4)),
    ("immobilise",
     {"0,0": (bd(),) * (MAXRAY + 1), "3,-3": (bd(),) * (MAXRAY + 1),
      "0,-3": (bd(),) * (MAXRAY + 1), "1,1": (wd(),), "-3,3": (wk(),)},
     "1,1>1,0", (2, 3)),
)
for src, desc, mv0, want_counts in _TRAIL:
    p0 = pos(desc, to_move=W)
    base = G.apply_move(p0, mv0)
    ok(base.winner == W, "premise: %s must be a WHITE win here, got %s"
       % (src, base.winner))
    ok(type(G)._stack_counts(base.board) == want_counts,
       "premise: White must TRAIL on stacks (%s), else this test is vacuous; got %s"
       % (want_counts, type(G)._stack_counts(base.board)))
    ok(want_counts[0] < want_counts[1],
       "premise: a stack-count adjudication of %s would award BLACK" % src)
    # the repetition counter says "third occurrence" — the WIN must still stand
    rep3 = {M.pos_key(base.board, B): M.REPEAT_LIMIT - 1}
    got = G.apply_move(replace(p0, reps=rep3), mv0)
    ok(got.winner == W and not got.drawn,
       "a %s win must OUTRANK a third-occurrence repetition that would otherwise "
       "hand the game to the opponent on stack count; got winner=%s drawn=%s"
       % (src, got.winner, got.drawn))
    # …and the same for the ply cap, which adjudicates the same way
    got2 = G.apply_move(replace(p0, ply=M.PLY_CAP - 1), mv0)
    ok(got2.winner == W and not got2.drawn,
       "a %s win must OUTRANK the ply cap for the same reason; got winner=%s"
       % (src, got2.winner))
# and the patch is proved to BITE: shrink the cap and a game must end on it
try:
    M.PLY_CAP = 6
    r2 = random.Random(4)
    s = G.initial_state()
    while not G.is_terminal(s):
        s = G.apply_move(s, r2.choice(G.legal_moves(s)))
    ok(s.ply == 6 and (s.drawn or s.winner is not None),
       "with PLY_CAP=6 a game must end at ply 6 (proves the patch bites), "
       "got ply=%d" % s.ply)
    M.REPEAT_LIMIT = 2
    cyc2 = S0
    for m in CYCLE:
        cyc2 = G.apply_move(cyc2, m)
    ok(G.is_terminal(cyc2), "with REPEAT_LIMIT=2 one lap must end the game "
                            "(proves that patch bites too)")
finally:
    M.PLY_CAP, M.REPEAT_LIMIT = LIVE_CAP, LIVE_REP
ok(M.PLY_CAP == LIVE_CAP and M.REPEAT_LIMIT == LIVE_REP, "constants restored")

# ---------------------------------------------------------------------------
# 10. SERIALISATION — compare STATES (a dict round-trip cannot see a dropped
#     field), assert the exact key set, and sweep a whole game so every field's
#     every shape is covered.
# ---------------------------------------------------------------------------
KEYS = {"board", "to_move", "winner", "drawn", "ply", "last", "reps"}
seen_shapes = set()
rs = random.Random(11)
for _ in range(40):
    s = G.initial_state()
    while True:
        d = G.serialize(s)
        ok(set(d) == KEYS, "serialize key set changed: %s" % sorted(d))
        ok(G.deserialize(d) == s, "serialize/deserialize must round-trip STATES")
        ok(json.loads(json.dumps(d)) == d, "serialize must be JSON-able")
        seen_shapes.add(("last%d" % min(len(s.last), 5),
                         "win" if s.winner is not None else
                         "draw" if s.drawn else "live",
                         "tall" if any(len(x) > 3 for x in s.board.values()) else "flat"))
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rs.choice(G.legal_moves(s)))
ok(len([x for x in seen_shapes if x[0] == "last0"]) > 0, "swept the empty `last`")
ok(len([x for x in seen_shapes if x[0] == "last5"]) > 0, "swept a long sow `last`")
ok(len([x for x in seen_shapes if x[1] == "win"]) > 0, "swept a decided state")
ok(len([x for x in seen_shapes if x[2] == "tall"]) > 0, "swept tall stacks")
# every field must actually be carried: drop each one and require a difference
for k in sorted(KEYS):
    d = G.serialize(G.apply_move(G.initial_state(), G.legal_moves(S0)[0]))
    d2 = dict(d)
    d2.pop(k)
    try:
        bad = G.deserialize(d2)
        ok(False, "deserialize silently tolerated a missing %r" % k)
    except (KeyError, TypeError):
        ok(True, "")

# ---------------------------------------------------------------------------
# 11. RENDER — the declared board must CONTAIN every piece, and the tower glyph
#     must report the real stack.  Checked on a reached far-corner position,
#     never on the (piece-free-looking) opening alone.
# ---------------------------------------------------------------------------
def check_render(s, tag):
    spec = G.render(s)
    b = spec["board"]
    ok(b["type"] == "hex" and b["shape"] == "hexagon" and b["size"] == M.SIZE,
       "%s: board spec" % tag)
    n = b["size"] - 1
    declared = set("%d,%d" % (q, r) for q in range(-n, n + 1)
                   for r in range(-n, n + 1) if abs(q + r) <= n)
    ok(len(declared) == 37, "%s: declared cell set" % tag)
    ok(len(spec["pieces"]) == len(s.board),
       "%s: one rendered piece per occupied point" % tag)
    for p in spec["pieces"]:
        ok(p["cell"] in declared,
           "%s: piece at %s is OUTSIDE the declared board" % (tag, p["cell"]))
        st = s.board[p["cell"]]
        ok(p["stack"] == [M.owner_of(x) for x in st],
           "%s: stack owners at %s" % (tag, p["cell"]))
        ok(p["owner"] == M.owner_of(st[-1]), "%s: owner = TOP piece" % tag)
    for h in spec["highlights"]:
        ok(h["cell"] in declared, "%s: highlight outside the board" % tag)
    # kernel marks: exactly on the kernel points, with the right 1-based level
    want = {}
    for c, st in s.board.items():
        for i, x in enumerate(st):
            if M.is_kernel(x):
                want[c] = want.get(c, "") + ("+" if c in want else "") + "K%d" % (i + 1)
    got = {p["cell"]: p["label"] for p in spec["pieces"] if "label" in p}
    ok(got == want, "%s: kernel labels %s vs %s" % (tag, got, want))
    return spec


check_render(S0, "setup")
ok(check_render(S0, "setup")["caption"].startswith("White to move"),
   "in-play caption at setup must name the starter (White)")
after1 = G.apply_move(S0, G.legal_moves(S0)[0])
ok(G.render(after1)["caption"].startswith("Black to move"),
   "in-play caption must flip to the other seat after one move")

# The caption's KERNEL REPORT names a seat per kernel, and nothing pinned it: a
# mutant that swapped those two names labelled White's kernel "Black" on every
# ply of every game and passed every other check here.  Ground truth is the
# printed figure, not the engine: BOTH editions draw the kernel that stands alone
# in the WHITE half of the board (r > 0, which the renderer puts at the bottom)
# as the WHITE kernel — the very fact section 2 asserts point by point.  So the
# literal string "White" must appear beside THAT point, and "Black" beside the
# other, with the wrong pairings absent.
SETUP_CAP = G.render(S0)["caption"]
WK_POINT = [c for c, st in S0.board.items()
            if M.is_kernel(st[0]) and M.parse_cell(c)[1] > 0][0]
BK_POINT = [c for c, st in S0.board.items()
            if M.is_kernel(st[0]) and M.parse_cell(c)[1] < 0][0]
ok(WK_POINT != BK_POINT and len(S0.board[WK_POINT]) == 1,
   "premise: exactly one kernel stands alone in each half")
ok(("White kernel %s" % WK_POINT) in SETUP_CAP,
   "the caption must call the kernel in the figure's WHITE half White; got %r"
   % SETUP_CAP)
ok(("Black kernel %s" % BK_POINT) in SETUP_CAP,
   "the caption must call the kernel in the figure's BLACK half Black; got %r"
   % SETUP_CAP)
ok(("Black kernel %s" % WK_POINT) not in SETUP_CAP
   and ("White kernel %s" % BK_POINT) not in SETUP_CAP,
   "…and must not name either kernel with the other colour: %r" % SETUP_CAP)

# The MOVE/SOW picker's labels were also unpinned, and they are the only thing
# telling a player which of the two same-cells moves a button plays: a mutant
# that swapped them made every click do the opposite of what it said, invisibly
# to every logic test.  Pin each label to the action its choice suffix performs.
PICK = pos({"0,0": (wd(), wd()), "3,-3": (bk(),)}, to_move=W)
PICK_NAMES = G.render(PICK)["choiceNames"]
ok(set(PICK_NAMES) == {"", "S"}, "the picker must name exactly the two choices")
_kept = G.apply_move(PICK, "0,0>2,0")          # no suffix  -> pile stays whole
_spread = G.apply_move(PICK, "0,0>2,0=S")      # "=S"       -> one piece a point
ok(len(_kept.board["2,0"]) == 2 and "1,0" not in _kept.board,
   "premise: the unsuffixed move keeps the pile together")
ok(len(_spread.board.get("1,0", ())) == 1 and len(_spread.board.get("2,0", ())) == 1,
   "premise: the '=S' move spreads it one piece per point")
ok("move" in PICK_NAMES[""].lower() and "sow" not in PICK_NAMES[""].lower(),
   "the unsuffixed choice must be labelled as MOVING the pile, got %r"
   % PICK_NAMES[""])
ok("sow" in PICK_NAMES["S"].lower() and "move" not in PICK_NAMES["S"].lower(),
   "the '=S' choice must be labelled as SOWING, got %r" % PICK_NAMES["S"])

# reach the far corners and a tall stack for real
rr = random.Random(5)
corners = set(M.cid(c) for c in M.CELLS
              if sum(1 for d in M.DIRS if (c[0] + d[0], c[1] + d[1]) in M.ON_BOARD) == 3)
ok(len(corners) == 6, "a hexhex has 6 corner points, got %d" % len(corners))
hit_corner = hit_tall = 0
for _ in range(60):
    s = G.initial_state()
    while not G.is_terminal(s):
        s = G.apply_move(s, rr.choice(G.legal_moves(s)))
        if corners & set(s.board):
            hit_corner += 1
        if any(len(x) >= 5 for x in s.board.values()):
            hit_tall += 1
        check_render(s, "swept")
ok(hit_corner > 0, "premise: the sweep must actually occupy corner points")
ok(hit_tall > 0, "premise: the sweep must actually build a 5+ stack")

# ---------------------------------------------------------------------------
# 12. describe_move / _kernel_at (not on the legality path)
# ---------------------------------------------------------------------------
rd = random.Random(2)
for _ in range(20):
    s = G.initial_state()
    while not G.is_terminal(s):
        for m in G.legal_moves(s):
            t = G.describe_move(s, m)
            h = len(s.board[m.split(">")[0]])
            ok(("sow" in t) == m.endswith("=S") and ("move" in t) != m.endswith("=S"),
               "describe_move must name the mode: %r for %s" % (t, m))
            ok(t.endswith("x%d" % h), "describe_move must state the height: %r" % t)
        s = G.apply_move(s, rd.choice(G.legal_moves(s)))
ka = G._kernel_at({"0,0": (bd(), wk(), bd()), "1,0": (bk(),)})
ok(ka == {W: ("0,0", 2, 3), B: ("1,0", 1, 1)},
   "_kernel_at must give (cell, 1-based level, height): %s" % (ka,))
both = G._kernel_at({"0,0": (wk(), bd(), bk())})
ok(both == {W: ("0,0", 1, 3), B: ("0,0", 3, 3)},
   "_kernel_at with both kernels in one stack: %s" % (both,))
ok("K1+K3" in G.render(pos({"0,0": (wk(), bd(), bk())}, to_move=W))["caption"]
   or G.render(pos({"0,0": (wk(), bd(), bk())}))["pieces"][0]["label"] == "K1+K3",
   "both kernels in one stack get both marks")

# ---------------------------------------------------------------------------
# 13. INVARIANTS over a long random sweep
# ---------------------------------------------------------------------------
ri = random.Random(9)
kinds = {}
for _ in range(400):
    s = G.initial_state()
    before = G.serialize(s)
    while not G.is_terminal(s):
        lm = G.legal_moves(s)
        ok(len(lm) > 0, "a non-terminal state must have a legal move")
        mv = ri.choice(lm)
        snap = G.serialize(s)
        s2 = G.apply_move(s, mv)
        ok(G.serialize(s) == snap, "apply_move mutated its input state")
        ok(s2.to_move == 1 - s.to_move, "the turn must alternate")
        ok(sum(len(x) for x in s2.board.values()) == 22,
           "pieces are never created or destroyed")
        ok(all(len(x) > 0 for x in s2.board.values()), "no empty stack may persist")
        ok(all(c in M.ON_BOARD for c in map(M.parse_cell, s2.board)),
           "every occupied point must be on the board")
        s = s2
    r = G.returns(s)
    ok(len(r) == 2 and sum(r) == 0, "returns must be a zero-sum pair: %s" % r)
    ok(max(s.reps.values()) <= M.REPEAT_LIMIT,
       "no position may be seen more than %d times" % M.REPEAT_LIMIT)
    ok(len(s.reps) <= s.ply + 1, "the repetition table cannot outgrow the game")
    if s.ply >= M.PLY_CAP:
        k = "ply-cap"
    elif max(s.reps.values()) >= M.REPEAT_LIMIT:
        k = "repetition-draw" if s.drawn else "repetition-win"
    else:
        ok(not s.drawn, "a draw can only come from a repetition/cap end")
        k = "kernel" if HOLDS(s.board, s.winner) else "immobilised"
    kinds[k] = kinds.get(k, 0) + 1
# The PLY_CAP is the one rule NOT in any edition of the sheet, so it must decide
# nothing.  (Threefold repetition IS sourced, so it is allowed to fire.)
ok(kinds.get("ply-cap", 0) == 0,
   "the unsourced ply cap must decide no outcome, fired %d/400 times"
   % kinds.get("ply-cap", 0))
ok(kinds.get("kernel", 0) > 0 and kinds.get("immobilised", 0) > 0,
   "the sweep must reach BOTH published win conditions, got %s" % kinds)

print("amoeba selftest: %d checks, %d failures  (sweep endings %s)"
      % (CHECKS[0], len(FAILS), kinds))
if FAILS:
    sys.exit(1)
