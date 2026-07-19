"""Mattock, by Drew Edwards (2020; formerly "Las Médulas").

A territory game on a hexhex board played with neutral TILES (mined
corridors) and per-player MINERS that stand on tiles. Rules implemented
from the designer's article in Abstract Games magazine #21 (Spring 2021),
pp. 14-20, cross-checked against the Mindsports/Dagaz implementation
(mindsports.nl/index.php/dagaz/1116-las-medulas-base5), whose move
generator encodes the same ruleset.

Core mechanic (the collapse rule): a newly mined tile may not touch more
than three other tiles, nor touch any tile that already touches three
other tiles. Consequently every tile always touches at most 3 tiles.

A turn is three steps:
  1. MINE (mandatory): place a tile on an empty space next to, or
     connected by stone-free tiles to, one of your miners (opponent's
     miners block connections). If you hold miners removed on previous
     turns, one of them is placed onto the new tile. If you cannot mine,
     you LOSE.
  2. MOVE (optional): move one of your miners any distance through
     connected tiles (through your own miners, never through the
     opponent's) to a miner-free tile.
  3. REMOVE (automatic): every opponent miner that is now both
     (a) not connected to another of its own miners and (b) connected to
     two or more of your miners is removed and returned to its owner
     (who re-places one per turn via step 1). "Connected" = adjacent to
     the region of stone-free tiles reachable from the miner's tile
     (any miner blocks these paths).

Board: hexhex-7 (127 cells, 6 miners each) or the inner hexhex-5
(61 cells, 3 miners each). Fixed setup per the magazine diagram
(pixel-verified; the hex-5 subset matches Mindsports base5 up to board
symmetry), or freestyle alternating placement (no placement adjacent to
an earlier one; the player who places last takes the first turn — here
Blue places first so Red both places last and moves first).

MOVE GRAMMAR: setup/mine = "q,r" (single cell); move phase = "q,r>q',r'"
or "pass" (skip the optional move and end the turn).

Termination: mining is mandatory and strictly monotonic (one tile added
per turn, tiles never leave), so the game ends in at most ~2*cells plies;
it always ends with a winner (the player whose opponent cannot mine).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

SEAT_NAMES = ("Red", "Blue")

# Fixed setups (axial "q,r"; pixel-read from the AG#21 board-sizes/fixed-setup
# diagram, p.14). Blue = the central reflection of Red. Hex-5 uses the inner
# marked cells (matches the Mindsports base5 setup up to board symmetry).
SETUP_RED = {
    7: ((2, -6), (-2, -1), (3, -2), (-6, 4), (-1, 3), (4, 2)),
    5: ((-2, -1), (3, -2), (-1, 3)),
}
TILE_FILL = "#7d6b3a"          # mined-corridor tint (sandy gold, dark-theme safe)


def _neighbors(q: int, r: int):
    return ((q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1),
            (q + 1, r - 1), (q - 1, r + 1))


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    n = size - 1
    out = []
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            if max(abs(q), abs(r), abs(q + r)) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


def _cid(c) -> str:
    return f"{c[0]},{c[1]}"


def _cell(s: str):
    q, r = s.split(",")
    return (int(q), int(r))


@dataclass
class MState:
    size: int = 7
    tiles: set = field(default_factory=set)     # cells holding a tile
    miners: dict = field(default_factory=dict)  # cell -> seat (miners stand on tiles)
    hands: list = field(default_factory=lambda: [0, 0])  # removed miners awaiting re-placement
    to_move: int = 0
    phase: str = "mine"                          # "setup" | "mine" | "move"
    setup_left: list = field(default_factory=lambda: [0, 0])
    mined: Optional[tuple] = None                # tile placed this turn
    last: tuple = ()                             # previous turn's cells (highlights)
    winner: Optional[int] = None
    over: bool = False
    ply: int = 0


class Mattock(Game):
    name = "Mattock"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup ---------------------------------------------------------------

    def initial_state(self, options=None, rng=None) -> MState:
        opts = options or {}
        size = 5 if str(opts.get("board", "hex7")) == "hex5" else 7
        n_miners = len(SETUP_RED[size])
        if str(opts.get("setup", "fixed")) == "freestyle":
            # Blue (seat 1) places first, alternating; Red places last and
            # takes the first turn (article: "The player who places last
            # takes the first turn").
            return MState(size=size, phase="setup", to_move=1,
                          setup_left=[n_miners, n_miners])
        st = MState(size=size, phase="mine", to_move=0)
        for c in SETUP_RED[size]:
            st.tiles.add(c)
            st.miners[c] = 0
        for c in SETUP_RED[size]:
            nc = (-c[0], -c[1])
            st.tiles.add(nc)
            st.miners[nc] = 1
        return st

    def current_player(self, s: MState) -> int:
        return s.to_move

    # -- connectivity helpers -----------------------------------------------

    @staticmethod
    def _connected_stones(s: MState, start) -> tuple:
        """Miners adjacent to the stone-free-tile region reachable from
        ``start`` (start itself is traversed but never counted). Any miner
        blocks the paths. Returns ({seat0 cells}, {seat1 cells})."""
        on = _cell_set(s.size)
        found = (set(), set())
        seen = {start}
        stack = [start]
        while stack:
            c = stack.pop()
            for nb in _neighbors(*c):
                if nb not in on or nb in seen:
                    continue
                if nb in s.miners:
                    seen.add(nb)
                    found[s.miners[nb]].add(nb)
                elif nb in s.tiles:
                    seen.add(nb)
                    stack.append(nb)
        return found

    def _mine_cells(self, s: MState, seat: int) -> list:
        """All legal mine placements for ``seat`` (collapse + connection)."""
        on = _cell_set(s.size)
        tiles = s.tiles
        deg = {}
        for t in tiles:
            deg[t] = sum(1 for nb in _neighbors(*t) if nb in tiles)
        # stone-free tiles connected to one of seat's miners (multi-source BFS)
        region = set()
        stack = []
        for m, owner in s.miners.items():
            if owner != seat:
                continue
            for nb in _neighbors(*m):
                if nb in on and nb in tiles and nb not in s.miners and nb not in region:
                    region.add(nb)
                    stack.append(nb)
        while stack:
            c = stack.pop()
            for nb in _neighbors(*c):
                if (nb in on and nb in tiles and nb not in s.miners
                        and nb not in region):
                    region.add(nb)
                    stack.append(nb)
        out = []
        for e in _cells(s.size):
            if e in tiles:
                continue
            cnt = 0
            ok = True
            connected = False
            for nb in _neighbors(*e):
                if nb not in on:
                    continue
                if nb in tiles:
                    cnt += 1
                    if deg[nb] >= 3:
                        ok = False
                        break
                    if nb in region:
                        connected = True
                    if nb in s.miners and s.miners[nb] == seat:
                        connected = True
            if ok and cnt <= 3 and connected:
                out.append(e)
        return out

    def _move_dests(self, s: MState, src) -> list:
        """Miner-free tiles reachable from ``src`` through connected tiles
        (own miners passable, enemy miners block)."""
        seat = s.miners[src]
        on = _cell_set(s.size)
        seen = {src}
        stack = [src]
        dests = []
        while stack:
            c = stack.pop()
            for nb in _neighbors(*c):
                if nb not in on or nb in seen or nb not in s.tiles:
                    continue
                if nb in s.miners:
                    if s.miners[nb] == seat:
                        seen.add(nb)
                        stack.append(nb)
                    continue
                seen.add(nb)
                dests.append(nb)
                stack.append(nb)
        return dests

    def _removals(self, s: MState, mover: int) -> list:
        """Opponent miners removed at the end of ``mover``'s turn (evaluated
        simultaneously on the current board)."""
        out = []
        for m, owner in s.miners.items():
            if owner == mover:
                continue
            found = self._connected_stones(s, m)
            if not found[owner] and len(found[mover]) >= 2:
                out.append(m)
        return out

    # -- moves ---------------------------------------------------------------

    def _setup_cells(self, s: MState) -> list:
        on = _cells(s.size)
        return [c for c in on
                if c not in s.tiles
                and not any(nb in s.tiles for nb in _neighbors(*c))]

    def legal_moves(self, s: MState) -> list:
        if self.is_terminal(s):
            return []
        if s.phase == "setup":
            return [_cid(c) for c in self._setup_cells(s)]
        if s.phase == "mine":
            return [_cid(c) for c in self._mine_cells(s, s.to_move)]
        moves = ["pass"]
        for m, owner in sorted(s.miners.items()):
            if owner != s.to_move:
                continue
            moves.extend(f"{_cid(m)}>{_cid(d)}"
                         for d in sorted(self._move_dests(s, m)))
        return moves

    def _copy(self, s: MState) -> MState:
        return MState(size=s.size, tiles=set(s.tiles), miners=dict(s.miners),
                      hands=list(s.hands), to_move=s.to_move, phase=s.phase,
                      setup_left=list(s.setup_left), mined=s.mined,
                      last=s.last, winner=s.winner, over=s.over, ply=s.ply)

    def apply_move(self, s: MState, move: str, rng=None) -> MState:
        if self.is_terminal(s):
            raise ValueError("game over")
        ns = self._copy(s)
        ns.ply += 1
        seat = s.to_move

        if s.phase == "setup":
            c = _cell(move)
            if c not in self._setup_cells(s):
                raise ValueError(f"illegal setup placement {move!r}")
            ns.tiles.add(c)
            ns.miners[c] = seat
            ns.setup_left[seat] -= 1
            other = 1 - seat
            if ns.setup_left[other] > 0:
                ns.to_move = other
            elif ns.setup_left[seat] > 0:
                ns.to_move = seat
            else:
                # setup complete: the last placer takes the first turn
                ns.phase = "mine"
                ns.to_move = seat
            return ns

        if s.phase == "mine":
            c = _cell(move)
            if c not in self._mine_cells(s, seat):
                raise ValueError(f"illegal mine {move!r}")
            ns.tiles.add(c)
            if ns.hands[seat] > 0:
                ns.hands[seat] -= 1
                ns.miners[c] = seat
            ns.mined = c
            ns.phase = "move"
            return ns

        # phase == "move"
        moved = ()
        if move != "pass":
            if ">" not in move:
                raise ValueError(f"bad move {move!r}")
            a, b = move.split(">")
            src, dst = _cell(a), _cell(b)
            if s.miners.get(src) != seat:
                raise ValueError(f"no {SEAT_NAMES[seat]} miner on {a}")
            if dst not in self._move_dests(s, src):
                raise ValueError(f"illegal move {move!r}")
            del ns.miners[src]
            ns.miners[dst] = seat
            moved = (src, dst)

        # step 3: automatic removal (simultaneous)
        removed = self._removals(ns, seat)
        for m in removed:
            owner = ns.miners.pop(m)
            ns.hands[owner] += 1

        ns.last = tuple(x for x in ((s.mined,) + moved + tuple(removed))
                        if x is not None)
        ns.mined = None
        ns.phase = "mine"
        ns.to_move = 1 - seat
        # win check: the incoming player must be able to mine
        if not self._mine_cells(ns, ns.to_move):
            ns.winner = seat
            ns.over = True
        return ns

    def is_terminal(self, s: MState) -> bool:
        return s.over

    def returns(self, s: MState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: MState) -> list:
        """Mine-mobility difference (the game is lost at 0 mobility)."""
        if s.over:
            return self.returns(s)
        d = len(self._mine_cells(s, 0)) - len(self._mine_cells(s, 1))
        v = math.tanh(d / 6.0)
        return [v, -v]

    # -- serialization -------------------------------------------------------

    def serialize(self, s: MState) -> dict:
        return {
            "size": s.size,
            "tiles": sorted(_cid(c) for c in s.tiles),
            "miners": {_cid(c): seat for c, seat in sorted(s.miners.items())},
            "hands": list(s.hands),
            "to_move": s.to_move,
            "phase": s.phase,
            "setup_left": list(s.setup_left),
            "mined": _cid(s.mined) if s.mined else None,
            "last": [_cid(c) for c in s.last],
            "winner": s.winner,
            "over": s.over,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> MState:
        return MState(
            size=d["size"],
            tiles={_cell(c) for c in d["tiles"]},
            miners={_cell(c): seat for c, seat in d["miners"].items()},
            hands=list(d["hands"]),
            to_move=d["to_move"],
            phase=d["phase"],
            setup_left=list(d.get("setup_left", [0, 0])),
            mined=_cell(d["mined"]) if d.get("mined") else None,
            last=tuple(_cell(c) for c in d.get("last", [])),
            winner=d.get("winner"),
            over=d.get("over", False),
            ply=d.get("ply", 0),
        )

    # -- presentation --------------------------------------------------------

    def describe_move(self, s: MState, move: str) -> str:
        if s.phase == "setup":
            return f"setup {move}"
        if s.phase == "mine":
            label = f"mine {move}"
            if s.hands[s.to_move] > 0:
                label += " +miner"
            return label
        # move phase: report removals the completed turn would make
        try:
            ns = self.apply_move(s, move)
            n = sum(ns.hands) - sum(s.hands)
        except ValueError:
            n = 0
        label = "no move" if move == "pass" else move.replace(">", " > ")
        if n:
            label += f" (removes {n})"
        return label

    def render(self, s: MState, perspective=None) -> dict:
        tints = {_cid(c): TILE_FILL for c in s.tiles}
        pieces = [{"cell": _cid(c), "owner": seat}
                  for c, seat in sorted(s.miners.items())]
        highlights = [{"cell": _cid(c), "kind": "last-move"} for c in s.last]
        if s.mined:
            highlights.append({"cell": _cid(s.mined), "kind": "last-move"})

        name = SEAT_NAMES[s.to_move]
        hand_bits = [f"{SEAT_NAMES[i]} holds {h} removed miner{'s' * (h != 1)}"
                     for i, h in enumerate(s.hands) if h > 0]
        suffix = (" — " + "; ".join(hand_bits)) if hand_bits else ""
        if s.over:
            caption = (f"{SEAT_NAMES[s.winner]} wins — "
                       f"{SEAT_NAMES[1 - s.winner]} cannot mine")
        elif s.phase == "setup":
            caption = (f"Setup: {name} places a tile + miner "
                       f"({s.setup_left[s.to_move]} left){suffix}")
        elif s.phase == "mine":
            caption = f"{name} to mine (place a tile){suffix}"
        else:
            caption = f"{name}: move a miner or end the turn{suffix}"

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": {"pass": "End turn (no move)"},
        }
