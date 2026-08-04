"""heXentafl correctness anchors (pure stdlib; `agp` + this package only).

The anchors, and what each one is for:

* **Setup transcription** -- the rule sheet's two setup figures, cell by cell,
  including the 4x4 board's ONE asymmetry (defenders on every *other* neighbour
  of the throne).  That asymmetry is what makes a wrong board orientation
  observable at all: it cuts the starting position's symmetry group from the
  board's full D6 down to D3, so a 60-degree rotation of the coordinate map
  changes the game.  On the 5x5 board the setup IS D6-symmetric, so no test can
  see an orientation error there -- that is a lemma, not a gap.
* **Opening move counts** -- 36/33 (4x4) and 42/78 (5x5), computed independently
  by AbstractPlay's `hexentafl.ts`.
* **The four capture figures**, replayed as predicates, each with the PREMISE it
  relies on asserted separately and with the wrong readings it is meant to
  exclude listed explicitly.
* **A decisive result outranks the draw counters** -- every decisive terminal is
  re-scored with the ply counter and the repetition table poisoned.
* **Serialisation** compares STATE OBJECTS over whole games (`serialize` alone
  cannot see a dropped field), plus the exact key set and a JSON round trip.
* **render() bounds for every board size**, from positions reached through
  `apply_move` with pieces on the rim.
* **Seat naming pinned outside the engine** -- to the owner of the piece on a
  specific printed hex, and to the winner of a game actually played out.
"""

import json
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                  # noqa: E402
from games.hexentafl.game import (                                    # noqa: E402
    ATTACKERS, CELLS, CORNERS, DEFENDERS, DIRS, HexTaflState, REPS_DRAW,
    SEAT_NAMES, SIZES, THRONE, cid, epoch_plies, max_men, on_board, owner,
    ply_cap, pos_key, start_board,
)

MAN, G = load_from_dir(Path(__file__).resolve().parent)

_checks = 0


def ok(cond, msg):
    global _checks
    _checks += 1
    assert cond, msg


def state(board, to_move, size=4):
    return HexTaflState(board=dict(board), to_move=to_move, size=size,
                        reps={pos_key(board, to_move): 1})


def caps(board, to, player, size=4):
    return sorted(G.captures(dict(board), to, player, size))


# --------------------------------------------------------------- geometry ---

def test_geometry():
    ok(len(CELLS[4]) == 37 and len(CELLS[5]) == 61, "hexhex cell counts")
    for n in SIZES:
        R = n - 1
        ok(CORNERS[n] == {(R * dq, R * dr) for dq, dr in DIRS}, "corners")
        ok(len(CORNERS[n]) == 6, "six corners")
        ok(all(on_board(c, n) for c in CORNERS[n]), "corners on board")
        # DIRS is a clockwise cycle whose index+3 is the opposite direction
        for i, (dq, dr) in enumerate(DIRS):
            o = DIRS[(i + 3) % 6]
            ok((dq + o[0], dr + o[1]) == (0, 0), "DIRS[i+3] is opposite DIRS[i]")


def test_corner_lemma():
    """Every corner has exactly three on-board neighbours and they are
    cyclically CONSECUTIVE, so no opposite pair exists there at all -- which is
    why the sheet needs a separate corner clause.  For a mover standing on one
    of them, at most one of the two flanking cells the clause looks at is on the
    board, so the clause can never double-count a victim; and the mover standing
    on the *inward* neighbour has zero flanks, i.e. it can never capture."""
    for n in SIZES:
        for c in CORNERS[n]:
            onb = {i for i in range(6)
                   if on_board((c[0] + DIRS[i][0], c[1] + DIRS[i][1]), n)}
            ok(len(onb) == 3, "corner has 3 on-board neighbours")
            ok(any(all((st + d) % 6 in onb for d in range(3)) for st in onb),
               "corner's on-board neighbours are consecutive")
            ok(not any((i + 3) % 6 in onb for i in onb),
               "corner has no opposite pair on the board")
            seen = {}
            for i in range(6):
                mover = (c[0] - DIRS[i][0], c[1] - DIRS[i][1])
                if not on_board(mover, n):
                    continue
                fl = [j for j in ((i - 1) % 6, (i + 1) % 6)
                      if on_board((c[0] + DIRS[j][0], c[1] + DIRS[j][1]), n)]
                ok(len(fl) <= 1, "at most one flank on board -> no double count")
                seen[len(fl)] = seen.get(len(fl), 0) + 1
            ok(seen == {1: 2, 0: 1},
               "the two RIM movers have one flank; the INWARD mover has none")


# ------------------------------------------------------- setup transcription --

def test_setup_4():
    """HOW TO PLAY figure: King on the red central hex; three black discs on the
    throne's N, SE and SW neighbours; six white discs on the six corners."""
    b = start_board(4)
    ok(b[THRONE] == "K", "King on the throne")
    ok({c for c, p in b.items() if p == "D"} == {DIRS[0], DIRS[2], DIRS[4]},
       "defenders on N, SE, SW of the throne")
    ok({c for c, p in b.items() if p == "A"} == set(CORNERS[4]),
       "six attackers on the six corners")
    ok(len(b) == 10, "10 pieces")
    # the asymmetry: the OTHER three neighbours are empty.  This is the single
    # assertion a 60-degree rotation of the board breaks.
    ok(all(DIRS[i] not in b for i in (1, 3, 5)),
       "the other three throne neighbours are EMPTY (the figure's asymmetry)")
    # each defender stands on the line from the throne to a corner
    for i in (0, 2, 4):
        far = (3 * DIRS[i][0], 3 * DIRS[i][1])
        ok(far in CORNERS[4] and b[far] == "A",
           "each defender points at a corner held by an attacker")


def test_setup_5():
    """5x5 figure: defenders on ALL six neighbours; attackers on the six corners
    of the board and on the six corners of the inner 4x4 hexagon."""
    b = start_board(5)
    ok(b[THRONE] == "K", "King on the throne")
    ok({c for c, p in b.items() if p == "D"} == set(DIRS), "six defenders ring the throne")
    inner = {(3 * dq, 3 * dr) for dq, dr in DIRS}
    ok({c for c, p in b.items() if p == "A"} == set(CORNERS[5]) | inner,
       "12 attackers: outer corners + inner-hexagon corners")
    ok(len(b) == 19, "19 pieces")
    ok(inner == CORNERS[4], "the inner ring is exactly the 4x4 board's corners")


def test_opening_counts():
    """Independently computed by AbstractPlay gameslib's hexentafl.ts."""
    for size, defenders, attackers in ((4, 36, 33), (5, 42, 78)):
        for first, want in (("defenders", defenders), ("attackers", attackers)):
            s = G.initial_state({"size": size, "first_player": first})
            ok(len(G.legal_moves(s)) == want,
               f"size {size} {first} opening count {len(G.legal_moves(s))} != {want}")


def test_seat_names_pinned_outside_the_engine():
    """SEAT_NAMES is pinned to the printed figure, never to the engine's own
    derived naming: the side holding the King on the central throne is the side
    that must escort him out, and the side on the corners is the besieging one."""
    for n in SIZES:
        b = start_board(n)
        ok(SEAT_NAMES[owner(b[THRONE])] == "Defenders", "throne piece = Defenders")
        corner = (n - 1) * DIRS[0][0], (n - 1) * DIRS[0][1]
        ok(SEAT_NAMES[owner(b[corner])] == "Attackers", "corner piece = Attackers")
    ok(SEAT_NAMES[DEFENDERS] == "Defenders" and SEAT_NAMES[ATTACKERS] == "Attackers",
       "seat constants agree with the names")


# ----------------------------------------------------------- the figures ----

def test_fig_king_capture():
    """"white moves into position to surround the King and capture it".  The
    King stands off the throne at (-2,0); one attacker is already at (-1,-1) and
    the second arrives at (-3,1).  Those two cells are OPPOSITE about the King
    -- assert that premise, because a figure read as "any two sides" would pass
    the outcome assertion while being wrong."""
    k = (-2, 0)
    a1, a2 = (-1, -1), (-3, 1)
    i = DIRS.index((a1[0] - k[0], a1[1] - k[1]))
    j = DIRS.index((a2[0] - k[0], a2[1] - k[1]))
    ok((i + 3) % 6 == j, "the figure's two attackers are on OPPOSITE sides")
    b = {k: "K", a1: "A", a2: "A", (-1, 0): "D", (0, -1): "D"}
    ok(caps(b, a2, ATTACKERS) == [k], "King off the throne dies to a plain sandwich")
    ok(caps(b, a1, ATTACKERS) == [k], "...from either side")
    ok(caps({k: "K", a2: "A", (-1, 0): "D"}, a2, ATTACKERS) == [],
       "one attacker alone does not capture")
    # the same two attackers 120 degrees apart must NOT capture
    b2 = {k: "K", a2: "A", (-2, -1): "A"}
    ok(caps(b2, a2, ATTACKERS) == [], "two attackers 120 degrees apart do not capture")


def test_fig_self_capture_is_safe():
    """"the black piece is not captured when it moves between the two white
    pieces" -- capture is ACTIVE, only the mover's side captures."""
    b = {(-2, 0): "D", (-1, -1): "A", (-3, 1): "A"}
    ok(caps(b, (-2, 0), DEFENDERS) == [], "moving in between is safe")
    # and the King may do the same
    b = {(-2, 0): "K", (-1, -1): "A", (-3, 1): "A"}
    ok(caps(b, (-2, 0), DEFENDERS) == [], "the King may move in between too")


def test_no_hostile_squares():
    """The sheet gives neither an empty corner nor an empty throne any capturing
    role, so neither assists a sandwich.  Random play cannot isolate this, so it
    is tested on constructed inputs."""
    ok((3, -3) in CORNERS[4], "premise: (3,-3) is a corner")
    ok(caps({(2, -3): "D", (1, -3): "A"}, (1, -3), ATTACKERS) == [],
       "an EMPTY corner is not hostile")
    ok(caps({(0, -1): "D", (0, -2): "A"}, (0, -2), ATTACKERS) == [],
       "an EMPTY throne is not hostile")
    # ... but a real piece on the far side does capture, so the tests above are
    # not passing for the trivial reason that nothing captures there
    ok(caps({(2, -3): "D", (1, -3): "A", (3, -3): "A"}, (1, -3), ATTACKERS) == [(2, -3)],
       "an attacker on the same far cell DOES capture (non-vacuity)")
    ok(caps({(0, -1): "D", (0, -2): "A", THRONE: "A"}, (0, -2), ATTACKERS) == [(0, -1)],
       "an attacker on the throne cell would capture (non-vacuity)")


def test_fig_corner_capture():
    """"Pieces can be captured on a corner by surrounding them in the manner
    shown" -- the figure puts the two black men on the corner's two RIM
    neighbours and leaves the third, INWARD neighbour empty.

    What this figure can and cannot discriminate: it kills "all three
    neighbours are needed" and it kills "an opposite pair" (a corner has none),
    but it CANNOT by itself distinguish "the rim pair" from "any two of the
    three".  The two readings are separated below on constructed inputs, and the
    tie is broken by AbstractPlay's independent implementation, which takes the
    rim pair.  See rules.md."""
    c = (3, -3)
    rim1, rim2, inward = (2, -3), (3, -2), (2, -2)
    ok(c in CORNERS[4], "premise: (3,-3) is a corner")
    for x in (rim1, rim2, inward):
        ok(on_board(x, 4), "premise: all three neighbours are on the board")
    b = {c: "A", rim1: "D", rim2: "D"}
    ok(caps(b, rim2, DEFENDERS) == [c], "the rim pair captures a man on a corner")
    ok(caps(b, rim1, DEFENDERS) == [c], "...whichever of the two arrived last")
    # the rejected "any two" reading -- these must NOT capture
    ok(caps({c: "A", inward: "D", rim1: "D"}, inward, DEFENDERS) == [],
       "inward + rim does not capture (mover inward)")
    ok(caps({c: "A", inward: "D", rim1: "D"}, rim1, DEFENDERS) == [],
       "inward + rim does not capture (mover on the rim)")
    ok(caps({c: "A", inward: "D", rim2: "D"}, rim2, DEFENDERS) == [],
       "inward + the other rim does not capture either")
    # and it works in both directions
    ok(caps({c: "D", rim1: "A", rim2: "A"}, rim2, ATTACKERS) == [c],
       "the corner clause is colour-symmetric")


def test_fig_throne_capture():
    """"When the King is on the throne ... he must be surrounded on three sides
    as shown below to be captured."  The figure's three attackers sit on the
    throne's NW, NE and S sides -- three MUTUALLY NON-ADJACENT sides.

    Discriminating power of this figure, measured: of the four candidate
    readings it is meant to exclude it kills two outright ("two opposite sides",
    "three consecutive sides"); it CANNOT distinguish "three non-adjacent sides"
    from "any three sides", because the arrangement it draws satisfies both.
    The `four consecutive` case below is exactly that undecided case, and the
    implemented reading (non-adjacent) is the one AbstractPlay's independent
    implementation also takes.  See rules.md."""
    def thr(idxs, mover):
        b = {THRONE: "K"}
        for i in idxs:
            b[DIRS[i]] = "A"
        return caps(b, DIRS[mover], ATTACKERS)

    fig = (5, 1, 3)   # NW, NE, S -- the sheet's figure
    ok(all((a - b) % 6 not in (1, 5) for a in fig for b in fig if a != b),
       "premise: the figure's three sides are mutually NON-adjacent")
    for m in fig:
        ok(thr(fig, m) == [THRONE], "the figure's triple captures the King")
    for m in (0, 2, 4):
        ok(thr((0, 2, 4), m) == [THRONE], "the other non-adjacent triple too")
    # killed by the figure
    ok(all(thr((0, 3), m) == [] for m in (0, 3)),
       "two OPPOSITE attackers do not take a King on the throne")
    ok(all(thr((0, 1, 2), m) == [] for m in (0, 1, 2)),
       "three CONSECUTIVE attackers do not take him (killed by the figure)")
    # the undecided case: documented, not claimed to be proved by the figure
    ok(all(thr((0, 1, 2, 3), m) == [] for m in (0, 1, 2, 3)),
       "four consecutive attackers do not take him under the implemented reading")
    ok([m for m in range(5) if thr((0, 1, 2, 3, 4), m)] == [0, 2, 4],
       "with five attackers only an arrival completing a non-adjacent triple takes him")
    ok(all(thr(range(6), m) == [THRONE] for m in range(6)),
       "all six attackers always take him")
    # off the throne the King is an ordinary target again
    b = {(1, 0): "K", (2, 0): "A", (0, 0): "A"}
    ok(caps(b, (2, 0), ATTACKERS) == [(1, 0)],
       "the King OFF the throne dies to two opposite attackers")


def test_king_edge_safety():
    """A King with one side off the board cannot be sandwiched along that axis
    -- a consequence of clause 1, worth pinning because it decides endgames."""
    k = (3, -1)                                    # a rim cell, not a corner
    ok(on_board(k, 4) and k not in CORNERS[4], "premise: rim, non-corner")
    off = (4, -1)
    ok(not on_board(off, 4), "premise: one neighbour is off the board")
    b = {k: "K", (2, -1): "A"}
    ok(caps(b, (2, -1), ATTACKERS) == [], "no capture across a board edge")
    b = {k: "K", (3, -2): "A", (3, 0): "A"}
    ok(caps(b, (3, 0), ATTACKERS) == [k], "but the on-board axis still works")


# ------------------------------------------------------------- movement ----

def test_throne_occupancy():
    b = {(0, -2): "A", (0, 2): "D"}
    s = state(b, ATTACKERS)
    tos = {t for f, t in G._moves(s)}
    ok(THRONE not in tos, "a man may not STOP on the throne")
    ok((0, 1) in tos, "a man slides THROUGH the empty throne")
    s = state({(0, -1): "K"}, DEFENDERS)
    ok(THRONE in {t for f, t in G._moves(s)}, "the King may return to the throne")


def test_king_movement():
    s = G.initial_state({"size": 4})
    kmoves = [(f, t) for f, t in G._moves(s) if s.board[f] == "K"]
    ok(len(kmoves) == 3, "4x4 King has 3 moves at the start")
    ok(all(max(abs(t[0] - f[0]), abs(t[1] - f[1]), abs(t[0] + t[1] - f[0] - f[1])) == 1
           for f, t in kmoves), "4x4 King steps exactly one space")
    s5 = state({(0, 0): "K", (3, 0): "A"}, DEFENDERS, size=5)
    kt = {t for f, t in G._moves(s5)}
    ok((0, -4) in kt, "5x5 King slides like a rook, all the way to the rim")
    ok((2, 0) in kt and (3, 0) not in kt and (4, 0) not in kt,
       "...but stops in front of a piece and cannot jump it")


# ------------------------------------------------------------ termination ---

def test_ply_cap_derivation():
    for n in SIZES:
        ok(max_men(n) == sum(1 for p in start_board(n).values() if p != "K"),
           "max_men counts the men actually on the board")
        ok(ply_cap(n) == (max_men(n) + 1) * epoch_plies(n), "cap is derived, not pinned")
    ok((max_men(4), max_men(5)) == (9, 18), "9 and 18 men")
    ok((ply_cap(4), ply_cap(5)) == (1480, 4636), "derived cap values")
    ok(MAN.get("max_random_plies", 3000) < ply_cap(4),
       "max_random_plies must sit BELOW the game's own cap so a "
       "termination regression fails loudly rather than being absorbed")


def test_counters_are_live():
    """Neither draw counter is dead code: forced onto an ordinary mid-game
    position each one ends the game as a draw."""
    s = G.initial_state({"size": 4})
    for _ in range(6):
        s = G.apply_move(s, G.legal_moves(s)[0])
    ok(not G.is_terminal(s), "premise: an ordinary mid-game position")
    capped = replace(s, ply=ply_cap(s.size))
    ok(G.is_terminal(capped) and G.returns(capped) == [0.0, 0.0], "ply cap draws")
    poisoned = replace(s, reps={**s.reps, pos_key(s.board, s.to_move): REPS_DRAW})
    ok(G.is_terminal(poisoned) and G.returns(poisoned) == [0.0, 0.0], "repetition draws")


def test_repetition_reached_by_play():
    """Reach a threefold repetition through apply_move (never hand-built), and
    pin the count to THREE: the position must survive its second occurrence."""
    b = {THRONE: "K", (0, -3): "A", (0, 3): "A", (2, -3): "D"}
    s0 = state(b, DEFENDERS)
    cycle = ["2,-3>2,-2", "0,-3>1,-3", "2,-2>2,-3", "1,-3>0,-3"]
    ok(s0.reps[pos_key(s0.board, s0.to_move)] == 1, "the start counts as occurrence 1")
    s = s0
    for mv in cycle:
        ok(not G.is_terminal(s), "still running during the first cycle")
        s = G.apply_move(s, mv)
    ok(s.board == s0.board and s.to_move == s0.to_move, "the cycle returned home")
    ok(s.reps[pos_key(s.board, s.to_move)] == 2, "second occurrence")
    ok(not G.is_terminal(s),
       "a position seen TWICE is not yet a draw (threefold, not twofold)")
    for mv in cycle:
        s = G.apply_move(s, mv)
    ok(s.reps[pos_key(s.board, s.to_move)] == REPS_DRAW == 3, "third occurrence")
    ok(G.is_terminal(s), "the third occurrence ends the game")
    ok(G.returns(s) == [0.0, 0.0], "threefold repetition is an honest DRAW")
    ok(s.winner is None, "and nobody is declared a winner")
    ok(G.render(s)["caption"] == "Draw", "the caption says so")


def test_escape_is_corners_only():
    """The King wins on a CORNER, not anywhere on the rim.  Random play never
    separates these (it reaches rim cells constantly but only corners end the
    game), so every rim cell is checked explicitly."""
    rim = [c for c in CELLS[4]
           if max(abs(c[0]), abs(c[1]), abs(c[0] + c[1])) == 3 and c not in CORNERS[4]]
    ok(len(rim) == 12, "the 4x4 board has 12 non-corner rim cells")
    for t in rim:
        f = next(n for n in ((t[0] + d[0], t[1] + d[1]) for d in DIRS)
                 if on_board(n, 4) and n != THRONE)
        far = max(CORNERS[4], key=lambda c: abs(c[0] - t[0]) + abs(c[1] - t[1]))
        if far in (f, t):
            continue
        s = state({f: "K", far: "A"}, DEFENDERS)
        mv = f"{cid(f)}>{cid(t)}"
        if mv not in G.legal_moves(s):
            continue
        s2 = G.apply_move(s, mv)
        ok(s2.winner is None,
           f"the King reaching non-corner rim cell {t} must NOT win")
        ok(not G.is_terminal(s2), f"...and the game continues at {t}")
    for t in CORNERS[4]:
        f = next(n for n in ((t[0] + d[0], t[1] + d[1]) for d in DIRS)
                 if on_board(n, 4) and n != THRONE)
        far = max(CORNERS[4], key=lambda c: abs(c[0] - t[0]) + abs(c[1] - t[1]))
        s = state({f: "K", far: "A"}, DEFENDERS)
        s2 = G.apply_move(s, f"{cid(f)}>{cid(t)}")
        ok(s2.winner == DEFENDERS and G.is_terminal(s2),
           f"the King reaching corner {t} wins immediately")


def test_stuck_side_loses():
    """The sheet is silent on a side with no legal move; we follow the rest of
    the tafl family and make it a LOSS.  Reached through apply_move, because
    `winner` is only ever set there."""
    pre = {(0, -2): "A", (3, 0): "A", (2, -1): "A", (2, 0): "A", (3, -3): "A",
           (3, -1): "K", (3, -2): "D"}
    s = state(pre, ATTACKERS)
    ok("0,-2>2,-2" in G.legal_moves(s), "premise: the sealing move is legal")
    s2 = G.apply_move(s, "0,-2>2,-2")
    ok(s2.winner is None, "premise: nobody won by escape or regicide")
    ok(s2.to_move == DEFENDERS and G._moves(s2) == [], "the DEFENDERS are stuck")
    ok(G.is_terminal(s2) and G.legal_moves(s2) == [], "a stuck position is terminal")
    ok(G.returns(s2) == [-1.0, 1.0], "the stuck side loses")
    ok(G.render(s2)["caption"] == "Attackers win", "caption names the right winner")
    _assert_decisive_beats_counters(s2, "stuck")


def _assert_decisive_beats_counters(s, what):
    """A DECISIVE result must outrank the draw counters.  Random play will never
    find this: it needs the same decisive position re-scored with each counter
    tripped."""
    base = G.returns(s)
    ok(base != [0.0, 0.0], f"premise: {what} is decisive")
    for mut, tag in (
        (replace(s, ply=10 ** 9), "ply far past the cap"),
        (replace(s, ply=ply_cap(s.size)), "ply exactly at the cap"),
        (replace(s, reps={**s.reps, pos_key(s.board, s.to_move): 99}), "poisoned repetitions"),
        (replace(s, ply=10 ** 9, reps={**s.reps, pos_key(s.board, s.to_move): 99}), "both"),
    ):
        ok(G.is_terminal(mut), f"{what} still terminal with {tag}")
        ok(G.returns(mut) == base, f"{what} still decisive with {tag}")


# ------------------------------------------------------------ whole games ---

def _play(size, rng, first="defenders", collect=None):
    s = G.initial_state({"size": size, "first_player": first})
    while not G.is_terminal(s):
        if collect is not None:
            collect(s)
        mv = rng.choice(G.legal_moves(s))
        ok(mv in G.legal_moves(s), "chosen move is legal")
        s = G.apply_move(s, mv)
    if collect is not None:
        collect(s)
    return s


def why(s):
    if s.winner is not None:
        return "escape" if s.winner == DEFENDERS else "regicide"
    if not G._moves(s):
        return "stuck"
    if s.reps.get(pos_key(s.board, s.to_move), 0) >= REPS_DRAW:
        return "repetition"
    return "plycap"


def test_random_games_and_reachability():
    """Every win condition's reachability is MEASURED, not assumed -- a
    condition random play never reaches is one the conformance harness, the
    differential and this sweep all silently skip."""
    rng = random.Random(20260803)
    seen = {}
    longest = 0
    decisive = {}
    for size in SIZES:
        for i in range(400 if size == 4 else 150):
            s = _play(size, rng)
            w = why(s)
            seen[w] = seen.get(w, 0) + 1
            longest = max(longest, s.ply)
            if w in ("escape", "regicide") and w not in decisive:
                decisive[w] = s
            # every terminal state must agree with returns
            r = G.returns(s)
            if s.winner is not None:
                ok(r[s.winner] == 1.0, "winner scores +1")
            ok(sorted(r) in ([-1.0, 1.0], [0.0, 0.0]), "returns are zero-sum")
    ok(seen.get("escape", 0) > 0, "King escapes are reachable")
    ok(seen.get("regicide", 0) > 0, "King captures are reachable")
    ok(seen.get("stuck", 0) > 0, "the stuck-side loss is reachable under random play")
    ok(seen.get("plycap", 0) == 0,
       "the ply cap is NOT outcome-load-bearing: no random game reaches it")
    ok(longest < ply_cap(4), "longest random game is well inside the cap")
    for w, s in decisive.items():
        _assert_decisive_beats_counters(s, w)
    ok(len(decisive) == 2, "both decisive endings were sampled")
    ok(G.render(decisive["escape"])["caption"] == "Defenders win",
       "an escape is announced as a DEFENDERS win")
    ok(G.render(decisive["regicide"])["caption"] == "Attackers win",
       "a regicide is announced as an ATTACKERS win")
    ok(G.returns(decisive["escape"])[DEFENDERS] == 1.0, "escape pays the defenders")
    ok(G.returns(decisive["regicide"])[ATTACKERS] == 1.0, "regicide pays the attackers")


def test_invariants_over_play():
    """No stuck non-terminal state; the King on a corner is always terminal;
    describe_move never crashes."""
    rng = random.Random(4242)
    reached_rim = {4: set(), 5: set()}
    for size in SIZES:
        for _ in range(25):
            def collect(s, size=size):
                if not G.is_terminal(s):
                    ok(G.legal_moves(s), "a non-terminal state always has a move")
                    G.describe_move(s, rng.choice(G.legal_moves(s)))
                king = [c for c, p in s.board.items() if p == "K"]
                ok(len(king) <= 1, "at most one King")
                if king and king[0] in CORNERS[size]:
                    ok(G.is_terminal(s) and s.winner == DEFENDERS,
                       "a King standing on a corner has already won")
                for c in s.board:
                    ok(on_board(c, size), "every piece is on the board")
                    if max(abs(c[0]), abs(c[1]), abs(c[0] + c[1])) == size - 1:
                        reached_rim[size].add(c)
            _play(size, rng, collect=collect)
    for size in SIZES:
        ok(len(reached_rim[size]) > 6,
           "the sweep really did put pieces out on the rim (non-vacuity)")


def test_serialization_round_trip():
    """`serialize(deserialize(d)) == d` is VACUOUS -- a field `serialize` stops
    emitting just re-defaults on the way in.  Compare the STATE OBJECTS, over a
    whole game, and pin the exact key set."""
    keys = {"board", "to_move", "winner", "ply", "size", "reps"}
    rng = random.Random(99)
    n = 0
    for size in SIZES:
        for _ in range(6):
            def collect(s):
                nonlocal n
                n += 1
                d = G.serialize(s)
                ok(set(d) == keys, "exact serialised key set")
                ok(G.deserialize(d) == s, "state round-trips through serialize")
                d2 = json.loads(json.dumps(d))
                ok(G.deserialize(d2) == s, "state round-trips through JSON")
                ok(G.serialize(G.deserialize(d)) == d, "and the dict is stable")
            _play(size, rng, collect=collect)
    ok(n > 200, "the round trip was swept over real play")
    # a state carrying a non-trivial repetition table must round-trip too
    s = G.initial_state()
    for mv in ("0,-1>1,-2", "0,-3>1,-3", "1,-2>0,-1", "1,-3>0,-3"):
        s = G.apply_move(s, mv)
    ok(max(s.reps.values()) >= 2 and G.deserialize(G.serialize(s)) == s,
       "a populated repetition table survives the round trip")


def test_render_bounds_every_size():
    """Board.jsx builds its clickable cells from the DECLARED board, so a piece
    outside it is silently dropped.  Checked for every size option, from
    positions reached through apply_move, and required to be non-vacuous."""
    rng = random.Random(7)
    for size in SIZES:
        for first in ("defenders", "attackers"):
            s = G.initial_state({"size": size, "first_player": first})
            far = set()
            for _ in range(120):
                if G.is_terminal(s):
                    break
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
                spec = G.render(s)
                b = spec["board"]
                ok(b["type"] == "hex" and b["shape"] == "hexagon", "hex board")
                ok(b["size"] == size, "render declares THIS state's size")
                ok(b["orientation"] == "flat",
                   "flat-top: the sheet's board has corners at N and S")
                ok({h["cell"] for h in spec["highlights"]}
                   == {cid(c) for c in CORNERS[size]}, "the six corners are the goals")
                for p in spec["pieces"]:
                    q, r = (int(x) for x in p["cell"].split(","))
                    ok(on_board((q, r), size),
                       f"rendered piece {p['cell']} outside the declared size {size}")
                    if max(abs(q), abs(r), abs(q + r)) == size - 1:
                        far.add((q, r))
            ok(len(far) >= 6, "pieces really did reach the rim (non-vacuity)")
    ok(G.render(G.initial_state({"size": 4}))["board"]["size"] !=
       G.render(G.initial_state({"size": 5}))["board"]["size"],
       "the declared size is not hard-coded")


def test_options():
    ok(G.initial_state({"first_player": "attackers"}).to_move == ATTACKERS,
       "first_player option")
    ok(G.initial_state().to_move == DEFENDERS,
       "the sheet's default: the defenders move first")
    ok(G.initial_state({"size": 5}).size == 5, "size option")
    try:
        G.initial_state({"size": 7})
    except ValueError:
        pass
    else:
        ok(False, "an unsupported size must be rejected")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"hexentafl selftest: {len(tests)} test groups, {_checks} checks passed")


if __name__ == "__main__":
    main()
