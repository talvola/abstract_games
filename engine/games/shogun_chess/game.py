"""Shogun Chess (Couch Tomato, 2019-2020) -- a crazyhouse/shogi hybrid on the
standard 8x8 chess array, as played on pychess.org and defined in
Fairy-Stockfish's variants.ini ([shogun:crazyhouse]).

Western chess rules (castling, en passant, double step, check/checkmate)
plus two shogi mechanics:

* **Shogi-style promotion in the far three ranks** (ranks 6-8 from each
  player's side). A move that starts or ends in the zone may OPTIONALLY
  promote: P->C (Captain, moves like a king), N->G (General, knight+king),
  B->A (Archbishop, bishop+knight), R->M (Mortar, rook+knight),
  F (Duchess/ferz, one step diagonal) -> Q (Queen). Only ONE of each major
  promoted type (G/A/M/Q) may be on the board per side at a time (the
  Captain is unlimited). The queen starts on the board as a *promoted
  duchess*. A pawn reaching the last rank MUST promote (it could never
  move again); a pawn capturing en passant may NOT promote.

* **Crazyhouse-style drops with demotion**: a captured piece goes to the
  capturer's hand, demoted to its base type (Q->F, M->R, A->B, G->N, C->P).
  A piece in hand may be dropped on any empty square in YOUR FIRST FIVE
  ranks (never in the promotion zone). Unlike crazyhouse, pawns MAY be
  dropped on the first rank; there is no doubled-pawn or drop-mate
  restriction. A pawn dropped on the first rank single-steps (double step
  only from the usual second rank); a dropped rook cannot castle.

Draws: stalemate, threefold repetition, 50-move rule (any drop or promotion
also resets the counter, as in Fairy-Stockfish), plus a hard ply cap. White = player 0.
Moves: "c,r>c,r" with an optional "=X" promotion suffix; drops "L@c,r".
Anchored move-for-move against pyffish (Fairy-Stockfish) -- see selftest.py.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, StandardCastling,
    DropRules, cell, ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# base type -> promoted type (promotion is encoded in the piece letter itself,
# so no separate promoted-square set is needed; demotion is the inverse map).
PROMOTE = {"P": "C", "N": "G", "B": "A", "R": "M", "F": "Q"}
DEMOTE = {v: k for k, v in PROMOTE.items()}
LIMITED = ("G", "A", "M", "Q")     # majors: at most one of each on board per side

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]   # Q = promoted duchess


class ShogunDrops(DropRules):
    """Drops on empty squares in the dropper's first five ranks only (the
    complement of the promotion zone). All banked types, pawns included, may
    drop anywhere there -- even the first rank (unlike crazyhouse)."""

    enabled = True

    def initial_hands(self, core) -> dict:
        return {WHITE: {}, BLACK: {}}

    def can_drop_on(self, core, state, letter, to, player) -> bool:
        return to[1] <= 4 if player == WHITE else to[1] >= 3

    def captured_to_hand(self, core, letter, was_promoted):
        if letter == "K":
            return None                          # never happens in legal play
        return DEMOTE.get(letter, letter)        # promoted pieces demote


class ShogunChess(ChessLike):
    name = "Shogun Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []),
        "B": (DIAG, []),
        "Q": (ALL8, []),
        "N": ([], KNIGHT),
        "K": ([], ALL8),
        "F": ([], DIAG),            # Duchess (ferz): one step diagonally
        "C": ([], ALL8),            # Captain: king move (non-royal)
        "G": ([], ALL8 + KNIGHT),   # General: knight + king (centaur)
        "A": (DIAG, KNIGHT),        # Archbishop: bishop + knight
        "M": (ORTHO, KNIGHT),       # Mortar: rook + knight (chancellor)
    }
    HEAVY = ("P", "R", "Q", "M", "A", "G", "C")
    PIECE_VALUES = {"P": 1.0, "F": 1.5, "N": 3.0, "B": 3.0, "C": 3.0,
                    "R": 5.0, "G": 5.5, "A": 7.0, "M": 8.0, "Q": 9.0, "K": 0.0}
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("C",))   # unused (legal_moves overridden)
    CASTLING = StandardCastling()
    DROPS = ShogunDrops()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # ---- shogun promotion ---------------------------------------------------
    def _zone(self, player):
        """The promotion zone: the three ranks farthest from ``player``."""
        return (5, 6, 7) if player == WHITE else (0, 1, 2)

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        pl = state.to_move
        zone = self._zone(pl)
        last = self.HEIGHT - 1 if pl == WHITE else 0
        # promotionLimit: a major promotion is unavailable while one of that
        # type is already on the board for this side (Captain is unlimited).
        full = {t for (p, t) in state.board.values() if p == pl and t in LIMITED}
        ep_t = state.ep[0] if state.ep else None
        out = []
        for f, t in self._legal(state):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            letter = state.board[f][1]
            promo = PROMOTE.get(letter)
            if letter == "P" and t[1] == last:
                out.append(base + "=" + promo)   # mandatory: pawn could never move
                continue
            out.append(base)
            if (promo is not None and promo not in full
                    and (f[1] in zone or t[1] in zone)
                    # no promotion on an en-passant capture
                    and not (letter == "P" and t == ep_t and t not in state.board)):
                out.append(base + "=" + promo)
        out.extend(self._drop_moves(state))
        return out

    # ---- apply (base handles promotion for pawns only; here ANY piece may
    # carry an "=X" suffix, and captured promoted pieces demote by letter) ----
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
        hands = {p: dict(h) for p, h in state.hands.items()}

        capture = to in state.board
        captured = state.board.get(to)
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
        if promo:
            t = promo
        b[to] = (pl, t)

        if capture and captured is not None:
            gained = self.DROPS.captured_to_hand(self, captured[1], False)
            if gained is not None:
                hands.setdefault(pl, {})
                hands[pl][gained] = hands[pl].get(gained, 0) + 1

        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        # 50-move counter resets on captures, pawn moves AND promotions (an
        # irreversible PIECE_PROMOTION resets rule50 in Fairy-Stockfish).
        reset = capture or state.board[frm][1] == "P" or bool(promo)
        key = self._poskey(b, 1 - pl, castling, ep_new, hands)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps,
                      hands=hands, promoted=frozenset())

    def _apply_drop(self, state, move):
        # Fairy-Stockfish resets the 50-move counter on every drop.
        st = super()._apply_drop(state, move)
        st.halfmove = 0
        return st
