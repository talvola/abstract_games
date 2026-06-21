"""Fanorona — the national board game of Madagascar.

Played on a 5-row x 9-column grid of intersections with an alquerque-style line
pattern. We render it as a 9-wide x 5-tall SQUARE board: pieces sit at the cell
centres and the connecting lines are cosmetic (not drawn).

ADJACENCY. Orthogonal neighbours are always connected. Diagonal neighbours are
connected only on "strong" intersections — a point (c, r) is strong (has the
four diagonal lines) iff (c + r) is EVEN; "weak" points have only the four
orthogonal lines. ``_neighbours`` honours this.

SETUP. 22 White (player 0) and 22 Black (player 1) pieces fill every point
except the centre (4, 2), which starts empty. White occupies the bottom two
rows (r = 0, 1) plus the left/right of the middle row in the standard opening
"clash" array; Black occupies the top two rows (r = 3, 4) plus the rest of the
middle row. See ``_start_board`` / rules.md for the exact middle-row pattern.
White moves first.

MOVEMENT & CAPTURE. A piece moves one step along a connected line to an empty
adjacent point. Capturing is MANDATORY when any capture is available anywhere;
non-capturing moves ("paika") are legal only when no capture exists.

Two capture types share the same single step (move into an empty neighbour):
  * APPROACH — you move *toward* the enemy: the first enemy piece on the far
    side of your destination, in your direction of travel, plus every enemy
    piece continuing in that straight line (until a gap or a friendly piece),
    is removed.
  * WITHDRAWAL — you move *away* from the enemy: the enemy piece directly
    behind your start point (opposite your direction of travel), plus its
    in-line successors, is removed.
If a single step offers BOTH an approach and a withdrawal, the player must pick
one (encoded as a "=A"/"=W" suffix on the step's destination).

A turn may CHAIN several captures with the SAME piece, subject to:
  * each successive step must change direction (no two consecutive steps in the
    same line-direction), and
  * the chain may not revisit a point already visited this turn.
The chain ends when the player stops (only allowed after >=1 capture) or no
further capturing step is available. The first step of a turn, if any capture
exists, must itself be a capturing step.

WIN. Capture all of the opponent's pieces. A player with no pieces, or with no
legal move on their turn, loses. A ply cap forces termination (treated as a
draw) so random self-play always terminates.

MOVE NOTATION. The platform's ">"-separated cell path: the points the piece
visits, e.g. "0,0>1,0" (one step). Ambiguous capturing steps carry a "=A" or
"=W" suffix on the relevant destination cell, e.g. "1,2>1,1=W". A purely
non-capturing paika move is a single step with no suffix.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

W = 9   # columns
H = 5   # rows
PLY_CAP = 1000

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(c, r):
    return f"{c},{r}"


def _on(c, r):
    return 0 <= c < W and 0 <= r < H


def _strong(c, r):
    """A strong intersection (has diagonal lines) iff (c + r) is even."""
    return (c + r) % 2 == 0


def _neighbours(c, r):
    """Directions (dc, dr) along which (c, r) is line-connected to a neighbour."""
    dirs = list(ORTHO)
    if _strong(c, r):
        dirs += DIAG
    return [(dc, dr) for (dc, dr) in dirs if _on(c + dc, r + dr)]


def _start_board() -> dict:
    """Standard Fanorona opening array. (c, r) -> player (0 = White, 1 = Black).

    White (0) fills the bottom two rows (r = 0, 1). Black (1) fills the top two
    rows (r = 3, 4). The middle row (r = 2) is the "clash" row: from the left,
    Black, White, Black, White, EMPTY(centre), Black, White, Black, White —
    i.e. columns 0,2,5,7 Black and 1,3,6,8 White, with column 4 empty. This is
    the classic alternating middle-row pattern that brings the armies into
    immediate contact, with the empty centre at (4, 2).
    """
    b = {}
    for r in (0, 1):
        for c in range(W):
            b[(c, r)] = 0
    for r in (3, 4):
        for c in range(W):
            b[(c, r)] = 1
    # middle row r = 2
    mid = {0: 1, 1: 0, 2: 1, 3: 0, 5: 1, 6: 0, 7: 1, 8: 0}  # col 4 empty
    for c, pl in mid.items():
        b[(c, 2)] = pl
    return b


def _capture_line(board, start, ddir, enemy):
    """List of enemy cells from `start` walking in `ddir`, stopping at the first
    non-enemy (empty or friendly) or the board edge."""
    out = []
    c, r = start
    dc, dr = ddir
    c, r = c + dc, r + dr
    while _on(c, r) and board.get((c, r)) == enemy:
        out.append((c, r))
        c, r = c + dc, r + dr
    return out


def _step_captures(board, frm, to, player):
    """Captures available for moving piece of `player` from `frm` to empty `to`.

    Returns a dict possibly containing keys "A" (approach) and/or "W"
    (withdrawal), each mapping to the (non-empty) list of captured enemy cells.
    Only entries with a non-empty capture line are included.
    """
    enemy = 1 - player
    dc = to[0] - frm[0]
    dr = to[1] - frm[1]
    res = {}
    # Approach: enemies beyond `to` in the travel direction.
    appr = _capture_line(board, to, (dc, dr), enemy)
    if appr:
        res["A"] = appr
    # Withdrawal: enemies behind `frm` (opposite travel direction).
    wd = _capture_line(board, frm, (-dc, -dr), enemy)
    if wd:
        res["W"] = wd
    return res


def _capturing_steps(board, frm, player, last_dir, visited):
    """All capturing steps from `frm` for `player`.

    Honours: destination empty & line-connected; no repeat of `last_dir`; no
    revisiting a `visited` point. Yields tuples (to, ddir, choice, captured)
    where choice is "A"/"W" and captured is the list of removed enemy cells.
    """
    out = []
    for dc, dr in _neighbours(*frm):
        if last_dir is not None and (dc, dr) == last_dir:
            continue
        to = (frm[0] + dc, frm[1] + dr)
        if to in visited or board.get(to) is not None:
            continue
        caps = _step_captures(board, frm, to, player)
        for choice, cells in caps.items():
            out.append((to, (dc, dr), choice, cells))
    return out


def _apply_step(board, frm, to, captured):
    """Return a new board with the piece moved frm->to and `captured` removed."""
    nb = dict(board)
    pl = nb.pop(frm)
    nb[to] = pl
    for cell in captured:
        nb.pop(cell, None)
    return nb


def _enumerate_capture_moves(board, player):
    """All maximal-or-stopped capturing move paths for `player`.

    Each result is a list of step records:
        [(frm, to, ddir, choice, captured), ...]
    A path is included if it has length >= 1 (at least one capture) and either
    it has been stopped (we always record every reachable prefix of length >= 1,
    i.e. the player may stop after any capture) AND we also record longer
    continuations. We therefore record EVERY capturing path of length >= 1 that
    obeys the chain constraints — the player chooses any of them.
    """
    results = []

    def recurse(b, frm, last_dir, visited, path):
        steps = _capturing_steps(b, frm, player, last_dir, visited)
        # record the current path (length >= 1) as a legal stopping point
        if path:
            results.append(list(path))
        for to, ddir, choice, captured in steps:
            nb = _apply_step(b, frm, to, captured)
            nv = visited | {to}
            path.append((frm, to, ddir, choice, captured))
            recurse(nb, to, ddir, nv, path)
            path.pop()

    mine = [pos for pos, pl in board.items() if pl == player]
    for pos in mine:
        recurse(board, pos, None, {pos}, [])
    return results


@dataclass
class FanoronaState:
    board: dict = field(default_factory=dict)  # (c, r) -> player
    to_move: int = 0
    ply: int = 0
    winner: int = -1  # -1 none, else player index; -2 draw (ply cap)


class Fanorona(Game):
    uid = "fanorona"
    name = "Fanorona"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> FanoronaState:
        return FanoronaState(board=_start_board())

    def current_player(self, s: FanoronaState) -> int:
        return s.to_move

    # ---- move generation -------------------------------------------------
    def _capture_moves(self, s: FanoronaState):
        """(move_str, final_board) for every legal capturing move."""
        out = []
        for path in _enumerate_capture_moves(s.board, s.to_move):
            # encode, marking a step as ambiguous iff both A and W capture there
            parts = [_fmt(*path[0][0])]
            b = s.board
            for frm, to, ddir, choice, captured in path:
                caps = _step_captures(b, frm, to, s.to_move)
                suffix = f"={choice}" if len(caps) == 2 else ""
                parts.append(_fmt(*to) + suffix)
                b = _apply_step(b, frm, to, captured)
            out.append((">".join(parts), b))
        return out

    def _paika_moves(self, s: FanoronaState):
        """Non-capturing single-step moves (only used when no capture exists)."""
        out = []
        for pos, pl in s.board.items():
            if pl != s.to_move:
                continue
            for dc, dr in _neighbours(*pos):
                to = (pos[0] + dc, pos[1] + dr)
                if s.board.get(to) is None:
                    out.append(f"{_fmt(*pos)}>{_fmt(*to)}")
        return out

    def legal_moves(self, s: FanoronaState) -> list[str]:
        if s.winner != -1 or s.ply >= PLY_CAP:
            return []
        caps = self._capture_moves(s)
        if caps:
            seen = set()
            out = []
            for m, _ in caps:
                if m not in seen:
                    seen.add(m)
                    out.append(m)
            return out
        return self._paika_moves(s)

    # ---- apply -----------------------------------------------------------
    def _replay(self, s: FanoronaState, move: str):
        """Replay a move string, returning the resulting board. Raises on illegal."""
        tokens = move.split(">")
        cells = []
        choices = []
        for t in tokens:
            if "=" in t:
                cs, ch = t.split("=")
                cells.append(_cell(cs))
                choices.append(ch)
            else:
                cells.append(_cell(t))
                choices.append(None)
        board = dict(s.board)
        player = s.to_move
        # paika (single step, no capture)
        if len(cells) == 2:
            frm, to = cells
            caps = _step_captures(board, frm, to, player)
            if not caps:
                return _apply_step(board, frm, to, [])
            # capturing single step
            ch = choices[1]
            if ch is None:
                # unambiguous: exactly one capture type
                ch = next(iter(caps))
            return _apply_step(board, frm, to, caps[ch])
        # multi-step chain
        b = board
        for i in range(1, len(cells)):
            frm, to = cells[i - 1], cells[i]
            caps = _step_captures(b, frm, to, player)
            ch = choices[i]
            if ch is None:
                ch = next(iter(caps))
            b = _apply_step(b, frm, to, caps[ch])
        return b

    def apply_move(self, s: FanoronaState, move: str, rng=None) -> FanoronaState:
        board = self._replay(s, move)
        nxt = 1 - s.to_move
        winner = -1
        # win: opponent has no pieces
        if not any(pl == nxt for pl in board.values()):
            winner = s.to_move
        ply = s.ply + 1
        ns = FanoronaState(board=board, to_move=nxt, ply=ply, winner=winner)
        # opponent with no legal move loses
        if winner == -1:
            if ply >= PLY_CAP:
                ns.winner = -2
            elif not self.legal_moves(ns):
                ns.winner = s.to_move
        return ns

    def is_terminal(self, s: FanoronaState) -> bool:
        return s.winner != -1 or s.ply >= PLY_CAP

    def returns(self, s: FanoronaState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- serialize -------------------------------------------------------
    def serialize(self, s: FanoronaState) -> dict:
        return {
            "board": {_fmt(c, r): pl for (c, r), pl in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> FanoronaState:
        return FanoronaState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], ply=d["ply"], winner=d["winner"],
        )

    # ---- display ---------------------------------------------------------
    def describe_move(self, s: FanoronaState, move: str) -> str:
        tokens = move.split(">")
        cells = [t.split("=")[0] for t in tokens]
        # mark capture vs paika
        is_cap = len(self._capture_moves(s)) > 0
        sep = "x" if is_cap else "-"
        suffixes = "".join(t[t.index("="):] for t in tokens if "=" in t)
        return sep.join(cells) + ("" if not suffixes else f" {suffixes}")

    def render(self, s: FanoronaState, perspective=None) -> dict:
        names = {0: "White", 1: "Black"}
        pieces = [
            {"cell": _fmt(c, r), "owner": pl, "label": ""}
            for (c, r), pl in s.board.items()
        ]
        if self.is_terminal(s):
            if s.winner == -2 or (s.winner == -1 and s.ply >= PLY_CAP):
                caption = "Draw"
            else:
                w = s.winner if s.winner in (0, 1) else (1 - s.to_move)
                caption = f"{names[w]} wins"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
