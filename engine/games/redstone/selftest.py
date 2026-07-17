"""Redstone selftest -- anchors every worked example in Mark Steere's rule sheet
(marksteeregames.com/Redstone_rules.pdf, Feb 2012) plus win/loss and invariant
probes. Pure stdlib.

Figure coordinates were read from the PDF's diagrams at 400 dpi; (c,r) with
r increasing downward exactly as in the sheet's figures.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir            # noqa: E402

PKG = Path(__file__).resolve().parent
_man, G = load_from_dir(PKG)

gm = sys.modules[G.__class__.__module__]
BLACK, WHITE, RED = gm.BLACK, gm.WHITE, gm.RED
RState, _groups = gm.RState, gm._groups


def state(size, black=(), white=(), red=(), to_move=BLACK, ply=None):
    board = {}
    for p in black:
        board[p] = BLACK
    for p in white:
        board[p] = WHITE
    for p in red:
        board[p] = RED
    if ply is None:
        ply = len(board) + 2   # past the pie-rule window
    return RState(size=size, board=board, to_move=to_move, ply=ply)


def board_of(s):
    b = {p for p, v in s.board.items() if v == BLACK}
    w = {p for p, v in s.board.items() if v == WHITE}
    r = {p for p, v in s.board.items() if v == RED}
    return b, w, r


# ---------------------------------------------------------------- Figure 1
# "Four groups, 18 liberties."
def test_fig1():
    black = {(1, 2), (2, 3), (0, 3), (0, 4), (1, 4), (1, 5)}
    white = {(4, 2), (5, 2), (6, 2), (4, 3), (3, 4), (4, 4)}
    s = state(7, black, white)
    gs = _groups(s.board, s.size)
    assert len(gs) == 4, f"fig1: expected 4 groups, got {len(gs)}"
    libs = set()
    for _col, _cells, glibs in gs:
        libs |= set(glibs)
    assert len(libs) == 18, f"fig1: expected 18 distinct liberties, got {len(libs)}"
    sizes = sorted(len(c) for _col, c, _l in gs)
    assert sizes == [1, 1, 4, 6], sizes


# ---------------------------------------------------------------- Figure 2
# Black captures the two-stone white group with a red stone at (4,2).
def test_fig2():
    black = {(3, 0), (2, 1), (4, 1), (2, 2), (3, 3)}
    white = {(3, 1), (3, 2), (0, 2), (0, 3), (1, 4)}
    s = state(5, black, white, to_move=BLACK)
    lm = set(G.legal_moves(s))
    assert "4,2=red" in lm, "fig2: red capture at 4,2 must be legal"
    # filling the white group's last liberty with a black stone is a capturing
    # placement -> only red may do it
    assert "4,2=black" not in lm, "fig2: black stone on 4,2 must be illegal"
    s2 = G.apply_move(s, "4,2=red")
    b, w, r = board_of(s2)
    assert b == black, "fig2: black stones must be untouched"
    assert w == {(0, 2), (0, 3), (1, 4)}, f"fig2: white group not removed: {w}"
    assert r == {(4, 2)}, r
    assert s2.winner is None and s2.to_move == WHITE


# ---------------------------------------------------------------- Figure 3
# White's red stone at (2,3) captures ONE white group and TWO black groups
# simultaneously ("unlike Go": your own temporarily-bounded group dies too).
def test_fig3():
    black = {(3, 0), (0, 2), (0, 3), (1, 3), (3, 3), (4, 3), (0, 4), (4, 4)}
    white = {(0, 1), (1, 2), (3, 2), (4, 2), (1, 4), (2, 4), (3, 4)}
    s = state(5, black, white, to_move=WHITE)
    assert "2,3=red" in G.legal_moves(s)
    s2 = G.apply_move(s, "2,3=red")
    b, w, r = board_of(s2)
    assert b == {(3, 0)}, f"fig3: expected lone black at (3,0), got {b}"
    assert w == {(0, 1), (1, 2), (3, 2), (4, 2)}, f"fig3: white after = {w}"
    assert r == {(2, 3)}, r
    assert s2.winner is None, "fig3: both sides still have stones"


# ---------------------------------------------------------------- Figure 4
# On the green point (0,2) Black may play EITHER black (joins his groups, no
# capture) OR red (self-captures his upper two-stone group).
def test_fig4():
    black = {(0, 0), (0, 1), (0, 3)}
    white = {(1, 0), (1, 1), (5, 4)}
    red = {(1, 2)}
    s = state(7, black, white, red, to_move=BLACK)
    lm = set(G.legal_moves(s))
    assert "0,2=black" in lm and "0,2=red" in lm, "fig4: both colours legal on green"
    # red: self-capture of the upper black group only
    s2 = G.apply_move(s, "0,2=red")
    b, w, r = board_of(s2)
    assert b == {(0, 3)}, f"fig4 red: expected only (0,3) black left, got {b}"
    assert w == white and r == {(1, 2), (0, 2)}
    assert s2.winner is None
    # black: joins the groups, captures nothing
    s3 = G.apply_move(s, "0,2=black")
    b, w, r = board_of(s3)
    assert b == {(0, 0), (0, 1), (0, 2), (0, 3)} and w == white and r == {(1, 2)}
    assert s3.winner is None


# ---------------------------------------------------------------- Figure 5
# Black can place a stone of NO colour on either green spot ((1,4) and (0,6)):
# a black stone would itself be a bounded group, and a red stone there bounds
# nothing. Black can play black on every other empty point, and red nowhere.
def test_fig5():
    black = {(2, 3), (4, 3), (3, 4), (5, 4), (3, 5), (4, 5), (2, 6), (3, 6)}
    white = {(1, 2), (1, 3), (0, 4), (2, 4), (0, 5), (1, 5), (2, 5), (1, 6)}
    s = state(7, black, white, to_move=BLACK)
    lm = set(G.legal_moves(s))
    assert not any(m.endswith("=red") for m in lm), "fig5: no red placement exists"
    for green in ("1,4", "0,6"):
        assert f"{green}=black" not in lm and f"{green}=red" not in lm, \
            f"fig5: green spot {green} must be unplayable for Black"
    empties = 7 * 7 - len(black) - len(white)
    blacks = {m for m in lm if m.endswith("=black")}
    assert len(blacks) == empties - 2, \
        f"fig5: Black should have {empties - 2} placements, got {len(blacks)}"


# ------------------------------------------------------- win / loss / no-draw
def test_annihilation_win():
    # Black red-captures White's last group -> Black wins.
    s = state(5, black={(1, 0)}, white={(0, 0)}, to_move=BLACK)
    s2 = G.apply_move(s, "0,1=red")
    assert s2.winner == BLACK and G.is_terminal(s2)
    assert G.returns(s2) == [1.0, -1.0]
    assert G.legal_moves(s2) == []


def test_self_annihilation_loss():
    # Black self-captures his only group while White remains -> Black loses.
    s = state(5, black={(0, 0)}, white={(1, 0), (3, 3)}, to_move=BLACK)
    lm = set(G.legal_moves(s))
    assert "0,1=red" in lm
    s2 = G.apply_move(s, "0,1=red")
    assert s2.winner == WHITE
    assert G.returns(s2) == [-1.0, 1.0]


def test_double_annihilation_mover_wins():
    # One red stone removes ALL black and white stones -> the mover wins
    # ("If your placement eliminates all black and white stones ... you win").
    black = {(0, 0)}
    white = {(0, 2)}
    red = {(1, 0), (1, 2), (0, 3)}
    s = state(4, black, white, red, to_move=WHITE)
    lm = set(G.legal_moves(s))
    assert "0,1=red" in lm, lm
    s2 = G.apply_move(s, "0,1=red")
    b, w, r = board_of(s2)
    assert b == set() and w == set()
    assert s2.winner == WHITE, "both armies annihilated: the mover wins"


def test_red_only_forced_loss():
    # QA pin: a position where Black's ONLY legal move is a red stone -- and
    # that forced move self-annihilates his army, losing.  The same position
    # gives White an own-colour move Black lacks (per-colour asymmetry): (3,3)
    # is a suicide point for Black but a legal join for White, while (1,0) is
    # red-only for both.
    black = {(0, 0)}
    white = {(2, 0), (1, 1), (0, 1), (0, 2), (0, 3), (1, 2), (1, 3),
             (2, 1), (2, 2), (2, 3), (3, 0), (3, 1), (3, 2)}
    s = state(4, black, white, to_move=BLACK)
    assert G.legal_moves(s) == ["1,0=red"], G.legal_moves(s)
    s2 = G.apply_move(s, "1,0=red")
    assert s2.winner == WHITE and G.returns(s2) == [-1.0, 1.0]
    sw = state(4, black, white, to_move=WHITE)
    assert sorted(G.legal_moves(sw)) == ["1,0=red", "3,3=white"]


# ------------------------------------------------------------------ pie rule
def test_pie_rule():
    s0 = G.initial_state({"size": 7})
    assert "swap" not in G.legal_moves(s0), "no swap on Black's first move"
    s1 = G.apply_move(s0, "3,3=black")
    lm1 = G.legal_moves(s1)
    assert "swap" in lm1
    assert all(m == "swap" or m.endswith("=white") or m.endswith("=red")
               for m in lm1)
    s2 = G.apply_move(s1, "swap")
    assert s2.board == {(3, 3): WHITE}, "swap: White takes over the opening stone"
    assert s2.to_move == BLACK and s2.winner is None and s2.swapped
    assert "swap" not in G.legal_moves(s2), "swap is one-shot"
    s2b = G.apply_move(s1, "0,0=white")
    assert "swap" not in G.legal_moves(s2b), "swap only on move 2"


# -------------------------------------------------- random-play invariant sweep
def test_random_games():
    rng = random.Random(20120212)
    for size in (5, 5, 5, 7, 7, 9):
        for _ in range(4):
            s = G.initial_state({"size": size})
            plies = 0
            while not G.is_terminal(s):
                lm = G.legal_moves(s)
                assert lm, "non-terminal state with no legal moves"
                prev_board = dict(s.board)
                mv = rng.choice(lm)
                s = G.apply_move(s, mv, rng)
                plies += 1
                assert plies <= size * size * (size * size + 1), "unbounded game"
                if mv == "swap":
                    continue
                removed = set(prev_board) - set(s.board)
                if mv.endswith("=red"):
                    assert removed, "a red placement must capture something"
                else:
                    assert not removed, "an own-stone placement never captures"
                assert all(prev_board[p] != RED for p in removed), \
                    "red stones are permanent"
                # no bounded group may survive a placement
                for _col, _cells, libs in _groups(s.board, s.size):
                    assert libs, "a liberty-less group survived"
            assert s.winner in (BLACK, WHITE), "Redstone has no draws"
            ret = G.returns(s)
            assert sorted(ret) == [-1.0, 1.0]
            # serialize round-trip on the final state
            assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)


# ------------------------------------------------------- heuristic shape (SPEC)
def test_heuristic_shape():
    from agp.mcts import MCTSBot
    s = G.initial_state({"size": 7})
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2
    bot = MCTSBot(random.Random(1), iterations=20, max_rollout=4)
    mv = bot.select(G, s)                       # forces the rollout cutoff path
    assert mv in G.legal_moves(s)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"redstone selftest: {len(tests)} checks passed")


if __name__ == "__main__":
    main()
