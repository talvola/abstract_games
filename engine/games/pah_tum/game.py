"""Pah Tum (Pa Tum) — an ancient Near-Eastern / Assyrian grid placement game.

Described in R. C. Bell, *Board and Table Games from Many Civilizations*. Played on
a 7x7 grid of 49 cells, a fixed symmetric set of cells is BLOCKED (impassable,
holds no stone). Players alternately place one stone of their colour on any empty,
non-blocked cell until every playable cell is filled. Then each maximal horizontal
or vertical run of >=3 consecutive same-colour stones scores by an escalating
table; diagonals never score. Highest total wins, equal totals draw.

This is a "win as event" game: the per-player scores and the winner are computed
once and stored when the board fills (`apply_move` of the last stone).

Cells are "col,row", 0-based. A move is a single empty playable cell, e.g. "3,2".

RULESET CHOICES (see rules.md):
  * Board: 7x7 (49 cells). A 9x9 option is offered.
  * Blocked cells: instead of the historical alternating placement of an ODD
    number (commonly 5) of "boulders", we use a FIXED, symmetric EVEN preset so
    the game is fully deterministic from move one. Default "diamond" = the four
    diagonal neighbours of the centre; "cross" = the four orthogonal neighbours.
    On 7x7 this leaves 45 playable cells (player 0 places 23, player 1 places 22).
  * Scoring table (per maximal run, length L): 3->3, 4->10, 5->25, 6->56, 7->88.
    This fixed table is the de-facto standard across game references. Runs longer
    than 7 (only reachable on the 9x9 option) extend the table's escalation; see
    rules.md / SCORE_TABLE.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

NAMES = {0: "Red", 1: "Blue"}
BLOCKED_COLOR = "#6b6b6b"

# Maximal-run scoring table. Runs of <3 score nothing.
SCORE_TABLE = {3: 3, 4: 10, 5: 25, 6: 56, 7: 88}


def run_score(length: int) -> int:
    """Points for one maximal same-colour run of `length` consecutive stones.

    Lengths <3 score 0. Lengths 3..7 use the standard published table. Lengths >7
    (only reachable on the 9x9 board) continue the escalation: each extra cell adds
    the previous step's increment plus the running gap growth, i.e. we extrapolate
    score(L) = score(L-1) + (score(L-1) - score(L-2)) + (L - 6). This keeps the
    sequence strictly increasing and super-linear past the published table.
    """
    if length < 3:
        return 0
    if length <= 7:
        return SCORE_TABLE[length]
    # Extrapolate beyond the published table (9x9 only).
    s_prev2, s_prev = SCORE_TABLE[6], SCORE_TABLE[7]
    for L in range(8, length + 1):
        s = s_prev + (s_prev - s_prev2) + (L - 6)
        s_prev2, s_prev = s_prev, s
    return s_prev


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _blocked_cells(n: int, layout: str) -> frozenset:
    """A fixed symmetric set of blocked cells for an n x n board (n odd)."""
    mid = n // 2
    if layout == "cross":
        cells = {(mid - 1, mid), (mid + 1, mid), (mid, mid - 1), (mid, mid + 1)}
    else:  # "diamond" (default): four diagonal neighbours of the centre
        cells = {(mid - 1, mid - 1), (mid + 1, mid - 1),
                 (mid - 1, mid + 1), (mid + 1, mid + 1)}
    return frozenset(cells)


@dataclass
class PahTumState:
    n: int = 7
    layout: str = "diamond"
    board: dict = field(default_factory=dict)   # (c, r) -> player (0/1)
    to_move: int = 0
    scores: list = field(default_factory=lambda: [0, 0])  # final scores once full
    winner: int = -1     # -1 = none yet, 0/1 = winner, 2 = draw (board full only)


class PahTum(Game):
    uid = "pah_tum"
    name = "Pah Tum"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> PahTumState:
        opts = options or {}
        n = int(opts.get("size", 7))
        layout = opts.get("layout", "diamond")
        return PahTumState(n=n, layout=layout)

    # --- helpers -------------------------------------------------------------

    def _blocked(self, s: PahTumState) -> frozenset:
        return _blocked_cells(s.n, s.layout)

    def _empty_playable(self, s: PahTumState) -> list:
        blocked = self._blocked(s)
        return [(c, r) for r in range(s.n) for c in range(s.n)
                if (c, r) not in blocked and (c, r) not in s.board]

    def _board_full(self, s: PahTumState) -> bool:
        return not self._empty_playable(s)

    def _compute_scores(self, board: dict, n: int, blocked: frozenset) -> list:
        """Sum of run_score over every maximal horizontal/vertical same-colour run.

        Blocked cells and empty cells break runs (on a full board only blocked
        cells break them). Diagonals are never scored.
        """
        scores = [0, 0]

        def scan_line(coords):
            cur_owner = None
            cur_len = 0
            for (c, r) in coords:
                if (c, r) in blocked:
                    owner = None
                else:
                    owner = board.get((c, r))
                if owner is not None and owner == cur_owner:
                    cur_len += 1
                else:
                    if cur_owner is not None:
                        scores[cur_owner] += run_score(cur_len)
                    cur_owner = owner
                    cur_len = 1 if owner is not None else 0
            if cur_owner is not None:
                scores[cur_owner] += run_score(cur_len)

        for r in range(n):
            scan_line([(c, r) for c in range(n)])   # rows
        for c in range(n):
            scan_line([(c, r) for r in range(n)])   # columns
        return scores

    # --- Game interface ------------------------------------------------------

    def current_player(self, s: PahTumState) -> int:
        return s.to_move

    def is_terminal(self, s: PahTumState) -> bool:
        return s.winner != -1

    def legal_moves(self, s: PahTumState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in self._empty_playable(s)]

    def apply_move(self, s: PahTumState, move: str, rng=None) -> PahTumState:
        cell = _cell(move)
        board = dict(s.board)
        board[cell] = s.to_move
        ns = PahTumState(
            n=s.n, layout=s.layout, board=board,
            to_move=1 - s.to_move, scores=list(s.scores), winner=s.winner,
        )
        if self._board_full(ns):
            scores = self._compute_scores(board, s.n, self._blocked(s))
            ns.scores = scores
            if scores[0] > scores[1]:
                ns.winner = 0
            elif scores[1] > scores[0]:
                ns.winner = 1
            else:
                ns.winner = 2  # draw
        return ns

    def returns(self, s: PahTumState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: PahTumState) -> dict:
        return {
            "n": s.n,
            "layout": s.layout,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "scores": list(s.scores),
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> PahTumState:
        return PahTumState(
            n=d["n"],
            layout=d.get("layout", "diamond"),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            scores=list(d.get("scores", [0, 0])),
            winner=d.get("winner", -1),
        )

    def describe_move(self, s: PahTumState, move: str) -> str:
        c, r = _cell(move)
        return f"{NAMES[s.to_move][0]}:{c},{r}"

    def render(self, s: PahTumState, perspective=None) -> dict:
        blocked = self._blocked(s)
        tints = {f"{c},{r}": BLOCKED_COLOR for (c, r) in blocked}
        pieces = [{"cell": f"{c},{r}", "owner": p}
                  for (c, r), p in s.board.items()]

        if self.is_terminal(s):
            sc = s.scores
            if s.winner == 2:
                caption = f"Draw {sc[0]}-{sc[1]}"
            else:
                w = s.winner
                caption = f"{NAMES[w]} wins {sc[w]}-{sc[1 - w]}"
        else:
            # show the running (provisional) scores for the current board
            live = self._compute_scores(s.board, s.n, blocked)
            caption = (f"{NAMES[s.to_move]} to move  "
                       f"({NAMES[0]} {live[0]} - {live[1]} {NAMES[1]})")

        return {
            "board": {"type": "square", "width": s.n, "height": s.n, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
