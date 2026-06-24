"""Maharajah and the Sepoys correctness anchor (pure stdlib).

Asserts the asymmetric setup, the Amazon (Q+N) move set, the no-Sepoy-promotion
rule, both per-side royals (the Maharajah is royal; it cannot move into capture;
trapping it wins for the Sepoys), the Maharajah checkmating the Sepoy king, a
serialize round-trip, and a frozen opening-move-count regression lock.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.chesslike import CState, WHITE, BLACK, ALL8, KNIGHT  # noqa: E402
from games.maharajah.game import Maharajah  # noqa: E402

G = Maharajah()


def targets(state):
    """Set of destination cells for the side to move, ignoring promotion suffix."""
    out = set()
    for m in G.legal_moves(state):
        to = m.split("=")[0].split(">")[-1]
        out.add(tuple(int(x) for x in to.split(",")))
    return out


def main():
    s = G.initial_state()

    # --- asymmetric setup ---------------------------------------------------
    white = [(sq, t) for sq, (pl, t) in s.board.items() if pl == WHITE]
    black = [(sq, t) for sq, (pl, t) in s.board.items() if pl == BLACK]
    assert len(white) == 1, white                      # lone Maharajah
    assert white[0] == ((4, 0), "M"), white[0]         # on e1
    assert len(black) == 16, len(black)                # full Sepoy army
    assert sum(1 for _, t in black if t == "P") == 8
    assert sorted(t for _, t in black if t != "P") == sorted("RNBQKBNR")

    # Sepoys (Black) move first.
    assert s.to_move == BLACK, s.to_move
    assert G.current_player(s) == BLACK

    # --- the Amazon moves as Queen + Knight ---------------------------------
    # Lone Maharajah on an open square: its move set must equal queen ∪ knight.
    # Put the Sepoy king in a far corner so it never blocks/forbids a square that
    # the Amazon's own move geometry should reach.
    KING = (7, 7)
    st = CState(board={(3, 3): (WHITE, "M"), KING: (BLACK, "K")}, to_move=WHITE)
    # Ignore the king's own square (capturing a king is not a real move; it only
    # appears here because this stripped-down position has no White king).
    got = targets(st) - {KING}
    c0, r0 = 3, 3
    expect = set()
    for dc, dr in ALL8:                                # queen rays
        cc, rr = c0 + dc, r0 + dr
        while 0 <= cc < 8 and 0 <= rr < 8 and (cc, rr) != KING:
            expect.add((cc, rr))
            cc += dc
            rr += dr
    for dc, dr in KNIGHT:                               # knight jumps
        cc, rr = c0 + dc, r0 + dr
        if 0 <= cc < 8 and 0 <= rr < 8:
            expect.add((cc, rr))
    # The Amazon is royal, so it may not move onto a square the enemy king
    # attacks (king-adjacency). Remove those before comparing.
    expect = {sq for sq in expect
              if max(abs(sq[0] - KING[0]), abs(sq[1] - KING[1])) > 1}
    assert got == expect, (got ^ expect)

    # --- Sepoy pawns do NOT promote -----------------------------------------
    # A black pawn one step from the last rank (row 0); its forward push must be a
    # plain move with NO "=" promotion suffix, and afterward it is still a pawn.
    st = CState(board={(2, 1): (BLACK, "P"), (4, 4): (WHITE, "M")}, to_move=BLACK)
    pmoves = [m for m in G.legal_moves(st) if m.startswith("2,1>")]
    assert any(m == "2,1>2,0" for m in pmoves), pmoves
    assert all("=" not in m for m in pmoves), pmoves    # never a promotion move
    after = G.apply_move(st, "2,1>2,0")
    assert after.board[(2, 0)] == (BLACK, "P"), after.board[(2, 0)]  # stays a pawn

    # --- the Maharajah is royal: cannot move into capture -------------------
    # M on (4,4); a black rook on (4,0) controls the whole file. The M must not
    # step to any square the rook attacks along that file.
    st = CState(board={(4, 4): (WHITE, "M"), (4, 0): (BLACK, "R"),
                       (0, 7): (BLACK, "K")}, to_move=WHITE)
    dests = targets(st)
    # the M may NOT stay-on / move along the controlled file into the rook's line
    # except capturing the rook itself (4,0) which is defended? rook undefended
    # here so capture is legal; but moving to (4,1),(4,2),(4,3),(4,5)... staying on
    # the file leaves it in check -> illegal.
    for r in (1, 2, 3, 5, 6, 7):
        assert (4, r) not in dests, (4, r)
    assert (4, 0) in dests, "should be able to capture the undefended rook"

    # If the Maharajah is in check and cannot escape, the Sepoys win. Because the
    # Amazon is so mobile, trapping it takes a wall of Sepoys: M cornered at a1,
    # with every queen-ray, both knight-jumps, and a1 itself attacked (and every
    # would-be capture target defended).
    mate = CState(board={
        (0, 0): (WHITE, "M"),
        (7, 0): (BLACK, "R"), (6, 0): (BLACK, "R"),   # rank 0 (checks a1) + defence
        (0, 7): (BLACK, "R"), (0, 6): (BLACK, "R"),   # file 0 + defence
        (7, 7): (BLACK, "B"), (7, 6): (BLACK, "R"),   # a1-h8 diagonal + defence
        (1, 2): (BLACK, "N"), (2, 1): (BLACK, "N"),   # knight squares (both attack a1)
        (1, 7): (BLACK, "R"), (2, 7): (BLACK, "R"),   # defend the two knights
    }, to_move=WHITE)
    assert G.in_check(mate.board, WHITE)
    assert G.legal_moves(mate) == [], G.legal_moves(mate)
    assert G.is_terminal(mate)
    assert G.returns(mate) == [-1.0, 1.0], G.returns(mate)   # Sepoys (seat 1) win

    # --- the Maharajah checkmating the Sepoy king ---------------------------
    # A clean single-Amazon corner mate, reached via apply_move. Lone Sepoy king
    # on a8 (0,7); the Maharajah swings to b6 (1,5): from b6 it covers a8 (knight
    # jump), a7 (0,6, diagonal), b7 (1,6, file) and b8 (1,7, file), and it is a
    # knight's-distance from a8 so the king cannot capture it. Mate.
    mate2_pre = CState(board={(0, 7): (BLACK, "K"), (3, 5): (WHITE, "M")},
                       to_move=WHITE)
    s2 = G.apply_move(mate2_pre, "3,5>1,5")             # M: d6 -> b6
    assert G.in_check(s2.board, BLACK)
    assert G.legal_moves(s2) == [], G.legal_moves(s2)
    assert G.is_terminal(s2)
    assert G.returns(s2) == [1.0, -1.0], G.returns(s2)  # Maharajah (seat 0) wins

    # --- serialize round-trip ----------------------------------------------
    s0 = G.initial_state()
    d = G.serialize(s0)
    s0b = G.deserialize(d)
    assert s0b.board == s0.board and s0b.to_move == s0.to_move
    assert G.legal_moves(s0b) == G.legal_moves(s0)

    # --- opening move-count regression lock --------------------------------
    n = len(G.legal_moves(s0))
    assert n == OPENING_MOVES, f"opening move count changed: {n} != {OPENING_MOVES}"

    print(f"SELFTEST OK (opening moves = {n})")


# Frozen by computing it once below; filled in after first run.
OPENING_MOVES = 20


if __name__ == "__main__":
    main()
