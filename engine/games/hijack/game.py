"""Hi-Jack -- Barrie Evans' territorial stacking game (Abstract Games #14, 2003).

Players alternate PLACING pieces (which never move) on an 8x8 board. A stack of
height h exerts *territorial strength* (value 1 per square) over the board:

  * orthogonally up to h squares out, and
  * diagonally up to max(0, h-2) squares out (so 1- and 2-high stacks are
    orthogonal-only; a 3-high reaches 1 diagonally; a 4-high reaches 2).

The furthest ORTHOGONAL square of a ray gets no strength if all the intervening
squares along that ray are occupied ("blocking"). The controller of a stack's
strength is the owner of its TOP piece.

Placement legality (strength measured BEFORE the piece is laid):
  * empty square: your strength >= opponent's strength.
  * opponent's square (an attack): your strength >= attacked height + defender's
    strength. Success puts your piece on top; attacking a stack >= 2 high is a
    "hi-jack".
  * your own single piece: you may add a second piece for free (rule 1).
  * a stack you have attacked-and-occupied: on a later turn you may add ONE more
    piece for free (rule 2).

Scoring at game end: 1 point per UNOCCUPIED square where you exert strictly
greater strength than the opponent, plus 1 point per hi-jacked stack you still
occupy. Higher total wins; equal is an honest draw.

Passing is allowed; two consecutive passes end the game (a hard ply cap also
ends it, for termination under random play). An anti-mirroring "switch" action
is offered when the position is symmetric after each player has made >= 3 moves.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

WHITE, BLACK = 0, 1
ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
PLY_CAP = 400


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _alg(c, r):
    return f"{chr(ord('a') + c)}{r + 1}"


@dataclass
class HState:
    board: dict = field(default_factory=dict)      # (c,r) -> list of owners, bottom->top
    to_move: int = BLACK
    size: int = 8
    passes: int = 0                                # consecutive passes
    ply: int = 0
    moved: list = field(default_factory=lambda: [0, 0])   # turns taken per player
    hijacks: set = field(default_factory=set)      # squares that are hi-jacked stacks
    reinforce: dict = field(default_factory=dict)  # sq -> player who may add 1 free piece
    forced: list = field(default_factory=list)     # forthcoming forced movers (anti-mirror switch)


class HiJack(Game):
    uid = "hijack"
    name = "Hi-Jack"

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        size = int(opts.get("size", 8))
        return HState(board={}, to_move=BLACK, size=size)

    def current_player(self, state):
        return state.to_move

    # ---- strength ----------------------------------------------------------
    def _covered(self, pos, h, occ, size):
        """Squares (on board) over which a height-h stack at pos exerts strength."""
        c, r = pos
        out = []
        orange = h
        drange = max(0, h - 2)
        for dc, dr in ORTH:
            ray = []
            for d in range(1, orange + 1):
                x, y = c + dc * d, r + dr * d
                if not (0 <= x < size and 0 <= y < size):
                    break
                ray.append((d, (x, y)))
            for d, sq in ray:
                if d == orange and orange >= 2:
                    # furthest square: blocked iff all intervening squares occupied
                    if all((c + dc * k, r + dr * k) in occ for k in range(1, orange)):
                        continue
                out.append(sq)
        for dc, dr in DIAG:
            for d in range(1, drange + 1):
                x, y = c + dc * d, r + dr * d
                if 0 <= x < size and 0 <= y < size:
                    out.append((x, y))    # diagonals are not subject to blocking
        return out

    def _strength(self, state):
        """dict sq -> [white_strength, black_strength]."""
        occ = set(state.board.keys())
        strength = {}
        for pos, col in state.board.items():
            owner = col[-1]
            h = len(col)
            for sq in self._covered(pos, h, occ, state.size):
                cell = strength.setdefault(sq, [0, 0])
                cell[owner] += 1
        return strength

    def _at(self, strength, sq):
        return strength.get(sq, [0, 0])

    # ---- legality ----------------------------------------------------------
    def _legal_placements(self, state, strength):
        out = []
        p = state.to_move
        o = 1 - p
        for r in range(state.size):
            for c in range(state.size):
                sq = (c, r)
                col = state.board.get(sq)
                mine, theirs = self._at(strength, sq)
                if col is None:                       # empty
                    if (mine if p == WHITE else theirs) >= (theirs if p == WHITE else mine):
                        out.append(sq)
                elif col[-1] == p:                    # my own stack
                    if len(col) == 1 or state.reinforce.get(sq) == p:
                        out.append(sq)
                else:                                 # opponent's stack -> attack
                    atk = mine if p == WHITE else theirs
                    dfd = theirs if p == WHITE else mine
                    if atk >= len(col) + dfd:
                        out.append(sq)
        return out

    def _symmetric(self, state):
        """180-degree rotation with colours swapped (a mirror/copy game)."""
        n = state.size
        for (c, r), col in state.board.items():
            rc, rr = n - 1 - c, n - 1 - r
            other = state.board.get((rc, rr))
            inv = [1 - o for o in col]
            if other != inv:
                return False
        return True

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        strength = self._strength(state)
        moves = [f"{c},{r}" for (c, r) in self._legal_placements(state, strength)]
        moves.append("pass")
        if (not state.forced and state.moved[0] >= 3 and state.moved[1] >= 3
                and state.board and self._symmetric(state)):
            moves.append("switch")
        return moves

    # ---- apply -------------------------------------------------------------
    def _advance(self, ns, mover):
        if ns.forced:
            ns.to_move = ns.forced.pop(0)
        else:
            ns.to_move = 1 - mover

    def apply_move(self, state, move, rng=None):
        ns = HState(
            board={k: list(v) for k, v in state.board.items()},
            to_move=state.to_move, size=state.size, passes=state.passes,
            ply=state.ply + 1, moved=list(state.moved),
            hijacks=set(state.hijacks), reinforce=dict(state.reinforce),
            forced=list(state.forced))
        p = state.to_move

        if move == "switch":
            o = 1 - p
            ns.to_move = o
            ns.forced = [p, p, o]
            ns.passes = 0                             # a switch is not a pass -> breaks the consecutive-pass chain
            return ns                                 # no placement, no pass, no move-count

        ns.moved[p] += 1
        if move == "pass":
            ns.passes = state.passes + 1
            self._advance(ns, p)
            return ns

        ns.passes = 0
        sq = _cell(move)
        col = ns.board.get(sq)
        if col is None:                               # place on empty
            ns.board[sq] = [p]
        elif col[-1] == p:                            # reinforce own
            if state.reinforce.get(sq) == p:
                ns.reinforce.pop(sq, None)            # consume the free reinforcement
            ns.board[sq] = col + [p]
        else:                                         # attack
            attacked_h = len(col)
            ns.board[sq] = col + [p]
            if attacked_h >= 2:
                ns.hijacks.add(sq)                    # a hi-jack
            ns.reinforce[sq] = p                      # earns one free reinforcement later
        self._advance(ns, p)
        return ns

    # ---- terminal / scoring ------------------------------------------------
    def is_terminal(self, state):
        return state.passes >= 2 or state.ply >= PLY_CAP

    def score(self, state):
        strength = self._strength(state)
        pts = [0, 0]
        for r in range(state.size):
            for c in range(state.size):
                sq = (c, r)
                if sq in state.board:
                    continue                          # only UNOCCUPIED squares
                w, b = self._at(strength, sq)
                if w > b:
                    pts[WHITE] += 1
                elif b > w:
                    pts[BLACK] += 1
        for sq in state.hijacks:
            col = state.board.get(sq)
            if col:
                pts[col[-1]] += 1                     # hi-jacked and still occupied
        return pts

    def returns(self, state):
        w, b = self.score(state)
        if w > b:
            return [1.0, -1.0]
        if b > w:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, state):
        import math
        w, b = self.score(state)
        v = math.tanh((w - b) / 8.0)
        return [v, -v]

    # ---- serialise ---------------------------------------------------------
    def serialize(self, state):
        return {
            "board": {f"{c},{r}": "".join(str(o) for o in col)
                      for (c, r), col in state.board.items()},
            "to_move": state.to_move, "size": state.size, "passes": state.passes,
            "ply": state.ply, "moved": list(state.moved),
            "hijacks": [f"{c},{r}" for (c, r) in sorted(state.hijacks)],
            "reinforce": {f"{c},{r}": o for (c, r), o in state.reinforce.items()},
            "forced": list(state.forced),
        }

    def deserialize(self, d):
        return HState(
            board={_cell(k): [int(ch) for ch in v] for k, v in d["board"].items()},
            to_move=d["to_move"], size=d.get("size", 8), passes=d.get("passes", 0),
            ply=d.get("ply", 0), moved=list(d.get("moved", [0, 0])),
            hijacks={_cell(k) for k in d.get("hijacks", [])},
            reinforce={_cell(k): v for k, v in d.get("reinforce", {}).items()},
            forced=list(d.get("forced", [])))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if move in ("pass", "switch"):
            return move
        c, r = _cell(move)
        return _alg(c, r)

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), col in state.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": col[-1],
                "stack": list(col),                   # bottom -> top owners
                "label": "H" if (c, r) in state.hijacks else "",
            })
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            w, b = self.score(state)
            if w == b:
                cap = f"Draw {w}-{b}"
            else:
                win = WHITE if w > b else BLACK
                cap = f"{names[win]} wins {max(w, b)}-{min(w, b)}"
        else:
            cap = f"{names[state.to_move]} to place"
        spec = {
            "board": {"type": "square", "width": state.size, "height": state.size},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
            "actionNames": {"pass": "Pass", "switch": "Switch order (anti-mirror)"},
        }
        return spec
