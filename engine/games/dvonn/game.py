"""DVONN (Kris Burm, 2001 -- the third GIPF project game) -- a STACKING game on
a 49-field elongated-hexagon board.

Board: 49 hexagonal fields, "five hexes wide, nine on the edges, eleven in the
centre". We model this as 5 rows (axial coordinate r = 0..4) whose lengths are
9, 10, 11, 10, 9 = 49, laid out as an elongated hexagon with the standard six
hex neighbours. Cells are axial "q,r".

Two phases:
  * PLACEMENT -- starting from an empty board the players alternately drop single
    pieces, one per field, until all 49 fields hold a height-1 stack. The three
    neutral red DVONN pieces are placed first (alternating placer, board-owner
    convention), then the two players alternately place their 23 pieces each
    (White first). A single piece is a stack of height 1.
  * MOVEMENT -- on your turn you move a stack you control (your colour on top) in
    a straight line along one of the SIX hex directions, a distance EXACTLY equal
    to the stack's height, and it must land squarely on top of another OCCUPIED
    field (you may jump over empty/occupied fields in between but may never land
    on an empty field). A stack whose every in-range landing along all six
    directions is empty/off-board cannot move; a stack ringed by six occupied
    neighbours of height 1 is in particular immobile.

DVONN rule: a red DVONN piece anchors the board. Immediately after each move,
every stack no longer joined -- through a chain of edge-adjacent stacks -- to at
least one stack that contains a DVONN piece is REMOVED from play (pieces are
never returned).

End / scoring: when neither player has a legal move the game ends; each player
scores the total number of pieces in the stacks they control (the top piece is
theirs). Most pieces wins; equal is a draw. (If only one player is stuck they
simply pass; play continues for the other until they too are stuck.)

This reuses Lasca's `piece.stack` tower model: a piece carries `stack` = the list
of owners bottom->top; the renderer draws layered owner-coloured discs with a
height badge. Owner 2 is the neutral DVONN/red piece colour.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK, DVONN = 0, 1, 2          # owner codes (2 = neutral red DVONN piece)
N_DVONN = 3
N_EACH = 23                            # pieces per player

# Six axial hex directions (q, r).
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

# --- board geometry: 5 rows of length 9,10,11,10,9 = 49, an elongated hexagon.
ROW_LEN = [9, 10, 11, 10, 9]


def _build_board():
    """Return the ordered list of axial (q, r) cells of the DVONN board.

    Row r spans q in [qmin(r), qmin(r)+ROW_LEN[r]-1]. We slide successive rows so
    the figure is an elongated hexagon: the widest row (r=2, 11 cells) is the
    reference; rows above/below taper symmetrically. With axial neighbours
    (q,r)+DIR this yields the standard DVONN adjacency (interior = 6 neighbours,
    edges = 4, corners = 3)."""
    cells = []
    # qmin chosen so adjacency is the canonical elongated hexagon:
    #   6 corners (deg 3), 18 edge fields (deg 4), 25 interior (deg 6).
    # r:0 len9, r:1 len10, r:2 len11, r:3 len10, r:4 len9
    qmin = {0: 1, 1: 0, 2: -1, 3: -1, 4: -1}
    for r in range(5):
        for i in range(ROW_LEN[r]):
            q = qmin[r] + i
            cells.append((q, r))
    return cells


CELLS = _build_board()
CELLSET = set(CELLS)


def _cell(s):
    q, r = s.split(",")
    return int(q), int(r)


def _key(q, r):
    return f"{q},{r}"


# A stack is a tuple of owners bottom->top (e.g. (WHITE, DVONN, BLACK)).
def _top(stack):
    return stack[-1]


def _has_dvonn(stack):
    return DVONN in stack


@dataclass
class DState:
    board: dict = field(default_factory=dict)     # (q,r) -> stack tuple
    phase: str = "place"                           # "place" | "move"
    to_move: int = WHITE
    # placement bookkeeping
    placed_dvonn: int = 0
    placed_white: int = 0
    placed_black: int = 0
    ply: int = 0
    winner: object = None                          # set only at end; None during play
    last: object = None                            # last destination cell for highlight


class Dvonn(Game):
    uid = "dvonn"
    name = "DVONN"

    @property
    def num_players(self):
        return 2

    # ------------------------------------------------------------------ setup
    def initial_state(self, options=None, rng=None):
        return DState(board={}, phase="place", to_move=WHITE)

    def current_player(self, state):
        return state.to_move

    # -------------------------------------------------------- placement phase
    def _placement_role(self, state):
        """Which colour does the NEXT placed piece have? DVONNs first, then
        White/Black alternate. Returns one of WHITE/BLACK/DVONN."""
        if state.placed_dvonn < N_DVONN:
            return DVONN
        # after the 3 DVONNs, players alternate placing their own pieces
        if state.placed_white <= state.placed_black:
            return WHITE
        return BLACK

    def _empty_cells(self, board):
        return [c for c in CELLS if c not in board]

    # ---------------------------------------------------------- move phase gen
    def _stack_moves(self, board, sq):
        """All legal destination cells for the stack at sq (mover = its top owner)."""
        stack = board[sq]
        h = len(stack)
        outs = []
        for (dq, dr) in DIRS:
            land = (sq[0] + h * dq, sq[1] + h * dr)
            if land in board:                       # must land on an occupied field
                outs.append(land)
        return outs

    def _moves_for(self, board, player):
        out = []
        for sq, stack in board.items():
            if _top(stack) != player:
                continue
            for land in self._stack_moves(board, sq):
                out.append([sq, land])
        return out

    def legal_moves(self, state):
        if state.winner is not None:
            return []
        if state.phase == "place":
            return [_key(*c) for c in self._empty_cells(state.board)]
        # movement phase
        moves = self._moves_for(state.board, state.to_move)
        if moves:
            return [">".join(_key(*c) for c in m) for m in moves]
        # no move for the player to move
        if self._moves_for(state.board, 1 - state.to_move):
            return ["pass"]                          # opponent can still move -> pass
        return []                                    # neither can move -> terminal

    # ------------------------------------------------------------------ apply
    def apply_move(self, state, move, rng=None):
        if state.phase == "place":
            return self._apply_place(state, move)
        return self._apply_move(state, move)

    def _apply_place(self, state, move):
        c = _cell(move)
        role = self._placement_role(state)
        board = dict(state.board)
        board[c] = (role,)
        ns = DState(
            board=board, phase="place", to_move=1 - state.to_move,
            placed_dvonn=state.placed_dvonn + (1 if role == DVONN else 0),
            placed_white=state.placed_white + (1 if role == WHITE else 0),
            placed_black=state.placed_black + (1 if role == BLACK else 0),
            ply=state.ply + 1, last=c,
        )
        # placement complete?
        if len(ns.board) == len(CELLS):
            ns.phase = "move"
            ns.to_move = WHITE                       # White moves first in phase 2
            # game could (degenerately) already be over
            if not self.legal_moves(ns):
                ns.winner = self._score_winner(ns.board)
        return ns

    def _apply_move(self, state, move):
        board = dict(state.board)
        player = state.to_move
        if move == "pass":
            ns = DState(board=board, phase="move", to_move=1 - player,
                        ply=state.ply + 1, last=state.last)
            if not self.legal_moves(ns):
                ns.winner = self._score_winner(ns.board)
            return ns

        pts = [_cell(s) for s in move.split(">")]
        frm, to = pts[0], pts[1]
        moving = board.pop(frm)
        dest = board[to]
        board[to] = dest + moving                    # moving stack lands on top
        # DVONN connectivity removal
        board = self._remove_disconnected(board)

        ns = DState(board=board, phase="move", to_move=1 - player,
                    ply=state.ply + 1, last=to)
        if not self.legal_moves(ns):
            ns.winner = self._score_winner(ns.board)
        return ns

    # ----------------------------------------------- DVONN connectivity removal
    def _remove_disconnected(self, board):
        """Flood-fill from every stack containing a DVONN piece through edge
        adjacency; any stack not reached is removed."""
        anchors = [sq for sq, st in board.items() if _has_dvonn(st)]
        if not anchors:
            return {}                                # no DVONN left -> all gone
        seen = set(anchors)
        stack = list(anchors)
        while stack:
            q, r = stack.pop()
            for (dq, dr) in DIRS:
                nb = (q + dq, r + dr)
                if nb in board and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        return {sq: st for sq, st in board.items() if sq in seen}

    # ------------------------------------------------------------- scoring/end
    def _scores(self, board):
        sc = {WHITE: 0, BLACK: 0}
        for st in board.values():
            owner = _top(st)
            if owner in (WHITE, BLACK):
                sc[owner] += len(st)
        return sc

    def _score_winner(self, board):
        sc = self._scores(board)
        if sc[WHITE] > sc[BLACK]:
            return WHITE
        if sc[BLACK] > sc[WHITE]:
            return BLACK
        return -1                                    # draw sentinel

    def is_terminal(self, state):
        return state.winner is not None

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        if state.winner == -1:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # --------------------------------------------------------------- serialise
    def _stack_str(self, st):
        return "".join("wbd"[o] for o in st)

    def _parse_stack(self, s):
        m = {"w": WHITE, "b": BLACK, "d": DVONN}
        return tuple(m[ch] for ch in s)

    def serialize(self, state):
        return {
            "board": {_key(*c): self._stack_str(st) for c, st in state.board.items()},
            "phase": state.phase,
            "to_move": state.to_move,
            "placed_dvonn": state.placed_dvonn,
            "placed_white": state.placed_white,
            "placed_black": state.placed_black,
            "ply": state.ply,
            "winner": state.winner,
            "last": (list(state.last) if state.last is not None else None),
        }

    def deserialize(self, d):
        return DState(
            board={_cell(k): self._parse_stack(v) for k, v in d["board"].items()},
            phase=d.get("phase", "place"),
            to_move=d["to_move"],
            placed_dvonn=d.get("placed_dvonn", 0),
            placed_white=d.get("placed_white", 0),
            placed_black=d.get("placed_black", 0),
            ply=d.get("ply", 0),
            winner=d.get("winner"),
            last=(tuple(d["last"]) if d.get("last") is not None else None),
        )

    # ------------------------------------------------------------ presentation
    def describe_move(self, state, move):
        if move == "pass":
            return "pass"
        if state.phase == "place":
            role = self._placement_role(state)
            tag = {WHITE: "W", BLACK: "B", DVONN: "D"}[role]
            return f"{tag}@{move}"
        return move.replace(">", "-")

    def render(self, state, perspective=None):
        import math
        cells = []
        rad = 0.58
        for (q, r) in CELLS:
            # axial -> pixel (pointy-top), then the elongated hexagon reads as a
            # horizontal band 5 rows tall.
            cx = math.sqrt(3) * (q + r / 2.0)
            cy = 1.5 * r
            pts = [[round(cx + rad * math.cos(math.radians(60 * k + 30)), 3),
                    round(cy + rad * math.sin(math.radians(60 * k + 30)), 3)]
                   for k in range(6)]
            cells.append({"id": _key(q, r), "points": pts})

        pieces = []
        for (q, r), st in state.board.items():
            top = _top(st)
            label = ""
            if _has_dvonn(st):
                label = "D"                          # tower contains a DVONN piece
            pieces.append({
                "cell": _key(q, r),
                "owner": top,
                "stack": list(st),                   # owners bottom->top
                "label": label,
            })

        highlights = []
        if state.last is not None and tuple(state.last) in state.board:
            highlights.append({"cell": _key(*state.last), "kind": "last-move"})

        names = {WHITE: "White", BLACK: "Black"}
        if state.winner is not None:
            sc = self._scores(state.board)
            if state.winner == -1:
                cap = f"Draw {sc[WHITE]}-{sc[BLACK]}"
            else:
                cap = f"{names[state.winner]} wins {sc[WHITE]}-{sc[BLACK]}"
        elif state.phase == "place":
            role = self._placement_role(state)
            what = {WHITE: "a White piece", BLACK: "a Black piece",
                    DVONN: "a red DVONN piece"}[role]
            cap = f"Placement: {names[state.to_move]} places {what}"
        else:
            sc = self._scores(state.board)
            cap = f"{names[state.to_move]} to move  (W {sc[WHITE]} - B {sc[BLACK]})"

        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
