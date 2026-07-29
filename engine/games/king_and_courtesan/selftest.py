#!/usr/bin/env python3
"""King & Courtesan correctness anchors — pure stdlib, run by the suite.

Anchors, in order:
  A. Setup matches the rulebook's Figure 1 (piece counts, home squares, the
     empty middle diagonal) for every board size.
  B. Movement: the exact three FORWARD directions, captures in all EIGHT, no
     backward step, no friendly capture, exchange only king->own courtesan and
     only forward -- for BOTH seats and BOTH piece kinds. Every fixture is
     ASYMMETRIC, so a mirrored/rotated bug fails, and `test_seat_symmetry`
     conjugates the whole engine under the 180-degree seat swap so no
     seat-specific regression can hide behind Red-to-move fixtures.
  C. Winning: king onto the enemy home square by step, by capture and by
     exchange; capturing the enemy king; a COURTESAN on the enemy home is NOT
     a win. All reached through apply_move (winner is set there).
  D. A decisive result OUTRANKS the ply-cap counter.
  E. The ply cap is live code, is the derived bound, and is never reached.
  F. "A player always has a move" — the structural theorem plus 600 random
     games' worth of evidence.
  G. serialize/deserialize compares STATE OBJECTS and the exact key set, over
     whole random games.
  H. apply_move is pure and never aliases the parent's board.
  I. render() declares the right board and puts every piece inside it, for
     every size, on positions reached through apply_move (full board coverage).
"""

from __future__ import annotations

import copy
import json
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)
M = sys.modules[type(G).__module__]          # the LIVE module, not games.<uid>.game
KCState, ply_cap, home = M.KCState, M.ply_cap, M.home
SIZES = (6, 7, 8)


def ok(msg):
    print(f"  ok  {msg}")


def state(size, board, to_move=0, ply=0, winner=None):
    """A hand-built position. `board` maps 'c,r' -> '0K'/'1C'/..."""
    return KCState(size=size,
                   board={tuple(int(x) for x in k.split(",")): (int(v[0]), v[1])
                          for k, v in board.items()},
                   to_move=to_move, ply=ply, winner=winner)


def targets(s, frm):
    """Destination cell ids of the legal moves that start at `frm`."""
    return {m.split(">")[1] for m in G.legal_moves(s) if m.split(">")[0] == frm}


# --------------------------------------------------------------- A. setup ---
def test_setup():
    for size in SIZES:
        s = G.initial_state({"size": size})
        red = {c for c, v in s.board.items() if v[0] == 0}
        blue = {c for c, v in s.board.items() if v[0] == 1}
        want = size * (size - 1) // 2                     # 15 / 21 / 28
        assert len(red) == len(blue) == want, (size, len(red), len(blue))
        assert not (red & blue)
        # the long middle anti-diagonal is empty, and is the ONLY empty part
        empty = {(c, r) for c in range(size) for r in range(size)} - red - blue
        assert empty == {(c, r) for c in range(size) for r in range(size)
                         if c + r == size - 1}, size
        assert len(empty) == size
        # exactly one king per side, on its own home square
        kings = {v[0]: c for c, v in s.board.items() if v[1] == "K"}
        assert len(kings) == 2 and kings[0] == home(0, size) and kings[1] == home(1, size)
        assert sum(1 for v in s.board.values() if v[1] == "K") == 2
        # Steere's own count: the king plus 14 courtesans on 6x6 (rows 2..5)
        if size == 6:
            assert sum(1 for c, v in s.board.items()
                       if v[0] == 0 and v[1] == "C") == 14
        assert s.to_move == 0 and s.ply == 0 and s.winner is None
    # frozen opening move counts (independently confirmed against AbstractPlay
    # gameslib by _diff_gameslib.py): 6x6 = 10 steps + 5 captures + 4 steps
    # from the second rank + 3 king exchanges.
    for size, want in ((6, 22), (7, 26), (8, 30)):
        got = len(G.legal_moves(G.initial_state({"size": size})))
        assert got == want, (size, got, want)
    ok("setup: counts, empty middle diagonal, kings, opening move counts")


# ------------------------------------------------------------ B. movement ---
def test_forward_directions():
    # A lone red KING at 2,3 with nothing around it: exactly the three forward
    # squares. Asymmetric position (2,3), asymmetric answer.
    s = state(6, {"2,3": "0K", "5,5": "1K"})
    assert targets(s, "2,3") == {"3,3", "2,4", "3,4"}, targets(s, "2,3")
    # A lone red COURTESAN moves identically.
    s = state(6, {"2,3": "0C", "0,0": "0K", "5,5": "1K"})
    assert targets(s, "2,3") == {"3,3", "2,4", "3,4"}
    # Blue's forward set is the exact mirror.
    s = state(6, {"2,3": "1K", "0,0": "0K"}, to_move=1)
    assert targets(s, "2,3") == {"1,3", "2,2", "1,2"}, targets(s, "2,3")
    # ...and a blue COURTESAN moves identically to the blue king. Testing only
    # the blue KING (as this file once did) leaves seat 1's 14 courtesans with
    # NO assertion at all: `to_move=1` never reaches the frozen opening counts,
    # which are measured with Red to move, and random play asserts no legality.
    # A regression that special-cased the seat -- blue courtesans stepping in
    # RED's directions, or frozen, or unable to capture backward -- shipped
    # green through every gate. See test_seat_symmetry for the structural fix.
    s = state(6, {"2,3": "1C", "5,5": "1K", "0,0": "0K"}, to_move=1)
    assert targets(s, "2,3") == {"1,3", "2,2", "1,2"}, targets(s, "2,3")
    # blue never steps backward onto an empty square
    for bad in ("3,3", "2,4", "3,4", "1,4", "3,2"):
        assert bad not in targets(s, "2,3"), bad
    # Edge clipping: a red king on the far file has only the +row step, and a
    # blue courtesan on the near file mirrors it.
    s = state(6, {"5,2": "0K", "0,5": "1K"})
    assert targets(s, "5,2") == {"5,3"}
    s = state(6, {"0,3": "1C", "5,5": "1K", "0,0": "0K"}, to_move=1)
    assert targets(s, "0,3") == {"0,2"}, targets(s, "0,3")
    ok("movement: the three forward directions, per seat AND per piece kind, "
       "clipped at the edge")


def test_captures_all_eight():
    # Red king at 2,2 ringed by eight blue courtesans: eight captures, and no
    # non-capturing move at all (every forward square is occupied).
    ring = {f"{2 + dc},{2 + dr}": "1C"
            for dc in (-1, 0, 1) for dr in (-1, 0, 1) if (dc, dr) != (0, 0)}
    s = state(6, dict(ring, **{"2,2": "0K", "5,5": "1K"}))
    assert targets(s, "2,2") == set(ring), targets(s, "2,2")
    assert len(targets(s, "2,2")) == 8
    # backward and sideways captures are real: strip the forward three, so the
    # five survivors can only be reached by a non-forward capture (the three
    # vacated forward squares become ordinary steps).
    back = {k: v for k, v in ring.items() if k not in ("3,2", "2,3", "3,3")}
    s = state(6, dict(back, **{"2,2": "0K", "5,5": "1K"}))
    assert targets(s, "2,2") == {"1,2", "2,1", "1,1", "3,1", "1,3",
                                 "3,2", "2,3", "3,3"}, targets(s, "2,2")
    # The same for a BLUE COURTESAN -- seat 1's non-king pieces need their own
    # fixture (the blue-courtesan capture elsewhere in this file goes straight
    # through apply_move and so never asserts the move was legal).
    ring = {f"{3 + dc},{3 + dr}": "0C"
            for dc in (-1, 0, 1) for dr in (-1, 0, 1) if (dc, dr) != (0, 0)}
    s = state(6, dict(ring, **{"3,3": "1C", "5,5": "1K", "0,0": "0K"}), to_move=1)
    assert targets(s, "3,3") == set(ring), targets(s, "3,3")
    assert len(targets(s, "3,3")) == 8
    ok("captures: all eight directions, including backward and sideways, "
       "for both seats")


def test_no_backward_step_no_friendly_capture():
    # Empty backward squares are NOT legal destinations.
    s = state(6, {"2,2": "0K", "5,5": "1K"})
    assert targets(s, "2,2") == {"3,2", "2,3", "3,3"}
    for bad in ("1,2", "2,1", "1,1", "3,1", "1,3"):
        assert bad not in targets(s, "2,2")
    # A courtesan may never move onto a friendly piece (that is not an exchange).
    s = state(6, {"2,2": "0C", "3,2": "0C", "2,3": "0C", "3,3": "0C",
                  "0,0": "0K", "5,5": "1K"})
    assert targets(s, "2,2") == set(), targets(s, "2,2")
    ok("no backward steps; a courtesan never displaces a friend")


def test_exchange():
    # King exchanges with a friendly courtesan in each forward direction only.
    s = state(6, {"2,2": "0K", "3,2": "0C", "2,3": "0C", "3,3": "0C",
                  "1,2": "0C", "2,1": "0C", "1,1": "0C", "3,1": "0C", "1,3": "0C",
                  "5,5": "1K"})
    assert targets(s, "2,2") == {"3,2", "2,3", "3,3"}, targets(s, "2,2")
    # ...and only the KING may: the courtesans around it have no move onto 2,2.
    for frm in ("1,2", "2,1", "1,1"):
        assert "2,2" not in targets(s, frm), frm
    # the exchange swaps roles and leaves the occupied SET untouched
    before = set(s.board)
    t = G.apply_move(s, "2,2>3,3")
    assert set(t.board) == before
    assert t.board[(3, 3)] == (0, "K") and t.board[(2, 2)] == (0, "C")
    assert sum(1 for v in t.board.values() if v == (0, "K")) == 1
    # a blue piece forward of the king is a CAPTURE, not an exchange
    s = state(6, {"2,2": "0K", "3,3": "1C", "5,5": "1K"})
    t = G.apply_move(s, "2,2>3,3")
    assert (2, 2) not in t.board and t.board[(3, 3)] == (0, "K")
    ok("exchange: king only, forward only, swaps roles, occupancy unchanged")


def _rot_cell(cell, n):
    return (n - 1 - cell[0], n - 1 - cell[1])


def _rot(s):
    """The position rotated 180 degrees with the seats swapped."""
    n = s.size
    return KCState(size=n,
                   board={_rot_cell(c, n): (1 - o, k)
                          for c, (o, k) in s.board.items()},
                   to_move=1 - s.to_move, ply=s.ply,
                   winner=None if s.winner is None else 1 - s.winner)


def _rot_move(m, n):
    a, b = (tuple(int(x) for x in p.split(",")) for p in m.split(">"))
    ra, rb = _rot_cell(a, n), _rot_cell(b, n)
    return f"{ra[0]},{ra[1]}>{rb[0]},{rb[1]}"


def test_seat_symmetry():
    """The two armies are congruent under the 180-degree rotation that swaps
    the seats, so the ENTIRE engine must conjugate cleanly under it.

    This is the structural guard for seat 1. Every hand-built fixture is
    inherently partial, and the frozen opening move counts are all measured
    with RED to move -- so a seat-asymmetric regression in move generation can
    leave every other assertion in this file green while Blue plays a different
    game. Comparing full move sets against the conjugate at every ply of whole
    random games catches all of them at once.

    It is also why the seat win-rate under random play is ~50/50: the position
    is exactly symmetric and Red merely moves first.
    """
    checked = 0
    for size in SIZES:
        init = G.initial_state({"size": size})
        # the armies really are congruent (only the mover differs)
        assert _rot(init).board == init.board, size
        assert _rot(init) == replace(init, to_move=1), size
        # ...so Blue's opening move count equals Red's frozen one
        assert len(G.legal_moves(replace(init, to_move=1))) == \
            len(G.legal_moves(init)), size
        assert {_rot_move(m, size) for m in G.legal_moves(init)} == \
            set(G.legal_moves(replace(init, to_move=1))), size
        rng = random.Random(5150 + size)
        for _ in range(15):
            s = init
            while not G.is_terminal(s):
                r = _rot(s)
                assert {_rot_move(m, size) for m in G.legal_moves(s)} == \
                    set(G.legal_moves(r)), (size, s.ply, "move sets differ "
                                            "under the seat conjugation")
                assert G.heuristic(r) == [-x for x in G.heuristic(s)], (size, s.ply)
                m = rng.choice(G.legal_moves(s))
                s2, r2 = G.apply_move(s, m), G.apply_move(r, _rot_move(m, size))
                assert _rot(s2) == r2, (size, s.ply, m)
                assert G.returns(r2) == [-x for x in G.returns(s2)], (size, s.ply)
                assert G.is_terminal(r2) == G.is_terminal(s2)
                checked += 1
                s = s2
    ok(f"the engine conjugates exactly under the 180-degree seat swap "
       f"({checked} positions) — neither seat plays a different game")


def test_describe_move():
    s = state(6, {"2,2": "0K", "3,3": "1C", "2,3": "0C", "3,2": "1C"})
    assert G.describe_move(s, "2,2>3,3") == "Kc3xd4"
    assert G.describe_move(s, "2,2>2,3") == "Kc3/c4"
    s2 = state(6, {"2,2": "0K", "4,4": "0C"})
    assert G.describe_move(s2, "2,2>3,3") == "Kc3-d4"
    assert G.describe_move(s2, "4,4>4,5") == "e5-e6"
    ok("describe_move distinguishes step / capture / exchange")


# ------------------------------------------------------------- C. winning ---
def test_win_king_reaches_enemy_home():
    n = 6
    # by a plain step
    s = state(n, {"4,5": "0K", "0,0": "1K"})
    t = G.apply_move(s, "4,5>5,5")
    assert t.winner == 0 and G.is_terminal(t) and G.returns(t) == [1.0, -1.0]
    # by a capture (a blue courtesan is sitting on blue's own home square)
    s = state(n, {"4,4": "0K", "5,5": "1C", "0,5": "1K"})
    t = G.apply_move(s, "4,4>5,5")
    assert t.winner == 0 and G.returns(t) == [1.0, -1.0]
    # by an exchange (a friendly courtesan is on the enemy home square)
    s = state(n, {"4,5": "0K", "5,5": "0C", "0,3": "1K"})
    t = G.apply_move(s, "4,5>5,5")
    assert t.board[(5, 5)] == (0, "K") and t.board[(4, 5)] == (0, "C")
    assert t.winner == 0 and G.returns(t) == [1.0, -1.0]
    # blue wins symmetrically on 0,0
    s = state(n, {"1,0": "1K", "5,2": "0K"}, to_move=1)
    t = G.apply_move(s, "1,0>0,0")
    assert t.winner == 1 and G.returns(t) == [-1.0, 1.0]
    ok("win: king onto the enemy home square by step, capture and exchange")


def test_courtesan_on_enemy_home_is_not_a_win():
    s = state(6, {"4,5": "0C", "0,0": "0K", "1,1": "1K"})
    t = G.apply_move(s, "4,5>5,5")
    assert t.board[(5, 5)] == (0, "C")
    assert t.winner is None and not G.is_terminal(t) and G.legal_moves(t)
    ok("a courtesan on the enemy home square is NOT a win")


def test_win_by_capturing_the_king():
    s = state(6, {"2,2": "0C", "1,1": "1K", "4,4": "1C", "0,0": "0K"})
    t = G.apply_move(s, "2,2>1,1")            # a BACKWARD capture of the king
    assert t.winner == 0 and G.is_terminal(t) and G.returns(t) == [1.0, -1.0]
    assert not any(k == "K" for _, k in
                   [v for v in t.board.values() if v[0] == 1])
    # and the mirror
    s = state(6, {"3,3": "1C", "4,4": "0K", "0,0": "0C", "5,5": "1K"}, to_move=1)
    t = G.apply_move(s, "3,3>4,4")
    assert t.winner == 1 and G.returns(t) == [-1.0, 1.0]
    ok("win: capturing the enemy king (including backward)")


# ---------------------------------- D. decisive outranks the draw counter ---
def test_decisive_outranks_ply_cap():
    """The single most repeated defect in this library: a counter consulted
    BEFORE the win check, so a win delivered at the cap scores 0-0."""
    checked = 0
    for size in SIZES:
        rng = random.Random(1234 + size)
        for _ in range(25):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            assert s.winner is not None, "expected a decisive terminal"
            good = G.returns(s)
            for poisoned_ply in (ply_cap(size), ply_cap(size) + 1, 10 ** 9):
                p = replace(s, ply=poisoned_ply)
                assert G.is_terminal(p)
                assert G.returns(p) == good, (size, poisoned_ply, G.returns(p), good)
                assert G.legal_moves(p) == []
                assert G.render(p)["caption"].endswith("wins")
            checked += 1
    ok(f"a decisive result survives every tripped counter ({checked} terminals)")


# -------------------------------------------------------- E. the ply cap ---
def test_ply_cap():
    # the derived bound, frozen
    assert (ply_cap(6), ply_cap(7), ply_cap(8)) == (755, 1225, 1857), \
        (ply_cap(6), ply_cap(7), ply_cap(8))
    for size in SIZES:
        cap = ply_cap(size)
        # LIVE, not vacuous: one ply below the cap the game runs on; at the cap
        # it stops, with an honest draw (no fabricated winner).
        s = replace(G.initial_state({"size": size}), ply=cap - 1)
        assert not G.is_terminal(s) and G.legal_moves(s)
        s = replace(s, ply=cap)
        assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0]
        assert G.legal_moves(s) == []
        assert G.render(s)["caption"] == "Draw (ply cap)"
    # ...and DEAD in practice: 600 random games never come close.
    worst = 0
    for size in SIZES:
        rng = random.Random(2718 + size)
        for _ in range(200):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            assert s.winner is not None, "cap draw in a random game!"
            worst = max(worst, s.ply / ply_cap(size))
        assert worst < 0.5
    ok(f"ply cap live and honest; 600 random games peak at {worst:.1%} of it")


# ------------------------------------------- F. a player is never stuck ---
def test_never_stuck():
    """Steere asserts "players will always have a move available". It is a
    theorem: the KING's three forward squares are empty (=> step), enemy
    (=> capture) or friendly (=> necessarily a courtesan, so exchange), and
    they are all off-board only when the king already stands on the enemy home
    square — which is terminal."""
    positions = 0
    for size in SIZES:
        rng = random.Random(31415 + size)
        for _ in range(200):
            s = G.initial_state({"size": size})
            while not G.is_terminal(s):
                ms = G.legal_moves(s)
                assert ms, f"stuck at ply {s.ply}, size {size}"
                # the king alone always accounts for at least one of them
                king = next(c for c, v in s.board.items()
                            if v == (s.to_move, "K"))
                kc = f"{king[0]},{king[1]}"
                assert any(m.startswith(kc + ">") for m in ms), (size, king)
                positions += 1
                s = G.apply_move(s, rng.choice(ms))
    ok(f"never stuck; the king always has a move ({positions} positions)")


# ------------------------------------------------ G. serialize round-trip ---
KEYS = {"size", "board", "to_move", "ply", "winner"}


def test_serialize_roundtrip():
    seen_winner = set()
    for size in SIZES:
        rng = random.Random(161803 + size)
        for _ in range(12):
            s = G.initial_state({"size": size})
            while True:
                d = G.serialize(s)
                assert set(d) == KEYS, set(d) ^ KEYS
                json.loads(json.dumps(d))                     # JSON-able
                # compare STATE OBJECTS: `serialize(deserialize(d)) == d` is
                # vacuous, since a dropped field would simply re-default.
                assert G.deserialize(d) == s, (size, d)
                assert G.deserialize(json.loads(json.dumps(d))) == s
                seen_winner.add(s.winner)
                if G.is_terminal(s):
                    break
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    # every field shape actually occurred: winner None AND both seats, a
    # non-default size, a non-zero ply, both movers.
    assert seen_winner == {None, 0, 1}, seen_winner
    s = G.initial_state({"size": 8})
    assert G.deserialize(G.serialize(s)).size == 8
    # a mutated field must survive the trip (no field is silently dropped)
    for field_name, value in (("size", 7), ("to_move", 1), ("ply", 41),
                              ("winner", 1)):
        base = replace(G.initial_state({"size": 7}), **{field_name: value})
        assert getattr(G.deserialize(G.serialize(base)), field_name) == value
    ok("serialize round-trips STATES, exact key set, every field shape")


# ------------------------------------------------- H. purity / no aliasing ---
def test_purity():
    for size in SIZES:
        rng = random.Random(577 + size)
        s = G.initial_state({"size": size})
        while not G.is_terminal(s):
            snapshot = copy.deepcopy(G.serialize(s))
            m = rng.choice(G.legal_moves(s))
            t = G.apply_move(s, m)
            assert G.serialize(s) == snapshot, "apply_move mutated its input"
            assert t.board is not s.board, "successor aliases the parent board"
            assert t.ply == s.ply + 1 and t.to_move == 1 - s.to_move
            s = t
    ok("apply_move is pure and never aliases the parent's board")


# ---------------------------------------------------------- I. rendering ---
def test_render_bounds():
    """Board.jsx builds its clickable cell set from board.width/height and
    silently DROPS any piece outside it — no crash, no warning. Check every
    size on positions reached through apply_move, and prove non-vacuity by
    requiring that the sweep visits every square of the board."""
    for size in SIZES:
        rng = random.Random(8080 + size)
        covered = set()
        for _ in range(60):
            s = G.initial_state({"size": size})
            while True:
                spec = G.render(s)
                b = spec["board"]
                assert b["type"] == "square"
                assert (b["width"], b["height"]) == (size, size), (size, b)
                assert set(b["tints"]) == {"0,0", f"{size - 1},{size - 1}"}
                cells = {p["cell"] for p in spec["pieces"]}
                assert len(cells) == len(spec["pieces"]) == len(s.board)
                for cid in cells:
                    c, r = (int(x) for x in cid.split(","))
                    assert 0 <= c < size and 0 <= r < size, (size, cid)
                    covered.add((c, r))
                kings = [p for p in spec["pieces"] if p.get("stack")]
                assert all(p["stack"] == [p["owner"]] * 2 for p in kings)
                assert len(kings) == sum(1 for v in s.board.values() if v[1] == "K")
                if G.is_terminal(s):
                    break
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        assert covered == {(c, r) for c in range(size) for r in range(size)}, \
            (size, sorted({(c, r) for c in range(size) for r in range(size)} - covered))
    ok("render(): every size declares its own board and keeps pieces inside it")


def test_heuristic_shape():
    """Must be a LIST of num_players payoffs — a bare float raises deep inside
    MCTS back-propagation, and only when the rollout cutoff is reached."""
    from agp.mcts import MCTSBot
    s = G.initial_state({"size": 6})
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2, h
    assert abs(h[0] + h[1]) < 1e-9 and abs(h[0]) < 1e-9, h   # symmetric start
    # red king one step from the enemy home, blue's still on its own: red ahead
    s2 = state(6, {"4,4": "0K", "5,5": "1K"})
    h2 = G.heuristic(s2)
    assert h2[0] > 0 > h2[1] and abs(h2[0] + h2[1]) < 1e-9, h2
    # ...and the mirror position must favour blue by the same amount
    s3 = state(6, {"1,1": "1K", "0,0": "0K"})
    assert G.heuristic(s3) == [-h2[0], -h2[1]], (h2, G.heuristic(s3))
    # force the rollout cutoff so a malformed heuristic cannot hide
    mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(
        G, G.initial_state({"size": 6}))
    assert mv in G.legal_moves(G.initial_state({"size": 6}))
    ok("heuristic returns a per-seat list and survives a forced rollout cutoff")


if __name__ == "__main__":
    print("King & Courtesan selftest")
    test_setup()
    test_forward_directions()
    test_captures_all_eight()
    test_no_backward_step_no_friendly_capture()
    test_exchange()
    test_seat_symmetry()
    test_describe_move()
    test_win_king_reaches_enemy_home()
    test_courtesan_on_enemy_home_is_not_a_win()
    test_win_by_capturing_the_king()
    test_decisive_outranks_ply_cap()
    test_ply_cap()
    test_never_stuck()
    test_serialize_roundtrip()
    test_purity()
    test_render_bounds()
    test_heuristic_shape()
    print("all king_and_courtesan selftests passed")
