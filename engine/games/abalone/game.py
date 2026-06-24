"""Abalone, by Michel Lalet & Laurent Levi (1987).

A push-the-marbles ("sumito") game on a hexagon-of-hexes ("hexhex") of side 5
(61 cells). Each player has 14 marbles. Axial coordinates (q, r); the third cube
coordinate is s = -q-r, and a cell is on the board iff
max(|q|, |r|, |q+r|) <= 4. Adjacency is the 6 hex neighbours.

A move slides an in-line group of 1, 2, or 3 of your OWN adjacent marbles one
step, in one of two ways:

  * IN-LINE move (along the group's own axis): the group steps one cell forward.
    The lead cell must be EMPTY, OR a SUMITO (push): the cells ahead hold a
    SHORTER line of enemy marbles (2-push-1, 3-push-1, or 3-push-2 only) and the
    cell immediately behind the enemy line is EMPTY or OFF-BOARD. The enemy line
    is shoved one cell; an enemy pushed off the edge is EJECTED (captured).
  * BROADSIDE / side-step move (perpendicular to the group's axis): a group of
    2 or 3 in-line marbles all step one cell in a non-line direction. Every
    destination must be EMPTY (no pushing on a broadside).

WIN: eject 6 of the opponent's marbles (stored as a ``winner`` event).

Move encoding (a ``>``-separated cell path so the generic click UI can drive it):
the group's source cells in CANONICAL SORTED order, followed by the destination
cell of the FIRST (lowest-sorted) source marble. A single marble is
``"src>dst"``. apply_move reconstructs the full move (group + direction +
in-line/broadside + push) from that path. See rules.md.

Termination safeguard (non-original): a no-progress draw after PLY_NOPROGRESS
plies with no ejection, plus a hard ply cap, so random play always terminates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1
NAMES = {BLACK: "Black", WHITE: "White"}

N = 4                     # extreme axial coordinate magnitude -> side-5, 61 cells
WIN_EJECTIONS = 6         # eject this many enemy marbles to win
PLY_NOPROGRESS = 200      # draw after this many plies with no ejection (safeguard)
PLY_CAP = 4000            # absolute hard ply cap -> draw (safeguard)

# 6 hex-neighbour directions (axial).
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

# The 3 unordered axes (each a direction and its opposite). A group of marbles
# lies along one of these axes; an in-line move goes along that axis, a broadside
# move along either of the other two.
AXES = [(1, 0), (0, 1), (1, -1)]


def _onboard(q: int, r: int) -> bool:
    return max(abs(q), abs(r), abs(q + r)) <= N


@lru_cache(maxsize=None)
def _all_cells() -> tuple:
    """All 61 on-board axial cells of the side-5 hexhex."""
    return tuple(
        (q, r)
        for q in range(-N, N + 1)
        for r in range(-N, N + 1)
        if _onboard(q, r)
    )


def _add(c, d):
    return (c[0] + d[0], c[1] + d[1])


def _cell(s: str) -> tuple:
    q, r = s.split(",")
    return int(q), int(r)


def _cstr(c) -> str:
    return f"{c[0]},{c[1]}"


@lru_cache(maxsize=None)
def standard_start() -> tuple:
    """The STANDARD Abalone opening: two armies facing across the board.

    Returns (black_cells, white_cells) as sorted tuples. Black fills its back two
    rows (r=-4: 5 cells, r=-3: 6 cells) plus the middle 3 cells of r=-2; White is
    the 180-degree rotation (r=4, r=3, and middle 3 of r=2). 14 marbles each.
    """
    from collections import defaultdict

    rows = defaultdict(list)
    for q, r in _all_cells():
        rows[r].append(q)
    for r in rows:
        rows[r].sort()

    def middle3(r):
        qs = rows[r]
        m = len(qs) // 2
        return qs[m - 1:m + 2]

    black = (
        [(q, -4) for q in rows[-4]]
        + [(q, -3) for q in rows[-3]]
        + [(q, -2) for q in middle3(-2)]
    )
    white = [(-q, -r) for (q, r) in black]  # 180-degree rotation
    return tuple(sorted(black)), tuple(sorted(white))


@dataclass
class AbaloneState:
    board: dict = field(default_factory=dict)   # (q, r) -> 0/1
    to_move: int = BLACK
    ejected: tuple = (0, 0)                       # marbles each player has LOST
    winner: Optional[int] = None
    last: tuple = ()                              # cells touched by the last move (for highlight)
    ply: int = 0
    no_progress: int = 0                          # plies since the last ejection


def _line_cells(start, d, k):
    """k cells starting at ``start`` stepping by direction ``d``."""
    out, c = [], start
    for _ in range(k):
        out.append(c)
        c = _add(c, d)
    return out


def _decode_group(board, src_cells):
    """Validate that ``src_cells`` (a sorted list) is an in-line group of 1-3 of
    the side-to-move's marbles, all the same owner. Returns (owner, axis) where
    axis is the unit step between consecutive cells (None for a single marble),
    or None if the cells are not a contiguous in-line same-owner group."""
    if not (1 <= len(src_cells) <= 3):
        return None
    owners = {board.get(c) for c in src_cells}
    if len(owners) != 1 or None in owners:
        return None
    owner = next(iter(owners))
    if len(src_cells) == 1:
        return owner, None
    # All consecutive cells must differ by the same unit hex direction.
    d = (src_cells[1][0] - src_cells[0][0], src_cells[1][1] - src_cells[0][1])
    if d not in DIRS:
        return None
    for i in range(1, len(src_cells)):
        if (src_cells[i][0] - src_cells[i - 1][0],
                src_cells[i][1] - src_cells[i - 1][1]) != d:
            return None
    return owner, d


def _axis_of(d):
    """Unordered axis key for a direction d (so d and -d share an axis)."""
    return d if d in AXES else (-d[0], -d[1])


class Abalone(Game):
    uid = "abalone"
    name = "Abalone"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AbaloneState:
        black, white = standard_start()
        board = {}
        for c in black:
            board[c] = BLACK
        for c in white:
            board[c] = WHITE
        return AbaloneState(board=board, to_move=BLACK)

    def current_player(self, s: AbaloneState) -> int:
        return s.to_move

    # ---- move generation -------------------------------------------------

    def _gen_moves(self, s: AbaloneState):
        """Yield (path_str, result_state-info) — we yield the canonical encoding
        strings; apply_move re-derives the effect. Here we just enumerate every
        legal move and return its encoding."""
        board = s.board
        me = s.to_move
        moves = []
        # Enumerate every contiguous in-line group of 1, 2, 3 own marbles.
        groups = []  # each: (sorted_cells_tuple, axis_dir_or_None)
        mine = [c for c, p in board.items() if p == me]
        mine_set = set(mine)
        # singles
        for c in mine:
            groups.append(((c,), None))
        # 2- and 3-groups along each axis (canonicalised so we don't double count)
        for axis in AXES:
            for c in mine:
                # build forward run along +axis starting at c, but only count a
                # group whose lowest cell (in our sort) is c so each group is unique
                for length in (2, 3):
                    cells = _line_cells(c, axis, length)
                    if all(x in mine_set for x in cells):
                        scells = tuple(sorted(cells))
                        # ensure c is the canonical anchor (min) so no duplicates
                        if scells[0] == c:
                            groups.append((scells, axis))

        for scells, axis in groups:
            anchor = scells[0]
            for d in DIRS:
                effect = self._try_move(board, me, scells, axis, d)
                if effect is None:
                    continue
                dst = _add(anchor, d)
                path = ">".join(_cstr(x) for x in scells) + ">" + _cstr(dst)
                moves.append(path)
        return moves

    def _try_move(self, board, me, scells, axis, d):
        """Return a description of the legal move (group, direction, pushed list)
        if moving ``scells`` (a sorted same-owner in-line group, axis=axis) by
        direction ``d`` is legal, else None.

        Returns dict: {kind, group, dir, pushed:[enemy cells in push order]}.
        """
        opp = 1 - me
        group = set(scells)
        if axis is None:
            # single marble: any of 6 dirs; in-line/broadside distinction is moot.
            dst = _add(scells[0], d)
            if not _onboard(*dst):
                return None
            if board.get(dst) is None:
                return {"kind": "step", "pushed": []}
            # a single marble can never push (would be 1v1 or worse)
            return None

        in_line = _axis_of(d) == _axis_of(axis)
        if in_line:
            # Determine the leading marble (frontmost in direction d).
            # The group occupies scells along axis; the lead cell in dir d is the
            # extreme cell when stepping +d.
            # Pick the cell c in group maximizing projection along d.
            lead = max(group, key=lambda c: c[0] * d[0] + c[1] * d[1])
            front = _add(lead, d)
            if not _onboard(*front):
                return None  # can't push self off / move group off
            occ = board.get(front)
            if occ is None:
                return {"kind": "inline", "pushed": []}
            if occ == me:
                return None  # blocked by own marble
            # SUMITO: count consecutive enemy marbles ahead.
            enemy = []
            c = front
            while _onboard(*c) and board.get(c) == opp:
                enemy.append(c)
                c = _add(c, d)
            # must be strictly fewer enemies than our group size
            if len(enemy) >= len(group):
                return None
            # cell immediately behind the enemy line must be empty or off-board
            behind = _add(enemy[-1], d)
            if _onboard(*behind) and board.get(behind) is not None:
                return None  # blocked (own or enemy) -> illegal push
            return {"kind": "push", "pushed": enemy}
        else:
            # BROADSIDE: only for 2- or 3-groups (axis not None guarantees >=2).
            # every marble steps by d; all destinations must be EMPTY & on-board.
            for c in group:
                dst = _add(c, d)
                if not _onboard(*dst) or board.get(dst) is not None:
                    return None
            return {"kind": "broadside", "pushed": []}

    def legal_moves(self, s: AbaloneState):
        if self.is_terminal(s):
            return []
        return self._gen_moves(s)

    # ---- applying a move -------------------------------------------------

    def _parse_path(self, board, me, move: str):
        """Reconstruct (scells, axis, d, effect) from an encoded path, validating
        it is legal. Raises ValueError if not."""
        parts = move.split(">")
        if len(parts) < 2:
            raise ValueError(f"bad move {move!r}")
        cells = [_cell(p) for p in parts]
        dst = cells[-1]
        scells = tuple(sorted(cells[:-1]))
        if list(scells) != cells[:-1]:
            raise ValueError(f"group not in canonical sorted order: {move!r}")
        dec = _decode_group(board, list(scells))
        if dec is None:
            raise ValueError(f"not an in-line own group: {move!r}")
        owner, axis = dec
        if owner != me:
            raise ValueError(f"not your group: {move!r}")
        anchor = scells[0]
        d = (dst[0] - anchor[0], dst[1] - anchor[1])
        if d not in DIRS:
            raise ValueError(f"destination not adjacent to anchor: {move!r}")
        effect = self._try_move(board, me, scells, axis, d)
        if effect is None:
            raise ValueError(f"illegal move {move!r}")
        return scells, axis, d, effect

    def apply_move(self, s: AbaloneState, move: str, rng=None) -> AbaloneState:
        me = s.to_move
        scells, axis, d, effect = self._parse_path(s.board, me, move)
        board = dict(s.board)
        ejected = list(s.ejected)
        touched = []

        # Move pushed enemy marbles first (from the rear forward so cells are
        # vacated correctly). pushed list is front->back along d.
        opp = 1 - me
        ejected_now = 0
        for ec in reversed(effect["pushed"]):
            board.pop(ec)
        for ec in effect["pushed"]:
            nc = _add(ec, d)
            if _onboard(*nc):
                board[nc] = opp
            else:
                ejected_now += 1  # shoved off the board
            touched.append(nc)

        # Now move our group: remove all, then place shifted by d.
        for c in scells:
            board.pop(c)
        for c in scells:
            nc = _add(c, d)
            board[nc] = me
            touched.append(nc)

        if ejected_now:
            ejected[opp] += ejected_now

        winner = None
        if ejected[opp] >= WIN_EJECTIONS:
            winner = me

        no_progress = 0 if ejected_now else s.no_progress + 1
        return AbaloneState(
            board=board,
            to_move=1 - me,
            ejected=tuple(ejected),
            winner=winner,
            last=tuple(touched),
            ply=s.ply + 1,
            no_progress=no_progress,
        )

    def is_terminal(self, s: AbaloneState) -> bool:
        if s.winner is not None:
            return True
        if s.no_progress >= PLY_NOPROGRESS:
            return True
        if s.ply >= PLY_CAP:
            return True
        return False

    def returns(self, s: AbaloneState):
        if s.winner == BLACK:
            return [1.0, -1.0]
        if s.winner == WHITE:
            return [-1.0, 1.0]
        return [0.0, 0.0]  # draw (no-progress / ply-cap safeguard)

    # ---- serialization ---------------------------------------------------

    def serialize(self, s: AbaloneState) -> dict:
        return {
            "board": {_cstr(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "ejected": list(s.ejected),
            "winner": s.winner,
            "last": [_cstr(c) for c in s.last],
            "ply": s.ply,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> AbaloneState:
        return AbaloneState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ejected=tuple(d.get("ejected", [0, 0])),
            winner=d.get("winner"),
            last=tuple(_cell(c) for c in d.get("last", [])),
            ply=d.get("ply", 0),
            no_progress=d.get("no_progress", 0),
        )

    # ---- presentation ----------------------------------------------------

    def describe_move(self, s: AbaloneState, move: str) -> str:
        try:
            scells, axis, d, effect = self._parse_path(s.board, s.to_move, move)
        except ValueError:
            return move
        dirname = {
            (1, 0): "E", (-1, 0): "W", (0, 1): "SE", (0, -1): "NW",
            (1, -1): "NE", (-1, 1): "SW",
        }.get(d, str(d))
        grp = "+".join(_cstr(c) for c in scells)
        kind = effect["kind"]
        if kind == "push":
            n = len(effect["pushed"])
            # detect potential ejection
            behind = _add(effect["pushed"][-1], d)
            eject = "" if _onboard(*behind) else " EJECT"
            return f"{grp} push {n} {dirname}{eject}"
        if kind == "broadside":
            return f"{grp} broadside {dirname}"
        return f"{grp} {dirname}"

    def render(self, s: AbaloneState, perspective=None) -> dict:
        pieces = [
            {"cell": _cstr(c), "owner": p, "label": ""}
            for c, p in s.board.items()
        ]
        highlights = [{"cell": _cstr(c), "kind": "last-move"} for c in s.last]
        # ejected[p] = marbles player p has LOST; show captures (Black-White).
        score = f"(ejected {s.ejected[1]}-{s.ejected[0]})"
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins {score}"
        elif self.is_terminal(s):
            caption = f"Draw {score}"
        else:
            caption = f"{NAMES[s.to_move]} to move  {score}"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": 5},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
