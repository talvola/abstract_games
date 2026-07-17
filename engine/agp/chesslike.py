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

import math
from dataclasses import dataclass, field
from typing import Optional

from .game import Game

WHITE, BLACK = 0, 1

# Movement signatures for classifying compound pieces → a UI icon (see _piece_icon).
_ORTHO_DIRS = {(1, 0), (-1, 0), (0, 1), (0, -1)}
_DIAG_DIRS = {(1, 1), (1, -1), (-1, 1), (-1, -1)}
_KNIGHT_OFFS = {(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)}
_KING_OFFS = frozenset(_ORTHO_DIRS | _DIAG_DIRS)
_FERZ_OFFS = frozenset(_DIAG_DIRS)
_WAZIR_OFFS = frozenset(_ORTHO_DIRS)
_ALFIL_OFFS = frozenset({(2, 2), (2, -2), (-2, 2), (-2, -2)})
_DABBABA_OFFS = frozenset({(2, 0), (-2, 0), (0, 2), (0, -2)})
_CAMEL_OFFS = frozenset({(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)})
_ZEBRA_OFFS = frozenset({(2, 3), (3, 2), (-2, 3), (-3, 2), (2, -3), (3, -2), (-2, -3), (-3, -2)})
_GIRAFFE_OFFS = frozenset({(1, 4), (4, 1), (-1, 4), (-4, 1), (1, -4), (4, -1), (-1, -4), (-4, -1)})
# Pure leapers/steppers, keyed by their EXACT leap set -> icon name in
# web/src/pieceImages.js. Movement-keyed like the compound table in
# ``_piece_icon`` so letters stay variant-local.
_LEAPER_ICONS = {
    _FERZ_OFFS: "ferz",
    _WAZIR_OFFS: "wazir",
    _KING_OFFS: "mann",                                # non-royal king-mover
    _ALFIL_OFFS: "alfil",
    _DABBABA_OFFS: "dabbaba",
    _ZEBRA_OFFS: "zebra",
    _GIRAFFE_OFFS: "giraffe",
    frozenset(_WAZIR_OFFS | _ALFIL_OFFS | _DABBABA_OFFS): "champion",   # Omega Chess
    frozenset(_FERZ_OFFS | _CAMEL_OFFS): "wizard",                      # Omega Chess
    frozenset(_KING_OFFS | _KNIGHT_OFFS): "centaur",
}

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
    # --- drop / reserve support (empty + unused unless DROPS is enabled) ---
    hands: dict = field(default_factory=dict)           # player -> {letter: count}
    promoted: frozenset = field(default_factory=frozenset)  # squares holding a promoted piece


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
# Drop / reserve strategies. A drop move is the string "L@c,r" (place a piece of
# type L from the side-to-move's reserve onto an empty cell). When DROPS is the
# default NoDrops every hook is a no-op, so a variant without a reserve behaves
# and serialises exactly as before.
# --------------------------------------------------------------------------- #
class DropRules:
    enabled = False

    def initial_hands(self, core) -> dict:
        """The reserve each player starts with: ``{player: {letter: count}}``."""
        return {}

    def can_drop_on(self, core, state, letter, to, player) -> bool:
        """Per-type restriction on the (already-empty) target cell."""
        return True

    def captured_to_hand(self, core, letter, was_promoted):
        """The piece type the capturer banks when capturing ``letter`` (which was
        a promoted piece iff ``was_promoted``), or ``None`` to bank nothing."""
        return None


class NoDrops(DropRules):
    enabled = False


class CrazyhouseDrops(DropRules):
    """Crazyhouse: a captured piece switches colour and goes to the capturer's
    reserve (a promoted piece reverts to a pawn); from the reserve it can be
    dropped on any empty square, except pawns may not drop on the first or last
    rank. A drop may block a check or even deliver mate."""

    enabled = True

    def initial_hands(self, core) -> dict:
        return {WHITE: {}, BLACK: {}}

    def can_drop_on(self, core, state, letter, to, player) -> bool:
        if letter == "P":
            return 0 < to[1] < core.HEIGHT - 1   # no pawns on the back ranks
        return True

    def captured_to_hand(self, core, letter, was_promoted):
        if letter == "K":
            return None                          # never happens in legal play
        return "P" if was_promoted else letter


# --------------------------------------------------------------------------- #
# The shared game
# --------------------------------------------------------------------------- #
class ChessLike(Game):
    WIDTH = 8
    HEIGHT = 8
    PLY_CAP = 600
    PIECES: dict = {}
    HEAVY = ("P", "R", "Q")
    # Frontend piece-set hint: the renderer maps standard letters (KQRBNP) to real
    # chess glyphs instead of drawing the letter. Fairy pieces (A/C/M/…) and any
    # other letters fall back to the letter. A variant that reuses a STANDARD
    # letter for a non-standard piece can set ``PIECESET = None`` to opt out.
    PIECESET = "chess"
    # Per-letter icon overrides ({letter: icon-name-or-None}) checked before the
    # movement-derived mapping in ``_piece_icon``. Icon names must exist in
    # web/src/pieceImages.js (unknown names harmlessly fall back to the letter);
    # map a letter to None to suppress a derived icon.
    ICONS: dict = {}
    PAWN: PawnRules = None
    PROMOTION: PromotionRules = None
    CASTLING: Castling = NoCastling()
    DROPS: DropRules = NoDrops()

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

    def _drop_moves(self, state) -> list:
        """Legal "L@c,r" drops for the side to move (empty target, per-type rule,
        and -- only when in check -- the drop must leave the king safe)."""
        if not self.DROPS.enabled:
            return []
        player = state.to_move
        letters = [L for L, n in state.hands.get(player, {}).items() if n > 0]
        if not letters:
            return []
        in_chk = self.in_check(state.board, player)
        out = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                if (c, r) in state.board:
                    continue
                for L in letters:
                    if not self.DROPS.can_drop_on(self, state, L, (c, r), player):
                        continue
                    if in_chk:
                        b = dict(state.board)
                        b[(c, r)] = (player, L)
                        if self.in_check(b, player):
                            continue
                    out.append(f"{L}@{c},{r}")
        return out

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
        out.extend(self._drop_moves(state))
        return out

    # ---- draws / terminal ---------------------------------------------------
    def _insufficient(self, board) -> bool:
        if self.DROPS.enabled:
            return False          # captured material can always re-enter via a drop
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
                or state.reps.get(self._poskey_state(state), 0) >= 3)

    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        if self._legal(state):
            return False
        return not self._drop_moves(state)

    def returns(self, state) -> list:
        if self._draw(state) or not self.in_check(state.board, state.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # Material values for the MCTS rollout cutoff heuristic. Royal pieces score
    # 0 (always present); unknown variant pieces fall back to a minor's worth.
    PIECE_VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}

    def heuristic(self, state) -> list:
        """Material-balance eval squashed to (-1, 1), as MCTS payoffs [white, black].

        Used by ``MCTSBot`` when a random rollout is truncated before reaching a
        terminal position — a material count is a far better signal than the
        draw that ~400 random plies would otherwise drift to. Returns are in the
        same [white_payoff, black_payoff] convention as ``returns``.
        """
        vals = self.PIECE_VALUES
        bal = 0.0  # positive = WHITE (player 0) is ahead on material
        for (pl, t) in state.board.values():
            v = vals.get(t, 3.0)
            bal += v if pl == WHITE else -v
        if self.DROPS.enabled:                      # captured material in reserve counts
            for p, hand in state.hands.items():
                sign = 1.0 if p == WHITE else -1.0
                for t, n in hand.items():
                    bal += sign * vals.get(t, 3.0) * n
        score = math.tanh(bal / 8.0)
        return [score, -score]

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        if "@" in move:
            return self._apply_drop(state, move)
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)

        drops = self.DROPS.enabled
        hands = {p: dict(h) for p, h in state.hands.items()} if drops else {}
        promoted = set(state.promoted) if drops else None

        capture = to in state.board
        captured = state.board.get(to)        # (player, letter) or None
        captured_sq = to if capture else None
        ep_new = None
        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        elif t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                captured_sq = state.ep[1]
                captured = state.board.get(captured_sq)
                b.pop(captured_sq, None)
                capture = True
            else:
                ep_new = self.PAWN.ep_after(frm, to)

        promoting = t == "P" and bool(promo)
        if promoting:
            t = promo
        b[to] = (pl, t)

        if drops:
            if capture and captured is not None:
                gained = self.DROPS.captured_to_hand(self, captured[1],
                                                     captured_sq in state.promoted)
                if gained is not None:
                    hands.setdefault(pl, {})
                    hands[pl][gained] = hands[pl].get(gained, 0) + 1
            moved_promoted = frm in state.promoted
            promoted.discard(frm)
            promoted.discard(to)
            if captured_sq is not None:
                promoted.discard(captured_sq)
            if moved_promoted or promoting:
                promoted.add(to)
            promoted = frozenset(promoted)

        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        reset = capture or state.board[frm][1] == "P"
        key = self._poskey(b, 1 - pl, castling, ep_new, hands if drops else None)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps,
                      hands=hands, promoted=promoted if drops else frozenset())

    def _apply_drop(self, state, move):
        letter, cs = move.split("@")
        to = cell(cs)
        pl = state.to_move
        b = dict(state.board)
        b[to] = (pl, letter)
        hands = {p: dict(h) for p, h in state.hands.items()}
        hand = hands.setdefault(pl, {})
        hand[letter] = hand.get(letter, 0) - 1
        if hand[letter] <= 0:
            del hand[letter]
        key = self._poskey(b, 1 - pl, state.castling, None, hands)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=state.castling, ep=None,
                      halfmove=state.halfmove + 1, ply=state.ply + 1, reps=reps,
                      hands=hands, promoted=state.promoted)

    # ---- (de)serialize ------------------------------------------------------
    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None):
        board = self.setup_board()
        rights = self.CASTLING.initial_rights()
        hands = self.DROPS.initial_hands(self)
        st = CState(board=board, to_move=WHITE, castling=rights, ep=None, hands=hands)
        st.reps = {self._poskey_state(st): 1}
        return st

    def current_player(self, state) -> int:
        return state.to_move

    def setup_board(self) -> dict:
        raise NotImplementedError

    def _poskey_state(self, state) -> str:
        return self._poskey(state.board, state.to_move, state.castling, state.ep,
                            state.hands if self.DROPS.enabled else None)

    def _poskey(self, board, to_move, castling, ep, hands=None) -> str:
        et = ep[0] if ep else None
        rows = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                occ = board.get((c, r))
                rows.append("." if occ is None else "wb"[occ[0]] + occ[1])
        key = "|".join(rows) + f"#{to_move}#{''.join(sorted(castling))}#{et}"
        if hands:
            key += "#" + ";".join(
                f"{p}=" + ",".join(f"{L}{n}" for L, n in sorted(h.items()) if n > 0)
                for p, h in sorted(hands.items())
            )
        return key

    def serialize(self, state) -> dict:
        ep = state.ep
        d = {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "castling": "".join(sorted(state.castling)),
            "ep": f"{ep[0][0]},{ep[0][1]},{ep[1][0]},{ep[1][1]}" if ep else None,
            "halfmove": state.halfmove,
            "ply": state.ply,
            "reps": dict(state.reps),
        }
        if self.DROPS.enabled:
            d["hands"] = {str(p): {L: n for L, n in sorted(h.items()) if n > 0}
                          for p, h in sorted(state.hands.items())}
            d["promoted"] = [f"{c},{r}" for (c, r) in sorted(state.promoted)]
        return d

    def deserialize(self, d: dict):
        ep = None
        if d.get("ep"):
            a, b, c, e = (int(x) for x in d["ep"].split(","))
            ep = ((a, b), (c, e))
        hands = {int(p): {L: int(n) for L, n in h.items()}
                 for p, h in d.get("hands", {}).items()}
        promoted = frozenset(cell(s) for s in d.get("promoted", []))
        return CState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(d.get("castling", "")),
            ep=ep,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            hands=hands,
            promoted=promoted,
        )

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if "@" in move:
            letter, cs = move.split("@")
            c = cell(cs)
            return f"{letter}@{_FILES[c[0]]}{c[1] + 1}"
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

    def _piece_icon(self, t: str):
        """A movement-derived icon name for compound pieces that have no usable
        Unicode glyph, so the UI can draw a real piece image instead of the bare
        letter. Keyed on MOVEMENT (not the letter, which collides across variants:
        "M" is a Chancellor here but a Met/ferz in Makruk, an Amazon in Maharajah).
        chancellor = rook-rays+knight, archbishop = bishop-rays+knight,
        amazon = queen-rays+knight; pure leapers/steppers via ``_LEAPER_ICONS``.
        ``ICONS`` overrides per letter; standard-glyph letters (KQRBNP) are left
        to the Unicode pieceset (an icon would shadow the glyph in the UI)."""
        if t in self.ICONS:
            return self.ICONS[t]
        if self.PIECESET and t in "KQRBNP":
            return None
        slides, leaps = self.PIECES.get(t, ((), ()))
        sl, lp = set(slides), set(leaps)
        if sl:
            if not _KNIGHT_OFFS <= lp:
                return None
            ortho, diag = _ORTHO_DIRS <= sl, _DIAG_DIRS <= sl
            if ortho and diag:
                return "amazon"
            if ortho:
                return "chancellor"
            if diag:
                return "archbishop"
            return None
        return _LEAPER_ICONS.get(frozenset(lp))

    def render(self, state, perspective=None) -> dict:
        pieces = []
        for (c, r), (pl, t) in state.board.items():
            p = {"cell": f"{c},{r}", "owner": pl, "label": t}
            icon = self._piece_icon(t)
            if icon:
                p["icon"] = icon
            pieces.append(p)
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins (checkmate)"
        elif self.in_check(state.board, state.to_move):
            caption = f"{names[state.to_move]} to move (check)"
        else:
            caption = f"{names[state.to_move]} to move"
        spec = {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
        if self.PIECESET:
            spec["pieceset"] = self.PIECESET
        if self.DROPS.enabled:
            spec["reserve"] = {
                str(p): {L: n for L, n in sorted(h.items()) if n > 0}
                for p, h in sorted(state.hands.items())
            }
        return spec
