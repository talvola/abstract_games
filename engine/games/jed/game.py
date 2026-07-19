"""Jed — Jade with the hox protocol (J. Mark Thompson & Kerry Handscomb, 2021).

Source: Abstract Games magazine issue 22 (Autumn 2021), pp. 24-25 + 34 —
Mark Thompson's original Jade article (written for the unpublished AG17),
the Jed rules, and the two chilling Addenda.  Jade dates back to ~2001
(Shared Pieces Game Design Competition 2003); Jed adds Larry Back's "hox
protocol" (AG21) to fix Jade's "chilling" flaw.

Board: a hex-grid PARALLELOGRAM, 11 columns x 9 rows (the standard 9x11).
Cell id "c,r": c = column 0..10 (printed 1..11), r = row 0..8 (printed A..I).
Hex adjacency: (c±1,r), (c,r±1), (c+1,r-1), (c-1,r+1).

Every cell has a fixed type J / E / D (magazine colours Red / Green / Yellow).
The 3-colouring was extracted pixel-precisely from the "Jed board" figure
(AG22 p. 25):  type(c, r) = "JED"[(c - r) % 3]  — a proper colouring of the
hex lattice (adjacent cells always differ), 33 cells of each type, corners
A1=J, A11=E, I1=E, I11=D.

Rules as implemented:
  * Two roles, Cross and Parallel.  Stones are SHARED: on any turn a player
    places one stone of EITHER colour (Black or White) on a vacant cell.
  * Hox/jed protocol: the first stone may go on any cell; thereafter the cell
    type must follow the strict cycle J -> E -> D -> J -> ...
  * Cross wins when a single connected like-coloured group touches all four
    sides (corner cells belong to both adjacent sides).
  * Parallel wins when a Black group and a White group each span the SAME
    pair of opposite sides (either pair).
  * The player whose objective is completed wins, EVEN IF the other player
    placed the final stone.  (The two objectives can never be completed
    simultaneously: a Cross group spans BOTH pairs of sides, and the
    opposite-coloured spanning group Parallel would need must cross one of
    those two chains — impossible on a hex board, where two crossing chains
    share a cell.  The selftest verifies exclusivity empirically over
    hundreds of filled boards; the check order below is therefore moot.)
  * Modified pie rule: the first player places a stone AND declares a role
    (Cross or Parallel); the second player either replies with a placement
    (taking the other role) or plays "swap" — adopting the first move and
    the declared role, with play returning to the first player.
  * Passing is not allowed (never needed: 99 = 3x33, so the required type
    never runs out before the board is full, and a filled board always
    satisfies one objective — draws are impossible; see rules.md).
  * The game ends at the FIRST completion.  Minimum stones for a win: 11 for
    Cross (the short-diagonal chain A11-I1 — corner cells count for both
    sides; anchored on the historical pbmserv Jade implementation, whose
    example diagrams adjudicate a bare 7-stone short-diagonal chain on 7x7
    as "Cross wins"), 18 for Parallel (two disjoint 9-chains across rows
    A-I).  The magazine's printed "Cross needs 19" counts the row+column
    cross shape and does not account for the corner rule (errata).

Move strings:
  ply 0:  "c,r=BC" / "c,r=BP" / "c,r=WC" / "c,r=WP"   (colour + declared role)
  ply 1:  "swap"  or  "c,r=B" / "c,r=W"
  later:  "c,r=B" / "c,r=W"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

COLS, ROWS = 11, 9          # printed columns 1..11, rows A..I
TYPES = "JED"               # cycle J -> E -> D -> J (Red -> Green -> Yellow)
TYPE_COLOURS = {"J": "red", "E": "green", "D": "yellow"}
ROW_NAMES = "ABCDEFGHI"

# Edge bitmask: which board sides a cell lies on (corners carry two bits).
ROW_PAIR = 1 | 2            # sides row A (r=0) and row I (r=8)
COL_PAIR = 4 | 8            # sides column 1 (c=0) and column 11 (c=10)
ALL_SIDES = ROW_PAIR | COL_PAIR


def cell_type(c: int, r: int) -> int:
    """0=J, 1=E, 2=D — extracted from the AG22 'Jed board' figure."""
    return (c - r) % 3


def _edge_bits(c: int, r: int) -> int:
    bits = 0
    if r == 0:
        bits |= 1
    if r == ROWS - 1:
        bits |= 2
    if c == 0:
        bits |= 4
    if c == COLS - 1:
        bits |= 8
    return bits


def _neighbors(c: int, r: int):
    return ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1),
            (c + 1, r - 1), (c - 1, r + 1))


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _group_masks(board: dict, colour: str) -> list[int]:
    """Edge-bit mask of every connected group of `colour` stones."""
    seen: set = set()
    masks = []
    for cell, col in board.items():
        if col != colour or cell in seen:
            continue
        mask = 0
        stack = [cell]
        seen.add(cell)
        while stack:
            cur = stack.pop()
            mask |= _edge_bits(*cur)
            for nb in _neighbors(*cur):
                if nb not in seen and board.get(nb) == colour:
                    seen.add(nb)
                    stack.append(nb)
        masks.append(mask)
    return masks


def _cross_won(mb: list[int], mw: list[int]) -> bool:
    """Some like-coloured group touches all four sides."""
    return any(m == ALL_SIDES for m in mb) or any(m == ALL_SIDES for m in mw)


def _parallel_won(mb: list[int], mw: list[int]) -> bool:
    """A Black group and a White group both span the SAME pair of sides."""
    for pair in (ROW_PAIR, COL_PAIR):
        if any(m & pair == pair for m in mb) and any(m & pair == pair for m in mw):
            return True
    return False


def _decide(board: dict) -> Optional[str]:
    """'C' / 'P' / None.  Cross checked first (see module docstring)."""
    mb = _group_masks(board, "B")
    mw = _group_masks(board, "W")
    if _cross_won(mb, mw):
        return "C"
    if _parallel_won(mb, mw):
        return "P"
    return None


@dataclass
class JedState:
    board: dict = field(default_factory=dict)   # (c, r) -> 'B' / 'W'
    to_move: int = 0
    ply: int = 0
    declared: Optional[str] = None              # first player's declaration 'C'/'P'
    cross_seat: Optional[int] = None            # fixed after move 2 (or swap)
    last_type: Optional[int] = None             # type index of the last placement
    last_cell: Optional[tuple] = None
    winner: Optional[int] = None                # seat index
    win_role: Optional[str] = None              # 'C' / 'P'


class Jed(Game):
    name = "Jed"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> JedState:
        return JedState()

    def current_player(self, s: JedState) -> int:
        return s.to_move

    def legal_moves(self, s: JedState) -> list[str]:
        if s.winner is not None or len(s.board) == COLS * ROWS:
            return []
        moves: list[str] = []
        if s.ply == 0:
            for r in range(ROWS):
                for c in range(COLS):
                    for choice in ("BC", "BP", "WC", "WP"):
                        moves.append(f"{c},{r}={choice}")
            return moves
        due = (s.last_type + 1) % 3
        for r in range(ROWS):
            for c in range(COLS):
                if cell_type(c, r) == due and (c, r) not in s.board:
                    moves.append(f"{c},{r}=B")
                    moves.append(f"{c},{r}=W")
        if s.ply == 1:
            moves.append("swap")
        return moves

    def apply_move(self, s: JedState, move: str, rng=None) -> JedState:
        if move == "swap":
            # Second player adopts the first move AND the declared role;
            # play returns to the first player.
            cross_seat = 1 if s.declared == "C" else 0
            return JedState(board=dict(s.board), to_move=0, ply=s.ply + 1,
                            declared=s.declared, cross_seat=cross_seat,
                            last_type=s.last_type, last_cell=s.last_cell,
                            winner=None, win_role=None)
        cell_part, choice = move.split("=")
        c, r = _cell(cell_part)
        colour = choice[0]
        declared = s.declared
        cross_seat = s.cross_seat
        if s.ply == 0:
            declared = choice[1]              # 'C' or 'P'
        elif s.ply == 1:
            # Second player replies with a move: first player keeps the role.
            cross_seat = 0 if declared == "C" else 1
        board = dict(s.board)
        board[(c, r)] = colour
        winner = None
        win_role = None
        # 11 = the true minimum stones for ANY win: Cross's fastest pattern is
        # the 11-cell short-diagonal chain A11-I1 (corner cells count for both
        # sides, so it touches all four); any group touching both column sides
        # needs >= 11 cells, and Parallel needs two disjoint 9-chains (18).
        # (The magazine's printed "Cross needs 19" counts the row+column cross
        # shape and is an errata — see rules.md.)
        if cross_seat is not None and len(board) >= 11:
            win_role = _decide(board)
            if win_role == "C":
                winner = cross_seat
            elif win_role == "P":
                winner = 1 - cross_seat
        return JedState(board=board, to_move=1 - s.to_move, ply=s.ply + 1,
                        declared=declared, cross_seat=cross_seat,
                        last_type=cell_type(c, r), last_cell=(c, r),
                        winner=winner, win_role=win_role)

    def is_terminal(self, s: JedState) -> bool:
        # A filled board always has a winner (the article's two-notional-Hex-
        # boards proof), so the len() clause is a pure formality.
        return s.winner is not None or len(s.board) == COLS * ROWS

    def returns(self, s: JedState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]                 # unreachable: no draws in Jed
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    def heuristic(self, s: JedState) -> list[float]:
        """Progress of Cross vs Parallel; list of per-seat payoffs."""
        if s.cross_seat is None:
            return [0.0, 0.0]
        mb = _group_masks(s.board, "B")
        mw = _group_masks(s.board, "W")
        cross = max((bin(m).count("1") for m in mb + mw), default=0) / 4.0

        def span(masks, pair):
            return max((bin(m & pair).count("1") for m in masks), default=0) / 2.0

        par = max((span(mb, ROW_PAIR) + span(mw, ROW_PAIR)) / 2.0,
                  (span(mb, COL_PAIR) + span(mw, COL_PAIR)) / 2.0)
        v = 0.7 * (cross - par)
        out = [0.0, 0.0]
        out[s.cross_seat] = v
        out[1 - s.cross_seat] = -v
        return out

    def serialize(self, s: JedState) -> dict:
        return {
            "board": {f"{c},{r}": col for (c, r), col in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "declared": s.declared,
            "cross_seat": s.cross_seat,
            "last_type": s.last_type,
            "last_cell": None if s.last_cell is None else list(s.last_cell),
            "winner": s.winner,
            "win_role": s.win_role,
        }

    def deserialize(self, d: dict) -> JedState:
        return JedState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d["ply"],
            declared=d.get("declared"),
            cross_seat=d.get("cross_seat"),
            last_type=d.get("last_type"),
            last_cell=None if d.get("last_cell") is None else tuple(d["last_cell"]),
            winner=d.get("winner"),
            win_role=d.get("win_role"),
        )

    # ---- presentation -----------------------------------------------------

    @staticmethod
    def _cell_name(c: int, r: int) -> str:
        return f"{ROW_NAMES[r]}{c + 1}"

    def describe_move(self, s: JedState, move: str) -> str:
        if move == "swap":
            return "swap (adopt move & role)"
        cell_part, choice = move.split("=")
        c, r = _cell(cell_part)
        name = self._cell_name(c, r)
        t = TYPES[cell_type(c, r)]
        colour = "Black" if choice[0] == "B" else "White"
        if len(choice) == 2:
            role = "Cross" if choice[1] == "C" else "Parallel"
            return f"{colour} {name} [{t}] — declares {role}"
        return f"{colour} {name} [{t}]"

    def render(self, s: JedState, perspective=None) -> dict:
        tint = {"J": "#4d2b28", "E": "#28402f", "D": "#474023"}
        tints = {f"{c},{r}": tint[TYPES[cell_type(c, r)]]
                 for r in range(ROWS) for c in range(COLS)}
        pieces = []
        for (c, r), col in s.board.items():
            if col == "B":
                pieces.append({"cell": f"{c},{r}", "owner": 0,
                               "fill": "#17171a", "stroke": "#8f8f96"})
            else:
                pieces.append({"cell": f"{c},{r}", "owner": 1,
                               "fill": "#efece4", "stroke": "#3a3a40"})
        highlights = []
        if s.last_cell is not None:
            highlights.append({"cell": f"{s.last_cell[0]},{s.last_cell[1]}",
                               "kind": "last-move"})
        role_of = {}
        if s.cross_seat is not None:
            role_of = {s.cross_seat: "Cross", 1 - s.cross_seat: "Parallel"}
        if s.winner is not None:
            caption = f"{role_of[s.winner]} (P{s.winner + 1}) wins"
        elif len(s.board) == COLS * ROWS:
            caption = "Board full — no objective met (unreachable)"
        elif s.ply == 0:
            caption = "P1: place a stone anywhere and declare Cross or Parallel"
        elif s.ply == 1:
            due = TYPES[(s.last_type + 1) % 3]
            decl = "Cross" if s.declared == "C" else "Parallel"
            caption = (f"P2: play a {due} ({TYPE_COLOURS[due]}) cell "
                       f"(taking {'Parallel' if s.declared == 'C' else 'Cross'}) — "
                       f"or swap to adopt {decl}")
        else:
            due = TYPES[(s.last_type + 1) % 3]
            caption = (f"{role_of[s.to_move]} (P{s.to_move + 1}) to move — "
                       f"must play a {due} ({TYPE_COLOURS[due]}) cell, either colour")
        return {
            "board": {"type": "hex", "shape": "rhombus",
                      "width": COLS, "height": ROWS, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": {"swap": "Adopt move & role (swap)"},
            "choiceNames": {
                "B": "Black stone", "W": "White stone",
                "BC": "Black — declare Cross", "BP": "Black — declare Parallel",
                "WC": "White — declare Cross", "WP": "White — declare Parallel",
            },
        }
