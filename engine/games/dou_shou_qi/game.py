"""Dou Shou Qi (鬥獸棋) — "Jungle" / "Animal Chess" / "The Game of Fighting Animals".

A traditional Chinese capture game on a 7-column x 9-row board. Each side has
eight ranked animals; you win by moving a piece into the opponent's *den* (or by
leaving the opponent with no legal move).

Ranks, high to low: Elephant(8) Lion(7) Tiger(6) Leopard(5) Wolf(4) Dog(3)
Cat(2) Rat(1). A piece captures an enemy of EQUAL OR LOWER rank, with the one
exception that the Rat(1) captures the Elephant(8) (and the Elephant may NOT
capture the Rat). Pieces standing on an enemy *trap* are treated as rank 0 and
may be captured by anything of the trap's owner.

All pieces move one square orthogonally. Only the Rat may enter the *water*
(river). A Rat in the water cannot capture or be captured across the
land/water boundary, and cannot capture the Elephant from the water. The Lion
and Tiger jump straight across a river region (horizontally or vertically),
landing on the far bank — provided no Rat (of either colour) sits on any water
square in the leap path.

Cells are "col,row" with col 0..6, row 0..8. Player 0's den is at the row-0
end, player 1's den at the row-8 end. Moves are clickable "from>to" cell paths.

See rules.md for the exact board layout and ruleset choices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WIDTH = 7
HEIGHT = 9

PLY_CAP = 400

NAMES = {0: "Red", 1: "Blue"}

# Rank -> single-letter label (used for rendering and notation).
RANK_LETTER = {8: "E", 7: "L", 6: "T", 5: "P", 4: "W", 3: "D", 2: "C", 1: "R"}
RANK_NAME = {8: "Elephant", 7: "Lion", 6: "Tiger", 5: "Leopard",
             4: "Wolf", 3: "Dog", 2: "Cat", 1: "Rat"}

# --- Fixed terrain -------------------------------------------------------- #
# Water (river): two 2-col x 3-row blocks in the middle three rows (3,4,5),
# columns {1,2} and {4,5}. Columns 0, 3, 6 are land bridges.
WATER = frozenset(
    (c, r) for r in (3, 4, 5) for c in (1, 2, 4, 5)
)

# Dens: back-centre of each side. Player 0's den at the row-0 end (3,0);
# player 1's den at (3,8).
DEN = {0: (3, 0), 1: (3, 8)}

# Traps: the three squares flanking/behind each den.
TRAPS = {
    0: frozenset({(2, 0), (4, 0), (3, 1)}),   # guard player 0's den
    1: frozenset({(2, 8), (4, 8), (3, 7)}),   # guard player 1's den
}
ALL_TRAPS = TRAPS[0] | TRAPS[1]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < WIDTH and 0 <= r < HEIGHT


@dataclass
class DSQState:
    # board: (c, r) -> (player, rank)
    board: dict = field(default_factory=dict)
    to_move: int = 0
    winner: Optional[int] = None
    ply: int = 0


def _start_board() -> dict:
    """Canonical Dou Shou Qi starting position.

    Player 0 occupies the row-0..2 end, player 1 the row-6..8 end. Each side's
    layout (relative to its own back rank): Lion and Tiger in the back corners,
    Dog and Cat just in front of the den's flanks, Rat..Elephant on the third
    rank in the order Rat, Leopard, Wolf(centre-ish)... using the standard
    placement below.
    """
    b: dict = {}

    # Player 0 (rows 0,1,2). Den at (3,0).
    b[(0, 0)] = (0, 7)  # Lion  (left corner)
    b[(6, 0)] = (0, 6)  # Tiger (right corner)
    b[(1, 1)] = (0, 3)  # Dog   (right-flank of den, mirrored)
    b[(5, 1)] = (0, 2)  # Cat
    b[(0, 2)] = (0, 1)  # Rat
    b[(2, 2)] = (0, 5)  # Leopard
    b[(4, 2)] = (0, 4)  # Wolf
    b[(6, 2)] = (0, 8)  # Elephant

    # Player 1 (rows 8,7,6) — point-mirror of player 0 through the board centre.
    b[(6, 8)] = (1, 7)  # Lion
    b[(0, 8)] = (1, 6)  # Tiger
    b[(5, 7)] = (1, 3)  # Dog
    b[(1, 7)] = (1, 2)  # Cat
    b[(6, 6)] = (1, 1)  # Rat
    b[(4, 6)] = (1, 5)  # Leopard
    b[(2, 6)] = (1, 4)  # Wolf
    b[(0, 6)] = (1, 8)  # Elephant

    return b


def _effective_rank(board: dict, cell, player_capturing: int) -> int:
    """Rank of the piece on `cell` *as seen by* `player_capturing`.

    A piece sitting on one of `player_capturing`'s own trap squares counts as 0
    (anything can capture it)."""
    pl, rank = board[cell]
    if cell in TRAPS[player_capturing]:
        return 0
    return rank


def _can_capture(board: dict, attacker_cell, target_cell) -> bool:
    """Can the piece on `attacker_cell` capture the enemy on `target_cell`,
    given they are adjacent / on a valid landing square (terrain already OK)?"""
    a_pl, a_rank = board[attacker_cell]
    t_pl, t_rank = board[target_cell]
    if a_pl == t_pl:
        return False

    # Water / land capture restrictions for the Rat and against rats in water.
    a_in_water = attacker_cell in WATER
    t_in_water = target_cell in WATER

    # A piece on land cannot capture a Rat that is in the water, and a Rat in
    # the water cannot capture a piece on land. (Only Rat-vs-Rat captures may
    # happen with one side in water — and both rats can only ever meet inside
    # the water or both on land, never across the bank, given adjacency.)
    if a_in_water != t_in_water:
        return False

    eff = _effective_rank(board, target_cell, a_pl)
    if eff == 0:
        return True  # enemy is in our trap: anything captures it.

    # Standard rank rule with the Rat/Elephant exception.
    if a_rank == 1 and t_rank == 8:
        return True   # Rat captures Elephant
    if a_rank == 8 and t_rank == 1:
        return False  # Elephant may not capture Rat
    return a_rank >= eff


def _jump_landing(board: dict, frm, dc: int, dr: int):
    """If the piece on `frm` (a Lion or Tiger) can leap the river in direction
    (dc,dr), return the landing cell, else None.

    The leap spans a contiguous run of water squares in that direction, landing
    on the first non-water square. It is blocked if any water square in the path
    holds a Rat (of either colour)."""
    c, r = frm
    nc, nr = c + dc, r + dr
    if not _on(nc, nr) or (nc, nr) not in WATER:
        return None  # not jumping over water
    # advance across the contiguous water run
    while _on(nc, nr) and (nc, nr) in WATER:
        if (nc, nr) in board:  # a Rat in the water blocks the leap
            return None
        nc += dc
        nr += dr
    if not _on(nc, nr):
        return None
    return (nc, nr)


def _moves(s: DSQState):
    """Yield (frm, to) tuples of legal moves for the player to move."""
    me = s.to_move
    board = s.board
    out = []
    for (c, r), (pl, rank) in board.items():
        if pl != me:
            continue
        # ---- ordinary one-square orthogonal steps ----
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if not _on(nc, nr):
                continue
            dest = (nc, nr)
            # may never enter your OWN den
            if dest == DEN[me]:
                continue
            # only the Rat may enter water
            if dest in WATER and rank != 1:
                continue
            occ = board.get(dest)
            if occ is None:
                out.append(((c, r), dest))
            elif occ[0] != me and _can_capture(board, (c, r), dest):
                out.append(((c, r), dest))

        # ---- Lion / Tiger river jumps ----
        if rank in (7, 6):  # Lion or Tiger
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                land = _jump_landing(board, (c, r), dc, dr)
                if land is None:
                    continue
                if land == DEN[me]:
                    continue
                occ = board.get(land)
                if occ is None:
                    out.append(((c, r), land))
                elif occ[0] != me and _can_capture(board, (c, r), land):
                    out.append(((c, r), land))
    return out


class DouShouQi(Game):
    uid = "dou_shou_qi"
    name = "Dou Shou Qi (Jungle)"
    PLY_CAP = PLY_CAP

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DSQState:
        return DSQState(board=_start_board())

    def current_player(self, s: DSQState) -> int:
        return s.to_move

    def legal_moves(self, s: DSQState):
        if self.is_terminal(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in _moves(s)]

    def apply_move(self, s: DSQState, move: str, rng=None) -> DSQState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        piece = board.pop(frm)            # (player, rank)
        board[to] = piece                 # capture overwrites the destination
        mover = piece[0]
        # Win by entering the enemy den.
        winner = mover if to == DEN[1 - mover] else None
        return DSQState(board=board, to_move=1 - mover, winner=winner,
                        ply=s.ply + 1)

    # ---- termination ---- #
    def is_terminal(self, s: DSQState) -> bool:
        if s.winner is not None:
            return True
        if s.ply >= PLY_CAP:
            return True
        return not _moves(s)

    def returns(self, s: DSQState):
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if s.ply >= PLY_CAP and _moves(s):
            return [0.0, 0.0]   # ply-cap draw
        # player to move has no legal move -> they lose
        loser = s.to_move
        return [-1.0, 1.0] if loser == 0 else [1.0, -1.0]

    # ---- serialize ---- #
    def serialize(self, s: DSQState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, rank]
                      for (c, r), (pl, rank) in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> DSQState:
        return DSQState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            ply=d["ply"],
        )

    def describe_move(self, s: DSQState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        pl, rank = s.board[frm]
        cap = to in s.board
        letter = RANK_LETTER[rank]
        sep = "x" if cap else "-"
        tag = ""
        if to == DEN[1 - pl]:
            tag = "#"   # reached enemy den
        return f"{letter}{frm[0]},{frm[1]}{sep}{to[0]},{to[1]}{tag}"

    def render(self, s: DSQState, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": RANK_LETTER[rank]}
            for (c, r), (pl, rank) in s.board.items()
        ]
        highlights = []
        for (c, r) in WATER:
            highlights.append({"cell": f"{c},{r}", "kind": "zone"})
        for pl in (0, 1):
            highlights.append({"cell": f"{DEN[pl][0]},{DEN[pl][1]}", "kind": "goal"})
        for (c, r) in ALL_TRAPS:
            highlights.append({"cell": f"{c},{r}", "kind": "zone"})

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif s.ply >= PLY_CAP:
            caption = "Draw (ply cap)"
        elif not _moves(s):
            caption = f"{NAMES[1 - s.to_move]} wins (no moves)"
        else:
            caption = f"{NAMES[s.to_move]} to move"

        return {
            "board": {"type": "square", "width": WIDTH, "height": HEIGHT},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
