"""Tak (James Ernest & Patrick Rothfuss, 2016) -- the road-building stacking game.

Players build a **road**: an unbroken orthogonal chain of squares they control
(topped by a flat stone or a capstone) joining two opposite edges of the board.
Pieces come in three kinds:

- **flat stone** (``F``): lies flat, counts toward roads, can be stacked upon.
- **standing stone / wall** (``S``): blocks roads (counts for nothing) and cannot
  be stacked upon -- except a lone capstone may flatten it.
- **capstone** (``C``): counts toward roads, can never be covered, and when moving
  ALONE onto a wall flattens that wall to a flat stone.

You control a stack iff your piece is the **top** piece. A turn is either a
PLACE (one reserve piece on an empty square) or a stack MOVE (a "spread": lift up
to N pieces, move in a straight orthogonal line dropping >=1 on each square).

The **opening double-move**: on each player's very FIRST turn they must place a
single flat of the OPPONENT's colour on an empty square.

Squares are ``c,r`` on an NxN grid. The renderer draws each square's stack as
layered owner-coloured bands (the Lasca tower glyph) with a top-piece label.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from agp.game import Game

P0, P1 = 0, 1
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
PLY_CAP = 400          # hard cap -> flat-count (no-progress safety)

# piece kinds, stored as the top-of-stack "cap"
FLAT, WALL, CAP = "F", "S", "C"

# reserves by board size: (flats, capstones)
RESERVES = {
    3: (10, 0),
    4: (15, 0),
    5: (21, 1),
    6: (30, 1),
    8: (50, 2),
}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(c, r):
    return f"{c},{r}"


# A square is None (empty) or a (stack, top_kind) pair where:
#   stack    = tuple of owners bottom->top (every covered piece is a flattened flat)
#   top_kind = FLAT / WALL / CAP -- the kind of the TOP piece only
# The top owner = stack[-1]; covered pieces always act as flats.

def _owner(sq):
    return sq[0][-1]


def _height(sq):
    return len(sq[0])


@dataclass
class TState:
    n: int = 5
    board: dict = field(default_factory=dict)         # (c,r) -> (stack_tuple, top_kind)
    to_move: int = P0
    reserves: dict = field(default_factory=dict)      # player -> [flats_left, caps_left]
    first_done: list = field(default_factory=lambda: [False, False])
    ply: int = 0
    winner: object = None                              # None | 0 | 1 | "draw"


class Tak(Game):
    uid = "tak"
    name = "Tak"

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        n = int((options or {}).get("size", 5))
        if n not in RESERVES:
            n = 5
        flats, caps = RESERVES[n]
        return TState(
            n=n,
            board={},
            to_move=P0,
            reserves={P0: [flats, caps], P1: [flats, caps]},
            first_done=[False, False],
        )

    def current_player(self, state):
        return state.to_move

    # ---- geometry ----------------------------------------------------------
    def _on(self, state, c, r):
        return 0 <= c < state.n and 0 <= r < state.n

    # ---- move generation ---------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        p = state.to_move
        n = state.n

        # opening double-move: place ONE flat of the OPPONENT's colour on empty
        if not state.first_done[p]:
            return [_fmt(c, r) for r in range(n) for c in range(n)
                    if (c, r) not in state.board]

        moves = []
        flats_left, caps_left = state.reserves[p]
        have_stone = flats_left > 0          # flats reserve = flats + walls share it
        # PLACEMENTS on empty squares
        for r in range(n):
            for c in range(n):
                if (c, r) in state.board:
                    continue
                if have_stone:
                    moves.append(f"{c},{r}=F")
                    moves.append(f"{c},{r}=S")
                if caps_left > 0:
                    moves.append(f"{c},{r}=C")

        # STACK MOVES (spreads) from squares this player controls
        for (c, r), sq in state.board.items():
            if _owner(sq) != p:
                continue
            top_kind = sq[1]
            height = _height(sq)
            max_lift = min(height, n)
            for (dc, dr) in ORTHO:
                moves.extend(self._spreads(state, c, r, dc, dr, max_lift, top_kind))
        return moves

    def _spreads(self, state, oc, or_, dc, dr, max_lift, top_kind):
        """Generate every legal spread move string in one direction.

        For each lift count `k` (1..max_lift) enumerate every drop distribution
        d1,d2,... (each >=1, summing to k) along consecutive squares. A wall
        blocks unless the moving stack is a LONE capstone whose final drop lands
        on it (flattening). A capstone-topped square always blocks.
        """
        out = []
        for k in range(1, max_lift + 1):
            self._spread_rec(state, oc, or_, oc, or_, dc, dr, k, top_kind, [], out)
        return out

    def _spread_rec(self, state, oc, or_, c, r, dc, dr, remaining, top_kind,
                    drops, out):
        """We have already entered square (c,r) (origin if drops empty) with
        `remaining` pieces still in hand; consider stepping onto the next square.
        `oc,or_` is the spread origin (for encoding the move string)."""
        nc, nr = c + dc, r + dr
        if not self._on(state, nc, nr):
            return
        target = state.board.get((nc, nr))
        flatten = False
        if target is not None:
            tk = target[1]
            if tk == CAP:
                return                      # capstone can never be covered
            if tk == WALL:
                # only a LONE capstone, dropping its single remaining piece, flattens
                if top_kind == CAP and remaining == 1:
                    flatten = True
                else:
                    return
        if flatten:
            lo, hi = remaining, remaining   # final square, drop the last piece
        else:
            lo, hi = 1, remaining
        for d in range(lo, hi + 1):
            new_drops = drops + [d]
            left = remaining - d
            if left == 0:
                out.append(self._encode_full(oc, or_, dc, dr, new_drops))
            elif not flatten:
                self._spread_rec(state, oc, or_, nc, nr, dc, dr, left, top_kind,
                                 new_drops, out)

    def _encode_full(self, oc, or_, dc, dr, all_drops):
        path = [_fmt(oc, or_)]
        cc, rr = oc, or_
        for _ in all_drops:
            cc += dc
            rr += dr
            path.append(_fmt(cc, rr))
        suffix = "".join(str(d) for d in all_drops)
        return ">".join(path) + "=" + suffix

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        ns = TState(
            n=state.n,
            board=dict(state.board),
            to_move=state.to_move,
            reserves={pl: list(v) for pl, v in state.reserves.items()},
            first_done=list(state.first_done),
            ply=state.ply + 1,
            winner=None,
        )
        p = state.to_move

        if not state.first_done[p]:
            # opening: place opponent-coloured flat
            c, r = _cell(move)
            ns.board[(c, r)] = ((1 - p,), FLAT)
            ns.first_done[p] = True
        elif "=" in move and ">" not in move:
            # PLACEMENT
            cell, kind = move.split("=")
            c, r = _cell(cell)
            ns.board[(c, r)] = ((p,), kind)
            if kind == CAP:
                ns.reserves[p][1] -= 1
            else:
                ns.reserves[p][0] -= 1
        else:
            # SPREAD: path=drops
            path_str, drops_str = move.split("=")
            path = [_cell(s) for s in path_str.split(">")]
            drops = [int(ch) for ch in drops_str]
            origin = path[0]
            sq = ns.board[origin]
            stack, top_kind = sq
            lift = sum(drops)
            carried = list(stack[-lift:])           # bottom->top of carried portion
            remaining = stack[:-lift]
            if remaining:
                ns.board[origin] = (remaining, FLAT)  # exposed piece acts as flat
            else:
                del ns.board[origin]
            # the TOP of the carried stack keeps top_kind; covered pieces are flats
            idx = 0  # index into carried from bottom
            for i, (cell, d) in enumerate(zip(path[1:], drops)):
                piece_owners = carried[idx:idx + d]
                idx += d
                is_last_group = (i == len(drops) - 1)
                existing = ns.board.get(cell)
                base = list(existing[0]) if existing else []
                new_stack = tuple(base + piece_owners)
                if is_last_group:
                    kind = top_kind
                else:
                    kind = FLAT
                ns.board[cell] = (new_stack, kind)

        ns.to_move = 1 - p
        self._resolve_terminal(ns, mover=p)
        return ns

    # ---- terminal ----------------------------------------------------------
    def _resolve_terminal(self, ns, mover):
        """Set ns.winner after `mover` just moved (ns.to_move = the other player)."""
        n = ns.n
        # 1) ROAD check -- mover wins tie-break, so check mover FIRST
        mover_road = self._has_road(ns, mover)
        other = 1 - mover
        other_road = self._has_road(ns, other)
        if mover_road:
            ns.winner = mover
            return
        if other_road:
            ns.winner = other
            return
        # 2) FLAT WIN: board full, OR a player has placed their LAST piece —
        # i.e. their ENTIRE reserve is gone (BOTH flats and capstone). Running
        # out of just flats while still holding a capstone does NOT end the game
        # (official USTak rule); the player keeps playing the capstone.
        board_full = len(ns.board) == n * n
        out_of_pieces = any(ns.reserves[pl][0] == 0 and ns.reserves[pl][1] == 0
                            for pl in (P0, P1))
        if board_full or out_of_pieces:
            ns.winner = self._flat_winner(ns)
            return
        # 3) no-progress safety cap
        if ns.ply >= PLY_CAP:
            ns.winner = self._flat_winner(ns)
            return

    def _flat_winner(self, state):
        c0 = sum(1 for sq in state.board.values()
                 if sq[1] == FLAT and _owner(sq) == P0)
        c1 = sum(1 for sq in state.board.values()
                 if sq[1] == FLAT and _owner(sq) == P1)
        if c0 > c1:
            return P0
        if c1 > c0:
            return P1
        return "draw"

    def _road_squares(self, state, player):
        """Squares that count for `player`'s road: top piece is theirs and is a
        flat or a capstone (NOT a wall)."""
        return {(c, r) for (c, r), sq in state.board.items()
                if _owner(sq) == player and sq[1] in (FLAT, CAP)}

    def _has_road(self, state, player):
        n = state.n
        cells = self._road_squares(state, player)
        if not cells:
            return False
        # vertical: top edge (r=0) to bottom edge (r=n-1)
        if self._connects(cells, n, vertical=True):
            return True
        # horizontal: left (c=0) to right (c=n-1)
        if self._connects(cells, n, vertical=False):
            return True
        return False

    def _connects(self, cells, n, vertical):
        if vertical:
            starts = [(c, 0) for c in range(n) if (c, 0) in cells]
            def at_goal(cell):
                return cell[1] == n - 1
        else:
            starts = [(0, r) for r in range(n) if (0, r) in cells]
            def at_goal(cell):
                return cell[0] == n - 1
        seen = set(starts)
        q = deque(starts)
        while q:
            c, r = q.popleft()
            if at_goal((c, r)):
                return True
            for dc, dr in ORTHO:
                nb = (c + dc, r + dr)
                if nb in cells and nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        return False

    def is_terminal(self, state):
        return state.winner is not None

    def returns(self, state):
        if state.winner is None or state.winner == "draw":
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialise ---------------------------------------------------------
    def _sq_str(self, sq):
        owners = "".join(str(o) for o in sq[0])
        return f"{owners}:{sq[1]}"

    def _parse_sq(self, s):
        owners, kind = s.split(":")
        return (tuple(int(ch) for ch in owners), kind)

    def serialize(self, state):
        return {
            "n": state.n,
            "board": {_fmt(c, r): self._sq_str(sq)
                      for (c, r), sq in state.board.items()},
            "to_move": state.to_move,
            "reserves": {str(pl): list(v) for pl, v in state.reserves.items()},
            "first_done": list(state.first_done),
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return TState(
            n=d["n"],
            board={_cell(k): self._parse_sq(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            reserves={int(pl): list(v) for pl, v in d["reserves"].items()},
            first_done=list(d.get("first_done", [False, False])),
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        return move

    def render(self, state, perspective=None):
        n = state.n
        pieces = []
        for (c, r), sq in state.board.items():
            stack, kind = sq
            label = {FLAT: "", WALL: "S", CAP: "C"}[kind]
            pieces.append({
                "cell": _fmt(c, r),
                "owner": stack[-1],
                "stack": list(stack),       # bottom->top owners (tower glyph)
                "label": label,
            })
        names = {P0: "Player 1", P1: "Player 2"}
        if state.winner == "draw":
            cap = "Draw"
        elif state.winner is not None:
            cap = f"{names[state.winner]} wins"
        else:
            p = state.to_move
            if not state.first_done[p]:
                cap = f"{names[p]} to place (opening: opponent's flat)"
            else:
                fl, cp = state.reserves[p]
                cap = f"{names[p]} to move  [stones:{fl} caps:{cp}]"
        reserve = {
            str(P0): {"flat": state.reserves[P0][0], "cap": state.reserves[P0][1]},
            str(P1): {"flat": state.reserves[P1][0], "cap": state.reserves[P1][1]},
        }
        return {
            "board": {"type": "square", "width": n, "height": n},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
            "reserve": reserve,
            # Label the placement-type picker (F/S/C collide with chess letters).
            "choiceTitle": "Place as",
            "choiceNames": {"F": "Flat", "S": "Wall", "C": "Capstone"},
        }
