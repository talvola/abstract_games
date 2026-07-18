"""Chaturaji -- Chaturanga for four players (the medieval Indian four-handed
dice-chess, a.k.a. Choupat/Chaturaji), reconstructed by Captain Hiram Cox and
Duncan Forbes and documented by Murray in his *History of Chess*.

Four armies of eight (King, Rook/Elephant, Knight/Horse, Boat/Ship, four Pawns)
sit in the four corners of an 8x8 board. Play goes CLOCKWISE: Red, Green, Yellow,
Black. Each turn a player throws two long dice (values 2-5); the pip decides which
arm may move -- 2 = Boat, 3 = Knight, 4 = Rook, 5 = King or Pawn -- and the player
makes up to two moves. There is no check or checkmate: kings are captured like any
other piece and the game is scored by the value of the men you take (King 5,
Rook 4, Knight 3, Boat 2, Pawn 1 -- al-Biruni's values). Take all three enemy
kings while your own survives and you sweep the board.

Randomness is modelled without a chance node (SPEC.md): the dice for a turn are
rolled and STORED in the state when the previous turn ends, so ``legal_moves`` is
deterministic given the state -- exactly the EinStein pattern. ``num_players`` is
a fixed 4.

An optional ``dice: off`` gives the diceless "modern" variant: one free move with
any piece per turn.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace

from agp.game import Game

SIZE = 8
VALUES = {"K": 5, "R": 4, "N": 3, "S": 2, "P": 1}

# Piece move geometry.
KNIGHT = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
KING = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
BOAT = [(2, 2), (2, -2), (-2, 2), (-2, -2)]          # Boat = Alfil (2 sq diagonal leaper)
ROOKDIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

# Per-seat pawn "forward" direction and its two diagonal-capture offsets.
# 0 Red faces down (-row), 1 Green faces left (-col),
# 2 Yellow faces up (+row), 3 Black faces right (+col).
FORWARD = {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}
PAWN_DIAG = {
    0: [(-1, -1), (1, -1)],
    1: [(-1, -1), (-1, 1)],
    2: [(-1, 1), (1, 1)],
    3: [(1, -1), (1, 1)],
}
PROMO_CHOICES = ["R", "N", "S"]                       # modern rule: Rook / Knight / Boat

# Dice: pip -> the piece-letters it may move (5 moves King OR Pawn).
DIE_PIECES = {2: {"S"}, 3: {"N"}, 4: {"R"}, 5: {"K", "P"}}
DIE_LABEL = {2: "Boat", 3: "Knight", 4: "Rook", 5: "King/Pawn"}
COLOR_NAMES = {0: "Red", 1: "Green", 2: "Yellow", 3: "Black"}

NO_CAP_LIMIT = 60          # plies with no capture -> settle
PLY_CAP = 400              # hard ply cap -> settle


def _sq(s):
    """Chess square like 'e8' -> (col, row) 0-based."""
    return (ord(s[0]) - 97, int(s[1]) - 1)


# Opening setup, per the chessvariants "Chaturanga for four players" entry.
_SETUP_SPEC = {
    0: {"K": "e8", "R": "f8", "N": "g8", "S": "h8", "P": ["e7", "f7", "g7", "h7"]},  # Red
    1: {"K": "h4", "R": "h3", "N": "h2", "S": "h1", "P": ["g1", "g2", "g3", "g4"]},  # Green
    2: {"K": "d1", "R": "c1", "N": "b1", "S": "a1", "P": ["a2", "b2", "c2", "d2"]},  # Yellow
    3: {"K": "a5", "R": "a6", "N": "a7", "S": "a8", "P": ["b5", "b6", "b7", "b8"]},  # Black
}


def _build_setup():
    b = {}
    for p, d in _SETUP_SPEC.items():
        for k in ("K", "R", "N", "S"):
            b[_sq(d[k])] = (p, k)
        for pw in d["P"]:
            b[_sq(pw)] = (p, "P")
    return b


SETUP = _build_setup()


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _on(t):
    return 0 <= t[0] < SIZE and 0 <= t[1] < SIZE


def _is_promo(p, c, r):
    return ((p == 0 and r == 0) or (p == 1 and c == 0) or
            (p == 2 and r == SIZE - 1) or (p == 3 and c == SIZE - 1))


@dataclass
class CState:
    board: dict = field(default_factory=dict)     # (c,r) -> (owner, piece)
    dice: list = field(default_factory=list)      # remaining pips this turn; ['*'] = free move
    to_move: int = 0
    points: list = field(default_factory=lambda: [0, 0, 0, 0])
    kings_by: list = field(default_factory=lambda: [0, 0, 0, 0])   # enemy kings each seat has taken
    king_alive: list = field(default_factory=lambda: [True, True, True, True])
    no_cap: int = 0
    ply: int = 0
    over: bool = False
    use_dice: bool = True
    last: object = None                            # last piece-move "c,r>c,r" (for render)


class Chaturaji(Game):
    uid = "chaturaji"
    name = "Chaturaji"

    @property
    def num_players(self):
        return 4

    # ------------------------------------------------------------------ setup
    def _roll(self, rng, use_dice):
        if not use_dice:
            return ["*"]
        return [rng.choice([2, 3, 4, 5]), rng.choice([2, 3, 4, 5])]

    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        opts = options or {}
        use_dice = opts.get("dice", "on") != "off"
        return CState(board=dict(SETUP), dice=self._roll(rng, use_dice), to_move=0,
                      use_dice=use_dice)

    def current_player(self, s):
        return s.to_move

    # -------------------------------------------------------------- move gen
    def _piece_moves(self, board, p, cell, pt):
        c, r = cell
        res = []

        def enemy(t):
            v = board.get(t)
            return v is not None and v[0] != p

        def empty(t):
            return t not in board

        if pt == "P":
            dc, dr = FORWARD[p]
            f = (c + dc, r + dr)
            if _on(f) and empty(f):
                res += self._pawn_strs(p, cell, f)
            for ddc, ddr in PAWN_DIAG[p]:
                t = (c + ddc, r + ddr)
                if _on(t) and enemy(t):
                    res += self._pawn_strs(p, cell, t)
            return res

        if pt == "R":
            for dc, dr in ROOKDIRS:
                x, y = c + dc, r + dr
                while _on((x, y)):
                    if empty((x, y)):
                        res.append(f"{c},{r}>{x},{y}")
                    else:
                        if enemy((x, y)):
                            res.append(f"{c},{r}>{x},{y}")
                        break
                    x += dc
                    y += dr
            return res

        offs = KNIGHT if pt == "N" else KING if pt == "K" else BOAT
        for dc, dr in offs:
            t = (c + dc, r + dr)
            if _on(t) and (empty(t) or enemy(t)):
                res.append(f"{c},{r}>{t[0]},{t[1]}")
        return res

    def _pawn_strs(self, p, cell, dest):
        c, r = cell
        x, y = dest
        base = f"{c},{r}>{x},{y}"
        if _is_promo(p, x, y):
            return [base + "=" + ch for ch in PROMO_CHOICES]
        return [base]

    def legal_moves(self, s):
        if s.over:
            return []
        p = s.to_move
        allowed = set()
        for d in s.dice:
            if d == "*":
                allowed |= {"K", "R", "N", "S", "P"}
            else:
                allowed |= DIE_PIECES.get(d, set())
        out = []
        for cell, (owner, pt) in s.board.items():
            if owner != p or pt not in allowed:
                continue
            out.extend(self._piece_moves(s.board, p, cell, pt))
        # A dice-turn may always be declined (forfeit the roll); a diceless turn
        # only passes when the player is stuck.
        if s.use_dice or not out:
            out.append("pass")
        seen = set()
        res = []
        for m in out:
            if m not in seen:
                seen.add(m)
                res.append(m)
        return res

    # ------------------------------------------------------------ transition
    def _boat_triumph(self, board, to):
        """Cells (besides `to`) captured when `to` completes a 2x2 of four Boats."""
        c, r = to
        removed = set()
        for bc in (c - 1, c):
            for br in (r - 1, r):
                cells = [(bc, br), (bc + 1, br), (bc, br + 1), (bc + 1, br + 1)]
                if all(_on(cl) for cl in cells) and all(
                        board.get(cl) is not None and board[cl][1] == "S" for cl in cells):
                    for cl in cells:
                        if cl != to:
                            removed.add(cl)
        return removed

    def apply_move(self, s, move, rng=None):
        rng = rng or random.Random()
        board = dict(s.board)
        points = list(s.points)
        kings_by = list(s.kings_by)
        king_alive = list(s.king_alive)
        p = s.to_move
        dice = list(s.dice)
        ply = s.ply + 1
        captured = False
        last = s.last

        if move == "pass":
            dice = []
        else:
            core, promo = (move.split("=") + [None])[:2]
            frm, to = (_cell(x) for x in core.split(">"))
            owner, pt = board[frm]
            if to in board:                                   # ordinary capture
                vo, vp = board[to]
                points[p] += VALUES[vp]
                points[vo] -= VALUES[vp]
                if vp == "K":
                    king_alive[vo] = False
                    kings_by[p] += 1
                captured = True
                del board[to]
            del board[frm]
            board[to] = (p, promo if (promo and pt == "P") else pt)
            if pt == "S":                                     # triumph of the boat
                for cl in self._boat_triumph(board, to):
                    vo, vp = board[cl]
                    if vo != p:
                        points[p] += VALUES[vp]
                        points[vo] -= VALUES[vp]
                    del board[cl]
                    captured = True
            last = core
            if "*" in dice:
                dice.remove("*")
            else:
                dice.remove({"S": 2, "N": 3, "R": 4, "K": 5, "P": 5}[pt])

        no_cap = 0 if captured else s.no_cap + 1

        # ----- end conditions
        over = False
        grand = next((q for q in range(4) if king_alive[q] and kings_by[q] >= 3), None)
        if grand is not None:
            # Swept all three enemy kings with your own king alive: take everything.
            for cl, (vo, vp) in list(board.items()):
                if vo != grand:
                    points[grand] += VALUES[vp]
                    points[vo] -= VALUES[vp]
            over = True
        elif sum(1 for a in king_alive if a) <= 1:            # only one king left
            over = True
        elif no_cap >= NO_CAP_LIMIT or ply >= PLY_CAP:
            over = True

        to_move = p
        if not over and not dice:
            to_move = (p + 1) % 4
            dice = self._roll(rng, s.use_dice)

        return CState(board=board, dice=dice, to_move=to_move, points=points,
                      kings_by=kings_by, king_alive=king_alive, no_cap=no_cap,
                      ply=ply, over=over, use_dice=s.use_dice, last=last)

    def is_terminal(self, s):
        return s.over

    def returns(self, s):
        pts = s.points
        scale = max(1.0, max(abs(x) for x in pts))
        return [x / scale for x in pts]

    def heuristic(self, s):
        return [math.tanh(x / 8.0) for x in s.points]

    # -------------------------------------------------------------- ser/de
    def serialize(self, s):
        return {
            "board": {f"{c},{r}": [o, pt] for (c, r), (o, pt) in s.board.items()},
            "dice": list(s.dice),
            "to_move": s.to_move,
            "points": list(s.points),
            "kings_by": list(s.kings_by),
            "king_alive": list(s.king_alive),
            "no_cap": s.no_cap,
            "ply": s.ply,
            "over": s.over,
            "use_dice": s.use_dice,
            "last": s.last,
        }

    def deserialize(self, d):
        return CState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            dice=list(d["dice"]),
            to_move=d["to_move"],
            points=list(d["points"]),
            kings_by=list(d["kings_by"]),
            king_alive=list(d["king_alive"]),
            no_cap=d.get("no_cap", 0),
            ply=d.get("ply", 0),
            over=d.get("over", False),
            use_dice=d.get("use_dice", True),
            last=d.get("last"),
        )

    # ---------------------------------------------------------------- render
    def describe_move(self, s, move):
        if move == "pass":
            return "pass"
        core, promo = (move.split("=") + [None])[:2]
        frm, to = core.split(">")
        piece = s.board.get(_cell(frm), (None, "?"))[1]
        cap = "x" if _cell(to) in s.board else "-"
        txt = f"{piece} {frm}{cap}{to}"
        if promo:
            txt += "=" + promo
        return txt

    def render(self, s, perspective=None):
        pieces = []
        for (c, r), (owner, pt) in s.board.items():
            pc = {"cell": f"{c},{r}", "owner": owner, "label": pt}
            if pt == "S":
                pc["icon"] = "alfil"          # Boat moves as an Alfil (2-diagonal leaper)
            pieces.append(pc)

        highlights = []
        if s.last:
            for part in s.last.split(">"):
                highlights.append({"cell": part, "kind": "last-move"})

        if s.over:
            order = sorted(range(4), key=lambda i: -s.points[i])
            best = s.points[order[0]]
            winners = [i for i in range(4) if s.points[i] == best]
            score_str = ", ".join(f"{COLOR_NAMES[i]} {s.points[i]}" for i in order)
            if len(winners) == 4 and best == 0:
                cap = "Game over — draw. " + score_str
            elif len(winners) > 1:
                cap = ("Game over — tie: " +
                       "/".join(COLOR_NAMES[i] for i in winners) + ". " + score_str)
            else:
                cap = f"Game over — {COLOR_NAMES[winners[0]]} wins. {score_str}"
        else:
            if s.use_dice:
                desc = "rolled " + ", ".join(DIE_LABEL[d] for d in s.dice)
            else:
                desc = "free move"
            king = "" if s.king_alive[s.to_move] else " (king lost)"
            cap = f"{COLOR_NAMES[s.to_move]} to move{king} — {desc}"

        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
            "pieceset": "chess",
            "choiceNames": {"R": "Rook", "N": "Knight", "S": "Boat"},
        }
