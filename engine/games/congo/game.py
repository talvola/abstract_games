"""Congo — Demian Freeling's 7x7 animal chess variant (1982).

Two players on a 7x7 board. The middle row (rank 4) is a *river*; each side
has a 3x3 *castle* (files c-e x its own three ranks) housing its Lion. You win
by CAPTURING the enemy Lion — there is no check rule: moving into attack is
legal, the opponent simply takes the Lion and wins. Stalemate (no legal move)
loses for the stalemated player.

Pieces per side: Lion, 2 Elephants, 2* Giraffe/Zebra/Crocodile/Monkey (one
each), 7 Pawns. See rules.md for exact movement. The crux rules:

* Lion: king step, confined to its castle; may capture the enemy Lion by
  moving as a queen along an open file or diagonal (the "facing lions" rule).
* Monkey: king-step move; captures draughts-style by jumping an adjacent enemy
  to the empty square beyond, with optional chain jumps (never mandatory, may
  stop anytime, each man jumped once, squares may be revisited, jumped men
  removed only after the whole move; jumping the Lion ends move and game).
* Drowning: except the Crocodile, a piece that is in the river at the end of
  its owner's turn drowns (is removed) UNLESS it entered the river this very
  move. (Equivalently: ending two consecutive own turns in the river drowns —
  and a river piece whose owner moves something else drowns too.)

State is a plain board dict + a position-count history (threefold repetition
draw). Win is an event stored in ``winner``. Honest draws: threefold
repetition, the published two-bare-lions adjudication, and a hard ply cap.

Standalone ``agp.game.Game`` (NOT ChessLike): Congo has no check/checkmate
machinery, multi-leg capture paths, move-only vs capture-only steps, and an
end-of-turn drowning side effect — nothing of ChessLike's core applies.

Cells are "col,row": col 0..6 = files a..g, row 0..6 = ranks 1..7. White
(player 0) starts on rows 0-1 and moves toward row 6.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 7
RIVER_ROW = 3
PLY_CAP = 600
REPETITION = 3

NAMES = {0: "White", 1: "Black"}

KIND_NAME = {
    "L": "Lion", "Z": "Zebra", "E": "Elephant", "G": "Giraffe",
    "C": "Crocodile", "M": "Monkey", "P": "Pawn", "S": "Superpawn",
}

KING_DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
ORTH_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
KNIGHT = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]

CASTLE_COLS = (2, 3, 4)
CASTLE_ROWS = {0: (0, 1, 2), 1: (4, 5, 6)}

# Rough material values for the rollout-cutoff heuristic (Lion excluded).
PIECE_VALUES = {"P": 1.0, "S": 2.0, "G": 2.0, "Z": 3.0, "E": 3.0, "C": 4.0, "M": 4.0}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _cid(c, r) -> str:
    return f"{c},{r}"


def _on(c, r) -> bool:
    return 0 <= c < N and 0 <= r < N


def _fwd(pl: int) -> int:
    return 1 if pl == 0 else -1


def _last_rank(pl: int) -> int:
    return N - 1 if pl == 0 else 0


def _past_river(pl: int, r: int) -> bool:
    return r > RIVER_ROW if pl == 0 else r < RIVER_ROW


def _in_castle(pl: int, c: int, r: int) -> bool:
    return c in CASTLE_COLS and r in CASTLE_ROWS[pl]


@dataclass
class CongoState:
    board: dict = field(default_factory=dict)   # (c, r) -> (player, kind)
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0
    history: dict = field(default_factory=dict)  # poskey -> count (repetition)


def _poskey(board: dict, to_move: int) -> str:
    items = ";".join(f"{c},{r}:{pl}{k}" for (c, r), (pl, k) in sorted(board.items()))
    return f"{to_move}|{items}"


def _start_board() -> dict:
    b: dict = {}
    back = "GMELECZ"  # files a..g: Giraffe Monkey Elephant Lion Elephant Croc Zebra
    for c, k in enumerate(back):
        b[(c, 0)] = (0, k)
        b[(c, 6)] = (1, k)
    for c in range(N):
        b[(c, 1)] = (0, "P")
        b[(c, 5)] = (1, "P")
    return b


# --------------------------------------------------------------------------- #
# Move generation
# --------------------------------------------------------------------------- #

def _lion_face_target(board: dict, pl: int):
    """If `pl`'s lion may capture the enemy lion (open file/diagonal), return
    (frm, to), else None."""
    mine = enemy = None
    for cell, (p, k) in board.items():
        if k == "L":
            if p == pl:
                mine = cell
            else:
                enemy = cell
    if mine is None or enemy is None:
        return None
    dc, dr = enemy[0] - mine[0], enemy[1] - mine[1]
    if not (dc == 0 or abs(dc) == abs(dr)):
        return None  # only along a file or a diagonal (never a rank: castles)
    uc = (dc > 0) - (dc < 0)
    ur = (dr > 0) - (dr < 0)
    c, r = mine[0] + uc, mine[1] + ur
    while (c, r) != enemy:
        if (c, r) in board:
            return None
        c, r = c + uc, r + ur
    return (mine, enemy)


def _monkey_paths(board: dict, frm, pl: int):
    """All monkey capture paths (>=1 jump) from `frm`. Jumped men stay on the
    board (as blockers) during the chain and each may be jumped only once;
    squares may be revisited; the chain may stop after any jump; jumping the
    enemy Lion terminates the chain."""
    b = dict(board)
    del b[frm]  # the monkey has left its square; it may revisit/end there
    out = []

    def dfs(pos, jumped, path):
        for dc, dr in KING_DIRS:
            over = (pos[0] + dc, pos[1] + dr)
            land = (pos[0] + 2 * dc, pos[1] + 2 * dr)
            if not _on(*land) or land in b:
                continue
            tgt = b.get(over)
            if tgt is None or tgt[0] == pl or over in jumped:
                continue
            npath = path + [land]
            out.append(npath)
            if tgt[1] != "L":  # jumping the Lion ends move and game
                dfs(land, jumped | {over}, npath)

    dfs(frm, frozenset(), [frm])
    return out


def _piece_targets(board: dict, cell, pl: int, kind: str):
    """Single-destination targets (set of cells) for a non-monkey-jump move."""
    c, r = cell
    t = set()

    def try_to(nc, nr, capture=True, move=True):
        if not _on(nc, nr):
            return
        occ = board.get((nc, nr))
        if occ is None:
            if move:
                t.add((nc, nr))
        elif occ[0] != pl and capture:
            t.add((nc, nr))

    if kind == "L":
        for dc, dr in KING_DIRS:
            nc, nr = c + dc, r + dr
            if _in_castle(pl, nc, nr):
                try_to(nc, nr)
        face = _lion_face_target(board, pl)
        if face is not None and face[0] == cell:
            t.add(face[1])
    elif kind == "Z":
        for dc, dr in KNIGHT:
            try_to(c + dc, r + dr)
    elif kind == "E":
        for dc, dr in ORTH_DIRS:
            try_to(c + dc, r + dr)
            try_to(c + 2 * dc, r + 2 * dr)  # jump: intervening square ignored
    elif kind == "G":
        for dc, dr in KING_DIRS:
            try_to(c + dc, r + dr, capture=False)          # step: move only
            try_to(c + 2 * dc, r + 2 * dr)                 # jump: move or capture
    elif kind == "C":
        for dc, dr in KING_DIRS:
            try_to(c + dc, r + dr)
        if r != RIVER_ROW:
            # rook toward the river along the file, up to and incl. the river
            ur = 1 if r < RIVER_ROW else -1
            nr = r + ur
            while True:
                occ = board.get((c, nr))
                if occ is None:
                    t.add((c, nr))
                else:
                    if occ[0] != pl:
                        t.add((c, nr))
                    break
                if nr == RIVER_ROW:
                    break
                nr += ur
        else:
            # rook along the river row, both directions
            for uc in (1, -1):
                nc = c + uc
                while _on(nc, RIVER_ROW):
                    occ = board.get((nc, RIVER_ROW))
                    if occ is None:
                        t.add((nc, RIVER_ROW))
                    else:
                        if occ[0] != pl:
                            t.add((nc, RIVER_ROW))
                        break
                    nc += uc
    elif kind == "M":
        for dc, dr in KING_DIRS:
            try_to(c + dc, r + dr, capture=False)  # step: move only (jumps separate)
    elif kind in ("P", "S"):
        f = _fwd(pl)
        for dc in (-1, 0, 1):
            try_to(c + dc, r + f)                  # forward: move or capture
        if kind == "S":
            try_to(c - 1, r, capture=True)
            try_to(c + 1, r, capture=True)         # sideways: move or capture
            back_dirs = [(-1, -f), (0, -f), (1, -f)]   # straight or diagonal back
        else:
            back_dirs = [(0, -f)] if _past_river(pl, r) else []
        for dc, dr in back_dirs:                   # retreat: move only, no jumping
            n1 = (c + dc, r + dr)
            if _on(*n1) and n1 not in board:
                t.add(n1)
                n2 = (c + 2 * dc, r + 2 * dr)
                if _on(*n2) and n2 not in board:
                    t.add(n2)
    return t


def _moves(s: CongoState):
    """All legal move strings for the player to move."""
    out = []
    pl = s.to_move
    for cell, (p, kind) in s.board.items():
        if p != pl:
            continue
        for to in sorted(_piece_targets(s.board, cell, pl, kind)):
            out.append(f"{_cid(*cell)}>{_cid(*to)}")
        if kind == "M":
            for path in _monkey_paths(s.board, cell, pl):
                out.append(">".join(_cid(*x) for x in path))
    return out


# --------------------------------------------------------------------------- #

class Congo(Game):
    name = "Congo"
    PLY_CAP = PLY_CAP

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CongoState:
        board = _start_board()
        return CongoState(board=board, history={_poskey(board, 0): 1})

    def current_player(self, s: CongoState) -> int:
        return s.to_move

    def legal_moves(self, s: CongoState):
        if self.is_terminal(s):
            return []
        return _moves(s)

    def apply_move(self, s: CongoState, move: str, rng=None) -> CongoState:
        cells = [_cell(x) for x in move.split(">")]
        frm, final = cells[0], cells[-1]
        board = dict(s.board)
        pl, kind = board.pop(frm)
        winner = None

        if kind == "M" and any(
            max(abs(b[0] - a[0]), abs(b[1] - a[1])) == 2
            for a, b in zip(cells, cells[1:])
        ):
            # monkey capture chain: every leg is a 2-step jump over an enemy
            for a, b in zip(cells, cells[1:]):
                mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
                taken = board.pop(mid)
                if taken[1] == "L":
                    winner = pl
        else:
            occ = board.get(final)
            if occ is not None:
                if occ[1] == "L":
                    winner = pl

        if kind == "P" and final[1] == _last_rank(pl):
            kind = "S"  # promotion (always a Superpawn; no choice)
        board[final] = (pl, kind)

        # Drowning: at the end of the mover's turn, every one of the mover's
        # non-crocodile pieces in the river drowns, EXCEPT the moved piece if
        # it entered the river this move (started outside it).
        entered = frm[1] != RIVER_ROW
        for c in range(N):
            cell = (c, RIVER_ROW)
            occ = board.get(cell)
            if occ is None or occ[0] != pl or occ[1] == "C":
                continue
            if cell == final and entered:
                continue
            del board[cell]

        nxt = 1 - pl
        history = dict(s.history)
        if winner is None:
            key = _poskey(board, nxt)
            history[key] = history.get(key, 0) + 1
        return CongoState(board=board, to_move=nxt, winner=winner,
                          ply=s.ply + 1, history=history)

    # ---- termination ---- #
    def _repetition(self, s: CongoState) -> bool:
        return s.history.get(_poskey(s.board, s.to_move), 0) >= REPETITION

    def _bare_lions_draw(self, s: CongoState) -> bool:
        """Only the two lions remain and the mover cannot capture: draw
        (gamerz.net / Wikipedia endgame adjudication)."""
        if len(s.board) != 2 or any(k != "L" for (_, k) in s.board.values()):
            return False
        return _lion_face_target(s.board, s.to_move) is None

    def is_terminal(self, s: CongoState) -> bool:
        if s.winner is not None:
            return True
        if s.ply >= PLY_CAP or self._repetition(s) or self._bare_lions_draw(s):
            return True
        return not _moves(s)

    def returns(self, s: CongoState):
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if not _moves(s):
            # stalemated player must move but cannot: loses (no draw by stalemate)
            return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]
        return [0.0, 0.0]  # repetition / bare-lions / ply-cap draw

    def heuristic(self, s: CongoState):
        bal = 0.0
        for (pl, k) in s.board.values():
            v = PIECE_VALUES.get(k, 0.0)
            bal += v if pl == 0 else -v
        x = math.tanh(bal / 8.0)
        return [x, -x]

    # ---- serialize ---- #
    def serialize(self, s: CongoState) -> dict:
        return {
            "board": {_cid(c, r): [pl, k] for (c, r), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "history": dict(s.history),
        }

    def deserialize(self, d: dict) -> CongoState:
        return CongoState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d["ply"],
            history=dict(d["history"]),
        )

    # ---- presentation ---- #
    def describe_move(self, s: CongoState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        pl, kind = s.board[cells[0]]
        alg = lambda x: f"{'abcdefg'[x[0]]}{x[1] + 1}"  # noqa: E731
        jump_legs = kind == "M" and any(
            max(abs(b[0] - a[0]), abs(b[1] - a[1])) == 2
            for a, b in zip(cells, cells[1:])
        )
        if jump_legs:
            txt = kind + "x".join(alg(x) for x in cells)
            took_lion = any(
                s.board.get(((a[0] + b[0]) // 2, (a[1] + b[1]) // 2), (None, ""))[1] == "L"
                for a, b in zip(cells, cells[1:])
            )
        else:
            occ = s.board.get(cells[-1])
            sep = "x" if occ is not None else "-"
            txt = f"{kind}{alg(cells[0])}{sep}{alg(cells[-1])}"
            took_lion = occ is not None and occ[1] == "L"
        if kind == "P" and cells[-1][1] == _last_rank(pl):
            txt += "=S"
        if took_lion:
            txt += "#"
        return txt

    def render(self, s: CongoState, perspective=None) -> dict:
        pieces = [
            {"cell": _cid(c, r), "owner": pl, "label": k}
            for (c, r), (pl, k) in s.board.items()
        ]
        tints = {}
        for pl in (0, 1):
            for c in CASTLE_COLS:
                for r in CASTLE_ROWS[pl]:
                    tints[_cid(c, r)] = "#3d3019"   # castles (tan)
        for c in range(N):
            tints[_cid(c, RIVER_ROW)] = "#173a4d"   # the river

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins (lion captured)"
        elif self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw"
            else:
                caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins (no moves)"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
