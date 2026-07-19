"""SanQi — "The Game of Three", by L. Lynn Smith (c. 2003).

Rules implemented from the designer's own rules document ("The Rules of
SanQi", archived from his geocities site, distributed by superdupergames.org)
cross-checked against the lightly edited reprint in Abstract Games magazine
#17 (Autumn 2019), pp. 13-17. The two sources state the same ruleset; where
the AG#17 edit clarifies a point (immunity extends to pieces created by
replacement; the editor's equivalent "seven-space" counting of the
replacement majority) we follow the clarified wording.

Summary of the ruleset (see rules.md for the full text as implemented):

* Two players (First and Second) on a hexhex board (side 4..10; the designer
  calls hex-10 optimal, smaller boards learning sizes).
* Three SHARED piece types, the Lingqijing characters: Shang 上 "Above"
  (red), Zhong 中 "Middle" (yellow), Xia 下 "Below" (blue). Unlimited
  supply, owned by neither player.
* A turn is exactly one of:
  - PLACEMENT: put any one of the three types on any vacant cell.
  - REPLACEMENT: change an occupied cell's piece to a DIFFERENT type T,
    legal only if among the six neighbours of that cell
        count(T) >= count(current type) + 2.
    (Equivalently, per the AG#17 editor: counting the target cell itself
    plus its six neighbours, attackers must outnumber defenders.)
  No passing.
* Immunity: the piece created by the opponent's last move (placed OR
  replaced) may not be replaced on your immediately following turn. It is
  never immune to its own creator, and the immunity lapses after that one
  turn.
* Goals — checked only at the end of the MOVER's own turn, over pieces of
  any ONE type:
  - First wins if a CIRCLE of six exists (the six neighbours of some cell,
    regardless of that centre cell's condition).
  - Second wins if a straight LINE of six exists.
  - Either player wins if a compact TRIANGLE of six (side-3, cells
    a + i*d1 + j*d2 with i+j<=2 for two directions 60 degrees apart)
    exists at the end of their own turn.
  A pattern completed on the opponent's turn therefore wins for you only
  if it still stands at the end of YOUR next turn.

Termination backstops (implementation notes, not in the sources — the
designer lets replacement play continue forever on a full board):
  - max(40, #cells) consecutive replacements with no intervening placement
    -> DRAW;
  - hard cap of 20 * #cells plies -> DRAW;
  - a player with no legal move (only possible on a full board with no
    legal replacement) -> DRAW.
All draws are honest (winner None, returns [0, 0]).

Move grammar: "q,r=T" with T in {S, Z, X} — a placement if the cell is
vacant, a replacement if occupied. The generic UI shows the =CHOICE picker.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

TYPES = ("S", "Z", "X")
KANJI = {"S": "上", "Z": "中", "X": "下"}   # 上 中 下
NAMES = {"S": "Shang", "Z": "Zhong", "X": "Xia"}
# AG#17 colour scheme: Shang=Red, Zhong=Yellow, Xia=Blue (shared pieces —
# these colours do not denote ownership; label colour = the stroke colour).
FILLS = {"S": "#c04432", "Z": "#e0b23a", "X": "#3a66b8"}
STROKES = {"S": "#f5e9dc", "Z": "#4a3a10", "X": "#e8eefc"}

SEAT_NAMES = ("First", "Second")

DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
LINE_DIRS = ((1, 0), (0, 1), (1, -1))
# Pairs of directions 60 degrees apart (ring-adjacent) — triangle spanners.
ADJ_PAIRS = tuple((DIRS[i], DIRS[(i + 1) % 6]) for i in range(6))


def _cid(c) -> str:
    return f"{c[0]},{c[1]}"


def _cell(s: str):
    q, r = s.split(",")
    return (int(q), int(r))


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    n = size - 1
    out = []
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            if max(abs(q), abs(r), abs(q + r)) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


@lru_cache(maxsize=None)
def _windows(size: int):
    """All six-cell goal patterns on the board.

    Returns (windows, by_cell): windows = tuple of (kind, cells-tuple) with
    kind in {"circle", "line", "triangle"}; by_cell maps each cell to the
    indices of every window containing it (for incremental win detection).
    """
    on = _cell_set(size)
    seen = set()
    windows = []

    def add(kind, cells):
        key = frozenset(cells)
        if key in seen:
            return
        seen.add(key)
        windows.append((kind, tuple(cells)))

    for (q, r) in _cells(size):
        # circle: the six neighbours of (q, r); centre condition irrelevant
        ring = [(q + d[0], r + d[1]) for d in DIRS]
        if all(c in on for c in ring):
            add("circle", ring)
        # lines of six, three axes
        for d in LINE_DIRS:
            run = [(q + i * d[0], r + i * d[1]) for i in range(6)]
            if all(c in on for c in run):
                add("line", run)
        # side-3 triangles: a + i*d1 + j*d2, i+j <= 2 (six orientations;
        # each geometric triangle recurs from its 3 corners — deduped above)
        for d1, d2 in ADJ_PAIRS:
            tri = [(q + i * d1[0] + j * d2[0], r + i * d1[1] + j * d2[1])
                   for i in range(3) for j in range(3 - i)]
            if all(c in on for c in tri):
                add("triangle", tri)

    by_cell = {}
    for wi, (_kind, cells) in enumerate(windows):
        for c in cells:
            by_cell.setdefault(c, []).append(wi)
    by_cell = {c: tuple(v) for c, v in by_cell.items()}
    return tuple(windows), by_cell


def _repl_cap(n_cells: int) -> int:
    return max(40, n_cells)


def _ply_cap(n_cells: int) -> int:
    return 20 * n_cells


@dataclass
class SState:
    size: int = 7
    board: dict = field(default_factory=dict)   # (q,r) -> "S" | "Z" | "X"
    to_move: int = 0                            # 0 = First, 1 = Second
    immune: Optional[tuple] = None              # opponent's last-move cell
    winner: Optional[int] = None
    over: bool = False
    end: Optional[str] = None                   # win pattern / draw reason
    repl_run: int = 0                           # consecutive replacements
    ply: int = 0


class SanQi(Game):
    name = "SanQi"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SState:
        opts = options or {}
        size = int(opts.get("size", 7))
        if size < 4:
            size = 4
        return SState(size=size)

    def current_player(self, s: SState) -> int:
        return s.to_move

    # -- move generation -----------------------------------------------------

    @staticmethod
    def _neighbor_counts(board: dict, c) -> dict:
        counts = {"S": 0, "Z": 0, "X": 0}
        for d in DIRS:
            t = board.get((c[0] + d[0], c[1] + d[1]))
            if t is not None:
                counts[t] += 1
        return counts

    def _replacements_at(self, s: SState, c) -> list:
        """Legal replacement types for occupied cell ``c`` (ignores immunity)."""
        cur = s.board[c]
        counts = self._neighbor_counts(s.board, c)
        need = counts[cur] + 2
        return [t for t in TYPES if t != cur and counts[t] >= need]

    def legal_moves(self, s: SState) -> list:
        if self.is_terminal(s):
            return []
        out = []
        for c in _cells(s.size):
            cur = s.board.get(c)
            cid = _cid(c)
            if cur is None:
                out.extend(f"{cid}={t}" for t in TYPES)
            elif c != s.immune:
                out.extend(f"{cid}={t}" for t in self._replacements_at(s, c))
        return out

    # -- win detection -------------------------------------------------------
    #
    # Incremental: a pattern present at the end of the mover's turn that did
    # NOT exist at the end of their previous turn must pass through one of
    # the (at most two) cells changed since — the opponent's last move
    # (s.immune) and the mover's own move. Checking only windows through
    # those cells is therefore complete along any real game line (it can
    # miss patterns only in hand-built unreachable states).

    def _kinds_through(self, board: dict, size: int, cells) -> set:
        windows, by_cell = _windows(size)
        kinds = set()
        for c in cells:
            for wi in by_cell.get(c, ()):
                kind, wcells = windows[wi]
                if kind in kinds:
                    continue
                t0 = board.get(wcells[0])
                if t0 is not None and all(board.get(x) == t0
                                          for x in wcells[1:]):
                    kinds.add(kind)
        return kinds

    # -- apply ---------------------------------------------------------------

    def apply_move(self, s: SState, move: str, rng=None) -> SState:
        if self.is_terminal(s):
            raise ValueError("game over")
        cell_str, sep, t = move.partition("=")
        if not sep or t not in TYPES:
            raise ValueError(f"bad move {move!r}")
        c = _cell(cell_str)
        if c not in _cell_set(s.size):
            raise ValueError(f"off-board cell {cell_str!r}")
        cur = s.board.get(c)
        seat = s.to_move
        if cur is not None:
            if c == s.immune:
                raise ValueError(f"{cell_str} is protected this turn")
            if t == cur or t not in self._replacements_at(s, c):
                raise ValueError(f"illegal replacement {move!r}")

        ns = SState(size=s.size, board=dict(s.board), to_move=1 - seat,
                    immune=c, repl_run=0 if cur is None else s.repl_run + 1,
                    ply=s.ply + 1)
        ns.board[c] = t

        # goal check at the end of the mover's own turn
        check = {c}
        if s.immune is not None:
            check.add(s.immune)
        kinds = self._kinds_through(ns.board, s.size, check)
        wins = ("circle", "triangle") if seat == 0 else ("line", "triangle")
        for kind in wins:
            if kind in kinds:
                ns.winner = seat
                ns.over = True
                ns.end = kind
                return ns

        # draw backstops (implementation notes; see module docstring)
        n = len(_cells(s.size))
        if ns.repl_run >= _repl_cap(n):
            ns.over = True
            ns.end = "no-progress (replacement churn)"
            return ns
        if ns.ply >= _ply_cap(n):
            ns.over = True
            ns.end = "move limit"
            return ns
        if len(ns.board) == n and not self.legal_moves(ns):
            ns.over = True
            ns.end = "no legal moves"
            return ns
        return ns

    def is_terminal(self, s: SState) -> bool:
        return s.over

    def returns(self, s: SState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # -- bot eval ------------------------------------------------------------

    def heuristic(self, s: SState) -> list:
        """Best partial goal pattern per seat (windows of one type + empties)."""
        if s.over:
            return self.returns(s)
        windows, _ = _windows(s.size)
        board = s.board
        best = [0, 0]
        for kind, wcells in windows:
            t0 = None
            cnt = 0
            clean = True
            for x in wcells:
                t = board.get(x)
                if t is None:
                    continue
                if t0 is None:
                    t0 = t
                elif t != t0:
                    clean = False
                    break
                cnt += 1
            if not clean or cnt == 0:
                continue
            if kind != "line" and cnt > best[0]:
                best[0] = cnt
            if kind != "circle" and cnt > best[1]:
                best[1] = cnt
        v = math.tanh(0.5 * (best[0] - best[1]))
        return [v, -v]

    # -- serialization -------------------------------------------------------

    def serialize(self, s: SState) -> dict:
        return {
            "size": s.size,
            "board": {_cid(c): t for c, t in sorted(s.board.items())},
            "to_move": s.to_move,
            "immune": _cid(s.immune) if s.immune else None,
            "winner": s.winner,
            "over": s.over,
            "end": s.end,
            "repl_run": s.repl_run,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> SState:
        return SState(
            size=d["size"],
            board={_cell(k): t for k, t in d["board"].items()},
            to_move=d["to_move"],
            immune=_cell(d["immune"]) if d.get("immune") else None,
            winner=d.get("winner"),
            over=d.get("over", False),
            end=d.get("end"),
            repl_run=d.get("repl_run", 0),
            ply=d.get("ply", 0),
        )

    # -- presentation --------------------------------------------------------

    def describe_move(self, s: SState, move: str) -> str:
        cell_str, _, t = move.partition("=")
        cur = s.board.get(_cell(cell_str)) if t in TYPES else None
        if cur is None:
            return f"place {NAMES.get(t, t)} {KANJI.get(t, '')} at {cell_str}"
        return (f"replace {KANJI[cur]}→{KANJI[t]} "
                f"({NAMES[cur]}→{NAMES[t]}) at {cell_str}")

    def render(self, s: SState, perspective=None) -> dict:
        pieces = [{"cell": _cid(c), "label": KANJI[t],
                   "fill": FILLS[t], "stroke": STROKES[t]}
                  for c, t in sorted(s.board.items())]
        highlights = ([{"cell": _cid(s.immune), "kind": "last-move"}]
                      if s.immune else [])
        if s.over:
            if s.winner is None:
                caption = f"Draw — {s.end}"
            else:
                caption = (f"{SEAT_NAMES[s.winner]} wins — "
                           f"{s.end} of six alike")
        else:
            goal = ("circle or triangle" if s.to_move == 0
                    else "line or triangle")
            caption = (f"{SEAT_NAMES[s.to_move]} to move — "
                       f"goal: a {goal} of six alike")
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "choiceNames": {
                "S": "Shang 上 (red)",
                "Z": "Zhong 中 (yellow)",
                "X": "Xia 下 (blue)",
            },
        }
