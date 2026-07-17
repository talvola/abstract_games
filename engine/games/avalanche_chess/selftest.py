"""Avalanche Chess selftest — pure stdlib.

Anchors (no engine oracle exists for Avalanche; all numbers were derived
arithmetically and cross-checked by hand, see rules.md):

* perft(1) = 160 = 20 orthodox first moves x 8 available pushes (no first move
  blocks a black pawn's advance square, and no push can self-check at ply 1).
* Node 1.a3/push a6 -> 152 = 19 black regulars x 8 pushes (the pushed a6 pawn
  blocks Nb8-a6; +a6-a5 +Ra8-a7 -a7-a6 -a7-a5 nets 19).
* Node 1.Nf3/push e6 -> 209 = 30 black regulars x 7 pushes (f2 pawn blocked by
  Nf3) minus 1 (the regular Bf8-a3 lands on a3, blocking the a2-a3 push).
* perft(2) = 27488 (frozen regression value, computed by this implementation).

Rule positions: mandatory push, no-push turns, self-check push = instant loss,
push-to-promotion owner choice (+ pusher-checked loss), discovered check via a
push, no en passant, threefold repetition.
"""

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))          # engine/ on the path

from agp.loader import load_from_dir  # noqa: E402

man, g = load_from_dir(HERE)


def perft(state, d):
    if d == 0:
        return 1
    return sum(perft(g.apply_move(state, m), d - 1) for m in g.legal_moves(state))


def path_cells(m):
    return m.split("=")[0].split(">")


def mk(board, to_move, ply=20, balanced=False, pending=None, castling=""):
    """Build a state via the serialization format (kings assumed present)."""
    return g.deserialize({
        "board": board, "to_move": to_move, "castling": castling, "ep": None,
        "halfmove": 0, "ply": ply, "reps": {}, "winner": None,
        "pending": pending, "balanced": balanced,
    })


# ---- opening counts ---------------------------------------------------------
s = g.initial_state()
mv = g.legal_moves(s)
assert len(mv) == 160, len(mv)
assert all(len(path_cells(m)) == 4 for m in mv), "every opening turn must include a push"
assert perft(s, 2) == 27488, "frozen perft(2) regression"

s2 = g.apply_move(s, "0,1>0,2>0,6>0,5")              # 1.a3 / push a6
assert g.current_player(s2) == 1
assert s2.board[(0, 5)] == (1, "P") and (0, 6) not in s2.board
assert len(g.legal_moves(s2)) == 152, len(g.legal_moves(s2))

s3 = g.apply_move(s, "6,0>5,2>4,6>4,5")              # 1.Nf3 / push e6
assert len(g.legal_moves(s3)) == 209, len(g.legal_moves(s3))
# the pushed pawn lost its double-step: e6-e5 exists, e6-e4 does not
b_moves = {tuple(path_cells(m)[:2]) for m in g.legal_moves(s3)}
assert ("4,5", "4,4") in b_moves and ("4,5", "4,3") not in b_moves

assert g.describe_move(s, "0,1>0,2>0,6>0,5") == "Pa2-a3 / push a6"

# ---- balanced variant: no White push on move 1 only -------------------------
sb = g.initial_state(options={"variant": "balanced"})
mb = g.legal_moves(sb)
assert len(mb) == 20 and all(len(path_cells(m)) == 2 for m in mb)
sb2 = g.apply_move(sb, "0,1>0,2")
assert len(g.legal_moves(sb2)) == 160                # Black pushes as normal

# ---- no-push turns (opponent has no advanceable pawn) -----------------------
st = mk({"4,0": [0, "K"], "4,1": [0, "P"], "4,7": [1, "K"]}, to_move=0)
assert all(len(path_cells(m)) == 2 for m in g.legal_moves(st)), "Black pawnless: no push"
st_b = mk({"4,0": [0, "K"], "4,1": [0, "P"], "4,7": [1, "K"]}, to_move=1)
assert all(len(path_cells(m)) == 4 for m in g.legal_moves(st_b)), "Black must push e2"

# ---- self-check push = a legal move that loses instantly --------------------
# Black: Ka8, Rh5; White: Ke1, Pb6. Any Black rook move must push b6-b7, and
# the pawn on b7 then attacks a8: Black self-checks and LOSES. Ka8-b7 instead
# blocks the only push (2-cell move, game goes on).
st = mk({"4,0": [0, "K"], "1,5": [0, "P"], "0,7": [1, "K"], "7,4": [1, "R"]},
        to_move=1)
lm = g.legal_moves(st)
assert "7,4>7,5>1,5>1,6" in lm, "self-check push is LEGAL (it just loses)"
assert "0,7>1,6" in lm, "Kb7 blocks the only push -> no-push turn"
lost = g.apply_move(st, "7,4>7,5>1,5>1,6")
assert lost.winner == 0 and g.is_terminal(lost) and g.returns(lost) == [1.0, -1.0]
cont = g.apply_move(st, "0,7>1,6")
assert cont.winner is None and not g.is_terminal(cont)

# ---- push to promotion: the OWNER chooses; a checking choice wins -----------
# White: Ra5, Kh1; Black: Pe2, Ke8. White pushes e2-e1; Black chooses the piece.
st = mk({"0,4": [0, "R"], "7,0": [0, "K"], "4,1": [1, "P"], "4,7": [1, "K"]},
        to_move=0)
assert all(len(path_cells(m)) == 4 for m in g.legal_moves(st))
pend = g.apply_move(st, "0,4>0,3>4,1>4,0")           # Ra5-a4 / push e1
assert pend.pending == (4, 0) and g.current_player(pend) == 1
assert not g.is_terminal(pend)
assert sorted(g.legal_moves(pend)) == ["=B", "=N", "=Q", "=R"]
assert g.describe_move(pend, "=Q") == "e1=Q"
qs = g.apply_move(pend, "=Q")                        # Qe1+ checks Kh1 -> pusher loses
assert qs.winner == 1 and g.is_terminal(qs) and g.returns(qs) == [-1.0, 1.0]
ns = g.apply_move(pend, "=N")                        # Ne1 gives no check -> play on
assert ns.winner is None and ns.board[(4, 0)] == (1, "N")
assert g.current_player(ns) == 1, "owner continues with their own turn"
assert not g.is_terminal(ns)
# serialize round-trip of the pending state
assert g.serialize(g.deserialize(g.serialize(pend))) == g.serialize(pend)

# ---- a push can deliver (discovered) check to the opponent ------------------
# White: Bb3, Ra1, Ke1; Black: Pd5, Kf7. Pushing d5-d4 opens b3-f7: check.
st = mk({"1,2": [0, "B"], "0,0": [0, "R"], "4,0": [0, "K"],
         "3,4": [1, "P"], "5,6": [1, "K"]}, to_move=0)
chk = g.apply_move(st, "0,0>0,1>3,4>3,3")            # Ra2 / push d4 -> discovered +
assert chk.winner is None
assert g.in_check(chk.board, 1) and not g.in_check(chk.board, 0)
assert not g.is_terminal(chk)
after = g.apply_move(chk, g.legal_moves(chk)[0])     # Black can respond
assert not g.in_check(after.board, 1)

# ---- no en passant ----------------------------------------------------------
st = mk({"4,1": [0, "P"], "4,0": [0, "K"], "3,3": [1, "P"], "7,6": [1, "P"],
         "4,7": [1, "K"]}, to_move=0)
dbl = g.apply_move(st, "4,1>4,3>7,6>7,5")            # e2-e4 / push h6
assert not any(path_cells(m)[:2] == ["3,3", "4,2"] for m in g.legal_moves(dbl)), \
    "no en passant capture exists in Avalanche Chess"

# ---- threefold repetition (pawnless -> plain chess moves) -------------------
st = mk({"4,0": [0, "K"], "0,0": [0, "R"], "4,7": [1, "K"], "0,7": [1, "R"]},
        to_move=0)
seq = ["0,0>1,0", "0,7>1,7", "1,0>0,0", "1,7>0,7"] * 3
for n, m in enumerate(seq):
    if g.is_terminal(st):
        break
    st = g.apply_move(st, m)
assert g.is_terminal(st) and n <= 10, "threefold repetition must end the shuffle"
assert g.returns(st) == [0.0, 0.0], "threefold repetition draw"

# ---- heuristic shape + a full random game terminates ------------------------
assert len(g.heuristic(g.initial_state())) == 2
rng = random.Random(0)
st = g.initial_state()
plies = 0
while not g.is_terminal(st):
    st = g.apply_move(st, rng.choice(g.legal_moves(st)))
    plies += 1
    assert plies <= 700
ret = g.returns(st)
assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

print("avalanche_chess selftest: all tests passed")
