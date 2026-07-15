"""Blokus — the original four-player game (Bernard Tavitian; Sekkoia 2000).

Four players each hold the same 21 pieces: every FREE polyomino of size 1..5
(1 monomino, 1 domino, 2 trominoes, 5 tetrominoes, 12 pentominoes). Rotations
AND reflections are both allowed, which is exactly why the count is 21 (the
one-sided count would be 29).

Rules as implemented (Mattel R1983 "Blokus" rulebook):

* "a board of 400 squares" (20x20); "84 pieces in four different colours
  (21 pieces per colour)".
* "The order of play is as follows: blue, yellow, red, green." Seats 0..3 are
  blue, yellow, red, green, which on the physical board runs CLOCKWISE.
* "The first piece played by each player must cover a corner square." Each seat
  owns one corner (see START) — see rules.md for why the assignment is fixed.
* "Each new piece must touch at least one other piece of the same colour, but
  only at the corners. Pieces of the same colour cannot be in contact along an
  edge." "There are no restrictions on how pieces of different colours may
  contact each other."  Note both tests are per-COLOUR: only a seat's OWN
  pieces constrain it.
* "The game ends when all players are blocked from laying down any more of their
  pieces. This also includes any players who may have placed all of their
  pieces." A blocked player is skipped (see `apply_move`).
* Scoring: "1 unit square = -1 point"; "+15 points if all of his/her pieces have
  been placed on the board plus 5 additional bonus points if the last piece
  placed on the board was the smallest piece (one square)".
* Ties: the rulebook is SILENT (it says only "the player with the highest score
  is the winner"). A tie for first is an honest DRAW (see rules.md).

The rulebook's official 2-player and 3-player variants (one player driving two
colours / a shared fourth colour) are NOT implemented here: `num_players` is a
fixed property read before any state exists, so they cannot be a manifest
option. This package is the canonical 4-player game.

Moves use the palette primitive: ``"KEY:o@c,r"`` — piece KEY, orientation index
o into ``ORIENTS[KEY]``, anchored at cell ``c,r``. The anchor is the piece's
bottom-most then left-most covered square, so every orientation contains
``[0, 0]`` and the anchor is always a cell the piece covers (SPEC's anchor
contract).

Implementation note (performance): every legal placement of every piece at every
anchor is precomputed at import time as a 400-bit bitboard mask, so move
generation is three integer ops per candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from agp.game import Game

W = H = 20
N_CELLS = W * H
N_SEATS = 4

# Each seat's own starting corner, 0-indexed (col, row) with row 0 at the BOTTOM
# (platform cell convention; Board.jsx draws row 0 at the bottom). Verified
# against Pentobi (`set_game blokus` + `all_legal <1|2|3|4>`), whose opening move
# sets pin colour 1 to a20, 2 to t20, 3 to t1 and 4 to a1:
#   seat 0 blue   (0, 19)  top-left      = Pentobi a20
#   seat 1 yellow (19, 19) top-right     = Pentobi t20
#   seat 2 red    (19, 0)  bottom-right  = Pentobi t1
#   seat 3 green  (0, 0)   bottom-left   = Pentobi a1
# Play order 0->1->2->3 therefore runs clockwise, matching the rulebook's
# "blue, yellow, red, green" around the physical board.
START = ((0, 19), (19, 19), (19, 0), (0, 0))

SEAT_NAMES = ("Blue", "Yellow", "Red", "Green")


# --------------------------------------------------------------------------
# Piece set: generated programmatically, then named.
#
# This mirrors games/blokus_duo/game.py (the identical 21-piece set) rather than
# importing it: every game package in this library is self-contained, and `agp.cli
# pack` zips only the package's own directory — a cross-package import would make
# this game un-packable and un-uploadable. The generated set is asserted below,
# so a divergence between the two copies cannot pass silently.
# --------------------------------------------------------------------------

def _normalize(cells) -> tuple:
    """Translate so the tile's ANCHOR sits at (0, 0); canonical offset order.

    The anchor is the tile's **bottom-most, then left-most covered cell**, so
    every orientation contains (0, 0) and the anchor is always a square the tile
    actually covers — click a highlighted anchor and the piece lands on it.
    (Normalising to the bounding-box min corner instead leaves the anchor
    *uncovered* for ~37% of these orientations, so you would click a cell up to
    two squares from where the piece appears.) `dr` is therefore always >= 0,
    while `dc` may be NEGATIVE.

    Still a canonical translation representative — two shapes are translations
    of each other iff their normalised forms are equal — so it remains valid for
    the dedup in `_orients()` / `_free_polyominoes()`.
    """
    ar, ac = min((r, c) for c, r in cells)      # bottom-most, then left-most
    return tuple(sorted((c - ac, r - ar) for c, r in cells))


def _orients(cells) -> list:
    """All distinct rotations+reflections of a shape, each normalised so the
    tile's anchor is at (0, 0) (see `_normalize`). Blokus allows both rotation
    and reflection, so this is the full dihedral orbit (1..8 entries)."""
    out, seen = [], set()
    cur = list(cells)
    for flip in (False, True):
        c0 = [(-c, r) for c, r in cur] if flip else list(cur)
        for _ in range(4):
            c0 = [(r, -c) for c, r in c0]  # rotate 90 degrees
            norm = _normalize(c0)
            if norm not in seen:
                seen.add(norm)
                out.append([list(x) for x in norm])
    return out


def _canonical(cells) -> tuple:
    """Free-polyomino identity: the lexicographically smallest orientation."""
    return min(tuple(map(tuple, o)) for o in _orients(cells))


def _free_polyominoes(n: int) -> set:
    """All free polyominoes of size n, as canonical forms (grown from a cell)."""
    fixed = {((0, 0),)}
    for _ in range(n - 1):
        nxt = set()
        for sh in fixed:
            for (c, r) in sh:
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    p = (c + dc, r + dr)
                    if p not in sh:
                        nxt.add(_normalize(sh + (p,)))
        fixed = nxt
    return {_canonical(sh) for sh in fixed}


# The 21 Blokus pieces, named with the standard polyomino letters (size-suffixed
# so every key is unique and stable). Cells are (col, row) with row increasing
# upward; only the shape matters — orientations are derived.
_NAMED = {
    # 1 monomino
    "I1": [(0, 0)],
    # 1 domino
    "I2": [(0, 0), (1, 0)],
    # 2 trominoes
    "I3": [(0, 0), (1, 0), (2, 0)],
    "V3": [(0, 0), (1, 0), (0, 1)],
    # 5 tetrominoes
    "I4": [(0, 0), (1, 0), (2, 0), (3, 0)],
    "L4": [(0, 0), (1, 0), (2, 0), (0, 1)],
    "N4": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "O4": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T4": [(0, 0), (1, 0), (2, 0), (1, 1)],
    # 12 pentominoes
    "F5": [(1, 2), (2, 2), (0, 1), (1, 1), (1, 0)],
    "I5": [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],
    "L5": [(0, 3), (0, 2), (0, 1), (0, 0), (1, 0)],
    "N5": [(1, 3), (1, 2), (0, 1), (1, 1), (0, 0)],
    "P5": [(0, 2), (1, 2), (0, 1), (1, 1), (0, 0)],
    "T5": [(0, 2), (1, 2), (2, 2), (1, 1), (1, 0)],
    "U5": [(0, 1), (2, 1), (0, 0), (1, 0), (2, 0)],
    "V5": [(0, 2), (0, 1), (0, 0), (1, 0), (2, 0)],
    "W5": [(0, 2), (0, 1), (1, 1), (1, 0), (2, 0)],
    "X5": [(1, 2), (0, 1), (1, 1), (2, 1), (1, 0)],
    "Y5": [(1, 3), (0, 2), (1, 2), (1, 1), (1, 0)],
    "Z5": [(0, 2), (1, 2), (1, 1), (1, 0), (2, 0)],
}

# Verify the named set IS exactly the free polyominoes of size 1..5. This checks
# the naming table against generation (no typos, no duplicates, none missing).
_GENERATED = set()
for _n in (1, 2, 3, 4, 5):
    _GENERATED |= _free_polyominoes(_n)
if {_canonical(v) for v in _NAMED.values()} != _GENERATED:
    raise AssertionError("piece table is not the free polyominoes of size 1..5")
if len(_NAMED) != 21:
    raise AssertionError(f"expected 21 pieces, got {len(_NAMED)}")

PIECES = tuple(_NAMED)                                   # stable key order
ORIENTS = {k: _orients(v) for k, v in _NAMED.items()}
SIZES = {k: len(v) for k, v in _NAMED.items()}
MONOMINO = "I1"

# "84 pieces in four different colours (21 pieces per colour)" (R1983).
if len(PIECES) * N_SEATS != 84:
    raise AssertionError("the four colours must total 84 pieces")


# --------------------------------------------------------------------------
# Bitboards. Bit index of (c, r) is r * W + c.
# --------------------------------------------------------------------------

FULL = (1 << N_CELLS) - 1
_NOT_LEFT = 0    # cells with c > 0
_NOT_RIGHT = 0   # cells with c < W - 1
for _r in range(H):
    for _c in range(W):
        _b = 1 << (_r * W + _c)
        if _c > 0:
            _NOT_LEFT |= _b
        if _c < W - 1:
            _NOT_RIGHT |= _b


def _bit(c: int, r: int) -> int:
    return 1 << (r * W + c)


START_MASK = tuple(_bit(*p) for p in START)


def _edge_zone(own: int) -> int:
    """Cells orthogonally adjacent to `own` (where same-colour edges would touch)."""
    return (((own & _NOT_RIGHT) << 1)
            | ((own & _NOT_LEFT) >> 1)
            | ((own << W) & FULL)
            | (own >> W))


def _corner_zone(own: int) -> int:
    """Cells diagonally adjacent to `own` (where a legal corner touch happens)."""
    return ((((own & _NOT_RIGHT) << (W + 1))
             | ((own & _NOT_LEFT) << (W - 1))
             | ((own & _NOT_RIGHT) >> (W - 1))
             | ((own & _NOT_LEFT) >> (W + 1))) & FULL)


def _build_placements():
    """Every (orientation, anchor) that fits on the board, as (mask, move-string).

    Precomputed once at import: 91 orientations x ~330 anchors.
    """
    out = {}
    lookup = {}
    for key in PIECES:
        entries = []
        for oi, offs in enumerate(ORIENTS[key]):
            # `dc` may be negative (the anchor is a covered cell, not the
            # bounding-box corner), so the anchor range is bounded on BOTH
            # sides: 0 <= c + dc < W for every dc. `dr` is always >= 0, but
            # derive its bound the same way rather than assuming it.
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


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------

@dataclass
class BState:
    occ: tuple = (0, 0, 0, 0)                       # per-seat occupancy bitboards
    hands: tuple = (PIECES, PIECES, PIECES, PIECES)  # per-seat remaining pieces
    to_move: int = 0
    last: tuple = ()                                # cells of the last placement
    last_key: tuple = (None, None, None, None)      # each seat's last piece placed


class Blokus(Game):
    name = "Blokus"

    @property
    def num_players(self) -> int:
        return 4

    def initial_state(self, options=None, rng=None) -> BState:
        return BState()

    def current_player(self, s: BState) -> int:
        return s.to_move

    # -- move generation ---------------------------------------------------

    def _gen(self, s: BState, seat: int) -> Iterator[str]:
        own = s.occ[seat]
        all_occ = s.occ[0] | s.occ[1] | s.occ[2] | s.occ[3]
        if own == 0:
            # First piece: must cover THIS seat's own corner. No corner-touch
            # rule applies (there is nothing of your colour to touch yet), and
            # other colours never restrict you.
            need = START_MASK[seat]
            for key in s.hands[seat]:
                for mask, mv in PLACEMENTS[key]:
                    if not (mask & all_occ) and (mask & need):
                        yield mv
        else:
            # Must not overlap ANY colour, must not share an edge with OWN
            # colour, must share at least one corner with OWN colour. Other
            # colours only block by occupancy — "there are no restrictions on
            # how pieces of different colours may contact each other".
            forbidden = all_occ | _edge_zone(own)
            corners = _corner_zone(own)
            for key in s.hands[seat]:
                for mask, mv in PLACEMENTS[key]:
                    if not (mask & forbidden) and (mask & corners):
                        yield mv

    def _any_moves(self, s: BState, seat: int) -> bool:
        for _ in self._gen(s, seat):
            return True
        return False

    def legal_moves(self, s: BState) -> list[str]:
        return list(self._gen(s, s.to_move))

    def apply_move(self, s: BState, move: str, rng=None) -> BState:
        seat = s.to_move
        mask = MOVE_MASK.get(move)
        if mask is None:
            raise ValueError(f"malformed move: {move}")
        key = move.split(":", 1)[0]
        if key not in s.hands[seat]:
            raise ValueError(f"piece already used: {move}")
        # Full legality (cheap: the same three tests move generation uses).
        own = s.occ[seat]
        all_occ = s.occ[0] | s.occ[1] | s.occ[2] | s.occ[3]
        if mask & all_occ:
            raise ValueError(f"overlapping placement: {move}")
        if own == 0:
            if not (mask & START_MASK[seat]):
                raise ValueError(f"first piece must cover this seat's corner: {move}")
        else:
            if mask & _edge_zone(own):
                raise ValueError(f"edge contact with own colour: {move}")
            if not (mask & _corner_zone(own)):
                raise ValueError(f"no corner contact with own colour: {move}")

        occ = list(s.occ)
        occ[seat] |= mask
        hands = list(s.hands)
        hands[seat] = tuple(k for k in hands[seat] if k != key)
        last_key = list(s.last_key)
        last_key[seat] = key
        ns = BState(occ=tuple(occ), hands=tuple(hands), to_move=seat,
                    last=tuple(_cells_of(mask)), last_key=tuple(last_key))

        # Advance to the next seat (clockwise) who can place. A player who
        # cannot place "must pass" — modelled implicitly by skipping them, so
        # legal_moves is never empty on a non-terminal state (per SPEC). If
        # nobody else can move, the turn returns to the mover (who either
        # continues alone or, if also blocked, ends the game).
        ns.to_move = seat
        for step in range(1, N_SEATS + 1):
            nxt = (seat + step) % N_SEATS
            if self._any_moves(ns, nxt):
                ns.to_move = nxt
                break
        return ns

    # -- terminal / scoring ------------------------------------------------

    def is_terminal(self, s: BState) -> bool:
        # "The game ends when ALL players are blocked from laying down any more
        # of their pieces." Computed from the position (not stored as an event),
        # so hand-built blocked positions are correctly terminal too.
        return not any(self._any_moves(s, p) for p in range(N_SEATS))

    def score(self, s: BState, seat: int) -> int:
        """Rulebook scoring: -1 per remaining unit square; +15 for placing all
        21 pieces; +5 more if the last piece placed was the monomino."""
        hand = s.hands[seat]
        pts = -sum(SIZES[k] for k in hand)
        if not hand:
            pts += 15
            if s.last_key[seat] == MONOMINO:
                pts += 5
        return pts

    def returns(self, s: BState) -> list[float]:
        if not self.is_terminal(s):
            return [0.0] * N_SEATS
        sc = [self.score(s, p) for p in range(N_SEATS)]
        best = max(sc)
        winners = [i for i, v in enumerate(sc) if v == best]
        # +1 to the sole leader, -1 to everyone else; a tie for first is an
        # honest DRAW (the rulebook is silent on ties — see rules.md).
        if len(winners) == 1:
            return [1.0 if i == winners[0] else -1.0 for i in range(N_SEATS)]
        return [0.0] * N_SEATS

    def heuristic(self, s: BState) -> list:
        """Per-seat payoffs for the MCTS rollout cutoff: each seat's score margin
        over the best OTHER seat, squashed to (-1, 1).

        Must be a LIST of num_players payoffs — MCTS indexes it as `payoffs[p]`.
        (A full game runs to 84 plies, well past MCTSBot's default 50-ply rollout
        cutoff, so this is reached routinely and a bare float would crash it.)
        """
        sc = [self.score(s, p) for p in range(N_SEATS)]
        out = []
        for p in range(N_SEATS):
            rival = max(sc[q] for q in range(N_SEATS) if q != p)
            out.append(max(-1.0, min(1.0, (sc[p] - rival) / 30.0)))
        return out

    # -- serialization -----------------------------------------------------

    def serialize(self, s: BState) -> dict:
        return {
            "occ": [str(x) for x in s.occ],
            "hands": [list(h) for h in s.hands],
            "to_move": s.to_move,
            "last": [f"{c},{r}" for c, r in s.last],
            "last_key": list(s.last_key),
        }

    def deserialize(self, d: dict) -> BState:
        cell = lambda t: tuple(int(x) for x in t.split(","))  # noqa: E731
        return BState(
            occ=tuple(int(x) for x in d["occ"]),
            hands=tuple(tuple(h) for h in d["hands"]),
            to_move=d["to_move"],
            last=tuple(cell(x) for x in d.get("last", [])),
            last_key=tuple(d.get("last_key", [None] * N_SEATS)),
        )

    def describe_move(self, s: BState, move: str) -> str:
        key, rest = move.split(":", 1)
        c, r = (int(x) for x in rest.split("@", 1)[1].split(","))
        return f"{key}@{chr(ord('a') + c)}{r + 1}"

    # -- rendering ---------------------------------------------------------

    def render(self, s: BState, perspective=None) -> dict:
        pieces = []
        for seat in range(N_SEATS):
            for c, r in _cells_of(s.occ[seat]):
                pieces.append({"cell": f"{c},{r}", "owner": seat, "shape": "fill"})

        palette = {}
        for seat in range(N_SEATS):
            palette[str(seat)] = [
                {"key": k, "label": f"{k} ({SIZES[k]})", "orients": ORIENTS[k]}
                for k in s.hands[seat]
            ]

        # Mark each seat's starting corner while it is still uncovered.
        all_occ = s.occ[0] | s.occ[1] | s.occ[2] | s.occ[3]
        tints = {}
        for seat in range(N_SEATS):
            if not (START_MASK[seat] & all_occ):
                c, r = START[seat]
                tints[f"{c},{r}"] = "#c8b88a"

        sc = [self.score(s, p) for p in range(N_SEATS)]
        tally = ", ".join(f"{SEAT_NAMES[p]} {sc[p]:+d}" for p in range(N_SEATS))
        if self.is_terminal(s):
            best = max(sc)
            winners = [i for i, v in enumerate(sc) if v == best]
            if len(winners) == 1:
                head = f"{SEAT_NAMES[winners[0]]} wins"
            else:
                head = "Draw — " + " / ".join(SEAT_NAMES[i] for i in winners) + " tie"
            caption = f"{head} — final score {tally}"
        else:
            caption = (f"{SEAT_NAMES[s.to_move]} to move — {tally} "
                       f"({len(s.hands[s.to_move])} pieces left)")

        return {
            "board": {"type": "square", "width": W, "height": H, "tints": tints},
            "pieces": pieces,
            "highlights": [{"cell": f"{c},{r}", "kind": "last-move"} for c, r in s.last],
            "palette": palette,
            "caption": caption,
        }
