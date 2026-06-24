"""Dobutsu Shogi correctness anchor (pure stdlib).

Anchors:
* The opening has exactly **4** legal moves (hand-derived: Lion to either empty
  flank, Giraffe up, Chick captures the facing Chick) -- and perft 4/13/67/398
  (d1 hand-checked = 4; d2 = 13 hand-checked by enumerating White's replies to all
  four openings; the rest are frozen self-consistent counts from this verified
  generator).
* Each animal's move from a constructed position (Giraffe orthogonal, Elephant
  diagonal, Chick forward + promotion to Hen, Hen = gold-general 6 directions).
* A drop from the reserve.
* Both win conditions reached via apply_move: the **Catch** (capturing the enemy
  Lion) and the **Try** (a Lion safely reaching the enemy home rank).
* A serialize round-trip with pieces in hand.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.dobutsu.game import Dobutsu                 # noqa: E402
from agp.shogilike import SState, BLACK, WHITE          # noqa: E402

G = Dobutsu()


def perft(s, d):
    if d == 0:
        return 1
    if G.is_terminal(s):
        return 0
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def targets(board, sq, to_move):
    """Bare destination squares for the piece on `sq` (ignores nothing -- uses the
    real legal-move generator so king-safety is included)."""
    st = SState(board=dict(board), hands={BLACK: {}, WHITE: {}}, to_move=to_move)
    fc, fr = sq
    out = set()
    for m in G.legal_moves(st):
        if "@" in m:
            continue
        raw = m[:-2] if m.endswith("=+") else m
        f, t = raw.split(">")
        if f == f"{fc},{fr}":
            tc, tr = t.split(",")
            out.add((int(tc), int(tr)))
    return out


def main():
    s0 = G.initial_state()

    # --- opening count + frozen perft ---
    assert len(G.legal_moves(s0)) == 4, G.legal_moves(s0)
    for d, want in {1: 4, 2: 13, 3: 67, 4: 398}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # --- setup: 3x4, Elephant-left / Lion-centre / Giraffe-right per player ---
    assert (G.WIDTH, G.HEIGHT) == (3, 4)
    b = s0.board
    assert b[(0, 0)] == (BLACK, "E") and b[(1, 0)] == (BLACK, "L") and b[(2, 0)] == (BLACK, "G")
    assert b[(1, 1)] == (BLACK, "C")
    assert b[(0, 3)] == (WHITE, "G") and b[(1, 3)] == (WHITE, "L") and b[(2, 3)] == (WHITE, "E")
    assert b[(1, 2)] == (WHITE, "C")

    # --- Giraffe: one square orthogonally (4 dirs) ---
    kings = {(0, 0): (BLACK, "L"), (0, 3): (WHITE, "L")}
    bd = dict(kings); bd[(1, 1)] = (BLACK, "G")
    assert targets(bd, (1, 1), BLACK) == {(0, 1), (2, 1), (1, 0), (1, 2)}

    # --- Elephant: one square diagonally (4 dirs) ---
    bd = dict(kings); bd[(1, 1)] = (BLACK, "E")
    assert targets(bd, (1, 1), BLACK) == {(0, 0), (2, 0), (0, 2), (2, 2)} - set(kings)
    # (0,0) holds the Black king, so it is not a legal Elephant target:
    assert targets(bd, (1, 1), BLACK) == {(2, 0), (0, 2), (2, 2)}

    # --- Chick: one square forward only ---
    bd = dict(kings); bd[(1, 1)] = (BLACK, "C")
    assert targets(bd, (1, 1), BLACK) == {(1, 2)}

    # --- Chick promotes to Hen on the far rank (mandatory) ---
    bd = {(0, 0): (BLACK, "L"), (2, 2): (WHITE, "L"), (1, 2): (BLACK, "C")}
    st = SState(board=bd, hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    pm = [m for m in G.legal_moves(st) if m.startswith("1,2>")]
    assert pm == ["1,2>1,3=+"], pm
    st2 = G.apply_move(st, "1,2>1,3=+")
    assert (1, 3) in st2.promoted and st2.board[(1, 3)] == (BLACK, "C")

    # --- Hen moves as a gold general: 6 dirs (no backward diagonals) ---
    bd = {(0, 0): (BLACK, "L"), (0, 3): (WHITE, "L"), (1, 1): (BLACK, "C")}
    st = SState(board=bd, promoted=frozenset({(1, 1)}),
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    hen = targets({k: v for k, v in bd.items()}, (1, 1), BLACK)
    # recompute with promoted flag honoured:
    out = set()
    for m in G.legal_moves(st):
        if m.startswith("1,1>"):
            t = m.split(">")[1]
            tc, tr = t.split(","); out.add((int(tc), int(tr)))
    # gold from (1,1) Black (fwd +): fwd (1,2); fwd-diags (0,2),(2,2);
    # sideways (0,1),(2,1); straight back (1,0). NOT (0,0)/(2,0) backward diags.
    assert out == {(1, 2), (0, 2), (2, 2), (0, 1), (2, 1), (1, 0)}, out

    # --- a drop from the reserve places an empty-square animal ---
    bd = {(0, 0): (BLACK, "L"), (2, 3): (WHITE, "L")}
    st = SState(board=bd, hands={BLACK: {"G": 1}, WHITE: {}}, to_move=BLACK)
    assert "G@1,1" in G.legal_moves(st)
    st2 = G.apply_move(st, "G@1,1")
    assert st2.board[(1, 1)] == (BLACK, "G") and st2.hands[BLACK].get("G", 0) == 0

    # --- Catch win: capturing the enemy Lion ends the game (Black wins) ---
    bd = {(1, 1): (BLACK, "G"), (1, 2): (WHITE, "L"), (0, 0): (BLACK, "L")}
    st = SState(board=bd, hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "1,1>1,2")            # Giraffe captures the White Lion
    assert G.is_terminal(st2)
    assert G.returns(st2) == [1.0, -1.0]
    assert G.legal_moves(st2) == []

    # --- Try win: Black Lion safely reaches White's home rank (row 3) ---
    bd = {(1, 2): (BLACK, "L"), (0, 1): (WHITE, "L")}
    st = SState(board=bd, hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "1,2>1,3")            # Lion onto the far rank
    assert G.is_terminal(st2) and G.returns(st2) == [1.0, -1.0]
    # White Try mirrors (Lion onto row 0):
    bd = {(1, 1): (WHITE, "L"), (2, 2): (BLACK, "L")}
    st = SState(board=bd, hands={BLACK: {}, WHITE: {}}, to_move=WHITE)
    st2 = G.apply_move(st, "1,1>1,0")
    assert G.is_terminal(st2) and G.returns(st2) == [-1.0, 1.0]

    # --- serialize round-trips through a position with a piece in hand ---
    bd = {(0, 0): (BLACK, "L"), (2, 3): (WHITE, "L")}
    st = SState(board=bd, hands={BLACK: {"C": 1}, WHITE: {}}, to_move=BLACK)
    assert G.serialize(G.deserialize(G.serialize(st))) == G.serialize(st)
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)

    print("dobutsu selftest OK")


if __name__ == "__main__":
    main()
