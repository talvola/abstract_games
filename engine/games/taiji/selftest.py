#!/usr/bin/env python3
"""Taiji correctness anchors -- pure stdlib, run by tests/test_games.py.

Two independent anchors:

1. The designer's OWN worked example.  The figure on page 1 of
   https://nestorgames.com/rulebooks/TAIJI_EN.pdf shows a finished 9x9 game
   captioned "Type = 2 groups.  Light wins (6+7=13 vs 5+5=10)".  The position
   was read off that figure square by square (offline, from the embedded
   image) and is hard-coded below.  This test rebuilds it by finding a real
   domino decomposition of the 70 stones and PLAYING those 35 placements
   through `apply_move`, then checks the resulting position is terminal and
   scores exactly what the designer says it does.  It pins, all at once: the
   domino shape, orthogonal-only group connectivity (an 8-connected reading
   scores 32-25 on this same board, not 13-10), "sum the N largest groups",
   the end condition, and the winner.

2. The differential against the AbstractPlay `gameslib` reference
   implementation (`_diff_ap.py`, manual/one-time -- it needs node): 300
   random games in each of 7 (board size x scoring type) configurations,
   81,116 positions, comparing the full legal-move SET in our coordinates,
   the colour of every occupied square, the side to move, both scores,
   terminality and the winner -- 0 mismatches.  What follows re-checks the
   rules with constructed positions and invariants, without needing node.
"""

import dataclasses
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                              # noqa: E402
from agp.mcts import MCTSBot                                      # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
M = sys.modules[type(G).__module__]        # the LIVE module object
EMPTY, LIGHT, DARK = M.EMPTY, M.LIGHT, M.DARK

FAILS = []
SIZES_ALL = (7, 9, 11)             # the three published board sizes


def ok(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("FAIL:", msg)


def build(rows, size=None, groups=2, tie="dark", to_move=LIGHT):
    """Position from strings given TOP row first ('L', 'D', '.')."""
    size = size or len(rows)
    val = {".": EMPTY, "L": LIGHT, "D": DARK}
    board = [EMPTY] * (size * size)
    for i, line in enumerate(rows):
        r = size - 1 - i                              # row 0 is the BOTTOM
        for c, ch in enumerate(line):
            board[M._idx(size, c, r)] = val[ch]
    return M.TState(size=size, groups=groups, tie=tie,
                    board=tuple(board), to_move=to_move, last=None)


def show(state):
    sym = {EMPTY: ".", LIGHT: "L", DARK: "D"}
    n = state.size
    return ["".join(sym[state.board[M._idx(n, c, r)]] for c in range(n))
            for r in range(n - 1, -1, -1)]


# ==========================================================================
# 1. Board, naming, opening
# ==========================================================================
s0 = G.initial_state()
ok(s0.size == 9 and s0.groups == 2 and s0.tie == "dark",
   "default game is 9x9, 2 scoring groups, official tie-break")
ok(all(v == EMPTY for v in s0.board) and len(s0.board) == 81,
   "the 9x9 board starts empty")
ok(G.current_player(s0) == LIGHT, "Light moves first (rulebook: 'Light player starts')")

for n, want in ((7, 168), (9, 288), (11, 440)):
    s = G.initial_state(options={"size": n})
    ok(len(s.board) == n * n, f"{n}x{n} board has {n * n} squares")
    ok(len(G.legal_moves(s)) == want,
       f"{n}x{n} opening has {want} legal moves "
       f"(2 orientations x {2 * n * (n - 1)} adjacent pairs)")
# 288 on the default board is the published AbstractPlay figure for this game.

ok(M.cell_name(9, M._idx(9, 0, 0)) == "a1"
   and M.cell_name(9, M._idx(9, 8, 8)) == "i9"
   and M.cell_name(9, M._idx(9, 4, 2)) == "e3",
   "algebraic naming: a1 is bottom-left, i9 top-right (matches AbstractPlay)")
ok(all(M.parse_cell(9, M.cell_id(9, i)) == i for i in range(81)),
   "cell id <-> index round-trips on every square")
# the 11x11 board runs past 'i', so pin its file letters too (AbstractPlay's
# indexToColumnLabel gives a..k); every square must get a distinct name.
ok(M.cell_name(11, M._idx(11, 0, 0)) == "a1"
   and M.cell_name(11, M._idx(11, 10, 10)) == "k11"
   and M.cell_name(11, M._idx(11, 9, 0)) == "j1",
   "11x11 algebraic naming runs a1..k11")
for n in SIZES_ALL:
    ok(len({M.cell_name(n, i) for i in range(n * n)}) == n * n,
       f"{n}x{n}: every square has a distinct algebraic name")
    ok(all(M.parse_cell(n, M.cell_id(n, i)) == i for i in range(n * n)),
       f"{n}x{n}: cell id <-> index round-trips on every square")

# options are clamped, never trusted blindly
sx = G.initial_state(options={"size": 8, "groups": 9, "tie": "nope"})
ok((sx.size, sx.groups, sx.tie) == (9, 2, "dark"),
   "out-of-range options fall back to the 9x9 / 2-group / official defaults")

# ==========================================================================
# 2. Move generation: orthogonal adjacency, both orientations, both empty
# ==========================================================================
mv = set(G.legal_moves(s0))
ok("0,0>1,0" in mv and "1,0>0,0" in mv,
   "both orientations of a domino are offered (the mover picks which square "
   "is Light)")
ok("0,0>1,1" not in mv and "1,1>0,0" not in mv,
   "a DIAGONAL pair is not a legal placement (rulebook: horizontally or "
   "vertically adjacent)")
ok("0,0>2,0" not in mv, "the two squares must be adjacent, not merely aligned")
ok("0,0>0,0" not in mv, "a domino covers two DIFFERENT squares")
ok(len(mv) == len(G.legal_moves(s0)), "the legal-move list has no duplicates")

s1 = G.apply_move(s0, "3,4>3,5")
ok(s1.board[M._idx(9, 3, 4)] == LIGHT and s1.board[M._idx(9, 3, 5)] == DARK,
   "the FIRST cell of the move gets the Light half, the second the Dark half")
ok(s1.to_move == DARK and G.current_player(s1) == DARK, "turn passes to Dark")
ok(all(v == EMPTY for v in s0.board), "apply_move does not mutate its input")
mv1 = set(G.legal_moves(s1))
ok(not any("3,4" in m.split(">") or "3,5" in m.split(">") for m in mv1),
   "an occupied square can never be covered again")
# d5/d6 are both interior squares: 4 + 4 - 1 = 7 grid edges touch them, and
# each edge contributed two ordered pairs.
ok(len(mv1) == 288 - 14,
   "the two covered squares remove exactly their incident ordered pairs")

for m in ("3,4>3,5", "3,4>2,4", "9,0>8,0", "0,0>1,1", "0,0", "bogus"):
    try:
        G.apply_move(s1, m)
        ok(False, f"illegal move {m!r} must be rejected")
    except Exception:
        pass

# every generated move is applicable, and describe_move renders it
for m in list(mv)[:40] + list(mv)[-40:]:
    G.apply_move(s0, m)
ok(G.describe_move(s0, "0,0>1,0") == "a1(L)-b1(D)"
   and G.describe_move(s0, "1,0>0,0") == "b1(L)-a1(D)",
   "describe_move names both halves and which colour each got")

# ==========================================================================
# 3. Group scoring (constructed positions)
# ==========================================================================
#   L L L . .    Light: an L-shaped 4-group + a lone stone       -> 4, 1
#   L . . . .    Dark : a 4-group (the row plus the D below its
#   . . D D D           right end) + a lone stone                -> 4, 1
#   . . . . D
#   L . . D .    <- this D touches the one above it only DIAGONALLY
tst = build(["LLL..",
             "L....",
             "..DDD",
             "....D",
             "L..D."], size=5)
ok(M.Taiji.group_sizes(tst, LIGHT) == [4, 1],
   "Light's groups are 4 and 1 (orthogonal connectivity)")
ok(M.Taiji.group_sizes(tst, DARK) == [4, 1],
   "Dark's groups are 4 and 1; the diagonal contact does NOT connect")
diag = build(["D...", ".D..", "..D.", "...D"], size=4)
ok(M.Taiji.group_sizes(diag, DARK) == [1, 1, 1, 1],
   "a purely diagonal chain is four separate groups of one")
line = build([".....", "LLLLL", ".....", ".....", "....."], size=5)
ok(M.Taiji.group_sizes(line, LIGHT) == [5], "a full row is one group of five")

for n, want in ((1, 4), (2, 5), (3, 5)):
    st = build(["LLL..", "L....", "..DDD", "....D", "L..D."], size=5, groups=n)
    ok(M.Taiji.score(st, LIGHT) == want,
       f"scoring type {n}: Light scores {want} (groups 4 + 1)")
ok(M.Taiji.scores(build(["LLL..", "L....", "..DDD", "....D", "L..D."],
                        size=5, groups=2)) == (5, 5),
   "scores() returns (Light, Dark) and is symmetric on this position")

# ==========================================================================
# 4. THE DESIGNER'S WORKED EXAMPLE (TAIJI_EN.pdf, page 1 figure)
#    "9x9 game.  Type = 2 groups.  Light wins (6+7=13 vs 5+5=10)"
# ==========================================================================
FIGURE = ["DL.LD.DL.",
          "DLDL.LDDL",
          "LLDDDL.LL",
          "LDLDLLDDD",
          "DDLL.LLD.",
          ".DLDDD.LL",
          "LLLDLLDDD",
          "DDDLLDLD.",
          ".LDDLDLLD"]           # top row first, as printed
fig = build(FIGURE, size=9, groups=2)
ok(sum(1 for v in fig.board if v == LIGHT) == 35
   and sum(1 for v in fig.board if v == DARK) == 35
   and sum(1 for v in fig.board if v == EMPTY) == 11,
   "the figure holds 35 Light + 35 Dark stones (35 dominoes) and 11 empties")
ok(M.Taiji.group_sizes(fig, LIGHT) == [7, 6, 5, 5, 3, 3, 2, 2, 1, 1],
   "figure: Light's groups are 7,6,5,5,3,3,2,2,1,1")
ok(M.Taiji.group_sizes(fig, DARK) == [5, 5, 4, 4, 4, 4, 3, 2, 2, 1, 1],
   "figure: Dark's groups are 5,5,4,4,4,4,3,2,2,1,1")
ok(M.Taiji.scores(fig) == (13, 10),
   "figure scores 13-10 with 2 groups, exactly the rulebook's 6+7 vs 5+5")
ok(G.is_terminal(fig) and G.legal_moves(fig) == [],
   "the figure is a finished game: no two empty squares are adjacent")
ok(G.returns(fig) == [1.0, -1.0], "the rulebook's caption: Light wins")
ok(M.Taiji.scores(build(FIGURE, size=9, groups=1)) == (7, 5)
   and M.Taiji.scores(build(FIGURE, size=9, groups=3)) == (18, 14),
   "the same figure scores 7-5 with 1 group and 18-14 with 3 groups")


def decompose(state):
    """Find a real domino decomposition of a finished position: a perfect
    matching of Light stones to orthogonally adjacent Dark stones."""
    n = state.size
    nb = M.NEIGHBOURS[n]
    lights = [i for i, v in enumerate(state.board) if v == LIGHT]
    darks = {i for i, v in enumerate(state.board) if v == DARK}
    match = {}                                     # dark idx -> light idx

    def aug(l, seen):
        for d in nb[l]:
            if d not in darks or d in seen:
                continue
            seen.add(d)
            if d not in match or aug(match[d], seen):
                match[d] = l
                return True
        return False

    for l in lights:
        if not aug(l, set()):
            return None
    if len(match) != len(lights) or len(match) != len(darks):
        return None
    return [(l, d) for d, l in match.items()]


pairs = decompose(fig)
ok(pairs is not None and len(pairs) == 35,
   "the figure position is REACHABLE: its 70 stones split into 35 dominoes")
if pairs:
    s = G.initial_state(options={"size": 9, "groups": 2})
    for k, (l, d) in enumerate(pairs):
        m = f"{M.cell_id(9, l)}>{M.cell_id(9, d)}"
        ok(m in G.legal_moves(s), f"replaying the figure: move {k} is legal")
        s = G.apply_move(s, m)
    ok(show(s) == FIGURE, "replaying the 35 dominoes reproduces the figure")
    ok(G.is_terminal(s) and M.Taiji.scores(s) == (13, 10)
       and G.returns(s) == [1.0, -1.0],
       "the replayed game ends 13-10 for Light, played out through apply_move")
    ok(s.to_move == DARK,
       "35 dominoes = 18 by Light and 17 by Dark, so Dark is on turn at the end")

# ==========================================================================
# 5. End condition and termination
# ==========================================================================
# A board whose only empties are isolated is over even though squares remain.
# (`is_terminal` / `legal_moves` are pure board predicates, so these small
# synthetic boards exercise them directly; only 7/9/11 are playable sizes.)
done = build(["LDLDL",
              "DLDLD",
              "LD.DL",
              "DLDLD",
              "LDLDL"], size=5)
ok(G.is_terminal(done) and G.legal_moves(done) == [],
   "an isolated empty square ends the game (12 Light + 12 Dark, 1 free)")
alive = build(["LDLDL",
               "DLDLD",
               "LD..L",
               "DLDLD",
               "LDLDL"], size=5)
ok(not G.is_terminal(alive) and len(G.legal_moves(alive)) == 2,
   "one adjacent empty pair left -> exactly 2 moves (the two orientations)")
ok(not G.is_terminal(s0), "the empty board is not terminal")

rng = random.Random(20080101)
lengths = {}
tie_count = decisive = 0
for n, cap in ((7, 24), (9, 40), (11, 60)):
    longest = 0
    for _ in range(60):
        s = G.initial_state(options={"size": n})
        empt0 = sum(1 for v in s.board if v == EMPTY)
        plies = 0
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            ok(ms, "a non-terminal position always has a legal move")
            s = G.apply_move(s, rng.choice(ms))
            plies += 1
            empt = sum(1 for v in s.board if v == EMPTY)
            ok(empt == empt0 - 2, "every placement fills exactly two squares")
            empt0 = empt
            ok(plies <= cap, f"a {n}x{n} game cannot exceed {cap} plies")
        longest = max(longest, plies)
        lt, dk = M.Taiji.scores(s)
        if lt == dk:
            tie_count += 1
        else:
            decisive += 1
        # the stone counts must stay balanced: one of each colour per move
        ok(sum(1 for v in s.board if v == LIGHT)
           == sum(1 for v in s.board if v == DARK) == plies,
           "each placement adds exactly one Light and one Dark stone")
    lengths[n] = longest
print(f"  random games: longest {lengths}, "
      f"{tie_count} ties / {tie_count + decisive} games "
      f"({tie_count / (tie_count + decisive):.1%})")

# ==========================================================================
# 6. Result, and the official tie-break
# ==========================================================================
# A finished checkerboard: every stone is its own group, so both sides score
# 1 + 1 = 2 with the standard 2-group rule.
tied = build(["LDLDL",
              "DLDLD",
              "LD.DL",
              "DLDLD",
              "LDLDL"], size=5, groups=2)
ok(M.Taiji.scores(tied) == (2, 2) and G.is_terminal(tied),
   "constructed terminal position with equal scores")
ok(G.returns(tied) == [-1.0, 1.0],
   "equal scores: Dark wins by the rulebook's tie-break "
   "('In case of a tie, the Dark player wins')")
ok(G.returns(M.TState(size=tied.size, groups=2, tie="draw", board=tied.board, to_move=tied.to_move, last=None))
   == [0.0, 0.0],
   "with the 'draw' option an equal score is an honest draw (0, 0)")
# The tie-break must NEVER touch a decided game (a decisive result outranks it).
checked = 0
for n in (7, 9):
    for _ in range(40):
        s = G.initial_state(options={"size": n})
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        lt, dk = M.Taiji.scores(s)
        want = [1.0, -1.0] if lt > dk else [-1.0, 1.0] if dk > lt else None
        for opt in ("dark", "draw"):
            got = G.returns(dataclasses.replace(s, tie=opt))
            if want is not None:
                ok(got == want,
                   f"a decisive {lt}-{dk} result is unaffected by tie={opt!r}")
                checked += 1
            else:
                ok(got == ([-1.0, 1.0] if opt == "dark" else [0.0, 0.0]),
                   f"a tied result follows tie={opt!r}")
ok(checked > 0, "decisive games were actually reached and re-scored")
for s in (s0, s1, fig, tied):
    r = G.returns(s)
    ok(len(r) == 2 and all(isinstance(x, float) for x in r),
       "returns() is a 2-list of finite numbers")

# ==========================================================================
# 7. Persistence -- round-trip at the STATE level, and no dropped field
# ==========================================================================
samples = [s0, s1, fig, tied,
           G.initial_state(options={"size": 7, "groups": 1, "tie": "draw"}),
           G.initial_state(options={"size": 11, "groups": 3})]
for s in samples:
    d = G.serialize(s)
    ok(sorted(d) == ["board", "groups", "last", "size", "tie", "to_move"],
       f"serialize() key set is exactly the state's fields (got {sorted(d)})")
    ok(G.deserialize(d) == s, "deserialize(serialize(s)) == s (STATE level)")
    ok(json.loads(json.dumps(d)) == d, "the serialized form is JSON-able")

# mutating any single serialized field must change the deserialized state --
# this is what catches a field the round-trip silently drops.
base = G.apply_move(G.apply_move(s0, "0,0>1,0"), "4,4>4,5")
d = G.serialize(base)
for key, alt in (("size", 7), ("groups", 3), ("tie", "draw"),
                 ("board", "D" + d["board"][1:]), ("to_move", 1 - d["to_move"]),
                 ("last", None)):
    if key == "size":                       # size must stay consistent
        continue
    mutated = dict(d)
    mutated[key] = alt
    ok(G.deserialize(mutated) != base,
       f"a change to serialized {key!r} survives deserialize (field not dropped)")
small = G.serialize(G.initial_state(options={"size": 7}))
ok(G.deserialize(small).size == 7 and len(G.deserialize(small).board) == 49,
   "the board size round-trips (a 7x7 game does not come back as 9x9)")

# ==========================================================================
# 8. Render spec
# ==========================================================================
spec = G.render(s0)
ok(spec["board"] == {"type": "square", "width": 9, "height": 9},
   "render(): 9x9 square board")
ok(spec["pieces"] == [], "render(): the opening board has no pieces")
spec1 = G.render(s1)
ok({(p["cell"], p["owner"]) for p in spec1["pieces"]}
   == {("3,4", LIGHT), ("3,5", DARK)},
   "render(): pieces carry the COLOUR as owner (0 = Light, 1 = Dark)")
ok(sorted(h["cell"] for h in spec1["highlights"]) == ["3,4", "3,5"],
   "render(): the last domino is highlighted")
ok("Dark to place" in spec1["caption"] and "Light 1 - Dark 1" in spec1["caption"],
   "render(): the caption shows the side to move and the running score")
ok("Light wins" in G.render(fig)["caption"], "render(): finished game captions the result")
ok("Dark wins the tie-break" in G.render(tied)["caption"],
   "render(): a tie caption names the tie-break")
for s in samples:
    sp = G.render(s)
    json.dumps(sp)
    n = s.size
    ok(all(p["cell"] in {M.cell_id(n, i) for i in range(n * n)}
           and p["owner"] in (0, 1) for p in sp["pieces"]),
       "render(): every piece sits on a real cell with owner 0/1")

# The declared board must TRACK the option, on every size -- Board.jsx builds
# its cell set from board.width/height and joins pieces to it by cell id, so a
# board declared too small silently SWALLOWS every piece outside it (the two
# outer files/ranks of an 11x11 game would simply never appear, and could never
# be clicked).  Reach a far-corner position through apply_move so the check bites
# on the corner square, which is exactly what a wrong size loses first.
for n in SIZES_ALL:
    st = G.initial_state(options={"size": n})
    for mvc in (f"{n - 1},{n - 1}>{n - 2},{n - 1}", "0,0>1,0"):
        ok(mvc in G.legal_moves(st), f"{n}x{n}: corner placement {mvc} is legal")
        st = G.apply_move(st, mvc)
    sp = G.render(st)
    ok(sp["board"] == {"type": "square", "width": n, "height": n},
       f"render(): a {n}x{n} game declares a {n}x{n} board (got {sp['board']})")
    W, H = sp["board"]["width"], sp["board"]["height"]
    cells = [tuple(int(x) for x in p["cell"].split(",")) for p in sp["pieces"]]
    ok(len(cells) == 4 and all(0 <= c < W and 0 <= r < H for c, r in cells),
       f"render(): all 4 stones of a {n}x{n} game lie inside the declared board")
    ok((n - 1, n - 1) in cells,
       f"render(): the far corner {n - 1},{n - 1} is inside the declared board")
    ok(all(0 <= int(h["cell"].split(",")[0]) < W
           and 0 <= int(h["cell"].split(",")[1]) < H
           for h in sp.get("highlights", [])),
       f"render(): {n}x{n} highlights lie inside the declared board")

# The caption must tell the player WHICH click picks the light half -- choosing
# the orientation IS the move, and nothing else on screen conveys it.
live = G.render(G.initial_state())["caption"]
ok("LIGHT" in live and "DARK" in live and live.index("LIGHT") < live.index("DARK"),
   f"render(): a live caption says to click the LIGHT square first (got {live!r})")
ok("LIGHT" not in G.render(fig)["caption"],
   "render(): the click hint is dropped once the game is over")

# ==========================================================================
# 9. Bot plumbing -- heuristic shape, forced at the rollout cutoff
# ==========================================================================
h = G.heuristic(fig)
ok(isinstance(h, list) and len(h) == 2
   and abs(h[0] + h[1]) < 1e-9 and all(-1.0 <= x <= 1.0 for x in h),
   "heuristic() returns a 2-list of bounded, zero-sum payoffs")
bot = MCTSBot(random.Random(5), iterations=30, max_rollout=4)
mv_bot = bot.select(G, G.initial_state(options={"size": 11}))
ok(mv_bot in G.legal_moves(G.initial_state(options={"size": 11})),
   "MCTSBot with max_rollout=4 (forcing the heuristic cutoff) returns a legal move")

print(f"taiji selftest: {len(FAILS)} failure(s)")
if FAILS:
    sys.exit(1)
