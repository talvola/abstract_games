"""Accasta — Dieter Stein, 1998 (Bambus Spieleverlag "tactic blue").

A pure stacking game on a hexhex-4 board (37 points). Each player has 20
pieces — Shields, Horses, and Chariots, which move UP TO 1, 2, or 3 spaces
straight (no jumping; landing on any friendly or enemy stack in reach is
allowed). Both armies start fully stacked inside a 9-space triangular
"castle" (rows a+g: S/H/C towers, b+f: S/H, c+e: single shields — article
Fig. 1). The TOP piece of a stack (the "head") controls it and may carry
("lead") any number of pieces below — a stack splits at any point; buried
enemy pieces are captured but never leave the board (recapturing liberates
them). After a split, if a FRIENDLY piece surfaces at the origin it may
also move this turn (optional, repeatable — all of a turn's sub-moves come
from the one origin stack); uncovering an ENEMY piece ("release") ends the
turn at once. Safe-stack rule: a stacking move is legal only if the
resulting stack holds NO MORE THAN 3 PIECES OF ONE COLOUR — so a stack
with three captured pieces is invulnerable ("safe stack").

WIN: you control >=3 stacks in the enemy castle at the START of your turn
(the threatened player gets one turn to defend); also (7 Mar 2010 update)
you win if your opponent has no legal move on their turn. No passing.

Implemented from the designer's official rules, spielstein.com/games/
accasta/rules (This version: 12 April 1998; Update: 7 March 2010 — new
winning condition), cross-checked against Stein's own article "Accasta —
Introduction to a Pure Stacking Game" (written for the old Abstract Games
#17, published on spielstein.com; its Fig. 1 pins the exact setup, Figs.
3a/3b the move sets, and its complete sample game Stein–Williams 2004 is
replayed move-by-move in selftest.py). NOTE: the article's extra rule
"releasing an enemy piece in one's own castle is illegal" does NOT appear
in the current official rules (the 2010 beginning-of-turn win check
resolves the double-win paradox it addressed) and is not implemented.

VARIANT — Accasta Pari (official, spielstein.com/games/accasta/rules/pari):
same board and setup but a single piece type; a stack's head moves up to
min(3, number of pieces of its own colour in the stack) spaces, evaluated
BEFORE the move ("pieces are promoted or demoted" as they stack/unstack).
All other rules apply, in particular the 3-pieces rule.

MOVE ENCODING: a sub-move is "q1,r1>q2,r2" (single piece) or
"q1,r1>q2,r2=K" (K = number of pieces taken off the top, when the source
stack is taller than 1 — the UI shows a K picker). "done" ends the turn
when an optional continuation is available. Cells are axial "q,r" on the
platform hex board; row a (White's side, r=+3) renders at the bottom.

Draw backstops (house rules — pieces never leave the board, so official
play has no draw rule): threefold repetition of a turn-start position,
or a hard cap on turns/sub-moves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import tanh

from agp.game import Game

WHITE, BLACK = 0, 1
SEAT_NAMES = ("White", "Black")
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))
RANGE = {"S": 1, "H": 2, "C": 3}
TURN_CAP = 400          # completed turns (house backstop)
PLY_CAP = 2200          # total sub-moves (house backstop)

CELLS = tuple((q, r) for q in range(-3, 4) for r in range(-3, 4)
              if abs(q + r) <= 3)
CELL_SET = frozenset(CELLS)


def _alg(cell) -> str:
    """Axial -> article coordinates (rows a..g from White's side)."""
    q, r = cell
    qmin = max(-3, -3 - r)
    return f"{'abcdefg'[3 - r]}{q - qmin + 1}"


def _from_alg(s: str):
    r = 3 - "abcdefg".index(s[0])
    qmin = max(-3, -3 - r)
    return (qmin + int(s[1:]) - 1, r)


def _cid(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _cell(s: str):
    q, r = s.split(",")
    return (int(q), int(r))


# 9-space triangular castles (article Fig. 1: shaded spaces).
CASTLES = (
    frozenset(_from_alg(a) for a in
              "a1 a2 a3 a4 b2 b3 b4 c3 c4".split()),   # White's castle
    frozenset(_from_alg(a) for a in
              "g1 g2 g3 g4 f2 f3 f4 e3 e4".split()),   # Black's castle
)

# Initial towers by row letter (bottom -> top): Chariot on top on the back
# row, Horse on top on the middle row, single Shields in front (Fig. 1).
_SETUP_ROWS = {"a": ("S", "H", "C"), "b": ("S", "H"), "c": ("S",),
               "g": ("S", "H", "C"), "f": ("S", "H"), "e": ("S",)}


# A piece is (owner, kind); a stack is a tuple of pieces, bottom -> top.


@dataclass
class AState:
    variant: str = "accasta"
    board: dict = field(default_factory=dict)   # (q,r) -> stack tuple
    to_move: int = WHITE
    cont: object = None                          # origin cell of an ongoing turn
    last: list = field(default_factory=list)     # cells of the last sub-move
    winner: object = None                        # None | 0 | 1 | "draw"
    ply: int = 0                                 # sub-moves applied
    turn_no: int = 0                             # completed turns
    reps: dict = field(default_factory=dict)     # turn-start position counts


class Accasta(Game):

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        variant = (options or {}).get("variant", "accasta")
        if variant not in ("accasta", "pari"):
            raise ValueError(f"unknown variant {variant!r}")
        board = {}
        for seat, castle in enumerate(CASTLES):
            for cell in castle:
                kinds = _SETUP_ROWS[_alg(cell)[0]]
                if variant == "pari":
                    kinds = ("P",) * len(kinds)
                board[cell] = tuple((seat, k) for k in kinds)
        st = AState(variant=variant, board=board)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _power(self, state, stack):
        """Movement range of the stack's head (= of any led group)."""
        if state.variant == "pari":
            own = stack[-1][0]
            return min(3, sum(1 for (o, _k) in stack if o == own))
        return RANGE[stack[-1][1]]

    @staticmethod
    def _stack_ok(target, group):
        """Safe-stack rule: <=3 pieces of each colour in the merged stack."""
        w = sum(1 for (o, _k) in target if o == WHITE) \
            + sum(1 for (o, _k) in group if o == WHITE)
        return w <= 3 and (len(target) + len(group) - w) <= 3

    @staticmethod
    def _mk(x, y, k, h):
        return f"{_cid(x)}>{_cid(y)}" + ("" if h == 1 else f"={k}")

    def _cell_moves(self, state, x):
        """All sub-moves of the stack on x (head assumed to be the mover's)."""
        stack = state.board[x]
        h = len(stack)
        out = []
        for dq, dr in DIRS:
            for dist in range(1, self._power(state, stack) + 1):
                y = (x[0] + dq * dist, x[1] + dr * dist)
                if y not in CELL_SET:
                    break
                target = state.board.get(y)
                if target is None:
                    out.extend(self._mk(x, y, k, h) for k in range(1, h + 1))
                else:                            # land on it (if legal), no jumping past
                    out.extend(self._mk(x, y, k, h) for k in range(1, h + 1)
                               if self._stack_ok(target, stack[h - k:]))
                    break
        return out

    def legal_moves(self, state):
        if state.winner is not None:
            return []
        if state.cont is not None:
            return self._cell_moves(state, state.cont) + ["done"]
        out = []
        for cell, stack in state.board.items():
            if stack[-1][0] == state.to_move:
                out.extend(self._cell_moves(state, cell))
        return out

    def _has_move(self, state):
        return any(stack[-1][0] == state.to_move
                   and self._cell_moves(state, cell)
                   for cell, stack in state.board.items())

    # ---- transition --------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        if state.winner is not None:
            raise ValueError("game over")
        if move not in self.legal_moves(state):
            raise ValueError(f"illegal move {move!r}")
        mover = state.to_move

        if move == "done":
            return self._end_turn(state, dict(state.board), list(state.last),
                                  state.ply)

        frm_s, _, rest_s = move.partition(">")
        to_s, _, k_s = rest_s.partition("=")
        x, y = _cell(frm_s), _cell(to_s)
        k = int(k_s) if k_s else 1

        board = dict(state.board)
        stack = board.pop(x)
        group = stack[-k:]
        remainder = stack[:-k]
        if remainder:
            board[x] = remainder
        board[y] = board.get(y, ()) + group
        last = [_cid(x), _cid(y)]

        if remainder and remainder[-1][0] == mover:
            # A friendly piece surfaced: optional continuation from x.
            return AState(variant=state.variant, board=board, to_move=mover,
                          cont=x, last=last, ply=state.ply + 1,
                          turn_no=state.turn_no, reps=dict(state.reps))
        # Origin emptied, or an enemy piece was released: the turn is over.
        return self._end_turn(state, board, last, state.ply + 1)

    def _castle_count(self, board, player):
        """Stacks controlled by `player` inside the ENEMY castle."""
        return sum(1 for cell in CASTLES[1 - player]
                   if cell in board and board[cell][-1][0] == player)

    def _end_turn(self, state, board, last, ply):
        nxt = 1 - state.to_move
        ns = AState(variant=state.variant, board=board, to_move=nxt,
                    cont=None, last=last, winner=None, ply=ply,
                    turn_no=state.turn_no + 1, reps=dict(state.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        # Official rules, checked at the beginning of the incoming turn:
        if self._castle_count(board, nxt) >= 3:
            ns.winner = nxt                       # castle occupation
        elif not self._has_move(ns):
            ns.winner = state.to_move             # opponent cannot move (2010)
        elif (ns.reps[key] >= 3 or ns.turn_no >= TURN_CAP
              or ns.ply >= PLY_CAP):
            ns.winner = "draw"                    # house backstop
        return ns

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        return state.winner is not None

    def returns(self, state):
        if state.winner == "draw" or state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    def heuristic(self, state):
        cw = self._castle_count(state.board, WHITE)
        cb = self._castle_count(state.board, BLACK)
        ctrl = [0, 0]
        for stack in state.board.values():
            ctrl[stack[-1][0]] += len(stack)
        v = tanh(1.1 * (cw - cb) / 3.0 + 0.4 * (ctrl[0] - ctrl[1]) / 40.0)
        return [v, -v]

    # ---- serialization -----------------------------------------------------
    @staticmethod
    def _stack_str(stack):
        return "".join(k if o == WHITE else k.lower() for (o, k) in stack)

    @staticmethod
    def _parse_stack(s):
        return tuple((WHITE if ch.isupper() else BLACK, ch.upper())
                     for ch in s)

    def _key(self, state):
        b = "|".join(f"{_cid(c)}:{self._stack_str(state.board[c])}"
                     for c in sorted(state.board))
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        return {
            "variant": state.variant,
            "board": {_cid(c): self._stack_str(s)
                      for c, s in state.board.items()},
            "to_move": state.to_move,
            "cont": None if state.cont is None else _cid(state.cont),
            "last": list(state.last),
            "winner": state.winner,
            "ply": state.ply,
            "turn_no": state.turn_no,
            "reps": dict(state.reps),
        }

    def deserialize(self, data):
        return AState(
            variant=data.get("variant", "accasta"),
            board={_cell(k): self._parse_stack(v)
                   for k, v in data["board"].items()},
            to_move=data["to_move"],
            cont=None if data.get("cont") is None else _cell(data["cont"]),
            last=list(data.get("last", [])),
            winner=data.get("winner"),
            ply=data.get("ply", 0),
            turn_no=data.get("turn_no", 0),
            reps=dict(data.get("reps", {})),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if move == "done":
            return "end turn"
        frm_s, _, rest_s = move.partition(">")
        to_s, _, k_s = rest_s.partition("=")
        x, y = _cell(frm_s), _cell(to_s)
        k = int(k_s) if k_s else 1
        mover = state.to_move
        target = state.board.get(y)
        sym = "-" if target is None else ("+" if target[-1][0] == mover
                                          else "x")
        if state.variant == "pari":
            body = str(k)
        else:
            body = "".join(kind if o == mover else kind.lower()
                           for (o, kind) in reversed(state.board[x][-k:]))
        return f"{_alg(x)}:{body}{sym}{_alg(y)}"

    def render(self, state, perspective=None):
        tints = {}
        for cell in CASTLES[WHITE]:
            tints[_cid(cell)] = "#3b3322"
        for cell in CASTLES[BLACK]:
            tints[_cid(cell)] = "#26313b"
        pieces = []
        for cell, stack in state.board.items():
            head_owner, head_kind = stack[-1]
            label = (str(self._power(state, stack)) if state.variant == "pari"
                     else head_kind)
            pieces.append({
                "cell": _cid(cell),
                "owner": head_owner,
                "stack": [o for (o, _k) in stack],
                "label": label,
            })
        highlights = [{"cell": c, "kind": "last-move"} for c in state.last]
        if state.cont is not None:
            highlights.append({"cell": _cid(state.cont), "kind": "goal"})
        if state.winner == "draw":
            cap = "Draw"
        elif state.winner is not None:
            cap = f"{SEAT_NAMES[state.winner]} wins"
        elif state.cont is not None:
            cap = (f"{SEAT_NAMES[state.to_move]} — continue from "
                   f"{_alg(state.cont)} or end the turn")
        else:
            cap = f"{SEAT_NAMES[state.to_move]} to move"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": 4,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
            "actionNames": {"done": "End turn"},
            "choiceNames": {str(i): f"{i} piece{'s' if i > 1 else ''}"
                            for i in range(1, 7)},
        }
