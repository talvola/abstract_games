"""Core shared types for the Abstract Games Platform engine.

A *state* is any object a game chooses to use internally; the engine treats it
opaquely and only ever touches it through ``Game`` methods. A *move* is always a
short string in the game's own notation (e.g. ``"1,2"``). Keeping moves as
strings makes them trivial to store, log, transmit, and let a human type.
"""

from __future__ import annotations

from typing import Any

# A move is the game's canonical string notation for a single action.
Move = str

# A state is opaque to the engine.
State = Any

# current_player() returns this when the next thing to happen is a random
# (chance) resolution rather than a player decision. None of the Phase-0 games
# use it, but the contract reserves it so stochastic games slot in later.
CHANCE = -1

# A RenderSpec is a plain JSON-able dict describing the board so a single
# generic frontend renderer can draw any game. Phase-0 shape (intentionally
# small; may converge toward AbstractPlay's APRenderRep in Phase 1):
#
#   {
#     "board": {"type": "square", "width": 3, "height": 3}
#             | {"type": "hex", "shape": "hexagon", "size": 7},
#     "pieces":     [{"cell": "1,2", "owner": 0, "label": "X"}],
#     "highlights": [{"cell": "0,0", "kind": "last-move" | "legal" | ...}],
#     "caption": "Red to move",            # optional
#   }
RenderSpec = dict
