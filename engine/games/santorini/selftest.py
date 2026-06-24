"""Santorini correctness anchor — pure stdlib, fast.

No published perft for Santorini, so the anchor is a set of baked rule
assertions: the 5x5 board + 0..4 levels; the placement phase (4 placements,
seat order 0,0,1,1, single-cell move, no double-occupancy); MOVE legality
(<=1 level up, any down, not onto a worker/dome); BUILD legality (adjacent to
the new worker position, not onto a worker/dome, raises level, level-3 ->
dome); the move encoding (wfrom>wto>build triples; 2-cell wfrom>wto climbs);
the CLIMB win (reached via apply_move); the STUCK-player loss (terminal,
opponent wins); a build-then-dome (level 3 -> 4) case; and serialize
round-trip.

Run with:  PYTHONPATH=. python3 games/santorini/selftest.py
Prints "SELFTEST OK" and exits 0 on success; raises / nonzero on failure.
"""

from __future__ import annotations

import json

from games.santorini.game import (
    Santorini, SState, SIZE, DOME, PLACEMENT_ORDER, _s, _cell,
)


def _play_state(workers, levels=None, to_move=0):
    """Build a play-phase state (placement already done)."""
    return SState(levels=dict(levels or {}), workers=dict(workers),
                  to_move=to_move, placed=len(PLACEMENT_ORDER))


def main() -> None:
    g = Santorini()

    # ---- (1) board geometry + render levels dict --------------------------
    assert SIZE == 5 and DOME == 4
    st = g.initial_state()
    rs = g.render(st)
    assert rs["board"]["type"] == "square"
    assert rs["board"]["width"] == 5 and rs["board"]["height"] == 5
    assert rs["board"]["levels"] == {}, "no levels at game start"
    assert rs["pieces"] == [], "no workers on the board at game start"
    # a level dict only contains cells with level>=1
    st2 = _play_state({(0, 0): 0, (4, 4): 1}, levels={(2, 2): 3, (1, 1): 4})
    lv = g.render(st2)["board"]["levels"]
    assert lv == {"2,2": 3, "1,1": 4}, f"levels dict wrong: {lv}"

    # ---- (2) placement phase: order 0,0,1,1, single-cell, no overlap ------
    assert PLACEMENT_ORDER == [0, 0, 1, 1]
    st = g.initial_state()
    assert g.current_player(st) == 0
    pm = g.legal_moves(st)
    assert len(pm) == 25 and "2,2" in pm, "placement move = a single empty cell"
    assert all(">" not in m for m in pm), "placement moves are single cells"
    st = g.apply_move(st, "0,0")          # P0 places worker 1
    assert g.current_player(st) == 0, "P0 still places (both workers first)"
    assert "0,0" not in g.legal_moves(st), "cannot place on an occupied cell"
    st = g.apply_move(st, "1,1")          # P0 places worker 2
    assert g.current_player(st) == 1, "now P1 places"
    st = g.apply_move(st, "3,3")          # P1 places worker 1
    assert g.current_player(st) == 1
    st = g.apply_move(st, "4,4")          # P1 places worker 2
    assert not g._in_placement(st), "placement complete after 4 placements"
    assert g.current_player(st) == 0, "play phase begins with player 0"
    assert st.workers == {(0, 0): 0, (1, 1): 0, (3, 3): 1, (4, 4): 1}

    # ---- (3) MOVE legality: <=1 up, any down, not onto worker/dome --------
    # worker on ground at (2,2); neighbours have assorted levels
    st = _play_state(
        {(2, 2): 0, (0, 0): 1},
        levels={(2, 1): 1,    # one up -> OK
                (3, 2): 2,    # two up -> illegal
                (1, 2): 4},   # dome -> illegal
    )
    dests = {m.split(">")[1] for m in g.legal_moves(st)}
    assert "2,1" in dests, "step exactly one level up must be legal"
    assert "3,2" not in dests, "stepping two levels up must be illegal"
    assert "1,2" not in dests, "stepping onto a dome must be illegal"
    # any number DOWN is fine: worker on a level-3-ish high cell stepping to 0
    st = _play_state({(2, 2): 0, (0, 0): 1}, levels={(2, 2): 2})
    dests = {m.split(">")[1] for m in g.legal_moves(st)}
    assert "1,1" in dests, "stepping down two levels (2 -> 0) must be legal"
    # cannot move onto another worker
    st = _play_state({(2, 2): 0, (2, 3): 1, (0, 0): 1})
    dests = {m.split(">")[1] for m in g.legal_moves(st)}
    assert "2,3" not in dests, "cannot move onto a cell occupied by a worker"

    # ---- (4) BUILD legality: adjacent to NEW pos, not worker/dome, +1 -----
    st = _play_state({(2, 2): 0, (0, 4): 1})
    # pick the move 2,2>2,3 ; builds must be adjacent to (2,3)
    builds = {m.split(">")[2] for m in g.legal_moves(st)
              if m.startswith("2,2>2,3>")}
    assert "2,2" in builds, "the vacated origin is a legal build target"
    assert "2,4" in builds and "1,3" in builds, "adjacent empties buildable"
    assert "0,0" not in builds, "a non-adjacent cell is not a build target"
    # build raises the level by one
    ns = g.apply_move(st, "2,2>2,3>2,4")
    assert ns.level((2, 4)) == 1, "a build raises an empty cell to level 1"
    assert ns.workers == {(2, 3): 0, (0, 4): 1}, "worker ended on its destination"
    assert g.current_player(ns) == 1, "turn passes to the opponent"
    # cannot build onto a worker or a dome
    st = _play_state({(2, 2): 0, (2, 4): 1, (0, 0): 1},
                     levels={(1, 3): 4})
    builds = {m.split(">")[2] for m in g.legal_moves(st)
              if m.startswith("2,2>2,3>")}
    assert "2,4" not in builds, "cannot build on a cell holding a worker"
    assert "1,3" not in builds, "cannot build on an existing dome"

    # ---- (5) BUILD-then-DOME: level 3 -> 4 --------------------------------
    st = _play_state({(2, 2): 0, (0, 0): 1}, levels={(2, 3): 3})
    # move (2,2)->(3,3) (ground, not a climb) then build the level-3 cell (2,3)
    m = "2,2>3,3>2,3"
    assert m in g.legal_moves(st), "building on a level-3 cell must be legal"
    ns = g.apply_move(st, m)
    assert ns.level((2, 3)) == 4, "a build on a level-3 cell makes a dome (4)"

    # ---- (6) move ENCODING: 3-cell normal, 2-cell winning climb -----------
    # The mover must be at level 2 to step up one level onto the level-3 cell.
    st = _play_state({(2, 2): 0, (0, 0): 1}, levels={(2, 2): 2, (2, 3): 3})
    # moving up onto the level-3 cell (2,3) is a 2-cell WINNING climb (no build)
    assert "2,2>2,3" in g.legal_moves(st), "winning climb is a 2-cell path"
    # and there is NO 3-cell move that climbs onto (2,3) (no build after a win)
    assert not any(m.startswith("2,2>2,3>") for m in g.legal_moves(st)), \
        "a climb win must not also produce build variations"

    # ---- (7) CLIMB WIN: reach it via apply_move ---------------------------
    st = _play_state({(2, 2): 0, (0, 0): 1}, levels={(2, 2): 2, (2, 3): 3})
    ns = g.apply_move(st, "2,2>2,3")
    assert ns.winner == 0, "moving up onto a level-3 building wins immediately"
    assert ns.workers.get((2, 3)) == 0, "winner's worker ends on the level-3 cell"
    assert ns.level((2, 3)) == 3, "no build occurred on a winning climb"
    assert g.is_terminal(ns) and g.returns(ns) == [1.0, -1.0]
    # blue (player 1) climbing wins for blue
    st = _play_state({(0, 0): 0, (2, 2): 1}, levels={(2, 2): 2, (2, 3): 3},
                     to_move=1)
    ns = g.apply_move(st, "2,2>2,3")
    assert ns.winner == 1 and g.returns(ns) == [-1.0, 1.0]

    # ---- (7b) cannot climb >1 level: ground (0) -> level-3 is illegal -----
    st = _play_state({(2, 2): 0, (0, 0): 1}, levels={(2, 3): 3})
    assert "2,2>2,3" not in g.legal_moves(st), \
        "climbing from ground straight to level 3 (>1 up) must be illegal"

    # ---- (8) STUCK-player loss: no legal move -> terminal, opponent wins ---
    # Player 0's two workers are completely walled in by domes on every
    # neighbour, so neither can move at all -> P0 has no legal move and loses.
    # Worker A at (0,0): neighbours (1,0),(0,1),(1,1) all domes.
    # Worker B at (4,4): neighbours (3,4),(4,3),(3,3) all domes.
    domes = {(1, 0): 4, (0, 1): 4, (1, 1): 4,
             (3, 4): 4, (4, 3): 4, (3, 3): 4}
    st = _play_state({(0, 0): 0, (4, 4): 0,
                      (2, 0): 1, (0, 2): 1}, levels=domes, to_move=0)
    assert g.legal_moves(st) == [], "a fully walled-in player has no legal move"
    assert g.is_terminal(st), "no-legal-move state is terminal"
    assert g.returns(st) == [-1.0, 1.0], "the stuck player loses (opponent wins)"

    # ---- (8b) 'moved but cannot build' is filtered out of legal_moves -----
    # Sanity: when a worker DOES move next to a dome it can still build on its
    # vacated origin, so that move stays legal (origin always re-buildable).
    st = _play_state(
        {(0, 0): 0, (4, 4): 0, (2, 2): 1, (0, 4): 1},
        levels={(1, 0): 4, (0, 1): 4,            # (0,0) may only reach (1,1)
                (2, 0): 4, (0, 2): 4, (2, 1): 4, (1, 2): 4,
                (4, 3): 4, (3, 4): 4, (3, 3): 4},  # wall in worker B at (4,4)
        to_move=0,
    )
    assert any(m.startswith("0,0>1,1>") for m in g.legal_moves(st)), \
        "moving to (1,1) and building the vacated origin must be legal"

    # A worker boxed in by WORKERS on all 8 sides has no destination at all ->
    # genuinely stuck. (Domes alone can't fully trap a worker since its vacated
    # origin re-opens, but other workers persist, so they can.)
    st = _play_state(
        {(1, 1): 0,                       # the worker to move
         (0, 0): 1, (1, 0): 1, (2, 0): 1,  # surround (1,1)'s upper neighbours
         (0, 1): 1, (2, 1): 1,
         (0, 2): 1, (1, 2): 1, (2, 2): 1},  # and lower -> fully boxed by workers
        to_move=0,
    )
    # The single worker (1,1) has NO empty neighbour to move to at all.
    assert g.legal_moves(st) == [], \
        "a worker boxed in by workers on all 8 sides has no move -> stuck loss"
    assert g.is_terminal(st) and g.returns(st) == [-1.0, 1.0]

    # ---- (9) serialize round-trip (JSON-able), incl. levels + placement ---
    # placement-phase state
    d = g.serialize(g.initial_state())
    assert g.serialize(g.deserialize(d)) == d
    assert json.loads(json.dumps(d)) == d
    # mid-play state with levels
    st = _play_state({(0, 0): 0, (4, 4): 1}, levels={(2, 2): 3, (1, 1): 4})
    st.ply = 7
    d = g.serialize(st)
    assert g.serialize(g.deserialize(d)) == d
    assert json.loads(json.dumps(d)) == d
    assert d["levels"] == {"2,2": 3, "1,1": 4} and d["placed"] == 4

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
