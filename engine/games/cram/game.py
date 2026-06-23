"""Cram — the impartial domino-covering game (a.k.a. plugg; popularised by
Martin Gardner in *Scientific American*).

Cram is the **impartial** cousin of Domineering. Two players alternately place
dominoes on an empty rectangular grid (default 6x6). The crucial difference from
Domineering: on a turn EITHER player may place a domino in EITHER orientation —
covering two empty orthogonally-adjacent on-board cells, horizontal OR vertical.
The move set is therefore the same for both players (the game is *impartial*).

* There are **no captures** and placed dominoes never move.
* **Normal play**: the player who cannot place a domino on their turn LOSES
  (equivalently, the last player to place a domino wins). There are no draws.

Each placement fills two cells, so the game is strictly bounded and always
terminates. A move is the two covered cells as a path, ``"c,r>c2,r2"`` (click
the two cells); the second cell is always orthogonally adjacent to the first.

**Parity theorem (the correctness anchor):** the one rigorously-proven result is
that on a board with BOTH dimensions even the SECOND player wins (mirror strategy
— reflect the opponent's domino through the board centre). Beyond that Cram has
no simple closed-form winner (e.g. 3x3, both odd, is a 2nd-player win, contra the
often-quoted "else first player wins"). ``selftest.py`` bakes exhaustive-search
outcomes for small boards; ``rules.md`` documents the details.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game


@dataclass
class CramState:
    width: int = 6
    height: int = 6
    board: dict = field(default_factory=dict)   # (c, r) -> owner (the placer)
    to_move: int = 0
    last: tuple = ()                              # cells covered by the last domino


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


# Accepted size option choices -> (width, height). Keys are option values.
SIZES = {
    "4x4": (4, 4),
    "5x5": (5, 5),
    "6x6": (6, 6),
    "4x6": (4, 6),
    "6x4": (6, 4),
}


class Cram(Game):
    uid = "cram"
    name = "Cram"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CramState:
        opts = options or {}
        size = opts.get("size", "6x6")
        w, h = SIZES.get(size, (6, 6))
        return CramState(width=w, height=h)

    def current_player(self, s: CramState) -> int:
        return s.to_move

    def _on_board(self, s: CramState, cell) -> bool:
        c, r = cell
        return 0 <= c < s.width and 0 <= r < s.height

    def legal_moves(self, s: CramState) -> list[str]:
        """Every empty domino placement, in EITHER orientation (impartial).

        To avoid listing each domino twice, an anchor cell (c, r) only generates
        its RIGHT neighbour (c+1, r) and its DOWN neighbour (c, r+1)."""
        moves = []
        for r in range(s.height):
            for c in range(s.width):
                if (c, r) in s.board:
                    continue
                # horizontal: (c, r) + (c+1, r)
                if c + 1 < s.width and (c + 1, r) not in s.board:
                    moves.append(f"{c},{r}>{c + 1},{r}")
                # vertical: (c, r) + (c, r+1)
                if r + 1 < s.height and (c, r + 1) not in s.board:
                    moves.append(f"{c},{r}>{c},{r + 1}")
        return moves

    def apply_move(self, s: CramState, move: str, rng=None) -> CramState:
        a_s, b_s = move.split(">")
        a, b = _cell(a_s), _cell(b_s)
        who = s.to_move
        # Validate: both cells on-board, empty, orthogonally adjacent.
        if not self._on_board(s, a) or not self._on_board(s, b):
            raise ValueError(f"off-board domino: {move}")
        if a in s.board or b in s.board:
            raise ValueError(f"overlapping domino: {move}")
        dc, dr = abs(a[0] - b[0]), abs(a[1] - b[1])
        if (dc, dr) not in ((1, 0), (0, 1)):
            raise ValueError(f"cells not orthogonally adjacent: {move}")
        board = dict(s.board)
        board[a] = who
        board[b] = who
        return CramState(
            width=s.width,
            height=s.height,
            board=board,
            to_move=1 - who,
            last=(a, b),
        )

    def is_terminal(self, s: CramState) -> bool:
        return len(self.legal_moves(s)) == 0

    def returns(self, s: CramState) -> list[float]:
        # Normal play: the player to move (who has no legal move) loses.
        loser = s.to_move
        winner = 1 - loser
        out = [0.0, 0.0]
        out[winner] = 1.0
        out[loser] = -1.0
        return out

    def serialize(self, s: CramState) -> dict:
        return {
            "width": s.width,
            "height": s.height,
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "to_move": s.to_move,
            "last": [f"{c},{r}" for (c, r) in s.last],
        }

    def deserialize(self, d: dict) -> CramState:
        return CramState(
            width=d["width"],
            height=d["height"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=tuple(_cell(x) for x in d.get("last", [])),
        )

    def describe_move(self, s: CramState, move: str) -> str:
        a_s, b_s = move.split(">")
        a, b = _cell(a_s), _cell(b_s)
        orient = "H" if a[1] == b[1] else "V"
        return f"P{s.to_move + 1} {orient}:{a[0] + 1},{a[1] + 1}-{b[0] + 1},{b[1] + 1}"

    def render(self, s: CramState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": v} for (c, r), v in s.board.items()]
        last_cells = {f"{c},{r}" for (c, r) in s.last}
        highlights = [{"cell": cid, "kind": "last-move"} for cid in last_cells]
        if self.is_terminal(s):
            winner = 1 - s.to_move
            caption = f"Player {winner + 1} wins (opponent cannot place a domino)"
        else:
            caption = f"Player {s.to_move + 1} to move"
        return {
            "board": {"type": "square", "width": s.width, "height": s.height},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
