"""Manalath, by Dieter Stein & Nestor Romeral Andres (2012).

"A simply difficult game for 2 players." Played on a hexagon of hexagons
(hexhex) of side 5 = 61 cells, initially empty.

On your turn you place ONE stone of EITHER colour (your own or your opponent's)
on any empty cell. A *group* is a maximal set of orthogonally-adjacent stones of
the same colour. A group of 4 is a **quart**; a group of 5 is a **quint**.

  * A stone may never be placed so that a group of MORE THAN 5 stones is
    created. This is a legality constraint on the placement, not a loss.
  * At the end of YOUR turn, if a **quint of your own colour** is on the board
    you WIN; if a **quart of your own colour** is on the board you LOSE.
  * These conditions are checked only after your own move, and an end condition
    "is effective when it occurred first" -- so a quart/quint that your opponent
    built for you on the previous turn outranks anything you build now.
  * You pass only when you have no legal placement (rare). An end condition can
    still become effective on a pass. Two passes in a row end the game in a
    draw.

Seat 0 owns colour 0 (RED, "White" in the designer's rules) and moves first;
seat 1 owns colour 1 (BLUE, "Black" in the designer's rules).

Moves are drop strings: ``"R@q,r"`` places a red stone on cell ``q,r``,
``"B@q,r"`` a blue one; ``"pass"`` is offered only when no placement is legal.
The two colour chips appear in the mover's reserve tray, so the UI is
click-a-colour then click-a-cell.

Termination is structural: every non-pass move fills one of the 61 cells, and
the legal-placement set does not depend on whose turn it is, so if one player
must pass the other must pass too. A game therefore lasts at most 61 + 2 = 63
plies. No ply cap is needed.

Sources: https://spielstein.com/games/manalath/rules (designer's official rules,
the primary source) and the AbstractPlay `gameslib` reference implementation
(used as a rule-enforcing oracle only; see rules.md and _diff_ap.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

RED, BLUE = 0, 1
COLOUR_NAME = {RED: "Red", BLUE: "Blue"}
COLOUR_LETTER = {RED: "R", BLUE: "B"}
LETTER_COLOUR = {"R": RED, "B": BLUE}

SIDE = 5          # hexhex side length -> 61 cells
MAX_GROUP = 5     # a placement may never create a group larger than this
QUINT = 5         # group of 5 of your colour at the end of your turn -> win
QUART = 4         # group of 4 of your colour at the end of your turn -> loss

# Structural upper bound on the length of a game: 61 placements + 2 passes.
PLY_BOUND = 63


def _neighbors(q: int, r: int):
    return ((q + 1, r), (q - 1, r), (q, r + 1), (q, r - 1),
            (q + 1, r - 1), (q - 1, r + 1))


@lru_cache(maxsize=None)
def _cells(side: int) -> tuple:
    """All axial cells of a hexhex of side ``side`` (max |coord| = side-1)."""
    n = side - 1
    out = []
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            if abs(q) <= n and abs(r) <= n and abs(-q - r) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(side: int) -> frozenset:
    return frozenset(_cells(side))


@lru_cache(maxsize=None)
def _adj(side: int) -> dict:
    """cell -> tuple of on-board neighbours."""
    on = _cell_set(side)
    return {c: tuple(n for n in _neighbors(*c) if n in on) for c in _cells(side)}


def _cid(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _parse_cell(text: str):
    q, r = text.split(",")
    return int(q), int(r)


def _group_at(board: dict, side: int, cell, colour: int) -> frozenset:
    """The maximal connected same-colour group containing ``cell``."""
    adj = _adj(side)
    seen = {cell}
    todo = [cell]
    while todo:
        c = todo.pop()
        for n in adj[c]:
            if n not in seen and board.get(n) == colour:
                seen.add(n)
                todo.append(n)
    return frozenset(seen)


def _groups(board: dict, side: int, colour: int) -> list:
    """All maximal groups of ``colour`` on the board."""
    adj = _adj(side)
    seen = set()
    out = []
    for c, v in board.items():
        if v != colour or c in seen:
            continue
        grp = set()
        todo = [c]
        while todo:
            x = todo.pop()
            if x in grp:
                continue
            grp.add(x)
            for n in adj[x]:
                if n not in grp and board.get(n) == colour:
                    todo.append(n)
        seen |= grp
        out.append(frozenset(grp))
    return out


def _placement_group_size(board: dict, side: int, cell, colour: int) -> int:
    """Size of the group that would contain ``cell`` if ``colour`` were placed there."""
    adj = _adj(side)
    seen = {cell}
    todo = [cell]
    n = 0
    while todo:
        c = todo.pop()
        n += 1
        for x in adj[c]:
            if x not in seen and board.get(x) == colour:
                seen.add(x)
                todo.append(x)
    return n


@dataclass
class MState:
    side: int = SIDE
    board: dict = field(default_factory=dict)   # (q, r) -> colour (0 red / 1 blue)
    to_move: int = 0                            # seat to move
    over: bool = False                          # terminal flag
    winner: Optional[int] = None                # winning SEAT, or None (draw)
    last: Optional[tuple] = None                # last placed cell (None after a pass)
    last_pass: bool = False                     # previous ply was a pass
    ply: int = 0


class Manalath(Game):
    name = "Manalath"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> MState:
        # Manalath is defined on the hexhex-5 board only; there are no options.
        return MState(side=SIDE)

    def current_player(self, s: MState) -> int:
        return s.to_move

    # ---- moves -----------------------------------------------------------
    def legal_moves(self, s: MState) -> list[str]:
        if s.over:
            return []
        board = s.board
        side = s.side
        out = []
        for cell in _cells(side):
            if cell in board:
                continue
            cid = _cid(cell)
            for colour in (RED, BLUE):
                if _placement_group_size(board, side, cell, colour) <= MAX_GROUP:
                    out.append(f"{COLOUR_LETTER[colour]}@{cid}")
        if not out:
            return ["pass"]
        return out

    def _outcome(self, board: dict, side: int, mover: int, placed):
        """The seat that wins, or None, after ``mover`` finished their turn.

        ``placed`` is the cell just filled (None on a pass). Following the
        designer's "an end condition is effective when it occurred first" rule,
        a quart/quint of the mover's colour that does NOT contain the cell just
        played -- i.e. one that was already on the board when the turn began --
        outranks whatever the placement itself created.
        """
        colour = mover  # seat n owns colour n
        groups = _groups(board, side, colour)
        current = None
        if placed is not None and board.get(placed) == colour:
            for g in groups:
                if placed in g:
                    current = g
                    break
        others = [g for g in groups if g is not current]
        # Pre-existing (older) conditions first. At most one can exist in a real
        # game, but the loss is checked first so the order is still defined.
        if any(len(g) == QUART for g in others):
            return 1 - mover
        if any(len(g) == QUINT for g in others):
            return mover
        if current is not None:
            if len(current) == QUART:
                return 1 - mover
            if len(current) == QUINT:
                return mover
        return None

    def apply_move(self, s: MState, move: str, rng=None) -> MState:
        if s.over:
            raise ValueError("game is over")
        mover = s.to_move
        side = s.side

        if move == "pass":
            if self.legal_moves(s) != ["pass"]:
                raise ValueError("pass is only legal with no placement available")
            board = dict(s.board)          # never share a mutable board between states
            winner = self._outcome(board, side, mover, None)
            over = winner is not None
            if not over and s.last_pass:
                over = True          # both players passed -> draw
            return MState(side=side, board=board, to_move=1 - mover,
                          over=over, winner=winner, last=None, last_pass=True,
                          ply=s.ply + 1)

        if "@" not in move:
            raise ValueError(f"illegal move {move!r}")
        letter, _, cellpart = move.partition("@")
        if letter not in LETTER_COLOUR:
            raise ValueError(f"illegal move {move!r}")
        colour = LETTER_COLOUR[letter]
        try:
            cell = _parse_cell(cellpart)
        except ValueError:
            raise ValueError(f"illegal move {move!r}")
        if cell not in _cell_set(side) or cell in s.board:
            raise ValueError(f"illegal move {move!r}")
        if _placement_group_size(s.board, side, cell, colour) > MAX_GROUP:
            raise ValueError(f"illegal move {move!r}: creates a group larger than {MAX_GROUP}")

        board = dict(s.board)
        board[cell] = colour
        winner = self._outcome(board, side, mover, cell)
        return MState(side=side, board=board, to_move=1 - mover,
                      over=winner is not None, winner=winner,
                      last=cell, last_pass=False, ply=s.ply + 1)

    # ---- terminal --------------------------------------------------------
    def is_terminal(self, s: MState) -> bool:
        return s.over

    def returns(self, s: MState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- persistence -----------------------------------------------------
    def serialize(self, s: MState) -> dict:
        return {
            "side": s.side,
            "board": {_cid(c): v for c, v in s.board.items()},
            "to_move": s.to_move,
            "over": s.over,
            "winner": s.winner,
            "last": (_cid(s.last) if s.last is not None else None),
            "last_pass": s.last_pass,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> MState:
        last = d.get("last")
        return MState(
            side=d.get("side", SIDE),
            board={_parse_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            over=d.get("over", False),
            winner=d.get("winner"),
            last=(_parse_cell(last) if last else None),
            last_pass=d.get("last_pass", False),
            ply=d.get("ply", 0),
        )

    # ---- presentation ----------------------------------------------------
    def describe_move(self, s: MState, move: str) -> str:
        who = f"P{s.to_move + 1}"
        if move == "pass":
            return f"{who} pass"
        letter, _, cellpart = move.partition("@")
        return f"{who} {COLOUR_NAME[LETTER_COLOUR[letter]]} {cellpart}"

    def render(self, s: MState, perspective=None) -> dict:
        pieces = [{"cell": _cid(c), "owner": v} for c, v in s.board.items()]
        highlights = []
        if s.last is not None:
            highlights.append({"cell": _cid(s.last), "kind": "last-move"})
        if s.over:
            if s.winner is None:
                caption = "Draw (both players passed)"
            else:
                caption = f"P{s.winner + 1} ({COLOUR_NAME[s.winner]}) wins"
        else:
            caption = (f"P{s.to_move + 1} ({COLOUR_NAME[s.to_move]}) to move "
                       f"- place a Red or a Blue stone")
        # The reserve tray is a COLOUR PICKER, not a limited supply: both chips
        # are always available (count 1 so no "xN" badge is drawn).  Because it
        # is a colour picker, `reserveOwners` tints each chip by the stone it
        # will PUT ON THE BOARD (R -> seat 0's red, B -> seat 1's blue) rather
        # than by whose tray it sits in -- otherwise seat 0's "B" chip would be
        # drawn red and seat 1's "R" chip blue.  The letters here MUST match the
        # drop-move letters emitted by `legal_moves` (COLOUR_LETTER), and the
        # seat indices MUST match `piece.owner` above, which is the colour.
        tray = {"R": 1, "B": 1}
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.side},
            "pieces": pieces,
            "highlights": highlights,
            "reserve": {"0": dict(tray), "1": dict(tray)},
            "reserveOwners": {COLOUR_LETTER[RED]: RED, COLOUR_LETTER[BLUE]: BLUE},
            "caption": caption,
        }
