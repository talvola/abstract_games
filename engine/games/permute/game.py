"""Permute — Eric Silverman (2020). A game about twisting things.

An n×n board (9 default, 13 optional) starts COMPLETELY FULL of stones in a
two-colour chequerboard. A "face" is any 2×2 block of cells fully on the board.
Each turn the mover twists one face — rotates its 4 stones 90° clockwise or
anticlockwise, like a face of a 2×2 Rubik's Cube — then MUST bandage one of
their OWN stones in the just-twisted face; a bandaged stone is permanently
locked and any face containing it can never be twisted again.

A face may be twisted only if it (a) contains no bandaged stone and (b) is not
all one colour (on a two-colour board "not monochrome" already implies it holds
at least one stone of EACH player, so the set of twistable faces is the same
for both players). The first player moves first; after their first move the
second player may play "swap" (pie rule) to take over the opening position.

The game ends when no face can be twisted. Scoring is a Catchup-style cascade:
compare each side's largest orthogonally-connected group; if tied, the
second-largest, then the third, ... — the first difference wins. A tie all the
way down is a draw (only possible on even-sided boards; 9 and 13 are drawless).

Colour mapping (source rules use Orange/Yellow): seat 0 = Orange (moves first),
seat 1 = Yellow. Yellow sits on the (col+row)-even cells, so on an odd board
the SECOND player has the extra stone (Metzger's balance suggestion).

Move encoding: "ax,ay>sx,sy=CW" — ax,ay is the face's bottom-left (anchor)
cell, sx,sy the mover's stone (pre-twist position) to bandage after the twist,
and the =CW/=CCW suffix the rotation direction. Termination is guaranteed:
every twist bandages one stone forever, so a game lasts at most n²(+1) plies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from agp.game import Game

ORANGE, YELLOW = 0, 1  # seat 0 = Orange (first player), seat 1 = Yellow
CW, CCW = "CW", "CCW"


def _cell(s: str) -> tuple[int, int]:
    x, y = s.split(",")
    return int(x), int(y)


def _face(ax: int, ay: int) -> list[tuple[int, int]]:
    """The 4 cells of the face anchored (bottom-left) at (ax, ay):
    A=(ax,ay) BL, B=(ax+1,ay) BR, C=(ax,ay+1) TL, D=(ax+1,ay+1) TR."""
    return [(ax, ay), (ax + 1, ay), (ax, ay + 1), (ax + 1, ay + 1)]


def _dest(ax: int, ay: int, sx: int, sy: int, direction: str) -> tuple[int, int]:
    """Where the stone at (sx,sy) inside face (ax,ay) lands after the twist.
    Screen convention: row y increases upward, so CW sends BL->TL->TR->BR->BL."""
    a, b, c, d = _face(ax, ay)
    cw = {a: c, c: d, d: b, b: a}
    if direction == CW:
        return cw[(sx, sy)]
    return {v: k for k, v in cw.items()}[(sx, sy)]


def _rotate(board: tuple, n: int, ax: int, ay: int, direction: str) -> tuple:
    """Return a new board tuple with face (ax,ay) twisted 90° in ``direction``."""
    out = list(board)
    for (sx, sy) in _face(ax, ay):
        dx, dy = _dest(ax, ay, sx, sy, direction)
        out[dy * n + dx] = board[sy * n + sx]
    return tuple(out)


def _face_twistable(board: tuple, bandaged: frozenset, n: int, ax: int, ay: int) -> bool:
    """A face may be twisted iff it contains no bandaged stone and is not
    monochrome. (Not-monochrome on a 2-colour board == contains a stone of
    BOTH players, so twistability is the same for both seats.)"""
    idxs = [y * n + x for (x, y) in _face(ax, ay)]
    if any(i in bandaged for i in idxs):
        return False
    owners = {board[i] for i in idxs}
    return len(owners) > 1


def _group_sizes(board: tuple, n: int, player: int) -> list[int]:
    """Sizes of ``player``'s orthogonally-connected groups, sorted descending.
    Bandaged stones count like any other stone (bandaging only locks twisting)."""
    seen = [False] * (n * n)
    sizes = []
    for i in range(n * n):
        if seen[i] or board[i] != player:
            continue
        comp = 0
        stack = [i]
        seen[i] = True
        while stack:
            j = stack.pop()
            comp += 1
            x, y = j % n, j // n
            for (nx, ny) in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < n and 0 <= ny < n:
                    k = ny * n + nx
                    if not seen[k] and board[k] == player:
                        seen[k] = True
                        stack.append(k)
        sizes.append(comp)
    sizes.sort(reverse=True)
    return sizes


def _compare(a: list[int], b: list[int]) -> int:
    """Catchup-style cascade: largest group, then 2nd, 3rd, ... (missing
    entries count 0). +1 if a wins, -1 if b wins, 0 = dead tie (draw)."""
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x != y:
            return 1 if x > y else -1
    return 0


@dataclass
class PermuteState:
    size: int
    board: tuple                 # n*n owners (0/1), index y*n+x; always full
    bandaged: frozenset          # cell indices that are bandaged (locked)
    to_move: int = ORANGE
    ply: int = 0
    last: tuple = ()             # cell-id strings of the last twisted face


class Permute(Game):
    uid = "permute"
    name = "Permute"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> PermuteState:
        n = int((options or {}).get("size", 9))
        # Chequerboard: Yellow (seat 1) on (x+y)-even cells (incl. corners), so
        # on odd boards the second player holds the extra stone.
        board = tuple(
            YELLOW if (x + y) % 2 == 0 else ORANGE
            for y in range(n) for x in range(n)
        )
        return PermuteState(size=n, board=board, bandaged=frozenset())

    def current_player(self, s: PermuteState) -> int:
        return s.to_move

    def _twistable_faces(self, s: PermuteState) -> list[tuple[int, int]]:
        n = s.size
        return [
            (ax, ay)
            for ay in range(n - 1)
            for ax in range(n - 1)
            if _face_twistable(s.board, s.bandaged, n, ax, ay)
        ]

    def legal_moves(self, s: PermuteState) -> list[str]:
        n = s.size
        moves = []
        for (ax, ay) in self._twistable_faces(s):
            for (sx, sy) in _face(ax, ay):
                if s.board[sy * n + sx] == s.to_move:
                    for d in (CW, CCW):
                        moves.append(f"{ax},{ay}>{sx},{sy}={d}")
        if moves and s.ply == 1:
            moves.append("swap")  # pie rule for the second player
        return moves

    def apply_move(self, s: PermuteState, move: str, rng=None) -> PermuteState:
        n = s.size
        if move == "swap":
            if s.ply != 1:
                raise ValueError("swap is only legal on the second player's first turn")
            # Pie rule: the mover takes over the opening side. Equivalent to
            # flipping every stone's ownership; bandaged cells stay bandaged.
            return PermuteState(
                size=n,
                board=tuple(1 - o for o in s.board),
                bandaged=s.bandaged,
                to_move=1 - s.to_move,
                ply=s.ply + 1,
                last=s.last,
            )
        try:
            path, direction = move.split("=")
            anchor, stone = path.split(">")
            ax, ay = _cell(anchor)
            sx, sy = _cell(stone)
        except ValueError:
            raise ValueError(f"bad move {move!r}")
        if direction not in (CW, CCW):
            raise ValueError(f"bad direction in {move!r}")
        if not (0 <= ax < n - 1 and 0 <= ay < n - 1):
            raise ValueError(f"face anchor off board in {move!r}")
        if not _face_twistable(s.board, s.bandaged, n, ax, ay):
            raise ValueError(f"face {ax},{ay} is not twistable")
        if (sx, sy) not in _face(ax, ay):
            raise ValueError(f"bandage target {sx},{sy} is not in face {ax},{ay}")
        if s.board[sy * n + sx] != s.to_move:
            raise ValueError("must bandage one of your OWN stones in the twisted face")

        board = _rotate(s.board, n, ax, ay, direction)
        dx, dy = _dest(ax, ay, sx, sy, direction)  # where the chosen stone landed
        bandaged = s.bandaged | {dy * n + dx}
        return PermuteState(
            size=n,
            board=board,
            bandaged=bandaged,
            to_move=1 - s.to_move,
            ply=s.ply + 1,
            last=tuple(f"{x},{y}" for (x, y) in _face(ax, ay)),
        )

    def is_terminal(self, s: PermuteState) -> bool:
        # The game ends when no face can be twisted. Twistability is
        # player-symmetric, so "mover is stuck" == "no twists remain at all".
        n = s.size
        return not any(
            _face_twistable(s.board, s.bandaged, n, ax, ay)
            for ay in range(n - 1)
            for ax in range(n - 1)
        )

    def returns(self, s: PermuteState) -> list[float]:
        if not self.is_terminal(s):
            return [0.0, 0.0]
        cmp = _compare(
            _group_sizes(s.board, s.size, ORANGE),
            _group_sizes(s.board, s.size, YELLOW),
        )
        if cmp > 0:
            return [1.0, -1.0]
        if cmp < 0:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # dead tie — only possible on even-sided boards

    def heuristic(self, s: PermuteState) -> list[float]:
        """Cheap rollout-cutoff eval: largest-group differential (the primary
        scoring term), squashed to (-1, 1)."""
        a = _group_sizes(s.board, s.size, ORANGE)
        b = _group_sizes(s.board, s.size, YELLOW)
        val = math.tanh(((a[0] if a else 0) - (b[0] if b else 0)) / 8.0)
        return [val, -val]

    def serialize(self, s: PermuteState) -> dict:
        return {
            "size": s.size,
            "board": "".join(str(o) for o in s.board),
            "bandaged": sorted(s.bandaged),
            "to_move": s.to_move,
            "ply": s.ply,
            "last": list(s.last),
        }

    def deserialize(self, d: dict) -> PermuteState:
        return PermuteState(
            size=d["size"],
            board=tuple(int(ch) for ch in d["board"]),
            bandaged=frozenset(d["bandaged"]),
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            last=tuple(d.get("last", [])),
        )

    def describe_move(self, s: PermuteState, move: str) -> str:
        if move == "swap":
            return "swap (pie)"
        try:
            path, direction = move.split("=")
            anchor, stone = path.split(">")
        except ValueError:
            return move
        arrow = "↻" if direction == CW else "↺"  # ↻ / ↺
        return f"twist {anchor} {arrow}, bandage {stone}"

    def render(self, s: PermuteState, perspective=None) -> dict:
        n = s.size
        names = {ORANGE: "Red", YELLOW: "Blue"}  # platform seat colours
        pieces = []
        for i, owner in enumerate(s.board):
            x, y = i % n, i // n
            p = {"cell": f"{x},{y}", "owner": owner, "label": ""}
            if i in s.bandaged:
                p["label"] = "✕"  # ✕ bandage marker
            pieces.append(p)
        if self.is_terminal(s):
            a = _group_sizes(s.board, n, ORANGE)
            b = _group_sizes(s.board, n, YELLOW)
            cmp = _compare(a, b)
            top = f"{a[0] if a else 0}–{b[0] if b else 0}"
            if cmp == 0:
                caption = f"Draw ({top})"
            else:
                caption = f"{names[ORANGE if cmp > 0 else YELLOW]} wins ({top})"
        else:
            a = _group_sizes(s.board, n, ORANGE)
            b = _group_sizes(s.board, n, YELLOW)
            caption = (
                f"{names[s.to_move]} to move — twist a 2×2 face, "
                f"bandage your stone (largest groups {a[0]}–{b[0]})"
            )
        return {
            "board": {"type": "square", "width": n, "height": n},
            "pieces": pieces,
            "highlights": [{"cell": c, "kind": "last-move"} for c in s.last],
            "caption": caption,
            "choiceNames": {CW: "Clockwise ↻", CCW: "Anticlockwise ↺"},
        }
