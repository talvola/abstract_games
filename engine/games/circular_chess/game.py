"""Circular Chess -- the medieval round game revived by Dave Reynolds (Lincoln,
England, 1983; Circular Chess Society + World Championship from 1996).

The board is an ANNULUS: 4 concentric rings x 16 sectors = 64 cells (no centre
square -- the hole is unplayable). It is topologically a 16-wide x 4-tall
CYLINDER: the SECTOR axis (0..15) wraps modulo 16 (going round the ring), while
the RING axis (0 = innermost .. 3 = outermost) is bounded (no wrap across the
centre hole or off the outer edge). Cell ids are ``"sector,ring"``.

Standard chess pieces on the cylinder geometry:

* Rook   -- slides around a ring (sector +/-1, wrapping) OR radially (ring +/-1).
* Bishop -- slides diagonally (sector +/-1 AND ring +/-1).
* Queen  -- rook + bishop.
* Knight -- (+/-1,+/-2) / (+/-2,+/-1), sector mod 16, ring bounded.
* King   -- one step to any of 8 neighbours.

Setup ("folded" standard board -- split down the middle, join the short ends,
bend into a ring). Each army straddles a line; the two lines sit on opposite
sides of the board. White straddles the seam between sectors 15|0; Black the
opposite seam between sectors 7|8. King & Queen on the inner ring adjacent
across the seam, then Bishops, Knights, Rooks going outward; the pawns sit one
sector further toward the enemy:

    sector : ring0(inner) ring1 ring2 ring3(outer)
    White  15 :  Q  B  N  R          (queenside stack)
            0 :  K  B  N  R          (kingside stack)
            1 :  P  P  P  P          (pawns, travel +sector)
           14 :  P  P  P  P          (pawns, travel -sector)
    Black   7 :  Q  B  N  R
            8 :  K  B  N  R
            9 :  P  P  P  P          (pawns, travel +sector)
            6 :  P  P  P  P          (pawns, travel -sector)

PAWNS keep a FIXED rotational direction round the board (each pawn "continues in
that direction"). Each army's two pawn groups march in OPPOSITE directions, both
heading for the opponent's back pieces on the far seam. A pawn's direction is a
pure function of its side and sector (the two streams never share a sector):

* White pawns on sectors 1..7  travel +sector; on 8..14 travel -sector.
* Black pawns on sectors 9..15 travel +sector; on 0..6  travel -sector.

A pawn promotes on reaching the opponent's back-piece sectors (6 squares from
start): White promotes on sectors 7 or 8, Black on sectors 15 or 0 -- to
Q/R/B/N. Pawns may advance two squares from their HOME sector (Lincoln version,
per Jelliss/mayhematics; the chessvariants rules list only castling and en
passant as removed) -- toggle with the ``double_step`` option. There is NO en
passant and NO castling.

The NULL-MOVE rule: a rook or queen may not run the FULL circle round a ring
back to its own square (a move that doesn't change the position). Implemented by
capping a circular ray at 15 steps, so it stops one sector short of its origin.

Check / checkmate / stalemate are standard; stalemate is an honest DRAW. Draws
also on the fifty-move rule, king-vs-king, and a hard ply cap (termination).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
NSEC = 16          # sectors round a ring (wraps)
NRING = 4          # rings (0 = inner .. 3 = outer; bounded)

# --- movement offsets (dsector, dring) ---
SECTOR_DIRS = [(1, 0), (-1, 0)]          # around a ring (circular)
RADIAL_DIRS = [(0, 1), (0, -1)]          # across rings (bounded)
DIAG_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ROOK_DIRS = SECTOR_DIRS + RADIAL_DIRS
BISHOP_DIRS = DIAG_DIRS
QUEEN_DIRS = ROOK_DIRS + BISHOP_DIRS
KING_STEPS = SECTOR_DIRS + RADIAL_DIRS + DIAG_DIRS
KNIGHT_LEAPS = [(1, 2), (1, -2), (-1, 2), (-1, -2),
                (2, 1), (2, -1), (-2, 1), (-2, -1)]

SLIDE_DIRS = {"R": ROOK_DIRS, "B": BISHOP_DIRS, "Q": QUEEN_DIRS}
LEAPS = {"N": KNIGHT_LEAPS, "K": KING_STEPS}

PIECE_VALUE = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}

# Pawn direction: promotion sectors and home (double-step) sectors per side.
PROMO_SECTORS = {WHITE: {7, 8}, BLACK: {0, 15}}
HOME_SECTORS = {WHITE: {1, 14}, BLACK: {6, 9}}

PLY_CAP = 500
FIFTY_MOVE = 100   # half-moves without a pawn move or capture -> draw


def pawn_dir(player: int, s: int) -> int:
    """The fixed rotational direction (+1 / -1) of a pawn of ``player`` on sector
    ``s``. The two streams occupy disjoint sector ranges, so this is exact."""
    if player == WHITE:
        return 1 if 1 <= s <= 7 else -1        # -1 on 8..14
    return 1 if 9 <= s <= 15 else -1           # -1 on 0..6


def _key(s: int, g: int) -> str:
    return f"{s},{g}"


def _parse_cell(cid: str):
    a, b = cid.split(",")
    return int(a), int(b)


@dataclass
class CCState:
    board: dict = field(default_factory=dict)     # (sector, ring) -> (player, piece)
    to_move: int = WHITE
    halfmove: int = 0                              # for the fifty-move draw
    ply: int = 0
    result: Optional[str] = None                   # None / "W0" / "W1" / "D"
    last: Optional[tuple] = None                    # ((fs,fg),(ts,tg)) for render
    double_step: bool = True


class CircularChess(Game):
    name = "Circular Chess"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> CCState:
        opts = options or {}
        double_step = bool(opts.get("double_step", True))
        b: dict = {}
        stack = ["B", "N", "R"]  # rings 1,2,3 outward from the K/Q on ring 0

        def place(base_sector: int, player: int, king_sector: int, queen_sector: int):
            # king stack and queen stack
            b[(king_sector, 0)] = (player, "K")
            b[(queen_sector, 0)] = (player, "Q")
            for g, pc in enumerate(stack, start=1):
                b[(king_sector, g)] = (player, pc)
                b[(queen_sector, g)] = (player, pc)

        # White: K stack at sector 0, Q stack at sector 15; pawns on 1 and 14.
        place(0, WHITE, king_sector=0, queen_sector=15)
        for g in range(NRING):
            b[(1, g)] = (WHITE, "P")
            b[(14, g)] = (WHITE, "P")
        # Black: K stack at sector 8, Q stack at sector 7; pawns on 9 and 6.
        place(8, BLACK, king_sector=8, queen_sector=7)
        for g in range(NRING):
            b[(9, g)] = (BLACK, "P")
            b[(6, g)] = (BLACK, "P")

        return CCState(board=b, to_move=WHITE, double_step=double_step)

    def current_player(self, s: CCState) -> int:
        return s.to_move

    # ---- geometry helpers --------------------------------------------------
    @staticmethod
    def _on(g: int) -> bool:
        return 0 <= g < NRING

    def _slide_targets(self, board, s, g, ds, dg):
        """Yield (cell, occupant) along a ray. Circular rays (dg == 0) are capped
        at 15 steps so they never complete the full circle back to the origin
        (the null-move ban); radial/diagonal rays stop at the ring boundary."""
        for step in range(1, NSEC):           # 1..15
            ns = (s + ds * step) % NSEC
            ng = g + dg * step
            if not self._on(ng):
                return
            occ = board.get((ns, ng))
            yield (ns, ng), occ
            if occ is not None:
                return

    def _attacked(self, board, s, g, by: int) -> bool:
        """Is cell (s,g) attacked by any piece of player ``by``?"""
        # pawns: a `by` pawn at (ps,pg) with its direction d attacks (ps+d, pg+/-1)
        for d in (1, -1):
            ps = (s - d) % NSEC
            if pawn_dir(by, ps) != d:
                continue
            for pg in (g - 1, g + 1):
                if self._on(pg) and board.get((ps, pg)) == (by, "P"):
                    return True
        # knights
        for ds, dg in KNIGHT_LEAPS:
            ns, ng = (s - ds) % NSEC, g - dg
            if self._on(ng) and board.get((ns, ng)) == (by, "N"):
                return True
        # king
        for ds, dg in KING_STEPS:
            ns, ng = (s - ds) % NSEC, g - dg
            if self._on(ng) and board.get((ns, ng)) == (by, "K"):
                return True
        # sliders
        for ds, dg in QUEEN_DIRS:
            for (ns, ng), occ in self._slide_targets(board, s, g, ds, dg):
                if occ is None:
                    continue
                if occ[0] == by:
                    pc = occ[1]
                    if pc == "Q":
                        return True
                    if pc == "R" and (ds, dg) in ROOK_DIRS:
                        return True
                    if pc == "B" and (ds, dg) in BISHOP_DIRS:
                        return True
                break
        return False

    def _king_cell(self, board, player):
        for cell, (pl, pc) in board.items():
            if pl == player and pc == "K":
                return cell
        return None

    def _in_check(self, board, player) -> bool:
        kc = self._king_cell(board, player)
        if kc is None:
            return False
        return self._attacked(board, kc[0], kc[1], 1 - player)

    # ---- pseudo-move generation -------------------------------------------
    def _pawn_moves(self, board, s, g, player, double_step):
        d = pawn_dir(player, s)
        # forward one
        ns = (s + d) % NSEC
        moves = []
        if self._on(g) and (ns, g) not in board:
            moves += self._emit_pawn(s, g, ns, g, player)
            # forward two from home
            if double_step and s in HOME_SECTORS[player]:
                ns2 = (s + 2 * d) % NSEC
                if (ns2, g) not in board:
                    moves.append((_key(s, g), _key(ns2, g), None))
        # captures (diagonal in the travel direction)
        for dg in (-1, 1):
            ng = g + dg
            if not self._on(ng):
                continue
            occ = board.get((ns, ng))
            if occ is not None and occ[0] != player:
                moves += self._emit_pawn(s, g, ns, ng, player)
        return moves

    def _emit_pawn(self, s, g, ts, tg, player):
        """Emit one pawn destination, expanded into promotions if on a promo
        sector."""
        frm, to = _key(s, g), _key(ts, tg)
        if ts in PROMO_SECTORS[player]:
            return [(frm, to, pc) for pc in ("Q", "R", "B", "N")]
        return [(frm, to, None)]

    def _pseudo(self, s: CCState):
        board, player = s.board, s.to_move
        for (cs, cg), (pl, pc) in list(board.items()):
            if pl != player:
                continue
            if pc == "P":
                yield from self._pawn_moves(board, cs, cg, player, s.double_step)
                continue
            if pc in LEAPS:
                for ds, dg in LEAPS[pc]:
                    ns, ng = (cs + ds) % NSEC, cg + dg
                    if not self._on(ng):
                        continue
                    occ = board.get((ns, ng))
                    if occ is None or occ[0] != player:
                        yield (_key(cs, cg), _key(ns, ng), None)
                continue
            # slider (R/B/Q) -- dedup destinations (a rook's two circular rays
            # cover the same squares on an open ring)
            seen = set()
            for ds, dg in SLIDE_DIRS[pc]:
                for (ns, ng), occ in self._slide_targets(board, cs, cg, ds, dg):
                    if occ is None:
                        if (ns, ng) not in seen:
                            seen.add((ns, ng))
                            yield (_key(cs, cg), _key(ns, ng), None)
                    else:
                        if occ[0] != player and (ns, ng) not in seen:
                            seen.add((ns, ng))
                            yield (_key(cs, cg), _key(ns, ng), None)
                        break

    def _make(self, board, frm, to, promo):
        """Apply a (frm,to,promo) tuple to a COPY of board; return (new_board,
        captured_bool, pawn_move_bool)."""
        nb = dict(board)
        fc = _parse_cell(frm)
        tc = _parse_cell(to)
        player, pc = nb.pop(fc)
        captured = tc in nb
        nb[tc] = (player, promo if promo else pc)
        return nb, captured, (pc == "P")

    # ---- public move API ---------------------------------------------------
    def _legal_tuples(self, s: CCState):
        out = []
        player = s.to_move
        for frm, to, promo in self._pseudo(s):
            nb, _, _ = self._make(s.board, frm, to, promo)
            if not self._in_check(nb, player):
                out.append((frm, to, promo))
        return out

    @staticmethod
    def _tuple_to_move(frm, to, promo) -> str:
        m = f"{frm}>{to}"
        if promo:
            m += f"={promo}"
        return m

    def legal_moves(self, s: CCState):
        if s.result is not None:
            return []
        return [self._tuple_to_move(*t) for t in self._legal_tuples(s)]

    def _parse_move(self, move: str):
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        frm, to = move.split(">")
        return frm, to, promo

    def apply_move(self, s: CCState, move: str, rng=None) -> CCState:
        frm, to, promo = self._parse_move(move)
        nb, captured, pawn_move = self._make(s.board, frm, to, promo)
        halfmove = 0 if (captured or pawn_move) else s.halfmove + 1
        ply = s.ply + 1
        nxt = 1 - s.to_move
        ns = CCState(board=nb, to_move=nxt, halfmove=halfmove, ply=ply,
                     last=(_parse_cell(frm), _parse_cell(to)),
                     double_step=s.double_step)
        ns.result = self._compute_result(ns)
        return ns

    def _insufficient(self, board) -> bool:
        # Draw only on lone kings (K vs K).
        return all(pc == "K" for (_, pc) in board.values())

    def _compute_result(self, s: CCState) -> Optional[str]:
        if self._insufficient(s.board):
            return "D"
        if s.halfmove >= FIFTY_MOVE:
            return "D"
        if s.ply >= PLY_CAP:
            return "D"
        if self._legal_tuples(s):
            return None
        # no legal moves: checkmate (loss for side to move) or stalemate (draw)
        if self._in_check(s.board, s.to_move):
            winner = 1 - s.to_move
            return f"W{winner}"
        return "D"

    def is_terminal(self, s: CCState) -> bool:
        return s.result is not None

    def returns(self, s: CCState):
        if s.result == "W0":
            return [1.0, -1.0]
        if s.result == "W1":
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- heuristic (bot eval) ---------------------------------------------
    def heuristic(self, s: CCState):
        if s.result is not None:
            return self.returns(s)
        diff = 0.0
        for (pl, pc) in s.board.values():
            v = PIECE_VALUE[pc]
            diff += v if pl == WHITE else -v
        t = math.tanh(diff / 8.0)
        return [t, -t]

    # ---- persistence -------------------------------------------------------
    def serialize(self, s: CCState) -> dict:
        return {
            "board": {_key(cs, cg): [pl, pc] for (cs, cg), (pl, pc) in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
            "result": s.result,
            "last": [list(s.last[0]), list(s.last[1])] if s.last else None,
            "double_step": s.double_step,
        }

    def deserialize(self, d: dict) -> CCState:
        board = {}
        for cid, (pl, pc) in d["board"].items():
            board[_parse_cell(cid)] = (pl, pc)
        last = None
        if d.get("last"):
            last = (tuple(d["last"][0]), tuple(d["last"][1]))
        return CCState(
            board=board,
            to_move=d["to_move"],
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            result=d.get("result"),
            last=last,
            double_step=d.get("double_step", True),
        )

    # ---- notation ----------------------------------------------------------
    def describe_move(self, s: CCState, move: str) -> str:
        frm, to, promo = self._parse_move(move)
        pc = s.board.get(_parse_cell(frm), (None, "?"))[1]
        cap = "x" if _parse_cell(to) in s.board else "-"
        letter = "" if pc == "P" else pc
        txt = f"{letter}{frm}{cap}{to}"
        if promo:
            txt += f"={promo}"
        return txt

    # ---- render (polygons annulus) ----------------------------------------
    _CX = _CY = 150.0
    _R0 = 34.0          # inner radius (centre hole)
    _DR = 26.0          # ring thickness
    _ARC_SUBDIV = 4     # points sampled along each cell arc

    def _cell_polygon(self, s: int, g: int):
        """Annular-sector polygon for cell (sector s, ring g). Sector s spans the
        angular wedge [s, s+1] * 22.5deg; ring g the radial band
        [R0+g*DR, R0+(g+1)*DR]. Arcs are approximated by sampled points so the
        cell reads as curved; winding is consistent (outer arc CCW then inner arc
        back)."""
        a0 = (s / NSEC) * 2.0 * math.pi
        a1 = ((s + 1) / NSEC) * 2.0 * math.pi
        r_in = self._R0 + g * self._DR
        r_out = self._R0 + (g + 1) * self._DR
        n = self._ARC_SUBDIV
        pts = []
        # outer arc a0 -> a1
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append([round(self._CX + r_out * math.cos(a), 2),
                        round(self._CY + r_out * math.sin(a), 2)])
        # inner arc a1 -> a0
        for i in range(n + 1):
            a = a1 - (a1 - a0) * i / n
            pts.append([round(self._CX + r_in * math.cos(a), 2),
                        round(self._CY + r_in * math.sin(a), 2)])
        return pts

    def render(self, s: CCState, perspective=None) -> dict:
        cells = []
        for g in range(NRING):
            for sec in range(NSEC):
                cells.append({"id": _key(sec, g), "points": self._cell_polygon(sec, g)})
        pieces = []
        for (cs, cg), (pl, pc) in s.board.items():
            pieces.append({"cell": _key(cs, cg), "owner": pl, "label": pc})
        highlights = []
        if s.last:
            (fs, fg), (ts, tg) = s.last
            highlights.append({"cell": _key(fs, fg), "kind": "last-move"})
            highlights.append({"cell": _key(ts, tg), "kind": "last-move"})

        if s.result == "W0":
            caption = "White wins (checkmate)"
        elif s.result == "W1":
            caption = "Black wins (checkmate)"
        elif s.result == "D":
            caption = "Draw"
        else:
            who = "White" if s.to_move == WHITE else "Black"
            chk = " -- in check" if self._in_check(s.board, s.to_move) else ""
            caption = f"{who} to move{chk}"

        return {
            "board": {"type": "polygons", "cells": cells},
            "pieceset": "chess",
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
