"""Kyoto Shogi correctness anchor (pure stdlib).

Anchors:
* The opening has exactly **12** legal moves -- hand-derived from the T S K G P
  back rank (Tokin/Gold 2, Silver 3, King 3, Gold 3, Pawn 1) -- and perft
  12 / 137 / 1636 (d1 hand-checked; d2/d3 frozen self-consistent counts from this
  generator).
* Each face's move from a constructed position: Tokin = Gold, Lance slides
  forward, Silver, Bishop slides diagonally, Gold, Knight leap (2 fwd + 1
  sideways), Pawn one step, Rook slides orthogonally.
* The FLIP: a piece that moves as face X ends as its paired face Y (T<->L,
  S<->B, G<->N, P<->R); the King does NOT flip.
* A drop choosing EACH face of a held pair (face-choice), and that the captured
  token banks by its pair.
* A checkmate reached via apply_move (win = checkmate).
* A serialize round-trip with a pair in hand.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.kyoto_shogi.game import KyotoShogi          # noqa: E402
from agp.shogilike import SState, BLACK, WHITE          # noqa: E402

G = KyotoShogi()


def perft(s, d):
    if d == 0:
        return 1
    if G.is_terminal(s):
        return 0
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def targets(board, sq, to_move, hands=None):
    """Bare destination squares for the piece on `sq`, via the real legal-move
    generator (so king-safety -- on the post-flip board -- is included)."""
    st = SState(board=dict(board), hands=hands or {BLACK: {}, WHITE: {}}, to_move=to_move)
    out = set()
    for m in G.legal_moves(st):
        if "@" in m:
            continue
        f, t = m.split(">")
        if f == f"{sq[0]},{sq[1]}":
            tc, tr = t.split(",")
            out.add((int(tc), int(tr)))
    return out


def main():
    s0 = G.initial_state()

    # --- opening count + frozen perft ---
    assert len(G.legal_moves(s0)) == 12, G.legal_moves(s0)
    for d, want in {1: 12, 2: 137, 3: 1636}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # --- setup: 5x5, back rank T S K G P, White a 180-degree rotation ---
    assert (G.WIDTH, G.HEIGHT) == (5, 5)
    b = s0.board
    for c, t in enumerate("TSKGP"):
        assert b[(c, 0)] == (BLACK, t), (c, b.get((c, 0)))
        assert b[(4 - c, 4)] == (WHITE, t), (c, b.get((4 - c, 4)))
    assert sum(1 for v in b.values() if v[0] == BLACK) == 5
    assert sum(1 for v in b.values() if v[0] == WHITE) == 5

    # kings used to keep test positions legal (far apart, never adjacent to action)
    K = {(0, 0): (BLACK, "K"), (4, 4): (WHITE, "K")}

    # --- each face's move from a constructed position (Black, fwd = +row) ---
    def faceset(letter, sq=(2, 2)):
        bd = dict(K); bd[sq] = (BLACK, letter)
        return targets(bd, sq, BLACK)

    # Tokin = Gold general: fwd, both fwd-diags, both sideways, straight back.
    assert faceset("T") == {(2, 3), (1, 3), (3, 3), (1, 2), (3, 2), (2, 1)}, faceset("T")
    # Gold general (the other "gold" face) -- same shape.
    assert faceset("G") == faceset("T")
    # Lance: slides straight forward to the top edge.
    assert faceset("L") == {(2, 3), (2, 4)}, faceset("L")
    # Silver: fwd + both fwd-diags + both back-diags (no sideways / straight back).
    assert faceset("S") == {(2, 3), (1, 3), (3, 3), (1, 1), (3, 1)}, faceset("S")
    # Bishop: full diagonal slider. Toward (0,0) it is blocked by its own King;
    # toward (4,4) it slides up to and may capture the enemy King.
    assert faceset("B") == {(1, 3), (0, 4), (3, 3), (4, 4), (1, 1), (3, 1), (4, 0)}, faceset("B")
    # Knight: jumps 2 forward + 1 sideways (forward only).
    assert faceset("N") == {(1, 4), (3, 4)}, faceset("N")
    # Pawn: one step straight forward.
    assert faceset("P") == {(2, 3)}, faceset("P")
    # Rook: full orthogonal slider.
    assert faceset("R") == {(2, 3), (2, 4), (2, 1), (2, 0), (1, 2), (0, 2), (3, 2), (4, 2)}, faceset("R")

    # --- THE FLIP: a moving token lands as its paired face; the King does NOT flip
    flips = {"T": "L", "L": "T", "S": "B", "B": "S",
             "G": "N", "N": "G", "P": "R", "R": "P"}
    for face, other in flips.items():
        bd = dict(K); bd[(2, 2)] = (BLACK, face)
        st = SState(board=bd, hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
        m = next(mv for mv in G.legal_moves(st) if mv.startswith("2,2>"))
        st2 = G.apply_move(st, m)
        to = tuple(int(x) for x in m.split(">")[1].split(","))
        assert st2.board[to] == (BLACK, other), (face, m, st2.board[to])
    # the King keeps its face after moving
    bd = {(2, 2): (BLACK, "K"), (4, 4): (WHITE, "K")}
    st = SState(board=bd, hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "2,2>2,3")
    assert st2.board[(2, 3)] == (BLACK, "K"), st2.board[(2, 3)]

    # --- check is evaluated on the POST-FLIP board (the timing) ---
    # A Black Silver on (2,2) moves to (3,3) AS a Silver, then flips to a Bishop.
    # The Bishop on (3,3) attacks down the long diagonal to the White King on (1,1)
    # -> check. A Silver on (3,3) would NOT reach (1,1), so the check is delivered
    # by the post-flip face, confirming the flip is on the board the opponent faces.
    bd = {(2, 2): (BLACK, "S"), (1, 1): (WHITE, "K"), (4, 4): (BLACK, "K")}
    st = SState(board=bd, hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "2,2>3,3")
    assert st2.board[(3, 3)] == (BLACK, "B")                  # flipped Silver -> Bishop
    assert G.in_check(st2.board, st2.promoted, WHITE)         # the Bishop checks
    # control: an unflipped Silver on (3,3) does NOT check the King on (1,1)
    assert not G.in_check({(3, 3): (BLACK, "S"), (1, 1): (WHITE, "K")},
                          frozenset(), WHITE)

    # --- capture banks the token by its PAIR; then it drops as EITHER face ---
    bd = dict(K); bd[(2, 2)] = (BLACK, "R"); bd[(2, 3)] = (WHITE, "S")  # Rook takes a Silver-face
    st = SState(board=bd, hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "2,2>2,3")
    assert st2.hands[BLACK] == {"S": 1}, st2.hands           # banked by pair key "S"
    assert st2.board[(2, 3)] == (BLACK, "P")                 # Rook flipped to its Pawn face
    # both faces of the held pair are offered as drops (the face-choice). Build a
    # Black-to-move position holding that captured pair:
    dst = SState(board=dict(K), hands={BLACK: {"S": 1}, WHITE: {}}, to_move=BLACK)
    drops = {m for m in G.legal_moves(dst) if "@" in m}
    assert "S@1,1" in drops and "B@1,1" in drops, drops
    # dropping the Silver face places an S and empties the hand (no flip on drop):
    st3 = G.apply_move(dst, "S@1,1")
    assert st3.board[(1, 1)] == (BLACK, "S") and st3.hands[BLACK].get("S", 0) == 0
    # dropping the Bishop face of the SAME pair instead places a B:
    st3b = G.apply_move(dst, "B@1,1")
    assert st3b.board[(1, 1)] == (BLACK, "B") and st3b.hands[BLACK].get("S", 0) == 0

    # --- a checkmate reached via apply_move (a drop-mate) ---
    # Black King in the (0,0) corner. Two White Tokin-faces (Gold move) sit on the
    # file at (0,2)/(0,3) covering the King's flight squares; White drops a third
    # Tokin onto (0,1), attacking the King with no escape. Mate.
    bd = {(0, 0): (BLACK, "K"), (0, 2): (WHITE, "T"), (0, 3): (WHITE, "T"),
          (4, 4): (WHITE, "K")}
    st = SState(board=bd, hands={WHITE: {"T": 1}, BLACK: {}}, to_move=WHITE)
    st2 = G.apply_move(st, "T@0,1")
    assert st2.board[(0, 1)] == (WHITE, "T")            # dropped showing the chosen face
    assert G.in_check(st2.board, st2.promoted, BLACK)
    assert G.is_terminal(st2) and G.legal_moves(st2) == [], G.legal_moves(st2)
    assert G.returns(st2) == [-1.0, 1.0]                # Black (to move, mated) loses

    # --- serialize round-trips through a position with a pair in hand ---
    bd = dict(K); bd[(2, 2)] = (BLACK, "T")
    st = SState(board=bd, hands={BLACK: {"P": 1}, WHITE: {}}, to_move=BLACK)
    assert G.serialize(G.deserialize(G.serialize(st))) == G.serialize(st)
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)

    print("kyoto_shogi selftest OK")


if __name__ == "__main__":
    main()
