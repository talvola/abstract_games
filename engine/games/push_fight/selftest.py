#!/usr/bin/env python3
"""Push Fight correctness anchor. Pure stdlib (agp + this package only).

Covers the board geometry and the rail semantics against the published position
encoding, the push/anchor rules, the two loss conditions, the draw counters, and
the serialize/deserialize round trip. The heavy anchors live outside this file:
`_diff_reference.py` (2.03M legal turns vs Maks Verver's reference generator) and
`_diff_solver.py` (the complete tablebase).
"""
from __future__ import annotations

import dataclasses
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                   # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
# load_from_dir imports game.py under a SYNTHETIC module name, so this is the
# only way to reach the module object the game instance actually runs from.
M = sys.modules[type(G).__module__]

SER_KEYS = {"board", "to_move", "moves_used", "anchor", "stock", "turns",
            "reps", "winner", "draw", "last"}


def cell(name):
    """'d2' -> '3,1'."""
    return f"{ord(name[0]) - ord('a')},{int(name[1]) - 1}"


def pos(spec, anchor=None, to_move=0, **kw):
    """Build a state from 'd2:0S e3:1C ...' shorthand."""
    board = {}
    for tok in spec.split():
        c, pc = tok.split(":")
        board[cell(c)] = (int(pc[0]), pc[1])
    return M.PFState(board=board, to_move=to_move,
                     anchor=cell(anchor) if anchor else None, **kw)


def moves(s):
    return set(G.legal_moves(s))


# --------------------------------------------------------------------------- #
# 1. Board geometry and the published position encoding
# --------------------------------------------------------------------------- #

def test_geometry():
    assert len(M.CELLS) == 26, len(M.CELLS)
    assert len(M.PERM_ORDER) == 26 and set(M.PERM_ORDER) == set(M.CELLS)
    # rank 4 = files c-g, rank 1 = files b-f, ranks 2 and 3 are full.
    by_rank = {r: sorted(int(c.split(",")[0]) for c in M.CELLS
                         if int(c.split(",")[1]) == r) for r in range(4)}
    assert by_rank[3] == [2, 3, 4, 5, 6], by_rank[3]
    assert by_rank[2] == list(range(8)) and by_rank[1] == list(range(8))
    assert by_rank[0] == [1, 2, 3, 4, 5], by_rank[0]
    assert sorted(M.VOID) == sorted(["0,3", "1,3", "7,3", "0,0", "6,0", "7,0"])
    # 180-degree rotational symmetry (the solver relies on it).
    for c in M.CELLS:
        x, y = map(int, c.split(","))
        assert f"{7 - x},{3 - y}" in M.CELLS, c
    # The eight cells the anchor can never occupy are exactly the degree-2 cells.
    deg2 = {M.alg(c) for c in M.CELLS if len(M.ADJ[c]) == 2}
    assert deg2 == {"a2", "a3", "b1", "c4", "f1", "g4", "h2", "h3"}, deg2


def test_standard_opening_string():
    """The standard opening must equal board.js INITIAL_PIECES, char for char.

    This one literal pins the cell set, the PERM_ORDER traversal and the opening
    simultaneously -- it is Maks Verver's own encoding of his app's default.
    """
    s = G.initial_state(options={"setup": "standard"})
    assert M.perm_string(s.board, s.anchor) == ".OX.....oXx....oOx.....OX."
    assert sum(1 for v in s.board.values() if v == (0, "S")) == 3
    assert sum(1 for v in s.board.values() if v == (0, "C")) == 2
    assert sum(1 for v in s.board.values() if v == (1, "S")) == 3
    assert sum(1 for v in s.board.values() if v == (1, "C")) == 2
    assert M.alg("3,1") == "d2" and M.alg("0,0" if False else "6,2") == "g3"


# --------------------------------------------------------------------------- #
# 2. Pushing: rails, open edges, chains, the "at least one piece" rule
# --------------------------------------------------------------------------- #

def test_rails_block_vertical_pushes():
    # Rail above rank 4: d3 cannot shove d4 through the top edge.
    s = pos("d3:0S d4:1C")
    assert f"{cell('d3')}>{cell('d4')}" not in moves(s)
    # Rail below rank 1: d2 cannot shove d1 through the bottom edge.
    s = pos("d2:0S d1:1C")
    assert f"{cell('d2')}>{cell('d1')}" not in moves(s)
    # A whole column still cannot be shoved through the rail.
    s = pos("d1:0S d2:1C d3:1C d4:1C")
    assert f"{cell('d1')}>{cell('d2')}" not in moves(s)


def test_open_edges_push_pieces_off():
    """Only rank 4's top edge and rank 1's bottom edge are railed.

    maksverver's README calls out b3 and g2 explicitly: a piece there CAN be
    shoved off the top / bottom, because ranks 4 and 1 do not extend that far.
    """
    for pusher, victim, loser in [("b2", "b3", 1),   # off the top past file b
                                  ("g3", "g2", 1),   # off the bottom past file g
                                  ("b3", "a3", 1),   # off the left edge
                                  ("g2", "h2", 1),   # off the right edge
                                  ("d4", "c4", 1)]:  # sideways out of rank 4
        s = pos(f"{pusher}:0S {victim}:1C")
        mv = f"{cell(pusher)}>{cell(victim)}"
        assert mv in moves(s), (pusher, victim)
        n = G.apply_move(s, mv)
        assert n.winner == 1 - loser and G.is_terminal(n)
        assert G.returns(n) == [1.0, -1.0]


def test_pushing_your_own_piece_off_loses():
    """Demaine et al.: 'A player loses if any of their pieces are pushed off the
    board (even by their own push).'"""
    s = pos("b3:0S a3:0C")
    n = G.apply_move(s, f"{cell('b3')}>{cell('a3')}")
    assert n.winner == 1, n.winner            # red shoved a red piece off: red loses
    assert G.returns(n) == [-1.0, 1.0]


def test_push_must_move_a_piece():
    """A push into an empty square is not a push -- it is an ordinary move."""
    s = pos("d2:0S f2:1C")
    mv = f"{cell('d2')}>{cell('e2')}"
    assert mv in moves(s)                     # legal as a MOVE
    n = G.apply_move(s, mv)
    assert n.moves_used == 1 and n.to_move == 0 and n.anchor is None
    # ... and it did not end the turn or place an anchor.


def test_push_chain_and_anchor_placement():
    s = pos("b2:0S c2:1C d2:1S e2:0C")
    n = G.apply_move(s, f"{cell('b2')}>{cell('c2')}")
    assert n.board[cell("c2")] == (0, "S")    # the pusher advanced one square
    assert n.board[cell("d2")] == (1, "C")
    assert n.board[cell("e2")] == (1, "S")
    assert n.board[cell("f2")] == (0, "C")    # the whole line moved one square
    assert cell("b2") not in n.board
    assert n.anchor == cell("c2")             # anchor lands on the pushing piece
    assert n.to_move == 1 and n.moves_used == 0 and n.turns == 1


def test_anchor_blocks_the_whole_line():
    # Blue's anchor sits on d2; red may not push it, nor any line containing it.
    s = pos("b2:0S c2:1C d2:1S", anchor="d2")
    assert f"{cell('b2')}>{cell('c2')}" not in moves(s)
    # With the anchor elsewhere the very same push is legal.
    s2 = pos("b2:0S c2:1C d2:1S", anchor="e3")
    assert f"{cell('b2')}>{cell('c2')}" in moves(s2)
    # A pusher adjacent to the anchor cannot push it directly either.
    s3 = pos("c2:0S d2:1S e2:1C", anchor="d2")
    assert f"{cell('c2')}>{cell('d2')}" not in moves(s3)


def test_only_squares_push():
    s = pos("b2:0C c2:1C")                    # a circle beside an enemy piece
    assert f"{cell('b2')}>{cell('c2')}" not in moves(s)


def test_you_may_only_move_and_push_your_own_pieces():
    s = pos("b2:1S c2:0C f2:0S g2:0C", to_move=0)
    theirs = {cell("b2")}
    assert not [m for m in moves(s) if m.split(">")[0] in theirs], moves(s)
    assert f"{cell('b2')}>{cell('c2')}" not in moves(s)
    # ... and the very same push IS legal when it is that player's turn.
    assert f"{cell('b2')}>{cell('c2')}" in moves(dataclasses.replace(s, to_move=1))


# --------------------------------------------------------------------------- #
# 3. Moves: sliding through empties, and the 0-2 move budget
# --------------------------------------------------------------------------- #

def test_moves_slide_through_empty_squares_only():
    s = pos("a2:0S b2:1C d2:0S f2:1C")
    src = cell("a2")
    all_dst = {m.split(">")[1] for m in moves(s) if m.startswith(src + ">")}
    quiet = {d for d in all_dst if d not in s.board}
    # An occupied square is never a move destination -- only a PUSH target.
    assert cell("b2") in all_dst and cell("b2") not in quiet
    assert cell("a3") in quiet and cell("c3") in quiet
    assert cell("c4") in quiet                # rounds the corner through empties
    assert quiet <= (M.CELLS - set(s.board))
    # Sealing the detour traps the piece: b2 and a3 occupied leaves a2 no move.
    s2 = pos("a2:0S b2:1C a3:1C")
    assert not [m for m in moves(s2)
                if m.startswith(src + ">") and m.split(">")[1] not in s2.board]


def test_move_budget_is_two_then_a_push():
    s = G.initial_state(options={"setup": "standard"})
    quiet = [m for m in G.legal_moves(s) if m.split(">")[1] not in s.board]
    s1 = G.apply_move(s, quiet[0])
    assert s1.to_move == 0 and s1.moves_used == 1
    quiet1 = [m for m in G.legal_moves(s1) if m.split(">")[1] not in s1.board]
    s2 = G.apply_move(s1, quiet1[0])
    assert s2.to_move == 0 and s2.moves_used == 2
    # After two moves ONLY pushes remain, and each ends the turn.
    rest = G.legal_moves(s2)
    assert rest and all(m.split(">")[1] in s2.board for m in rest)
    quiet_push = next(m for m in rest if G.apply_move(s2, m).winner is None)
    s3 = G.apply_move(s2, quiet_push)
    assert s3.to_move == 1 and s3.moves_used == 0 and s3.turns == 1
    assert s3.anchor == quiet_push.split(">")[1]


def test_offered_moves_always_leave_a_push():
    """The ply decomposition must generate exactly the legal TURNS: a quiet move
    is only offered if the turn can still be completed with a push."""
    rng = random.Random(5)
    checked = 0
    for i in range(30):
        s = G.initial_state(options={"setup": "standard" if i % 2 else "free"})
        while not G.is_terminal(s):
            if not G._placing(s):
                for m in G.legal_moves(s):
                    src, dst = m.split(">")
                    if dst in s.board:
                        continue
                    nb = dict(s.board)
                    nb[dst] = nb.pop(src)
                    assert M._can_complete(nb, s.to_move, s.anchor,
                                           2 - s.moves_used - 1), (m, s.moves_used)
                    checked += 1
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert checked > 2000, checked


# --------------------------------------------------------------------------- #
# 4. The "cannot push" loss
# --------------------------------------------------------------------------- #

def test_cannot_push_loses():
    """A side with no legal turn loses, and `winner` is set through apply_move.

    The position is synthetic (see rules.md: no legal 3+2 position where a player
    is stuck could be found), but the rule and its code path are real: here red's
    lone square is walled in, its two vertical pushes hit the rail / the edge of
    the board, its left neighbour b4 does not exist and its right neighbour is
    the anchor.
    """
    stuck = pos("c4:0S d4:1S c3:1C c2:1C c1:1C", anchor="d4", to_move=0)
    assert not M._can_complete(stuck.board, 0, stuck.anchor, 2)
    assert M._can_complete(stuck.board, 1, stuck.anchor, 2)     # blue is fine
    # Reach it through apply_move (a hand-built terminal would report
    # is_terminal False, since `winner` is only ever set inside apply_move):
    # blue shoves the red square from d4 to c4 and anchors on d4 behind it.
    pre = pos("e4:1S d4:0S c3:1C c2:1C c1:1C", to_move=1)
    mv = f"{cell('e4')}>{cell('d4')}"
    assert mv in moves(pre)
    after = G.apply_move(pre, mv)
    assert after.anchor == cell("d4") and after.board == stuck.board
    assert after.winner == 1, (after.winner, M.perm_string(after.board, after.anchor))
    assert G.is_terminal(after) and G.returns(after) == [-1.0, 1.0]


def test_cannot_push_is_judged_over_the_WHOLE_turn():
    """"Stuck" means no push after ANY legal 0-2 moves, not after 0 or 1.

    Red's square on e2 has only e1 (its own circle) adjacent, and shoving it down
    hits the rail below rank 1; the circle on e1 is walled in by d1, f1 and the
    square itself, so no SINGLE move gives red a push. Two do: the square steps
    aside, the circle follows it out, and now the square has something to shove.
    A `_start_turn` that only looked two plies deep (budget 1) would declare red
    lost here -- so this position pins the budget the rule is evaluated with.
    """
    s = pos("d1:1S e1:0C e2:0S f1:1S", anchor="f1", to_move=0)
    assert not M._can_complete(s.board, 0, s.anchor, 0)
    assert not M._can_complete(s.board, 0, s.anchor, 1)
    assert M._can_complete(s.board, 0, s.anchor, 2)
    n = M.PFState(board=dict(s.board), to_move=0, anchor=s.anchor)
    G._start_turn(n)
    assert n.winner is None and n.draw is None, (n.winner, n.draw)
    # Every offered move is quiet (no push exists yet), and playing one of them
    # really does leave a push two plies later.
    ms = G.legal_moves(s)
    assert ms and all(m.split(">")[1] not in s.board for m in ms)
    s1 = G.apply_move(s, ms[0])
    assert M._can_complete(s1.board, 0, s1.anchor, 1)


# --------------------------------------------------------------------------- #
# 5. Draw counters -- and that a DECISIVE result outranks them
# --------------------------------------------------------------------------- #

def _quiet_push_state():
    """A state whose only sensible push resolves without anyone falling off."""
    return pos("b2:0S c2:1C e3:1S f3:0C", anchor="e3", to_move=0)


def test_turn_cap_is_derived_from_the_games_own_bound():
    """The cap must come from Push Fight's own decisive bound, never be shrunk to
    suit the harness -- a cap small enough to truncate real play decides games."""
    import json
    # The complete solution's longest forced win is 49 turns for one player,
    # i.e. 97 turns in total; the cap sits at roughly three times that.
    assert M.TURN_CAP >= 3 * 97, M.TURN_CAP
    # The manifest's random-play ceiling must sit strictly BELOW our own bound
    # (a turn is at most 3 plies), so a termination regression fails loudly as
    # "did not terminate" instead of being absorbed into a silent cap draw.
    mrp = json.loads((PKG / "manifest.json").read_text())["max_random_plies"]
    assert mrp < 3 * M.TURN_CAP, (mrp, M.TURN_CAP)


def test_turn_cap_is_load_bearing_and_bites():
    s = _quiet_push_state()
    mv = f"{cell('b2')}>{cell('c2')}"
    assert G.apply_move(dataclasses.replace(s, turns=0), mv).draw is None
    capped = G.apply_move(dataclasses.replace(s, turns=M.TURN_CAP - 1), mv)
    assert capped.draw == "turn limit"
    assert G.is_terminal(capped) and G.returns(capped) == [0.0, 0.0]
    assert capped.winner is None
    # ... and the threshold is EXACT: one turn earlier must not draw. Without
    # this the cap is only pinned from one side and an off-by-one survives.
    near = G.apply_move(dataclasses.replace(s, turns=M.TURN_CAP - 2), mv)
    assert near.draw is None and near.turns == M.TURN_CAP - 1


def test_repetition_is_load_bearing_and_bites():
    s = _quiet_push_state()
    mv = f"{cell('b2')}>{cell('c2')}"
    plain = G.apply_move(s, mv)
    assert plain.draw is None
    key = M.perm_string(plain.board, plain.anchor) + str(plain.to_move)
    poisoned = G.apply_move(dataclasses.replace(s, reps={key: 2}), mv)
    assert poisoned.draw == "repetition"
    assert G.returns(poisoned) == [0.0, 0.0]
    # A near miss must NOT draw -- proves the threshold is really threefold.
    assert G.apply_move(dataclasses.replace(s, reps={key: 1}), mv).draw is None


def test_decisive_result_outranks_every_counter():
    """The nine-times-repeated defect of this library: a win delivered on a
    repeated position or at the ply cap must NOT be scored as a draw."""
    # (a) a push that shoves a piece off the board
    win = pos("b3:0S a3:1C")
    mv = f"{cell('b3')}>{cell('a3')}"
    base = G.apply_move(win, mv)
    assert base.winner == 0
    key = M.perm_string(base.board, base.anchor) + str(base.to_move)
    for poison in ({"turns": M.TURN_CAP + 7},
                   {"reps": {key: 99}},
                   {"turns": M.TURN_CAP + 7, "reps": {key: 99}}):
        n = G.apply_move(dataclasses.replace(win, **poison), mv)
        assert n.winner == 0 and n.draw is None, poison
        assert G.returns(n) == [1.0, -1.0], poison

    # ... and returns() itself ranks a winner above a draw reason, so the
    # priority survives even if some future path ever set both fields.
    both = dataclasses.replace(base, draw="turn limit")
    assert G.returns(both) == [1.0, -1.0], G.returns(both)
    # (the two are mutually exclusive as shipped -- assert that too)
    assert not (base.winner is not None and base.draw is not None)

    # (b) the other decisive ending: the opponent is left with no legal turn
    pre = pos("e4:1S d4:0S c3:1C c2:1C c1:1C", to_move=1)
    pmv = f"{cell('e4')}>{cell('d4')}"
    plain = G.apply_move(pre, pmv)
    assert plain.winner == 1
    key2 = M.perm_string(plain.board, plain.anchor) + str(plain.to_move)
    for poison in ({"turns": M.TURN_CAP + 7},
                   {"reps": {key2: 99}},
                   {"turns": M.TURN_CAP + 7, "reps": {key2: 99}}):
        n = G.apply_move(dataclasses.replace(pre, **poison), pmv)
        assert n.winner == 1 and n.draw is None, poison
        assert G.returns(n) == [-1.0, 1.0], poison


def test_turn_cap_patch_actually_bites():
    """Guard against a vacuous constant patch: M is the LIVE module (resolved via
    sys.modules[type(G).__module__]), so changing TURN_CAP must change behaviour."""
    s = _quiet_push_state()
    mv = f"{cell('b2')}>{cell('c2')}"
    old = M.TURN_CAP
    try:
        M.TURN_CAP = 10 ** 9
        assert G.apply_move(dataclasses.replace(s, turns=old - 1), mv).draw is None
        M.TURN_CAP = 1
        assert G.apply_move(dataclasses.replace(s, turns=5), mv).draw == "turn limit"
    finally:
        M.TURN_CAP = old
    assert G.apply_move(dataclasses.replace(s, turns=old - 1), mv).draw == "turn limit"


# --------------------------------------------------------------------------- #
# 6. Setup phase
# --------------------------------------------------------------------------- #

def test_free_placement():
    s = G.initial_state()
    assert G._placing(s) and s.stock == [[3, 2], [3, 2]]
    # Red places only in files a-d, blue only in files e-h.
    assert all(int(m.split("@")[1].split(",")[0]) < 4 for m in G.legal_moves(s))
    rng = random.Random(2)
    seen_seats = []
    while G._placing(s):
        seen_seats.append(s.to_move)
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert seen_seats == [0] * 5 + [1] * 5     # red places all five, then blue
    assert len(s.board) == 10 and s.to_move == 0 and s.turns == 0
    assert sorted(v for v in s.board.values()) == \
        sorted([(0, "S")] * 3 + [(0, "C")] * 2 + [(1, "S")] * 3 + [(1, "C")] * 2)
    assert all(int(c.split(",")[0]) < 4 for c, v in s.board.items() if v[0] == 0)
    assert all(int(c.split(",")[0]) >= 4 for c, v in s.board.items() if v[0] == 1)


# --------------------------------------------------------------------------- #
# 7. serialize / deserialize -- compare STATE OBJECTS, sweep every field shape
# --------------------------------------------------------------------------- #

def test_serialize_round_trip_over_whole_games():
    rng = random.Random(99)
    seen = {k: set() for k in SER_KEYS}
    n = 0

    def check(s):
        nonlocal n
        d = G.serialize(s)
        assert set(d) == SER_KEYS, set(d) ^ SER_KEYS
        back = G.deserialize(d)
        # The VACUOUS form is serialize(deserialize(d)) == d: a field that
        # serialize() stopped emitting simply re-defaults on the way in and is
        # re-omitted on the way out, so equality still holds. Compare the STATES.
        assert back == s, (n, d)
        assert G.serialize(back) == d
        for k, v in d.items():
            seen[k].add(repr(v)[:120])
        n += 1

    for i in range(24):
        s = G.initial_state(options={"setup": "standard" if i % 2 else "free"})
        while True:
            check(s)
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))

    # Random play never draws (see rules.md), so cover the drawn shapes by hand:
    # a field only ever seen at its default proves nothing about the round trip.
    base = _quiet_push_state()
    mv = f"{cell('b2')}>{cell('c2')}"
    check(G.apply_move(dataclasses.replace(base, turns=M.TURN_CAP - 1), mv))
    drawn = G.apply_move(base, mv)
    key = M.perm_string(drawn.board, drawn.anchor) + str(drawn.to_move)
    check(G.apply_move(dataclasses.replace(base, reps={key: 2}), mv))
    # Every field must actually vary across the sweep, or the round trip proves
    # nothing about it.
    for k in SER_KEYS:
        assert len(seen[k]) > 1, f"{k} never varied ({n} states)"
    # And every field shape that matters must have been exercised.
    assert any(v != "None" for v in seen["anchor"])
    assert any(v not in ("0",) for v in seen["moves_used"])
    assert any(v != "{}" for v in seen["reps"])
    assert any(v != "None" for v in seen["winner"])
    assert any(v != "None" for v in seen["last"])
    assert any(v != "[[0, 0], [0, 0]]" for v in seen["stock"])


def test_json_able():
    import json
    s = G.initial_state()
    for _ in range(6):
        s = G.apply_move(s, G.legal_moves(s)[0])
    json.dumps(G.serialize(s))
    json.dumps(G.render(s))


# --------------------------------------------------------------------------- #
# 8. Engine contract: purity, non-empty moves, render bounds
# --------------------------------------------------------------------------- #

def test_apply_move_is_pure_and_moves_never_empty():
    rng = random.Random(31)
    for i in range(20):
        s = G.initial_state(options={"setup": "standard" if i % 2 else "free"})
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            assert ms, "empty legal_moves on a non-terminal state"
            before = G.serialize(s)
            mv = rng.choice(ms)
            G.describe_move(s, mv)             # must never raise
            nxt = G.apply_move(s, mv)
            assert G.serialize(s) == before, "apply_move mutated its input"
            s = nxt
        assert G.returns(s) in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])
        # Random play resolves in a handful of turns (measured max 22 over 3000
        # games), nowhere near the cap -- the cap never decides a random game.
        assert s.turns < M.TURN_CAP // 2, s.turns


def test_render_stays_inside_the_declared_board():
    """Board.jsx builds its clickable cell set from board.width/height and joins
    pieces by cell id -- a piece outside it is silently DROPPED."""
    rng = random.Random(77)
    checked = 0
    for i in range(20):
        s = G.initial_state(options={"setup": "standard" if i % 2 else "free"})
        while True:
            spec = G.render(s)
            b = spec["board"]
            assert (b["type"], b["width"], b["height"]) == ("square", 8, 4)
            for p in spec["pieces"]:
                c, r = map(int, p["cell"].split(","))
                assert 0 <= c < b["width"] and 0 <= r < b["height"], p
                assert p["cell"] in M.CELLS, p
            for cid in b["tints"]:
                c, r = map(int, cid.split(","))
                assert 0 <= c < b["width"] and 0 <= r < b["height"], cid
            assert len(spec["pieces"]) == len(s.board)
            assert ("reserve" in spec) == G._placing(s)
            checked += 1
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert checked > 200, checked
    # The six holes are tinted, and the anchor cell is tinted while it exists.
    s = G.initial_state(options={"setup": "standard"})
    b = G.render(s)["board"]
    assert set(M.VOID) <= set(b["tints"])
    # Both side rails are drawn, spanning exactly the railed edges: the top of
    # rank 4 (files c-g) and the bottom of rank 1 (files b-f).
    rails = b["overlay"]
    assert len(rails) == 2, rails
    (tl, tr, _c1), (bl, br, _c2) = rails
    assert round(tl[1], 3) == round(tr[1], 3) > 3 and tl[0] < 2 < 6 < tr[0]
    assert round(bl[1], 3) == round(br[1], 3) < 0 and bl[0] < 1 < 5 < br[0]
    assert tr[0] - tl[0] < 6 and br[0] - bl[0] < 6      # not the full 8 files
    s = G.apply_move(s, [m for m in G.legal_moves(s) if m.split(">")[1] in s.board][0])
    assert s.anchor in G.render(s)["board"]["tints"]


def test_anchor_tint_is_never_painted_over_by_the_last_move_highlight():
    """Board.jsx resolves a cell's fill as last-move > tints > default.

    The push destination IS the anchor cell, so emitting a last-move highlight
    there would hide the anchor tint on exactly the ply the opponent plans around
    it. render() must therefore leave the anchor out of `highlights` (verified in
    the browser: the cell rendered #3a3228, the highlight colour, before the fix).
    """
    rng = random.Random(1234)
    seen_push = 0
    for i in range(8):
        s = G.initial_state(options={"setup": "standard" if i % 2 else "free"})
        while not G.is_terminal(s):
            spec = G.render(s)
            hls = {h["cell"] for h in spec["highlights"]}
            assert s.anchor not in hls, (s.anchor, hls)
            if s.anchor is not None:
                assert s.anchor in spec["board"]["tints"]
            # the SOURCE of the last action is still shown
            if s.last and s.last[0] and s.last[0] != s.anchor:
                assert s.last[0] in hls
            if s.last and s.last[1] == s.anchor:
                seen_push += 1
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    assert seen_push > 20, seen_push


def test_heuristic_shape():
    """MUST be a LIST of num_players payoffs -- a bare float raises deep inside
    MCTS back-propagation, and only when the rollout cutoff is reached."""
    import random as _r
    from agp.mcts import MCTSBot
    s = G.initial_state(options={"setup": "standard"})
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2, h
    assert all(isinstance(x, float) and -1.0 <= x <= 1.0 for x in h), h
    assert abs(h[0] + h[1]) < 1e-9, h
    # A low max_rollout forces the cutoff, which is the only path that calls it.
    mv = MCTSBot(_r.Random(1), iterations=25, max_rollout=2).select(G, s)
    assert mv in G.legal_moves(s)


def test_describe_move():
    s = G.initial_state()
    assert G.describe_move(s, f"{M.PUSHER}@{cell('d2')}") == "Red square → d2"
    s = G.initial_state(options={"setup": "standard"})
    assert G.describe_move(s, f"{cell('c2')}>{cell('b2')}") == "c2-b2"
    assert G.describe_move(s, f"{cell('d4')}>{cell('e4')}") == "d4-e4 push"
    off = pos("b3:0S a3:1C")
    assert "Blue piece off" in G.describe_move(off, f"{cell('b3')}>{cell('a3')}")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"push_fight selftest: {len(tests)} checks passed")


if __name__ == "__main__":
    main()
