"""Antichess (Losing Chess / Giveaway), the lichess variant.

The goal is INVERTED: you win by losing all your pieces, or by being the player
who has no legal move on their turn. Rules vs standard chess:

* **The king is not royal.** There is no check, no checkmate and no castling; the
  king is an ordinary one-step piece that can be captured, and a pawn may promote
  to a king (promotion targets are Q/R/B/N/K).
* **Capturing is compulsory.** If the side to move has any capture available it
  *must* make a capture (it may choose which); only when no capture exists may it
  play a non-capturing move. En passant counts as a capture and so is forced when
  no other capture is available.
* **Winning.** A player wins as soon as they have no pieces left, or when, on
  their turn, they have no legal move (so being "stalemated" is a WIN here).

This does not fit ``agp.chesslike``'s royal-king model, so it is a custom
``agp.game.Game``. Move geometry is borrowed from ordinary chess (sliders +
leapers + pawns) but there is no king-safety / check filtering. White = player 0
advances toward higher rows. Moves use the platform's clickable cell-path strings
``"fc,fr>tc,tr"`` with an optional ``"=Q/R/B/N/K"`` promotion suffix.

Termination is guaranteed by the fifty-move rule, threefold repetition and a hard
ply cap (those end the game in a draw); under normal play the forced-capture rule
makes games end quickly by annihilation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL8 = ORTHO + DIAG
KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]

# Slider directions / leaper offsets per piece. The king is just a one-step
# all-directions leaper (non-royal here).
PIECES = {
    "R": (ORTHO, []),
    "B": (DIAG, []),
    "Q": (ALL8, []),
    "N": ([], KNIGHT),
    "K": ([], ALL8),
}

PROMOTION_TARGETS = ("Q", "R", "B", "N", "K")

WIDTH = HEIGHT = 8
PLY_CAP = 600

_FILES = "abcdefgh"
BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


def cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class AState:
    board: dict = field(default_factory=dict)        # (c, r) -> (player, letter)
    to_move: int = WHITE
    ep: Optional[tuple] = None                         # ((tc,tr),(cc,cr)) or None
    halfmove: int = 0
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: Optional[int] = None                       # set when a side has no pieces


class Antichess(Game):
    uid = "antichess"
    name = "Antichess"

    WIDTH = WIDTH
    HEIGHT = HEIGHT
    PLY_CAP = PLY_CAP

    # ---- geometry ----------------------------------------------------------
    def on(self, c, r) -> bool:
        return 0 <= c < self.WIDTH and 0 <= r < self.HEIGHT

    # ---- pseudo-legal move generation --------------------------------------
    # Yields (frm, to, is_capture). No king-safety filtering: there is no check.
    def _pseudo(self, board, player, ep):
        ep_target = ep[0] if ep else None
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "P":
                yield from self._pawn_moves(board, c, r, player, ep_target)
                continue
            slides, leaps = PIECES[t]
            for dc, dr in leaps:
                tc, tr = c + dc, r + dr
                if not self.on(tc, tr):
                    continue
                occ = board.get((tc, tr))
                if occ is None:
                    yield (c, r), (tc, tr), False
                elif occ[0] != player:
                    yield (c, r), (tc, tr), True
            for dc, dr in slides:
                cc, rr = c + dc, r + dr
                while self.on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is None:
                        yield (c, r), (cc, rr), False
                    else:
                        if occ[0] != player:
                            yield (c, r), (cc, rr), True
                        break
                    cc += dc
                    rr += dr

    def _pawn_moves(self, board, c, r, player, ep_target):
        fwd = 1 if player == WHITE else -1
        start = 1 if player == WHITE else self.HEIGHT - 2
        # straight, non-capturing
        if self.on(c, r + fwd) and (c, r + fwd) not in board:
            yield (c, r), (c, r + fwd), False
            if r == start and (c, r + 2 * fwd) not in board:
                yield (c, r), (c, r + 2 * fwd), False
        # diagonal captures (incl. en passant, which is a capture)
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not self.on(*t):
                continue
            occ = board.get(t)
            if occ is not None and occ[0] != player:
                yield (c, r), t, True
            elif t == ep_target:
                yield (c, r), t, True

    def _ep_after(self, frm, to):
        if abs(to[1] - frm[1]) == 2:
            mid = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
            return (mid, to)
        return None

    # ---- legal moves (the crux: forced captures) ---------------------------
    def _legal_pairs(self, state):
        """Return (pairs, any_capture). pairs = [(frm,to,is_capture)]. If any
        capture exists, only captures are returned (compulsory capture)."""
        all_moves = list(self._pseudo(state.board, state.to_move, state.ep))
        caps = [m for m in all_moves if m[2]]
        if caps:
            return caps, True
        return all_moves, False

    def legal_moves(self, state) -> list:
        if self.is_terminal(state):
            return []
        pairs, _ = self._legal_pairs(state)
        out = []
        for frm, to, _cap in pairs:
            base = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
            if state.board[frm][1] == "P" and self._is_last_rank(to, state.to_move):
                for ch in PROMOTION_TARGETS:
                    out.append(base + "=" + ch)
            else:
                out.append(base)
        return out

    def _is_last_rank(self, to, player) -> bool:
        return (player == WHITE and to[1] == self.HEIGHT - 1) or (
            player == BLACK and to[1] == 0)

    # ---- terminal / returns ------------------------------------------------
    def _no_pieces(self, board, player) -> bool:
        return not any(pl == player for (pl, _t) in board.values())

    def _draw(self, state) -> bool:
        if state.halfmove >= 100 or state.ply >= self.PLY_CAP:
            return True
        key = self._poskey(state.board, state.to_move, state.ep)
        return state.reps.get(key, 0) >= 3

    def is_terminal(self, state) -> bool:
        if state.winner is not None:
            return True
        if self._draw(state):
            return True
        # The player to move with no legal move WINS (stalemate is a win); either
        # way the game is over.
        pairs, _ = self._legal_pairs(state)
        return len(pairs) == 0

    def returns(self, state) -> list:
        # Win-by-no-pieces: the side that lost all its pieces wins.
        if state.winner is not None:
            return [1.0, -1.0] if state.winner == WHITE else [-1.0, 1.0]
        if self._draw(state):
            return [0.0, 0.0]
        # The side to move has no legal move -> that side WINS.
        pairs, _ = self._legal_pairs(state)
        if len(pairs) == 0:
            return [1.0, -1.0] if state.to_move == WHITE else [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- apply -------------------------------------------------------------
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

        if t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                b.pop(state.ep[1], None)
                capture = True
            else:
                ep_new = self._ep_after(frm, to)
            if promo and self._is_last_rank(to, pl):
                t = promo
        b[to] = (pl, t)

        # win-by-annihilation: did the *mover* just give away their last piece?
        winner = None
        if self._no_pieces(b, pl):
            winner = pl
        elif self._no_pieces(b, 1 - pl):
            # mover captured the opponent's last piece: opponent wins (they have
            # no pieces). This is a loss for the mover.
            winner = 1 - pl

        reset = capture or state.board[frm][1] == "P"
        key = self._poskey(b, 1 - pl, ep_new)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return AState(board=b, to_move=1 - pl, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps, winner=winner)

    # ---- identity / setup --------------------------------------------------
    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None):
        board = {}
        for c in range(self.WIDTH):
            board[(c, 0)] = (WHITE, BACK_RANK[c])
            board[(c, 1)] = (WHITE, "P")
            board[(c, self.HEIGHT - 2)] = (BLACK, "P")
            board[(c, self.HEIGHT - 1)] = (BLACK, BACK_RANK[c])
        return AState(board=board, to_move=WHITE, ep=None,
                      reps={self._poskey(board, WHITE, None): 1})

    def current_player(self, state) -> int:
        return state.to_move

    # ---- (de)serialize -----------------------------------------------------
    def _poskey(self, board, to_move, ep) -> str:
        et = ep[0] if ep else None
        rows = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                occ = board.get((c, r))
                rows.append("." if occ is None else "wb"[occ[0]] + occ[1])
        return "|".join(rows) + f"#{to_move}#{et}"

    def serialize(self, state) -> dict:
        ep = state.ep
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "ep": f"{ep[0][0]},{ep[0][1]},{ep[1][0]},{ep[1][1]}" if ep else None,
            "halfmove": state.halfmove,
            "ply": state.ply,
            "reps": dict(state.reps),
            "winner": state.winner,
        }

    def deserialize(self, d: dict):
        ep = None
        if d.get("ep"):
            a, b, c, e = (int(x) for x in d["ep"].split(","))
            ep = ((a, b), (c, e))
        return AState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ep=ep,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            winner=d.get("winner"),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move) -> str:
        raw, promo = (move.split("=") + [None])[:2]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        capture = to in state.board or (
            t == "P" and state.ep is not None and to == state.ep[0])
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
            if ret == [0.0, 0.0]:
                caption = "Draw"
            else:
                caption = f"{names[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
