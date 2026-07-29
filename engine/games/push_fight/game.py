"""Push Fight (Brett Picotte, ~1990) -- shove your opponent off a 26-square board.

The board is a 4x8 grid with six squares missing: rank 4 spans files c-g, rank 1
spans files b-f, ranks 2 and 3 span the full a-h. **Side rails** run along the
outer top edge of rank 4 and the outer bottom edge of rank 1; a piece can never
be pushed through a rail, but every other board edge is open and a piece pushed
across it falls off.

Each player has 3 **squares** (pushers) and 2 **circles** (movers). A turn is up
to two *moves* (slide a piece any distance through empty squares) followed by one
mandatory *push* (a square shoves an adjacent line of pieces one step). After a
push an **anchor** is placed on the pushing square; the opponent may not push
that piece -- nor any line containing it -- on their next turn.

A player loses if one of their pieces is pushed off the board (even by their own
push) or if they cannot complete a turn (no legal push after any legal 0-2 moves).

**Move encoding.** A turn is played as SEPARATE plies by the same player, so the
click-a-cell UI works: each move and the final push is its own ``"from>to"``
string. The two are never ambiguous -- a *move* always ends on an EMPTY square, a
*push* always ends on an OCCUPIED one. Setup places one piece per ply with the
reserve drop syntax ``"S@c,r"`` (square) / ``"C@c,r"`` (circle).

Sources: the official rules (pushfightgame.com/rules.htm, Brettco Inc.), Bosboom,
Demaine & Rudoy, "Computational Complexity of Generalized Push Fight"
(arXiv:1803.03708) and Maks Verver's complete solution of the game
(github.com/maksverver/pushfight), whose reference implementation fixes the exact
board geometry and rail semantics used here.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from agp.game import Game

W, H = 8, 4

# Which files exist on each rank (r = rank - 1, so r=0 is rank 1 at the bottom).
# Verified against maksverver/pushfight html/src/board.js FIELD_INDEX.
ROW_FILES = {3: range(2, 7), 2: range(0, 8), 1: range(0, 8), 0: range(1, 6)}
CELLS = frozenset(f"{c},{r}" for r, cs in ROW_FILES.items() for c in cs)   # 26
VOID = [f"{c},{r}" for r in range(H) for c in range(W) if f"{c},{r}" not in CELLS]

# maksverver's field order: rank 4 left->right, then rank 3, rank 2, rank 1.
PERM_ORDER = [f"{c},{r}" for r in (3, 2, 1, 0) for c in ROW_FILES[r]]

DIRS = ((0, 1), (0, -1), (1, 0), (-1, 0))
ADJ = {p: [q for q in (f"{int(p.split(',')[0]) + dc},{int(p.split(',')[1]) + dr}"
                       for dc, dr in DIRS) if q in CELLS] for p in CELLS}

PUSHER, MOVER = "S", "C"
HALF = {0: range(0, 4), 1: range(4, 8)}          # a-d for red, e-h for blue
PLACE_CELLS = {p: sorted(c for c in CELLS if int(c.split(",")[0]) in HALF[p])
               for p in (0, 1)}

# The complete solution reports the longest forced win as 49 turns for one player
# (97 total turns).  The cap below is ~3x that bound, so it can never truncate a
# decisive line; it exists only because tied positions are genuinely infinite.
TURN_CAP = 300

# The web app's default opening (board.js INITIAL_PIECES) -- 180-degree symmetric,
# four pieces on each centre file.  Maks Verver's solver evaluates it as a TIE.
STANDARD = {
    "3,3": (0, PUSHER), "3,2": (0, MOVER), "3,1": (0, PUSHER),
    "3,0": (0, PUSHER), "2,1": (0, MOVER),
    "4,3": (1, PUSHER), "4,2": (1, PUSHER), "4,1": (1, MOVER),
    "4,0": (1, PUSHER), "5,2": (1, MOVER),
}

NAMES = {0: "Red", 1: "Blue"}


def _xy(cell):
    c, r = cell.split(",")
    return int(c), int(r)


def alg(cell):
    """Cell id -> chess-style name ('3,1' -> 'd2'), the notation every source uses."""
    c, r = _xy(cell)
    return chr(ord("a") + c) + str(r + 1)


def perm_string(board, anchor=None):
    """maksverver's 26-character position string ('.oOxXY' + 'P' for a red anchor)."""
    out = []
    for cell in PERM_ORDER:
        pc = board.get(cell)
        if pc is None:
            out.append(".")
            continue
        owner, kind = pc
        if kind == MOVER:
            out.append("o" if owner == 0 else "x")
        elif cell == anchor:
            out.append("P" if owner == 0 else "Y")
        else:
            out.append("O" if owner == 0 else "X")
    return "".join(out)


# --------------------------------------------------------------------------- #
# Rules primitives.  `_push_ok` / `_do_push` are literal transcriptions of
# canPush() / executeMoves() in maksverver/pushfight html/src/moves.js.
# --------------------------------------------------------------------------- #

def _reach(board, start):
    """Every empty cell reachable from `start` through orthogonally adjacent empties."""
    seen = set()
    todo = deque([start])
    while todo:
        cur = todo.popleft()
        for nxt in ADJ[cur]:
            if nxt not in seen and nxt not in board:
                seen.add(nxt)
                todo.append(nxt)
    return seen


def _quiet_moves(board, player):
    out = []
    for cell, (owner, _kind) in board.items():
        if owner != player:
            continue
        for dst in sorted(_reach(board, cell)):
            out.append((cell, dst))
    return out


def _push_ok(board, anchor, src, dc, dr):
    """Can the square on `src` push in direction (dc, dr)?"""
    c, r = _xy(src)
    c += dc
    r += dr
    cell = f"{c},{r}"
    if cell not in CELLS or cell not in board:
        return False                       # a push must move at least one piece
    while True:
        if cell == anchor:
            return False                   # the anchored piece cannot be pushed
        c += dc
        r += dr
        if not (0 <= r < H):
            return False                   # side rail: top of rank 4 / bottom of rank 1
        cell = f"{c},{r}"
        if cell not in CELLS or cell not in board:
            return True                    # chain ends on an empty square, or falls off


def _pushes(board, player, anchor):
    out = []
    for cell, (owner, kind) in board.items():
        if owner != player or kind != PUSHER:
            continue
        c, r = _xy(cell)
        for dc, dr in DIRS:
            if _push_ok(board, anchor, cell, dc, dr):
                out.append((cell, f"{c + dc},{r + dr}"))
    return sorted(out)


def _any_push(board, player, anchor):
    for cell, (owner, kind) in board.items():
        if owner != player or kind != PUSHER:
            continue
        for dc, dr in DIRS:
            if _push_ok(board, anchor, cell, dc, dr):
                return True
    return False


def _do_push(board, src, dst):
    """Resolve a push. Returns (new_board, fallen_piece_or_None)."""
    nb = dict(board)
    sc, sr = _xy(src)
    c, r = _xy(dst)
    dc, dr = c - sc, r - sr
    carry = nb.pop(src)
    cell = dst
    while True:
        nxt = nb.get(cell)
        nb[cell] = carry
        carry = nxt
        c += dc
        r += dr
        cell = f"{c},{r}"
        if carry is None:
            return nb, None
        if cell not in CELLS:
            return nb, carry               # this piece is pushed off the board


def _can_complete(board, player, anchor, budget):
    """Is a legal turn (<= `budget` further moves, then a push) available?"""
    if _any_push(board, player, anchor):
        return True
    if budget <= 0:
        return False
    for src, dst in _quiet_moves(board, player):
        nb = dict(board)
        nb[dst] = nb.pop(src)
        if _can_complete(nb, player, anchor, budget - 1):
            return True
    return False


@dataclass
class PFState:
    board: dict = field(default_factory=dict)        # cell -> (owner, kind)
    to_move: int = 0
    moves_used: int = 0                              # 0..2 within the current turn
    anchor: object = None                            # cell of the anchored square
    stock: list = field(default_factory=lambda: [[0, 0], [0, 0]])   # [S, C] left to place
    turns: int = 0                                   # completed turns (pushes)
    reps: dict = field(default_factory=dict)         # turn-start position -> count
    winner: object = None                            # seat index, or None
    draw: object = None                              # reason string, or None
    last: object = None                              # (from, to) of the last action


class PushFight(Game):
    uid = "push_fight"
    name = "Push Fight"

    @property
    def num_players(self):
        return 2

    # ---- setup ------------------------------------------------------------ #

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        if opts.get("setup", "free") == "standard":
            s = PFState(board=dict(STANDARD))
            self._start_turn(s)
            return s
        return PFState(stock=[[3, 2], [3, 2]])

    def current_player(self, state):
        return state.to_move

    # ---- moves ------------------------------------------------------------ #

    def _placing(self, s):
        return any(n for seat in s.stock for n in seat)

    def legal_moves(self, s):
        if self.is_terminal(s):
            return []
        if self._placing(s):
            n_s, n_c = s.stock[s.to_move]
            out = []
            for cell in PLACE_CELLS[s.to_move]:
                if cell in s.board:
                    continue
                if n_s:
                    out.append(f"{PUSHER}@{cell}")
                if n_c:
                    out.append(f"{MOVER}@{cell}")
            return out

        pushes = [f"{a}>{b}" for a, b in _pushes(s.board, s.to_move, s.anchor)]
        budget = 2 - s.moves_used
        if budget <= 0:
            return pushes

        quiet = _quiet_moves(s.board, s.to_move)
        if budget >= 2 and pushes:
            # Two moves left and a push already available: every quiet move is safe,
            # because the piece can always retrace its (still empty) path next ply
            # and then make that same push.  No completion check needed.
            keep = quiet
        else:
            keep = []
            for src, dst in quiet:
                nb = dict(s.board)
                nb[dst] = nb.pop(src)
                if _can_complete(nb, s.to_move, s.anchor, budget - 1):
                    keep.append((src, dst))
        return [f"{a}>{b}" for a, b in keep] + pushes

    def apply_move(self, s, move, rng=None):
        n = PFState(board=dict(s.board), to_move=s.to_move, moves_used=s.moves_used,
                    anchor=s.anchor, stock=[list(x) for x in s.stock], turns=s.turns,
                    reps=dict(s.reps), winner=s.winner, draw=s.draw, last=s.last)

        if "@" in move:                                    # setup placement
            kind, cell = move.split("@", 1)
            n.board[cell] = (n.to_move, kind)
            n.stock[n.to_move][0 if kind == PUSHER else 1] -= 1
            n.last = (None, cell)
            if not any(n.stock[n.to_move]):                # this seat is done placing
                if any(n.stock[1 - n.to_move]):
                    n.to_move = 1 - n.to_move
                else:
                    n.to_move = 0
                    self._start_turn(n)
            return n

        src, dst = move.split(">")
        n.last = (src, dst)
        if dst not in n.board:                             # a quiet move
            n.board[dst] = n.board.pop(src)
            n.moves_used += 1
            return n

        n.board, fallen = _do_push(n.board, src, dst)      # the push ends the turn
        n.anchor = dst
        n.moves_used = 0
        n.turns += 1
        if fallen is not None:
            n.winner = 1 - fallen[0]                       # the owner of the fallen piece loses
            return n
        n.to_move = 1 - n.to_move
        self._start_turn(n)
        return n

    def _start_turn(self, n):
        """Open a turn for `n.to_move`: decide stuck-loss FIRST, then the draw counters.

        A decisive result must outrank the repetition/ply counters -- the single
        most repeated defect in this library -- so the stuck check runs first and
        returns before `draw` can ever be set.
        """
        if not _can_complete(n.board, n.to_move, n.anchor, 2):
            n.winner = 1 - n.to_move                       # cannot push => you lose
            return
        key = perm_string(n.board, n.anchor) + str(n.to_move)
        c = n.reps.get(key, 0) + 1
        n.reps[key] = c
        if c >= 3:
            n.draw = "repetition"
        elif n.turns >= TURN_CAP:
            n.draw = "turn limit"

    # ---- results ---------------------------------------------------------- #

    def is_terminal(self, s):
        return s.winner is not None or s.draw is not None

    def returns(self, s):
        if s.winner is not None:                           # decisive beats every counter
            return [1.0 if p == s.winner else -1.0 for p in (0, 1)]
        return [0.0, 0.0]

    # ---- persistence ------------------------------------------------------ #

    def serialize(self, s):
        return {
            "board": {k: [v[0], v[1]] for k, v in s.board.items()},
            "to_move": s.to_move,
            "moves_used": s.moves_used,
            "anchor": s.anchor,
            "stock": [list(x) for x in s.stock],
            "turns": s.turns,
            "reps": dict(s.reps),
            "winner": s.winner,
            "draw": s.draw,
            "last": list(s.last) if s.last is not None else None,
        }

    def deserialize(self, d):
        return PFState(
            board={k: (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            moves_used=d["moves_used"],
            anchor=d["anchor"],
            stock=[list(x) for x in d["stock"]],
            turns=d["turns"],
            reps=dict(d["reps"]),
            winner=d["winner"],
            draw=d["draw"],
            last=tuple(d["last"]) if d["last"] is not None else None,
        )

    # ---- notation --------------------------------------------------------- #

    def describe_move(self, s, move):
        if "@" in move:
            kind, cell = move.split("@", 1)
            what = "square" if kind == PUSHER else "circle"
            return f"{NAMES[s.to_move]} {what} → {alg(cell)}"
        src, dst = move.split(">")
        if dst not in s.board:
            return f"{alg(src)}-{alg(dst)}"
        _nb, fallen = _do_push(s.board, src, dst)
        if fallen is not None:
            return (f"{alg(src)}-{alg(dst)} push — {NAMES[fallen[0]]} piece off "
                    f"({NAMES[1 - fallen[0]]} wins)")
        return f"{alg(src)}-{alg(dst)} push"

    # ---- bot eval --------------------------------------------------------- #

    def heuristic(self, s):
        """Per-seat payoffs (a LIST, as `returns`) for the MCTS rollout cutoff.

        Cheap positional read: a piece standing where the opponent could shove it
        over an open edge is a liability, and push mobility is tempo.
        """
        exposed = [0, 0]
        for cell, (owner, _k) in s.board.items():
            c, r = _xy(cell)
            for dc, dr in DIRS:
                out = f"{c + dc},{r + dr}"
                back = f"{c - dc},{r - dr}"
                # Off an open edge that way, and a pusher could stand behind it.
                if out not in CELLS and 0 <= r + dr < H and back in CELLS:
                    exposed[owner] += 1
                    break
        mob = [len(_pushes(s.board, p, s.anchor)) for p in (0, 1)]
        v = 0.30 * (exposed[1] - exposed[0]) + 0.04 * (mob[0] - mob[1])
        v = math.tanh(v)
        return [v, -v]

    # ---- rendering -------------------------------------------------------- #

    def render(self, s, perspective=None):
        tints = {cell: "#12100d" for cell in VOID}          # the six missing squares
        if s.anchor is not None:
            # Dark enough that the seat-coloured piece standing on it keeps its
            # contrast (a brighter red dropped a red square to ~1.9:1 against its
            # own cell), red enough to read as the anchor token.
            tints[s.anchor] = "#5c2626"

        pieces = []
        for cell, (owner, kind) in sorted(s.board.items()):
            if kind == MOVER:
                pieces.append({"cell": cell, "owner": owner})
            else:
                pieces.append({"cell": cell, "owner": owner,
                               "glyph": "▣" if cell == s.anchor else "■"})

        # Side rails: the outer top edge of rank 4 and outer bottom edge of rank 1.
        # 5/11 is half a cell in board-coord space (Board.jsx: R=30, pitch=66).
        e = 5.0 / 11.0
        rail = "#d8cdb4"
        overlay = [[[2 - e, 3 + e], [6 + e, 3 + e], rail],
                   [[1 - e, 0 - e], [5 + e, 0 - e], rail]]

        spec = {
            "board": {"type": "square", "width": W, "height": H,
                      "tints": tints, "overlay": overlay},
            "pieces": pieces,
            # NOTE the `c != s.anchor` filter. Board.jsx resolves a cell's fill as
            #   last-move highlight > board.tints > default
            # so highlighting the push DESTINATION -- which is always exactly the
            # cell the anchor lands on -- would paint over the anchor tint on the
            # one ply that matters (the opponent's, while they plan around it).
            # The source cell still shows the push, and the anchor keeps its tint.
            "highlights": ([{"cell": c, "kind": "last-move"}
                            for c in (s.last or ()) if c and c != s.anchor]
                           if s.last else []),
            "caption": self._caption(s),
        }
        if self._placing(s):
            spec["reserve"] = {str(p): {k: v for k, v in
                                        ((PUSHER, s.stock[p][0]), (MOVER, s.stock[p][1])) if v}
                               for p in (0, 1)}
        return spec

    def _caption(self, s):
        if s.winner is not None:
            return f"{NAMES[s.winner]} wins"
        if s.draw is not None:
            return f"Draw ({s.draw})"
        if self._placing(s):
            n_s, n_c = s.stock[s.to_move]
            return (f"{NAMES[s.to_move]} to place — {n_s} square(s), "
                    f"{n_c} circle(s) left")
        left = 2 - s.moves_used
        return (f"{NAMES[s.to_move]} to move — {left} move(s) left, then a push"
                if left else f"{NAMES[s.to_move]} must push")
