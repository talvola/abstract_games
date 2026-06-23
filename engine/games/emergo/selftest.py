"""Emergo correctness anchor -- pure stdlib, fast.

No published perft exists for Emergo, so the anchor is a set of baked rule
assertions covering every distinctive mechanic:

 (1) the dark-square 9x9 board (41 cells) + the ENTRY mechanic (12 men in hand,
     entered as the drop move 'm@c,r', captures take precedence over entry);
 (2) a single man / a controlled column steps one square in ANY diagonal
     direction (no forward rule, no kings) and CAPTURES by jumping an adjacent
     enemy column to the empty square beyond;
 (3) the jumped column's TOP man becomes a PRISONER placed UNDER the capturing
     column (ordered stacks; controller == top), reusing the Lasca model -- and
     the rest of the jumped column stays put;
 (4) captures are mandatory, chain, and must take the MAXIMUM (majority capture);
 (5) win == opponent has no man left (capture-all) or no legal move;
 (6) hand-built positions: prisoner-under, a multi-jump, liberation.

Run:  PYTHONPATH=. python3 games/emergo/selftest.py
"""

import sys

from games.emergo.game import (
    Emergo, EState, WHITE, BLACK, SIZE, MEN_PER_PLAYER, CENTER, _on,
)


def check(cond, msg):
    if not cond:
        print("SELFTEST FAILED:", msg)
        sys.exit(1)


def main():
    g = Emergo()

    # ---- (1) board + entry -------------------------------------------------
    dark = [(c, r) for r in range(SIZE) for c in range(SIZE) if _on(c, r)]
    check(SIZE == 9, "board must be 9x9")
    check(len(dark) == 41, f"dark squares of 9x9 must be 41, got {len(dark)}")
    check(_on(*CENTER), "centre (4,4) must be a dark square")
    for corner in [(0, 0), (8, 0), (0, 8), (8, 8)]:
        check(_on(*corner), f"corner {corner} must be dark")

    st = g.initial_state()
    check(st.board == {}, "all men start OFF the board")
    check(st.hands == [MEN_PER_PLAYER, MEN_PER_PLAYER], "12 men per player in hand")
    check(g.current_player(st) == WHITE, "White moves first")

    moves = g.legal_moves(st)
    check(all(m.startswith("m@") for m in moves), "opening: only single entries")
    # White may NOT open in the centre.
    check(f"m@{CENTER[0]},{CENTER[1]}" not in moves, "White cannot enter centre first")
    # All 40 other dark squares are legal entries.
    check(len(moves) == 40, f"opening should offer 40 entries, got {len(moves)}")

    st2 = g.apply_move(st, "m@1,1")
    check(st2.board[(1, 1)] == (WHITE,), "entry places a single white man")
    check(st2.hands == [MEN_PER_PLAYER - 1, MEN_PER_PLAYER], "entry decrements hand")
    check(g.current_player(st2) == BLACK, "turn passes after entry")

    # ---- (2)+(3) step + capture + prisoner-under ---------------------------
    # A lone white man steps one square in a backward-diagonal (no forward rule).
    s = EState(board={(4, 4): (WHITE,)}, hands=[0, 0], to_move=WHITE)
    steps = {m for m in g.legal_moves(s)}
    for d in ["4,4>5,5", "4,4>3,3", "4,4>5,3", "4,4>3,5"]:
        check(d in steps, f"man must be able to step diagonally {d} (omnidirectional)")
    check(len(steps) == 4, f"central lone man has 4 diagonal steps, got {len(steps)}")

    # White at (4,4) jumps a black man at (5,5), landing on the empty (6,6).
    s = EState(board={(4, 4): (WHITE,), (5, 5): (BLACK,)}, hands=[0, 0], to_move=WHITE)
    lm = g.legal_moves(s)
    check(lm == ["4,4>6,6"], f"capture is mandatory & is the only move, got {lm}")
    ns = g.apply_move(s, "4,4>6,6")
    check((4, 4) not in ns.board, "moving piece left its square")
    check((5, 5) not in ns.board, "single jumped man fully removed from its square")
    check(ns.board[(6, 6)] == (BLACK, WHITE),
          f"prisoner (black) tucked UNDER white cap: {ns.board.get((6,6))}")
    # controller == top piece (Lasca model)
    check(ns.board[(6, 6)][-1] == WHITE, "white controls the new 2-stack (cap on top)")

    # Prisoner-under from a TALL enemy column: only the TOP man is taken; the
    # rest stays put and is now controlled by the newly-exposed man.
    s = EState(board={(4, 4): (WHITE,), (5, 5): (WHITE, WHITE, BLACK)},
               hands=[0, 0], to_move=WHITE)
    ns = g.apply_move(s, "4,4>6,6")
    check(ns.board[(6, 6)] == (BLACK, WHITE), "only the top (black) man becomes a prisoner")
    check(ns.board[(5, 5)] == (WHITE, WHITE),
          "the rest of the jumped column REMAINS in place")
    check(ns.board[(5, 5)][-1] == WHITE, "exposed column now controlled by white (liberation)")

    # ---- (4) mandatory + chained + MAXIMUM capture -------------------------
    # Two black men set up a double jump 4,4 -> 6,6 -> 4,8 ... arrange a chain.
    s = EState(board={(2, 2): (WHITE,), (3, 3): (BLACK,), (5, 3): (BLACK,)},
               hands=[0, 0], to_move=WHITE)
    lm = g.legal_moves(s)
    # First jump 2,2>4,4 lands at (4,4); then can jump (5,3) -> (6,2). Max = 2 men.
    check(all(">" in m for m in lm), "only captures offered (mandatory)")
    best = max(m.count(">") for m in lm)
    check(best == 2, f"a 2-jump chain must be found (max capture), paths={lm}")
    # Every offered capture must be a MAXIMUM one (a single jump must NOT be offered).
    check(all(m.count(">") == 2 for m in lm),
          f"only MAXIMUM captures may be offered, got {lm}")
    chain = [m for m in lm if m == "2,2>4,4>6,2"][0]
    ns = g.apply_move(s, chain)
    check(ns.board[(6, 2)] == (BLACK, BLACK, WHITE),
          f"both prisoners tucked under, white on top: {ns.board.get((6,2))}")
    check((3, 3) not in ns.board and (5, 3) not in ns.board, "both jumped men removed")

    # No 180-degree immediate reversal: a lone man with one enemy can't jump back.
    s = EState(board={(4, 4): (WHITE,), (5, 5): (BLACK,)}, hands=[0, 0], to_move=WHITE)
    paths = g._all_captures(s.board, WHITE)
    check(all(len(p) == 2 for p in paths), "no spurious reversal extends the chain")

    # ---- (5) win conditions ------------------------------------------------
    # Capture-all: white jumps black's last man -> white wins.
    s = EState(board={(4, 4): (WHITE,), (5, 5): (BLACK,)}, hands=[0, 0], to_move=WHITE)
    ns = g.apply_move(s, "4,4>6,6")
    check(ns.winner == WHITE, "capturing the opponent's last man wins")
    check(g.is_terminal(ns), "win is terminal")
    check(g.returns(ns) == [1.0, -1.0], "winner payoff +1/-1")

    # Opponent still has a buried man (prisoner) but no MAN ON TOP and none in
    # hand -> they have no controllable column -> they lost.
    s = EState(board={(6, 6): (BLACK, WHITE)}, hands=[0, 0], to_move=WHITE)
    # White makes a quiet step; black then controls nothing -> black has no move.
    nb = dict(s.board)
    ns = g.apply_move(s, "6,6>7,7")
    check(ns.winner == WHITE, "opponent with only buried prisoners (no cap, no hand) loses")

    # ---- entry: the no-force restriction -----------------------------------
    # Black to move, must NOT enter a man where White could then capture it.
    # White man at (4,4); black entering. Dropping black at (5,5) lets White jump
    # to (6,6) (empty) -> that entry must be illegal.
    s = EState(board={(4, 4): (WHITE,)}, hands=[5, 5], to_move=BLACK)
    lm = g.legal_moves(s)
    check("m@5,5" not in lm, "entry that forces opponent capture is illegal")
    check("m@1,1" in lm, "a safe entry is legal")

    # ---- end-of-entry: stacked entry when opponent has all 12 placed --------
    s = EState(board={(0, 0): (BLACK,)}, hands=[3, 0], to_move=WHITE)
    # Black hand empty -> White must enter ALL 3 remaining men as one column.
    lm = g.legal_moves(s)
    drops = [m for m in lm if m.startswith("M@")]
    check(drops, "with opponent fully placed, the stacked entry 'M@' is offered")
    ns = g.apply_move(s, drops[0])
    cell = drops[0].split("@")[1].split(",")
    cell = (int(cell[0]), int(cell[1]))
    check(ns.board[cell] == (WHITE, WHITE, WHITE), "all remaining men enter as one column")
    check(ns.hands[WHITE] == 0, "hand emptied by the stacked entry")

    # ---- serialize round-trips ---------------------------------------------
    s = EState(board={(6, 6): (BLACK, BLACK, WHITE), (2, 2): (WHITE,)},
               hands=[4, 7], to_move=BLACK, since=3, ply=12)
    d = g.serialize(s)
    rt = g.serialize(g.deserialize(d))
    check(rt == d, "serialize must round-trip")
    import json
    json.dumps(d)  # must be JSON-able

    # ---- a short random self-play terminates -------------------------------
    import random
    rng = random.Random(7)
    for game_i in range(6):
        s = g.initial_state()
        for _ in range(PLY_GUARD):
            if g.is_terminal(s):
                break
            lm = g.legal_moves(s)
            check(lm, "non-terminal state must have a legal move")
            s = g.apply_move(s, rng.choice(lm))
        check(g.is_terminal(s), "random game must reach a terminal state")
        r = g.returns(s)
        check(len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r),
              f"well-formed returns, got {r}")

    print("SELFTEST OK")
    sys.exit(0)


PLY_GUARD = 1200

if __name__ == "__main__":
    main()
