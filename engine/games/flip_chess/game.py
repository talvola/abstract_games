"""Flip Chess / Flip Shogi — John William Brown (1998).

An entry (second prize) in Hans Bodlaender's "38-square challenge". Documented
on chessvariants.com (38.dir/flip.html); rules re-derived from that page, its
piece-pattern / board-array GIFs, and the author-sanctioned Zillions file
(programs.dir/zillions/flip.zip, Flip3.zrf, by Hans Bodlaender). Thomas E. Havel
collaborated. `Meta-Chess` (Brown) is the print source.

Board / notation
----------------
NOT the crazy_38s Celtic-knot board. Flip Chess uses a plain rectangular lattice
of **7 files (a-g) x 6 ranks (1-6) with the four CORNERS removed** (a1, a6, g1,
g6) = 38 cells. A cell is the tuple ``(c, r)`` with c = file 1..7 (a..g) and
r = rank 1..6. White's home rank is r=1 (bottom), Black's is r=6 (top); White
moves toward +r, Black toward -r. All pieces move by ordinary chess geometry on
this grid (no bridging / loop-effect — that was crazy_38s, a different game).

The flip mechanic
-----------------
Every piece is a double-sided counter. A non-King piece may flip to its other
side at the close of its move, OR flip in place as a whole move (CVP rule 1).
Flip pairs: Pawn(P) <-> Berolina Pawn(X); Bishop(B) <-> Rook(R); Ferz(F) <->
Knight(N). King(K) is royal and never flips. A Pawn/Berolina reaching the last
rank promotes (forced) to a Prince(C) — a non-royal king-stepper used only as a
promotion piece; the Prince has no reverse side.

Pieces (all "as in usual chess" unless noted; from Flip3.zrf + the CVP legend):
  P  Pawn        — steps 1 forward, captures 1 diagonally-forward.
  X  Berolina     — steps 1 diagonally-forward (no capture), captures 1 straight
                    forward. (Berlin/Berolina pawn, Nebermann 1926.)
  F  Ferz         — steps 1 square diagonally.
  N  Knight       — the ordinary chess knight leap.
  B  Bishop       — slides diagonally.
  R  Rook         — slides orthogonally (no castling).
  K  King         — steps 1 in any direction, may not move into check (royal).
  C  Prince        — steps 1 in any direction, NOT royal (promotion piece only).

There is NO initial double-step and NO en passant: both are dead code in the
reference ZRF (its "third-rank" two-step zone is a single unreachable square and
its En-Passant macro is never attached to a piece), so a forward-moving pawn
never triggers them. This is the game as the reference engine actually plays.

Win / draw
----------
Win by checkmating the King, OR by reducing the opponent to a **bare King**
(CVP rule 3: "A bare King loses" — a lone king, and in Shogi mode an empty hand
too). Stalemate (no legal move, not in check) is an honest draw; four-fold
repetition and a hard ply cap also draw (flips + Shogi drops recycle material).

Flip Shogi (manifest option ``mode = "shogi"``) adds shogi-style drops
(CVP rules 4-8): captured pieces switch sides into your reserve and may be
dropped; a drop may be made with EITHER side of the token up; a drop must
attack (threaten) an enemy piece; Pawn/Berolina drops are limited to your own
first two ranks. See rules.md for the ruleset as implemented.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
PLY_CAP = 300               # hard draw cap (flips / drops recycle material)
REP_LIMIT = 4              # four-fold repetition -> draw

FILES = 7                  # a..g
RANKS = 6                  # 1..6
LETTERS = "abcdefg"

# 7x6 rectangle with the four corners removed  ->  38 cells.
MISSING = frozenset({(1, 1), (1, 6), (7, 1), (7, 6)})
CELLS = frozenset((c, r) for c in range(1, FILES + 1) for r in range(1, RANKS + 1)
                  if (c, r) not in MISSING)
assert len(CELLS) == 38, len(CELLS)

# Movement geometry (ordinary chess on the (c,r) grid).
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
KINGD = DIAG + ORTH
KNIGHT = [(1, 2), (1, -2), (-1, 2), (-1, -2), (2, 1), (2, -1), (-2, 1), (-2, -1)]

# Flip pairs. K (royal) and C (Prince) are single-sided.
FLIP = {"P": "X", "X": "P", "B": "R", "R": "B", "F": "N", "N": "F"}
# Capturing a piece banks the PAIR token (which side you drop is your choice).
PAIR_TOKEN = {"P": "P", "X": "P", "C": "P", "B": "B", "R": "B", "F": "F", "N": "F"}
DROP_SIDES = {"P": ("P", "X"), "B": ("B", "R"), "F": ("F", "N")}
VALUE = {"P": 1, "X": 1, "F": 2, "N": 3, "B": 3, "R": 5, "C": 2, "K": 0}
TOKEN_VALUE = {"P": 1, "B": 4, "F": 3}

CHOICE_NAMES = {"P": "Pawn", "X": "Berolina Pawn", "B": "Bishop", "R": "Rook",
                "F": "Ferz", "N": "Knight", "C": "Prince"}


def _fwd(owner):
    return 1 if owner == WHITE else -1


def promo_rank(owner):
    return RANKS if owner == WHITE else 1


def _cid(c):
    return f"{c[0]},{c[1]}"


def _cell(s):
    a, b = s.split(",")
    return (int(a), int(b))


def _label(c):
    return f"{LETTERS[c[0] - 1]}{c[1]}"


# --------------------------------------------------------------------------- #
#  State
# --------------------------------------------------------------------------- #
@dataclass
class FState:
    board: dict = field(default_factory=dict)       # (c,r) -> (owner, ptype)
    hands: dict = field(default_factory=lambda: {WHITE: {}, BLACK: {}})
    to_move: int = WHITE
    mode: str = "chess"                              # "chess" or "shogi"
    winner: Optional[int] = None
    draw: bool = False
    reps: dict = field(default_factory=dict)
    ply: int = 0
    last: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  Geometry helpers
# --------------------------------------------------------------------------- #
def _slide(board, cell, dc, dr, owner):
    """Reachable cells along a ray (moves + a capture of an enemy non-King)."""
    out = []
    c, r = cell
    while True:
        c += dc
        r += dr
        cc = (c, r)
        if cc not in CELLS:
            break
        occ = board.get(cc)
        if occ is None:
            out.append(cc)
            continue
        if occ[0] != owner and occ[1] != "K":
            out.append(cc)
        break
    return out


def _piece_targets(board, cell, owner, pt):
    """Legal-destination cells (empty or an enemy non-King) — geometry only."""
    c, r = cell
    fwd = _fwd(owner)
    out = []

    def enemy_here(cc):
        o = board.get(cc)
        return o is not None and o[0] != owner and o[1] != "K"

    if pt == "P":
        f = (c, r + fwd)
        if f in CELLS and board.get(f) is None:
            out.append(f)
        for dc in (-1, 1):
            cc = (c + dc, r + fwd)
            if cc in CELLS and enemy_here(cc):
                out.append(cc)
    elif pt == "X":                              # Berolina: move diag, take straight
        for dc in (-1, 1):
            cc = (c + dc, r + fwd)
            if cc in CELLS and board.get(cc) is None:
                out.append(cc)
        f = (c, r + fwd)
        if f in CELLS and enemy_here(f):
            out.append(f)
    elif pt == "F":
        for dc, dr in DIAG:
            cc = (c + dc, r + dr)
            if cc in CELLS and (board.get(cc) is None or enemy_here(cc)):
                out.append(cc)
    elif pt == "N":
        for dc, dr in KNIGHT:
            cc = (c + dc, r + dr)
            if cc in CELLS and (board.get(cc) is None or enemy_here(cc)):
                out.append(cc)
    elif pt in ("K", "C"):
        for dc, dr in KINGD:
            cc = (c + dc, r + dr)
            if cc in CELLS and (board.get(cc) is None or enemy_here(cc)):
                out.append(cc)
    elif pt == "B":
        for dc, dr in DIAG:
            out += _slide(board, cell, dc, dr, owner)
    elif pt == "R":
        for dc, dr in ORTH:
            out += _slide(board, cell, dc, dr, owner)
    return out


def _piece_attacks(board, cell, owner, pt):
    """Squares this piece attacks (for check + the Shogi drop-attacks rule)."""
    c, r = cell
    fwd = _fwd(owner)
    hit = set()
    if pt == "P":
        for dc in (-1, 1):
            cc = (c + dc, r + fwd)
            if cc in CELLS:
                hit.add(cc)
    elif pt == "X":
        cc = (c, r + fwd)
        if cc in CELLS:
            hit.add(cc)
    elif pt == "F":
        for dc, dr in DIAG:
            cc = (c + dc, r + dr)
            if cc in CELLS:
                hit.add(cc)
    elif pt == "N":
        for dc, dr in KNIGHT:
            cc = (c + dc, r + dr)
            if cc in CELLS:
                hit.add(cc)
    elif pt in ("K", "C"):
        for dc, dr in KINGD:
            cc = (c + dc, r + dr)
            if cc in CELLS:
                hit.add(cc)
    elif pt == "B":
        for dc, dr in DIAG:
            hit.update(_ray_attack(board, cell, dc, dr))
    elif pt == "R":
        for dc, dr in ORTH:
            hit.update(_ray_attack(board, cell, dc, dr))
    return hit


def _ray_attack(board, cell, dc, dr):
    out = []
    c, r = cell
    while True:
        c += dc
        r += dr
        cc = (c, r)
        if cc not in CELLS:
            break
        out.append(cc)
        if board.get(cc) is not None:
            break                     # first blocker is attacked, then stop
    return out


def _attacked(board, by_owner):
    hit = set()
    for cell, (o, pt) in board.items():
        if o == by_owner:
            hit |= _piece_attacks(board, cell, o, pt)
    return hit


def _king_cell(board, owner):
    for c, (o, pt) in board.items():
        if o == owner and pt == "K":
            return c
    return None


def _in_check(board, owner):
    kc = _king_cell(board, owner)
    if kc is None:
        return False
    return kc in _attacked(board, 1 - owner)


def _bare_king(board, hands, owner, mode):
    """CVP rule 3 — a lone King (empty hand too, in Shogi) has lost."""
    npieces = sum(1 for (o, pt) in board.values() if o == owner)
    if npieces != 1:
        return False
    if mode == "shogi" and sum(hands.get(owner, {}).values()) > 0:
        return False
    return True


# --------------------------------------------------------------------------- #
#  Move application (pure)
# --------------------------------------------------------------------------- #
def _apply(board, hands, owner, move, mode):
    """Return (new_board, new_hands, info). Does not touch outcome flags."""
    nb = dict(board)
    nh = {WHITE: dict(hands.get(WHITE, {})), BLACK: dict(hands.get(BLACK, {}))}
    info = {"from": None, "to": None, "cap": None, "drop": None,
            "ptype": None, "flip": None, "promo": False}

    if "@" in move:                                  # drop  "L@c,r"
        side, cell = move.split("@")
        c = _cell(cell)
        nb[c] = (owner, side)
        tok = PAIR_TOKEN[side]
        nh[owner][tok] = nh[owner].get(tok, 0) - 1
        if nh[owner][tok] <= 0:
            del nh[owner][tok]
        info.update(drop=side, to=c, ptype=side)
        return nb, nh, info

    path, _, suffix = move.partition("=")
    frm_s, to_s = path.split(">")
    frm, to = _cell(frm_s), _cell(to_s)
    o_from, pt = nb[frm]

    if frm == to:                                    # flip in place
        nb[frm] = (owner, suffix)
        info.update({"from": frm, "to": to, "ptype": suffix, "flip": suffix})
        return nb, nh, info

    occ = nb.get(to)
    if occ is not None:                              # capture
        info["cap"] = occ[1]
        if mode == "shogi":
            tok = PAIR_TOKEN[occ[1]]
            nh[owner][tok] = nh[owner].get(tok, 0) + 1
    del nb[frm]
    newpt = pt
    if suffix:
        newpt = suffix                               # flip or promotion (=C)
        if suffix == "C":
            info["promo"] = True
        elif suffix != pt:
            info["flip"] = suffix
    nb[to] = (owner, newpt)
    info.update({"from": frm, "to": to, "ptype": newpt})
    return nb, nh, info


def _king_safe_after(board, owner, frm, to):
    """Own-king safety of a displacement — independent of the flip choice."""
    nb = dict(board)
    o, pt = nb.pop(frm)
    nb[to] = (owner, pt)               # type does not affect OWN king safety
    return not _in_check(nb, owner)


def _all_legal(board, hands, owner, mode):
    out = []
    in_check = _in_check(board, owner)
    prank = promo_rank(owner)

    for cell, (o, pt) in list(board.items()):
        if o != owner:
            continue
        a = _cid(cell)
        for to in _piece_targets(board, cell, owner, pt):
            if not _king_safe_after(board, owner, cell, to):
                continue
            b = _cid(to)
            base = f"{a}>{b}"
            if pt in ("P", "X") and to[1] == prank:
                out.append(base + "=C")               # forced promotion to Prince
            elif pt in FLIP:
                out.append(f"{base}={pt}")            # move, keep this side
                out.append(f"{base}={FLIP[pt]}")      # move, flip to other side
            else:                                     # K, C (non-flip)
                out.append(base)
        # flip in place (a whole move) — legal only when not in check
        if pt in FLIP and not in_check:
            out.append(f"{a}>{a}={FLIP[pt]}")

    if mode == "shogi":
        out += _drop_moves(board, hands, owner)
    return out


def _drop_moves(board, hands, owner):
    out = []
    empties = [c for c in CELLS if c not in board]
    hand = hands.get(owner, {})
    for tok, cnt in hand.items():
        if cnt <= 0:
            continue
        for side in DROP_SIDES[tok]:
            for c in empties:
                # rule 8: Pawn/Berolina drops only on your own first two ranks
                if side in ("P", "X"):
                    own_rank = c[1] if owner == WHITE else (RANKS + 1 - c[1])
                    if own_rank > 2:
                        continue
                nb = dict(board)
                nb[c] = (owner, side)
                if _in_check(nb, owner):
                    continue
                # rule 7: a drop must attack (threaten) an enemy piece
                atk = _piece_attacks(nb, c, owner, side)
                if not any(nb.get(t) and nb[t][0] != owner for t in atk):
                    continue
                out.append(f"{side}@{_cid(c)}")
    return out


def _poskey(board, hands, to_move, mode):
    b = ";".join(f"{_cid(c)}:{o}{pt}" for c, (o, pt) in sorted(board.items()))
    hh = "|".join(f"{o}:" + ",".join(f"{k}{v}" for k, v in sorted(hands.get(o, {}).items()))
                  for o in (WHITE, BLACK))
    return f"{b}#{hh}#{to_move}#{mode}"


# --------------------------------------------------------------------------- #
class FlipChess(Game):
    name = "Flip Chess"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None) -> FState:
        mode = "chess"
        if options and options.get("mode") in ("chess", "shogi"):
            mode = options["mode"]
        board = {}
        # White home rank 1 (bottom); pawns rank 2.
        white = {(2, 1): "B", (3, 1): "F", (4, 1): "K", (5, 1): "F", (6, 1): "B",
                 (2, 2): "P", (3, 2): "P", (4, 2): "P", (5, 2): "P", (6, 2): "P"}
        for c, pt in white.items():
            board[c] = (WHITE, pt)
        # Black = 180-degree rotation (c,r)->(FILES+1-c, RANKS+1-r).
        for (c, r), pt in white.items():
            board[(FILES + 1 - c, RANKS + 1 - r)] = (BLACK, pt)
        return FState(board=board, hands={WHITE: {}, BLACK: {}}, to_move=WHITE, mode=mode)

    def current_player(self, state):
        return state.to_move

    def is_terminal(self, state):
        return state.winner is not None or state.draw

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        return _all_legal(state.board, state.hands, state.to_move, state.mode)

    def apply_move(self, state, move, rng=None):
        owner = state.to_move
        nb, nh, info = _apply(state.board, state.hands, owner, move, state.mode)
        opp = 1 - owner
        ns = FState(board=nb, hands=nh, to_move=opp, mode=state.mode,
                    reps=dict(state.reps), ply=state.ply + 1)
        if info["from"] is not None:
            ns.last = [_cid(info["from"]), _cid(info["to"])]
        else:
            ns.last = [_cid(info["to"])]

        # 1) bare-king loss (CVP rule 3) — decisive at once
        if _bare_king(nb, nh, opp, state.mode):
            ns.winner = owner
            return ns
        # 2) checkmate / stalemate for the side to move
        if not _all_legal(nb, nh, opp, state.mode):
            if _in_check(nb, opp):
                ns.winner = owner              # checkmate
            else:
                ns.draw = True                 # stalemate -> honest draw
            return ns
        # 3) repetition / ply cap
        key = _poskey(nb, nh, opp, state.mode)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        if ns.reps[key] >= REP_LIMIT or ns.ply >= PLY_CAP:
            ns.draw = True
        return ns

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if p == state.winner else -1.0 for p in (WHITE, BLACK)]

    def heuristic(self, state):
        if state.winner is not None:
            return [1.0 if p == state.winner else -1.0 for p in (WHITE, BLACK)]
        if state.draw:
            return [0.0, 0.0]
        m = 0
        for (o, pt) in state.board.values():
            v = VALUE[pt]
            m += v if o == WHITE else -v
        for o in (WHITE, BLACK):
            for tok, cnt in state.hands.get(o, {}).items():
                v = TOKEN_VALUE.get(tok, 1) * cnt
                m += v if o == WHITE else -v
        h = math.tanh(m / 7.0)
        return [h, -h]

    # ---- notation --------------------------------------------------------
    def describe_move(self, state, move):
        owner = state.to_move
        if "@" in move:
            side, cell = move.split("@")
            return f"{CHOICE_NAMES[side][0]}{side}@{_label(_cell(cell))}"
        path, _, suffix = move.partition("=")
        frm, to = path.split(">")
        fc, tc = _cell(frm), _cell(to)
        pt = state.board.get(fc, (owner, "?"))[1]
        if fc == tc:
            return f"{_label(fc)}={suffix}"        # flip in place
        cap = "x" if tc in state.board else "-"
        s = f"{pt}{_label(fc)}{cap}{_label(tc)}"
        if suffix == "C":
            s += "=Pc"
        elif suffix and suffix != pt:
            s += f"={suffix}"
        return s

    # ---- persistence -----------------------------------------------------
    def serialize(self, state):
        return {
            "board": {_cid(c): [o, pt] for c, (o, pt) in state.board.items()},
            "hands": {str(o): dict(h) for o, h in state.hands.items()},
            "to_move": state.to_move,
            "mode": state.mode,
            "winner": state.winner,
            "draw": state.draw,
            "reps": dict(state.reps),
            "ply": state.ply,
            "last": list(state.last),
        }

    def deserialize(self, data):
        board = {_cell(k): (v[0], v[1]) for k, v in data["board"].items()}
        hands = {WHITE: dict(data["hands"].get("0", {})),
                 BLACK: dict(data["hands"].get("1", {}))}
        return FState(board=board, hands=hands, to_move=data["to_move"],
                      mode=data.get("mode", "chess"), winner=data["winner"],
                      draw=data["draw"], reps=dict(data.get("reps", {})),
                      ply=data.get("ply", 0), last=list(data.get("last", [])))

    # ---- render ----------------------------------------------------------
    def render(self, state, perspective=None):
        cells, tints = [], {}
        for (c, r) in sorted(CELLS):
            x0, x1 = c, c + 1
            y0, y1 = RANKS - r, RANKS + 1 - r            # rank 1 at the bottom
            cid = _cid((c, r))
            cells.append({"id": cid, "points": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]})
            tints[cid] = "#b9855a" if (c + r) % 2 == 0 else "#e2c9a0"
        pieces = [{"cell": _cid(c), "owner": o, "label": pt}
                  for c, (o, pt) in state.board.items()]
        names = {WHITE: "White", BLACK: "Black"}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif state.draw:
            cap = "Draw"
        else:
            chk = " (check)" if _in_check(state.board, state.to_move) else ""
            cap = f"{names[state.to_move]} to move{chk}"
        spec = {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "pieceset": "chess",
            "highlights": [{"cell": c, "kind": "last-move"} for c in state.last],
            "choiceNames": dict(CHOICE_NAMES),
            "caption": cap,
        }
        if state.mode == "shogi":
            reserve = {}
            for o in (WHITE, BLACK):
                chips = {}
                for tok, cnt in state.hands.get(o, {}).items():
                    if cnt > 0:                          # both sides share the token count
                        for side in DROP_SIDES[tok]:
                            chips[side] = cnt
                if chips:
                    reserve[str(o)] = chips
            if reserve:
                spec["reserve"] = reserve
        return spec
