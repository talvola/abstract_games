"""Pocket Mutation Chess (Michael Nelson, 2003) -- FIDE chess in which, instead
of a normal move, a player may pull one of their own pieces OFF the board into a
one-slot "pocket", where it may MUTATE into another piece of an equivalent value
class; on a later turn the pocketed piece is DROPPED back onto an empty square.

Source (authoritative): https://www.chessvariants.com/large.dir/pocketmutation.html

Rules as implemented (all FIDE rules apply except as noted):

* Each player has a pocket holding AT MOST ONE piece, empty at the start.
* POCKETING (only if the pocket is empty): as an entire move a player removes any
  of their own pieces EXCEPT the King into the pocket. White may NOT pocket on the
  very first move of the game.
    - Removed from the owner's 1st-7th rank: the piece keeps its value class but
      may OPTIONALLY mutate into any (other) piece of that class -- chosen at the
      moment of pocketing.
    - Removed from the owner's 8th rank: the piece PROMOTES to the next-higher
      value class (the exact piece is chosen at once); the AmazonRider (top class)
      has no higher class and is unchanged. This is the ONLY promotion in the game
      -- a pawn that reaches the 8th rank stays a pawn until it is pocketed.
* DROPPING (only if the pocket holds a piece): as an entire move the pocketed
  piece is placed on ANY empty square, EXCEPT it may not be dropped on the owner's
  8th rank.
* There is NO castling. A pawn on the 1st rank cannot double-step; a pawn on the
  2nd rank may double-step (however it got there); en passant is normal.
* The game is drawn if 50 consecutive moves pass with no capture and no promotion
  (a pocket-promotion counts; ordinary pawn pushes do NOT reset the counter).
  FIDE threefold repetition still applies -- the pocket contents are part of the
  repetition key.

The eight value classes (pieces with no note move as in FIDE chess):
  1: Pawn
  2: Knight, Bishop
  3: Rook, Nightrider, SuperBishop(Bishop+Wazir)
  4: Cardinal(Bishop+Knight), SuperRook(Rook+Ferz)
  5: Queen, Chancellor(Rook+Knight), CardinalRider(Bishop+Nightrider),
     SuperCardinal(Bishop+Knight+Wazir)
  6: ChancellorRider(Rook+Nightrider), SuperChancellor(Rook+Knight+Ferz),
     SuperCardinalRider(Bishop+Nightrider+Wazir)
  7: Amazon(Queen+Knight), SuperChancellorRider(Rook+Nightrider+Ferz)
  8: AmazonRider(Queen+Nightrider)

A Nightrider makes repeated Knight steps in one direction (a "knight-line"
slider); it is modelled as a slider whose eight step-vectors are the knight
offsets. Wazir = one step orthogonally, Ferz = one step diagonally (both leapers).

Move notation:
* normal move        "fc,fr>tc,tr"
* pocket a piece     "c,r>c,r=X"   (same-cell path; X = the chosen pocketed type)
* drop from pocket   "X@c,r"
The pocket is shown as a reserve tray above/below the board. White = player 0.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, PawnRules, PromotionRules, StandardPawn, DropRules, CState,
    cell, _FILES, WHITE, BLACK, ORTHO, DIAG, ALL8, KNIGHT,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

# --- piece movement table: {letter: (slide_dirs, leap_offsets)} -------------
# Nightrider slides along the knight vectors; Wazir leaps = ORTHO one-steps,
# Ferz leaps = DIAG one-steps.
PIECES = {
    "K": ([], ALL8),
    "N": ([], KNIGHT),
    "B": (DIAG, []),
    "R": (ORTHO, []),
    "Q": (ALL8, []),
    "H": (KNIGHT, []),               # Nightrider
    "S": (DIAG, ORTHO),              # SuperBishop         = Bishop + Wazir
    "C": (DIAG, KNIGHT),             # Cardinal            = Bishop + Knight (archbishop)
    "T": (ORTHO, DIAG),              # SuperRook           = Rook + Ferz
    "M": (ORTHO, KNIGHT),            # Chancellor          = Rook + Knight
    "D": (DIAG + KNIGHT, []),        # CardinalRider       = Bishop + Nightrider
    "E": (DIAG, KNIGHT + ORTHO),     # SuperCardinal       = Bishop + Knight + Wazir
    "G": (ORTHO + KNIGHT, []),       # ChancellorRider     = Rook + Nightrider
    "J": (ORTHO, KNIGHT + DIAG),     # SuperChancellor     = Rook + Knight + Ferz
    "L": (DIAG + KNIGHT, ORTHO),     # SuperCardinalRider  = Bishop + Nightrider + Wazir
    "A": (ALL8, KNIGHT),             # Amazon              = Queen + Knight
    "U": (ORTHO + KNIGHT, DIAG),     # SuperChancellorRider= Rook + Nightrider + Ferz
    "Z": (ALL8 + KNIGHT, []),        # AmazonRider         = Queen + Nightrider
}

# The eight value classes (0-based here; class N in the rules is index N-1).
CLASSES = [
    ["P"],                       # class 1
    ["N", "B"],                  # class 2
    ["R", "H", "S"],             # class 3
    ["C", "T"],                  # class 4
    ["Q", "M", "D", "E"],        # class 5
    ["G", "J", "L"],             # class 6
    ["A", "U"],                  # class 7
    ["Z"],                       # class 8
]
CLASS_OF = {p: i for i, cls in enumerate(CLASSES) for p in cls}

PIECE_NAMES = {
    "P": "Pawn", "N": "Knight", "B": "Bishop", "R": "Rook", "Q": "Queen",
    "H": "Nightrider", "S": "SuperBishop", "C": "Cardinal", "T": "SuperRook",
    "M": "Chancellor", "D": "CardinalRider", "E": "SuperCardinal",
    "G": "ChancellorRider", "J": "SuperChancellor", "L": "SuperCardinalRider",
    "A": "Amazon", "U": "SuperChancellorRider", "Z": "AmazonRider",
}


class NoPromotion(PromotionRules):
    """Pawns never promote by moving in this game (rule 4)."""

    def options(self, core, state, frm, to):
        return [None]


class PocketDrops(DropRules):
    """The pocket: a one-slot reserve. Captures are NEVER banked (only your own
    pocketed piece is ever in hand); a piece may be dropped on any empty square
    except the owner's 8th rank."""

    enabled = True

    def initial_hands(self, core) -> dict:
        return {WHITE: {}, BLACK: {}}

    def can_drop_on(self, core, state, letter, to, player) -> bool:
        eighth = core.HEIGHT - 1 if player == WHITE else 0
        return to[1] != eighth

    def captured_to_hand(self, core, letter, was_promoted):
        return None


class PocketMutationChess(ChessLike):
    uid = "pocket_mutation_chess"
    name = "Pocket Mutation Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = PIECES
    HEAVY = tuple(L for L in CLASS_OF if L not in ("N", "B"))
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = NoPromotion()
    DROPS = PocketDrops()
    # Suppress the movement-derived archbishop/chancellor icon on the "super"
    # compounds (they carry an extra Wazir/Ferz the icon would not convey); they
    # render as their letter instead. Cardinal(C)/Chancellor(M)/Amazon(A) keep
    # their correct auto-derived icons.
    ICONS = {"E": None, "J": None}

    # Rough class-based material values for the MCTS rollout heuristic.
    PIECE_VALUES = {
        "K": 0.0, "P": 1.0,
        "N": 3.0, "B": 3.0,
        "R": 5.0, "H": 5.0, "S": 5.0,
        "C": 7.0, "T": 7.0,
        "Q": 9.0, "M": 9.0, "D": 9.0, "E": 9.0,
        "G": 11.0, "J": 11.0, "L": 11.0,
        "A": 13.0, "U": 13.0,
        "Z": 15.0,
    }

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    # ---- geometry helper ----------------------------------------------------
    def _on_eighth(self, sq, player) -> bool:
        """True if square ``sq`` is on ``player``'s own 8th (far) rank."""
        return sq[1] == (self.HEIGHT - 1 if player == WHITE else 0)

    # ---- king-safety board (override: NO auto pawn-promotion) ---------------
    def _apply_board(self, board, frm, to, ep):
        b = dict(board)
        pl, t = b.pop(frm)
        if t == "P" and ep is not None and to == ep[0] and to not in board:
            b.pop(ep[1], None)
        b[to] = (pl, t)           # pawns do NOT promote on reaching the last rank
        return b

    # ---- move generation ----------------------------------------------------
    def _pocket_moves(self, state) -> list:
        """Legal "c,r>c,r=X" pocketing moves for the side to move."""
        player = state.to_move
        if state.ply == 0:                    # White may not pocket on move 1
            return []
        hand = state.hands.get(player, {})
        if any(n > 0 for n in hand.values()):  # pocket must be empty
            return []
        out = []
        for (c, r), (pl, t) in list(state.board.items()):
            if pl != player or t == "K":
                continue
            b = dict(state.board)
            b.pop((c, r))
            if self.in_check(b, player):       # may not expose own king (pin/check)
                continue
            cls = CLASS_OF[t]
            target = cls
            if self._on_eighth((c, r), player) and cls < len(CLASSES) - 1:
                target = cls + 1               # 8th-rank pocketing promotes a class
            for X in CLASSES[target]:
                out.append(f"{c},{r}>{c},{r}={X}")
        return out

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        out = [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for f, t in self._legal(state)]
        out.extend(self._drop_moves(state))
        out.extend(self._pocket_moves(state))
        return out

    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        return not self.legal_moves(state)

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        if "@" in move:
            return self._apply_drop(state, move)      # drop from pocket
        if "=" in move:
            return self._apply_pocket(state, move)     # pocket a piece
        return self._apply_normal(state, move)         # ordinary board move

    def _apply_normal(self, state, move):
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)
        capture = to in state.board
        ep_new = None
        if t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                b.pop(state.ep[1], None)                # en-passant capture
                capture = True
            else:
                ep_new = self.PAWN.ep_after(frm, to)
        b[to] = (pl, t)                                # no move-promotion
        hands = {p: dict(h) for p, h in state.hands.items()}
        reset = capture                                # pawn pushes do NOT reset
        key = self._poskey(b, 1 - pl, state.castling, ep_new, hands)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=state.castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps, hands=hands,
                      promoted=state.promoted)

    def _apply_pocket(self, state, move):
        raw, X = move.split("=")
        fs, _ = raw.split(">")
        frm = cell(fs)
        pl, t = state.board[frm]
        cls = CLASS_OF[t]
        promoted = self._on_eighth(frm, pl) and cls < len(CLASSES) - 1 and X != t
        b = dict(state.board)
        b.pop(frm)
        hands = {p: dict(h) for p, h in state.hands.items()}
        hands[pl] = {X: 1}
        key = self._poskey(b, 1 - pl, state.castling, None, hands)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=state.castling, ep=None,
                      halfmove=0 if promoted else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps, hands=hands,
                      promoted=state.promoted)

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if "@" in move:
            letter, cs = move.split("@")
            c = cell(cs)
            return f"{letter}@{_FILES[c[0]]}{c[1] + 1}"
        if "=" in move:
            raw, X = move.split("=")
            fs, ts = raw.split(">")
            frm, to = cell(fs), cell(ts)
            if frm == to:                              # pocketing
                _, t = state.board.get(frm, (None, "?"))
                sq = f"{_FILES[frm[0]]}{frm[1] + 1}"
                return f"{t}{sq}=>pocket" if X == t else f"{t}{sq}=>pocket:{X}"
        return super().describe_move(state, move)

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        spec["choiceNames"] = dict(PIECE_NAMES)
        return spec
