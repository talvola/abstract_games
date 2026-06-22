"""Crazyhouse correctness anchor (pure stdlib -- imports only agp + this game).

Perft node counts, both from the start (which equal standard-chess perft, since no
drop is reachable within 4 plies) and from a mid-game position whose pockets are
non-empty so the counts genuinely exercise drops. Every number here was verified
against python-chess's chess.variant.CrazyhouseBoard (see _diff_pychess.py, run
once with the project .venv) and is frozen as the regression anchor. Also checks
the capture->reserve flow, the no-pawn-on-back-rank drop rule, and that a promoted
piece reverts to a pawn when captured.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # engine/ for `agp`
from games.crazyhouse.game import Crazyhouse  # noqa: E402

G = Crazyhouse()


def perft(state, depth):
    if depth == 0:
        return 1
    if G.is_terminal(state):
        return 0
    return sum(perft(G.apply_move(state, m), depth - 1) for m in G.legal_moves(state))


def play(state, moves):
    for m in moves:
        state = G.apply_move(state, m)
    return state


def main():
    # 1) Start-position perft == standard chess (no drop reachable in <=4 plies).
    expect_start = {1: 20, 2: 400, 3: 8902, 4: 197281}
    s0 = G.initial_state()
    for d, want in expect_start.items():
        got = perft(s0, d)
        assert got == want, f"start perft depth {d}: {got} != {want}"

    # 2) Mid-game perft with non-empty pockets (1.e4 d5 2.exd5 Qxd5; both sides
    #    hold a pawn). Counts include legal pawn/piece drops. python-chess-verified.
    mid = play(s0, ["4,1>4,3", "3,6>3,4", "4,3>3,4", "3,7>3,4"])
    assert mid.hands == {0: {"P": 1}, 1: {"P": 1}}, mid.hands
    expect_mid = {1: 62, 2: 4715, 3: 197413}
    for d, want in expect_mid.items():
        got = perft(mid, d)
        assert got == want, f"mid perft depth {d}: {got} != {want}"

    # 3) A capture banks the captured piece into the capturer's reserve.
    after_capture = play(s0, ["4,1>4,3", "3,6>3,4", "4,3>3,4"])  # exd5
    assert after_capture.hands.get(0, {}).get("P") == 1, after_capture.hands

    # 4) A reserved pawn may be dropped on ranks 2..7 (rows 1..6) but never on the
    #    first/last rank -- even though d8 (row 7) is empty in this position.
    drops = [m for m in G.legal_moves(mid) if m.startswith("P@")]
    rows = {int(m.split("@")[1].split(",")[1]) for m in drops}
    assert rows and rows <= set(range(1, 7)), f"pawn drop rows {rows}"
    assert "P@3,7" not in drops and (3, 7) not in mid.board, "pawn dropped on rank 8"

    # 5) A promoted piece reverts to a pawn when captured. Hand-built endgame:
    #    white pawn on g7 promotes, black king captures it -> black gains a PAWN.
    from agp.chesslike import CState, WHITE, BLACK
    board = {(6, 6): (WHITE, "P"), (4, 0): (WHITE, "K"), (7, 7): (BLACK, "K")}
    st = CState(board=board, to_move=WHITE, hands={WHITE: {}, BLACK: {}})
    st = G.apply_move(st, "6,6>6,7=Q")          # g7-g8=Q (a promoted queen)
    assert (6, 7) in st.promoted and st.board[(6, 7)] == (WHITE, "Q")
    st = G.apply_move(st, "7,7>6,7")            # Kxg8: black captures the promoted Q
    assert st.hands[BLACK] == {"P": 1}, st.hands  # banked as a PAWN, not a queen
    assert (6, 7) not in st.promoted

    # 6) Serialize round-trips (including hands + promoted markers).
    assert G.serialize(G.deserialize(G.serialize(mid))) == G.serialize(mid)

    print("crazyhouse selftest OK")


if __name__ == "__main__":
    main()
