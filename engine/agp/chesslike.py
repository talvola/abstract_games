"""Shared core for chess-like games (rectangular board, slider/leaper/compound
pieces, a royal king, and the usual mate/stalemate/draw rules).

A variant subclasses :class:`ChessLike` and declares:

* ``WIDTH`` / ``HEIGHT`` and ``setup_board()`` (the opening position);
* ``PIECES`` -- a movement table ``{letter: (slide_dirs, leap_offsets)}`` (pawns
  are NOT listed here; they are handled by the pawn strategy). The king is just a
  one-step all-directions leaper, e.g. ``"K": ([], ALL8)``;
* ``HEAVY`` -- piece letters that count as mating material (everything that is not
  a lone-minor draw);
* three pluggable strategies: ``PAWN`` (a :class:`PawnRules`), ``PROMOTION`` (a
  :class:`PromotionRules`) and ``CASTLING`` (a :class:`Castling`).

The board is a dict ``(col, row) -> (player, letter)``; White = player 0 advances
toward higher rows. Moves are the platform's clickable cell-path strings
``"fc,fr>tc,tr"`` with an optional ``"=X"`` promotion suffix. State is the shared
:class:`CState`; en passant is stored uniformly as ``((target), (captured))`` --
the square an enemy pawn lands on, and the pawn it removes -- which covers both
ordinary and Berolina pawns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .game import Game

WHITE, BLACK = 0, 1

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL8 = ORTHO + DIAG
KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]

_FILES = "abcdefghijklmnopqrstuvwxyz"


def cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class CState:
    board: dict = field(default_factory=dict)         # (c, r) -> (player, letter)
    to_move: int = WHITE
    castling: frozenset = field(default_factory=frozenset)
    ep: Optional[tuple] = None                          # ((tc,tr),(cc,cr)) or None
    halfmove: int = 0
    ply: int = 0
    reps: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Pawn strategies
# --------------------------------------------------------------------------- #
class PawnRules:
    """How pawns move, capture, and attack. ``white_start`` / ``black_start`` are
    the home ranks (for the double step); ``double`` enables the two-square move."""

    def __init__(self, white_start: int, black_start: int, double: bool = True):
        self.white_start = white_start
        self.black_start = black_start
        self.double = double

    def fwd(self, player: int) -> int:
        return 1 if player == WHITE else -1

    def start(self, player: int) -> int:
        return self.white_start if player == WHITE else self.black_start

    def ep_after(self, frm, to):
        """The e.p. value ``((target),(captured))`` created by a double step, else
        None. The skipped square is the target; the pawn that moved is captured."""
        if abs(to[1] - frm[1]) == 2:
            mid = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
            return (mid, to)
        return None

    def pseudo(self, core, board, c, r, player, ep_target):
        raise NotImplementedError

    def attacks(self, core, board, c, r, by) -> bool:
        raise NotImplementedError


class StandardPawn(PawnRules):
    """Orthodox pawn: steps straight, captures diagonally."""

    def pseudo(self, core, board, c, r, player, ep_target):
        fwd = self.fwd(player)
        if core.on(c, r + fwd) and (c, r + fwd) not in board:
            yield (c, r), (c, r + fwd)
            if self.double and r == self.start(player) and (c, r + 2 * fwd) not in board:
                yield (c, r), (c, r + 2 * fwd)
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if (occ is not None and occ[0] != player) or t == ep_target:
                yield (c, r), t

    def attacks(self, core, board, c, r, by) -> bool:
        pr = r - self.fwd(by)
        return any(board.get((c + dc, pr)) == (by, "P") for dc in (-1, 1))


class BerolinaPawn(PawnRules):
    """Berolina pawn: steps diagonally, captures straight."""

    def pseudo(self, core, board, c, r, player, ep_target):
        fwd = self.fwd(player)
        for dc in (-1, 1):
            one = (c + dc, r + fwd)
            if core.on(*one) and one not in board:
                yield (c, r), one
                if self.double and r == self.start(player):
                    two = (c + 2 * dc, r + 2 * fwd)
                    if core.on(*two) and two not in board:
                        yield (c, r), two
        st = (c, r + fwd)
        if core.on(*st):
            occ = board.get(st)
            if (occ is not None and occ[0] != player) or st == ep_target:
                yield (c, r), st

    def attacks(self, core, board, c, r, by) -> bool:
        return board.get((c, r - self.fwd(by))) == (by, "P")


# --------------------------------------------------------------------------- #
# Promotion strategies. options() returns a list of choices for a pawn move,
# where None = "stay a pawn" (plain move) and a letter = promote to that piece.
# --------------------------------------------------------------------------- #
class PromotionRules:
    def options(self, core, state, frm, to) -> list:
        raise NotImplementedError

    def safety_piece(self) -> str:
        return "Q"   # what a promoting pawn becomes when only testing king safety


class LastRankPromotion(PromotionRules):
    """Promote (mandatory) on reaching the final rank; choose from ``targets``."""

    def __init__(self, targets):
        self.targets = tuple(targets)

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        last = (to[1] == core.HEIGHT - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK)
        return list(self.targets) if last else [None]


class GrandPromotion(PromotionRules):
    """Grand-Chess promotion: only to a type the player has *lost* (current count
    below the starting count); optional on the two ranks before the end and
    mandatory on the final rank."""

    def __init__(self, original: dict):
        self.original = dict(original)           # {letter: starting count}
        self.targets = tuple(original.keys())

    def _avail(self, board, player):
        cnt = {}
        for (_, (pl, t)) in board.items():
            if pl == player:
                cnt[t] = cnt.get(t, 0) + 1
        return [T for T in self.targets if cnt.get(T, 0) < self.original[T]]

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        H = core.HEIGHT
        if pl == WHITE:
            mand, opt = to[1] == H - 1, to[1] in (H - 3, H - 2)
        else:
            mand, opt = to[1] == 0, to[1] in (1, 2)
        if not (mand or opt):
            return [None]
        avail = self._avail(state.board, pl)
        return list(avail) if mand else [None] + list(avail)


# --------------------------------------------------------------------------- #
# Castling strategies
# --------------------------------------------------------------------------- #
class Castling:
    def initial_rights(self) -> frozenset:
        return frozenset()

    def moves(self, core, state):
        return iter(())

    def rook_move(self, frm, to, player):
        """If a king move (frm->to) is a castle, return (rook_from, rook_to)."""
        return None

    def update_rights(self, rights, frm, to, board) -> frozenset:
        return rights


class NoCastling(Castling):
    pass


class StandardCastling(Castling):
    """Orthodox 8x8 castling (king e1/e8, rooks a/h-file corners)."""

    CASTLES = {
        "K": ((4, 0), (6, 0), (7, 0), (5, 0), [(5, 0), (6, 0)], [(4, 0), (5, 0), (6, 0)]),
        "Q": ((4, 0), (2, 0), (0, 0), (3, 0), [(1, 0), (2, 0), (3, 0)], [(4, 0), (3, 0), (2, 0)]),
        "k": ((4, 7), (6, 7), (7, 7), (5, 7), [(5, 7), (6, 7)], [(4, 7), (5, 7), (6, 7)]),
        "q": ((4, 7), (2, 7), (0, 7), (3, 7), [(1, 7), (2, 7), (3, 7)], [(4, 7), (3, 7), (2, 7)]),
    }
    BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
    ROOK_HOME = {(7, 0): "K", (0, 0): "Q", (7, 7): "k", (0, 7): "q"}
    KING_HOME = {(4, 0): WHITE, (4, 7): BLACK}

    def initial_rights(self):
        return frozenset("KQkq")

    def moves(self, core, state):
        player = state.to_move
        enemy = 1 - player
        if core.in_check(state.board, player):
            return
        for flag in self.BY_COLOR[player]:
            if flag not in state.castling:
                continue
            kfrom, kto, rfrom, rto, empties, path = self.CASTLES[flag]
            if state.board.get(kfrom) != (player, "K") or state.board.get(rfrom) != (player, "R"):
                continue
            if any(sq in state.board for sq in empties):
                continue
            if any(core.attacked(state.board, c, r, enemy) for (c, r) in path):
                continue
            yield kfrom, kto

    def rook_move(self, frm, to, player):
        if abs(to[0] - frm[0]) != 2:
            return None
        flag = self.BY_COLOR[player][0] if to[0] > frm[0] else self.BY_COLOR[player][1]
        _, _, rfrom, rto, _, _ = self.CASTLES[flag]
        return rfrom, rto

    def update_rights(self, rights, frm, to, board):
        rights = set(rights)
        pl, t = board[frm]
        if t == "K" and frm in self.KING_HOME:
            rights -= set(self.BY_COLOR[pl])
        if frm in self.ROOK_HOME:
            rights.discard(self.ROOK_HOME[frm])
        if to in self.ROOK_HOME:                 # a rook captured on its home square
            rights.discard(self.ROOK_HOME[to])
        return frozenset(rights)


# --------------------------------------------------------------------------- #
# The shared game
# --------------------------------------------------------------------------- #
class ChessLike(Game):
    WIDTH = 8
    HEIGHT = 8
    PLY_CAP = 600
    PIECES: dict = {}
    HEAVY = ("P", "R", "Q")
    PAWN: PawnRules = None
    PROMOTION: PromotionRules = None
    CASTLING: Castling = NoCastling()

    def __init__(self):
        self._slide_map: dict = {}
        self._leap_map: dict = {}
        for T, (slides, leaps) in self.PIECES.items():
            for d in slides:
                self._slide_map.setdefault(d, set()).add(T)
            for o in leaps:
                self._leap_map.setdefault(o, set()).add(T)

    # ---- geometry / attacks -------------------------------------------------
    def on(self, c, r) -> bool:
        return 0 <= c < self.WIDTH and 0 <= r < self.HEIGHT

    def attacked(self, board, c, r, by) -> bool:
        for (dx, dy), types in self._leap_map.items():
            occ = board.get((c + dx, r + dy))
            if occ is not None and occ[0] == by and occ[1] in types:
                return True
        for (dx, dy), types in self._slide_map.items():
            cc, rr = c + dx, r + dy
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] == by and occ[1] in types:
                        return True
                    break
                cc += dx
                rr += dy
        return self.PAWN.attacks(self, board, c, r, by)

    def _king(self, board, player):
        for (c, r), (pl, t) in board.items():
            if pl == player and t == "K":
                return c, r
        return None

    def in_check(self, board, player) -> bool:
        k = self._king(board, player)
        return k is not None and self.attacked(board, k[0], k[1], 1 - player)

    # ---- move generation ----------------------------------------------------
    def _pseudo(self, state):
        board, player = state.board, state.to_move
        ep_target = state.ep[0] if state.ep else None
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "P":
                yield from self.PAWN.pseudo(self, board, c, r, player, ep_target)
                continue
            slides, leaps = self.PIECES[t]
            for dc, dr in leaps:
                tc, tr = c + dc, r + dr
                if self.on(tc, tr) and (board.get((tc, tr)) or (None,))[0] != player:
                    yield (c, r), (tc, tr)
            for dc, dr in slides:
                cc, rr = c + dc, r + dr
                while self.on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is None:
                        yield (c, r), (cc, rr)
                    else:
                        if occ[0] != player:
                            yield (c, r), (cc, rr)
                        break
                    cc += dc
                    rr += dr

    def _apply_board(self, board, frm, to, ep):
        """Board after a (non-castling) move, for king-safety testing only."""
        b = dict(board)
        pl, t = b.pop(frm)
        if t == "P" and ep is not None and to == ep[0] and to not in board:
            b.pop(ep[1], None)
        if t == "P" and (to[1] == self.HEIGHT - 1 and pl == WHITE or to[1] == 0 and pl == BLACK):
            t = self.PROMOTION.safety_piece()
        b[to] = (pl, t)
        return b

    def _legal(self, state):
        moves = []
        for frm, to in self._pseudo(state):
            nb = self._apply_board(state.board, frm, to, state.ep)
            if not self.in_check(nb, state.to_move):
                moves.append((frm, to))
        moves.extend(self.CASTLING.moves(self, state))
        return moves

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        out = []
        for f, t in self._legal(state):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if state.board[f][1] == "P":
                for ch in self.PROMOTION.options(self, state, f, t):
                    out.append(base if ch is None else base + "=" + ch)
            else:
                out.append(base)
        return out

    # ---- draws / terminal ---------------------------------------------------
    def _insufficient(self, board) -> bool:
        if any(t in self.HEAVY for (_, t) in board.values()):
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

    def _draw(self, state) -> bool:
        return (state.halfmove >= 100 or state.ply >= self.PLY_CAP
                or self._insufficient(state.board)
                or state.reps.get(self._poskey(state.board, state.to_move,
                                               state.castling, state.ep), 0) >= 3)

    def is_terminal(self, state) -> bool:
        return self._draw(state) or len(self._legal(state)) == 0

    def returns(self, state) -> list:
        if self._draw(state) or not self.in_check(state.board, state.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)

        capture = to in state.board
        ep_new = None
        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        elif t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                b.pop(state.ep[1], None)
                capture = True
            else:
                ep_new = self.PAWN.ep_after(frm, to)

        if t == "P" and promo:
            t = promo
        b[to] = (pl, t)

        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        reset = capture or state.board[frm][1] == "P"
        key = self._poskey(b, 1 - pl, castling, ep_new)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps)

    # ---- (de)serialize ------------------------------------------------------
    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None):
        board = self.setup_board()
        rights = self.CASTLING.initial_rights()
        return CState(board=board, to_move=WHITE, castling=rights, ep=None,
                      reps={self._poskey(board, WHITE, rights, None): 1})

    def current_player(self, state) -> int:
        return state.to_move

    def setup_board(self) -> dict:
        raise NotImplementedError

    def _poskey(self, board, to_move, castling, ep) -> str:
        et = ep[0] if ep else None
        rows = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                occ = board.get((c, r))
                rows.append("." if occ is None else "wb"[occ[0]] + occ[1])
        return "|".join(rows) + f"#{to_move}#{''.join(sorted(castling))}#{et}"

    def serialize(self, state) -> dict:
        ep = state.ep
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "castling": "".join(sorted(state.castling)),
            "ep": f"{ep[0][0]},{ep[0][1]},{ep[1][0]},{ep[1][1]}" if ep else None,
            "halfmove": state.halfmove,
            "ply": state.ply,
            "reps": dict(state.reps),
        }

    def deserialize(self, d: dict):
        ep = None
        if d.get("ep"):
            a, b, c, e = (int(x) for x in d["ep"].split(","))
            ep = ((a, b), (c, e))
        return CState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(d.get("castling", "")),
            ep=ep,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
        )

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        raw, promo = (move.split("=") + [None])[:2]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        if t == "K" and self.CASTLING.rook_move(frm, to, pl) is not None:
            return "O-O" if to[0] > frm[0] else "O-O-O"
        capture = to in state.board or (t == "P" and state.ep is not None and to == state.ep[0])
        alg = lambda c: f"{_FILES[c[0]]}{c[1] + 1}"  # noqa: E731
        text = f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}"
        return text + (f"={promo}" if promo else "")

    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": t}
            for (c, r), (pl, t) in state.board.items()
        ]
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins (checkmate)"
        elif self.in_check(state.board, state.to_move):
            caption = f"{names[state.to_move]} to move (check)"
        else:
            caption = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
