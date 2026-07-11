"""Mixtour -- Dieter Stein's 2011 pure stacking game on an empty 5x5 board.

Each player has a supply of 20 pieces. On a turn you either ENTER a piece of
your colour on an empty square, or MOVE the top part of any stack (ownership
does not matter -- you may move your opponent's pieces!) in a straight line,
orthogonally or diagonally, onto another stack. The crux: the move's distance
must exactly equal the TARGET stack's height (before landing), and moving
pieces may not cross occupied squares. Stacks may be split at any level.
You may not "effectively take back" the opponent's last move (moving the
same pieces straight back). Build a stack of height 5+ and whoever owns its
TOP piece wins immediately (the standard 1-point game).

If you cannot enter and have no stack move, you must pass; two passes in
sequence is an official draw. The official rules note that endless single-
piece loops are possible and "should be declared drawn" -- implemented here
as a threefold-repetition draw plus no-progress / total-ply backstops.

Rules verified against the designer's page: https://spielstein.com/games/mixtour/rules

Cells are "c,r" on the 5x5 grid ((0,0) = a1). Moves: enter = "c,r";
stack move = "src>dst" (single piece) or "src>dst=k" (top k pieces, picker).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from agp.game import Game

SIZE = 5
WHITE, RED = 0, 1
SUPPLY = 20
WIN_HEIGHT = 5
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]

NO_PROGRESS_DRAW = 100      # plies without an entry (or a score) -> draw backstop
PLY_CAP = 600               # absolute hard stop -> draw
NAMES = {WHITE: "White", RED: "Red"}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE


@dataclass
class MxState:
    board: dict = field(default_factory=dict)   # (c,r) -> tuple of owners, bottom->top
    supply: list = field(default_factory=lambda: [SUPPLY, SUPPLY])
    to_move: int = WHITE
    passes: int = 0                              # consecutive passes
    since: int = 0                               # plies since an entry (or score)
    ply: int = 0
    reps: dict = field(default_factory=dict)     # position key -> count (reset on entry)
    no_takeback: object = None                   # (src, dst, k) forbidden for the mover
    winner: object = None


class Mixtour(Game):

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        st = MxState()
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _stack_moves(self, state):
        """All legal stack moves as (src, dst, k) triples.

        In each of the 8 directions from a source, the FIRST occupied square
        is the only reachable one (stacks may not cross occupied spaces), and
        it is a legal target iff its height equals the distance travelled.
        """
        board = state.board
        out = []
        for src, col in board.items():
            h = len(col)
            for (dc, dr) in DIRS:
                c, r = src[0] + dc, src[1] + dr
                dist = 1
                while _on(c, r):
                    tgt = board.get((c, r))
                    if tgt is not None:
                        if len(tgt) == dist:
                            for k in range(1, h + 1):
                                if state.no_takeback == (src, (c, r), k):
                                    continue      # would take back opponent's move
                                out.append((src, (c, r), k))
                        break                     # cannot cross an occupied square
                    c, r, dist = c + dc, r + dr, dist + 1
        return out

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        moves = []
        if state.supply[state.to_move] > 0:
            for r in range(SIZE):
                for c in range(SIZE):
                    if (c, r) not in state.board:
                        moves.append(f"{c},{r}")
        for (src, dst, k) in self._stack_moves(state):
            base = f"{src[0]},{src[1]}>{dst[0]},{dst[1]}"
            h = len(state.board[src])
            moves.append(base if h == 1 else f"{base}={k}")
        return moves if moves else ["pass"]

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        p = state.to_move
        ns = MxState(board=dict(state.board), supply=list(state.supply),
                     to_move=1 - p, passes=0, since=state.since + 1,
                     ply=state.ply + 1, reps=dict(state.reps),
                     no_takeback=None, winner=state.winner)

        if move == "pass":
            ns.passes = state.passes + 1
        elif ">" not in move:                     # enter a piece
            cell = _cell(move)
            ns.board[cell] = (p,)
            ns.supply[p] -= 1
            ns.since = 0
            ns.reps = {}                          # entries are irreversible
        else:                                     # move a stack (top k pieces)
            body, _, ks = move.partition("=")
            frm, _, to = body.partition(">")
            src, dst = _cell(frm), _cell(to)
            col = ns.board[src]
            k = int(ks) if ks else len(col)
            moved, rest = col[len(col) - k:], col[:len(col) - k]
            if rest:
                ns.board[src] = rest
            else:
                del ns.board[src]
            ncol = ns.board[dst] + moved
            if len(ncol) >= WIN_HEIGHT:           # the stack scores: top owner wins
                del ns.board[dst]                 # removed; pieces back to reserves
                for o in ncol:
                    ns.supply[o] += 1
                ns.winner = ncol[-1]
                ns.since = 0
            else:
                ns.board[dst] = ncol
                ns.no_takeback = (dst, src, k)    # opponent may not move it straight back

        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.passes >= 2
                     or state.reps.get(self._key(state), 0) >= 3
                     or state.since >= NO_PROGRESS_DRAW
                     or state.ply >= PLY_CAP))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    def heuristic(self, state):
        """Tall stacks you top are close to scoring; squash to (-1, 1)."""
        bal = 0.0
        for col in state.board.values():
            v = (len(col) ** 2) / 16.0
            bal += v if col[-1] == WHITE else -v
        t = math.tanh(0.5 * bal)
        return [t, -t]

    # ---- keys / serialise --------------------------------------------------
    def _col_str(self, col):
        return "".join(str(o) for o in col)

    def _key(self, state):
        b = "|".join(f"{c},{r}:{self._col_str(state.board[(c, r)])}"
                     for r in range(SIZE) for c in range(SIZE)
                     if (c, r) in state.board)
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        return {
            "board": {f"{c},{r}": self._col_str(col)
                      for (c, r), col in state.board.items()},
            "supply": list(state.supply), "to_move": state.to_move,
            "passes": state.passes, "since": state.since, "ply": state.ply,
            "reps": dict(state.reps),
            "no_takeback": (None if state.no_takeback is None else
                            [list(state.no_takeback[0]), list(state.no_takeback[1]),
                             state.no_takeback[2]]),
            "winner": state.winner,
        }

    def deserialize(self, d):
        nt = d.get("no_takeback")
        return MxState(
            board={_cell(k): tuple(int(ch) for ch in v)
                   for k, v in d["board"].items()},
            supply=list(d["supply"]), to_move=d["to_move"],
            passes=d.get("passes", 0), since=d.get("since", 0),
            ply=d.get("ply", 0), reps=dict(d.get("reps", {})),
            no_takeback=(None if nt is None else
                         (tuple(nt[0]), tuple(nt[1]), nt[2])),
            winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def _alg(self, cell):
        return "abcde"[cell[0]] + str(cell[1] + 1)

    def describe_move(self, state, move):
        if move == "pass":
            return "pass"
        if ">" not in move:
            return f"+{self._alg(_cell(move))}"
        body, _, ks = move.partition("=")
        frm, _, to = body.partition(">")
        s = f"{self._alg(_cell(frm))}-{self._alg(_cell(to))}"
        return f"{s} x{ks}" if ks else s

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), col in state.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": col[-1],
                "stack": list(col),               # bottom -> top owners
            })
        if state.winner is not None:
            cap = f"{NAMES[state.winner]} wins (stack of {WIN_HEIGHT})"
        elif self._draw(state):
            cap = "Draw"
        else:
            cap = (f"{NAMES[state.to_move]} to move · reserve "
                   f"W {state.supply[WHITE]} / R {state.supply[RED]}")
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
