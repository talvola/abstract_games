#!/usr/bin/env python3
"""Correctness anchors for Congo (Demian Freeling, 1982).

No published perft exists; the anchors are a HAND-DERIVED perft (d1 = 24 and
d2 = 24^2 = 576 were counted piece-by-piece from the initial position: Giraffe
2 jumps, Elephants 1 jump each, Zebra 1, 19 pawn moves, everything else boxed
in; the sides cannot interact within one move each, so d2 is exactly 24^2),
a frozen d3, and rule positions pinning every Wikipedia/mindsports.nl rule:

  * setup; Lion castle confinement + the facing-lions queen capture;
  * Elephant / Giraffe jumps (move-only vs capture rules);
  * Crocodile file-slide toward the river (both sides of it) + river rank-slide;
  * Pawn straight-forward CAPTURE, past-river retreat (move-only, no jumping),
    promotion; Superpawn sideways capture + backward move-only retreats;
  * Monkey: move-only steps, chain jumps (optional stopping, direction changes,
    no re-jumping a man, landing must be vacant, jumping the Lion ends the
    chain), captures removed after the whole move;
  * drowning timing via apply_move (enter = safe; stay/move-within = drowned at
    the end of the owner's next turn; crocodile exempt; opponent's river piece
    untouched on my turn; monkey drowning keeps its captures);
  * win by lion capture (step / facing / monkey jump); bare-lions draw;
    threefold repetition; 500-playout termination stats.

Pure stdlib + agp only. Run: PYTHONPATH=. python3 games/congo/selftest.py
"""

from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agp.conformance import check as conformance_check  # noqa: E402

import importlib.util  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("congo_game", os.path.join(_HERE, "game.py"))
_mod = importlib.util.module_from_spec(_spec)
sys.modules["congo_game"] = _mod
_spec.loader.exec_module(_mod)

Congo = _mod.Congo
CongoState = _mod.CongoState

G = Congo()

W, B = 0, 1
LIONS = {(3, 0): (W, "L"), (3, 6): (B, "L")}   # default anchors, out of the way


def fail(msg):
    print("SELFTEST FAILED:", msg, file=sys.stderr)
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


def state(pieces, to_move=0, lions=True):
    b = dict(LIONS) if lions else {}
    b.update(pieces)
    return CongoState(board=b, to_move=to_move)


def moves(s):
    return set(G.legal_moves(s))


def dests_from(s, frm):
    out = set()
    for m in G.legal_moves(s):
        parts = m.split(">")
        if parts[0] == f"{frm[0]},{frm[1]}" and len(parts) == 2:
            c, r = parts[1].split(",")
            out.add((int(c), int(r)))
    return out


# --------------------------------------------------------------------------- #
def test_conformance():
    with open(os.path.join(_HERE, "manifest.json")) as fh:
        manifest = json.load(fh)
    rep = conformance_check(G, manifest, games=30, seed=7)
    if not rep.ok:
        fail("conformance:\n" + rep.summary())


def test_setup_and_perft():
    s0 = G.initial_state()
    check(not G.is_terminal(s0), "start must not be terminal")
    check(len(s0.board) == 28, f"28 men at start, got {len(s0.board)}")
    back = "GMELECZ"
    for c, k in enumerate(back):
        check(s0.board.get((c, 0)) == (W, k), f"white {k} on file {c}")
        check(s0.board.get((c, 6)) == (B, k), f"black {k} on file {c}")
        check(s0.board.get((c, 1)) == (W, "P"), "white pawn rank 2")
        check(s0.board.get((c, 5)) == (B, "P"), "black pawn rank 6")
    d = G.serialize(s0)
    check(G.serialize(G.deserialize(d)) == d, "serialize must round-trip")

    def perft(s, depth):
        if depth == 0:
            return 1
        if G.is_terminal(s):
            return 0
        return sum(perft(G.apply_move(s, m), depth - 1) for m in G.legal_moves(s))

    check(perft(s0, 1) == 24, "perft(1) == 24 (hand-derived)")
    check(perft(s0, 2) == 576, "perft(2) == 576 (hand-derived, 24^2)")
    check(perft(s0, 3) == 14332, "perft(3) == 14332 (frozen)")


# --------------------------------------------------------------------------- #
def test_lion():
    # confinement: from the castle corner c3=(2,2) only in-castle king steps
    # (the extra pawn avoids the bare-lions adjudication)
    s = CongoState(board={(2, 2): (W, "L"), (3, 6): (B, "L"), (0, 6): (B, "P")})
    d = dests_from(s, (2, 2))
    check(d == {(2, 1), (3, 1), (3, 2)},
          f"lion confined to its castle; got {sorted(d)}")

    # facing lions on a file: open river square between -> queen capture, win
    s = CongoState(board={(2, 2): (W, "L"), (2, 4): (B, "L")})
    check("2,2>2,4" in moves(s), "facing lions (file) capture must be legal")
    s2 = G.apply_move(s, "2,2>2,4")
    check(s2.winner == W and G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0],
          "lion capture must end the game")
    # blocked file -> no capture
    s = CongoState(board={(2, 2): (W, "L"), (2, 4): (B, "L"), (2, 3): (B, "P")})
    check("2,2>2,4" not in moves(s), "a blocker kills the facing capture")
    # diagonal facing
    s = CongoState(board={(2, 2): (W, "L"), (4, 4): (B, "L")})
    check("2,2>4,4" in moves(s), "facing lions (diagonal) capture must be legal")
    # non-aligned lions: no long move, king steps only
    s = CongoState(board={(3, 2): (W, "L"), (2, 4): (B, "L"), (0, 0): (W, "P")})
    d = dests_from(s, (3, 2))
    check(d == {(2, 1), (3, 1), (4, 1), (2, 2), (4, 2)},
          f"non-aligned lions: king steps only; got {sorted(d)}")
    # black lion is confined to ITS castle (rows 4-6)
    s = CongoState(board={(3, 0): (W, "L"), (2, 4): (B, "L"), (0, 0): (W, "P")},
                   to_move=B)
    d = dests_from(s, (2, 4))
    check(d == {(2, 5), (3, 5), (3, 4)}, f"black castle confinement; got {sorted(d)}")


def test_zebra():
    s = state({(3, 2): (W, "Z")})
    d = dests_from(s, (3, 2))
    check(d == {(1, 1), (1, 3), (2, 0), (4, 0), (2, 4), (4, 4), (5, 1), (5, 3)},
          f"zebra = chess knight; got {sorted(d)}")


def test_elephant():
    # own piece adjacent blocks the step but NOT the jump over it
    s = state({(4, 2): (W, "E"), (4, 3): (W, "P"), (4, 4): (B, "P")})
    d = dests_from(s, (4, 2))
    check((4, 3) not in d, "elephant step blocked by own piece")
    check((4, 4) in d, "elephant 2-jump over an occupied square captures beyond")
    check((5, 3) not in d and (3, 3) not in d, "elephant has no diagonal move")
    # full move set on an empty board
    s = state({(4, 2): (W, "E")})
    d = dests_from(s, (4, 2))
    check(d == {(3, 2), (5, 2), (4, 1), (4, 3), (2, 2), (6, 2), (4, 0), (4, 4)},
          f"elephant: 1-2 orthogonal only; got {sorted(d)}")


def test_giraffe():
    # step is move-only: an adjacent enemy is NOT capturable
    s = state({(5, 2): (W, "G"), (5, 3): (B, "P"), (5, 4): (B, "Z")})
    d = dests_from(s, (5, 2))
    check((5, 3) not in d, "giraffe step may not capture")
    check((5, 4) in d, "giraffe 2-jump captures (over an occupied square)")
    s2 = G.apply_move(s, "5,2>5,4")
    check(s2.board[(5, 4)] == (W, "G") and (5, 3) in s2.board,
          "giraffe jump captures the TARGET only, not the jumped-over man")
    # all 8 directions at distance 2, king steps to empty
    s = state({(5, 2): (W, "G")})
    d = dests_from(s, (5, 2))
    for t in ((5, 0), (3, 2), (3, 4), (5, 4), (4, 1), (6, 1), (4, 3), (6, 3)):
        check(t in d, f"giraffe should reach {t}")
    check((3, 0) not in d, "giraffe may not land on its own lion")


def test_crocodile():
    # on land: file slide toward the river, up to and including it
    s = state({(1, 0): (W, "C")})
    d = dests_from(s, (1, 0))
    for t in ((1, 1), (1, 2), (1, 3)):
        check(t in d, f"croc file-slide should reach {t}")
    check((1, 4) not in d, "croc slide must STOP at the river")
    # slide captures the first piece in the way, not beyond
    s = state({(1, 0): (W, "C"), (1, 2): (B, "P")})
    d = dests_from(s, (1, 0))
    check((1, 2) in d and (1, 3) not in d, "croc slide blocked by first piece")
    # from the FAR side of the river it slides back TOWARD the river
    s = state({(1, 5): (W, "C")})
    d = dests_from(s, (1, 5))
    check((1, 4) in d and (1, 3) in d, "croc past the river slides back to it")
    check((1, 2) not in d, "…and not beyond")
    # in the river: rook along the row
    s = state({(3, 3): (W, "C"), (5, 3): (B, "P")})
    d = dests_from(s, (3, 3))
    for t in ((0, 3), (1, 3), (2, 3), (4, 3), (5, 3)):
        check(t in d, f"river croc should reach {t}")
    check((6, 3) not in d, "river slide blocked by the pawn")
    check((3, 2) in d and (3, 4) in d, "river croc keeps its king step")


def test_pawn():
    # forward: move AND capture straight or diagonal
    s = state({(3, 2): (W, "P"), (3, 3): (B, "P"), (2, 3): (B, "Z")})
    d = dests_from(s, (3, 2))
    check(d == {(2, 3), (3, 3), (4, 3)}, f"pawn forward fan; got {sorted(d)}")
    s2 = G.apply_move(s, "3,2>3,3")
    check(s2.board[(3, 3)] == (W, "P"), "pawn CAPTURES straight ahead (unlike chess)")
    # no retreat before the river
    check((3, 1) not in d, "no retreat on its own side")
    # past the river: retreat 1 or 2 straight back, move-only, no jumping
    s = state({(1, 5): (W, "P")})
    d = dests_from(s, (1, 5))
    check((1, 4) in d and (1, 3) in d, "past-river pawn retreats 1 or 2")
    s = state({(1, 5): (W, "P"), (1, 4): (B, "P")})
    d = dests_from(s, (1, 5))
    check((1, 4) not in d and (1, 3) not in d,
          "retreat cannot capture and cannot jump")
    # black pawn mirrors (past river = rows < 3, retreat = +row)
    s = state({(1, 2): (B, "P")}, to_move=B)
    d = dests_from(s, (1, 2))
    check((1, 3) in d and (1, 4) in d, "black past-river pawn retreats upward")
    # promotion: reaching the last rank makes a Superpawn (automatic)
    s = state({(1, 5): (W, "P")})
    s2 = G.apply_move(s, "1,5>1,6")
    check(s2.board[(1, 6)] == (W, "S"), "pawn promotes to superpawn on rank 7")


def test_superpawn():
    s = state({(3, 4): (W, "S"), (2, 4): (B, "P"), (3, 3): (B, "P")})
    d = dests_from(s, (3, 4))
    check((2, 4) in d, "superpawn captures sideways")
    check((4, 4) in d, "superpawn moves sideways")
    check((3, 3) not in d and (3, 2) not in d,
          "superpawn retreat is move-only and non-jumping")
    for t in ((2, 5), (3, 5), (4, 5)):
        check(t in d, f"superpawn keeps the pawn forward fan ({t})")
    s = state({(3, 4): (W, "S")})
    d = dests_from(s, (3, 4))
    for t in ((3, 3), (3, 2), (2, 3), (1, 2), (4, 3), (5, 2)):
        check(t in d, f"superpawn retreat straight/diagonal 1-2 ({t})")
    # retreats are position-independent (also on its OWN side of the river)
    s = state({(1, 1): (W, "S")})
    d = dests_from(s, (1, 1))
    check((1, 0) in d and (0, 0) in d and (2, 0) in d,
          "superpawn retreats on its own side too")


# --------------------------------------------------------------------------- #
def test_monkey():
    # steps are move-only
    s = state({(2, 1): (W, "M"), (3, 2): (B, "P")})
    check("2,1>3,2" not in moves(s), "monkey step may not capture")
    # single jump over an adjacent enemy to the vacant square beyond
    check("2,1>4,3" in moves(s), "monkey jump capture")
    s2 = G.apply_move(s, "2,1>4,3")
    check((3, 2) not in s2.board and s2.board[(4, 3)] == (W, "M"), "jumped man removed")
    # landing must be vacant
    s = state({(2, 1): (W, "M"), (3, 2): (B, "P"), (4, 3): (B, "Z")})
    check("2,1>4,3" not in moves(s), "occupied landing square blocks the jump")
    # a man may be jumped only once (no immediate back-and-forth)
    s = state({(2, 0): (W, "M"), (2, 1): (B, "P")})
    chains = [m for m in moves(s) if m.startswith("2,0>") and len(m.split(">")) >= 2
              and m != "2,0>1,0" and m != "2,0>3,0" and m != "2,0>1,1" and m != "2,0>3,1"]
    check(chains == ["2,0>2,2"], f"single enemy = single jump path; got {chains}")
    # chains: direction changes + optional stopping (every prefix is legal)
    s = state({(2, 2): (W, "M"), (2, 3): (B, "P"), (3, 4): (B, "P"),
               (4, 3): (B, "P"), (3, 2): (B, "P")})
    ms = moves(s)
    full = "2,2>2,4>4,4>4,2>2,2"
    for k in range(2, 6):
        prefix = ">".join(full.split(">")[:k])
        check(prefix in ms, f"chain prefix must be legal: {prefix}")
    check(not any(m.startswith(full + ">") for m in ms),
          "the 4-cycle cannot extend (all four men already jumped)")
    # captures are never mandatory: quiet steps still legal alongside jumps
    check("2,2>1,1" in ms, "capturing is optional (quiet move still offered)")
    # captures removed only after the move: apply the full cycle
    s2 = G.apply_move(s, full)
    check(s2.board[(2, 2)] == (W, "M") and len(
        [1 for (pl, k) in s2.board.values() if pl == B and k == "P"]) == 0,
        "all four men captured by the cycle")
    # jumping the LION terminates the chain (and the game)
    s = state({(1, 1): (W, "M"), (2, 4): (B, "L"), (2, 2): (B, "P"), (3, 4): (B, "P")},
              lions=False)
    b = dict(s.board)
    b[(3, 0)] = (W, "L")
    s = CongoState(board=b)
    ms = moves(s)
    check("1,1>3,3" in ms, "monkey jump path over the pawn exists")
    lion_jump = "1,1>3,3>1,5"   # second leg jumps the lion at (2,4)
    check(lion_jump in ms, "monkey may jump the lion")
    check(not any(m.startswith(lion_jump + ">") for m in ms),
          "no continuation past a lion jump")
    s2 = G.apply_move(s, lion_jump)
    check(s2.winner == W and G.is_terminal(s2), "jumping the lion wins")


# --------------------------------------------------------------------------- #
def test_drowning():
    # a piece that ENTERS the river survives that turn…
    s = state({(1, 2): (W, "P"), (6, 5): (B, "P")})
    s = G.apply_move(s, "1,2>1,3")
    check(s.board.get((1, 3)) == (W, "P"), "entering the river is safe")
    # …the opponent's move leaves it alone…
    s = G.apply_move(s, "6,5>6,4")
    check(s.board.get((1, 3)) == (W, "P"), "opponent's turn does not drown my piece")
    # …but if the owner then moves ANOTHER piece, it drowns at end of turn
    s2 = G.apply_move(s, "3,0>3,1")
    check((1, 3) not in s2.board, "piece left in the river drowns")
    # moving OUT of the river saves it
    s3 = G.apply_move(s, "1,3>1,4")
    check(s3.board.get((1, 4)) == (W, "P"), "leaving the river saves the piece")
    # moving WITHIN the river still drowns (superpawn sideways)
    s = state({(2, 3): (W, "S")})
    s2 = G.apply_move(s, "2,3>3,3")
    check((3, 3) not in s2.board and (2, 3) not in s2.board,
          "moving within the river still drowns")
    # the crocodile never drowns
    s = state({(2, 3): (W, "C")})
    s2 = G.apply_move(s, "3,0>3,1")     # move the lion instead
    check(s2.board.get((2, 3)) == (W, "C"), "crocodile is exempt")
    # black's river piece drowns at the end of BLACK's turn
    s = state({(4, 3): (B, "P"), (0, 1): (W, "P")})
    s = G.apply_move(s, "0,1>0,2")      # white moves: black pawn survives
    check(s.board.get((4, 3)) == (B, "P"), "not my turn, not my drowning")
    s = G.apply_move(s, "3,6>3,5")      # black moves its lion: pawn drowns
    check((4, 3) not in s.board, "black river pawn drowns after black's turn")
    # monkey: chain through the river is free; ending a SECOND consecutive
    # turn in the river drowns it, but its captures stand
    s = state({(2, 3): (W, "M"), (3, 3): (B, "P"), (5, 3): (B, "Z")})
    s2 = G.apply_move(s, "2,3>4,3")     # started in river, ends in river
    check((3, 3) not in s2.board, "the monkey's capture stands")
    check((4, 3) not in s2.board, "the drowned monkey is removed")
    check((5, 3) in s2.board, "unjumped piece survives")
    # same chain but ending OUT of the river: monkey survives
    s = state({(2, 3): (W, "M"), (3, 3): (B, "P"), (4, 4): (B, "Z")})
    s2 = G.apply_move(s, "2,3>4,3>4,5")
    check(s2.board.get((4, 5)) == (W, "M"), "monkey out of the river survives")
    check((3, 3) not in s2.board and (4, 4) not in s2.board, "both captures stand")


# --------------------------------------------------------------------------- #
def test_endings():
    # bare lions, not aligned: draw
    s = CongoState(board={(3, 2): (W, "L"), (2, 4): (B, "L")})
    check(G.is_terminal(s) and G.returns(s) == [0.0, 0.0], "bare lions = draw")
    # bare lions, aligned: NOT a draw (mover captures)
    s = CongoState(board={(3, 2): (W, "L"), (3, 4): (B, "L")})
    check(not G.is_terminal(s) and "3,2>3,4" in moves(s),
          "aligned bare lions: the mover can win")
    # lion + pawn vs bare lion is not adjudicated
    s = CongoState(board={(3, 2): (W, "L"), (2, 4): (B, "L"), (0, 1): (W, "P")})
    check(not G.is_terminal(s), "lion+pawn vs lion plays on")
    # capture the lion with an ordinary piece: zebra hits d7 from b6
    s = state({(1, 5): (W, "Z")})
    check("1,5>3,6" in moves(s), "zebra attacks the lion")
    s2 = G.apply_move(s, "1,5>3,6")
    check(s2.winner == W and G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0],
          "capturing the lion wins immediately")
    # threefold repetition from the real initial position (zebra shuffle)
    s = G.initial_state()
    for _ in range(2):
        for m in ("6,0>5,2", "6,6>5,4", "5,2>6,0", "5,4>6,6"):
            check(not G.is_terminal(s), "shuffle should not be terminal early")
            s = G.apply_move(s, m)
    check(G.is_terminal(s) and G.returns(s) == [0.0, 0.0],
          "threefold repetition is a draw")
    # a side with no legal move loses (no draw by stalemate)
    s = CongoState(board={(3, 6): (B, "L")}, to_move=W)
    check(G.is_terminal(s) and G.returns(s) == [-1.0, 1.0],
          "no legal move = loss for the mover")


# --------------------------------------------------------------------------- #
def test_playouts():
    rng = random.Random(2026)
    results = {"lion": 0, "draw": 0, "other": 0}
    lengths = []
    for _ in range(500):
        s = G.initial_state()
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        lengths.append(s.ply)
        ret = G.returns(s)
        if s.winner is not None:
            results["lion"] += 1
        elif ret == [0.0, 0.0]:
            results["draw"] += 1
        else:
            results["other"] += 1
        check(len(ret) == 2 and all(isinstance(x, float) for x in ret), "returns well-formed")
    print(f"  playouts: 500 terminated, avg {sum(lengths)/len(lengths):.1f} plies "
          f"(min {min(lengths)}, max {max(lengths)}), "
          f"lion-capture {results['lion']}, draws {results['draw']}, other {results['other']}")
    check(results["lion"] > 300, "random play should usually end in a lion capture")


def main():
    test_conformance()
    test_setup_and_perft()
    test_lion()
    test_zebra()
    test_elephant()
    test_giraffe()
    test_crocodile()
    test_pawn()
    test_superpawn()
    test_monkey()
    test_drowning()
    test_endings()
    test_playouts()
    print("SELFTEST OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
