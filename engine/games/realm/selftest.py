"""Realm selftest — pure stdlib.

Anchors (all from the authoritative Abstract Games #9 article by Mikulas):

1. THE GOLD ANCHOR — full replay of the article's complete sample game
   (set-up 1.Bh11 Bh2 ... 6.Pc4 Pc9, then turns 7-16).  Every sub-move must
   be legal, every parenthesised Special Event must fire EXACTLY as
   annotated (base creations, enforcer creations with facing, base captures,
   immobilizations — and nothing else), the intermediate positions must
   match the article's Figure 6 (after turn 9) and Figure 7 (after turn 12)
   pixel-read from the magazine scan, and 16.Pe7e6(Be5) must end the game
   at White's 12th created Base with White the winner (Realms 8:7).

2. The mid-article worked example: the Figure 3 set-up (b11-e8-h5 vs
   h8-e5-b2), White's Concentration into h11, Black's into h2 (position =
   Figure 4), then White's Dispersal from h11 (position = Figure 5).
   (Note: the article's sample game and Figure 3 are two DIFFERENT games —
   Figures 3-5 belong to the worked example, Figures 6-7 to the sample
   game.)

3. The article's combinatorial claim: exactly 16 distinct ways to place
   one player's 3 Bases under the placement rule, up to the board's 8
   symmetries (96 raw sets).

4. Constructed rule checks: enforcer never reverses; Powers can't end on a
   Center / must change Realm; immobilization & capture arithmetic
   (+1 vs +2 Powers, event 3 vs event 4 exclusivity, multi-candidate
   choice); dispersal/concentration turn consistency; rearrangement swap +
   per-piece different-space + three-turns-in-a-row ban; double-pass
   honest draw; serialization round-trips mid-turn; random playouts
   terminate.
"""

import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

PKG = Path(__file__).resolve().parent
_, G = load_from_dir(PKG)

from games.realm.game import RState, MAX_PLY  # noqa: E402


def cell(alg):
    m = re.fullmatch(r"([a-l])(\d{1,2})", alg)
    assert m, alg
    return (ord(m.group(1)) - ord("a"), int(m.group(2)) - 1)


def cid(alg):
    c = cell(alg)
    return f"{c[0]},{c[1]}"


def board_from(spec):
    """spec = {owner: {"B": "h11 e8", "P": "...", "E": [("d4","W",True), ...]}}"""
    b = {}
    for owner, kinds in spec.items():
        for a in kinds.get("B", "").split():
            b[cell(a)] = (owner, "B", None, False)
        for a in kinds.get("P", "").split():
            b[cell(a)] = (owner, "P", None, True)
        for a, d, mobile in kinds.get("E", []):
            b[cell(a)] = (owner, "E", d, mobile)
    return b


def assert_board(st, spec, label):
    exp = board_from(spec)
    if st.board != exp:
        extra = {k: v for k, v in st.board.items() if exp.get(k) != v}
        missing = {k: v for k, v in exp.items() if st.board.get(k) != v}
        raise AssertionError(f"{label}: board mismatch\n unexpected: {extra}\n"
                             f" missing: {missing}")


TOKEN = re.compile(r"([PE])([a-l]\d{1,2})([a-l]\d{1,2})(?:\((.*)\))?")


def play_token(st, token, mover):
    """Apply one article token like Pi10i6(Bh5) and verify its events exactly."""
    m = TOKEN.fullmatch(token)
    assert m, token
    src, dst = cell(m.group(2)), cell(m.group(3))
    assert st.board[src][1] == m.group(1), f"{token}: wrong piece at source"
    ann = [a for a in (m.group(4) or "").split(",") if a]
    exp_bases, exp_caps, exp_immobs, exp_create = set(), set(), set(), None
    for a in ann:
        if a.startswith("xB"):
            exp_caps.add(cell(a[2:]))
        elif a.startswith("xE"):
            exp_immobs.add(cell(a[2:]))
        elif a.startswith("B"):
            exp_bases.add(cell(a[1:]))
        else:
            assert a.startswith("E")
            exp_create = (cell(a[1:-1]), a[-1])

    pre = st
    mv = f"{src[0]},{src[1]}>{dst[0]},{dst[1]}"
    assert mv in G.legal_moves(st), f"{token}: {mv} not legal"
    st = G.apply_move(st, mv)

    if st.pending is not None and st.pending[0] == "immob":
        # attacker chooses among several enemy enforcers
        pick = next(c for c in exp_immobs
                    if pre.board.get(c, (None,))[0] == 1 - mover)
        cm = f"{pick[0]},{pick[1]}"
        assert cm in G.legal_moves(st), token
        st = G.apply_move(st, cm)
    if st.pending is not None and st.pending[0] == "create":
        assert exp_create is not None, f"{token}: unexpected enforcer creation"
        (c, d) = exp_create
        cm = f"{c[0]},{c[1]}={d}"
        assert cm in G.legal_moves(st), f"{token}: {cm} not legal"
        # serialization must round-trip mid-turn (pending state)
        sd = G.serialize(st)
        assert G.serialize(G.deserialize(sd)) == sd, "round-trip (pending)"
        st = G.apply_move(st, cm)
        assert st.board[c] == (mover, "E", d, True), token
    else:
        assert exp_create is None, f"{token}: expected enforcer creation"

    # verify the full diff matches the annotation exactly
    new_bases = {c for c, v in st.board.items()
                 if v[1] == "B" and c not in pre.board}
    gone_bases = {c for c, v in pre.board.items()
                  if v[1] == "B" and c not in st.board}
    frozen = {c for c, v in st.board.items()
              if v[1] == "E" and not v[3]
              and (c not in pre.board or pre.board[c][3])}
    assert new_bases == exp_bases, f"{token}: bases {new_bases} != {exp_bases}"
    assert gone_bases == exp_caps, f"{token}: captures {gone_bases} != {exp_caps}"
    assert frozen == exp_immobs, f"{token}: immobs {frozen} != {exp_immobs}"
    assert st.captured[mover] - pre.captured[mover] == len(exp_caps), token
    for c in new_bases:
        assert st.board[c][0] == mover, f"{token}: base owner"
    return st


def play_turn(st, tokens, mover):
    assert st.to_move == mover
    for token in tokens.split(";"):
        st = play_token(st, token.strip(), mover)
        if st.over:
            return st
    assert "done" in G.legal_moves(st)
    return G.apply_move(st, "done")


def do_setup(st, placements):
    for i, alg in enumerate(placements):
        mv = cid(alg)
        assert mv in G.legal_moves(st), f"setup {alg} illegal"
        assert st.to_move == i % 2
        st = G.apply_move(st, mv)
    return st


# ---------------------------------------------------------------- anchor 1

def test_sample_game():
    st = G.initial_state()
    # Set-up: 1.Bh11 Bh2, 2.Be8 Be5, 3.Bb5 Bb8, 4.Pi10 Pg3, 5.Pf7 Pd6, 6.Pc4 Pc9
    st = do_setup(st, ["h11", "h2", "e8", "e5", "b5", "b8",
                       "i10", "g3", "f7", "d6", "c4", "c9"])
    assert st.phase == "play" and st.to_move == 0
    # the row/column-of-Realms rule held during setup by construction; also
    # check a violation is rejected: after Bh11 White may not use realm row
    # 10-12 or realm column g-i again (checked in test_16_placements).
    assert_board(st, {
        0: {"B": "h11 e8 b5", "P": "i10 f7 c4"},
        1: {"B": "h2 e5 b8", "P": "g3 d6 c9"},
    }, "sample set-up")

    turns = [
        (0, "Pi10i6(Bh5) ; Pc4g4(Ei4W)"),
        (1, "Pd6d1(Be2) ; Pg3d3(Ed2N)"),
        (0, "Pi6j6(Bk5) ; Pg4g9(Bh8) ; Ei4d4"),
        (1, "Pd3a3(Bb2) ; Ed2c2 ; Pd1l1(Bk2)"),
        (0, "Pg9l9(Bk8) ; Pj6j7(El7W)"),
        (1, "Pc9c10(Bb11) ; Pa3a12(Ec12S)"),          # -> Figure 6
        (0, "Pf7f12(Be11) ; Ed4d10"),
        (1, "Pa12a6 ; Pc10c6 ; Ec2c4(xBb5)"),
        (0, "Pj7j10(Bk11) ; Pl9c9 ; El7a7(xBb8,xEa7)"),
        (1, "Pl1l6 ; Pc6j6 ; Ec4j4(xBk5)"),
        (0, "Pf12f7(Ef9S) ; Pc9d9"),
        (1, "Pj6b6(Bb5) ; Pl6l7 ; Ej4j7(xBk8,xEj7)"),  # -> Figure 7
        (0, "Pf7c7(Bb8) ; Pd9d6 ; Ef9f6(xBe5,xEf6)"),
        (1, "Pl7l4(Bk5)"),
        (0, "Pj10j9(Bk8)"),
        (1, "Pl4l10 ; Ec12j12(xBk11,xEj12)"),
        (0, "Pc7e7(Ef7N)"),
        (1, "Pl10l4(El6W)"),
        (0, "Pe7e6(Be5)"),                              # White wins
    ]
    for i, (mover, tokens) in enumerate(turns):
        st = play_turn(st, tokens, mover)
        if i == 5:   # after 9...: Figure 6
            assert_board(st, {
                0: {"B": "h11 e8 b5 h5 k5 h8 k8", "P": "l9 j7 f7",
                    "E": [("d4", "W", True), ("l7", "W", True)]},
                1: {"B": "h2 e5 b8 e2 b2 k2 b11", "P": "a12 c10 l1",
                    "E": [("c2", "W", True), ("c12", "S", True)]},
            }, "Figure 6")
        if i == 11:  # after 12...: Figure 7
            assert_board(st, {
                0: {"B": "h11 e8 h5 h8 e11 k11", "P": "f7 d9 j10",
                    "E": [("d10", "N", True), ("a7", "W", False),
                          ("f9", "S", True)]},
                1: {"B": "h2 e5 e2 b2 k2 b11 b5", "P": "a6 b6 l7",
                    "E": [("c12", "S", True), ("j7", "N", False)]},
            }, "Figure 7")
            assert st.captured == [1, 3]   # W holds xBb8; B holds b5,k5,k8

    assert st.over and st.winner == 0, "White must win the sample game"
    assert st.bases_created[0] == 12       # ended by White's 12th created Base
    assert G.is_terminal(st) and G.returns(st) == [1.0, -1.0]
    r0 = sum(1 for v in st.board.values() if v == (0, "B", None, False))
    r1 = sum(1 for v in st.board.values() if v == (1, "B", None, False))
    assert (r0, r1) == (8, 7), (r0, r1)
    print("anchor 1 OK: sample game replays, all events as annotated, "
          "Figures 6+7 match, White wins 8:7 on his 12th Base")


# ---------------------------------------------------------------- anchor 2

def test_worked_example():
    st = G.initial_state()
    st = do_setup(st, ["b11", "h8", "e8", "e5", "h5", "b2",
                       "c10", "g7", "f7", "f6", "i4", "a3"])
    assert_board(st, {
        0: {"B": "b11 e8 h5", "P": "c10 f7 i4"},
        1: {"B": "h8 e5 b2", "P": "g7 f6 a3"},
    }, "Figure 3")
    st = play_turn(st, "Pc10g10(Bh11) ; Pi4i10(Eg12S)", 0)
    st = play_turn(st, "Pa3i3(Bh2) ; Pg7g1(Eg3N)", 1)
    assert_board(st, {
        0: {"B": "b11 h11 e8 h5", "P": "g10 i10 f7",
            "E": [("g12", "S", True)]},
        1: {"B": "h8 e5 b2 h2", "P": "f6 i3 g1",
            "E": [("g3", "N", True)]},
    }, "Figure 4")
    st = play_turn(st, "Pi10i4(Eg4S) ; Pg10a10(Ec12S) ; Eg12g6", 0)
    assert_board(st, {
        0: {"B": "b11 h11 e8 h5", "P": "a10 f7 i4",
            "E": [("c12", "S", True), ("g6", "S", True),
                  ("g4", "S", True)]},
        1: {"B": "h8 e5 b2 h2", "P": "f6 i3 g1",
            "E": [("g3", "N", True)]},
    }, "Figure 5")
    print("anchor 2 OK: worked example replays; Figures 3, 4, 5 match")


# ---------------------------------------------------------------- anchor 3

SYMS = [
    lambda x, y: (x, y), lambda x, y: (y, 3 - x),
    lambda x, y: (3 - x, 3 - y), lambda x, y: (3 - y, x),
    lambda x, y: (y, x), lambda x, y: (3 - x, y),
    lambda x, y: (x, 3 - y), lambda x, y: (3 - y, 3 - x),
]


def test_16_placements():
    """Enumerate the real setup generator for ONE player on an empty board."""
    sets = set()

    def rec(placed):
        if len(placed) == 3:
            sets.add(frozenset(placed))
            return
        s = RState(phase="setup_b",
                   board={c: (0, "B", None, False) for c in placed},
                   to_move=0, bases_created=[len(placed), 0])
        for mv in G.legal_moves(s):
            c, r = map(int, mv.split(","))
            rec(placed + [(c, r)])

    rec([])
    assert len(sets) == 96, len(sets)
    # also: the row/column rule actually bit — after h11 (realm (2,3)),
    # b11 (realm row 3) and h5 (realm col 2) must be gone
    s = RState(phase="setup_b", board={cell("h11"): (0, "B", None, False)},
               to_move=0, bases_created=[1, 0])
    lm = G.legal_moves(s)
    assert cid("b11") not in lm and cid("h5") not in lm and cid("e8") in lm

    def canon(fs):
        realms = [(c // 3, r // 3) for c, r in fs]
        return min(tuple(sorted(f(x, y) for x, y in realms)) for f in SYMS)

    orbits = {canon(fs) for fs in sets}
    assert len(orbits) == 16, f"expected 16 placement classes, got {len(orbits)}"
    print("anchor 3 OK: 96 raw base placements = 16 up to the 8 symmetries")


# ---------------------------------------------------------------- anchor 4

def play_state(spec, to_move=0):
    return RState(phase="play", board=board_from(spec), to_move=to_move,
                  bases_created=[3, 3])


def cross_realm_moves(lm, src="5,5"):
    """Normal (cross-Realm) from>to moves of the piece at ``src``."""
    out = []
    sc, sr = map(int, src.split(","))
    for m in lm:
        if ">" not in m or "=" in m or not m.startswith(src + ">"):
            continue
        tc, tr = map(int, m.split(">")[1].split(","))
        if (tc // 3, tr // 3) != (sc // 3, sr // 3):
            out.append((tc, tr))
    return out

def test_enforcer_rotation():
    st = play_state({0: {"E": [("f6", "N", True)]}, 1: {"P": "l12"}})
    lm = G.legal_moves(st)
    assert "5,5>5,8" in lm and "5,5>6,5" in lm and "5,5>2,5" in lm
    assert not any(tc == 5 and tr < 5 for tc, tr in cross_realm_moves(lm)), \
        "enforcer must never reverse"
    # immobile enforcers generate no normal moves
    st2 = play_state({0: {"E": [("f6", "N", False)], "P": "a1"}, 1: {"P": "l12"}})
    assert not cross_realm_moves(G.legal_moves(st2))
    print("rotation OK: no reverse; immobile enforcers frozen")


def test_power_center_realm():
    st = play_state({0: {"P": "d5"}, 1: {"P": "l12"}})
    lm = G.legal_moves(st)
    assert "3,4>1,4" not in lm, "may not END on a Center"
    assert "3,4>0,4" in lm, "may pass THROUGH a vacant Center"
    assert "3,4>4,4" not in lm, "b) center of own realm"
    # cross-realm same-row squares fine; same-realm squares appear only as
    # rearrangement (within-realm) moves, never as normal moves
    st3 = play_state({0: {"P": "a5"}, 1: {"P": "l12"}})
    lm3 = G.legal_moves(st3)
    assert "0,4>2,4" in lm3   # same realm => a rearrangement opener
    st4 = G.apply_move(st3, "0,4>2,4")
    assert st4.to_move == 1 and st4.board[cell("c5")][1] == "P"
    print("power movement OK: center + new-Realm rules enforced")


def test_capture_arithmetic():
    base = {1: {"B": "h5", "P": "l12"}}
    # +2 Powers: capture, enforcer stays mobile
    st = play_state({0: {"E": [("d4", "E", True)], "P": "g5 g6"}, **base})
    st = G.apply_move(st, "3,3>6,3")
    assert cell("h5") not in st.board and st.captured[0] == 1
    assert st.board[cell("g4")] == (0, "E", "E", True)
    # +1 Power: capture, enforcer immobilized
    st = play_state({0: {"E": [("d4", "E", True)], "P": "g5"}, **base})
    st = G.apply_move(st, "3,3>6,3")
    assert cell("h5") not in st.board
    assert st.board[cell("g4")] == (0, "E", "E", False)
    # equal Powers: no capture
    st = play_state({0: {"E": [("d4", "E", True)], "P": "g5"},
                     1: {"B": "h5", "P": "i6 l12"}})
    st = G.apply_move(st, "3,3>6,3")
    assert cell("h5") in st.board and st.captured[0] == 0
    # event 3 (one enemy enforcer) preempts event 4: base survives
    st = play_state({0: {"E": [("d4", "E", True)], "P": "g5 g6"},
                     1: {"B": "h5", "P": "l12", "E": [("i4", "N", True)]}})
    st = G.apply_move(st, "3,3>6,3")
    assert cell("h5") in st.board, "event 3 excludes event 4"
    assert st.board[cell("i4")][3] is False
    assert st.board[cell("g4")][3] is True   # 2 > 0 Powers: mover stays mobile
    # ... and with no Power superiority the mover flips too
    st = play_state({0: {"E": [("d4", "E", True)]},
                     1: {"P": "l12", "E": [("i4", "N", True)]}})
    st = G.apply_move(st, "3,3>6,3")
    assert st.board[cell("i4")][3] is False and st.board[cell("g4")][3] is False
    # two candidates: attacker chooses
    st = play_state({0: {"E": [("d4", "E", True)], "P": "g5 g6"},
                     1: {"P": "l12", "E": [("i4", "N", True), ("i5", "N", True)]}})
    st = G.apply_move(st, "3,3>6,3")
    assert st.pending is not None and st.pending[0] == "immob"
    assert sorted(G.legal_moves(st)) == ["8,3", "8,4"]
    st = G.apply_move(st, "8,4")
    assert st.board[cell("i5")][3] is False and st.board[cell("i4")][3] is True
    assert st.board[cell("g4")][3] is True
    print("capture/immobilization arithmetic OK")


def test_turn_consistency():
    # (Black's Power on d3 keeps realm (1,0) event-free during the turn.)
    st = play_state({0: {"P": "a1 a4 g1"}, 1: {"P": "d3 l12"}})
    st = G.apply_move(st, "0,0>4,0")
    lm = G.legal_moves(st)
    assert "0,3>3,3" not in lm, "neither one source Realm nor one target Realm"
    assert "6,0>5,0" in lm and "done" in lm
    st = G.apply_move(st, "6,0>5,0")   # concentration into realm (1,0)
    lm = G.legal_moves(st)
    assert "done" in lm
    assert not any(m.startswith(("4,0>", "5,0>")) for m in lm), "moved pieces lock"
    for m in lm:
        if ">" in m:
            t = m.split(">")[1].split("=")[0]
            tc, tr = map(int, t.split(","))
            assert (tc // 3, tr // 3) == (1, 0), f"non-concentration move {m}"
    print("dispersal/concentration consistency OK")


def test_rearrangement():
    st = play_state({0: {"P": "a1 b1"}, 1: {"P": "l12"}})
    assert "0,0>0,0" not in G.legal_moves(st)
    st1 = G.apply_move(st, "0,0>1,0")   # onto the other piece's square
    assert st1.tmode == "rearr"
    assert "1,0>0,0" in G.legal_moves(st1)
    sd = G.serialize(st1)               # mid-rearrangement round-trip
    assert G.serialize(G.deserialize(sd)) == sd
    st2 = G.apply_move(st1, "1,0>0,0")  # swap commits, turn ends
    assert st2.to_move == 1 and st2.tmode is None
    assert st2.board[cell("a1")][1] == "P" and st2.board[cell("b1")][1] == "P"
    # three-in-a-row ban
    st = play_state({0: {"P": "a1"}, 1: {"P": "l12"}})
    st = G.apply_move(st, "0,0>1,0")            # W rearr #1
    st = G.apply_move(st, "11,11>10,11")        # B rearr
    st = G.apply_move(st, "1,0>0,0")            # W rearr #2
    st = G.apply_move(st, "10,11>11,11")        # B rearr
    lm = G.legal_moves(st)
    assert st.to_move == 0
    in_realm = [m for m in lm if ">" in m
                and m.split(">")[0] in ("0,0", "1,0")
                and tuple(int(x) // 3 for x in
                          m.split(">")[1].split("=")[0].split(",")) == (0, 0)]
    assert not in_realm, f"3rd rearrangement in a row offered: {in_realm}"
    assert "0,0>0,3" in lm              # normal moves still fine
    st = G.apply_move(st, "0,0>0,3")
    st = G.apply_move(st, "done")       # non-rearr turn resets the streak
    st = G.apply_move(st, "pass")
    assert any(m.startswith("0,3>") and m.split(">")[1].startswith(("1,", "2,"))
               and int(m.split(">")[1].split(",")[1]) // 3 == 1
               for m in G.legal_moves(st)), "streak should reset"
    # a PASS turn also breaks the streak ("three turns in a row"): W rearranges
    # realm (0,0) twice (Black shuttling l12<->l9 in realms kept event-free by
    # White powers at j8/j11), is banned, passes, and is then free again.
    st = play_state({0: {"P": "a1 j8 j11"}, 1: {"P": "l12"}})

    def w_rearrs(state):
        return [m for m in G.legal_moves(state) if ">" in m
                and tuple(int(x) // 3 for x in m.split(">")[0].split(",")) == (0, 0)
                and tuple(int(x) // 3 for x in
                          m.split(">")[1].split("=")[0].split(",")) == (0, 0)]

    st = G.apply_move(st, "0,0>1,0")            # W rearr #1
    st = G.apply_move(G.apply_move(st, "11,11>11,8"), "done")
    st = G.apply_move(st, "1,0>0,0")            # W rearr #2
    st = G.apply_move(G.apply_move(st, "11,8>11,11"), "done")
    assert not w_rearrs(st), "3rd consecutive rearrangement must be banned"
    st = G.apply_move(st, "pass")               # not "three turns in a row" now
    st = G.apply_move(G.apply_move(st, "11,11>11,8"), "done")
    assert w_rearrs(st), "a pass turn must break the rearrangement streak"
    print("rearrangement OK: swap, different-space, 3-in-a-row ban, "
          "move+pass resets")


def test_pass_draw():
    st = play_state({0: {"P": "a1"}, 1: {"P": "l12"}})
    st = G.apply_move(st, "pass")
    assert not st.over
    st = G.apply_move(st, "pass")
    assert st.over and st.winner is None and G.returns(st) == [0.0, 0.0]
    # tiebreak: a mobile-enforcer edge decides an equal-realms end
    st = play_state({0: {"P": "a1", "E": [("c1", "N", True)]},
                     1: {"P": "l12", "E": [("j12", "N", False)]}})
    st.enf_created = [1, 1]
    st = G.apply_move(st, "pass")
    st = G.apply_move(st, "pass")
    assert st.over and st.winner == 0   # 8 vs 7 enforcer total
    print("pass/draw OK: double pass ends; honest draw; enforcer tiebreak")


def test_random_playouts():
    for seed in (1, 2):
        rng = random.Random(seed)
        st = G.initial_state()
        n = 0
        while not G.is_terminal(st):
            moves = G.legal_moves(st)
            assert moves, "non-terminal state with no moves"
            st = G.apply_move(st, rng.choice(moves))
            n += 1
            assert n <= MAX_PLY + 8, "runaway game"
        assert len(G.returns(st)) == 2
    print("random playouts OK: terminate within the ply cap")


if __name__ == "__main__":
    test_sample_game()
    test_worked_example()
    test_16_placements()
    test_enforcer_rotation()
    test_power_center_realm()
    test_capture_arithmetic()
    test_turn_consistency()
    test_rearrangement()
    test_pass_draw()
    test_random_playouts()
    print("realm selftest: all tests passed")
