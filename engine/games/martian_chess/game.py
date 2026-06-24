"""Martian Chess — Andrew Looney (Looney Labs / Icehouse, 1999).

A 4-wide x 8-tall board split into two 4x4 zones (quadrants) by a "canal"
between rows 3 and 4. Player 0 owns the bottom zone (rows 0-3), player 1
the top zone (rows 4-7).

THE SIGNATURE RULE — ownership by zone, not by colour:
  Pieces have no colour. On your turn you move any piece that is CURRENTLY
  sitting in YOUR zone. The instant a piece crosses the canal into the other
  zone, it belongs to that player to move next.

Pieces (the three Looney-pyramid sizes), by movement:
  * Pawn  (size 1) — one square diagonally (any of the 4 diagonals).
  * Drone (size 2) — 1 or 2 squares orthogonally in a straight line; no jumping.
  * Queen (size 3) — any distance orthogonally OR diagonally; no jumping.

Capture & scoring:
  Moving onto a square occupied by ANY piece (necessarily in the other zone,
  since your own zone's friendly pieces can only be entered via a merge, see
  below) removes that piece and adds its point value to the MOVER's score
  (Pawn 1, Drone 2, Queen 3).

Field promotion (merging) — base-game rule:
  If you control NO Queens, you may move a Drone onto one of your Pawns (or a
  Pawn onto one of your Drones), removing both and replacing them with a Queen.
  If you control NO Drones, you may move one of your Pawns onto another of your
  Pawns, replacing both with a Drone. Merges happen entirely within your own
  zone and score nothing.

No-take-back (2-player):
  You may not "reject" the opponent's immediately preceding move: if they just
  moved a piece across the canal from B to your zone at A... — precisely, you
  may not move that piece straight back to the square it just came from. We
  implement this as: the move that exactly reverses the opponent's last move
  (same piece, to->from) is forbidden.

Game end & winner:
  The game ends the instant one zone is completely empty. Highest score wins;
  on a tie, the player who made the move that ended the game wins (tie-break
  from the official rules). A hard ply-cap draw guarantees termination
  (NON-ORIGINAL safety rule; a real game empties a zone long before).

Moves are clickable cell paths "from>to" (two "c,r" cells). Player 0 = Red
(bottom), player 1 = Blue (top).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

W, H = 4, 8
CANAL = 4  # rows 0..3 = zone 0, rows 4..7 = zone 1
NAMES = {0: "Red", 1: "Blue"}
LABELS = {1: "P", 2: "D", 3: "Q"}  # size -> label
PLY_CAP = 400  # NON-ORIGINAL hard draw cap; a real game ends far sooner

DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
ORTHO = [(-1, 0), (1, 0), (0, -1), (0, 1)]
ALL8 = DIAG + ORTHO


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _s(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _on(c, r) -> bool:
    return 0 <= c < W and 0 <= r < H


def _zone(r: int) -> int:
    """Which player's zone row r belongs to."""
    return 0 if r < CANAL else 1


def _start_pieces() -> dict:
    """Each zone: a triangular corner block of 9 pieces — 3 Queens in the
    corner (L-shape), 3 Drones on the next diagonal, 3 Pawns on the next.

    Player 0's zone (rows 0-3), corner at (0,0):
        Q at (0,0),(1,0),(0,1);  D at (2,0),(1,1),(0,2);  P at (3,0),(2,1),(1,2)
    Player 1's zone (rows 4-7) is the 180-degree rotation (corner at (3,7)).
    """
    b: dict = {}
    # bottom zone, corner (0,0)
    for cell in [(0, 0), (1, 0), (0, 1)]:
        b[cell] = 3
    for cell in [(2, 0), (1, 1), (0, 2)]:
        b[cell] = 2
    for cell in [(3, 0), (2, 1), (1, 2)]:
        b[cell] = 1
    # top zone = 180-degree rotation: (c,r) -> (W-1-c, H-1-r)
    rot = {(W - 1 - c, H - 1 - r): v for (c, r), v in list(b.items())}
    b.update(rot)
    return b


@dataclass
class MartianState:
    board: dict = field(default_factory=dict)      # (c, r) -> size (1/2/3)
    to_move: int = 0
    scores: list = field(default_factory=lambda: [0, 0])
    # the opponent's immediately-preceding move, as (from_cell, to_cell), for
    # the no-take-back rule. None at game start / after a merge that vanishes.
    last_move: Optional[tuple] = None
    winner: Optional[int] = None                   # set on game end
    draw: bool = False                             # set at PLY_CAP
    ply: int = 0


def _slide_targets(board: dict, c: int, r: int, dirs, max_steps: int):
    """Yield reachable empty cells, plus the first occupied cell (a capture
    target), sliding from (c,r) along each direction, no jumping."""
    out = []
    for dc, dr in dirs:
        nc, nr = c, r
        for _ in range(max_steps):
            nc, nr = nc + dc, nr + dr
            if not _on(nc, nr):
                break
            if (nc, nr) in board:
                out.append((nc, nr))   # occupied: a possible capture/merge
                break
            out.append((nc, nr))       # empty: continue sliding
    return out


def _piece_targets(board: dict, c: int, r: int):
    """All geometric destinations of the piece at (c,r) (empty squares it can
    reach + the first blocking square in each line). Ownership/legality of the
    landing square is decided by the caller."""
    size = board[(c, r)]
    if size == 1:      # Pawn: one diagonal step
        return _slide_targets(board, c, r, DIAG, 1)
    if size == 2:      # Drone: 1-2 orthogonal
        return _slide_targets(board, c, r, ORTHO, 2)
    return _slide_targets(board, c, r, ALL8, max(W, H))  # Queen


def _count_sizes(board: dict, player: int) -> dict:
    """How many of each size `player` currently controls (pieces in their zone)."""
    n = {1: 0, 2: 0, 3: 0}
    for (c, r), size in board.items():
        if _zone(r) == player:
            n[size] += 1
    return n


def _merge_result(have: dict, mover_size: int, target_size: int) -> Optional[int]:
    """If moving a `mover_size` piece onto a friendly `target_size` piece is a
    LEGAL field promotion given current holdings `have`, return the resulting
    size; else None. Rules: make a Queen (3) from a Pawn+Drone only when you
    have no Queens; make a Drone (2) from Pawn+Pawn only when you have no Drones."""
    pair = {mover_size, target_size}
    if pair == {1, 2} and have[3] == 0:
        return 3
    if pair == {1} and have[2] == 0:   # two pawns
        return 2
    return None


def _gen_moves(s: MartianState):
    """Legal (from, to, kind) moves for the player to move, where kind is
    'move', 'capture', or ('merge', result_size)."""
    player = s.to_move
    have = _count_sizes(s.board, player)
    moves = []
    for (c, r), size in list(s.board.items()):
        if _zone(r) != player:
            continue  # can only move pieces in your own zone
        for (tc, tr) in _piece_targets(s.board, c, r):
            # no-take-back: forbid exactly reversing the opponent's last move
            if s.last_move is not None and (c, r) == s.last_move[1] \
                    and (tc, tr) == s.last_move[0]:
                continue
            if (tc, tr) not in s.board:
                moves.append(((c, r), (tc, tr), "move"))
            elif _zone(tr) != player:
                moves.append(((c, r), (tc, tr), "capture"))
            else:
                # landing on a friendly piece in your own zone: only legal as a
                # field-promotion merge.
                res = _merge_result(have, size, s.board[(tc, tr)])
                if res is not None:
                    moves.append(((c, r), (tc, tr), ("merge", res)))
    return moves


def _zone_empty(board: dict, player: int) -> bool:
    return not any(_zone(r) == player for (c, r) in board)


class MartianChess(Game):
    uid = "martian_chess"
    name = "Martian Chess"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> MartianState:
        return MartianState(board=_start_pieces())

    def current_player(self, s: MartianState) -> int:
        return s.to_move

    def legal_moves(self, s: MartianState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{_s(a)}>{_s(b)}" for a, b, _ in _gen_moves(s)]

    def _find(self, s: MartianState, move: str):
        frm, to = (_cell(x) for x in move.split(">"))
        for a, b, kind in _gen_moves(s):
            if a == frm and b == to:
                return frm, to, kind
        raise ValueError(f"illegal move: {move}")

    def apply_move(self, s: MartianState, move: str, rng=None) -> MartianState:
        frm, to, kind = self._find(s, move)
        board = dict(s.board)
        size = board.pop(frm)
        scores = list(s.scores)
        last_move: Optional[tuple] = (frm, to)

        if kind == "capture":
            scores[s.to_move] += board[to]   # captured piece's value to mover
            board[to] = size
        elif isinstance(kind, tuple) and kind[0] == "merge":
            board.pop(to)                    # both source pieces vanish...
            board[to] = kind[1]              # ...replaced by the merged piece
            last_move = None                 # a merge can't be "reversed"
        else:  # plain move
            board[to] = size

        ply = s.ply + 1
        winner: Optional[int] = None
        draw = False
        # game ends the instant a zone empties
        if _zone_empty(board, 0) or _zone_empty(board, 1):
            if scores[0] > scores[1]:
                winner = 0
            elif scores[1] > scores[0]:
                winner = 1
            else:
                winner = s.to_move          # tie -> the player who ended it wins
        elif ply >= PLY_CAP:
            draw = True

        return MartianState(board=board, to_move=1 - s.to_move, scores=scores,
                            last_move=last_move, winner=winner, draw=draw, ply=ply)

    def is_terminal(self, s: MartianState) -> bool:
        if s.winner is not None or s.draw:
            return True
        # a player with no legal move: end the game and score it (rare, but must
        # be well-formed). Treated like a game end -> higher score wins.
        return not _gen_moves(s)

    def returns(self, s: MartianState) -> list[float]:
        if s.draw:
            return [0.0, 0.0]
        if s.winner is not None:
            w = s.winner
        else:
            # stuck player (no moves): score the position, tie -> stuck player
            if s.scores[0] > s.scores[1]:
                w = 0
            elif s.scores[1] > s.scores[0]:
                w = 1
            else:
                w = s.to_move
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def serialize(self, s: MartianState) -> dict:
        return {
            "board": {_s(cell): size for cell, size in s.board.items()},
            "to_move": s.to_move,
            "scores": list(s.scores),
            "last_move": ([_s(s.last_move[0]), _s(s.last_move[1])]
                          if s.last_move is not None else None),
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> MartianState:
        lm = d.get("last_move")
        return MartianState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            scores=list(d["scores"]),
            last_move=((_cell(lm[0]), _cell(lm[1])) if lm is not None else None),
            winner=d["winner"],
            draw=d["draw"],
            ply=d["ply"],
        )

    def describe_move(self, s: MartianState, move: str) -> str:
        frm, to, kind = self._find(s, move)
        size = s.board[frm]
        alg = lambda c: f"{'abcd'[c[0]]}{c[1] + 1}"  # noqa: E731
        if isinstance(kind, tuple) and kind[0] == "merge":
            return f"{LABELS[size]} {alg(frm)}+{alg(to)}={LABELS[kind[1]]}"
        sep = "x" if kind == "capture" else "-"
        return f"{LABELS[size]} {alg(frm)}{sep}{alg(to)}"

    def render(self, s: MartianState, perspective=None) -> dict:
        pieces = [{"cell": _s(cell), "owner": _zone(cell[1]), "label": LABELS[size]}
                  for cell, size in s.board.items()]
        score = f"(score {s.scores[0]}-{s.scores[1]})"
        if self.is_terminal(s):
            if s.draw:
                caption = f"Draw, move cap reached  {score}"
            else:
                ret = self.returns(s)
                w = 0 if ret[0] > 0 else 1
                caption = f"{NAMES[w]} wins  {score}"
        else:
            caption = f"{NAMES[s.to_move]} to move  {score}"
        # tint the two zones so the canal is visible
        tints = {}
        for c in range(W):
            for r in range(H):
                tints[f"{c},{r}"] = "#3a2730" if r < CANAL else "#27313a"
        return {
            "board": {"type": "square", "width": W, "height": H, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
