"""Pure-stdlib selftest for Senet (Kendall reconstruction).

Anchors: the 30-house boustrophedon mapping; the throw-stick distribution
(1..5, all-black=5); a basic move by the throw; swap-on-lone-enemy and
pair-protection; the three-in-a-row block; the House of Water send-back; the
mandatory stop at House of Happiness; exact bear-off at houses 28/29/30; the win
(all 5 off) reached via apply_move; and a serialize round-trip incl. the throw.

Run: PYTHONPATH=. python3 games/senet/selftest.py
"""

import json
import random
import sys

from games.senet.game import (
    Senet, SenetState, CELLS, CELL_TO_TRACK, track_to_cell, OFF, TRACK,
    NPIECES, HOUSE_REBIRTH, HOUSE_HAPPINESS, HOUSE_WATER,
    HOUSE_THREE_TRUTHS, HOUSE_RE_ATOUM, HOUSE_HORUS,
)


class FixedThrow(random.Random):
    """rng whose randint(0,1) bits force a given Senet throw (1..5), repeating.

    throw 1..4 -> that many white sides (ones) then blacks; throw 5 -> all black.
    """
    def __init__(self, throw):
        super().__init__()
        whites = 0 if throw == 5 else throw
        self._bits = [1] * whites + [0] * (4 - whites)
        self._i = 0

    def randint(self, a, b):
        bit = self._bits[self._i % 4]
        self._i += 1
        return bit


def forced(throw):
    return FixedThrow(throw)


def st(pos0, pos1, throw, to_move=0, winner=None):
    return SenetState(positions={0: sorted(pos0), 1: sorted(pos1)},
                      throw=throw, to_move=to_move, winner=winner)


def cellstr(idx):
    c, r = CELLS[idx]
    return f"{c},{r}"


def mv(src, dest):
    if dest == OFF:
        return f"{cellstr(src)}>off"
    return f"{cellstr(src)}>{cellstr(dest)}"


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def main():
    g = Senet()

    # --- boustrophedon mapping spot checks --------------------------------
    check(track_to_cell(0) == (0, 0), "house 1 -> (0,0)")
    check(track_to_cell(9) == (9, 0), "house 10 -> (9,0)")
    check(track_to_cell(10) == (9, 1), "house 11 -> (9,1) (under house 10)")
    check(track_to_cell(19) == (0, 1), "house 20 -> (0,1) (under house 1)")
    check(track_to_cell(20) == (0, 2), "house 21 -> (0,2)")
    check(track_to_cell(29) == (9, 2), "house 30 -> (9,2)")
    check(len(set(CELLS)) == 30, "30 distinct cells")
    # consecutive houses are grid-adjacent (the S snakes correctly)
    for i in range(TRACK - 1):
        (c0, r0), (c1, r1) = CELLS[i], CELLS[i + 1]
        adj = (abs(c0 - c1) + abs(r0 - r1)) == 1
        check(adj, f"houses {i+1},{i+2} grid-adjacent")

    # --- throw distribution: all throws in 1..5, all-black -> 5 ------------
    rng = random.Random(2024)
    counts = {k: 0 for k in range(1, 6)}
    N = 200000
    for _ in range(N):
        t = Senet._throw(rng)
        check(1 <= t <= 5, f"throw {t} in 1..5")
        counts[t] += 1
    # expected: 1->4/16, 2->6/16, 3->4/16, 4->1/16, 5->1/16
    expected = {1: 4/16, 2: 6/16, 3: 4/16, 4: 1/16, 5: 1/16}
    for k in range(1, 6):
        frac = counts[k] / N
        check(abs(frac - expected[k]) < 0.01,
              f"throw {k}: observed {frac:.4f} vs expected {expected[k]:.4f}")
    # bonus rolls
    check(Senet._bonus(1) and Senet._bonus(4) and Senet._bonus(5), "1/4/5 bonus")
    check(not Senet._bonus(2) and not Senet._bonus(3), "2/3 no bonus")

    # --- initial state: 5 pawns each, interleaved on houses 1..10 ----------
    s0 = g.initial_state(rng=forced(2))
    check(s0.positions[0] == [0, 2, 4, 6, 8], "White start 1,3,5,7,9")
    check(s0.positions[1] == [1, 3, 5, 7, 9], "Black start 2,4,6,8,10")
    check(s0.throw == 2, "initial throw uses supplied rng")

    # --- a basic move by the throw ----------------------------------------
    # White pawn at house 12 (idx 11), throw 3 -> idx 14 (house 15), empty.
    s = st([11], [25], throw=3, to_move=0)  # black far away, no interference
    m = mv(11, 14)
    check(m in g.legal_moves(s), f"basic move {m} legal")
    sn = g.apply_move(s, m, forced(2))
    check(14 in sn.positions[0], "pawn advanced to idx 14")
    check(sn.to_move == 1, "throw 3 ends the turn")

    # --- bonus throw keeps the same player ---------------------------------
    s = st([11], [29], throw=4, to_move=0)
    sn = g.apply_move(s, mv(11, 15), forced(2))
    check(sn.to_move == 0, "throw 4 grants an extra turn (same player)")

    # --- swap a lone enemy pawn back to the source -------------------------
    # White at idx 11, Black lone at idx 13; White throws 2 -> lands on 13.
    s = st([11], [13], throw=2, to_move=0)
    m = mv(11, 13)
    check(m in g.legal_moves(s), "swap move legal vs lone enemy")
    sn = g.apply_move(s, m, forced(2))
    check(13 in sn.positions[0], "White took idx 13")
    check(11 in sn.positions[1], "swapped Black pawn went back to idx 11")

    # --- pair protection: adjacent enemy pawn cannot be swapped ------------
    # Black pawns at idx 13 and 14 (a pair) -> neither is swappable.
    s = st([11], [13, 14], throw=2, to_move=0)
    check(mv(11, 13) not in g.legal_moves(s),
          "cannot swap a protected (paired) enemy pawn")
    # throw 3 -> idx 14 also protected
    s2 = st([11], [13, 14], throw=3, to_move=0)
    check(mv(11, 14) not in g.legal_moves(s2),
          "cannot swap the other protected pawn either")

    # --- cannot land on your own pawn --------------------------------------
    s = st([11, 13], [29], throw=2, to_move=0)
    check(mv(11, 13) not in g.legal_moves(s), "cannot land on own pawn")

    # --- three-in-a-row block: enemy cannot pass --------------------------
    # Black block at idx 12,13,14; White at idx 11 throwing 4 (-> idx 15) must
    # cross the block -> illegal.
    s = st([11], [12, 13, 14], throw=4, to_move=0)
    check(mv(11, 15) not in g.legal_moves(s),
          "enemy may not move past a 3-in-a-row block")
    # a 2-pawn run does NOT block passage (but the landing square rules apply)
    s = st([11], [12, 13, 19], throw=4, to_move=0)  # block of 2, target idx15 free
    check(mv(11, 15) in g.legal_moves(s), "a pair does not block passage")

    # --- House of Water: lands on idx 26 -> sent back to House of Rebirth ---
    # White on House of Happiness (idx 25, already stopped), throw 1 -> idx 26
    # (house 27 = Water).
    s = st([HOUSE_HAPPINESS], [29], throw=1, to_move=0)
    m = mv(HOUSE_HAPPINESS, HOUSE_WATER)
    check(m in g.legal_moves(s), "move onto House of Water legal")
    sn = g.apply_move(s, m, forced(2))
    check(HOUSE_REBIRTH in sn.positions[0], "Water sent pawn back to House 15")
    check(HOUSE_WATER not in sn.positions[0], "pawn no longer on House of Water")

    # House of Water with House 15 occupied -> first empty house before it.
    s = st([HOUSE_HAPPINESS, HOUSE_REBIRTH], [29], throw=1, to_move=0)
    sn = g.apply_move(s, mv(HOUSE_HAPPINESS, HOUSE_WATER), forced(2))
    check(13 in sn.positions[0],
          "Water send-back goes to first empty house before 15 when 15 is taken")

    # --- mandatory stop at House of Happiness (26): cannot overshoot -------
    # White at idx 23 (house 24), throw 4 -> idx 27 overshoots house 26 -> illegal.
    s = st([23], [5], throw=4, to_move=0)
    check(mv(23, 27) not in g.legal_moves(s),
          "cannot pass over the House of Happiness")
    # exact landing on house 26 (idx 25) is allowed: idx 23 + 2.
    s = st([23], [5], throw=2, to_move=0)
    check(mv(23, HOUSE_HAPPINESS) in g.legal_moves(s),
          "may land exactly on House of Happiness")

    # --- exact bear-off at houses 28/29/30 --------------------------------
    # house 28 (idx 27) bears off only on exact 3
    s = st([HOUSE_THREE_TRUTHS], [5], throw=3, to_move=0)
    check(mv(HOUSE_THREE_TRUTHS, OFF) in g.legal_moves(s), "house 28 off on 3")
    s = st([HOUSE_THREE_TRUTHS], [5], throw=2, to_move=0)
    check(g.legal_moves(s) == ["pass"], "house 28 does not bear off on 2")
    # house 29 (idx 28) off on exact 2
    s = st([HOUSE_RE_ATOUM], [5], throw=2, to_move=0)
    check(mv(HOUSE_RE_ATOUM, OFF) in g.legal_moves(s), "house 29 off on 2")
    # house 30 (idx 29) off on 1
    s = st([HOUSE_HORUS], [5], throw=1, to_move=0)
    check(mv(HOUSE_HORUS, OFF) in g.legal_moves(s), "house 30 off on 1")

    # --- no legal move => pass; pass advances the other player -------------
    # White's only pawn at house 28, throw 2 (can't bear off, can't move) -> pass
    s = st([HOUSE_THREE_TRUTHS], [5], throw=2, to_move=0)
    check(g.legal_moves(s) == ["pass"], "stuck -> only pass")
    sn = g.apply_move(s, "pass", forced(3))
    check(sn.to_move == 1, "pass advances to the other player")

    # --- reach the win (all 5 off) via apply_move --------------------------
    # 4 already off, last at house 30 (idx 29), throw 1 -> bears off -> win.
    pos0 = [OFF, OFF, OFF, OFF, HOUSE_HORUS]
    s = st(pos0, [5, 6, 7, 8, 9], throw=1, to_move=0)
    sn = g.apply_move(s, mv(HOUSE_HORUS, OFF), forced(2))
    check(sn.winner == 0, "bearing off the 5th pawn wins")
    check(g.is_terminal(sn), "winning state is terminal")
    check(g.returns(sn) == [1.0, -1.0], "returns reflect the winner")
    check(g.legal_moves(sn) == [], "no moves at terminal")

    # --- serialize round-trip (incl. throw, off pawns) ---------------------
    s = st([0, 14, OFF, 26, HOUSE_HORUS], [3, OFF, 8, HOUSE_RE_ATOUM, 25],
           throw=5, to_move=1, winner=None)
    d = g.serialize(s)
    s2 = g.deserialize(d)
    check(g.serialize(s2) == d, "serialize round-trips identically")
    json.dumps(d)  # must be JSON-able

    # --- random playouts terminate quickly --------------------------------
    for seed in range(40):
        rng = random.Random(seed)
        s = g.initial_state(rng=rng)
        steps = 0
        while not g.is_terminal(s):
            mvs = g.legal_moves(s)
            check(len(mvs) >= 1, "non-terminal state always has a move")
            s = g.apply_move(s, rng.choice(mvs), rng)
            steps += 1
            check(steps < 4000, "playout terminates")
        check(s.winner in (0, 1), "playout ends with a winner")

    # --- render is the 10x3 square board with special-house tints ----------
    spec = g.render(g.initial_state(rng=forced(3)))
    check(spec["board"]["type"] == "square", "render is square")
    check(spec["board"]["width"] == 10 and spec["board"]["height"] == 3,
          "render is 10x3")
    check(len(spec["board"]["tints"]) == 6, "render tints the 6 special houses")
    check(len(spec["pieces"]) == 10, "render shows all 10 pawns at start")
    check("threw 3" in spec["caption"], "caption shows the throw")

    print("senet selftest: all tests passed")


if __name__ == "__main__":
    main()
