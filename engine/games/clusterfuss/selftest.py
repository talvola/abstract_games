"""Clusterfuss correctness anchors (pure stdlib).

What is pinned here, and by what:

* **Figure 1 — the setup.**  The 4x4 array of the rule sheet's Figure 1, decoded
  from the PDF's vector art, cell by cell: a strict checkerboard with RED on the
  top-left cell.  Plus the per-size material split (even boards are equal; the
  odd board gives Red one extra checker) and the opening move count — **112 on
  the standard 8x8**, which is exactly the number AbstractPlay's independent
  `gameslib` implementation reports for its default board.

* **Figure 2 — the move restriction.**  Red may capture the blue checker on the
  right but NOT the one on the left, because the left capture would leave two
  groups containing red checkers.  The whole legal set of that position is
  frozen.

* **Figures 3a / 3b / 3c — enemy-only group removal.**  Red's capture detaches
  exactly TWO enemy-only groups (Figure 3b shows three groups: Red's singleton
  plus the two blue ones); both are removed at once, leaving the lone red
  checker of Figure 3c, and Red has won.

* **Figures 5 and 6 — the friendly-capture puzzles, SOLVED.**  The sheet asserts
  a game-theoretic value: in both positions Red can capture a FRIENDLY checker
  and win, but capturing an enemy checker instead loses.  Both positions are
  solved exhaustively here and both claims are asserted move by move.  This is
  the strongest anchor in the package: it exercises the move restriction, the
  removal rule, friendly capture and the win condition end to end, and it is the
  designer's own published statement about the ruleset.

* **Termination, proved rather than capped.**  Every move removes at least one
  checker and never adds one, so a game is at most ``n*n - 1`` plies.  Asserted
  move by move on random play at every board size, and the bound is shown to be
  TIGHT (a 4x4 game really does reach 15 plies), so it is not an off-by-one
  guess.  There is no ply cap and no repetition rule to be outcome-load-bearing.

* **Nobody ever has to skip a turn.**  The rule sheet's "if you don't have an
  available move, your turn is skipped" is provably vacuous: after any legal
  move exactly one group survives, and in a connected group the mover's checker
  that is a leaf of the group's spanning tree always has a legal move.  Asserted
  on every position of random play (both seats, every size) AND on random
  connected positions built independently of play, because random play alone
  never even approaches the clause.

* **The immobility draw** — the honest draw the engine falls back on if the
  above ever failed — is exercised from a hand-built position, for both seats,
  and a paired control proves a DECISIVE result outranks it: a WON board with
  the winner still to move and fully mobile must be terminal.  (In real play
  the seat to move after a wipe-out is the loser, who is immobile anyway, so
  an immobility-first terminal test looks correct until exactly that position
  is tried — it survived mutation testing until this check was added.)

* **The game ends the INSTANT the last enemy checker goes**, not a ply later,
  even when the winner still has a healthy mobile army — checked on a
  hand-built win and on every ply of random play.

* **Both seats.**  The engine is asserted to conjugate exactly under the colour
  swap: swap the colours and the side to move, and the legal moves, the
  resulting boards and the payoffs must all transform accordingly.

* **serialize / deserialize** compared as STATE OBJECTS (``deserialize(
  serialize(s)) == s``) plus the exact key set, swept over whole games at every
  size.  ``serialize(deserialize(d)) == d`` is vacuous — it cannot see a field
  ``serialize`` stops emitting.

* **render()** checked for EVERY board size at every ply of a real game (not on
  a fresh board): every rendered piece must lie inside the declared
  ``board.width``/``board.height``, since ``Board.jsx`` silently drops any piece
  outside them.

The move-for-move differential against AbstractPlay's `gameslib` (a second,
independent rule-enforcing implementation) is a one-time manual check; it is not
part of this stdlib selftest because it needs node.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.clusterfuss.game import (  # noqa: E402
    DEFAULT_SIZE, ORTHO, SIZES, CState, Clusterfuss, any_move, cell_name,
    components, counts, gen_moves, group_count, initial_board, moves_for,
    neighbours, parse_cell, resolve,
)

G = Clusterfuss()
R, B = 0, 1


def mk(cells, n=4, to_move=0, ply=0):
    return CState(n=n, board=dict(cells), to_move=to_move, ply=ply, last=None)


def ascii_board(s):
    return "\n".join("".join({R: "R", B: "B", None: "."}[s.board.get((c, r))]
                             for c in range(s.n)) for r in range(s.n - 1, -1, -1))


# --------------------------------------------------------------------------- #
# Figure 1 — the setup                                                         #
# --------------------------------------------------------------------------- #
# Decoded cell by cell from the vector art of Clusterfuss_rules.pdf: a 4x4 board,
# every cell occupied, colours alternating, RED on the top-left cell.
FIG1 = [
    "RBRB",
    "BRBR",
    "RBRB",
    "BRBR",
]


def test_figure1_setup():
    s = G.initial_state(options={"size": 4})
    assert ascii_board(s) == "\n".join(FIG1), ascii_board(s)
    assert s.to_move == 0, "Red moves first"
    assert s.ply == 0 and s.last is None
    assert not G.is_terminal(s)

    for n in SIZES:
        t = G.initial_state(options={"size": n})
        assert len(t.board) == n * n, "the board starts completely FULL"
        assert group_count(t.board, n) == 1, "a full rectangle is one group"
        red, blue = counts(t.board)
        # Even boards split the material evenly; an odd board gives the extra
        # (corner-coloured) checker to Red, who also moves first.
        assert red + blue == n * n
        if n % 2 == 0:
            assert red == blue == n * n // 2, (n, red, blue)
        else:
            assert red == blue + 1 == (n * n + 1) // 2, (n, red, blue)
        # Red owns all four corners on an odd board, and the top-left on any.
        assert t.board[(0, n - 1)] == R, "Red on the top-left cell (Figure 1)"
        # every cell differs from each orthogonal neighbour: a true checkerboard
        for c in range(n):
            for r in range(n):
                for nb in neighbours((c, r), n):
                    assert t.board[nb] != t.board[(c, r)]

    # Opening move counts.  112 on the standard board is the number AbstractPlay's
    # independent implementation reports for its default position.
    assert len(G.legal_moves(G.initial_state())) == 112
    frozen = {4: 24, 5: 40, 6: 60, 8: 112, 10: 180}
    for n, want in frozen.items():
        got = len(G.legal_moves(G.initial_state(options={"size": n})))
        assert got == want, (n, got, want)
    # Derivation: a full n x n rectangle has 2*n*(n-1) orthogonal adjacencies,
    # every one of them bichromatic (the setup is a strict checkerboard), so
    # exactly half of the 4*n*(n-1) ordered pairs start on a red checker — and
    # every one is legal, because removing any single cell from a full rectangle
    # leaves it connected.
    for n in SIZES:
        assert frozen[n] == 2 * n * (n - 1)

    assert G.initial_state().n == DEFAULT_SIZE == 8
    for bad in (3, 7, 9, 12):
        try:
            G.initial_state(options={"size": bad})
        except ValueError:
            pass
        else:
            raise AssertionError(f"size {bad} should be rejected")


# --------------------------------------------------------------------------- #
# Figure 2 — the move restriction                                              #
# --------------------------------------------------------------------------- #
# "In Figure 2, Red can capture the blue checker on the right, but he can't
#  capture the blue checker on the left because then there would be two groups
#  containing red checkers."
#     . . . .
#     . R R .
#     B R B .
#     . . . .
FIG2 = mk({(1, 2): R, (2, 2): R, (1, 1): R, (0, 1): B, (2, 1): B})


def test_figure2_move_restriction():
    assert group_count(FIG2.board, FIG2.n) == 1
    legal = set(G.legal_moves(FIG2))
    assert "1,1>2,1" in legal, "Red CAN capture the blue checker on the right"
    assert "1,1>0,1" not in legal, "Red CANNOT capture the blue checker on the left"
    # the whole legal set, frozen (3 friendly captures both ways + the one enemy
    # capture that keeps Red in a single group)
    assert legal == {"1,1>1,2", "1,1>2,1", "1,2>1,1", "1,2>2,2",
                     "2,2>1,2", "2,2>2,1"}, sorted(legal)
    # friendly capture really is generated, and is the majority of the list here
    friendly = {m for m in legal if FIG2.board[parse_cell(m.split(">")[1])] == R}
    assert len(friendly) == 4, sorted(friendly)

    # ...and the illegal capture is illegal for exactly the stated reason: it
    # would leave two groups holding red checkers.
    after = dict(FIG2.board)
    del after[(1, 1)]
    after[(0, 1)] = R
    labels, _ = components(after, FIG2.n)
    assert len({labels[c] for c, p in after.items() if p == R}) == 2

    # Blue, to move in the same position, has its own moves (both seats live).
    blue_to_move = mk(FIG2.board, to_move=1)
    assert set(G.legal_moves(blue_to_move)) == {"0,1>1,1", "2,1>1,1", "2,1>2,2"}


# --------------------------------------------------------------------------- #
# Figures 3a / 3b / 3c — enemy-only group removal                              #
# --------------------------------------------------------------------------- #
#   FIG 3a          after the capture (3b)      after removal (3c)
#   . B . .            . B . .                     . . . .
#   B R B .            B . R .                     . . R .
#   B B . .            B B . .                     . . . .
FIG3A = mk({(1, 2): B, (0, 1): B, (1, 1): R, (2, 1): B, (0, 0): B, (1, 0): B})


def test_figure3_enemy_only_removal():
    assert group_count(FIG3A.board, FIG3A.n) == 1
    # Figure 3b: the intermediate board, before removal — three groups, of which
    # exactly two are enemy-only.
    mid = dict(FIG3A.board)
    del mid[(1, 1)]
    mid[(2, 1)] = R
    labels, ngroups = components(mid, FIG3A.n)
    assert ngroups == 3
    enemy_only = [i for i in range(ngroups)
                  if all(p == B for c, p in mid.items() if labels[c] == i)]
    assert len(enemy_only) == 2, "Red detaches exactly TWO enemy-only groups"
    assert sorted(sorted(c for c in mid if labels[c] == i) for i in enemy_only) == \
        [[(0, 0), (0, 1), (1, 0)], [(1, 2)]]

    # Figure 3c: both removed at once; a lone red checker remains and Red wins.
    end = G.apply_move(FIG3A, "1,1>2,1")
    assert end.board == {(2, 1): R}, end.board
    assert G.is_terminal(end) and G.returns(end) == [1.0, -1.0]
    assert G.legal_moves(end) == []
    assert "4 cut off" in G.describe_move(FIG3A, "1,1>2,1")
    assert G.describe_move(FIG3A, "1,1>2,1").endswith("wins")

    # The mirror image with the colours swapped must be a Blue win (both seats).
    swapped = mk({c: 1 - p for c, p in FIG3A.board.items()}, to_move=1)
    end2 = G.apply_move(swapped, "1,1>2,1")
    assert end2.board == {(2, 1): B}
    assert G.is_terminal(end2) and G.returns(end2) == [-1.0, 1.0]


# --------------------------------------------------------------------------- #
# Figures 5 and 6 — the friendly-capture puzzles, solved exhaustively          #
# --------------------------------------------------------------------------- #
# "In both examples, Red can capture a friendly checker and then have a path to
#  winning.  But if Red were to capture an enemy checker instead, Blue would have
#  a path to winning."
FIG5 = mk({(0, 2): R, (0, 1): R, (1, 1): B, (2, 1): B, (3, 1): R})
FIG6 = mk({(2, 3): R, (1, 2): R, (2, 2): R, (1, 1): B, (2, 1): B})


def solve(s, memo):
    """Exact game value from RED's point of view (+1 / 0 / -1).

    Driving both seats through one Red-perspective value avoids any sign
    bookkeeping around a skipped turn.
    """
    if G.is_terminal(s):
        return G.returns(s)[0]
    key = (tuple(sorted(s.board.items())), s.to_move)
    if key not in memo:
        memo[key] = None  # cycle guard; the game is acyclic so this never sticks
        vals = [solve(G.apply_move(s, m), memo) for m in G.legal_moves(s)]
        assert all(v is not None for v in vals), "the game graph must be acyclic"
        memo[key] = max(vals) if s.to_move == R else min(vals)
    return memo[key]


def test_figures5_and_6_puzzles():
    memo = {}
    for tag, pos, want_friendly_wins in (("Figure 5", FIG5, {"0,2>0,1"}),
                                         ("Figure 6", FIG6, {"2,3>2,2"})):
        assert group_count(pos.board, pos.n) == 1
        assert solve(pos, memo) == 1.0, f"{tag}: Red to move must be winning"
        friendly_winners, enemy_values = set(), []
        for m in G.legal_moves(pos):
            target = parse_cell(m.split(">")[1])
            v = solve(G.apply_move(pos, m), memo)
            if pos.board[target] == R:
                if v == 1.0:
                    friendly_winners.add(m)
            else:
                enemy_values.append((m, v))
        assert friendly_winners == want_friendly_wins, (tag, friendly_winners)
        assert enemy_values, f"{tag}: there must BE an enemy capture to reject"
        for m, v in enemy_values:
            assert v == -1.0, f"{tag}: capturing an enemy checker ({m}) must lose"

    # And the same puzzles conjugate: swap the colours and the seat and Blue wins.
    for pos in (FIG5, FIG6):
        mirror = mk({c: 1 - p for c, p in pos.board.items()}, to_move=1)
        assert solve(mirror, memo) == -1.0


# --------------------------------------------------------------------------- #
# the two constraints, and the single-group invariant                          #
# --------------------------------------------------------------------------- #

def test_group_invariant_and_removal_semantics():
    """After ANY legal move the board is exactly one group.

    That is what reconciles the sheet's two differently-worded constraints: the
    MOVE RESTRICTIONS paragraph only requires one group *containing your
    checkers*, and the GROUPS paragraph's "only one group on the board" then
    follows, because every other group is by definition enemy-only and is
    removed.  It also holds unconditionally (not merely by induction), which is
    why mutual immobility is unreachable.
    """
    rng = random.Random(20230701)
    seen_removals = 0
    for n in SIZES:
        for gi in range(2 if n >= 8 else 12):
            s = G.initial_state(options={"size": n})
            while not G.is_terminal(s):
                assert group_count(s.board, s.n) == 1
                for m in G.legal_moves(s):
                    x, y = (parse_cell(t) for t in m.split(">"))
                    assert y in neighbours(x, s.n), "captures are orthogonal steps"
                    assert s.board[x] == s.to_move, "you move your OWN checker"
                    assert y in s.board, "every move is a CAPTURE, never a step"
                    mid = dict(s.board)
                    del mid[x]
                    mid[y] = s.to_move
                    labels, _ = components(mid, s.n)
                    mine = {labels[c] for c, p in mid.items() if p == s.to_move}
                    assert len(mine) == 1, "one group containing YOUR checkers"
                before = len(s.board)
                t = G.apply_move(s, rng.choice(G.legal_moves(s)))
                assert group_count(t.board, t.n) == 1
                assert len(t.board) <= before - 1, "a move never adds a checker"
                seen_removals += (before - 1) - len(t.board)
                s = t
    assert seen_removals > 0, "enemy-only removal must actually fire in play"


# --------------------------------------------------------------------------- #
# termination                                                                  #
# --------------------------------------------------------------------------- #

def test_termination_and_no_skipping():
    """Bound: at most n*n - 1 plies, derived from the two named factors (the
    board starts with n*n checkers and every ply removes at least one, and the
    game is over once a colour is gone, i.e. at 1 checker at the latest).

    Also asserts the vacuity of the skip clause and the absence of draws.
    """
    rng = random.Random(4242)
    longest = {}
    results = {n: {0: 0, 1: 0, "draw": 0} for n in SIZES}
    skips = 0
    for n in SIZES:
        games = 300 if n == 4 else (60 if n <= 6 else (8 if n == 8 else 3))
        for gi in range(games):
            s = G.initial_state(options={"size": n})
            prev_count = len(s.board)
            while not G.is_terminal(s):
                mvs = G.legal_moves(s)
                assert mvs, "legal_moves must be non-empty on a non-terminal state"
                mover = s.to_move
                s = G.apply_move(s, rng.choice(mvs))
                assert len(s.board) < prev_count, "strictly decreasing monovariant"
                prev_count = len(s.board)
                # the game must END the moment a colour is wiped out, never one
                # ply later
                if 0 in counts(s.board):
                    assert G.is_terminal(s), sorted(s.board.items())
                if not G.is_terminal(s) and s.to_move == mover:
                    skips += 1
                assert s.ply <= n * n - 1, (n, s.ply)
            longest[n] = max(longest.get(n, 0), s.ply)
            ret = G.returns(s)
            results[n][0 if ret[0] > 0 else (1 if ret[1] > 0 else "draw")] += 1
    assert skips == 0, "a turn is never actually skipped (the clause is vacuous)"
    total = {0: 0, 1: 0}
    for n in SIZES:
        assert results[n]["draw"] == 0, (n, results[n])
        assert longest[n] <= n * n - 1
        total[0] += results[n][0]
        total[1] += results[n][1]
        if n <= 6:      # only the large samples are statistically safe per size
            assert results[n][0] > 0 and results[n][1] > 0, \
                f"both seats must win some games on {n}x{n}: {results[n]}"
    assert total[0] > 0 and total[1] > 0, total
    # the bound is TIGHT, not an off-by-one guess: a 4x4 game really reaches 15
    assert longest[4] == 4 * 4 - 1, longest


def test_nobody_is_ever_stuck():
    """A player holding at least one checker on a single-group board ALWAYS has
    a legal move.

    Proof: take the subtree of a spanning tree of the group spanned by that
    player's checkers, and let X be one of its leaves (X is the player's).
    Removing X from the tree leaves every other checker of the player's in one
    component, and every component of the group minus X touches X, so some
    neighbour Y of X lies in that component: X->Y is legal.

    Random play never gets anywhere near this clause (it produced zero skips
    above), so it is checked here directly, on positions built independently of
    play: random connected boards with a random 2-colouring.
    """
    rng = random.Random(99)
    checked = 0
    for trial in range(1200):
        n = rng.choice((4, 5, 6))
        size = rng.randint(2, min(12, n * n))
        # grow a random connected cell set
        cells = [(rng.randrange(n), rng.randrange(n))]
        while len(cells) < size:
            base = cells[rng.randrange(len(cells))]
            opts = [nb for nb in neighbours(base, n) if nb not in cells]
            if not opts:
                if all(all(nb in cells for nb in neighbours(c, n)) for c in cells):
                    break
                continue
            cells.append(opts[rng.randrange(len(opts))])
        board = {c: rng.randrange(2) for c in cells}
        if group_count(board, n) != 1 or len(board) < 2:
            continue
        for p in (0, 1):
            if any(v == p for v in board.values()):
                assert any_move(board, n, p), (n, sorted(board.items()), p)
                checked += 1
    assert checked > 1500, checked


def test_any_move_matches_moves_for():
    """``any_move`` is an early-exit twin of ``moves_for``; a divergence would
    silently mis-skip a turn.  Pinned on real play, both seats."""
    rng = random.Random(7)
    n = 6
    for gi in range(20):
        s = G.initial_state(options={"size": n})
        while not G.is_terminal(s):
            for p in (0, 1):
                assert any_move(s.board, n, p) == bool(moves_for(s.board, n, p))
            assert moves_for(s.board, n, s.to_move) == sorted(
                gen_moves(s.board, n, s.to_move))
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))


# --------------------------------------------------------------------------- #
# terminal classification                                                      #
# --------------------------------------------------------------------------- #

def test_terminal_classification():
    # Wiping the enemy out wins, for either seat.
    assert G.is_terminal(mk({(0, 0): R})) and G.returns(mk({(0, 0): R})) == [1.0, -1.0]
    assert G.is_terminal(mk({(0, 0): B})) and G.returns(mk({(0, 0): B})) == [-1.0, 1.0]

    # ...and the game ends the INSTANT the last enemy checker goes, even though
    # the winner still has a healthy, fully mobile army.  (A terminal test that
    # only looks at immobility would let the winner keep capturing his own
    # checkers after the game was already decided.)
    #   R .        R R
    #   R B  --->  R .   : Red steps right, takes the last blue, and has won
    won = G.apply_move(mk({(0, 1): R, (1, 1): R, (0, 0): R, (1, 0): B}), "0,0>1,0")
    assert won.board == {(0, 1): R, (1, 1): R, (1, 0): R}
    assert counts(won.board) == (3, 0)
    assert any_move(won.board, won.n, R), "control: the winner is NOT immobile"
    assert G.is_terminal(won), "a wipe-out ends the game at once"
    assert G.legal_moves(won) == [] and G.returns(won) == [1.0, -1.0]
    # the same for seat 1
    won_b = G.apply_move(mk({(0, 1): B, (1, 1): B, (0, 0): B, (1, 0): R},
                            to_move=1), "0,0>1,0")
    assert counts(won_b.board) == (0, 3) and G.is_terminal(won_b)
    assert G.returns(won_b) == [-1.0, 1.0] and G.legal_moves(won_b) == []

    # A DECISIVE result outranks the immobility draw.  The lone-checker states
    # above are also totally immobile, so if the draw test ran first they would
    # score 0-0.  Control: the same immobility WITHOUT a wipe-out IS a draw.
    for seat in (0, 1):
        won = mk({(0, 0): R}, to_move=seat)
        assert G.returns(won) == [1.0, -1.0], "a wipe-out must outrank immobility"
        assert not any_move(won.board, won.n, seat), "control: the winner is immobile"
        drawn = mk({(0, 0): R, (2, 2): B}, to_move=seat)
        assert G.is_terminal(drawn), "mutual immobility ends the game"
        assert G.returns(drawn) == [0.0, 0.0], "and it is an honest DRAW"
        assert G.legal_moves(drawn) == []
        assert "Draw" in G.render(drawn)["caption"]

    # THE DECISIVE CHECK MUST COME FIRST.  Re-score a WON board with the WINNER
    # to move and still fully mobile: an engine that consulted immobility first
    # would call this non-terminal and let the winner carry on capturing his own
    # checkers after the game was already decided.  (In real play the seat to
    # move after a wipe-out is the loser, who is immobile anyway, so this
    # ordering bug is invisible without exactly this position.)
    for seat, colour, want in ((0, R, [1.0, -1.0]), (1, B, [-1.0, 1.0])):
        board = {(0, 0): colour, (1, 0): colour}
        st = mk(board, to_move=seat)
        assert any_move(board, st.n, seat), "control: the winner CAN still move"
        assert G.is_terminal(st), "a wiped-out opponent ends it, whoever is to move"
        assert G.legal_moves(st) == []
        assert G.returns(st) == want

    # The RENDER CAPTION names the winner, and it is off the legality path, so
    # nothing else in this file would notice it naming the wrong one.  A single
    # swapped comparison there makes a finished board announce "Draw (2-0)" when
    # Red has won and "Red wins" when BLUE has won, while every other assertion
    # here, `validate` and conformance all still pass.  Pin it for both seats,
    # with the loser to move as well (that is the seat the real UI shows).
    for seat, colour, name, loser in ((0, R, "Red", "Blue"), (1, B, "Blue", "Red")):
        for to_move in (0, 1):
            cap = G.render(mk({(0, 0): colour, (1, 0): colour},
                              to_move=to_move))["caption"]
            assert cap.startswith(f"{name} wins"), (seat, to_move, cap)
            assert f"{loser} wiped out" in cap, (seat, to_move, cap)
            assert "Draw" not in cap, (seat, to_move, cap)

    # ...and that draw really is unreachable through apply_move: after any legal
    # move the survivors form exactly one group, so somebody can always move.
    # (test_termination_and_no_skipping asserts zero draws over ~450 games.)


# --------------------------------------------------------------------------- #
# seat symmetry                                                                #
# --------------------------------------------------------------------------- #

def swap(s):
    return CState(n=s.n, board={c: 1 - p for c, p in s.board.items()},
                  to_move=1 - s.to_move, ply=s.ply, last=s.last)


def test_seat_conjugation():
    """Swapping both colours and the side to move must conjugate everything:
    the same move list, the swapped resulting board, the reversed payoffs.
    A mutant that freezes or reverses one seat's army dies here."""
    rng = random.Random(31337)
    for n in (4, 5, 6):
        for gi in range(15):
            s = G.initial_state(options={"size": n})
            while not G.is_terminal(s):
                t = swap(s)
                assert G.is_terminal(t) == G.is_terminal(s)
                assert set(G.legal_moves(t)) == set(G.legal_moves(s))
                m = rng.choice(G.legal_moves(s))
                a, b = G.apply_move(s, m), G.apply_move(t, m)
                assert b.board == {c: 1 - p for c, p in a.board.items()}
                assert b.to_move == 1 - a.to_move
                assert G.returns(b) == list(reversed(G.returns(a)))
                s = a


# --------------------------------------------------------------------------- #
# persistence, purity, render                                                  #
# --------------------------------------------------------------------------- #

KEYS = {"n", "board", "to_move", "ply", "last"}


def test_serialize_roundtrip_and_purity():
    """Compare STATE OBJECTS, not serialized dicts: ``serialize(deserialize(d))
    == d`` cannot see a field ``serialize`` stops emitting."""
    rng = random.Random(1234)
    saw_last_none = saw_last_set = 0
    for n in SIZES:
        for gi in range(3):
            s = G.initial_state(options={"size": n})
            while True:
                d = G.serialize(s)
                assert set(d) == KEYS, set(d) ^ KEYS
                json.dumps(d)
                back = G.deserialize(d)
                assert back == s, (back, s)
                assert type(back.last) is type(s.last)
                if s.last is None:
                    saw_last_none += 1
                else:
                    assert all(isinstance(t, tuple) for t in back.last)
                    saw_last_set += 1
                # dropping ANY key must be loud, never silently re-defaulted
                for k in KEYS:
                    trimmed = {kk: vv for kk, vv in d.items() if kk != k}
                    try:
                        G.deserialize(trimmed)
                    except KeyError:
                        pass
                    else:
                        raise AssertionError(f"deserialize tolerated a missing {k!r}")
                if G.is_terminal(s):
                    break
                m = rng.choice(G.legal_moves(s))
                snapshot = G.serialize(s)
                t = G.apply_move(s, m)
                assert G.serialize(s) == snapshot, "apply_move mutated its input"
                assert t.board is not s.board
                s = t
    assert saw_last_none >= len(SIZES) and saw_last_set > 100


def test_render_every_size():
    """Board.jsx builds its clickable cells from board.width/height and joins
    pieces by cell id, so a piece outside the declared board is silently
    DROPPED.  Checked at every ply of a real game, for every size."""
    rng = random.Random(555)
    for n in SIZES:
        maxc = maxr = -1
        s = G.initial_state(options={"size": n})
        plies = 0
        while True:
            spec = G.render(s)
            board = spec["board"]
            assert board == {"type": "square", "width": n, "height": n}, board
            cells = set()
            for pc in spec["pieces"]:
                c, r = parse_cell(pc["cell"])
                assert 0 <= c < board["width"] and 0 <= r < board["height"], \
                    (n, pc, board)
                assert pc["owner"] == s.board[(c, r)], (pc, s.board[(c, r)])
                cells.add((c, r))
                maxc, maxr = max(maxc, c), max(maxr, r)
            assert cells == set(s.board), "render must show every checker exactly once"
            for h in spec["highlights"]:
                hc, hr = parse_cell(h["cell"])
                assert 0 <= hc < n and 0 <= hr < n
            assert isinstance(spec["caption"], str) and spec["caption"]
            json.dumps(spec)
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            plies += 1
        assert plies > 0
        # the far corner of the LARGEST file/rank is exercised after real moves,
        # not merely on the untouched starting array
        assert (maxc, maxr) == (n - 1, n - 1), (n, maxc, maxr)
        # highlights appear once a move has been made
        assert len(G.render(s)["highlights"]) == 2
        # ...and the caption of a terminal REACHED THROUGH PLAY names the right
        # winner (the hand-built pair in test_terminal_classification pins both
        # seats; this pins it on a real game too).
        ret, cap = G.returns(s), G.render(s)["caption"]
        winner = "Red" if ret[0] > ret[1] else ("Blue" if ret[1] > ret[0] else None)
        assert winner is not None, (n, ret)
        assert cap.startswith(f"{winner} wins"), (n, ret, cap)


def test_describe_move():
    s = G.initial_state(options={"size": 4})
    for m in G.legal_moves(s):
        text = G.describe_move(s, m)
        assert text.startswith("R "), text
        assert m.replace(">", "x") in text
    # The opening array is a strict checkerboard, so EVERY opening move is an
    # enemy capture -- there is no friendly capture until the pattern breaks.
    enemy = [m for m in G.legal_moves(s)
             if s.board[parse_cell(m.split(">")[1])] != s.to_move]
    assert len(enemy) == len(G.legal_moves(s)) == 24
    assert all("(own)" not in G.describe_move(s, m) for m in enemy)
    t = G.apply_move(s, enemy[0])
    assert G.describe_move(t, G.legal_moves(t)[0]).startswith("B ")

    # a friendly capture is labelled (Figure 2 has four of them)
    friendly = [m for m in G.legal_moves(FIG2)
                if FIG2.board[parse_cell(m.split(">")[1])] == FIG2.to_move]
    assert friendly and all("(own)" in G.describe_move(FIG2, m) for m in friendly)


def test_move_string_hygiene():
    """Every move is a two-cell path, so the web UI routes it to the board click
    handler (select a checker, click an adjacent occupied cell).  No move is a
    self-path, which would fire on the instinctive deselect click."""
    rng = random.Random(3)
    s = G.initial_state(options={"size": 6})
    while not G.is_terminal(s):
        for m in G.legal_moves(s):
            frm, to = m.split(">")
            assert frm != to
            assert parse_cell(frm) != parse_cell(to)
            assert cell_name(parse_cell(frm)) == frm
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))


def test_helpers():
    assert parse_cell("3,4") == (3, 4) and cell_name((3, 4)) == "3,4"
    assert sorted(neighbours((0, 0), 4)) == [(0, 1), (1, 0)]
    assert sorted(neighbours((1, 1), 4)) == [(0, 1), (1, 0), (1, 2), (2, 1)]
    assert len(ORTHO) == 4 and all(abs(a) + abs(b) == 1 for a, b in ORTHO)
    assert counts({(0, 0): R, (1, 0): R, (2, 0): B}) == (2, 1)
    assert group_count({}, 4) == 0
    assert group_count({(0, 0): R, (2, 2): B}, 4) == 2
    assert group_count({(0, 0): R, (1, 0): B}, 4) == 1, "groups mix colours"
    labels, k = components({(0, 0): R, (1, 0): B, (3, 3): R}, 4)
    assert k == 2 and labels[(0, 0)] == labels[(1, 0)] != labels[(3, 3)]
    # resolve: the capture plus enemy-only removal, in one step
    # B R B: Red steps right, and the blue left behind is detached and removed
    assert resolve({(0, 0): B, (1, 0): R, (2, 0): B}, 4, R, (1, 0), (2, 0)) == \
        {(2, 0): R}, "the detached enemy-only group goes"
    # ...but a group still touching Red's group stays
    assert resolve({(0, 0): R, (1, 0): B, (2, 0): B}, 4, R, (0, 0), (1, 0)) == \
        {(1, 0): R, (2, 0): B}, "an attached enemy checker survives"
    assert initial_board(2) == {(0, 1): R, (1, 1): B, (0, 0): B, (1, 0): R}


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"clusterfuss selftest: {len(tests)} checks passed")


if __name__ == "__main__":
    main()
