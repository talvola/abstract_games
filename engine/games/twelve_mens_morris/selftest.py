"""Twelve Men's Morris correctness anchor (pure stdlib -- imports only agp + this
game, and nine_mens_morris for a core cross-check). No published perft exists for
this variant, so the anchor is its defining differences from Nine Men's Morris:

  * the four added corner diagonals produce four extra, VALID diagonal mills
    (a diagonal three-in-a-line is a real mill that lets you remove an enemy man);
  * the eight corner points gain a cross-ring adjacency (degree 2 -> 3);
  * twelve men per side in the placement phase;
  * reduce-opponent-to-two win and no-legal-move win still hold;
  * the ring/spoke CORE (the 16 Nine Men's Morris mills + its adjacencies) is
    preserved exactly -- the diagonals are purely additive.

All baked as plain asserts. Fast (no game loops)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.twelve_mens_morris.game import (  # noqa: E402
    TwelveMensMorris, MState, POINTS, ADJ, MILLS,
)
from games.nine_mens_morris.game import (  # noqa: E402
    ADJ as NMM_ADJ, MILLS as NMM_MILLS,
)

G = TwelveMensMorris()

# The four corner diagonals (outer-corner, middle-corner, inner-corner).
DIAGONALS = [
    ("0,0", "1,1", "2,2"),   # top-left
    ("6,0", "5,1", "4,2"),   # top-right
    ("6,6", "5,5", "4,4"),   # bottom-right
    ("0,6", "1,5", "2,4"),   # bottom-left
]


def main():
    # --- twelve men per side ---------------------------------------------
    assert G.MEN == 12, G.MEN

    # --- topology --------------------------------------------------------
    assert len(POINTS) == 24, len(POINTS)
    # 16 Nine Men's Morris mills + 4 new diagonals = 20
    assert len(MILLS) == 20, len(MILLS)

    mill_set = {frozenset(m) for m in MILLS}
    # every diagonal is present as a mill
    for d in DIAGONALS:
        assert frozenset(d) in mill_set, f"diagonal {d} not a mill"
    # exactly the four diagonals are new vs Nine Men's Morris
    nmm_set = {frozenset(m) for m in NMM_MILLS}
    assert mill_set - nmm_set == {frozenset(d) for d in DIAGONALS}, "unexpected mills"
    assert nmm_set <= mill_set, "Nine Men's Morris mills not preserved"

    # mills-per-point: corners lie on 3 (two ring edges + a diagonal),
    # everyone else still on 2.
    corners = {p for d in DIAGONALS for p in d}
    middle_corners = {d[1] for d in DIAGONALS}   # the diagonal's middle point
    for p in POINTS:
        n = sum(1 for m in MILLS if p in m)
        if p in corners:
            assert n == 3, f"corner {p} in {n} mills"
        else:
            assert n == 2, f"{p} in {n} mills"

    # --- adjacency: diagonals are purely additive over Nine Men's Morris -
    for p in POINTS:
        assert NMM_ADJ[p] <= ADJ[p], f"core adjacency lost at {p}"
        extra = set(ADJ[p]) - set(NMM_ADJ[p])
        if p in middle_corners:
            # middle corner gains both its outer- and inner-corner diagonal nbrs
            assert len(extra) == 2, f"middle corner {p} extra adj {extra}"
        elif p in corners:
            # outer/inner corner gains the single (middle) diagonal neighbour
            assert len(extra) == 1, f"corner {p} extra adj {extra}"
        else:
            assert extra == set(), f"non-corner {p} gained {extra}"
    # outer/inner corners now degree 3, middle corners degree 4 (two diagonal
    # neighbours + two ring edges)
    deg = {p: len(ADJ[p]) for p in POINTS}
    assert deg["0,0"] == 3 and deg["6,6"] == 3, "outer corner degree"
    assert deg["2,2"] == 3 and deg["4,4"] == 3, "inner corner degree"
    assert deg["1,1"] == 4 and deg["5,5"] == 4, "middle corner degree"
    # adjacency symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- a diagonal three-in-a-line IS a mill and removes an enemy man ----
    #  White has two of the top-left diagonal placed; completing it mills.
    st = MState(pos={"0,0": 0, "1,1": 0, "3,1": 1}, to_move=0, placed=[2, 1])
    st2 = G.apply_move(st, "2,2")            # completes the 0,0-1,1-2,2 diagonal
    assert st2.removing and st2.to_move == 0, "diagonal mill should keep the turn"
    # the lone enemy man (not in any mill) is the legal removal target
    assert G.legal_moves(st2) == ["3,1"], G.legal_moves(st2)
    st3 = G.apply_move(st2, "3,1")          # remove it
    assert "3,1" not in st3.pos and st3.to_move == 1, "removal failed"

    # a diagonal mill is detected from any of its three points
    for d in DIAGONALS:
        pos = {d[0]: 0, d[1]: 0, d[2]: 0}
        for pt in d:
            assert G._is_mill(pos, pt, 0), f"diagonal {d} not seen at {pt}"

    # --- removal restriction still holds (cannot take a man in a mill) ----
    pos = {"0,0": 0, "1,1": 0, "2,2": 0,    # White diagonal mill
           "3,1": 1, "3,5": 1}              # two Black men, neither in a mill
    st = MState(pos=dict(pos), to_move=0, placed=[3, 2], removing=True)
    assert set(G.legal_moves(st)) == {"3,1", "3,5"}, G.legal_moves(st)

    # if the only enemy men are all in a mill, any may be taken
    pos = {"0,0": 0, "1,1": 0, "2,2": 0,    # White diagonal mill (mover)
           "6,0": 1, "5,1": 1, "4,2": 1}    # Black: entirely a diagonal mill
    st = MState(pos=dict(pos), to_move=0, placed=[3, 3], removing=True)
    assert set(G.legal_moves(st)) == {"6,0", "5,1", "4,2"}, G.legal_moves(st)

    # --- win by reduction to two men -------------------------------------
    #  Black has 3 men; White's mill removal leaves Black with 2 -> White wins.
    st = MState(pos={"0,0": 0, "1,1": 0, "2,2": 0,        # White diagonal mill
                     "3,1": 1, "5,5": 1, "0,3": 1},
                to_move=0, placed=[12, 12], removing=True)
    st2 = G.apply_move(st, "3,1")           # Black drops to 2 men
    assert st2.winner == 0, f"winner={st2.winner}"
    assert G.returns(st2) == [1.0, -1.0]

    # --- win by leaving the opponent with no legal move ------------------
    #  Black (to move, 3 men, flying OFF) is completely blocked.
    G.FLYING = False
    #  Build the block precisely from the adjacency table to avoid mistakes:
    #  surround three Black men so every neighbour is occupied by White.
    black = ["3,1", "5,3", "3,5"]
    pos = {b: 1 for b in black}
    for b in black:
        for q in ADJ[b]:
            if q not in pos:
                pos[q] = 0
    st = MState(pos=pos, to_move=1, placed=[12, 12])
    assert G._on_board(st, 1) == 3, "black should have 3 men"
    assert G.legal_moves(st) == [], "black should be fully blocked (flying off)"
    # _settle marks the stuck player as the loser
    settled = G._settle(MState(pos=dict(pos), to_move=1, placed=[12, 12],
                               reps={}))
    assert settled.winner == 0, f"no-move win winner={settled.winner}"
    G.FLYING = True

    # --- full twelve-man placement phase ---------------------------------
    #  Drive a real game, preferring placements that do NOT complete a mill so
    #  both sides reach 12 placed men. Confirms 12-per-side placement and that
    #  the phase only flips to movement once both have placed all twelve.
    G2 = TwelveMensMorris()
    st = G2.initial_state()
    guard = 0
    while G2._phase_placing(st, 0) or G2._phase_placing(st, 1):
        guard += 1
        assert guard < 200, "placement phase did not complete"
        if G2.is_terminal(st):
            break
        # while still placing, the mover must be in the placing phase
        if st.removing:
            st = G2.apply_move(st, G2.legal_moves(st)[0])   # forced removal
            continue
        pl = st.to_move
        moves = G2.legal_moves(st)
        if not G2._phase_placing(st, pl):
            # this side has finished placing but the other has not -> it makes a
            # movement move; just take any legal move to keep the game going.
            st = G2.apply_move(st, moves[0])
            continue
        # prefer a placement that does not complete a mill (to avoid stalling
        # the board via captures), else take any legal placement
        chosen = None
        for m in moves:
            if ">" in m:
                continue
            trial = dict(st.pos); trial[m] = pl
            if not G2._is_mill(trial, m, pl):
                chosen = m
                break
        st = G2.apply_move(st, chosen if chosen is not None else moves[0])
    assert st.placed == [12, 12], st.placed
    assert not G2._phase_placing(st, 0) and not G2._phase_placing(st, 1)

    # --- full-board deadlock is a DRAW, not a loss -----------------------
    #  All 24 points occupied, placement done, no removal pending: nobody can
    #  slide. Traditional rule scores this a draw (the variant's drawishness),
    #  NOT a loss for the player to move.
    full = {p: (i % 2) for i, p in enumerate(POINTS)}     # 12 each, board full
    fs = MState(pos=full, to_move=0, placed=[12, 12], removing=False)
    assert len(fs.pos) == 24
    assert G.legal_moves(fs) == [], "full board should have no legal moves"
    assert G.is_terminal(fs), "full board should be terminal"
    assert fs.winner is None, "full-board deadlock must not credit a winner"
    assert G.returns(fs) == [0.0, 0.0], f"full board must draw, got {G.returns(fs)}"
    #  ...but a player blocked with empty points remaining still LOSES.
    assert settled.winner == 0, "blocked-with-empty-squares is still a loss"

    # --- serialize round-trips -------------------------------------------
    s = G.apply_move(G.apply_move(G.initial_state(), "0,0"), "6,6")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
