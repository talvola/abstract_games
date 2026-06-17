"""Los Alamos chess — simplified 6x6 chess (Stein & Wells, MANIAC I, 1956).

Differences from orthodox chess: 6x6 board, no bishops (the queen still moves in
all 8 directions), no castling, no double pawn step, no en passant. Pawns
promote on the far rank to Queen, Rook, or Knight (no bishop).

Moves use the platform's clickable cell-path notation: "fromCol,fromRow>toCol,
toRow", e.g. "2,1>2,2". A promotion adds a choice suffix: "from>to=Q" (=Q/=R/=N)
— the UI shows a picker. White = player 0 (rows 0-1, up); Black = player 1
(rows 4-5, down).

Draw rules (also guarantee termination for random play): stalemate, a 50-ply
no-capture-no-pawn-move rule, and a hard 200-ply cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 6
WHITE, BLACK = 0, 1
DRAW_HALFMOVE = 50
PLY_CAP = 200

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL8 = ORTHO + DIAG
KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
BACK_RANK = ["R", "N", "Q", "K", "N", "R"]


@dataclass
class ChessState:
    board: dict = field(default_factory=dict)  # (c, r) -> (player, piece_letter)
    to_move: int = WHITE
    halfmove: int = 0   # plies since last capture or pawn move
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    for c in range(N):
        b[(c, 0)] = (WHITE, BACK_RANK[c])
        b[(c, 1)] = (WHITE, "P")
        b[(c, 4)] = (BLACK, "P")
        b[(c, 5)] = (BLACK, BACK_RANK[c])
    return b


def _attacked(board: dict, c: int, r: int, by: int) -> bool:
    """Is square (c, r) attacked by player `by`?"""
    for dc, dr in KNIGHT:
        if board.get((c + dc, r + dr)) == (by, "N"):
            return True
    for dc, dr in ALL8:
        if board.get((c + dc, r + dr)) == (by, "K"):
            return True
    # pawns: a `by` pawn attacks one rank toward the opponent
    pr = r - 1 if by == WHITE else r + 1
    for dc in (-1, 1):
        if board.get((c + dc, pr)) == (by, "P"):
            return True
    for dirs, sliders in ((ORTHO, ("R", "Q")), (DIAG, ("Q",))):
        for dc, dr in dirs:
            cc, rr = c + dc, r + dr
            while _on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] == by and occ[1] in sliders:
                        return True
                    break
                cc += dc
                rr += dr
    return False


def _king(board: dict, player: int):
    for (c, r), (pl, t) in board.items():
        if pl == player and t == "K":
            return c, r
    return None


def _in_check(board: dict, player: int) -> bool:
    k = _king(board, player)
    return k is not None and _attacked(board, k[0], k[1], 1 - player)


def _pseudo_moves(board: dict, player: int):
    """All pseudo-legal moves (ignoring own-king-in-check) as (from, to)."""
    for (c, r), (pl, t) in list(board.items()):
        if pl != player:
            continue
        if t in ("K", "N"):
            for dc, dr in (ALL8 if t == "K" else KNIGHT):
                tc, tr = c + dc, r + dr
                if _on(tc, tr) and (board.get((tc, tr)) or (None,))[0] != player:
                    yield (c, r), (tc, tr)
        elif t in ("R", "Q"):
            for dc, dr in (ORTHO if t == "R" else ALL8):
                cc, rr = c + dc, r + dr
                while _on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is None:
                        yield (c, r), (cc, rr)
                    else:
                        if occ[0] != player:
                            yield (c, r), (cc, rr)
                        break
                    cc += dc
                    rr += dr
        elif t == "P":
            fwd = 1 if player == WHITE else -1
            if _on(c, r + fwd) and (c, r + fwd) not in board:
                yield (c, r), (c, r + fwd)
            for dc in (-1, 1):
                occ = board.get((c + dc, r + fwd))
                if occ is not None and occ[0] != player:
                    yield (c, r), (c + dc, r + fwd)


def _apply_board(board: dict, frm, to) -> dict:
    """New board after a move (auto-queening promotions). For check-testing."""
    b = dict(board)
    pl, t = b.pop(frm)
    if t == "P" and (to[1] == N - 1 and pl == WHITE or to[1] == 0 and pl == BLACK):
        t = "Q"
    b[to] = (pl, t)
    return b


class LosAlamosChess(Game):
    uid = "los_alamos_chess"
    name = "Los Alamos Chess"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ChessState:
        return ChessState(board=_start_board())

    def current_player(self, s: ChessState) -> int:
        return s.to_move

    def _legal(self, s: ChessState):
        moves = []
        for frm, to in _pseudo_moves(s.board, s.to_move):
            nb = _apply_board(s.board, frm, to)
            if not _in_check(nb, s.to_move):
                moves.append((frm, to))
        return moves

    def _is_promotion(self, board: dict, frm, to) -> bool:
        pl, t = board[frm]
        return t == "P" and ((to[1] == N - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK))

    def legal_moves(self, s: ChessState) -> list[str]:
        if self._draw(s):
            return []
        out = []
        for f, t in self._legal(s):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if self._is_promotion(s.board, f, t):
                out += [base + "=Q", base + "=R", base + "=N"]
            else:
                out.append(base)
        return out

    def _draw(self, s: ChessState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def apply_move(self, s: ChessState, move: str, rng=None) -> ChessState:
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        pl, t = s.board[frm]
        capture = to in s.board
        b = dict(s.board)
        b.pop(frm)
        if t == "P" and (to[1] == N - 1 and pl == WHITE or to[1] == 0 and pl == BLACK):
            t = promo if promo in ("Q", "R", "N") else "Q"
        b[to] = (pl, t)
        reset = capture or s.board[frm][1] == "P"
        return ChessState(
            board=b,
            to_move=1 - pl,
            halfmove=0 if reset else s.halfmove + 1,
            ply=s.ply + 1,
        )

    def is_terminal(self, s: ChessState) -> bool:
        return self._draw(s) or len(self._legal(s)) == 0

    def returns(self, s: ChessState) -> list[float]:
        # draw / stalemate
        if self._draw(s) or not _in_check(s.board, s.to_move):
            return [0.0, 0.0]
        # checkmate: the player to move is mated and loses
        return [-1.0, 1.0] if s.to_move == WHITE else [1.0, -1.0]

    def serialize(self, s: ChessState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> ChessState:
        return ChessState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            halfmove=d["halfmove"],
            ply=d["ply"],
        )

    def describe_move(self, s: ChessState, move: str) -> str:
        promo = None
        mv = move
        if "=" in mv:
            mv, promo = mv.split("=")
        fs, ts = mv.split(">")
        frm, to = _cell(fs), _cell(ts)
        pl, t = s.board.get(frm, (None, "?"))
        capture = to in s.board
        alg = lambda c: f"{'abcdef'[c[0]]}{c[1] + 1}"  # noqa: E731
        text = f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}"
        if promo:
            text += f"={promo}"
        return text

    def render(self, s: ChessState, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": t}
            for (c, r), (pl, t) in s.board.items()
        ]
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(s):
            r = self.returns(s)
            caption = "Draw" if r == [0.0, 0.0] else f"{names[0 if r[0] > 0 else 1]} wins (checkmate)"
        elif _in_check(s.board, s.to_move):
            caption = f"{names[s.to_move]} to move (check)"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
