"""Shape Chess correctness anchors (pure stdlib: agp + this game only).

Anchored on David Ploog's Shape Chess article, Abstract Games magazine #24
(Winter 2022) pp. 4-7, and the printed puzzle solutions on p. 38:

  * the six symmetry examples of p. 4 (three symmetric black shapes with a
    horizontal grid-line axis, a diagonal axis and a half-grid vertical axis;
    three non-symmetric white shapes, two of which are ONLY rotationally
    symmetric and must not count);
  * the worked scoring example of p. 5: the unique push that builds a
    symmetric 7-stone black shape, scoring 7 - 5 = 2 and giving a bonus turn;
  * puzzle 1 (p. 5 "Black to move and score 3 / White to move and score 3",
    solution p. 38: "Black jumps h4-d5. White jumps g4-g7") -- both jumps
    score exactly 3, and 3 is the maximum single-move score for either side;
  * puzzle 2 (p. 5 "Black to move and score 4 / White to move and score 4",
    solution p. 38): all four printed White winning lines
    f6-d9(1),e5:e4(3) / f6-g3(2),e5:e4(2) / f6-e9(1),e10(3) / f6-e10(1),e9(3)
    and the Black line g4-j7(1),g6:g7(3) -- each reaches 4 points through the
    bonus-turn chain and wins on the spot;
  * the final problem (p. 8 "Black to mate in 3. Score 3:3", solution p. 38
    #3): White's d5-d1 threat scores 2 and wins; Black's defensive push
    f4:g5 disarms every immediate White win, and g5 is the ONLY destination
    for the pushed stone that does (f3/g3/f5 all lose on the spot).

The stone positions were digitised from the magazine figures (300 dpi); the
coordinate frame (files a.. from the left edge, 'i' NOT skipped, top visible
line = rank 11) is the unique mapping under which every printed solution line
scores exactly as stated.

Run standalone:  cd engine && PYTHONPATH=. python3 games/shape_chess/selftest.py
"""

import random
from pathlib import Path

from agp.loader import load_from_dir
from games.shape_chess.game import (
    SCState, components, symmetric, sweep, BLACK, WHITE,
)

_M, G = load_from_dir(Path(__file__).resolve().parent)

CHECKS = 0


def ok(cond, msg):
    global CHECKS
    CHECKS += 1
    if not cond:
        raise AssertionError(msg)


def alg(name):
    """'f6' -> (5, 5): file letter (i included) + 1-based rank."""
    return (ord(name[0]) - ord("a"), int(name[1:]) - 1)


def cellstr(name):
    c, r = alg(name)
    return f"{c},{r}"


def mv(frm, to=None):
    return cellstr(frm) if to is None else f"{cellstr(frm)}>{cellstr(to)}"


def rot180(S):
    xs = [p[0] for p in S]
    ys = [p[1] for p in S]
    sx, sy = min(xs) + max(xs), min(ys) + max(ys)
    return all((sx - x, sy - y) in S for x, y in S)


# ---------------------------------------------------------------------------
# 1. symmetry unit cases straight from the p. 4 rules diagrams
# ---------------------------------------------------------------------------

def test_symmetry_examples():
    # "Three symmetric black shapes" (each 6 stones, would score 1 point)
    s1 = {(1, 1), (1, 2), (1, 3), (2, 1), (2, 3), (3, 2)}   # horizontal axis
    s2 = {(5, 3), (5, 2), (6, 3), (6, 1), (7, 2), (7, 1)}   # diagonal axis
    s3 = {(0, 2), (0, 1), (3, 2), (3, 1), (1, 0), (2, 0)}   # half-grid vert.
    for i, s in enumerate((s1, s2, s3), 1):
        ok(len(components(s)) == 1, f"sym shape {i} must be 8-connected")
        ok(symmetric(s), f"sym shape {i} must be symmetric")
        ok(sweep(s) == (1, s), f"sym shape {i} scores 6-5=1 and is removed")

    # "Three non-symmetric white shapes" -- two have ONLY rotational symmetry
    n1 = {(1, 0), (2, 1), (2, 2), (3, 0), (3, 1), (3, 2)}   # no symmetry
    n2 = {(5, 0), (5, 1), (6, 1), (7, 1), (7, 2)}           # rotational only
    n3 = {(9, 1), (9, 2), (10, 2), (11, 1), (12, 1), (12, 2)}  # rotational only
    for i, s in enumerate((n1, n2, n3), 1):
        ok(len(components(s)) == 1, f"nonsym shape {i} must be 8-connected")
        ok(not symmetric(s), f"nonsym shape {i} must NOT count as symmetric")
    ok(rot180(n2) and rot180(n3),
       "the article's 2nd/3rd white shapes DO have 180-degree symmetry")
    ok(not rot180(n1), "the article's 1st white shape has no symmetry at all")
    ok(sweep(n1) == (0, set()), "a non-symmetric 6-shape never scores")

    # size threshold: a symmetric shape of five stones does not score
    ok(sweep({(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)}) == (0, set()),
       "symmetric shapes below six stones do not score")


# ---------------------------------------------------------------------------
# 2. worked scoring example (p. 5): the push scoring 7 - 5 = 2
# ---------------------------------------------------------------------------

# Figure window, y up.  Black to play.
EX_B = [(1, 4), (1, 3), (2, 2), (3, 3), (3, 2), (4, 5), (4, 1)]
EX_W = [(1, 5), (1, 2), (2, 5), (2, 4), (2, 3), (3, 4)]
EX_PUSH = ((2, 4), (3, 5))     # push the white stone at (2,4) NE -- unique


def test_scoring_example():
    off = 3                     # translation-invariant; keep clear of edges
    board = {}
    for x, y in EX_B:
        board[(x + off, y + off)] = BLACK
    for x, y in EX_W:
        board[(x + off, y + off)] = WHITE
    s = SCState(n=12, target=4, board=board, to_move=BLACK)

    (fx, fy), (tx, ty) = EX_PUSH
    move = f"{fx + off},{fy + off}>{tx + off},{ty + off}"
    ok(move in G.legal_moves(s), "the example push must be legal")

    # It is the UNIQUE scoring push in the position (the article shows one).
    scoring_pushes = []
    for m in G.legal_moves(s):
        if ">" not in m:
            continue
        a = tuple(int(v) for v in m.split(">")[0].split(","))
        if s.board.get(a) != WHITE:
            continue
        if G.apply_move(s, m).scores[BLACK] > 0:
            scoring_pushes.append(m)
    ok(scoring_pushes == [move],
       f"exactly one push scores in the example (got {scoring_pushes})")

    s2 = G.apply_move(s, move)
    ok(s2.scores == [2, 0], "the push scores 7 - 5 = 2 points for Black")
    nb = sum(1 for p in s2.board.values() if p == BLACK)
    nw = sum(1 for p in s2.board.values() if p == WHITE)
    ok(nb == 1, "the symmetric 7-stone black shape is removed (1 black left)")
    ok(nw == 6, "white keeps all six stones (one merely pushed)")
    ok(G.current_player(s2) == BLACK and s2.bonus,
       "afterwards Black gets to make another turn")
    ok(not G.is_terminal(s2), "2 points < target 4: game continues")
    ok("(+2)" in G.describe_move(s, move), "move log annotates the score")


# ---------------------------------------------------------------------------
# 3. puzzle 1 (p. 5 / solution p. 38 #1)
# ---------------------------------------------------------------------------

P1_B = "d6 d3 e6 f5 f4 g6 h6 h5 h4".split()
P1_W = "d4 e5 e4 f6 g5 g4 g3 h8 h7".split()


def p1_state(to_move):
    board = {alg(n): BLACK for n in P1_B}
    board.update({alg(n): WHITE for n in P1_W})
    return SCState(n=12, target=4, board=board, to_move=to_move)


def max_single_move_score(s):
    p = s.to_move
    return max(G.apply_move(s, m).scores[p] for m in G.legal_moves(s))


def test_puzzle1():
    # Black jumps h4-d5: an 8-stone symmetric shape, 8 - 5 = 3 points.
    s = p1_state(BLACK)
    m = mv("h4", "d5")
    ok(m in G.legal_moves(s), "h4-d5 must be a legal jump")
    ok(G.describe_move(s, m) == "Jump h4-d5 (+3)", "notation for h4-d5")
    s2 = G.apply_move(s, m)
    ok(s2.scores == [3, 0], "Black h4-d5 scores exactly 3")
    ok(sum(1 for p in s2.board.values() if p == BLACK) == 1,
       "the 8-stone shape is removed; only d3 remains black")
    ok(s2.board.get(alg("d3")) == BLACK, "the leftover black stone is d3")
    ok(sum(1 for p in s2.board.values() if p == WHITE) == 9,
       "white stones are untouched")
    ok(G.current_player(s2) == BLACK, "Black moves again after scoring")
    ok(max_single_move_score(s) == 3,
       "3 is the LARGEST possible single-move score for Black (puzzle text)")

    # White jumps g4-g7: also 3 points.
    s = p1_state(WHITE)
    m = mv("g4", "g7")
    ok(m in G.legal_moves(s), "g4-g7 must be a legal jump")
    s2 = G.apply_move(s, m)
    ok(s2.scores == [0, 3], "White g4-g7 scores exactly 3")
    ok(max_single_move_score(s) == 3,
       "3 is the largest possible single-move score for White too")


# ---------------------------------------------------------------------------
# 4. puzzle 2 (p. 5 / solution p. 38 #2): win-in-two via the bonus turn
# ---------------------------------------------------------------------------

P2_B = "c4 d5 d6 d7 e5 f5 f7 g4 h5 h6 i4 i7 i8".split()
P2_W = "e3 e6 e7 e8 f4 f6 f8 g5 g6 g8 h4 h8 i3".split()


def p2_state(to_move):
    board = {alg(n): BLACK for n in P2_B}
    board.update({alg(n): WHITE for n in P2_W})
    return SCState(n=12, target=4, board=board, to_move=to_move)


def run_line(to_move, moves, pts):
    """Play a printed solution line, asserting the per-move scores."""
    s = p2_state(to_move)
    total = 0
    for m, p in zip(moves, pts):
        ok(not G.is_terminal(s), f"line {moves}: game must still be live")
        ok(G.current_player(s) == to_move,
           f"line {moves}: bonus turn keeps {to_move} on the move")
        ok(m in G.legal_moves(s), f"line {moves}: {m} must be legal")
        before = s.scores[to_move]
        s = G.apply_move(s, m)
        got = s.scores[to_move] - before
        ok(got == p, f"line {moves}: {m} must score {p}, got {got}")
        total += p
    ok(total == 4 and s.winner == to_move and G.is_terminal(s),
       f"line {moves}: reaching 4 points wins on the spot")
    ret = G.returns(s)
    ok(ret[to_move] == 1.0 and ret[1 - to_move] == -1.0,
       f"line {moves}: returns reflect the win")
    return s


def test_puzzle2():
    # White's four printed winning lines (jump/push/drop chains).
    run_line(WHITE, [mv("f6", "d9"), mv("e5", "e4")], [1, 3])
    run_line(WHITE, [mv("f6", "g3"), mv("e5", "e4")], [2, 2])
    run_line(WHITE, [mv("f6", "e9"), cellstr("e10")], [1, 3])
    run_line(WHITE, [mv("f6", "e10"), cellstr("e9")], [1, 3])
    # Black's printed winning line.
    run_line(BLACK, [mv("g4", "j7"), mv("g6", "g7")], [1, 3])

    # Notation spot-checks on the first line.
    s = p2_state(WHITE)
    ok(G.describe_move(s, mv("f6", "d9")) == "Jump f6-d9 (+1)",
       "jump notation")
    s2 = G.apply_move(s, mv("f6", "d9"))
    ok(G.describe_move(s2, mv("e5", "e4")) == "Push e5:e4 (+3)",
       "push notation")
    s3 = p2_state(BLACK)
    ok(G.describe_move(s3, cellstr("a1")) == "Drop a1", "drop notation")


# ---------------------------------------------------------------------------
# 4b. final problem (p. 8 "Black to mate in 3. Score 3:3" / solution p. 38 #3)
#
# Machine-checked claims from the printed solution (the deeper double-threat
# follow-ups are prose and are not asserted):
#   * "White threatens to win with the jump d5-d1" -- it scores 2 (a 7-stone
#     shape c3/d1/d2/e3/e5/f4/g4), and 3+2 >= 4 wins;
#   * "The Black push f4:g5 is a very clever move" -- it scores nothing, and
#     afterwards White has NO immediately winning move at all;
#   * "The white stone must go to g5 as any other destination lets White
#     win" -- the pushed f4 stone's only other empty destinations are f3, g3
#     and f5, and after each White wins on the spot (e.g. drop b3 / jump
#     c6-f5 / jump c6-g3 respectively).
# ---------------------------------------------------------------------------

P3_B = "b2 b4 b7 b8 c2 c4 c7 c9 d4 d6 e4 e6 f6".split()
P3_W = "a4 c3 c5 c6 d2 d5 e3 e5 f4 g4 g6 g7".split()


def p3_state(to_move):
    board = {alg(n): BLACK for n in P3_B}
    board.update({alg(n): WHITE for n in P3_W})
    return SCState(n=12, target=4, board=board, scores=[3, 3],
                   to_move=to_move)


def white_wins_now(s):
    """All White moves that win immediately from a White-to-move state."""
    return [m for m in G.legal_moves(s)
            if G.apply_move(s, m).winner == WHITE]


def test_final_problem():
    # the threat: White d5-d1 would score 2 and win
    s = p3_state(WHITE)
    m = mv("d5", "d1")
    ok(m in G.legal_moves(s), "d5-d1 must be a legal White jump")
    s2 = G.apply_move(s, m)
    ok(s2.scores[WHITE] == 5 and s2.winner == WHITE,
       "White d5-d1 scores 2 (7-stone shape) and wins from 3:3")

    # the defence: f4:g5 scores nothing but disarms every immediate win
    s = p3_state(BLACK)
    m = mv("f4", "g5")
    ok(m in G.legal_moves(s), "f4:g5 must be a legal Black push")
    s2 = G.apply_move(s, m)
    ok(s2.scores == [3, 3] and G.current_player(s2) == WHITE,
       "f4:g5 scores nothing; turn passes")
    ok(white_wins_now(s2) == [],
       "after f4:g5 White has NO immediately winning move")

    # every other destination for the pushed stone loses on the spot
    refutes = {"f3": mv("b3"), "g3": mv("c6", "f5"), "f5": mv("c6", "g3")}
    for dest, reply in refutes.items():
        alt = mv("f4", dest)
        ok(alt in G.legal_moves(s), f"f4:{dest} must be legal")
        sa = G.apply_move(s, alt)
        ok(sa.scores == [3, 3], f"f4:{dest} itself scores nothing")
        wins = white_wins_now(sa)
        ok(reply in wins,
           f"after f4:{dest} White wins immediately (e.g. {reply})")


# ---------------------------------------------------------------------------
# 5. action legality basics
# ---------------------------------------------------------------------------

def test_action_rules():
    s = G.initial_state({"size": 12, "target": 4})
    lm = G.legal_moves(s)
    ok(len(lm) == 144 and all(">" not in m for m in lm),
       "empty board: drops only, one per point")

    board = {alg("c3"): BLACK, alg("g7"): WHITE}
    s = SCState(n=12, target=4, board=board, to_move=BLACK)
    lm = set(G.legal_moves(s))
    ok(mv("c3", "j10") in lm, "jump may go anywhere (own stone, empty target)")
    ok(mv("g7", "g8") in lm, "push an adjacent-empty enemy stone one step")
    ok(mv("g7", "h8") in lm, "diagonal pushes are legal (8 directions)")
    ok(mv("g7", "g9") not in lm, "push destination must be ADJACENT")
    ok(mv("g7", "c3") not in lm, "push destination must be empty")
    ok(cellstr("c3") not in lm and cellstr("g7") not in lm,
       "drops only on empty points")
    ok(mv("c3", "g7") not in lm, "jump target must be empty")

    # push mechanics: enemy stone moves, own stone appears at the origin
    s2 = G.apply_move(s, mv("g7", "h8"))
    ok(s2.board[alg("h8")] == WHITE and s2.board[alg("g7")] == BLACK,
       "push: enemy stone shoved, own stone placed at the origin")
    ok(G.current_player(s2) == WHITE, "no score: turn passes")

    # board edges clip push targets
    board = {alg("a1"): WHITE}
    s = SCState(n=12, target=4, board=board, to_move=BLACK)
    pushes = [m for m in G.legal_moves(s) if ">" in m
              and m.startswith(cellstr("a1") + ">")]
    ok(len(pushes) == 3, "a corner enemy stone has 3 push destinations")


# ---------------------------------------------------------------------------
# 6. termination / draw honesty
# ---------------------------------------------------------------------------

def test_termination():
    # stall-stop with equal scores is an HONEST DRAW
    s = SCState(n=12, target=4, board={}, to_move=BLACK, stopped=True)
    ok(G.is_terminal(s) and G.returns(s) == [0.0, 0.0],
       "no-progress stop with equal scores is a draw")
    s = SCState(n=12, target=4, board={}, scores=[2, 1], to_move=BLACK,
                stopped=True)
    ok(G.returns(s) == [1.0, -1.0], "no-progress stop: higher score wins")

    # the no-progress counter actually trips (jump shuffles forever)
    s = SCState(n=12, target=4,
                board={alg("a1"): BLACK, alg("l12"): WHITE}, to_move=BLACK)
    rng = random.Random(7)
    plies = 0
    while not G.is_terminal(s):
        moves = G.legal_moves(s)
        ok(moves, "non-terminal state must have moves")
        s = G.apply_move(s, rng.choice(moves))
        plies += 1
        ok(plies <= 6 * 144 + 1, "hard cap must stop the game")
    ok(G.returns(s) is not None and len(G.returns(s)) == 2,
       "random game reaches a well-formed terminal")

    # serialize round-trip on a live position
    s = p2_state(WHITE)
    s = G.apply_move(s, mv("f6", "d9"))
    d = G.serialize(s)
    import json
    json.dumps(d)
    s2 = G.deserialize(d)
    ok(G.serialize(s2) == d, "serialize round-trips")
    ok(G.legal_moves(s2) == G.legal_moves(s), "round-trip preserves moves")


def main():
    test_symmetry_examples()
    test_scoring_example()
    test_puzzle1()
    test_puzzle2()
    test_final_problem()
    test_action_rules()
    test_termination()
    print(f"shape_chess selftest: all {CHECKS} checks passed")


if __name__ == "__main__":
    main()
