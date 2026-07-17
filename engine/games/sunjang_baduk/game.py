"""Sunjang Baduk (순장바둑) -- the historical Korean form of Go, played from the
late 16th century until it died out around 1950 (last recorded game 1937).

Built on the platform's Go core (same liberty capture, suicide-illegal,
positional superko, two-pass termination, ply-cap backstop), with the three
Sunjang deltas:

* **Fixed 19x19 board with a 17-stone prescribed setup**: 8 White + 8 Black
  stones on the marked "guard points", plus Black's prescribed first stone on
  tengen (K10) -- pre-placed here, so **White makes the first free move**.
* **In-game rules identical to ordinary Go** (Fairbairn: "Ko and seki are
  treated exactly as in Japan").
* **Korean removal counting**: after two passes, stones interior to their own
  area are removed (the walls must stay -- no removal may leave a friendly
  group in atari; cutting points may remain), then each side scores the EMPTY
  points of its territory. Stones do not count; prisoners are ignored.
  Traditionally there was no komi (default 0 -- ties are honest draws);
  a 4.5 komi is attested for the mid-20th century (the 1937 "last game").

Scoring internals are module-level (`sunjang_score`, `remove_interior`) so the
selftest can drive them on a hand-built 9x9 board (Bill Spight's worked example
on Sensei's Library) even though the game itself is fixed at 19x19.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

BLACK, WHITE = 0, 1
SIZE = 19

# ---------------------------------------------------------------------------
# Prescribed setup, internal (col, row) coords with row 0 = TOP (displayed row
# 19).  Display "D16" = col letter D (skipping I) -> c=3, row 16 -> r = 19-16 = 3.
# Source: Sensei's Library SunjangBaduk diagram (matches the Wikipedia
# "Go variants" diagram stone-for-stone).
#   White (8): D16 K16 D13 Q13 D7 Q7 K4 Q4
#   Black (8): G16 N16 Q16 D10 Q10 D4 G4 N4   + prescribed 17th stone K10 (tengen)
SETUP_WHITE = [(3, 3), (9, 3), (3, 6), (15, 6), (3, 12), (15, 12), (9, 15), (15, 15)]
SETUP_BLACK = [(6, 3), (12, 3), (15, 3), (3, 9), (15, 9), (3, 15), (6, 15), (12, 15)]
TENGEN = (9, 9)   # K10 -- Black's prescribed first stone, pre-placed


def _cell(s: str):
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


def _group(board, start, size):
    color = board[start]
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for nb in _neighbors(c, r, size):
            if nb not in seen and board.get(nb) == color:
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_liberty(board, group, size):
    for c, r in group:
        for nb in _neighbors(c, r, size):
            if nb not in board:
                return True
    return False


def _liberty_count_at_least(board, group, size, n):
    libs = set()
    for c, r in group:
        for nb in _neighbors(c, r, size):
            if nb not in board:
                libs.add(nb)
                if len(libs) >= n:
                    return True
    return False


def _board_key(board, size):
    return "".join(
        "." if (c, r) not in board else "bw"[board[(c, r)]]
        for r in range(size) for c in range(size)
    )


def _resolve(board, c, r, mover, size):
    """Board after `mover` plays at (c,r): capture enemy dead groups first, then a
    dead own group (suicide). Returns (new_board, captured_count)."""
    nb = dict(board)
    nb[(c, r)] = mover
    captured = 0
    enemy = 1 - mover
    done = set()
    for ec, er in _neighbors(c, r, size):
        if nb.get((ec, er)) == enemy and (ec, er) not in done:
            grp = _group(nb, (ec, er), size)
            done |= grp
            if not _has_liberty(nb, grp, size):
                for sq in grp:
                    del nb[sq]
                captured += len(grp)
    if captured == 0:
        own = _group(nb, (c, r), size)
        if not _has_liberty(nb, own, size):
            for sq in own:
                del nb[sq]
    return nb, captured


# ---------------------------------------------------------------------------
# Sunjang scoring (Korean removal counting)

def _empty_regions(board, size):
    """All maximal empty regions -> list of (region_cellset, border_colour_set)."""
    seen = set()
    out = []
    for r in range(size):
        for c in range(size):
            if (c, r) in board or (c, r) in seen:
                continue
            region, border = set(), set()
            stack = [(c, r)]
            seen.add((c, r))
            while stack:
                cur = stack.pop()
                region.add(cur)
                for nb in _neighbors(cur[0], cur[1], size):
                    if nb in board:
                        border.add(board[nb])
                    elif nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            out.append((region, border))
    return out


def _region_at(board, pt, size):
    """Empty region containing pt -> (region, border colours); early-exits once
    the border is mixed (both colours seen)."""
    region = {pt}
    border = set()
    stack = [pt]
    while stack:
        cur = stack.pop()
        for nb in _neighbors(cur[0], cur[1], size):
            if nb in board:
                border.add(board[nb])
                if len(border) > 1:
                    return region, border
            elif nb not in region:
                region.add(nb)
                stack.append(nb)
    return region, border


def _removable(board, pt, size):
    """A stone is removable iff it is interior to its own area: after deleting
    it, the empty region containing its point touches ONLY its own colour, and
    no remaining friendly group is left in atari (<2 liberties).  Only
    fragments of the stone's own group can lose liberties, so the atari check
    is local to them."""
    colour = board[pt]
    for nb in _neighbors(pt[0], pt[1], size):
        if board.get(nb, colour) != colour:      # adjacent enemy stone
            return False
    trial = dict(board)
    del trial[pt]
    _region, border = _region_at(trial, pt, size)
    if border != {colour}:
        return False
    checked = set()
    for nb in _neighbors(pt[0], pt[1], size):
        if trial.get(nb) == colour and nb not in checked:
            grp = _group(trial, nb, size)
            checked |= grp
            if not _liberty_count_at_least(trial, grp, size, 2):
                return False
    return True


def remove_interior(board, size):
    """Sunjang removal fixpoint: sweep the stones in row-major (top-to-bottom,
    left-to-right) order, deleting each removable stone as it is met; repeat
    sweeps until one removes nothing.  Deterministic (documented in rules.md);
    reproduces Bill Spight's worked example exactly."""
    b = dict(board)
    changed = True
    while changed:
        changed = False
        for pt in sorted(b, key=lambda p: (p[1], p[0])):
            if _removable(b, pt, size):
                del b[pt]
                changed = True
    return b


def sunjang_score(board, size, komi=0.0):
    """Korean removal counting -> (black, white).  Interior stones are removed,
    then each side scores the EMPTY points of the regions touching only its
    colour (mixed regions -- dame, seki shared liberties -- score nobody).
    Stones do not count; prisoners are ignored; White adds komi."""
    walls = remove_interior(board, size)
    black = white = 0
    for region, border in _empty_regions(walls, size):
        if border == {BLACK}:
            black += len(region)
        elif border == {WHITE}:
            white += len(region)
    return black, white + komi


def _area_score(board, size):
    """Tromp-Taylor area count (stones + one-colour empty regions) -- used only
    as a cheap mid-game heuristic proxy, never for the final result."""
    black = sum(1 for v in board.values() if v == BLACK)
    white = sum(1 for v in board.values() if v == WHITE)
    for region, border in _empty_regions(board, size):
        if border == {BLACK}:
            black += len(region)
        elif border == {WHITE}:
            white += len(region)
    return black, white


# ---------------------------------------------------------------------------

@dataclass
class SunjangState:
    komi: float = 0.0
    board: dict = field(default_factory=dict)
    to_move: int = WHITE                     # White makes the first free move
    passes: int = 0
    ply: int = 0
    last_move: object = None                 # (c,r) or "pass" or None
    history: frozenset = field(default_factory=frozenset)


class SunjangBaduk(Game):
    uid = "sunjang_baduk"
    name = "Sunjang Baduk"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        komi = float(opts.get("komi", 0))
        board = {}
        for pt in SETUP_WHITE:
            board[pt] = WHITE
        for pt in SETUP_BLACK:
            board[pt] = BLACK
        board[TENGEN] = BLACK
        s = SunjangState(komi=komi, board=board, to_move=WHITE)
        s.history = frozenset({_board_key(board, SIZE)})
        return s

    def current_player(self, s):
        return s.to_move

    def _ply_cap(self, s):
        return SIZE * SIZE * 3

    def _legal_placements(self, s):
        for r in range(SIZE):
            for c in range(SIZE):
                if (c, r) in s.board:
                    continue
                nb, captured = _resolve(s.board, c, r, s.to_move, SIZE)
                if captured == 0 and (c, r) not in nb:
                    continue                       # suicide
                if _board_key(nb, SIZE) in s.history:
                    continue                       # positional superko
                yield f"{c},{r}", nb

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [m for m, _ in self._legal_placements(s)] + ["pass"]

    def apply_move(self, s, move, rng=None):
        if move == "pass":
            return SunjangState(komi=s.komi, board=dict(s.board),
                                to_move=1 - s.to_move, passes=s.passes + 1,
                                ply=s.ply + 1, last_move="pass", history=s.history)
        c, r = _cell(move)
        nb, _cap = _resolve(s.board, c, r, s.to_move, SIZE)
        return SunjangState(komi=s.komi, board=nb, to_move=1 - s.to_move,
                            passes=0, ply=s.ply + 1, last_move=(c, r),
                            history=s.history | {_board_key(nb, SIZE)})

    def is_terminal(self, s):
        return s.passes >= 2 or s.ply >= self._ply_cap(s)

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        b, w = sunjang_score(s.board, SIZE, s.komi)
        if b > w:
            return [1.0, -1.0]
        if w > b:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s):
        """Cheap rollout-cutoff eval: Tromp-Taylor area balance (komi-adjusted).
        Returns ONE payoff PER SEAT, like `returns`."""
        b, w = _area_score(s.board, SIZE)
        v = math.tanh((b - (w + s.komi)) / 20.0)
        return [v, -v]

    def serialize(self, s):
        lm = s.last_move
        return {
            "komi": s.komi,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move, "passes": s.passes, "ply": s.ply,
            "last_move": ("pass" if lm == "pass" else (list(lm) if lm else None)),
            "history": sorted(s.history),
        }

    def deserialize(self, d):
        lm = d.get("last_move")
        return SunjangState(
            komi=d.get("komi", 0.0),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], passes=d.get("passes", 0), ply=d.get("ply", 0),
            last_move=("pass" if lm == "pass" else (tuple(lm) if lm else None)),
            history=frozenset(d.get("history", [])))

    def describe_move(self, s, move):
        if move == "pass":
            return "pass"
        c, r = _cell(move)
        letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"      # Go convention skips 'I'
        return f"{letters[c]}{SIZE - r}"

    def render(self, s, perspective=None):
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = []
        if isinstance(s.last_move, tuple):
            highlights.append({"cell": f"{s.last_move[0]},{s.last_move[1]}",
                               "kind": "last-move"})
        if self.is_terminal(s):
            b, w = sunjang_score(s.board, SIZE, s.komi)
            res = "Draw" if b == w else f"{names[BLACK] if b > w else names[WHITE]} wins"
            caption = (f"{res} — Sunjang count: Black {b:g}, White {w:g} "
                       f"(komi {s.komi:g})")
        else:
            passed = "  ·  opponent passed" if s.last_move == "pass" else ""
            caption = f"{names[s.to_move]} to move{passed}  ·  komi {s.komi:g}"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
