"""Shatar -- Mongolian chess (traditional rules), 8x8, on the shared chess-like core.

Pieces (letters follow Fairy-Stockfish, our differential oracle):

* **Noyon** (King, ``K``) -- a chess king; there is NO castling.
* **Bers** (``J``) -- the queen: moves like a chess rook OR one square
  diagonally (shogi's promoted rook / dragon king).
* **Teme** (Bishop, ``B``), **Terge** (Rook, ``R``), **Mori** (Knight, ``N``) --
  exactly as in chess.
* **Khuu** (Pawn, ``P``) -- steps one square forward, captures diagonally
  forward, and promotes ONLY to a Bers on the last rank. Pawns have no double
  step and there is no en passant; the game's single prescribed double step is
  the obligatory opening 1.d4 d5, which (following Fairy-Stockfish) is baked
  into the initial position, so play starts with White's SECOND move.

What makes Shatar distinctive is the classification of checks and mates:

* A check by the bers, rook or knight is a **shak**; a check by the bishop is a
  **tuk**; a check by a pawn is a **zod**. Only a mate at the end of an
  UNBROKEN series of checks that contained at least one shak wins the game.
* A mate whose check-series contained no shak (only bishop/pawn checks) is
  **niol** -- a DRAW.
* A mate delivered by the knight alone is FORBIDDEN: following Fairy-Stockfish,
  playing it loses -- i.e. the *mated* side wins.
* **Robado**: as soon as either side is reduced to a lone king the game is an
  immediate DRAW (checked before mate, so baring the last piece with "mate" is
  still a draw).
* Stalemate is a draw. Standard draws: threefold repetition, 100 halfmoves
  without a pawn move or capture, plus a hard ply cap for termination.

Anchored move-for-move and result-for-result against Fairy-Stockfish's
``shatar`` variant via pyffish (see ``_diff_pyffish.py``); the pure-stdlib
anchors live in ``selftest.py``. White = player 0. See ``rules.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, NoCastling,
    ORTHO, DIAG, KNIGHT, ALL8, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "J", "K", "B", "N", "R"]

#: Piece letters whose check counts as a *shak*.
SHAK_PIECES = frozenset(("N", "R", "J"))

_NO_CHAIN = ((False, False), (False, False))


@dataclass
class SState(CState):
    """CState plus, per player, that player's check status *when they were last
    to move*: ``chain[p] = (was_in_check, series_had_shak)``. This mirrors the
    Fairy-Stockfish walk over ``StateInfo`` two plies at a time: the second flag
    accumulates "the current unbroken series of checks against p contains at
    least one shak" and resets whenever p gets a move while not in check."""
    chain: tuple = _NO_CHAIN


class ShatarPromotion(LastRankPromotion):
    def safety_piece(self) -> str:
        return "J"


class Shatar(ChessLike):
    name = "Shatar"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []),          # Terge -- rook
        "N": ([], KNIGHT),         # Mori -- knight
        "B": (DIAG, []),           # Teme -- bishop
        "J": (ORTHO, DIAG),        # Bers -- rook slides + one-step diagonal
        "K": ([], ALL8),           # Noyon -- king
    }
    HEAVY = ("P", "R", "J", "B", "N")   # informational; _insufficient is off
    PIECE_VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "J": 6.0, "K": 0.0}
    PAWN = StandardPawn(white_start=1, black_start=6, double=False)
    PROMOTION = ShatarPromotion(("J",))
    CASTLING = NoCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 7)] = (BLACK, BACK_RANK[c])
            if c == 3:
                b[(3, 3)] = (WHITE, "P")   # the prescribed 1.d4
                b[(3, 4)] = (BLACK, "P")   # ... and 1...d5, baked in
            else:
                b[(c, 1)] = (WHITE, "P")
                b[(c, 6)] = (BLACK, "P")
        return b

    # ---- check classification ------------------------------------------------
    def _checker_types(self, board, player) -> set:
        """The piece letters of every enemy piece currently checking ``player``'s
        king (used both for the knight-mate rule and the shak flag)."""
        k = self._king(board, player)
        if k is None:
            return set()
        enemy = 1 - player
        out = set()
        for (c, r), (pl, t) in board.items():
            if pl != enemy or t in out:
                continue
            if t == "P":
                fwd = self.PAWN.fwd(enemy)
                if k in ((c - 1, r + fwd), (c + 1, r + fwd)):
                    out.add("P")
                continue
            slides, leaps = self.PIECES[t]
            if any((c + dc, r + dr) == k for dc, dr in leaps):
                out.add(t)
                continue
            for dc, dr in slides:
                cc, rr = c + dc, r + dr
                while self.on(cc, rr):
                    if (cc, rr) == k:
                        out.add(t)
                        break
                    if (cc, rr) in board:
                        break
                    cc += dc
                    rr += dr
                if t in out:
                    break
        return out

    @staticmethod
    def _chain_of(state) -> tuple:
        return getattr(state, "chain", _NO_CHAIN)

    def _mate_shak(self, state) -> bool:
        """At a mate against ``state.to_move``: does the unbroken series of
        checks (this one included) contain a shak?"""
        shak_now = bool(self._checker_types(state.board, state.to_move)
                        & SHAK_PIECES)
        was_in_check, had_shak = self._chain_of(state)[state.to_move]
        return shak_now or (was_in_check and had_shak)

    # ---- bare king (robado) ---------------------------------------------------
    def _bared(self, board) -> bool:
        counts = [0, 0]
        for (pl, _t) in board.values():
            counts[pl] += 1
        return counts[0] <= 1 or counts[1] <= 1

    # ---- draws / terminal ------------------------------------------------------
    def _insufficient(self, board) -> bool:
        return False        # robado (bare king = draw) supersedes material draws

    def legal_moves(self, state) -> list:
        if self._bared(state.board):
            return []
        return super().legal_moves(state)

    def is_terminal(self, state) -> bool:
        if self._bared(state.board):
            return True
        return super().is_terminal(state)

    def returns(self, state) -> list:
        if self._bared(state.board) or self._draw(state):
            return [0.0, 0.0]
        if self._legal(state):
            return [0.0, 0.0]                      # not terminal
        loser = state.to_move
        checkers = self._checker_types(state.board, loser)
        if not checkers:
            return [0.0, 0.0]                      # stalemate = draw
        if checkers <= {"N"}:
            winner = loser                         # forbidden knight mate
        elif self._mate_shak(state):
            winner = 1 - loser                     # proper (shak) mate
        else:
            return [0.0, 0.0]                      # niol = draw
        return [1.0, -1.0] if winner == WHITE else [-1.0, 1.0]

    # ---- apply -----------------------------------------------------------------
    def _as_sstate(self, cs: CState, chain: tuple) -> SState:
        return SState(board=cs.board, to_move=cs.to_move, castling=cs.castling,
                      ep=cs.ep, halfmove=cs.halfmove, ply=cs.ply, reps=cs.reps,
                      hands=cs.hands, promoted=cs.promoted, chain=chain)

    def apply_move(self, state, move, rng=None):
        ns = super().apply_move(state, move, rng)
        chain = list(self._chain_of(state))
        mover_to_be = ns.to_move                   # the side now to move
        if self.in_check(ns.board, mover_to_be):
            shak_now = bool(self._checker_types(ns.board, mover_to_be)
                            & SHAK_PIECES)
            was_in_check, had_shak = chain[mover_to_be]
            chain[mover_to_be] = (True, shak_now or (was_in_check and had_shak))
        else:
            chain[mover_to_be] = (False, False)
        return self._as_sstate(ns, tuple(chain))

    # ---- (de)serialize ----------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        st = super().initial_state(options, rng)
        return self._as_sstate(st, _NO_CHAIN)

    def serialize(self, state) -> dict:
        d = super().serialize(state)
        ch = self._chain_of(state)
        d["chain"] = [[bool(ch[0][0]), bool(ch[0][1])],
                      [bool(ch[1][0]), bool(ch[1][1])]]
        return d

    def deserialize(self, d: dict):
        st = super().deserialize(d)
        ch = d.get("chain", [[False, False], [False, False]])
        return self._as_sstate(st, (tuple(ch[0]), tuple(ch[1])))

    # ---- presentation -------------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            if self._bared(state.board):
                spec["caption"] = "Draw (robado — bare king)"
            elif self._draw(state):
                pass                               # base "Draw" caption is fine
            elif not self._legal(state):
                loser = state.to_move
                checkers = self._checker_types(state.board, loser)
                if not checkers:
                    spec["caption"] = "Draw (stalemate)"
                elif checkers <= {"N"}:
                    spec["caption"] = (f"{names[loser]} wins "
                                       f"(forbidden knight mate)")
                elif self._mate_shak(state):
                    spec["caption"] = f"{names[1 - loser]} wins (checkmate)"
                else:
                    spec["caption"] = "Draw (niol — mate without shak)"
        return spec
