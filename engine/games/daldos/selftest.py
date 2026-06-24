"""Pure-stdlib selftest for Daldøs.

Anchors: path/circuit topology + a couple of adjacencies; the dal-activation
rule (a piece leaves home only on a roll of 1, and only the stern-most undalled
piece may dal); an undalled piece cannot capture but a dalled one can; capturing
removes the enemy permanently; the dice are uniform 1..4; the win (remove all
enemy pieces) reached via apply_move; a full seeded random playout terminates;
serialize round-trip (incl. roll/dice/dalled flags).

Run: PYTHONPATH=. python3 games/daldos/selftest.py
"""

import json
import random
import sys

from games.daldos.game import Daldos, DaldosState, _geometry, SIZES


class FixedDice(random.Random):
    """rng whose randint(1,4) cycles through a forced list of die values.

    ``random.Random.__new__`` forwards the constructor arg to seeding, so the
    value passed must be hashable -- we accept it as ``*values`` (a tuple).
    """
    def __new__(cls, *values):
        return super().__new__(cls)

    def __init__(self, values):
        super().__init__()
        self._vals = list(values)
        self._i = 0

    def randint(self, a, b):
        v = self._vals[self._i % len(self._vals)]
        self._i += 1
        return v


def stt(pieces0, pieces1, dice, to_move=0, H=12, winner=None):
    return DaldosState(
        pieces={0: [dict(p) for p in pieces0], 1: [dict(p) for p in pieces1]},
        roll=tuple(dice), dice=tuple(dice), to_move=to_move,
        winner=winner, H=H, ply=0,
    )


def pc(idx, dalled):
    return {"idx": idx, "dalled": dalled}


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def main():
    g = Daldos()
    geo = _geometry(12)
    H = geo["H"]

    # --- topology ----------------------------------------------------------
    check(H == 12 and geo["M"] == 13, "Norwegian H=12, M=13")
    check(len(geo["home"][0]) == 12, "home row 0 has 12 holes")
    check(len(geo["circuit"][0]) == 25, "circuit (middle+enemy) = 25 cells")
    # stern home piece (idx 11) dals INTO the middle stern (12,1).
    check(g._abs_cell(geo, 0, 11) == (12, 0), "idx 11 = stern home (12,0)")
    check(g._abs_cell(geo, 0, 12) == (12, 1), "dal off stern -> middle (12,1)")
    # middle is traversed toward the prow; prow (extra hole) is (0,1).
    check(g._abs_cell(geo, 0, 12 + 12) == (0, 1), "prow extra hole (0,1)")
    # after the prow a piece enters the ENEMY home (y=2) from the prow end.
    check(g._abs_cell(geo, 0, 12 + 13) == (1, 2), "enters enemy home at (1,2)")
    # the circuit repeats: index +25 lands on the same cell.
    check(g._abs_cell(geo, 0, 12) == g._abs_cell(geo, 0, 12 + 25),
          "circuit repeats with period 25")
    # symmetry: player 1's enemy-home is player 0's home row (y=0).
    check(g._abs_cell(geo, 1, 12 + 13) == (1, 0), "p1 enters p0's home (1,0)")

    # --- dice are uniform 1..4 --------------------------------------------
    rng = random.Random(999)
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    N = 200000
    for _ in range(N):
        a, b = Daldos._roll(rng)
        counts[a] += 1
        counts[b] += 1
    for k in (1, 2, 3, 4):
        frac = counts[k] / (2 * N)
        check(abs(frac - 0.25) < 0.01, f"die face {k}: {frac:.4f} ~ 0.25")

    # --- dal activation: a piece can ONLY leave home on a roll of 1 --------
    # Fresh board, dice (2,3): no piece is dalled and there is no dal -> pass.
    s = g.initial_state(rng=FixedDice([2, 3]))
    # initial roll consumed FixedDice -> roll (2,3)
    check(s.roll == (2, 3), f"initial roll (2,3); got {s.roll}")
    check(g.legal_moves(s) == ["pass"], "no dal + no dalled piece -> only pass")

    # dice (1,2): the dal can activate the stern-most piece.
    s = g.initial_state(rng=FixedDice([1, 2]))
    moves = g.legal_moves(s)
    # the ONLY dal move available is dalling the stern piece (col 12) -> (12,1).
    dal_move = "12,0>12,1"
    check(dal_move in moves, f"stern dal move present; got {moves}")
    # a NON-stern piece may NOT be dalled first (e.g. col 11 -> (11,1)? no).
    check("11,0>11,1" not in moves, "only stern-most undalled piece may dal")
    # die 2 cannot move any (undalled) piece, so it offers no advance moves yet.
    check(all(m == dal_move for m in moves),
          f"with no dalled piece, only the dal move is legal; got {moves}")

    # apply the dal -> that piece is now dalled and on (12,1); same player keeps
    # moving with the remaining die 2.
    s2 = g.apply_move(s, dal_move, FixedDice([3, 3]))
    check(s2.to_move == 0, "same player continues after using one die")
    check(s2.dice == (2,), "the dal (1) was consumed; die 2 remains")
    moved = [p for p in s2.pieces[0] if p["dalled"]]
    check(len(moved) == 1 and moved[0]["idx"] == 12, "stern piece dalled to idx 12")
    # now die 2 advances the dalled piece (12,1) -> two holes toward prow (10,1).
    adv = "12,1>10,1"
    check(adv in g.legal_moves(s2), f"dalled piece advances by die 2; got {g.legal_moves(s2)}")

    # --- an UNDALLED piece cannot capture; a DALLED one can ----------------
    # Place a Blue piece on a middle cell; a Red UNDALLED piece is irrelevant
    # (it can't move). Construct: Red dalled piece one hole behind a Blue piece.
    # Red dalled at idx 12 -> (12,1). Blue piece sits on (10,1). Red die 2 -> (10,1) capture.
    blue_idx = geo["circuit"][1].index((10, 1)) + H  # idx for blue on (10,1)
    red = [pc(12, True)]
    blue = [pc(blue_idx, True), pc(5, False)]  # one on (10,1), one undalled home
    s = stt(red, blue, dice=(2, 4), to_move=0)
    check(g._abs_cell(geo, 1, blue_idx) == (10, 1), "blue sits on (10,1)")
    cap_move = "12,1>10,1"
    check(cap_move in g.legal_moves(s), "dalled red can reach the enemy cell")
    sn = g.apply_move(s, cap_move, FixedDice([2, 2]))
    # the blue piece on (10,1) is removed; blue's other (undalled) piece remains.
    check(len(sn.pieces[1]) == 1, "captured blue piece removed permanently")
    check(sn.pieces[1][0]["idx"] == 5, "the surviving blue piece is the home one")

    # an UNDALLED red piece sharing a cell with blue does NOT capture: undalled
    # pieces never move, so they can't land on anyone. Verify no capture move is
    # generated from an undalled piece even with a die that "would" reach an enemy.
    red = [pc(11, False)]   # undalled red on (12,0)
    blue = [pc(geo["circuit"][1].index((10, 0)) + H, True)]  # blue passing thru red's home
    s = stt(red, blue, dice=(2, 3), to_move=0)
    # red is undalled & there is no dal in the dice -> red has no moves -> pass.
    check(g.legal_moves(s) == ["pass"], "undalled piece generates no capture (pass)")

    # --- cannot land on your OWN piece -------------------------------------
    red = [pc(12, True), pc(14, True)]  # (12,1) and (10,1)
    s = stt(red, [pc(2, False)], dice=(2, 4), to_move=0)
    check(g._abs_cell(geo, 0, 12) == (12, 1) and g._abs_cell(geo, 0, 14) == (10, 1),
          "two red pieces 2 apart")
    check("12,1>10,1" not in g.legal_moves(s), "cannot land on own piece")

    # --- reach the WIN (remove all enemy pieces) via apply_move ------------
    # Blue has a single piece on (8,1); Red dalled 2 holes behind on (10,1)->idx
    # for red. red idx for (10,1) is circuit index .index((10,1))+H.
    r10 = geo["circuit"][0].index((10, 1)) + H
    b8 = geo["circuit"][1].index((8, 1)) + H
    red = [pc(r10, True)]
    blue = [pc(b8, True)]
    s = stt(red, blue, dice=(2, 4), to_move=0)
    check(g._abs_cell(geo, 0, r10) == (10, 1) and g._abs_cell(geo, 1, b8) == (8, 1),
          "red on (10,1), blue on (8,1)")
    win_move = "10,1>8,1"
    check(win_move in g.legal_moves(s), "red can capture blue's last piece")
    sn = g.apply_move(s, win_move, FixedDice([2, 2]))
    check(sn.winner == 0, "removing all enemy pieces wins")
    check(g.is_terminal(sn), "win state is terminal")
    check(g.returns(sn) == [1.0, -1.0], "returns reflect the winner")
    check(g.legal_moves(sn) == [], "no moves at terminal")

    # --- dal-dal gives an effective extra-turn feel (both dice are dals) ----
    # Both dice are 1: you may dal up to two pieces (the stern, then the next).
    s = g.initial_state(rng=FixedDice([1, 1]))
    check(s.dice == (1, 1), "rolled dal-dal")
    s1 = g.apply_move(s, "12,0>12,1", FixedDice([3, 3]))
    check(s1.to_move == 0 and s1.dice == (1,), "still your turn, one dal left")
    # The next stern-most undalled piece (col 11) may now dal: it advances one
    # hole toward the (now-vacated) stern home hole (12,0). (Only the FIRST dal
    # of all goes straight into the middle row; later dals step up the home row.)
    check("11,0>12,0" in g.legal_moves(s1), "second dal activates the next piece")
    check(g._stern_undalled_index(s1, 0) == 10, "stern-most undalled is now col 11")

    # --- serialize round-trip ---------------------------------------------
    s = stt([pc(0, False), pc(12, True), pc(30, True)],
            [pc(5, True), pc(9, False)], dice=(1, 3), to_move=1, H=12)
    d = g.serialize(s)
    s2 = g.deserialize(d)
    check(g.serialize(s2) == d, "serialize round-trips identically")
    json.dumps(d)

    # --- Danish-size sanity -------------------------------------------------
    sd = g.initial_state(options={"size": "danish"}, rng=FixedDice([1, 2]))
    check(sd.H == 16 and len(sd.pieces[0]) == 16, "Danish: 16 pieces, H=16")

    # --- random seeded full playouts terminate -----------------------------
    for seed in range(30):
        rng = random.Random(seed)
        s = g.initial_state(rng=rng)
        steps = 0
        while not g.is_terminal(s):
            mvs = g.legal_moves(s)
            check(len(mvs) >= 1, "non-terminal always has a move")
            s = g.apply_move(s, rng.choice(mvs), rng)
            steps += 1
            check(steps < 8000, "playout terminates")
        check(s.winner in (0, 1), "playout ends with a winner")

    # --- render is a valid polygons spec -----------------------------------
    spec = g.render(g.initial_state(rng=FixedDice([1, 2])))
    check(spec["board"]["type"] == "polygons", "render is polygons")
    check(isinstance(spec["board"]["cells"], list), "cells is a list")
    check(len(spec["board"]["cells"]) == 12 + 13 + 12, "37 cells")
    for c in spec["board"]["cells"]:
        check("points" in c and "id" in c, "polygons cell has id+points")
    json.dumps(spec)

    print("daldos selftest: all tests passed")


if __name__ == "__main__":
    main()
