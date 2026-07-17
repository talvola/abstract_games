"""Choko -- a traditional West African (Gambia River valley; Mandinka/Fula) war
game on a 5x5 board. Sources: Parker 1909 p.604 (via Ludii's Choko.lud), Murray
1952 "A History of Board-Games Other than Chess" p.83 (via Winther's transcription).

Both players start with 12 sticks in hand and an empty board. On your turn you
drop a stick from hand onto any empty cell, move a stick one step orthogonally
to an empty cell, or jump orthogonally over an adjacent enemy stick to the empty
cell beyond -- the jumped stick is captured AND you then remove a second enemy
stick of your choice from anywhere on the board. Capturing is not compulsory and
only one leap per turn is allowed.

Choko's signature "drop initiative" rule: whenever a player VOLUNTARILY places a
stick, the opponent must also place a stick on their following turn (a forced
reply-drop, which itself forces nothing). Win by capturing all enemy sticks
(board and hand empty), or by leaving the opponent with no legal move.

Cells are "col,row" (col 0..4, row 0..4). A drop and the "remove a second man"
follow-up both look like a single cell click; the engine's `removing` flag tells
them apart.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

W, H = 5, 5
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
class ChokoState:
    board: dict = field(default_factory=dict)        # (c,r) -> player
    hands: list = field(default_factory=lambda: [MEN, MEN])
    to_move: int = 0
    removing: bool = False                            # mid-capture: pick 2nd man
    forced: bool = False                              # mover must reply-drop
    since: int = 0                                    # plies since a capture/drop
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class Choko(Game):
    name = "Choko"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        st = ChokoState()
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

    def _drops(self, board):
        return [f"{c},{r}" for r in range(H) for c in range(W) if (c, r) not in board]

    def legal_moves(self, s):
        if s.winner is not None or self._draw(s):
            return []
        pl = s.to_move
        if s.removing:
            return [f"{c},{r}" for (c, r), who in s.board.items() if who == 1 - pl]
        if s.forced and s.hands[pl] > 0:
            # drop initiative: the opponent placed by choice, so we must place too
            return self._drops(s.board)
        out = list(self._moves(s.board, pl))
        if s.hands[pl] > 0:
            out += self._drops(s.board)
        return out

    def apply_move(self, s, move, rng=None):
        pl = s.to_move
        board = dict(s.board)
        hands = list(s.hands)
        since = s.since + 1

        if s.removing:
            del board[_cell(move)]                    # the free second capture
            return self._finish(board, hands, 1 - pl, False, False, 0, s)

        if ">" in move:                               # step or jump
            frm, to = (_cell(x) for x in move.split(">"))
            board[to] = board.pop(frm)
            if max(abs(to[0] - frm[0]), abs(to[1] - frm[1])) == 2:
                mid = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
                del board[mid]
                since = 0
                # signature rule: also remove any second enemy man, if one remains
                if self._count(board, 1 - pl) > 0:
                    return self._finish(board, hands, pl, True, False, since, s)
                return self._finish(board, hands, 1 - pl, False, False, since, s)
            return self._finish(board, hands, 1 - pl, False, False, since, s)

        # a bare cell with no '>' and not removing -> a drop from hand
        board[_cell(move)] = pl
        hands[pl] -= 1
        # a VOLUNTARY drop forces the opponent to reply with a drop; a forced
        # reply-drop forces nothing (Ludii's Pending encoding of Parker/Murray)
        forced_next = (not s.forced) and hands[1 - pl] > 0
        return self._finish(board, hands, 1 - pl, False, forced_next, 0, s)

    def _finish(self, board, hands, to_move, removing, forced, since, s):
        ns = ChokoState(board=board, hands=hands, to_move=to_move,
                        removing=removing, forced=forced, since=since,
                        ply=s.ply + 1, reps=dict(s.reps))
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
        # Never declare a draw mid-removal: the pending capture must resolve
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

    def heuristic(self, s):
        m0 = self._count(s.board, 0) + s.hands[0]
        m1 = self._count(s.board, 1) + s.hands[1]
        v = math.tanh((m0 - m1) / 4.0)
        return [v, -v]

    # ---- keys / serialise --------------------------------------------------
    def _key(self, s):
        b = ",".join(f"{c},{r}:{s.board[(c, r)]}"
                     for r in range(H) for c in range(W) if (c, r) in s.board)
        return (f"{b}#{s.to_move}#{s.hands[0]}.{s.hands[1]}"
                f"#{int(s.removing)}{int(s.forced)}")

    def serialize(self, s):
        return {"board": {f"{c},{r}": v for (c, r), v in s.board.items()},
                "hands": list(s.hands), "to_move": s.to_move,
                "removing": s.removing, "forced": s.forced,
                "since": s.since, "ply": s.ply, "reps": dict(s.reps),
                "winner": s.winner}

    def deserialize(self, d):
        return ChokoState(board={_cell(k): v for k, v in d["board"].items()},
                          hands=list(d["hands"]), to_move=d["to_move"],
                          removing=d.get("removing", False),
                          forced=d.get("forced", False), since=d.get("since", 0),
                          ply=d.get("ply", 0), reps=dict(d.get("reps", {})),
                          winner=d.get("winner"))

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
            cap = f"{names[s.to_move]}: remove a second enemy stick"
        elif s.forced and s.hands[s.to_move] > 0:
            cap = (f"{names[s.to_move]} must place a stick "
                   f"({s.hands[s.to_move]} in hand)")
        else:
            inhand = f" ({s.hands[s.to_move]} in hand)" if s.hands[s.to_move] else ""
            cap = f"{names[s.to_move]} to move{inhand}"
        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
