"""Teeko correctness anchor (pure stdlib -- imports only agp + this game).

There is no published perft for Teeko, so the anchor is a set of the rules baked
as plain asserts:

* DROP phase: each player places exactly four markers on empty cells,
  alternating; the phase ends after eight drops.
* MOVE phase: a marker slides to one of the up-to-eight ADJACENT empty cells
  (the eight king-step neighbours).
* WIN = your four markers form a straight line of four (horizontal, vertical, or
  either diagonal) OR a 2x2 square; checked after every drop and every move.
* a hand-built straight-line win, a hand-built 2x2-square win, and a rejection of
  a bent / non-winning 4-shape;
* a handful of rule-specific positions (no capture, draw cap, serialize
  round-trip, a win reached during the drop phase, a win reached by a slide).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.teeko.game import (  # noqa: E402
    Teeko, TState, CELLS, ADJ, WIN_SHAPES, SIZE, MARKERS,
)

G = Teeko()


def main():
    # --- topology --------------------------------------------------------
    assert SIZE == 5 and MARKERS == 4
    assert len(CELLS) == 25, len(CELLS)

    # --- adjacency = 8 king-step neighbours ------------------------------
    # centre cell has all 8 neighbours
    assert ADJ["2,2"] == frozenset({
        "1,1", "2,1", "3,1", "1,2", "3,2", "1,3", "2,3", "3,3"}), ADJ["2,2"]
    # a corner has exactly 3
    assert ADJ["0,0"] == frozenset({"1,0", "0,1", "1,1"}), ADJ["0,0"]
    assert ADJ["4,4"] == frozenset({"3,4", "4,3", "3,3"}), ADJ["4,4"]
    # an edge (non-corner) cell has exactly 5
    assert ADJ["2,0"] == frozenset({
        "1,0", "3,0", "1,1", "2,1", "3,1"}), ADJ["2,0"]
    # every adjacency is symmetric and never includes the cell itself
    for c in CELLS:
        assert c not in ADJ[c], c
        for q in ADJ[c]:
            assert c in ADJ[q], f"asymmetric {c},{q}"
        # in-bounds king step => at most 8 neighbours
        assert 3 <= len(ADJ[c]) <= 8, (c, len(ADJ[c]))

    # --- winning shapes: count + composition -----------------------------
    # Lines of four on a 5x5:
    #   horizontal: 2 starts/row * 5 rows           = 10
    #   vertical:   2 starts/col * 5 cols           = 10
    #   "\" diagonal: a 2x2 grid of starts          =  4
    #   "/" diagonal: a 2x2 grid of starts          =  4
    #   total lines                                 = 28
    # 2x2 squares: 4*4 top-left corners             = 16
    # grand total                                   = 44
    assert len(WIN_SHAPES) == 44, len(WIN_SHAPES)
    assert len(set(WIN_SHAPES)) == 44, "duplicate win shapes"
    for sh in WIN_SHAPES:
        assert len(sh) == MARKERS, sh

    # explicit examples of each kind are present
    assert frozenset({"0,0", "1,0", "2,0", "3,0"}) in WIN_SHAPES   # horizontal
    assert frozenset({"4,1", "4,2", "4,3", "4,4"}) in WIN_SHAPES   # vertical
    assert frozenset({"0,0", "1,1", "2,2", "3,3"}) in WIN_SHAPES   # "\" diag
    assert frozenset({"3,0", "2,1", "1,2", "0,3"}) in WIN_SHAPES   # "/" diag
    assert frozenset({"1,1", "2,1", "1,2", "2,2"}) in WIN_SHAPES   # 2x2 square

    # --- _is_win: line, square, and rejection of a bent shape ------------
    # hand-built straight-line win (horizontal)
    line_pos = {"0,2": 0, "1,2": 0, "2,2": 0, "3,2": 0}
    assert G._is_win(line_pos, 0), "horizontal line-of-four not a win"
    # a diagonal line win
    diag_pos = {"1,1": 1, "2,2": 1, "3,3": 1, "4,4": 1}
    assert G._is_win(diag_pos, 1), "diagonal line-of-four not a win"
    # hand-built 2x2-square win
    sq_pos = {"2,2": 0, "3,2": 0, "2,3": 0, "3,3": 0}
    assert G._is_win(sq_pos, 0), "2x2 square not a win"
    # a BENT / non-winning 4-shape must NOT be a win:
    #   an L / zig-zag of four contiguous-but-not-aligned cells
    bent = {"0,0": 0, "1,0": 0, "2,0": 0, "2,1": 0}     # three-in-row + a tail
    assert not G._is_win(bent, 0), "bent shape wrongly counted as a win"
    # a "broken line" (gap in the middle) is not a win either
    broken = {"0,0": 0, "1,0": 0, "3,0": 0, "4,0": 0}
    assert not G._is_win(broken, 0), "broken line wrongly a win"
    # a 1x4 with a wrong cell -> not aligned, not square
    notwin = {"0,0": 0, "1,0": 0, "2,0": 0, "0,1": 0}
    assert not G._is_win(notwin, 0), "non-shape wrongly a win"
    # three in a row is NOT a win (needs four)
    assert not G._is_win({"0,0": 0, "1,0": 0, "2,0": 0}, 0), "3 wrongly a win"
    # mixed ownership across a winning shape is not a win for either
    mixed = {"0,0": 0, "1,0": 0, "2,0": 0, "3,0": 1}
    assert not G._is_win(mixed, 0) and not G._is_win(mixed, 1), "mixed win"

    # --- DROP phase: exactly 4 each, alternating, on empty cells ---------
    st = G.initial_state()
    assert st.to_move == 0 and st.placed == [0, 0]
    # at the start every move is a single-cell drop onto any empty cell
    assert all(">" not in m for m in G.legal_moves(st)), "phase-1 = drops"
    assert set(G.legal_moves(st)) == set(CELLS), "all empty cells droppable"
    # play 8 alternating drops that do NOT form a winning shape
    seq = ["0,0", "4,4", "2,0", "4,3", "0,4", "4,2", "4,0", "0,2"]
    s = G.initial_state()
    expect_player = 0
    for i, mv in enumerate(seq):
        assert ">" not in mv
        assert G.current_player(s) == expect_player, (i, G.current_player(s))
        # the dropped cell must currently be empty
        assert mv not in s.pos, f"drop {mv} onto occupied cell"
        s = G.apply_move(s, mv)
        assert s.winner is None, f"unexpected early win at drop {i}"
        expect_player = 1 - expect_player
    assert s.placed == [4, 4], s.placed
    # each player owns exactly 4 markers
    assert sum(1 for v in s.pos.values() if v == 0) == 4
    assert sum(1 for v in s.pos.values() if v == 1) == 4

    # --- MOVE phase: every legal move is an adjacent slide to empty -------
    mv = G.legal_moves(s)
    assert mv and all(">" in m for m in mv), "phase-2 = slides"
    for m in mv:
        frm, to = m.split(">")
        assert s.pos.get(frm) == s.to_move, "must move own marker"
        assert to not in s.pos, "must move to empty cell"
        assert to in ADJ[frm], f"slide {m} not a king-step"

    # --- a win reached DURING the drop phase -----------------------------
    # P0 drops three corners of a 2x2 then the fourth completes it.
    s = G.initial_state()
    s = G.apply_move(s, "1,1")   # P0
    s = G.apply_move(s, "0,0")   # P1
    s = G.apply_move(s, "2,1")   # P0
    s = G.apply_move(s, "0,1")   # P1
    s = G.apply_move(s, "1,2")   # P0   (three corners of the 2x2 at 1,1)
    s = G.apply_move(s, "0,2")   # P1
    assert s.winner is None
    s = G.apply_move(s, "2,2")   # P0 completes the 2x2 square -> win on a drop
    assert s.winner == 0, f"winner={s.winner}"
    assert G.is_terminal(s) and G.returns(s) == [1.0, -1.0]
    assert G.legal_moves(s) == [], "no moves once terminal"

    # --- a win reached BY A SLIDE in the movement phase ------------------
    # P0 markers on 0,2 1,2 2,2 and 4,4; slide 4,4->3,3? no. Instead set up a
    # line-of-four needing one slide: P0 on 0,2 1,2 2,2 and 4,3; slide 4,3->3,2
    # completes the horizontal row 0,2 1,2 2,2 3,2.
    s = TState(
        pos={"0,2": 0, "1,2": 0, "2,2": 0, "4,3": 0,
             "0,0": 1, "1,0": 1, "2,0": 1, "3,0": 1},
        to_move=0, placed=[4, 4], move_plies=2)
    # (P1's markers happen to be a winning row, but P1 didn't just move, so the
    # state has winner=None; this only exercises P0's slide.)
    assert "4,3>3,2" in G.legal_moves(s), G.legal_moves(s)
    s2 = G.apply_move(s, "4,3>3,2")
    assert s2.winner == 0, f"winner={s2.winner}"
    assert G.is_terminal(s2)

    # --- no capture: opponent markers are never removed ------------------
    s = TState(
        pos={"0,0": 0, "2,2": 0, "4,0": 0, "0,4": 0,
             "1,1": 1, "3,3": 1, "1,3": 1, "3,1": 1},
        to_move=0, placed=[4, 4])
    before = sum(1 for v in s.pos.values() if v == 1)
    for m in G.legal_moves(s):
        ns = G.apply_move(s, m)
        after = sum(1 for v in ns.pos.values() if v == 1)
        assert after == before, "opponent marker removed -- no captures allowed"
        # total marker count is conserved (a slide neither adds nor drops)
        assert len(ns.pos) == len(s.pos), "marker count changed on a slide"

    # --- draw cap guarantees termination ---------------------------------
    s = TState(
        pos={"0,0": 0, "2,2": 0, "4,0": 0, "0,4": 0,
             "1,1": 1, "3,3": 1, "1,3": 1, "3,1": 1},
        to_move=0, placed=[4, 4], move_plies=G.DRAW_MOVE_PLIES)
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0], "draw cap not enforced"
    assert G.legal_moves(s) == [], "terminal state must offer no moves"

    # --- serialize round-trips -------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(), "1,1"), "3,3")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
