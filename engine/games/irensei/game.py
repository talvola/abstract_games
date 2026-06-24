"""Irensei (囲連星) -- a Go/Gomoku hybrid on a 19x19 board.

Irensei ("surrounding-connected-stars") is played with Go stones on a Go board:
players alternately place a stone on an empty intersection, Black first. It blends
Gomoku's line-making goal with Go's capturing.

Win condition (the signature rule):
  * The goal is an unbroken line of SEVEN stones (horizontal, vertical or
    diagonal) -- BUT every stone of that line must lie inside the central 15x15
    area. A line that uses any point on the OUTER TWO LINES of the board (the two
    outermost rows/columns on every side) does NOT win. On a 0-indexed 19x19
    board the valid (inner) coordinates are 2..16 inclusive on both axes.
  * BLACK must make EXACTLY seven in a row and LOSES immediately on an overline
    (eight or more in a row), to offset the first-move advantage.
  * WHITE wins with seven OR MORE in a row (overlines are fine for White) as long
    as a span of seven consecutive White stones lies wholly in the central area.

Go mechanics also apply:
  * Stones with no liberties are captured and removed (enemy groups first, then
    your own = suicide). Capture/liberty adjacency is ORTHOGONAL only; the
    winning line may be diagonal.
  * SUICIDE is illegal -- EXCEPT a suicidal move that completes a winning line is
    allowed (it wins before the self-capture matters).
  * KO / positional superko: a move may not recreate an earlier whole-board
    position.

Win is evaluated on the board AFTER captures resolve, so a move that captures the
opponent and thereby reveals or completes a seven-in-a-row wins, and a move that
gets your own line captured does not.

Termination: the game ends in a DRAW if the board fills (361 stones) or a hard
ply cap is reached with no winner. (Sources do not specify a board-full result;
documented Irensei games always end in a line, so a full board is essentially
unreachable -- we score it as a draw to bound the game.)

Cells are "col,row"; a move is a single empty cell id, or "pass".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 19
BLACK, WHITE = 0, 1
NAMES = {BLACK: "Black", WHITE: "White"}
CONNECT = 7

# Inner (central 15x15) bounds: exclude the outer two lines on every side.
# 0-indexed 19x19 -> valid coordinates 2..16 inclusive.
INNER_LO = 2
INNER_HI = SIZE - 3  # == 16

# Winning-line directions (each handled symmetrically by +/-).
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _inner(c, r):
    return INNER_LO <= c <= INNER_HI and INNER_LO <= r <= INNER_HI


def _neighbors(c, r):
    if c > 0:
        yield (c - 1, r)
    if c < SIZE - 1:
        yield (c + 1, r)
    if r > 0:
        yield (c, r - 1)
    if r < SIZE - 1:
        yield (c, r + 1)


def _group(board, start):
    color = board[start]
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for nb in _neighbors(c, r):
            if nb not in seen and board.get(nb) == color:
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_liberty(board, group):
    for c, r in group:
        for nb in _neighbors(c, r):
            if nb not in board:
                return True
    return False


def _board_key(board):
    return "".join(
        "." if (c, r) not in board else "bw"[board[(c, r)]]
        for r in range(SIZE) for c in range(SIZE)
    )


def _resolve(board, c, r, mover):
    """Board after `mover` plays at (c,r): capture enemy dead groups first, then a
    dead own group (suicide). Returns (new_board, captured_count, suicided)."""
    nb = dict(board)
    nb[(c, r)] = mover
    captured = 0
    enemy = 1 - mover
    done = set()
    for ec, er in _neighbors(c, r):
        if nb.get((ec, er)) == enemy and (ec, er) not in done:
            grp = _group(nb, (ec, er))
            done |= grp
            if not _has_liberty(nb, grp):
                for sq in grp:
                    del nb[sq]
                captured += len(grp)
    suicided = False
    if captured == 0:
        own = _group(nb, (c, r))
        if not _has_liberty(nb, own):
            for sq in own:
                del nb[sq]
            suicided = True
    return nb, captured, suicided


def _line_run(board, c, r, dc, dr, player):
    """Length of the unbroken run of `player` through (c,r) along (dc,dr) for
    which EVERY stone lies in the inner 15x15 area. Stones touching the excluded
    edge break the run (they cannot contribute to a winning line)."""
    if board.get((c, r)) != player or not _inner(c, r):
        return 0
    run = 1
    for sign in (1, -1):
        cc, rr = c + dc * sign, r + dr * sign
        while board.get((cc, rr)) == player and _inner(cc, rr):
            run += 1
            cc += dc * sign
            rr += dr * sign
    return run


def _best_inner_run(board, cell, player):
    """Longest inner-area run through `cell` over all four directions."""
    c, r = cell
    best = 0
    for dc, dr in DIRS:
        best = max(best, _line_run(board, c, r, dc, dr, player))
    return best


def _has_seven_anywhere(board, player):
    """True if SOME inner-area run of `player` reaches length >= 7 (used after a
    capture may complete a line not passing through the placed stone)."""
    for (c, r), p in board.items():
        if p != player or not _inner(c, r):
            continue
        for dc, dr in DIRS:
            if _line_run(board, c, r, dc, dr, player) >= CONNECT:
                return True
    return False


@dataclass
class IrenseiState:
    board: dict = field(default_factory=dict)   # (c, r) -> player
    to_move: int = BLACK
    winner: Optional[int] = None                # 0/1 winner, None = undecided
    ply: int = 0
    last_move: object = None                    # (c,r) | "pass" | None
    history: frozenset = field(default_factory=frozenset)


class Irensei(Game):
    uid = "irensei"
    name = "Irensei"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> IrenseiState:
        s = IrenseiState()
        s.history = frozenset({_board_key(s.board)})
        return s

    def current_player(self, s: IrenseiState) -> int:
        return s.to_move

    def _ply_cap(self) -> int:
        # Generous bound well above the 361 cells; captures can extend play.
        return SIZE * SIZE * 3

    def _legal_placements(self, s):
        for r in range(SIZE):
            for c in range(SIZE):
                if (c, r) in s.board:
                    continue
                nb, captured, suicided = _resolve(s.board, c, r, s.to_move)
                if suicided:
                    # Suicide allowed only if it makes a winning line for mover.
                    if not self._win_for(nb, s.to_move):
                        continue
                if _board_key(nb) in s.history:
                    continue                       # positional superko
                yield f"{c},{r}", nb

    def legal_moves(self, s: IrenseiState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [m for m, _ in self._legal_placements(s)] + ["pass"]

    def _win_for(self, board, player) -> bool:
        """Does `board` contain a valid winning line for `player`?

        BLACK: needs an inner run of length EXACTLY 7 (any run >= 8 is an
        overline and not itself a win, though it triggers a loss elsewhere).
        WHITE: needs an inner run of length >= 7."""
        target_exact = (player == BLACK)
        for (c, r), p in board.items():
            if p != player or not _inner(c, r):
                continue
            for dc, dr in DIRS:
                run = _line_run(board, c, r, dc, dr, player)
                if target_exact:
                    if run == CONNECT:
                        return True
                else:
                    if run >= CONNECT:
                        return True
        return False

    def _black_overline(self, board) -> bool:
        """True if Black has any inner run of length >= 8 (forbidden overline)."""
        for (c, r), p in board.items():
            if p != BLACK or not _inner(c, r):
                continue
            for dc, dr in DIRS:
                if _line_run(board, c, r, dc, dr, BLACK) >= CONNECT + 1:
                    return True
        return False

    def apply_move(self, s: IrenseiState, move: str, rng=None) -> IrenseiState:
        if move == "pass":
            return IrenseiState(board=dict(s.board), to_move=1 - s.to_move,
                                winner=s.winner, ply=s.ply + 1,
                                last_move="pass", history=s.history)
        c, r = _cell(move)
        player = s.to_move
        nb, _cap, _suic = _resolve(s.board, c, r, player)

        winner = None
        if player == BLACK:
            # An exact-7 wins even if the move would otherwise overline.
            if self._win_for(nb, BLACK):
                winner = BLACK
            elif self._black_overline(nb):
                winner = WHITE          # Black loses on an overline
        else:  # WHITE
            if self._win_for(nb, WHITE):
                winner = WHITE

        return IrenseiState(board=nb, to_move=1 - player, winner=winner,
                            ply=s.ply + 1, last_move=(c, r),
                            history=s.history | {_board_key(nb)})

    def is_terminal(self, s: IrenseiState) -> bool:
        return (s.winner is not None
                or len(s.board) >= SIZE * SIZE
                or s.ply >= self._ply_cap())

    def returns(self, s: IrenseiState) -> list[float]:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: IrenseiState) -> dict:
        lm = s.last_move
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "last_move": ("pass" if lm == "pass" else (list(lm) if lm else None)),
            "history": sorted(s.history),
        }

    def deserialize(self, d: dict) -> IrenseiState:
        lm = d.get("last_move")
        return IrenseiState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            last_move=("pass" if lm == "pass" else (tuple(lm) if lm else None)),
            history=frozenset(d.get("history", [])),
        )

    def describe_move(self, s: IrenseiState, move: str) -> str:
        if move == "pass":
            return f"{NAMES[s.to_move][0]}:pass"
        c, r = _cell(move)
        return f"{NAMES[s.to_move][0]}:{c + 1},{r + 1}"

    def render(self, s: IrenseiState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = []
        if isinstance(s.last_move, tuple):
            highlights.append({"cell": f"{s.last_move[0]},{s.last_move[1]}",
                               "kind": "last-move"})
        # Tint the excluded outer-two-line frame so the central 15x15 win area
        # is visible.
        tints = {}
        for r in range(SIZE):
            for c in range(SIZE):
                if not _inner(c, r):
                    tints[f"{c},{r}"] = "#00000018"
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins (7-in-a-row in the central area)"
        elif self.is_terminal(s):
            caption = "Draw"
        else:
            caption = f"{NAMES[s.to_move]} to move — make 7 in a row inside the 15×15 center"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
