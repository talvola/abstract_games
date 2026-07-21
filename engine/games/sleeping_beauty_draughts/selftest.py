#!/usr/bin/env python3
"""Standalone correctness self-test for Sleeping Beauty Draughts (Ralf Gering, 1986).

Run from engine/ with:  PYTHONPATH=. python3 games/sleeping_beauty_draughts/selftest.py

PRIMARY ANCHOR: the five composed problems published with full solution move-lists
in Abstract Games magazine, Issue 14 (Summer 2003), p.26.  Each printed solution is
replayed move-for-move against the engine's legal-move generator; the win problems
(1-3) must end in a terminal position with the stated point margin, and the two
repetition studies (4-5) must reproduce the printed anti-loop lock (the forbidden
lady move is genuinely illegal, the played one legal).

Also anchors: promotion-to-beauty (one-lady rule), forced waking on lady-loss, the
backward man-captures-lady leap, jump of joy, serialization round-trip, termination.
Pure stdlib; imports only the agp package / this game.
"""
import random
import sys

from games.sleeping_beauty_draughts.game import SleepingBeautyDraughts, SBState, _key

G = SleepingBeautyDraughts()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def sq(alg):
    return (ord(alg[0]) - 97, int(alg[1]) - 1)


def make(pieces, to_move):
    """pieces = list of (alg, owner, kind). Seeds the anti-loop history as if the
    position had just been reached by a non-lady move (a fresh run)."""
    board = {sq(a): (o, k) for a, o, k in pieces}
    return SBState(board=board, to_move=to_move, hist=(_key(board, to_move),))


def parse(tok):
    """Algebraic solution token -> engine move string.  Handles ':' capture
    chains, glued 2-char squares, the '*' awaken marker and the 'sb' suffix."""
    tok = tok.strip().rstrip("!?").replace("sb", "").replace("*", "")
    parts = tok.split(":") if ":" in tok else [tok[i:i + 2] for i in range(0, len(tok), 2)]
    coords = [sq(p) for p in parts]
    return ">".join(f"{c},{r}" for c, r in coords)


def replay(state, moves, name):
    for i, tok in enumerate(moves):
        mv = parse(tok)
        legal = G.legal_moves(state)
        if mv not in legal:
            fail(f"{name}: ply {i} '{tok}' -> {mv} not legal.\n  legal = {sorted(legal)}")
        state = G.apply_move(state, mv)
    return state


# ---------------------------------------------------------------------------
# Problem 1 — White to move and win by five points.  (R. Gering, 1988)
# ---------------------------------------------------------------------------
p1 = make([("d6", 0, "l"), ("a3", 0, "m"), ("c1", 0, "m"), ("d2", 0, "m"),
           ("a7", 1, "l"), ("d4", 1, "m"), ("a1", 1, "s")], 0)
end = replay(p1, ["d2c3", "d4:b2", "d6c7", "a7b8", "c7:b8"], "P1")
if not G.is_terminal(end):
    fail("P1: final position is not terminal (Black should have no move)")
if G.returns(end) != [1.0, -1.0]:
    fail(f"P1: expected White win, got {G.returns(end)}")
if G.score(end) != 5:
    fail(f"P1: expected win by 5 points, got {G.score(end)} pieces on board")
print("Problem 1 (win by 5)  OK")

# ---------------------------------------------------------------------------
# Problem 2 — White to move and win by one point.  (R. Gering, 2002)
#   h8 is a WHITE sleeping beauty (a beauty on rank 8 can only be White's); it
#   wakes on the last move after White's lady is captured, and sweeps five men.
# ---------------------------------------------------------------------------
p2 = make([("a1", 0, "m"), ("d2", 0, "m"), ("e3", 0, "m"), ("h4", 0, "m"),
           ("e1", 0, "l"), ("h8", 0, "s"),
           ("c7", 1, "m"), ("e7", 1, "m"), ("g7", 1, "m"), ("c5", 1, "m"),
           ("a3", 1, "m"), ("e5", 1, "l")], 0)
end = replay(p2, ["a1b2", "a3:c1sb", "e3f4", "e5:g3", "h4:f2", "c1*:e3:g1",
                  "e1f2", "g1:e3", "h8*:f6:d8:b6:d4:f2"], "P2")
if not G.is_terminal(end) or G.returns(end) != [1.0, -1.0]:
    fail(f"P2: expected terminal White win, got terminal={G.is_terminal(end)} "
         f"returns={G.returns(end)}")
if G.score(end) != 1:
    fail(f"P2: expected win by 1 point, got {G.score(end)} pieces")
print("Problem 2 (win by 1, wake + 5-jump sweep)  OK")

# ---------------------------------------------------------------------------
# Problem 3 — "Gundi's Position": White lady + 2 men beat 1 lady + 4 beauties.
#   White to move and win by one point.  A 37-move shepherd exercising almost
#   every rule: replacement lady-captures, promotion-to-beauty on both sides,
#   four separate wakes, and jumps of joy.  (R. Gering, 2002)
# ---------------------------------------------------------------------------
p3 = make([("a7", 0, "m"), ("c7", 0, "m"), ("d4", 0, "l"),
           ("g7", 1, "l"), ("a1", 1, "s"), ("c1", 1, "s"),
           ("e1", 1, "s"), ("g1", 1, "s")], 0)
p3_moves = [
    "d4e5", "g7h8", "e5f6", "h8g7", "f6:g7", "a1*c3", "g7f6", "c3d4",
    "a7b8sb", "d4c3", "f6e5", "c3b2", "e5d4", "b2a1", "d4c3", "a1b2",
    "c3:a1", "g1*e3", "c7d8sb", "e3d4", "a1b2", "d4e5", "b2c3", "e5f6",
    "c3d4", "f6g7", "d4e5", "g7h8", "e5f6", "h8g7", "f6:g7", "e1*c3",
    "g7f6", "c3b4", "f6e5", "b4a5", "e5d4", "a5b6", "d4c5", "b6:c5",
    "b8*c7", "c5d4", "c7d6", "d4e3", "d6e5", "e3f2", "e5f4", "f2g1",
    "f4g3", "g1h2", "g3:h2", "c1*d2", "h2g3", "d2c3", "g3f4", "c3b4",
    "f4e5", "b4a5", "e5d4", "a5b6", "d4c5", "b6:c5", "d8*c7", "c5d4",
    "c7d6", "d4e3", "d6e5", "e3f2", "e5f4", "f2g1", "f4g3", "g1h2", "g3:h2",
]
end = replay(p3, p3_moves, "P3")
if not G.is_terminal(end) or G.returns(end) != [1.0, -1.0]:
    fail(f"P3: expected terminal White win, got terminal={G.is_terminal(end)} "
         f"returns={G.returns(end)}")
if G.score(end) != 1:
    fail(f"P3: expected win by 1 point, got {G.score(end)} pieces")
print("Problem 3 (37-move shepherd, win by 1)  OK")

# ---------------------------------------------------------------------------
# Problem 4 — "Dungeon Position": White has just played f2e3; Black to move.
#   The anti-loop rule is the point: after the first full-board repetition,
#   Black's h2g1 is forbidden and he must lose a tempo with a man.  (R. Gering)
# ---------------------------------------------------------------------------
p4 = make([("a7", 0, "l"), ("e3", 0, "m"), ("f4", 0, "m"),
           ("h2", 1, "l"), ("d6", 1, "m"), ("c5", 1, "m")], 1)
st = replay(p4, ["h2g1", "a7b8", "g1h2", "b8a7"], "P4")   # first full-board repetition
if parse("h2g1") in G.legal_moves(st):
    fail("P4: h2g1 should be FORBIDDEN after the full-board repetition")
if parse("c5b4") not in G.legal_moves(st):
    fail("P4: c5b4 (the tempo-loss) should be legal")
st = replay(st, ["c5b4", "a7b6"], "P4-tail")
print("Problem 4 (Dungeon: repetition forbids h2g1)  OK")

# ---------------------------------------------------------------------------
# Problem 5 — "Castle Position": White has just played g3f4; Black to move.
#   Zugzwang built entirely on the repetition rule; e1f2 is illegal at the end.
# ---------------------------------------------------------------------------
p5 = make([("d8", 0, "l"), ("f4", 0, "m"), ("c3", 0, "m"),
           ("e1", 1, "l"), ("f6", 1, "m"), ("c5", 1, "m")], 1)
st = replay(p5, ["e1f2", "d8c7", "f2g1", "c7b8", "g1h2", "b8a7", "h2g1", "a7b8"], "P5")
if parse("g1h2") in G.legal_moves(st):
    fail("P5: g1h2 should be FORBIDDEN (recreates a seen position)")
if parse("g1f2") not in G.legal_moves(st):
    fail("P5: g1f2 should be legal (a new position)")
st = replay(st, ["g1f2", "b8a7", "f2e1", "a7b8"], "P5-tail")
if parse("e1f2") in G.legal_moves(st):
    fail("P5: e1f2 should be FORBIDDEN at the end (repetition)")
print("Problem 5 (Castle: repetition zugzwang)  OK")


# ---------------------------------------------------------------------------
# Mechanic tests
# ---------------------------------------------------------------------------
# (a) Promotion-to-beauty: a White man reaching rank 8 while White already holds
#     a lady becomes a frozen beauty, NOT a second lady.
st = make([("b7", 0, "m"), ("a1", 0, "l"), ("h8", 1, "m")], 0)
ns = G.apply_move(st, "1,6>0,7")
if ns.board.get((0, 7)) != (0, "s"):
    fail(f"promotion-to-beauty: a8 should be (0,'s'), got {ns.board.get((0, 7))}")
if sum(1 for v in ns.board.values() if v == (0, "l")) != 1:
    fail("promotion-to-beauty: White must still have exactly one lady")
# same man WITHOUT an existing lady promotes to a lady
st2 = make([("b7", 0, "m"), ("h8", 1, "m")], 0)
ns2 = G.apply_move(st2, "1,6>0,7")
if ns2.board.get((0, 7)) != (0, "l"):
    fail(f"promotion: with no lady, a8 should be (0,'l'), got {ns2.board.get((0, 7))}")
print("promotion to beauty vs lady (one-lady rule)  OK")

# (b) Backward man-captures-lady leap (forward capture of a lady is illegal).
st = make([("d4", 0, "m"), ("c3", 1, "l"), ("e5", 1, "l")], 0)
mvs = set(G.legal_moves(st))
if "3,3>1,1" not in mvs:                       # d4 leaps BACKWARD over c3 -> b2
    fail(f"man should capture the enemy lady backward (d4xb2); legal = {sorted(mvs)}")
if "3,3>5,5" in mvs:                           # forward leap over a lady is illegal
    fail("man illegally allowed to capture a lady FORWARD")
ns = G.apply_move(st, "3,3>1,1")
if (2, 2) in ns.board or ns.board.get((1, 1)) != (0, "m"):
    fail("backward lady-capture did not resolve correctly")
print("man captures lady by backward leap only  OK")

# (c) Forced waking: with no lady but a beauty, every legal move originates at a
#     beauty (you must wake and move her).
st = make([("c1", 1, "s"), ("e1", 1, "s"), ("h8", 1, "m"),
           ("a3", 0, "m")], 1)
mvs = G.legal_moves(st)
if not mvs or any(not (m.startswith("2,0") or m.startswith("4,0")) for m in mvs):
    fail(f"forced-wake: all moves must start at a beauty (c1/e1); got {mvs}")
print("forced wake on lady-loss  OK")

# (d) Jump of joy: a just-woken lady may leap two squares over a vacant,
#     unguarded square; but not over a guarded one.
st = make([("c1", 1, "s"), ("f8", 0, "m")], 1)          # wake c1 -> jump to e3 over d2
if "2,0>4,2" not in set(G.legal_moves(st)):
    fail("jump of joy c1->e3 (over empty, unguarded d2) should be legal")
# now guard d2 with a White man on c3 (c3 leaps backward over d2 -> e1): forbidden
st = make([("c1", 1, "s"), ("c3", 0, "m")], 1)
if "2,0>4,2" in set(G.legal_moves(st)):
    fail("jump of joy over a GUARDED square must be illegal")
print("jump of joy (guarded-square restriction)  OK")

# ---------------------------------------------------------------------------
# Serialization round-trip + termination smoke test
# ---------------------------------------------------------------------------
s = G.initial_state()
d = G.deserialize(G.serialize(s))
if d.board != s.board or d.to_move != s.to_move or d.hist != s.hist:
    fail("serialize/deserialize did not round-trip")
if len(s.board) != 24 or any((c + r) % 2 for (c, r) in s.board):
    fail("opening: expected 24 men on (c+r)-even dark squares")

rng = random.Random(7)
terminated = 0
for g in range(12):
    st = G.initial_state()
    for _ in range(PLY := 800):
        if G.is_terminal(st):
            terminated += 1
            break
        lm = G.legal_moves(st)
        st = G.apply_move(st, rng.choice(lm))
if terminated < 12:
    fail(f"termination smoke: only {terminated}/12 random games terminated")
print("serialization + termination smoke  OK")

print("SELFTEST OK")
sys.exit(0)
