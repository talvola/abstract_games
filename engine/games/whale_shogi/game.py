"""Whale Shogi (Kujira Shogi) -- a 6x6 shogi variant by R. Wayne Schmittberger
(1981) themed on whaling.

It is built on the shared :mod:`agp.shogilike` core (state model, drops, check /
mate, serialize, render), but its pieces, promotion and drop rules differ enough
from orthodox shogi that this module supplies its own movement table and a few
overrides:

* **Whale-themed pieces**, none of which move like an orthodox shogi piece:
  White Whale (W, the royal piece -- capturing it wins), Porpoise (P), Humpback
  (H), Grey Whale (G), Narwhal (N), Blue Whale (B) and six Dolphins (D).
* **Promotion only on capture, and only for the porpoise.** There is no
  promotion zone: a porpoise turns into a Killer Whale (K) *when it is captured*
  and thereafter exists only as a killer whale (in hand or dropped). No other
  piece ever promotes, and a captured killer whale stays a killer whale.
* **Dolphin conditional move.** A dolphin steps one square forward; only while it
  sits on the farthest rank does it gain a diagonally-backward slide (it has no
  other move once it can no longer advance).
* **Dolphin-specific drop rules** (all three are dolphin-only): no drop on the
  farthest rank, at most two dolphins of one player per file, and no drop that
  delivers immediate checkmate (uchifuzume). Every other piece drops freely.

Player 0 = Sente (Black) starts at the bottom (row 0) and advances toward higher
rows, exactly as in the shogi core.
"""

from __future__ import annotations

from agp.shogilike import ShogiLike, BLACK, WHITE, cell, ORTHO, DIAG, KING

# Movement in the *forward frame* (Black advancing +row): (slide_dirs, leap_offsets).
# Colour only flips the forward sign (handled by the core's _fwd).
SIDEWAYS = [(1, 0), (-1, 0)]
DIAG_BACK = [(1, -1), (-1, -1)]        # diagonally *backward* slides (dolphin, grey whale)

MOVES = {
    "W": ([], KING),                               # White Whale: steps 1 any direction (royal)
    "P": ([], SIDEWAYS),                           # Porpoise: 1 square orthogonally sideways
    "K": (ORTHO, DIAG),                            # Killer Whale: rook slide + 1 diagonal step
    "H": ([], [(1, 1), (1, -1), (-1, 1), (-1, -1), (0, -1)]),  # Humpback: 4 diagonals + backward
    "G": ([(0, 1)] + DIAG_BACK, []),               # Grey Whale: slide forward + slide diag-back
    "N": ([], [(0, 2), (0, -1), (1, 0), (-1, 0)]), # Narwhal: jump 2 forward + back + sideways
    "B": ([], [(0, 1), (0, -1), (1, 1), (-1, 1)]), # Blue Whale: fwd/back + diagonal-forward
    "D": ([], [(0, 1)]),                           # Dolphin: 1 forward (+ conditional diag-back)
}


class WhaleShogi(ShogiLike):
    uid = "whale_shogi"
    name = "Whale Shogi"

    WIDTH = HEIGHT = 6
    ZONE = 0                 # no promotion zone (promotion happens only on capture)
    PLY_CAP = 300
    MOVES = MOVES
    LABELS = {
        "W": "W", "P": "P", "H": "H", "G": "G", "N": "N", "B": "B", "D": "D",
        "K": "K",            # Killer Whale (promoted porpoise, only ever in hand / dropped)
    }

    def __init__(self):
        # The core precomputes reverse-attack maps from the *orthodox* shogi
        # tables; whale pieces are entirely different, so we override attacked()
        # with a brute-force scan and skip that setup.
        pass

    def setup_board(self):
        b = {}
        # Black (Sente) home rank at the bottom (row 0), left->right: H G W P N B
        for c, t in enumerate("HGWPNB"):
            b[(c, 0)] = (BLACK, t)
        for c in range(self.WIDTH):
            b[(c, 1)] = (BLACK, "D")               # six black dolphins on row 1
        # White (Gote) is a 180-degree rotation of Black.
        for (c, r), (p, t) in list(b.items()):
            b[(self.WIDTH - 1 - c, self.HEIGHT - 1 - r)] = (WHITE, t)
        return b, set()

    # ---- movement (whale table + conditional dolphin slide) ----------------
    def _piece_targets(self, board, sq, pl, letter, promoted=False):
        c, r = sq
        fwd = self._fwd(pl)
        slides, leaps = self.MOVES[letter]
        # a dolphin gains a diagonally-backward slide only on the farthest rank
        if letter == "D" and self._last_rank(pl, r):
            slides = slides + DIAG_BACK
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

    # ---- attacks (brute force -- handles the position-dependent dolphin) ----
    def attacked(self, board, promoted, sq, by) -> bool:
        for psq, (p, t) in board.items():
            if p != by:
                continue
            for to in self._piece_targets(board, psq, by, t, False):
                if to == sq:
                    return True
        return False

    def _king(self, board, pl):
        for sq, (p, t) in board.items():
            if p == pl and t == "W":
                return sq
        return None

    # ---- no board promotion (porpoise promotes only when captured) ---------
    def _promotion_options(self, letter, promoted, frm_r, to_r, pl):
        return [False]

    # ---- capture: a captured porpoise enters the hand as a killer whale -----
    def apply_move(self, state, move, rng=None):
        if "@" in move:
            return self._apply_drop(state, move)
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)
        hands = {p: dict(h) for p, h in state.hands.items()}
        captured = state.board.get(to)
        if captured is not None:
            gained = "K" if captured[1] == "P" else captured[1]   # porpoise -> killer whale
            hands.setdefault(pl, {})
            hands[pl][gained] = hands[pl].get(gained, 0) + 1
        b[to] = (pl, t)
        return self._finish(b, frozenset(), hands, 1 - pl, state)

    # ---- drops (all three restrictions are dolphin-only) -------------------
    def _drop_moves(self, state):
        pl = state.to_move
        letters = [L for L, n in state.hands.get(pl, {}).items() if n > 0]
        if not letters:
            return []
        in_chk = self.in_check(state.board, state.promoted, pl)
        dolphin_files = {}
        for (c, r), (p, t) in state.board.items():
            if p == pl and t == "D":
                dolphin_files[c] = dolphin_files.get(c, 0) + 1
        out = []
        for c in range(self.WIDTH):
            for r in range(self.HEIGHT):
                if (c, r) in state.board:
                    continue
                for L in letters:
                    if L == "D":
                        if self._last_rank(pl, r):
                            continue                       # no dolphin on the farthest rank
                        if dolphin_files.get(c, 0) >= 2:
                            continue                       # at most two dolphins per file
                    if in_chk:
                        b = dict(state.board)
                        b[(c, r)] = (pl, L)
                        if self.in_check(b, state.promoted, pl):
                            continue                       # a drop must not leave you in check
                    if L == "D":                           # uchifuzume: no drop-mate with a dolphin
                        b = dict(state.board)
                        b[(c, r)] = (pl, L)
                        ok = self._king(b, 1 - pl)
                        if ok and self.attacked(b, state.promoted, ok, pl) \
                                and self._is_mated(b, state.promoted, state.hands, 1 - pl):
                            continue
                    out.append(f"{L}@{c},{r}")
        return out
