"""Domain — a tile game related to Othello (Larry Back).

Marketed in Europe in the early 1980s as Boomerang (France), Kiss (Italy) and
Chameleon (England); Parker Brothers published it in North America in 1983 as
"Domain". Source: Larry Back, "Domain", *Abstract Games* magazine issue 12
(Winter 2002), pp. 27-28.

Rules as implemented (all quotes from the AG#12 article):

* "Domain is played on a 9x9 square board." Two players: Blue (seat 0) and
  White (seat 1). Either may move first; here seat 0 moves first.
* Each player owns the SAME set of 26 reversible polyomino tiles (blue on one
  side, white on the other): 6 Short Bars (2), 6 Medium Bars (3), 2 Long Bars
  (5), 4 Angles (3), 2 Squares (4), 2 Small T's (4), 2 Crosses (5) and 2 Large
  T's (5). "Each Domain tile is necessarily symmetrical so that it can be
  flipped over and placed back on the board in such a way that it covers the
  same squares." Because tiles are reversible, orientations include reflections
  — but every tile here is mirror-symmetric, so reflections coincide with
  rotations. 26 tiles cover 88 squares per side.
* A move places one of your tiles over empty squares (fully on-board, no
  overlap), your colour up.
* FLIP: "After a player places a tile on the board any tiles belonging to the
  opponent that are touching the placed tile are flipped over to the player's
  color. (Two tiles must occupy horizontally or vertically adjacent squares to
  be considered touching; diagonal touches do not count.)" A whole opponent
  TILE flips to your colour; only tiles touching the just-placed tile flip, and
  they are judged once against the pre-flip board — there is no chaining.
* TOUCH restriction (intermediate/advanced only): "except for the first move of
  the game, a tile must be placed so that it touches at least one tile of the
  opponent." A player with no legal placement "can only pass ... in which case
  passing is mandatory" — modelled by skipping the blocked player, so
  legal_moves is empty only on a terminal state.
* END: "The game ends when neither player is able to move." Score = squares your
  colour covers ("add up the number value of all your tiles"). "The player whose
  tiles cover the most squares at the end of the game wins. Ties are possible" —
  and an equal cover is an honest DRAW (returns [0, 0]).

Three rule versions ship as the manifest ``variant`` option (AG#12, "Alternate
rules"): the described default is the second/"Intermediate Level" version.
* ``basic`` (first version) — "both players play from a common pool of tiles,
  and there is no requirement to place a tile so that it touches at least one of
  the opponent's tiles." Flip rule as default.
* ``intermediate`` (second version, DEFAULT) — each player has their own 26
  tiles; the touch restriction applies; opponent tiles touched flip to you.
* ``advanced`` (third version) — like intermediate "except that all tiles, both
  blue and white, which are touched by a placed tile are flipped over to the
  opposite color."

Moves use the palette primitive ``"KEY:o@c,r"`` (tile KEY, orientation index o,
anchored at cell c,r); the anchor is the tile's bottom-most then left-most
covered square so every orientation contains [0,0] (SPEC's anchor contract).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

from agp.game import Game

W = H = 9
N_CELLS = W * H

SEAT_NAMES = ("Blue", "White")

# The 26 Domain tiles for one side, transcribed from the AG#12 figure "A set of
# Domain tiles for one side" (pixel-read from the issue-12 PDF). Cells are
# (col, row) with row increasing upward; the circled number on each tile equals
# its square count. Orientations (rotations + reflections) are derived below.
_NAMED = {
    "S2": [(0, 0), (1, 0)],                                  # Short Bar (1x2), 2
    "M3": [(0, 0), (1, 0), (2, 0)],                          # Medium Bar (1x3), 3
    "L5": [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],          # Long Bar (1x5), 5
    "A3": [(0, 0), (1, 0), (0, 1)],                          # Angle (V-tromino), 3
    "Q4": [(0, 0), (1, 0), (0, 1), (1, 1)],                  # Square (2x2), 4
    "T4": [(0, 1), (1, 1), (2, 1), (1, 0)],                  # Small T (T-tetromino), 4
    "X5": [(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)],          # Cross (plus-pentomino), 5
    "T5": [(0, 2), (1, 2), (2, 2), (1, 1), (1, 0)],          # Large T (T-pentomino), 5
}
# Quantities per side (total 26 tiles, 88 squares).
_COUNTS = {"S2": 6, "M3": 6, "L5": 2, "A3": 4, "Q4": 2, "T4": 2, "X5": 2, "T5": 2}
_LABELS = {
    "S2": "Short Bar", "M3": "Medium Bar", "L5": "Long Bar", "A3": "Angle",
    "Q4": "Square", "T4": "Small T", "X5": "Cross", "T5": "Large T",
}
PIECES = ("S2", "M3", "L5", "A3", "Q4", "T4", "X5", "T5")   # stable key order
START_COUNTS = tuple(_COUNTS[k] for k in PIECES)
SIZES = {k: len(v) for k, v in _NAMED.items()}

if sum(_COUNTS.values()) != 26:
    raise AssertionError("a Domain set has 26 tiles per side")
if sum(_COUNTS[k] * SIZES[k] for k in PIECES) != 88:
    raise AssertionError("a Domain set covers 88 squares per side")


def _normalize(cells) -> tuple:
    """Translate so the tile's bottom-most, then left-most covered cell is the
    anchor at (0, 0); canonical offset order (SPEC anchor contract)."""
    ar, ac = min((r, c) for c, r in cells)
    return tuple(sorted((c - ac, r - ar) for c, r in cells))


def _orients(cells) -> list:
    """Every distinct rotation + reflection of a shape, normalised so the anchor
    is at (0, 0). Tiles are reversible (flip allowed), so this is the full
    dihedral orbit — but each Domain tile is mirror-symmetric, so reflections
    add nothing beyond the rotations."""
    out, seen = [], set()
    cur = list(cells)
    for flip in (False, True):
        c0 = [(-c, r) for c, r in cur] if flip else list(cur)
        for _ in range(4):
            c0 = [(r, -c) for c, r in c0]          # rotate 90 degrees
            norm = _normalize(c0)
            if norm not in seen:
                seen.add(norm)
                out.append([list(x) for x in norm])
    return out


ORIENTS = {k: _orients(v) for k, v in _NAMED.items()}


# --------------------------------------------------------------------------
# Bitboards. Bit index of (c, r) is r * W + c.
# --------------------------------------------------------------------------

FULL = (1 << N_CELLS) - 1
_NOT_LEFT = 0     # cells with c > 0
_NOT_RIGHT = 0    # cells with c < W - 1
for _r in range(H):
    for _c in range(W):
        _b = 1 << (_r * W + _c)
        if _c > 0:
            _NOT_LEFT |= _b
        if _c < W - 1:
            _NOT_RIGHT |= _b


def _bit(c: int, r: int) -> int:
    return 1 << (r * W + c)


def _edge_zone(own: int) -> int:
    """Cells orthogonally adjacent to `own` (diagonal touches excluded)."""
    return ((((own & _NOT_RIGHT) << 1)
             | ((own & _NOT_LEFT) >> 1)
             | (own << W)
             | (own >> W)) & FULL)


def _build_placements():
    """Every (orientation, anchor) that fits on the 9x9 board, as (mask, move)."""
    out, lookup = {}, {}
    for key in PIECES:
        entries = []
        for oi, offs in enumerate(ORIENTS[key]):
            # The anchor is a covered cell, not the bounding-box corner, so `dc`
            # may be negative — bound the anchor range on BOTH sides.
            cmin = min(dc for dc, _ in offs)
            cmax = max(dc for dc, _ in offs)
            rmin = min(dr for _, dr in offs)
            rmax = max(dr for _, dr in offs)
            for r in range(-rmin, H - rmax):
                for c in range(-cmin, W - cmax):
                    mask = 0
                    for dc, dr in offs:
                        mask |= _bit(c + dc, r + dr)
                    mv = f"{key}:{oi}@{c},{r}"
                    entries.append((mask, mv))
                    lookup[mv] = mask
        out[key] = tuple(entries)
    return out, lookup


PLACEMENTS, MOVE_MASK = _build_placements()


def _cells_of(mask: int):
    return [(i % W, i // W) for i in range(N_CELLS) if mask >> i & 1]


VARIANTS = ("basic", "intermediate", "advanced")


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------

@dataclass
class DState:
    # Placed tiles as (owner, mask); a whole tile flips by rewriting its owner.
    tiles: tuple = ()
    # Per-seat remaining counts, aligned to PIECES. For `basic` the two tuples
    # stay identical (a single shared pool, decremented for both on any place).
    hands: tuple = (START_COUNTS, START_COUNTS)
    to_move: int = 0
    variant: str = "intermediate"
    last: tuple = ()                                  # cells of the last placement


class Domain(Game):
    name = "Domain"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DState:
        opts = options or {}
        variant = str(opts.get("variant", "intermediate"))
        if variant not in VARIANTS:
            variant = "intermediate"
        return DState(variant=variant)

    def current_player(self, s: DState) -> int:
        return s.to_move

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _occ(s: DState, seat: Optional[int] = None) -> int:
        m = 0
        for owner, mask in s.tiles:
            if seat is None or owner == seat:
                m |= mask
        return m

    def _gen(self, s: DState, seat: int) -> Iterator[str]:
        all_occ = self._occ(s)
        counts = s.hands[seat]
        # Touch requirement (intermediate/advanced): every move after the very
        # first of the game must touch an opponent tile. `basic` never requires
        # it; the opening move (empty board) is always exempt.
        exempt = s.variant == "basic" or not s.tiles
        opp_occ = 0 if exempt else self._occ(s, 1 - seat)
        for i, key in enumerate(PIECES):
            if counts[i] <= 0:
                continue
            for mask, mv in PLACEMENTS[key]:
                if mask & all_occ:
                    continue
                if not exempt and not (_edge_zone(mask) & opp_occ):
                    continue
                yield mv

    def _any_moves(self, s: DState, seat: int) -> bool:
        for _ in self._gen(s, seat):
            return True
        return False

    def legal_moves(self, s: DState) -> list:
        return list(self._gen(s, s.to_move))

    # -- transition --------------------------------------------------------

    def apply_move(self, s: DState, move: str, rng=None) -> DState:
        seat = s.to_move
        mask = MOVE_MASK.get(move)
        if mask is None:
            raise ValueError(f"malformed move: {move}")
        key = move.split(":", 1)[0]
        idx = PIECES.index(key)
        if s.hands[seat][idx] <= 0:
            raise ValueError(f"tile no longer available: {move}")
        all_occ = self._occ(s)
        if mask & all_occ:
            raise ValueError(f"overlapping placement: {move}")
        if not (s.variant == "basic" or not s.tiles):
            if not (_edge_zone(mask) & self._occ(s, 1 - seat)):
                raise ValueError(f"tile must touch an opponent tile: {move}")

        zone = _edge_zone(mask)
        new_tiles = []
        for owner, tmask in s.tiles:
            if zone & tmask:
                if s.variant == "advanced":
                    owner = 1 - owner               # every touched tile flips
                elif owner != seat:
                    owner = seat                    # opponent tiles flip to you
            new_tiles.append((owner, tmask))
        new_tiles.append((seat, mask))

        hands = list(s.hands)
        if s.variant == "basic":
            pool = list(hands[0])
            pool[idx] -= 1
            hands = [tuple(pool), tuple(pool)]      # one shared pool
        else:
            h = list(hands[seat])
            h[idx] -= 1
            hands[seat] = tuple(h)

        ns = DState(tiles=tuple(new_tiles), hands=tuple(hands), to_move=seat,
                    variant=s.variant, last=tuple(_cells_of(mask)))

        # Advance to the opponent if they can move; otherwise the mover plays
        # again (opponent passed); if neither can move the game is over and this
        # state is terminal (legal_moves for to_move is then empty).
        other = 1 - seat
        if self._any_moves(ns, other):
            ns.to_move = other
        elif self._any_moves(ns, seat):
            ns.to_move = seat
        else:
            ns.to_move = other
        return ns

    # -- terminal / scoring ------------------------------------------------

    def is_terminal(self, s: DState) -> bool:
        # "The game ends when neither player is able to move." Computed from the
        # position, so a hand-built blocked state is correctly terminal too.
        return not self._any_moves(s, 0) and not self._any_moves(s, 1)

    def score(self, s: DState, seat: int) -> int:
        """Squares covered by `seat`'s colour."""
        return sum(len(_cells_of(mask)) for owner, mask in s.tiles if owner == seat)

    def returns(self, s: DState) -> list:
        if not self.is_terminal(s):
            return [0.0, 0.0]
        a, b = self.score(s, 0), self.score(s, 1)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]                            # a genuine tie is a DRAW

    def heuristic(self, s: DState) -> list:
        """Per-seat payoffs for the MCTS rollout cutoff (LIST of num_players):
        the cover margin squashed to (-1, 1)."""
        a, b = self.score(s, 0), self.score(s, 1)
        d = max(-1.0, min(1.0, (a - b) / 40.0))
        return [d, -d]

    # -- serialization -----------------------------------------------------

    def serialize(self, s: DState) -> dict:
        return {
            "tiles": [[owner, str(mask)] for owner, mask in s.tiles],
            "hands": [list(h) for h in s.hands],
            "to_move": s.to_move,
            "variant": s.variant,
            "last": [f"{c},{r}" for c, r in s.last],
        }

    def deserialize(self, d: dict) -> DState:
        cell = lambda t: tuple(int(x) for x in t.split(","))  # noqa: E731
        return DState(
            tiles=tuple((int(o), int(m)) for o, m in d.get("tiles", [])),
            hands=tuple(tuple(int(x) for x in h) for h in d["hands"]),
            to_move=int(d["to_move"]),
            variant=d.get("variant", "intermediate"),
            last=tuple(cell(x) for x in d.get("last", [])),
        )

    def describe_move(self, s: DState, move: str) -> str:
        key, rest = move.split(":", 1)
        c, r = (int(x) for x in rest.split("@", 1)[1].split(","))
        return f"{_LABELS[key]}@{chr(ord('a') + c)}{r + 1}"

    # -- rendering ---------------------------------------------------------

    def render(self, s: DState, perspective=None) -> dict:
        pieces = []
        for owner, mask in s.tiles:
            for c, r in _cells_of(mask):
                pieces.append({"cell": f"{c},{r}", "owner": owner, "shape": "fill"})

        def _tray(counts):
            return [
                {"key": k, "label": f"{_LABELS[k]} ({SIZES[k]})",
                 "count": counts[i], "orients": ORIENTS[k]}
                for i, k in enumerate(PIECES) if counts[i] > 0
            ]

        if s.variant == "basic":
            palette = {"shared": _tray(s.hands[0])}   # one common pool
        else:
            palette = {str(seat): _tray(s.hands[seat]) for seat in (0, 1)}

        a, b = self.score(s, 0), self.score(s, 1)
        tally = f"{SEAT_NAMES[0]} {a} — {SEAT_NAMES[1]} {b}"
        if self.is_terminal(s):
            if a > b:
                head = f"{SEAT_NAMES[0]} wins"
            elif b > a:
                head = f"{SEAT_NAMES[1]} wins"
            else:
                head = "Draw"
            caption = f"{head} — final cover {tally}"
        else:
            caption = f"{SEAT_NAMES[s.to_move]} to move — {tally}"

        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": [{"cell": f"{c},{r}", "kind": "last-move"} for c, r in s.last],
            "palette": palette,
            "caption": caption,
        }
