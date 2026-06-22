"""Mū Tōrere correctness anchor (pure stdlib -- imports only agp + this game).

There is no published perft for Mū Tōrere, so the anchor is the four documented
move rules baked as plain assertions, plus loss-on-no-legal-move reached via
apply_move and the standard opening position. Fast (no game loops)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.mu_torere.game import (  # noqa: E402
    MuTorere, TState, POINTS, KEWAI, PUTAHI, ADJ, RING_NEIGHBOURS,
)

G = MuTorere()


def main():
    # --- topology ---------------------------------------------------------
    assert len(POINTS) == 9, POINTS
    assert len(KEWAI) == 8 and PUTAHI == "c"
    # each kewai: 3 neighbours (two ring + putahi); putahi: all 8 kewai
    for i in range(8):
        k = str(i)
        assert ADJ[k] == frozenset({str((i - 1) % 8), str((i + 1) % 8), PUTAHI}), \
            (k, ADJ[k])
    assert ADJ[PUTAHI] == frozenset(KEWAI), ADJ[PUTAHI]
    # adjacency symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- standard opening position ----------------------------------------
    st = G.initial_state()
    assert st.pos == {"0": 0, "1": 0, "2": 0, "3": 0,
                      "4": 1, "5": 1, "6": 1, "7": 1}, st.pos
    assert PUTAHI not in st.pos, "putahi must start empty"
    assert sum(1 for v in st.pos.values() if v == 0) == 4
    assert sum(1 for v in st.pos.values() if v == 1) == 4
    assert st.to_move == 0 and st.winner is None
    # player 0 men on contiguous kewai 0..3; player 1 on contiguous 4..7
    assert [p for p, v in sorted(st.pos.items()) if v == 0] == ["0", "1", "2", "3"]
    assert [p for p, v in sorted(st.pos.items()) if v == 1] == ["4", "5", "6", "7"]

    # --- rule (b): kewai -> empty putahi only when next to an enemy man ----
    # In the opening, kewai 0 (neighbours 7=enemy,1=own) and kewai 3
    # (neighbours 2=own,4=enemy) border an enemy; kewai 1 and 2 do not.
    opening_moves = set(G.legal_moves(st))
    assert "0>c" in opening_moves, "kewai 0 borders enemy -> may enter putahi"
    assert "3>c" in opening_moves, "kewai 3 borders enemy -> may enter putahi"
    assert "1>c" not in opening_moves, "kewai 1 has no enemy neighbour"
    assert "2>c" not in opening_moves, "kewai 2 has no enemy neighbour"
    # those are the ONLY two putahi-entry moves available in the opening
    assert {m for m in opening_moves if m.endswith(">c")} == {"0>c", "3>c"}
    # and no kewai->kewai moves exist in the opening (every kewai neighbour is
    # occupied) -- so the only legal moves are the two putahi entries
    assert opening_moves == {"0>c", "3>c"}, opening_moves

    # --- rule (a): kewai -> adjacent EMPTY kewai is always allowed ---------
    # Empty kewai 1, player 0 man on kewai 0, no enemy adjacency needed.
    st_a = TState(pos={"0": 0, "2": 1}, to_move=0)
    mv = set(G.legal_moves(st_a))
    assert "0>1" in mv, "kewai->adjacent empty kewai must be allowed"  # 1 is empty
    # 0's other ring neighbour is 7 (empty) -> also allowed
    assert "0>7" in mv

    # --- rule (b) negative: no enemy neighbour -> cannot enter putahi ------
    # Lone player-0 man on kewai 0 with only a friendly man nearby; putahi empty.
    st_b0 = TState(pos={"0": 0, "1": 0}, to_move=0)
    assert "0>c" not in set(G.legal_moves(st_b0)), \
        "no enemy neighbour -> putahi entry forbidden"
    # add an enemy on kewai 7 (a ring neighbour of 0) -> now allowed
    st_b1 = TState(pos={"0": 0, "1": 0, "7": 1}, to_move=0)
    assert "0>c" in set(G.legal_moves(st_b1)), \
        "enemy on ring neighbour -> putahi entry allowed"
    # the OTHER neighbour (1) being friendly is irrelevant; only enemy counts
    st_b2 = TState(pos={"0": 0, "1": 1}, to_move=0)  # 1 is enemy -> allowed
    assert "0>c" in set(G.legal_moves(st_b2))

    # --- rule (c): putahi -> any empty kewai is always allowed -------------
    st_c = TState(pos={"c": 0, "1": 1}, to_move=0)  # man on putahi, kewai 1 enemy
    cmoves = set(G.legal_moves(st_c))
    for k in KEWAI:
        if k != "1":  # 1 is occupied
            assert f"c>{k}" in cmoves, f"putahi->{k} should be allowed"
    assert "c>1" not in cmoves, "cannot move onto an occupied kewai"

    # --- apply_move slides a man and passes the turn ----------------------
    st2 = G.apply_move(st, "0>c")
    assert st2.pos.get("c") == 0 and "0" not in st2.pos, st2.pos
    assert st2.to_move == 1, "turn should pass to player 1"
    assert st2.ply == 1

    # --- loss on no legal move (reached via apply_move) -------------------
    # Construct a position where, after player 0 moves, player 1 is stuck.
    # Player 1 has one man on kewai 5; its neighbours 4 and 6 and the putahi are
    # all blocked -> after player 0's move, player 1 cannot move and loses.
    pre = TState(pos={"4": 0, "6": 0, "c": 0, "5": 1, "0": 0}, to_move=0)
    # Player 0 makes a harmless legal move (0>1) that leaves player 1 sealed:
    # player 1's only man (5) has neighbours 4(P0),6(P0),putahi(P0) all occupied.
    after = G.apply_move(pre, "0>1")
    assert after.to_move == 1
    assert G.legal_moves(after) == [], "player 1 should have no legal move"
    assert G.is_terminal(after), "stuck player -> terminal"
    assert after.winner == 0, f"mover (player 0) should win, got {after.winner}"
    assert G.returns(after) == [1.0, -1.0]

    # --- serialize round-trips --------------------------------------------
    s = G.apply_move(G.initial_state(), "0>c")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
