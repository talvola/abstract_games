"""Hnefatafl — the classic 11x11 Norse tafl, modern COPENHAGEN ruleset.

Asymmetric siege. The DEFENDERS (player 1) have a King on the central throne
plus 12 soldiers in a diamond/cross around him; the ATTACKERS (player 0), twice
as many, sit in four T-shaped groups of 6 at the edge midpoints and move first.
All pieces move like a rook (orthogonally, any distance, no jumping). The King
wins by escaping to any CORNER; the attackers win by capturing the King.

Ruleset as implemented (Copenhagen Hnefatafl — documented because tafl rules
vary; see rules.md for the full writeup):

* Restricted squares — the throne (centre) and the four corners. Only the King
  may *stop* on a restricted square; any piece may pass over an empty throne, but
  the corners may only be entered by the King.
* Hostile squares — the four CORNERS are always hostile; the central THRONE is
  hostile while it is EMPTY (i.e. when the King is not standing on it). A hostile
  square acts as a friendly flank for either side's custodial captures.
* Custodial capture — after your move, an enemy *soldier* is captured if it is
  sandwiched orthogonally between the piece you just moved (or another friendly
  piece) and a friendly piece or a HOSTILE square. The KING may assist in
  captures, like any piece. Capture is active: a soldier that moves *between* two
  enemies is safe.
* The King is captured only by being surrounded on all four orthogonal sides by
  attackers and/or hostile squares (a corner or the empty throne). When the King
  stands orthogonally next to the (empty) throne, the throne counts as one wall,
  so throne + 3 attackers captures him. A King on a board edge (one side off the
  board) cannot be surrounded and so is safe there.
* The King WINS by reaching any CORNER square (Copenhagen corner-escape rule).
* A side with no legal move loses. A 400-ply cap draws (tafl can otherwise
  shuffle forever).

Omitted advanced Copenhagen rules (documented in rules.md): shield-wall captures,
exit forts, and the "clear path to a corner" defender win.

Pieces: "A" attacker (player 0), "D" defender soldier (player 1), "K" king
(player 1). Cells are "col,row"; moves are clickable "from>to" paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 11
THRONE = (5, 5)
CORNERS = {(0, 0), (N - 1, 0), (0, N - 1), (N - 1, N - 1)}
RESTRICTED = {THRONE} | CORNERS          # only the King may STOP here
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
PLY_CAP = 400
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
    # 12 defenders: a diamond/cross around the throne — two soldiers out along
    # each orthogonal arm plus the four diagonal corners of the diamond.
    defenders = [
        (5, 3), (5, 4), (5, 6), (5, 7),   # vertical arm
        (3, 5), (4, 5), (6, 5), (7, 5),   # horizontal arm
        (4, 4), (6, 4), (4, 6), (6, 6),   # diagonal points of the diamond
    ]
    for cell in defenders:
        b[cell] = "D"
    # 24 attackers: four T-shaped groups of 6 at the edge midpoints (five along
    # the edge plus one stepping inward toward the centre).
    attackers = [
        (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (5, 1),   # top edge
        (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (5, 9),   # bottom edge
        (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (1, 5),   # left edge
        (10, 3), (10, 4), (10, 5), (10, 6), (10, 7), (9, 5),   # right edge
    ]
    for cell in attackers:
        b[cell] = "A"
    return b


class Hnefatafl(Game):
    uid = "hnefatafl"
    name = "Hnefatafl (Copenhagen)"

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
                    # only the king may LAND on a restricted square (throne/corner);
                    # any piece may pass over an empty throne, but corners block
                    # non-king pieces entirely (they cannot pass through them).
                    if (cc, rr) not in RESTRICTED or is_king:
                        out.append(((c, r), (cc, rr)))
                    if (cc, rr) in CORNERS and not is_king:
                        break          # a corner blocks a non-king slider
                    cc += dc
                    rr += dr
        return out

    def legal_moves(self, s: TaflState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    def _hostile_to(self, board: dict, cell, player: int) -> bool:
        """Does `cell` act as a friendly flank for `player`'s custodial capture?
        Hostile squares (a corner, or the empty throne) flank for either side;
        otherwise the cell must hold one of `player`'s own pieces."""
        if cell in CORNERS:
            return True                # corners are always hostile
        if cell == THRONE and board.get(THRONE) != "K":
            return True                # empty throne is hostile to both sides
        occ = board.get(cell)
        return occ is not None and _owner(occ) == player

    def apply_move(self, s: TaflState, move: str, rng=None) -> TaflState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        piece = board.pop(frm)
        board[to] = piece
        player = s.to_move

        # custodial capture of enemy SOLDIERS around the destination
        for dc, dr in ORTHO:
            mid = (to[0] + dc, to[1] + dr)
            beyond = (to[0] + 2 * dc, to[1] + 2 * dr)
            occ = board.get(mid)
            if occ is not None and occ in ("A", "D") and _owner(occ) != player:
                if _on(*beyond) and self._hostile_to(board, beyond, player):
                    del board[mid]

        winner = None
        if piece == "K" and to in CORNERS:
            winner = DEFENDERS                      # king escaped to a corner
        elif self._king_captured(board):
            winner = ATTACKERS                      # king surrounded
        elif not self._side_has_move(board, 1 - player):
            winner = player                         # opponent has no legal move

        return TaflState(board=board, to_move=1 - player, winner=winner, ply=s.ply + 1)

    def _side_has_move(self, board: dict, player: int) -> bool:
        for (c, r), piece in board.items():
            if _owner(piece) != player:
                continue
            is_king = piece == "K"
            for dc, dr in ORTHO:
                cc, rr = c + dc, r + dr
                while _on(cc, rr) and (cc, rr) not in board:
                    if (cc, rr) not in RESTRICTED or is_king:
                        return True
                    if (cc, rr) in CORNERS and not is_king:
                        break
                    cc += dc
                    rr += dr
        return False

    def _king_captured(self, board: dict) -> bool:
        """Copenhagen: the King is captured when every orthogonal neighbour is an
        attacker or a hostile square (a corner or the empty throne). When the King
        is beside the (empty) throne, the throne is one wall (throne + 3 attackers
        captures). A King on an edge (a side off the board) cannot be surrounded."""
        king = next((c for c, p in board.items() if p == "K"), None)
        if king is None:
            return True
        kc, kr = king
        if king in CORNERS:
            return False                            # the King on a corner has won, not lost
        for dc, dr in ORTHO:
            nc, nr = kc + dc, kr + dr
            if not _on(nc, nr):
                return False                        # an edge side -> cannot surround
            if board.get((nc, nr)) == "A":
                continue                            # attacker wall
            if (nc, nr) == THRONE and board.get(THRONE) != "K":
                continue                            # empty throne is a hostile wall
            if (nc, nr) in CORNERS:
                continue                            # a corner is a hostile wall
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
        alg = lambda c: f"{'abcdefghijk'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{s.board.get(frm, '?')}:{alg(frm)}-{alg(to)}"

    def render(self, s: TaflState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": _owner(p), "label": "K" if p == "K" else ""}
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
