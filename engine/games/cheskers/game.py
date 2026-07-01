"""Cheskers — Solomon W. Golomb's 1948 chess/checkers hybrid.

Played on the 32 dark squares of an 8x8 board (col+row even). Each side has two
Kings, a Bishop, a Camel, and eight Pawns.

Movement / capture (faithful to chessvariants.com / Wikipedia / Seattle Cosmic):
  * Pawn  — moves one square diagonally forward (no capture); captures by jumping
            two squares diagonally forward over an adjacent enemy to the empty
            square beyond (checkers style, multi-jump chains).
  * King  — a *checkers* king: one diagonal step in any of the four directions;
            captures by jumping (checkers style, any diagonal direction, multi-jump).
  * Bishop— a normal chess bishop: slides any distance diagonally, captures by
            replacement (landing on the enemy square). Blocked by pieces.
  * Camel — a (1,3)/(3,1) leaper ("one diagonal and two straight"): leaps over
            intervening pieces (like a knight) and captures by replacement.

Forced capture: if any Pawn or King can make a checkers jump, the player MUST
capture this turn — but may capture with ANY piece (pawn, king, bishop or camel).
If only a Bishop or Camel can capture (no pawn/king jump exists), capturing is
optional. So the obligation is triggered solely by an available pawn/king jump.

Promotion: a Pawn reaching the far row ends its move and promotes to a King,
Bishop or Camel (player's choice — the "=K"/"=B"/"=C" move suffix).

Win: capture ALL of the opponent's Kings, or stalemate the opponent (they have
no legal move). Termination safety: 50-ply no-progress draw + 400-ply hard cap.

Player 0 = Black (top rows, moves first, advances toward row 0).
Player 1 = White (bottom rows, advances toward row 7).

Moves are the platform's clickable cell-path notation, e.g. "3,5>2,4" (a step),
"3,5>1,3>3,1" (a double jump), "1,5>0,6=B" (a pawn promoting to Bishop).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 8
DRAW_HALFMOVE = 50   # plies with no capture and no pawn move -> draw
PLY_CAP = 400        # hard ply cap -> draw

DIAGS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]


@dataclass
class CheskersState:
    board: dict = field(default_factory=dict)  # (c, r) -> (player, kind) kind in {"p","K","B","C"}
    to_move: int = 0
    winner: int | None = None
    halfmove: int = 0
    ply: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _pawn_dirs(player: int):
    return [(1, -1), (-1, -1)] if player == 0 else [(1, 1), (-1, 1)]


def _promo_row(player: int) -> int:
    return 0 if player == 0 else 7


def _start_board() -> dict:
    b = {}
    # Player 0 = Black (top). Kings d8,f8; Bishop h8; Camel b8; pawns a7..h6.
    b[(3, 7)] = (0, "K")
    b[(5, 7)] = (0, "K")
    b[(7, 7)] = (0, "B")
    b[(1, 7)] = (0, "C")
    for c, r in [(0, 6), (1, 5), (2, 6), (3, 5), (4, 6), (5, 5), (6, 6), (7, 5)]:
        b[(c, r)] = (0, "p")
    # Player 1 = White (bottom). Kings c1,e1; Bishop a1; Camel g1; pawns a3..h2.
    b[(2, 0)] = (1, "K")
    b[(4, 0)] = (1, "K")
    b[(0, 0)] = (1, "B")
    b[(6, 0)] = (1, "C")
    for c, r in [(0, 2), (1, 1), (2, 2), (3, 1), (4, 2), (5, 1), (6, 2), (7, 1)]:
        b[(c, r)] = (1, "p")
    return b


def _checkers_jumps(board: dict, pos, player: int, kind: str):
    """Maximal checkers jump chains for a pawn ("p") or king ("K") at pos.
    Returns list of paths [pos, land, ...]. A pawn that reaches the promotion
    row ends its move (no further jumping)."""
    dirs = _pawn_dirs(player) if kind == "p" else DIAGS
    c, r = pos
    paths = []
    for dc, dr in dirs:
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        occ = board.get(over)
        if _on(*land) and occ is not None and occ[0] != player and board.get(land) is None:
            nb = dict(board)
            del nb[over]
            del nb[pos]
            nb[land] = (player, kind)
            promoted = kind == "p" and land[1] == _promo_row(player)
            cont = [] if promoted else _checkers_jumps(nb, land, player, kind)
            if cont:
                paths += [[pos] + p for p in cont]
            else:
                paths.append([pos, land])
    return paths


def _gen(s: CheskersState):
    """Structured legal moves as (cells, kind, is_capture), honouring the
    pawn/king forced-capture rule."""
    board, pl = s.board, s.to_move
    pk_jumps = []   # pawn/king checkers jumps (trigger the obligation)
    bc_caps = []    # bishop/camel replacement captures
    quiets = []     # non-capture moves
    for pos, (owner, kind) in board.items():
        if owner != pl:
            continue
        c, r = pos
        if kind == "p":
            for path in _checkers_jumps(board, pos, pl, "p"):
                pk_jumps.append((path, "p", True))
            for dc, dr in _pawn_dirs(pl):
                t = (c + dc, r + dr)
                if _on(*t) and t not in board:
                    quiets.append(([pos, t], "p", False))
        elif kind == "K":
            for path in _checkers_jumps(board, pos, pl, "K"):
                pk_jumps.append((path, "K", True))
            for dc, dr in DIAGS:
                t = (c + dc, r + dr)
                if _on(*t) and t not in board:
                    quiets.append(([pos, t], "K", False))
        elif kind == "B":
            for dc, dr in DIAGS:
                cc, rr = c + dc, r + dr
                while _on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is None:
                        quiets.append(([pos, (cc, rr)], "B", False))
                    elif occ[0] != pl:
                        bc_caps.append(([pos, (cc, rr)], "B", True))
                        break
                    else:
                        break
                    cc += dc
                    rr += dr
        elif kind == "C":
            for dc, dr in CAMEL:
                t = (c + dc, r + dr)
                if not _on(*t):
                    continue
                occ = board.get(t)
                if occ is None:
                    quiets.append(([pos, t], "C", False))
                elif occ[0] != pl:
                    bc_caps.append(([pos, t], "C", True))
    if pk_jumps:                     # forced: only capturing moves (any piece)
        return pk_jumps + bc_caps
    return quiets + bc_caps          # optional bishop/camel captures + quiets


class Cheskers(Game):
    uid = "cheskers"
    name = "Cheskers"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> CheskersState:
        return CheskersState(board=_start_board(), to_move=0)

    def current_player(self, s: CheskersState) -> int:
        return s.to_move

    def _draw(self, s: CheskersState) -> bool:
        return s.halfmove >= DRAW_HALFMOVE or s.ply >= PLY_CAP

    def legal_moves(self, s: CheskersState) -> list[str]:
        if s.winner is not None or self._draw(s):
            return []
        out = []
        pl = s.to_move
        for cells, kind, _cap in _gen(s):
            base = ">".join(f"{c},{r}" for c, r in cells)
            if kind == "p" and cells[-1][1] == _promo_row(pl):
                out += [f"{base}={ch}" for ch in ("K", "B", "C")]
            else:
                out.append(base)
        return out

    def apply_move(self, s: CheskersState, move: str, rng=None) -> CheskersState:
        parts = move.split("=")
        promo = parts[1] if len(parts) > 1 else None
        cells = [_cell(x) for x in parts[0].split(">")]
        board = dict(s.board)
        pl, kind = board.pop(cells[0])
        captured = False
        if kind in ("p", "K"):
            for a, b in zip(cells, cells[1:]):
                if abs(b[0] - a[0]) == 2:   # a checkers jump step
                    mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
                    if board.pop(mid, None) is not None:
                        captured = True
        else:   # bishop/camel capture by replacement
            if s.board.get(cells[-1]) is not None:
                captured = True
        final = cells[-1]
        if kind == "p" and final[1] == _promo_row(pl):
            kind = promo   # "K" / "B" / "C"
        board[final] = (pl, kind)
        opp = 1 - pl
        opp_kings = sum(1 for o, k in board.values() if o == opp and k == "K")
        winner = pl if opp_kings == 0 else None
        progress = captured or s.board[cells[0]][1] == "p"
        return CheskersState(
            board=board,
            to_move=opp,
            winner=winner,
            halfmove=0 if progress else s.halfmove + 1,
            ply=s.ply + 1,
        )

    def is_terminal(self, s: CheskersState) -> bool:
        if s.winner is not None or self._draw(s):
            return True
        return len(_gen(s)) == 0

    def returns(self, s: CheskersState) -> list[float]:
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if self._draw(s):
            return [0.0, 0.0]
        # stalemate: the player to move has no legal move and loses
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: CheskersState) -> dict:
        return {
            "board": {f"{c},{r}": [o, k] for (c, r), (o, k) in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "halfmove": s.halfmove,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> CheskersState:
        return CheskersState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            halfmove=d["halfmove"],
            ply=d["ply"],
        )

    def describe_move(self, s: CheskersState, move: str) -> str:
        parts = move.split("=")
        promo = parts[1] if len(parts) > 1 else None
        cells = [_cell(x) for x in parts[0].split(">")]
        entry = s.board.get(cells[0])
        kind = entry[1] if entry else "p"
        if kind in ("p", "K"):
            capture = any(abs(b[0] - a[0]) == 2 for a, b in zip(cells, cells[1:]))
        else:
            capture = s.board.get(cells[-1]) is not None
        prefix = "" if kind == "p" else kind
        sep = "x" if capture else "-"
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        text = prefix + sep.join(alg(c) for c in cells)
        if promo:
            text += "=" + promo
        return text

    def render(self, s: CheskersState, perspective=None) -> dict:
        names = {0: "Black", 1: "White"}
        label = {"p": "", "K": "K", "B": "B", "C": "C"}
        pieces = [
            {"cell": f"{c},{r}", "owner": o, "label": label[k]}
            for (c, r), (o, k) in s.board.items()
        ]
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw"
            else:
                caption = f"{names[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
