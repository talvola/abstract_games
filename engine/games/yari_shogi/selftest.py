"""Yari Shogi correctness anchor (pure stdlib -- imports only agp + this game).

There is no external Yari-Shogi oracle, so the perft counts below are this engine's
own: depth 1 (opening = 20) is hand-derived in the docstring of main; depths 2-3 are
FROZEN as a regression guard. The bulk of the value is the targeted move-shape
assertions -- every spear (Yari Knight's forward-slide-plus-jump, the Yari Bishop,
the forward+sideways Yari Rook) and every promotion (Pawn->Yari Silver,
Bishop/Knight->Yari Gold, Yari Rook->Rook) is checked against a constructed
position, plus the standard nifu, a reserve drop, a capture banking with
promoted-piece reversion, a serialize round-trip, and a checkmate reached via
apply_move.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.yari_shogi.game import YariShogi          # noqa: E402
from agp.shogilike import SState, BLACK, WHITE        # noqa: E402

G = YariShogi()


def perft(s, d):
    if d == 0:
        return 1
    if G.is_terminal(s):
        return 0
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def dests(st, frm):
    out = set()
    for m in G.legal_moves(st):
        if ">" in m and m.split(">")[0] == frm:
            out.add(m.split(">")[1].split("=")[0])
    return out


def main():
    s0 = G.initial_state()

    # 1) Opening count = 20, hand-derived (Black, row 1 empty, row 2 = own pawns):
    #    7 Pawns step forward (7)
    #    + 2 Yari Rooks (corners): forward 1 each; sideways blocked by own piece (2)
    #    + 2 Yari Bishops: forward slide 1 + 2 forward-diagonal steps each = 3 each (6)
    #    + General (centre): forward + 2 fwd-diagonals (sideways blocked, back off) (3)
    #    + 2 Yari Knights: forward slide 1; the (+-1,+2) leap lands on own pawns (2)
    #    = 7 + 2 + 6 + 3 + 2 = 20.
    assert len(G.legal_moves(s0)) == 20, len(G.legal_moves(s0))
    # frozen perft (this engine's own counts; no published oracle exists)
    for d, want in {1: 20, 2: 400, 3: 7960}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # 2) Setup: 7x9, back rank R B B G N N R, full pawn rank, General on centre file,
    #    White a clean 180-degree rotation.
    assert G.WIDTH == 7 and G.HEIGHT == 9
    back = ["R", "B", "B", "G", "N", "N", "R"]
    for c, t in enumerate(back):
        assert s0.board[(c, 0)] == (BLACK, t), (c, s0.board.get((c, 0)))
        assert s0.board[(6 - c, 8)] == (WHITE, t), (c, s0.board.get((6 - c, 8)))
    assert all(s0.board[(c, 2)] == (BLACK, "P") for c in range(7))
    assert all(s0.board[(c, 6)] == (WHITE, "P") for c in range(7))
    assert s0.board[(3, 0)] == (BLACK, "G") and s0.board[(3, 8)] == (WHITE, "G")
    assert sum(1 for v in s0.board.values() if v[0] == BLACK) == 14

    # 3) Yari Knight: ranges straight forward (slide) AND jumps (+-1, +2).
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G"), (3, 3): (BLACK, "N")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"3,4", "3,5", "3,6", "3,7", "3,8", "2,5", "4,5"}, dests(st, "3,3")
    # the forward jump leaps OVER an intervening piece:
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G"),
                       (3, 3): (BLACK, "N"), (3, 4): (WHITE, "P")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert "2,5" in dests(st, "3,3") and "4,5" in dests(st, "3,3")
    assert "3,5" not in dests(st, "3,3")          # forward slide blocked by the pawn

    # 4) Yari Bishop: forward slide + one-step forward diagonals (both).
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G"), (3, 3): (BLACK, "B")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"3,4", "3,5", "3,6", "3,7", "3,8", "2,4", "4,4"}, dests(st, "3,3")

    # 5) Yari Rook: forward slide + the whole rank (sideways).
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G"), (3, 3): (BLACK, "R")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"3,4", "3,5", "3,6", "3,7", "3,8",
                                "0,3", "1,3", "2,3", "4,3", "5,3", "6,3"}, dests(st, "3,3")

    # 6) Yari Silver (promoted Pawn): backward slide + the 3 forward steps.
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G"), (3, 3): (BLACK, "P")},
                promoted=frozenset({(3, 3)}), hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"3,1", "3,2", "2,4", "3,4", "4,4"}, dests(st, "3,3")

    # 7) Yari Gold (promoted Bishop / Knight): backward slide + the 5 fwd/lateral steps
    #    (no diagonal-backward step).
    for L in ("B", "N"):
        st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G"), (3, 3): (BLACK, L)},
                    promoted=frozenset({(3, 3)}), hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
        assert dests(st, "3,3") == {"3,1", "3,2", "2,4", "3,4", "4,4", "2,3", "4,3"}, (L, dests(st, "3,3"))

    # 8) Rook (promoted Yari Rook): the full four-direction rook.
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G"), (3, 3): (BLACK, "R")},
                promoted=frozenset({(3, 3)}), hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"3,1", "3,2", "3,4", "3,5", "3,6", "3,7", "3,8",
                                "0,3", "1,3", "2,3", "4,3", "5,3", "6,3"}, dests(st, "3,3")

    # 9) Promotion: mandatory when otherwise immobile, optional in-zone otherwise.
    #    Pawn reaching the last rank MUST promote (only the +move exists):
    st = SState(board={(3, 0): (BLACK, "G"), (0, 8): (WHITE, "G"), (3, 7): (BLACK, "P")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert [m for m in G.legal_moves(st) if m.startswith("3,7>")] == ["3,7>3,8=+"]
    #    Yari Bishop into the zone (3,6) -> optional:
    st = SState(board={(3, 0): (BLACK, "G"), (0, 8): (WHITE, "G"), (3, 5): (BLACK, "B")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    fm = {m for m in G.legal_moves(st) if m.startswith("3,5>3,6")}
    assert fm == {"3,5>3,6", "3,5>3,6=+"}, fm
    #    Yari Knight landing in the last two ranks MUST promote:
    st = SState(board={(3, 0): (BLACK, "G"), (0, 8): (WHITE, "G"), (3, 5): (BLACK, "N")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert [m for m in G.legal_moves(st) if m.startswith("3,5>4,7")] == ["3,5>4,7=+"]

    # 10) Nifu: at most ONE unpromoted Pawn per file (standard Shogi); a Pawn may not
    #     be dropped on the last rank.
    st = SState(board={(3, 0): (BLACK, "G"), (0, 8): (WHITE, "G"), (4, 3): (BLACK, "P")},
                hands={BLACK: {"P": 1}, WHITE: {}}, to_move=BLACK)
    drops = {m for m in G.legal_moves(st) if m.startswith("P@")}
    assert not any(m.split("@")[1].split(",")[0] == "4" for m in drops), "nifu: 2nd pawn on file allowed"
    assert any(m.split("@")[1].split(",")[0] == "5" for m in drops), "pawn drop missing"
    assert not any(m.endswith(",8") for m in drops), "pawn dropped on last rank"

    # 11) Capture banks to hand; a captured Yari Gold reverts to a plain Yari Bishop.
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G"),
                       (2, 2): (BLACK, "B"), (3, 3): (WHITE, "B")},
                promoted=frozenset({(3, 3)}), hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "2,2>3,3")             # Yari Bishop steps fwd-diag to capture
    assert st2.hands[BLACK] == {"B": 1}, st2.hands
    assert (3, 3) not in st2.promoted

    # 12) Drop from the reserve places the spear and decrements the hand.
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "G")},
                hands={BLACK: {"R": 1}, WHITE: {}}, to_move=BLACK)
    st3 = G.apply_move(st, "R@4,4")
    assert st3.board[(4, 4)] == (BLACK, "R") and st3.hands[BLACK] == {}

    # 13) Serialize round-trips (board + promoted + hands + to_move + ply).
    st = SState(board={(3, 0): (BLACK, "G"), (3, 8): (WHITE, "R"), (2, 3): (BLACK, "P")},
                promoted=frozenset({(3, 8)}), hands={BLACK: {"B": 2}, WHITE: {"N": 1}},
                to_move=WHITE, ply=5)
    assert G.serialize(G.deserialize(G.serialize(st))) == G.serialize(st)
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)

    # 14) Checkmate REACHED via apply_move (the General is royal): White's General is
    #     cornered at (0,8); Black's Yari Rook ranges up file 0 to (0,7) giving check,
    #     a second Yari Rook (file 1) covers (1,8) and a Yari Bishop defends (0,7) ->
    #     White has no reply and loses.
    st = SState(board={(0, 8): (WHITE, "G"), (3, 0): (BLACK, "G"),
                       (0, 4): (BLACK, "R"), (1, 5): (BLACK, "R"), (1, 6): (BLACK, "B")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    mated = G.apply_move(st, "0,4>0,7")
    assert mated.to_move == WHITE
    assert G.legal_moves(mated) == [] and G.is_terminal(mated)
    assert G.returns(mated) == [1.0, -1.0]

    print("yari_shogi selftest OK")


if __name__ == "__main__":
    main()
