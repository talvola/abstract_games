"""Onager — Néstor Romeral Andrés, 2012 (nestorgames).

A hexagon-of-hexes with 6 cells per side (91 cells).  Each player fills the two
rows nearest himself (6 + 7 = 13 discs), then three neutral grey "lakes" are
placed.  You win by getting more of your pieces onto the opponent's back rank
than he has on yours.  Discs are never captured: a piece that jumps onto an
enemy piece simply sits ON it, and only the topmost disc of a stack is a
"piece".

SOURCE.  The nestorgames rulebook `ONAGER_EN.pdf`
(https://www.nestorgames.com/rulebooks/ONAGER_EN.pdf, md5
41f09beb55336f67e5aa6f57161fdcdb, PDF CreationDate 2018-06-23, credited
"Rules and rule book (c) 2012 Néstor Romeral Andrés.  Revisions by Nathan
Morse").  The English sheet has never been captured by the Wayback Machine, but
the SPANISH edition has (2012-12-11, archived 2016-03-27) and so has the
JAPANESE one (2018-06-23, archived 2021-10-14).  Comparing the three settles two
questions and exposes one unadvertised revision — see INTERPRETIVE DECISIONS.

BOARD AND COORDINATES.  Axial `(q, r)`, `|q| <= N-1`, `|r| <= N-1`,
`|q+r| <= N-1`, pointy-top hexes, so a ROW is a constant `r` drawn horizontally
(exactly how every figure in the rulebook draws the board: the widest row is
horizontal and the two 6-cell rows are the top and bottom edges).  `r` increases
DOWNWARDS in the renderer, so:

* seat 0 = **Black** = the bottom of the board.  Black fills rows `r = N-1`
  (N cells — Black's back rank) and `r = N-2` (N+1 cells).
* seat 1 = **White** = the top.  White fills rows `r = -(N-1)` (White's back
  rank) and `r = -(N-2)`.

`N + (N+1) = 2N+1` discs each, which is 13 at the published N = 6 — the exact
disc count in the rulebook's MATERIAL list, and the arithmetic that pins "your
2 nearest rows" to these two rows and no others.

TURN.  Do exactly one of:

* **WALK** — move one of your pieces to an ADJACENT EMPTY space.
* **JUMP** — two friendly PIECES aligned along one of the 3 axes with no
  obstacle (lake or any other disc) strictly between them, at distance `d`.
  One of them jumps over the other and lands `d` further on, i.e. `2d` from the
  jumper (Figure "a–d": (a) legal, empty landing, same distance; (b) legal,
  landing on an enemy piece with a LAKE sitting between the jumped-over piece
  and the landing square — the cells beyond the jumped-over piece need not be
  empty; (c) illegal, a lake BETWEEN the two friendly pieces; (d) illegal, a
  landing at `2d-1` instead of `2d`).  The landing square must be on the board
  and either empty or occupied by an ENEMY piece — never a lake, never a
  friendly piece.
  Landing on an enemy piece stacks onto it (nothing is captured or removed) and
  the piece MAY then jump again under the same conditions, and so on.
  Walks and jumps cannot be combined, and a jumping piece may not end its turn
  on the square it started from.

MOVE NOTATION — `"from>to"`, WITH NO ROUTE.  Whatever a turn is, its effect is
the same single operation: the mover's one disc leaves `from` (liberating any
disc under it) and lands on `to` (stacking on any enemy piece there).  A jump
chain changes NOTHING else — every square it passes through reverts the moment
the disc leaves it — so the destination determines the resulting position
completely and the route is not part of the move.  This also keeps every legal
move reachable in the web UI: continuing a chain is OPTIONAL, so a chain's
prefix is itself a legal move, and `Board.jsx` submits a clicked path as soon as
it matches one exactly — which would make every multi-hop chain unplayable if
routes were encoded.  `describe_move` reconstructs a shortest route for the move
log.

STACKS.  A stack is created only by jumping onto an ENEMY piece, so a stack's
colours always alternate and the disc under any piece is always an ENEMY disc.
Only the top disc is a "piece": it alone can move, it alone counts towards the
victory condition, and moving it LIBERATES the (enemy) disc beneath.  Stack
height is irrelevant.

VICTORY (checked at the START of a turn, before moving).  If the player to move
has strictly more pieces on the opponent's back rank than the opponent has on
his, he has won.  Otherwise, if he has no legal move, he loses.  Draws are by
agreement only.

INTERPRETIVE DECISIONS (each named, with the source that decided it)
--------------------------------------------------------------------
1. **WHITE MAKES THE FIRST MOVEMENT MOVE.**  The three lakes are placed as
   ordinary alternating turns starting with Black ("players alternate turns
   placing one 'lake' ... so Black places 2 lakes and White places 1"), and HOW
   TO PLAY says "Black starts.  Players alternate turns during the game."  Under
   strict alternation the four turns are Black-lake, White-lake, Black-lake,
   then White's first walk-or-jump.  The alternative reading (Black also opens
   the movement phase) would give Black two consecutive turns, which no sheet
   mentions, and would leave White with no compensation at all for placing one
   lake instead of two.  AbstractPlay's `onager.ts` independently implements the
   reading used here (its placement phase runs while `stack.length < 4`, with
   `currplayer` flipping every move).  All three language editions carry the
   same two sentences, so this is a genuine sheet-level ambiguity, resolved the
   only way that keeps "players alternate turns" true.
2. **ONLY TOPMOST DISCS COUNT TOWARDS VICTORY.**  The 2018 English sheet says
   only "Remember the definition of 'piece'"; the superseded 2012 SPANISH sheet
   is far more explicit — "Si al comienzo de tu turno (ANTES DE MOVER) tienes
   más PIEZAS (NO DISCOS) en la primera fila de tu oponente..." — pinning both
   the "before moving" timing and the "pieces, not discs" counting.  The endgame
   figure confirms the "topmost disc only" reading independently: one of White's
   two counted pieces on Black's back rank is only the TOP of a white-on-black
   stack (2 to 1).  (The black disc buried under it proves nothing either way —
   it sits on Black's OWN back rank, where it would never count for Black.)
3. **"CANNOT END THE TURN WHERE IT STARTED" IS A 2018 ADDITION, AND IS
   IMPLEMENTED AS "A JUMP CHAIN NEVER REVISITS A CELL".**  The 2012 Spanish
   sheet has no such sentence; the 2018 English and Japanese sheets both do.
   The clause is not vacuous: a jumper that was a STACK TOP leaves an enemy disc
   behind, so its start square really can be a legal landing square.
   During a chain the board is exactly "the original board with the mover's one
   disc moved to its current square" (each intermediate square reverts when the
   disc leaves it), so the position depends only on WHERE the disc is.  Hence a
   chain that revisits a cell reproduces an earlier position, and deleting the
   loop yields a legal chain with the SAME final square and the SAME resulting
   state.  Forbidding all revisits therefore loses no reachable successor state
   while making the sheet's clause impossible to violate — and it is what stops
   move generation from recursing forever.  `selftest.py` checks both halves on
   a constructed stack position.
4. **THE MOVER'S START SQUARE IS VACATED FOR THE SECOND AND LATER JUMPS.**  The
   piece is physically somewhere else, so it can no longer serve as the friendly
   piece to jump over, and the square it left is empty (or shows the liberated
   enemy disc).  AbstractPlay's `onager.ts` generates whole chains against the
   UN-UPDATED board and so disagrees.  Over a two-sided differential of 2,641
   positions (1,041 from played games plus 1,600 constructed ones, 1,720 of
   them holding stacks and 1,481 holding stacks three or more discs tall) the
   two engines agreed on every walk, every single jump and every terminal
   result, and differed on 13 multi-hop destinations — every one of them
   adjudicated mechanically to the same defect: the oracle's final hop needed a
   friendly piece standing on the mover's own vacated start square.  In that
   sample we never offered a destination the oracle rejected; over a larger run
   (12,997 movement plies) the same defect also shows up in the other direction,
   the oracle missing destinations the rules allow.  `selftest.py` pins the
   minimised case, with the premise that makes it non-vacuous.
5. **Board size is a platform option, not a rule.**  The published game is N = 6
   only (that is the board in the box and the source of the 13-disc count).
   N = 4, 5 and 7 are offered for convenience; the lake count stays 3 at every
   size, as in the published rules.

BOT EVALUATION.  This package deliberately ships NO ``heuristic``.  One was
written (back-rank difference plus normalised advancement towards the enemy back
rank) and MEASURED THROUGH ``MCTSBot``, the only consumer, at 100 iterations and
``max_rollout=4`` so the cutoff -- and therefore the eval -- is always reached,
seats alternated, 40 games per matchup on the side-4 board:

* against a CONSTANT-ZERO eval: **19-21** (0.475, two-sided p ~= 0.87) -- no
  measurable gain over having no eval at all;
* against its own SIGN-FLIPPED self: **23-17** (0.575, p ~= 0.43) -- not even
  the DIRECTION is established through the consumer.

The likely reason is structural: the win is tested at the START of a turn, so a
piece that arrives on the enemy back rank can simply be answered (jumped onto,
burying it, or matched at the other end), and an eval that rewards the arrival
scores a position the opponent refutes on the very next ply.  Rather than ship a
number that reads as bot strength and is not, the package ships none and records
the measurement.  See ``rules.md``.

TERMINATION.  Onager has no monovariant: walks are freely reversible and discs
are never removed, so a position can repeat forever and the rules offer no
repetition or no-progress rule (only "players may agree on a draw").  A hard ply
cap is therefore a platform backstop, not a rule.  It is derived from named
factors in code (`PLY_CAP_CELL_FACTOR * n_cells(size)`), scored as an honest
DRAW, and set far above anything real play reaches: the longest of 2,500
uniform-random games at N = 6 ran 730 plies against a cap of 18,200.  See
`selftest.py` for the checks and `rules.md` for the measured distribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SEAT_NAMES = ("Black", "White")

# Board sizes offered by the manifest.  6 is the published board (2*6+1 = 13
# discs per player, matching the rulebook's MATERIAL list).
SIZES = (4, 5, 6, 7)

# The published game always uses three lakes, placed alternately starting with
# Black, so Black places two and White one.
LAKES = 3

# Sentinel for a lake in the "top occupant" map.  Seats are 0 and 1.
LAKE = 2

# The six hex directions in axial (q, r) space, pointy-top: a row is a constant
# r drawn horizontally, so E/W are the horizontal neighbours and there is no
# vertical neighbour at all — exactly the geometry of the rulebook's figures
# (the walk figure marks W and E neighbours of the same piece).
DIRS = ((1, 0), (-1, 0), (1, -1), (0, -1), (0, 1), (-1, 1))

# Ply-cap backstop (see the module docstring): plies per board cell.  Measured
# over 2,500 uniform-random games at N = 6: mean 220 plies, median 207, 99th
# percentile 523, maximum 730 -- i.e. 8.0 plies per cell at the very worst.  200
# per cell leaves a factor of 25 over the longest random game ever observed, and
# the manifest's `max_random_plies` (2500) sits an order of magnitude BELOW the
# cap so a termination regression fails loudly instead of being absorbed.
PLY_CAP_CELL_FACTOR = 200


# --------------------------------------------------------------------------
#  Board geometry.  Pure functions on (size, cell) so the selftest and any
#  offline tool can use them without instantiating the game.
# --------------------------------------------------------------------------

def n_cells(size: int) -> int:
    """Number of cells on a hexagon-of-hexes with `size` cells per side."""
    return 3 * size * size - 3 * size + 1


def on_board(size: int, cell: tuple) -> bool:
    q, r = cell
    return abs(q) <= size - 1 and abs(r) <= size - 1 and abs(q + r) <= size - 1


def q_min(size: int, r: int) -> int:
    """Leftmost column of row `r` (the row drawn horizontally at height r)."""
    return max(-(size - 1), -(size - 1) - r)


def q_max(size: int, r: int) -> int:
    return min(size - 1, size - 1 - r)


def row_cells(size: int, r: int) -> list:
    return [(q, r) for q in range(q_min(size, r), q_max(size, r) + 1)]


def all_cells(size: int) -> list:
    """Every cell, in a deterministic top-to-bottom, left-to-right order."""
    out = []
    for r in range(-(size - 1), size):
        out.extend(row_cells(size, r))
    return out


def back_rank(size: int, seat: int) -> list:
    """The `size`-cell row a player defends.  Seat 0 (Black) is at the BOTTOM of
    the rendered board (r = size-1); seat 1 (White) is at the top."""
    return row_cells(size, size - 1 if seat == 0 else -(size - 1))


def home_rows(size: int, seat: int) -> list:
    """The two rows a player fills at setup: his back rank and the row in front
    of it — 2*size+1 cells in total (13 at the published size 6)."""
    if seat == 0:
        return row_cells(size, size - 1) + row_cells(size, size - 2)
    return row_cells(size, -(size - 1)) + row_cells(size, -(size - 2))


def centre(size: int) -> tuple:
    """The one space no lake may occupy."""
    return (0, 0)


def cell_id(cell: tuple) -> str:
    return f"{cell[0]},{cell[1]}"


def parse_cell(text: str) -> tuple:
    q, r = text.split(",")
    return int(q), int(r)


def cell_name(size: int, cell: tuple) -> str:
    """Printed-board name: a letter for the row counting UP from the bottom
    (Black's back rank is row `a`), then the 1-based index within that row.
    Same scheme as AbstractPlay's `HexTriGraph`, which makes the differential
    harness trivial to read."""
    q, r = cell
    row_from_bottom = (size - 1) - r
    return chr(ord("a") + row_from_bottom) + str(q - q_min(size, r) + 1)


def ply_cap(size: int) -> int:
    """Hard backstop on the number of plies, derived from the board rather than
    pinned: `PLY_CAP_CELL_FACTOR` plies per cell.  Onager has no repetition or
    no-progress rule, so this is a platform termination guarantee and NOT a rule
    of the game; reaching it is scored as an honest draw."""
    return PLY_CAP_CELL_FACTOR * n_cells(size)


# --------------------------------------------------------------------------
#  Move generation.  `stacks` maps a cell to a tuple of seats, bottom -> top;
#  `lakes` is a set of cells.  `occ` is the derived "who is on top" map, whose
#  values are a seat (0/1) or LAKE.
# --------------------------------------------------------------------------

def occupancy(stacks: dict, lakes) -> dict:
    occ = {c: s[-1] for c, s in stacks.items()}
    for c in lakes:
        occ[c] = LAKE
    return occ


def walk_targets(size: int, occ: dict, cell: tuple) -> list:
    """Every adjacent EMPTY space — a lake or any disc blocks."""
    q, r = cell
    out = []
    for dq, dr in DIRS:
        nb = (q + dq, r + dr)
        if on_board(size, nb) and nb not in occ:
            out.append(nb)
    return out


def jump_landings(size: int, occ: dict, cell: tuple, seat: int) -> list:
    """Every square the piece on `cell` may jump to in one hop.

    In each of the six directions, find the first occupied square: it must be a
    FRIENDLY piece (anything else — a lake, an enemy piece, or nothing at all —
    means no jump that way, which is Figure c).  If that partner is `d` away,
    the landing square is `2d` away and must be on the board and either empty or
    an enemy piece (Figures a and b).  Whatever sits strictly between the
    partner and the landing square is irrelevant (Figure b's lake)."""
    q, r = cell
    out = []
    for dq, dr in DIRS:
        d = 1
        while True:
            probe = (q + dq * d, r + dr * d)
            if not on_board(size, probe):
                break
            here = occ.get(probe)
            if here is not None:
                if here == seat:
                    land = (q + dq * 2 * d, r + dr * 2 * d)
                    if on_board(size, land):
                        there = occ.get(land)
                        if there is None or there == 1 - seat:
                            out.append(land)
                break
            d += 1
    return out


def jump_targets(size: int, stacks: dict, lakes, cell: tuple, seat: int) -> set:
    """Every square the piece on `cell` can reach by a jump — one hop, or a
    chain of them.

    The board is updated between hops (the mover's disc really does leave its
    square), and no cell may be visited twice.  See the module docstring,
    interpretive decision 3: the position during a chain depends only on WHERE
    the disc currently is, so a chain that revisits a cell reproduces an earlier
    position and can be shortened without changing the square it ends on.  The
    no-revisit rule therefore loses no reachable destination, subsumes the
    sheet's "cannot end the turn in the same space where it started", and is
    what stops this recursion from running forever."""
    work = {c: list(v) for c, v in stacks.items()}
    out: set = set()
    path = {cell}

    def recurse(cur):
        occ = occupancy(work, lakes)
        for land in jump_landings(size, occ, cur, seat):
            if land in path:
                continue
            out.add(land)
            if occ.get(land) != 1 - seat:
                continue                    # landed on an empty square: turn over
            # Continue the chain: the disc leaves `cur` (liberating whatever is
            # under it) and stacks onto the enemy piece at `land`.
            src = work[cur]
            src.pop()
            if not src:
                del work[cur]
            work.setdefault(land, []).append(seat)
            path.add(land)
            recurse(land)
            path.discard(land)
            work[land].pop()
            if not work[land]:
                del work[land]
            work.setdefault(cur, []).append(seat)

    recurse(cell)
    return out


def jump_route(size: int, stacks: dict, lakes, frm: tuple, to: tuple,
               seat: int) -> tuple:
    """A shortest legal chain of hops from `frm` to `to`, as a cell path, or
    `()` if there is none.  Used only for the move log: every chain that ends on
    the same square leaves the board in the SAME position (the mover's one disc
    moves, every square it passed through reverts), so any route is as good an
    explanation as any other."""
    base = {c: list(v) for c, v in stacks.items()}
    if frm in base:
        base[frm].pop()
        if not base[frm]:
            del base[frm]
    frontier = [(frm,)]
    while frontier:
        nxt = []
        for path in frontier:
            cur = path[-1]
            work = {c: list(v) for c, v in base.items()}
            work.setdefault(cur, []).append(seat)
            occ = occupancy(work, lakes)
            for land in jump_landings(size, occ, cur, seat):
                if land in path:
                    continue
                if land == to:
                    return path + (land,)
                if occ.get(land) == 1 - seat:
                    nxt.append(path + (land,))
        frontier = nxt
    return ()


def move_targets(size: int, stacks: dict, lakes, cell: tuple, seat: int) -> set:
    """Every square the piece on `cell` may move to this turn — walk or jump.

    A turn always has the same EFFECT whichever way it is played: the mover's
    one disc leaves `cell` (liberating any disc under it) and lands on the
    destination (stacking on any enemy piece there).  Nothing else on the board
    changes, not even the squares a jump chain passed through.  That is why a
    move is written `from>to` with no route: the destination determines the
    resulting position completely."""
    occ = occupancy(stacks, lakes)
    return (set(walk_targets(size, occ, cell))
            | jump_targets(size, stacks, lakes, cell, seat))


def all_turns(size: int, stacks: dict, lakes, seat: int) -> list:
    """Every `(from, to)` a player may play, in deterministic order."""
    out = []
    for cell in sorted(c for c, s in stacks.items() if s[-1] == seat):
        for to in sorted(move_targets(size, stacks, lakes, cell, seat)):
            out.append((cell, to))
    return out


def has_turn(size: int, stacks: dict, lakes, seat: int) -> bool:
    """Does `seat` have any legal move?  Exact and cheap: a single hop is always
    a complete legal move (it can never land back on its own start square), so
    the existence question never needs the chain search."""
    occ = occupancy(stacks, lakes)
    for cell, stack in stacks.items():
        if stack[-1] != seat:
            continue
        if walk_targets(size, occ, cell):
            return True
        if jump_landings(size, occ, cell, seat):
            return True
    return False


def is_adjacent(cell_a: tuple, cell_b: tuple) -> bool:
    return (cell_b[0] - cell_a[0], cell_b[1] - cell_a[1]) in DIRS


def back_rank_counts(size: int, stacks: dict) -> tuple:
    """`(black, white)` — how many PIECES (topmost discs only) each seat has on
    the opponent's back rank."""
    counts = [0, 0]
    for seat in (0, 1):
        target = back_rank(size, 1 - seat)
        counts[seat] = sum(1 for c in target
                           if c in stacks and stacks[c][-1] == seat)
    return tuple(counts)


# --------------------------------------------------------------------------


@dataclass
class OnagerState:
    size: int = 6
    stacks: dict = field(default_factory=dict)      # (q,r) -> tuple bottom->top
    lakes: frozenset = frozenset()
    to_move: int = 0
    winner: Optional[int] = None
    capped: bool = False                            # ply cap reached -> draw
    ply: int = 0                                    # completed plies
    last: tuple = ()                                # cells of the last move


class Onager(Game):
    name = "Onager"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ core

    def initial_state(self, options=None, rng=None) -> OnagerState:
        o = options or {}
        size = int(o.get("size", 6))
        if size not in SIZES:
            raise ValueError(f"unsupported board size {size!r}")
        stacks = {}
        for seat in (0, 1):
            for cell in home_rows(size, seat):
                stacks[cell] = (seat,)
        return OnagerState(size=size, stacks=stacks)

    def current_player(self, s: OnagerState) -> int:
        return s.to_move

    def in_placement(self, s: OnagerState) -> bool:
        return len(s.lakes) < LAKES

    def legal_moves(self, s: OnagerState) -> list:
        if s.winner is not None or s.capped:
            return []
        if self.in_placement(s):
            mid = centre(s.size)
            return [cell_id(c) for c in all_cells(s.size)
                    if c != mid and c not in s.stacks and c not in s.lakes]
        return [f"{cell_id(a)}>{cell_id(b)}"
                for a, b in all_turns(s.size, s.stacks, s.lakes, s.to_move)]

    # -------------------------------------------------------------- applying

    def _relocate(self, s: OnagerState, frm: tuple, to: tuple) -> dict:
        """Apply a turn: the mover's top disc leaves `frm` and lands on `to`.
        This one operation covers a walk, a single jump and a whole jump chain
        alike — see `move_targets`."""
        seat = s.to_move
        size = s.size
        for cell in (frm, to):
            if not on_board(size, cell):
                raise ValueError(f"{cell_id(cell)} is off the board")
        if frm not in s.stacks or s.stacks[frm][-1] != seat:
            raise ValueError(f"no piece of yours on {cell_name(size, frm)}")
        if to not in move_targets(size, s.stacks, s.lakes, frm, seat):
            raise ValueError(f"{cell_name(size, frm)} cannot reach "
                             f"{cell_name(size, to)} this turn")
        work = {c: list(v) for c, v in s.stacks.items()}
        work[frm].pop()
        if not work[frm]:
            del work[frm]
        work.setdefault(to, []).append(seat)
        return {c: tuple(v) for c, v in work.items()}

    def apply_move(self, s: OnagerState, move: str, rng=None) -> OnagerState:
        if s.winner is not None or s.capped:
            raise ValueError("the game is over")
        size = s.size
        seat = s.to_move

        if self.in_placement(s):
            cell = parse_cell(move)
            if not on_board(size, cell):
                raise ValueError(f"{move} is off the board")
            if cell == centre(size):
                raise ValueError("a lake may not be placed on the centre space")
            if cell in s.stacks or cell in s.lakes:
                raise ValueError(f"{cell_name(size, cell)} is not empty")
            new = OnagerState(size=size, stacks=dict(s.stacks),
                              lakes=frozenset(s.lakes | {cell}),
                              to_move=1 - seat, ply=s.ply + 1,
                              last=(cell,))
        else:
            parts = move.split(">")
            if len(parts) != 2:
                raise ValueError(f"{move}: a turn is written 'from>to'")
            frm, to = (parse_cell(p) for p in parts)
            stacks = self._relocate(s, frm, to)
            new = OnagerState(size=size, stacks=stacks, lakes=s.lakes,
                              to_move=1 - seat, ply=s.ply + 1, last=(frm, to))

        self._score(new)
        return new

    def _score(self, s: OnagerState) -> None:
        """Apply the victory condition at the START of `s.to_move`'s turn: the
        back-rank comparison first, then the no-legal-move loss.  The order is
        the sheet's ("If the above condition is not reached AND you can't make a
        legal movement ... you lose"), so a decisive back-rank lead outranks
        being stuck — and it also outranks the ply-cap draw."""
        mine, theirs = back_rank_counts(s.size, s.stacks)
        if s.to_move == 1:
            mine, theirs = theirs, mine
        if mine > theirs:
            s.winner = s.to_move
            return
        if self.in_placement(s):
            return                      # a placement is always available
        if not has_turn(s.size, s.stacks, s.lakes, s.to_move):
            s.winner = 1 - s.to_move
            return
        if s.ply >= ply_cap(s.size):
            s.capped = True

    def is_terminal(self, s: OnagerState) -> bool:
        return s.winner is not None or s.capped

    def returns(self, s: OnagerState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        # The ply-cap backstop.  Onager's only real draw is by agreement, so a
        # capped game is scored as the honest draw it is rather than given a
        # fabricated winner.
        return [0.0, 0.0]

    # ----------------------------------------------------------- (de)serialize

    def serialize(self, s: OnagerState) -> dict:
        return {
            "size": s.size,
            "stacks": {cell_id(c): list(v) for c, v in s.stacks.items()},
            "lakes": [cell_id(c) for c in sorted(s.lakes)],
            "to_move": s.to_move,
            "winner": s.winner,
            "capped": s.capped,
            "ply": s.ply,
            "last": [cell_id(c) for c in s.last],
        }

    def deserialize(self, d: dict) -> OnagerState:
        return OnagerState(
            size=int(d["size"]),
            stacks={parse_cell(k): tuple(int(x) for x in v)
                    for k, v in d["stacks"].items()},
            lakes=frozenset(parse_cell(c) for c in d["lakes"]),
            to_move=int(d["to_move"]),
            winner=None if d["winner"] is None else int(d["winner"]),
            capped=bool(d["capped"]),
            ply=int(d["ply"]),
            last=tuple(parse_cell(c) for c in d["last"]),
        )

    # ------------------------------------------------------------------- UI

    def describe_move(self, s: OnagerState, move: str) -> str:
        """Move-log notation: `f1` for a lake, `f6-f7` for a walk, and carets
        for a jump — `f6^f10`, or `f6^f10^d10` for a chain.  The route shown for
        a chain is a shortest one; every route ending on the same square leaves
        the board in the same position, so the log explains the jump rather than
        replaying a choice the player never had to make."""
        try:
            cells = [parse_cell(p) for p in move.split(">")]
        except Exception:
            return move
        if len(cells) == 1:
            return f"lake {cell_name(s.size, cells[0])}"
        if len(cells) != 2:
            return move
        frm, to = cells
        if is_adjacent(frm, to) and to not in s.stacks and to not in s.lakes:
            return f"{cell_name(s.size, frm)}-{cell_name(s.size, to)}"
        seat = s.stacks[frm][-1] if frm in s.stacks else s.to_move
        route = jump_route(s.size, s.stacks, s.lakes, frm, to, seat)
        if not route:
            route = (frm, to)
        return "^".join(cell_name(s.size, c) for c in route)

    def render(self, s: OnagerState, perspective=None) -> dict:
        size = s.size
        pieces = []
        for cell, stack in sorted(s.stacks.items()):
            p = {"cell": cell_id(cell), "owner": stack[-1]}
            if len(stack) > 1:
                p["stack"] = list(stack)
            pieces.append(p)
        for cell in sorted(s.lakes):
            # A neutral grey disc: `fill`/`stroke` override the seat colour
            # exactly as ZERTZ's unowned marbles do.
            pieces.append({"cell": cell_id(cell), "owner": 2,
                           "fill": "#7f97a6", "stroke": "#3c525f"})

        # The two back ranks are the goal lines, so tint each in its owner's
        # seat colour (dark enough to sit under the board's own contrast rules).
        tints = {}
        for cell in back_rank(size, 0):
            tints[cell_id(cell)] = "#3d2626"
        for cell in back_rank(size, 1):
            tints[cell_id(cell)] = "#26304a"

        black, white = back_rank_counts(size, s.stacks)
        highlights = []
        if s.winner is not None:
            for cell in back_rank(size, 1 - s.winner):
                if cell in s.stacks and s.stacks[cell][-1] == s.winner:
                    highlights.append({"cell": cell_id(cell), "kind": "goal"})
            # WHICH rule ended the game is recorded exactly by `_score`: the
            # back-rank comparison awards the win to the player TO MOVE, the
            # no-legal-move rule to his opponent.  Deriving the reason from
            # `highlights` instead would caption a stuck loss as a back-rank
            # win whenever the winner happens to hold one of the loser's back
            # rank cells without leading on the count.
            if s.winner == s.to_move:
                caption = (f"{SEAT_NAMES[s.winner]} wins — pieces on the "
                           f"opponent's back rank: {SEAT_NAMES[0]} {black}, "
                           f"{SEAT_NAMES[1]} {white}")
            else:
                caption = (f"{SEAT_NAMES[s.winner]} wins — "
                           f"{SEAT_NAMES[1 - s.winner]} has no legal move")
        elif s.capped:
            caption = f"Draw — the {ply_cap(size)}-ply backstop was reached"
        else:
            for cell in s.last:
                highlights.append({"cell": cell_id(cell), "kind": "last-move"})
            who = SEAT_NAMES[s.to_move]
            if self.in_placement(s):
                left = LAKES - len(s.lakes)
                caption = (f"{who} to place a lake — {left} still to come "
                           f"(any empty space except the centre)")
            else:
                caption = (f"{who} to move — walk to an adjacent empty space, "
                           f"or jump over a friendly piece. Pieces on the "
                           f"opponent's back rank: {SEAT_NAMES[0]} {black}, "
                           f"{SEAT_NAMES[1]} {white}")
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": size,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
