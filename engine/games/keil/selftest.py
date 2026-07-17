"""Keil selftest — anchors from the designer's ruleset (senseis.xmp.net/?Keil,
word-for-word identical to his BGG description) and his lifein19x19 rules
thread. Pure stdlib; run with PYTHONPATH=engine from the repo, or PYTHONPATH=.
from engine/:  python3 games/keil/selftest.py
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
sys.path.insert(0, str(PKG))
import game as K  # noqa: E402

checks = 0


def ok(cond, msg):
    global checks
    assert cond, msg
    checks += 1


def start(size, komi=6, side="white"):
    s = G.initial_state(options={"size": size})
    s = G.apply_move(s, f"komi={komi}")
    return G.apply_move(s, side)


# ---------------------------------------------------------------- geometry
# The SL sample game: "Black won by 0.5, with 67 points to White's 66.5. Komi
# was 6; the button was taken by White" — board points owned = 67 + (66.5 -
# 6 - 0.5) = 127, exactly a hexhex of side 7. Anchors our board to the
# designer's.
ok(len(K._geom(7)[0]) == 127, "hexhex-7 has 127 points (SL sample game)")
ok(len(K._geom(5)[0]) == 61 and len(K._geom(4)[0]) == 37, "point counts")
cells, cs, nbrs, common = K._geom(3)
ok(all(1 <= len(common[k]) <= 2 for k in common), "1-2 witnesses per pair")

# ------------------------------------------------------------ linking rule
# A lone stone in the open is linked to all 6 adjacent empties (empty witness).
b = {(0, 0): K.BLACK}
grp = K._group(b, (0, 0), nbrs, common)
ok(len(K._liberties(b, grp, nbrs, common)) == 6, "lone stone: 6 liberties")

# Two adjacent same-colour stones with empty witnesses are NOT linked; a third
# same-colour stone adjacent to both links them (designer, L19: stones "are
# not permanently connected until there is a third, same-color stone adjacent
# to both" — under the current same-type wording the third stone IS the link).
b = {(0, 0): K.BLACK, (1, 0): K.BLACK}
ok(not K._linked(b, (0, 0), (1, 0), common), "adjacent pair alone: cut")
ok(K._group(b, (0, 0), nbrs, common) == {(0, 0)}, "two groups")
b[(0, 1)] = K.BLACK  # (0,1) is a witness of the (0,0)-(1,0) pair
ok(K._group(b, (0, 0), nbrs, common) == {(0, 0), (1, 0), (0, 1)},
   "third stone connects the pair")

# CROSSCUT (the game's raison d'être — "Keil preserves crosscuts and ko"):
# black (0,0),(1,0) with white on both witnesses (0,1),(1,-1): four stones,
# four mutually-cut groups, all alive.
b = {(0, 0): K.BLACK, (1, 0): K.BLACK, (0, 1): K.WHITE, (1, -1): K.WHITE}
ok(not K._linked(b, (0, 0), (1, 0), common), "crosscut: blacks cut")
ok((1, -1) not in nbrs[(0, 1)], "crosscut: whites not even adjacent")
for st in b:
    g2 = K._group(b, st, nbrs, common)
    ok(g2 == {st}, "crosscut: singleton group")
    ok(K._has_lib(b, g2, nbrs, common), "crosscut: each stone alive")

# ------------------------------------------------- capture without filling
# Liberties are LINKS, so a corner stone dies to just TWO enemy stones (its
# remaining empty neighbour's only witness turns enemy) — impossible in plain
# hex Go. Reached via apply_move (win-as-event hygiene).
s = start(3, komi=0)
s = G.apply_move(s, "2,0")      # Black corner
s = G.apply_move(s, "1,0")      # White
s = G.apply_move(s, "-2,0")     # Black elsewhere
s = G.apply_move(s, "2,-1")     # White: captures the corner stone
ok((2, 0) not in s.board, "corner stone captured by two stones")
ok(s.board[(1, 0)] == K.WHITE and s.board[(2, -1)] == K.WHITE, "captors stay")

# ------------------------------------------------------------------ suicide
# White ring around the centre; Black may not play the centre (0 liberties, no
# capture).
s = start(4, komi=0)
ring = ["1,0", "-1,0", "0,1", "0,-1", "1,-1", "-1,1"]
far = ["-3,0", "-3,1", "-3,2", "-3,3", "-2,-1", "-1,-2"]
for bmv, wmv in zip(far, ring):
    s = G.apply_move(s, bmv)
    s = G.apply_move(s, wmv)
ok(all(K._cell(m) in s.board for m in ring), "ring built")
ok("0,0" not in G.legal_moves(s), "suicide excluded from legal_moves")
try:
    G.apply_move(s, "0,0")
    ok(False, "suicide must raise")
except ValueError:
    ok(True, "suicide raises")

# --------------------------------------------------------------------- ko
# "It preserves ... ko": a real single-stone ko found in self-play (size 4,
# komi 6, chooser keeps White; fixed sequence, deterministic replay). White's
# 20th move (3,-1) captures the black stone at (3,0); Black's immediate
# recapture at 3,0 would recreate the position at the end of Black's previous
# turn -> illegal; after a threat exchange elsewhere it is legal and captures
# exactly the white ko stone.
seq = ["1,-1", "1,2", "-3,2", "0,-1", "3,0", "3,-1", "2,-2", "button",
       "2,-1", "2,1", "-1,-1", "0,0", "-1,2", "1,-2", "-2,2", "1,1",
       "-2,0", "0,3", "-2,1"]
s = start(4, komi=6)
for mv in seq:
    s = G.apply_move(s, mv)
before = dict(s.board)
ok(before[(3, 0)] == K.BLACK, "ko: black stone on 3,0")
s = G.apply_move(s, "3,-1")     # White captures it
ok((3, 0) not in s.board and s.board[(3, -1)] == K.WHITE, "ko capture")
ok(len(set(before) - set(s.board)) == 1, "ko: exactly one stone captured")
ok("3,0" not in G.legal_moves(s), "immediate recapture blocked (repetition)")
norep = {m for m, _ in G._legal_placements(s, ignore_repetition=True)}
ok("3,0" in norep, "recapture blocked ONLY by the repetition rule")
try:
    G.apply_move(s, "3,0")
    ok(False, "ko recapture must raise")
except ValueError:
    ok(True, "ko recapture raises")
s = G.apply_move(s, "-3,0")     # Black: ko threat elsewhere
s = G.apply_move(s, "-1,-2")    # White answers
ok("3,0" in G.legal_moves(s), "recapture legal after the exchange")
b4 = dict(s.board)
s = G.apply_move(s, "3,0")
ok(set(b4) - set(s.board) == {(3, -1)}, "delayed recapture takes the ko stone")

# ------------------------------------------------------------------ scoring
cells3 = cells
def score(board):
    return K._score_points(board, cells3, nbrs, common)

ok(score({}) == (0, 0), "stoneless territory is neutral (empty board)")
ok(score({(0, 0): K.BLACK}) == (19, 0), "lone stone owns the board")
ok(score({c: K.BLACK for c in
          [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]}) == (19, 0),
   "ring: centre eye + outside all Black")
ok(score({(0, 0): K.BLACK, (2, 0): K.WHITE}) == (1, 1),
   "contested board: all territories neutral")

# ------------------------------------------------- protocol, button, ending
s0 = G.initial_state(options={"size": 3})
ok(G.current_player(s0) == 0, "seat 0 names komi")
ok(G.legal_moves(s0) == [f"komi={k}" for k in range(13)], "komi offers 0-12")
ok(not G.is_terminal(s0), "protocol states not terminal")
ok("Black" not in G.render(s0)["caption"],
   "komi-phase caption must not pre-assign colours (sides not chosen yet)")
s1 = G.apply_move(s0, "komi=6")
ok(G.current_player(s1) == 1 and G.legal_moves(s1) == ["black", "white"],
   "seat 1 chooses sides")
# swap: seat 1 takes Black and moves first; empty-board button game -> the
# button half point decides (komi 0), and returns are seat-oriented.
s = G.initial_state(options={"size": 3})
s = G.apply_move(s, "komi=0")
s = G.apply_move(s, "black")
ok(G.current_player(s) == 1, "after swap, Black = seat 1 moves first")
ok("pass" not in G.legal_moves(s) and "button" in G.legal_moves(s),
   "passing illegal until the button is taken")
s = G.apply_move(s, "button")
ok(s.button_taken and s.button_holder == K.BLACK, "button taken by Black")
ok("button" not in G.legal_moves(s) and "pass" in G.legal_moves(s),
   "button gone, passing now legal")
s = G.apply_move(s, "pass")
s = G.apply_move(s, "pass")
ok(G.is_terminal(s), "double pass ends the game")
ok(G._final_scores(s) == (0.5, 0.0), "empty board: only the button scores")
ok(G.returns(s) == [-1.0, 1.0], "swap orientation: seat 1 (Black) wins")

# ------------------------------------------- machinery invariants (random)
# Scoped legal_moves == full-board resolve; every post-placement state has no
# liberty-less enemy group; button-taken games never tie (whole komi + button).
for seed in range(3):
    rng = random.Random(seed)
    s = start(3, komi=rng.choice([0, 6]))
    while not G.is_terminal(s):
        cl, _, nb2, cm2 = K._geom(s.size)
        scoped = {m for m, _ in G._legal_placements(s)}
        hist = G._hist(s, s.to_move)
        for p in cl:
            if p in s.board:
                continue
            b2, _d, okk = K._resolve_full(s.board, p, s.to_move, cl, nb2, cm2)
            legal = okk and G._pos_key(b2, cl, s.button_taken) not in hist
            ok((f"{p[0]},{p[1]}" in scoped) == legal, "scoped == full resolve")
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        if isinstance(s.last, tuple):
            # after M's placement every enemy-of-M group has a liberty;
            # enemy of the mover == the colour now to move.
            _gid, groups = K._enemy_groups(s.board, s.to_move, cl, nb2, cm2)
            for grp in groups:
                ok(K._has_lib(s.board, grp, nb2, cm2),
                   "no dead enemy group survives a placement")
    ok(s.button_taken, "random game: button was taken before the end")
    bsc, wsc = G._final_scores(s)
    ok(bsc != wsc and abs(bsc - wsc) % 1 == 0.5,
       "whole komi + button: no tie possible")
    ok(G.returns(s) != [0.0, 0.0], "no fabricated draws")

# ------------------------------------------------------------ serialization
s = start(4, komi=6)
rng = random.Random(7)
for _ in range(25):
    if G.is_terminal(s):
        break
    s = G.apply_move(s, rng.choice(G.legal_moves(s)))
d1 = G.serialize(s)
d2 = G.serialize(G.deserialize(json.loads(json.dumps(d1))))
ok(d1 == d2, "serialize round-trips (with histories)")

# ------------------------------------------------------------- heuristic
h = G.heuristic(s)
ok(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
   "heuristic: per-seat zero-sum list")
ok(G.heuristic(G.initial_state(options={"size": 4})) == [0.0, 0.0],
   "heuristic neutral during the komi pie")

print(f"keil selftest: all {checks} checks passed")
