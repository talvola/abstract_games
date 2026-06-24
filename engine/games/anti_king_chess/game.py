"""Anti-King Chess II, by Peter Aronson (2002) -- chessvariants.com.

Standard chess (8x8) PLUS a second, *inverted* royal piece for each side: the
**Anti-King** (letter ``A``).  The signature rule is inverted check:

* A normal King is in check when it IS attacked; you must never leave it
  attacked.  An **Anti-King is "in check" (SAFE) only when it IS attacked by an
  enemy piece** -- you must never end your turn with your own Anti-King
  *un*-attacked.  Leaving your Anti-King unattacked is the inverted equivalent of
  moving into check, and is ILLEGAL; being unable to keep it attacked is
  "anti-checkmate" and you lose.

Anti-King particulars (verified against chessvariants.com / Wikibooks):

* The Anti-King **moves exactly like a King** (one square any direction) but
  **may capture only FRIENDLY pieces, never enemy pieces**, and **can never be
  captured** (only anti-mated).
* **Kings do not attack Anti-Kings** -- an Anti-King sitting next to the enemy
  King but attacked by nothing else is *un*-attacked, hence in danger.  So when
  testing whether an Anti-King is "kept attacked", the enemy King's attacks do
  NOT count.
* The Anti-King is **not** a checking piece: it neither gives check to the enemy
  King nor counts as an attacker of the enemy Anti-King (it is simply absent from
  the attack tables).

Both royals are live at once.  A player **wins** by EITHER checkmating the enemy
King (orthodox) OR anti-checkmating the enemy Anti-King (it ends the opponent's
turn un-attacked with no legal move to fix it).  Mechanically both collapse to:
the side to move has no legal move while "in danger" (King attacked OR Anti-King
un-attacked) -> that side loses; no legal move while NOT in danger -> stalemate
draw.

This is **version II**: standard pawns, standard castling, en passant and
promotion to Q/R/B/N (you may not promote to an Anti-King).  Version I (Berolina
pawns, a king's knight-leap instead of castling, asymmetric array) is a different
game and is not implemented here.

Two-royal wiring on ``agp.chesslike``
-------------------------------------
``ChessLike`` enforces royalty for the single King via ``in_check`` inside
``_legal``.  Anti-King Chess needs a *second*, inverted royal, so:

* ``A`` is deliberately **NOT** in ``PIECES`` -- that keeps it out of the
  ``attacked()`` tables (an Anti-King attacks nothing), and lets us give it its
  own movement (king-step, friendly-capture-only) in an overridden ``_pseudo``.
* ``attacked()`` is inherited (it covers every real attacker -- ``K`` included);
  a separate ``_attacked_by_nonking()`` excludes the enemy King, used only to ask
  "is the Anti-King kept attacked?".
* ``_in_danger(board, player)`` = (King attacked by enemy) OR (Anti-King NOT
  attacked by an enemy non-King).  ``_legal`` filters every move -- ordinary,
  castle and otherwise -- through ``not _in_danger(after, mover)``.
* ``is_terminal`` / ``returns`` read ``_in_danger`` exactly where stock ChessLike
  reads ``in_check``.

The mate/anti-mate test uses ordinary move generation for the opponent's replies
(the filter only calls ``attacked`` / ``_attacked_by_nonking``, never recurses
into ``legal_moves``), so there is no infinite regress.

White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

# Anti-King home squares (col, row): White d6 = (3, 5); Black d3 = (3, 2).
WHITE_ANTIKING = (3, 5)
BLACK_ANTIKING = (3, 2)


class AntiKingChess(ChessLike):
    uid = "anti_king_chess"
    name = "Anti-King Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    # NOTE: the Anti-King "A" is intentionally absent here -- see module docstring.
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
        b[WHITE_ANTIKING] = (WHITE, "A")
        b[BLACK_ANTIKING] = (BLACK, "A")
        return b

    # ---- attack helpers -----------------------------------------------------
    def _attacked_by_nonking(self, board, c, r, by) -> bool:
        """Like ``attacked``, but the enemy KING's attacks are EXCLUDED.

        Used to decide whether an Anti-King is "kept attacked": a King does not
        attack an Anti-King, so a bare King adjacency does not keep it safe."""
        for (dx, dy), types in self._leap_map.items():
            occ = board.get((c + dx, r + dy))
            if occ is not None and occ[0] == by and occ[1] in types and occ[1] != "K":
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

    def _anti_king(self, board, player):
        for (c, r), (pl, t) in board.items():
            if pl == player and t == "A":
                return c, r
        return None

    def _antiking_safe(self, board, player) -> bool:
        """True if ``player``'s Anti-King is kept attacked (i.e. NOT in danger).

        Vacuously True if the Anti-King is gone (it can never be captured, so in
        legal play it is always present -- this only guards hand-built tests)."""
        a = self._anti_king(board, player)
        if a is None:
            return True
        return self._attacked_by_nonking(board, a[0], a[1], 1 - player)

    def _in_danger(self, board, player) -> bool:
        """``player`` is in danger if its King is attacked (orthodox check) OR its
        Anti-King is un-attacked (anti-check).  A legal move may leave neither."""
        return self.in_check(board, player) or not self._antiking_safe(board, player)

    # ---- move generation ----------------------------------------------------
    def _pseudo(self, state):
        """Standard pseudo-moves, but the Anti-King is handled specially: it steps
        like a King to any EMPTY or FRIENDLY square (capturing the friend), and
        never onto an enemy-occupied square (it cannot capture enemies)."""
        board, player = state.board, state.to_move
        ep_target = state.ep[0] if state.ep else None
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "A":
                for dc, dr in ALL8:
                    tc, tr = c + dc, r + dr
                    if not self.on(tc, tr):
                        continue
                    occ = board.get((tc, tr))
                    # empty, or a FRIENDLY piece (capture own); never an enemy.
                    if occ is None or occ[0] == player:
                        yield (c, r), (tc, tr)
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

    def _castle_board(self, state, frm, to):
        """The full board after a castling king-move (rook follows), for the
        Anti-King-safety filter -- moving the rook can block/unblock a slider that
        attacks the Anti-King, so we apply the real move, not just the king step."""
        b = dict(state.board)
        pl, t = b.pop(frm)
        b[to] = (pl, t)
        rook = self.CASTLING.rook_move(frm, to, pl)
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        return b

    def _legal(self, state):
        """Every move must leave the mover NOT in danger (King safe AND Anti-King
        kept attacked).  This filters ordinary moves and castles alike."""
        player = state.to_move
        moves = []
        for frm, to in self._pseudo(state):
            nb = self._apply_board(state.board, frm, to, state.ep)
            if not self._in_danger(nb, player):
                moves.append((frm, to))
        for frm, to in self.CASTLING.moves(self, state):
            nb = self._castle_board(state, frm, to)
            if not self._in_danger(nb, player):
                moves.append((frm, to))
        return moves

    # ---- terminal / result --------------------------------------------------
    def _insufficient(self, board) -> bool:
        # Orthodox insufficient-material is meaningless with a second (Anti-)royal:
        # you can anti-mate with very little material, and the heuristic ignores
        # the ever-present Anti-Kings.  Disabled; the 50-move / repetition / ply-cap
        # draws (kept) still guarantee termination.
        return False

    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        return not self._legal(state)

    def returns(self, state) -> list:
        # No legal move while NOT in danger -> stalemate (draw); otherwise the side
        # to move is check/anti-checkmated and loses.
        if self._draw(state) or not self._in_danger(state.board, state.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                spec["caption"] = "Draw"
            else:
                w = 0 if ret[0] > 0 else 1
                loser = 1 - w
                why = "checkmate" if self.in_check(state.board, loser) else "anti-checkmate"
                spec["caption"] = f"{names[w]} wins ({why})"
        else:
            p = state.to_move
            flags = []
            if self.in_check(state.board, p):
                flags.append("check")
            if not self._antiking_safe(state.board, p):
                flags.append("anti-check")
            tag = f" ({', '.join(flags)})" if flags else ""
            spec["caption"] = f"{names[p]} to move{tag}"
        return spec
