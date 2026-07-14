"""Tenjiku Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Anchors (all sourced from https://en.wikipedia.org/wiki/Tenjiku_shogi):
  * the exact 16x16 / 78-piece / 36-type starting setup (transcribed from the
    Wikipedia setup table; White = the 180-degree rotation);
  * each distinctive piece's move from a central square, frozen from the Betza
    notation / movement diagrams: the four range-jumping Generals (rank order
    King/Prince > Great > Vice > Rook/Bishop; jump strictly-lower when
    capturing, capture any, never pass a king), Fire Demon (Bishop + sideways
    slide + 3-step area move), Lion / Lion Hawk (Lion+Bishop) / Free Eagle
    (Queen + diagonal Lion), Horned Falcon / Soaring Eagle stings, Heavenly
    Tetrarch (skips square 1), Kirin / Phoenix / plain pieces;
  * Fire Demon burning: active burn after moving, passive-priority burn (a piece
    moving next to a Demon is destroyed and the Demon survives), FD-vs-FD (mover
    dies), a Water Buffalo promoting to Fire Demon burns immediately, capturing
    a Demon by landing on it is safe, burning a King wins, own-King suicide loses;
  * DUAL ROYALTY (King + a promoted Drunk Elephant = Prince): capturing one of
    two royals does not win; capturing the last one wins;
  * Lion double-move / igui / out-and-back pass; a promotion example;
  * win by capturing the last royal via apply_move (not a hand-built state);
  * attacked() (forward from the move generator) agrees with a direct capture
    diff over random exotic boards, and reports obvious attacks;
  * self-computed perft 74 / 5540 / 464333 at depths 1-3 (frozen);
  * serialize / deserialize round-trips; random games terminate.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.tenjiku_shogi.game import TenjikuShogi, TenjikuState      # noqa: E402
from agp.shogilike import BLACK, WHITE                               # noqa: E402

G = TenjikuShogi()
Kk = {(0, 0): (BLACK, "K"), (15, 15): (WHITE, "K")}


def st(board, to_move=BLACK, promoted=(), ply=0):
    s = TenjikuState(board=dict(board), promoted=frozenset(promoted),
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


def targets(s, frm="8,8"):
    """Destination cells of simple 2-cell (non-promoting) moves from `frm`."""
    out = set()
    for m in G.legal_moves(s):
        if m.endswith("=+") or m.count(">") != 1:
            continue
        f, t = m.split(">")
        if f == frm:
            out.add(t)
    return out


def solo(letter, sq=(8, 8), to_move=BLACK, promoted=False, extra=()):
    b = dict(Kk)
    b[sq] = (to_move, letter)
    b.update(dict(extra))
    return st(b, to_move=to_move, promoted={sq} if promoted else ())


def main():
    s0 = G.initial_state()

    # ---- 1) setup ----------------------------------------------------------
    assert G.WIDTH == G.HEIGHT == 16 and G.ZONE == 5
    assert len(s0.board) == 156
    for pl in (BLACK, WHITE):
        assert sum(1 for v in s0.board.values() if v[0] == pl) == 78
    counts = {}
    for (pl, t) in s0.board.values():
        counts[(pl, t)] = counts.get((pl, t), 0) + 1
    per_type = {"K": 1, "GG": 1, "VG": 1, "RG": 2, "BG": 2, "FE": 1, "Q": 1,
                "SE": 2, "HF": 2, "WB": 2, "CS": 4, "FD": 2, "LH": 1, "Ln": 1,
                "DK": 2, "DH": 2, "R": 2, "B": 2, "Kr": 1, "Ph": 1, "DE": 1,
                "BT": 2, "FL": 2, "G": 2, "S": 2, "C": 2, "VM": 2, "SM": 2,
                "RC": 2, "VS": 2, "SS": 2, "L": 2, "N": 2, "I": 2, "D": 2,
                "P": 16}
    assert sum(per_type.values()) == 78 and len(per_type) == 36
    for pl in (BLACK, WHITE):
        for t, n in per_type.items():
            assert counts[(pl, t)] == n, (pl, t, counts.get((pl, t)))
    # spot squares (files 16..1 -> col 0..15; Black at the bottom, row 0 = back)
    assert s0.board[(7, 0)] == (BLACK, "K") and s0.board[(8, 0)] == (BLACK, "DE")
    assert s0.board[(6, 1)] == (BLACK, "Kr") and s0.board[(7, 1)] == (BLACK, "Ln")
    assert s0.board[(8, 1)] == (BLACK, "Q") and s0.board[(9, 1)] == (BLACK, "Ph")
    assert s0.board[(6, 2)] == (BLACK, "FD") and s0.board[(9, 2)] == (BLACK, "FD")
    assert s0.board[(7, 2)] == (BLACK, "LH") and s0.board[(8, 2)] == (BLACK, "FE")
    assert s0.board[(7, 3)] == (BLACK, "GG") and s0.board[(8, 3)] == (BLACK, "VG")
    assert s0.board[(5, 3)] == (BLACK, "BG") and s0.board[(6, 3)] == (BLACK, "RG")
    assert s0.board[(4, 5)] == (BLACK, "D") and s0.board[(11, 5)] == (BLACK, "D")
    assert s0.board[(1, 0)] == (BLACK, "N") and s0.board[(0, 0)] == (BLACK, "L")
    assert sum(1 for (c, r), (p, t) in s0.board.items()
               if p == BLACK and t == "P" and r == 4) == 16
    # White = 180 rotation (King & Drunk Elephant swap sides)
    assert s0.board[(8, 15)] == (WHITE, "K") and s0.board[(7, 15)] == (WHITE, "DE")
    assert s0.board[(8, 12)] == (WHITE, "GG") and s0.board[(7, 12)] == (WHITE, "VG")

    # ---- 2) plain colour-relative pieces (spot) -----------------------------
    assert targets(solo("S")) == {"7,9", "9,9", "7,7", "9,7", "8,9"}      # silver FfW
    assert targets(solo("G")) == {"8,9", "8,7", "7,8", "9,8", "7,9", "9,9"}  # gold WfF
    assert targets(solo("C")) == {"7,9", "8,7", "8,9", "9,9"}             # copper fKbW
    assert targets(solo("I")) == {"7,9", "8,9", "9,9"}                    # iron fK
    assert targets(solo("N")) == {"7,10", "9,10"}                         # knight ffN
    assert targets(solo("N", to_move=WHITE)) == {"7,6", "9,6"}            # flips
    assert targets(solo("D")) == {"8,9", "7,7", "9,7"}                    # dog fWbF
    assert targets(solo("BT")) == {"7,7", "7,8", "7,9", "8,7", "9,7", "9,8", "9,9"}
    assert targets(solo("DE")) == {"7,7", "7,8", "7,9", "8,9", "9,7", "9,8", "9,9"}
    assert targets(solo("Kr")) == {"7,9", "9,9", "7,7", "9,7",            # kirin FD
                                   "8,10", "8,6", "10,8", "6,8"}
    assert targets(solo("Ph")) == {"8,9", "8,7", "7,8", "9,8",            # phoenix WA
                                   "10,10", "6,10", "10,6", "6,6"}
    assert targets(solo("D", promoted=True)) == {                        # multi general fRbB
        "8,9", "8,10", "8,11", "8,12", "8,13", "8,14", "8,15",
        "7,7", "6,6", "5,5", "4,4", "3,3", "2,2", "1,1",
        "9,7", "10,6", "11,5", "12,4", "13,3", "14,2", "15,1"}

    # ---- 3) range-jumping Generals' rank order ------------------------------
    # Great General (rank 3): jumps VG/RG/BG/others when capturing; captures but
    # cannot pass a King, Prince, or another Great General.
    s = solo("GG", extra={(8, 9): (BLACK, "VG"), (8, 10): (WHITE, "P")})
    assert "8,8>8,10" in G.legal_moves(s)                # jump own VG, cap P
    s = solo("GG", extra={(8, 9): (WHITE, "GG"), (8, 10): (WHITE, "P")})
    assert "8,8>8,9" in G.legal_moves(s) and "8,8>8,10" not in G.legal_moves(s)
    s = solo("GG", extra={(8, 9): (WHITE, "K"), (8, 11): (WHITE, "P")})
    assert "8,8>8,9" in G.legal_moves(s) and "8,8>8,11" not in G.legal_moves(s)
    # Bishop General (rank 1): jumps only rank-0; may capture but not pass a
    # rank-1 Rook General.
    s = solo("BG", extra={(9, 9): (BLACK, "P"), (10, 10): (WHITE, "P")})
    assert "8,8>10,10" in G.legal_moves(s) and "8,8>9,9" not in G.legal_moves(s)
    s = solo("BG", extra={(9, 9): (WHITE, "RG"), (10, 10): (WHITE, "P")})
    assert "8,8>9,9" in G.legal_moves(s) and "8,8>10,10" not in G.legal_moves(s)
    # Vice General = diagonal range-jump (rank 2) + 3-step area move
    vm = set(moves_from(solo("VG"), "8,8"))
    assert "8,8>11,11" in vm and "8,8>8,11" in vm and "8,8>8,12" not in vm
    assert not any(m.endswith("=+") for m in vm)         # VG never promotes
    # promoted generals become the next rank up
    assert "8,8>8,11" in set(moves_from(solo("BG", promoted=True), "8,8"))   # ->VG (area)
    assert "8,8>8,15" in set(moves_from(solo("RG", promoted=True), "8,8"))   # ->GG (ray)
    assert "8,8>11,11" in set(moves_from(solo("HF", promoted=True), "8,8"))  # ->BG diag
    assert "8,8>8,15" in set(moves_from(solo("SE", promoted=True), "8,8"))   # ->RG ortho

    # ---- 4) Fire Demon slide/area + Lion family + falcon/eagle + tetrarch ----
    fd = targets(solo("FD"))
    assert "11,11" in fd and "0,8" in fd                 # bishop + sideways slide
    assert "8,12" not in [m.split(">")[1] for m in moves_from(solo("FD"), "8,8")]  # no vert slide
    assert "8,11" in fd and "8,12" not in fd             # area move <=3
    lh = set(moves_from(solo("LH"), "8,8"))
    assert "8,8>11,11" in lh and "8,8>8,10" in lh and "8,8>8,9" in lh   # bishop + lion
    fe = set(moves_from(solo("FE"), "8,8"))
    assert "8,8>8,15" in fe and "8,8>11,11" in fe                       # queen rays
    assert "8,8>10,10" in fe and "8,8>8,10" in fe                       # diagonal lion
    fem = set(G.legal_moves(solo("FE", extra={(9, 9): (WHITE, "P"), (10, 10): (WHITE, "S")})))
    assert "8,8>9,9>10,10" in fem and "8,8>9,9>8,8" in fem              # diag double / igui
    hf = set(moves_from(solo("HF"), "8,8"))
    assert "8,8>8,0" in hf and "8,8>8,12" not in hf                     # back slide, no fwd
    assert "8,8>8,9>8,9" in hf and "8,8>8,10" in hf                     # fwd sting / 2-leap
    se = set(moves_from(solo("SE"), "8,8"))
    assert "8,8>8,15" in se and "8,8>11,11" not in se                   # rook, no fwd-diag slide
    assert "8,8>9,9>9,9" in se and "8,8>10,10" in se                    # fwd-diag sting / 2-leap
    tt = targets(solo("CS", promoted=True))
    assert "8,9" not in moves_from(solo("CS", promoted=True), "8,8")    # can't land sq1
    assert "8,10" in tt and "8,15" in tt                               # long from sq2
    assert {"10,8", "11,8"} <= tt and "9,8" not in tt and "12,8" not in tt  # sideways 2-3
    ti = set(G.legal_moves(solo("CS", promoted=True, extra={(9, 9): (WHITE, "P")})))
    assert "8,8>9,9>8,8" in ti                                          # igui

    # ---- 5) Fire Demon burning ----------------------------------------------
    s = solo("FD", extra={(9, 10): (WHITE, "P"), (10, 10): (WHITE, "S")})
    n = G.apply_move(s, "8,8>9,9")
    assert n.board.get((9, 9)) == (BLACK, "FD")
    assert (9, 10) not in n.board and (10, 10) not in n.board           # active burn
    s = st({(8, 8): (WHITE, "FD"), (8, 6): (BLACK, "R"), (9, 7): (WHITE, "P"),
            **Kk}, to_move=BLACK)
    n = G.apply_move(s, "8,6>9,7")                                      # Rook lands by FD
    assert (9, 7) not in n.board and n.board.get((8, 8)) == (WHITE, "FD")  # passive priority
    s = st({(8, 8): (WHITE, "FD"), (8, 6): (BLACK, "FD"), **Kk}, to_move=BLACK)
    n = G.apply_move(s, "8,6>8,7")
    assert (8, 7) not in n.board and n.board.get((8, 8)) == (WHITE, "FD")  # FD vs FD
    s = st({(8, 8): (BLACK, "R"), (8, 11): (WHITE, "FD"), **Kk})
    n = G.apply_move(s, "8,8>8,11")
    assert n.board.get((8, 11)) == (BLACK, "R") and n.winner is None    # safe capture
    s = st({(8, 8): (BLACK, "FD"), (9, 10): (WHITE, "K"), (0, 0): (BLACK, "K")})
    n = G.apply_move(s, "8,8>9,9")
    assert (9, 10) not in n.board and n.winner == BLACK and G.is_terminal(n)
    assert G.returns(n) == [1.0, -1.0]
    s = st({(8, 8): (WHITE, "FD"), (8, 6): (BLACK, "K"), (0, 0): (WHITE, "K")},
           to_move=BLACK)
    n = G.apply_move(s, "8,6>8,7")
    assert (8, 7) not in n.board and n.winner == WHITE                  # own-King suicide
    s = st({(6, 10): (BLACK, "WB"), (7, 12): (WHITE, "P"), **Kk})
    n = G.apply_move(s, "6,10>6,11=+")                                  # WB -> FD, burns
    assert (6, 11) in n.promoted and (7, 12) not in n.board

    # ---- 6) DUAL ROYALTY (King + promoted Drunk Elephant = Prince) ----------
    s = st({(5, 5): (BLACK, "R"), (5, 10): (WHITE, "K"), (9, 9): (WHITE, "DE"),
            (0, 0): (BLACK, "K")}, promoted={(9, 9)})
    n = G.apply_move(s, "5,5>5,10")                                     # capture King only
    assert n.winner is None                                             # Prince survives
    assert any(p == WHITE and t == "DE" for (p, t) in n.board.values())
    s = st({(9, 5): (BLACK, "R"), (9, 9): (WHITE, "DE"), (0, 0): (BLACK, "K")},
           to_move=BLACK, promoted={(9, 9)})
    n = G.apply_move(s, "9,5>9,9")                                      # capture the Prince
    assert n.winner == BLACK and G.is_terminal(n)
    # an UNPROMOTED Drunk Elephant is NOT royal: capturing the King wins outright
    s = st({(5, 5): (BLACK, "R"), (5, 10): (WHITE, "K"), (9, 9): (WHITE, "DE"),
            (0, 0): (BLACK, "K")})
    n = G.apply_move(s, "5,5>5,10")
    assert n.winner == BLACK

    # ---- 7) Lion double-move / igui / pass ----------------------------------
    s = st({(8, 8): (BLACK, "Ln"), (8, 9): (WHITE, "P"), (9, 10): (WHITE, "S"),
            **Kk})
    ms = set(G.legal_moves(s))
    assert "8,8>8,9>9,10" in ms and "8,8>8,9>8,8" in ms and "8,8>7,7>8,8" in ms
    n = G.apply_move(s, "8,8>8,9>9,10")
    assert n.board.get((9, 10)) == (BLACK, "Ln") and (8, 9) not in n.board
    n = G.apply_move(s, "8,8>7,7>8,8")                                  # pass
    assert n.board == s.board and n.to_move == WHITE

    # ---- 8) promotion (zone = far FIVE ranks: rows 11-15 for Black) ----------
    s = st({(3, 10): (BLACK, "S"), **Kk})
    ms = set(G.legal_moves(s))
    assert "3,10>3,11" in ms and "3,10>3,11=+" in ms                    # entering the zone
    s = st({(3, 9): (BLACK, "S"), **Kk})
    assert "3,9>3,10=+" not in set(G.legal_moves(s))                    # row 10 not in zone
    s = st({(3, 11): (BLACK, "S"), **Kk})
    ms = set(G.legal_moves(s))
    assert "3,11>3,12" in ms and "3,11>3,12=+" not in ms                # quiet inside: no
    s = st({(3, 11): (BLACK, "S"), (2, 12): (WHITE, "P"), **Kk})
    assert "3,11>2,12=+" in set(G.legal_moves(s))                       # capture from inside
    for L in ("K", "GG", "VG", "FE", "LH", "FD"):                       # never promote
        s = st({(3, 11): (BLACK, L), **Kk})
        assert not any(m.endswith("=+") for m in G.legal_moves(s)), L

    # ---- 9) win by capturing the King via apply_move ------------------------
    s = st({(6, 5): (BLACK, "R"), (6, 15): (WHITE, "K"), (0, 0): (BLACK, "K"),
            (1, 1): (WHITE, "P")})
    n = G.apply_move(s, "6,5>6,15")
    assert n.winner == BLACK and G.is_terminal(n) and G.returns(n) == [1.0, -1.0]

    # ---- 10) attacked() forward-consistency ---------------------------------
    s = st({(4, 4): (BLACK, "R"), (4, 12): (WHITE, "P"), **Kk})
    assert G.attacked(s, (4, 12), BLACK) and not G.attacked(s, (15, 15), BLACK)
    s = st({(4, 4): (BLACK, "Ln"), (6, 6): (WHITE, "P"), **Kk})
    assert G.attacked(s, (6, 6), BLACK)
    s = st({(8, 8): (BLACK, "FD"), (9, 10): (WHITE, "P"), **Kk})
    assert G.attacked(s, (9, 10), BLACK)                                # FD can burn
    letters = ["P", "S", "G", "R", "B", "Ln", "BG", "RG", "GG", "VG", "FD",
               "Q", "FE", "LH", "HF", "SE", "CS", "WB", "N", "Kr"]
    rng = random.Random(23)
    for _ in range(24):
        b = dict(Kk)
        for _ in range(rng.randint(3, 8)):
            c, r = rng.randint(0, 15), rng.randint(0, 15)
            if (c, r) in b:
                continue
            b[(c, r)] = (rng.randint(0, 1), rng.choice(letters))
        by = rng.randint(0, 1)
        s = st(b, to_move=by, promoted={sq for sq in b if rng.random() < 0.2
                                        and b[sq][1] not in ("K", "FD", "VG", "GG", "FE", "LH")})
        att = G.attacked_squares(s, by)
        enemy = 1 - by
        victims = {sq for sq, (p, t) in s.board.items() if p == enemy}
        direct = set()
        for m in G._moves(s):
            nb = G.apply_move(s, m).board
            direct |= {sq for sq in victims if nb.get(sq) != s.board[sq]}
        assert att == direct

    # ---- 11) perft (self-computed, frozen) ----------------------------------
    ms0 = G.legal_moves(s0)
    assert len(ms0) == len(set(ms0)), "duplicate move strings at the root"
    assert perft(s0, 1) == 74, perft(s0, 1)
    assert perft(s0, 2) == 5540, perft(s0, 2)
    assert perft(s0, 3) == 464333, perft(s0, 3)

    # ---- 12) serialize round-trip + random games terminate ------------------
    n = G.apply_move(s0, "6,3>6,9")                    # a Rook General march
    snap = G.serialize(n)
    assert json.dumps(G.serialize(G.deserialize(snap)), sort_keys=True) == \
        json.dumps(snap, sort_keys=True)
    for seed in (1, 4):
        rng = random.Random(seed)
        sx = G.initial_state()
        for _ in range(G.PLY_CAP + 1):
            if G.is_terminal(sx):
                break
            sx = G.apply_move(sx, rng.choice(G.legal_moves(sx)))
        assert G.is_terminal(sx)
        ret = G.returns(sx)
        assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

    print("tenjiku_shogi selftest: all checks passed")


if __name__ == "__main__":
    main()
