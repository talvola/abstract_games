"""Alquerque -- the ancient Near-Eastern capture game that is the common ancestor
of draughts/checkers and of Fanorona. Played on the 5x5 alquerque board (lines
orthogonal everywhere, diagonal at the "strong" points where c+r is even).

Each side has 12 pieces; the centre starts empty. A piece steps one point along a
line to an empty point, or jumps an adjacent enemy along a line to the empty point
beyond, removing it (as in draughts). Captures are compulsory and chain. Capture
all of the enemy -- or leave them with no move -- to win.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 5
WHITE, BLACK = 0, 1
PLY_CAP = 300
NO_CAPTURE_DRAW = 40

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _strong(c, r):
    return (c + r) % 2 == 0


def _dirs(c, r):
    return ORTHO + DIAG if _strong(c, r) else ORTHO


def _lines():
    segs = []
    for r in range(N):
        for c in range(N):
            if c + 1 < N:
                segs.append([[c, r], [c + 1, r]])
            if r + 1 < N:
                segs.append([[c, r], [c, r + 1]])
            if _strong(c, r):
                if c + 1 < N and r + 1 < N:
                    segs.append([[c, r], [c + 1, r + 1]])
                if c + 1 < N and r - 1 >= 0:
                    segs.append([[c, r], [c + 1, r - 1]])
    return segs


LINES = _lines()


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class AState:
    board: dict = field(default_factory=dict)        # (c,r) -> WHITE/BLACK
    to_move: int = WHITE
    since: int = 0
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class Alquerque(Game):
    uid = "alquerque"
    name = "Alquerque"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {}
        for r in range(N):
            for c in range(N):
                if r < 2 or (r == 2 and c < 2):
                    board[(c, r)] = WHITE
                elif r > 2 or (r == 2 and c > 2):
                    board[(c, r)] = BLACK
        st = AState(board=board, to_move=WHITE)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _capture_paths(self, board, sq, player):
        found = False
        c, r = sq
        for (dc, dr) in _dirs(c, r):
            over = (c + dc, r + dr)
            land = (c + 2 * dc, r + 2 * dr)
            if not _on(*land) or land in board or board.get(over) not in (1 - player,):
                continue
            nb = dict(board)
            del nb[over]
            del nb[sq]
            nb[land] = player
            found = True
            tails = list(self._capture_paths(nb, land, player))
            if tails:
                for t in tails:
                    yield [sq] + t
            else:
                yield [sq, land]
        if not found:
            return

    def _all_captures(self, board, player):
        out = []
        for sq, who in board.items():
            if who == player:
                out.extend(self._capture_paths(board, sq, player))
        return out

    def _steps(self, board, player):
        out = []
        for (c, r), who in board.items():
            if who != player:
                continue
            for (dc, dr) in _dirs(c, r):
                to = (c + dc, r + dr)
                if _on(*to) and to not in board:
                    out.append([(c, r), to])
        return out

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        caps = self._all_captures(state.board, state.to_move)
        paths = caps if caps else self._steps(state.board, state.to_move)
        return [">".join(f"{c},{r}" for (c, r) in p) for p in paths]

    def apply_move(self, state, move, rng=None):
        pts = [_cell(s) for s in move.split(">")]
        board = dict(state.board)
        player = state.to_move
        who = board.pop(pts[0])
        captured = False
        for i in range(1, len(pts)):
            frm, to = pts[i - 1], pts[i]
            if max(abs(to[0] - frm[0]), abs(to[1] - frm[1])) == 2:
                mid = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
                board.pop(mid, None)
                captured = True
        board[pts[-1]] = who
        since = 0 if captured else state.since + 1
        ns = AState(board=board, to_move=1 - player, since=since,
                    ply=state.ply + 1, reps=dict(state.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        # win by annihilation or by leaving the opponent unable to move
        if not any(v == ns.to_move for v in board.values()):
            ns.winner = player
        elif not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = player
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.ply >= PLY_CAP or state.since >= NO_CAPTURE_DRAW
                     or state.reps.get(self._key(state), 0) >= 3))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- keys / serialise --------------------------------------------------
    def _key(self, state):
        b = ",".join(f"{c},{r}:{state.board[(c, r)]}"
                     for r in range(N) for c in range(N) if (c, r) in state.board)
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        return {"board": {f"{c},{r}": v for (c, r), v in state.board.items()},
                "to_move": state.to_move, "since": state.since, "ply": state.ply,
                "reps": dict(state.reps), "winner": state.winner}

    def deserialize(self, d):
        return AState(board={_cell(k): v for k, v in d["board"].items()},
                      to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
                      reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        pts = move.split(">")
        jump = any(max(abs(_cell(pts[i])[0] - _cell(pts[i - 1])[0]),
                       abs(_cell(pts[i])[1] - _cell(pts[i - 1])[1])) == 2
                   for i in range(1, len(pts)))
        return ("x" if jump else "-").join(pts)

    def render(self, state, perspective=None):
        names = {WHITE: "White", BLACK: "Black"}
        pieces = [{"cell": f"{c},{r}", "owner": who} for (c, r), who in state.board.items()]
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        else:
            must = self._all_captures(state.board, state.to_move)
            cap = f"{names[state.to_move]} to move" + (" (must capture)" if must else "")
        return {
            "board": {"type": "square", "width": N, "height": N, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
