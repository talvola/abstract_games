"""heXentafl -- a hexagonal Hnefatafl by Kevin R. Kane (2020).

Implemented from the nestorgames rule sheet
(nestorgames.com/rulebooks/HEXENTAFL_EN.pdf, "Game design and rules by Kevin R.
Kane"), cross-checked against the designer's own pages (nxsgame.com/hexentafl.html
and the 2019 announcement post nxsgame.wordpress.com/2019/09/26/hexentafl/).
The 2019 blog post is 4x4 only and merely speculates that the game "should scale
up ... although at that scale, the king might need to be allowed to move more
than one space at a time"; the 5x5 board with the rook-moving King is a 2020
nestorgames addition.  See ``rules.md`` for the interpretation log.

Board model
-----------
A hexhex of side ``size`` (4 or 5): axial cells ``(q, r)`` with
``|q|, |r|, |q + r| <= size - 1`` -- 37 cells for the 4x4 grid, 61 for the 5x5.
``THRONE`` is the centre ``(0, 0)`` and the six ``CORNERS`` are ``(size - 1) * d``
for each neighbour direction ``d``.  ``DIRS`` is in clockwise order starting due
N, so ``DIRS[(i + 3) % 6]`` is opposite ``DIRS[i]`` and ``DIRS[(i +- 1) % 6]`` are
the two directions 60 degrees away.  ``render()`` asks for flat-top hexes, which
is what makes index 0 point straight up and puts the six corners at N/NE/SE/S/
SW/NW exactly as the sheet draws them.

Rules as implemented
--------------------
* **Setup (4x4)** -- King on the throne; three defenders on the throne's N, SE
  and SW neighbours (every *other* neighbour, each on the line to a corner --
  this is the sheet's HOW TO PLAY figure and it is the one asymmetry in the
  starting position); six attackers on the six corners.
* **Setup (5x5)** -- King on the throne; six defenders on *all six* neighbours;
  twelve attackers on the six corners of the board and the six corners of the
  inner 4x4 hexagon (i.e. at distance ``size - 1`` and ``size - 2`` along each
  of the six directions).
* **Moving** -- every piece except the 4x4 King slides like a rook along the
  three hex lines, any distance, no jumping.  On the 4x4 board the King moves
  exactly one space; on the 5x5 board he slides like everybody else.
* **The throne** -- only the King may *stop* on the centre; a man may slide over
  it while it is empty, and the King may return to it.  The empty throne is NOT
  hostile (the sheet gives it no capturing role).
* **Capture** -- captures are *active*: only the piece that just moved triggers
  them, so a man that moves in between two enemies is safe.  Three clauses:
  1. an enemy **man on an ordinary cell** is taken when it is sandwiched between
     the moved piece and a friendly piece on the **opposite** side;
  2. an enemy **man on a corner** -- a corner has no opposite pair on the board
     at all -- is taken when the two **rim** neighbours flanking it (the two of
     its three on-board neighbours that are 120 degrees apart) are both enemies
     of it, one of them being the piece that just moved;
  3. the **King on the throne** is taken only when three attackers stand on
     three mutually **non-adjacent** sides of the throne, the arrangement in the
     sheet's "The Throne" figure.
  The King off the throne is an ordinary target for clause 1, and any friendly
  piece -- the King included -- may serve as the far side of a sandwich.
* **Winning** -- the defenders win the moment the King stands on any of the six
  corners; the attackers win by capturing him.
* **Stuck** -- a side with no legal move LOSES (not in the sheet; see rules.md).
* **Draws** -- a position (board + side to move) occurring for the third time is
  a draw, and ``ply_cap(size)`` plies is a hard backstop.  A decisive result
  always outranks both counters.

Pieces: ``"A"`` attacker, ``"D"`` defender man, ``"K"`` King.  Seat 0 is the
DEFENDERS, who move first; seat 1 is the ATTACKERS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# ---------------------------------------------------------------- geometry ---

# Axial neighbour offsets in CLOCKWISE order.  With the flat-top orientation
# render() asks for, index 0 is due N, so the cycle reads N, NE, SE, S, SW, NW.
DIRS = ((0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0))

SIZES = (4, 5)
THRONE = (0, 0)

DEFENDERS, ATTACKERS = 0, 1
# Pinned by the sheet's setup figure: the side whose King sits on the central
# throne is the side that must ESCORT him out, i.e. the defenders.
SEAT_NAMES = ("Defenders", "Attackers")

# A position (board + side to move) reaching this many occurrences is a draw.
REPS_DRAW = 3


def on_board(cell, size: int) -> bool:
    q, r = cell
    R = size - 1
    return abs(q) <= R and abs(r) <= R and abs(q + r) <= R


def all_cells(size: int) -> list:
    R = size - 1
    return [(q, r) for q in range(-R, R + 1) for r in range(-R, R + 1)
            if abs(q + r) <= R]


def corners(size: int) -> frozenset:
    R = size - 1
    return frozenset((R * dq, R * dr) for dq, dr in DIRS)


CORNERS = {n: corners(n) for n in SIZES}
CELLS = {n: all_cells(n) for n in SIZES}


def start_board(size: int) -> dict:
    """The starting position, transcribed from the rule sheet's two figures."""
    R = size - 1
    b = {THRONE: "K"}
    if size == 4:
        # HOW TO PLAY figure: defenders on every OTHER neighbour of the throne
        # -- N, SE and SW -- so each one stands on the line to a corner.  This
        # triple is the starting position's only asymmetry.
        for i in (0, 2, 4):
            b[DIRS[i]] = "D"
        for dq, dr in DIRS:
            b[(R * dq, R * dr)] = "A"
    else:
        # 5x5 figure: defenders on all six neighbours; attackers on the six
        # corners of the board AND the six corners of the inner hexagon.
        for dq, dr in DIRS:
            b[(dq, dr)] = "D"
            b[(R * dq, R * dr)] = "A"
            b[((R - 1) * dq, (R - 1) * dr)] = "A"
    return b


def owner(piece: str) -> int:
    return ATTACKERS if piece == "A" else DEFENDERS


# ------------------------------------------------------------- termination ---

def max_men(size: int) -> int:
    """Men (King excluded) on the board at the start = the number of captures a
    game can contain without ending it."""
    b = start_board(size)
    return sum(1 for p in b.values() if p != "K")


# Threefold repetition already guarantees termination (the state space is
# finite, so unbounded play must repeat some position three times), which makes
# the ply cap a pure backstop against a bookkeeping bug rather than a rule.  It
# is still derived rather than pinned: every capture is irreversible, so a game
# splits into at most ``max_men(size) + 1`` capture-free epochs, and we allow
# each epoch ``EPOCH_PLIES`` plies -- itself derived from the board, two full
# plies for every (cell, mover) pair, which is far more shuffling than the
# repetition rule can actually sustain.  selftest.py asserts no game ever
# reaches it, i.e. that the cap is NOT outcome-load-bearing.
def epoch_plies(size: int) -> int:
    return 2 * 2 * len(CELLS[size])


def ply_cap(size: int) -> int:
    return (max_men(size) + 1) * epoch_plies(size)


# ------------------------------------------------------------------ state ---

@dataclass
class HexTaflState:
    board: dict = field(default_factory=dict)      # (q, r) -> "A" | "D" | "K"
    to_move: int = DEFENDERS
    winner: Optional[int] = None
    ply: int = 0
    size: int = 4
    reps: dict = field(default_factory=dict)       # position key -> occurrences


def cid(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def pos_key(board: dict, to_move: int) -> str:
    return f"{to_move}|" + ";".join(sorted(f"{q},{r}{p}" for (q, r), p in board.items()))


# ------------------------------------------------------------------- game ---

class Hexentafl(Game):
    name = "heXentafl"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> HexTaflState:
        options = options or {}
        size = int(options.get("size", 4))
        if size not in SIZES:
            raise ValueError(f"size must be one of {SIZES}")
        first = str(options.get("first_player", "defenders")).lower()
        to_move = ATTACKERS if first.startswith("a") else DEFENDERS
        board = start_board(size)
        return HexTaflState(board=board, to_move=to_move, size=size,
                            reps={pos_key(board, to_move): 1})

    def current_player(self, s: HexTaflState) -> int:
        return s.to_move

    # -- movement ----------------------------------------------------------

    def _moves(self, s: HexTaflState) -> list:
        out = []
        size = s.size
        for cell, piece in s.board.items():
            if owner(piece) != s.to_move:
                continue
            king = piece == "K"
            one_step = king and size == 4       # the 4x4 King steps, 5x5 slides
            for dq, dr in DIRS:
                q, r = cell
                while True:
                    q += dq
                    r += dr
                    if not on_board((q, r), size) or (q, r) in s.board:
                        break
                    # only the King may STOP on the throne; a man slides over it
                    if king or (q, r) != THRONE:
                        out.append((cell, (q, r)))
                    if one_step:
                        break
        return out

    def legal_moves(self, s: HexTaflState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [f"{cid(a)}>{cid(b)}" for a, b in self._moves(s)]

    # -- capture -----------------------------------------------------------

    @staticmethod
    def _friend(board: dict, cell, player: int) -> bool:
        """Does `cell` act as the far side of `player`'s sandwich?  Only an
        actual friendly piece does: heXentafl has no hostile squares -- neither
        the empty throne nor a corner assists a capture."""
        occ = board.get(cell)
        return occ is not None and owner(occ) == player

    def captures(self, board: dict, to, player: int, size: int) -> list:
        """Pieces captured by `player` having just moved a piece onto `to`.

        `board` must already contain the moved piece at `to`."""
        caps = []
        corner_cells = CORNERS[size]
        for i, (dq, dr) in enumerate(DIRS):
            nxt = (to[0] + dq, to[1] + dr)
            if not on_board(nxt, size):
                continue
            victim = board.get(nxt)
            if victim is None or owner(victim) == player:
                continue
            if victim == "K" and nxt == THRONE:
                # Clause 3 -- three attackers on three mutually NON-ADJACENT
                # sides.  The mover stands on one of them (direction i + 3 seen
                # from the throne); the other two are i - 1 and i + 1, which are
                # exactly the two sides 120 degrees from the mover's.
                flanks = [(nxt[0] + DIRS[j][0], nxt[1] + DIRS[j][1])
                          for j in ((i - 1) % 6, (i + 1) % 6)]
                if all(self._friend(board, f, player) for f in flanks):
                    caps.append(nxt)
            elif victim != "K" and nxt in corner_cells:
                # Clause 2 -- a man on a corner is taken by the two rim
                # neighbours flanking it.  At most one of the two candidates is
                # ever on the board -- one for each of the two RIM approaches,
                # none for the INWARD one, which therefore never captures
                # (selftest.py's corner lemma proves exactly this split), so
                # this cannot double-count.
                for j in ((i - 1) % 6, (i + 1) % 6):
                    f = (nxt[0] + DIRS[j][0], nxt[1] + DIRS[j][1])
                    if on_board(f, size) and self._friend(board, f, player):
                        caps.append(nxt)
                        break
            else:
                # Clause 1 -- ordinary custodial sandwich on OPPOSITE sides.
                beyond = (to[0] + 2 * dq, to[1] + 2 * dr)
                if on_board(beyond, size) and self._friend(board, beyond, player):
                    caps.append(nxt)
        return caps

    # -- play --------------------------------------------------------------

    def apply_move(self, s: HexTaflState, move: str, rng=None) -> HexTaflState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        piece = board.pop(frm)
        board[to] = piece
        player = s.to_move
        for c in self.captures(board, to, player, s.size):
            del board[c]

        winner = None
        if "K" not in board.values():
            winner = ATTACKERS                      # the King has been taken
        elif piece == "K" and to in CORNERS[s.size]:
            winner = DEFENDERS                      # the King has escaped
        # (the two are mutually exclusive: captures are active, so only the
        # attackers can take the King and only the defenders can move him)

        nxt = 1 - player
        reps = dict(s.reps)
        key = pos_key(board, nxt)
        reps[key] = reps.get(key, 0) + 1
        return HexTaflState(board=board, to_move=nxt, winner=winner,
                            ply=s.ply + 1, size=s.size, reps=reps)

    # -- terminal ----------------------------------------------------------

    def is_terminal(self, s: HexTaflState) -> bool:
        if s.winner is not None:
            return True
        if not self._moves(s):
            return True                             # stuck side loses
        return (s.reps.get(pos_key(s.board, s.to_move), 0) >= REPS_DRAW
                or s.ply >= ply_cap(s.size))

    def returns(self, s: HexTaflState) -> list[float]:
        # A DECISIVE result outranks the draw counters: both the escape/capture
        # win and the stuck-side loss are read BEFORE repetition and the ply
        # cap, so a win delivered on the capping ply (or in a thrice-repeated
        # position) still scores as a win.
        if s.winner is not None:
            w = s.winner
        elif not self._moves(s):
            w = 1 - s.to_move
        else:
            return [0.0, 0.0]                       # repetition / cap -> draw
        out = [-1.0, -1.0]
        out[w] = 1.0
        return out

    # -- serialisation -----------------------------------------------------

    def serialize(self, s: HexTaflState) -> dict:
        return {
            "board": {cid(c): p for c, p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "ply": s.ply,
            "size": s.size,
            "reps": dict(s.reps),
        }

    def deserialize(self, d: dict) -> HexTaflState:
        return HexTaflState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d.get("winner"),
            ply=d.get("ply", 0),
            size=d.get("size", 4),
            reps=dict(d.get("reps", {})),
        )

    # -- presentation ------------------------------------------------------

    def describe_move(self, s: HexTaflState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        piece = s.board.get(frm, "?")
        board = dict(s.board)
        board.pop(frm, None)
        board[to] = piece
        n = len(self.captures(board, to, s.to_move, s.size))
        tag = {"K": "King ", "A": "", "D": ""}.get(piece, "?")
        return f"{tag}{cid(frm)}>{cid(to)}" + (f" x{n}" if n else "")

    def render(self, s: HexTaflState, perspective=None) -> dict:
        pieces = [{"cell": cid(c), "owner": owner(p), "label": "",
                   "glyph": "♚" if p == "K" else None}
                  for c, p in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = ("Draw" if ret[0] == ret[1]
                       else f"{SEAT_NAMES[0 if ret[0] > ret[1] else 1]} win")
        else:
            caption = f"{SEAT_NAMES[s.to_move]} to move"
        return {
            "board": {
                "type": "hex",
                "shape": "hexagon",
                "size": s.size,
                "orientation": "flat",
                "tints": {cid(THRONE): "#f3d6d6"},
            },
            "pieces": pieces,
            "highlights": [{"cell": cid(c), "kind": "goal"} for c in sorted(CORNERS[s.size])],
            "caption": caption,
        }
