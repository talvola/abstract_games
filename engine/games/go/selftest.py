"""Go correctness anchor (pure stdlib). Pins the parts full Go adds over the
lighter Go-family cousins: Tromp-Taylor area scoring (stones + single-colour
territory + komi), two-pass termination deciding the winner, capture, illegal
suicide, and positional superko (the ko rule). The liberty/group/capture core is
the same logic verified in Atari Go.

Also anchors the three variant options (all default-off, and the default path
is pinned byte-identical to the pre-option engine):
- handicap: fixed Japanese placement (Sensei's Library "Handicap placement" /
  "Handicap stone placement on smaller boards"; matches OGS fixed placement),
  White to move first;
- topology=torus: adjacency wraps for capture, liberties AND territory floods;
- mode=killall: White wins iff any White stone survives at the end (komi and
  area score ignored, no draws) — per SL "Kill-all Game" Black is the killer.
Plus backward compatibility: an old serialized payload (no new fields) must
deserialize to normal/0/normal behaviour."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.go.game import (Go, GoState, _score, _board_key,  # noqa: E402
                           _handicap_points, BLACK, WHITE)

G = Go()

# sha256 of json.dumps(serialize(state), sort_keys=True) after the scripted
# default-options game below, computed on the PRE-OPTION engine (git HEAD
# before handicap/topology/mode existed). Guarantees the default path — and
# every state a live default match can be in — serializes byte-identically.
_PINNED_DEFAULT_TRACE = (
    "682762b6c4c98a990d6ddb2ed4d606476dae5f9ff8884ae9bf67961c5260a5ad")
_LEGACY_KEYS = {"size", "komi", "board", "to_move", "passes", "ply",
                "last_move", "history"}


def main():
    # --- area scoring -----------------------------------------------------
    assert _score({}, 9, 7.5) == (0, 7.5)                       # empty board
    assert _score({(2, 2): BLACK}, 5, 0.5) == (25, 0.5)        # one stone owns all
    split = {}
    for r in range(5):
        split[(0, r)] = split[(1, r)] = BLACK
        split[(3, r)] = split[(4, r)] = WHITE
    assert _score(split, 5, 0.5) == (10, 10.5)                  # middle column = dame

    # --- capture: a surrounded stone is removed ---------------------------
    s = GoState(size=5, board={(0, 0): WHITE, (1, 0): BLACK}, to_move=BLACK)
    s.history = frozenset({_board_key(s.board, 5)})
    s2 = G.apply_move(s, "0,1")                                 # black surrounds (0,0)
    assert (0, 0) not in s2.board and s2.board.get((0, 1)) == BLACK

    # --- suicide is illegal ----------------------------------------------
    #  White stones ring the empty corner (0,0); Black may not play into it.
    board = {(1, 0): WHITE, (0, 1): WHITE}
    s = GoState(size=5, board=board, to_move=BLACK)
    s.history = frozenset({_board_key(board, 5)})
    assert "0,0" not in G.legal_moves(s), "suicide must be illegal"
    #  ...but the same move IS legal if it captures (not suicide):
    board2 = {(1, 0): WHITE, (0, 1): BLACK, (2, 0): BLACK}      # white (1,0) in atari
    s = GoState(size=5, board=board2, to_move=BLACK)
    s.history = frozenset({_board_key(board2, 5)})
    # black at (0,0) would still self-atari? (0,0) libs after: none unless capture.
    # Build a clean capture-not-suicide: white (1,1) lone, black around except (0,1).
    cap = {(1, 1): WHITE, (0, 1): BLACK, (1, 0): BLACK, (1, 2): BLACK}
    s = GoState(size=5, board=cap, to_move=BLACK)
    s.history = frozenset({_board_key(cap, 5)})
    assert "2,1" in G.legal_moves(s)                            # captures (1,1), legal

    # --- positional superko forbids recreating a prior board (the ko) -----
    base = {(1, 0): BLACK, (0, 1): BLACK, (1, 2): BLACK,
            (2, 0): WHITE, (3, 1): WHITE, (2, 2): WHITE, (1, 1): WHITE}
    s0 = GoState(size=5, board=dict(base), to_move=BLACK)
    s0.history = frozenset({_board_key(base, 5)})
    s1 = G.apply_move(s0, "2,1")                                # black takes the ko at (1,1)
    assert (1, 1) not in s1.board and (2, 1) in s1.board
    assert "1,1" not in G.legal_moves(s1), "ko recapture must be superko-illegal"

    # --- two passes end the game and the score decides --------------------
    s = G.initial_state(options={"size": 5, "komi": 0.5})
    s = G.apply_move(s, "2,2")                                  # a lone black stone
    s = G.apply_move(s, "pass")
    s = G.apply_move(s, "pass")
    assert G.is_terminal(s) and G.returns(s) == [1.0, -1.0]     # black controls all
    # 'pass' is always offered while the game is live
    assert "pass" in G.legal_moves(G.initial_state())

    # --- serialize round-trips (incl. komi, passes, history) --------------
    s = G.apply_move(G.apply_move(G.initial_state(), "4,4"), "pass")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    # ======================================================================
    # (a) default-behaviour regression: pinned pre-option trace
    # ======================================================================
    s = G.initial_state()
    for m in ["4,4", "2,2", "6,6", "pass", "0,0"]:
        s = G.apply_move(s, m)
    d = G.serialize(s)
    assert set(d.keys()) == _LEGACY_KEYS, \
        "default-options serialize must not grow new fields (live matches!)"
    got = hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
    assert got == _PINNED_DEFAULT_TRACE, "default behaviour changed!"
    assert len(G.legal_moves(s)) == 78
    # explicit-default options are the same game as no options at all
    s2 = G.initial_state(options={"size": 9, "komi": 7.5, "handicap": 0,
                                  "topology": "normal", "mode": "normal"})
    assert G.serialize(s2) == G.serialize(G.initial_state())

    # ======================================================================
    # (b) handicap on 19x19: exact fixed placements, White to move
    #     (SL HandicapPlacement SGFs: h2 = Q16+D4 = (15,3)+(3,15) 0-indexed)
    # ======================================================================
    s = G.initial_state(options={"size": 19, "handicap": 2})
    assert s.to_move == WHITE and s.ply == 0
    assert set(s.board) == {(15, 3), (3, 15)}
    assert all(v == BLACK for v in s.board.values())
    s = G.initial_state(options={"size": 19, "handicap": 3})
    assert set(s.board) == {(15, 3), (3, 15), (15, 15)}     # upper-left open
    s = G.initial_state(options={"size": 19, "handicap": 9})
    assert set(s.board) == {(c, r) for c in (3, 9, 15) for r in (3, 9, 15)}
    # the handicap position seeds the superko history
    assert _board_key(s.board, 19) in s.history and len(s.history) == 1
    # White may not immediately recreate it, e.g. by... (nothing to capture:
    # just check White really is the mover and has the full complement)
    assert len(G.legal_moves(s)) == 19 * 19 - 9 + 1

    # ======================================================================
    # (c) handicap on 13x13 (4-4 points) and 9x9 (3-3 points, per SL/OGS)
    # ======================================================================
    s = G.initial_state(options={"size": 13, "handicap": 5})
    assert set(s.board) == {(9, 3), (3, 9), (9, 9), (3, 3), (6, 6)}
    assert s.to_move == WHITE
    s = G.initial_state(options={"size": 9, "handicap": 2})
    assert set(s.board) == {(6, 2), (2, 6)}                 # G7 + C3
    s = G.initial_state(options={"size": 9, "handicap": 4})
    assert set(s.board) == {(2, 2), (6, 2), (2, 6), (6, 6)}
    s = G.initial_state(options={"size": 9, "handicap": 9})  # OGS supports 9
    assert set(s.board) == {(c, r) for c in (2, 4, 6) for r in (2, 4, 6)}
    # handicap 1 is not a placement (it's just no-komi Go) -> treated as 0
    s = G.initial_state(options={"size": 9, "handicap": 1})
    assert s.board == {} and s.to_move == BLACK and s.handicap == 0
    assert _handicap_points(19, 7)[6] == (9, 9)             # 7th stone: tengen

    # ======================================================================
    # (d) torus: capture and territory wrap across the seam
    # ======================================================================
    # White (0,0)'s only remaining liberty is (0,4), ACROSS the top seam.
    cross = {(0, 0): WHITE, (1, 0): BLACK, (0, 1): BLACK, (4, 0): BLACK}
    st = GoState(size=5, board=dict(cross), to_move=BLACK, torus=True)
    st.history = frozenset({_board_key(st.board, 5)})
    assert "0,4" in G.legal_moves(st)
    st2 = G.apply_move(st, "0,4")
    assert (0, 0) not in st2.board, "wrap-around capture must work"
    # ...whereas on a normal board the same move touches nothing at (0,0)
    sn = GoState(size=5, board=dict(cross), to_move=BLACK, torus=False)
    sn.history = frozenset({_board_key(sn.board, 5)})
    assert (0, 0) in G.apply_move(sn, "0,4").board
    # scoring flood wraps and the wrapped region is counted ONCE:
    # a lone black column on a torus owns the whole rest of the board...
    col = {(2, r): BLACK for r in range(5)}
    assert _score(col, 5, 0.5, torus=True) == (25, 0.5)
    # ...but add a white column and the "edge" territory becomes dame,
    # because cols 3-4 now wrap around to touch white col 0.
    two = dict(col)
    two.update({(0, r): WHITE for r in range(5)})
    assert _score(two, 5, 0.5, torus=False) == (15, 5.5)    # normal: B owns 3-4
    assert _score(two, 5, 0.5, torus=True) == (5, 5.5)      # torus: all dame
    # torus flag survives apply_move + serialize round-trip
    st3 = G.initial_state(options={"size": 9, "topology": "torus"})
    st3 = G.apply_move(st3, "0,0")
    assert st3.torus and G.deserialize(G.serialize(st3)).torus
    assert G.serialize(st3)["topology"] == "torus"

    # ======================================================================
    # (e) kill-all: White wins iff any White stone survives; komi/score
    #     ignored; no draws (SL "Kill-all Game": Black must kill everything)
    # ======================================================================
    s = G.initial_state(options={"size": 9, "handicap": 9, "mode": "killall",
                                 "komi": 7.5})
    assert s.to_move == WHITE
    sw = G.apply_move(s, "0,0")                             # White lives (crudely)
    sw = G.apply_move(G.apply_move(sw, "pass"), "pass")
    assert G.is_terminal(sw)
    assert G.returns(sw) == [-1.0, 1.0], "surviving White stone => White wins"
    # area scoring would say BLACK here (9 stones vs 1 + 7.5 komi = 8.5):
    # proves killall ignores komi and the area score entirely.
    b, w = _score(sw.board, 9, 7.5)
    assert b > w
    # White never plays a stone -> nothing survives -> Black wins
    sb = G.apply_move(G.apply_move(s, "pass"), "pass")
    assert G.is_terminal(sb) and G.returns(sb) == [1.0, -1.0]
    # killall mode round-trips
    assert G.deserialize(G.serialize(s)).mode == "killall"
    assert G.serialize(s)["mode"] == "killall"

    # ======================================================================
    # (f) old-payload compatibility: a pre-option serialized match (no
    #     handicap/topology/mode keys) deserializes to default behaviour
    # ======================================================================
    old = {
        "size": 9, "komi": 7.5, "board": {"4,4": 0, "2,2": 1},
        "to_move": 0, "passes": 0, "ply": 2,
        "last_move": [2, 2],
        "history": [_board_key({}, 9),
                    _board_key({(4, 4): BLACK}, 9),
                    _board_key({(4, 4): BLACK, (2, 2): WHITE}, 9)],
    }
    so = G.deserialize(old)
    assert so.handicap == 0 and so.torus is False and so.mode == "normal"
    assert "pass" in G.legal_moves(so)
    so2 = G.apply_move(so, "6,6")                           # still playable
    assert set(G.serialize(so2).keys()) == _LEGACY_KEYS     # and stays legacy

    print("go selftest OK")


if __name__ == "__main__":
    main()
