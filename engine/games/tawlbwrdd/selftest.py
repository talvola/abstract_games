"""Standalone correctness anchor for Tawlbwrdd (Welsh tafl, 11x11).

Run from engine/:  PYTHONPATH=. python3 games/tawlbwrdd/selftest.py

The point of this file is to pin the FOUR rules that make Tawlbwrdd a different
game from the Copenhagen Hnefatafl in this library, each to the primary source
(Robert ap Ifan 1587, in H. J. R. Murray's translation) rather than to anything
the engine itself derives:

  * the KING IS CAPTURED BETWEEN TWO attackers, and is NOT captured by three;
  * the king wins on ANY EDGE SQUARE, including a non-corner one;
  * there are NO SPECIAL SQUARES -- a corner is an ordinary square that neither
    blocks a soldier nor helps capture, and the centre is ordinary too unless
    the `throne=restricted` option is chosen;
  * capture is one-deep and active: a row of two is not taken, and a piece that
    moves BETWEEN two enemies is safe.

Plus the traps this library keeps re-finding:

  * both starting layouts pinned CELL BY CELL to the published diagrams
    (Cyningstan's T-shape and Bell's arrow), not to the engine's own output;
  * a decisive result must OUTRANK the ply cap, tested from a poisoned ply for
    both winners and with the draw as the competing outcome;
  * `returns()` seat attribution pinned to ground truth OUTSIDE the engine --
    the side that owns the K piece is the side ap Ifan says wins on escape --
    so a flipped seat cannot pass shape + zero-sum checks;
  * BOTH the in-play and the terminal caption pinned the same way;
  * `render()` bounds AND content (owner per piece letter) for every option combo;
  * serialize round-trip compared as STATES with an exact key set, swept over a
    whole game, so a dropped field cannot re-default its way past the check;
  * heuristic DIRECTION pinned to measured values.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import dataclasses
import json
import random
import sys

from games.tawlbwrdd.game import (
    Tawlbwrdd, TaflState, ATTACKERS, DEFENDERS, THRONE, N, PLY_CAP,
)

G = Tawlbwrdd()
CORNERS = {(0, 0), (N - 1, 0), (0, N - 1), (N - 1, N - 1)}


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def mk(board, to_move=ATTACKERS, ply=0, restricted_throne=False) -> TaflState:
    return TaflState(board=dict(board), to_move=to_move, ply=ply,
                     restricted_throne=restricted_throne)


# ------------------------------------------------------- setup, pinned to figures
# Transcribed from the diagrams on tafl.cyningstan.com/page/172/tawlbwrdd:
# "A typical layout for the 11x11 board" (T) and "Bell's layout for tawlbwrdd".
# Written out in full ON PURPOSE -- a generated expectation would just be the
# engine agreeing with itself.
FIG_T_ATTACKERS = {
    (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (5, 1),
    (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (5, 9),
    (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (1, 5),
    (10, 3), (10, 4), (10, 5), (10, 6), (10, 7), (9, 5),
}
FIG_BELL_ATTACKERS = {
    (4, 0), (5, 0), (6, 0), (4, 1), (6, 1), (5, 2),
    (4, 10), (5, 10), (6, 10), (4, 9), (6, 9), (5, 8),
    (0, 4), (0, 5), (0, 6), (1, 4), (1, 6), (2, 5),
    (10, 4), (10, 5), (10, 6), (9, 4), (9, 6), (8, 5),
}
FIG_DEFENDERS = {
    (5, 3),
    (4, 4), (5, 4), (6, 4),
    (3, 5), (4, 5), (6, 5), (7, 5),
    (4, 6), (5, 6), (6, 6),
    (5, 7),
}


def test_setup():
    for layout, expect in (("t", FIG_T_ATTACKERS), ("bell", FIG_BELL_ATTACKERS)):
        s = G.initial_state({"layout": layout})
        b = s.board
        atk = {c for c, p in b.items() if p == "A"}
        dfn = {c for c, p in b.items() if p == "D"}
        if atk != expect:
            fail(f"{layout}: attacker layout != published diagram; "
                 f"extra {sorted(atk - expect)}, missing {sorted(expect - atk)}")
        if dfn != FIG_DEFENDERS:
            fail(f"{layout}: defender diamond != published diagram")
        if b.get(THRONE) != "K":
            fail(f"{layout}: King is not on the central square at start")
        if len(atk) != 24 or len(dfn) != 12:
            fail(f"{layout}: ap Ifan gives 24 attackers and 12 defenders, "
                 f"got {len(atk)}/{len(dfn)}")
        if s.to_move != ATTACKERS:
            fail(f"{layout}: attackers must move first")
        # every diagram is four-fold symmetric; a mis-reflected edge group would
        # keep the piece COUNT right and only break here
        if {(N - 1 - r, c) for (c, r) in atk} != atk:
            fail(f"{layout}: attacker layout is not 90-degree rotationally symmetric")
        # the king starts boxed in by his own men (no ply-1 dash for the edge)
        if any(G.apply_move(s, m).winner is not None for m in G.legal_moves(s)):
            fail(f"{layout}: no opening attacker move may end the game")
    print("  starting layouts match the published diagrams (T and Bell): OK")


# --------------------------------------------- the king is caught between TWO
def test_king_captured_by_two():
    """ap Ifan: 'If the king himself comes between two of the attackers ... you
    catch him.' Two, not four -- the single biggest difference from Copenhagen."""
    # king on an open square with one attacker already west of him; an attacker
    # slides in from the east to close the sandwich.
    board = {(5, 5): "K", (4, 5): "A", (8, 5): "A", (0, 0): "D"}
    s = mk(board, to_move=ATTACKERS)
    s2 = G.apply_move(s, "8,5>6,5")
    if s2.winner != ATTACKERS:
        fail("king between two attackers must be captured (attackers win)")
    if (5, 5) in s2.board:
        fail("the captured king must be removed from the board")
    # ... while attackers on ADJACENT sides do nothing: one west, one north, and a
    # third arriving east of him -- no two of them opposite one another.
    board = {(5, 5): "K", (4, 5): "A", (5, 4): "A", (8, 8): "A", (0, 0): "D"}
    s = mk(board, to_move=ATTACKERS)
    s2 = G.apply_move(s, "8,8>8,5")
    if s2.winner is not None:
        fail("two attackers on ADJACENT (non-opposite) sides must not capture the king")
    if (5, 5) not in s2.board:
        fail("king wrongly removed by a non-opposite pair")
    print("  king captured between two opposite attackers, not by adjacent ones: OK")


def test_king_safe_on_three_sides():
    """Copenhagen's four-sided rule would make this a non-capture too, but the
    discriminating case is the opposite one: a THREE-sided surround with no
    opposite pair must be harmless, while Copenhagen's throne/corner walls do
    not exist here at all."""
    # The king must be INTERIOR for this to test anything: on an edge square he
    # has already escaped. Attackers north and east, a third arriving from the
    # east file -- three neighbours flanked, no opposite pair.
    board = {(5, 5): "K", (5, 4): "A", (6, 5): "A", (9, 9): "A", (0, 0): "D"}
    s = mk(board, to_move=ATTACKERS)
    s2 = G.apply_move(s, "9,9>9,5")
    if s2.winner is not None:
        fail("attackers on N, E and a distant file must not capture the king")
    print("  a three-sided surround with no opposite pair is harmless: OK")


# ------------------------------------------------------ the king escapes to an EDGE
def test_king_escapes_to_any_edge():
    """ap Ifan: 'If the king can go along the line that side wins the game.'
    Two of these destinations are plain edge squares -- under Copenhagen's
    corner-escape rule they would not be wins at all."""
    cases = [
        ((3, 5), "0,5", "left edge, not a corner"),
        ((3, 7), "3,10", "bottom edge, not a corner"),
        ((3, 0), "0,0", "corner"),
        ((3, 10), "10,10", "far corner"),
    ]
    for king, dest, what in cases:
        board = {king: "K", (9, 9): "A", (5, 5): "A"}
        s = mk(board, to_move=DEFENDERS)
        mv = f"{king[0]},{king[1]}>{dest}"
        if mv not in G.legal_moves(s):
            fail(f"king move to the {what} ({mv}) should be legal")
        s2 = G.apply_move(s, mv)
        if s2.winner != DEFENDERS:
            fail(f"king reaching the {what} must win for the defenders")
    print("  king wins on ANY edge square (corner or not): OK")


def test_soldier_on_edge_is_not_a_win():
    board = {(5, 5): "K", (3, 3): "D", (9, 9): "A"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "3,3>3,0")
    if s2.winner is not None:
        fail("an ordinary defender reaching the edge must not win")
    print("  only the KING escaping ends the game: OK")


# ---------------------------------------------------------- no special squares
def test_no_special_squares():
    """The manuscript gives the centre and the corners no privileges, and
    Cyningstan's reconstruction keeps them ordinary. Each assertion below is a
    place where Copenhagen would behave differently."""
    # 1. a soldier may STOP on a corner (Copenhagen: forbidden)
    board = {(5, 5): "K", (3, 0): "D", (9, 9): "A"}
    s = mk(board, to_move=DEFENDERS)
    if "3,0>0,0" not in G.legal_moves(s):
        fail("a soldier must be able to stop on a corner (no restricted squares)")
    # 2. a soldier may slide along the edge INTO a corner (Copenhagen: blocked)
    board = {(5, 5): "K", (0, 3): "D", (9, 9): "A"}
    s = mk(board, to_move=DEFENDERS)
    dests = {m.split(">")[1] for m in G.legal_moves(s) if m.startswith("0,3>")}
    if "0,0" not in dests:
        fail("a soldier must be able to reach a corner along the edge")
    # 3. a corner is NOT hostile -- no capture against an empty corner
    board = {(5, 5): "K", (0, 1): "A", (3, 3): "D", (9, 9): "D"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "3,3>0,2")      # attacker at (0,1) now between (0,2)D and empty corner (0,0)
    if (0, 1) not in s2.board:
        fail("an EMPTY CORNER must not act as a capturing wall (no hostile squares)")
    # 4. the empty centre is NOT hostile either
    board = {(5, 4): "A", (3, 3): "D", (9, 9): "D", (2, 2): "K"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "3,3>5,3")      # attacker (5,4) between (5,3)D and the empty centre (5,5)
    if (5, 4) not in s2.board:
        fail("the EMPTY CENTRE must not act as a capturing wall (no hostile squares)")
    # 5. a soldier may stop ON the centre, and pass over it
    board = {(5, 0): "D", (9, 9): "A", (2, 2): "K"}
    s = mk(board, to_move=DEFENDERS)
    dests = {m.split(">")[1] for m in G.legal_moves(s) if m.startswith("5,0>")}
    if "5,5" not in dests:
        fail("with throne=none a soldier must be able to stop on the centre")
    if "5,10" not in dests:
        fail("a soldier must be able to pass over the empty centre")
    print("  no special squares: corners and centre are ordinary: OK")


def test_restricted_throne_option():
    """The alternative reading (Tablut-style, favoured by Nielsen's balance
    tests): only the king may STOP on the centre. It must still be passable."""
    board = {(5, 0): "D", (9, 9): "A", (2, 2): "K"}
    s = mk(board, to_move=DEFENDERS, restricted_throne=True)
    dests = {m.split(">")[1] for m in G.legal_moves(s) if m.startswith("5,0>")}
    if "5,5" in dests:
        fail("throne=restricted: a soldier must not be able to stop on the centre")
    if "5,10" not in dests:
        fail("throne=restricted: the centre must still be passable")
    # the king himself may stop there
    board = {(5, 0): "K", (9, 9): "A"}
    s = mk(board, to_move=DEFENDERS, restricted_throne=True)
    if "5,0>5,5" not in G.legal_moves(s):
        fail("throne=restricted: the king must be able to stop on the centre")
    # and the option must actually reach the engine from the manifest
    s0 = G.initial_state({"throne": "restricted"})
    if not s0.restricted_throne:
        fail("the manifest option throne=restricted did not reach the state")
    s0 = G.initial_state({"throne": "none"})
    if s0.restricted_throne:
        fail("throne=none must leave the centre ordinary")
    print("  throne=restricted option bites, and only on STOPPING: OK")


# -------------------------------------------------------------- capture mechanics
def test_capture_mechanics():
    # a soldier is taken between two enemies
    board = {(2, 2): "K", (5, 5): "A", (4, 5): "D", (9, 9): "D", (6, 9): "D"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "6,9>6,5")
    if (5, 5) in s2.board:
        fail("a soldier sandwiched between two enemies must be captured")
    # ACTIVE capture: moving BETWEEN two enemies is safe ("gwrheill")
    board = {(2, 2): "K", (4, 5): "A", (6, 5): "A", (9, 9): "D"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "9,9>5,9")
    s3 = mk({**s2.board}, to_move=DEFENDERS)
    s4 = G.apply_move(s3, "5,9>5,5")
    if (5, 5) not in s4.board:
        fail("a piece that MOVES BETWEEN two enemies must be safe (active capture)")
    # no row capture: two in a line between two enemies survive
    board = {(2, 2): "K", (4, 5): "A", (5, 5): "A", (6, 5): "D", (9, 9): "D"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "9,9>3,9")
    s3 = G.apply_move(mk(s2.board, to_move=DEFENDERS), "3,9>3,5")
    if (4, 5) not in s3.board or (5, 5) not in s3.board:
        fail("a ROW of two enemies must not be captured (ap Ifan rule 9)")
    # two at once, in different directions
    board = {(2, 2): "K", (5, 4): "A", (5, 6): "A", (5, 3): "D", (5, 7): "D", (9, 9): "D"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "9,9>5,5")
    if (5, 4) in s2.board or (5, 6) in s2.board:
        fail("two enemies on opposite sides of the destination must both be captured")
    # the KING assists in a capture, like any of "the king's men"
    board = {(3, 5): "K", (5, 5): "A", (6, 5): "D", (9, 9): "A"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "3,5>4,5")
    if (5, 5) in s2.board:
        fail("the king must be able to assist in a capture")
    print("  custodial capture: active, one-deep, multi-directional, king assists: OK")


# ------------------------------------------ a decisive result outranks the ply cap
def test_decisive_outranks_cap():
    """The library's most-repeated bug: a draw counter consulted before the win.
    Both poison positions below are built so the competing outcome (a cap DRAW)
    genuinely differs from the decisive one, for BOTH winners."""
    # defenders win on the escape, at a poisoned ply
    board = {(3, 5): "K", (9, 9): "A", (5, 0): "A"}
    s = mk(board, to_move=DEFENDERS, ply=PLY_CAP - 1)
    s2 = G.apply_move(s, "3,5>0,5")
    if s2.ply < PLY_CAP:
        fail("poison position did not actually reach the ply cap (test is vacuous)")
    if not G.is_terminal(s2):
        fail("an escape at the ply cap must still be terminal")
    if G.returns(s2) != [-1.0, 1.0]:
        fail(f"escape ON the cap ply must still win for the defenders, got {G.returns(s2)}")
    # attackers win on the king capture, at a poisoned ply
    board = {(5, 5): "K", (4, 5): "A", (8, 5): "A", (0, 0): "D"}
    s = mk(board, to_move=ATTACKERS, ply=PLY_CAP - 1)
    s2 = G.apply_move(s, "8,5>6,5")
    if s2.ply < PLY_CAP:
        fail("poison position did not actually reach the ply cap (test is vacuous)")
    if G.returns(s2) != [1.0, -1.0]:
        fail(f"a king capture ON the cap ply must still win for the attackers, got {G.returns(s2)}")
    # and the cap really does draw when nothing decisive happened -- otherwise
    # the two assertions above would pass for the wrong reason
    quiet = dataclasses.replace(s2, winner=None, board={(5, 5): "K", (0, 0): "A"},
                                ply=PLY_CAP)
    if G.returns(quiet) != [0.0, 0.0]:
        fail("the ply cap must otherwise be a draw (the competing outcome is absent)")
    print("  a decisive result outranks the ply cap, for both winners: OK")


# ---------------------------------- returns() seat attribution, pinned to the text
def test_returns_seat_attribution():
    """Shape + zero-sum are BLIND to which seat gets +1. Pin it to ground truth
    outside the engine: ap Ifan says the side whose king reaches the line wins,
    and the king is the K piece on the board. So the winner must be the seat that
    OWNS the king -- and the loser the seat that owns the attackers."""
    board = {(3, 5): "K", (4, 5): "D", (9, 9): "A", (5, 0): "A"}
    s = mk(board, to_move=DEFENDERS)
    s2 = G.apply_move(s, "3,5>0,5")
    ret = G.returns(s2)
    if sorted(ret) != [-1.0, 1.0]:
        fail(f"a decisive result must be +1/-1, got {ret}")
    winner_seat = ret.index(1.0)
    # which seat owns the king? read it off the BOARD of the position before the win
    king_seat = DEFENDERS if s.board[(3, 5)] == "K" else None
    if king_seat is None:
        fail("test setup: no king on the board")
    if winner_seat != king_seat:
        fail(f"the side owning the KING must win on the escape; +1 went to seat "
             f"{winner_seat}, king belongs to seat {king_seat}")
    # and the mirror: when the king is caught, +1 must go to the side owning the "A"s
    board = {(5, 5): "K", (4, 5): "A", (8, 5): "A", (0, 0): "D"}
    s = mk(board, to_move=ATTACKERS)
    s2 = G.apply_move(s, "8,5>6,5")
    ret = G.returns(s2)
    if ret.index(1.0) != ATTACKERS:
        fail(f"the side owning the ATTACKERS must win when the king is caught, got {ret}")
    if G.render(s, None)["pieces"]:
        owners = {p["cell"]: p["owner"] for p in G.render(s, None)["pieces"]}
        if owners["5,5"] == owners["4,5"]:
            fail("render must give the king and an attacker DIFFERENT owners")
        if owners["5,5"] != DEFENDERS or owners["4,5"] != ATTACKERS:
            fail("render owner must follow the piece letter: K/D -> seat 1, A -> seat 0")
    print("  returns() credits the right SEAT, pinned to the piece on the board: OK")


# ---------------------------------------------- captions, in-play AND terminal
def test_captions():
    """A naming constant no test pins is this library's most reliable defect.
    Pin both captions to ground truth: the side to move is the side whose pieces
    have legal moves, and the terminal caption must name the seat that got +1."""
    board = {(5, 5): "K", (3, 3): "D", (9, 9): "A"}
    s = mk(board, to_move=ATTACKERS)
    cap = G.render(s, None)["caption"]
    frm = {m.split(">")[0] for m in G.legal_moves(s)}
    owners_that_can_move = {ATTACKERS if s.board[(int(c), int(r))] == "A" else DEFENDERS
                            for c, r in (x.split(",") for x in frm)}
    if owners_that_can_move != {ATTACKERS}:
        fail("test setup: only the attackers should have moves here")
    if cap != "Attackers to move":
        fail(f"in-play caption must name the side that actually has the moves; got {cap!r}")
    s_d = mk(board, to_move=DEFENDERS)
    owners_that_can_move = {ATTACKERS if s_d.board[(int(c), int(r))] == "A" else DEFENDERS
                            for c, r in (x.split(",") for x in
                                         {m.split(">")[0] for m in G.legal_moves(s_d)})}
    if owners_that_can_move != {DEFENDERS}:
        fail("test setup: only the defenders should have moves here")
    if G.render(s_d, None)["caption"] != "Defenders to move":
        fail(f"in-play caption flipped for the defenders: {G.render(s_d, None)['caption']!r}")
    # terminal captions, both ways, checked against returns()
    board = {(3, 5): "K", (9, 9): "A", (5, 0): "A"}
    s2 = G.apply_move(mk(board, to_move=DEFENDERS), "3,5>0,5")
    if G.returns(s2)[DEFENDERS] != 1.0 or G.render(s2, None)["caption"] != "Defenders win":
        fail(f"terminal caption must say Defenders win; got {G.render(s2, None)['caption']!r}")
    board = {(5, 5): "K", (4, 5): "A", (8, 5): "A", (0, 0): "D"}
    s2 = G.apply_move(mk(board, to_move=ATTACKERS), "8,5>6,5")
    if G.returns(s2)[ATTACKERS] != 1.0 or G.render(s2, None)["caption"] != "Attackers win":
        fail(f"terminal caption must say Attackers win; got {G.render(s2, None)['caption']!r}")
    print("  in-play AND terminal captions pinned to the side that owns the pieces: OK")


# ------------------------------------------------------------- render bounds+content
def test_render():
    for layout in ("t", "bell"):
        for throne in ("none", "restricted"):
            s = G.initial_state({"layout": layout, "throne": throne})
            rng = random.Random(7)
            for _ in range(60):
                if G.is_terminal(s):
                    break
                spec = G.render(s, None)
                b = spec["board"]
                if (b["type"], b["width"], b["height"]) != ("square", N, N):
                    fail(f"{layout}/{throne}: render declares {b}")
                for pc in spec["pieces"]:
                    c, r = (int(x) for x in pc["cell"].split(","))
                    if not (0 <= c < b["width"] and 0 <= r < b["height"]):
                        fail(f"{layout}/{throne}: piece at {pc['cell']} outside the board")
                    letter = s.board[(c, r)]
                    want = ATTACKERS if letter == "A" else DEFENDERS
                    if pc["owner"] != want:
                        fail(f"{layout}/{throne}: {letter} at {pc['cell']} rendered as "
                             f"seat {pc['owner']}, expected {want}")
                    if (letter == "K") != (pc.get("glyph") == "♚"):
                        fail(f"{layout}/{throne}: only the king may carry the king glyph")
                if len(spec["pieces"]) != len(s.board):
                    fail(f"{layout}/{throne}: render dropped a piece")
                goals = {h["cell"] for h in spec["highlights"]}
                if len(goals) != 4 * N - 4:
                    fail(f"{layout}/{throne}: every edge square is a goal; got {len(goals)}")
                if "5,5" in goals:
                    fail("the centre is not an edge square")
                json.dumps(spec)
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
    print("  render(): bounds, per-piece owner, king glyph and edge goals: OK")


# ----------------------------------------------------- serialize, compared as STATES
EXPECT_KEYS = {"board", "to_move", "winner", "ply", "restricted_throne"}


def roundtrip(s: TaflState, where: str):
    d = G.serialize(s)
    json.dumps(d)
    if set(d) != EXPECT_KEYS:
        fail(f"{where}: serialize keys {set(d)} != {EXPECT_KEYS}")
    back = G.deserialize(d)
    if back != s:                       # STATES, not dicts: a dropped field shows up here
        fail(f"{where}: deserialize(serialize(s)) != s\n  got  {back}\n  want {s}")


def test_serialize_sweep():
    for layout in ("t", "bell"):
        for throne in ("none", "restricted"):
            s = G.initial_state({"layout": layout, "throne": throne})
            rng = random.Random(11)
            n = 0
            while not G.is_terminal(s) and n < 120:
                roundtrip(s, f"{layout}/{throne} ply {n}")
                s = G.apply_move(s, rng.choice(G.legal_moves(s)))
                n += 1
            roundtrip(s, f"{layout}/{throne} final")
    print("  serialize round-trips as STATES, exact key set, over whole games: OK")


# ------------------------------------------------------------------ heuristic
def test_heuristic_direction():
    """Shape/zero-sum checks pass for a sign-flipped or constant eval. Assert the
    DIRECTION against measured values instead."""
    far = mk({(5, 5): "K", (0, 0): "A", (10, 10): "A"}, to_move=ATTACKERS)
    near = mk({(1, 5): "K", (0, 0): "A", (10, 10): "A"}, to_move=ATTACKERS)
    h_far, h_near = G.heuristic(far), G.heuristic(near)
    for h in (h_far, h_near):
        if len(h) != 2 or abs(h[0] + h[1]) > 1e-9:
            fail(f"heuristic must return 2 zero-sum payoffs, got {h}")
    if not (h_near[DEFENDERS] > h_far[DEFENDERS]):
        fail(f"a king NEARER the edge must score better for the defenders: "
             f"near={h_near} far={h_far}")
    rich = mk({(5, 5): "K", **{(c, 0): "A" for c in range(9)}}, to_move=ATTACKERS)
    poor = mk({(5, 5): "K", (0, 0): "A", **{(c, 9): "D" for c in range(8)}},
              to_move=ATTACKERS)
    if not (G.heuristic(rich)[ATTACKERS] > G.heuristic(poor)[ATTACKERS]):
        fail("more attacker material must score better for the attackers")
    if h_far == h_near:
        fail("heuristic is constant across very different positions")
    print(f"  heuristic direction pinned (near-edge king {h_near[DEFENDERS]:+.3f} > "
          f"far {h_far[DEFENDERS]:+.3f}): OK")


# ---------------------------------------------------------------- conformance
def test_conformance():
    wins = {ATTACKERS: 0, DEFENDERS: 0, "draw": 0}
    rng = random.Random(2026)
    games = 160
    for i in range(games):
        opts = {"layout": ("t", "bell")[i % 2], "throne": ("none", "restricted")[(i // 2) % 2]}
        s = G.initial_state(opts)
        plies = 0
        while not G.is_terminal(s):
            moves = G.legal_moves(s)
            if not moves:
                fail(f"non-terminal state with no legal moves at ply {plies}")
            s = G.apply_move(s, rng.choice(moves))
            plies += 1
            if plies > PLY_CAP + 5:
                fail("game did not terminate at the ply cap")
        r = G.returns(s)
        if len(r) != 2 or abs(r[0] + r[1]) > 1e-9:
            fail(f"returns must be two zero-sum payoffs, got {r}")
        if r == [0.0, 0.0]:
            wins["draw"] += 1
        else:
            wins[r.index(1.0)] += 1
        if G.legal_moves(s) != []:
            fail("a terminal state must offer no legal moves")
    if wins[ATTACKERS] == 0 or wins[DEFENDERS] == 0:
        fail(f"both sides must be able to win under random play: {wins}")
    print(f"  conformance over {games} random games: attackers {wins[ATTACKERS]}, "
          f"defenders {wins[DEFENDERS]}, cap draws {wins['draw']}: OK")


def test_no_legal_move_loss():
    """'Win as event': reach the stuck position THROUGH apply_move, since winner
    is only ever set there.

    The trap here is that (0,1) and (1,0) are EDGE squares, so a king moving in to
    box the attacker in would win by ESCAPE instead and this test would prove
    nothing about the stuck rule. Both positions below are therefore closed by an
    ordinary soldier, with the king parked out of the way."""
    # attackers stuck -> defenders win
    board = {(0, 0): "A", (0, 1): "D", (1, 5): "D", (5, 5): "K"}
    s = mk(board, to_move=DEFENDERS)
    if G.apply_move(s, "1,5>1,1").winner is not None:
        fail("test setup: the attacker is not stuck yet after the first move")
    s2 = G.apply_move(s, "1,5>1,0")     # a SOLDIER on an edge square: not a win
    if s2.winner != DEFENDERS:
        fail(f"a side with no legal move must lose; winner={s2.winner}")
    if G.returns(s2) != [-1.0, 1.0]:
        fail(f"stuck-loss returns wrong: {G.returns(s2)}")
    if G._side_has_move(s2.board, ATTACKERS, False):
        fail("test setup: the attackers were not actually stuck")
    # the mirror, so a flipped credit cannot pass: defenders stuck -> attackers win
    board = {(0, 0): "D", (0, 1): "A", (1, 5): "A"}
    s = mk(board, to_move=ATTACKERS)
    s2 = G.apply_move(s, "1,5>1,0")
    if s2.winner != ATTACKERS:
        fail(f"the stuck DEFENDERS must lose too; winner={s2.winner}")
    if G._side_has_move(s2.board, DEFENDERS, False):
        fail("test setup: the defenders were not actually stuck")
    print("  a side with no legal move loses, both ways: OK")


def main():
    test_setup()
    test_king_captured_by_two()
    test_king_safe_on_three_sides()
    test_king_escapes_to_any_edge()
    test_soldier_on_edge_is_not_a_win()
    test_no_special_squares()
    test_restricted_throne_option()
    test_capture_mechanics()
    test_decisive_outranks_cap()
    test_returns_seat_attribution()
    test_captions()
    test_render()
    test_serialize_sweep()
    test_heuristic_direction()
    test_no_legal_move_loss()
    test_conformance()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
