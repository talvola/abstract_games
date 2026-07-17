"""Selftest for Jul-Gonu — frozen anchors + scripted rule positions.

SOLVED-GAME ANCHOR (one-time full solve, games/jul_gonu/_solve.py — not run
here): forward BFS enumerated the entire reachable (board, side-to-move) graph
ignoring the repetition ban, then retrograde win/loss propagation with
cycle-bound positions defaulting to DRAW.  Result (frozen 2026-07-17,
~4.5 min pure Python; bitboard generator differentially identical to game.py
on 400 random positions):
    reachable states = 3,412,738   move edges = 21,039,712
    values: WIN(to-move) 1,315,354 / LOSS 807,911 / DRAW(ban-free) 1,289,473
    ROOT = DRAW (cycle-bound) in the ban-free game
So Jul-Gonu WITHOUT the repetition ban (infinite shuffling scored as a draw)
is a DRAW — neither side can force a win against repetition. The superko ban
is what makes real play decisive; its exact value is path-dependent (history
matters inside the 1.29M-state draw region) and remains open. Resolved
(WIN/LOSS) positions keep their exact value under superko play PROVIDED the
game's earlier history stayed inside the draw region — a minimal-dist winning
line strictly decreases dist every ply, so it never revisits a position and
never collides with the draw-region history (see _solve.py for the argument
and full stats).

This file stays fast + pure-stdlib: frozen opening counts, scripted captures
(single, line-of-two, double-direction), sandwich safety, the repetition ban,
lone-piece and stalemate wins reached via apply_move, serialize round-trip.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.jul_gonu.game import JulGonu, JGState  # noqa: E402


def state(black, white, to_move):
    """Hand-built position (empty history => the repetition ban is not binding)."""
    board = {c: 0 for c in black}
    board.update({c: 1 for c in white})
    return JGState(board=board, to_move=to_move)


def run():
    g = JulGonu()

    # --- opening: frozen move counts -----------------------------------
    s0 = g.initial_state()
    assert g.current_player(s0) == 0 and not g.is_terminal(s0)
    ms = g.legal_moves(s0)
    assert len(ms) == 4, ms                     # each back-rank piece steps forward
    assert sorted(ms) == ["0,0>0,1", "1,0>1,1", "2,0>2,1", "3,0>3,1"], ms
    s1 = g.apply_move(s0, "1,0>1,1")
    assert len(g.legal_moves(s1)) == 4          # White mirrors: four forward steps

    # --- repetition ban (positional superko) ---------------------------
    s2 = g.apply_move(s1, "1,3>1,2")            # White advances
    s3 = g.apply_move(s2, "1,1>1,0")            # Black retreats (new position)
    assert "1,1>1,0" in g.legal_moves(s2)
    ms3 = g.legal_moves(s3)
    assert "1,2>1,3" not in ms3, ms3            # would recreate the initial position
    assert any(m.startswith("1,2>") for m in ms3)  # ...but the piece may go elsewhere

    # --- single custodial capture --------------------------------------
    s = state(black=[(1, 1), (3, 0)], white=[(2, 0), (0, 3), (1, 3)], to_move=0)
    assert "1,1>1,0" in g.legal_moves(s)
    t = g.apply_move(s, "1,1>1,0")
    assert (2, 0) not in t.board and t.board[(1, 0)] == 0 and t.board[(3, 0)] == 0
    assert t.winner is None and not g.is_terminal(t)
    assert g.describe_move(s, "1,1>1,0") == "b2-b1xc1"

    # --- line-of-two capture (both flanked men removed) ----------------
    s = state(black=[(0, 1), (3, 0)], white=[(1, 0), (2, 0), (0, 3), (1, 3)], to_move=0)
    t = g.apply_move(s, "0,1>0,0")
    assert (1, 0) not in t.board and (2, 0) not in t.board
    assert sum(1 for o in t.board.values() if o == 1) == 2 and t.winner is None

    # --- double-direction capture (row + column on one move) -----------
    s = state(black=[(0, 1), (3, 1), (1, 3)],
              white=[(2, 1), (1, 2), (0, 3), (3, 3)], to_move=0)
    t = g.apply_move(s, "0,1>1,1")
    assert (2, 1) not in t.board and (1, 2) not in t.board   # both captures fired
    assert sum(1 for o in t.board.values() if o == 1) == 2 and t.winner is None

    # --- sandwich safety: moving INTO a sandwich is safe; capture is
    # --- active-only (an uninvolved enemy move captures nothing) --------
    s = state(black=[(1, 0), (3, 3)], white=[(0, 1), (2, 1), (0, 3)], to_move=0)
    t = g.apply_move(s, "1,0>1,1")              # step between the two whites
    assert t.board.get((1, 1)) == 0             # not captured
    u = g.apply_move(t, "0,3>0,2")              # White moves elsewhere
    assert u.board.get((1, 1)) == 0             # still not captured (no passive capture)

    # --- lone-piece win via apply_move (incl. capture-to-zero) ---------
    s = state(black=[(1, 1), (3, 0)], white=[(2, 0), (0, 3)], to_move=0)
    t = g.apply_move(s, "1,1>1,0")              # captures (2,0): White down to 1
    assert t.winner == 0 and g.is_terminal(t) and g.returns(t) == [1.0, -1.0]
    s = state(black=[(0, 1), (3, 0)], white=[(1, 0), (2, 0)], to_move=0)
    t = g.apply_move(s, "0,1>0,0")              # line-of-two takes White's last 2
    assert t.winner == 0 and g.is_terminal(t) and g.returns(t) == [1.0, -1.0]

    # --- stalemate win via apply_move ----------------------------------
    s = state(black=[(0, 2), (1, 3), (2, 3), (3, 1)], white=[(0, 3), (3, 3)], to_move=0)
    t = g.apply_move(s, "3,1>3,2")              # completes the blockade, no capture
    assert len(t.board) == 6 and t.winner is None
    assert g.legal_moves(t) == [] and g.is_terminal(t)
    assert g.returns(t) == [1.0, -1.0]          # stalemated player (White) loses

    # --- heuristic shape (one payoff per seat) -------------------------
    h = g.heuristic(s1)
    assert isinstance(h, list) and len(h) == 2 and h[0] == -h[1]

    # --- serialize round-trip (incl. history) + random playout ---------
    rng = random.Random(11)
    for game_i in range(3):
        s = g.initial_state()
        while not g.is_terminal(s):
            d = g.serialize(s)
            json.dumps(d)
            assert g.serialize(g.deserialize(d)) == d
            s = g.apply_move(s, rng.choice(g.legal_moves(s)))
        r = g.returns(s)
        assert len(r) == 2 and r in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])
        assert s.ply <= 250

    print("jul_gonu selftest: OK")


if __name__ == "__main__":
    run()
