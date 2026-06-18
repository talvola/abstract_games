"""Grand Chess (Christian Freeling, 1984), 10x10.

Differences from orthodox chess:
* 10x10 board (files a-j, ranks 1-10).
* Two compound pieces: the Marshall "M" (rook + knight) and the Cardinal "C"
  (bishop + knight).
* Pawns start on the third rank and may step one or two squares on the first move
  (en passant applies as usual).
* No castling.
* Promotion is restricted and rank-dependent: a pawn may promote only to a piece
  type its owner has *lost* (current count on the board < starting count, so you
  can never have more of a piece than you began with). It is optional on the 8th
  and 9th ranks and compulsory on the 10th; with nothing available to promote to,
  a pawn cannot advance onto the final rank.

White = player 0 (rows 0-2, advancing up). Moves use the clickable cell-path
notation; promotion appends "=Q/M/C/R/B/N". An optional promotion also offers the
plain (no-suffix) move to stay a pawn.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 10
WHITE, BLACK = 0, 1
PLY_CAP = 800

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL8 = ORTHO + DIAG
KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
PROMO = ("Q", "M", "C", "R", "B", "N")
# how many of each promotable type a side starts with (king/pawn excluded)
ORIGINAL = {"Q": 1, "M": 1, "C": 1, "R": 2, "B": 2, "N": 2}

# sliding directions per piece (Marshall slides like a rook, Cardinal like a bishop)
SLIDE = {"R": ORTHO, "B": DIAG, "Q": ALL8, "M": ORTHO, "C": DIAG}


@dataclass
class GrandState:
    board: dict = field(default_factory=dict)   # (c, r) -> (player, piece)
    to_move: int = WHITE
    ep: Optional[tuple] = None
    halfmove: int = 0
    ply: int = 0
    reps: dict = field(default_factory=dict)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    # corners: rooks on rank 1 / rank 10
    b[(0, 0)] = b[(N - 1, 0)] = (WHITE, "R")
    b[(0, N - 1)] = b[(N - 1, N - 1)] = (BLACK, "R")
    # rank 2 / rank 9 majors:  N B Q K M C B N  on files b..i
    majors = ["N", "B", "Q", "K", "M", "C", "B", "N"]
    for i, t in enumerate(majors):
        c = i + 1
        b[(c, 1)] = (WHITE, t)
        b[(c, N - 2)] = (BLACK, t)
    # pawns on rank 3 / rank 8
    for c in range(N):
        b[(c, 2)] = (WHITE, "P")
        b[(c, N - 3)] = (BLACK, "P")
    return b


def _attacked(board: dict, c: int, r: int, by: int) -> bool:
    """Is square (c, r) attacked by player ``by``?"""
    for dc, dr in KNIGHT:                       # knight + Marshall + Cardinal leap
        occ = board.get((c + dc, r + dr))
        if occ is not None and occ[0] == by and occ[1] in ("N", "M", "C"):
            return True
    for dc, dr in ALL8:                         # adjacent king
        if board.get((c + dc, r + dr)) == (by, "K"):
            return True
    pr = r - 1 if by == WHITE else r + 1        # pawn captures diagonally
    for dc in (-1, 1):
        if board.get((c + dc, pr)) == (by, "P"):
            return True
    for dirs, sliders in ((ORTHO, ("R", "Q", "M")), (DIAG, ("B", "Q", "C"))):
        for dc, dr in dirs:
            cc, rr = c + dc, r + dr
            while _on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] == by and occ[1] in sliders:
                        return True
                    break
                cc += dc
                rr += dr
    return False


def _king(board: dict, player: int):
    for (c, r), (pl, t) in board.items():
        if pl == player and t == "K":
            return c, r
    return None


def _in_check(board: dict, player: int) -> bool:
    k = _king(board, player)
    return k is not None and _attacked(board, k[0], k[1], 1 - player)


def _pseudo_moves(board: dict, player: int, ep):
    for (c, r), (pl, t) in list(board.items()):
        if pl != player:
            continue
        # leaper component (knight for N/M/C, single-step all-8 for K)
        if t in ("N", "M", "C"):
            for dc, dr in KNIGHT:
                tc, tr = c + dc, r + dr
                if _on(tc, tr) and (board.get((tc, tr)) or (None,))[0] != player:
                    yield (c, r), (tc, tr)
        if t == "K":
            for dc, dr in ALL8:
                tc, tr = c + dc, r + dr
                if _on(tc, tr) and (board.get((tc, tr)) or (None,))[0] != player:
                    yield (c, r), (tc, tr)
        # sliding component
        if t in SLIDE:
            for dc, dr in SLIDE[t]:
                cc, rr = c + dc, r + dr
                while _on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is None:
                        yield (c, r), (cc, rr)
                    else:
                        if occ[0] != player:
                            yield (c, r), (cc, rr)
                        break
                    cc += dc
                    rr += dr
        if t == "P":
            fwd = 1 if player == WHITE else -1
            start = 2 if player == WHITE else N - 3
            if _on(c, r + fwd) and (c, r + fwd) not in board:
                yield (c, r), (c, r + fwd)
                if r == start and (c, r + 2 * fwd) not in board:
                    yield (c, r), (c, r + 2 * fwd)
            for dc in (-1, 1):
                tc, tr = c + dc, r + fwd
                if not _on(tc, tr):
                    continue
                occ = board.get((tc, tr))
                if (occ is not None and occ[0] != player) or (tc, tr) == ep:
                    yield (c, r), (tc, tr)


def _apply_board(board: dict, frm, to, ep):
    b = dict(board)
    pl, t = b.pop(frm)
    if t == "P" and to == ep and to not in board:        # en passant
        b.pop((to[0], frm[1]), None)
    if t == "P" and (to[1] == N - 1 and pl == WHITE or to[1] == 0 and pl == BLACK):
        t = "Q"                                          # auto-queen for safety test
    b[to] = (pl, t)
    return b


def _poskey(board, to_move, ep) -> str:
    rows = []
    for r in range(N):
        for c in range(N):
            occ = board.get((c, r))
            rows.append("." if occ is None else "wb"[occ[0]] + occ[1])
    return "|".join(rows) + f"#{to_move}#{ep}"


def _insufficient(board: dict) -> bool:
    if any(t in ("P", "R", "Q", "M", "C") for (_, t) in board.values()):
        return False
    minors = [(sq, pl) for sq, (pl, t) in board.items() if t in ("B", "N")]
    bishops = [(sq, pl) for sq, (pl, t) in board.items() if t == "B"]
    if len(minors) <= 1:
        return True
    if len(minors) == 2 and len(bishops) == 2:
        (s1, p1), (s2, p2) = bishops
        if p1 != p2 and (s1[0] + s1[1]) % 2 == (s2[0] + s2[1]) % 2:
            return True
    return False


def _promo_avail(board: dict, player: int) -> list[str]:
    """Piece types the player may promote to: those they currently have fewer of
    than at the start (i.e. a piece of that type has been captured)."""
    cnt = {}
    for (_, (pl, t)) in board.items():
        if pl == player:
            cnt[t] = cnt.get(t, 0) + 1
    return [T for T in PROMO if cnt.get(T, 0) < ORIGINAL[T]]


class GrandChess(Game):
    uid = "grand_chess"
    name = "Grand Chess"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GrandState:
        board = _start_board()
        return GrandState(board=board, reps={_poskey(board, WHITE, None): 1})

    def current_player(self, s: GrandState) -> int:
        return s.to_move

    def _legal(self, s: GrandState):
        moves = []
        for frm, to in _pseudo_moves(s.board, s.to_move, s.ep):
            nb = _apply_board(s.board, frm, to, s.ep)
            if not _in_check(nb, s.to_move):
                moves.append((frm, to))
        return moves

    def legal_moves(self, s: GrandState) -> list[str]:
        if self._draw(s):
            return []
        avail = _promo_avail(s.board, s.to_move)
        out = []
        for f, t in self._legal(s):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            pl, pt = s.board[f]
            if pt != "P":
                out.append(base)
                continue
            if pl == WHITE:
                mandatory, optional = t[1] == N - 1, t[1] in (N - 3, N - 2)
            else:
                mandatory, optional = t[1] == 0, t[1] in (1, 2)
            if mandatory:
                out += [base + "=" + T for T in avail]      # no avail -> move dropped
            elif optional:
                out.append(base)                            # stay a pawn
                out += [base + "=" + T for T in avail]
            else:
                out.append(base)
        return out

    def _draw(self, s: GrandState) -> bool:
        return (s.halfmove >= 100 or s.ply >= PLY_CAP
                or _insufficient(s.board)
                or s.reps.get(_poskey(s.board, s.to_move, s.ep), 0) >= 3)

    def apply_move(self, s: GrandState, move: str, rng=None) -> GrandState:
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        pl, t = s.board[frm]
        b = dict(s.board)
        b.pop(frm)

        capture = to in s.board
        ep = None
        if t == "P" and s.ep is not None and to == s.ep and not capture:   # en passant
            b.pop((to[0], frm[1]), None)
            capture = True
        elif t == "P" and abs(to[1] - frm[1]) == 2:                        # double step
            ep = (frm[0], (frm[1] + to[1]) // 2)

        if t == "P" and promo in PROMO:
            t = promo
        b[to] = (pl, t)

        reset = capture or s.board[frm][1] == "P"
        key = _poskey(b, 1 - pl, ep)
        reps = dict(s.reps)
        reps[key] = reps.get(key, 0) + 1
        return GrandState(board=b, to_move=1 - pl, ep=ep,
                          halfmove=0 if reset else s.halfmove + 1,
                          ply=s.ply + 1, reps=reps)

    def is_terminal(self, s: GrandState) -> bool:
        return self._draw(s) or len(self.legal_moves(s)) == 0

    def returns(self, s: GrandState) -> list[float]:
        if self._draw(s) or not _in_check(s.board, s.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if s.to_move == WHITE else [1.0, -1.0]

    def serialize(self, s: GrandState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in s.board.items()},
            "to_move": s.to_move,
            "ep": f"{s.ep[0]},{s.ep[1]}" if s.ep else None,
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
        }

    def deserialize(self, d: dict) -> GrandState:
        return GrandState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ep=_cell(d["ep"]) if d.get("ep") else None,
            halfmove=d["halfmove"],
            ply=d["ply"],
            reps=dict(d.get("reps", {})),
        )

    def describe_move(self, s: GrandState, move: str) -> str:
        raw = move
        promo = None
        if "=" in raw:
            raw, promo = raw.split("=")
        fs, ts = raw.split(">")
        frm, to = _cell(fs), _cell(ts)
        pl, t = s.board.get(frm, (None, "?"))
        capture = to in s.board or (t == "P" and s.ep is not None and to == s.ep)
        alg = lambda c: f"{'abcdefghij'[c[0]]}{c[1] + 1}"  # noqa: E731
        text = f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}"
        if promo:
            text += f"={promo}"
        return text

    def render(self, s: GrandState, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": t}
            for (c, r), (pl, t) in s.board.items()
        ]
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins (checkmate)"
        elif _in_check(s.board, s.to_move):
            caption = f"{names[s.to_move]} to move (check)"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
