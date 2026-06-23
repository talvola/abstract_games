"""Selftest for Five Field Kono — pure stdlib, fast.

Anchor = baked rule assertions (no published perft):
  (1) 5x5 board; each player has exactly 7 pieces at the documented start
      (whole back row of 5 + the two outer second-row points).
  (2) a piece moves one step diagonally to an adjacent EMPTY cell; orthogonal
      moves are illegal; there are no captures ever.
  (3) WIN = be first to move ALL your pieces onto the opponent's starting cells.
Plus a hand-built diagonal move, rejection of an orthogonal move, and a
near-win race check.

Run: PYTHONPATH=. python3 games/five_field_kono/selftest.py
"""

import sys

from games.five_field_kono.game import FiveFieldKono, KonoState, _home, N


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def main():
    g = FiveFieldKono()
    s = g.initial_state()

    # (1) Board geometry + piece counts / exact layout.
    spec = g.render(s)
    check(spec["board"]["type"] == "square", "board is square")
    check(spec["board"]["width"] == 5 and spec["board"]["height"] == 5, "5x5 board")
    check(N == 5, "N == 5")

    p0 = {cell for cell, pl in s.board.items() if pl == 0}
    p1 = {cell for cell, pl in s.board.items() if pl == 1}
    check(len(p0) == 7, f"player 0 has 7 pieces (got {len(p0)})")
    check(len(p1) == 7, f"player 1 has 7 pieces (got {len(p1)})")

    expect0 = {(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (0, 1), (4, 1)}
    expect1 = {(0, 4), (1, 4), (2, 4), (3, 4), (4, 4), (0, 3), (4, 3)}
    check(p0 == expect0, f"player 0 start layout {sorted(p0)}")
    check(p1 == expect1, f"player 1 start layout {sorted(p1)}")
    check(_home(0) == expect0 and _home(1) == expect1, "_home matches layout")
    # No overlap between homes.
    check(not (expect0 & expect1), "home sets disjoint")
    # Same parity multiset -> race is feasible.
    par0 = sorted((c + r) % 2 for c, r in expect0)
    par1 = sorted((c + r) % 2 for c, r in expect1)
    check(par0 == par1, "home sets share parity multiset (race feasible)")

    # Cells r=2 (middle) and inner r=1/r=3 start empty.
    for c in range(5):
        check((c, 2) not in s.board, f"middle ({c},2) empty at start")
    for c in (1, 2, 3):
        check((c, 1) not in s.board, f"inner ({c},1) empty at start")
        check((c, 3) not in s.board, f"inner ({c},3) empty at start")

    # (2) Movement: only diagonal-to-empty; no orthogonal; no captures.
    moves = g.legal_moves(s)
    check(moves and "pass" not in moves, "start has real moves")
    for m in moves:
        frm, to = m.split(">")
        fc, fr = (int(x) for x in frm.split(","))
        tc, tr = (int(x) for x in to.split(","))
        check(abs(tc - fc) == 1 and abs(tr - fr) == 1, f"move {m} is diagonal one step")
        check((tc, tr) not in s.board, f"move {m} lands on empty cell")

    # A specific legal diagonal: (0,1)->(1,2) is empty diagonally adjacent.
    check("0,1>1,2" in moves, "expected diagonal 0,1>1,2 legal")
    s2 = g.apply_move(s, "0,1>1,2")
    check((1, 2) in s2.board and s2.board[(1, 2)] == 0, "piece moved to (1,2)")
    check((0, 1) not in s2.board, "source (0,1) vacated")
    check(len([1 for v in s2.board.values() if v == 0]) == 7, "still 7 pieces (no loss)")
    check(s2.to_move == 1, "turn passed to player 1")

    # Orthogonal move must NOT be legal (e.g. 1,0 forward to 1,1 is empty but orthogonal).
    check((1, 1) not in s.board, "target (1,1) is empty")
    check("1,0>1,1" not in moves, "orthogonal 1,0>1,1 rejected")
    # Two-step diagonal also illegal.
    check("0,0>2,2" not in g.legal_moves(s2) and "0,0>2,2" not in moves, "no two-step jump")

    # No captures: a diagonal onto an enemy/own piece is never offered.
    # Construct: enemy sits diagonally adjacent to a friendly piece.
    cap_board = {(2, 2): 0, (3, 3): 1}
    cs = KonoState(board=cap_board, to_move=0)
    cmoves = g.legal_moves(cs)
    check("2,2>3,3" not in cmoves, "cannot move onto an occupied (no capture)")
    check("2,2>1,1" in cmoves and "2,2>1,3" in cmoves and "2,2>3,1" in cmoves,
          "free diagonals available")

    # (3) Win condition: all own pieces on opponent's home set.
    # Build a near-win: player 0 has 6 pieces already on player 1's home, 1 to go.
    target = _home(1)
    tlist = sorted(target)
    near = {}
    for cell in tlist[:6]:
        near[cell] = 0          # 6 of player 0's pieces parked on the goal
    # last piece one diagonal step from the remaining target slot
    last_target = tlist[6]
    ltc, ltr = last_target
    # find a diagonal source that is empty and on-board
    src = None
    for dc, dr in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        sc, sr = ltc + dc, ltr + dr
        if 0 <= sc < 5 and 0 <= sr < 5 and (sc, sr) not in near:
            src = (sc, sr)
            break
    check(src is not None, "found a source for the winning move")
    near[src] = 0               # 7th piece of player 0
    # give player 1 a token piece somewhere harmless so state is sensible
    filler = None
    for c in range(5):
        for r in range(5):
            if (c, r) not in near and (c, r) not in target:
                filler = (c, r)
                break
        if filler:
            break
    near[filler] = 1
    ns = KonoState(board=near, to_move=0)
    check(not g.is_terminal(ns), "near-win not yet terminal")
    win_move = f"{src[0]},{src[1]}>{last_target[0]},{last_target[1]}"
    check(win_move in g.legal_moves(ns), f"winning move {win_move} legal")
    won = g.apply_move(ns, win_move)
    check(won.winner == 0, "player 0 wins by occupying opponent home")
    check(g.is_terminal(won), "win is terminal")
    check(g.returns(won) == [1.0, -1.0], "returns reflect player 0 win")

    # Sanity: an early position is NOT terminal and returns are 0/0 only at draw.
    check(not g.is_terminal(s), "start not terminal")

    # serialize round-trips
    d = g.serialize(s2)
    s2b = g.deserialize(d)
    check(g.serialize(s2b) == d, "serialize round-trips")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
