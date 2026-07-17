"""Tibetan Go (Mig-mang) -- the traditional Tibetan form of Go.

Ruleset per John Fairbairn's "Tibetan go - the mists are lifting" (GoGoD,
New In Go parts 1-5, 2005), anchored by the played-out 2005 Shangri-la
exhibition game Jiang Zhujiu 9d (W) vs Yue Liang 4d (B), RE W+0.5 zi.
"The rules of Tibetan go follow Chinese rules with the following exceptions":

* Board is **17x17** with a fixed setup of six Black and six White stones on
  the third line (the "Bo"); **White plays first**. Komi 0.
* **The vacated-point ban** (the one special rule): it is not permissible to
  play *immediately* on any point just vacated by a captured stone. After a
  capture removes stones from a set of points S, the opponent's very next
  move may not be a placement on any point of S; the ban lapses after that
  one move. This applies "to kos, snapbacks and throw-ins - to all captures",
  and subsumes the simple-ko ban.
* Otherwise Chinese: liberty capture, suicide illegal, two passes end the game.
* **Area scoring** (Tromp-Taylor region classification): stones + empty points
  controlled. **Bonuses**: a player whose area contains all four corner 1-1
  points gets +20 zi (40 points); if that same player also controls the centre
  point, a further +5 zi (10 points). "Control here also means occupation" --
  occupation or territory-containment both count. Higher total wins; an equal
  total is an honest draw (komi is 0 and all quantities are integral points).

Engine additions (documented in rules.md): positional superko is kept as a
repetition backstop (base Chinese rules ban whole-board repetition anyway),
plus a hard ply cap. The traditional match-play komi convention (next game's
komi = previous margin) is a *match* rule and is not modelled.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

BLACK, WHITE = 0, 1
SIZE = 17
CORNERS = ((0, 0), (SIZE - 1, 0), (0, SIZE - 1), (SIZE - 1, SIZE - 1))
CENTRE = (SIZE // 2, SIZE // 2)

# Fixed 12-stone setup ("Bo"), from the 2005 exhibition SGF header
# AB[kc][cc][oo][ck][go][og] AW[oc][co][cg][ko][ok][gc] (SZ 17; a=0, row 0 at
# the top) -- identical to the Sensei's Library diagram. In Go coordinates
# (A-R skipping I, rows numbered from the bottom):
#   Black: C15 L15 P11 C7 G3 P3    White: G15 P15 C11 P7 C3 L3
SETUP_BLACK = ((10, 2), (2, 2), (14, 14), (2, 10), (6, 14), (14, 6))
SETUP_WHITE = ((14, 2), (2, 14), (2, 6), (10, 14), (14, 10), (6, 2))


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _neighbors(c, r):
    if c > 0:
        yield (c - 1, r)
    if c < SIZE - 1:
        yield (c + 1, r)
    if r > 0:
        yield (c, r - 1)
    if r < SIZE - 1:
        yield (c, r + 1)


def _group(board, start):
    color = board[start]
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for nb in _neighbors(c, r):
            if nb not in seen and board.get(nb) == color:
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_liberty(board, group):
    for c, r in group:
        for nb in _neighbors(c, r):
            if nb not in board:
                return True
    return False


def _board_key(board):
    return "".join(
        "." if (c, r) not in board else "bw"[board[(c, r)]]
        for r in range(SIZE) for c in range(SIZE)
    )


def _resolve(board, c, r, mover):
    """Board after `mover` plays at (c,r): capture enemy dead groups, else a
    dead own group (suicide). Returns (new_board, captured_points:set)."""
    nb = dict(board)
    nb[(c, r)] = mover
    captured = set()
    enemy = 1 - mover
    for ec, er in _neighbors(c, r):
        if nb.get((ec, er)) == enemy and (ec, er) not in captured:
            grp = _group(nb, (ec, er))
            if not _has_liberty(nb, grp):
                captured |= grp
                for sq in grp:
                    del nb[sq]
    if not captured:
        own = _group(nb, (c, r))
        if not _has_liberty(nb, own):
            for sq in own:
                del nb[sq]
    return nb, captured


def _control(board):
    """Tromp-Taylor area map: point -> BLACK/WHITE for every occupied point and
    every empty point in a region bordering only that colour."""
    ctrl = dict(board)
    seen = set()
    for r in range(SIZE):
        for c in range(SIZE):
            if (c, r) in board or (c, r) in seen:
                continue
            region, border = [], set()
            stack = [(c, r)]
            seen.add((c, r))
            while stack:
                cur = stack.pop()
                region.append(cur)
                for nb in _neighbors(cur[0], cur[1]):
                    if nb in board:
                        border.add(board[nb])
                    elif nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            if len(border) == 1:
                owner = border.pop()
                for p in region:
                    ctrl[p] = owner
    return ctrl


def _score(board):
    """Area score in points, bonuses included -> (black, white, bonuses[2]).

    Bonuses: all four 1-1 corner points in one player's area -> +40 points
    (20 zi); if that same player also controls the centre -> +10 (5 zi).
    """
    ctrl = _control(board)
    black = sum(1 for v in ctrl.values() if v == BLACK)
    white = sum(1 for v in ctrl.values() if v == WHITE)
    bonus = [0, 0]
    for p in (BLACK, WHITE):
        if all(ctrl.get(corner) == p for corner in CORNERS):
            bonus[p] += 40
            if ctrl.get(CENTRE) == p:
                bonus[p] += 10
    return black + bonus[BLACK], white + bonus[WHITE], bonus


@dataclass
class TState:
    board: dict = field(default_factory=dict)
    to_move: int = WHITE                     # White plays first
    passes: int = 0
    ply: int = 0
    last_move: object = None                 # (c,r) or "pass" or None
    banned: frozenset = frozenset()          # points vacated by the last move's capture
    history: frozenset = frozenset()


class TibetanGo(Game):
    uid = "tibetan_go"
    name = "Tibetan Go (Mig-mang)"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {p: BLACK for p in SETUP_BLACK}
        board.update({p: WHITE for p in SETUP_WHITE})
        s = TState(board=board)
        s.history = frozenset({_board_key(board)})
        return s

    def current_player(self, s):
        return s.to_move

    def _ply_cap(self, s):
        return SIZE * SIZE * 3

    def _placement(self, s, c, r):
        """The game's single legality predicate for a placement by the player
        to move. Returns the resolved board, or None if illegal (occupied /
        vacated-point ban / suicide / positional-superko backstop)."""
        if (c, r) in s.board:
            return None
        if (c, r) in s.banned:
            return None                        # vacated-point ban (Tibetan rule)
        nb, captured = _resolve(s.board, c, r, s.to_move)
        if not captured and (c, r) not in nb:
            return None                        # suicide
        if _board_key(nb) in s.history:
            return None                        # positional superko (backstop)
        return nb

    def _legal_placements(self, s):
        for r in range(SIZE):
            for c in range(SIZE):
                nb = self._placement(s, c, r)
                if nb is not None:
                    yield f"{c},{r}", nb

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [m for m, _ in self._legal_placements(s)] + ["pass"]

    def apply_move(self, s, move, rng=None):
        if move == "pass":
            return TState(board=dict(s.board), to_move=1 - s.to_move,
                          passes=s.passes + 1, ply=s.ply + 1, last_move="pass",
                          banned=frozenset(), history=s.history)
        c, r = _cell(move)
        nb, captured = _resolve(s.board, c, r, s.to_move)
        return TState(board=nb, to_move=1 - s.to_move, passes=0, ply=s.ply + 1,
                      last_move=(c, r), banned=frozenset(captured),
                      history=s.history | {_board_key(nb)})

    def is_terminal(self, s):
        return s.passes >= 2 or s.ply >= self._ply_cap(s)

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        b, w, _ = _score(s.board)
        if b > w:
            return [1.0, -1.0]
        if w > b:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s):
        b, w, _ = _score(s.board)
        t = math.tanh((b - w) / 20.0)
        return [t, -t]

    def serialize(self, s):
        lm = s.last_move
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move, "passes": s.passes, "ply": s.ply,
            "last_move": ("pass" if lm == "pass" else (list(lm) if lm else None)),
            "banned": sorted(f"{c},{r}" for c, r in s.banned),
            "history": sorted(s.history),
        }

    def deserialize(self, d):
        lm = d.get("last_move")
        return TState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], passes=d.get("passes", 0), ply=d.get("ply", 0),
            last_move=("pass" if lm == "pass" else (tuple(lm) if lm else None)),
            banned=frozenset(_cell(k) for k in d.get("banned", [])),
            history=frozenset(d.get("history", [])))

    def describe_move(self, s, move):
        if move == "pass":
            return "pass"
        c, r = _cell(move)
        letters = "ABCDEFGHJKLMNOPQRST"        # Go convention skips 'I'
        return f"{letters[c]}{SIZE - r}"

    def render(self, s, perspective=None):
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = []
        if isinstance(s.last_move, tuple):
            highlights.append({"cell": f"{s.last_move[0]},{s.last_move[1]}",
                               "kind": "last-move"})
        b, w, bonus = _score(s.board)
        bon = ""
        if bonus[BLACK] or bonus[WHITE]:
            who = BLACK if bonus[BLACK] else WHITE
            bon = f"  ·  {names[who]} corner bonus +{bonus[who]}"
        if self.is_terminal(s):
            if b == w:
                res = "Draw"
            else:
                margin = abs(b - w)
                res = (f"{names[BLACK] if b > w else names[WHITE]} wins "
                       f"by {margin / 2:g} zi ({margin} pt)")
            caption = f"{res} — Black {b} / White {w}{bon}"
        else:
            note = ""
            if s.last_move == "pass":
                note = "  ·  opponent passed"
            elif s.banned:
                note = f"  ·  {len(s.banned)} vacated point(s) banned this move"
            caption = (f"{names[s.to_move]} to move{note}  ·  "
                       f"area B {b} / W {w}{bon}")
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
