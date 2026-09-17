"""Tawlbwrdd — the Welsh tafl, 11x11, after Robert ap Ifan (1587).

Tawlbwrdd is the Welsh member of the tafl family. The only near-contemporary
account is Robert ap Ifan's 1587 manuscript (Peniarth MS 158), translated by
H. J. R. Murray (*A History of Board-Games Other Than Chess*, p.63):

    "The above board must be played with a king in the centre and twelve men in
    the places next to him, and twenty-four lie in wait to capture him. These are
    placed, six in the centre of every end of the board and in the six central
    places. ... if one belonging to the king comes between the attackers, he is
    dead and is thrown out of the play; and if one of the attackers comes between
    two of the king's men, the same. If the king himself comes between two of the
    attackers and if you say 'watch your king' before he moves into that place,
    and he is unable to escape, you catch him. ... If the king can go along the
    line that side wins the game."

That passage fixes the three rules that make Tawlbwrdd a DIFFERENT GAME from the
11x11 Copenhagen Hnefatafl also in this library (uid `hnefatafl`), rather than a
re-skin of it:

* The KING IS CAPTURED LIKE ANY OTHER PIECE — between **two** attackers on
  opposite sides ("if the king himself comes between two of the attackers").
  Copenhagen needs all four sides.
* The king ESCAPES TO ANY EDGE SQUARE ("if the king can go along the line"), not
  to a corner.
* THERE ARE NO SPECIAL SQUARES. The manuscript mentions no privilege for the
  central square and none for the corners, and the game works without them, so
  the throne neither shelters the king nor blocks anyone, and the corners are
  ordinary squares. Copenhagen makes both restricted AND hostile.

Rules as implemented follow Damian Walker's reconstruction (Cyningstan,
tafl.cyningstan.com/page/172/tawlbwrdd), which fills ap Ifan's gaps from the
better-documented Tablut. See rules.md for the full writeup and for the points
where the sources disagree.

Options:

* `layout` — the attackers' formation, the one genuinely open question in the
  reconstruction. `t` (default) is the T-shape of Cyningstan's illustrated
  starting position: five along each edge plus one stepping inward. `bell` is
  R. C. Bell's 1969 reconstruction: a 3-2-1 arrow against each edge.
  The 12 defenders form the same diamond in both.
* `throne` — `none` (default, Cyningstan: the centre is an ordinary square) or
  `restricted`, the reading in which the central square is reserved to the king,
  as in Tablut. Aage Nielsen's balance testing favours a throne.

Pieces: "A" attacker (player 0), "D" defender soldier (player 1), "K" king
(player 1). Cells are "col,row"; moves are clickable "from>to" paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 11
THRONE = (5, 5)
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
PLY_CAP = 400
ATTACKERS, DEFENDERS = 0, 1

# The 12 defenders: the same diamond around the throne in every published
# reconstruction (1-3-5-3-1, king at the centre of the middle row).
DEFENDERS_DIAMOND = [
    (5, 3),
    (4, 4), (5, 4), (6, 4),
    (3, 5), (4, 5), (6, 5), (7, 5),
    (4, 6), (5, 6), (6, 6),
    (5, 7),
]

# Attacker formations, given for the TOP edge as (col, row) offsets from the
# board's top-left-ish anchor and then reflected to the other three edges.
# `t`    — five along the edge, one stepping inward (Cyningstan's diagram).
# `bell` — a 3-2-1 arrow pointing inward (R. C. Bell, 1969).
_T_GROUP = [(3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (5, 1)]
_BELL_GROUP = [(4, 0), (5, 0), (6, 0), (4, 1), (6, 1), (5, 2)]


@dataclass
class TaflState:
    board: dict = field(default_factory=dict)   # (c, r) -> "A" | "D" | "K"
    to_move: int = ATTACKERS
    winner: Optional[int] = None
    ply: int = 0
    restricted_throne: bool = False


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _owner(piece: str) -> int:
    return ATTACKERS if piece == "A" else DEFENDERS


def _is_edge(c, r) -> bool:
    return c == 0 or r == 0 or c == N - 1 or r == N - 1


def _start_board(layout: str) -> dict:
    """King + 12 defenders in the diamond, and 24 attackers in four groups of six
    (one per edge). The top-edge group is mirrored/rotated onto all four edges, so
    the position has the full four-fold symmetry every source's diagram shows."""
    b = {THRONE: "K"}
    for cell in DEFENDERS_DIAMOND:
        b[cell] = "D"
    group = _BELL_GROUP if layout == "bell" else _T_GROUP
    for c, r in group:
        b[(c, r)] = "A"                       # top edge
        b[(c, N - 1 - r)] = "A"               # bottom edge (reflect the row)
        b[(r, c)] = "A"                       # left edge (transpose)
        b[(N - 1 - r, c)] = "A"               # right edge
    return b


class Tawlbwrdd(Game):
    name = "Tawlbwrdd"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TaflState:
        options = options or {}
        return TaflState(
            board=_start_board(options.get("layout", "t")),
            restricted_throne=bool(options.get("throne", "none") == "restricted"),
        )

    def current_player(self, s: TaflState) -> int:
        return s.to_move

    def _blocked(self, s: TaflState, cell, is_king: bool) -> bool:
        """May this piece STOP on `cell`? Only the optional restricted throne ever
        says no; with `throne=none` (the default) every empty square is legal."""
        return s.restricted_throne and cell == THRONE and not is_king

    def _moves(self, s: TaflState) -> list:
        out = []
        for (c, r), piece in s.board.items():
            if _owner(piece) != s.to_move:
                continue
            is_king = piece == "K"
            for dc, dr in ORTHO:
                cc, rr = c + dc, r + dr
                while _on(cc, rr) and (cc, rr) not in s.board:
                    # Nothing ever blocks a slider in Tawlbwrdd: a piece may always
                    # pass over the (empty) centre, and the corners are ordinary
                    # squares. Only STOPPING on a restricted throne is forbidden.
                    if not self._blocked(s, (cc, rr), is_king):
                        out.append(((c, r), (cc, rr)))
                    cc += dc
                    rr += dr
        return out

    def legal_moves(self, s: TaflState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._moves(s)]

    def apply_move(self, s: TaflState, move: str, rng=None) -> TaflState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        piece = board.pop(frm)
        board[to] = piece
        player = s.to_move
        king_taken = False

        # Custodial capture, ACTIVE (only the piece that just moved can trigger it)
        # and one deep in each direction: ap Ifan's "it is not possible to capture a
        # row of pieces". The KING is captured on exactly the same terms as a
        # soldier -- that is the rule that most sets Tawlbwrdd apart from Copenhagen.
        for dc, dr in ORTHO:
            mid = (to[0] + dc, to[1] + dr)
            beyond = (to[0] + 2 * dc, to[1] + 2 * dr)
            occ = board.get(mid)
            if occ is None or _owner(occ) == player:
                continue
            anchor = board.get(beyond)
            if _on(*beyond) and anchor is not None and _owner(anchor) == player:
                del board[mid]
                if occ == "K":
                    king_taken = True

        winner = None
        if piece == "K" and _is_edge(*to):
            winner = DEFENDERS                      # "if the king can go along the line"
        elif king_taken:
            winner = ATTACKERS                      # king caught between two attackers
        elif not self._side_has_move(board, 1 - player, s.restricted_throne):
            winner = player                         # opponent has no legal move

        return TaflState(
            board=board,
            to_move=1 - player,
            winner=winner,
            ply=s.ply + 1,
            restricted_throne=s.restricted_throne,
        )

    def _side_has_move(self, board: dict, player: int, restricted_throne: bool) -> bool:
        for (c, r), piece in board.items():
            if _owner(piece) != player:
                continue
            is_king = piece == "K"
            for dc, dr in ORTHO:
                cc, rr = c + dc, r + dr
                while _on(cc, rr) and (cc, rr) not in board:
                    if not (restricted_throne and (cc, rr) == THRONE and not is_king):
                        return True
                    cc += dc
                    rr += dr
        return False

    def is_terminal(self, s: TaflState) -> bool:
        return s.winner is not None or s.ply >= PLY_CAP or not self._moves(s)

    def returns(self, s: TaflState) -> list[float]:
        if s.winner is None:
            if s.ply >= PLY_CAP:
                return [0.0, 0.0]                   # cap -> an honest draw
            w = 1 - s.to_move                       # no legal move -> to_move loses
        else:
            w = s.winner
        # ATTACKERS are seat 0, DEFENDERS seat 1 (see rules.md "Winning").
        return [1.0, -1.0] if w == ATTACKERS else [-1.0, 1.0]

    def heuristic(self, s: TaflState) -> list[float]:
        """Attackers want material and a boxed-in king; the defenders want the king
        near an edge. Returns [attackers, defenders], squashed to about -1..+1."""
        king = next((c for c, p in s.board.items() if p == "K"), None)
        if king is None:
            return [1.0, -1.0]
        atk = sum(1 for p in s.board.values() if p == "A")
        dfn = sum(1 for p in s.board.values() if p == "D")
        # material: attackers start 24 v 12, so compare against that ratio
        material = (atk / 24.0) - (dfn / 12.0)
        # king run: 0 when the king is on an edge (a win), 1 at the centre
        run = min(king[0], king[1], N - 1 - king[0], N - 1 - king[1]) / 5.0
        score = 0.55 * material + 0.45 * (2.0 * run - 1.0)
        score = max(-1.0, min(1.0, score))
        return [score, -score]

    def serialize(self, s: TaflState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "restricted_throne": s.restricted_throne,
        }

    def deserialize(self, d: dict) -> TaflState:
        return TaflState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            restricted_throne=d.get("restricted_throne", False),
        )

    def describe_move(self, s: TaflState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcdefghijk'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{s.board.get(frm, '?')}:{alg(frm)}-{alg(to)}"

    def render(self, s: TaflState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": _owner(p), "label": "",
                   "glyph": "♚" if p == "K" else None}
                  for (c, r), p in s.board.items()]
        names = {ATTACKERS: "Attackers", DEFENDERS: "Defenders"}
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = ("Draw" if ret == [0.0, 0.0]
                       else f"{names[ATTACKERS if ret[0] > 0 else DEFENDERS]} win")
        else:
            caption = f"{names[s.to_move]} to move"
        # Every edge square is a goal: the king escapes "along the line".
        goals = [f"{c},{r}" for c in range(N) for r in range(N) if _is_edge(c, r)]
        spec = {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [{"cell": g, "kind": "goal"} for g in goals],
            "caption": caption,
        }
        if s.restricted_throne:
            spec["board"]["tints"] = {f"{THRONE[0]},{THRONE[1]}": "#d8cbb0"}
        return spec
