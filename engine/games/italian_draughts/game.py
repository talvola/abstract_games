"""Italian Draughts (Dama Italiana) — the traditional 8x8 Italian ruleset.

Rules as codified by the Federazione Italiana Dama (FID) official rulebook
(Regolamento Tecnico, Capo I, 2006). Played on the dark squares of an 8x8 board,
12 men per side. White moves first.

Distinctive Italian rules (see rules.md for the full diff vs checkers /
brazilian_draughts):

* **Men move and capture FORWARD only** (like English checkers, unlike Brazilian
  where men capture backward too).                                    [FID 4.1, 5.3a]
* **A man may never capture a king** ("una pedina prende solo pedine e non
  dame") — men jump only enemy MEN.                                   [FID 5.3b]
* **Kings are NON-flying ("short") kings**: a king moves one square diagonally
  forward or backward to an adjacent empty square, and captures by jumping an
  ADJACENT enemy piece (man or king), landing on the FIRST square immediately
  beyond it — exactly like an English-checkers king (NOT a flying king). [FID 4.7, 5.8]
* **Capture is mandatory and MAXIMAL, with a strict quality priority chain**
  applied over every legal capture sequence, in order:               [FID 6.6-6.10]
    1. capture the GREATEST NUMBER of pieces;
    2. then capture WITH A KING rather than with a man, if possible;
    3. then capture the GREATEST NUMBER OF KINGS;
    4. then capture the sequence in which a KING is encountered EARLIEST;
    5. any remaining ties — free choice.
* Captured pieces are removed only at the END of the sequence, and a piece may
  not be jumped twice in one sequence.                               [FID 5.12, 6.4]
* A man promotes to king only if it ENDS its move on the last rank; a man that
  reaches the last rank via a capture stops there (it cannot continue that turn
  and does not act as a king until the next move). Because men capture forward
  only, reaching the last rank is always the end of the sequence.    [FID 4.2, 6.5]

Board orientation: for each player the bottom-right square is DARK (light square
in the lower-left / double corner on the left) [FID 2.3]. Modelled with the dark
(playing) squares at (col+row) odd, matching that orientation.

Moves are the platform's clickable cell-path notation: the squares the moving
piece visits, e.g. "1,2>2,3" (simple) or "3,4>5,6>7,4" (a chain). Because only
maximal-and-highest-priority capture sequences are legal, clicking a chain forces
it to completion.

Player 0 (White, rows 0-2) moves toward row 7; player 1 (Black, rows 5-7) toward
row 0. Draw by a 50-ply no-progress rule (no capture and no man move) and a hard
400-ply cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 8
DRAW_HALFMOVE = 50
PLY_CAP = 400
DIAGS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


@dataclass
class DraughtsState:
    board: dict = field(default_factory=dict)  # (c, r) -> (player, "m"|"k")
    to_move: int = 0
    halfmove: int = 0   # plies since last capture or man move
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _king_row(player: int) -> int:
    return N - 1 if player == 0 else 0


def _man_dirs(player: int):
    return [(1, 1), (-1, 1)] if player == 0 else [(1, -1), (-1, -1)]


def _start_board() -> dict:
    """12 men per side on the dark squares ((c+r) odd) of the three nearest
    ranks: White on rows 0-2, Black on rows 5-7. This dark-square parity places
    each player's bottom-right square on a dark cell (Italian orientation)."""
    b = {}
    for r in (0, 1, 2):
        for c in range(N):
            if (c + r) % 2 == 1:
                b[(c, r)] = (0, "m")
    for r in (5, 6, 7):
        for c in range(N):
            if (c + r) % 2 == 1:
                b[(c, r)] = (1, "m")
    return b


def _capture_paths(board, pos, origin, player, kind, captured):
    """Short-jump capture sequences from `pos` for a piece of `kind` ("m"/"k").

    `board` is the ORIGINAL board (captured pieces are removed only at the end,
    so they remain as blockers). `origin` = the moving piece's true start square
    (now vacated → treated as empty). `captured` = set of enemy squares already
    jumped this sequence (a piece may not be jumped twice).

    A man captures forward only and only over an enemy MAN (never a king); a king
    captures in all four diagonals over any enemy piece. Either way the jump is
    SHORT: the enemy must be adjacent and the landing square immediately beyond.
    A man that lands on its king row stops (promotion ends the sequence)."""
    c, r = pos
    dirs = DIAGS if kind == "k" else _man_dirs(player)
    paths = []
    for dc, dr in dirs:
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        if not _on(*land):
            continue
        occ = board.get(over)
        if occ is None or occ[0] == player:
            continue
        if over in captured or over == origin:
            continue
        if kind == "m" and occ[1] == "k":
            continue  # a man may never capture a king
        land_free = board.get(land) is None or land == origin
        if not land_free:
            continue
        if kind == "m" and land[1] == _king_row(player):
            # man reaches the last rank: it promotes and the sequence ends here
            paths.append([pos, land])
            continue
        cont = _capture_paths(board, land, origin, player, kind, captured | {over})
        if cont:
            paths += [[pos] + p for p in cont]
        else:
            paths.append([pos, land])
    return paths


class ItalianDraughts(Game):
    name = "Italian Draughts"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> DraughtsState:
        return DraughtsState(board=_start_board())

    def current_player(self, s: DraughtsState) -> int:
        return s.to_move

    def _draw(self, s: DraughtsState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def _captured_squares(self, board, path):
        """Enemy squares jumped along a visited-square path: the single occupied
        square strictly between consecutive vertices, in capture order."""
        caps = []
        for a, b in zip(path, path[1:]):
            dc = (b[0] > a[0]) - (b[0] < a[0])
            dr = (b[1] > a[1]) - (b[1] < a[1])
            step = (a[0] + dc, a[1] + dr)
            while step != b:
                if board.get(step) is not None:
                    caps.append(step)
                    break
                step = (step[0] + dc, step[1] + dr)
        return caps

    def _seq_key(self, board, path, kind):
        """Priority key for a capture sequence, to be MAXIMISED (FID 6.6-6.10):
        (number of pieces, capturing piece is a king, number of kings captured,
        captured-value vector). The value vector lists 1 for each king / 0 for
        each man in capture order; taking its lexicographic maximum places the
        captured kings as EARLY as possible (the 6.9 "king encountered first"
        tie-break). num_kings precedes the vector because capturing MORE kings
        (6.8) outranks capturing a king EARLIER (6.9)."""
        caps = self._captured_squares(board, path)
        vals = [1 if board[sq][1] == "k" else 0 for sq in caps]
        cap_val = 1 if kind == "k" else 0
        return (len(caps), cap_val, sum(vals), tuple(vals))

    def _all_moves(self, s: DraughtsState) -> list[list]:
        """Legal move paths. If any capture exists, only the capture sequences
        with the maximal priority key (FID 6.6-6.10) are legal."""
        mine = [(pos, k) for pos, k in s.board.items() if k[0] == s.to_move]
        captures = []
        for pos, (pl, kind) in mine:
            for path in _capture_paths(s.board, pos, pos, pl, kind, frozenset()):
                captures.append((path, kind))
        if captures:
            best = max(self._seq_key(s.board, p, k) for p, k in captures)
            return [p for p, k in captures if self._seq_key(s.board, p, k) == best]
        # quiet moves: men one square forward, kings one square any diagonal
        simples = []
        for pos, (pl, kind) in mine:
            c, r = pos
            dirs = DIAGS if kind == "k" else _man_dirs(pl)
            for dc, dr in dirs:
                t = (c + dc, r + dr)
                if _on(*t) and t not in s.board:
                    simples.append([pos, t])
        return simples

    def legal_moves(self, s: DraughtsState) -> list[str]:
        if self._draw(s):
            return []
        return [">".join(f"{c},{r}" for c, r in path) for path in self._all_moves(s)]

    def apply_move(self, s: DraughtsState, move: str, rng=None) -> DraughtsState:
        cells = [_cell(x) for x in move.split(">")]
        board = dict(s.board)
        pl, kind = board.pop(cells[0])
        caps = self._captured_squares(s.board, cells)
        for sq in caps:
            board.pop(sq, None)
        final = cells[-1]
        # promote only if ENDING on the king row
        if kind == "m" and final[1] == _king_row(pl):
            kind = "k"
        board[final] = (pl, kind)
        started_as_man = s.board[cells[0]][1] == "m"
        progress = bool(caps) or started_as_man
        return DraughtsState(
            board=board, to_move=1 - pl,
            halfmove=0 if progress else s.halfmove + 1, ply=s.ply + 1,
        )

    def is_terminal(self, s: DraughtsState) -> bool:
        return self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: DraughtsState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move: the player to move loses
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: DraughtsState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, k] for (c, r), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> DraughtsState:
        return DraughtsState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"], halfmove=d["halfmove"], ply=d["ply"],
        )

    def describe_move(self, s: DraughtsState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        caps = self._captured_squares(s.board, cells)
        sep = "x" if caps else "-"
        return sep.join(f"{c},{r}" for c, r in cells)

    def render(self, s: DraughtsState, perspective=None) -> dict:
        names = {0: "White", 1: "Black"}
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": "K" if k == "k" else ""}
            for (c, r), (pl, k) in s.board.items()
        ]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
