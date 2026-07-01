"""King's Valley — Kanare Kato (Logy Games / Kanare_Abstract), 5x5.

A tense little race-to-the-centre game. Each side has 1 King + 4 Soldiers on its
back row, the King on the centre file. Every piece moves like a "maximum-distance"
slider: it picks one of the 8 directions and MUST slide as far as it can, stopping
only at the board edge or the square just before another piece. Mid-slide stops
are illegal (this is the game's defining rule — contrast Amazons, where a queen
may stop anywhere). There are NO captures; pieces only block one another.

The central square (2,2) is the "King's Valley":
  * ONLY a King may END its slide there.
  * A Soldier may never stop on the centre. The centre is otherwise a normal empty
    square — pieces (Kings and Soldiers alike) slide THROUGH it. So a Soldier whose
    maximal slide would naturally end on the centre simply has NO move in that
    direction (it cannot stop short — mid-slide stops are illegal).

WIN: move your King onto the centre (2,2). (Win-as-event: `winner` is set inside
apply_move.)

LOSS: on your turn, if your KING has no legal move, you lose (a "fixed" king). This
is King's-Valley-specific: even if your Soldiers can still move, a trapped King
loses. Passing is illegal.

OPENING: the first player (White) must move a Soldier on the very first move — the
King may not move on ply 0.

Termination: pieces are never removed and positions can repeat, so a defensive ply
cap forces a draw if neither side has won.

Moves are clickable cell-path strings "fc,fr>tc,tr". Player 0 = White (back row 0),
Player 1 = Black (back row 4). White moves first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 5
CENTER = (2, 2)
PLY_CAP = 200  # defensive draw cap (no published value; guarantees termination)
NAMES = {0: "White", 1: "Black"}

# 8 slide directions: orthogonal + diagonal.
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


@dataclass
class KVState:
    # (c, r) -> (owner:int, king:bool)
    board: dict = field(default_factory=dict)
    to_move: int = 0
    ply: int = 0
    winner: int = -1  # -1 = none yet, else the winning player


def _start_board() -> dict:
    board = {}
    for c in range(N):
        is_king = (c == 2)
        board[(c, 0)] = (0, is_king)          # White back row (row 0), King on centre file
        board[(c, N - 1)] = (1, is_king)      # Black back row (row 4), King on centre file
    return board


def _slide_landing(board: dict, start, dc, dr):
    """The maximal-slide landing square from `start` heading (dc,dr): the last
    empty square before an obstacle/edge. Slides THROUGH the empty centre (the
    centre is not special for pass-through). Returns None if the adjacent square
    is already blocked (no move in that direction)."""
    cc, rr = start[0] + dc, start[1] + dr
    last = None
    while _on(cc, rr) and (cc, rr) not in board:
        last = (cc, rr)
        cc += dc
        rr += dr
    return last


class KingsValley(Game):
    uid = "kings_valley"
    name = "King's Valley"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> KVState:
        return KVState(board=_start_board(), to_move=0, ply=0, winner=-1)

    def current_player(self, s: KVState) -> int:
        return s.to_move

    # ---- move generation ----------------------------------------------------
    def _piece_landings(self, board: dict, start, king: bool):
        """Legal maximal-slide landing squares for the piece at `start`."""
        for dc, dr in DIRS:
            land = _slide_landing(board, start, dc, dr)
            if land is None:
                continue
            if land == CENTER and not king:
                # Only a King may stop on the centre; a Soldier can't stop there
                # and can't stop short (mid-slide stops are illegal) -> no move.
                continue
            yield land

    def _all_moves(self, s: KVState):
        """(from, to) pairs for every legal move of the side to move, honouring
        the opening-Soldier restriction (ply 0: the first player can't move the King)."""
        opening = (s.ply == 0)
        for (c, r), (owner, king) in s.board.items():
            if owner != s.to_move:
                continue
            if opening and king:
                continue
            for land in self._piece_landings(s.board, (c, r), king):
                yield (c, r), land

    def _king_can_move(self, s: KVState, player: int) -> bool:
        """Does `player`'s King have at least one legal slide? (Ignores the
        opening restriction — used only to detect the trapped-king loss.)"""
        for (c, r), (owner, king) in s.board.items():
            if owner != player or not king:
                continue
            for _ in self._piece_landings(s.board, (c, r), True):
                return True
            return False
        return False

    def legal_moves(self, s: KVState) -> list:
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._all_moves(s)]

    # ---- apply --------------------------------------------------------------
    def apply_move(self, s: KVState, move: str, rng=None) -> KVState:
        frm, to = (_cell(x) for x in move.split(">"))
        owner, king = s.board[frm]
        board = dict(s.board)
        board.pop(frm)
        board[to] = (owner, king)  # no captures: `to` is always empty

        winner = -1
        if king and to == CENTER:
            winner = owner  # King reached the King's Valley

        return KVState(board=board, to_move=1 - owner, ply=s.ply + 1, winner=winner)

    # ---- terminal / returns -------------------------------------------------
    def is_terminal(self, s: KVState) -> bool:
        if s.winner != -1:
            return True
        if s.ply >= PLY_CAP:
            return True
        # The side to move loses if its King cannot move (a "fixed" king).
        return not self._king_can_move(s, s.to_move)

    def returns(self, s: KVState) -> list:
        if s.winner != -1:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if s.ply >= PLY_CAP:
            return [0.0, 0.0]
        # Trapped king: the side to move loses.
        loser = s.to_move
        return [-1.0, 1.0] if loser == 0 else [1.0, -1.0]

    # ---- (de)serialize ------------------------------------------------------
    def serialize(self, s: KVState) -> dict:
        return {
            "board": {f"{c},{r}": [owner, king] for (c, r), (owner, king) in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> KVState:
        return KVState(
            board={_cell(k): (v[0], bool(v[1])) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner", -1),
        )

    # ---- presentation -------------------------------------------------------
    def describe_move(self, s: KVState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        _, king = s.board[frm]
        alg = lambda p: f"{'abcde'[p[0]]}{p[1] + 1}"  # noqa: E731
        return f"{'K' if king else 'S'}{alg(frm)}-{alg(to)}"

    def render(self, s: KVState, perspective=None) -> dict:
        pieces = []
        for (c, r), (owner, king) in s.board.items():
            pc = {"cell": f"{c},{r}", "owner": owner}
            if king:
                pc["glyph"] = "♚"  # ♚ — distinct King glyph
            else:
                pc["label"] = ""
            pieces.append(pc)

        if s.winner != -1:
            caption = f"{NAMES[s.winner]} wins"
        elif self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret == [0.0, 0.0] else f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move"

        return {
            "board": {
                "type": "square", "width": N, "height": N,
                "tints": {f"{CENTER[0]},{CENTER[1]}": "#ffe08a"},  # mark the King's Valley
            },
            "pieces": pieces,
            "highlights": [{"cell": f"{CENTER[0]},{CENTER[1]}", "kind": "target"}],
            "caption": caption,
        }
