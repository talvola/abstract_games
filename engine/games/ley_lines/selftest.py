"""Ley Lines correctness anchor.

Primary anchor: the "Sample position" figure from Abstract Games Issue 17
(pp. 44). The 63-stone layout below was pixel-read from that figure (the article
states 63 stones are used); the two labelled ley lines and the ring-start cells
(marked 1 and 2) were verified to be exactly collinear and to contain exactly
the stones the article narrates.

We then replay the article's worked example move-for-move and assert the piles
match the narration:

  * P1 single-steps 1->a, P2 single-steps 2->f.
  * P1 jumps a->b->c->d->e, "capturing 5 stones which will score 10 because he
    captured all stones in a line"  => pile1 = 5 (doubles to 10).
  * P2 jumps f->g->h, "and could have gone on to i, capturing all 4 stones in
    the line"  => stops at h: pile2 = 3; the continuation to i is legal.

Pure stdlib; run: `python3 games/ley_lines/selftest.py`.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

MAN, G = load_from_dir(Path(__file__).resolve().parent)

# --- Sample position: 63 white stones (pixel-read from the AG#17 figure) ------
SAMPLE = [
    (0, 8), (0, 14), (1, 0), (1, 2), (1, 5), (1, 8), (1, 10), (2, 1), (2, 7),
    (2, 10), (2, 12), (2, 17), (3, 4), (3, 14), (4, 0), (4, 7), (4, 9), (4, 12),
    (4, 13), (4, 15), (5, 2), (6, 9), (6, 14), (7, 0), (7, 6), (7, 7), (7, 13),
    (7, 16), (8, 2), (8, 4), (8, 13), (8, 17), (9, 6), (9, 10), (10, 0), (10, 2),
    (10, 3), (10, 7), (10, 11), (10, 15), (10, 17), (11, 1), (12, 6),
    (12, 16), (13, 2), (13, 4), (13, 7), (13, 10), (13, 12), (13, 17), (14, 1),
    (14, 3), (14, 9), (14, 11), (14, 13), (15, 17), (16, 3), (16, 7), (16, 9),
    (16, 15), (17, 0), (17, 5), (17, 12),
]
# Labelled cells (from the figure):
A, B, C, D, E = (2, 17), (4, 13), (6, 9), (7, 7), (10, 2)     # line 1 (P1)
F, Gg, Hh, I = (7, 16), (6, 14), (2, 7), (1, 5)               # line 2 (P2)
RING1, RING2 = (1, 17), (8, 16)                               # cells "1" and "2"


def cs(cell):
    return f"{cell[0]},{cell[1]}"


def sample_state(prev_step=(False, False)):
    """The sample position with both rings placed, P1 to move."""
    d = {
        "stones": {cs(c): "W" for c in SAMPLE},
        "rings": [cs(RING1), cs(RING2)],
        "phase": "move",
        "place_order": [],
        "turn": 0,
        "piles": [[0, 0], [0, 0]],
        "prev_step": list(prev_step),
        "passes": 0, "plies": 0, "over": False, "last": [],
    }
    return G.deserialize(d)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ---------------------------------------------------------------------------
def test_worked_example():
    s0 = sample_state()
    check(G.num_players == 2, "num_players")

    # 1) P1 single-steps 1 -> a
    step1 = f"{cs(RING1)}>{cs(A)}"
    check(step1 in G.legal_moves(s0), "step 1->a must be legal")
    s1 = G.apply_move(s0, step1)
    check(s1.rings[0] == A, "ring0 on a")
    check(s1.prev_step[0] is True, "prev_step[0] set by the single step")
    check(G.current_player(s1) == 1, "P2 to move")

    # 2) P2 single-steps 2 -> f
    step2 = f"{cs(RING2)}>{cs(F)}"
    check(step2 in G.legal_moves(s1), "step 2->f must be legal")
    s2 = G.apply_move(s1, step2)
    check(s2.rings[1] == F and s2.prev_step[1] is True, "ring1 on f, prev_step set")
    check(G.current_player(s2) == 0, "P1 to move")

    # partial jump prefix a->b must also be offered
    check(f"{cs(A)}>{cs(B)}=J" in G.legal_moves(s2), "partial jump a->b legal")

    # 3) P1 jumps a->b->c->d->e : complete line of 5, doubles to 10
    jump1 = f"{cs(A)}>{cs(B)}>{cs(C)}>{cs(D)}>{cs(E)}=J"
    check(jump1 in G.legal_moves(s2), "full line jump a..e must be legal")
    s3 = G.apply_move(s2, jump1)
    check(s3.piles[0] == [5, 0], f"pile1=5 expected, got {s3.piles[0]}")
    check(G._score(s3, 0) == 10, "P1 score 10")
    check(s3.rings[0] == E, "ring0 ends on e")
    for cell in (A, B, C, D, E):
        check(s3.stones[cell] == "B", f"{cell} captured (black)")
    check(s3.prev_step[0] is False, "jump clears prev_step")

    # 4) P2 jumps f->g->h (stops); the continuation to i is also legal
    jump2 = f"{cs(F)}>{cs(Gg)}>{cs(Hh)}=J"
    jump2_full = f"{cs(F)}>{cs(Gg)}>{cs(Hh)}>{cs(I)}=J"
    lm3 = G.legal_moves(s3)
    check(jump2 in lm3, "jump f->g->h legal")
    check(jump2_full in lm3, "continuation to i legal ('could have gone on to i')")
    s4 = G.apply_move(s3, jump2)
    check(s4.piles[1] == [0, 3], f"P2 partial line -> pile2=3, got {s4.piles[1]}")
    check(G._score(s4, 1) == 3, "P2 score 3")
    check(s4.rings[1] == Hh, "ring1 ends on h")

    # ...and had P2 completed the line to i it would be pile1=4 (score 8)
    s4b = G.apply_move(s3, jump2_full)
    check(s4b.piles[1] == [4, 0], f"full f..i line -> pile1=4, got {s4b.piles[1]}")
    check(G._score(s4b, 1) == 8, "full line scores 8")


def test_complete_line_needs_preceding_step():
    # Same a..e sweep but WITHOUT a preceding single step -> mopped up (pile2).
    s = sample_state(prev_step=(False, False))
    jump1 = f"{cs(A)}>{cs(B)}>{cs(C)}>{cs(D)}>{cs(E)}=J"
    s2 = G.apply_move(s, jump1)
    check(s2.piles[0] == [0, 5],
          f"no preceding step => pile2 (single), got {s2.piles[0]}")
    check(G._score(s2, 0) == 5, "scores single (5) without the step")


def test_lines_are_exact():
    # The two narrated lines must contain EXACTLY the stones the article lists,
    # else "captured all stones in a line" would be wrong.
    from games.ley_lines.game import LeyLines
    st = {c: "W" for c in SAMPLE}
    l1 = set(LeyLines._line_stones(st, A, E))
    check(l1 == {A, B, C, D, E}, f"line 1 must be exactly a..e, got {sorted(l1)}")
    l2 = set(LeyLines._line_stones(st, F, I))
    check(l2 == {F, Gg, Hh, I}, f"line 2 must be exactly f..i, got {sorted(l2)}")


def test_zone_quota_and_deal():
    for seed in range(8):
        s = G.initial_state(rng=random.Random(seed))
        counts = {}
        for (c, r) in s.stones:
            z = (c // 6, r // 6)
            counts[z] = counts.get(z, 0) + 1
        check(len(counts) == 9, "all nine zones present")
        for z, n in counts.items():
            check(n >= 6, f"zone {z} has {n} < 6 stones")
        check(len(s.stones) == 54, f"default deal = 54 stones, got {len(s.stones)}")


def test_placement_order_and_first_mover():
    s = G.initial_state(rng=random.Random(3))
    check(G.current_player(s) == 1, "seat 1 (Player 2) places first")
    s = G.apply_move(s, G.legal_moves(s)[0])
    check(G.current_player(s) == 0, "seat 0 (Player 1) places second")
    last_cell = G.legal_moves(s)[0]
    s = G.apply_move(s, last_cell)
    check(s.phase == "move", "movement begins after both rings placed")
    check(G.current_player(s) == 0, "last player to place (P1) moves first")


def test_termination_and_roundtrip():
    # double pass ends the game as an honest draw from a fresh (empty-score) game
    s = sample_state()
    s = G.apply_move(s, "pass")
    check(not G.is_terminal(s), "one pass does not end the game")
    s = G.apply_move(s, "pass")
    check(G.is_terminal(s), "two consecutive passes end the game")
    check(G.returns(s) == [0.0, 0.0], "equal score is a draw")

    # serialize round-trip
    s3 = G.apply_move(sample_state(), f"{cs(RING1)}>{cs(A)}")
    d1 = G.serialize(s3)
    d2 = G.serialize(G.deserialize(d1))
    check(d1 == d2, "serialize round-trips")

    # a full random game terminates under the ply cap
    rng = random.Random(11)
    s = G.initial_state(rng=rng)
    for _ in range(5000):
        if G.is_terminal(s):
            break
        lm = G.legal_moves(s)
        s = G.apply_move(s, rng.choice(lm), rng=rng)
    check(G.is_terminal(s), "random game terminates")
    r = G.returns(s)
    check(len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r), "well-formed returns")


def test_heuristic_shape():
    # heuristic must return a list of num_players payoffs (bot back-prop safety).
    from agp.mcts import MCTSBot
    s = sample_state()
    h = G.heuristic(s)
    check(isinstance(h, list) and len(h) == 2, "heuristic returns 2-list")
    # force the rollout cutoff so a bad shape would raise
    MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(G, s)


if __name__ == "__main__":
    test_lines_are_exact()
    test_worked_example()
    test_complete_line_needs_preceding_step()
    test_zone_quota_and_deal()
    test_placement_order_and_first_mover()
    test_termination_and_roundtrip()
    test_heuristic_shape()
    print("ley_lines selftest: all checks passed")
