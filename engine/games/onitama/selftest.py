"""Onitama correctness anchor (pure stdlib). Checks the card-driven two-step turn
(pick a card, then move), the card-rotation (used card -> middle -> hand), the
per-player offset mirroring, capture, and both win conditions."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.onitama.game import Onitama, OniState, CARDS  # noqa: E402

G = Onitama()


def main():
    # --- setup ------------------------------------------------------------
    s = G.initial_state(rng=random.Random(1))
    assert len(s.board) == 10 and s.board[(2, 0)] == (0, True) and s.board[(2, 4)] == (1, True)
    assert len(s.hands[0]) == 2 and len(s.hands[1]) == 2 and s.middle
    # the five dealt cards are distinct
    assert len({*s.hands[0], *s.hands[1], s.middle}) == 5

    # --- two-step turn: pick a card, then move ----------------------------
    picks = G.legal_moves(s)
    assert all(m.startswith("use:") for m in picks) and len(picks) == 2
    s2 = G.apply_move(s, picks[0])
    assert s2.selected == picks[0][4:] and s2.to_move == 0
    moves = G.legal_moves(s2)
    assert all(">" in m or m == "cancel" for m in moves) and "cancel" in moves

    # --- offsets mirror for player 1 --------------------------------------
    st = OniState(board={(2, 2): (1, False), (2, 1): (0, True)},
                  hands={0: ["Tiger", "Crab"], 1: ["Crab", "Frog"]}, middle="Ox",
                  to_move=1, selected="Crab")
    # Crab canonical for p0: (0,1),(-2,0),(2,0). For p1 mirrored -> (0,-1),(2,0),(-2,0).
    dests = {m.split(">")[1] for m in G.legal_moves(st) if ">" in m}
    assert "2,1" in dests, dests          # (0,-1) toward p1's goal, also captures the master

    # --- card rotation: used card -> middle, old middle -> hand -----------
    s2 = G.apply_move(s, "use:" + s.hands[0][0])
    used = s2.selected
    old_middle = s.middle
    mv = next(m for m in G.legal_moves(s2) if ">" in m)
    s3 = G.apply_move(s2, mv)
    assert s3.middle == used and old_middle in s3.hands[0] and used not in s3.hands[0]
    assert s3.to_move == 1 and s3.selected is None

    # --- capture the enemy master wins ------------------------------------
    st = OniState(board={(2, 2): (0, True), (2, 3): (1, True)},
                  hands={0: ["Crab", "Tiger"], 1: ["Frog", "Ox"]}, middle="Cobra",
                  to_move=0, selected="Crab")              # Crab (0,1): (2,2)->(2,3)
    assert G.apply_move(st, "2,2>2,3").winner == 0

    # --- reaching the enemy temple with your master wins ------------------
    st = OniState(board={(2, 3): (0, True), (0, 0): (1, True)},
                  hands={0: ["Crab", "Tiger"], 1: ["Frog", "Ox"]}, middle="Cobra",
                  to_move=0, selected="Crab")              # (2,3)->(2,4) = enemy temple
    assert G.apply_move(st, "2,3>2,4").winner == 0
    # ...but a non-master reaching it does NOT win
    st = OniState(board={(2, 3): (0, False), (2, 0): (0, True), (0, 0): (1, True)},
                  hands={0: ["Crab", "Tiger"], 1: ["Frog", "Ox"]}, middle="Cobra",
                  to_move=0, selected="Crab")
    assert G.apply_move(st, "2,3>2,4").winner is None

    assert G.serialize(G.deserialize(G.serialize(s3))) == G.serialize(s3)
    print("onitama selftest OK")


if __name__ == "__main__":
    main()
