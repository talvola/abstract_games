"""Tapatan correctness anchor (pure stdlib -- imports only agp + this game).

There is no published perft for Tapatan, so the anchor is an exhaustive set of
the rules baked as plain asserts:

* a three-in-a-row on each of the eight lines (3 rows, 3 cols, 2 diagonals) is a
  win;
* sliding adjacency is exactly: centre <-> all 8 outer points, each corner <->
  its 2 edge-midpoints + centre, each edge-midpoint <-> its 2 corners + centre,
  and corners are never adjacent to each other;
* the placement -> movement phase boundary: each side places exactly 3 men, then
  may only slide along adjacency;
* a short forced sequence that reaches a win;
* a handful of rule-specific positions (no capture, draw cap, serialize
  round-trip).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.tapatan.game import (  # noqa: E402
    Tapatan, TState, POINTS, ADJ, LINES,
)

G = Tapatan()


def main():
    # --- topology: points and lines --------------------------------------
    assert len(POINTS) == 9, len(POINTS)
    assert len(LINES) == 8, len(LINES)         # 3 rows + 3 cols + 2 diagonals
    # the eight expected lines, as sets
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

    # --- adjacency for sliding -------------------------------------------
    # centre adjacent to all 8 outer points
    assert ADJ["1,1"] == frozenset(p for p in POINTS if p != "1,1"), ADJ["1,1"]
    # corners: 2 edge-midpoints + centre
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
        pos = {q: 0 for q in ln}
        assert G._is_line(pos, 0), f"line {ln} not detected as a win"
        # owned by the other player too
        pos2 = {q: 1 for q in ln}
        assert G._is_line(pos2, 1), f"line {ln} not detected for player 1"
        # mixed ownership is NOT a win
        mixed = dict(pos)
        mixed[ln[0]] = 1
        assert not G._is_line(mixed, 0) and not G._is_line(mixed, 1), \
            f"mixed line {ln} wrongly a win"

    # --- placement -> movement phase boundary ----------------------------
    # from the start, all moves are single-point placements
    st = G.initial_state()
    assert all(">" not in m for m in G.legal_moves(st)), "phase-1 should be placements"
    assert set(G.legal_moves(st)) == set(POINTS), "all empty points placeable"
    # play 6 alternating placements that do NOT form a line, then we must be in
    # movement: P0 on 0,0 / 0,2 / 2,1 ; P1 on 1,1 / 1,0 / 2,2  (no 3-in-line)
    seq = ["0,0", "1,1", "0,2", "1,0", "2,1", "2,2"]
    s = G.initial_state()
    for i, mv in enumerate(seq):
        assert ">" not in mv
        s = G.apply_move(s, mv)
        # no winner before all placed (none of these is a completed line)
        assert s.winner is None, f"unexpected early win at step {i}"
    assert s.placed == [3, 3], s.placed
    # now every legal move is a slide along adjacency to an empty point
    mv = G.legal_moves(s)
    assert mv and all(">" in m for m in mv), "phase-2 should be slides"
    for m in mv:
        frm, to = m.split(">")
        assert s.pos.get(frm) == s.to_move, "must move own man"
        assert to not in s.pos, "must move to empty point"
        assert to in ADJ[frm], f"slide {m} not along adjacency"

    # --- short forced sequence that reaches a win (during placement) -----
    # P0 places 0,0 then 1,1; threatens the main diagonal at 2,2. P1 cannot
    # occupy 2,2 in time if it stays empty: P0 places 2,2 and completes it.
    s = G.initial_state()
    s = G.apply_move(s, "0,0")   # P0
    s = G.apply_move(s, "1,0")   # P1
    s = G.apply_move(s, "1,1")   # P0  (diagonal 0,0 + 1,1, needs 2,2)
    s = G.apply_move(s, "0,1")   # P1  (does not block 2,2)
    assert s.winner is None
    s = G.apply_move(s, "2,2")   # P0 completes the main diagonal -> win
    assert s.winner == 0, f"winner={s.winner}"
    assert G.is_terminal(s) and G.returns(s) == [1.0, -1.0]
    assert G.legal_moves(s) == [], "no moves once terminal"

    # --- a win in the MOVEMENT phase by sliding --------------------------
    # P0 men on 0,0 and 2,2 (diagonal ends), one man on 1,0; centre 1,1 empty.
    # P0 slides 1,0->1,1 to complete the main diagonal.
    s = TState(pos={"0,0": 0, "2,2": 0, "1,0": 0,
                    "0,1": 1, "2,1": 1, "1,2": 1},
               to_move=0, placed=[3, 3], move_plies=4)
    assert "1,0>1,1" in G.legal_moves(s), G.legal_moves(s)
    s2 = G.apply_move(s, "1,0>1,1")
    assert s2.winner == 0, f"winner={s2.winner}"

    # --- no capture: opponent men are never removed ----------------------
    s = TState(pos={"0,0": 0, "1,1": 1, "0,1": 0, "2,1": 1, "1,0": 0, "1,2": 1},
               to_move=0, placed=[3, 3])
    before = sum(1 for v in s.pos.values() if v == 1)
    # any legal slide keeps all of P1's men on the board
    for m in G.legal_moves(s):
        after = sum(1 for v in G.apply_move(s, m).pos.values() if v == 1)
        assert after == before, "opponent man was removed -- captures not allowed"

    # --- draw cap guarantees termination ---------------------------------
    s = TState(pos={"0,0": 0, "2,2": 0, "1,0": 0, "0,2": 1, "2,0": 1, "1,2": 1},
               to_move=0, placed=[3, 3], move_plies=G.DRAW_MOVE_PLIES)
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0], "draw cap not enforced"
    assert G.legal_moves(s) == [], "terminal state must offer no moves"

    # --- serialize round-trips -------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(), "0,0"), "2,2")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
