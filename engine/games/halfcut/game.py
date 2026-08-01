"""Halfcut - a square-board connection game by Mark Steere (August 2023).

Played on the squares of an initially empty NxN board.  The TOP and BOTTOM
edges are RED, the LEFT and RIGHT edges are BLUE.  Red (player 0) must form a
path of red checkers - interconnected via HORIZONTAL or VERTICAL adjacencies
only - joining the two red sides; Blue (player 1) joins the two blue sides.
"Diagonal adjacencies are irrelevant in Halfcut."

Players alternate placing one checker of their own colour on an unoccupied
square, RED FIRST.  "Passing is not allowed, but if you don't have an available
placement, your turn is skipped."

THE CROSSCUT MACHINERY (the whole game)

  CROSSCUT        four checkers filling a 2x2 area, two of each colour, with
                  like colours diagonally opposed.
  CROSSCUT GROUP  the (monocolour, orthogonally connected) group containing a
                  crosscut checker.  A crosscut therefore has up to two
                  crosscut groups per colour - one per checker, and the two
                  same-coloured checkers of a crosscut are diagonally opposed,
                  so they need not be in the same group.
  CROSSCUT RULE   "You can only form a crosscut if by doing so you create a new
                  crosscut group which is larger than at least one of the enemy
                  crosscut groups OF THE CROSSCUT."
  REMOVAL         "Having formed a crosscut, immediately remove the enemy
                  crosscut checkers which are part of enemy crosscut groups
                  which are smaller than your newly formed crosscut group,
                  concluding your turn."
  SIMULTANEOUS    a placement forming two crosscuts at once must satisfy the
                  crosscut rule for each of them, considered separately.

Source: the official rule sheet, marksteeregames.com/Halfcut_rules.pdf
(Illustrator PDF, ModDate 2023-08-14, md5 4d0c94735c463c4e7d1e9e8702a41794).
All seven figures are reproduced verbatim in selftest.py and every printed
number in the prose is asserted against this implementation:

  Figure 1   a 6x6 position in which BLUE has won.  Its coloured frame is the
             ground truth for the seat/edge mapping: the RED bars are the top
             and bottom of the board, the BLUE bars the left and right, and the
             winning blue chain runs from the left column to the right column.
  Figure 2   the crosscut shape.
  Figure 3   "Red has crosscut groups of sizes 1 and 4.  Blue has crosscut
             groups of sizes 2 and 3."  Pins the per-CHECKER reading of
             "crosscut group" and the orthogonal-only group definition.
  Figure 4   Red MAY place on the ?: his new crosscut group of size 3 is larger
             than the blue crosscut group of size 2 (the crosscut's other blue
             group is size 3).  Pins "at least one", i.e. compare against the
             SMALLER of the crosscut's enemy groups.
  Figure 5   Red may NOT place on the ? (new group 3 vs blue groups 3 and 5);
             Blue MAY (new group 9 vs red groups 1 and 1).  Pins that the two
             colours are judged independently at the same square.
  Figures 6a/6b  before/after: Red places the dotted checker (new group 4) and
             kills exactly ONE blue checker - the crosscut checker whose group
             has size 2.  The crosscut's other blue checker (group size 5)
             survives, AND the second checker of the size-2 group survives.
             Pins that removal takes the crosscut CHECKERS, never whole groups.
  Figure 7   simultaneous crosscuts: Red's new group of size 3 beats the left
             crosscut's blue size-2 group but not either of the right
             crosscut's blue size-3 groups, so the placement is illegal.

IMPLEMENTATION NOTES

* Legality and removal are both judged on the position IMMEDIATELY AFTER the
  placement and BEFORE any removal.  This cannot matter for your own group
  (removing enemy checkers can never merge or split a friendly group) and it
  cannot matter for the enemy groups either: every group a removal touches has
  size < N, groups are disjoint, so removing a checker of one such group leaves
  every other group - in particular any group of size >= N - untouched.
  Sequential and simultaneous resolution are therefore provably identical; see
  rules.md.

* Only the (at most four) 2x2 areas containing the new checker can gain a
  crosscut, and in each of them the new checker is a corner, so the test is
  local: a crosscut is formed towards a diagonal neighbour that holds a
  FRIENDLY checker while both squares orthogonally between them hold ENEMY
  checkers.

* NO CROSSCUT EVER SURVIVES A TURN.  The crosscut rule says your new group must
  be larger than at least one enemy crosscut group of the crosscut; the removal
  rule says every enemy crosscut checker whose group is smaller than your new
  group is removed.  Those are the same comparison, so forming a crosscut
  ALWAYS removes at least one of its own enemy checkers and destroys it.  A
  removal can only empty squares, so it never creates one either.  Hence every
  position at the start of a turn is crosscut-free (`crosscuts_on_board` is the
  independent whole-board diagnostic; the selftest asserts it every ply).
  This is what the name means, and it is why Halfcut inherits Crossway's
  drawlessness - see rules.md for the full proof.

* Skips are applied inside apply_move (the platform wants a non-empty
  legal_moves on every non-terminal state), so EVERY ply of the game is a
  placement.  If NEITHER player can place, the game ends; with no connection on
  the board that would be an honest draw.  That branch is provably unreachable
  (rules.md carries the proof; selftest.py asserts both of its lemmas on
  constructed inputs and exhaustively on small boards), but a fabricated
  tiebreak would be a bug, so the draw is real code rather than an invented
  winner.

* A DECISIVE RESULT OUTRANKS THE STALL: the winning connection is checked
  before the skip/stall bookkeeping, so a placement that connects wins even if
  it simultaneously leaves both players with no legal placement.

* NO `heuristic` IS SHIPPED, and that is a measured decision, not an omission.
  An edge-distance evaluation (0-1 BFS: your own checker free, an empty square
  one step, an enemy checker blocking) was written and played head to head
  through `MCTSBot` - the consumer that would use it - against the same bot
  with a constant-zero evaluation, which is exactly what a game without a
  `heuristic` gets.  At the production shape (9x9, max_rollout=50, 0.5 s/move,
  colours alternating) it scored 11/24 in one run and 17/26 in another, i.e.
  28/50 = 0.56 pooled: indistinguishable from no evaluation.  It IS
  informative - with the cutoff forced (max_rollout=4) it scored 13/14 - but
  each call costs two whole-board BFS, which roughly halves the rollout count,
  and at the real rollout depth that cost cancels the information.  See
  rules.md.

TERMINATION.  Checkers are removed, so the board does not fill monotonically
and the usual "one empty square fewer" argument is unavailable.  Instead order
positions by their MULTISET OF GROUP SIZES, sorted descending and compared
lexicographically.  Let N be the size of the group containing the checker just
placed.  Every friendly group it merged has size <= N-1, and the removal rule
only touches enemy groups of size < N (whose pieces can only split into still
smaller groups), so the multiset of group sizes >= N gains exactly one member,
N, and loses none: the ordering strictly increases on every ply.  The multiset
lives in a finite set (total size <= size*size), so play is finite.  No ply cap
and no repetition rule are needed or shipped.  `group_size_signature` is that
monovariant, exposed so the selftest can assert it strictly increases.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1        # Red joins top<->bottom (rows), Blue left<->right (cols)

_ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
_DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class HalfcutState:
    size: int = 11
    board: dict = field(default_factory=dict)   # (c, r) -> RED / BLUE
    to_move: int = RED
    last: Optional[tuple] = None                # checker placed by the previous mover
    removed: tuple = ()                         # enemy checkers it killed
    winner: Optional[int] = None
    stalled: bool = False                       # neither player can place
    ply: int = 0
    skips: int = 0                              # turns skipped so far (no placement)


# --------------------------------------------------------------------------
# groups
# --------------------------------------------------------------------------

def group_of(board: dict, cell) -> set:
    """The monocolour, ORTHOGONALLY connected group containing an occupied cell.

    "A group here is a monocolored group of checkers interconnected
    horizontally or vertically, or both.  Diagonal adjacencies are irrelevant
    in Halfcut."
    """
    who = board[cell]
    seen = {cell}
    stack = [cell]
    while stack:
        c, r = stack.pop()
        for dc, dr in _ORTH:
            nb = (c + dc, r + dr)
            if nb not in seen and board.get(nb) == who:
                seen.add(nb)
                stack.append(nb)
    return seen


def group_size(board: dict, cell) -> int:
    """Size of the group containing an occupied cell."""
    return len(group_of(board, cell))


def group_size_signature(board: dict) -> tuple:
    """The termination monovariant: every group size, sorted DESCENDING.

    Compared lexicographically this strictly increases on every ply of a legal
    game (see the module docstring), which is what makes Halfcut finite.
    Written as an independent whole-board recomputation so the selftest can
    check it without trusting the incremental code.
    """
    seen = set()
    sizes = []
    for cell in board:
        if cell in seen:
            continue
        grp = group_of(board, cell)
        seen |= grp
        sizes.append(len(grp))
    return tuple(sorted(sizes, reverse=True))


# --------------------------------------------------------------------------
# crosscuts
# --------------------------------------------------------------------------

def crosscuts_formed(board: dict, c: int, r: int, player: int) -> list:
    """The crosscuts `player` would form by placing on the empty square (c, r).

    Returns one entry per crosscut, each the pair of ENEMY crosscut checkers of
    that crosscut (the two squares orthogonally adjacent to (c, r) inside its
    2x2).  Only the four 2x2 areas containing (c, r) can gain a crosscut, and
    (c, r) is a corner of each, so a crosscut is formed towards a diagonal
    neighbour holding a FRIENDLY checker with both squares orthogonally between
    them holding ENEMY checkers.

    Note the board argument does NOT need the new checker on it - none of the
    four squares inspected is (c, r) itself.
    """
    enemy = 1 - player
    out = []
    for dc, dr in _DIAG:
        a = (c + dc, r)
        b = (c, r + dr)
        if (board.get((c + dc, r + dr)) == player
                and board.get(a) == enemy
                and board.get(b) == enemy):
            out.append((a, b))
    return out


def crosscuts_on_board(board: dict, size: int) -> list:
    """Every crosscut present anywhere on the board (diagnostic).

    Returns the (c, r) lower-left squares of the offending 2x2 areas.  In real
    play this is ALWAYS empty at the start of a turn: the empty board has none,
    every crosscut a placement forms is immediately half-cut by its own
    removal, and a removal cannot create one.  Deliberately written without
    reference to any candidate square, so the selftest can cross-check the
    local `crosscuts_formed` predicate against it.
    """
    out = []
    for c in range(size - 1):
        for r in range(size - 1):
            a = board.get((c, r))
            b = board.get((c + 1, r))
            d = board.get((c, r + 1))
            e = board.get((c + 1, r + 1))
            if a is None or b is None or d is None or e is None:
                continue
            if a == e and b == d and a != b:
                out.append((c, r))
    return out


def resolve(board: dict, c: int, r: int, player: int):
    """Place `player`'s checker on (c, r) and apply the crosscut rule.

    Returns `(new_board, removed, mine)` when the placement is legal and
    `(None, (), mine)` when it is not, where `mine` is the size of the mover's
    newly formed crosscut group (0 when no crosscut is formed and the group was
    never needed).

    Both the legality test and the removal set are read off the position
    immediately AFTER the placement and BEFORE any removal - the sheet's
    "having formed a crosscut" position, which is exactly what Figure 6a
    prints.
    """
    crosses = crosscuts_formed(board, c, r, player)
    out = dict(board)
    out[(c, r)] = player
    if not crosses:
        return out, (), 0
    mine = group_size(out, (c, r))
    # Enemy group sizes are read once, on the pre-removal position.  Caching
    # also keeps a shared enemy checker (two crosscuts can share one) honest.
    sizes = {}
    kill = set()
    for pair in crosses:
        smaller = False
        for p in pair:
            if p not in sizes:
                sizes[p] = group_size(out, p)
            if sizes[p] < mine:
                smaller = True
                kill.add(p)
        if not smaller:
            # The crosscut rule fails for THIS crosscut, so - simultaneous
            # crosscuts being judged "each considered separately" - the whole
            # placement is illegal.
            return None, (), mine
    for p in kill:
        del out[p]
    return out, tuple(sorted(kill)), mine


def is_legal(board: dict, c: int, r: int, player: int) -> bool:
    """May `player` place on the empty square (c, r)?"""
    return resolve(board, c, r, player)[0] is not None


def placements(board: dict, size: int, player: int) -> list:
    """Every legal placement square for `player`, in (c, r) reading order."""
    return [(c, r) for r in range(size) for c in range(size)
            if (c, r) not in board and is_legal(board, c, r, player)]


def has_placement(board: dict, size: int, player: int) -> bool:
    """Does `player` have ANY legal placement?  (short-circuiting `placements`)"""
    for r in range(size):
        for c in range(size):
            if (c, r) not in board and is_legal(board, c, r, player):
                return True
    return False


# --------------------------------------------------------------------------
# connection
# --------------------------------------------------------------------------

def connects(board: dict, player: int, size: int) -> bool:
    """Does `player` join their two sides via an ORTHOGONAL chain of checkers?"""
    if player == RED:                          # row 0 <-> row size-1
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == RED]

        def at_goal(cell):
            return cell[1] == size - 1
    else:                                      # col 0 <-> col size-1
        starts = [(0, r) for r in range(size) if board.get((0, r)) == BLUE]

        def at_goal(cell):
            return cell[0] == size - 1
    seen = set(starts)
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if at_goal(cur):
            return True
        cc, cr = cur
        for dc, dr in _ORTH:
            nb = (cc + dc, cr + dr)
            if nb not in seen and board.get(nb) == player:
                seen.add(nb)
                stack.append(nb)
    return False


def connection_path(board: dict, player: int, size: int) -> list:
    """One winning chain for `player`, or [] if there is none (diagnostic/render)."""
    if player == RED:
        starts = [(c, 0) for c in range(size) if board.get((c, 0)) == RED]

        def at_goal(cell):
            return cell[1] == size - 1
    else:
        starts = [(0, r) for r in range(size) if board.get((0, r)) == BLUE]

        def at_goal(cell):
            return cell[0] == size - 1
    prev = {s: None for s in starts}
    queue = deque(starts)
    while queue:
        cur = queue.popleft()
        if at_goal(cur):
            path = []
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        for dc, dr in _ORTH:
            nb = (cur[0] + dc, cur[1] + dr)
            if nb not in prev and board.get(nb) == player:
                prev[nb] = cur
                queue.append(nb)
    return []


class Halfcut(Game):
    name = "Halfcut"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HalfcutState:
        size = int((options or {}).get("size", 11))
        return HalfcutState(size=size)

    def current_player(self, s: HalfcutState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def legal_moves(self, s: HalfcutState) -> list:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in placements(s.board, s.size, s.to_move)]

    # -- move application ---------------------------------------------------

    def _advance(self, s: HalfcutState, mover: int) -> None:
        """Hand the turn on after `mover` placed, applying the skip rule.

        "Passing is not allowed, but if you don't have an available placement,
        your turn is skipped."  A skip is not a ply of its own here: if the
        opponent cannot place we simply give the turn back to `mover`; if
        neither side can place the game is over.
        """
        opp = 1 - mover
        if has_placement(s.board, s.size, opp):
            s.to_move = opp
        elif has_placement(s.board, s.size, mover):
            s.to_move = mover
            s.skips += 1
        else:
            s.stalled = True
            s.to_move = opp

    def apply_move(self, s: HalfcutState, move: str, rng=None) -> HalfcutState:
        me = s.to_move
        c, r = _cell(move)
        board, removed, _ = resolve(s.board, c, r, me)
        if board is None:
            raise ValueError(f"illegal move {move!r}: crosscut rule")
        out = HalfcutState(size=s.size, board=board, to_move=1 - me, last=(c, r),
                           removed=removed, ply=s.ply + 1, skips=s.skips)
        # A decisive result outranks the stall bookkeeping.
        if connects(board, me, s.size):
            out.winner = me
            return out
        self._advance(out, me)
        return out

    # -- termination / scoring ----------------------------------------------

    def is_terminal(self, s: HalfcutState) -> bool:
        return s.winner is not None or s.stalled

    def returns(self, s: HalfcutState) -> list:
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]    # both players stuck with nobody connected: a draw

    # -- serialization ------------------------------------------------------

    def serialize(self, s: HalfcutState) -> dict:
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "last": None if s.last is None else f"{s.last[0]},{s.last[1]}",
            "removed": [f"{c},{r}" for (c, r) in s.removed],
            "winner": s.winner,
            "stalled": s.stalled,
            "ply": s.ply,
            "skips": s.skips,
        }

    def deserialize(self, d: dict) -> HalfcutState:
        return HalfcutState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            last=None if d.get("last") is None else _cell(d["last"]),
            removed=tuple(_cell(k) for k in d.get("removed", ())),
            winner=d.get("winner"),
            stalled=d.get("stalled", False),
            ply=d.get("ply", 0),
            skips=d.get("skips", 0),
        )

    # -- presentation -------------------------------------------------------

    def _coord(self, cell) -> str:
        letters = "abcdefghijklmnopqrstuvwxyz"
        c, r = cell
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{r + 1}"

    def describe_move(self, s: HalfcutState, move: str) -> str:
        p = _cell(move)
        nxt = self.apply_move(s, move)
        text = self._coord(p)
        if nxt.removed:
            text += "x" + "".join(self._coord(q) for q in nxt.removed)
        if nxt.winner is not None:
            text += "#"
        elif nxt.stalled:
            text += " (both stuck)"
        elif nxt.skips > s.skips:
            text += " (opponent skipped)"
        return text

    def render(self, s: HalfcutState, perspective=None) -> dict:
        names = {RED: "Red", BLUE: "Blue"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.stalled:
            caption = "Draw - neither player has a legal placement"
        else:
            edge = "top-bottom" if s.to_move == RED else "left-right"
            caption = f"{names[s.to_move]} to move ({edge})"
        # The winning chain goes in FIRST so the last-move marker still wins on
        # the square they share: Board.jsx keys `highlights` by cell (last write
        # wins) and draws only the 'goal' and 'last-move' kinds.
        highlights = []
        if s.winner is not None:
            highlights += [{"cell": f"{c},{r}", "kind": "goal"}
                           for (c, r) in connection_path(s.board, s.winner, s.size)]
        if s.last is not None:
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})
        return {
            "board": {
                "type": "square", "width": s.size, "height": s.size,
                "edges": {"top": RED, "bottom": RED,
                          "left": BLUE, "right": BLUE},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
