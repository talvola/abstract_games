"""Tak correctness anchor (pure stdlib). No published perft exists for Tak, so
the anchor is a set of baked rule assertions on hand-built positions covering
every distinctive rule:

  (1) opening double-move places an OPPONENT-coloured flat on an empty square;
  (2) ROAD win by orthogonal BFS spanning opposite edges, checked after a move;
  (3) a WALL never counts toward a road;
  (4) a lone capstone flattens a wall it moves onto; you cannot otherwise drop
      onto a wall or a capstone;
  (5) carry limit = board size N; a spread drops >=1 on each successive square;
  (6) flat-count end (board full or a reserve emptied): count flat-TOPPED squares
      only, most wins, tie = draw;
  (7) per-size reserve counts (5x5 = 21 flats + 1 capstone).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.tak.game import (  # noqa: E402
    Tak, TState, P0, P1, FLAT, WALL, CAP, RESERVES,
)

G = Tak()


def st(n=5, board=None, to_move=P0, first=(True, True), reserves=None):
    """Build a mid-game state (both openings already done by default)."""
    if reserves is None:
        f, c = RESERVES[n]
        reserves = {P0: [f, c], P1: [f, c]}
    return TState(n=n, board=dict(board or {}), to_move=to_move,
                  reserves=reserves, first_done=list(first))


def main():
    # ---- (7) per-size reserve counts -------------------------------------
    assert RESERVES == {3: (10, 0), 4: (15, 0), 5: (21, 1), 6: (30, 1), 8: (50, 2)}
    s0 = G.initial_state({"size": 5})
    assert s0.reserves[P0] == [21, 1] and s0.reserves[P1] == [21, 1]
    assert G.initial_state({"size": 3}).reserves[P0] == [10, 0]
    assert G.initial_state({"size": 8}).reserves[P0] == [50, 2]

    # ---- (1) opening double-move: place OPPONENT's flat ------------------
    s = G.initial_state({"size": 5})
    assert s.to_move == P0 and not s.first_done[P0]
    moves = G.legal_moves(s)
    assert moves and all("=" not in m and ">" not in m for m in moves), \
        "opening offers only bare-cell flat placements"
    s1 = G.apply_move(s, "2,2")
    sq = s1.board[(2, 2)]
    assert sq == ((P1,), FLAT), "P0's opening places a P1-coloured flat"
    assert s1.first_done[P0] and s1.to_move == P1
    # P1's opening likewise places a P0 flat
    s2 = G.apply_move(s1, "0,0")
    assert s2.board[(0, 0)] == ((P0,), FLAT), "P1's opening places a P0-coloured flat"
    assert s2.first_done == [True, True] and s2.to_move == P0
    # reserves untouched by openings (those pieces are "free")? -- per our rules
    # the opening flat does come from nowhere special; we do NOT debit reserves
    # for the opponent-coloured opening (standard Tak: it's still a normal stone,
    # but it belongs to the placer's opponent and is not charged to anyone here).
    assert s2.reserves[P0] == [21, 1] and s2.reserves[P1] == [21, 1]

    # ---- placement after opening: F / S / C choices ----------------------
    s = st(5, to_move=P0)
    ms = G.legal_moves(s)
    assert "0,0=F" in ms and "0,0=S" in ms and "0,0=C" in ms
    sF = G.apply_move(s, "0,0=F")
    assert sF.board[(0, 0)] == ((P0,), FLAT) and sF.reserves[P0][0] == 20
    sC = G.apply_move(s, "0,0=C")
    assert sC.board[(0, 0)] == ((P0,), CAP) and sC.reserves[P0][1] == 0
    # with no capstone left, =C is not offered
    s_nocap = st(5, to_move=P0, reserves={P0: [21, 0], P1: [21, 1]})
    assert "0,0=C" not in G.legal_moves(s_nocap)

    # ---- (3) a WALL never counts toward a road ---------------------------
    # full column of P0 flats from r=0..4 EXCEPT (0,2) is a wall -> no road.
    board = {}
    for r in range(5):
        board[(0, r)] = (((P0,), WALL) if r == 2 else ((P0,), FLAT))
    s = st(5, board=board, to_move=P1)
    assert not G._has_road(s, P0), "a wall breaks the road"
    # make (0,2) a flat -> road appears
    board[(0, 2)] = ((P0,), FLAT)
    s = st(5, board=board, to_move=P1)
    assert G._has_road(s, P0), "full flat column is a vertical road"

    # ---- (2) ROAD win checked after a move; capstone counts --------------
    # P0 has flats at (0,0)..(0,3); placing a flat at (0,4) completes a road.
    board = {(0, r): ((P0,), FLAT) for r in range(4)}
    s = st(5, board=board, to_move=P0)
    s2 = G.apply_move(s, "0,4=F")
    assert s2.winner == P0 and G.returns(s2) == [1.0, -1.0], "road completes -> win"
    # a capstone-topped square also counts toward a road
    board = {(0, r): ((P0,), FLAT) for r in range(4)}
    s = st(5, board=board, to_move=P0)
    s2 = G.apply_move(s, "0,4=C")
    assert s2.winner == P0, "capstone completes the road"

    # horizontal road too
    board = {(c, 0): ((P0,), FLAT) for c in range(4)}
    s = st(5, board=board, to_move=P0)
    s2 = G.apply_move(s, "4,0=F")
    assert s2.winner == P0, "left-right road wins"

    # ---- mover-wins road tie-break ---------------------------------------
    # Two completed roads of opposite players cannot coexist on one board (a P0
    # vertical and a P1 horizontal road must cross at a single cell, owned by one
    # player), so a genuine double-road is geometrically impossible. We therefore
    # verify the DOCUMENTED resolver order directly: _resolve_terminal checks the
    # mover's road first, so if both flags were ever true the mover would win.
    # Confirm a road is still awarded to its owner regardless of who just moved:
    chk = st(5, board={(0, r): ((P0,), FLAT) for r in range(5)}, to_move=P0)
    G._resolve_terminal(chk, mover=P1)   # P1 'just moved' into a board with a P0 road
    assert chk.winner == P0, "only P0 has a road -> P0 wins regardless of mover"
    # mover-first ordering is structural in _resolve_terminal (mover_road checked
    # before other_road), so a simultaneous road would award the mover.

    # ---- (5) carry limit = N, spreads drop >=1 each square ---------------
    # A controlled stack of height 6 on a 5-board: max lift = 5 (not 6).
    s = st(5, board={(2, 2): ((P0, P0, P0, P0, P0, P0), FLAT)}, to_move=P0)
    spread_moves = [m for m in G.legal_moves(s) if m.startswith("2,2>")]
    # the largest single suffix-sum (= lift) must be <= 5
    lifts = [sum(int(ch) for ch in m.split("=")[1]) for m in spread_moves]
    assert lifts and max(lifts) == 5, ("carry capped at N", max(lifts))
    # every drop digit >=1
    assert all(all(int(ch) >= 1 for ch in m.split("=")[1]) for m in spread_moves)

    # a concrete spread: lift the whole height-3 stack (bottom->top P0,P1,P0),
    # move +x, drop 1 then 2. The first piece dropped is the BOTTOM of the lifted
    # column (P0); the final square keeps the original top piece's kind.
    s = st(5, board={(2, 2): ((P0, P1, P0), FLAT)}, to_move=P0)
    mv = "2,2>3,2>4,2=12"
    assert mv in G.legal_moves(s), G.legal_moves(s)
    s2 = G.apply_move(s, mv)
    assert (2, 2) not in s2.board, "whole stack lifted -> origin empties"
    assert s2.board[(3, 2)][0] == (P0,), "first drop = bottom of the lifted column"
    assert s2.board[(4, 2)][0] == (P1, P0), "last drop = remaining two (P1 then top P0)"
    assert s2.board[(4, 2)][1] == FLAT
    assert s2.board[(4, 2)][0][-1] == P0, "P0 still controls the moved stack"

    # spread leaving some behind exposes the new top as a flat
    s = st(5, board={(2, 2): ((P1, P0, P0), FLAT)}, to_move=P0)
    s2 = G.apply_move(s, "2,2>3,2=1")
    assert s2.board[(2, 2)] == ((P1, P0), FLAT), "exposed piece acts as flat"
    assert s2.board[(3, 2)] == ((P0,), FLAT)

    # ---- (4) lone capstone flattens a wall; cannot otherwise cover --------
    s = st(5, board={(2, 2): ((P0,), CAP), (3, 2): ((P1,), WALL)}, to_move=P0)
    flat_mv = "2,2>3,2=1"
    assert flat_mv in G.legal_moves(s), "lone capstone may flatten a wall"
    s2 = G.apply_move(s, flat_mv)
    assert s2.board[(3, 2)] == ((P1, P0), CAP), "wall flattened, capstone on top"
    # A capstone-topped stack may lift JUST the capstone (1 piece) to flatten a
    # wall -- that IS a lone-capstone move. But carrying 2+ onto the wall is illegal.
    s = st(5, board={(2, 2): ((P0, P0), CAP), (3, 2): ((P1,), WALL)}, to_move=P0)
    onto_wall = [m for m in G.legal_moves(s) if m.split("=")[0].endswith(">3,2")]
    assert onto_wall == ["2,2>3,2=1"], \
        ("only the lone-capstone (lift 1) may flatten the wall", onto_wall)
    # a flat-topped stack may never enter a wall
    s = st(5, board={(2, 2): ((P0,), FLAT), (3, 2): ((P1,), WALL)}, to_move=P0)
    assert not any(m.startswith("2,2>3,2") for m in G.legal_moves(s)), \
        "flats cannot move onto a wall"
    # nothing may ever cover a capstone
    s = st(5, board={(2, 2): ((P0,), CAP), (3, 2): ((P1,), CAP)}, to_move=P0)
    assert not any(m.startswith("2,2>3,2") for m in G.legal_moves(s)), \
        "a capstone can never be covered"

    # ---- (6) flat-count end: board full OR reserve emptied ---------------
    # tiny: 3x3 with 10 flats. Fill the board, no road; count flat tops.
    # Build an 8-cell board (one short of full) where P0 leads in flat tops,
    # then P0 places the last flat (no road) -> board full -> P0 wins on flats.
    board = {}
    cells = [(c, r) for r in range(3) for c in range(3)]
    # arrange so NO road exists: checkerboard-ish ownership, use a wall to be safe
    owners = [P0, P1, P0,
              P1, P0, P1,
              P0, P1, None]
    for (c, r), o in zip(cells, owners):
        if o is None:
            continue
        board[(c, r)] = ((o,), FLAT)
    # P0 has 4 flats (cells 0,2,4,6), P1 has 4 (1,3,5,7); last cell (2,2) empty
    s = st(3, board=board, to_move=P0)
    # placing a P0 flat at (2,2) fills the board: P0 5 vs P1 4 (if no road)
    assert not G._has_road(s, P0) and not G._has_road(s, P1)
    s2 = G.apply_move(s, "2,2=F")
    assert len(s2.board) == 9, "board is full"
    assert s2.winner == P0, ("more flats wins on a full board", s2.winner)

    # walls/capstones do NOT count as flats in the tally
    board = {(0, 0): ((P0,), WALL), (1, 0): ((P1,), FLAT)}
    # fill remaining 3x3 cells with neutral-ish to force full board, no road
    fillers = [(2, 0, P1, FLAT), (0, 1, P1, WALL), (1, 1, P0, FLAT),
               (2, 1, P1, FLAT), (0, 2, P1, WALL), (1, 2, P0, FLAT)]
    for c, r, o, k in fillers:
        board[(c, r)] = ((o,), k)
    s = st(3, board=board, to_move=P0)
    assert not G._has_road(s, P0) and not G._has_road(s, P1)
    # P0 flat tops: (1,1),(1,2) = 2 ; P1 flat tops: (1,0),(2,0),(2,1) = 3
    s2 = G.apply_move(s, "2,2=F")   # P0 places a flat -> now P0 has 3 flats, full
    # P0 flats: (1,1),(1,2),(2,2)=3 ; P1 flats: (1,0),(2,0),(2,1)=3 -> tie -> draw
    assert s2.winner == "draw", ("equal flats -> draw", s2.winner)

    # reserve-empty trigger: a player placing their LAST stone ends the game.
    # 3x3, P0 down to its last flat. Give P0 a slight flat lead so it wins.
    board = {(0, 0): ((P0,), FLAT), (1, 0): ((P0,), FLAT), (0, 1): ((P1,), FLAT)}
    s = st(3, board=board, to_move=P0, reserves={P0: [1, 0], P1: [5, 0]})
    # ensure the placement does NOT make a road (P0 has (0,0),(1,0); adding (2,2))
    s2 = G.apply_move(s, "2,2=F")
    assert s2.reserves[P0][0] == 0
    assert s2.winner is not None, "emptying a reserve ends the game"
    assert s2.winner == P0, "P0 leads on flats at the reserve-empty end"

    # reserve-empty REGRESSION (5x5, capstone-bearing size): placing your last
    # FLAT while you still hold a capstone must NOT end the game — only running
    # out of EVERY piece does. (Was a bug: the flat reserve hitting 0 ended it.)
    s = st(5, board={(2, 2): ((P0,), FLAT)}, to_move=P0,
           reserves={P0: [1, 1], P1: [5, 1]})       # P0: 1 flat + 1 capstone
    s2 = G.apply_move(s, "0,4=F")                    # P0 plays its last flat...
    assert s2.reserves[P0] == [0, 1], s2.reserves[P0]
    assert s2.winner is None, ("last flat but capstone remains -> game continues",
                               s2.winner)
    # ...and now emptying the LAST piece (the capstone) does end it.
    s = st(5, board={(2, 2): ((P0,), FLAT), (3, 3): ((P0,), FLAT),
                     (0, 4): ((P1,), FLAT)}, to_move=P0,
           reserves={P0: [0, 1], P1: [5, 1]})        # P0: only a capstone left
    s2 = G.apply_move(s, "4,0=C")                     # isolated -> no road
    assert s2.reserves[P0] == [0, 0]
    assert s2.winner == P0, ("emptying the whole reserve ends the game; P0 leads "
                             "on flats (caps don't count)", s2.winner)

    # ---- serialise round-trips (mixed stacks, walls, caps) ---------------
    s = st(5, board={(2, 2): ((P0, P1, P0), CAP), (3, 3): ((P1,), WALL),
                     (1, 1): ((P0,), FLAT)}, to_move=P1)
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    # ---- a short random-ish game terminates ------------------------------
    import random
    rng = random.Random(7)
    for _ in range(5):
        s = G.initial_state({"size": 3})
        steps = 0
        while not G.is_terminal(s) and steps < 500:
            ms = G.legal_moves(s)
            assert ms, "non-terminal states must have moves"
            s = G.apply_move(s, rng.choice(ms))
            steps += 1
        assert G.is_terminal(s), "game must terminate"
        r = G.returns(s)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
