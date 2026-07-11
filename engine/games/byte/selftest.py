"""Byte correctness anchor (pure stdlib). No perft exists; the anchor is a set
of rule assertions taken directly from Mark Steere's official rule sheet
(marksteeregames.com/Byte_rules.pdf), including its worked figures:

 (1) initial array: standard checkers setup, 12 v 12 on dark squares, White first;
 (2) basic moves: whole stack, bottom-checker ownership, ONLY when not adjacent
     to any stack, and strictly closer to a closest stack (incl. the tie case);
 (3) merging: pick up YOUR checker at any level carrying everything above it;
     must rise to a higher altitude (Fig. 5: same-level merge illegal); may not
     form 9+ (Fig. 6); order preserved; onto friendly or mixed stacks alike;
 (4) a stack of exactly 8 is removed and scored for its TOP checker's owner --
     including the forced Fig. 6 move that hands the stack to the opponent;
 (5) majority win: the 2nd scored stack ends the game (via apply_move);
 (6) no-move -> forced "pass" (opponent still to move normally);
 (7) serialize round-trip; (8) 500 random playouts all terminate decisively.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.byte.game import (  # noqa: E402
    Byte, BState, WHITE, BLACK, _dist, _on,
)

G = Byte()


def S(board, to_move=WHITE, scored=None):
    return BState(board=board, scored=scored or {WHITE: 0, BLACK: 0},
                  to_move=to_move)


def cols(st):
    return {f"{c},{r}": G._col_str(v) for (c, r), v in st.board.items()}


def main():
    # --- (1) initial array ---------------------------------------------------
    s0 = G.initial_state()
    assert s0.to_move == WHITE, "White moves first (PDF: MOVE)"
    assert len(s0.board) == 24
    assert all(_on(c, r) for (c, r) in s0.board), "dark squares only"
    assert all(len(col) == 1 for col in s0.board.values())
    assert sum(1 for col in s0.board.values() if col == (WHITE,)) == 12
    assert sum(1 for col in s0.board.values() if col == (BLACK,)) == 12
    assert all(r <= 2 for (c, r), col in s0.board.items() if col == (WHITE,))
    assert all(r >= 5 for (c, r), col in s0.board.items() if col == (BLACK,))
    # every opening move is a single-checker merge (all White stacks touch);
    # 14 adjacent White pairs x 2 directions = 28 moves, no slides, no pass
    om = G.legal_moves(s0)
    assert len(om) == 28 and all(m.endswith("=1") for m in om), (len(om), om[:4])

    # --- distance metric -----------------------------------------------------
    assert _dist((1, 0), (0, 1)) == 1 and _dist((1, 0), (5, 0)) == 4
    assert _dist((3, 2), (3, 6)) == 4 and _dist((3, 2), (7, 6)) == 4

    # --- (2) basic move: bottom ownership + isolation + move-closer ----------
    # White-bottomed stack at (3,2); enemy-bottomed stacks at (3,6) and (7,6)
    # tie as closest (both distance 4). Legal slides = the two neighbours that
    # approach ONE of the tied nearest stacks: (2,3) [toward 3,6] and (4,3)
    # [toward both]; the away squares (2,1)/(4,1) are illegal.
    st = S({(3, 2): (WHITE, BLACK), (3, 6): (BLACK,), (7, 6): (BLACK,)})
    lm = set(G.legal_moves(st))
    assert lm == {"3,2>2,3", "3,2>4,3"}, lm
    # Black owns no bottom of an isolated stack he may slide toward... he does:
    # (3,6)'s and (7,6)'s bottoms are Black -> Black may slide those instead,
    # but NOT the White-bottomed (3,2) even though Black's checker is on top.
    st_b = S({(3, 2): (WHITE, BLACK), (3, 6): (BLACK,), (7, 6): (BLACK,)}, BLACK)
    assert not any(m.startswith("3,2>") for m in G.legal_moves(st_b)), \
        "bottom checker (not top) grants the basic move"
    assert any(m.startswith("3,6>") for m in G.legal_moves(st_b))
    # slide moves the ENTIRE stack
    st2 = G.apply_move(st, "3,2>4,3")
    assert cols(st2)["4,3"] == "WB" and "3,2" not in cols(st2)

    # --- (2b) adjacent stacks can never move to an unoccupied square ---------
    st = S({(2, 1): (WHITE,), (1, 2): (WHITE,)})
    lm = G.legal_moves(st)
    assert all("=" in m for m in lm), ("merge-only when adjacent", lm)

    # --- (3) merging: levels, altitude, carry-order, 9-cap -------------------
    # A = (2,1) W,B,W bottom->top (h3); B = (1,2) W,W (h2), adjacent.
    A, B = (2, 1), (1, 2)
    st = S({A: (WHITE, BLACK, WHITE), B: (WHITE, WHITE)})
    lm = set(G.legal_moves(st))
    # White may lift his level-1 checker (carrying B,W above) -> lands level 3.
    assert "2,1>1,2=3" in lm
    # Fig. 5 rule: White's level-3 checker would land at level 3 = SAME altitude
    # -> illegal (n=1 -> picked level 3 > hB=2).
    assert "2,1>1,2=1" not in lm, "same-or-lower altitude merge must be illegal"
    # Black's level-2 checker is not White's to move.
    assert "2,1>1,2=2" not in lm
    st_b = S({A: (WHITE, BLACK, WHITE), B: (WHITE, WHITE)}, BLACK)
    assert "2,1>1,2=2" in set(G.legal_moves(st_b)), "any level of YOUR checker"
    # carry-order: Black lifts level 2 carrying the White above; order preserved
    st2 = G.apply_move(st_b, "2,1>1,2=2")
    assert cols(st2)["1,2"] == "WWBW" and cols(st2)["2,1"] == "W", cols(st2)
    # whole-stack merge leaves the source empty
    st2 = G.apply_move(st, "2,1>1,2=3")
    assert cols(st2)["1,2"] == "WWWBW" and "2,1" not in cols(st2)
    # Fig. 6 rule: cannot form a stack of nine or more
    st = S({A: (BLACK, BLACK), B: (WHITE,) * 7}, BLACK)
    lm = set(G.legal_moves(st))
    assert "2,1>1,2=2" not in lm, "2+7=9 forbidden"
    # ...and the altitude rule works downhill too: White may NOT move B's top
    # checker onto the shorter A (level 7 -> level 3 is lower), but lifting his
    # level-2 checker (carrying the 5 above) lands it at level 3 > 2: legal.
    st_w = S({A: (BLACK, BLACK), B: (WHITE,) * 7})
    lm_w = set(G.legal_moves(st_w))
    assert "1,2>2,1=1" not in lm_w, "top checker would sink: illegal"
    assert "1,2>2,1=6" in lm_w and "1,2>2,1=7" not in lm_w, lm_w  # 7 would make 9

    # --- (4) stack of 8 removed, scored for the TOP checker's owner ----------
    # Fig. 6 scenario: Black's ONLY move completes an 8 topped by WHITE.
    st = S({A: (BLACK, WHITE), B: (WHITE, WHITE, BLACK, BLACK, BLACK, WHITE)},
           BLACK)
    assert G.legal_moves(st) == ["2,1>1,2=2"], G.legal_moves(st)
    st2 = G.apply_move(st, "2,1>1,2=2")
    assert st2.board == {}, "the 8-stack is removed at once"
    assert st2.scored == {WHITE: 1, BLACK: 0}, \
        ("top checker owns the stack", st2.scored)
    assert st2.winner is None, "1 of 3 stacks is not yet the majority"

    # --- (5) majority win via apply_move --------------------------------------
    st = S({A: (BLACK, WHITE), B: (WHITE, WHITE, BLACK, BLACK, BLACK, WHITE)},
           BLACK, scored={WHITE: 1, BLACK: 1})
    st2 = G.apply_move(st, "2,1>1,2=2")
    assert st2.winner == WHITE and G.is_terminal(st2)
    assert G.returns(st2) == [1.0, -1.0]
    assert G.legal_moves(st2) == []

    # --- (6) no-move -> forced pass -------------------------------------------
    # Black's only checker is buried at level 1 under a White, next to a White
    # 7-stack: his merge would make 9, the stacks are adjacent (no slide) -> pass.
    st = S({A: (BLACK, WHITE), B: (WHITE,) * 7}, BLACK)
    assert G.legal_moves(st) == ["pass"]
    st2 = G.apply_move(st, "pass")
    assert st2.to_move == WHITE and st2.board == st.board
    assert any(m != "pass" for m in G.legal_moves(st2)), "White can still move"

    # --- (7) serialize round-trip ---------------------------------------------
    st = S({A: (BLACK, WHITE, WHITE), (5, 4): (WHITE,)}, BLACK,
           scored={WHITE: 1, BLACK: 0})
    st.ply, st.since = 31, 7
    assert G.serialize(G.deserialize(G.serialize(st))) == G.serialize(st)

    # --- (8) 500 random playouts: all terminate, all decisive ----------------
    rng = random.Random(20050713)               # Byte's birthday
    results, plies = [0, 0, 0], []
    for _ in range(500):
        st = G.initial_state()
        n = 0
        while not G.is_terminal(st):
            st = G.apply_move(st, rng.choice(G.legal_moves(st)))
            n += 1
            assert n < 1200, "runaway game"
        plies.append(n)
        r = G.returns(st)
        results[0 if r[0] > 0 else (1 if r[1] > 0 else 2)] += 1
        # exactly three stacks of 8 exist in a finished game's accounting:
        assert sum(st.scored.values()) <= 3
        assert max(st.scored.values()) == 2, "winner has the majority"
    assert results[2] == 0, ("Byte is drawless; got draws", results)
    print(f"playouts: W {results[0]} / B {results[1]} / draws {results[2]}; "
          f"plies avg {sum(plies)/len(plies):.1f} min {min(plies)} max {max(plies)}")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
