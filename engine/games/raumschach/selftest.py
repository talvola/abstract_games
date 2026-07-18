"""Raumschach selftest — pure stdlib (imports only agp + this game).

Run: cd engine && PYTHONPATH=. python3 games/raumschach/selftest.py

Anchors (no engine oracle exists for Raumschach):
  (a) frozen self-perft(1..3) from the opening, with perft(1) hand-derived in
      rules.md;
  (b) exact movement-vector destination sets for each piece alone at the centre
      (pins the 3-D geometry);
  (c) rule positions: Unicorn colour-bound sub-lattice, pawn move/capture
      vectors + promotion, checkmate, stalemate;
  (d) random conformance playouts that must all terminate.
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import games.raumschach.game as R  # noqa: E402
from games.raumschach.game import Raumschach, RaumState, WHITE, BLACK  # noqa: E402

G = Raumschach()


def _state(pieces, to_move):
    s = RaumState(pieces=dict(pieces), to_move=to_move)
    s.seen = {R._pos_key(s.pieces, to_move): 1}
    return s


def _piece_dests(letter, cell=(2, 2, 2), extra=None):
    pieces = {cell: (WHITE, letter)}
    if extra:
        pieces.update(extra)
    return {(mv[3], mv[4], mv[5]) for mv in R._legal(pieces, WHITE)
            if mv[:3] == cell}


# ---------------------------------------------------------------- structure ---
def test_direction_sets():
    assert len(R.ROOK_DIRS) == 6, len(R.ROOK_DIRS)
    assert len(R.BISHOP_DIRS) == 12, len(R.BISHOP_DIRS)
    assert len(R.UNICORN_DIRS) == 8, len(R.UNICORN_DIRS)
    assert len(R.QUEEN_DIRS) == 26, len(R.QUEEN_DIRS)
    assert len(R.KNIGHT_OFFS) == 24, len(R.KNIGHT_OFFS)
    # Rook = one axis; Bishop = two axes; Unicorn = all three; each entry ±1.
    for d in R.ROOK_DIRS:
        assert sum(1 for c in d if c) == 1
    for d in R.BISHOP_DIRS:
        assert sum(1 for c in d if c) == 2 and all(abs(c) <= 1 for c in d)
    for d in R.UNICORN_DIRS:
        assert all(abs(c) == 1 for c in d)
    # Knight = one 0, the other two are 1 and 2 in magnitude.
    for d in R.KNIGHT_OFFS:
        mags = sorted(abs(c) for c in d)
        assert mags == [0, 1, 2], d
    print("test_direction_sets OK (6/12/8/26 slider dirs, 24 knight leaps)")


def test_setup():
    s = G.initial_state()
    assert len(s.pieces) == 40, len(s.pieces)
    # Kings.
    assert s.pieces[(2, 0, 0)] == (WHITE, "K")   # Kc1 (level A)
    assert s.pieces[(2, 4, 4)] == (BLACK, "K")   # Kc5 (level E)
    # White queen on level B (Bc1), unicorns on Bb1/Be1.
    assert s.pieces[(2, 0, 1)] == (WHITE, "Q")
    assert s.pieces[(1, 0, 1)] == (WHITE, "U")
    assert s.pieces[(4, 0, 1)] == (WHITE, "U")
    # Black unicorns Db5/De5.
    assert s.pieces[(1, 4, 3)] == (BLACK, "U")
    assert s.pieces[(4, 4, 3)] == (BLACK, "U")
    # Level C (z=2) empty.
    assert not any(z == 2 for (_x, _y, z) in s.pieces)
    counts = {}
    for (o, l) in s.pieces.values():
        counts[(o, l)] = counts.get((o, l), 0) + 1
    for o in (WHITE, BLACK):
        assert counts[(o, "P")] == 10
        assert counts[(o, "R")] == 2 and counts[(o, "N")] == 2
        assert counts[(o, "B")] == 2 and counts[(o, "U")] == 2
        assert counts[(o, "Q")] == 1 and counts[(o, "K")] == 1
    assert not R._in_check(s.pieces, WHITE)
    assert len(G.legal_moves(s)) == 61
    print("test_setup OK (40 pieces, level C empty, 61 opening moves)")


def test_perft():
    s = G.initial_state()
    assert R._perft(s.pieces, WHITE, 1) == 61
    assert R._perft(s.pieces, WHITE, 2) == 3608
    assert R._perft(s.pieces, WHITE, 3) == 236510
    print("test_perft OK (1=61, 2=3608, 3=236510)")


# ------------------------------------------------------ movement geometry -----
def test_centre_move_sets():
    # Exact destination COUNTS for each piece alone at the centre Cc3=(2,2,2).
    assert len(_piece_dests("R")) == 12
    assert len(_piece_dests("B")) == 24
    assert len(_piece_dests("U")) == 16
    assert len(_piece_dests("N")) == 24
    assert len(_piece_dests("Q")) == 52
    assert len(_piece_dests("K")) == 26

    # Exact SET for the Unicorn at the centre (all 16 triagonal cells).
    exp_u = set()
    for dx, dy, dz in R.UNICORN_DIRS:
        for k in (1, 2):
            exp_u.add((2 + dx * k, 2 + dy * k, 2 + dz * k))
    exp_u = {c for c in exp_u if R._inb(*c)}
    assert _piece_dests("U") == exp_u, "unicorn geometry mismatch"

    # Rook at centre = the 12 axis cells at distance 1 and 2.
    exp_r = set()
    for dx, dy, dz in R.ROOK_DIRS:
        for k in (1, 2):
            exp_r.add((2 + dx * k, 2 + dy * k, 2 + dz * k))
    assert _piece_dests("R") == exp_r

    # Knight at centre = all 24 (0,1,2)-leaps (all in bounds from the centre).
    exp_n = {(2 + dx, 2 + dy, 2 + dz) for (dx, dy, dz) in R.KNIGHT_OFFS}
    assert _piece_dests("N") == exp_n and len(exp_n) == 24

    # Queen = Rook ∪ Bishop ∪ Unicorn.
    exp_b = _piece_dests("B")
    assert _piece_dests("Q") == exp_r | exp_b | exp_u
    print("test_centre_move_sets OK (R12 B24 U16 N24 Q52 K26, exact sets)")


def test_unicorn_colourbound():
    # A Unicorn is confined to a triagonal sub-lattice: each step flips the
    # parity of all three coordinates, so it visits only two complementary
    # parity-classes. From Bb1=(1,0,1) it reaches exactly 30 of 125 cells
    # (Wikipedia's stated figure).
    def reach(start):
        seen = {start}
        frontier = [start]
        while frontier:
            nxt = []
            for (x, y, z) in frontier:
                for dx, dy, dz in R.UNICORN_DIRS:
                    sx, sy, sz = x + dx, y + dy, z + dz
                    while R._inb(sx, sy, sz):
                        if (sx, sy, sz) not in seen:
                            seen.add((sx, sy, sz))
                            nxt.append((sx, sy, sz))
                        sx, sy, sz = sx + dx, sy + dy, sz + dz
            frontier = nxt
        return seen

    r = reach((1, 0, 1))   # Bb1
    assert len(r) == 30, len(r)
    classes = {(x % 2, y % 2, z % 2) for (x, y, z) in r}
    assert len(classes) == 2, classes           # exactly two parity-classes
    # From an (even,even,even) cell it reaches 27 + 8 = 35 cells.
    assert len(reach((2, 2, 2))) == 35
    print("test_unicorn_colourbound OK (Bb1 → 30 cells, 2 parity-classes)")


# ---------------------------------------------------------------- pawns -------
def test_pawn_vectors():
    far_k = {(0, 0, 4): (WHITE, "K"), (4, 4, 0): (BLACK, "K")}
    # White pawn on Ac2 = (file c=2, rank2=1, level A=0). Enemies on every
    # candidate capture square incl. the disputed forward-up "Bc3".
    enemies = {
        (1, 2, 0): (BLACK, "P"), (3, 2, 0): (BLACK, "P"),   # Ab3, Ad3 (in-level)
        (1, 1, 1): (BLACK, "P"), (3, 1, 1): (BLACK, "P"),   # Bb2, Bd2 (side-up)
        (2, 2, 1): (BLACK, "P"),                            # Bc3 (Dickens; excl.)
    }
    pieces = {(2, 1, 0): (WHITE, "P")}
    pieces.update(far_k)
    pieces.update(enemies)
    d = {(mv[3], mv[4], mv[5]) for mv in R._legal(pieces, WHITE)
         if mv[:3] == (2, 1, 0)}
    expect = {(2, 2, 0), (2, 1, 1),                 # push forward / up
              (1, 2, 0), (3, 2, 0), (1, 1, 1), (3, 1, 1)}   # 4 captures
    assert d == expect, sorted(d)
    assert (2, 2, 1) not in d, "Bc3 forward-up capture must be excluded"

    # Black pawn mirrors: Ec4 = (2,3,4) pushes -rank/-level, captures diag down.
    bp = {(2, 3, 4): (BLACK, "P")}
    bp.update({(0, 0, 4): (WHITE, "K"), (4, 4, 0): (BLACK, "K")})
    bp.update({(1, 2, 4): (WHITE, "P"), (3, 2, 4): (WHITE, "P"),
               (1, 3, 3): (WHITE, "P"), (3, 3, 3): (WHITE, "P")})
    bd = {(mv[3], mv[4], mv[5]) for mv in R._legal(bp, BLACK)
          if mv[:3] == (2, 3, 4)}
    assert bd == {(2, 2, 4), (2, 3, 3), (1, 2, 4), (3, 2, 4),
                  (1, 3, 3), (3, 3, 3)}, sorted(bd)
    print("test_pawn_vectors OK (push fwd/up, capture in-level + side-up; "
          "forward-up excluded; Black mirrors)")


def test_no_double_step():
    s = G.initial_state()
    # The a2 pawn (level A) has ONLY a single push forward (up is blocked).
    ms = [m for m in G.legal_moves(s) if m.startswith("0,0,1>")]
    assert ms == ["0,0,1>0,0,2"], ms
    print("test_no_double_step OK")


def test_promotion():
    # White pawn one step from the far rank promotes to Q/R/B/N/U.
    pieces = {(0, 3, 0): (WHITE, "P"), (2, 0, 0): (WHITE, "K"),
              (2, 4, 4): (BLACK, "K")}
    s = _state(pieces, WHITE)
    promos = sorted(m for m in G.legal_moves(s) if m.startswith("0,0,3>0,0,4"))
    assert promos == ["0,0,3>0,0,4=B", "0,0,3>0,0,4=N", "0,0,3>0,0,4=Q",
                      "0,0,3>0,0,4=R", "0,0,3>0,0,4=U"], promos
    ns = G.apply_move(s, "0,0,3>0,0,4=U")
    assert ns.pieces[(0, 4, 0)] == (WHITE, "U")
    assert (0, 3, 0) not in ns.pieces
    print("test_promotion OK (rank 5 → Q/R/B/N/U)")


# --------------------------------------------------------- terminal states ----
def test_checkmate():
    # Legal mate-in-1 (found by exhaustive search; kings non-adjacent, the
    # side-not-to-move is not pre-checked): Black Kc... at Aa1, White K on
    # Ca1, two White rooks. Rook Ba2→Aa2 delivers mate.
    pieces = {(0, 0, 0): (BLACK, "K"), (0, 0, 2): (WHITE, "K"),
              (0, 1, 1): (WHITE, "R"), (1, 1, 0): (WHITE, "R")}
    assert not R._in_check(pieces, BLACK)      # legal position
    s = _state(pieces, WHITE)
    mv = "1,0,1>0,0,1"                          # RBa2-Aa2
    assert mv in G.legal_moves(s)
    ns = G.apply_move(s, mv)
    assert ns.winner == WHITE, (ns.winner, ns.draw)
    assert G.is_terminal(ns)
    assert G.returns(ns) == [1.0, -1.0]
    assert R._in_check(ns.pieces, BLACK) and G.legal_moves(ns) == []
    print("test_checkmate OK (White mates via apply_move)")


def test_stalemate():
    # Reach a stalemate via a White move: Black K on Aa1, White K on Ca1,
    # White Q slides to Ab3 leaving Black with no move and no check.
    pieces = {(0, 0, 0): (BLACK, "K"), (0, 0, 2): (WHITE, "K"),
              (3, 2, 0): (WHITE, "Q")}     # Q on Ad3, will slide to Ab3
    assert not R._in_check(pieces, BLACK)
    s = _state(pieces, WHITE)
    mv = "0,3,2>0,1,2"                      # QAd3-Ab3 (rook-line along the rank)
    assert mv in G.legal_moves(s), "stalemating move not legal"
    ns = G.apply_move(s, mv)
    assert ns.draw and ns.winner is None, (ns.draw, ns.winner)
    assert G.is_terminal(ns) and G.returns(ns) == [0.0, 0.0]
    assert not R._in_check(ns.pieces, BLACK)
    print("test_stalemate OK (stalemate → draw)")


def test_serialize_roundtrip():
    s = G.initial_state()
    for mv in ("1,0,1>2,0,1", "3,0,3>2,0,3"):   # Ba2→Ca2 up; Da4→Ca4 down
        s = G.apply_move(s, mv)
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert G.serialize(s2) == d
    # A piece did reach level C.
    assert any(z == 2 for (_x, _y, z) in s.pieces)
    print("test_serialize_roundtrip OK")


def test_heuristic_shape():
    s = G.initial_state()
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2
    assert abs(h[0]) <= 1.0 and h[0] == -h[1]
    print("test_heuristic_shape OK (list of 2 payoffs, bounded, zero-sum)")


def test_conformance_playouts():
    for seed in range(8):
        rng = random.Random(seed)
        s = G.initial_state()
        n = 0
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            assert ms, "non-terminal state with no legal moves"
            s = G.apply_move(s, rng.choice(ms))
            n += 1
            assert n <= R.PLY_CAP + 2, "game failed to terminate"
        r = G.returns(s)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)
    print("test_conformance_playouts OK (8 random games, all terminate)")


if __name__ == "__main__":
    test_direction_sets()
    test_setup()
    test_perft()
    test_centre_move_sets()
    test_unicorn_colourbound()
    test_pawn_vectors()
    test_no_double_step()
    test_promotion()
    test_checkmate()
    test_stalemate()
    test_serialize_roundtrip()
    test_heuristic_shape()
    test_conformance_playouts()
    print("\nALL raumschach selftests passed")
