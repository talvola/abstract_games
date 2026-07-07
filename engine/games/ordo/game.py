"""Ordo (Dieter Stein, 2009).

A 10x8 board (10 files wide, 8 ranks tall). Each player has 20 men, set up in a
crenellated double-row formation on their side. Player 0 (Light/White) moves
first from the bottom (home row = row 0); player 1 (Dark/Black) starts at the top
(home row = row 7). "Forward" for a player is toward the OPPONENT's home row.

THE GROUP -- CONNECTION RULE (the defining twist)
    A player's "group" is ALL of their men, and they must be connected in ONE
    sole group by 8-connectivity (orthogonally OR diagonally adjacent).
    Throughout the game, AFTER a player's move, that player's group must be
    connected. A lone piece counts as a connected group.

MOVES -- two kinds
  * Singleton move: a single man slides any number of empty squares in a
    straight line, FORWARD or SIDEWAYS, orthogonally or diagonally (the 5
    directions: forward, left, right, forward-left, forward-right). It may end on
    an empty square, or on an opponent's man, which is CAPTURED and removed. Only
    a singleton may capture.
  * Ordo move: an "ordo" is 2+ friendly men in an uninterrupted straight
    horizontal or vertical line. The whole ordo slides, keeping formation, any
    number of empty squares, ORTHOGONALLY and only PERPENDICULAR to its own axis:
    a horizontal ordo moves forward (rank direction); a vertical ordo moves
    sideways (file direction). All swept squares must be empty -- an ordo may not
    capture and may not move in single file (along its own axis). Any contiguous
    sub-line of 2+ men also counts as an ordo.

DISCONNECTION / REPAIR
    Normally men (and ordos) move only forward or sideways -- never backward. The
    ONLY exception: if the OPPONENT's capture splits your group so you start your
    turn disconnected, you must make a reconnecting move, and for that move
    BACKWARD directions become available. You must reconnect into one group in a
    single move; if no move reconnects your group, you lose immediately.

WIN
  * Land a man on the opponent's home row (the primary goal).
  * Capture all of the opponent's men.
  * Split the opponent's group so that they cannot reconnect on their next move.
    A player with no legal move loses (players may not pass).

A ply cap declares a draw if play drags on (guarantees termination under random
play). Moves: singleton = "c,r>c,r" (from>to); ordo = "c,r>c,r>c,r" (the two
endpoints of the line, then where the first endpoint lands).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

W, H = 10, 8
PLY_CAP = 300
HOME_ROW = {0: 0, 1: H - 1}          # each player's own home row
OPP_HOME = {0: H - 1, 1: 0}          # the row a player wins by reaching


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < W and 0 <= r < H


def _start_board() -> dict:
    """Ordo's crenellated setup. Columns come in pairs; even-indexed pairs sit a
    rank higher than odd-indexed pairs, giving the zig-zag battlement that is one
    connected diagonal group."""
    b = {}
    for c in range(W):
        high = (c // 2) % 2 == 0            # cols 0,1,4,5,8,9 = "high" pairs
        light_rows = (1, 2) if high else (0, 1)
        for r in light_rows:
            b[(c, r)] = 0
            b[(c, H - 1 - r)] = 1           # mirror for Dark
    return b


def _connected(cells) -> bool:
    """True iff the set of cells is 8-connected (or has <= 1 member)."""
    cells = set(cells)
    if len(cells) <= 1:
        return True
    start = next(iter(cells))
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc or dr:
                    nb = (c + dc, r + dr)
                    if nb in cells and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
    return len(seen) == len(cells)


def _runs(coords: list[int]):
    """Given sorted distinct ints, yield maximal contiguous runs as (lo, hi)."""
    if not coords:
        return
    lo = prev = coords[0]
    for x in coords[1:]:
        if x == prev + 1:
            prev = x
        else:
            yield (lo, prev)
            lo = prev = x
    yield (lo, prev)


def _line_cells(a, b):
    if a[1] == b[1]:                      # same row -> horizontal
        r = a[1]
        return [(c, r) for c in range(min(a[0], b[0]), max(a[0], b[0]) + 1)]
    c = a[0]                              # same col -> vertical
    return [(c, rr) for rr in range(min(a[1], b[1]), max(a[1], b[1]) + 1)]


@dataclass
class OrdoState:
    board: dict = field(default_factory=dict)   # (c, r) -> 0/1
    to_move: int = 0
    winner: Optional[int] = None
    drawn: bool = False
    ply: int = 0
    last: Optional[list] = None                  # list of cell strings for render


class Ordo(Game):
    uid = "ordo"
    name = "Ordo"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> OrdoState:
        return OrdoState(board=_start_board())

    def current_player(self, s: OrdoState) -> int:
        return s.to_move

    # ---- move generation --------------------------------------------------
    def _apply_board(self, board: dict, move: str, p: int) -> dict:
        parts = move.split(">")
        nb = dict(board)
        if len(parts) == 2:                       # singleton (may capture)
            frm, to = _cell(parts[0]), _cell(parts[1])
            del nb[frm]
            nb[to] = p                            # overwrites any enemy = capture
            return nb
        a, b, dest = _cell(parts[0]), _cell(parts[1]), _cell(parts[2])
        cells = _line_cells(a, b)
        vec = (dest[0] - a[0], dest[1] - a[1])
        for cell in cells:
            del nb[cell]
        for (cc, rr) in cells:
            nb[(cc + vec[0], rr + vec[1])] = p
        return nb

    def _raw_moves(self, board: dict, p: int) -> list[str]:
        my = {pos for pos, pl in board.items() if pl == p}
        disconnected = not _connected(my)
        fwd = 1 if p == 0 else -1

        # Singleton directions: forward + sideways (+ backward only when repairing)
        sdirs = [(0, fwd), (1, 0), (-1, 0), (1, fwd), (-1, fwd)]
        if disconnected:
            sdirs = sdirs + [(0, -fwd), (1, -fwd), (-1, -fwd)]

        cands: list[str] = []
        for (c, r) in my:
            for dc, dr in sdirs:
                k = 1
                while True:
                    nc, nr = c + dc * k, r + dr * k
                    if not _on(nc, nr):
                        break
                    occ = board.get((nc, nr))
                    if occ is None:
                        cands.append(f"{c},{r}>{nc},{nr}")
                        k += 1
                    elif occ != p:                # capture the first enemy, then stop
                        cands.append(f"{c},{r}>{nc},{nr}")
                        break
                    else:                         # own piece blocks
                        break

        cands += self._ordo_moves(board, p, my, disconnected, fwd)

        # Legality: after the move the mover's group must be connected.
        legal = []
        for m in cands:
            nb = self._apply_board(board, m, p)
            if _connected(pos for pos, pl in nb.items() if pl == p):
                legal.append(m)
        return legal

    def _ordo_moves(self, board, p, my, disconnected, fwd) -> list[str]:
        out: list[str] = []
        occ = board  # any occupant blocks an ordo (it may not capture)

        # Horizontal ordos: men sharing a row. Move perpendicular = forward
        # (rank +fwd); backward (rank -fwd) only when repairing.
        rows: dict[int, list[int]] = {}
        cols: dict[int, list[int]] = {}
        for (c, r) in my:
            rows.setdefault(r, []).append(c)
            cols.setdefault(c, []).append(r)

        hdirs = [fwd] + ([-fwd] if disconnected else [])   # dr values
        for r, cs in rows.items():
            for lo, hi in _runs(sorted(cs)):
                for c1 in range(lo, hi):                    # sub-lines length >= 2
                    for c2 in range(c1 + 1, hi + 1):
                        for dr in hdirs:
                            d = 1
                            while True:
                                nr = r + dr * d
                                if not (0 <= nr < H) or any(
                                    (c, nr) in occ for c in range(c1, c2 + 1)
                                ):
                                    break
                                out.append(f"{c1},{r}>{c2},{r}>{c1},{nr}")
                                d += 1

        # Vertical ordos: men sharing a column. Move perpendicular = sideways
        # (file +/-1), always allowed.
        for c, rs in cols.items():
            for lo, hi in _runs(sorted(rs)):
                for r1 in range(lo, hi):
                    for r2 in range(r1 + 1, hi + 1):
                        for dc in (1, -1):
                            d = 1
                            while True:
                                nc = c + dc * d
                                if not (0 <= nc < W) or any(
                                    (nc, r) in occ for r in range(r1, r2 + 1)
                                ):
                                    break
                                out.append(f"{c},{r1}>{c},{r2}>{nc},{r1}")
                                d += 1
        return out

    def legal_moves(self, s: OrdoState) -> list[str]:
        if s.winner is not None or s.drawn:
            return []
        return self._raw_moves(s.board, s.to_move)

    def is_terminal(self, s: OrdoState) -> bool:
        if s.winner is not None or s.drawn:
            return True
        return not self._raw_moves(s.board, s.to_move)

    # ---- apply ------------------------------------------------------------
    def apply_move(self, s: OrdoState, move: str, rng=None) -> OrdoState:
        p = s.to_move
        opp = 1 - p
        board = self._apply_board(s.board, move, p)

        winner = None
        mine = [pos for pos, pl in board.items() if pl == p]
        if any(r == OPP_HOME[p] for (c, r) in mine):
            winner = p                                    # reached opponent's home row
        elif not any(pl == opp for pl in board.values()):
            winner = p                                    # opponent annihilated
        else:
            oppset = {pos for pos, pl in board.items() if pl == opp}
            if not _connected(oppset) and not self._raw_moves(board, opp):
                winner = p                                # opponent cannot reconnect

        ply = s.ply + 1
        drawn = winner is None and ply >= PLY_CAP
        return OrdoState(board=board, to_move=opp, winner=winner, drawn=drawn,
                         ply=ply, last=move.split(">"))

    def returns(self, s: OrdoState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        if s.drawn:
            return [0.0, 0.0]
        # terminal because the player to move has no legal move: they lose
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    # ---- MCTS rollout-cutoff heuristic ------------------------------------
    def heuristic(self, s: OrdoState) -> list:
        """Material + advancement toward the opponent's home row, squashed to
        (-1, 1) as [player0, player1] payoffs."""
        import math
        score = 0.0
        for (c, r), pl in s.board.items():
            adv = r if pl == 0 else (H - 1 - r)          # distance advanced from home
            v = 1.0 + 0.25 * adv
            score += v if pl == 0 else -v
        val = math.tanh(score / 12.0)
        return [val, -val]

    # ---- serialize --------------------------------------------------------
    def serialize(self, s: OrdoState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "drawn": s.drawn,
            "ply": s.ply,
            "last": s.last,
        }

    def deserialize(self, d: dict) -> OrdoState:
        return OrdoState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], winner=d.get("winner"),
            drawn=d.get("drawn", False), ply=d.get("ply", 0),
            last=d.get("last"),
        )

    # ---- notation ---------------------------------------------------------
    def _alg(self, cell_str: str) -> str:
        c, r = _cell(cell_str)
        return f"{'abcdefghij'[c]}{r + 1}"

    def describe_move(self, s: OrdoState, move: str) -> str:
        parts = move.split(">")
        if len(parts) == 2:
            cap = _cell(parts[1]) in s.board
            return f"{self._alg(parts[0])}{'x' if cap else '-'}{self._alg(parts[1])}"
        # ordo: [line-end..line-end] => destination of the first end
        return (f"[{self._alg(parts[0])}-{self._alg(parts[1])}]"
                f">{self._alg(parts[2])}")

    # ---- render -----------------------------------------------------------
    def render(self, s: OrdoState, perspective=None) -> dict:
        names = {0: "White", 1: "Black"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = []
        if s.last:
            highlights.append({"cell": s.last[-1], "kind": "last-move"})
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.drawn:
            caption = "Draw (ply cap)"
        else:
            caption = f"{names[s.to_move]} to move"
        # tint each player's home row so the objective is visible
        tints = {}
        for c in range(W):
            tints[f"{c},{HOME_ROW[0]}"] = "#553333"
            tints[f"{c},{HOME_ROW[1]}"] = "#333355"
        return {
            "board": {"type": "square", "width": W, "height": H, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
