"""Sygo (Christian Freeling, mindsports.nl) -- a Go / Othello hybrid.

Sygo is played on a Go board (intersections), starting EMPTY. It uses Go's
liberty/group capture, but with the Othello twist: a captured group is not
removed -- it is **reversed** to the capturing player's colour (Freeling's
"othelloanian capture"). The game ends on two consecutive passes; the winner is
the player with the larger **territory** = own stones + vacant points surrounded
only by that colour. Equal territory is a draw (a seki can force this).

This package implements the mindsports rules with ONE documented simplification:
each turn a player places a SINGLE stone on any legal vacant point (which grows a
group if adjacent to a friendly stone, or starts a new group otherwise). The
mindsports "grow any-or-all of your groups by one stone each in one turn" multi-
placement and the Black first-turn balance bonus are NOT implemented -- they are
combinatorially explosive for a generic string-move engine. See rules.md (FLAG).
The core that distinguishes Sygo from both Go and Othello -- liberty capture by
GROUP REVERSAL plus the suicide rule -- is implemented faithfully.

Cells are "col,row" (0-indexed). A move is a single cell or "pass". White (player
0) moves first, matching the mindsports/Wikipedia statement.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1          # White (0) moves first per mindsports
NAMES = {WHITE: "White", BLACK: "Black"}


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


def _board_key(board, size):
    return "".join(
        "." if (c, r) not in board else "wb"[board[(c, r)]]
        for r in range(size) for c in range(size)
    )


def _resolve(board, c, r, mover, size):
    """Board after `mover` places at (c,r).

    Othelloanian capture: any orthogonally-adjacent enemy group that loses its
    last liberty is REVERSED to `mover`'s colour (not removed). Returns
    (new_board, reversed_count, legal). `legal` is False on suicide -- i.e. if,
    after all reversals, the mover's own group at (c,r) still has no liberty
    (this also models the source's exception: a capturing move is legal iff the
    reversal leaves the captor's group alive)."""
    nb = dict(board)
    nb[(c, r)] = mover
    enemy = 1 - mover
    reversed_count = 0
    done = set()
    for ec, er in _neighbors(c, r, size):
        if nb.get((ec, er)) == enemy and (ec, er) not in done:
            grp = _group(nb, (ec, er), size)
            done |= grp
            if not _has_liberty(nb, grp, size):
                for sq in grp:
                    nb[sq] = mover          # reverse, don't remove
                reversed_count += len(grp)
    # suicide check AFTER reversals (reversal can give the group a liberty)
    own = _group(nb, (c, r), size)
    legal = _has_liberty(nb, own, size)
    return nb, reversed_count, legal


def _score(board, size):
    """Territory = stones + vacant points surrounded by a single colour.
    Returns (white, black)."""
    white = sum(1 for v in board.values() if v == WHITE)
    black = sum(1 for v in board.values() if v == BLACK)
    seen = set()
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
                for n in _neighbors(cur[0], cur[1], size):
                    if n in board:
                        border.add(board[n])
                    elif n not in seen:
                        seen.add(n)
                        stack.append(n)
            if border == {WHITE}:
                white += len(region)
            elif border == {BLACK}:
                black += len(region)
    return white, black


@dataclass
class SygoState:
    size: int = 9
    board: dict = field(default_factory=dict)
    to_move: int = WHITE
    passes: int = 0
    ply: int = 0
    last_move: object = None                     # (c,r) | "pass" | None
    history: frozenset = field(default_factory=frozenset)


class Sygo(Game):
    uid = "sygo"
    name = "Sygo"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        size = int((options or {}).get("size", 19))     # standard board (manifest default)
        s = SygoState(size=size)
        s.history = frozenset({_board_key(s.board, size)})
        return s

    def current_player(self, s):
        return s.to_move

    def _ply_cap(self, s):
        # safety net so random self-play always terminates
        return s.size * s.size * 4

    def _legal_placements(self, s):
        for r in range(s.size):
            for c in range(s.size):
                if (c, r) in s.board:
                    continue
                nb, _rev, legal = _resolve(s.board, c, r, s.to_move, s.size)
                if not legal:
                    continue                               # suicide
                if _board_key(nb, s.size) in s.history:
                    continue                               # positional superko
                yield f"{c},{r}", nb

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [m for m, _ in self._legal_placements(s)] + ["pass"]

    def apply_move(self, s, move, rng=None):
        if move == "pass":
            return SygoState(size=s.size, board=dict(s.board),
                             to_move=1 - s.to_move, passes=s.passes + 1,
                             ply=s.ply + 1, last_move="pass", history=s.history)
        c, r = _cell(move)
        nb, _rev, _legal = _resolve(s.board, c, r, s.to_move, s.size)
        return SygoState(size=s.size, board=nb, to_move=1 - s.to_move,
                         passes=0, ply=s.ply + 1, last_move=(c, r),
                         history=s.history | {_board_key(nb, s.size)})

    def is_terminal(self, s):
        return s.passes >= 2 or s.ply >= self._ply_cap(s)

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        w, b = _score(s.board, s.size)
        if w > b:
            return [1.0, -1.0]
        if b > w:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s):
        lm = s.last_move
        return {
            "size": s.size,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move, "passes": s.passes, "ply": s.ply,
            "last_move": ("pass" if lm == "pass" else (list(lm) if lm else None)),
            "history": sorted(s.history),
        }

    def deserialize(self, d):
        lm = d.get("last_move")
        return SygoState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], passes=d.get("passes", 0), ply=d.get("ply", 0),
            last_move=("pass" if lm == "pass" else (tuple(lm) if lm else None)),
            history=frozenset(d.get("history", [])))

    def describe_move(self, s, move):
        if move == "pass":
            return f"{NAMES[s.to_move][0]}:pass"
        c, r = _cell(move)
        letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"          # Go convention skips 'I'
        col = letters[c] if c < len(letters) else str(c)
        return f"{NAMES[s.to_move][0]}:{col}{s.size - r}"

    def render(self, s, perspective=None):
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = []
        if isinstance(s.last_move, tuple):
            highlights.append({"cell": f"{s.last_move[0]},{s.last_move[1]}",
                               "kind": "last-move"})
        w, b = _score(s.board, s.size)
        if self.is_terminal(s):
            res = "Draw" if w == b else f"{NAMES[WHITE] if w > b else NAMES[BLACK]} wins"
            caption = f"{res} — White {w}, Black {b}"
        else:
            passed = "  ·  opponent passed" if s.last_move == "pass" else ""
            caption = f"{NAMES[s.to_move]} to move{passed}  ·  territory W {w} / B {b}"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
