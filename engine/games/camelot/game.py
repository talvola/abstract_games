"""Camelot — George S. Parker's medieval strategy classic (Parker Brothers).

Two players, White (player 0) and Black (player 1), each with 14 pieces: 4
KNIGHTS and 10 MEN. The board is the distinctive cross / plus shape — a 12-file
(A-L) by 16-rank (1-16) grid with three squares cut from each corner, plus a
two-square CASTLE jutting from the middle of each player's back edge (White: F1,
G1; Black: F16, G16). 160 playable squares in all.

Coordinates are "c,r" with c = file index 0..11 (A=0 .. L=11) and r = rank index
0..15 (rank 1 .. rank 16). Off-board squares are simply absent from CELLS.

Move types (each move string is a ">"-separated path of squares the moving piece
visits):
  * PLAIN  — one step to any adjoining empty square (8 directions). Path length 2.
  * CANTER — leap over an adjacent FRIENDLY piece to the empty square directly
             beyond (no capture). Chainable: several canters in one move.
  * JUMP   — leap over an adjacent ENEMY piece to the empty square beyond,
             REMOVING it. Chainable.
  * KNIGHT'S CHARGE — a knight (only) may combine canter(s) then jump(s) in a
             single move (canters first, then jumps).

Jumping is COMPULSORY in the authoritative World Camelot Federation rules: if any
of your pieces stands next to an exposed enemy, you must make a jump move, and a
started jump must continue while further jumps are available. (The task brief said
jumping is "optional" — this package follows the authoritative WCF rule instead
and flags the choice in rules.md.)

Win: move TWO of your pieces onto the two squares of the OPPONENT's castle; OR
capture all enemy pieces while keeping >=2 of your own; OR the opponent has no
legal move. Draw if both players are reduced to <=1 piece (neither can win), or on
the no-progress ply cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WIDTH = 12   # files A..L  (col 0..11)
HEIGHT = 16  # ranks 1..16 (row 0..15)

KNIGHT = "K"
MAN = "M"
NAMES = {0: "White", 1: "Black"}

# White's castle = F1,G1 (row 0); Black's castle = F16,G16 (row 15). F=5,G=6.
CASTLE = {0: {(5, 0), (6, 0)}, 1: {(5, 15), (6, 15)}}
# The castle a player is trying to INVADE (the opponent's).
TARGET_CASTLE = {0: CASTLE[1], 1: CASTLE[0]}

DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

NO_PROGRESS_CAP = 100  # plies without a capture -> draw


def _build_cells() -> set:
    """The 160-square cross/plus board.

    Main body ranks 2..15 (rows 1..14), 12 files wide, with a 3-square stepped
    cut at each corner; plus the 4 castle squares jutting at ranks 1 and 16.
      rank 2  (row 1):  files C..J  (cols 2..9)   -> 8
      rank 3  (row 2):  files B..K  (cols 1..10)  -> 10
      ranks 4..13 (rows 3..12): files A..L (0..11) -> 12 each
      rank 14 (row 13): files B..K  -> 10
      rank 15 (row 14): files C..J  -> 8
      rank 1  (row 0):  F1,G1 (castle)
      rank 16 (row 15): F16,G16 (castle)
    Total: 8+10+12*10+10+8 + 4 = 160.
    """
    cells = set()
    cells |= CASTLE[0] | CASTLE[1]
    for c in range(2, 10):   # rank 2
        cells.add((c, 1))
    for c in range(1, 11):   # rank 3
        cells.add((c, 2))
    for r in range(3, 13):   # ranks 4..13
        for c in range(0, 12):
            cells.add((c, r))
    for c in range(1, 11):   # rank 14
        cells.add((c, 13))
    for c in range(2, 10):   # rank 15
        cells.add((c, 14))
    return cells


CELLS = _build_cells()


def _start_board() -> dict:
    """White on ranks 6-7 (rows 5-6); Black on ranks 10-11 (rows 9-10).

    White Knights: C6,D7,I7,J6 ; Black Knights: C11,D10,I10,J11.
    Each side's 10 Men fill the remaining of the standard two-rank block.
    """
    b = {}
    # --- White (player 0) ---
    wk = [(2, 5), (3, 6), (8, 6), (9, 5)]            # C6 D7 I7 J6
    wm = [(3, 5), (4, 5), (4, 6), (5, 5), (5, 6),    # D6 E6 E7 F6 F7
          (6, 5), (6, 6), (7, 5), (7, 6), (8, 5)]    # G6 G7 H6 H7 I6
    for cell in wk:
        b[cell] = (0, KNIGHT)
    for cell in wm:
        b[cell] = (0, MAN)
    # --- Black (player 1) ---  (mirror across the board centre)
    bk = [(2, 10), (3, 9), (8, 9), (9, 10)]          # C11 D10 I10 J11
    bm = [(3, 10), (4, 9), (4, 10), (5, 9), (5, 10),  # D11 E10 E11 F10 F11
          (6, 9), (6, 10), (7, 9), (7, 10), (8, 10)]  # G10 G11 H10 H11 I11
    for cell in bk:
        b[cell] = (1, KNIGHT)
    for cell in bm:
        b[cell] = (1, MAN)
    return b


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _s(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _file(c) -> str:
    return "ABCDEFGHIJKL"[c]


def _alg(cell) -> str:
    return f"{_file(cell[0])}{cell[1] + 1}"


@dataclass
class CState:
    board: dict = field(default_factory=dict)   # (c,r) -> (owner, kind)
    to_move: int = 0
    winner: Optional[int] = None                 # set on a win event
    draw: bool = False                           # set on a draw event
    no_progress: int = 0                         # plies since last capture


class Camelot(Game):
    uid = "camelot"
    name = "Camelot"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CState:
        return CState(board=_start_board())

    def current_player(self, s: CState) -> int:
        return s.to_move

    # ---- geometry helpers -------------------------------------------------
    @staticmethod
    def _own_castle(player) -> set:
        return CASTLE[player]

    # ---- move generation --------------------------------------------------
    def _gen_moves(self, s: CState):
        """Return a list of move paths (each a list of (c,r) cells, len>=2).

        Compulsory-jump rule: if any jump move exists, ONLY jump moves are legal.
        Otherwise plain moves, canters and knight-charges (which here are pure
        canters, since charges require a terminating jump) are legal.
        """
        player = s.to_move
        jump_moves = []
        quiet_moves = []
        for cell, (owner, kind) in s.board.items():
            if owner != player:
                continue
            # JUMP / KNIGHT'S CHARGE paths (capturing). A man may only jump.
            self._gather_captures(s, cell, kind, player, [cell], set(), jump_moves)
            # Quiet: plain + canters (knights & men alike).
            self._gather_quiet(s, cell, kind, player, [cell], quiet_moves)
        if jump_moves:
            return jump_moves
        return quiet_moves

    def _gather_quiet(self, s, start, kind, player, path, out):
        """Plain (1 step) + canter chains (no captures). path[0] is the origin."""
        cur = path[-1]
        if len(path) == 1:
            # plain moves: one step to an adjoining empty square
            for dc, dr in DIRS:
                dest = (cur[0] + dc, cur[1] + dr)
                if dest in CELLS and dest not in s.board \
                        and self._dest_allowed(start, dest, player, captured=False):
                    out.append([start, dest])
        # canter legs (chainable). A canter jumps an adjacent FRIENDLY piece to
        # the empty square beyond.
        for dc, dr in DIRS:
            over = (cur[0] + dc, cur[1] + dr)
            land = (cur[0] + 2 * dc, cur[1] + 2 * dr)
            if over not in s.board:
                continue
            if s.board[over][0] != player:           # must be a friendly piece
                continue
            if land not in CELLS or land in s.board:
                continue
            if land in path:                          # no revisiting (no loops)
                continue
            if not self._dest_allowed(start, land, player, captured=False):
                continue
            newpath = path + [land]
            out.append(list(newpath))
            # chain further canters
            self._gather_quiet(s, start, kind, player, newpath, out)

    def _jump_legs(self, s, start, kind, player, path, removed):
        """All single JUMP continuations from path[-1].

        Returns a list of (new_path, new_removed) for each legal jump over an
        adjacent (not-yet-removed) enemy to the empty square beyond.
        """
        cur = path[-1]
        legs = []
        for dc, dr in DIRS:
            over = (cur[0] + dc, cur[1] + dr)
            land = (cur[0] + 2 * dc, cur[1] + 2 * dr)
            if over not in CELLS or over in removed:
                continue
            occ = s.board.get(over)
            if occ is None or occ[0] == player:        # need an enemy to jump
                continue
            if land not in CELLS:
                continue
            if land in s.board and land not in removed:
                continue
            if land in path:
                continue
            if not self._dest_allowed(start, land, player, captured=True):
                continue
            new_removed = set(removed)
            new_removed.add(over)
            legs.append((path + [land], new_removed))
        return legs

    def _gather_captures(self, s, start, kind, player, path, removed, out):
        """Jump chains (capturing), and for KNIGHTS the canter-then-jump charge.

        `removed` is the set of enemy cells already captured this move (they are
        treated as vacated so the same piece can't be re-used). Continuation is
        COMPULSORY: a capturing path is emitted ONLY when at least one jump has
        occurred AND no further jump leg exists from its endpoint (i.e. only the
        continuation-maximal leaves of the jump tree are emitted). Branching is
        preserved — if two distinct further jumps exist, both full chains emit.
        """
        captured_any = bool(removed)

        # For a KNIGHT that has not yet jumped, leading canters are allowed
        # (the Knight's Charge = canter(s) then jump(s)). A pure-canter move (no
        # terminating jump) is emitted by _gather_quiet, not here.
        if kind == KNIGHT and not captured_any:
            cur = path[-1]
            for dc, dr in DIRS:
                over = (cur[0] + dc, cur[1] + dr)
                land = (cur[0] + 2 * dc, cur[1] + 2 * dr)
                if over in s.board and s.board[over][0] == player \
                        and land in CELLS and land not in s.board and land not in path:
                    self._gather_captures(s, start, kind, player,
                                          path + [land], set(removed), out)

        # JUMP legs: over an adjacent enemy to the empty square beyond.
        legs = self._jump_legs(s, start, kind, player, path, removed)
        if legs:
            # A started jump MUST continue while any further jump exists, so we
            # never emit the current (premature-stop) path here — only recurse.
            for new_path, new_removed in legs:
                self._gather_captures(s, start, kind, player,
                                      new_path, new_removed, out)
        elif captured_any:
            # No further jump available and we have jumped at least once: this is
            # a continuation-maximal leaf — emit it.
            out.append((list(path), frozenset(removed)))

    def _dest_allowed(self, start, dest, player, captured: bool) -> bool:
        """Castle restrictions on a landing square.

        * A piece may not PLAIN-move or CANTER into its OWN castle (only a jump
          may land there). For a capturing path `captured` reflects whether a
          jump has occurred before this landing.
        * Landing in the opponent's castle is always allowed (that is the goal).
        """
        own = CASTLE[player]
        if dest in own and not captured:
            return False
        return True

    def legal_moves(self, s: CState) -> list[str]:
        if self.is_terminal(s):
            return []
        raw = self._gen_moves(s)
        out = []
        for item in raw:
            path = item[0] if isinstance(item, tuple) else item
            out.append(">".join(_s(c) for c in path))
        # de-dup while preserving order (a knight charge and a plain canter could
        # in principle coincide as cell paths; keep unique strings)
        seen = set()
        uniq = []
        for m in out:
            if m not in seen:
                seen.add(m)
                uniq.append(m)
        return uniq

    # ---- applying a move --------------------------------------------------
    def apply_move(self, s: CState, move: str, rng=None) -> CState:
        path = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        player = s.to_move
        piece = board.pop(path[0])
        captured = 0
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
            # a jump leg is a length-2 hop OVER an enemy; a canter hops over a
            # friend; a plain move is a 1-step. Distinguish by the midpoint.
            dist = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
            if dist == 2 and mid in board and board[mid][0] != player:
                del board[mid]      # capture
                captured += 1
        board[path[-1]] = piece

        winner = None
        draw = False
        # WIN 1: two of my pieces now occupy the opponent's castle.
        tgt = TARGET_CASTLE[player]
        if all(board.get(cell) is not None and board[cell][0] == player for cell in tgt):
            winner = player
        # WIN 2: opponent has no pieces left (I captured them all) — but only a
        # win if I keep >=2 (else it becomes the both-<=1 draw, handled below).
        opp = 1 - player
        my_count = sum(1 for v in board.values() if v[0] == player)
        opp_count = sum(1 for v in board.values() if v[0] == opp)
        if winner is None and opp_count == 0 and my_count >= 2:
            winner = player

        no_progress = 0 if captured else s.no_progress + 1
        if winner is None:
            # DRAW: neither side can win (both reduced to <=1 piece).
            if my_count <= 1 and opp_count <= 1:
                draw = True
            elif no_progress >= NO_PROGRESS_CAP:
                draw = True

        return CState(board=board, to_move=opp, winner=winner,
                      draw=draw, no_progress=no_progress)

    def is_terminal(self, s: CState) -> bool:
        if s.winner is not None or s.draw:
            return True
        # opponent (the side to move) with no legal move loses
        return not self._gen_moves(s)

    def returns(self, s: CState) -> list[float]:
        if s.draw:
            return [0.0, 0.0]
        if s.winner is not None:
            w = s.winner
        else:
            # the side to move has no move -> it loses
            w = 1 - s.to_move
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    # ---- serialization ----------------------------------------------------
    def serialize(self, s: CState) -> dict:
        return {
            "board": {_s(k): list(v) for k, v in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> CState:
        return CState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            draw=d.get("draw", False),
            no_progress=d.get("no_progress", 0),
        )

    def describe_move(self, s: CState, move: str) -> str:
        path = [_cell(x) for x in move.split(">")]
        # detect any capture leg
        cap = False
        player = s.to_move
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
            dist = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
            if dist == 2 and s.board.get(mid) and s.board[mid][0] != player:
                cap = True
        sep = "x" if cap else "-"
        return sep.join(_alg(c) for c in path) if cap else \
            f"{_alg(path[0])}-{_alg(path[-1])}"

    # ---- rendering --------------------------------------------------------
    @staticmethod
    def _square_poly(c, r):
        # flip rank so rank 1 (White home) sits at the BOTTOM of the SVG.
        y = (HEIGHT - 1 - r)
        return [[c, y], [c + 1, y], [c + 1, y + 1], [c, y + 1]]

    def render(self, s: CState, perspective=None) -> dict:
        cell_specs = [{"id": _s(cell), "points": self._square_poly(*cell)}
                      for cell in CELLS]
        # tint the four castle squares
        tints = {}
        for cell in CASTLE[0]:
            tints[_s(cell)] = "#f3d6a8"   # White castle (warm)
        for cell in CASTLE[1]:
            tints[_s(cell)] = "#c9d8f0"   # Black castle (cool)
        pieces = []
        for cell, (owner, kind) in s.board.items():
            pieces.append({
                "cell": _s(cell),
                "owner": owner,
                "label": kind,            # K = Knight, M = Man
            })
        if s.winner is not None:
            cap = f"{NAMES[s.winner]} wins"
        elif s.draw:
            cap = "Draw"
        elif self.is_terminal(s):
            cap = f"{NAMES[1 - s.to_move]} wins (no moves)"
        else:
            cap = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "polygons", "cells": cell_specs, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
