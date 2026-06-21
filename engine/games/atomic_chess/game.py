"""Atomic Chess (the lichess variant), built on the shared chess-like core.

Pieces move exactly as in standard chess (castling, en passant, double-step and
promotion all included), but **every capture triggers an explosion**: the
capturing piece, the captured piece, and every *non-pawn* piece on the eight
squares orthogonally and diagonally adjacent to the capture square are removed.
Pawns adjacent to a blast survive; only the pawn actually captured (on the target
square, or the en-passant pawn) is removed.

Consequences, all faithful to lichess / python-chess ``AtomicBoard``:

* You may **not** play a move that would blow up your *own* king (so a capture
  whose explosion would catch your king is illegal).
* You **win** the instant the enemy king is exploded (or captured). Because a
  king capture would always blow up the capturing king too, a king may never
  capture.
* Kings may stand on adjacent squares: while the two kings are adjacent **no
  check is in force** (neither king can be captured, so neither is attacked),
  exactly mirroring ``AtomicBoard``'s "connected kings" rule.
* A side to move may ignore being in check **if** its move explodes the enemy
  king (winning outright). Otherwise it must leave its own king safe, as usual.
* No castling out of, through, or into check (squares adjacent to the enemy king
  count as safe for castling, again per ``AtomicBoard``).

White = player 0. Moves use the platform's clickable cell-path notation; castling
is the king's two-square move and promotion appends ``=Q/R/B/N``.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, cell,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

# the 8 king-adjacency offsets (the explosion radius)
ADJ8 = ALL8


class AtomicChess(ChessLike):
    uid = "atomic_chess"
    name = "Atomic Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # --------------------------------------------------------------------- #
    # Explosion-aware move resolution
    # --------------------------------------------------------------------- #
    def _resolve(self, board, frm, to, ep, promo=None):
        """Return the new board dict after playing frm->to (with optional
        promotion), applying the atomic explosion on any capture. Pure: does not
        mutate ``board``. Castling is handled by the caller (it never captures)."""
        b = dict(board)
        pl, t = b.pop(frm)

        captured_sq = None
        if to in board:                       # ordinary capture (any piece)
            captured_sq = to
        elif t == "P" and ep is not None and to == ep[0]:
            captured_sq = ep[1]               # en-passant: remove the passed pawn

        if t == "P" and promo:
            t = promo

        if captured_sq is None:
            # quiet move (incl. castling handled elsewhere): just relocate
            b[to] = (pl, t)
            return b, False

        # --- a capture happened: explode ---
        b.pop(captured_sq, None)              # remove the captured piece
        # the capturing piece is destroyed too (it never lands on `to`)
        for dc, dr in ADJ8:                    # remove adjacent NON-pawn pieces
            sq = (to[0] + dc, to[1] + dr)
            occ = b.get(sq)
            if occ is not None and occ[1] != "P":
                b.pop(sq, None)
        return b, True

    def _king_alive(self, board, player) -> bool:
        return self._king(board, player) is not None

    def _kings_adjacent(self, board) -> bool:
        wk = self._king(board, WHITE)
        bk = self._king(board, BLACK)
        if wk is None or bk is None:
            return False
        return max(abs(wk[0] - bk[0]), abs(wk[1] - bk[1])) == 1

    def in_check(self, board, player) -> bool:
        """Atomic check: no check while the kings are connected (adjacent),
        because no piece may capture a king without exploding its own."""
        if self._kings_adjacent(board):
            return False
        return super().in_check(board, player)

    # --------------------------------------------------------------------- #
    # Legality: own king must survive; you may ignore check iff you explode the
    # enemy king this move.
    # --------------------------------------------------------------------- #
    def _legal(self, state):
        moves = []
        board, player = state.board, state.to_move
        enemy = 1 - player
        for frm, to in self._pseudo(state):
            promo = self.PROMOTION.safety_piece() if board[frm][1] == "P" else None
            nb, _cap = self._resolve(board, frm, to, state.ep, promo)
            if not self._king_alive(nb, player):
                continue                       # never blow up your own king
            if not self._king_alive(nb, enemy):
                moves.append((frm, to))        # exploded enemy king -> always legal (win)
                continue
            if not self.in_check(nb, player):
                moves.append((frm, to))
        moves.extend(self.CASTLING.moves(self, state))
        return moves

    # --------------------------------------------------------------------- #
    # Terminal / result.  A side with no king has lost; a side whose enemy king
    # is gone has won.  Otherwise: no legal moves while not in check = stalemate
    # (draw); no legal moves while in check = checkmate.
    # --------------------------------------------------------------------- #
    def _king_gone_result(self, state):
        """Return a returns() list if a king is already off the board, else None."""
        w = self._king_alive(state.board, WHITE)
        b = self._king_alive(state.board, BLACK)
        if w and b:
            return None
        if not w and not b:
            return [0.0, 0.0]                  # should never arise, be safe
        return [1.0, -1.0] if w else [-1.0, 1.0]

    def is_terminal(self, state) -> bool:
        if self._king_gone_result(state) is not None:
            return True
        return self._draw(state) or len(self._legal(state)) == 0

    def returns(self, state) -> list:
        kg = self._king_gone_result(state)
        if kg is not None:
            return kg
        if self._draw(state) or not self.in_check(state.board, state.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    def legal_moves(self, state) -> list:
        if self._king_gone_result(state) is not None:
            return []
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

    # --------------------------------------------------------------------- #
    # Apply: identical bookkeeping to ChessLike, but the board transform uses
    # the explosion resolver.
    # --------------------------------------------------------------------- #
    def apply_move(self, state, move, rng=None):
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]

        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            # castling never captures -> no explosion
            b = dict(state.board)
            b[to] = b.pop(frm)
            b[rook[1]] = b.pop(rook[0])
            capture = False
            ep_new = None
        else:
            ep_new = None
            if t == "P" and not (to in state.board) and not (
                    state.ep is not None and to == state.ep[0]):
                ep_new = self.PAWN.ep_after(frm, to)
            b, capture = self._resolve(state.board, frm, to, state.ep, promo)

        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        # an explosion can also destroy rooks/kings on their home squares ->
        # recompute castling rights against pieces actually still present.
        castling = frozenset(
            f for f in castling if self._castle_flag_intact(b, f))

        reset = capture or t == "P"
        key = self._poskey(b, 1 - pl, castling, ep_new)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps)

    @staticmethod
    def _castle_flag_intact(board, flag) -> bool:
        sc = StandardCastling
        kfrom, _, rfrom, _, _, _ = sc.CASTLES[flag]
        pl = WHITE if flag in "KQ" else BLACK
        return board.get(kfrom) == (pl, "K") and board.get(rfrom) == (pl, "R")

    # --------------------------------------------------------------------- #
    # Insufficient material.  In atomic almost anything can mate (a piece beside
    # the enemy king can be exploded), so a "dead" position is rarer than in
    # chess.  This ports python-chess ``AtomicBoard.has_insufficient_material``:
    # a side cannot win unless it has a queen or pawn, two-plus non-(two-knight)
    # minors, or the enemy king is not bare (enemy pieces could self-explode).
    # The game is a forced draw only when *neither* side can ever win.
    # --------------------------------------------------------------------- #
    def _side_insufficient(self, board, color) -> bool:
        enemy = 1 - color
        mine = [t for (_, (pl, t)) in board.items() if pl == color]
        theirs = [(sq, t) for (sq, (pl, t)) in board.items() if pl == enemy]

        # enemy king already gone -> material irrelevant (you've won)
        if not any(t == "K" for (_, t) in theirs):
            return False
        # bare king can never mate
        if all(t == "K" for t in mine):
            return True

        enemy_non_king = [(sq, t) for (sq, t) in theirs if t != "K"]
        if enemy_non_king:
            # enemy has extra pieces -> they can usually be exploded beside their
            # king, UNLESS the whole board is only bishops + kings and no two
            # bishops (of opposite colour) can ever explode each other / a king.
            # (Faithful port of AtomicBoard.has_insufficient_material.)
            non_king_types = {t for (_, (pl, t)) in board.items() if t != "K"}
            if non_king_types <= {"B"}:
                def has(col, shade):  # shade: 0 = dark, 1 = light (parity of c+r)
                    return any((sq[0] + sq[1]) % 2 == shade
                               for (sq, (pl, t)) in board.items()
                               if t == "B" and pl == col)
                if not has(WHITE, 0):          # no white bishop on a dark square
                    return not has(BLACK, 1)
                if not has(WHITE, 1):          # no white bishop on a light square
                    return not has(BLACK, 0)
            return False

        # enemy is a bare king: classic mating-material test for our pieces
        my_non_king = [t for t in mine if t != "K"]
        if "Q" in my_non_king or "P" in my_non_king:
            return False
        minors_rooks = [t for t in my_non_king if t in ("B", "N", "R")]
        if len(my_non_king) == 1 and len(minors_rooks) == 1:
            return True                       # lone N / B / R can't mate
        if my_non_king and all(t == "N" for t in my_non_king):
            return len(my_non_king) <= 2      # one or two knights can't mate
        return False

    def _insufficient(self, board) -> bool:
        return (self._side_insufficient(board, WHITE)
                and self._side_insufficient(board, BLACK))

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        kg = self._king_gone_result(state)
        if kg is not None:
            names = {WHITE: "White", BLACK: "Black"}
            spec["caption"] = f"{names[0 if kg[0] > 0 else 1]} wins (king exploded)"
        return spec
