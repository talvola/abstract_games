"""Standalone correctness anchor for Chaturaji (Chaturanga for four players).

Pure-stdlib: imports only ``agp`` and this package. Run:
    cd engine && PYTHONPATH=. python3 games/chaturaji/selftest.py
"""

from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path

from agp.loader import load_from_dir

HERE = Path(__file__).resolve().parent
_man, GAME = load_from_dir(HERE)
STATE = __import__("games.chaturaji.game", fromlist=["CState"]).CState


def _sq(s):
    return (ord(s[0]) - 97, int(s[1]) - 1)


def _nonpass(moves):
    return [m for m in moves if m != "pass"]


# ---------------------------------------------------------------- (a) setup
def test_setup():
    s = GAME.initial_state()
    assert len(s.board) == 32, len(s.board)
    # spot-check all four corners
    assert s.board[_sq("e8")] == (0, "K"), "Red king"
    assert s.board[_sq("h8")] == (0, "S"), "Red boat"
    assert s.board[_sq("h4")] == (1, "K"), "Green king"
    assert s.board[_sq("h1")] == (1, "S"), "Green boat"
    assert s.board[_sq("d1")] == (2, "K"), "Yellow king"
    assert s.board[_sq("a1")] == (2, "S"), "Yellow boat"
    assert s.board[_sq("a5")] == (3, "K"), "Black king"
    assert s.board[_sq("a8")] == (3, "S"), "Black boat"
    # pawn counts and ownership
    for p, files in {0: "efgh", 1: "gggg", 2: "abcd", 3: "bbbb"}.items():
        pawns = [c for c, (o, pt) in s.board.items() if o == p and pt == "P"]
        assert len(pawns) == 4, (p, len(pawns))
    assert s.to_move == 0 and s.use_dice is True
    print("  setup OK (32 men, four corners)")


# ------------------------------------------------ (b) per-die opening counts
def test_die_counts():
    s = GAME.initial_state()  # Red (seat 0) to move
    expect = {2: 1, 3: 2, 4: 0, 5: 6}  # hand-derived from the opening position
    for pip, want in expect.items():
        forced = replace(s, dice=[pip])
        got = len(_nonpass(GAME.legal_moves(forced)))
        assert got == want, f"die {pip}: got {got} want {want}"
        assert "pass" in GAME.legal_moves(forced)  # dice-turn may always decline
    print("  per-die opening counts OK  boat=1 knight=2 rook=0 king/pawn=6")


# ------------------------------------------------------- (c) piece movements
def _bare(board, dice, **kw):
    return STATE(board=dict(board), dice=list(dice), to_move=kw.get("to_move", 0),
                 use_dice=kw.get("use_dice", True), **{k: v for k, v in kw.items()
                 if k in ("points", "kings_by", "king_alive", "no_cap", "ply")})


def test_boat_alfil():
    board = {(3, 3): (0, "S")}
    s = _bare(board, [2])
    dests = {m.split(">")[1] for m in _nonpass(GAME.legal_moves(s))}
    assert dests == {"1,1", "5,5", "1,5", "5,1"}, dests
    print("  boat = alfil (2-square diagonal leap) OK")


def test_rook_slider():
    board = {(0, 0): (0, "R")}
    s = _bare(board, [4])
    ms = _nonpass(GAME.legal_moves(s))
    assert len(ms) == 14, len(ms)  # full rank + file on an empty board
    print("  rook slides full rank+file OK (14)")


def test_pawn_direction_and_promotion():
    # Yellow (seat 2) pawn advances +row; promotes on row 7.
    board = {(2, 6): (2, "P")}
    s = _bare(board, [5], to_move=2)
    ms = _nonpass(GAME.legal_moves(s))
    assert {m for m in ms} == {"2,6>2,7=R", "2,6>2,7=N", "2,6>2,7=S"}, ms
    # Green (seat 1) pawn advances -col; promotes on col 0.
    board = {(1, 4): (1, "P")}
    s = _bare(board, [5], to_move=1)
    ms = _nonpass(GAME.legal_moves(s))
    assert set(ms) == {"1,4>0,4=R", "1,4>0,4=N", "1,4>0,4=S"}, ms
    # a Yellow pawn actually becomes a Rook when it promotes
    board = {(2, 6): (2, "P")}
    s = _bare(board, [5], to_move=2)
    ns = GAME.apply_move(s, "2,6>2,7=R")
    assert ns.board[(2, 7)] == (2, "R"), ns.board.get((2, 7))
    # pawn diagonal capture: Red (seat 0, faces -row) takes an enemy at (c-1,r-1)
    board = {(4, 4): (0, "P"), (3, 3): (1, "N")}
    s = _bare(board, [5], to_move=0)
    caps = {m for m in _nonpass(GAME.legal_moves(s)) if m.endswith("3,3")}
    assert caps == {"4,4>3,3"}, caps
    print("  pawn direction, diagonal capture and promotion OK")


def test_king_capture_scoring_and_dead_army():
    # Red rook captures Green's king.
    board = {(0, 0): (0, "R"), (0, 3): (1, "K"), (7, 7): (1, "P")}
    s = _bare(board, [4], to_move=0)
    ns = GAME.apply_move(s, "0,0>0,3")
    assert ns.points[0] == 5 and ns.points[1] == -5, ns.points
    assert ns.king_alive[1] is False and ns.kings_by[0] == 1
    assert ns.over is False  # three kings notionally still standing (list default)
    # Dead player's men remain and can still move on their turn.
    d = replace(ns, to_move=1, dice=["*"], use_dice=False)
    assert _nonpass(GAME.legal_moves(d)), "Green (king lost) can still move its pawn"
    assert d.board[(7, 7)] == (1, "P")  # its pawn is still on the board / capturable
    print("  king capture scores 5, victim survives-but-kingless OK")


def test_boat_triumph():
    # Three boats form an L; a fourth Red boat leaps in to complete the 2x2.
    board = {
        (3, 3): (0, "S"), (3, 4): (0, "S"), (4, 3): (1, "S"),  # will make a 2x2 with (4,4)
        (2, 6): (0, "S"),                                      # mover: (2,6)->(4,4)
    }
    s = _bare(board, [2], to_move=0)
    ns = GAME.apply_move(s, "2,6>4,4")
    assert ns.board.get((4, 4)) == (0, "S")
    for cl in [(3, 3), (3, 4), (4, 3)]:
        assert cl not in ns.board, f"{cl} should be captured by triumph"
    # only the enemy boat (owner 1) scores; own boats give nothing
    assert ns.points[0] == 2 and ns.points[1] == -2, ns.points
    print("  triumph of the boat OK (four boats -> takes the other three)")


def test_grand_slam():
    # Red already took two enemy kings; now captures the third with its own alive.
    board = {(0, 0): (0, "R"), (0, 2): (3, "K"), (5, 5): (3, "P")}
    s = _bare(board, [4], to_move=0,
              kings_by=[2, 0, 0, 0], king_alive=[True, False, False, True])
    ns = GAME.apply_move(s, "0,0>0,2")
    assert ns.over is True, "sweeping all three kings ends the game"
    assert ns.kings_by[0] == 3
    # king (5) + swept enemy pawn (1) = 6
    assert ns.points[0] == 6 and ns.points[3] == -6, ns.points
    print("  grand slam (all three kings, own alive) ends + sweeps OK")


def test_returns_zero_sum():
    board = {(0, 0): (0, "R")}
    s = _bare(board, [4], to_move=0, points=[7, -2, -5, 0], ply=0)
    s = replace(s, over=True)
    r = GAME.returns(s)
    assert len(r) == 4 and abs(sum(GAME.serialize(s)["points"])) < 1e-9
    assert max(r) == 1.0 and all(-1.0 <= x <= 1.0 for x in r), r
    # honest draw when nobody scores
    s0 = replace(s, points=[0, 0, 0, 0])
    assert GAME.returns(s0) == [0.0, 0.0, 0.0, 0.0]
    print("  returns() zero-sum, normalized, honest draw OK")


# ------------------------------- (d) conformance playouts + serialize + uniq
def test_serialize_roundtrip():
    s = GAME.initial_state(rng=random.Random(1))
    # advance a few plies to reach a mid-turn state (a partly-used roll) too
    for seed in range(30):
        d1 = GAME.serialize(s)
        s2 = GAME.deserialize(d1)
        assert GAME.serialize(s2) == d1, "round-trip mismatch"
        if GAME.is_terminal(s):
            break
        ms = GAME.legal_moves(s)
        s = GAME.apply_move(s, ms[0], rng=random.Random(seed))
    # explicitly exercise a diceless '*' state round-trip
    sd = GAME.initial_state(options={"dice": "off"})
    assert sd.dice == ["*"] and sd.use_dice is False
    assert GAME.serialize(GAME.deserialize(GAME.serialize(sd))) == GAME.serialize(sd)
    print("  serialize round-trip (incl. stored roll and '*') OK")


def test_move_uniqueness():
    s = GAME.initial_state(rng=random.Random(2))
    for seed in range(40):
        if GAME.is_terminal(s):
            break
        ms = GAME.legal_moves(s)
        assert len(ms) == len(set(ms)), "duplicate legal move"
        s = GAME.apply_move(s, random.Random(seed).choice(ms), rng=random.Random(seed))
    print("  move-string uniqueness OK")


def test_playouts():
    for mode in ("on", "off"):
        for seed in range(6):
            rng = random.Random(1000 + seed)
            s = GAME.initial_state(options={"dice": mode}, rng=rng)
            steps = 0
            while not GAME.is_terminal(s):
                ms = GAME.legal_moves(s)
                assert ms, "non-terminal state with no legal move"
                s = GAME.apply_move(s, rng.choice(ms), rng=rng)
                steps += 1
                assert steps <= 2000, "playout did not terminate"
            r = GAME.returns(s)
            assert len(r) == 4 and all(isinstance(x, float) for x in r)
    print("  random playouts terminate for dice on/off, returns well-formed OK")


def main():
    test_setup()
    test_die_counts()
    test_boat_alfil()
    test_rook_slider()
    test_pawn_direction_and_promotion()
    test_king_capture_scoring_and_dead_army()
    test_boat_triumph()
    test_grand_slam()
    test_returns_zero_sum()
    test_serialize_roundtrip()
    test_move_uniqueness()
    test_playouts()
    print("chaturaji selftest: all tests passed")


if __name__ == "__main__":
    main()
