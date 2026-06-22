"""Shared core for Shogi-family games (9x9 Shogi, 5x5 Mini-Shogi, ...).

Shogi differs from Western chess enough to warrant its own core rather than
bending :mod:`agp.chesslike`:

* **Colour-relative movement** -- golds, silvers, knights, lances and pawns all
  move *forward*-relative, so every offset flips with the owner's direction.
* **Drops** -- a captured piece changes side and joins the capturer's hand; on a
  later turn it may be dropped (unpromoted) onto an empty square, subject to the
  two-pawns (nifu), last-rank and drop-mate (uchifuzume) rules.
* **Zone promotion** -- a move that touches the far three ranks may promote the
  piece (mandatory when it would otherwise have no move); promoted minors move
  like a gold, a promoted rook/bishop gains the king's other steps.

Player 0 = Sente (Black) starts at the bottom (row 0) and advances toward higher
rows. Board is a dict ``(col,row) -> (player, letter)`` with a parallel
``promoted`` set of squares. Moves are the platform's clickable cell strings:
``"fc,fr>tc,tr"`` (optionally ``"=+"`` to promote) and ``"L@c,r"`` (a drop).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .game import Game

BLACK, WHITE = 0, 1

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
KING = ORTHO + DIAG
GOLD = [(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0), (0, -1)]
SILVER = [(-1, 1), (0, 1), (1, 1), (-1, -1), (1, -1)]
KNIGHT = [(-1, 2), (1, 2)]
PAWN = [(0, 1)]
LANCE = [(0, 1)]            # a forward ray (slide)

# Movement in the *forward frame* (Black advancing +row): (slide_dirs, leap_offsets)
GOLDISH = ([], GOLD)
BASE_MOVE = {
    "P": ([], PAWN),
    "L": (LANCE, []),
    "N": ([], KNIGHT),
    "S": ([], SILVER),
    "G": ([], GOLD),
    "K": ([], KING),
    "R": (ORTHO, []),
    "B": (DIAG, []),
}
PROMO_MOVE = {
    "P": GOLDISH, "L": GOLDISH, "N": GOLDISH, "S": GOLDISH,
    "R": (ORTHO, DIAG),        # Dragon King: rook + diagonal king steps
    "B": (DIAG, ORTHO),        # Dragon Horse: bishop + orthogonal king steps
}
CAN_PROMOTE = ("P", "L", "N", "S", "R", "B")
DROP_TYPES = ("P", "L", "N", "S", "G", "B", "R")   # king is never in hand


def cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _movement(letter, promoted):
    return PROMO_MOVE[letter] if promoted else BASE_MOVE[letter]


@dataclass
class SState:
    board: dict = field(default_factory=dict)          # (c,r) -> (player, letter)
    promoted: frozenset = field(default_factory=frozenset)
    hands: dict = field(default_factory=dict)          # player -> {letter: count}
    to_move: int = BLACK
    ply: int = 0
    reps: dict = field(default_factory=dict)


class ShogiLike(Game):
    WIDTH = 9
    HEIGHT = 9
    ZONE = 3              # number of far ranks forming the promotion zone
    PLY_CAP = 400
    LABELS = {}           # optional pretty labels per (letter); default uses the letter

    def __init__(self):
        # Per-colour reverse-attack maps: offset/dir -> set of (letter, promoted)
        # kinds of that colour that attack across it. Built once; colour only
        # flips the forward sign, so we precompute both.
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        kinds = [(L, False) for L in BASE_MOVE] + [(L, True) for L in PROMO_MOVE]
        for pl in (BLACK, WHITE):
            fwd = 1 if pl == BLACK else -1
            for (letter, prom) in kinds:
                slides, leaps = _movement(letter, prom)
                for (dc, dr) in leaps:
                    off = (dc, dr * fwd)
                    self._leap_att[pl].setdefault((-off[0], -off[1]), set()).add((letter, prom))
                for (dc, dr) in slides:
                    d = (dc, dr * fwd)
                    self._slide_att[pl].setdefault((-d[0], -d[1]), set()).add((letter, prom))

    # ---- geometry ----------------------------------------------------------
    def on(self, c, r) -> bool:
        return 0 <= c < self.WIDTH and 0 <= r < self.HEIGHT

    def _fwd(self, pl) -> int:
        return 1 if pl == BLACK else -1

    def in_zone(self, pl, r) -> bool:
        return r >= self.HEIGHT - self.ZONE if pl == BLACK else r < self.ZONE

    def _last_rank(self, pl, r) -> bool:
        return r == (self.HEIGHT - 1 if pl == BLACK else 0)

    def _last_two(self, pl, r) -> bool:
        return r >= self.HEIGHT - 2 if pl == BLACK else r <= 1

    # ---- attacks / check ---------------------------------------------------
    def attacked(self, board, promoted, sq, by) -> bool:
        c, r = sq
        for (dc, dr), kinds in self._leap_att[by].items():
            pc = board.get((c + dc, r + dr))
            if pc is not None and pc[0] == by and (pc[1], (c + dc, r + dr) in promoted) in kinds:
                return True
        for (dc, dr), kinds in self._slide_att[by].items():
            cc, rr = c + dc, r + dr
            while self.on(cc, rr):
                pc = board.get((cc, rr))
                if pc is not None:
                    if pc[0] == by and (pc[1], (cc, rr) in promoted) in kinds:
                        return True
                    break
                cc += dc
                rr += dr
        return False

    def _king(self, board, pl):
        for sq, (p, t) in board.items():
            if p == pl and t == "K":
                return sq
        return None

    def in_check(self, board, promoted, pl) -> bool:
        k = self._king(board, pl)
        return k is not None and self.attacked(board, promoted, k, 1 - pl)

    # ---- pseudo-moves ------------------------------------------------------
    def _piece_targets(self, board, sq, pl, letter, promoted):
        c, r = sq
        fwd = self._fwd(pl)
        slides, leaps = _movement(letter, promoted)
        for (dc, dr) in leaps:
            t = (c + dc, r + dr * fwd)
            if self.on(*t) and (board.get(t) or (None,))[0] != pl:
                yield t
        for (dc, dr) in slides:
            step_r = dr * fwd
            cc, rr = c + dc, r + step_r
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is None:
                    yield (cc, rr)
                else:
                    if occ[0] != pl:
                        yield (cc, rr)
                    break
                cc += dc
                rr += step_r

    def _board_after(self, state, frm, to, promote):
        """Resulting (board, promoted) after a board move -- for king-safety."""
        b = dict(state.board)
        prom = set(state.promoted)
        pl, t = b.pop(frm)
        moved_prom = frm in state.promoted
        prom.discard(frm)
        prom.discard(to)
        if promote or moved_prom:
            prom.add(to)
        b[to] = (pl, t)
        return b, prom

    def _legal_board_moves(self, state):
        """Yield (frm, to, promote_bool) legal non-drop moves."""
        pl = state.to_move
        for sq, (p, t) in list(state.board.items()):
            if p != pl:
                continue
            prom = sq in state.promoted
            for to in self._piece_targets(state.board, sq, pl, t, prom):
                opts = self._promotion_options(t, prom, sq[1], to[1], pl)
                for promote in opts:
                    nb, npr = self._board_after(state, sq, to, promote)
                    if not self.in_check(nb, npr, pl):
                        yield sq, to, promote

    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted or letter not in CAN_PROMOTE:
            return [False]
        if not (self.in_zone(pl, frm_r) or self.in_zone(pl, to_r)):
            return [False]
        # mandatory when the piece would otherwise be stuck
        if letter == "P" or letter == "L":
            if self._last_rank(pl, to_r):
                return [True]
        if letter == "N" and self._last_two(pl, to_r):
            return [True]
        return [False, True]

    # ---- drops -------------------------------------------------------------
    def _drop_moves(self, state):
        pl = state.to_move
        letters = [L for L, n in state.hands.get(pl, {}).items() if n > 0]
        if not letters:
            return []
        in_chk = self.in_check(state.board, state.promoted, pl)
        # files already holding an unpromoted own pawn (for nifu)
        pawn_files = {c for (c, r), (p, t) in state.board.items()
                      if p == pl and t == "P" and (c, r) not in state.promoted}
        out = []
        for c in range(self.WIDTH):
            for r in range(self.HEIGHT):
                if (c, r) in state.board:
                    continue
                for L in letters:
                    if not self._drop_ok(state, pl, L, c, r, pawn_files, in_chk):
                        continue
                    out.append(f"{L}@{c},{r}")
        return out

    def _drop_ok(self, state, pl, L, c, r, pawn_files, in_chk):
        if L == "P":
            if self._last_rank(pl, r) or c in pawn_files:
                return False
        elif L == "L":
            if self._last_rank(pl, r):
                return False
        elif L == "N":
            if self._last_two(pl, r):
                return False
        # king safety (placing a piece can only block, never expose)
        if in_chk:
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            if self.in_check(b, state.promoted, pl):
                return False
        # uchifuzume: a pawn drop may not deliver immediate checkmate
        if L == "P":
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            if self.attacked(b, state.promoted, self._king(b, 1 - pl), pl):
                if self._is_mated(b, state.promoted, state.hands, 1 - pl):
                    return False
        return True

    def _is_mated(self, board, promoted, hands, pl):
        """Has player `pl` (to move) no legal reply? (used only for uchifuzume)."""
        probe = SState(board=board, promoted=promoted, hands=hands, to_move=pl)
        for _ in self._legal_board_moves(probe):
            return False
        return not self._drop_moves(probe)

    # ---- Game interface ----------------------------------------------------
    @property
    def num_players(self) -> int:
        return 2

    def current_player(self, state) -> int:
        return state.to_move

    def setup_board(self):
        raise NotImplementedError

    def initial_state(self, options=None, rng=None):
        board, promoted = self.setup_board()
        st = SState(board=board, promoted=frozenset(promoted),
                    hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
        st.reps = {self._poskey(st): 1}
        return st

    def legal_moves(self, state):
        if self._draw(state):
            return []
        out = []
        for frm, to, promote in self._legal_board_moves(state):
            m = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
            out.append(m + "=+" if promote else m)
        out.extend(self._drop_moves(state))
        return out

    def _has_move(self, state) -> bool:
        for _ in self._legal_board_moves(state):
            return True
        return bool(self._drop_moves(state))

    def _draw(self, state) -> bool:
        return state.ply >= self.PLY_CAP or state.reps.get(self._poskey(state), 0) >= 4

    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        return not self._has_move(state)

    def returns(self, state):
        if self._draw(state):
            return [0.0, 0.0]
        # no legal move: the side to move is mated and loses
        return [-1.0, 1.0] if state.to_move == BLACK else [1.0, -1.0]

    def apply_move(self, state, move, rng=None):
        if "@" in move:
            return self._apply_drop(state, move)
        promote = move.endswith("=+")
        if promote:
            move = move[:-2]
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)
        prom = set(state.promoted)
        hands = {p: dict(h) for p, h in state.hands.items()}

        captured = state.board.get(to)
        if captured is not None:
            gained = captured[1]
            if to in state.promoted:               # captured a promoted piece -> base type
                pass                                 # letter already the base letter
            hands.setdefault(pl, {})
            hands[pl][gained] = hands[pl].get(gained, 0) + 1

        moved_prom = frm in state.promoted
        prom.discard(frm)
        prom.discard(to)
        if promote or moved_prom:
            prom.add(to)
        b[to] = (pl, t)

        return self._finish(b, prom, hands, 1 - pl, state)

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
        return self._finish(b, set(state.promoted), hands, 1 - pl, state)

    def _finish(self, board, promoted, hands, to_move, state):
        promoted = frozenset(promoted)
        st = SState(board=board, promoted=promoted, hands=hands, to_move=to_move,
                    ply=state.ply + 1, reps=dict(state.reps))
        key = self._poskey(st)
        st.reps[key] = st.reps.get(key, 0) + 1
        return st

    # ---- keys / (de)serialise ---------------------------------------------
    def _poskey(self, state) -> str:
        rows = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                occ = state.board.get((c, r))
                if occ is None:
                    rows.append(".")
                else:
                    tag = ("+" if (c, r) in state.promoted else "") + occ[1]
                    rows.append("bw"[occ[0]] + tag)
        h = ";".join(
            f"{p}=" + ",".join(f"{L}{n}" for L, n in sorted(hd.items()) if n > 0)
            for p, hd in sorted(state.hands.items())
        )
        return "|".join(rows) + f"#{state.to_move}#{h}"

    def serialize(self, state) -> dict:
        return {
            "board": {f"{c},{r}": [p, t] for (c, r), (p, t) in state.board.items()},
            "promoted": [f"{c},{r}" for (c, r) in sorted(state.promoted)],
            "hands": {str(p): {L: n for L, n in sorted(hd.items()) if n > 0}
                      for p, hd in sorted(state.hands.items())},
            "to_move": state.to_move,
            "ply": state.ply,
            "reps": dict(state.reps),
        }

    def deserialize(self, d) -> SState:
        return SState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            promoted=frozenset(cell(s) for s in d.get("promoted", [])),
            hands={int(p): {L: int(n) for L, n in hd.items()}
                   for p, hd in d.get("hands", {}).items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
        )

    # ---- presentation ------------------------------------------------------
    def _label(self, letter, promoted) -> str:
        if promoted:
            return self.LABELS.get("+" + letter, "+" + letter)
        return self.LABELS.get(letter, letter)

    def describe_move(self, state, move) -> str:
        if "@" in move:
            letter, cs = move.split("@")
            c = cell(cs)
            return f"{letter}*{c[0]},{c[1]}"
        promote = move.endswith("=+")
        raw = move[:-2] if promote else move
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        cap = "x" if to in state.board else "-"
        tag = self._label(t, frm in state.promoted)
        return f"{tag}{fs}{cap}{ts}" + ("+" if promote else "")

    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": p,
             "label": self._label(t, (c, r) in state.promoted)}
            for (c, r), (p, t) in state.board.items()
        ]
        names = {BLACK: "Sente (Black)", WHITE: "Gote (White)"}
        if self.is_terminal(state):
            ret = self.returns(state)
            caption = "Draw" if ret == [0.0, 0.0] else f"{names[0 if ret[0] > 0 else 1]} wins"
        elif self.in_check(state.board, state.promoted, state.to_move):
            caption = f"{names[state.to_move]} to move (check)"
        else:
            caption = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
            "reserve": {str(p): {L: n for L, n in sorted(hd.items()) if n > 0}
                        for p, hd in sorted(state.hands.items())},
        }
