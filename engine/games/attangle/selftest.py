#!/usr/bin/env python3
"""Attangle correctness anchors — pure stdlib, run by tests/test_games.py.

The heavy anchor is the differential against the AbstractPlay `gameslib`
reference implementation (`_diff_ap.py`, manual/one-time): 600 random games per
variant, 82,041 positions, comparing the full legal-move SET, the exact
bottom->top composition of every stack, both stocks, the side to move and the
final winner — 0 mismatches.  What follows re-checks the same rules with
constructed positions and invariants, without needing node.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                              # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
M = sys.modules[type(G).__module__]        # the LIVE module object
W, B = M.WHITE, M.BLACK

FAILS = []


def ok(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


def pos(desc, stock=(9, 9), to_move=W, variant="attangle"):
    """Build a position from {algebraic: (owner, ... bottom->top)}."""
    return M.AState(variant=variant, stock=stock, to_move=to_move,
                    board={M.from_alg(k, variant): tuple(v)
                           for k, v in desc.items()})


def mv(*algs, variant="attangle"):
    return ">".join(M._cid(M.from_alg(a, variant)) for a in algs)


def stacks(s):
    return {M.alg(c, s.variant): st for c, st in s.board.items()}


# --------------------------------------------------------------------------
# 1. Board, voids, opening
# --------------------------------------------------------------------------
ok(len(M.CELLS["attangle"]) == 37, "hexhex-4 board has 37 spaces")
ok(len(M.CELLS["grand"]) == 61, "Grand board (hexhex-5) has 61 spaces")
ok(M.alg((0, 0)) == "d4" and M.alg((0, 0), "grand") == "e5",
   "the centre space is d4 (base) / e5 (grand)")
ok(sorted(M.alg(c) for c in M.VOIDS["attangle"]) == ["d4"],
   "standard Attangle has exactly one void: the centre d4")
ok(sorted(M.alg(c, "grand") for c in M.VOIDS["grand"])
   == ["b3", "c6", "d2", "e5", "f7", "g2", "h4"],
   "Grand Attangle's 7 voids are e5 + b3 c6 d2 f7 g2 h4 "
   "(spielstein setup figure)")
# the 6 non-centre voids are one 6-fold orbit (the figure's pinwheel)
rot = {(-r, q + r) for (q, r) in M.VOIDS["grand"]}
ok(rot == set(M.VOIDS["grand"]),
   "the Grand void set is invariant under 60-degree rotation")

# algebraic naming round-trips on every cell of both boards
for v in ("attangle", "grand"):
    ok(all(M.from_alg(M.alg(c, v), v) == c for c in M.CELLS[v]),
       f"[{v}] axial <-> algebraic naming round-trips on every cell")

s0 = G.initial_state()
ok(s0.board == {} and s0.stock == (18, 18) and s0.to_move == W,
   "base: empty board, 18 pieces each in stock, White moves first")
ok(len(G.legal_moves(s0)) == 36,
   "opening position has 36 legal moves (37 spaces minus the void)")
ok(M._cid((0, 0)) not in G.legal_moves(s0),
   "the void is not a legal placement")
ok(sorted(G.legal_moves(s0))
   == sorted(M._cid(c) for c in M.CELLS["attangle"] if c != (0, 0)),
   "every non-void space is a legal opening placement")

g0 = G.initial_state(options={"variant": "grand"})
ok(g0.stock == (24, 24),
   "grand: 27 pieces each, 3 pre-placed => 24 in hand "
   "(27+27 = 54 = the number of non-void spaces)")
ok(sorted(M.alg(c, "grand") for c, st in g0.board.items() if st == (W,))
   == ["b4", "f2", "g6"], "grand setup: White on b4 f2 g6")
ok(sorted(M.alg(c, "grand") for c, st in g0.board.items() if st == (B,))
   == ["c2", "d7", "h3"], "grand setup: Black on c2 d7 h3")
ok(len(G.legal_moves(g0)) == 48, "grand opening: 48 legal moves (61-7-6)")
ok(M.TARGET["attangle"] == 3 and M.TARGET["grand"] == 5,
   "win at 3 triple stacks (5 in Grand Attangle)")
for _bad in (None, {}, {"variant": "nonsense"}, {"variant": ""}):
    _s = (G.initial_state() if _bad is None else G.initial_state(options=_bad))
    ok(_s.variant == "attangle" and _s.board == {} and _s.stock == (18, 18),
       f"a missing or unknown 'variant' option falls back to standard "
       f"Attangle, never to the bigger board (options={_bad!r})")

# --------------------------------------------------------------------------
# 2. Capture resolution — the three captures of the rulebook figures
# --------------------------------------------------------------------------
# Fig. 2.1  two singles capture a single.  d1 and d5 both see d3: the d5 ray
# crosses the VOID d4, which is explicitly allowed.
p = pos({"d3": (B,), "d1": (W,), "d5": (W,)}, stock=(9, 9))
ok(mv("d1", "d5", "d3") in G.legal_moves(p)
   and mv("d5", "d1", "d3") in G.legal_moves(p),
   "1+1 vs 1 is legal, and a capture ray may cross the void")
q = G.apply_move(p, mv("d1", "d5", "d3"))
ok(stacks(q) == {"d3": (B, W)},
   "1+1 vs 1 leaves a 2-stack: enemy piece at the bottom, mover on top")
ok(q.stock == (10, 9), "the mover takes the top piece back into stock")
ok(G.apply_move(p, mv("d5", "d1", "d3")).board == q.board,
   "naming the attackers in either order gives the same position")

# Fig. 2.2  two singles capture a DOUBLE stack
p = pos({"d3": (W, B), "d1": (W,), "d5": (W,)})
ok(mv("d1", "d5", "d3") in G.legal_moves(p), "1+1 vs 2 is legal")
q = G.apply_move(p, mv("d1", "d5", "d3"))
ok(stacks(q) == {"d3": (W, B, W)}, "1+1 vs 2 leaves a 3-stack (target's pieces "
                                   "at the bottom, mover on top)")

# Fig. 2.3  a single plus a DOUBLE capture a single; the taller attacker lands
# first, so the mover's two pieces end up on top and one goes back to stock
p = pos({"d3": (B,), "d1": (B, W), "d5": (W,)})
ok(mv("d1", "d5", "d3") in G.legal_moves(p)
   and mv("d5", "d1", "d3") in G.legal_moves(p),
   "2+1 vs 1 is legal (a double stack may take part in a capture)")
q = G.apply_move(p, mv("d1", "d5", "d3"))
ok(stacks(q) == {"d3": (B, B, W)},
   "2+1 vs 1 leaves target + the double's pieces, mover on top")
ok(G.apply_move(p, mv("d5", "d1", "d3")).board == q.board,
   "the merge order depends on stack HEIGHT, not on the move string's order")
ok(q.stock == (10, 9), "one piece — always the mover's — returns to stock")

# Every double stack that can exist has an ENEMY piece at the bottom, so the
# taken-back piece is always the mover's.  (A wrong merge order would put the
# mover's piece at the bottom and hand an enemy piece to his stock.)
ok(all(st[0] != st[-1] for st in q.board.values() if len(st) > 1),
   "a captured stack never has the mover's own piece at the bottom")

# --------------------------------------------------------------------------
# 3. What is NOT a capture
# --------------------------------------------------------------------------
def caps(p):
    return [m for m in G.legal_moves(p) if ">" in m]


ok(caps(pos({"d3": (W, B), "d1": (B, W), "d5": (W,)})) == [],
   "2+1 vs 2 is illegal — the survivor would be 4 high")
ok(caps(pos({"d3": (B,), "d1": (B, W), "d5": (B, W)})) == [],
   "2+2 vs 1 is illegal (two double stacks in one capture)")
ok(caps(pos({"d3": (B,), "d1": (B, B, W), "d5": (W,)})) == [],
   "a triple stack cannot move")
ok(caps(pos({"d3": (W, W, B), "d1": (W,), "d5": (W,)})) == [],
   "a triple stack cannot be captured")
ok(caps(pos({"d3": (B,), "d1": (W,), "d2": (B,), "d5": (W,)})) == [],
   "a blocked ray yields no attacker (d2 hides d1)")
ok(caps(pos({"d3": (B,), "d5": (W,), "d6": (W,)})) == [],
   "only the FIRST piece on a ray attacks, so two pieces in line are one "
   "attacker — a capture needs two different directions")
ok(caps(pos({"d3": (W,), "d1": (W,), "d5": (W,)})) == [],
   "you cannot capture your own stack")

# The designer's OWN worked example: spielstein's figure captioned "White or
# black: no captures are possible here."  (Pixel-read off
# https://spielstein.com/images/games/attangle/rules/no-capture.png — white
# discs on e1/c4, white-topped doubles on e2/f5, black singles on d5/e5.)
# It exercises three separate rules at once: e5 has TWO visible white attackers
# but both are doubles (2+2+1 = 5 is too tall); every other enemy stack has
# exactly ONE attacker on its six rays, so a second direction is missing.
NO_CAPTURE_FIG = {"e1": (W,), "e2": (B, W), "f5": (B, W),
                  "c4": (W,), "d5": (B,), "e5": (B,)}
for _side, _name in ((W, "White"), (B, "black")):
    _p = pos(NO_CAPTURE_FIG, stock=(9, 9), to_move=_side)
    ok(caps(_p) == [],
       f"designer's figure 'White or black: no captures are possible here' — "
       f"{_name} has none")
# ...and the reason is the height law, not a missing attacker: relaxing the cap
# would let e2+f5 take e5.  (Guards against the figure passing vacuously.)
_p = pos(NO_CAPTURE_FIG, stock=(9, 9), to_move=W)
ok([M.alg(c) for c in G._attackers(_p, M.from_alg("e5"), W)] == ["e2", "f5"],
   "in that figure White DOES see e5 from two directions — only the "
   "'one double stack' height law forbids the capture")
ok(caps(pos({"d3": (B,), "d1": (W,), "d5": (W,)}, to_move=B)) == [],
   "the opponent's pieces are not yours to move")
# All SIX rays really are scanned, and they are the six hex-lattice directions
# (a wrong entry in DIRS would silently drop one direction and invent another
# that is not a straight line on the board at all).
ok(len(set(M.DIRS)) == 6
   and all((abs(dq) + abs(dr) + abs(dq + dr)) // 2 == 1 for dq, dr in M.DIRS)
   and all((-dq, -dr) in M.DIRS for dq, dr in M.DIRS),
   "DIRS is exactly the six unit hex directions, closed under reversal")
# c4 with a white piece two spaces away down every one of its six rays: all six
# are attackers (the ray pointing at d4 crosses the void), giving 15 pairs.
SIXWAY = {"c4": (B,)}
for _d in M.DIRS:
    SIXWAY[M.alg((0 + 2 * _d[0], 1 + 2 * _d[1]))] = (W,)
p = pos(SIXWAY)
ok(len(SIXWAY) == 7 and len(G._attackers(p, M.from_alg("c4"), W)) == 6,
   "a stack is attackable from all six directions (one attacker per ray)")
ok(len(caps(p)) == 30,
   "six visible attackers give 15 distinct capture pairs (30 strings)")

# three different directions -> three distinct pairs, each listed both ways
p = pos({"d3": (B,), "d1": (W,), "d5": (W,), "c2": (W,)})
ok(len(caps(p)) == 6 and len(set(caps(p))) == 6,
   "three visible attackers give 3 capture pairs (listed in both orders)")
ok(len({str(G.serialize(G.apply_move(p, m))) for m in caps(p)
        if set(m.split(">")[:2]) == {M._cid(M.from_alg("d1")),
                                     M._cid(M.from_alg("d5"))}}) == 1,
   "the two orderings of one capture serialize identically — same move")

# The designer's rule of thumb — "looking at the three pieces (or stacks resp.)
# of a capture move, only one double stack can be involved" — is not a separate
# rule here; it is claimed to be *exactly* what the height law implies.  Prove
# that exhaustively over every combination of participant heights, using the
# engine's own generator rather than restating the arithmetic: for each
# (attacker, attacker, target) height triple, build the position and ask whether
# the capture is offered.
for ha in (1, 2, 3):
    for hb in (1, 2, 3):
        for ht in (1, 2, 3):
            # d1 and d5 both see d3; stacks are built so the tops are right.
            def _stk(h, top):
                return tuple([1 - top] * (h - 1) + [top])
            p = pos({"d3": _stk(ht, B), "d1": _stk(ha, W), "d5": _stk(hb, W)})
            offered = mv("d1", "d5", "d3") in G.legal_moves(p)
            # the rulebook's own formulation
            rulebook = (max(ha, hb, ht) <= 2
                        and [ha, hb, ht].count(2) <= 1)
            ok(offered == rulebook,
               f"height law == 'only one double stack may be involved' for "
               f"attackers {ha}+{hb} onto a {ht}-stack "
               f"(engine {offered}, rulebook {rulebook})")
ok(sorted((a, b, t) for a in (1, 2, 3) for b in (1, 2, 3) for t in (1, 2, 3)
          if mv("d1", "d5", "d3") in G.legal_moves(
              pos({"d3": tuple([W] * (t - 1) + [B]),
                   "d1": tuple([B] * (a - 1) + [W]),
                   "d5": tuple([B] * (b - 1) + [W])})))
   == [(1, 1, 1), (1, 1, 2), (1, 2, 1), (2, 1, 1)],
   "exactly the three captures of the rulebook figures exist (1+1v1, 1+1v2, "
   "1+2v1) and nothing else")

# --------------------------------------------------------------------------
# 4. Winning and losing
# --------------------------------------------------------------------------
# White already holds two triples and completes the third.
p = pos({"a1": (B, B, W), "a2": (B, B, W),
         "d3": (B,), "d1": (B, W), "d5": (W,)}, stock=(5, 5))
ok(not G.is_terminal(p), "two triples is not yet a win")
q = G.apply_move(p, mv("d1", "d5", "d3"))
ok(G.is_terminal(q) and G.returns(q) == [1.0, -1.0],
   "completing the THIRD triple stack wins at once")
ok(G.legal_moves(q) == [], "a won position offers no moves")
ok(G.describe_move(p, mv("d1", "d5", "d3")) == "d1+d5xd3#",
   "describe_move: 'd1+d5xd3#' for the winning capture")
ok(G.describe_move(p, mv("d5", "d1", "d3")) == "d1+d5xd3#",
   "describe_move is independent of the attacker order")
ok(G.describe_move(p, M._cid(M.from_alg("g1"))) == "g1",
   "describe_move: a placement is just the space")

# A triple belongs to whoever owns its TOP piece, and the counts are per player
# (a count that ignored ownership would hand every game to White).
p = pos({"a1": (B, B, W), "a2": (W, W, B), "a3": (B, W, B)})
ok((G._triples(p, W), G._triples(p, B)) == (1, 2),
   "_triples counts only the stacks the player controls")
# Black completes the third BLACK triple while White also holds two: Black wins.
p = pos({"g1": (B, B, W), "g2": (B, B, W), "g3": (W, W, B), "g4": (W, W, B),
         "d3": (W,), "d1": (W, B), "d5": (B,)}, stock=(4, 4), to_move=B)
ok(G._triples(p, W) == 2 and G._triples(p, B) == 2 and not G.is_terminal(p),
   "2-2 in triple stacks is not yet a win for anybody")
q = G.apply_move(p, mv("d1", "d5", "d3"))
ok(stacks(q)[M.alg(M.from_alg("d3"))] == (W, W, B)
   and G.is_terminal(q) and G.returns(q) == [-1.0, 1.0],
   "the player who completes the third triple wins — even when the OPPONENT "
   "holds two triples as well")

# The triple count can only ever go UP: triples cannot move or be captured.
ok(caps(pos({"a1": (B, B, W), "d3": (B, B, W), "d1": (W,), "d5": (W,)})) == [],
   "a completed triple can never be dismantled")

# Grand needs five.
p = pos({"a1": (B, B, W), "a2": (B, B, W), "a3": (B, B, W), "a4": (B, B, W)},
        stock=(1, 3), to_move=W, variant="grand")
ok(not G.is_terminal(p) and G._triples(p, W) == 4,
   "grand: four triple stacks is not yet a win (five are needed)")

# Stock empty and no capture available => the player to move resigns.
p = pos({"a1": (B,), "b1": (B,)}, stock=(0, 4), to_move=W)
ok(G.is_terminal(p) and G.returns(p) == [-1.0, 1.0],
   "empty stock and no capture: the player to move loses")
p = pos({"a1": (B,), "b1": (B,)}, stock=(1, 4), to_move=W)
ok(not G.is_terminal(p) and len(G.legal_moves(p)) == 34,
   "with a piece in stock there is always a placement, so never a stalemate")
# ...and that is a THEOREM, resting on one number per variant: the two stocks
# together exactly fill the non-void spaces, so while any piece is in hand some
# space must be empty.  (This is also the load-bearing check on Grand Attangle's
# 27-pieces-per-player reading of "2 x 27 pieces" — AbstractPlay's 27-in-hand
# *plus* 3 on the board would put 60 pieces on 54 spaces and break it.)
for v in ("attangle", "grand"):
    ok(2 * M.TOTAL[v] == len(M.CELLS[v]) - len(M.VOIDS[v]),
       f"[{v}] both stocks together exactly fill the non-void spaces "
       f"({2 * M.TOTAL[v]} pieces, "
       f"{len(M.CELLS[v]) - len(M.VOIDS[v])} spaces) — so a player holding a "
       f"piece always has a legal placement")
# There is no draw in Attangle: returns is always +1/-1.
ok(all(sorted(G.returns(x)) == [-1.0, 1.0]
       for x in (q, pos({"a1": (B,)}, stock=(0, 4), to_move=W))),
   "every terminal is decisive — Attangle has no draw")

# --------------------------------------------------------------------------
# 5. Invariants over random play (both variants)
# --------------------------------------------------------------------------
# Proven ply ceilings (see rules.md), DERIVED here rather than hard-coded, so
# the number in the test can never drift away from the argument in rules.md.
#
#   * Every capture creates exactly one stack.  Type 2.1 (1+1 onto 1) gives
#     D+1, T+0; types 2.2/2.3 give D-1, T+1.  Both boards start with D = T = 0,
#     so #2.1 = D_final + T_final and #2.2/2.3 = T_final.
#   * A triple is permanent and always belongs to the mover, who wins on his
#     TARGET-th, so T_final <= 2*TARGET - 1.
#   * The pieces on the board bound the stacks: 2*D + 3*T <= 2*TOTAL.
#   * Stock is refilled only by a capture, so placements <= initial stock total
#     + captures.
def _ceilings(variant):
    total = M.TOTAL[variant] * 2                       # pieces in the game
    hand = sum(G.initial_state(options={"variant": variant}).stock)
    caps = max(d + 2 * t                               # #2.1 + #2.2/2.3
               for t in range(2 * M.TARGET[variant])   # T_final: 0..2*TARGET-1
               for d in [(total - 3 * t) // 2])        # D_final
    return caps, (hand + caps) + caps                  # placements + captures


CAPBOUND, BOUND = {}, {}
for _v in ("attangle", "grand"):
    CAPBOUND[_v], BOUND[_v] = _ceilings(_v)
ok(CAPBOUND == {"attangle": 20, "grand": 31}
   and BOUND == {"attangle": 76, "grand": 110},
   f"the termination argument in rules.md gives <= 20/31 captures and "
   f"<= 76/110 plies (got {CAPBOUND}, {BOUND})")

for variant, ngames in (("attangle", 300), ("grand", 120)):
    rnd = random.Random(20060520)
    longest = 0
    most_caps = 0
    win_count = [0, 0]
    reasons = {"triples": 0, "stuck": 0}
    total = M.TOTAL[variant]
    for gi in range(ngames):
        s = G.initial_state(options={"variant": variant})
        n = ncaps = 0
        prev_triples = (0, 0)
        while not G.is_terminal(s):
            # material is conserved: stock + pieces on the board = the set
            for pl in (W, B):
                onboard = sum(st.count(pl) for st in s.board.values())
                if s.stock[pl] + onboard != total:
                    ok(False, f"[{variant}] material invariant broken "
                              f"(seat {pl}: {s.stock[pl]}+{onboard})")
                    break
            # triples never decrease, and never move
            tri = tuple(G._triples(s, pl) for pl in (W, B))
            if tri[0] < prev_triples[0] or tri[1] < prev_triples[1]:
                ok(False, f"[{variant}] a triple stack disappeared")
            prev_triples = tri
            if max(tri) >= M.TARGET[variant]:
                ok(False, f"[{variant}] play continued past the win")
            ms = G.legal_moves(s)
            # captures are always listed in both attacker orders
            cs = [m for m in ms if ">" in m]
            if len(cs) % 2:
                ok(False, f"[{variant}] odd number of capture strings")
            m = rnd.choice(ms)
            if ">" in m:
                ncaps += 1
                # both orderings lead to the identical position
                a, b, t = m.split(">")
                if G.serialize(G.apply_move(s, m)) != \
                        G.serialize(G.apply_move(s, f"{b}>{a}>{t}")):
                    ok(False, f"[{variant}] attacker order changed the result")
            # serialize round-trips
            snap = G.serialize(s)
            if G.serialize(G.deserialize(snap)) != snap:
                ok(False, f"[{variant}] serialize does not round-trip")
            before = G.serialize(s)
            s = G.apply_move(s, m)
            if G.serialize(s) == before:
                ok(False, f"[{variant}] apply_move produced no change")
            n += 1
        longest = max(longest, n)
        most_caps = max(most_caps, ncaps)
        r = G.returns(s)
        ok(sorted(r) == [-1.0, 1.0], f"[{variant}] terminal is decisive")
        win_count[0 if r[0] > r[1] else 1] += 1
        if G._triple_winner(s) is not None:
            reasons["triples"] += 1
        else:
            reasons["stuck"] += 1
            # reached by PLAY, not hand-built: the player to move has an empty
            # stock and no capture, and it is HE who loses.
            ok(s.stock[s.to_move] == 0 and r[s.to_move] == -1.0
               and r[1 - s.to_move] == 1.0,
               f"[{variant}] the player who runs out of moves loses "
               f"(stock {s.stock}, to move {s.to_move}, returns {r})")
    ok(longest <= BOUND[variant],
       f"[{variant}] every random game ends within the proven ply ceiling "
       f"{BOUND[variant]} (longest seen: {longest})")
    ok(reasons["triples"] > 0.9 * ngames,
       f"[{variant}] random games are decided by the third/fifth triple stack, "
       f"not by running out of pieces ({reasons})")
    ok(most_caps <= CAPBOUND[variant],
       f"[{variant}] captures per game stay under the proven ceiling "
       f"{CAPBOUND[variant]} (most seen: {most_caps})")
    # The "empty stock, no capture" loss is a WIN-AS-EVENT branch that a
    # hand-built position cannot fully exercise, so require random play to have
    # actually REACHED it at least once (see also the targeted search below).
    ok(reasons["stuck"] > 0,
       f"[{variant}] random play reaches the 'empty stock, no capture' loss "
       f"at least once ({reasons})")
    print(f"  {variant}: {ngames} random games, longest {longest} plies, "
          f"most captures {most_caps}, wins {win_count}, ends {reasons}")

# --------------------------------------------------------------------------
# 6. purity, rendering, bot eval
# --------------------------------------------------------------------------
p = pos({"d3": (B,), "d1": (W,), "d5": (W,)})
before = G.serialize(p)
G.apply_move(p, mv("d1", "d5", "d3"))
ok(G.serialize(p) == before, "apply_move does not mutate its input state")

for variant in ("attangle", "grand"):
    s = G.initial_state(options={"variant": variant})
    s = G.apply_move(s, G.legal_moves(s)[0])
    spec = G.render(s)
    ok(spec["board"]["type"] == "hex" and spec["board"]["shape"] == "hexagon"
       and spec["board"]["size"] == M.SIZE[variant],
       f"[{variant}] render(): hexhex-{M.SIZE[variant]} board")
    ok(set(spec["board"]["tints"]) == {M._cid(c) for c in M.VOIDS[variant]},
       f"[{variant}] render(): the voids are tinted")
    ok(all(pc["owner"] == pc["stack"][-1] for pc in spec["pieces"]),
       f"[{variant}] render(): a stack is owned by its TOP piece")
    ok(spec["reserve"]["0"]["P"] == s.stock[W]
       and spec["reserve"]["1"]["P"] == s.stock[B],
       f"[{variant}] render(): the reserve trays show the stocks")
    ok(set(spec["board"]["labels"]) == {M._cid(c) for c in M.VOIDS[variant]},
       f"[{variant}] render(): the voids carry the 'x' label")
    ok(spec["board"].get("orientation") is None,
       f"[{variant}] render(): pointy-top hexes, so rows a..g run HORIZONTALLY "
       f"as in the designer's diagrams")
    # a full round trip through the wire format must preserve every field
    ser = G.serialize(s)
    back = G.deserialize(ser)
    ok((back.variant, back.board, back.stock, back.to_move, back.ply, back.last)
       == (s.variant, s.board, s.stock, s.to_move, s.ply, s.last),
       f"[{variant}] serialize/deserialize preserves every field of the state")

# a rendered tall stack keeps its bottom->top composition and its owner
p = pos({"d3": (B, B, W), "d1": (W, B), "a1": (B,)}, stock=(2, 3))
byc = {pc["cell"]: pc for pc in G.render(p)["pieces"]}
ok(byc[M._cid(M.from_alg("d3"))]["stack"] == [B, B, W]
   and byc[M._cid(M.from_alg("d3"))]["owner"] == W
   and byc[M._cid(M.from_alg("d1"))]["stack"] == [W, B]
   and byc[M._cid(M.from_alg("d1"))]["owner"] == B,
   "render(): stacks are listed bottom->top and owned by the TOP piece")

h = G.heuristic(pos({"a1": (B, B, W), "d3": (B,)}))
ok(isinstance(h, list) and len(h) == 2 and h[0] > 0 > h[1],
   "heuristic returns one payoff per seat and prefers the player with a triple")

# force the MCTS rollout cutoff so a malformed heuristic would blow up
from agp.mcts import MCTSBot                                      # noqa: E402
bot = MCTSBot(random.Random(1), iterations=30, max_rollout=4)
ok(bot.select(G, G.initial_state()) in G.legal_moves(G.initial_state()),
   "MCTSBot with max_rollout=4 (heuristic cutoff reached) picks a legal move")

print("attangle selftest:", "FAILED" if FAILS else "all anchors passed")
if FAILS:
    sys.exit(1)
