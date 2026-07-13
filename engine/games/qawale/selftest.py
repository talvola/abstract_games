"""Qawale correctness anchors (pure stdlib). No perft exists; the anchors are
rule assertions taken from the official Gigamic rulebook (USA/GB page,
"QAWALE rules" PDF) plus the BGA game help:

 (1) setup: 2 neutral pebbles on each corner, hands 8/8, Red first;
 (2) placement only onto existing stacks; sowing path length = lifted height;
     every move from one source has equal length (prefix-safe paths);
 (3) path legality: orthogonal steps, no immediate backtrack (including back
     onto the lifted square as the 2nd drop), circling back to a square IS
     legal -- cross-checked against an independent path enumerator;
 (4) sowing order: bottom pebble first, one per square, your pebble last;
     a revisited square receives a second pebble on top;
 (5) wins via apply_move: row + diagonal lines of visible tops; a sow that
     completes the OPPONENT's line loses immediately; a sow completing BOTH
     colours' lines at once wins for the NON-mover (documented interpretation,
     rules.md); a vertical stack of 4 of one colour is NOT a line;
 (6) supply exhaustion with no line -> honest draw, returns [0,0];
 (7) serialize round-trip; (8) 500 random playouts all terminate within 16
     plies with legal moves at every non-terminal node (stats printed).
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.qawale.game import (  # noqa: E402
    Qawale, QState, LIGHT, DARK, NEUTRAL, SIZE, HAND, CORNERS, ORTH, _on,
)

G = Qawale()


def S(board, to_move=LIGHT, hands=(HAND, HAND), ply=0):
    return QState(board=dict(board), hands=tuple(hands), to_move=to_move, ply=ply)


def indep_paths(src, n):
    """Independent path enumerator (BFS over extended sequences), written
    without reference to the game's DFS: e = [src, p1..pn], each step
    orthogonally adjacent, e[i+1] != e[i-1]."""
    seqs = [[src]]
    for _ in range(n):
        nxt = []
        for e in seqs:
            cur, back = e[-1], (e[-2] if len(e) >= 2 else None)
            for dc, dr in ORTH:
                t = (cur[0] + dc, cur[1] + dr)
                if _on(t) and t != back:
                    nxt.append(e + [t])
        seqs = nxt
    return {tuple(e[1:]) for e in seqs}


def moves_from(state, src):
    pre = f"{src[0]},{src[1]}>"
    return [m for m in G.legal_moves(state) if m.startswith(pre)]


def main():
    # --- (1) setup -----------------------------------------------------------
    s0 = G.initial_state()
    assert s0.hands == (8, 8) and s0.to_move == LIGHT and s0.ply == 0
    assert set(s0.board) == set(CORNERS)
    assert all(col == (NEUTRAL, NEUTRAL) for col in s0.board.values())
    assert not G.is_terminal(s0)

    # --- (2)+(3) move generation vs the independent enumerator ---------------
    ms0 = G.legal_moves(s0)
    # only the 4 corner stacks are playable; lifted height 3 -> 3-square paths
    for m in ms0:
        cells = m.split(">")
        assert len(cells) == 4, m                      # src + 3 sow squares
        assert tuple(map(int, cells[0].split(","))) in CORNERS, m
    for corner in CORNERS:
        got = {tuple(tuple(map(int, x.split(","))) for x in m.split(">")[1:])
               for m in moves_from(s0, corner)}
        assert got == indep_paths(corner, 3), corner
    # corner (0,0): 2 first steps; (1,0)->{(2,0),(1,1)} then 2/3 -> 10 paths
    assert len(moves_from(s0, (0, 0))) == 10
    assert len(ms0) == 40
    # a lone pebble is a stack: lifted height 2 -> 2-square paths; and the
    # 2nd drop may not step back onto the lifted square
    s = S({(0, 0): (DARK,)})
    ms = G.legal_moves(s)
    assert {len(m.split(">")) for m in ms} == {3}
    assert "0,0>1,0>0,0" not in ms and "0,0>0,1>0,0" not in ms
    assert "0,0>1,0>2,0" in ms and "0,0>1,0>1,1" in ms
    got = {tuple(tuple(map(int, x.split(","))) for x in m.split(">")[1:]) for m in ms}
    assert got == indep_paths((0, 0), 2)
    # centre square, deep stack: exhaustive cross-check at height 5
    s = S({(1, 1): (DARK, NEUTRAL, DARK, NEUTRAL)})
    got = {tuple(tuple(map(int, x.split(","))) for x in m.split(">")[1:])
           for m in G.legal_moves(s)}
    assert got == indep_paths((1, 1), 5)
    # circling back to the lifted square after a 4-cycle IS legal
    s = S({(0, 0): (DARK, DARK, DARK)})
    assert "0,0>1,0>1,1>0,1>0,0" in G.legal_moves(s)

    # --- (4) sowing order: bottom first, your pebble last --------------------
    s = S({(1, 1): (DARK, NEUTRAL)}, to_move=LIGHT)
    t = G.apply_move(s, "1,1>1,2>1,3>2,3")
    assert (1, 1) not in t.board                      # whole stack lifted
    assert t.board[(1, 2)] == (DARK,)                 # bottom pebble first
    assert t.board[(1, 3)] == (NEUTRAL,)
    assert t.board[(2, 3)] == (LIGHT,)                # your pebble last
    assert t.hands == (7, 8) and t.to_move == DARK and t.winner is None
    # drops land ON TOP of existing stacks; a revisited square gets two pebbles
    s = S({(0, 0): (DARK, DARK, DARK), (1, 0): (NEUTRAL,)}, to_move=LIGHT)
    t = G.apply_move(s, "0,0>1,0>1,1>0,1>0,0")
    assert t.board[(1, 0)] == (NEUTRAL, DARK)         # on top of the neutral
    assert t.board[(1, 1)] == (DARK,)
    assert t.board[(0, 1)] == (DARK,)
    assert t.board[(0, 0)] == (LIGHT,)                # circled back to source
    assert t.winner is None

    # --- (5) wins (all via apply_move) ----------------------------------------
    # row: Red tops 0..2 of row 1, sow finishes through (3,1)
    s = S({(0, 1): (LIGHT,), (1, 1): (LIGHT,), (2, 1): (LIGHT,),
           (3, 2): (LIGHT,)}, to_move=LIGHT)
    m = "3,2>3,1>3,0"
    assert m in G.legal_moves(s)
    t = G.apply_move(s, m)                            # LIGHT dropped on 3,1 then 3,0
    assert t.board[(3, 1)] == (LIGHT,) and t.winner == LIGHT
    assert G.is_terminal(t) and G.returns(t) == [1.0, -1.0]
    assert G.legal_moves(t) == []
    # diagonal: Red tops (0,0),(1,1),(2,2), finish (3,3)
    s = S({(0, 0): (LIGHT,), (1, 1): (LIGHT,), (2, 2): (LIGHT,),
           (3, 2): (LIGHT,)}, to_move=LIGHT)
    m = "3,2>3,3>2,3"
    assert m in G.legal_moves(s)
    t = G.apply_move(s, m)
    assert t.board[(3, 3)] == (LIGHT,) and t.winner == LIGHT
    # covering a line square breaks the line: same position, sow over (2,2)
    s = S({(0, 0): (LIGHT,), (1, 1): (LIGHT,), (2, 2): (LIGHT,),
           (3, 2): (DARK,)}, to_move=DARK)
    t = G.apply_move(s, "3,2>2,2>2,1")                # DARK tops (2,2)
    assert t.board[(2, 2)] == (LIGHT, DARK) and t.winner is None
    # OPPONENT's line: Red's sow re-tops a buried Dark pebble -> Dark wins
    s = S({(0, 2): (DARK,), (1, 2): (DARK,), (2, 2): (DARK,),
           (3, 3): (DARK,)}, to_move=LIGHT)
    m = "3,3>3,2>3,1"                                 # drops DARK on (3,2), LIGHT on (3,1)
    assert m in G.legal_moves(s)
    t = G.apply_move(s, m)
    assert t.board[(3, 2)] == (DARK,)
    assert t.winner == DARK and G.returns(t) == [-1.0, 1.0]
    # SIMULTANEOUS lines -> the non-mover wins (documented interpretation)
    s = S({(0, 1): (LIGHT,), (1, 1): (LIGHT,), (2, 1): (LIGHT,),
           (0, 2): (DARK,), (1, 2): (DARK,), (2, 2): (DARK,),
           (3, 3): (DARK,)}, to_move=LIGHT)
    m = "3,3>3,2>3,1"                                 # completes BOTH rows at once
    assert m in G.legal_moves(s)
    t = G.apply_move(s, m)
    assert t.board[(3, 2)] == (DARK,) and t.board[(3, 1)] == (LIGHT,)
    assert t.winner == DARK
    # a vertical stack of 4 of one colour is NOT a line
    s = S({(1, 1): (LIGHT, LIGHT, LIGHT, LIGHT), (3, 3): (DARK,)}, to_move=DARK)
    t = G.apply_move(s, "3,3>3,2>3,1")
    assert t.winner is None and not G.is_terminal(t)

    # --- (6) supply exhaustion -> honest draw ---------------------------------
    s = S({(0, 0): (NEUTRAL, NEUTRAL), (1, 2): (DARK,)},
          to_move=DARK, hands=(0, 1), ply=15)
    t = G.apply_move(s, "1,2>1,1>1,0")
    assert t.hands == (0, 0) and t.winner is None
    assert G.is_terminal(t) and G.returns(t) == [0.0, 0.0]
    assert G.legal_moves(t) == []

    # --- (7) serialize round-trip ---------------------------------------------
    for st in (s0, t, G.apply_move(s0, G.legal_moves(s0)[7])):
        rt = G.deserialize(G.serialize(st))
        assert rt.board == st.board and rt.hands == st.hands
        assert rt.to_move == st.to_move and rt.ply == st.ply
        assert rt.winner == st.winner

    # render probe: stack arrays present, neutral entries = owner 2
    spec = G.render(s0)
    assert spec["board"] == {"type": "square", "width": SIZE, "height": SIZE}
    assert len(spec["pieces"]) == 4
    assert all(p["stack"] == [NEUTRAL, NEUTRAL] and p["owner"] == NEUTRAL
               for p in spec["pieces"])

    # --- (8) 500 random playouts ----------------------------------------------
    rng = random.Random(2022)
    wins = [0, 0]
    draws = 0
    plies = []
    maxh = 0
    maxbr = 0
    for _ in range(500):
        st = G.initial_state()
        while not G.is_terminal(st):
            ms = G.legal_moves(st)
            assert ms, "non-terminal state with no legal move"
            maxbr = max(maxbr, len(ms))
            st = G.apply_move(st, rng.choice(ms))
            maxh = max(maxh, max(len(c) for c in st.board.values()))
            assert st.ply <= 2 * HAND
        plies.append(st.ply)
        if st.winner is None:
            draws += 1
            assert st.hands == (0, 0)
        else:
            wins[st.winner] += 1
    print(f"playouts: 500  red {wins[LIGHT]}  blue {wins[DARK]}  draws {draws}  "
          f"avg plies {sum(plies) / len(plies):.1f}  max plies {max(plies)}  "
          f"max stack {maxh}  max branching {maxbr}")

    print("qawale selftest: all anchors passed")


if __name__ == "__main__":
    main()
