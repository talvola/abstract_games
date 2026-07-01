"""Grand Shatranj correctness anchor (pure stdlib -- imports only agp + this game).

Anchors:
  * the exact "Grand Shatranj D" 10x10 setup (verified vs chessvariants.com:
    War Machines in the corners, N O J K M H O N on files b-i of rank 2,
    ten pawns on rank 3, Black mirrored);
  * frozen self-computed perft from the start position: 63 / 3969 at depths
    1/2 (depth 3 = 245735, verified once but too slow for this suite; the
    depth-1 count 63 was also verified by hand piece-by-piece);
  * the movement geometry of every non-standard piece on sparse hand-built
    positions, derived from the source prose:
      - Jumping General: 8 steps + 8 two-square jumps; jumps over a full ring;
      - Minister: wazir + dabbabah-jump + knight (16 targets);
      - High Priestess: ferz + alfil-jump + knight (16 targets);
      - Oliphant / Lightning War Machine: 1-4 squares along one line, where
        distance 3 needs an empty 1st OR 2nd intermediate, distance 4 needs an
        empty 2nd; jumped squares may be occupied, intermediate landings not;
  * pawns: no double step; promotion optional on the 9th rank, mandatory on
    the 10th, restricted to LOST piece types; the stranded-pawn sideways move
    (and its sideways attack) on the 10th rank;
  * shatranj wins: baring reached via apply_move; the immediate counter-bare
    declared a draw; K vs K a draw;
  * a capture reached via a scripted opening, a serialize round-trip, and a
    random game terminating under the ply cap.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.grand_shatranj.game import GrandShatranj          # noqa: E402
from agp.chesslike import CState, WHITE, BLACK               # noqa: E402

G = GrandShatranj()


def perft(state, d):
    if d == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), d - 1) for m in G.legal_moves(state))


def st(board, to_move=WHITE):
    return CState(board=dict(board), to_move=to_move)


def dests(state, frm):
    return {m.split(">")[1].split("=")[0]
            for m in G.legal_moves(state) if m.split(">")[0] == frm}


def cs(pairs):
    return {f"{c},{r}" for (c, r) in pairs}


def main():
    s0 = G.initial_state()

    # 1) Setup (Grand Shatranj D, vs chessvariants.com).
    assert G.WIDTH == 10 and G.HEIGHT == 10
    assert len(s0.board) == 40
    b = s0.board
    assert b[(0, 0)] == b[(9, 0)] == (WHITE, "W")            # War Machine corners
    assert b[(0, 9)] == b[(9, 9)] == (BLACK, "W")
    assert "".join(b[(c, 1)][1] for c in range(1, 9)) == "NOJKMHON"
    assert "".join(b[(c, 8)][1] for c in range(1, 9)) == "NOJKMHON"
    assert all(b[(c, 2)] == (WHITE, "P") for c in range(10))
    assert all(b[(c, 7)] == (BLACK, "P") for c in range(10))
    assert (0, 1) not in b and (9, 1) not in b               # rank-2 wings empty

    # 2) Frozen perft (self-computed; depth 1 verified by hand).
    assert perft(s0, 1) == 63, perft(s0, 1)
    assert perft(s0, 2) == 3969, perft(s0, 2)
    # perft(s0, 3) == 245735  (verified once; ~20s, too slow to run here)

    # 3) No pawn double step, no en passant target.
    assert "4,2>4,4" not in G.legal_moves(s0)
    assert G.apply_move(s0, "4,2>4,3").ep is None

    # 4) Jumping General: 8 steps + 8 exact-2 jumps; jumps clear a full ring.
    # (The black pawn keeps Black from being BARE -- a terminal state here.)
    kings = {(0, 1): (WHITE, "K"), (9, 6): (BLACK, "K"), (9, 5): (BLACK, "P")}
    s = st({**kings, (4, 4): (WHITE, "J")})
    steps = [(3, 3), (4, 3), (5, 3), (3, 4), (5, 4), (3, 5), (4, 5), (5, 5)]
    jumps = [(2, 2), (4, 2), (6, 2), (2, 4), (6, 4), (2, 6), (4, 6), (6, 6)]
    assert dests(s, "4,4") == cs(steps + jumps)
    ring = {(c, r): (WHITE, "P") for (c, r) in steps}        # fully boxed in
    s = st({**kings, (4, 4): (WHITE, "J"), **ring})
    assert cs(jumps) <= dests(s, "4,4")                      # still jumps out

    # 5) Minister: wazir + dabbabah + knight = 16 targets.
    s = st({**kings, (4, 4): (WHITE, "M")})
    assert dests(s, "4,4") == cs(
        [(3, 4), (5, 4), (4, 3), (4, 5), (2, 4), (6, 4), (4, 2), (4, 6),
         (3, 2), (5, 2), (2, 3), (6, 3), (2, 5), (6, 5), (3, 6), (5, 6)])

    # 6) High Priestess: ferz + alfil + knight = 16 targets.
    s = st({**kings, (4, 4): (WHITE, "H")})
    assert dests(s, "4,4") == cs(
        [(3, 3), (5, 3), (3, 5), (5, 5), (2, 2), (6, 2), (2, 6), (6, 6),
         (3, 2), (5, 2), (2, 3), (6, 3), (2, 5), (6, 5), (3, 6), (5, 6)])

    # 7) Oliphant: 1-4 diagonally; blocker logic on the (+1,+1) ray.
    s = st({**kings, (4, 4): (WHITE, "O")})                  # open board
    ray = lambda s_: {d for d in dests(s_, "4,4")            # noqa: E731
                      if d in cs([(5, 5), (6, 6), (7, 7), (8, 8)])}
    assert len(dests(s, "4,4")) == 16                        # 4 per diagonal
    assert ray(s) == cs([(5, 5), (6, 6), (7, 7), (8, 8)])
    # enemy on s1 AND s2: can capture either (jump over s1), but 3/4 blocked.
    s = st({**kings, (4, 4): (WHITE, "O"),
            (5, 5): (BLACK, "P"), (6, 6): (BLACK, "P")})
    assert ray(s) == cs([(5, 5), (6, 6)])
    # enemy on s2 only: distance 3 ok (via empty s1), distance 4 blocked.
    s = st({**kings, (4, 4): (WHITE, "O"), (6, 6): (BLACK, "P")})
    assert ray(s) == cs([(5, 5), (6, 6), (7, 7)])
    # OWN man on s1: no landing there, but jump over it; s2 empty so 3+4 ok.
    s = st({**kings, (4, 4): (WHITE, "O"), (5, 5): (WHITE, "N")})
    assert ray(s) == cs([(6, 6), (7, 7), (8, 8)])
    # Oliphant ATTACK is symmetric: black K on the ray is in check over a jump.
    bd = {(0, 1): (WHITE, "K"), (4, 4): (WHITE, "O"),
          (5, 5): (WHITE, "N"), (7, 7): (BLACK, "K")}
    assert G.in_check(bd, BLACK)

    # 8) Lightning War Machine: the orthogonal twin.
    s = st({**kings, (4, 4): (WHITE, "W")})
    assert len(dests(s, "4,4")) == 16
    s = st({**kings, (4, 4): (WHITE, "W"),
            (4, 5): (BLACK, "P"), (4, 6): (BLACK, "P")})
    up = {d for d in dests(s, "4,4") if d in cs([(4, 5), (4, 6), (4, 7), (4, 8)])}
    assert up == cs([(4, 5), (4, 6)])

    # 9) Promotion: only to LOST types; optional on rank 9, mandatory on rank 10.
    sparse = {(0, 0): (WHITE, "K"), (9, 0): (BLACK, "K"),
              (9, 3): (BLACK, "P")}                          # all 6 white types lost
    s = st({**sparse, (4, 7): (WHITE, "P")})
    mv = [m for m in G.legal_moves(s) if m.startswith("4,7>4,8")]
    assert sorted(mv) == sorted(["4,7>4,8"] +                # optional on 9th
                                [f"4,7>4,8={t}" for t in "JMHON W".replace(" ", "")])
    s = st({**sparse, (4, 8): (WHITE, "P")})
    mv = [m for m in G.legal_moves(s) if m.startswith("4,8>4,9")]
    assert "4,8>4,9" not in mv and len(mv) == 6              # mandatory on 10th
    # Full army -> nothing lost -> the pawn arrives on the 10th UNPROMOTED.
    full = dict(s0.board)
    del full[(0, 9)]                                         # clear a10 (a black W)
    full[(0, 8)] = (WHITE, "P")
    s = st(full)
    assert "0,8>0,9" in G.legal_moves(s)
    assert not any(m.startswith("0,8>0,9=") for m in G.legal_moves(s))
    s2 = G.apply_move(s, "0,8>0,9")
    assert s2.board[(0, 9)] == (WHITE, "P")                  # stranded pawn

    # 10) Stranded pawn: sideways moves; promotes sideways once a type is lost.
    full = dict(s0.board)
    full[(4, 9)] = (WHITE, "P")                              # e10 is empty at start
    s = st(full)
    side = [m for m in G.legal_moves(s) if m.startswith("4,9>")]
    assert sorted(side) == ["4,9>3,9", "4,9>5,9"]            # plain only (no losses)
    lost = dict(full)
    del lost[(1, 1)]                                         # white knight lost
    s = st(lost)
    side = [m for m in G.legal_moves(s) if m.startswith("4,9>3,9")]
    assert sorted(side) == ["4,9>3,9", "4,9>3,9=N"]          # optional promotion
    s2 = G.apply_move(s, "4,9>3,9=N")
    assert s2.board[(3, 9)] == (WHITE, "N")
    # A stranded pawn attacks sideways (checks a king beside it on the rank).
    bd = {(0, 0): (WHITE, "K"), (4, 9): (WHITE, "P"), (5, 9): (BLACK, "K"),
          (9, 5): (BLACK, "P")}
    assert G.in_check(bd, BLACK)

    # 11) A capture via a scripted opening (pawn takes pawn).
    s = s0
    for m in ["3,2>3,3", "4,7>4,6", "3,3>3,4", "4,6>4,5", "3,4>4,5"]:
        assert m in G.legal_moves(s), m
        s = G.apply_move(s, m)
    assert len(s.board) == 39 and s.board[(4, 5)] == (WHITE, "P")

    # 12) Baring, reached via apply_move: M jumps to capture Black's last man.
    s = st({(0, 0): (WHITE, "K"), (4, 4): (WHITE, "M"),
            (9, 9): (BLACK, "K"), (6, 4): (BLACK, "P")})
    assert not G.is_terminal(s)
    s2 = G.apply_move(s, "4,4>6,4")                          # dabbabah jump-capture
    assert G.is_terminal(s2)
    assert G.returns(s2) == [1.0, -1.0]                      # White wins (bare king)
    assert G.legal_moves(s2) == []
    assert "bare" in G.render(s2)["caption"]

    # 13) Immediate counter-bare -> draw; K vs K -> draw.
    s = st({(0, 0): (WHITE, "K"), (8, 8): (WHITE, "N"), (9, 9): (BLACK, "K")},
           to_move=BLACK)                                    # bare K can take the N
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0]
    s = st({(0, 0): (WHITE, "K"), (2, 2): (WHITE, "N"), (9, 9): (BLACK, "K")},
           to_move=BLACK)                                    # out of reach -> loss
    assert G.is_terminal(s) and G.returns(s) == [1.0, -1.0]
    s = st({(0, 0): (WHITE, "K"), (9, 9): (BLACK, "K")})
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0]

    # 14) Serialize round-trip.
    s = G.apply_move(s0, "4,2>4,3")
    s = G.apply_move(s, "5,7>5,6")
    rt = G.deserialize(G.serialize(s))
    assert rt.board == s.board and rt.to_move == s.to_move
    assert G.legal_moves(rt) == G.legal_moves(s)

    # 15) Render shape + a random game terminates under the ply cap.
    spec = G.render(s0)
    assert spec["board"]["type"] == "square"
    assert all(len(p["label"]) <= 2 for p in spec["pieces"])
    rng = random.Random(7)
    s, n = s0, 0
    while not G.is_terminal(s):
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        n += 1
        assert n <= G.PLY_CAP + 1
    assert len(G.returns(s)) == 2

    print("grand_shatranj selftest: all checks passed")


if __name__ == "__main__":
    main()
