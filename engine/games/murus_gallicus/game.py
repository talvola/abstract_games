"""Murus Gallicus -- Phil Leduc's 2009 tower/wall breakthrough game.

8x7 board (8 columns, 7 rows). Each player starts with 16 stones stacked as
eight two-stone **towers** on their home row. On a turn a player must either:

* **Move a tower**: distribute its two stones onto the two nearest cells in any
  one straight-line direction (orthogonal or diagonal) -- one stone on the near
  cell, one on the far cell. Each destination must be empty or hold a friendly
  **wall** (a single stone); a stone landing on a friendly wall builds it into a
  tower. Friendly towers and any enemy stones block the distribution.
* **Sacrifice**: remove one stone from a tower (leaving a wall) to demolish an
  adjacent (orthogonal or diagonal) enemy wall. Enemy towers cannot be
  sacrificed against.

Walls never move. A player wins by getting any stone onto the opponent's home
row, or by stalemating the opponent (no legal move at the start of their turn
loses). Threefold repetition or a hard ply cap is scored an honest draw.

Rules per the official nestorgames rulebook (rules (c) 2009 Phillip Leduc) and
Wikipedia. Romans (player 0, home row 0) move first.

Move encoding: distribution = ``"from>far"`` (the far cell is two steps away;
the near cell is implied). Sacrifice = ``"from>wall"`` (the enemy wall is one
step away). The Chebyshev distance disambiguates the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

WIDTH, HEIGHT = 8, 7
ROMAN, GAUL = 0, 1                       # player 0 = Romans (home row 0)
DIRS = [(dc, dr) for dc in (-1, 0, 1) for dr in (-1, 0, 1) if (dc, dr) != (0, 0)]
PLY_CAP = 500                            # honest-draw backstop


def _on(c, r):
    return 0 <= c < WIDTH and 0 <= r < HEIGHT


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _home_row(player):
    return 0 if player == ROMAN else HEIGHT - 1


def _goal_row(player):
    return HEIGHT - 1 if player == ROMAN else 0


@dataclass
class MGState:
    board: dict = field(default_factory=dict)   # (c,r) -> (owner, height 1|2)
    to_move: int = ROMAN
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class MurusGallicus(Game):
    name = "Murus Gallicus"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {}
        for c in range(WIDTH):
            board[(c, _home_row(ROMAN))] = (ROMAN, 2)
            board[(c, _home_row(GAUL))] = (GAUL, 2)
        st = MGState(board=board, to_move=ROMAN)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- move generation ----------------------------------------------------
    def _dest_ok(self, board, cell, player):
        """A distribution stone may land on an empty cell or a friendly wall."""
        if not _on(*cell):
            return False
        occ = board.get(cell)
        return occ is None or occ == (player, 1)

    def _gen_moves(self, board, player):
        out = []
        for (c, r), (owner, h) in board.items():
            if owner != player or h != 2:        # only towers act
                continue
            for (dc, dr) in DIRS:
                near = (c + dc, r + dr)
                far = (c + 2 * dc, r + 2 * dr)
                # distribution: both cells empty-or-friendly-wall
                if self._dest_ok(board, near, player) and self._dest_ok(board, far, player):
                    out.append(f"{c},{r}>{far[0]},{far[1]}")
                # sacrifice: adjacent enemy wall
                if board.get(near) == (1 - player, 1):
                    out.append(f"{c},{r}>{near[0]},{near[1]}")
        return out

    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        return self._gen_moves(state.board, state.to_move)

    # ---- apply ---------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        frm_s, to_s = move.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        player = state.to_move
        board = dict(state.board)
        dist = max(abs(to[0] - frm[0]), abs(to[1] - frm[1]))
        if dist == 2:                            # tower distribution
            near = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
            del board[frm]
            for cell in (near, to):
                occ = board.get(cell)
                board[cell] = (player, 1) if occ is None else (player, 2)
        else:                                    # sacrifice vs adjacent enemy wall
            board[frm] = (player, 1)             # tower loses a stone -> wall
            del board[to]                        # enemy wall demolished

        ns = MGState(board=board, to_move=1 - player, ply=state.ply + 1,
                     reps=dict(state.reps))
        # win: any own stone on the opponent's home row (only a distribution
        # can put one there, but check generically)
        goal = _goal_row(player)
        if any(r == goal and owner == player
               for (c, r), (owner, h) in board.items()):
            ns.winner = player
            return ns
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        # stalemate: the opponent cannot move or sacrifice at the start of
        # their turn -> they lose
        if not self._draw(ns) and not self._gen_moves(board, ns.to_move):
            ns.winner = player
        return ns

    # ---- terminal --------------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.ply >= PLY_CAP
                     or state.reps.get(self._key(state), 0) >= 3))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- heuristic (MCTS rollout-cutoff eval) ---------------------------------
    def heuristic(self, state):
        """Stone count + advancement toward the goal row, squashed to (-1, 1)."""
        import math
        score = 0.0
        for (c, r), (owner, h) in state.board.items():
            adv = r if owner == ROMAN else (HEIGHT - 1 - r)
            v = h * 1.0 + h * 0.25 * adv
            score += v if owner == ROMAN else -v
        val = math.tanh(score / 8.0)
        return [val, -val]

    # ---- keys / serialise ------------------------------------------------------
    def _key(self, state):
        b = "|".join(f"{c},{r}:{o}{h}" for (c, r), (o, h) in sorted(state.board.items()))
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        return {
            "board": {f"{c},{r}": [o, h] for (c, r), (o, h) in state.board.items()},
            "to_move": state.to_move, "ply": state.ply,
            "reps": dict(state.reps), "winner": state.winner,
        }

    def deserialize(self, d):
        return MGState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"], ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ----------------------------------------------------------
    def describe_move(self, state, move):
        frm_s, to_s = move.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        dist = max(abs(to[0] - frm[0]), abs(to[1] - frm[1]))
        return f"{frm_s}-{to_s}" if dist == 2 else f"{frm_s}x{to_s}"

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), (owner, h) in state.board.items():
            p = {"cell": f"{c},{r}", "owner": owner}
            if h == 2:
                p["stack"] = [owner, owner]      # tower glyph
            pieces.append(p)
        names = {ROMAN: "Romans", GAUL: "Gauls"}
        if state.winner is not None:
            cap = f"{names[state.winner]} win"
        elif self._draw(state):
            cap = "Draw"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": WIDTH, "height": HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
