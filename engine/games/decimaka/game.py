"""Decimaka (H. G. Muller, 2018) -- a 10x10 western chess variant that emulates
the promotion dynamics of Maka Dai Dai Shogi: promotion is NOT reserved for
pawns and does NOT come from reaching a zone. Instead a piece may (and
sometimes must) promote when it MAKES A CAPTURE, anywhere on the board.

Primary source: https://www.chessvariants.com/rules/decimaka (Muller's own
page, 2018-03-13, including his machine-readable Interactive Diagram block --
this implements the ORIGINAL version described there, not the later revision
he links to).

Piece letters (setup army):

* **K King** -- orthodox king; castles by moving THREE squares toward a rook.
* **R Rook / B Bishop / N Knight / P Pawn** -- orthodox (pawns start on the
  3rd/8th rank with an initial double step and e.p. capture).
* **F Fiancee** (Betza K) -- non-royal king-mover.
* **T Tee** (vWfF) -- steps 1 straight forward/backward or diagonally forward.
* **C Cross** (WD) -- steps 1 or jumps 2 orthogonally.
* **Y Y** (fFfAfGbWbDbH) -- leaps 1, 2 or 3 diagonally forward or straight
  backward.
* **S Star** (KDAGH) -- jumps 1, 2 or 3 squares orthogonally or diagonally.
* **L Lion** (KNAD) -- king step, knight jump, or a 2-square orthogonal or
  diagonal jump.

Promoted types (only ever appear via capture-promotion):

* **Q Queen** (promoted Fiancee) -- orthodox queen.
* **+T Trident** (vRfB, promoted Tee) -- slides along the file both ways or
  diagonally forward.
* **+N Nightrider** (NN, promoted Knight) -- repeated knight moves in one
  direction until blocked.
* **O Omni** (mWcF, promoted Pawn/Cross/Y/Star/Lion) -- moves WITHOUT
  capturing 1 step orthogonally, captures 1 step diagonally.

Promotion rules (all promotion happens on the capture move itself):

1. Capturing a **Queen** with anything but the King promotes the capturer to
   Queen -- mandatorily, even for already-promoted or normally-unpromotable
   pieces.
2. Otherwise, capturing a **promoted piece** (Q / O / +T / +N) makes the
   capturer's own promotion mandatory (if it has one; R/B/K and the promoted
   types themselves have none and stay as they are).
3. Any other capture makes promotion **optional**.
4. There is no promotion zone: a pawn reaching the last rank stays a pawn
   ("dead wood"); pieces never promote on non-capture moves.

Checkmate wins; stalemate and the usual 50-move/threefold/ply-cap rules draw.

Directional pieces (T, Y, +T, pawn attacks, omni captures) differ per colour,
so this subclass owns its movement model: per-player (slides, leaps) tables in
White's frame with a 180-degree rotation for Black, plus reverse capture maps
for `attacked` (the nightrider is a "slider" whose step is a knight offset).
Moves are the platform cell paths ``"fc,fr>tc,tr"`` with ``"=X"`` carrying the
promotion choice (only the mandatory variant is offered when promotion is
forced).
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, PromotionRules, StandardCastling,
    cell, ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

# ---- movement tables, in WHITE's frame (forward = +row). Black = 180-deg
# rotation (negate both offsets). All entries are capture-as-you-move except
# the pawn and the Omni, which are handled specially. ----
TEE = [(0, 1), (0, -1), (1, 1), (-1, 1)]
CROSS = [(1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)]
Y_LEAPS = [(1, 1), (-1, 1), (2, 2), (-2, 2), (3, 3), (-3, 3),
           (0, -1), (0, -2), (0, -3)]
STAR = [(dc * k, dr * k) for (dc, dr) in ALL8 for k in (1, 2, 3)]
LION = ALL8 + KNIGHT + [(2, 2), (-2, 2), (2, -2), (-2, -2),
                        (2, 0), (-2, 0), (0, 2), (0, -2)]
TRIDENT = [(0, 1), (0, -1), (1, 1), (-1, 1)]        # slide directions

MOVES = {                                            # letter -> (slides, leaps)
    "T": ([], TEE),
    "N": ([], KNIGHT),
    "F": ([], ALL8),
    "C": ([], CROSS),
    "Y": ([], Y_LEAPS),
    "S": ([], STAR),
    "L": ([], LION),
    "B": (DIAG, []),
    "R": (ORTHO, []),
    "K": ([], ALL8),
    "Q": (ALL8, []),
    "+T": (TRIDENT, []),
    "+N": (KNIGHT, []),                              # nightrider: knight-step slider
}
OMNI_CAP = DIAG                                      # Omni captures 1 diagonally
PAWN_CAP = [(1, 1), (-1, 1)]                         # pawn attack squares (White)

PROMOTES = {"P": "O", "C": "O", "Y": "O", "S": "O", "L": "O",
            "T": "+T", "N": "+N", "F": "Q"}
PROMOTED = frozenset(("O", "+T", "+N", "Q"))

RANK1 = {0: "R", 3: "Y", 4: "F", 5: "K", 6: "Y", 9: "R"}     # a1 d1 e1 f1 g1 j1
RANK2 = ["C", "T", "N", "B", "L", "S", "B", "N", "T", "C"]   # a2..j2


class CapturePromotion(PromotionRules):
    """No zone promotion at all -- a pawn on the last rank stays a pawn
    ("dead wood"). Capture-promotion is handled in legal_moves/apply_move."""

    def options(self, core, state, frm, to):
        return [None]

    def safety_piece(self):
        return "P"


class DecimakaCastling(StandardCastling):
    """10-wide castling: the King (f1 White / e10 Black, rotational symmetry)
    moves THREE squares toward either rook; orthodox virginity / clear-path /
    not-through-check conditions. 'K'/'k' = toward the j-file rook."""

    CASTLES = {
        "K": ((5, 0), (8, 0), (9, 0), (7, 0),
              [(6, 0), (7, 0), (8, 0)], [(5, 0), (6, 0), (7, 0), (8, 0)]),
        "Q": ((5, 0), (2, 0), (0, 0), (3, 0),
              [(1, 0), (2, 0), (3, 0), (4, 0)], [(5, 0), (4, 0), (3, 0), (2, 0)]),
        "k": ((4, 9), (7, 9), (9, 9), (6, 9),
              [(5, 9), (6, 9), (7, 9), (8, 9)], [(4, 9), (5, 9), (6, 9), (7, 9)]),
        "q": ((4, 9), (1, 9), (0, 9), (2, 9),
              [(1, 9), (2, 9), (3, 9)], [(4, 9), (3, 9), (2, 9), (1, 9)]),
    }
    ROOK_HOME = {(9, 0): "K", (0, 0): "Q", (9, 9): "k", (0, 9): "q"}
    KING_HOME = {(5, 0): WHITE, (4, 9): BLACK}

    def rook_move(self, frm, to, player):
        if abs(to[0] - frm[0]) != 3:
            return None
        flag = self.BY_COLOR[player][0] if to[0] > frm[0] else self.BY_COLOR[player][1]
        _, _, rfrom, rto, _, _ = self.CASTLES[flag]
        return rfrom, rto


class Decimaka(ChessLike):
    name = "Decimaka"

    WIDTH = HEIGHT = 10
    PLY_CAP = 800
    PIECES = {}                       # movement is fully custom (directional pieces)
    HEAVY = ("P", "R", "Q", "T", "F", "C", "Y", "S", "L", "O", "+T", "+N")
    PIECE_VALUES = {"P": 1.0, "N": 3.0, "B": 3.5, "R": 5.0, "Q": 9.5, "K": 0.0,
                    "T": 1.5, "F": 4.0, "C": 3.0, "Y": 2.0, "S": 5.0, "L": 6.5,
                    "O": 1.5, "+T": 4.5, "+N": 5.5}
    PAWN = StandardPawn(white_start=2, black_start=7)
    PROMOTION = CapturePromotion()
    CASTLING = DecimakaCastling()

    def __init__(self):
        # Per-player movement tables + reverse CAPTURE maps for `attacked`.
        self._moves = {WHITE: {}, BLACK: {}}
        self._cap_leap = {WHITE: {}, BLACK: {}}
        self._cap_slide = {WHITE: {}, BLACK: {}}
        for pl in (WHITE, BLACK):
            sgn = 1 if pl == WHITE else -1
            for letter, (slides, leaps) in MOVES.items():
                sl = [(dc * sgn, dr * sgn) for dc, dr in slides]
                lp = [(dc * sgn, dr * sgn) for dc, dr in leaps]
                self._moves[pl][letter] = (sl, lp)
                for d in sl:
                    self._cap_slide[pl].setdefault(d, set()).add(letter)
                for o in lp:
                    self._cap_leap[pl].setdefault(o, set()).add(letter)
            for dc, dr in OMNI_CAP:                  # Omni captures diagonally only
                self._cap_leap[pl].setdefault((dc * sgn, dr * sgn), set()).add("O")
            for dc, dr in PAWN_CAP:
                self._cap_leap[pl].setdefault((dc * sgn, dr * sgn), set()).add("P")

    # ---- setup --------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c, t in RANK1.items():
            b[(c, 0)] = (WHITE, t)
            b[(9 - c, 9)] = (BLACK, t)               # 180-degree rotational symmetry
        for c, t in enumerate(RANK2):
            b[(c, 1)] = (WHITE, t)
            b[(9 - c, 8)] = (BLACK, t)
        for c in range(10):
            b[(c, 2)] = (WHITE, "P")
            b[(c, 7)] = (BLACK, "P")
        return b

    # ---- attacks (reverse capture maps; nightrider = knight-offset slider) --
    def attacked(self, board, c, r, by) -> bool:
        for (dx, dy), types in self._cap_leap[by].items():
            occ = board.get((c - dx, r - dy))
            if occ is not None and occ[0] == by and occ[1] in types:
                return True
        for (dx, dy), types in self._cap_slide[by].items():
            cc, rr = c - dx, r - dy
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] == by and occ[1] in types:
                        return True
                    break
                cc -= dx
                rr -= dy
        return False

    # ---- move generation -----------------------------------------------------
    def _pseudo(self, state):
        board, player = state.board, state.to_move
        ep_target = state.ep[0] if state.ep else None
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "P":
                yield from self.PAWN.pseudo(self, board, c, r, player, ep_target)
                continue
            if t == "O":                             # move ortho, capture diag
                for dc, dr in ORTHO:
                    tc, tr = c + dc, r + dr
                    if self.on(tc, tr) and (tc, tr) not in board:
                        yield (c, r), (tc, tr)
                for dc, dr in DIAG:
                    tc, tr = c + dc, r + dr
                    occ = board.get((tc, tr))
                    if self.on(tc, tr) and occ is not None and occ[0] != player:
                        yield (c, r), (tc, tr)
                continue
            slides, leaps = self._moves[player][t]
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

    # ---- capture-promotion ---------------------------------------------------
    def _promo_options(self, state, frm, to):
        """[None] = plain move only; letters = promotion choices. Mandatory
        promotions return ONLY the promoted variant."""
        pl, t = state.board[frm]
        victim = state.board.get(to)
        if victim is None and t == "P" and state.ep is not None and to == state.ep[0]:
            victim = state.board.get(state.ep[1])
        if victim is None or t == "K":               # non-capture / royal: never
            return [None]
        if victim[1] == "Q":                         # Queen-capture rule: forced Q
            return ["Q"]
        target = PROMOTES.get(t)
        if target is None:                           # R/B or already promoted
            return [None]
        if victim[1] in PROMOTED:                    # capturing a promoted piece
            return [target]
        return [None, target]                        # ordinary capture: optional

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        out = []
        for f, t in self._legal(state):
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            for ch in self._promo_options(state, f, t):
                out.append(base if ch is None else base + "=" + ch)
        return out

    # ---- apply ----------------------------------------------------------------
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
        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        elif t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                b.pop(state.ep[1], None)             # en passant
                capture = True
            else:
                ep_new = self.PAWN.ep_after(frm, to)

        if promo:                                    # capture-promotion (any piece)
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

    # ---- presentation ----------------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        spec["choiceTitle"] = "Promote?"
        spec["choiceNames"] = {"O": "Omni", "+T": "Trident", "+N": "Nightrider",
                               "Q": "Queen"}
        return spec
