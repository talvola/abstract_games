"""Hare and Hounds correctness anchor (pure stdlib -- imports only agp + this
game). There is no published perft; the anchor is baked rule asserts:

  (1) the standard 11-point board geometry (3x3 grid + left/right apex, with
      orthogonals plus the central-X diagonals) and its line-adjacency;
  (2) 3 Hounds vs 1 Hare; Hounds step one point along a line but may NOT move
      toward their own (left) end -- only vertically or toward the Hare's side;
      the Hare steps one point along any line in any direction;
  (3) the Hounds win by trapping the Hare (Hare has no legal move); the Hare
      wins by reaching the Hounds' far (left) end OR by the stalling rule
      (10 consecutive non-advancing Hound moves, counted across the turn
      alternation and not reset by the Hare).

Plus hand-built positions: a Hound no-retreat check, a Hare escape, a trap win,
and a stalling win. Fast (no game loops); run with PYTHONPATH=.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.hare_and_hounds.game import (  # noqa: E402
    HareAndHounds, HHState, POINTS, ADJ, LINES,
    HOUNDS, HARE, LEFT_APEX, RIGHT_APEX, CENTER, STALL_LIMIT,
)

G = HareAndHounds()


def main():
    # --- (1) board topology ----------------------------------------------
    assert len(POINTS) == 11, len(POINTS)
    assert LEFT_APEX == (0, 1) and RIGHT_APEX == (4, 1)
    assert CENTER == (2, 1)

    # adjacency symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p} {q}"

    # the central point joins all 4 grid corners (the central X) + 4 orthogonal
    # neighbours = degree 8
    assert ADJ[CENTER] == frozenset(
        {(1, 0), (3, 0), (1, 2), (3, 2), (2, 0), (2, 2), (1, 1), (3, 1)}
    ), sorted(ADJ[CENTER])

    # corners reach the centre diagonally; degree 3 (two orthogonal + the X)
    assert (2, 1) in ADJ[(1, 0)] and len(ADJ[(1, 0)]) == 3, sorted(ADJ[(1, 0)])
    assert (2, 1) in ADJ[(3, 2)] and len(ADJ[(3, 2)]) == 3, sorted(ADJ[(3, 2)])

    # NO diagonals in the outer cells: e.g. top-mid 2,0 does NOT touch 1,1 or 3,1
    assert (1, 1) not in ADJ[(2, 0)] and (3, 1) not in ADJ[(2, 0)], sorted(ADJ[(2, 0)])
    # left apex connects only to 1,1
    assert ADJ[LEFT_APEX] == frozenset({(1, 1)}), sorted(ADJ[LEFT_APEX])
    assert ADJ[RIGHT_APEX] == frozenset({(3, 1)}), sorted(ADJ[RIGHT_APEX])

    # lines list is non-empty and mirrors the undirected pair count
    assert len(LINES) == sum(len(v) for v in ADJ.values()) // 2, len(LINES)

    # --- (2) start position: 3 Hounds (left) + 1 Hare (right apex) --------
    st = G.initial_state()
    hounds = [p for p, v in st.board.items() if v == HOUNDS]
    hares = [p for p, v in st.board.items() if v == HARE]
    assert sorted(hounds) == [(1, 0), (1, 1), (1, 2)], hounds
    assert hares == [RIGHT_APEX], hares
    assert st.to_move == HOUNDS, "Hounds move first"

    # --- (2) Hound no-retreat: every legal Hound move keeps x >= source x --
    mv = G.legal_moves(st)
    assert mv, "Hounds must have opening moves"
    for m in mv:
        (fx, _), (tx, _) = _frto(m)
        assert tx >= fx, f"Hound retreated: {m}"
    # specifically a Hound on 1,1 may go forward to 2,1 but NOT backward to 0,1
    assert "1,1>2,1" in mv
    assert "1,1>0,1" not in mv  # 0,1 is toward their own end (smaller x) -> illegal

    # a sideways (vertical) Hound move is legal (same x): 1,0 has 1,1 occupied,
    # so test the centre-reaching diagonal forward and a vertical from an open col
    st2 = HHState(board={(2, 0): HOUNDS, (3, 2): HARE}, to_move=HOUNDS)
    m2 = set(G.legal_moves(st2))
    assert "2,0>2,1" in m2, m2          # vertical (down, same x) -> legal
    assert "2,0>3,0" in m2, m2          # forward along the top row (x increases) -> legal
    assert "2,0>1,0" not in m2, m2      # toward own end (x decreases) -> illegal

    # --- (2) Hare moves any direction along a line -----------------------
    sth = HHState(board={(2, 1): HARE}, to_move=HARE)
    hm = set(G.legal_moves(sth))
    # from the centre the Hare can reach all 8 neighbours
    assert hm == {f"2,1>{q[0]},{q[1]}" for q in ADJ[CENTER]}, sorted(hm)

    # --- (3) Hare escape: reaching the left apex 0,1 wins ----------------
    st_esc = HHState(board={(1, 1): HARE, (1, 0): HOUNDS, (1, 2): HOUNDS},
                     to_move=HARE)
    s_after = G.apply_move(st_esc, "1,1>0,1")
    assert s_after.winner == HARE, s_after.winner
    assert G.is_terminal(s_after)
    assert G.returns(s_after) == [-1.0, 1.0]

    # --- (3) trap win: Hare with no legal move -> Hounds win -------------
    # Hare on the right apex 4,1; its only neighbour 3,1 is occupied by a Hound.
    st_trap = HHState(board={(4, 1): HARE, (3, 1): HOUNDS}, to_move=HARE)
    assert G.legal_moves(st_trap) == [], "Hare should be trapped"
    assert G.is_terminal(st_trap)
    assert G.returns(st_trap) == [1.0, -1.0]  # Hounds win

    # --- (3) stalling win via REAL ALTERNATING PLAY ----------------------
    # Regression for the dead-stalling-rule bug: the counter must track
    # CONSECUTIVE non-advancing Hound moves and must NOT be reset by the Hare's
    # intervening turns. We drive a normal (hound, hare, hound, hare, ...)
    # sequence from a regular position: a lone Hound shuffles vertically in an
    # empty column (3,1 <-> 3,0, same x -> non-advancing) while the Hare harmlessly
    # bounces along the top row (1,0 <-> 2,0, never reaching the 0,1 escape).
    # The stall win must fire on the 10th non-advancing Hound move purely from
    # apply_move -- never via a hand-built near-limit state.
    s = HHState(board={(3, 1): HOUNDS, (1, 0): HARE}, to_move=HOUNDS, vstalls=0)
    hound_toggle = ("3,1>3,0", "3,0>3,1")   # vertical bounce, same x (non-advancing)
    hare_toggle = ("1,0>2,0", "2,0>1,0")    # harmless bounce, never the escape apex
    for i in range(STALL_LIMIT):
        # Hound makes a non-advancing (vertical) move.
        before = s.vstalls
        s = G.apply_move(s, hound_toggle[i % 2])
        if s.winner is not None:
            # The win must land exactly on the STALL_LIMIT-th non-advancing move.
            assert i == STALL_LIMIT - 1, (i, s.vstalls)
            assert s.vstalls >= STALL_LIMIT, s.vstalls
            assert s.winner == HARE, s.winner
            break
        assert s.vstalls == before + 1, (s.vstalls, before)
        # Hare moves: the counter MUST survive its turn unchanged (the core of
        # the fixed bug).
        carried = s.vstalls
        s = G.apply_move(s, hare_toggle[i % 2])
        assert s.vstalls == carried, (
            "Hare's move must NOT reset the Hound stall counter", s.vstalls, carried)
        assert s.winner is None, s.winner
    else:  # pragma: no cover - the loop must break on the stall win
        raise AssertionError("stalling rule never fired in alternating play")
    assert s.winner == HARE, s.winner
    assert G.returns(s) == [-1.0, 1.0]

    # an advancing (forward, x-increasing) Hound move resets the stall counter
    s = HHState(board={(1, 1): HOUNDS, (3, 0): HARE}, to_move=HOUNDS, vstalls=5)
    s = G.apply_move(s, "1,1>2,1")   # forward (x increases) -> advancing
    assert s.vstalls == 0, s.vstalls
    assert s.winner is None

    # --- serialize round-trips -------------------------------------------
    s = G.apply_move(G.initial_state(), G.legal_moves(G.initial_state())[0])
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


def _frto(move):
    fs, ts = move.split(">")
    fx, fy = (int(t) for t in fs.split(","))
    tx, ty = (int(t) for t in ts.split(","))
    return (fx, fy), (tx, ty)


if __name__ == "__main__":
    main()
