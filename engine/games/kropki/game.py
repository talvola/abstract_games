"""Kropki (Точки / Dots) -- the traditional Russian/Polish paper-and-pencil
encirclement game, in the standard competitive "no-territory" ruleset.

Players alternately place dots on grid intersections; dots never move. A closed
chain of one player's LIVE dots (steps of one cell horizontally, vertically or
diagonally -- 8-connectivity) that encloses at least one enemy live dot captures
everything inside: the area is painted and dead forever, each enemy live dot
inside scores +1 for the capturer, and any of the capturer's own previously
captured dots inside are freed (the opponent's score drops accordingly). The
enclosed interior is 4-connected (the standard Jordan pairing with 8-connected
chains), and the board edge never helps enclose anything.

A ring around an area with NO enemy live dots captures nothing -- it is an
"empty base" (домик). The area stays playable, but an enemy dot placed inside
it is captured on the spot (+1 to the base owner, area painted) UNLESS that
very dot simultaneously completes a capture for its own player, in which case
the mover's capture stands and the base dissolves (СКСТ rule; also how the
reference engine oppai-rs implements it).

Game ends when no playable intersection remains or after two consecutive
passes; most captures wins, equal captures is an honest draw.

Rules cross-checked against the СКСТ competitive rules (playdots.ru, via
Wayback), zagram.org's no-territory rules, ru.wikipedia «Точки», and verified
move-by-move against the pointsgame reference engine oppai-rs
(https://github.com/pointsgame/oppai-rs) -- see _diff_oppai.py. This module is
an independent implementation; oppai-rs (AGPL) is used strictly as an external
test oracle.

Internal geometry follows the classic contour-walk formulation: after each
placement, minimal closed chains through the new dot are traced with a
clockwise boundary walk (shortest chain preferred, per СКСТ "система выбирает
цепь минимальной протяженности"), the interior is flooded 4-connectedly, and
capture / empty-base bookkeeping is applied per chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

RED, BLUE = 0, 1          # seat 0 = red (moves first), seat 1 = blue
NAMES = {RED: "Red", BLUE: "Blue"}

# per-cell flag bits (flat padded board, y = 0 at the TOP internally)
PLAYER = 1                # owner bit of PUT / CAP / BASE below
PUT = 2                   # a dot is here
CAP = 4                   # captured: dead dot, or painted (dead) empty cell
BOUND = 8                 # dot is part of a chain that performed a capture
BASE = 16                 # empty-base ("домик") mark
BAD = 32                  # off-board padding

SIZES = {"13x13": (13, 13), "20x20": (20, 20), "25x25": (25, 25),
         "39x32": (39, 32)}


def _first_next(d):
    return ((d + 6) | 1) & 7


class _B:
    """Mutable padded board + capture engine (working object, not the state)."""

    def __init__(self, w, h, cells=None):
        self.w, self.h = w, h
        self.stride = w + 1
        n = self.stride
        # directions 0..7 clockwise from N (internal y grows downward)
        self.OFF = (-n, -n + 1, 1, n + 1, n, n - 1, -1, -n - 1)
        self.length = (w + 1) * (h + 2) + 1
        if cells is not None:
            self.cells = cells
        else:
            self.cells = [0] * self.length
            last = self.length - 2
            self.cells[last + 1] = BAD
            for x in range(self.stride):
                self.cells[x] = BAD
                self.cells[last - x] = BAD
            for y in range(1, h + 1):
                self.cells[y * self.stride] = BAD

    def pos(self, x, y):
        return (y + 1) * self.stride + x + 1

    def allowed(self, p):
        return not self.cells[p] & (PUT | CAP | BAD)

    def _live(self, p, pbit):
        return (self.cells[p] & (PUT | CAP | PLAYER)) == (PUT | pbit)

    def _first_live(self, p, pbit, start_d):
        """First neighbour of p, clockwise from start_d, that is a live dot of
        pbit; None if the scan runs into the board edge first (edge never
        encloses -- the walk is abandoned)."""
        cells, OFF = self.cells, self.OFF
        for i in range(8):
            d = (start_d + i) & 7
            f = cells[p + OFF[d]]
            if f & BAD:
                return None
            if (f & (PUT | CAP | PLAYER)) == (PUT | pbit):
                return d
        return None

    def _delta(self, diff):
        dy = 1 if diff > 1 else (-1 if diff < -1 else 0)
        return diff - dy * self.stride, dy

    def _build_chain(self, start, pbit, d0):
        """Clockwise boundary walk from `start` beginning towards direction d0.
        Returns (chain, None): a minimal closed enclosing chain, or
        (None, aborted_len) when the walk fails (aborted_len==0 means the walk
        hit the board edge; otherwise the length of the orientation-rejected
        chain, used for the short-chain skip)."""
        OFF = self.OFF
        cur = start + OFF[d0]
        chain = [start, cur]
        on = {cur}                      # start itself is deliberately untagged
        d = d0
        while True:
            nd = self._first_live(cur, pbit, _first_next(d))
            if nd is None:
                return None, 0          # fell off the board edge
            q = cur + OFF[nd]
            if q == start:
                break
            if q in on:                 # trim a spur / inner loop
                while chain[-1] != q:
                    on.discard(chain.pop())
            else:
                on.add(q)
                chain.append(q)
            cur = q
            d = nd
        # shoelace in coordinates relative to start: only the orientation that
        # actually encloses the interior side is accepted
        area = x = y = 0
        prev = start
        for p in chain[1:]:
            dx, dy = self._delta(p - prev)
            area += x * dy - y * dx
            x += dx
            y += dy
            prev = p
        dx, dy = self._delta(start - prev)
        area += x * dy - y * dx
        if area < 0:
            return chain, None
        return None, len(chain)

    def _input_points(self, p, pbit):
        """Candidate (walk direction, interior seed cell) pairs around p: one
        per cardinal side of p that is not a live own dot but has a live own
        dot just clockwise of it."""
        OFF = self.OFF
        live = self._live
        res = []
        for card in (6, 4, 2, 0):       # W, S, E, N
            if live(p + OFF[card], pbit):
                continue
            diag, nxt = (card + 1) & 7, (card + 2) & 7
            if live(p + OFF[diag], pbit):
                res.append((diag, p + OFF[card]))
            elif live(p + OFF[nxt], pbit):
                res.append((nxt, p + OFF[card]))
        return res

    def _capture(self, chain, seed, pbit, scores):
        """Flood the interior of `chain` from `seed` (4-connected; the mover's
        own live dots inside are part of the interior, own capture-boundary
        dots block). Capture if any enemy dot is inside, else mark the area as
        an empty base. Returns True on a capture."""
        cells, OFF = self.cells, self.OFF
        tags = set(chain)
        buf = [seed]
        seen = {seed}
        captured = freed = 0
        i = 0
        while i < len(buf):
            p = buf[i]
            i += 1
            f = cells[p]
            if f & PUT:
                if (f & PLAYER) != pbit:
                    captured += 1
                elif f & CAP:
                    freed += 1
            for k in (0, 2, 4, 6):
                q = p + OFF[k]
                if q in seen or q in tags:
                    continue
                if (cells[q] & (PUT | CAP | PLAYER | BOUND)) == (PUT | BOUND | pbit):
                    continue
                seen.add(q)
                buf.append(q)
        if captured:
            scores[pbit] += captured
            scores[pbit ^ 1] -= freed
            for p in chain:
                cells[p] |= BOUND
            for p in buf:
                f = cells[p]
                if not f & PUT:
                    cells[p] = (f & ~(BASE | PLAYER)) | CAP | pbit
                elif (f & PLAYER) != pbit:
                    cells[p] = (f & ~BOUND) | CAP
                elif f & CAP:
                    cells[p] = f & ~CAP
            return True
        for p in buf:
            if not cells[p] & PUT:
                cells[p] = (cells[p] & ~PLAYER) | BASE | pbit
        return False

    def _find_captures(self, p, pbit, scores):
        """All new minimal chains through the just-placed dot at p; shortest
        chains are resolved first (СКСТ: minimal-length chain preferred)."""
        inputs = self._input_points(p, pbit)
        cap = len(inputs) - 1           # n groups bound at most n-1 interiors
        if cap <= 0:
            return False
        found = []
        for d, seed in inputs:
            chain, rej = self._build_chain(p, pbit, d)
            if chain is not None:
                found.append((chain, seed))
                if len(found) == cap:
                    break
            elif rej and rej < 4:
                # a too-short rejected walk cannot be a valid chain in the
                # other orientation either: one fewer interior is possible
                cap -= 1
                if len(found) == cap:
                    break
        found.sort(key=lambda cs: len(cs[0]))
        got = False
        for chain, seed in found:
            self._capture(chain, seed, pbit, scores)
            got = True
        return got

    def _clear_base_marks(self, start):
        cells, OFF = self.cells, self.OFF
        if not cells[start] & BASE:
            return
        cells[start] &= ~BASE
        buf = [start]
        while buf:
            p = buf.pop()
            for k in (0, 2, 4, 6):
                q = p + OFF[k]
                if cells[q] & BASE:
                    cells[q] &= ~BASE
                    buf.append(q)

    def _inside(self, p, chain):
        """Is cell p strictly inside the closed chain? (4-flood from p blocked
        by the chain; inside iff it never reaches the board edge)."""
        cells, OFF = self.cells, self.OFF
        tags = set(chain)
        if p in tags:
            return False
        buf = [p]
        seen = {p}
        i = 0
        while i < len(buf):
            q = buf[i]
            i += 1
            if cells[q] & BAD:
                return False
            for k in (0, 2, 4, 6):
                r = q + OFF[k]
                if r not in seen and r not in tags:
                    seen.add(r)
                    buf.append(r)
        return True

    def _close_base(self, x, qbit, scores):
        """The opponent placed at x inside a qbit empty base and did not
        capture: find the owner's enclosing chain and capture x with it."""
        for p in range(x - 1, 0, -1):
            if (self.cells[p] & (PUT | PLAYER)) != (PUT | qbit):
                continue
            for d, seed in self._input_points(p, qbit):
                chain, _rej = self._build_chain(p, qbit, d)
                if chain is not None and self._inside(x, chain):
                    self._capture(chain, seed, qbit, scores)
                    return
        # unreachable if base marks are consistent; be defensive anyway
        self._clear_base_marks(x)

    def put(self, x, pbit, scores):
        """Place a dot of pbit at pos x (must be allowed) and resolve captures,
        empty bases and the house rule. Mutates cells/scores."""
        f = self.cells[x]
        base_owner = (f & PLAYER) if f & BASE else None
        self.cells[x] = (f & ~PLAYER) | PUT | pbit
        if base_owner is None:
            self._find_captures(x, pbit, scores)
        elif base_owner == pbit:
            # into one's own house: never a capture (any new chain through x
            # lies entirely within the base, which contains no enemy dots)
            self.cells[x] &= ~BASE
        elif self._find_captures(x, pbit, scores):
            # mover's simultaneous capture takes precedence: the enemy base
            # dissolves (marks cleared), the capture stands
            self._clear_base_marks(x)
        else:
            self._close_base(x, base_owner, scores)


@dataclass
class KState:
    w: int = 20
    h: int = 20
    cells: list = field(default_factory=list)
    scores: list = field(default_factory=lambda: [0, 0])
    to_move: int = RED
    passes: int = 0
    ply: int = 0
    last: object = None                  # internal pos, "pass" or None


class Kropki(Game):
    name = "Kropki"

    @property
    def num_players(self):
        return 2

    # -- coordinate mapping: cell id "c,r" has r = 0 at the BOTTOM ------------
    def _pos(self, s, c, r):
        return (s.h - r) * (s.w + 1) + c + 1

    def _cr(self, s, pos):
        stride = s.w + 1
        return pos % stride - 1, s.h - pos // stride

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        size = str(opts.get("size", "20x20"))
        if size in SIZES:
            w, h = SIZES[size]
        else:
            try:
                w, h = (int(v) for v in size.split("x"))
            except ValueError:
                w, h = 20, 20
            if not (3 <= w <= 64 and 3 <= h <= 64):
                w, h = 20, 20
        b = _B(w, h)
        s = KState(w=w, h=h, cells=b.cells)
        if str(opts.get("start", "cross")) == "cross":
            # standard central cross: a 2x2 block, each player on one diagonal
            # (oppai-rs InitialPosition::Cross; playdots "скрест"), first
            # mover (Red) on the main diagonal, Red to move after it
            w2, h2 = w // 2, h // 2
            scores = s.scores
            for (ix, iy), p in (((w2 - 1, h2 - 1), RED), ((w2 - 1, h2), BLUE),
                                ((w2, h2), RED), ((w2, h2 - 1), BLUE)):
                b.put(b.pos(ix, iy), p, scores)
        return s

    def current_player(self, s):
        return s.to_move

    def _board(self, s):
        return _B(s.w, s.h, s.cells)

    def _allowed(self, s):
        b = self._board(s)
        return [p for r in range(s.h) for c in range(s.w)
                if b.allowed(p := self._pos(s, c, r))]

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        out = []
        for p in self._allowed(s):
            c, r = self._cr(s, p)
            out.append(f"{c},{r}")
        out.append("pass")
        return out

    def apply_move(self, s, move, rng=None):
        ns = KState(w=s.w, h=s.h, cells=list(s.cells), scores=list(s.scores),
                    to_move=s.to_move ^ 1, passes=0, ply=s.ply + 1)
        if move == "pass":
            ns.passes = s.passes + 1
            ns.last = "pass"
            return ns
        c, r = move.split(",")
        pos = self._pos(s, int(c), int(r))
        b = _B(s.w, s.h, ns.cells)
        if not b.allowed(pos):
            raise ValueError(f"illegal move {move!r}")
        b.put(pos, s.to_move, ns.scores)
        ns.last = pos
        return ns

    def is_terminal(self, s):
        if s.passes >= 2 or s.ply >= 3 * s.w * s.h:
            return True
        return not self._allowed(s)

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        a, b = s.scores
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s):
        import math
        v = math.tanh((s.scores[RED] - s.scores[BLUE]) / 3.0)
        return [v, -v]

    def serialize(self, s):
        return {"w": s.w, "h": s.h,
                "cells": "".join(chr(48 + f) for f in s.cells),
                "scores": list(s.scores), "to_move": s.to_move,
                "passes": s.passes, "ply": s.ply,
                "last": s.last if s.last in (None, "pass") else int(s.last)}

    def deserialize(self, d):
        return KState(w=d["w"], h=d["h"],
                      cells=[ord(ch) - 48 for ch in d["cells"]],
                      scores=list(d["scores"]), to_move=d["to_move"],
                      passes=d.get("passes", 0), ply=d.get("ply", 0),
                      last=d.get("last"))

    def describe_move(self, s, move):
        if move == "pass":
            return "pass"
        c, r = move.split(",")
        c, r = int(c), int(r)
        col = chr(97 + c) if c < 26 else "a" + chr(97 + c - 26)
        label = f"{col}{r + 1}"
        try:
            ns = self.apply_move(s, move)
            gain = ns.scores[s.to_move] - s.scores[s.to_move]
            if gain > 0:
                label += f" x{gain}"
        except Exception:
            pass
        return label

    def render(self, s, perspective=None):
        tint_col = {RED: "#f2caca", BLUE: "#c9d7f2"}
        pieces, tints = [], {}
        stride = s.w + 1
        for r in range(s.h):
            for c in range(s.w):
                f = s.cells[(s.h - r) * stride + c + 1]
                cid = f"{c},{r}"
                if f & PUT:
                    owner = f & PLAYER
                    pieces.append({"cell": cid, "owner": owner})
                    if f & CAP:                      # dead dot: captor's tint
                        tints[cid] = tint_col[owner ^ 1]
                elif f & CAP:                        # painted territory
                    tints[cid] = tint_col[f & PLAYER]
        highlights = []
        if isinstance(s.last, int):
            c, r = self._cr(s, s.last)
            highlights.append({"cell": f"{c},{r}", "kind": "last-move"})
        score = f"captures Red {s.scores[RED]} – {s.scores[BLUE]} Blue"
        if self.is_terminal(s):
            a, b = s.scores
            res = "Draw" if a == b else f"{NAMES[RED] if a > b else NAMES[BLUE]} wins"
            caption = f"{res} — {score}"
        else:
            passed = "  ·  opponent passed" if s.last == "pass" else ""
            caption = f"{NAMES[s.to_move]} to move{passed}  ·  {score}"
        return {
            "board": {"type": "square", "width": s.w, "height": s.h,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
