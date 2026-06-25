"""Hive, by John Yianni (Gen42 Games, 2001) -- the base game (no expansions).

A boardless tile game: each insect tile IS part of the board. The two players
(0 = White, 1 = Black) each have 11 pieces -- 1 Queen Bee, 2 Spiders, 2 Beetles,
3 Grasshoppers, 3 Soldier Ants -- and either PLACE a new piece from their hand
or MOVE a piece already in the hive. The goal is to completely surround the
opponent's Queen Bee (all 6 neighbours occupied); the surrounded player loses.
If a single move surrounds both Queens at once, the game is a draw.

Coordinates are axial hex (q, r); a cell's 6 neighbours are the usual axial six.
Stacks (a Beetle climbed on top) are modelled as a list of (owner, bug) tuples
bottom->top at one cell; only the TOP piece can move and the pieces beneath are
frozen.

Render: a `polygons` board whose cells are every occupied hex PLUS every empty
hex that is a legal target this turn; pieces carry a bug `label` (and `stack`
owners for towers); the hand is a per-seat `reserve` tray. A placement is the
drop move "<bug>@q,r"; a move of a placed piece is "q,r>q,r".

Termination: Hive can in principle cycle, so a hard ply cap and a
no-progress (plies since a placement) cap both force a draw for the engine's
random-playout conformance check.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1

# Bug letters and the starting hand counts.
HAND = {"Q": 1, "S": 2, "B": 2, "G": 3, "A": 3}
BUG_ORDER = ["Q", "B", "G", "A", "S"]  # tray display order
BUG_NAME = {"Q": "Queen Bee", "S": "Spider", "B": "Beetle",
            "G": "Grasshopper", "A": "Soldier Ant"}

NO_PROGRESS_DRAW = 60   # plies with no placement (no new tile) -> draw safety
PLY_CAP = 300           # absolute hard cap -> draw safety

# axial neighbour offsets, in a consistent rotational order
DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def _neighbors(q, r):
    return [(q + dq, r + dr) for (dq, dr) in DIRS]


def _cell(s):
    q, r = s.split(",")
    return int(q), int(r)


def _cstr(c):
    return f"{c[0]},{c[1]}"


@dataclass
class HState:
    # board: (q,r) -> list of (owner, bug) bottom->top  (a non-empty stack)
    board: dict = field(default_factory=dict)
    # hands[player] = {bug: count}
    hands: dict = field(default_factory=dict)
    to_move: int = WHITE
    ply: int = 0
    since_place: int = 0   # plies since a piece was placed (no-progress counter)
    winner: object = "none"   # "none" | WHITE | BLACK | "draw"


# --------------------------------------------------------------------------
# Geometry / hive helpers
# --------------------------------------------------------------------------
def _occupied(board):
    return set(board.keys())


def _connected_without(board, removed):
    """Is the set of occupied cells minus `removed` connected (or empty)?"""
    cells = set(board.keys())
    cells.discard(removed)
    if not cells:
        return True
    start = next(iter(cells))
    seen = {start}
    stack = [start]
    while stack:
        c = stack.pop()
        for nb in _neighbors(*c):
            if nb in cells and nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return len(seen) == len(cells)


def _can_slide(occ, frm, to):
    """Freedom-to-move: can a ground piece slide from `frm` to adjacent empty
    `to`, given the set of occupied cells `occ` (with the moving piece already
    removed)? The two cells common to frm and to: exactly one must be occupied
    (one => room to slide through the gap AND staying in contact with the hive).
    """
    common = [n for n in _neighbors(*frm) if n in set(_neighbors(*to))]
    # there are always exactly two such hexes for adjacent cells
    occ_count = sum(1 for c in common if c in occ)
    return occ_count == 1


def _dir_index(frm, to):
    d = (to[0] - frm[0], to[1] - frm[1])
    return DIRS.index(d)


# --------------------------------------------------------------------------
# Per-bug move generation. `board` is the *full* board (incl. moving piece);
# we pop the moving piece's top before generating so connectivity / contact use
# the post-lift board.
# --------------------------------------------------------------------------
def _slide_steps(occ, frm):
    """One-step ground slides from `frm` to each legal adjacent empty hex."""
    out = []
    for to in _neighbors(*frm):
        if to in occ:
            continue
        if _can_slide(occ, frm, to):
            out.append(to)
    return out


def _queen_moves(occ, frm):
    return _slide_steps(occ, frm)


def _ant_moves(occ, frm):
    """Soldier Ant: any number of slide steps around the hive perimeter."""
    seen = set()
    stack = [frm]
    seen.add(frm)
    out = set()
    while stack:
        cur = stack.pop()
        for to in _slide_steps(occ, cur):
            if to not in seen:
                seen.add(to)
                out.add(to)
                stack.append(to)
    out.discard(frm)
    return list(out)


def _spider_moves(occ, frm):
    """Spider: exactly 3 slide steps, never revisiting a hex this move."""
    results = set()

    def walk(cur, path):
        if len(path) == 4:  # frm + 3 steps
            results.add(cur)
            return
        for to in _slide_steps(occ, cur):
            if to in path:
                continue
            walk(to, path + [to])

    walk(frm, [frm])
    results.discard(frm)
    return list(results)


def _grasshopper_moves(board, frm):
    """Grasshopper: jump in a straight line over >=1 contiguous occupied hexes,
    landing on the first empty hex beyond."""
    out = []
    occ = _occupied(board)
    for (dq, dr) in DIRS:
        nq, nr = frm[0] + dq, frm[1] + dr
        if (nq, nr) not in occ:
            continue  # must jump over at least one piece
        while (nq, nr) in occ:
            nq, nr = nq + dq, nr + dr
        out.append((nq, nr))
    return out


def _beetle_moves(board, occ, frm, height):
    """Beetle: one step in any direction, onto the ground OR onto/over the hive
    (climbing). The freedom-to-move gap rule is relaxed when moving at height:
    a beetle can move to an adjacent cell unless BOTH of the two gates are at a
    height strictly greater than the higher of (its own destination/source
    context). We use the standard simplified rule:

      - moving from height h (h = current stack height after lift) to adjacent
        cell, the move is blocked only if BOTH shared neighbours have a stack
        height > max(h_from_after_lift, h_to) -- i.e. you can't slip between two
        taller walls. At ground level (all heights 0/1) this reduces to the
        normal slide gap rule, except the beetle may also climb onto an occupied
        neighbour.
    """
    out = []
    h_from = height  # height the beetle sits at after lifting itself off
    for to in _neighbors(*frm):
        h_to = len(board.get(to, []))  # destination ground height (excludes us)
        # the two gates shared by frm and to
        common = [n for n in _neighbors(*frm) if n in set(_neighbors(*to))]
        gate_heights = [len(board.get(c, [])) for c in common]
        # the beetle moves at the higher of its source-after-lift level and the
        # destination level; it is blocked iff both gates are strictly higher.
        move_level = max(h_from, h_to)
        if all(gh > move_level for gh in gate_heights):
            continue  # squeezed between two taller stacks -> blocked
        # must always stay in contact with the hive (at least one gate or the
        # destination is occupied, OR the source still has the rest of the hive).
        # A beetle climbing onto `to` is fine; a beetle dropping to ground `to`
        # is fine if it remains adjacent to the hive.
        if h_to == 0 and gate_heights == [0, 0]:
            # dropping to an empty hex with both gates empty: stays attached only
            # if `to` touches the rest of the hive (any occupied post-lift cell,
            # which includes `frm` when the beetle came off a taller stack).
            others = [n for n in _neighbors(*to) if n in occ]
            if not others:
                continue
        out.append(to)
    return out


# --------------------------------------------------------------------------
# Placement helpers
# --------------------------------------------------------------------------
def _placement_cells(board, player):
    """Empty cells adjacent to the hive that touch ONLY `player`'s pieces.
    (Special-cased for the first two placements by the caller.)"""
    occ = _occupied(board)
    cands = set()
    for c in occ:
        for nb in _neighbors(*c):
            if nb not in occ:
                cands.add(nb)
    out = []
    for c in cands:
        owners = set()
        touches = False
        for nb in _neighbors(*c):
            if nb in board:
                touches = True
                owners.add(board[nb][-1][0])  # top owner of the neighbour stack
        if touches and owners == {player}:
            out.append(c)
    return out


class Hive(Game):
    uid = "hive"
    name = "Hive"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        return HState(
            board={},
            hands={WHITE: dict(HAND), BLACK: dict(HAND)},
            to_move=WHITE,
            ply=0,
            since_place=0,
            winner="none",
        )

    def current_player(self, s):
        return s.to_move

    # ---- queen placed? ----
    def _queen_placed(self, s, player):
        return s.hands[player].get("Q", 0) == 0

    def _piece_count(self, s, player):
        """How many of `player`'s pieces are already placed (on the board)."""
        n = 0
        for col in s.board.values():
            for (o, _b) in col:
                if o == player:
                    n += 1
        return n

    # ---- placement move generation ----
    def _placements(self, s):
        player = s.to_move
        hand = s.hands[player]
        avail = [b for b in BUG_ORDER if hand.get(b, 0) > 0]
        if not avail:
            return []
        occ = _occupied(s.board)

        # The very first piece of the whole game: only the origin.
        if not occ:
            cells = [(0, 0)]
        elif len(occ) == 1 and self._piece_count(s, player) == 0:
            # second placement of the game (opponent's first piece): adjacent to
            # the lone piece; it may touch the enemy piece (only one exists).
            (only,) = list(occ)
            cells = _neighbors(*only)
        else:
            cells = _placement_cells(s.board, player)

        # Queen-by-4th rule: a player MUST place their Queen by their 4th piece.
        # If this would be the player's 4th placement and the Queen is unplaced,
        # the only legal bug to place is the Queen.
        placed = self._piece_count(s, player)
        if placed == 3 and not self._queen_placed(s, player):
            avail = ["Q"] if hand.get("Q", 0) > 0 else []

        out = []
        for bug in avail:
            for c in cells:
                out.append(f"{bug}@{_cstr(c)}")
        return out

    # ---- movement move generation ----
    def _moves(self, s):
        player = s.to_move
        if not self._queen_placed(s, player):
            return []  # may not move any piece until the Queen is down
        out = []
        for cell, col in s.board.items():
            top_owner, top_bug = col[-1]
            if top_owner != player:
                continue
            height = len(col)  # this stack's height (incl. the moving top piece)
            # One-hive: removing the top piece must not disconnect the hive.
            # If height > 1, the cell stays occupied -> never disconnects.
            if height == 1:
                if not _connected_without(s.board, cell):
                    continue
            # Build the post-lift board (top piece removed).
            board2 = dict(s.board)
            rest = col[:-1]
            if rest:
                board2[cell] = rest
            else:
                board2.pop(cell)
            occ2 = _occupied(board2)

            if top_bug == "Q":
                dests = _queen_moves(occ2, cell)
            elif top_bug == "A":
                dests = _ant_moves(occ2, cell)
            elif top_bug == "S":
                dests = _spider_moves(occ2, cell)
            elif top_bug == "G":
                dests = _grasshopper_moves(board2, cell)
            elif top_bug == "B":
                # beetle's height after lifting itself = height of the rest at cell
                h_self = len(rest)
                dests = _beetle_moves(board2, occ2, cell, h_self)
            else:
                dests = []
            for d in dests:
                out.append(f"{_cstr(cell)}>{_cstr(d)}")
        return out

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        moves = self._placements(s) + self._moves(s)
        if not moves:
            return ["pass"]   # forced pass when no placement and no move exist
        return moves

    # ---- apply ----
    def apply_move(self, s, move, rng=None):
        player = s.to_move
        board = {c: list(col) for c, col in s.board.items()}
        hands = {WHITE: dict(s.hands[WHITE]), BLACK: dict(s.hands[BLACK])}
        placed = False

        if move == "pass":
            pass
        elif "@" in move:
            bug, cstr = move.split("@")
            c = _cell(cstr)
            if hands[player].get(bug, 0) <= 0:
                raise ValueError(f"no {bug} in hand")
            hands[player][bug] -= 1
            board.setdefault(c, [])
            board[c].append((player, bug))
            placed = True
        else:
            frm_s, to_s = move.split(">")
            frm, to = _cell(frm_s), _cell(to_s)
            col = board[frm]
            piece = col.pop()  # the top piece
            if not col:
                board.pop(frm)
            board.setdefault(to, [])
            board[to].append(piece)

        since_place = 0 if placed else s.since_place + 1
        ns = HState(
            board=board,
            hands=hands,
            to_move=1 - player,
            ply=s.ply + 1,
            since_place=since_place,
            winner="none",
        )
        ns.winner = self._compute_winner(ns)
        return ns

    # ---- win detection ----
    def _queen_cell(self, board, player):
        for c, col in board.items():
            for (o, b) in col:
                if o == player and b == "Q":
                    return c
        return None

    def _surrounded(self, board, player):
        qc = self._queen_cell(board, player)
        if qc is None:
            return False
        return all(nb in board for nb in _neighbors(*qc))

    def _compute_winner(self, s):
        w_dead = self._surrounded(s.board, WHITE)
        b_dead = self._surrounded(s.board, BLACK)
        if w_dead and b_dead:
            return "draw"
        if w_dead:
            return BLACK
        if b_dead:
            return WHITE
        return "none"

    # ---- terminal ----
    def _safety_draw(self, s):
        return (s.winner == "none"
                and (s.ply >= PLY_CAP or s.since_place >= NO_PROGRESS_DRAW))

    def is_terminal(self, s):
        return s.winner != "none" or self._safety_draw(s)

    def returns(self, s):
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # "draw" or safety draw

    # ---- serialize ----
    def serialize(self, s):
        return {
            "board": {_cstr(c): [[o, b] for (o, b) in col] for c, col in s.board.items()},
            "hands": {str(p): dict(h) for p, h in s.hands.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "since_place": s.since_place,
            "winner": s.winner,
        }

    def deserialize(self, d):
        return HState(
            board={_cell(k): [(o, b) for (o, b) in col] for k, col in d["board"].items()},
            hands={int(p): dict(h) for p, h in d["hands"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            since_place=d.get("since_place", 0),
            winner=d.get("winner", "none"),
        )

    # ---- presentation ----
    def describe_move(self, s, move):
        if move == "pass":
            return "pass"
        if "@" in move:
            bug, cstr = move.split("@")
            return f"place {BUG_NAME[bug]} @ {cstr}"
        frm, to = move.split(">")
        return f"{frm} -> {to}"

    # ---- render ----
    SQRT3 = math.sqrt(3.0)

    def _hex_points(self, q, r):
        """Pointy-top hexagon vertices around the axial->pixel centre of (q,r)."""
        cx = self.SQRT3 * (q + r / 2.0)
        cy = 1.5 * r
        pts = []
        for k in range(6):
            ang = math.radians(60 * k - 90)  # pointy-top: first vertex at top
            pts.append([round(cx + math.cos(ang), 4), round(cy + math.sin(ang), 4)])
        return pts

    def render(self, s, perspective=None):
        # Cells to draw: all occupied + all legal target hexes this turn.
        cells = set(s.board.keys())
        targets = set()
        if self.is_terminal(s):
            pass
        else:
            for m in self.legal_moves(s):
                if m == "pass":
                    continue
                if "@" in m:
                    _, cstr = m.split("@")
                    targets.add(_cell(cstr))
                else:
                    _, to_s = m.split(">")
                    targets.add(_cell(to_s))
        cells |= targets
        if not cells:
            cells = {(0, 0)}

        cell_list = [{"id": _cstr(c), "points": self._hex_points(*c)} for c in sorted(cells)]

        pieces = []
        for c, col in s.board.items():
            top_owner, top_bug = col[-1]
            piece = {"cell": _cstr(c), "owner": top_owner, "label": top_bug}
            if len(col) > 1:
                piece["stack"] = [o for (o, _b) in col]  # bottom -> top owners
            pieces.append(piece)

        names = {WHITE: "White", BLACK: "Black"}
        if s.winner == "draw":
            caption = "Draw (both Queens surrounded)"
        elif s.winner in (WHITE, BLACK):
            caption = f"{names[s.winner]} wins (Queen surrounded)"
        elif self._safety_draw(s):
            caption = "Draw"
        else:
            caption = f"{names[s.to_move]} to move"
            if not self._queen_placed(s, s.to_move):
                placed = self._piece_count(s, s.to_move)
                if placed == 3:
                    caption += " (must place Queen)"

        spec = {
            "board": {"type": "polygons", "cells": cell_list},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
        # reserve trays (the hand), only for non-empty hands
        reserve = {}
        for p in (WHITE, BLACK):
            entries = {b: n for b in BUG_ORDER if (n := s.hands[p].get(b, 0)) > 0}
            if entries:
                reserve[str(p)] = entries
        if reserve:
            spec["reserve"] = reserve
        return spec
