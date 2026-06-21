"""Xiangqi (Chinese Chess) — 9x10 board, the full standard rules.

Red (player 0, uppercase, home rows 0-4) moves first; Black (player 1, lowercase,
rows 5-9). Pieces sit on the points of a 9-file x 10-rank grid (rendered here as
cells; the river and palace diagonals are positional rules, drawn lines are a
future cosmetic touch). Seven piece types:

* General  G/g — steps one point orthogonally, confined to the 3x3 palace.
* Advisor  A/a — steps one point diagonally, confined to the palace.
* Elephant E/e — moves exactly two points diagonally, may not cross the river,
                 blocked if the "elephant's eye" (the midpoint) is occupied.
* Horse    H/h — a chess-knight move, but "lame": blocked if the orthogonal
                 point it would step through (the "horse's leg") is occupied.
* Chariot  R/r — a rook: any distance orthogonally, no jumping.
* Cannon   C/c — moves like a rook to an EMPTY square; to CAPTURE it must jump
                 exactly one piece (a "screen", any colour) and land on an enemy.
* Soldier  S/s — steps one point forward; after crossing the river it may also
                 step sideways. Never moves backward; no promotion.

Plus the "flying general" rule: the two generals may not face each other along an
open file (an enemy general attacks along an open file like a chariot). A move
that leaves your own general in check — including exposing it to the enemy general
— is illegal. A player with no legal move LOSES (checkmate and stalemate are both
losses in Xiangqi). Draw rules (and termination guarantee): a 120-ply no-capture
rule, a threefold-repetition draw, and a hard ply cap. (Tournament perpetual-
check/chase-is-a-loss rules are simplified to a repetition draw — see rules.md.)

Moves are clickable cell paths "fc,fr>tc,tr".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

W, H = 9, 10
RED, BLACK = 0, 1
NAMES = {RED: "Red", BLACK: "Black"}
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
PALACE_COLS = (3, 4, 5)
RED_PALACE_ROWS = (0, 1, 2)
BLACK_PALACE_ROWS = (7, 8, 9)
NO_CAPTURE_DRAW = 120
PLY_CAP = 600


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < W and 0 <= r < H


def owner(piece: str) -> int:
    return RED if piece.isupper() else BLACK


def kind(piece: str) -> str:
    return piece.upper()


def _in_palace(player: int, c, r) -> bool:
    rows = RED_PALACE_ROWS if player == RED else BLACK_PALACE_ROWS
    return c in PALACE_COLS and r in rows


def _own_side(player: int, r) -> bool:
    return r <= 4 if player == RED else r >= 5


def _forward(player: int) -> int:
    return 1 if player == RED else -1


def _start_board() -> dict:
    back = ["R", "H", "E", "A", "G", "A", "E", "H", "R"]
    b = {}
    for c, t in enumerate(back):
        b[(c, 0)] = t              # Red back rank
        b[(c, 9)] = t.lower()      # Black back rank
    b[(1, 2)] = b[(7, 2)] = "C"
    b[(1, 7)] = b[(7, 7)] = "c"
    for c in (0, 2, 4, 6, 8):
        b[(c, 3)] = "S"
        b[(c, 6)] = "s"
    return b


def _soldier_targets(board, sq, player):
    c, r = sq
    outs = [(c, r + _forward(player))]
    if not _own_side(player, r):                 # has crossed the river -> sideways
        outs += [(c - 1, r), (c + 1, r)]
    return [(tc, tr) for tc, tr in outs if _on(tc, tr)]


def _pseudo_targets(board, sq):
    """Destination squares for the piece at `sq`, ignoring own-general safety.
    Captures of own pieces are already excluded."""
    piece = board[sq]
    pl, t = owner(piece), kind(piece)
    c, r = sq
    out = []

    if t == "G":
        for dc, dr in ORTHO:
            tc, tr = c + dc, r + dr
            if _in_palace(pl, tc, tr) and (board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl):
                out.append((tc, tr))
    elif t == "A":
        for dc, dr in DIAG:
            tc, tr = c + dc, r + dr
            if _in_palace(pl, tc, tr) and (board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl):
                out.append((tc, tr))
    elif t == "E":
        for dc, dr in DIAG:
            eye = (c + dc, r + dr)
            tc, tr = c + 2 * dc, r + 2 * dr
            if _on(tc, tr) and _own_side(pl, tr) and eye not in board:
                if board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl:
                    out.append((tc, tr))
    elif t == "H":
        for dc, dr in KNIGHT:
            leg = (c + (dc // 2 if abs(dc) == 2 else 0), r + (dr // 2 if abs(dr) == 2 else 0))
            tc, tr = c + dc, r + dr
            if _on(tc, tr) and leg not in board:
                if board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl:
                    out.append((tc, tr))
    elif t == "R":
        for dc, dr in ORTHO:
            cc, rr = c + dc, r + dr
            while _on(cc, rr) and (cc, rr) not in board:
                out.append((cc, rr))
                cc += dc
                rr += dr
            if _on(cc, rr) and owner(board[(cc, rr)]) != pl:
                out.append((cc, rr))
    elif t == "C":
        for dc, dr in ORTHO:
            cc, rr = c + dc, r + dr
            while _on(cc, rr) and (cc, rr) not in board:       # non-capture slide
                out.append((cc, rr))
                cc += dc
                rr += dr
            cc += dc                                            # skip the screen
            rr += dr
            while _on(cc, rr) and (cc, rr) not in board:
                cc += dc
                rr += dr
            if _on(cc, rr) and owner(board[(cc, rr)]) != pl:    # capture beyond screen
                out.append((cc, rr))
    elif t == "S":
        for tc, tr in _soldier_targets(board, sq, pl):
            if board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl:
                out.append((tc, tr))
    return out


def _find_general(board, player):
    g = "G" if player == RED else "g"
    for sq, p in board.items():
        if p == g:
            return sq
    return None


def _attacked(board, sq, by) -> bool:
    """Is `sq` attacked by player `by` (includes the flying-general file rule)?"""
    c, r = sq
    # Chariot / Cannon / flying-General along the four orthogonal rays
    for dc, dr in ORTHO:
        cc, rr = c + dc, r + dr
        while _on(cc, rr) and (cc, rr) not in board:
            cc += dc
            rr += dr
        if _on(cc, rr):
            p = board[(cc, rr)]
            if owner(p) == by:
                t = kind(p)
                if t == "R":
                    return True
                if t == "G" and (dc == 0 or abs(cc - c) + abs(rr - r) == 1):
                    return True   # vertical = flying general (any dist); else adjacent
            # cannon: look past this screen for an enemy cannon
            cc += dc
            rr += dr
            while _on(cc, rr) and (cc, rr) not in board:
                cc += dc
                rr += dr
            if _on(cc, rr) and owner(board[(cc, rr)]) == by and kind(board[(cc, rr)]) == "C":
                return True
    # Horse (check each square a horse could attack from, with its leg empty)
    for dc, dr in KNIGHT:
        hsq = (c + dc, r + dr)
        p = board.get(hsq)
        if p is not None and owner(p) == by and kind(p) == "H":
            leg = (hsq[0] - (dc // 2 if abs(dc) == 2 else 0), hsq[1] - (dr // 2 if abs(dr) == 2 else 0))
            if leg not in board:
                return True
    # Advisor (diagonal adjacent)
    for dc, dr in DIAG:
        p = board.get((c + dc, r + dr))
        if p is not None and owner(p) == by and kind(p) == "A":
            return True
    # Elephant (two diagonal with the eye empty)
    for dc, dr in DIAG:
        p = board.get((c + 2 * dc, r + 2 * dr))
        if p is not None and owner(p) == by and kind(p) == "E" and (c + dc, r + dr) not in board:
            return True
    # Soldier (an enemy soldier on an adjacent square whose move reaches sq)
    for dc, dr in ORTHO:
        nsq = (c + dc, r + dr)
        p = board.get(nsq)
        if p is not None and owner(p) == by and kind(p) == "S" and sq in _soldier_targets(board, nsq, by):
            return True
    return False


def _in_check(board, player) -> bool:
    g = _find_general(board, player)
    return g is not None and _attacked(board, g, 1 - player)


@dataclass
class XQState:
    board: dict = field(default_factory=dict)   # (c, r) -> piece letter
    to_move: int = RED
    halfmove: int = 0                            # plies since last capture
    ply: int = 0
    reps: dict = field(default_factory=dict)     # position key -> count


class Xiangqi(Game):
    uid = "xiangqi"
    name = "Xiangqi"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> XQState:
        return XQState(board=_start_board())

    def current_player(self, s: XQState) -> int:
        return s.to_move

    def _draw(self, s: XQState) -> bool:
        return (s.halfmove >= NO_CAPTURE_DRAW or s.ply >= PLY_CAP
                or any(v >= 3 for v in s.reps.values()))

    def _gen(self, s: XQState) -> list:
        """Fully legal (from, to) moves for the side to move."""
        moves = []
        for sq, p in s.board.items():
            if owner(p) != s.to_move:
                continue
            for to in _pseudo_targets(s.board, sq):
                nb = dict(s.board)
                nb[to] = nb.pop(sq)
                if not _in_check(nb, s.to_move):
                    moves.append((sq, to))
        return moves

    def legal_moves(self, s: XQState) -> list[str]:
        if self._draw(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._gen(s)]

    def apply_move(self, s: XQState, move: str, rng=None) -> XQState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        capture = to in board
        board[to] = board.pop(frm)
        halfmove = 0 if capture else s.halfmove + 1
        reps = {} if capture else dict(s.reps)        # captures are irreversible
        key = self._key(board, 1 - s.to_move)
        reps[key] = reps.get(key, 0) + 1
        return XQState(board=board, to_move=1 - s.to_move,
                       halfmove=halfmove, ply=s.ply + 1, reps=reps)

    def _key(self, board, to_move) -> str:
        return str(to_move) + "|" + ",".join(
            f"{c}{r}{p}" for (c, r), p in sorted(board.items()))

    def is_terminal(self, s: XQState) -> bool:
        return self._draw(s) or not self._gen(s)

    def returns(self, s: XQState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move (checkmate or stalemate): the side to move loses
        return [-1.0, 1.0] if s.to_move == RED else [1.0, -1.0]

    def serialize(self, s: XQState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
        }

    def deserialize(self, d: dict) -> XQState:
        return XQState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
        )

    def describe_move(self, s: XQState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        p = s.board.get(frm, "?")
        cap = "x" if to in s.board else "-"
        alg = lambda c: f"{'abcdefghi'[c[0]]}{c[1]}"  # noqa: E731
        return f"{p}{alg(frm)}{cap}{alg(to)}"

    def render(self, s: XQState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": owner(p), "label": kind(p)}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = ("Draw" if ret == [0.0, 0.0]
                       else f"{NAMES[RED if ret[0] > 0 else BLACK]} wins")
        elif _in_check(s.board, s.to_move):
            caption = f"{NAMES[s.to_move]} to move (check)"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
