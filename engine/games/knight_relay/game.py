"""Knight Relay Chess, by Mannis Charosh (c. 1972) -- chessvariants.com.

Standard chess (8x8, orthodox array and piece movement) with one extra power and
one big restriction, both centred on the knight:

* **Relay.**  Any piece **other than a king or a knight** that is *defended by a
  friendly knight* (a friendly knight attacks the square it stands on, by an
  ordinary knight-leap) gains, **in addition** to its normal moves, the power to
  move *and capture* like a knight.  So a queen, rook, bishop or pawn guarded by
  a friendly knight may leap like a knight.  Pawns and pieces *relay* the
  knight's power; the king and the knight do **not** receive it (the king is
  excluded deliberately, "to prevent kings escaping mate too readily").
* **Non-capturing, un-capturable knights.**  A knight **cannot capture** anything
  and **cannot itself be captured** (it can only ever move to an empty square, and
  it is immune from capture by any enemy move, relayed or not).  A consequence:
  **a knight can never give check** by itself -- but it CAN *relay* a check, i.e.
  a friendly non-knight piece guarded by the knight may deliver a knight-leap
  check (chessvariants/mayhematics: "the knight's check is relayed via Bg5").

Verified ruleset (chessvariants.com "Knight Relay Chess", Wikipedia, mayhematics)
--------------------------------------------------------------------------------
* Relay recipients: **all pieces except the king and the knight**, when defended
  by a friendly knight.  (The task brief guessed the king relays too -- that is
  WRONG per every published source; the king is explicitly excluded.  We follow
  the canonical rule and document the override here and in rules.md.)
* Knights: cannot capture, cannot be captured, cannot give check (only relay one).
  They still move normally to empty squares and still *guard* (relay) friendly
  pieces.  A knight is an excellent immovable blocker.
* Pawns: a pawn may **not** use a relayed knight-move to move to or capture on its
  own first or last rank -- so there is **no promotion via a relayed move**; a
  pawn promotes only by an ordinary pawn move.  (If a pawn relays back onto its
  initial rank it regains its double-step -- a natural consequence of our
  generator, which re-derives the double-step from the pawn's current rank.)
* **No en passant.**
* **Castling:** the published rules do not mention it; orthodox chess otherwise,
  so we keep standard castling.  (The king cannot relay, so castling is
  unaffected by the relay mechanic.  Documented as an interpretation.)
* Check / mate: the king is in check iff an enemy piece attacks its square by an
  ordinary (non-knight, non-relay) move OR an enemy non-knight piece *guarded by
  an enemy knight* attacks it by a knight-leap.  An enemy knight by itself never
  attacks the king.  Checkmate / stalemate are the usual no-legal-move tests.

Wiring on ``agp.chesslike``
---------------------------
Two override points, exactly mirroring the other royal variants:

1. ``attacked(board, c, r, by)`` -- the single source of truth for "is square
   (c,r) attacked by side ``by``" (drives ``in_check`` and the king-safety filter
   in the inherited ``_legal``).  We REPLACE it with a Knight-Relay-aware version:
   sliders and pawns attack as usual; a real knight does **not** attack (it cannot
   check); and any enemy non-knight, non-king piece that is *guarded by an enemy
   knight* additionally attacks every knight-leap square (a pawn never via its own
   first/last rank).

2. ``_pseudo(state)`` -- move generation.  Each piece yields its ordinary moves,
   except: a knight yields only moves onto EMPTY squares (no captures); no move of
   any kind may land on an enemy knight (knights are un-capturable); and every
   non-king, non-knight piece *guarded by a friendly knight* additionally yields
   its knight-leaps (to empty or enemy squares, but never onto an enemy knight,
   and -- for pawns -- never onto rank 0 / HEIGHT-1).

Crucially, "guarded by a knight" is computed from the **raw board positions**
(``_guarded_by_knight``), never from legality, so there is no recursion: a knight
guards a square iff it sits a knight-leap away from it, full stop (a knight cannot
be pinned off a guard -- it never moves to capture, and pins only restrict moves).

The inherited ``_legal`` filters pseudo-moves through ``in_check(after, mover)``
using our ``attacked``; ``_apply_board`` (king-safety test) is reused unchanged --
it just relocates a piece, which is exactly right.  En passant is suppressed by
forcing ``ep`` to ``None`` everywhere (the ``NoEpPawn`` below never sets it and
never reads an ep-target).  White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]


class NoEpPawn(StandardPawn):
    """A standard pawn with **no en passant**: it never creates an ep target and
    never captures onto one.  (Knight Relay Chess forbids e.p.)"""

    def ep_after(self, frm, to):
        return None

    def pseudo(self, core, board, c, r, player, ep_target):
        # Ignore any ep_target -> no e.p. capture is ever generated.
        yield from super().pseudo(core, board, c, r, player, None)


class KnightRelayChess(ChessLike):
    uid = "knight_relay"
    name = "Knight Relay Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = NoEpPawn(white_start=1, black_start=6)
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

    # ---- the relay primitive -----------------------------------------------
    def _guarded_by_knight(self, board, c, r, player) -> bool:
        """True iff a knight of ``player`` guards square (c, r) -- i.e. sits a
        knight-leap away from it.  Computed purely from piece positions (no
        legality), so it is safe to call from attack- and move-generation without
        recursion.  A knight can guard from any square it occupies; it never needs
        to (and cannot) actually move there."""
        for dc, dr in KNIGHT:
            occ = board.get((c + dc, r + dr))
            if occ is not None and occ[0] == player and occ[1] == "N":
                return True
        return False

    def _relays_knight(self, t) -> bool:
        """Piece types that CAN receive a relayed knight-move (everything but the
        king and the knight)."""
        return t not in ("K", "N")

    def _pawn_relay_ok(self, player, tr) -> bool:
        """A pawn may not use a relayed knight-move onto its own first or last
        rank (so: no relayed promotion, and no relayed move to the back rank)."""
        return 0 < tr < self.HEIGHT - 1

    # ---- attacks (Knight-Relay-aware) --------------------------------------
    def attacked(self, board, c, r, by) -> bool:
        """Is square (c, r) attacked by side ``by``?

        * Sliders and the king attack exactly as in chess.
        * A real **knight does NOT attack** (it cannot give check).
        * A non-knight, non-king piece of ``by`` that is **guarded by a ``by``
          knight** additionally attacks every knight-leap square (a pawn never via
          its own first/last rank -- but the king can't stand there relative to a
          pawn-leap anyway; the guard keeps the rule uniform).
        * Pawns attack as usual (orthodox pawn captures).
        """
        # Sliders (R/B/Q and any slider piece).  Knights are leapers only, so the
        # leap branch below is where we must EXCLUDE them.
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
        # Leapers EXCEPT the knight (the king is the only other leaper here).  A
        # real knight is intentionally skipped -- it cannot attack/check.
        for (dx, dy), types in self._leap_map.items():
            non_knight = types - {"N"}
            if not non_knight:
                continue
            occ = board.get((c + dx, r + dy))
            if occ is not None and occ[0] == by and occ[1] in non_knight:
                return True
        # Relayed knight-attacks: a square (c,r) is hit by a knight-leap from an
        # attacker at (c+dx, r+dy); that attacker relays iff it is a non-king,
        # non-knight ``by`` piece guarded by a ``by`` knight.  Pawns relay-attack
        # only if (c,r) is not on the pawn's own first/last rank.
        for dx, dy in KNIGHT:
            ac, ar = c + dx, r + dy
            occ = board.get((ac, ar))
            if occ is None or occ[0] != by or not self._relays_knight(occ[1]):
                continue
            if occ[1] == "P" and not self._pawn_relay_ok(by, r):
                continue
            if self._guarded_by_knight(board, ac, ar, by):
                return True
        return self.PAWN.attacks(self, board, c, r, by)

    # ---- move generation ----------------------------------------------------
    def _can_land(self, board, to, player) -> bool:
        """May a (non-knight) piece of ``player`` move/capture onto ``to``?
        Yes if empty or an enemy piece -- but NEVER onto an enemy knight (knights
        are immune from capture)."""
        occ = board.get(to)
        if occ is None:
            return True
        return occ[0] != player and occ[1] != "N"

    def _pseudo(self, state):
        """Pseudo-legal moves with the Knight-Relay rules baked in:

        * a knight moves only to EMPTY squares (no capture);
        * no piece may land on an enemy knight (un-capturable);
        * a non-king, non-knight piece guarded by a friendly knight ALSO yields
          its knight-leaps (to empty / enemy squares, never onto an enemy knight,
          and -- pawns -- never onto rank 0 / HEIGHT-1).
        """
        board, player = state.board, state.to_move
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue

            if t == "N":
                # Non-capturing knight: empty squares only.
                for dc, dr in KNIGHT:
                    to = (c + dc, r + dr)
                    if self.on(*to) and to not in board:
                        yield (c, r), to
                continue

            if t == "P":
                # No ep_target is ever passed (e.p. is off in this variant).  A
                # forward step always lands on an empty square; a diagonal capture
                # must not land on an enemy knight.
                for frm, to in self.PAWN.pseudo(self, board, c, r, player, None):
                    if to not in board or self._can_land(board, to, player):
                        yield frm, to
            else:
                slides, leaps = self.PIECES[t]
                for dc, dr in leaps:                      # only the king reaches here
                    to = (c + dc, r + dr)
                    if self.on(*to) and self._can_land(board, to, player):
                        yield (c, r), to
                for dc, dr in slides:
                    cc, rr = c + dc, r + dr
                    while self.on(cc, rr):
                        occ = board.get((cc, rr))
                        if occ is None:
                            yield (c, r), (cc, rr)
                        else:
                            if occ[0] != player and occ[1] != "N":
                                yield (c, r), (cc, rr)
                            break                          # a knight also BLOCKS
                        cc += dc
                        rr += dr

            # ---- relayed knight-moves (all but K and N) --------------------
            if self._relays_knight(t) and self._guarded_by_knight(board, c, r, player):
                for dc, dr in KNIGHT:
                    to = (c + dc, r + dr)
                    if not self.on(*to):
                        continue
                    if t == "P" and not self._pawn_relay_ok(player, to[1]):
                        continue
                    if self._can_land(board, to, player):
                        yield (c, r), to

    # ---- presentation -------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        # Base caption already handles check / mate / stalemate / draw via our
        # overridden ``attacked``; nothing extra to do.
        return spec
