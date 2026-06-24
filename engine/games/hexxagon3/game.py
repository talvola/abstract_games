"""Hexxagon (3-player) — the 3-player Hexxagon / hex-Ataxx variant.

Same geometry and mechanics as 2-player Hexxagon (clone / jump / infection on a
side-5 hexagon-of-hexes, 61 cells minus 3 central holes -> 58 playable), but with
THREE players. The exact 3-player setup is a designed extension — published Ataxx /
Hexxagon sources focus on 2-player, so the alternating-corner P0/P1/P2 layout, the
turn-order (skip eliminated/stuck players), and the 3-way win are our choices.

Setup: 3 players, 2 pieces each (6 total). The six hexagon corners, in cyclic
(angular) order, get owners P0, P1, P2, P0, P1, P2 — so each player owns two
OPPOSITE corners (3 apart in the cycle) and adjacent corners are always different
players. This is 3-fold rotationally symmetric and fair. P0 moves first.

Mechanics (identical to 2-player):

  (A) GROW / clone — target at hex distance 1 (one of the 6 adjacent hexes). A NEW
      piece of your colour appears; the source STAYS (n -> n+1).
  (B) JUMP — target at hex distance EXACTLY 2 (the 12-cell second ring). The piece
      RELOCATES: source vacates, count unchanged.

Infection: after the piece lands, EVERY adjacent (6-nbr) piece belonging to ANY
OTHER player (either of the two opponents) flips to the mover's colour. Holes are
never targetable, never neighbours, never hold a piece.

Turn order: current_player cycles 0->1->2->0, SKIPPING any player who is eliminated
(0 pieces) or who currently has no legal move (they pass). An eliminated player is
permanently out.

End / win:
  - Last survivor: if after a move only ONE player still has pieces, that survivor
    auto-fills every remaining empty (non-hole) cell and WINS.
  - Otherwise the game ends when the board is full or no remaining player can move;
    winner = most pieces (3-way count). Sole leader wins; a tie for the lead is a
    draw.

Termination: each grow adds a piece (board bounded at 58); jumps and flips never
reduce the total, so play can't cycle. A defensive hard ply cap also forces an end.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from agp.game import Game

SIDE = 5            # hexhex side length -> 61 cells
N = SIDE - 1        # extreme coordinate magnitude (4)
NUM_PLAYERS = 3
NAMES = {0: "Red", 1: "Blue", 2: "Green"}
HOLE_COLOR = "#2b2b2b"
PLY_CAP = 3000      # defensive: end-and-count if play runs absurdly long

# 6 hex-neighbour directions (axial). Used for grow targets AND infection.
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

# The 3 default "holes": 3 of the 6 cells adjacent to center (0,0), at alternating
# 120deg positions -> 3-fold rotationally symmetric, center stays playable.
STANDARD_HOLES = frozenset({(1, 0), (-1, 1), (0, -1)})


@lru_cache(maxsize=None)
def _all_cells() -> tuple:
    """All 61 on-board axial cells of the side-5 hexhex."""
    out = []
    for q in range(-N, N + 1):
        for r in range(-N, N + 1):
            if max(abs(q), abs(r), abs(q + r)) <= N:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _all_cell_set() -> frozenset:
    return frozenset(_all_cells())


# The 6 corners of the hexagon, in cyclic (angular) order. Assigning ownership
# i % 3 around this ring gives each player two OPPOSITE corners (3 apart in the
# cycle); adjacent corners are always different players (3-fold symmetric, fair).
CORNERS_CYCLIC = ((0, -N), (N, -N), (N, 0), (0, N), (-N, N), (-N, 0))
# owner = i % 3:  P0,P1,P2,P0,P1,P2
CORNER_OWNER = {c: (i % NUM_PLAYERS) for i, c in enumerate(CORNERS_CYCLIC)}
PLAYER_CORNERS = {
    p: tuple(c for c, o in CORNER_OWNER.items() if o == p)
    for p in range(NUM_PLAYERS)
}


def _holes_for(name: str) -> frozenset:
    return STANDARD_HOLES if name == "standard" else frozenset()


def _playable(holes: frozenset) -> frozenset:
    return _all_cell_set() - holes


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _hex_dist(a, b) -> int:
    dq, dr = a[0] - b[0], a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def _grow_targets(q, r, playable):
    """On-board, non-hole cells at hex distance 1 (the 6 neighbours)."""
    for dq, dr in DIRS:
        cc = (q + dq, r + dr)
        if cc in playable:
            yield cc


def _jump_targets(q, r, playable):
    """On-board, non-hole cells at hex distance exactly 2 (the 12-cell ring)."""
    for dq in range(-2, 3):
        for dr in range(-2, 3):
            if _hex_dist((0, 0), (dq, dr)) != 2:
                continue
            cc = (q + dq, r + dr)
            if cc in playable:
                yield cc


def _moves_for(board: dict, player: int, playable: frozenset):
    """All legal (src, dst, kind) moves for `player`."""
    moves = []
    for (q, r), p in board.items():
        if p != player:
            continue
        for tc in _grow_targets(q, r, playable):
            if tc not in board:
                moves.append(((q, r), tc, "grow"))
        for tc in _jump_targets(q, r, playable):
            if tc not in board:
                moves.append(((q, r), tc, "jump"))
    return moves


def _flip_neighbours(board: dict, cell, player: int, playable: frozenset) -> list:
    """Pieces of ANY OTHER player in the 6 hexes adjacent to `cell` (flip to
    `player`)."""
    q, r = cell
    out = []
    for dq, dr in DIRS:
        cc = (q + dq, r + dr)
        if cc in playable:
            occ = board.get(cc)
            if occ is not None and occ != player:
                out.append(cc)
    return out


@dataclass
class Hexxagon3State:
    board: dict = field(default_factory=dict)   # (q, r) -> player (0/1/2)
    holes: frozenset = STANDARD_HOLES
    to_move: int = 0
    ply: int = 0


class Hexxagon3(Game):
    uid = "hexxagon3"
    name = "Hexxagon (3-player)"

    @property
    def num_players(self) -> int:
        return NUM_PLAYERS

    def initial_state(self, options=None, rng=None) -> Hexxagon3State:
        opts = options or {}
        holes = _holes_for(str(opts.get("holes", "standard")))
        board = {}
        for c, owner in CORNER_OWNER.items():
            board[c] = owner
        return Hexxagon3State(board=board, holes=holes, to_move=0, ply=0)

    def current_player(self, s: Hexxagon3State) -> int:
        return s.to_move

    def _has_pieces(self, board, player) -> bool:
        return any(p == player for p in board.values())

    def _board_full(self, s: Hexxagon3State) -> bool:
        return len(s.board) >= len(_playable(s.holes))

    def _anyone_can_move(self, board, playable) -> bool:
        return any(_moves_for(board, p, playable) for p in range(NUM_PLAYERS))

    def is_terminal(self, s: Hexxagon3State) -> bool:
        if s.ply >= PLY_CAP:
            return True
        if self._board_full(s):
            return True
        # only one player left with pieces -> terminal (last survivor)
        alive = sum(1 for p in range(NUM_PLAYERS) if self._has_pieces(s.board, p))
        if alive <= 1:
            return True
        playable = _playable(s.holes)
        return not self._anyone_can_move(s.board, playable)

    def _next_to_move(self, board, after, playable):
        """The next player cyclically after `after` who is alive (has pieces) AND
        has a legal move. Returns `after` itself if nobody (incl. after) can move
        — caller treats that as terminal."""
        for step in range(1, NUM_PLAYERS + 1):
            cand = (after + step) % NUM_PLAYERS
            if self._has_pieces(board, cand) and _moves_for(board, cand, playable):
                return cand
        return after

    def legal_moves(self, s: Hexxagon3State) -> list[str]:
        if self.is_terminal(s):
            return []
        playable = _playable(s.holes)
        mine = _moves_for(s.board, s.to_move, playable)
        if mine:
            return [f"{sq},{sr}>{tq},{tr}" for (sq, sr), (tq, tr), _ in mine]
        # no move -> we pass (some other player must have a move, else terminal)
        return ["pass"]

    def apply_move(self, s: Hexxagon3State, move: str, rng=None) -> Hexxagon3State:
        playable = _playable(s.holes)
        if move == "pass":
            board = dict(s.board)
            nxt = self._next_to_move(board, s.to_move, playable)
            return Hexxagon3State(board=board, holes=s.holes,
                                  to_move=nxt, ply=s.ply + 1)
        src_s, dst_s = move.split(">")
        src = _cell(src_s)
        dst = _cell(dst_s)
        board = dict(s.board)
        dist = _hex_dist(src, dst)
        # place / relocate
        if dist == 2:           # JUMP: source vacates
            del board[src]
        # (dist == 1 GROW: source piece stays)
        board[dst] = s.to_move
        # infection: flip every adjacent piece of ANY other player
        for fc in _flip_neighbours(board, dst, s.to_move, playable):
            board[fc] = s.to_move
        # Last survivor: if exactly ONE player now has pieces, they auto-fill every
        # empty playable cell and win. Two opponents must have been eliminated this
        # move (or earlier). Guarded by "more than one had pieces before" so a
        # synthetic single-colour position never auto-fills.
        survivors = [p for p in range(NUM_PLAYERS) if self._has_pieces(board, p)]
        before = sum(1 for p in range(NUM_PLAYERS) if self._has_pieces(s.board, p))
        if before > 1 and len(survivors) == 1:
            win = survivors[0]
            for cc in playable:
                board.setdefault(cc, win)
            return Hexxagon3State(board=board, holes=s.holes,
                                  to_move=win, ply=s.ply + 1)
        nxt = self._next_to_move(board, s.to_move, playable)
        return Hexxagon3State(board=board, holes=s.holes,
                              to_move=nxt, ply=s.ply + 1)

    def _counts(self, s: Hexxagon3State):
        c = [0] * NUM_PLAYERS
        for p in s.board.values():
            c[p] += 1
        return c

    def returns(self, s: Hexxagon3State) -> list[float]:
        # Match Rolit's >2-seat convention: sole leader +1, everyone else -1; a
        # tie for the lead is a draw (all 0).
        if not self.is_terminal(s):
            return [0.0] * NUM_PLAYERS
        c = self._counts(s)
        best = max(c)
        winners = [i for i, v in enumerate(c) if v == best]
        if len(winners) == 1:
            return [1.0 if i == winners[0] else -1.0 for i in range(NUM_PLAYERS)]
        return [0.0] * NUM_PLAYERS

    def serialize(self, s: Hexxagon3State) -> dict:
        return {
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "holes": [f"{q},{r}" for (q, r) in sorted(s.holes)],
            "to_move": s.to_move,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> Hexxagon3State:
        holes = frozenset(_cell(k) for k in d.get("holes", []))
        return Hexxagon3State(
            board={_cell(k): v for k, v in d["board"].items()},
            holes=holes,
            to_move=d["to_move"],
            ply=d.get("ply", 0),
        )

    def describe_move(self, s: Hexxagon3State, move: str) -> str:
        who = "P" + str(s.to_move + 1)
        if move == "pass":
            return f"{who}:pass"
        src_s, dst_s = move.split(">")
        dist = _hex_dist(_cell(src_s), _cell(dst_s))
        kind = "grow" if dist == 1 else "jump"
        return f"{who}:{kind} {dst_s}"

    def render(self, s: Hexxagon3State, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": p, "label": ""}
                  for (q, r), p in s.board.items()]
        tints = {f"{q},{r}": HOLE_COLOR for (q, r) in s.holes}
        c = self._counts(s)
        score_str = "-".join(str(c[i]) for i in range(NUM_PLAYERS))
        if self.is_terminal(s):
            best = max(c)
            lead = [i for i, v in enumerate(c) if v == best]
            if len(lead) == 1:
                caption = f"{NAMES[lead[0]]} wins  ({score_str})"
            else:
                caption = f"Draw  ({score_str})"
        else:
            playable = _playable(s.holes)
            mine = _moves_for(s.board, s.to_move, playable)
            verb = "to move" if mine else "must pass"
            caption = f"{NAMES[s.to_move]} {verb}  ({score_str})"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": SIDE, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
