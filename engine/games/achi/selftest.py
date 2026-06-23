"""Achi correctness anchor (pure stdlib -- imports only agp + this game).

There is no published perft for Achi, so the anchor is the ruleset baked as plain
asserts:

* topology: a 3x3 board of 9 points with the 8 standard lines (3 rows, 3 cols,
  2 diagonals) and orthogonal+diagonal sliding adjacency along those lines;
* each player has FOUR pieces;
* a PLACEMENT phase (alternately drop your 4 -- eight in total -- leaving exactly
  one empty point) then a MOVEMENT phase (slide a piece one step along a line into
  the single empty adjacent point);
* WIN = three of your pieces in a row along any of the 8 lines (or the opponent
  being left with no legal move);
* a hand-built placement-phase three-in-a-row win and a movement-phase slide win,
  plus a few rule-specific positions (no capture, stuck-loses, draw cap,
  serialize round-trip).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.achi.game import (  # noqa: E402
    Achi, AState, POINTS, ADJ, LINES, MEN,
)

G = Achi()


def main():
    # --- pieces per player: FOUR (distinguishes Achi from Tapatan's three) ---
    assert MEN == 4, MEN
    assert G.MEN == 4, G.MEN

    # --- topology: 9 points and 8 lines ----------------------------------
    assert len(POINTS) == 9, len(POINTS)
    assert len(LINES) == 8, len(LINES)         # 3 rows + 3 cols + 2 diagonals
    expected_lines = {
        frozenset({"0,0", "1,0", "2,0"}),      # rows
        frozenset({"0,1", "1,1", "2,1"}),
        frozenset({"0,2", "1,2", "2,2"}),
        frozenset({"0,0", "0,1", "0,2"}),      # cols
        frozenset({"1,0", "1,1", "1,2"}),
        frozenset({"2,0", "2,1", "2,2"}),
        frozenset({"0,0", "1,1", "2,2"}),      # main diagonal
        frozenset({"2,0", "1,1", "0,2"}),      # anti-diagonal
    }
    assert {frozenset(ln) for ln in LINES} == expected_lines, "line set wrong"

    # --- adjacency for sliding (orthogonal + diagonal along the 8 lines) --
    # centre adjacent to all 8 outer points
    assert ADJ["1,1"] == frozenset(p for p in POINTS if p != "1,1"), ADJ["1,1"]
    # corners: 2 edge-midpoints + centre (the centre link is the diagonal)
    corner_adj = {
        "0,0": {"1,0", "0,1", "1,1"},
        "2,0": {"1,0", "2,1", "1,1"},
        "0,2": {"0,1", "1,2", "1,1"},
        "2,2": {"2,1", "1,2", "1,1"},
    }
    for c, exp in corner_adj.items():
        assert ADJ[c] == frozenset(exp), (c, ADJ[c])
    # edge-midpoints: 2 corners + centre
    edge_adj = {
        "1,0": {"0,0", "2,0", "1,1"},
        "0,1": {"0,0", "0,2", "1,1"},
        "2,1": {"2,0", "2,2", "1,1"},
        "1,2": {"0,2", "2,2", "1,1"},
    }
    for e, exp in edge_adj.items():
        assert ADJ[e] == frozenset(exp), (e, ADJ[e])
    # corners are NOT adjacent to each other
    for a in ("0,0", "2,0", "0,2", "2,2"):
        for b in ("0,0", "2,0", "0,2", "2,2"):
            if a != b:
                assert b not in ADJ[a], f"{a},{b} should not be adjacent"
    # adjacency is symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- a 3-in-a-row on EACH of the 8 lines is a win --------------------
    for ln in LINES:
        assert G._is_line({q: 0 for q in ln}, 0), f"line {ln} not a win for 0"
        assert G._is_line({q: 1 for q in ln}, 1), f"line {ln} not a win for 1"
        mixed = {q: 0 for q in ln}
        mixed[ln[0]] = 1
        assert not G._is_line(mixed, 0) and not G._is_line(mixed, 1), \
            f"mixed line {ln} wrongly a win"

    # --- placement -> movement boundary: FOUR each, ONE empty point ------
    st = G.initial_state()
    assert all(">" not in m for m in G.legal_moves(st)), "phase-1 should be placements"
    assert set(G.legal_moves(st)) == set(POINTS), "all empty points placeable"
    # eight alternating placements that do NOT form a line:
    #   P0: 0,0 / 2,0 / 0,2 / 2,2 (the four corners)
    #   P1: 1,0 / 0,1 / 2,1 / 1,2 (the four edge-midpoints)
    # leaving the centre 1,1 empty. No line is completed by either side.
    seq = ["0,0", "1,0", "2,0", "0,1", "0,2", "2,1", "2,2", "1,2"]
    s = G.initial_state()
    for i, mv in enumerate(seq):
        assert ">" not in mv
        s = G.apply_move(s, mv)
        assert s.winner is None, f"unexpected early win at step {i}"
    assert s.placed == [MEN, MEN], s.placed
    # exactly one point empty
    empties = [p for p in POINTS if p not in s.pos]
    assert empties == ["1,1"], empties
    assert len(s.pos) == 8, len(s.pos)
    # now every legal move is a slide along adjacency into the single empty point
    mv = G.legal_moves(s)
    assert mv and all(">" in m for m in mv), "phase-2 should be slides"
    for m in mv:
        frm, to = m.split(">")
        assert s.pos.get(frm) == s.to_move, "must move own piece"
        assert to == "1,1", "must slide into the single empty point"
        assert to in ADJ[frm], f"slide {m} not along adjacency"

    # --- PLACEMENT-PHASE three-in-a-row win ------------------------------
    # P0 builds the main diagonal during placement; P1 fails to block 2,2.
    s = G.initial_state()
    s = G.apply_move(s, "0,0")   # P0
    s = G.apply_move(s, "1,0")   # P1
    s = G.apply_move(s, "1,1")   # P0  (diagonal 0,0 + 1,1, needs 2,2)
    s = G.apply_move(s, "0,1")   # P1  (does not block 2,2)
    assert s.winner is None
    s = G.apply_move(s, "2,2")   # P0 completes the main diagonal -> win
    assert s.winner == 0, f"winner={s.winner}"
    assert s.placed == [3, 2], s.placed   # P0 won having placed only 3 so far
    assert G.is_terminal(s) and G.returns(s) == [1.0, -1.0]
    assert G.legal_moves(s) == [], "no moves once terminal"

    # --- MOVEMENT-PHASE win by sliding into the empty point --------------
    # 8 pieces down, 1,1 empty. P0 = 0,0 / 2,2 / 1,0 / 0,1 ; P1 = 2,0 / 2,1 /
    # 0,2 / 1,2. P0 slides 1,0->1,1 to complete the main diagonal 0,0-1,1-2,2.
    s = AState(pos={"0,0": 0, "2,2": 0, "1,0": 0, "0,1": 0,
                    "2,0": 1, "2,1": 1, "0,2": 1, "1,2": 1},
               to_move=0, placed=[MEN, MEN], move_plies=6)
    assert sum(1 for v in s.pos.values() if v == 0) == 4
    assert sum(1 for v in s.pos.values() if v == 1) == 4
    assert [p for p in POINTS if p not in s.pos] == ["1,1"]
    assert "1,0>1,1" in G.legal_moves(s), G.legal_moves(s)
    s2 = G.apply_move(s, "1,0>1,1")
    assert s2.winner == 0, f"winner={s2.winner}"
    assert G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0]

    # --- no capture: opponent pieces are never removed -------------------
    before = sum(1 for v in s.pos.values() if v == 1)
    for m in G.legal_moves(s):
        after = sum(1 for v in G.apply_move(s, m).pos.values() if v == 1)
        assert after == before, "opponent piece removed -- captures not allowed"

    # --- stuck player loses (no legal slide on their turn) ---------------
    # Empty = 0,0 (neighbours 1,0 / 0,1 / 1,1). P0 owns all three neighbours, so
    # the side to move (P1) has no piece adjacent to the empty point -> P1 loses.
    stuck = AState(pos={"1,0": 0, "0,1": 0, "1,1": 0, "2,2": 0,
                        "2,0": 1, "2,1": 1, "0,2": 1, "1,2": 1},
                   to_move=1, placed=[MEN, MEN], move_plies=10)
    assert [p for p in POINTS if p not in stuck.pos] == ["0,0"]
    assert not G._is_line(stuck.pos, 0) and not G._is_line(stuck.pos, 1), \
        "stuck test position must not already contain a line"
    assert G._slides(stuck, 1) == [], "P1 should have no slides here"
    assert G.legal_moves(stuck) == [], "stuck player has no legal moves"
    # reach the stuck state via a real move so the no-move loss is credited:
    # P0 at 1,1 slides nowhere useful... instead verify via apply_move that
    # leaving the opponent with no move sets the winner. Build a position where
    # P0's move strands P1: P0 = 0,1 / 1,1 / 2,2 / (a piece to move) ; we move
    # a P0 piece into 1,0 to seal 0,0's last friendly-for-P1 neighbour.
    pre = AState(pos={"0,0": 0, "0,1": 0, "1,1": 0, "2,2": 0,
                      "2,0": 1, "2,1": 1, "0,2": 1, "1,2": 1},
                 to_move=0, placed=[MEN, MEN], move_plies=10)
    # empty point is 1,0 (neighbours 0,0 / 2,0 / 1,1); P0 slides 0,0->1,0.
    assert [p for p in POINTS if p not in pre.pos] == ["1,0"]
    assert "0,0>1,0" in G.legal_moves(pre)
    after = G.apply_move(pre, "0,0>1,0")
    # now empty = 0,0 (neighbours 1,0[P0] / 0,1[P0] / 1,1[P0]); P1 to move stuck.
    assert [p for p in POINTS if p not in after.pos] == ["0,0"]
    assert not G._is_line(after.pos, 0), "P0 must not have won by a line here"
    assert after.winner == 0, f"stuck-loss not credited: winner={after.winner}"
    assert G.is_terminal(after) and G.returns(after) == [1.0, -1.0]

    # --- draw cap guarantees termination ---------------------------------
    s = AState(pos={"0,0": 0, "2,2": 0, "1,0": 0, "0,1": 0,
                    "2,0": 1, "2,1": 1, "0,2": 1, "1,2": 1},
               to_move=0, placed=[MEN, MEN], move_plies=G.DRAW_MOVE_PLIES)
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0], "draw cap not enforced"
    assert G.legal_moves(s) == [], "terminal state must offer no moves"

    # --- serialize round-trips -------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(), "0,0"), "2,2")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
