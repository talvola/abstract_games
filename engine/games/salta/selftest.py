"""Salta selftest (pure stdlib).

Anchors:
1. Exact initial setup and target mapping (Abstract Games #8 diagrams,
   verified square by square from the article's figures).
2. Opening move count (9 sun steps; moons/stars are boxed in; no jumps).
3. Compulsory single forward jump: jumps-only when available, no chains, no
   backward jumps, no jumping own pieces, jumped piece NOT removed.
4. Blockade rule: a move leaving the opponent with no legal move is illegal.
5. Goal completion via apply_move: first-player win, the one-tempo draw, and
   the second-player-completes-always-wins asymmetry.
6. The 120-move (240-ply) cutoff scoring, including the {0,1} draw band.
7. THE HISTORICAL GAME: Krone-Grotewold, Jüterbog 1901 (the article's full
   214-ply record) replays with every recorded move legal; Red (player 1)
   exactly completes the goal on move 107; player 0's free remaining count is
   25 and the true own-blocking optimum (A* search) is 27 = the published
   "Red wins by 27 Points!".
8. 200 random playouts terminate within the 240-ply cap with sane returns.
9. heuristic returns per-seat payoffs; MCTSBot smoke test at max_rollout=4.
"""

import heapq
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))     # engine root (for agp)

from agp.loader import load_from_dir  # noqa: E402

man, g = load_from_dir(HERE)
import importlib  # noqa: E402

sg = importlib.import_module(type(g).__module__)
SaltaState = sg.SaltaState


def cellstr(sq):
    return f"{sq[0]},{sq[1]}"


def alg2sq(a):
    return (ord(a[0]) - 97, int(a[1:]) - 1)


# ---- 1. setup & targets ----------------------------------------------------
s0 = g.initial_state()
assert len(s0.board) == 30
exp_start0 = {}
exp_target0 = {}
for n in range(1, 6):
    exp_start0[("star", n)] = alg2sq("acegi"[n - 1] + "1")
    exp_start0[("moon", n)] = alg2sq("bdfhj"[n - 1] + "2")
    exp_start0[("sun", n)] = alg2sq("acegi"[n - 1] + "3")
    exp_target0[("star", n)] = alg2sq("bdfhj"[n - 1] + "8")
    exp_target0[("moon", n)] = alg2sq("acegi"[n - 1] + "9")
    exp_target0[("sun", n)] = alg2sq("bdfhj"[n - 1] + "10")
for k, sq in exp_start0.items():
    assert s0.board[sq] == (0, k[0], k[1]), (k, sq, s0.board.get(sq))
    rsq = (9 - sq[0], 9 - sq[1])
    assert s0.board[rsq] == (1, k[0], k[1]), (k, rsq)          # 180-deg mirror
    assert sg.TARGET[0][k] == exp_target0[k]
    assert sg.TARGET[1][k] == (9 - exp_target0[k][0], 9 - exp_target0[k][1])
# spot checks straight from the article's diagrams
assert sg.START[1][("star", 1)] == alg2sq("j10")
assert sg.TARGET[0][("star", 1)] == alg2sq("b8")
assert sg.TARGET[0][("sun", 5)] == alg2sq("j10")
assert sg.TARGET[1][("star", 1)] == alg2sq("i3")
assert sg.TARGET[1][("moon", 1)] == alg2sq("j2")
assert sg.TARGET[1][("sun", 5)] == alg2sq("a1")
# all squares dark (a1 dark => c+r even)
for tbl in (*sg.START, *sg.TARGET):
    for c, r in tbl.values():
        assert (c + r) % 2 == 0

# ---- 2. opening moves ------------------------------------------------------
first = set(g.legal_moves(s0))
exp = set()
for frm, tos in [("a3", ["b4"]), ("c3", ["b4", "d4"]), ("e3", ["d4", "f4"]),
                 ("g3", ["f4", "h4"]), ("i3", ["h4", "j4"])]:
    for to in tos:
        exp.add(f"{cellstr(alg2sq(frm))}>{cellstr(alg2sq(to))}")
assert first == exp, first
assert len(first) == 9

# ---- 3. jumping ------------------------------------------------------------
def mkstate(pieces, to_move, ply=None):
    board = {}
    for pl, kind, n, a in pieces:
        board[alg2sq(a)] = (pl, kind, n)
    if ply is None:
        ply = 100 + to_move       # keep parity consistent with to_move
    return SaltaState(board=board, to_move=to_move, ply=ply)


# green sun1 e5 faces red star1 f6 (g7 empty): jump compulsory; another red on
# h8 (i9 empty) must NOT extend into a chain; green moon1 a1 has free steps
# that must be suppressed; red star2 d4 sits diagonally BEHIND e5 (c3 empty)
# and must not be jumpable.
st = mkstate([(0, "sun", 1, "e5"), (0, "moon", 1, "a1"),
              (1, "star", 1, "f6"), (1, "star", 2, "d4"), (1, "moon", 1, "h8"),
              (1, "sun", 1, "j10")], to_move=0)
lm = g.legal_moves(st)
assert lm == [f"{cellstr(alg2sq('e5'))}>{cellstr(alg2sq('g7'))}"], lm
nxt = g.apply_move(st, lm[0])
assert nxt.board[alg2sq("f6")] == (1, "star", 1)      # jumped piece NOT removed
assert nxt.board[alg2sq("g7")] == (0, "sun", 1)
assert alg2sq("e5") not in nxt.board
assert len(nxt.board) == len(st.board)                # nothing ever captured
# no jumping own pieces: green piece in front instead of red -> steps offered
st2 = mkstate([(0, "sun", 1, "e5"), (0, "star", 1, "f6"), (1, "sun", 1, "j10")],
              to_move=0)
assert all(abs(int(m.split(">")[1].split(",")[1]) -
               int(m.split(">")[0].split(",")[1])) == 1 for m in g.legal_moves(st2))
# red jumps FORWARD = down the board
st3 = mkstate([(1, "sun", 1, "f6"), (0, "star", 1, "e5"), (0, "sun", 1, "a1")],
              to_move=1)
assert f"{cellstr(alg2sq('f6'))}>{cellstr(alg2sq('d4'))}" in g.legal_moves(st3)
assert len(g.legal_moves(st3)) == 1                   # jump obligatory for red too

# ---- 4. blockade rule ------------------------------------------------------
# red's ONLY piece sits on a1; its only escape square is b2. Green c3->b2
# would leave red without any legal move and must be filtered out, while
# green's other moves remain.
st4 = mkstate([(1, "sun", 1, "a1"), (0, "star", 1, "c3"), (0, "moon", 1, "j8")],
              to_move=0)
lm4 = g.legal_moves(st4)
bad = f"{cellstr(alg2sq('c3'))}>{cellstr(alg2sq('b2'))}"
assert bad not in lm4, lm4
assert any(m.startswith(cellstr(alg2sq("c3"))) for m in lm4)   # c3 may still move elsewhere
assert any(m.startswith(cellstr(alg2sq("j8"))) for m in lm4)

# ---- 5. completion & tempo draw -------------------------------------------
def near_complete(pl, hold_out_kind, hold_out_n, at, others_exact=True):
    """All of `pl`'s pieces on target except one, placed at `at`."""
    pieces = []
    for (kind, n), sq in sg.TARGET[pl].items():
        if (kind, n) == (hold_out_kind, hold_out_n):
            pieces.append((pl, kind, n, at))
        else:
            pieces.append((pl, kind, n, f"{chr(97 + sq[0])}{sq[1] + 1}"))
    return pieces


# green a7 -> b8 completes; red one move from home => DRAW (tempo rule)
pieces = near_complete(0, "star", 1, "a7") + near_complete(1, "sun", 1, "j2")
std = mkstate(pieces, to_move=0, ply=200)
mv = f"{cellstr(alg2sq('a7'))}>{cellstr(alg2sq('b8'))}"
assert mv in g.legal_moves(std)
end = g.apply_move(std, mv)
assert end.done and g.is_terminal(end)
assert end.winner is None and g.returns(end) == [0.0, 0.0], (end.winner)

# same but red two moves away => green WINS
pieces = near_complete(0, "star", 1, "a7") + near_complete(1, "sun", 1, "i3")
stw = mkstate(pieces, to_move=0, ply=200)
end = g.apply_move(stw, mv)
assert end.done and end.winner == 0 and g.returns(end) == [1.0, -1.0]

# red completes while green needs one move => RED WINS (no draw: asymmetry)
pieces = near_complete(1, "sun", 1, "j2") + near_complete(0, "star", 1, "a7")
str_ = mkstate(pieces, to_move=1, ply=201)
mvr = f"{cellstr(alg2sq('j2'))}>{cellstr(alg2sq('i1'))}"
assert mvr in g.legal_moves(str_)
end = g.apply_move(str_, mvr)
assert end.done and end.winner == 1 and g.returns(end) == [-1.0, 1.0]

# ---- 6. 120-move cutoff ----------------------------------------------------
# equal counts at the cutoff -> draw band; player 1 one closer -> also draw;
# player 1 two closer -> player 1 wins; player 0 two closer -> player 0 wins
# by diff-1 >= 1.
base0 = near_complete(0, "star", 1, "a7")             # D0 = 1
for red_at, expect in [("j2", [0.0, 0.0]),            # D1=1, diff=0 -> draw
                       ("i3", [0.0, 0.0])]:           # D1=2, diff=1 -> draw (tempo)
    stc = mkstate(base0 + near_complete(1, "sun", 1, red_at), to_move=0, ply=240)
    assert g.is_terminal(stc)
    assert g.returns(stc) == expect, (red_at, g.returns(stc))
stc = mkstate(near_complete(0, "star", 1, "c5")       # D0=3 (c5 -> b8)
              + near_complete(1, "sun", 1, "j2"), to_move=0, ply=240)
assert g.returns(stc) == [-1.0, 1.0]                  # diff=-2 -> player 1 wins
stc = mkstate(base0 + near_complete(1, "sun", 1, "f4"), to_move=0, ply=240)
assert sg._needed(stc.board, 1) == 3                  # f4 -> i1
assert g.returns(stc) == [1.0, -1.0]                  # diff=2 -> player 0 wins by 1

# ---- 7. the historical game (Krone-Grotewold, Jüterbog 1901) ---------------
RECORD = (
    "e3f4 f8e7 c3d4 d8c7 b2c3 h8g7 g3h4 j8i7 c1b2 i7j6 i3j4 j6i5 j4:h6 i5:g3 "
    "h6:f8 c9d8 d2e3 d10c9 f8:d10 c7b6 e1d2 g3:e1 a3b4 b8a7 j2i3 d8c7 i3j4 c7d6 "
    "d4c5 b6:d4 c3:e5 a9b8 e5:c7 g9h8 c7:a9 d6e5 f4:d6 h10g9 d6:f8 g7h6 "
    "f8:h10 h6g5 h4:f6 b8c7 f6:d8 g5f4 e3:g5 f4g3 h2:f4 e9f8 f4:d6 c9b8 "
    "f2:h4 b10c9 d8:b10 e7f6 g5:e7 c9d8 e7:c9 f6g5 h4:f6 g3h2 g1:i3 h8i7 "
    "i1:g3 d4c3 b2:d4 c3b2 a1:c3 d8e7 f6:d8 i9h8 d4:f6 h8g7 f6:h8 j10i9 "
    "h8:j10 f10e9 d8:f10 e5f4 g3:e5 f4e3 d2:f4 c7d8 f4:h6 g7:i5 h6:j8 e3d4 "
    "j4:h6 b8c7 d6:b8 a7b6 c5:a7 e7f6 e5:g7 d8e7 c3:e5 e9d8 g7:e9 i9h8 "
    "e5:g7 f6e5 g7:i9 f8g7 h6:f8 g5h4 i3:g5 i7h6 g5:i7 h8:j6 i9h8 e1f2 "
    "b4c5 e7f6 c5d6 g9:e7 h10g9 e7:c5 f8e7 f2g3 e9f8 h2g1 d10e9 g3h2 "
    "j10i9 h2i1 i9h10 h4g3 j8i9 g3f2 i9j8 f2e1 j8i9 i5j4 i9j8 j4i3 j8i9 i3j2 "
    "i9j8 b2c1 j8i9 d4e3 i9j8 e3d2 j8i9 b6a5 a7b6 a5b4 i9j8 c7:a5 b6c7 d8:b6 "
    "b8a7 b4c3 c9b8 c3b2 c7d8 b2a1 b8c7 a5b4 d8c9 e5d4 c9d10 f6e5 e7f6 h6g5 "
    "i7h6 g7:i5 j8i7 d4c3 f8g7 c3b2 e9f8 b2a3 b10c9 c5d4 c9d8 b6c5 a7b6 d4e3 "
    "d8e7 e3f4 f10e9 e5d4 g9f10 d4c3 h8g9 c5d4 b6c5 c3b2 c7b8 g5h4 d6c7 h4g3 "
    "c7d8 g3h2 d8c9 i5h4 c9b10 h4g3 g7h8 g3f2 h8i9 j6i5 i9j8 i5h4 f8g7 h4i3 "
    "g7h8 f4g3 h8i9 d4e3 i9j10 b4c3"
)
tokens = RECORD.split()
assert len(tokens) == 214
s = g.initial_state()
for i, tok in enumerate(tokens):
    jump = ":" in tok
    tok = tok.replace(":", "")
    # split the algebraic pair: first square = letter + digits (rank may be "10")
    k = 1
    while tok[k].isdigit():
        k += 1
    frm, to = alg2sq(tok[:k]), alg2sq(tok[k:])
    mv = f"{cellstr(frm)}>{cellstr(to)}"
    legal = g.legal_moves(s)
    assert mv in legal, (i + 1, tok, mv, legal[:12])
    assert jump == (abs(to[1] - frm[1]) == 2), (i + 1, tok)
    s = g.apply_move(s, mv)
assert s.ply == 214
# Red (player 1) completed the goal position exactly on move 107
assert s.done and s.winner == 1 and g.returns(s) == [-1.0, 1.0]
assert sg._needed(s.board, 1) == 0
# free remaining count for player 0 (Wikipedia's counting) is 25
assert sg._needed(s.board, 0) == 25
mid = g.deserialize(g.serialize(s))                   # round-trip a rich state
assert g.serialize(mid) == g.serialize(s)

# 7b. published score: "Red wins by 27 Points!" = player 0's true minimum
# with OWN pieces blocking (opponent removed), found by A* search.
targets = tuple(sg.TARGET[0][(p[1], p[2])]
                for sq, p in sorted(s.board.items()) if p[0] == 0)
start = tuple(sq for sq, p in sorted(s.board.items()) if p[0] == 0)


def hsum(state):
    return sum(sg._dist(a, b) for a, b in zip(state, targets))


seen = {start: 0}
pq = [(hsum(start), 0, start)]
best = None
while pq:
    f, dep, st_ = heapq.heappop(pq)
    if hsum(st_) == 0:
        best = dep
        break
    if f > 28:
        break
    occ = set(st_)
    for idx, pos in enumerate(st_):
        for dc in (-1, 1):
            for dr in (-1, 1):
                t = (pos[0] + dc, pos[1] + dr)
                if not (0 <= t[0] < 10 and 0 <= t[1] < 10) or t in occ:
                    continue
                ns = list(st_)
                ns[idx] = t
                ns = tuple(ns)
                nd = dep + 1
                if seen.get(ns, 1 << 30) <= nd:
                    continue
                seen[ns] = nd
                heapq.heappush(pq, (nd + hsum(ns), nd, ns))
assert best == 27, best     # the published margin, re-derived

# ---- 8. random playouts ----------------------------------------------------
rng = random.Random(20260718)
outcomes = {(1.0, -1.0): 0, (-1.0, 1.0): 0, (0.0, 0.0): 0}
for _ in range(200):
    s = g.initial_state()
    while not g.is_terminal(s):
        assert s.ply < 240
        moves = g.legal_moves(s)
        assert moves
        s = g.apply_move(s, rng.choice(moves))
    r = tuple(g.returns(s))
    assert r in outcomes, r
    outcomes[r] += 1
assert sum(outcomes.values()) == 200

# ---- 9. heuristic shape + bot smoke ---------------------------------------
h = g.heuristic(g.initial_state())
assert isinstance(h, list) and len(h) == 2
assert abs(h[0] + h[1]) < 1e-9
from agp.mcts import MCTSBot  # noqa: E402

mv = MCTSBot(random.Random(1), iterations=24, max_rollout=4).select(g, g.initial_state())
assert mv in g.legal_moves(g.initial_state())

print("salta selftest OK", outcomes)
