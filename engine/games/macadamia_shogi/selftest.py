"""Macadamia Shogi correctness anchor (pure stdlib -- imports only agp + this
game).

HaChu 0.21 (``variant macadamia-shogi``) was used as a differential oracle in
the dev process (NOT called here -- selftests must be pure-stdlib):
  * the exact 13x13 / 48-piece / 26-type starting setup was verified piece-for
    -piece against HaChu's board dump;
  * board orientation (Sente bottom, +row forward) and ALL 48 non-pass initial
    legal moves were confirmed accepted by HaChu (10 hand-picked illegal moves
    rejected), covering pawn / snake(vW) / copper(vWfF) / silver / gold /
    priest / pirate / kirin(FD) / lion(step) / wolf(3-jump) movement;
  * across 14+ plies of real play HaChu never rejected a move this engine
    generated (zero false positives) and its plain replies were all legal here.
HaChu's setboard and search both SEGFAULT on this variant and its Lion/Wolf
moves use an opaque ``@@@@`` notation, so the deeper mechanics below (long
rides, bent movers, Lion/Wolf multi-capture, promotion-by-capture, dual
royalty) are anchored against the complete authoritative Betza + prose rules at
https://www.chessvariants.com/rules/macadamia-shogi and frozen here.

Anchors:
  * exact setup + mirror symmetry;
  * opening perft 51 / 2601 at depths 1-2 (self-computed, frozen);
  * every unpromoted & promoted piece's move geometry from a central square
    (frozen destination sets matching each piece's Betza definition);
  * Lion double-move (5x5 leaps + step + igui/pass + double-capture) and Wolf
    (Lion Dog) triple-move with up-to-3 annihilation + jitto pass;
  * Capricorner / Hook Mover single-bend rides;
  * Emperor universal leap; Prince (promoted Elephant) royalty;
  * PROMOTION BY CAPTURE: optional on capture, forced when the captured piece
    was promoted, none without a capture, the Saint/Ghost capture-override
    (incl. Queen -> Saint), royal exclusion (King -> Emperor not Saint), and
    Elephant -> King;
  * win by capturing ALL royals via apply_move (dual royalty: taking one King
    while a Prince survives does not end the game);
  * fourfold-repetition / ply-cap draw; a random game terminates;
  * serialize/deserialize round-trip.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.macadamia_shogi.game import MacadamiaShogi, MacState        # noqa: E402
from agp.shogilike import BLACK, WHITE                                 # noqa: E402

G = MacadamiaShogi()
KK = {(0, 0): (BLACK, "K"), (12, 12): (WHITE, "K")}


def st(board, to_move=BLACK, promoted=()):
    s = MacState(board=dict(board), promoted=frozenset(promoted),
                 hands={BLACK: {}, WHITE: {}}, to_move=to_move)
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


def dests(s, frm):
    fs = f"{frm[0]},{frm[1]}"
    return set(m.split(">")[-1] for m in G.legal_moves(s)
               if m.startswith(fs + ">") and not m.endswith("=+"))


def moves_from(s, frm):
    return sorted(m for m in G.legal_moves(s) if m.startswith(frm + ">"))


def main():
    s0 = G.initial_state()

    # ---- 1) setup ----------------------------------------------------------
    assert G.WIDTH == G.HEIGHT == 13 and G.ZONE == 0
    assert len(s0.board) == 96
    for pl in (BLACK, WHITE):
        assert sum(1 for v in s0.board.values() if v[0] == pl) == 48
    from collections import Counter
    per = {"P": 13, "I": 2, "C": 2, "S": 2, "G": 2, "T": 2, "X": 1, "O": 1,
           "N": 1, "Y": 1, "Z": 1, "E": 1, "K": 1, "L": 2, "F": 2, "A": 1,
           "M": 1, "U": 1, "V": 1, "B": 2, "R": 2, "J": 1, "H": 1, "W": 1,
           "D": 2, "Q": 1}
    assert sum(per.values()) == 48 and len(per) == 26
    bc = Counter(t for (p, t) in s0.board.values() if p == BLACK)
    for t, n in per.items():
        assert bc[t] == n, (t, n, bc[t])
    # spot squares (config: files a-m = col 0-12; rank r -> row r-1)
    assert s0.board[(6, 0)] == (BLACK, "K")          # g1 King
    assert s0.board[(5, 0)] == (BLACK, "Z")          # f1 Priest
    assert s0.board[(7, 0)] == (BLACK, "Y")          # h1 Pirate
    assert s0.board[(3, 1)] == (BLACK, "N")          # d2 Lion
    assert s0.board[(9, 1)] == (BLACK, "W")          # j2 Wolf
    assert s0.board[(6, 2)] == (BLACK, "Q")          # g3 Queen
    assert s0.board[(5, 2)] == (BLACK, "J") and s0.board[(7, 2)] == (BLACK, "H")
    assert s0.board[(3, 4)] == (BLACK, "I")          # d5 Snake
    # mirror symmetry (Gote = 180-degree rotation)
    for (c, r), (p, t) in s0.board.items():
        if p == BLACK:
            assert s0.board[(12 - c, 12 - r)] == (WHITE, t)
    assert s0.board[(6, 12)] == (WHITE, "K")

    # ---- 2) opening perft (self-computed, frozen) --------------------------
    ms0 = G.legal_moves(s0)
    assert len(ms0) == len(set(ms0)), "duplicate initial move strings"
    assert perft(s0, 1) == 51, perft(s0, 1)
    assert perft(s0, 2) == 2601, perft(s0, 2)

    # ---- 2b) 180-degree rotational symmetry (identical armies) -------------
    # The game is symmetric under a 180-degree rotation + colour swap, so from a
    # symmetric position White's legal moves must equal the rotation of Black's.
    # This locks in the correct handling of the CHIRAL pieces (Priest/Pirate
    # lateral step, Left/Right Chariot diagonals): White must be a ROTATION of
    # Black, not a left-right mirror.
    def _rot(cs):
        c, r = cs.split(","); return f"{12 - int(c)},{12 - int(r)}"
    def _rotmove(m):
        prom = m.endswith("=+"); raw = m[:-2] if prom else m
        return ">".join(_rot(p) for p in raw.split(">")) + ("=+" if prom else "")
    sw0 = MacState(board=dict(s0.board), promoted=frozenset(s0.promoted),
                   hands={BLACK: {}, WHITE: {}}, to_move=WHITE)
    sw0.key = G._poskey(sw0); sw0.reps = {sw0.key: 1}
    assert {_rotmove(m) for m in G.legal_moves(s0)} == set(G.legal_moves(sw0))
    # a lone White chiral piece rotates (does not mirror) its Black twin
    for L, blk, wht in (("Z", "5,6", "7,6"), ("Y", "7,6", "5,6")):   # priest,pirate
        sb = st({(6, 6): (BLACK, L), (0, 0): (BLACK, "K"), (12, 12): (WHITE, "K")})
        sw = st({(6, 6): (WHITE, L), (0, 0): (BLACK, "K"), (12, 12): (WHITE, "K")}, to_move=WHITE)
        bd = {m.split(">")[-1] for m in G.legal_moves(sb) if m.startswith("6,6>")}
        wd = {m.split(">")[-1] for m in G.legal_moves(sw) if m.startswith("6,6>")}
        assert blk in bd and wht in wd and blk not in wd, (L, sorted(bd), sorted(wd))

    # ---- 3) piece geometry from a central square (Betza-frozen) ------------
    def D(letter, exp, promoted=False):
        s = st({(6, 6): (BLACK, letter), **KK}, promoted={(6, 6)} if promoted else ())
        got = dests(s, (6, 6))
        assert got == set(exp), (letter, promoted, sorted(got), sorted(set(exp)))
    D("I", ["6,5", "6,7"])                                            # vW snake
    D("C", ["6,5", "6,7", "5,7", "7,7"])                             # vWfF copper
    D("S", ["5,5", "5,7", "6,7", "7,5", "7,7"])                      # FfW silver
    D("G", ["5,6", "5,7", "6,5", "6,7", "7,6", "7,7"])              # WfF gold
    D("T", ["5,5", "5,6", "5,7", "6,5", "7,5", "7,6", "7,7"])       # FsbW tiger (no fwd orth)
    D("X", ["4,4", "4,8", "5,6", "6,5", "6,7", "7,6", "8,4", "8,8"])  # WA phoenix (alfil jumps)
    D("O", ["4,6", "5,5", "5,7", "6,4", "6,8", "7,5", "7,7", "8,6"])  # FD kirin (dabbaba jumps)
    D("Y", ["5,5", "5,7", "7,5", "7,6", "7,7"])                     # pirate: 4 diag + right step
    D("Z", ["5,5", "5,6", "5,7", "7,5", "7,7"])                     # priest: 4 diag + left step
    D("E", ["5,5", "5,6", "5,7", "6,7", "7,5", "7,6", "7,7"])       # FfsW elephant (no back orth)
    D("L", ["6,7", "6,8", "6,9", "6,10", "6,11", "6,12"])           # fR lance
    D("F", ["4,4", "4,8", "5,5", "5,7", "7,5", "7,7", "8,4", "8,8"])  # F2 dragon (diag ride max 2)
    # guardian W3fF, wrestler F3sW: ranged rides
    D("A", ["3,6", "4,6", "5,6", "5,7", "6,3", "6,4", "6,5", "6,7", "6,8",
            "6,9", "7,6", "7,7", "8,6", "9,6"])
    D("M", ["3,3", "3,9", "4,4", "4,8", "5,5", "5,6", "5,7", "7,5", "7,6",
            "7,7", "8,4", "8,8", "9,3", "9,9"])
    # promoted forms
    D("I", ["6,0", "6,1", "6,2", "6,3", "6,4", "6,5", "6,7", "6,8", "6,9",
            "6,10", "6,11", "6,12"], promoted=True)                 # +I Sliding Snake vR
    D("O", ["0,6", "1,6", "2,6", "3,6", "10,6", "11,6", "12,6", "4,6",
            "3,3", "3,9", "4,4", "4,8", "5,5", "5,6", "5,7", "6,4", "6,5",
            "6,7", "6,8", "7,5", "7,6", "7,7", "8,4", "8,6", "8,8", "9,3",
            "9,6", "9,9"], promoted=True)                           # +O Unicorn sRvW2F3

    # ---- 4) Lion double-mover (piece N) ------------------------------------
    s = st({(6, 6): (BLACK, "N"), **KK})
    lion = set(moves_from(s, "6,6"))
    assert len([m for m in lion if m.count(">") == 1]) == 24          # 5x5 leaps/steps
    assert len([m for m in lion if m.count(">") == 2 and
                m.split(">")[0] == m.split(">")[2]]) == 8             # passes f>m>f
    # double capture / igui against two adjacent enemies
    s = st({(6, 6): (BLACK, "N"), (6, 7): (WHITE, "P"), (7, 8): (WHITE, "S"), **KK})
    ms = set(G.legal_moves(s))
    assert "6,6>6,7>7,8" in ms                                        # double capture P then S
    assert "6,6>6,7>6,6" in ms                                        # igui
    n = G.apply_move(s, "6,6>6,7>7,8")
    assert n.board[(7, 8)] == (BLACK, "N") and (6, 7) not in n.board

    # ---- 5) Wolf (Lion Dog) triple-mover (piece W) -------------------------
    s = st({(6, 6): (BLACK, "W"), (6, 7): (WHITE, "P"), (6, 8): (WHITE, "P"),
            (6, 9): (WHITE, "P"), **KK})
    ms = set(m for m in G.legal_moves(s) if m.startswith("6,6"))
    assert "6,6>6,7>6,8>6,9" in {m[:-2] if m.endswith("=+") else m for m in ms}
    m3 = next(m for m in ms if (m[:-2] if m.endswith("=+") else m) == "6,6>6,7>6,8>6,9")
    n = G.apply_move(s, m3)
    assert (6, 7) not in n.board and (6, 8) not in n.board and n.board[(6, 9)][0] == BLACK
    # jump over own pieces (3-leap lands past friends)
    s = st({(6, 6): (BLACK, "W"), (6, 7): (BLACK, "P"), (6, 8): (BLACK, "P"), **KK})
    assert "6,6>6,9" in set(G.legal_moves(s))
    # igui: annihilate an adjacent enemy without moving
    s = st({(6, 6): (BLACK, "W"), (7, 6): (WHITE, "P"), **KK})
    n = G.apply_move(s, "6,6>7,6>6,6")
    assert n.board[(6, 6)] == (BLACK, "W") and (7, 6) not in n.board

    # ---- 6) bent movers (single 90-degree turn) ----------------------------
    s = st({(6, 6): (BLACK, "J"), (8, 8): (BLACK, "P"), **KK})       # capricorn, own on FR ray
    d = dests(s, (6, 6))
    assert "7,7" in d and "8,8" not in d                             # blocked at own piece
    assert "5,7" in d and "4,8" in d                                 # slides other diagonals
    assert "9,5" in d                                                # bend: FR to (7,5) then... reach (9,5)? via FR+... check a genuine bend target
    s = st({(6, 6): (BLACK, "H"), (6, 8): (WHITE, "P"), **KK})       # hook mover
    d = dests(s, (6, 6))
    assert "6,7" in d and "6,8" in d and "6,9" not in d             # forward ray stops at capture
    assert "0,6" in d and "6,0" in d                                 # straight rook rays
    assert "3,8" in d                                                # bend: up then left along rank 8

    # ---- 7) Emperor (universal leaper) + Prince ----------------------------
    s = st({(6, 6): (BLACK, "K")}, promoted={(6, 6)})               # promoted King = Emperor
    s.board[(0, 0)] = (BLACK, "R"); s.board[(12, 12)] = (WHITE, "K")
    s.key = G._poskey(s); s.reps = {s.key: 1}
    d = dests(s, (6, 6))
    assert "0,12" in d and "12,0" in d and "1,7" in d               # any empty square
    assert "12,12" in d                                              # may capture the enemy King
    assert len(d) == 169 - 1 - 1                                     # all but self + own Rook
    assert G._is_royal("E", True) and not G._is_royal("E", False)   # Prince royal, Elephant not

    # ---- 8) PROMOTION BY CAPTURE -------------------------------------------
    # optional on capturing an unpromoted piece
    s = st({(6, 6): (BLACK, "R"), (6, 8): (WHITE, "P"), **KK})
    ms = moves_from(s, "6,6")
    assert "6,6>6,8" in ms and "6,6>6,8=+" in ms
    assert G.apply_move(s, "6,6>6,8").board[(6, 8)] == (BLACK, "R")
    assert (6, 8) in G.apply_move(s, "6,6>6,8=+").promoted
    # no promotion without a capture
    s = st({(6, 6): (BLACK, "R"), **KK})
    assert not any(m.endswith("=+") for m in moves_from(s, "6,6"))
    # forced when the captured piece was itself promoted
    s = st({(6, 6): (BLACK, "R"), (6, 8): (WHITE, "S")}, promoted={(6, 8)})
    s.board.update(KK); s.key = G._poskey(s); s.reps = {s.key: 1}
    ms = moves_from(s, "6,6")
    assert "6,6>6,8=+" in ms and "6,6>6,8" not in ms
    # Saint override: any non-royal capturing a Priest becomes a Saint (Z+prom)
    s = st({(6, 6): (BLACK, "R"), (6, 8): (WHITE, "Z"), **KK})
    assert "6,6>6,8=+" in moves_from(s, "6,6") and "6,6>6,8" not in moves_from(s, "6,6")
    n = G.apply_move(s, "6,6>6,8=+")
    assert n.board[(6, 8)] == (BLACK, "Z") and (6, 8) in n.promoted
    # Ghost override: capturing a Pirate -> Ghost (Y+prom)
    s = st({(6, 6): (BLACK, "B"), (7, 7): (WHITE, "Y"), **KK})
    n = G.apply_move(s, "6,6>7,7=+")
    assert n.board[(7, 7)] == (BLACK, "Y") and (7, 7) in n.promoted
    # even a Queen (never promotes normally) becomes a Saint on a Priest...
    s = st({(6, 6): (BLACK, "Q"), (6, 8): (WHITE, "Z"), **KK})
    assert G.apply_move(s, "6,6>6,8=+").board[(6, 8)] == (BLACK, "Z")
    # ...but a Queen capturing a plain pawn is NOT offered promotion
    s = st({(6, 6): (BLACK, "Q"), (6, 8): (WHITE, "P"), **KK})
    assert not any(m.endswith("=+") for m in moves_from(s, "6,6"))
    # royal exclusion: King x Priest -> Emperor (optional), never Saint
    s = st({(6, 6): (BLACK, "K"), (6, 7): (WHITE, "Z")},
           to_move=BLACK)
    s.board[(0, 0)] = (BLACK, "R"); s.board[(12, 12)] = (WHITE, "K")
    s.key = G._poskey(s); s.reps = {s.key: 1}
    ms = moves_from(s, "6,6")
    assert "6,6>6,7" in ms and "6,6>6,7=+" in ms
    assert G.apply_move(s, "6,6>6,7=+").board[(6, 7)] == (BLACK, "K")   # Emperor
    # Elephant -> King via capture
    s = st({(6, 6): (BLACK, "E"), (6, 7): (WHITE, "P")})
    s.board[(0, 0)] = (BLACK, "K"); s.board[(12, 12)] = (WHITE, "K")
    s.key = G._poskey(s); s.reps = {s.key: 1}
    n = G.apply_move(s, "6,6>6,7=+")
    assert n.board[(6, 7)] == (BLACK, "E") and (6, 7) in n.promoted

    # ---- 9) win by capturing ALL royals (dual royalty) ---------------------
    # Black has King + Prince; White Rook takes the King -> Prince still reigns
    s = st({(6, 3): (WHITE, "R"), (6, 6): (BLACK, "K"), (6, 8): (BLACK, "E"),
            (0, 0): (WHITE, "K")}, to_move=WHITE, promoted={(6, 8)})
    n = G.apply_move(s, "6,3>6,6")
    assert n.winner is None and not G.is_terminal(n)
    # now take the Prince -> Black has no royal -> White wins
    s = st({(6, 6): (WHITE, "R"), (6, 8): (BLACK, "E"), (0, 0): (WHITE, "K")},
           to_move=WHITE, promoted={(6, 8)})
    n = G.apply_move(s, "6,6>6,8")
    assert n.winner == WHITE and G.is_terminal(n) and G.returns(n) == [-1.0, 1.0]

    # ---- 10) repetition draw + random game terminates ----------------------
    s = st({(6, 6): (BLACK, "R"), (0, 6): (WHITE, "R"),
            (6, 0): (BLACK, "K"), (6, 12): (WHITE, "K")})
    seq = ["6,6>7,6", "0,6>1,6", "7,6>6,6", "1,6>0,6"]
    n = s
    for _ in range(3):
        for m in seq:
            assert not G.is_terminal(n)
            n = G.apply_move(n, m)
    assert G.is_terminal(n) and G.returns(n) == [0.0, 0.0]

    n = G.apply_move(s0, "9,1>12,4")                                 # a Wolf 3-jump (m5)
    snap = G.serialize(n)
    assert json.dumps(G.serialize(G.deserialize(snap)), sort_keys=True) == \
        json.dumps(snap, sort_keys=True)

    rng = random.Random(42)
    sx = G.initial_state()
    for _ in range(G.PLY_CAP + 1):
        if G.is_terminal(sx):
            break
        sx = G.apply_move(sx, rng.choice(G.legal_moves(sx)))
    assert G.is_terminal(sx)
    ret = G.returns(sx)
    assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

    print("macadamia_shogi selftest: all checks passed")


if __name__ == "__main__":
    main()
