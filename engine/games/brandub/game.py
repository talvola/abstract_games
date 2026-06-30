"""Brandub — the 7x7 Irish tafl (hnefatafl family).

Asymmetric siege. The DEFENDERS (player 1) have a King on the central throne plus
4 men; the ATTACKERS (player 0), twice as many, ring the edges and move first.
All pieces move like a rook (orthogonally, any distance, no jumping). The King
wins by reaching any corner; the attackers win by capturing the King.

Ruleset as implemented (documented because tafl rules vary):
* Restricted squares — the throne (centre) and the 4 corners. Only the King may
  *land* on them; any piece may pass over them when empty.
* Custodial capture — after your move, an enemy *man* is captured if it is
  sandwiched orthogonally between the piece you just moved (or another friendly
  piece) and a friendly piece or a HOSTILE square. Hostile squares are the four
  corners (always) and the throne when the King is not on it. Capture is active:
  a man that moves *between* two enemies is safe.
* The King is captured only by being surrounded on all four orthogonal sides by
  attackers and/or the throne; a King on an edge (a side off the board) is safe.
* A side with no legal move loses. A 200-ply cap draws (tafl can otherwise shuffle
  forever).

Pieces: "A" attacker (player 0), "D" defender man (player 1), "K" king (player 1).
Cells are "col,row"; moves are clickable "from>to" paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 7
THRONE = (3, 3)
CORNERS = {(0, 0), (N - 1, 0), (0, N - 1), (N - 1, N - 1)}
RESTRICTED = CORNERS | {THRONE}
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
PLY_CAP = 200
ATTACKERS, DEFENDERS = 0, 1


@dataclass
class TaflState:
    board: dict = field(default_factory=dict)   # (c, r) -> "A" | "D" | "K"
    to_move: int = ATTACKERS
    winner: Optional[int] = None
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _owner(piece: str) -> int:
    return ATTACKERS if piece == "A" else DEFENDERS


def _start_board() -> dict:
    b = {THRONE: "K"}
    for cell in [(3, 2), (3, 4), (2, 3), (4, 3)]:
        b[cell] = "D"
    for cell in [(3, 0), (3, 1), (3, 5), (3, 6), (0, 3), (1, 3), (5, 3), (6, 3)]:
        b[cell] = "A"
    return b


class Brandub(Game):
    uid = "brandub"
    name = "Brandub"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TaflState:
        return TaflState(board=_start_board())

    def current_player(self, s: TaflState) -> int:
        return s.to_move

    def _moves(self, s: TaflState) -> list:
        out = []
        for (c, r), piece in s.board.items():
            if _owner(piece) != s.to_move:
                continue
            is_king = piece == "K"
            for dc, dr in ORTHO:
                cc, rr = c + dc, r + dr
                while _on(cc, rr) and (cc, rr) not in s.board:
                    # only the king may LAND on a restricted square
                    if (cc, rr) not in RESTRICTED or is_king:
                        out.append(((c, r), (cc, rr)))
                    cc += dc
                    rr += dr
        return out

    def legal_moves(self, s: TaflState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    def _hostile_to(self, board: dict, cell, player: int) -> bool:
        """Does `cell` act as a friendly flank for `player`'s capture?"""
        if cell in CORNERS:
            return True
        if cell == THRONE and board.get(THRONE) != "K":
            return True            # empty throne is hostile to both sides
        occ = board.get(cell)
        return occ is not None and _owner(occ) == player and occ != "K"

    def apply_move(self, s: TaflState, move: str, rng=None) -> TaflState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        piece = board.pop(frm)
        board[to] = piece
        player = s.to_move

        # custodial capture of enemy MEN around the destination
        for dc, dr in ORTHO:
            mid = (to[0] + dc, to[1] + dr)
            beyond = (to[0] + 2 * dc, to[1] + 2 * dr)
            occ = board.get(mid)
            if occ is not None and occ in ("A", "D") and _owner(occ) != player:
                if _on(*beyond) and self._hostile_to(board, beyond, player):
                    del board[mid]

        winner = None
        if piece == "K" and to in CORNERS:
            winner = DEFENDERS                      # king escaped
        elif self._king_captured(board):
            winner = ATTACKERS                      # king surrounded

        return TaflState(board=board, to_move=1 - player, winner=winner, ply=s.ply + 1)

    def _king_captured(self, board: dict) -> bool:
        king = next((c for c, p in board.items() if p == "K"), None)
        if king is None:
            return True
        kc, kr = king
        for dc, dr in ORTHO:
            nc, nr = kc + dc, kr + dr
            if not _on(nc, nr):
                return False                        # an edge side -> safe
            if board.get((nc, nr)) == "A" or (nc, nr) == THRONE:
                continue
            return False
        return True

    def is_terminal(self, s: TaflState) -> bool:
        return s.winner is not None or s.ply >= PLY_CAP or not self._moves(s)

    def returns(self, s: TaflState) -> list[float]:
        if s.winner is None:
            if s.ply >= PLY_CAP:
                return [0.0, 0.0]                   # cap -> draw
            w = 1 - s.to_move                        # no legal move -> to_move loses
        else:
            w = s.winner
        return [1.0, -1.0] if w == ATTACKERS else [-1.0, 1.0]

    def serialize(self, s: TaflState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> TaflState:
        return TaflState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: TaflState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcdefg'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{s.board.get(frm, '?')}:{alg(frm)}-{alg(to)}"

    def render(self, s: TaflState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": _owner(p), "label": "", "glyph": "♚" if p == "K" else None}
                  for (c, r), p in s.board.items()]
        names = {ATTACKERS: "Attackers", DEFENDERS: "Defenders"}
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = ("Draw" if ret == [0.0, 0.0]
                       else f"{names[ATTACKERS if ret[0] > 0 else DEFENDERS]} win")
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [{"cell": f"{c},{r}", "kind": "goal"} for c, r in CORNERS],
            "caption": caption,
        }
