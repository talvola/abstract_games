"""Entropy correctness anchor (pure stdlib). Checks the board + 7 colours/counts,
the draw-and-store randomness model, Chaos placement, Order's slide-through-empties
(no jumping) / pass, the palindrome scoring on hand-built lines, the board-full
terminal reached via apply_move, the single-game winner rule, and serialize
round-trip (bag + next_tile included)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.entropy.game import (  # noqa: E402
    Entropy, EntropyState, COLOURS, PER_COLOUR, N, PAR, CHAOS, ORDER,
    _palindrome_score, _full_bag,
)

G = Entropy()


def main():
    # --- board + colour counts -------------------------------------------
    assert N == 7
    assert len(COLOURS) == 7 and PER_COLOUR == 7
    bag = _full_bag()
    assert sum(bag.values()) == 49 and all(bag[c] == 7 for c in COLOURS)

    # --- initial state: Chaos to move with a drawn-and-stored next_tile ---
    s = G.initial_state(rng=random.Random(1))
    assert s.to_move == CHAOS
    assert s.next_tile in COLOURS            # drawn from the bag, stored in state
    assert sum(s.bag.values()) == 48         # one chip removed from the bag
    assert len(s.board) == 0
    # Chaos's legal moves are placements on any empty cell.
    assert len(G.legal_moves(s)) == 49

    # --- Chaos places the stored tile; it lands as that colour -----------
    drawn = s.next_tile
    s1 = G.apply_move(s, "3,3", rng=random.Random(2))
    assert s1.board[(3, 3)] == drawn         # the STORED tile was placed
    assert s1.to_move == ORDER and s1.next_tile is None

    # --- Order slides through empties, no jumping ------------------------
    # Chip at (0,0); a blocker at (3,0) should stop horizontal slides at (2,0).
    st = EntropyState(board={(0, 0): "A", (3, 0): "B"}, to_move=ORDER)
    moves = set(G._slides(st))
    assert "0,0>1,0" in moves and "0,0>2,0" in moves
    assert "0,0>3,0" not in moves and "0,0>4,0" not in moves   # cannot jump (3,0)
    assert "pass" in G.legal_moves(st)
    # Performing a slide moves the chip and hands off to Chaos (draws next tile).
    s2 = G.apply_move(st, "0,0>2,0", rng=random.Random(3))
    assert (0, 0) not in s2.board and s2.board[(2, 0)] == "A"
    assert s2.to_move == CHAOS and s2.next_tile in COLOURS
    # Pass is a no-op slide that still hands off and draws.
    sp = G.apply_move(st, "pass", rng=random.Random(4))
    assert sp.board == st.board and sp.to_move == CHAOS and sp.next_tile in COLOURS

    # --- palindrome scoring on hand-built lines --------------------------
    # red-green-blue-green-red -> 3 + 5 = 8
    assert _palindrome_score(["A", "B", "C", "B", "A"] + [None, None]) == 8
    # red-red-red -> 2 + 2 + 3 = 7
    assert _palindrome_score(["A", "A", "A"] + [None] * 4) == 7
    # all distinct -> 0
    assert _palindrome_score(list("ABCDEFG")) == 0
    # a lone pair -> 2; lone chip -> 0
    assert _palindrome_score(["A", "A"] + [None] * 5) == 2
    assert _palindrome_score(["A"] + [None] * 6) == 0
    # full row order_score: build a board whose row 0 is A B C B A and rest distinct.
    board = {}
    row0 = ["A", "B", "C", "B", "A", "D", "E"]   # the ...ABA? tail: D E adds nothing
    for c, col in enumerate(row0):
        board[(c, 0)] = col
    # The first five cells A B C B A: palindromes are BCB(3) and ABCBA(5) = 8.
    st_score = EntropyState(board={**board,
                                   **{(c, r): COLOURS[(c + 2 * r) % 7]
                                      for c in range(N) for r in range(1, N)}})
    # Just verify row 0 contributes >= 8 (columns/other rows may add more); test the
    # raw line function for the exact 8.
    assert _palindrome_score(row0) == 8

    # --- board fills -> terminal via apply_move; winner per PAR rule -----
    s = G.initial_state(rng=random.Random(11))
    n = 0
    while not G.is_terminal(s):
        mv = random.Random(n).choice(G.legal_moves(s))
        s = G.apply_move(s, mv, rng=random.Random(n + 100))
        n += 1
        assert n < 2000
    assert len(s.board) == 49                 # board is full
    assert s.winner in (CHAOS, ORDER, "draw")
    sc = G.order_score(s)
    if sc > PAR:
        assert s.winner == ORDER
    elif sc < PAR:
        assert s.winner == CHAOS
    else:
        assert s.winner == "draw"
    # returns are zero-sum (or all-zero on a draw).
    assert sum(G.returns(s)) == 0.0

    # --- explicit winner-rule checks on hand-built full boards -----------
    # Build a full board of all distinct-per-line colours -> low score -> Chaos.
    chaos_board = {(c, r): COLOURS[(c + r) % 7] for c in range(N) for r in range(N)}
    fs = G._finish(chaos_board, _full_bag(), ply=49)
    assert G.order_score(fs) < PAR and fs.winner == CHAOS
    # Build a full board of a single colour everywhere -> huge score -> Order.
    order_board = {(c, r): "A" for c in range(N) for r in range(N)}
    fo = G._finish(order_board, _full_bag(), ply=49)
    assert G.order_score(fo) > PAR and fo.winner == ORDER

    # --- serialize round-trip (bag + next_tile) --------------------------
    s0 = G.initial_state(rng=random.Random(9))
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)
    d = G.serialize(s0)
    assert "bag" in d and "next_tile" in d and d["next_tile"] in COLOURS
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)   # terminal too

    print("entropy selftest OK")
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
