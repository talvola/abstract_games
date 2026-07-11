"""Veletas correctness anchors (pure stdlib: agp + this game only).

Anchored on the official nestorgames rulebook
(nestorgames.com/rulebooks/VELETAS_EN.pdf; Boardspace's copy is
byte-identical), including its worked claiming examples: biggest orthogonally
adjacent group claims; diagonally-adjacent groups are irrelevant; a tie (or no
adjacent group) gives the shooter to the trapper's OPPONENT.

Run by tests/test_games.py::test_package_selftests, and standalone:
    cd engine && PYTHONPATH=. python3 games/veletas/selftest.py
"""

import random
import time
from pathlib import Path

from agp.loader import load_from_dir

_M, G = load_from_dir(Path(__file__).resolve().parent)

BLACK, WHITE = 0, 1


def _play_state(size, shooters, stones, turn, black_seat=0):
    """Build a mid-game (play-phase) state via deserialize; claims/wins are
    then only ever produced by apply_move, as in real play."""
    return G.deserialize({
        "size": size, "shooters": shooters, "stones": stones,
        "phase": "play", "left": 0, "black_seat": black_seat,
        "turn": turn, "winner": None, "last": [], "ply": 20,
    })


# ---------------------------------------------------------------- opening ----
def test_opening_protocol():
    # 9x9: first player places 5//2 = 2 shooters (interior only), then 1 stone.
    st = G.initial_state({"size": 9})
    assert G.current_player(st) == 0
    legal = G.legal_moves(st)
    assert len(legal) == 49, legal  # 7x7 interior
    assert "0,0" not in legal and "8,4" not in legal and "4,4" in legal
    st = G.apply_move(st, "2,2")
    assert G.current_player(st) == 0  # same player, sub-move
    legal = G.legal_moves(st)
    assert len(legal) == 48 and "2,2" not in legal
    st = G.apply_move(st, "3,3")
    # both shooters down -> the Black stone, anywhere empty incl. perimeter
    legal = G.legal_moves(st)
    assert G.current_player(st) == 0
    assert len(legal) == 81 - 2 and "0,0" in legal
    st = G.apply_move(st, "0,0")
    # pie: player 2 chooses sides
    assert G.current_player(st) == 1
    assert sorted(G.legal_moves(st)) == ["stay", "swap"]
    pie = st

    # stay: seat 0 stays Black; White (seat 1) places 3 shooters + 1 stone,
    # then Black (seat 0) moves first.
    st = G.apply_move(pie, "stay")
    assert G.current_player(st) == 1
    assert len(G.legal_moves(st)) == 49 - 2  # interior minus the 2 shooters
    for mv in ("4,4", "5,5", "6,6", "8,8"):   # 3 shooters + White stone
        assert G.current_player(st) == 1
        st = G.apply_move(st, mv)
    assert st.phase == "play" and G.current_player(st) == 0

    # swap: seat 1 takes Black; White is seat 0, and after White's setup the
    # first regular turn is Black's = seat 1.
    st = G.apply_move(pie, "swap")
    assert st.black_seat == 1
    assert G.current_player(st) == 0
    for mv in ("4,4", "5,5", "6,6", "8,8"):
        assert G.current_player(st) == 0
        st = G.apply_move(st, mv)
    assert st.phase == "play" and G.current_player(st) == 1

    # 7x7 = 3 shooters (first places 1), 10x10 = 7 (first places 3).
    assert len(G.legal_moves(G.initial_state({"size": 7}))) == 25
    st7 = G.apply_move(G.initial_state({"size": 7}), "3,3")
    assert st7.left == 0  # only one first-player shooter on 7x7
    st10 = G.initial_state({"size": 10})
    assert st10.left == 3 and len(G.legal_moves(st10)) == 64

    # perimeter shooter is rejected outright
    try:
        G.apply_move(G.initial_state({"size": 9}), "0,4")
        raise AssertionError("perimeter setup shooter was accepted")
    except ValueError:
        pass


# ---------------------------------------------------- queen-move geometry ----
def test_queen_geometry():
    st = _play_state(7,
                     {"3,3": None, "3,5": None, "1,3": None},
                     {"5,3": BLACK, "3,1": WHITE}, turn=BLACK)
    legal = set(G.legal_moves(st))
    starts = {m.split(">")[1] for m in legal if m.startswith("3,3>")}
    # stones block movement: (5,3) stone kills the E ray beyond (4,3)
    assert "4,3" in starts and "5,3" not in starts and "6,3" not in starts
    # S ray blocked by the (3,1) stone
    assert "3,2" in starts and "3,1" not in starts and "3,0" not in starts
    # shooters are jumped, not landed on: W ray skips (1,3), reaches edge
    assert "2,3" in starts and "1,3" not in starts and "0,3" in starts
    # N ray skips the (3,5) shooter
    assert "3,4" in starts and "3,5" not in starts and "3,6" in starts
    # the vacated square is a legal shot target
    assert "3,3>4,3>3,3" in legal
    # shoot-only single cells: reachable empties from ANY unclaimed shooter
    assert "4,3" in legal and "0,3" in legal
    assert "5,3" not in legal and "1,3" not in legal   # stone / shooter cells
    assert "6,3" not in legal   # behind the stone from every shooter
    # no prefix traps: a single-cell move is never the start of a 3-part one
    singles = {m for m in legal if ">" not in m}
    assert all(not m.startswith(sgl + ">") for m in legal for sgl in singles)


# ------------------------------------------------------------- claiming ----
def test_claim_majority_group():
    # BLACK traps a cornered shooter; black's orth group (2) > white's (1).
    st = _play_state(7,
                     {"0,0": None, "4,4": None, "5,2": None},
                     {"1,0": BLACK, "0,1": WHITE}, turn=BLACK)
    st = G.apply_move(st, "1,1")   # shot from (4,4) along the diagonal
    d = G.serialize(st)
    assert d["shooters"]["0,0"] == BLACK
    assert d["shooters"]["4,4"] is None and d["shooters"]["5,2"] is None
    assert st.winner is None and st.turn == WHITE


def test_claim_tie_goes_to_opponent():
    # Rulebook: "the biggest black and white groups ... are tied, so the
    # shooter is claimed by the opponent" of the player who ended the turn.
    st = _play_state(7,
                     {"0,3": None, "1,3": None, "5,5": None},
                     {"0,2": BLACK, "1,2": BLACK, "0,4": WHITE, "1,4": WHITE},
                     turn=WHITE)
    st = G.apply_move(st, "2,3")   # WHITE's shot (from the (1,3) shooter) traps (0,3)
    d = G.serialize(st)
    assert d["shooters"]["0,3"] == BLACK      # tie 2-2 -> opponent of White
    assert d["shooters"]["1,3"] is None       # still has a move (NE ray)
    assert st.winner is None


def test_claim_diagonal_groups_irrelevant():
    # Rulebook: "White's group ... is irrelevant because it is only diagonally
    # adjacent." White traps the shooter with a 3-stone group touching it only
    # diagonally; Black's lone orthogonal stones (biggest group 1) claim it.
    st = _play_state(7,
                     {"0,0": None, "4,4": None, "5,2": None},
                     {"0,1": BLACK, "1,0": BLACK, "2,1": WHITE, "1,2": WHITE},
                     turn=WHITE)
    st = G.apply_move(st, "1,1")
    d = G.serialize(st)
    assert d["shooters"]["0,0"] == BLACK


def test_multi_claim_and_win():
    # One shot traps TWO shooters at once; both go to Black (group of 4),
    # reaching the 7x7 majority (2 of 3) -> Black's seat wins immediately.
    shooters = {"0,0": None, "0,1": None, "4,4": None}
    stones = {"0,2": BLACK, "1,0": BLACK, "1,2": BLACK}
    st = _play_state(7, dict(shooters), dict(stones), turn=BLACK, black_seat=0)
    st = G.apply_move(st, "1,1")
    d = G.serialize(st)
    assert d["shooters"]["0,0"] == BLACK and d["shooters"]["0,1"] == BLACK
    assert st.winner == 0 and G.is_terminal(st)
    assert G.returns(st) == [1.0, -1.0]
    # same position after a pie swap (Black = seat 1): the seat mapping flips
    st = _play_state(7, dict(shooters), dict(stones), turn=BLACK, black_seat=1)
    assert G.current_player(st) == 1
    st = G.apply_move(st, "1,1")
    assert st.winner == 1 and G.returns(st) == [-1.0, 1.0]


# --------------------------------------------------------- serialization ----
def test_serialize_roundtrip():
    st = _play_state(9, {"3,3": None, "5,5": BLACK, "2,6": None},
                     {"4,4": WHITE, "1,1": BLACK}, turn=WHITE, black_seat=1)
    d = G.serialize(st)
    assert G.serialize(G.deserialize(d)) == d


# --------------------------------------------------------------- playouts ----
def _playout(size, rng):
    st = G.initial_state({"size": size})
    plies = 0
    used = {"single": 0, "triple": 0}
    while not G.is_terminal(st):
        moves = G.legal_moves(st)
        assert moves, f"no legal moves in a non-terminal state (size {size})"
        mv = rng.choice(moves)
        if st.phase == "play":
            used["triple" if ">" in mv else "single"] += 1
        st = G.apply_move(st, mv)
        plies += 1
        assert plies <= size * size + 50, "playout failed to terminate"
    assert st.winner in (0, 1)
    return st.winner, plies, used


def test_playouts():
    rng = random.Random(20130713)
    t0 = time.time()
    for size, n in ((7, 500), (9, 50), (10, 10)):
        wins = [0, 0]
        tot_plies = 0
        used = {"single": 0, "triple": 0}
        for _ in range(n):
            w, plies, u = _playout(size, rng)
            wins[w] += 1
            tot_plies += plies
            for k in u:
                used[k] += u[k]
        assert used["single"] > 0 and used["triple"] > 0
        print(f"  {size}x{size}: {n} playouts, seat wins {wins[0]}/{wins[1]}, "
              f"avg plies {tot_plies / n:.1f}, moves used "
              f"shoot-only={used['single']} move+shoot={used['triple']}")
    print(f"  playouts took {time.time() - t0:.1f}s")


if __name__ == "__main__":
    test_opening_protocol()
    test_queen_geometry()
    test_claim_majority_group()
    test_claim_tie_goes_to_opponent()
    test_claim_diagonal_groups_irrelevant()
    test_multi_claim_and_win()
    test_serialize_roundtrip()
    test_playouts()
    print("veletas selftest: all tests passed")
