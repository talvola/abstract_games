"""Grant Acedrex ("Great Chess"), from Alfonso X's *Libro de los Juegos* (1283),
built on the shared chess-like core.

A medieval 12x12 game with exotic "animal" pieces.  The reconstruction here
follows the scholarly reconstruction by Jean-Louis Cazaux and Sonja Musser
(as given on Wikipedia / chessvariants.com) -- see ``rules.md`` for the sourced
ruleset and the documented choices for the points where sources disagree.

Pieces (per side), files a..l = columns 0..11 on the back rank:

    R  L  U  G  C  A  K  C  G  U  L  R

  * **King (K)** -- royal; one step in any of the eight directions.  *On its
    very first move only* it may instead make a two-square leap (orthogonal or
    diagonal), jumping over the intermediate square even if occupied, but it may
    not capture with that leap.
  * **Rook (R)** -- orthogonal slider (the modern chess rook).
  * **Crocodile (C)** -- diagonal slider (the modern chess bishop).
  * **Aanca (A)** -- the griffon / "roc": steps **one square diagonally** to an
    intermediate square (which must be empty if it continues), then slides
    **orthogonally outward** any number of squares in either of the two
    directions that lead away from the origin.  (Betza ``t[FR]``.)
  * **Unicorn (U)** -- the "rhinoceros": makes a **knight leap** to an
    intermediate square (which must be empty if it continues), then slides
    **diagonally outward** any number of squares in the direction continuing the
    knight's hop.  (Betza ``t[NB]``.)
  * **Lion (L)** -- a leaper: a combined **(3,0)** + **(3,1)** leaper
    (threeleaper + camel); it jumps directly to those squares.
  * **Giraffe (G)** -- a **(3,2)** oblique leaper (a "zebra").
  * **Pawn (P)** -- one square straight forward, captures one square diagonally
    forward; **no double step, no en passant**.  On reaching the far rank a pawn
    promotes to **the piece that started on its file** (so a g-file pawn -- the
    King's file -- becomes an **Aanca**, never a second King).

There is no castling.  White = player 0.  See ``rules.md``.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, PromotionRules, Castling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# King's first-move two-square leap offsets: two squares orthogonally or
# diagonally (it jumps over the intermediate square, which may be occupied).
KING_LEAP = [(2, 0), (-2, 0), (0, 2), (0, -2),
             (2, 2), (2, -2), (-2, 2), (-2, -2)]

# --- simple leapers -------------------------------------------------------- #
# Lion: combined (3,0)-leaper (threeleaper) + (3,1)-leaper (camel).
THREELEAPER = [(3, 0), (-3, 0), (0, 3), (0, -3)]
CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]
LION = THREELEAPER + CAMEL
# Giraffe: the (3,2) oblique leaper (a "zebra") -- all eight sign/axis combos.
GIRAFFE = [(3, 2), (2, 3), (-3, 2), (-2, 3), (3, -2), (2, -3), (-3, -2), (-2, -3)]

# Back rank, files a..l (columns 0..11).  Identical for both colours: the kings
# stand on the SAME file (g, col 6), facing each other -- this array is NOT a
# left-right mirror (col 5 = Aanca, col 6 = King).
BACK_RANK = ["R", "L", "U", "G", "C", "A", "K", "C", "G", "U", "L", "R"]


class KingLeap(Castling):
    """The King's one-time first-move leap (Alfonso's rule), modelled through the
    ``Castling`` hook (which is the engine's mechanism for special king moves).

    Each king carries an "unmoved" flag (single chars ``"W"`` / ``"B"``, so the
    base char-by-char ``serialize``/``deserialize`` of the rights string round-
    trips them).  While the flag is set, the king may, instead of a normal step,
    leap exactly two squares orthogonally or diagonally to an **empty** square,
    jumping over the intermediate square even if occupied (no capture on the
    leap).  These moves are emitted here (king-safety filtered, since
    ``Castling.moves`` output is NOT re-filtered by ``_legal``); the flag is
    cleared the moment the king moves.  There is no rook relocation, so
    ``rook_move`` always returns ``None``."""

    FLAG = {WHITE: "W", BLACK: "B"}

    def initial_rights(self) -> frozenset:
        return frozenset(self.FLAG.values())

    def moves(self, core, state):
        player = state.to_move
        if self.FLAG[player] not in state.castling:
            return
        k = core._king(state.board, player)
        if k is None:
            return
        kc, kr = k
        enemy = 1 - player
        for dc, dr in KING_LEAP:
            to = (kc + dc, kr + dr)
            if not core.on(*to):
                continue
            if to in state.board:                 # destination must be empty
                continue
            nb = dict(state.board)
            nb.pop((kc, kr))
            nb[to] = (player, "K")
            if not core.attacked(nb, to[0], to[1], enemy):
                yield (kc, kr), to

    def rook_move(self, frm, to, player):
        return None

    def update_rights(self, rights, frm, to, board):
        pl, t = board[frm]
        if t == "K" and self.FLAG.get(pl) in rights:
            return frozenset(rights - {self.FLAG[pl]})
        return rights


class FilePromotion(PromotionRules):
    """A pawn promotes to whatever piece started on the file it reaches.  The
    back-rank array is symmetric in colour, so the target is ``BACK_RANK[col]``
    for either side -- except the King's file (col 6) promotes to an **Aanca**
    (you can never gain a second King)."""

    def _target(self, col: int) -> str:
        t = BACK_RANK[col]
        return "A" if t == "K" else t

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        last = (to[1] == core.HEIGHT - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK)
        return [self._target(to[0])] if last else [None]

    def safety_piece(self) -> str:
        # Used only for king-safety probing of a promoting pawn; the Aanca is the
        # strongest promotion piece, a safe over-approximation of "is the king
        # still safe after this pawn promotes?".
        return "A"


class GrantAcedrex(ChessLike):
    uid = "grand_acedrex"
    name = "Grant Acedrex"

    WIDTH = HEIGHT = 12
    PLY_CAP = 800
    PIECES = {
        "R": (ORTHO, []),          # Rook -- orthogonal slider
        "C": (DIAG, []),           # Crocodile -- diagonal slider (modern bishop)
        "L": ([], LION),           # Lion -- (3,0)+(3,1) leaper
        "G": ([], GIRAFFE),        # Giraffe -- (3,2) zebra leaper
        "K": ([], ALL8),           # King -- one step any direction (royal)
        # "A" (Aanca) and "U" (Unicorn) are COMPOUND step-then-slide pieces;
        # their empty slide/leap entry keeps the base generator/attack maps happy
        # while the real geometry is supplied by the custom generators below.
        "A": ([], []),             # Aanca -- diagonal-step then orthogonal slide
        "U": ([], []),             # Unicorn -- knight-hop then diagonal slide
    }
    HEAVY = ("P", "R", "C", "A", "U", "L", "G")   # everything but the lone king
    PAWN = StandardPawn(white_start=3, black_start=8, double=False)
    PROMOTION = FilePromotion()
    CASTLING = KingLeap()      # no castling; this only adds the king's first-move leap

    # ---- compound-piece geometry -------------------------------------------
    # An Aanca/Unicorn move = a fixed first leg (diagonal step / knight hop) to
    # an intermediate square, then a slide outward.  The intermediate square must
    # be empty to continue sliding; the piece may also stop ON the intermediate
    # square (capturing there if it holds an enemy).  These helpers yield every
    # destination cell for a piece of the given type sitting on (c, r).

    @staticmethod
    def _aanca_legs():
        # (step_dc, step_dr) -> the two orthogonal slide dirs leading outward.
        legs = []
        for sx in (1, -1):
            for sy in (1, -1):
                legs.append(((sx, sy), [(sx, 0), (0, sy)]))
        return legs

    @staticmethod
    def _unicorn_legs():
        # knight hop (a,b) -> the single diagonal slide dir (sign a, sign b).
        return [((a, b), [(1 if a > 0 else -1, 1 if b > 0 else -1)]) for (a, b) in KNIGHT]

    def _compound_targets(self, board, c, r, player, legs):
        """Yield destination cells (c2, r2) for a compound step-then-slide piece
        of ``player`` standing on (c, r), given its ``legs`` list."""
        for (sdc, sdr), slide_dirs in legs:
            mc, mr = c + sdc, r + sdr            # intermediate square
            if not self.on(mc, mr):
                continue
            mocc = board.get((mc, mr))
            if mocc is not None:
                # may capture an enemy on the intermediate square; cannot pass it
                if mocc[0] != player:
                    yield (mc, mr)
                continue
            yield (mc, mr)                        # stop on the empty intermediate
            for ddc, ddr in slide_dirs:
                cc, rr = mc + ddc, mr + ddr
                while self.on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is None:
                        yield (cc, rr)
                    else:
                        if occ[0] != player:
                            yield (cc, rr)
                        break
                    cc += ddc
                    rr += ddr

    def _compound_moves_from(self, board, c, r, player, t):
        legs = self._aanca_legs() if t == "A" else self._unicorn_legs()
        seen = set()
        for to in self._compound_targets(board, c, r, player, legs):
            if to not in seen:
                seen.add(to)
                yield to

    # ---- attacks (override to include the compound pieces) ------------------
    def attacked(self, board, c, r, by) -> bool:
        # 1) the normal slider/leaper/pawn attacks from the base machinery.
        if super().attacked(board, c, r, by):
            return True
        # 2) compound Aanca / Unicorn attacks: a square is attacked iff some
        #    enemy A/U can reach it (these moves are symmetric enough that
        #    forward generation from the attacker is the simplest correct test).
        for (ac, ar), (pl, t) in board.items():
            if pl != by or t not in ("A", "U"):
                continue
            if (c, r) in self._compound_moves_from(board, ac, ar, by, t):
                return True
        return False

    # ---- move generation (add compound pieces) ------------------------------
    def _pseudo(self, state):
        # Start from the base generation (handles pawns, sliders, leapers, king).
        yield from super()._pseudo(state)
        board, player = state.board, state.to_move
        for (c, r), (pl, t) in list(board.items()):
            if pl != player or t not in ("A", "U"):
                continue
            for to in self._compound_moves_from(board, c, r, player, t):
                yield (c, r), to

    # ---- setup --------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c in range(self.WIDTH):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 3)] = (WHITE, "P")
            b[(c, self.HEIGHT - 4)] = (BLACK, "P")     # row 8
            b[(c, self.HEIGHT - 1)] = (BLACK, BACK_RANK[c])
        return b

    # ---- insufficient material ---------------------------------------------
    def _insufficient(self, board) -> bool:
        # The shared-core heuristic only understands chess B/N minors; none of
        # this game's pieces are those.  Only bare king vs bare king is a dead
        # draw; everything else is mating material and plays on (the ply cap
        # guarantees termination).
        return all(t == "K" for (_, t) in board.values())
