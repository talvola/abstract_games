"""Correctness anchors for Hex Shogi 91 (pure stdlib; run by tests/test_games.py).

Every expected value below was derived from a primary source and cross-checked
against a second one:

* the piece target sets and the promotion zone come from the designer's own 2000
  Zillions rules file (hexshogi91.zrf: its `(directions ...)` table, its
  `(zone (name promotion-zone) ...)` cell lists and its piece move macros) and
  agree with the prose on chessvariants.com;
* the opening array comes from the setup diagram on the rules page and from the
  Game Courier preset's `code` field (they agree exactly);
* the drop rules come from the family rules page and the ZRF's `no-support` /
  `no-check` / `not-back` / `not-back-two` macros.

The perft numbers are this implementation's own frozen values (it has been
compared move-for-move against a ZRF-derived oracle over 900+ positions).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                                    # noqa: E402
import games.hex_shogi_91.game as G                                     # noqa: E402

MAN, g = load_from_dir(Path(__file__).resolve().parent)
BLACK, WHITE = G.BLACK, G.WHITE

# `load_from_dir` imports game.py under a SYNTHETIC module name, so the module
# object backing `g` is NOT the one `import games.hex_shogi_91.game` produced.
# Reading module constants through either copy is equivalent, but PATCHING one
# (e.g. PLY_CAP, below) only takes effect on the copy the game actually runs.
GM = sys.modules[type(g).__module__]
assert GM is not None and GM.PLY_CAP == G.PLY_CAP


def nm(c):
    return G.cell_name(*c)


def sq(name):
    """'8b' -> (q, r)."""
    f, rank = int(name[:-1]), name[-1]
    r = G.RANK_LETTERS.index(rank) - 5
    return (6 - f - r, r)


def blank(pieces, to_move=BLACK, hands=None, promoted=()):
    """A position from {cell-name: (owner, letter)} -- for rule probes."""
    s = g.initial_state()
    s.board = {sq(k): v for k, v in pieces.items()}
    s.promoted = frozenset(sq(k) for k in promoted)
    s.hands = hands or {BLACK: {}, WHITE: {}}
    s.to_move = to_move
    s.ply = 0
    s.since_cap = 0
    s.key = g._poskey(s)
    s.reps = {s.key: 1}
    s.last = None
    return s


def targets(state, name):
    c = sq(name)
    pl, t = state.board[c]
    return sorted(nm(x) for x in g._piece_targets(
        state.board, c, pl, t, c in state.promoted))


def moves(state):
    return sorted(g.describe_move(state, m) for m in g.legal_moves(state))


def eq(got, want, what):
    assert got == want, f"{what}:\n  got  {got}\n  want {want}"


# --------------------------------------------------------------- 1. board
def test_board():
    cs = list(G.cells())
    eq(len(cs), 91, "board size")
    eq(sorted(nm(c) for c in cs if c[1] == -5), ["10a", "11a", "6a", "7a", "8a", "9a"],
       "rank a (6 cells, files 6-11)")
    eq(sorted(nm(c) for c in cs if c[1] == 5), ["1k", "2k", "3k", "4k", "5k", "6k"],
       "rank k (6 cells, files 1-6)")
    eq(len([c for c in cs if c[1] == 0]), 11, "rank f is 11 wide")
    # round-trip of the printed notation
    for c in cs:
        assert sq(nm(c)) == c, c
    # the six corners of the hexagon
    eq(sorted(nm(c) for c in cs
              if len([1 for d in G.ORTHO if not G.on_board(c[0] + d[0], c[1] + d[1])]) == 3),
       ["11a", "11f", "1f", "1k", "6a", "6k"], "corners")


# --------------------------------------------------------------- 2. setup
def test_setup():
    s = g.initial_state()
    got = {nm(c): ("bw"[p], t) for c, (p, t) in s.board.items()}
    want = {}
    # White (seat 1, top): rank a back row, rank b, nine pawns on rank d
    for f, t in zip(range(11, 5, -1), "LNGGNL"):
        want[f"{f}a"] = ("w", t)
    for f, t in zip(range(10, 5, -1), "RSKSB"):
        want[f"{f}b"] = ("w", t)
    for f in range(3, 12):
        want[f"{f}d"] = ("w", "P")
    # Black (seat 0, bottom): rank k back row, rank j, nine pawns on rank h
    for f, t in zip(range(6, 0, -1), "LNGGNL"):
        want[f"{f}k"] = ("b", t)
    for f, t in zip(range(6, 1, -1), "RSKSB"):
        want[f"{f}j"] = ("b", t)
    for f in range(1, 10):
        want[f"{f}h"] = ("b", "P")
    eq(got, want, "opening array")
    eq(len(s.board), 40, "piece count")
    eq(s.to_move, BLACK, "Black (sente) moves first")
    eq(s.hands, {BLACK: {}, WHITE: {}}, "empty hands")
    # the two lance pairs face each other down a straight orthogonal ray, and
    # the bishops share a diagonal -- the designer's stated setup constraints
    for a, b in (("6k", "6a"), ("1k", "11a")):
        d = (sq(b)[0] - sq(a)[0], sq(b)[1] - sq(a)[1])
        assert any(d[0] * o[1] == d[1] * o[0] for o in G.ORTHO), (a, b)
    d = (sq("6b")[0] - sq("2j")[0], sq("6b")[1] - sq("2j")[1])
    assert any(d[0] * o[1] == d[1] * o[0] for o in G.DIAG), "bishops share a diagonal"


# ----------------------------------------------------- 3. piece move sets
def test_piece_moves():
    """Every target set from the central hex 6f, per the ZRF direction table."""
    gold = ["5e", "5f", "5g", "6e", "6g", "7d", "7e", "7f", "8e"]
    cases = {
        # letter, promoted -> expected targets for BLACK from 6f
        ("P", False): ["6e", "7e"],                       # 2 orthogonally forward
        ("L", False): ["10b", "11a", "6a", "6b", "6c", "6d", "6e",
                       "7e", "8d", "9c"],                 # the 2 forward rays
        ("N", False): ["5d", "7c", "8c", "9d"],           # 4 forward leaps
        ("S", False): ["4g", "5e", "5h", "6e", "7d", "7e", "7g", "8e"],
        ("G", False): gold,
        ("K", False): ["4g", "5e", "5f", "5g", "5h", "6e", "6g",
                       "7d", "7e", "7f", "7g", "8e"],     # 12 neighbours
        ("P", True): gold, ("L", True): gold, ("N", True): gold, ("S", True): gold,
    }
    for (letter, prom), want in cases.items():
        s = blank({"6f": (BLACK, letter)}, promoted=("6f",) if prom else ())
        eq(targets(s, "6f"), sorted(want), f"black {'+' if prom else ''}{letter} from 6f")
    # sliders
    s = blank({"6f": (BLACK, "R")})
    eq(len(targets(s, "6f")), 30, "rook: 6 rays x 5")
    s = blank({"6f": (BLACK, "B")})
    bish = targets(s, "6f")
    eq(bish, ["10d", "2h", "4d", "4g", "4j", "5e", "5h", "7d", "7g", "8b", "8e", "8h"],
       "bishop from 6f")
    # colourbound: every bishop target keeps (q-r) mod 3
    for t in bish:
        assert (sq(t)[0] - sq(t)[1]) % 3 == 0, t
    s = blank({"6f": (BLACK, "R")}, promoted=("6f",))
    eq(len(targets(s, "6f")), 36, "dragon king = rook + 6 diagonal steps")
    s = blank({"6f": (BLACK, "B")}, promoted=("6f",))
    eq(len(targets(s, "6f")), 18, "dragon horse = bishop + 6 orthogonal steps")
    # White is the exact negation of Black
    for letter in "PLNSGKRB":
        b = blank({"6f": (BLACK, letter)})
        w = blank({"6f": (WHITE, letter)})
        eq(sorted(sq(t) for t in targets(w, "6f")),
           sorted((-q, -r) for q, r in (sq(t) for t in targets(b, "6f"))),
           f"white {letter} = negated black {letter}")


def test_knight_jumps():
    """The knight is a LEAPER: intervening pieces do not block it."""
    open_ = blank({"6f": (BLACK, "N")})
    ring = {"6f": (BLACK, "N")}
    for d in G.ORTHO + G.DIAG:
        c = (sq("6f")[0] + d[0], sq("6f")[1] + d[1])
        ring[nm(c)] = (WHITE, "G")
    eq(targets(blank(ring), "6f"), targets(open_, "6f"), "knight jumps the ring")


# ------------------------------------------------------- 4. promotion zone
def test_promotion_zone():
    zb = sorted(nm(c) for c in G.cells() if G._in_zone(BLACK, c[1]))
    zw = sorted(nm(c) for c in G.cells() if G._in_zone(WHITE, c[1]))
    eq(len(zb), 30, "Black's zone = 30 cells")
    eq(len(zw), 30, "White's zone = 30 cells")
    eq(sorted({c[-1] for c in zb}), ["a", "b", "c", "d"], "Black promotes on ranks a-d")
    eq(sorted({c[-1] for c in zw}), ["h", "i", "j", "k"], "White promotes on ranks h-k")


def test_promotion_options():
    # into the zone -> optional
    s = blank({"6e": (BLACK, "S"), "4k": (BLACK, "K"), "8a": (WHITE, "K")})
    got = [m for m in moves(s) if m.startswith("S6e-6d")]
    eq(sorted(got), ["S6e-6d", "S6e-6d+"], "silver entering the zone may promote")
    # entirely outside -> no promotion offered.  (NB a silver on rank f already
    # reaches rank d diagonally, so probe from rank h.)
    s = blank({"6h": (BLACK, "S"), "4k": (BLACK, "K"), "8a": (WHITE, "K")})
    assert not [m for m in moves(s) if m.endswith("+")], "no promotion outside the zone"
    # out of the zone -> still optional (origin in the zone counts)
    s = blank({"6d": (BLACK, "S"), "4k": (BLACK, "K"), "8a": (WHITE, "K")})
    got = [m for m in moves(s) if m.startswith("S6d-5f")]     # backward diagonal
    eq(sorted(got), ["S6d-5f", "S6d-5f+"], "silver leaving the zone may promote")
    # mandatory: pawn / lance on the last rank, knight on the last two
    s = blank({"7b": (BLACK, "P"), "4k": (BLACK, "K"), "1a": (WHITE, "K")})
    eq(sorted(m for m in moves(s) if m.startswith("P")), ["P7b-7a+", "P7b-8a+"],
       "pawn must promote on rank a (both forward cells are on rank a)")
    s = blank({"7b": (BLACK, "L"), "4k": (BLACK, "K"), "1a": (WHITE, "K")})
    eq(sorted(m for m in moves(s) if m.startswith("L")), ["L7b-7a+", "L7b-8a+"],
       "lance must promote on rank a")
    s = blank({"6d": (BLACK, "N"), "4k": (BLACK, "K"), "1a": (WHITE, "K")})
    eq(sorted(m for m in moves(s) if m.startswith("N")),
       ["N6d-5b+", "N6d-7a+", "N6d-8a+", "N6d-9b+"],
       "knight must promote on either of the last two ranks")
    s = blank({"6e": (BLACK, "N"), "4k": (BLACK, "K"), "1a": (WHITE, "K")})
    eq(sorted(m for m in moves(s) if m.startswith("N")),
       ["N6e-5c", "N6e-5c+", "N6e-7b+", "N6e-8b+", "N6e-9c", "N6e-9c+"],
       "knight to rank c is optional, to rank b mandatory")
    # a promoted piece never promotes again; a gold and a king never promote
    s = blank({"6c": (BLACK, "G"), "4k": (BLACK, "K"), "1a": (WHITE, "K")})
    assert not [m for m in moves(s) if m.endswith("+")], "gold does not promote"


# --------------------------------------------------------------- 5. drops
def test_drop_dead_piece():
    kings = {"4k": (BLACK, "K"), "8a": (WHITE, "K")}
    for L, banned in (("P", ["a"]), ("L", ["a"]), ("N", ["a", "b"])):
        s = blank(dict(kings), hands={BLACK: {L: 1}, WHITE: {}})
        cells = {m.split("*")[1] for m in moves(s) if "*" in m}
        assert not any(c[-1] in banned for c in cells), f"{L} dropped on rank {banned}"
        ok = [r for r in G.RANK_LETTERS if r not in banned]
        assert any(c[-1] == ok[0] for c in cells), f"{L} may be dropped on rank {ok[0]}"
    # a dropped piece is never promoted
    s = blank(dict(kings), hands={BLACK: {"P": 1}, WHITE: {}})
    s2 = g.apply_move(s, "P@" + ",".join(map(str, sq("6b"))))
    assert sq("6b") not in s2.promoted, "a drop never promotes"
    assert s2.board[sq("6b")] == (BLACK, "P")


def test_drop_pawn_support():
    """No nifu; instead: no pawn drop onto a cell defended by a friendly
    UNPROMOTED pawn (the ZRF's `no-support`)."""
    kings = {"4k": (BLACK, "K"), "8a": (WHITE, "K")}
    # a black pawn on 6f defends 6e and 7e
    s = blank(dict(kings, **{"6f": (BLACK, "P")}), hands={BLACK: {"P": 1}, WHITE: {}})
    cells = {m.split("*")[1] for m in moves(s) if "*" in m}
    assert "6e" not in cells and "7e" not in cells, "pawn-defended cells are barred"
    assert "6d" in cells and "5f" in cells, "other cells are fine"
    # ... but a promoted pawn (tokin) does NOT bar the drop
    s = blank(dict(kings, **{"6f": (BLACK, "P")}), hands={BLACK: {"P": 1}, WHITE: {}},
              promoted=("6f",))
    cells = {m.split("*")[1] for m in moves(s) if "*" in m}
    assert "6e" in cells and "7e" in cells, "a tokin does not defend for this rule"
    # ... nor does an ENEMY pawn
    s = blank(dict(kings, **{"6f": (WHITE, "P")}), hands={BLACK: {"P": 1}, WHITE: {}})
    cells = {m.split("*")[1] for m in moves(s) if "*" in m}
    assert "6g" in cells and "5g" in cells, "an enemy pawn does not bar the drop"
    # and the rule applies to pawns only
    s = blank(dict(kings, **{"6f": (BLACK, "P")}), hands={BLACK: {"L": 1}, WHITE: {}})
    cells = {m.split("*")[1] for m in moves(s) if "*" in m}
    assert "6e" in cells, "only pawn drops are restricted"


def test_drop_pawn_no_check():
    """A pawn drop may not give check AT ALL (stronger than Shogi's drop-mate
    rule). A black pawn on X checks a white king on X's forward neighbours."""
    kings = {"4k": (BLACK, "K"), "6e": (WHITE, "K")}
    s = blank(dict(kings), hands={BLACK: {"P": 1, "L": 1, "G": 1}, WHITE: {}})
    cells = {m.split("*")[1] for m in moves(s) if m.startswith("P*")}
    # 6f and 5f are the two cells from which a black pawn attacks 6e
    assert "6f" not in cells and "5f" not in cells, "pawn drop may not check"
    assert "7f" in cells and "6g" in cells, "a non-checking pawn drop is fine"
    lances = {m.split("*")[1] for m in moves(s) if m.startswith("L*")}
    assert "6f" in lances, "a LANCE drop may give check"
    golds = {m.split("*")[1] for m in moves(s) if m.startswith("G*")}
    assert "6f" in golds, "a GOLD drop may give check"


def test_drop_bookkeeping():
    """A drop must actually spend the piece, must resolve an existing check,
    and must NOT reset the no-capture counter."""
    kings = {"4k": (BLACK, "K"), "8a": (WHITE, "K")}

    # the hand shrinks; the input state is untouched; the letter goes at zero
    s = blank(dict(kings), hands={BLACK: {"P": 2}, WHITE: {}})
    s1 = g.apply_move(s, "P@" + ",".join(map(str, sq("6f"))))
    eq(s1.hands[BLACK], {"P": 1}, "a drop decrements the hand")
    eq(s.hands[BLACK], {"P": 2}, "apply_move leaves the input hand alone")
    s2 = g.apply_move(s1, [m for m in g.legal_moves(s1) if ">" in m][0])
    s3 = g.apply_move(s2, "P@" + ",".join(map(str, sq("5f"))))
    assert "P" not in s3.hands[BLACK], f"letter removed at zero: {s3.hands[BLACK]}"
    s4 = g.apply_move(s3, [m for m in g.legal_moves(s3) if ">" in m][0])
    assert not [m for m in g.legal_moves(s4) if "@" in m], "an empty hand offers no drops"

    # a drop while in check must resolve the check -- here only the four cells
    # between the checking Rook and the King will do.
    s = blank({"6f": (BLACK, "K"), "6a": (WHITE, "R"), "1k": (WHITE, "K")},
              hands={BLACK: {"G": 1}, WHITE: {}})
    assert g.in_check(s.board, s.promoted, BLACK), "Black is in check"
    eq(sorted(m.split("*")[1] for m in moves(s) if m.startswith("G*")),
       ["6b", "6c", "6d", "6e"], "only check-blocking drops are legal")

    # a drop is not a capture: the no-capture counter keeps running
    s = blank(dict(kings), hands={BLACK: {"G": 1}, WHITE: {}})
    s.since_cap = 41
    eq(g.apply_move(s, "G@0,0").since_cap, 42, "a drop does not reset since_cap")


def test_position_key_separates_hands_and_promotions():
    """The repetition key is board + PROMOTIONS + both hands + side to move.
    Two positions that differ only in what is held in hand, or only in whether
    a piece is promoted, are different positions."""
    base = {"4k": (BLACK, "K"), "8a": (WHITE, "K"), "6f": (BLACK, "S")}
    a = blank(dict(base))
    b = blank(dict(base), hands={BLACK: {"P": 1}, WHITE: {}})
    c = blank(dict(base), hands={WHITE: {"P": 1}, BLACK: {}})
    d = blank(dict(base), promoted=("6f",))
    keys = {"plain": g._poskey(a), "black holds P": g._poskey(b),
            "white holds P": g._poskey(c), "silver promoted": g._poskey(d)}
    eq(len(set(keys.values())), 4, f"all four keys differ: {keys}")
    # and the same board with the same hand IS the same key
    eq(g._poskey(blank(dict(base), hands={BLACK: {"P": 1}, WHITE: {}})),
       keys["black holds P"], "identical positions share a key")


def test_drop_and_capture_mechanics():
    """Captured pieces change side and revert to their unpromoted type."""
    s = blank({"6f": (BLACK, "R"), "6d": (WHITE, "B"), "4k": (BLACK, "K"),
               "8a": (WHITE, "K")}, promoted=("6d",))
    mv = f"{sq('6f')[0]},{sq('6f')[1]}>{sq('6d')[0]},{sq('6d')[1]}"
    assert mv in g.legal_moves(s) or mv + "=+" in g.legal_moves(s)
    s2 = g.apply_move(s, mv + "=+")
    eq(s2.hands[BLACK], {"B": 1}, "a captured dragon horse enters hand as a bishop")
    assert sq("6d") in s2.promoted, "the rook promoted on capture"
    eq(s2.board[sq("6d")], (BLACK, "R"), "still an R, flagged promoted")


# --------------------------------------------------------- 6. game endings
def test_checkmate_via_apply_move():
    """Reach mate by playing the move (never by hand-building the position)."""
    # White king cornered on 11a; Black rooks on 9b and 7b, Black king on 7a.
    # R9b-10b covers the last flight square and mates.
    s = blank({"11a": (WHITE, "K"), "9b": (BLACK, "R"), "7b": (BLACK, "R"),
               "7a": (BLACK, "K")}, to_move=BLACK)
    assert not g.in_check(s.board, s.promoted, WHITE), "not yet check"
    mv = f"{sq('9b')[0]},{sq('9b')[1]}>{sq('10b')[0]},{sq('10b')[1]}"
    assert mv in g.legal_moves(s), moves(s)
    s2 = g.apply_move(s, mv)
    assert g.in_check(s2.board, s2.promoted, WHITE), "White is in check"
    assert g.is_terminal(s2), "checkmate"
    eq(g.returns(s2), [1.0, -1.0], "the mated side loses")
    eq(g._draw_reason(s2), None, "mate is not a draw")


def test_checkmate_beats_every_draw_counter():
    """A mating move is NOT nullified by a draw counter firing on the same ply.

    Checkmate ends the game immediately (the designer's ZRF and Game Courier
    preset both score it unconditionally; the counters come from the prose
    rules page), so a mate delivered on the 100th quiet ply, on a third
    repetition, or on the ply cap is still a win -- never 0-0.
    """
    pos = {"11a": (WHITE, "K"), "9b": (BLACK, "R"), "7b": (BLACK, "R"),
           "7a": (BLACK, "K")}
    mv = f"{sq('9b')[0]},{sq('9b')[1]}>{sq('10b')[0]},{sq('10b')[1]}"

    # (a) the plain mate, for reference
    s = g.apply_move(blank(dict(pos)), mv)
    eq(g.returns(s), [1.0, -1.0], "the plain mate is a win")

    # (b) the same mate landing exactly on the no-capture limit
    st = blank(dict(pos))
    st.since_cap = G.NO_CAPTURE_PLIES - 1
    s = g.apply_move(st, mv)
    eq(s.since_cap, G.NO_CAPTURE_PLIES, "the counter did fire")
    eq(g._draw_reason(s), None, "checkmate outranks the 50-turn counter")
    assert g.is_terminal(s)
    eq(g.returns(s), [1.0, -1.0], "mate on the 100th quiet ply is still a win")
    assert "checkmate" in g.render(s)["caption"], g.render(s)["caption"]

    # (c) the same mate landing on the ply cap
    real = GM.PLY_CAP
    try:
        GM.PLY_CAP = 1
        s = g.apply_move(blank(dict(pos)), mv)
        eq(g._draw_reason(s), None, "checkmate outranks the ply cap")
        eq(g.returns(s), [1.0, -1.0], "mate on the cap ply is still a win")
    finally:
        GM.PLY_CAP = real

    # (d) the same mate on a position that has already occurred twice
    st = blank(dict(pos))
    after = g.apply_move(st, mv)
    st.reps = dict(st.reps)
    st.reps[after.key] = G.REP_LIMIT - 1
    s = g.apply_move(st, mv)
    eq(s.reps[s.key], G.REP_LIMIT, "the repetition counter did fire")
    eq(g._draw_reason(s), None, "checkmate outranks threefold repetition")
    eq(g.returns(s), [1.0, -1.0], "mate on a third repetition is still a win")

    # ... but a STALEMATE on a fired counter stays a draw either way
    st = blank({"6j": (BLACK, "K"), "4j": (WHITE, "K"), "9h": (WHITE, "R"),
                "8g": (WHITE, "B")}, to_move=BLACK)
    st.since_cap = G.NO_CAPTURE_PLIES
    eq(g.returns(st), [0.0, 0.0], "stalemate needs no special case")


def test_stalemate_is_a_draw():
    """Hex Shogi's own rules page: 'Stalemate is a draw.' (The Game Courier
    preset scores it as a win for the stalemating side -- see rules.md.)"""
    s = blank({"6j": (BLACK, "K"), "4j": (WHITE, "K"),
               "9h": (WHITE, "R"), "8g": (WHITE, "B")}, to_move=BLACK)
    assert not g.in_check(s.board, s.promoted, BLACK), "not in check"
    eq(g.legal_moves(s), [], "no legal move")
    assert g.is_terminal(s)
    eq(g.returns(s), [0.0, 0.0], "stalemate is a draw")


def test_repetition_and_no_capture_draws():
    kings = {"4k": (BLACK, "K"), "8a": (WHITE, "K"), "1f": (BLACK, "G"),
             "11f": (WHITE, "G")}
    s = blank(dict(kings))
    shuffle = ["4k>4j", "8a>8b", "4j>4k", "8b>8a"]      # a 4-ply cycle
    cyc = [f"{sq(a)[0]},{sq(a)[1]}>{sq(b)[0]},{sq(b)[1]}"
           for a, b in (m.split(">") for m in shuffle)]
    ply = 0
    while not g.is_terminal(s):
        s = g.apply_move(s, cyc[ply % 4])
        ply += 1
        assert ply < 60, "repetition draw never fired"
    eq(g._draw_reason(s), "threefold repetition", "threefold repetition draws")
    eq(g.returns(s), [0.0, 0.0], "a repetition draw is 0-0")
    assert ply == 8, f"third occurrence after 8 plies, got {ply}"
    # no-capture rule: 50 turns each side = 100 plies without a capture
    eq(G.NO_CAPTURE_PLIES, 100, "counted in plies (50 turns each side)")
    s = blank({"6f": (BLACK, "R"), "6d": (WHITE, "P"), "4k": (BLACK, "K"),
               "8a": (WHITE, "K")})
    s.since_cap = G.NO_CAPTURE_PLIES - 1
    quiet = f"{sq('6f')[0]},{sq('6f')[1]}>{sq('5f')[0]},{sq('5f')[1]}"
    grab = f"{sq('6f')[0]},{sq('6f')[1]}>{sq('6d')[0]},{sq('6d')[1]}"
    after_quiet = g.apply_move(s, quiet)
    eq(after_quiet.since_cap, 100, "a quiet move advances the counter")
    eq(g._draw_reason(after_quiet), "50 turns without a capture", "the no-capture draw")
    eq(g.returns(after_quiet), [0.0, 0.0], "and it is a draw")
    after_grab = g.apply_move(s, grab)
    eq(after_grab.since_cap, 0, "a capture resets the counter")
    eq(g._draw_reason(after_grab), None, "no draw after a capture")


def test_ply_cap_is_not_outcome_bearing():
    """The hard cap is a guard against a pathological loop, not a rule.

    It sits FAR outside the measured distribution: over 300 uniform-random games
    with the cap disabled the longest was 10,561 plies (median 305), and the
    empirical tail decays by ~0.67 per further 500 plies, so reaching 50,000 has
    probability ~1e-18. Here we show directly that replaying fixed-seed random
    games with the cap effectively disabled gives the SAME length, result and
    reason -- and that each finishes an order of magnitude short of the cap.
    (For a drop game no finite cap is *provably* outcome-neutral under uniform-
    random play; the honest claim is that this one is nowhere near firing.)
    """
    assert G.PLY_CAP >= 50000, "the cap must clear the measured tail with margin"
    assert G.PLY_CAP > 4 * 10561, "at least 4x the longest game ever observed"
    real = GM.PLY_CAP
    try:
        # First prove that patching GM.PLY_CAP really reaches the running game
        # -- patching the `import games...` copy does NOT (see GM, above), which
        # would make the loop below compare a run with itself.
        GM.PLY_CAP = 1
        s = g.apply_move(g.initial_state(), g.legal_moves(g.initial_state())[0])
        eq(g._draw_reason(s), "move limit", "the cap patch reaches the live module")
        GM.PLY_CAP = real
        for seed in (1, 2, 3, 5, 7, 11):
            out = []
            for cap in (real, 10 ** 9):
                GM.PLY_CAP = cap
                rng = random.Random(seed)
                s = g.initial_state()
                n = 0
                while not g.is_terminal(s):
                    s = g.apply_move(s, rng.choice(g.legal_moves(s)))
                    n += 1
                out.append((n, tuple(g.returns(s)), g._draw_reason(s)))
            eq(out[0], out[1], f"seed {seed}: outcome depends on the ply cap")
            assert out[0][2] != "move limit", f"seed {seed} hit the cap"
            assert out[0][0] < real // 10, \
                f"seed {seed} ran {out[0][0]} plies -- too close to the cap"
    finally:
        GM.PLY_CAP = real


def test_manifest_random_ply_budget():
    """The conformance harness is told about the heavy random tail through the
    manifest instead of the game shrinking its own backstop to fit."""
    budget = int(MAN.get("max_random_plies", 3000))
    assert budget > 10561, "must exceed the longest random game measured (10561)"
    assert budget <= G.PLY_CAP, "the game's own backstop still bounds every game"


# ---------------------------------------------------------------- 7. perft
def test_perft():
    """Frozen node counts from the opening position (drops appear from depth 3
    onwards, once a capture has happened)."""
    def perft(s, d):
        ms = g.legal_moves(s)
        if d == 1:
            return len(ms)
        return sum(perft(g.apply_move(s, m), d - 1) for m in ms)

    s = g.initial_state()
    for depth, want in ((1, 45), (2, 2024), (3, 92922)):
        eq(perft(s, depth), want, f"perft({depth})")


# ------------------------------------------------------------ 8. plumbing
def test_serialisation_and_notation():
    s = g.initial_state()
    s2 = g.apply_move(s, g.legal_moves(s)[0])
    d = g.serialize(s2)
    assert g.serialize(g.deserialize(d)) == d, "serialize round-trip"
    import json
    json.dumps(d)
    # notation uses the printed file/rank labels
    eq(G.cell_name(*sq("8b")), "8b", "cell name round-trip")
    s3 = blank({"6f": (BLACK, "R"), "6d": (WHITE, "P"), "4k": (BLACK, "K"),
                "8a": (WHITE, "K")})
    mv = f"{sq('6f')[0]},{sq('6f')[1]}>{sq('6d')[0]},{sq('6d')[1]}"
    eq(g.describe_move(s3, mv), "R6fx6d", "capture notation")
    eq(g.describe_move(s3, mv + "=+"), "R6fx6d+", "promotion notation")
    eq(g.describe_move(s3, "P@0,0"), "P*6f", "drop notation")


def test_render():
    s = g.initial_state()
    spec = g.render(s)
    eq(spec["board"]["type"], "hex", "hex board")
    eq(spec["board"]["shape"], "hexagon", "hexhex")
    eq(spec["board"]["size"], 6, "side 6")
    assert "orientation" not in spec["board"], \
        "pointy-top (hexes stand on a corner => horizontal ranks) is the default"
    eq(len(spec["board"]["tints"]), 91, "three-colour tinting")
    eq(len(spec["pieces"]), 40, "40 pieces")
    eq(sorted(spec["reserve"]), ["0", "1"], "per-seat reserve trays")
    import json
    json.dumps(spec)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"hex_shogi_91 selftest: {len(tests)} checks passed")


if __name__ == "__main__":
    main()
