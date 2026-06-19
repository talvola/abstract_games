"""Freeform (unenforced / honor-system) games — Game Courier's reach model.

A *freeform* game defines a board and a starting position but **no movement or
win rules**: either player may move any piece anywhere, on the honor system, and
the result is set by an explicit action (resign / agree a result). This is how
Game Courier hosts hundreds of variants with zero rule code, and it is the cheap
on-ramp for porting the long tail (see PLATFORM_PLAN §8 + FREEFORM_MODE.md). The
generic MCTS bot does not apply to freeform games, and the conformance harness
checks them on a separate, lighter path (it does not random-self-play to a
terminal — a freeform game has no algorithmic terminal).

A freeform author subclasses :class:`FreeformGame` and supplies only board
geometry + the opening position:

    class MyVariant(FreeformGame):
        uid = "my_variant"
        name = "My Variant"
        WIDTH = HEIGHT = 8
        def setup_board(self):
            b = {}
            b[(0, 0)] = (0, "R"); ...      # (col,row) -> (player, label)
            return b

Override :meth:`board_spec` for a non-square board (e.g. return
``{"type": "hex", "shape": "hexagon", "size": 7}``).

Moves (all strings, in the platform's clickable notation):

* ``"fc,fr>tc,tr"`` — move whatever is on the source cell to the destination
  (capturing anything there); **no legality check**. An optional ``"=X"`` suffix
  retypes the moved piece (promotion-as-relabel), e.g. ``"4,6>4,7=Q"``.
* ``"@fc,fr"`` — remove the piece on a cell.
* ``"pass"`` — yield the turn without moving.
* ``"resign"`` — the player to move resigns (the opponent wins).

``legal_moves`` returns only the discrete *action* tokens (``pass`` / ``resign``)
— the unrestricted board moves are validated structurally by the server, not
enumerated here (the cross-product would be huge and the UI uses free drag).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .game import Game


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class FState:
    board: dict = field(default_factory=dict)       # (c, r) -> (player, label)
    to_move: int = 0
    result: Optional[list] = None                    # per-player returns once over
    last: Optional[tuple] = None                     # (from, to) for highlighting
    ply: int = 0


class FreeformGame(Game):
    """Base for honor-system games: a board + opening position, no rules."""

    enforced = False            # marks the freeform path for conformance/server/bot
    NUM_PLAYERS = 2
    WIDTH = 8
    HEIGHT = 8
    SIDES = ("White", "Black")

    # ---- author supplies this ----------------------------------------------
    def setup_board(self) -> dict:
        raise NotImplementedError("a FreeformGame must define setup_board()")

    def board_spec(self) -> dict:
        """RenderSpec board geometry; override for hex/other boards."""
        return {"type": "square", "width": self.WIDTH, "height": self.HEIGHT}

    # ---- contract -----------------------------------------------------------
    @property
    def num_players(self) -> int:
        return self.NUM_PLAYERS

    def initial_state(self, options=None, rng=None) -> FState:
        return FState(board=dict(self.setup_board()), to_move=0)

    def current_player(self, state: FState) -> int:
        return state.to_move

    def legal_moves(self, state: FState) -> list:
        # Board moves are unrestricted (free drag, validated by shape elsewhere);
        # only the discrete actions are enumerated. Non-empty until terminal.
        if state.result is not None:
            return []
        return ["pass", "resign"]

    def apply_move(self, state: FState, move: str, rng=None) -> FState:
        board = dict(state.board)
        nxt = (state.to_move + 1) % self.NUM_PLAYERS
        last = None
        result = state.result

        if move == "pass":
            pass
        elif move == "resign":
            # the resigning player (to_move) loses; everyone else shares the win
            result = [1.0] * self.NUM_PLAYERS
            result[state.to_move] = -1.0
            nxt = state.to_move
        elif move.startswith("@"):
            board.pop(_cell(move[1:]), None)
        else:
            raw, _, promo = move.partition("=")
            fs, _, ts = raw.partition(">")
            frm, to = _cell(fs), _cell(ts)
            piece = board.pop(frm, None)
            if piece is not None:
                pl, label = piece
                board[to] = (pl, promo or label)
                last = (frm, to)

        return FState(board=board, to_move=nxt, result=result,
                      last=last, ply=state.ply + 1)

    def is_terminal(self, state: FState) -> bool:
        return state.result is not None

    def returns(self, state: FState) -> list:
        return list(state.result) if state.result is not None else [0.0] * self.NUM_PLAYERS

    # ---- persistence --------------------------------------------------------
    def serialize(self, state: FState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "result": list(state.result) if state.result is not None else None,
            "last": [list(state.last[0]), list(state.last[1])] if state.last else None,
            "ply": state.ply,
        }

    def deserialize(self, d: dict) -> FState:
        last = None
        if d.get("last"):
            (a, b), (c, e) = d["last"]
            last = ((a, b), (c, e))
        return FState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            result=list(d["result"]) if d.get("result") is not None else None,
            last=last,
            ply=d.get("ply", 0),
        )

    # ---- presentation -------------------------------------------------------
    def render(self, state: FState, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": t}
            for (c, r), (pl, t) in state.board.items()
        ]
        highlights = []
        if state.last:
            for cr in state.last:
                highlights.append({"cell": f"{cr[0]},{cr[1]}", "kind": "last-move"})
        names = self.SIDES
        if state.result is not None:
            r = state.result
            caption = "Draw" if all(x == 0 for x in r) else \
                f"{names[max(range(len(r)), key=lambda i: r[i])]} wins (resignation)"
        else:
            caption = f"{names[state.to_move]} to move — unenforced (honor system)"
        return {
            "board": self.board_spec(),
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
