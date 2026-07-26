"""De Vasa's Hexagonal Chess (Helge E. de Vasa, 1953; pub. Boyer, Paris 1954).

The "other" orientation of hexagonal chess. Where Gliński's, McCooey's and
Shafran's boards are drawn with VERTICAL files (so a pawn has one straight-ahead
move), de Vasa turned the hexes 90 degrees so the board has ORDERLY HORIZONTAL
RANKS — and the board itself is a rhombus (parallelogram) of 9 files x 9 ranks =
81 cells rather than a hexagon. The first-rank array R N B Q B K B N R he
introduced was later borrowed by Brusky (1966).

Board & coordinates
-------------------
Cells are the platform's ``hex``/``rhombus`` ids ``"c,r"`` with
``0 <= c,r <= 8``:

    c = file index, "abcdefghi"[c]
    r = 9 - rank      (rank 9 = r 0, rank 1 = r 8)

The renderer draws a rhombus pointy-top (the default), i.e. x = sqrt(3)(c+r/2),
y = 1.5r: a rank (constant r) is HORIZONTAL and files lean up-left, exactly as
in de Vasa's published diagram. There is deliberately NO ``orientation: flat``
here — that is for the vertical-file hex chesses (Gliński/McCooey/Shafran).

White's home rank is 1 (r = 8) at the bottom right; White advances toward rank
9, i.e. in the -r direction, but along TWO lattice directions (there is no
"straight ahead" on a pointy-top board).

This is the REVISED (81-cell) game.  De Vasa's original 1953 game was a 72-cell
board (nine files x EIGHT ranks, pawns on ranks 2 and 7) whose pawn captured on
THREE forward bishop steps; the revision added a ninth rank, moved the pawns to
ranks 3 and 7, and deleted the straight-ahead capture.  Sources that describe
the original (quadibloc) therefore disagree with this package on purpose.

Rules implemented -- primary source first (see rules.md for the quotations):
  * the French sheet "Modification au projet de jeu hexagonal De Vasa, pages 81
    et 82" from Pritchard's files, printed in Variant Chess 64 (Jan 2010)
    pp. 161-62: the 81 cells (27/27/27), the array shift, "suppression de la
    faculte des Pions de prendre a un pas de Fou en avant ... leurs deux
    avancements et leurs deux prises a droite et a gauche", the double step,
    en passant, and both castlings by name (grand roque -> Rc1/Td1, petit roque
    -> Rh1/Tg1);
  * Pritchard & Beasley, Classified Encyclopedia of Chess Variants (2007),
    pp. 209-10 (and p. 203 for the stalemate scoping);
  * Wikipedia "Hexagonal chess" § De Vasa's hexagonal chess + its two diagrams;
    greenchess.net/rules.php?v=de-vasa (prose + pawn/castling diagrams);
    Wikibooks; Jocly's model as an array/pawn-graph/promotion oracle.
--------------------------------------------------------------------------
* Setup. White: R a1, N b1, B c1, Q d1, B e1, K f1, B g1, N h1, R i1; pawns
  a3-i3. Black: R a9, N b9, B c9, K d9, B e9, Q f9, B g9, N h9, R i9; pawns
  a7-i7. The KINGS STAND ON OPPOSITE WINGS (Kf1 vs Kd9) — Black's array is
  White's rotated 180 degrees about the board centre, not mirrored.
* Rook: 6 orthogonal (edge) directions. Bishop: 6 diagonal (vertex) directions
  (colourbound; the three bishops start on the three cell colours). Queen =
  rook + bishop. King: one step in any of the 12. Knight: the 12-target hex
  leap (cube permutations of 1/2/3), jumping over intervening pieces.
* Pawn. TWO forward moves — the two forward edge-neighbours (rank+1 keeping
  the file, and rank+1 gaining a file). From its own third rank it may instead
  advance TWO cells IN THE SAME DIRECTION over a vacant cell. It CAPTURES only
  on the two SIDE diagonals (rank+1, file-1 and rank+1, file+2) — never on the
  straight-ahead diagonal, which is two ranks away. En passant applies to the
  cell a double step crossed. Promotion to Q/R/B/N on the opponent's back rank
  (rank 9 for White, rank 1 for Black).
* Castling, in two lengths, one toward each rook:
    - SHORT (0-0), toward the rook three cells away: king moves 2, rook moves 2
      (White f1->h1, i1->g1; Black d9->b9, a9->c9).
    - LONG (0-0-0), toward the rook five cells away: king moves 3, rook moves 3
      (White f1->c1, a1->d1; Black d9->g9, i9->f9).
  All the cells between king and rook must be vacant, both must be unmoved,
  and the king may not start from, cross, or land on an attacked cell.
* STALEMATE IS A DRAW (the orthodox result). Gliński's 3/4-1/4 rule is a
  match-play SCORING convention specific to Gliński's game, and the standard
  reference explicitly says it does not propagate: "those of other variants by
  reference to Glinski at least as regards the moves of the men (Glinksi's
  treatment of stalemate has not been followed elsewhere)" — CECV 2007 p. 203,
  the preamble to the chapter that contains De Vasa. See rules.md.
* Draws: 50-move rule (100 plies with no pawn move or capture), threefold
  repetition (board + side + en-passant + castling rights), and a hard ply cap
  that is a pure termination backstop the 50-move rule provably beats.

Move strings: ``"c1,r1>c2,r2"`` with an ``"=Q/=R/=B/=N"`` suffix on promotions.
Castling is written as the king's ordinary from>to (2 or 3 cells).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NAMES = {WHITE: "White", BLACK: "Black"}
FILES = "abcdefghi"
W = H = 9                      # 9 files x 9 ranks = 81 cells
# Defensive termination backstop -- it must NEVER decide a game, or a live
# position becomes a bogus "move limit" draw. The 50-move rule is the real
# terminator. Bound: <=34 captures (36 men, 2 kings immortal) + <=108 pawn
# moves (18 pawns, each needs at most 6 moves to cross the 6 ranks from its
# third rank to promotion, since every pawn move gains 1 or 2 ranks) = <=142
# irreversible plies, with <=99 reversible plies in each of the 143 gaps
# around them => no game can exceed 142 + 143*99 = 14,299 plies. So this cap
# is unreachable dead code; selftest.py also measures it over random games.
PLY_CAP = 25000

# --- directions (axial c,r on the rhombus; the same hex lattice as the other
# hex chesses, only the ORIENTATION of "forward" differs) --------------------
# Orthogonal = through cell edges (rook). Listed NW, NE, E, SE, SW, W where NW
# and NE are White's two forward directions (both gain a rank).
ORTHO = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
# Diagonal = through cell vertices (bishop): sums of adjacent orthogonals.
# Listed N, NE-side, SE, S, SW-side, NW-side.
DIAG = [(1, -2), (2, -1), (1, 1), (-1, 2), (-2, 1), (-1, -1)]
# Knight: two hexes orthogonally then one at 60 deg = cube perms of (1,2,-3).
KNIGHT = [(1, -3), (2, -3), (3, -2), (3, -1), (2, 1), (1, 2),
          (-1, 3), (-2, 3), (-3, 2), (-3, 1), (-2, -1), (-1, -2)]

# A pawn has TWO forward moves (the two forward edge-neighbours) ...
PAWN_FWD = {WHITE: [(0, -1), (1, -1)], BLACK: [(0, 1), (-1, 1)]}
# ... and captures ONLY on the two SIDE diagonals (each is a forward move plus
# one lateral step: NW+W and NE+E). The third forward diagonal (0,-2)+... i.e.
# (1,-2) "straight ahead" is TWO ranks away and is NOT a capture.
PAWN_CAPS = {WHITE: [(-1, -1), (2, -1)], BLACK: [(1, 1), (-2, 1)]}

# Pawn home ranks: White rank 3 (r = 6), Black rank 7 (r = 2). A pawn can only
# gain ranks, and no pawn of a colour ever starts below its home rank, so
# "standing on its home rank" is exactly equivalent to "has not moved".
PAWN_HOME_R = {WHITE: 6, BLACK: 2}
BACK_R = {WHITE: 8, BLACK: 0}          # own back rank (rank 1 / rank 9)
PROMO_R = {WHITE: 0, BLACK: 8}         # opponent's back rank

# --- castling ---------------------------------------------------------------
# Both kings sit 3 cells from one rook and 5 from the other; castling toward
# the near rook is SHORT (king 2, rook 2) and toward the far one LONG (king 3,
# rook 3). White K f1 (c 5) with rooks a1/i1; Black K d9 (c 3) with a9/i9.
KING_START = {WHITE: (5, 8), BLACK: (3, 0)}
ROOK_START = {(WHITE, "a"): (0, 8), (WHITE, "i"): (8, 8),
              (BLACK, "a"): (0, 0), (BLACK, "i"): (8, 0)}
ALL_CASTLES = tuple(sorted(ROOK_START))


def _castle_plan(player: int, flank: str):
    """(short?, king_to, rook_to, between, king_path) for one castling flank."""
    kc, kr = KING_START[player]
    rc, _ = ROOK_START[(player, flank)]
    d = 1 if rc > kc else -1
    dist = abs(rc - kc)                       # 3 (short) or 5 (long)
    short = dist == 3
    n = 2 if short else 3                     # cells the king slides
    between = [(kc + i * d, kr) for i in range(1, dist)]
    king_path = [(kc + i * d, kr) for i in range(0, n + 1)]
    return (short, (kc + n * d, kr), (kc + (n - 1) * d, kr), between, king_path)


CASTLE = {k: _castle_plan(*k) for k in ROOK_START}


def _setup_board() -> dict:
    """White's array plus Black's exact 180-degree rotation (c,r)->(8-c,8-r)."""
    b = {}
    for i, letter in enumerate("RNBQBKBNR"):   # a1 .. i1
        b[(i, 8)] = (WHITE, letter)
    for i in range(W):
        b[(i, 6)] = (WHITE, "P")               # a3 .. i3
    for (c, r), (_, letter) in list(b.items()):
        b[(8 - c, 8 - r)] = (BLACK, letter)
    return b


def on_board(c: int, r: int) -> bool:
    return 0 <= c < W and 0 <= r < H


CELLS = tuple((c, r) for r in range(H) for c in range(W))


def _is_promo(player: int, cell) -> bool:
    return cell[1] == PROMO_R[player]


def cell_name(cell) -> str:
    """(c,r) -> de Vasa notation, e.g. (5,8) -> 'f1'."""
    c, r = cell
    return f"{FILES[c]}{9 - r}"


def _cell(sstr: str):
    c, r = sstr.split(",")
    return int(c), int(r)


@dataclass
class VState:
    board: dict = field(default_factory=_setup_board)  # (c,r) -> (owner, letter)
    to_move: int = WHITE
    # en passant: (crossed_cell, double_stepped_pawn_cell) or None
    ep: Optional[tuple] = None
    castling: frozenset = field(default_factory=lambda: frozenset(ALL_CASTLES))
    halfmove: int = 0     # plies since last pawn move / capture (50-move rule)
    ply: int = 0
    reps: dict = field(default_factory=dict)  # position key -> count (3-fold)
    last: Optional[tuple] = None              # (from, to) for highlights


def _poskey(board: dict, to_move: int, ep, castling) -> str:
    items = sorted((c, r, o, t) for (c, r), (o, t) in board.items())
    ep_s = f"{ep[0][0]},{ep[0][1]}" if ep else "-"
    cs = "".join(f"{p}{f}" for p, f in sorted(castling)) or "-"
    return (f"{to_move}|{ep_s}|{cs}|"
            + ";".join(f"{c},{r},{o},{t}" for c, r, o, t in items))


def _attacked(board: dict, cell, by: int) -> bool:
    """Is `cell` attacked by any piece of player `by`?"""
    c, r = cell
    for dc, dr in PAWN_CAPS[by]:                     # pawns (reverse)
        p = board.get((c - dc, r - dr))
        if p is not None and p[0] == by and p[1] == "P":
            return True
    for dc, dr in KNIGHT:
        p = board.get((c + dc, r + dr))
        if p is not None and p[0] == by and p[1] == "N":
            return True
    for dc, dr in ORTHO + DIAG:                      # kings
        p = board.get((c + dc, r + dr))
        if p is not None and p[0] == by and p[1] == "K":
            return True
    for dirs, letters in ((ORTHO, ("R", "Q")), (DIAG, ("B", "Q"))):
        for dc, dr in dirs:
            xc, xr = c + dc, r + dr
            while on_board(xc, xr):
                p = board.get((xc, xr))
                if p is not None:
                    if p[0] == by and p[1] in letters:
                        return True
                    break
                xc += dc
                xr += dr
    return False


def _king_cell(board: dict, player: int):
    for cell, (o, t) in board.items():
        if o == player and t == "K":
            return cell
    return None


def _in_check(board: dict, player: int) -> bool:
    k = _king_cell(board, player)
    return k is not None and _attacked(board, k, 1 - player)


class DeVasaChess(Game):

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> VState:
        s = VState()
        s.reps = {_poskey(s.board, s.to_move, s.ep, s.castling): 1}
        return s

    def current_player(self, s: VState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------
    def _pseudo(self, s: VState) -> list:
        """Pseudo-legal moves as (frm, to, promo, ep_capture_cell, castle)."""
        out = []
        me = s.to_move
        board = s.board
        for (c, r), (owner, t) in board.items():
            if owner != me:
                continue
            if t == "P":
                for dc, dr in PAWN_FWD[me]:
                    one = (c + dc, r + dr)
                    if not on_board(*one) or one in board:
                        continue
                    if _is_promo(me, one):
                        for pc in ("Q", "R", "B", "N"):
                            out.append(((c, r), one, pc, None, None))
                    else:
                        out.append(((c, r), one, None, None, None))
                    # double step: same direction, from the pawn's home rank
                    if r == PAWN_HOME_R[me]:
                        two = (c + 2 * dc, r + 2 * dr)
                        if on_board(*two) and two not in board:
                            out.append(((c, r), two, None, None, None))
                for dc, dr in PAWN_CAPS[me]:
                    tgt = (c + dc, r + dr)
                    if not on_board(*tgt):
                        continue
                    occ = board.get(tgt)
                    if occ is not None:
                        if occ[0] != me:
                            if _is_promo(me, tgt):
                                for pc in ("Q", "R", "B", "N"):
                                    out.append(((c, r), tgt, pc, None, None))
                            else:
                                out.append(((c, r), tgt, None, None, None))
                    elif s.ep is not None and tgt == s.ep[0]:
                        out.append(((c, r), tgt, None, s.ep[1], None))
            elif t == "N":
                for dc, dr in KNIGHT:
                    tgt = (c + dc, r + dr)
                    if on_board(*tgt):
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((c, r), tgt, None, None, None))
            elif t == "K":
                for dc, dr in ORTHO + DIAG:
                    tgt = (c + dc, r + dr)
                    if on_board(*tgt):
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append(((c, r), tgt, None, None, None))
            else:
                dirs = ORTHO if t == "R" else DIAG if t == "B" else ORTHO + DIAG
                for dc, dr in dirs:
                    xc, xr = c + dc, r + dr
                    while on_board(xc, xr):
                        occ = board.get((xc, xr))
                        if occ is None:
                            out.append(((c, r), (xc, xr), None, None, None))
                        else:
                            if occ[0] != me:
                                out.append(((c, r), (xc, xr), None, None, None))
                            break
                        xc += dc
                        xr += dr
        out.extend(self._castles(s))
        return out

    def _castles(self, s: VState) -> list:
        me = s.to_move
        rights = [k for k in s.castling if k[0] == me]
        if not rights:
            return []
        king = KING_START[me]
        if s.board.get(king) != (me, "K") or _in_check(s.board, me):
            return []
        out = []
        for key in sorted(rights):
            if s.board.get(ROOK_START[key]) != (me, "R"):
                continue
            _short, king_to, rook_to, between, king_path = CASTLE[key]
            if any(x in s.board for x in between):
                continue
            # The king may not cross an attacked cell; its start is already
            # known safe and its destination is checked by the in-check filter.
            if any(_attacked(s.board, x, 1 - me) for x in king_path[1:-1]):
                continue
            out.append((king, king_to, None, None, (ROOK_START[key], rook_to)))
        return out

    def _apply_board(self, board: dict, frm, to, promo, ep_cap, castle) -> dict:
        nb = dict(board)
        owner, t = nb.pop(frm)
        if ep_cap is not None:
            nb.pop(ep_cap, None)                    # the double-stepped pawn
        nb[to] = (owner, promo if promo else t)
        if castle is not None:
            rf, rt = castle
            nb[rt] = nb.pop(rf)
        return nb

    def _legal(self, s: VState) -> list:
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
    def _draw_reason(self, s: VState) -> Optional[str]:
        if s.halfmove >= 100:
            return "50-move rule"
        if s.reps and max(s.reps.values()) >= 3:
            return "threefold repetition"
        if s.ply >= PLY_CAP:
            return "move limit"
        return None

    # ---- Game interface ----------------------------------------------------
    def legal_moves(self, s: VState) -> list:
        if self._draw_reason(s) is not None:
            return []
        return [self._mstr(frm, to, promo)
                for frm, to, promo, _, _ in self._legal(s)]

    def apply_move(self, s: VState, move: str, rng=None) -> VState:
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
        # en passant right: only a double step (2 x one forward direction)
        ep = None
        if moved[1] == "P":
            dc, dr = to[0] - frm[0], to[1] - frm[1]
            for fc, fr in PAWN_FWD[me]:
                if (dc, dr) == (2 * fc, 2 * fr):
                    ep = ((frm[0] + fc, frm[1] + fr), to)
                    break
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
        return VState(board=nb, to_move=1 - me, ep=ep, castling=castling,
                      halfmove=halfmove, ply=s.ply + 1, reps=reps,
                      last=(frm, to))

    def is_terminal(self, s: VState) -> bool:
        if self._draw_reason(s) is not None:
            return True
        return len(self._legal(s)) == 0

    def returns(self, s: VState) -> list:
        if self._draw_reason(s) is not None:
            return [0.0, 0.0]
        if len(self._legal(s)) == 0:
            loser = s.to_move
            if _in_check(s.board, loser):          # checkmate
                return [-1.0, 1.0] if loser == WHITE else [1.0, -1.0]
            return [0.0, 0.0]                      # stalemate IS a draw
        return [0.0, 0.0]

    # ---- serialization -----------------------------------------------------
    def serialize(self, s: VState) -> dict:
        return {
            "board": {f"{c},{r}": [o, t] for (c, r), (o, t) in s.board.items()},
            "to_move": s.to_move,
            "ep": ([f"{s.ep[0][0]},{s.ep[0][1]}", f"{s.ep[1][0]},{s.ep[1][1]}"]
                   if s.ep else None),
            "castling": sorted(f"{p}{f}" for p, f in s.castling),
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
            "last": ([f"{s.last[0][0]},{s.last[0][1]}",
                      f"{s.last[1][0]},{s.last[1][1]}"] if s.last else None),
        }

    def deserialize(self, d: dict) -> VState:
        ep = d.get("ep")
        last = d.get("last")
        cast = d.get("castling")
        if cast is None:
            cast = [f"{p}{f}" for p, f in ALL_CASTLES]
        return VState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ep=(_cell(ep[0]), _cell(ep[1])) if ep else None,
            castling=frozenset((int(x[0]), x[1]) for x in cast),
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            last=(_cell(last[0]), _cell(last[1])) if last else None,
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s: VState, move: str) -> str:
        promo = None
        body = move
        if "=" in move:
            body, promo = move.split("=")
        frm_s, to_s = body.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        piece = s.board.get(frm)
        # Castling notation. The `frm == KING_START` test is load-bearing, not
        # decorative: two of the four castling destinations are also reachable
        # by an ORDINARY king step from elsewhere -- the diagonal directions
        # (+-2, -+1) mean a White king on e2 can step to c1 and a Black king on
        # e8 to g9. Without the guard those quiet moves (and captures on those
        # cells) would be written "0-0-0" in the move log.
        if piece is not None and piece[1] == "K" and frm == KING_START[piece[0]] \
                and abs(to[0] - frm[0]) > 1:
            for key, (short, king_to, _rt, _b, _p) in CASTLE.items():
                if key[0] == piece[0] and to == king_to:
                    return "0-0" if short else "0-0-0"
        letter = "" if piece is None or piece[1] == "P" else piece[1]
        is_ep = (piece is not None and piece[1] == "P" and s.ep is not None
                 and to == s.ep[0] and to not in s.board)
        cap = "x" if (to in s.board or is_ep) else "-"
        out = f"{letter}{cell_name(frm)}{cap}{cell_name(to)}"
        if promo:
            out += f"={promo}"
        if is_ep:
            out += " e.p."
        return out

    def render(self, s: VState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": o, "label": t}
                  for (c, r), (o, t) in s.board.items()]
        highlights = []
        if s.last is not None:
            for x in s.last:
                highlights.append({"cell": f"{x[0]},{x[1]}", "kind": "last-move"})
        # The three hex colours (bishop colour classes): colour = (c - r) mod 3.
        # Which class is light / mid / dark was read off the Wikipedia
        # diagram's pixels (0 light, 1 mid, 2 dark); the three hex codes are
        # the platform's shared hex-chess palette. This puts the three bishops
        # (c1/e1/g1) on the three colours.
        shades = {0: "#ffce9e", 1: "#e8ab6f", 2: "#d18b47"}
        tints = {f"{c},{r}": shades[(c - r) % 3] for c, r in CELLS}
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
            "board": {"type": "hex", "shape": "rhombus", "width": W, "height": H,
                      # De Vasa's ranks are drawn HORIZONTAL, which is the
                      # pointy-top default -- do NOT set "flat" here (that is
                      # for the vertical-file hex chesses). See SPEC.md.
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "pieceset": "chess",
        }

    # ---- bot eval ----------------------------------------------------------
    VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}

    def heuristic(self, s: VState) -> list:
        import math
        bal = 0.0
        for (o, t) in s.board.values():
            v = self.VALUES.get(t, 0.0)
            bal += v if o == WHITE else -v
        v = math.tanh(bal / 8.0)
        return [v, -v]
