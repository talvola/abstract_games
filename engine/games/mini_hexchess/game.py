"""Mini Hexchess (Dave McCooey, 1997).

A birthday present. On 21 April 1997 Hans Bodlaender put a 37-cell board on the
Chess Variant Pages and asked his readers to invent a game on it for his 37th
birthday; Dave McCooey noticed that 37 is a hexagonal number and that there is a
perfect hexagonal board of 37 hexes, and shrank his own 1978 hexagonal chess
onto it. ("I couldn't miss the opportunity: the next perfect hex board will be
when you're 61.")

It is McCooey's Hexagonal Chess on a hexhex-4 board (37 of the full game's 91
hexes), with a queenless army of K R B N + five pawns, no double step, no en
passant, and promotion to R/B/N only.

Board & coordinates
-------------------
Cells are axial hex coordinates "q,r" with cube s = -q-r and
max(|q|,|r|,|s|) <= 3 — a hexhex-4 board, 37 cells. The seven files a..g are
drawn VERTICAL (so the board renders flat-top, as in Gliński/McCooey/Shafran),
with ranks that bend 60 deg at the central d-file:

    file letter = "abcdefg"[q+3]
    rank        = r0 - r + 1,  where r0 = 3 - max(q, 0)

so d1=(0,3) is White's near corner, d4=(0,0) the centre and d7=(0,-3) Black's
corner. File lengths are 4,5,6,7,6,5,4. White moves in the -r direction.

Rules implemented (chessvariants.com/hexagonal.dir/minihex.html = Bodlaender's
write-up of McCooey's own email; greenchess.net/rules.php?v=mini-hex; the Game
Courier preset FEN; see rules.md)
--------------------------------------------------------------------------
* Setup, each side K R B N + 5 pawns. White: N c1, B d1, R e1, P b1, P f1,
  P c2, K d2, P e2, P d3. Black is the exact 180-degree rotation
  (N e6, B d7, R c6, P f5, P b5, P e5, K d6, P c5, P d5).
  NB the ranks are numbered from White's corner on EVERY file and the files
  are only 4-7 cells long, so Black's men sit on ranks 5-7 and cells like
  "e7"/"c7"/"b7"/"f7" DO NOT EXIST.
* Rook: 6 orthogonal (edge) directions. Bishop: 6 diagonal (vertex) directions
  (colourbound). King: one step in any of the 12. Knight: the 12-target hex
  leap. There is NO QUEEN in the array, though the piece exists in principle —
  and it can never appear, because a pawn may not promote to one.
* Pawn: one vacant cell straight forward; captures one cell along the two
  forward DIAGONAL (bishop-wise) directions, as in McCooey's game. There is
  NO initial double step and therefore NO en passant.
* Promotion: forced, to ROOK, BISHOP or KNIGHT — never a queen — on any of the
  SEVEN hexes of the opponent's side of the board (the two far edges, which
  meet at the far corner).
* No castling (as in McCooey's and Gliński's games).
* Check/checkmate as in chess, and checkmate ENDS THE GAME AT ONCE — it
  outranks the 50-move / repetition counters. STALEMATE IS A DRAW —
  McCooey's rule, explicitly not Gliński's 3/4-1/4.
* Draws: 50-move rule (100 plies with no pawn move or capture), threefold
  repetition (board + side to move), and a hard ply cap that is a pure
  termination backstop the 50-move rule provably beats.

Move strings: "q1,r1>q2,r2" with an "=R/=B/=N" suffix on promotions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefg"              # seven files, lengths 4 5 6 7 6 5 4
N = 3                          # hexhex side 4 -> coordinates in [-3, 3]
# Defensive termination backstop -- it must NEVER decide a game, or a live
# position becomes a bogus "move limit" draw. The 50-move rule is the real
# terminator. Bound: <=16 captures (18 men, 2 kings immortal) + <=60 pawn moves
# (10 pawns; every pawn move drops r by 1 or 2 and a pawn starts at r <= 3 and
# promotes by r = -3, so at most 6 moves each) = <=76 irreversible plies, with
# <=99 reversible plies in each of the 77 gaps around them => no game can
# exceed 76 + 77*99 = 7,699 plies. This cap is therefore unreachable dead code;
# selftest.py asserts the bound and measures random games against it.
PLY_CAP = 25000

# --- directions (axial q,r; cube s = -q-r) ---------------------------------
# Orthogonal = through cell edges (rook); listed N, NE, SE, S, SW, NW where
# "N" (0,-1) is White's forward direction.
ORTHO = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
# Diagonal = through cell vertices (bishop): sums of adjacent orthogonals.
DIAG = [(1, -2), (2, -1), (1, 1), (-1, 2), (-2, 1), (-1, -1)]
# Knight: two hexes orthogonally then one at 60 deg = cube perms of (1,2,-3).
KNIGHT = [(1, -3), (2, -3), (3, -2), (3, -1), (2, 1), (1, 2),
          (-1, 3), (-2, 3), (-3, 2), (-3, 1), (-2, -1), (-1, -2)]

PAWN_FWD = {WHITE: (0, -1), BLACK: (0, 1)}
# Captures: the two forward DIAGONAL (bishop) directions, exactly as McCooey.
PAWN_CAPS = {WHITE: [(1, -2), (-1, -1)], BLACK: [(-1, 2), (1, 1)]}

# Promotion choices: R, B, N -- NEVER Q. This is McCooey's own rule for this
# game and the reason no queen can ever reach the board.
PROMO_CHOICES = ("R", "B", "N")

# --- start position --------------------------------------------------------
# Double-sourced: read off the chessvariants.com setup diagram, and decoded
# independently from the Game Courier preset FEN
#   1prb/2pkn/3ppp/7/-PPP3/--NKP2/---BRP1   (cols 7)
# via q = col - 4, r = row - col. Both agree cell for cell, and the position is
# exactly 180-degree rotationally symmetric.
WHITE_START = {
    (-1, 3): "N", (0, 3): "B", (1, 2): "R",          # c1, d1, e1
    (-2, 3): "P", (2, 1): "P",                       # b1, f1
    (-1, 2): "P", (0, 2): "K", (1, 1): "P",          # c2, d2, e2
    (0, 1): "P",                                     # d3
}


def _setup_board() -> dict:
    b = {}
    for cell, letter in WHITE_START.items():
        b[cell] = (WHITE, letter)
        b[(-cell[0], -cell[1])] = (BLACK, letter)
    return b


def on_board(q: int, r: int) -> bool:
    return abs(q) <= N and abs(r) <= N and abs(q + r) <= N


CELLS = tuple((q, r) for q in range(-N, N + 1) for r in range(-N, N + 1)
              if on_board(q, r))


def _is_promo(player: int, cell) -> bool:
    """The seven hexes of the opponent's side: the two far edges of the hex."""
    q, r = cell
    if player == WHITE:
        return r == -N or q + r == -N
    return r == N or q + r == N


def cell_name(cell) -> str:
    """Axial (q,r) -> McCooey notation, e.g. (0,3) -> 'd1'."""
    q, r = cell
    r0 = N - max(q, 0)
    return f"{FILES[q + N]}{r0 - r + 1}"


def _cell(sstr: str):
    q, r = sstr.split(",")
    return int(q), int(r)


@dataclass
class MState:
    board: dict = field(default_factory=_setup_board)  # (q,r) -> (owner, letter)
    to_move: int = WHITE
    halfmove: int = 0     # plies since last pawn move / capture (50-move rule)
    ply: int = 0
    reps: dict = field(default_factory=dict)  # position key -> count (3-fold)
    last: Optional[tuple] = None              # (from, to) for highlights


def _poskey(board: dict, to_move: int) -> str:
    items = sorted((q, r, o, t) for (q, r), (o, t) in board.items())
    # No en-passant or castling state exists in this game, so board + side to
    # move is the complete position.
    return f"{to_move}|" + ";".join(f"{q},{r},{o},{t}" for q, r, o, t in items)


def _attacked(board: dict, cell, by: int) -> bool:
    """Is `cell` attacked by any piece of player `by`?"""
    q, r = cell
    for dq, dr in PAWN_CAPS[by]:                     # pawns (reverse)
        p = board.get((q - dq, r - dr))
        if p is not None and p[0] == by and p[1] == "P":
            return True
    for dq, dr in KNIGHT:
        p = board.get((q + dq, r + dr))
        if p is not None and p[0] == by and p[1] == "N":
            return True
    for dq, dr in ORTHO + DIAG:                      # kings
        p = board.get((q + dq, r + dr))
        if p is not None and p[0] == by and p[1] == "K":
            return True
    for dirs, letters in ((ORTHO, ("R", "Q")), (DIAG, ("B", "Q"))):
        for dq, dr in dirs:
            cq, cr = q + dq, r + dr
            while on_board(cq, cr):
                p = board.get((cq, cr))
                if p is not None:
                    if p[0] == by and p[1] in letters:
                        return True
                    break
                cq += dq
                cr += dr
    return False


def _king_cell(board: dict, player: int):
    for cell, (o, t) in board.items():
        if o == player and t == "K":
            return cell
    return None


def _in_check(board: dict, player: int) -> bool:
    k = _king_cell(board, player)
    return k is not None and _attacked(board, k, 1 - player)


class MiniHexchess(Game):

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> MState:
        s = MState()
        s.reps = {_poskey(s.board, s.to_move): 1}
        return s

    def current_player(self, s: MState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _pseudo(self, s: MState) -> list:
        """Pseudo-legal moves as (frm, to, promo_or_None)."""
        out = []
        me = s.to_move
        board = s.board
        for (q, r), (owner, t) in board.items():
            if owner != me:
                continue
            if t == "P":
                fq, fr = PAWN_FWD[me]
                one = (q + fq, r + fr)
                # one vacant cell straight forward -- NO double step, ever
                if on_board(*one) and one not in board:
                    if _is_promo(me, one):
                        for pc in PROMO_CHOICES:
                            out.append(((q, r), one, pc))
                    else:
                        out.append(((q, r), one, None))
                for dq, dr in PAWN_CAPS[me]:
                    tgt = (q + dq, r + dr)
                    if not on_board(*tgt):
                        continue
                    occ = board.get(tgt)
                    # no en passant: a capture needs a real enemy piece there
                    if occ is not None and occ[0] != me:
                        if _is_promo(me, tgt):
                            for pc in PROMO_CHOICES:
                                out.append(((q, r), tgt, pc))
                        else:
                            out.append(((q, r), tgt, None))
            elif t == "N":
                for dq, dr in KNIGHT:
                    tgt = (q + dq, r + dr)
                    if on_board(*tgt):
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((q, r), tgt, None))
            elif t == "K":
                for dq, dr in ORTHO + DIAG:
                    tgt = (q + dq, r + dr)
                    if on_board(*tgt):
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((q, r), tgt, None))
            else:
                dirs = ORTHO if t == "R" else DIAG if t == "B" else ORTHO + DIAG
                for dq, dr in dirs:
                    cq, cr = q + dq, r + dr
                    while on_board(cq, cr):
                        occ = board.get((cq, cr))
                        if occ is None:
                            out.append(((q, r), (cq, cr), None))
                        else:
                            if occ[0] != me:
                                out.append(((q, r), (cq, cr), None))
                            break
                        cq += dq
                        cr += dr
        return out

    def _apply_board(self, board: dict, frm, to, promo) -> dict:
        nb = dict(board)
        owner, t = nb.pop(frm)
        nb[to] = (owner, promo if promo else t)
        return nb

    def _legal(self, s: MState) -> list:
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        me = s.to_move
        out = []
        for frm, to, promo in self._pseudo(s):
            if not _in_check(self._apply_board(s.board, frm, to, promo), me):
                out.append((frm, to, promo))
        object.__setattr__(s, "_legal_cache", out)
        return out

    @staticmethod
    def _mstr(frm, to, promo) -> str:
        base = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
        return base + (f"={promo}" if promo else "")

    # ---- draws -------------------------------------------------------------
    def _draw_reason(self, s: MState) -> Optional[str]:
        if s.halfmove >= 100:
            return "50-move rule"
        if s.reps and max(s.reps.values()) >= 3:
            return "threefold repetition"
        if s.ply >= PLY_CAP:
            return "move limit"
        return None

    # ---- Game interface ----------------------------------------------------
    def legal_moves(self, s: MState) -> list:
        if self._draw_reason(s) is not None:
            return []
        return [self._mstr(*m) for m in self._legal(s)]

    def apply_move(self, s: MState, move: str, rng=None) -> MState:
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        frm_s, to_s = body.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        match = [m for m in self._legal(s)
                 if m[0] == frm and m[1] == to and (m[2] or None) == promo]
        if not match or self._draw_reason(s) is not None:
            raise ValueError(f"illegal move {move!r}")
        frm, to, promo = match[0]
        me = s.to_move
        moved = s.board[frm]
        is_capture = to in s.board
        nb = self._apply_board(s.board, frm, to, promo)
        irreversible = is_capture or moved[1] == "P"
        halfmove = 0 if irreversible else s.halfmove + 1
        # prior positions can never recur after an irreversible move
        reps = {} if irreversible else dict(s.reps)
        key = _poskey(nb, 1 - me)
        reps[key] = reps.get(key, 0) + 1
        return MState(board=nb, to_move=1 - me, halfmove=halfmove,
                      ply=s.ply + 1, reps=reps, last=(frm, to))

    def is_terminal(self, s: MState) -> bool:
        if self._draw_reason(s) is not None:
            return True
        return len(self._legal(s)) == 0

    def returns(self, s: MState) -> list:
        # CHECKMATE OUTRANKS THE DRAW COUNTERS. Chess ends the game the instant
        # the king is mated, so a mate delivered on the 100th reversible ply is
        # a win, not a "50-move rule" draw -- checking the counters first would
        # hand the mated side half a point. (Random play never lands on that
        # boundary, so only a constructed position exposes it; selftest.py has
        # one.) Stalemate IS a draw, as McCooey ruled -- never Glinski's 3/4-1/4.
        loser = s.to_move
        if len(self._legal(s)) == 0 and _in_check(s.board, loser):
            return [-1.0, 1.0] if loser == WHITE else [1.0, -1.0]
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: MState) -> dict:
        return {
            "board": {f"{q},{r}": [o, t] for (q, r), (o, t) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
            "last": ([f"{s.last[0][0]},{s.last[0][1]}",
                      f"{s.last[1][0]},{s.last[1][1]}"] if s.last else None),
        }

    def deserialize(self, d: dict) -> MState:
        last = d.get("last")
        return MState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            last=(_cell(last[0]), _cell(last[1])) if last else None,
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s: MState, move: str) -> str:
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        frm_s, to_s = body.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        piece = s.board.get(frm)
        letter = "" if piece is None or piece[1] == "P" else piece[1]
        cap = "x" if to in s.board else "-"
        out = f"{letter}{cell_name(frm)}{cap}{cell_name(to)}"
        if promo:
            out += f"={promo}"
        return out

    def render(self, s: MState, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": o, "label": t}
                  for (q, r), (o, t) in s.board.items()]
        highlights = []
        if s.last is not None:
            for c in s.last:
                highlights.append({"cell": f"{c[0]},{c[1]}", "kind": "last-move"})
        # The three hex colours (bishop colour classes): colour = (q - r) mod 3.
        # As in McCooey's full-size game, the CENTRE hex is the lightest.
        shades = {0: "#ffce9e", 1: "#e8ab6f", 2: "#d18b47"}
        tints = {f"{q},{r}": shades[(q - r) % 3] for q, r in CELLS}
        if self.is_terminal(s):
            reason = self._draw_reason(s)
            # same precedence as returns(): checkmate first, counters second
            if len(self._legal(s)) == 0 and _in_check(s.board, s.to_move):
                caption = f"{NAMES[1 - s.to_move]} wins (checkmate)"
            elif reason is not None:
                caption = f"Draw ({reason})"
            else:
                caption = f"Draw (stalemate — {NAMES[s.to_move]} has no move)"
        else:
            check = " (check)" if _in_check(s.board, s.to_move) else ""
            caption = f"{NAMES[s.to_move]} to move{check}"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": N + 1,
                      # q IS the file letter and the files are drawn VERTICAL
                      # (same board family as McCooey's), so: flat-top hexes.
                      "orientation": "flat", "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "pieceset": "chess",
        }

    # ---- bot eval ----------------------------------------------------------
    VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}

    def heuristic(self, s: MState) -> list:
        import math
        bal = 0.0
        for (o, t) in s.board.values():
            v = self.VALUES.get(t, 0.0)
            bal += v if o == WHITE else -v
        v = math.tanh(bal / 5.0)
        return [v, -v]
