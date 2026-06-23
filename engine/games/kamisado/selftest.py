"""Kamisado correctness anchor — pure-stdlib, fast.

No published perft exists for Kamisado, so the anchor is a set of baked rule
assertions plus a few hand-built positions:

(1) 8x8 board where every cell is one of 8 fixed colours, and the layout is the
    standard Kamisado pattern: a Latin square (each colour once per row/column)
    with 180-degree rotational symmetry.
(2) each player has 8 towers, one per colour, on their home row, each on the cell
    of its own colour.
(3) a tower slides straight FORWARD or diagonally FORWARD any number of empty
    cells (no sideways, no backward, no jumping).
(4) the colour of the cell a tower lands on dictates which colour tower the
    opponent must move next (colour chaining); the first move is free.
(5) WIN = move a tower onto the opponent's home row.
(6) deadlock: a player whose required tower has no move must pass; the obligation
    bounces to the colour of the cell the blocked tower stands on. Simultaneous
    deadlock = draw.

Run: PYTHONPATH=. python3 games/kamisado/selftest.py
"""

import sys

from games.kamisado.game import (
    Kamisado, KState, LAYOUT, COLORS, COLOR_HEX, cell_color, N, _far_row,
)


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def main():
    g = Kamisado()

    # (1) board geometry + colour layout invariants -----------------------
    check(N == 8, "board is 8x8")
    check(len(LAYOUT) == 8 and all(len(row) == 8 for row in LAYOUT),
          "layout is 8 rows of 8")
    all_codes = set("".join(LAYOUT))
    check(all_codes == set(COLORS) and len(COLORS) == 8,
          "exactly 8 distinct colours used")
    check(all(c in COLOR_HEX for c in COLORS), "every colour has a hex")
    # Latin square: each colour once per row and per column.
    for r in range(8):
        check(len(set(LAYOUT[r])) == 8, f"row {r} has all 8 colours")
    for c in range(8):
        col = {LAYOUT[r][c] for r in range(8)}
        check(len(col) == 8, f"col {c} has all 8 colours")
    # 180-degree rotational symmetry.
    for r in range(8):
        for c in range(8):
            check(LAYOUT[r][c] == LAYOUT[7 - r][7 - c],
                  "layout has 180-degree rotational symmetry")

    # (2) starting setup: 8 towers per player, one of each colour, on home row,
    # each on its own colour's cell -------------------------------------
    s = g.initial_state()
    p0 = [(c, r, col) for (c, r), (pl, col) in s.board.items() if pl == 0]
    p1 = [(c, r, col) for (c, r), (pl, col) in s.board.items() if pl == 1]
    check(len(p0) == 8 and len(p1) == 8, "8 towers each")
    check({col for _, _, col in p0} == set(COLORS), "player 0 has one of each colour")
    check({col for _, _, col in p1} == set(COLORS), "player 1 has one of each colour")
    check(all(r == 0 for _, r, _ in p0), "player 0 towers on row 0")
    check(all(r == 7 for _, r, _ in p1), "player 1 towers on row 7")
    for (c, r), (pl, col) in s.board.items():
        check(col == cell_color(c, r), "each tower starts on the cell of its colour")
    check(g.current_player(s) == 0, "player 0 starts")
    check(s.required is None, "first move is free")

    # round-trip serialization
    check(g.serialize(g.deserialize(g.serialize(s))) == g.serialize(s),
          "serialize round-trips")

    # (4) first move is free: every player-0 tower with any move is offered
    moves = g.legal_moves(s)
    check(all(">" in m for m in moves), "first-move legal moves are slides")
    sources = {m.split(">")[0] for m in moves}
    # all 8 home towers can move forward off the back row (front is empty)
    check(len(sources) == 8, "first move free: all 8 towers movable")

    # (3) movement: forward straight + forward diagonal, no sideways/backward,
    # no jumping. Build a sparse position to assert exact reachable set.
    # One player-0 tower (colour 'O') alone at (3,3); nothing else around it
    # except a blocker to test no-jump.
    b = {(3, 3): (0, "O")}
    s2 = KState(board=b, to_move=0, required=None)
    mv = {m.split(">")[1] for m in g.legal_moves(s2)}
    # forward = increasing r for player 0. A tower slides ANY number of empty
    # cells. straight up the file: (3,4..7); diagonals run to the edge:
    # left  (2,4),(1,5),(0,6); right (4,4),(5,5),(6,6),(7,7).
    expect = {"3,4", "3,5", "3,6", "3,7",
              "2,4", "1,5", "0,6",
              "4,4", "5,5", "6,6", "7,7"}
    check(mv == expect, f"forward-only slide set wrong: {sorted(mv)}")
    check("3,2" not in mv and "2,2" not in mv, "no backward movement")
    check("2,3" not in mv and "4,3" not in mv, "no sideways movement")

    # no jumping: place a blocker straight ahead at (3,5)
    b2 = {(3, 3): (0, "O"), (3, 5): (1, "B")}
    s3 = KState(board=b2, to_move=0, required=None)
    mv3 = {m.split(">")[1] for m in g.legal_moves(s3)}
    check("3,4" in mv3, "can move up to a blocker")
    check("3,5" not in mv3 and "3,6" not in mv3 and "3,7" not in mv3,
          "cannot land on or jump a blocker")

    # (4) colour chaining: after a move, the opponent must move the colour of the
    # landed cell, and only that tower is movable. Hand-built chain.
    landed = (4, 4)  # cell_color here determines next required colour
    next_colour = cell_color(*landed)
    b4 = {(3, 3): (0, "O")}
    # give player 1 a full home row so the required colour tower exists
    for c in range(8):
        b4[(c, 7)] = (1, cell_color(c, 7))
    s4 = KState(board=b4, to_move=0, required=None)
    s4b = g.apply_move(s4, "3,3>4,4")
    check(s4b.to_move == 1, "turn passes to opponent")
    check(s4b.required == next_colour,
          f"required colour = landed cell colour ({next_colour})")
    movers = {g.deserialize(g.serialize(s4b)).board[
        (int(m.split(">")[0].split(',')[0]), int(m.split(">")[0].split(',')[1]))][1]
        for m in g.legal_moves(s4b) if m != "pass"}
    check(movers == {next_colour}, "only the required-colour tower may move")

    # (5) reach-home win via apply_move. Put a player-0 tower one step from row 7.
    b5 = {(0, 6): (0, "O"), (0, 7): None}
    del b5[(0, 7)]
    s5 = KState(board={(0, 6): (0, "O")}, to_move=0, required="O")
    check(not g.is_terminal(s5), "not terminal before the winning move")
    s5b = g.apply_move(s5, "0,6>0,7")
    check(_far_row(0) == 7, "player 0's far row is 7")
    check(s5b.winner == 0, "reaching the far row wins")
    check(g.is_terminal(s5b), "win is terminal")
    check(g.returns(s5b) == [1.0, -1.0], "winner returns +1/-1")

    # win for player 1 too (far row 0)
    s5c = KState(board={(0, 1): (1, "O")}, to_move=1, required="O")
    s5d = g.apply_move(s5c, "0,1>0,0")
    check(s5d.winner == 1 and g.returns(s5d) == [-1.0, 1.0],
          "player 1 wins by reaching row 0")

    # (6) deadlock: required tower has no move -> only legal move is "pass", and
    # passing bounces the obligation to the colour the blocked tower stands on.
    # Blocked tower: player 0 'O' at (3,3); fill (2,4),(3,4),(4,4) with friendly
    # towers so all its forward cells are occupied -> it cannot move.
    bd = {(3, 3): (0, "O"),
          (2, 4): (0, "B"), (3, 4): (0, "P"), (4, 4): (0, "K")}
    sd = KState(board=bd, to_move=0, required="O")
    lm = g.legal_moves(sd)
    check(lm == ["pass"], f"blocked required tower -> only pass, got {lm}")
    # the colour the blocked 'O' tower stands on:
    bounce_colour = cell_color(3, 3)
    sd2 = g.apply_move(sd, "pass")
    check(sd2.to_move == 1, "pass hands the turn to opponent")
    check(sd2.required == bounce_colour,
          f"obligation bounces to colour under blocked tower ({bounce_colour})")

    # Full deadlock -> the last player to move a tower loses (official rule).
    # Reach it via a real move so last_mover is set, then a double pass:
    #   player 0 moves a tower (sets last_mover=0), landing so that player 1's
    #   required tower is blocked; player 1 passes, bouncing to a colour whose
    #   player-0 tower is ALSO blocked -> deadlock -> last mover (player 0) loses.
    # Build it concretely. Player 0 'R' at (0,0) will move straight to (0,1);
    # cell (0,1) colour dictates player 1's required colour. Box everything else.
    landed = (0, 1)
    req1 = cell_color(*landed)              # colour player 1 must move
    # Place player 1's req1 tower immobile (on row 0, its far row -> no forward).
    # It will sit at (7,0): for player 1, forward is toward row -1, so row 0 tower
    # has no forward cells -> blocked.
    # Its bounce colour (the cell it stands on) must be a player-0 tower that is
    # also immobile.
    bounce = cell_color(7, 0)              # colour player 0 must move after bounce
    # Player-0 bounce tower at (7,7): for player 0 forward is row 8 -> off board,
    # so a tower on row 7 has no forward move -> blocked.
    dl = {
        (0, 0): (0, "R"),                 # the only tower that can move now
        (7, 0): (1, req1),                # player 1's forced tower, immobile
        (7, 7): (0, bounce),              # player 0's bounce tower, immobile
    }
    s_dl = KState(board=dl, to_move=0, required="R", last_mover=None)
    # ensure 'R' at (0,0) really can move to (0,1)
    check("0,0>0,1" in g.legal_moves(s_dl), "setup: red tower can advance")
    a = g.apply_move(s_dl, "0,0>0,1")     # player 0 moves -> last_mover=0
    check(a.last_mover == 0, "tower move records last_mover")
    check(a.to_move == 1 and a.required == req1, "chain to player 1")
    check(g.legal_moves(a) == ["pass"], "player 1's forced tower is blocked")
    b = g.apply_move(a, "pass")           # player 1 passes -> bounce to player 0
    check(b.required == bounce and b.to_move == 0, "bounce back to player 0")
    # player 0's bounce tower is also blocked -> deadlock already resolved on pass
    check(b.winner == 1, "deadlock: last mover (player 0) loses")
    check(g.is_terminal(b) and g.returns(b) == [-1.0, 1.0],
          "deadlock loss is terminal, opponent wins")

    # render sanity: tints present for all 64 cells, towers carry fill.
    rs = g.render(s)
    check(rs["board"]["type"] == "square", "renders a square board")
    check(len(rs["board"]["tints"]) == 64, "tints for all 64 cells")
    check(all("fill" in p for p in rs["pieces"]), "towers carry a fill colour")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
