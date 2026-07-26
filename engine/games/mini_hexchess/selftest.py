"""Selftest for Mini Hexchess (pure stdlib; run from engine/):

    PYTHONPATH=. python3 games/mini_hexchess/selftest.py

Correctness anchors
-------------------
1. The starting array, decoded HERE from the Game Courier preset FEN
   `1prb/2pkn/3ppp/7/-PPP3/--NKP2/---BRP1` — an independent second source from
   the chessvariants.com setup diagram this package was built from — plus a
   proof that it is exactly 180-degree rotationally symmetric.
2. PERFT from the initial position: 9 / 71 / 681 / 7,534 / 92,914 (depths 1-5).
   Frozen after two one-time differentials (2026-07-26, not rerun here):
     * against `mccooey_chess`'s OWN move generator retargeted at the 37-hex
       board with the double step switched off (so every rule the two games
       share is compared byte for byte): 22,329 positions from 200 random games
       in lockstep, 0 mismatches, covering 7,071 promotion and 33,673 capture
       moves;
     * against a from-scratch reimplementation whose directions are DISCOVERED
       by measuring distances between hex CENTRES in pixel space and whose
       promotion cells are characterised as "the cells a forward move would
       leave the board from": 33,812 positions from 250 random games,
       0 mismatches.
   Depth 1 = 9 is hand-derived below.
3. The three rule deltas from McCooey's full-size game, each tested directly:
   NO double step and NO en passant anywhere on the board (proved by
   exhaustion over all 37 cells), promotion to R/B/N and NEVER to a queen, on
   all SEVEN hexes of the opponent's edge; and no castling.
4. Checkmate and stalemate REACHED through apply_move; stalemate is a DRAW.
5. The hard ply cap is not outcome-load-bearing: proved unreachable (bound
   7,699 < PLY_CAP) and measured over random games.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agp.loader import load_from_dir  # noqa: E402

HERE = Path(__file__).resolve().parent
man, g = load_from_dir(HERE)
mod = sys.modules[type(g).__module__]
cell_name = mod.cell_name
WHITE, BLACK = mod.WHITE, mod.BLACK

t0 = time.time()
checks = 0


def ok(cond, what):
    global checks
    checks += 1
    if not cond:
        raise AssertionError(f"FAIL: {what}")


NAMED = {cell_name(c): c for c in mod.CELLS}


def cell(nm):
    return NAMED[nm]


def mstr(a, b, promo=None):
    x, y = cell(a), cell(b)
    return f"{x[0]},{x[1]}>{y[0]},{y[1]}" + (f"={promo}" if promo else "")


def pos(pieces, to_move=WHITE):
    return mod.MState(board={cell(n): v for n, v in pieces.items()},
                      to_move=to_move)


def named(s):
    return {cell_name(k): v for k, v in s.board.items()}


def desc_set(s):
    return {g.describe_move(s, m) for m in g.legal_moves(s)}


# --- 1. the board -----------------------------------------------------------
ok(len(mod.CELLS) == 37, "37 cells (hexhex-4)")
ok(sorted(len([c for c in mod.CELLS if c[0] == q]) for q in range(-3, 4))
   == [4, 4, 5, 5, 6, 6, 7], "file lengths 4 5 6 7 6 5 4")
ok(cell_name((0, 3)) == "d1" and cell_name((0, 0)) == "d4"
   and cell_name((0, -3)) == "d7" and cell_name((-3, 0)) == "a4",
   "McCooey-style file/rank naming on the small board")

# --- 2. the starting array, decoded independently from the Game Courier FEN -
FEN = "1prb/2pkn/3ppp/7/-PPP3/--NKP2/---BRP1"


def decode_fen():
    """GC preset (cols 7): '-' = a cell that is not on the board, digits =
    empty cells; (q, r) = (col - 4, row - col)."""
    board = {}
    for row_i, row in enumerate(FEN.split("/"), start=1):
        col = 1
        for ch in row:
            if ch == "-" or ch.isdigit():
                col += 1 if ch == "-" else int(ch)
                continue
            board[(col - 4, row_i - col)] = (
                WHITE if ch.isupper() else BLACK, ch.upper())
            col += 1
    return board


s0 = g.initial_state()
fen_board = decode_fen()
ok(len(fen_board) == 18 and all(c in mod.CELLS for c in fen_board),
   "the FEN decodes to 18 men, all on the 37-hex board")
ok(fen_board == s0.board,
   "the Game Courier FEN agrees with the chessvariants diagram, cell for cell")
ok(all(fen_board.get((-q, -r)) == (1 - o, t)
       for (q, r), (o, t) in fen_board.items()),
   "the starting position is exactly 180-degree rotationally symmetric")
ok(named(s0) == {"c1": (WHITE, "N"), "d1": (WHITE, "B"), "e1": (WHITE, "R"),
                 "b1": (WHITE, "P"), "f1": (WHITE, "P"), "c2": (WHITE, "P"),
                 "d2": (WHITE, "K"), "e2": (WHITE, "P"), "d3": (WHITE, "P"),
                 "e6": (BLACK, "N"), "d7": (BLACK, "B"), "c6": (BLACK, "R"),
                 "f5": (BLACK, "P"), "b5": (BLACK, "P"), "e5": (BLACK, "P"),
                 "d6": (BLACK, "K"), "c5": (BLACK, "P"), "d5": (BLACK, "P")},
   "the setup in McCooey notation (ranks are numbered from White's corner, so "
   "Black's men sit on ranks 5-7 of files b..f)")
for p in (WHITE, BLACK):
    army = sorted(t for (o, t) in s0.board.values() if o == p)
    ok(army == ["B", "K", "N", "P", "P", "P", "P", "P", "R"],
       f"army = K R B N + 5 pawns, and NO QUEEN (seat {p})")

# the three bishops... there is only one, but it is still colourbound
ok(all(((a[0] + d[0]) - (a[1] + d[1])) % 3 == (a[0] - a[1]) % 3
       for d in mod.DIAG for a in [(0, 0)]),
   "every bishop direction preserves the cell colour")

# --- 3. the RenderSpec shape ------------------------------------------------
spec = g.render(s0)
b = spec["board"]
ok(b["type"] == "hex" and b["shape"] == "hexagon" and b["size"] == 4,
   "board is a hexhex of side 4")
ok(b["orientation"] == "flat",
   "flat-top: the files are drawn VERTICAL, as in McCooey's full-size game")
ok(len(b["tints"]) == 37 and len(set(b["tints"].values())) == 3,
   "37 tinted cells in three colours")
ok(len(spec["pieces"]) == 18 and spec["pieceset"] == "chess", "18 rendered men")
ok(spec["highlights"] == [] and spec["caption"] == "White to move",
   "nothing is highlighted before the first move")
# render() is NOT exercised by validate, and a malformed spec white-screens the
# board -- so pin the cell ids, the last-move highlight and the check flag.
_ids = {f"{q},{r}" for q, r in mod.CELLS}
_r1 = g.render(g.apply_move(s0, mstr("d3", "d4")))
ok([h["cell"] for h in _r1["highlights"]] == ["0,1", "0,0"]
   and all(h["kind"] == "last-move" and h["cell"] in _ids
           for h in _r1["highlights"]),
   "the last move highlights BOTH its from-cell (d3 = 0,1) and its to-cell "
   "(d4 = 0,0), by cell id and in that order")
ok(all(p["cell"] in _ids and p["owner"] in (WHITE, BLACK)
       and p["label"] in "PNBRQK" for p in _r1["pieces"]),
   "every rendered piece names a real cell, a real seat and a real letter")
_chk = pos({"d4": (WHITE, "K"), "d6": (BLACK, "R"), "a1": (BLACK, "K")})
ok("(check)" in g.render(_chk)["caption"],
   "the caption flags check")
ok("(check)" not in g.render(s0)["caption"], "and only when there is one")

# --- 4. depth-1 move count, hand-derived ------------------------------------
# 5 pawn steps (b1-b2, c2-c3, d3-d4, e2-e3, f1-f2) + 4 knight moves
# (Nc1: a2 b3 d4 e3) + 0 bishop, 0 rook (both hemmed in) + 0 king (both its
# free cells, c3 and e3, are attacked by the black d5 pawn).
ok(sorted(desc_set(s0)) == ["Nc1-a2", "Nc1-b3", "Nc1-d4", "Nc1-e3",
                            "b1-b2", "c2-c3", "d3-d4", "e2-e3", "f1-f2"],
   "the nine opening moves, by name")
s0b = mod.MState(board=dict(s0.board), to_move=BLACK)
ok(len(g.legal_moves(s0b)) == 9, "Black has the same 9 by symmetry")

# --- 5. frozen perft --------------------------------------------------------
def perft(s, d):
    ms = g.legal_moves(s)
    if d == 1:
        return len(ms)
    return sum(perft(g.apply_move(s, m), d - 1) for m in ms)


for depth, want_n in ((1, 9), (2, 71), (3, 681), (4, 7534), (5, 92914)):
    ok(perft(g.initial_state(), depth) == want_n, f"perft({depth}) == {want_n}")

# --- 6. NO double step and NO en passant, proved by exhaustion --------------
for player in (WHITE, BLACK):
    kings = {cell("a1"): (WHITE, "K"), cell("g4"): (BLACK, "K")}
    for c in mod.CELLS:
        if c in kings or mod._is_promo(player, c):
            continue
        board = dict(kings)
        board[c] = (player, "P")
        st = mod.MState(board=board, to_move=player)
        quiet = sorted({m[1] for m in g._legal(st)
                        if m[0] == c and m[1] not in board})
        fwd = (c[0] + mod.PAWN_FWD[player][0], c[1] + mod.PAWN_FWD[player][1])
        want = [fwd] if (mod.on_board(*fwd) and fwd not in board) else []
        ok(quiet == want,
           f"a lone pawn on {cell_name(c)} has exactly its one forward step "
           f"(no double step anywhere on the board)")
ok("ep" not in g.serialize(s0),
   "there is no en-passant state at all (no double step => no e.p.)")
ok(not hasattr(s0, "ep"), "and none on the state object either")

# a pawn on its own home cell still has only one step
ok({m for m in desc_set(s0) if m.startswith("d3")} == {"d3-d4"},
   "even an unmoved pawn has no double step")

# --- 7. promotion: R/B/N on all SEVEN edge hexes, never a queen -------------
wpromo = sorted(cell_name(c) for c in mod.CELLS if mod._is_promo(WHITE, c))
bpromo = sorted(cell_name(c) for c in mod.CELLS if mod._is_promo(BLACK, c))
ok(wpromo == ["a4", "b5", "c6", "d7", "e6", "f5", "g4"],
   "White's seven promotion hexes = the two far edges")
ok(bpromo == ["a1", "b1", "c1", "d1", "e1", "f1", "g1"],
   "Black's seven promotion hexes")
ok(mod.PROMO_CHOICES == ("R", "B", "N"), "promotion choices are R, B, N only")

# reach every one of the seven, for both colours, by an actual move
KINGS = {WHITE: ("a1", "g1"), BLACK: ("g4", "a4")}      # (own, enemy)
for player, promos in ((WHITE, wpromo), (BLACK, bpromo)):
    back = mod.PAWN_FWD[1 - player]
    own, enemy = KINGS[player]
    for pn in promos:
        tgt = cell(pn)
        src = (tgt[0] + back[0], tgt[1] + back[1])
        ok(mod.on_board(*src), f"{pn} is reachable from behind")
        st = mod.MState(board={src: (player, "P"),
                               cell(own): (player, "K"),
                               cell(enemy): (1 - player, "K")}, to_move=player)
        step = f"{src[0]},{src[1]}>{tgt[0]},{tgt[1]}"
        got = {m.split("=")[1] for m in g.legal_moves(st) if m.startswith(step)}
        ok(got == {"R", "B", "N"},
           f"promotion on {pn} offers exactly R/B/N (never Q), and is forced")
# a capture onto a promotion hex also promotes
capp = pos({"c5": (WHITE, "P"), "d7": (BLACK, "R"), "d4": (WHITE, "K"),
            "g4": (BLACK, "K")})
ok({m for m in desc_set(capp) if m.startswith("c5x")}
   == {f"c5xd7={pc}" for pc in "RBN"},
   "a capture onto an edge hex promotes too, still without a queen option")

# no queen can ever appear on the board
ok(not any("Q" in m for m in g.legal_moves(g.initial_state())),
   "no queen promotion is even expressible")

# --- 8. no castling ---------------------------------------------------------
ok(not hasattr(mod, "CASTLE") and not hasattr(mod, "KING_START"),
   "no castling machinery exists")
kmoves = pos({"d4": (WHITE, "K")})          # a lone king on the centre hex
deltas = {(mod._cell(m.split(">")[1])[0] - cell("d4")[0],
           mod._cell(m.split(">")[1])[1] - cell("d4")[1])
          for m in g.legal_moves(kmoves)}
ok(deltas == set(mod.ORTHO) | set(mod.DIAG),
   "a central king has exactly its 12 one-step moves -- no 2-cell castling")

# --- 9. the pawn's McCooey capture geometry ---------------------------------
pc = pos({"d4": (WHITE, "P"), "e5": (BLACK, "N"), "c5": (BLACK, "N"),
          "d5": (BLACK, "N"), "e4": (BLACK, "N"),
          "a1": (WHITE, "K"), "g4": (BLACK, "K")})
ok({m for m in desc_set(pc) if m.startswith("d4")} == {"d4xe5", "d4xc5"},
   "the pawn captures on its two forward DIAGONALS (e5, c5); it cannot "
   "capture the piece straight ahead on d5 -- which also blocks its move -- "
   "nor the one on the forward-side edge neighbour e4")

# --- 10. checkmate / stalemate, REACHED through apply_move ------------------
mate_pre = pos({"a3": (WHITE, "K"), "b5": (WHITE, "R"), "a1": (BLACK, "K")})
mate = g.apply_move(mate_pre, mstr("b5", "b2"))
ok(g.is_terminal(mate) and g.legal_moves(mate) == []
   and mod._in_check(mate.board, BLACK) and g.returns(mate) == [1.0, -1.0],
   "1.Rb5-b2 is checkmate (Ka3 + Rb2 vs Ka1)")
stale_pre = pos({"a4": (WHITE, "K"), "d3": (WHITE, "R"), "a1": (BLACK, "K")})
stale = g.apply_move(stale_pre, mstr("a4", "a3"))
ok(g.is_terminal(stale) and g.legal_moves(stale) == []
   and not mod._in_check(stale.board, BLACK) and g.returns(stale) == [0.0, 0.0],
   "1.Ka4-a3 is STALEMATE, and stalemate IS A DRAW (McCooey's rule)")

# --- 11. draw rules ---------------------------------------------------------
rep = pos({"d4": (WHITE, "K"), "d7": (BLACK, "K")})
rep.reps = {mod._poskey(rep.board, rep.to_move): 1}
st = rep
for a, b2 in [("d4", "d3"), ("d7", "d6"), ("d3", "d4"), ("d6", "d7")] * 2:
    st = g.apply_move(st, mstr(a, b2))
ok(g._draw_reason(st) == "threefold repetition" and g.is_terminal(st)
   and g.returns(st) == [0.0, 0.0], "threefold repetition draws")
ok(g._draw_reason(mod.MState(board=dict(rep.board), halfmove=100))
   == "50-move rule", "the 50-move rule draws")

# the halfmove clock: RESET by a capture and by a pawn move, and by nothing
# else.  (Getting this wrong turns live positions into bogus 50-move draws.)
clk = pos({"d4": (WHITE, "R"), "a1": (WHITE, "K"), "g4": (BLACK, "K"),
           "d6": (BLACK, "R"), "b3": (WHITE, "P")})
clk.halfmove = 42
ok(g.apply_move(clk, mstr("d4", "d5")).halfmove == 43,
   "a quiet piece move ticks the halfmove clock")
ok(g.apply_move(clk, mstr("d4", "d6")).halfmove == 0,
   "a CAPTURE resets the halfmove clock")
ok(g.apply_move(clk, mstr("b3", "b4")).halfmove == 0,
   "a PAWN move resets the halfmove clock")
clk.reps = {"an-earlier-position": 2}
ok("an-earlier-position" in g.apply_move(clk, mstr("d4", "d5")).reps,
   "a reversible move KEEPS the earlier repetition counts")
for _irrev in ("d6", "b4"):                       # a capture, then a pawn move
    _src = "d4" if _irrev == "d6" else "b3"
    _after = g.apply_move(clk, mstr(_src, _irrev))
    ok(_after.reps == {mod._poskey(_after.board, BLACK): 1},
       f"...but {_src}-{_irrev} CLEARS it: no earlier position can ever recur "
       "once a man has been captured or a pawn has advanced, so keeping the "
       "counts would manufacture false threefold draws")

# the repetition key must include the side to move -- the same board with the
# other player on move is a DIFFERENT position and must not count towards the
# threefold.
_b = dict(rep.board)
ok(mod._poskey(_b, WHITE) != mod._poskey(_b, BLACK),
   "the position key distinguishes the side to move")
ok(g.initial_state().reps
   == {mod._poskey(g.initial_state().board, WHITE): 1},
   "the STARTING position is seeded into the repetition table (it is the "
   "first of its three occurrences)")

# --- 11b. checkmate OUTRANKS the draw counters ------------------------------
# Chess ends the instant the king is mated, so a mate delivered on the 100th
# reversible ply is a win, not a "50-move rule" draw.  Random play never lands
# on that boundary, so it takes a constructed position to pin it.
late = pos({"a3": (WHITE, "K"), "b5": (WHITE, "R"), "a1": (BLACK, "K")})
late.halfmove = 99
late_mate = g.apply_move(late, mstr("b5", "b2"))
ok(late_mate.halfmove == 100 and g._draw_reason(late_mate) == "50-move rule",
   "the mating move is also the 100th reversible ply")
ok(g.is_terminal(late_mate) and g.returns(late_mate) == [1.0, -1.0],
   "checkmate on the 50-move boundary is a WIN, not a draw")
ok("checkmate" in g.render(late_mate)["caption"],
   "and the board says so")
ok(g.returns(stale) == [0.0, 0.0] and g.returns(st) == [0.0, 0.0],
   "while stalemate and the counters still pay 0-0")

# --- 12. the ply cap is NOT outcome-load-bearing ----------------------------
# Bound: <=16 captures + <=60 pawn moves (10 pawns; each pawn move drops r by
# 1 or 2 and a pawn starts at r <= 3 and promotes by r = -3, so <= 6 moves
# each) = <=76 irreversible plies, with <=99 reversible plies in each of the
# 77 gaps around them.
BOUND = 16 + 10 * 6 + (16 + 10 * 6 + 1) * 99
ok(BOUND == 7699 and mod.PLY_CAP > BOUND,
   f"the 50-move rule provably fires first (bound {BOUND} < cap {mod.PLY_CAP})")

import random  # noqa: E402

longest = 0
for seed in range(20):
    rng = random.Random(seed)
    st = g.initial_state()
    while not g.is_terminal(st):
        st = g.apply_move(st, rng.choice(g.legal_moves(st)))
        ok("Q" not in (t for (_o, t) in st.board.values()),
           "no queen ever reaches the board")
    longest = max(longest, st.ply)
    ok(g._draw_reason(st) != "move limit",
       "no random game is ever decided by the ply cap")
    ret = g.returns(st)
    ok(len(ret) == 2 and all(-1.0 <= x <= 1.0 for x in ret), "well-formed returns")
ok(longest * 10 < mod.PLY_CAP,
   f"longest random game {longest} plies -- an order of magnitude under the cap")

# --- 13. serialization round-trip -------------------------------------------
st = g.initial_state()
for _ in range(5):
    st = g.apply_move(st, sorted(g.legal_moves(st))[0])
import json  # noqa: E402

back = g.deserialize(json.loads(json.dumps(g.serialize(st))))
ok(back.board == st.board and back.to_move == st.to_move
   and back.halfmove == st.halfmove and back.ply == st.ply
   and back.reps == st.reps and back.last == st.last,
   "serialize/deserialize round-trips EVERY field through JSON -- board, side "
   "to move, halfmove clock, ply, the repetition table and the last move. The "
   "server stores the state this way on every move, so anything dropped here "
   "silently disables a draw rule in async play.")
ok(set(g.serialize(st)) == {"board", "to_move", "halfmove", "ply", "reps",
                            "last"},
   "and it carries exactly those six fields -- no en-passant, no castling")
ok(sorted(g.legal_moves(back)) == sorted(g.legal_moves(st)),
   "and the restored state generates the same moves")
ok(g._draw_reason(back) == g._draw_reason(st),
   "and the same draw status")
ok(g.describe_move(g.initial_state(), mstr("d3", "d4")) == "d3-d4",
   "move description uses McCooey notation")

# --- 14. bot contract -------------------------------------------------------
h = g.heuristic(g.initial_state())
ok(isinstance(h, list) and len(h) == 2 and abs(h[0] + h[1]) < 1e-9,
   "heuristic is a zero-sum pair (a bare float raises TypeError in MCTS "
   "back-prop, and only when the rollout cutoff is reached)")
ok(abs(h[0]) < 1e-9, "and it is level on the symmetric starting array")
# ...and it must point the right way: White a rook up must score POSITIVE.
_up = pos({"d4": (WHITE, "K"), "d1": (WHITE, "R"), "d7": (BLACK, "K")})
ok(g.heuristic(_up)[0] > 0 > g.heuristic(_up)[1],
   "a material edge scores in favour of the side that HAS it")
from agp.mcts import MCTSBot  # noqa: E402

MCTSBot(random.Random(1), iterations=20, max_rollout=4).select(g, g.initial_state())
checks += 1

print(f"mini_hexchess selftest OK ({checks} checks, {time.time() - t0:.1f}s)")
