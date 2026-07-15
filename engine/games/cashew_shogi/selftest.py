"""Cashew Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Every move-offset set frozen below was DIFFERENTIAL-CONFIRMED against HaChu 0.21
(H. G. Muller's reference engine for `variant cashew-shogi`): HaChu prints, on
loading the variant, its full initial FEN (matched here rank-by-rank) and every
piece's Betza string, and these tables reproduce those exact definitions.

Anchors:
  * the exact 13x13 / 54-piece / 35-type starting setup + the 8-per-side
    already-promoted partners (goblin/crowned bishop/queen/castle/hook mover/
    golden bird/unicorn/flag);
  * the asymmetric flank pieces' exact move offsets (Left/Right General,
    Broad/Deep Guard, Left/Right Chariot) + Viper / Dragon / Elephant / Golden
    Bird -- the highest-risk Betza translations, each == HaChu's string;
  * Lion double-move (24 leaps + 8 passes), Wolf (Lion-Dog) 3-step ray jumps
    and multi-capture paths, Goblin (bent Bishop) and Hook Mover (bent Rook);
  * promotion BY CAPTURE ONLY, mandatory, no zone: a capturing promotable piece
    promotes, a quiet move never does, and Pawns never promote;
  * win by capturing the King via apply_move; fourfold-repetition draw;
  * opening perft 21 / 423 at depths 1-2 (self-computed, frozen);
  * serialize/deserialize round-trip; a random game terminates.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.cashew_shogi.game import CashewShogi, CashewState        # noqa: E402
from agp.shogilike import BLACK, WHITE                              # noqa: E402

G = CashewShogi()


def st(board, to_move=BLACK, promoted=(), ply=0):
    s = CashewState(board=dict(board), promoted=frozenset(promoted),
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


def offsets(letter, at=(6, 6), promoted=False):
    KK = {(0, 0): (BLACK, "K"), (12, 12): (WHITE, "K")}
    b = dict(KK)
    b[at] = (BLACK, letter)
    s = st(b, promoted=([at] if promoted else []))
    out = set()
    for m in G.legal_moves(s):
        if not m.startswith(f"{at[0]},{at[1]}>"):
            continue
        c, r = map(int, m.split(">")[-1].split(","))
        out.add((c - at[0], r - at[1]))
    return out


def main():
    s0 = G.initial_state()

    # ---- 1) setup ---------------------------------------------------------
    assert G.WIDTH == G.HEIGHT == 13
    assert len(s0.board) == 108
    for pl in (BLACK, WHITE):
        assert sum(1 for v in s0.board.values() if v[0] == pl) == 54
    assert len(s0.promoted) == 16                          # 8 promoted partners a side
    counts = {}
    for (pl, t) in s0.board.values():
        if pl == BLACK:
            counts[t] = counts.get(t, 0) + 1
    per_type = {"LA": 2, "KT": 2, "BU": 2, "FH": 2, "LG": 1, "K": 1, "RG": 1,
                "DR": 2, "VP": 2, "BG": 1, "LN": 1, "PH": 2, "G": 2, "N": 2,
                "KI": 2, "WO": 1, "DG": 1, "LC": 1, "BE": 2, "VI": 1, "FL": 2,
                "S": 2, "TI": 2, "HU": 1, "RC": 1, "P": 13, "GU": 2}
    assert len(per_type) == 27 and sum(per_type.values()) == 54
    assert counts == per_type, counts
    # spot squares (Black bottom; col 0 = file a, row r -> rank r+1)
    assert s0.board[(6, 0)] == (BLACK, "K")                # king g1
    assert s0.board[(5, 0)] == (BLACK, "LG") and s0.board[(7, 0)] == (BLACK, "RG")
    assert s0.board[(2, 1)] == (BLACK, "LN")              # lion c2
    assert s0.board[(10, 1)] == (BLACK, "WO")            # wolf k2
    assert s0.board[(3, 4)] == (BLACK, "GU") and s0.board[(9, 4)] == (BLACK, "GU")
    # already-promoted partners (base letter + promoted flag). Squares match
    # HaChu's printed initial FEN: c1 Crowned Bishop, j1 Castle (NOT d1/k1).
    for sq, base, tag in [((1, 0), "KT", "goblin"), ((2, 0), "BU", "crowned bishop"),
                          ((4, 0), "FH", "queen"), ((9, 0), "DR", "castle"),
                          ((11, 0), "VP", "hook mover"), ((3, 1), "PH", "golden bird"),
                          ((9, 1), "KI", "unicorn"), ((6, 2), "N", "flag")]:
        assert s0.board[sq] == (BLACK, base) and sq in s0.promoted, (sq, tag)
    # the promotable partners sit adjacent and start UNPROMOTED (Muller/HaChu):
    #   d1 Butterfly (-> Crowned Bishop), k1 Dragon (-> Castle).
    assert s0.board[(3, 0)] == (BLACK, "BU") and (3, 0) not in s0.promoted   # d1 butterfly
    assert s0.board[(10, 0)] == (BLACK, "DR") and (10, 0) not in s0.promoted  # k1 dragon
    # White = 180-degree rotation: rightgen/leftgen swapped on the back rank
    assert s0.board[(5, 12)] == (WHITE, "RG") and s0.board[(7, 12)] == (WHITE, "LG")
    assert s0.board[(6, 12)] == (WHITE, "K")

    # ---- 2) asymmetric flank pieces (HaChu Betza, frozen) -----------------
    assert offsets("LG") == {(-1, -1), (-1, 1), (0, -1), (0, 1),
                             (1, -1), (1, 0), (1, 1)}          # FvrW: no left step
    assert offsets("RG") == {(-1, -1), (-1, 0), (-1, 1), (0, -1),
                             (0, 1), (1, -1), (1, 1)}          # FvlW: no right step
    assert offsets("BG") == {(-6, 0), (-5, 0), (-4, 0), (-3, 0), (-2, 0), (-1, 0),
                             (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),      # sR
                             (0, -2), (0, -1), (0, 1), (0, 2),                    # vW2
                             (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6),      # frB
                             (-1, 1)}                                            # flF
    assert offsets("DG") == {(0, -6), (0, -5), (0, -4), (0, -3), (0, -2), (0, -1),
                             (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),      # vR
                             (-2, 0), (-1, 0), (1, 0), (2, 0),                    # sW2
                             (-1, 1), (-2, 2), (-3, 3), (-4, 4), (-5, 5), (-6, 6),  # flB
                             (1, 1)}                                             # frF
    assert offsets("LC") == {(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),      # fR
                             (0, -1),                                            # bW
                             (-1, 1), (-2, 2), (-3, 3), (-4, 4), (-5, 5), (-6, 6),  # FL ray
                             (1, -1), (2, -2), (3, -3), (4, -4), (5, -5), (6, -6)}  # BR ray
    assert offsets("RC") == {(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
                             (0, -1),
                             (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6),      # FR ray
                             (-1, -1), (-2, -2), (-3, -3), (-4, -4), (-5, -5)}    # BL ray (to edge)
    assert offsets("VP") == {(-1, 0), (1, 0), (0, 2), (-2, -2), (2, -2)}          # sWfDbA
    assert offsets("DR") == {(-1, 1), (1, 1), (-1, -1), (1, -1),
                             (-2, 2), (2, 2), (-2, -2), (2, -2)}                  # F2
    assert offsets("N", promoted=True) == {                                      # +N flag
        (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),                          # fR
        (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6),
        (-1, 1), (-2, 2), (-3, 3), (-4, 4), (-5, 5), (-6, 6),                    # fB
        (-1, -1), (1, -1), (-2, -2), (2, -2),                                    # bF2
        (0, -1), (0, -2), (-1, 0), (1, 0), (-2, 0), (2, 0)}                      # bsW2
    assert offsets("WO", promoted=True) == {                                     # +W! elephant
        (0, 1), (0, 2), (0, 3), (0, -1), (0, -2), (0, -3),                       # vW3
        (-1, 1), (1, 1), (-2, 2), (2, 2), (-3, 3), (3, 3),                       # fF3
        (-1, 0), (1, 0), (-2, 0), (2, 0), (-3, 0), (3, 0), (-4, 0), (4, 0),
        (-5, 0), (5, 0),                                                         # sW5
        (-1, -1), (1, -1), (-2, -2), (2, -2), (-3, -3), (3, -3),
        (-4, -4), (4, -4), (-5, -5), (5, -5)}                                    # bF5

    # ---- 3) special pieces -------------------------------------------------
    KK = {(0, 0): (BLACK, "K"), (12, 12): (WHITE, "K")}
    # Lion: 24 leaps (5x5) + 8 passes on an open board
    s = st({(6, 6): (BLACK, "LN"), **KK})
    lion = [m for m in G.legal_moves(s) if m.startswith("6,6>")]
    assert len([m for m in lion if m.count(">") == 1]) == 24
    assert len([m for m in lion if m.count(">") == 2 and
                m.split(">")[0] == m.split(">")[2]]) == 8
    # Wolf: 3-step ray jumps (8 dirs x dist 1-3 = 24) + one pass on open board
    s = st({(6, 6): (BLACK, "WO"), **KK})
    assert len([m for m in G.legal_moves(s) if m.startswith("6,6>")]) == 25
    # Wolf multi-capture along a ray + forced promotion to Elephant
    s = st({(6, 6): (BLACK, "WO"), (6, 7): (WHITE, "P"), (6, 8): (WHITE, "S"), **KK})
    wm = set(G.legal_moves(s))
    for mv in ["6,6>6,7", "6,6>6,8", "6,6>6,9", "6,6>6,7>6,8", "6,6>6,7>6,9",
               "6,6>6,8>6,9", "6,6>6,7>6,8>6,9", "6,6>6,7>6,6"]:
        assert mv in wm, mv
    n = G.apply_move(s, "6,6>6,7>6,8")                     # kill P, land on S
    assert n.board[(6, 8)] == (BLACK, "WO") and (6, 8) in n.promoted  # -> Elephant
    assert (6, 7) not in n.board
    # Wolf jumps over friendly pieces (Lion-Dog): reach s3 over two own pieces
    s = st({(6, 6): (BLACK, "WO"), (6, 7): (BLACK, "P"), (6, 8): (BLACK, "S"), **KK})
    assert "6,6>6,9" in set(G.legal_moves(s))
    # Goblin (bent Bishop) reaches the whole board; Hook Mover (bent Rook) too
    s = st({(6, 6): (BLACK, "KT"), **KK}, promoted=[(6, 6)])          # +KT = goblin
    gob = [m for m in G.legal_moves(s) if m.startswith("6,6>")]
    assert any(m.count(">") == 2 for m in gob)             # has bent moves
    assert "6,6>7,7" in gob and "6,6>6,7" in gob           # diag slide + ortho step
    s = st({(6, 6): (BLACK, "VP"), **KK}, promoted=[(6, 6)])          # +VP = hook mover
    hook = [m for m in G.legal_moves(s) if m.startswith("6,6>")]
    assert len([m for m in hook if m.count(">") == 1]) == 24          # straight rook
    assert any(m.count(">") == 2 for m in hook)            # bent

    # ---- 4) promotion BY CAPTURE ONLY, mandatory, no zone -----------------
    # butterfly (promotable) capturing -> promotes to crowned bishop
    s = st({(5, 5): (BLACK, "BU"), (6, 6): (WHITE, "P"), **KK})
    n = G.apply_move(s, "5,5>6,6")
    assert (6, 6) in n.promoted and n.board[(6, 6)] == (BLACK, "BU")
    # quiet move never promotes, even deep in enemy territory (no zone)
    s = st({(5, 11): (BLACK, "BU"), **KK})
    n = G.apply_move(s, "5,11>6,12")
    assert (6, 12) not in n.promoted
    # Pawns never promote, not even on a capture
    s = st({(5, 5): (BLACK, "P"), (5, 6): (WHITE, "P"), **KK})
    assert "5,5>5,6" in set(G.legal_moves(s))
    n = G.apply_move(s, "5,5>5,6")
    assert (5, 6) not in n.promoted and n.board[(5, 6)] == (BLACK, "P")
    # a Gold (non-promotable) never promotes
    s = st({(5, 5): (BLACK, "G"), (5, 6): (WHITE, "P"), **KK})
    n = G.apply_move(s, "5,5>5,6")
    assert (5, 6) not in n.promoted

    # ---- 5) opening perft --------------------------------------------------
    ms0 = G.legal_moves(s0)
    assert len(ms0) == len(set(ms0)), "duplicate move strings"
    assert perft(s0, 1) == 21, perft(s0, 1)
    assert perft(s0, 2) == 423, perft(s0, 2)

    # ---- 6) win by capturing the King -------------------------------------
    s = st({(11, 12): (BLACK, "G"), (6, 0): (BLACK, "K"), (12, 12): (WHITE, "K")})
    n = G.apply_move(s, "11,12>12,12")                     # Gold takes the King
    assert n.winner == BLACK and G.is_terminal(n)
    assert G.returns(n) == [1.0, -1.0]

    # ---- 7) fourfold repetition draw --------------------------------------
    s = st({(0, 0): (BLACK, "G"), (12, 12): (WHITE, "G"),
            (6, 0): (BLACK, "K"), (6, 12): (WHITE, "K")})
    seq = ["0,0>1,0", "12,12>11,12", "1,0>0,0", "11,12>12,12"]
    n = s
    for _ in range(3):
        for m in seq:
            assert not G.is_terminal(n)
            n = G.apply_move(n, m)
    assert G.is_terminal(n) and G.returns(n) == [0.0, 0.0]

    # ---- 8) serialize round-trip + a random game terminates ---------------
    n = G.apply_move(s0, "3,4>3,8")                        # a gun capture
    snap = G.serialize(n)
    assert json.dumps(G.serialize(G.deserialize(snap)), sort_keys=True) == \
        json.dumps(snap, sort_keys=True)
    rng = random.Random(11)
    sx = G.initial_state()
    for _ in range(G.PLY_CAP + 1):
        if G.is_terminal(sx):
            break
        sx = G.apply_move(sx, rng.choice(G.legal_moves(sx)))
    assert G.is_terminal(sx)
    ret = G.returns(sx)
    assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

    print("cashew_shogi selftest: all checks passed")


if __name__ == "__main__":
    main()
