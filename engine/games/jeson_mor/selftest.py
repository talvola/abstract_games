"""Standalone correctness anchor for Jeson Mor.

Run with:  PYTHONPATH=. python3 games/jeson_mor/selftest.py
Pure stdlib + the agp package only. Prints SELFTEST OK and exits 0 on success.

No published perft exists for Jeson Mor, so the anchor is a set of baked rule
assertions:
  (1) every piece moves as a chess KNIGHT (the (1,2) leaper) and MAY jump over
      pieces — 8 targets from an open centre, fewer from edge/corner;
  (2) a knight captures an enemy knight by landing on it;
  (3) the WIN condition: occupy the central square (4,4), then on a LATER turn
      move OFF it -> the mover wins (occupy-then-vacate); merely landing on the
      centre is NOT a win; a player with no knights / no move loses.
"""

from __future__ import annotations

import sys

from games.jeson_mor.game import JesonMor, JMState, N, CENTER


def fail(msg):
    print("SELFTEST FAIL:", msg)
    sys.exit(1)


def targets_from(g, board, frm):
    """Set of destination cells the legal moves offer for the piece at `frm`."""
    s = JMState(board=board, to_move=board[frm], ply=0, winner=-1)
    out = set()
    for mv in g.legal_moves(s):
        fs, ts = mv.split(">")
        if fs == f"{frm[0]},{frm[1]}":
            c, r = ts.split(",")
            out.add((int(c), int(r)))
    return out


def main():
    g = JesonMor()

    # ---- starting position --------------------------------------------------
    s0 = g.initial_state()
    assert g.num_players == 2
    if len(s0.board) != 18:
        fail(f"start should have 18 knights, got {len(s0.board)}")
    for c in range(N):
        if s0.board.get((c, 0)) != 0:
            fail(f"White knight missing at {c},0")
        if s0.board.get((c, N - 1)) != 1:
            fail(f"Black knight missing at {c},8")
    if g.current_player(s0) != 0:
        fail("White (0) must move first")
    if g.is_terminal(s0):
        fail("start should not be terminal")
    # round-trip
    if g.serialize(g.deserialize(g.serialize(s0))) != g.serialize(s0):
        fail("serialize does not round-trip")

    # ---- (1) KNIGHT movement: 8 targets from an open centre -----------------
    board = {CENTER: 0}
    tg = targets_from(g, board, CENTER)
    expect = {
        (5, 6), (6, 5), (3, 6), (2, 5), (5, 2), (6, 3), (3, 2), (2, 3),
    }
    if tg != expect:
        fail(f"open-centre knight should have 8 L-targets {expect}, got {tg}")
    if len(tg) != 8:
        fail(f"open-centre knight should have exactly 8 targets, got {len(tg)}")

    # corner: a knight in the corner has exactly 2 targets
    board = {(0, 0): 0}
    tg = targets_from(g, board, (0, 0))
    if tg != {(1, 2), (2, 1)}:
        fail(f"corner knight should have 2 targets, got {tg}")

    # edge (middle of an edge): 4 targets
    board = {(4, 0): 0}
    tg = targets_from(g, board, (4, 0))
    if tg != {(2, 1), (6, 1), (3, 2), (5, 2)}:
        fail(f"edge-centre knight should have 4 targets, got {tg}")

    # ---- (1b) MAY JUMP over intervening pieces ------------------------------
    # Surround a central knight with friendly + enemy knights on all 8 ortho/diag
    # neighbours; the knight must still reach all 8 of its L-targets (jumping).
    board = {CENTER: 0}
    blockers = [(3, 3), (3, 4), (3, 5), (4, 3), (4, 5), (5, 3), (5, 4), (5, 5)]
    for i, b in enumerate(blockers):
        board[b] = i % 2  # mix of friendly (0) and enemy (1)
    tg = targets_from(g, board, CENTER)
    if tg != expect:
        fail(f"knight must JUMP surrounding pieces and still reach 8 targets, got {tg}")

    # ---- (2) CAPTURE by landing on an enemy knight --------------------------
    board = {(2, 3): 0, (4, 4): 1}  # White knight at (2,3) can leap to (4,4) capturing Black
    s = JMState(board=board, to_move=0, ply=0, winner=-1)
    if "2,3>4,4" not in set(g.legal_moves(s)):
        fail("capture move 2,3>4,4 onto enemy not offered")
    s2 = g.apply_move(s, "2,3>4,4")
    if s2.board.get((4, 4)) != 0:
        fail("after capture the destination must hold the capturing White knight")
    if (2, 3) in s2.board:
        fail("source must be vacated after the move")
    if len(s2.board) != 1:
        fail(f"capture should remove the enemy knight (1 piece left), got {len(s2.board)}")
    # may NOT land on a friendly knight
    board = {(2, 3): 0, (4, 4): 0}
    s = JMState(board=board, to_move=0, ply=0, winner=-1)
    if "2,3>4,4" in set(g.legal_moves(s)):
        fail("knight must not land on a friendly knight")

    # ---- (3) WIN: occupy-then-vacate the centre -----------------------------
    # (3a) landing ON the centre is NOT a win, and the game continues.
    board = {(2, 3): 0, (0, 8): 1}  # White can leap (2,3)->(4,4); Black has a move
    s = JMState(board=board, to_move=0, ply=0, winner=-1)
    s_on = g.apply_move(s, "2,3>4,4")
    if s_on.winner != -1:
        fail("merely LANDING on the centre must NOT win")
    if s_on.board.get(CENTER) != 0:
        fail("White knight should now sit on the centre")
    if g.is_terminal(s_on):
        fail("sitting on the centre must not be terminal (opponent still has a move)")

    # (3b) on a LATER turn, moving OFF the centre wins for the mover.
    # Build a position with a White knight already on (4,4) and Black to move,
    # then have Black move (irrelevant), then White leaves the centre and wins.
    board = {CENTER: 0, (0, 8): 1, (8, 0): 0}  # White on centre + a spare; Black piece
    s = JMState(board=board, to_move=1, ply=5, winner=-1)  # Black to move
    s_black = g.apply_move(s, "0,8>2,7")  # Black makes some move
    if s_black.winner != -1:
        fail("Black's unrelated move must not win")
    if s_black.to_move != 0:
        fail("after Black's move it should be White's turn")
    # White now vacates the centre -> White wins.
    off = None
    for mv in g.legal_moves(s_black):
        if mv.startswith(f"{CENTER[0]},{CENTER[1]}>"):
            off = mv
            break
    if off is None:
        fail("White on the centre should have legal moves leaving it")
    s_win = g.apply_move(s_black, off)
    if s_win.winner != 0:
        fail("moving a knight OFF the centre (occupy-then-vacate) must win for White")
    if not g.is_terminal(s_win):
        fail("a centre-vacate win must be terminal")
    if g.returns(s_win) != [1.0, -1.0]:
        fail(f"White centre win should return [1,-1], got {g.returns(s_win)}")

    # (3c) a move that neither starts on the centre nor empties the enemy does not win.
    board = {(0, 0): 0, (8, 8): 1}
    s = JMState(board=board, to_move=0, ply=0, winner=-1)
    s2 = g.apply_move(s, "0,0>1,2")
    if s2.winner != -1:
        fail("an ordinary move must not win")

    # ---- (4) annihilation: capturing the opponent's LAST knight wins --------
    board = {(2, 3): 0, (4, 4): 1}  # White captures Black's only knight
    s = JMState(board=board, to_move=0, ply=0, winner=-1)
    s2 = g.apply_move(s, "2,3>4,4")
    if s2.winner != 0:
        fail("capturing the opponent's last knight must win for the capturer")
    if not g.is_terminal(s2):
        fail("annihilation win must be terminal")
    if g.returns(s2) != [1.0, -1.0]:
        fail(f"annihilation win should return [1,-1], got {g.returns(s2)}")

    # ---- (5) no legal move -> the side to move loses ------------------------
    # White to move but has zero knights -> White loses (Black wins).
    board = {(8, 8): 1}
    s = JMState(board=board, to_move=0, ply=0, winner=-1)
    if g.legal_moves(s) != []:
        fail("a player with no knights must have no legal moves")
    if not g.is_terminal(s):
        fail("a player with no move must be terminal")
    if g.returns(s) != [-1.0, 1.0]:
        fail(f"White with no knights should lose: expected [-1,1], got {g.returns(s)}")

    # ---- (6) purity: apply_move must not mutate the input state --------------
    s0 = g.initial_state()
    snap = g.serialize(s0)
    _ = g.apply_move(s0, g.legal_moves(s0)[0])
    if g.serialize(s0) != snap:
        fail("apply_move mutated the input state")

    # ---- (7) random self-play terminates with well-formed returns -----------
    import random
    rng = random.Random(0)
    for seed in range(15):
        rng.seed(seed)
        st = g.initial_state()
        steps = 0
        while not g.is_terminal(st) and steps < 2000:
            lm = g.legal_moves(st)
            if not lm:
                fail("non-terminal state returned no legal moves")
            st = g.apply_move(st, rng.choice(lm))
            steps += 1
        if not g.is_terminal(st):
            fail("game did not terminate within step budget")
        ret = g.returns(st)
        if len(ret) != 2 or sorted(ret) not in ([-1.0, 1.0], [0.0, 0.0]):
            fail(f"bad terminal returns {ret}")

    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
