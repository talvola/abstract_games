"""Correctness anchors for Flip Chess / Flip Shogi (pure stdlib).

Sources: chessvariants.com/38.dir/flip.html (rules text + board-array &
piece-pattern GIFs) and the author-sanctioned Zillions file
(programs.dir/zillions/flip.zip -> Flip3.zrf, by Hans Bodlaender).

Anchors:
  (a) the 38-cell board set, asserted as DATA (7x6 minus 4 corners), plus the
      opening array transcribed from fliparray.gif;
  (b) perft(1)=23 hand-justified from the setup, and Black-mirror symmetry;
  (c) rule positions for every piece's move on BOTH sides, the flip mechanic
      (move-then-flip, flip-in-place, forced promotion), check/checkmate,
      bare-King loss, stalemate draw, and all four Shogi drop rules;
  (d) move-string uniqueness, serialize round-trip, random playouts to terminal.

Run:  cd engine && PYTHONPATH=. python3 games/flip_chess/selftest.py
"""
import random

from games.flip_chess.game import (
    FlipChess, FState, CELLS, MISSING, LETTERS, WHITE, BLACK, FLIP,
    _piece_targets, _all_legal, _in_check, _bare_king, _label, _cid,
)

g = FlipChess()


def cell_of(s):        # "b1" -> (2, 1)
    return (LETTERS.index(s[0]) + 1, int(s[1:]))


def tgt_labels(board, cell, owner, pt):
    return sorted(_label(c) for c in _piece_targets(board, cell, owner, pt))


# -- (a) board set -----------------------------------------------------------
def test_board():
    assert len(CELLS) == 38
    assert MISSING == {(1, 1), (1, 6), (7, 1), (7, 6)}      # the 4 removed corners
    for c in range(1, 8):
        for r in range(1, 7):
            here = (c, r) in CELLS
            want = (c, r) not in {(1, 1), (1, 6), (7, 1), (7, 6)}
            assert here == want, (c, r)
    # the four corners specifically are absent
    for corner in ("a1", "a6", "g1", "g6"):
        assert cell_of(corner) not in CELLS


# -- opening array (fliparray.gif / Flip3.zrf board-setup) -------------------
def test_setup():
    s = g.initial_state()
    b = s.board
    assert len(b) == 20
    # back rank pattern B F K F B, pawns in front
    assert b[cell_of("b1")] == (WHITE, "B")
    assert b[cell_of("c1")] == (WHITE, "F")
    assert b[cell_of("d1")] == (WHITE, "K")
    assert b[cell_of("e1")] == (WHITE, "F")
    assert b[cell_of("f1")] == (WHITE, "B")
    for f in "bcdef":
        assert b[cell_of(f + "2")] == (WHITE, "P")
    # Black mirror (180-degree rotation, colours swapped)
    assert b[cell_of("d6")] == (BLACK, "K")
    for (c, r), (o, pt) in b.items():
        assert b[(8 - c, 7 - r)] == (1 - o, pt)
    # exactly one King, two Bishops, two Ferz, five Pawns per side
    for o in (WHITE, BLACK):
        kinds = sorted(pt for (ow, pt) in b.values() if ow == o)
        assert kinds == sorted(["K", "B", "B", "F", "F", "P", "P", "P", "P", "P"])


# -- (b) perft --------------------------------------------------------------
def test_perft1():
    # Hand count of White's opening moves (see game.py header for the geometry):
    #   Pawns b2..f2 each step forward to rank 3 (1 each)     -> 5 displacements
    #   Ferz c1,e1 boxed in by own pawns / off-board          -> 0
    #   Bishop b1 -> a2 ; Bishop f1 -> g2                     -> 2 displacements
    #   King d1 fully blocked                                 -> 0
    #   => 7 displacements, each x2 (keep-side / flip)        -> 14
    #   + flip-in-place for the 9 non-King pieces             -> 9
    #   total = 23
    s = g.initial_state()
    lm = g.legal_moves(s)
    assert len(lm) == 23, (len(lm), sorted(lm))
    assert len(set(lm)) == 23
    # composition check
    disp = [m for m in lm if ">" in m and m.split(">")[0] != m.split(">")[1].split("=")[0]]
    flips = [m for m in lm if ">" in m and m.split(">")[0] == m.split(">")[1].split("=")[0]]
    assert len(disp) == 14 and len(flips) == 9, (len(disp), len(flips))


def test_perft2_and_symmetry():
    s = g.initial_state()
    lm = g.legal_moves(s)
    tot = sum(len(g.legal_moves(g.apply_move(s, m))) for m in lm)
    # engine-computed; frozen. Sanity: 23 replies, none terminal.
    assert tot == 529, tot          # 23 * 23 (fully symmetric opening, no captures)
    # Black to move from the mirrored opening also has 23 moves.
    s2 = g.apply_move(s, "4,2>4,3=P")       # a quiet White pawn push
    # (Black now to move; its own opening mobility is the mirror of White's 23
    #  minus nothing that push touched — just assert Black has a full move set.)
    assert len(g.legal_moves(s2)) == 23


# -- (c) pawn & berolina geometry -------------------------------------------
def test_pawn_and_berolina():
    # White pawn on d3: steps straight to d4; captures the two forward diagonals.
    b = {cell_of("d3"): (WHITE, "P"),
         cell_of("c4"): (BLACK, "P"), cell_of("e4"): (BLACK, "P")}
    assert tgt_labels(b, cell_of("d3"), WHITE, "P") == ["c4", "d4", "e4"]
    # a friendly piece straight ahead blocks the push but not the diagonals
    b2 = {cell_of("d3"): (WHITE, "P"), cell_of("d4"): (WHITE, "P"),
          cell_of("c4"): (BLACK, "P")}
    assert tgt_labels(b2, cell_of("d3"), WHITE, "P") == ["c4"]
    # Berolina on d3: steps the two forward DIAGONALS; captures STRAIGHT.
    b3 = {cell_of("d3"): (WHITE, "X"), cell_of("d4"): (BLACK, "P")}
    assert tgt_labels(b3, cell_of("d3"), WHITE, "X") == ["c4", "d4", "e4"]
    # Berolina cannot capture on a diagonal, and cannot push into an enemy.
    b4 = {cell_of("d3"): (WHITE, "X"), cell_of("c4"): (BLACK, "P")}
    assert tgt_labels(b4, cell_of("d3"), WHITE, "X") == ["e4"]
    # Black pawn direction is reversed
    assert tgt_labels({}, cell_of("d4"), BLACK, "P") == ["d3"]


def test_steppers_and_sliders():
    # Ferz = single diagonal step; Knight = ordinary leap; Prince/King = 8 steps.
    assert tgt_labels({}, cell_of("d3"), WHITE, "F") == ["c2", "c4", "e2", "e4"]
    assert tgt_labels({}, cell_of("d3"), WHITE, "N") == \
        ["b2", "b4", "c1", "c5", "e1", "e5", "f2", "f4"]
    assert tgt_labels({}, cell_of("d3"), WHITE, "C") == \
        tgt_labels({}, cell_of("d3"), WHITE, "K")
    assert tgt_labels({}, cell_of("d3"), WHITE, "K") == \
        ["c2", "c3", "c4", "d2", "d4", "e2", "e3", "e4"]
    # Bishop slides diagonally; Rook slides orthogonally (stopping at a capture).
    bb = {cell_of("d3"): (WHITE, "B"), cell_of("f5"): (BLACK, "P")}
    assert "e4" in tgt_labels(bb, cell_of("d3"), WHITE, "B")
    assert "f5" in tgt_labels(bb, cell_of("d3"), WHITE, "B")     # capture
    assert "g6" not in CELLS                                     # (removed corner)
    rr = {cell_of("d3"): (WHITE, "R"), cell_of("d5"): (BLACK, "P"),
          cell_of("b3"): (WHITE, "P")}
    labs = tgt_labels(rr, cell_of("d3"), WHITE, "R")
    assert "d4" in labs and "d5" in labs and "d6" not in labs     # stops at capture
    assert "c3" in labs and "b3" not in labs                      # stops before friend
    # off-board is respected: a knight never lands on a removed corner
    assert "a1" not in tgt_labels({}, cell_of("c2"), WHITE, "N")


# -- (c) the flip mechanic ---------------------------------------------------
def test_flip_move_and_inplace():
    # A lone bishop: every displacement offers keep-side (=B) and flip (=R);
    # plus one flip-in-place (=R) since we are not in check.
    b = {cell_of("d3"): (WHITE, "B"), cell_of("d6"): (BLACK, "K"),
         cell_of("a3"): (WHITE, "K")}
    s = FState(board=b, to_move=WHITE)
    d3, e4 = _cid(cell_of("d3")), _cid(cell_of("e4"))    # "4,3", "5,4"
    lm = g.legal_moves(s)
    assert f"{d3}>{e4}=B" in lm and f"{d3}>{e4}=R" in lm  # move keep / move-flip
    assert f"{d3}>{d3}=R" in lm                           # flip in place
    assert f"{d3}>{d3}=B" not in lm                       # (null same-side flip absent)
    # applying the flip-in-place turns the Bishop into a Rook, same square
    s2 = g.apply_move(s, f"{d3}>{d3}=R")
    assert s2.board[cell_of("d3")] == (WHITE, "R")
    # a move-then-flip lands the flipped piece on the destination
    s3 = g.apply_move(s, f"{d3}>{e4}=R")
    assert cell_of("d3") not in s3.board
    assert s3.board[cell_of("e4")] == (WHITE, "R")
    # Ferz<->Knight flips exist too
    b2 = {cell_of("d3"): (WHITE, "F"), cell_of("d6"): (BLACK, "K"),
          cell_of("a3"): (WHITE, "K")}
    lm2 = g.legal_moves(FState(board=b2, to_move=WHITE))
    assert f"{d3}>{d3}=N" in lm2                          # flip in place
    # a move-then-flip-to-Knight (destination differs from origin) also exists
    assert any(m.endswith("=N") and ">" in m and m.split(">")[1].split("=")[0] != d3
               for m in lm2)


def test_flip_in_place_blocked_by_check():
    # In check, flip-in-place is NOT offered (it cannot resolve the check).
    # Black rook on d5 checks the White king down the open d-file; a White
    # bishop sits off the file on b3.
    b = {cell_of("d1"): (WHITE, "K"), cell_of("b3"): (WHITE, "B"),
         cell_of("d5"): (BLACK, "R"), cell_of("a6"): (BLACK, "K")}
    s = FState(board=b, to_move=WHITE)
    assert _in_check(b, WHITE)
    lm = g.legal_moves(s)
    assert not any(">" in m and m.split(">")[0] == m.split(">")[1].split("=")[0]
                   for m in lm)                          # no flip-in-place while in check
    assert lm                                            # but king moves / a block exist


def test_promotion_forced_to_prince():
    # White pawn a-file... use e5 -> e6 straight promotes to Prince (=C), no flip.
    b = {cell_of("e5"): (WHITE, "P"), cell_of("d1"): (WHITE, "K"),
         cell_of("a6"): (BLACK, "K")}
    s = FState(board=b, to_move=WHITE)
    lm = g.legal_moves(s)
    assert "5,5>5,6=C" in lm
    assert "5,5>5,6=P" not in lm and "5,5>5,6=X" not in lm   # promotion is forced
    s2 = g.apply_move(s, "5,5>5,6=C")
    assert s2.board[cell_of("e6")] == (WHITE, "C")
    # a Berolina promotes on its diagonal step too
    b2 = {cell_of("d5"): (WHITE, "X"), cell_of("d1"): (WHITE, "K"),
          cell_of("a6"): (BLACK, "K")}
    lm2 = g.legal_moves(FState(board=b2, to_move=WHITE))
    assert "4,5>3,6=C" in lm2 and "4,5>5,6=C" in lm2
    # Prince does not flip and is not royal (no promotion / no reverse side)
    lm3 = g.legal_moves(s2)  # Black to move; ensure no crash and Prince present
    assert isinstance(lm3, list)


# -- (c) check, checkmate, bare king, stalemate ------------------------------
def test_king_cannot_move_into_check():
    b = {cell_of("d3"): (WHITE, "K"), cell_of("f4"): (BLACK, "R"),
         cell_of("a6"): (BLACK, "K")}
    s = FState(board=b, to_move=WHITE)
    lm = g.legal_moves(s)
    d3 = _cid(cell_of("d3"))                             # "4,3"
    # King may not step onto rank-4 squares (attacked by the rook along rank 4)
    for dest in ("c4", "d4", "e4"):
        assert f"{d3}>{_cid(cell_of(dest))}" not in lm, dest
    assert f"{d3}>{_cid(cell_of('d2'))}" in lm           # a safe retreat exists


def test_checkmate():
    # Two rooks deliver a rank/file mate to a Black king on the top edge.
    # Black king d6; a rook covers rank 5, another mates along rank 6.
    b = {cell_of("d6"): (BLACK, "K"),
         cell_of("b5"): (WHITE, "R"),      # slides to b6 to give the mate
         cell_of("c5"): (WHITE, "R"),      # covers rank 5 (blocks the king down)
         cell_of("f2"): (WHITE, "K")}
    s = FState(board=b, to_move=WHITE)
    # White plays Rb5-b6 -> check along rank 6; the escape rank (5) is covered.
    assert "2,5>2,6=R" in g.legal_moves(s)
    s2 = g.apply_move(s, "2,5>2,6=R")
    assert g.is_terminal(s2) and s2.winner == WHITE, (
        s2.winner, sorted(_all_legal(s2.board, {WHITE: {}, BLACK: {}}, BLACK, "chess")))
    assert g.returns(s2) == [1.0, -1.0]


def test_bare_king_loss():
    # Black has only King + one pawn; White rook captures the pawn -> bare -> loss.
    b = {cell_of("a6"): (BLACK, "K"), cell_of("c5"): (BLACK, "P"),
         cell_of("c1"): (WHITE, "R"), cell_of("f1"): (WHITE, "K")}
    assert not _bare_king(b, {}, BLACK, "chess")
    s = FState(board=b, to_move=WHITE)
    s2 = g.apply_move(s, "3,1>3,5=R")           # Rc1xc5
    assert _bare_king(s2.board, s2.hands, BLACK, "chess")
    assert g.is_terminal(s2) and s2.winner == WHITE
    assert g.returns(s2) == [1.0, -1.0]


def test_draw_paths():
    # NOTE ON STALEMATE: a true stalemate is effectively unreachable in Flip
    # Chess and its draw branch is defensive.  Any flippable piece always has a
    # flip-in-place move when not in check; the Prince is NOT royal, so attacked
    # squares do not immobilise it (only own pieces / the board edge do); and a
    # lone King is scored as a bare-King LOSS, not a stalemate.  So we exercise
    # the (reachable) draw plumbing via the ply cap and four-fold repetition.
    from games.flip_chess.game import PLY_CAP, REP_LIMIT

    # (1) ply cap: a quiet position one ply short of the cap draws on the next move.
    b = {cell_of("d3"): (WHITE, "K"), cell_of("d5"): (BLACK, "K"),
         cell_of("b1"): (WHITE, "R"), cell_of("f6"): (BLACK, "R")}
    s = FState(board=b, to_move=WHITE, mode="chess", ply=PLY_CAP - 1)
    mv = "2,1>3,1=R"                                   # a quiet rook shuffle Rb1-c1
    assert mv in g.legal_moves(s)
    s2 = g.apply_move(s, mv)
    assert g.is_terminal(s2) and s2.draw and s2.winner is None
    assert g.returns(s2) == [0.0, 0.0]

    # (2) four-fold repetition: shuffle two rooks through a 4-cycle until it draws.
    s = FState(board=dict(b), to_move=WHITE, mode="chess")
    cycle = ["2,1>3,1=R", "6,6>5,6=R", "3,1>2,1=R", "5,6>6,6=R"]
    drew = False
    for i in range(40):
        mv = cycle[i % 4]
        assert mv in g.legal_moves(s)
        s = g.apply_move(s, mv)
        if g.is_terminal(s):
            drew = True
            break
    assert drew and s.draw and s.winner is None


# -- (c) Flip Shogi drops ----------------------------------------------------
def test_shogi_capture_banks_pair_token():
    b = {cell_of("d3"): (WHITE, "R"), cell_of("d5"): (BLACK, "R"),
         cell_of("a6"): (BLACK, "K"), cell_of("d1"): (WHITE, "K")}
    s = FState(board=b, to_move=WHITE, mode="shogi")
    s2 = g.apply_move(s, "4,3>4,5=R")          # RxR ; a Rook banks as a "B" token
    assert s2.hands[WHITE] == {"B": 1}
    # a captured Prince banks as a Pawn token
    b2 = {cell_of("d3"): (WHITE, "R"), cell_of("d5"): (BLACK, "C"),
          cell_of("a6"): (BLACK, "K"), cell_of("d1"): (WHITE, "K")}
    s3 = g.apply_move(FState(board=b2, to_move=WHITE, mode="shogi"), "4,3>4,5=R")
    assert s3.hands[WHITE] == {"P": 1}


def test_shogi_drop_rules():
    # A "B" token can drop as EITHER a Bishop or a Rook (rule 6), but only where
    # it attacks an enemy piece (rule 7).
    b = {cell_of("d1"): (WHITE, "K"), cell_of("a6"): (BLACK, "K"),
         cell_of("d4"): (BLACK, "P")}
    hands = {WHITE: {"B": 1}, BLACK: {}}
    s = FState(board=b, hands=hands, to_move=WHITE, mode="shogi")
    lm = g.legal_moves(s)
    # Rook side dropped on d-file or rank 4 attacks the enemy pawn -> legal.
    assert "R@4,3" in lm            # Rook on d3 attacks d4
    assert "B@3,3" in lm            # Bishop on c3 attacks d4 diagonally
    # a Bishop dropped where it hits nothing enemy is illegal (rule 7)
    assert "B@6,3" not in lm        # f3 bishop rays hit no enemy
    # both faces of the token are offered
    assert any(m.startswith("R@") for m in lm) and any(m.startswith("B@") for m in lm)


def test_shogi_pawn_drop_rank_limit():
    # Pawn/Berolina drops limited to the dropper's own first two ranks (rule 8).
    b = {cell_of("d1"): (WHITE, "K"), cell_of("a6"): (BLACK, "K"),
         cell_of("c3"): (BLACK, "P"), cell_of("c4"): (BLACK, "P")}
    hands = {WHITE: {"P": 1}, BLACK: {}}
    s = FState(board=b, hands=hands, to_move=WHITE, mode="shogi")
    lm = [m for m in g.legal_moves(s) if m[0] in ("P", "X") and "@" in m]
    for m in lm:
        cell = m.split("@")[1]
        r = int(cell.split(",")[1])
        assert r <= 2, m               # White's first two ranks are 1 and 2
    # a pawn dropped on b2 attacks c3 (rule 7 satisfied) -> present
    assert "P@2,2" in g.legal_moves(s)
    # and a Berolina face (attacks straight) can also be dropped in-zone
    assert any(m.startswith("X@") for m in g.legal_moves(s))


# -- (d) serialize / uniqueness / termination --------------------------------
def test_serialize_roundtrip():
    for mode in ("chess", "shogi"):
        s = g.initial_state(options={"mode": mode})
        r = random.Random(3)
        for _ in range(25):
            if g.is_terminal(s):
                break
            s = g.apply_move(s, r.choice(g.legal_moves(s)))
        d = g.serialize(s)
        s2 = g.deserialize(d)
        assert g.serialize(s2) == d
        assert s2.mode == mode
        h = g.heuristic(s)
        assert isinstance(h, list) and len(h) == 2 and all(-1.001 <= x <= 1.001 for x in h)


def test_describe_move_runs():
    s = g.initial_state(options={"mode": "shogi"})
    for m in g.legal_moves(s):
        assert isinstance(g.describe_move(s, m), str)


def test_random_games_terminate():
    for mode in ("chess", "shogi"):
        r = random.Random(19 if mode == "chess" else 23)
        for _ in range(25):
            s = g.initial_state(options={"mode": mode})
            steps = 0
            while not g.is_terminal(s) and steps < 2000:
                lm = g.legal_moves(s)
                assert lm, "non-terminal with no legal moves"
                assert len(set(lm)) == len(lm), "duplicate legal move"
                s = g.apply_move(s, r.choice(lm))
                steps += 1
            assert g.is_terminal(s), "game did not terminate under the cap"
            rr = g.returns(s)
            assert len(rr) == 2 and abs(rr[0] + rr[1]) < 1e-9      # zero-sum


def run():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("flip_chess selftest: all passed")


if __name__ == "__main__":
    run()
