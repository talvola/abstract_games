"""Spartan Chess -- an asymmetric-army chess variant by Steven Streetman (2010),
published on chessvariants.com.

Two civilisations face off on an 8x8 board:

* **Persians (White, seat 0)** -- an ORTHODOX FIDE army (R N B Q K B N R + pawns),
  one royal King, standard castling, standard pawn promotion. **White moves
  first.**
* **Spartans (Black, seat 1)** -- an unorthodox army with **TWO Kings** and four
  unique piece types. No castling, no en passant. Spartan pawns are *Hoplites*.

Spartan back rank (a8-h8):  L G K C C K W L
Spartan 7th rank (a7-h7):   eight Hoplites.

Spartan pieces (Betza, from the inventor's page)
------------------------------------------------
* **General "G"** = RF  -- moves as a Rook, or one square diagonally (rook + king).
* **Warlord "W"** = BN  -- moves as a Bishop, or leaps as a Knight.
* **Captain "C"** = WD  -- moves/captures one OR two squares orthogonally, jumping
  over the first square to reach the second (an unblockable 1- or 2-step rook).
* **Lieutenant "L"** = FAsmW -- moves/captures one OR two squares DIAGONALLY,
  jumping over the first; AND may move (but NOT capture) one square sideways.
* **Hoplite "H"** -- the Spartan pawn: moves one square diagonally forward
  (non-capture), captures one square straight forward.  On its first move it may
  go one OR two squares diagonally forward, jumping the first square, but may not
  capture on that move.  Promotes on the 8th rank (see below).
* **King "K"** -- an orthodox king (one square any direction).

The two-King mechanic (the signature rule)
-------------------------------------------
While the Spartan has **two** Kings in play, a Spartan King is **immune from
check**: the Spartan may move a King onto an attacked square, leave a King under
attack, or expose a King to attack.  The ONLY restriction is **duple-check**: a
Spartan move that leaves **both** Kings attacked at once is illegal.

Because a single Spartan King is en prise, the **Persian may capture a Spartan
King** as an ordinary capture.  Once the Spartan is down to **one** King, that
King reverts to an orthodox royal (ordinary check / checkmate apply).

Win / loss
----------
* **Spartans win** by checkmating the Persian King (orthodox).
* **Persians win** by (a) capturing one Spartan King and checkmating the other,
  or (b) placing both Spartan Kings under simultaneous attack such that the
  Spartan, on his move, cannot remove at least one from attack ("duple-check &
  mate").  Mechanically: the Spartan side to move has no legal move while *in
  danger* (its sole King attacked, OR -- with two Kings -- both attacked) -> the
  Spartan loses; no legal move while NOT in danger -> stalemate (draw).

Hoplite promotion
-----------------
A Hoplite reaching the 8th rank (row 0, since Black advances toward row 0)
promotes to any Spartan piece -- G, W, C or L -- and **may promote to a King only
if the Spartan currently has exactly one King in play** (regaining a second King).
Persian pawns promote orthodoxly to Q/R/B/N.

Wiring on ``agp.chesslike``
---------------------------
* G, W, C and the Lieutenant's *capturing* (diagonal) component live in ``PIECES``
  so the inherited ``attacked()`` is correct for them.  The Lieutenant's sideways
  *non-capture* step and the Hoplite are added in an overridden ``_pseudo`` and
  ``attacked`` (the Hoplite's straight-ahead capture).
* Both Persian and Spartan Kings use letter ``"K"`` (distinguished by colour), so
  ``"K": ([], ALL8)`` in ``PIECES`` makes every King a correct 1-step attacker.
* ``_in_danger(board, player)`` encodes royalty: Persian = orthodox single-King
  check; Spartan = single-King check OR (two Kings) BOTH attacked.  ``_legal``
  filters every move through ``not _in_danger(after, mover)``.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, StandardCastling,
    PromotionRules, ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# Persian (White) orthodox back rank.
PERSIAN_BACK = ["R", "N", "B", "Q", "K", "B", "N", "R"]
# Spartan (Black) back rank a8-h8:  L G K C C K W L
# (Kings c8/f8, General b8, Warlord g8, Captains d8/e8, Lieutenants a8/h8).
SPARTAN_BACK = ["L", "G", "K", "C", "C", "K", "W", "L"]

# Captain WD: one/two squares orthogonally, jumping (unblockable leaps).
WD_LEAPS = [(1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)]
# Lieutenant capturing component FA: one/two squares diagonally, jumping.
FA_LEAPS = [(1, 1), (1, -1), (-1, 1), (-1, -1), (2, 2), (2, -2), (-2, 2), (-2, -2)]
# Lieutenant sideways non-capture step (move only).
SIDE_STEPS = [(1, 0), (-1, 0)]

# Spartan promotion targets that are NOT a King.
SPARTAN_PROMO = ("G", "W", "C", "L")


def _fwd(player: int) -> int:
    return 1 if player == WHITE else -1


class PersianPawnPromotion(LastRankPromotion):
    """Persian pawns are orthodox (promote to Q/R/B/N on the last rank).  The
    Hoplite is letter ``"H"``, not ``"P"``, so this never fires for a Hoplite --
    Hoplite promotion is handled directly in the game's ``legal_moves``/apply."""


class SpartanChess(ChessLike):
    uid = "spartan_chess"
    name = "Spartan Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600

    PIECES = {
        # Persian orthodox pieces.
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT),
        # Kings (both sides; one-step all directions -- correct attacker for both).
        "K": ([], ALL8),
        # Spartan pieces.
        "G": (ORTHO, DIAG),        # General = Rook + Ferz (rook or one diagonal step)
        "W": (DIAG, KNIGHT),       # Warlord = Bishop + Knight
        "C": ([], WD_LEAPS),       # Captain = WD (1/2 orthogonal jumping leaps)
        "L": ([], FA_LEAPS),       # Lieutenant CAPTURING part = FA (1/2 diagonal jumping)
        # "H" (Hoplite) is intentionally absent -- handled custom (see _pseudo/attacked).
    }
    # Mating material: list everything that can appear so we never declare a bogus
    # insufficient-material draw (the two-King logic makes the orthodox heuristic
    # meaningless anyway -- see _insufficient).
    HEAVY = ("P", "R", "Q", "N", "B", "H", "G", "W", "C", "L", "K")
    PAWN = StandardPawn(white_start=1, black_start=6)   # for Persian "P" only
    PROMOTION = PersianPawnPromotion(("Q", "R", "B", "N"))
    CASTLING = StandardCastling()                       # only Persians can castle

    # ---- setup --------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, PERSIAN_BACK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "H")            # Hoplites
            b[(c, 7)] = (BLACK, SPARTAN_BACK[c])
        return b

    def initial_state(self, options=None, rng=None):
        st = super().initial_state(options, rng)
        # Only the Persian (White) may castle; strip any Black rights.
        st.castling = frozenset("KQ")
        st.reps = {self._poskey_state(st): 1}
        return st

    # ---- royalty / danger ---------------------------------------------------
    def _kings(self, board, player):
        return [(c, r) for (c, r), (pl, t) in board.items()
                if pl == player and t == "K"]

    def _king(self, board, player):
        """First king square (used by ChessLike.in_check & by castling).  For a
        two-King Spartan side this returns *a* king; danger is decided by
        ``_in_danger`` which inspects all kings."""
        ks = self._kings(board, player)
        return ks[0] if ks else None

    def _in_danger(self, board, player) -> bool:
        """``player`` is "in danger" (the side-to-move-loses-if-stuck condition).

        Persian (single King): orthodox -- King attacked.
        Spartan with ONE King: orthodox -- that King attacked.
        Spartan with TWO Kings: check-immune -- in danger ONLY if BOTH are
        attacked (duple-check).
        """
        kings = self._kings(board, player)
        if not kings:
            return False
        enemy = 1 - player
        attacked = [self.attacked(board, c, r, enemy) for (c, r) in kings]
        if len(kings) >= 2:
            return all(attacked)        # duple-check: every king attacked
        return attacked[0]

    # ---- attacks (add Hoplite straight-ahead capture) -----------------------
    def attacked(self, board, c, r, by) -> bool:
        # Inherited: PIECES (R B Q N K G W C L) + the Persian pawn strategy.
        if super().attacked(board, c, r, by):
            return True
        # Hoplite captures one square STRAIGHT ahead, so it attacks the square
        # directly in front of it.  A "by"-Hoplite sits one rank behind (c,r).
        return board.get((c, r - _fwd(by))) == (by, "H")

    # ---- move generation ----------------------------------------------------
    def _hoplite_moves(self, board, c, r, player):
        """Hoplite pseudo-moves: diagonal-forward non-capture (one square, or two
        on the first move, jumping the first); straight-forward capture only."""
        fwd = _fwd(player)
        start = 1 if player == WHITE else self.HEIGHT - 2   # home rank (Black: row 6)
        # Diagonal-forward NON-capturing step(s).
        for dc in (-1, 1):
            one = (c + dc, r + fwd)
            if self.on(*one) and one not in board:
                yield (c, r), one
            # The initial double step is a JUMPING move: per the inventor's rules
            # ("the two-square movement is also a jumping movement ... it can hop
            # over intervening pieces"), the intermediate diagonal square may be
            # occupied -- only the destination must be empty (it never captures).
            if r == start:
                two = (c + 2 * dc, r + 2 * fwd)
                if self.on(*two) and two not in board:
                    yield (c, r), two
        # Straight-forward CAPTURE only.
        cap = (c, r + fwd)
        if self.on(*cap):
            occ = board.get(cap)
            if occ is not None and occ[0] != player:
                yield (c, r), cap

    def _pseudo(self, state):
        board, player = state.board, state.to_move
        ep_target = state.ep[0] if state.ep else None
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "P":
                yield from self.PAWN.pseudo(self, board, c, r, player, ep_target)
                continue
            if t == "H":
                yield from self._hoplite_moves(board, c, r, player)
                continue
            if t == "L":
                # Lieutenant: diagonal FA captures/moves (from PIECES leaps) ...
                for dc, dr in FA_LEAPS:
                    tc, tr = c + dc, r + dr
                    if self.on(tc, tr) and (board.get((tc, tr)) or (None,))[0] != player:
                        yield (c, r), (tc, tr)
                # ... plus a sideways step that may NOT capture.
                for dc, dr in SIDE_STEPS:
                    s = (c + dc, r + dr)
                    if self.on(*s) and s not in board:
                        yield (c, r), s
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
        """Board after a (non-castling) move, for danger testing.  Override
        ChessLike's auto-queen logic: only PERSIAN pawns ("P") auto-promote for
        the safety preview; Hoplites are handled explicitly and never reach here
        as a promotion (their real promotion is materialised in apply_move)."""
        b = dict(board)
        pl, t = b.pop(frm)
        if t == "P" and ep is not None and to == ep[0] and to not in board:
            b.pop(ep[1], None)
        if t == "P" and (to[1] == self.HEIGHT - 1 and pl == WHITE
                         or to[1] == 0 and pl == BLACK):
            t = self.PROMOTION.safety_piece()
        b[to] = (pl, t)
        return b

    def _legal(self, state):
        """Every move must leave the mover NOT in danger.  This is orthodox for the
        Persian and for a one-King Spartan; for a two-King Spartan it only forbids
        moves that leave BOTH kings attacked (duple-check)."""
        player = state.to_move
        moves = []
        for frm, to in self._pseudo(state):
            nb = self._apply_board(state.board, frm, to, state.ep)
            if not self._in_danger(nb, player):
                moves.append((frm, to))
        for frm, to in self.CASTLING.moves(self, state):
            # Only the Persian castles; build the post-castle board (rook follows).
            b = dict(state.board)
            pl, t = b.pop(frm)
            b[to] = (pl, t)
            rook = self.CASTLING.rook_move(frm, to, pl)
            if rook is not None:
                b[rook[1]] = b.pop(rook[0])
            if not self._in_danger(b, player):
                moves.append((frm, to))
        return moves

    # ---- promotion (Hoplite + Persian pawn) ---------------------------------
    def _hoplite_promo_options(self, state, frm, to):
        """Promotion choices when a Hoplite reaches the 8th rank (row 0).  Always
        G/W/C/L; King ("K") is allowed ONLY if the Spartan has exactly one King."""
        if to[1] != 0:
            return [None]
        opts = list(SPARTAN_PROMO)
        n_kings = len(self._kings(state.board, BLACK))
        # The Hoplite is about to leave the board as a Hoplite; count current kings.
        if n_kings == 1:
            opts.append("K")
        return opts

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        out = []
        for f, t in self._legal(state):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            piece = state.board[f][1]
            if piece == "P":
                for ch in self.PROMOTION.options(self, state, f, t):
                    out.append(base if ch is None else base + "=" + ch)
            elif piece == "H":
                for ch in self._hoplite_promo_options(state, f, t):
                    out.append(base if ch is None else base + "=" + ch)
            else:
                out.append(base)
        return out

    # ---- apply (Hoplite promotion materialisation) --------------------------
    def apply_move(self, state, move, rng=None):
        promo = None
        raw = move
        if "=" in raw:
            raw, promo = raw.split("=")
        fs, ts = raw.split(">")
        frm = tuple(int(x) for x in fs.split(","))
        pl, t = state.board[frm]
        if t == "H":
            return self._apply_hoplite(state, frm, ts, promo)
        return super().apply_move(state, move, rng)

    def _apply_hoplite(self, state, frm, ts, promo):
        to = tuple(int(x) for x in ts.split(","))
        pl = state.board[frm][0]
        b = dict(state.board)
        b.pop(frm)
        capture = to in state.board
        t = promo if promo else "H"
        b[to] = (pl, t)
        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        # A Hoplite move is always a "progress" move (pawn-type) -> reset halfmove.
        key = self._poskey(b, 1 - pl, castling, None, None)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=None,
                      halfmove=0, ply=state.ply + 1, reps=reps,
                      hands={}, promoted=frozenset())

    # ---- terminal / result --------------------------------------------------
    def _insufficient(self, board) -> bool:
        # The orthodox lone-minor heuristic is meaningless with two royals and
        # unorthodox material; rely on 50-move / repetition / ply-cap draws.
        return False

    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        return not self._legal(state)

    def returns(self, state) -> list:
        # No legal move while NOT in danger -> stalemate (draw); otherwise the side
        # to move is (check / duple-)mated and loses.
        if self._draw(state) or not self._in_danger(state.board, state.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        raw, promo = (move.split("=") + [None])[:2]
        fs, ts = raw.split(">")
        frm = tuple(int(x) for x in fs.split(","))
        to = tuple(int(x) for x in ts.split(","))
        pl, t = state.board.get(frm, (None, "?"))
        if t == "K" and self.CASTLING.rook_move(frm, to, pl) is not None:
            return "O-O" if to[0] > frm[0] else "O-O-O"
        files = "abcdefgh"
        alg = lambda c: f"{files[c[0]]}{c[1] + 1}"  # noqa: E731
        capture = to in state.board
        text = f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}"
        return text + (f"={promo}" if promo else "")

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {WHITE: "Persians", BLACK: "Spartans"}
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                spec["caption"] = "Draw"
            else:
                w = 0 if ret[0] > 0 else 1
                spec["caption"] = f"{names[w]} win"
        else:
            p = state.to_move
            danger = self._in_danger(state.board, p)
            tag = ""
            if danger:
                if p == BLACK and len(self._kings(state.board, BLACK)) >= 2:
                    tag = " (duple-check)"
                else:
                    tag = " (check)"
            spec["caption"] = f"{names[p]} to move{tag}"
        return spec
