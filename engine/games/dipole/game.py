"""Dipole -- Mark Steere, May 2007.

A checkers-set stacking game played on the 32 dark squares of an 8x8 board.
Each player owns ONE 12-high stack (the "pole") on a dark square of their own
near row: White on e1 = ``4,0``, Black on d8 = ``3,7``.

The one rule that generates everything else: **a stack moves exactly as many
squares as it has checkers in it**, and you may split any number of checkers off
the top of a stack and move just those. So a 12-stack can send 1 checker one
square, or 7 checkers seven squares, etc.

* **Non-capturing moves** (to an empty square, or merging onto a friendly stack)
  go only **forward or diagonally forward** (3 directions).
* **Capturing moves** go in **any of the 8 queen directions**, and take an
  **entire** enemy stack of size **<= the moving sub-stack**.
* Nothing ever blocks a move -- stacks jump over anything in between.
* A move whose destination falls **off the board** removes those checkers from
  play (a bear-off). Only the 3 forward directions may bear off.
* Only dark squares exist, so a straight (non-diagonal) move must be an **even**
  number of squares; diagonal moves always land on a dark square.

**Object:** remove *every* enemy checker from the board. Note that bearing off
your own checkers costs you material, so running out of your own men loses.

A player with no legal move **sits out** until they have one (the engine simply
does not hand them the turn); the PDF states there is always a move available to
one player or the other. Steere states "Draws cannot occur in Dipole."

Rules verified against the designer's rulebook,
https://www.marksteeregames.com/Dipole_rules.pdf
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}

# All eight queen directions as (dc, dr).
ALL_DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def forward_dirs(player):
    """The three legal NON-capturing / bear-off directions for `player`."""
    d = 1 if player == WHITE else -1
    return [(-1, d), (0, d), (1, d)]


def dark_parity(c, r):
    """Dark-square test on the *infinite* extension of the board (bear-offs)."""
    return (c + r) % 2 == 0


def checkers_for(size):
    """Checkers per player: 12 on the 8x8 board, 20 on the 10x10 board."""
    return 12 if size == 8 else 20


def pole_columns(size):
    """(white_col, black_col) -- the dark square of row 0 nearest the centre,
    and its 180-degree image on the far row.  8x8 -> (4, 3) = e1/d8;
    10x10 -> (4, 5) = e1/f10 (both confirmed against the rulebook figure)."""
    # `size` is even, so `mid` is a half-integer and the even columns are all a
    # different distance from it -- no tie to break.
    mid = (size - 1) / 2.0
    wc = min((c for c in range(size) if c % 2 == 0), key=lambda c: abs(c - mid))
    return wc, size - 1 - wc


def _cell(txt):
    c, r = txt.split(",")
    return int(c), int(r)


def alg(c, r):
    """'4,0' -> 'e1' (the rulebook's notation), for move descriptions."""
    return f"{chr(ord('a') + c)}{r + 1}"


@dataclass
class DState:
    size: int = 8
    board: dict = field(default_factory=dict)   # (c,r) -> (owner, height)
    to_move: int = WHITE
    ply: int = 0
    last: object = None                          # last move string, or None
    over: bool = False
    winner: object = None                        # 0 / 1 when over; None = draw


def ply_cap(size):
    """A provably-dead termination backstop, derived from the game's own bound.

    Let PHI = sum over on-board checkers of how many rows each has advanced
    toward the enemy back row (0 .. size-1).  Every non-capturing move (plain or
    merging) sends k checkers exactly k rows FORWARD, so it raises PHI by k*k >= 1.
    A bear-off strictly reduces material.  A capture strictly reduces material
    (it removes >= 1 enemy checker) and can lower PHI by at most k*k <= N*N.

    Material starts at M = 2N and never grows, so there are at most M
    material-reducing moves; PHI in [0, M*(size-1)]; hence the total PHI gain --
    and therefore the number of non-capturing moves -- is at most
    M*(size-1) + M*N*N.  Add the M material moves for the bound below.
    (Passes are not plies here: a stuck player is simply skipped.)
    """
    n = checkers_for(size)
    m = 2 * n
    return m * (size - 1) + m * n * n + m


class Dipole(Game):
    """Dipole (Mark Steere, 2007)."""

    @property
    def num_players(self):
        return 2

    # ---------------------------------------------------------------- setup
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        size = int(opts.get("size", 8))
        if size not in (8, 10):
            size = 8
        n = checkers_for(size)
        wc, bc = pole_columns(size)
        board = {(wc, 0): (WHITE, n), (bc, size - 1): (BLACK, n)}
        return DState(size=size, board=board, to_move=WHITE, ply=0)

    def current_player(self, state):
        return state.to_move

    # ------------------------------------------------------------ movegen
    def _moves_for(self, s, player):
        """Every legal move string for `player` in state `s` (board only)."""
        size = s.size
        fwd_set = set(forward_dirs(player))
        out = []
        offs = set()
        for (c, r), (owner, h) in sorted(s.board.items()):
            if owner != player:
                continue
            for k in range(1, h + 1):
                for (dc, dr) in ALL_DIRS:
                    # Only dark squares exist: a straight move must be even.
                    if not dark_parity(c + k * dc, r + k * dr):
                        continue
                    tc, tr = c + k * dc, r + k * dr
                    is_fwd = (dc, dr) in fwd_set
                    if not (0 <= tc < size and 0 <= tr < size):
                        # Off the board: a bear-off, forward directions only.
                        # (The parity test above is redundant for bear-offs and
                        # only ever costs a duplicate: a straight-forward move
                        # leaves the board when r + k is past the far row, and
                        # then BOTH forward diagonals leave it too -- and those
                        # always land on a dark square -- so the same (from, k)
                        # is already in `offs`.  Verified exhaustively over
                        # every cell/height/size.)
                        if is_fwd:
                            offs.add((c, r, k))
                        continue
                    occ = s.board.get((tc, tr))
                    if occ is None:
                        if is_fwd:
                            out.append(f"{c},{r}>{tc},{tr}")
                    elif occ[0] == player:
                        if is_fwd:                      # merge
                            out.append(f"{c},{r}>{tc},{tr}")
                    elif occ[1] <= k:                   # capture, any direction
                        out.append(f"{c},{r}>{tc},{tr}")
        for (c, r, k) in sorted(offs):
            out.append(f"{c},{r}>off={k}")
        return out

    def legal_moves(self, state):
        if state.over:
            return []
        return self._moves_for(state, state.to_move)

    def _has_move(self, s, player):
        # Cheap short-circuit: a player with no checkers has no move.
        if not any(o == player for (o, _h) in s.board.values()):
            return False
        return bool(self._moves_for(s, player))

    # ------------------------------------------------------------- apply
    @staticmethod
    def parse(move):
        """'4,0>7,3' -> ((4,0),(7,3),3);  '4,0>off=5' -> ((4,0),None,5)."""
        frm_s, _, rest = move.partition(">")
        frm = _cell(frm_s)
        if rest.startswith("off="):
            return frm, None, int(rest[4:])
        to = _cell(rest)
        k = max(abs(to[0] - frm[0]), abs(to[1] - frm[1]))
        return frm, to, k

    def apply_move(self, state, move, rng=None):
        s = state
        frm, to, k = self.parse(move)
        player = s.to_move
        board = dict(s.board)                    # copy-on-write; values are tuples
        owner, h = board[frm]
        if h > k:
            board[frm] = (owner, h - k)
        else:
            del board[frm]
        if to is not None:
            occ = board.get(to)
            if occ is not None and occ[0] == player:
                board[to] = (player, occ[1] + k)     # merge
            else:
                board[to] = (player, k)              # move, or capture (enemy gone)

        ns = DState(size=s.size, board=board, to_move=player, ply=s.ply + 1,
                    last=move)

        # --- terminal checks.  A DECISIVE RESULT OUTRANKS EVERY DRAW COUNTER:
        # the win test runs first and returns before the ply cap / stuck test.
        counts = {WHITE: 0, BLACK: 0}
        for (o, hh) in board.values():
            counts[o] += hh
        other = 1 - player
        if counts[other] == 0:
            ns.over, ns.winner = True, player
            return ns
        if counts[player] == 0:                  # bore off your own last checker
            ns.over, ns.winner = True, other
            return ns

        # Whose turn?  The opponent moves if they can; otherwise the mover moves
        # again ("sit the game out until you do have a move available").
        if self._has_move(ns, other):
            ns.to_move = other
        elif self._has_move(ns, player):
            ns.to_move = player
        else:
            # Both players stuck with material on the board.  PROVABLY dead:
            # take the TALLEST stack on the board, height H at (c, r), and try
            # moving all H of it diagonally forward.  If that destination is off
            # the board it is a legal bear-off; if it is on the board it is
            # empty (legal move), friendly (legal merge) or enemy of height
            # <= H (legal capture, since H is the maximum) -- and a diagonal
            # destination is always a dark square, so parity never blocks it.
            # So the owner of a maximal stack ALWAYS has a move, which is
            # exactly Steere's "there will always be a move available to one
            # player or the other".  Kept anyway as an honest DRAW rather than a
            # fabricated winner, in case the argument is ever invalidated.
            ns.over, ns.winner = True, None
            return ns

        if ns.ply >= ply_cap(s.size):            # provably dead backstop
            ns.over, ns.winner = True, None
        return ns

    def is_terminal(self, state):
        return state.over

    def returns(self, state):
        if not state.over or state.winner is None:
            return [0, 0]
        return [1 if p == state.winner else -1 for p in range(2)]

    # --------------------------------------------------------------- bot
    def heuristic(self, state):
        """Material is king (you lose by running out); a little credit for
        keeping checkers far from your own exit edge, i.e. having room left."""
        mat = {WHITE: 0, BLACK: 0}
        room = {WHITE: 0.0, BLACK: 0.0}
        size = state.size
        for (c, r), (o, h) in state.board.items():
            mat[o] += h
            room[o] += h * ((size - 1 - r) if o == WHITE else r)
        v = (mat[WHITE] - mat[BLACK]) + 0.08 * (room[WHITE] - room[BLACK])
        x = math.tanh(v / 6.0)
        return [x, -x]

    # ------------------------------------------------------- (de)serialize
    def serialize(self, state):
        return {
            "size": state.size,
            "board": {f"{c},{r}": [o, h] for (c, r), (o, h) in sorted(state.board.items())},
            "to_move": state.to_move,
            "ply": state.ply,
            "last": state.last,
            "over": state.over,
            "winner": state.winner,
        }

    def deserialize(self, data):
        return DState(
            size=int(data["size"]),
            board={_cell(k): (int(v[0]), int(v[1])) for k, v in data["board"].items()},
            to_move=int(data["to_move"]),
            ply=int(data["ply"]),
            last=data["last"],
            over=bool(data["over"]),
            winner=(None if data["winner"] is None else int(data["winner"])),
        )

    # ------------------------------------------------------------- notation
    def describe_move(self, state, move):
        frm, to, k = self.parse(move)
        who = NAMES[state.to_move]
        if to is None:
            return f"{who} {alg(*frm)} bears off {k}"
        occ = state.board.get(to)
        if occ is None:
            return f"{who} {alg(*frm)}-{alg(*to)} ({k})"
        if occ[0] == state.to_move:
            return f"{who} {alg(*frm)}+{alg(*to)} ({k}, merge to {occ[1] + k})"
        return f"{who} {alg(*frm)}x{alg(*to)} ({k}, takes {occ[1]})"

    # --------------------------------------------------------------- render
    def render(self, state, perspective=None):
        size = state.size
        pieces = []
        for (c, r), (o, h) in sorted(state.board.items()):
            pieces.append({"cell": f"{c},{r}", "owner": o, "stack": [o] * h})
        # Explicit checkerboard tints: only the dark squares are in play, and
        # the renderer's built-in shading is deliberately subtle.  The PLAYABLE
        # tint has to stay well clear of Board.jsx's fixed "last-move" fill
        # (#3a3228): the first colour tried here, #3b352a, matched it to within
        # a 1.04:1 contrast ratio, so the last-move highlight was invisible on
        # the only squares a move can ever touch.  selftest.py asserts the gap.
        tints = {}
        for r in range(size):
            for c in range(size):
                tints[f"{c},{r}"] = "#514734" if (c + r) % 2 == 0 else "#201d17"

        highlights = []
        if state.last:
            frm, to, _k = self.parse(state.last)
            highlights.append({"cell": f"{frm[0]},{frm[1]}", "kind": "last-move"})
            if to is not None:
                highlights.append({"cell": f"{to[0]},{to[1]}", "kind": "last-move"})

        counts = {WHITE: 0, BLACK: 0}
        for (o, h) in state.board.values():
            counts[o] += h
        tally = f"White {counts[WHITE]} - Black {counts[BLACK]}"
        if state.over:
            cap = (f"{NAMES[state.winner]} wins" if state.winner is not None
                   else "Draw") + f"  ({tally})"
        else:
            cap = f"{NAMES[state.to_move]} to move  ({tally})"
            # If the opponent is sitting out, say so -- otherwise the same seat
            # appearing twice in a row in the move log looks like a bug.
            if not self._has_move(state, 1 - state.to_move):
                cap += f" -- {NAMES[1 - state.to_move]} has no legal move"

        spec = {
            "board": {"type": "square", "width": size, "height": size, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
        # Bear-offs have no destination square, so they render as action buttons.
        names = {}
        for m in (self.legal_moves(state) if not state.over else []):
            if ">off=" in m:
                frm, _to, k = self.parse(m)
                names[m] = f"{alg(*frm)}: bear off {k}"
        if names:
            spec["actionNames"] = names
        return spec
