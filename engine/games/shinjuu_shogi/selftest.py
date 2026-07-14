"""Shinjuu Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Anchors (every geometry below was read square-by-square from Silverman's move
guide PDF, https://drericsilverman.com/wp-content/uploads/2021/11/shinjuu-shogi-guide.pdf):

  * the exact 11x11 / 58-piece / 16-type / 29-per-side starting setup, with the
    deliberate left/right asymmetry (Blue Dragon / Turtle Snake / Old Kite left,
    White Tiger / Vermillion Sparrow / Fierce Eagle right); White = 180-deg
    rotation of Black;
  * the exact move-target set of every one of the 30 piece-forms (16 base + 14
    promoted) from the centre of an empty board -- the frozen CENTRE table;
  * the three "special" pieces with blockers: the Golden Bird leaping over up to
    3 pieces on a forward diagonal, the Wooden Dove jumping to the 3rd diagonal
    square then sliding 1-2 more, the Great Dragon jumping 2/3 sideways;
  * drops: capture banks to hand, nifu (no two unpromoted pawns on a file), no
    pawn drop on the last rank; promotion: optional in the far 3 ranks, mandatory
    only for a Pawn reaching the last rank; King and Great Standard never promote;
  * forward-vs-reverse attack consistency (attacked() agrees with _piece_targets)
    under random fuzz;
  * checkmate detection; serialize round-trips; opening perft d1/d2/d3 =
    39 / 1521 / 60799 (self-computed, frozen); a random game terminates.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.shinjuu_shogi.game import ShinjuuShogi, SPEC_BASE, SPEC_PROMO   # noqa: E402
from agp.shogilike import SState, BLACK, WHITE                             # noqa: E402

G = ShinjuuShogi()


def st(board, to_move=BLACK, promoted=(), hands=None):
    s = SState(board=dict(board), promoted=frozenset(promoted),
               hands=hands or {BLACK: {}, WHITE: {}}, to_move=to_move)
    s.reps = {G._poskey(s): 1}
    return s


def perft(state, d):
    if d == 0:
        return 1
    ms = G.legal_moves(state)
    if d == 1:
        return len(ms)
    return sum(perft(G.apply_move(state, m), d - 1) for m in ms)


def center_targets(letter, prom):
    c = (5, 5)
    ts = G._piece_targets({c: (BLACK, letter)}, c, BLACK, letter, prom)
    return tuple(sorted((x - 5, y - 5) for (x, y) in ts))


# Exact centre move-target offsets (dc, df) [df = forward], one per piece-form,
# read from the guide PDF's orange step-cells + red slide-arrows. Rays reach the
# board edge (|off| up to 5 from centre); ranges are capped; jumpers show gaps.
CENTER = {
    ('P', False): ((0, 1),),
    ('G', False): ((-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)),
    ('K', False): ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)),
    ('L', False): ((-1, -1), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 1)),
    ('D', False): ((-1, -1), (0, 1), (1, -1)),
    ('O', False): ((-2, 0), (-1, 0), (-1, 1), (0, -2), (0, -1), (0, 1), (0, 2), (1, 0), (1, 1), (2, 0)),
    ('E', False): ((-2, -2), (-2, 0), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, -1), (1, 0), (1, 1), (2, -2), (2, 0)),
    ('T', False): ((-5, 5), (-4, 4), (-3, 3), (-2, -2), (-2, 2), (-1, -1), (-1, 1), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, -1), (1, 1), (2, -2), (2, 2), (3, 3), (4, 4), (5, 5)),
    ('V', False): ((-5, 5), (-4, 4), (-3, 3), (-2, -2), (-2, 2), (-1, -1), (-1, 1), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (1, -1), (1, 1), (2, -2), (2, 2), (3, 3), (4, 4), (5, 5)),
    ('F', False): ((-5, 5), (-4, 4), (-3, 3), (-2, -2), (-2, 0), (-2, 2), (-1, -1), (-1, 0), (-1, 1), (0, -2), (0, -1), (0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, -2), (2, 0), (2, 2), (3, 3), (4, 4), (5, 5)),
    ('W', False): ((-5, -5), (-4, -4), (-3, -3), (-2, -2), (-2, 0), (-2, 2), (-1, -1), (-1, 0), (-1, 1), (0, -2), (0, -1), (0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, -2), (2, 0), (2, 2), (3, -3), (4, -4), (5, -5)),
    ('B', False): ((-2, 0), (-1, 0), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 0), (1, 1), (2, 0), (2, 2), (3, 3), (4, 4), (5, 5)),
    ('X', False): ((-5, 0), (-5, 5), (-4, 0), (-4, 4), (-3, 0), (-3, 3), (-2, 0), (-2, 2), (-1, 0), (-1, 1), (0, -2), (0, -1), (0, 1), (0, 2), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)),
    ('R', False): ((-2, 0), (-1, -1), (-1, 1), (0, -2), (0, 2), (1, -1), (1, 1), (2, 0)),
    ('N', False): ((-2, -2), (-2, 2), (-1, 0), (0, -1), (0, 1), (1, 0), (2, -2), (2, 2)),
    ('S', False): ((-5, 0), (-5, 5), (-4, 0), (-4, 4), (-3, 0), (-3, 3), (-2, -2), (-2, 0), (-2, 2), (-1, -1), (-1, 0), (-1, 1), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, -1), (1, 0), (1, 1), (2, -2), (2, 0), (2, 2), (3, 0), (3, 3), (4, 0), (4, 4), (5, 0), (5, 5)),
    ('P', True):  ((-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)),
    ('G', True):  ((-5, 0), (-5, 5), (-4, 0), (-4, 4), (-3, 0), (-3, 3), (-2, 0), (-2, 2), (-1, 0), (-1, 1), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 0), (1, 1), (2, 0), (2, 2), (3, 0), (3, 3), (4, 0), (4, 4), (5, 0), (5, 5)),
    ('L', True):  ((-1, -1), (-1, 0), (-1, 1), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, -1), (1, 0), (1, 1)),
    ('D', True):  ((-5, -5), (-4, -4), (-3, -3), (-2, -2), (-1, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, -1), (2, -2), (3, -3), (4, -4), (5, -5)),
    ('O', True):  ((-5, 5), (-4, 4), (-3, 3), (-2, 2), (-1, 1), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)),
    ('E', True):  ((-2, 0), (-2, 2), (-1, 0), (-1, 1), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 0), (1, 1), (2, 0), (2, 2)),
    ('T', True):  ((-5, -5), (-5, 5), (-4, -4), (-4, 4), (-3, -3), (-3, 3), (-2, -2), (-2, 2), (-1, -1), (-1, 1), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, -1), (1, 1), (2, -2), (2, 2), (3, -3), (3, 3), (4, -4), (4, 4), (5, -5), (5, 5)),
    ('V', True):  ((-5, -5), (-5, 5), (-4, -4), (-4, 4), (-3, -3), (-3, 3), (-2, -2), (-2, 2), (-1, -1), (-1, 1), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (1, -1), (1, 1), (2, -2), (2, 2), (3, -3), (3, 3), (4, -4), (4, 4), (5, -5), (5, 5)),
    ('F', True):  ((-5, -5), (-5, 0), (-4, -4), (-4, 0), (-3, -3), (-3, 0), (-2, -2), (-2, 0), (-2, 2), (-1, -1), (-1, 0), (-1, 1), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, -1), (1, 0), (1, 1), (2, -2), (2, 0), (2, 2), (3, -3), (3, 0), (4, -4), (4, 0), (5, -5), (5, 0)),
    ('W', True):  ((-5, 5), (-4, 4), (-3, 3), (-2, -2), (-2, 0), (-2, 2), (-1, -1), (-1, 0), (-1, 1), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, -1), (1, 0), (1, 1), (2, -2), (2, 0), (2, 2), (3, 3), (4, 4), (5, 5)),
    ('B', True):  ((-2, 0), (-1, 0), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 0), (1, 1), (2, 0), (2, 2), (3, 0), (3, 3), (4, 0), (4, 4), (5, 0), (5, 5)),
    ('X', True):  ((-5, 0), (-5, 5), (-4, 0), (-4, 4), (-3, 0), (-3, 3), (-2, 0), (-2, 2), (-1, 0), (-1, 1), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)),
    ('R', True):  ((-5, 0), (-4, 0), (-3, -3), (-3, 0), (-2, -2), (-2, 0), (-1, -1), (-1, 0), (0, -2), (0, -1), (0, 1), (0, 2), (1, -1), (1, 0), (2, -2), (2, 0), (3, -3), (3, 0), (4, 0), (5, 0)),
    ('N', True):  ((-5, -5), (-5, 5), (-4, -4), (-4, 4), (-3, -3), (-3, 3), (-1, 0), (0, -1), (0, 1), (1, 0), (3, -3), (3, 3), (4, -4), (4, 4), (5, -5), (5, 5)),
}

PER_TYPE = {"B": 1, "R": 2, "N": 2, "L": 2, "G": 2, "K": 1, "X": 1, "T": 1,
            "F": 1, "S": 1, "W": 1, "V": 1, "O": 1, "E": 1, "D": 2, "P": 9}


def main():
    s0 = G.initial_state()

    # ---- 1) setup ---------------------------------------------------------
    assert G.WIDTH == G.HEIGHT == 11 and G.ZONE == 3
    assert len(s0.board) == 58
    assert sum(PER_TYPE.values()) == 29 and len(PER_TYPE) == 16
    for pl in (BLACK, WHITE):
        assert sum(1 for v in s0.board.values() if v[0] == pl) == 29
    counts = {}
    for (pl, t) in s0.board.values():
        counts[(pl, t)] = counts.get((pl, t), 0) + 1
    for pl in (BLACK, WHITE):
        for t, n in PER_TYPE.items():
            assert counts[(pl, t)] == n, (pl, t, counts.get((pl, t)))
    # Black back rank + the left/right asymmetry (files 1..11 = cols 0..10)
    assert [s0.board[(c, 0)][1] for c in range(11)] == \
        ["B", "R", "N", "L", "G", "K", "G", "L", "N", "R", "X"]
    assert s0.board[(1, 1)] == (BLACK, "T") and s0.board[(9, 1)] == (BLACK, "V")
    assert s0.board[(3, 1)] == (BLACK, "F") and s0.board[(7, 1)] == (BLACK, "W")
    assert s0.board[(5, 1)] == (BLACK, "S")
    assert s0.board[(3, 2)] == (BLACK, "O") and s0.board[(7, 2)] == (BLACK, "E")
    assert all(s0.board[(c, 2)] == (BLACK, "P")
               for c in range(11) if c not in (3, 7))
    assert s0.board[(3, 3)] == (BLACK, "D") and s0.board[(7, 3)] == (BLACK, "D")
    # White = 180-deg rotation
    for (c, r), (p, t) in s0.board.items():
        if p == BLACK:
            assert s0.board[(10 - c, 10 - r)] == (WHITE, t)

    # ---- 2) exact centre move geometry (guide PDF) ------------------------
    for (letter, prom), expect in CENTER.items():
        got = center_targets(letter, prom)
        assert got == expect, (letter, prom, got)
    # King and Great Standard do not promote; all 14 others do.
    assert set(G.CAN_PROMOTE) == set(SPEC_BASE) - {"K", "S"}
    assert "K" not in SPEC_PROMO and "S" not in SPEC_PROMO
    assert len(SPEC_BASE) == 16 and len(SPEC_PROMO) == 14

    # ---- 3) the three special pieces with blockers ------------------------
    def off(board, sq, letter, prom):
        return {(c - sq[0], r - sq[1])
                for (c, r) in G._piece_targets(board, sq, BLACK, letter, prom)}
    # Golden Bird (+W): leap over <=3 pieces on a forward diagonal, blocked by
    # an own piece at distance 4 (captures at 1,2,3 only).
    b = {(5, 5): (BLACK, "W")}
    for d, owner in ((1, WHITE), (2, WHITE), (3, WHITE), (4, BLACK)):
        b[(5 + d, 5 + d)] = (owner, "P")
    fr = {o for o in off(b, (5, 5), "W", True) if o[0] > 0 and o[1] > 0}
    assert fr == {(1, 1), (2, 2), (3, 3)}, fr
    # Wooden Dove (+N): jumps over dist 1,2 (any contents), captures enemy at 3.
    b = {(5, 5): (BLACK, "N"), (6, 6): (WHITE, "P"), (7, 7): (BLACK, "P"),
         (8, 8): (WHITE, "P")}
    fr = {o for o in off(b, (5, 5), "N", True) if o[0] > 0 and o[1] > 0}
    assert fr == {(3, 3)}, fr
    # Wooden Dove: empty at 3 -> slide to 4, blocked by own at 5.
    b = {(5, 5): (BLACK, "N"), (10, 10): (BLACK, "P")}
    fr = {o for o in off(b, (5, 5), "N", True) if o[0] > 0 and o[1] > 0}
    assert fr == {(3, 3), (4, 4)}, fr
    # Great Dragon (+R): jump 2/3 sideways over an adjacent own piece.
    b = {(5, 5): (BLACK, "R"), (6, 5): (BLACK, "P")}
    fr = {o for o in off(b, (5, 5), "R", True) if o[1] == 0 and o[0] > 0}
    assert fr == {(2, 0), (3, 0)}, fr

    # ---- 4) promotion -----------------------------------------------------
    # Leopard entering the zone (row >= 8) may optionally promote.
    s = st({(0, 0): (BLACK, "K"), (10, 10): (WHITE, "K"), (5, 7): (BLACK, "L")})
    mv = [m for m in G.legal_moves(s) if m.startswith("5,7>")]
    assert any(m.endswith("=+") for m in mv) and any(not m.endswith("=+") for m in mv)
    # Pawn reaching the last rank MUST promote (mandatory, only option).
    s = st({(0, 0): (BLACK, "K"), (10, 10): (WHITE, "K"), (4, 9): (BLACK, "P")})
    mv = [m for m in G.legal_moves(s) if m.startswith("4,9>")]
    assert mv == ["4,9>4,10=+"], mv

    # ---- 5) drops: banking, nifu, last rank -------------------------------
    s = st({(0, 0): (BLACK, "K"), (10, 10): (WHITE, "K"), (5, 5): (BLACK, "G"),
            (5, 6): (WHITE, "P")})
    s2 = G.apply_move(s, "5,5>5,6")            # gold captures a pawn
    assert s2.hands[BLACK] == {"P": 1}
    # a hand pawn: cannot drop on the file already holding a pawn (nifu), and
    # cannot drop on the last rank.
    s = st({(0, 0): (BLACK, "K"), (10, 10): (WHITE, "K"), (4, 3): (BLACK, "P")},
           hands={BLACK: {"P": 1}, WHITE: {}})
    drops = [m for m in G.legal_moves(s) if m.startswith("P@")]
    files = {int(m.split("@")[1].split(",")[0]) for m in drops}
    assert 4 not in files, "nifu failed"
    assert not any(m.split("@")[1].endswith(",10") for m in drops), "last-rank pawn drop"

    # ---- 6) checkmate -----------------------------------------------------
    s = st({(5, 0): (BLACK, "K"), (5, 1): (WHITE, "G"), (5, 2): (WHITE, "L"),
            (9, 9): (WHITE, "K")})
    assert G.in_check(s.board, s.promoted, BLACK)
    assert G.legal_moves(s) == [] and G.is_terminal(s)
    assert G.returns(s) == [-1.0, 1.0]
    # removing the defender lets the king capture the checker (not mate)
    s = st({(5, 0): (BLACK, "K"), (5, 1): (WHITE, "G"), (9, 9): (WHITE, "K")})
    assert "5,0>5,1" in G.legal_moves(s) and not G.is_terminal(s)

    # ---- 7) forward-vs-reverse attack consistency (fuzz) ------------------
    letters = list(SPEC_BASE)
    rng = random.Random(20260714)
    for _ in range(400):
        board = {}
        cells = [(c, r) for c in range(11) for r in range(11)]
        rng.shuffle(cells)
        promoted = set()
        for i in range(rng.randint(3, 14)):
            sq = cells[i]
            L = rng.choice(letters)
            pr = L in SPEC_PROMO and rng.random() < 0.4
            board[sq] = (rng.choice([BLACK, WHITE]), L)
            if pr:
                promoted.add(sq)
        promoted = frozenset(promoted)
        # brute-force forward attack set for each colour
        for by in (BLACK, WHITE):
            reach = set()
            for psq, (p, t) in board.items():
                if p == by:
                    reach |= set(G._piece_targets(board, psq, by, t, psq in promoted))
            for c in range(11):
                for r in range(11):
                    exp = (c, r) in reach
                    assert G.attacked(board, promoted, (c, r), by) == exp, \
                        ((c, r), by)

    # ---- 8) serialize round-trip + perft + termination --------------------
    s = st({(5, 0): (BLACK, "K"), (5, 1): (WHITE, "G"), (5, 2): (WHITE, "L"),
            (9, 9): (WHITE, "K")}, promoted=[(5, 2)],
           hands={BLACK: {"P": 2, "R": 1}, WHITE: {"N": 1}})
    d = G.serialize(s)
    s2 = G.deserialize(d)
    assert s2.board == s.board and s2.promoted == s.promoted and s2.hands == s.hands

    ms0 = G.legal_moves(s0)
    assert len(ms0) == len(set(ms0)), "duplicate move strings"
    assert perft(s0, 1) == 39, perft(s0, 1)
    assert perft(s0, 2) == 1521, perft(s0, 2)
    assert perft(s0, 3) == 60799, perft(s0, 3)

    rng = random.Random(2)
    s = s0
    n = 0
    while not G.is_terminal(s) and n < 600:
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        n += 1
    assert G.is_terminal(s)

    print("shinjuu_shogi selftest: all assertions passed "
          "(setup 29/side, perft 39/1521/60799, 30 piece-forms, "
          "specials, drops/nifu, checkmate, attack-consistency).")


if __name__ == "__main__":
    main()
