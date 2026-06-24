"""Dobutsu Shogi (Animal Shogi / どうぶつしょうぎ, Madoka Kitao 2008).

A 3x4 introductory Shogi for children -- and a fully *solved* game. Built on the
:mod:`agp.shogilike` core so it reuses the colour-relative move generation, the
captures-switch-sides drop machinery, the reserve/hand model and the
serialize/render plumbing. Dobutsu's pieces are animals rather than Shogi pieces,
so this subclass replaces the piece-movement tables, the royal (Lion) lookup, the
promotion logic (only the Chick promotes, to a Hen) and the drop restrictions
(Dobutsu has *no* nifu and lets a Chick drop on the last rank -- it just cannot
move there). It also adds Dobutsu's two win-as-event conditions on top of the
inherited mate/draw handling:

* **Catch**  -- capturing the enemy Lion wins immediately.
* **Try**    -- landing your Lion on the enemy's home (farthest) rank wins, *as
  long as the Lion is not in check there* (it cannot be captured next turn). Since
  the move generator never lets a Lion move into check, a Lion that reaches the
  enemy back rank is by construction safe, so a Lion sitting on the opponent's
  home rank is always a completed, winning Try -- we can detect it statically.

Player 0 = Black/Sente at the bottom (row 0) advancing toward higher rows;
player 1 = White/Gote at the top (row 3). Black moves first.
"""

from __future__ import annotations

from agp.shogilike import (
    ShogiLike, SState, BLACK, WHITE, ORTHO, DIAG, KING, GOLD, cell,
)

# --- Dobutsu animal movement, in the forward frame (Black advancing +row) ------
# Each entry is (slide_dirs, leap_offsets); Dobutsu pieces are all single-step
# leapers, so slide lists stay empty.
CHICK = [(0, 1)]                       # one square straight forward
ANIMAL_BASE = {
    "L": ([], KING),                   # Lion (royal): one square in all 8 dirs
    "G": ([], list(ORTHO)),            # Giraffe: one square orthogonally (Wazir)
    "E": ([], list(DIAG)),             # Elephant: one square diagonally (Ferz)
    "C": ([], CHICK),                  # Chick: one square forward (Shogi pawn)
}
# Only the Chick promotes; it becomes a Hen, which moves as a gold general
# (forward, both forward-diagonals, sideways and straight back -- the 6 dirs that
# are "any way except diagonally backwards").
ANIMAL_PROMO = {
    "C": ([], list(GOLD)),             # Hen (promoted Chick)
}


def _animal_movement(letter, promoted):
    return ANIMAL_PROMO[letter] if promoted else ANIMAL_BASE[letter]


class Dobutsu(ShogiLike):
    name = "Dobutsu Shogi"

    WIDTH = 3
    HEIGHT = 4
    ZONE = 1                 # only the farthest rank promotes
    PLY_CAP = 200            # Dobutsu games are short; hard cap guarantees a draw
    LABELS = {
        "L": "L", "G": "G", "E": "E", "C": "C", "+C": "H",
    }

    def __init__(self):
        # Rebuild the reverse-attack maps from the *animal* movement tables rather
        # than the standard-Shogi globals the base __init__ would use.
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        kinds = ([(L, False) for L in ANIMAL_BASE]
                 + [(L, True) for L in ANIMAL_PROMO])
        for pl in (BLACK, WHITE):
            fwd = 1 if pl == BLACK else -1
            for (letter, prom) in kinds:
                slides, leaps = _animal_movement(letter, prom)
                for (dc, dr) in leaps:
                    off = (dc, dr * fwd)
                    self._leap_att[pl].setdefault(
                        (-off[0], -off[1]), set()).add((letter, prom))
                for (dc, dr) in slides:
                    d = (dc, dr * fwd)
                    self._slide_att[pl].setdefault(
                        (-d[0], -d[1]), set()).add((letter, prom))

    # ---- piece movement (override the standard-Shogi table) ---------------
    def _piece_targets(self, board, sq, pl, letter, promoted):
        c, r = sq
        fwd = self._fwd(pl)
        slides, leaps = _animal_movement(letter, promoted)
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

    # ---- the Lion is the royal (the base class looks for "K") -------------
    def _king(self, board, pl):
        for sq, (p, t) in board.items():
            if p == pl and t == "L":
                return sq
        return None

    # ---- promotion: only the Chick promotes (mandatory on the far rank) ---
    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        if promoted or letter != "C":
            return [False]
        # The Chick promotes the instant it reaches the farthest rank.
        if self._last_rank(pl, to_r):
            return [True]
        return [False]

    # ---- drops: no nifu; a Chick MAY drop on the last rank ----------------
    def _drop_ok(self, state, pl, L, c, r, pawn_files, in_chk):
        # Dobutsu has none of Shogi's drop restrictions (no nifu, last-rank or
        # knight rules; a dropped Chick on the final rank is simply stuck).
        if in_chk:
            b = dict(state.board)
            b[(c, r)] = (pl, L)
            if self.in_check(b, state.promoted, pl):
                return False
        return True

    # ---- Dobutsu win conditions: Catch + Try (win as event) ---------------
    def _winner(self, state):
        """Return the winning player if the position is a completed Catch/Try,
        else None. Derived statically (see module docstring for why this is
        sound): a missing Lion = it was just captured (Catch); a Lion on the
        enemy home rank = a safe Try that already ended the game."""
        for pl in (BLACK, WHITE):
            opp = 1 - pl
            lion = self._king(state.board, pl)
            if lion is None:                 # pl's Lion was captured -> opp wins
                return opp
            # pl's Lion reaching the enemy home rank is pl's own farthest rank.
            if self._last_rank(pl, lion[1]):   # successful Try -> pl wins
                return pl
        return None

    def is_terminal(self, state) -> bool:
        if self._winner(state) is not None:
            return True
        return super().is_terminal(state)

    def returns(self, state):
        w = self._winner(state)
        if w is not None:
            return [1.0, -1.0] if w == BLACK else [-1.0, 1.0]
        return super().returns(state)

    def legal_moves(self, state):
        if self._winner(state) is not None:
            return []
        return super().legal_moves(state)

    def setup_board(self):
        b = {}
        # Each player has, from their OWN perspective, the Elephant on their left,
        # the Lion in the centre, and the Giraffe on their right, with a Chick in
        # front of the Lion. Black (Sente) sits at the bottom (row 0) looking up,
        # so Black's right is the high file: E, L, G across files 0,1,2.
        b[(0, 0)] = (BLACK, "E")
        b[(1, 0)] = (BLACK, "L")
        b[(2, 0)] = (BLACK, "G")
        b[(1, 1)] = (BLACK, "C")          # Chick in front of the Lion
        # White (Gote) at the top (row 3), mirrored 180 degrees: G, L, E.
        b[(0, 3)] = (WHITE, "G")
        b[(1, 3)] = (WHITE, "L")
        b[(2, 3)] = (WHITE, "E")
        b[(1, 2)] = (WHITE, "C")          # Chick in front of the Lion
        return b, set()

    # ---- presentation -----------------------------------------------------
    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        names = {BLACK: "Black (Sente)", WHITE: "White (Gote)"}
        w = self._winner(state)
        if w is not None:
            spec["caption"] = f"{names[w]} wins"
        return spec
