"""Jeson Mor — Mongolian "Running Horses" (Зон мөр).

A chess-family game on a 9x9 board where EVERY piece is a knight (the (1,2)/(2,1)
chess knight: an 8-target leaper that may jump over intervening pieces). Each
player starts with 9 knights filling their back rank: player 0 (White) on row 0,
player 1 (Black) on row 8. A knight captures an enemy knight by landing on it.

The CENTRAL square is (4,4).

WIN (the "occupy-then-vacate the centre" rule — see rules.md):
  A player wins by moving one of their knights ONTO the central square (4,4) and
  then, on a SUBSEQUENT turn, moving a knight OFF the central square — i.e. you
  must OCCUPY the centre and then LEAVE it. Merely passing through (a single move
  that does not start on the centre) is not a win, and merely SITTING on the
  centre is not yet a win: you win the instant you vacate the centre, having
  occupied it. Concretely: a move whose SOURCE cell is (4,4) wins immediately for
  the mover (the knight could only be standing on (4,4) because it arrived there
  on a previous turn).

LOSS: a player who has NO knights left, or who has no legal move on their turn,
loses. (There is no king, no check, no promotion, no pawns — knights are captured
like any other piece.)

Termination: knight games can shuffle indefinitely, so a defensive ply cap forces
a draw if neither side has won by then.

Moves use the platform's clickable cell-path strings: "fc,fr>tc,tr".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 9
CENTER = (4, 4)
PLY_CAP = 400  # defensive draw cap (no published value; just guarantees termination)
NAMES = {0: "White", 1: "Black"}

# The 8 chess-knight leaper offsets (the (1,2)/(2,1) leaper).
KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


@dataclass
class JMState:
    board: dict = field(default_factory=dict)   # (c, r) -> player (0/1); every piece is a knight
    to_move: int = 0
    ply: int = 0
    winner: int = -1                            # -1 = none yet, else the winning player


class JesonMor(Game):
    uid = "jeson_mor"
    name = "Jeson Mor"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup --------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> JMState:
        board = {}
        for c in range(N):
            board[(c, 0)] = 0   # White knights on row 0
            board[(c, N - 1)] = 1  # Black knights on row 8
        return JMState(board=board, to_move=0, ply=0, winner=-1)

    def current_player(self, state) -> int:
        return state.to_move

    # ---- move generation ----------------------------------------------------
    def _knight_targets(self, board, c, r, player):
        """Legal landing squares for the knight at (c,r): on-board cells not
        occupied by a friendly knight (enemy = capture)."""
        for dc, dr in KNIGHT:
            tc, tr = c + dc, r + dr
            if not _on(tc, tr):
                continue
            occ = board.get((tc, tr))
            if occ is None or occ != player:
                yield (tc, tr)

    def legal_moves(self, state) -> list:
        if self.is_terminal(state):
            return []
        player = state.to_move
        out = []
        for (c, r), owner in state.board.items():
            if owner != player:
                continue
            for (tc, tr) in self._knight_targets(state.board, c, r, player):
                out.append(f"{c},{r}>{tc},{tr}")
        return out

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None) -> JMState:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        player = state.board[frm]
        board = dict(state.board)
        board.pop(frm)
        board[to] = player  # captures by landing (overwrites any enemy on `to`)

        winner = -1
        # WIN: vacating the centre. The piece could only be standing on (4,4)
        # because it arrived there on an earlier turn, so leaving it now means
        # "occupied then vacated" -> the mover wins immediately.
        if frm == CENTER:
            winner = player
        else:
            # LOSS by annihilation: if the opponent has no knights left after
            # this move, the opponent cannot move next turn -> the mover wins.
            opp = 1 - player
            if not any(o == opp for o in board.values()):
                winner = player

        return JMState(board=board, to_move=1 - player, ply=state.ply + 1, winner=winner)

    # ---- terminal / returns -------------------------------------------------
    def is_terminal(self, state) -> bool:
        if state.winner != -1:
            return True
        if state.ply >= PLY_CAP:
            return True
        # The player to move has no legal move (no knights, or all knights stuck) -> they lose.
        return not self._has_move(state)

    def _has_move(self, state) -> bool:
        player = state.to_move
        for (c, r), owner in state.board.items():
            if owner != player:
                continue
            for _ in self._knight_targets(state.board, c, r, player):
                return True
        return False

    def returns(self, state) -> list:
        if state.winner != -1:
            return [1.0, -1.0] if state.winner == 0 else [-1.0, 1.0]
        if state.ply >= PLY_CAP:
            return [0.0, 0.0]
        # The side to move has no legal move -> they lose, the opponent wins.
        if not self._has_move(state):
            loser = state.to_move
            return [-1.0, 1.0] if loser == 0 else [1.0, -1.0]
        return [0.0, 0.0]

    # ---- (de)serialize ------------------------------------------------------
    def serialize(self, state) -> dict:
        return {
            "board": {f"{c},{r}": owner for (c, r), owner in state.board.items()},
            "to_move": state.to_move,
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, data) -> JMState:
        return JMState(
            board={_cell(k): v for k, v in data["board"].items()},
            to_move=data["to_move"],
            ply=data.get("ply", 0),
            winner=data.get("winner", -1),
        )

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        cap = "x" if to in state.board and state.board[to] != state.board.get(frm) else "-"
        alg = lambda p: f"{chr(ord('a') + p[0])}{p[1] + 1}"  # noqa: E731
        return f"N{alg(frm)}{cap}{alg(to)}"

    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": owner, "label": "N"}
            for (c, r), owner in state.board.items()
        ]
        if state.winner != -1:
            caption = f"{NAMES[state.winner]} wins"
        elif self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                caption = "Draw"
            else:
                caption = f"{NAMES[0 if ret[0] > 0 else 1]} wins"
        else:
            caption = f"{NAMES[state.to_move]} to move"
        return {
            "board": {
                "type": "square", "width": N, "height": N,
                "tints": {f"{CENTER[0]},{CENTER[1]}": "#d9b3ff"},  # mark the central square
            },
            "pieces": pieces,
            "highlights": [{"cell": f"{CENTER[0]},{CENTER[1]}", "kind": "target"}],
            "caption": caption,
        }
