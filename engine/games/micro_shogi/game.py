"""Micro Shogi (マイクロ将棋): a tiny 4x5 Shogi whose signature is
**promote-on-capture**. There is NO promotion zone -- instead a piece flips to
its other face the instant it *captures*, and this is mandatory. A promoted
piece flips back to its base face when *it* captures, so a token oscillates
between its two roles over the game, purely driven by captures.

Each side has five pieces: King, Bishop, Gold, Silver and one Pawn. Every
non-royal piece is a two-faced token (like Kyoto Shogi's flip tokens, but here
the flip is triggered by a capture rather than by every move):

* **Silver (S) <-> Lance (L)**    -- Silver general; Lance slides straight forward.
* **Gold (G) <-> Rook (R)**       -- Gold general; Rook slides orthogonally.
* **Bishop (B) <-> Tokin (T)**    -- Bishop slides diagonally; Tokin moves as a Gold.
* **Pawn (P) <-> Knight (N)**     -- Pawn steps one forward; Knight = the Shogi knight.
* **King (K)**                    -- royal, one step any direction; never flips.

Timing: a piece moves as its CURRENT (pre-flip) face; if that move captures, the
token then flips to its other face on the destination square. A non-capturing
move leaves the face unchanged. King-safety / check / checkmate are evaluated on
the board *after* any capture-flip (that is the position the opponent faces).

Drops: a captured token joins your hand keyed by its PAIR, and may be dropped
showing **either face** (your choice). Micro Shogi imposes *no* drop
restrictions -- no nifu (two pawns on a file is fine), no last-rank ban and no
drop-mate ban; the only requirement is that the target square is empty. A piece
dropped on a rank from which it has no move (e.g. a Pawn/Lance on the last rank,
a Knight on the last two ranks) is simply trapped until captured.

Setup, each player's back rank from their own left: **Silver, Gold, Bishop,
King (S G B K)**, with the Pawn on the second rank directly in front of the King.
Player 0 = Black (Sente) at the bottom (row 0), advancing toward higher rows;
White is a 180-degree rotation. Win by checkmating the King.
"""

from __future__ import annotations

from agp.shogilike import (
    ShogiLike, BLACK, WHITE,
    ORTHO, DIAG, KING, GOLD, SILVER, KNIGHT, PAWN, LANCE,
)

# Movement of every face, in Black's forward frame: (slide_dirs, leap_offsets).
# All standard Shogi moves; the Tokin (promoted Bishop face) moves as a Gold.
MOVE = {
    "K": ([], KING),       # King -- one step any direction (never flips)
    "S": ([], SILVER),     # Silver general
    "L": (LANCE, []),      # Lance -- straight-forward slider
    "G": ([], GOLD),       # Gold general
    "R": (ORTHO, []),      # Rook -- orthogonal slider
    "B": (DIAG, []),       # Bishop -- diagonal slider
    "T": ([], GOLD),       # Tokin -- moves as a Gold general
    "P": ([], PAWN),       # Pawn -- one step forward
    "N": ([], KNIGHT),     # Knight -- jump 2 fwd + 1 sideways, forward only
}

# A capture flips the capturing token to its other face (King never flips).
FLIP = {"S": "L", "L": "S", "G": "R", "R": "G",
        "B": "T", "T": "B", "P": "N", "N": "P"}
# A token in hand is identified by its PAIR's canonical (base) letter.
PAIR = {"S": "S", "L": "S", "G": "G", "R": "G",
        "B": "B", "T": "B", "P": "P", "N": "P"}
# The two faces each pair can be dropped as (the canonical/base face first).
PAIR_FACES = {"S": ("S", "L"), "G": ("G", "R"), "B": ("B", "T"), "P": ("P", "N")}
DROP_PAIRS = ("S", "G", "B", "P")   # the King is never captured / in hand


class MicroShogi(ShogiLike):
    uid = "micro_shogi"
    name = "Micro Shogi"

    WIDTH = 4                 # 4 files
    HEIGHT = 5                # 5 ranks
    ZONE = 0                  # no promotion zone -- capture drives the flip
    PLY_CAP = 300
    LABELS = {
        "K": "K", "S": "S", "L": "L", "G": "G", "R": "R",
        "B": "B", "T": "T", "P": "P", "N": "N",
    }

    # ------------------------------------------------------------------ setup
    def __init__(self):
        # Rebuild the reverse-attack maps from OUR movement table (every face may
        # sit on the board). All faces are left/right symmetric, so the colour
        # flip is row-only, exactly as in the core. `promoted` is always empty.
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

    def setup_board(self):
        b = {}
        # Black (Sente) back rank (row 0), from Black's left: S G B K.
        for c, t in enumerate("SGBK"):
            b[(c, 0)] = (BLACK, t)
        b[(3, 1)] = (BLACK, "P")          # Pawn in front of the King (file 3)
        # White (Gote): a 180-degree rotation of Black's army.
        for c, t in enumerate("SGBK"):
            b[(self.WIDTH - 1 - c, self.HEIGHT - 1)] = (WHITE, t)
        b[(0, self.HEIGHT - 2)] = (WHITE, "P")
        return b, set()

    # ------------------------------------------------------------------ moves
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
        return [False]        # never a zone-promotion choice -- the flip is on capture

    def _flip(self, letter):
        return FLIP.get(letter, letter)   # King (and any unknown) is unchanged

    def _board_after(self, state, frm, to, promote):
        """Resulting board for king-safety -- the moving token flips iff this move
        is a capture (the destination was occupied), since the flip precedes the
        opponent's turn."""
        b = dict(state.board)
        pl, t = b.pop(frm)
        captured = state.board.get(to) is not None
        b[to] = (pl, self._flip(t) if captured else t)
        return b, frozenset()             # promoted is always empty in Micro Shogi

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
            b[to] = (pl, self._flip(t))           # capture -> the mover flips faces
        else:
            b[to] = (pl, t)                        # quiet move -> no flip

        return self._finish(b, frozenset(), hands, 1 - pl, state)

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

    # ------------------------------------------------ presentation (per-pair hand)
    def describe_move(self, state, move):
        if "@" in move:
            face, cs = move.split("@")
            c = tuple(int(x) for x in cs.split(","))
            return f"{self._label(face, False)}*{c[0]},{c[1]}"
        fs, ts = move.split(">")
        frm = tuple(int(x) for x in fs.split(","))
        to = tuple(int(x) for x in ts.split(","))
        pl, t = state.board.get(frm, (None, "?"))
        cap = to in state.board
        face = self._flip(t) if cap else t
        arrow = "x" if cap else "-"
        note = f"={self._label(face, False)}" if cap else ""
        return f"{self._label(t, False)}{fs}{arrow}{ts}{note}"

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
