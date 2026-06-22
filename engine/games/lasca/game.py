"""Lasca (Laska) -- Emanuel Lasker's 1911 checkers variant with **towers**.

Played on the 25 dark squares of a 7x7 board, 11 men a side. Pieces move and
capture diagonally like draughts, but **capturing does not remove a piece**:
instead you take the **top** piece of the jumped column and tuck it under the
**bottom** of your moving column as a prisoner. A column (tower) is controlled by
whoever owns its **top** piece, and only that top piece's powers count; capturing
the top can liberate a friendly piece buried beneath. Soldiers move and capture
forward; an officer (a soldier promoted on the last rank) moves and captures in
all four diagonal directions. Captures are compulsory and a multi-capture must be
played to the end. You lose if you cannot move.

This is the platform's first **stacking** game: the renderer shows each square's
column as layered owner-coloured discs with a height badge. Squares are "c,r" on a
7x7 grid; a move is a ">"-path of squares (a simple step, or a jump chain).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 7
WHITE, BLACK = 0, 1
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
NO_CAPTURE_DRAW = 40        # plies without a capture or promotion -> draw
PLY_CAP = 400


def _on(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE and (c + r) % 2 == 0


def _fwd(player):
    return 1 if player == WHITE else -1


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


# A piece is (owner, is_officer); a column is a tuple of pieces, bottom -> top.
def _top(col):
    return col[-1]


def _controller(col):
    return col[-1][0]


@dataclass
class LState:
    board: dict = field(default_factory=dict)        # (c,r) -> column tuple
    to_move: int = WHITE
    since: int = 0                                    # plies since capture/promotion
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class Lasca(Game):
    uid = "lasca"
    name = "Lasca"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {}
        for r in range(SIZE):
            for c in range(SIZE):
                if not _on(c, r):
                    continue
                if r <= 2:
                    board[(c, r)] = ((WHITE, False),)
                elif r >= 4:
                    board[(c, r)] = ((BLACK, False),)
        st = LState(board=board, to_move=WHITE)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _dirs(self, piece, player):
        if piece[1]:                      # officer: all four diagonals
            return DIAG
        f = _fwd(player)
        return [(1, f), (-1, f)]          # soldier: the two forward diagonals

    def _capture_paths(self, board, sq, col, player):
        """Yield full forced jump chains [(sq, land1, land2, ...)] from `sq`."""
        top = _top(col)
        found = False
        for (dc, dr) in self._dirs(top, player):
            over = (sq[0] + dc, sq[1] + dr)
            land = (sq[0] + 2 * dc, sq[1] + 2 * dr)
            if not _on(*land) or land in board or over not in board:
                continue
            ocol = board[over]
            if _controller(ocol) == player:
                continue
            # apply this jump on a copy, then recurse
            nb = dict(board)
            prisoner = _top(ocol)
            rest = ocol[:-1]
            if rest:
                nb[over] = rest
            else:
                del nb[over]
            ncol = (prisoner,) + col       # captured piece tucked under the bottom
            nb[land] = ncol
            found = True
            tails = list(self._capture_paths(nb, land, ncol, player))
            if tails:
                for t in tails:
                    yield [sq] + t
            else:
                yield [sq, land]
        if not found:
            return

    def _all_captures(self, board, player):
        out = []
        for sq, col in board.items():
            if _controller(col) != player:
                continue
            for path in self._capture_paths(board, sq, col, player):
                out.append(path)
        return out

    def _simple_moves(self, board, player):
        out = []
        for sq, col in board.items():
            if _controller(col) != player:
                continue
            for (dc, dr) in self._dirs(_top(col), player):
                to = (sq[0] + dc, sq[1] + dr)
                if _on(*to) and to not in board:
                    out.append([sq, to])
        return out

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        caps = self._all_captures(state.board, state.to_move)
        paths = caps if caps else self._simple_moves(state.board, state.to_move)
        return [">".join(f"{c},{r}" for (c, r) in p) for p in paths]

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        pts = [_cell(s) for s in move.split(">")]
        board = dict(state.board)
        player = state.to_move
        col = board.pop(pts[0])
        captured = False
        for i in range(1, len(pts)):
            frm, to = pts[i - 1], pts[i]
            if abs(to[0] - frm[0]) == 2:               # a jump
                over = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
                ocol = board[over]
                col = (_top(ocol),) + col              # tuck prisoner under
                rest = ocol[:-1]
                if rest:
                    board[over] = rest
                else:
                    del board[over]
                captured = True
            # else: a simple step (single segment)
        landing = pts[-1]
        promoted = False
        top_owner, top_off = _top(col)
        last_rank = (SIZE - 1 if player == WHITE else 0)
        if not top_off and top_owner == player and landing[1] == last_rank:
            col = col[:-1] + ((player, True),)         # promote the top piece
            promoted = True
        board[landing] = col

        since = 0 if (captured or promoted) else state.since + 1
        ns = LState(board=board, to_move=1 - player, since=since,
                    ply=state.ply + 1, reps=dict(state.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        if not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = player                          # opponent has no move
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.ply >= PLY_CAP
                     or state.since >= NO_CAPTURE_DRAW
                     or state.reps.get(self._key(state), 0) >= 3))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- keys / serialise --------------------------------------------------
    def _col_str(self, col):
        return "".join(("WB"[o] if f else "wb"[o]) for (o, f) in col)

    def _parse_col(self, s):
        return tuple((0 if ch in "wW" else 1, ch.isupper()) for ch in s)

    def _key(self, state):
        b = "|".join(f"{c},{r}:{self._col_str(state.board[(c, r)])}"
                     for r in range(SIZE) for c in range(SIZE) if (c, r) in state.board)
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        return {
            "board": {f"{c},{r}": self._col_str(col) for (c, r), col in state.board.items()},
            "to_move": state.to_move, "since": state.since, "ply": state.ply,
            "reps": dict(state.reps), "winner": state.winner,
        }

    def deserialize(self, d):
        return LState(
            board={_cell(k): self._parse_col(v) for k, v in d["board"].items()},
            to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        pts = move.split(">")
        jump = any(abs(_cell(pts[i])[0] - _cell(pts[i - 1])[0]) == 2
                   for i in range(1, len(pts)))
        return ("x" if jump else "-").join(pts)

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), col in state.board.items():
            top = _top(col)
            pieces.append({
                "cell": f"{c},{r}",
                "owner": top[0],
                "stack": [o for (o, _f) in col],       # bottom -> top owners
                "label": "O" if top[1] else "",        # O marks an officer on top
            })
        names = {WHITE: "White", BLACK: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        else:
            caps = self._all_captures(state.board, state.to_move)
            cap = f"{names[state.to_move]} to move" + (" (must capture)" if caps else "")
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
