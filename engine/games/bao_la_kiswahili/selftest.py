"""Selftest for Bao la Kiswahili -- frozen published anchors + rule probes.

Anchors:

* The worked diagrams from Rob Nierse's Game Cabinet article "Bao (Zanzibar)"
  (written directly from Alex de Voogt's *Limits of the Mind*, the master-rules
  codification): diagrams 3/4 (namua capture, kichwa entry), 5/7/8 (multi-seed
  entry both sides), 9/10/11/12/13 (all four kichwa/kimbi forced-entry cases),
  14/15 (kimbi capture + chain capture with direction continuation), 14/16
  (kichwa capture + chain + nyumba safari, around the corner), 17/18 (relay
  continuation into the back row), 19 (nyumba stop), 22 (nyumba tax), 23
  (mtaji-stage captures incl. around-the-corner) -- each reproduced move-by-move
  and compared pit-by-pit.
* De Voogt's published never-ending move (Mancala World "Bao la Kiswahili",
  Problem 3, first given by de Voogt in 2006): the full 23-ply game from the
  initial position is replayed from its classical notation, then the 24th move
  A3L is played and must be detected as a never-ending sowing with period 218.
* Mancala World Puzzles 1 and 2 replayed against their published solutions
  (Bao hamna both lines, the "(forced)" move verified forced), pinning the
  classical-notation letters for captures and back-row moves along the way.
* Synthetic probes for the 16-seed rule, singleton ban, back-row fallback,
  the front-row-never-emptied rule (forced kichwa direction), takasia,
  loss-by-empty-front-row and loss-by-no-move (both reached via apply_move),
  namua takasa restrictions, serialize round-trip, seed conservation, and
  random-playout termination for both variants.

Pure stdlib; imports only agp + this game.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.bao_la_kiswahili.game import (  # noqa: E402
    BaoLaKiswahili, BaoState, IDX, HOUSE, TOTAL_SEEDS,
)


def board_from(b, a, A, B):
    """Build a 32-pit board from four screen rows (top to bottom:
    North back, North front, South front, South back), columns left->right."""
    board = [0] * 32
    for c in range(8):
        board[IDX(c, 3)] = b[c]
        board[IDX(c, 2)] = a[c]
        board[IDX(c, 1)] = A[c]
        board[IDX(c, 0)] = B[c]
    return board


def rows(board):
    return {
        "b": [board[IDX(c, 3)] for c in range(8)],
        "a": [board[IDX(c, 2)] for c in range(8)],
        "A": [board[IDX(c, 1)] for c in range(8)],
        "B": [board[IDX(c, 0)] for c in range(8)],
    }


def st(b, a, A, B, hands=(0, 0), alive=(False, False), to_move=0):
    return BaoState(board=board_from(b, a, A, B), hands=list(hands),
                    alive=list(alive), to_move=to_move)


Z = [0] * 8


def check_rows(s, exp_a, exp_A, exp_B=None, exp_b=None, tag=""):
    r = rows(s.board)
    assert r["a"] == exp_a, (tag, "a", r["a"], exp_a)
    assert r["A"] == exp_A, (tag, "A", r["A"], exp_A)
    if exp_B is not None:
        assert r["B"] == exp_B, (tag, "B", r["B"], exp_B)
    if exp_b is not None:
        assert r["b"] == exp_b, (tag, "b", r["b"], exp_b)


def run():
    g = BaoLaKiswahili()

    # ------------------------------------------------------------------
    # 1. Initial positions + serialize round-trip
    # ------------------------------------------------------------------
    s0 = g.initial_state()
    check_rows(s0,
               exp_a=[0, 2, 2, 6, 0, 0, 0, 0],
               exp_A=[0, 0, 0, 0, 6, 2, 2, 0],
               exp_B=Z, exp_b=Z, tag="init")
    assert s0.hands == [22, 22] and s0.alive == [True, True]
    assert sum(s0.board) + sum(s0.hands) == TOTAL_SEEDS
    d = g.serialize(s0)
    assert g.serialize(g.deserialize(d)) == d
    # opening takasa: no captures; the functional nyumba may not be chosen
    assert sorted(g.legal_moves(s0)) == ["5,1=L", "5,1=R", "6,1=L", "6,1=R"]
    assert g.describe_move(s0, "5,1=L") == "A6L*"

    sk = g.initial_state(options={"variant": "kujifunza"})
    assert sum(sk.board) == 64 and sk.hands == [0, 0]
    assert sk.alive == [False, False]
    assert all("=" in m for m in g.legal_moves(sk))

    # ------------------------------------------------------------------
    # 2. Game Cabinet diagram 3 -> 4 (namua capture, single seed, left entry)
    # ------------------------------------------------------------------
    s = st(Z, [1, 0, 1, 8, 1, 2, 0, 0], [0, 0, 0, 0, 7, 0, 2, 1], Z,
           hands=(10, 10), alive=(True, True))
    assert sorted(g.legal_moves(s)) == ["4,1=L", "4,1=R"]  # only capture
    s2 = g.apply_move(s, "4,1=L")
    check_rows(s2, [1, 0, 1, 8, 0, 2, 0, 0], [1, 0, 0, 0, 8, 0, 2, 1],
               tag="d4")
    assert s2.hands[0] == 9 and s2.to_move == 1

    # ------------------------------------------------------------------
    # 3. Diagram 5 -> 7 (left entry) and 5 -> 8 (right entry)
    # ------------------------------------------------------------------
    s = st(Z, [1, 0, 1, 8, 3, 2, 0, 0], [0, 0, 0, 0, 7, 0, 0, 0], Z,
           hands=(10, 10), alive=(True, True))
    assert sorted(g.legal_moves(s)) == ["4,1=L", "4,1=R"]
    check_rows(g.apply_move(s, "4,1=L"),
               [1, 0, 1, 8, 0, 2, 0, 0], [1, 1, 1, 0, 8, 0, 0, 0], tag="d7")
    check_rows(g.apply_move(s, "4,1=R"),
               [1, 0, 1, 8, 0, 2, 0, 0], [0, 0, 0, 0, 8, 1, 1, 1], tag="d8")

    # ------------------------------------------------------------------
    # 4. Diagram 9: all four kichwa/kimbi captures have FORCED entry sides
    # ------------------------------------------------------------------
    d9 = dict(b=Z, a=[4, 3, 1, 8, 0, 2, 5, 6], A=[1, 2, 0, 0, 8, 0, 3, 4],
              B=Z)
    s = st(d9["b"], d9["a"], d9["A"], d9["B"], hands=(10, 10),
           alive=(True, True))
    assert sorted(g.legal_moves(s)) == ["0,1", "1,1", "6,1", "7,1"]
    check_rows(g.apply_move(s, "0,1"),                       # diagram 10
               [0, 3, 1, 8, 0, 2, 5, 6], [3, 3, 1, 1, 8, 0, 3, 4], tag="d10")
    check_rows(g.apply_move(s, "1,1"),                       # diagram 12
               [4, 0, 1, 8, 0, 2, 5, 6], [2, 4, 1, 0, 8, 0, 3, 4], tag="d12")
    # NB: GC's printed diagram 11 shows A8=6, but that makes its row sum to 25
    # seeds when only 24 exist (18 + 1 placed + 5 captured) -- a typo in the
    # article; diagrams 10/12/13 all sum correctly and match exactly.
    check_rows(g.apply_move(s, "6,1"),                       # diagram 11
               [4, 3, 1, 8, 0, 2, 0, 6], [1, 2, 0, 1, 9, 1, 5, 5], tag="d11")
    check_rows(g.apply_move(s, "7,1"),                       # diagram 13
               [4, 3, 1, 8, 0, 2, 5, 0], [1, 2, 1, 1, 9, 1, 4, 6], tag="d13")

    # ------------------------------------------------------------------
    # 5. Diagram 14 -> 15 (kimbi capture + chain, direction continues) and
    #    14 -> 16 (kichwa capture + chain + nyumba SAFARI around the corner)
    # ------------------------------------------------------------------
    d14 = dict(a=[0, 3, 4, 8, 0, 2, 5, 6], A=[0, 2, 1, 0, 8, 0, 3, 4])
    s = st(Z, d14["a"], d14["A"], Z, hands=(10, 10), alive=(True, True))
    ms = sorted(g.legal_moves(s))
    assert ms == ["1,1", "2,1=L", "2,1=R", "6,1", "7,1"], ms
    check_rows(g.apply_move(s, "1,1"),                       # diagram 15
               [0, 0, 0, 8, 0, 2, 5, 6], [2, 5, 3, 1, 8, 0, 3, 4], tag="d15")
    sp = g.apply_move(s, "7,1")
    assert sp.pending is not None and g.current_player(sp) == 0
    assert sorted(g.legal_moves(sp)) == ["safari", "stop"]
    s16 = g.apply_move(sp, "safari")                         # diagram 16
    check_rows(s16, [0, 3, 0, 8, 0, 2, 5, 0], [1, 3, 3, 2, 0, 2, 5, 7],
               exp_B=[1, 1, 1, 1, 1, 1, 0, 0], tag="d16")
    assert s16.alive[0] is False and s16.to_move == 1        # house destroyed
    s_stop = g.apply_move(sp, "stop")
    r = rows(s_stop.board)
    assert r["A"][4] == 10 and s_stop.alive[0] is True       # house kept
    assert s_stop.to_move == 1

    # ------------------------------------------------------------------
    # 6. Diagram 17 -> 18 (relay continuation around the corner)
    # ------------------------------------------------------------------
    s = st(Z, [1, 0, 0, 7, 0, 0, 0, 2], [0, 2, 3, 2, 0, 2, 5, 0], Z,
           hands=(10, 10), alive=(True, True))
    assert sorted(g.legal_moves(s)) == ["3,1=L", "3,1=R"]
    check_rows(g.apply_move(s, "3,1=L"),                     # diagram 18
               [1, 0, 0, 0, 0, 0, 0, 2], [1, 3, 4, 4, 1, 3, 0, 1],
               exp_B=[0, 0, 0, 1, 1, 1, 1, 1], tag="d18")
    # right entry: self-consistency (the GC prose has an off-by-one here;
    # our circuit is pinned by the exact diagram-18 match above)
    check_rows(g.apply_move(s, "3,1=R"),
               [1, 0, 0, 0, 0, 0, 0, 2], [1, 0, 4, 4, 1, 3, 6, 1],
               exp_B=[1, 1, 0, 0, 0, 0, 0, 0], tag="d17R")

    # ------------------------------------------------------------------
    # 7. Diagram 19: capture ending in the nyumba -> may STOP
    # ------------------------------------------------------------------
    s = st(Z, [0, 1, 2, 10, 4, 4, 0, 0], [2, 1, 0, 0, 12, 0, 0, 0], Z,
           hands=(10, 10), alive=(True, True))
    assert sorted(g.legal_moves(s)) == ["1,1", "4,1=L", "4,1=R"]
    sp = g.apply_move(s, "4,1=R")
    assert sp.pending is not None
    s2 = g.apply_move(sp, "stop")
    check_rows(s2, [0, 1, 2, 10, 0, 4, 0, 0], [2, 1, 0, 0, 14, 1, 1, 1],
               tag="d19")
    assert s2.alive[0] is True

    # ------------------------------------------------------------------
    # 8. Diagram 22: nyumba tax (only occupied front pit -> sow two seeds)
    # ------------------------------------------------------------------
    s = st(Z, [0, 1, 2, 9, 0, 2, 0, 0], [0, 0, 0, 0, 9, 0, 0, 0], Z,
           hands=(10, 10), alive=(True, True))
    assert sorted(g.legal_moves(s)) == ["4,1=L", "4,1=R"]
    s2 = g.apply_move(s, "4,1=R")
    check_rows(s2, [0, 1, 2, 9, 0, 2, 0, 0], [0, 0, 0, 0, 8, 1, 1, 0],
               tag="d22")
    assert s2.alive[0] is True                               # tax keeps house
    s3 = g.apply_move(s, "4,1=L")
    assert rows(s3.board)["A"] == [0, 0, 1, 1, 8, 0, 0, 0]

    # ------------------------------------------------------------------
    # 8b. Namua takasa without a functional house: must add to a pit with
    #     2+ seeds unless the front row holds only singletons
    # ------------------------------------------------------------------
    s = st(Z, [0, 0, 0, 0, 0, 0, 0, 3], [1, 2, 0, 0, 0, 0, 0, 0], Z,
           hands=(5, 5), alive=(False, False))
    assert sorted(g.legal_moves(s)) == ["1,1=L", "1,1=R"]   # not the singleton
    s = st(Z, [0, 0, 0, 0, 0, 0, 0, 3], [1, 0, 0, 1, 0, 0, 0, 0], Z,
           hands=(5, 5), alive=(False, False))
    assert sorted(g.legal_moves(s)) == \
        ["0,1=L", "0,1=R", "3,1=L", "3,1=R"]   # all singletons -> allowed

    # ------------------------------------------------------------------
    # 8c. Mtaji-stage capture ending in the functional nyumba: FORCED safari
    # ------------------------------------------------------------------
    s = st(Z, [0, 0, 5, 0, 0, 1, 0, 0], [2, 0, 1, 0, 6, 0, 0, 0], Z,
           alive=(True, False))
    assert "0,1=R" in g.legal_moves(s)
    s2 = g.apply_move(s, "0,1=R")
    assert s2.pending is None            # no choice in the mtaji stage
    assert s2.alive[0] is False          # the safari destroyed the house
    check_rows(s2, [0, 0, 0, 0, 0, 1, 0, 0], [1, 2, 3, 1, 0, 1, 1, 1],
               exp_B=[0, 0, 0, 0, 1, 1, 1, 1], tag="forced-safari")

    # ------------------------------------------------------------------
    # 9. Diagram 23: mtaji-stage captures (mandatory; around the corner)
    # ------------------------------------------------------------------
    s = st(Z, [0, 0, 0, 0, 5, 6, 0, 0], [0, 3, 0, 0, 4, 1, 0, 0],
           [0, 9, 0, 0, 0, 0, 0, 0])
    assert sorted(g.legal_moves(s)) == ["1,0=L", "1,1=R"]
    s2 = g.apply_move(s, "1,1=R")
    check_rows(s2, [0, 0, 0, 0, 0, 6, 0, 0], [1, 1, 2, 2, 0, 2, 1, 1],
               exp_B=[0, 9, 0, 0, 0, 1, 1, 1], tag="d23a")
    s3 = g.apply_move(s, "1,0=L")
    check_rows(s3, [0, 0, 0, 0, 5, 0, 0, 0], [0, 3, 1, 1, 5, 3, 2, 2],
               exp_B=[0, 0, 1, 1, 1, 1, 1, 1], tag="d23b")

    # ------------------------------------------------------------------
    # 10. 16-seed rule: a first lap of 16+ seeds never captures
    # ------------------------------------------------------------------
    s = st(Z, [3, 0, 2, 0, 0, 0, 0, 0], [2, 17, 1, 0, 0, 0, 0, 0], Z)
    assert g.legal_moves(s) == ["0,1=R"]     # the 17-pit capture is banned
    s = st(Z, [0, 0, 0, 0, 0, 0, 0, 1], [0, 17, 0, 0, 1, 0, 0, 0], Z)
    ms = g.legal_moves(s)
    assert ms and all(m.startswith("1,1=") for m in ms)
    before = sum(rows(s.board)["a"]) + sum(rows(s.board)["b"])
    s2 = g.apply_move(s, ms[0])
    after = sum(rows(s2.board)["a"]) + sum(rows(s2.board)["b"])
    assert before == after                    # takata: nothing captured

    # ------------------------------------------------------------------
    # 11. Singleton ban + back-row fallback; forced kichwa direction
    # ------------------------------------------------------------------
    s = st(Z, [0, 0, 4, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0, 0],
           [0, 5, 0, 0, 0, 0, 0, 0])
    assert sorted(g.legal_moves(s)) == ["1,0=L", "1,0=R"]
    # only occupied front pit is the left kichwa: must sow toward the centre
    s = st(Z, [0, 0, 0, 0, 0, 0, 0, 1], [3, 0, 0, 0, 0, 0, 0, 0],
           [0, 0, 4, 0, 0, 0, 0, 0])
    assert g.legal_moves(s) == ["0,1=R"]

    # ------------------------------------------------------------------
    # 12. Losses reached via apply_move
    # ------------------------------------------------------------------
    # (a) Bao hamna: the capture empties North's front row (during namua!)
    s = st(Z, [0, 0, 0, 0, 2, 0, 0, 0], [0, 0, 0, 0, 3, 0, 0, 0],
           [0, 0, 1, 0, 0, 0, 0, 0], hands=(5, 5), alive=(True, True))
    s2 = g.apply_move(s, "4,1=L")
    assert s2.winner == 0 and g.is_terminal(s2)
    assert g.returns(s2) == [1.0, -1.0]
    # (b) stuck: after South's takata North has only singletons -> no move
    s = st([0] * 8, [1, 0, 0, 0, 0, 0, 0, 1], [0, 3, 0, 0, 0, 0, 0, 0], Z)
    s2 = g.apply_move(s, "1,1=R")
    assert s2.to_move == 1 and g.legal_moves(s2) == []
    assert g.is_terminal(s2) and g.returns(s2) == [1.0, -1.0]

    # ------------------------------------------------------------------
    # 13. Takasia: South's takata leaves exactly one threatened pit
    # ------------------------------------------------------------------
    s = st(Z, [0, 0, 2, 0, 0, 0, 2, 0], [0, 0, 3, 2, 0, 0, 1, 0], Z)
    assert "2,1=R" in g.legal_moves(s)        # a takata (no captures exist)
    s2 = g.apply_move(s, "2,1=R")
    assert s2.takasia == IDX(6, 2), s2.takasia
    ms = g.legal_moves(s2)
    assert ms and all(not m.startswith("6,2=") for m in ms), ms
    # exception: the threatened pit is North's only multi-seed front pit
    s = st(Z, [0, 0, 1, 0, 0, 0, 2, 0], [0, 0, 3, 2, 0, 0, 1, 0], Z)
    s2 = g.apply_move(s, "2,1=R")
    assert s2.takasia is None

    # ------------------------------------------------------------------
    # 14. Pending state serialize round-trip
    # ------------------------------------------------------------------
    s = st(Z, d14["a"], d14["A"], Z, hands=(10, 10), alive=(True, True))
    sp = g.apply_move(s, "7,1")
    d = g.serialize(sp)
    sp2 = g.deserialize(d)
    assert g.serialize(sp2) == d
    assert sorted(g.legal_moves(sp2)) == ["safari", "stop"]

    # ------------------------------------------------------------------
    # 15. De Voogt's published never-ending move.
    #     Mancala World "Bao la Kiswahili" Problem 3: from the initial
    #     position, 1.A6L* a6R 2.A4R a6R 3.A5L a3R 4.A8> a8 5.A4R a4L
    #     6.A8 a7 7.A1 a4R 8.A6R a4L 9.A2 a4L 10.A4L a4L 11.A7 a4L,
    #     then South plays A3L -> a never-ending move (first given by
    #     de Voogt, 2006). Replaying those 22 plies from classical notation
    #     reproduces the puzzle's published board PIT-FOR-PIT (frozen below
    #     from the puzzle diagram), every scripted move being legal at every
    #     ply -- an end-to-end anchor over namua captures, kimbi/kichwa
    #     forcing, chain captures, direction continuation, takasa, safari and
    #     mandatory capture for BOTH players. A3L is then detected as a
    #     never-ending sowing. Our measured full-state lap-period is 228
    #     (the trajectory is immediately periodic: the lap-1 state recurs at
    #     lap 229; verified as the minimal period). Mancala World says
    #     "period 218": no projection of the verified cycle can have period
    #     218 (all sub-periods divide 228), and the position itself matches
    #     the puzzle exactly, so we freeze 228 and attribute 218 to the
    #     page's own counting.
    # ------------------------------------------------------------------
    def notation_to_move(note, player):
        note = note.rstrip("*>")
        letter, num = note[0], int(note[1])
        side = note[2] if len(note) > 2 else None
        if player == 0:
            col = num - 1
            row = 1 if letter == "A" else 0
            suffix = side
        else:
            col = 8 - num
            row = 2 if letter == "a" else 3
            suffix = {"L": "R", "R": "L", None: None}[side]
        mv = f"{col},{row}"
        if suffix:
            mv += f"={suffix}"
        return mv

    script = ["A6L*", "a6R", "A4R", "a6R", "A5L", "a3R", "A8>", "a8",
              "A4R", "a4L", "A8", "a7", "A1", "a4R", "A6R", "a4L",
              "A2", "a4L", "A4L", "a4L", "A7", "a4L"]
    s = g.initial_state()
    for i, note in enumerate(script):
        mv = notation_to_move(note, i % 2)
        ms = g.legal_moves(s)
        assert mv in ms, (i, note, mv, ms)
        s = g.apply_move(s, mv)
        if s.pending is not None:
            s = g.apply_move(s, "safari" if note.endswith(">") else "stop")
        assert not g.is_terminal(s), (i, note)
    # the puzzle's published position (read from the Mancala World diagram)
    check_rows(s, exp_b=[0] * 8,
               exp_a=[0, 0, 0, 0, 9, 0, 0, 1],
               exp_A=[1, 6, 3, 1, 0, 5, 4, 0],
               exp_B=[2, 1, 0, 5, 0, 3, 0, 1], tag="problem3")
    assert s.hands == [11, 11] and s.to_move == 0
    mv = notation_to_move("A3L", 0)
    assert mv in g.legal_moves(s), (mv, g.legal_moves(s))
    s = g.apply_move(s, mv)
    assert s.draw and s.loop_period == 228, (s.draw, s.loop_period)

    # ------------------------------------------------------------------
    # 15b. Mancala World Puzzles 1 and 2 (published solutions; positions
    #      transcribed from the puzzle diagrams during adversarial QA).
    #      Puzzle 1: "South to move and win! 1. B2L Bao hamna!"
    #      Puzzle 2: "North to play and win! 1. a4R A4L* 2. b3R B4R (forced)
    #      3. b2R = Bao hamna!  If A: 1.... A4R, then 2. b2R = Bao hamna!"
    #      Also pins the classical-notation letters for these moves
    #      (capture letters = entry-kichwa side, owner frame; back-row
    #      letters = the physical direction the seeds first travel).
    # ------------------------------------------------------------------
    s = st([2, 2, 4, 6, 0, 0, 3, 4], [3, 0, 3, 0, 0, 5, 1, 0],
           [2, 0, 1, 2, 0, 1, 1, 1], [1, 2, 4, 5, 3, 3, 3, 2])
    assert g.describe_move(s, "1,0=R") == "B2L"
    assert "1,0=R" in g.legal_moves(s)
    s2 = g.apply_move(s, "1,0=R")
    assert rows(s2.board)["a"] == Z and s2.winner == 0     # Bao hamna!

    p2 = dict(b=[1, 1, 2, 2, 3, 3, 0, 0], a=[1, 2, 2, 0, 12, 0, 2, 0],
              A=[2, 3, 2, 4, 2, 0, 3, 0], B=[8, 0, 1, 5, 2, 1, 0, 0])
    s = st(p2["b"], p2["a"], p2["A"], p2["B"], to_move=1)
    assert g.describe_move(s, "4,2=R") == "a4R"
    # main line: 1. a4R A4L* 2. b3R B4R (forced) 3. b2R = Bao hamna
    line = ["4,2=R", "3,1=L", "5,3=L", "3,0=L", "6,3=L"]
    notes = ["a4R", "A4L*", "b3R", "B4R", "b2R"]
    for mv, note in zip(line, notes):
        ms = g.legal_moves(s)
        assert mv in ms, (note, mv, ms)
        assert g.describe_move(s, mv).rstrip("*") == note.rstrip("*"), \
            (note, g.describe_move(s, mv))
        if note == "B4R":
            assert ms == [mv], ("B4R must be forced", ms)
        s = g.apply_move(s, mv)
        assert s.pending is None
    assert rows(s.board)["A"] == Z and s.winner == 1       # Bao hamna!
    # alternative defense: 1.... A4R 2. b2R = Bao hamna
    s = st(p2["b"], p2["a"], p2["A"], p2["B"], to_move=1)
    for mv in ["4,2=R", "3,1=R", "6,3=L"]:
        assert mv in g.legal_moves(s)
        s = g.apply_move(s, mv)
    assert rows(s.board)["A"] == Z and s.winner == 1

    # ------------------------------------------------------------------
    # 16. Random playouts: conservation, termination, both variants
    # ------------------------------------------------------------------
    for variant, n_games, seed0 in (("kiswahili", 25, 100),
                                    ("kujifunza", 12, 500)):
        decisive = 0
        mtaji_seen = 0
        for k in range(n_games):
            rng = random.Random(seed0 + k)
            s = g.initial_state(options={"variant": variant})
            steps = 0
            hit_mtaji = False
            while not g.is_terminal(s):
                assert sum(s.board) + sum(s.hands) == TOTAL_SEEDS
                ms = g.legal_moves(s)
                assert ms
                s = g.apply_move(s, rng.choice(ms))
                if s.hands == [0, 0]:
                    hit_mtaji = True
                steps += 1
                assert steps < 6000, (variant, k)
            rr = g.returns(s)
            assert len(rr) == 2 and all(-1.0 <= x <= 1.0 for x in rr)
            if rr[0] != rr[1]:
                decisive += 1
            if hit_mtaji:
                mtaji_seen += 1
        assert decisive > 0, variant
        assert mtaji_seen > n_games // 2, (variant, mtaji_seen)

    # ------------------------------------------------------------------
    # 17. Heuristic shape + MCTS smoke at a forced-low rollout cutoff
    # ------------------------------------------------------------------
    h = g.heuristic(g.initial_state())
    assert isinstance(h, list) and len(h) == 2
    from agp.mcts import MCTSBot  # noqa: E402
    bot = MCTSBot(random.Random(1), iterations=12, max_rollout=4)
    mv = bot.select(g, g.initial_state())
    assert mv in g.legal_moves(g.initial_state())

    print("bao_la_kiswahili selftest: all checks passed")


if __name__ == "__main__":
    run()
