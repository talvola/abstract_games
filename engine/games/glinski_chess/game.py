"""Gliński's Hexagonal Chess (Władysław Gliński, 1936; launched 1949).

Chess on a regular hexagonal board of 91 hexes (side 6), the most widely played
hexagonal chess variant. Each side has the orthodox army plus one extra bishop
and one extra pawn (K Q R×2 B×3 N×2 P×9). The three bishops live on the three
hex colours.

Board & coordinates
-------------------
Cells are axial hex coordinates "q,r" with cube s = -q-r and
max(|q|,|r|,|s|) <= 5 (a "hexhex-6" board, 91 cells). Gliński's own notation
uses 11 files a..l (no "j") and ranks that bend 60 deg at the central f-file;
the mapping used here (and by ``describe_move``) is:

    file letter = "abcdefghikl"[q+5]
    rank        = r0 - r + 1,  where r0 = 5 - max(q, 0)

so f1=(0,5) is White's near corner, f6=(0,0) the centre, f11=(0,-5) Black's
corner. White moves in the -r direction ("north").

Rules implemented (Wikipedia "Hexagonal chess", chessvariants.com; see rules.md)
-------------------------------------------------------------------------------
* Rook: 6 orthogonal (edge) directions. Bishop: 6 diagonal (vertex)
  directions (colourbound; the three bishops start on the three colours).
  Queen = rook + bishop (12 directions). King: one step in any of the 12;
  NO castling. Knight: two hexes orthogonally then one at 60 deg (a
  12-target hex leap), jumping over intervening pieces.
* Pawn: one vacant cell straight forward. From ANY starting cell of a pawn of
  its colour (its own, or another friendly pawn's reached by capturing) it may
  instead advance two vacant cells forward. It captures one cell orthogonally
  forward at 60 deg to the vertical (the two forward rook directions that are
  NOT straight ahead), including en passant. It promotes to Q/R/B/N on
  reaching the end of any file (the 11 far-edge cells).
* Check/checkmate as in chess. STALEMATE IS NOT A DRAW: the stalemating side
  scores 3/4, the stalemated side 1/4 (tournament rule). On this engine's
  +1/0/-1 payoff scale that is +0.5 / -0.5 (chess points p map to 2p-1), so
  win > stalemate-win > draw > stalemated > loss orders correctly.
* Draws: 50-move rule (100 plies with no pawn move or capture), threefold
  repetition (same board+side+en-passant), and a defensive hard ply cap as a
  termination backstop. There is deliberately NO "insufficient material"
  auto-draw: unlike orthodox chess, K vs K stalemate is REACHABLE on the hex
  board (e.g. white Kf9 vs black Kf11, Black to move) and scores 3/4-1/4, so
  declaring bare kings drawn would misjudge a live position (see rules.md).

Move strings: "q1,r1>q2,r2" with an "=Q/=R/=B/=N" suffix on promotions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefghikl"          # no "j", per Gliński's official notation
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
# Captures: one cell orthogonally forward at 60 deg to the vertical.
PAWN_CAPS = {WHITE: [(1, -1), (-1, 0)], BLACK: [(1, 0), (-1, 1)]}

# --- start position (verified vs Wikipedia diagram + hexchess.club FEN) ----
# White: K g1, Q e1, B f1/f2/f3, N d1/h1, R c1/i1, P b1 c2 d3 e4 f5 g4 h3 i2 k1
# Black: K g10, Q e10, B f9/f10/f11, N d9/h9, R c8/i8, P b7..k7 (rank 7)
WHITE_PAWN_START = frozenset(
    [(-4, 5), (-3, 4), (-2, 3), (-1, 2), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1)])
BLACK_PAWN_START = frozenset(
    [(-4, -1), (-3, -1), (-2, -1), (-1, -1), (0, -1), (1, -2), (2, -3), (3, -4), (4, -5)])
PAWN_START = {WHITE: WHITE_PAWN_START, BLACK: BLACK_PAWN_START}


def _setup_board() -> dict:
    b = {}
    for c in WHITE_PAWN_START:
        b[c] = (WHITE, "P")
    for c in BLACK_PAWN_START:
        b[c] = (BLACK, "P")
    for c in [(-3, 5), (3, 2)]:
        b[c] = (WHITE, "R")
    for c in [(-2, 5), (2, 3)]:
        b[c] = (WHITE, "N")
    for c in [(0, 5), (0, 4), (0, 3)]:
        b[c] = (WHITE, "B")
    b[(-1, 5)] = (WHITE, "Q")
    b[(1, 4)] = (WHITE, "K")
    for c in [(-3, -2), (3, -5)]:
        b[c] = (BLACK, "R")
    for c in [(-2, -3), (2, -5)]:
        b[c] = (BLACK, "N")
    for c in [(0, -3), (0, -4), (0, -5)]:
        b[c] = (BLACK, "B")
    b[(-1, -4)] = (BLACK, "Q")
    b[(1, -5)] = (BLACK, "K")
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
    """Axial (q,r) -> Gliński notation, e.g. (0,5) -> 'f1'."""
    q, r = cell
    r0 = 5 - max(q, 0)
    return f"{FILES[q + 5]}{r0 - r + 1}"

def _cell(sstr: str):
    q, r = sstr.split(",")
    return int(q), int(r)


@dataclass
class GState:
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


class GlinskiChess(Game):

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GState:
        s = GState()
        s.reps = {_poskey(s.board, s.to_move, s.ep): 1}
        return s

    def current_player(self, s: GState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _pseudo(self, s: GState) -> list:
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
                    # double step from any friendly pawn starting cell
                    if (q, r) in PAWN_START[me]:
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

    def _legal(self, s: GState) -> list:
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
    def _draw_reason(self, s: GState) -> Optional[str]:
        if s.halfmove >= 100:
            return "50-move rule"
        if s.reps and max(s.reps.values()) >= 3:
            return "threefold repetition"
        if s.ply >= PLY_CAP:
            return "move limit"
        return None

    # ---- Game interface ----------------------------------------------------
    def legal_moves(self, s: GState) -> list:
        if self._draw_reason(s) is not None:
            return []
        return [self._mstr(frm, to, promo) for frm, to, promo, _ in self._legal(s)]

    def apply_move(self, s: GState, move: str, rng=None) -> GState:
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
        return GState(board=nb, to_move=1 - me, ep=ep, halfmove=halfmove,
                      ply=s.ply + 1, reps=reps, last=(frm, to))

    def is_terminal(self, s: GState) -> bool:
        if self._draw_reason(s) is not None:
            return True
        return len(self._legal(s)) == 0

    def returns(self, s: GState) -> list:
        if self._draw_reason(s) is not None:
            return [0.0, 0.0]
        if len(self._legal(s)) == 0:
            loser = s.to_move
            if _in_check(s.board, loser):          # checkmate
                return [-1.0, 1.0] if loser == WHITE else [1.0, -1.0]
            # Stalemate: 3/4 - 1/4 in chess points -> +0.5 / -0.5 on the
            # +1/0/-1 payoff scale (p points -> 2p-1). See rules.md.
            return [-0.5, 0.5] if loser == WHITE else [0.5, -0.5]
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: GState) -> dict:
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

    def deserialize(self, d: dict) -> GState:
        ep = d.get("ep")
        last = d.get("last")
        return GState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ep=(_cell(ep[0]), _cell(ep[1])) if ep else None,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            last=(_cell(last[0]), _cell(last[1])) if last else None,
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s: GState, move: str) -> str:
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

    def render(self, s: GState, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": o, "label": t}
                  for (q, r), (o, t) in s.board.items()]
        highlights = []
        if s.last is not None:
            for c in s.last:
                highlights.append({"cell": f"{c[0]},{c[1]}", "kind": "last-move"})
        # The three hex colours (bishop colour classes): colour = (q - r) mod 3.
        shades = {0: "#e8ab6f", 1: "#ffce9e", 2: "#d18b47"}  # mid, light, dark
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
                caption = (f"{NAMES[1 - s.to_move]} stalemates {NAMES[s.to_move]} "
                           f"(3/4 - 1/4)")
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

    def heuristic(self, s: GState) -> list:
        import math
        bal = 0.0
        for (o, t) in s.board.values():
            v = self.VALUES.get(t, 0.0)
            bal += v if o == WHITE else -v
        v = math.tanh(bal / 8.0)
        return [v, -v]
