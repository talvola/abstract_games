"""Metamachy (Jean-Louis Cazaux, 2012) -- 12x12, built on the shared ChessLike core.

Sources of truth:
  * https://www.chessvariants.com/rules/metamachy (H.G. Muller & J.-L. Cazaux,
    incl. the Interactive-Diagram definition with exact Betza moves and setup)
  * http://history.chess.free.fr/metamachy.htm (Cazaux's own site)

60 pieces in total: each side has 1 King, 1 Queen, 1 Eagle, 1 Lion,
2 Princes, 2 Bishops, 2 Knights, 2 Camels, 2 Rooks, 2 Cannons, 2 Elephants
and 12 Pawns (30 pieces per side, 12 types).

Pieces (letters as in the chessvariants.com diagram):

  * **K King** -- royal, one step any direction.  NO castling; instead, on its
    FIRST move only it may leap two squares away in any of the 16 directions
    (orthogonal, diagonal, or knight-wise) to an EMPTY square, jumping over
    anything.  The jump is forbidden while in check, and forbidden if the
    square jumped over is threatened (for the knight jump there are two
    intermediate squares -- orthogonally- and diagonally-adjacent -- and BOTH
    must be threatened to prevent the jump).  "Threatened" is tested as: the
    King could not have legally stood on that square had it been empty.
  * **Q Queen / R Rook / B Bishop / N Knight** -- as in orthodox chess.
  * **G Eagle** -- the Gryphon/Aanca bent rider: one square diagonally, then
    outward orthogonally any distance.  May stop after the diagonal step; the
    first obstacle on the path blocks (an enemy on it can be captured, even at
    the bend); it never jumps.
  * **L Lion** -- leaps directly to any of the 24 squares within two king
    steps (Chebyshev distance <= 2); blocking is irrelevant.  (The Chu-Shogi
    "lioness": no double capture.)
  * **C Cannon** -- Xiangqi cannon: moves (without capturing) like a rook
    along empty lines; captures only by jumping exactly one screen (either
    colour) and taking the first piece beyond it.
  * **E Elephant** -- Ferz + Alfil: one step diagonally, or a two-square
    diagonal leap (jumping over the intermediate square).
  * **A Camel** -- (1,3) leaper.
  * **M Prince** -- a non-royal king (one step any direction, capturing or
    not), plus a NON-capturing straight-forward double step from ANY square
    (the passed square must be empty).  Promotes like a pawn on the last rank.
    A double-stepping Prince can be captured en passant BY A PAWN, but a
    Prince can never capture en passant itself.
  * **P Pawn** -- steps one square straight forward without capturing,
    captures one square diagonally forward, and may make a NON-capturing
    double step from ANY square (not just its home rank; the passed square
    must be empty).  En passant applies after every double step.

Promotion: a Pawn or Prince reaching the last rank MUST promote to a Queen,
Eagle or Lion (free choice; no other type allowed).

Setup (White, files a..l = cols 0..11; Black mirrors on the same files):

    rank 3 :  P P P P P P P P P P P P
    rank 2 :  E R N B M L G M B N R E
    rank 1 :  C A . . . Q K . . . A C

The real game lets Black permute King/Queen/Lion/Eagle over f12,g12,f11,g11
(12 essentially different setups, White mirroring); this port fixes the
Interactive Diagram's default array (Q f1, K g1, Lion f2, Eagle g2) -- see
rules.md.

Checkmate wins; stalemate is a draw; 50-move rule, threefold repetition and a
hard ply cap draw.  White = player 0, moving toward higher rows.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, Castling, cell,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
DABBABA = [(2, 0), (-2, 0), (0, 2), (0, -2)]
CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]
# Lion: every square within two king steps (K + Dabbaba + Alfil + Knight = 24).
LION = ALL8 + DABBABA + ALFIL + KNIGHT
# King's one-time jump: exactly two squares away in all 16 directions.
KING_JUMP = DABBABA + ALFIL + KNIGHT


class MetamachyPawn(StandardPawn):
    """Orthodox pawn except the non-capturing double step is available from ANY
    square (the passed square must be empty), and en passant therefore applies
    anywhere on the board.  ``ep_after`` (inherited) marks the passed square."""

    def pseudo(self, core, board, c, r, player, ep_target):
        fwd = self.fwd(player)
        if core.on(c, r + fwd) and (c, r + fwd) not in board:
            yield (c, r), (c, r + fwd)
            if core.on(c, r + 2 * fwd) and (c, r + 2 * fwd) not in board:
                yield (c, r), (c, r + 2 * fwd)
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if (occ is not None and occ[0] != player) or t == ep_target:
                yield (c, r), t


class KingJump(Castling):
    """Metamachy's replacement for castling: while a king has never moved it
    may leap two squares away in any of the 16 directions to an EMPTY square,
    jumping over occupied squares.  Restrictions (chessvariants.com):

      * not allowed while in check;
      * the square jumped over must be one the king could have legally moved
        to had it been empty (i.e. not threatened); a knight jump has TWO
        such intermediate squares and only needs ONE of them safe;
      * the destination must be empty and safe (normal king-safety).

    Rights ride in ``state.castling`` as single chars "W"/"B" (cleared the
    moment the king moves), so the base serialize round-trips them."""

    FLAG = {WHITE: "W", BLACK: "B"}

    def initial_rights(self) -> frozenset:
        return frozenset(self.FLAG.values())

    @staticmethod
    def _mids(k, dc, dr):
        """Intermediate square(s) jumped over for offset (dc, dr)."""
        kc, kr = k
        if abs(dc) == 1:      # (1,2) knight jump: orthogonal- and diagonal-adjacent
            return [(kc, kr + dr // 2), (kc + dc, kr + dr // 2)]
        if abs(dr) == 1:      # (2,1) knight jump
            return [(kc + dc // 2, kr), (kc + dc // 2, kr + dr)]
        return [(kc + dc // 2, kr + dr // 2)]     # (2,0) / (0,2) / (2,2)

    @staticmethod
    def _mid_ok(core, board, player, k, mid):
        """Could the king have legally moved to ``mid`` had it been empty?"""
        b = dict(board)
        b.pop(k)
        b.pop(mid, None)                 # "had that square been empty"
        b[mid] = (player, "K")
        return not core.in_check(b, player)

    def moves(self, core, state):
        player = state.to_move
        if self.FLAG[player] not in state.castling:
            return
        k = core._king(state.board, player)
        if k is None or core.in_check(state.board, player):
            return                        # may not jump out of check
        for dc, dr in KING_JUMP:
            to = (k[0] + dc, k[1] + dr)
            if not core.on(*to) or to in state.board:   # non-capturing
                continue
            if not any(self._mid_ok(core, state.board, player, k, m)
                       for m in self._mids(k, dc, dr)):
                continue
            b = dict(state.board)
            b.pop(k)
            b[to] = (player, "K")
            if not core.in_check(b, player):
                yield k, to

    def rook_move(self, frm, to, player):
        return None                       # no rook is involved

    def update_rights(self, rights, frm, to, board):
        pl, t = board[frm]
        if t == "K" and self.FLAG[pl] in rights:
            return frozenset(rights - {self.FLAG[pl]})
        return rights


class Metamachy(ChessLike):
    name = "Metamachy"

    WIDTH = HEIGHT = 12
    PLY_CAP = 800
    PIECES = {
        "R": (ORTHO, []),
        "B": (DIAG, []),
        "Q": (ALL8, []),
        "N": ([], KNIGHT),
        "K": ([], ALL8),
        "E": ([], DIAG + ALFIL),   # Elephant: ferz step + alfil leap
        "A": ([], CAMEL),          # Camel: (1,3) leaper
        "L": ([], LION),           # Lion: leap anywhere within 2 king steps
        "M": ([], ALL8),           # Prince: king steps (double push added in _pseudo)
        "C": ([], []),             # Cannon -- custom (_pseudo / attacked)
        "G": ([], []),             # Eagle (gryphon) -- custom (_pseudo / attacked)
    }
    HEAVY = ("P", "R", "Q", "M", "E", "A", "C", "G", "L")
    # Cazaux's own "more realistic" values (history.chess.free.fr/metamachy.htm).
    PIECE_VALUES = {"P": 1.0, "A": 2.0, "E": 2.5, "N": 2.5, "M": 3.5, "B": 3.5,
                    "C": 4.0, "R": 5.0, "L": 7.5, "G": 8.0, "Q": 9.0, "K": 0.0}
    PAWN = MetamachyPawn(white_start=2, black_start=9)
    PROMOTION = LastRankPromotion(("Q", "G", "L"))
    CASTLING = KingJump()          # no castling; the king's one-time jump instead

    # ---- setup ---------------------------------------------------------------
    # Files a..l = cols 0..11.  The default array of the source's Interactive
    # Diagram: Queen f1, King g1, Lion f2, Eagle g2 (Black mirrors on the same
    # files: Q f12, K g12, L f11, G g11).
    RANK1 = ["C", "A", None, None, None, "Q", "K", None, None, None, "A", "C"]
    RANK2 = ["E", "R", "N", "B", "M", "L", "G", "M", "B", "N", "R", "E"]

    def setup_board(self) -> dict:
        b = {}
        for c in range(12):
            if self.RANK1[c]:
                b[(c, 0)] = (WHITE, self.RANK1[c])
                b[(c, 11)] = (BLACK, self.RANK1[c])
            if self.RANK2[c]:
                b[(c, 1)] = (WHITE, self.RANK2[c])
                b[(c, 10)] = (BLACK, self.RANK2[c])
            b[(c, 2)] = (WHITE, "P")
            b[(c, 9)] = (BLACK, "P")
        return b

    # ---- custom piece geometry ------------------------------------------------
    def _cannon_targets(self, board, c, r, player):
        """Xiangqi cannon: slide along empty orthogonal lines without capturing;
        capture by hopping exactly one screen and taking the first piece beyond."""
        for dc, dr in ORTHO:
            cc, rr = c + dc, r + dr
            while self.on(cc, rr) and (cc, rr) not in board:
                yield (cc, rr)                       # rider move, no capture
                cc += dc
                rr += dr
            if not self.on(cc, rr):
                continue
            cc += dc                                 # hop over the screen
            rr += dr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] != player:
                        yield (cc, rr)               # hop capture
                    break
                cc += dc
                rr += dr

    def _eagle_targets(self, board, c, r, player):
        """Eagle/Gryphon: one diagonal step (may stop there, capturing an enemy
        at the bend), then -- only if the bend square was empty -- an outward
        orthogonal slide in either of the two directions leading away from the
        origin.  The first obstacle blocks; no jumping."""
        for dc, dr in DIAG:
            bend = (c + dc, r + dr)
            if not self.on(*bend):
                continue
            occ = board.get(bend)
            if occ is not None:
                if occ[0] != player:
                    yield bend                       # capture at the bend
                continue                             # blocked: no slide beyond
            yield bend
            for ddc, ddr in ((dc, 0), (0, dr)):
                cc, rr = bend[0] + ddc, bend[1] + ddr
                while self.on(cc, rr):
                    o2 = board.get((cc, rr))
                    if o2 is None:
                        yield (cc, rr)
                    else:
                        if o2[0] != player:
                            yield (cc, rr)
                        break
                    cc += ddc
                    rr += ddr

    # ---- move generation -------------------------------------------------------
    def _pseudo(self, state):
        yield from super()._pseudo(state)      # pawns, sliders, leapers, king steps
        board, player = state.board, state.to_move
        fwd = 1 if player == WHITE else -1
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "M":
                # non-capturing double push from anywhere; passed square empty
                one, two = (c, r + fwd), (c, r + 2 * fwd)
                if self.on(*two) and one not in board and two not in board:
                    yield (c, r), two
            elif t == "C":
                for to in self._cannon_targets(board, c, r, player):
                    yield (c, r), to
            elif t == "G":
                for to in self._eagle_targets(board, c, r, player):
                    yield (c, r), to

    def attacked(self, board, c, r, by) -> bool:
        if super().attacked(board, c, r, by):
            return True
        # Cannon: (c, r) is attacked if, scanning outward, the FIRST piece is a
        # screen and the SECOND is an enemy cannon (plain cannon moves don't
        # capture, so only the hop pattern attacks).
        for dc, dr in ORTHO:
            cc, rr = c + dc, r + dr
            while self.on(cc, rr) and (cc, rr) not in board:
                cc += dc
                rr += dr
            if not self.on(cc, rr):
                continue
            cc += dc
            rr += dr
            while self.on(cc, rr) and (cc, rr) not in board:
                cc += dc
                rr += dr
            if self.on(cc, rr) and board[(cc, rr)] == (by, "C"):
                return True
        # Eagle: forward generation from each enemy eagle (its capture set equals
        # its move set).
        for (ec, er), (pl, t) in board.items():
            if pl == by and t == "G":
                if (c, r) in self._eagle_targets(board, ec, er, by):
                    return True
        return False

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        out = []
        for f, t in self._legal(state):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if state.board[f][1] in ("P", "M"):     # Princes promote like pawns
                for ch in self.PROMOTION.options(self, state, f, t):
                    out.append(base if ch is None else base + "=" + ch)
            else:
                out.append(base)
        return out

    # ---- apply (base minus drops/rooks, plus Prince double-push ep + promotion)
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
        if t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                b.pop(state.ep[1], None)             # en passant (pawn or prince)
                capture = True
            elif promo is None:
                ep_new = self.PAWN.ep_after(frm, to)
        elif (t == "M" and promo is None
              and frm[0] == to[0] and abs(to[1] - frm[1]) == 2):
            # Prince double push: capturable en passant (by pawns only)
            ep_new = ((frm[0], (frm[1] + to[1]) // 2), to)
        if promo:
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

    # ---- insufficient material -------------------------------------------------
    def _insufficient(self, board) -> bool:
        """Conservative: bare kings, or a lone piece that provably cannot mate
        (B/N single minor; E and A are colourbound short-range/leaper).  A lone
        Cannon (needs a screen) or Prince plays on -- the 50-move rule,
        repetition and the ply cap still guarantee termination."""
        rest = [t for (_, t) in board.values() if t != "K"]
        if not rest:
            return True
        return len(rest) == 1 and rest[0] in ("B", "N", "E", "A")
