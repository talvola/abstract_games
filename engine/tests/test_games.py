"""Engine + reference-game tests. Run: ``PYTHONPATH=. python -m pytest`` (or
``python tests/test_games.py`` for a dependency-free smoke run)."""

from __future__ import annotations

import random
from pathlib import Path

from agp import MCTSBot, RandomBot, check, load, play_match

GAMES = Path(__file__).resolve().parent.parent / "games"


def _load(uid):
    return load(GAMES / uid)


def test_tictactoe_conforms():
    manifest, game = _load("tic_tac_toe")
    assert check(game, manifest, games=50).ok


def test_oust_conforms():
    manifest, game = _load("oust")
    assert check(game, manifest, games=30).ok


def test_chess_conforms():
    manifest, game = _load("los_alamos_chess")
    assert check(game, manifest, games=15).ok


def test_checkers_conforms():
    manifest, game = _load("checkers")
    assert check(game, manifest, games=20).ok


def test_foxsox_conforms_and_geometry():
    manifest, game = _load("foxsox")
    assert check(game, manifest, games=15).ok
    for n, want in [(4, 32), (5, 50), (9, 162)]:
        s = game.initial_state(options={"size": n})
        cells = game.render(s)["board"]["cells"]
        assert len(cells) == 2 * n * n == want         # rhombus of triangles
        assert all(len(c["points"]) == 3 for c in cells)  # triangular cells
        assert game.current_player(s) == 0             # geese move first
    # fox reaching the goal corner wins (returns favour the fox = player 1)
    fw = game.deserialize({"size": 4, "board": {"3,3": 1, "5,2": 0}, "to_move": 1,
                           "winner": None, "drawn": False, "ply": 0})
    assert game.apply_move(fw, "3,3>2,2").winner == 1


def test_goose_chase_conforms_and_geometry():
    manifest, game = _load("goose_chase")
    assert check(game, manifest, games=15).ok
    # cell counts per board match the ZRF; every cell renders as a pentagon
    want = {"2x2": 16, "3x2": 24, "3x3": 36, "4x3": 40,
            "4x4": 64, "5x4": 60, "5x5": 100, "6x5": 84}
    for board, n in want.items():
        s = game.initial_state(options={"board": board})
        cells = game.render(s)["board"]["cells"]
        assert len(cells) == n
        assert all(len(c["points"]) == 5 for c in cells)
        assert game.current_player(s) == 0  # geese move first
    # cell ids are numeric "col,row" coords (2x2: D9=3,2  E11=4,0  B8=1,3
    # C6=2,5  E5=4,6  B4=1,7  A6=0,5  E1=4,10); the ZRF label shows in the log.
    # The fox reaching the goal cell wins (returns favour the fox = player 1).
    fw = game.deserialize({"board_key": "2x2", "board": {"3,2": 1, "1,3": 0},
                           "to_move": 1, "winner": None, "drawn": False, "ply": 0})
    nxt = game.apply_move(fw, "3,2>4,0")  # D9 -> E11 (the goal)
    assert nxt.winner == 1 and game.returns(nxt) == [-1.0, 1.0]
    assert game.describe_move(fw, "3,2>4,0") == "F D9-E11"
    # geese move only sideways/away from the goal (never toward a lower row index)
    gg = game.deserialize({"board_key": "2x2", "board": {"4,10": 1, "2,5": 0},
                           "to_move": 0, "winner": None, "drawn": False, "ply": 0})
    assert set(game.legal_moves(gg)) == {"2,5>4,6", "2,5>1,7", "2,5>0,5"}


def test_fox_and_hounds_conforms_and_asymmetry():
    manifest, game = _load("fox_and_hounds")
    assert check(game, manifest, games=30).ok
    s = game.initial_state()
    assert game.current_player(s) == 0  # fox moves first
    # hounds move only forward (never to a lower row)
    h = game.deserialize({"board": {"1,0": 1, "4,7": 0}, "to_move": 1,
                          "winner": None, "drawn": False, "ply": 0})
    assert set(game.legal_moves(h)) == {"1,0>2,1", "1,0>0,1"}
    # fox reaching row 0 wins
    fw = game.deserialize({"board": {"1,1": 0, "3,0": 1}, "to_move": 0,
                           "winner": None, "drawn": False, "ply": 0})
    assert game.apply_move(fw, "1,1>0,0").winner == 0


def test_loa_conforms_and_option():
    manifest, game = _load("lines_of_action")
    assert check(game, manifest, games=12, seed=1).ok
    assert len(game.legal_moves(game.initial_state())) == 36  # known LOA opening count
    # sim_connection option: a move connecting both is a draw, or a win for mover
    b = {"board": {"3,3": 0, "5,3": 1}, "to_move": 0, "winner": None, "drawn": False, "ply": 0}
    draw = game.apply_move(game.deserialize({**b, "sim_win": False}), "3,3>5,3")
    win = game.apply_move(game.deserialize({**b, "sim_win": True}), "3,3>5,3")
    assert draw.drawn and draw.winner is None
    assert win.winner == 0 and not win.drawn


def test_hex_conforms_and_never_draws():
    manifest, game = _load("hex")
    assert check(game, manifest, games=20, seed=3).ok
    rng = random.Random(5)
    for _ in range(20):
        res = play_match(game, [RandomBot(rng), RandomBot(rng)], rng, options={"size": 7})
        assert res["result"] == "terminal" and 0.0 not in res["returns"]  # Hex can't draw


def test_checkers_forced_capture_and_multijump():
    _, game = _load("checkers")
    # a man with a jump available -> only the jump is legal; a double jump is one path
    s = game.deserialize({"board": {"1,1": [0, "m"], "2,2": [1, "m"], "2,4": [1, "m"],
                                    "0,0": [0, "k"], "7,7": [1, "k"]},
                          "to_move": 0, "halfmove": 0, "ply": 0})
    moves = game.legal_moves(s)
    assert all("x" not in m and ">" in m for m in moves)  # all are jumps (paths)
    assert "1,1>3,3>1,5" in moves  # the double jump as a single path


def test_oust_never_draws():
    # The official rules state draws cannot occur.
    _, game = _load("oust")
    rng = random.Random(7)
    for _ in range(60):
        res = play_match(game, [RandomBot(rng), RandomBot(rng)], rng,
                         options={"size": 4})
        assert res["result"] == "terminal"
        assert 0.0 not in res["returns"]  # someone always wins


def test_tictactoe_mcts_never_loses_as_x():
    # TTT is a draw under perfect play; a sound MCTS as X must never lose.
    _, game = _load("tic_tac_toe")
    rng = random.Random(1)
    for _ in range(12):
        res = play_match(game, [MCTSBot(rng, iterations=400), RandomBot(rng)], rng)
        assert res["returns"][0] >= 0.0  # X wins or draws, never loses


def test_apply_move_is_pure():
    _, game = _load("oust")
    rng = random.Random(0)
    s = game.initial_state(options={"size": 4})
    before = game.serialize(s)
    game.apply_move(s, game.legal_moves(s)[0])
    assert game.serialize(s) == before


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all tests passed")
