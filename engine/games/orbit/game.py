"""Orbit (Half-Prohibition Orbit) -- Steven Meyers, 2000.

A Go-like territory game with NO liberties, NO capture-by-suffocation and no ko.
Everything turns on *encirclement*:

* stones are **connected orthogonally OR diagonally** (8-connectivity);
* a connected group that, **together with one side of the board**, completely
  encircles one or more points forms a **half-orbit** -- the opponent may never
  play inside it, but nothing is captured;
* a connected group that completely encircles points on its own forms an
  **orbit** -- it captures every enemy stone inside *and* prohibits the opponent
  from playing there.

"Half-orbits prohibit, orbits capture and prohibit."  Two consecutive passes end
the game; each player scores the vacant points inside his own formations, and
points that lie inside *both* players' formations ("shared territory") score for
nobody.

Rules sources: *Abstract Games* magazine issue 12 (Winter 2002) pp. 21-23, and
Meyers' own rules page http://home.fuse.net/swmeyers/orru.htm (Internet Archive),
which is the fuller statement and supplies the anti-mirroring rule and the
"refined" pie rule.

The enclosure test is the exact dual of the connectivity rule.  Take the
complement of a player's stones (empty points + enemy stones) and split it into
**4-connected** components -- 4-connectivity of the enclosed region is the dual of
8-connectivity of the enclosing wall, so a component is sealed iff no 4-step path
escapes off the board.  OR the board-edge memberships of the component's points
into a side mask: mask 0 = an orbit; exactly one side bit = a half-orbit; two or
more bits = the wall would need two sides ("quarter-orbit" in Meyers' family of
29 Orbit variants), which is *not* a formation in the standard game.

Note the consequence that makes the whole thing cheap and safe: a player's own
enclosure map depends only on *his own* stones, so placing a stone can never
capture your own stones (no self-capture) and never changes what the opponent is
forbidden to do.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

BLACK, WHITE = 0, 1

S_LEFT, S_RIGHT, S_BOTTOM, S_TOP = 1, 2, 4, 8
ONE_SIDE = (S_LEFT, S_RIGHT, S_BOTTOM, S_TOP)

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

MIRROR_LIMIT = 10          # "may not mirror ten or more turns in succession"


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _enclosures(stones, W, H):
    """(enclosed, orbit_points) for the player owning `stones`.

    `enclosed` = every point the OPPONENT may not play on (the union of all orbit
    and half-orbit regions).  `orbit_points` = the subset lying in full orbits,
    i.e. the points whose enemy stones are captured.

    A bare corner point is never enclosed -- it belongs to both of the sides that
    meet there, so sealing it needs two sides.  (Confirmed by Diagram 5 of the
    designer's rules page, where P1, walled in by White at O1 and P2, is marked
    as neutral *dame*.)
    """
    enclosed, orbits = set(), set()
    seen = set()
    for r0 in range(H):
        for c0 in range(W):
            if (c0, r0) in stones or (c0, r0) in seen:
                continue
            region = []
            stack = [(c0, r0)]
            seen.add((c0, r0))
            sides = 0
            while stack:
                c, r = stack.pop()
                region.append((c, r))
                if c == 0:
                    sides |= S_LEFT
                if c == W - 1:
                    sides |= S_RIGHT
                if r == 0:
                    sides |= S_BOTTOM
                if r == H - 1:
                    sides |= S_TOP
                for nc, nr in ((c - 1, r), (c + 1, r), (c, r - 1), (c, r + 1)):
                    if 0 <= nc < W and 0 <= nr < H and (nc, nr) not in stones \
                            and (nc, nr) not in seen:
                        seen.add((nc, nr))
                        stack.append((nc, nr))
            if sides == 0:                       # sealed by stones alone: orbit
                enclosed.update(region)
                orbits.update(region)
            elif sides in ONE_SIDE:              # leaks through one side only
                enclosed.update(region)
    return enclosed, orbits


def _stones(board, colour):
    return {p for p, v in board.items() if v == colour}


def _territory(board, W, H):
    """Exclusive territory (black, white) for the position exactly as it stands."""
    encB, _ = _enclosures(_stones(board, BLACK), W, H)
    encW, _ = _enclosures(_stones(board, WHITE), W, H)
    b = sum(1 for p in encB if p not in encW and p not in board)
    w = sum(1 for p in encW if p not in encB and p not in board)
    return b, w


def _cleanup(board, W, H):
    """Rule 7/10 removal of "stones that cannot avoid capture", made deterministic.

    A player may fill every vacant point of the regions he encloses EXCLUSIVELY
    (the opponent is prohibited there and can never interfere), so simulate that
    maximal fill and apply the resulting orbit captures.  Both players' removals
    are computed from the same snapshot -- so the outcome does not depend on whose
    turn it is -- and the process repeats until nothing more dies.
    """
    board = dict(board)
    while True:
        have = {BLACK: _stones(board, BLACK), WHITE: _stones(board, WHITE)}
        enc = {}
        for col in (BLACK, WHITE):
            enc[col], _ = _enclosures(have[col], W, H)
        dead = {BLACK: set(), WHITE: set()}
        for col in (BLACK, WHITE):
            opp = 1 - col
            fill = {p for p in enc[col] if p not in enc[opp] and p not in board}
            _, orb = _enclosures(have[col] | fill, W, H)
            dead[opp] |= have[opp] & orb
        if not dead[BLACK] and not dead[WHITE]:
            return board
        for col in (BLACK, WHITE):
            for p in dead[col]:
                del board[p]


def _final_score(board, W, H):
    return _territory(_cleanup(board, W, H), W, H)


@dataclass
class OrbitState:
    size: int = 16
    opening: str = "pie"                         # "pie" | "refined"
    board: dict = field(default_factory=dict)    # (c,r) -> BLACK/WHITE
    to_move: int = BLACK                         # COLOUR to move
    swapped: bool = False                        # seat 1 took Black
    passes: int = 0
    ply: int = 0
    last_move: object = None                     # (c,r) | "pass" | "swap" | "take:*"
    last_captures: tuple = ()
    prev_point: object = None                    # previous ply's placement, if any
    mirror: tuple = (0, 0)                       # consecutive mirroring moves, by colour


class Orbit(Game):
    name = "Orbit"

    @property
    def num_players(self):
        return 2

    # ---- seats <-> colours -------------------------------------------------
    @staticmethod
    def _seat(colour, swapped):
        """Seat index playing `colour`.  Without a swap, seat 0 = Black."""
        return colour ^ (1 if swapped else 0)

    @staticmethod
    def _mirror_of(p, W, H):
        return (W - 1 - p[0], H - 1 - p[1])

    # ---- setup phase -------------------------------------------------------
    def _in_setup(self, s):
        """Refined pie rule: Player 1 makes plies 0-2 (Black, White, Black)."""
        return s.opening == "refined" and s.ply < 3

    def _choice_due(self, s):
        return s.opening == "refined" and s.ply == 3

    # ---- core --------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        size = int(opts.get("size", 16))
        opening = "refined" if str(opts.get("opening", "pie")) == "refined" else "pie"
        return OrbitState(size=size, opening=opening)

    def current_player(self, s):
        if self._in_setup(s):
            return 0
        if self._choice_due(s):
            return 1
        return self._seat(s.to_move, s.swapped)

    def _ply_cap(self, s):
        return 3 * s.size * s.size

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        if self._choice_due(s):
            return ["take:black", "take:white"]
        W = H = s.size
        banned, _ = _enclosures(_stones(s.board, 1 - s.to_move), W, H)
        blocked = None
        if s.prev_point is not None and s.mirror[s.to_move] >= MIRROR_LIMIT - 1:
            blocked = self._mirror_of(s.prev_point, W, H)
        moves = [f"{c},{r}" for r in range(H) for c in range(W)
                 if (c, r) not in s.board and (c, r) not in banned and (c, r) != blocked]
        moves.append("pass")
        if s.opening == "pie" and s.ply == 1 and not s.swapped:
            moves.append("swap")
        return moves

    def _next(self, s, **kw):
        base = dict(size=s.size, opening=s.opening, board=dict(s.board),
                    to_move=s.to_move, swapped=s.swapped, passes=s.passes,
                    ply=s.ply + 1, last_move=None, last_captures=(),
                    prev_point=None, mirror=(0, 0))
        base.update(kw)
        return OrbitState(**base)

    def apply_move(self, s, move, rng=None):
        W = H = s.size
        if move in ("take:black", "take:white"):
            # Player 2 picks a side; White is to move either way.
            return self._next(s, to_move=WHITE, swapped=(move == "take:black"),
                              passes=0, last_move=move)
        if move == "swap":
            return self._next(s, swapped=True, passes=0, last_move="swap")
        if move == "pass":
            # During the refined setup the three opening plies are Player 1's
            # alone, so passes there do not end the game (the designer notes the
            # plain pie rule is reproduced by "move, pass, pass").
            passes = s.passes if self._in_setup(s) else s.passes + 1
            return self._next(s, to_move=1 - s.to_move, passes=passes,
                              last_move="pass")
        c, r = _cell(move)
        board = dict(s.board)
        board[(c, r)] = s.to_move
        _, orb = _enclosures(_stones(board, s.to_move), W, H)
        opp = 1 - s.to_move
        caps = tuple(sorted(p for p, v in board.items() if v == opp and p in orb))
        for p in caps:
            del board[p]
        streak = 0
        if s.prev_point is not None and (c, r) == self._mirror_of(s.prev_point, W, H):
            streak = s.mirror[s.to_move] + 1
        mirror = list(s.mirror)          # the opponent's own streak is untouched
        mirror[s.to_move] = streak
        return self._next(s, board=board, to_move=opp, passes=0,
                          last_move=(c, r), last_captures=caps,
                          prev_point=(c, r), mirror=tuple(mirror))

    def is_terminal(self, s):
        return s.passes >= 2 or s.ply >= self._ply_cap(s)

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        b, w = _final_score(s.board, s.size, s.size)
        out = [0.0, 0.0]
        if b == w:
            return out                       # a genuine tie is an honest draw
        winner = BLACK if b > w else WHITE
        out[self._seat(winner, s.swapped)] = 1.0
        out[self._seat(1 - winner, s.swapped)] = -1.0
        return out

    def heuristic(self, s):
        b, w = _territory(s.board, s.size, s.size)
        v = math.tanh((b - w) / 10.0)
        out = [0.0, 0.0]
        out[self._seat(BLACK, s.swapped)] = v
        out[self._seat(WHITE, s.swapped)] = -v
        return out

    # ---- (de)serialisation -------------------------------------------------
    def serialize(self, s):
        lm = s.last_move
        return {
            "size": s.size,
            "opening": s.opening,
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "to_move": s.to_move,
            "swapped": s.swapped,
            "passes": s.passes,
            "ply": s.ply,
            "last_move": (lm if isinstance(lm, str) else (list(lm) if lm else None)),
            "last_captures": [f"{c},{r}" for c, r in s.last_captures],
            "prev_point": (list(s.prev_point) if s.prev_point else None),
            "mirror": list(s.mirror),
        }

    def deserialize(self, d):
        lm = d.get("last_move")
        pp = d.get("prev_point")
        return OrbitState(
            size=int(d["size"]),
            opening=d.get("opening", "pie"),
            board={_cell(k): int(v) for k, v in d["board"].items()},
            to_move=int(d["to_move"]),
            swapped=bool(d.get("swapped", False)),
            passes=int(d.get("passes", 0)),
            ply=int(d.get("ply", 0)),
            last_move=(lm if isinstance(lm, str) else (tuple(lm) if lm else None)),
            last_captures=tuple(_cell(k) for k in d.get("last_captures", [])),
            prev_point=(tuple(pp) if pp else None),
            mirror=tuple(d.get("mirror", (0, 0))),
        )

    # ---- presentation ------------------------------------------------------
    def point_name(self, c, r):
        return f"{LETTERS[c] if c < 26 else c}{r + 1}"

    def describe_move(self, s, move):
        if move == "pass":
            return "pass"
        if move == "swap":
            return "swap (pie)"
        if move.startswith("take:"):
            return "take " + move.split(":", 1)[1].capitalize()
        c, r = _cell(move)
        name = ("B " if s.to_move == BLACK else "W ") + self.point_name(c, r)
        nxt = self.apply_move(s, move)
        return f"{name} x{len(nxt.last_captures)}" if nxt.last_captures else name

    def render(self, s, perspective=None):
        W = H = s.size
        seatB = self._seat(BLACK, s.swapped)
        pieces = [{"cell": f"{c},{r}", "owner": self._seat(v, s.swapped), "label": ""}
                  for (c, r), v in s.board.items()]
        highlights = []
        if isinstance(s.last_move, tuple):
            highlights.append({"cell": f"{s.last_move[0]},{s.last_move[1]}",
                               "kind": "last-move"})

        encB, _ = _enclosures(_stones(s.board, BLACK), W, H)
        encW, _ = _enclosures(_stones(s.board, WHITE), W, H)
        seat_tint = ("#3a2626", "#232a3a")
        tints = {}
        for r in range(H):
            for c in range(W):
                p = (c, r)
                if p in s.board:
                    continue
                inB, inW = p in encB, p in encW
                if inB and inW:
                    tints[f"{c},{r}"] = "#33322c"          # shared: nobody scores
                elif inB:
                    tints[f"{c},{r}"] = seat_tint[seatB]
                elif inW:
                    tints[f"{c},{r}"] = seat_tint[1 - seatB]

        b, w = _final_score(s.board, W, H)
        note = "  ·  seats swapped" if s.swapped else ""
        if self.is_terminal(s):
            res = "Draw" if b == w else f"{'Black' if b > w else 'White'} wins"
            caption = f"{res} — territory Black {b}, White {w}{note}"
        elif self._choice_due(s):
            caption = "Player 2 chooses a colour (refined pie rule)"
        else:
            who = "Black" if s.to_move == BLACK else "White"
            setup = "  ·  opening setup" if self._in_setup(s) else ""
            passed = "  ·  opponent passed" if s.last_move == "pass" else ""
            caption = (f"{who} to move{setup}{passed}  ·  territory B {b} / W {w}"
                       f"  ·  ply {s.ply}{note}")
        return {
            "board": {"type": "square", "width": W, "height": H, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": {"pass": "Pass", "swap": "Swap (pie rule)",
                            "take:black": "Take Black", "take:white": "Take White"},
        }
