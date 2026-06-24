"""Sittuyin (Burmese chess), 8x8, built on the shared chess-like core.

Sittuyin is the traditional chess of Myanmar (Burma). It is a close cousin of
Makruk (Thai chess): the same short-range Ferz "general", a silver-general-like
"elephant", a knight, a rook and a one-step pawn. Its two signature features are
the **deployment (setup) phase** -- only the pawns start on the board, and the
players alternately place their remaining eight pieces on their own half -- and
the distinctive **sit-tu promotion**: a pawn may promote to a *general* only when
it stands on one of the board's two long diagonals (in the enemy half) and only
if the player's own general has already been captured.

Pieces (letters):

* **Min-gyi (King, ``K``)** -- moves one square in any of the eight directions,
  like a chess king. No castling.
* **Sit-ke (General, ``G``)** -- a *ferz*: one square diagonally only.
* **Sin (Elephant, ``E``/``e``)** -- one square diagonally (any of the four
  diagonals) OR one square straight forward -- five destinations, exactly like
  the Makruk Khon / a silver-general. White's elephant is ``E`` and Black's is
  ``e`` (the forward direction is colour-dependent, and the engine's leap table
  is colour-blind, so the two need two letters; both render/describe as Elephant).
* **Myin (Horse, ``N``)** -- the chess knight.
* **Yahta / Ratha (Chariot, ``R``)** -- the chess rook (orthogonal slider).
* **Ne (Pawn / feudal lord, ``P``)** -- one square straight forward (no double
  step, hence no en passant), captures one square diagonally forward.

Win by checkmate; stalemate is **not** a win and is treated as a draw here. There
is no castling and no en passant.

This module is anchored on the Fairy-Stockfish ``sittuyin`` variant definition
(start FEN, the rook-on-back-rank deployment rule, and the eight promotion
squares).  See ``rules.md`` for the documented interpretations.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, StandardPawn, PromotionRules, NoCastling, CState,
    ORTHO, DIAG, KNIGHT, ALL8, WHITE, BLACK,
)

# --- pawn (Ne) starting formation (Fairy-Stockfish start FEN) -------------- #
# FEN: 8/8/4pppp/pppp4/4PPPP/PPPP4/8/8
#   White pawns: files a-d on rank 3 (row 2), files e-h on rank 4 (row 3).
#   Black pawns: files a-d on rank 5 (row 4), files e-h on rank 6 (row 5).
WHITE_PAWNS = [(c, 2) for c in range(4)] + [(c, 3) for c in range(4, 8)]
BLACK_PAWNS = [(c, 4) for c in range(4)] + [(c, 5) for c in range(4, 8)]

# Elephant (Sin) leap sets: four diagonals + the single straight-forward step.
SIN_WHITE = DIAG + [(0, 1)]     # White advances toward higher rows
SIN_BLACK = DIAG + [(0, -1)]    # Black advances toward lower rows

# The two long diagonals (main c==r and anti c+r==7). A pawn promotes only on the
# squares of these diagonals that lie in the ENEMY half of the board.
WHITE_PROMO = frozenset(  # enemy half = rows 4..7 for White
    [(c, c) for c in range(4, 8)] + [(c, 7 - c) for c in range(4)]
)
BLACK_PROMO = frozenset(  # enemy half = rows 0..3 for Black
    [(c, c) for c in range(4)] + [(c, 7 - c) for c in range(4, 8)]
)


class _NoLastRankPromotion(PromotionRules):
    """Pawns never promote by *reaching a rank* in Sittuyin (the sit-tu promotion
    is a separate move handled directly by the game). So the standard pawn-move
    generator must always offer the plain (non-promoting) move."""

    def options(self, core, state, frm, to):
        return [None]

    def safety_piece(self) -> str:
        return "G"


class Sittuyin(ChessLike):
    uid = "sittuyin"
    name = "Sittuyin"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []),
        "N": ([], KNIGHT),
        "G": ([], DIAG),          # Sit-ke (general) = ferz
        "K": ([], ALL8),          # Min-gyi (king)
        "E": ([], SIN_WHITE),     # White Sin (elephant)
        "e": ([], SIN_BLACK),     # Black Sin (elephant)
    }
    HEAVY = ("P", "R")            # mating material; lone general/elephant/horse can't force mate
    PAWN = StandardPawn(white_start=2, black_start=5, double=False)
    PROMOTION = _NoLastRankPromotion()
    CASTLING = NoCastling()

    # The eight pieces each side deploys from its reserve during the setup phase.
    RESERVE_WHITE = {"K": 1, "G": 1, "R": 2, "E": 2, "N": 2}
    RESERVE_BLACK = {"K": 1, "G": 1, "R": 2, "e": 2, "N": 2}

    _LABELS = {"E": "E", "e": "E", "G": "G", "K": "K", "R": "R", "N": "N", "P": "P"}
    _NAMES = {WHITE: "White", BLACK: "Black"}

    # ---- per-side helpers ---------------------------------------------------
    def _promo_squares(self, player):
        return WHITE_PROMO if player == WHITE else BLACK_PROMO

    def _own_region(self, player):
        """Rows a player may deploy into (its own three ranks)."""
        return range(0, 3) if player == WHITE else range(5, 8)

    def _back_rank(self, player):
        return 0 if player == WHITE else 7

    def _has_general(self, board, player):
        return any(pl == player and t == "G" for (pl, t) in board.values())

    def _in_setup(self, state) -> bool:
        return any(n > 0 for h in state.hands.values() for n in h.values())

    # ---- setup-phase placement (deployment) ---------------------------------
    def _setup_drops(self, state) -> list:
        """Legal "L@c,r" deployment placements for the side to move: a reserve
        piece onto an empty square in the player's own half, with the chariots
        (R) restricted to the back rank."""
        player = state.to_move
        hand = state.hands.get(player, {})
        letters = [L for L, n in hand.items() if n > 0]
        if not letters:
            return []
        out = []
        for r in self._own_region(player):
            for c in range(self.WIDTH):
                if (c, r) in state.board:
                    continue
                for L in letters:
                    if L == "R" and r != self._back_rank(player):
                        continue
                    out.append(f"{L}@{c},{r}")
        return out

    # ---- sit-tu promotion ---------------------------------------------------
    def _promotion_moves(self, state) -> list:
        """Sit-tu promotion moves for the side to move. A pawn standing on one of
        the player's promotion squares may, on its turn, become a general --
        either in place or by stepping to an adjacent *empty* diagonal square --
        but ONLY when the player currently has no general, and the promotion may
        not leave the player's own king in check.

        (The historical rule additionally forbids a promotion that immediately
        gives check / captures with the new general; that finer restriction is
        documented as an omitted simplification in rules.md.)"""
        player = state.to_move
        if self._has_general(state.board, player):
            return []
        promo_sqs = self._promo_squares(player)
        out = []
        for (c, r), (pl, t) in state.board.items():
            if pl != player or t != "P" or (c, r) not in promo_sqs:
                continue
            targets = [(c, r)]                      # in-place
            for dc, dr in DIAG:                     # adjacent diagonal, must be empty
                t2 = (c + dc, r + dr)
                if self.on(*t2) and t2 not in state.board:
                    targets.append(t2)
            for to in targets:
                b = dict(state.board)
                b.pop((c, r))
                b[to] = (player, "G")
                if self.in_check(b, player):        # may not leave own king in check
                    continue
                out.append(f"{c},{r}>{to[0]},{to[1]}=G")
        return out

    # ---- move generation ----------------------------------------------------
    def legal_moves(self, state) -> list:
        if self._in_setup(state):
            return self._setup_drops(state)
        if self._draw(state):
            return []
        out = []
        for f, t in self._legal(state):
            out.append(f"{f[0]},{f[1]}>{t[0]},{t[1]}")
        out.extend(self._promotion_moves(state))
        return out

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        if "@" in move:                              # deployment placement
            return self._apply_drop(state, move)
        if move.endswith("=G"):                      # sit-tu promotion
            return self._apply_promotion(state, move)
        return super().apply_move(state, move, rng)

    def _apply_promotion(self, state, move):
        raw = move[:-2]                              # strip "=G"
        fs, ts = raw.split(">")
        frm = tuple(int(x) for x in fs.split(","))
        to = tuple(int(x) for x in ts.split(","))
        pl = state.to_move
        b = dict(state.board)
        b.pop(frm)
        b[to] = (pl, "G")
        # promotion advances a pawn -> counts as progress (reset the no-progress clock)
        key = self._poskey(b, 1 - pl, state.castling, None, None)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=state.castling, ep=None,
                      halfmove=0, ply=state.ply + 1, reps=reps,
                      hands={}, promoted=frozenset())

    # ---- terminal / draws ---------------------------------------------------
    def is_terminal(self, state) -> bool:
        if self._in_setup(state):
            return False
        if self._draw(state):
            return True
        if self._legal(state):
            return False
        return not self._promotion_moves(state)

    def returns(self, state) -> list:
        if self._in_setup(state):
            return [0.0, 0.0]
        if self._draw(state) or not self.in_check(state.board, state.to_move):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # ---- initial state ------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for sq in WHITE_PAWNS:
            b[sq] = (WHITE, "P")
        for sq in BLACK_PAWNS:
            b[sq] = (BLACK, "P")
        return b

    def initial_state(self, options=None, rng=None):
        board = self.setup_board()
        hands = {WHITE: dict(self.RESERVE_WHITE), BLACK: dict(self.RESERVE_BLACK)}
        st = CState(board=board, to_move=WHITE, castling=frozenset(), ep=None,
                    hands=hands)
        st.reps = {self._poskey_state(st): 1}
        return st

    # We always carry a `hands` reserve (full in setup, empty in play) and the
    # base DropRules object stays the default NoDrops, so we override the few
    # hooks that gate on ``DROPS.enabled`` (serialize / poskey) to keep the
    # reserve in the state key and on the wire.
    def _poskey_state(self, state) -> str:
        return self._poskey(state.board, state.to_move, state.castling, state.ep,
                            state.hands)

    def serialize(self, state) -> dict:
        ep = state.ep
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "castling": "",
            "ep": None,
            "halfmove": state.halfmove,
            "ply": state.ply,
            "reps": dict(state.reps),
            "hands": {str(p): {L: n for L, n in sorted(h.items()) if n > 0}
                      for p, h in sorted(state.hands.items())},
        }

    def deserialize(self, d: dict):
        hands = {int(p): {L: int(n) for L, n in h.items()}
                 for p, h in d.get("hands", {}).items()}
        return CState(
            board={tuple(int(x) for x in k.split(",")): tuple(v)
                   for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(),
            ep=None,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            hands=hands,
            promoted=frozenset(),
        )

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if "@" in move:
            letter, cs = move.split("@")
            c, r = (int(x) for x in cs.split(","))
            return f"{self._LABELS.get(letter, letter)}@{'abcdefgh'[c]}{r + 1}"
        if move.endswith("=G"):
            raw = move[:-2]
            fs, ts = raw.split(">")
            fc, fr = (int(x) for x in fs.split(","))
            tc, tr = (int(x) for x in ts.split(","))
            frm = f"{'abcdefgh'[fc]}{fr + 1}"
            to = f"{'abcdefgh'[tc]}{tr + 1}"
            return f"P{frm}=G" if (fc, fr) == (tc, tr) else f"P{frm}-{to}=G"
        text = super().describe_move(state, move)
        return text.replace("e", "E", 1) if text[:1] == "e" else text

    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": self._LABELS.get(t, t)}
            for (c, r), (pl, t) in state.board.items()
        ]
        setup = self._in_setup(state)
        if self.is_terminal(state):
            ret = self.returns(state)
            caption = "Draw" if ret == [0.0, 0.0] else \
                f"{self._NAMES[0 if ret[0] > 0 else 1]} wins (checkmate)"
        elif setup:
            caption = f"{self._NAMES[state.to_move]} to deploy (setup phase)"
        elif self.in_check(state.board, state.to_move):
            caption = f"{self._NAMES[state.to_move]} to move (check)"
        else:
            caption = f"{self._NAMES[state.to_move]} to move"

        spec = {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
        # During the setup phase, tint the side-to-move's legal deployment region.
        if setup:
            player = state.to_move
            tint = "#3b6fb0" if player == WHITE else "#b03b3b"
            tints = {}
            for r in self._own_region(player):
                for c in range(self.WIDTH):
                    if (c, r) not in state.board:
                        tints[f"{c},{r}"] = tint
            if tints:
                spec["board"]["tints"] = tints
        # Reserve keys must stay the RAW move letters (the UI builds the drop move
        # "<key>@c,r"; Black's elephant is the letter "e", not the "E" label).
        spec["reserve"] = {
            str(p): {L: n for L, n in sorted(h.items()) if n > 0}
            for p, h in sorted(state.hands.items())
        }
        return spec
