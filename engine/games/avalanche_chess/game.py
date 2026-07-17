"""Avalanche Chess — Ralph Betza (1977). A Recognized Chess Variant.

Orthodox chess, except every turn has a mandatory second component: after your
regular move you must push one ENEMY pawn one square straight forward (its own
forward — i.e. toward you, toward its promotion rank), never a capture. Rules
implemented from the authoritative page
https://www.chessvariants.com/mvopponent.dir/avalanche.html (Bodlaender's
write-up of Betza's game), cross-checked against Wikipedia "Avalanche chess";
the two agree. Key rulings (quotes in rules.md):

* The regular part must be legal by orthodox rules (own king safe after it —
  you may NOT plan to undo a check with the push).
* The push is OBLIGATORY unless, after your regular part, the opponent has no
  pawn with an empty square directly ahead.
* A push that leaves the PUSHER's own king in check is a legal move that LOSES
  the game instantly ("he loses the game ... even when he checks or mates his
  opponent in that turn"). It is modelled as a legal, immediately-losing move
  (winner stored in state), exactly as the source words it — so a player whose
  every push self-checks is lost, even if the regular part mated.
* A pawn pushed to its last rank promotes; the pawn's OWNER (not the pusher)
  chooses the piece — modelled as a standalone "=Q"/"=R"/"=B"/"=N" move that
  the owner must play at the start of their turn. If the chosen piece checks
  the pusher, the pusher loses (same self-check rule).
* There is NO en passant capture at all (double-steps still exist).

Move encoding: a compound turn is a 4-cell path
``"fc,fr>tc,tr>pc,pr>qc,qr"`` (regular move, then the pushed pawn's step), with
an optional trailing ``=X`` for the mover's OWN pawn promoting on the regular
part. A turn with no available push is the plain 2-cell ``"fc,fr>tc,tr[=X]"``.
The push-promotion choice is the bare ``"=Q"`` etc. (renders as action
buttons). Built on :class:`agp.chesslike.ChessLike` (board model, movement,
attack/check, castling, draw machinery), following the multi-part-turn pattern
of ``games/marseillais_chess``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agp.chesslike import (
    ChessLike, CState, cell, _FILES,
    StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]
PROMO_CHOICES = ("Q", "R", "B", "N")


@dataclass
class AState(CState):
    """Chess state + Avalanche bookkeeping.

    ``winner``   — event win: set when a push (or a push-promotion choice)
                   leaves the pusher's own king in check (the pusher loses).
    ``pending``  — square of an enemy pawn pushed to its last rank, awaiting
                   the OWNER's promotion choice (owner == ``to_move``).
    ``balanced`` — Castelli's Balanced Avalanche: White's first turn has no
                   push. The base ``ep`` field is unused (always None): there
                   is no en passant in Avalanche Chess.
    """

    winner: Optional[int] = None
    pending: Optional[tuple] = None
    balanced: bool = False


class AvalancheChess(ChessLike):
    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(PROMO_CHOICES)
    CASTLING = StandardCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # ---- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> AState:
        balanced = bool(options and options.get("variant") == "balanced")
        st = AState(board=self.setup_board(), to_move=WHITE,
                    castling=self.CASTLING.initial_rights(), ep=None,
                    balanced=balanced)
        st.reps = {self._poskey_state(st): 1}
        return st

    def current_player(self, state) -> int:
        return state.to_move

    # ---- position key (include the pending-promotion square) ---------------
    def _poskey_state(self, state) -> str:
        base = self._poskey(state.board, state.to_move, state.castling, None, None)
        pend = f"{state.pending[0]},{state.pending[1]}" if state.pending else "-"
        return f"{base}#pd{pend}"

    # ---- push machinery -----------------------------------------------------
    def _pushes(self, board, player) -> list:
        """(from, to) single-step advances available to ``player``'s OPPONENT's
        pawns on ``board`` — the pushes ``player`` may (must) make."""
        enemy = 1 - player
        fwd = 1 if enemy == WHITE else -1
        out = []
        for (c, r), (pl, t) in board.items():
            if pl == enemy and t == "P":
                tgt = (c, r + fwd)
                if self.on(*tgt) and tgt not in board:
                    out.append(((c, r), tgt))
        return out

    def _apply_regular(self, board, frm, to, promo, player) -> dict:
        """Board after the regular (orthodox) part only. No en passant exists."""
        b = dict(board)
        pl, t = b.pop(frm)
        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        if t == "P" and promo:
            t = promo
        b[to] = (pl, t)
        return b

    # ---- move generation ----------------------------------------------------
    def legal_moves(self, state) -> list:
        if state.winner is not None or self._draw(state):
            return []
        if state.pending is not None:                 # owner picks the promotion
            return ["=" + x for x in PROMO_CHOICES]
        pl = state.to_move
        tmp = CState(board=state.board, to_move=pl, castling=state.castling, ep=None)
        push_ok = not (state.balanced and state.ply == 0)
        out = []
        for f, t in self._legal(tmp):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if state.board[f][1] == "P":
                chs = self.PROMOTION.options(self, tmp, f, t)
            else:
                chs = [None]
            # Push availability depends only on occupancy, not on which piece a
            # promoting pawn becomes — compute the post-move board once.
            b_after = self._apply_regular(state.board, f, t, chs[0], pl)
            pushes = self._pushes(b_after, pl) if push_ok else []
            for ch in chs:
                suf = "" if ch is None else "=" + ch
                if pushes:                            # push is obligatory
                    for pf, pt in pushes:
                        out.append(f"{base}>{pf[0]},{pf[1]}>{pt[0]},{pt[1]}{suf}")
                else:                                 # no pawn can be advanced
                    out.append(base + suf)
        return out

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None) -> AState:
        pl = state.to_move
        if move.startswith("="):                      # owner's push-promotion choice
            letter = move[1:]
            b = dict(state.board)
            b[state.pending] = (pl, letter)
            # Rule: if the promotion checks the PUSHER (the previous mover),
            # the pusher loses — the chooser (owner) wins.
            winner = pl if self.in_check(b, 1 - pl) else None
            new = AState(board=b, to_move=pl, castling=state.castling, ep=None,
                         halfmove=0, ply=state.ply + 1, reps=dict(state.reps),
                         winner=winner, pending=None, balanced=state.balanced)
            key = self._poskey_state(new)
            new.reps[key] = new.reps.get(key, 0) + 1
            return new

        promo = None
        if "=" in move:
            move, promo = move.split("=")
        cells = [cell(s) for s in move.split(">")]
        frm, to = cells[0], cells[1]
        capture = to in state.board
        pawn_move = state.board[frm][1] == "P"
        b = self._apply_regular(state.board, frm, to, promo, pl)
        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)

        winner = None
        pending = None
        if len(cells) == 4:                           # the push component
            pf, pt = cells[2], cells[3]
            ppl, ptt = b.pop(pf)
            b[pt] = (ppl, ptt)
            pawn_move = True
            if self.in_check(b, pl):                  # self-check push → pusher loses
                winner = 1 - pl
            else:
                last = self.HEIGHT - 1 if ppl == WHITE else 0
                if pt[1] == last:                     # pushed to its promotion rank
                    pending = pt                      # owner (next mover) chooses

        new = AState(board=b, to_move=1 - pl, castling=castling, ep=None,
                     halfmove=0 if (capture or pawn_move) else state.halfmove + 1,
                     ply=state.ply + 1, reps=dict(state.reps),
                     winner=winner, pending=pending, balanced=state.balanced)
        key = self._poskey_state(new)
        new.reps[key] = new.reps.get(key, 0) + 1
        return new

    # ---- terminal / returns -------------------------------------------------
    def is_terminal(self, state) -> bool:
        if state.winner is not None or self._draw(state):
            return True
        return not self.legal_moves(state)

    def returns(self, state) -> list:
        if state.winner is not None:
            return [1.0, -1.0] if state.winner == WHITE else [-1.0, 1.0]
        if self._draw(state) or not self.in_check(state.board, state.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # ---- (de)serialize ------------------------------------------------------
    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["winner"] = state.winner
        d["pending"] = f"{state.pending[0]},{state.pending[1]}" if state.pending else None
        d["balanced"] = state.balanced
        return d

    def deserialize(self, d: dict) -> AState:
        base = super().deserialize(d)
        return AState(board=base.board, to_move=base.to_move,
                      castling=base.castling, ep=None,
                      halfmove=base.halfmove, ply=base.ply, reps=base.reps,
                      winner=d.get("winner"),
                      pending=cell(d["pending"]) if d.get("pending") else None,
                      balanced=bool(d.get("balanced", False)))

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        alg = lambda c: f"{_FILES[c[0]]}{c[1] + 1}"  # noqa: E731
        if move.startswith("="):
            sq = state.pending
            return (alg(sq) if sq else "push") + move
        promo = None
        raw = move
        if "=" in move:
            raw, promo = move.split("=")
        cells = [cell(s) for s in raw.split(">")]
        frm, to = cells[0], cells[1]
        pl, t = state.board.get(frm, (None, "?"))
        if t == "K" and self.CASTLING.rook_move(frm, to, pl) is not None:
            main = "O-O" if to[0] > frm[0] else "O-O-O"
        else:
            main = f"{t}{alg(frm)}{'x' if to in state.board else '-'}{alg(to)}"
        if promo:
            main += "=" + promo
        if len(cells) == 4:
            return f"{main} / push {alg(cells[3])}"
        return main

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "White", BLACK: "Black"}
        if state.winner is not None:
            spec["caption"] = f"{names[state.winner]} wins (opponent self-checked by pawn push)"
        elif state.pending is not None and not self.is_terminal(state):
            sq = state.pending
            spec["caption"] = (f"{names[state.to_move]} to choose the pushed "
                               f"pawn's promotion")
            spec["highlights"].append({"cell": f"{sq[0]},{sq[1]}", "kind": "last-move"})
        return spec
