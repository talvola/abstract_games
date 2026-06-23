"""TZAAR correctness anchor (pure stdlib). No published perft exists, so the
anchor is a set of baked rule assertions covering the facts that define TZAAR:

  (1) board = hexhex side 5 = 61 cells; the single CENTRE cell is empty at start,
      so exactly 60 cells are filled, 30 per player, each player holding exactly
      6 Tzaar / 9 Tzarra / 15 Tott (type tracked per stack, by the TOP piece).
  (2) a turn = TWO actions: first a MANDATORY capture (move a controlled stack
      onto an adjacent enemy stack of height <= yours; the enemy stack is removed
      ENTIRELY and replaced by yours -- height unchanged, no banking), then a
      SECOND action that is EITHER another capture OR a STACK move (onto an
      adjacent FRIENDLY stack, combining: moved stack on top, heights summed,
      type = mover's top). The 2nd action may be skipped (pass) only on the very
      first turn of the game.
  (3) a player LOSES at the start of their turn if they have no stacks of one of
      the three TYPES, or if they cannot make a capture.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.tzaar.game import (  # noqa: E402
    Tzaar, TState, N, WHITE, BLACK, TOTT, TZARRA, TZAAR,
    _cells, _type_sequence, _height, _type, _owner,
)

G = Tzaar()


def main():
    # --- (1) board shape + setup ------------------------------------------
    assert len(_cells(N)) == 61, len(_cells(N))           # hexhex side 5
    s0 = G.initial_state()
    assert (0, 0) not in s0.board, "centre must be empty at start"
    assert len(s0.board) == 60, len(s0.board)             # 60 filled cells
    for p in (WHITE, BLACK):
        mine = [stk for stk in s0.board.values() if _owner(stk) == p]
        assert len(mine) == 30, (p, len(mine))
        cnt = {TZAAR: 0, TZARRA: 0, TOTT: 0}
        for stk in mine:
            cnt[_type(stk)] += 1
            assert _height(stk) == 1, "singletons at start"
        assert cnt == {TZAAR: 6, TZARRA: 9, TOTT: 15}, (p, cnt)
    # the fixed type sequence has the right composition
    seq = _type_sequence()
    assert seq.count(TZAAR) == 6 and seq.count(TZARRA) == 9 and seq.count(TOTT) == 15
    # deterministic / reproducible
    assert G.serialize(G.initial_state()) == G.serialize(G.initial_state())

    # --- (2a) first action is a MANDATORY capture; no stack/pass offered ----
    # Hand-built: white Tott (h1) adjacent to a black Tott (h1).
    st = TState(board={(0, 0): (WHITE, TOTT, 1), (1, 0): (BLACK, TOTT, 1)},
                to_move=WHITE, phase=0, ply=5)
    lm = G.legal_moves(st)
    assert lm == ["0,0>1,0"], lm                         # only the capture
    assert "pass" not in lm

    # capture by REPLACEMENT: enemy removed entirely, your height unchanged
    st2 = G.apply_move(st, "0,0>1,0")
    assert (0, 0) not in st2.board, "mover left its origin"
    assert st2.board[(1, 0)] == (WHITE, TOTT, 1), st2.board[(1, 0)]
    assert st2.to_move == WHITE and st2.phase == 1, "same player, 2nd action pending"

    # --- height rule: cannot capture a TALLER enemy stack -----------------
    st = TState(board={(0, 0): (WHITE, TOTT, 1), (1, 0): (BLACK, TOTT, 2)},
                to_move=WHITE, phase=0, ply=5)
    # white has only the height-1 stack; the height-2 black is uncapturable ->
    # white cannot capture -> white loses at start of turn (no moves).
    assert G.legal_moves(st) == [], "no legal capture against taller stack"
    # but an equal-or-taller stack CAN capture:
    st = TState(board={(0, 0): (WHITE, TOTT, 2), (1, 0): (BLACK, TOTT, 2)},
                to_move=WHITE, phase=0, ply=5)
    assert G.legal_moves(st) == ["0,0>1,0"], G.legal_moves(st)

    # --- (2b) second action: a STACK move combines two friendly stacks -----
    # After a phase-0 capture we are in phase 1. Build a phase-1 state directly:
    st = TState(board={(0, 0): (WHITE, TZARRA, 1), (1, 0): (WHITE, TOTT, 1)},
                to_move=WHITE, phase=1, ply=6)
    lm = G.legal_moves(st)
    assert "0,0>1,0" in lm and "1,0>0,0" in lm and "pass" in lm, lm
    # combine: move the Tzarra onto the Tott -> top is Tzarra, height 2
    st2 = G.apply_move(st, "0,0>1,0")
    assert (0, 0) not in st2.board
    assert st2.board[(1, 0)] == (WHITE, TZARRA, 2), st2.board[(1, 0)]
    assert st2.to_move == BLACK and st2.phase == 0, "turn passes after 2nd action"
    # combine the other way -> top is Tott, height 2
    st3 = G.apply_move(st, "1,0>0,0")
    assert st3.board[(0, 0)] == (WHITE, TOTT, 2), st3.board[(0, 0)]

    # --- SLIDING: a LONG-RANGE capture across vacant cells is legal ---------
    # White Tott at (-3,0) slides east over the empty cells (-2,0),(-1,0),(0,0),
    # (1,0),(2,0) to the first occupied cell (3,0), a black Tott -> capture.
    st = TState(board={(-3, 0): (WHITE, TOTT, 1), (3, 0): (BLACK, TOTT, 1)},
                to_move=WHITE, phase=0, ply=5)
    assert G.legal_moves(st) == ["-3,0>3,0"], G.legal_moves(st)
    st2 = G.apply_move(st, "-3,0>3,0")
    assert (-3, 0) not in st2.board, "mover left its origin after a long slide"
    assert st2.board[(3, 0)] == (WHITE, TOTT, 1), st2.board[(3, 0)]

    # --- SLIDING: a capture is BLOCKED by an intervening piece (no jumping) --
    # Same line, but a piece sits at (0,0) between attacker (-3,0) and target
    # (3,0). The slide must STOP at the first occupied cell (0,0); it may not
    # jump to (3,0). If the blocker is friendly, no capture exists on this line.
    st = TState(board={(-3, 0): (WHITE, TOTT, 1),
                       (0, 0): (WHITE, TZAAR, 3),     # taller friendly blocker
                       (3, 0): (BLACK, TOTT, 1)},
                to_move=WHITE, phase=0, ply=5)
    lm = G.legal_moves(st)
    assert "-3,0>3,0" not in lm, "cannot jump over the blocker at (0,0)"
    # the only thing (-3,0) reaches eastward is the friendly blocker -> no
    # capture there; and applying the jump move must be REJECTED outright.
    try:
        G.apply_move(st, "-3,0>3,0")
        assert False, "jumping over a piece must raise"
    except ValueError:
        pass
    # with an ENEMY blocker of height <= ours, the slide stops there and that
    # blocker (not the far piece) is the capture target.
    st = TState(board={(-3, 0): (WHITE, TOTT, 1),
                       (0, 0): (BLACK, TOTT, 1),       # enemy blocker
                       (3, 0): (BLACK, TOTT, 1)},
                to_move=WHITE, phase=0, ply=5)
    lm = G.legal_moves(st)
    assert lm == ["-3,0>0,0"], lm                      # stops at the blocker
    assert "-3,0>3,0" not in lm, "cannot reach the far piece through a blocker"

    # --- SLIDING: a long-range STACK-combine onto a non-adjacent friend ------
    st = TState(board={(-2, 0): (WHITE, TZARRA, 1), (2, 0): (WHITE, TOTT, 1)},
                to_move=WHITE, phase=1, ply=8)
    lm = G.legal_moves(st)
    assert "-2,0>2,0" in lm and "2,0>-2,0" in lm, lm
    st2 = G.apply_move(st, "-2,0>2,0")                 # Tzarra slides onto Tott
    assert (-2, 0) not in st2.board
    assert st2.board[(2, 0)] == (WHITE, TZARRA, 2), st2.board[(2, 0)]

    # --- (2c) second action may be a CAPTURE too ---------------------------
    st = TState(board={(0, 0): (WHITE, TOTT, 1), (1, 0): (BLACK, TOTT, 1)},
                to_move=WHITE, phase=1, ply=6)
    assert "0,0>1,0" in G.legal_moves(st)
    st2 = G.apply_move(st, "0,0>1,0")
    assert st2.board[(1, 0)] == (WHITE, TOTT, 1)
    assert st2.phase == 0 and st2.to_move == BLACK

    # --- first-move rule: opening turn is a SINGLE capture (no 2nd action) --
    st = TState(board={(0, 0): (WHITE, TOTT, 1), (1, 0): (BLACK, TOTT, 1),
                       (2, 0): (BLACK, TOTT, 1)},
                to_move=WHITE, phase=0, ply=0)               # ply 0 = first move
    st2 = G.apply_move(st, "0,0>1,0")
    assert st2.to_move == BLACK and st2.phase == 0, "first move ends the turn"

    # --- (3) survival loss: missing a TYPE loses at start of turn -----------
    # The loss is resolved when the turn is handed over (in _end_turn), so we
    # REACH it via apply_move rather than constructing the dead state.
    # Black has a single Tzarra (only one type); white captures it -> black now
    # has zero Totts and zero Tzaars -> black is missing types -> black loses.
    pre = TState(board={(0, 0): (WHITE, TOTT, 1), (1, 0): (BLACK, TZARRA, 1),
                        (2, 0): (WHITE, TZARRA, 1), (3, 0): (WHITE, TZAAR, 1)},
                 to_move=WHITE, phase=1, ply=11)
    post = G.apply_move(pre, "0,0>1,0")     # white Tott replaces black's last piece
    assert post.to_move == BLACK
    assert not G._has_all_types(post.board, BLACK)
    assert post.winner == WHITE, post.winner
    assert G.is_terminal(post) and G.returns(post) == [1.0, -1.0]

    # A player MISSING a type still has 'legal_moves' only if winner unset; in
    # real play _end_turn sets winner first. Verify the helper directly:
    half = {(0, 0): (BLACK, TOTT, 1), (1, 0): (BLACK, TZARRA, 1)}  # no Tzaar
    assert not G._has_all_types(half, BLACK)
    full = dict(half); full[(2, 0)] = (BLACK, TZAAR, 1)
    assert G._has_all_types(full, BLACK)

    # --- loss by inability to capture (all types present, no capture) -------
    # All white stacks are height 1; every black stack is height 2, so no white
    # slide can ever capture (height rule) however far it reaches -> white loses.
    st = TState(board={(0, 0): (WHITE, TOTT, 1), (0, 1): (WHITE, TZARRA, 1),
                       (0, 2): (WHITE, TZAAR, 1), (4, 0): (BLACK, TOTT, 2),
                       (4, -1): (BLACK, TZARRA, 2), (4, -2): (BLACK, TZAAR, 2)},
                to_move=WHITE, phase=0, ply=20)
    assert G.legal_moves(st) == [], "no capturable enemy -> cannot capture"

    # --- serialize round-trips (mixed types + heights) ---------------------
    st = TState(board={(0, 0): (WHITE, TZAAR, 3), (1, 0): (BLACK, TOTT, 1),
                       (2, -1): (WHITE, TZARRA, 2)},
                to_move=BLACK, phase=1, ply=7)
    assert G.serialize(G.deserialize(G.serialize(st))) == G.serialize(st)

    # --- a full random game terminates (sanity, small/fast) ----------------
    import random
    rng = random.Random(12345)
    s = G.initial_state()
    steps = 0
    while not G.is_terminal(s) and steps < 5000:
        moves = G.legal_moves(s)
        assert moves, "non-terminal must have moves"
        s = G.apply_move(s, rng.choice(moves))
        steps += 1
    assert G.is_terminal(s), "game terminated"
    r = G.returns(s)
    assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
