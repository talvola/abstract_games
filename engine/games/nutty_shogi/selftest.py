"""Nutty Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Anchors (all sourced from https://www.chessvariants.com/rules/nutty-shogi):
  * the exact 13x13 / 50-piece / 25-type starting setup (chariot d2, buffalo k2
    per the executable interactive-diagram Betza block; White = 180 rotation);
  * each exotic piece's move from a central square, frozen from the Betza block:
    Lion (double king-move), Griffon (Lion+Bishop), Harpy (Queen+diagonal Lion),
    Jumping Rook/Bishop/Queen + Regent (jump lower-ranked pieces when capturing),
    Tetrarchs (skip square 1), Eagle/Unicorn (forward-diagonal / forward sting),
    Fire Demon (Bishop + sideways slide + 3-step area move);
  * Fire Demon burning: active burn after moving, passive-priority burn (a piece
    moving next to a Demon is destroyed and the Demon survives), burning the King
    wins, a Buffalo promoting to Fire Demon burns immediately, capturing a Demon
    by landing on it is safe;
  * jumping-general rank order (King > Jumping Queen > Regent > Jumping Rook/
    Bishop > others): jump over strictly-lower, capture any rank, cannot pass an
    equal/higher jumper;
  * Lion double-move / igui / out-and-back pass; a promotion example;
  * win by capturing OR burning the King via apply_move (not a hand-built state);
  * attacked() (forward from the move generator) agrees with a direct capture
    diff over random exotic boards, and reports obvious attacks;
  * self-computed perft 43 / 1845 / 85710 at depths 1-3 (frozen);
  * serialize / deserialize round-trips; random games terminate.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.nutty_shogi.game import NuttyShogi, NuttyState        # noqa: E402
from agp.shogilike import BLACK, WHITE                           # noqa: E402

G = NuttyShogi()
Kk = {(0, 0): (BLACK, "K"), (12, 12): (WHITE, "K")}


def st(board, to_move=BLACK, promoted=(), ply=0):
    s = NuttyState(board=dict(board), promoted=frozenset(promoted),
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


def targets(s, frm="6,6"):
    """Destination cells of simple 2-cell (non-promoting) moves from `frm`."""
    out = set()
    for m in G.legal_moves(s):
        if m.endswith("=+") or m.count(">") != 1:
            continue
        f, t = m.split(">")
        if f == frm:
            out.add(t)
    return out


def solo(letter, sq=(6, 6), to_move=BLACK, promoted=False, extra=()):
    b = dict(Kk)
    b[sq] = (to_move, letter)
    b.update(dict(extra))
    return st(b, to_move=to_move,
              promoted={sq} if promoted else ())


def main():
    s0 = G.initial_state()

    # ---- 1) setup ----------------------------------------------------------
    assert G.WIDTH == G.HEIGHT == 13 and G.ZONE == 4
    assert len(s0.board) == 100
    for pl in (BLACK, WHITE):
        assert sum(1 for v in s0.board.values() if v[0] == pl) == 50
    counts = {}
    for (pl, t) in s0.board.values():
        counts[(pl, t)] = counts.get((pl, t), 0) + 1
    per_type = {"K": 1, "FD": 1, "LN": 1, "Q": 1, "KY": 1, "PH": 1, "CS": 1,
                "WB": 1, "VG": 1, "BG": 1, "RG": 1,
                "G": 2, "S": 2, "FL": 2, "BT": 2, "N": 2, "L": 2, "VM": 2,
                "SS": 2, "B": 2, "R": 2, "DH": 2, "DK": 2, "D": 2, "P": 13}
    assert sum(per_type.values()) == 50 and len(per_type) == 25
    for pl in (BLACK, WHITE):
        for t, n in per_type.items():
            assert counts[(pl, t)] == n, (pl, t, counts.get((pl, t)))
    # spot squares (a1=col0 .. m1=col12; rank r -> row r-1; Black at bottom)
    assert s0.board[(6, 0)] == (BLACK, "K") and s0.board[(6, 1)] == (BLACK, "FD")
    assert s0.board[(5, 1)] == (BLACK, "LN") and s0.board[(7, 1)] == (BLACK, "Q")
    assert s0.board[(2, 1)] == (BLACK, "KY") and s0.board[(9, 1)] == (BLACK, "PH")
    assert s0.board[(3, 1)] == (BLACK, "CS"), "chariot on d2 (Betza block)"
    assert s0.board[(10, 1)] == (BLACK, "WB"), "buffalo on k2 (Betza block)"
    assert s0.board[(6, 2)] == (BLACK, "RG") and s0.board[(5, 2)] == (BLACK, "BG")
    assert s0.board[(7, 2)] == (BLACK, "VG")
    assert s0.board[(3, 4)] == (BLACK, "D") and s0.board[(9, 4)] == (BLACK, "D")
    assert s0.board[(1, 0)] == (BLACK, "N") and s0.board[(0, 0)] == (BLACK, "L")
    # White = 180 rotation
    assert s0.board[(6, 12)] == (WHITE, "K") and s0.board[(6, 11)] == (WHITE, "FD")
    assert s0.board[(7, 11)] == (WHITE, "LN") and s0.board[(5, 11)] == (WHITE, "Q")
    assert sum(1 for (c, r), (p, t) in s0.board.items()
               if p == BLACK and t == "P" and r == 3) == 13

    # ---- 2) plain colour-relative pieces (spot) -----------------------------
    assert targets(solo("S")) == {"6,7", "5,7", "7,7", "5,5", "7,5"}      # silver
    assert targets(solo("G")) == {"6,7", "6,5", "5,6", "7,6", "5,7", "7,7"}  # gold
    assert targets(solo("N")) == {"5,8", "7,8"}                           # shogi knight
    assert targets(solo("N", to_move=WHITE)) == {"5,4", "7,4"}            # flips
    assert targets(solo("D")) == {"6,7", "5,5", "7,5"}                    # dog bFfW
    assert targets(solo("D", promoted=True)) == \
        {"6,7", "6,8", "6,9", "6,10", "6,11", "6,12",                     # greyhound fR
         "5,5", "4,4", "3,3", "2,2", "1,1", "7,5", "8,4", "9,3", "10,2",  # bB
         "11,1", "12,0"}
    assert targets(solo("KY")) == {"5,7", "7,7", "5,5", "7,5",            # kirin FD
                                   "6,8", "6,4", "8,6", "4,6"}

    # ---- 3) exotic move sets (frozen from the Betza block) ------------------
    # LION: 8 adjacent steps + 16 distance-2 leaps (2-cell), symmetric
    lm = set(moves_from(solo("LN"), "6,6"))
    assert len([m for m in lm if m.count(">") == 1]) == 24
    assert "6,6>6,8" in lm and "6,6>4,4" in lm                     # dist-2 leaps
    assert "6,6>7,7>6,6" in lm and "6,6>8,8" in lm                 # pass / dist-2 leap
    # GRIFFON = Lion + Bishop: adds long diagonal slides
    gm = set(moves_from(solo("LN", promoted=True), "6,6"))
    assert "6,6>9,9" in gm and "6,6>3,9" in gm                     # bishop rays
    assert "6,6>6,8" in gm                                         # lion ortho leap
    # HARPY = Queen + diagonal Lion
    hm = set(moves_from(solo("Q", promoted=True), "6,6"))
    assert "6,6>6,12" in hm and "6,6>12,0" in hm                   # queen rays
    hm2 = set(G.legal_moves(solo("Q", promoted=True,
              extra={(7, 7): (WHITE, "P"), (8, 8): (WHITE, "S")})))
    assert "6,6>7,7>8,8" in hm2 and "6,6>7,7>6,6" in hm2           # diag double / igui
    assert "6,6>8,8" in hm2                                        # 2-diag jump over P
    # UNICORN (=+DH): slides everywhere but forward; forward = sting (<=2)
    um = set(moves_from(solo("DH", promoted=True), "6,6"))
    assert "6,6>6,0" in um and "6,6>9,9" in um                     # back / diag slides
    assert "6,6>6,7>6,7" in um and "6,6>6,8" in um                 # sting step / 2-leap
    assert "6,6>6,9" not in um                                    # NO forward slide >2
    # EAGLE (=+DK): slides but forward-diagonals; those = sting
    em = set(moves_from(solo("DK", promoted=True), "6,6"))
    assert "6,6>6,12" in em and "6,6>3,3" in em                    # rook / back-diag
    assert "6,6>7,7>7,7" in em and "6,6>8,8" in em                 # fwd-diag sting
    assert "6,6>9,9" not in em                                    # no fwd-diag slide >2
    # TETRARCHS (=+CS): skip square 1; unlimited long, 2-3 sideways; + igui
    tm = targets(solo("CS", promoted=True), "6,6")
    assert "6,6>6,7" not in moves_from(solo("CS", promoted=True), "6,6")  # can't land sq1
    assert "6,6" and "6,8" in tm and "6,12" in tm                 # forward from sq2
    assert {"4,6", "3,6"} <= tm and "5,6" not in tm and "2,6" not in tm   # sideways 2-3
    ti = set(G.legal_moves(solo("CS", promoted=True,
             extra={(7, 7): (WHITE, "P")})))
    assert "6,6>7,7>6,6" in ti                                    # igui (capture in place)
    # FIRE DEMON slide = Bishop + sideways (no vertical slide); + area move
    fm = targets(solo("FD"), "6,6")
    assert "6,6>9,9" in [m for m in moves_from(solo("FD"), "6,6")]  # bishop ray
    assert "5,6" in fm and "0,6" in fm                            # sideways slide
    assert "6,7" in fm and "6,9" in fm and "6,10" not in fm       # area move <=3 fwd

    # ---- 4) jumping-general rank order --------------------------------------
    # Jumping Bishop (rank1) jumps over own low pieces to capture; not over a
    # rank>=1 jumper, but may CAPTURE it.
    s = solo("BG", extra={(7, 7): (BLACK, "P"), (8, 8): (WHITE, "P")})
    assert "6,6>8,8" in G.legal_moves(s) and "6,6>7,7" not in G.legal_moves(s)
    s = solo("BG", extra={(7, 7): (WHITE, "BG"), (8, 8): (WHITE, "P")})
    assert "6,6>7,7" in G.legal_moves(s)         # capture equal-rank jumper: OK
    assert "6,6>8,8" not in G.legal_moves(s)     # cannot jump PAST it
    # Jumping Queen (rank3) CAN jump over a Regent (rank2)
    s = solo("RG", promoted=True,
             extra={(7, 7): (WHITE, "VG"), (8, 8): (WHITE, "P")})
    assert "6,6>7,7" in G.legal_moves(s) and "6,6>8,8" in G.legal_moves(s)
    # no jumper may pass a King (rank4)
    s = solo("RG", promoted=True,
             extra={(6, 7): (WHITE, "K"), (6, 9): (WHITE, "P")})
    assert "6,6>6,7" in G.legal_moves(s) and "6,6>6,9" not in G.legal_moves(s)
    # Regent (VG) = jumping bishop + area move (no promotion)
    rm = set(G.legal_moves(solo("VG")))
    assert "6,6>9,9" in rm and "6,6>6,9" in rm and "6,6>6,10" not in rm
    assert not any(m.endswith("=+") for m in rm)                  # Regent never promotes

    # ---- 5) Fire Demon burning ----------------------------------------------
    # active burn: FD steps next to enemies -> both incinerated
    s = solo("FD", extra={(7, 8): (WHITE, "P"), (8, 8): (WHITE, "S")})
    n = G.apply_move(s, "6,6>7,7")
    assert n.board.get((7, 7)) == (BLACK, "FD")
    assert (7, 8) not in n.board and (8, 8) not in n.board
    # passive burn has PRIORITY: a piece moving next to a Demon dies; the Demon
    # lives (and whatever it would have captured is gone too).
    s = st({(6, 6): (WHITE, "FD"), (6, 4): (BLACK, "R"), (7, 5): (WHITE, "P"),
            **Kk}, to_move=BLACK)
    n = G.apply_move(s, "6,4>7,5")               # Rook captures P but lands next to FD
    assert (7, 5) not in n.board                  # Rook incinerated on arrival...
    assert n.board.get((6, 6)) == (WHITE, "FD")   # ...Demon survives
    # two Demons: the mover dies, the stationary one survives (no mutual burn)
    s = st({(6, 6): (WHITE, "FD"), (6, 4): (BLACK, "FD"), **Kk}, to_move=BLACK)
    n = G.apply_move(s, "6,4>6,5")
    assert (6, 5) not in n.board and n.board.get((6, 6)) == (WHITE, "FD")
    # capturing a Fire Demon by landing exactly on it is SAFE
    s = st({(6, 6): (BLACK, "R"), (6, 9): (WHITE, "FD"), **Kk})
    n = G.apply_move(s, "6,6>6,9")
    assert n.board.get((6, 9)) == (BLACK, "R") and n.winner is None
    # burning the King wins (in your own turn)
    s = st({(6, 6): (BLACK, "FD"), (7, 8): (WHITE, "K"), (0, 0): (BLACK, "K")})
    n = G.apply_move(s, "6,6>7,7")
    assert (7, 8) not in n.board and n.winner == BLACK and G.is_terminal(n)
    assert G.returns(n) == [1.0, -1.0]
    # ...and moving your own King next to an enemy Demon loses (opponent's win)
    s = st({(6, 6): (WHITE, "FD"), (6, 4): (BLACK, "K"), (0, 0): (WHITE, "K")},
           to_move=BLACK)
    n = G.apply_move(s, "6,4>6,5")
    assert (6, 5) not in n.board and n.winner == WHITE
    # a Buffalo promoting to Fire Demon burns adjacent enemies immediately
    s = st({(3, 2): (BLACK, "WB"), (4, 4): (WHITE, "P"), **Kk})
    n = G.apply_move(s, "3,2>3,3=+")             # enters zone, promotes -> FD
    assert (3, 3) in n.promoted and (4, 4) not in n.board

    # ---- 6) Lion double-move / igui / pass ----------------------------------
    s = st({(6, 6): (BLACK, "LN"), (6, 7): (WHITE, "P"), (7, 8): (WHITE, "S"),
            **Kk})
    ms = set(G.legal_moves(s))
    assert "6,6>6,7>7,8" in ms                    # double capture P then S
    assert "6,6>6,7>6,6" in ms                    # igui: capture P in place
    assert "6,6>5,5>6,6" in ms                    # pass via an empty square
    n = G.apply_move(s, "6,6>6,7>7,8")
    assert n.board.get((7, 8)) == (BLACK, "LN") and (6, 7) not in n.board
    n = G.apply_move(s, "6,6>6,7>6,6")
    assert n.board.get((6, 6)) == (BLACK, "LN") and (6, 7) not in n.board
    n = G.apply_move(s, "6,6>5,5>6,6")            # pass: board unchanged, turn passes
    assert n.board == s.board and n.to_move == WHITE

    # ---- 7) promotion (zone = far FOUR ranks: rows 9-12 for Black) -----------
    s = st({(3, 8): (BLACK, "S"), **Kk})
    ms = set(G.legal_moves(s))
    assert "3,8>3,9" in ms and "3,8>3,9=+" in ms           # entering the zone
    assert "3,8>2,8" not in ms                             # (S has no sideways)
    s = st({(3, 7): (BLACK, "S"), **Kk})
    assert "3,7>3,8=+" not in set(G.legal_moves(s))        # row 8 not in zone
    s = st({(3, 9): (BLACK, "S"), **Kk})
    ms = set(G.legal_moves(s))
    assert "3,9>3,10" in ms and "3,9>3,10=+" not in ms      # quiet move inside: no
    s = st({(3, 9): (BLACK, "S"), (2, 10): (WHITE, "P"), **Kk})
    assert "3,9>2,10=+" in set(G.legal_moves(s))           # capture starting in zone
    # promoted Silver = Vertical Mover, cannot re-promote
    s = st({(3, 9): (BLACK, "S"), **Kk}, promoted={(3, 9)})
    assert not any(m.endswith("=+") for m in moves_from(s, "3,9"))
    assert "3,9>3,12" in set(G.legal_moves(s))             # vR slide
    # King / Fire Demon / Regent never promote
    s = st({(6, 10): (BLACK, "FD"), (7, 10): (BLACK, "VG"), **Kk})
    assert not any(m.endswith("=+") for m in G.legal_moves(s))

    # ---- 8) win by capturing the King via apply_move ------------------------
    s = st({(6, 5): (BLACK, "R"), (6, 12): (WHITE, "K"), (0, 0): (BLACK, "K"),
            (1, 1): (WHITE, "P")})
    n = G.apply_move(s, "6,5>6,12")               # Rook captures the King
    assert n.winner == BLACK and G.is_terminal(n) and G.returns(n) == [1.0, -1.0]

    # ---- 9) attacked() forward-consistency ----------------------------------
    # targeted: a Rook attacks along its file; a Lion attacks at distance 2;
    # a Fire Demon "attacks" (can burn) an adjacent enemy.
    s = st({(4, 4): (BLACK, "R"), (4, 9): (WHITE, "P"), **Kk})
    assert G.attacked(s, (4, 9), BLACK) and not G.attacked(s, (12, 12), BLACK)
    s = st({(4, 4): (BLACK, "LN"), (6, 6): (WHITE, "P"), **Kk})
    assert G.attacked(s, (6, 6), BLACK)
    s = st({(6, 6): (BLACK, "FD"), (7, 8): (WHITE, "P"), **Kk})
    assert G.attacked(s, (7, 8), BLACK)           # FD steps to (7,7)/(6,7) & burns
    # fuzz: attacked_squares == squares removed by some move, over random boards
    letters = ["P", "S", "G", "R", "B", "LN", "BG", "RG", "FD", "Q", "DH", "DK",
               "CS", "WB", "VG", "N", "KY"]
    rng = random.Random(20)
    for _ in range(30):
        b = dict(Kk)
        for _ in range(rng.randint(3, 9)):
            c, r = rng.randint(0, 12), rng.randint(0, 12)
            if (c, r) in b:
                continue
            b[(c, r)] = (rng.randint(0, 1), rng.choice(letters))
        by = rng.randint(0, 1)
        s = st(b, to_move=by, promoted={sq for sq in b if rng.random() < 0.2
                                        and b[sq][1] not in ("K", "FD", "VG")})
        att = G.attacked_squares(s, by)
        # independent recompute: apply each move, diff the opponent's pieces
        enemy = 1 - by
        victims = {sq for sq, (p, t) in s.board.items() if p == enemy}
        direct = set()
        for m in G._moves(s):
            nb = G.apply_move(s, m).board
            direct |= {sq for sq in victims if nb.get(sq) != s.board[sq]}
        assert att == direct

    # ---- 10) perft (self-computed, frozen) ----------------------------------
    ms0 = G.legal_moves(s0)
    assert len(ms0) == len(set(ms0)), "duplicate move strings at the root"
    assert perft(s0, 1) == 43, perft(s0, 1)
    assert perft(s0, 2) == 1845, perft(s0, 2)
    assert perft(s0, 3) == 85710, perft(s0, 3)

    # ---- 11) serialize round-trip + random games terminate ------------------
    n = G.apply_move(s0, "5,2>12,9")              # a Jumping Bishop deep snipe
    snap = G.serialize(n)
    assert json.dumps(G.serialize(G.deserialize(snap)), sort_keys=True) == \
        json.dumps(snap, sort_keys=True)
    for seed in (3, 11):
        rng = random.Random(seed)
        sx = G.initial_state()
        for _ in range(G.PLY_CAP + 1):
            if G.is_terminal(sx):
                break
            sx = G.apply_move(sx, rng.choice(G.legal_moves(sx)))
        assert G.is_terminal(sx)
        ret = G.returns(sx)
        assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

    print("nutty_shogi selftest: all checks passed")


if __name__ == "__main__":
    main()
