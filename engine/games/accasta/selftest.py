"""Accasta selftest — pure stdlib.

Anchors (all from the designer's official material):

1. Exact initial setup (article Fig. 1 / official rules): 4 S-H-C towers on
   the back row, 3 S-H towers on b2-b4/f2-f4, single Shields on c3-c4/e3-e4,
   inside the two 9-space castles; 20 pieces a side. Same geometry for Pari.
2. Article Fig. 3a EXACTLY (pixel-read): Shield e5 + Horse b2 (White) with
   Black pieces on f4 and c3 — the shield's 6 destinations (f4 a capture)
   and the horse's 8 (d4 unreachable BEHIND the c3 blocker; c3 a capture).
3. Article Fig. 3b EXACTLY: Chariot c4, own Shield b4, Black piece e5 —
   13 destinations (b4 a friendly landing that blocks a4; e5 a capture that
   blocks f5).
4. Splitting: every k = 1..height is offered; the led group's range is the
   HEAD's (chariot leading 3, etc.).
5. Multiple moves: surfacing a friendly piece allows an optional
   continuation FROM THE SAME ORIGIN ONLY ("done" ends it); surfacing an
   enemy piece (release) ends the turn immediately (Fig. 6 semantics).
6. Safe stacks: no more than 3 pieces of one colour in a resulting stack,
   counting the carried group's pieces of BOTH colours.
7. THE GOLD ANCHOR — full replay of the article's sample game
   Stein-Williams (email, Jan 2004), 23 turns to Black's resignation.
   Every sub-move's piece letters (case = ownership), move type (-/+/x)
   and legality are checked against the printed notation, exercising
   splits, captures, liberations, releases, and 3-colour-limit landings
   (10. e4:Chsxc3 lands 3+3). End position spot-checked.
8. Win conditions: 3 stacks in the enemy castle at the START of your turn
   (article Fig. 8 cells e4/f4/g1; the defender gets one turn and CAN
   defend; the incoming player's check has priority — beginning-of-turn
   semantics), and the 2010 no-legal-move win (safe-stack lockout).
9. Accasta Pari (official variant page): setup, position-dependent power
   min(3, own pieces in stack) evaluated before the move, and the
   documented conflict: the page's notation example "a1:1-c1,+b2" violates
   the 3-pieces rule it says still applies — the rule wins here.
10. Serialization round-trips mid-turn; random playouts terminate.
"""

import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = Path(__file__).resolve().parent
_, G = load_from_dir(PKG)

from games.accasta.game import (  # noqa: E402
    BLACK, CASTLES, WHITE, _alg, _cid, _from_alg,
)


def cid(alg):
    return _cid(_from_alg(alg))


def state_of(board, to_move=WHITE, variant="accasta"):
    """board = {alg: stack string bottom->top, upper=White lower=Black}."""
    return G.deserialize({
        "variant": variant,
        "board": {cid(a): s for a, s in board.items()},
        "to_move": to_move, "cont": None, "last": [], "winner": None,
        "ply": 0, "turn_no": 0, "reps": {},
    })


def mv(frm, to, k=None):
    return f"{cid(frm)}>{cid(to)}" + ("" if k is None else f"={k}")


def dests_from(st, frm):
    pre = cid(frm) + ">"
    out = set()
    for m in G.legal_moves(st):
        if m != "done" and m.startswith(pre):
            out.add(m.split(">")[1].split("=")[0])
    return out


def algs(*names):
    return {cid(n).split(">")[0] for n in names}


# ---------------------------------------------------------------------------
# 1. Initial setup (Fig. 1)
# ---------------------------------------------------------------------------
def test_setup():
    for variant, up in (("accasta", None), ("pari", "P")):
        st = G.initial_state(options={"variant": variant})
        b = G.serialize(st)["board"]
        exp = {}
        for a in ("a1", "a2", "a3", "a4"):
            exp[cid(a)] = "SHC" if up is None else "PPP"
        for a in ("b2", "b3", "b4"):
            exp[cid(a)] = "SH" if up is None else "PP"
        for a in ("c3", "c4"):
            exp[cid(a)] = "S" if up is None else "P"
        for a in ("g1", "g2", "g3", "g4"):
            exp[cid(a)] = "shc" if up is None else "ppp"
        for a in ("f2", "f3", "f4"):
            exp[cid(a)] = "sh" if up is None else "pp"
        for a in ("e3", "e4"):
            exp[cid(a)] = "s" if up is None else "p"
        assert b == exp, (variant, b)
        n = sum(len(s) for s in b.values())
        assert n == 40
        assert G.current_player(st) == WHITE
        assert G.legal_moves(st)
        assert not G.is_terminal(st)
    assert len(CASTLES[0]) == len(CASTLES[1]) == 9


# ---------------------------------------------------------------------------
# 2./3. Article Figs. 3a and 3b — exact move sets
# ---------------------------------------------------------------------------
def test_fig3a():
    st = state_of({"e5": "S", "b2": "H", "f4": "s", "c3": "s"})
    # Shield e5: all six neighbours, f4 being a capture.
    assert dests_from(st, "e5") == algs("e4", "e6", "d5", "d6", "f5", "f4")
    # Horse b2: up to 2; d4 is NOT reachable (c3 blocks the ray), c3 capture.
    assert dests_from(st, "b2") == algs("b1", "b3", "b4", "a1", "a2",
                                        "c2", "d2", "c3")
    # Nothing else moves, all single pieces -> bare from>to strings.
    assert all("=" not in m for m in G.legal_moves(st))
    assert len(G.legal_moves(st)) == 6 + 8


def test_fig3b():
    st = state_of({"c4": "C", "b4": "S", "e5": "s"})
    assert dests_from(st, "c4") == algs(
        "c1", "c2", "c3", "c5", "c6",     # along the row
        "b3", "a2",                        # one diagonal
        "b4",                              # friendly landing; a4 blocked
        "d4", "e3", "f2",                  # toward Black
        "d5", "e5")                        # e5 a capture; f5 blocked
    assert cid("a4") not in dests_from(st, "c4")
    assert cid("f5") not in dests_from(st, "c4")


# ---------------------------------------------------------------------------
# 4. Splitting: k choices, head's range
# ---------------------------------------------------------------------------
def test_split_choices():
    st = state_of({"d4": "SHC", "g4": "s"})
    moves = [m for m in G.legal_moves(st) if m.startswith(cid("d4"))]
    # Chariot head: 18 destinations (6 rays x 3), each with k = 1, 2, 3.
    assert len(moves) == 54
    for k in (1, 2, 3):
        assert mv("d4", "d1", k) in moves          # 3 straight west
        assert mv("d4", "g1", k) in moves          # 3 toward Black's corner
    assert mv("d4", "d1", 4) not in moves


# ---------------------------------------------------------------------------
# 5. Continuation / release / done
# ---------------------------------------------------------------------------
def test_continuation_and_release():
    # d4 = black shield under white Horse under white Chariot.
    st0 = state_of({"d4": "sHC", "g4": "s"})
    st = G.apply_move(st0, mv("d4", "d5", 1))       # Chariot off the top
    assert G.current_player(st) == WHITE            # friendly H surfaced
    lm = G.legal_moves(st)
    assert "done" in lm
    assert all(m == "done" or m.startswith(cid("d4") + ">") for m in lm)
    # serialization round-trips mid-turn
    d = G.serialize(st)
    assert d["cont"] == cid("d4")
    assert G.serialize(G.deserialize(d)) == d
    # moving the Horse now RELEASES the black shield -> turn over at once
    st2 = G.apply_move(st, mv("d4", "c4", 1))
    assert G.current_player(st2) == BLACK
    assert G.serialize(st2)["cont"] is None
    assert G.serialize(st2)["board"][cid("d4")] == "s"
    # ... or the player may just stop
    st3 = G.apply_move(st, "done")
    assert G.current_player(st3) == BLACK
    assert G.serialize(st3)["board"][cid("d4")] == "sH"

    # Fig. 6: three pieces moved in one turn, all from the same origin.
    st = state_of({"d4": "SHC", "g4": "s"})
    st = G.apply_move(st, mv("d4", "e4", 1))
    assert G.current_player(st) == WHITE
    st = G.apply_move(st, mv("d4", "c4", 1))
    assert G.current_player(st) == WHITE
    st = G.apply_move(st, mv("d4", "d5"))           # single piece: bare move
    assert G.current_player(st) == BLACK            # origin emptied
    b = G.serialize(st)["board"]
    assert (b[cid("e4")], b[cid("c4")], b[cid("d5")]) == ("C", "H", "S")


# ---------------------------------------------------------------------------
# 6. Safe stacks (3 of a colour)
# ---------------------------------------------------------------------------
def test_safe_stacks():
    st = state_of({"d4": "SSS", "d5": "S", "d7": "s"})
    assert mv("d5", "d4") not in G.legal_moves(st)   # 4 white: forbidden
    assert mv("d5", "d6") in G.legal_moves(st)
    st = state_of({"d4": "SSS", "d3": "s", "a1": "S"}, to_move=BLACK)
    assert mv("d3", "d4") in G.legal_moves(st)       # capture: 3W+1b is fine
    # The carried group's pieces count too: black head carrying a white piece
    st = state_of({"d5": "Ss", "d4": "SSS", "g4": "s"}, to_move=BLACK)
    assert mv("d5", "d4", 2) not in G.legal_moves(st)  # would make 4 white
    assert mv("d5", "d4", 1) in G.legal_moves(st)      # lone black is fine


# ---------------------------------------------------------------------------
# 7. GOLD ANCHOR — the article's sample game (Stein-Williams, 2004)
# ---------------------------------------------------------------------------
SAMPLE_GAME = """
a1:C+b2,HS-c1    g2:C+f2,H+f3
b2:CHS-c2        f2:Cxc1,HS-e2
c2:Cxc1,H+c3,S-d2   e2:Hxc3,S-d3
c1:Cc+d2,HS-b1   f3:H+e4,H-f2,S+e3
d2:Cc-d1,Sxd3    c3:Hhsxd3
b3:H+c4,S-c3     d3:Hhss-c2,Sxc3
a4:CHS-b5        c3:Ssxc4
b5:Cxe4,HS-d5    e3:S-d3,S-d4
a3:Cxd3,HS-c3    d4:Sxc3
e4:Chsxc3        f4:H-d4,S-e4
d5:Hxd4,Sxe4     g1:Cxd1,HS-e1
d3:Cxg3
"""

SUB_RE = re.compile(r"^([SHCshc]+)([-+x])([a-g][1-7])$")


def test_sample_game():
    st = G.initial_state(options={"variant": "accasta"})
    turns = SAMPLE_GAME.split()
    for tno, turn in enumerate(turns):
        mover = G.current_player(st)
        assert mover == tno % 2, (tno, turn)
        origin_alg, subs = turn.split(":")
        origin = _from_alg(origin_alg)
        for sub in subs.split(","):
            m = SUB_RE.match(sub)
            assert m, sub
            letters, sym, tgt_alg = m.groups()
            k = len(letters)
            stack = st.board[origin]
            got = "".join(kind if o == mover else kind.lower()
                          for (o, kind) in reversed(stack[-k:]))
            assert got == letters, (turn, sub, got)
            tgt = st.board.get(_from_alg(tgt_alg))
            want = "-" if tgt is None else (
                "+" if tgt[-1][0] == mover else "x")
            assert want == sym, (turn, sub, want)
            move = mv(origin_alg, tgt_alg,
                      None if len(stack) == 1 else k)
            assert move in G.legal_moves(st), (turn, sub, move)
            assert G.describe_move(st, move) == f"{origin_alg}:{sub}"
            st = G.apply_move(st, move)
            assert not G.is_terminal(st), (turn, sub)
        if G.current_player(st) == mover:      # notation stopped early
            assert "done" in G.legal_moves(st)
            st = G.apply_move(st, "done")
        assert G.current_player(st) == 1 - mover, turn

    # Position after 12. d3:Cxg3 (Black resigned here):
    b = G.serialize(st)["board"]
    assert b[cid("g3")] == "shcC"     # White's chariot tops the g3 tower
    assert b[cid("d1")] == "cCc"      # Black's chariot liberated at d1
    assert b[cid("c3")] == "SHsshC"   # the 3+3 tower from 10. e4:Chsxc3
    assert b[cid("e4")] == "sS"
    assert b[cid("d4")] == "hH"
    assert b[cid("d3")] == "s"        # the released shield ended the turn
    assert b[cid("c2")] == "SSHh"
    assert b[cid("b1")] == "SH"
    assert b[cid("e1")] == "sh"
    assert cid("b5") not in b and cid("e2") not in b
    # White controls two stacks in Black's castle (e4, g3) — "one step ahead"
    assert sum(1 for c in CASTLES[BLACK]
               if _cid(c) in b and b[_cid(c)][-1].isupper()) == 2
    assert not G.is_terminal(st)


# ---------------------------------------------------------------------------
# 8. Win conditions
# ---------------------------------------------------------------------------
def test_castle_win_fig8():
    # Article Fig. 8: White wins with stacks on e4, f4 and g1.
    st = state_of({"e4": "S", "f4": "S", "d1": "C", "d7": "s"})
    st = G.apply_move(st, mv("d1", "g1"))      # third stack enters
    assert not G.is_terminal(st)               # Black gets one turn to defend
    st = G.apply_move(st, mv("d7", "d6"))      # ... and fails to
    assert G.is_terminal(st)
    assert G.returns(st) == [1.0, -1.0]

    # The defender CAN defend by capturing one of the three.
    st = state_of({"e4": "S", "f4": "S", "d1": "C", "f5": "h"})
    st = G.apply_move(st, mv("d1", "g1"))
    st = G.apply_move(st, mv("f5", "f4"))      # capture: only 2 remain
    assert not G.is_terminal(st)

    # Beginning-of-turn priority: the incoming player's check comes first.
    st = state_of({"e4": "S", "f4": "S", "d1": "C",
                   "a1": "c", "a2": "c", "b2": "c"})
    st = G.apply_move(st, mv("d1", "g1"))      # White also reaches three...
    assert G.is_terminal(st)                   # ...but Black's turn begins
    assert G.returns(st) == [-1.0, 1.0]


def test_no_move_win():
    # Black's lone shield is locked out by the safe-stack rule (2010 rule).
    lock = "sssS"                              # 3 black prisoners, white head
    st = state_of({"d7": "s", "c6": lock, "d6": lock, "e6": lock,
                   "a1": "S"})
    st = G.apply_move(st, mv("a1", "a2"))
    assert G.is_terminal(st)
    assert G.returns(st) == [1.0, -1.0]


# ---------------------------------------------------------------------------
# 9. Accasta Pari
# ---------------------------------------------------------------------------
def test_pari_power():
    # Head's power = min(3, own-colour pieces in the stack), pre-move.
    st = state_of({"d4": "PPP", "g4": "p"}, variant="pari")
    lm = G.legal_moves(st)
    assert mv("d4", "d1", 3) in lm and mv("d4", "d1", 1) in lm
    st = state_of({"d4": "pPP", "g4": "p"}, variant="pari")
    lm = G.legal_moves(st)
    assert mv("d4", "d2", 1) in lm             # distance 2: power 2
    assert mv("d4", "d1", 1) not in lm         # distance 3: too far
    st = state_of({"d4": "ppP", "g4": "p"}, variant="pari")
    lm = G.legal_moves(st)
    assert mv("d4", "d3", 1) in lm             # distance 1 only
    assert mv("d4", "d2", 1) not in lm


def test_pari_opening_and_3rule():
    st = G.initial_state(options={"variant": "pari"})
    # Official page's opening example, first half: one piece a1 -> c1
    # (the head's power is 3 — three friendly pieces — before the move).
    m1 = mv("a1", "c1", 1)
    assert m1 in G.legal_moves(st)
    assert G.describe_move(st, m1) == "a1:1-c1"
    st = G.apply_move(st, m1)
    assert G.current_player(st) == WHITE       # friendly piece surfaced
    lm = G.legal_moves(st)
    # The example's second half ("+b2", two pieces onto b2) would make FOUR
    # white pieces — it contradicts the 3-pieces rule the same page keeps,
    # so it must NOT be legal (documented in rules.md). One piece is fine.
    assert mv("a1", "b2", 2) not in lm
    assert mv("a1", "b2", 1) in lm
    st = G.apply_move(st, mv("a1", "b1", 2))   # legal alternative: to b1
    assert G.current_player(st) == BLACK
    assert G.serialize(st)["board"][cid("b1")] == "PP"


# ---------------------------------------------------------------------------
# 10. Random playouts terminate (draw backstops)
# ---------------------------------------------------------------------------
def test_random_termination():
    for variant, games in (("accasta", 8), ("pari", 5)):
        for seed in range(games):
            rng = random.Random(1000 + seed)
            st = G.initial_state(options={"variant": variant})
            steps = 0
            while not G.is_terminal(st):
                st = G.apply_move(st, rng.choice(G.legal_moves(st)))
                steps += 1
                assert steps < 6000, (variant, seed)
            r = G.returns(st)
            assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)


def main():
    tests = [
        test_setup, test_fig3a, test_fig3b, test_split_choices,
        test_continuation_and_release, test_safe_stacks, test_sample_game,
        test_castle_win_fig8, test_no_move_win, test_pari_power,
        test_pari_opening_and_3rule, test_random_termination,
    ]
    for t in tests:
        t()
        print(f"  ok: {t.__name__}")
    print("accasta selftest: all tests passed")


if __name__ == "__main__":
    main()
