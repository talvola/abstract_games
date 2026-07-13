"""Qawale -- Romain Froger & Didier Lenain-Bragard, Gigamic 2022.

A 4x4 stacking / sowing race. Each player holds 8 pebbles; 2 NEUTRAL (tan)
pebbles start stacked on each corner. On your turn you choose any stack (a
single pebble counts as a stack -- you may NOT play into an empty space),
place one of your pebbles on top, then pick the whole stack up and sow it:
starting on a square orthogonally adjacent to the stack's square, drop the
pebbles ONE PER SQUARE, BOTTOM pebble first, each square orthogonally
adjacent to the previous one. You may never step straight back onto the
square you just came from (including the lifted stack's own square as the
second drop), but you may return to a square by circling round to it -- it
then simply receives another pebble on top.

The first *visible* line of 4 of a colour -- row, column or diagonal, where
visible = the top (or only) pebble of a stack -- wins for THAT colour's
player, whoever made the move: sowing your opponent's buried pebbles back on
top can hand them the game. (The Gigamic rulebook is silent on the
simultaneous case; per the Quixo precedent we rule that if one sow completes
lines of BOTH colours the NON-mover wins -- see rules.md.) A vertical stack
of 4 of a colour is NOT a line. If both players have played all 8 pebbles
and no line exists, the game is a DRAW (the game therefore always ends
within 16 plies).

Move encoding: `"c,r>p1>p2>...>pn"` -- the first cell is the stack you top
and lift, the rest is the full sowing path (n = lifted height, one drop per
listed square, bottom-first, so YOUR pebble lands on the last square). All
moves from one source have equal length and distinct sources differ at the
first cell, so paths are prefix-safe for the click-to-move UI.

Renders via the standard square board + `piece.stack` towers; neutral
pebbles are owner 2, the platform's neutral colour (green).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 4
LIGHT, DARK = 0, 1          # seats (rendered red / blue)
NEUTRAL = 2                 # the tan pebbles (platform neutral colour)
HAND = 8                    # pebbles per player
ORTH = [(0, 1), (0, -1), (1, 0), (-1, 0)]
CORNERS = [(0, 0), (SIZE - 1, 0), (0, SIZE - 1), (SIZE - 1, SIZE - 1)]

# The 10 lines of 4 on a 4x4 board: 4 rows, 4 columns, 2 diagonals.
LINES = (
    [[(c, r) for c in range(SIZE)] for r in range(SIZE)]
    + [[(c, r) for r in range(SIZE)] for c in range(SIZE)]
    + [[(i, i) for i in range(SIZE)], [(i, SIZE - 1 - i) for i in range(SIZE)]]
)


def _on(sq):
    return 0 <= sq[0] < SIZE and 0 <= sq[1] < SIZE


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(sq):
    return f"{sq[0]},{sq[1]}"


@dataclass
class QState:
    board: dict = field(default_factory=dict)  # (c,r) -> tuple of owners, bottom->top
    hands: tuple = (HAND, HAND)                # pebbles left in each player's hand
    to_move: int = LIGHT
    ply: int = 0
    winner: object = None


class Qawale(Game):
    name = "Qawale"

    @property
    def num_players(self):
        return 2

    # ---- setup -------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        board = {sq: (NEUTRAL, NEUTRAL) for sq in CORNERS}
        return QState(board=board)

    def current_player(self, state):
        return state.to_move

    # ---- move generation ---------------------------------------------------
    def _paths(self, src, n):
        """All sowing paths of exactly n squares starting orthogonally adjacent
        to src. With the extended sequence e = [src, p1..pn], the rule "you
        cannot go back over a space you have just passed through" forbids
        e[i+1] == e[i-1]; circling back to a square later is legal."""
        out = []

        def go(back, cur, acc):
            if len(acc) == n:
                out.append(tuple(acc))
                return
            for dc, dr in ORTH:
                t = (cur[0] + dc, cur[1] + dr)
                if _on(t) and t != back:
                    go(cur, t, acc + [t])

        go(None, src, [])
        return out

    def legal_moves(self, state):
        if self.is_terminal(state) or state.hands[state.to_move] <= 0:
            return []
        moves = []
        for src, stack in state.board.items():
            n = len(stack) + 1                  # lifted height after the placement
            for path in self._paths(src, n):
                moves.append(_fmt(src) + ">" + ">".join(_fmt(p) for p in path))
        return moves

    # ---- apply -------------------------------------------------------------
    def _line_colour(self, board, colour):
        """True if some row/column/diagonal has `colour` visible (on top) on
        all four squares. Empty squares break every line through them."""
        for line in LINES:
            if all(sq in board and board[sq][-1] == colour for sq in line):
                return True
        return False

    def apply_move(self, state, move, rng=None):
        player = state.to_move
        cells = [_cell(x) for x in move.split(">")]
        src, path = cells[0], cells[1:]

        board = dict(state.board)
        picked = board.pop(src) + (player,)     # your pebble goes on top, then lift all
        for sq, stone in zip(path, picked):     # sow bottom-first, one per square
            board[sq] = board.get(sq, ()) + (stone,)

        hands = list(state.hands)
        hands[player] -= 1

        # A visible line wins for its COLOUR, whoever moved; if the sow
        # completes lines of both colours at once, the non-mover wins.
        opp = 1 - player
        winner = None
        if self._line_colour(board, opp):
            winner = opp
        elif self._line_colour(board, player):
            winner = player

        return QState(board=board, hands=tuple(hands), to_move=opp,
                      ply=state.ply + 1, winner=winner)

    # ---- terminal ----------------------------------------------------------
    def is_terminal(self, state):
        return state.winner is not None or state.hands == (0, 0)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    def heuristic(self, state):
        """Rollout-cutoff eval: value open lines (no enemy pebble visible on
        them) super-linearly in how many of your tops they already hold."""
        import math
        w = (0.0, 1.0, 3.0, 9.0, 27.0)
        score = 0.0
        for line in LINES:
            tops = [state.board[sq][-1] for sq in line if sq in state.board]
            mine, theirs = tops.count(LIGHT), tops.count(DARK)
            if theirs == 0:
                score += w[mine]
            if mine == 0:
                score -= w[theirs]
        v = math.tanh(0.08 * score)
        return [v, -v]

    # ---- serialise ---------------------------------------------------------
    def serialize(self, state):
        return {
            "board": {_fmt(sq): "".join(str(o) for o in col)
                      for sq, col in state.board.items()},
            "hands": list(state.hands),
            "to_move": state.to_move,
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return QState(
            board={_cell(k): tuple(int(ch) for ch in v)
                   for k, v in d["board"].items()},
            hands=tuple(d["hands"]),
            to_move=d["to_move"], ply=d.get("ply", 0), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        cells = move.split(">")
        return f"@{cells[0]} sow {'-'.join(cells[1:])}"

    def render(self, state, perspective=None):
        pieces = []
        for sq, col in state.board.items():
            pieces.append({
                "cell": _fmt(sq),
                "owner": col[-1],
                "stack": list(col),
            })
        names = {LIGHT: "Red", DARK: "Blue"}
        h = f"hand {state.hands[LIGHT]}:{state.hands[DARK]}"
        if state.winner is not None:
            cap = f"{names[state.winner]} wins - line of 4 on top ({h})"
        elif self.is_terminal(state):
            cap = f"Draw - all pebbles played, no line ({h})"
        else:
            cap = f"{names[state.to_move]} to move ({h}; green = neutral)"
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
