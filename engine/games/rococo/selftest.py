"""Pure-stdlib selftest for Rococo (Aronson & Howe).

Anchors (no machine oracle exists for Rococo):
  * exact opening legal-move count, justified piece by piece (see below);
  * the official page's worked examples reproduced as positions and driven
    through apply_move:
      - the Withdrawer d2-g2 example ("captures only an enemy piece at c2"),
      - the Long Leaper edge example (leaper on x00, victim on x3: may land on
        x2 only, not x1/x0),
      - the Chameleon combined-capture example (Withdrawer a1, Chameleon a2,
        Long Leaper a3, Advancer a5: one move captures all three),
  * every capture method + the edge-square rule per piece,
  * swap-back ban, mutual destruction, suicide-of-frozen, promotion recycling,
  * stalemate = loss and third-time repetition = loss (reached via apply_move),
  * random-playout termination + move-string uniqueness + serialize round-trip.

Opening count = 25 per side:
  22 Cannon-Pawn steps (8x N + 7x NE + 7x NW; E/W/S* blocked by own pieces or
     the edge ring, and no leap has an empty interior landing) and
   3 Swapper swaps (h1 with g1 Advancer, h2 Pawn, g2 Pawn).
  Every other piece is boxed in: queen-sliders have no empty interior square
  adjacent (row 0 / files x,y are edge squares, passive moves may not enter),
  and the Long Leapers may not leap friendly pieces.

Run: cd engine && PYTHONPATH=. python3 games/rococo/selftest.py
"""

from __future__ import annotations

import json
import random

from games.rococo.game import Rococo, RState, WHITE, BLACK


def _pos(pairs, to_move=WHITE, pools=None, ban=None):
    return RState(board=dict(pairs), to_move=to_move,
                  pools=[dict((pools or [{}, {}])[0]), dict((pools or [{}, {}])[1])],
                  ban=ban)


def _apply(g, s, move):
    mv = g.legal_moves(s)
    assert move in mv, f"{move!r} not legal; from-square moves: " \
        f"{sorted(m for m in mv if m.startswith(move.split('>')[0]))}"
    return g.apply_move(s, move)


KINGS = {(1, 1): (WHITE, "K"), (8, 8): (BLACK, "K")}


def main():
    g = Rococo()

    # --- opening -----------------------------------------------------------
    s0 = g.initial_state()
    mv = g.legal_moves(s0)
    assert len(mv) == len(set(mv)), "duplicate move strings"
    assert len(mv) == 25, f"opening moves {len(mv)} != 25"
    pawn_steps = [m for m in mv if "=" not in m and m.split(">")[0].endswith(",2")]
    assert len(pawn_steps) == 22, f"pawn steps {len(pawn_steps)} != 22"
    swaps = sorted(m for m in mv if m.endswith("=swap"))
    assert swaps == ["8,1>7,1=swap", "8,1>7,2=swap", "8,1>8,2=swap"], swaps
    # setup sanity: King d1=(4,1), Chameleon e1=(5,1) (page diagram + ZRF; the
    # page's prose "King e1" is a typo)
    assert s0.board[(4, 1)] == (WHITE, "K") and s0.board[(5, 1)] == (WHITE, "C")
    assert s0.board[(4, 8)] == (BLACK, "K") and s0.board[(5, 8)] == (BLACK, "C")
    assert len(s0.board) == 32
    # black is symmetric after any white move
    s1 = g.apply_move(s0, "4,2>4,3")
    assert len(g.legal_moves(s1)) == 25

    # --- Advancer ----------------------------------------------------------
    s = _pos({**KINGS, (2, 2): (WHITE, "A"), (6, 2): (BLACK, "P")})
    s2 = _apply(g, s, "2,2>5,2")            # stop next to the pawn -> capture
    assert (6, 2) not in s2.board, "advancer approach capture failed"
    s2 = _apply(g, s, "2,2>4,2")            # stop short -> no capture
    assert (6, 2) in s2.board, "advancer captured without approaching"
    assert "2,2>6,2" not in g.legal_moves(s), "advancer moved onto a piece"
    # captures a ring piece from an interior landing
    s = _pos({**KINGS, (3, 3): (WHITE, "A"), (0, 3): (BLACK, "P")})
    s2 = _apply(g, s, "3,3>1,3")
    assert (0, 3) not in s2.board, "advancer failed to capture onto-ring victim"
    # never enters an edge square by its own move
    for m in g.legal_moves(_pos({**KINGS, (3, 3): (WHITE, "A")})):
        if m.startswith("3,3>"):
            c, r = map(int, m.split(">")[1].split(","))
            assert 1 <= c <= 8 and 1 <= r <= 8, f"advancer entered the ring: {m}"
    # once ON the ring: capturing moves along the edge OK, passive ring moves not
    s = _pos({**KINGS, (0, 2): (WHITE, "A"), (0, 6): (BLACK, "P")})
    ms = g.legal_moves(s)
    assert "0,2>0,5" in ms, "on-ring advancer capture along the edge missing"
    assert "0,2>0,3" not in ms, "on-ring advancer passive edge move allowed"
    assert "0,2>1,2" in ms, "on-ring advancer cannot step back inside"
    s2 = _apply(g, s, "0,2>0,5")
    assert (0, 6) not in s2.board

    # --- Withdrawer (official d2-g2 example) -------------------------------
    # d2=(4,2), g2=(7,2), c2=(3,2); an enemy on c3=(3,3) must survive.
    s = _pos({**KINGS, (4, 2): (WHITE, "W"), (3, 2): (BLACK, "P"),
              (3, 3): (BLACK, "P")})
    s2 = _apply(g, s, "4,2>7,2")
    assert (3, 2) not in s2.board, "withdrawer failed to capture c2"
    assert (3, 3) in s2.board, "withdrawer wrongly captured c3"
    s2 = _apply(g, s, "4,2>4,1")            # moving south: behind is (4,3) empty
    assert (3, 2) in s2.board and (3, 3) in s2.board
    # edge landing legal only when it is the only way to make the capture
    s = _pos({**KINGS, (1, 5): (WHITE, "W"), (2, 5): (BLACK, "P")})
    s2 = _apply(g, s, "1,5>0,5")            # only landing on the west ray
    assert (2, 5) not in s2.board
    s = _pos({**KINGS, (2, 5): (WHITE, "W"), (3, 5): (BLACK, "P")})
    ms = g.legal_moves(s)
    assert "2,5>1,5" in ms and "2,5>0,5" not in ms, \
        "withdrawer edge landing allowed despite interior alternative"

    # --- Long Leaper -------------------------------------------------------
    s = _pos({**KINGS, (1, 4): (WHITE, "L"), (3, 4): (BLACK, "P"),
              (5, 4): (BLACK, "P")})
    s2 = _apply(g, s, "1,4>6,4")            # chain leap captures both
    assert (3, 4) not in s2.board and (5, 4) not in s2.board
    s2 = _apply(g, s, "1,4>4,4")            # single leap captures the first only
    assert (3, 4) not in s2.board and (5, 4) in s2.board
    s = _pos({**KINGS, (1, 4): (WHITE, "L"), (3, 4): (BLACK, "P"),
              (4, 4): (BLACK, "P")})
    assert "1,4>5,4" not in g.legal_moves(s), "leaped two adjacent enemies"
    s = _pos({**KINGS, (1, 4): (WHITE, "L"), (3, 4): (WHITE, "P")})
    assert not any(m in g.legal_moves(s)
                   for m in ("1,4>4,4", "1,4>5,4", "1,4>6,4", "1,4>7,4", "1,4>8,4")), \
        "leaped a friendly piece"
    # official edge example: Leaper on x00=(0,9), victim on x3=(0,3), x8-x4
    # empty: may land on x2=(0,2) ONLY (not x1/x0)
    s = _pos({**KINGS, (0, 9): (WHITE, "L"), (0, 3): (BLACK, "P")})
    ms = g.legal_moves(s)
    assert "0,9>0,2" in ms, "corner leaper capture missing"
    assert "0,9>0,1" not in ms and "0,9>0,0" not in ms, \
        "leaper crossed more edge squares than necessary"
    assert "0,9>0,8" not in ms, "leaper passive move along the ring allowed"
    assert "0,9>1,8" in ms, "leaper cannot leave the ring passively"
    # interior landing forbids the edge landing for the same capture
    s = _pos({**KINGS, (1, 5): (WHITE, "L"), (5, 5): (BLACK, "P")})
    ms = g.legal_moves(s)
    assert "1,5>6,5" in ms and "1,5>9,5" not in ms
    # ...but the edge landing is legal when it is the only one
    s = _pos({**KINGS, (1, 5): (WHITE, "L"), (8, 5): (BLACK, "P")})
    assert "1,5>9,5" in g.legal_moves(s), "only-way edge landing missing"

    # --- Swapper -----------------------------------------------------------
    s = _pos({**KINGS, (4, 4): (WHITE, "S"), (4, 5): (BLACK, "P"),
              (6, 4): (WHITE, "I"), (0, 4): (BLACK, "P")})
    ms = g.legal_moves(s)
    assert "4,4>4,5=swap" in ms and "4,4>4,5=boom" in ms   # distinct actions
    assert "4,4>6,4=swap" in ms, "swap with a friendly piece missing"
    assert "4,4>0,4=swap" in ms, "swap with a piece on an edge square missing"
    assert "4,4>3,4" in ms and "4,4>2,4" in ms
    assert not any(m in ms for m in ("4,4>0,4", "4,4>4,9")), \
        "swapper passive move onto the ring"
    s2 = _apply(g, s, "4,4>0,4=swap")       # swapper itself lands on the ring
    assert s2.board[(0, 4)] == (WHITE, "S") and s2.board[(4, 4)] == (BLACK, "P")
    s2 = _apply(g, s, "4,4>4,5=boom")       # mutual destruction
    assert (4, 4) not in s2.board and (4, 5) not in s2.board
    assert s2.pools[WHITE].get("S") == 1, "destroyed swapper missing from pool"
    # mutual destruction of the King wins
    s = _pos({**KINGS, (7, 8): (WHITE, "S")})
    s2 = _apply(g, s, "7,8>8,8=boom")
    assert s2.winner == WHITE and g.returns(s2) == [1.0, -1.0]

    # swap-back ban: after S x S, the reverse swap is illegal for one turn
    s = _pos({**KINGS, (4, 4): (WHITE, "S"), (4, 6): (BLACK, "S"),
              (2, 7): (BLACK, "P")})
    s2 = _apply(g, s, "4,4>4,6=swap")
    assert s2.board[(4, 6)] == (WHITE, "S") and s2.board[(4, 4)] == (BLACK, "S")
    bm = g.legal_moves(s2)
    assert "4,4>4,6=swap" not in bm, "swap-back not banned"
    assert any(m.startswith("4,4>") for m in bm), "banned swapper fully frozen"
    s3 = _apply(g, s2, "2,7>2,6")           # black makes any other move
    assert "4,6>4,4=swap" in g.legal_moves(s3), "swap-back ban did not expire"
    # a frozen Swapper: no swap, no mutual destruction, only suicide
    s = _pos({**KINGS, (4, 4): (WHITE, "I"), (4, 5): (BLACK, "S")},
             to_move=BLACK)
    from_s = [m for m in g.legal_moves(s) if m.startswith("4,5>")]
    assert from_s == ["4,5>4,5"], f"frozen swapper moves: {from_s}"
    s2 = _apply(g, s, "4,5>4,5")
    assert (4, 5) not in s2.board and s2.pools[BLACK].get("S") == 1

    # --- Immobilizer -------------------------------------------------------
    s = _pos({**KINGS, (3, 3): (WHITE, "I"), (3, 4): (BLACK, "P")},
             to_move=BLACK)
    from_p = [m for m in g.legal_moves(s) if m.startswith("3,4>")]
    assert from_p == ["3,4>3,4"], "frozen pawn should only have suicide"
    # an unfrozen piece has no suicide move
    assert not any(m.split(">")[0] == m.split(">")[1].split("=")[0]
                   for m in g.legal_moves(s0)), "suicide offered while unfrozen"
    # a frozen King has no moves at all (cannot suicide)
    s = _pos({**KINGS, (7, 7): (WHITE, "I"), (2, 5): (BLACK, "P")},
             to_move=BLACK)
    assert not any(m.startswith("8,8>") for m in g.legal_moves(s)), \
        "frozen king still has moves"
    # the immobilizer never enters an edge square
    for m in g.legal_moves(_pos({**KINGS, (3, 3): (WHITE, "I")})):
        if m.startswith("3,3>"):
            c, r = map(int, m.split(">")[1].split(","))
            assert 1 <= c <= 8 and 1 <= r <= 8, f"immobilizer on the ring: {m}"
    # two adjacent enemy immobilizers freeze each other (suicide only)
    s = _pos({**KINGS, (3, 3): (WHITE, "I"), (3, 4): (BLACK, "I")})
    assert [m for m in g.legal_moves(s) if m.startswith("3,3>")] == ["3,3>3,3"]
    # chameleon vs immobilizer: mutual freeze, no capture
    s = _pos({**KINGS, (3, 3): (WHITE, "C"), (3, 4): (BLACK, "I")})
    assert [m for m in g.legal_moves(s) if m.startswith("3,3>")] == ["3,3>3,3"]
    sB = _pos({**KINGS, (3, 3): (WHITE, "C"), (3, 4): (BLACK, "I")},
              to_move=BLACK)
    assert [m for m in g.legal_moves(sB) if m.startswith("3,4>")] == ["3,4>3,4"]

    # --- Chameleon ---------------------------------------------------------
    # leaps (and captures) enemy Long Leapers only
    s = _pos({**KINGS, (1, 4): (WHITE, "C"), (3, 4): (BLACK, "L")})
    s2 = _apply(g, s, "1,4>4,4")
    assert (3, 4) not in s2.board, "chameleon-as-leaper failed"
    s = _pos({**KINGS, (1, 4): (WHITE, "C"), (3, 4): (BLACK, "P")})
    assert "1,4>4,4" not in g.legal_moves(s), "chameleon leaped a non-leaper"
    # withdraws from Withdrawers only
    s = _pos({**KINGS, (3, 3): (WHITE, "C"), (2, 3): (BLACK, "W")})
    s2 = _apply(g, s, "3,3>5,3")
    assert (2, 3) not in s2.board, "chameleon-as-withdrawer failed"
    s = _pos({**KINGS, (3, 3): (WHITE, "C"), (2, 3): (BLACK, "P")})
    s2 = _apply(g, s, "3,3>5,3")
    assert (2, 3) in s2.board, "chameleon withdrew-captured a non-withdrawer"
    # approaches Advancers only (an approached Immobilizer survives)
    s = _pos({**KINGS, (2, 2): (WHITE, "C"), (6, 2): (BLACK, "A")})
    s2 = _apply(g, s, "2,2>5,2")
    assert (6, 2) not in s2.board, "chameleon-as-advancer failed"
    s = _pos({**KINGS, (2, 2): (WHITE, "C"), (6, 2): (BLACK, "I")})
    s2 = _apply(g, s, "2,2>5,2")
    assert (6, 2) in s2.board, "chameleon captured an immobilizer"
    # cannon-captures enemy Pawns (landing on the Pawn beyond a mount)
    s = _pos({**KINGS, (3, 3): (WHITE, "C"), (4, 3): (WHITE, "P"),
              (5, 3): (BLACK, "P")})
    s2 = _apply(g, s, "3,3>5,3")
    assert s2.board[(5, 3)] == (WHITE, "C") and (4, 3) in s2.board
    s = _pos({**KINGS, (3, 3): (WHITE, "C"), (4, 3): (WHITE, "P"),
              (5, 3): (BLACK, "A")})
    assert "3,3>5,3" not in g.legal_moves(s), "chameleon cannon-captured a non-pawn"
    # captures an adjacent enemy King king-wise -> win
    s = _pos({(1, 1): (WHITE, "K"), (3, 3): (WHITE, "C"), (3, 4): (BLACK, "K")})
    s2 = _apply(g, s, "3,3>3,4")
    assert s2.winner == WHITE, "chameleon king capture did not win"
    # the official combined example: white Withdrawer a1, black Chameleon a2,
    # white Long Leaper a3, white Advancer a5 -- the chameleon leaps to a4 and
    # captures all three in one move.  a1=(1,1) ... a5=(1,5).
    s = _pos({(8, 1): (WHITE, "K"), (8, 8): (BLACK, "K"),
              (1, 1): (WHITE, "W"), (1, 2): (BLACK, "C"),
              (1, 3): (WHITE, "L"), (1, 5): (WHITE, "A")}, to_move=BLACK)
    s2 = _apply(g, s, "1,2>1,4")
    assert (1, 1) not in s2.board, "combined: withdrawer not captured"
    assert (1, 3) not in s2.board, "combined: long leaper not captured"
    assert (1, 5) not in s2.board, "combined: advancer not captured"
    assert s2.board[(1, 4)] == (BLACK, "C")
    # swap with an enemy Swapper combined with leaping a Long Leaper
    s = _pos({**KINGS, (1, 4): (WHITE, "C"), (3, 4): (BLACK, "L"),
              (5, 4): (BLACK, "S")})
    s2 = _apply(g, s, "1,4>5,4=swap")
    assert s2.board[(5, 4)] == (WHITE, "C") and s2.board[(1, 4)] == (BLACK, "S")
    assert (3, 4) not in s2.board, "combined swap: leaper not captured"
    # mutual destruction only against an adjacent enemy Swapper
    s = _pos({**KINGS, (4, 4): (WHITE, "C"), (4, 5): (BLACK, "S"),
              (5, 4): (BLACK, "P")})
    ms = g.legal_moves(s)
    assert "4,4>4,5=boom" in ms and "4,4>5,4=boom" not in ms

    # --- Cannon Pawn -------------------------------------------------------
    s = _pos({**KINGS, (4, 4): (WHITE, "P"), (4, 5): (WHITE, "I"),
              (5, 4): (BLACK, "P")})
    ms = g.legal_moves(s)
    assert "4,4>4,6" in ms, "pawn leap over a friendly mount missing"
    assert "4,4>6,4" in ms, "pawn leap over an enemy mount missing"
    assert "4,4>3,4" in ms and "4,4>3,3" in ms
    s2 = _apply(g, s, "4,4>6,4")            # passive leap: the mount survives
    assert (5, 4) in s2.board and s2.board[(6, 4)] == (WHITE, "P")
    # capture leap: land ON the enemy just beyond the mount
    s = _pos({**KINGS, (4, 4): (WHITE, "P"), (5, 4): (BLACK, "P"),
              (6, 4): (BLACK, "A")})
    s2 = _apply(g, s, "4,4>6,4")
    assert s2.board[(6, 4)] == (WHITE, "P") and (5, 4) in s2.board
    assert s2.pools[BLACK].get("A") == 1, "captured advancer not pooled"
    # no passive move onto the ring; ring capture OK
    s = _pos({**KINGS, (4, 7): (WHITE, "P"), (4, 8): (WHITE, "I")})
    assert "4,7>4,9" not in g.legal_moves(s), "pawn passive leap onto the ring"
    s = _pos({**KINGS, (4, 7): (WHITE, "P"), (4, 8): (WHITE, "I"),
              (4, 9): (BLACK, "L")})
    assert "4,7>4,9" in g.legal_moves(s), "pawn ring capture missing"
    # promotion: optional, only to pooled pieces, on ranks 8/9 (White)
    s = _pos({**KINGS, (4, 7): (WHITE, "P")}, pools=[{"S": 1}, {}])
    ms = g.legal_moves(s)
    assert "4,7>4,8" in ms and "4,7>4,8=S" in ms, "promotion choice missing"
    assert "4,7>4,8=A" not in ms, "promotion to an uncaptured piece"
    assert "4,7>4,6=S" not in ms, "promotion outside the zone"
    s2 = _apply(g, s, "4,7>4,8=S")
    assert s2.board[(4, 8)] == (WHITE, "S") and not s2.pools[WHITE], \
        "promotion did not consume the pool"
    s2 = _apply(g, s, "4,7>4,8")
    assert s2.board[(4, 8)] == (WHITE, "P"), "declined promotion changed piece"
    # black promotes on ranks 1/0
    s = _pos({**KINGS, (4, 2): (BLACK, "P")}, to_move=BLACK,
             pools=[{}, {"L": 1}])
    assert "4,2>4,1=L" in g.legal_moves(s), "black promotion missing"
    # no promotion with an empty pool
    s = _pos({**KINGS, (4, 7): (WHITE, "P")})
    assert not any("=" in m for m in g.legal_moves(s) if m.startswith("4,7>"))

    # --- stalemate = loss --------------------------------------------------
    # Black has only a King; White freezes it -> Black cannot move -> White wins.
    s = _pos({(1, 1): (WHITE, "K"), (6, 6): (WHITE, "I"), (8, 8): (BLACK, "K")})
    assert any(m.startswith("8,8>")
               for m in g.legal_moves(_pos(dict(s.board), to_move=BLACK)))
    s2 = _apply(g, s, "6,6>7,7")
    assert s2.winner == WHITE and "no legal moves" in s2.reason, \
        f"stalemate loss not detected: {s2.winner} {s2.reason!r}"

    # --- third-time repetition = loss for the repeater ---------------------
    s = _pos({(2, 2): (WHITE, "K"), (6, 6): (BLACK, "K")})
    cycle = ["2,2>2,3", "6,6>6,5", "2,3>2,2", "6,5>6,6"]
    for ply in range(12):
        assert not g.is_terminal(s), f"terminated early at ply {ply}"
        s = _apply(g, s, cycle[ply % 4])
        if g.is_terminal(s):
            assert ply + 1 == 9, f"repetition fired at ply {ply + 1}, expected 9"
            break
    assert s.winner == BLACK and "repetition" in s.reason, \
        f"repetition loss wrong: {s.winner} {s.reason!r}"

    # --- serialize round-trip (with ban, pools, history) --------------------
    s = g.initial_state()
    for m in ("8,1>8,2=swap", "8,8>8,7=swap", "4,2>4,3"):
        s = _apply(g, s, m)
    d = g.serialize(s)
    json.dumps(d)
    s_rt = g.deserialize(d)
    assert g.serialize(s_rt) == d, "serialize round-trip mismatch"
    assert sorted(g.legal_moves(s_rt)) == sorted(g.legal_moves(s))

    # --- random playouts: termination + invariants -------------------------
    for seed in range(3):
        rng = random.Random(seed)
        s = g.initial_state()
        plies = 0
        while not g.is_terminal(s):
            mv = g.legal_moves(s)
            assert mv and len(mv) == len(set(mv))
            s = g.apply_move(s, rng.choice(mv))
            plies += 1
            assert plies <= 700, "runaway game"
        assert g.returns(s) in ([1.0, -1.0], [-1.0, 1.0], [0.0, 0.0])

    print("rococo selftest: all tests passed")


if __name__ == "__main__":
    main()
