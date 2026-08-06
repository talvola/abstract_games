"""SIX -- Steffen Muehlhaeuser (Steffen-Spiele, 2003).

A BOARDLESS hexagonal tile game: the tiles themselves are the playing area.
Two tokens (one of each colour) start side by side; each player then holds 20
tokens of their colour (21 per colour in the box).

Round one -- each player in turn lays one token from hand next to any token
already on the table (own or enemy).  Round two (after all 40 hand tokens are
down) -- each player in turn picks up one token OF THEIR OWN COLOUR and lays it
down again somewhere else.  Tokens that the pickup cuts loose from the field are
CAPTURED (removed from the game): the largest surviving group stays, every other
group is taken off, and a tie for largest is broken by the player who moved.
Captures are colour-blind -- you routinely lose your own tokens too.

You win by getting six tokens of your colour into one of three formations --
a **row** of six, a **triangle** of six, or a **circle** of six (a ring around a
single cell, whose contents are irrelevant) -- or by reducing your opponent
below six tokens, so that no formation is possible for them any more.

Coordinates are axial hex (q, r); the six neighbours are the usual axial six.
The playing area is UNBOUNDED and drifts as tokens move, so `render()` emits an
explicit axial cell LIST (every occupied cell plus every legal target this
turn) rather than a fixed board; the renderer's viewBox auto-fits.

Termination: round one is exactly 40 plies.  Round two can cycle (a non-capturing
pickup-and-replace is fully reversible), which the printed rules do not address,
so this implementation adds a NO-CAPTURE DRAW: NO_CAPTURE_DRAW (100) consecutive round-two plies
without a capture end the game as a draw.  `PLY_CAP` is a backstop derived from
that rule and is provably unreachable (see selftest.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

RED, BLACK = 0, 1
# Seat 0 renders in web/src/colors.js SEAT_FILL[0] = '#d23b3b' (red), so seat 0
# is the rulebook's RED player and seat 1 its BLACK player.  Pinned by
# selftest.py against the rulebook's own two-colour capture figure.
SEAT_NAMES = ("Red", "Black")

# Axial neighbours, in rotational order.
DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))

# --- component counts (Steffen-Spiele 2013/2022 editions) ------------------
TOKENS_PER_PLAYER = 21          # "21 red tokens / 21 black tokens"
START_TOKENS_PER_PLAYER = 1     # "two starting tokens are placed side by side"
HAND_SIZE = TOKENS_PER_PLAYER - START_TOKENS_PER_PLAYER      # 20 in hand
PLACEMENT_PLIES = 2 * HAND_SIZE                              # round one = 40
MIN_FORMATION = 6               # every winning formation is six tokens

# --- added termination rules (NOT in the printed rules) --------------------
NO_CAPTURE_DRAW = 100           # round-two plies with no capture -> draw
# While the game is still running both players hold at least MIN_FORMATION
# tokens, i.e. at least 2*MIN_FORMATION tokens are on the table.  Every capture
# event removes at least one token from the game, so at most
# 2*TOKENS_PER_PLAYER - 2*MIN_FORMATION of them can happen and leave the game
# running; the next one ends it.
MAX_CAPTURE_EVENTS = 2 * TOKENS_PER_PLAYER - 2 * MIN_FORMATION + 1
# Round two is at most MAX_CAPTURE_EVENTS capturing plies plus at most
# MAX_CAPTURE_EVENTS+1 capture-free runs, each shorter than or equal to
# NO_CAPTURE_DRAW plies (the last ply of such a run is already terminal).
MAX_ROUND2_PLIES = (MAX_CAPTURE_EVENTS
                    + (MAX_CAPTURE_EVENTS + 1) * NO_CAPTURE_DRAW)
PLY_CAP = PLACEMENT_PLIES + MAX_ROUND2_PLIES + 1     # provably unreachable


# --------------------------------------------------------------------------
# The three winning formations, as normalised offset templates.
# --------------------------------------------------------------------------
def _normalise(cells):
    """Translate a cell set so its lexicographically smallest cell is (0, 0)."""
    cs = sorted(cells)
    q0, r0 = cs[0]
    return tuple(sorted((q - q0, r - r0) for q, r in cs))


def _build_shapes():
    """Every winning formation, as (kind, template).  A template's cells are
    offsets from the formation's lexicographically smallest cell, so scanning
    every own token as that anchor enumerates every placement exactly once."""
    out = {}
    # ROW: six consecutive cells along a lattice direction.
    for d in DIRS:
        out[_normalise((i * d[0], i * d[1]) for i in range(MIN_FORMATION))] = "row"
    # CIRCLE: the six neighbours of one cell (whose contents are irrelevant).
    out[_normalise(DIRS)] = "circle"
    # TRIANGLE: side-3 triangle, {i*u + j*v : i, j >= 0, i + j <= 2} for two
    # directions 60 degrees apart.  The six (u, v) pairs give two orientations.
    for i, u in enumerate(DIRS):
        v = DIRS[(i + 1) % len(DIRS)]
        tri = [(a * u[0] + b * v[0], a * u[1] + b * v[1])
               for a in range(3) for b in range(3) if a + b <= 2]
        out[_normalise(tri)] = "triangle"
    return tuple(sorted(out.items()))


# ((template, kind), ...) -- 3 rows, 1 circle, 2 triangles.
SHAPES = _build_shapes()


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _cell(text):
    q, r = text.split(",")
    return (int(q), int(r))


def _cstr(c):
    return f"{c[0]},{c[1]}"


def _neighbors(c):
    q, r = c
    return [(q + dq, r + dr) for dq, dr in DIRS]


def _components(cells):
    """Connected components of a cell set, as a list of sets."""
    todo = set(cells)
    comps = []
    while todo:
        start = todo.pop()
        comp = {start}
        stack = [start]
        while stack:
            for nb in _neighbors(stack.pop()):
                if nb in todo:
                    todo.discard(nb)
                    comp.add(nb)
                    stack.append(nb)
        comps.append(comp)
    return comps


def _frontier(cells):
    """Empty cells touching at least one cell of `cells` -- the legal targets."""
    out = set()
    for c in cells:
        for nb in _neighbors(c):
            if nb not in cells:
                out.add(nb)
    return out


def _win_shape(own):
    """(kind, cells) of a winning formation inside `own`, else None."""
    for template, kind in SHAPES:
        for q, r in own:
            cells = [(q + dq, r + dr) for dq, dr in template]
            if all(c in own for c in cells):
                return kind, cells
    return None


def _split_options(rest):
    """The capture outcomes of a pickup that leaves the field `rest`.

    Returns a list of (kept_cells, choice_token).  `choice_token` is None when
    the outcome is forced; when several groups tie for largest the mover picks
    which one survives, and each option is tagged with that group's
    lexicographically smallest cell.
    """
    comps = _components(rest)
    if len(comps) <= 1:
        return [(rest, None)]
    biggest = max(len(c) for c in comps)
    best = [c for c in comps if len(c) == biggest]
    if len(best) == 1:
        return [(best[0], None)]
    return [(c, _cstr(min(c))) for c in sorted(best, key=lambda c: min(c))]


# --------------------------------------------------------------------------
@dataclass
class SState:
    board: dict = field(default_factory=dict)      # (q, r) -> owner
    hands: list = field(default_factory=list)      # tokens still to place
    to_move: int = RED
    ply: int = 0
    since_capture: int = 0     # consecutive round-two plies with no capture
    winner: object = "none"    # "none" | 0 | 1 | "draw"
    last: list = field(default_factory=list)       # cell ids to highlight


class Six(Game):
    name = "Six"

    @property
    def num_players(self):
        return 2

    # ---- setup ----
    def initial_state(self, options=None, rng=None):
        # "Two starting tokens are placed side by side in the centre of the
        # playing area" -- one of each colour (the rulebook figure shows a red
        # and a black token touching).  Red moves first.
        return SState(
            board={(0, 0): RED, (1, 0): BLACK},
            hands=[HAND_SIZE, HAND_SIZE],
            to_move=RED,
            ply=0,
            since_capture=0,
            winner="none",
            last=[],
        )

    def current_player(self, s):
        return s.to_move

    # ---- helpers on a state ----
    def _own(self, s, p):
        return {c for c, o in s.board.items() if o == p}

    def _stock(self, s, p):
        """Tokens `p` still has in the game: on the table plus in hand."""
        return s.hands[p] + sum(1 for o in s.board.values() if o == p)

    def _placing(self, s):
        return s.hands[s.to_move] > 0

    # ---- move generation ----
    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        p = s.to_move
        field = set(s.board)
        if self._placing(s):
            # Round one: lay a token next to any token already on the table.
            return sorted(_cstr(c) for c in _frontier(field))
        # Round two: pick up one of your own tokens, resolve captures, lay it
        # down again somewhere else.
        out = []
        for frm in sorted(self._own(s, p)):
            rest = field - {frm}
            if not rest:
                # Unreachable: the mover holds >= MIN_FORMATION tokens on a
                # non-terminal round-two state, so |field| >= 6.
                continue
            for kept, token in _split_options(rest):
                suffix = "" if token is None else "=" + token
                for to in sorted(_frontier(kept)):
                    if to == frm:
                        continue      # "somewhere ELSE" -- no null move
                    out.append(f"{_cstr(frm)}>{_cstr(to)}{suffix}")
        return out

    # ---- apply ----
    def apply_move(self, s, move, rng=None):
        p = s.to_move
        board = dict(s.board)
        hands = list(s.hands)
        body, _, token = move.partition("=")
        token = token or None
        captured = []

        if ">" in body:
            if self._placing(s):
                raise ValueError("still in round one: place a token from hand")
            frm_s, to_s = body.split(">")
            frm, to = _cell(frm_s), _cell(to_s)
            if board.get(frm) != p:
                raise ValueError(f"{frm_s} does not hold your token")
            if frm == to:
                raise ValueError("a token must be laid down somewhere else")
            del board[frm]
            rest = set(board)
            options = _split_options(rest)
            if len(options) == 1:
                kept, want = options[0]
                if token != want:
                    raise ValueError("this split allows no surviving-group choice")
            else:
                match = [k for k, t in options if t == token]
                if not match:
                    raise ValueError("this split needs a surviving-group choice")
                kept = match[0]
            for c in rest - kept:
                captured.append(c)
                del board[c]
            if to in board:
                raise ValueError(f"{to_s} is occupied")
            if not any(nb in board for nb in _neighbors(to)):
                raise ValueError(f"{to_s} touches no token")
            board[to] = p
            last = [_cstr(frm), _cstr(to)]
            since = 0 if captured else s.since_capture + 1
        else:
            if not self._placing(s):
                raise ValueError("round two: move a token already on the table")
            to = _cell(body)
            if to in board:
                raise ValueError(f"{body} is occupied")
            if not any(nb in board for nb in _neighbors(to)):
                raise ValueError(f"{body} touches no token")
            hands[p] -= 1
            board[to] = p
            last = [_cstr(to)]
            since = 0

        ns = SState(board=board, hands=hands, to_move=1 - p, ply=s.ply + 1,
                    since_capture=since, winner="none", last=last)
        ns.winner = self._result(ns, p)
        return ns

    # ---- result ----
    def _result(self, ns, mover):
        """Who (if anyone) has just won.

        Only the mover can have NEWLY completed a formation: a placement adds
        only the mover's own token, and a capture only ever DELETES tokens,
        which can never complete a formation for anybody.  (selftest.py sweeps
        whole games asserting the non-mover never holds a formation alone.)
        """
        if _win_shape(self._own(ns, mover)):
            return mover
        short = [p for p in (RED, BLACK) if self._stock(ns, p) < MIN_FORMATION]
        if len(short) == 2:
            return "draw"     # neither side can ever form a six again
        if short:
            return 1 - short[0]
        return "none"

    # ---- terminal ----
    def _safety_draw(self, s):
        """Has one of the added termination counters run out?

        A DECISIVE RESULT ALWAYS OUTRANKS THESE COUNTERS, and that cannot
        regress here: `returns()` and `_caption()` both branch on `s.winner`
        before they ever look at a counter, and `is_terminal` ORs this in, so a
        set `winner` short-circuits every consumer.  The `winner == "none"`
        guard below is therefore belt-and-braces (a mutant that removes it is a
        proven no-op), not the thing doing the work.
        """
        return s.winner == "none" and (s.ply >= PLY_CAP
                                       or s.since_capture >= NO_CAPTURE_DRAW)

    def is_terminal(self, s):
        return s.winner != "none" or self._safety_draw(s)

    def returns(self, s):
        if s.winner == RED:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- serialize ----
    def serialize(self, s):
        return {
            "board": {_cstr(c): o for c, o in s.board.items()},
            "hands": list(s.hands),
            "to_move": s.to_move,
            "ply": s.ply,
            "since_capture": s.since_capture,
            "winner": s.winner,
            "last": list(s.last),
        }

    def deserialize(self, d):
        return SState(
            board={_cell(k): v for k, v in d["board"].items()},
            hands=list(d["hands"]),
            to_move=d["to_move"],
            ply=d["ply"],
            since_capture=d["since_capture"],
            winner=d["winner"],
            last=list(d["last"]),
        )

    # ---- move log ----
    def describe_move(self, s, move):
        body, _, token = move.partition("=")
        if ">" not in body:
            return f"{SEAT_NAMES[s.to_move]} lays {body}"
        frm_s, to_s = body.split(">")
        rest = set(s.board) - {_cell(frm_s)}
        options = _split_options(rest)
        kept = options[0][0]
        if len(options) > 1:
            for k, t in options:
                if t == (token or None):
                    kept = k
                    break
        taken = len(rest - kept)
        text = f"{SEAT_NAMES[s.to_move]} {frm_s}→{to_s}"
        if taken:
            text += f" (captures {taken})"
        return text

    # ---- render ----
    def render(self, s, perspective=None):
        cells = set(s.board)
        tokens = set()
        terminal = self.is_terminal(s)
        if not terminal:
            for m in self.legal_moves(s):
                body, _, token = m.partition("=")
                cells.add(_cell(body.split(">")[-1]))
                if token:
                    tokens.add(token)
        if not cells:
            cells = {(0, 0)}

        ids = [_cstr(c) for c in sorted(cells)]
        shown = set(ids)
        pieces = [{"cell": _cstr(c), "owner": o} for c, o in sorted(s.board.items())]
        spec = {
            "board": {"type": "hex", "cells": ids},
            "pieces": pieces,
            # the vacated cell is highlighted too, but only when it is drawn
            "highlights": [{"cell": c, "kind": "last-move"} for c in s.last
                           if c in shown],
            "caption": self._caption(s),
        }
        if any(s.hands):
            spec["reserve"] = {str(p): {"T": s.hands[p]} for p in (RED, BLACK)
                               if s.hands[p] > 0}
        if tokens:
            spec["choiceTitle"] = "Which group survives?"
            spec["choiceNames"] = {t: f"Keep the group at {t}" for t in sorted(tokens)}
        return spec

    def _caption(self, s):
        if s.winner in (RED, BLACK):
            shape = _win_shape(self._own(s, s.winner))
            if shape:
                return f"{SEAT_NAMES[s.winner]} wins — {shape[0]} of six"
            left = self._stock(s, 1 - s.winner)
            return (f"{SEAT_NAMES[s.winner]} wins — "
                    f"{SEAT_NAMES[1 - s.winner]} has only {left} tokens left")
        if s.winner == "draw":
            return "Draw — neither player can form a six"
        if self._safety_draw(s):
            if s.since_capture >= NO_CAPTURE_DRAW:
                return f"Draw — {NO_CAPTURE_DRAW} moves with no capture"
            return f"Draw — move limit ({PLY_CAP}) reached"
        who = SEAT_NAMES[s.to_move]
        if self._placing(s):
            return f"{who} to move — lay a token ({s.hands[s.to_move]} in hand)"
        return f"{who} to move — move one of your tokens"
