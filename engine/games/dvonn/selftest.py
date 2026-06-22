"""DVONN correctness anchor (pure stdlib). No published perft exists, so the
anchor is a set of baked rule assertions covering the distinctive mechanics:

  1. the 49-field elongated-hexagon board (6 corners / 18 edges / 25 interior),
     and the placement phase fills all 49 fields with 3 DVONN + 23 White + 23 Black,
     one piece per field;
  2. a stack moves EXACTLY its own height in a straight line along one of the SIX
     hex axes, may jump over intervening fields, and must land on an OCCUPIED field
     (never an empty one);
  3. you may move a stack iff your colour is on top;
  4. after every move, any stack not connected (via chains of adjacent stacks) to a
     DVONN/red piece is removed -- proven on a hand-built position;
  5. the game ends when no moves remain and the player controlling the most pieces
     (summed heights of stacks they top) wins; equal => draw.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.dvonn.game import (  # noqa: E402
    Dvonn, DState, CELLS, CELLSET, DIRS, WHITE, BLACK, DVONN, _top,
)

G = Dvonn()


def cols(st):
    return {f"{q},{r}": G._stack_str(v) for (q, r), v in st.board.items()}


def main():
    # --- (1) board geometry: 49 fields, canonical degree distribution --------
    assert len(CELLS) == 49 and len(CELLSET) == 49
    deg = Counter(sum(1 for (dq, dr) in DIRS if (q + dq, r + dr) in CELLSET)
                  for (q, r) in CELLS)
    assert dict(sorted(deg.items())) == {3: 6, 4: 18, 6: 25}, dict(deg)

    # --- (1) placement fills all 49 fields: 3 DVONN, 23 White, 23 Black ------
    s = G.initial_state()
    assert s.phase == "place" and s.board == {}
    import random
    rng = random.Random(7)
    while s.phase == "place":
        moves = G.legal_moves(s)
        assert moves, "placement must always offer a field until full"
        s = G.apply_move(s, rng.choice(moves))
    assert len(s.board) == 49, len(s.board)
    owners = Counter(_top(st) for st in s.board.values())   # each stack is height 1
    assert all(len(st) == 1 for st in s.board.values())
    assert owners[DVONN] == 3 and owners[WHITE] == 23 and owners[BLACK] == 23, owners
    assert s.phase == "move" and s.to_move == WHITE

    # --- (2)+(3) movement: exactly height, straight line, land on occupied ---
    # height-1 white stack at (0,1); neighbour occupied (1,1) -> legal step of 1.
    b = {(0, 1): (WHITE,), (1, 1): (DVONN,), (3, 1): (BLACK,)}
    st = DState(board=dict(b), phase="move", to_move=WHITE)
    mv = G.legal_moves(st)
    assert "0,1>1,1" in mv, mv
    # cannot reach (3,1): distance 3 but height is 1 -> not a legal move.
    assert "0,1>3,1" not in mv
    # black is not on top anywhere it controls except (3,1); white can't move it.
    assert all(m.split(">")[0] == "0,1" for m in mv if ">" in m), mv

    # height-2 white stack jumps EXACTLY 2 over an empty field onto an occupied one
    b = {(0, 1): (BLACK, WHITE), (2, 1): (DVONN,)}     # height 2, white on top
    st = DState(board=dict(b), phase="move", to_move=WHITE)
    mv = G.legal_moves(st)
    assert "0,1>2,1" in mv, mv                          # jumps over empty (1,1)
    st2 = G.apply_move(st, "0,1>2,1")
    # lands on top: stack at (2,1) becomes dvonn + (black,white) = 'dbw'
    assert cols(st2) == {"2,1": "dbw"}, cols(st2)
    # may NEVER land on an empty field: a lone height-1 stack with no occupied
    # neighbour at range 1 cannot move. (Give black a movable piece so white must
    # PASS rather than the game ending.)
    st = DState(board={(0, 1): (WHITE,), (2, 0): (DVONN,),
                       (3, 0): (BLACK,)}, phase="move", to_move=WHITE)
    # white at (0,1): range-1 neighbours all empty/off-board -> no landing -> pass.
    assert G.legal_moves(st) == ["pass"], G.legal_moves(st)

    # --- (3) control follows the TOP piece -----------------------------------
    # (0,1) is white-bottom/black-top -> BLACK controls it. White may not move it.
    # Give white a genuinely movable stack so "white can't touch the black tower"
    # is the thing under test (white moves its own (3,1) instead).
    b = {(0, 1): (WHITE, BLACK), (1, 1): (DVONN,), (2, 1): (WHITE,)}
    st = DState(board=dict(b), phase="move", to_move=WHITE)
    mv = G.legal_moves(st)
    assert all(m.split(">")[0] != "0,1" for m in mv if ">" in m), mv
    assert "2,1>1,1" in mv, mv                           # white moves ITS own piece

    # --- (4) DVONN disconnection removal fires -------------------------------
    # A chain: DVONN anchor at (0,2); white at (1,2) adjacent (kept). A separate
    # white at (5,2) NOT adjacent to anything in the anchor chain -> removed after
    # a move that doesn't reconnect it.
    b = {
        (0, 2): (DVONN,),        # anchor
        (1, 2): (WHITE,),        # adjacent to anchor -> stays
        (5, 2): (WHITE,),        # isolated white
        (6, 2): (BLACK,),        # adjacent to the isolated white but no DVONN in group
    }
    st = DState(board=dict(b), phase="move", to_move=WHITE)
    # White moves (1,2) one step onto the anchor (0,2)... that keeps the new tower
    # on the anchor; the {(5,2),(6,2)} group is disconnected -> removed.
    st2 = G.apply_move(st, "1,2>0,2")
    assert (5, 2) not in st2.board and (6, 2) not in st2.board, cols(st2)
    assert (0, 2) in st2.board and st2.board[(0, 2)] == (DVONN, WHITE), cols(st2)

    # direct unit test of the removal helper: nothing touching a DVONN survives
    board = {(0, 2): (WHITE,), (8, 2): (DVONN,), (7, 2): (BLACK,)}
    kept = G._remove_disconnected(board)
    assert set(kept) == {(8, 2), (7, 2)}, kept       # (0,2) far from DVONN -> gone
    # if no DVONN remains, the whole board is wiped
    assert G._remove_disconnected({(0, 2): (WHITE,)}) == {}

    # --- (5) end + scoring: most controlled pieces wins ----------------------
    # neither side can move -> terminal; score = summed heights of stacks you top.
    b = {
        (0, 2): (DVONN, WHITE, WHITE),   # white controls, height 3 -> +3 white
        (1, 2): (BLACK,),                # adjacent (connected), black controls -> +1 black
    }
    st = DState(board=dict(b), phase="move", to_move=WHITE)
    # white stack height 3 -> would land 3 away (empty/off-board) -> no move;
    # black height 1 -> neighbour (0,2) occupied -> black CAN move. So white passes.
    assert G.legal_moves(st) == ["pass"], G.legal_moves(st)
    # craft a truly stuck terminal: both stacks so TALL that every distance-h
    # landing in all six directions falls off the board (the board is only ~11
    # fields wide), so neither player has any move.
    big = 11
    b3 = {
        (4, 2): (DVONN,),                          # anchor (neutral, never moves)
        (3, 2): tuple([BLACK] + [WHITE] * big),    # white controls, height big+1
        (5, 2): tuple([WHITE] + [BLACK] * big),    # black controls, height big+1
    }
    st = DState(board=dict(b3), phase="move", to_move=WHITE)
    assert G.legal_moves(st) == [], "both stacks immobile + no other -> terminal"
    # REACH the terminal via apply_move so `winner` is actually set (win-as-event):
    # give black one last movable piece, white passes, black moves into a dead
    # position. Here we instead drive the placement->full->already-stuck path:
    # confirm that when apply_move produces a no-move state it stamps the winner.
    movable = {
        (4, 2): (DVONN,),
        (3, 2): tuple([BLACK] + [WHITE] * big),    # white: immobile (too tall)
        (5, 2): (BLACK,),                          # black: can step onto (4,2)... no, dist1 -> (4,2) occupied? (4,2) is range1 -> yes movable
    }
    # white is stuck (immobile tall stack) but black can move -> white passes;
    # after black's move, if black also becomes stuck the game ends with a winner.
    stp = DState(board=dict(movable), phase="move", to_move=WHITE)
    assert G.legal_moves(stp) == ["pass"], G.legal_moves(stp)
    after_pass = G.apply_move(stp, "pass")          # now black to move
    assert after_pass.to_move == BLACK
    bmoves = G.legal_moves(after_pass)
    assert bmoves and bmoves != ["pass"], bmoves
    final = G.apply_move(after_pass, bmoves[0])
    # black moved (5,2)->(4,2); now nobody can move -> terminal, winner stamped.
    assert G.is_terminal(final) and final.winner is not None, (final.winner, cols(final))
    # equal heights -> draw
    assert G._score_winner(b3) == -1, G._scores(b3)

    # a decisive end: white tops MORE pieces than black -> white wins.
    b4 = {
        (4, 2): (DVONN,),
        (3, 2): tuple([BLACK] + [WHITE] * (big + 2)),   # white controls, taller
        (5, 2): tuple([WHITE] + [BLACK] * big),         # black controls
    }
    assert G._score_winner(b4) == WHITE, G._scores(b4)
    sc = G._scores(b4)
    assert sc[WHITE] > sc[BLACK], sc

    # --- serialize round-trips (mixed towers incl. DVONN) --------------------
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
