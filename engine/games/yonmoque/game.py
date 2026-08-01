"""Yonmoque (Mitsuo Yamamoto, Logy Games, 1997) -- 5x5, place-or-move, flip,
win with FOUR in a row but LOSE with five.

Rules as implemented follow the publisher's own page,
http://www.logygames.com/english/yonmoque.html ("Complete Rules"), cross-checked
against the older (2016) revision of the same page archived at
web.archive.org/web/20160112123056/http://www.logygames.com/english/yonmoque.html
which states several clauses more explicitly.  See rules.md for the full writeup
and for every interpretive decision.

Board -- 25 squares, each square coloured for one of the two players or NEUTRAL.
The publisher states the census as "8 blue, 12 white and only 5 neutral spaces"
and the 2016 sheet locates the neutrals: "The half white and half blue squares,
at the center and on the corners, are neutral".  Those two facts determine the
whole map, given that a colour has to form diagonal *chains* (a slide is a
bishop move):  diagonal steps preserve the parity of ``c+r``, the 13 even cells
are the centre + 4 corners (neutral) + the 8 cells at Manhattan distance 2 from
the centre, and the 12 odd cells are the rest.  So

    tile(c,r) = NEUTRAL       if |c-2|+|r-2| in (0, 4)     -> 5 cells
              = first player   if |c-2|+|r-2| == 2         -> 8 cells
              = second player  otherwise (distance 1 or 3) -> 12 cells

which is exactly the board photographed and drawn on the publisher's page.  The
map is invariant under the full dihedral group of the square, so the package's
choice of orientation is not observable.

Seats -- seat 0 is the FIRST player (the physical game's *blue*; drawn red by
the platform palette), seat 1 the second (the physical game's *white*; drawn
blue).  Seat 0's tiles are the 8; seat 1's are the 12.  That asymmetry is the
game: the second player's pieces slide over a much larger network, and the first
move is the compensation.

Turn -- place one piece from your hand on any empty square, OR move one of your
pieces already on the board.  Both are available while you still hold pieces.

Move -- one king step to an empty square, or (only if the square you stand on is
YOUR colour) any distance in a straight DIAGONAL line over empty squares of your
own colour.

Flip -- a MOVE (never a placement) that sandwiches a solid line of enemy pieces
between the arriving piece and another of your pieces, in any of the eight
directions, flips every piece of that line to your colour.  Mandatory, all or
nothing.

Result -- creating four in a row *with a move* wins; creating five in a row (by
moving OR placing) loses; being unable to place or move loses.  Four in a row
made by a PLACEMENT is not a win and the game simply continues.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 5
PIECES_PER_PLAYER = 6
CENTRE = SIZE // 2

COORDS = [(c, r) for r in range(SIZE) for c in range(SIZE)]
CELLS = [f"{c},{r}" for (c, r) in COORDS]

NEUTRAL = None


def tile_owner(c, r):
    """Which seat's colour is the square (c,r)?  ``None`` = neutral.

    Derived, not tabulated: see the module docstring.  Manhattan distance 0 (the
    centre) and 4 (the four corners) are the five neutral squares; distance 2 is
    the eight squares of the first player's colour; distances 1 and 3 are the
    twelve of the second player's.
    """
    d = abs(c - CENTRE) + abs(r - CENTRE)
    if d == 0 or d == 2 * CENTRE:
        return NEUTRAL
    return 0 if d % 2 == 0 else 1


TILE = {f"{c},{r}": tile_owner(c, r) for (c, r) in COORDS}

# Eight king-step directions, and the four diagonals used by the long slide.
KING_DIRS = [(-1, -1), (0, -1), (1, -1),
             (-1, 0), (1, 0),
             (-1, 1), (0, 1), (1, 1)]
DIAG_DIRS = [(-1, -1), (1, -1), (-1, 1), (1, 1)]


def _in_bounds(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE


def _runs(length):
    """Every straight run of `length` consecutive cells, in all four line
    directions.  Returned as a list of tuples of cell ids."""
    out = []
    for dc, dr in [(1, 0), (0, 1), (1, 1), (1, -1)]:
        for (c, r) in COORDS:
            cells = []
            for k in range(length):
                nc, nr = c + dc * k, r + dr * k
                if not _in_bounds(nc, nr):
                    break
                cells.append(f"{nc},{nr}")
            if len(cells) == length:
                out.append(tuple(cells))
    return out


RUNS4 = _runs(4)   # 28 of them
RUNS5 = _runs(5)   # 12 of them

# For each cell, the runs that contain it (win check only ever needs these).
RUNS4_BY_CELL = {cell: tuple(run for run in RUNS4 if cell in run) for cell in CELLS}

ADJ = {}
RAYS = {}
for (_c, _r) in COORDS:
    _id = f"{_c},{_r}"
    ADJ[_id] = tuple(f"{_c + dc},{_r + dr}" for dc, dr in KING_DIRS
                     if _in_bounds(_c + dc, _r + dr))
    # RAYS[cell][dir] = the cells outward from `cell` in that direction.
    RAYS[_id] = {}
    for _d in KING_DIRS:
        _ray = []
        _nc, _nr = _c + _d[0], _r + _d[1]
        while _in_bounds(_nc, _nr):
            _ray.append(f"{_nc},{_nr}")
            _nc += _d[0]
            _nr += _d[1]
        RAYS[_id][_d] = tuple(_ray)


@dataclass
class YState:
    pos: dict = field(default_factory=dict)                     # cell -> seat
    to_move: int = 0
    hands: list = field(default_factory=lambda: [PIECES_PER_PLAYER,
                                                 PIECES_PER_PLAYER])
    ply: int = 0
    winner: object = None            # set inside apply_move ("win as event")
    reason: object = None            # "four" / "five" / "stuck"
    last: list = field(default_factory=list)      # cells touched by the last move
    flipped: list = field(default_factory=list)   # cells flipped by the last move


class Yonmoque(Game):
    name = "Yonmoque"

    PIECES_PER_PLAYER = PIECES_PER_PLAYER

    # --- termination -------------------------------------------------------
    # The published rules contain NO draw, repetition or move-count rule: "Play
    # continues until either a player has won (4 in a row), or a player has lost
    # (5 in a row)" (2016 sheet).  With every piece on the board and no forced
    # progress the position can repeat forever, so this package imposes a
    # practical backstop and calls the result an honest DRAW.  The bound is
    # built from the game's own named quantities: the at most
    # 2*PIECES_PER_PLAYER placement plies, plus a movement allowance of
    # MOVE_ALLOWANCE plies.  See rules.md for the measurement of how often it
    # actually fires.
    MOVE_ALLOWANCE = 400
    PLY_CAP = 2 * PIECES_PER_PLAYER + MOVE_ALLOWANCE

    # No `heuristic` is shipped, and that is a measured decision rather than an
    # omission.  Games are short (60,000 random games averaged 28 plies, longest
    # 125), so MCTSBot's 50-ply rollout cutoff fires on only 2.6% of rollouts --
    # a positional eval is consulted almost never.  Measured head to head
    # through MCTSBot (iterations=200, 40 games, seats alternated): a material
    # eval scored 0.525 and a material+open-threes eval scored 0.500 against no
    # heuristic at all, both inside one standard error (0.079) of 0.5.

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return YState()

    def current_player(self, state):
        return state.to_move

    # --- helpers -----------------------------------------------------------
    def _gen(self, pos, pl, hand):
        """Legal moves from raw components (no terminal test)."""
        out = []
        if hand > 0:
            out.extend(c for c in CELLS if c not in pos)
        for cell, v in pos.items():
            if v != pl:
                continue
            # (a) one king step to an empty square, whatever colour it is
            for q in ADJ[cell]:
                if q not in pos:
                    out.append(f"{cell}>{q}")
            # (b) a bishop slide, but only from a square of your own colour and
            #     only over squares of your own colour.  Distance 1 duplicates a
            #     king step, so start at the second square of the ray.
            if TILE[cell] != pl:
                continue
            for d in DIAG_DIRS:
                for i, q in enumerate(RAYS[cell][d]):
                    if q in pos or TILE[q] != pl:
                        break
                    if i > 0:
                        out.append(f"{cell}>{q}")
        return out

    def _has_run(self, pos, pl, runs):
        for run in runs:
            if all(pos.get(x) == pl for x in run):
                return True
        return False

    def _new_four(self, pos, pl, newly):
        """A four-in-a-row of `pl` that CONTAINS a square which only became
        `pl`'s this turn -- i.e. a four-in-a-row that did not exist before the
        move.  (Every newly created four must contain such a square, and no
        pre-existing four can, since those squares were empty or enemy-held.)"""
        for cell in newly:
            for run in RUNS4_BY_CELL[cell]:
                if all(pos.get(x) == pl for x in run):
                    return True
        return False

    def _flip_from(self, pos, to, pl):
        """Custodian capture out of `to` in all eight directions."""
        flipped = []
        for d in KING_DIRS:
            run = []
            for q in RAYS[to][d]:
                v = pos.get(q)
                if v is None:            # a gap breaks the sandwich
                    run = []
                    break
                if v == pl:              # closed by a friendly piece
                    break
                run.append(q)
            else:
                run = []                 # ran off the board: no sandwich
            flipped.extend(run)
        return flipped

    def _draw(self, state):
        return state.winner is None and state.ply >= self.PLY_CAP

    # --- interface ---------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        return self._gen(state.pos, state.to_move, state.hands[state.to_move])

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        pos = dict(state.pos)
        hands = list(state.hands)
        flipped = []

        if ">" in move:
            frm, to = move.split(">")
            del pos[frm]
            pos[to] = pl
            flipped = self._flip_from(pos, to, pl)
            for q in flipped:
                pos[q] = pl
            newly = [to] + flipped
            last = [frm, to]
            moved = True
        else:
            pos[move] = pl
            hands[pl] -= 1
            newly = [move]
            last = [move]
            moved = False

        winner = None
        reason = None
        # Five in a row is a loss for whoever made it -- by MOVING **or**
        # PLACING -- and it outranks the four-in-a-row win.
        if self._has_run(pos, pl, RUNS5):
            winner = 1 - pl
            reason = "five"
        # Four in a row wins, but only when created by a MOVE.
        elif moved and self._new_four(pos, pl, newly):
            winner = pl
            reason = "four"

        ns = YState(pos=pos, to_move=1 - pl, hands=hands, ply=state.ply + 1,
                    winner=winner, reason=reason, last=last, flipped=flipped)

        # "Players must either place or move a piece; if they cannot, they
        # lose."  Checked BEFORE the ply cap, so a decisive result always
        # outranks the draw counter.
        if winner is None and not self._gen(pos, ns.to_move, hands[ns.to_move]):
            ns.winner = pl
            ns.reason = "stuck"
        return ns

    def is_terminal(self, state):
        return state.winner is not None or state.ply >= self.PLY_CAP

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # --- serialization -----------------------------------------------------
    def serialize(self, state):
        return {
            "pos": dict(state.pos),
            "to_move": state.to_move,
            "hands": list(state.hands),
            "ply": state.ply,
            "winner": state.winner,
            "reason": state.reason,
            "last": list(state.last),
            "flipped": list(state.flipped),
        }

    def deserialize(self, d):
        return YState(pos=dict(d["pos"]), to_move=d["to_move"],
                      hands=list(d["hands"]), ply=d["ply"],
                      winner=d["winner"], reason=d["reason"],
                      last=list(d["last"]), flipped=list(d["flipped"]))

    # --- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        pl = state.to_move
        if ">" not in move:
            note = ""
            pos = dict(state.pos)
            pos[move] = pl
            if self._has_run(pos, pl, RUNS5):
                note = " !5"
            return f"@{move}{note}"
        frm, to = move.split(">")
        pos = dict(state.pos)
        del pos[frm]
        pos[to] = pl
        flipped = self._flip_from(pos, to, pl)
        for q in flipped:
            pos[q] = pl
        note = f" x{len(flipped)}" if flipped else ""
        if self._has_run(pos, pl, RUNS5):
            note += " !5"
        elif self._new_four(pos, pl, [to] + flipped):
            note += " #4"
        return f"{frm}-{to}{note}"

    # Wash of each seat's colour for that seat's squares, and a warm grey for
    # the five neutrals.  A piece slides only over its OWN tint.
    TILE_TINT = {0: "#f2cccc", 1: "#ccd8f2", NEUTRAL: "#ded9d0"}

    def render(self, state, perspective=None):
        names = {0: "Red", 1: "Blue"}
        pieces = [{"cell": c, "owner": v} for c, v in state.pos.items()]
        highlights = [{"cell": c, "kind": "last-move"} for c in state.last]
        highlights.extend({"cell": c, "kind": "last-move"} for c in state.flipped)
        if state.winner is not None:
            why = {"four": "four in a row",
                   "five": f"{names[1 - state.winner]} made five in a row",
                   "stuck": f"{names[1 - state.winner]} had no move"}
            cap = f"{names[state.winner]} wins - {why.get(state.reason, '')}"
        elif self._draw(state):
            cap = f"Draw - move limit ({self.PLY_CAP} plies) reached"
        else:
            cap = (f"{names[state.to_move]} to play "
                   f"(in hand: Red {state.hands[0]}, Blue {state.hands[1]})")
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE,
                      "tints": {c: self.TILE_TINT[TILE[c]] for c in CELLS}},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
