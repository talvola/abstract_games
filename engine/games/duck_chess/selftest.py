#!/usr/bin/env python3
"""Standalone correctness anchor for Duck Chess.

Run from the engine dir with::

    PYTHONPATH=. python3 games/duck_chess/selftest.py

Pure stdlib + this game only. Prints ``SELFTEST OK`` and exits 0 on success.
(The gold anchor is the separate one-time Fairy-Stockfish differential in
``_diff_pyffish.py``: perft(1)=640 / perft(2)=379,440 from the start plus
full legal-turn-set and FEN agreement along random games.)

Asserts:
  * setup (standard array, duck off-board) and the two-sub-move turn cycle;
  * first duck placement = 32 squares after 1.e4; the duck must MOVE (its own
    square is never a legal duck target);
  * the duck blocks sliders and pawns, can't be captured, doesn't stop a
    knight's leap (only its landing), and kills a duck-occupied e.p. capture;
  * no check: a king may move onto an attacked square;
  * win by king capture via apply_move (winner set, no duck move follows);
  * fowling: the player with NO chess move wins;
  * castling: legal through an attacked square, blocked by the duck on f1/g1;
  * promotion choices, blocked by a duck on the promotion square;
  * threefold repetition (including duck square) is a draw;
  * serialize round-trips; random games terminate with well-formed returns.
"""

import random
import sys

from agp.chesslike import WHITE, BLACK
from games.duck_chess.game import DuckChess, DState

G = DuckChess()


def fail(msg):
    print("SELFTEST FAILED:", msg)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def mk(board, to_move=WHITE, duck=None, need_duck=False, castling=frozenset(),
       ep=None):
    st = DState(board=dict(board), to_move=to_move, castling=castling, ep=ep,
                duck=duck, need_duck=need_duck, winner=None)
    st.reps = {G._poskey_state(st): 1}
    return st


# --------------------------------------------------------------------------- #
# 1. Setup + turn cycle + first duck placement
# --------------------------------------------------------------------------- #
s0 = G.initial_state()
check(len(s0.board) == 32 and s0.duck is None and not s0.need_duck,
      "standard 32-man setup, duck off-board")
check(s0.board[(4, 0)] == (WHITE, "K") and s0.board[(4, 7)] == (BLACK, "K"),
      "kings on e1/e8")
check(s0.castling == frozenset("KQkq"), "all castling rights")
lm = G.legal_moves(s0)
check(len(lm) == 20, f"20 opening chess moves (got {len(lm)})")

s1 = G.apply_move(s0, "4,1>4,3")                     # 1. e4
check(s1.to_move == WHITE and s1.need_duck, "same player owes the duck move")
dm = G.legal_moves(s1)
check(len(dm) == 32, f"first duck placement: 32 empty squares (got {len(dm)})")
check(all(">" not in m for m in dm), "duck moves are single-cell strings")

s2 = G.apply_move(s1, "4,2")                         # duck -> e3
check(s2.duck == (4, 2) and s2.to_move == BLACK and not s2.need_duck,
      "duck placed, turn passes to Black")

# the duck must MOVE: its current square is never a duck target
s3 = G.apply_move(s2, "4,6>4,4")                     # 1... e5
dm2 = G.legal_moves(s3)
check("4,2" not in dm2, "duck may not stay on its square")
check(len(dm2) == 31, f"32 empties minus the duck's own square (got {len(dm2)})")

# --------------------------------------------------------------------------- #
# 2. The duck blocks: sliders, pawns, knights (landing only), no capture
# --------------------------------------------------------------------------- #
base = {(0, 0): (WHITE, "R"), (7, 0): (WHITE, "K"), (7, 7): (BLACK, "K")}
st = mk(base, duck=(0, 3))                           # duck on a4, rook a1
rook_ups = [m for m in G.legal_moves(st) if m.startswith("0,0>0,")]
check(sorted(rook_ups) == ["0,0>0,1", "0,0>0,2"],
      f"duck stops the rook at a3 and can't be captured (got {rook_ups})")

st = mk({(4, 1): (WHITE, "P"), (7, 0): (WHITE, "K"), (7, 7): (BLACK, "K")},
        duck=(4, 2))                                 # duck right in front of Pe2
pawn = [m for m in G.legal_moves(st) if m.startswith("4,1>")]
check(pawn == [], f"duck blocks the pawn entirely (got {pawn})")
st = mk({(4, 1): (WHITE, "P"), (7, 0): (WHITE, "K"), (7, 7): (BLACK, "K")},
        duck=(4, 3))                                 # duck on e4
pawn = [m for m in G.legal_moves(st) if m.startswith("4,1>")]
check(pawn == ["4,1>4,2"], f"duck blocks only the double step (got {pawn})")

st = mk({(6, 0): (WHITE, "N"), (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K")},
        duck=(5, 2))                                 # Ng1, duck f3
kn = [m for m in G.legal_moves(st) if m.startswith("6,0>")]
check("6,0>5,2" not in kn, "knight may not land on the duck")
check("6,0>7,2" in kn and "6,0>4,1" in kn,
      "the duck does not stop the knight's other leaps")

# --------------------------------------------------------------------------- #
# 3. En passant killed by a duck on the e.p. square
# --------------------------------------------------------------------------- #
epb = {(0, 1): (WHITE, "P"), (1, 3): (BLACK, "P"),
       (7, 0): (WHITE, "K"), (7, 7): (BLACK, "K")}
st = mk(epb, duck=(7, 4))
st = G.apply_move(st, "0,1>0,3")                     # a2-a4 (double)
check(st.ep is not None and st.ep[0] == (0, 2), "e.p. target a3 recorded")
sA = G.apply_move(st, "0,2")                         # duck onto a3 (the e.p. square)
check("1,3>0,2" not in G.legal_moves(sA), "duck on a3 kills b4xa3 e.p.")
sB = G.apply_move(st, "7,3")                         # duck far away instead
check("1,3>0,2" in G.legal_moves(sB), "e.p. b4xa3 legal with the duck away")
sC = G.apply_move(sB, "1,3>0,2")                     # play the e.p. capture
check((0, 3) not in sC.board and sC.board[(0, 2)] == (BLACK, "P"),
      "e.p. removes the a4 pawn")

# --------------------------------------------------------------------------- #
# 4. No check: the king may walk into attack; win = king capture
# --------------------------------------------------------------------------- #
st = mk({(4, 0): (WHITE, "K"), (4, 7): (BLACK, "R"), (0, 7): (BLACK, "K")},
        duck=(7, 3))
check("4,0>4,1" in G.legal_moves(st), "king may stay/move on an attacked file")

st = mk({(1, 6): (WHITE, "Q"), (0, 7): (BLACK, "K"),
         (7, 0): (WHITE, "K")}, duck=(2, 0))
check("1,6>0,7" in G.legal_moves(st), "capturing the king is a legal move")
won = G.apply_move(st, "1,6>0,7")                    # Qxa8 takes the king
check(won.winner == WHITE and not won.need_duck,
      "king capture ends the game at once (no duck move)")
check(G.is_terminal(won) and G.returns(won) == [1.0, -1.0],
      "White wins by king capture")
check(G.legal_moves(won) == [], "no moves after the game ends")

st = mk({(1, 1): (BLACK, "Q"), (0, 0): (WHITE, "K"), (7, 7): (BLACK, "K")},
        to_move=BLACK, duck=(2, 7))
won = G.apply_move(st, "1,1>0,0")
check(won.winner == BLACK and G.returns(won) == [-1.0, 1.0],
      "Black wins by king capture")

# --------------------------------------------------------------------------- #
# 5. Fowling: no chess move at all -> the stuck player WINS
# --------------------------------------------------------------------------- #
# White: Kh1 boxed by own pawns g1/g2/g3 and the duck on h2; Pg3 is blocked
# by a black rook on g4 (straight ahead, so not capturable by a pawn); no
# white piece has any move. White to move -> fowled -> White wins.
fowl = {(7, 0): (WHITE, "K"), (6, 0): (WHITE, "P"), (6, 1): (WHITE, "P"),
        (6, 2): (WHITE, "P"), (6, 3): (BLACK, "R"), (4, 7): (BLACK, "K")}
st = mk(fowl, duck=(7, 1))
check(G.legal_moves(st) == [], "fowled position: no chess moves")
check(G.is_terminal(st), "fowled position is terminal")
check(G.returns(st) == [1.0, -1.0], "the fowled (stalemated) player WINS")
# sanity: with the duck elsewhere the same position is NOT fowled (Kxh2 free)
st = mk(fowl, duck=(0, 3))
check("7,0>7,1" in G.legal_moves(st), "un-fowled once h2 is free")

# --------------------------------------------------------------------------- #
# 6. Castling: through attack OK; duck on f1/g1 blocks
# --------------------------------------------------------------------------- #
cas = {(4, 0): (WHITE, "K"), (7, 0): (WHITE, "R"),
       (5, 6): (BLACK, "R"), (0, 7): (BLACK, "K")}   # Rf7 attacks f1
st = mk(cas, duck=(0, 3), castling=frozenset("K"))
check("4,0>6,0" in G.legal_moves(st), "may castle THROUGH an attacked square")
st = mk(cas, duck=(5, 0), castling=frozenset("K"))   # duck f1
check("4,0>6,0" not in G.legal_moves(st), "duck on f1 blocks O-O")
st = mk(cas, duck=(6, 0), castling=frozenset("K"))   # duck g1
check("4,0>6,0" not in G.legal_moves(st), "duck on g1 blocks O-O")
# executing the castle moves the rook and keeps the turn for the duck
st = mk(cas, duck=(0, 3), castling=frozenset("K"))
oo = G.apply_move(st, "4,0>6,0")
check(oo.board[(6, 0)] == (WHITE, "K") and oo.board[(5, 0)] == (WHITE, "R"),
      "O-O places Kg1/Rf1")
check(oo.need_duck and oo.to_move == WHITE, "duck move still owed after O-O")

# --------------------------------------------------------------------------- #
# 7. Promotion + duck on the promotion square
# --------------------------------------------------------------------------- #
pro = {(0, 6): (WHITE, "P"), (7, 0): (WHITE, "K"), (7, 7): (BLACK, "K")}
st = mk(pro, duck=(4, 3))
ups = sorted(m for m in G.legal_moves(st) if m.startswith("0,6>0,7"))
check(ups == ["0,6>0,7=B", "0,6>0,7=N", "0,6>0,7=Q", "0,6>0,7=R"],
      f"four promotion choices (got {ups})")
st = mk(pro, duck=(0, 7))                            # duck sits on a8
check(all(not m.startswith("0,6>") for m in G.legal_moves(st)),
      "duck on a8 blocks the promotion push")
st = mk(pro, duck=(4, 3))
q = G.apply_move(st, "0,6>0,7=Q")
check(q.board[(0, 7)] == (WHITE, "Q") and q.need_duck, "promotion applied")

# --------------------------------------------------------------------------- #
# 8. Threefold repetition (duck square included) is a draw
# --------------------------------------------------------------------------- #
st = G.initial_state()
cycle = [("6,0>5,2", "0,2"), ("6,7>5,5", "0,5"),     # Nf3/duck a3, Nf6/duck a6
         ("5,2>6,0", "0,2"), ("5,5>6,7", "0,5")]     # Ng1/duck a3, Ng8/duck a6
done = False
for _ in range(3):
    for cm, dm in cycle:
        st = G.apply_move(st, cm)
        if G.is_terminal(st):
            done = True
            break
        st = G.apply_move(st, dm)
        if G.is_terminal(st):
            done = True
            break
    if done:
        break
check(done and G.returns(st) == [0.0, 0.0] and st.winner is None,
      "threefold repetition -> honest draw")

# --------------------------------------------------------------------------- #
# 9. Serialize round-trip (duck / need_duck / winner)
# --------------------------------------------------------------------------- #
import json                                           # noqa: E402
s = G.apply_move(G.initial_state(), "4,1>4,3")
for stx in (s, G.apply_move(s, "3,4")):
    d = json.loads(json.dumps(G.serialize(stx)))
    back = G.deserialize(d)
    check(back.board == stx.board and back.duck == stx.duck
          and back.need_duck == stx.need_duck and back.winner == stx.winner
          and back.ep == stx.ep and back.castling == stx.castling,
          "serialize round-trip")

# --------------------------------------------------------------------------- #
# 10. Random playouts terminate with well-formed returns
# --------------------------------------------------------------------------- #
rng = random.Random(7)
results = {"king": 0, "draw": 0, "fowl": 0}
for _ in range(30):
    st = G.initial_state()
    plies = 0
    while not G.is_terminal(st):
        ms = G.legal_moves(st)
        check(ms, "non-terminal position must have moves")
        st = G.apply_move(st, rng.choice(ms))
        plies += 1
        check(plies <= G.PLY_CAP + 2, "playout exceeded the ply cap")
    ret = G.returns(st)
    check(ret in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]), f"bad returns {ret}")
    if st.winner is not None:
        results["king"] += 1
    elif ret == [0.0, 0.0]:
        results["draw"] += 1
    else:
        results["fowl"] += 1

print(f"playouts: {results}")
print("SELFTEST OK")
