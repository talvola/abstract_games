"""Redstone -- Mark Steere (February 2012).

A Go variant in which all captures are made with shared, permanent RED stones.
Implemented from the author's rule sheet (marksteeregames.com/Redstone_rules.pdf):

* Black and White alternate placing one stone per turn on an empty point of a
  square grid; each also has access to an unlimited shared supply of red stones.
* A group = orthogonally connected like-coloured (black or white) stones; red
  stones never form groups and are never removed. A liberty is an empty point
  adjacent to a group.
* A placement that leaves one or more (black or white) groups with no liberties
  is a *capturing placement* and may only be made with a RED stone; conversely a
  red stone may only be placed if it bounds (deprives of all liberties) at least
  one group of either or both colours.  All bounded groups are removed
  immediately and simultaneously -- unlike Go, a group of your own that is only
  *temporarily* bounded (it would regain liberties once a neighbouring enemy
  group is lifted) is still removed (Fig. 3 of the sheet). Self-capture is
  allowed.
* No passing; draws cannot occur; positions cannot repeat (red stones are
  permanent, so no ko/superko rule is needed).
* You win by removing all enemy stones from the board.  If your placement
  removes every black AND white stone, you (the mover) win; if it removes all
  of your own stones while enemy stones remain, you lose.
* Pie rule: on move 2 White may "swap" instead of placing, taking over Black's
  opening stone.

Move encoding: ``"c,r=black"`` / ``"c,r=white"`` (a stone of your own colour --
seat 0 is Black, seat 1 is White), ``"c,r=red"`` (a shared red stone), plus
``"swap"``.  The ``=colour`` choice-suffix means the generic UI auto-plays the
single option on a click and opens a Black-or-Red picker only on the (rare)
points where both are legal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

BLACK, WHITE, RED = 0, 1, 2
COLOUR_NAME = {BLACK: "black", WHITE: "white", RED: "red"}
NAME_COLOUR = {v: k for k, v in COLOUR_NAME.items()}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _neighbors(c, r, size):
    if c > 0:
        yield (c - 1, r)
    if c < size - 1:
        yield (c + 1, r)
    if r > 0:
        yield (c, r - 1)
    if r < size - 1:
        yield (c, r + 1)


def _groups(board, size):
    """All black/white groups: list of (colour, cells frozenset, liberties frozenset).
    Red stones are not groups and only block liberties."""
    seen = set()
    out = []
    for pt, col in board.items():
        if col == RED or pt in seen:
            continue
        cells = {pt}
        stack = [pt]
        libs = set()
        while stack:
            c, r = stack.pop()
            for nb in _neighbors(c, r, size):
                v = board.get(nb)
                if v is None:
                    libs.add(nb)
                elif v == col and nb not in cells:
                    cells.add(nb)
                    stack.append(nb)
        seen |= cells
        out.append((col, frozenset(cells), frozenset(libs)))
    return out


def _point_moves(board, size, mover, groups=None):
    """Yield (point, is_red) for every legal placement by `mover`.

    Own-colour stone at p: legal iff NO group ends up bounded -- i.e. no
    adjacent enemy group has p as its only liberty, and the merged own group
    (adjacent own groups + the new stone) still has a liberty.
    Red stone at p: legal iff at least one adjacent (black or white) group has
    p as its only liberty.
    """
    if groups is None:
        groups = _groups(board, size)
    # index groups by their liberty points for O(1) adjacency lookups
    by_lib = {}
    for gi, (_col, _cells, libs) in enumerate(groups):
        for lb in libs:
            by_lib.setdefault(lb, []).append(gi)
    enemy = 1 - mover
    for r in range(size):
        for c in range(size):
            p = (c, r)
            if p in board:
                continue
            adj = by_lib.get(p, ())
            # red: bounds >=1 group whose only liberty is p
            if any(groups[gi][2] == frozenset((p,)) for gi in adj):
                yield p, True
            # own stone: no enemy group bounded, merged own group keeps a liberty
            if any(groups[gi][0] == enemy and groups[gi][2] == frozenset((p,))
                   for gi in adj):
                continue
            merged_libs = {nb for nb in _neighbors(c, r, size) if nb not in board}
            for gi in adj:
                if groups[gi][0] == mover:
                    merged_libs |= set(groups[gi][2])
            merged_libs.discard(p)
            if merged_libs:
                yield p, False


@dataclass
class RState:
    size: int = 9
    board: dict = field(default_factory=dict)   # {(c,r): BLACK|WHITE|RED}
    to_move: int = BLACK
    ply: int = 0
    winner: object = None                       # None | 0 | 1
    last_move: object = None                    # (c,r) | "swap" | None
    swapped: bool = False


class Redstone(Game):
    uid = "redstone"
    name = "Redstone"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        size = int((options or {}).get("size", 9))
        return RState(size=size)

    def current_player(self, s):
        return s.to_move

    def is_terminal(self, s):
        return s.winner is not None

    def _has_any_move(self, board, size, mover):
        return next(iter(_point_moves(board, size, mover)), None) is not None

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        moves = []
        for (c, r), is_red in _point_moves(s.board, s.size, s.to_move):
            colour = "red" if is_red else COLOUR_NAME[s.to_move]
            moves.append(f"{c},{r}={colour}")
        if s.ply == 1 and not s.swapped:
            moves.append("swap")                # pie rule: White's first turn
        return moves

    def apply_move(self, s, move, rng=None):
        if move == "swap":
            # Pie rule: White takes over Black's opening stone (colours are
            # otherwise symmetric, so recolouring the lone stone = swapping).
            board = {pt: WHITE for pt in s.board}
            return RState(size=s.size, board=board, to_move=BLACK,
                          ply=s.ply + 1, winner=None, last_move="swap",
                          swapped=True)
        cellpart, _, colourname = move.partition("=")
        c, r = _cell(cellpart)
        colour = NAME_COLOUR[colourname]
        board = dict(s.board)
        winner = None
        if colour == RED:
            # remove every group whose only liberty was (c,r) -- simultaneously,
            # own and enemy alike (the "unlike Go" rule)
            p = (c, r)
            doomed = set()
            for _col, cells, libs in _groups(s.board, s.size):
                if libs == frozenset((p,)):
                    doomed |= cells
            board[p] = RED
            for pt in doomed:
                del board[pt]
            mine = sum(1 for v in board.values() if v == s.to_move)
            theirs = sum(1 for v in board.values() if v == 1 - s.to_move)
            if theirs == 0:
                winner = s.to_move            # incl. both-annihilated: mover wins
            elif mine == 0:
                winner = 1 - s.to_move        # removed only your own army: lose
        else:
            board[(c, r)] = colour            # never removes anything (legality)
        nxt = 1 - s.to_move
        if winner is None and not self._has_any_move(board, s.size, nxt):
            # Defensive backstop -- the rule sheet states a placement is always
            # available ("Players will always have a placement available and
            # must make one"), so this should be unreachable; if it ever fires,
            # the player unable to move loses (Steere's standard convention).
            winner = s.to_move
        return RState(size=s.size, board=board, to_move=nxt, ply=s.ply + 1,
                      winner=winner, last_move=(c, r), swapped=s.swapped)

    def returns(self, s):
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]                     # unreachable: Redstone has no draws

    def heuristic(self, s):
        """Material + atari pressure, from Black's perspective. Per-seat list."""
        import math
        if s.winner is not None:
            return self.returns(s)
        b = sum(1 for v in s.board.values() if v == BLACK)
        w = sum(1 for v in s.board.values() if v == WHITE)
        b_atari = w_atari = 0
        for col, _cells, libs in _groups(s.board, s.size):
            if len(libs) == 1:
                if col == BLACK:
                    b_atari += 1
                else:
                    w_atari += 1
        v = math.tanh(0.2 * (b - w) + 0.35 * (w_atari - b_atari))
        return [v, -v]

    def serialize(self, s):
        lm = s.last_move
        return {
            "size": s.size,
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
            "last_move": ("swap" if lm == "swap" else (list(lm) if lm else None)),
            "swapped": s.swapped,
        }

    def deserialize(self, d):
        lm = d.get("last_move")
        return RState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
            last_move=("swap" if lm == "swap" else (tuple(lm) if lm else None)),
            swapped=d.get("swapped", False),
        )

    def describe_move(self, s, move):
        if move == "swap":
            return "swap (pie)"
        cellpart, _, colourname = move.partition("=")
        c, r = _cell(cellpart)
        letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"   # Go convention skips I
        col = letters[c] if c < len(letters) else str(c)
        tag = {"black": "B", "white": "W", "red": "red"}[colourname]
        return f"{tag} {col}{s.size - r}"

    def render(self, s, perspective=None):
        names = {BLACK: "Black", WHITE: "White"}
        pieces = []
        for (c, r), v in s.board.items():
            if v == RED:
                pieces.append({"cell": f"{c},{r}", "owner": 0,
                               "fill": "#d93025", "stroke": "#8c1a12"})
            else:
                pieces.append({"cell": f"{c},{r}", "owner": v, "label": ""})
        highlights = []
        if isinstance(s.last_move, tuple):
            highlights.append({"cell": f"{s.last_move[0]},{s.last_move[1]}",
                               "kind": "last-move"})
        b = sum(1 for v in s.board.values() if v == BLACK)
        w = sum(1 for v in s.board.values() if v == WHITE)
        if s.winner is not None:
            caption = f"{names[s.winner]} wins by annihilation"
        else:
            caption = (f"{names[s.to_move]} to move  ·  "
                       f"stones B {b} / W {w}"
                       + ("  ·  swapped" if s.swapped else ""))
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "choiceTitle": "Place",
            "choiceNames": {"black": "Black stone", "white": "White stone",
                            "red": "Red stone"},
        }
