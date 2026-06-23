"""Seega — traditional Egyptian/Nubian custodial-capture game.

Two phases on an odd square board (5x5 default; 7 or 9 via the `size` option).

PHASE 1 — PLACEMENT. Starting from an empty board, players alternately place
TWO of their stones per turn on any empty cell EXCEPT the centre, until every
cell but the centre is filled. Each player ends with (size^2 - 1) / 2 stones.

PHASE 2 — MOVEMENT. A player moves one of their stones one step orthogonally
into an adjacent empty cell. CUSTODIAL capture is active: if the move flanks one
or more enemy stones between the moved stone and another friendly stone in a
straight orthogonal line with no gap, those enemies are removed. Multiple
directions can capture at once. A stone that moves INTO a sandwich is safe. The
CENTRE cell is a safe square — a stone standing on it can never be captured.

Ruleset choices (sources differ; the most commonly documented version is used,
flagged where genuinely ambiguous):
* First to MOVE in phase 2 = the player who placed their stones SECOND (player
  1). Placing first is a disadvantage, so the second placer opens the movement
  phase (matches the common heritage rule and online implementations). FLAGGED:
  Wikipedia's wording is ambiguous (it also mentions a "first move to the
  centre"); we use the second-placer-moves-first convention.
* SINGLE move per turn — we do NOT grant an extra move after a capture. Some
  sources allow chaining moves while captures continue; we keep one move per
  turn for a clean encoding and guaranteed termination. FLAGGED as a variant.
* If the player to move has NO legal move they LOSE (a blockade loss), matching
  the documented win condition "trapped so they cannot move". We do not use the
  pass / opponent-frees-a-stone variants.
* WIN: reduce the opponent below 2 stones (one stone can never capture, so the
  game is decided) OR blockade the opponent (no legal move). A no-progress ply
  cap in the movement phase draws to guarantee termination.

Encoding: placement move = a single cell id "c,r" (one click); the same player
places twice before the turn passes. Movement move = "from>to". Cells are
"col,row".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
PLACE, MOVE = "place", "move"
# No-progress cap in the MOVEMENT phase (plies since the last capture). Past this
# with no capture -> draw. Generous so genuine play is never cut short.
NO_PROGRESS_CAP = 120


@dataclass
class SeegaState:
    board: dict = field(default_factory=dict)   # (c, r) -> owner int (0/1)
    size: int = 5
    phase: str = PLACE
    to_move: int = 0
    placed_this_turn: int = 0    # placements made by to_move this turn (0 or 1)
    winner: Optional[int] = None
    no_progress: int = 0         # movement plies since the last capture


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


class Seega(Game):
    uid = "seega"
    name = "Seega"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SeegaState:
        size = 5
        if options and "size" in options:
            size = int(options["size"])
        if size not in (5, 7, 9):
            size = 5
        return SeegaState(board={}, size=size, phase=PLACE, to_move=0,
                          placed_this_turn=0)

    # ----- helpers -----
    def _centre(self, s: SeegaState):
        m = s.size // 2
        return (m, m)

    def _on(self, s: SeegaState, c, r) -> bool:
        return 0 <= c < s.size and 0 <= r < s.size

    def _per_player(self, s: SeegaState) -> int:
        return (s.size * s.size - 1) // 2

    def current_player(self, s: SeegaState) -> int:
        return s.to_move

    # ----- moves -----
    def _placement_moves(self, s: SeegaState) -> list:
        centre = self._centre(s)
        out = []
        for r in range(s.size):
            for c in range(s.size):
                if (c, r) == centre:
                    continue
                if (c, r) not in s.board:
                    out.append((c, r))
        return out

    def _movement_moves(self, s: SeegaState) -> list:
        out = []
        for (c, r), owner in s.board.items():
            if owner != s.to_move:
                continue
            for dc, dr in ORTHO:
                cc, rr = c + dc, r + dr
                if self._on(s, cc, rr) and (cc, rr) not in s.board:
                    out.append(((c, r), (cc, rr)))
        return out

    def legal_moves(self, s: SeegaState) -> list[str]:
        if self.is_terminal(s):
            return []
        if s.phase == PLACE:
            return [f"{c},{r}" for (c, r) in self._placement_moves(s)]
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._movement_moves(s)]

    # ----- apply -----
    def apply_move(self, s: SeegaState, move: str, rng=None) -> SeegaState:
        if s.phase == PLACE:
            return self._apply_place(s, move)
        return self._apply_move(s, move)

    def _begin_movement(self, board: dict, size: int) -> SeegaState:
        # The player who placed SECOND (player 1) opens the movement phase.
        ns = SeegaState(board=board, size=size, phase=MOVE, to_move=1,
                        placed_this_turn=0, no_progress=0)
        # If the opener somehow has no move, decide immediately (blockade).
        if not self._movement_moves(ns):
            ns.winner = 1 - ns.to_move
        return ns

    def _apply_place(self, s: SeegaState, move: str) -> SeegaState:
        cell = _cell(move)
        board = dict(s.board)
        board[cell] = s.to_move
        placed = s.placed_this_turn + 1

        empties = (s.size * s.size - 1) - len(board)  # non-centre empties left
        if empties == 0:
            return self._begin_movement(board, s.size)

        if placed >= 2:
            # turn passes to the other player
            return SeegaState(board=board, size=s.size, phase=PLACE,
                              to_move=1 - s.to_move, placed_this_turn=0)
        # one more placement by the same player
        return SeegaState(board=board, size=s.size, phase=PLACE,
                          to_move=s.to_move, placed_this_turn=placed)

    def _apply_move(self, s: SeegaState, move: str) -> SeegaState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        owner = board.pop(frm)
        board[to] = owner
        centre = self._centre(s)

        # active custodial capture around the destination, each ortho direction.
        captured = 0
        for dc, dr in ORTHO:
            mid = (to[0] + dc, to[1] + dr)
            beyond = (to[0] + 2 * dc, to[1] + 2 * dr)
            if mid == centre:
                continue  # the centre is a safe square: never captured
            if board.get(mid) == (1 - owner) and board.get(beyond) == owner:
                del board[mid]
                captured += 1

        # win checks
        opp = 1 - owner
        opp_count = sum(1 for v in board.values() if v == opp)
        winner = None
        if opp_count < 2:
            winner = owner
        else:
            no_progress = 0 if captured else s.no_progress + 1
            nxt = SeegaState(board=board, size=s.size, phase=MOVE,
                             to_move=opp, placed_this_turn=0,
                             no_progress=no_progress)
            if not self._movement_moves(nxt):
                nxt.winner = owner  # opponent blockaded
            return nxt

        return SeegaState(board=board, size=s.size, phase=MOVE, to_move=opp,
                          placed_this_turn=0, winner=winner,
                          no_progress=0)

    # ----- terminal -----
    def is_terminal(self, s: SeegaState) -> bool:
        if s.winner is not None:
            return True
        if s.phase == MOVE and s.no_progress >= NO_PROGRESS_CAP:
            return True
        return False

    def returns(self, s: SeegaState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]   # no-progress cap -> draw
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    # ----- serialize -----
    def serialize(self, s: SeegaState) -> dict:
        return {
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "size": s.size,
            "phase": s.phase,
            "to_move": s.to_move,
            "placed_this_turn": s.placed_this_turn,
            "winner": s.winner,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> SeegaState:
        return SeegaState(
            board={_cell(k): v for k, v in d["board"].items()},
            size=d.get("size", 5),
            phase=d.get("phase", PLACE),
            to_move=d.get("to_move", 0),
            placed_this_turn=d.get("placed_this_turn", 0),
            winner=d.get("winner"),
            no_progress=d.get("no_progress", 0),
        )

    def describe_move(self, s: SeegaState, move: str) -> str:
        if s.phase == PLACE:
            return f"place {move}"
        frm, to = move.split(">")
        return f"{frm}-{to}"

    # ----- render -----
    def render(self, s: SeegaState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": v} for (c, r), v in s.board.items()]
        centre = self._centre(s)
        names = {0: "Player 1", 1: "Player 2"}
        if self.is_terminal(s):
            if s.winner is None:
                caption = "Draw"
            else:
                caption = f"{names[s.winner]} wins"
        elif s.phase == PLACE:
            left = 2 - s.placed_this_turn
            caption = (f"Placement — {names[s.to_move]} places "
                       f"({left} stone{'s' if left != 1 else ''} this turn)")
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": [{"cell": f"{centre[0]},{centre[1]}", "kind": "goal"}],
            "caption": caption,
        }
