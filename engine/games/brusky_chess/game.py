"""Brusky's Hexagonal Chess (Yakov Brusky, USSR, 1966).

Chess on an irregular hexagonal board of 84 cells with HORIZONTAL ranks and
slanting files -- the other orientation family from Gliński's (whose files are
vertical).  Each side has the orthodox army plus one extra bishop (three, one
per hex colour) and one extra pawn, and the two kings sit on OPPOSITE wings so
that the position has 180-degree rotational symmetry.

Board & coordinates
-------------------
Brusky's own notation names a cell by a *left-leaning* file letter a..l and a
horizontal rank 1..8::

    a1-a5   b1-b6   c1-c7   d1-d8 ... i1-i8   j2-j8   k3-k8   l4-l8   = 84 cells

Internally a cell is an axial hex coordinate ``"q,r"`` with::

    q = file index (a=0 .. l=11)        r = -rank (rank 1 = -1 .. rank 8 = -8)

so a cell exists iff ``0 <= q <= 11``, ``-8 <= r <= -1`` and ``-5 <= q+r <= 7``
(``q+r`` is the index of the *right*-leaning file, which is why the two cut
corners are exactly the ``q+r < -5`` and ``q+r > 7`` triangles).  The web
renderer draws pointy-top hexes at ``x = sqrt(3)(q + r/2), y = 1.5r``, so
constant ``r`` is a horizontal row and rank 1 (r = -1) sits at the bottom for
White -- the board's natural orientation.

Because the axial frame is just Gliński's rotated, the direction TABLES are
identical to ``glinski_chess``'s (6 orthogonals, 6 diagonals, 12 knight leaps);
only which vector is "forward" for a pawn differs -- a Brusky pawn has TWO
forward orthogonals.

Rules implemented (chessvariants.com/rules/bruskyshexagonalchess, which follows
Pritchard's *Encyclopedia of Chess Variants*; see rules.md)
------------------------------------------------------------------------------
* Rook 6 orthogonals, bishop 6 diagonals (colourbound; three bishops on the
  three colours), queen = both, knight = the 12-target hex leap, king one step
  in any of the 12 directions -- exactly as in Gliński's.
* Castling: the king moves TWO cells toward the rook on the king's side
  (O-O) or THREE toward the rook on the queen's side (O-O-O); the rook hops to
  the cell on the king's far side.  All orthodox castling conditions apply.
* Pawn (the variant's distinctive part):
  - two orthogonally forward directions;
  - a double step from the pawn's own starting rank may not change direction;
  - an ENEMY piece adjacent in one forward direction blocks the other forward
    direction too (a friendly piece blocks only its own direction);
  - captures on the two slanted forward diagonals always, and additionally on
    the fully vertical forward diagonal while the pawn stands on its starting
    rank;
  - en passant; promotion to Q/R/B/N on the far rank.
* Stalemate is a DRAW and the rest of orthodox chess applies (checkmate, 50-move
  rule, threefold repetition, bare kings).  A hard ply cap is a defensive
  backstop only -- see PLY_CAP.

Move strings: "q1,r1>q2,r2" plus an "=Q/=R/=B/=N" suffix on promotions;
castling is written as the king's two- or three-cell move.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefghijkl"          # 12 left-leaning files; Brusky's notation uses "j"

# The 50-move rule always fires first: a pawn advances at most 6 ranks and there
# are 10 pawns a side (<= 120 pawn moves) and at most 36 capturable units, so a
# game contains at most 156 irreversible plies and therefore at most
# 156 + 157*100 = 15,856 plies before "halfmove >= 100" ends it.  PLY_CAP is set
# above that bound, so it is dead code that can only fire if a rule above it is
# broken -- it is NEVER outcome-load-bearing.
PLY_CAP = 20000

# --- directions (axial q,r; cube s = -q-r) ---------------------------------
# Orthogonal = through cell edges (rook), listed NW, NE, E, SE, SW, W.
ORTHO = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
# Diagonal = through cell vertices (bishop): sums of adjacent orthogonals.
# (1,-2) is "straight up the board", (-1,2) straight down.
DIAG = [(1, -2), (2, -1), (1, 1), (-1, 2), (-2, 1), (-1, -1)]
# Knight: one orthogonal step then one OUTWARD diagonal step = the 12 cells of
# the fourth perimeter a queen cannot reach.
KNIGHT = [(1, -3), (2, -3), (3, -2), (3, -1), (2, 1), (1, 2),
          (-1, 3), (-2, 3), (-3, 2), (-3, 1), (-2, -1), (-1, -2)]

# Pawns: two forward orthogonals, two slanted forward diagonals, and the fully
# vertical forward diagonal (a capture direction only from the starting rank).
PAWN_FWD = {WHITE: [(0, -1), (1, -1)], BLACK: [(0, 1), (-1, 1)]}
PAWN_SLANT = {WHITE: [(-1, -1), (2, -1)], BLACK: [(1, 1), (-2, 1)]}
PAWN_VERT = {WHITE: (1, -2), BLACK: (-1, 2)}
HOME_RANK = {WHITE: -2, BLACK: -7}      # r of the pawns' starting rank
PROMO_RANK = {WHITE: -8, BLACK: -1}     # r of the far rank
PROMO_PIECES = ("Q", "R", "B", "N")

# --- castling (king's side = the rook next to the king; queen's side = the
# rook beyond the queen).  Each entry: king from/to, rook from/to, the cells
# between king and rook that must be empty, and the king's transit path that
# must not be attacked. -------------------------------------------------------
CASTLES = {
    "K": {"player": WHITE, "kfrom": (5, -1), "kto": (7, -1),
          "rfrom": (8, -1), "rto": (6, -1),
          "empty": [(6, -1), (7, -1)],
          "path": [(5, -1), (6, -1), (7, -1)], "name": "O-O"},
    "Q": {"player": WHITE, "kfrom": (5, -1), "kto": (2, -1),
          "rfrom": (0, -1), "rto": (3, -1),
          "empty": [(1, -1), (2, -1), (3, -1), (4, -1)],
          "path": [(5, -1), (4, -1), (3, -1), (2, -1)], "name": "O-O-O"},
    "k": {"player": BLACK, "kfrom": (6, -8), "kto": (4, -8),
          "rfrom": (3, -8), "rto": (5, -8),
          "empty": [(4, -8), (5, -8)],
          "path": [(6, -8), (5, -8), (4, -8)], "name": "O-O"},
    "q": {"player": BLACK, "kfrom": (6, -8), "kto": (9, -8),
          "rfrom": (11, -8), "rto": (8, -8),
          "empty": [(7, -8), (8, -8), (9, -8), (10, -8)],
          "path": [(6, -8), (7, -8), (8, -8), (9, -8)], "name": "O-O-O"},
}
FLAGS_BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
ROOK_HOME = {c["rfrom"]: f for f, c in CASTLES.items()}
KING_HOME = {(5, -1): WHITE, (6, -8): BLACK}
ALL_RIGHTS = frozenset("KQkq")


def on_board(q: int, r: int) -> bool:
    return 0 <= q <= 11 and -8 <= r <= -1 and -5 <= q + r <= 7


CELLS = frozenset((q, r) for q in range(12) for r in range(-8, 0) if on_board(q, r))


def cell_name(cell) -> str:
    """Axial (q,r) -> Brusky notation, e.g. (2,-4) -> 'c4'."""
    q, r = cell
    return f"{FILES[q]}{-r}"


def name_to_cell(name: str):
    """Brusky notation -> axial, e.g. 'c4' -> (2,-4)."""
    return (FILES.index(name[0]), -int(name[1:]))


def _cell(sstr: str):
    q, r = sstr.split(",")
    return int(q), int(r)


def _setup_board() -> dict:
    """White R a1 N b1 B c1 Q d1 B e1 K f1 B g1 N h1 R i1, pawns a2-j2;
    Black the 180-degree rotation: R d8 N e8 B f8 K g8 B h8 Q i8 B j8 N k8 R l8,
    pawns c7-l7.  (The kings really do stand on opposite wings.)"""
    b = {}
    back = "RNBQBKBNR"
    for i, t in enumerate(back):
        b[(i, -1)] = (WHITE, t)                 # a1 .. i1
        b[(11 - i, -8)] = (BLACK, t)            # l8 .. d8
    for q in range(0, 10):
        b[(q, -2)] = (WHITE, "P")               # a2 .. j2
    for q in range(2, 12):
        b[(q, -7)] = (BLACK, "P")               # c7 .. l7
    return b


def pawn_caps(player: int, cell) -> list:
    """The directions this pawn captures in: the two slants always, plus the
    fully vertical diagonal while it stands on its own starting rank."""
    caps = list(PAWN_SLANT[player])
    if cell[1] == HOME_RANK[player]:
        caps.append(PAWN_VERT[player])
    return caps


@dataclass
class BState:
    board: dict = field(default_factory=_setup_board)  # (q,r) -> (owner, letter)
    to_move: int = WHITE
    castling: frozenset = ALL_RIGHTS
    # en passant: (target_cell, pawn_cell) set by the last double step, or None
    ep: Optional[tuple] = None
    halfmove: int = 0     # plies since last pawn move / capture (50-move rule)
    ply: int = 0
    reps: dict = field(default_factory=dict)   # position key -> count (threefold)
    last: Optional[tuple] = None               # (from, to) for highlights


def _poskey(board: dict, to_move: int, castling, ep) -> str:
    items = sorted((q, r, o, t) for (q, r), (o, t) in board.items())
    ep_s = f"{ep[0][0]},{ep[0][1]}" if ep else "-"
    return (f"{to_move}|{''.join(sorted(castling))}|{ep_s}|"
            + ";".join(f"{q},{r},{o},{t}" for q, r, o, t in items))


def _attacked(board: dict, cell, by: int) -> bool:
    """Is `cell` attacked by any piece of player `by`?  (Pawn attacks use the
    same starting-rank rule as pawn captures.)"""
    q, r = cell
    for dq, dr in PAWN_SLANT[by]:
        p = board.get((q - dq, r - dr))
        if p is not None and p == (by, "P"):
            return True
    dq, dr = PAWN_VERT[by]
    src = (q - dq, r - dr)
    if src[1] == HOME_RANK[by] and board.get(src) == (by, "P"):
        return True
    for dq, dr in KNIGHT:
        p = board.get((q + dq, r + dr))
        if p is not None and p == (by, "N"):
            return True
    for dq, dr in ORTHO + DIAG:
        p = board.get((q + dq, r + dr))
        if p is not None and p == (by, "K"):
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


def _ep_right(letter: str, player: int, frm, to):
    """The en-passant right created by a move, or None.

    It must be recognised by the DIRECTION of the step, not by |dr| == 2: the
    vertical-diagonal capture (1,-2)/(-1,2) also spans two ranks but is not a
    double step.  The right records both the skipped cell (the capture target)
    and the double-stepper's cell (the pawn to remove) -- with two forward
    directions the victim is not at a fixed offset from the target."""
    if letter != "P":
        return None
    d = (to[0] - frm[0], to[1] - frm[1])
    for dq, dr in PAWN_FWD[player]:
        if d == (2 * dq, 2 * dr):
            return ((frm[0] + dq, frm[1] + dr), to)
    return None


def _king_cell(board: dict, player: int):
    for cell, (o, t) in board.items():
        if o == player and t == "K":
            return cell
    return None


def _in_check(board: dict, player: int) -> bool:
    k = _king_cell(board, player)
    return k is not None and _attacked(board, k, 1 - player)


class BruskyChess(Game):

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> BState:
        s = BState()
        s.reps = {_poskey(s.board, s.to_move, s.castling, s.ep): 1}
        return s

    def current_player(self, s: BState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _pseudo(self, s: BState) -> list:
        """Pseudo-legal moves as (frm, to, promo_or_None, ep_victim_or_None)."""
        out = []
        me = s.to_move
        board = s.board
        for (q, r), (owner, t) in board.items():
            if owner != me:
                continue
            if t == "P":
                self._pawn_moves(board, s.ep, me, (q, r), out)
            elif t == "N":
                for dq, dr in KNIGHT:
                    tgt = (q + dq, r + dr)
                    if tgt in CELLS:
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((q, r), tgt, None, None))
            elif t == "K":
                for dq, dr in ORTHO + DIAG:
                    tgt = (q + dq, r + dr)
                    if tgt in CELLS:
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((q, r), tgt, None, None))
            else:
                dirs = ORTHO if t == "R" else DIAG if t == "B" else ORTHO + DIAG
                for dq, dr in dirs:
                    cq, cr = q + dq, r + dr
                    while on_board(cq, cr):
                        occ = board.get((cq, cr))
                        if occ is None:
                            out.append(((q, r), (cq, cr), None, None))
                        else:
                            if occ[0] != me:
                                out.append(((q, r), (cq, cr), None, None))
                            break
                        cq += dq
                        cr += dr
        out.extend(self._castles(s))
        return out

    def _pawn_moves(self, board: dict, ep, me: int, cell, out: list) -> None:
        q, r = cell
        promo_r = PROMO_RANK[me]
        # --- non-capturing advances.  An ENEMY piece adjacent in EITHER forward
        # direction blocks BOTH; a friendly one blocks only its own direction.
        blocked = False
        for dq, dr in PAWN_FWD[me]:
            occ = board.get((q + dq, r + dr))
            if occ is not None and occ[0] != me:
                blocked = True
                break
        if not blocked:
            home = (r == HOME_RANK[me])
            for dq, dr in PAWN_FWD[me]:
                one = (q + dq, r + dr)
                if one not in CELLS or one in board:
                    continue
                if one[1] == promo_r:
                    for pc in PROMO_PIECES:
                        out.append((cell, one, pc, None))
                else:
                    out.append((cell, one, None, None))
                if home:                       # double step, same direction
                    two = (q + 2 * dq, r + 2 * dr)
                    if two in CELLS and two not in board:
                        out.append((cell, two, None, None))
        # --- captures (and en passant)
        for dq, dr in pawn_caps(me, cell):
            tgt = (q + dq, r + dr)
            if tgt not in CELLS:
                continue
            occ = board.get(tgt)
            if occ is not None:
                if occ[0] != me:
                    if tgt[1] == promo_r:
                        for pc in PROMO_PIECES:
                            out.append((cell, tgt, pc, None))
                    else:
                        out.append((cell, tgt, None, None))
            elif ep is not None and tgt == ep[0]:
                out.append((cell, tgt, None, ep[1]))

    def _castles(self, s: BState) -> list:
        me = s.to_move
        board = s.board
        out = []
        if _in_check(board, me):
            return out
        for flag in FLAGS_BY_COLOR[me]:
            if flag not in s.castling:
                continue
            c = CASTLES[flag]
            if board.get(c["kfrom"]) != (me, "K") or board.get(c["rfrom"]) != (me, "R"):
                continue
            if any(x in board for x in c["empty"]):
                continue
            if any(_attacked(board, x, 1 - me) for x in c["path"]):
                continue
            out.append((c["kfrom"], c["kto"], None, None))
        return out

    @staticmethod
    def _castle_flag(board: dict, frm, to):
        """If this king move is a castling, return its flag, else None."""
        piece = board.get(frm)
        if piece is None or piece[1] != "K":
            return None
        if frm[1] != to[1] or abs(to[0] - frm[0]) < 2:
            return None
        for flag in FLAGS_BY_COLOR[piece[0]]:
            c = CASTLES[flag]
            if c["kfrom"] == frm and c["kto"] == to:
                return flag
        return None

    def _apply_board(self, board: dict, frm, to, promo, ep_victim, mover: int) -> dict:
        """Apply a move to a bare board.  ``ep_victim`` is the EXACT cell of the
        pawn removed by an en-passant capture (never inferred from ``to``: with
        two forward directions, two different enemy pawns can sit on the two
        cells behind the en-passant target)."""
        flag = self._castle_flag(board, frm, to)
        nb = dict(board)
        owner, t = nb.pop(frm)
        if ep_victim is not None:
            nb.pop(ep_victim, None)
        nb[to] = (owner, promo if promo else t)
        if flag is not None:
            c = CASTLES[flag]
            nb.pop(c["rfrom"], None)
            nb[c["rto"]] = (mover, "R")
        return nb

    def _legal(self, s: BState) -> list:
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        me = s.to_move
        out = []
        for frm, to, promo, victim in self._pseudo(s):
            nb = self._apply_board(s.board, frm, to, promo, victim, me)
            if not _in_check(nb, me):
                out.append((frm, to, promo, victim))
        object.__setattr__(s, "_legal_cache", out)
        return out

    @staticmethod
    def _mstr(frm, to, promo) -> str:
        base = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
        return base + (f"={promo}" if promo else "")

    def _update_rights(self, rights, frm, to, board) -> frozenset:
        pl, t = board[frm]
        out = set(rights)
        if t == "K" and frm in KING_HOME:
            out -= set(FLAGS_BY_COLOR[pl])
        if frm in ROOK_HOME:
            out.discard(ROOK_HOME[frm])
        if to in ROOK_HOME:                      # a rook captured on its home cell
            out.discard(ROOK_HOME[to])
        return frozenset(out)

    # ---- draws -------------------------------------------------------------
    def _draw_reason(self, s: BState) -> Optional[str]:
        reason = None
        if s.halfmove >= 100:
            reason = "50-move rule"
        elif s.reps and max(s.reps.values()) >= 3:
            reason = "threefold repetition"
        # Bare kings is the ONLY insufficient-material case: unlike orthodox
        # chess, K+B vs K and K+N vs K are not dead positions here (a corner has
        # just five king-neighbours, so a lone minor really can mate -- e.g.
        # Kc5+Nb3 vs Ka5#), so auto-drawing them would be a rule error.
        elif len(s.board) == 2:                  # bare kings: mate is impossible
            reason = "insufficient material"
        elif s.ply >= PLY_CAP:
            reason = "move limit"
        if reason is None:
            return None
        # As in orthodox chess, a move that delivers CHECKMATE ends the game
        # there and then, even if it is also the 100th reversible ply or the
        # third occurrence of the position.
        if not self._legal(s) and _in_check(s.board, s.to_move):
            return None
        return reason

    # ---- Game interface ----------------------------------------------------
    def legal_moves(self, s: BState) -> list:
        if self._draw_reason(s) is not None:
            return []
        return [self._mstr(frm, to, promo) for frm, to, promo, _ in self._legal(s)]

    def apply_move(self, s: BState, move: str, rng=None) -> BState:
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        frm_s, to_s = body.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        if self._draw_reason(s) is not None:
            raise ValueError(f"illegal move {move!r} (game over)")
        match = [m for m in self._legal(s)
                 if m[0] == frm and m[1] == to and (m[2] or None) == promo]
        if not match:
            raise ValueError(f"illegal move {move!r}")
        frm, to, promo, victim = match[0]
        me = s.to_move
        moved = s.board[frm]
        is_capture = victim is not None or (to in s.board)
        castling = self._update_rights(s.castling, frm, to, s.board)
        nb = self._apply_board(s.board, frm, to, promo, victim, me)
        ep = _ep_right(moved[1], me, frm, to)
        irreversible = is_capture or moved[1] == "P"
        halfmove = 0 if irreversible else s.halfmove + 1
        # prior positions can never recur after an irreversible move
        reps = {} if irreversible else dict(s.reps)
        key = _poskey(nb, 1 - me, castling, ep)
        reps[key] = reps.get(key, 0) + 1
        return BState(board=nb, to_move=1 - me, castling=castling, ep=ep,
                      halfmove=halfmove, ply=s.ply + 1, reps=reps, last=(frm, to))

    def is_terminal(self, s: BState) -> bool:
        if self._draw_reason(s) is not None:
            return True
        return len(self._legal(s)) == 0

    def returns(self, s: BState) -> list:
        if self._draw_reason(s) is not None:
            return [0.0, 0.0]
        if len(self._legal(s)) == 0:
            loser = s.to_move
            if _in_check(s.board, loser):        # checkmate
                return [-1.0, 1.0] if loser == WHITE else [1.0, -1.0]
            return [0.0, 0.0]                    # stalemate is a draw
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: BState) -> dict:
        return {
            "board": {f"{q},{r}": [o, t] for (q, r), (o, t) in s.board.items()},
            "to_move": s.to_move,
            "castling": "".join(sorted(s.castling)),
            "ep": ([f"{s.ep[0][0]},{s.ep[0][1]}", f"{s.ep[1][0]},{s.ep[1][1]}"]
                   if s.ep else None),
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
            "last": ([f"{s.last[0][0]},{s.last[0][1]}", f"{s.last[1][0]},{s.last[1][1]}"]
                     if s.last else None),
        }

    def deserialize(self, d: dict) -> BState:
        ep = d.get("ep")
        last = d.get("last")
        return BState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(d.get("castling", "")),
            ep=(_cell(ep[0]), _cell(ep[1])) if ep else None,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            last=(_cell(last[0]), _cell(last[1])) if last else None,
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s: BState, move: str) -> str:
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        frm_s, to_s = body.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        piece = s.board.get(frm)
        flag = self._castle_flag(s.board, frm, to)
        is_ep = (piece is not None and piece[1] == "P" and s.ep is not None
                 and to == s.ep[0] and to not in s.board)
        if flag is not None:
            out = CASTLES[flag]["name"]
        else:
            letter = "" if piece is None or piece[1] == "P" else piece[1]
            cap = "x" if (to in s.board or is_ep) else "-"
            out = f"{letter}{cell_name(frm)}{cap}{cell_name(to)}"
            if promo:
                out += f"={promo}"
            if is_ep:
                out += " e.p."
        if piece is not None:
            victim = s.ep[1] if is_ep else None
            nb = self._apply_board(s.board, frm, to, promo, victim, piece[0])
            foe = 1 - piece[0]
            if _in_check(nb, foe):
                nxt = BState(board=nb, to_move=foe,
                             ep=_ep_right(piece[1], piece[0], frm, to),
                             castling=self._update_rights(s.castling, frm, to, s.board))
                out += "#" if not self._legal(nxt) else "+"
        return out

    def render(self, s: BState, perspective=None) -> dict:
        pieces = [{"cell": f"{q},{r}", "owner": o, "label": t}
                  for (q, r), (o, t) in s.board.items()]
        highlights = []
        if s.last is not None:
            for c in s.last:
                highlights.append({"cell": f"{c[0]},{c[1]}", "kind": "last-move"})
        # The three hex colours (the bishop colour classes): (q - r) mod 3.
        shades = {0: "#e8ab6f", 1: "#ffce9e", 2: "#d18b47"}   # mid, light, dark
        cells = sorted(CELLS, key=lambda c: (-c[1], c[0]))
        if self.is_terminal(s):
            reason = self._draw_reason(s)
            if reason is not None:
                caption = f"Draw ({reason})"
            elif _in_check(s.board, s.to_move):
                caption = f"{NAMES[1 - s.to_move]} wins (checkmate)"
            else:
                caption = f"Draw (stalemate — {NAMES[s.to_move]} has no move)"
        else:
            check = " (check)" if _in_check(s.board, s.to_move) else ""
            caption = f"{NAMES[s.to_move]} to move{check}"
        return {
            "board": {
                "type": "hex",
                "cells": [f"{q},{r}" for q, r in cells],
                "tints": {f"{q},{r}": shades[(q - r) % 3] for q, r in cells},
            },
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "pieceset": "chess",
        }

    # ---- bot eval ----------------------------------------------------------
    VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}

    def heuristic(self, s: BState) -> list:
        import math
        bal = 0.0
        for (o, t) in s.board.values():
            v = self.VALUES.get(t, 0.0)
            bal += v if o == WHITE else -v
        v = math.tanh(bal / 8.0)
        return [v, -v]
