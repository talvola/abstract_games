"""Slyde -- correctness anchors.  Pure stdlib (only `agp` + this package).

The anchors, strongest first:

  1. Kanare Abstract's GROUPS figure (Slyde_EN.pdf, 2024-06-13), transcribed
     from the embedded raster by pixel classification.  It is SELF-VALIDATING:
     the figure prints a size beside EVERY group, and both colours' printed
     sizes sum to 32 = 64/2, which is only possible if the board is 8x8 and no
     group was left unlabelled.  The figure's PREMISES are asserted, not just
     its outcome, and its DISCRIMINATING POWER is measured against an
     enumerated list of wrong readings -- the caption alone kills only 1 of 5,
     the printed label SET kills all 5.
  2. An exhaustive solve of the smallest shipped board (4x4, anti-mirroring
     off): every reachable state, the exact game value, and the reachability of
     an exact TIE.  ~60s; this is the termination + drawlessness anchor.
  3. The designer's published game-length number ("about 0.25-0.35 the size of
     the board ... an 8x8 board ... should last 16-23 moves each"), measured.
  4. The termination monovariant, checked ply by ply on real play.
  5. The cascading tiebreak on constructed inputs, including the exact case
     that the AbstractPlay oracle gets wrong (singletons compared one by one).
  6. serialize/deserialize compared as STATE OBJECTS across whole games.
  7. render() bounds for EVERY shipped board size, from a position reached
     through apply_move with pieces in the FAR CORNERS.
  8. Areas a differential structurally cannot cover: the anti-mirroring rule's
     "except on the first move" clause, and the padding in compare_scores
     (proved VACUOUS rather than trusted).

Run:  cd engine && PYTHONPATH=. python3 games/slyde/selftest.py
"""
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from games.slyde.game import (  # noqa: E402
    BLACK, CAP_RECYCLES, DEFAULT_SIZE, SEAT_NAMES, SIZES, WHITE, Slyde, SState,
    algebraic, cell_name, compare_scores, group_sizes, idx, is_symmetric,
    neighbours, parse_cell, ply_cap,
)

G = Slyde()
OK = []


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: FAILED {detail}")
    OK.append(name)


def play_random(size, anti="on", seed=0, stop=None):
    rng = random.Random(seed)
    s = G.initial_state(options={"size": size, "anti_mirror": anti})
    while not G.is_terminal(s):
        if stop and stop(s):
            return s
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    return s


# ===========================================================================
# 0. Geometry and the module's own vocabulary
# ===========================================================================
check("cell_name/parse_cell round-trip",
      all(parse_cell(cell_name(c, r)) == (c, r) for c in range(12) for r in range(12)))
check("idx is row-major and matches cell_name",
      all(idx(c, r, 12) == r * 12 + c for c in range(12) for r in range(12)))
check("algebraic follows the sheet's file-letter/rank style",
      algebraic(0, 0) == "a1" and algebraic(5, 3) == "f4" and algebraic(11, 11) == "l12")

# Adjacency is ORTHOGONAL only -- both sheets say so explicitly (MindSports
# "orthogonal connectivity", Kanare "connected ... vertically and horizontally"
# and "slide a single tile horizontally or vertically").
_n = 8
check("neighbours: interior cell has exactly 4, all orthogonal",
      set(neighbours(idx(3, 3, _n), _n)) ==
      {idx(2, 3, _n), idx(4, 3, _n), idx(3, 2, _n), idx(3, 4, _n)})
check("neighbours: corner has 2, edge has 3",
      len(neighbours(idx(0, 0, _n), _n)) == 2 and len(neighbours(idx(0, 3, _n), _n)) == 3)
check("neighbours excludes all four diagonals",
      all(idx(c, r, _n) not in neighbours(idx(3, 3, _n), _n)
          for c, r in ((2, 2), (2, 4), (4, 2), (4, 4))))
check("neighbours is symmetric over the whole board",
      all(i in neighbours(j, _n) for i in range(_n * _n) for j in neighbours(i, _n)))

# ===========================================================================
# 1. Setup, seats, and the opening move count
# ===========================================================================
s0 = G.initial_state()
check("default board is 12x12 (MindSports: 'a full 12x12 board')",
      s0.size == DEFAULT_SIZE == 12 and len(s0.colour) == 144)
check("the board starts FULL and every piece is MOBILE",
      len(s0.colour) == 144 and set(s0.fixed) == {0})
check("setup is a checkerboard",
      all(s0.colour[idx(c, r, 12)] == (c + r) % 2 for c in range(12) for r in range(12)))
check("each side owns exactly half the pieces",
      s0.colour.count(WHITE) == s0.colour.count(BLACK) == 72)
# GROUND TRUTH OUTSIDE THE ENGINE: MindSports "White begins"; Kanare "The White
# player moves first, then turns alternate."  Seat 0 must therefore be White.
check("White is seat 0 and moves first",
      SEAT_NAMES == ("White", "Black") and G.current_player(s0) == WHITE == 0)
check("initial caption names White as the mover",
      G.render(s0)["caption"].startswith("White to move"))
# 2*n*(n-1) orthogonally adjacent pairs, every one of them a white/black pair
# with both pieces mobile.  264 at 12x12 -- the published opening count.
for n in SIZES:
    st = G.initial_state(options={"size": n})
    check(f"opening move count at {n}x{n} == 2*n*(n-1)",
          len(G.legal_moves(st)) == 2 * n * (n - 1),
          f"{len(G.legal_moves(st))} != {2*n*(n-1)}")
check("opening move count at 12x12 is 264 (matches the AbstractPlay oracle)",
      len(G.legal_moves(s0)) == 264)

# ===========================================================================
# 2. The move: swap, and the MOVER's piece freezes
# ===========================================================================
m = "5,5>5,6"
check("that opening move is legal", m in G.legal_moves(s0))
s1 = G.apply_move(s0, m)
i_from, i_to = idx(5, 5, 12), idx(5, 6, 12)
check("apply_move does not mutate the input state",
      s0.fixed[i_to] == 0 and s0.colour[i_from] == WHITE and s0.ply == 0)
check("the two pieces exchange squares",
      s1.colour[i_from] == BLACK and s1.colour[i_to] == WHITE)
check("the SWAPPING player's own piece becomes fixed", s1.fixed[i_to] == 1)
check("the opponent's piece stays MOBILE", s1.fixed[i_from] == 0)
check("exactly one piece is fixed after one ply", sum(s1.fixed) == 1)
check("turn passes to Black", s1.to_move == BLACK)
check("piece counts are unchanged by a swap",
      s1.colour.count(WHITE) == s1.colour.count(BLACK) == 72)
check("a fixed piece can never be moved again (not a source and not a target)",
      all(idx(5, 6, 12) not in (idx(*parse_cell(a), 12), idx(*parse_cell(b), 12))
          for a, b in (mv.split(">") for mv in G.legal_moves(s1))))
# You may only move your OWN mobile piece, onto an ENEMY mobile piece.
for mv in G.legal_moves(s1):
    a, b = mv.split(">")
    if a == b:
        continue
    ia, ib = idx(*parse_cell(a), 12), idx(*parse_cell(b), 12)
    assert s1.colour[ia] == s1.to_move and s1.colour[ib] != s1.to_move
    assert not s1.fixed[ia] and not s1.fixed[ib]
    assert ib in neighbours(ia, 12)
OK.append("every generated swap is own-mobile -> adjacent enemy-mobile")

# THE LEMMA THAT MAKES THE END-OF-GAME WORDING UNAMBIGUOUS.  The sheets differ
# in phrasing -- Kanare "the game ends when no more TILES CAN BE MOVED" (and
# "passing is not allowed"), MindSports "when no more moves can be made" -- but
# the swap relation is SYMMETRIC: a mobile white piece adjacent to a mobile
# black piece is a legal move for BOTH players.  So "the player to move is
# stuck" and "nobody can move" coincide and the ambiguity is vacuous.
def swaps_for(s, seat):
    return {(i, j) for i in range(s.size * s.size)
            if s.colour[i] == seat and not s.fixed[i]
            for j in neighbours(i, s.size)
            if s.colour[j] != seat and not s.fixed[j]}


_sym_checked = 0
for seed in range(30):
    rng = random.Random(1000 + seed)
    s = G.initial_state(options={"size": 6})
    while True:
        w, b = swaps_for(s, WHITE), swaps_for(s, BLACK)
        assert (len(w) > 0) == (len(b) > 0), "one side stuck while the other is not"
        assert {(i, j) for i, j in w} == {(j, i) for i, j in b}
        _sym_checked += 1
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
check("LEMMA: swap availability is symmetric, so 'mover stuck' == 'nobody can move'",
      _sym_checked > 400, f"only {_sym_checked} positions")

# ===========================================================================
# 3. Kanare's GROUPS figure -- the primary scoring anchor
# ===========================================================================
# Transcribed from Slyde_EN.pdf's embedded GROUPS raster (image18.png) by
# classifying each cell as tile/empty.  'B' = black tile, '.' = white empty.
FIGURE = ["....B..B",
          "BB.BBB.B",
          "B.B.B.BB",
          ".....B..",
          "B.B...B.",
          "B.BBBBBB",
          "BBB.B.B.",
          ".BB...B."]
FIG_COLOUR = tuple(BLACK if ch == "B" else WHITE for row in FIGURE for ch in row)
# The sizes printed on the figure, one circle per group.
FIG_BLACK = [18, 5, 4, 3, 1, 1]
FIG_WHITE = [12, 5, 5, 3, 3, 2, 1, 1]

# --- the figure's PREMISES (a mis-transcription breaks these first) ---
check("figure premise: the diagram is 8x8", len(FIG_COLOUR) == 64)
check("figure premise: the printed sizes sum to 32 for EACH colour, i.e. every "
      "group is labelled and the two armies are equal",
      sum(FIG_BLACK) == sum(FIG_WHITE) == 32)
check("figure premise: my transcription has 32 tiles and 32 empty cells",
      FIG_COLOUR.count(BLACK) == FIG_COLOUR.count(WHITE) == 32)
check("figure premise: the transcription is a REACHABLE Slyde position "
      "(equal colour counts is the invariant a swap preserves)",
      FIG_COLOUR.count(BLACK) == 64 // 2)

# --- the figure's OUTCOME ---
fig_b = group_sizes(FIG_COLOUR, 8, BLACK)
fig_w = group_sizes(FIG_COLOUR, 8, WHITE)
check("figure: every printed BLACK group size is reproduced", fig_b == FIG_BLACK, str(fig_b))
check("figure: every printed WHITE group size is reproduced", fig_w == FIG_WHITE, str(fig_w))
check("figure: TWO separate size-1 groups for each colour, not one lump of 2 "
      "('an isolated tile/cell is also considered a group of size 1')",
      fig_b.count(1) == 2 and fig_w.count(1) == 2)
# The rulebook's caption: "the black player wins with a group of size 18".
# This pins SEAT NAMING to ground truth OUTSIDE the engine -- the owner of the
# figure's printed 18-group -- rather than to the engine's own naming.
check("figure caption: BLACK (the owner of the printed 18-group) wins",
      compare_scores(fig_w, fig_b) < 0 and max(fig_b) == 18 and max(fig_w) == 12)

# --- MEASURED discriminating power (what this anchor CANNOT catch) ---
def _diag_groups(colour, size, player):
    seen = [False] * len(colour)
    out = []
    for s_ in range(len(colour)):
        if colour[s_] != player or seen[s_]:
            continue
        seen[s_] = True
        st, n = [s_], 0
        while st:
            i = st.pop()
            n += 1
            c, r = i % size, i // size
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    if dc or dr:
                        nc, nr = c + dc, r + dr
                        if 0 <= nc < size and 0 <= nr < size:
                            j = nr * size + nc
                            if colour[j] == player and not seen[j]:
                                seen[j] = True
                                st.append(j)
        out.append(n)
    return sorted(out, reverse=True)


_agg = lambda g: [x for x in g if x > 1] + [sum(1 for x in g if x == 1)]
WRONG_READINGS = {
    "8-way connectivity": (_diag_groups(FIG_COLOUR, 8, WHITE), _diag_groups(FIG_COLOUR, 8, BLACK)),
    "singletons aggregated (the oracle's bug)": (_agg(fig_w), _agg(fig_b)),
    "largest group only": (fig_w[:1], fig_b[:1]),
    "colours swapped": (fig_b, fig_w),
    "smallest group wins": (fig_w[::-1], fig_b[::-1]),
}
killed_by_labels = sum(1 for vw, vb in WRONG_READINGS.values() if (vw, vb) != (fig_w, fig_b))
killed_by_caption = sum(1 for vw, vb in WRONG_READINGS.values() if not compare_scores(vw, vb) < 0)
check("figure: its printed LABEL SET kills all 5 enumerated wrong readings",
      killed_by_labels == 5, f"{killed_by_labels}/5")
check("figure: its CAPTION alone kills only 1 of 5 -- the gap the constructed "
      "tiebreak positions below exist to close",
      killed_by_caption == 1, f"{killed_by_caption}/5")

# ===========================================================================
# 4. The cascading tiebreak
# ===========================================================================
check("tiebreak: bigger largest group wins outright",
      compare_scores([9, 1], [8, 2]) > 0)
check("tiebreak: equal largest -> compare second",
      compare_scores([8, 3, 1], [8, 2, 2]) > 0 and compare_scores([8, 2, 2], [8, 3, 1]) < 0)
check("tiebreak: cascades to the third and fourth group",
      compare_scores([8, 3, 2, 1], [8, 3, 1, 2]) > 0 and
      compare_scores([6, 4, 2, 2, 1], [6, 4, 2, 1, 2]) > 0)
check("tiebreak: identical partitions are an honest DRAW",
      compare_scores([8, 3, 2, 1], [8, 3, 2, 1]) == 0 and compare_scores([], []) == 0)
# THE CASE THE ABSTRACTPLAY ORACLE GETS WRONG.  Kanare: "If there are multiple
# groups of the same color and size, they are taken as separate groups for
# comparison."  Four singletons are 1,1,1,1 -- NOT a group of size 4.
check("tiebreak: singletons compare one by one, never as a count",
      compare_scores([4, 1, 1, 1, 1], [4, 2, 1, 1]) < 0)
check("tiebreak: a lone singleton loses to a pair at the same rank",
      compare_scores([5, 1, 1, 1], [5, 2, 1]) < 0 and
      compare_scores([11, 3, 2, 1, 1], [11, 3, 1, 1, 1, 1]) > 0)

# The padding in compare_scores is VACUOUS and only defensive: both armies
# always hold exactly size*size/2 pieces, so two sorted lists with a common
# prefix and different lengths would have different sums.  Proved here rather
# than trusted.
_pad_used = 0
for size in (4, 6):
    for seed in range(120):
        s = play_random(size, "on", seed)
        w, b = G.scores(s)
        assert sum(w) == sum(b) == size * size // 2
        n = min(len(w), len(b))
        if w[:n] == b[:n] and len(w) != len(b):
            _pad_used += 1
check("compare_scores' 0-padding is VACUOUS on real positions (equal army "
      "sizes make a common prefix with unequal lengths impossible)",
      _pad_used == 0, f"padding decided {_pad_used} positions")
# The invariant the vacuity argument rests on, checked at EVERY ply of real
# games at every shipped size -- not merely at the opening.
_plies = 0
for size in SIZES:
    rng = random.Random(size * 31)
    s = G.initial_state(options={"size": size})
    while True:
        assert s.colour.count(WHITE) == s.colour.count(BLACK) == size * size // 2, \
            f"army sizes drifted at ply {s.ply}"
        _plies += 1
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
check("both armies hold exactly cells/2 pieces at EVERY ply of a full game, at "
      "every shipped size", _plies > 200, f"only {_plies} plies")

# An exact tie really is reachable -- it is not a theoretical nicety.
_ties = [seed for seed in range(400) if G.returns(play_random(4, "on", seed))[0] == 0]
check("an exact tie (winner=None, returns [0,0]) is REACHABLE under random play",
      len(_ties) > 10, f"only {len(_ties)}/400")
_tie_state = play_random(4, "on", _ties[0])
check("a drawn game returns [0,0] and names no winner",
      G.returns(_tie_state) == [0.0, 0.0] and G.winner(_tie_state) is None)
check("a drawn game's caption says Draw", G.render(_tie_state)["caption"].startswith("Draw"))
check("a drawn game really has identical partitions "
      "('a draw is only possible when both sets are partitioned in the same way')",
      G.scores(_tie_state)[0] == G.scores(_tie_state)[1])

# returns() is well-formed and zero-sum at every terminal.
for size in (4, 6, 8):
    for seed in range(25):
        s = play_random(size, "on", seed)
        r = G.returns(s)
        assert len(r) == 2 and abs(r[0] + r[1]) < 1e-9 and all(abs(x) <= 1 for x in r)
        w, b = G.scores(s)
        assert (r[0] > 0) == (compare_scores(w, b) > 0)
OK.append("returns() is 2 payoffs, zero-sum, and agrees with the cascade")

# ===========================================================================
# 5. The anti-mirroring rule
# ===========================================================================
# PREMISE: the opening position IS symmetric under both mirrors -- which is
# exactly why the "except on the first move" clause matters.  Without it White
# would open with 144 extra free state changes.
check("PREMISE: the opening checkerboard is symmetric under BOTH mirrors",
      is_symmetric(s0))
check("...yet NO state change is offered on move 1 (BGG: 'except on the first "
      "move'); the opening list is exactly the 264 swaps",
      len(G.legal_moves(s0)) == 264 and all(a != b for a, b in
                                            (m.split(">") for m in G.legal_moves(s0))))
check("with anti_mirror off the opening is unchanged",
      len(G.legal_moves(G.initial_state(options={"anti_mirror": "off"}))) == 264)

# --- THE DESIGNER'S OWN WORKED EXAMPLE --------------------------------------
# MindSports, verbatim and unchanged in every Wayback capture from 2020-08-05
# to 2026-04-20: "In the diagram White opened with f3-f4 and Black replied with
# the symmetrical f10-f9.  White then played k6-j6 and Black replied with the
# symmetrical k7-j7. ... So here White instead of swapping could say fix one of
# the pieces of his 4-group, or 'unfix' f9."
#
# This is the ONLY primary-source artefact for the anti-mirroring rule, and the
# artefact rules.md names as adjudicating "what counts as a symmetric position"
# -- so it is replayed here move for move rather than merely cited.
#
# The sheet's diagram holds White on the parity where f3 is a White cell; this
# package uses the other parity, which the LEMMA below proves is the same game
# under a left-right mirror.  The example is therefore replayed through that
# mirror (file x -> file 11-x, ranks unchanged).  The control at the end shows
# the mirror is load-bearing and not a fudge.
def _sheet(cell):
    """A cell named in the sheet's coordinates -> our mirrored cell id."""
    return f"{11 - (ord(cell[0]) - ord('a'))},{int(cell[1:]) - 1}"


_ex = G.initial_state()
for _a, _b in (("f3", "f4"), ("f10", "f9"), ("k6", "j6"), ("k7", "j7")):
    _mv = f"{_sheet(_a)}>{_sheet(_b)}"
    assert _mv in G.legal_moves(_ex), \
        f"the sheet's move {_a}-{_b} is not legal at ply {_ex.ply}"
    _ex = G.apply_move(_ex, _mv)
check("WORKED EXAMPLE: all four of the sheet's moves are legal, in order",
      _ex.ply == 4)
check("WORKED EXAMPLE: it reaches a SYMMETRIC position with White to move, "
      "which is what 'the next player to move can choose to change the state' "
      "needs", is_symmetric(_ex) and _ex.to_move == WHITE)
check("WORKED EXAMPLE: the mirror is the TOP-BOTTOM one the sheet names, not "
      "merely some symmetry",
      all(_ex.colour[r * 12 + c] != _ex.colour[(11 - r) * 12 + c] and
          _ex.fixed[r * 12 + c] == _ex.fixed[(11 - r) * 12 + c]
          for r in range(12) for c in range(12)))
_ex_tog = [m for m in G.legal_moves(_ex) if m.split(">")[0] == m.split(">")[1]]
check("WORKED EXAMPLE: a state change is offered on all 144 cells",
      len(_ex_tog) == 144)
_f9 = _sheet("f9")
_f9i = idx(*parse_cell(_f9), 12)
check("WORKED EXAMPLE: the sheet's \"'unfix' f9\" is offered, and f9 really "
      "holds a FIXED BLACK piece -- so a state change reaches an ENEMY piece "
      "and an ALREADY-FIXED one, exactly as 'any pawn regardless of color' says",
      f"{_f9}>{_f9}" in _ex_tog and _ex.colour[_f9i] == BLACK
      and _ex.fixed[_f9i] == 1)
check("WORKED EXAMPLE: describe_move calls that move an unfix",
      G.describe_move(_ex, f"{_f9}>{_f9}") == f"unfix {algebraic(*parse_cell(_f9))}")
check("WORKED EXAMPLE: the sheet's other option, 'fix one of the pieces of his "
      "4-group' -- White does have a group of exactly 4 here",
      4 in G.scores(_ex)[WHITE])
check("WORKED EXAMPLE control: the sheet's UNMIRRORED f3-f4 is NOT legal in "
      "this package's parity, so the mirror above is doing real work and the "
      "replay is not passing by accident",
      f"{ord('f') - ord('a')},2>{ord('f') - ord('a')},3" not in G.legal_moves(G.initial_state()))


def find_symmetric(size, seeds=600):
    for seed in range(seeds):
        rng = random.Random(seed)
        s = G.initial_state(options={"size": size, "anti_mirror": "on"})
        while not G.is_terminal(s):
            if s.ply > 0 and is_symmetric(s):
                return s
            s = G.apply_move(s, rng.choice(sorted(G.legal_moves(s))))
    return None


sym = find_symmetric(4)
check("a symmetric position after move 1 is REACHABLE under random play", sym is not None)
tog = [m for m in G.legal_moves(sym) if m.split(">")[0] == m.split(">")[1]]
check("in a symmetric position a state change is offered for EVERY cell, "
      "'any pawn regardless of color'", len(tog) == sym.size * sym.size)
_any_fixed = [m for m in tog if sym.fixed[idx(*parse_cell(m.split(">")[0]), sym.size)]]
check("...including already-FIXED pieces ('mobile to fixed OR VICE VERSA')",
      len(_any_fixed) > 0)
_t = tog[0]
_ti = idx(*parse_cell(_t.split(">")[0]), sym.size)
after = G.apply_move(sym, _t)
check("a state change flips exactly that one fixed bit and moves NO piece",
      after.colour == sym.colour and after.fixed[_ti] == 1 - sym.fixed[_ti] and
      sum(abs(a - b) for a, b in zip(after.fixed, sym.fixed)) == 1)
check("a state change passes the turn", after.to_move == 1 - sym.to_move)
# LEMMA that bounds consecutive state changes: on an EVEN board no cell is its
# own mirror image, so toggling one cell always unbalances the pair {X, mirror
# X} under the axis that allowed the change.  It could in principle land on the
# OTHER axis instead -- so that is checked EXHAUSTIVELY below rather than
# assumed, which is the whole point of the lemma (it is what stops two players
# trading state changes back and forth for ever).
check("LEMMA: after a state change the position is no longer symmetric under "
      "the axis that allowed it", not is_symmetric(after))
_broken = 0
for _t2 in tog:
    _a = G.apply_move(sym, _t2)
    if is_symmetric(_a):
        _broken += 1
check("LEMMA holds for EVERY cell that could be toggled there", _broken == 0)


def _sym_family_4x4(pairs):
    """Every 4x4 position symmetric under the involution given by `pairs`.

    Such a position is determined by one representative per mirror pair: 8 free
    colours (the partner is forced OPPOSITE) and 8 free fixed bits (the partner
    is forced EQUAL), so 256 x 256 = 65,536 positions per axis.
    """
    N = 4
    out = []
    for colmask in range(1 << len(pairs)):
        col = [0] * (N * N)
        for k, ((c, r), (c2, r2)) in enumerate(pairs):
            v = (colmask >> k) & 1
            col[r * N + c] = v
            col[r2 * N + c2] = 1 - v
        for fixmask in range(1 << len(pairs)):
            fx = [0] * (N * N)
            for k, ((c, r), (c2, r2)) in enumerate(pairs):
                b = (fixmask >> k) & 1
                fx[r * N + c] = b
                fx[r2 * N + c2] = b
            out.append((tuple(col), tuple(fx)))
    return out


# BOTH axes, not just one.  `is_symmetric` is an OR over the two mirrors, so
# enumerating only the left-right family would leave every TOP-BOTTOM-only
# symmetric position untested -- 65,280 of them, half the domain of the very
# lemma being proved.
_lr = _sym_family_4x4([((c, r), (3 - c, r)) for r in range(4) for c in range(2)])
_tb = _sym_family_4x4([((c, r), (c, 3 - r)) for r in range(2) for c in range(4)])
_union = set(_lr) | set(_tb)
_tot = _still = 0
for _col, _fx in _union:
    _p = SState(size=4, colour=_col, fixed=_fx, to_move=WHITE, ply=1,
                anti_mirror=True)
    assert is_symmetric(_p), "construction of a symmetric position is wrong"
    _tot += 1
    for _i in range(16):
        _f2 = list(_fx)
        _f2[_i] ^= 1
        if is_symmetric(replace(_p, fixed=tuple(_f2))):
            _still += 1
            break
check("LEMMA proved EXHAUSTIVELY on 4x4: over ALL 130,816 symmetric positions "
      "(65,536 per axis, overlapping in 256), NONE has a state change that "
      "leaves it symmetric -- so two state changes can never happen back to "
      "back.  This is the ONLY termination evidence for the anti-mirroring "
      "rule, since the exhaustive solve below runs with it OFF.",
      len(_lr) == 65536 and len(_tb) == 65536 and len(_union) == 130816
      and _tot == 130816 and _still == 0, f"{_still}/{_tot}")
# Free the enumeration before the exhaustive solve below: holding 130,816
# position tuples alive would add ~150 MB to the run's PEAK, on top of the
# solve's own memo.
del _lr, _tb, _union
check("with anti_mirror OFF the same symmetric position offers no state change",
      all(a != b for a, b in (m.split(">") for m in
          G.legal_moves(replace(sym, anti_mirror=False)))))

# A CONSTRUCTED case random play cannot be relied on to reach: a symmetric
# position with NO swap available at all, where the state change is the ONLY
# legal move.  Kanare's "passing is not allowed" means the mover must take it.
_frozen = SState(size=4, colour=tuple((c + r) % 2 for r in range(4) for c in range(4)),
                 fixed=(1,) * 16, to_move=WHITE, ply=5, anti_mirror=True)
check("a fully frozen checkerboard is symmetric and has no swaps",
      is_symmetric(_frozen) and not any(a != b for a, b in
                                        (m.split(">") for m in G.legal_moves(_frozen))))
check("...so it is NOT terminal with anti_mirror on: the 16 state changes are "
      "the only legal moves and the mover must take one",
      not G.is_terminal(_frozen) and len(G.legal_moves(_frozen)) == 16)
_after_forced = G.apply_move(_frozen, G.legal_moves(_frozen)[0])
check("...unfixing one piece leaves it asymmetric with still no swap, so the "
      "opponent is stuck and the game ends there",
      not is_symmetric(_after_forced) and G.is_terminal(_after_forced))
check("...and that finish is an honest DRAW (a checkerboard splits BOTH armies "
      "into 8 lone pieces -- identical partitions)",
      G.returns(_after_forced) == [0.0, 0.0] and G.winner(_after_forced) is None and
      G.scores(_after_forced) == ([1] * 8, [1] * 8))
check("the very same board with anti_mirror OFF is terminal immediately",
      G.is_terminal(replace(_frozen, anti_mirror=False)) and
      G.legal_moves(replace(_frozen, anti_mirror=False)) == [])
check("describe_move names a state change by direction",
      G.describe_move(sym, _t).startswith("unfix" if sym.fixed[_ti] else "fix"))
check("describe_move renders a swap in the sheet's own notation",
      G.describe_move(s0, "5,5>5,6") == "f6-f7")

# is_symmetric itself: a hand-built mirrored position and a hand-built near-miss
_n2 = 4
_col = [0] * 16
for r in range(4):
    for c in range(4):
        _col[r * 4 + c] = (c + r) % 2
_mir = SState(size=4, colour=tuple(_col), fixed=(0,) * 16, to_move=0, ply=1, anti_mirror=True)
check("is_symmetric accepts the mirrored checkerboard", is_symmetric(_mir))
_f = [0] * 16
_f[0] = 1
check("is_symmetric REJECTS it when one cell's fixed state is unpaired",
      not is_symmetric(replace(_mir, fixed=tuple(_f))))
_f2 = [0] * 16
_f2[0] = 1
_f2[3] = 1                      # 0 and 3 are h-mirror partners in row 0
check("is_symmetric accepts a fixed PAIR that respects the mirror",
      is_symmetric(replace(_mir, fixed=tuple(_f2))))
_c2 = list(_col)
_c2[0] ^= 1
check("is_symmetric REJECTS a colour that is not the opposite of its mirror",
      not is_symmetric(replace(_mir, colour=tuple(_c2))))

# BOTH axes must count.  These two positions separate them: fixing a
# TOP-BOTTOM mirror pair leaves the position v-symmetric but not h-symmetric,
# and fixing a LEFT-RIGHT pair does the reverse.  Without both, an
# implementation that tested only one mirror would pass everything above.
def _with_fixed(cells):
    f = [0] * 16
    for c, r in cells:
        f[idx(c, r, 4)] = 1
    return replace(_mir, fixed=tuple(f))


_v_only = _with_fixed([(0, 0), (0, 3)])     # (0,0) and (0,3) are v-mirror partners
_h_only = _with_fixed([(0, 0), (3, 0)])     # (0,0) and (3,0) are h-mirror partners
check("is_symmetric accepts a TOP-BOTTOM-only symmetric position "
      "(so testing just the left-right mirror is not enough)", is_symmetric(_v_only))
check("is_symmetric accepts a LEFT-RIGHT-only symmetric position "
      "(so testing just the top-bottom mirror is not enough)", is_symmetric(_h_only))
check("...and those two really are one-axis-only, not symmetric under both",
      _v_only.fixed != _h_only.fixed and
      not is_symmetric(_with_fixed([(0, 0)])) and
      not is_symmetric(_with_fixed([(0, 0), (1, 1)])))
check("a state change is therefore offered in a one-axis-symmetric position too",
      len([m for m in G.legal_moves(_v_only) if m.split(">")[0] == m.split(">")[1]]) == 16 and
      len([m for m in G.legal_moves(_h_only) if m.split(">")[0] == m.split(">")[1]]) == 16)

# ===========================================================================
# 6. Termination
# ===========================================================================
# THE MONOVARIANT.  Every swap fixes exactly one previously-mobile piece, and a
# fixed piece can be neither a source nor a target, so with the anti-mirroring
# rule off the mobile count strictly decreases -- the game ends within `cells`
# plies and no ply cap is ever consulted.
_worst = 0
for size in (4, 6, 8):
    for seed in range(20):
        rng = random.Random(seed)
        s = G.initial_state(options={"size": size, "anti_mirror": "off"})
        prev = sum(1 for f in s.fixed if not f)
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            cur = sum(1 for f in s.fixed if not f)
            assert cur == prev - 1, "mobile count did not strictly decrease"
            prev = cur
        assert s.ply <= size * size
        _worst = max(_worst, s.ply / (size * size))
check("MONOVARIANT: with anti_mirror off the mobile count strictly decreases "
      "every ply and the game ends within `cells` plies", _worst < 1.0)
check("...so the ply cap is PROVABLY unreachable there (cells < cap)",
      all(n * n < ply_cap(n) for n in SIZES) and CAP_RECYCLES >= 2)

# With the anti-mirroring rule ON an 'unfix' can hand mobility back, so the cap
# is a real backstop.  Measured: even a player that unfixes at every chance
# never approaches it.
_max_on = 0
for size in (4, 6, 8):
    for seed in range(40):
        rng = random.Random(seed)
        s = G.initial_state(options={"size": size, "anti_mirror": "on"})
        seen = {(s.colour, s.fixed, s.to_move)}
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            un = [m for m in ms if m.split(">")[0] == m.split(">")[1]
                  and s.fixed[idx(*parse_cell(m.split(">")[0]), size)]]
            s = G.apply_move(s, rng.choice(un) if un else rng.choice(ms))
            k = (s.colour, s.fixed, s.to_move)
            assert k not in seen, "state repeated -- the game can cycle!"
            seen.add(k)
        assert s.ply < ply_cap(size)
        _max_on = max(_max_on, s.ply / (size * size))
check("with anti_mirror ON, an always-unfix player still never repeats a state "
      f"and stays far below the cap (worst {_max_on:.2f} x cells vs cap "
      f"{CAP_RECYCLES} x cells)", _max_on < 1.0)

# The cap must actually BITE if it is ever reached -- assert the patch changes
# behaviour, so this test cannot silently become vacuous.
_live = sys.modules[type(G).__module__]
_orig_cap = _live.ply_cap
try:
    _live.ply_cap = lambda size: 3
    _s = G.initial_state(options={"size": 4})
    _s = G.apply_move(_s, G.legal_moves(_s)[0])
    _s = G.apply_move(_s, G.legal_moves(_s)[0])
    _s = G.apply_move(_s, G.legal_moves(_s)[0])
    check("the ply cap BITES when reached (patch verified to change behaviour)",
          G.legal_moves(_s) == [] and G.is_terminal(_s) and _s.ply == 3)
    # ...and the RESULT at a capped state is the honest cascade, NOT a forced
    # draw.  Asserting only that the cap ends the game stops one step short of
    # the claim rules.md makes about it, which is how a "declares a draw"
    # mis-description survived in the sources for as long as it did.
    _cw, _cb = G.scores(_s)
    check("a CAPPED game is scored by the normal cascade, not fabricated into "
          "a draw (its winner is exactly what compare_scores says)",
          G.winner(_s) == (None if compare_scores(_cw, _cb) == 0 else
                           (WHITE if compare_scores(_cw, _cb) > 0 else BLACK))
          and G.returns(_s) == ([0.0, 0.0] if compare_scores(_cw, _cb) == 0 else
                                ([1.0, -1.0] if compare_scores(_cw, _cb) > 0
                                 else [-1.0, 1.0])))
finally:
    _live.ply_cap = _orig_cap
check("...and the real cap is restored", ply_cap(4) == CAP_RECYCLES * 16 and
      not G.is_terminal(G.initial_state(options={"size": 4})))

# THE DESIGNER'S PUBLISHED NUMBER.  "On a square board, the number of moves it
# takes to finish a game is about 0.25-0.35 the size of the board.  For
# instance, an 8x8 board has 64 fields, so the games should last 16-23 moves
# each."  Measured under random play, as he describes.
_lens = [play_random(8, "on", 5000 + seed).ply for seed in range(120)]
_each = sum(_lens) / len(_lens) / 2
check("PUBLISHED NUMBER: an 8x8 random game lasts 16-23 moves EACH "
      f"(measured {_each:.1f})", 16 <= _each <= 23, f"{_each:.2f}")
_ratio = _each / 64
check(f"...i.e. 0.25-0.35 x the 64 fields (measured {_ratio:.3f})",
      0.25 <= _ratio <= 0.35, f"{_ratio:.3f}")

# TWO MORE PUBLISHED NUMBERS, from Stephen Tavener's Ai Ai report for Slyde
# (mrraow.com/uploads/AiAiReports/Slyde.html, generated 2020-06-11 from 1000
# logged games).  Its "Playout/Search Speed" table reports a RANDOM-playout
# game length of 94 (SD 4) on the 12x12 board -- the apples-to-apples number,
# as its headline "Game Length: mean 91.09" comes from BOT games (its own
# UCB/UCT rows report 90).
_l12 = [play_random(12, "off", 9000 + seed).ply for seed in range(150)]
_m12 = sum(_l12) / len(_l12)
check(f"PUBLISHED NUMBER (Ai Ai): a 12x12 random playout runs 94 plies, SD 4 "
      f"(measured mean {_m12:.2f})", 92.0 <= _m12 <= 96.0, f"{_m12:.2f}")
# Ai Ai's "Move Classification" reports 528 DISTINCT actions on 12x12.  That is
# exactly the number of ORDERED orthogonally adjacent cell pairs, 2 x 2n(n-1) --
# every pair can be swapped in either direction depending on which colour is
# the mover -- so it pins the move encoding as well as the adjacency.
_all_moves = set()
for _seed in range(60):
    _s = G.initial_state(options={"size": 12, "anti_mirror": "off"})
    _rng = random.Random(_seed)
    while not G.is_terminal(_s):
        _all_moves.update(G.legal_moves(_s))
        _s = G.apply_move(_s, _rng.choice(G.legal_moves(_s)))
check("PUBLISHED NUMBER (Ai Ai): 528 distinct actions on 12x12 = 2 x 2n(n-1) "
      "ordered adjacent pairs, and no move outside that set is ever generated",
      len(_all_moves) <= 528 and _all_moves <= {
          f"{c},{r}>{c+dc},{r+dr}"
          for r in range(12) for c in range(12) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
          if 0 <= c + dc < 12 and 0 <= r + dr < 12},
      f"{len(_all_moves)} distinct moves seen")
check("...and random play alone already reaches nearly all 528 of them",
      len(_all_moves) > 500, f"{len(_all_moves)}")
check("Ai Ai's 0.00% draw rate over 1000 12x12 games is reproduced (exact ties "
      "need a fully mirrored partition, which 12x12 never delivers by chance)",
      all(G.returns(play_random(12, "off", 400 + s_)) != [0.0, 0.0] for s_ in range(40)))

# ===========================================================================
# 7. serialize / deserialize -- compared as STATE OBJECTS
# ===========================================================================
KEYS = {"size", "colour", "fixed", "to_move", "ply", "anti_mirror", "last"}
_checked = 0
for size in (4, 6):
    for anti in ("on", "off"):
        rng = random.Random(size)
        s = G.initial_state(options={"size": size, "anti_mirror": anti})
        while True:
            d = G.serialize(s)
            assert set(d) == KEYS, f"key set drifted: {set(d) ^ KEYS}"
            assert G.deserialize(d) == s, "state object did not round-trip"
            import json
            assert json.loads(json.dumps(d)) == d, "not JSON-able"
            _checked += 1
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
check("serialize/deserialize compared as STATE OBJECTS over whole games, with "
      "the exact key set asserted", _checked > 60, f"only {_checked}")
# Every field must be load-bearing: dropping any one must break the round-trip.
_s = play_random(6, "on", 3, stop=lambda st: st.ply == 9)
for k in sorted(KEYS):
    d = G.serialize(_s)
    del d[k]
    try:
        G.deserialize(d)
        raise AssertionError(f"serialize may drop '{k}' unnoticed")
    except KeyError:
        pass
check("EVERY serialized field is load-bearing (a dropped key raises, it does "
      "not silently re-default)", True)
_d = G.serialize(_s)
_d["fixed"] = [0] * len(_d["fixed"])
check("the mobile/fixed flag really survives the round trip (clearing it "
      "changes the deserialized state)", G.deserialize(_d) != _s)

# ===========================================================================
# 8. render() -- bounds for EVERY shipped size, from a FAR-CORNER position
# ===========================================================================
for size in SIZES:
    for anti in ("on", "off"):
        # Reach a position with pieces moved in the far corners, through
        # apply_move -- a freshly initialised state would make this vacuous.
        s = G.initial_state(options={"size": size, "anti_mirror": anti})
        corners = [f"{size-1},{size-1}", f"{size-1},{size-2}", "0,0", "1,0"]
        for _ in range(4):
            mv = next((m for m in G.legal_moves(s)
                       if m.split(">")[0] in corners or m.split(">")[1] in corners), None)
            s = G.apply_move(s, mv if mv else G.legal_moves(s)[0])
        spec = G.render(s)
        b = spec["board"]
        assert b == {"type": "square", "width": size, "height": size}, b
        assert len(spec["pieces"]) == size * size, "a piece went missing"
        seen_cells = set()
        for p in spec["pieces"]:
            c, r = parse_cell(p["cell"])
            assert 0 <= c < b["width"] and 0 <= r < b["height"], \
                f"piece {p['cell']} outside the declared {size}x{size} board"
            assert p["owner"] in (0, 1)
            seen_cells.add(p["cell"])
        assert len(seen_cells) == size * size, "duplicate cells in render()"
        # a far corner really is occupied by a piece we can see
        assert f"{size-1},{size-1}" in seen_cells
        for h in spec["highlights"]:
            assert h["cell"] in seen_cells
        assert isinstance(spec["caption"], str) and spec["caption"]
check("render() declares the right dimensions and keeps every piece inside, "
      "for EVERY shipped size, from a far-corner position", True)

# The fixed/mobile distinction must be VISIBLE, or the game is unplayable.
_s = G.apply_move(s0, "5,5>5,6")
_by_cell = {p["cell"]: p for p in G.render(_s)["pieces"]}
check("a FIXED piece renders as a ring with an inner marker (Board.jsx honours "
      "shape='ring' + inner)",
      _by_cell["5,6"].get("shape") == "ring" and _by_cell["5,6"].get("inner") == WHITE)
check("a MOBILE piece renders as a plain disc (no shape key)",
      "shape" not in _by_cell["5,5"] and "shape" not in _by_cell["0,0"])
check("every fixed piece, and only a fixed piece, gets the ring",
      all((p.get("shape") == "ring") == bool(_s.fixed[idx(*parse_cell(p["cell"]), 12)])
          for p in G.render(_s)["pieces"]))
check("the caption reports both cascading tallies",
      "White" in G.render(_s)["caption"] and "Black" in G.render(_s)["caption"])

# Winner naming, pinned to the Kanare figure's ground truth (Black owns the
# printed 18-group and the sheet says Black wins) rather than to our own code.
_fig_state = SState(size=8, colour=FIG_COLOUR, fixed=(1,) * 64, to_move=WHITE,
                    ply=1, anti_mirror=False)
check("figure position is terminal when every piece is fixed",
      G.is_terminal(_fig_state))
check("WINNER NAMING pinned to the sheet: the figure position is a BLACK win",
      G.winner(_fig_state) == BLACK and G.returns(_fig_state) == [-1.0, 1.0])
check("...and the caption says so in words",
      G.render(_fig_state)["caption"].startswith("Black wins"))
check("...while the mirror-image position (colours exchanged) is a WHITE win, "
      "so the caption is not a constant",
      G.render(replace(_fig_state,
                       colour=tuple(1 - x for x in FIG_COLOUR)))["caption"].startswith("White wins"))

# LEMMA: the setup-parity choice is unobservable.  A left-right mirror carries
# the (c+r) even setup onto the (c+r) odd setup and is an automorphism of
# adjacency, of grouping and of the mirror-symmetry test -- so the sheets are
# right not to specify which parity holds White.
def _hmir(cid, n):
    c, r = parse_cell(cid)
    return f"{n-1-c},{r}"


_n3 = 6
_a = G.initial_state(options={"size": _n3})
_flipped = replace(_a, colour=tuple(1 - x for x in _a.colour))
_ma = {tuple(_hmir(x, _n3) for x in m.split(">")) for m in G.legal_moves(_a)}
_mb = {tuple(m.split(">")) for m in G.legal_moves(_flipped)}
check("LEMMA: the two setup parities are the same game under a mirror "
      "(so the unspecified parity is unobservable)", _ma == _mb)

# ===========================================================================
# 8b. heuristic() -- shape AND direction, pinned to measured values
# ===========================================================================
_h6 = G.initial_state(options={"size": 6})
_hv = G.heuristic(_h6)
check("heuristic returns a LIST of num_players payoffs (a bare float would "
      "raise TypeError in MCTS back-propagation)",
      isinstance(_hv, list) and len(_hv) == 2 and all(isinstance(x, float) for x in _hv))
check("heuristic is zero-sum and bounded to [-1, 1]",
      abs(_hv[0] + _hv[1]) < 1e-12 and all(abs(x) <= 1.0 for x in _hv))
check("heuristic is 0 at the symmetric opening (every piece a lone group)",
      abs(_hv[0]) < 1e-12)
# DIRECTION is a separate assertion from shape: a sign-flipped eval (the bot
# plays to LOSE) and a constant-zero eval both pass every shape check.
_blk = list(_h6.colour)
for _i in range(6):
    _blk[_i] = WHITE                      # give White one solid 6-block
_white_better = replace(_h6, colour=tuple(_blk))
_black_better = replace(_h6, colour=tuple(1 - x for x in _blk))
check("heuristic DIRECTION: the side with the bigger block scores higher, "
      "pinned to measured values (+0.7456 / -0.7456)",
      abs(G.heuristic(_white_better)[0] - 0.745596) < 1e-4 and
      abs(G.heuristic(_black_better)[0] + 0.745596) < 1e-4,
      f"{G.heuristic(_white_better)[0]:.6f}")
check("heuristic is seat-antisymmetric (mirroring the colours negates it)",
      abs(G.heuristic(_white_better)[0] + G.heuristic(_black_better)[0]) < 1e-12)
check("heuristic is not a constant (it separates these two positions)",
      G.heuristic(_white_better)[0] > _hv[0] > G.heuristic(_black_better)[0])
# It must actually survive the consumer that will call it, at a max_rollout low
# enough to FORCE the cutoff (a game longer than max_rollout hides a bad shape).
from agp.mcts import MCTSBot  # noqa: E402
_mv = MCTSBot(random.Random(1), iterations=30, max_rollout=4).select(G, _h6)
check("MCTSBot with max_rollout=4 (cutoff forced) uses the heuristic and "
      "returns a legal move", _mv in G.legal_moves(_h6))
# ...and it is genuinely consulted on the DEFAULT board at the DEFAULT
# max_rollout, which is the only condition under which it can matter at all.
_calls = [0]
_orig_h = type(G).heuristic
try:
    type(G).heuristic = lambda self, st: (_calls.__setitem__(0, _calls[0] + 1),
                                          _orig_h(self, st))[1]
    _mv12 = MCTSBot(random.Random(2), iterations=20, max_rollout=50).select(G, s0)
finally:
    type(G).heuristic = _orig_h
check("the heuristic is actually CONSULTED on the default 12x12 board at the "
      f"default max_rollout=50 ({_calls[0]}/20 rollouts hit the cutoff), so it "
      "is not dead code", _calls[0] == 20 and _mv12 in G.legal_moves(s0),
      f"{_calls[0]}/20")

# ===========================================================================
# 9. Exhaustive solve of the smallest shipped board (4x4, anti-mirroring off)
# ===========================================================================
# Every reachable state, by memoised negamax over the SHIPPED game.  This is the
# termination + drawlessness + game-value anchor, all at once.
# The recursion limit is deliberately just above the monovariant bound: a cycle
# in the state graph would recurse for ever (a memo entry is only written after
# its subtree returns), so completing the solve at this limit IS the proof of
# acyclicity rather than a claim about it.  `_depth` records how deep it went.
#
# The memo key is PACKED into a 33-bit int rather than kept as the pair of
# 16-tuples it comes from.  A tuple-of-tuples key costs ~600 B per state, so the
# 1.6 M states peak at ~855 MB; packed it is ~191 MB.  `_BITS` makes packing two
# C-level bytes() calls plus two dict hits.  The key is DERIVED from the shipped
# state, so this changes bookkeeping only -- every count below is unchanged.
sys.setrecursionlimit(200)
_BITS = {bytes((m >> i) & 1 for i in range(16)): m for m in range(1 << 16)}
_memo = {}
_stats = {"term": 0, "ties": 0, "depth": 0, "cur": 0, "edges": 0}


def _solve(s, mobile):
    k = (_BITS[bytes(s.colour)] << 17) | (_BITS[bytes(s.fixed)] << 1) | s.to_move
    hit = _memo.get(k)
    if hit is not None:
        return hit
    ms = G.legal_moves(s)
    if not ms:
        v = G.returns(s)[0]
        _stats["term"] += 1
        _stats["ties"] += (v == 0)
        _memo[k] = (v, 0)
        return _memo[k]
    _stats["cur"] += 1
    _stats["depth"] = max(_stats["depth"], _stats["cur"])
    best, ln = None, 0
    for mv in ms:
        child = G.apply_move(s, mv)
        cmob = child.fixed.count(0)
        # THE MONOVARIANT, asserted on EVERY EDGE of the entire state graph --
        # not merely on a sample of random games.  This is what makes the
        # acyclicity above a consequence rather than an observation: a strictly
        # decreasing integer cannot return to a value it has left.
        assert cmob == mobile - 1, "mobile count did not strictly decrease"
        _stats["edges"] += 1
        v, l = _solve(child, cmob)
        if best is None or (v > best if s.to_move == WHITE else v < best):
            best = v
        ln = max(ln, l + 1)
    _stats["cur"] -= 1
    _memo[k] = (best, ln)
    return _memo[k]


_root = G.initial_state(options={"size": 4, "anti_mirror": "off"})
_val, _longest = _solve(_root, _root.fixed.count(0))
check("4x4 exhaustive solve: the mobile count strictly decreases across ALL "
      "4,397,292 edges of the state graph, which is WHY it is acyclic",
      _stats["edges"] == 4397292, str(_stats["edges"]))
check("4x4 exhaustive solve: 1,607,132 reachable states", len(_memo) == 1607132, str(len(_memo)))
check("4x4 exhaustive solve: the game is a FIRST-PLAYER (White) win", _val == 1, str(_val))
check("4x4 exhaustive solve: the longest possible line is 15 plies, inside the "
      "monovariant bound of 16 = cells", _longest == 15 and _longest <= 16, str(_longest))
check("4x4 exhaustive solve: the search never nested deeper than 16 = cells, "
      "so no state repeats on any path -- the state graph is ACYCLIC and every "
      f"line terminates (max nesting {_stats['depth']}, recursion limit 200)",
      _stats["depth"] <= 16, str(_stats["depth"]))
check("4x4 exhaustive solve: 161,979 terminal positions, 21,609 of them exact "
      "TIES (13.34%) -- draws are common, not a corner case",
      _stats["term"] == 161979 and _stats["ties"] == 21609,
      f"{_stats['term']}/{_stats['ties']}")

print(f"slyde selftest: {len(OK)} checks passed")
for name in OK:
    print("  OK", name)
