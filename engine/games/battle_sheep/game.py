"""Battle Sheep (Blue Orange Games, designer Francesco Rotta) -- the 'Splitter'
mechanism on a hex pasture.

Each player owns a single tower of 16 sheep. A turn SPLITS one of your stacks
(height >= 2): you leave at least one sheep behind and take the rest (any number
1..height-1) off the TOP, then slide that taken group in ONE of the six straight
hex directions as FAR as it can go -- it must move at least one hex and stops on
the last empty hex before a board edge or any occupied hex. A stack of height 1
cannot move. There are NO captures. When no player can make any move the game
ends; the winner is the player occupying the MOST hexes, tie-broken by the
LARGEST single connected herd (chain of own hexes joined by a shared side).

BOARD (a documented FIXED choice -- see rules.md / the module note below). The
physical game builds the pasture from 4-hex tiles (each player contributes 4
tiles of 4 hexes); a 2-player game therefore uses 8 tiles = 32 hexes. This
package bakes in ONE fixed, symmetric 32-hex arrangement instead of modelling
tile placement: an 8-wide x 4-row axial parallelogram (q in 0..7, r in 0..3).
It is fully connected and has 180-degree rotational symmetry, so the two fixed
starting corners are mirror images and the position is balanced. We FLAG this:
the real game lets players build the board from tiles; we use a fixed board.

SETUP is also fixed (not modelled as opening moves): player 0's 16-sheep tower
starts on perimeter corner (0,0); player 1's on the opposite corner (7,3).

Termination is guaranteed: every move slides a non-empty group onto a hex that
was previously empty, so the number of OCCUPIED hexes strictly increases by 1
each move, bounded by the 32 board hexes.

Reuses the platform's stacking glyph: each hex renders as an owner-coloured
tower (`piece.stack`) with a height badge equal to the number of sheep there.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

# Six axial hex directions (q, r).
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

WIDTH, HEIGHT = 8, 4            # the fixed parallelogram board, q in 0..7, r in 0..3
SHEEP = 16                      # sheep per player


def _build_board():
    """The fixed 32-hex pasture: an 8-wide x 4-row axial parallelogram.

    Connected and 180-deg rotationally symmetric about its centre (3.5, 1.5)."""
    return frozenset((q, r) for r in range(HEIGHT) for q in range(WIDTH))


BOARD = _build_board()

# Fixed starting hexes (opposite, mirror-symmetric perimeter corners).
START = {0: (0, 0), 1: (WIDTH - 1, HEIGHT - 1)}


def _cell(s):
    q, r = s.split(",")
    return int(q), int(r)


def _key(q, r):
    return f"{q},{r}"


@dataclass
class BSState:
    # board: (q, r) -> [owner, height]; only occupied hexes are present.
    board: dict = field(default_factory=dict)
    to_move: int = 0
    ply: int = 0
    winner: object = None      # set only at terminal: 0, 1, or -1 for a draw


class BattleSheep(Game):
    uid = "battle_sheep"
    name = "Battle Sheep"

    @property
    def num_players(self):
        return 2

    # ------------------------------------------------------------------ setup
    def initial_state(self, options=None, rng=None):
        board = {START[0]: [0, SHEEP], START[1]: [1, SHEEP]}
        return BSState(board=board, to_move=0)

    def current_player(self, state):
        return state.to_move

    # -------------------------------------------------------- move generation
    def _slide_dest(self, board, sq, d):
        """From `sq`, slide in direction `d` as far as possible; return the last
        empty hex reached, or None if the group cannot move at all (the very next
        hex is off-board or occupied)."""
        q, r = sq
        dq, dr = d
        dest = None
        nq, nr = q + dq, r + dr
        while (nq, nr) in BOARD and (nq, nr) not in board:
            dest = (nq, nr)
            nq, nr = nq + dq, nr + dr
        return dest

    def _moves_for(self, board, player):
        """All legal moves for `player` as [from, to, count] triples."""
        out = []
        for sq, (owner, h) in board.items():
            if owner != player or h < 2:
                continue
            for d in DIRS:
                dest = self._slide_dest(board, sq, d)
                if dest is None:
                    continue
                # Any split count 1..h-1 (leave >=1 behind, take >=1).
                for count in range(1, h):
                    out.append((sq, dest, count))
        return out

    def _has_move(self, board, player):
        for sq, (owner, h) in board.items():
            if owner != player or h < 2:
                continue
            for d in DIRS:
                if self._slide_dest(board, sq, d) is not None:
                    return True
        return False

    def legal_moves(self, state):
        if state.winner is not None:
            return []
        moves = self._moves_for(state.board, state.to_move)
        if moves:
            return [f"{_key(*frm)}>{_key(*to)}={count}" for (frm, to, count) in moves]
        # current player cannot move; if the opponent can, pass to them.
        if self._has_move(state.board, 1 - state.to_move):
            return ["pass"]
        return []   # neither can move -> terminal (winner set in apply_move)

    # ------------------------------------------------------------------ apply
    def apply_move(self, state, move, rng=None):
        board = {sq: list(v) for sq, v in state.board.items()}
        player = state.to_move

        if move == "pass":
            ns = BSState(board=board, to_move=1 - player, ply=state.ply + 1)
            return self._finish_if_done(ns)

        path, _, count_s = move.partition("=")
        frm_s, _, to_s = path.partition(">")
        frm, to = _cell(frm_s), _cell(to_s)
        count = int(count_s)

        owner, h = board[frm]
        if owner != player:
            raise ValueError(f"not {player}'s stack at {frm_s}")
        if not (1 <= count <= h - 1):
            raise ValueError(f"illegal split count {count} from height {h}")
        if to in board or to not in BOARD:
            raise ValueError(f"illegal destination {to_s}")

        board[frm][1] = h - count
        board[to] = [player, count]

        ns = BSState(board=board, to_move=1 - player, ply=state.ply + 1)
        return self._finish_if_done(ns)

    def _finish_if_done(self, ns):
        """If the player to move (ns.to_move) cannot move, either pass (handled by
        legal_moves) or, if NEITHER side can move, set the winner."""
        if self._has_move(ns.board, ns.to_move):
            return ns
        if self._has_move(ns.board, 1 - ns.to_move):
            return ns   # current player will 'pass'; game continues
        ns.winner = self._score_winner(ns.board)
        return ns

    # ------------------------------------------------------------- scoring/end
    def _hex_count(self, board, player):
        return sum(1 for (owner, _h) in board.values() if owner == player)

    def _largest_herd(self, board, player):
        own = {sq for sq, (owner, _h) in board.items() if owner == player}
        best = 0
        seen = set()
        for start in own:
            if start in seen:
                continue
            comp = 0
            stack = [start]
            seen.add(start)
            while stack:
                q, r = stack.pop()
                comp += 1
                for dq, dr in DIRS:
                    nb = (q + dq, r + dr)
                    if nb in own and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            best = max(best, comp)
        return best

    def _score_winner(self, board):
        h0, h1 = self._hex_count(board, 0), self._hex_count(board, 1)
        if h0 != h1:
            return 0 if h0 > h1 else 1
        # tie-break: largest single connected herd
        g0, g1 = self._largest_herd(board, 0), self._largest_herd(board, 1)
        if g0 != g1:
            return 0 if g0 > g1 else 1
        return -1   # genuine draw

    def is_terminal(self, state):
        return state.winner is not None

    def returns(self, state):
        if state.winner is None or state.winner == -1:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # --------------------------------------------------------------- serialise
    def serialize(self, state):
        return {
            "board": {_key(*sq): [owner, h] for sq, (owner, h) in state.board.items()},
            "to_move": state.to_move,
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return BSState(
            board={_cell(k): [v[0], v[1]] for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # ------------------------------------------------------------ presentation
    def describe_move(self, state, move):
        if move == "pass":
            return "pass"
        path, _, count = move.partition("=")
        return f"{path.replace('>', '-')} ({count})"

    def render(self, state, perspective=None):
        import math
        cells = []
        rad = 0.58
        for (q, r) in sorted(BOARD):
            cx = math.sqrt(3) * (q + r / 2.0)
            cy = 1.5 * r
            pts = [[round(cx + rad * math.cos(math.radians(60 * k + 30)), 3),
                    round(cy + rad * math.sin(math.radians(60 * k + 30)), 3)]
                   for k in range(6)]
            cells.append({"id": _key(q, r), "points": pts})

        pieces = []
        for (q, r), (owner, h) in state.board.items():
            pieces.append({
                "cell": _key(q, r),
                "owner": owner,
                "stack": [owner] * h,      # tower glyph; height badge = sheep count
                "label": str(h),
            })

        names = {0: "Orange", 1: "Blue"}
        if state.winner is not None:
            h0, h1 = self._hex_count(state.board, 0), self._hex_count(state.board, 1)
            if state.winner == -1:
                cap = f"Draw {h0}-{h1}"
            else:
                cap = f"{names[state.winner]} wins {h0}-{h1} hexes"
        else:
            h0, h1 = self._hex_count(state.board, 0), self._hex_count(state.board, 1)
            cap = f"{names[state.to_move]} to move  (hexes {h0}-{h1})"

        return {
            "board": {"type": "polygons", "cells": cells},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
