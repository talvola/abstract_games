"""TZAAR, by Kris Burm (2007) -- the fourth game of Project GIPF.

A stacking capture game played on a **hexagonal board of hexagons** of side 5
(a "hexhex" with N=5): 61 cells, of which the single CENTRE cell is empty at the
start, leaving 60 cells each holding one piece. Coordinates are axial ``q,r``
(cube s = -q-r); a cell is on-board iff max(|q|,|r|,|s|) <= 4. There are 6 hex
directions; a piece/stack SLIDES in a straight line over any number of VACANT
cells and stops at the FIRST occupied cell (it may NEVER jump over a piece, and
never lands on an empty cell). Both actions use this slide: a capture lands on
the first occupied cell if it is a capturable enemy; a stack-combine lands on the
first occupied cell if it is friendly.

Each player owns three TYPES of piece of differing importance:
  * **Tzaar**  (6 per player) -- most important
  * **Tzarra** (9 per player)
  * **Tott**   (15 per player) -- least important
A stack's type is the type of its TOP piece; a single piece is a stack of
height 1. We track (owner, type, height) per cell; this game reuses Lasca's
tower glyph (``piece.stack``) but ALSO carries the type as a label.

A TURN is TWO actions:
  1. **Capture** (MANDATORY): pick a stack you control (your colour on top) and
     slide it in a straight line over vacant cells to the FIRST occupied cell; if
     that cell holds an ENEMY stack whose height is <= your stack's height, the
     enemy stack is removed ENTIRELY and replaced by your stack (capture by
     replacement). Your height is UNCHANGED; you do not bank enemy pieces.
  2. **Second action** (OPTIONAL): EITHER another capture (same rule), OR a
     **stack move** -- slide a stack you control onto a FRIENDLY stack (the first
     occupied cell in some direction), combining them: your moved stack goes on
     TOP, the combined height is the sum, and the type becomes your top piece's
     type.

Loss: a player LOSES at the START of their turn if they have ZERO stacks of any
one of the three types (all of Tzaar / Tzarra / Tott must survive), or if they
cannot make a capture.

First-move rule (the standard TZAAR convention, implemented here): the very
first action of the game is a single CAPTURE only -- the opening player does NOT
get a second action on the first turn. From the second turn on, every turn is
the full two-action turn (capture, then optional capture-or-stack).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

N = 5                       # hexhex side length (cells with max(|q|,|r|,|s|) <= N-1)
WHITE, BLACK = 0, 1

# Piece types, by importance (used only for the survival-loss check & display).
TOTT, TZARRA, TZAAR = 0, 1, 2
TYPE_LETTER = {TOTT: "o", TZARRA: "a", TZAAR: "z"}   # tott / tzarra / tzaar
LETTER_TYPE = {v: k for k, v in TYPE_LETTER.items()}
TYPE_NAME = {TOTT: "Tott", TZARRA: "Tzarra", TZAAR: "Tzaar"}
TYPE_COUNT = {TZAAR: 6, TZARRA: 9, TOTT: 15}         # per player

PLY_CAP = 600               # defensive draw cap (captures strictly reduce pieces)


# The 6 hex (axial) directions a piece can slide along.
_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


def _neighbors(q: int, r: int):
    return [(q + dq, r + dr) for (dq, dr) in _DIRS]


def _slide_targets(board, cells, q, r):
    """The first OCCUPIED cell reached by sliding from (q,r) along each of the 6
    hex directions over vacant cells. Yields the occupied destination cells; a
    direction that runs off the board with no occupied cell yields nothing."""
    for (dq, dr) in _DIRS:
        nq, nr = q + dq, r + dr
        while (nq, nr) in cells:
            if board.get((nq, nr)) is not None:
                yield (nq, nr)
                break
            nq, nr = nq + dq, nr + dr


def _slide_path_clear(board, cells, frm, to):
    """True iff (to) is reachable from (frm) by sliding in a straight hex line:
    (to) is collinear with (frm) along one of the 6 directions, every cell
    strictly between them is on-board and EMPTY, and (to) is on-board. Does not
    check what occupies (to)."""
    if to not in cells:
        return False
    for (dq, dr) in _DIRS:
        nq, nr = frm[0] + dq, frm[1] + dr
        while (nq, nr) in cells:
            if (nq, nr) == to:
                return True                       # reached target with clear path
            if board.get((nq, nr)) is not None:
                break                             # blocked before the target
            nq, nr = nq + dq, nr + dr
    return False


@lru_cache(maxsize=None)
def _cells(size: int) -> tuple:
    """All on-board axial cells of a hexhex of side ``size``."""
    out = []
    n = size - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            s = -q - r
            if abs(q) <= n and abs(r) <= n and abs(s) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(size: int) -> frozenset:
    return frozenset(_cells(size))


def _cell(s: str) -> tuple:
    q, r = s.split(",")
    return int(q), int(r)


# A stack is (owner, type, height).
def _owner(stk):
    return stk[0]


def _type(stk):
    return stk[1]


def _height(stk):
    return stk[2]


@dataclass
class TState:
    board: dict = field(default_factory=dict)   # (q,r) -> (owner, type, height)
    to_move: int = WHITE
    phase: int = 0          # 0 = must capture; 1 = optional 2nd action (cap or stack)
    ply: int = 0            # total actions taken (for the first-move rule & cap)
    winner: object = None


# --------------------------------------------------------------------------- #
#  Canonical fixed starting layout                                            #
# --------------------------------------------------------------------------- #
#
# The physical game randomises placement; we use a DETERMINISTIC canonical
# layout so the game has no chance node and is reproducible. The recipe:
#   * Order the 60 non-centre cells in a fixed reading order (sorted by (q, r)).
#   * Build a fixed multiset of 60 pieces interleaving the two colours and the
#     three types so neither colour nor type is clustered: for piece index i,
#     owner = i % 2, and the type is drawn from a fixed round-robin pattern that
#     yields exactly 6 Tzaar / 9 Tzarra / 15 Totts per colour.
#   * Deal piece i onto cell i.
# The pattern below is hand-built (not random) and asserted by selftest.

@lru_cache(maxsize=None)
def _layout(size: int) -> dict:
    cells = sorted(c for c in _cells(size) if c != (0, 0))   # 60 cells, fixed order
    # Per-colour type sequence: 30 pieces = 6 z, 9 a, 15 o, interleaved as a
    # repeating "o a o" with periodic "z" insertions so they spread out.
    # Build by a fixed deterministic schedule rather than relying on luck.
    seq = _type_sequence()            # length 30, exactly 6 z / 9 a / 15 o
    board = {}
    # Deal alternating colours; each colour walks its own copy of `seq`.
    idx = {WHITE: 0, BLACK: 0}
    for i, cell in enumerate(cells):
        owner = i % 2
        t = seq[idx[owner]]
        idx[owner] += 1
        board[cell] = (owner, t, 1)
    return board


@lru_cache(maxsize=None)
def _type_sequence() -> tuple:
    """A fixed length-30 type sequence with exactly 6 TZAAR, 9 TZARRA, 15 TOTT,
    spread out (no long runs of one type) by a deterministic even spread.

    Slots 0..29. TZAAR occupies the 6 slots that fall on an even 6-way split of
    30; among the remaining 24 slots, TZARRA occupies an even 9-way split; the
    rest (15) are TOTT. Fully deterministic -- no RNG."""
    tzaar_slots = sorted({(k * 30) // 6 for k in range(6)})        # 6 slots
    non = [i for i in range(30) if i not in tzaar_slots]           # 24 slots
    tzarra_slots = sorted({non[(k * len(non)) // 9] for k in range(9)})
    seq = []
    for i in range(30):
        if i in tzaar_slots:
            seq.append(TZAAR)
        elif i in tzarra_slots:
            seq.append(TZARRA)
        else:
            seq.append(TOTT)
    assert seq.count(TZAAR) == 6 and seq.count(TZARRA) == 9 and seq.count(TOTT) == 15, (
        seq.count(TZAAR), seq.count(TZARRA), seq.count(TOTT))
    return tuple(seq)


class Tzaar(Game):
    uid = "tzaar"
    name = "TZAAR"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> TState:
        return TState(board=dict(_layout(N)), to_move=WHITE, phase=0, ply=0)

    def current_player(self, s: TState) -> int:
        return s.to_move

    # ---- helpers ----------------------------------------------------------- #
    def _captures(self, board, player):
        """All capture moves 'from>to' for ``player``: SLIDE in a straight line
        over vacant cells to the first occupied cell; capture if it is an enemy
        stack of height <= yours (no jumping over intervening pieces)."""
        out = []
        cells = _cell_set(N)
        for (q, r), stk in board.items():
            if _owner(stk) != player:
                continue
            h = _height(stk)
            for (nq, nr) in _slide_targets(board, cells, q, r):
                nbr = board[(nq, nr)]
                if _owner(nbr) != player and _height(nbr) <= h:
                    out.append(f"{q},{r}>{nq},{nr}")
        return out

    def _stack_moves(self, board, player):
        """All stacking moves 'from>to' for ``player``: SLIDE in a straight line
        over vacant cells to the first occupied cell; combine if it is a FRIENDLY
        stack (no jumping over intervening pieces)."""
        out = []
        cells = _cell_set(N)
        for (q, r), stk in board.items():
            if _owner(stk) != player:
                continue
            for (nq, nr) in _slide_targets(board, cells, q, r):
                nbr = board[(nq, nr)]
                if _owner(nbr) == player:
                    out.append(f"{q},{r}>{nq},{nr}")
        return out

    def _has_all_types(self, board, player):
        present = {_type(stk) for stk in board.values() if _owner(stk) == player}
        return present >= {TOTT, TZARRA, TZAAR}

    # ---- turn / loss bookkeeping ------------------------------------------ #
    def _check_loss_at_turn_start(self, s: TState):
        """At the start of ``to_move``'s turn (phase 0): they lose if missing a
        type or unable to capture. Returns the winner (the OTHER player) or None."""
        p = s.to_move
        if not self._has_all_types(s.board, p):
            return 1 - p
        if not self._captures(s.board, p):
            return 1 - p
        return None

    def legal_moves(self, s: TState):
        if s.winner is not None or s.ply >= PLY_CAP:
            return []
        if s.phase == 0:
            # A real start-of-turn loss is already resolved in _end_turn (winner
            # set -> caught by the guard above). The capture list being empty is
            # itself the "cannot capture" loss; we still return [] so the
            # non-terminal-must-have-moves invariant is only ever violated on a
            # genuinely terminal (winner-set) state.
            return self._captures(s.board, s.to_move)
        # phase 1: optional second action -> capture OR stack OR pass.
        moves = self._captures(s.board, s.to_move) + self._stack_moves(s.board, s.to_move)
        moves.append("pass")
        return moves

    # ---- apply ------------------------------------------------------------- #
    def apply_move(self, s: TState, move: str, rng=None) -> TState:
        board = dict(s.board)
        player = s.to_move

        if move == "pass":
            if s.phase != 1:
                raise ValueError("pass only allowed as the optional second action")
            return self._end_turn(board, player, s.ply + 1)

        frm, to = (_cell(x) for x in move.split(">"))
        stk = board.get(frm)
        if stk is None or _owner(stk) != player:
            raise ValueError(f"no controlled stack at {frm}")
        # The destination must be reachable by a straight-line slide over vacant
        # cells (no jumping over a piece) and must itself be occupied.
        if not _slide_path_clear(board, _cell_set(N), frm, to):
            raise ValueError("move must slide in a straight line over empty cells")
        target = board.get(to)
        if target is None:
            raise ValueError("a slide must end on the first occupied cell")

        if s.phase == 0:
            # Must be a capture.
            if target is None or _owner(target) == player or _height(target) > _height(stk):
                raise ValueError("first action must be a legal capture")
            del board[frm]
            board[to] = stk                       # capture by replacement
            # First move of the game: single capture only -> end turn now.
            if s.ply == 0:
                return self._end_turn(board, player, s.ply + 1)
            ns = TState(board=board, to_move=player, phase=1,
                        ply=s.ply + 1)
            return ns

        # phase 1: either a capture or a stack move.
        if target is None:
            raise ValueError("second action must land on an occupied cell")
        if _owner(target) == player:
            # stack move: combine, moved stack on top.
            combined = (player, _type(stk), _height(stk) + _height(target))
            del board[frm]
            board[to] = combined
        else:
            # capture
            if _height(target) > _height(stk):
                raise ValueError("capture requires height >= target")
            del board[frm]
            board[to] = stk
        return self._end_turn(board, player, s.ply + 1)

    def _end_turn(self, board, player, ply):
        """Hand the turn to the opponent and resolve their start-of-turn loss."""
        opp = 1 - player
        ns = TState(board=board, to_move=opp, phase=0, ply=ply)
        w = self._check_loss_at_turn_start(ns)
        if w is not None:
            ns.winner = w
        return ns

    # ---- terminal ---------------------------------------------------------- #
    def is_terminal(self, s: TState) -> bool:
        return s.winner is not None or s.ply >= PLY_CAP

    def returns(self, s: TState):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # ---- serialise --------------------------------------------------------- #
    def _stk_str(self, stk):
        o, t, h = stk
        return f"{o}{TYPE_LETTER[t]}{h}"

    def _parse_stk(self, s):
        o = int(s[0]); t = LETTER_TYPE[s[1]]; h = int(s[2:])
        return (o, t, h)

    def serialize(self, s: TState) -> dict:
        return {
            "board": {f"{q},{r}": self._stk_str(stk) for (q, r), stk in s.board.items()},
            "to_move": s.to_move,
            "phase": s.phase,
            "ply": s.ply,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> TState:
        return TState(
            board={_cell(k): self._parse_stk(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            phase=d.get("phase", 0),
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # ---- presentation ------------------------------------------------------ #
    def describe_move(self, s: TState, move: str) -> str:
        if move == "pass":
            return "pass (no 2nd action)"
        frm, to = move.split(">")
        fq, fr = _cell(frm)
        tq, tr = _cell(to)
        src = s.board.get((fq, fr))
        tgt = s.board.get((tq, tr))
        if tgt is not None and src is not None and _owner(tgt) == _owner(src):
            return f"{frm}+{to}"          # stack (combine)
        return f"{frm}x{to}"              # capture

    def render(self, s: TState, perspective=None) -> dict:
        names = {WHITE: "White", BLACK: "Black"}
        pieces = []
        for (q, r), stk in s.board.items():
            o, t, h = stk
            pieces.append({
                "cell": f"{q},{r}",
                "owner": o,
                "stack": [o] * h,                 # Lasca-style tower glyph
                # distinct type glyph (Tzaar/Tzarra/Tott all start with 'T'):
                "label": {TZAAR: "Z", TZARRA: "z", TOTT: "o"}[t] + (str(h) if h > 1 else ""),
            })
        if s.winner is not None:
            cap = f"{names[s.winner]} wins"
        elif s.ply >= PLY_CAP:
            cap = "Draw (ply cap)"
        else:
            if s.phase == 0:
                cap = f"{names[s.to_move]} to move (must capture)"
            else:
                cap = f"{names[s.to_move]}: 2nd action (capture, stack, or pass)"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": N},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
