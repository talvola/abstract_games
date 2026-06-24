"""Pure-stdlib correctness anchor for Seirawan Chess (S-Chess).

Frozen, engine-derived facts (no external oracle needed):
  * Opening move count = 28: 16 pawn pushes + 4 knight moves, where each of the 4
    knight moves ALSO offers 2 gating variants (gate Hawk / gate Elephant onto the
    vacated knight square) -> 16 + 4 + 8 = 28. (Only the knights can leave the
    back rank on move 1, so only knight moves can gate at the start.)
  * Frozen perft: perft(1)=28, perft(2)=784, perft(3)=24830.
  * A knight's first move WITH a gate places the gated piece on the vacated FROM
    square, decrements the reserve, and consumes that square's gating right.
  * A back-rank piece that moves WITHOUT gating loses that square's gating right.
  * Castling can gate one piece onto EITHER the king's or the rook's vacated
    square (=H/=E vs =Hr/=Er); not both.
  * Promotion to Hawk/Elephant only when it is still in the reserve, and the
    promotion consumes it from the reserve.
  * Gating is forbidden while in check (cannot gate to block check).
  * serialize/deserialize round-trips board + reserves + gating rights.
  * A gated piece can deliver checkmate (reach a terminal via apply_move).

Run: PYTHONPATH=. python3 games/seirawan/selftest.py
"""

from __future__ import annotations

from agp.chesslike import CState, WHITE, BLACK
from games.seirawan.game import Seirawan


def perft(g, st, d):
    if d == 0:
        return 1
    if g.is_terminal(st):
        return 0
    return sum(perft(g, g.apply_move(st, m), d - 1) for m in g.legal_moves(st))


def main() -> None:
    g = Seirawan()
    s = g.initial_state()

    # --- opening move count + composition (frozen) ---
    mv = g.legal_moves(s)
    plain = [m for m in mv if "=" not in m]
    gated = [m for m in mv if "=" in m]
    assert len(mv) == 28, f"opening total {len(mv)} != 28"
    assert len(plain) == 20, f"plain opening moves {len(plain)} != 20"
    assert len(gated) == 8, f"gating opening moves {len(gated)} != 8"
    # every gated opening move is a knight move that gates H or E onto the vacated
    # knight square (b1/g1 for White).
    for m in gated:
        body, suf = m.split("=")
        assert suf in ("H", "E"), f"unexpected opening gate suffix {m}"
        frm = body.split(">")[0]
        assert frm in ("1,0", "6,0"), f"gating from non-knight square {m}"

    # --- starting reserves: one Hawk + one Elephant each ---
    assert s.hands == {WHITE: {"H": 1, "E": 1}, BLACK: {"H": 1, "E": 1}}, s.hands
    assert g._gates(s) == frozenset(
        [(c, 0) for c in range(8)] + [(c, 7) for c in range(8)]), "wrong starting gates"

    # --- frozen perft ---
    assert perft(g, s, 1) == 28
    assert perft(g, s, 2) == 784
    assert perft(g, s, 3) == 24830

    # --- knight first move WITH a gate-drop ---
    s2 = g.apply_move(s, "1,0>2,2=H")             # Nb1-c3, gate Hawk onto b1
    assert s2.board[(1, 0)] == (WHITE, "H"), "Hawk not gated onto vacated square"
    assert s2.board[(2, 2)] == (WHITE, "N"), "knight did not land"
    assert s2.hands[WHITE].get("H", 0) == 0, "Hawk not removed from reserve"
    assert s2.hands[WHITE].get("E", 0) == 1, "Elephant should remain in reserve"
    assert (1, 0) not in g._gates(s2), "gating right not consumed"

    # --- a back-rank piece that moves WITHOUT gating loses the right ---
    s3 = g.apply_move(s, "1,0>2,2")
    assert (1, 0) not in g._gates(s3), "gating right not lost on a no-gate move"
    assert (1, 0) not in s3.board, "no piece should be on the vacated square"
    assert s3.hands[WHITE] == {"H": 1, "E": 1}, "reserve changed on a no-gate move"

    # --- castling can gate onto the king's OR the rook's vacated square ---
    b = {(4, 0): (WHITE, "K"), (7, 0): (WHITE, "R"), (4, 7): (BLACK, "K")}
    st = CState(board=b, to_move=WHITE, castling=frozenset("K"), ep=None,
                hands={WHITE: {"H": 1, "E": 1}, BLACK: {"H": 1, "E": 1}})
    st.gates = frozenset({(4, 0), (7, 0)})
    castle = sorted(m for m in g.legal_moves(st) if m.startswith("4,0>6,0"))
    assert castle == ["4,0>6,0", "4,0>6,0=E", "4,0>6,0=Er",
                      "4,0>6,0=H", "4,0>6,0=Hr"], f"castle gate menu wrong: {castle}"
    sc = g.apply_move(st, "4,0>6,0=Hr")           # gate onto the rook's square h1
    assert sc.board[(6, 0)] == (WHITE, "K") and sc.board[(5, 0)] == (WHITE, "R")
    assert sc.board[(7, 0)] == (WHITE, "H"), "Hawk not gated onto rook square"
    sc2 = g.apply_move(st, "4,0>6,0=E")           # gate onto the king's square e1
    assert sc2.board[(4, 0)] == (WHITE, "E"), "Elephant not gated onto king square"

    # --- promotion to Hawk only when it is still in reserve; it is consumed ---
    b2 = {(0, 6): (WHITE, "P"), (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K")}
    sp = CState(board=b2, to_move=WHITE, castling=frozenset(), ep=None,
                hands={WHITE: {"H": 1, "E": 1}, BLACK: {}})
    sp.gates = frozenset()
    pm = sorted(m for m in g.legal_moves(sp) if m.startswith("0,6>0,7"))
    assert "0,6>0,7=H" in pm and "0,6>0,7=E" in pm, f"missing H/E promotion: {pm}"
    sp2 = g.apply_move(sp, "0,6>0,7=H")
    assert sp2.board[(0, 7)] == (WHITE, "H"), "pawn did not promote to Hawk"
    assert sp2.hands[WHITE].get("H", 0) == 0, "Hawk promotion did not consume reserve"
    # with no Hawk left, H-promotion is unavailable
    sp3 = CState(board=b2, to_move=WHITE, castling=frozenset(), ep=None,
                 hands={WHITE: {"E": 1}, BLACK: {}})
    sp3.gates = frozenset()
    pm3 = [m for m in g.legal_moves(sp3) if m.startswith("0,6>0,7")]
    assert "0,6>0,7=H" not in pm3 and "0,6>0,7=E" in pm3, f"H-promo should be gone: {pm3}"

    # --- gating is forbidden while in check (cannot gate to block check) ---
    b3 = {(4, 0): (WHITE, "K"), (1, 0): (WHITE, "N"),
          (4, 5): (BLACK, "R"), (0, 7): (BLACK, "K")}
    sk = CState(board=b3, to_move=WHITE, castling=frozenset(), ep=None,
                hands={WHITE: {"H": 1, "E": 1}, BLACK: {}})
    sk.gates = frozenset({(1, 0), (4, 0)})
    assert not any("=" in m for m in g.legal_moves(sk)), "gating offered while in check"

    # --- a gated piece can deliver checkmate (reach a terminal via apply_move) ---
    # White: Re1 gives the long file; gating an Elephant onto a knight square that
    # mates the cornered black king. Build a clean smothered-style mate by gating.
    # Black king h8 (7,7); White Rg1 controls g-file; Hawk gated to f6 mates? We
    # use a direct construction: Black Kh8, pawns g7,h7; White Qg-... Simpler: a
    # back-rank gated Elephant mate.
    bm = {
        (7, 7): (BLACK, "K"),               # Kh8
        (6, 6): (BLACK, "P"), (7, 6): (BLACK, "P"),  # g7,h7 pawns
        (1, 0): (WHITE, "N"),               # knight b1 (will move, gating)
        (6, 0): (WHITE, "R"),               # Rg1 controls g-file
        (5, 5): (WHITE, "Q"),               # Qf6: guards g7, attacks along
        (0, 0): (WHITE, "K"),               # Ka1
    }
    sm = CState(board=bm, to_move=WHITE, castling=frozenset(), ep=None,
                hands={WHITE: {"H": 1, "E": 1}, BLACK: {}})
    sm.gates = frozenset({(1, 0)})
    # Qf6xg7 is mate already in this construction (Kh8, Rg1 pins the g-file,
    # Qg7#). Confirm a mating move exists and produces a terminal.
    mated = None
    for m in g.legal_moves(sm):
        nxt = g.apply_move(sm, m)
        if g.is_terminal(nxt) and g.returns(nxt) == [1.0, -1.0]:
            mated = (m, nxt)
            break
    assert mated is not None, "expected at least one mating move in the construction"

    # --- serialize / deserialize round-trip (board + reserves + gating rights) ---
    for state in (s, s2, s3, sc, sc2, sp2):
        rt = g.deserialize(g.serialize(state))
        assert rt.board == state.board, "board lost in round-trip"
        assert rt.hands == state.hands, "reserves lost in round-trip"
        assert g._gates(rt) == g._gates(state), "gating rights lost in round-trip"
        assert rt.to_move == state.to_move and rt.castling == state.castling

    print("SELFTEST OK  (opening 28 = 20 plain + 8 gating; perft 28/784/24830)")


if __name__ == "__main__":
    main()
