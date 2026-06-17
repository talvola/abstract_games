"""The Game contract every module implements.

This is the single most important interface in the platform: it is what a game
package's ``game.py`` provides, what the generic MCTS opponent plays through,
and what the conformance harness checks. Keep it small and stable.

Authoring rules (also enforced/encouraged by ``agp validate``):

* ``apply_move`` MUST be pure: it returns a *new* state and never mutates the
  state passed in. (This lets the engine and search reuse states freely.)
* ``serialize`` MUST round-trip: ``deserialize(serialize(s))`` is equivalent to
  ``s`` and serializes identically. Output must be JSON-able.
* On a non-terminal state, ``legal_moves`` MUST be non-empty. If the player to
  move has no action, the game should advance past them (pass) inside
  ``apply_move`` / ``initial_state`` rather than returning an empty list.
* ``render`` returns a JSON-able RenderSpec dict; never pixels.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .types import Move, RenderSpec, State


class Game(ABC):
    """Rules of one game. Instances are stateless; all per-match data lives in
    the ``State`` objects produced by ``initial_state`` and ``apply_move``."""

    # ---- identity (mirrors manifest.json; manifest is the source of truth) ----
    uid: str = ""
    name: str = ""

    @property
    @abstractmethod
    def num_players(self) -> int:
        ...

    # ---- setup -------------------------------------------------------------
    @abstractmethod
    def initial_state(self, options: Optional[dict] = None, rng=None) -> State:
        """Return the starting state. ``options`` carries variant settings
        (e.g. board size); ``rng`` is a ``random.Random`` for random setups."""

    # ---- core loop ---------------------------------------------------------
    @abstractmethod
    def current_player(self, state: State) -> int:
        """Index of the player to move (0-based), or ``CHANCE`` for a pending
        random resolution."""

    @abstractmethod
    def legal_moves(self, state: State) -> list[Move]:
        """All legal moves in ``state``. Non-empty unless ``is_terminal``."""

    @abstractmethod
    def apply_move(self, state: State, move: Move, rng=None) -> State:
        """Return the new state after ``move``. Pure: must not mutate ``state``."""

    @abstractmethod
    def is_terminal(self, state: State) -> bool:
        ...

    @abstractmethod
    def returns(self, state: State) -> list[float]:
        """Per-player payoff at a terminal state (e.g. +1 win / -1 loss /
        0 draw). Length == ``num_players``."""

    # ---- persistence & notation -------------------------------------------
    @abstractmethod
    def serialize(self, state: State) -> dict:
        """JSON-able snapshot of ``state``."""

    @abstractmethod
    def deserialize(self, data: dict) -> State:
        ...

    def move_to_str(self, move: Move) -> str:
        return str(move)

    def parse_move(self, text: str) -> Move:
        return text

    # ---- presentation ------------------------------------------------------
    @abstractmethod
    def render(self, state: State, perspective: Optional[int] = None) -> RenderSpec:
        """A JSON-able RenderSpec describing the board for the generic renderer.
        ``perspective`` is the viewing player (for future hidden-info games)."""

    # ---- optional: hidden information -------------------------------------
    def player_view(self, state: State, player: int) -> State:
        """State as ``player`` is allowed to see it. Default: full information."""
        return state
