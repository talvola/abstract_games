"""Kaooa correctness anchor (pure stdlib). There is no published perft for
Kaooa, so the anchor is a set of baked rule assertions:

  (1) the 10-point pentagram board: 5 outer tips (degree 2) + 5 inner points
      (degree 4), adjacency exactly along the drawn star segments;
  (2) asymmetric 1 VULTURE vs 7 CROWS, with a placement phase (crows dropped one
      at a time; the vulture enters after the first crow and is then active);
  (3) the vulture steps one point or jumps an adjacent crow in a straight line to
      the empty point beyond (draughts-style), removing it; crows only step, and
      only after all 7 are placed;
  (4) the vulture wins by capturing 4 crows; the crows win by trapping the
      vulture (no legal move). Includes a hand-built jump-capture and a
      vulture-trapped crow win.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.kaooa.game import (  # noqa: E402
    Kaooa, KState, ADJ, JUMPS, POINTS, TIPS, INNERS,
    CROW, VULTURE, CROWS_TOTAL, CROWS_TO_LOSE,
)

G = Kaooa()


def main():
    # --- (1) board topology -----------------------------------------------
    assert len(POINTS) == 10 and len(TIPS) == 5 and len(INNERS) == 5
    # each outer tip: degree 2 (two inner neighbours, no tip-tip edge)
    for t in TIPS:
        assert len(ADJ[t]) == 2, f"{t} should have degree 2"
        assert all(nb in INNERS for nb in ADJ[t]), f"{t} must link only inners"
    # each inner point: degree 4 (two tips + two inners)
    for i in INNERS:
        assert len(ADJ[i]) == 4, f"{i} should have degree 4"
        assert sum(nb in TIPS for nb in ADJ[i]) == 2, f"{i}: two tip links"
        assert sum(nb in INNERS for nb in ADJ[i]) == 2, f"{i}: two inner links"
    # adjacency is symmetric
    for p in ADJ:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric adjacency {p},{q}"
    # 15 undirected edges total
    edges = {frozenset((p, q)) for p in ADJ for q in ADJ[p]}
    assert len(edges) == 15, f"expected 15 edges, got {len(edges)}"
    # jumps are collinear: src and land are NOT adjacent, but src-over and
    # over-land both are (the over point sits between, on a star line)
    for (src, over), land in JUMPS.items():
        assert over in ADJ[src] and land in ADJ[over], "jump not along segments"
        assert land not in ADJ[src], "jump land must be 2 steps away"
        assert src != land

    # --- (2) initial position & placement flow ----------------------------
    s = G.initial_state()
    assert s.board == {} and s.in_hand == CROWS_TOTAL == 7
    assert s.to_move == CROW and not s.vulture_placed
    assert len(G.legal_moves(s)) == 10            # crow may drop on any point
    # crow places first
    s1 = G.apply_move(s, "I0")
    assert s1.board == {"I0": CROW} and s1.in_hand == 6 and s1.to_move == VULTURE
    # the vulture now drops (it enters after the first crow) onto any empty point
    assert not s1.vulture_placed
    assert "I0" not in G.legal_moves(s1) and "T0" in G.legal_moves(s1)
    s2 = G.apply_move(s1, "T0")
    assert s2.board["T0"] == VULTURE and s2.vulture_placed and s2.to_move == CROW
    # crows still being placed -> a crow turn is still a DROP, not a move
    assert all(">" not in m for m in G.legal_moves(s2))
    assert s2.in_hand == 6

    # vulture is active while crows place: give it a turn and confirm it can step
    sv = KState(board={"I0": VULTURE}, to_move=VULTURE, in_hand=3,
                vulture_placed=True)
    mv = G.legal_moves(sv)
    assert mv and all(">" in m for m in mv), "active vulture should step"

    # --- crows may only move once all 7 are placed ------------------------
    # in_hand>0 -> crow turn yields drops (single ids), never '>' moves
    sc = KState(board={"I0": CROW, "T0": VULTURE}, to_move=CROW, in_hand=3,
                vulture_placed=True)
    assert all(">" not in m for m in G.legal_moves(sc))
    # in_hand==0 -> crow turn yields slide moves
    sc2 = KState(board={"I0": CROW, "T0": VULTURE}, to_move=CROW, in_hand=0,
                 vulture_placed=True)
    cm = G.legal_moves(sc2)
    assert cm and all(">" in m for m in cm)
    # crows never produce a capturing (2-step) move: every crow slide is to an
    # adjacent point
    for m in cm:
        f, t = m.split(">")
        assert t in ADJ[f], "crow move must be a single step"

    # --- (3) vulture jump-capture (hand-built) ----------------------------
    # Stroke T0-I1-I0-T2: vulture on T0, crow on I1, land I0 empty -> jump.
    assert JUMPS[("T0", "I1")] == "I0"
    st = KState(board={"T0": VULTURE, "I1": CROW}, to_move=VULTURE, in_hand=0,
                vulture_placed=True)
    assert "T0>I0" in G.legal_moves(st), "vulture jump over adjacent crow missing"
    st2 = G.apply_move(st, "T0>I0")
    assert st2.board.get("I0") == VULTURE and "I1" not in st2.board
    assert st2.captured == 1, "the jumped crow must be removed"
    # a jump needs the landing point empty: block I0 -> no jump, but a step to a
    # free neighbour remains
    st_block = KState(board={"T0": VULTURE, "I1": CROW, "I0": CROW},
                      to_move=VULTURE, in_hand=0, vulture_placed=True)
    assert "T0>I0" not in G.legal_moves(st_block)
    assert "T0>I4" in G.legal_moves(st_block)     # I4 is T0's other neighbour
    # vulture cannot jump into a non-collinear direction / over empty
    st_step = KState(board={"T0": VULTURE}, to_move=VULTURE, in_hand=0,
                     vulture_placed=True)
    assert set(G.legal_moves(st_step)) == {"T0>I1", "T0>I4"}, "only the 2 steps"

    # --- (4a) vulture wins at 4 captures ----------------------------------
    near = KState(board={"T0": VULTURE, "I1": CROW}, to_move=VULTURE,
                  in_hand=0, vulture_placed=True, captured=3)
    won = G.apply_move(near, "T0>I0")             # 4th capture
    assert won.winner == VULTURE
    assert G.returns(won) == [-1.0, 1.0]          # seat0=crows lose, seat1=vulture

    # --- (4b) crows win by trapping the vulture ---------------------------
    # Vulture on T0 (neighbours I1, I4). Put crows on both neighbours AND on the
    # landing point beyond each so no jump escapes:
    #   over I1 lands I0 ; over I4 lands I3  (from the strokes through T0)
    assert JUMPS[("T0", "I4")] == "I3"
    trap = {"T0": VULTURE, "I1": CROW, "I4": CROW, "I0": CROW, "I3": CROW}
    sv_trap = KState(board=dict(trap), to_move=VULTURE, in_hand=0,
                     vulture_placed=True)
    assert G.legal_moves(sv_trap) == [], "vulture should be fully trapped"
    G._settle(sv_trap)
    assert sv_trap.winner == CROW, "trapped vulture -> crows win"
    assert G.returns(sv_trap) == [1.0, -1.0]

    # --- serialize round-trips --------------------------------------------
    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)
    assert G.serialize(G.deserialize(G.serialize(won))) == G.serialize(won)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
