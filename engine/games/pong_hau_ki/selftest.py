"""Pong Hau K'i correctness anchor (pure stdlib -- imports only agp + this game).

There is no published perft for Pong Hau K'i, so the anchor is the verified
board facts baked as plain assertions:
  (1) the standard 5-point / 7-edge board (centre joined to all four corners;
      three of the four square sides are edges; exactly the top side tl-tr is
      NOT an edge);
  (2) each player has two stones; four points start occupied, one empty;
  (3) a move slides one stone along an edge into the single empty point; no
      captures;
  (4) WIN = the opponent cannot move (both their stones blocked) -- reached via
      apply_move, plus a hand-built blocking win.
Fast (no game loops)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.pong_hau_ki.game import (  # noqa: E402
    PongHauKi, PState, POINTS, EDGES, ADJ,
)

G = PongHauKi()


def main():
    # --- topology: 5 nodes, 7 edges -------------------------------------------
    assert len(POINTS) == 5, POINTS
    assert set(POINTS) == {"tl", "tr", "bl", "br", "c"}, POINTS
    assert len(EDGES) == 7, EDGES
    # undirected edges are unique
    norm = {frozenset(e) for e in EDGES}
    assert len(norm) == 7, "edges must be distinct"

    # centre connects to all four corners
    assert ADJ["c"] == frozenset({"tl", "tr", "bl", "br"}), ADJ["c"]
    # three square sides are edges
    assert frozenset({"tl", "bl"}) in norm, "left side tl-bl must be an edge"
    assert frozenset({"bl", "br"}) in norm, "bottom side bl-br must be an edge"
    assert frozenset({"tr", "br"}) in norm, "right side tr-br must be an edge"
    # the top side tl-tr is deliberately NOT an edge (the blocking dynamic)
    assert frozenset({"tl", "tr"}) not in norm, "top side tl-tr must NOT be an edge"
    # per-corner adjacency
    assert ADJ["tl"] == frozenset({"c", "bl"}), ADJ["tl"]
    assert ADJ["tr"] == frozenset({"c", "br"}), ADJ["tr"]
    assert ADJ["bl"] == frozenset({"c", "tl", "br"}), ADJ["bl"]
    assert ADJ["br"] == frozenset({"c", "tr", "bl"}), ADJ["br"]
    # adjacency symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- standard opening: 2 stones each, exactly one empty point -------------
    st = G.initial_state()
    assert st.pos == {"tl": 0, "tr": 0, "bl": 1, "br": 1}, st.pos
    assert "c" not in st.pos, "centre must start empty"
    assert sum(1 for v in st.pos.values() if v == 0) == 2, "player 0 has 2 stones"
    assert sum(1 for v in st.pos.values() if v == 1) == 2, "player 1 has 2 stones"
    assert len(st.pos) == 4, "exactly four of five points occupied at start"
    assert st.to_move == 0 and st.winner is None

    # --- move rule: slide a stone into the single empty point -----------------
    # Opening: only 'c' is empty; its neighbours are all four corners, so both
    # of player 0's stones (tl, tr) may move to c, and nothing else.
    om = set(G.legal_moves(st))
    assert om == {"tl>c", "tr>c"}, om
    # no captures / no move onto an occupied point: tl cannot go to bl (occupied)
    assert "tl>bl" not in om

    # apply a move: stone slides, turn passes, the vacated point becomes empty
    st2 = G.apply_move(st, "tl>c")
    assert st2.pos.get("c") == 0 and "tl" not in st2.pos, st2.pos
    assert st2.to_move == 1 and st2.ply == 1
    # now 'tl' is empty; tl's neighbours are c (player 0) and bl (player 1),
    # so player 1's only mover is bl>tl.
    assert set(G.legal_moves(st2)) == {"bl>tl"}, G.legal_moves(st2)

    # --- a hand-built stuck (blocking) position -------------------------------
    # Empty = tl (neighbours c, bl). White (player 1) on tr, br -- neither is a
    # neighbour of tl, so White has NO legal move and is stuck.
    stuck = PState(pos={"bl": 0, "c": 0, "tr": 1, "br": 1}, to_move=1)
    assert G._moves_for(stuck, 1) == [], "White must be fully blocked"

    # --- WIN reached via apply_move (the mover seals the opponent) -------------
    # Pre: centre empty, Black tl+bl, White tr+br, Black to move. Black plays
    # tl>c, which empties tl; White (tr,br) is then stuck and loses.
    pre = PState(pos={"tl": 0, "bl": 0, "tr": 1, "br": 1}, to_move=0)
    assert "tl>c" in set(G.legal_moves(pre))
    after = G.apply_move(pre, "tl>c")
    assert after.to_move == 1
    assert G.legal_moves(after) == [], "player 1 should have no legal move"
    assert G.is_terminal(after), "stuck player -> terminal"
    assert after.winner == 0, f"mover (player 0) should win, got {after.winner}"
    assert G.returns(after) == [1.0, -1.0]

    # symmetric: player 1 can also win by stalemating player 0
    pre1 = PState(pos={"bl": 1, "tr": 1, "tl": 0, "br": 0}, to_move=1)
    # empty = c; player 1 plays bl>c, emptying bl. Player 0 has tl,br.
    # After: empty=bl (neighbours c,tl,br). tl and br are BOTH neighbours of bl,
    # so player 0 is NOT stuck here -- assert it is a normal continuing position.
    after1 = G.apply_move(pre1, "bl>c")
    assert after1.winner is None and G.legal_moves(after1), \
        "this line should not stalemate player 0"

    # --- non-terminal opening, finite via ply cap -----------------------------
    assert not G.is_terminal(st)
    assert G.returns(PState(pos={}, to_move=0, ply=G.PLY_CAP, winner=None)) == [0.0, 0.0]

    # --- serialize round-trips ------------------------------------------------
    s = G.apply_move(G.initial_state(), "tr>c")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
