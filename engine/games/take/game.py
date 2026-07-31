"""Take — Mark Steere, February 2024.  A "free-form Tanbo" on a hexhex board.

The board is a regular hexagon of hexagonal cells ("hexhex") of side ``size``,
initially **completely filled with clods** — neutral brown stones belonging to
neither player.  Red and Blue alternately place one stone of their own colour.

Placement (Steere's PLAY paragraph, verified against Figure 1):

* A **seed** is a stone with no friendly neighbour.  A seed may be placed
  **only on a clod-occupied cell**, removing the clod.
* Any other stone may be placed on **any unoccupied or clod-occupied cell**
  (removing the clod) so long as it forms **exactly one** adjacency with a
  friendly stone.

So the legality test on a cell that holds no stone is::

    clod-occupied cell  ->  friendly-neighbour count <= 1   (0 = seed, 1 = growth)
    bare (clod-free)    ->  friendly-neighbour count == 1   (growth only)

A **group** is a maximal connected set of same-coloured stones.  Because every
non-seed placement touches exactly one friendly stone, groups never merge and
every group is connected; a seed starts a brand new group.

A group is **BOUNDED** when it cannot be expanded by the placement of an
adjacent like-coloured stone.  Spelled out: group ``G`` of colour ``c`` is
bounded iff **no** stone-free cell adjacent to ``G`` has exactly one
``c``-coloured neighbour on the whole board.  (For a cell adjacent to ``G`` the
count is already >= 1, so the "clod: <= 1" and "bare: == 1" tests collapse to
the same thing — the clod/bare distinction is irrelevant to boundedness and
matters only for seeds.  ``selftest.py`` asserts that collapse rather than
assuming it.)

**Group removal.**  After your placement, every bounded group of *either*
colour — including the group your own stone just joined or created — is removed
**simultaneously** (all bounded groups are identified on the post-placement
board, then all are cleared at once).  Unlike Tanbo there is **no current-root
precedence**: your own doomed group does not shield the opponent's.

**Object.**  Remove all enemy stones.  If your placement eliminates all red and
blue stones you win; if it eliminates all friendly stones while enemy stones
remain, you lose.

**High Churn variant.**  Each cell starts covered by a brown *tile* rather than
a brown stone.  A seed still removes the tile it lands on, but a non-seed stone
placed on a tiled cell sits **on top of** the tile — so when that stone is later
removed the tile is still there.  Tiles therefore deplete far more slowly, seeds
stay available much longer, and the board churns.  Everything else is identical.
(Verified against Figures 3a/3b, where the removed blue group's cells revert to
bare tiles.)

TERMINATION — a monovariant, no ply cap, no repetition rule
-----------------------------------------------------------
Let ``K`` = number of clods/tiles still on the board, ``G`` = number of groups,
``U`` = number of stone-free cells.  The triple ``(K, G, U)`` **strictly
decreases lexicographically on every single ply**:

* a placement that consumes a clod/tile lowers ``K``;
* every other placement is a non-seed on a cell that keeps (or never had) a
  clod, so ``K`` is unchanged and no new group is created.  If the ply removes
  any group, ``G`` drops; if it removes none, a stone was added, so ``U`` drops.

Since ``0 <= K, G, U <= C`` (``C`` = cell count), play is finite, with the
crude derived bound ``(C + 1) ** 3`` plies.  See ``PLY_BOUND`` below — it is
computed from the board, never pinned, and it is *not* used as a cap: the game
declares no ply cap at all.

NO STUCK POSITION — no draw exists
----------------------------------
Removing bounded groups can never bound a *surviving* group: if ``X`` witnessed
that ``G`` can grow (``X`` stone-free, exactly one ``c``-neighbour, and that
neighbour lies in ``G``), then after the sweep ``X`` is still stone-free and its
single ``c``-neighbour — a stone of ``G``, which was not removed — is still
there.  So at the start of every turn **no group is bounded**, and a player who
still owns a group therefore always has at least one legal placement.  A player
who owns no group has already lost (or the game has already ended).  The only
turns with no friendly stone on the board are plies 1 and 2, when the board is
still awash with clods and every cell is a legal seed.  Hence ``legal_moves``
is never empty on a non-terminal state and the game can never be drawn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# Board side lengths offered by the manifest.  Every figure of the rule sheet
# uses side 3 (19 cells); AbstractPlay's default is side 5 (61 cells), which is
# this package's default too.
SIZES = (2, 3, 4, 5, 6)

SEAT_NAMES = ("Red", "Blue")

# Axial neighbour offsets.  Pointy-top rendering (a *row*, constant r, is
# horizontal) — exactly how the rule sheet draws every figure: the SVG cell
# outlines in Take_rules.pdf are 21.13 wide by 24.40 tall, i.e. vertex-up.
DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))

# Cell fill for a clod / High-Churn tile.  Clods are rendered as a brown CELL
# TINT rather than as a neutral brown disc: a cell carrying a `piece` suppresses
# the renderer's legal-move dot, and in Take almost every legal placement lands
# on a clod, so a disc would hide the move hints on the cells that need them
# most.  It also makes the two variants read consistently — a brown cell means
# "there is brown stuff here", with the stone drawn on top in High Churn.
CLOD_TINT = "#6b4423"


def _cell(text: str):
    q, r = text.split(",")
    return int(q), int(r)


def _name(c) -> str:
    return f"{c[0]},{c[1]}"


@dataclass(frozen=True)
class BoardSpec:
    size: int
    cells: tuple            # every cell, sorted, deterministic
    cellset: frozenset
    nbrs: dict              # cell -> tuple of on-board neighbours


_SPECS: dict = {}


def spec_for(size: int) -> BoardSpec:
    n = int(size)
    if n in _SPECS:
        return _SPECS[n]
    if n < 2:
        raise ValueError(f"board side must be at least 2 (got {n})")
    cells = tuple(sorted(
        (q, r)
        for q in range(-(n - 1), n)
        for r in range(-(n - 1), n)
        if abs(q + r) <= n - 1
    ))
    cellset = frozenset(cells)
    nbrs = {c: tuple(d for d in ((c[0] + dq, c[1] + dr) for dq, dr in DIRS)
                     if d in cellset)
            for c in cells}
    sp = BoardSpec(size=n, cells=cells, cellset=cellset, nbrs=nbrs)
    _SPECS[n] = sp
    return sp


@dataclass(frozen=True)
class TakeState:
    size: int
    churn: bool                       # True = High Churn variant
    stones: dict = field(default_factory=dict)     # cell -> seat (0 Red, 1 Blue)
    clods: frozenset = frozenset()                 # cells holding a clod / tile
    to_move: int = 0
    winner: Optional[int] = None
    last: Optional[tuple] = None                   # last placed cell
    removed: tuple = ()                            # cells cleared by that ply
    plies: int = 0


# --------------------------------------------------------------------------- #
# Board predicates.  All of these take the plain (stones, nbrs) pair so the
# selftest can drive them on constructed positions.
# --------------------------------------------------------------------------- #

def ally_count(stones: dict, nbrs: dict, cell, seat: int) -> int:
    """How many stones of `seat` sit next to `cell`."""
    return sum(1 for y in nbrs[cell] if stones.get(y) == seat)


def placeable(stones: dict, clods, nbrs: dict, cell, seat: int) -> bool:
    """Is placing a `seat` stone on `cell` legal?  (Steere's PLAY paragraph.)"""
    if cell in stones:
        return False
    n = ally_count(stones, nbrs, cell, seat)
    if cell in clods:
        return n <= 1            # 0 = seed (removes the clod), 1 = growth
    return n == 1                # a bare cell can never take a seed


def groups(stones: dict, nbrs: dict) -> list:
    """All maximal same-colour connected groups as (seat, [cells])."""
    seen = set()
    out = []
    for c in sorted(stones):
        if c in seen:
            continue
        col = stones[c]
        comp = []
        stack = [c]
        seen.add(c)
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in nbrs[x]:
                if y not in seen and stones.get(y) == col:
                    seen.add(y)
                    stack.append(y)
        out.append((col, sorted(comp)))
    return out


def is_bounded(stones: dict, nbrs: dict, comp, seat: int) -> bool:
    """A group is bounded when no like-coloured stone can be placed next to it.

    Only cells adjacent to the group can expand it, and such a cell already has
    at least one `seat` neighbour — so the clod-vs-bare distinction collapses to
    "exactly one friendly neighbour".  `clods` is deliberately not a parameter.
    """
    for x in comp:
        for y in nbrs[x]:
            if y not in stones and ally_count(stones, nbrs, y, seat) == 1:
                return False
    return True


class TakeGame(Game):
    """Take (Mark Steere, 2024)."""

    # ------------------------------------------------------------------ core

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TakeState:
        o = options or {}
        size = int(o.get("size", 5))
        if size not in SIZES:
            raise ValueError(f"unsupported board size {size!r}")
        churn = o.get("churn", "standard")
        if isinstance(churn, bool):
            churn = "high" if churn else "standard"
        churn = str(churn).lower()
        if churn not in ("standard", "high"):
            raise ValueError(f"unsupported variant {churn!r}")
        sp = spec_for(size)
        return TakeState(size=size, churn=(churn == "high"),
                         stones={}, clods=frozenset(sp.cells), to_move=0)

    def current_player(self, s: TakeState) -> int:
        return s.to_move

    def legal_moves(self, s: TakeState) -> list:
        if s.winner is not None:
            return []
        sp = spec_for(s.size)
        return [_name(c) for c in sp.cells
                if placeable(s.stones, s.clods, sp.nbrs, c, s.to_move)]

    def apply_move(self, s: TakeState, move: str, rng=None) -> TakeState:
        sp = spec_for(s.size)
        cell = _cell(move)
        if cell not in sp.cellset:
            raise ValueError(f"cell {move!r} is off the board")
        if s.winner is not None:
            raise ValueError("the game is over")
        if not placeable(s.stones, s.clods, sp.nbrs, cell, s.to_move):
            raise ValueError(f"illegal placement {move!r}")

        seat = s.to_move
        other = 1 - seat
        before_other = sum(1 for v in s.stones.values() if v == other)

        seeding = ally_count(s.stones, sp.nbrs, cell, seat) == 0

        stones = dict(s.stones)
        stones[cell] = seat

        clods = s.clods
        if cell in clods and (seeding or not s.churn):
            # Base game: any placement on a clod cell removes the clod.
            # High Churn: only a SEED removes the tile; a growth stone sits on
            # top of it and the tile survives the stone's later removal.
            clods = clods - {cell}

        # Identify every bounded group on the post-placement board FIRST, then
        # clear them all — the removals are simultaneous.
        doomed = []
        for col, comp in groups(stones, sp.nbrs):
            if is_bounded(stones, sp.nbrs, comp, col):
                doomed.extend(comp)
        for c in doomed:
            del stones[c]

        after_mine = sum(1 for v in stones.values() if v == seat)
        after_other = sum(1 for v in stones.values() if v == other)

        # OBJECT OF THE GAME, verbatim.  The mover always has >= 1 stone right
        # after placing, so `after_mine == 0` can only mean their own stones
        # were eliminated.  `before_other > 0` encodes "REMOVE all enemy stones"
        # — on ply 1 the opponent simply has not played yet and nothing has been
        # removed, which is the only time that guard bites.
        if after_mine == 0 and after_other == 0:
            winner = seat                       # "you win"
        elif after_mine == 0:
            winner = other                      # "you lose"
        elif after_other == 0 and before_other > 0:
            winner = seat                       # all enemy stones removed
        else:
            winner = None

        return TakeState(
            size=s.size,
            churn=s.churn,
            stones=stones,
            clods=clods,
            to_move=other,
            winner=winner,
            last=cell,
            removed=tuple(sorted(doomed)),
            plies=s.plies + 1,
        )

    def is_terminal(self, s: TakeState) -> bool:
        return s.winner is not None

    def returns(self, s: TakeState) -> list:
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if p == s.winner else -1.0 for p in (0, 1)]

    # ------------------------------------------------------------- (de)serial

    def serialize(self, s: TakeState) -> dict:
        return {
            "size": s.size,
            "churn": s.churn,
            "stones": {_name(c): v for c, v in sorted(s.stones.items())},
            "clods": [_name(c) for c in sorted(s.clods)],
            "to_move": s.to_move,
            "winner": s.winner,
            "last": None if s.last is None else _name(s.last),
            "removed": [_name(c) for c in s.removed],
            "plies": s.plies,
        }

    def deserialize(self, d: dict) -> TakeState:
        return TakeState(
            size=int(d["size"]),
            churn=bool(d["churn"]),
            stones={_cell(k): int(v) for k, v in d["stones"].items()},
            clods=frozenset(_cell(c) for c in d["clods"]),
            to_move=int(d["to_move"]),
            winner=None if d["winner"] is None else int(d["winner"]),
            last=None if d["last"] is None else _cell(d["last"]),
            removed=tuple(_cell(c) for c in d["removed"]),
            plies=int(d["plies"]),
        )

    # -------------------------------------------------------------------- UI

    def describe_move(self, s: TakeState, move: str) -> str:
        sp = spec_for(s.size)
        cell = _cell(move)
        seed = ally_count(s.stones, sp.nbrs, cell, s.to_move) == 0
        nxt = self.apply_move(s, move)
        text = f"{SEAT_NAMES[s.to_move]} {move}"
        if seed:
            text += " seed"
        if nxt.removed:
            # Colour of each removed stone at the moment of removal: the freshly
            # placed cell belongs to the mover, everything else to whoever held
            # it before the placement.
            def owner(c):
                return s.to_move if c == cell else s.stones[c]
            mine = sum(1 for c in nxt.removed if owner(c) == s.to_move)
            text += f" ×{len(nxt.removed)}"
            if mine:
                text += f" (incl. {mine} own)"
        return text

    def render(self, s: TakeState, perspective=None) -> dict:
        red = sum(1 for v in s.stones.values() if v == 0)
        blue = sum(1 for v in s.stones.values() if v == 1)
        pieces = [{"cell": _name(c), "owner": v} for c, v in sorted(s.stones.items())]
        tints = {_name(c): CLOD_TINT for c in sorted(s.clods)}
        highlights = []
        if s.last is not None and s.last in s.stones:
            highlights.append({"cell": _name(s.last), "kind": "last-move"})
        for c in s.removed:
            highlights.append({"cell": _name(c), "kind": "goal"})

        kind = "tiles" if s.churn else "clods"
        if s.winner is not None:
            loser = SEAT_NAMES[1 - s.winner]
            caption = f"{SEAT_NAMES[s.winner]} wins — every {loser} stone removed"
        else:
            caption = (f"{SEAT_NAMES[s.to_move]} to move  "
                       f"(Red {red} – Blue {blue}, {len(s.clods)} {kind})")
        return {
            "board": {
                "type": "hex",
                "shape": "hexagon",
                "size": s.size,
                "tints": tints,
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }


# The crude but honestly derived finiteness bound from the (K, G, U) monovariant
# in the module docstring.  Computed from the board, used by `selftest.py` as a
# sanity ceiling; the GAME declares no ply cap and no repetition rule.
def PLY_BOUND(size: int) -> int:
    return (len(spec_for(size).cells) + 1) ** 3
