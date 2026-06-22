"""Bagh-Chal (Tigers and Goats) -- the Nepali hunt game on a 5x5 alquerque board.

Asymmetric: player 0 = **Goats** (20 of them, placed one per turn, then moved),
player 1 = **Tigers** (4, starting in the corners). Goats move first. Pieces slide
one step along a board line to an empty point; a Tiger may also *jump* an adjacent
Goat along a line to the empty point beyond, capturing it. **Tigers win by
capturing five Goats; Goats win by trapping every Tiger** (no Tiger can move). A
side with no legal move loses.

The board is the 25-point alquerque grid: orthogonal neighbours are always
connected, diagonals only at "strong" points where (c + r) is even. Points are
addressed "c,r" with c, r in 0..4.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 5
GOAT, TIGER = 0, 1
GOATS_TOTAL = 20
GOATS_TO_LOSE = 5          # tigers win once this many goats are captured
PLY_CAP = 400

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _strong(c, r):
    return (c + r) % 2 == 0


def _dirs(c, r):
    return ORTHO + DIAG if _strong(c, r) else ORTHO


def _adj():
    adj = {}
    for c in range(N):
        for r in range(N):
            adj[(c, r)] = frozenset(
                (c + dc, r + dr) for (dc, dr) in _dirs(c, r) if _on(c + dc, r + dr)
            )
    return adj


ADJ = _adj()


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
CORNERS = [(0, 0), (4, 0), (0, 4), (4, 4)]


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class BState:
    board: dict = field(default_factory=dict)        # (c,r) -> GOAT/TIGER
    to_move: int = GOAT
    in_hand: int = GOATS_TOTAL                        # goats yet to be placed
    captured: int = 0                                 # goats captured by tigers
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class BaghChal(Game):
    uid = "bagh_chal"
    name = "Bagh-Chal"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {sq: TIGER for sq in CORNERS}
        st = BState(board=board, to_move=GOAT)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- moves -------------------------------------------------------------
    def _tiger_moves(self, board):
        """(frm, to, captured_or_None) for every tiger step and jump."""
        for sq, who in board.items():
            if who != TIGER:
                continue
            c, r = sq
            for (dc, dr) in _dirs(c, r):
                step = (c + dc, r + dr)
                if not _on(*step):
                    continue
                if step not in board:
                    yield sq, step, None
                elif board[step] == GOAT:
                    land = (c + 2 * dc, r + 2 * dr)
                    if _on(*land) and land not in board:
                        yield sq, land, step      # jump capturing the goat at `step`

    def _goat_slides(self, board):
        for sq, who in board.items():
            if who != GOAT:
                continue
            for to in ADJ[sq]:
                if to not in board:
                    yield sq, to

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        if state.to_move == GOAT:
            if state.in_hand > 0:
                return [f"{c},{r}" for (c, r) in _all_points() if (c, r) not in state.board]
            return [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for (f, t) in self._goat_slides(state.board)]
        return [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for (f, t, _) in self._tiger_moves(state.board)]

    def apply_move(self, state, move, rng=None):
        board = dict(state.board)
        in_hand, captured = state.in_hand, state.captured
        if ">" not in move:                      # goat placement
            board[_cell(move)] = GOAT
            in_hand -= 1
        else:
            frm, to = (_cell(x) for x in move.split(">"))
            who = board.pop(frm)
            board[to] = who
            is_jump = max(abs(to[0] - frm[0]), abs(to[1] - frm[1])) == 2
            if who == TIGER and is_jump:
                mid = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
                if board.get(mid) == GOAT:
                    del board[mid]
                    captured += 1
        nxt = 1 - state.to_move
        ns = BState(board=board, to_move=nxt, in_hand=in_hand, captured=captured,
                    ply=state.ply + 1, reps=dict(state.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        self._settle(ns)
        return ns

    def _settle(self, ns):
        if ns.captured >= GOATS_TO_LOSE:
            ns.winner = TIGER
            return
        # the side to move with no legal move loses (tigers trapped -> goats win)
        if not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = 1 - ns.to_move

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.ply >= PLY_CAP
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
                     for (c, r) in _all_points() if (c, r) in state.board)
        return f"{b}#{state.to_move}#{state.in_hand}#{state.captured}"

    def serialize(self, state):
        return {
            "board": {f"{c},{r}": v for (c, r), v in state.board.items()},
            "to_move": state.to_move, "in_hand": state.in_hand,
            "captured": state.captured, "ply": state.ply,
            "reps": dict(state.reps), "winner": state.winner,
        }

    def deserialize(self, d):
        return BState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], in_hand=d["in_hand"], captured=d["captured"],
            ply=d.get("ply", 0), reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if ">" not in move:
            return f"goat@{move}"
        frm, to = move.split(">")
        f, t = _cell(frm), _cell(to)
        cap = abs(t[0] - f[0]) == 2 or abs(t[1] - f[1]) == 2
        return f"{frm}{'x' if cap else '-'}{to}"

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), who in state.board.items():
            pieces.append({"cell": f"{c},{r}", "owner": who,
                           "label": "T" if who == TIGER else "G"})
        if state.winner is not None:
            cap = ("Tigers win" if state.winner == TIGER else "Goats win")
        elif self._draw(state):
            cap = "Draw"
        else:
            side = "Goats" if state.to_move == GOAT else "Tigers"
            extra = (f" — place ({state.in_hand} in hand)"
                     if state.to_move == GOAT and state.in_hand > 0 else "")
            cap = f"{side} to move{extra}  ·  captured {state.captured}/{GOATS_TO_LOSE}"
        return {
            "board": {"type": "square", "width": N, "height": N, "lines": LINES},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }


def _all_points():
    return [(c, r) for r in range(N) for c in range(N)]
