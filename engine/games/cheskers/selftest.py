"""Cheskers selftest — pure stdlib (agp + this game only). Prints SELFTEST OK.

Anchors: verified starting setup, the four distinct movement rules exercised via
apply_move (pawn multi-jump, bishop replacement capture, camel (1,3) leap+capture,
pawn promotion), the pawn/king forced-capture rule, the win conditions (all kings
captured; stalemate), serialize round-trip, and the termination safety.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # engine/ on path

from games.cheskers.game import Cheskers, CheskersState  # noqa: E402

G = Cheskers()


def st(pairs, to_move, **kw):
    """Build a state from {(c,r): (owner, kind)} dict."""
    return CheskersState(board=dict(pairs), to_move=to_move, **kw)


# ---- 1. starting setup matches Golomb exactly --------------------------------
s0 = G.initial_state()
b = s0.board
assert G.current_player(s0) == 0, "Black (player 0) moves first"
# Black
assert b[(3, 7)] == (0, "K") and b[(5, 7)] == (0, "K"), "Black kings d8,f8"
assert b[(7, 7)] == (0, "B"), "Black bishop h8"
assert b[(1, 7)] == (0, "C"), "Black camel b8"
black_pawns = {(0, 6), (1, 5), (2, 6), (3, 5), (4, 6), (5, 5), (6, 6), (7, 5)}
assert {p for p, v in b.items() if v == (0, "p")} == black_pawns
# White
assert b[(2, 0)] == (1, "K") and b[(4, 0)] == (1, "K"), "White kings c1,e1"
assert b[(0, 0)] == (1, "B"), "White bishop a1"
assert b[(6, 0)] == (1, "C"), "White camel g1"
white_pawns = {(0, 2), (1, 1), (2, 2), (3, 1), (4, 2), (5, 1), (6, 2), (7, 1)}
assert {p for p, v in b.items() if v == (1, "p")} == white_pawns
assert len(b) == 24, "12 pieces per side"
# every piece on a dark (col+row even) square
assert all((c + r) % 2 == 0 for (c, r) in b), "all pieces on dark squares"
# opening is legal, non-terminal, no captures forced
assert not G.is_terminal(s0)
lm0 = G.legal_moves(s0)
assert lm0 and all("=" not in m for m in lm0)

# ---- 2. render shape ---------------------------------------------------------
r = G.render(s0)
assert r["board"] == {"type": "square", "width": 8, "height": 8}
assert {"cell": "3,7", "owner": 0, "label": "K"} in r["pieces"]
assert {"cell": "0,6", "owner": 0, "label": ""} in r["pieces"]  # pawn = plain disc

# ---- 3. pawn checkers multi-jump (double jump) via apply_move -----------------
# Black pawn at (3,5) forward = decreasing row. White pawns at (2,4) and (2,2),
# landing squares (1,3) and (1,1) empty => a double jump 3,5>1,3>1,1... arrange:
pos = {(3, 5): (0, "p"), (2, 4): (1, "p"), (0, 2): (1, "p"),
       (3, 7): (0, "K"), (2, 0): (1, "K")}
s = st(pos, 0)
# after first jump lands on (1,3); to chain, need enemy at (0,2)? forward-left
# from (1,3) is (0,2), land (-1,1) off-board; forward-right is (2,2) land (3,1).
pos = {(3, 5): (0, "p"), (2, 4): (1, "p"), (2, 2): (1, "p"),
       (3, 7): (0, "K"), (2, 0): (1, "K")}
s = st(pos, 0)
lm = G.legal_moves(s)
assert "3,5>1,3>3,1" in lm, f"expected black pawn double jump; got {lm}"
# forced: every legal move here is a capture (a pawn jump exists)
assert all(">" in m for m in lm)
s2 = G.apply_move(s, "3,5>1,3>3,1")
assert s2.board[(3, 1)] == (0, "p"), "pawn ended on 3,1"
assert (2, 4) not in s2.board and (2, 2) not in s2.board, "both jumped pawns gone"
assert s2.to_move == 1 and s2.halfmove == 0, "capture resets no-progress"

# ---- 4. forced-capture rule: pawn/king jump forces a capturing move ----------
# White pawn (2,2) can jump black pawn (3,3) to (4,4); a bishop that could quietly
# move must NOT appear as a legal option (capture is obligatory).
pos = {(2, 2): (1, "p"), (3, 3): (0, "p"), (0, 0): (1, "B"),
       (2, 0): (1, "K"), (3, 7): (0, "K")}
s = st(pos, 1)
lm = G.legal_moves(s)
assert lm == ["2,2>4,4"], f"pawn jump must be forced/only move; got {lm}"

# ---- 5. bishop/camel capture is OPTIONAL when no pawn/king can jump -----------
# White bishop a1 can capture black pawn on the a1-h8 diagonal, but no pawn/king
# jump exists -> quiet moves remain legal too.
pos = {(0, 0): (1, "B"), (3, 3): (0, "p"), (6, 0): (1, "C"),
       (2, 0): (1, "K"), (3, 7): (0, "K"), (5, 7): (0, "K")}
s = st(pos, 1)
lm = G.legal_moves(s)
assert "0,0>3,3" in lm, "bishop replacement capture available"
# a quiet (non-capture) move is also legal -> capture is NOT forced (no pawn/king
# jump exists). A non-capture leaves the total piece count unchanged.
assert any(len(G.apply_move(s, m).board) == len(s.board) for m in lm), \
    "at least one non-capturing move is legal (bishop/camel capture optional)"

# ---- 6. bishop capture by replacement, and blocking ---------------------------
pos = {(0, 0): (1, "B"), (2, 2): (0, "p"), (5, 5): (0, "p"),
       (2, 0): (1, "K"), (3, 7): (0, "K")}
s = st(pos, 1)
lm = G.legal_moves(s)
assert "0,0>2,2" in lm, "bishop reaches first enemy"
assert "0,0>5,5" not in lm, "bishop blocked by the piece it captures"
s2 = G.apply_move(s, "0,0>2,2")
assert s2.board[(2, 2)] == (1, "B") and s2.board[(5, 5)] == (0, "p")
assert s2.halfmove == 0, "capture resets no-progress"

# ---- 7. camel (1,3) leap + replacement capture -------------------------------
# White camel at (3,3): (1,3)->(4,6). Put a black piece to leap OVER and capture.
pos = {(3, 3): (1, "C"), (3, 4): (0, "p"), (4, 6): (0, "p"),
       (2, 0): (1, "K"), (3, 7): (0, "K")}
s = st(pos, 1)
lm = G.legal_moves(s)
assert "3,3>4,6" in lm, f"camel (1,3) leap to 4,6 (over an intervening pawn); got {lm}"
s2 = G.apply_move(s, "3,3>4,6")
assert s2.board[(4, 6)] == (1, "C"), "camel captured by replacement"
assert s2.board[(3, 4)] == (0, "p"), "leaped-over piece is NOT captured"
# quiet camel leap to an empty (3,1)/(1,1) offset also present somewhere
pos = {(3, 3): (1, "C"), (2, 0): (1, "K"), (3, 7): (0, "K")}
s = st(pos, 1)
lm = G.legal_moves(s)
camel_targets = {tuple(int(x) for x in m.split(">")[1].split(",")) for m in lm}
assert (4, 6) in camel_targets and (0, 4) in camel_targets, "camel 8-leap set"

# ---- 8. pawn promotion to K/B/C (a real choice) ------------------------------
# White promotes on row 7. White pawn on (1,6) steps to (0,7)/(2,7).
pos = {(1, 6): (1, "p"), (2, 0): (1, "K"), (3, 7): (0, "K")}
s = st(pos, 1)
lm = G.legal_moves(s)
assert "1,6>0,7=K" in lm and "1,6>0,7=B" in lm and "1,6>0,7=C" in lm, \
    f"promotion offers K/B/C; got {lm}"
s2 = G.apply_move(s, "1,6>2,7=C")
assert s2.board[(2, 7)] == (1, "C"), "pawn promoted to camel"
assert s2.halfmove == 0, "pawn move is progress"

# ---- 9. win by capturing ALL enemy kings (set inside apply_move) -------------
# White bishop captures Black's last king.
pos = {(0, 0): (1, "B"), (3, 3): (0, "K"), (2, 0): (1, "K")}
s = st(pos, 1)
assert not G.is_terminal(s)
s2 = G.apply_move(s, "0,0>3,3")
assert s2.winner == 1, "capturing the last black king wins for White"
assert G.is_terminal(s2)
assert G.returns(s2) == [-1.0, 1.0]
# with TWO kings, capturing one does NOT win yet
pos = {(0, 0): (1, "B"), (3, 3): (0, "K"), (5, 5): (0, "K"), (2, 0): (1, "K")}
s = st(pos, 1)
s2 = G.apply_move(s, "0,0>3,3")
assert s2.winner is None, "one king remains -> game continues"

# ---- 10. win by stalemate (opponent has no legal move) -----------------------
# Black to move with a single king boxed so it has no diagonal step/jump and no
# other pieces. King at corner (0,0); block both on-board diagonals with own... no,
# own pieces would give moves. Surround with enemy adjacent (can't jump: no empty
# landing) so no move exists.
pos = {(0, 0): (0, "K"), (1, 1): (1, "p"), (2, 2): (1, "p"),
       (2, 0): (1, "K"), (4, 0): (1, "K")}
s = st(pos, 0)
# king at (0,0): only diagonal on-board is (1,1) occupied by enemy; jump lands
# (2,2) occupied -> no move. No other black pieces -> stalemate.
assert G.legal_moves(s) == [], "black king has no move"
assert G.is_terminal(s)
assert G.returns(s) == [-1.0, 1.0], "stalemated black (player 0) loses"

# ---- 11. termination safety: no-progress + ply cap ---------------------------
s = st({(2, 0): (1, "K"), (3, 7): (0, "K"), (0, 0): (1, "B"), (7, 7): (0, "B")},
       0, halfmove=49)
# a non-capturing, non-pawn move bumps halfmove to 50 -> draw
mv = next(m for m in G.legal_moves(s) if ">" in m)
s2 = G.apply_move(s, mv)
assert s2.halfmove == 50 and G.is_terminal(s2) and G.returns(s2) == [0.0, 0.0], \
    "50-ply no-progress draw"
s3 = st(dict(s.board), 0, ply=400)
assert G.is_terminal(s3) and G.returns(s3) == [0.0, 0.0], "hard ply cap draw"

# ---- 12. serialize round-trips -----------------------------------------------
for state in (s0, s2, G.apply_move(s0, G.legal_moves(s0)[0])):
    d = G.serialize(state)
    import json
    json.dumps(d)  # JSON-able
    back = G.deserialize(d)
    assert G.serialize(back) == d, "serialize round-trips"

# ---- 13. a short random game terminates --------------------------------------
import random
rng = random.Random(7)
for _ in range(5):
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s) and steps < 1000:
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        steps += 1
    assert G.is_terminal(s), "random game reached a terminal state"
    ret = G.returns(s)
    assert len(ret) == 2 and all(x in (-1.0, 0.0, 1.0) for x in ret)

print("SELFTEST OK")
