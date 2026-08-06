"""Amoeba — Masahiro Nakajima, 2010 (nestorgames rulebook, © 2014 Néstor Romeral Andrés).

A hexhex-4 board of 37 POINTS (the vertices of a triangular grid, drawn here as
hex cells — the two are the same graph).  Each player owns ten discs plus one
"kernel"; the kernel is an ordinary piece in every respect except that burying
it under an enemy piece loses the game.

A *stack* is a pile of pieces of any height, even one.  A stack is controlled by
the owner of its TOPMOST piece — so a stack can hold enemy pieces, and stacks
change hands.  On your turn you take one stack you control and either

  * MOVE it — the whole pile travels in a straight line exactly as many points
    as it has pieces, landing on top of anything already there.  Nothing
    blocks the way; only the far end has to be on the board.
  * SOW it — travelling the same line, drop the pile's BOTTOM piece on the
    first point, the next one up on the second, and so on, one piece per point.
    All the pieces must be deployed, so the whole line must fit on the board.

Sowing is the game's engine: the pieces of the pile land as separate stacks, and
any enemy piece you were carrying is handed back to its owner as the new top of
whatever point it falls on.

You win at the end of your turn if you control a stack containing the enemy
kernel, or if your opponent then has no legal move.  (Pieces are never removed,
so "no legal move" means every stack you control is jammed against the edge, or
you control none at all.)  And if the same position occurs for the THIRD time,
the game stops and whoever controls MORE STACKS wins — equal counts are a draw.

MOVE ENCODING (axial cell ids "q,r"; hexhex-4 ⇒ |q|,|r|,|q+r| <= 3):
  * "from>to"      — move the whole stack (one click on the source, one on the
    landing point).
  * "from>to=S"    — sow along that same line.
  For a stack of height >= 2 both moves always exist and share the same two
  cells, so the UI offers a "Move whole stack / Sow along the line" picker.  A
  height-1 stack has only the plain form: sowing one piece one point is the
  same action as moving it, so it is not listed twice.

TERMINATION.  Play can repeat for ever on its own: a lone disc shuffles A->B->A
while the opponent does the same (selftest.py plays the concrete 4-ply cycle
"a1-b1, g1-f1, b1-a1, f1-g1" out of the opening position).  The ENGLISH
rulebook has no clause for that at all — but the publisher's JAPANESE edition of
the same rulebook does, and it is the more complete document:

    「同一局面が 3 回現れた場合、[...] 制圧しているスタックの数がより多い
      プレーヤーの勝ちです。[...] 支配しているスタックの数が同じ場合は、
      引き分けとします。」
    "If the same position appears 3 times [...] the player controlling the
     greater number of stacks wins. [...] If the number of stacks controlled is
     equal, it is a draw."

So THREEFOLD REPETITION is a real, sourced rule and it is implemented here; it
also guarantees termination, since the position space is finite.  Two further
clauses of that paragraph are NOT mechanisable and are deliberately not
implemented: "if neither side has any effective move to control the enemy
kernel" (a judgement about whether a win is still possible) and an
end-by-mutual-agreement — the platform's resign/agree already covers the latter.
PLY_CAP is a pure engine backstop for the second of those; it adjudicates by the
sheet's OWN rule (count the stacks) rather than inventing a different outcome,
and it is set far above what play reaches, so it decides nothing.  Both
end-of-game counters are checked strictly AFTER the two win conditions, so a
decisive result can never be downgraded.  See rules.md.

NO `heuristic` is shipped, on purpose.  The MCTS rollout cutoff really does bite
here — measured over COMPLETE games (not from ply 0) it fires on 21.7% of
rollouts at the default max_rollout=50 — so an eval could help, and a candidate
(kernel burial depth + stacks controlled) was written and checked for shape:
zero-sum, bounded, never raising, 0 at the symmetric start.  But its head-to-head
through `MCTSBot` never finished, so there is NO evidence it plays better than
scoring the cutoff as a draw, and an unmeasured eval is not worth shipping (a
directionally-correct one measured 0.500 against constant-zero in another game).

Verified against the nestorgames rulebook in BOTH editions (rules text + all
three figures of each, decoded independently) and differentialled against the
AbstractPlay `gameslib` reference implementation (see the report; the harness is
not shipped).  NOTE that `gameslib` implements NO repetition rule, so that one
area has no differential coverage and is covered by constructed positions
instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from agp.game import Game

WHITE, BLACK = 0, 1
# Ground truth for these names is the rulebook: the SETUP figure draws the
# lower half of the board (rows a/b/c) in WHITE and the upper half (e/f/g) in
# BLACK, and "Each player has an allocated colour (White or Black). White
# starts."  Seat 0 is therefore White and starts, and White's pieces occupy the
# rows with r > 0 — which the renderer draws at the BOTTOM (screen y = 1.5*r).
SEAT_NAMES = ("White", "Black")

SIZE = 4                  # hexhex side length -> 37 points
N = SIZE - 1

# The six axial directions of a hex lattice (E, W, NE, SW, SE, NW on screen).
DIRS = ((1, 0), (-1, 0), (1, -1), (-1, 1), (0, 1), (0, -1))

# Threefold repetition ends the game (Japanese rulebook).  PLY_CAP is a pure
# engine backstop for the sheet's unmechanisable "the position does not
# converge" clause; both adjudicate by the sheet's own stack count.  Play never
# gets near either.
REPEAT_LIMIT = 3
PLY_CAP = 1000


# ---------------------------------------------------------------------------
# pieces: a small int so a stack is a plain tuple (bottom -> top)
#   bit 0 = owner (0 White, 1 Black);  value >= 2 = that owner's kernel
# ---------------------------------------------------------------------------
def piece(owner: int, kernel: bool = False) -> int:
    return owner + (2 if kernel else 0)


def owner_of(p: int) -> int:
    return p & 1


def is_kernel(p: int) -> bool:
    return p >= 2


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def _cells() -> tuple:
    return tuple((q, r) for r in range(-N, N + 1) for q in range(-N, N + 1)
                 if abs(q + r) <= N)


CELLS = _cells()
ON_BOARD = frozenset(CELLS)


def cid(c) -> str:
    return "%d,%d" % c


def parse_cell(s: str) -> tuple:
    q, r = s.split(",")
    return (int(q), int(r))


CIDS = tuple(cid(c) for c in CELLS)      # fixed cell order, for pos_key


def row_cells(r: int) -> list:
    """Row `r` left to right (screen x grows with q at fixed r)."""
    lo, hi = max(-N, -N - r), min(N, N - r)
    return [(q, r) for q in range(lo, hi + 1)]


def _setup() -> dict:
    """The rulebook's SETUP figure.

    Reading the figure top to bottom (rows g,f,e,d,c,b,a == r = -3..3):
    four black discs, the black kernel alone on the middle point of its row,
    six black discs, an empty middle row, six white discs, the white kernel
    alone on the middle point of its row, four white discs.

    Note the published figure OMITS one white disc (the right-hand end of row
    c): it draws 10 black discs but only 9 white ones, contradicting its own
    MATERIAL list ("10 white discs, 10 black discs") and breaking the 180°
    rotational symmetry that the other 36 points obey exactly.  The symmetric
    reading below is the one the material list, the symmetry and the reference
    implementation all agree on.  See rules.md.
    """
    b = {}
    for r, seat, kernel_only in ((-3, BLACK, False), (-2, BLACK, True), (-1, BLACK, False),
                                 (1, WHITE, False), (2, WHITE, True), (3, WHITE, False)):
        row = row_cells(r)
        if kernel_only:
            b[cid(row[len(row) // 2])] = (piece(seat, True),)
        else:
            for c in row:
                b[cid(c)] = (piece(seat, False),)
    return b


@dataclass(frozen=True)
class AState:
    board: dict = field(default_factory=dict)   # cell id -> tuple of pieces, bottom->top
    to_move: int = WHITE
    winner: int = None                          # seat index, or None
    drawn: bool = False                         # PLY_CAP backstop only
    ply: int = 0
    last: tuple = ()                            # cell ids touched by the last move
    reps: dict = field(default_factory=dict)    # position key -> times seen


def pos_key(board: dict, to_move: int) -> str:
    """Canonical "same position" key: the whole board plus the side to move.

    One digit per piece, cells in a fixed order, so it is short enough to store
    a whole game's history in the match record.
    """
    return "/".join("".join(str(p) for p in board.get(c, ())) for c in CIDS) \
        + "#%d" % to_move


class Amoeba(Game):
    name = "Amoeba"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> AState:
        board = _setup()
        # the opening position is itself the first occurrence
        return AState(board=board, to_move=WHITE,
                      reps={pos_key(board, WHITE): 1})

    def current_player(self, state: AState) -> int:
        return state.to_move

    # ---- moves -----------------------------------------------------------
    def legal_moves(self, state: AState) -> list:
        if self.is_terminal(state):
            return []
        out = []
        me = state.to_move
        for c, st in state.board.items():
            if owner_of(st[-1]) != me:
                continue
            n = len(st)
            q, r = parse_cell(c)
            for dq, dr in DIRS:
                to = (q + dq * n, r + dr * n)
                # A hexhex is convex along every lattice direction, so if the
                # far end is on the board every point in between is too — which
                # is exactly what sowing needs (all n pieces must be deployed).
                if to not in ON_BOARD:
                    continue
                base = "%s>%s" % (c, cid(to))
                out.append(base)
                if n > 1:
                    out.append(base + "=S")
        out.sort()
        return out

    # ---- applying --------------------------------------------------------
    @staticmethod
    def _decode(move: str):
        """-> (from-id, to-id, sowing?)"""
        frm, rest = move.split(">")
        sow = rest.endswith("=S")
        return frm, (rest[:-2] if sow else rest), sow

    def apply_move(self, state: AState, move: str, rng=None) -> AState:
        frm, to, sow = self._decode(move)
        st = state.board[frm]
        n = len(st)
        fq, fr = parse_cell(frm)
        tq, tr = parse_cell(to)
        dq, dr = (tq - fq) // n, (tr - fr) // n

        board = dict(state.board)
        del board[frm]
        if sow:
            touched = []
            for i in range(n):
                c = cid((fq + dq * (i + 1), fr + dr * (i + 1)))
                board[c] = board.get(c, ()) + (st[i],)
                touched.append(c)
        else:
            board[to] = board.get(to, ()) + st
            touched = [to]

        mover = state.to_move
        nxt = replace(state, board=board, to_move=1 - mover, ply=state.ply + 1,
                      last=tuple([frm] + touched))

        # "You win if, at the end of your turn, you control a stack with the
        # enemy kernel in it or if your opponent has no available moves at the
        # start of her turn."  Only the MOVER's condition is tested, exactly as
        # written: handing the opponent a stack containing your own kernel does
        # not lose on the spot, it loses at the end of THEIR next turn.
        winner = None
        if self._holds_enemy_kernel(board, mover):
            winner = mover
        elif not self.legal_moves(nxt):
            winner = mover
        if winner is not None:
            return replace(nxt, winner=winner)

        # Only now the end-of-game counters, so a decisive result can never be
        # downgraded.  Threefold repetition is the Japanese rulebook's rule;
        # PLY_CAP is the engine backstop for its unmechanisable
        # "position does not converge" clause.  BOTH adjudicate the way that
        # paragraph says to: whoever controls more stacks wins, equal is a draw.
        key = pos_key(board, nxt.to_move)
        seen = nxt.reps.get(key, 0) + 1
        nxt = replace(nxt, reps={**nxt.reps, key: seen})
        if seen >= REPEAT_LIMIT or nxt.ply >= PLY_CAP:
            w, b = self._stack_counts(board)
            if w == b:
                return replace(nxt, drawn=True)
            return replace(nxt, winner=WHITE if w > b else BLACK)
        return nxt

    @staticmethod
    def _stack_counts(board: dict) -> tuple:
        """(stacks White controls, stacks Black controls) — the tie-break."""
        n = [0, 0]
        for st in board.values():
            n[owner_of(st[-1])] += 1
        return (n[WHITE], n[BLACK])

    @staticmethod
    def _holds_enemy_kernel(board: dict, seat: int) -> bool:
        foe = 1 - seat
        for st in board.values():
            if owner_of(st[-1]) != seat:
                continue
            for p in st:
                if is_kernel(p) and owner_of(p) == foe:
                    return True
        return False

    # ---- terminal --------------------------------------------------------
    def is_terminal(self, state: AState) -> bool:
        return state.winner is not None or state.drawn

    def returns(self, state: AState) -> list:
        if state.winner is None:
            return [0.0, 0.0]
        out = [-1.0, -1.0]
        out[state.winner] = 1.0
        return out

    # ---- serialisation ---------------------------------------------------
    def serialize(self, state: AState) -> dict:
        return {
            "board": {c: list(st) for c, st in state.board.items()},
            "to_move": state.to_move,
            "winner": state.winner,
            "drawn": state.drawn,
            "ply": state.ply,
            "last": list(state.last),
            "reps": dict(state.reps),
        }

    def deserialize(self, data: dict) -> AState:
        return AState(
            board={c: tuple(st) for c, st in data["board"].items()},
            to_move=data["to_move"],
            winner=data["winner"],
            drawn=data["drawn"],
            ply=data["ply"],
            last=tuple(data["last"]),
            reps=dict(data["reps"]),
        )

    # ---- presentation ----------------------------------------------------
    def describe_move(self, state: AState, move: str) -> str:
        frm, to, sow = self._decode(move)
        n = len(state.board.get(frm, ()))
        return "%s>%s %s x%d" % (frm, to, "sow" if sow else "move", n)

    def _kernel_at(self, board: dict):
        """-> {seat: (cell id, 1-based level from the bottom, stack height)}."""
        found = {}
        for c, st in board.items():
            for i, p in enumerate(st):
                if is_kernel(p):
                    found[owner_of(p)] = (c, i + 1, len(st))
        return found

    def render(self, state: AState, perspective=None) -> dict:
        kern = self._kernel_at(state.board)
        # Which levels of a stack are kernels — the tower glyph paints owner
        # colours only, so the kernel's depth goes on the top band as a label
        # ("K2" = the kernel is the 2nd piece from the bottom) and the caption
        # spells both kernels out in full.
        marks = {}
        for seat, (c, lvl, _h) in kern.items():
            marks[c] = marks.get(c, "") + ("+" if c in marks else "") + "K%d" % lvl

        pieces = []
        for c, st in state.board.items():
            p = {"cell": c, "owner": owner_of(st[-1]),
                 "stack": [owner_of(x) for x in st]}
            if c in marks:
                p["label"] = marks[c]
            pieces.append(p)

        bits = []
        for seat in (WHITE, BLACK):
            if seat in kern:
                c, lvl, h = kern[seat]
                where = "top" if lvl == h else "level %d of %d" % (lvl, h)
                bits.append("%s kernel %s (%s)" % (SEAT_NAMES[seat], c, where))
        info = "; ".join(bits)
        w, b = self._stack_counts(state.board)

        if state.winner is not None:
            cap = "%s wins — %s" % (SEAT_NAMES[state.winner], info)
        elif state.drawn:
            cap = "Draw — equal stacks %d-%d — %s" % (w, b, info)
        else:
            cap = "%s to move — stacks %d-%d — %s" % (
                SEAT_NAMES[state.to_move], w, b, info)

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": SIZE},
            "pieces": pieces,
            "highlights": [{"cell": c, "kind": "last-move"} for c in state.last],
            "caption": cap,
            "choiceNames": {"": "Move whole stack", "S": "Sow along the line"},
            "choiceTitle": "Move the pile, or sow it?",
        }
