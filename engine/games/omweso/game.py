"""Omweso -- the traditional four-row Ugandan (Baganda) Mancala.

Board model for the platform: an **8-wide x 4-tall SQUARE board**. Every cell is
a pit; its rendered LABEL is the seed count. Each player owns the TWO rows
nearest them (16 pits each); there are NO stores -- captured seeds are re-sown
back onto the board, so the total number of seeds on the board is a constant 64
for the whole game and the winner is decided by who can still move, not by
accumulated seeds.

Rows (bottom to top on screen):
    row 0 = player 0 (South) OUTER row  (the row closest to South)
    row 1 = player 0 (South) INNER row  (adjacent to the opponent)
    row 2 = player 1 (North) INNER row  (adjacent to the opponent)
    row 3 = player 1 (North) OUTER row  (the row closest to North)

Player 0 = South owns rows 0 & 1 (seat 0, bottom). Player 1 = North owns rows
2 & 3. Columns 0..7 align vertically across all four rows, so column alignment
is what the capture rule uses.

See rules.md for the full, as-implemented ruleset (Omweso has regional
variants; the choices/simplifications made here are documented there).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SOUTH, NORTH = 0, 1
WIDTH = 8
SIDE = {SOUTH: "South", NORTH: "North"}

# Which two rows each player owns; and which is the inner / outer row.
OWN_ROWS = {SOUTH: (0, 1), NORTH: (2, 3)}
INNER_ROW = {SOUTH: 1, NORTH: 2}
OUTER_ROW = {SOUTH: 0, NORTH: 3}

OWN_PITS = {
    SOUTH: [(c, r) for r in (0, 1) for c in range(WIDTH)],
    NORTH: [(c, r) for r in (2, 3) for c in range(WIDTH)],
}

# The counterclockwise sowing circuit around each player's OWN 16 pits.
#
# South: along the INNER row left->right (row 1, cols 0..7), then DOWN to the
# outer row and back along it right->left (row 0, cols 7..0), then wrap to the
# start. This traces a single physical loop around South's two rows.
SOW_ORDER = {
    SOUTH: (
        [(c, 1) for c in range(WIDTH)]              # inner row, left -> right
        + [(c, 0) for c in range(WIDTH - 1, -1, -1)]  # outer row, right -> left
    ),
    # North is the 180-degree rotation of South.
    NORTH: (
        [(c, 2) for c in range(WIDTH - 1, -1, -1)]  # inner row, right -> left
        + [(c, 3) for c in range(WIDTH)]            # outer row, left -> right
    ),
}
SOW_INDEX = {p: {pit: i for i, pit in enumerate(order)}
             for p, order in SOW_ORDER.items()}

TOTAL_SEEDS = 64
PLY_CAP = 500            # anti-loop safety: reaching it is a draw
LAP_GUARD = 200000       # per-turn relay guard (defensive; never hit in practice)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _owner_of_row(r: int) -> int:
    return SOUTH if r in (0, 1) else NORTH


@dataclass
class OmwesoState:
    board: dict = field(default_factory=dict)   # (col,row) -> seed count
    to_move: int = SOUTH
    ply: int = 0


class Omweso(Game):
    uid = "omweso"
    name = "Omweso"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> OmwesoState:
        # Standard "checking" opening: 4 seeds in each of the 8 pits closest to
        # a player (that player's OUTER row); inner rows start empty.
        board = {(c, r): 0 for r in range(4) for c in range(WIDTH)}
        for c in range(WIDTH):
            board[(c, OUTER_ROW[SOUTH])] = 4
            board[(c, OUTER_ROW[NORTH])] = 4
        return OmwesoState(board=board, to_move=SOUTH, ply=0)

    def current_player(self, s: OmwesoState) -> int:
        return s.to_move

    # -- core sowing / relay / capture (pure; operates on a plain dict) ------
    def _sow(self, board, player, start):
        """Sow from `start` for `player`; return a NEW board.

        Implements the relay (lap) rule and the inner-row column capture with
        re-sowing of captured seeds from where the capturing lap began. Does
        NOT mutate the input `board`.
        """
        board = dict(board)
        order = SOW_ORDER[player]
        index = SOW_INDEX[player]
        n = len(order)                       # 16
        opp = 1 - player
        inner = INNER_ROW[player]

        lap_start = start
        hand = board[start]
        board[start] = 0
        pos = index[start]

        guard = 0
        while True:
            guard += 1
            if guard > LAP_GUARD:
                break                        # defensive; should never trigger
            last = None
            for _ in range(hand):
                pos = (pos + 1) % n
                pit = order[pos]
                board[pit] += 1
                last = pit

            # Last seed landed in a previously-EMPTY pit -> the turn ends.
            if board[last] == 1:
                break

            # Occupied pit (now >= 2): capture or relay.
            if last[1] == inner:
                c = last[0]
                opp_inner = (c, INNER_ROW[opp])
                opp_outer = (c, OUTER_ROW[opp])
                if board[opp_inner] > 0 and board[opp_outer] > 0:
                    # CAPTURE both opposing pits; re-sow the captured seeds
                    # starting from where THIS lap began.
                    captured = board[opp_inner] + board[opp_outer]
                    board[opp_inner] = 0
                    board[opp_outer] = 0
                    hand = captured
                    pos = index[lap_start]
                    continue

            # RELAY: pick up the occupied landing pit and keep sowing.
            lap_start = last
            hand = board[last]
            board[last] = 0
            pos = index[last]

        return board

    # -- legal moves --------------------------------------------------------
    def _stuck(self, s: OmwesoState) -> bool:
        """The player to move has no pit with >= 2 seeds (cannot sow)."""
        b = s.board
        return not any(b[p] >= 2 for p in OWN_PITS[s.to_move])

    def legal_moves(self, s: OmwesoState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{c},{r}" for (c, r) in OWN_PITS[s.to_move] if s.board[(c, r)] >= 2]

    # -- apply --------------------------------------------------------------
    def apply_move(self, s: OmwesoState, move: str, rng=None) -> OmwesoState:
        player = s.to_move
        start = _cell(move)
        board = self._sow(s.board, player, start)
        return OmwesoState(board=board, to_move=1 - player, ply=s.ply + 1)

    # -- terminal / returns -------------------------------------------------
    def is_terminal(self, s: OmwesoState) -> bool:
        return s.ply >= PLY_CAP or self._stuck(s)

    def returns(self, s: OmwesoState) -> list[float]:
        # A player who cannot move loses (the last player able to move wins).
        if self._stuck(s):
            loser = s.to_move
            r = [0.0, 0.0]
            r[loser] = -1.0
            r[1 - loser] = 1.0
            return r
        # Reached only via the anti-loop ply cap -> draw.
        return [0.0, 0.0]

    # -- serialize ----------------------------------------------------------
    def serialize(self, s: OmwesoState) -> dict:
        return {
            "board": {f"{c},{r}": n for (c, r), n in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> OmwesoState:
        return OmwesoState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
        )

    # -- render -------------------------------------------------------------
    def render(self, s: OmwesoState, perspective=None) -> dict:
        pieces = []
        for (c, r), n in s.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": _owner_of_row(r),
                "label": str(n),
            })
        if self.is_terminal(s):
            r = self.returns(s)
            if r[SOUTH] > r[NORTH]:
                caption = "South wins"
            elif r[NORTH] > r[SOUTH]:
                caption = "North wins"
            else:
                caption = "Draw"
        else:
            caption = f"{SIDE[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": WIDTH, "height": 4},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }

    # -- nicer move log -----------------------------------------------------
    def describe_move(self, s: OmwesoState, move: str) -> str:
        c, r = _cell(move)
        side = SIDE[_owner_of_row(r)]
        band = "inner" if r == INNER_ROW[_owner_of_row(r)] else "outer"
        return f"{side} {band} col {c} ({s.board.get((c, r), 0)} seeds)"
