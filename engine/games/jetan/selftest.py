"""Jetan correctness anchor — pure stdlib, fast.

No machine oracle exists for Jetan, so the anchor is Burroughs' text itself
(The Chessmen of Mars, Chapter II + Appendix) plus the Abstract Games issue 6
"suggested standard" interpretations (Handscomb / L. Lynn Smith):

* the exact initial array (Appendix: back row W Pd D F C Pr F D Pd W from each
  player's own left, so the Chiefs face the enemy Princesses; Thoats on the
  second-row ends, 8 Panthans between),
* per-piece movement tables probed from constructed positions, including the
  exact-step ("Chained") rule, combination turning, the no-revisit rule,
  blocking vs jumping, and the Princess restrictions,
* the win/draw events (Princess capture, Chief takes Chief, Chief slain by a
  lesser piece, the <=3-pieces-of-equal-value ten-move countdown),
* the one-time escape (empty + unthreatened targets only, once per side),
* hand-verified initial-position move counts (133 path moves + 40 escapes),
* termination under 200 random playouts.

Run with:  PYTHONPATH=. python3 games/jetan/selftest.py
Prints "SELFTEST OK" and exits 0 on success; raises on failure.
"""

from __future__ import annotations

import random

from games.jetan.game import (
    Jetan, JState, _start_board, _moves, _attacks, _piece_paths,
    NO_CAPTURE_CAP, VALUES,
)

G = Jetan()


def mk(pieces, to_move=0, chief_rule="draw", **kw):
    """Build a state from {(c,r): (pl, kind)}."""
    return JState(board=dict(pieces), to_move=to_move, chief_rule=chief_rule, **kw)


def dests(state, frm):
    """Final-square set (as cell tuples) of all path moves from `frm`."""
    pre = f"{frm[0]},{frm[1]}>"
    out = set()
    for m in _moves(state):
        if m.startswith(pre):
            c, r = m.split(">")[-1].split(",")
            out.add((int(c), int(r)))
    return out


# ---------------------------------------------------------------- setup ---- #
def test_setup():
    b = _start_board()
    assert len(b) == 40
    back = ["W", "Pd", "D", "F", "C", "Pr", "F", "D", "Pd", "W"]
    for c, k in enumerate(back):
        assert b[(c, 0)] == (0, k)              # Black, left to right col 0..9
        assert b[(9 - c, 9)] == (1, k)          # Orange mirrored
    for c in range(10):
        k = "T" if c in (0, 9) else "P"
        assert b[(c, 1)] == (0, k) and b[(c, 8)] == (1, k)
    # Chief faces the ENEMY Princess (Burroughs' mirrored perspectives)
    assert b[(4, 0)] == (0, "C") and b[(4, 9)] == (1, "Pr")
    assert b[(5, 0)] == (0, "Pr") and b[(5, 9)] == (1, "C")
    counts = {}
    for (_, k) in b.values():
        counts[k] = counts.get(k, 0) + 1
    assert counts == {"P": 16, "W": 4, "Pd": 4, "D": 4, "F": 4, "T": 4,
                      "C": 2, "Pr": 2}


# ---------------------------------------------------- movement (centre) ---- #
# A lone piece at e5 = (4,4) on an otherwise empty board (no Princess on the
# board, so no threat machinery interferes).
def centre(kind, pl=0):
    return mk({(4, 4): (pl, kind)}, to_move=pl)


def off(ds):
    return {(4 + dc, 4 + dr) for dc, dr in ds}


def test_movement_tables():
    # Panthan: 1 step forward / forward-diagonal / sideways, never backward.
    assert dests(centre("P"), (4, 4)) == off({(0, 1), (1, 1), (-1, 1), (1, 0), (-1, 0)})
    assert dests(centre("P", pl=1), (4, 4)) == off({(0, -1), (1, -1), (-1, -1), (1, 0), (-1, 0)})

    # Warrior: exactly 2 orthogonal steps, turning allowed -> the 4 straight
    # doubles plus the 4 diagonals (via an L-turn); never 1 step, never back
    # to the start square.
    assert dests(centre("W"), (4, 4)) == off(
        {(2, 0), (-2, 0), (0, 2), (0, -2), (1, 1), (1, -1), (-1, 1), (-1, -1)})

    # Padwar: exactly 2 diagonal steps -> long diagonals plus the orthogonal
    # doubles reached by a diagonal V-turn.
    assert dests(centre("Pd"), (4, 4)) == off(
        {(2, 2), (2, -2), (-2, 2), (-2, -2), (2, 0), (-2, 0), (0, 2), (0, -2)})

    # Dwar: exactly 3 orthogonal steps; parity => Manhattan distance 1 or 3.
    dw = dests(centre("D"), (4, 4))
    assert dw == {(4 + dc, 4 + dr) for dc in range(-3, 4) for dr in range(-3, 4)
                  if abs(dc) + abs(dr) in (1, 3)}
    assert len(dw) == 16

    # Flier: exactly 3 diagonal steps; both offsets odd, Chebyshev <= 3.
    fl = dests(centre("F"), (4, 4))
    assert fl == {(4 + dc, 4 + dr) for dc in (-3, -1, 1, 3) for dr in (-3, -1, 1, 3)}
    assert len(fl) == 16

    # Chief: exactly 3 steps, any mix -> the whole Chebyshev-3 ball minus start.
    ch = dests(centre("C"), (4, 4))
    assert ch == {(4 + dc, 4 + dr) for dc in range(-3, 4) for dr in range(-3, 4)
                  if (dc, dr) != (0, 0)}
    assert len(ch) == 48

    # Thoat: one orthogonal + one diagonal, either order -> 8 knight squares
    # plus the 4 orthogonally adjacent; never its own square.
    th = dests(centre("T"), (4, 4))
    knight = {(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)}
    assert th == off(knight | {(1, 0), (-1, 0), (0, 1), (0, -1)})
    assert len(th) == 12


def test_blocking_and_jumping():
    # A Warrior with all four orthogonal neighbours occupied cannot move at
    # all (its first step is blocked; capture happens only on the FINAL square).
    s = mk({(4, 4): (0, "W"), (3, 4): (1, "P"), (5, 4): (1, "P"),
            (4, 3): (1, "P"), (4, 5): (1, "P")})
    assert dests(s, (4, 4)) == set()
    # ...but it may CAPTURE on its final square.
    s = mk({(4, 4): (0, "W"), (6, 4): (1, "P")})
    assert (6, 4) in dests(s, (4, 4))
    # A Dwar path through an occupied square is blocked; other routes survive.
    s = mk({(4, 4): (0, "D"), (4, 5): (0, "P"), (4, 3): (0, "P"),
            (3, 4): (0, "P"), (5, 4): (0, "P")})
    assert dests(s, (4, 4)) == set()          # all first steps blocked
    # A Flier fully walled in by friends JUMPS out (but may not land on them).
    ring = {(4 + dc, 4 + dr): (0, "P") for dc in (-1, 0, 1) for dr in (-1, 0, 1)
            if (dc, dr) != (0, 0)}
    s = mk({(4, 4): (0, "F"), **ring})
    assert dests(s, (4, 4)) == {(4 + dc, 4 + dr) for dc in (-3, -1, 1, 3)
                                for dr in (-3, -1, 1, 3)} - set(ring)
    # A Thoat jumps too.
    s = mk({(4, 4): (0, "T"), **ring})
    th = dests(s, (4, 4))
    assert (5, 6) in th and (6, 5) in th and len(th) == 8  # knight squares only
    # No-revisit: a Chief cannot end where it has already stepped, so a
    # 3-step move can still reach an adjacent square only by a detour; with
    # the detours blocked the adjacent square is unreachable.
    s = mk({(0, 0): (0, "C"), (1, 0): (0, "P"), (1, 1): (0, "P")})
    # (0,1) needs e.g. E-N-W or NE-N-SW... all routes pass (1,0)/(1,1): blocked
    assert (0, 1) not in dests(s, (0, 0))


def test_princess_rules():
    # The Princess may never capture: an enemy piece on a reachable square is
    # NOT a destination.
    s = mk({(4, 4): (0, "Pr"), (7, 7): (1, "P")})
    assert (7, 7) not in dests(s, (4, 4))
    # She may not END on a threatened square (enemy Warrior covers (2,0),(0,2),
    # (1,1)... from (1,-1)-ish geometry) but may pass over threats (jumper).
    s = mk({(4, 4): (0, "Pr"), (0, 4): (1, "W")})
    w_cover = _attacks({(0, 4): (1, "W")}, 1)
    pd = dests(s, (4, 4))
    assert pd and not (pd & w_cover)
    # She jumps: walled in by enemies, she still gets out (without capturing).
    ring = {(4 + dc, 4 + dr): (1, "P") for dc in (-1, 0, 1) for dr in (-1, 0, 1)
            if (dc, dr) != (0, 0)}
    s = mk({(4, 4): (0, "Pr"), **ring})
    assert dests(s, (4, 4))  # non-empty despite the wall
    # The enemy Princess does NOT threaten (she cannot capture).
    s = mk({(4, 4): (0, "Pr"), (4, 8): (1, "Pr")}, to_move=0)
    d = dests(s, (4, 4))
    assert (4, 7) in d  # adjacent-to-enemy-princess square is safe


def test_escape():
    # Escape: any EMPTY square not threatened by the enemy; once per side.
    s = mk({(4, 4): (0, "Pr"), (9, 9): (1, "W"), (0, 0): (1, "Pr")})
    mv = _moves(s)
    esc = {m for m in mv if m.startswith("E@")}
    assert esc
    threatened = _attacks({(9, 9): (1, "W")}, 1)
    for m in esc:
        c, r = m.split("@")[1].split(",")
        t = (int(c), int(r))
        assert t not in s.board and t not in threatened
    # occupied squares are never escape targets
    assert "E@9,9" not in esc and "E@0,0" not in esc and "E@4,4" not in esc
    # applying an escape consumes it
    s2 = G.apply_move(s, "E@7,2")
    assert s2.escape_used == [True, False]
    assert s2.board[(7, 2)] == (0, "Pr") and (4, 4) not in s2.board
    # black has no second escape...
    s3 = JState(board=s2.board, to_move=0, escape_used=list(s2.escape_used))
    assert not any(m.startswith("E@") for m in _moves(s3))
    # ...but orange still has one
    assert any(m.startswith("E@") for m in _moves(s2))


# ------------------------------------------------------------ win / draw --- #
def test_win_events():
    # Any piece landing on the enemy Princess wins.
    s = mk({(4, 4): (0, "P"), (4, 5): (1, "Pr"), (5, 0): (0, "Pr"),
            (9, 9): (1, "C"), (4, 0): (0, "C")})
    s2 = G.apply_move(s, "4,4>4,5")
    assert s2.over and s2.winner == 0 and G.is_terminal(s2)
    assert G.returns(s2) == [1.0, -1.0]
    # Chief takes Chief wins.
    s = mk({(4, 4): (0, "C"), (4, 7): (1, "C"), (0, 0): (0, "Pr"), (9, 9): (1, "Pr")})
    s2 = G.apply_move(s, "4,4>4,5>4,6>4,7")
    assert s2.winner == 0 and s2.reason == "chief takes chief"
    # A Chief slain by a LESSER piece: instant draw under Burroughs' rule...
    s = mk({(4, 4): (0, "W"), (5, 5): (1, "C"), (0, 0): (0, "Pr"),
            (9, 9): (1, "Pr"), (0, 3): (0, "C")})
    s2 = G.apply_move(s, "4,4>4,5>5,5")
    assert s2.over and s2.winner is None and G.returns(s2) == [0.0, 0.0]
    # ...and merely a lost piece under the modern option.
    s = mk({(4, 4): (0, "W"), (5, 5): (1, "C"), (0, 0): (0, "Pr"),
            (9, 9): (1, "Pr"), (0, 3): (0, "C")}, chief_rule="plays_on")
    s2 = G.apply_move(s, "4,4>4,5>5,5")
    assert not s2.over and s2.board[(5, 5)] == (0, "W")
    assert not any(k == "C" for (p, k) in s2.board.values() if p == 1)


def test_endgame_countdown():
    # Both sides <=3 pieces of equal value -> ten plies to produce a win.
    pieces = {(0, 0): (0, "Pr"), (4, 4): (0, "C"),
              (9, 9): (1, "Pr"), (4, 9): (1, "C")}
    assert VALUES["C"] == 10 and VALUES["Pr"] == 0
    s = mk(pieces, to_move=0)
    s2 = G.apply_move(s, "4,4>3,4>2,4>1,4")     # quiet chief move
    assert s2.endgame == 10 and not s2.over
    s3 = G.apply_move(s2, "4,9>3,9>3,8>2,8")
    assert s3.endgame == 9
    # fast-forward: countdown at 1, next quiet ply ends it in a draw
    s = mk(pieces, to_move=0, endgame=1)
    s2 = G.apply_move(s, "4,4>3,4>2,4>1,4")
    assert s2.over and s2.winner is None and s2.reason == "endgame ten-move rule"
    # but a WIN still beats the countdown
    s = mk({(0, 0): (0, "Pr"), (4, 4): (0, "C"),
            (9, 9): (1, "Pr"), (4, 7): (1, "C")}, to_move=0, endgame=1)
    s2 = G.apply_move(s, "4,4>4,5>4,6>4,7")
    assert s2.winner == 0
    # condition NOT met (unequal value): no countdown
    s = mk({(0, 0): (0, "Pr"), (4, 4): (0, "C"),
            (9, 9): (1, "Pr"), (0, 9): (1, "W")}, to_move=0)
    s2 = G.apply_move(s, "4,4>3,4>2,4>1,4")
    assert s2.endgame is None


def test_no_capture_and_repetition():
    # 50 captureless moves by each player -> draw.
    # (unequal totals — 6 vs 5 — keep the endgame countdown disarmed here)
    pieces = {(0, 0): (0, "Pr"), (4, 4): (0, "D"), (5, 9): (1, "D"),
              (9, 9): (1, "Pr"), (0, 4): (0, "W"), (9, 5): (1, "P")}
    s = mk(pieces, to_move=0, captureless=NO_CAPTURE_CAP - 1)
    s2 = G.apply_move(s, "4,4>3,4>2,4>1,4")
    assert s2.over and s2.winner is None and s2.reason == "50 captureless moves each"
    # a capture resets the counter
    s = mk({**pieces, (1, 4): (1, "P")}, to_move=0, captureless=NO_CAPTURE_CAP - 1)
    s2 = G.apply_move(s, "4,4>3,4>2,4>1,4")
    assert not s2.over and s2.captureless == 0
    # threefold repetition: two Dwars shuffling A-B-A-B... the first shuffled
    # position recurs at plies 1, 5 and 9 -> drawn at ply 9.
    s = G.deserialize(G.serialize(mk(pieces, to_move=0)))
    cyc = ["4,4>4,5>4,6>4,7", "5,9>5,8>5,7>5,6",       # out
           "4,7>4,6>4,5>4,4", "5,6>5,7>5,8>5,9"]       # back
    n = 0
    for _ in range(4):
        for m in cyc:
            if s.over:
                break
            s = G.apply_move(s, m)
            n += 1
        if s.over:
            break
    assert s.over and s.winner is None and s.reason == "threefold repetition"
    assert n <= 12


# ------------------------------------------------- initial position ------- #
def test_initial_position():
    s = G.initial_state()
    mv = G.legal_moves(s)
    esc = [m for m in mv if m.startswith("E@")]
    paths = [m for m in mv if not m.startswith("E@")]
    # Hand-verified: back-row Warriors/Padwars/Dwars/Chief are boxed in; the 8
    # Panthans have 3 forward squares each (24); each Thoat reaches 3 squares;
    # Fliers jump the pawn row to 4 squares each; the Princess (a jumper) has
    # 14 empty safe destinations on rows 3-4.
    assert dests(s, (0, 0)) == set() and dests(s, (1, 0)) == set()
    assert dests(s, (2, 0)) == set() and dests(s, (4, 0)) == set()
    assert dests(s, (1, 1)) == {(0, 2), (1, 2), (2, 2)}
    assert dests(s, (0, 1)) == {(0, 2), (1, 3), (2, 2)}
    assert dests(s, (3, 0)) == {(0, 3), (2, 3), (4, 3), (6, 3)}
    assert dests(s, (6, 0)) == {(3, 3), (5, 3), (7, 3), (9, 3)}
    assert len(dests(s, (5, 0))) == 14
    # Escape targets: every empty square not attacked by Orange = rows 2..5
    # entire (Orange's Panthans/Thoats/Fliers cover ALL of rows 6 and 7).
    assert len(esc) == 40
    assert {m.split("@")[1] for m in esc} == {f"{c},{r}" for c in range(10)
                                              for r in range(2, 6)}
    assert len(paths) == 133 and len(mv) == 173      # frozen totals
    # mirrored position, Orange to move: identical count by symmetry
    s1 = JState(board=_start_board(), to_move=1)
    assert len(_moves(s1)) == 173


# ------------------------------------------------------- termination ------ #
def test_serialization_roundtrip():
    s = G.initial_state()
    rng = random.Random(7)
    for _ in range(30):
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert G.serialize(s2) == d
    import json
    json.dumps(d)


def test_termination():
    rng = random.Random(2026)
    lengths = []
    results = {"win": 0, "draw": 0}
    for _ in range(200):
        s = G.initial_state()
        n = 0
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            n += 1
            assert n <= 1100, "runaway game"
        lengths.append(n)
        r = G.returns(s)
        assert len(r) == 2 and all(isinstance(x, float) for x in r)
        results["win" if s.winner is not None else "draw"] += 1
    assert max(lengths) <= 1000
    # sanity: random play produces plenty of decisive princess captures
    assert results["win"] > 50
    print(f"  200 playouts: avg {sum(lengths)/len(lengths):.0f} plies, "
          f"max {max(lengths)}, {results}")


def test_heuristic_shape():
    s = G.initial_state()
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("SELFTEST OK")
