"""Standalone correctness anchor for Permute (Eric Silverman, 2020).

Run from the engine dir:  PYTHONPATH=. python3 games/permute/selftest.py

Pure stdlib + agp + this game. Anchors (vs the designer's rules /
mindsports.nl canonical text):

  (a) initial board = full two-colour chequerboard (second player holds the
      corner parity, so 41 vs 40 stones on 9x9);
  (b) twist legality — monochrome faces, bandaged faces and (equivalently)
      no-own-stone faces are illegal; the pie-rule "swap" appears only on the
      second player's first turn;
  (c) rotation math — CW then CCW on the same face restores the stones, and a
      concrete CW twist matches the hand-computed permutation;
  (d) bandaging is mandatory (encoded in every move), own-stone-only, lands
      inside the twisted face, and grows the bandaged set by exactly one;
  (e) Catchup-style cascade scoring on hand-built end positions, including a
      top-group tie broken lower down and an even-board dead-tie draw;
  (f) a full random playout terminates with a well-formed result within the
      provable n^2(+1) ply bound.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import random
import sys

from games.permute.game import (
    Permute, PermuteState, ORANGE, YELLOW, CW, CCW,
    _face, _dest, _rotate, _face_twistable, _group_sizes, _compare,
)


def check(cond, msg):
    if not cond:
        print(f"SELFTEST FAIL: {msg}")
        sys.exit(1)


def state_from_rows(rows, bandaged=(), to_move=ORANGE, ply=10):
    """Build a state from rows of '0'/'1' chars, row 0 first (y=0)."""
    n = len(rows)
    board = tuple(int(ch) for row in rows for ch in row)
    return PermuteState(size=n, board=board, bandaged=frozenset(bandaged),
                        to_move=to_move, ply=ply)


def main():
    g = Permute()

    # (a) initial position -------------------------------------------------
    s = g.initial_state()
    check(s.size == 9 and len(s.board) == 81, "default board is 9x9")
    for y in range(9):
        for x in range(9):
            want = YELLOW if (x + y) % 2 == 0 else ORANGE
            check(s.board[y * 9 + x] == want, f"chequerboard at {x},{y}")
    check(s.board.count(YELLOW) == 41 and s.board.count(ORANGE) == 40,
          "second player (Yellow) holds the 41st stone on 9x9")
    check(not s.bandaged and s.to_move == ORANGE and s.ply == 0,
          "clean initial state, Orange to move")
    s13 = g.initial_state(options={"size": 13})
    check(s13.size == 13 and len(s13.board) == 169, "13x13 option")

    # (b) twist legality ---------------------------------------------------
    # Fresh chequerboard: every one of the 8x8 faces is twistable, each holds
    # exactly 2 mover stones, 2 directions => 256 moves; no swap on ply 0.
    m0 = g.legal_moves(s)
    check(len(m0) == 256 and "swap" not in m0, f"opening move count 256, got {len(m0)}")
    for m in m0:
        path, d = m.split("=")
        anchor, stone = path.split(">")
        ax, ay = map(int, anchor.split(","))
        sx, sy = map(int, stone.split(","))
        check(d in (CW, CCW), f"direction suffix in {m}")
        check((sx, sy) in _face(ax, ay), f"bandage target inside face in {m}")
        check(s.board[sy * 9 + sx] == ORANGE, f"bandage target is mover's own stone in {m}")

    # Swap offered exactly on the second player's first turn (ply 1).
    s1 = g.apply_move(s, m0[0])
    m1 = g.legal_moves(s1)
    check("swap" in m1 and s1.ply == 1, "swap offered on ply 1")
    s2 = g.apply_move(s1, "swap")
    check(s2.to_move == ORANGE and s2.ply == 2, "after swap the first seat moves again")
    check(all(a == 1 - b for a, b in zip(s2.board, s1.board)), "swap flips every stone")
    check(s2.bandaged == s1.bandaged, "swap keeps bandages in place")
    bidx = next(iter(s2.bandaged))
    check(s2.board[bidx] == YELLOW, "the opening bandaged stone now belongs to seat 1")
    check("swap" not in g.legal_moves(s2), "swap not offered later")

    # Monochrome face: board of two solid halves -> faces inside a half are
    # illegal; only the 8 faces straddling the colour boundary are twistable.
    rows = ["000000000"] * 4 + ["111111111"] * 5
    sm = state_from_rows(rows)
    faces = {(ax, ay) for ay in range(8) for ax in range(8)
             if _face_twistable(sm.board, sm.bandaged, 9, ax, ay)}
    check(faces == {(ax, 3) for ax in range(8)}, "monochrome faces are untwistable")
    for m in g.legal_moves(sm):
        check(m.split(">")[0].split(",")[1] == "3", "moves only on the boundary row")

    # Bandaged face: bandage one cell of the chequerboard -> the up-to-4 faces
    # containing it disappear from the move list.
    sb = PermuteState(size=9, board=s.board, bandaged=frozenset({4 * 9 + 4}),
                      to_move=ORANGE, ply=10)
    banned = {(3, 3), (4, 3), (3, 4), (4, 4)}
    for m in g.legal_moves(sb):
        ax, ay = map(int, m.split(">")[0].split(","))
        check((ax, ay) not in banned, f"face {ax},{ay} contains a bandaged stone")

    # No-own-stone faces: with YELLOW to move on the two-halves board, every
    # twistable (boundary) face still contains a Yellow stone => moves exist,
    # and every all-Orange face was already excluded as monochrome.
    smy = state_from_rows(rows, to_move=YELLOW)
    check(len(g.legal_moves(smy)) > 0, "twistable faces always hold both colours")

    # (c) rotation math ----------------------------------------------------
    b0 = s.board
    b1 = _rotate(b0, 9, 3, 4, CW)
    check(_rotate(b1, 9, 3, 4, CCW) == b0, "CW then CCW restores the face")
    check(_rotate(_rotate(_rotate(_rotate(b0, 9, 2, 2, CW), 9, 2, 2, CW),
                          9, 2, 2, CW), 9, 2, 2, CW) == b0, "4 CW twists = identity")
    # Concrete CW check on face (0,0) of the chequerboard: BL(0,0)=Y goes to
    # TL(0,1); TL(0,1)=O to TR(1,1); TR(1,1)=Y to BR(1,0); BR(1,0)=O to BL.
    b2 = _rotate(b0, 9, 0, 0, CW)
    check((b2[0 * 9 + 0], b2[0 * 9 + 1], b2[1 * 9 + 0], b2[1 * 9 + 1])
          == (ORANGE, YELLOW, YELLOW, ORANGE), "hand-computed CW permutation")
    check(_dest(0, 0, 0, 0, CW) == (0, 1) and _dest(0, 0, 0, 0, CCW) == (1, 0),
          "stone destination map")

    # (d) bandaging --------------------------------------------------------
    mv = "3,4>3,4=CW"  # (3,4) is Orange on the chequerboard ((3+4) odd)
    check(mv in m0, "sample move is legal")
    sn = g.apply_move(s, mv)
    check(len(sn.bandaged) == 1, "exactly one stone bandaged per move")
    dx, dy = _dest(3, 4, 3, 4, CW)
    check(sn.bandaged == frozenset({dy * 9 + dx}), "bandage lands on the stone's destination")
    check(sn.board[dy * 9 + dx] == ORANGE, "bandaged stone is the mover's")
    # Bandaging an opponent stone must be rejected: (3,5) is Yellow.
    try:
        g.apply_move(s, "3,4>3,5=CW")
        check(False, "bandaging an opponent stone must raise")
    except ValueError:
        pass
    try:
        g.apply_move(s, "3,4>6,6=CW")
        check(False, "bandaging outside the face must raise")
    except ValueError:
        pass

    # (e) cascade scoring --------------------------------------------------
    # Alternating full rows: Orange rows 0,2,4,6,8 -> groups [9]*5; Yellow
    # rows 1,3,5,7 -> [9]*4. Tied 9,9,9,9 then 9 vs nothing => Orange wins.
    rows = ["000000000" if y % 2 == 0 else "111111111" for y in range(9)]
    se = state_from_rows(rows, bandaged=range(81))
    check(g.is_terminal(se), "fully bandaged board is terminal")
    check(_group_sizes(se.board, 9, ORANGE) == [9] * 5, "orange stripes")
    check(_group_sizes(se.board, 9, YELLOW) == [9] * 4, "yellow stripes")
    check(g.returns(se) == [1.0, -1.0], "tie broken by the extra lower group")

    # Flip one corner: Yellow's (0,0) joins row 1 -> Yellow [10,9,9,9] beats
    # Orange [9,9,9,9,8] on the FIRST rung.
    rows2 = ["100000000"] + rows[1:]
    se2 = state_from_rows(rows2, bandaged=range(81))
    check(_group_sizes(se2.board, 9, YELLOW) == [10, 9, 9, 9], "merged yellow group")
    check(g.returns(se2) == [-1.0, 1.0], "largest group decides first")

    # Top-group tie broken strictly lower: O = [4,3,2], Y = [4,3,1,1] on the
    # cascade -> 4=4, 3=3, 2>1 => Orange. Built on a 3x3... use direct compare.
    check(_compare([4, 3, 2], [4, 3, 1, 1]) == 1, "cascade third-rung break")
    check(_compare([5, 2], [5, 2, 1]) == -1, "extra group beats a missing rung")

    # Even-board dead tie = draw: 4x4 alternating rows -> both [4,4].
    se4 = state_from_rows(["0000", "1111", "0000", "1111"], bandaged=range(16))
    check(g.is_terminal(se4) and g.returns(se4) == [0.0, 0.0], "even-board dead tie is a draw")

    # (f) random playout terminates with a result --------------------------
    rng = random.Random(7)
    st = g.initial_state()
    plies = 0
    while not g.is_terminal(st):
        moves = g.legal_moves(st)
        check(moves, "non-terminal state has moves")
        st = g.apply_move(st, rng.choice(moves))
        plies += 1
        check(plies <= 82, "ply bound n^2 + 1 (every twist bandages a stone)")
    ret = g.returns(st)
    check(len(ret) == 2 and sorted(ret) == [-1.0, 1.0],
          "odd board playout ends decisively")
    # Serialize round-trip on a mid/terminal state.
    check(g.serialize(g.deserialize(g.serialize(st))) == g.serialize(st),
          "serialize round-trips")

    print(f"SELFTEST OK (random playout: {plies} plies, result {ret})")


if __name__ == "__main__":
    main()
