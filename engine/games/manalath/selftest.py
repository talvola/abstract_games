#!/usr/bin/env python3
"""Manalath correctness anchors (pure stdlib; run by tests/test_games.py).

Every rule assertion below was independently confirmed against the AbstractPlay
`gameslib` reference implementation (`src/games/manalath.ts`, MIT — used as a
rule-enforcing ORACLE only).  The constructed positions below are the Python
twins of the probes emitted by `_diff_ap.py --cases`; each one cites the oracle
case letter, and the oracle's verdict is quoted beside it.  See rules.md.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir  # noqa: E402

HERE = Path(__file__).resolve().parent
_MAN, GAME = load_from_dir(HERE)
MOD = sys.modules[type(GAME).__module__]   # the LIVE module object (synthetic name)

CHECKS = 0


def ok(cond, msg):
    global CHECKS
    CHECKS += 1
    if not cond:
        raise AssertionError(msg)


def state(board, to_move=0, last_pass=False):
    """Build a state from {"q,r": colour} (0 = Red, 1 = Blue)."""
    return GAME.deserialize({
        "side": 5, "board": dict(board), "to_move": to_move,
        "over": False, "winner": None, "last": None,
        "last_pass": last_pass, "ply": len(board),
    })


def red(*cells):
    return {c: 0 for c in cells}


def blue(*cells):
    return {c: 1 for c in cells}


# --------------------------------------------------------------------------- #
def t_board_and_opening():
    s = GAME.initial_state()
    ok(len(MOD._cells(5)) == 61, "hexhex-5 must have 61 cells")
    ok(len(set(MOD._cells(5))) == 61, "cells must be distinct")
    # every cell has 3 (corner), 4 (edge) or 6 (interior) neighbours
    degs = sorted({len(v) for v in MOD._adj(5).values()})
    ok(degs == [3, 4, 6], f"unexpected hexhex degrees {degs}")
    ok(sum(1 for v in MOD._adj(5).values() if len(v) == 3) == 6, "6 corners of degree 3")

    mv = GAME.legal_moves(s)
    # ORACLE: gameslib's opening position has 122 legal moves (61 cells x 2 colours).
    ok(len(mv) == 122, f"opening must have 122 moves, got {len(mv)}")
    ok(len(set(mv)) == 122, "opening moves must be distinct")
    for q, r in MOD._cells(5):
        ok(f"R@{q},{r}" in mv and f"B@{q},{r}" in mv, f"missing a colour at {q},{r}")
    ok(GAME.current_player(s) == 0, "seat 0 (Red) moves first")
    ok(not GAME.is_terminal(s), "the empty board is not terminal")


def t_group_cap():
    """A placement may never build a group of more than five."""
    # ORACLE case G: with a red quint e3..e7, e8w is invalid and e8b is valid.
    quint = red("-2,0", "-1,0", "0,0", "1,0", "2,0")
    s = state(quint)
    mv = set(GAME.legal_moves(s))
    empties = [c for c in MOD._cells(5) if f"{c[0]},{c[1]}" not in quint]
    touching = 0
    for cell in empties:
        cid = f"{cell[0]},{cell[1]}"
        adjacent = any(f"{n[0]},{n[1]}" in quint for n in MOD._adj(5)[cell])
        ok(f"B@{cid}" in mv, f"blue must always be placeable at {cid}")
        if adjacent:
            touching += 1
            ok(f"R@{cid}" not in mv, f"red at {cid} would make a group of 6")
        else:
            ok(f"R@{cid}" in mv, f"red at {cid} is a fresh group and must be legal")
    # a straight run of n hexes has 2n+4 neighbours -> 14 for n = 5
    ok(touching == 14, f"a straight quint through the centre touches 14 empties, got {touching}")

    # ORACLE case H: joining a 3-group and a 2-group would make 6 -> illegal.
    s = state(red("-3,0", "-2,0", "-1,0", "1,0", "2,0"))
    mv = set(GAME.legal_moves(s))
    ok("R@0,0" not in mv, "3 + 1 + 2 = 6 must be illegal")
    ok("B@0,0" in mv, "the same cell must accept the other colour")
    # ORACLE case I: joining a 3-group and a 1-group makes exactly 5 -> legal.
    s = state(red("-3,0", "-2,0", "-1,0", "1,0"))
    mv = set(GAME.legal_moves(s))
    ok("R@0,0" in mv, "3 + 1 + 1 = 5 must be legal")
    # the cap applies to BOTH colours symmetrically
    s = state(blue("-2,0", "-1,0", "0,0", "1,0", "2,0"))
    mv = set(GAME.legal_moves(s))
    ok("B@3,0" not in mv and "R@3,0" in mv, "the cap must apply to Blue as well")
    # ...and it is enforced in apply_move, not just advertised
    try:
        GAME.apply_move(s, "B@3,0")
        ok(False, "apply_move must reject an oversized placement")
    except ValueError:
        ok(True, "apply_move rejects an oversized placement")


def t_win_and_loss():
    # ORACLE case A: e3,e4,e5,e7 white, White plays e6w -> winner [1] (mover wins).
    s = state(red("-2,0", "-1,0", "0,0", "2,0"), to_move=0)
    n = GAME.apply_move(s, "R@1,0")
    ok(GAME.is_terminal(n) and n.winner == 0, "own quint on your own turn wins")
    ok(GAME.returns(n) == [1.0, -1.0], "seat 0 win payoff")

    # ORACLE case B: e3,e4,e5 white, White plays e6w -> winner [2] (mover loses).
    s = state(red("-2,0", "-1,0", "0,0"), to_move=0)
    n = GAME.apply_move(s, "R@1,0")
    ok(GAME.is_terminal(n) and n.winner == 1, "own quart on your own turn loses")
    ok(GAME.returns(n) == [-1.0, 1.0], "seat 1 win payoff")
    ok(GAME.legal_moves(n) == [], "a terminal state has no legal moves")

    # the mirror image for seat 1 (Blue).
    s = state(blue("-2,0", "-1,0", "0,0", "2,0"), to_move=1)
    n = GAME.apply_move(s, "B@1,0")
    ok(n.winner == 1, "Blue's own quint wins for seat 1")
    s = state(blue("-2,0", "-1,0", "0,0"), to_move=1)
    n = GAME.apply_move(s, "B@1,0")
    ok(n.winner == 0, "Blue's own quart loses for seat 1")

    # a group of 3 or of 2 is neither
    s = state(red("-2,0", "-1,0"), to_move=0)
    n = GAME.apply_move(s, "R@0,0")
    ok(not GAME.is_terminal(n), "a group of 3 is not an end condition")


def t_only_your_own_colour():
    """Win/loss is judged on the MOVER's colour only."""
    # ORACLE case C1: Black stones e3,e4,e5; White plays e6b (building a BLACK
    # quart) -> gameover=false.  Red owns no stones, so nothing fires.
    s = state(blue("-2,0", "-1,0", "0,0"), to_move=0)
    n = GAME.apply_move(s, "B@1,0")
    ok(not GAME.is_terminal(n), "building the ENEMY's quart is harmless on your turn")
    ok(n.to_move == 1, "turn passes to seat 1")
    # ORACLE case C2: ...and it kills Blue at the end of Blue's own next turn,
    # whatever Blue plays (winner [1] = seat 0).
    m = GAME.apply_move(n, "R@4,-4")
    ok(GAME.is_terminal(m) and m.winner == 0, "a quart of your colour kills you on your turn")
    # a quint built FOR you by the opponent likewise wins for you next turn
    s = state(blue("-2,0", "-1,0", "0,0", "1,0"), to_move=0)
    n = GAME.apply_move(s, "B@2,0")          # seat 0 builds a BLUE quint
    ok(not GAME.is_terminal(n), "building the enemy's quint is harmless on your turn")
    m = GAME.apply_move(n, "R@4,-4")
    ok(GAME.is_terminal(m) and m.winner == 1, "a quint of your colour wins on your turn")


def alg(cell):
    """Designer/gameslib algebraic name -> our axial cell id.

    Rows 'a' (bottom, 5 cells) .. 'e' (middle, 9) .. 'i' (top, 5), numbered from
    the left.  r = 4 - rowIndex, q = (number - 1) + max(-4, -4 - r).
    """
    r = 4 - (ord(cell[0]) - ord("a"))
    return f"{(int(cell[1:]) - 1) + max(-4, -4 - r)},{r}"


def diagram(white, black):
    return {**{alg(c): 0 for c in white.split()}, **{alg(c): 1 for c in black.split()}}


# The two worked examples ON THE DESIGNER'S OWN RULES PAGE, transcribed cell by
# cell from his diagrams (spielstein.com/images/games/manalath/rules/
# winorloss.png and wl2.png, read pixel-by-pixel).  They are the primary source
# for the precedence rule and for "e7b is simply illegal", so they are pinned
# here as executable assertions rather than paraphrased.
EX1_W = ("a2 a3 a4 b1 b6 c2 c4 c7 d5 d6 e1 e3 e4 f1 f5 f6 g2 g4 h1 h2 i1 i3 i4")
EX1_B = ("c6 d4 f3 f4 g5 g6 h3")
EX2_W = ("a2 a3 a5 b2 c4 c6 d2 d3 d8 e1 e6 e8 e9 f1 f2 f4 g4 h1 h2 h6 i1 i5")
EX2_B = ("a1 a4 b1 b3 b4 d4 d5 d6 f7 f8 h4 i3")


def t_designer_diagrams():
    """Both worked examples from the designer's rules page, executed."""
    # Pin the algebraic <-> axial mapping first: if it drifted, every assertion
    # below would still "pass" while testing the wrong cells.
    for name, axial in (("e5", "0,0"), ("a1", "-4,4"), ("a5", "0,4"),
                        ("i1", "0,-4"), ("i5", "4,-4"), ("e1", "-4,0"),
                        ("e9", "4,0")):
        ok(alg(name) == axial, f"{name} must map to {axial}, got {alg(name)}")
    named = [f"{chr(97 + L)}{n}" for L in range(9) for n in range(1, 10 - abs(4 - L))]
    ok(len(named) == 61, "61 algebraic names")
    ok(sorted(MOD._parse_cell(alg(c)) for c in named) == sorted(MOD._cells(5)),
       "the algebraic names must be a bijection onto our 61 axial cells")
    # -- Example 1: "White to move.  Black has just completed a white quart
    #    playing i1w, which White can't defend.  Even if White is going to play
    #    on one of the three marked spaces e2w, d2w, or d3w building a quint,
    #    the game is lost for White as the losing condition was created first
    #    and is still active after White's move."
    s = state(diagram(EX1_W, EX1_B), to_move=0)
    grp = MOD._group_at(s.board, 5, MOD._parse_cell(alg("i1")), 0)
    ok(len(grp) == 4, f"the group Black completed at i1 must be a quart, got {len(grp)}")
    sz = sorted(len(g) for g in MOD._groups(s.board, 5, 0))
    ok(sz.count(4) == 1 and 5 not in sz, "exactly one White quart, no White quint")
    # the three marked spaces are EXACTLY the cells where a White stone makes a
    # quint -- an independent check that the diagram was transcribed correctly.
    quints = sorted(c for c in MOD._cells(5) if c not in s.board
                    and MOD._placement_group_size(s.board, 5, c, 0) == 5)
    ok(quints == sorted(MOD._parse_cell(alg(c)) for c in ("d2", "d3", "e2")),
       f"the marked quint-building spaces must be exactly d2/d3/e2, got {quints}")
    for c in ("d2", "d3", "e2"):
        n = GAME.apply_move(s, f"R@{alg(c)}")
        ok(GAME.is_terminal(n) and n.winner == 1,
           f"White still LOSES after building a quint at {c}")
    # ...and in fact after every legal move: the quart cannot be averted here.
    moves = GAME.legal_moves(s)
    ok(len(moves) == 46, f"46 legal moves in the diagram, got {len(moves)}")
    for mv in moves:
        n = GAME.apply_move(s, mv)
        ok(GAME.is_terminal(n) and n.winner == 1,
           f"White is lost whatever they play ({mv})")

    # -- Example 2: "White has played at e8w.  Black can't play at c7, d7, or
    #    e7; neither a white nor a black piece.  c7w, d7w, and e7w are all
    #    quints for White (and White can play somewhere else in the next turn).
    #    c7b does not obstruct White ..., d7b is an immediate loss because of
    #    the black quart, and e7b is simply illegal."   BLACK to move.
    s = state(diagram(EX2_W, EX2_B), to_move=1)
    for c in ("c7", "d7", "e7"):
        ok(MOD._parse_cell(alg(c)) not in s.board, f"{c} must be empty")
        n = GAME.apply_move(s, f"R@{alg(c)}")          # Black places a WHITE stone
        g = MOD._group_at(n.board, 5, MOD._parse_cell(alg(c)), 0)
        ok(len(g) == 5, f"{c}w must build a White quint, got {len(g)}")
        ok(not GAME.is_terminal(n),
           f"{c}w does not end the game on BLACK's turn -- it is White's colour")
    # c7b: legal and harmless for Black
    n = GAME.apply_move(s, f"B@{alg('c7')}")
    ok(not GAME.is_terminal(n), "c7b is legal and does not end the game")
    # d7b: an immediate loss for Black (a black quart of Black's own colour)
    n = GAME.apply_move(s, f"B@{alg('d7')}")
    ok(len(MOD._group_at(n.board, 5, MOD._parse_cell(alg("d7")), 1)) == 4,
       "d7b must build a BLACK quart")
    ok(GAME.is_terminal(n) and n.winner == 0, "d7b loses immediately for Black")
    # e7b: illegal, because it would build a black group of six
    ok(MOD._placement_group_size(s.board, 5, MOD._parse_cell(alg("e7")), 1) == 6,
       "e7b would join black groups into six")
    ok(f"B@{alg('e7')}" not in GAME.legal_moves(s), "e7b is simply illegal")
    try:
        GAME.apply_move(s, f"B@{alg('e7')}")
        ok(False, "apply_move must also reject e7b")
    except ValueError:
        ok(True, "apply_move rejects e7b")


def t_precedence():
    """'An end condition is effective when it occurred FIRST.'"""
    # ORACLE case D (the designer's own worked example): White already has a
    # quart (a1-a4) built by Black last turn, and completes a quint at i4 --
    # White still LOSES, winner [2].
    s = state({**red("-4,4", "-3,4", "-2,4", "-1,4"),
               **red("0,-4", "1,-4", "2,-4", "4,-4")}, to_move=0)
    n = GAME.apply_move(s, "R@3,-4")
    ok(GAME.is_terminal(n) and n.winner == 1,
       "a pre-existing friendly QUART outranks a freshly built friendly quint")

    # ORACLE case E: a pre-existing friendly QUINT outranks a fresh quart.
    s = state({**red("-4,4", "-3,4", "-2,4", "-1,4", "0,4"),
               **red("0,-4", "1,-4", "2,-4")}, to_move=0)
    n = GAME.apply_move(s, "R@3,-4")
    ok(GAME.is_terminal(n) and n.winner == 0,
       "a pre-existing friendly QUINT outranks a freshly built friendly quart")

    # ORACLE case F: a quart CAN be averted by absorbing it into a quint --
    # after the move the quart no longer exists, so only the quint is on the
    # board.  White e3-e6 plays e7w -> winner [1].
    s = state(red("-2,0", "-1,0", "0,0", "1,0"), to_move=0)
    n = GAME.apply_move(s, "R@2,0")
    ok(GAME.is_terminal(n) and n.winner == 0,
       "extending your own quart into a quint wins (the quart is gone)")

    # ORACLE case J: with BOTH a pre-existing friendly quart AND a pre-existing
    # friendly quint on the board, the quart decides -- the mover loses.  This
    # position is UNREACHABLE in real play (your previous turn ended with
    # neither, and your opponent's single stone can create at most one), so the
    # assertion only pins a defined behaviour; the oracle agrees (winner [2]).
    s = state({**red("-4,4", "-3,4", "-2,4", "-1,4"),
               **red("0,-4", "1,-4", "2,-4", "3,-4", "4,-4")}, to_move=0)
    n = GAME.apply_move(s, "B@0,0")
    ok(GAME.is_terminal(n) and n.winner == 1,
       "with both pre-existing conditions the QUART decides (unreachable, but defined)")

    # a pre-existing friendly quart that is NOT touched is fatal no matter what
    # harmless move is played.
    s = state(red("-4,4", "-3,4", "-2,4", "-1,4"), to_move=0)
    for mv in ("R@4,-4", "B@4,-4", "B@0,0"):
        n = GAME.apply_move(s, mv)
        ok(GAME.is_terminal(n) and n.winner == 1,
           f"an untouched friendly quart is fatal after {mv}")
    # ...but it is NOT fatal for the opponent on the opponent's turn.
    s = state(red("-4,4", "-3,4", "-2,4", "-1,4"), to_move=1)
    n = GAME.apply_move(s, "B@4,-4")
    ok(not GAME.is_terminal(n), "a RED quart does not touch Blue on Blue's turn")


# A dead position: 51 stones, every group of size 1-3 (so no quart and no
# quint), and all 10 empty cells blocked for BOTH colours.  Found by search;
# used to exercise the pass / double-pass code path.
#
# It is REACHABLE, and `t_pass_is_reachable` below reaches it by legal play
# rather than asserting it.  The proof is short: every group here has size <= 3,
# and a group in any PARTIAL position is a connected subset of a final group, so
# it too has size <= 3.  Hence (a) no placement ever builds a group of more than
# five, and (b) no player ever finishes a turn with a quart or a quint of their
# own colour -- so ANY order of these 51 placements is a legal, non-terminating
# game.  Whose turn it is never constrains anything, because either colour may
# be placed on any turn.
DEAD = {
    '-4,0': 0, '-4,1': 1, '-4,2': 0, '-4,3': 1, '-4,4': 0, '-3,-1': 1, '-3,0': 0,
    '-3,2': 1, '-3,3': 0, '-3,4': 1, '-2,-2': 1, '-2,-1': 0, '-2,0': 1, '-2,1': 0,
    '-2,3': 1, '-2,4': 0, '-1,-3': 1, '-1,-1': 1, '-1,0': 0, '-1,1': 1, '-1,2': 0,
    '-1,4': 0, '0,-4': 0, '0,-3': 0, '0,-2': 0, '0,0': 0, '0,1': 1, '0,2': 0,
    '0,3': 1, '0,4': 0, '1,-4': 1, '1,-3': 1, '1,-1': 1, '1,2': 1, '1,3': 1,
    '2,-4': 1, '2,-3': 0, '2,-2': 1, '2,-1': 1, '2,0': 0, '2,2': 0, '3,-4': 0,
    '3,-3': 0, '3,-1': 0, '3,0': 1, '3,1': 0, '4,-4': 1, '4,-3': 1, '4,-2': 0,
    '4,-1': 1, '4,0': 0,
}


def t_pass_and_draw():
    sizes = sorted(len(g) for c in (0, 1) for g in MOD._groups(
        {MOD._parse_cell(k): v for k, v in DEAD.items()}, 5, c))
    ok(max(sizes) <= 3, "the dead position must contain no quart and no quint")
    ok(len(DEAD) == 51, "dead position has 51 stones")

    for seat in (0, 1):
        s = state(DEAD, to_move=seat)
        ok(GAME.legal_moves(s) == ["pass"],
           "with no placement available the only move is pass (both seats)")
    # both pass -> honest draw
    s = state(DEAD, to_move=0)
    n = GAME.apply_move(s, "pass")
    ok(not GAME.is_terminal(n), "one pass does not end the game")
    ok(n.last_pass, "the pass is recorded")
    m = GAME.apply_move(n, "pass")
    ok(GAME.is_terminal(m), "two passes end the game")
    ok(m.winner is None and GAME.returns(m) == [0.0, 0.0], "double pass is a DRAW")

    # an end condition still fires on a forced pass: recolour 1,-4 to Red and
    # Red now has a lone quart with no legal placement anywhere.
    quart = dict(DEAD, **{'1,-4': 0})
    g0 = [len(g) for g in MOD._groups({MOD._parse_cell(k): v for k, v in quart.items()}, 5, 0)]
    g1 = [len(g) for g in MOD._groups({MOD._parse_cell(k): v for k, v in quart.items()}, 5, 1)]
    ok(g0.count(4) == 1 and 5 not in g0 and 4 not in g1 and 5 not in g1,
       "the variant position holds exactly one RED quart")
    s = state(quart, to_move=0)
    ok(GAME.legal_moves(s) == ["pass"], "still no placement available")
    n = GAME.apply_move(s, "pass")
    ok(GAME.is_terminal(n) and n.winner == 1,
       "a forced pass still loses to your own quart")
    # ...but Blue is unaffected by a RED quart
    s = state(quart, to_move=1)
    n = GAME.apply_move(s, "pass")
    ok(not GAME.is_terminal(n), "a RED quart does not decide Blue's forced pass")

    # pass is illegal while a placement exists
    try:
        GAME.apply_move(GAME.initial_state(), "pass")
        ok(False, "pass must be rejected when placements exist")
    except ValueError:
        ok(True, "pass rejected when placements exist")

    # A DECISIVE RESULT OUTRANKS THE DOUBLE-PASS DRAW.  This position is not
    # reachable (see t_pass_is_reachable / rules.md: the second passer's
    # condition would already have decided the game a ply earlier), but the
    # ordering inside apply_move is pinned here so a refactor cannot silently
    # flip it into "draw first" -- the failure shape that has bitten this
    # codebase nine times in the chess families.
    s = state(dict(DEAD, **{'1,-4': 0}), to_move=0, last_pass=True)
    ok(GAME.legal_moves(s) == ["pass"], "second-passer probe must be a dead position")
    n = GAME.apply_move(s, "pass")
    ok(GAME.is_terminal(n) and n.winner == 1,
       "an end condition must outrank the double-pass draw, not be masked by it")


def _fill(order, target):
    """Play `target`'s stones in `order` through apply_move; return the state."""
    s = GAME.initial_state()
    for cell in order:
        mv = f"{'R' if target[cell] == 0 else 'B'}@{cell}"
        ok(mv in GAME.legal_moves(s), f"{mv} must be legal at ply {s.ply}")
        ok(not GAME.is_terminal(s), f"game ended early before ply {s.ply + 1}")
        s = GAME.apply_move(s, mv)
    return s


def t_pass_is_reachable():
    """The pass / double-pass paths are REACHED by legal play, not hand-built."""
    # (a) the draw.  51 legal placements in plain sorted order, no end condition
    # ever fires, then both players are forced to pass.
    order = sorted(DEAD)
    ok(len(order) == 51, "51 placements")
    s = _fill(order, DEAD)
    ok(s.ply == 51 and not GAME.is_terminal(s), "51 plies played, game still live")
    ok(s.to_move == 1, "ply 51 was seat 0's, so seat 1 is on move")
    ok(GAME.legal_moves(s) == ["pass"], "the reached position is dead")
    n = GAME.apply_move(s, "pass")
    ok(not GAME.is_terminal(n) and n.last_pass, "one pass does not end the game")
    m = GAME.apply_move(n, "pass")
    ok(GAME.is_terminal(m) and m.winner is None and GAME.returns(m) == [0.0, 0.0],
       "a REACHED double pass is an honest draw")
    ok(m.ply == 53 and m.ply <= MOD.PLY_BOUND, "63-ply structural bound respected")

    # (b) a forced pass that LOSES, also reached.  Same fill, but '-4,2' is Blue,
    # and it is played LAST -- on ply 51, i.e. by seat 0, who thereby completes a
    # BLUE quart.  That is harmless on Red's own turn (the game's main attacking
    # idea), and seat 1 then has no placement at all: Blue must pass, and the
    # pre-existing Blue quart kills Blue.
    trap = dict(DEAD, **{'-4,2': 1})
    order = [c for c in sorted(trap) if c != '-4,2'] + ['-4,2']
    s = _fill(order, trap)
    ok(s.ply == 51 and not GAME.is_terminal(s),
       "completing the OPPONENT's quart is harmless on your own turn")
    ok(s.to_move == 1, "seat 1 (Blue) to move")
    b = {MOD._parse_cell(k): v for k, v in trap.items()}
    ok(sorted(len(g) for g in MOD._groups(b, 5, 1)).count(4) == 1,
       "exactly one Blue quart")
    ok(4 not in [len(g) for g in MOD._groups(b, 5, 0)]
       and 5 not in [len(g) for g in MOD._groups(b, 5, 0)],
       "and no Red quart or quint, so ply 51 really was safe for Red")
    ok(GAME.legal_moves(s) == ["pass"], "Blue has no legal placement")
    n = GAME.apply_move(s, "pass")
    ok(GAME.is_terminal(n) and n.winner == 0 and GAME.returns(n) == [1.0, -1.0],
       "a REACHED forced pass loses to your own pre-existing quart")


def t_termination():
    """Structural: 61 cells + at most 2 passes = at most 63 plies."""
    rng = random.Random(20260728)
    longest = 0
    outcomes = {0: 0, 1: 0, None: 0}
    for _ in range(300):
        s = GAME.initial_state()
        while not GAME.is_terminal(s):
            mv = GAME.legal_moves(s)
            ok(mv, "a non-terminal state must offer a move")
            s = GAME.apply_move(s, rng.choice(mv))
            ok(s.ply <= MOD.PLY_BOUND, f"ply {s.ply} exceeded the structural bound")
        longest = max(longest, s.ply)
        outcomes[s.winner] += 1
        ok(GAME.returns(s) in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0]), "payoff shape")
    ok(longest <= MOD.PLY_BOUND, "no random game exceeded the structural bound")
    ok(outcomes[0] > 0 and outcomes[1] > 0, "random play must reach both winners")
    print(f"      300 random games: longest {longest} plies "
          f"(structural bound {MOD.PLY_BOUND}); outcomes {outcomes}")


def t_serialize_and_render():
    rng = random.Random(4)
    s = GAME.initial_state()
    for _ in range(9):
        s = GAME.apply_move(s, rng.choice(GAME.legal_moves(s)))
        d = GAME.serialize(s)
        ok(GAME.serialize(GAME.deserialize(d)) == d, "serialize must round-trip")
        # ...and through JSON, which is how the server actually stores it.
        ok(GAME.serialize(GAME.deserialize(json.loads(json.dumps(d)))) == d,
           "serialize must round-trip through JSON (the DB path)")
        ok(set(d) == {"side", "board", "to_move", "over", "winner", "last",
                      "last_pass", "ply"},
           f"serialize must carry every MState field, got {sorted(d)}")
    spec = GAME.render(s)
    ok(spec["board"] == {"type": "hex", "shape": "hexagon", "size": 5}, "board spec")
    ok(len(spec["pieces"]) == len(s.board), "one piece per stone")
    ok(all(p["owner"] in (0, 1) for p in spec["pieces"]), "piece owner is the COLOUR")
    ok(spec["reserve"] == {"0": {"R": 1, "B": 1}, "1": {"R": 1, "B": 1}},
       "both colour chips are offered to both seats")
    # The tray is a COLOUR PICKER, so each chip must be tinted by the stone it
    # puts on the board, not by whose tray it sits in.  The letters must be
    # exactly the drop-move letters, and the seat indices exactly `piece.owner`.
    ok(spec["reserveOwners"] == {"R": 0, "B": 1}, "reserveOwners tints by stone colour")
    ok(set(spec["reserveOwners"]) == set(spec["reserve"]["0"]),
       "reserveOwners must cover exactly the tray letters")
    for mv in GAME.legal_moves(s):
        ok(mv.partition("@")[0] in spec["reserveOwners"],
           f"drop letter of {mv} must be a tray chip")
    for p in spec["pieces"]:
        ok(p["owner"] == spec["reserveOwners"][
            "R" if p["owner"] == 0 else "B"], "piece owner agrees with its chip")
    ok(isinstance(spec["caption"], str) and spec["caption"], "caption")
    ok(GAME.describe_move(GAME.initial_state(), "R@0,0") == "P1 Red 0,0", "move notation")
    ok(GAME.describe_move(GAME.initial_state(), "pass") == "P1 pass", "pass notation")


# --------------------------------------------------------------------------- #
# Frozen oracle games: full move sequences produced by AbstractPlay `gameslib`
# (which chose the moves AND adjudicated the result).  Replaying them here keeps
# the oracle's verdict as a pure-stdlib regression anchor.  Moves are already
# translated into our notation; `winner` is the seat index (None = draw).
ORACLE_GAMES = [
    # the mover completes a QUART of their own colour -> they lose
    (['B@-3,3', 'B@-1,0', 'R@0,-3', 'R@4,-1', 'B@-2,2', 'R@0,0', 'R@-1,-1', 'B@-2,1'],
     0),
    (['B@-3,0', 'R@-1,2', 'B@3,0', 'B@2,1', 'R@3,-3', 'R@-2,3', 'R@-1,3', 'B@-1,-2',
      'R@-2,4'],
     1),
    # the mover completes a QUINT of their own colour -> they win
    (['B@-4,0', 'R@1,2', 'R@4,-4', 'R@4,-1', 'B@0,4', 'R@-3,0', 'B@3,1', 'R@-2,1',
      'R@-3,-1', 'B@2,1', 'R@-1,0', 'B@0,0', 'R@-3,1'],
     0),
    (['R@-1,-2', 'B@-4,2', 'R@0,2', 'R@3,-4', 'R@3,1', 'R@0,-2', 'R@-2,1', 'R@2,-4',
      'R@-3,2', 'B@1,2', 'B@2,-1', 'B@-1,-3', 'R@1,-3'],
     0),
    # a quart of the mover's colour built by the OPPONENT last turn -> mover loses
    (['R@0,-4', 'R@0,-3', 'R@-1,-1', 'R@-3,0', 'R@-2,0', 'R@-2,-1', 'B@4,-3'],
     1),
    (['B@-3,3', 'R@-1,-2', 'B@3,-4', 'B@-1,4', 'B@-2,4', 'R@0,1', 'R@3,-2', 'R@1,2',
      'B@-2,3', 'B@1,3'],
     0),
    # a quint of the mover's colour built by the OPPONENT last turn -> mover wins
    (['B@0,4', 'B@1,-4', 'R@-2,2', 'B@0,-2', 'R@-2,0', 'B@-1,-3', 'R@-4,0', 'R@-4,4',
      'R@-2,-2', 'R@-2,-1', 'B@-4,3', 'R@-3,0', 'R@3,-1'],
     0),
    (['R@-4,1', 'B@3,1', 'B@4,-1', 'R@0,-1', 'R@2,2', 'B@-4,0', 'R@1,-2', 'R@2,0',
      'B@-2,0', 'R@1,2', 'B@-1,0', 'B@-2,1', 'B@2,-2', 'R@0,0', 'B@-3,0', 'R@-1,4'],
     1),
]


def t_oracle_games():
    for idx, (moves, winner) in enumerate(ORACLE_GAMES):
        s = GAME.initial_state()
        for i, mv in enumerate(moves):
            ok(not GAME.is_terminal(s), f"oracle game {idx} ended early at ply {i}")
            ok(mv in GAME.legal_moves(s), f"oracle game {idx}: {mv} not legal at ply {i}")
            s = GAME.apply_move(s, mv)
        ok(GAME.is_terminal(s), f"oracle game {idx} must be terminal after {len(moves)} plies")
        ok(s.winner == winner,
           f"oracle game {idx}: winner {s.winner} != oracle {winner}")


def main():
    for fn in (t_board_and_opening, t_group_cap, t_win_and_loss,
               t_only_your_own_colour, t_designer_diagrams, t_precedence,
               t_pass_and_draw,
               t_pass_is_reachable, t_oracle_games, t_serialize_and_render,
               t_termination):
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"manalath selftest: {CHECKS} assertions passed "
          f"({len(ORACLE_GAMES)} frozen oracle games)")


if __name__ == "__main__":
    main()
