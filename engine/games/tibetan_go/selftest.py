"""Tibetan Go (Mig-mang) correctness anchors (pure stdlib).

Pins the deltas over plain Go:
1. the fixed 17x17 twelve-stone third-line setup (from the 2005 exhibition
   SGF header) with White to move, plus its structural invariants;
2. the vacated-point ban -- ko, snapback and multi-stone captures all ban the
   just-vacated points for exactly one opposing move;
3. area scoring with the corner (+40 pt / 20 zi) and centre (+10 pt / 5 zi)
   bonuses, via both occupation and territory-containment, and the honest draw;
4. a full replay of the played-out professional exhibition game
   Jiang Zhujiu 9d (W) vs Yue Liang 4d (B), Shangri-la 2005, RE W+0.5 zi
   (GoGoD New In Go, TibetanGo2.sgf) -- every one of its 217 moves must be
   legal under this engine.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.tibetan_go.game import (  # noqa: E402
    TibetanGo, TState, _board_key, _score, BLACK, WHITE, SIZE,
    SETUP_BLACK, SETUP_WHITE, CORNERS, CENTRE,
)

G = TibetanGo()


def _state(board, to_move, passes=0):
    s = TState(board=dict(board), to_move=to_move, passes=passes)
    s.history = frozenset({_board_key(s.board)})
    return s


def test_setup():
    s = G.initial_state()
    assert SIZE == 17 and len(s.board) == 12
    assert {p for p, v in s.board.items() if v == BLACK} == set(SETUP_BLACK)
    assert {p for p, v in s.board.items() if v == WHITE} == set(SETUP_WHITE)
    assert G.current_player(s) == WHITE                  # White plays first
    # all stones on the third line
    assert all(2 in (c, r) or 14 in (c, r) for c, r in s.board)
    # 3-3 corner points alternate in colour
    assert s.board[(2, 2)] == s.board[(14, 14)] == BLACK
    assert s.board[(14, 2)] == s.board[(2, 14)] == WHITE
    # 90-degree rotation is a colour swap: (c,r) -> (r, 16-c)
    assert {(r, 16 - c) for c, r in SETUP_BLACK} == set(SETUP_WHITE)


def test_ko_ban():
    """(b) simple ko: immediate recapture is illegal, legal after one
    intervening exchange, and the counter-recapture is then banned in turn."""
    board = {(5, 4): BLACK, (4, 5): BLACK, (5, 6): BLACK,
             (5, 5): WHITE, (6, 4): WHITE, (7, 5): WHITE, (6, 6): WHITE}
    s = _state(board, BLACK)
    assert "6,5" in G.legal_moves(s)
    s = G.apply_move(s, "6,5")                           # B takes the ko
    assert (5, 5) not in s.board and s.banned == {(5, 5)}
    assert "5,5" not in G.legal_moves(s)                 # W: no immediate retake
    s = G.apply_move(s, "0,10")                          # W elsewhere
    s = G.apply_move(s, "0,12")                          # B answers
    assert s.banned == frozenset()                       # ban lasted one move only
    assert "5,5" in G.legal_moves(s)
    s = G.apply_move(s, "5,5")                           # W retakes the ko
    assert (6, 5) not in s.board and s.board[(5, 5)] == WHITE
    assert "6,5" not in G.legal_moves(s)                 # B banned in turn


def test_snapback_and_multistone_ban():
    """(c) snapback must be delayed one move; (d) the 4-stone recapture then
    bans ALL vacated points for exactly one move."""
    board = {(2, 0): WHITE, (2, 1): WHITE, (3, 1): WHITE,
             (3, 0): BLACK,                              # the throw-in stone
             (1, 0): BLACK, (1, 1): BLACK, (2, 2): BLACK, (3, 2): BLACK,
             (4, 1): BLACK, (5, 0): BLACK}
    s = _state(board, WHITE)
    s = G.apply_move(s, "4,0")                           # W captures the throw-in
    assert (3, 0) not in s.board and s.banned == {(3, 0)}
    # W's group {(2,0),(2,1),(3,1),(4,0)} now has (3,0) as its ONLY liberty:
    # in plain go Black snaps back at once; here it is banned for one move.
    assert "3,0" not in G.legal_moves(s)
    s = G.apply_move(s, "10,10")                         # B must wait
    s = G.apply_move(s, "12,10")                         # W (does not fix it)
    assert "3,0" in G.legal_moves(s)
    s = G.apply_move(s, "3,0")                           # delayed snapback
    vacated = {(2, 0), (2, 1), (3, 1), (4, 0)}
    assert s.banned == vacated and s.board[(3, 0)] == BLACK
    assert all((p not in s.board) for p in vacated)
    lm = set(G.legal_moves(s))                           # W to move under the ban
    assert all(f"{c},{r}" not in lm for c, r in vacated)
    s = G.apply_move(s, "12,12")                         # W elsewhere
    s = G.apply_move(s, "10,12")                         # B elsewhere
    lm = set(G.legal_moves(s))                           # ban lapsed after one move
    assert s.banned == frozenset()
    # three of the vacated points are open to White again; (4,0) stays out,
    # but for the ordinary reason -- it is now a one-point suicide.
    assert all(f"{c},{r}" in lm for c, r in vacated - {(4, 0)})
    assert "4,0" not in lm


def test_scoring_bonuses():
    C = SIZE - 1
    # containment: one Black stone owns the whole board -> corners AND centre
    # controlled by territory -> +40 +10.
    s = _state({(8, 0): BLACK}, WHITE, passes=2)
    assert _score(s.board) == (SIZE * SIZE + 50, 0, [50, 0])
    assert G.returns(s) == [1.0, -1.0]
    # occupation: Black stones ON the four 1-1 points, White holds the centre
    # -> +40 for Black, no centre bonus for anyone (it is contingent on the
    # corner bonus), rest of the board neutral.
    s = _state({p: BLACK for p in CORNERS} | {CENTRE: WHITE}, WHITE, passes=2)
    assert _score(s.board) == (44, 1, [40, 0])
    # mixed: Black walls on columns 3 and 13 -> corners by containment; White
    # wall on column 8 occupies the centre -> Black +40 only.
    board = {(3, r): BLACK for r in range(SIZE)}
    board |= {(13, r): BLACK for r in range(SIZE)}
    board |= {(8, r): WHITE for r in range(SIZE)}
    s = _state(board, WHITE, passes=2)
    assert _score(s.board) == (34 + 51 + 51 + 40, 17, [40, 0])
    # same but Black also takes the centre point -> +50.
    board[(8, 8)] = BLACK
    s = _state(board, WHITE, passes=2)
    assert _score(s.board) == (35 + 51 + 51 + 50, 16, [50, 0])
    # honest draw: symmetric position, komi 0, no bonuses -> equal totals.
    board = {(3, r): BLACK for r in range(SIZE)}
    board |= {(13, r): WHITE for r in range(SIZE)}
    s = _state(board, WHITE, passes=2)
    assert _score(s.board) == (68, 68, [0, 0])
    assert G.returns(s) == [0.0, 0.0]


# Jiang Zhujiu 9d (W) vs Yue Liang 4d (B), 1st Shangri-la Tibetan Board Game
# Festival, Diqing 2005-06, RU[Tibetan] RE[W+0.5 zi]. SGF coords (a=0, row 0
# top), strict W/B alternation, White first. Source: GoGoD New In Go part 4,
# http://web.archive.org/web/2017/http://www.gogod.co.uk/NewInGo/sgf/TibetanGo2.sgf
PRO_GAME = (
    "pn on pm dn do eo ep en fp fd gd ge he fc id nd od nc ne oe nb me nf pe mb "
    "lc ng ob pb pc oa pd ob oh mc md ld lf kd kg fb eb gb km mm ln mn mo lo mp "
    "po pp om jo kn jn lm kp nh ni lh oj mi nk kl jm mj pk ih ji pi nj jh mk lk "
    "lj kj ki li kh ik ii hi hh gi hg gg jk jl hj ij hf if je gf jd gh lb jb jc "
    "ib ma cn cm bd bc cd dd de bn db ce dc ed be cb ab ch bg dh eg gk jj ba ac "
    "bb da ea bo lg gl fk hk lp fl ek bm bl an dl oi of pj ol mh ph gj hm hl gp "
    "ee ec fe ca ka la db bh eh ag cf ei nn op ln ic af ah jf kb hc ja ia fi ml "
    "nl pl qi gn hn fo fn gm dp cp qo nm qj qn qp ip jp ho hp ie ql fj ej qb jg "
    "ig ke no np gq io dq hq fq fh fg dg df al am im ka"
).split()


def test_pro_game_replay():
    s = G.initial_state()
    captures = ban_plies = 0
    for i, mv in enumerate(PRO_GAME):
        assert G.current_player(s) == (WHITE if i % 2 == 0 else BLACK)
        c, r = ord(mv[0]) - 97, ord(mv[1]) - 97
        if s.banned:
            ban_plies += 1
            assert (c, r) not in s.banned, f"move {i + 1} plays a banned point"
        # the game's own single legality predicate, every ply...
        assert G._placement(s, c, r) is not None, f"move {i + 1} {mv} illegal"
        # ...and full legal_moves membership on a sample (kept cheap)
        if i % 25 == 0 or i >= 210:
            assert f"{c},{r}" in G.legal_moves(s), f"move {i + 1} not offered"
        s = G.apply_move(s, f"{c},{r}")
        if s.banned:
            captures += 1
    assert len(PRO_GAME) == 217 and captures == 15 and ban_plies == 14
    # W[db] and W[ka] are each played twice -- both replays are of points
    # vacated by an earlier capture, delayed past the one-move ban.
    # The record stops before a Tromp-Taylor-clean end (dame and dead stones
    # remain -> 36 neutral points), so we do NOT pin the recorded 0.5 zi
    # margin; after two closing passes raw area scoring still agrees with the
    # recorded WINNER (White), with no corner bonus for either side.
    s = G.apply_move(s, "pass")
    s = G.apply_move(s, "pass")
    assert G.is_terminal(s)
    b, w, bonus = _score(s.board)
    assert (b, w, bonus) == (121, 132, [0, 0])
    assert G.returns(s) == [-1.0, 1.0]                   # White wins, as recorded


def main():
    test_setup()
    test_ko_ban()
    test_snapback_and_multistone_ban()
    test_scoring_bonuses()
    test_pro_game_replay()
    print("tibetan_go selftest OK")


if __name__ == "__main__":
    main()
