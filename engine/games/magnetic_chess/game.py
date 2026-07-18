"""Magnetic Chess -- João Pedro Neto & Claude Chaunier (1996).

Standard FIDE chess with one game-transforming rule added: after a piece moves,
it acts as a MAGNET.  Every piece carries a charge (White = one polarity, Black =
the other) *except the two kings, which are neutral*.  From the square the moving
piece has just landed on, look outward along the rank and file (never diagonals):
the closest piece in each of the four orthogonal directions is

  * REPELLED, if it has the same charge (same colour) -- it slides directly away
    from the mover until it hits another piece or the board edge; or
  * ATTRACTED, if it has the opposite charge (other colour) -- it slides toward
    the mover until it is adjacent to it.

A king is never attracted or repelled, never attracts or repels, and *blocks* a
field line (so nothing behind a king is affected).  There is NO check, checkmate
or stalemate -- **the player who captures the enemy king wins.**

Source: https://www.chessvariants.com/other.dir/magnetic.html (a Recognized
Variant; page written by the inventors, with corrections by Michael Keller).  The
rules *as implemented* are documented in ``rules.md`` next to this file.

Built on the shared chess-like core (``agp.chesslike``); the magnetism is a
post-move resolution step inside :meth:`apply_move`, and the win condition /
move generation drop all of the check machinery.  White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    CState, cell, ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class MagneticPawn(StandardPawn):
    """Orthodox pawn with two Magnetic-Chess changes: NO en passant, and a pawn
    may take its two-square step from *either* of the two ranks nearest its own
    side (even if it has already moved) -- because magnetism can push a pawn back
    home again ("real missiles")."""

    def ep_after(self, frm, to):
        return None  # no en passant in Magnetic Chess

    def pseudo(self, core, board, c, r, player, ep_target):
        fwd = self.fwd(player)
        one = (c, r + fwd)
        if core.on(*one) and one not in board:
            yield (c, r), one
            # double step allowed from the two ranks on this player's home side
            home = (r <= 1) if player == WHITE else (r >= core.HEIGHT - 2)
            two = (c, r + 2 * fwd)
            if home and core.on(*two) and two not in board:
                yield (c, r), two
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if occ is not None and occ[0] != player:   # capture only; no e.p.
                yield (c, r), t


class MagneticCastling(StandardCastling):
    """Orthodox castling geometry, but with the check restrictions removed --
    Magnetic Chess has no notion of check, so a king may castle out of, through
    or into an attacked square.  The king and rook must merely be unmoved (rights
    still held) with the squares between them empty."""

    def moves(self, core, state):
        player = state.to_move
        for flag in self.BY_COLOR[player]:
            if flag not in state.castling:
                continue
            kfrom, kto, rfrom, rto, empties, path = self.CASTLES[flag]
            if state.board.get(kfrom) != (player, "K") or state.board.get(rfrom) != (player, "R"):
                continue
            if any(sq in state.board for sq in empties):
                continue
            yield kfrom, kto


class MagneticChess(ChessLike):
    uid = "magnetic_chess"
    name = "Magnetic Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = MagneticPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = MagneticCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # ---- the magnet ---------------------------------------------------------
    def _magnet(self, board, src, color):
        """Resolve the magnetic field emanating from ``src`` (the square the just-
        moved, non-king piece of ``color`` now occupies).  Mutates ``board``.

        Each of the four orthogonal rays is resolved independently from the same
        snapshot -- the rays share no square other than ``src`` (which is
        occupied), so the order of resolution is irrelevant and no two displaced
        pieces can collide.  A pawn moved onto its promotion rank by the field is
        promoted to a Queen (the only choice the sample games ever show)."""
        moves = []
        for dc, dr in ORTHO:
            c, r = src[0] + dc, src[1] + dr
            while self.on(c, r) and (c, r) not in board:   # find closest neighbour
                c, r = c + dc, r + dr
            if not self.on(c, r):
                continue                                    # ran off the board
            npl, nt = board[(c, r)]
            if nt == "K":
                continue                                    # king blocks; unaffected
            if npl == color:                                # like charge -> repel
                tc, tr = c + dc, r + dr
                dest = None
                while self.on(tc, tr) and (tc, tr) not in board:
                    dest = (tc, tr)
                    tc, tr = tc + dc, tr + dr
                if dest is not None:
                    moves.append(((c, r), dest))
            else:                                           # opposite charge -> attract
                dest = (src[0] + dc, src[1] + dr)           # slide adjacent to src
                if dest != (c, r):
                    moves.append(((c, r), dest))
        for frm, dest in moves:
            board[dest] = board.pop(frm)
        for _frm, dest in moves:                            # magnetic promotion
            occ = board.get(dest)
            if occ is not None and occ[1] == "P":
                p = occ[0]
                if (p == WHITE and dest[1] == self.HEIGHT - 1) or (p == BLACK and dest[1] == 0):
                    board[dest] = (p, "Q")

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
        is_pawn = (t == "P")
        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        new_t = promo if (is_pawn and promo) else t
        b[to] = (pl, new_t)

        # Magnetism.  Kings are neutral (no field).  On castling the KING is
        # neutral but the ROOK moved too, so the field is generated by the rook's
        # arrival on its new square ("the changes are made by the rook movement").
        if t == "K":
            if rook is not None:
                self._magnet(b, rook[1], pl)
        else:
            self._magnet(b, to, pl)

        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        reset = capture or is_pawn
        key = self._poskey(b, 1 - pl, castling, None, None)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=None,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps, hands={}, promoted=frozenset())

    # ---- move generation (no check -> no king-safety filter) ----------------
    def _legal(self, state):
        moves = list(self._pseudo(state))
        moves.extend(self.CASTLING.moves(self, state))
        return moves

    def legal_moves(self, state):
        if self.is_terminal(state):
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

    # ---- terminal / winner (king capture) -----------------------------------
    def _winner(self, board):
        """WHITE / BLACK if a king has been captured off the board, else None.
        Kings are never moved or removed by magnetism, so a missing king can only
        mean it was captured by the opponent's move."""
        kings = {pl for (pl, t) in board.values() if t == "K"}
        if WHITE not in kings:
            return BLACK
        if BLACK not in kings:
            return WHITE
        return None

    def _draw(self, state):
        # No insufficient-material draw: even a lone king can win by capturing the
        # enemy king, so "insufficient" FIDE material is not a draw here.
        return (state.halfmove >= 100 or state.ply >= self.PLY_CAP
                or state.reps.get(self._poskey_state(state), 0) >= 3)

    def is_terminal(self, state):
        if self._winner(state.board) is not None:
            return True
        if self._draw(state):
            return True
        return not self._legal(state)   # no move for the side on turn -> drawn

    def returns(self, state):
        w = self._winner(state.board)
        if w is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if w == WHITE else [-1.0, 1.0]

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None):
        spec = super().render(state, perspective)
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                spec["caption"] = "Draw"
            else:
                w = 0 if ret[0] > 0 else 1
                spec["caption"] = f"{names[w]} wins (king captured)"
        else:
            spec["caption"] = f"{names[state.to_move]} to move"
        return spec
