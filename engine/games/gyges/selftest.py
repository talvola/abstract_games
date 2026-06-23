"""Gygès correctness anchor (pure stdlib). There is no published perft for
Gygès, so the anchor is a set of baked rule assertions that pin down the game's
defining mechanics:

  (1) the 12 pieces are NEUTRAL (owned by neither player) and each has a HEIGHT
      of 1, 2 or 3 (four of each), a movement rank -- not ownership;
  (2) on your turn you may move only a piece in the occupied row NEAREST your own
      side (the 'active' row), with a documented fallback to the next row;
  (3) a piece moves EXACTLY its height in single orthogonal steps -- it may turn
      corners, may not reuse an edge within the move, intermediate squares must
      be EMPTY (it cannot pass THROUGH an occupied square) but the final square
      may be occupied;
  (4) if a move would end on an OCCUPIED square it does not stop -- the mover
      either BOUNCES (the SAME piece continues by the height of the piece it
      landed on, which STAYS put; bounces chain) or REPLACES (stops there and
      relocates the landed-on piece to an empty square);
  (5) WIN: land a piece exactly on YOUR goal cell (beyond the opponent's home
      edge), by a normal move or at the end of a bounce chain.

These facts were cross-checked one-time against the Board Game Arena and
Boardspace rule pages; here they are plain stdlib assertions.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.gyges.game import Gyges, GState  # noqa: E402

G = Gyges()


def board_of(st):
    return {(c, r): h for (c, r), h in st.board.items()}


def main():
    # (1) NEUTRAL pieces with heights 1/2/3, four of each, 12 total ------------
    s0 = G.initial_state()
    assert G.num_players == 2
    assert len(s0.board) == 12, len(s0.board)
    assert all(h in (1, 2, 3) for h in s0.board.values())
    assert Counter(s0.board.values()) == Counter({1: 4, 2: 4, 3: 4})
    # state stores ONLY (cell -> height); no owner field anywhere.
    ser = G.serialize(s0)
    assert set(ser.keys()) == {"board", "to_move", "ply", "winner"}, ser.keys()
    assert all(v in (1, 2, 3) for v in ser["board"].values())
    # render exposes neutrality (no owner) and the height as a label/stack.
    rs = G.render(s0)
    assert all(p["owner"] is None for p in rs["pieces"]), "pieces are NEUTRAL"
    assert {p["label"] for p in rs["pieces"]} == {"1", "2", "3"}

    # serialize round-trips ----------------------------------------------------
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)

    # (2) ACTIVE ROW: only the occupied row nearest the mover is playable ------
    #   player 0 (bottom) -> lowest occupied row; player 1 (top) -> highest.
    st = GState(board={(0, 2): 1, (5, 2): 1, (0, 4): 2}, to_move=0)
    assert sorted(G._movable_sources(st.board, 0)) == [(0, 2), (5, 2)]
    assert all(m.startswith(("0,2", "5,2")) for m in G.legal_moves(st))
    st1 = GState(board={(0, 2): 1, (5, 2): 1, (0, 4): 2}, to_move=1)
    assert G._movable_sources(st1.board, 1) == [(0, 4)]  # highest row for p1

    # (3a) move EXACTLY height in orthogonal steps -----------------------------
    #   a lone height-1 piece reaches only its 4 orthogonal neighbours.
    st = GState(board={(2, 2): 1}, to_move=0)
    dests = {m.split(">")[1] for m in G.legal_moves(st)}
    assert dests == {"3,2", "1,2", "2,3", "2,1"}, dests
    #   a height-2 piece: exactly-2-step landings (turning corners allowed),
    #   never a 1-step or 3-step square, never its own square.
    st = GState(board={(2, 2): 2}, to_move=0)
    d2 = {m.split(">")[1] for m in G.legal_moves(st)}
    assert "2,2" not in d2
    assert "4,2" in d2 and "0,2" in d2 and "2,4" in d2 and "2,0" in d2  # straight
    assert "3,3" in d2 and "1,1" in d2                                   # corner
    assert "3,2" not in d2 and "2,3" not in d2                           # 1-step

    # (3b) cannot pass THROUGH an occupied intermediate square -----------------
    #   h2 at (0,0) with (1,0) occupied: (0,0)->(1,0)->(2,0) is blocked and no
    #   other 2-step route reaches (2,0), so '0,0>2,0' is illegal.
    st = GState(board={(0, 0): 2, (1, 0): 1}, to_move=0)
    assert "0,0>2,0" not in G.legal_moves(st)
    #   ...but the final square MAY be occupied: h1 at (0,0) may land on (1,0).
    st = GState(board={(0, 0): 1, (1, 0): 3}, to_move=0)
    assert any(m.startswith("0,0>1,0") for m in G.legal_moves(st))

    # (4a) BOUNCE: mover continues by the landed-on piece's height; that piece
    #      STAYS, and the mover keeps its OWN height when it finally settles. ---
    st = GState(board={(0, 0): 1, (1, 0): 3}, to_move=0)
    #   h1 lands on h3 at (1,0) -> bounce by 3; e.g. settle at (4,0).
    mv = "0,0>1,0>4,0"
    assert mv in G.legal_moves(st), G.legal_moves(st)
    st2 = G.apply_move(st, mv)
    assert st2.board.get((1, 0)) == 3, "bounced-off piece stays put"
    assert st2.board.get((4, 0)) == 1, "mover keeps its own height (1)"
    assert (0, 0) not in st2.board, "mover left its source square"
    assert len(st2.board) == 2

    # (4b) REPLACE: stop on the occupied square, relocate that piece elsewhere --
    st = GState(board={(0, 0): 1, (1, 0): 3}, to_move=0)
    rep = "0,0>1,0>R3,3"     # land on (1,0); move that h3 piece to (3,3)
    assert rep in G.legal_moves(st), [m for m in G.legal_moves(st) if "R3,3" in m]
    st2 = G.apply_move(st, rep)
    assert st2.board.get((1, 0)) == 1, "mover settles on the landed-on square"
    assert st2.board.get((3, 3)) == 3, "landed-on piece relocated"
    assert (0, 0) not in st2.board
    assert len(st2.board) == 2

    # (5a) WIN by landing on YOUR goal -- direct, exact count ------------------
    #   the goal is adjacent to EVERY square of the row in front of it, so a
    #   piece on that row is one step from the goal.
    st = GState(board={(2, 5): 1}, to_move=0)          # p0 goal G0 beyond r=5
    assert "2,5>G0" in G.legal_moves(st)
    st2 = G.apply_move(st, "2,5>G0")
    assert st2.winner == 0 and G.is_terminal(st2)
    assert G.returns(st2) == [1.0, -1.0]
    #   exact count: a height-2 piece two rows away reaches the goal exactly.
    st = GState(board={(2, 4): 2}, to_move=0)
    assert "2,4>G0" in G.legal_moves(st)
    #   player 1 wins at G1 beyond r=0.
    st = GState(board={(3, 0): 1}, to_move=1)
    st2 = G.apply_move(st, "3,0>G1")
    assert st2.winner == 1 and G.returns(st2) == [-1.0, 1.0]

    # (5b) WIN via a BOUNCE chain (the typical Gygès finish) -------------------
    st = GState(board={(2, 3): 1, (2, 4): 2}, to_move=0)
    #   h1 from (2,3) -> (2,4) [occupied] -> bounce by 2 -> (2,5) -> G0.
    assert "2,3>2,4>G0" in G.legal_moves(st)
    st2 = G.apply_move(st, "2,3>2,4>G0")
    assert st2.winner == 0, "bounce chain into the goal wins"

    # the goal may only be a FINAL landing (exact count), never an intermediate
    # step. A height-2 piece on the goal row reaches G0 only as a real 2-step
    # landing (e.g. (2,5)->(1,5)->G0), and the goal never appears mid-path.
    st = GState(board={(2, 5): 2}, to_move=0)
    gmoves = [m for m in G.legal_moves(st) if "G0" in m]
    assert gmoves, "h2 on the goal row can finish on the goal in two steps"
    assert all(m.split(">")[-1] == "G0" for m in gmoves), "goal only as last step"
    #   a height-1 piece NOT on the goal row cannot reach the goal at all
    #   (wrong count): (2,4) is two steps from G0, h1 reaches only adjacents.
    st = GState(board={(2, 4): 1}, to_move=0)
    assert not any("G0" in m for m in G.legal_moves(st)), "exact count required"

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
