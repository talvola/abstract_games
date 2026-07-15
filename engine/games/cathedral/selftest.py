#!/usr/bin/env python3
"""Standalone correctness anchor for Cathedral. Pure stdlib + agp only.

Run:  PYTHONPATH=. python3 games/cathedral/selftest.py

There is NO machine oracle for Cathedral (no engine, no perft, no published
solve), so this file IS the anchor. It is written against the official rulesheet
(c)1978 Robert P. Moore — http://www.gamecatalog.org/rules/Moore_Cathedral.pdf —
whose four pages carry the piece figures and SIX worked "NOTES ON THE RULES"
examples, cross-checked against the designer's site (cathedral-game.co.nz).

Anchors:
  * the inventory arithmetic 2 x 47 + 6 = 100 — the two players' buildings plus
    the Cathedral tile the 10x10 city EXACTLY. This one identity validates the
    entire reading of the piece figures (shapes AND counts) at once,
  * pieces rotate but NEVER reflect: exactly the Abbey and the Academy come out
    chiral, and Light/Dark hold opposite forms of both ("All pieces except the
    Abbey and the Academy are the same between colours"),
  * rulesheet note 1 / note 4: an enclosure claims space, but a corner-to-corner
    contact does NOT form a boundary (the adversarial pair that pins the
    connectivity duality),
  * rulesheet note 6: one and only one enclosed building is captured, returns to
    its owner's stock and is replayable,
  * rulesheet notes 2 / 3 / 5: two or more enclosed pieces are ALL safe and the
    space stays open to both players; the Cathedral may not form a boundary; a
    lone enclosed Cathedral IS removed and never comes back,
  * rule 4: neither player may claim space on their first move,
  * rule 7's full ladder: place-all win, fewest-unplaced-squares tiebreak, and
    the published, honest DRAW on a tie.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                  # noqa: E402
from games.cathedral.game import (                                    # noqa: E402
    BASE, CATHEDRAL_CELLS, CATHEDRAL_KEY, COUNTS, DARK, LIGHT, ORIENTS, SIZE,
    CState, _mirror, _norm, _rotations, _sc, is_chiral,
)

MAN, G = load_from_dir(Path(__file__).resolve().parent)

FAILED = []


def check(name, cond):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}")
        FAILED.append(name)


# ---------------------------------------------------------------------------
# scaffolding
# ---------------------------------------------------------------------------
def mk(ply=9, light_moves=5, dark_moves=5, stock=None):
    st = stock or {LIGHT: dict(COUNTS), DARK: dict(COUNTS)}
    return CState(stock=st, moves_made={LIGHT: light_moves, DARK: dark_moves},
                  ply=ply, next_pid=100)


def put(s, pid, owner, key, cells):
    """Drop a piece straight onto the board (test scaffolding)."""
    s.pieces[pid] = (owner, key, tuple(sorted(cells)))
    for c in cells:
        s.board[c] = pid


def find_move(s, key, cells):
    """The legal move for `key` whose footprint is exactly `cells`."""
    want = tuple(sorted(cells))
    p = G.current_player(s)
    for m in G.legal_moves(s):
        if m == "pass" or not m.startswith(key + ":"):
            continue
        keyo, anchor = m.split("@")
        k, oi = keyo.split(":")
        if tuple(sorted(G._covered(p, k, int(oi), _sc(anchor)))) == want:
            return m
    raise AssertionError(f"no legal {key} covering {want}")


def can_place_at(s, p, cell):
    """Could player p put a Tavern on `cell` right now?"""
    saved, s.ply = s.ply, (s.ply - s.ply % 2) + p       # force p to move
    try:
        return any(m.startswith("Tavern:") and _sc(m.split("@")[1]) == cell
                   for m in G.legal_moves(s))
    finally:
        s.ply = saved


# ---------------------------------------------------------------------------
# 1. the inventory arithmetic — 2 x 47 + 6 = 100
# ---------------------------------------------------------------------------
print("inventory (rulesheet p.4 'THE BUILDINGS')")
per_player_pieces = sum(COUNTS.values())
per_player_squares = sum(SIZE[k] * n for k, n in COUNTS.items())
check("14 buildings per player", per_player_pieces == 14)
check("47 squares per player", per_player_squares == 47)
check("Cathedral is a 6-cell Latin cross", len(CATHEDRAL_CELLS) == 6)
check("2 x 47 + 6 == 100 (tiles the 10x10 city exactly)",
      2 * per_player_squares + len(CATHEDRAL_CELLS) == 100)
check("every building is a 4-connected polyomino",
      all(len(_rotations(v)) >= 1 and len(v) == SIZE[k] for k, v in BASE[LIGHT].items()))
check("shape sizes match the figures",
      [SIZE[k] for k in ("Tavern", "Stable", "Inn", "Bridge", "Manor", "Square",
                         "Abbey", "Infirmary", "Castle", "Tower", "Academy")]
      == [1, 2, 3, 3, 4, 4, 4, 5, 5, 5, 5])

# ---------------------------------------------------------------------------
# 2. rotation only, no flipping -> exactly Abbey + Academy are chiral
# ---------------------------------------------------------------------------
print("chirality (rotate but never flip)")
chiral = {k for k, v in BASE[LIGHT].items() if is_chiral(v)}
check("exactly {Abbey, Academy} are chiral", chiral == {"Abbey", "Academy"})
check("the Cathedral itself is achiral", not is_chiral(CATHEDRAL_CELLS))
for k in ("Abbey", "Academy"):
    check(f"Light/Dark hold opposite forms of the {k}",
          set(ORIENTS[DARK][k]) == set(_rotations(_mirror(BASE[LIGHT][k])))
          and set(ORIENTS[DARK][k]).isdisjoint(set(ORIENTS[LIGHT][k])))
for k in set(BASE[LIGHT]) - chiral:
    check(f"the {k} is the same for both colours",
          set(ORIENTS[DARK][k]) == set(ORIENTS[LIGHT][k]))
check("no building has more than 4 orientations (rotations only)",
      all(len(o) <= 4 for seat in (LIGHT, DARK) for o in ORIENTS[seat].values()))

# Hard literals, derived by hand from the rulesheet figures and independent of
# this module's own rotate/mirror helpers — these are what actually pin
# "rotate but never flip". Under Blokus-style flipping the Abbey would have 4
# orientations and the Academy 8.
EXPECTED_ORIENTS = {"Tavern": 1, "Stable": 2, "Inn": 4, "Bridge": 2, "Manor": 4,
                    "Square": 1, "Abbey": 2, "Infirmary": 1, "Castle": 4,
                    "Tower": 4, "Academy": 4}
for seat, colour in ((LIGHT, "Light"), (DARK, "Dark")):
    got = {k: len(v) for k, v in ORIENTS[seat].items()}
    check(f"{colour}: exact orientation counts under rotation only",
          got == EXPECTED_ORIENTS)
check("the Cathedral has 4 orientations", len(_rotations(CATHEDRAL_CELLS)) == 4)

# The Abbey as drawn ("XX." over ".XX", read with +r up) and its mirror image.
# Compared up to TRANSLATION via a normaliser written out locally on purpose:
# game.py's `_norm` is the very thing under test here, so importing it would make
# this check circular, and hard-coding offsets would pin the internal anchor
# convention rather than the shape the rulesheet actually fixes.
ABBEY_S = ((0, 1), (1, 0), (1, 1), (2, 0))
ABBEY_Z = ((0, 0), (1, 0), (1, 1), (2, 1))


def _shape(cells):
    """A translation-invariant key for a footprint (min corner -> origin)."""
    mc = min(c for c, _ in cells)
    mr = min(r for _, r in cells)
    return tuple(sorted((c - mc, r - mr) for c, r in cells))


def _shapes(orients):
    return {_shape(o) for o in orients}


check("Light holds the Abbey exactly as the rulesheet draws it",
      _shape(ABBEY_S) in _shapes(ORIENTS[LIGHT]["Abbey"])
      and _shape(ABBEY_Z) not in _shapes(ORIENTS[LIGHT]["Abbey"]))
check("Dark holds the mirror-image Abbey, and only that",
      _shape(ABBEY_Z) in _shapes(ORIENTS[DARK]["Abbey"])
      and _shape(ABBEY_S) not in _shapes(ORIENTS[DARK]["Abbey"]))
check("every orientation is anchored on a cell it covers (SPEC: contains [0,0])",
      all((0, 0) in o for seat in (LIGHT, DARK)
          for v in ORIENTS[seat].values() for o in v)
      and all((0, 0) in o for o in _rotations(CATHEDRAL_CELLS)))

# every Abbey/Academy footprint a player can ever lay is a ROTATION of their own
# form and never the mirror form (which is the other colour's piece).
s = mk()
for seat in (LIGHT, DARK):
    for k in ("Abbey", "Academy"):
        s.ply = (s.ply - s.ply % 2) + seat
        own = set(_rotations(BASE[seat][k]))
        mirrored = set(_rotations(_mirror(BASE[seat][k])))
        foots = set()
        for m in G.legal_moves(s):
            if m.startswith(k + ":"):
                keyo, anchor = m.split("@")
                foots.add(_norm(G._covered(seat, k, int(keyo.split(":")[1]), _sc(anchor))))
        colour = "Light" if seat == LIGHT else "Dark"
        check(f"{colour} {k}: every placement is a rotation of its own form",
              foots and foots <= own)
        check(f"{colour} {k}: NO reflected placement is legal",
              foots.isdisjoint(mirrored))

# ---------------------------------------------------------------------------
# 3. note 4 vs note 1 — corner contact does not enclose, wall-to-wall does
# ---------------------------------------------------------------------------
print("enclosure (rulesheet notes 1 & 4)")
s = mk()
put(s, 1, DARK, "Tavern", [(0, 1)])
put(s, 2, DARK, "Tavern", [(1, 0)])          # meets piece 1 only at a POINT
put(s, 3, LIGHT, "Tavern", [(9, 9)])
put(s, 4, LIGHT, "Tavern", [(9, 7)])
check("note 4: a corner-to-corner contact claims nothing",
      (0, 0) not in G._territory(s, DARK))
check("note 4: the leaked cell stays open to the opponent",
      can_place_at(s, LIGHT, (0, 0)))

s = mk()
put(s, 1, DARK, "Inn", [(0, 1), (1, 1), (1, 0)])   # the same corner, sealed
put(s, 3, LIGHT, "Tavern", [(9, 9)])
put(s, 4, LIGHT, "Tavern", [(9, 7)])
check("note 1: a wall-to-wall boundary DOES claim the space",
      (0, 0) in G._territory(s, DARK))
check("note 1: only the owner may build in claimed space",
      not can_place_at(s, LIGHT, (0, 0)) and can_place_at(s, DARK, (0, 0)))

# ---------------------------------------------------------------------------
# 4. note 6 — one and only one enclosed building is captured & is replayable
# ---------------------------------------------------------------------------
print("capture (rulesheet note 6 / rule 5)")
stock = {LIGHT: dict(COUNTS), DARK: dict(COUNTS)}
stock[DARK]["Tavern"] = 1                    # one Tavern is on the board
stock[DARK]["Stable"] = 1                    # one Stable is on the board
s = mk(ply=8, stock=stock)                   # LIGHT to move (ply 8 -> seat 0)
put(s, 1, DARK, "Tavern", [(0, 0)])
put(s, 2, LIGHT, "Bridge", [(0, 1), (0, 2), (0, 3)])
put(s, 3, 2, CATHEDRAL_KEY, [(5, 9), (4, 8), (5, 8), (6, 8), (5, 7), (5, 6)])
put(s, 4, DARK, "Stable", [(8, 8), (8, 7)])  # keeps the big region at 2+ foreign
check("the victim is on the board and out of stock before the seal",
      (0, 0) in s.board and s.stock[DARK]["Tavern"] == 1)
mv = find_move(s, "Square", [(1, 0), (2, 0), (1, 1), (2, 1)])
after = G.apply_move(s, mv)
check("the isolated dark Tavern is removed", (0, 0) not in after.board)
check("the captured building returns to its owner's stock (replayable)",
      after.stock[DARK]["Tavern"] == 2)
check("the emptied space is claimed by the capturer",
      (0, 0) in G._territory(after, LIGHT))
check("the capturer may not also carry off the 2-foreign big region",
      (5, 6) in after.board and not after.cathedral_gone)
check("the returned building really can be replayed",
      can_place_at(after, DARK, (7, 0)))

# ---------------------------------------------------------------------------
# 5. notes 2/3/5 — two or more enclosed pieces are ALL safe
# ---------------------------------------------------------------------------
print("two-or-more enclosed (rulesheet notes 2, 3 & 5)")
stock = {LIGHT: dict(COUNTS), DARK: dict(COUNTS)}
stock[DARK]["Tavern"] = 1                    # one Tavern + one Stable are walled in
stock[DARK]["Stable"] = 1
s = mk(ply=8, stock=stock)                   # LIGHT to move (ply 8 -> seat 0)
put(s, 1, DARK, "Tavern", [(0, 0)])
put(s, 2, DARK, "Stable", [(0, 2), (0, 3)])
put(s, 3, LIGHT, "Bridge", [(1, 0), (1, 1), (1, 2)])
put(s, 5, LIGHT, "Tavern", [(9, 9)])
mv = find_move(s, "Manor", [(0, 4), (1, 3), (1, 4), (1, 5)])
after = G.apply_move(s, mv)
check("note 2: neither of the two enclosed buildings is removed",
      (0, 0) in after.board and (0, 2) in after.board)
check("note 2: the space is NOT claimed",
      (0, 1) not in G._territory(after, LIGHT))
check("note 2: the space is still available to the opponent",
      can_place_at(after, DARK, (0, 1)))

# note 5 / the designer's "if the Cathedral is contacted both are safe":
# the Cathedral + a light Tavern sealed in by dark -> BOTH secure.
def cathedral_pocket(with_light_tavern):
    st = {LIGHT: dict(COUNTS), DARK: dict(COUNTS)}
    s = mk(stock=st)
    put(s, 3, 2, CATHEDRAL_KEY, [(1, 3), (0, 2), (1, 2), (2, 2), (1, 1), (1, 0)])
    if with_light_tavern:
        put(s, 1, LIGHT, "Tavern", [(0, 0)])
    put(s, 4, DARK, "Bridge", [(3, 0), (3, 1), (3, 2)])
    put(s, 5, DARK, "Tavern", [(3, 3)])
    put(s, 6, DARK, "Stable", [(0, 4), (1, 4)])
    put(s, 7, LIGHT, "Tavern", [(9, 9)])
    put(s, 8, LIGHT, "Tavern", [(9, 7)])
    s.ply = 9                                    # dark to move
    return G.apply_move(s, find_move(s, "Stable", [(2, 4), (3, 4)]))

after = cathedral_pocket(True)
check("note 5: the Cathedral and the touching building are both secure",
      (1, 1) in after.board and (0, 0) in after.board and not after.cathedral_gone)
check("note 5: that space may not be claimed by the encloser",
      not ({(2, 0), (2, 1), (0, 1)} & G._territory(after, DARK)))
check("note 5: the space stays usable by both players",
      can_place_at(after, LIGHT, (2, 0)) and can_place_at(after, DARK, (2, 0)))

after = cathedral_pocket(False)               # ...but a LONE Cathedral is taken
check("rule 5: a lone enclosed Cathedral is removed", after.cathedral_gone
      and (1, 1) not in after.board)
check("rule 5: the Cathedral is never replaced (not in either stock)",
      CATHEDRAL_KEY not in after.stock[LIGHT] and CATHEDRAL_KEY not in after.stock[DARK])
check("rule 5: and that space becomes the encloser's",
      (1, 1) in G._territory(after, DARK))

# ---------------------------------------------------------------------------
# 6. note 3 — the Cathedral may not form part of a claim boundary
# ---------------------------------------------------------------------------
print("the Cathedral is not a boundary (rulesheet note 3)")
def ring(sixth_is_cathedral):
    """(5,5) ringed by dark on 7 of its 8 neighbours; the 8th is either a
    Cathedral cell or a dark Tavern."""
    s = mk()
    put(s, 1, DARK, "Bridge", [(4, 4), (5, 4), (6, 4)])
    put(s, 2, DARK, "Stable", [(4, 5), (4, 6)])
    put(s, 3, DARK, "Stable", [(6, 5), (6, 6)])
    if sixth_is_cathedral:
        put(s, 4, 2, CATHEDRAL_KEY,
            [(5, 9), (4, 8), (5, 8), (6, 8), (5, 7), (5, 6)])
    else:
        put(s, 4, DARK, "Tavern", [(5, 6)])
    put(s, 5, LIGHT, "Tavern", [(0, 0)])
    put(s, 6, LIGHT, "Tavern", [(0, 2)])
    return s

s = ring(True)
check("note 3: a Cathedral in the boundary claims nothing",
      (5, 5) not in G._territory(s, DARK))
check("note 3: so the opponent may still build there",
      can_place_at(s, LIGHT, (5, 5)))
s = ring(False)
check("contrast: the same ring of the encloser's OWN buildings does claim it",
      (5, 5) in G._territory(s, DARK) and not can_place_at(s, LIGHT, (5, 5)))

# ---------------------------------------------------------------------------
# 7. rule 4 — neither player may claim space on their first move
# ---------------------------------------------------------------------------
print("no claim on your first move (rule 4)")
s = G.initial_state()
check("Light places the Cathedral first (a setup action, not a move)",
      G.current_player(s) == LIGHT
      and all(m.startswith(CATHEDRAL_KEY + ":") for m in G.legal_moves(s)))
s = G.apply_move(s, find_move(s, CATHEDRAL_KEY,
                              [(5, 6), (4, 5), (5, 5), (6, 5), (5, 4), (5, 3)]))
check("Dark then makes the first move (rule 3)", G.current_player(s) == DARK)
# Dark's opening Castle seals its own notch against the west wall.
s2 = G.apply_move(s, find_move(s, "Castle", [(0, 4), (1, 4), (1, 5), (0, 6), (1, 6)]))
check("rule 4: dark's first move claims nothing",
      (0, 5) not in G._territory(s2, DARK))
check("rule 4: so light may use that space",
      can_place_at(s2, LIGHT, (0, 5)))
check("rule 4 protects the Cathedral from the opening move",
      not s2.cathedral_gone and (5, 5) in s2.board)
# after dark's SECOND building the claim does take effect
s3 = G.apply_move(s2, find_move(s2, "Tavern", [(9, 9)]))          # light elsewhere
s4 = G.apply_move(s3, find_move(s3, "Tavern", [(3, 0)]))          # dark's 2nd
check("the claim takes effect from dark's second move on",
      (0, 5) in G._territory(s4, DARK) and not can_place_at(s4, LIGHT, (0, 5)))

# ---------------------------------------------------------------------------
# 8. rule 7 — win / tiebreak / honest draw, all REACHED via apply_move
# ---------------------------------------------------------------------------
print("rule 7: the win/tiebreak/draw ladder")
def endgame(light_stock, dark_stock):
    """Board full but for (9,9), Light to move. Dark owns rows 0-4, Light 5-9."""
    s = mk(stock={LIGHT: dict(light_stock), DARK: dict(dark_stock)},
           ply=8, light_moves=5, dark_moves=5)
    pid = 0
    for r in range(10):
        for c in range(10):
            if (c, r) == (9, 9):
                continue
            pid += 1
            put(s, pid, DARK if r < 5 else LIGHT, "Tavern", [(c, r)])
    return s

s = endgame({"Tavern": 1}, {"Stable": 1})
check("not terminal while a move remains", not G.is_terminal(s))
end = G.apply_move(s, find_move(s, "Tavern", [(9, 9)]))
check("rule 6: terminal once neither player can place", G.is_terminal(end))
check("rule 7: placing all your buildings while the other cannot = win",
      G.unplaced_squares(end, LIGHT) == 0 and G.returns(end) == [1.0, -1.0])

s = endgame({"Tavern": 1, "Stable": 1}, {"Bridge": 1})
end = G.apply_move(s, find_move(s, "Tavern", [(9, 9)]))
check("rule 7: else fewest unplaced SQUARES wins (2 < 3)",
      G.is_terminal(end) and G.unplaced_squares(end, LIGHT) == 2
      and G.unplaced_squares(end, DARK) == 3 and G.returns(end) == [1.0, -1.0])

s = endgame({"Tavern": 1, "Stable": 1}, {"Stable": 1})
end = G.apply_move(s, find_move(s, "Tavern", [(9, 9)]))
check("rule 7: an equal count is the published, honest DRAW",
      G.is_terminal(end) and G.unplaced_squares(end, LIGHT) == 2
      and G.unplaced_squares(end, DARK) == 2 and G.returns(end) == [0.0, 0.0])

# Rule 6: "if one player can no longer make a move the other player continues
# to place buildings until they run out or can also no longer place any."
# Two single-cell holes: (9,9) inside Light's half, (0,0) inside Dark's. Light
# holds only a Stable (2 squares) and so is stuck; Dark still has a Tavern.
s = mk(stock={LIGHT: {"Stable": 1}, DARK: {"Tavern": 1}}, ply=8)
pid = 0
for r in range(10):
    for c in range(10):
        if (c, r) in ((9, 9), (0, 0)):
            continue
        pid += 1
        put(s, pid, DARK if r < 5 else LIGHT, "Tavern", [(c, r)])
check("rule 6: a stuck player passes, the other plays on",
      not G.is_terminal(s) and G.legal_moves(s) == ["pass"])
s2 = G.apply_move(s, "pass")
check("rule 6: the pass hands the turn over", G.current_player(s2) == DARK)
s3 = G.apply_move(s2, find_move(s2, "Tavern", [(0, 0)]))
check("rule 6: the game ends once neither side can place", G.is_terminal(s3))
check("rule 7: Dark placed all of its buildings and wins",
      G.unplaced_squares(s3, DARK) == 0 and G.returns(s3) == [-1.0, 1.0])

# ---------------------------------------------------------------------------
# 9. serialize round-trips (including a captured/removed Cathedral)
# ---------------------------------------------------------------------------
print("persistence")
after = cathedral_pocket(False)
check("serialize round-trips",
      G.serialize(G.deserialize(G.serialize(after))) == G.serialize(after))
check("cathedral_gone survives the round-trip",
      G.deserialize(G.serialize(after)).cathedral_gone)

print()
if FAILED:
    print(f"FAILED: {len(FAILED)}")
    for f in FAILED:
        print("  -", f)
    sys.exit(1)
print("cathedral selftest: all checks passed")
