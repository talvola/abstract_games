"""Standalone correctness anchors for Akron (Cameron Browne 2002).

Run: PYTHONPATH=. python3 games/akron/selftest.py     (pure stdlib + agp)

Anchors, all reconstructed from Cameron Browne's own sources:
  * Abstract Games #14 Figure 2 -- the EXACT set of valid moves for a marked
    piece (8 moves, four of them steps up to level 1), embedded at the top
    edge of the 8x8 board so the figure's neighbourhood is closed.
  * Figure 3 -- moving a support ball drops the supported ball into the
    vacated pocket; plus a two-ball cascade (Figures 7/8 mechanism).
  * Figure 5 -- Black's move to the interstitial point is legal and CUTS
    White's column via the over/under rule (level-1 edge over level-0 edge).
  * Figure 6 -- White's move up to level 2 forms a level-2 edge over the same
    crossing point, cutting Black's cut and RESTORING White's column.
  * Official rules v3.7 "directly overhead" clarification -- a ball with an
    enemy ball straight above it (level +2) is cut from all connections.
  * Delayed win (v3.7 / PBM default): a spanning connection wins only after
    the opponent's reply; revealing the opponent's connection loses at once.
  * swap, no-legal-move loss, automatic repetition draw, random playouts.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ENGINE))

from games.akron.game import (  # noqa: E402
    Akron, AkronState, BLACK, WHITE,
    _cut_info, _touch_graph, _component, _spans, _pos, _key, _resolve_drops,
)


def S(board, to_move=0, pile=(20, 20), seat_colour=(0, 1), ply=10, size=8):
    """Build a state from {(L,c,r): colour}."""
    return AkronState(size=size,
                      board={_key(p): col for p, col in board.items()},
                      pile=list(pile), seat_colour=list(seat_colour),
                      to_move=to_move, ply=ply)


def connected(balls, a, b):
    adj = _touch_graph(balls)
    return b in _component(adj, a)


def test_fig2_move_set(g):
    """AG#14 Figure 2 (pixel-verified from the printed 300dpi figure): the
    EXACT set of valid moves for White piece a — 10 moves mid-board (four of
    them steps up, incl. the two board holes above the top ball row)."""
    board = {
        # Black
        (0, 1, 6): BLACK, (0, 4, 6): BLACK, (0, 2, 5): BLACK,
        (0, 4, 5): BLACK, (0, 5, 4): BLACK, (0, 6, 4): BLACK,
        # White
        (0, 2, 6): WHITE, (0, 3, 6): WHITE, (0, 7, 6): WHITE,
        (0, 1, 5): WHITE, (0, 3, 5): WHITE,               # b = (0,3,5)
        (0, 5, 5): WHITE, (0, 6, 5): WHITE,
        (0, 1, 4): WHITE, (0, 3, 4): WHITE, (0, 4, 4): WHITE,  # a, c
        (1, 4, 4): WHITE,                                  # level-1 ball
    }
    st = S(board, to_move=1)
    a = "0,3,4"
    got = sorted(m for m in g.legal_moves(st) if m.startswith(a + ">"))
    want = sorted(a + ">" + d for d in [
        "0,2,7", "0,3,7",               # the two holes above the top row
        "1,1,5", "1,2,5", "1,3,5",      # three level-1 steps along the top
        "1,5,4",                        # level-1 step on the right group
        "0,5,6", "0,6,6", "0,7,5",      # board holes by the right group
        "0,4,3",                        # board hole below c
    ])
    assert got == want, (got, want)
    # the interstitial over a's own square is NOT legal (self-support)
    assert a + ">1,3,4" not in got
    # a hole touching only the OTHER white group is not a destination
    assert a + ">0,2,4" not in got

    # Same figure embedded at the TOP edge: the two holes above the top row
    # fall off the board, leaving 8 moves (board-edge clipping).
    board2 = {(L, c, r + 1): col for (L, c, r), col in board.items()}
    st2 = S(board2, to_move=1)
    a2 = "0,3,5"
    got2 = [m for m in g.legal_moves(st2) if m.startswith(a2 + ">")]
    assert len(got2) == 8, got2


def test_fig3_drop_and_cascade(g):
    """Figure 3 drop + a two-step cascade (Figures 7/8 mechanism)."""
    # -- simple drop: lifting the only support drops the upper ball into
    #    the vacated pocket.
    board = {
        (0, 0, 0): BLACK, (0, 1, 0): WHITE, (0, 0, 1): BLACK, (0, 1, 1): WHITE,
        (0, 0, 2): BLACK,
        (1, 0, 0): WHITE,                       # rests on the 2x2 square
    }
    st = S(board, to_move=0)
    mv = "0,0,0>0,0,3"
    assert mv in g.legal_moves(st), g.legal_moves(st)
    ns = g.apply_move(st, mv)
    nb = {_pos(k): v for k, v in ns.board.items()}
    assert nb.get((0, 0, 0)) == WHITE          # dropped ball fills the pocket
    assert (1, 0, 0) not in nb
    assert nb.get((0, 0, 3)) == BLACK

    # -- cascade: f supports u, u supports v; lifting f drops both.
    board = {}
    for c in range(3):
        for r in range(3):
            board[(0, c, r)] = BLACK
    board[(0, 0, 3)] = BLACK                    # not needed, keep group open
    for cc, rr in ((0, 0), (1, 0), (0, 1), (1, 1)):
        board[(1, cc, rr)] = WHITE
    board[(2, 0, 0)] = WHITE                    # v, over plan (1,1)
    st = S(board, to_move=0)
    mv = "0,0,0>0,0,4"                          # f = corner under u=(1,0,0)
    assert mv in g.legal_moves(st), [m for m in g.legal_moves(st) if ">" in m]
    ns = g.apply_move(st, mv)
    nb = {_pos(k): v for k, v in ns.board.items()}
    assert nb.get((0, 0, 0)) == WHITE           # u dropped into f's pocket
    assert nb.get((1, 0, 0)) == WHITE           # v dropped into u's pocket
    assert (2, 0, 0) not in nb


FIG5_BOARD = {
    # White column (S-N) at c=3, plus (0,2,5)  [pixel-verified vs the print;
    # the print also shows one isolated far-right Black ball 5 holes right of
    # the column -- off this embed's board and inert, so omitted]
    (0, 3, 7): WHITE, (0, 3, 6): WHITE, (0, 3, 5): WHITE, (0, 3, 4): WHITE,
    (0, 3, 3): WHITE, (0, 3, 2): WHITE, (0, 2, 5): WHITE,
    # Black: a + arms
    (0, 4, 6): BLACK,                                    # a
    (0, 4, 5): BLACK, (0, 4, 4): BLACK, (0, 5, 4): BLACK,
    (0, 1, 4): BLACK, (0, 2, 4): BLACK,
    (1, 3, 4): BLACK,                                    # pre-existing L1 ball
}


def test_fig5_black_cuts_white(g):
    st = S(FIG5_BOARD, to_move=0)
    balls = {_pos(k): v for k, v in st.board.items()}
    # before: White's column is intact, Black's arms are split
    assert connected(balls, (0, 3, 4), (0, 3, 5))
    assert not connected(balls, (0, 1, 4), (0, 5, 4))
    mv = "0,4,6>1,2,4"                       # a to the interstitial point
    assert mv in g.legal_moves(st), [m for m in g.legal_moves(st) if ">" in m]
    ns = g.apply_move(st, mv)
    nb = {_pos(k): v for k, v in ns.board.items()}
    # after: the level-1 Black edge crosses over White's (3,4)-(3,5) edge
    assert not connected(nb, (0, 3, 4), (0, 3, 5))       # White cut
    assert connected(nb, (0, 1, 4), (0, 5, 4))           # Black bridged


FIG6_BOARD = {
    # White
    (0, 3, 7): WHITE, (0, 3, 6): WHITE, (0, 3, 5): WHITE, (0, 3, 4): WHITE,
    (0, 3, 3): WHITE, (0, 3, 2): WHITE,
    (0, 2, 5): WHITE, (0, 2, 6): WHITE, (0, 4, 6): WHITE, (0, 2, 3): WHITE,
    (0, 1, 5): WHITE,                                    # n
    (1, 2, 5): WHITE, (1, 3, 3): WHITE,
    (2, 2, 3): WHITE,                                    # level-2 ball
    # Black
    (0, 1, 4): BLACK, (0, 2, 4): BLACK,
    (0, 4, 5): BLACK, (0, 4, 4): BLACK, (0, 5, 4): BLACK,
    (0, 4, 3): BLACK,
    (1, 3, 5): BLACK, (1, 2, 4): BLACK, (1, 3, 4): BLACK, (1, 2, 3): BLACK,
}


def test_fig6_white_cuts_blacks_cut(g):
    st = S(FIG6_BOARD, to_move=1)
    balls = {_pos(k): v for k, v in st.board.items()}
    # before: Black's level-1 bridge cuts White's column and spans the arms
    assert not connected(balls, (0, 3, 4), (0, 3, 5))
    assert connected(balls, (0, 1, 4), (0, 5, 4))
    mv = "0,1,5>2,2,4"                       # n steps up to level 2
    assert mv in g.legal_moves(st), [m for m in g.legal_moves(st) if ">" in m]
    ns = g.apply_move(st, mv)
    nb = {_pos(k): v for k, v in ns.board.items()}
    # after: the White level-2 edge over the same crossing point prevails --
    # Black's cut is cut, White's column is restored.
    assert connected(nb, (0, 3, 4), (0, 3, 5))
    assert not connected(nb, (0, 1, 4), (0, 5, 4))


def test_overhead_cut():
    """v3.7: an enemy ball directly overhead cuts a ball from everything."""
    board = {}
    for c in range(2, 5):
        for r in range(2, 5):
            board[(0, c, r)] = WHITE
    board[(0, 3, 3)] = BLACK
    board[(0, 2, 3)] = BLACK
    board[(1, 2, 2)] = BLACK
    board[(1, 3, 2)] = WHITE
    board[(1, 2, 3)] = WHITE
    board[(1, 3, 3)] = BLACK
    balls = dict(board)
    assert connected(balls, (0, 2, 3), (0, 3, 3))
    balls[(2, 2, 2)] = WHITE          # white directly overhead (0,3,3)
    assert not connected(balls, (0, 2, 3), (0, 3, 3))
    balls[(2, 2, 2)] = BLACK          # own colour overhead: no cut
    assert connected(balls, (0, 2, 3), (0, 3, 3))


def test_pbm_five_moves(g):
    """Browne's gamerz.net PBM help worked example: Horz piece a has EXACTLY
    five valid moves (three board holes, one level-1 point, one level-2
    point); piece b is pinned (supports two) and cut from a by the
    overpassing Vert level-1 pair. Horz = BLACK here.  The two balls of the
    middle column hidden behind arc art in the ASCII diagram are taken as
    Horz (the reading under which Browne's 'cuts all paths between a and b'
    remark is meaningful)."""
    H, V = BLACK, WHITE
    board = {
        (0, 4, 1): V,
        (0, 2, 2): H, (0, 3, 2): H, (0, 4, 2): H, (0, 5, 2): V,   # a=(3,2)
        (0, 2, 3): V, (0, 3, 3): H, (0, 4, 3): H, (0, 5, 3): H,
        (0, 3, 4): V, (0, 4, 4): H, (0, 5, 4): V,
        (0, 3, 5): H, (0, 4, 5): H, (0, 5, 5): H,                 # b=(4,5)
        (1, 3, 3): H, (1, 4, 3): H,        # Horz level-1 pair
        (1, 3, 4): V, (1, 4, 4): V,        # Vert level-1 pair (the overpass)
    }
    st = S(board, to_move=0)
    a = "0,3,2"
    got = sorted(m for m in g.legal_moves(st) if m.startswith(a + ">"))
    want = sorted(a + ">" + d for d in [
        "0,2,1",                # 1: board hole above
        "0,1,2",                # 2: board hole left
        "0,6,3",                # 3: board hole right
        "1,4,2",                # 4: level-1 point
        "2,3,3",                # 5: level-2 point over the four L1 balls
    ])
    assert got == want, (got, want)
    # b supports two level-1 balls -> pinned, no moves at all
    b = "0,4,5"
    assert not [m for m in g.legal_moves(st) if m.startswith(b + ">")]
    # and the overpass cuts b from a
    balls = {_pos(k): v for k, v in st.board.items()}
    assert not connected(balls, (0, 3, 2), (0, 4, 5))


def test_pbm_won_game(g):
    """Browne's PBM help 'game won by Vert' final diagram (Vert = WHITE =
    rank/S-N direction; ranks 8..1 -> r 7..0).  White spans via a chain
    through levels 0-2 that survives Black's level-1 cutting pairs; Black
    does not span.  Balls hidden behind the ASCII art (supports only) are
    taken as White, except F5 (Black) to respect the 32-ball supply."""
    V, H = WHITE, BLACK
    board = {
        # rank 8 (r7) .. rank 1 (r0); cols A..H -> c 0..7
        (0, 3, 7): V,
        (0, 0, 6): H, (0, 1, 6): H, (0, 2, 6): H, (0, 3, 6): V, (0, 4, 6): V,
        (0, 1, 5): V, (0, 2, 5): V, (0, 3, 5): V, (0, 4, 5): V,
        (0, 2, 4): V, (0, 3, 4): V, (0, 4, 4): V, (0, 5, 4): H,
        (0, 2, 3): V, (0, 3, 3): V, (0, 4, 3): V, (0, 5, 3): H,
        (0, 2, 2): V, (0, 3, 2): V, (0, 4, 2): V, (0, 5, 2): H,
        (0, 6, 2): H, (0, 7, 2): H,
        (0, 0, 1): H, (0, 1, 1): H, (0, 2, 1): V, (0, 3, 1): V, (0, 4, 1): V,
        (0, 5, 1): V, (0, 7, 1): H,
        (0, 0, 0): V, (0, 1, 0): H, (0, 2, 0): H, (0, 3, 0): H, (0, 4, 0): V,
        (0, 5, 0): H, (0, 6, 0): H, (0, 7, 0): V,
        # level 1 (a ball anchored at ranks k/k-1 has r = k-2)
        (1, 3, 5): V,
        (1, 2, 4): V, (1, 3, 4): V,
        (1, 2, 3): V, (1, 3, 3): H, (1, 4, 3): H,
        (1, 2, 2): V, (1, 3, 2): H,
        (1, 3, 1): V, (1, 4, 1): V,
        (1, 3, 0): H, (1, 4, 0): V,
        # level 2
        (2, 2, 3): V,
    }
    st = S(board, to_move=0)
    balls = {_pos(k): v for k, v in st.board.items()}
    assert _spans(balls, WHITE, 8)          # Vert's winning chain holds
    assert not _spans(balls, BLACK, 8)


def test_swap(g):
    st = g.initial_state()
    assert "swap" not in g.legal_moves(st)
    st1 = g.apply_move(st, "0,4,4")
    assert "swap" in g.legal_moves(st1)
    st2 = g.apply_move(st1, "swap")
    assert st2.seat_colour == [1, 0]           # seat 1 now owns Black
    assert st2.to_move == 0
    assert "swap" not in g.legal_moves(st2)
    # the placed Black ball is now rendered as seat 1's
    spec = g.render(st2)
    assert spec["pieces"][0]["owner"] == 1


def test_no_move_loss(g):
    # White: empty pile, one isolated ball -> no legal move -> Black wins.
    st = S({(0, 7, 7): WHITE, (0, 0, 7): BLACK}, to_move=0, pile=(5, 0))
    ns = g.apply_move(st, "0,0,0")
    assert ns.winner == 0, ns.winner
    assert g.returns(ns) == [1.0, -1.0]


def test_repetition_draw(g):
    board = {
        (0, 0, 0): BLACK, (0, 1, 0): BLACK, (0, 0, 1): BLACK,
        (0, 7, 7): WHITE, (0, 6, 7): WHITE, (0, 7, 6): WHITE,
    }
    st = S(board, to_move=0, pile=(0, 0))
    cycle = ["0,1,0>0,1,1", "0,6,7>0,6,6", "0,1,1>0,1,0", "0,6,6>0,6,7"]
    n = 0
    for _ in range(3):
        for mv in cycle:
            assert mv in g.legal_moves(st), (mv, g.legal_moves(st))
            st = g.apply_move(st, mv)
            n += 1
            if st.winner is not None:
                assert st.winner == "draw", st.winner
                assert n >= 8      # one repetition is allowed
                return
    raise AssertionError("repetition draw never fired")


def test_delayed_win(g):
    # White completes a S-N span; it only wins after Black's reply.
    board = {(0, 3, r): WHITE for r in range(7)}
    board[(0, 6, 6)] = BLACK
    board[(0, 6, 5)] = BLACK
    st = S(board, to_move=1)
    ns = g.apply_move(st, "0,3,7")
    assert ns.winner is None                   # span exists but must survive
    ns2 = g.apply_move(ns, "0,6,4")            # Black's harmless reply
    assert ns2.winner == 1, ns2.winner
    assert g.returns(ns2) == [-1.0, 1.0]


def test_reveal_loses_immediately(g):
    # Black's only bridge over White's complete column: moving it away
    # reveals White's connection -> White wins as the ball is lifted.
    board = {(0, 3, r): WHITE for r in range(8)}
    board.update({
        (0, 2, 4): BLACK, (0, 2, 5): BLACK, (0, 4, 4): BLACK,
        (0, 4, 5): BLACK, (0, 5, 4): BLACK,
        (1, 2, 4): BLACK, (1, 3, 4): BLACK,
    })
    st = S(board, to_move=0)
    balls = {_pos(k): v for k, v in st.board.items()}
    assert not _spans(balls, WHITE, 8)         # cut by the level-1 edge
    mv = "1,3,4>0,5,5"
    assert mv in g.legal_moves(st), [m for m in g.legal_moves(st) if ">" in m]
    ns = g.apply_move(st, mv)
    assert ns.winner == 1, ns.winner           # White's connection revealed


def test_break_keeps_playing(g):
    # White places a spanning ball; Black's reply CUTS it -> no win, play on.
    board = {(0, 3, r): WHITE for r in range(7)}
    board.update({
        (0, 2, 4): BLACK, (0, 2, 5): BLACK, (0, 4, 4): BLACK,
        (0, 4, 5): BLACK, (0, 5, 4): BLACK,
        (1, 2, 4): BLACK,                       # one bridge ball pre-placed
    })
    st = S(board, to_move=1)
    ns = g.apply_move(st, "0,3,7")             # White spans...
    assert ns.winner is None                   # ...but must survive the reply
    mv = "0,5,4>1,3,4"                         # Black completes the L1 edge
    assert mv in g.legal_moves(ns), [m for m in g.legal_moves(ns) if ">" in m]
    ns2 = g.apply_move(ns, mv)                 # the over/under cut lands
    assert ns2.winner is None, ns2.winner      # White's win never happened


def test_serialization_roundtrip(g):
    st = S(FIG6_BOARD, to_move=1)
    d = g.serialize(st)
    st2 = g.deserialize(d)
    assert g.serialize(st2) == d
    import json
    json.dumps(d)


def test_random_playouts(g):
    for seed in range(4):
        rng = random.Random(1000 + seed)
        st = g.initial_state()
        n = 0
        while not g.is_terminal(st):
            moves = g.legal_moves(st)
            assert moves, "non-terminal state with no moves"
            st = g.apply_move(st, rng.choice(moves))
            n += 1
            assert n < 700, "runaway game"
        r = g.returns(st)
        assert len(r) == 2 and all(isinstance(x, float) for x in r)


def test_heuristic_shape(g):
    st = g.initial_state()
    st = g.apply_move(st, "0,4,4")
    v = g.heuristic(st)
    assert isinstance(v, list) and len(v) == 2, v
    assert all(-1.0 <= x <= 1.0 for x in v), v


def main():
    g = Akron()
    test_fig2_move_set(g)
    test_fig3_drop_and_cascade(g)
    test_fig5_black_cuts_white(g)
    test_fig6_white_cuts_blacks_cut(g)
    test_overhead_cut()
    test_pbm_five_moves(g)
    test_pbm_won_game(g)
    test_swap(g)
    test_no_move_loss(g)
    test_repetition_draw(g)
    test_delayed_win(g)
    test_reveal_loses_immediately(g)
    test_break_keeps_playing(g)
    test_serialization_roundtrip(g)
    test_heuristic_shape(g)
    test_random_playouts(g)
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
