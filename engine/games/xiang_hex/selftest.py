"""Xiang Hex selftest -- pure standard library.

Anchors, in order of strength:

0. The Game Courier preset's own board string, parsed here: it must reproduce
   the 79-cell shape AND the whole opening array, a second primary source for
   the setup that is independent of the diagram.
1. Every one of the EIGHT movement diagrams on the chessvariants.com rules page
   (Soldier before/after the river, Horse with its lamed leg, Chariot, Cannon
   with its blocked slide and its screen capture, Elephant blocked by the river,
   Mandarin, General pinned off the enemy General's file) reproduced
   cell-for-cell.  Those diagrams and Fergus Duniho's rule-enforcing Game
   Courier GAME code are the two primary sources, and they agree.
2. Frozen perft 30 / 874 / 28,968 from the opening array -- all three also
   recomputed inside the GAME-code reimplementation itself
   (`_diff_gamecourier.py`, which additionally agrees move-for-move over 10,675
   positions; run it by hand, see rules.md).
3. The board itself: 79 cells, the file lengths, the river, the two palaces,
   and the proof that only the FILE can ever join the two palaces (which is
   what makes "flying general" a file rule).
4. The three unusual endings -- stalemate loses, repetition loses, and the
   no-river-crossers draw -- each REACHED through apply_move, never hand-built,
   plus the PRECEDENCE between them: a player with no legal move loses, and that
   stays true with the repetition counter and the ply cap both tripped.
5. Check DETECTION (`_attacked`), which is a separate code path from move
   generation and therefore needs its own tests for the Horse's lame leg and the
   Soldier's river gate.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir                          # noqa: E402

HERE = Path(__file__).resolve().parent
MAN, GAME = load_from_dir(HERE)
G = sys.modules[type(GAME).__module__]
cn, pn = G.cell_name, G.parse_name

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}\n     got : {got}\n     want: {want}")


def state(place, to_move):
    """A position from {cell name: (seat, letter)} -- no Generals required."""
    bd = {pn(k): v for k, v in place.items()}
    s = G.GState(board=bd, to_move=to_move)
    s.hist = (G._poskey(bd, to_move),)
    return s


def dests(place, to_move, frm):
    s = state(place, to_move)
    f = pn(frm)
    return sorted(cn(t) for (a, t) in GAME._legal(s) if a == f)


# ---------------------------------------------------------------- 3. board --
check("cell count", len(G.CELLS), 79)
check("file lengths",
      [sum(1 for q, r in G.CELLS if q == Q) for Q in range(-4, 5)],
      [7, 8, 9, 10, 11, 10, 9, 8, 7])
check("round-trip naming",
      all(pn(cn(c)) == c for c in G.CELLS), True)
# The rules page: "the fourth cell of the first and ninth file, the fifth cell
# of the third and seventh file and the sixth cell of the center file".
check("river", sorted(cn(c) for c in G.RIVER), ["a4", "c5", "e6", "g5", "i4"])
# "the first three cells of the center file and the first two cells which flank"
check("Red palace", sorted(cn(c) for c in G.PALACE[0]),
      ["d1", "d2", "e1", "e2", "e3", "f1", "f2"])
check("Blue palace", sorted(cn(c) for c in G.PALACE[1]),
      ["d10", "d9", "e10", "e11", "e9", "f10", "f9"])
check("palaces are 180 deg rotations",
      {(-q, -r) for q, r in G.PALACE[0]}, set(G.PALACE[1]))
check("river cells are their own rotation",
      {(-q, -r) for q, r in G.RIVER}, set(G.RIVER))

# Only the FILE can ever join the two palaces, which is why the flying-general
# rule is a file rule (the module relies on this).
for name, key in (("file", lambda c: c[0]),
                  ("SE line", lambda c: c[1]),
                  ("NE line", lambda c: c[0] + c[1])):
    shared = {key(c) for c in G.PALACE[0]} & {key(c) for c in G.PALACE[1]}
    check(f"palaces share a {name}", bool(shared), name == "file")

# Setup: 16 a side, an exact 180 deg rotation of each other.
s0 = GAME.initial_state()
check("piece count", len(s0.board), 32)
check("Red array",
      {cn(c): t for c, (o, t) in s0.board.items() if o == 0},
      {"a1": "C", "b1": "H", "c1": "E", "d1": "M", "e1": "G", "f1": "M",
       "g1": "E", "h1": "H", "i1": "C", "b2": "A", "h2": "A",
       "a2": "S", "c3": "S", "e4": "S", "g3": "S", "i2": "S"})
check("Blue array is Red's 180 deg rotation",
      {(-q, -r): (1 - o, t) for (q, r), (o, t) in s0.board.items() if o == 0},
      {c: p for c, p in s0.board.items() if p[0] == 1})

# The Game Courier preset's own board string -- a SECOND primary source for both
# the 79-cell shape and the whole opening array, in the preset's *global* rank
# 1-11 (its (file F, rank R) is axial (F - 4, 10 - F - R); '-' = off the board).
GC_CODE = ("rnefg/pc3f/2p3e/4p2n/6pcr/P7p/RCP6/-N2P4/--E3P2/---F3CP/"
           "----GFENR")
GC_PIECE = {"R": "C", "N": "H", "C": "A", "P": "S", "E": "E", "F": "M", "G": "G"}
gc_cells, gc_board = set(), {}
for _row, _line in enumerate(GC_CODE.split("/")):
    _rank, _f = 11 - _row, 0
    for _ch in _line:
        if _ch == "-":
            _f += 1
            continue
        for _ in range(int(_ch) if _ch.isdigit() else 1):
            _c = (_f - 4, 10 - _f - _rank)
            gc_cells.add(_c)
            if not _ch.isdigit():
                gc_board[_c] = (0 if _ch.isupper() else 1, GC_PIECE[_ch.upper()])
            _f += 1
check("preset board string: the same 79 cells", gc_cells, set(G.CELLS))
check("preset board string: the same opening array", gc_board, s0.board)
# ... and the two numbering schemes line up cell for cell: the preset's global
# rank R is this page's number n on files e-i, and n - q on files a-d.
check("GC global rank <-> per-file numbering",
      all(cn(c) == G.FILES[c[0] + 4] +
          str((6 - c[0] - c[1]) + (c[0] if c[0] < 0 else 0)) for c in G.CELLS),
      True)
check("the preset's a5 is this page's a1", cn(pn("a1")), "a1")
check("...i.e. a1 has global rank 5", 6 - pn("a1")[0] - pn("a1")[1], 5)

# ------------------------------------------ 1. the rules page's diagrams -----
# Duniho's diagrams use no Generals except in the General diagram, so neither
# do these positions (a General-less position is legal for move generation).
DIAGRAMS = [
    # SOLDIER, on its own side of the river: one step straight forward only.
    ("Soldier e4 (own side)", {"e4": (0, "S")}, 0, "e4", ["e5"]),
    # SOLDIER, standing ON the river: "upon and after entering the river step
    # one forward, right forward or left forward orthogonal, or right or left
    # diagonal".
    ("Soldier e6 (on the river)", {"e6": (0, "S")}, 0, "e6",
     ["c5", "d6", "e7", "f6", "g5"]),
    ("Blue Soldier e8 (own side)", {"e8": (1, "S")}, 1, "e8", ["e7"]),
    ("Blue Soldier e6 (on the river)", {"e6": (1, "S")}, 1, "e6",
     ["c5", "d5", "e5", "f5", "g5"]),
    # The preset gates on the DESTINATION (`rank #1`/`file #1`), so a Soldier
    # one short of the river may step forward-DIAGONALLY into it (e6/g5) --
    # but still not sideways, which would stay on its own side.  See rules.md.
    ("Soldier f5, one short of the river", {"f5": (0, "S")}, 0, "f5",
     ["e6", "f6", "g5"]),
    ("Soldier f4, two short of the river", {"f4": (0, "S")}, 0, "f4", ["f5"]),
    ("Blue Soldier f6, one short of the river", {"f6": (1, "S")}, 1, "f6",
     ["e6", "f5", "g5"]),
    # HORSE: the diagram's Cannon on e5 lames the two moves through e5, so d3
    # and f3 are missing -- the rules page names exactly those two.
    ("Horse e6, lamed by e5 and f7",
     {"e6": (0, "H"), "e5": (1, "A"), "f7": (1, "A")}, 0, "e6",
     ["b4", "b5", "c3", "c7", "d8", "f8", "g3", "g7", "h4", "h5"]),
    ("Horse e6, unobstructed (12 targets)", {"e6": (0, "H")}, 0, "e6",
     ["b4", "b5", "c3", "c7", "d3", "d8", "f3", "f8", "g3", "g7", "h4", "h5"]),
    # CHARIOT: full rays in all six orthogonal directions.
    ("Chariot e6", {"e6": (0, "C")}, 0, "e6",
     ["a2", "a6", "b3", "b6", "c4", "c6", "d5", "d6", "e1", "e2", "e3", "e4",
      "e5", "e7", "e8", "e9", "e10", "e11", "f5", "f6", "g4", "g6", "h3",
      "h6", "i2", "i6"]),
    # CANNON: e7 blocks the slide north but is the screen for a capture on e9;
    # b6 is an enemy the Cannon may NOT take, having no screen on that line.
    ("Cannon e6, screen e7, enemies e9 and b6",
     {"e6": (0, "A"), "e7": (1, "H"), "e9": (1, "H"), "b6": (1, "H")}, 0, "e6",
     ["a2", "b3", "c4", "c6", "d5", "d6", "e1", "e2", "e3", "e4", "e5", "e9",
      "f5", "f6", "g4", "g6", "h3", "h6", "i2", "i6"]),
    # ELEPHANT: only 4 of its 6 destinations -- g7 and c7 would cross the river.
    ("Elephant e5 (river-bound)", {"e5": (0, "E")}, 0, "e5",
     ["a3", "c1", "g1", "i3"]),
    # MANDARIN: a diagonal spans two cells, so from e3 only d1 and f1.
    ("Mandarin e3", {"e3": (0, "M")}, 0, "e3", ["d1", "f1"]),
    ("Mandarin e2 (palace centre) is stuck", {"e2": (0, "M")}, 0, "e2", []),
    # GENERAL: from e3 it may step to e2 and f2 but NOT to d2 -- the enemy
    # General on d10 holds the whole d file.
    ("General e3 vs enemy General d10",
     {"e3": (0, "G"), "d10": (1, "G")}, 0, "e3", ["e2", "f2"]),
    # ... and with the enemy General off the d file, d2 comes back (while f2
    # now goes, because it would face him on the f file).
    ("General e3 vs enemy General f10",
     {"e3": (0, "G"), "f10": (1, "G")}, 0, "e3", ["d2", "e2"]),
    # A piece between them unblocks the file again.
    ("General e3, enemy d10, a piece on d5",
     {"e3": (0, "G"), "d10": (1, "G"), "d5": (1, "S")}, 0, "e3",
     ["d2", "e2", "f2"]),
]
for name, place, mover, frm, want in DIAGRAMS:
    check(name, dests(place, mover, frm), sorted(want))

# Check DETECTION runs through `_attacked`, a separate code path from move
# generation, so every restriction has to hold there too or a position picks up a
# phantom check (and phantom checkmates).
# A Horse's lame leg: Red's Horse on d8 reaches e11 only while d9 is vacant.
_h = {pn("e11"): (1, "G"), pn("d8"): (0, "H")}
check("check detection: Horse with a clear leg gives check",
      G._in_check(_h, 1), True)
_hl = dict(_h)
_hl[pn("d9")] = (1, "M")
check("check detection: the SAME Horse lamed on d9 gives none",
      G._in_check(_hl, 1), False)
# A Soldier's river gate is on the destination in `_attacked` as well: a Red
# Soldier on f5 does not cover h4 sideways, but does cover the river cell e6 it
# may step into, and on the river it covers sideways along it.
check("check detection: Soldier does not cover sideways before the river",
      G._attacked({pn("f5"): (0, "S")}, pn("h4"), 0), False)
check("check detection: Soldier covers the river cell it may enter",
      G._attacked({pn("f5"): (0, "S")}, pn("e6"), 0), True)
check("check detection: Soldier on the river covers sideways along it",
      G._attacked({pn("e6"): (0, "S")}, pn("g5"), 0), True)

# The Elephant's whole world is five cells (the diagram's e5 plus its four
# destinations); the Mandarin's palace splits into two triangles plus a dead
# centre.
for seat, home in ((0, ("c1", "g1")), (1, ("c9", "g9"))):
    seen, stack = {pn(h) for h in home}, [pn(h) for h in home]
    while stack:
        c = stack.pop()
        for v, t in G.ELEPHANT:
            tgt, eye = (c[0] + t[0], c[1] + t[1]), (c[0] + v[0], c[1] + v[1])
            if (G.on_board(*tgt) and G.on_board(*eye)
                    and G._elephant_ok(seat, tgt) and tgt not in seen):
                seen.add(tgt)
                stack.append(tgt)
    check(f"Elephant range seat {seat}", sorted(cn(c) for c in seen),
          ["a3", "c1", "e5", "g1", "i3"] if seat == 0
          else ["a5", "c9", "e7", "g9", "i5"])
    check(f"Elephants never touch the river, seat {seat}",
          bool(seen & set(G.RIVER)), False)
tri = {}
for c in G.PALACE[0]:
    tri[cn(c)] = sorted(cn((c[0] + d[0], c[1] + d[1])) for d in G.DIAG
                        if (c[0] + d[0], c[1] + d[1]) in G.PALACE[0])
check("Mandarin triangles", tri,
      {"d1": ["e3", "f1"], "f1": ["d1", "e3"], "e3": ["d1", "f1"],
       "d2": ["e1", "f2"], "f2": ["d2", "e1"], "e1": ["d2", "f2"], "e2": []})

# ------------------------------------------------------------- 2. perft -----
def perft(s, d):
    mv = GAME.legal_moves(s)
    if d == 1:
        return len(mv)
    return sum(perft(GAME.apply_move(s, m), d - 1) for m in mv)


check("perft(1)", perft(s0, 1), 30)
check("perft(2)", perft(s0, 2), 874)
check("perft(3)", perft(s0, 3), 28968)
# Both Chariots are walled in at the start (an outer file's first cell has only
# three board neighbours, and all three are occupied).
check("Chariots have no opening move",
      [m for m in GAME.legal_moves(s0)
       if s0.board[tuple(map(int, m.split(">")[0].split(",")))][1] == "C"], [])

# ---------------------------------------------------------- 4. the endings --
def play(place, to_move, moves):
    s = state(place, to_move)
    for m in moves:
        s = GAME.apply_move(s, f"{pn(m[0])[0]},{pn(m[0])[1]}>"
                               f"{pn(m[1])[0]},{pn(m[1])[1]}")
    return s


# (a) CHECKMATE -- Blue's General on e11 has only e10, d10 and f10; the Chariot
# arriving on e4 checks down the e file (covering e10 too) while the d- and
# f-file Chariots hold the other two.
mate = play({"d1": (0, "G"), "e11": (1, "G"),
             "a4": (0, "C"), "d5": (0, "C"), "f5": (0, "C")},
            0, [("a4", "e4")])
check("checkmate is terminal", GAME.is_terminal(mate), True)
check("checkmate: no legal move", GAME.legal_moves(mate), [])
check("checkmate: Blue is in check", G._in_check(mate.board, 1), True)
check("checkmate: Red wins", GAME.returns(mate), [1.0, -1.0])

# (b) STALEMATE LOSES -- the Chariot reaching i6 rakes the whole d10-e10 line
# without ever touching e11 itself, so Blue's General is NOT in check yet has
# nowhere to go.
stale = play({"d1": (0, "G"), "e11": (1, "G"), "f5": (0, "C"), "i2": (0, "C")},
             0, [("i2", "i6")])
check("stalemate is terminal", GAME.is_terminal(stale), True)
check("stalemate: no legal move", GAME.legal_moves(stale), [])
check("stalemate: Blue is NOT in check", G._in_check(stale.board, 1), False)
check("stalemate LOSES for the stalemated player", GAME.returns(stale),
      [1.0, -1.0])

# (c) REPETITION LOSES -- both Chariots step out and back; the fourth ply
# recreates the starting position, so Blue, who made it, loses.
rep_start = {"d1": (0, "G"), "e11": (1, "G"), "a3": (0, "C"), "a5": (1, "C")}
rep = play(rep_start, 0,
           [("a3", "b3"), ("a5", "b5"), ("b3", "a3"), ("b5", "a5")])
check("repetition is terminal", GAME.is_terminal(rep), True)
check("repetition: no moves offered", GAME.legal_moves(rep), [])
check("repetition: the repeating player loses", GAME.returns(rep),
      [1.0, -1.0])
check("repetition reason", GAME._over(rep)[0], "repetition")
# Three of the four plies are NOT terminal.
part = play(rep_start, 0, [("a3", "b3"), ("a5", "b5"), ("b3", "a3")])
check("no premature repetition", GAME.is_terminal(part), False)
# A capture wipes the history (no earlier position can recur once material has
# gone), and so does a Soldier move that changes its distance from the river.
cap = play(rep_start, 0, [("a3", "a5")])
check("a capture clears the history", len(cap.hist), 1)
sol = dict(rep_start, **{"e6": (0, "S")})
adv = play(sol, 0, [("a3", "b3"), ("a5", "b5"), ("e6", "e7")])
check("a Soldier advance clears the history", len(adv.hist), 1)
# ... but a sideways Soldier step along the river does NOT (it is reversible).
side = play(sol, 0, [("a3", "b3"), ("a5", "b5"), ("e6", "g5")])
check("a sideways Soldier step keeps the history", len(side.hist), 4)

# (d) NO RIVER-CROSSERS = an honest DRAW -- Red's Mandarin takes Blue's last
# Soldier (which had walked into Red's palace), and neither side then has a
# Soldier/Horse/Chariot/Cannon at all.
draw = play({"e1": (0, "G"), "e11": (1, "G"), "f1": (0, "M"), "e3": (1, "S"),
             "c9": (1, "E")}, 0, [("f1", "e3")])
check("no-crossers is terminal", GAME.is_terminal(draw), True)
check("no-crossers reason", GAME._over(draw), ("no river-crossers", None))
check("no-crossers is an honest DRAW", GAME.returns(draw), [0.0, 0.0])
check("no-crossers offers no moves", GAME.legal_moves(draw), [])
# ... and it does NOT fire while one side still has a crosser -- ANY of the four.
for _t in "SHCA":
    alive = play({"e1": (0, "G"), "e11": (1, "G"), "f1": (0, "M"),
                  "e3": (1, "S"), "c9": (1, "E"), "a3": (0, _t)},
                 0, [("f1", "e3")])
    check(f"a surviving {G.PIECE_NAMES[_t]} keeps the game alive",
          GAME._over(alive), None)

# ---------------------------------------------- precedence between endings ---
# A decisive ending (no legal move) must outrank EVERY drawing counter.  The
# collisions cannot arise in play -- an ending position can never recur, and the
# no-crossers draw fires on the capture that creates it -- so they are built.
for _nm, _s in (("checkmate", mate), ("stalemate", stale)):
    rep2 = G.GState(board=dict(_s.board), to_move=_s.to_move, ply=_s.ply,
                    hist=(_s.hist[-1],) + _s.hist, last=_s.last)
    check(f"{_nm} + repetition: the counter WOULD award the other side",
          GAME._over(rep2), ("repetition", rep2.to_move))
    check(f"{_nm} + repetition: returns is still decisive",
          GAME.returns(rep2), [1.0, -1.0])
    check(f"{_nm} + repetition: caption still names the winner",
          GAME.render(rep2)["caption"], f"Red wins ({_nm})")
    cap2 = G.GState(board=dict(_s.board), to_move=_s.to_move,
                    ply=G.PLY_CAP + 1, hist=(_s.hist[-1],) + _s.hist,
                    last=_s.last)
    check(f"{_nm} + repetition + ply cap: returns is still decisive",
          GAME.returns(cap2), [1.0, -1.0])
# ... and the one collision that IS reachable: the capture that removes the last
# river-crosser also stalemates Blue, whose own men fill his palace.
both = play({"e11": (1, "G"), "e10": (1, "M"), "d10": (1, "M"), "f10": (1, "M"),
             "e9": (1, "M"), "d9": (1, "M"), "f9": (1, "M"),
             "e1": (0, "G"), "f1": (0, "M"), "e3": (1, "S")},
            0, [("f1", "e3")])
check("no-crossers + stalemate: the draw counter fires",
      GAME._over(both), ("no river-crossers", None))
check("no-crossers + stalemate: Blue has no legal move", GAME._legal(both), [])
check("no-crossers + stalemate: Blue is NOT in check",
      G._in_check(both.board, 1), False)
check("no-crossers + stalemate: returns is DECISIVE, not 0-0",
      GAME.returns(both), [1.0, -1.0])
check("no-crossers + stalemate: caption",
      GAME.render(both)["caption"], "Red wins (stalemate)")

# The initial position always has crossers, so the draw can only ever be
# reached through apply_move.
check("opening has crossers", GAME._over(s0), None)

# --------------------------------------------------- termination / ply cap --
# "Repetition loses" makes a repeated position impossible, so every game is
# finite by construction; PLY_CAP is a backstop that must never bind.
import random                                                  # noqa: E402
longest = 0
for seed in range(12):
    rng = random.Random(seed)
    s = GAME.initial_state()
    while not GAME.is_terminal(s):
        s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
    longest = max(longest, s.ply)
    check(f"random game {seed} ended below the ply cap", s.ply < G.PLY_CAP,
          True)
    check(f"random game {seed} ended for a real reason",
          GAME._over(s) is None or GAME._over(s)[0] != "move limit", True)
check("PLY_CAP leaves ample headroom", longest * 4 < G.PLY_CAP, True)

# ------------------------------------------------------------ round-trips ---
probe = play(rep_start, 0, [("a3", "b3"), ("a5", "b5")])
back = GAME.deserialize(GAME.serialize(probe))
check("serialize round-trip: board", back.board, probe.board)
check("serialize round-trip: hist", back.hist, probe.hist)
check("serialize round-trip: to_move / ply",
      (back.to_move, back.ply), (probe.to_move, probe.ply))
check("serialize round-trip: last", back.last, probe.last)
check("serialize round-trip: moves", GAME.legal_moves(back),
      GAME.legal_moves(probe))
check("serialize round-trip is a fixpoint", GAME.serialize(back),
      GAME.serialize(probe))
check("describe_move", GAME.describe_move(s0, "%d,%d>%d,%d" % (pn("e4")
                                                               + pn("e5"))),
      "Se4-e5")
check("describe_move marks check",
      GAME.describe_move(state({"d1": (0, "G"), "e11": (1, "G"),
                                "a4": (0, "C"), "d5": (0, "C"),
                                "f5": (0, "C")}, 0),
                         "%d,%d>%d,%d" % (pn("a4") + pn("e4"))), "Ca4-e4+")
check("describe_move marks a capture",
      GAME.describe_move(state({"e1": (0, "G"), "e11": (1, "G"),
                                "f1": (0, "M"), "e3": (1, "S"),
                                "c9": (1, "E")}, 0),
                         "%d,%d>%d,%d" % (pn("f1") + pn("e3"))), "Mf1xe3")
spec = GAME.render(s0)
check("render: hex board", spec["board"]["type"], "hex")
check("render: flat-top", spec["board"]["orientation"], "flat")
# The orientation is a correctness question (30 deg is not a lattice symmetry),
# so DERIVE it rather than assert it.  Under Board.jsx's flat-top map
# (x, y) = (1.5q, sqrt3 * (r + q/2)) a file is VERTICAL and the river's five
# cells -- successive steps of (+2,-1) -- lie on one HORIZONTAL line, which is
# exactly how every diagram on the rules page draws them.  Pointy-top, whose map
# is (sqrt3 * (q + r/2), 1.5r), does neither.
def flat(c):
    return (1.5 * c[0], c[1] + c[0] / 2.0)          # y in units of sqrt(3)


def pointy(c):
    return (c[0] + c[1] / 2.0, 1.5 * c[1])          # x in units of sqrt(3)


_col = [flat(pn(f"e{n}")) for n in (1, 2, 3)]
check("flat-top puts a file on one vertical line",
      (len({round(x, 9) for x, _ in _col}), len({round(y, 9) for _, y in _col})),
      (1, 3))
_riv = [flat(c) for c in sorted(G.RIVER)]
check("flat-top puts the five river cells on one horizontal line",
      (len({round(y, 9) for _, y in _riv}), len({round(x, 9) for x, _ in _riv})),
      (1, 5))
check("pointy-top would scatter them over five different heights",
      len({round(y, 9) for _, y in (pointy(c) for c in G.RIVER)}), 5)
check("render: cell list", len(spec["board"]["cells"]), 79)
check("render: every piece sits on a listed cell",
      all(p["cell"] in set(spec["board"]["cells"]) for p in spec["pieces"]),
      True)
check("render: every tinted cell exists",
      set(spec["board"]["tints"]) - set(spec["board"]["cells"]), set())

if fails:
    print("FAILED:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print(f"xiang_hex selftest OK ({len(DIAGRAMS)} positions from the 8 source "
      f"diagrams, preset board string, perft 3 = 28968, longest random game "
      f"{longest} plies)")
