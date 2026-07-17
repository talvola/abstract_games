"""McCooey's Hexagonal Chess (Dave McCooey & Richard Honeycutt, 1978-79).

Chess on the same regular hexagonal board of 91 hexes (side 6) as Glinski's
game, designed independently to be "the closest hexagonal equivalent to the
real game of chess". Army: K, Q, 2xR, 3xB, 2xN and SEVEN pawns per side
(vs Glinski's nine); every pawn starts exactly seven hexes from promotion,
and there are no unoccupied cells behind the pawn chain.

Board & coordinates
-------------------
Cells are axial hex coordinates "q,r" with cube s = -q-r and
max(|q|,|r|,|s|) <= 5 (a "hexhex-6" board, 91 cells). McCooey's own notation
(used in his published sample games) has 11 files a..k INCLUDING "j" (unlike
Glinski's a..l without "j"), with ranks that bend 60 deg at the central
f-file; the mapping used here (and by ``describe_move``) is:

    file letter = "abcdefghijk"[q+5]
    rank        = r0 - r + 1,  where r0 = 5 - max(q, 0)

so f1=(0,5) is White's near corner, f6=(0,0) the centre, f11=(0,-5) Black's
corner. White moves in the -r direction ("north").

Rules implemented (chessvariants.com hexchess2.html = McCooey's own page;
Wikipedia "Hexagonal chess"; see rules.md)
-------------------------------------------------------------------------
Identical to Glinski's game EXCEPT the starting array, the pawn's capturing
move, the f-pawn double-step exclusion, and the stalemate rule:

* Rook: 6 orthogonal (edge) directions. Bishop: 6 diagonal (vertex)
  directions (colourbound; the three bishops start on the three colours).
  Queen = rook + bishop (12 directions). King: one step in any of the 12;
  NO castling. Knight: two hexes orthogonally then one at 60 deg (a
  12-target hex leap), jumping over intervening pieces.
* Pawn: one vacant cell straight forward; it CAPTURES one cell along the two
  forward DIAGONAL (bishop-wise) directions -- like orthodox chess and unlike
  Glinski, whose pawns capture along the forward orthogonals. Every pawn
  except the centre pawn (f4 / f8) may advance two vacant cells straight
  forward on its first move (the centre-pawn exclusion stops White grabbing
  the centre hex on move one). Because a pawn can never re-enter a starting
  hex, "first move" is equivalent to "standing on its own starting hex".
  En passant: a pawn double-stepping across an enemy pawn's attack hex may
  be captured on that crossed hex on the immediately following move.
  Promotion to Q/R/B/N on reaching the end of any file (the 11 far-edge
  cells); forced, and free choice regardless of pieces on the board.
* Check/checkmate as in chess. STALEMATE IS A DRAW (1/2-1/2) -- McCooey
  chose the orthodox outcome, explicitly rejecting Glinski's 3/4-1/4 rule.
* Draws: 50-move rule (100 plies with no pawn move or capture), threefold
  repetition (same board+side+en-passant), and a defensive hard ply cap as
  a termination backstop. No "insufficient material" auto-draw (bare-king
  endings end via the 50-move rule; K+2N genuinely mates in this family).

Move strings: "q1,r1>q2,r2" with an "=Q/=R/=B/=N" suffix on promotions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefghijk"          # 11 files INCLUDING "j", per McCooey's notation
N = 5                          # hexhex side 6 -> coordinates in [-5, 5]
PLY_CAP = 1000                 # defensive backstop; 50-move rule ends games first

# --- directions (axial q,r; cube s = -q-r) ---------------------------------
# Orthogonal = through cell edges (rook); listed N, NE, SE, S, SW, NW where
# "N" (0,-1) is White's forward direction.
ORTHO = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
# Diagonal = through cell vertices (bishop): sums of adjacent orthogonals.
DIAG = [(1, -2), (2, -1), (1, 1), (-1, 2), (-2, 1), (-1, -1)]
# Knight: two orthogonal steps then one at 60 deg = cube perms of (1,2,-3).
KNIGHT = [(1, -3), (2, -3), (3, -2), (3, -1), (2, 1), (1, 2),
          (-1, 3), (-2, 3), (-3, 2), (-3, 1), (-2, -1), (-1, -2)]

PAWN_FWD = {WHITE: (0, -1), BLACK: (0, 1)}
# Captures: the two forward DIAGONAL (bishop) directions -- McCooey's key
# difference from Glinski (whose pawns capture along forward orthogonals).
PAWN_CAPS = {WHITE: [(1, -2), (-1, -1)], BLACK: [(-1, 2), (1, 1)]}

# --- start position --------------------------------------------------------
# Verified against three independent sources (McCooey's chessvariants.com
# page, his published sample games, and the Markmann Zillions ZRF):
# White: K g1, Q e1, N e2 g2, R d1 h1, B f1 f2 f3, P c1 d2 e3 f4 g3 h2 i1
# Black: K g10, Q e10, N e9 g9, R d9 h9, B f9 f10 f11, P c8..i8 (rank 8)
WHITE_PAWN_START = frozenset(
    [(-3, 5), (-2, 4), (-1, 3), (0, 2), (1, 2), (2, 2), (3, 2)])
BLACK_PAWN_START = frozenset(
    [(-3, -2), (-2, -2), (-1, -2), (0, -2), (1, -3), (2, -4), (3, -5)])
PAWN_START = {WHITE: WHITE_PAWN_START, BLACK: BLACK_PAWN_START}
# The centre pawn (f4 / f8) is denied the initial double step.
CENTRE_PAWN = {WHITE: (0, 2), BLACK: (0, -2)}


def _setup_board() -> dict:
    b = {}
    for c in WHITE_PAWN_START:
        b[c] = (WHITE, "P")
    for c in BLACK_PAWN_START:
        b[c] = (BLACK, "P")
    for c in [(-2, 5), (2, 3)]:            # d1, h1
        b[c] = (WHITE, "R")
    for c in [(-1, 4), (1, 3)]:            # e2, g2
        b[c] = (WHITE, "N")
    for c in [(0, 5), (0, 4), (0, 3)]:     # f1, f2, f3
        b[c] = (WHITE, "B")
    b[(-1, 5)] = (WHITE, "Q")              # e1
    b[(1, 4)] = (WHITE, "K")               # g1
    for c in [(-2, -3), (2, -5)]:          # d9, h9
        b[c] = (BLACK, "R")
    for c in [(-1, -3), (1, -4)]:          # e9, g9
        b[c] = (BLACK, "N")
    for c in [(0, -3), (0, -4), (0, -5)]:  # f9, f10, f11
        b[c] = (BLACK, "B")
    b[(-1, -4)] = (BLACK, "Q")             # e10
    b[(1, -5)] = (BLACK, "K")              # g10
    return b


def on_board(q: int, r: int) -> bool:
    return abs(q) <= N and abs(r) <= N and abs(q + r) <= N

def _is_promo(player: int, cell) -> bool:
    """End-of-file cells: the 11 far-edge hexes for each side."""
    q, r = cell
    if player == WHITE:
        return r == -N or q + r == -N
    return r == N or q + r == N

def cell_name(cell) -> str:
    """Axial (q,r) -> McCooey notation, e.g. (0,5) -> 'f1'."""
    q, r = cell
    r0 = 5 - max(q, 0)
    return f"{FILES[q + 5]}{r0 - r + 1}"

def _cell(sstr: str):
    q, r = sstr.split(",")
    return int(q), int(r)


@dataclass
class MState:
    board: dict = field(default_factory=_setup_board)  # (q,r) -> (owner, letter)
    to_move: int = WHITE
    # en passant: (target_cell, pawn_cell) set by the last double-step, or None
    ep: Optional[tuple] = None
    halfmove: int = 0     # plies since last pawn move / capture (50-move rule)
    ply: int = 0
    reps: dict = field(default_factory=dict)  # position key -> count (3-fold)
    last: Optional[tuple] = None              # (from, to) for highlights


def _poskey(board: dict, to_move: int, ep) -> str:
    items = sorted((q, r, o, t) for (q, r), (o, t) in board.items())
    ep_s = f"{ep[0][0]},{ep[0][1]}" if ep else "-"
    return f"{to_move}|{ep_s}|" + ";".join(f"{q},{r},{o},{t}" for q, r, o, t in items)


def _attacked(board: dict, cell, by: int) -> bool:
    """Is `cell` attacked by any piece of player `by`?"""
    q, r = cell
    # pawns (reverse of their capture directions)
    for dq, dr in PAWN_CAPS[by]:
        p = board.get((q - dq, r - dr))
        if p is not None and p[0] == by and p[1] == "P":
            return True
    # knights
    for dq, dr in KNIGHT:
        p = board.get((q + dq, r + dr))
        if p is not None and p[0] == by and p[1] == "N":
            return True
    # kings (adjacent in all 12 directions)
    for dq, dr in ORTHO + DIAG:
        p = board.get((q + dq, r + dr))
        if p is not None and p[0] == by and p[1] == "K":
            return True
    # sliders
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


class McCooeyChess(Game):

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> MState:
        s = MState()
        s.reps = {_poskey(s.board, s.to_move, s.ep): 1}
        return s

    def current_player(self, s: MState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _pseudo(self, s: MState) -> list:
        """Pseudo-legal moves as (frm, to, promo_or_None, is_ep)."""
        out = []
        me = s.to_move
        board = s.board
        for (q, r), (owner, t) in board.items():
            if owner != me:
                continue
            if t == "P":
                fq, fr = PAWN_FWD[me]
                one = (q + fq, r + fr)
                if on_board(*one) and one not in board:
                    if _is_promo(me, one):
                        for pc in ("Q", "R", "B", "N"):
                            out.append(((q, r), one, pc, False))
                    else:
                        out.append(((q, r), one, None, False))
                    # double step: from the pawn's own starting cell only,
                    # and never for the centre pawn (f4 / f8)
                    if (q, r) in PAWN_START[me] and (q, r) != CENTRE_PAWN[me]:
                        two = (q + 2 * fq, r + 2 * fr)
                        if on_board(*two) and two not in board:
                            out.append(((q, r), two, None, False))
                for dq, dr in PAWN_CAPS[me]:
                    tgt = (q + dq, r + dr)
                    if not on_board(*tgt):
                        continue
                    occ = board.get(tgt)
                    if occ is not None and occ[0] != me:
                        if _is_promo(me, tgt):
                            for pc in ("Q", "R", "B", "N"):
                                out.append(((q, r), tgt, pc, False))
                        else:
                            out.append(((q, r), tgt, None, False))
                    elif s.ep is not None and tgt == s.ep[0]:
                        out.append(((q, r), tgt, None, True))
            elif t == "N":
                for dq, dr in KNIGHT:
                    tgt = (q + dq, r + dr)
                    if on_board(*tgt):
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((q, r), tgt, None, False))
            elif t == "K":
                for dq, dr in ORTHO + DIAG:
                    tgt = (q + dq, r + dr)
                    if on_board(*tgt):
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((q, r), tgt, None, False))
            else:
                dirs = ORTHO if t == "R" else DIAG if t == "B" else ORTHO + DIAG
                for dq, dr in dirs:
                    cq, cr = q + dq, r + dr
                    while on_board(cq, cr):
                        occ = board.get((cq, cr))
                        if occ is None:
                            out.append(((q, r), (cq, cr), None, False))
                        else:
                            if occ[0] != me:
                                out.append(((q, r), (cq, cr), None, False))
                            break
                        cq += dq
                        cr += dr
        return out

    def _apply_board(self, board: dict, frm, to, promo, is_ep, mover: int) -> dict:
        nb = dict(board)
        owner, t = nb.pop(frm)
        if is_ep:
            fq, fr = PAWN_FWD[1 - mover]
            nb.pop((to[0] + fq, to[1] + fr), None)  # the double-stepped pawn
        nb[to] = (owner, promo if promo else t)
        return nb

    def _legal(self, s: MState) -> list:
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        me = s.to_move
        out = []
        for frm, to, promo, is_ep in self._pseudo(s):
            nb = self._apply_board(s.board, frm, to, promo, is_ep, me)
            if not _in_check(nb, me):
                out.append((frm, to, promo, is_ep))
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
        return [self._mstr(frm, to, promo) for frm, to, promo, _ in self._legal(s)]

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
        frm, to, promo, is_ep = match[0]
        me = s.to_move
        moved = s.board[frm]
        is_capture = is_ep or (to in s.board)
        nb = self._apply_board(s.board, frm, to, promo, is_ep, me)
        # en passant right: set only on a double step
        ep = None
        if moved[1] == "P" and abs(to[1] - frm[1]) == 2:
            mid = (frm[0], (frm[1] + to[1]) // 2)
            ep = (mid, to)
        irreversible = is_capture or moved[1] == "P"
        halfmove = 0 if irreversible else s.halfmove + 1
        # prior positions can never recur after an irreversible move
        reps = {} if irreversible else dict(s.reps)
        key = _poskey(nb, 1 - me, ep)
        reps[key] = reps.get(key, 0) + 1
        return MState(board=nb, to_move=1 - me, ep=ep, halfmove=halfmove,
                      ply=s.ply + 1, reps=reps, last=(frm, to))

    def is_terminal(self, s: MState) -> bool:
        if self._draw_reason(s) is not None:
            return True
        return len(self._legal(s)) == 0

    def returns(self, s: MState) -> list:
        if self._draw_reason(s) is not None:
            return [0.0, 0.0]
        if len(self._legal(s)) == 0:
            loser = s.to_move
            if _in_check(s.board, loser):          # checkmate
                return [-1.0, 1.0] if loser == WHITE else [1.0, -1.0]
            # Stalemate is a DRAW (1/2-1/2) in McCooey's game -- unlike
            # Glinski's 3/4-1/4 rule. See rules.md.
            return [0.0, 0.0]
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: MState) -> dict:
        return {
            "board": {f"{q},{r}": [o, t] for (q, r), (o, t) in s.board.items()},
            "to_move": s.to_move,
            "ep": ([f"{s.ep[0][0]},{s.ep[0][1]}", f"{s.ep[1][0]},{s.ep[1][1]}"]
                   if s.ep else None),
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
            "last": ([f"{s.last[0][0]},{s.last[0][1]}", f"{s.last[1][0]},{s.last[1][1]}"]
                     if s.last else None),
        }

    def deserialize(self, d: dict) -> MState:
        ep = d.get("ep")
        last = d.get("last")
        return MState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ep=(_cell(ep[0]), _cell(ep[1])) if ep else None,
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
        is_ep = s.ep is not None and to == s.ep[0] and piece is not None and piece[1] == "P" \
            and to not in s.board
        cap = "x" if (to in s.board or is_ep) else "-"
        out = f"{letter}{cell_name(frm)}{cap}{cell_name(to)}"
        if promo:
            out += f"={promo}"
        if is_ep:
            out += " e.p."
        return out

    def render(self, s: MState, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": o, "label": t}
                  for (q, r), (o, t) in s.board.items()]
        highlights = []
        if s.last is not None:
            for c in s.last:
                highlights.append({"cell": f"{c[0]},{c[1]}", "kind": "last-move"})
        # The three hex colours (bishop colour classes): colour = (q - r) mod 3.
        # McCooey specifies the CENTRE hex is the lightest ("white") colour.
        shades = {0: "#ffce9e", 1: "#e8ab6f", 2: "#d18b47"}  # light, mid, dark
        tints = {}
        for q in range(-N, N + 1):
            for r in range(-N, N + 1):
                if on_board(q, r):
                    tints[f"{q},{r}"] = shades[(q - r) % 3]
        if self.is_terminal(s):
            reason = self._draw_reason(s)
            if reason is not None:
                caption = f"Draw ({reason})"
            elif _in_check(s.board, s.to_move):
                caption = f"{NAMES[1 - s.to_move]} wins (checkmate)"
            else:
                caption = "Draw (stalemate)"
        else:
            check = " (check)" if _in_check(s.board, s.to_move) else ""
            caption = f"{NAMES[s.to_move]} to move{check}"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": N + 1, "tints": tints},
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
        v = math.tanh(bal / 8.0)
        return [v, -v]
