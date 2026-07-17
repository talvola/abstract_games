"""Go (Weiqi / Baduk) with full territory scoring -- the flagship of the
Go-family, on 9x9 / 13x13 / 19x19.

Built on the same liberty/group/capture core that powers Atari Go, NoGo, Gonnect
and Tanbo (replicated here so the package is self-contained), this adds the parts
those lighter cousins omit: **two-pass termination** and **area scoring**.

Scoring is **Tromp-Taylor area scoring** -- fully algorithmic, so no dead-stone
marking is needed: each side scores its stones on the board plus every empty
region that touches only its colour; White also receives the **komi**. The higher
score wins (a half-point komi avoids ties). Other rules: stones with no liberty
are captured (enemy first, then your own), **suicide is illegal**, and **positional
superko** forbids recreating any earlier whole-board position. Black moves first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

BLACK, WHITE = 0, 1


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _neighbors(c, r, size, torus=False):
    if torus:
        # Toroidal topology: every point has exactly 4 neighbours, edges wrap.
        yield ((c - 1) % size, r)
        yield ((c + 1) % size, r)
        yield (c, (r - 1) % size)
        yield (c, (r + 1) % size)
        return
    if c > 0:
        yield (c - 1, r)
    if c < size - 1:
        yield (c + 1, r)
    if r > 0:
        yield (c, r - 1)
    if r < size - 1:
        yield (c, r + 1)


def _group(board, start, size, torus=False):
    color = board[start]
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for nb in _neighbors(c, r, size, torus):
            if nb not in seen and board.get(nb) == color:
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_liberty(board, group, size, torus=False):
    for c, r in group:
        for nb in _neighbors(c, r, size, torus):
            if nb not in board:
                return True
    return False


def _board_key(board, size):
    return "".join(
        "." if (c, r) not in board else "bw"[board[(c, r)]]
        for r in range(size) for c in range(size)
    )


def _resolve(board, c, r, mover, size, torus=False):
    """Board after `mover` plays at (c,r): capture enemy dead groups first, then a
    dead own group (suicide). Returns (new_board, captured_count)."""
    nb = dict(board)
    nb[(c, r)] = mover
    captured = 0
    enemy = 1 - mover
    done = set()
    for ec, er in _neighbors(c, r, size, torus):
        if nb.get((ec, er)) == enemy and (ec, er) not in done:
            grp = _group(nb, (ec, er), size, torus)
            done |= grp
            if not _has_liberty(nb, grp, size, torus):
                for sq in grp:
                    del nb[sq]
                captured += len(grp)
    if captured == 0:
        own = _group(nb, (c, r), size, torus)
        if not _has_liberty(nb, own, size, torus):
            for sq in own:
                del nb[sq]
    return nb, captured


def _score(board, size, komi, torus=False):
    """Tromp-Taylor area score -> (black, white). White includes komi."""
    black = sum(1 for v in board.values() if v == BLACK)
    white = sum(1 for v in board.values() if v == WHITE)
    seen = set()
    for r in range(size):
        for c in range(size):
            if (c, r) in board or (c, r) in seen:
                continue
            # flood the empty region, recording which stone colours it touches
            region, border = set(), set()
            stack = [(c, r)]
            seen.add((c, r))
            while stack:
                cur = stack.pop()
                region.add(cur)
                for nb in _neighbors(cur[0], cur[1], size, torus):
                    if nb in board:
                        border.add(board[nb])
                    elif nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            if border == {BLACK}:
                black += len(region)
            elif border == {WHITE}:
                white += len(region)
    return black, white + komi


def _handicap_points(size, n):
    """Fixed handicap placement (Japanese convention; Sensei's Library
    'Handicap placement' + 'Handicap stone placement on smaller boards', and
    OGS's fixed-placement code): star points on the 4th line (3rd line on 9x9).
    Returns the list of (c, r) points for an n-stone handicap, r = 0 at the top.
    Order: UR, LL, LR, UL corners, then left/right sides, top/bottom sides,
    tengen (5- and 7-stone use tengen instead of the extra side pair)."""
    e = 3 if size >= 13 else 2
    f = size - 1 - e
    m = size // 2
    ur, ll, lr, ul = (f, e), (e, f), (f, f), (e, e)
    left, right, top, bottom = (e, m), (f, m), (m, e), (m, f)
    center = (m, m)
    table = {
        2: [ur, ll],
        3: [ur, ll, lr],
        4: [ur, ll, lr, ul],
        5: [ur, ll, lr, ul, center],
        6: [ur, ll, lr, ul, left, right],
        7: [ur, ll, lr, ul, left, right, center],
        8: [ur, ll, lr, ul, left, right, top, bottom],
        9: [ur, ll, lr, ul, left, right, top, bottom, center],
    }
    return table.get(n, [])


@dataclass
class GoState:
    size: int = 9
    komi: float = 7.5
    board: dict = field(default_factory=dict)
    to_move: int = BLACK
    passes: int = 0
    ply: int = 0
    last_move: object = None                 # (c,r) or "pass" or None
    history: frozenset = field(default_factory=frozenset)
    handicap: int = 0                        # 0 or 2..9 pre-placed Black stones
    torus: bool = False                      # toroidal topology (edges wrap)
    mode: str = "normal"                     # "normal" or "killall"


class Go(Game):
    uid = "go"
    name = "Go"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        size = int(opts.get("size", 9))
        komi = float(opts.get("komi", 7.5))
        handicap = int(opts.get("handicap", 0))
        handicap = 0 if handicap < 2 else min(handicap, 9)
        torus = str(opts.get("topology", "normal")) == "torus"
        mode = "killall" if str(opts.get("mode", "normal")) == "killall" else "normal"
        s = GoState(size=size, komi=komi, handicap=handicap, torus=torus, mode=mode)
        if handicap:
            for pt in _handicap_points(size, handicap):
                s.board[pt] = BLACK
            s.to_move = WHITE                # White moves first in handicap games
        s.history = frozenset({_board_key(s.board, size)})
        return s

    def current_player(self, s):
        return s.to_move

    def _ply_cap(self, s):
        return s.size * s.size * 3

    def _legal_placements(self, s):
        for r in range(s.size):
            for c in range(s.size):
                if (c, r) in s.board:
                    continue
                nb, captured = _resolve(s.board, c, r, s.to_move, s.size, s.torus)
                if captured == 0 and (c, r) not in nb:
                    continue                       # suicide
                if _board_key(nb, s.size) in s.history:
                    continue                       # positional superko
                yield f"{c},{r}", nb

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        return [m for m, _ in self._legal_placements(s)] + ["pass"]

    def apply_move(self, s, move, rng=None):
        if move == "pass":
            return GoState(size=s.size, komi=s.komi, board=dict(s.board),
                           to_move=1 - s.to_move, passes=s.passes + 1,
                           ply=s.ply + 1, last_move="pass", history=s.history,
                           handicap=s.handicap, torus=s.torus, mode=s.mode)
        c, r = _cell(move)
        nb, _cap = _resolve(s.board, c, r, s.to_move, s.size, s.torus)
        return GoState(size=s.size, komi=s.komi, board=nb, to_move=1 - s.to_move,
                       passes=0, ply=s.ply + 1, last_move=(c, r),
                       history=s.history | {_board_key(nb, s.size)},
                       handicap=s.handicap, torus=s.torus, mode=s.mode)

    def is_terminal(self, s):
        return s.passes >= 2 or s.ply >= self._ply_cap(s)

    def returns(self, s):
        if not self.is_terminal(s):
            return [0.0, 0.0]
        if s.mode == "killall":
            # Kill-All Go: Black must kill every White stone; White wins by
            # having any stone survive. No komi, no draws.
            white_alive = any(v == WHITE for v in s.board.values())
            return [-1.0, 1.0] if white_alive else [1.0, -1.0]
        b, w = _score(s.board, s.size, s.komi, s.torus)
        if b > w:
            return [1.0, -1.0]
        if w > b:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s):
        lm = s.last_move
        d = {
            "size": s.size, "komi": s.komi,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move, "passes": s.passes, "ply": s.ply,
            "last_move": ("pass" if lm == "pass" else (list(lm) if lm else None)),
            "history": sorted(s.history),
        }
        # New-option fields are emitted only when non-default, so a game played
        # with default options serializes byte-identically to the pre-option
        # format (and old payloads deserialize to default behaviour below).
        if s.handicap:
            d["handicap"] = s.handicap
        if s.torus:
            d["topology"] = "torus"
        if s.mode != "normal":
            d["mode"] = s.mode
        return d

    def deserialize(self, d):
        lm = d.get("last_move")
        return GoState(
            size=d["size"], komi=d.get("komi", 7.5),
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], passes=d.get("passes", 0), ply=d.get("ply", 0),
            last_move=("pass" if lm == "pass" else (tuple(lm) if lm else None)),
            history=frozenset(d.get("history", [])),
            handicap=int(d.get("handicap", 0)),
            torus=(d.get("topology", "normal") == "torus"),
            mode=d.get("mode", "normal"))

    def describe_move(self, s, move):
        if move == "pass":
            return "pass"
        c, r = _cell(move)
        letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"      # Go convention skips 'I'
        col = letters[c] if c < len(letters) else str(c)
        return f"{col}{s.size - r}"

    def render(self, s, perspective=None):
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = []
        if isinstance(s.last_move, tuple):
            highlights.append({"cell": f"{s.last_move[0]},{s.last_move[1]}", "kind": "last-move"})
        passed = "  ·  opponent passed" if s.last_move == "pass" else ""
        if s.mode == "killall":
            w_stones = sum(1 for v in s.board.values() if v == WHITE)
            if self.is_terminal(s):
                res = ("White wins — a White stone survives" if w_stones
                       else "Black wins — every White stone is dead")
                caption = f"{res} (kill-all)"
            else:
                caption = (f"{names[s.to_move]} to move{passed}  ·  "
                           f"kill-all: Black must kill every White stone "
                           f"({w_stones} on board)")
        else:
            b, w = _score(s.board, s.size, s.komi, s.torus)
            if self.is_terminal(s):
                res = "Draw" if b == w else f"{names[BLACK] if b > w else names[WHITE]} wins"
                caption = f"{res} — Black {b:g}, White {w:g} (komi {s.komi:g})"
            else:
                caption = (f"{names[s.to_move]} to move{passed}  ·  "
                           f"score B {b:g} / W {w:g} (komi {s.komi:g})")
        if s.torus:
            caption += "  ·  (torus: edges wrap)"
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
