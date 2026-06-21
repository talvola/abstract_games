"""NoGo — the misère-capture anti-Go (a combinatorial Go-family game).

Played on an N×N grid (N = 7/9/11, option; 9 is the default). Black is player 0,
White is player 1; Black moves first. Groups and liberties use 4-orthogonal
adjacency, exactly as in Go.

THE ONE RULE THAT MATTERS — NO CAPTURE EVER HAPPENS:
On your turn you place one stone of your colour on an empty intersection, BUT a
placement is ILLEGAL if it would either
  (a) CAPTURE — leave any enemy group with zero liberties, or
  (b) SUICIDE — leave your own (just-formed) group with zero liberties.
Equivalently, every legal move must leave EVERY group on the board (yours and the
opponent's) with at least one liberty. Because no stone is ever removed, the board
only fills up and positions never repeat — so no ko rule is needed and the game
always terminates (≤ N² placements).

WIN (normal-play convention): the player to move who has NO legal placement
LOSES. Results are decisive — there are no draws.

Moves are single-cell placements "c,r" (one click).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class NoGoState:
    n: int = 9
    board: dict = field(default_factory=dict)  # (c, r) -> 0 (Black) / 1 (White)
    to_move: int = BLACK
    # winner is set lazily when the side to move has no legal placement.
    winner: Optional[int] = None
    ply: int = 0


def _on(n: int, c: int, r: int) -> bool:
    return 0 <= c < n and 0 <= r < n


def _group_has_liberty(board: dict, n: int, start, player: int) -> bool:
    """True if the group of `player`-stones connected to `start` has ≥1 liberty
    (an orthogonally-adjacent empty intersection). 4-adjacency flood fill."""
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for dc, dr in ORTHO:
            nc, nr = c + dc, r + dr
            if not _on(n, nc, nr):
                continue
            occ = board.get((nc, nr))
            if occ is None:
                return True  # found a liberty
            if occ == player and (nc, nr) not in seen:
                seen.add((nc, nr))
                stack.append((nc, nr))
    return False


def _is_legal(board: dict, n: int, c: int, r: int, player: int) -> bool:
    """Is placing `player`'s stone at the empty cell (c, r) legal under NoGo?

    Place the stone, then require that NO group ends with zero liberties:
      * every orthogonally-adjacent ENEMY group must still have a liberty
        (otherwise the move captures — illegal), and
      * the player's OWN group containing (c, r) must have a liberty
        (otherwise the move is suicide — illegal).
    Only groups touching (c, r) can change their liberty count, so checking the
    placed group plus the adjacent enemy groups is exhaustive.
    """
    nb = dict(board)
    nb[(c, r)] = player
    enemy = 1 - player
    for dc, dr in ORTHO:
        ac, ar = c + dc, r + dr
        if _on(n, ac, ar) and nb.get((ac, ar)) == enemy:
            if not _group_has_liberty(nb, n, (ac, ar), enemy):
                return False  # captures an enemy group
    if not _group_has_liberty(nb, n, (c, r), player):
        return False  # suicide
    return True


def _legal_cells(s: NoGoState):
    out = []
    for r in range(s.n):
        for c in range(s.n):
            if (c, r) in s.board:
                continue
            if _is_legal(s.board, s.n, c, r, s.to_move):
                out.append((c, r))
    return out


class NoGo(Game):
    uid = "nogo"
    name = "NoGo"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> NoGoState:
        n = 9
        if options and "size" in options:
            n = int(options["size"])
        return NoGoState(n=n)

    def current_player(self, s: NoGoState) -> int:
        return s.to_move

    def legal_moves(self, s: NoGoState) -> list[str]:
        if s.winner is not None:
            return []
        return [f"{c},{r}" for (c, r) in _legal_cells(s)]

    def apply_move(self, s: NoGoState, move: str, rng=None) -> NoGoState:
        c, r = _cell(move)
        board = dict(s.board)
        board[(c, r)] = s.to_move
        nxt = 1 - s.to_move
        # The opponent now moves. If they have no legal placement, they lose.
        nxt_state = NoGoState(n=s.n, board=board, to_move=nxt,
                              winner=None, ply=s.ply + 1)
        if not _legal_cells(nxt_state):
            nxt_state.winner = s.to_move  # mover wins; opponent is stuck
        return nxt_state

    def is_terminal(self, s: NoGoState) -> bool:
        if s.winner is not None:
            return True
        # Robust to hand-built states: a side with no legal placement is
        # terminal even if `winner` was never recorded by apply_move.
        return not _legal_cells(s)

    def _loser(self, s: NoGoState) -> int:
        """The losing player at a terminal state."""
        if s.winner is not None:
            return 1 - s.winner
        # No winner recorded -> the side to move is the one with no legal move.
        return s.to_move

    def returns(self, s: NoGoState) -> list[float]:
        loser = self._loser(s)
        return [-1.0, 1.0] if loser == BLACK else [1.0, -1.0]

    def serialize(self, s: NoGoState) -> dict:
        return {
            "n": s.n,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> NoGoState:
        return NoGoState(
            n=d["n"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", len(d["board"])),
        )

    def describe_move(self, s: NoGoState, move: str) -> str:
        c, r = _cell(move)
        letters = "ABCDEFGHJKLMNOPQRST"  # Go convention skips 'I'
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def render(self, s: NoGoState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        if self.is_terminal(s):
            winner = 1 - self._loser(s)
            caption = f"{names[winner]} wins (opponent has no legal move)"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": s.n, "height": s.n},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
