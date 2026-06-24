"""Andernach Chess (8x8), built on the shared chess-like core.

Standard chess in every respect EXCEPT one rule: **a piece that makes a capture
changes to the opponent's colour** and remains on the capture square -- so after
White captures with a knight, that square now holds a *Black* knight. The single
exception is the KING: a king that captures does NOT change colour, and a king is
never produced by a colour change.

Non-capturing moves are completely normal (no colour change). En-passant capture
*does* count as a capture and so flips the capturing pawn's colour (the pawn ends
on its diagonal landing square, now an enemy pawn). A pawn that captures onto the
last rank both promotes AND changes colour: it becomes the opponent's promoted
piece -- but a piece can never be "promoted onto the opponent's back rank into a
king", so promotion targets (Q/R/B/N) are unaffected by the exception.

How the colour-flip is wired into ChessLike's apply_move + legality
------------------------------------------------------------------
The ONLY board transform that differs from standard chess is "on a capture, the
mover's piece becomes the opponent's". I express that transform once in
``_resolve(board, frm, to, ep, promo)`` (pure; returns ``(new_board, captured)``)
and route BOTH the legality filter and the real apply through it:

* ``_legal`` overrides the base filter: for each pseudo-move it builds the board
  with ``_resolve`` (so the capturing piece has ALREADY flipped to the enemy) and
  keeps the move only if the MOVER's king is not in check on that flipped board.
  This is the crucial correctness point: a capture that hands the capturing piece
  to the opponent can *expose* the mover's own king (e.g. the capturing rook was
  the only thing guarding the king's rank, and after the flip it is an enemy rook
  giving check) -- such a move is ILLEGAL because king-safety is tested on the
  post-flip board, exactly as the base class tests it on the post-move board.

* ``apply_move`` does the same ChessLike bookkeeping (castling rights, e.p.,
  halfmove clock, repetition key) but obtains the resulting board from
  ``_resolve`` instead of the inline relocate. Castling never captures, so it is
  handled separately and is byte-identical to standard chess.

Everything else -- move generation, check/mate/stalemate detection, the
fifty-move / threefold / insufficient-material draws, (de)serialisation and
rendering -- is inherited unchanged. White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, cell,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class AndernachChess(ChessLike):
    uid = "andernach_chess"
    name = "Andernach Chess"

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
    # The Andernach board transform: a capturing piece flips colour (except a
    # king). Pure -- does not mutate ``board``. Castling never captures, so it
    # is resolved by the caller and never reaches here.
    #
    # Returns (new_board, captured) where ``captured`` is the (player, letter)
    # that was removed, or None for a quiet move.
    # --------------------------------------------------------------------- #
    def _resolve(self, board, frm, to, ep, promo=None):
        b = dict(board)
        pl, t = b.pop(frm)

        captured_sq = None
        if to in board and board[to][0] != pl:     # ordinary capture
            captured_sq = to
        elif t == "P" and ep is not None and to == ep[0] and to not in board:
            captured_sq = ep[1]                     # en-passant capture

        captured = None
        if captured_sq is not None:
            captured = board.get(captured_sq)
            b.pop(captured_sq, None)

        if t == "P" and promo:
            t = promo

        if captured_sq is not None and t != "K":
            # Andernach rule: the capturing piece changes to the enemy's colour
            # (kings are exempt and never change).
            pl = 1 - pl

        b[to] = (pl, t)
        return b, captured

    # --------------------------------------------------------------------- #
    # Legality: build the post-capture (and thus post-colour-flip) board and
    # require the MOVER's king to be safe on it. Castling is delegated to the
    # base strategy (it never captures, so no flip is possible).
    # --------------------------------------------------------------------- #
    def _legal(self, state):
        moves = []
        board, player = state.board, state.to_move
        for frm, to in self._pseudo(state):
            promo = self.PROMOTION.safety_piece() if board[frm][1] == "P" else None
            nb, _cap = self._resolve(board, frm, to, state.ep, promo)
            if not self.in_check(nb, player):
                moves.append((frm, to))
        moves.extend(self.CASTLING.moves(self, state))
        return moves

    # --------------------------------------------------------------------- #
    # Apply: identical ChessLike bookkeeping, but the resulting board comes from
    # the Andernach resolver so the capturing piece is flipped to the enemy.
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
            # Castling never captures -> no colour change.
            b = dict(state.board)
            b[to] = b.pop(frm)
            b[rook[1]] = b.pop(rook[0])
            capture = False
            ep_new = None
        else:
            ep_new = None
            if t == "P" and to not in state.board and not (
                    state.ep is not None and to == state.ep[0]):
                ep_new = self.PAWN.ep_after(frm, to)
            b, captured = self._resolve(state.board, frm, to, state.ep, promo)
            capture = captured is not None

        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        reset = capture or t == "P"
        key = self._poskey(b, 1 - pl, castling, ep_new)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps)
