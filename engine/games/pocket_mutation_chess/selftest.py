"""Correctness anchors for Pocket Mutation Chess (pure stdlib).

Run:  cd engine && PYTHONPATH=. python3 games/pocket_mutation_chess/selftest.py

Anchors:
  (a) perft(1)=20, perft(2)=920 from the opening (arithmetic justification below);
  (b) the CVP value-class table + every piece's movement, transcribed here as an
      INDEPENDENT oracle and cross-checked against the game's tables;
  (c) rule positions: pocketing a pinned piece / while in check is illegal, drop
      may not land on the owner's 8th rank, a mutation from each value class,
      checkmate delivered by a dropped piece, and a pocket-sensitive repetition key;
  (d) conformance: random games reach a terminal, move strings are unique, and
      states round-trip through serialize/deserialize.
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from agp.chesslike import CState

HERE = Path(__file__).resolve().parent
_man, G = load_from_dir(HERE)
from games.pocket_mutation_chess.game import CLASSES, CLASS_OF  # noqa: E402


# --- independent movement oracle (built from scratch from the CVP page) ------
ORTHO = frozenset({(1, 0), (-1, 0), (0, 1), (0, -1)})           # Rook rays / Wazir steps
DIAG = frozenset({(1, 1), (1, -1), (-1, 1), (-1, -1)})          # Bishop rays / Ferz steps
KNIGHT = frozenset({(1, 2), (2, 1), (-1, 2), (-2, 1),
                    (1, -2), (2, -1), (-1, -2), (-2, -1)})       # Knight / Nightrider steps
ALL8 = ORTHO | DIAG

# {letter: (slide-vectors, leap-vectors)} exactly as the eight classes describe.
EXPECTED_MOVE = {
    "K": (frozenset(), ALL8),
    "N": (frozenset(), KNIGHT),
    "B": (DIAG, frozenset()),
    "R": (ORTHO, frozenset()),
    "Q": (ALL8, frozenset()),
    "H": (KNIGHT, frozenset()),                 # Nightrider
    "S": (DIAG, ORTHO),                         # SuperBishop  = Bishop + Wazir
    "C": (DIAG, KNIGHT),                        # Cardinal     = Bishop + Knight
    "T": (ORTHO, DIAG),                         # SuperRook    = Rook + Ferz
    "M": (ORTHO, KNIGHT),                       # Chancellor   = Rook + Knight
    "D": (DIAG | KNIGHT, frozenset()),          # CardinalRider = Bishop + Nightrider
    "E": (DIAG, KNIGHT | ORTHO),                # SuperCardinal = Bishop + Knight + Wazir
    "G": (ORTHO | KNIGHT, frozenset()),         # ChancellorRider = Rook + Nightrider
    "J": (ORTHO, KNIGHT | DIAG),                # SuperChancellor = Rook + Knight + Ferz
    "L": (DIAG | KNIGHT, ORTHO),                # SuperCardinalRider = Bishop + Nightrider + Wazir
    "A": (ALL8, KNIGHT),                        # Amazon       = Queen + Knight
    "U": (ORTHO | KNIGHT, DIAG),                # SuperChancellorRider = Rook + Nightrider + Ferz
    "Z": (ALL8 | KNIGHT, frozenset()),          # AmazonRider  = Queen + Nightrider
}

# The eight value classes, transcribed from the CVP page (class N = index N-1).
EXPECTED_CLASSES = [
    ["P"],
    ["N", "B"],
    ["R", "H", "S"],
    ["C", "T"],
    ["Q", "M", "D", "E"],
    ["G", "J", "L"],
    ["A", "U"],
    ["Z"],
]


def test_tables():
    assert CLASSES == EXPECTED_CLASSES, ("class table mismatch", CLASSES)
    # every non-pawn class member has a movement entry, matching the oracle
    for cls in EXPECTED_CLASSES:
        for L in cls:
            if L == "P":
                continue
            slides, leaps = G.PIECES[L]
            assert (frozenset(slides), frozenset(leaps)) == EXPECTED_MOVE[L], \
                ("movement mismatch", L, slides, leaps)
    # CLASS_OF is consistent
    for i, cls in enumerate(EXPECTED_CLASSES):
        for L in cls:
            assert CLASS_OF[L] == i, ("CLASS_OF", L)
    print("tables (value classes + movement) OK")


def _perft(state, depth):
    if depth == 0:
        return 1
    return sum(_perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


def test_perft():
    s = G.initial_state()
    # perft(1): White may not pocket on move 1 and has no drops, so it is exactly
    # the 20 ordinary FIDE opening moves (16 pawn + 4 knight); no castling/promotion.
    assert _perft(s, 1) == 20, _perft(s, 1)
    # perft(2): every one of White's 20 first moves leaves Black with its usual 20
    # ordinary replies (chess perft(2)=400) PLUS 26 pocketing moves -- Black may
    # pocket on its first move. The 26: 8 pawns x1 + 2 knights x2 + 2 bishops x2
    # (class 2 = {N,B}) + 2 rooks x3 (class 3 = {R,H,S}) + 1 queen x4
    # (class 5 = {Q,M,D,E}) = 8+4+4+6+4 = 26. So 400 + 20*26 = 920.
    assert _perft(s, 2) == 920, _perft(s, 2)
    print("perft(1)=20, perft(2)=920 OK")


def _st(board, to_move=0, ply=2, hands=None):
    return CState(board=dict(board), to_move=to_move, ply=ply,
                  hands=hands if hands is not None else {0: {}, 1: {}})


def test_rule_positions():
    # (1) A pinned piece may not be pocketed (removing it exposes the king), but
    #     it may still move along the pin line.
    s = _st({(4, 0): (0, "K"), (4, 1): (0, "R"),
             (4, 7): (1, "R"), (7, 7): (1, "K")})
    lm = G.legal_moves(s)
    assert not any(m.startswith("4,1>4,1=") for m in lm), "pinned rook pocketed!"
    assert "4,1>4,6" in lm, "pinned rook cannot slide on the pin line"

    # (2) While in check, no pocketing move is legal (removing a piece never
    #     resolves a check).
    s = _st({(4, 0): (0, "K"), (2, 0): (0, "B"),
             (4, 7): (1, "R"), (7, 7): (1, "K")})
    assert G.in_check(s.board, 0)
    assert not any("=" in m for m in G.legal_moves(s)), "pocketed while in check!"

    # (3) A drop may not land on the owner's 8th rank (White = row 7).
    s = _st({(4, 0): (0, "K"), (7, 7): (1, "K")}, hands={0: {"Q": 1}, 1: {}})
    drops = [m for m in G.legal_moves(s) if "@" in m]
    assert drops and not any(m.endswith(",7") for m in drops), "drop on 8th rank"

    # (4) Mutation options == the value class (mid-board) / next class (own 8th).
    for i, cls in enumerate(EXPECTED_CLASSES):
        piece = cls[0]
        mid = _st({(0, 0): (0, "K"), (7, 0): (1, "K"), (3, 3): (0, piece)})
        got = sorted(m.split("=")[1] for m in G.legal_moves(mid)
                     if m.startswith("3,3>3,3="))
        assert got == sorted(cls), ("mid-rank class", i + 1, got)
        top = _st({(0, 0): (0, "K"), (7, 0): (1, "K"), (3, 7): (0, piece)})
        got = sorted(m.split("=")[1] for m in G.legal_moves(top)
                     if m.startswith("3,7>3,7="))
        nxt = EXPECTED_CLASSES[min(i + 1, len(EXPECTED_CLASSES) - 1)]
        assert got == sorted(nxt), ("8th-rank class", i + 1, got)

    # (5) Checkmate delivered by a dropped piece: Wk c1, Bk a1, drop Q@a3 mates.
    s = _st({(2, 0): (0, "K"), (0, 0): (1, "K")}, hands={0: {"Q": 1}, 1: {}})
    assert "Q@0,2" in G.legal_moves(s)
    s2 = G.apply_move(s, "Q@0,2")
    assert G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0], "drop-mate failed"

    # (6) The repetition key distinguishes pocket contents (same board, diff pocket).
    b = {(0, 0): (0, "K"), (7, 7): (1, "K")}
    a = _st(b, hands={0: {}, 1: {}})
    c = _st(b, hands={0: {"Q": 1}, 1: {}})
    assert G._poskey_state(a) != G._poskey_state(c), "pocket absent from rep key"
    print("rule positions (pin/check/drop/mutation/mate/repetition) OK")


def test_conformance():
    rng = random.Random(2003)
    reached = 0
    for _ in range(30):
        s = G.initial_state()
        for _ in range(200):
            if G.is_terminal(s):
                reached += 1
                break
            mv = G.legal_moves(s)
            assert mv, "no legal moves on a non-terminal state"
            assert len(mv) == len(set(mv)), "duplicate move strings"
            # serialize round-trips
            d = G.serialize(s)
            assert G.serialize(G.deserialize(d)) == d, "serialize round-trip"
            s = G.apply_move(s, rng.choice(mv))
    assert reached >= 1, "no random game reached a terminal"
    print(f"conformance OK ({reached}/30 random games terminated within 200 plies)")


if __name__ == "__main__":
    test_tables()
    test_perft()
    test_rule_positions()
    test_conformance()
    print("all pocket_mutation_chess selftests passed")
