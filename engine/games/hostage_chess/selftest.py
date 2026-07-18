"""Hostage Chess correctness anchor (pure stdlib -- imports only agp + this game).

No engine oracle exists (pyffish has no hostage variant and the exchange
mechanic is not expressible in a Fairy-Stockfish variants.ini), so the anchors
are:

1. Start perft 1-4 == orthodox chess (20/400/8902/197281). Justified: the first
   capture in chess occurs at ply 3 and the first MUTUAL capture at ply 4, so
   within 4 plies no prison pair is ever populated => no exchange, no airfield
   drop, no promotion (only pawns get captured by ply 4) and no dynamic
   7th-rank-pawn effect. Hostage Chess is therefore move-for-move identical to
   orthodox chess to depth 4.
2. The worked examples from Wikipedia "Hostage chess" (Pritchard, Variant Chess
   32): the Fried Liver refutation 9.(N-B)B*f7+ and the promotion-availability
   self-check rule.
3. Constructed positions for every special rule: exchange values (Q>R>B=N>P),
   airfield transfer, pawn-drop rank limits, dropped-pawn double step / no
   immediate e.p., castling with a dropped rook, promotion from the opponent's
   prison, drop checkmate, threefold repetition.
4. A conservation invariant over random games: the 32 men (and each type count)
   are conserved forever across board + airfields + prisons + pending.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # engine/ for `agp`
from games.hostage_chess.game import HostageChess, HState, WHITE, BLACK  # noqa: E402

G = HostageChess()


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


def play(state, moves):
    for m in moves:
        assert m in G.legal_moves(state), f"{m} not legal"
        state = G.apply_move(state, m)
    return state


def mk(board, to_move, prisons=None, hands=None, castling="", pending=None):
    st = HState(board=dict(board), to_move=to_move, castling=frozenset(castling),
                ep=None, hands=hands or {WHITE: {}, BLACK: {}},
                prisons=prisons or {WHITE: {}, BLACK: {}}, pending=pending)
    st.reps = {G._poskey_state(st): 1}
    return st


def main():
    # 1) start perft == orthodox chess to depth 4 (see module docstring).
    s0 = G.initial_state()
    for d, want in {1: 20, 2: 400, 3: 8902, 4: 197281}.items():
        got = perft(s0, d)
        assert got == want, f"start perft {d}: {got} != {want}"

    # 2) Wikipedia's Fried Liver refutation: 1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5
    #    d5 5.exd5 Nxd5 6.Nxf7 Kxf7 7.Qf3+ Ke6 8.Bxd5+ Qxd5 9.(N-B)B*f7+.
    line = ["4,1>4,3", "4,6>4,4", "6,0>5,2", "1,7>2,5", "5,0>2,3", "6,7>5,5",
            "5,2>6,4", "3,6>3,4", "4,3>3,4", "5,5>3,4", "6,4>5,6", "4,7>5,6",
            "3,0>5,2", "5,6>4,5", "2,3>3,4", "3,7>3,4"]
    s = play(G.initial_state(), line)
    assert s.prisons[WHITE] == {"P": 2, "N": 1}, s.prisons
    assert s.prisons[BLACK] == {"P": 1, "N": 1, "B": 1}, s.prisons
    ex = sorted(m for m in G.legal_moves(s) if m.startswith("exchange:"))
    assert ex == ["exchange:N-B", "exchange:N-N", "exchange:N-P",
                  "exchange:P-P"], ex  # value rule: P may not buy back N/B
    s = G.apply_move(s, "exchange:N-B")            # release the black N, rescue the B
    assert s.pending == "B" and s.to_move == WHITE  # same player must now drop
    assert s.hands[BLACK] == {"N": 1}               # released hostage -> Black's airfield
    ms = G.legal_moves(s)
    assert ms and all(m.startswith("B@") for m in ms)
    assert "B@5,6" in ms                            # B*f7+
    s = G.apply_move(s, "B@5,6")
    assert s.to_move == BLACK
    assert G._in_check_h(s.board, BLACK, s.prisons)  # drop delivers check

    # 3) dynamic 7th-rank-pawn rule (promotion availability).
    board = {(3, 6): (WHITE, "P"), (4, 7): (BLACK, "K"), (6, 0): (WHITE, "K"),
             (0, 0): (WHITE, "N"), (0, 7): (BLACK, "Q")}
    s = mk(board, BLACK)
    assert not G._in_check_h(s.board, BLACK, s.prisons)   # d7 pawn gives no check
    ms = G.legal_moves(s)
    assert "0,7>0,0" not in ms      # Qxa1 illegal: imprisoning the N would let
    assert "0,7>0,3" in ms          # the pawn promote => self-check on e8
    sw = mk(board, WHITE)
    assert not any(m.startswith("3,6>") for m in G.legal_moves(sw))  # pawn stuck
    s2 = mk(board, BLACK, prisons={WHITE: {}, BLACK: {"N": 1}})
    assert G._in_check_h(s2.board, BLACK, s2.prisons)     # now it checks e8

    # 4) promotion: only to types in the opponent's prison; pawn goes to prison.
    sw2 = mk(board, WHITE, prisons={WHITE: {}, BLACK: {"N": 1, "R": 1}})
    promos = sorted(m for m in G.legal_moves(sw2) if m.startswith("3,6>3,7"))
    assert promos == ["3,6>3,7=N", "3,6>3,7=R"], promos   # no =Q available
    s3 = G.apply_move(sw2, "3,6>3,7=R")
    assert s3.board[(3, 7)] == (WHITE, "R")
    assert s3.prisons[BLACK] == {"N": 1, "P": 1}          # R out, pawn in

    # 5) castling with a dropped rook (rights regenerate iff king never moved).
    b2 = {(4, 0): (WHITE, "K"), (4, 7): (BLACK, "K"), (7, 6): (BLACK, "P")}
    sc = mk(b2, WHITE, hands={WHITE: {"R": 1}, BLACK: {}}, castling="Ee")
    sc = G.apply_move(sc, "R@7,0")
    assert "K" in sc.castling
    sc = G.apply_move(sc, "7,6>7,5")
    assert "4,0>6,0" in G.legal_moves(sc)
    sc = G.apply_move(sc, "4,0>6,0")
    assert sc.board[(6, 0)] == (WHITE, "K") and sc.board[(5, 0)] == (WHITE, "R")
    sn = mk(b2, WHITE, hands={WHITE: {"R": 1}, BLACK: {}}, castling="e")
    sn = G.apply_move(sn, "R@7,0")                        # king already moved
    assert "K" not in sn.castling
    sn = G.apply_move(sn, "7,6>7,5")
    assert "4,0>6,0" not in G.legal_moves(sn)

    # 6) pawn drops: not on ranks 1/8; double step from rank 2; no e.p. against
    #    the drop itself, normal e.p. after a later double step.
    b3 = {(4, 0): (WHITE, "K"), (4, 7): (BLACK, "K"), (0, 6): (BLACK, "P")}
    sp = mk(b3, WHITE, hands={WHITE: {"P": 1}, BLACK: {}})
    ms = G.legal_moves(sp)
    assert "P@4,3" in ms and "P@0,0" not in ms and "P@0,7" not in ms
    sp = G.apply_move(sp, "P@4,1")
    assert sp.ep is None                                  # a drop never sets e.p.
    sp = G.apply_move(sp, "0,6>0,5")
    assert "4,1>4,3" in G.legal_moves(sp)                 # inherited double step
    sp = G.apply_move(sp, "4,1>4,3")
    assert sp.ep == ((4, 2), (4, 3))                      # ...which allows e.p.

    # 7) exchange value rule: a pawn cannot buy back a queen; Q-Q and N-B ok.
    kk = {(4, 0): (WHITE, "K"), (4, 7): (BLACK, "K"), (0, 1): (WHITE, "P")}
    ex = lambda pr: sorted(m for m in G.legal_moves(mk(kk, WHITE, prisons=pr))
                           if m.startswith("exchange:"))
    assert ex({WHITE: {"P": 1}, BLACK: {"Q": 1}}) == []
    assert ex({WHITE: {"Q": 1}, BLACK: {"Q": 1}}) == ["exchange:Q-Q"]
    assert ex({WHITE: {"N": 1}, BLACK: {"B": 1}}) == ["exchange:N-B"]
    assert ex({WHITE: {"B": 1}, BLACK: {"N": 1}}) == ["exchange:B-N"]

    # 8) a drop may checkmate.
    bm = {(7, 7): (BLACK, "K"), (6, 6): (BLACK, "P"), (7, 6): (BLACK, "P"),
          (0, 0): (WHITE, "K")}
    sm = G.apply_move(mk(bm, WHITE, hands={WHITE: {"R": 1}, BLACK: {}}), "R@3,7")
    assert G.is_terminal(sm) and G.returns(sm) == [1.0, -1.0]

    # 9) threefold repetition is a draw (key includes prisons/airfields/pending).
    s = G.initial_state()
    for m in ["6,0>5,2", "6,7>5,5", "5,2>6,0", "5,5>6,7"] * 2:
        s = G.apply_move(s, m)
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0]

    # 10) serialize round-trip + conservation invariant over random play: all 32
    #     men and every type count survive forever, wherever they live.
    import json
    want = {"P": 16, "N": 4, "B": 4, "R": 4, "Q": 2, "K": 2}
    rng = random.Random(7)
    for _ in range(2):
        s = G.initial_state()
        for _ in range(300):
            if G.is_terminal(s):
                break
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            cnt = {}
            for (_, t) in s.board.values():
                cnt[t] = cnt.get(t, 0) + 1
            for pool in list(s.hands.values()) + list(s.prisons.values()):
                for t, n in pool.items():
                    cnt[t] = cnt.get(t, 0) + n
            if s.pending:
                cnt[s.pending] = cnt.get(s.pending, 0) + 1
            assert cnt == want, (s.ply, cnt)
            s2 = G.deserialize(json.loads(json.dumps(G.serialize(s))))
            assert G.serialize(s2) == G.serialize(s)

    print("hostage_chess selftest: all checks passed")


if __name__ == "__main__":
    main()
