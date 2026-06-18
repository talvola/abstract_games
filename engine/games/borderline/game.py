"""Borderline (Gerd P. Degens, 2022) -- a minimalist 7x7 chess variant.

* Each side has R N B Q B N R on its back rank (rows 0 and 6); no pawns.
* A single NEUTRAL king sits in the centre (d4). On a turn a player moves one of
  their own pieces OR the king.
* Pieces move by FIDE rules but CANNOT capture pieces -- they only move to empty
  squares. Only the king can be captured (which wins).
* The king may stand only on ranks 3-5 (rows 2-4). Rank 4 (row 3) is the
  "borderline". A piece may attack the king only beyond the borderline: White
  threatens the king on rank 5 (row 4), Black on rank 3 (row 2); rank 4 is safe.
* You may not move the king into the opponent's attack ("own check"), but you may
  push it into your own attack zone. If, on your turn, the king is in check (the
  opponent threatens it) and you cannot remove the threat, you lose.

This variant doesn't fit the shared ChessLike base (neutral king, no captures,
zone-based check), so it only reuses the movement geometry from agp.chesslike.
A ply cap forces a draw since, with no captures, material never changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game
from agp.chesslike import ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK

N = 7
BORDER = 3                 # rank 4 (row 3) -- the borderline
KING_ROWS = (2, 3, 4)      # ranks 3-5: where the king may stand
PLY_CAP = 160

PIECE_SLIDES = {"R": ORTHO, "B": DIAG, "Q": ALL8}   # N is a leaper; K handled separately


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _attacks_king(board, king, attacker) -> bool:
    """Can ``attacker`` capture the (neutral) king? Only beyond the borderline:
    White attacks on rows 4-6, Black on rows 0-2 (the king only ever sits on
    rows 2-4, so in practice White checks on row 4 and Black on row 2)."""
    kc, kr = king
    if attacker == WHITE and kr <= BORDER:
        return False
    if attacker == BLACK and kr >= BORDER:
        return False
    for dc, dr in KNIGHT:
        if board.get((kc + dc, kr + dr)) == (attacker, "N"):
            return True
    for dirs, types in ((ORTHO, ("R", "Q")), (DIAG, ("B", "Q"))):
        for dc, dr in dirs:
            cc, rr = kc + dc, kr + dr
            while _on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] == attacker and occ[1] in types:
                        return True
                    break
                cc += dc
                rr += dr
    return False


@dataclass
class BorderState:
    board: dict = field(default_factory=dict)   # (c, r) -> (player, piece); king NOT here
    king: tuple = (3, 3)
    to_move: int = WHITE
    ply: int = 0


class Borderline(Game):
    uid = "borderline"
    name = "Borderline"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> BorderState:
        back = ["R", "N", "B", "Q", "B", "N", "R"]
        board = {}
        for c in range(N):
            board[(c, 0)] = (WHITE, back[c])
            board[(c, 6)] = (BLACK, back[c])
        return BorderState(board=board, king=(3, 3), to_move=WHITE, ply=0)

    def current_player(self, s: BorderState) -> int:
        return s.to_move

    def _pseudo(self, s: BorderState):
        occupied = set(s.board) | {s.king}
        for (pc, pr), (pl, t) in s.board.items():
            if pl != s.to_move:
                continue
            if t == "N":
                for dc, dr in KNIGHT:
                    to = (pc + dc, pr + dr)
                    if _on(*to) and to not in occupied:
                        yield (pc, pr), to
            else:
                for dc, dr in PIECE_SLIDES[t]:
                    cc, rr = pc + dc, pr + dr
                    while _on(cc, rr) and (cc, rr) not in occupied:
                        yield (pc, pr), (cc, rr)
                        cc += dc
                        rr += dr
        # the neutral king (either player may move it) -- one step within its zone
        kc, kr = s.king
        for dc, dr in ALL8:
            to = (kc + dc, kr + dr)
            if _on(*to) and to[1] in KING_ROWS and to not in occupied:
                yield s.king, to

    def _after(self, s: BorderState, frm, to):
        """(board, king) after moving frm->to, for the check test."""
        if frm == s.king:
            return s.board, to
        b = dict(s.board)
        b[to] = b.pop(frm)
        return b, s.king

    def legal_moves(self, s: BorderState) -> list[str]:
        if s.ply >= PLY_CAP:
            return []
        if _attacks_king(s.board, s.king, s.to_move):
            return []                       # mover could capture the king -> already won
        opp = 1 - s.to_move
        out = []
        for frm, to in self._pseudo(s):
            nb, nk = self._after(s, frm, to)
            if not _attacks_king(nb, nk, opp):   # may not leave the king capturable by the opponent
                out.append(f"{frm[0]},{frm[1]}>{to[0]},{to[1]}")
        return out

    def apply_move(self, s: BorderState, move: str, rng=None) -> BorderState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        if frm == s.king:
            return BorderState(board=s.board, king=to, to_move=1 - s.to_move, ply=s.ply + 1)
        board = dict(s.board)
        board[to] = board.pop(frm)
        return BorderState(board=board, king=s.king, to_move=1 - s.to_move, ply=s.ply + 1)

    def is_terminal(self, s: BorderState) -> bool:
        return len(self.legal_moves(s)) == 0

    def returns(self, s: BorderState) -> list[float]:
        win = lambda p: [1.0, -1.0] if p == WHITE else [-1.0, 1.0]  # noqa: E731
        opp = 1 - s.to_move
        if _attacks_king(s.board, s.king, s.to_move):
            return win(s.to_move)                        # king capturable by the mover
        if s.ply >= PLY_CAP:
            return [0.0, 0.0]
        if _attacks_king(s.board, s.king, opp) and not self.legal_moves(s):
            return win(opp)                              # in check, no escape -> mover loses
        return [0.0, 0.0]                                # stalemate / cap -> draw

    def serialize(self, s: BorderState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in s.board.items()},
            "king": f"{s.king[0]},{s.king[1]}",
            "to_move": s.to_move,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> BorderState:
        return BorderState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            king=_cell(d["king"]),
            to_move=d["to_move"],
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: BorderState, move: str) -> str:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        t = "K" if frm == s.king else s.board.get(frm, (None, "?"))[1]
        alg = lambda c: f"{'abcdefg'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{t}{alg(frm)}-{alg(to)}"

    def render(self, s: BorderState, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": t}
            for (c, r), (pl, t) in s.board.items()
        ]
        pieces.append({"cell": f"{s.king[0]},{s.king[1]}", "owner": 2, "label": "K"})
        highlights = [{"cell": f"{s.king[0]},{s.king[1]}", "kind": "goal"}]
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins"
        else:
            opp = 1 - s.to_move
            chk = " (check)" if _attacks_king(s.board, s.king, opp) else ""
            caption = f"{names[s.to_move]} to move{chk}"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
