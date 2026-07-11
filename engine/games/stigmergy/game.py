"""Stigmergy, by Luis Bolaños Mures & Steven Metzger (2021).

A drawless territory game on an initially empty hexhex board (hexagonal grid
of hexagons, side N, default 8). Based on Mike Zapawa's Tumbleweed, but with
single flippable stones instead of stacks.

Rules as implemented (from the designer's revised rules, Zillions submission
id 3126, updated 2021-07-03; the bundled ReadMe carries the same text):

SEEING.  Two stones, or a stone and an empty cell, SEE each other if they lie
on the same straight line of adjacent cells with no other stones between them
along that line. So from a cell, along each of the 6 hex directions, only the
FIRST stone is seen (it blocks anything beyond). A cell's own occupant is not
seen by the cell and does not block its outward rays.

CONTROL.  You CONTROL a cell if the number of stones of your colour it sees
is more than half the number of cells (empty or occupied) ADJACENT to it.
Interior cells have 6 neighbours (control needs 4+ seen), edge cells 4
(needs 3+), corner cells 3 (needs 2+). At most one player can control a
given cell (each ray yields at most one seen stone, and rays leaving the
board immediately yield none, so seen_black + seen_white <= adjacent count).

PLAY.  Black moves first; turns alternate. On your turn do exactly one of:
  * PASS — only if there are no empty cells, or every empty cell is
    controlled by some player (and, with an odd komi, only once the button
    has been taken);
  * PLACE a stone of your colour on an empty cell NOT controlled by your
    opponent;
  * FLIP an enemy stone on a cell YOU control (it becomes your colour).

END + SCORING.  The game ends when both players pass in succession. Score =
your stones on the board + the empty cells you control (+ komi for White,
+ half a point for whoever holds the button). Higher score wins; a genuine
tie is a draw (unreachable at a double-pass end: every empty cell is then
controlled by exactly one player, so the base scores sum to the odd cell
total 3N^2-3N+1, and an odd komi brings the half-point button into play).

KOMI & BUTTON.  Komi is a whole number added to White's score (a manifest
option here; the official pre-game "first player names komi, second picks
sides" auction is out of scope). When komi is ODD the BUTTON is in play:
until either player takes it nobody may pass, and on your turn you may take
the button instead of a board play; it is worth half a point at the end.

TERMINATION BACKSTOP.  Placements are monotone (stones are never removed),
but flips alone could in principle cycle, so a no-progress rule (too many
consecutive plies without a placement) or a hard ply cap force an end, at
which the position is scored as-is (empty cells controlled by nobody then
count for nobody, so a tie — an honest draw — is possible on that path only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # Black moves first

# The six axial hex directions; the three line orientations are the first
# three (each with its opposite).
_DIRS = [(1, 0), (0, 1), (1, -1), (-1, 0), (0, -1), (-1, 1)]
_ORIENTS = [(1, 0), (0, 1), (1, -1)]


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    """All axial cells of a hexhex of side ``size``."""
    out = []
    n = size - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            if abs(q + r) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


@lru_cache(maxsize=None)
def _adj(size: int) -> dict:
    """(q, r) -> number of on-board neighbours (6 interior, 4 edge, 3 corner)."""
    on = _cell_set(size)
    return {
        (q, r): sum(1 for dq, dr in _DIRS if (q + dq, r + dr) in on)
        for (q, r) in on
    }


@lru_cache(maxsize=None)
def _lines(size: int) -> tuple:
    """All maximal straight lines of the board, one per orientation, as
    tuples of cells in ray order."""
    on = _cell_set(size)
    lines = []
    for dq, dr in _ORIENTS:
        for (q, r) in _cells(size):
            if (q - dq, r - dr) in on:
                continue  # not the start of this line
            line = []
            while (q, r) in on:
                line.append((q, r))
                q += dq
                r += dr
            lines.append(tuple(line))
    return tuple(lines)


def _cell(s: str) -> tuple:
    q, r = s.split(",")
    return int(q), int(r)


def _seen_counts(board: dict, size: int) -> dict:
    """(q, r) -> [black_seen, white_seen]: how many stones of each colour the
    cell sees (first stone per direction only; own occupant not counted)."""
    seen = {c: [0, 0] for c in _cells(size)}
    for line in _lines(size):
        last = None  # owner of the nearest stone behind the scan front
        for c in line:
            if last is not None:
                seen[c][last] += 1
            if c in board:
                last = board[c]
        last = None
        for c in reversed(line):
            if last is not None:
                seen[c][last] += 1
            if c in board:
                last = board[c]
    return seen


def _controller(seen_bw, adj_n: int) -> Optional[int]:
    """Which player controls a cell with these seen counts, if any."""
    if 2 * seen_bw[BLACK] > adj_n:
        return BLACK
    if 2 * seen_bw[WHITE] > adj_n:
        return WHITE
    return None


def _scores(board: dict, size: int, komi: int, button: Optional[int]) -> list:
    """[black_score, white_score]: stones + controlled empty cells, plus komi
    (White) and the half-point button."""
    seen = _seen_counts(board, size)
    adj = _adj(size)
    sc = [0.0, 0.0]
    for c in _cells(size):
        if c in board:
            sc[board[c]] += 1
        else:
            ctl = _controller(seen[c], adj[c])
            if ctl is not None:
                sc[ctl] += 1
    sc[WHITE] += komi
    if button is not None:
        sc[button] += 0.5
    return sc


@dataclass
class StigmergyState:
    size: int = 8
    komi: int = 0
    board: dict = field(default_factory=dict)   # (q, r) -> BLACK/WHITE
    to_move: int = BLACK
    passes: int = 0                              # consecutive passes
    ply: int = 0
    since_place: int = 0                         # plies since a stone was placed
    button: Optional[int] = None                 # holder seat (odd komi only)
    last: Optional[tuple] = None                 # last placed/flipped cell
    winner: Optional[int] = None                 # set at game end (None = draw)
    over: bool = False


class Stigmergy(Game):
    name = "Stigmergy"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> StigmergyState:
        opts = options or {}
        size = int(opts.get("size", 8))
        komi = int(opts.get("komi", 0))
        return StigmergyState(size=size, komi=komi)

    def current_player(self, s: StigmergyState) -> int:
        return s.to_move

    # -- move generation -----------------------------------------------------

    def _button_pending(self, s: StigmergyState) -> bool:
        """The button is in play (odd komi) and nobody has taken it yet."""
        return s.komi % 2 == 1 and s.button is None

    def legal_moves(self, s: StigmergyState) -> list:
        if self.is_terminal(s):
            return []
        me, opp = s.to_move, 1 - s.to_move
        seen = _seen_counts(s.board, s.size)
        adj = _adj(s.size)
        moves = []
        all_empties_controlled = True
        for c in _cells(s.size):
            if c in s.board:
                if s.board[c] == opp and 2 * seen[c][me] > adj[c]:
                    moves.append(f"{c[0]},{c[1]}")      # flip
            else:
                ctl = _controller(seen[c], adj[c])
                if ctl is None:
                    all_empties_controlled = False
                if ctl != opp:
                    moves.append(f"{c[0]},{c[1]}")      # place
        if self._button_pending(s):
            moves.append("button")
        elif all_empties_controlled:
            moves.append("pass")
        return moves

    # -- transition ------------------------------------------------------------

    def _no_progress_cap(self, size: int) -> int:
        return 2 * len(_cells(size)) + 20

    def _ply_cap(self, size: int) -> int:
        return 8 * len(_cells(size)) + 100

    def apply_move(self, s: StigmergyState, move: str, rng=None) -> StigmergyState:
        if self.is_terminal(s):
            raise ValueError("game over")
        me, opp = s.to_move, 1 - s.to_move

        if move == "button":
            if not self._button_pending(s):
                raise ValueError("button not available")
            ns = StigmergyState(
                size=s.size, komi=s.komi, board=dict(s.board), to_move=opp,
                passes=0, ply=s.ply + 1, since_place=s.since_place + 1,
                button=me, last=None,
            )
            self._maybe_finish(ns)
            return ns

        if move == "pass":
            if "pass" not in self.legal_moves(s):
                raise ValueError("pass not allowed now")
            ns = StigmergyState(
                size=s.size, komi=s.komi, board=dict(s.board), to_move=opp,
                passes=s.passes + 1, ply=s.ply + 1,
                since_place=s.since_place + 1, button=s.button, last=None,
            )
            self._maybe_finish(ns, force=(ns.passes >= 2))
            return ns

        c = _cell(move)
        if c not in _cell_set(s.size):
            raise ValueError(f"off-board {move!r}")
        seen = _seen_counts(s.board, s.size)
        adj_n = _adj(s.size)[c]
        board = dict(s.board)
        if c in board:
            # flip: enemy stone on a cell I control
            if board[c] != opp:
                raise ValueError(f"{move!r}: not an enemy stone")
            if not 2 * seen[c][me] > adj_n:
                raise ValueError(f"{move!r}: cell not controlled by mover")
            board[c] = me
            since = s.since_place + 1
        else:
            # placement: empty cell not controlled by the opponent
            if 2 * seen[c][opp] > adj_n:
                raise ValueError(f"{move!r}: cell controlled by opponent")
            board[c] = me
            since = 0
        ns = StigmergyState(
            size=s.size, komi=s.komi, board=board, to_move=opp,
            passes=0, ply=s.ply + 1, since_place=since,
            button=s.button, last=c,
        )
        self._maybe_finish(ns)
        return ns

    def _maybe_finish(self, ns: StigmergyState, force: bool = False):
        """Set winner/over on ``ns`` if the game has ended (double pass, or a
        no-progress / ply-cap backstop); score the final position honestly."""
        end = force
        if not end and ns.since_place >= self._no_progress_cap(ns.size):
            end = True
        if not end and ns.ply >= self._ply_cap(ns.size):
            end = True
        if end:
            b, w = _scores(ns.board, ns.size, ns.komi, ns.button)
            if b > w:
                ns.winner = BLACK
            elif w > b:
                ns.winner = WHITE
            else:
                ns.winner = None  # honest draw (backstop endings only)
            ns.over = True

    def is_terminal(self, s: StigmergyState) -> bool:
        return s.over

    def returns(self, s: StigmergyState) -> list:
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- serialization ---------------------------------------------------------

    def serialize(self, s: StigmergyState) -> dict:
        return {
            "size": s.size,
            "komi": s.komi,
            "board": {f"{q},{r}": owner for (q, r), owner in s.board.items()},
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "since_place": s.since_place,
            "button": s.button,
            "last": (f"{s.last[0]},{s.last[1]}" if s.last is not None else None),
            "winner": s.winner,
            "over": s.over,
        }

    def deserialize(self, d: dict) -> StigmergyState:
        last = d.get("last")
        return StigmergyState(
            size=d["size"],
            komi=d.get("komi", 0),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            ply=d.get("ply", 0),
            since_place=d.get("since_place", 0),
            button=d.get("button"),
            last=(_cell(last) if last else None),
            winner=d.get("winner"),
            over=d.get("over", False),
        )

    def describe_move(self, s: StigmergyState, move: str) -> str:
        if move == "pass":
            return "pass"
        if move == "button":
            return "take button"
        c = _cell(move)
        return f"flip {move}" if c in s.board else f"place {move}"

    # -- rendering --------------------------------------------------------------

    # Faint seat-coloured fills for controlled empty cells (over the dark board).
    _TINTS = {BLACK: "#463029", WHITE: "#2c3344"}

    def render(self, s: StigmergyState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{q},{r}", "owner": owner}
            for (q, r), owner in s.board.items()
        ]

        seen = _seen_counts(s.board, s.size)
        adj = _adj(s.size)
        tints = {}
        for c in _cells(s.size):
            if c in s.board:
                continue
            ctl = _controller(seen[c], adj[c])
            if ctl is not None:
                tints[f"{c[0]},{c[1]}"] = self._TINTS[ctl]

        highlights = []
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}",
                               "kind": "last-move"})

        b, w = _scores(s.board, s.size, s.komi, s.button)
        score_txt = f"Black {b:g}, White {w:g}"
        if s.komi:
            score_txt += f" (komi {s.komi})"
        if s.over:
            if s.winner is None:
                caption = f"Draw — {score_txt}"
            else:
                caption = f"{names[s.winner]} wins — {score_txt}"
        else:
            caption = f"{names[s.to_move]} to move — {score_txt}"
            if self._button_pending(s):
                caption += " — button available"
            elif s.button is not None:
                caption += f" — button: {names[s.button]}"

        board = {"type": "hex", "shape": "hexagon", "size": s.size}
        if tints:
            board["tints"] = tints
        return {
            "board": board,
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
