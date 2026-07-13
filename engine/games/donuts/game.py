"""Donuts (Bruno Cathala, Funforge 2023 -- first playable as "INSERT").

A tactical 2-player alignment game on a 6x6 board that is *randomly assembled*
from four 3x3 tiles. Every square carries a printed line -- horizontal, vertical
or one of the two diagonals -- and that line dictates play:

* You place a ring (a "donut") of your colour on an empty square. The line drawn
  on the square you just played tells your OPPONENT the direction along which
  their next ring must sit -- anywhere on the straight line through your ring in
  that orientation. If every square on that line is already occupied, they are
  free to play any empty square.
* INSERTION (capture): if your placement leaves a run of your own rings flanked
  on BOTH ends, along any straight line, by a single opponent ring, those two
  bracketing opponent rings flip to your colour (the donuts are two-sided). The
  rulebook's two illustrated cases -- ``O_O`` (fill a one-cell gap between two
  opponent rings) and ``O X X _ O`` (complete a bracket around your own rings) --
  are both instances of this one rule.
* You win the instant you align FIVE rings of your colour in a row, column or
  diagonal. Each player owns 15 donuts, so after all 30 are placed (the board has
  six squares to spare) the game ends; the player with the largest orthogonally
  connected group of rings then wins, and a genuine tie is an honest draw.

Randomness has no chance node: ``initial_state`` shuffles + rotates the four
tiles with the supplied rng and STORES the resulting per-cell line map in the
state (the EinStein / Onitama pattern), so the generic UI and bot never see a
CHANCE player. ``has_randomness`` is true.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

N = 6                          # 6x6 board
GOAL_LEN = 5                   # align 5 to win
PER_PLAYER = 15                # donuts each -> 30 placements total (board holds 36)
TOTAL = 2 * PER_PLAYER

# The four line orientations. Values are the geometric step vector of the line;
# 'S' is the "/" diagonal (screen up-right), 'B' the "\" diagonal.
DIRS = {"H": (1, 0), "V": (0, 1), "S": (1, 1), "B": (1, -1)}
LINE_DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]   # the 4 straight lines on the grid

# Rotating a tile 90 degrees clockwise turns each printed line: H<->V, S<->B.
ROT90 = {"H": "V", "V": "H", "S": "B", "B": "S"}

# Four 3x3 tile faces (tile-local rows top->bottom, cells left->right). The exact
# art on the physical tiles is not published in text sources; these faithful
# stand-ins carry a balanced mix of all four orientations so the random assembly
# produces varied boards (documented as an interpretation in rules.md). Only the
# *mechanic* -- a random V/H/D line map -- is load-bearing, not the specific art.
TILES = [
    [["S", "H", "B"], ["V", "S", "V"], ["B", "H", "S"]],
    [["H", "V", "H"], ["B", "S", "B"], ["H", "V", "H"]],
    [["V", "B", "S"], ["H", "V", "H"], ["S", "B", "V"]],
    [["B", "S", "V"], ["H", "B", "H"], ["V", "S", "B"]],
]
QUADRANTS = [(0, 0), (3, 0), (0, 3), (3, 3)]     # base (col,row) of each 3x3 block


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _rot90(tile):
    """Rotate a 3x3 tile 90 degrees clockwise (cells move + each line turns)."""
    return [[ROT90[tile[2 - c][r]] for c in range(3)] for r in range(3)]


def _build_linemap(rng):
    """Shuffle the four tiles into the four quadrants, each at a random rotation,
    and return {(c, r): orientation} for all 36 squares."""
    order = list(range(4))
    rng.shuffle(order)
    lm = {}
    for q, ti in enumerate(order):
        tile = TILES[ti]
        for _ in range(rng.randrange(4)):
            tile = _rot90(tile)
        bc, br = QUADRANTS[q]
        for tr in range(3):
            for tc in range(3):
                lm[(bc + tc, br + tr)] = tile[tr][tc]
    return lm


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


@dataclass
class DonutState:
    linemap: dict = field(default_factory=dict)   # (c,r) -> orientation letter
    board: dict = field(default_factory=dict)     # (c,r) -> owner 0/1
    to_move: int = 0
    last: object = None                            # last-placed (c,r) or None
    placed: tuple = (0, 0)                         # donuts placed per player
    winner: object = None                          # set only on a 5-in-a-row


class Donuts(Game):
    uid = "donuts"
    name = "Donuts"

    @property
    def num_players(self):
        return 2

    # -- setup ---------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        return DonutState(linemap=_build_linemap(rng), board={}, to_move=0,
                          last=None, placed=(0, 0), winner=None)

    def current_player(self, s):
        return s.to_move

    # -- move generation -----------------------------------------------------
    def _line_cells(self, cell, orient):
        """All on-board cells collinear with `cell` in `orient` (excluding it)."""
        c, r = cell
        dc, dr = DIRS[orient]
        out = []
        for sign in (1, -1):
            x, y = c + sign * dc, r + sign * dr
            while _on(x, y):
                out.append((x, y))
                x += sign * dc
                y += sign * dr
        return out

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        empty = [(c, r) for r in range(N) for c in range(N) if (c, r) not in s.board]
        if s.last is None:
            pool = empty                                   # opening: anywhere
        else:
            line = self._line_cells(s.last, s.linemap[s.last])
            forced = [cell for cell in line if cell not in s.board]
            pool = forced if forced else empty             # all-occupied fallback
        return [f"{c},{r}" for (c, r) in pool]

    # -- capture / win helpers ----------------------------------------------
    def _flips(self, board, cell, owner):
        """Cells to flip: for each straight line, the maximal run of `owner`
        through `cell` flanked on BOTH ends by exactly one opponent ring."""
        opp = 1 - owner
        c, r = cell
        flips = set()
        for dc, dr in LINE_DIRS:
            fx, fy = c + dc, r + dr
            while _on(fx, fy) and board.get((fx, fy)) == owner:
                fx, fy = fx + dc, fy + dr
            bx, by = c - dc, r - dr
            while _on(bx, by) and board.get((bx, by)) == owner:
                bx, by = bx - dc, by - dr
            if (_on(fx, fy) and board.get((fx, fy)) == opp
                    and _on(bx, by) and board.get((bx, by)) == opp):
                flips.add((fx, fy))
                flips.add((bx, by))
        return flips

    def _has_five(self, board, owner):
        for dc, dr in LINE_DIRS:
            for r in range(N):
                for c in range(N):
                    if board.get((c, r)) != owner:
                        continue
                    if board.get((c - dc, r - dr)) == owner:
                        continue
                    length, x, y = 0, c, r
                    while board.get((x, y)) == owner:
                        length += 1
                        x, y = x + dc, y + dr
                    if length >= GOAL_LEN:
                        return True
        return False

    def apply_move(self, s, move, rng=None):
        cell = _cell(move)
        owner = s.to_move
        board = dict(s.board)
        board[cell] = owner
        for f in self._flips(board, cell, owner):
            board[f] = owner
        winner = owner if self._has_five(board, owner) else None
        placed = list(s.placed)
        placed[owner] += 1
        return DonutState(linemap=s.linemap, board=board, to_move=1 - owner,
                          last=cell, placed=tuple(placed), winner=winner)

    # -- termination ---------------------------------------------------------
    def is_terminal(self, s):
        return s.winner is not None or sum(s.placed) >= TOTAL

    def _largest_group(self, board, owner):
        cells = {cr for cr, o in board.items() if o == owner}
        best = 0
        seen = set()
        for start in cells:
            if start in seen:
                continue
            stack, size = [start], 0
            seen.add(start)
            while stack:
                c, r = stack.pop()
                size += 1
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (c + dc, r + dr)
                    if n in cells and n not in seen:
                        seen.add(n)
                        stack.append(n)
            best = max(best, size)
        return best

    def _result(self, s):
        """Terminal winner: 0/1, or None for a genuine draw."""
        if s.winner is not None:
            return s.winner
        g0, g1 = self._largest_group(s.board, 0), self._largest_group(s.board, 1)
        if g0 > g1:
            return 0
        if g1 > g0:
            return 1
        return None

    def returns(self, s):
        w = self._result(s)
        if w is None:
            return [0.0, 0.0]
        return [1.0 if i == w else -1.0 for i in range(2)]

    # -- (de)serialize -------------------------------------------------------
    def serialize(self, s):
        return {
            "linemap": {f"{c},{r}": o for (c, r), o in s.linemap.items()},
            "board": {f"{c},{r}": o for (c, r), o in s.board.items()},
            "to_move": s.to_move,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "placed": list(s.placed),
            "winner": s.winner,
        }

    def deserialize(self, d):
        return DonutState(
            linemap={_cell(k): v for k, v in d["linemap"].items()},
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=(_cell(d["last"]) if d.get("last") is not None else None),
            placed=tuple(d.get("placed", (0, 0))),
            winner=d.get("winner"),
        )

    # -- move log ------------------------------------------------------------
    def describe_move(self, s, move):
        cell = _cell(move)
        orient = s.linemap.get(cell, "?")
        glyph = {"H": "-", "V": "|", "S": "/", "B": "\\"}.get(orient, "?")
        return f"{move} ({glyph})"

    # -- render --------------------------------------------------------------
    def render(self, s, perspective=None):
        # Per-cell orientation marks: drawn as a short overlay segment (over the
        # opaque cell, unlike board.lines which is hidden UNDER cells). Rings are
        # hollow, so the mark reads through the donut hole. Coords are board-space
        # (c, r); the renderer maps y with row 0 at the bottom, so 'S' = "/".
        seg = 0.32
        overlay = []
        for (c, r), orient in s.linemap.items():
            dc, dr = DIRS[orient]
            overlay.append([[c - seg * dc, r - seg * dr], [c + seg * dc, r + seg * dr]])

        pieces = [{"cell": f"{c},{r}", "owner": o, "shape": "ring"}
                  for (c, r), o in s.board.items()]
        highlights = ([{"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"}]
                      if s.last is not None else [])

        names = {0: "Player 1 (dark)", 1: "Player 2 (light)"}
        if self.is_terminal(s):
            w = self._result(s)
            cap = ("Draw -- equal largest groups" if w is None
                   else f"{names[w]} wins")
        elif s.last is None:
            cap = f"{names[s.to_move]} to place anywhere ({s.placed} placed)"
        else:
            words = {"H": "horizontally", "V": "vertically",
                     "S": "on the / diagonal", "B": "on the \\ diagonal"}
            direction = words[s.linemap[s.last]]
            cap = f"{names[s.to_move]} must play {direction} through the last ring"
        return {
            "board": {"type": "square", "width": N, "height": N,
                      "overlay": overlay},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
