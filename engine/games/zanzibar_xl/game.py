"""Zanzibar-XL (Jean-Louis Cazaux, 2020) -- a 12x12 great-chess variant with 19
piece types and a player-chosen opening setup, built on the shared ChessLike core.

Sources of truth:
  * https://ftp.chessvariants.com/rules/zanzibar-xl  (Cazaux; incl. H.G. Muller's
    Interactive-Diagram definition with the exact Betza moves and default array)
  * https://www.chessvariants.com/rules/zanzibar-s   (the sibling small version)

80 pieces total (40 per side, 19 types): 1 King, 1 Queen, 1 Eagle, 1 Lion,
1 Duchess, 1 Sorceress, 1 Rhinoceros, 1 Buffalo, 2 Princes, 2 Bishops,
2 Knights, 2 Camels, 2 Rooks, 2 Cannons, 2 Elephants, 2 Giraffes, 2 Archers,
2 Machines and 12 Pawns.

Piece letters (as used internally; the frontend draws real glyphs only for the
orthodox K/Q/R/B/N/P and falls back to the letter for the fairy pieces):

  * **K King** -- royal, one step any direction.  NO castling; instead, on its
    FIRST move only, it may leap two squares away in any of the 16 directions
    (orthogonal, diagonal or knight-wise) to an EMPTY square, jumping over any
    occupant.  Forbidden while in check and forbidden over a threatened square
    (a knight jump has two intermediates and needs only ONE safe).  Identical to
    Metamachy.  (Betza ``KimAimDimN``.)
  * **Q Queen / R Rook / B Bishop / N Knight** -- as in orthodox chess.
  * **G Eagle** -- the Gryphon/Aanca bent rider: one diagonal step, then an
    outward orthogonal slide (may stop at the bend; never jumps).  (``FyafsF``.)
  * **U Rhinoceros** -- the counterpart bent rider: one orthogonal step, then an
    outward diagonal slide.  (``WyafsW``.)
  * **L Lion** -- leaps to any of the 24 squares within two king steps
    (Chebyshev <= 2); blocking is irrelevant.  (``KNAD``.)
  * **E Elephant** -- Ferz + Alfil: one step diagonally, or a two-square diagonal
    leap over the intermediate square.  (``FA``.)
  * **A Camel** -- (1,3) leaper.  (``C`` in Betza.)
  * **Z Giraffe** -- (2,3) leaper (a "zebra").  (``Z``.)
  * **W Machine** -- Wazir + Dabbaba: one or two squares orthogonally, leaping the
    first square if occupied (the orthogonal counterpart of the Elephant).
    (``WD``.)
  * **M Prince** -- a non-royal king (one step any direction, capturing or not),
    plus a NON-capturing straight-forward double step from ANY square (the passed
    square must be empty).  Promotes like a pawn.  (``KfmnnD``.)
  * **C Cannon** -- Xiangqi cannon: moves (without capturing) like a rook along
    empty files/ranks; captures by hopping exactly one screen (either colour) and
    taking the first piece beyond it.  (``mRcpR``.)
  * **V Archer** -- the diagonal cannon (Vao): moves like a bishop without
    capturing; captures by hopping one screen along a diagonal.  (``mBcpB``.)
  * **O Sorceress** -- the queen-line cannon (Cannon + Archer): moves like a queen
    without capturing; captures by hopping one screen along any rank/file/diagonal.
    (``mQcpQ``.)
  * **D Duchess** -- steps or LEAPS one, two or three squares in any of the eight
    queen directions (jumping over intermediate squares on a 2- or 3-step).
    (``KADGH``.)
  * **F Buffalo** -- Knight + Camel + Giraffe = (2,1)+(3,1)+(3,2) leaper.  (``NCZ``.)
  * **P Pawn** -- steps one square straight forward without capturing, captures one
    square diagonally forward, and may make a NON-capturing double step from ANY
    square (the passed square must be empty).  En passant applies after every
    double step (by pawns only).  Identical to Metamachy.

Promotion: a Pawn or Prince reaching the last rank MUST become a "chief" -- a
Queen, Eagle, Lion, Duchess, Sorceress, Rhinoceros or Buffalo (free choice; no
other type).

Opening setup (the game's signature): the paired pieces and the pawns start on a
fixed formation; then Black freely arranges its King/Queen/Eagle/Lion on the four
centre squares f12,g12,f11,g11 and its Duchess/Sorceress/Rhinoceros/Buffalo on the
four flank squares e12,h12,e11,h11.  White's chiefs are then placed in mirror
symmetry (Black K on f12 -> White K on f1) and White makes the first move.  This
port models the arrangement as a sequence of explicit placement moves by Black
(the reserve is shown as a drop tray); the mirror is applied automatically once
Black has placed all eight chiefs.

Checkmate wins; stalemate is a draw; the 50-move rule, threefold repetition and a
hard ply cap draw.  White = player 0, advancing toward higher rows.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, Castling, cell,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# ---- fairy leap sets --------------------------------------------------------
ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
DABBABA = [(2, 0), (-2, 0), (0, 2), (0, -2)]
CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]
ZEBRA = [(2, 3), (3, 2), (-2, 3), (-3, 2), (2, -3), (3, -2), (-2, -3), (-3, -2)]
# Lion: every square within two king steps (K + Dabbaba + Alfil + Knight = 24).
LION = ALL8 + DABBABA + ALFIL + KNIGHT
# King's one-time jump: exactly two squares away in all 16 directions.
KING_JUMP = DABBABA + ALFIL + KNIGHT
# Buffalo: Knight + Camel + Giraffe.
BUFFALO = KNIGHT + CAMEL + ZEBRA
# Machine: Wazir + Dabbaba (1 or 2 orthogonally, leaping the near square).
MACHINE = ORTHO + DABBABA
# Elephant: Ferz + Alfil (1 or 2 diagonally).
ELEPHANT = DIAG + ALFIL
# Duchess: 1, 2 or 3 squares along any of the eight queen rays (leaps over
# intermediates on the 2- and 3-step).
DUCHESS = [(dx * k, dy * k) for (dx, dy) in (ORTHO + DIAG) for k in (1, 2, 3)]

_FILES = "abcdefghijkl"


class ZanzibarPawn(StandardPawn):
    """Metamachy "rapid" pawn: the non-capturing double step is available from ANY
    square (the passed square must be empty); en passant therefore applies
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
    """Zanzibar's replacement for castling (identical to Metamachy): while a king
    has never moved it may leap two squares away in any of the 16 directions to an
    EMPTY square, jumping over occupied squares.  Restrictions:

      * not allowed while in check;
      * the square jumped over must be one the king could have legally moved to
        had it been empty (i.e. not threatened); a knight jump has TWO such
        intermediate squares and only needs ONE of them safe;
      * the destination must be empty and safe.

    Rights ride in ``state.castling`` as single chars "W"/"B" (cleared the moment
    the king moves)."""

    FLAG = {WHITE: "W", BLACK: "B"}

    def initial_rights(self) -> frozenset:
        return frozenset(self.FLAG.values())

    @staticmethod
    def _mids(k, dc, dr):
        kc, kr = k
        if abs(dc) == 1:      # (1,2) knight jump
            return [(kc, kr + dr // 2), (kc + dc, kr + dr // 2)]
        if abs(dr) == 1:      # (2,1) knight jump
            return [(kc + dc // 2, kr), (kc + dc // 2, kr + dr)]
        return [(kc + dc // 2, kr + dr // 2)]     # (2,0) / (0,2) / (2,2)

    @staticmethod
    def _mid_ok(core, board, player, k, mid):
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
            return
        for dc, dr in KING_JUMP:
            to = (k[0] + dc, k[1] + dr)
            if not core.on(*to) or to in state.board:      # non-capturing
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
        return None

    def update_rights(self, rights, frm, to, board):
        pl, t = board[frm]
        if t == "K" and self.FLAG[pl] in rights:
            return frozenset(rights - {self.FLAG[pl]})
        return rights


class ZanzibarXL(ChessLike):
    uid = "zanzibar_xl"
    name = "Zanzibar-XL"

    WIDTH = HEIGHT = 12
    PLY_CAP = 350
    PIECESET = "chess"        # KQRBNP get glyphs; fairy letters fall back to text
    PIECES = {
        "R": (ORTHO, []),
        "B": (DIAG, []),
        "Q": (ALL8, []),
        "N": ([], KNIGHT),
        "K": ([], ALL8),
        "E": ([], ELEPHANT),       # Elephant: ferz step + alfil leap
        "A": ([], CAMEL),          # Camel: (1,3) leaper
        "Z": ([], ZEBRA),          # Giraffe: (2,3) leaper
        "F": ([], BUFFALO),        # Buffalo: N + Camel + Giraffe
        "W": ([], MACHINE),        # Machine: wazir + dabbaba leap
        "D": ([], DUCHESS),        # Duchess: 1/2/3 along the 8 queen rays (leaping)
        "L": ([], LION),           # Lion: leap anywhere within 2 king steps
        "M": ([], ALL8),           # Prince: king steps (double push added in _pseudo)
        "C": ([], []),             # Cannon  -- custom (orthogonal pao)
        "V": ([], []),             # Archer  -- custom (diagonal pao / Vao)
        "O": ([], []),             # Sorceress -- custom (queen-line pao)
        "G": ([], []),             # Eagle   -- custom (diagonal-then-orthogonal rider)
        "U": ([], []),             # Rhinoceros -- custom (orthogonal-then-diagonal rider)
    }
    HEAVY = tuple("PQRBNGULCEAZFWDOMV")
    # Cazaux's "more realistic" values (from the rules page), royals at 0.
    PIECE_VALUES = {
        "P": 1.0, "Z": 2.0, "A": 2.0, "E": 2.5, "N": 2.5, "W": 3.0, "V": 3.0,
        "M": 3.5, "B": 3.5, "C": 4.0, "R": 5.0, "U": 6.0, "O": 6.5, "F": 7.0,
        "D": 7.5, "L": 7.5, "G": 8.0, "Q": 9.0, "K": 0.0,
    }
    PAWN = ZanzibarPawn(white_start=2, black_start=9)
    PROMOTION = LastRankPromotion(("Q", "G", "L", "D", "O", "U", "F"))
    CASTLING = KingJump()

    # ---- fixed opening formation (the pieces that are NOT player-arranged) ----
    # Files a..l = cols 0..11.  Centre squares e..h on ranks 1-2 (and their Black
    # mirrors) are left empty for the eight chiefs.
    RANK1 = ["C", "A", "Z", "V", None, None, None, None, "V", "Z", "A", "C"]
    RANK2 = ["E", "R", "N", "B", None, None, None, None, "B", "N", "R", "E"]
    RANK3 = ["P", "P", "P", "P", "M", "W", "W", "M", "P", "P", "P", "P"]
    RANK4 = [None, None, None, None, "P", "P", "P", "P", None, None, None, None]

    # The eight chiefs Black arranges, and their legal target squares (Black side).
    CENTRE_PIECES = ("K", "Q", "G", "L")               # -> f12,g12,f11,g11
    FLANK_PIECES = ("D", "O", "U", "F")                # -> e12,h12,e11,h11
    CENTRE_SQUARES = frozenset({(5, 11), (6, 11), (5, 10), (6, 10)})
    FLANK_SQUARES = frozenset({(4, 11), (7, 11), (4, 10), (7, 10)})
    CHIEF_SQUARES = CENTRE_SQUARES | FLANK_SQUARES

    _NAMES = {WHITE: "White", BLACK: "Black"}

    # ---- setup phase --------------------------------------------------------
    def _in_setup(self, state) -> bool:
        return any(n > 0 for h in state.hands.values() for n in h.values())

    def _setup_drops(self, state) -> list:
        """Legal ``"L@c,r"`` placements for Black during the arrangement phase:
        each chief still in hand onto an empty square of its allowed group."""
        hand = state.hands.get(BLACK, {})
        out = []
        for L, n in hand.items():
            if n <= 0:
                continue
            squares = self.CENTRE_SQUARES if L in self.CENTRE_PIECES else self.FLANK_SQUARES
            for (c, r) in sorted(squares):
                if (c, r) not in state.board:
                    out.append(f"{L}@{c},{r}")
        return out

    def _apply_setup(self, state, move):
        letter, cs = move.split("@")
        to = cell(cs)
        b = dict(state.board)
        b[to] = (BLACK, letter)
        hand = dict(state.hands.get(BLACK, {}))
        hand[letter] = hand.get(letter, 0) - 1
        if hand[letter] <= 0:
            del hand[letter]

        if hand:                                    # more chiefs to place: Black again
            hands = {BLACK: hand}
            to_move = BLACK
        else:                                       # last chief placed -> mirror + White
            for (c, r), (pl, t) in list(b.items()):
                if pl == BLACK and (c, r) in self.CHIEF_SQUARES:
                    b[(c, self.HEIGHT - 1 - r)] = (WHITE, t)
            hands = {}
            to_move = WHITE

        st = CState(board=b, to_move=to_move, castling=state.castling, ep=None,
                    halfmove=0, ply=state.ply + 1, hands=hands)
        st.reps = {self._poskey_state(st): 1}       # fresh position history
        return st

    # ---- move generation ----------------------------------------------------
    def _cannon_family(self, board, c, r, player, dirs):
        """Pao (cannon-family) generator over the direction set ``dirs``: slide
        (without capturing) along empty lines; capture by hopping exactly one
        screen (either colour) and taking the first piece beyond it."""
        for dc, dr in dirs:
            cc, rr = c + dc, r + dr
            while self.on(cc, rr) and (cc, rr) not in board:
                yield (cc, rr)                      # quiet move
                cc += dc
                rr += dr
            if not self.on(cc, rr):
                continue
            cc += dc                                # hop over the screen
            rr += dr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] != player:
                        yield (cc, rr)              # hop capture
                    break
                cc += dc
                rr += dr

    def _bent_targets(self, board, c, r, player, step_dirs, diagonal_slide):
        """Gryphon-family bent rider: one step along a ``step_dir`` (may stop
        there, capturing an enemy at the bend), then -- only if the bend square
        was empty -- an outward slide in the two directions leading away from the
        origin.  For the Eagle the step is diagonal and the slide orthogonal; for
        the Rhinoceros the step is orthogonal and the slide diagonal."""
        for dc, dr in step_dirs:
            bend = (c + dc, r + dr)
            if not self.on(*bend):
                continue
            occ = board.get(bend)
            if occ is not None:
                if occ[0] != player:
                    yield bend                      # capture at the bend
                continue                            # blocked: no slide beyond
            yield bend
            if diagonal_slide:                      # orthogonal step -> diagonal slide
                slides = [(dc, 1), (dc, -1)] if dc != 0 else [(1, dr), (-1, dr)]
            else:                                   # diagonal step -> orthogonal slide
                slides = [(dc, 0), (0, dr)]
            for ddc, ddr in slides:
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

    def _eagle_targets(self, board, c, r, player):
        return self._bent_targets(board, c, r, player, DIAG, diagonal_slide=False)

    def _rhino_targets(self, board, c, r, player):
        return self._bent_targets(board, c, r, player, ORTHO, diagonal_slide=True)

    def _pseudo(self, state):
        yield from super()._pseudo(state)      # pawns, sliders, leapers, king steps
        board, player = state.board, state.to_move
        fwd = 1 if player == WHITE else -1
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "M":
                one, two = (c, r + fwd), (c, r + 2 * fwd)
                if self.on(*two) and one not in board and two not in board:
                    yield (c, r), two
            elif t == "C":
                for to in self._cannon_family(board, c, r, player, ORTHO):
                    yield (c, r), to
            elif t == "V":
                for to in self._cannon_family(board, c, r, player, DIAG):
                    yield (c, r), to
            elif t == "O":
                for to in self._cannon_family(board, c, r, player, ALL8):
                    yield (c, r), to
            elif t == "G":
                for to in self._eagle_targets(board, c, r, player):
                    yield (c, r), to
            elif t == "U":
                for to in self._rhino_targets(board, c, r, player):
                    yield (c, r), to

    # The five custom pieces whose attacks need ray/hop scans; gating on their
    # presence makes ``attacked`` cheap in the sparse endgames that random games
    # drift into (the single Eagle/Rhino/Sorceress are usually long gone).
    _SPECIALS = frozenset("CVOGU")

    def attacked(self, board, c, r, by) -> bool:
        if super().attacked(board, c, r, by):
            return True
        # Which of the enemy's five custom pieces are on the board at all?
        present = set()
        for (pl, t) in board.values():
            if pl == by and t in self._SPECIALS:
                present.add(t)
                if len(present) == 5:
                    break
        if not present:
            return False
        pao = present & frozenset("CVO")
        has_eagle = "G" in present
        has_rhino = "U" in present
        W, H = self.WIDTH, self.HEIGHT
        bget = board.get
        eagle, rhino = (by, "G"), (by, "U")
        # --- Cannon-family (Cannon/Archer/Sorceress): scan outward; the FIRST
        # piece is a screen and the SECOND, beyond it, is an enemy pao of a type
        # that rides in this direction (C orthogonal, V diagonal, O either).
        for dc, dr in (ALL8 if pao else ()):
            cc, rr = c + dc, r + dr
            while 0 <= cc < W and 0 <= rr < H and (cc, rr) not in board:   # to screen
                cc += dc
                rr += dr
            if not (0 <= cc < W and 0 <= rr < H):
                continue
            cc += dc                                                       # past screen
            rr += dr
            while 0 <= cc < W and 0 <= rr < H and (cc, rr) not in board:   # to shooter
                cc += dc
                rr += dr
            if not (0 <= cc < W and 0 <= rr < H):
                continue
            occ = board[(cc, rr)]
            if occ[0] != by:
                continue
            t = occ[1]
            orth = (dc == 0 or dr == 0)
            if t == "O" or (t == "C" and orth) or (t == "V" and not orth):
                return True
        # --- Eagle (diagonal step then outward orthogonal slide) -- detected by
        # reverse ray-tracing (there is at most one eagle, so no full-board scan).
        if has_eagle:
            for dc, dr in DIAG:                    # capture AT the bend (adjacent)
                if bget((c + dc, r + dr)) == eagle:
                    return True
            for sx, sy in ORTHO:                   # reached by an orthogonal slide
                bc, br = c - sx, r - sy             # walk back toward the empty bend
                while 0 <= bc < W and 0 <= br < H and (bc, br) not in board:
                    if sx != 0:
                        if bget((bc - sx, br - 1)) == eagle or bget((bc - sx, br + 1)) == eagle:
                            return True
                    elif bget((bc - 1, br - sy)) == eagle or bget((bc + 1, br - sy)) == eagle:
                        return True
                    bc -= sx
                    br -= sy
        # --- Rhinoceros (orthogonal step then outward diagonal slide) ---
        if has_rhino:
            for dc, dr in ORTHO:                   # capture AT the bend (adjacent)
                if bget((c + dc, r + dr)) == rhino:
                    return True
            for sx, sy in DIAG:                    # reached by a diagonal slide
                bc, br = c - sx, r - sy
                while 0 <= bc < W and 0 <= br < H and (bc, br) not in board:
                    if bget((bc - sx, br)) == rhino or bget((bc, br - sy)) == rhino:
                        return True
                    bc -= sx
                    br -= sy
        return False

    def legal_moves(self, state) -> list:
        if self._in_setup(state):
            return self._setup_drops(state)
        if self._draw(state):
            return []
        out = []
        for f, t in self._legal(state):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if state.board[f][1] in ("P", "M"):        # Princes promote like pawns
                for ch in self.PROMOTION.options(self, state, f, t):
                    out.append(base if ch is None else base + "=" + ch)
            else:
                out.append(base)
        return out

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        if "@" in move:
            return self._apply_setup(state, move)
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
            ep_new = ((frm[0], (frm[1] + to[1]) // 2), to)   # prince double push
        if promo:
            t = promo
        b[to] = (pl, t)
        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        reset = capture or state.board[frm][1] == "P"
        key = self._poskey(b, 1 - pl, castling, ep_new, None)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps, hands={})

    # ---- terminal / draws ---------------------------------------------------
    def _insufficient(self, board) -> bool:
        """Conservative: bare kings, or a single lone minor/short-range leaper that
        provably cannot force mate.  Anything richer plays on (the 50-move rule,
        repetition and the ply cap still guarantee termination)."""
        rest = [t for (_, t) in board.values() if t != "K"]
        if not rest:
            return True
        return len(rest) == 1 and rest[0] in ("B", "N", "E", "A", "Z")

    def is_terminal(self, state) -> bool:
        if self._in_setup(state):
            return False
        if self._draw(state):
            return True
        return not self._legal(state)

    def returns(self, state) -> list:
        if self._in_setup(state):
            return [0.0, 0.0]
        if self._draw(state) or not self.in_check(state.board, state.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # ---- initial state ------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c in range(12):
            if self.RANK1[c]:
                b[(c, 0)] = (WHITE, self.RANK1[c])
                b[(c, 11)] = (BLACK, self.RANK1[c])
            if self.RANK2[c]:
                b[(c, 1)] = (WHITE, self.RANK2[c])
                b[(c, 10)] = (BLACK, self.RANK2[c])
            if self.RANK3[c]:
                b[(c, 2)] = (WHITE, self.RANK3[c])
                b[(c, 9)] = (BLACK, self.RANK3[c])
            if self.RANK4[c]:
                b[(c, 3)] = (WHITE, self.RANK4[c])
                b[(c, 8)] = (BLACK, self.RANK4[c])
        return b

    def initial_state(self, options=None, rng=None):
        board = self.setup_board()
        rights = self.CASTLING.initial_rights()
        hands = {BLACK: {"K": 1, "Q": 1, "G": 1, "L": 1,
                         "D": 1, "O": 1, "U": 1, "F": 1}}
        st = CState(board=board, to_move=BLACK, castling=rights, ep=None, hands=hands)
        st.reps = {self._poskey_state(st): 1}
        return st

    def current_player(self, state) -> int:
        return state.to_move

    # We always carry a ``hands`` reserve (full for Black in setup, empty in play);
    # the base DropRules stays NoDrops, so we override the few hooks that gate on
    # ``DROPS.enabled`` to keep the reserve in the position key and on the wire.
    def _poskey_state(self, state) -> str:
        return self._poskey(state.board, state.to_move, state.castling, state.ep,
                            state.hands or None)

    def serialize(self, state) -> dict:
        ep = state.ep
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "castling": "".join(sorted(state.castling)),
            "ep": f"{ep[0][0]},{ep[0][1]},{ep[1][0]},{ep[1][1]}" if ep else None,
            "halfmove": state.halfmove,
            "ply": state.ply,
            "reps": dict(state.reps),
            "hands": {str(p): {L: n for L, n in sorted(h.items()) if n > 0}
                      for p, h in sorted(state.hands.items())},
        }

    def deserialize(self, d: dict):
        ep = None
        if d.get("ep"):
            a, b, c, e = (int(x) for x in d["ep"].split(","))
            ep = ((a, b), (c, e))
        hands = {int(p): {L: int(n) for L, n in h.items()}
                 for p, h in d.get("hands", {}).items()}
        return CState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(d.get("castling", "")),
            ep=ep,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            hands=hands,
        )

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if "@" in move:
            letter, cs = move.split("@")
            c, r = cell(cs)
            return f"{letter}@{_FILES[c]}{r + 1}"
        raw, promo = (move.split("=") + [None])[:2]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        capture = to in state.board or (t == "P" and state.ep is not None and to == state.ep[0])
        alg = lambda cc: f"{_FILES[cc[0]]}{cc[1] + 1}"   # noqa: E731
        text = f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}"
        return text + (f"={promo}" if promo else "")

    def render(self, state, perspective=None) -> dict:
        pieces = []
        for (c, r), (pl, t) in state.board.items():
            p = {"cell": f"{c},{r}", "owner": pl, "label": t}
            icon = self._piece_icon(t)
            if icon:
                p["icon"] = icon
            pieces.append(p)
        setup = self._in_setup(state)
        if self.is_terminal(state):
            ret = self.returns(state)
            caption = "Draw" if ret == [0.0, 0.0] else \
                f"{self._NAMES[0 if ret[0] > 0 else 1]} wins (checkmate)"
        elif setup:
            caption = "Black to arrange its chiefs (setup phase)"
        elif self.in_check(state.board, state.to_move):
            caption = f"{self._NAMES[state.to_move]} to move (check)"
        else:
            caption = f"{self._NAMES[state.to_move]} to move"

        spec = {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
            "pieceset": self.PIECESET,
        }
        if setup:
            # Tint the empty chief squares Black may still fill.
            hand = state.hands.get(BLACK, {})
            want_centre = any(L in hand for L in self.CENTRE_PIECES)
            want_flank = any(L in hand for L in self.FLANK_PIECES)
            tints = {}
            for (c, r) in self.CENTRE_SQUARES:
                if want_centre and (c, r) not in state.board:
                    tints[f"{c},{r}"] = "#b03b3b"
            for (c, r) in self.FLANK_SQUARES:
                if want_flank and (c, r) not in state.board:
                    tints[f"{c},{r}"] = "#3b6fb0"
            if tints:
                spec["board"]["tints"] = tints
            spec["reserve"] = {
                str(BLACK): {L: n for L, n in sorted(hand.items()) if n > 0}
            }
        return spec
