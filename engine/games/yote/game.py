"""Yote -- a West African war game on a 5x6 board. Its signature: when you capture
by jumping, you ALSO remove a second enemy piece of your choice.

Both players start with 12 men in hand and an empty board. On your turn you may
drop a man from hand onto an empty cell, OR move a man one step orthogonally to an
empty cell, OR jump orthogonally over an adjacent enemy to the empty cell beyond
(removing it) -- and after such a capture you immediately take one more enemy man
from anywhere on the board. Capturing is not compulsory. Win by capturing all of
the enemy (or leaving them with no move).

Cells are "col,row" (col 0..4, row 0..5). A drop and a "remove a second man" both
look like a single cell click; the engine's `removing` flag tells them apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

W, H = 5, 6
MEN = 12
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
NO_PROGRESS_DRAW = 50
PLY_CAP = 400


def _on(c, r):
    return 0 <= c < W and 0 <= r < H


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class YoteState:
    board: dict = field(default_factory=dict)        # (c,r) -> player
    hands: list = field(default_factory=lambda: [MEN, MEN])
    to_move: int = 0
    removing: bool = False
    since: int = 0                                    # plies since a capture/drop
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class Yote(Game):
    uid = "yote"
    name = "Yote"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        st = YoteState()
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, s):
        return s.to_move

    def _count(self, board, pl):
        return sum(1 for v in board.values() if v == pl)

    def _moves(self, board, pl):
        out = []
        for (c, r), who in board.items():
            if who != pl:
                continue
            for dc, dr in ORTHO:
                step = (c + dc, r + dr)
                if _on(*step) and step not in board:
                    out.append(f"{c},{r}>{step[0]},{step[1]}")
                elif _on(*step) and board.get(step) == 1 - pl:
                    land = (c + 2 * dc, r + 2 * dr)
                    if _on(*land) and land not in board:
                        out.append(f"{c},{r}>{land[0]},{land[1]}")
        return out

    def legal_moves(self, s):
        if s.winner is not None or self._draw(s):
            return []
        pl = s.to_move
        if s.removing:
            return [f"{c},{r}" for (c, r), who in s.board.items() if who == 1 - pl]
        out = list(self._moves(s.board, pl))
        if s.hands[pl] > 0:
            out += [f"{c},{r}" for r in range(H) for c in range(W) if (c, r) not in s.board]
        return out

    def apply_move(self, s, move, rng=None):
        pl = s.to_move
        board = dict(s.board)
        hands = list(s.hands)
        since = s.since + 1

        if s.removing:
            del board[_cell(move)]                    # bonus removal
            return self._finish(board, hands, 1 - pl, False, 0, s)

        if ">" in move:                               # move or jump
            frm, to = (_cell(x) for x in move.split(">"))
            board[to] = board.pop(frm)
            if max(abs(to[0] - frm[0]), abs(to[1] - frm[1])) == 2:
                mid = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
                del board[mid]
                since = 0
                # bonus: remove one more enemy if any remain
                if self._count(board, 1 - pl) > 0:
                    return self._finish(board, hands, pl, True, since, s)
                return self._finish(board, hands, 1 - pl, False, since, s)
            return self._finish(board, hands, 1 - pl, False, since, s)

        # a bare cell with no '>' and not removing -> a drop from hand
        board[_cell(move)] = pl
        hands[pl] -= 1
        return self._finish(board, hands, 1 - pl, False, 0, s)

    def _finish(self, board, hands, to_move, removing, since, s):
        ns = YoteState(board=board, hands=hands, to_move=to_move, removing=removing,
                       since=since, ply=s.ply + 1, reps=dict(s.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        if not removing and not self._draw(ns):
            opp = to_move
            if self._count(board, opp) == 0 and hands[opp] == 0:
                ns.winner = 1 - opp                   # opponent annihilated
            elif not self.legal_moves(ns):
                ns.winner = 1 - opp                   # opponent has no move
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, s):
        # Never declare a draw mid-bonus-removal: the pending capture must resolve
        # first (otherwise the ply cap could strand a turn before its 2nd removal).
        return (s.winner is None and not s.removing
                and (s.ply >= PLY_CAP or s.since >= NO_PROGRESS_DRAW
                     or s.reps.get(self._key(s), 0) >= 3))

    def is_terminal(self, s):
        return s.winner is not None or self._draw(s)

    def returns(self, s):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # ---- keys / serialise --------------------------------------------------
    def _key(self, s):
        b = ",".join(f"{c},{r}:{s.board[(c, r)]}"
                     for r in range(H) for c in range(W) if (c, r) in s.board)
        return f"{b}#{s.to_move}#{s.hands[0]}{s.hands[1]}#{int(s.removing)}"

    def serialize(self, s):
        return {"board": {f"{c},{r}": v for (c, r), v in s.board.items()},
                "hands": list(s.hands), "to_move": s.to_move, "removing": s.removing,
                "since": s.since, "ply": s.ply, "reps": dict(s.reps), "winner": s.winner}

    def deserialize(self, d):
        return YoteState(board={_cell(k): v for k, v in d["board"].items()},
                         hands=list(d["hands"]), to_move=d["to_move"],
                         removing=d.get("removing", False), since=d.get("since", 0),
                         ply=d.get("ply", 0), reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s, move):
        if s.removing:
            return f"x{move}"
        if ">" in move:
            f, t = move.split(">")
            cap = max(abs(_cell(t)[0] - _cell(f)[0]), abs(_cell(t)[1] - _cell(f)[1])) == 2
            return f"{f}{'x' if cap else '-'}{t}"
        return f"@{move}"

    def render(self, s, perspective=None):
        names = {0: "Player 1", 1: "Player 2"}
        pieces = [{"cell": f"{c},{r}", "owner": who} for (c, r), who in s.board.items()]
        if s.winner is not None:
            cap = f"{names[s.winner]} wins"
        elif self._draw(s):
            cap = "Draw"
        elif s.removing:
            cap = f"{names[s.to_move]}: remove an enemy man"
        else:
            inhand = f" ({s.hands[s.to_move]} in hand)" if s.hands[s.to_move] else ""
            cap = f"{names[s.to_move]} to move{inhand}"
        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
