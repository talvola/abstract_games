"""Standalone correctness anchor for Atomic Chess.

Run from the engine dir:  PYTHONPATH=. python3 games/atomic_chess/selftest.py

Asserts, against the published Atomic opening perft AND python-chess
``AtomicBoard`` as a reference oracle:

  * perft at depths 1-3 from the opening (20 / 400 / 8902) plus deeper / tactical
    positions where explosions actually occur;
  * a move-generation + outcome differential vs ``AtomicBoard`` over many random
    games (every position: identical legal-move set; every terminal: identical
    win/loss/draw verdict);
  * specific rule positions: king-explosion win, illegality of blowing up your
    own king, ignoring check to explode the enemy king, connected-kings (no
    check), and pawns surviving a blast.

Prints "SELFTEST OK" and exits 0 on success; raises / exits nonzero on failure.
python-chess is required (the differential is the real anchor).
"""

import sys
import random

sys.path.insert(0, ".")

import chess  # noqa: E402
import chess.variant  # noqa: E402

from agp.chesslike import WHITE, BLACK  # noqa: E402
from games.atomic_chess.game import AtomicChess  # noqa: E402

G = AtomicChess()

# --------------------------------------------------------------------------- #
# Conversion AGP <-> python-chess
# --------------------------------------------------------------------------- #
PIECE_TO_CHESS = {"P": chess.PAWN, "N": chess.KNIGHT, "B": chess.BISHOP,
                  "R": chess.ROOK, "Q": chess.QUEEN, "K": chess.KING}


def agp_to_board(state) -> chess.variant.AtomicBoard:
    b = chess.variant.AtomicBoard(None)  # empty
    b.clear_board()
    for (c, r), (pl, t) in state.board.items():
        sq = chess.square(c, r)
        color = chess.WHITE if pl == WHITE else chess.BLACK
        b.set_piece_at(sq, chess.Piece(PIECE_TO_CHESS[t], color))
    b.turn = chess.WHITE if state.to_move == WHITE else chess.BLACK
    rights = 0
    if "K" in state.castling and b.piece_at(chess.H1):
        rights |= chess.BB_H1
    if "Q" in state.castling and b.piece_at(chess.A1):
        rights |= chess.BB_A1
    if "k" in state.castling and b.piece_at(chess.H8):
        rights |= chess.BB_H8
    if "q" in state.castling and b.piece_at(chess.A8):
        rights |= chess.BB_A8
    b.castling_rights = rights
    if state.ep is not None:
        (tc, tr), _ = state.ep
        b.ep_square = chess.square(tc, tr)
    b.halfmove_clock = state.halfmove
    return b


def fen_to_agp(fen):
    b = chess.variant.AtomicBoard(fen)
    board = {}
    for sq in chess.SQUARES:
        p = b.piece_at(sq)
        if p:
            board[(chess.square_file(sq), chess.square_rank(sq))] = (
                WHITE if p.color == chess.WHITE else BLACK,
                p.symbol().upper(),
            )
    from agp.chesslike import CState
    castling = ""
    if b.castling_rights & chess.BB_H1:
        castling += "K"
    if b.castling_rights & chess.BB_A1:
        castling += "Q"
    if b.castling_rights & chess.BB_H8:
        castling += "k"
    if b.castling_rights & chess.BB_A8:
        castling += "q"
    ep = None
    if b.ep_square is not None:
        tc, tr = chess.square_file(b.ep_square), chess.square_rank(b.ep_square)
        # captured pawn sits behind the ep target
        cr = tr - 1 if b.turn == chess.WHITE else tr + 1
        ep = ((tc, tr), (tc, cr))
    st = CState(board=board,
                to_move=WHITE if b.turn == chess.WHITE else BLACK,
                castling=frozenset(castling), ep=ep,
                halfmove=b.halfmove_clock)
    st.reps = {G._poskey(board, st.to_move, st.castling, st.ep): 1}
    return st


def agp_moves_as_uci(state):
    """The AGP legal moves rendered as UCI strings, for set comparison."""
    out = set()
    for m in G.legal_moves(state):
        promo = None
        mm = m
        if "=" in mm:
            mm, promo = mm.split("=")
        fs, ts = mm.split(">")
        fc, fr = (int(x) for x in fs.split(","))
        tc, tr = (int(x) for x in ts.split(","))
        u = chess.square_name(chess.square(fc, fr)) + chess.square_name(chess.square(tc, tr))
        if promo:
            u += promo.lower()
        out.add(u)
    return out


def chess_moves_as_uci(board):
    return {m.uci() for m in board.legal_moves}


# --------------------------------------------------------------------------- #
# 1. Perft
# --------------------------------------------------------------------------- #
def agp_perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0  # no further nodes from a finished game
    n = 0
    for m in G.legal_moves(state):
        n += agp_perft(G.apply_move(state, m), depth - 1)
    return n


def ref_perft(board, depth):
    if depth == 0:
        return 1
    if board.is_variant_end():
        return 0
    n = 0
    for m in board.legal_moves:
        board.push(m)
        n += ref_perft(board, depth - 1)
        board.pop()
    return n


def test_perft():
    cases = [
        # (label, fen-or-None, depths, published-opening-anchor)
        ("opening", None, [1, 2, 3], {1: 20, 2: 400, 3: 8902}),
        ("opening-d4", None, [4], {4: 197326}),
        ("kiwipete",
         "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
         [1, 2, 3], None),
        ("ep-blast", "4k3/8/8/3pP3/8/8/8/4K3 w - - 0 1", [1, 2, 3], None),
        ("explosive-mid",
         "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 0 1",
         [1, 2, 3], None),
    ]
    for label, fen, depths, anchor in cases:
        state = G.initial_state() if fen is None else fen_to_agp(fen)
        ref = chess.variant.AtomicBoard() if fen is None else chess.variant.AtomicBoard(fen)
        for d in depths:
            got = agp_perft(state, d)
            want = ref_perft(ref, d)
            assert got == want, f"perft[{label}] d={d}: AGP {got} != AtomicBoard {want}"
            if anchor and d in anchor:
                assert got == anchor[d], \
                    f"perft[{label}] d={d}: {got} != published anchor {anchor[d]}"
            print(f"  perft {label:14s} d={d}: {got}")


# --------------------------------------------------------------------------- #
# 2. Random-game differential vs AtomicBoard
# --------------------------------------------------------------------------- #
def test_differential(num_games=700, max_plies=160, seed=12345):
    rng = random.Random(seed)
    positions = 0
    for _ in range(num_games):
        state = G.initial_state()
        ref = chess.variant.AtomicBoard()
        for _ in range(max_plies):
            agp_term = G.is_terminal(state)
            # A *forced* end (checkmate / stalemate / king explosion / dead
            # material) -- no optional draw claim -- must be agreed exactly.
            ref_forced = ref.is_game_over(claim_draw=False)
            if ref_forced:
                assert agp_term, (
                    f"AGP missed a forced terminal at {ref.fen()}")
                _assert_same_outcome(state, ref)
                break
            if agp_term:
                # AGP ended but the ref did not *force* an end: this is only OK
                # if AGP is claiming a legitimate draw (threefold / fifty-move /
                # bare-kings) that python-chess agrees is claimable.
                assert G.returns(state) == [0.0, 0.0], (
                    f"AGP claims a non-draw end the ref doesn't force "
                    f"at {ref.fen()}: {G.returns(state)}")
                assert ref.can_claim_draw() or ref.is_insufficient_material(), (
                    f"AGP drew at {ref.fen()} but ref sees no claimable draw")
                break

            # Live position (neither side over): the legal-move sets must match
            # exactly -- this is the core move-generation anchor.
            a = agp_moves_as_uci(state)
            r = chess_moves_as_uci(ref)
            assert a == r, (
                f"move-set mismatch at {ref.fen()}\n"
                f"  AGP-only: {sorted(a - r)}\n  ref-only: {sorted(r - a)}"
            )
            positions += 1
            if not a:
                break

            uci = rng.choice(sorted(a))
            # apply to AGP
            state = _apply_uci(state, uci)
            # apply to ref
            ref.push(chess.Move.from_uci(uci))
    print(f"  differential: {num_games} games, {positions} positions matched")


def _apply_uci(state, uci):
    fr = chess.parse_square(uci[0:2])
    to = chess.parse_square(uci[2:4])
    promo = uci[4:].upper() if len(uci) > 4 else ""
    move = (f"{chess.square_file(fr)},{chess.square_rank(fr)}>"
            f"{chess.square_file(to)},{chess.square_rank(to)}")
    if promo:
        move += "=" + promo
    return G.apply_move(state, move)


def _assert_same_outcome(state, ref):
    """Compare AGP's payoff against AtomicBoard's authoritative result(). This
    covers king-explosion wins, checkmates, stalemates and all draw rules."""
    ret = G.returns(state)
    res = ref.result(claim_draw=False)  # "1-0", "0-1" or "1/2-1/2" (forced end)
    if res == "1-0":
        want = [1.0, -1.0]
    elif res == "0-1":
        want = [-1.0, 1.0]
    else:
        want = [0.0, 0.0]
    assert ret == want, (
        f"outcome mismatch at {ref.fen()}: AGP {ret} want {want} "
        f"(ref result {res})"
    )


# --------------------------------------------------------------------------- #
# 3. Specific rule positions
# --------------------------------------------------------------------------- #
def test_rule_positions():
    # (a) King-explosion win: white queen takes the pawn next to black's king,
    #     blowing up the king -> white wins immediately.
    st = fen_to_agp("4k3/3p4/8/8/8/8/3Q4/4K3 w - - 0 1")
    # Qd2xd7 explodes d8(king),c8,e8 ... king gone -> win
    assert "3,1>3,6" in G.legal_moves(st), "Qxd7 should be legal"
    nx = G.apply_move(st, "3,1>3,6")
    assert G._king(nx.board, BLACK) is None, "black king should be exploded"
    assert G.is_terminal(nx) and G.returns(nx) == [1.0, -1.0], \
        "exploding enemy king must be an immediate white win"

    # (b) You may NOT blow up your own king: white king on e1, white queen e2,
    #     black pawn d3. Qxd3? d3's blast hits e2 (queen) but not e1 -> ok.
    #     Make the king adjacent: king on d2 would be blown up by a capture on d3.
    st2 = fen_to_agp("4k3/8/8/8/8/3p4/3K4/8 w - - 0 1")
    # the king itself cannot capture d3 (would explode itself). No other capturer.
    moves2 = G.legal_moves(st2)
    assert "3,1>3,2" not in moves2, "king must not capture (would explode itself)"

    # (b2) a non-king capture that would catch the own king is illegal.
    #   White Ke2, white Rd2, black pawn on d3? Rxd3 explodes d2-area incl. e2?
    #   d3 neighbors: c2,d2,e2,c3,e3,c4,d4,e4. e2=own king -> illegal.
    st2b = fen_to_agp("4k3/8/8/8/8/3p4/3RK3/8 w - - 0 1")
    assert "3,1>3,2" not in G.legal_moves(st2b), \
        "Rxd3 would explode own adjacent king -> illegal"

    # (c) Ignore check to explode the enemy king.  White king e1 is in check
    #     from the black rook on e8 (open e-file).  White's queen on d7 sits
    #     beside the black king on c8: Qxc7+ ... actually Qd7xc8? no -- let the
    #     queen capture the pawn on c7, exploding c8 (the black king) -> win,
    #     even though white's own king is in check.
    st3 = fen_to_agp("2k5/2pQ4/8/8/8/8/8/r3K3 w - - 0 1")
    assert G.in_check(st3.board, WHITE), "white king in check from rook a1"
    # Qd7xc7 explodes c8 (black king) -> immediate win despite being in check.
    assert "3,6>2,6" in G.legal_moves(st3), \
        "must be allowed to ignore check to explode the enemy king"
    nx3 = G.apply_move(st3, "3,6>2,6")
    assert G._king(nx3.board, BLACK) is None and G.returns(nx3) == [1.0, -1.0], \
        "exploding the enemy king wins even while in check"
    # ... and a move that does NOT resolve the check is still illegal:
    assert "3,6>3,5" not in G.legal_moves(st3), \
        "a quiet queen move leaving own king in check is illegal"

    # (d) Connected kings -> no check. Kings adjacent e4/e5, black rook a4 on the
    #     4th rank "attacks" e4, but kings connected => not check.
    st4 = fen_to_agp("8/8/8/4k3/r3K3/8/8/8 w - - 0 1")
    assert not G.in_check(st4.board, WHITE), \
        "no check while kings are connected (adjacent)"
    # and once kings separate, the rook does check:
    st4b = fen_to_agp("8/8/4k3/8/r3K3/8/8/8 w - - 0 1")
    assert G.in_check(st4b.board, WHITE), "rook checks when kings not adjacent"

    # (e) Pawns survive a blast; only the captured pawn is removed.
    #   White knight on c2... let's: white Nf3 takes e5 pawn; surrounding pawns
    #   d6,f6 (black) survive; black pieces d5? use a crafted FEN.
    st5 = fen_to_agp("4k3/3p1p2/8/4p3/8/5N2/8/4K3 w - - 0 1")
    # Nf3xe5 : explosion centre e5; neighbours d6,f6 are pawns -> survive.
    nx5 = G.apply_move(st5, "5,2>4,4")
    assert (3, 6) in nx5.board and (5, 6) in nx5.board, \
        "pawns adjacent to the blast must survive"
    assert (4, 4) not in nx5.board, "captured pawn + capturer are gone"
    assert (5, 2) not in nx5.board, "the capturing knight is destroyed"

    # cross-check every crafted *live* position's full move set against
    # AtomicBoard (dead-material positions are excluded: python-chess still
    # enumerates pseudo-legal king moves there while AGP, correctly, returns no
    # moves for a finished game).
    for fen in [
        "4k3/3p4/8/8/8/8/3Q4/4K3 w - - 0 1",
        "4k3/8/8/8/8/3p4/3RK3/8 w - - 0 1",
        "2k5/2pQ4/8/8/8/8/8/r3K3 w - - 0 1",
        "4k3/3p1p2/8/4p3/8/5N2/8/4K3 w - - 0 1",
    ]:
        st = fen_to_agp(fen)
        ref = chess.variant.AtomicBoard(fen)
        assert not ref.is_insufficient_material(), f"crafted pos {fen} is a dead draw"
        a, r = agp_moves_as_uci(st), chess_moves_as_uci(ref)
        assert a == r, f"rule-pos move mismatch {fen}: {sorted(a ^ r)}"
    print("  rule positions: king-win / no-self-explode / connected-kings / "
          "pawn-survival OK")


def test_insufficient_material():
    """Cross-check the atomic dead-position rule against AtomicBoard over many
    small material configurations (both kings present)."""
    import itertools
    pieces = ["", "N", "B", "R", "Q", "P"]   # "" = nothing extra
    checked = 0
    # two squares per side, on opposite shades, to exercise the bishop-colour
    # branch: white c2 (light) / c4 (dark); black f7 (light) / f5 (dark).
    wsq = [(2, 1), (2, 3)]
    bsq = [(5, 6), (5, 4)]
    for w1, w2, b1, b2 in itertools.product(pieces, pieces, pieces, pieces):
        board = {(6, 0): (WHITE, "K"), (6, 7): (BLACK, "K")}
        for sq, p, pl in ((wsq[0], w1, WHITE), (wsq[1], w2, WHITE),
                          (bsq[0], b1, BLACK), (bsq[1], b2, BLACK)):
            if p:
                board[sq] = (pl, p)
        ref = _board_to_ref(board)
        got = G._insufficient(board)
        want = ref.is_insufficient_material()
        assert got == want, (
            f"insufficient-material mismatch at {ref.fen()}: AGP {got} ref {want}")
        checked += 1
    print(f"  insufficient-material: {checked} material configs match AtomicBoard")


def _board_to_ref(board):
    b = chess.variant.AtomicBoard(None)
    b.clear_board()
    for (c, r), (pl, t) in board.items():
        b.set_piece_at(chess.square(c, r),
                       chess.Piece(PIECE_TO_CHESS[t],
                                   chess.WHITE if pl == WHITE else chess.BLACK))
    return b


# --------------------------------------------------------------------------- #
def main():
    print("Atomic Chess selftest")
    print("- perft (published opening anchor + AtomicBoard cross-check):")
    test_perft()
    print("- specific rule positions:")
    test_rule_positions()
    print("- insufficient-material vs AtomicBoard:")
    test_insufficient_material()
    print("- random-game differential vs python-chess AtomicBoard:")
    test_differential()
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print("SELFTEST FAILED:", e, file=sys.stderr)
        sys.exit(1)
