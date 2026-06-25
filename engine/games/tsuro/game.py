"""Tsuro (Tom McMurchie / Calliope Games, 2004) -- the path-tile race.

Players each have one marker sitting on a notch at the edge of a 6x6 board.
On your turn you place one of your three path-tiles (in any of four rotations)
onto the empty cell your marker is about to enter; your marker then *follows*
the painted path across that tile -- and across any further already-placed
tiles -- until it stops on the edge of an empty cell or is carried off the
board (and is eliminated). The last marker on the board wins.

This package implements a clean **2-player** version of the 2-8 player game:
last marker standing wins; if a placement eliminates the last markers
simultaneously it is a draw.

A tile is a square whose 8 edge-notches are joined in 4 pairs (a perfect
matching of {0..7}). There are exactly 35 such tiles up to rotation; the deck
is those 35 distinct tiles. The deck is shuffled and the hands dealt in
``initial_state`` using the passed ``rng`` and STORED in the state (no chance
node); ``has_randomness`` is true.

Notch numbering (fixed; clockwise from a cell's top-left):
  0,1 = top side (left,right); 2,3 = right (top,bottom);
  4,5 = bottom (right,left); 6,7 = left (bottom,top).
Cross-cell mapping (a token exiting a notch enters the neighbour at the
matching notch): 0->(c,r+1)@5, 1->(c,r+1)@4, 2->(c+1,r)@7, 3->(c+1,r)@6,
4->(c,r-1)@1, 5->(c,r-1)@0, 6->(c-1,r)@3, 7->(c-1,r)@2. (So +row is the
visual "top".) A notch whose neighbour cell is off the 6x6 board is the
board's outer boundary.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

W = H = 6
PLY_CAP = 400  # hard safety cap (board has 36 cells; play is far shorter)

# exit notch -> (dc, dr, entry notch) on the neighbour cell.
CROSS = {
    0: (0, 1, 5), 1: (0, 1, 4),
    2: (1, 0, 7), 3: (1, 0, 6),
    4: (0, -1, 1), 5: (0, -1, 0),
    6: (-1, 0, 3), 7: (-1, 0, 2),
}

# Fixed, documented starting positions for the two markers (cell, notch).
# A marker rests on a notch of an EMPTY on-board cell; that notch lies on the
# board's outer boundary (its cross-neighbour is off-board), so the marker faces
# inward. The two starts are on opposite edges, far apart.
#   Player 0: left edge, cell (0,1), notch 6 (left side, bottom third).
#             CROSS[6] -> (-1,1) is off-board, so notch 6 is the outer boundary.
#   Player 1: right edge, cell (5,4), notch 3 (right side, bottom third).
#             CROSS[3] -> (6,4) is off-board, so notch 3 is the outer boundary.
STARTS = {0: ((0, 1), 6), 1: ((5, 4), 3)}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _rotate_pairs(pairs, k):
    """Rotate a tile's notch-pairs by k quarter-turns: each notch n -> (n+2k)%8."""
    out = []
    for a, b in pairs:
        na, nb = (a + 2 * k) % 8, (b + 2 * k) % 8
        out.append((na, nb) if na <= nb else (nb, na))
    return tuple(sorted(out))


def _all_matchings(elems):
    if not elems:
        yield ()
        return
    first, rest = elems[0], elems[1:]
    for i in range(len(rest)):
        pair = (first, rest[i])
        remaining = rest[:i] + rest[i + 1:]
        for m in _all_matchings(remaining):
            yield (pair,) + m


def build_deck():
    """The 35 distinct path-tiles (canonical orientation), deterministic order."""
    seen = {}
    for m in _all_matchings(list(range(8))):
        m = tuple(sorted((a, b) if a <= b else (b, a) for a, b in m))
        # canonical key = the lexicographically smallest rotation
        best = min(_rotate_pairs(m, k) for k in range(4))
        if best not in seen:
            seen[best] = best
    deck = sorted(seen.values())
    return [list(t) for t in deck]


DECK = build_deck()  # list of 35 tiles, each a list of 4 [a,b] pairs


@dataclass
class TsuroState:
    placed: dict = field(default_factory=dict)        # (c,r) -> [[a,b]x4] placed orientation
    tokens: dict = field(default_factory=dict)        # seat -> (cell, notch) or None if eliminated
    hands: dict = field(default_factory=dict)         # seat -> [tile, tile, tile]
    deck: list = field(default_factory=list)          # remaining draw pile (each a list of pairs)
    to_move: int = 0
    ply: int = 0
    winner: object = None                             # None | seat | "draw"


class Tsuro(Game):
    uid = "tsuro"
    name = "Tsuro"

    @property
    def num_players(self):
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        deck = [list(t) for t in DECK]
        rng.shuffle(deck)
        hands = {0: [deck.pop() for _ in range(3)], 1: [deck.pop() for _ in range(3)]}
        tokens = {0: (STARTS[0][0], STARTS[0][1]), 1: (STARTS[1][0], STARTS[1][1])}
        return TsuroState(placed={}, tokens=tokens, hands=hands, deck=deck,
                          to_move=0, ply=0, winner=None)

    def current_player(self, s):
        return s.to_move

    # ---- geometry helpers -----------------------------------------------
    @staticmethod
    def _on_board(c, r):
        return 0 <= c < W and 0 <= r < H

    @staticmethod
    def _exit_for(tile_pairs, entry):
        """Given a placed tile's pairs, the other end of the path entering at `entry`."""
        for a, b in tile_pairs:
            if a == entry:
                return b
            if b == entry:
                return a
        return None  # should not happen: a tile is a perfect matching of all 8

    def _follow(self, placed, cell, entry_notch):
        """Follow the path starting at (cell, entry_notch) across placed tiles.

        Returns (final_cell, final_notch, eliminated). The marker rests on the
        edge of `cell` at `entry_notch`; this assumes `cell` HAS a placed tile
        (the just-resolved move). It crosses the tile to its exit, steps to the
        neighbour, and repeats until it rests on the notch of a cell with NO
        placed tile (stop) or steps off the board (eliminated).
        """
        c = cell
        notch = entry_notch
        guard = 0
        while True:
            guard += 1
            if guard > 4 * W * H + 8:  # safety; a finite board cannot loop forever
                return c, notch, False
            tile = placed.get(c)
            if tile is None:
                # resting on the edge of an empty cell -- but if that cell is off
                # the board the marker has been carried off the edge.
                if not self._on_board(*c):
                    return c, notch, True
                return c, notch, False
            exit_notch = self._exit_for(tile, notch)
            # cross to the neighbour cell at the matching entry notch
            nc, ent = self._cross(c, exit_notch)
            c, notch = nc, ent

    @staticmethod
    def _cross(cell, exit_notch):
        c, r = cell
        dc, dr, entry = CROSS[exit_notch]
        return (c + dc, r + dr), entry

    # ---- move generation -------------------------------------------------
    def _forced_cell(self, s, seat):
        """The (empty) cell `seat`'s marker rests on, where it must place a tile."""
        tok = s.tokens.get(seat)
        if tok is None:
            return None
        cell, _notch = tok
        return cell

    def _resolve_placement(self, s, cell, oriented):
        """Apply placing `oriented` on `cell`; move ALL tokens whose path now runs.

        Returns (new_placed, new_tokens, winner). Pure (does not mutate s).
        """
        placed = dict(s.placed)
        placed[cell] = oriented
        tokens = dict(s.tokens)
        # Each living token may now be able to advance (its target cell may be
        # newly filled). Recompute every token's resting place; iterate to a
        # fixed point (a token can be pushed onto another newly-filled tile).
        ends = {}  # seat -> (cell, notch) or None (eliminated)
        for seat, tok in tokens.items():
            if tok is None:
                ends[seat] = None
                continue
            cur_cell, cur_notch = tok
            if placed.get(cur_cell) is None:
                ends[seat] = tok                      # its cell is still empty: stays put
                continue
            fc, fn, elim = self._follow(placed, cur_cell, cur_notch)
            ends[seat] = None if elim else (fc, fn)
        # collision: two living tokens ending on the same (cell, notch) -> both die
        living = [(seat, pos) for seat, pos in ends.items() if pos is not None]
        seen = {}
        collided = set()
        for seat, pos in living:
            if pos in seen:
                collided.add(seat)
                collided.add(seen[pos])
            else:
                seen[pos] = seat
        for seat in collided:
            ends[seat] = None
        alive = [seat for seat, pos in ends.items() if pos is not None]
        winner = None
        if len(alive) == 1:
            winner = alive[0]
        elif len(alive) == 0:
            winner = "draw"
        return placed, ends, winner

    def _candidate_orientations(self, s, seat):
        """All (hand_index, rotation, oriented_pairs) for the forced cell."""
        out = []
        for hi, tile in enumerate(s.hands[seat]):
            seen_rot = set()
            for rot in range(4):
                oriented = _rotate_pairs(tile, rot)
                if oriented in seen_rot:     # symmetric tile: skip duplicate rotations
                    continue
                seen_rot.add(oriented)
                out.append((hi, rot, [list(p) for p in oriented]))
        return out

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        seat = s.to_move
        cell = self._forced_cell(s, seat)
        if cell is None:
            return []   # eliminated player never moves (game is terminal once 1 left)
        cid = f"{cell[0]},{cell[1]}"
        all_moves = []
        safe_moves = []
        for hi, rot, oriented in self._candidate_orientations(s, seat):
            mv = f"{cid}={hi}.{rot}"
            _placed, ends, _w = self._resolve_placement(s, cell, oriented)
            all_moves.append(mv)
            if ends.get(seat) is not None:    # the mover survives this placement
                safe_moves.append(mv)
        # no-suicide-unless-forced: only offer self-eliminating moves if there is
        # no safe move at all.
        return safe_moves if safe_moves else all_moves

    # ---- apply -----------------------------------------------------------
    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        seat = s.to_move
        cid, choice = move.split("=")
        hi_s, rot_s = choice.split(".")
        hi, rot = int(hi_s), int(rot_s)
        cell = _cell(cid)
        tile = s.hands[seat][hi]
        oriented = [list(p) for p in _rotate_pairs(tile, rot)]

        placed, ends, winner = self._resolve_placement(s, cell, oriented)

        # remove the placed tile from the hand; eliminated players return their
        # whole hand to the deck (the simplified dragon handling, see rules.md).
        hands = {0: list(s.hands[0]), 1: list(s.hands[1])}
        deck = [list(t) for t in s.deck]
        del hands[seat][hi]

        # return eliminated players' hands to the deck
        for st in (0, 1):
            if s.tokens.get(st) is not None and ends.get(st) is None:
                deck.extend(hands[st])
                hands[st] = []

        # refill the mover's hand to 3 (only if still alive)
        if ends.get(seat) is not None:
            while len(hands[seat]) < 3 and deck:
                hands[seat].append(deck.pop())

        ply = s.ply + 1
        nxt = 1 - seat
        if winner is None:
            # If the next player to move is still alive but has no tile to place
            # (the deck and their hand are exhausted -- only possible deep into a
            # game once ~all tiles are on the board), the game stalls: both markers
            # survived, so it is a draw. (Keeps legal_moves non-empty on every
            # non-terminal state.)
            if ends.get(nxt) is not None and not hands[nxt]:
                winner = "draw"
            elif ply >= PLY_CAP:
                winner = "draw"

        return TsuroState(placed=placed, tokens=ends, hands=hands, deck=deck,
                          to_move=nxt, ply=ply, winner=winner)

    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None or s.winner == "draw":
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # ---- serialize -------------------------------------------------------
    def serialize(self, s):
        return {
            "placed": {f"{c},{r}": [list(p) for p in pairs]
                       for (c, r), pairs in s.placed.items()},
            "tokens": {str(seat): (None if tok is None else [f"{tok[0][0]},{tok[0][1]}", tok[1]])
                       for seat, tok in s.tokens.items()},
            "hands": {str(seat): [[list(p) for p in tile] for tile in s.hands[seat]]
                      for seat in (0, 1)},
            "deck": [[list(p) for p in tile] for tile in s.deck],
            "to_move": s.to_move, "ply": s.ply, "winner": s.winner,
        }

    def deserialize(self, d):
        placed = {_cell(k): [list(p) for p in pairs] for k, pairs in d["placed"].items()}
        tokens = {}
        for seat, tok in d["tokens"].items():
            tokens[int(seat)] = None if tok is None else (_cell(tok[0]), tok[1])
        hands = {int(seat): [[list(p) for p in tile] for tile in tiles]
                 for seat, tiles in d["hands"].items()}
        deck = [[list(p) for p in tile] for tile in d["deck"]]
        return TsuroState(placed=placed, tokens=tokens, hands=hands, deck=deck,
                          to_move=d["to_move"], ply=d.get("ply", 0), winner=d.get("winner"))

    # ---- move log --------------------------------------------------------
    def describe_move(self, s, move):
        cid, choice = move.split("=")
        hi_s, rot_s = choice.split(".")
        deg = int(rot_s) * 90
        return f"P{s.to_move + 1} tile {int(hi_s) + 1}{f' rot{deg}' if deg else ''} @ {cid}"

    # ---- render ----------------------------------------------------------
    def render(self, s, perspective=None):
        tiles = {f"{c},{r}": [list(p) for p in pairs]
                 for (c, r), pairs in s.placed.items()}
        tokens = []
        for seat, tok in s.tokens.items():
            if tok is None:
                continue
            (c, r), notch = tok
            tokens.append({"cell": f"{c},{r}", "notch": notch, "owner": seat})

        board = {"type": "square", "width": W, "height": H,
                 "tiles": tiles, "tokens": tokens}

        # show the current player's hand as a movement-pattern card strip
        cards = []
        if s.winner is None:
            for hi, tile in enumerate(s.hands[s.to_move]):
                cards.append({"name": f"Tile {hi + 1}", "paths": [list(p) for p in tile],
                              "owner": s.to_move, "selectable": False})
        if cards:
            board["cards"] = cards

        # choice picker metadata for the =CHOICE UI
        choice_names = {}
        if s.winner is None:
            for hi, rot, _o in self._candidate_orientations(s, s.to_move):
                deg = rot * 90
                label = f"Tile {hi + 1}" + (f" ⟳{deg}" if deg else "")
                choice_names[f"{hi}.{rot}"] = label

        names = {0: "Player 1", 1: "Player 2"}
        if s.winner == "draw":
            cap = "Draw -- markers eliminated simultaneously"
        elif s.winner is not None:
            cap = f"{names[s.winner]} wins"
        else:
            alive = [names[st] for st in (0, 1) if s.tokens.get(st) is not None]
            cap = (f"{names[s.to_move]} to move: place a path tile  "
                   f"(alive: {', '.join(alive)})")

        return {
            "board": board,
            "pieces": [],
            "highlights": [],
            "caption": cap,
            "choiceTitle": "Place a path tile",
            "choiceNames": choice_names,
        }
