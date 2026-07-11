"""Chu Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Anchors:
  * the exact 12x12 / 46-piece / 21-type starting setup (verified against the
    Wikipedia setup diagram; White = 180-degree rotation of Black);
  * opening perft 36 / 1296 / 48819 at depths 1-3. The 36 root moves were
    verified piece-by-piece by hand AND against HaChu's root move list
    (one-time differential; HaChu is the reference engine for the Wikipedia
    ruleset);
  * Lion mechanics: 5x5 direct leaps, adjacent-step encoding f>m>m, double
    capture f>m>t, igui f>m>f, and the jitto turn pass (only via an empty
    adjacent square);
  * the Lion-trading rules, reconstructing Wikipedia's worked examples:
    I (adjacent LnxLn always legal), II (protected non-adjacent LnxLn banned
    both ways, BxLn fine), III (X-ray "hidden protector" bans the capture),
    IV (LnxPxLn banned when taking the pawn opens the recapture line, while
    the plain leap past the pawn is legal), V (capturing the protecting pawn
    together with the Lion is LEGAL under the post-move/CVP reading -- the
    JCSA reads this position as illegal; documented in rules.md), and the
    tsukegui exception (a substantial extra capture legalises the trade);
  * the counterstrike rule: after a non-Lion captures a Lion, a non-Lion may
    not capture a Lion on another square for one turn (a Lion may; the fresh
    Lion made by a Kirin promoting while capturing MAY be taken on that same
    square); the flag expires after one move;
  * Horned Falcon / Soaring Eagle Lion powers restricted to their forward
    ray(s): step, jump-2, double capture, igui, pass;
  * promotion: optional on entering the zone (far 4 ranks), inside the zone
    only on a capture (either end in the zone), no promotion on wholly-inside
    quiet moves, the Pawn's extra last-rank chance (declinable -> dead pawn),
    and no re-promotion of promoted pieces;
  * win by capturing ALL royals via apply_move: King captured with a Prince
    still alive -> game continues; capturing the last royal -> winner;
  * fourfold repetition -> an honest draw; a random game terminates.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.chu_shogi.game import ChuShogi, ChuState                 # noqa: E402
from agp.shogilike import BLACK, WHITE                              # noqa: E402

G = ChuShogi()


def st(board, to_move=BLACK, promoted=(), counter=(), ply=0):
    s = ChuState(board=dict(board), promoted=frozenset(promoted),
                 hands={BLACK: {}, WHITE: {}}, to_move=to_move,
                 ply=ply, counter=tuple(counter))
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


def main():
    s0 = G.initial_state()

    # ---- 1) setup ---------------------------------------------------------
    assert G.WIDTH == G.HEIGHT == 12 and G.ZONE == 4
    assert len(s0.board) == 92
    for pl in (BLACK, WHITE):
        assert sum(1 for v in s0.board.values() if v[0] == pl) == 46
    counts = {}
    for (pl, t) in s0.board.values():
        counts[(pl, t)] = counts.get((pl, t), 0) + 1
    per_type = {"K": 1, "E": 1, "Q": 1, "N": 1, "O": 1, "X": 1, "G": 2, "S": 2,
                "C": 2, "F": 2, "T": 2, "L": 2, "A": 2, "B": 2, "R": 2, "H": 2,
                "D": 2, "V": 2, "M": 2, "I": 2, "P": 12}
    assert sum(per_type.values()) == 46 and len(per_type) == 21
    for pl in (BLACK, WHITE):
        for t, n in per_type.items():
            assert counts[(pl, t)] == n, (pl, t, counts.get((pl, t)))
    # spot squares from the Wikipedia diagram (Black bottom, col 0 = file 12)
    assert s0.board[(5, 0)] == (BLACK, "K") and s0.board[(6, 0)] == (BLACK, "E")
    assert s0.board[(5, 2)] == (BLACK, "N") and s0.board[(6, 2)] == (BLACK, "Q")
    assert s0.board[(5, 1)] == (BLACK, "O") and s0.board[(6, 1)] == (BLACK, "X")
    assert s0.board[(6, 11)] == (WHITE, "K") and s0.board[(5, 11)] == (WHITE, "E")
    assert s0.board[(6, 9)] == (WHITE, "N") and s0.board[(5, 9)] == (WHITE, "Q")
    assert s0.board[(3, 4)] == (BLACK, "I") and s0.board[(8, 7)] == (WHITE, "I")

    # ---- 2) opening perft --------------------------------------------------
    ms0 = G.legal_moves(s0)
    assert len(ms0) == len(set(ms0)), "duplicate move strings"
    assert perft(s0, 1) == 36, perft(s0, 1)
    assert perft(s0, 2) == 1296
    assert perft(s0, 3) == 48819
    # the Lion's five opening moves (leaps only; every adjacent square is own)
    assert moves_from(s0, "5,2") == ["5,2>3,1", "5,2>4,4", "5,2>5,4", "5,2>6,4",
                                     "5,2>7,4"]

    # ---- 3) Lion mechanics --------------------------------------------------
    # lone Lion: 24 leap/step destinations + 8 passes
    s = st({(5, 5): (BLACK, "N"), (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    lion = set(moves_from(s, "5,5"))
    assert len([m for m in lion if m.count(">") == 1]) == 16          # dist-2 leaps
    assert len([m for m in lion if m.count(">") == 2 and
                m.split(">")[1] == m.split(">")[2]]) == 8             # steps f>m>m
    assert len([m for m in lion if m.split(">")[0] == m.split(">")[-1] !=
                m.split(">")[1]]) == 8                                # passes f>m>f
    # double capture, igui and pass against two adjacent enemies
    s = st({(5, 5): (BLACK, "N"), (5, 6): (WHITE, "P"), (6, 7): (WHITE, "S"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    ms = set(G.legal_moves(s))
    assert "5,5>5,6>6,7" in ms                        # double capture P then S
    assert "5,5>5,6>5,5" in ms                        # igui: capture P in place
    assert "5,5>4,4>5,5" in ms                        # jitto via an empty square
    n2 = G.apply_move(s, "5,5>5,6>6,7")
    assert n2.board[(6, 7)] == (BLACK, "N") and (5, 6) not in n2.board
    n3 = G.apply_move(s, "5,5>5,6>5,5")
    assert n3.board[(5, 5)] == (BLACK, "N") and (5, 6) not in n3.board
    n4 = G.apply_move(s, "5,5>4,4>5,5")               # pass: board unchanged
    assert n4.board == s.board and n4.to_move == WHITE
    # a Lion completely boxed in by friends has no pass (initial position)
    assert not any(m.split(">")[0] == "5,2" and m.split(">")[0] == m.split(">")[-1]
                   for m in ms0)

    # ---- 4) Lion-trading rule 1 (Wikipedia examples) ------------------------
    # Ex I: ADJACENT LnxLn is always legal, protection irrelevant; may even
    # take the protector as the second bite.
    s = st({(2, 2): (BLACK, "N"), (3, 3): (WHITE, "N"), (4, 4): (WHITE, "G"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    ms = set(G.legal_moves(s))
    assert "2,2>3,3>3,3" in ms and "2,2>3,3>4,4" in ms
    # Ex II: both Lions protected, distance 2: no LnxLn either way; BxLn fine.
    s = st({(4, 4): (BLACK, "N"), (3, 3): (BLACK, "S"), (1, 3): (BLACK, "B"),
            (4, 6): (WHITE, "N"), (4, 8): (WHITE, "L"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    assert "4,4>4,6" not in G.legal_moves(s)
    assert "1,3>4,6" in G.legal_moves(s)              # BxLn is unrestricted
    sw = st(dict(s.board), to_move=WHITE)
    assert "4,6>4,4" not in G.legal_moves(sw)
    # Ex III: X-ray hidden protector through the capturer's vacated square.
    s = st({(4, 4): (BLACK, "N"), (2, 2): (WHITE, "N"), (6, 6): (WHITE, "B"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    assert "4,4>2,2" not in G.legal_moves(s)
    del s.board[(6, 6)]
    s = st(dict(s.board))
    assert "4,4>2,2" in G.legal_moves(s)              # unprotected -> legal
    # Ex IV: LnxPxLn illegal when eating the pawn opens the recapture line,
    # but leaping straight at the Lion (pawn keeps blocking) is legal.
    s = st({(4, 4): (BLACK, "N"), (5, 5): (WHITE, "P"), (6, 6): (WHITE, "N"),
            (3, 3): (WHITE, "B"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    ms = set(G.legal_moves(s))
    assert "4,4>5,5>6,6" not in ms
    assert "4,4>6,6" in ms
    # Ex V: Lion protected only by a pawn that is captured en route: legal
    # under the post-move (CVP/Wikipedia rule-as-stated) reading.
    s = st({(4, 6): (BLACK, "N"), (4, 5): (WHITE, "P"), (4, 4): (WHITE, "N"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    ms = set(G.legal_moves(s))
    assert "4,6>4,5>4,4" in ms                        # eat protector, then Lion
    assert "4,6>4,4" not in ms                        # plain leap: recapturable
    # tsukegui: a substantial (non-pawn/GB) extra capture legalises the trade
    # even though the Lion stays recapturable...
    s = st({(4, 6): (BLACK, "N"), (4, 5): (WHITE, "S"), (4, 4): (WHITE, "N"),
            (0, 4): (WHITE, "D"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    assert "4,6>4,5>4,4" in G.legal_moves(s)
    # ...but a pawn extra capture does not (Dragon King still guards).
    s = st({(4, 6): (BLACK, "N"), (4, 5): (WHITE, "P"), (4, 4): (WHITE, "N"),
            (0, 4): (WHITE, "D"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")})
    assert "4,6>4,5>4,4" not in G.legal_moves(s)
    # a promoted Kirin is a Lion for these rules (protected, distance 2)
    s = st({(4, 4): (BLACK, "N"), (4, 6): (WHITE, "O"), (4, 8): (WHITE, "L"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")},
           promoted={(4, 6)})
    assert "4,4>4,6" not in G.legal_moves(s)

    # ---- 5) counterstrike (rule 2) ------------------------------------------
    base = {(0, 0): (BLACK, "R"), (0, 5): (WHITE, "N"), (5, 5): (BLACK, "N"),
            (5, 11): (WHITE, "R"), (6, 6): (WHITE, "N"), (11, 0): (BLACK, "K"),
            (11, 11): (WHITE, "K")}
    s = st(base)
    n = G.apply_move(s, "0,0>0,5")                     # non-Lion takes a Lion
    assert n.counter == ((0, 5),)
    wm = set(G.legal_moves(n))
    assert "5,11>5,5" not in wm                        # RxLn elsewhere: banned
    assert "6,6>5,5>5,5" in wm                         # LnxLn (adjacent): fine
    n2 = G.apply_move(n, "11,11>11,10")                # any quiet reply
    assert n2.counter == ()
    n3 = G.apply_move(n2, "11,0>10,0")                 # Black quiet move
    assert "5,11>5,5" in G.legal_moves(n3)             # ban lasted one turn only
    # Kirin promoting to Lion while capturing one: recapture on THAT square ok
    s = st({(3, 3): (WHITE, "O"), (2, 2): (BLACK, "N"), (2, 9): (BLACK, "R"),
            (9, 9): (WHITE, "N"), (9, 0): (BLACK, "R"),
            (11, 0): (BLACK, "K"), (11, 11): (WHITE, "K")}, to_move=WHITE)
    n = G.apply_move(s, "3,3>2,2=+")                   # Kirin x Lion, promotes
    assert n.counter == ((2, 2),)
    assert n.board[(2, 2)] == (WHITE, "O") and (2, 2) in n.promoted
    bm = set(G.legal_moves(n))
    assert "2,9>2,2" in bm                             # shooting the fresh Lion
    assert "9,0>9,9" not in bm                         # another Lion: banned

    # ---- 6) Falcon / Eagle Lion powers ---------------------------------------
    s = st({(5, 5): (BLACK, "H"), (5, 6): (WHITE, "P"), (5, 7): (WHITE, "S"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")}, promoted={(5, 5)})
    ms = set(G.legal_moves(s))
    assert "5,5>5,6>5,6" in ms                         # forward capture-step
    assert "5,5>5,6>5,5" in ms                         # igui
    assert "5,5>5,7" in ms                             # jump over the pawn
    assert "5,5>5,6>5,7" in ms                         # double capture P then S
    assert "5,5>5,6" not in ms                         # no plain forward slide
    assert not any(m.startswith("5,5>4,6>") or m.startswith("5,5>6,6>")
                   for m in ms)                        # power is forward-only
    # pass needs the front square EMPTY
    s2 = st({(5, 5): (BLACK, "H"), (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")},
            promoted={(5, 5)})
    assert "5,5>5,6>5,5" in G.legal_moves(s2)
    # Soaring Eagle: powers on BOTH forward diagonals, slides elsewhere
    s = st({(5, 5): (BLACK, "D"), (4, 6): (WHITE, "P"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")}, promoted={(5, 5)})
    ms = set(G.legal_moves(s))
    assert "5,5>4,6>3,7" in ms and "5,5>4,6>5,5" in ms and "5,5>3,7" in ms
    assert "5,5>6,6>6,6" in ms and "5,5>6,6>5,5" in ms and "5,5>7,7" in ms
    assert "5,5>4,6" not in ms                         # fwd-diag is power-only
    assert "5,5>5,6" in ms                             # straight fwd = slide
    # a Falcon igui-capturing a Lion triggers the counterstrike flag
    s = st({(5, 5): (BLACK, "H"), (5, 6): (WHITE, "N"),
            (0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")}, promoted={(5, 5)})
    n = G.apply_move(s, "5,5>5,6>5,5")
    assert n.counter == ((5, 6),) and (5, 6) not in n.board

    # ---- 7) promotion ---------------------------------------------------------
    Kk = {(0, 0): (BLACK, "K"), (11, 11): (WHITE, "K")}
    s = st({(3, 7): (BLACK, "S"), **Kk})
    ms = set(G.legal_moves(s))
    assert "3,7>3,8" in ms and "3,7>3,8=+" in ms       # entering the zone
    s = st({(3, 8): (BLACK, "S"), **Kk})
    ms = set(G.legal_moves(s))
    assert "3,8>3,9" in ms and "3,8>3,9=+" not in ms   # quiet inside: no promo
    assert "3,8>2,7" in ms and "3,8>2,7=+" not in ms   # quiet exit: no promo
    s = st({(3, 8): (BLACK, "S"), (2, 9): (WHITE, "P"), **Kk})
    assert "3,8>2,9=+" in set(G.legal_moves(s))        # capture inside zone
    s = st({(3, 8): (BLACK, "S"), (2, 7): (WHITE, "P"), **Kk})
    assert "3,8>2,7=+" in set(G.legal_moves(s))        # capture LEAVING zone
    s = st({(3, 6): (BLACK, "S"), (2, 7): (WHITE, "P"), **Kk})
    assert "3,6>2,7=+" not in set(G.legal_moves(s))    # capture outside: no
    # pawn: no promo on a quiet inside move, but an extra last-rank chance
    s = st({(5, 9): (BLACK, "P"), **Kk})
    ms = set(G.legal_moves(s))
    assert "5,9>5,10" in ms and "5,9>5,10=+" not in ms
    s = st({(5, 10): (BLACK, "P"), **Kk})
    ms = set(G.legal_moves(s))
    assert "5,10>5,11" in ms and "5,10>5,11=+" in ms
    dead = G.apply_move(s, "5,10>5,11")                # declined: a dead pawn
    dead2 = ChuState(board=dead.board, promoted=dead.promoted, hands=dead.hands,
                     to_move=BLACK, ply=dead.ply, reps=dead.reps,
                     counter=dead.counter)
    dead2.key = G._poskey(dead2)
    assert moves_from(dead2, "5,11") == []
    # promoted pieces never promote again (+G moves as a Rook, no =+ offered)
    s = st({(5, 8): (BLACK, "G"), (5, 9): (WHITE, "P"), **Kk}, promoted={(5, 8)})
    ms = moves_from(s, "5,8")
    assert "5,8>5,9" in ms and "5,8>5,9=+" not in ms
    assert "5,8>5,0" in ms                             # rook slide all the way
    # K / Q / N never promote
    s = st({(5, 7): (BLACK, "Q"), (6, 7): (BLACK, "N"), (7, 7): (BLACK, "K"),
            **Kk})
    assert not any(m.endswith("=+") for m in G.legal_moves(s))

    # ---- 8) win by capturing all royals ---------------------------------------
    b = {(5, 0): (BLACK, "K"), (6, 5): (BLACK, "Q"),
         (6, 11): (WHITE, "K"), (5, 10): (WHITE, "E"), (0, 8): (WHITE, "P")}
    s = st(b, promoted={(5, 10)})                      # promoted DE = Prince
    n = G.apply_move(s, "6,5>6,11")                    # Queen takes the King...
    assert n.winner is None and not G.is_terminal(n)   # ...Prince still reigns
    n = G.apply_move(n, "0,8>0,7")
    n = G.apply_move(n, "6,11>5,10")                   # Queen takes the Prince
    assert n.winner == BLACK and G.is_terminal(n)
    assert G.returns(n) == [1.0, -1.0]
    # unpromoted Drunk Elephant is NOT royal
    s = st({(5, 0): (BLACK, "K"), (6, 5): (BLACK, "Q"),
            (6, 11): (WHITE, "K"), (5, 10): (WHITE, "E"), (0, 8): (WHITE, "P")})
    n = G.apply_move(s, "6,5>6,11")
    assert n.winner == BLACK and G.is_terminal(n)

    # ---- 9) fourfold repetition draw ------------------------------------------
    s = st({(0, 0): (BLACK, "G"), (11, 11): (WHITE, "G"),
            (5, 0): (BLACK, "K"), (6, 11): (WHITE, "K")})
    seq = ["0,0>1,0", "11,11>10,11", "1,0>0,0", "10,11>11,11"]
    n = s
    for _ in range(3):
        for m in seq:
            assert not G.is_terminal(n)
            n = G.apply_move(n, m)
    assert G.is_terminal(n) and G.returns(n) == [0.0, 0.0]

    # ---- 10) serialize round-trip + a random game terminates -------------------
    import json
    n = G.apply_move(s0, "5,2>5,4")                    # Lion out
    snap = G.serialize(n)
    assert json.dumps(G.serialize(G.deserialize(snap)), sort_keys=True) == \
        json.dumps(snap, sort_keys=True)
    rng = random.Random(42)
    sx = G.initial_state()
    for i in range(G.PLY_CAP + 1):
        if G.is_terminal(sx):
            break
        sx = G.apply_move(sx, rng.choice(G.legal_moves(sx)))
    assert G.is_terminal(sx)
    ret = G.returns(sx)
    assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

    print("chu_shogi selftest: all checks passed")


if __name__ == "__main__":
    main()
