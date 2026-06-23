"""Kamisado — Peter Burley's colour-chain race game (8x8).

Every cell of the 8x8 board is one of 8 colours laid out in a fixed, symmetric
pattern (a Latin square — each colour appears exactly once in every row and
column, and the board has 180-degree rotational symmetry). Each player owns 8
towers, one of each colour, that start on their home row sitting on the cell of
their own colour. A tower moves straight FORWARD (away from its own home row) or
FORWARD-diagonally, any number of EMPTY cells, never sideways, never backward,
and never jumping over another tower.

Colour chain: after a tower lands, the colour of the cell it stopped on dictates
which colour tower the OPPONENT must move next. The very first move of the game
is free (any tower). Deadlock: if the player to move cannot move their required
tower at all, they pass; the obligation then bounces — the opponent must move
the tower whose colour matches the cell the blocked tower is standing on. If
both players are simultaneously blocked (a true gridlock) the round is drawn.

Win: move one of your towers onto the opponent's home row (the far row).

Player 0 starts on row 0 (advances toward row 7); player 1 starts on row 7
(advances toward row 0). This package is the base single-round game; the
match / Sumo cumulative-scoring variants are not implemented (see rules.md).

Moves are clickable cell paths "from>to". A pass (only legal when the required
tower is blocked) is the action string "pass".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 8
NAMES = {0: "Black", 1: "White"}

# Colour codes: O=Orange B=Blue P=Purple K=Pink Y=Yellow R=Red G=Green N=Brown
# The fixed Kamisado board layout, row 0 (player 0's home row) at top to row 7
# (player 1's home row) at bottom, each string left-to-right (col 0..7).
LAYOUT = [
    "OBPKYRGN",
    "ROKGBYNP",
    "GKORPNYB",
    "KPBONGRY",
    "YRGNOBPK",
    "BYNPROKG",
    "PNYBGKOR",
    "NGRYKPBO",
]

# Display hex per colour code (used for board tints and tower fills).
COLOR_HEX = {
    "O": "#ff8c1a",  # orange
    "B": "#2e7bd6",  # blue
    "P": "#8a4fc4",  # purple
    "K": "#ff7fb0",  # pink
    "Y": "#f4d03f",  # yellow
    "R": "#e03b3b",  # red
    "G": "#3aa84a",  # green
    "N": "#8a5a2b",  # brown
}
COLOR_NAME = {
    "O": "Orange", "B": "Blue", "P": "Purple", "K": "Pink",
    "Y": "Yellow", "R": "Red", "G": "Green", "N": "Brown",
}
COLORS = "OBPKYRGN"

PLY_CAP = 600  # defensive draw cap


def cell_color(c: int, r: int) -> str:
    return LAYOUT[r][c]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _fwd(player: int) -> int:
    # player 0 advances toward larger r; player 1 toward smaller r
    return 1 if player == 0 else -1


def _far_row(player: int) -> int:
    return N - 1 if player == 0 else 0


def _start_board() -> dict:
    """(c, r) -> (player, colour-code). Each tower on the cell of its colour."""
    b = {}
    for c in range(N):
        b[(c, 0)] = (0, cell_color(c, 0))   # player 0 on row 0
        b[(c, 7)] = (1, cell_color(c, 7))   # player 1 on row 7
    return b


@dataclass
class KState:
    board: dict = field(default_factory=dict)   # (c, r) -> (player, colour)
    to_move: int = 0
    # colour the player to move is OBLIGED to move (None = free choice, only the
    # very first move of the game).
    required: Optional[str] = None
    winner: Optional[int] = None
    draw: bool = False
    ply: int = 0
    # the player who last actually moved a tower (not a pass); used to resolve a
    # full deadlock — that player loses the round.
    last_mover: Optional[int] = None


class Kamisado(Game):
    uid = "kamisado"
    name = "Kamisado"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> KState:
        return KState(board=_start_board(), to_move=0, required=None)

    def current_player(self, s: KState) -> int:
        return s.to_move

    # ----- movement -----------------------------------------------------
    def _tower_at(self, s: KState, c: int, r: int):
        return s.board.get((c, r))

    def _find_tower(self, s: KState, player: int, colour: str):
        for (c, r), (pl, col) in s.board.items():
            if pl == player and col == colour:
                return (c, r)
        return None

    def _moves_for_tower(self, s: KState, c: int, r: int) -> list:
        """All forward / forward-diagonal slides from (c,r) over empty cells."""
        player = s.board[(c, r)][0]
        dr = _fwd(player)
        out = []
        for dc in (-1, 0, 1):
            nc, nr = c + dc, r + dr
            while _on(nc, nr) and (nc, nr) not in s.board:
                out.append((nc, nr))
                nc += dc
                nr += dr
        return out

    def _required_tower_cell(self, s: KState):
        """Cell of the tower the player to move is obliged to move (or None when
        free)."""
        if s.required is None:
            return None
        return self._find_tower(s, s.to_move, s.required)

    def _movable_cells(self, s: KState) -> list:
        """Cells of towers the player to move is allowed to move this turn."""
        if s.required is None:
            return [(c, r) for (c, r), (pl, _) in s.board.items()
                    if pl == s.to_move]
        cell = self._required_tower_cell(s)
        return [cell] if cell is not None else []

    def legal_moves(self, s: KState) -> list[str]:
        if self.is_terminal(s):
            return []
        out = []
        for (c, r) in self._movable_cells(s):
            for (nc, nr) in self._moves_for_tower(s, c, r):
                out.append(f"{c},{r}>{nc},{nr}")
        if not out:
            # required tower is blocked -> the only legal action is to pass.
            out.append("pass")
        return out

    # ----- transitions --------------------------------------------------
    def apply_move(self, s: KState, move: str, rng=None) -> KState:
        board = dict(s.board)
        ply = s.ply + 1

        if move == "pass":
            # The required tower cannot move, so the player forfeits the turn.
            # The obligation bounces: the opponent must move the tower matching
            # the colour of the cell the blocked tower stands on.
            cell = self._required_tower_cell(s)
            bounce_colour = cell_color(cell[0], cell[1])
            nxt = KState(board=board, to_move=1 - s.to_move,
                         required=bounce_colour, ply=ply,
                         last_mover=s.last_mover)
            # Full deadlock: if the opponent ALSO cannot move their newly-required
            # tower, neither side can progress. Per the official rule, "the last
            # person to move a tower before the deadlock occurs loses that round."
            if not self._any_move(nxt):
                if nxt.last_mover is None:
                    nxt.draw = True            # no tower has ever moved (degenerate)
                else:
                    nxt.winner = 1 - nxt.last_mover
            if ply >= PLY_CAP:
                nxt.draw = True
            return nxt

        frm, to = (_cell(x) for x in move.split(">"))
        player, colour = board.pop(frm)
        board[to] = (player, colour)
        landed_colour = cell_color(to[0], to[1])

        if to[1] == _far_row(player):
            return KState(board=board, to_move=1 - player, required=landed_colour,
                          winner=player, ply=ply, last_mover=player)

        nxt = KState(board=board, to_move=1 - player, required=landed_colour,
                     ply=ply, last_mover=player)
        if ply >= PLY_CAP:
            nxt.draw = True
        return nxt

    def _any_move(self, s: KState) -> bool:
        for (c, r) in self._movable_cells(s):
            if self._moves_for_tower(s, c, r):
                return True
        return False

    def is_terminal(self, s: KState) -> bool:
        return s.winner is not None or s.draw

    def returns(self, s: KState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    # ----- serialization ------------------------------------------------
    def serialize(self, s: KState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, col] for (c, r), (pl, col) in s.board.items()},
            "to_move": s.to_move,
            "required": s.required,
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
            "last_mover": s.last_mover,
        }

    def deserialize(self, d: dict) -> KState:
        return KState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            required=d.get("required"),
            winner=d.get("winner"),
            draw=d.get("draw", False),
            ply=d.get("ply", 0),
            last_mover=d.get("last_mover"),
        )

    def describe_move(self, s: KState, move: str) -> str:
        if move == "pass":
            return "pass (blocked)"
        frm, to = (_cell(x) for x in move.split(">"))
        col = s.board[frm][1]
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{COLOR_NAME[col][0]}:{alg(frm)}-{alg(to)}"

    # ----- render -------------------------------------------------------
    def render(self, s: KState, perspective=None) -> dict:
        tints = {}
        for r in range(N):
            for c in range(N):
                tints[f"{c},{r}"] = COLOR_HEX[cell_color(c, r)]

        pieces = []
        for (c, r), (pl, col) in s.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": pl,
                "fill": COLOR_HEX[col],
                "stroke": "#111111" if pl == 0 else "#f5f5f5",
                "label": col,
            })

        highlights = []
        req_cell = self._required_tower_cell(s)
        if req_cell is not None and not self.is_terminal(s):
            highlights.append({"cell": f"{req_cell[0]},{req_cell[1]}",
                               "kind": "selected"})

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins (reached the far row)"
        elif s.draw:
            caption = "Draw"
        elif s.required is None:
            caption = f"{NAMES[s.to_move]} to move (free: any tower)"
        else:
            caption = (f"{NAMES[s.to_move]} to move "
                       f"({COLOR_NAME[s.required]} tower)")

        return {
            "board": {"type": "square", "width": N, "height": N,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
