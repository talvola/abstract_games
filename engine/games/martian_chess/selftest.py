"""Pure-stdlib correctness anchor for Martian Chess.

Run: cd engine && PYTHONPATH=. python3 games/martian_chess/selftest.py
Asserts the 4x8 board + two zones, the exact starting setup, the three
movement types, zone ownership, capture scoring, the no-take-back rule, and
the zone-empty game end (reached via apply_move). Prints SELFTEST OK.
"""

from __future__ import annotations

import json

from games.martian_chess.game import (
    MartianChess, MartianState, _cell, _zone, _start_pieces, W, H, CANAL,
)


def _board(spec):
    """Build a board dict from {(c,r): size}."""
    return dict(spec)


def main():
    g = MartianChess()

    # --- board geometry: 4 wide x 8 tall, canal between zones -----------------
    assert (W, H) == (4, 8), (W, H)
    r = g.render(g.initial_state())
    assert r["board"]["width"] == 4 and r["board"]["height"] == 8
    assert _zone(0) == 0 and _zone(3) == 0 and _zone(4) == 1 and _zone(7) == 1
    assert CANAL == 4

    # --- exact starting setup: 9 pieces per zone, triangular corner block -----
    b = _start_pieces()
    assert len(b) == 18, len(b)
    # bottom zone (player 0)
    assert {c: b.get(c) for c in [(0, 0), (1, 0), (0, 1)]} == {(0, 0): 3, (1, 0): 3, (0, 1): 3}
    assert {c: b.get(c) for c in [(2, 0), (1, 1), (0, 2)]} == {(2, 0): 2, (1, 1): 2, (0, 2): 2}
    assert {c: b.get(c) for c in [(3, 0), (2, 1), (1, 2)]} == {(3, 0): 1, (2, 1): 1, (1, 2): 1}
    # top zone (player 1) = 180-degree rotation
    assert b.get((3, 7)) == 3 and b.get((2, 7)) == 3 and b.get((3, 6)) == 3
    assert b.get((1, 7)) == 2 and b.get((2, 6)) == 2 and b.get((3, 5)) == 2
    assert b.get((0, 7)) == 1 and b.get((1, 6)) == 1 and b.get((2, 5)) == 1
    # each side: 3 queens, 3 drones, 3 pawns; all pieces within own zone
    for player in (0, 1):
        sizes = sorted(sz for cell, sz in b.items() if _zone(cell[1]) == player)
        assert sizes == [1, 1, 1, 2, 2, 2, 3, 3, 3], (player, sizes)

    # --- PAWN: one square diagonally only -------------------------------------
    s = MartianState(board=_board({(1, 1): 1}), to_move=0)
    dests = {m.split(">")[1] for m in g.legal_moves(s)}
    assert dests == {"0,0", "2,0", "0,2", "2,2"}, dests  # 4 diagonals, 1 step
    # pawn cannot move orthogonally or two steps
    assert "1,3" not in dests and "1,0" not in dests and "0,1" not in dests

    # --- DRONE: 1 or 2 orthogonally, no jumping -------------------------------
    s = MartianState(board=_board({(1, 1): 2}), to_move=0)
    dests = {m.split(">")[1] for m in g.legal_moves(s)}
    # from (1,1): up to (1,2),(1,3); down to (1,0); left to (0,1); right (2,1),(3,1)
    assert dests == {"1,2", "1,3", "1,0", "0,1", "2,1", "3,1"}, dests
    assert "2,2" not in dests  # no diagonal
    # no jumping: a blocker at (1,2) (own zone) stops the drone at... it's a
    # friendly piece with no legal merge, so (1,2) and (1,3) both unreachable.
    s = MartianState(board=_board({(1, 0): 2, (1, 2): 2, (3, 2): 2}), to_move=0)
    dests = {m.split(">")[1] for m in g.legal_moves(s) if m.startswith("1,0>")}
    assert "1,2" not in dests and "1,3" not in dests, dests  # blocked by (1,2)
    assert "1,1" in dests  # can step to empty square before blocker

    # --- QUEEN: any distance any line, no jumping -----------------------------
    s = MartianState(board=_board({(0, 0): 3, (0, 2): 1}), to_move=0)
    dests = {m.split(">")[1] for m in g.legal_moves(s) if m.startswith("0,0>")}
    assert "0,1" in dests and "0,2" not in dests  # blocked by friendly pawn (no merge: queen exists)
    assert "0,3" not in dests                      # can't jump
    assert "3,3" in dests                          # long diagonal slide
    assert "3,0" in dests                          # long horizontal slide

    # --- ZONE OWNERSHIP: you move only pieces in your zone --------------------
    s = MartianState(board=_board({(0, 0): 1, (0, 7): 1}), to_move=0)
    froms = {m.split(">")[0] for m in g.legal_moves(s)}
    assert froms == {"0,0"}, froms  # player 0 may not move the piece at row 7

    # a piece crossing the canal becomes the opponent's: a drone at (1,3) moves
    # to (1,4), now in zone 1; next player (1) must be able to move it.
    s = MartianState(board=_board({(1, 3): 2, (0, 0): 1, (3, 7): 1}), to_move=0)
    s2 = g.apply_move(s, "1,3>1,4")
    assert s2.to_move == 1
    assert s2.board[(1, 4)] == 2 and _zone(4) == 1
    froms = {m.split(">")[0] for m in g.legal_moves(s2)}
    assert "1,4" in froms, froms  # player 1 now controls the crossed piece

    # --- CAPTURE scores the captured piece's value to the MOVER ---------------
    # player 0 queen at (0,3) captures player 1 queen at (0,5) (slide up).
    s = MartianState(board=_board({(0, 3): 3, (0, 5): 3, (3, 0): 1}), to_move=0)
    s2 = g.apply_move(s, "0,3>0,5")
    assert s2.scores == [3, 0], s2.scores       # queen worth 3 to mover
    assert s2.board.get((0, 5)) == 3 and (0, 3) not in s2.board
    # capturing a drone scores 2, a pawn scores 1
    s = MartianState(board=_board({(0, 3): 2, (0, 4): 1, (3, 0): 1}), to_move=0)
    s2 = g.apply_move(s, "0,3>0,4")
    assert s2.scores == [1, 0], s2.scores       # captured pawn -> 1

    # --- FIELD PROMOTION (merge): only when you lack the result type ----------
    # player 0 has no queens: drone onto pawn (own zone) -> queen.
    s = MartianState(board=_board({(0, 0): 2, (0, 1): 1}), to_move=0)
    moves = g.legal_moves(s)
    assert "0,0>0,1" in moves, moves  # drone slides onto friendly pawn = merge
    s2 = g.apply_move(s, "0,0>0,1")
    assert s2.board == {(0, 1): 3}, s2.board    # both gone, queen appears
    # but if you DO control a queen, the same merge is illegal
    s = MartianState(board=_board({(0, 0): 2, (0, 1): 1, (3, 0): 3}), to_move=0)
    assert "0,0>0,1" not in g.legal_moves(s)
    # pawn+pawn -> drone only when you have no drones
    s = MartianState(board=_board({(0, 0): 1, (1, 1): 1}), to_move=0)
    assert "1,1>0,0" in g.legal_moves(s)
    s2 = g.apply_move(s, "1,1>0,0")
    assert s2.board == {(0, 0): 2}, s2.board

    # --- NO-TAKE-BACK: can't immediately reverse opponent's last move ---------
    # player 1 moves a piece across the canal from (1,4)->(1,3); player 0 may
    # not move it straight back (1,3)->(1,4).
    s = MartianState(board=_board({(1, 4): 2, (3, 7): 1, (3, 0): 1}), to_move=1)
    s2 = g.apply_move(s, "1,4>1,3")             # drone crosses into zone 0
    assert s2.to_move == 0 and s2.last_move == ((1, 4), (1, 3))
    assert "1,3>1,4" not in g.legal_moves(s2), "take-back must be forbidden"
    assert "1,3>1,2" in g.legal_moves(s2)       # other moves of that piece fine

    # --- GAME END: zone empties; higher score wins (reached via apply_move) ---
    # player 0 has a lone pawn in zone 0; moving it across the canal empties
    # zone 0 and ends the game. Give player 0 a higher score.
    s = MartianState(board=_board({(1, 3): 1, (3, 7): 3}), to_move=0,
                     scores=[5, 2])
    s2 = g.apply_move(s, "1,3>0,4")             # pawn crosses; zone 0 now empty
    assert g.is_terminal(s2)
    assert g.returns(s2) == [1.0, -1.0], g.returns(s2)   # higher score wins
    # tie -> the player who made the ending move wins
    s = MartianState(board=_board({(1, 3): 1, (3, 7): 3}), to_move=0,
                     scores=[4, 4])
    s2 = g.apply_move(s, "1,3>0,4")
    assert g.is_terminal(s2) and g.returns(s2) == [1.0, -1.0]  # mover (0) wins tie

    # capturing into the opponent's last piece can also empty a zone
    s = MartianState(board=_board({(0, 3): 3, (0, 4): 1}), to_move=0,
                     scores=[0, 0])
    s2 = g.apply_move(s, "0,3>0,4")             # captures p1's only piece -> zone 1 empty
    assert g.is_terminal(s2)
    assert s2.scores == [1, 0] and g.returns(s2) == [1.0, -1.0]

    # --- serialize round-trips (JSON-able, incl. scores & last_move) ----------
    for st in (g.initial_state(), s2,
               MartianState(board=_board({(1, 4): 2}), to_move=1,
                            scores=[3, 7], last_move=((1, 5), (1, 4)), ply=9)):
        data = g.serialize(st)
        json.dumps(data)                        # must be JSON-able
        again = g.serialize(g.deserialize(data))
        assert again == data, (data, again)

    # --- a full random self-play terminates and scores well-formed ------------
    import random
    rng = random.Random(7)
    for _ in range(50):
        st = g.initial_state()
        steps = 0
        while not g.is_terminal(st):
            mv = rng.choice(g.legal_moves(st))
            st = g.apply_move(st, mv)
            steps += 1
            assert steps <= 1000
        ret = g.returns(st)
        assert len(ret) == 2 and all(x in (-1.0, 0.0, 1.0) for x in ret)
        assert ret in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
