"""Shogun Chess correctness anchor (pure stdlib -- imports only agp + this game).

Every perft number and every rule fact below was verified against pyffish
(Fairy-Stockfish, variant [shogun:crazyhouse] from variants.ini) with the
project .venv, then frozen here as the regression anchor. The one-time
differential (see the build report) compared the FULL legal-move set at
21,325 positions over 120 random games (3,691 drops, 1,103 promotions
played; terminal results and pockets agreed; 0 mismatches), plus
perft(1..4) from the start = 20 / 400 / 8,978 / 200,537.

Anchored rules: shogi-style optional promotion on moves into/out of the far
three ranks (P->C, N->G, B->A, R->M, F->Q); at most one G/A/M/Q on board per
side; mandatory pawn promotion on the last rank; no promotion on an
en-passant capture; captured pieces demote into the capturer's hand; drops
only on the dropper's first five ranks (first rank allowed, even for pawns);
drop mate is legal; repetition draw; playout termination; the 50-move
counter resets on drops AND promotions (Fairy-Stockfish PIECE_PROMOTION).
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # engine/ for `agp`
from games.shogun_chess.game import ShogunChess  # noqa: E402

G = ShogunChess()


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


def play(state, moves):
    for m in moves:
        state = G.apply_move(state, m)
    return state


def pos(board, to_move=0, castling="", hands=None, ep=None):
    """Build a test state via deserialize. board = {'c,r': [player, letter]}."""
    return G.deserialize({
        "board": board, "to_move": to_move, "castling": castling, "ep": ep,
        "halfmove": 0, "ply": 0, "reps": {},
        "hands": hands or {"0": {}, "1": {}}, "promoted": [],
    })


def main():
    # 1) Initial array: standard chess setup (the queen IS the promoted duchess,
    #    encoded directly as Q) and the standard 20 opening moves.
    s0 = G.initial_state()
    assert s0.board[(3, 0)] == (0, "Q") and s0.board[(3, 7)] == (1, "Q")
    assert s0.board[(4, 0)] == (0, "K") and s0.hands == {0: {}, 1: {}}
    assert len(G.legal_moves(s0)) == 20

    # 2) Start perft (pyffish-verified). Depth 3 EXCEEDS chess's 8,902 because
    #    Bf1-a6/Bc1-a3-type moves into the zone add optional "=A" promotions.
    for d, want in {1: 20, 2: 400, 3: 8978}.items():
        got = perft(s0, d)
        assert got == want, f"start perft d{d}: {got} != {want}"

    # 3) Mid-game perft with pockets: 1.e4 d5 2.exd5 Qxd5 (each side holds a
    #    pawn; counts include drops). pyffish-verified (d3 = 155,856 also
    #    matched; omitted here for speed).
    mid = play(s0, ["4,1>4,3", "3,6>3,4", "4,3>3,4", "3,7>3,4"])
    assert mid.hands == {0: {"P": 1}, 1: {"P": 1}}, mid.hands
    for d, want in {1: 54, 2: 3802}.items():
        got = perft(mid, d)
        assert got == want, f"mid perft d{d}: {got} != {want}"

    # 4) Deeper frozen line (20 plies of a seeded game): pockets N vs P, an
    #    archbishop promotion available. pyffish-verified.
    line2 = ["4,1>4,2", "1,7>2,5", "3,1>3,2", "2,5>1,3", "0,1>0,3", "0,7>1,7",
             "4,2>4,3", "7,6>7,4", "2,0>3,1", "5,6>5,4", "1,0>0,2", "5,4>4,3",
             "3,1>1,3", "6,7>7,5", "0,0>0,1", "2,6>2,4", "1,3>3,1", "2,4>2,3",
             "3,0>1,0", "7,7>7,6"]
    mid2 = play(s0, line2)
    assert mid2.hands == {0: {"N": 1}, 1: {"P": 1}}, mid2.hands
    assert "3,1>7,5=A" in G.legal_moves(mid2)      # bishop d2xh6 promoting
    for d, want in {1: 56, 2: 2912}.items():
        got = perft(mid2, d)
        assert got == want, f"mid2 perft d{d}: {got} != {want}"

    # 5) Promotion map + into/out-of-zone rule, per piece (white zone = rows
    #    5..7). A move promotes iff its FROM or TO square is in the zone.
    base = {"4,0": [0, "K"], "4,7": [1, "K"]}
    cases = [("B", "0,4", "1,5", "A"),   # bishop a5-b6: INTO the zone
             ("B", "0,5", "1,4", "A"),   # bishop a6-b5: OUT of the zone
             ("N", "3,4", "4,6", "G"),   # knight d5-e7: into
             ("R", "0,5", "0,1", "M"),   # rook a6-a2: out
             ("F", "3,4", "4,5", "Q")]   # duchess d5-e6: into
    for L, frm, to, pro in cases:
        st = pos({**base, frm: [0, L]})
        mv = f"{frm.replace(',', ',')}>{to}"
        ms = G.legal_moves(st)
        assert mv in ms and mv + "=" + pro in ms, (L, ms)
        nxt = G.apply_move(st, mv + "=" + pro)
        tc, tr = map(int, to.split(","))
        assert nxt.board[(tc, tr)] == (0, pro)
    # out-of-zone move: no promotion offered
    st = pos({**base, "0,3": [0, "B"]})
    assert "0,3>1,4=A" not in G.legal_moves(st) and "0,3>1,4" in G.legal_moves(st)

    # 6) promotionLimit: only one of each major (G/A/M/Q) per side. With an own
    #    archbishop on the board the bishop may still move into the zone but
    #    cannot promote; the (unlimited) Captain is exempt.
    st = pos({**base, "0,4": [0, "B"], "7,0": [0, "A"]})
    ms = G.legal_moves(st)
    assert "0,4>1,5" in ms and "0,4>1,5=A" not in ms
    st = pos({**base, "0,4": [0, "P"], "7,4": [0, "C"]})
    ms = G.legal_moves(st)
    assert "0,4>0,5=C" in ms                        # second captain is fine
    # The queen counts: at the start the duchess-to-queen promotion is blocked
    # until your queen is off the board.
    st = pos({**base, "3,4": [0, "F"], "0,0": [0, "Q"]})
    assert "3,4>4,5=Q" not in G.legal_moves(st)
    st = pos({**base, "3,4": [0, "F"]})
    assert "3,4>4,5=Q" in G.legal_moves(st)

    # 7) Mandatory promotion on the last rank (an unpromoted pawn there could
    #    never move -- Fairy-Stockfish's immobilityIllegal).
    st = pos({**base, "0,6": [0, "P"]})
    ms = G.legal_moves(st)
    assert "0,6>0,7=C" in ms and "0,6>0,7" not in ms

    # 8) En-passant capture may NOT promote, even though it lands in the zone
    #    (white pawn e5, black d7-d5, exd6 e.p. -- d6 = row 5 is in the zone).
    st = pos({**base, "4,4": [0, "P"], "3,6": [1, "P"]}, to_move=1)
    st = G.apply_move(st, "3,6>3,4")
    ms = G.legal_moves(st)
    assert "4,4>3,5" in ms and "4,4>3,5=C" not in ms, ms
    nxt = G.apply_move(st, "4,4>3,5")
    assert (3, 4) not in nxt.board and nxt.hands[0] == {"P": 1}
    # ...but an ordinary capture into the zone does promote:
    st = pos({**base, "4,4": [0, "P"], "3,5": [1, "N"]})
    assert "4,4>3,5=C" in G.legal_moves(st)

    # 9) Demotion into hand: capturing a promoted piece banks its BASE type
    #    (Q->F, C->P); capturing a base piece banks it unchanged.
    st = pos({**base, "3,3": [0, "R"], "3,6": [1, "Q"]})
    assert play(st, ["3,3>3,6"]).hands[0] == {"F": 1}
    st = pos({**base, "3,3": [0, "R"], "3,6": [1, "C"]})
    assert play(st, ["3,3>3,6"]).hands[0] == {"P": 1}
    st = pos({**base, "3,3": [0, "R"], "3,6": [1, "N"]})
    assert play(st, ["3,3>3,6"]).hands[0] == {"N": 1}

    # 10) Drop zone: your first five ranks only -- first rank INCLUDED, even
    #     for pawns (unlike crazyhouse); never the promotion zone.
    st = pos(base, hands={"0": {"P": 1, "N": 1}, "1": {"P": 1}})
    rows = {int(m.split("@")[1].split(",")[1]) for m in G.legal_moves(st) if "@" in m}
    assert rows == {0, 1, 2, 3, 4}, rows
    assert "P@1,0" in G.legal_moves(st)
    st = pos(base, to_move=1, hands={"0": {}, "1": {"P": 1}})
    rows = {int(m.split("@")[1].split(",")[1]) for m in G.legal_moves(st) if "@" in m}
    assert rows == {3, 4, 5, 6, 7}, rows
    # A pawn dropped on the first rank single-steps (no double step from row 0);
    # from the normal second rank the double step is available.
    st = pos({**base, "1,0": [0, "P"]})
    ms = [m for m in G.legal_moves(st) if m.startswith("1,0>")]
    assert ms == ["1,0>1,1"], ms
    st = pos({**base, "1,1": [0, "P"]})
    ms = {m for m in G.legal_moves(st) if m.startswith("1,1>")}
    assert ms == {"1,1>1,2", "1,1>1,3"}, ms

    # 11) Drop mate is legal (no shogi drop-mate restriction), reached via
    #     apply_move: P@g3 mates the black king on h4.
    st = pos({"7,1": [0, "K"], "6,7": [0, "R"], "5,5": [0, "N"],
              "7,3": [1, "K"]}, hands={"0": {"P": 1}, "1": {}})
    assert "P@6,2" in G.legal_moves(st)
    end = G.apply_move(st, "P@6,2")
    assert G.is_terminal(end) and G.returns(end) == [1.0, -1.0]

    # 12) Checkmate via ordinary play: the fool's-mate analogue (the "queen"
    #     -- a promoted duchess -- mates on h4 exactly as in chess).
    end = play(s0, ["5,1>5,2", "4,6>4,4", "6,1>6,3", "3,7>7,3"])
    assert G.is_terminal(end) and G.returns(end) == [-1.0, 1.0]
    assert G.in_check(end.board, 0)

    # 13) Threefold repetition is a draw (knight shuffle; the start position
    #     occurs for the third time).
    shuffle = ["1,0>2,2", "1,7>2,5", "2,2>1,0", "2,5>1,7"] * 2
    end = play(s0, shuffle)
    assert G.is_terminal(end) and G.returns(end) == [0.0, 0.0]

    # 14) Castling survives the overrides (kingside squares cleared).
    st = pos({"0,0": [0, "R"], "4,0": [0, "K"], "7,0": [0, "R"],
              "4,7": [1, "K"]}, castling="KQ")
    ms = G.legal_moves(st)
    assert "4,0>6,0" in ms and "4,0>2,0" in ms
    st = pos({"0,0": [0, "R"], "4,0": [0, "K"], "7,0": [0, "R"],
              "4,7": [1, "K"]}, castling="")
    assert "4,0>6,0" not in G.legal_moves(st)

    # 14b) 50-move counter: a promotion resets it (pyffish-verified: FSF
    #      resets rule50 on irreversible PIECE_PROMOTIONs and on every drop);
    #      a plain piece move increments it.
    st = pos({**base, "0,4": [0, "B"], "3,3": [0, "N"]},
             hands={"0": {"P": 1}, "1": {}})
    assert G.apply_move(st, "3,3>4,5").halfmove == 1      # plain knight move
    assert G.apply_move(st, "0,4>1,5=A").halfmove == 0    # promotion
    assert G.apply_move(st, "P@3,0").halfmove == 0        # drop

    # 15) Serialize round-trip keeps hands + board.
    d = G.serialize(mid2)
    rt = G.deserialize(d)
    assert rt.board == mid2.board and rt.hands == mid2.hands

    # 16) Random playouts terminate (draw backstops: 50-move, repetition,
    #     ply cap) and render() always carries the reserve trays.
    for seed in (1, 2):
        rng = random.Random(seed)
        st = G.initial_state()
        for _ in range(G.PLY_CAP + 1):
            if G.is_terminal(st):
                break
            st = G.apply_move(st, rng.choice(G.legal_moves(st)))
        assert G.is_terminal(st)
        spec = G.render(st)
        assert "reserve" in spec and all(len(p["label"]) <= 2 for p in spec["pieces"])

    print("shogun_chess selftest: all checks passed")


if __name__ == "__main__":
    main()
