"""Hi-Jack self-test -- pure stdlib.

Anchors:
  (a) both annotated sample games from Abstract Games #14 replay legally
      end-to-end via apply_move (each printed move must be in legal_moves);
  (b) hand-computed strength / blocking cases (4-high affected set, a blocked
      far square, the article's g3/c5/f6 strength claims);
  (c) a small end-of-game scoring case;
  (d) an honest draw is reachable via symmetric play.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir   # noqa: E402

_, GAME = load_from_dir(Path(__file__).resolve().parent)
WHITE, BLACK = 0, 1


def cell(alg):
    """Algebraic 'd4' -> move string 'c,r' (a=col0, rank1=row0)."""
    c = ord(alg[0]) - ord('a')
    r = int(alg[1:]) - 1
    return f"{c},{r}"


def replay(moves, label, first=1):
    """moves = flat list of algebraic/pass/switch tokens in play order.
    `first` = seat to move first (1=Black default, 0=White)."""
    st = GAME.initial_state()
    st.to_move = first
    for i, tok in enumerate(moves):
        mv = tok if tok in ("pass", "switch") else cell(tok)
        legal = GAME.legal_moves(st)
        assert mv in legal, (
            f"{label}: move #{i} '{tok}' ({mv}) illegal; "
            f"to_move={st.to_move} legal-count={len(legal)}")
        st = GAME.apply_move(st, mv)
        # round-trip serialise as we go
        assert GAME.serialize(GAME.deserialize(GAME.serialize(st))) == GAME.serialize(st)
    return st


# --------------------------------------------------------------------------
# (a) Sample Game 1 (Black moves first). Flat play order: B, W, B, W, ...
G1 = [
    "d4", "f4",   # 1
    "e6", "f4",   # 2  (White reinforces f4 -> 2-high)
    "d3", "f6",   # 3
    "e7", "e2",   # 4
    "b6", "b4",   # 5
    "a6", "c2",   # 6
    "a2", "b3",   # 7
    "e3", "c2",   # 8  (White reinforces c2)
    "a2", "g3",   # 9  (Black reinforces a2)
    "f1", "f3",   # 10
    "e3", "h5",   # 11 (Black reinforces e3)
    "g7", "h6",   # 12
    "c8", "c5",   # 13
    "d6", "a8",   # 14
    "f8", "h8",   # 15
    "a4", "b8",   # 16
    "c8", "b7",   # 17 (Black reinforces c8)
    "e7", "h1",   # 18 (Black reinforces e7)
    "d1", "d2",   # 19
    "c1", "g3",   # 20 (White reinforces g3 -> 2-high; strength reaches g1 & g5)
    "pass", "c5", # 21 (Black passes; White reinforces c5 -> reaches c7)
    "c6", "f6",   # 22 (White reinforces f6)
    "f8", "h8",   # 23 (Black reinforces f8; White reinforces h8)
    "g8",         # 24 (Black; game continues in the article)
]

st1 = replay(G1, "Game1")
print("Sample Game 1: replayed", len(G1), "half-moves legally")


# --------------------------------------------------------------------------
# (b) strength / blocking hand cases, using the running Game-1 position.
def strength_of(st, alg):
    s = GAME._strength(st)
    c, r = map(int, cell(alg).split(","))
    return s.get((c, r), [0, 0])   # [white, black]


# White reinforced g3 -> 2-high (move 20); a 2-high stack reaches 2 orthogonally,
# so its strength reaches g1 and g5 (article's own annotation).
assert strength_of(st1, "g1")[0] >= 1, "g3(2-high) should reach g1"
assert strength_of(st1, "g5")[0] >= 1, "g3(2-high) should reach g5"
# White reinforced c5 -> 2-high (move 21); strength reaches c7.
assert strength_of(st1, "c7")[0] >= 1, "c5(2-high) should reach c7"

# 4-high stack affected-set on an empty board: orth 4, diag 2, matching the text
# ("four squares orthogonally and two squares diagonally").
empty = GAME.initial_state()
cov = set(GAME._covered((4, 4), 4, set(), empty.size))
expect = set()
for d in range(1, 5):
    expect |= {(4 + d, 4), (4 - d, 4), (4, 4 + d), (4, 4 - d)}
for d in range(1, 3):
    expect |= {(4 + d, 4 + d), (4 + d, 4 - d), (4 - d, 4 + d), (4 - d, 4 - d)}
expect = {(x, y) for (x, y) in expect if 0 <= x < empty.size and 0 <= y < empty.size}
assert cov == expect, f"4-high pattern mismatch: {cov ^ expect}"

# Blocking: a 2-high stack at (2,2) whose one intervening square to the right is
# occupied loses its far (distance-2) square; the near (distance-1) square keeps
# its strength. (The article's "blocked on the far right" diagram, left case.)
occ = {(2, 2), (3, 2)}   # stack square + the intervening occupied square
cov2 = set(GAME._covered((2, 2), 2, occ, 8))
assert (4, 2) not in cov2, "far orthogonal square must be blocked"
assert (3, 2) in cov2, "intervening square still receives strength"
assert (0, 2) in cov2 and (2, 4) in cov2, "unblocked rays reach distance 2"
print("Strength / blocking hand cases: OK")


# --------------------------------------------------------------------------
# (a') Sample Game 2 (White moves first). Flat play order: W, B, W, B, ...
G2 = [
    "e5", "c5",   # 1
    "d4", "c4",   # 2
    "d4", "e7",   # 3  (White reinforces d4 -> 2-high)
    "f6", "f7",   # 4
    "f6", "e3",   # 5  (White reinforces f6 -> 2-high)
    "d3", "e2",   # 6
    "b3", "b4",   # 7
    "a3", "a6",   # 8
    "c1", "a1",   # 9
    "c1", "b1",   # 10 (White reinforces c1)
    "b2", "b1",   # 11 (Black reinforces b1)
    "f1", "f2",   # 12
    "f1", "g4",   # 13 (White reinforces f1)
    "b2", "g4",   # 14 (White reinforces b2; Black reinforces g4)
    "h5", "g6",   # 15
    "f5", "h6",   # 16
    "g5", "g6",   # 17 (Black reinforces g6)
    "h3", "e3",   # 18 (Black reinforces e3)
    "f4", "g3",   # 19
    "h4", "c5",   # 20 (Black reinforces c5 -> reaches e5)
    "g4", "g7",   # 21 (White reinforces g4)
    "g3", "e5",   # 22 (White reinforces g3; Black attacks/takes e5)
    "d6", "e6",   # 23
    "d5", "c7",   # 24
    "d8", "d7",   # 25
    "c8", "d6",   # 26
    "a8", "c7",   # 27 (Black reinforces c7)
    "a8", "d6",   # 28 (White reinforces a8; Black reinforces d6)
    "e8", "f6",   # 29 (Black HI-JACKS White's 2-high f6)
    "h8", "g8",   # 30
    "g3", "f6",   # 31 (Black reinforces the hi-jacked f6 -> 4-high, reaches f3 & f2)
    "f4", "f3",   # 32 (White reinforces f4)
    "d2", "d5",   # 33 (Black attacks/takes White's d5)
    "e4", "e5",   # 34 (Black reinforces the taken e5)
    "b3", "a6",   # 35 (White reinforces b3; Black reinforces a6)
    "pass", "d4", # 36 (White passes; Black HI-JACKS White's 2-high d4)
    "pass", "e4", # 37 (White passes; Black attacks/takes White's e4)
    "c3", "d5",   # 38 (Black reinforces the taken d5)
    "d1", "d3",   # 39
    "d2", "d8",   # 40 (Black reinforces d8)
    "pass", "c8", # 41 (White passes; Black reinforces c8)
    "b8", "b7",   # 42
    "c3", "b8",   # 43 (White reinforces c3; Black attacks/takes White's b8)
    "pass", "a8", # 44 (White passes; Black HI-JACKS White's 2-high a8)
]

st2 = replay(G2, "Game2", first=0)   # White moves first in Sample Game 2
print("Sample Game 2: replayed", len(G2), "half-moves legally")

# hi-jack bookkeeping: f6, d4, a8 were hi-jacked by Black and still Black-topped.
for hj in ("f6", "d4", "a8"):
    c, r = map(int, cell(hj).split(","))
    assert (c, r) in st2.hijacks, f"{hj} should be a hi-jack"
    assert st2.board[(c, r)][-1] == 1, f"{hj} should be Black-topped"
# f6 reinforced to 4-high; strength reaches f3 and f2 (article annotation).
c, r = map(int, cell("f6").split(","))
assert len(st2.board[(c, r)]) == 4, "f6 should be 4-high"
assert strength_of(st2, "f3")[1] >= 1 and strength_of(st2, "f2")[1] >= 1, \
    "hi-jacked 4-high f6 reaches f3 and f2"
print("Sample Game 2 hi-jack bookkeeping: OK")


# --------------------------------------------------------------------------
# (c) small end-of-game scoring case.
sc = GAME.initial_state()
# a lone Black 1-high stack at d4: it out-strengths White on its 4 orthogonal
# neighbours (White has nothing) -> Black scores 4, White 0.
sc.board = {(3, 3): [BLACK]}
w, b = GAME.score(sc)
assert (w, b) == (0, 4), f"lone-stack scoring wrong: {(w, b)}"
# add a Black-topped stack in the corner (Black gains its territory rays but no
# hi-jack point yet), then mark it hi-jacked: exactly +1 more to Black.
sc.board[(0, 0)] = [WHITE, WHITE, BLACK]
_, b_terr = GAME.score(sc)
sc.hijacks = {(0, 0)}
w, b = GAME.score(sc)
assert b == b_terr + 1, f"hi-jack should add exactly 1 point: {(b_terr, b)}"
assert w == 0
assert GAME.returns(sc) == [-1.0, 1.0]
print("Scoring case: OK")

# --------------------------------------------------------------------------
# (d) an honest draw is reachable via symmetric (central-mirror) play.
draw_moves = ["a1", "h8", "a2", "h7", "b1", "g8", "pass", "pass"]
sd = GAME.initial_state()
for tok in draw_moves:
    mv = tok if tok == "pass" else cell(tok)
    assert mv in GAME.legal_moves(sd), f"draw move {tok} illegal"
    sd = GAME.apply_move(sd, mv)
assert GAME.is_terminal(sd), "two passes should end the game"
assert GAME.returns(sd) == [0.0, 0.0], f"symmetric play must draw: {GAME.score(sd)}"
print("Honest-draw case: OK")

print("hijack selftest: all checks passed")
