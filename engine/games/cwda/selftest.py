"""Self-test for Chess with Different Armies (pure stdlib).

Anchors:
  (a) opening perft(1..2) for each army-as-White and the FIDE-vs-Clobberers
      default (perft(1) is hand-justified piece-by-piece in the report / rules);
  (b) exact destination sets from a centre square for every non-FIDE piece --
      both colours for the direction-dependent Nutty-Knights pieces;
  (c) rule positions: castling per army (incl. the colourbound flip), pawn
      promotion to either army's pieces, and a fairy-piece checkmate;
  (d) random conformance playouts for several army pairings.

Run:  cd engine && PYTHONPATH=. python3 games/cwda/selftest.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir           # noqa: E402
from agp.chesslike import WHITE, BLACK          # noqa: E402

_, GAME = load_from_dir(Path(__file__).resolve().parent)


# --------------------------------------------------------------------------- #
def perft(state, depth):
    if depth == 0:
        return 1
    n = 0
    for mv in GAME.legal_moves(state):
        n += perft(GAME.apply_move(state, mv), depth - 1)
    return n


def start(white, black):
    return GAME.initial_state({"white_army": white, "black_army": black})


def test_perft():
    # perft(1) depends only on White's army (no piece contact at ply 0).
    expect1 = {"fide": 20, "clobberers": 28, "rookies": 24, "knights": 26}
    for army, n in expect1.items():
        got = perft(start(army, army), 1)
        assert got == n, f"perft(1) {army} mirror: {got} != {n}"
    # FIDE-vs-Clobberers default: White=FIDE -> 20.
    assert perft(start("fide", "clobberers"), 1) == 20

    # perft(2) -- machine-computed and frozen (self-consistent regression guard).
    expect2 = {
        "fide": 400,          # 20*20 orthodox
        "clobberers": 784,
        "rookies": 576,
        "knights": 676,
    }
    for army, n in expect2.items():
        got = perft(start(army, army), 2)
        assert got == n, f"perft(2) {army} mirror: {got} != {n}"
    # default mixed game perft(2).
    assert perft(start("fide", "clobberers"), 2) == 560
    print("  perft OK  perft1", expect1, " perft2", expect2, " default2=560")


# --------------------------------------------------------------------------- #
def dests(t, player, at=(4, 4)):
    """Destination OFFSETS for a single piece of `t`/`player` alone on the board
    (empty board -> raw geometry, no king-safety / king-capture artefacts)."""
    c, r = at
    board = {(c, r): (player, t)}
    outs = set()
    if t in ("S", "G", "J", "C"):
        for to in GAME._custom_targets(board, c, r, player, t):
            outs.add((to[0] - c, to[1] - r))
        return outs
    slides, leaps = GAME.PIECES[t]
    for dc, dr in leaps:
        if GAME.on(c + dc, r + dr):
            outs.add((dc, dr))
    for dc, dr in slides:
        cc, rr = c + dc, r + dr
        while GAME.on(cc, rr):
            outs.add((cc - c, rr - r))
            cc += dc
            rr += dr
    return outs


def test_movement():
    # --- pure leapers: exact offset equality ---
    assert dests("W", WHITE) == {(1, 0), (-1, 0), (0, 1), (0, -1),
                                 (2, 2), (2, -2), (-2, 2), (-2, -2)}          # Waffle WA
    assert dests("F", WHITE) == {(1, 1), (1, -1), (-1, 1), (-1, -1),
                                 (2, 2), (2, -2), (-2, 2), (-2, -2),
                                 (2, 0), (-2, 0), (0, 2), (0, -2)}            # FAD
    assert dests("O", WHITE) == {(1, 0), (-1, 0), (0, 1), (0, -1),
                                 (2, 0), (-2, 0), (0, 2), (0, -2)}            # Woody WD
    assert dests("H", WHITE) == {(1, 1), (1, -1), (-1, 1), (-1, -1),
                                 (2, 0), (-2, 0), (0, 2), (0, -2),
                                 (3, 0), (-3, 0), (0, 3), (0, -3)}            # Half-Duck HFD
    assert dests("I", WHITE) == {(1, 2), (-1, 2), (1, -2), (-1, -2),
                                 (1, 1), (1, -1), (-1, 1), (-1, -1)}          # Fibnif vN+F
    # Fibnif is symmetric -> identical for Black.
    assert dests("I", BLACK) == dests("I", WHITE)

    # --- Cardinal (B+N) and Chancellor (R+N): knight leaps + slides present ---
    card = dests("A", WHITE)
    for k in [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]:
        assert k in card
    assert (1, 1) in card and (3, 3) in card                                 # bishop rays
    assert (1, 0) not in card and (2, 0) not in card                         # no rook rays
    chan = dests("M", WHITE)
    for k in [(1, 2), (2, 1), (-1, 2), (-2, 1)]:
        assert k in chan
    assert (1, 0) in chan and (3, 0) in chan                                 # rook rays
    assert (1, 1) not in chan and (2, 2) not in chan                         # no bishop rays

    # --- Bede (B + Dabbaba) ---
    bede = dests("D", WHITE)
    assert (1, 1) in bede and (3, 3) in bede                                 # bishop rays
    assert (2, 0) in bede and (0, 2) in bede and (-2, 0) in bede             # dabbaba leap
    assert (1, 0) not in bede and (1, 2) not in bede                         # not wazir/knight

    # --- Short Rook R4: range-limited (test from a corner for room) ---
    sr = dests("S", WHITE, at=(0, 0))
    assert (0, 1) in sr and (0, 4) in sr                                     # up to 4
    assert (0, 5) not in sr and (0, 7) not in sr                             # not 5+
    assert (1, 0) in sr and (4, 0) in sr and (5, 0) not in sr
    assert (1, 1) not in sr                                                  # orthogonal only

    # --- Nutty Knights: direction-dependent, verify BOTH colours ---
    # Charging Rook: forward+sideways rook rays, king-step backwards.
    gW = dests("G", WHITE)
    assert (0, 1) in gW and (0, 3) in gW                                     # slides forward
    assert (1, 0) in gW and (-4, 0) in gW                                    # slides sideways
    assert {(0, -1), (1, -1), (-1, -1)} <= gW                                # king backwards (1 step)
    assert (0, -2) not in gW                                                 # cannot slide backward
    gB = dests("G", BLACK)
    assert (0, -1) in gB and (0, -3) in gB                                   # Black slides "forward" = -row
    assert {(0, 1), (1, 1), (-1, 1)} <= gB                                   # king backwards for Black
    assert (0, 2) not in gB

    # Charging Knight: 4 forward knight leaps + king sideways/backwards.
    jW = dests("J", WHITE)
    assert jW == {(1, 2), (-1, 2), (2, 1), (-2, 1),                          # forward knight
                  (0, -1), (1, 0), (-1, 0),                                  # back+side wazir
                  (1, -1), (-1, -1)}                                         # back ferz
    jB = dests("J", BLACK)
    assert jB == {(1, -2), (-1, -2), (2, -1), (-2, -1),
                  (0, 1), (1, 0), (-1, 0),
                  (1, 1), (-1, 1)}

    # Colonel: forward+side rook rays + 4 forward knight + all-ferz + back wazir.
    cW = dests("C", WHITE)
    assert (0, 1) in cW and (0, 3) in cW                                     # forward slide
    assert (1, 0) in cW and (-4, 0) in cW                                    # sideways slide
    for k in [(1, 2), (-1, 2), (2, 1), (-2, 1)]:
        assert k in cW                                                       # forward knight
    assert {(1, 1), (1, -1), (-1, 1), (-1, -1)} <= cW                        # ferz (all diag)
    assert (0, -1) in cW                                                     # backward wazir step
    assert (0, -2) not in cW and (2, -1) not in cW                          # no back slide / back knight
    cB = dests("C", BLACK)
    assert (0, -1) in cB and (0, -3) in cB                                   # Black forward = -row
    assert (2, -1) in cB and (-2, -1) in cB                                  # Black forward knight
    assert (0, 1) in cB                                                      # Black backward wazir
    assert (0, 2) not in cB and (2, 1) not in cB
    print("  movement OK  (all fairy pieces, both colours for Nutty Knights)")


# --------------------------------------------------------------------------- #
def find(state, frm, to):
    tag = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
    return [m for m in GAME.legal_moves(state) if m.split("=")[0] == tag]


def clear(state, cells):
    for cc in cells:
        state.board.pop(cc, None)


def test_castling():
    # FIDE queenside (standard) + kingside.
    st = start("fide", "fide")
    clear(st, [(1, 0), (2, 0), (3, 0)])                     # b1,c1,d1 empty
    clear(st, [(5, 0), (6, 0)])                             # f1,g1 empty
    assert find(st, (4, 0), (2, 0)), "FIDE O-O-O (king e1->c1) missing"
    assert find(st, (4, 0), (6, 0)), "FIDE O-O (king e1->g1) missing"
    assert not find(st, (4, 0), (1, 0)), "FIDE should not do the 3-square flip"
    ns = GAME.apply_move(st, "4,0>2,0")
    assert ns.board[(2, 0)] == (WHITE, "K") and ns.board[(3, 0)] == (WHITE, "R")

    # Clobberers: colourbound corner (Bede) -> queenside is the 3-square flip.
    st = start("clobberers", "clobberers")
    clear(st, [(1, 0), (2, 0), (3, 0)])                     # b1(Waffle),c1(FAD),d1(Cardinal) gone
    assert find(st, (4, 0), (1, 0)), "Clobberers colourbound flip (e1->b1) missing"
    assert not find(st, (4, 0), (2, 0)), "Clobberers must NOT castle e1->c1 (flip is forced)"
    ns = GAME.apply_move(st, "4,0>1,0")
    assert ns.board[(1, 0)] == (WHITE, "K"), "king should land on b1"
    assert ns.board[(2, 0)] == (WHITE, "D"), "Bede should hop to c1"
    assert (0, 0) not in ns.board, "a1 should be vacated"

    # Clobberers kingside is the ordinary 2-square castle (h1 not colourbound-blocked).
    st = start("clobberers", "clobberers")
    clear(st, [(5, 0), (6, 0)])                             # f1(FAD),g1(Waffle) gone
    assert find(st, (4, 0), (6, 0)), "Clobberers O-O (king e1->g1) missing"
    ns = GAME.apply_move(st, "4,0>6,0")
    assert ns.board[(6, 0)] == (WHITE, "K") and ns.board[(5, 0)] == (WHITE, "D")

    # Rookies / Nutters: ordinary queenside (their a-file piece is NOT colourbound).
    for army in ("rookies", "knights"):
        st = start(army, army)
        clear(st, [(1, 0), (2, 0), (3, 0)])
        assert find(st, (4, 0), (2, 0)), f"{army} standard O-O-O missing"
        assert not find(st, (4, 0), (1, 0)), f"{army} should not flip-castle"
    print("  castling OK  (FIDE std, Clobberers colourbound flip, Rookies/Nutters std)")


def test_promotion():
    st = start("fide", "clobberers")
    # White pawn one step from promotion on the b-file; clear its target square.
    clear(st, [(1, 6), (1, 7)])                             # remove black b7 pawn + b8 piece
    st.board[(1, 6)] = (WHITE, "P")                         # white pawn on b7
    promos = {m.split("=")[1] for m in GAME.legal_moves(st)
              if m.startswith("1,6>1,7=") or m.startswith("1,6>0,7=") or m.startswith("1,6>2,7=")}
    # union of FIDE {Q,R,B,N} and Clobberers {A,D,F,W}
    assert promos == {"Q", "R", "B", "N", "A", "D", "F", "W"}, promos
    # Promote to a Clobberer Cardinal and confirm the piece is placed.
    ns = GAME.apply_move(st, "1,6>1,7=A")
    assert ns.board[(1, 7)] == (WHITE, "A")
    print("  promotion OK  (either army's pieces; union of both rosters)")


def test_checkmate():
    # Back-rank mate delivered by a Chancellor (Rook+Knight, Rookies army).
    from agp.chesslike import CState
    board = {
        (4, 0): (WHITE, "K"),
        (0, 7): (WHITE, "M"),          # White Chancellor on a8, mating along rank 8
        (6, 7): (BLACK, "K"),          # Black king g8
        (5, 6): (BLACK, "P"),          # f7
        (6, 6): (BLACK, "P"),          # g7
        (7, 6): (BLACK, "P"),          # h7
    }
    st = GAME.deserialize({
        "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in board.items()},
        "to_move": BLACK, "castling": "", "ep": None, "halfmove": 0, "ply": 0, "reps": {},
        "white_army": "rookies", "black_army": "fide", "promo_targets": [],
    })
    assert GAME.in_check(st.board, BLACK), "Black king should be in check"
    assert GAME.legal_moves(st) == [], "position should be checkmate (no legal moves)"
    assert GAME.is_terminal(st)
    assert GAME.returns(st) == [1.0, -1.0], "White should win the checkmate"
    print("  checkmate OK  (fairy-piece back-rank mate; terminal + returns)")


# --------------------------------------------------------------------------- #
def test_conformance():
    pairings = [("fide", "clobberers"), ("clobberers", "rookies"),
                ("rookies", "knights"), ("knights", "fide"),
                ("knights", "knights"), ("clobberers", "clobberers")]
    rng = random.Random(1234)
    for wa, ba in pairings:
        for _ in range(3):
            st = start(wa, ba)
            plies = 0
            while not GAME.is_terminal(st):
                moves = GAME.legal_moves(st)
                assert moves, "non-terminal state with no moves"
                st = GAME.apply_move(st, rng.choice(moves))
                plies += 1
                assert plies <= GAME.PLY_CAP + 5, "did not terminate"
            # returns is a valid 2-vector
            ret = GAME.returns(st)
            assert ret in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0]), ret
            # serialize round-trip
            rt = GAME.deserialize(GAME.serialize(st))
            assert GAME._poskey_state(rt) == GAME._poskey_state(st)
    print("  conformance OK  (random playouts reach terminal; serialize round-trips)")


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    print("cwda selftest")
    test_perft()
    test_movement()
    test_castling()
    test_promotion()
    test_checkmate()
    test_conformance()
    print("all cwda selftests passed")
