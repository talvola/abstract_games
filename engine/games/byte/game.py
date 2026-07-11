"""Byte -- Mark Steere, 2005. A merge-only **stacking** game played with a
Checkers set on the 32 dark squares of an 8x8 board.

Stacks are 1..8 checkers of any colour mix. The moment a stack of exactly 8
forms it is removed and scored for the owner of its TOP checker; the 24
checkers thus yield three stacks of 8, and whoever wins the majority (2) wins
the game (Steere: draws and ties cannot occur).

Two move types (movement is mandatory; with no move you must pass):

  * BASIC MOVE -- only a stack that is NOT diagonally adjacent to any other
    stack, and only if you own its BOTTOM checker: slide the ENTIRE stack one
    square diagonally, and it MUST move closer to its closest stack (distance =
    number of one-square diagonal moves, i.e. max(|dc|,|dr|); if several stacks
    tie as closest, moving closer to any one of them is legal).

  * MERGE -- between two diagonally ADJACENT stacks A and B: pick up YOUR
    checker at any level of A, carrying every checker on top of it, and place
    that portion on top of B. Two conditions: (1) your picked checker must land
    at a HIGHER altitude than it started (level > its old level), and (2) the
    result may not exceed 8. Adjacent stacks may never slide to empty squares.

Encoding: a basic move is `"c,r>c,r"`; a merge is `"c,r>c,r=n"` where n = the
number of checkers moved (the top n of the source; the focus/mixtour `=k`
precedent). With no legal move the single legal move is `"pass"`.

White (seat 0, rows 0-2) moves first. Renders via the standard square board +
`piece.stack` towers (Lasca's renderer).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 8
WHITE, BLACK = 0, 1
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
TARGET = 8                     # a stack of exactly 8 is removed and scored
STACKS_TO_WIN = 2              # majority of the three stacks of 8
# Engine safeguards only -- Byte itself is drawless by design (see rules.md):
NO_PROGRESS = 100              # plies without a merge -> draw
PLY_CAP = 1000


def _on(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE and (c + r) % 2 == 1


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _dist(a, b):
    """Moves needed between two dark squares = Chebyshev distance (a one-square
    diagonal step changes each of |dc|,|dr| by at most 1; parity always matches)."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


@dataclass
class BState:
    board: dict = field(default_factory=dict)   # (c,r) -> tuple of owners, bottom->top
    scored: dict = field(default_factory=dict)  # owner -> stacks of 8 won
    to_move: int = WHITE
    since: int = 0                              # plies since the last merge
    ply: int = 0
    winner: object = None


class Byte(Game):
    uid = "byte"
    name = "Byte"

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        board = {}
        for r in (0, 1, 2):                     # White: dark squares of rows 0-2
            for c in range(SIZE):
                if _on(c, r):
                    board[(c, r)] = (WHITE,)
        for r in (5, 6, 7):                     # Black: dark squares of rows 5-7
            for c in range(SIZE):
                if _on(c, r):
                    board[(c, r)] = (BLACK,)
        return BState(board=board, scored={WHITE: 0, BLACK: 0}, to_move=WHITE)

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _merges(self, board, player):
        """All legal merges for `player`: move the top n checkers of stack A onto
        a diagonally adjacent stack B. Legality (PDF "Merging Stacks"): the picked
        checker (level k = hA-n+1 of A) must be player's own, must rise to a
        higher altitude (lands at level hB+1 > k, i.e. n >= hA-hB+1), and the
        result may not exceed 8 (hB + n <= 8)."""
        out = []
        for (ac, ar), ca in board.items():
            ha = len(ca)
            for (dc, dr) in DIAG:
                b = (ac + dc, ar + dr)
                cb = board.get(b)
                if cb is None:
                    continue
                hb = len(cb)
                for n in range(max(1, ha - hb + 1), ha + 1):
                    if hb + n > TARGET:
                        break                    # taller portions only get worse
                    if ca[ha - n] == player:     # your checker at level hA-n+1
                        out.append(((ac, ar), b, n))
        return out

    def _slides(self, board, player):
        """All legal basic moves: a stack with no diagonally adjacent stack, whose
        BOTTOM checker is player's, slides one diagonal square, strictly closer to
        (one of) its closest stack(s)."""
        out = []
        for a, ca in board.items():
            if ca[0] != player:
                continue
            if any(board.get((a[0] + dc, a[1] + dr)) for (dc, dr) in DIAG):
                continue                         # adjacent to a stack: merge only
            others = [x for x in board if x != a]
            if not others:
                continue
            dmin = min(_dist(a, x) for x in others)
            nearest = [x for x in others if _dist(a, x) == dmin]
            for (dc, dr) in DIAG:
                t = (a[0] + dc, a[1] + dr)
                if not _on(*t):
                    continue
                # t is empty: every stack is >= 2 away, so a neighbour of `a`
                # is >= 1 away from all of them.
                if any(_dist(t, x) < dmin for x in nearest):
                    out.append((a, t))
        return out

    def _real_moves(self, state):
        p = state.to_move
        moves = [f"{a[0]},{a[1]}>{b[0]},{b[1]}={n}"
                 for (a, b, n) in self._merges(state.board, p)]
        moves += [f"{a[0]},{a[1]}>{t[0]},{t[1]}"
                  for (a, t) in self._slides(state.board, p)]
        return moves

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        return self._real_moves(state) or ["pass"]

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        player = state.to_move
        board = dict(state.board)
        scored = dict(state.scored)
        winner = None
        since = state.since + 1

        if move != "pass":
            if "=" in move:                              # ---- merge ----
                path, nstr = move.split("=")
                n = int(nstr)
                srcs, dsts = path.split(">")
                src, dst = _cell(srcs), _cell(dsts)
                ca = board[src]
                moving = ca[-n:]                         # top n, order preserved
                rest = ca[:-n]
                if rest:
                    board[src] = rest
                else:
                    del board[src]
                merged = board[dst] + moving
                if len(merged) == TARGET:                # stack of 8: score it
                    del board[dst]
                    top = merged[-1]                     # top checker's owner wins it
                    scored[top] = scored.get(top, 0) + 1
                    if scored[top] >= STACKS_TO_WIN:     # majority of 3 clinched
                        winner = top
                else:
                    board[dst] = merged
                since = 0
            else:                                        # ---- basic move ----
                srcs, dsts = move.split(">")
                board[_cell(dsts)] = board.pop(_cell(srcs))

        return BState(board=board, scored=scored, to_move=1 - player,
                      since=since, ply=state.ply + 1, winner=winner)

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.since >= NO_PROGRESS or state.ply >= PLY_CAP))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    def heuristic(self, state):
        """Rollout-cutoff eval: stacks of 8 already won dominate; owning the top
        (and secondarily the bottom) of tall stacks is the live currency."""
        import math
        bal = 3.0 * (state.scored.get(WHITE, 0) - state.scored.get(BLACK, 0))
        for col in state.board.values():
            w = len(col) / 8.0
            bal += (w if col[-1] == WHITE else -w)
            bal += 0.25 * (w if col[0] == WHITE else -w)
        v = math.tanh(0.5 * bal)
        return [v, -v]

    # ---- serialise ---------------------------------------------------------
    def _col_str(self, col):
        return "".join("WB"[o] for o in col)

    def _parse_col(self, s):
        return tuple(0 if ch == "W" else 1 for ch in s)

    def serialize(self, state):
        return {
            "board": {f"{c},{r}": self._col_str(col)
                      for (c, r), col in state.board.items()},
            "scored": {str(k): v for k, v in state.scored.items()},
            "to_move": state.to_move,
            "since": state.since,
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return BState(
            board={_cell(k): self._parse_col(v) for k, v in d["board"].items()},
            scored={int(k): v for k, v in d.get("scored", {}).items()},
            to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
            winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if move == "pass":
            return "pass"
        if "=" in move:
            path, n = move.split("=")
            return f"{path} (x{n})"
        return move.replace(">", "-")

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), col in state.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": col[-1],                    # top checker's owner
                "stack": list(col),                  # bottom -> top
                "label": str(len(col)) if len(col) > 1 else "",
            })
        names = {WHITE: "White", BLACK: "Black"}
        sw, sb = state.scored.get(WHITE, 0), state.scored.get(BLACK, 0)
        tally = f"stacks won {sw}:{sb}"
        if state.winner is not None:
            cap = f"{names[state.winner]} wins ({tally})"
        elif self._draw(state):
            cap = f"Draw ({tally})"
        else:
            cap = f"{names[state.to_move]} to move ({tally})"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
