"""Hex Shogi 91 (Fergus Duniho, November 2000).

Shogi adapted to the 91-hex hexagonal board of Gliński's / McCooey's Hexagonal
Chess -- but *oriented differently*: the hexes stand on a corner (POINTY-TOP), so
the board has **horizontal ranks and no vertical files** (Duniho's own words).
Instead of vertical files there are two leaning file directions. Everything else
is Shogi: captured pieces go to hand and may be dropped, the far four ranks are
the promotion zone, and you win by checkmate.

Board & coordinates
-------------------
Cells are axial "q,r" with cube s = -q-r and max(|q|,|r|,|s|) <= 5 (hexhex-6,
91 cells). ``r`` is the rank: r = -5 is rank **a** (the top row of the published
diagram, 6 cells) and r = +5 is rank **k** (the bottom row). The printed FILE
number is ``F = 6 - q - r = 6 + s`` (1..11), file 11 on the left and file 1 on
the right -- exactly like the diagram on chessvariants.com, and like Shogi's own
notation (files numbered right-to-left, ranks lettered from the top).
``describe_move`` therefore speaks "8b", "4j", ... Cell (q,r) <-> label F+rank.

Seat 0 = **Black / sente**, the bottom army (back rank k), moves first and
advances toward rank a (the -r direction). Seat 1 = White, the top army.

Directions (clock-face, as the designer describes them): the six ORTHOGONAL
(shared-edge) directions are the odd hours, the six DIAGONAL (shared-corner)
directions the even hours. Black's two orthogonally forward directions are
1 and 11 o'clock, and its three diagonally forward directions are 10, 12 and 2.
White's are the negations (the board is centrally symmetric, so a plain sign
flip of every offset is the colour flip).

Pieces (all verified against the family rules page, the Game Courier preset and
the designer's 2000 ZRF -- see rules.md)
    K  king           6 ortho + 6 diag steps (12)
    G  gold           6 ortho + 3 forward diag steps (9)
    S  silver         6 diag + 2 forward ortho steps (8)
    R  rook           slides on the 6 ortho rays
    B  bishop         slides on the 6 diag rays (colourbound)
    L  lance          slides on the 2 forward ortho rays
    N  knight         4 forward leaps (jumps): 2 ortho-forward then 60 deg
    P  pawn           1 step on either forward ortho direction (moves = captures)
  +P/+L/+N/+S move as a gold; +R = rook + diagonal step; +B = bishop + ortho step.

Rules as implemented (rules.md is the local source of truth)
------------------------------------------------------------
* Promotion zone = the opponent's first FOUR ranks (r <= -2 for Black,
  r >= 2 for White). A piece may promote when its move starts in or ends in the
  zone. Promotion is MANDATORY for a pawn/lance reaching the last rank and for a
  knight reaching either of the last two (they would otherwise be stuck); a
  dropped piece never promotes on the drop itself.
* Drops: onto any empty cell, never promoted, and a piece may not be dropped
  where it would have no move on an empty board (P/L not on the last rank,
  N not on the last two). There is NO nifu (two-pawns-per-file) rule -- files
  are not vertical here. In its place: a pawn may not be dropped onto a cell
  defended by another friendly *unpromoted* pawn, and a pawn drop may not give
  check at all (stronger than Shogi's drop-mate rule).
* Win by checkmate. **Stalemate is a DRAW**, and so are threefold repetition and
  50 turns (100 plies) with no capture -- the designer's family rules page lists
  exactly those three as draws. A hard ply cap is only a defensive backstop.
  Checkmate OUTRANKS all three counters: a mate delivered on the 100th quiet
  ply (or a third repetition, or the cap ply) is still a win, never 0-0 -- the
  same precedence agp.chesslike applies, and the only reading consistent with
  the designer's ZRF and Game Courier preset, which end on checkmate outright.

Move strings: "q1,r1>q2,r2" (+"=+" to promote) and "L@q,r" for a drop.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1
NAMES = {BLACK: "Black (sente)", WHITE: "White (gote)"}
N = 5                                   # hexhex side 6 -> coords in [-5, 5]
RANK_LETTERS = "abcdefghijk"            # rank a = r -5 (top) .. rank k = r +5

# --- directions (axial q,r), written in BLACK's frame; WHITE negates them -----
# Orthogonal = through a shared edge.  E, W, NE, NW, SW, SE.
ORTHO = ((1, 0), (-1, 0), (1, -1), (0, -1), (-1, 1), (0, 1))
# Diagonal = through a shared corner (sum of two adjacent orthogonals).
DIAG = ((1, -2), (-1, 2), (2, -1), (1, 1), (-2, 1), (-1, -1))
FWD_ORTHO = ((1, -1), (0, -1))                    # 1 and 11 o'clock
FWD_DIAG = ((1, -2), (2, -1), (-1, -1))           # 12, 2 and 10 o'clock
# Knight: one step orthogonally forward then one diagonally outward (a LEAP).
KNIGHT = ((-1, -2), (1, -3), (2, -3), (3, -2))
GOLD = ORTHO + FWD_DIAG
SILVER = DIAG + FWD_ORTHO
KING = ORTHO + DIAG

# (slide_dirs, leap_offsets) in the forward frame
BASE_MOVE = {
    "P": ((), FWD_ORTHO),
    "L": (FWD_ORTHO, ()),
    "N": ((), KNIGHT),
    "S": ((), SILVER),
    "G": ((), GOLD),
    "K": ((), KING),
    "R": (ORTHO, ()),
    "B": (DIAG, ()),
}
PROMO_MOVE = {
    "P": ((), GOLD), "L": ((), GOLD), "N": ((), GOLD), "S": ((), GOLD),
    "R": (ORTHO, DIAG),        # Dragon King:  rook + one diagonal step
    "B": (DIAG, ORTHO),        # Dragon Horse: bishop + one orthogonal step
}
CAN_PROMOTE = ("P", "L", "N", "S", "R", "B")
DROP_TYPES = ("P", "L", "N", "S", "G", "B", "R")   # the king is never in hand

REP_LIMIT = 3            # "the exact same position has been repeated three times"
NO_CAPTURE_PLIES = 100   # "fifty turns ... without anyone capturing a piece"
# Defensive termination backstop against a pathological loop -- NOT a rule, and
# deliberately far outside the observed distribution rather than inside it.
# Checkmate is the real terminator: over 300 measured uniform-random games with
# the cap disabled, 299 ended in checkmate and 1 by the no-capture rule, median
# 305 plies. Drops recycle material, so the tail is heavy: p95 = 2524, longest
# observed 10561. The empirical survival ratio is ~0.67 per further 500 plies
# (83/54/34/22/15/11 games of 300 running past 500/1000/1500/2000/2500/3000),
# which extrapolates to P(a random game reaches 50000) ~ 1e-18 -- i.e. this cap
# is dead code. The conformance harness is told about the tail through the
# manifest's `max_random_plies` instead of by shrinking this number. See rules.md.
PLY_CAP = 50000


def on_board(q: int, r: int) -> bool:
    return abs(q) <= N and abs(r) <= N and abs(q + r) <= N


def cells():
    for q in range(-N, N + 1):
        for r in range(-N, N + 1):
            if on_board(q, r):
                yield (q, r)


ALL_CELLS = tuple(sorted(cells()))
# One character per (owner, letter, promoted) for the compact repetition key.
# The promoted letters are the ones the Game Courier preset uses (t = tokin,
# m = +lance, y = +knight, v = +silver, d = dragon king, h = dragon horse).
_PROM_CHAR = {"P": "t", "L": "m", "N": "y", "S": "v", "R": "d", "B": "h"}


def file_of(q: int, r: int) -> int:
    """The printed file number 1..11 (constant along the NE/SW lattice line)."""
    return 6 - q - r


def cell_name(q: int, r: int) -> str:
    return f"{file_of(q, r)}{RANK_LETTERS[r + N]}"


def cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _in_zone(pl: int, r: int) -> bool:
    """The opponent's first four ranks."""
    return r <= -2 if pl == BLACK else r >= 2


def _last_rank(pl: int, r: int) -> bool:
    return r == -N if pl == BLACK else r == N


def _last_two(pl: int, r: int) -> bool:
    return r <= -N + 1 if pl == BLACK else r >= N - 1


def _setup_board() -> dict:
    """The published opening array (chessvariants.com diagram + the Game Courier
    preset; the 2000 ZRF has the left-right mirror image of it, which is the same
    game -- see rules.md)."""
    b = {}
    # --- seat 0 / Black: back rank k (r=5), rank j (r=4), pawns on rank h (r=2)
    for f, t in zip(range(6, 0, -1), "LNGGNL"):        # files 6..1
        b[(1 - f, 5)] = (BLACK, t)
    for f, t in zip(range(6, 1, -1), "RSKSB"):         # files 6..2
        b[(2 - f, 4)] = (BLACK, t)
    for f in range(1, 10):                             # files 1..9
        b[(4 - f, 2)] = (BLACK, "P")
    # --- seat 1 / White: back rank a (r=-5), rank b (r=-4), pawns rank d (r=-2)
    for f, t in zip(range(11, 5, -1), "LNGGNL"):       # files 11..6
        b[(11 - f, -5)] = (WHITE, t)
    for f, t in zip(range(10, 5, -1), "RSKSB"):        # files 10..6
        b[(10 - f, -4)] = (WHITE, t)
    for f in range(3, 12):                             # files 3..11
        b[(8 - f, -2)] = (WHITE, "P")
    return b


@dataclass
class HState:
    board: dict = field(default_factory=dict)          # (q,r) -> (player, letter)
    promoted: frozenset = field(default_factory=frozenset)
    hands: dict = field(default_factory=dict)          # player -> {letter: count}
    to_move: int = BLACK
    ply: int = 0
    since_cap: int = 0
    reps: dict = field(default_factory=dict)
    last: Optional[tuple] = None                       # cells to highlight
    key: str = ""                                      # cached position key


class HexShogi91(Game):
    name = "Hex Shogi 91"

    def __init__(self):
        # Reverse-attack tables per colour: offset -> {(letter, promoted)} of
        # pieces of that colour that attack across it. Colour flip = negation.
        self._leap_att = {BLACK: {}, WHITE: {}}
        self._slide_att = {BLACK: {}, WHITE: {}}
        kinds = [(L, False) for L in BASE_MOVE] + [(L, True) for L in PROMO_MOVE]
        for pl in (BLACK, WHITE):
            sign = 1 if pl == BLACK else -1
            for (letter, prom) in kinds:
                slides, leaps = self._movement(letter, prom)
                for (dq, dr) in leaps:
                    off = (dq * sign, dr * sign)
                    self._leap_att[pl].setdefault((-off[0], -off[1]), set()).add(
                        (letter, prom))
                for (dq, dr) in slides:
                    d = (dq * sign, dr * sign)
                    self._slide_att[pl].setdefault((-d[0], -d[1]), set()).add(
                        (letter, prom))

    # ---- geometry ----------------------------------------------------------
    @staticmethod
    def _movement(letter, promoted):
        return PROMO_MOVE[letter] if promoted else BASE_MOVE[letter]

    @staticmethod
    def _dirs(pl, offsets):
        if pl == BLACK:
            return offsets
        return tuple((-a, -b) for (a, b) in offsets)

    # ---- attacks / check ---------------------------------------------------
    def attacked(self, board, promoted, sq, by) -> bool:
        q, r = sq
        for (dq, dr), kinds in self._leap_att[by].items():
            t = (q + dq, r + dr)
            pc = board.get(t)
            if pc is not None and pc[0] == by and (pc[1], t in promoted) in kinds:
                return True
        for (dq, dr), kinds in self._slide_att[by].items():
            qq, rr = q + dq, r + dr
            while on_board(qq, rr):
                pc = board.get((qq, rr))
                if pc is not None:
                    if pc[0] == by and (pc[1], (qq, rr) in promoted) in kinds:
                        return True
                    break
                qq += dq
                rr += dr
        return False

    @staticmethod
    def _king(board, pl):
        for sq, (p, t) in board.items():
            if p == pl and t == "K":
                return sq
        return None

    def in_check(self, board, promoted, pl) -> bool:
        k = self._king(board, pl)
        return k is not None and self.attacked(board, promoted, k, 1 - pl)

    # ---- pseudo-moves ------------------------------------------------------
    def _piece_targets(self, board, sq, pl, letter, promoted):
        q, r = sq
        slides, leaps = self._movement(letter, promoted)
        for (dq, dr) in self._dirs(pl, leaps):
            t = (q + dq, r + dr)
            if on_board(*t) and (board.get(t) or (None,))[0] != pl:
                yield t
        for (dq, dr) in self._dirs(pl, slides):
            qq, rr = q + dq, r + dr
            while on_board(qq, rr):
                occ = board.get((qq, rr))
                if occ is None:
                    yield (qq, rr)
                else:
                    if occ[0] != pl:
                        yield (qq, rr)
                    break
                qq += dq
                rr += dr

    def _promotion_options(self, letter, promoted, frm, to, pl):
        """[False] / [True] / [False, True] -- the promotion choices for a move."""
        if promoted or letter not in CAN_PROMOTE:
            return (False,)
        if not (_in_zone(pl, frm[1]) or _in_zone(pl, to[1])):
            return (False,)
        # Mandatory when the piece would otherwise have no move at all.
        if letter in ("P", "L") and _last_rank(pl, to[1]):
            return (True,)
        if letter == "N" and _last_two(pl, to[1]):
            return (True,)
        return (False, True)

    def _board_after(self, state, frm, to, promote):
        b = dict(state.board)
        prom = set(state.promoted)
        pl, t = b.pop(frm)
        moved_prom = frm in state.promoted
        prom.discard(frm)
        prom.discard(to)
        if promote or moved_prom:
            prom.add(to)
        b[to] = (pl, t)
        return b, prom

    def _legal_board_moves(self, state):
        pl = state.to_move
        for sq, (p, t) in list(state.board.items()):
            if p != pl:
                continue
            prom = sq in state.promoted
            for to in self._piece_targets(state.board, sq, pl, t, prom):
                for promote in self._promotion_options(t, prom, sq, to, pl):
                    nb, npr = self._board_after(state, sq, to, promote)
                    if not self.in_check(nb, npr, pl):
                        yield sq, to, promote

    # ---- drops -------------------------------------------------------------
    def _drop_moves(self, state):
        pl = state.to_move
        letters = sorted(L for L, n in state.hands.get(pl, {}).items() if n > 0)
        if not letters:
            return []
        king = self._king(state.board, pl)
        opp_king = self._king(state.board, 1 - pl)
        in_chk = king is not None and self.attacked(
            state.board, state.promoted, king, 1 - pl)
        # Cells defended by a friendly UNPROMOTED pawn (the nifu replacement):
        # a pawn attacks its two forward orthogonal neighbours.
        pawn_guard = set()
        if "P" in letters:
            for (q, r), (p, t) in state.board.items():
                if p == pl and t == "P" and (q, r) not in state.promoted:
                    for (dq, dr) in self._dirs(pl, FWD_ORTHO):
                        pawn_guard.add((q + dq, r + dr))
        # Cells from which a dropped pawn would check the enemy king.
        pawn_check = set()
        if "P" in letters and opp_king is not None:
            for (dq, dr) in self._dirs(pl, FWD_ORTHO):
                pawn_check.add((opp_king[0] - dq, opp_king[1] - dr))
        out = []
        for sq in cells():
            if sq in state.board:
                continue
            for L in letters:
                if L in ("P", "L") and _last_rank(pl, sq[1]):
                    continue
                if L == "N" and _last_two(pl, sq[1]):
                    continue
                if L == "P" and (sq in pawn_guard or sq in pawn_check):
                    continue
                if in_chk:
                    # A drop can only block or capture nothing -- it never
                    # exposes the king, so this test is needed only in check.
                    b = dict(state.board)
                    b[sq] = (pl, L)
                    if self.in_check(b, state.promoted, pl):
                        continue
                out.append(f"{L}@{sq[0]},{sq[1]}")
        return out

    # ---- Game interface ----------------------------------------------------
    @property
    def num_players(self) -> int:
        return 2

    def current_player(self, state) -> int:
        return state.to_move

    def initial_state(self, options=None, rng=None):
        st = HState(board=_setup_board(), promoted=frozenset(),
                    hands={BLACK: {}, WHITE: {}}, to_move=BLACK)
        st.key = self._poskey(st)
        st.reps = {st.key: 1}
        return st

    def legal_moves(self, state):
        if self._draw_reason(state) is not None:
            return []
        out = []
        for frm, to, promote in self._legal_board_moves(state):
            m = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
            out.append(m + "=+" if promote else m)
        out.extend(self._drop_moves(state))
        return out

    def _has_move(self, state) -> bool:
        for _ in self._legal_board_moves(state):
            return True
        return bool(self._drop_moves(state))

    def _draw_reason(self, state):
        if state.reps.get(state.key or self._poskey(state), 0) >= REP_LIMIT:
            reason = "threefold repetition"
        elif state.since_cap >= NO_CAPTURE_PLIES:
            reason = "50 turns without a capture"
        elif state.ply >= PLY_CAP:
            reason = "move limit"
        else:
            return None
        # A draw counter has fired -- but CHECKMATE ENDS THE GAME IMMEDIATELY,
        # so a mating move is not nullified by the 50-turn counter, a threefold
        # repetition or the ply-cap backstop. (Same precedence as
        # agp.chesslike._draw / FIDE 5.1.1; both of the designer's own
        # executable sources -- the 2000 ZRF's `(loss-condition (checkmated
        # King))` and the Game Courier preset's `postgame` -- score checkmate
        # unconditionally, the draw counters being additions made by the prose
        # rules page.)  Without this, a mate delivered on the 100th quiet ply
        # scores 0-0.  Stalemate needs no special case (it draws either way),
        # so the extra move generation is confined to positions that are BOTH
        # counter-triggered and in check.
        if (self.in_check(state.board, state.promoted, state.to_move)
                and not self._has_move(state)):
            return None
        return reason

    def is_terminal(self, state) -> bool:
        if self._draw_reason(state) is not None:
            return True
        return not self._has_move(state)

    def returns(self, state):
        if self._draw_reason(state) is not None:
            return [0.0, 0.0]
        if self.in_check(state.board, state.promoted, state.to_move):
            # checkmate: the side to move loses
            return [-1.0, 1.0] if state.to_move == BLACK else [1.0, -1.0]
        return [0.0, 0.0]          # stalemate is a draw in Hex Shogi

    def apply_move(self, state, move, rng=None):
        if "@" in move:
            letter, cs = move.split("@")
            to = cell(cs)
            pl = state.to_move
            b = dict(state.board)
            b[to] = (pl, letter)
            hands = {p: dict(h) for p, h in state.hands.items()}
            hand = hands.setdefault(pl, {})
            hand[letter] = hand.get(letter, 0) - 1
            if hand[letter] <= 0:
                del hand[letter]
            return self._finish(b, set(state.promoted), hands, state,
                                state.since_cap + 1, (to,))

        promote = move.endswith("=+")
        raw = move[:-2] if promote else move
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)
        prom = set(state.promoted)
        hands = {p: dict(h) for p, h in state.hands.items()}

        captured = state.board.get(to)
        if captured is not None:                 # promoted pieces revert in hand
            hand = hands.setdefault(pl, {})
            hand[captured[1]] = hand.get(captured[1], 0) + 1

        moved_prom = frm in state.promoted
        prom.discard(frm)
        prom.discard(to)
        if promote or moved_prom:
            prom.add(to)
        b[to] = (pl, t)
        since = 0 if captured is not None else state.since_cap + 1
        return self._finish(b, prom, hands, state, since, (frm, to))

    def _finish(self, board, promoted, hands, state, since_cap, last):
        st = HState(board=board, promoted=frozenset(promoted), hands=hands,
                    to_move=1 - state.to_move, ply=state.ply + 1,
                    since_cap=since_cap, reps=dict(state.reps), last=last)
        st.key = self._poskey(st)
        st.reps[st.key] = st.reps.get(st.key, 0) + 1
        return st

    # ---- keys / (de)serialise ---------------------------------------------
    def _poskey(self, state) -> str:
        """Board + both hands + side to move, as one compact lossless string
        (91 cell characters, lower case = Black): the repetition key."""
        board, prom = state.board, state.promoted
        out = []
        for sq in ALL_CELLS:
            pc = board.get(sq)
            if pc is None:
                out.append(".")
            else:
                p, t = pc
                c = _PROM_CHAR.get(t, t) if sq in prom else t
                out.append(c.lower() if p == BLACK else c.upper())
        h = ";".join(
            f"{p}=" + ",".join(f"{L}{n}" for L, n in sorted(hd.items()) if n > 0)
            for p, hd in sorted(state.hands.items()))
        return "".join(out) + f"#{state.to_move}#{h}"

    def serialize(self, state) -> dict:
        return {
            "board": {f"{q},{r}": [p, t] for (q, r), (p, t) in state.board.items()},
            "promoted": [f"{q},{r}" for (q, r) in sorted(state.promoted)],
            "hands": {str(p): {L: n for L, n in sorted(hd.items()) if n > 0}
                      for p, hd in sorted(state.hands.items())},
            "to_move": state.to_move,
            "ply": state.ply,
            "since_cap": state.since_cap,
            "reps": dict(state.reps),
            "last": [f"{q},{r}" for (q, r) in state.last] if state.last else None,
        }

    def deserialize(self, d) -> HState:
        st = HState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            promoted=frozenset(cell(s) for s in d.get("promoted", [])),
            hands={int(p): {L: int(n) for L, n in hd.items()}
                   for p, hd in d.get("hands", {}).items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            since_cap=d.get("since_cap", 0),
            reps=dict(d.get("reps", {})),
            last=tuple(cell(s) for s in d["last"]) if d.get("last") else None,
        )
        st.key = self._poskey(st)
        return st

    # ---- presentation ------------------------------------------------------
    @staticmethod
    def _label(letter, promoted) -> str:
        return ("+" + letter) if promoted else letter

    def describe_move(self, state, move) -> str:
        if "@" in move:
            letter, cs = move.split("@")
            return f"{letter}*{cell_name(*cell(cs))}"
        promote = move.endswith("=+")
        raw = move[:-2] if promote else move
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        _, t = state.board.get(frm, (None, "?"))
        tag = self._label(t, frm in state.promoted)
        sep = "x" if to in state.board else "-"
        return f"{tag}{cell_name(*frm)}{sep}{cell_name(*to)}" + ("+" if promote else "")

    def render(self, state, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": p,
                   "label": self._label(t, (q, r) in state.promoted)}
                  for (q, r), (p, t) in state.board.items()]
        highlights = []
        if state.last:
            for c in state.last:
                highlights.append({"cell": f"{c[0]},{c[1]}", "kind": "last-move"})
        # The three hex colours: orthogonal neighbours always differ, diagonal
        # neighbours always match (so bishops are colourbound).
        shades = {0: "#b7bf7a", 1: "#dfe2ae", 2: "#8d9a55"}
        tints = {f"{q},{r}": shades[(q - r) % 3] for (q, r) in cells()}
        reason = self._draw_reason(state)
        if reason is not None:
            caption = f"Draw ({reason})"
        elif self.is_terminal(state):
            if self.in_check(state.board, state.promoted, state.to_move):
                caption = f"{NAMES[1 - state.to_move]} wins (checkmate)"
            else:
                caption = "Draw (stalemate)"
        else:
            chk = " — check" if self.in_check(
                state.board, state.promoted, state.to_move) else ""
            caption = f"{NAMES[state.to_move]} to move{chk}"
        return {
            # Pointy-top hexes ("hexagons that stand on a corner") give the
            # horizontal ranks the game is built on -> the renderer default.
            "board": {"type": "hex", "shape": "hexagon", "size": N + 1,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "reserve": {str(p): {L: n for L, n in sorted(hd.items()) if n > 0}
                        for p, hd in sorted(state.hands.items())},
        }

    # ---- bot eval ----------------------------------------------------------
    VALUES = {"P": 1.0, "L": 3.0, "N": 3.5, "S": 5.0, "G": 6.0,
              "B": 8.0, "R": 10.0, "K": 0.0}
    PROM_VALUES = {"P": 6.0, "L": 6.0, "N": 6.0, "S": 6.0, "B": 11.0, "R": 13.0}

    def heuristic(self, state) -> list:
        score = 0.0
        for sq, (p, t) in state.board.items():
            v = (self.PROM_VALUES[t] if sq in state.promoted else self.VALUES[t])
            score += v if p == BLACK else -v
        for p, hd in state.hands.items():
            for L, n in hd.items():
                v = self.VALUES[L] * n
                score += v if p == BLACK else -v
        val = math.tanh(score / 15.0)
        return [val, -val]
