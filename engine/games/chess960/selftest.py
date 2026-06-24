"""Chess960 correctness anchor (pure stdlib -- imports only agp + this game).

Covers:
  1. Standard chess is Chess960 #518: perft 20 / 400 / 8902 / 197281 from that
     forced start (proves move-gen is unchanged when the setup is standard).
  2. Every random back rank satisfies the three constraints (bishops opposite
     colours, king between rooks, mirrored) over many seeds; all 960 ids do too.
  3. Chess960 castling on NON-standard back ranks: the correct king/rook final
     squares; the empty-path rule (rook already on target file; king & rook
     adjacent; a piece between blocks it); the king may not pass through check.
  4. serialize round-trips the stored home files (JSON-able).
  5. An engine-derived perft (depth 1/2) for a non-standard position, frozen here
     as a regression anchor (these are NOT externally published; they are this
     engine's own output, recorded so a future change that perturbs move-gen on a
     shuffled back rank is caught).
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # engine/ for `agp`
from agp.chesslike import WHITE, BLACK                         # noqa: E402
from games.chess960.game import (                              # noqa: E402
    Chess960, C9State, back_rank_from_id, validate_back_rank, STANDARD_960,
)

G = Chess960()


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


def homes(rank):
    return G._homes_from_rank(rank)


def king_at(board, player):
    return next(sq for sq, (pl, t) in board.items() if pl == player and t == "K")


def main():
    # ---- 1. Standard chess == #518, perft anchor. -------------------------
    assert STANDARD_960 == 518
    assert back_rank_from_id(518) == ["R", "N", "B", "Q", "K", "B", "N", "R"]
    s0 = G.initial_state(options={"position": "518"})
    expect = {1: 20, 2: 400, 3: 8902, 4: 197281}
    for d, want in expect.items():
        got = perft(s0, d)
        assert got == want, f"#518 perft depth {d}: {got} != {want}"

    # ---- 2. Constraints hold for all 960 ids and for many RNG draws. ------
    for idx in range(960):
        rank = back_rank_from_id(idx)
        validate_back_rank(rank)
    rng = random.Random(12345)
    for _ in range(500):
        st = G.initial_state(rng=rng)
        white = [st.board[(c, 0)][1] for c in range(8)]
        black = [st.board[(c, 7)][1] for c in range(8)]
        assert white == black, "Black does not mirror White"            # mirrored
        validate_back_rank(white)
        # homes stored in state match the board.
        assert st.homes == homes(white), (st.homes, white)

    # ---- 3a. Castling final squares on a NON-standard back rank. ----------
    # Back rank where the king is NOT on e and rooks are NOT on a/h. Use #0:
    # B B Q N N R K R  -> king g(6), qrook f(5), krook h(7).
    rank0 = back_rank_from_id(0)
    assert homes(rank0) == (6, 5, 7)
    # Kingside on an unusual layout: king g1(6), krook h1(7). Rook target f1(5)
    # must be empty -> use a board with no qrook in the way. Finals: K g1, R f1.
    board = {(6, 0): (WHITE, "K"), (7, 0): (WHITE, "R"), (4, 7): (BLACK, "K")}
    st = C9State(board=board, to_move=WHITE, castling=frozenset("KQkq"),
                 homes=(6, 5, 7))
    ks = "6,0>7,0"   # king g1 onto its krook h1
    assert ks in G.legal_moves(st), f"kingside castle missing: {G.legal_moves(st)}"
    after = G.apply_move(st, ks)
    assert after.board.get((6, 0)) == (WHITE, "K"), "king not on g1 after O-O"
    assert after.board.get((5, 0)) == (WHITE, "R"), "rook not on f1 after O-O"
    # Queenside on an unusual layout: king g1(6), qrook f1(5). Finals: K c1(2),
    # R d1(3). The king sweeps g1..c1; that whole stretch must be clear.
    board = {(6, 0): (WHITE, "K"), (5, 0): (WHITE, "R"), (4, 7): (BLACK, "K")}
    st = C9State(board=board, to_move=WHITE, castling=frozenset("KQkq"),
                 homes=(6, 5, 7))
    qs = "6,0>5,0"   # king g1 onto its qrook f1
    assert qs in G.legal_moves(st), f"queenside castle missing: {G.legal_moves(st)}"
    after = G.apply_move(st, qs)
    assert after.board.get((2, 0)) == (WHITE, "K"), "king not on c1 after O-O-O"
    assert after.board.get((3, 0)) == (WHITE, "R"), "rook not on d1 after O-O-O"

    # ---- 3b. Rook already on its target file; king & rook adjacent. -------
    # King b1(1,0), rook a1(0,0): queenside king target c(2), rook target d(3).
    # King and rook are adjacent; path c1,d1 must be empty.
    board = {(1, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (7, 0): (WHITE, "R"),
             (4, 7): (BLACK, "K")}
    st = C9State(board=board, to_move=WHITE, castling=frozenset("KQkq"),
                 homes=(1, 0, 7))
    qs = "1,0>0,0"   # king onto qrook a1
    assert qs in G.legal_moves(st), "adjacent king/rook queenside castle missing"
    after = G.apply_move(st, qs)
    assert after.board.get((2, 0)) == (WHITE, "K") and after.board.get((3, 0)) == (WHITE, "R")

    # Rook already sits on its target file: king e1(4), krook f1(5) -> kingside
    # rook target is f(5) (already there), king target g(6). Path g1 must be empty.
    board = {(4, 0): (WHITE, "K"), (5, 0): (WHITE, "R"), (0, 0): (WHITE, "R"),
             (4, 7): (BLACK, "K")}
    st = C9State(board=board, to_move=WHITE, castling=frozenset("KQkq"),
                 homes=(4, 0, 5))
    ks = "4,0>5,0"
    assert ks in G.legal_moves(st), "rook-on-target kingside castle missing"
    after = G.apply_move(st, ks)
    assert after.board.get((6, 0)) == (WHITE, "K") and after.board.get((5, 0)) == (WHITE, "R")

    # ---- 3c. A piece between blocks castling. -----------------------------
    board = {(1, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (7, 0): (WHITE, "R"),
             (2, 0): (WHITE, "N"),  # knight on c1 blocks the queenside path
             (4, 7): (BLACK, "K")}
    st = C9State(board=board, to_move=WHITE, castling=frozenset("KQkq"),
                 homes=(1, 0, 7))
    assert "1,0>0,0" not in G.legal_moves(st), "blocked queenside castle was allowed"

    # ---- 3d. King may not pass through (or land on) an attacked square. ---
    # King e1(4), qrook a1(0). Queenside king path is d1(3),c1(2). Put a black
    # rook attacking c1 -> queenside must be illegal; kingside (krook h1) still ok.
    board = {(4, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (7, 0): (WHITE, "R"),
             (2, 5): (BLACK, "R"),  # black rook on c6 rakes the c-file -> c1 attacked
             (4, 7): (BLACK, "K")}
    st = C9State(board=board, to_move=WHITE, castling=frozenset("KQkq"),
                 homes=(4, 0, 7))
    mv = G.legal_moves(st)
    assert "4,0>0,0" not in mv, "queenside castle through check was allowed"
    assert "4,0>7,0" in mv, "kingside castle wrongly forbidden"

    # King in check may not castle at all.
    board = {(4, 0): (WHITE, "K"), (0, 0): (WHITE, "R"), (7, 0): (WHITE, "R"),
             (4, 5): (BLACK, "R"),  # checks the king on the e-file
             (0, 7): (BLACK, "K")}
    st = C9State(board=board, to_move=WHITE, castling=frozenset("KQkq"),
                 homes=(4, 0, 7))
    mv = G.legal_moves(st)
    assert "4,0>0,0" not in mv and "4,0>7,0" not in mv, "castled out of check"

    # ---- 4. serialize round-trips the home files and is JSON-able. --------
    st = G.initial_state(rng=random.Random(7))
    ser = G.serialize(st)
    json.dumps(ser)                              # must be JSON-able
    assert ser["homes"] == list(st.homes)
    again = G.serialize(G.deserialize(ser))
    assert again == ser, "serialize did not round-trip"
    assert G.deserialize(ser).homes == st.homes

    # A reachable mid-game state (after castling) also round-trips with homes.
    mid = G.apply_move(G.initial_state(options={"position": "518"}), "4,1>4,3")
    assert G.serialize(G.deserialize(G.serialize(mid))) == G.serialize(mid)

    # ---- 5. Engine-derived perft for a non-standard position (frozen). ----
    # Position #356 (engine output recorded as a regression anchor, NOT published).
    s356 = G.initial_state(options={"position": "356"})
    ENGINE_DERIVED_356 = {1: 18, 2: 324}
    for d, want in ENGINE_DERIVED_356.items():
        got = perft(s356, d)
        assert got == want, f"#356 (engine-derived) perft depth {d}: {got} != {want}"

    print("SELFTEST OK  (perft #518: 20/400/8902/197281; #356 d1/d2: 18/324)")


if __name__ == "__main__":
    main()
