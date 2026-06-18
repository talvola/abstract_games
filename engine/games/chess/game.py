"""Standard chess (8x8), full rules.

Implements castling (both sides), en passant, pawn double-step and promotion to
Q/R/B/N, check / checkmate / stalemate, and draws by the fifty-move rule,
threefold repetition and insufficient material. White = player 0 (rows 0-1,
moving up the board); Black = player 1 (rows 6-7, moving down).

Move notation is the platform's clickable cell-path "fc,fr>tc,tr":
* normal move / capture: "4,1>4,3"
* promotion: "4,6>4,7=Q" (=Q/=R/=B/=N -- the UI shows a picker)
* castling: the king's two-square move, e.g. white O-O "4,0>6,0", O-O-O
  "4,0>2,0" (the rook is moved automatically)
* en passant: the capturing pawn's diagonal step onto the empty target square.

A hard ply cap backstops termination for random play; real games end well before
it via the fifty-move / repetition rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 8
WHITE, BLACK = 0, 1
PLY_CAP = 600

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL8 = ORTHO + DIAG
KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]
PROMO = ("Q", "R", "B", "N")

# castling: flag -> (king_from, king_to, rook_from, rook_to, empties, king_path)
CASTLES = {
    "K": ((4, 0), (6, 0), (7, 0), (5, 0), [(5, 0), (6, 0)], [(4, 0), (5, 0), (6, 0)]),
    "Q": ((4, 0), (2, 0), (0, 0), (3, 0), [(1, 0), (2, 0), (3, 0)], [(4, 0), (3, 0), (2, 0)]),
    "k": ((4, 7), (6, 7), (7, 7), (5, 7), [(5, 7), (6, 7)], [(4, 7), (5, 7), (6, 7)]),
    "q": ((4, 7), (2, 7), (0, 7), (3, 7), [(1, 7), (2, 7), (3, 7)], [(4, 7), (3, 7), (2, 7)]),
}
CASTLE_BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
ROOK_HOME = {(7, 0): "K", (0, 0): "Q", (7, 7): "k", (0, 7): "q"}
KING_HOME = {(4, 0): WHITE, (4, 7): BLACK}


@dataclass
class ChessState:
    board: dict = field(default_factory=dict)   # (c, r) -> (player, piece_letter)
    to_move: int = WHITE
    castling: frozenset = field(default_factory=frozenset)  # subset of K/Q/k/q
    ep: Optional[tuple] = None                   # en-passant target square or None
    halfmove: int = 0                            # plies since capture or pawn move
    ply: int = 0
    reps: dict = field(default_factory=dict)     # position key -> times seen


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start_board() -> dict:
    b = {}
    for c in range(N):
        b[(c, 0)] = (WHITE, BACK_RANK[c])
        b[(c, 1)] = (WHITE, "P")
        b[(c, 6)] = (BLACK, "P")
        b[(c, 7)] = (BLACK, BACK_RANK[c])
    return b


def _attacked(board: dict, c: int, r: int, by: int) -> bool:
    """Is square (c, r) attacked by player ``by``?"""
    for dc, dr in KNIGHT:
        if board.get((c + dc, r + dr)) == (by, "N"):
            return True
    for dc, dr in ALL8:
        if board.get((c + dc, r + dr)) == (by, "K"):
            return True
    pr = r - 1 if by == WHITE else r + 1   # a `by` pawn one rank toward its target
    for dc in (-1, 1):
        if board.get((c + dc, pr)) == (by, "P"):
            return True
    for dirs, sliders in ((ORTHO, ("R", "Q")), (DIAG, ("B", "Q"))):
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
    """Pseudo-legal (from, to) moves, ignoring own-king safety. Castling is added
    separately in _legal (it needs attack tests). En passant is included."""
    for (c, r), (pl, t) in list(board.items()):
        if pl != player:
            continue
        if t in ("K", "N"):
            for dc, dr in (ALL8 if t == "K" else KNIGHT):
                tc, tr = c + dc, r + dr
                if _on(tc, tr) and (board.get((tc, tr)) or (None,))[0] != player:
                    yield (c, r), (tc, tr)
        elif t in ("R", "B", "Q"):
            dirs = ORTHO if t == "R" else DIAG if t == "B" else ALL8
            for dc, dr in dirs:
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
        elif t == "P":
            fwd = 1 if player == WHITE else -1
            start = 1 if player == WHITE else 6
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
    """Board after a (non-castling) move, with promotions auto-queened and en
    passant captures removed. Used only for king-safety testing."""
    b = dict(board)
    pl, t = b.pop(frm)
    if t == "P" and to == ep and to not in board:        # en passant capture
        b.pop((to[0], frm[1]), None)
    if t == "P" and (to[1] == N - 1 and pl == WHITE or to[1] == 0 and pl == BLACK):
        t = "Q"
    b[to] = (pl, t)
    return b


def _poskey(board, to_move, castling, ep) -> str:
    rows = []
    for r in range(N):
        for c in range(N):
            occ = board.get((c, r))
            rows.append("." if occ is None else "wb"[occ[0]] + occ[1])
    return "|".join(rows) + f"#{to_move}#{''.join(sorted(castling))}#{ep}"


def _insufficient(board: dict) -> bool:
    """Only the dead-drawn material configurations (KvK, K+minor v K, KB v KB on
    same-coloured squares). The fifty-move rule covers everything else."""
    if any(t in ("P", "R", "Q") for (_, t) in board.values()):
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


class Chess(Game):
    uid = "chess"
    name = "Chess"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> ChessState:
        board = _start_board()
        castling = frozenset("KQkq")
        key = _poskey(board, WHITE, castling, None)
        return ChessState(board=board, castling=castling, reps={key: 1})

    def current_player(self, s: ChessState) -> int:
        return s.to_move

    def _castle_moves(self, s: ChessState):
        """Legal castling king-moves (frm, to) for the side to move."""
        enemy = 1 - s.to_move
        if _in_check(s.board, s.to_move):
            return
        for flag in CASTLE_BY_COLOR[s.to_move]:
            if flag not in s.castling:
                continue
            kfrom, kto, rfrom, rto, empties, path = CASTLES[flag]
            if s.board.get(kfrom) != (s.to_move, "K") or s.board.get(rfrom) != (s.to_move, "R"):
                continue
            if any(sq in s.board for sq in empties):
                continue
            if any(_attacked(s.board, c, r, enemy) for (c, r) in path):
                continue
            yield kfrom, kto

    def _legal(self, s: ChessState):
        moves = []
        for frm, to in _pseudo_moves(s.board, s.to_move, s.ep):
            nb = _apply_board(s.board, frm, to, s.ep)
            if not _in_check(nb, s.to_move):
                moves.append((frm, to))
        moves.extend(self._castle_moves(s))
        return moves

    def _is_promotion(self, board: dict, frm, to) -> bool:
        pl, t = board[frm]
        return t == "P" and ((to[1] == N - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK))

    def legal_moves(self, s: ChessState) -> list[str]:
        if self._draw(s):
            return []
        out = []
        for f, t in self._legal(s):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if self._is_promotion(s.board, f, t):
                out += [base + "=" + p for p in PROMO]
            else:
                out.append(base)
        return out

    def _draw(self, s: ChessState) -> bool:
        return (s.halfmove >= 100 or s.ply >= PLY_CAP
                or _insufficient(s.board)
                or s.reps.get(_poskey(s.board, s.to_move, s.castling, s.ep), 0) >= 3)

    def apply_move(self, s: ChessState, move: str, rng=None) -> ChessState:
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        pl, t = s.board[frm]
        b = dict(s.board)
        b.pop(frm)

        capture = to in s.board
        ep_target = None

        if t == "K" and abs(to[0] - frm[0]) == 2:                 # castling
            flag = CASTLE_BY_COLOR[pl][0] if to[0] == 6 else CASTLE_BY_COLOR[pl][1]
            _, _, rfrom, rto, _, _ = CASTLES[flag]
            b[rto] = b.pop(rfrom)
        elif t == "P" and to == s.ep and not capture:             # en passant
            b.pop((to[0], frm[1]), None)
            capture = True
        elif t == "P" and abs(to[1] - frm[1]) == 2:               # double step
            ep_target = (frm[0], (frm[1] + to[1]) // 2)

        if t == "P" and (to[1] == N - 1 and pl == WHITE or to[1] == 0 and pl == BLACK):
            t = promo if promo in PROMO else "Q"
        b[to] = (pl, t)

        # castling rights
        castling = set(s.castling)
        if frm in KING_HOME and KING_HOME[frm] == pl and s.board[frm][1] == "K":
            castling -= set(CASTLE_BY_COLOR[pl])
        if frm in ROOK_HOME:
            castling.discard(ROOK_HOME[frm])
        if to in ROOK_HOME:                                       # rook captured at home
            castling.discard(ROOK_HOME[to])
        castling = frozenset(castling)

        reset = capture or s.board[frm][1] == "P"
        key = _poskey(b, 1 - pl, castling, ep_target)
        reps = dict(s.reps)
        reps[key] = reps.get(key, 0) + 1
        return ChessState(
            board=b, to_move=1 - pl, castling=castling, ep=ep_target,
            halfmove=0 if reset else s.halfmove + 1, ply=s.ply + 1, reps=reps,
        )

    def is_terminal(self, s: ChessState) -> bool:
        return self._draw(s) or len(self._legal(s)) == 0

    def returns(self, s: ChessState) -> list[float]:
        if self._draw(s) or not _in_check(s.board, s.to_move):
            return [0.0, 0.0]                       # draw or stalemate
        return [-1.0, 1.0] if s.to_move == WHITE else [1.0, -1.0]   # mated

    def serialize(self, s: ChessState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in s.board.items()},
            "to_move": s.to_move,
            "castling": "".join(sorted(s.castling)),
            "ep": f"{s.ep[0]},{s.ep[1]}" if s.ep else None,
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
        }

    def deserialize(self, d: dict) -> ChessState:
        return ChessState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(d.get("castling", "")),
            ep=_cell(d["ep"]) if d.get("ep") else None,
            halfmove=d["halfmove"],
            ply=d["ply"],
            reps=dict(d.get("reps", {})),
        )

    def describe_move(self, s: ChessState, move: str) -> str:
        raw = move
        promo = None
        if "=" in raw:
            raw, promo = raw.split("=")
        fs, ts = raw.split(">")
        frm, to = _cell(fs), _cell(ts)
        pl, t = s.board.get(frm, (None, "?"))
        if t == "K" and abs(to[0] - frm[0]) == 2:
            return "O-O" if to[0] == 6 else "O-O-O"
        capture = to in s.board or (t == "P" and to == s.ep)
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        text = f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}"
        if promo:
            text += f"={promo}"
        return text

    def render(self, s: ChessState, perspective=None) -> dict:
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
