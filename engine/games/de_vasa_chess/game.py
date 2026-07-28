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
Piece movement, check/mate, the draw counters, serialisation, rendering and the
MCTS heuristic come from ``agp.hexchesslike`` (shared with the other classical
hex chesses -- the direction tables are identical in axial space for the whole
family).  This module supplies only what is de Vasa-specific:

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
  that is a pure termination backstop the 50-move rule provably beats.  As in
  orthodox chess a DECISIVE result outranks all three (``_draw_reason`` in the
  shared core yields to "the side to move has no legal move").

Move strings: ``"c1,r1>c2,r2"`` with an ``"=Q/=R/=B/=N"`` suffix on promotions.
Castling is written as the king's ordinary from>to (2 or 3 cells).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The names re-exported / defined here (VState, WHITE/BLACK, FILES, CELLS,
# ORTHO/DIAG/KNIGHT, on_board, cell_name, ALL_CASTLES, PLY_CAP, _cell, _poskey,
# _attacked, _king_cell, _in_check) are this module's PUBLIC SURFACE:
# ``selftest.py`` imports them and the selftest is the regression net for this
# refactor, so it is deliberately not rewritten.  Keep these names when editing.
from agp.hexchesslike import (BLACK, DIAG, KNIGHT, ORTHO, WHITE,  # noqa: F401
                              HexChessLike, HState, cell_str, parse_cell)

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

# ORTHO / DIAG / KNIGHT come from the shared core: in axial space the tables are
# byte-identical for every member of the hex-chess family, and only which vector
# is "forward" for a pawn differs.  Here the orthogonals read NW, NE, E, SE, SW,
# W, with NW and NE White's two forward directions.

# A pawn has TWO forward moves (the two forward edge-neighbours) ...
PAWN_FWD = {WHITE: [(0, -1), (1, -1)], BLACK: [(0, 1), (-1, 1)]}
# ... and captures ONLY on the two SIDE diagonals (each is a forward move plus
# one lateral step: NW+W and NE+E). The third forward diagonal (1,-2)
# "straight ahead" is TWO ranks away and is NOT a capture.
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


CELLS = frozenset((c, r) for r in range(H) for c in range(W))


def _is_promo(player: int, cell) -> bool:
    return cell[1] == PROMO_R[player]


def cell_name(cell) -> str:
    """(c,r) -> de Vasa notation, e.g. (5,8) -> 'f1'."""
    c, r = cell
    return f"{FILES[c]}{9 - r}"


def _cell(sstr: str):
    return parse_cell(sstr)


@dataclass
class VState(HState):
    """The shared hex-chess state with de Vasa's own defaults.

    ``castling`` is a set of ``(player, rook_file)`` pairs and ``ep`` is
    ``(crossed_cell, double_stepped_pawn_cell)`` -- the ORDER the shipped
    package used, kept because ``selftest.py`` reads ``s.ep[0]``/``s.ep[1]``
    and because the serialized form goes to the production DB.
    """
    board: dict = field(default_factory=_setup_board)   # (c,r) -> (owner, letter)
    castling: frozenset = field(
        default_factory=lambda: frozenset(ALL_CASTLES))


def _poskey(board: dict, to_move: int, ep, castling) -> str:
    """Repetition key.  Kept verbatim (rather than using the core's) so that a
    match already stored in the DB keeps counting its own repetitions."""
    items = sorted((c, r, o, t) for (c, r), (o, t) in board.items())
    ep_s = f"{ep[0][0]},{ep[0][1]}" if ep else "-"
    cs = "".join(f"{p}{f}" for p, f in sorted(castling)) or "-"
    return (f"{to_move}|{ep_s}|{cs}|"
            + ";".join(f"{c},{r},{o},{t}" for c, r, o, t in items))


class DeVasaChess(HexChessLike):
    CELLS = CELLS
    FILES = FILES
    NAME_OF = NAMES
    PLY_CAP = PLY_CAP
    STATE = VState
    # STALEMATE_SCORED stays False: stalemate is an ordinary draw (CECV p. 203).

    # ---- notation ---------------------------------------------------------
    def cell_name(self, cell) -> str:
        return cell_name(cell)

    # ---- setup ------------------------------------------------------------
    def setup_board(self) -> dict:
        return _setup_board()

    def initial_castling(self) -> frozenset:
        return frozenset(ALL_CASTLES)

    # ---- pawns ------------------------------------------------------------
    def is_promo(self, player: int, cell) -> bool:
        return cell[1] == PROMO_R[player]

    def pawn_attackers(self, player: int, cell):
        """Reverse of PAWN_CAPS: the cells a pawn of `player` attacks `cell` from."""
        c, r = cell
        return [(c - dc, r - dr) for dc, dr in PAWN_CAPS[player]]

    def pawn_moves(self, s, cell, out) -> None:
        me, board = s.to_move, s.board
        c, r = cell
        for dc, dr in PAWN_FWD[me]:
            one = (c + dc, r + dr)
            if one not in self.CELLS or one in board:
                continue
            if self.is_promo(me, one):
                for pc in self.PROMO_CHOICES:
                    out.append((cell, one, pc, None, None))
            else:
                out.append((cell, one, None, None, None))
            # double step: same direction, from the pawn's home rank
            if r == PAWN_HOME_R[me]:
                two = (c + 2 * dc, r + 2 * dr)
                if two in self.CELLS and two not in board:
                    out.append((cell, two, None, None, None))
        for dc, dr in PAWN_CAPS[me]:
            tgt = (c + dc, r + dr)
            if tgt not in self.CELLS:
                continue
            occ = board.get(tgt)
            if occ is not None:
                if occ[0] != me:
                    if self.is_promo(me, tgt):
                        for pc in self.PROMO_CHOICES:
                            out.append((cell, tgt, pc, None, None))
                    else:
                        out.append((cell, tgt, None, None, None))
            elif s.ep is not None and tgt == s.ep[0]:
                # s.ep = (crossed cell, victim); the victim is carried
                # explicitly because with two forward directions it is not at a
                # fixed offset from the crossed cell.
                out.append((cell, tgt, None, s.ep[1], None))

    def ep_after(self, s, frm, to, piece: str):
        """Only a double step (2 x one forward direction) creates the right."""
        if piece != "P":
            return None
        d = (to[0] - frm[0], to[1] - frm[1])
        for fc, fr in PAWN_FWD[s.to_move]:
            if d == (2 * fc, 2 * fr):
                return ((frm[0] + fc, frm[1] + fr), to)
        return None

    # ---- castling ---------------------------------------------------------
    def castle_moves(self, s, out) -> None:
        me = s.to_move
        rights = [k for k in s.castling if k[0] == me]
        if not rights:
            return
        king = KING_START[me]
        if s.board.get(king) != (me, "K") or self.in_check(s.board, me):
            return
        for key in sorted(rights):
            if s.board.get(ROOK_START[key]) != (me, "R"):
                continue
            _short, king_to, rook_to, between, king_path = CASTLE[key]
            if any(x in s.board for x in between):
                continue
            # The king may not cross an attacked cell; its start is already
            # known safe and its destination is checked by the in-check filter.
            if any(self.attacked(s.board, x, 1 - me) for x in king_path[1:-1]):
                continue
            out.append((king, king_to, None, None, (ROOK_START[key], rook_to)))

    def update_castling(self, rights: frozenset, frm, to, board,
                        new_board=None) -> frozenset:
        """Keep a right only while its king AND its rook still stand at home.

        The core hands us the PRE-move board, so the two cells that matter are
        resolved through the move: `frm` is vacated and `to` receives the mover
        (a promotion piece is never a rook of the right colour on that cell,
        and a castling move vacates KING_START, killing both of that side's
        rights anyway).
        """
        def at(c):
            if c == frm:
                return None
            if c == to:
                return board[frm]
            return board.get(c)

        return frozenset(k for k in rights
                         if at(KING_START[k[0]]) == (k[0], "K")
                         and at(ROOK_START[k]) == (k[0], "R"))

    # ---- state encoding (DO NOT CHANGE: async matches are stored serialized) --
    def poskey(self, board: dict, to_move: int, ep, castling) -> str:
        return _poskey(board, to_move, ep, castling)

    def ep_to_json(self, ep):
        return None if ep is None else [cell_str(ep[0]), cell_str(ep[1])]

    def ep_from_json(self, v):
        return (parse_cell(v[0]), parse_cell(v[1])) if v else None

    def castling_to_json(self, rights):
        return sorted(f"{p}{f}" for p, f in rights)

    def castling_from_json(self, v):
        if v is None:                       # legacy states predate the field
            v = [f"{p}{f}" for p, f in ALL_CASTLES]
        return frozenset((int(x[0]), x[1]) for x in v)

    # ---- presentation ------------------------------------------------------
    def describe_move(self, s, move: str) -> str:
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

    def board_spec(self, s) -> dict:
        # The three hex colours (bishop colour classes): colour = (c - r) mod 3.
        # Which class is light / mid / dark was read off the Wikipedia
        # diagram's pixels (0 light, 1 mid, 2 dark); the three hex codes are
        # the platform's shared hex-chess palette. This puts the three bishops
        # (c1/e1/g1) on the three colours.
        shades = {0: "#ffce9e", 1: "#e8ab6f", 2: "#d18b47"}
        tints = {f"{c},{r}": shades[(c - r) % 3]
                 for r in range(H) for c in range(W)}
        return {"type": "hex", "shape": "rhombus", "width": W, "height": H,
                # De Vasa's ranks are drawn HORIZONTAL, which is the pointy-top
                # default -- do NOT set "flat" here (that is for the
                # vertical-file hex chesses). See SPEC.md.
                "tints": tints}


# --- module-level helpers kept for selftest.py / callers ---------------------
_G = DeVasaChess()


def _attacked(board: dict, cell, by: int) -> bool:
    return _G.attacked(board, cell, by)


def _king_cell(board: dict, player: int):
    return _G.king_cell(board, player)


def _in_check(board: dict, player: int) -> bool:
    return _G.in_check(board, player)
