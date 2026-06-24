"""Tori Shogi correctness anchor (pure stdlib -- imports only agp + this game).

There is no external Tori-Shogi oracle (python-shogi doesn't cover it), so the
perft counts below are this engine's own, hand-checked at depth 1 (opening = 17,
derived piece-by-piece in the docstring of main) and FROZEN at depths 2-3 as a
regression guard. The bulk of the value is the targeted move-shape assertions:
every unusual bird (the asymmetric Quails, the jump-over Pheasant/Goose, the Crane,
the Eagle) is checked against a constructed position, plus the Falcon->Eagle /
Swallow->Goose promotions, the Tori two-swallow nifu, a reserve drop, a capture
banking with promoted-piece reversion, a serialize round-trip, and a checkmate
reached via apply_move.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.tori_shogi.game import ToriShogi          # noqa: E402
from agp.shogilike import SState, BLACK, WHITE        # noqa: E402

G = ToriShogi()


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

    # 1) Opening count = 17, hand-derived:
    #    7 Swallows step forward (the 6th file's row-2 swallow is blocked by the
    #    advanced swallow ahead of it, but that advanced swallow itself moves),
    #    + Phoenix 2 (the two forward diagonals; forward is blocked by the Falcon),
    #    + Falcon 2 (sideways; the rest blocked by own swallows/cranes),
    #    + 2 Cranes x 2, + Left Quail 1 + Right Quail 1 = 17.
    assert len(G.legal_moves(s0)) == 17, len(G.legal_moves(s0))
    # frozen perft (this engine's own counts; no published oracle exists)
    for d, want in {1: 17, 2: 288, 3: 5445}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # 2) Setup is a clean 180-degree rotation: advanced swallows are mirror images
    #    (Black on file c / White on file e), kings... err Phoenixes on the centre file.
    assert s0.board[(2, 3)] == (BLACK, "S") and s0.board[(4, 3)] == (WHITE, "S")
    assert s0.board[(3, 0)] == (BLACK, "P") and s0.board[(3, 6)] == (WHITE, "P")
    assert s0.board[(0, 0)] == (BLACK, "L") and s0.board[(6, 0)] == (BLACK, "R")
    assert s0.board[(6, 6)] == (WHITE, "L") and s0.board[(0, 6)] == (WHITE, "R")
    assert sum(1 for v in s0.board.values() if v == (BLACK, "S")) == 8

    # 3) Pheasant JUMPS over an intervening piece (2 forward) and steps both back-diags.
    st = SState(board={(3, 0): (BLACK, "P"), (3, 6): (WHITE, "P"),
                       (3, 3): (BLACK, "H"), (3, 4): (WHITE, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"3,5", "2,2", "4,2"}, dests(st, "3,3")

    # 4) Left Quail: ranges forward + diagonally back-right, steps back-left.
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"), (3, 3): (BLACK, "L")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"3,4", "3,5", "3,6", "4,2", "5,1", "6,0", "2,2"}, dests(st, "3,3")
    # Right Quail is the mirror: ranges forward + diagonally back-left, steps back-right.
    st = SState(board={(6, 0): (BLACK, "P"), (0, 6): (WHITE, "P"), (3, 3): (BLACK, "R")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"3,4", "3,5", "3,6", "2,2", "1,1", "0,0", "4,2"}, dests(st, "3,3")
    # And the same Left Quail for WHITE is a full 180-degree mirror of Black's.
    st = SState(board={(0, 6): (WHITE, "P"), (6, 0): (BLACK, "P"), (3, 3): (WHITE, "L")},
                hands={BLACK: {}, WHITE: {}}, to_move=WHITE)
    assert dests(st, "3,3") == {"3,2", "3,1", "3,0", "2,4", "1,5", "4,4"}, dests(st, "3,3")

    # 5) Crane = 6 steps (4 diagonals + straight fwd/back, no sideways).
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"), (3, 3): (BLACK, "C")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"2,4", "4,4", "2,2", "4,2", "3,4", "3,2"}, dests(st, "3,3")

    # 6) Falcon = 7 king steps except straight backward.
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"), (3, 3): (BLACK, "F")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"2,4", "3,4", "4,4", "2,3", "4,3", "2,2", "4,2"}, dests(st, "3,3")

    # 7) Eagle (promoted Falcon): ranges diag-fwd + straight back; steps 1-2 diag back,
    #    + one fwd and sideways.
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"), (3, 3): (BLACK, "F")},
                promoted=frozenset({(3, 3)}), hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {
        "2,4", "1,5", "0,6", "4,4", "5,5", "6,6",      # ranges diag-fwd
        "3,2", "3,1", "3,0",                            # range straight back
        "2,2", "1,1", "4,2", "5,1",                    # 1-2 diag back
        "3,4", "2,3", "4,3",                            # fwd + sideways
    }, dests(st, "3,3")

    # 8) Goose (promoted Swallow): jumps 2 diag-fwd (both) and 2 straight back.
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"), (3, 3): (BLACK, "S")},
                promoted=frozenset({(3, 3)}), hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert dests(st, "3,3") == {"1,5", "5,5", "3,1"}, dests(st, "3,3")

    # 9) Promotion: a Falcon entering the far two ranks MAY promote (optional);
    #    a Swallow reaching the last rank MUST (mandatory, only the +move exists).
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"), (3, 4): (BLACK, "F")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    fm = {m for m in G.legal_moves(st) if m.startswith("3,4>3,5")}
    assert fm == {"3,4>3,5", "3,4>3,5=+"}, fm
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"), (3, 5): (BLACK, "S")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    assert [m for m in G.legal_moves(st) if m.startswith("3,5>")] == ["3,5>3,6=+"]

    # 10) Tori nifu: at most TWO unpromoted swallows per file -- a THIRD drop is
    #     blocked on that file but allowed elsewhere, and never on the last rank.
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"),
                       (4, 2): (BLACK, "S"), (4, 3): (BLACK, "S")},
                hands={BLACK: {"S": 1}, WHITE: {}}, to_move=BLACK)
    drops = {m for m in G.legal_moves(st) if m.startswith("S@")}
    assert not any(m.split("@")[1].split(",")[0] == "4" for m in drops), "3rd swallow allowed (nifu)"
    assert any(m.split("@")[1].split(",")[0] == "5" for m in drops), "swallow drop missing"
    assert not any(m.endswith(",6") for m in drops), "swallow dropped on last rank"
    # but with only ONE swallow on the file the drop IS legal (the Tori difference).
    st1 = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P"), (4, 2): (BLACK, "S")},
                 hands={BLACK: {"S": 1}, WHITE: {}}, to_move=BLACK)
    assert any(m.split("@")[1].split(",")[0] == "4"
               for m in G.legal_moves(st1) if m.startswith("S@")), "2nd swallow wrongly blocked"

    # 11) Capture banks to hand; a captured Goose reverts to a plain Swallow.
    st = SState(board={(3, 0): (BLACK, "P"), (3, 6): (WHITE, "P"),
                       (2, 2): (BLACK, "F"), (2, 3): (WHITE, "S")},
                promoted=frozenset({(2, 3)}), hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    st2 = G.apply_move(st, "2,2>2,3")
    assert st2.hands[BLACK] == {"S": 1}, st2.hands
    assert (2, 3) not in st2.promoted

    # 12) Drop from the reserve places the bird and decrements the hand.
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "P")},
                hands={BLACK: {"F": 1}, WHITE: {}}, to_move=BLACK)
    st3 = G.apply_move(st, "F@3,3")
    assert st3.board[(3, 3)] == (BLACK, "F") and st3.hands[BLACK] == {}

    # 13) Serialize round-trips (board + promoted + hands + to_move + ply).
    st = SState(board={(0, 0): (BLACK, "P"), (6, 6): (WHITE, "F"), (2, 3): (BLACK, "S")},
                promoted=frozenset({(6, 6)}), hands={BLACK: {"C": 2}, WHITE: {"S": 1}},
                to_move=WHITE, ply=5)
    assert G.serialize(G.deserialize(G.serialize(st))) == G.serialize(st)
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)

    # 14) Checkmate REACHED via apply_move (Phoenix is the royal): Black's Left Quail
    #     ranges up file 0 to (0,5) giving check; a Crane guards (0,5) and a Falcon
    #     covers the escapes -> White has no reply and loses.
    st = SState(board={(0, 6): (WHITE, "P"), (3, 0): (BLACK, "P"),
                       (2, 5): (BLACK, "F"), (1, 4): (BLACK, "C"), (0, 3): (BLACK, "L")},
                hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
    mated = G.apply_move(st, "0,3>0,5")
    assert mated.to_move == WHITE
    assert G.legal_moves(mated) == [] and G.is_terminal(mated)
    assert G.returns(mated) == [1.0, -1.0]

    print("tori_shogi selftest OK")


if __name__ == "__main__":
    main()
