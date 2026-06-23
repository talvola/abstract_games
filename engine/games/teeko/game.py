"""Teeko (John Scarne, 1937) -- a two-phase placement/movement game on 5x5.

Two players, FOUR markers each.

* PHASE 1 (drop): players alternate placing one marker on any empty cell until
  each has placed all four (eight drops total).
* PHASE 2 (move): on your turn slide ONE of your markers to an ADJACENT empty
  cell. Adjacency is the eight surrounding cells (orthogonal + diagonal), i.e. a
  chess king's step.

A player WINS the instant their four markers form ONE of:
  (a) four-in-a-row -- four consecutive cells in a straight line (horizontal,
      vertical, or either diagonal direction), OR
  (b) a 2x2 square block of four cells.
The win is checked after every drop and after every slide and attributed to the
player who just moved. There are NO captures.

This is the BASE Teeko ruleset; "advanced Teeko" (the jumping / extra rules
Scarne later promoted) is deliberately NOT implemented -- see rules.md.

Because the movement phase could otherwise repeat forever, a no-progress draw is
declared after a hard cap of movement plies with no win.

Cells are addressed by their grid coordinate ``"c,r"`` on a 0..4 layout and the
plain 5x5 board is drawn by the generic ``square`` renderer; markers are stones.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 5
MARKERS = 4  # markers per player

COORDS = [(c, r) for r in range(SIZE) for c in range(SIZE)]
CELLS = [f"{c},{r}" for (c, r) in COORDS]


def _in_bounds(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE


# Eight king-step directions for movement adjacency.
KING_DIRS = [(-1, -1), (0, -1), (1, -1),
             (-1, 0), (1, 0),
             (-1, 1), (0, 1), (1, 1)]


def _adjacency():
    adj = {}
    for (c, r) in COORDS:
        nbrs = set()
        for dc, dr in KING_DIRS:
            nc, nr = c + dc, r + dr
            if _in_bounds(nc, nr):
                nbrs.add(f"{nc},{nr}")
        adj[f"{c},{r}"] = frozenset(nbrs)
    return adj


ADJ = _adjacency()


def _win_shapes():
    """All winning four-cell shapes: lines of four + 2x2 squares.

    Each shape is a frozenset of four cell ids. Returned as a list.
    """
    shapes = []
    # Four-in-a-row in the four line directions. Generate from each anchor cell
    # in the +direction only (the - direction is the same set from another
    # anchor), de-duplicated by the frozenset.
    line_dirs = [(1, 0), (0, 1), (1, 1), (1, -1)]
    seen = set()
    for (c, r) in COORDS:
        for dc, dr in line_dirs:
            cells = []
            ok = True
            for k in range(4):
                nc, nr = c + dc * k, r + dr * k
                if not _in_bounds(nc, nr):
                    ok = False
                    break
                cells.append(f"{nc},{nr}")
            if ok:
                fs = frozenset(cells)
                if fs not in seen:
                    seen.add(fs)
                    shapes.append(fs)
    # 2x2 squares: top-left corner at (c,r) for c,r in 0..3.
    for r in range(SIZE - 1):
        for c in range(SIZE - 1):
            fs = frozenset({
                f"{c},{r}", f"{c + 1},{r}",
                f"{c},{r + 1}", f"{c + 1},{r + 1}",
            })
            if fs not in seen:
                seen.add(fs)
                shapes.append(fs)
    return shapes


WIN_SHAPES = _win_shapes()


@dataclass
class TState:
    pos: dict = field(default_factory=dict)            # cell -> player
    to_move: int = 0
    placed: list = field(default_factory=lambda: [0, 0])   # markers placed/player
    move_plies: int = 0                                 # movement-phase plies so far
    winner: object = None                               # set when someone wins


class Teeko(Game):
    uid = "teeko"
    name = "Teeko"
    MARKERS = MARKERS
    # Hard cap of movement plies with no win -> draw (no-progress / termination
    # guarantee). 80 movement plies (40 full moves) is far beyond any sensible
    # game with 4 markers a side on 25 cells.
    DRAW_MOVE_PLIES = 80

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return TState()

    def current_player(self, state):
        return state.to_move

    # ---- helpers -----------------------------------------------------------
    def _phase_placing(self, state, pl):
        return state.placed[pl] < self.MARKERS

    def _both_placed(self, state):
        return (state.placed[0] >= self.MARKERS
                and state.placed[1] >= self.MARKERS)

    def _own_cells(self, pos, pl):
        return frozenset(c for c, v in pos.items() if v == pl)

    def _is_win(self, pos, pl):
        """True iff player pl's markers exactly cover a winning shape.

        A win shape is four cells. The player has exactly four markers, so a win
        is precisely: the set of the player's four occupied cells IS one of the
        winning shapes (a straight line of four or a 2x2 square).
        """
        own = self._own_cells(pos, pl)
        if len(own) != MARKERS:
            return False
        return own in _WIN_SHAPE_SET

    def _draw(self, state):
        return state.winner is None and state.move_plies >= self.DRAW_MOVE_PLIES

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        pl = state.to_move
        if self._phase_placing(state, pl):
            return [c for c in CELLS if c not in state.pos]
        # movement phase: slide a marker to an adjacent empty cell
        out = []
        for c, v in state.pos.items():
            if v != pl:
                continue
            for q in ADJ[c]:
                if q not in state.pos:
                    out.append(f"{c}>{q}")
        return out

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        pos = dict(state.pos)
        placed = list(state.placed)
        move_plies = state.move_plies

        if ">" in move:                              # movement
            frm, to = move.split(">")
            pos[to] = pos.pop(frm)
            move_plies += 1
        else:                                        # placement
            pos[move] = pl
            placed[pl] += 1

        winner = pl if self._is_win(pos, pl) else None
        ns = TState(pos=pos, to_move=1 - pl, placed=placed,
                    move_plies=move_plies, winner=winner)
        return ns

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialize ---------------------------------------------------------
    def serialize(self, state):
        return {
            "pos": {c: v for c, v in state.pos.items()},
            "to_move": state.to_move,
            "placed": list(state.placed),
            "move_plies": state.move_plies,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return TState(pos=dict(d["pos"]), to_move=d["to_move"],
                      placed=list(d["placed"]),
                      move_plies=d.get("move_plies", 0),
                      winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if ">" in move:
            return move.replace(">", "-")
        return f"@{move}"

    def render(self, state, perspective=None):
        pieces = [{"cell": c, "owner": v} for c, v in state.pos.items()]
        names = {0: "Red", 1: "Blue"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        elif self._phase_placing(state, state.to_move):
            left = self.MARKERS - state.placed[state.to_move]
            cap = f"{names[state.to_move]} to drop ({left} in hand)"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }


# Module-level set of winning shapes for fast membership tests.
_WIN_SHAPE_SET = set(WIN_SHAPES)
