"""Shafran's Hexagonal Chess (Isaak Grigorevich Shafran, USSR, 1939).

The third of the historic hexagonal chesses, alongside Gliński's (1936) and
McCooey's (1978). Shafran, a Soviet geologist, invented it in 1939, registered
it in 1956 and had it demonstrated at the Leipzig Chess Olympiad in 1960. Its
board is an *irregular* hexagon of only 70 cells — four sides of 5 and two of 6
— which brings it much closer to orthodox chess's 64 squares than Gliński's 91.

Board & coordinates
-------------------
Nine vertical files ``a``-``i`` and ten *obliquely descending* ranks ``1``-``10``
(a rank runs from the upper left down to the lower right, so ``a1`` is the
highest cell of rank 1 and ``e1``, the king's cell, is the lowest cell of the
whole board). File lengths are a=6, b=7, c=8, d=9, e=10, f=9, g=8, h=7, i=6;
files f..i start at ranks 2,3,4,5 respectively.

Cells are axial hex coordinates ``"q,r"`` (cube ``s = -q-r``) with

    q = file index - 4   (a = -4 ... i = +4)
    r = 5 - rank         (rank 1 = +4 ... rank 10 = -5)

so the board is exactly ``-4 <= q <= 4``, ``-5 <= r <= 4``, ``-5 <= q+r <= 4``
(70 cells). White moves in the ``-r`` direction ("north", up a file); the axial
direction tables are byte-identical to ``glinski_chess`` / ``mccooey_chess`` so
a shared hex-chess core can be factored out later.

Rules implemented (Derzhanski's write-up of the *Junyj texnik* report =
closest to primary; Wikipedia "Hexagonal chess" § Shafran; Duniho's
chessvariants.com page; the Jocly reference model; see rules.md)
--------------------------------------------------------------------------
* Setup (each side K Q R×2 B×3 N×2 P×9). White: R a1, N b1, B c1, Q d1, K e1,
  B f2, N g3, B h4, R i5; pawns a2 b2 c2 d2 e2 f3 g4 h5 i6. Black is the exact
  180° rotation (R i10, N h10, B g10, Q f10, K e10, B d9, N c8, B b7, R a6;
  pawns i9 h9 g9 f9 e9 d8 c7 b6 a5). NOTE: Duniho's prose says "the Bishop is
  on f1" — a typo. f1 is not a cell of this board at all (the f-file starts at
  f2), and only f2 puts the three bishops on the three cell colours, as his own
  text and diagram require. Jocly and the Wikipedia diagram both say f2.
* Rook: 6 orthogonal (edge) directions. Bishop: 6 diagonal (vertex) directions
  (colourbound; the three bishops start on the three colours). Queen = rook +
  bishop (12 directions). King: one step in any of the 12. Knight: the
  12-target hex leap (one orthogonal step then one *outward* diagonal step;
  equivalently, every cell of the third ring a queen cannot reach).
* Pawn: one vacant cell straight forward; captures one cell along the two
  forward DIAGONAL (bishop-wise) directions — McCooey-style, NOT Gliński's
  forward orthogonals. On its FIRST move it may advance as far as it can
  without leaving its own half of its file: 3 cells on the d/e/f files, 2 on
  b/c/g/h, 1 on a/i, over vacant cells only. Every cell CROSSED by such a
  multi-step move is an en-passant target for one move. Promotion to Q/R/B/N
  at the far end of any file (9 cells per side).
* Castling (unique among the classical hex chesses). Toward either rook, in
  two lengths: LONG (0-0-0) moves the king 3 cells, next to the rook, and the
  rook jumps over him to the far side; SHORT (0-0) is "the opposite procedure"
  (Derzhanski) -- the rook steps next to the king and the king jumps over it,
  landing 2 cells from home with the rook 1. The three cells between king and
  rook must be empty either way, and the king may not start from, pass through
  or land on an attacked cell. Notation is prefixed by the flank: ``Q-`` for
  the player's queen's flank, ``B-`` for his bishops' flank (the flanks are
  opposite for the two players).
* STALEMATE IS A DRAW (Wikipedia, explicit) — unlike Gliński's 3/4-1/4 rule.
* Draws: 50-move rule (100 plies with no pawn move or capture), threefold
  repetition (board + side + en-passant targets + castling rights), and a hard
  ply cap as a pure termination backstop that the 50-move rule provably always
  reaches first (see rules.md). No "insufficient material" auto-draw.

Move strings: ``"q1,r1>q2,r2"`` with an ``"=Q/=R/=B/=N"`` suffix on promotions.
Castling is written as the king's ordinary from>to (2 or 3 cells).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefghi"            # nine vertical files
# Defensive termination backstop. The 50-move rule provably fires first: at most
# 178 irreversible plies (<=34 captures + <=144 pawn moves -- every pawn move
# gains a rank and no pawn can gain more than 8) and at most 99 reversible plies
# in each of the 179 gaps around them cap any game at 178 + 179*99 = 17,899
# plies. Observed longest random game: 723 plies. See rules.md.
PLY_CAP = 20000

# --- directions (axial q,r; cube s = -q-r) ---------------------------------
# Orthogonal = through cell edges (rook); listed N, NE, SE, S, SW, NW where
# "N" (0,-1) is White's forward direction (up a file).
ORTHO = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
# Diagonal = through cell vertices (bishop): sums of adjacent orthogonals.
# Listed NNE, E, SSE, SSW, W, NNW.
DIAG = [(1, -2), (2, -1), (1, 1), (-1, 2), (-2, 1), (-1, -1)]
# Knight: one orthogonal step then one outward diagonal = cube perms of (1,2,-3).
KNIGHT = [(1, -3), (2, -3), (3, -2), (3, -1), (2, 1), (1, 2),
          (-1, 3), (-2, 3), (-3, 2), (-3, 1), (-2, -1), (-1, -2)]

PAWN_FWD = {WHITE: (0, -1), BLACK: (0, 1)}
# Captures: the two FORWARD DIAGONAL (bishop) directions -- Shafran follows
# McCooey here, not Gliński (whose pawns capture along the forward orthogonals).
PAWN_CAPS = {WHITE: [(1, -2), (-1, -1)], BLACK: [(-1, 2), (1, 1)]}

# --- board -----------------------------------------------------------------
QMIN, QMAX = -4, 4
RMIN, RMAX = -5, 4


def on_board(q: int, r: int) -> bool:
    return QMIN <= q <= QMAX and RMIN <= r <= RMAX and RMIN <= q + r <= RMAX


CELLS = tuple(sorted((q, r) for q in range(QMIN, QMAX + 1)
                     for r in range(RMIN, RMAX + 1) if on_board(q, r)))


def _file_top(q: int) -> int:
    """Smallest r (Black's end / White's promotion cell) of file q."""
    return max(RMIN, RMIN - q)


def _file_bottom(q: int) -> int:
    """Largest r (White's end / Black's promotion cell) of file q."""
    return min(RMAX, RMAX - q)


def _file_len(q: int) -> int:
    return _file_bottom(q) - _file_top(q) + 1


# Home ("back") cell of each file, and the pawn cell just in front of it.
HOME = {WHITE: {q: (q, _file_bottom(q)) for q in range(QMIN, QMAX + 1)},
        BLACK: {q: (q, _file_top(q)) for q in range(QMIN, QMAX + 1)}}

# A pawn's first move may take it "as far as it can without moving to the
# opponent's side of the board" (Duniho). Numbering a file 0..L-1 from the
# pawn's own end, the pawn stands on 1 and may reach at most (L-1)//2 (the
# midway cell of an odd-length file counts as reachable), so:
PAWN_STEPS = {q: (_file_len(q) - 1) // 2 - 1 for q in range(QMIN, QMAX + 1)}
# == {a:1, b:2, c:2, d:3, e:3, f:3, g:2, h:2, i:1}

PAWN_START = {p: {(q, HOME[p][q][1] + PAWN_FWD[p][1]): PAWN_STEPS[q]
                  for q in range(QMIN, QMAX + 1)} for p in (WHITE, BLACK)}

# --- castling --------------------------------------------------------------
KING_START = {WHITE: (0, 4), BLACK: (0, -5)}
# Flank key -> the direction from the king toward that flank's rook. The rook
# stands four cells away, with exactly three cells in between.
CASTLE_DIR = {(WHITE, "a"): (-1, 0), (WHITE, "i"): (1, -1),
              (BLACK, "a"): (-1, 1), (BLACK, "i"): (1, 0)}


def _castle_geometry(player: int, flank: str):
    """(rook_cell, [between1, between2, between3]) for one castling flank."""
    kq, kr = KING_START[player]
    dq, dr = CASTLE_DIR[(player, flank)]
    between = [(kq + i * dq, kr + i * dr) for i in (1, 2, 3)]
    return (kq + 4 * dq, kr + 4 * dr), between


ROOK_START = {k: _castle_geometry(*k)[0] for k in CASTLE_DIR}
CASTLE_BETWEEN = {k: _castle_geometry(*k)[1] for k in CASTLE_DIR}
ALL_CASTLES = tuple(sorted(CASTLE_DIR))
# The player's queen stands on the "a" flank for White and the "i" flank for
# Black, so the notation prefix (Q- / B-) is side-relative.
QUEEN_FLANK = {WHITE: "a", BLACK: "i"}


def _setup_board() -> dict:
    """White's array, plus Black's exact 180° rotation (q,r) -> (-q,-1-r)."""
    order = "RNBQKBNBR"                      # files a..i
    b = {}
    for i, letter in enumerate(order):
        q = QMIN + i
        b[HOME[WHITE][q]] = (WHITE, letter)
    for cell in PAWN_START[WHITE]:
        b[cell] = (WHITE, "P")
    for (q, r), (_, letter) in list(b.items()):
        b[(-q, -1 - r)] = (BLACK, letter)
    return b


def _is_promo(player: int, cell) -> bool:
    """The far end of a file: 9 cells per side (two edges of the hexagon)."""
    q, r = cell
    return r == (_file_top(q) if player == WHITE else _file_bottom(q))


def cell_name(cell) -> str:
    """Axial (q,r) -> Shafran notation, e.g. (0,4) -> 'e1'."""
    q, r = cell
    return f"{FILES[q - QMIN]}{5 - r}"


def _cell(sstr: str):
    q, r = sstr.split(",")
    return int(q), int(r)


def _hex_dist(a, b) -> int:
    dq, dr = b[0] - a[0], b[1] - a[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


@dataclass
class GState:
    board: dict = field(default_factory=_setup_board)  # (q,r) -> (owner, letter)
    to_move: int = WHITE
    # en passant: (pawn_cell, (crossed_cell, ...)) set by the last multi-step
    # pawn move -- EVERY cell it crossed is capturable -- or None.
    ep: Optional[tuple] = None
    castling: frozenset = field(default_factory=lambda: frozenset(ALL_CASTLES))
    halfmove: int = 0     # plies since last pawn move / capture (50-move rule)
    ply: int = 0
    reps: dict = field(default_factory=dict)  # position key -> count (3-fold)
    last: Optional[tuple] = None              # (from, to) for highlights


def _poskey(board: dict, to_move: int, ep, castling) -> str:
    items = sorted((q, r, o, t) for (q, r), (o, t) in board.items())
    ep_s = "-" if not ep else "+".join(f"{q},{r}" for q, r in sorted(ep[1]))
    cs = "".join(f"{p}{f}" for p, f in sorted(castling)) or "-"
    return (f"{to_move}|{ep_s}|{cs}|"
            + ";".join(f"{q},{r},{o},{t}" for q, r, o, t in items))


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


class ShafranChess(Game):

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GState:
        s = GState()
        s.reps = {_poskey(s.board, s.to_move, s.ep, s.castling): 1}
        return s

    def current_player(self, s: GState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _pseudo(self, s: GState) -> list:
        """Pseudo-legal moves as (frm, to, promo, ep_capture_cell, castle).

        `castle` is None or (rook_from, rook_to); castling is generated only
        when its own (empty / not-through-check) conditions already hold, the
        king's destination being validated by the shared in-check filter.
        """
        out = []
        me = s.to_move
        board = s.board
        for (q, r), (owner, t) in board.items():
            if owner != me:
                continue
            if t == "P":
                fq, fr = PAWN_FWD[me]
                steps = PAWN_START[me].get((q, r), 1)
                cq, cr = q, r
                for _ in range(steps):
                    cq, cr = cq + fq, cr + fr
                    if not on_board(cq, cr) or (cq, cr) in board:
                        break               # may not leap over an occupied cell
                    if _is_promo(me, (cq, cr)):
                        for pc in ("Q", "R", "B", "N"):
                            out.append(((q, r), (cq, cr), pc, None, None))
                    else:
                        out.append(((q, r), (cq, cr), None, None, None))
                for dq, dr in PAWN_CAPS[me]:
                    tgt = (q + dq, r + dr)
                    if not on_board(*tgt):
                        continue
                    occ = board.get(tgt)
                    if occ is not None:
                        if occ[0] != me:
                            if _is_promo(me, tgt):
                                for pc in ("Q", "R", "B", "N"):
                                    out.append(((q, r), tgt, pc, None, None))
                            else:
                                out.append(((q, r), tgt, None, None, None))
                    elif s.ep is not None and tgt in s.ep[1]:
                        out.append(((q, r), tgt, None, s.ep[0], None))
            elif t == "N":
                for dq, dr in KNIGHT:
                    tgt = (q + dq, r + dr)
                    if on_board(*tgt):
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((q, r), tgt, None, None, None))
            elif t == "K":
                for dq, dr in ORTHO + DIAG:
                    tgt = (q + dq, r + dr)
                    if on_board(*tgt):
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((q, r), tgt, None, None, None))
            else:
                dirs = ORTHO if t == "R" else DIAG if t == "B" else ORTHO + DIAG
                for dq, dr in dirs:
                    cq, cr = q + dq, r + dr
                    while on_board(cq, cr):
                        occ = board.get((cq, cr))
                        if occ is None:
                            out.append(((q, r), (cq, cr), None, None, None))
                        else:
                            if occ[0] != me:
                                out.append(((q, r), (cq, cr), None, None, None))
                            break
                        cq += dq
                        cr += dr
        out.extend(self._castles(s))
        return out

    def _castles(self, s: GState) -> list:
        me = s.to_move
        rights = [k for k in s.castling if k[0] == me]
        if not rights:
            return []
        king = KING_START[me]
        if s.board.get(king) != (me, "K") or _in_check(s.board, me):
            return []
        out = []
        for key in sorted(rights):
            between = CASTLE_BETWEEN[key]
            if s.board.get(ROOK_START[key]) != (me, "R"):
                continue
            if any(c in s.board for c in between):
                continue
            # long: K -> between[2], R -> between[1]; short: K -> between[1],
            # R -> between[0]. The king may not pass through an attacked cell;
            # its destination is checked by the shared in-check filter.
            if not _attacked(s.board, between[0], 1 - me):
                out.append((king, between[1], None, None,
                            (ROOK_START[key], between[0])))
                if not _attacked(s.board, between[1], 1 - me):
                    out.append((king, between[2], None, None,
                                (ROOK_START[key], between[1])))
        return out

    def _apply_board(self, board: dict, frm, to, promo, ep_cap, castle) -> dict:
        nb = dict(board)
        owner, t = nb.pop(frm)
        if ep_cap is not None:
            nb.pop(ep_cap, None)            # the multi-stepped pawn
        nb[to] = (owner, promo if promo else t)
        if castle is not None:
            rf, rt = castle
            nb[rt] = nb.pop(rf)
        return nb

    def _legal(self, s: GState) -> list:
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        me = s.to_move
        out = []
        for mv in self._pseudo(s):
            nb = self._apply_board(s.board, *mv)
            if not _in_check(nb, me):
                out.append(mv)
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
        return [self._mstr(frm, to, promo) for frm, to, promo, _, _ in self._legal(s)]

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
        frm, to, promo, ep_cap, castle = match[0]
        me = s.to_move
        moved = s.board[frm]
        is_capture = ep_cap is not None or (to in s.board)
        nb = self._apply_board(s.board, frm, to, promo, ep_cap, castle)
        # en passant: EVERY cell crossed by a multi-step pawn move is a target
        ep = None
        if moved[1] == "P":
            n = _hex_dist(frm, to)
            if n > 1 and to[0] == frm[0]:
                fq, fr = PAWN_FWD[me]
                crossed = tuple((frm[0] + i * fq, frm[1] + i * fr)
                                for i in range(1, n))
                ep = (to, crossed)
        # a rook or king that left home (or a rook captured at home) kills rights
        castling = frozenset(
            k for k in s.castling
            if nb.get(KING_START[k[0]]) == (k[0], "K")
            and nb.get(ROOK_START[k]) == (k[0], "R"))
        irreversible = is_capture or moved[1] == "P"
        halfmove = 0 if irreversible else s.halfmove + 1
        # prior positions can never recur after an irreversible move; losing a
        # castling right is likewise irreversible
        reps = {} if (irreversible or castling != s.castling) else dict(s.reps)
        key = _poskey(nb, 1 - me, ep, castling)
        reps[key] = reps.get(key, 0) + 1
        return GState(board=nb, to_move=1 - me, ep=ep, castling=castling,
                      halfmove=halfmove, ply=s.ply + 1, reps=reps, last=(frm, to))

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
            return [0.0, 0.0]                      # stalemate IS a draw
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: GState) -> dict:
        return {
            "board": {f"{q},{r}": [o, t] for (q, r), (o, t) in s.board.items()},
            "to_move": s.to_move,
            "ep": ([f"{s.ep[0][0]},{s.ep[0][1]}"]
                   + [f"{q},{r}" for q, r in s.ep[1]]) if s.ep else None,
            "castling": sorted(f"{p}{f}" for p, f in s.castling),
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
            "last": ([f"{s.last[0][0]},{s.last[0][1]}", f"{s.last[1][0]},{s.last[1][1]}"]
                     if s.last else None),
        }

    def deserialize(self, d: dict) -> GState:
        ep = d.get("ep")
        last = d.get("last")
        cast = d.get("castling")
        if cast is None:
            cast = [f"{p}{f}" for p, f in ALL_CASTLES]
        return GState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ep=(_cell(ep[0]), tuple(_cell(x) for x in ep[1:])) if ep else None,
            castling=frozenset((int(x[0]), x[1]) for x in cast),
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
        if piece is not None and piece[1] == "K" and _hex_dist(frm, to) > 1:
            for key, between in CASTLE_BETWEEN.items():
                if key[0] != piece[0]:
                    continue
                flank = "Q" if key[1] == QUEEN_FLANK[piece[0]] else "B"
                if to == between[2]:
                    return f"{flank}-0-0-0"
                if to == between[1]:
                    return f"{flank}-0-0"
        letter = "" if piece is None or piece[1] == "P" else piece[1]
        is_ep = (piece is not None and piece[1] == "P" and s.ep is not None
                 and to in s.ep[1] and to not in s.board)
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
        tints = {f"{q},{r}": shades[(q - r) % 3] for q, r in CELLS}
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
            "board": {"type": "hex",
                      "cells": [f"{q},{r}" for q, r in CELLS],
                      # q IS the file index, and Shafran's files are drawn
                      # VERTICAL, so use flat-top hexes (see SPEC.md).
                      "orientation": "flat",
                      "tints": tints},
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
