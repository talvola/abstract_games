"""Bashni (Башни, "towers") -- Russian column draughts, the stacking ancestor of
Lasca.

Played on the 32 dark squares of an 8x8 board, 12 men a side. Pieces move and
capture diagonally, but **capturing does not remove a piece**: you take the
**top** piece of the jumped column and tuck it under the **bottom** of your
moving column as a prisoner; the rest of the jumped column stays in place (now
possibly under new control). A column (tower) is controlled by whoever owns its
**top** piece, and only that top piece's powers count.

Russian draughts geometry:
  * A **man** moves one step diagonally **forward** to an empty square. It
    **captures** by jumping an adjacent enemy-controlled column diagonally
    (**forward OR backward**) to the empty square just beyond.
  * Captures are **mandatory** and **chain** -- a multi-capture is one move.
  * A man that ends (Russian rule: or, while capturing, *reaches*) the far rank
    becomes a **king**: a **flying king** that slides any distance along a
    diagonal and captures an enemy column anywhere ahead, landing on any empty
    square beyond it. See rules.md for the in-chain-promotion choice.

This reuses the platform's **stacking** render (layered owner-coloured discs
with a height badge). Squares are "c,r" on an 8x8 grid; a move is a ">"-path of
squares (a simple step, or a jump chain).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 8
WHITE, BLACK = 0, 1
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
NO_PROGRESS_DRAW = 60       # plies (king-moves) without a capture or promotion -> draw
PLY_CAP = 600


def _on(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE and (c + r) % 2 == 0


def _fwd(player):
    return 1 if player == WHITE else -1


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


# A piece is (owner, is_king); a column is a tuple of pieces, bottom -> top.
def _top(col):
    return col[-1]


def _controller(col):
    return col[-1][0]


@dataclass
class BState:
    board: dict = field(default_factory=dict)        # (c,r) -> column tuple
    to_move: int = WHITE
    since: int = 0                                    # plies since capture/promotion
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class Bashni(Game):
    uid = "bashni"
    name = "Bashni"

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
                elif r >= 5:
                    board[(c, r)] = ((BLACK, False),)
        st = BState(board=board, to_move=WHITE)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- capture generation -----------------------------------------------
    def _capture_paths(self, board, sq, col, player):
        """Yield full forced jump chains [sq, land1, land2, ...] from `sq`.

        The top piece's king-status decides reach: a man jumps an *adjacent*
        enemy column landing one beyond; a king slides any distance to an enemy
        column with only empties between, then lands on any empty square
        beyond it (flying king). Captures may go forward or backward.
        """
        top = _top(col)
        is_king = top[1]
        found = False
        for (dc, dr) in DIAG:
            jumps = self._jumps_in_dir(board, sq, dc, dr, player, is_king)
            for (over, land) in jumps:
                ocol = board[over]
                prisoner = _top(ocol)
                rest = ocol[:-1]
                nb = dict(board)
                if rest:
                    nb[over] = rest
                else:
                    del nb[over]
                ncol = (prisoner,) + col       # captured top tucked under the bottom
                # Russian rule: a man that REACHES the far rank during a capture
                # promotes immediately and continues the chain as a flying king.
                last_rank = (SIZE - 1 if player == WHITE else 0)
                if not is_king and ncol[-1][0] == player and land[1] == last_rank:
                    ncol = ncol[:-1] + ((player, True),)
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

    def _jumps_in_dir(self, board, sq, dc, dr, player, is_king):
        """Return [(over, land), ...] legal single captures from sq in (dc,dr)."""
        out = []
        if not is_king:
            over = (sq[0] + dc, sq[1] + dr)
            land = (sq[0] + 2 * dc, sq[1] + 2 * dr)
            if _on(*land) and land not in board and over in board \
                    and _controller(board[over]) != player:
                out.append((over, land))
            return out
        # flying king: scan along the diagonal for the first occupied square
        c, r = sq[0] + dc, sq[1] + dr
        over = None
        while _on(c, r):
            if (c, r) in board:
                if _controller(board[(c, r)]) == player:
                    return out          # blocked by a friendly-controlled column
                over = (c, r)
                break
            c += dc
            r += dr
        if over is None:
            return out                  # no piece to jump in this direction
        # landing squares: every empty square beyond `over` until blocked
        c, r = over[0] + dc, over[1] + dr
        while _on(c, r) and (c, r) not in board:
            out.append((over, (c, r)))
            c += dc
            r += dr
        return out

    def _all_captures(self, board, player):
        out = []
        for sq, col in board.items():
            if _controller(col) != player:
                continue
            for path in self._capture_paths(board, sq, col, player):
                out.append(path)
        return out

    # ---- simple (non-capturing) moves -------------------------------------
    def _simple_moves(self, board, player):
        out = []
        for sq, col in board.items():
            if _controller(col) != player:
                continue
            top = _top(col)
            if top[1]:                                  # flying king: slide any distance
                for (dc, dr) in DIAG:
                    c, r = sq[0] + dc, sq[1] + dr
                    while _on(c, r) and (c, r) not in board:
                        out.append([sq, (c, r)])
                        c += dc
                        r += dr
            else:                                       # man: one step forward
                f = _fwd(player)
                for dc in (1, -1):
                    to = (sq[0] + dc, sq[1] + f)
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
        promoted = False
        last_rank = (SIZE - 1 if player == WHITE else 0)
        for i in range(1, len(pts)):
            frm, to = pts[i - 1], pts[i]
            step = abs(to[0] - frm[0])
            # a jump captures iff there is an enemy column strictly between frm/to
            dc = 1 if to[0] > frm[0] else -1
            dr = 1 if to[1] > frm[1] else -1
            over = None
            c, r = frm[0] + dc, frm[1] + dr
            while (c, r) != to:
                if (c, r) in board:
                    over = (c, r)
                    break
                c += dc
                r += dr
            if over is not None:                        # this segment is a jump
                ocol = board[over]
                col = (_top(ocol),) + col               # tuck prisoner under the bottom
                rest = ocol[:-1]
                if rest:
                    board[over] = rest
                else:
                    del board[over]
                captured = True
                # Russian rule: promote the instant a man reaches the far rank
                # during a capture, so the rest of the chain runs as a king.
                tk_owner, tk_king = _top(col)
                if not tk_king and tk_owner == player and to[1] == last_rank:
                    col = col[:-1] + ((player, True),)
                    promoted = True
            # else: a simple step (the single segment of a non-capturing move)

        landing = pts[-1]
        top_owner, top_king = _top(col)
        if not top_king and top_owner == player and landing[1] == last_rank:
            col = col[:-1] + ((player, True),)          # promote on a simple step to the far rank
            promoted = True
        board[landing] = col

        since = 0 if (captured or promoted) else state.since + 1
        ns = BState(board=board, to_move=1 - player, since=since,
                    ply=state.ply + 1, reps=dict(state.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        if not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = player                          # opponent has no controlled column / no move
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.ply >= PLY_CAP
                     or state.since >= NO_PROGRESS_DRAW
                     or state.reps.get(self._key(state), 0) >= 3))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- keys / serialise --------------------------------------------------
    def _col_str(self, col):
        return "".join(("WB"[o] if k else "wb"[o]) for (o, k) in col)

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
        return BState(
            board={_cell(k): self._parse_col(v) for k, v in d["board"].items()},
            to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        pts = move.split(">")
        jump = any(abs(_cell(pts[i])[0] - _cell(pts[i - 1])[0]) >= 2
                   for i in range(1, len(pts)))
        return ("x" if jump else "-").join(pts)

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), col in state.board.items():
            top = _top(col)
            pieces.append({
                "cell": f"{c},{r}",
                "owner": top[0],
                "stack": [o for (o, _k) in col],       # bottom -> top owners
                "label": "K" if top[1] else "",        # K marks a king on top
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
