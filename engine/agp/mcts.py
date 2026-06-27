"""Generic agents that play *any* game implementing the Game contract.

``RandomBot`` picks a uniformly random legal move. ``MCTSBot`` runs UCT with
random playouts and backs up per-player payoffs, so it works for any number of
players and for games where the same player moves several times in a row (e.g.
Oust capture chains) -- it simply reads ``current_player`` at each node.

Pure stdlib. For stochastic / hidden-info games this plain UCT should later be
swapped for ISMCTS; the interface here stays the same.
"""

from __future__ import annotations

import math
import time
from typing import Optional

from .game import Game
from .types import Move, State


class RandomBot:
    def __init__(self, rng):
        self.rng = rng

    def select(self, game: Game, state: State) -> Move:
        return self.rng.choice(game.legal_moves(state))


class _Node:
    __slots__ = ("state", "player", "moves", "children", "visits", "value")

    def __init__(self, game: Game, state: State):
        self.state = state
        self.player = game.current_player(state)
        self.moves = game.legal_moves(state)
        self.children: dict[Move, "_Node"] = {}
        self.visits = 0
        # value[p] = total payoff for player p accumulated through this node
        self.value: list[float] = [0.0] * game.num_players


class MCTSBot:
    """UCT search with truncated, heuristic-evaluated rollouts.

    Two knobs keep heavy games (chess-family) responsive:

    * ``max_time`` -- a wall-clock budget (seconds). ``select`` returns the
      best move found so far once it is exceeded, so move time is bounded
      regardless of CPU speed or game length. ``None`` = no time limit (run the
      full ``iterations`` count, the old behaviour).
    * ``max_rollout`` -- random playouts stop after this many plies and the
      position is scored by ``game.heuristic(state)`` (if the game provides one;
      otherwise treated as a draw) instead of drifting ~400 random plies to a
      draw. Short rollouts + a real eval are far faster *and* stronger than long
      random rollouts that almost never reach a decisive terminal.
    """

    def __init__(self, rng, iterations: int = 800, c: float = 1.41,
                 max_rollout: int = 50, max_time: Optional[float] = None):
        self.rng = rng
        self.iterations = iterations
        self.c = c
        self.max_rollout = max_rollout
        self.max_time = max_time

    def select(self, game: Game, state: State) -> Move:
        root = _Node(game, state)
        if len(root.moves) == 1:
            return root.moves[0]

        deadline = None
        if self.max_time is not None:
            deadline = time.monotonic() + self.max_time

        for i in range(self.iterations):
            self._iterate(game, root)
            if deadline is not None and time.monotonic() >= deadline:
                break

        if not root.children:                     # ran out of time before expanding
            return self.rng.choice(root.moves)
        # Most-visited move (robust choice).
        return max(root.children.items(), key=lambda kv: kv[1].visits)[0]

    def _iterate(self, game: Game, root: _Node) -> None:
        node = root
        path = [node]

        # --- selection + expansion ---
        while True:
            if game.is_terminal(node.state):
                payoffs = game.returns(node.state)
                break
            untried = [m for m in node.moves if m not in node.children]
            if untried:
                move = self.rng.choice(untried)
                child = _Node(game, game.apply_move(node.state, move))
                node.children[move] = child
                path.append(child)
                payoffs = self._rollout(game, child.state)
                break
            node = self._uct_child(node)
            path.append(node)

        # --- backprop ---
        for n in path:
            n.visits += 1
            for p in range(game.num_players):
                n.value[p] += payoffs[p]

    def _uct_child(self, node: _Node) -> _Node:
        log_n = math.log(node.visits + 1)
        best, best_score = None, -math.inf
        for child in node.children.values():
            exploit = child.value[node.player] / child.visits
            explore = self.c * math.sqrt(log_n / child.visits)
            score = exploit + explore
            if score > best_score:
                best, best_score = child, score
        return best

    def _rollout(self, game: Game, state: State) -> list[float]:
        steps = 0
        while not game.is_terminal(state):
            if steps >= self.max_rollout:
                # Cutoff: score the position with the game's heuristic if it
                # exposes one, else treat as a draw (robust generic fallback).
                return self._evaluate(game, state)
            move = self.rng.choice(game.legal_moves(state))
            state = game.apply_move(state, move)
            steps += 1
        return game.returns(state)

    def _evaluate(self, game: Game, state: State) -> list[float]:
        h = getattr(game, "heuristic", None)
        if h is not None:
            try:
                val = h(state)
                if val is not None:
                    return val
            except Exception:
                pass
        return [0.0] * game.num_players


def play_match(game: Game, agents: list, rng, max_moves: int = 2000,
               options: Optional[dict] = None) -> dict:
    """Play one game; ``agents[i]`` controls player ``i``. Returns a summary."""
    state = game.initial_state(options=options, rng=rng)
    moves = 0
    while not game.is_terminal(state):
        if moves >= max_moves:
            return {"result": "move-cap", "moves": moves, "returns": None}
        p = game.current_player(state)
        move = agents[p].select(game, state)
        state = game.apply_move(state, move, rng=rng)
        moves += 1
    return {"result": "terminal", "moves": moves, "returns": game.returns(state)}
