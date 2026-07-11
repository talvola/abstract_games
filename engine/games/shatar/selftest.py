"""Shatar selftest -- pure stdlib correctness anchors.

Anchors (all cross-checked one-time against Fairy-Stockfish via pyffish, see
``_diff_pyffish.py``): the FSF start position (obligatory 1.d4 d5 pre-played)
with its exact 20 legal moves, perft(1..3) = 20/400/8426, bers movement,
mandatory promotion to bers, and the shatar mate classifications reached via
``apply_move`` -- shak-chain mate (win), niol (draw), forbidden knight mate
(mated side wins), robado (bare king draw, and its precedence over mate),
stalemate, repetition, serialization of the check chain, and random-playout
termination.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

man, G = load_from_dir(Path(__file__).resolve().parent)

FILES = "abcdefgh"
WHITE, BLACK = 0, 1


def to_uci(move):
    raw, promo = (move.split("=") + [None])[:2]
    fs, ts = raw.split(">")
    fc, fr = (int(x) for x in fs.split(","))
    tc, tr = (int(x) for x in ts.split(","))
    return f"{FILES[fc]}{fr + 1}{FILES[tc]}{tr + 1}" + ("j" if promo else "")


def state_from_fen(fen):
    """Minimal FEN -> state (board + side to move only; no history)."""
    board_s, stm = fen.split()[:2]
    board = {}
    for i, rank in enumerate(board_s.split("/")):
        row, col = 7 - i, 0
        for ch in rank:
            if ch.isdigit():
                col += int(ch)
            else:
                pl = WHITE if ch.isupper() else BLACK
                board[f"{col},{row}"] = [pl, ch.upper()]
                col += 1
    return G.deserialize({"board": board, "to_move": 0 if stm == "w" else 1,
                          "castling": "", "ep": None, "halfmove": 0,
                          "ply": 0, "reps": {}})


def play(state, ucis):
    for u in ucis:
        legal = {to_uci(m): m for m in G.legal_moves(state)}
        assert u in legal, f"{u} not legal; have {sorted(legal)}"
        state = G.apply_move(state, legal[u])
    return state


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1)
               for m in G.legal_moves(state))


# ---- initial position (FSF: rnbjkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBJKBNR w)
st0 = G.initial_state()
assert st0.to_move == WHITE
assert st0.board[(3, 0)] == (WHITE, "J") and st0.board[(3, 7)] == (BLACK, "J")
assert st0.board[(4, 0)] == (WHITE, "K") and st0.board[(4, 7)] == (BLACK, "K")
assert st0.board[(3, 3)] == (WHITE, "P") and st0.board[(3, 4)] == (BLACK, "P")
assert (3, 1) not in st0.board and (3, 6) not in st0.board
assert len(st0.board) == 32
# the exact FSF legal-move list from the start position
FSF_START_MOVES = ['a2a3', 'b1a3', 'b1c3', 'b1d2', 'b2b3', 'c1d2', 'c1e3',
                   'c1f4', 'c1g5', 'c1h6', 'c2c3', 'd1d2', 'd1d3', 'e1d2',
                   'e2e3', 'f2f3', 'g1f3', 'g1h3', 'g2g3', 'h2h3']
assert sorted(to_uci(m) for m in G.legal_moves(st0)) == FSF_START_MOVES
assert "a2a4" not in {to_uci(m) for m in G.legal_moves(st0)}  # no double step
print("initial position + FSF 20-move list OK")

# ---- perft (differentially anchored vs pyffish; perft(4)=177344 in _diff) ----
for d, want in ((1, 20), (2, 400), (3, 8426)):
    got = perft(st0, d)
    assert got == want, f"perft({d}) = {got}, want {want}"
print("perft(1..3) = 20/400/8426 OK")

# ---- bers movement: rook slides + one-step diagonals -------------------------
sb = state_from_fen("k7/p7/8/8/3J4/8/8/7K w - - 0 1")
bers = sorted(to_uci(m) for m in G.legal_moves(sb) if m.startswith("3,3>"))
want = sorted([f"d4d{r}" for r in (1, 2, 3, 5, 6, 7, 8)]
              + [f"d4{f}4" for f in "abcefgh"]
              + ["d4c3", "d4e3", "d4c5", "d4e5"])
assert bers == want, f"bers moves {bers}"
print("bers movement OK (7+7 rook rays + 4 diagonal steps)")

# ---- promotion: mandatory, bers only -----------------------------------------
sp = state_from_fen("8/6P1/7K/p7/k7/8/8/8 w - - 0 1")
promos = [to_uci(m) for m in G.legal_moves(sp) if m.startswith("6,6>")]
assert promos == ["g7g8j"], promos
sp2 = play(sp, ["g7g8j"])
assert sp2.board[(6, 7)] == (WHITE, "J")
print("promotion to bers (mandatory, only option) OK")

# ---- shak-chain mate: 1.Rg1+ Kh8 2.Bb2# -> White wins ------------------------
sc = play(state_from_fen("6k1/8/7K/p7/8/B7/8/R7 w - - 0 1"),
          ["a1g1", "g8h8", "a3b2"])
assert G.is_terminal(sc) and G.returns(sc) == [1.0, -1.0]
assert "checkmate" in G.render(sc)["caption"]
print("shak-chain mate (rook check then bishop mate) = win OK")

# ---- niol: same mate with no shak in the check series -> draw ----------------
sn = play(state_from_fen("7k/8/7K/p7/8/B7/8/6R1 w - - 0 1"),
          ["g1g2", "a5a4", "a3b2"])
assert G.is_terminal(sn) and G.returns(sn) == [0.0, 0.0]
assert "niol" in G.render(sn)["caption"]
print("niol (bishop mate, no shak) = draw OK")

# ---- forbidden knight mate -> the MATED side wins ----------------------------
sk = play(state_from_fen("k7/8/8/1N6/3B4/7p/7P/1R5K w - - 0 1"), ["b5c7"])
assert G.is_terminal(sk) and G.returns(sk) == [-1.0, 1.0]   # Black (mated) wins
assert "knight" in G.render(sk)["caption"]
print("forbidden knight mate = mated side wins OK")

# ---- robado: baring capture = draw, even when it would be mate ---------------
sr = play(state_from_fen("k7/1p5J/1K6/8/8/8/8/8 w - - 0 1"), ["h7b7"])
assert G.is_terminal(sr) and G.returns(sr) == [0.0, 0.0]
assert "robado" in G.render(sr)["caption"]
print("robado (bare king, overrides mate) = draw OK")

# ---- stalemate = draw ---------------------------------------------------------
ss = state_from_fen("k7/p1K5/P7/8/8/8/8/8 b - - 0 1")
assert G.is_terminal(ss) and G.returns(ss) == [0.0, 0.0]
assert "stalemate" in G.render(ss)["caption"]
print("stalemate = draw OK")

# ---- threefold repetition = draw ----------------------------------------------
sv = state_from_fen("kr6/8/8/8/8/8/8/KR6 w - - 0 1")
shuffle = ["b1h1", "b8h8", "h1b1", "h8b8"] * 2 + ["b1h1"]  # 3rd occurrence
sv = play(sv, shuffle)
assert G.is_terminal(sv) and G.returns(sv) == [0.0, 0.0]
print("threefold repetition = draw OK")

# ---- serialization round-trips the check chain --------------------------------
mid = play(state_from_fen("6k1/8/7K/p7/8/B7/8/R7 w - - 0 1"),
           ["a1g1", "g8h8"])          # Black in check; chain has a shak
d = G.serialize(mid)
assert d["chain"][BLACK] == [True, True], d["chain"]
mid2 = G.deserialize(d)
fin = play(mid2, ["a3b2"])
assert G.returns(fin) == [1.0, -1.0]  # chain survived the round-trip
# and without the chain field (legacy dict) the same mate degrades to niol
d2 = {k: v for k, v in d.items() if k != "chain"}
fin2 = play(G.deserialize(d2), ["a3b2"])
assert G.returns(fin2) == [0.0, 0.0]
print("check-chain serialization OK")

# ---- random playouts terminate -------------------------------------------------
rng = random.Random(42)
results = {"white": 0, "black": 0, "draw": 0}
plies = []
for _ in range(300):
    st = G.initial_state()
    while not G.is_terminal(st):
        st = G.apply_move(st, rng.choice(G.legal_moves(st)))
    r = G.returns(st)
    results["draw" if r == [0.0, 0.0] else ("white" if r[0] > 0 else "black")] += 1
    plies.append(st.ply)
print(f"300 random playouts OK: {results}, "
      f"avg {sum(plies) / len(plies):.1f} plies (max {max(plies)})")

print("shatar selftest: all tests passed")
