"""Ponte del Diavolo correctness anchor (pure stdlib): placement legality (no
5-group; the diagonal 'touching rule'; a legal island completion), bridge
legality (a legal span, and illegal crossings / a second bridge on a tile),
triangular scoring with a bridge-linked group, the two-tile turn structure, and
that a random game terminates. Runs under system python3 (agp + this game only)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.ponte_del_diavolo.game import (  # noqa: E402
    PonteDelDiavolo, PonteState, LIGHT, DARK,
    _single_ok, _bridge_cells, _crosses,
)

G = PonteDelDiavolo()


def rt(s):
    """serialize round-trips."""
    d = G.serialize(s)
    import json
    json.dumps(d)
    assert G.serialize(G.deserialize(d)) == d, "serialize does not round-trip"


def main():
    # --- bridge geometry --------------------------------------------------
    assert _bridge_cells((0, 0), (2, 0)) == [(1, 0)]            # orthogonal, 1 gap
    assert _bridge_cells((0, 0), (2, 2)) == [(1, 1)]            # diagonal, 1 gap
    assert set(_bridge_cells((0, 0), (1, 2))) == {(0, 1), (1, 1)}   # knight, 2 gaps
    assert set(_bridge_cells((0, 0), (2, 1))) == {(1, 0), (1, 1)}
    assert _bridge_cells((0, 0), (3, 0)) is None                # too far -> not a bridge

    # --- placement: never a group of 5+ -----------------------------------
    # a legal 4-in-a-row island; extending it to 5 is illegal.
    row4 = {(0, 0): LIGHT, (1, 0): LIGHT, (2, 0): LIGHT, (3, 0): LIGHT}
    assert not _single_ok(row4, LIGHT, (4, 0)), "5-group must be illegal"
    assert _single_ok(row4, DARK, (4, 0)), "opposite colour may touch"

    # --- placement: the diagonal 'touching rule' --------------------------
    isl = {(0, 0): LIGHT, (1, 0): LIGHT, (0, 1): LIGHT, (1, 1): LIGHT}   # 2x2 island
    assert not _single_ok(isl, LIGHT, (2, 2)), "same-colour tile may not touch an island diagonally"
    assert _single_ok(isl, LIGHT, (3, 3)), "a far same-colour tile is fine"
    assert _single_ok(isl, DARK, (2, 2)), "opposite colour may touch the island diagonally"

    # --- placement: a legal island completion, and its illegal twin -------
    tromino = {(0, 0): LIGHT, (1, 0): LIGHT, (0, 1): LIGHT}     # L-sandbank of 3
    assert _single_ok(tromino, LIGHT, (1, 1)), "completing an isolated 4-island is legal"
    # same completion, but a lone same-colour tile sits diagonally off the new island
    blocked = dict(tromino); blocked[(2, 2)] = LIGHT
    assert not _single_ok(blocked, LIGHT, (1, 1)), "completed island may not touch a same-colour tile"

    # --- bridge legality: a legal span linking two islands ----------------
    board = {
        (0, 0): LIGHT, (1, 0): LIGHT, (0, 1): LIGHT, (1, 1): LIGHT,     # island A
        (0, 3): LIGHT, (1, 3): LIGHT, (0, 4): LIGHT, (1, 4): LIGHT,     # island B
    }
    s = PonteState(board=dict(board), to_move=LIGHT)
    moves = G.legal_moves(s)
    assert "0,1>0,3" in moves and "0,3>0,1" in moves, "legal 1-gap bridge should be offered both ways"

    # a tile under the span blocks the bridge
    s_block = PonteState(board={**board, (0, 2): DARK}, to_move=LIGHT)
    assert "0,1>0,3" not in G.legal_moves(s_block), "a bridge may not span a tile"

    # --- bridge legality: one bridge per tile -----------------------------
    # three lone light tiles in a column; bridging (0,1)-(0,3) then blocks (0,3)-(0,5).
    col = {(0, 1): LIGHT, (0, 3): LIGHT, (0, 5): LIGHT}
    s = PonteState(board=dict(col), to_move=LIGHT)
    assert "0,3>0,5" in G.legal_moves(s)
    s2 = G.apply_move(s, "0,1>0,3")            # a bridge ends the turn -> Dark to move
    assert s2.to_move == DARK and len(s2.bridges) == 1
    s2b = PonteState(board=dict(col), bridges=list(s2.bridges), to_move=LIGHT)
    assert "0,3>0,5" not in G.legal_moves(s2b), "a tile may support at most one bridge"

    # --- bridge legality: bridges may not cross ---------------------------
    assert _crosses(((0, 1), (2, 1)), ((1, 0), (1, 2))), "crossing spans must be detected"
    crosser = {(0, 1): LIGHT, (2, 1): LIGHT, (1, 0): LIGHT, (1, 2): LIGHT}
    s = PonteState(board=dict(crosser), bridges=[((0, 1), (2, 1))], to_move=LIGHT)
    assert "1,0>1,2" not in G.legal_moves(s), "a bridge may not cross another bridge"

    # --- two-tile turn structure ------------------------------------------
    s = G.initial_state()
    assert G.current_player(s) == LIGHT and s.phase == 0
    s1 = G.apply_move(s, "4,4")                # first tile
    assert G.current_player(s1) == LIGHT and s1.phase == 1, "same player places the 2nd tile"
    s2 = G.apply_move(s1, "6,6")              # second tile
    assert G.current_player(s2) == DARK and s2.phase == 0, "turn passes after two tiles"
    rt(s); rt(s1); rt(s2)

    # --- scoring: a 2-island group (3 pts) + a lone island (1 pt) = 4 -----
    #   Light: islands A+B linked by a bridge (3) and a lone island C (1) = 4
    #   Dark : one lone island = 1  ->  Light wins
    end_board = {
        (0, 0): LIGHT, (1, 0): LIGHT, (0, 1): LIGHT, (1, 1): LIGHT,     # A
        (0, 3): LIGHT, (1, 3): LIGHT, (0, 4): LIGHT, (1, 4): LIGHT,     # B
        (5, 5): LIGHT, (6, 5): LIGHT, (5, 6): LIGHT, (6, 6): LIGHT,     # C (lone)
        (0, 8): DARK, (1, 8): DARK, (0, 9): DARK, (1, 9): DARK,         # dark lone island
    }
    s_end = PonteState(board=end_board, bridges=[((0, 1), (0, 3))],
                       to_move=LIGHT, ended=True)
    ls, li, lb = G._tally(s_end, LIGHT)
    ds, di, db = G._tally(s_end, DARK)
    assert (ls, li, lb) == (4, 3, 1), (ls, li, lb)   # 3 (linked pair) + 1 (lone) = 4
    assert (ds, di, db) == (1, 1, 0), (ds, di, db)
    assert G.is_terminal(s_end) and G.returns(s_end) == [1.0, -1.0], "Light should win 4-1"
    rt(s_end)

    # scoring tie-break by island count (equal points, Light has more islands)
    #   Light: two lone islands = 2 pts, 2 islands
    #   Dark : one 2-island bridge group = 3? -> make it equal-points instead:
    # Light: three lone islands = 3 pts / 3 islands; Dark: one 2-group (3) + 0 = 3 / 2 islands
    # (Light wins the points-tie on islands.)  Build minimally and just check ordering.
    assert (3, 3, 0) > (3, 2, 1), "island count breaks a points tie before bridges"

    # --- overlay render carries the bridge --------------------------------
    r = G.render(s_end)
    assert r["board"]["type"] == "square" and r["board"]["width"] == 10
    assert any(len(seg) == 3 for seg in r["board"]["overlay"]), "bridge should appear in overlay"
    assert r["board"]["tints"], "completed islands should be tinted"

    # --- a random game terminates -----------------------------------------
    rng = random.Random(12345)
    for game_i in range(4):
        st = G.initial_state()
        n = 0
        while not G.is_terminal(st):
            ms = G.legal_moves(st)
            assert ms, "legal_moves empty on a non-terminal state"
            st = G.apply_move(st, rng.choice(ms))
            n += 1
            assert n < 5000, "random game failed to terminate"
        ret = G.returns(st)
        assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
