"""Game of the Amazons — Walter Zamkauskas, 1988 (10x10).

Each side has four amazons that move like a chess queen. A turn is two parts done
by one amazon: first it MOVES (queen-style, any distance, no jumping) to an empty
square, then from its new square it SHOOTS an arrow (also queen-style) to an empty
square. The arrow permanently blocks that square for the rest of the game. Nothing
is ever captured. The first player who cannot complete a move loses.

Each turn fires exactly one arrow, so the empty squares strictly decrease and the
game always ends (<= 92 turns); there are no draws. The deep strategy is to wall
off territory and strangle the opponent's mobility.

A move is a three-cell clickable path "from>to>arrow": click the amazon, its
destination, then the arrow's landing square. Player 0 = White, 1 = Black; White
moves first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 10
NAMES = {0: "White", 1: "Black"}
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


@dataclass
class AmazonsState:
    queens: dict = field(default_factory=dict)   # (c, r) -> player
    arrows: set = field(default_factory=set)      # blocked cells
    to_move: int = 0


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _start():
    queens = {(0, 3): 0, (3, 0): 0, (6, 0): 0, (9, 3): 0,
              (0, 6): 1, (3, 9): 1, (6, 9): 1, (9, 6): 1}
    return queens


def _reach(start, blocked: set) -> list:
    """Queen-style empty squares reachable from `start` (start itself excluded)."""
    out = []
    c, r = start
    for dc, dr in DIRS:
        cc, rr = c + dc, r + dr
        while _on(cc, rr) and (cc, rr) not in blocked:
            out.append((cc, rr))
            cc += dc
            rr += dr
    return out


class Amazons(Game):
    uid = "amazons"
    name = "Amazons"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AmazonsState:
        return AmazonsState(queens=_start())

    def current_player(self, s: AmazonsState) -> int:
        return s.to_move

    def _occupied(self, s: AmazonsState) -> set:
        return set(s.queens) | s.arrows

    def _triples(self, s: AmazonsState):
        occ = self._occupied(s)
        for pos, owner in s.queens.items():
            if owner != s.to_move:
                continue
            for to in _reach(pos, occ):
                # the amazon has vacated `pos` and now sits on `to`
                occ2 = (occ - {pos}) | {to}
                for arrow in _reach(to, occ2):
                    yield pos, to, arrow

    def legal_moves(self, s: AmazonsState) -> list[str]:
        return [f"{p[0]},{p[1]}>{t[0]},{t[1]}>{a[0]},{a[1]}"
                for p, t, a in self._triples(s)]

    def _has_move(self, s: AmazonsState) -> bool:
        return next(self._triples(s), None) is not None

    def apply_move(self, s: AmazonsState, move: str, rng=None) -> AmazonsState:
        frm, to, arrow = (_cell(x) for x in move.split(">"))
        queens = dict(s.queens)
        owner = queens.pop(frm)
        queens[to] = owner
        arrows = set(s.arrows)
        arrows.add(arrow)
        return AmazonsState(queens=queens, arrows=arrows, to_move=1 - s.to_move)

    def is_terminal(self, s: AmazonsState) -> bool:
        return not self._has_move(s)

    def returns(self, s: AmazonsState) -> list[float]:
        # the player to move has no move -> they lose
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    def serialize(self, s: AmazonsState) -> dict:
        return {
            "queens": {f"{c},{r}": p for (c, r), p in s.queens.items()},
            "arrows": [f"{c},{r}" for (c, r) in sorted(s.arrows)],
            "to_move": s.to_move,
        }

    def deserialize(self, d: dict) -> AmazonsState:
        return AmazonsState(
            queens={_cell(k): v for k, v in d["queens"].items()},
            arrows={_cell(k) for k in d.get("arrows", [])},
            to_move=d["to_move"],
        )

    def describe_move(self, s: AmazonsState, move: str) -> str:
        frm, to, arrow = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcdefghij'[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{alg(frm)}-{alg(to)}/{alg(arrow)}"

    def render(self, s: AmazonsState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.queens.items()]
        pieces += [{"cell": f"{c},{r}", "owner": 2, "label": "✕"} for (c, r) in s.arrows]
        if self.is_terminal(s):
            caption = f"{NAMES[1 - s.to_move]} wins"
        else:
            caption = f"{NAMES[s.to_move]} to move (move an amazon, then shoot)"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
