"""Wildebeest Chess (R. Wayne Schmittberger, 1987), 11x10, on the shared core.

An 11-file by 10-rank board adding two leapers:

* the **Camel (C)** -- a (1,3) leaper (an "elongated knight": it jumps in a 2x4
  rectangle, so it is colour-bound like a bishop);
* the **Wildebeest (W)** -- a (1,2)+(1,3) leaper, i.e. it moves as either a
  knight or a camel.

Each side has 1 King, 1 Queen, 1 Wildebeest, 2 Rooks, 2 Knights, 2 Camels,
2 Bishops and 11 Pawns.  White = player 0.

This module keeps the ChessLike machinery for the leaper/slider pieces, check
detection, mate/draw handling, (de)serialisation and rendering, but supplies its
own faithful **multi-step pawn** (advance any distance while the destination
stays in the mover's own half) and **multi-square en passant**. Castling is
**omitted** (NoCastling): Wildebeest's authentic castling rule on an 11-wide
board is poorly/inconsistently sourced, so rather than ship a wrong one we leave
it out — consistent with the platform's other wide variants (Grand, Courier).

See ``rules.md`` for the full, sourced ruleset and the documented choices.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, PawnRules, PromotionRules, NoCastling,
    CState, cell, ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# Camel: (1,3) leaper -- all eight sign/axis combinations of {1,3}.
CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]
WILDEBEEST = KNIGHT + CAMEL


# --------------------------------------------------------------------------- #
# Multi-step pawn
# --------------------------------------------------------------------------- #
class WildebeestPawn(PawnRules):
    """A pawn advances orthogonally any number of empty squares as long as the
    destination stays in the mover's *own half* of the board; it captures one
    square diagonally forward (and en passant).  En passant is multi-square: a
    pawn that advanced N squares may be captured on any square it skipped over
    on the very next move.

    ``mid`` is the number of ranks in each half (HEIGHT // 2).  White's half is
    rows ``0 .. mid-1``; Black's is ``mid .. HEIGHT-1``.
    """

    def __init__(self, mid: int):
        # white_start / black_start are unused (any-distance), but the base
        # class wants them; double() is irrelevant here.
        super().__init__(white_start=1, black_start=mid * 2 - 2, double=False)
        self.mid = mid

    def in_own_half(self, player: int, r: int) -> bool:
        return r < self.mid if player == WHITE else r >= self.mid

    def pseudo(self, core, board, c, r, player, ep_target):
        fwd = self.fwd(player)
        # Straight advance. A pawn may always step one square forward (if empty);
        # while in its own half it may continue for as many empty squares as keep
        # the destination inside its own half (so a multi-square leap never
        # crosses the midline -- past the midline it is one square at a time).
        one = (c, r + fwd)
        if core.on(*one) and one not in board:
            yield (c, r), one
            if self.in_own_half(player, r):
                rr = r + 2 * fwd
                while core.on(c, rr) and (c, rr) not in board and self.in_own_half(player, rr):
                    yield (c, r), (c, rr)
                    rr += fwd
        # diagonal captures (incl. en passant on any skipped square)
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if (occ is not None and occ[0] != player) or (ep_target and t in ep_target):
                yield (c, r), t

    def ep_after(self, frm, to):
        """For a multi-square advance, the e.p. record is (skipped_squares,
        moved_pawn): an enemy may land on any skipped square and remove the
        pawn.  Returns ``(frozenset(skipped), to)`` or ``None``."""
        dist = abs(to[1] - frm[1])
        if dist >= 2 and to[0] == frm[0]:
            step = 1 if to[1] > frm[1] else -1
            skipped = frozenset((frm[0], frm[1] + step * k) for k in range(1, dist))
            return (skipped, to)
        return None

    def attacks(self, core, board, c, r, by) -> bool:
        pr = r - self.fwd(by)
        return any(board.get((c + dc, pr)) == (by, "P") for dc in (-1, 1))


# --------------------------------------------------------------------------- #
# Promotion: queen or wildebeest only, mandatory on the final rank
# --------------------------------------------------------------------------- #
class WildebeestPromotion(PromotionRules):
    TARGETS = ("Q", "W")

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        last = (to[1] == core.HEIGHT - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK)
        return list(self.TARGETS) if last else [None]


# Back-rank piece order (files a..k), per the Schmittberger / chessvariants.com
# and Wikipedia setup.  The position is point-symmetric (180-degree rotation).
WHITE_BACK = ["R", "N", "B", "B", "Q", "K", "W", "C", "C", "N", "R"]
BLACK_BACK = ["R", "N", "C", "C", "W", "K", "Q", "B", "B", "N", "R"]


class WildebeestChess(ChessLike):
    uid = "wildebeest_chess"
    name = "Wildebeest Chess"

    WIDTH = 11
    HEIGHT = 10
    PLY_CAP = 800
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "C": ([], CAMEL), "W": ([], WILDEBEEST),
        "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q", "C", "W")          # mating material besides lone minor
    PAWN = WildebeestPawn(mid=HEIGHT // 2)
    PROMOTION = WildebeestPromotion()
    CASTLING = NoCastling()   # authentic Wildebeest castling is uncertain on 11-wide; omitted (documented)

    def __init__(self, options=None):
        super().__init__()
        opts = options or {}
        # "stalemate": "draw" (task default) or "win" (authentic Schmittberger).
        self.stalemate_wins = (opts.get("stalemate", "draw") == "win")

    # ------ option plumbing: remember the option on the state via initial_state
    def initial_state(self, options=None, rng=None):
        if options:
            self.stalemate_wins = (options.get("stalemate", "draw") == "win")
        return super().initial_state(options=options, rng=rng)

    def setup_board(self) -> dict:
        b = {}
        for i, t in enumerate(WHITE_BACK):
            b[(i, 0)] = (WHITE, t)
        for i, t in enumerate(BLACK_BACK):
            b[(i, self.HEIGHT - 1)] = (BLACK, t)
        for c in range(self.WIDTH):
            b[(c, 1)] = (WHITE, "P")
            b[(c, self.HEIGHT - 2)] = (BLACK, "P")
        return b

    # ------ en passant: ep is stored as (skipped_squares_frozenset, captured) #
    # The base StandardPawn used a single square; our WildebeestPawn.ep_after
    # returns a frozenset of skipped squares.  We override the few spots that
    # interpret the ep tuple.

    def _ep_targets(self, state):
        return state.ep[0] if state.ep else None    # frozenset or None

    def _pseudo(self, state):
        # identical to the base, but the pawn branch needs the *set* of ep
        # target squares (the base passes a single square).
        board, player = state.board, state.to_move
        ep_target = self._ep_targets(state)
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
        if t == "P" and ep is not None and to in ep[0] and to not in board:
            b.pop(ep[1], None)
        if t == "P" and (to[1] == self.HEIGHT - 1 and pl == WHITE or to[1] == 0 and pl == BLACK):
            t = self.PROMOTION.safety_piece()
        b[to] = (pl, t)
        return b

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
            if state.ep is not None and to in state.ep[0] and to not in state.board:
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

    # ------ terminal / returns: stalemate may be a win (option) --------------
    def returns(self, state) -> list:
        if self._draw(state):
            return [0.0, 0.0]
        # not a draw and no legal move: either checkmate, or stalemate
        in_check = self.in_check(state.board, state.to_move)
        if not in_check and not self.stalemate_wins:
            return [0.0, 0.0]
        # the side to move is mated / stalemated and therefore loses
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # ------ en passant (de)serialisation: ep[0] is a frozenset of squares ----
    def _poskey(self, board, to_move, castling, ep, hands=None) -> str:
        ets = tuple(sorted(ep[0])) if ep else None
        rows = []
        for r in range(self.HEIGHT):
            for c in range(self.WIDTH):
                occ = board.get((c, r))
                rows.append("." if occ is None else "wb"[occ[0]] + occ[1])
        return "|".join(rows) + f"#{to_move}#{''.join(sorted(castling))}#{ets}"

    def serialize(self, state) -> dict:
        ep = state.ep
        ep_ser = None
        if ep:
            skipped = ";".join(f"{c},{r}" for (c, r) in sorted(ep[0]))
            ep_ser = f"{skipped}|{ep[1][0]},{ep[1][1]}"
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "castling": "".join(sorted(state.castling)),
            "ep": ep_ser,
            "halfmove": state.halfmove,
            "ply": state.ply,
            "reps": dict(state.reps),
            "stalemate_wins": self.stalemate_wins,
        }

    def deserialize(self, d: dict):
        ep = None
        if d.get("ep"):
            skipped_s, cap_s = d["ep"].split("|")
            skipped = frozenset(cell(s) for s in skipped_s.split(";")) if skipped_s else frozenset()
            ep = (skipped, cell(cap_s))
        if "stalemate_wins" in d:
            self.stalemate_wins = bool(d["stalemate_wins"])
        return CState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(d.get("castling", "")),
            ep=ep,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
        )
