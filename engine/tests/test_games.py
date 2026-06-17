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
