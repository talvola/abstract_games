"""Pure-stdlib selftest for The Royal Game of Ur.

Anchors: path length, the binomial(4,1/2) dice distribution, rosette extra
turn, capture-sends-home on the shared lane, rosette safety, exact bear-off,
the win at 7 borne-off reached via apply_move, and a serialize round-trip.

Run: PYTHONPATH=. python3 games/royal_game_of_ur/selftest.py
"""

import random
import sys

from games.royal_game_of_ur.game import (
    RoyalGameOfUr, UrState, PATH, PATH_LEN, ROSETTES, NPIECES, _is_shared,
)


class FixedRoll(random.Random):
    """An rng whose randint(0,1) bits sum to a forced 0..4 roll, then repeats."""
    def __init__(self, value):
        super().__init__()
        self._bits = [1] * value + [0] * (4 - value)
        self._i = 0

    def randint(self, a, b):
        bit = self._bits[self._i % 4]
        self._i += 1
        return bit


def forced(value):
    return FixedRoll(value)


def st(pos0, pos1, roll, to_move=0, winner=None):
    return UrState(positions={0: list(pos0), 1: list(pos1)},
                   roll=roll, to_move=to_move, winner=winner)


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def main():
    g = RoyalGameOfUr()

    # --- path length -------------------------------------------------------
    check(PATH_LEN == 14, "path length is 14")
    for pl in (0, 1):
        check(len(PATH[pl]) == 14, f"player {pl} path has 14 squares")
        check(len(set(PATH[pl])) == 14, f"player {pl} path has no repeats")
    # shared lane is the 8 middle squares; players share exactly those.
    shared0 = [c for c in PATH[0] if _is_shared(c)]
    shared1 = [c for c in PATH[1] if _is_shared(c)]
    check(len(shared0) == 8 and shared0 == shared1, "8 shared squares, identical")
    check(len(ROSETTES) == 5, "exactly 5 rosettes")

    # --- dice distribution is binomial(4, 1/2) ----------------------------
    rng = random.Random(12345)
    counts = {k: 0 for k in range(5)}
    N = 200000
    for _ in range(N):
        counts[RoyalGameOfUr._roll(rng)] += 1
    expected = {0: 1 / 16, 1: 4 / 16, 2: 6 / 16, 3: 4 / 16, 4: 1 / 16}
    for k in range(5):
        frac = counts[k] / N
        check(abs(frac - expected[k]) < 0.01,
              f"roll {k}: observed {frac:.4f} vs expected {expected[k]:.4f}")

    # --- a roll of 0 => only legal move is pass; apply just re-rolls/passes -
    s0 = st([-1] * NPIECES, [-1] * NPIECES, roll=0)
    check(g.legal_moves(s0) == ["pass"], "roll 0 -> only pass")
    s0n = g.apply_move(s0, "pass", forced(2))
    check(s0n.to_move == 1, "pass advances to the other player")

    # --- entry move + first roll comes from initial_state's rng ------------
    # Entry from off-board lands on path index (roll-1): roll 3 -> idx 2 =(1,0).
    s_init = g.initial_state(rng=forced(3))
    check(s_init.roll == 3, "initial roll uses supplied rng")
    check(PATH[0][2] == (1, 0), "path idx 2 is (1,0)")
    check(g.legal_moves(s_init) == ["1,0"],
          f"roll 3 entry -> path idx 2 = (1,0); got {g.legal_moves(s_init)}")

    # --- rosette extra turn (idx 3 is a rosette) ---------------------------
    # roll 4 from off -> path idx 3 = (0,0), a rosette -> extra turn.
    s = st([-1] * NPIECES, [-1] * NPIECES, roll=4, to_move=0)
    check(PATH[0][3] == (0, 0) and PATH[0][3] in ROSETTES, "path idx 3 = (0,0) rosette")
    check(g.legal_moves(s) == ["0,0"], f"roll 4 entry -> (0,0); got {g.legal_moves(s)}")
    sn = g.apply_move(s, "0,0", forced(1))
    check(sn.to_move == 0, "rosette landing keeps the same player (extra turn)")
    check(sn.roll == 1, "extra turn re-rolls")

    # --- a non-rosette landing passes the turn -----------------------------
    # roll 2 from off -> path idx 1 = (2,0), not a rosette.
    s = st([-1] * NPIECES, [-1] * NPIECES, roll=2, to_move=0)
    check(PATH[0][1] == (2, 0) and PATH[0][1] not in ROSETTES, "idx 1 (2,0) not rosette")
    sn = g.apply_move(s, "2,0", forced(2))
    check(sn.to_move == 1, "non-rosette landing passes the turn")

    # --- capture on a shared square sends enemy home -----------------------
    # White piece at shared idx 5; Black piece on the SAME cell (idx 5 of its
    # path -- shared squares coincide).  White rolls so as to land there? Set up
    # White just behind at idx 4 with roll 1.
    target_idx = 5
    cell = PATH[0][target_idx]
    check(_is_shared(cell), "target is a shared square")
    bidx = PATH[1].index(cell)
    pos0 = [4] + [-1] * (NPIECES - 1)   # White piece at idx 4
    pos1 = [bidx] + [-1] * (NPIECES - 1)  # Black piece sitting on the cell
    s = st(pos0, pos1, roll=1, to_move=0)
    # Confirm the move is legal and is a capture per describe_move.
    mv = f"{PATH[0][4][0]},{PATH[0][4][1]}>{cell[0]},{cell[1]}"
    check(mv in g.legal_moves(s), f"capture move {mv} is legal")
    sn = g.apply_move(s, mv, forced(0))
    check(sn.positions[1][0] == -1, "captured enemy sent off-board (-1)")
    check(sn.positions[0][0] == target_idx, "White moved onto the shared cell")

    # --- rosette safety: enemy may not land on an occupied rosette ---------
    # The shared rosette is at path idx 7 for both players. Put a Black piece on
    # it; White just behind (idx 6) rolling 1 should NOT be able to land there.
    ros_cell = PATH[0][7]
    check(ros_cell in ROSETTES and _is_shared(ros_cell), "idx 7 shared rosette")
    bidx = PATH[1].index(ros_cell)
    pos0 = [6] + [-1] * (NPIECES - 1)
    pos1 = [bidx] + [-1] * (NPIECES - 1)
    s = st(pos0, pos1, roll=1, to_move=0)
    blocked = f"{PATH[0][6][0]},{PATH[0][6][1]}>{ros_cell[0]},{ros_cell[1]}"
    check(blocked not in g.legal_moves(s),
          "cannot land on an enemy piece sitting on a rosette (safe)")

    # --- cannot land on your own piece -------------------------------------
    pos0 = [4, 5] + [-1] * (NPIECES - 2)   # one at idx4, one at idx5
    s = st(pos0, [-1] * NPIECES, roll=1, to_move=0)
    # idx4 + 1 -> idx5 is occupied by own piece -> that move illegal.
    bad = f"{PATH[0][4][0]},{PATH[0][4][1]}>{PATH[0][5][0]},{PATH[0][5][1]}"
    check(bad not in g.legal_moves(s), "cannot land on own piece")

    # --- bear off requires an EXACT roll -----------------------------------
    # Piece at idx 12 (one before last). Needs exactly 2 to bear off (12+2=14).
    pos0 = [12] + [PATH_LEN] * (NPIECES - 1)  # rest already home
    # roll 3 overshoots -> no move -> pass.
    s = st(pos0, [-1] * NPIECES, roll=3, to_move=0)
    check(g.legal_moves(s) == ["pass"], "overshoot roll cannot bear off (pass)")
    # roll 2 is exact -> bear off.
    s = st(pos0, [-1] * NPIECES, roll=2, to_move=0)
    cur = PATH[0][12]
    bear = f"{cur[0]},{cur[1]}>off"
    check(bear in g.legal_moves(s), "exact roll allows bear-off")

    # --- reach the win (7 borne off) via apply_move ------------------------
    pos0 = [12] + [PATH_LEN] * (NPIECES - 1)  # 6 home, last at idx 12
    s = st(pos0, [-1] * NPIECES, roll=2, to_move=0)
    sn = g.apply_move(s, bear, forced(0))
    check(sn.winner == 0, "bearing off the 7th piece wins")
    check(g.is_terminal(sn), "winning state is terminal")
    check(g.returns(sn) == [1.0, -1.0], "returns reflect the winner")
    check(g.legal_moves(sn) == [], "no moves at terminal")

    # --- serialize round-trip (incl. roll, off & borne-off encoded in pos) -
    s = st([-1, 0, 5, PATH_LEN, 7, -1, 13], [3, -1, PATH_LEN, 8, -1, 1, 2],
           roll=3, to_move=1, winner=None)
    d = g.serialize(s)
    s2 = g.deserialize(d)
    check(g.serialize(s2) == d, "serialize round-trips identically")
    import json
    json.dumps(d)  # must be JSON-able

    # --- a few random full playouts terminate quickly ----------------------
    for seed in range(40):
        rng = random.Random(seed)
        s = g.initial_state(rng=rng)
        steps = 0
        while not g.is_terminal(s):
            mvs = g.legal_moves(s)
            check(len(mvs) >= 1, "non-terminal state always has a move")
            s = g.apply_move(s, rng.choice(mvs), rng)
            steps += 1
            check(steps < 5000, "playout terminates")
        check(s.winner in (0, 1), "playout ends with a winner")

    # render must not crash and must be the polygons H-shape with tints.
    spec = g.render(g.initial_state(rng=forced(2)))
    check(spec["board"]["type"] == "polygons", "render is polygons")
    check(len(spec["board"]["cells"]) == 20, "render has 20 cells")
    check(len(spec["board"]["tints"]) == 5, "render tints 5 rosettes")
    for c in spec["board"]["cells"]:
        check("points" in c and "id" in c, "polygons cell has id+points")

    print("royal_game_of_ur selftest: all tests passed")


if __name__ == "__main__":
    main()
