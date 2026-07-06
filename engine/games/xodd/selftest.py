"""Xodd correctness anchor (pure stdlib -- imports only agp + this game).

Xodd (Luis Bolaños Mures, 2011) has no published perft, so the anchor is the
mindsports ruleset (https://mindsports.nl/index.php/the-pit/624-xodd) baked as
plain asserts:

* group counting: ORTHOGONALLY connected like-coloured stones only -- a merge
  reduces the count correctly and a diagonal touch does NOT join;
* Black's opening turn is single-stone only and pass is illegal on turn 1;
* parity legality: any move sequence must leave an ODD total group count at
  turn end -- "end" is only offered when the total is odd, every offered
  placement mid-turn restores odd, and a first stone that leaves an even total
  with no parity-fixing second placement is not offered at all;
* two passes in succession end the game and the player with FEWER groups of
  their own colour wins (winner differs when the counts differ; no draws);
* a full random playout on the default 9x9 board terminates.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.xodd.game import (  # noqa: E402
    Xodd, XoddState, BLACK, WHITE, _label, _cells,
)

G = Xodd()


def main():
    # --- (c) group counting: orthogonal-only flood fill -------------------
    # two stones a gap apart = 2 groups; filling the gap merges them into 1
    _, total, b, w = _label({(0, 0): BLACK, (0, 2): BLACK})
    assert (total, b, w) == (2, 2, 0), (total, b, w)
    _, total, b, w = _label({(0, 0): BLACK, (0, 1): BLACK, (0, 2): BLACK})
    assert (total, b, w) == (1, 1, 0), "merge across the gap should give 1 group"
    # a DIAGONAL touch does NOT join (square grid, orthogonal adjacency)
    _, total, b, w = _label({(0, 0): BLACK, (1, 1): BLACK})
    assert (total, b, w) == (2, 2, 0), "diagonal stones must be separate groups"
    # unlike colours never join even orthogonally
    _, total, b, w = _label({(0, 0): BLACK, (0, 1): WHITE})
    assert (total, b, w) == (2, 1, 1), (total, b, w)
    # a stone joining TWO like groups: 3 groups -> place the bridge -> 2
    _, total, b, w = _label({(0, 0): BLACK, (0, 2): BLACK, (5, 5): WHITE})
    assert total == 3, total
    _, total, b, w = _label({(0, 0): BLACK, (0, 1): BLACK, (0, 2): BLACK,
                             (5, 5): WHITE})
    assert (total, b, w) == (2, 1, 1), "bridge should merge two black groups"

    # --- (b) opening turn: one stone only, no pass, no end ----------------
    s0 = G.initial_state()
    assert s0.size == 9 and len(_cells(9)) == 81
    m0 = G.legal_moves(s0)
    assert "pass" not in m0, "Black cannot pass on turn 1"
    assert "end" not in m0
    # every cell, either colour, is a legal single placement (each gives 1 group)
    assert len(m0) == 81 * 2, len(m0)
    assert all("=" in m for m in m0)
    s1 = G.apply_move(s0, "4,4=black")
    assert s1.to_move == WHITE, "opening turn must end after ONE stone"
    assert s1.turn_cells == [] and not s1.over

    # --- (a) parity legality, mid-turn (placed == 1) ----------------------
    # even total (2) after a first stone: "end" must NOT be offered, and every
    # offered second placement must restore an odd total.
    s = XoddState(size=9, board={(0, 0): BLACK, (4, 4): WHITE},
                  to_move=BLACK, turn_cells=["4,4"])
    moves = G.legal_moves(s)
    assert "end" not in moves, "ending on an even total must be illegal"
    assert "pass" not in moves
    assert moves, "player must never be stranded mid-turn"
    # black at 0,1 would MERGE into the 0,0 black group: total stays 2 (even)
    assert "0,1=black" not in moves, "placement leaving an even total is illegal"
    # white at 0,1 starts a new group: total 3 (odd) -> legal
    assert "0,1=white" in moves
    for m in moves:
        _, total2, _, _ = _label(G.apply_move(s, m).board)
        assert total2 % 2 == 1, f"second stone {m} left an even total {total2}"

    # odd total (3) after a first stone: "end" IS offered
    s = XoddState(size=9, board={(0, 0): BLACK, (4, 4): WHITE, (8, 8): WHITE},
                  to_move=BLACK, turn_cells=["8,8"])
    moves = G.legal_moves(s)
    assert "end" in moves
    s2 = G.apply_move(s, "end")
    assert s2.to_move == WHITE and s2.turn_cells == [] and not s2.over

    # --- (a) parity legality, first stone with NO parity fix available ----
    # 2x2 board, one black group of 3, one empty cell. A white stone there
    # makes the total 2 (even) with no second placement possible -> the move
    # must not be offered; the black stone (merging, total stays 1) is fine.
    s = XoddState(size=2, board={(0, 0): BLACK, (0, 1): BLACK, (1, 0): BLACK},
                  to_move=WHITE, turn_cells=[])
    moves = G.legal_moves(s)
    assert "pass" in moves, "total is odd, pass must be legal"
    assert "1,1=black" in moves, "joining placement keeps the total odd"
    assert "1,1=white" not in moves, \
        "even-leaving first stone with no parity-fixing second must be illegal"

    # --- (d) two passes end the game; FEWER own groups wins ---------------
    # black 1 group vs white 2 -> Black wins
    s = XoddState(size=9, board={(0, 0): BLACK, (2, 2): WHITE, (4, 4): WHITE},
                  to_move=WHITE)
    assert "pass" in G.legal_moves(s)
    s = G.apply_move(s, "pass")
    assert not s.over and s.passes == 1 and s.to_move == BLACK
    assert "pass" in G.legal_moves(s)
    s = G.apply_move(s, "pass")
    assert s.over and G.is_terminal(s)
    assert s.winner == BLACK, s.winner
    assert G.returns(s) == [1.0, -1.0]
    assert G.legal_moves(s) == []
    # mirror: black 2 groups vs white 1 -> White wins (winner tracks the counts)
    s = XoddState(size=9, board={(0, 0): BLACK, (2, 2): BLACK, (4, 4): WHITE},
                  to_move=BLACK)
    s = G.apply_move(s, "pass")
    s = G.apply_move(s, "pass")
    assert s.winner == WHITE and G.returns(s) == [-1.0, 1.0]
    # a placement between two passes resets the pass count (no premature end)
    s = XoddState(size=9, board={(0, 0): BLACK, (2, 2): WHITE, (4, 4): WHITE},
                  to_move=WHITE)
    s = G.apply_move(s, "pass")
    s = G.apply_move(s, "7,7=black")     # total 4 -> even, mid-turn
    assert s.passes == 0 and not s.over
    s = G.apply_move(s, "7,0=white")     # total 5 -> odd, turn auto-ends (cap 2)
    assert s.to_move == WHITE and s.turn_cells == [] and not s.over

    # --- serialize round-trips --------------------------------------------
    s = G.apply_move(G.initial_state(), "4,4=black")
    s = G.apply_move(s, "3,3=white")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    # --- render shape (square board, generic renderer contract) -----------
    spec = G.render(s)
    assert spec["board"] == {"type": "square", "width": 9, "height": 9}
    assert all({"cell", "owner"} <= set(p) for p in spec["pieces"])
    assert isinstance(spec["caption"], str)

    # --- (e) a full random playout terminates ------------------------------
    rng = random.Random(42)
    s = G.initial_state()
    plies = 0
    while not G.is_terminal(s):
        moves = G.legal_moves(s)
        assert moves, "non-terminal state with no legal moves"
        s = G.apply_move(s, rng.choice(moves))
        plies += 1
        assert plies < 2000, "random playout did not terminate"
        # invariant: at the START of every turn the total is odd (or board empty)
        if not s.over and not s.turn_cells and s.board:
            _, total3, _, _ = _label(s.board)
            assert total3 % 2 == 1, f"turn ended on an even total {total3}"
    _, _, b, w = _label(s.board)
    assert b != w, "group counts can never tie (total is odd)"
    assert s.winner == (BLACK if b < w else WHITE), (s.winner, b, w)
    assert sorted(G.returns(s)) == [-1.0, 1.0]

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
