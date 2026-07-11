"""Dai Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Anchors:
  * the exact 15x15 / 65-piece / 29-type starting setup (verified against the
    Wikipedia setup diagram, CVP's interactive-diagram config and HaChu's
    daiArray; White = 180-degree rotation of Black);
  * opening perft 71 / 5041 / 357978 at depths 1-3. The 71 root moves were
    verified piece-by-piece by hand AND against HaChu 0.21's root move list
    in `variant dai` mode (one-time differential; HaChu is H.G. Muller's
    reference engine for the historical large shogi). 5041 = 71^2 (the
    armies cannot interact at ply 2); depth 3 is self-computed and frozen;
  * the exact move sets of the 8 Dai-only piece types (Iron/Stone General,
    Knight, Angry Boar, Cat Sword, Evil Wolf, Violent Ox, Flying Dragon) at
    centre and edge, for both colours; Violent Ox / Flying Dragon are
    2-range sliders (blockable, NO jumping); the Knight jumps;
  * Lion mechanics at 15x15: 5x5 direct leaps, adjacent-step encoding f>m>m,
    double capture f>m>t, igui f>m>f, jitto turn pass -- and the ABSENCE of
    Chu's Lion-trading rules (Wikipedia: "The capture rules in chu shogi do
    not apply in dai shogi"): a protected distance-2 LnxLn is legal, and
    there is no counterstrike restriction after a non-Lion captures a Lion;
  * Horned Falcon / Soaring Eagle Lion powers on their forward ray(s);
  * promotion: zone = far FIVE ranks (rows 10-14 for Black); optional on
    entry; inside the zone only on a capture (either end in the zone); a
    capture wholly outside gives no option; re-entry resets; NO last-rank
    second chance for the Pawn (a Chu-only refinement -- a pawn stepping to
    the last rank unpromoted is a dead piece); no re-promotion; promoted
    Go-Between moves as a Drunk Elephant but is NOT royal & cannot promote;
  * win by capturing ALL royals via apply_move: King captured with a Prince
    still alive -> game continues; capturing the last royal -> winner;
  * fourfold repetition -> an honest draw; serialize round-trips; a random
    game terminates.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.dai_shogi.game import DaiShogi, DaiState                 # noqa: E402
from agp.shogilike import BLACK, WHITE                              # noqa: E402

G = DaiShogi()


def st(board, to_move=BLACK, promoted=(), ply=0):
    s = DaiState(board=dict(board), promoted=frozenset(promoted),
                 hands={BLACK: {}, WHITE: {}}, to_move=to_move, ply=ply)
    s.key = G._poskey(s)
    s.reps = {s.key: 1}
    return s


def perft(state, d):
    if d == 0:
        return 1
    ms = G.legal_moves(state)
    if d == 1:
        return len(ms)
    return sum(perft(G.apply_move(state, m), d - 1) for m in ms)


def moves_from(s, frm):
    return sorted(m for m in G.legal_moves(s) if m.startswith(frm + ">"))


def targets(s, frm):
    """Destination cells of simple from>to moves (no =+, no lion legs)."""
    out = set()
    for m in G.legal_moves(s):
        if m.endswith("=+") or m.count(">") != 1:
            continue
        f, t = m.split(">")
        if f == frm:
            out.add(t)
    return out


Kk = {(0, 0): (BLACK, "K"), (14, 14): (WHITE, "K")}


def main():
    s0 = G.initial_state()

    # ---- 1) setup ---------------------------------------------------------
    assert G.WIDTH == G.HEIGHT == 15 and G.ZONE == 5
    assert len(s0.board) == 130
    for pl in (BLACK, WHITE):
        assert sum(1 for v in s0.board.values() if v[0] == pl) == 65
    counts = {}
    for (pl, t) in s0.board.values():
        counts[(pl, t)] = counts.get((pl, t), 0) + 1
    per_type = {"K": 1, "Q": 1, "N": 1, "O": 1, "X": 1, "E": 1,
                "G": 2, "S": 2, "C": 2, "T": 2, "F": 2, "L": 2, "A": 2,
                "B": 2, "R": 2, "H": 2, "D": 2, "V": 2, "M": 2, "I": 2,
                "Ir": 2, "St": 2, "Kt": 2, "AB": 2, "CS": 2, "EW": 2,
                "VO": 2, "FD": 2, "P": 15}
    assert sum(per_type.values()) == 65 and len(per_type) == 29
    for pl in (BLACK, WHITE):
        for t, n in per_type.items():
            assert counts[(pl, t)] == n, (pl, t, counts.get((pl, t)))
    # spot squares (Wikipedia diagram; col 0 = HaChu file 'a', Black bottom)
    assert s0.board[(7, 0)] == (BLACK, "K") and s0.board[(7, 1)] == (BLACK, "E")
    assert s0.board[(7, 2)] == (BLACK, "N") and s0.board[(7, 3)] == (BLACK, "Q")
    assert s0.board[(6, 2)] == (BLACK, "O") and s0.board[(8, 2)] == (BLACK, "X")
    assert s0.board[(1, 2)] == (BLACK, "VO") and s0.board[(1, 3)] == (BLACK, "FD")
    assert s0.board[(3, 2)] == (BLACK, "AB") and s0.board[(5, 2)] == (BLACK, "EW")
    assert s0.board[(2, 1)] == (BLACK, "CS") and s0.board[(2, 0)] == (BLACK, "St")
    assert s0.board[(3, 0)] == (BLACK, "Ir") and s0.board[(1, 0)] == (BLACK, "Kt")
    assert s0.board[(4, 5)] == (BLACK, "I") and s0.board[(10, 5)] == (BLACK, "I")
    assert s0.board[(7, 14)] == (WHITE, "K") and s0.board[(7, 13)] == (WHITE, "E")
    assert s0.board[(7, 12)] == (WHITE, "N") and s0.board[(8, 12)] == (WHITE, "O")
    assert s0.board[(6, 12)] == (WHITE, "X") and s0.board[(10, 9)] == (WHITE, "I")
    assert sum(1 for (c, r), (p, t) in s0.board.items()
               if p == BLACK and t == "P" and r == 4) == 15

    # ---- 2) opening perft (d1 anchored on HaChu 0.21 `variant dai`) --------
    ms0 = G.legal_moves(s0)
    assert len(ms0) == len(set(ms0)), "duplicate move strings"
    assert perft(s0, 1) == 71, perft(s0, 1)
    assert perft(s0, 2) == 5041
    assert perft(s0, 3) == 357978
    # pawns in front of the Go-Betweens are blocked by them
    assert "4,4>4,5" not in ms0 and "10,4>10,5" not in ms0
    # the Lion is boxed in by friends: exactly its two distance-2 leaps
    assert moves_from(s0, "7,2") == ["7,2>5,1", "7,2>9,1"]

    # ---- 3) the 8 Dai-only pieces ------------------------------------------
    def solo(letter, sq=(7, 7), to_move=BLACK, extra=()):
        b = dict(Kk)
        b[sq] = (to_move, letter)
        b.update(extra)
        return st(b, to_move=to_move)

    # Iron General: forward + both diagonally forward
    assert targets(solo("Ir"), "7,7") == {"7,8", "6,8", "8,8"}
    # Stone General: diagonally forward only
    assert targets(solo("St"), "7,7") == {"6,8", "8,8"}
    # ...and for White the forward frame flips
    assert targets(solo("St", to_move=WHITE), "7,7") == {"6,6", "8,6"}
    # Knight: shogi knight, jumps over anything
    assert targets(solo("Kt"), "7,7") == {"6,9", "8,9"}
    wall = {(c, 8): (WHITE, "P") for c in (6, 7, 8)}
    assert targets(solo("Kt", extra=wall), "7,7") == {"6,9", "8,9"}
    assert targets(solo("Kt", sq=(0, 7)), "0,7") == {"1,9"}          # edge
    # Angry Boar: one step orthogonally (all four ways)
    assert targets(solo("AB"), "7,7") == {"7,8", "7,6", "6,7", "8,7"}
    # Cat Sword: one step diagonally (all four ways)
    assert targets(solo("CS"), "7,7") == {"6,8", "8,8", "6,6", "8,6"}
    # Evil Wolf: forward, both forward diagonals, both sideways
    assert targets(solo("EW"), "7,7") == {"7,8", "6,8", "8,8", "6,7", "8,7"}
    # Violent Ox: 1-2 orthogonally, blockable (NOT a jump)
    assert targets(solo("VO"), "7,7") == {"7,8", "7,9", "7,6", "7,5",
                                          "6,7", "5,7", "8,7", "9,7"}
    blocked = solo("VO", extra={(7, 8): (BLACK, "P")})
    assert "7,7>7,8" not in [m for m in G.legal_moves(blocked)] \
        and "7,7>7,9" not in [m for m in G.legal_moves(blocked)]
    enemy = solo("VO", extra={(7, 8): (WHITE, "P")})
    tg = targets(enemy, "7,7")
    assert "7,8" in tg and "7,9" not in tg          # capture, no jump past
    # Flying Dragon: 1-2 diagonally, blockable
    assert targets(solo("FD"), "7,7") == {"6,8", "5,9", "8,8", "9,9",
                                          "6,6", "5,5", "8,6", "9,5"}
    enemy = solo("FD", extra={(8, 8): (WHITE, "P")})
    tg = targets(enemy, "7,7")
    assert "8,8" in tg and "9,9" not in tg
    # all eight promote to Gold: promoted move set = gold's, no re-promotion
    for L in ("Ir", "St", "Kt", "AB", "CS", "EW", "VO", "FD"):
        s = st({(7, 7): (BLACK, L), **Kk}, promoted={(7, 7)})
        assert targets(s, "7,7") == {"7,8", "6,8", "8,8", "6,7", "8,7", "7,6"}, L
        assert not any(m.endswith("=+") for m in moves_from(s, "7,7")), L
        assert G._label(L, True) == "+G"

    # ---- 4) Lion mechanics at 15x15 -----------------------------------------
    s = st({(7, 7): (BLACK, "N"), **Kk})
    lion = set(moves_from(s, "7,7"))
    assert len([m for m in lion if m.count(">") == 1]) == 16          # dist-2 leaps
    assert len([m for m in lion if m.count(">") == 2 and
                m.split(">")[1] == m.split(">")[2]]) == 8             # steps f>m>m
    assert len([m for m in lion if m.split(">")[0] == m.split(">")[-1] !=
                m.split(">")[1]]) == 8                                # passes f>m>f
    s = st({(7, 7): (BLACK, "N"), (7, 8): (WHITE, "P"), (8, 9): (WHITE, "S"),
            **Kk})
    ms = set(G.legal_moves(s))
    assert "7,7>7,8>8,9" in ms                        # double capture P then S
    assert "7,7>7,8>7,7" in ms                        # igui: capture P in place
    assert "7,7>6,6>7,7" in ms                        # jitto via an empty square
    n2 = G.apply_move(s, "7,7>7,8>8,9")
    assert n2.board[(8, 9)] == (BLACK, "N") and (7, 8) not in n2.board
    n3 = G.apply_move(s, "7,7>7,8>7,7")
    assert n3.board[(7, 7)] == (BLACK, "N") and (7, 8) not in n3.board
    n4 = G.apply_move(s, "7,7>6,6>7,7")               # pass: board unchanged
    assert n4.board == s.board and n4.to_move == WHITE

    # ---- 5) NO Lion-trading rules in Dai ------------------------------------
    # A PROTECTED distance-2 enemy Lion may be captured freely (in Chu this
    # is Wikipedia's example II and is banned; Dai: "the capture rules in
    # chu shogi do not apply").
    s = st({(4, 4): (BLACK, "N"), (4, 6): (WHITE, "N"), (4, 8): (WHITE, "L"),
            **Kk})
    assert "4,4>4,6" in G.legal_moves(s)
    # no counterstrike rule: after a non-Lion takes a Lion, the immediate
    # non-Lion x Lion reply on ANOTHER square is legal
    base = {(0, 0): (BLACK, "R"), (0, 5): (WHITE, "N"), (5, 5): (BLACK, "N"),
            (5, 14): (WHITE, "R"), (14, 0): (BLACK, "K"),
            (14, 14): (WHITE, "K")}
    n = G.apply_move(st(base), "0,0>0,5")             # non-Lion takes a Lion
    assert "5,14>5,5" in G.legal_moves(n)             # RxLn elsewhere: LEGAL

    # ---- 6) Falcon / Eagle Lion powers ---------------------------------------
    s = st({(5, 5): (BLACK, "H"), (5, 6): (WHITE, "P"), (5, 7): (WHITE, "S"),
            **Kk}, promoted={(5, 5)})
    ms = set(G.legal_moves(s))
    assert "5,5>5,6>5,6" in ms                         # forward capture-step
    assert "5,5>5,6>5,5" in ms                         # igui
    assert "5,5>5,7" in ms                             # jump over the pawn
    assert "5,5>5,6>5,7" in ms                         # double capture P then S
    assert "5,5>5,6" not in ms                         # no plain forward slide
    assert not any(m.startswith("5,5>4,6>") or m.startswith("5,5>6,6>")
                   for m in ms)                        # power is forward-only
    s2 = st({(5, 5): (BLACK, "H"), **Kk}, promoted={(5, 5)})
    assert "5,5>5,6>5,5" in G.legal_moves(s2)          # pass via empty front
    s = st({(5, 5): (BLACK, "D"), (4, 6): (WHITE, "P"), **Kk},
           promoted={(5, 5)})
    ms = set(G.legal_moves(s))
    assert "5,5>4,6>3,7" in ms and "5,5>4,6>5,5" in ms and "5,5>3,7" in ms
    assert "5,5>6,6>6,6" in ms and "5,5>6,6>5,5" in ms and "5,5>7,7" in ms
    assert "5,5>4,6" not in ms                         # fwd-diag is power-only
    assert "5,5>5,6" in ms                             # straight fwd = slide

    # ---- 7) promotion (zone = far FIVE ranks: rows 10-14 for Black) ----------
    s = st({(3, 9): (BLACK, "S"), **Kk})
    ms = set(G.legal_moves(s))
    assert "3,9>3,10" in ms and "3,9>3,10=+" in ms     # entering the zone
    assert "3,9>2,8" in ms and "3,9>2,8=+" not in ms   # not entering
    s = st({(3, 8): (BLACK, "S"), **Kk})
    assert "3,8>3,9=+" not in set(G.legal_moves(s))    # row 9 is NOT in zone
    s = st({(3, 10): (BLACK, "S"), **Kk})
    ms = set(G.legal_moves(s))
    assert "3,10>3,11" in ms and "3,10>3,11=+" not in ms  # quiet inside: no
    assert "3,10>2,9" in ms and "3,10>2,9=+" not in ms    # quiet exit: no
    s = st({(3, 10): (BLACK, "S"), (2, 11): (WHITE, "P"), **Kk})
    assert "3,10>2,11=+" in set(G.legal_moves(s))      # capture inside zone
    s = st({(3, 10): (BLACK, "S"), (2, 9): (WHITE, "P"), **Kk})
    assert "3,10>2,9=+" in set(G.legal_moves(s))       # capture LEAVING zone
    s = st({(3, 8): (BLACK, "S"), (2, 9): (WHITE, "P"), **Kk})
    assert "3,8>2,9=+" not in set(G.legal_moves(s))    # capture outside: no
    # pawn: promotes on entry, but NO extra last-rank chance (Dai rule --
    # a pawn stepping to the last rank unpromoted is a dead piece)
    s = st({(5, 9): (BLACK, "P"), **Kk})
    ms = set(G.legal_moves(s))
    assert "5,9>5,10" in ms and "5,9>5,10=+" in ms
    s = st({(5, 13): (BLACK, "P"), **Kk})
    ms = set(G.legal_moves(s))
    assert "5,13>5,14" in ms and "5,13>5,14=+" not in ms
    dead = G.apply_move(s, "5,13>5,14")
    dead2 = st(dead.board, to_move=BLACK, promoted=dead.promoted)
    assert moves_from(dead2, "5,14") == []             # dead pawn
    # White zone is rows 0-4
    s = st({(3, 5): (WHITE, "S"), **Kk}, to_move=WHITE)
    ms = set(G.legal_moves(s))
    assert "3,5>3,4" in ms and "3,5>3,4=+" in ms
    # promoted pieces never promote again (+G moves as a Rook, labelled GR)
    s = st({(5, 11): (BLACK, "G"), (5, 12): (WHITE, "P"), **Kk},
           promoted={(5, 11)})
    ms = moves_from(s, "5,11")
    assert "5,11>5,12" in ms and "5,11>5,12=+" not in ms
    assert "5,11>5,0" in ms                            # rook slide all the way
    assert G._label("G", True) == "GR"
    # promoted Go-Between moves as a Drunk Elephant but is NOT royal
    s = st({(4, 9): (BLACK, "I"), **Kk})
    assert "4,9>4,10=+" in set(G.legal_moves(s))
    n = G.apply_move(s, "4,9>4,10=+")
    assert targets(st(n.board, promoted=n.promoted), "4,10") == \
        {"4,11", "3,11", "5,11", "3,10", "5,10", "3,9", "5,9"}
    assert not G._royal("I", True)
    # K / Q / N never promote
    s = st({(5, 10): (BLACK, "Q"), (6, 10): (BLACK, "N"), (7, 10): (BLACK, "K"),
            **Kk})
    assert not any(m.endswith("=+") for m in G.legal_moves(s))

    # ---- 8) win by capturing all royals ---------------------------------------
    b = {(5, 0): (BLACK, "K"), (6, 5): (BLACK, "Q"),
         (6, 14): (WHITE, "K"), (5, 13): (WHITE, "E"), (0, 8): (WHITE, "P")}
    s = st(b, promoted={(5, 13)})                      # promoted DE = Prince
    n = G.apply_move(s, "6,5>6,14")                    # Queen takes the King...
    assert n.winner is None and not G.is_terminal(n)   # ...Prince still reigns
    n = G.apply_move(n, "0,8>0,7")
    n = G.apply_move(n, "6,14>5,13")                   # Queen takes the Prince
    assert n.winner == BLACK and G.is_terminal(n)
    assert G.returns(n) == [1.0, -1.0]
    # unpromoted Drunk Elephant is NOT royal
    s = st({(5, 0): (BLACK, "K"), (6, 5): (BLACK, "Q"),
            (6, 14): (WHITE, "K"), (5, 13): (WHITE, "E"), (0, 8): (WHITE, "P")})
    n = G.apply_move(s, "6,5>6,14")
    assert n.winner == BLACK and G.is_terminal(n)

    # ---- 9) fourfold repetition draw ------------------------------------------
    s = st({(0, 0): (BLACK, "G"), (14, 14): (WHITE, "G"),
            (5, 0): (BLACK, "K"), (6, 14): (WHITE, "K")})
    seq = ["0,0>1,0", "14,14>13,14", "1,0>0,0", "13,14>14,14"]
    n = s
    for _ in range(3):
        for m in seq:
            assert not G.is_terminal(n)
            n = G.apply_move(n, m)
    assert G.is_terminal(n) and G.returns(n) == [0.0, 0.0]

    # ---- 10) serialize round-trip + random games terminate ---------------------
    import json
    n = G.apply_move(s0, "7,2>5,1")                    # Lion out
    snap = G.serialize(n)
    assert json.dumps(G.serialize(G.deserialize(snap)), sort_keys=True) == \
        json.dumps(snap, sort_keys=True)
    for seed in (7, 42):
        rng = random.Random(seed)
        sx = G.initial_state()
        for i in range(G.PLY_CAP + 1):
            if G.is_terminal(sx):
                break
            sx = G.apply_move(sx, rng.choice(G.legal_moves(sx)))
        assert G.is_terminal(sx)
        ret = G.returns(sx)
        assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

    print("dai_shogi selftest: all checks passed")


if __name__ == "__main__":
    main()
