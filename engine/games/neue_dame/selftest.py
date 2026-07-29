#!/usr/bin/env python3
"""Neue Dame correctness anchors -- pure stdlib, run by tests/test_games.py.

There is no reference engine for Neue Dame (it is in no game library), so the
anchor is the *primary source itself*: the *four composed problems* published
with the rules in Abstract Games 18 (positions read off the printed diagrams,
solutions from p. 1 of the same issue) are replayed here move for move, together
with the magazine's own side variations and its "(forced)" annotations.

  * Puzzles 1, 2 and 3 replay EXACTLY -- every printed ply legal, every
    "(forced)" reply the unique legal move, and the printed point counts
    ("At least 3 points" / "At least 6 points") reproduced by the scoring rule.
  * Puzzle 4 replays 39 of its 40 printed plies; the 40th (Green's 4th move) is
    proved illegal here -- see rules.md, "Errata".

Second anchor: an INDEPENDENT re-implementation of move generation and move
application (different board representation, iterative instead of recursive) is
differentialled against the shipped engine.  The one-time run was 4,000 random
games / 311,872 positions with 0 mismatches; a 25-game slice runs below.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                              # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
M = sys.modules[type(G).__module__]        # the LIVE module object

GREEN, BLACK = M.GREEN, M.BLACK
gm, gd, bm, bd = (GREEN, False), (GREEN, True), (BLACK, False), (BLACK, True)

FAILS = []


def ok(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def pos(desc, to_move=GREEN, **kw):
    """Build a position from {algebraic: [top, ..., bottom]} (diagram order)."""
    board = {M.from_alg(k): tuple(reversed(v)) for k, v in desc.items()}
    s = M.NState(board=board, to_move=to_move, **kw)
    s.reps = {G._key(s): 1}
    return s


def notation(s):
    """{printed notation: internal move} for the side to move."""
    return {G.describe_move(s, m): m for m in G.legal_moves(s)}


def play(s, printed):
    """Play a printed move; return (new state, was it legal, how many choices)."""
    n = notation(s)
    if printed not in n:
        return s, False, sorted(n)
    return G.apply_move(s, n[printed]), True, len(n)


def force(s, printed):
    """Apply a printed move regardless of legality (used once, for the erratum)."""
    cells = [printed[i:i + 2] for i in range(len(printed))
             if printed[i] in "abcdefgh" and printed[i + 1:i + 2] in "12345678"]
    return G.apply_move(s, ">".join(M.cid(M.from_alg(c)) for c in cells))


def line(s, moves, tag, forced=(), relaxed=()):
    """Replay a printed line; check legality and the '(forced)' annotations."""
    for i, mv in enumerate(moves):
        ns, legal, info = play(s, mv)
        if not legal:
            if i in relaxed:
                ok(sorted(info) == relaxed[i] if isinstance(relaxed, dict) else True,
                   "%s ply %d: expected-illegal move %s, legal were %s"
                   % (tag, i, mv, info))
                s = force(s, mv)
                continue
            ok(False, "%s ply %d: printed move %s is not legal (legal: %s)"
               % (tag, i, mv, info))
            return s
        if i in forced:
            ok(info == 1, "%s ply %d: %s is annotated forced but there were "
                          "%d legal moves" % (tag, i, mv, info))
        s = ns
    return s


def stack(s, a):
    """The column on square `a`, top piece first."""
    col = s.board.get(M.from_alg(a))
    return list(reversed(col)) if col else []


# --------------------------------------------------------------------------
# 1. Board, setup, geometry
# --------------------------------------------------------------------------
cells = [(c, r) for r in range(8) for c in range(8) if M.on_board(c, r)]
ok(len(cells) == 32, "the board is the 32 dark squares of an 8x8 grid")
ok(M.on_board(*M.from_alg("a1")) and not M.on_board(*M.from_alg("h1")),
   "a1 is dark and h1 is light (the bottom right square is white)")
ok(all(M.from_alg(M.alg(c)) == c for c in cells),
   "algebraic naming round-trips on every playing square")

s0 = G.initial_state()
ok(len(s0.board) == 24, "24 columns at the start, one piece each")
ok(all(len(col) == 1 for col in s0.board.values()), "every opening column is a lone man")
ok(sorted(M.alg(c) for c, col in s0.board.items() if M.owner(col) == GREEN)
   == ["a1", "a3", "b2", "c1", "c3", "d2", "e1", "e3", "f2", "g1", "g3", "h2"],
   "Green's 12 men fill the dark squares of rows 1-3")
ok(sorted(M.alg(c) for c, col in s0.board.items() if M.owner(col) == BLACK)
   == ["a7", "b6", "b8", "c7", "d6", "d8", "e7", "f6", "f8", "g7", "h6", "h8"],
   "Black's 12 men fill the dark squares of rows 6-8")
ok(G.current_player(s0) == GREEN, "Green (the bottom player) moves first")
ok(len(G.legal_moves(s0)) == 7, "seven opening moves (the draughts opening)")

# --------------------------------------------------------------------------
# 2. Puzzle 1 -- "Green to promote one of his pieces" (Gering 2014)
#    Diagram: AG18 p.31, bottom left.  All 24 pieces are shown.
# --------------------------------------------------------------------------
P1 = {"a7": [gm, bm, bm], "a5": [bm, gm, gm], "a3": [gm, bm, bm], "a1": [gm],
      "b8": [bm], "c7": [bm], "c3": [bm], "e7": [bm], "e3": [gm, gm],
      "f8": [bm], "g7": [bm], "g3": [gm], "g1": [gm], "h8": [bm],
      "h6": [gm], "h4": [gm], "h2": [gm]}
p1 = pos(P1)
ok(sum(len(c) for c in p1.board.values()) == 24, "Puzzle 1 diagram holds all 24 pieces")
ok(sum(1 for c in p1.board.values() for (o, _k) in c if o == GREEN) == 12
   and sum(1 for c in p1.board.values() for (o, _k) in c if o == BLACK) == 12,
   "Puzzle 1: 12 pieces a side")
s = line(p1, ["a1-b2", "c3xa1*D", "e3-d4", "a1xe5", "d4xf6xd8*D"],
         "Puzzle 1", forced={1, 3, 4})
ok(G.dames(s) == 2, "Puzzle 1 ends with two Dames (Black's on a1's tower, Green's on d8)")
ok(stack(s, "d8")[0] == gd, "Puzzle 1: 3.d4xf6xd8 crowns the Green man on d8")

# the crowned man must NOT go on -- from d8 it could take c7 and land on b6
ok("d4xf6xd8*D" in notation(pos(P1_after := {
    "d4": [gm], "e5": [bd, gm, gm], "e7": [bm], "c7": [bm], "g7": [bm],
    "b8": [bm], "f8": [bm], "h8": [bm], "a7": [gm, bm, bm], "a5": [bm, gm, gm],
    "a3": [gm, bm, bm], "g3": [gm], "g1": [gm], "h6": [gm], "h4": [gm], "h2": [gm]})),
   "crowning ends the capture: d4xf6xd8*D and not d4xf6xd8xb6")
ok(not any(mv.startswith("d4xf6xd8x")
           for mv in notation(pos(P1_after))),
   "no capture may continue past the crowning square")

# --------------------------------------------------------------------------
# 3. Puzzle 2 -- "Black has just moved d8-e7, now Green to win" (Gering 2019)
#    Diagram: AG18 p.31, top right.  Only 9 pieces are shown; the article says
#    the other 15 are "stacked beneath other pieces in such a way that they do
#    not alter the solution".  Witness used here: all 15 buried under the one
#    column whose top is never captured, Green's Dame on e5.
# --------------------------------------------------------------------------
P2 = {"b8": [bd], "b4": [gm], "d6": [gm], "d2": [bm], "e7": [bm],
      "e5": [gd] + [gm] * 8 + [bm] * 7, "f8": [bm], "f4": [gm], "h2": [bm]}
p2 = pos(P2)
ok(sum(len(c) for c in p2.board.values()) == 24
   and sum(1 for c in p2.board.values() for (o, _k) in c if o == GREEN) == 12,
   "Puzzle 2 witness position has 24 pieces, 12 a side")
MAIN2 = ["e5-c3", "b8xe5xg3", "c3xe1xh4xd8"]
s = line(p2, MAIN2 + ["f8-g7", "g3-f4", "g7-h6", "f4-e5", "h6-g5", "d8xh4",
                      "h2-g1*D", "h4-d8", "g1-a7", "b4-c5", "a7xd4xf6", "d8xg5"],
         "Puzzle 2", forced={1, 2, 8, 9, 13, 14})
ok(G.is_terminal(s) and s.winner == GREEN,
   "Puzzle 2: 8.d8xg5 leaves Green owning every column -- Green wins")
ok(G.dames(s) == 3 and G.score(s) == 3.0,
   "Puzzle 2 scores exactly the printed 'At least 3 points for Green'")


def visible_dames(st):
    """The rival reading: count only the Dames sitting on TOP of a column."""
    return sum(1 for c in st.board.values() if M.is_dame(c))


ok(visible_dames(s) == 1,
   "Puzzle 2's printed 3 points is reproduced ONLY by counting buried Dames -- "
   "the rival 'visible Dames' reading gives 1")

# the printed side variations
B2 = MAIN2 + ["f8-e7", "d8xf6", "h2-g1*D", "f6-d8"]
line(pos(P2), MAIN2 + ["h2-g1*D", "b4-c5", "g1xb6", "d8xa5"], "Puzzle 2 var (a)")
line(pos(P2), B2 + ["g1-a7", "d8-a5", "a7-f2", "b4-c5", "f2xh4", "a5-d8",
                    "h4xf2xb6", "d8xa5"], "Puzzle 2 var (b)")
line(pos(P2), MAIN2 + ["f8-g7", "g3-f4", "g7-h6", "f4-e5", "h6-g5", "d8xh4",
                       "h2-g1*D", "h4-d8", "g1-h2", "e5-d6", "h2xc7", "d8xb6"],
     "Puzzle 2 var (d)")
line(pos(P2), B2 + ["g1-f2", "b4-c5", "f2xh4", "d8-a5", "h4xf2xb6", "a5xc7"],
     "Puzzle 2 var (e)")
sf = line(pos(P2), B2 + ["g1-h2", "b4-a5", "h2xf4"], "Puzzle 2 var (f)")
# 6.g3xe5 is a MAN's capture played by a side that owns a Dame (on d8) which
# cannot capture -- so Dame precedence only bites when a Dame actually CAN take.
ok(any(M.owner(c) == GREEN and M.is_dame(c) for c in sf.board.values()),
   "Puzzle 2 var (f): Green owns a Dame when the printed 6.g3xe5 is played")
ok("g3xe5" in notation(sf) and not M.is_dame(sf.board[M.from_alg("g3")]),
   "Puzzle 2 var (f): ... and 6.g3xe5 is nonetheless a MAN's capture, so a Dame "
   "that cannot capture does not suppress the men")
line(sf, ["g3xe5"], "Puzzle 2 var (f) end")
line(pos(P2), B2 + ["g1-a7", "d8-a5", "a7-b8", "b4-c5", "b8xh2", "a5-e1",
                    "h2xd6xb4", "e1xa5"], "Puzzle 2 var (g)")
line(pos(P2), B2 + ["g1-a7", "d8-a5", "a7-b8", "b4-c5", "b8xh2", "c5-d6",
                    "h2xe5xc7", "a5xd8"], "Puzzle 2 var (i)")
line(pos(P2), B2 + ["g1-a7", "d8-a5", "a7-d4", "b4-c5", "d4xb6", "a5xc7"],
     "Puzzle 2 var (h)")
# printed notation slips in those variations (rules.md, "Errata")
v = pos(P2)
for mv in MAIN2 + ["h2-g1*D", "b4-c5"]:
    v, _lg, _n = play(v, mv)
n = notation(v)
ok("g1xb6" in n and "g1-b6" not in n,
   "var (a): the printed quiet 'g1-b6' is in fact the capture g1xb6")
ok(not M.on_board(*M.from_alg("c4")),
   "var (g): the printed landing square c4 is a light square, not on the board")

# --------------------------------------------------------------------------
# 4. Puzzle 3 -- "Green to win" (Gering 2019).  AG18 p.31, middle right.
#    11 pieces shown; witness for the 13 buried ones: one Green under b8 and the
#    rest under Green's h2 man.  The choice is not free -- e.g. burying a BLACK
#    piece under b8 makes the printed 6.f4-e5 illegal -- which is exactly what
#    the article means by "stacked ... in such a way that they do not alter the
#    solution".
# --------------------------------------------------------------------------
P3 = {"b8": [bd, gm], "b2": [bm, bm, bm], "c3": [bm], "g7": [bm, bd], "g5": [bm],
      "e1": [gm], "g1": [gm], "h2": [gm] * 9 + [bm] * 4}
p3 = pos(P3)
ok(sum(len(c) for c in p3.board.values()) == 24
   and sum(1 for c in p3.board.values() for (o, _k) in c if o == BLACK) == 12,
   "Puzzle 3 witness position has 24 pieces, 12 a side")
MAIN3 = ["e1-d2", "c3xe1*D", "g1-f2", "e1xg3", "h2xf4xh6xf8*D", "b8xh2",
         "f8xh6", "h2xf4", "h6xc1xa3"]
s = line(p3, MAIN3 + ["b2-a1*D", "f4-e5", "a1xf6", "e5xg7", "f6-e5", "g7-h8*D",
                      "e5-f4", "h8-d4", "f4-g3", "d4-e3", "g3-h2", "e3-g1"],
         "Puzzle 3", forced={1, 3, 4, 5, 6, 7, 11, 12})
ok(G.is_terminal(s) and s.winner == GREEN,
   "Puzzle 3: 11.e3-g1 blockades Black -- Black has a column but no move, and loses")
ok(s.board and M.owner(list(s.board.values())[0]) is not None, "board intact")
ok(any(M.owner(c) == BLACK for c in s.board.values()),
   "Puzzle 3's loser still OWNS a column: this is a blockade, not a wipe-out")
ok(G.dames(s) == 6 and G.score(s) == 6.0,
   "Puzzle 3 scores exactly the printed 'At least 6 points for Green'")
ok(visible_dames(s) == 2,
   "Puzzle 3's printed 6 points needs the buried Dames too ('visible' gives 2)")
# variation (a): 5...b2-c1*D
s = line(p3, MAIN3 + ["b2-c1*D", "a3-d6", "c1xg5", "f4xh6", "g5-h4", "d6-b8",
                      "h4-g3"], "Puzzle 3 var (a)")
ok(list(notation(s)) == ["b8xh2"],
   "Puzzle 3 var (a) ends '9.The Lady captures' -- b8xh2 is Green's only move")
ok(G.dames(s) == 5, "Puzzle 3 var (a) holds the printed 5 Dames")
ok(visible_dames(s) == 1,
   "Puzzle 3 var (a): the printed 5 is the buried-inclusive count ('visible' = 1). "
   "Together with the main line's 6 this pins the scoring rule to two DIFFERENT "
   "printed totals from the same problem")

# --------------------------------------------------------------------------
# 5. Puzzle 4 -- "Battle of Dinklar", Green to win (Gering 2019).
#    AG18 p.31, bottom right.  All 24 pieces shown.
# --------------------------------------------------------------------------
P4 = {"a1": [bd], "b6": [gm] + [bm] * 6, "c5": [gm] * 5, "c3": [bd],
      "g1": [bd] + [gm] * 5, "h6": [gm, bm, bm], "h4": [bd]}
p4 = pos(P4)
ok(sum(len(c) for c in p4.board.values()) == 24, "Puzzle 4 diagram holds all 24 pieces")
ok(G.dames(p4) == 4, "Puzzle 4 starts with Black's four Dames (a1, c3, g1, h4)")

# 5a. the printed 4th move is illegal -- Green MUST capture with the c5 tower
s = line(p4, ["b6-a7", "g1xb6", "a7-b8*D", "b6xd4", "h6-g7", "d4xb6"],
         "Puzzle 4 opening", forced={1, 3, 5})
ok(list(notation(s)) == ["c5xa7"],
   "Puzzle 4: after 3...d4xb6 Green's ONLY legal move is c5xa7, so the printed "
   "'4.dg7-f8*D' is illegal (capturing is mandatory)")

# ... and no ordering of Green's four quiet moves rescues the line
import itertools                                                   # noqa: E402
A, B, C, D = "a7-b8*D", "b8-a7", "h6-g7", "g7-f8*D"
orders = [o for o in itertools.permutations([A, B, C, D])
          if o.index(A) < o.index(B) and o.index(C) < o.index(D)]
ok(len(orders) == 6, "Green's four quiet moves admit six dependency-respecting orders")
survivors = []
for o in orders:
    st, alive, gi, seq = pos(P4), True, 0, ["b6-a7"] + list(o)
    for ply in range(10):
        n = notation(st)
        if ply % 2 == 0:
            if seq[gi] not in n:
                alive = False
                break
            st = G.apply_move(st, n[seq[gi]])
            gi += 1
        else:
            pick = [k for k in n if k in ("g1xb6", "b6xd4", "d4xb6")]
            if not pick:
                alive = False
                break
            st = G.apply_move(st, n[pick[0]])
    if alive:
        survivors.append(o)
ok(not survivors,
   "no ordering of Green's four quiet moves makes Puzzle 4's printed line legal "
   "(survivors: %s)" % (survivors,))

# ... and no RULE READING rescues it either.  An illegal printed move is only an
# erratum if the ruleset is right; if some reading made it legal, that reading
# would be the better candidate.  Three readings do legalise it -- and each one
# is refuted by a printed move in one of the other three problems.
def replay_first_illegal(g, start, moves):
    """Index of the first printed ply this ruleset rejects (None = all legal)."""
    s = pos(start)
    for i, mv in enumerate(moves):
        n = {g.describe_move(s, m): m for m in g.legal_moves(s)}
        if mv not in n:
            return i
        s = g.apply_move(s, n[mv])
    return None


_BASE = type(G)


class _Italian(_BASE):
    """Italian draughts: a man may not capture a King (here: a Dame-topped column)."""

    def _candidates(self, board, sq, col, player, jumped):
        out = _BASE._candidates(self, board, sq, col, player, jumped)
        if M.is_dame(col):
            return out
        return [t for t in out if not M.is_dame(board[t[0]])]


class _DameMonopoly(_BASE):
    """'A capture by a Lady takes precedence' read as: if you OWN a Lady, only a
    Lady may capture -- so with no Lady capture available you make a quiet move."""

    def _all_captures(self, board, player):
        dame, man = [], []
        for sq_, col_ in board.items():
            if M.owner(col_) != player:
                continue
            (dame if M.is_dame(col_) else man).extend(
                [sq_] + p for p in self._chains(board, sq_, col_, player, frozenset()))
        if dame:
            return dame
        if any(M.owner(c) == player and M.is_dame(c) for c in board.values()):
            return []
        return man


class _NoTaller(_BASE):
    """Invented reading: a column may not jump a column taller than itself."""

    def _candidates(self, board, sq, col, player, jumped):
        return [t for t in _BASE._candidates(self, board, sq, col, player, jumped)
                if len(board[t[0]]) <= len(col)]


P4_TO_MOVE4 = ["b6-a7", "g1xb6", "a7-b8*D", "b6xd4", "h6-g7", "d4xb6", "g7-f8*D"]
L1_PRINTED = ["a1-b2", "c3xa1*D", "e3-d4", "a1xe5", "d4xf6xd8*D"]
MAIN2_ = ["e5-c3", "b8xe5xg3", "c3xe1xh4xd8"]
L2F_PRINTED = MAIN2_ + ["f8-e7", "d8xf6", "h2-g1*D", "f6-d8",
                        "g1-h2", "b4-a5", "h2xf4", "g3xe5"]      # variation (f)
L3_PRINTED = MAIN3 + ["b2-a1*D", "f4-e5", "a1xf6", "e5xg7", "f6-e5", "g7-h8*D",
                      "e5-f4", "h8-d4", "f4-g3", "d4-e3", "g3-h2", "e3-g1"]
for _name, _cls in (("Italian: a man may not take a Dame-topped column", _Italian),
                    ("only a Lady may capture if you own one", _DameMonopoly),
                    ("a column may not jump a taller column", _NoTaller)):
    _v = _cls()
    ok(replay_first_illegal(_v, P4, P4_TO_MOVE4) is None,
       "reading '%s' does legalise Puzzle 4's printed 4th move" % _name)
    _broken = [t for t, st, mv in (("Puzzle 1", P1, L1_PRINTED),
                                   ("Puzzle 2 var (f)", P2, L2F_PRINTED),
                                   ("Puzzle 3", P3, L3_PRINTED))
               if replay_first_illegal(_v, st, mv) is not None]
    ok(_broken,
       "reading '%s' would rescue Puzzle 4's move 4, so it must be refuted "
       "elsewhere -- and it is, by %s" % (_name, _broken))
# the shipped ruleset, by contrast, replays all three of those lines
ok([t for t, st, mv in (("Puzzle 1", P1, L1_PRINTED),
                        ("Puzzle 2 var (f)", P2, L2F_PRINTED),
                        ("Puzzle 3", P3, L3_PRINTED))
    if replay_first_illegal(G, st, mv) is not None] == [],
   "control: the shipped ruleset replays all three refuting lines")

# 5b. the rest of Puzzle 4 -- 39 of 40 printed plies, forced replies and score
L4 = ["b6-a7", "g1xb6", "a7-b8*D", "b6xd4", "h6-g7", "d4xb6",
      "g7-f8*D", "b6xd4", "b8-a7", "d4xb6",
      "a7xd4xb2", "a1xd4xa7", "f8-a3", "a7xc5", "a3xc1", "c5xa7",
      "c1xa3", "a7xc5", "a3xc1", "c5xa7", "c1xa3", "a7xc5",
      "a3xc1", "c5xa7", "c1xa3", "a7xc5", "a3xc1", "c5xa7",
      "c1xa3", "a7xc5", "a3xd6", "h4-e1", "c5-b4", "e1xa5",
      "d6-c7", "a5xc3", "c7-e5", "c3xa5", "e5-a1", "a5xc3"]
s = line(pos(P4), L4, "Puzzle 4", forced=set(range(13, 31)) | {1, 3, 5, 7, 9, 33, 35, 37, 39},
         relaxed={6: ["c5xa7"]})
ok(list(notation(s)) == ["a1xd4"],
   "Puzzle 4: '21.a1 (or h8) captures' -- a1xd4 is the only move")
s = line(s, ["a1xd4"], "Puzzle 4 finish")
ok(G.is_terminal(s) and s.winner == GREEN and G.score(s) == 6.0,
   "Puzzle 4 ends exactly on the printed '6 points for Green'")
ok(visible_dames(s) == 2,
   "Puzzle 4's printed 6 points is the buried-inclusive count ('visible' = 2)")

# the printed alternatives at moves 18 and 20 really are all playable
s18 = line(pos(P4), L4[:31] + ["h4-e1", "c5-b4", "e1xa5"], "Puzzle 4 to move 18",
           relaxed={6: ["c5xa7"]})
n18 = notation(s18)
ok(all(a in n18 for a in ("d6-c7", "d6-b8", "d6-e7", "d6-f8", "d6-h2")),
   "Puzzle 4 note (b): d6-c7, d6-b8, d6-e7, d6-f8 and d6-h2 all work")
s20 = line(s18, ["d6-c7", "a5xc3", "c7-e5", "c3xa5"], "Puzzle 4 to move 20")
n20 = notation(s20)
ok("e5-a1" in n20 and "e5-h8" in n20, "Puzzle 4 move 20: '20.e5-a1 (or h8)'")
sa = line(line(pos(P4), L4[:31], "Puzzle 4 to move 16", relaxed={6: ["c5xa7"]}),
          ["h4-d8", "c5-b6", "d8xa5", "d6-b8", "a5xc7"], "Puzzle 4 var (a)")
ok(list(notation(sa)) == ["b8xd6"],
   "Puzzle 4 var (a): '19.b8 (or h2) captures'")
ok(G.dames(sa) == 6,
   "Puzzle 4 var (a) holds SIX Dames, not the printed 'five' (a slip in the "
   "magazine's point count)")

# --------------------------------------------------------------------------
# 6. The rules, one at a time, on constructed positions
# --------------------------------------------------------------------------
# capture is mandatory (quiet moves exist but are not offered)
p = pos({"c3": [gm], "d4": [bm], "a1": [gm]})
ok(list(notation(p)) == ["c3xe5"], "capturing is mandatory: only the jump is legal")

# a man captures FORWARD only, and moves forward only
p = pos({"e5": [gm], "d4": [bm], "f4": [bm], "a1": [gm]})
ok(sorted(notation(p)) == ["a1-b2", "e5-d6", "e5-f6"],
   "a man captures forward only: the enemies BEHIND it on d4/f4 are not capturable")
p = pos({"d4": [gm]})
ok(sorted(notation(p)) == ["d4-c5", "d4-e5"], "a man steps forward only")

# a Dame flies and is blocked by any column
p = pos({"d4": [gd], "f6": [gm], "b2": [gm]})
ok(sorted(m for m in notation(p) if m.startswith("d4"))
   == ["d4-a7", "d4-b6", "d4-c3", "d4-c5", "d4-e3", "d4-e5", "d4-f2", "d4-g1"],
   "a Dame slides any distance and stops in front of any column: b2 cuts her "
   "diagonal after c3 and f6 cuts it after e5, the other two run to the edge")

# a Dame capture outranks a man capture
p = pos({"a1": [gd], "c3": [bm], "e5": [gm], "f6": [bm]})
ok(all(mv.startswith("a1") for mv in notation(p)),
   "a capture by a Dame takes precedence over a capture by a man")
ok("e5xg7" not in notation(p), "the man's capture is suppressed while a Dame can take")

# nearest first
p = pos({"d4": [gd], "c5": [bm], "g7": [bm]})
ok(list(notation(p)) == ["d4xb6"],
   "a Dame must capture the nearest piece first (c5 at 1, not g7 at 3)")
p = pos({"e1": [gd], "d2": [bm], "f2": [bm]})
ok(sorted(notation(p)) == ["e1xc3", "e1xg3"],
   "two capturable pieces at equal distance: the Dame may choose")

# stop immediately behind the LAST piece taken ...
p = pos({"a1": [gd], "c3": [bm]})
ok(list(notation(p)) == ["a1xd4"],
   "a Dame must stop immediately behind the piece she took (not e5/f6/g7/h8)")
# ... but landings INSIDE a chain are free
p = pos({"a1": [gd], "b2": [bm], "e5": [bm]})
ok(sorted(notation(p)) == ["a1xc3xf6", "a1xd4xf6"],
   "inside a chain the Dame may fly past (jumping b2 she may land on c3 OR on "
   "d4), but she must finish on f6, right behind the last piece taken")

# only the TOP piece is captured; the rest stays and changes hands
p = pos({"c3": [gm], "d4": [bm, gm, bm]})
s = G.apply_move(p, notation(p)["c3xe5"])
ok(stack(s, "d4") == [gm, bm],
   "only the top piece of the jumped column is taken; the rest stays put")
ok(M.owner(s.board[M.from_alg("d4")]) == GREEN,
   "taking the enemy top LIBERATES the friendly piece under it")
ok(stack(s, "e5") == [gm, bm],
   "the prisoner goes to the BOTTOM of the capturing column")

# a column moves as a unit and may not be split
p = pos({"c3": [gm, bm, bm]})
s = G.apply_move(p, notation(p)["c3-d4"])
ok(stack(s, "d4") == [gm, bm, bm] and not s.board.get(M.from_alg("c3")),
   "a column always moves as one unit")

# a square already jumped may not be jumped again in the same move
p = pos({"a1": [gd], "b2": [bm, bm, bm]})
ok(list(notation(p)) == ["a1xc3"],
   "a Dame may not re-jump a tower she has already jumped this move")

# promotion of the top piece only, on a quiet move
p = pos({"c7": [gm, bm]})
s = G.apply_move(p, notation(p)["c7-d8*D"])
ok(stack(s, "d8") == [gd, bm], "only the TOP piece of a column promotes")
p = pos({"c7": [bm]}, to_move=BLACK)
ok("c7-b6" in notation(p) and "c7-b6*D" not in notation(p),
   "Black promotes on row 1, not on row 8")

# the no-progress counter measures plies with NO capture and NO promotion
p = pos({"c3": [gm], "d4": [bm], "a1": [gm]}, since=17)
ok(G.apply_move(p, notation(p)["c3xe5"]).since == 0,
   "a capture resets the no-progress counter")
p = pos({"c7": [gm], "a1": [gm]}, since=17)
ok(G.apply_move(p, notation(p)["c7-d8*D"]).since == 0,
   "a promotion resets the no-progress counter")
ok(G.apply_move(p, notation(p)["a1-b2"]).since == 18,
   "a quiet move advances the no-progress counter")

# --------------------------------------------------------------------------
# 7. Ending, scoring, draws -- and a decisive result outranking every counter
# --------------------------------------------------------------------------
# Black's lone man on h8 is walled in: g7 is occupied and the square behind it
# (f6) is occupied too, so he can neither step nor jump.
BLOCKADE = {"a1": [gm], "f6": [gm], "g7": [gm], "h8": [bm]}
p = pos(BLOCKADE)
s = G.apply_move(p, notation(p)["a1-b2"])
ok(s.winner == GREEN and G.is_terminal(s) and G.returns(s) == [1.0, -1.0],
   "a player with no legal move loses (blockade)")
ok(G.dames(s) == 0 and G.score(s) == 0.5,
   "the house rule: a win with no promotion anywhere scores 1/2 point")
p = pos({"a1": [gm], "f6": [gd], "g7": [gm], "h8": [bm]})
s = G.apply_move(p, notation(p)["a1-b2"])
ok(s.winner == GREEN and G.score(s) == 1.0, "one Dame on the board = 1 point")

p = pos({"c3": [gm], "d4": [bm]})           # Green takes Black's last free piece
s = G.apply_move(p, notation(p)["c3xe5"])
ok(s.winner == GREEN and not s.board.get(M.from_alg("d4")),
   "owning every column ends the game")

# DECISIVE RESULT OUTRANKS THE DRAW COUNTERS (all three, together)
p = pos(BLOCKADE, since=M.NO_PROGRESS_DRAW - 1, ply=M.PLY_CAP - 1)
p.reps = {G._key(p): 2}
s = G.apply_move(p, notation(p)["a1-b2"])
poisoned = dict(s.reps)
poisoned[G._key(s)] = 9
s.reps = poisoned
s.since = 10 ** 6
s.ply = 10 ** 9
ok(s.winner == GREEN, "the win is recorded even as every draw counter trips")
ok(G.is_terminal(s) and not G._draw(s) and G.returns(s) == [1.0, -1.0],
   "a decisive result OUTRANKS the no-progress, repetition and ply-cap counters")

# genuine draws really are 0-0
p = pos({"a1": [gd], "h8": [bd]}, since=M.NO_PROGRESS_DRAW - 1)
s = G.apply_move(p, notation(p)["a1-b2"])
ok(s.winner is None and G.is_terminal(s) and G.returns(s) == [0.0, 0.0]
   and G.legal_moves(s) == [],
   "100 plies with no capture and no promotion is an honest 0-0 draw")
p = pos({"a1": [gd], "h8": [bd]})
p.reps = {G._key(p): 2}
s = G.apply_move(p, notation(p)["a1-b2"])
s.reps[G._key(s)] = 3
ok(G.is_terminal(s) and s.winner is None and G.returns(s) == [0.0, 0.0],
   "threefold repetition is an honest 0-0 draw")
p = pos({"a1": [gd], "h8": [bd]}, ply=M.PLY_CAP - 1)
s = G.apply_move(p, notation(p)["a1-b2"])
ok(G.is_terminal(s) and s.winner is None, "the hard ply cap draws")

# the repetition KEY must separate the two sides to move and the whole tower
# (a key that forgets either one manufactures threefold draws out of thin air)
a = pos({"a1": [gd], "h8": [bd]}, to_move=GREEN)
b = pos({"a1": [gd], "h8": [bd]}, to_move=BLACK)
ok(G._key(a) != G._key(b),
   "the repetition key distinguishes the side to move")
ok(G._key(pos({"c3": [gm, bm]})) != G._key(pos({"c3": [gm]})),
   "the repetition key sees the whole column, not just its top")
ok(G._key(pos({"c3": [gm, bm]})) != G._key(pos({"c3": [bm, gm]})),
   "the repetition key sees the ORDER of a column")
# ... and apply_move must not hand the child a dict ALIASED to the parent's:
# the bot explores many children of one live state, and a shared counter would
# poison the real game's repetition count.
p = pos({"a1": [gd], "h8": [bd]})
before = dict(p.reps)
kids = [G.apply_move(p, m) for m in G.legal_moves(p)]
ok(p.reps == before, "apply_move does not mutate the parent's repetition counter")
ok(all(k.reps is not p.reps for k in kids)
   and max(sum(v for v in k.reps.values()) for k in kids) == sum(before.values()) + 1,
   "each child gets its OWN repetition counter (siblings do not accumulate)")

# --------------------------------------------------------------------------
# 8. serialize / deserialize  (STATE level, plus a dropped-field mutation)
# --------------------------------------------------------------------------
rng = random.Random(4)
s = G.initial_state()
checked = 0
for _ in range(120):
    if G.is_terminal(s):
        break
    s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    d = G.serialize(s)
    ok(sorted(d) == ["board", "ply", "reps", "since", "to_move", "winner"],
       "serialize() emits exactly the six state fields")
    ok(G.deserialize(d) == s, "deserialize(serialize(state)) == state")
    checked += 1
ok(checked > 40, "serialize round-trip exercised on %d positions" % checked)
# mutation: dropping any single field must be *detected* by that round-trip
d = G.serialize(s)
for k in ("board", "to_move", "since", "ply", "reps", "winner"):
    mut = dict(d)
    if k == "board":
        mut["board"] = {kk: vv for i, (kk, vv) in enumerate(d["board"].items()) if i}
    elif k == "to_move":
        mut["to_move"] = 1 - d["to_move"]
    elif k == "winner":
        mut["winner"] = GREEN if d["winner"] is None else None
    elif k == "reps":
        mut["reps"] = {}
    else:
        mut[k] = d[k] + 1
    ok(G.deserialize(mut) != s,
       "a corrupted '%s' field is caught by the state-level round-trip" % k)

# --------------------------------------------------------------------------
# 9. Random play: invariants, termination, heuristic shape
# --------------------------------------------------------------------------
rng = random.Random(99)
lengths, results = [], {None: 0, GREEN: 0, BLACK: 0}
for _ in range(40):
    s = G.initial_state()
    while not G.is_terminal(s):
        ok(sum(len(c) for c in s.board.values()) == 24, "24 pieces at all times")
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        if s.ply > M.PLY_CAP + 5:
            ok(False, "a random game ran past the ply cap")
            break
    lengths.append(s.ply)
    results[s.winner] += 1
    ok(G.legal_moves(s) == [], "a terminal state offers no moves")
    r = G.returns(s)
    ok(len(r) == 2 and abs(r[0] + r[1]) < 1e-9, "returns are two opposite payoffs")
ok(max(lengths) < M.PLY_CAP,
   "no random game reached the ply cap (longest %d of %d)" % (max(lengths), M.PLY_CAP))
ok(results[GREEN] and results[BLACK], "both seats win random games")

h = G.heuristic(G.initial_state())
ok(isinstance(h, list) and len(h) == 2 and abs(h[0]) <= 1.0,
   "heuristic() returns a LIST of num_players payoffs")
ok(abs(h[0]) < 1e-9, "the opening position is heuristically even")
p = pos({"a1": [gd], "c3": [bm]})
ok(G.heuristic(p)[0] > 0, "heuristic prefers the side with the live Dame")

# render shape (a RenderSpec bug is invisible to validate)
spec = G.render(G.initial_state())
ok(spec["board"] == {"type": "square", "width": 8, "height": 8}, "board spec")
ok(all(set(pc) == {"cell", "owner", "stack", "label"} for pc in spec["pieces"]),
   "every rendered piece carries cell/owner/stack/label")
ok(all(isinstance(pc["stack"], list) and all(isinstance(o, int) for o in pc["stack"])
       for pc in spec["pieces"]), "stack is a list of owner ints, bottom -> top")
# (deliberately NOT a palindrome: Board.jsx draws stack[-1] as the top band, so a
# reversed list would silently draw every tower upside down)
p = pos({"c3": [gd, bm, bm]})
pc = [x for x in G.render(p)["pieces"] if x["cell"] == M.cid(M.from_alg("c3"))][0]
ok(pc["stack"] == [BLACK, BLACK, GREEN] and pc["owner"] == GREEN and pc["label"] == "D",
   "a 3-tower renders bottom->top (Board.jsx draws stack[-1] as the top band, and "
   "the top band carries the owner colour + the Dame's D)")
ok(pc["stack"][-1] == M.owner(p.board[M.from_alg("c3")]),
   "the LAST entry of the rendered stack is the column's owner, not the first")
p = pos({"c3": [bm, gm, gm]})
pc = [x for x in G.render(p)["pieces"] if x["cell"] == M.cid(M.from_alg("c3"))][0]
ok(pc["stack"] == [GREEN, GREEN, BLACK] and pc["owner"] == BLACK and pc["label"] == "",
   "a Black-topped tower renders bottom->top with no D")

# --------------------------------------------------------------------------
# 10. Differential vs an INDEPENDENT implementation (flat board, iterative)
# --------------------------------------------------------------------------
DIRS = ((1, 1), (-1, 1), (1, -1), (-1, -1))


def _flat(state):
    b = [None] * 64
    for (c, r), col in state.board.items():
        b[8 * r + c] = [(0 if o == GREEN else 2) + (1 if k else 0) for (o, k) in col]
    return b


def _side(v):
    return GREEN if v < 2 else BLACK


def _lady(v):
    return v % 2 == 1


def _ok(c, r):
    return 0 <= c < 8 and 0 <= r < 8 and (c + r) % 2 == 0


def _jumps(b, sq, me, jumped):
    c, r = sq
    col = b[8 * r + c]
    out = []
    if not _lady(col[-1]):
        dr = 1 if me == GREEN else -1
        for dc in (1, -1):
            over, land = (c + dc, r + dr), (c + 2 * dc, r + 2 * dr)
            if not _ok(*land) or b[8 * land[1] + land[0]] is not None:
                continue
            oc = b[8 * over[1] + over[0]] if _ok(*over) else None
            if oc is None or _side(oc[-1]) == me or over in jumped:
                continue
            out.append((over, (dc, dr), [land]))
        return out
    tagged = []
    for d in DIRS:
        x, y, n = c + d[0], r + d[1], 1
        while _ok(x, y) and b[8 * y + x] is None:
            x, y, n = x + d[0], y + d[1], n + 1
        if not _ok(x, y):
            continue
        oc = b[8 * y + x]
        if _side(oc[-1]) == me or (x, y) in jumped:
            continue
        lands, p, q = [], x + d[0], y + d[1]
        while _ok(p, q) and b[8 * q + p] is None:
            lands.append((p, q))
            p, q = p + d[0], q + d[1]
        if lands:
            tagged.append((n, ((x, y), d, lands)))
    if not tagged:
        return []
    lo = min(t[0] for t in tagged)
    return [t[1] for t in tagged if t[0] == lo]


def _seqs(b, start, me):
    """Complete capture sequences AND the board each one leaves behind, so the
    differential covers apply_move (a code path of its own) and not just movegen."""
    done, work = [], [(b, start, [start], frozenset())]
    while work:
        bb, sq, path, jumped = work.pop()
        for over, d, lands in _jumps(bb, sq, me, jumped):
            behind = (over[0] + d[0], over[1] + d[1])
            for land in lands:
                nb = [None if x is None else list(x) for x in bb]
                col = nb[8 * sq[1] + sq[0]]
                nb[8 * sq[1] + sq[0]] = None
                oc = nb[8 * over[1] + over[0]]
                col = [oc.pop()] + col
                if not oc:
                    nb[8 * over[1] + over[0]] = None
                nb[8 * land[1] + land[0]] = col
                if not _lady(col[-1]) and land[1] == (7 if me == GREEN else 0):
                    col[-1] += 1                       # crowned, and the move ends
                    done.append((path + [land], nb))
                    continue
                nj = jumped | {over}
                if _jumps(nb, land, me, nj):
                    work.append((nb, land, path + [land], nj))
                elif land == behind:
                    done.append((path + [land], nb))
    return done


def _quiet(b, i, c, r, x, y, me):
    nb = [None if v is None else list(v) for v in b]
    col = nb[8 * r + c]
    nb[8 * r + c] = None
    if not _lady(col[-1]) and y == (7 if me == GREEN else 0):
        col = col[:-1] + [col[-1] + 1]
    nb[8 * y + x] = col
    return nb


def _alt_moves(b, me):
    """{move string: the board it leaves} -- movegen AND application."""
    dame_c, man_c = [], []
    for i in range(64):
        col = b[i]
        if col is None or _side(col[-1]) != me:
            continue
        (dame_c if _lady(col[-1]) else man_c).extend(_seqs(b, (i % 8, i // 8), me))
    if dame_c or man_c:
        return {">".join("%d,%d" % p for p in path): nb
                for path, nb in (dame_c or man_c)}
    out = {}
    for i in range(64):
        col = b[i]
        if col is None or _side(col[-1]) != me:
            continue
        c, r = i % 8, i // 8
        if _lady(col[-1]):
            for dc, dr in DIRS:
                x, y = c + dc, r + dr
                while _ok(x, y) and b[8 * y + x] is None:
                    out["%d,%d>%d,%d" % (c, r, x, y)] = _quiet(b, i, c, r, x, y, me)
                    x, y = x + dc, y + dr
        else:
            dr = 1 if me == GREEN else -1
            for dc in (1, -1):
                x, y = c + dc, r + dr
                if _ok(x, y) and b[8 * y + x] is None:
                    out["%d,%d>%d,%d" % (c, r, x, y)] = _quiet(b, i, c, r, x, y, me)
    return out


def cross_check(s):
    """Compare the whole move list AND every resulting board.  Returns #moves."""
    alt, eng = _alt_moves(_flat(s), s.to_move), set(G.legal_moves(s))
    if set(alt) != eng:
        ok(False, "independent generator disagrees at ply %d: only-engine=%s "
                  "only-alt=%s" % (s.ply, sorted(eng - set(alt))[:4],
                                   sorted(set(alt) - eng)[:4]))
        return -1
    for mv in eng:
        if _flat(G.apply_move(s, mv)) != alt[mv]:
            ok(False, "apply_move disagrees with the independent applier on %s "
                      "(%s) at ply %d" % (mv, G.describe_move(s, mv), s.ply))
            return -1
    return len(eng)


rng = random.Random(2024)
positions = applied = 0
for _ in range(25):
    s = G.initial_state()
    while not G.is_terminal(s):
        n = cross_check(s)
        positions += 1
        if n < 0:
            break
        applied += n
        s = G.apply_move(s, rng.choice(sorted(G.legal_moves(s))))
# ... and from the four puzzle diagrams, where the towers are tall and Dames abound
for a in (P1, P2, P3, P4):
    for mover in (GREEN, BLACK):
        s = pos(a, to_move=mover)
        for _ in range(12):
            if G.is_terminal(s):
                break
            n = cross_check(s)
            positions += 1
            if n < 0:
                break
            applied += n
            s = G.apply_move(s, rng.choice(sorted(G.legal_moves(s))))
ok(positions > 1500 and applied > 8000,
   "independent cross-check covered %d positions / %d move RESULTS" % (positions, applied))

# --------------------------------------------------------------------------
print("neue_dame selftest: %d failures" % len(FAILS))
if FAILS:
    sys.exit(1)
print("OK")
