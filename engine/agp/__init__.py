"""Abstract Games Platform -- engine core (Phase 0).

Public surface:
    Game            the contract every game module implements
    load            load a package (dir or .zip) -> (manifest, Game)
    check           run the conformance harness on a loaded game
    MCTSBot, RandomBot, play_match   generic agents + a match runner
"""

from .conformance import Report, check
from .game import Game
from .loader import PackageError, load
from .mcts import MCTSBot, RandomBot, play_match
from .types import CHANCE

__all__ = [
    "Game",
    "load",
    "PackageError",
    "check",
    "Report",
    "MCTSBot",
    "RandomBot",
    "play_match",
    "CHANCE",
]
