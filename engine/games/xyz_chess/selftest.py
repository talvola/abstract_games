"""3D XYZ Chess selftest — pure stdlib (imports only agp + this game).

Run: cd engine && PYTHONPATH=. python3 games/xyz_chess/selftest.py

Anchors:
  (a) GOLD: the full 22-move annotated Hewson-Mandoshkin game from Abstract
      Games issue 24 (pp. 32-34) replays move for move — every printed move
      legal, every printed check ("+") and only those reproduced, spot
      positions matching the magazine diagrams, and the final move a
      checkmate won by Black.  The replay exercises all six piece types,
      three edge-pawn DOUBLE-STEP CAPTURES, and a mate whose net depends on
      a double-step guard.
  (b) piece-geometry figures stated in the article: Rook max 9 squares from
      the centre, Bishop max 15, Knight 8; Knight confined to a 16-cell
      quarter, the four knights' quarters disjoint and covering the board.
  (c) hand-derived perft(1) = 27 from the setup + frozen self-perft(2..3).
  (d) rule positions: edge-pawn double-step conditions, automatic Queen
      promotion, stalemate = draw, threefold repetition, termination
      playouts.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import games.xyz_chess.game as X  # noqa: E402
from games.xyz_chess.game import XyzChess, XyzState, WHITE, BLACK  # noqa: E402

G = XyzChess()


def _state(pieces, to_move):
    s = XyzState(pieces=dict(pieces), to_move=to_move)
    s.seen = {X._pos_key(s.pieces, to_move): 1}
    return s


def _dests(pieces, cell):
    return {(mv[3], mv[4], mv[5]) for mv in X._legal(pieces, pieces[cell][0])
            if mv[:3] == cell}


def _cid(sq):
    """'c2B' -> module cell id 'z,x,y'."""
    x = "abcd".index(sq[0])
    y = int(sq[1]) - 1
    z = "ABCD".index(sq[2])
    return f"{z},{x},{y}"


def _mv(frm, to):
    return f"{_cid(frm)}>{_cid(to)}"


# ---------------------------------------------------------------- structure ---
def test_direction_sets():
    assert len(X.ORTHO_DIRS) == 6
    assert len(X.PLANAR_DIRS) == 12
    assert len(X.QUEEN_DIRS) == 18          # NO triagonal for the Queen
    assert len(X.TRIAGONAL) == 8
    for d in X.PLANAR_DIRS:
        assert sum(1 for c in d if c) == 2 and all(abs(c) <= 1 for c in d)
    for d in X.TRIAGONAL:
        assert all(abs(c) == 1 for c in d)
    print("test_direction_sets OK (6 ortho / 12 planar / 18 queen / 8 triagonal)")


def test_setup():
    s = G.initial_state()
    assert len(s.pieces) == 32
    from collections import Counter
    for side in (WHITE, BLACK):
        c = Counter(l for (o, l) in s.pieces.values() if o == side)
        assert c == {"P": 8, "R": 2, "N": 2, "B": 2, "Q": 1, "K": 1}, c
    # Mirror symmetry: Black = White mapped (x,y)->(3-x,3-y), same level.
    for (x, y, z), (o, l) in s.pieces.items():
        assert s.pieces[(3 - x, 3 - y, z)] == (1 - o, l)
    # Article-named squares (each verified by its first move in the game).
    for sq, owner, letter in [
        ("a1A", WHITE, "N"), ("b1A", WHITE, "R"), ("a1B", WHITE, "K"),
        ("a2B", WHITE, "B"), ("a1C", WHITE, "Q"), ("b1C", WHITE, "N"),
        ("a1D", WHITE, "B"), ("a2D", WHITE, "R"), ("a2C", WHITE, "P"),
        ("d4A", BLACK, "N"), ("c4A", BLACK, "R"), ("d4B", BLACK, "K"),
        ("d3B", BLACK, "B"), ("d4C", BLACK, "Q"), ("c4C", BLACK, "N"),
        ("d4D", BLACK, "B"), ("d3D", BLACK, "R"), ("d3C", BLACK, "P"),
    ]:
        assert s.pieces[X._parse(_cid(sq))] == (owner, letter), sq
    print("test_setup OK (32 pieces, 2x2x4 corner blocks, mirror symmetry)")


# ----------------------------------------------------- article piece figures --
def test_piece_geometry():
    centre = (1, 1, 1)  # b2B
    for letter, want in (("R", 9), ("B", 15), ("N", 8), ("K", 6), ("Q", 24)):
        pieces = {centre: (WHITE, letter), (3, 0, 3): (WHITE, "K")}
        if letter == "K":
            pieces = {centre: (WHITE, letter)}
        d = _dests(pieces, centre)
        assert len(d) == want, (letter, len(d))
    # Article: "the Rook can move to a maximum of nine spaces from the centre
    # of the board, whereas the Bishop can move to a maximum of 15."
    # King strictly orthogonal: no diagonal one-steps.
    d = _dests({centre: (WHITE, "K")}, centre)
    assert (2, 2, 1) not in d and (0, 0, 0) not in d and (2, 1, 1) in d
    # Knight must change level: all destinations differ in z.
    d = _dests({centre: (WHITE, "N"), (3, 0, 3): (WHITE, "K")}, centre)
    assert all(dz != 1 for (_, _, dz) in d)
    print("test_piece_geometry OK (R 9 / B 15 / N 8 / K 6 ortho / Q 24)")


def test_knight_quarters():
    # A knight's reachable closure is a 16-cell quarter (parities of x+y and
    # y+z are invariant); the four starting knights' quarters are disjoint
    # and together cover all 64 cells -> opposing knights can never meet.
    def closure(start):
        seen, todo = {start}, [start]
        while todo:
            x, y, z = todo.pop()
            for dx, dy, dz in X.TRIAGONAL:
                n = (x + dx, y + dy, z + dz)
                if X._inb(*n) and n not in seen:
                    seen.add(n)
                    todo.append(n)
        return seen
    starts = [(0, 0, 0), (1, 0, 2), (3, 3, 0), (2, 3, 2)]  # Na1A Nb1C Nd4A Nc4C
    quarters = [closure(st) for st in starts]
    assert all(len(q) == 16 for q in quarters)
    union = set().union(*quarters)
    assert len(union) == 64
    print("test_knight_quarters OK (4 disjoint 16-cell quarters cover the cube)")


# -------------------------------------------------------------------- perft ---
def test_perft():
    s = G.initial_state()
    # perft(1) = 27 hand-derived in the port notes: R b1A 2 (c1A,d1A);
    # B a2B 5 (b3B, xc4B, a3C, a4D, a3A); N b1C 2 (c2D,c2B); R a2D 2
    # (a3D,a4D); pawns: a2A 2 (a3A + double a4A), b2A 2, b1B 2 (c1B + double
    # d1B), b2B 2, a2C 2 (a3C + double a4C), b2C 2, b1D 2 (c1D + double d1D),
    # b2D 2; N a1A, K, Q, B a1D all buried = 0.
    assert X._perft(s.pieces, WHITE, 1) == 27
    # Frozen self-values (regression guard).
    assert X._perft(s.pieces, WHITE, 2) == 729
    assert X._perft(s.pieces, WHITE, 3) == 22651
    print("test_perft OK (27 / 729 / 22651)")


# ---------------------------------------------------------------- pawn rules --
def test_pawn_rules():
    K = {(3, 0, 3): (WHITE, "K"), (0, 3, 0): (BLACK, "K")}  # far-off kings
    # Plain pawn: two forward dirs, no double (not an edge start).
    p = dict(K); p[(1, 1, 1)] = (WHITE, "P")                    # b2B
    assert _dests(p, (1, 1, 1)) == {(2, 1, 1), (1, 2, 1)}
    # Edge pawn on its start: single + double both directions.
    p = dict(K); p[(0, 1, 2)] = (WHITE, "P")                    # a2C
    assert _dests(p, (0, 1, 2)) == {(1, 1, 2), (0, 2, 2), (2, 1, 2), (0, 3, 2)}
    # Double blocked by an occupied FIRST space (even by an enemy).
    p[(0, 2, 2)] = (BLACK, "N")
    assert _dests(p, (0, 1, 2)) == {(1, 1, 2), (0, 2, 2), (2, 1, 2)}
    # Double-step CAPTURE on the destination (the anchor game plays three).
    del p[(0, 2, 2)]
    p[(0, 3, 2)] = (BLACK, "N")
    assert (0, 3, 2) in _dests(p, (0, 1, 2))
    # A BLACK pawn standing on a WHITE edge start gets no double.
    p = dict(K); p[(1, 0, 1)] = (BLACK, "P")                    # b1B
    assert _dests(p, (1, 0, 1)) == {(0, 0, 1)}
    # Pawns never change level and never move sideways/backwards.
    p = dict(K); p[(2, 2, 2)] = (BLACK, "P")
    assert _dests(p, (2, 2, 2)) == {(1, 2, 2), (2, 1, 2)}
    print("test_pawn_rules OK (dirs, edge double-step, double capture, block)")


def test_promotion():
    # White pawn promotes to Queen (automatically) at d4 of ITS level.
    pieces = {(3, 0, 3): (WHITE, "K"), (0, 3, 0): (BLACK, "K"),
              (2, 3, 1): (WHITE, "P")}                          # c4B
    s = _state(pieces, WHITE)
    ns = G.apply_move(s, _mv("c4B", "d4B"))
    assert ns.pieces[(3, 3, 1)] == (WHITE, "Q")
    # ... and via capture; Black promotes at a1.
    pieces = {(3, 0, 3): (WHITE, "K"), (2, 3, 0): (BLACK, "K"),
              (0, 1, 2): (BLACK, "P"), (0, 0, 2): (WHITE, "R")}  # a2C, a1C
    s = _state(pieces, BLACK)
    ns = G.apply_move(s, _mv("a2C", "a1C"))
    assert ns.pieces[(0, 0, 2)] == (BLACK, "Q")
    print("test_promotion OK (automatic Queen at the level's far corner)")


# ------------------------------------------------------------- terminations --
def test_stalemate_draw():
    # Black: bare K a1A.  White Qc2B-c1B covers b1A (planar diag) + a1B
    # (ortho line); R a2D covers a2A down the level-column; a1A itself stays
    # unattacked -> stalemate, an honest draw.
    pieces = {(0, 0, 0): (BLACK, "K"), (2, 1, 1): (WHITE, "Q"),
              (0, 1, 3): (WHITE, "R"), (3, 0, 3): (WHITE, "K")}
    s = _state(pieces, WHITE)
    ns = G.apply_move(s, _mv("c2B", "c1B"))
    assert ns.draw and ns.winner is None
    assert G.is_terminal(ns) and G.returns(ns) == [0.0, 0.0]
    print("test_stalemate_draw OK")


def test_threefold_repetition():
    pieces = {(0, 0, 0): (WHITE, "K"), (3, 3, 3): (BLACK, "K"),
              (3, 0, 0): (WHITE, "R"), (0, 3, 3): (BLACK, "R")}
    s = _state(pieces, WHITE)
    shuffle = [_mv("a1A", "b1A"), _mv("d4D", "c4D"),
               _mv("b1A", "a1A"), _mv("c4D", "d4D")]
    n = 0
    while not G.is_terminal(s):
        s = G.apply_move(s, shuffle[n % 4])
        n += 1
        assert n <= 12
    assert s.draw and s.winner is None
    print(f"test_threefold_repetition OK (draw after {n} plies)")


def test_random_playouts_terminate():
    rng = random.Random(20260719)
    results = {"W": 0, "B": 0, "D": 0}
    for _ in range(25):
        s = G.initial_state()
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            assert s.ply <= X.PLY_CAP
        r = G.returns(s)
        results["W" if r[0] > 0 else "B" if r[1] > 0 else "D"] += 1
    print(f"test_random_playouts_terminate OK {results}")


# ------------------------------------------------- GOLD: the annotated game ---
# Rick Hewson (White) vs Jake Mandoshkin (Black), March 28 2022, AG24 pp.32-34.
# (move, flag) with flag "" none, "+" check, "#" mate.  1...Pd3-d2C is printed
# without a level letter; pawns cannot change level, so the source is d3C.
GAME = [
    ("Rb1A-c1A", ""), ("Pd3C-d2C", ""),
    ("Pa2C-a4C", ""), ("Bd3B-d2A", ""),        # W edge-pawn double-step
    ("Rc1A-c1B", ""), ("Rd3D-d3B", ""),
    ("Ba2B-a3C", ""), ("Nc4C-d3D", ""),
    ("Pa4C-b4C", ""), ("Rc4A-b4A", ""),
    ("Pb2B-b3B", ""), ("Pc3B-c2B", ""),
    ("Nb1CxPc2B", ""), ("Pc4BxNc2B", ""),      # B edge-pawn DOUBLE-STEP x
    ("Rc1B-d1B", ""), ("Bd2AxRd1B", ""),
    ("Pb1BxBd1B", ""), ("Rd3BxPd1B", "+"),     # W edge-pawn DOUBLE-STEP x
    ("Ka1B-a2B", ""), ("Rb4AxPb4C", ""),
    ("Ba1D-a3B", ""), ("Pc3C-b3C", ""),
    ("Ba3C-a4B", ""), ("Qd4C-c4B", ""),
    ("Ba4B-a3A", ""), ("Bd4D-b4B", ""),
    ("Na1A-b2B", ""), ("Pc3A-b3A", ""),
    ("Nb2B-c3C", "+"), ("Kd4B-d3B", ""),
    ("Pb2AxPb3A", ""), ("Pd3AxPb3A", ""),      # B edge-pawn DOUBLE-STEP x
    ("Nc3CxBb4B", ""), ("Pb3AxBa3A", ""),
    ("Ka2B-a2C", ""), ("Pb3CxPb2C", "+"),
    ("Ka2C-a3C", ""), ("Qc4BxPb3B", "+"),
    ("Ka3C-a3D", ""), ("Qb3BxBa3B", "+"),
    ("Qa1C-a3C", ""), ("Qa3B-c3B", "+"),
    ("Qa3C-b3C", ""), ("Qc3BxQb3C", "#"),
]


def _game_move(txt):
    """'Nb1CxPc2B' / 'Rb1A-c1A' -> engine move string."""
    body = txt[1:]
    sep = "x" if "x" in body else "-"
    frm, to = body.split(sep)
    if sep == "x":
        to = to[1:]  # strip the captured piece's letter
    return _mv(frm, to), txt[0], frm, to, sep == "x"


# Magazine diagram spot-checks: (halfmove index just played, square, owner,
# letter) — positions the printed diagrams display.
DIAGRAM_SPOTS = {
    8:  [("d3D", BLACK, "N"), ("d2A", BLACK, "B"), ("a3C", WHITE, "B")],  # D2
    20: [("b4C", BLACK, "R"), ("a2B", WHITE, "K"), ("d1B", BLACK, "R")],  # D5
    40: [("a3B", BLACK, "Q"), ("a3D", WHITE, "K")],                       # D10
}


def test_annotated_game():
    s = G.initial_state()
    doubles = 0
    for i, (txt, flag) in enumerate(GAME):
        mover = s.to_move
        assert mover == (WHITE if i % 2 == 0 else BLACK)
        move, letter, frm, to, is_cap = _game_move(txt)
        # The printed piece letter matches the piece on the from-square.
        fx, fy, fz = X._parse(_cid(frm))
        assert s.pieces[(fx, fy, fz)] == (mover, letter), (i, txt)
        legal = G.legal_moves(s)
        assert move in legal, (i, txt, move)
        tx, ty, tz = X._parse(_cid(to))
        assert (((tx, ty, tz) in s.pieces) == is_cap), (i, txt)
        if letter == "P" and abs(tx - fx) + abs(ty - fy) == 2:
            doubles += 1 if not is_cap else 10
        s = G.apply_move(s, move)
        in_chk = X._in_check(s.pieces, s.to_move)
        if flag == "#":
            assert s.winner == mover, (i, txt)
        else:
            assert not G.is_terminal(s), (i, txt)
            assert in_chk == (flag == "+"), (i, txt, in_chk)
        for sq, owner, l in DIAGRAM_SPOTS.get(i + 1, []):
            assert s.pieces[X._parse(_cid(sq))] == (owner, l), (i, sq)
    assert s.winner == BLACK and G.returns(s) == [-1.0, 1.0]
    # Exactly 3 double-step pawn CAPTURES (weight 10) + 1 plain double-step
    # (2.Pa2C-a4C) occurred.
    assert doubles == 31, doubles
    # The mate depends on the c4D edge pawn guarding a4D via its double-step.
    assert X._attacked(s.pieces, 0, 3, 3, BLACK)
    del s.pieces[(2, 3, 3)]  # remove that pawn -> a4D is a flight square
    assert not X._attacked(s.pieces, 0, 3, 3, BLACK)
    print("test_annotated_game OK (44 halfmoves, 6 checks + mate, "
          "3 double-step captures, diagrams consistent, Black wins)")


def test_describe_move():
    s = G.initial_state()
    assert G.describe_move(s, _mv("b1A", "c1A")) == "Rb1A-c1A"
    s2 = G.apply_move(s, _mv("b1A", "c1A"))
    assert G.describe_move(s2, _mv("d3C", "d2C")) == "Pd3C-d2C"
    print("test_describe_move OK (magazine notation)")


def main():
    test_direction_sets()
    test_setup()
    test_piece_geometry()
    test_knight_quarters()
    test_perft()
    test_pawn_rules()
    test_promotion()
    test_stalemate_draw()
    test_threefold_repetition()
    test_annotated_game()
    test_describe_move()
    test_random_playouts_terminate()
    print("xyz_chess selftest: all tests passed")


if __name__ == "__main__":
    main()
