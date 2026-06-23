"""Pah Tum correctness anchor — pure stdlib, fast.

Run: PYTHONPATH=. python3 games/pah_tum/selftest.py

No published perft exists for Pah Tum, so the anchor is a set of baked rule
assertions: the scoring table, the no-diagonal rule, the fixed symmetric blocked
layout, place-until-full play, and a few hand-built scored boards.
"""

from games.pah_tum.game import PahTum, PahTumState, run_score, _blocked_cells


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    g = PahTum()

    # (1) Scoring table — the published standard.
    check(run_score(1) == 0, "run 1 scores 0")
    check(run_score(2) == 0, "run 2 (a double) scores 0")
    check(run_score(3) == 3, "run 3 scores 3")
    check(run_score(4) == 10, "run 4 scores 10")
    check(run_score(5) == 25, "run 5 scores 25")
    check(run_score(6) == 56, "run 6 scores 56")
    check(run_score(7) == 88, "run 7 scores 88")
    # extension beyond table is strictly increasing
    check(run_score(8) > 88 and run_score(9) > run_score(8), "extension increases")

    # (2) Blocked layout: even count, symmetric, holds no stone, off-board play.
    n = 7
    for layout in ("diamond", "cross"):
        b = _blocked_cells(n, layout)
        check(len(b) == 4, f"{layout}: 4 blocked cells (even)")
        for (c, r) in b:
            check((n - 1 - c, n - 1 - r) in b, f"{layout}: 180-symmetric")
            check((r, c) in b, f"{layout}: diagonal-symmetric")
    s = g.initial_state()
    blocked = g._blocked(s)
    legal = set(g.legal_moves(s))
    for (c, r) in blocked:
        check(f"{c},{r}" not in legal, "blocked cells are not legal placements")
    check(len(legal) == n * n - 4, "45 playable cells at start")

    # (3) Alternating placement until full; parity (odd playable -> 23 vs 22).
    cnt = [0, 0]
    cur = s
    rng_moves = g.legal_moves(cur)
    while not g.is_terminal(cur):
        mv = g.legal_moves(cur)[0]
        cnt[g.current_player(cur)] += 1
        cur = g.apply_move(cur, mv)
    check(g.is_terminal(cur), "game terminates when board fills")
    check(cnt == [23, 22], f"placement parity 23/22, got {cnt}")
    check(len(cur.board) == 45, "45 stones on a full board")

    # (4) Hand-built run-scoring checks.
    # A row of exactly 4 same-colour stones scores 10; an isolated double scores 0.
    def score_board(board, n=7, layout="diamond"):
        return g._compute_scores(board, n, _blocked_cells(n, layout))

    # Place a run of 4 for player 0 in an empty (no blocked interference) corner row.
    board = {(0, 0): 0, (1, 0): 0, (2, 0): 0, (3, 0): 0}
    sc = score_board(board)
    check(sc == [10, 0], f"row of 4 -> [10,0], got {sc}")

    # A run of exactly 2 scores nothing.
    board = {(0, 0): 1, (1, 0): 1}
    sc = score_board(board)
    check(sc == [0, 0], f"a double scores 0, got {sc}")

    # A vertical run of 3 scores 3.
    board = {(6, 0): 0, (6, 1): 0, (6, 2): 0}
    sc = score_board(board)
    check(sc == [3, 0], f"column of 3 -> [3,0], got {sc}")

    # Diagonals do NOT score: three on a diagonal -> 0.
    board = {(0, 0): 0, (1, 1): 0, (2, 2): 0}
    sc = score_board(board)
    check(sc == [0, 0], f"diagonal of 3 scores 0, got {sc}")

    # A blocked cell breaks a run: stones either side of a blocked cell are two
    # separate runs, not one. Diamond layout blocks (2,2),(4,2),(2,4),(4,4).
    # Row r=2: cols 0,1 then (2,2) blocked, then 3, then (4,2) blocked, then 5,6.
    board = {(0, 2): 0, (1, 2): 0, (3, 2): 0, (5, 2): 0, (6, 2): 0}
    sc = score_board(board, layout="diamond")
    # runs: [0,1]=2 (0pts), [3]=1 (0), [5,6]=2 (0) -> nothing
    check(sc == [0, 0], f"blocked cells split runs, got {sc}")

    # Now make the left segment a 3-run that is NOT bridged across the boulder:
    # put stones at (0,2),(1,2) plus none at (2,2 blocked); add (3,2),(5,2),(6,2)
    # all player 0 — still no run reaches 3 because (2,2) and (4,2) are blocked.
    # Build a clean 3-run on row 0 (no boulders): (0,0),(1,0),(2,0).
    board = {(0, 0): 0, (1, 0): 0, (2, 0): 0,
             (4, 0): 1, (5, 0): 1, (6, 0): 1}
    sc = score_board(board)
    check(sc == [3, 3], f"two separate 3-runs -> [3,3], got {sc}")

    # (5) A 5-run scores 25 and beats a 4-run (10): higher total wins.
    board = {(0, 0): 0, (1, 0): 0, (2, 0): 0, (3, 0): 0, (4, 0): 0,  # 5 -> 25
             (0, 6): 1, (1, 6): 1, (2, 6): 1, (3, 6): 1}             # 4 -> 10
    sc = score_board(board)
    check(sc == [25, 10], f"5-run vs 4-run -> [25,10], got {sc}")

    # (6) Full-game win-as-event: construct a near-full board, verify winner is set
    # only when the last cell is filled and matches the higher score.
    # Build all-Red board to force a clear Red win (every full row/col is a run).
    s2 = g.initial_state()
    cur = s2
    # Greedily fill: player to move always plays first legal cell, but to get a
    # deterministic non-draw we just check the engine sets a winner and returns
    # are consistent with stored scores.
    while not g.is_terminal(cur):
        cur = g.apply_move(cur, g.legal_moves(cur)[0])
    check(cur.winner in (0, 1, 2), "winner field set on full board")
    ret = g.returns(cur)
    if cur.winner == 0:
        check(ret == [1.0, -1.0] and cur.scores[0] > cur.scores[1], "p0 win consistent")
    elif cur.winner == 1:
        check(ret == [-1.0, 1.0] and cur.scores[1] > cur.scores[0], "p1 win consistent")
    else:
        check(ret == [0.0, 0.0] and cur.scores[0] == cur.scores[1], "draw consistent")

    # (7) serialize round-trips.
    d = g.serialize(cur)
    cur2 = g.deserialize(d)
    check(g.serialize(cur2) == d, "serialize round-trips")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
