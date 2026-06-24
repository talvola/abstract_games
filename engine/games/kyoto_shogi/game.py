"""Kyoto Shogi (京都将棋, Tamiya Katsuya, 1976): a tiny 5x5 Shogi whose signature
is the FLIP mechanic. Every piece is a single physical token with two faces; on
**every move (except the King) the token flips to its other face**, so a piece
alternates between its two roles turn by turn. There is no promotion zone -- the
flip replaces promotion entirely.

The five flipping pairs (both faces use *standard* Shogi moves, so the
colour-relative move generation, drop bookkeeping and check detection of
:mod:`agp.shogilike` apply unchanged -- only the flip and the per-pair hand are
new):

* **Tokin (T) <-> Lance (L)**  -- Tokin moves as a Gold; Lance slides straight forward.
* **Silver (S) <-> Bishop (B)** -- Silver general; Bishop slides diagonally.
* **Gold (G) <-> Knight (N)**   -- Gold general; Knight = the Shogi knight (jump 2
  forward + 1 sideways, forward only).
* **Pawn (P) <-> Rook (R)**     -- Pawn steps one square forward; Rook slides orthogonally.
* **King (K)**                  -- royal, one step any direction; **never flips**.

Timing: a piece moves as its CURRENT (pre-flip) face -- that face is what reaches
the destination -- then the token flips. The flipped board is exactly what the
opponent then faces, so check / king-safety / checkmate are all evaluated on the
board *as it stands after the flip*. (Confirmed against pychess.org & lishogi.org
Kyoto-shogi implementations: "after every move you flip the piece over"; the
resulting position is the new state.)

Drops: a captured token enters your hand and may be dropped showing **either
face** (your choice). There is no nifu, no last-rank restriction and no
promotion-zone -- the only requirement is that the target square is empty.
The hand is therefore keyed by the *pair* (one token = both faces); each pair in
hand offers two drop moves, one per face.

Setup, each player's back rank from their own left: Tokin, Silver, King, Gold,
Pawn (T S K G P). Player 0 = Black (Sente) at the bottom (row 0), advancing
toward higher rows; White is a 180-degree rotation. Win by checkmating the King.
"""

from __future__ import annotations

from agp.shogilike import (
    ShogiLike, SState, BLACK, WHITE,
    ORTHO, DIAG, KING, GOLD, SILVER, KNIGHT, PAWN, LANCE,
)

# Movement of every face, in Black's forward frame: (slide_dirs, leap_offsets).
# All standard Shogi moves; the only face not in the core's table is the Tokin
# (moves as a Gold general).
MOVE = {
    "T": ([], GOLD),       # Tokin -- Gold general
    "L": (LANCE, []),      # Lance -- straight-forward slider
    "S": ([], SILVER),     # Silver general
    "B": (DIAG, []),       # Bishop -- diagonal slider
    "G": ([], GOLD),       # Gold general
    "N": ([], KNIGHT),     # Knight -- jump 2 fwd + 1 sideways, forward only
    "P": ([], PAWN),       # Pawn -- one step forward
    "R": (ORTHO, []),      # Rook -- orthogonal slider
    "K": ([], KING),       # King -- one step any direction (never flips)
}

# Each piece token has two faces; moving (except the King) flips to the other.
FLIP = {"T": "L", "L": "T", "S": "B", "B": "S",
        "G": "N", "N": "G", "P": "R", "R": "P"}
# A token in hand is identified by its PAIR's canonical letter (the four pairs).
PAIR = {"T": "T", "L": "T", "S": "S", "B": "S",
        "G": "G", "N": "G", "P": "P", "R": "P"}
# The two faces each pair can be dropped as (the canonical letter first).
PAIR_FACES = {"T": ("T", "L"), "S": ("S", "B"), "G": ("G", "N"), "P": ("P", "R")}
DROP_PAIRS = ("T", "S", "G", "P")   # the King is never captured/in hand


class KyotoShogi(ShogiLike):
    uid = "kyoto_shogi"
    name = "Kyoto Shogi"

    WIDTH = HEIGHT = 5
    ZONE = 0                  # no promotion zone -- the flip replaces promotion
    PLY_CAP = 300
    # Board glyphs MATCH the reserve-tray chip letters (the tray shows the raw key),
    # so a piece reads the same on the board and in hand. Letter legend in rules.md:
    # T=Tokin L=Lance S=Silver B=Bishop G=Gold N=Knight P=Pawn R=Rook K=King.
    LABELS = {
        "T": "T", "L": "L", "S": "S", "B": "B",
        "G": "G", "N": "N", "P": "P", "R": "R", "K": "K",
    }

    # ------------------------------------------------------------------ moves
    # Movement/attacks/check come from ShogiLike's machinery driven by our MOVE
    # table (Tokin is the only non-core face; all faces are left/right symmetric,
    # so the colour flip is row-only exactly as in the core). `promoted` is always
    # empty here. The differences from the core are the flip (applied to the board
    # the opponent faces), no promotion, and the per-pair / face-choosing drops.
    def __init__(self):
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        for pl in (BLACK, WHITE):
            fwd = 1 if pl == BLACK else -1
            for letter, (slides, leaps) in MOVE.items():
                for (dc, dr) in leaps:
                    off = (dc, dr * fwd)
                    self._leap_att[pl].setdefault((-off[0], -off[1]), set()).add((letter, False))
                for (dc, dr) in slides:
                    d = (dc, dr * fwd)
                    self._slide_att[pl].setdefault((-d[0], -d[1]), set()).add((letter, False))

    def _piece_targets(self, board, sq, pl, letter, promoted):
        c, r = sq
        fwd = self._fwd(pl)
        slides, leaps = MOVE[letter]
        for (dc, dr) in leaps:
            t = (c + dc, r + dr * fwd)
            if self.on(*t) and (board.get(t) or (None,))[0] != pl:
                yield t
        for (dc, dr) in slides:
            step_r = dr * fwd
            cc, rr = c + dc, r + step_r
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is None:
                    yield (cc, rr)
                else:
                    if occ[0] != pl:
                        yield (cc, rr)
                    break
                cc += dc
                rr += step_r

    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        return [False]        # Kyoto has no promotion zone

    def _flip(self, letter):
        return FLIP.get(letter, letter)   # King (and any unknown) is unchanged

    def _board_after(self, state, frm, to, promote):
        """Resulting board for king-safety -- WITH the moving token flipped, since
        the flip happens before the opponent's turn."""
        b = dict(state.board)
        pl, t = b.pop(frm)
        b[to] = (pl, self._flip(t))
        return b, frozenset()             # promoted is always empty in Kyoto

    # ------------------------------------------------------------------ drops
    def _drop_moves(self, state):
        pl = state.to_move
        pairs = [P for P, n in state.hands.get(pl, {}).items() if n > 0]
        if not pairs:
            return []
        in_chk = self.in_check(state.board, state.promoted, pl)
        out = []
        for c in range(self.WIDTH):
            for r in range(self.HEIGHT):
                if (c, r) in state.board:
                    continue
                for P in pairs:
                    for face in PAIR_FACES[P]:
                        if in_chk:
                            b = dict(state.board)
                            b[(c, r)] = (pl, face)
                            if self.in_check(b, frozenset(), pl):
                                continue
                        out.append(f"{face}@{c},{r}")
        return out

    def _apply_drop(self, state, move):
        face, cs = move.split("@")
        c, r = (int(x) for x in cs.split(","))
        pl = state.to_move
        b = dict(state.board)
        b[(c, r)] = (pl, face)           # dropped showing the chosen face (no flip)
        hands = {p: dict(h) for p, h in state.hands.items()}
        hand = hands.setdefault(pl, {})
        key = PAIR[face]
        hand[key] = hand.get(key, 0) - 1
        if hand[key] <= 0:
            del hand[key]
        return self._finish(b, frozenset(), hands, 1 - pl, state)

    # ------------------------------------------------------------------ a move
    def apply_move(self, state, move, rng=None):
        if "@" in move:
            return self._apply_drop(state, move)
        fs, ts = move.split(">")
        frm = tuple(int(x) for x in fs.split(","))
        to = tuple(int(x) for x in ts.split(","))
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)
        hands = {p: dict(h) for p, h in state.hands.items()}

        captured = state.board.get(to)
        if captured is not None:                 # bank the captured token by its PAIR
            key = PAIR[captured[1]]
            hand = hands.setdefault(pl, {})
            hand[key] = hand.get(key, 0) + 1

        b[to] = (pl, self._flip(t))              # the token flips after moving
        return self._finish(b, frozenset(), hands, 1 - pl, state)

    # ------------------------------------------------ presentation (per-pair hand)
    def describe_move(self, state, move):
        if "@" in move:
            face, cs = move.split("@")
            c = tuple(int(x) for x in cs.split(","))
            return f"{self._label(face, False)}*{c[0]},{c[1]}"
        fs, ts = move.split(">")
        frm = tuple(int(x) for x in fs.split(","))
        pl, t = state.board.get(frm, (None, "?"))
        cap = "x" if tuple(int(x) for x in ts.split(",")) in state.board else "-"
        return f"{self._label(t, False)}{fs}{cap}{ts}={self._label(self._flip(t), False)}"

    def render(self, state, perspective=None):
        spec = super().render(state, perspective)
        # The hand is keyed by PAIR; show BOTH faces of each held token as separate
        # reserve chips (clicking either drops that face) so the drop face-choice is
        # the existing reserve-tray UI.
        reserve = {}
        for p, hd in sorted(state.hands.items()):
            trays = {}
            for key, n in sorted(hd.items()):
                if n <= 0:
                    continue
                for face in PAIR_FACES[key]:
                    trays[face] = n
            reserve[str(p)] = trays
        spec["reserve"] = reserve
        return spec

    # ------------------------------------------------------------------ setup
    def setup_board(self):
        b = {}
        # Black (Sente) back rank (row 0), from Black's left: T S K G P.
        for c, t in enumerate("TSKGP"):
            b[(c, 0)] = (BLACK, t)
        # White (Gote): a 180-degree rotation of Black's army.
        for c, t in enumerate("TSKGP"):
            b[(self.WIDTH - 1 - c, self.HEIGHT - 1)] = (WHITE, t)
        return b, set()
