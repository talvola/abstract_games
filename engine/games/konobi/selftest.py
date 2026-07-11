"""Konobi selftest — pure stdlib (imports only agp + this game).

Run: cd engine && PYTHONPATH=. python3 games/konobi/selftest.py

Anchors (all from the designer's official material — BGG #123213 description,
the official Konobi.pdf rule sheet and its diagrams):
  * strong/weak classification, incl. the shared-strong-neighbour exclusion;
  * the kosumi legality rule on the PDF's two LEGAL and two ILLEGAL worked
    examples (exact boards from the rule sheet), plus a banned weak placement
    that becomes legal once the clean strong alternative is removed;
  * the crosscut ban;
  * the PDF's full 5x5 sample game: all 25 moves legal in sequence, the rule
    sheet's "24 at 25 would have been illegal" fact, Black wins on move 25;
  * wins through a genuinely weak (diagonal) link for BOTH colours, reached
    via apply_move, where strong-only connectivity does NOT span;
  * the pie swap (Black's stone replaced by White's on the mirrored point);
  * 500 random playouts: all terminate with a winner (drawless), plus
    serialize round-trip.
"""

import random

from games.konobi.game import (
    Konobi, KonobiState, BLACK, WHITE,
    _weak_partners, _makes_crosscut, _legal_placement, _connects,
)


def _ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def _board(rows):
    """Build a board dict from strings: 'X'=Black, 'O'=White, '.'=empty."""
    b = {}
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "X":
                b[(c, r)] = BLACK
            elif ch == "O":
                b[(c, r)] = WHITE
    return b


def test_strong_weak_classification():
    # Diagonal pair, both shared cells empty -> weak.
    b = _board(["X.",
                ".X"])  # (0,0) and (1,1)
    _ok(_weak_partners({(0, 0): BLACK}, 1, 1, BLACK) == [(0, 0)],
        "plain diagonal pair should be weak")
    # Shared strongly-connected neighbour (friendly orthogonal to both)
    # kills the weakness: X at (1,0) is orthogonal to both (0,0) and (1,1).
    _ok(_weak_partners({(0, 0): BLACK, (1, 0): BLACK}, 1, 1, BLACK) == [],
        "shared friendly neighbour must exclude the weak link")
    # An ENEMY on a shared cell does NOT mediate -> still weak.
    _ok(_weak_partners({(0, 0): BLACK, (1, 0): WHITE}, 1, 1, BLACK) == [(0, 0)],
        "enemy on a shared cell must not mediate the diagonal pair")
    # Different colours never connect.
    _ok(_weak_partners({(0, 0): WHITE}, 1, 1, BLACK) == [],
        "opposite-colour diagonal is not a weak connection")


def test_crosscut_ban():
    # 2x2 checkerboard: B(0,0), W(1,0), W(0,1); Black completing at (1,1)
    # forms the crosscut (two diagonal B + two diagonal W) -> banned.
    b = {(0, 0): BLACK, (1, 0): WHITE, (0, 1): WHITE}
    _ok(_makes_crosscut(b, 1, 1, BLACK), "crosscut must be detected for Black")
    _ok(not _legal_placement(b, 5, 1, 1, BLACK), "crosscut placement must be illegal")
    # White at (1,1) makes W-W strong + no checkerboard -> no crosscut.
    _ok(not _makes_crosscut(b, 1, 1, WHITE), "no crosscut for White at (1,1)")


# ---- the four worked examples from the official PDF (5x5 boards) ----------
# Coordinates: (col,row), row 0 = the top row of the diagram.

def test_pdf_legal_example_1():
    # W(0,1) W(2,1) / B(0,2) [1 at (1,2)] W(2,2) B(4,2) / marked B q=(2,3) /
    # B(2,4) W(3,4).  Black 1 at (1,2) is LEGAL: weak to q(2,3), and both
    # empty strong attachments to q — (1,3) and (3,3) — would themselves make
    # weak connections (to B(0,2) and B(4,2) respectively).
    b = _board(["....." ,
                "O.O..",
                "X.O.X",
                "..X..",
                "..XO."])
    _ok(_weak_partners(b, 1, 2, BLACK) == [(2, 3)], "1 must be weak to q(2,3)")
    _ok(_legal_placement(b, 5, 1, 2, BLACK), "PDF legal example 1 must be legal")
    # ... because the alternatives are dirty:
    _ok(_weak_partners(b, 1, 3, BLACK) == [(0, 2)], "(1,3) must be weak to (0,2)")
    _ok(_weak_partners(b, 3, 3, BLACK) == [(4, 2)], "(3,3) must be weak to (4,2)")


def test_pdf_legal_example_2():
    # W(2,2) / W(0,3) [1 at (1,3)] B(2,3) / marked B q=(0,4).
    # Black 1 at (1,3) is LEGAL: weak to q(0,4); q's only empty strong
    # attachment (1,4) would be weakly connected to B(2,3).
    b = _board([".....",
                ".....",
                "..O..",
                "O.X..",
                "X...."])
    _ok(_weak_partners(b, 1, 3, BLACK) == [(0, 4)], "1 must be weak to q(0,4)")
    _ok(_legal_placement(b, 5, 1, 3, BLACK), "PDF legal example 2 must be legal")


def test_pdf_illegal_example_1():
    # W(0,1) W(2,1) / marked B q=(0,2) W(2,2) B(4,2) / [1 at (1,3)] B(2,3) /
    # B(2,4) W(3,4).  Black 1 at (1,3) is ILLEGAL: weak to q(0,2), and the
    # marked empty point (0,3) is a clean strong attachment to q.
    b = _board([".....",
                "O.O..",
                "X.O.X",
                "..X..",
                "..XO."])
    _ok(_weak_partners(b, 1, 3, BLACK) == [(0, 2)], "1 must be weak to q(0,2)")
    _ok(not _legal_placement(b, 5, 1, 3, BLACK),
        "PDF illegal example 1 must be illegal")
    # 'Black could play at the marked empty point instead':
    _ok(_legal_placement(b, 5, 0, 3, BLACK) and not _weak_partners(b, 0, 3, BLACK),
        "(0,3) must be a clean legal strong attachment")
    # Once that clean alternative is occupied, the SAME weak placement
    # becomes legal (the other attachment (1,2) is dirty: weak to B(2,3)).
    b2 = dict(b)
    b2[(0, 3)] = WHITE
    _ok(_weak_partners(b2, 1, 2, BLACK) == [(2, 3)], "(1,2) must be weak to (2,3)")
    _ok(_legal_placement(b2, 5, 1, 3, BLACK),
        "weak placement must become legal once no clean strong alternative exists")


def test_pdf_illegal_example_2():
    # W(2,2) / W(0,3) marked B q=(2,3) / B(0,4) [1 at (1,4)].
    # Black 1 at (1,4) is ILLEGAL: weak to q(2,3); (3,3) and (2,4) are clean
    # strong attachments to q.
    b = _board([".....",
                ".....",
                "..O..",
                "O.X..",
                "X...."])
    _ok(_weak_partners(b, 1, 4, BLACK) == [(2, 3)], "1 must be weak to q(2,3)")
    _ok(not _legal_placement(b, 5, 1, 4, BLACK),
        "PDF illegal example 2 must be illegal")


# ---- the official 5x5 sample game (PDF page 2) ----------------------------

SAMPLE = [  # (col,row), row 0 = top; Black plays the odd move numbers
    (2, 2), (3, 1), (2, 1), (2, 4), (2, 3), (0, 4), (4, 4), (3, 4),
    (4, 3), (3, 3), (4, 2), (3, 0), (4, 1), (4, 0), (3, 2), (2, 0),
    (0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2), (0, 3), (1, 4),
    (1, 3),
]


def test_official_sample_game():
    g = Konobi()
    s = g.initial_state({"size": 5})
    for i, (c, r) in enumerate(SAMPLE):
        _ok(not g.is_terminal(s), f"game ended early before move {i + 1}")
        _ok(g.current_player(s) == i % 2, f"wrong player to move at move {i + 1}")
        if i == 23:
            # The rule sheet: "24 at 25 would have been illegal for White"
            # (move 24 played at (1,3), where Black's 25 later landed).
            _ok("1,3" not in g.legal_moves(s),
                "White at (1,3) on move 24 must be illegal (PDF anchor)")
        mv = f"{c},{r}"
        _ok(mv in g.legal_moves(s), f"sample move {i + 1} at {mv} must be legal")
        s = g.apply_move(s, mv)
    _ok(s.winner == BLACK, "Black must win the sample game on move 25")
    _ok(g.is_terminal(s) and g.returns(s) == [1.0, -1.0], "bad terminal/returns")


# ---- wins through a genuinely weak link, both colours ----------------------

def _strong_only_spans(board, player, size):
    """Spans own edges using ONLY strong (orthogonal) links?"""
    if player == BLACK:
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == BLACK]
        goal = lambda p: p[1] == size - 1  # noqa: E731
    else:
        starts = [(0, r) for r in range(size) if board.get((0, r)) == WHITE]
        goal = lambda p: p[0] == size - 1  # noqa: E731
    seen = set(starts)
    stack = list(starts)
    while stack:
        p = stack.pop()
        if goal(p):
            return True
        for dc, dr in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nb = (p[0] + dc, p[1] + dr)
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


def test_black_win_via_weak_link():
    g = Konobi()
    s = g.initial_state({"size": 5})
    # B builds (0,4) + (2,3), W plays (0,3),(2,2); then B(1,3) is a LEGAL weak
    # attachment to (0,4) (same shape as PDF legal example 2) and B extends
    # the column to the top. The winning chain crosses the (1,3)~(0,4) weak link.
    seq = ["0,4", "0,3", "2,3", "2,2", "1,3", "4,0", "1,2", "4,4",
           "1,1", "0,0", "1,0"]
    for i, mv in enumerate(seq):
        _ok(mv in g.legal_moves(s), f"black-weak-win move {i + 1} ({mv}) illegal")
        pre = s
        s = g.apply_move(s, mv)
    _ok(s.winner == BLACK, "Black must win via the weak link")
    _ok(not _strong_only_spans(s.board, BLACK, 5),
        "the win must genuinely require the weak (diagonal) link")
    _ok(_weak_partners({k: v for k, v in s.board.items() if k != (1, 3)},
                       1, 3, BLACK).count((0, 4)) == 1,
        "(1,3)~(0,4) must be a weak link in the winning chain")


def test_white_win_via_weak_link():
    g = Konobi()
    s = g.initial_state({"size": 5})
    # Mirror-image construction for White (left-right), Black playing fillers.
    seq = ["3,0", "4,0", "2,2", "3,2", "0,4", "3,1", "2,4", "2,1",
           "4,4", "1,1", "0,3", "0,1"]
    for i, mv in enumerate(seq):
        _ok(mv in g.legal_moves(s), f"white-weak-win move {i + 1} ({mv}) illegal")
        s = g.apply_move(s, mv)
    _ok(s.winner == WHITE, "White must win via the weak link")
    _ok(not _strong_only_spans(s.board, WHITE, 5),
        "the White win must genuinely require the weak link")


# ---- pie rule ---------------------------------------------------------------

def test_pie_swap():
    g = Konobi()
    s = g.initial_state({"size": 7})
    _ok("swap" not in g.legal_moves(s), "no swap on Black's first move")
    s = g.apply_move(s, "2,1")
    _ok("swap" in g.legal_moves(s), "White must be offered the swap on move 2")
    s2 = g.apply_move(s, "swap")
    _ok(s2.board == {(1, 2): WHITE},
        "swap must mirror Black's stone to (1,2) as White")
    _ok(g.current_player(s2) == BLACK, "Black to move after the swap")
    _ok("swap" not in g.legal_moves(s2), "swap only available once")
    s3 = g.apply_move(s2, "3,3")
    _ok("swap" not in g.legal_moves(s3), "no swap after move 2")


# ---- drawless playouts + round-trip ----------------------------------------

def test_playouts_drawless():
    g = Konobi()
    rng = random.Random(2026)
    wins = {BLACK: 0, WHITE: 0}
    for trial in range(500):
        s = g.initial_state({"size": 6})
        steps = 0
        while not g.is_terminal(s):
            moves = g.legal_moves(s)
            _ok(moves, "legal_moves empty on a non-terminal state")
            s = g.apply_move(s, rng.choice(moves))
            steps += 1
            _ok(steps <= 6 * 6 + 8, "termination broken (too many plies)")
        _ok(s.winner in (BLACK, WHITE), f"trial {trial}: drawless property violated")
        wins[s.winner] += 1
    _ok(wins[BLACK] > 0 and wins[WHITE] > 0, "both colours should win sometimes")
    return wins


def test_serialize_roundtrip():
    import json
    g = Konobi()
    s = g.initial_state({"size": 7})
    rng = random.Random(11)
    for _ in range(9):
        if g.is_terminal(s):
            break
        s = g.apply_move(s, rng.choice(g.legal_moves(s)))
    d = g.serialize(s)
    _ok(g.serialize(g.deserialize(d)) == d, "serialize round-trip mismatch")
    json.dumps(d)


def main():
    test_strong_weak_classification()
    test_crosscut_ban()
    test_pdf_legal_example_1()
    test_pdf_legal_example_2()
    test_pdf_illegal_example_1()
    test_pdf_illegal_example_2()
    test_official_sample_game()
    test_black_win_via_weak_link()
    test_white_win_via_weak_link()
    test_pie_swap()
    wins = test_playouts_drawless()
    test_serialize_roundtrip()
    print(f"playouts 6x6: Black {wins[BLACK]} / White {wins[WHITE]} / draws 0")
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
