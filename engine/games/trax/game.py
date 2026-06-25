"""Trax (David Smith, 1980) -- the loops-and-lines colour-track tile game.

Every Trax tile is a square whose four edges are coloured so that two are WHITE
and two are RED, with a white track joining the two white edges and a red track
joining the two red edges. Up to rotation there are exactly two tile types:

  * the STRAIGHT tile  -- one colour joins a pair of OPPOSITE edges, the other
    joins the other opposite pair (two parallel straight lines); 2 orientations.
  * the CURVED tile    -- one colour joins two ADJACENT edges, the other joins
    the remaining adjacent pair (two corner curves); 4 orientations.

So a placed tile has exactly one of 6 ORIENTATIONS, each fully described by the
colour of each of its four edges (top/right/bottom/left, indices 0/1/2/3) plus
the two track segments (each joining two edge-midpoints in the segment's colour).

Players are WHITE (seat 0) and RED (seat 1); both place the same two-coloured
tiles. WHITE moves first. A player WINS the instant -- after their placement and
all forced moves resolve -- their colour forms a LOOP (a closed same-colour
track) or a winning LINE (a same-colour path spanning >= 8 rows/columns between
two opposite outermost edges of the tiles in play). If one turn completes a win
for BOTH colours, the player who MOVED wins.

Edge / midpoint numbering (matches the renderer's board.tracks contract):
    0 = top, 1 = right, 2 = bottom, 3 = left.
Neighbour across edge p: 0 -> (c, r+1), 1 -> (c+1, r), 2 -> (c, r-1),
3 -> (c-1, r). The opposite edge of a neighbour reached across edge p is
(p + 2) % 4 (a top edge touches the neighbour's bottom edge, etc.).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

W_COL = "W"   # white
R_COL = "R"   # red
WHITE_HEX = "#e8e8e8"
RED_HEX = "#d9534f"

# Hard safety cap. Real games end in a handful of placements; this only guards
# the conformance random-playout from an unbounded growing board.
PLY_CAP = 300
SIZE_CAP = 64        # max bounding-box span (cells) in either direction -> draw
WIN_LINE = 8         # a winning line spans at least this many rows/columns

# neighbour delta per edge index 0=top 1=right 2=bottom 3=left
DELTA = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}


# ---------------------------------------------------------------------------
# The six tile orientations.
#
# Each orientation: (token, edges, white_seg, red_seg) where
#   edges = (e0,e1,e2,e3) colour of top/right/bottom/left,
#   white_seg = the pair of edge indices the white track joins,
#   red_seg   = the pair the red track joins.
# Tokens chosen to be human-legible (used in the =CHOICE move suffix):
#   "|"  straight, white vertical   (white joins top<->bottom)
#   "-"  straight, white horizontal (white joins left<->right)
#   "TL" curved, white joins top+left      (the canonical opening tile)
#   "TR" curved, white joins top+right
#   "BR" curved, white joins bottom+right
#   "BL" curved, white joins bottom+left
# ---------------------------------------------------------------------------
ORIENTATIONS = {
    "|":  (("W", "R", "W", "R"), (0, 2), (1, 3)),
    "-":  (("R", "W", "R", "W"), (1, 3), (0, 2)),
    "TL": (("W", "R", "R", "W"), (0, 3), (1, 2)),
    "TR": (("W", "W", "R", "R"), (0, 1), (2, 3)),
    "BR": (("R", "W", "W", "R"), (1, 2), (0, 3)),
    "BL": (("R", "R", "W", "W"), (2, 3), (0, 1)),
}
ORIENT_TOKENS = list(ORIENTATIONS.keys())

ORIENT_LABELS = {
    "|":  "Straight (white vertical)",
    "-":  "Straight (white horizontal)",
    "TL": "Curve (white top-left)",
    "TR": "Curve (white top-right)",
    "BR": "Curve (white bottom-right)",
    "BL": "Curve (white bottom-left)",
}


def edges_of(token):
    return ORIENTATIONS[token][0]


def segs_of(token):
    """Return {colour: (a, b)} edge-midpoint pairs for the two tracks."""
    _e, wseg, rseg = ORIENTATIONS[token]
    return {W_COL: wseg, R_COL: rseg}


def edge_colour(token, edge):
    return ORIENTATIONS[token][0][edge]


# Map: for a given orientation, which edge does the track of `colour` use that is
# OTHER than `edge`?  (each colour occupies exactly two of the four edges)
def other_edge(token, colour, edge):
    a, b = segs_of(token)[colour]
    if edge == a:
        return b
    if edge == b:
        return a
    return None


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _cid(cell):
    return f"{cell[0]},{cell[1]}"


@dataclass
class TraxState:
    placed: dict = field(default_factory=dict)   # (c,r) -> orientation token
    to_move: int = 0                             # 0 = White, 1 = Red
    ply: int = 0
    winner: object = None                        # None | 0 | 1 | "draw"


class TraxError(Exception):
    """Raised when a forced configuration is illegal (3 same-colour edges)."""


class Trax(Game):
    uid = "trax"
    name = "Trax"

    @property
    def num_players(self):
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        return TraxState(placed={}, to_move=0, ply=0, winner=None)

    def current_player(self, s):
        return s.to_move

    # ---- adjacency / matching -------------------------------------------
    @staticmethod
    def _neighbour(cell, edge):
        dc, dr = DELTA[edge]
        return (cell[0] + dc, cell[1] + dr)

    @staticmethod
    def _required_colour(placed, cell, edge):
        """Colour forced on `cell`'s `edge` by the neighbour across it, or None.

        If the neighbour cell holds a tile, our edge MUST match the colour the
        neighbour shows on its touching edge.
        """
        nb = Trax._neighbour(cell, edge)
        tok = placed.get(nb)
        if tok is None:
            return None
        return edge_colour(tok, (edge + 2) % 4)

    @classmethod
    def _orientation_fits(cls, placed, cell, token):
        """Does `token` on `cell` match every already-placed neighbour edge?"""
        edges = edges_of(token)
        for edge in range(4):
            req = cls._required_colour(placed, cell, edge)
            if req is not None and req != edges[edge]:
                return False
        return True

    @classmethod
    def _legal_orientations(cls, placed, cell):
        """All orientation tokens that may be legally placed on empty `cell`."""
        if not placed:
            # First tile of the game: the canonical opening tile only (by board
            # symmetry every opening is equivalent; "TL" is the standard one).
            return ["TL"]
        # cell must touch at least one placed tile to be playable
        if not any(placed.get(cls._neighbour(cell, e)) is not None for e in range(4)):
            return []
        return [t for t in ORIENT_TOKENS if cls._orientation_fits(placed, cell, token=t)]

    # ---- forced-move resolution -----------------------------------------
    @classmethod
    def _empty_neighbours(cls, placed, cell):
        out = []
        for e in range(4):
            nb = cls._neighbour(cell, e)
            if placed.get(nb) is None:
                out.append(nb)
        return out

    @classmethod
    def _forced_token(cls, placed, cell):
        """If `cell` (empty, on the frontier) is FORCED, return its unique token.

        A cell is forced when two or more of its edges are constrained by placed
        neighbours to the SAME colour: that colour's track must join those edges,
        which determines the whole tile. Returns:
          * None              -- not forced (0 or 1 constrained edges, or the two
                                  constraints are different colours and a tile is
                                  not yet mandatory),
          * a token string    -- the forced orientation,
        and raises TraxError if the constraints are unsatisfiable (>=3 edges of
        one colour, or two same-colour edges that no single tile can join while
        also satisfying the rest).
        """
        req = {}
        for e in range(4):
            c = cls._required_colour(placed, cell, e)
            if c is not None:
                req[e] = c
        if not req:
            return None
        # count per colour
        whites = [e for e, c in req.items() if c == W_COL]
        reds = [e for e, c in req.items() if c == R_COL]
        if len(whites) >= 3 or len(reds) >= 3:
            raise TraxError(f"illegal: 3+ same-colour edges forced at {cell}")
        # A tile is MANDATORY exactly when some colour is forced on >=2 edges.
        if len(whites) < 2 and len(reds) < 2:
            return None
        # Find the unique orientation matching every constraint in req.
        matches = [t for t in ORIENT_TOKENS
                   if all(edge_colour(t, e) == c for e, c in req.items())]
        if len(matches) != 1:
            # 0 -> unsatisfiable; >1 would mean req underdetermines (can't happen
            # once a colour is doubled, since the doubled pair + 2 R/2 W fixes it).
            raise TraxError(f"no unique forced tile at {cell}: req={req}")
        return matches[0]

    @classmethod
    def _resolve_forced(cls, placed):
        """Place all mandatory tiles to a fixed point (mutates a COPY).

        Returns the new placed dict. Raises TraxError on an illegal forced
        configuration (which makes the originating move illegal).
        """
        placed = dict(placed)
        # frontier = empty cells adjacent to >=1 placed tile; re-scan after each
        # placement because a new tile can create / change forced cells.
        changed = True
        while changed:
            changed = False
            frontier = set()
            for cell in placed:
                for e in range(4):
                    nb = cls._neighbour(cell, e)
                    if placed.get(nb) is None:
                        frontier.add(nb)
            for cell in frontier:
                tok = cls._forced_token(placed, cell)
                if tok is not None:
                    placed[cell] = tok
                    changed = True
                    break  # restart the scan (sizes stay tiny)
        return placed

    # ---- win detection ---------------------------------------------------
    @classmethod
    def _colour_won(cls, placed, colour):
        """Return 'loop' | 'line' | None for `colour` over the board `placed`.

        Track connectivity: within a tile the `colour` track joins two edge
        endpoints; across a shared edge two tiles' endpoints connect. Model the
        graph whose NODES are (cell, edge) endpoints carrying `colour`, with:
          * an intra-tile edge between a tile's two same-colour endpoints,
          * an inter-tile edge between (cell, edge) and (neighbour, oppedge) when
            both tiles exist and both show `colour` on that shared edge.
        A LOOP exists iff a colour endpoint can return to itself (a cycle through
        a tile). A LINE wins iff a connected colour component touches two opposite
        outermost edges of the bounding box spanning >= WIN_LINE.
        """
        if not placed:
            return None
        # Build adjacency over endpoints (cell, edge) that carry `colour`.
        # endpoints list
        adj = {}

        def add(a, b):
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)

        for cell, tok in placed.items():
            a, b = segs_of(tok)[colour]
            na, nb = (cell, a), (cell, b)
            # intra-tile connection
            add(na, nb)
            # inter-tile: each endpoint links to the neighbour's opposite edge IF
            # that neighbour exists and shows `colour` there.
            for endpoint in (a, b):
                nbcell = cls._neighbour(cell, endpoint)
                ntok = placed.get(nbcell)
                if ntok is None:
                    continue
                opp = (endpoint + 2) % 4
                if edge_colour(ntok, opp) == colour:
                    add((cell, endpoint), (nbcell, opp))

        # ---- loop detection: a cycle in this graph that uses an intra-tile edge.
        # Simpler & exact for Trax: a loop exists iff following the track returns
        # to the start. Walk each tile's track as a path of alternating intra/inter
        # steps; if the walk returns to its start endpoint, it's a loop.
        if cls._has_loop(placed, colour):
            return "loop"

        # ---- line detection over connected components ----------------------
        cols = [c for (c, _r) in placed]
        rows = [r for (_c, r) in placed]
        minc, maxc, minr, maxr = min(cols), max(cols), min(rows), max(rows)
        span_w = maxc - minc + 1
        span_h = maxr - minr + 1
        comps = cls._components(adj)
        for comp in comps:
            ccols = {cell[0] for (cell, _e) in comp}
            crows = {cell[1] for (cell, _e) in comp}
            # horizontal line: component reaches both the leftmost & rightmost
            # occupied columns, and the board spans >= WIN_LINE columns.
            if span_w >= WIN_LINE and minc in ccols and maxc in ccols:
                return "line"
            if span_h >= WIN_LINE and minr in crows and maxr in crows:
                return "line"
        return None

    @classmethod
    def _has_loop(cls, placed, colour):
        """True iff `colour` forms a closed loop.

        Walk the track as a sequence of tiles: from a starting tile, enter at one
        edge, cross to the tile's other same-colour edge, step to the neighbour,
        and continue. A loop = the walk returns to the starting (cell, edge,
        direction) having traversed only existing tiles. We detect a loop as a
        cycle in the tile-crossing graph: nodes are directed (cell, entry_edge);
        a loop returns to a visited node forming a cycle that came back to start.
        """
        # Directed walk: state = (cell, entry_edge). Step: exit = other_edge,
        # neighbour across exit, entering at opposite edge. If neighbour missing,
        # the track is open (dead end) -> not part of a loop in this direction.
        for start_cell, tok in placed.items():
            a, b = segs_of(tok)[colour]
            for entry in (a, b):
                cell = start_cell
                ent = entry
                visited = set()
                while True:
                    state = (cell, ent)
                    if state in visited:
                        # returned to a previously seen directed endpoint -> cycle
                        if state == (start_cell, entry):
                            return True
                        break
                    visited.add(state)
                    t = placed.get(cell)
                    if t is None:
                        break
                    exit_edge = other_edge(t, colour, ent)
                    nb = cls._neighbour(cell, exit_edge)
                    ntok = placed.get(nb)
                    if ntok is None:
                        break  # open end
                    cell = nb
                    ent = (exit_edge + 2) % 4
                    if cell == start_cell and ent == entry:
                        return True
        return False

    @staticmethod
    def _components(adj):
        seen = set()
        comps = []
        for node in adj:
            if node in seen:
                continue
            stack = [node]
            comp = set()
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                comp.add(n)
                stack.extend(adj.get(n, ()))
            comps.append(comp)
        return comps

    # ---- move generation -------------------------------------------------
    def _frontier_cells(self, placed):
        if not placed:
            return [(0, 0)]
        out = set()
        for cell in placed:
            for e in range(4):
                nb = self._neighbour(cell, e)
                if placed.get(nb) is None:
                    out.add(nb)
        return sorted(out)

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        if not s.placed:
            return [f"0,0={t}" for t in self._legal_orientations({}, (0, 0))]
        moves = []
        for cell in self._frontier_cells(s.placed):
            for tok in self._legal_orientations(s.placed, cell):
                # the placement must lead to a LEGAL forced resolution; an
                # orientation that forces an illegal (3-edge) configuration is
                # itself illegal and is filtered out here.
                trial = dict(s.placed)
                trial[cell] = tok
                try:
                    self._resolve_forced(trial)
                except TraxError:
                    continue
                moves.append(f"{_cid(cell)}={tok}")
        return moves

    # ---- apply -----------------------------------------------------------
    def apply_move(self, s, move, rng=None):
        cid, tok = move.split("=")
        cell = _cell(cid)
        placed = dict(s.placed)
        placed[cell] = tok
        placed = self._resolve_forced(placed)   # may raise TraxError (illegal move)

        seat = s.to_move
        # Determine win. The mover is `seat` (0 White / 1 Red); seat 0 owns white,
        # seat 1 owns red. Check both colours; the MOVER wins ties.
        mover_colour = W_COL if seat == 0 else R_COL
        opp_colour = R_COL if seat == 0 else W_COL
        mover_win = self._colour_won(placed, mover_colour)
        opp_win = self._colour_won(placed, opp_colour)

        winner = None
        if mover_win:
            winner = seat               # mover wins ties (simultaneous rule)
        elif opp_win:
            winner = 1 - seat

        ply = s.ply + 1
        if winner is None:
            # termination guards (a real game never reaches these)
            cols = [c for (c, _r) in placed]
            rows = [r for (_c, r) in placed]
            span = max(max(cols) - min(cols), max(rows) - min(rows)) + 1
            if ply >= PLY_CAP or span >= SIZE_CAP:
                winner = "draw"

        return TraxState(placed=placed, to_move=1 - seat, ply=ply, winner=winner)

    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None or s.winner == "draw":
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # ---- serialize -------------------------------------------------------
    def serialize(self, s):
        return {
            "placed": {_cid(cell): tok for cell, tok in s.placed.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d):
        placed = {_cell(k): v for k, v in d["placed"].items()}
        return TraxState(placed=placed, to_move=d["to_move"],
                         ply=d.get("ply", 0), winner=d.get("winner"))

    # ---- move log --------------------------------------------------------
    def describe_move(self, s, move):
        cid, tok = move.split("=")
        who = "White" if s.to_move == 0 else "Red"
        return f"{who} {ORIENT_LABELS[tok]} @ {cid}"

    # ---- render ----------------------------------------------------------
    def render(self, s, perspective=None):
        placed = s.placed
        # bounding box of placed cells, +1 margin so adjacent legal cells exist
        if placed:
            cols = [c for (c, _r) in placed]
            rows = [r for (_c, r) in placed]
            minc, maxc = min(cols) - 1, max(cols) + 1
            minr, maxr = min(rows) - 1, max(rows) + 1
        else:
            minc, maxc, minr, maxr = -1, 1, -1, 1

        width = maxc - minc + 1
        height = maxr - minr + 1

        # The renderer's square board uses cell ids "col,row" with col,row >= 0.
        # Shift everything by (-minc, -minr) so ids are non-negative, and keep the
        # shift only for display (moves still use absolute ids? -> NO: we must map
        # both ways). To keep click-to-move correct we render in SHIFTED ids and
        # the frontend sends back shifted ids; but apply_move expects absolute.
        # Simplest robust choice: DON'T shift -- use board.extent so negative
        # coordinates are fine, and emit cells/ids in absolute (c,r) space using a
        # polygons-free square board whose ids are the true ids.
        #
        # The square renderer derives cells from width/height starting at 0, so we
        # cannot use negative ids there. Instead emit a "polygons" board is heavy;
        # simpler: shift to non-negative and translate moves. We translate in
        # parse via a stored origin? Moves are stateless strings. To avoid a
        # translation layer we keep the board NON-shifted by emitting a square
        # board sized to (maxc+1) x (maxr+1) covering absolute ids 0..max, with a
        # left/bottom margin of empty cells. That wastes cells when min<0, so we
        # KEEP origin at 0 by only ever growing in +c/+r from the first tile at
        # (0,0)? Tiles can grow negative. Therefore: emit polygons cells with
        # absolute ids.
        cells = []
        for c in range(minc, maxc + 1):
            for r in range(minr, maxr + 1):
                cells.append({"id": f"{c},{r}",
                              "points": _square_points(c, r, minc, minr, height)})

        tracks = {}
        for cell, tok in placed.items():
            segs = segs_of(tok)
            tracks[_cid(cell)] = [
                [segs[W_COL][0], segs[W_COL][1], WHITE_HEX],
                [segs[R_COL][0], segs[R_COL][1], RED_HEX],
            ]

        board = {
            "type": "polygons",
            "cells": cells,
            "tracks": tracks,
        }

        names = {0: "White", 1: "Red"}
        if s.winner == "draw":
            cap = "Draw (move/size cap reached)"
        elif s.winner is not None:
            cap = f"{names[s.winner]} wins!"
        else:
            cap = f"{names[s.to_move]} to move: place a tile"

        # =CHOICE picker metadata
        choice_names = {t: ORIENT_LABELS[t] for t in ORIENT_TOKENS}

        return {
            "board": board,
            "pieces": [],
            "highlights": [],
            "caption": cap,
            "choiceTitle": "Place a tile",
            "choiceNames": choice_names,
        }


def _square_points(c, r, minc, minr, height):
    """Vertices of cell (c,r) as a unit square, row 0 (minr) drawn at the bottom.

    x grows right with col; y grows DOWN in SVG, so a larger row is drawn higher
    (matches the square renderer's `height-1-r` convention, applied to the
    shifted coordinate).
    """
    x = c - minc
    # invert row so larger r is higher on screen
    y = (height - 1) - (r - minr)
    return [[x, y], [x + 1, y], [x + 1, y + 1], [x, y + 1]]
