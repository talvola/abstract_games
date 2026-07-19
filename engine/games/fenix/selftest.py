#!/usr/bin/env python3
"""Fenix correctness anchors (pure stdlib).

Run from engine/ with:  PYTHONPATH=. python3 games/fenix/selftest.py

Anchors:
  1. Figure 1 (Abstract Games #20 p.21) starting position: solid 28-disc corner
     triangles (Red c+r<=6, Black c+r>=10).
  2. Setup-phase turn structure: adjacency requirement (original), General/King
     creation counts, forced King promotion on the fifth turn, and the
     published (HUCH!) variant's anywhere-stacking.
  3. Figure 3 (AG#20 p.21), the magazine's fully worked forced-maximum-capture
     example: the legal move set is EXACTLY the five maximum-VALUE sequences
     (Soldier a-b, General h-then-beyond-the-King x3 landings, King f-k), with
     the three-Soldier chain e,f,g (3 jumps but value 3) excluded.
  4. A cyclic chain: each enemy piece jumped at most once (re-reaching it
     blocks), the vacated origin square is landable, and jumped pieces are
     removed only at the END of the turn.
  5. Reconstitution: King rebuild is compulsory and overrides compulsory
     capture; General rebuild is optional, coexists with captures, and is a
     one-shot next-turn right; King capture with no rebuild available = loss.
  6. Repetition (original rules): third occurrence of a position loses for the
     repeater; the published variant has no such rule.
  7. No-progress draw cap (termination guarantee).

Prints "SELFTEST OK" and exits 0 on success.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.fenix.game import Fenix, FState, QUIET_CAP  # noqa: E402

G = Fenix()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def battle_state(pieces, to_move, variant="original", mrk=None, mrg=None):
    """A mid-battle state (setup finished). pieces: {(c,r): (owner, height)}."""
    return FState(board=dict(pieces), to_move=to_move, setup=[5, 5],
                  mrk=list(mrk or [False, False]), mrg=list(mrg or [False, False]),
                  variant=variant)


def test_setup_figure1():
    s = G.initial_state()
    red = {q for q, (o, h) in s.board.items() if o == 0}
    black = {q for q, (o, h) in s.board.items() if o == 1}
    assert red == {(c, r) for c in range(9) for r in range(9) if c + r <= 6}
    assert black == {(c, r) for c in range(9) for r in range(9) if c + r >= 10}
    assert len(red) == len(black) == 28
    assert all(h == 1 for (o, h) in s.board.values())
    assert G.current_player(s) == 0  # Red starts


def test_setup_phase():
    s = G.initial_state()
    lm = set(G.legal_moves(s))
    assert "0,0>0,1" in lm, "adjacent stack must be legal"
    assert "0,0>6,0" not in lm, "original rules: non-adjacent stack illegal"
    assert all(len(m.split(">")) == 2 for m in lm)
    # Red General, Black General, then Red promotes it to the King.
    s = G.apply_move(s, "0,0>0,1")
    assert s.board[(0, 1)] == (0, 2) and (0, 0) not in s.board
    s = G.apply_move(s, "8,8>8,7")
    lm = set(G.legal_moves(s))
    assert "1,1>0,1" in lm, "Soldier onto adjacent own General -> King"
    s = G.apply_move(s, "1,1>0,1")
    assert s.board[(0, 1)] == (0, 3)
    # No second King: red 2-stacks would be needed; assert later via forced path.
    s = G.apply_move(s, "7,8>7,7")
    # Finish red: three more Generals (creations 2..4); black keeps making
    # Generals so its fifth turn will be a FORCED King promotion.
    for mv, reply in (("3,0>2,0", "8,5>8,6"), ("5,0>4,0", "6,8>6,7")):
        s = G.apply_move(s, mv)
        s = G.apply_move(s, reply)
    s = G.apply_move(s, "0,3>0,2")  # red's fifth setup turn
    # Red setup complete: 19 Soldiers, 3 Generals, 1 King.
    red = [(o, h) for (o, h) in s.board.values() if o == 0]
    assert sorted(red) == [(0, 1)] * 19 + [(0, 2)] * 3 + [(0, 3)]
    assert s.setup[0] == 5
    # Black has made 4 stacking moves, all Generals -> 5th MUST promote.
    black2 = [q for q, (o, h) in s.board.items() if o == 1 and h == 2]
    assert len(black2) == 4 and s.setup[1] == 4
    lm = set(G.legal_moves(s))
    assert lm and all(G.deserialize(G.serialize(s)).board[c] ==
                      s.board[c] for c in s.board)  # round-trip spot check
    for m in lm:
        dst = tuple(int(x) for x in m.split(">")[1].split(","))
        assert s.board[dst] == (1, 2), f"5th turn must promote a General: {m}"
    king_mv = sorted(lm)[0]
    s = G.apply_move(s, king_mv)
    blk = [(o, h) for (o, h) in s.board.values() if o == 1]
    assert sorted(blk) == [(1, 1)] * 19 + [(1, 2)] * 3 + [(1, 3)]
    # Battle phase begins: red's moves never land on an own piece.
    for m in G.legal_moves(s):
        dst = tuple(int(x) for x in m.split(">")[-1].split(","))
        assert dst not in s.board, m
    # Published variant: anywhere-stacking.
    sp = G.initial_state(options={"rules": "published"})
    assert "0,0>6,0" in set(G.legal_moves(sp)), "published: non-adjacent stack legal"


def test_figure3():
    # AG#20 Figure 3, Black to move. Coordinates: c=0..8 left-right, r=0..8
    # bottom-up (the magazine draws the board rotated 45 degrees).
    pieces = {
        (6, 7): (0, 1), (3, 5): (0, 1), (1, 4): (0, 1), (5, 4): (0, 1),
        (6, 4): (0, 1), (6, 2): (0, 1),          # red Soldiers
        (4, 3): (0, 3),                          # red King
        (8, 7): (1, 2),                          # black General
        (3, 3): (1, 1),                          # black Soldier
        (5, 2): (1, 3),                          # black King
    }
    s = battle_state(pieces, to_move=1)
    expect = {
        "3,3>5,3>5,5",          # S jumps King then Soldier (a, b) — value 4
        "8,7>4,7>4,2",          # G jumps S landing at h, then the King...
        "8,7>4,7>4,1",          # ...landing anywhere beyond (i, say)
        "8,7>4,7>4,0",
        "5,2>3,4>3,6",          # K jumps King diagonally (f) then Soldier (k)
    }
    got = set(G.legal_moves(s))
    assert got == expect, f"Figure 3 legal set mismatch:\n got {sorted(got)}"
    # The G's 3-Soldier chain e,f,g (3 jumps, value 3) must have been generated
    # but pruned by the maximum-VALUE rule ("four pieces rather than three,
    # even though there are fewer jumps").
    assert "8,7>3,7>3,4>0,4" not in got
    # Every max sequence fells the red King: red has no General left, so the
    # King cannot be rebuilt -> Black wins immediately.
    s2 = G.apply_move(s, "8,7>4,7>4,2")
    assert (6, 7) not in s2.board and (4, 3) not in s2.board  # jumped removed
    assert s2.mrk[0], "red owes a King rebuild"
    assert G.legal_moves(s2) == [] and G.is_terminal(s2)
    assert G.returns(s2) == [-1.0, 1.0], "unrebuildable King = Black wins"
    # describe_move sanity
    assert G.describe_move(s, "8,7>4,7>4,2") == "G 8,7x4,7x4,2 (+4)"


def test_cycle_chain():
    # Black Soldier ringed by four red Soldiers: the chain loops the block,
    # lands on its own vacated origin, and stops when it re-reaches the first
    # jumped piece. Jumped pieces stay on the board until the END of the turn.
    pieces = {
        (3, 3): (1, 1),
        (3, 4): (0, 1), (4, 5): (0, 1), (5, 4): (0, 1), (4, 3): (0, 1),
    }
    s = battle_state(pieces, to_move=1)
    got = set(G.legal_moves(s))
    assert got == {"3,3>3,5>5,5>5,3>3,3", "3,3>5,3>5,5>3,5>3,3"}, got
    s2 = G.apply_move(s, "3,3>3,5>5,5>5,3>3,3")
    assert s2.board == {(3, 3): (1, 1)}, "all four removed at end of turn"


def test_reconstitution_general():
    # Black's only capture fells red's only General; red MAY rebuild next turn.
    pieces = {
        (5, 4): (0, 2),                              # red General (victim)
        (0, 0): (0, 1), (0, 1): (0, 1), (4, 4): (0, 1),  # red Soldiers
        (0, 8): (0, 3),                              # red King
        (5, 5): (1, 1), (8, 0): (1, 3),              # black S + King
    }
    s = battle_state(pieces, to_move=1)
    assert G.legal_moves(s) == ["5,5>5,3"]
    s2 = G.apply_move(s, "5,5>5,3")
    assert s2.mrg[0] and not s2.mrk[0]
    lm = set(G.legal_moves(s2))
    assert {"0,0>0,1", "0,1>0,0"} <= lm, "General rebuild offered"
    assert "4,4>4,5" in lm, "...alongside ordinary moves (rebuild is optional)"
    s3 = G.apply_move(s2, "0,0>0,1")
    assert s3.board[(0, 1)] == (0, 2) and (0, 0) not in s3.board
    # One-shot: decline the rebuild and the right is gone.
    s3b = G.apply_move(s2, "4,4>4,5")
    assert not s3b.mrg[0]
    s4 = G.apply_move(s3b, "5,3>5,2")     # black quiet reply
    assert "0,0>0,1" not in set(G.legal_moves(s4)), "declined rebuild expired"


def test_reconstitution_king():
    # Black fells the red King (value 3 beats black's other value-1 capture);
    # red MUST rebuild — even though red has a capture available.
    pieces = {
        (4, 4): (0, 3),                  # red King (victim)
        (0, 0): (0, 2), (0, 1): (0, 1),  # red General + adjacent Soldier
        (7, 7): (0, 1),                  # red Soldier with a capture next turn
        (4, 5): (1, 1), (7, 6): (1, 1), (8, 8): (1, 3),
    }
    s = battle_state(pieces, to_move=1)
    assert G.legal_moves(s) == ["4,5>4,3"], "max-value rule picks the King strike"
    s2 = G.apply_move(s, "4,5>4,3")
    assert s2.mrk[0] and not s2.mrg[0]
    assert G.legal_moves(s2) == ["0,1>0,0"], \
        "King rebuild is the ONLY move (overrides compulsory capture)"
    s3 = G.apply_move(s2, "0,1>0,0")
    assert s3.board[(0, 0)] == (0, 3) and not s3.mrk[0] and not s3.mrg[0]
    assert not G.is_terminal(s3)
    # Same strike with no red General anywhere: red cannot rebuild -> loses.
    pieces2 = {(4, 4): (0, 3), (0, 1): (0, 1), (4, 5): (1, 1), (8, 8): (1, 3)}
    t = G.apply_move(battle_state(pieces2, to_move=1), "4,5>4,3")
    assert G.is_terminal(t) and G.returns(t) == [-1.0, 1.0]


def test_repetition():
    kings = {(0, 0): (0, 3), (8, 8): (1, 3)}
    s = battle_state(kings, to_move=0, variant="original")
    seq = ["0,0>0,1", "8,8>8,7", "0,1>0,0", "8,7>8,8"] * 2 + ["0,0>0,1"]
    for i, m in enumerate(seq):
        assert not G.is_terminal(s), f"terminal too early at move {i}"
        s = G.apply_move(s, m)
    assert s.winner == 1, "third repetition: the repeater (Red) loses"
    assert G.is_terminal(s) and G.returns(s) == [-1.0, 1.0]
    # Published rules: no repetition loss.
    sp = battle_state(kings, to_move=0, variant="published")
    for m in seq:
        sp = G.apply_move(sp, m)
    assert sp.winner is None and not G.is_terminal(sp)


def test_draw_cap():
    kings = {(0, 0): (0, 3), (8, 8): (1, 3)}
    s = battle_state(kings, to_move=0, variant="published")
    s.quiet = QUIET_CAP - 1
    s = G.apply_move(s, "0,0>0,1")
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0], "no-progress draw"


def main():
    test_setup_figure1()
    test_setup_phase()
    test_figure3()
    test_cycle_chain()
    test_reconstitution_general()
    test_reconstitution_king()
    test_repetition()
    test_draw_cap()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
